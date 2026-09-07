"""Seal the complete v3 extraction before any historical comparison source is opened."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.semantic.v3 import PREDICATE_CHECKS

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def main() -> None:
    if (ROOT / "comparison_sources_opened.marker").exists():
        raise RuntimeError("cannot create a clean v3 seal after comparison sources opened")
    config: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ids = [str(row["passage_key"]) for row in config["mantras"]]
    manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    if len(ids) != 120 or manifest["batch_count"] != 8 or manifest["batch_size"] != 15:
        raise RuntimeError("v3 seal requires exactly eight independent batches of fifteen")
    traces = rows(ROOT / "predicate_check_trace.jsonl")
    if len(traces) != 120 or {row["passage_key"] for row in traces} != set(ids):
        raise RuntimeError("v3 seal requires one trace per selected mantra")
    if any(
        not row.get("checklist_completed") or set(row.get("families", {})) != set(PREDICATE_CHECKS)
        for row in traces
    ):
        raise RuntimeError("v3 seal requires the complete fourteen-family checklist")
    payloads = [
        SemanticExtractionV3.model_validate(row) for row in rows(ROOT / "v3_extractions.jsonl")
    ]
    if len(payloads) != 120 or {item.mantra_id for item in payloads} != {
        str(row["citation"]) for row in config["mantras"]
    }:
        raise RuntimeError("v3 seal requires exactly 120 schema-valid payloads")
    validation = rows(ROOT / "v3_validation.jsonl")
    rejected = sum(row["status"] == "REJECTED" for row in validation)
    if rejected:
        raise RuntimeError(f"v3 seal refuses {rejected} validation rejections")
    packet_hashes = {
        key: value for batch in manifest["batches"] for key, value in batch["packet_hashes"].items()
    }
    output_names = [
        "batch_manifest.json",
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
        f"batch_{int(batch['batch']):03d}": batch["evidence_sha256"]
        for batch in manifest["batches"]
    }
    complete_hash = canonical_hash(
        {
            "packet_hashes": packet_hashes,
            "batch_hashes": batch_hashes,
            "output_hashes": output_hashes,
        }
    )
    seal = {
        "seal_version": "rigveda-semantic-luna-v3-output-seal-v1",
        "run_id": ROOT.name,
        "selected_count": 120,
        "selected_ids_sha256": canonical_hash(sorted(ids)),
        "packet_hashes": packet_hashes,
        "batch_hashes": batch_hashes,
        "output_hashes": output_hashes,
        "complete_extraction_sha256": complete_hash,
        "prompt_sha256": sha256(PROMPT),
        "schema_sha256": sha256(SCHEMA),
        "model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "reasoning": "high",
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "assertion_count": sum(len(item.assertions) for item in payloads),
        "ontology_gap_count": sum(len(item.ontology_gaps) for item in payloads),
        "validator_rejection_count": rejected,
        "checklist_trace_count": len(traces),
        "comparison_sources_opened": False,
        "sealed_at": datetime.now(UTC).isoformat(),
    }
    (ROOT / "v3_output_seal.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "seal": str(ROOT / "v3_output_seal.json"),
                "complete_extraction_sha256": complete_hash,
                "assertions": seal["assertion_count"],
                "gaps": seal["ontology_gap_count"],
                "comparison_sources_opened": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
