"""Seal the Claude Opus 5 V3.2 448 candidate run. Runs before any historical source is read.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.
ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.

Reads only this run, its frozen inputs, and the repository validators. It re-runs every
validator from scratch on the stored bytes rather than trusting the import that accepted
them, so the seal is a second independent verdict and not a restatement of the first.

Refuses to seal unless all 448 passages hold exactly one terminal validated response.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.semantic.claude_opus5_v3_2 import (  # noqa: E402
    EXECUTION_VERSION,
    EXPECTED_PASSAGES,
    MODEL,
    MODEL_PROVENANCE_CLASSIFICATION,
    PROVENANCE_BUCKET,
    REASONING,
    RUN_ID,
    RUN_ROOT,
    RUNTIME,
    frozen_hashes,
)
from vedagraph.semantic.codex_direct import (  # noqa: E402
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    canonical_sha256,
    response_payload_sha256,
    validate_bindings,
    validate_candidate_invariants,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors  # noqa: E402
from vedagraph.semantic.object_ontology import SemanticObjectKind  # noqa: E402
from vedagraph.semantic.v3 import validate_v3_payload  # noqa: E402

RUN_DIR = ROOT / RUN_ROOT
TASKS_DIR = RUN_DIR / "store" / "tasks"
PASSAGE_RE = re.compile(r"^VG:RV:SAK:M(?:0[1-9]|10):S\d{3}:V\d{3}$")

#: Markers that would mean a historical heuristic, Luna or Sol artefact leaked into this
#: run's custody. Searched over every stored response byte.
CONTAMINATION_MARKERS = (
    "gpt-5.6-luna",
    "heuristic_baseline",
    "DETERMINISTIC_HEURISTIC_BASELINE",
    "vedagraph-rigveda-semantic-luna-v3-508",
    "vedagraph-rigveda-semantic-user-selected-luna",
    "silver-sol",
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"SEAL_FAILED: {message}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    seal_path = RUN_DIR / "output_seal.json"
    if seal_path.exists():
        fail(f"refusing to overwrite an existing seal: {seal_path}")

    freeze = read_json(RUN_DIR / "input_freeze.json")
    if freeze["run_id"] != RUN_ID:
        fail("input freeze run id mismatch")
    for key, expected in (
        ("human_gold_status", "UNANNOTATED"),
        ("unlocked_predicates", []),
        ("canonical_promotion", False),
        ("historical_sources_opened_before_seal", False),
    ):
        if freeze.get(key) != expected:
            fail(f"input freeze {key} is {freeze.get(key)!r}, expected {expected!r}")

    selected_ids = list(freeze["selected_ids"])
    if len(selected_ids) != EXPECTED_PASSAGES or len(set(selected_ids)) != EXPECTED_PASSAGES:
        fail(f"selection is not exactly {EXPECTED_PASSAGES} unique ids")
    if any(PASSAGE_RE.fullmatch(item) is None for item in selected_ids):
        fail("selection contains an invalid canonical passage id")
    if canonical_sha256(sorted(selected_ids)) != freeze["selected_ids_sha256"]:
        fail("selection commitment mismatch")
    expected_packet_hashes = dict(freeze["packet_hashes"])
    if set(expected_packet_hashes) != set(selected_ids):
        fail("packet hash map does not match the selection")

    current = frozen_hashes(ROOT)
    if current != dict(freeze["frozen_hashes"]):
        fail(
            "frozen execution input drift: "
            + json.dumps({"frozen": freeze["frozen_hashes"], "actual": current}, sort_keys=True)
        )

    contract = RunContract.model_validate_json(
        (RUN_DIR / "store" / "run_contract.json").read_text(encoding="utf-8")
    )
    if contract.run_id != RUN_ID or contract.execution_version != EXECUTION_VERSION:
        fail("run contract identity mismatch")
    if contract.model_requested != MODEL or contract.reasoning_requested != REASONING:
        fail("run contract model/reasoning mismatch")
    if contract.runtime != RUNTIME:
        fail(f"run contract runtime is {contract.runtime!r}, expected {RUNTIME.value!r}")
    if contract.prompt_version != "rigveda-semantic-extraction-v3.2":
        fail("run contract does not execute the V3.2 prompt policy")
    if (
        contract.prompt_sha256 != current["prompt_sha256"]
        or contract.schema_sha256 != current["schema_sha256"]
        or contract.ontology_sha256 != current["semantic_ontology_sha256"]
    ):
        fail("run contract prompt/schema/ontology hashes differ from the frozen inputs")

    task_files = sorted(TASKS_DIR.glob("TASK_*/task.json"))
    if len(task_files) != EXPECTED_PASSAGES:
        fail(f"prepared task count is {len(task_files)}, expected {EXPECTED_PASSAGES}")
    tasks: dict[str, PreparedTask] = {}
    task_hashes: dict[str, str] = {}
    for path in task_files:
        task = PreparedTask.model_validate_json(path.read_text(encoding="utf-8"))
        if task.run_id != RUN_ID or task.execution_version != EXECUTION_VERSION:
            fail(f"task identity mismatch: {path}")
        if task.passage_id in tasks:
            fail(f"duplicate prepared task passage: {task.passage_id}")
        if task.evidence_packet_sha256 != expected_packet_hashes.get(task.passage_id):
            fail(f"packet hash mismatch for {task.passage_id}")
        tasks[task.passage_id] = task
        task_hashes[task.passage_id] = task.task_sha256
    if set(tasks) != set(selected_ids):
        fail("prepared task set differs from the frozen selection")

    integrity = Counter()
    validated_records: list[dict[str, Any]] = []
    attempt_records: list[dict[str, Any]] = []
    payloads: dict[str, Any] = {}
    all_ids: set[str] = set()
    for passage_id in selected_ids:
        task = tasks[passage_id]
        attempts_root = TASKS_DIR / task.task_id.replace(":", "_") / "attempts"
        attempt_dirs = sorted(path for path in attempts_root.glob("attempt_*") if path.is_dir())
        validated_dirs = [path for path in attempt_dirs if (path / "validated.json").exists()]
        for path in attempt_dirs:
            attempt_records.append(
                {
                    "passage_key": passage_id,
                    "attempt_id": path.name,
                    "terminal": (path / "validated.json").exists(),
                    "raw_response_sha256": sha256_file(path / "raw_response.json"),
                }
            )
        if len(validated_dirs) != 1:
            integrity["missing_or_ambiguous_terminal_response"] += 1
            fail(
                f"expected exactly one terminal validated response for {passage_id}, "
                f"found {len(validated_dirs)}"
            )
        directory = validated_dirs[0]
        raw = (directory / "raw_response.json").read_bytes()
        text = raw.decode("utf-8")
        for marker in CONTAMINATION_MARKERS:
            if marker.lower() in text.lower():
                integrity["heuristic_contamination"] += 1
                fail(f"contamination marker {marker!r} in the stored response for {passage_id}")
        response = ModelAuthoredResponse.model_validate_json(text)
        receipt = response.receipt
        if receipt.runtime != RUNTIME:
            integrity["provenance_mismatch"] += 1
            fail(f"receipt runtime mismatch for {passage_id}: {receipt.runtime!r}")
        if receipt.requested_model != MODEL or receipt.reported_model != MODEL:
            integrity["provenance_mismatch"] += 1
            fail(f"receipt model provenance mismatch for {passage_id}")
        if receipt.provider_build_metadata != "UNAVAILABLE":
            integrity["provenance_mismatch"] += 1
            fail(f"provider build metadata was invented for {passage_id}")
        if receipt.model_response_authored is not True:
            fail(f"response is not model-authored for {passage_id}")
        if receipt.attempt_id != directory.name:
            fail(f"validated attempt directory mismatch for {passage_id}")
        computed = response_payload_sha256(response)
        if receipt.response_sha256 != computed:
            integrity["receipt_failures"] += 1
            fail(f"response payload commitment mismatch for {passage_id}")

        packet = task.evidence_packet
        canonical = frozenset(mention.entity_key for mention in packet.mentions)
        errors = validate_receipt(receipt, task, contract, computed_response_sha256=computed)
        if errors:
            integrity["receipt_failures"] += 1
        packet_errors = [] if packet.input_sha256 == expected_packet_hashes[passage_id] else ["x"]
        if packet_errors:
            integrity["packet_hash_failures"] += 1
        evidence_errors = validate_evidence_anchors(response.semantic_output, packet)
        if evidence_errors:
            integrity["evidence_failures"] += 1
        binding_errors = validate_bindings(
            response.semantic_output, response.assertion_bindings, packet
        )
        if binding_errors:
            integrity["binding_failures"] += 1
        span_errors = [item for item in evidence_errors + binding_errors if "span" in item]
        if span_errors:
            integrity["span_failures"] += 1
        ontology_errors = validate_v3_payload(
            response.semantic_output, packet, canonical_entity_ids=canonical
        )
        if ontology_errors:
            integrity["ontology_type_failures"] += 1
        invariant_errors = validate_candidate_invariants(
            response.semantic_output, task, prompt_version=contract.prompt_version
        )
        combined = sorted(
            set(errors + evidence_errors + binding_errors + ontology_errors + invariant_errors)
        )
        if combined:
            fail(f"stored response no longer validates for {passage_id}: {'; '.join(combined)}")

        for candidate in [
            *(item.object for item in response.semantic_output.assertions),
            *response.semantic_output.ontology_gaps,
        ]:
            if (
                candidate.extraction_model != MODEL
                or candidate.prompt_version != "rigveda-semantic-extraction-v3.2"
            ):
                integrity["heuristic_contamination"] += 1
                fail(f"object provenance drift for {passage_id}")
        current_ids = [item.assertion_id for item in response.semantic_output.assertions]
        current_ids += [item.object.candidate_id for item in response.semantic_output.assertions]
        if all_ids.intersection(current_ids):
            fail(f"cross-passage duplicate assertion/object id at {passage_id}")
        all_ids.update(current_ids)

        stored = read_json(directory / "validated.json")
        if stored["raw_response_sha256"] != sha256_bytes(raw) or (
            stored["response_sha256"] != receipt.response_sha256
        ):
            fail(f"validated custody hash mismatch for {passage_id}")
        payloads[passage_id] = response
        validated_records.append(
            {
                "passage_key": passage_id,
                "task_id": task.task_id,
                "attempt_id": receipt.attempt_id,
                "raw_response_sha256": sha256_bytes(raw),
                "response_sha256": receipt.response_sha256,
                "validated_file_sha256": sha256_file(directory / "validated.json"),
                "assertions": len(response.semantic_output.assertions),
                "no_claim": bool(response.semantic_output.no_claim_reasons),
            }
        )

    if len(validated_records) != EXPECTED_PASSAGES:
        fail(f"final validated count is {len(validated_records)}, expected {EXPECTED_PASSAGES}")

    assignment_path = RUN_DIR / "claude_opus5_v3_2_448_agent_assignment.json"
    assignment = read_json(assignment_path)
    assertions_all = [
        item for response in payloads.values() for item in response.semantic_output.assertions
    ]
    predicate_counts = Counter(item.predicate.value for item in assertions_all)
    object_kind_counts = Counter(item.object.object_kind.value for item in assertions_all)
    events = [
        row
        for row in (RUN_DIR / "execution_events.jsonl").read_text(encoding="utf-8").splitlines()
        if row.strip()
    ]
    failed_events = [json.loads(row) for row in events]
    failed_imports = [row for row in failed_events if row.get("event") == "FAILED_IMPORT"]
    retry_categories = Counter(row.get("category", "UNKNOWN") for row in failed_imports)

    response_files = sorted((RUN_DIR / "responses").glob("TASK_*_attempt_*.json"))
    terminal_hashes = {row["raw_response_sha256"] for row in validated_records}
    preserved_failed = [path for path in response_files if sha256_file(path) not in terminal_hashes]
    seal = {
        "seal_version": "rigveda-semantic-claude-opus5-v3.2-448-output-seal-v1",
        "seal_status": "VALIDATED",
        "sealed_before_historical_comparison": True,
        "historical_sources_opened_before_seal": False,
        "run_id": RUN_ID,
        "provenance_bucket": PROVENANCE_BUCKET,
        "model_provenance_classification": MODEL_PROVENANCE_CLASSIFICATION,
        "execution_version": EXECUTION_VERSION,
        "execution_contract_version": "codex-direct-semantic-v1",
        "execution_contract": contract.model_dump(mode="json"),
        "model_requested": MODEL,
        "model_reported": MODEL,
        "runtime": RUNTIME.value,
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "independent_runtime_model_attestation": "UNAVAILABLE",
        "frozen_hashes": current,
        "selection_sha256": freeze["selection_sha256"],
        "selected_ids_sha256": freeze["selected_ids_sha256"],
        "run_selection_manifest_sha256": sha256_file(RUN_DIR / "run_selection_manifest.json"),
        "input_freeze_sha256": sha256_file(RUN_DIR / "input_freeze.json"),
        "agent_assignment_sha256": sha256_file(assignment_path),
        "agent_partition_sha256": assignment["partition_sha256"],
        "agent_group_counts": assignment["counts"],
        "packet_hashes": expected_packet_hashes,
        "prepared_task_hashes": task_hashes,
        "validated_response_hashes": validated_records,
        "attempt_histories": attempt_records,
        "execution_events_sha256": sha256_file(RUN_DIR / "execution_events.jsonl"),
        "preserved_failed_attempt_hashes": {
            path.name: sha256_file(path) for path in preserved_failed
        },
        "counts": {
            "expected_passages": EXPECTED_PASSAGES,
            "prepared_tasks": len(tasks),
            "final_validated_tasks": len(validated_records),
            "unique_final_passages": len({row["passage_key"] for row in validated_records}),
            "raw_response_receipts": len(attempt_records),
            "assertions": len(assertions_all),
            "no_claim_passages": sum(1 for row in validated_records if row["no_claim"]),
            "canonical_reference_assertions": sum(
                1
                for item in assertions_all
                if item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
            ),
            "failed_import_events_preserved": len(failed_imports),
            "retries_by_category": dict(sorted(retry_categories.items())),
            "authored_response_files": len(response_files),
            "preserved_failed_attempt_files": len(preserved_failed),
            "first_attempt_successes": sum(
                1 for row in validated_records if row["attempt_id"] == "attempt_001"
            ),
            "retried_to_success": sum(
                1 for row in validated_records if row["attempt_id"] != "attempt_001"
            ),
        },
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "object_kind_counts": dict(sorted(object_kind_counts.items())),
        "integrity": {
            "missing_final_tasks": EXPECTED_PASSAGES - len(validated_records),
            "duplicate_final_passages": len(validated_records)
            - len({row["passage_key"] for row in validated_records}),
            "receipt_failures": integrity["receipt_failures"],
            "packet_hash_failures": integrity["packet_hash_failures"],
            "evidence_failures": integrity["evidence_failures"],
            "span_failures": integrity["span_failures"],
            "binding_failures": integrity["binding_failures"],
            "ontology_type_failures": integrity["ontology_type_failures"],
            "heuristic_contamination": integrity["heuristic_contamination"],
            "provenance_mismatch": integrity["provenance_mismatch"],
            "cross_passage_duplicate_ids": 0,
        },
        "abandoned_luna_attempt": {
            "run_id": "vedagraph-rigveda-semantic-user-selected-luna-v3.2-448-new-v1",
            "classification": "ABORTED_BEFORE_IMPORT_EXECUTION_CAPACITY_EXHAUSTED",
            "imported_semantic_responses": 0,
            "partial_author_inputs_imported": 0,
            "preserved": True,
        },
        "model_self_agreement_is_accuracy": False,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "candidate_status": "CANDIDATE / NEEDS_REVIEW",
    }
    seal["seal_sha256"] = canonical_sha256(seal)
    seal_path.write_text(
        json.dumps(seal, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    file_hash = sha256_file(seal_path)
    (RUN_DIR / "output_seal.sha256").write_text(
        f"{file_hash}  output_seal.json\n", encoding="utf-8", newline="\n"
    )
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(
        json.dumps(
            {
                "seal_status": "VALIDATED",
                "seal_sha256": seal["seal_sha256"],
                "seal_file_sha256": file_hash,
                "final_validated_tasks": len(validated_records),
                "assertions": len(assertions_all),
                "integrity": seal["integrity"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
