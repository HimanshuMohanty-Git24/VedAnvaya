"""Seal Luna-v2 output before any v1 or Sol comparison source is opened."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import (
    SemanticAssertionCandidate,
    SemanticEntityCandidate,
    SemanticValidationResult,
)
from vedagraph.semantic.ontology import ALLOWED_PREDICATES

CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
SEAL = ROOT / "v2_output_seal.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ids = [str(row["passage_key"]) for row in config["mantras"]]
    traces = load_jsonl(ROOT / "checklist_trace.jsonl")
    if len(ids) != 120 or len(traces) != 120 or {row["passage_key"] for row in traces} != set(ids):
        raise RuntimeError("v2 seal requires exactly one complete trace for each selected id")
    if any(
        not row.get("checklist_completed")
        or set(row.get("families", {})) != set(ALLOWED_PREDICATES)
        for row in traces
    ):
        raise RuntimeError("v2 seal requires all fourteen predicate families in every trace")
    candidates = [
        SemanticAssertionCandidate.model_validate(row)
        for row in load_jsonl(ROOT / "semantic_candidates.jsonl")
    ]
    entities = [
        SemanticEntityCandidate.model_validate(row)
        for row in load_jsonl(ROOT / "semantic_entities_candidates.jsonl")
    ]
    validations = [
        SemanticValidationResult.model_validate(row)
        for row in load_jsonl(ROOT / "semantic_validation.jsonl")
    ]
    if not {item.subject_key for item in candidates} <= set(ids):
        raise RuntimeError("candidate subject set is outside benchmark")
    rejected = sum(item.status.value == "VALIDATION_REJECTED" for item in validations)
    if rejected:
        raise RuntimeError(f"v2 seal refuses {rejected} validation rejections")
    output_names = [
        "semantic_candidates.jsonl",
        "semantic_entities_candidates.jsonl",
        "semantic_validation.jsonl",
        "accepted_semantic_assertions.jsonl",
        "review_semantic_assertions.jsonl",
        "rejected_semantic_assertions.jsonl",
        "evidence_packet_index.jsonl",
        "parse_errors.jsonl",
        "normalization_queue.jsonl",
        "token_usage.json",
        "cost_report.json",
        "checklist_trace.jsonl",
        "codex_direct_payloads.jsonl",
        "batch_manifest.json",
    ]
    output_hashes = {name: file_sha256(ROOT / name) for name in output_names}
    complete_hash = canonical_sha256(
        {
            "output_hashes": output_hashes,
            "packet_hashes": {
                row["passage_key"]: row["input_sha256"]
                for row in load_jsonl(ROOT / "evidence_packet_index.jsonl")
            },
            "checklist_count": len(traces),
        }
    )
    seal = {
        "seal_version": "rigveda-semantic-luna-v2-output-seal-v1",
        "run_id": "vedagraph-rigveda-semantic-luna-v2-120",
        "model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "prompt_version": "rigveda-semantic-extraction-v2",
        "human_gold_status": "UNANNOTATED",
        "selected_count": len(ids),
        "selected_ids_sha256": canonical_sha256(sorted(ids)),
        "config_sha256": file_sha256(CONFIG),
        "packet_hashes": {
            row["passage_key"]: row["input_sha256"]
            for row in load_jsonl(ROOT / "evidence_packet_index.jsonl")
        },
        "output_hashes": output_hashes,
        "complete_extraction_sha256": complete_hash,
        "assertion_count": len(candidates),
        "entity_candidate_count": len(entities),
        "validation_rejected_count": rejected,
        "checklist_trace_count": len(traces),
        "comparison_sources_opened": False,
        "sealed_at": datetime.now(UTC).isoformat(),
    }
    SEAL.write_text(
        json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "seal": str(SEAL),
                "complete_extraction_sha256": complete_hash,
                "assertions": len(candidates),
                "entities": len(entities),
                "traces": len(traces),
                "comparison_sources_opened": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
