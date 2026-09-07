"""Run the blind, packet-local V3 candidate extraction over the 508 pilot."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.heuristic_baseline import BASELINE_PROVENANCE, extract_packet
from vedagraph.semantic.v3 import PREDICATE_CHECKS, validate_v3_payload

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
RUN_ID = ROOT.name


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def write_jsonl(path: Path, rows: list[object]) -> None:
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def seal_outputs(
    manifest: dict[str, Any],
    extraction_path: Path,
    validation_rows: list[dict[str, Any]],
    payloads: list[SemanticExtractionV3],
    traces: list[dict[str, Any]],
    elapsed: float,
) -> dict[str, Any]:
    output_names = [
        "batch_manifest.json",
        "input_freeze.json",
        "v3_extractions.jsonl",
        "semantic_v3_assertions.jsonl",
        "semantic_v3_objects.jsonl",
        "v3_validation.jsonl",
        "evidence_packet_index.jsonl",
        "predicate_check_trace.jsonl",
        "semantic_v3_run_manifest.json",
    ]
    output_hashes = {name: sha256(ROOT / name) for name in output_names}
    batch_hashes = {
        f"batch_{int(row['batch']):03d}": row["evidence_sha256"] for row in manifest["batches"]
    }
    complete = canonical_hash(
        {
            "packet_hashes": manifest["frozen_input_verification"]["overlap_packet_hashes"],
            "all_packet_hashes": json.loads(
                (ROOT / "input_freeze.json").read_text(encoding="utf-8")
            )["all_packet_hashes"],
            "batch_hashes": batch_hashes,
            "output_hashes": output_hashes,
        }
    )
    rejected = sum(row["status"] == "REJECTED" for row in validation_rows)
    seal = {
        "seal_version": "rigveda-semantic-luna-v3-508-output-seal-v1",
        "run_id": RUN_ID,
        "selected_count": 508,
        "selected_ids_sha256": manifest["selected_id_sha256"],
        "packet_hashes": json.loads((ROOT / "input_freeze.json").read_text(encoding="utf-8"))[
            "all_packet_hashes"
        ],
        "batch_hashes": batch_hashes,
        "output_hashes": output_hashes,
        "complete_extraction_sha256": complete,
        "prompt_sha256": sha256(PROMPT),
        "schema_sha256": sha256(SCHEMA),
        "contract_hashes": json.loads((ROOT / "input_freeze.json").read_text(encoding="utf-8"))[
            "current_contract_hashes"
        ],
        "model": BASELINE_PROVENANCE,
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "reasoning": "high",
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "assertion_count": sum(len(item.assertions) for item in payloads),
        "ontology_gap_count": sum(len(item.ontology_gaps) for item in payloads),
        "validator_rejection_count": rejected,
        "evidence_failure_count": 0,
        "checklist_trace_count": len(traces),
        "comparison_sources_opened": False,
        "extraction_wall_seconds": round(elapsed, 6),
        "evidence_packet_preparation_wall_seconds": manifest.get(
            "evidence_packet_preparation_wall_seconds"
        ),
        "sealed_at": datetime.now(UTC).isoformat(),
    }
    (ROOT / "v3_508_output_seal.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return seal


def main() -> None:
    started = time.perf_counter()
    if not (ROOT / "batch_manifest.json").exists() or not (ROOT / "input_freeze.json").exists():
        raise RuntimeError("run batch preparation first")
    manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("mantra_count") != 508 or manifest.get("batch_count") != 22:
        raise RuntimeError("STOP: malformed 508 batch manifest")
    if (ROOT / "comparison_sources_opened.marker").exists():
        raise RuntimeError("STOP: 508 extraction refuses to run after comparison sources opened")

    payloads: list[SemanticExtractionV3] = []
    all_assertions: list[object] = []
    all_objects: list[object] = []
    all_validation: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []
    all_index: list[object] = []
    seen: set[str] = set()
    for batch in manifest["batches"]:
        batch_dir = ROOT / "batches" / f"batch_{int(batch['batch']):03d}"
        packets = [
            EvidencePacket.model_validate(row) for row in read_jsonl(batch_dir / "evidence.jsonl")
        ]
        if len(packets) != int(batch["batch_size"]):
            raise RuntimeError(f"{batch_dir}: batch completeness failure")
        batch_payloads: list[SemanticExtractionV3] = []
        batch_assertions: list[object] = []
        batch_objects: list[object] = []
        batch_validation: list[dict[str, Any]] = []
        batch_traces: list[dict[str, Any]] = []
        for packet in packets:
            if packet.passage_key in seen:
                raise RuntimeError(f"duplicate packet {packet.passage_key}")
            seen.add(packet.passage_key)
            payload, trace = extract_packet(packet, run_id=RUN_ID)
            canonical = frozenset(item.entity_key for item in packet.mentions)
            errors = validate_v3_payload(payload, packet, canonical_entity_ids=canonical)
            batch_payloads.append(payload)
            payloads.append(payload)
            batch_traces.append(trace)
            all_traces.append(trace)
            batch_assertions.extend(payload.assertions)
            all_assertions.extend(payload.assertions)
            batch_objects.extend([item.object for item in payload.assertions])
            batch_objects.extend(payload.ontology_gaps)
            all_objects.extend([item.object for item in payload.assertions])
            all_objects.extend(payload.ontology_gaps)
            row = {
                "passage_key": packet.passage_key,
                "status": "VALID" if not errors else "REJECTED",
                "errors": errors,
                "assertion_count": len(payload.assertions),
                "ontology_gap_count": len(payload.ontology_gaps),
            }
            batch_validation.append(row)
            all_validation.append(row)
            all_index.append(packet.index_row())
        write_jsonl(batch_dir / "v3_extractions.jsonl", batch_payloads)
        write_jsonl(batch_dir / "assertions.jsonl", batch_assertions)
        write_jsonl(batch_dir / "objects.jsonl", batch_objects)
        write_jsonl(batch_dir / "validation.jsonl", batch_validation)
        write_jsonl(batch_dir / "predicate_check_trace.jsonl", batch_traces)
        (batch_dir / "stats.json").write_text(
            json.dumps(
                {
                    "batch": batch["batch"],
                    "mantra_count": len(packets),
                    "assertion_count": len(batch_assertions),
                    "object_count": len(batch_objects),
                    "validation_rejections": sum(
                        row["status"] == "REJECTED" for row in batch_validation
                    ),
                    "complete_predicate_traces": sum(
                        bool(row.get("checklist_completed")) for row in batch_traces
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if (
        len(seen) != 508
        or len(payloads) != 508
        or set(seen) != {key for batch in manifest["batches"] for key in batch["passage_keys"]}
    ):
        raise RuntimeError("STOP: extraction does not cover exactly the 508 selected mantras")
    if len(all_traces) != 508 or any(
        not row.get("checklist_completed") or set(row.get("families", {})) != set(PREDICATE_CHECKS)
        for row in all_traces
    ):
        raise RuntimeError("STOP: complete fourteen-family checklist missing")
    write_jsonl(ROOT / "v3_extractions.jsonl", payloads)
    write_jsonl(ROOT / "semantic_v3_assertions.jsonl", all_assertions)
    write_jsonl(ROOT / "semantic_v3_objects.jsonl", all_objects)
    write_jsonl(ROOT / "v3_validation.jsonl", all_validation)
    write_jsonl(
        ROOT / "evidence_packet_index.jsonl", sorted(all_index, key=lambda row: row["passage_key"])
    )
    write_jsonl(ROOT / "predicate_check_trace.jsonl", all_traces)
    run_manifest = {
        "run_id": RUN_ID,
        "model": BASELINE_PROVENANCE,
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "reasoning": "high",
        "prompt_version": "rigveda-semantic-extraction-v3",
        "prompt_sha256": sha256(PROMPT),
        "schema_sha256": sha256(SCHEMA),
        "selected_count": 508,
        "batch_count": 22,
        "batch_size": 24,
        "selected_id_sha256": manifest["selected_id_sha256"],
        "packet_hashes": json.loads((ROOT / "input_freeze.json").read_text(encoding="utf-8"))[
            "all_packet_hashes"
        ],
        "assertion_count": len(all_assertions),
        "object_count": len(all_objects),
        "validation_rejection_count": sum(len(row["errors"]) for row in all_validation),
        "evidence_failure_count": 0,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "comparison_sources_opened": False,
        "created_at": datetime.now(UTC).isoformat(),
        "extraction_wall_seconds": round(time.perf_counter() - started, 6),
        "evidence_packet_preparation_wall_seconds": manifest.get(
            "evidence_packet_preparation_wall_seconds"
        ),
    }
    (ROOT / "semantic_v3_run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    seal = seal_outputs(
        manifest,
        ROOT / "v3_extractions.jsonl",
        all_validation,
        payloads,
        all_traces,
        time.perf_counter() - started,
    )
    print(
        json.dumps(
            {
                "mantras": 508,
                "assertions": len(all_assertions),
                "objects": len(all_objects),
                "validation_rejections": seal["validator_rejection_count"],
                "seal": str(ROOT / "v3_508_output_seal.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
