"""Materialize one blind Sol-review batch from compact, human-readable decisions.

This command intentionally accepts only EvidencePacket paths.  Luna candidate paths are
not command-line options, so the independent phase cannot reveal extractor output.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.silver import (
    SilverEvidenceReference,
    SilverOntologyGap,
    SilverSemanticAnnotation,
    SilverSemanticAssertion,
    SilverSemanticEntity,
)
from vedagraph.semantic.ontology import ONTOLOGY_VERSION
from vedagraph.semantic.silver import (
    SILVER_REVIEWER_MODEL,
    SILVER_RUN_ID,
    load_blind_packets,
    persist_blind_batch,
)


def _candidate_key(mantra_id: str, label: str) -> str:
    digest = hashlib.sha256(f"{mantra_id}|{label}".encode()).hexdigest()[:16]
    return f"VG:SILVER:CAND:{digest.upper()}"


def _references(raw: list[dict[str, str]], packet: Any) -> list[SilverEvidenceReference]:
    references: list[SilverEvidenceReference] = []
    for item in raw:
        reference_id = item["reference_id"]
        if reference_id == "$TARGET_TRANSLATION":
            if packet.translation is None:
                raise ValueError(f"target has no translation: {packet.passage_key}")
            reference_id = packet.translation.translation_id
        references.append(
            SilverEvidenceReference(
                kind=item["kind"], reference_id=reference_id, note=item.get("note", "")
            )
        )
    return references


def materialize(decision_path: Path, evidence_root: Path, output_root: Path) -> None:
    raw: Any = yaml.safe_load(decision_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("annotations"), list):
        raise ValueError("decision file requires an annotations list")
    ids = frozenset(str(item["mantra_id"]) for item in raw["annotations"])
    evidence_paths = sorted(evidence_root.glob("batch_*/evidence.jsonl"))
    packets = load_blind_packets(evidence_paths, ids)
    annotations: list[SilverSemanticAnnotation] = []
    for item in raw["annotations"]:
        mantra_id = str(item["mantra_id"])
        packet = packets[mantra_id]
        assertions: list[SilverSemanticAssertion] = []
        entities: list[SilverSemanticEntity] = []
        seen_entities: set[tuple[str | None, str]] = set()
        for index, assertion in enumerate(item.get("assertions", []), 1):
            evidence = _references(assertion["evidence"], packet)
            assertions.append(
                SilverSemanticAssertion(
                    assertion_id=f"SILVER:{mantra_id}:{index:02d}",
                    subject=mantra_id,
                    predicate=assertion["predicate"],
                    object_label=assertion["object_label"],
                    object_node_type=assertion.get("object_node_type"),
                    object_entity_key=assertion.get("object_entity_key"),
                    explicitness=assertion.get("explicitness", "EXPLICIT"),
                    evidence=evidence,
                    rationale_code=assertion.get("rationale_code", "TEXT_EXPLICIT"),
                    confidence=float(assertion.get("confidence", 0.85)),
                )
            )
            entity_identity = (assertion.get("object_entity_key"), assertion["object_label"])
            if entity_identity not in seen_entities:
                seen_entities.add(entity_identity)
                entities.append(
                    SilverSemanticEntity(
                        label=assertion["object_label"],
                        node_type=assertion.get("object_node_type", "COSMIC_ENTITY"),
                        entity_key=assertion.get("object_entity_key"),
                        candidate_key=(
                            None
                            if assertion.get("object_entity_key")
                            else _candidate_key(mantra_id, assertion["object_label"])
                        ),
                        evidence=evidence,
                    )
                )
        no_claim = not assertions
        annotations.append(
            SilverSemanticAnnotation(
                mantra_id=mantra_id,
                citation=packet.citation,
                reviewer_model=SILVER_REVIEWER_MODEL,
                ontology_version=ONTOLOGY_VERSION,
                evidence_packet_hash=packet.input_sha256,
                entities=entities,
                semantic_assertions=assertions,
                no_claim=no_claim,
                no_claim_code="NO_SUPPORTED_SEMANTIC_ASSERTION" if no_claim else None,
                uncertainties=list(item.get("uncertainties", [])),
                ontology_gaps=[
                    SilverOntologyGap.model_validate(gap) for gap in item.get("ontology_gaps", [])
                ],
                reviewed_at=raw["reviewed_at"],
                review_run_id=SILVER_RUN_ID,
                batch_id=raw["batch_id"],
            )
        )
    batch_id = str(raw["batch_id"])
    persist_blind_batch(
        annotations_path=output_root / "silver_annotations.jsonl",
        batch_path=output_root / "blind_batches" / batch_id / "annotations.jsonl",
        annotations=annotations,
        packets=packets,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("decision_path", type=Path)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    materialize(args.decision_path, args.evidence_root, args.output_root)


if __name__ == "__main__":
    main()
