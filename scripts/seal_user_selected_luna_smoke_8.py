"""Seal one 8-task smoke run before any cross-run comparison."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.semantic.codex_direct import (  # noqa: E402
    ExecutionStore,
    ModelAuthoredResponse,
    canonical_sha256,
    file_sha256,
    load_run_contract,
)
from vedagraph.semantic.object_ontology import SemanticObjectKind  # noqa: E402

INPUT_ROOT = ROOT / "data/semantic/vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-input"
SELECTION = ROOT / "data/builds/rigveda_semantic_v3_2_user_selected_luna_smoke_8.yaml"
PROMPT = ROOT / "prompts/semantic_extraction_v3.2.md"
SCHEMA = ROOT / "schemas/semantic_extraction_v3.schema.json"
ONTOLOGY = ROOT / "src/vedagraph/semantic/ontology.py"
RUNS = (
    "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-a",
    "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-b",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contract_for(run_id: str):
    return load_run_contract(
        run_id=run_id,
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        ontology_path=ONTOLOGY,
        model_requested="gpt-5.6-luna",
        reasoning_requested="high",
        execution_version="rigveda-semantic-execution-v3.2",
    )


def seal_run(run_id: str, expected_ids: set[str]) -> dict[str, object]:
    root = INPUT_ROOT / run_id
    seal_path = root / "output_seal.json"
    if seal_path.exists():
        raise RuntimeError(f"refusing to overwrite existing seal: {seal_path}")
    contract = contract_for(run_id)
    store = ExecutionStore(root / "store")
    task_paths = sorted((root / "store" / "tasks").glob("*/task.json"))
    if len(task_paths) != 8:
        raise RuntimeError(f"{run_id}: expected 8 prepared tasks, found {len(task_paths)}")

    final_responses: dict[str, tuple[str, Path, ModelAuthoredResponse]] = {}
    receipt_failures = 0
    packet_hash_failures = 0
    evidence_failures = 0
    span_failures = 0
    binding_failures = 0
    ontology_type_failures = 0
    heuristic_contamination = 0
    for task_path in task_paths:
        task = store.load_task(json.loads(task_path.read_text(encoding="utf-8"))["task_id"])
        attempts = sorted((task_path.parent / "attempts").glob("*/raw_response.json"))
        valid: list[tuple[str, Path, ModelAuthoredResponse]] = []
        for raw_path in attempts:
            response = ModelAuthoredResponse.model_validate_json(
                raw_path.read_text(encoding="utf-8")
            )
            try:
                validated = store.import_response(raw_path, contract)
            except ValueError as exc:
                text = str(exc)
                receipt_failures += int("receipt" in text or "task " in text or "run id" in text)
                packet_hash_failures += int(
                    "packet hash" in text or "evidence_packet_sha256" in text
                )
                evidence_failures += int("evidence" in text)
                span_failures += int("span" in text or "anchor" in text)
                binding_failures += int("binding" in text)
                ontology_type_failures += int("type boundary" in text or "ontology" in text)
                continue
            if validated.payload.prompt_version != "rigveda-semantic-extraction-v3":
                raise RuntimeError(f"{run_id}: top-level payload schema identity drift")
            for candidate in [*validated.payload.assertions, *validated.payload.ontology_gaps]:
                if (
                    candidate.object.extraction_model != "gpt-5.6-luna"
                    or candidate.object.prompt_version != "rigveda-semantic-extraction-v3.2"
                ):
                    heuristic_contamination += 1
            valid.append((response.receipt.attempt_id, raw_path, response))
        if not valid:
            raise RuntimeError(f"{run_id}: no valid final response for {task.passage_id}")
        final_responses[task.passage_id] = min(valid, key=lambda row: row[0])

    if set(final_responses) != expected_ids:
        raise RuntimeError(f"{run_id}: final passage set does not match selection")

    assertions = [
        response.semantic_output.assertions for _, _, response in final_responses.values()
    ]
    predicate_counts = Counter(item.predicate.value for rows in assertions for item in rows)
    object_kind_counts = Counter(
        item.object.object_kind.value for rows in assertions for item in rows
    )
    no_claim_count = sum(
        bool(response.semantic_output.no_claim_reasons)
        for _, _, response in final_responses.values()
    )
    canonical_reference_count = sum(
        item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
        for rows in assertions
        for item in rows
    )
    response_files = sorted((root / "responses").glob("TASK_*_attempt_*.json"))
    imported_hashes = {sha256_bytes(path.read_bytes()) for _, path, _ in final_responses.values()}
    unimported = [
        path for path in response_files if sha256_bytes(path.read_bytes()) not in imported_hashes
    ]
    seal = {
        "seal_version": "rigveda-semantic-user-selected-luna-v3.2-smoke-8-output-seal-v1",
        "run_id": run_id,
        "sealed_before_comparison": True,
        "execution_contract": contract.model_dump(mode="json"),
        "model_provenance_classification": "USER_SELECTED_MODEL_UNATTESTED",
        "user_selected_model": "gpt-5.6-luna",
        "requested_model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "reasoning": "high",
        "provider_build_metadata": "UNAVAILABLE",
        "independent_runtime_model_attestation": "UNAVAILABLE",
        "selection_hash": yaml.safe_load(SELECTION.read_text(encoding="utf-8"))["selection_hash"],
        "expected_passages": 8,
        "final_passages": len(final_responses),
        "counts": {
            "prepared_tasks": len(task_paths),
            "final_validated_tasks": len(final_responses),
            "assertions": sum(len(row) for row in assertions),
            "no_claim_passages": no_claim_count,
            "authored_response_files": len(response_files),
            "selected_final_responses": len(final_responses),
            "unimported_authored_responses": len(unimported),
            "retry_count": len(response_files) - len(final_responses),
        },
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "object_kind_counts": dict(sorted(object_kind_counts.items())),
        "canonical_reference_count": canonical_reference_count,
        "integrity": {
            "receipt_failures": receipt_failures,
            "packet_hash_failures": packet_hash_failures,
            "evidence_failures": evidence_failures,
            "span_failures": span_failures,
            "binding_failures": binding_failures,
            "ontology_type_failures": ontology_type_failures,
            "heuristic_contamination": heuristic_contamination,
            "missing_final_tasks": 8 - len(final_responses),
        },
        "selected_response_hashes": {
            passage_id: {
                "attempt_id": attempt,
                "raw_response_sha256": sha256_bytes(path.read_bytes()),
            }
            for passage_id, (attempt, path, _) in sorted(final_responses.items())
        },
        "response_file_hashes": {
            path.name: sha256_bytes(path.read_bytes()) for path in response_files
        },
        "unimported_authored_response_hashes": {
            path.name: sha256_bytes(path.read_bytes()) for path in unimported
        },
        "model_self_agreement_is_accuracy": False,
        "human_gold_status": "UNANNOTATED",
        "canonical_promotion": False,
    }
    seal["seal_sha256"] = canonical_sha256(seal)
    seal_path.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "output_seal.sha256").write_text(
        f"{file_sha256(seal_path)}  output_seal.json\n", encoding="utf-8"
    )
    return seal


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in RUNS:
        raise SystemExit(f"usage: seal {'|'.join(RUNS)}")
    selection = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    expected = {row["passage_key"] for row in selection["mantras"]}
    print(json.dumps(seal_run(sys.argv[1], expected), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
