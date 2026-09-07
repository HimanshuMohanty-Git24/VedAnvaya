"""Coordinator operations for the Claude Opus 5 multi-agent V3.2 448 candidate run.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.
ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.

Single writer. ``prepare``, ``import`` and ``import-all`` mutate the run store and are the
coordinator's alone. ``render`` and ``check`` write nothing and are what an author agent
runs: ``render`` prints the evidence-only view of one packet, ``check`` says whether an
authored intermediate would import, without importing it.

Usage:
    python scripts/claude448.py prepare
    python scripts/claude448.py partition --groups 6
    python scripts/claude448.py render VG:RV:SAK:M01:S005:V003
    python scripts/claude448.py check  VG:RV:SAK:M01:S005:V003 path/to/intermediate.json
    python scripts/claude448.py import VG:RV:SAK:M01:S005:V003 path/to/intermediate.json
    python scripts/claude448.py import-all [--only-group A]
    python scripts/claude448.py status
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from vedagraph.models.normalization import SemanticExtractionV3  # noqa: E402
from vedagraph.models.semantic import EvidencePacket  # noqa: E402
from vedagraph.semantic.claude_opus5_v3_2 import (  # noqa: E402
    ABANDONED_AUTHOR_INPUT_CLASSIFICATION,
    ABANDONED_ROOT,
    ABANDONED_RUN_CLASSIFICATION,
    ABANDONED_RUN_ID,
    BATCH_SIZE,
    EXECUTION_VERSION,
    EXPECTED_PASSAGES,
    MODEL,
    MODEL_PROVENANCE_CLASSIFICATION,
    PARTITION_RULE,
    PROVENANCE_BUCKET,
    REASONING,
    RUN_ID,
    RUN_ROOT,
    RUNTIME,
    SELECTION_PATH,
    AuthorInputError,
    assemble,
    author_view,
    contract,
    frozen_hashes,
    load_intermediate,
    partition,
    partition_hash,
)
from vedagraph.semantic.codex_direct import (  # noqa: E402
    AssertionBinding,
    ExecutionStore,
    ModelAuthoredResponse,
    canonical_sha256,
    file_sha256,
    prepare_task,
    response_payload_sha256,
    task_id_for,
    validate_bindings,
    validate_candidate_invariants,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors  # noqa: E402
from vedagraph.semantic.v3 import validate_v3_payload  # noqa: E402

RUN_DIR = ROOT / RUN_ROOT
STORE_DIR = RUN_DIR / "store"
AUTHOR_DIR = RUN_DIR / "author_inputs"
RESPONSE_DIR = RUN_DIR / "responses"
EVENTS_PATH = RUN_DIR / "execution_events.jsonl"


def safe(passage_id: str) -> str:
    return passage_id.replace(":", "_")


def selection_ids() -> list[str]:
    document = yaml.safe_load((ROOT / SELECTION_PATH).read_text(encoding="utf-8"))
    if document.get("selection_policy") != "SET_DIFFERENCE_ONLY":
        raise SystemExit("selection policy is not SET_DIFFERENCE_ONLY")
    ids = [str(row["passage_key"]) for row in document["mantras"]]
    if len(ids) != EXPECTED_PASSAGES or len(set(ids)) != EXPECTED_PASSAGES:
        raise SystemExit(f"selection is not {EXPECTED_PASSAGES} unique ids")
    if canonical_sha256(sorted(ids)) != document["result_ids_sha256"]:
        raise SystemExit("selection commitment mismatch")
    return sorted(ids)


def reused_packets() -> dict[str, EvidencePacket]:
    """The interrupted attempt's packets, reused only after every hash re-verifies.

    Reads ``packets.jsonl`` and ``packet_build_manifest.json`` from the abandoned run and
    nothing else in it. Its ``author_inputs`` directory is never opened.
    """
    root = ROOT / ABANDONED_ROOT
    manifest = json.loads((root / "packet_build_manifest.json").read_text(encoding="utf-8"))
    expected = dict(manifest["packet_hashes"])
    packets: dict[str, EvidencePacket] = {}
    for line in (root / "packets.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        packet = EvidencePacket.model_validate_json(line)
        if packet.passage_key in packets:
            raise SystemExit(f"duplicate reused packet: {packet.passage_key}")
        packets[packet.passage_key] = packet
    if set(packets) != set(expected):
        raise SystemExit("reused packet set does not match its manifest")
    bad = sorted(key for key, packet in packets.items() if packet.input_sha256 != expected[key])
    if bad:
        raise SystemExit(f"reused packet hash mismatch: {bad[:5]}")
    return packets


def event(kind: str, **fields: Any) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"event": kind, "at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), **fields}
    with EVENTS_PATH.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


# --------------------------------------------------------------------------------------


def cmd_prepare(_: argparse.Namespace) -> dict[str, Any]:
    ids = selection_ids()
    packets = reused_packets()
    missing = sorted(set(ids) - set(packets))
    if missing:
        raise SystemExit(f"no reusable packet for {len(missing)} passages: {missing[:5]}")
    run_contract = contract(ROOT)
    store = ExecutionStore(STORE_DIR)
    for passage_id in ids:
        store.write_task(prepare_task(packets[passage_id], run_contract))
    write_json(STORE_DIR / "run_contract.json", run_contract.model_dump(mode="json"))

    packet_hashes = {key: packets[key].input_sha256 for key in ids}
    batches = [
        {
            "batch": number,
            "batch_size": len(ids[offset : offset + BATCH_SIZE]),
            "passage_keys": ids[offset : offset + BATCH_SIZE],
        }
        for number, offset in enumerate(range(0, len(ids), BATCH_SIZE), start=1)
    ]
    selection_manifest = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-run-selection-v1",
        "run_id": RUN_ID,
        "provenance_bucket": PROVENANCE_BUCKET,
        "model_provenance_classification": MODEL_PROVENANCE_CLASSIFICATION,
        "execution_version": EXECUTION_VERSION,
        "execution_contract_version": "codex-direct-semantic-v1",
        "model_requested": MODEL,
        "reasoning_requested": REASONING,
        "runtime": RUNTIME.value,
        "provider_build_metadata": "UNAVAILABLE",
        "independent_runtime_model_attestation": "UNAVAILABLE",
        "historical_selection_path": SELECTION_PATH.as_posix(),
        "historical_selection_sha256": file_sha256(ROOT / SELECTION_PATH),
        "historical_selection_unmodified": True,
        "selected_ids": ids,
        "selected_ids_sha256": canonical_sha256(sorted(ids)),
        "selected_count": len(ids),
        "packet_source_run_id": ABANDONED_RUN_ID,
        "packet_source_classification": ABANDONED_RUN_CLASSIFICATION,
        "packet_reuse_scope": "EVIDENCE_PACKET_PREPARATION_ONLY",
        "abandoned_author_inputs_classification": ABANDONED_AUTHOR_INPUT_CLASSIFICATION,
        "abandoned_author_inputs_imported": 0,
        "abandoned_author_inputs_read_by_authors": False,
        "packet_hashes": packet_hashes,
        "packet_count": len(packet_hashes),
        "duplicate_packet_count": 0,
        "missing_packet_count": 0,
        "semantic_outputs_in_packets": False,
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "batches": batches,
        "frozen_hashes": frozen_hashes(ROOT),
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened_before_seal": False,
        "model_self_agreement_is_accuracy": False,
    }
    write_json(RUN_DIR / "run_selection_manifest.json", selection_manifest)
    write_json(
        RUN_DIR / "input_freeze.json",
        {
            "freeze_version": "rigveda-semantic-claude-opus5-v3.2-448-input-freeze-v1",
            "run_id": RUN_ID,
            "provenance_bucket": PROVENANCE_BUCKET,
            "selected_ids": ids,
            "selected_ids_sha256": canonical_sha256(sorted(ids)),
            "selection_sha256": file_sha256(ROOT / SELECTION_PATH),
            "packet_hashes": packet_hashes,
            "frozen_hashes": frozen_hashes(ROOT),
            "human_gold_status": "UNANNOTATED",
            "unlocked_predicates": [],
            "canonical_promotion": False,
            "historical_sources_opened_before_seal": False,
        },
    )
    event("PREPARED", tasks=len(ids), run_id=RUN_ID)
    return {
        "run_id": RUN_ID,
        "prepared_tasks": len(ids),
        "batches": len(batches),
        "batch_sizes": [row["batch_size"] for row in batches],
        "selected_ids_sha256": selection_manifest["selected_ids_sha256"],
        "runtime": RUNTIME.value,
        "model_requested": MODEL,
    }


def cmd_partition(args: argparse.Namespace) -> dict[str, Any]:
    ids = selection_ids()
    groups = partition(ids, args.groups)
    assignment = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-agent-assignment-v1",
        "run_id": RUN_ID,
        "provenance_bucket": PROVENANCE_BUCKET,
        "partition_rule": PARTITION_RULE,
        "group_count": args.groups,
        "total_passages": len(ids),
        "contains_semantic_answers": False,
        "groups": {
            name: {"group": name, "count": len(members), "passage_ids": members}
            for name, members in sorted(groups.items())
        },
        "counts": {name: len(members) for name, members in sorted(groups.items())},
        "partition_sha256": partition_hash(groups),
    }
    write_json(RUN_DIR / "claude_opus5_v3_2_448_agent_assignment.json", assignment)
    write_json(
        ROOT / "docs/manifests/rigveda_semantic_claude_opus5_v3_2_agent_assignment.json",
        assignment,
    )
    return {
        "groups": assignment["counts"],
        "partition_sha256": assignment["partition_sha256"],
        "rule": PARTITION_RULE,
    }


def _task(passage_id: str) -> Any:
    return ExecutionStore(STORE_DIR).load_task(task_id_for(RUN_ID, passage_id))


def cmd_render(args: argparse.Namespace) -> dict[str, Any]:
    return author_view(_task(args.passage_id).evidence_packet)


def cmd_authored(args: argparse.Namespace) -> dict[str, Any]:
    """The terminal validated output for one passage. Read-only; for post-seal review."""
    task = _task(args.passage_id)
    directory = STORE_DIR / "tasks" / safe(task.task_id) / "attempts"
    terminal = [
        item for item in sorted(directory.glob("attempt_*")) if (item / "validated.json").exists()
    ]
    if len(terminal) != 1:
        raise SystemExit(f"{args.passage_id} has {len(terminal)} terminal responses")
    response = ModelAuthoredResponse.model_validate_json(
        (terminal[0] / "raw_response.json").read_text(encoding="utf-8")
    )
    packet = task.evidence_packet
    text = (packet.translation.text or "") if packet.translation else ""
    bindings = {item.assertion_id: item for item in response.assertion_bindings}
    return {
        "passage_id": args.passage_id,
        "citation": task.citation,
        "no_claim_reasons": list(response.semantic_output.no_claim_reasons),
        "assertions": [
            {
                "assertion_id": item.assertion_id,
                "predicate": item.predicate.value,
                "explicitness": item.explicitness.value,
                "inference_step": item.inference_step,
                "object_kind": item.object.object_kind.value,
                "display_label": item.object.display_label,
                "normalized_head": item.object.normalized_head,
                "canonical_entity_id": item.object.canonical_entity_id,
                "ontology_gap_code": (
                    item.object.ontology_gap_code.value if item.object.ontology_gap_code else None
                ),
                "event": item.object.event.model_dump(mode="json") if item.object.event else None,
                "qualifiers": list(item.object.qualifiers),
                "anchors": [
                    {"role": anchor.role.value, "text": anchor.text, "entity_id": anchor.entity_id}
                    for anchor in (
                        bindings[item.assertion_id].anchors if item.assertion_id in bindings else []
                    )
                ],
            }
            for item in response.semantic_output.assertions
        ],
        "translation_text": text,
    }


def _validation_errors(
    intermediate: dict[str, Any], passage_id: str
) -> tuple[list[str], dict[str, Any] | None]:
    run_contract = contract(ROOT)
    task = _task(passage_id)
    try:
        semantic_output, bindings = assemble(intermediate, task, run_contract)
    except AuthorInputError as exc:
        return [f"FORMAT: {exc}"], None
    try:
        body = normalised_body(semantic_output, bindings)
    except ValueError as exc:
        return [f"SCHEMA: {exc}"], None
    receipt = {
        "execution_contract_version": "codex-direct-semantic-v1",
        "execution_version": task.execution_version,
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "passage_id": passage_id,
        "requested_model": MODEL,
        "reported_model": MODEL,
        "runtime": RUNTIME.value,
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "task_sha256": task.task_sha256,
        "prompt_sha256": task.prompt_sha256,
        "schema_sha256": task.schema_sha256,
        "evidence_packet_sha256": task.evidence_packet_sha256,
        "response_sha256": canonical_sha256(body),
        "model_response_authored": True,
        "attempt_id": "attempt_001",
        "authored_at": "2026-01-01T00:00:00Z",
    }
    try:
        response = ModelAuthoredResponse.model_validate({"receipt": receipt, **body})
    except ValueError as exc:
        return [f"SCHEMA: {exc}"], None
    packet = task.evidence_packet
    canonical = frozenset(mention.entity_key for mention in packet.mentions)
    errors = validate_receipt(
        response.receipt,
        task,
        run_contract,
        computed_response_sha256=response_payload_sha256(response),
    )
    errors += validate_candidate_invariants(
        response.semantic_output, task, prompt_version=run_contract.prompt_version
    )
    errors += validate_v3_payload(response.semantic_output, packet, canonical_entity_ids=canonical)
    errors += validate_evidence_anchors(response.semantic_output, packet)
    errors += validate_bindings(response.semantic_output, response.assertion_bindings, packet)
    return sorted(set(errors)), body


def cmd_check(args: argparse.Namespace) -> dict[str, Any]:
    intermediate = load_intermediate(args.intermediate)
    errors, body = _validation_errors(intermediate, args.passage_id)
    return {
        "passage_id": args.passage_id,
        "status": "OK" if not errors else "REJECTED",
        "errors": errors,
        "assertions": 0 if body is None else len(body["semantic_output"]["assertions"]),
        "no_claim": bool(body and body["semantic_output"]["no_claim_reasons"]),
    }


def normalised_body(
    semantic_output: dict[str, Any], bindings: list[dict[str, Any]]
) -> dict[str, Any]:
    """The response payload exactly as the validator will recompute it.

    The receipt commits to ``response_sha256``, and ``import_response`` recomputes that
    hash from the *parsed* models. Hashing the assembler's raw dicts instead lets the two
    disagree whenever Pydantic fills a defaulted field the author omitted -- an ``event``
    written as ``{"action_head": "..."}`` gains four default keys on validation, and the
    receipt then commits to bytes the validator never sees. Normalising here makes the two
    hashes equal by construction rather than by luck.
    """
    return {
        "semantic_output": SemanticExtractionV3.model_validate(semantic_output).model_dump(
            mode="json"
        ),
        "assertion_bindings": [
            AssertionBinding.model_validate(item).model_dump(mode="json") for item in bindings
        ],
    }


def classify_failure(message: str) -> str:
    """Bucket a validator refusal into the retry categories the run reports.

    Order matters: a provenance mismatch and a binding failure can both mention a task,
    and provenance is the more serious diagnosis, so it is tested first.
    """
    text = message.lower()
    if any(
        marker in text
        for marker in ("runtime", "requested model", "reported model", "run id", "prompt version")
    ):
        return "PROVENANCE_RETRY"
    if "packet" in text or "task hash" in text or "receipt" in text:
        return "RECEIPT_RETRY"
    if "binding" in text or "anchor" in text:
        return "BINDING_RETRY"
    if "span" in text or "offset" in text:
        return "SPAN_RETRY"
    if "ontology" in text or "type boundary" in text or "predicate" in text:
        return "ONTOLOGY_TYPE_RETRY"
    if "evidence" in text or "fabricated" in text:
        return "EVIDENCE_RETRY"
    return "SEMANTIC_RETRY"


def _failed(passage_id: str, category: str, error: str) -> dict[str, Any]:
    return {"passage_id": passage_id, "status": "FAILED", "category": category, "error": error}


def _import_one(passage_id: str, path: Path, attempt: int) -> dict[str, Any]:
    run_contract = contract(ROOT)
    store = ExecutionStore(STORE_DIR)
    task = store.load_task(task_id_for(RUN_ID, passage_id))
    intermediate = load_intermediate(path)
    try:
        semantic_output, bindings = assemble(intermediate, task, run_contract)
    except AuthorInputError as exc:
        event("FAILED_IMPORT", passage_id=passage_id, category="FORMAT_RETRY", detail=str(exc))
        return _failed(passage_id, "FORMAT_RETRY", str(exc))
    try:
        body = normalised_body(semantic_output, bindings)
    except ValueError as exc:
        event("FAILED_IMPORT", passage_id=passage_id, category="SCHEMA_RETRY", detail=str(exc))
        return _failed(passage_id, "SCHEMA_RETRY", str(exc))
    attempt_id = f"attempt_{attempt:03d}"
    receipt = {
        "execution_contract_version": "codex-direct-semantic-v1",
        "execution_version": task.execution_version,
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "passage_id": passage_id,
        "requested_model": MODEL,
        "reported_model": MODEL,
        "runtime": RUNTIME.value,
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "task_sha256": task.task_sha256,
        "prompt_sha256": task.prompt_sha256,
        "schema_sha256": task.schema_sha256,
        "evidence_packet_sha256": task.evidence_packet_sha256,
        "response_sha256": canonical_sha256(body),
        "model_response_authored": True,
        "attempt_id": attempt_id,
        "authored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    try:
        response = ModelAuthoredResponse.model_validate({"receipt": receipt, **body})
    except ValueError as exc:
        event("FAILED_IMPORT", passage_id=passage_id, category="SCHEMA_RETRY", detail=str(exc))
        return _failed(passage_id, "SCHEMA_RETRY", str(exc))
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    response_path = RESPONSE_DIR / f"{safe(task.task_id)}_{attempt_id}.json"
    payload = (
        json.dumps(response.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    )
    if response_path.exists() and response_path.read_text(encoding="utf-8") != payload:
        return {
            "passage_id": passage_id,
            "status": "FAILED",
            "category": "CUSTODY",
            "error": f"{attempt_id} already holds different content; use a new attempt",
        }
    response_path.write_text(payload, encoding="utf-8", newline="\n")
    try:
        validated = ExecutionStore(STORE_DIR).import_response(response_path, run_contract)
    except ValueError as exc:
        category = classify_failure(str(exc))
        event("FAILED_IMPORT", passage_id=passage_id, category=category, detail=str(exc))
        return _failed(passage_id, category, str(exc))
    event(
        "IMPORTED",
        passage_id=passage_id,
        attempt_id=attempt_id,
        assertions=len(validated.payload.assertions),
    )
    return {
        "passage_id": passage_id,
        "status": "IMPORTED",
        "attempt_id": attempt_id,
        "assertions": len(validated.payload.assertions),
        "no_claim": bool(validated.payload.no_claim_reasons),
    }


def cmd_import(args: argparse.Namespace) -> dict[str, Any]:
    return _import_one(args.passage_id, args.intermediate, args.attempt)


def imported_passages() -> set[str]:
    """Passages that already hold a terminal validated response."""
    return {
        json.loads(path.read_text(encoding="utf-8"))["passage_id"]
        for path in (STORE_DIR / "tasks").glob("TASK_*/attempts/*/validated.json")
    }


def author_files(group: str | None) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    if not AUTHOR_DIR.exists():
        return rows
    for path in sorted(AUTHOR_DIR.glob("*/*.json")):
        if group and path.parent.name != group:
            continue
        rows.append((path.stem.replace("_", ":"), path))
    return rows


def cmd_import_all(args: argparse.Namespace) -> dict[str, Any]:
    """Import every settled author file that has no terminal response yet.

    ``--settled-seconds`` skips files still being written by a running author context, so
    continuous import never turns a half-written file into a spurious FORMAT_RETRY.
    """
    done = imported_passages()
    now = time.time()
    results: list[dict[str, Any]] = []
    skipped_unsettled = 0
    for passage_id, path in author_files(args.only_group):
        # A passage that already holds a terminal validated response is never re-imported:
        # a second one would leave two terminal responses and the seal refuses that. A
        # genuine retry goes through the single-passage `import` command with a new
        # attempt id, after the failed attempt has been preserved.
        if passage_id in done:
            continue
        if args.settled_seconds and now - path.stat().st_mtime < args.settled_seconds:
            skipped_unsettled += 1
            continue
        results.append(_import_one(passage_id, path, args.attempt))
    failures = [row for row in results if row["status"] != "IMPORTED"]
    return {
        "attempted": len(results),
        "imported": len(results) - len(failures),
        "failed": len(failures),
        "skipped_unsettled": skipped_unsettled,
        "failures_by_category": dict(sorted(Counter(row["category"] for row in failures).items())),
        "failures": failures[:40],
        "total_imported_now": len(imported_passages()),
    }


def cmd_status(_: argparse.Namespace) -> dict[str, Any]:
    ids = set(selection_ids())
    done = imported_passages()
    return {
        "run_id": RUN_ID,
        "expected": len(ids),
        "prepared_tasks": len(list((STORE_DIR / "tasks").glob("TASK_*/task.json"))),
        "authored_files": len(author_files(None)),
        "imported": len(done),
        "missing": len(ids - done),
        "missing_sample": sorted(ids - done)[:10],
        "raw_response_files": len(list(RESPONSE_DIR.glob("TASK_*_attempt_*.json")))
        if RESPONSE_DIR.exists()
        else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare").set_defaults(func=cmd_prepare)
    partition_parser = sub.add_parser("partition")
    partition_parser.add_argument("--groups", type=int, default=6)
    partition_parser.set_defaults(func=cmd_partition)
    render_parser = sub.add_parser("render")
    render_parser.add_argument("passage_id")
    render_parser.set_defaults(func=cmd_render)
    authored_parser = sub.add_parser("authored")
    authored_parser.add_argument("passage_id")
    authored_parser.set_defaults(func=cmd_authored)
    check_parser = sub.add_parser("check")
    check_parser.add_argument("passage_id")
    check_parser.add_argument("intermediate", type=Path)
    check_parser.set_defaults(func=cmd_check)
    import_parser = sub.add_parser("import")
    import_parser.add_argument("passage_id")
    import_parser.add_argument("intermediate", type=Path)
    import_parser.add_argument("--attempt", type=int, default=1)
    import_parser.set_defaults(func=cmd_import)
    all_parser = sub.add_parser("import-all")
    all_parser.add_argument("--only-group", default=None)
    all_parser.add_argument("--attempt", type=int, default=1)
    all_parser.add_argument("--settled-seconds", type=float, default=0.0)
    all_parser.set_defaults(func=cmd_import_all)
    sub.add_parser("status").set_defaults(func=cmd_status)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(json.dumps(args.func(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
