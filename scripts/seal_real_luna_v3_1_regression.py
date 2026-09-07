"""Audit and seal the bounded real-Luna regression before historical comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.codex_direct import (
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    canonical_sha256,
    file_sha256,
    response_payload_sha256,
)

CONFIG = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
STORE = ROOT / "store"
SEAL = Path("docs/manifests/vedagraph_rigveda_semantic_luna_v3_1_regression_output_seal.json")
MANIFEST = Path("docs/manifests/vedagraph-rigveda-semantic-luna-v3.1-regression.json")
RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-regression"

FROZEN_FILES = {
    "prompt_sha256": Path("prompts/semantic_extraction_v3.md"),
    "schema_sha256": Path("schemas/semantic_extraction_v3.schema.json"),
    "semantic_ontology_sha256": Path("src/vedagraph/semantic/ontology.py"),
    "object_ontology_sha256": Path("src/vedagraph/semantic/object_ontology.py"),
    "evidence_validator_sha256": Path("src/vedagraph/semantic/evidence.py"),
    "span_validator_sha256": Path("src/vedagraph/semantic/spans.py"),
    "execution_contract_sha256": Path("src/vedagraph/semantic/codex_direct.py"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_immutable(path: Path, value: object) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite an existing sealed file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)


def selection_hash(document: dict[str, Any]) -> str:
    ids = sorted(str(row["passage_key"]) for row in document["mantras"])
    return sha256_bytes(
        json.dumps(
            {"policy": document["selection_policy_version"], "ids": ids},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or len(config.get("mantras", [])) != 60:
        raise RuntimeError("STOP: the sealed run must contain exactly 60 configured mantras")
    ids = [str(row["passage_key"]) for row in config["mantras"]]
    if len(set(ids)) != 60 or selection_hash(config) != config.get("selection_hash"):
        raise RuntimeError("STOP: selection identity is not frozen")

    contract = RunContract.model_validate_json(
        (STORE / "run_contract.json").read_text(encoding="utf-8")
    )
    if (
        contract.run_id != RUN_ID
        or contract.model_requested != "gpt-5.6-luna"
        or contract.reasoning_requested != "high"
    ):
        raise RuntimeError("STOP: run contract identity mismatch")

    packet_manifest = json.loads((ROOT / "packet_build_manifest.json").read_text(encoding="utf-8"))
    if (
        packet_manifest["packet_count"] != 60
        or packet_manifest["duplicates"]
        or packet_manifest["missing"]
    ):
        raise RuntimeError("STOP: packet manifest is incomplete")
    packet_hashes = dict(packet_manifest["packet_hashes"])
    if set(packet_hashes) != set(ids):
        raise RuntimeError("STOP: packet IDs do not match the frozen selection")

    task_dirs = sorted((STORE / "tasks").iterdir())
    if len(task_dirs) != 60:
        raise RuntimeError(f"STOP: expected 60 prepared task directories, found {len(task_dirs)}")

    task_hashes: dict[str, str] = {}
    receipt_hashes: dict[str, dict[str, str]] = {}
    validated_hashes: dict[str, str] = {}
    attempt_histories: list[dict[str, str]] = []
    reported_models: set[str] = set()
    provider_metadata: set[str] = set()
    failures: list[str] = []

    for task_dir in task_dirs:
        task_path = task_dir / "task.json"
        task = PreparedTask.model_validate_json(task_path.read_text(encoding="utf-8"))
        if task.run_id != RUN_ID or task.passage_id not in ids:
            failures.append(f"unprepared or foreign task: {task.task_id}")
        if task.passage_id in task_hashes:
            failures.append(f"duplicate task passage: {task.passage_id}")
        task_hashes[task.passage_id] = task.task_sha256
        attempts_dir = task_dir / "attempts"
        attempts = sorted(attempts_dir.iterdir()) if attempts_dir.exists() else []
        if not attempts:
            failures.append(f"missing attempt: {task.task_id}")
        for attempt_dir in attempts:
            raw_path = attempt_dir / "raw_response.json"
            validated_path = attempt_dir / "validated.json"
            if not raw_path.exists() or not validated_path.exists():
                failures.append(f"incomplete attempt: {task.task_id}/{attempt_dir.name}")
                continue
            raw = raw_path.read_bytes()
            response = ModelAuthoredResponse.model_validate_json(raw.decode("utf-8"))
            receipt = response.receipt
            if receipt.task_id != task.task_id or receipt.attempt_id != attempt_dir.name:
                failures.append(f"receipt identity mismatch: {task.task_id}/{attempt_dir.name}")
            if (
                receipt.requested_model != "gpt-5.6-luna"
                or receipt.reported_model != "gpt-5.6-luna"
            ):
                failures.append(f"wrong model receipt: {task.task_id}/{attempt_dir.name}")
            if receipt.runtime != "CODEX_DIRECT" or receipt.reasoning != "high":
                failures.append(
                    f"runtime/reasoning receipt mismatch: {task.task_id}/{attempt_dir.name}"
                )
            if receipt.model_response_authored is not True:
                failures.append(f"non-authored receipt: {task.task_id}/{attempt_dir.name}")
            if response_payload_sha256(response) != receipt.response_sha256:
                failures.append(f"response commitment mismatch: {task.task_id}/{attempt_dir.name}")
            validated = json.loads(validated_path.read_text(encoding="utf-8"))
            if validated.get("raw_response_sha256") != sha256_bytes(raw):
                failures.append(f"raw receipt hash mismatch: {task.task_id}/{attempt_dir.name}")
            if validated.get("response_sha256") != receipt.response_sha256:
                failures.append(
                    f"validated response hash mismatch: {task.task_id}/{attempt_dir.name}"
                )
            key = f"{task.task_id}/{attempt_dir.name}"
            receipt_hashes[key] = {
                "raw_response_sha256": sha256_bytes(raw),
                "response_payload_sha256": receipt.response_sha256,
            }
            validated_hashes[key] = file_sha256(validated_path)
            attempt_histories.append(
                {
                    "task_id": task.task_id,
                    "passage_id": task.passage_id,
                    "attempt_id": receipt.attempt_id,
                    "raw_response_sha256": sha256_bytes(raw),
                    "validated_json_sha256": file_sha256(validated_path),
                }
            )
            reported_models.add(receipt.reported_model)
            provider_metadata.add(receipt.provider_build_metadata)

    if set(task_hashes) != set(ids):
        failures.append("prepared task passage set differs from selection")
    if len(receipt_hashes) != 60 or len(validated_hashes) != 60:
        failures.append("response receipt or validated response count is not 60")
    if failures:
        raise RuntimeError(
            "STOP: pre-seal integrity failures: " + " | ".join(sorted(set(failures)))
        )

    repair = json.loads(
        Path(
            "docs/manifests/vedagraph_rigveda_semantic_luna_v3_1_regression_config_repair.json"
        ).read_text(encoding="utf-8")
    )
    seal = {
        "seal_version": "vedagraph-real-luna-regression-seal-v1",
        "run_id": RUN_ID,
        "execution_contract_version": contract.execution_contract_version,
        "execution_version": contract.execution_version,
        "requested_model": contract.model_requested,
        "reported_models": sorted(reported_models),
        "runtime": "CODEX_DIRECT",
        "reasoning": contract.reasoning_requested,
        "provider_build_metadata": sorted(provider_metadata),
        "selection": {
            "ids": sorted(ids),
            "canonical_selection_sha256": config["selection_hash"],
            "yaml_sha256": file_sha256(CONFIG),
        },
        "packet_hashes": packet_hashes,
        "task_hashes": task_hashes,
        "attempt_receipt_hashes": receipt_hashes,
        "validated_response_hashes": validated_hashes,
        "attempt_histories": sorted(
            attempt_histories, key=lambda item: (item["task_id"], item["attempt_id"])
        ),
        "frozen_hashes": {name: file_sha256(path) for name, path in FROZEN_FILES.items()},
        "repair_provenance": repair,
        "counts": {
            "tasks_prepared": 60,
            "tasks_attempted": 60,
            "attempts": 60,
            "retries": 0,
            "imported": 60,
            "refused": 0,
        },
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened": False,
        "heuristic_baseline_in_codex_direct_custody": False,
    }
    seal["seal_sha256"] = canonical_sha256(seal)
    write_immutable(SEAL, seal)

    manifest = {
        "manifest_id": RUN_ID,
        "manifest_version": "vedagraph-real-luna-regression-manifest-v1",
        "output_seal": SEAL.as_posix(),
        "output_seal_sha256": file_sha256(SEAL),
        "run_id": RUN_ID,
        "execution_contract_version": contract.execution_contract_version,
        "model": contract.model_requested,
        "reported_models": sorted(reported_models),
        "reasoning": contract.reasoning_requested,
        "runtime": "CODEX_DIRECT",
        "selection_hash": config["selection_hash"],
        "yaml_sha256": file_sha256(CONFIG),
        "packet_hashes": packet_hashes,
        "task_hashes": task_hashes,
        "raw_response_receipt_hashes": receipt_hashes,
        "validated_response_hashes": validated_hashes,
        "attempt_histories": seal["attempt_histories"],
        "frozen_hashes": seal["frozen_hashes"],
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened": False,
        "serialization_repair_before_execution": True,
        "seal_sha256": seal["seal_sha256"],
    }
    write_immutable(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "seal": SEAL.as_posix(),
                "manifest": MANIFEST.as_posix(),
                "seal_sha256": seal["seal_sha256"],
                "integrity_failures": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
