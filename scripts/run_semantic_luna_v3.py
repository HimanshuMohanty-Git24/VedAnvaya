"""Validate and materialize the native v3 extraction without opening historical outputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.heuristic_baseline import BASELINE_PROVENANCE
from vedagraph.semantic.v3 import PROMPT_VERSION, validate_v3_payload

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
PROMPT = Path("prompts/semantic_extraction_v3.md")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: Iterable[object]) -> None:
    path.write_text(
        "".join(
            json.dumps(
                row.model_dump(mode="json") if hasattr(row, "model_dump") else row,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    if (ROOT / "comparison_sources_opened.marker").exists():
        raise RuntimeError("v3 run refuses to execute after comparison sources opened")
    config: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    selected = [str(row["passage_key"]) for row in config["mantras"]]
    if len(selected) != 120 or len(set(selected)) != 120:
        raise RuntimeError("v3 run requires the sealed 120-mantra selection")
    selected_set = set(selected)
    packets: dict[str, EvidencePacket] = {}
    payloads: dict[str, SemanticExtractionV3] = {}
    traces: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    assertion_rows: list[object] = []
    object_rows: list[object] = []
    for evidence_path in sorted((ROOT / "batches").glob("batch_*/evidence.jsonl")):
        batch_dir = evidence_path.parent
        extraction_path = batch_dir / "v3_extractions.jsonl"
        trace_path = batch_dir / "predicate_check_trace.jsonl"
        evidence_rows = [
            EvidencePacket.model_validate(json.loads(line))
            for line in evidence_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        extraction_rows = [
            SemanticExtractionV3.model_validate(json.loads(line))
            for line in extraction_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        trace_rows = [
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not (len(evidence_rows) == len(extraction_rows) == len(trace_rows) == 15):
            raise RuntimeError(
                f"{batch_dir}: every batch must contain 15 packets, payloads, and traces"
            )
        batch_assertions: list[object] = []
        batch_objects: list[object] = []
        batch_validation: list[dict[str, Any]] = []
        for packet, payload, trace in zip(evidence_rows, extraction_rows, trace_rows, strict=True):
            if packet.passage_key not in selected_set or payload.mantra_id != packet.citation:
                raise RuntimeError(f"{batch_dir}: packet/payload outside selected benchmark")
            canonical = frozenset(item.entity_key for item in packet.mentions)
            errors = validate_v3_payload(payload, packet, canonical_entity_ids=canonical)
            packets[packet.passage_key] = packet
            payloads[packet.passage_key] = payload
            traces.append(trace)
            for assertion in payload.assertions:
                batch_assertions.append(assertion)
                assertion_rows.append(assertion)
                batch_objects.append(assertion.object)
                object_rows.append(assertion.object)
            batch_objects.extend(payload.ontology_gaps)
            object_rows.extend(payload.ontology_gaps)
            batch_validation.append(
                {
                    "passage_key": packet.passage_key,
                    "status": "VALID" if not errors else "REJECTED",
                    "errors": errors,
                    "assertion_count": len(payload.assertions),
                    "ontology_gap_count": len(payload.ontology_gaps),
                }
            )
            validation_rows.extend(batch_validation[-1:])
        write_jsonl(batch_dir / "assertions.jsonl", batch_assertions)
        write_jsonl(batch_dir / "objects.jsonl", batch_objects)
        write_jsonl(batch_dir / "validation.jsonl", batch_validation)
        (batch_dir / "stats.json").write_text(
            json.dumps(
                {
                    "batch": batch_dir.name,
                    "mantra_count": 15,
                    "assertion_count": len(batch_assertions),
                    "object_count": len(batch_objects),
                    "validation_rejections": sum(
                        row["status"] == "REJECTED" for row in batch_validation
                    ),
                    "complete_predicate_traces": sum(
                        bool(row.get("checklist_completed")) for row in trace_rows
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if set(packets) != selected_set or len(payloads) != 120 or len(traces) != 120:
        raise RuntimeError("v3 materialization does not cover exactly the selected 120 mantras")
    if any(not trace.get("checklist_completed") for trace in traces):
        raise RuntimeError("v3 requires a complete fourteen-predicate checklist per mantra")
    write_jsonl(ROOT / "v3_extractions.jsonl", [payloads[key] for key in selected])
    write_jsonl(ROOT / "semantic_v3_assertions.jsonl", assertion_rows)
    write_jsonl(ROOT / "semantic_v3_objects.jsonl", object_rows)
    write_jsonl(ROOT / "v3_validation.jsonl", validation_rows)
    write_jsonl(
        ROOT / "evidence_packet_index.jsonl", [packets[key].index_row() for key in sorted(packets)]
    )
    write_jsonl(ROOT / "predicate_check_trace.jsonl", traces)
    errors = [error for row in validation_rows for error in row["errors"]]
    started = datetime.now(UTC).isoformat()
    run_manifest = {
        "run_id": ROOT.name,
        "model": BASELINE_PROVENANCE,
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "reasoning": "high",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": sha256(PROMPT),
        "schema_sha256": sha256(SCHEMA),
        "benchmark_config_sha256": sha256(CONFIG),
        "selected_id_sha256": hashlib.sha256(
            json.dumps(sorted(selected), separators=(",", ":")).encode()
        ).hexdigest(),
        "selected_count": 120,
        "batch_count": 8,
        "batch_size": 15,
        "packet_hashes": {key: packets[key].input_sha256 for key in sorted(packets)},
        "assertion_count": len(assertion_rows),
        "object_count": len(object_rows),
        "validation_rejection_count": len(errors),
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "created_at": started,
        "comparison_sources_opened": False,
    }
    (ROOT / "semantic_v3_run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mantras": 120,
                "assertions": len(assertion_rows),
                "objects": len(object_rows),
                "validation_rejections": len(errors),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
