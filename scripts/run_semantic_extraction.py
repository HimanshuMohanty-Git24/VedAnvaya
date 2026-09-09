#!/usr/bin/env python3
"""The two deterministic halves of the model-based semantic stage.

The stage is split in two on purpose. ``--emit-packets`` selects the passages and writes
exactly what a model may see; ``--ingest`` validates what came back and writes the
candidate rows. Only the gap between them is non-deterministic, and nothing in this
repository hides that gap inside a build step.

Usage:
    python scripts/run_semantic_extraction.py --emit-packets --out packets.json
    python scripts/run_semantic_extraction.py --ingest extractions.json --model claude-opus-5
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded semantic candidate extraction")
    parser.add_argument("--emit-packets", action="store_true")
    parser.add_argument("--ingest", default="", help="Path to a JSON array of extractions")
    parser.add_argument("--out", default="", help="Where to write packets")
    parser.add_argument("--model", default="", help="Model id, required for --ingest")
    parser.add_argument("--limit", type=int, default=0, help="Override the packet budget")
    return parser.parse_args()


def _inputs() -> tuple[object, dict[str, list[str]], dict[str, list[str]]]:
    """Corpus plus the two lookups packet assembly needs, read from the artifacts."""
    from vedagraph.enrich.build import (
        CONCEPT_ASSERTIONS_FILE,
        PARALLELS_FILE,
        read_artifact,
    )
    from vedagraph.enrich.corpus import load_corpus

    partners: dict[str, list[str]] = {}
    for row in read_artifact(PROJECT_ROOT, PARALLELS_FILE):
        partners.setdefault(row["subject_key"], []).append(row["object_key"])
        partners.setdefault(row["object_key"], []).append(row["subject_key"])

    concepts: dict[str, list[str]] = {}
    for row in read_artifact(PROJECT_ROOT, CONCEPT_ASSERTIONS_FILE):
        concepts.setdefault(row["passage_key"], []).append(row["concept_id"])

    return load_corpus(PROJECT_ROOT), partners, concepts


def emit_packets(out_path: pathlib.Path, limit: int) -> None:
    from vedagraph.enrich.guards import MAX_SEMANTIC_PASSAGES
    from vedagraph.enrich.semantic import build_packets, select_passages

    corpus, partners, concepts = _inputs()
    budget = limit or MAX_SEMANTIC_PASSAGES
    selected = select_passages(corpus, partners, budget)  # type: ignore[arg-type]
    packets = build_packets(selected, partners, concepts)

    by_veda: dict[str, int] = {}
    for packet in packets:
        by_veda[packet.veda] = by_veda.get(packet.veda, 0) + 1
    logger.info("Selected %d packets: %s", len(packets), dict(sorted(by_veda.items())))
    logger.info("With a translation: %d", sum(1 for p in packets if p.translations))
    logger.info("With a cross-Veda parallel: %d", sum(1 for p in packets if p.cross_veda_parallels))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([p.as_dict() for p in packets], ensure_ascii=False, indent=1), "utf-8"
    )
    logger.info("Wrote %s", out_path)


def ingest(path: pathlib.Path, model: str) -> None:
    from vedagraph.enrich.build import RELEASE_DIR, SEMANTIC_CANDIDATES_FILE, write_jsonl
    from vedagraph.enrich.concepts import load_concepts
    from vedagraph.enrich.guards import MAX_SEMANTIC_PASSAGES
    from vedagraph.enrich.semantic import (
        Extraction,
        ObjectVocabulary,
        build_packets,
        ingest_extractions,
        select_passages,
    )
    from vedagraph.graph.entities import iter_devata_nodes

    corpus, partners, concepts_by_passage = _inputs()
    packets = build_packets(
        select_passages(corpus, partners, MAX_SEMANTIC_PASSAGES),  # type: ignore[arg-type]
        partners,
        concepts_by_passage,
    )

    vocabulary = ObjectVocabulary(
        concepts={c.concept_id: c.preferred_label_en for c in load_concepts(PROJECT_ROOT)},
        devatas={d["entity_key"]: d["preferred_label"] for d in iter_devata_nodes(PROJECT_ROOT)},
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    extractions = [
        Extraction(
            passage_key=item["passage_key"],
            predicate=item["predicate"],
            object_label=item["object_label"],
            object_type=item["object_type"],
            evidence_quote=item["evidence_quote"],
            confidence=float(item.get("confidence", 0.5)),
            notes=item.get("notes", ""),
        )
        for item in raw
    ]

    rows, report = ingest_extractions(extractions, packets, vocabulary, model)

    logger.info("=== Semantic ingestion ===")
    logger.info("  proposals            %d", len(extractions))
    logger.info("  accepted as candidate %d", len(rows))
    for reason, count in sorted(report.report.rejected.items()):
        logger.info("  rejected %-32s %d", reason, count)
        for example in report.rejected_examples.get(reason, [])[:3]:
            logger.info("      %s", example)
    for reason, count in sorted(report.report.capped.items()):
        logger.info("  capped   %-32s %d", reason, count)

    digest = write_jsonl(
        PROJECT_ROOT / RELEASE_DIR / SEMANTIC_CANDIDATES_FILE, [row.as_row() for row in rows]
    )
    logger.info("Wrote %s (%s)", SEMANTIC_CANDIDATES_FILE, digest[:16])

    report_path = PROJECT_ROOT / RELEASE_DIR / "semantic_run_report.json"
    report_path.write_text(
        json.dumps(report.report.as_dict(), indent=2, ensure_ascii=False), "utf-8"
    )


def main() -> None:
    args = parse_args()
    if args.emit_packets:
        emit_packets(pathlib.Path(args.out or "packets.json"), args.limit)
        return
    if args.ingest:
        if not args.model:
            logger.error("--model is required for --ingest: an LLM row without a model id "
                         "cannot be attributed and provenance refuses it")
            sys.exit(1)
        ingest(pathlib.Path(args.ingest), args.model)
        return
    logger.error("Nothing to do: pass --emit-packets or --ingest")
    sys.exit(1)


if __name__ == "__main__":
    main()
