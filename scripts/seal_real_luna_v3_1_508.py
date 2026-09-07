"""Seal and revalidate the real-Luna 508 candidate pilot custody.

This script reads only the fresh 508 run, its frozen input manifest, and the repository
validators.  It deliberately does not read heuristic or Sol semantic payloads.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, NoReturn, cast

from vedagraph.semantic.codex_direct import (
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    canonical_sha256,
    response_payload_sha256,
    validate_bindings,
    validate_candidate_invariants,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors
from vedagraph.semantic.v3 import validate_v3_payload

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-508"
EXECUTION_VERSION = "rigveda-semantic-execution-v3.1"
CONTRACT_VERSION = "codex-direct-semantic-v1"
MODEL = "gpt-5.6-luna"
REASONING = "high"
ROOT = Path("data/semantic") / RUN_ID
OLD_HEURISTIC_RUN = "vedagraph-rigveda-semantic-luna-v3-508"
PASSAGE_RE = re.compile(r"^VG:RV:SAK:M(?:0[1-9]|10):S\d{3}:V\d{3}$")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def fail(message: str) -> NoReturn:
    raise SystemExit(f"SEAL_FAILED: {message}")


def main() -> None:
    freeze = read_json(ROOT / "input_freeze.json")
    if freeze.get("run_id") != RUN_ID:
        fail("input freeze run id mismatch")
    if freeze.get("historical_sources_opened") is not False:
        fail("historical sources are not marked closed")
    if freeze.get("human_gold_status") != "UNANNOTATED":
        fail("human gold status is not UNANNOTATED")
    if freeze.get("unlocked_predicates") != []:
        fail("unlocked predicates are not empty")
    if freeze.get("canonical_promotion") is not False:
        fail("canonical promotion is not false")

    selected_ids = list(freeze["selected_ids"])
    if len(selected_ids) != 508 or len(set(selected_ids)) != 508:
        fail("selection is not exactly 508 unique ids")
    if any(not PASSAGE_RE.fullmatch(item) for item in selected_ids):
        fail("selection contains an invalid canonical passage id")
    expected_packet_hashes = dict(freeze["packet_hashes"])
    if set(expected_packet_hashes) != set(selected_ids):
        fail("packet hash map does not match selected ids")
    if canonical_sha256(sorted(selected_ids)) != freeze["selected_ids_sha256"]:
        fail("selection commitment mismatch")

    frozen_paths = {
        "execution_contract_sha256": Path("src/vedagraph/semantic/codex_direct.py"),
        "prompt_sha256": Path("prompts/semantic_extraction_v3.md"),
        "schema_sha256": Path("schemas/semantic_extraction_v3.schema.json"),
        "semantic_ontology_sha256": Path("src/vedagraph/semantic/ontology.py"),
        "object_ontology_sha256": Path("src/vedagraph/semantic/object_ontology.py"),
        "span_validator_sha256": Path("src/vedagraph/semantic/spans.py"),
        "evidence_validator_sha256": Path("src/vedagraph/semantic/evidence.py"),
    }
    frozen_hashes = dict(freeze["frozen_hashes"])
    current_hashes = {key: sha256_file(path) for key, path in frozen_paths.items()}
    if current_hashes != frozen_hashes:
        fail(
            "frozen execution input drift: "
            + json.dumps({"expected": frozen_hashes, "actual": current_hashes}, sort_keys=True)
        )

    contract = RunContract.model_validate_json(
        (ROOT / "store" / "run_contract.json").read_text(encoding="utf-8")
    )
    if contract.run_id != RUN_ID or contract.execution_version != EXECUTION_VERSION:
        fail("run contract identity mismatch")
    if contract.model_requested != MODEL or contract.reasoning_requested != REASONING:
        fail("run contract model/reasoning mismatch")
    if (
        contract.prompt_sha256 != frozen_hashes["prompt_sha256"]
        or contract.schema_sha256 != frozen_hashes["schema_sha256"]
    ):
        fail("run contract prompt/schema mismatch")
    if contract.ontology_sha256 != frozen_hashes["semantic_ontology_sha256"]:
        fail("run contract ontology mismatch")

    packet_rows = [
        json.loads(line)
        for line in (ROOT / "packet_index.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(packet_rows) != 508 or len({row["passage_key"] for row in packet_rows}) != 508:
        fail("packet index is not exactly 508 unique rows")
    index_hashes = {row["passage_key"]: row["input_sha256"] for row in packet_rows}
    if index_hashes != expected_packet_hashes:
        fail("packet index hashes differ from the frozen packet map")

    tasks_root = ROOT / "store" / "tasks"
    task_files = sorted(tasks_root.glob("TASK_*/task.json"))
    if len(task_files) != 508:
        fail(f"prepared task count is {len(task_files)}, expected 508")
    tasks: dict[str, PreparedTask] = {}
    task_hashes: dict[str, str] = {}
    for path in task_files:
        task = PreparedTask.model_validate_json(path.read_text(encoding="utf-8"))
        if task.run_id != RUN_ID or task.execution_version != EXECUTION_VERSION:
            fail(f"task identity mismatch: {path}")
        if task.passage_id not in expected_packet_hashes:
            fail(f"task passage is outside selection: {task.passage_id}")
        if task.evidence_packet_sha256 != expected_packet_hashes[task.passage_id]:
            fail(f"packet hash mismatch for {task.passage_id}")
        if task.passage_id in tasks:
            fail(f"duplicate prepared task passage: {task.passage_id}")
        tasks[task.passage_id] = task
        task_hashes[task.passage_id] = task.task_sha256
    if set(tasks) != set(selected_ids):
        fail("prepared task selection differs from frozen selection")

    response_files = sorted((ROOT / "responses").glob("TASK_*_attempt_*.json"))
    response_records: list[dict[str, Any]] = []
    imported_by_task: dict[str, list[dict[str, Any]]] = {}
    for path in response_files:
        raw = path.read_bytes()
        response = ModelAuthoredResponse.model_validate_json(raw.decode("utf-8"))
        receipt = response.receipt
        response_task = tasks.get(response.receipt.passage_id)
        if response_task is None or response_task.task_id != receipt.task_id:
            fail(f"response is not bound to a prepared task: {path}")
        if (
            receipt.runtime != "CODEX_DIRECT"
            or receipt.requested_model != MODEL
            or receipt.reported_model != MODEL
        ):
            fail(f"receipt provenance mismatch: {path}")
        if receipt.provider_build_metadata != "UNAVAILABLE":
            fail(f"provider build metadata was invented: {path}")
        if receipt.model_response_authored is not True:
            fail(f"response is not model-authored: {path}")
        computed = response_payload_sha256(response)
        if receipt.response_sha256 != computed:
            fail(f"response payload commitment mismatch: {path}")
        imported_path = (
            tasks_root / receipt.task_id.replace(":", "_") / "attempts" / receipt.attempt_id
        )
        raw_store = imported_path / "raw_response.json"
        validated_path = imported_path / "validated.json"
        imported = raw_store.exists() and validated_path.exists() and raw_store.read_bytes() == raw
        record = {
            "task_id": receipt.task_id,
            "passage_key": receipt.passage_id,
            "attempt_id": receipt.attempt_id,
            "response_file": str(path).replace("\\", "/"),
            "raw_response_sha256": sha256_bytes(raw),
            "response_sha256": receipt.response_sha256,
            "imported": imported,
            "validated_file_sha256": sha256_file(validated_path) if imported else None,
        }
        response_records.append(record)
        imported_by_task.setdefault(receipt.task_id, []).append(record)

    if len(response_records) < 508:
        fail("fewer than 508 authored response receipts are present")
    if sum(1 for row in response_records if row["imported"]) != 508:
        fail("final imported response count is not 508")

    validated_records: list[dict[str, Any]] = []
    for passage_key in selected_ids:
        task = tasks[passage_key]
        attempt_dirs = sorted(
            (tasks_root / task.task_id.replace(":", "_") / "attempts").glob("attempt_*/")
        )
        validated_dirs = [path for path in attempt_dirs if (path / "validated.json").exists()]
        if len(validated_dirs) != 1:
            fail(f"expected one terminal validated response for {passage_key}")
        directory = validated_dirs[0]
        raw = (directory / "raw_response.json").read_bytes()
        response = ModelAuthoredResponse.model_validate_json(raw.decode("utf-8"))
        computed = response_payload_sha256(response)
        errors = validate_receipt(
            response.receipt, task, contract, computed_response_sha256=computed
        )
        errors += validate_candidate_invariants(response.semantic_output, task)
        canonical = frozenset(mention.entity_key for mention in task.evidence_packet.mentions)
        errors += validate_v3_payload(
            response.semantic_output, task.evidence_packet, canonical_entity_ids=canonical
        )
        errors += validate_evidence_anchors(response.semantic_output, task.evidence_packet)
        errors += validate_bindings(
            response.semantic_output, response.assertion_bindings, task.evidence_packet
        )
        if errors:
            fail(
                f"accepted response no longer validates for {passage_key}: "
                f"{'; '.join(sorted(set(errors)))}"
            )
        if response.receipt.attempt_id != directory.name:
            fail(f"validated attempt directory mismatch for {passage_key}")
        validated = read_json(directory / "validated.json")
        if (
            validated["raw_response_sha256"] != sha256_bytes(raw)
            or validated["response_sha256"] != response.receipt.response_sha256
        ):
            fail(f"validated custody hash mismatch for {passage_key}")
        validated_records.append(
            {
                "task_id": task.task_id,
                "passage_key": passage_key,
                "attempt_id": response.receipt.attempt_id,
                "raw_response_sha256": sha256_bytes(raw),
                "response_sha256": response.receipt.response_sha256,
                "validated_file_sha256": sha256_file(directory / "validated.json"),
            }
        )

    contamination_markers = (OLD_HEURISTIC_RUN, "heuristic_baseline", "sol silver")
    contamination_files = [
        ROOT / "model_authored_decisions.jsonl",
        *[Path(row["response_file"]) for row in response_records],
    ]
    contamination_hits: list[str] = []
    for path in contamination_files:
        text = path.read_text(encoding="utf-8").lower()
        for marker in contamination_markers:
            if marker.lower() in text:
                contamination_hits.append(f"{path}:{marker}")
    if contamination_hits:
        fail("heuristic/Sol contamination markers found: " + ", ".join(contamination_hits))

    event_rows = [
        json.loads(line)
        for line in (ROOT / "execution_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failed_events = [row for row in event_rows if row.get("state") == "FAILED_IMPORT"]
    final_attempts = {row["passage_key"]: row["attempt_id"] for row in validated_records}
    if len(final_attempts) != 508:
        fail("terminal attempt map is not complete")

    seal = {
        "seal_status": "VALIDATED",
        "run_id": RUN_ID,
        "execution_version": EXECUTION_VERSION,
        "execution_contract_version": CONTRACT_VERSION,
        "execution_contract_sha256": frozen_hashes["execution_contract_sha256"],
        "selection_config_sha256": freeze["selection_config_sha256"],
        "selected_ids_sha256": freeze["selected_ids_sha256"],
        "selected_ids": selected_ids,
        "packet_hashes": expected_packet_hashes,
        "prepared_task_hashes": task_hashes,
        "attempt_histories": response_records,
        "validated_response_hashes": validated_records,
        "execution_events_sha256": sha256_file(ROOT / "execution_events.jsonl"),
        "frozen_hashes": frozen_hashes,
        "regression_run_id": freeze["regression_run_id"],
        "regression_seal_sha256": freeze["regression_seal_sha256"],
        "regression_overlap_count": len(freeze["regression_overlap_ids"]),
        "regression_overlap_packet_hashes_match": freeze["regression_overlap_packet_hashes_match"],
        "model_requested": MODEL,
        "model_reported": MODEL,
        "runtime": "CODEX_DIRECT",
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "human_gold": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened": False,
        "heuristic_baseline_in_custody": False,
        "prepared_tasks": len(tasks),
        "terminal_validated_tasks": len(validated_records),
        "raw_response_receipts": len(response_records),
        "failed_import_events_preserved": len(failed_events),
        "final_imports": len(validated_records),
        "heuristic_contamination": 0,
    }
    seal_path = ROOT / "output_seal.json"
    seal_path.write_text(
        json.dumps(seal, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    seal_hash = sha256_file(seal_path)
    (ROOT / "output_seal.sha256").write_text(
        seal_hash + "  output_seal.json\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "status": "VALIDATED",
                "seal": str(seal_path),
                "seal_sha256": seal_hash,
                "tasks": 508,
                "responses": len(response_records),
                "failed_import_events": len(failed_events),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
