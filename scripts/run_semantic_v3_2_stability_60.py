"""Execute the V3.2 two-run 60-mantra stability experiment via CODEX_DIRECT.

This script is pure orchestration: it prepares tasks, assembles a model-authored
intermediate JSON (semantic content only, no IDs, no offsets, no receipts) into the full
``ModelAuthoredResponse`` shape the CODEX_DIRECT contract requires, and imports it through
the existing validators. It authors no semantics itself: every predicate, object kind,
explicitness judgement and evidence quote in the intermediate JSON comes from the isolated
per-mantra agent context that produced it. This module only does the mechanical part the
docstring in ``codex_direct.py`` assigns to Python: locating a quoted span, minting a
deterministic candidate id, and assembling the receipt.

Usage (see __main__): one call prepares both runs' PreparedTasks; one call per task
imports one already-authored intermediate response file.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import (
    ExecutionStore,
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    canonical_sha256,
    prepare_task,
)
from vedagraph.semantic.v3_2 import (
    MODEL,
    REASONING,
    RUNTIME,
    STABILITY_RUN_A,
    STABILITY_RUN_B,
    build_stability_experiment,
)

V31_REGRESSION_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
RUN_ROOTS = {
    STABILITY_RUN_A: Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.2-stability-60-a"),
    STABILITY_RUN_B: Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.2-stability-60-b"),
}

CANONICAL_TARGET_PREDICATES = {"INVOKES", "PRAISES", "DESCRIBES"}


def load_v31_packets() -> dict[str, EvidencePacket]:
    """Reuse the sealed v3.1 packets unchanged; verify their hashes against the manifest."""
    manifest = json.loads((V31_REGRESSION_ROOT / "packet_build_manifest.json").read_text("utf-8"))
    packets: dict[str, EvidencePacket] = {}
    for line in (V31_REGRESSION_ROOT / "packets.jsonl").read_text("utf-8").splitlines():
        if not line.strip():
            continue
        packet = EvidencePacket.model_validate_json(line)
        packets[packet.passage_key] = packet
    expected = manifest["packet_hashes"]
    if set(packets) != set(expected):
        raise RuntimeError(f"packet set does not match manifest: {set(packets) ^ set(expected)}")
    mismatches = [key for key, packet in packets.items() if packet.input_sha256 != expected[key]]
    if mismatches:
        raise RuntimeError(f"packet hash mismatch against sealed v3.1 manifest: {mismatches}")
    return packets


def prepare_all() -> None:
    experiment = build_stability_experiment()
    diffs = experiment.contract_differences()
    if diffs:
        raise RuntimeError(f"STOP: run contracts differ beyond run id: {diffs}")
    packets = load_v31_packets()
    missing = [pid for pid in experiment.selection.passage_ids if pid not in packets]
    if missing:
        raise RuntimeError(f"STOP: missing packets for selection: {missing}")
    for contract in (experiment.run_a, experiment.run_b):
        store = ExecutionStore(RUN_ROOTS[contract.run_id] / "store")
        for passage_id in experiment.selection.passage_ids:
            task = prepare_task(packets[passage_id], contract)
            store.write_task(task)
    print(
        json.dumps(
            {
                "run_a": experiment.run_a.run_id,
                "run_b": experiment.run_b.run_id,
                "prepared_per_run": len(experiment.selection.passage_ids),
                "contract_differences": diffs,
            },
            indent=2,
        )
    )


def _find_span(text: str, quote: str, *, label: str) -> tuple[int, int]:
    if not quote:
        raise ValueError(f"{label}: empty quote")
    start = text.find(quote)
    if start < 0:
        raise ValueError(f"{label}: quote {quote!r} not found verbatim in translation text")
    if text.find(quote, start + 1) >= 0:
        raise ValueError(f"{label}: quote {quote!r} is not unique in translation text")
    return start, start + len(quote)


def _anchor(
    *, passage_key: str, translation_id: str, start: int, end: int, text: str
) -> dict[str, Any]:
    return {
        "source_passage_id": passage_key,
        "passage_ids": [passage_key],
        "token_ids": [],
        "other_evidence_ids": [],
        "translation_record_id": translation_id,
        "translation_span": {"start": start, "end": end},
    }


def assemble_semantic_output(
    intermediate: dict[str, Any], task: PreparedTask, contract: RunContract
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Turn model-authored semantic decisions into schema-shaped output plus bindings.

    ``intermediate`` carries only what a model can decide: predicate, object kind,
    explicitness, and the exact translation substrings that are the evidence. Candidate
    ids, assertion ids, and character offsets are minted here, mechanically, from those
    substrings -- never a predicate, an object kind, or a judgement call.
    """
    packet = task.evidence_packet
    translation = packet.translation
    text = translation.text if translation else ""
    translation_id = translation.translation_id if translation else ""
    mention_keys = {m.entity_key for m in packet.mentions}

    if intermediate.get("no_claim"):
        reasons = intermediate.get("no_claim_reasons") or []
        if not reasons:
            raise ValueError("no_claim requires at least one reason")
        return (
            {
                "mantra_id": packet.citation,
                "assertions": [],
                "no_claim_reasons": reasons,
                "ontology_gaps": [],
                "object_schema_version": "rigveda-semantic-object-v1",
                "prompt_version": "rigveda-semantic-extraction-v3",
            },
            [],
        )

    assertions: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(intermediate.get("assertions", []), start=1):
        predicate = raw["predicate"]
        obj = raw["object"]
        object_kind = obj["object_kind"]
        relation_start, relation_end = _find_span(
            text, raw["relation_quote"], label=f"assertion {ordinal} relation"
        )
        object_start, object_end = _find_span(
            text, obj["object_quote"], label=f"assertion {ordinal} object"
        )
        candidate_id = f"VG:SEMOBJ:{ordinal:020X}"
        assertion_id = f"{contract.run_id[-1].upper()}32A:{candidate_id}"

        canonical_entity_id = obj.get("canonical_entity_id")
        if object_kind == "CANONICAL_ENTITY_REF":
            if not canonical_entity_id or canonical_entity_id not in mention_keys:
                raise ValueError(
                    f"assertion {ordinal}: canonical_entity_id {canonical_entity_id!r} is not "
                    "a supplied lexical mention"
                )

        object_evidence = [
            _anchor(
                passage_key=packet.passage_key,
                translation_id=translation_id,
                start=object_start,
                end=object_end,
                text=text,
            )
        ]
        assertion_evidence = [
            _anchor(
                passage_key=packet.passage_key,
                translation_id=translation_id,
                start=relation_start,
                end=relation_end,
                text=text,
            )
        ]

        object_payload = {
            "candidate_id": candidate_id,
            "object_kind": object_kind,
            "display_label": obj["display_label"],
            "normalized_head": obj.get("normalized_head"),
            "canonical_entity_id": canonical_entity_id,
            "target_entity_id": obj.get("target_entity_id"),
            "beneficiary_entity_id": obj.get("beneficiary_entity_id"),
            "event": obj.get("event"),
            "ontology_gap_code": obj.get("ontology_gap_code"),
            "qualifiers": obj.get("qualifiers", []),
            "source_passage_id": packet.passage_key,
            "evidence": object_evidence,
            "extraction_model": contract.model_requested,
            "prompt_version": contract.prompt_version,
            "normalization_status": (
                "CANONICAL_REF"
                if object_kind == "CANONICAL_ENTITY_REF"
                else "ONTOLOGY_GAP"
                if object_kind == "ONTOLOGY_GAP_REF"
                else "NORMALIZED_CANDIDATE"
            ),
            "legacy_object_id": None,
            "schema_version": "rigveda-semantic-object-v1",
        }
        assertion_payload = {
            "assertion_id": assertion_id,
            "source_run_id": contract.run_id,
            "subject_id": packet.passage_key,
            "predicate": predicate,
            "object": object_payload,
            "evidence": assertion_evidence,
            "explicitness": raw["explicitness"],
            "inference_step": raw.get("inference_step"),
            "legacy_assertion_id": None,
            "schema_version": "rigveda-semantic-object-v1",
        }
        assertions.append(assertion_payload)

        anchors = [
            {
                "role": "RELATION",
                "translation_record_id": translation_id,
                "start": relation_start,
                "end": relation_end,
                "text": raw["relation_quote"],
                "entity_id": None,
            }
        ]
        if object_kind == "CANONICAL_ENTITY_REF" and predicate in CANONICAL_TARGET_PREDICATES:
            anchors.append(
                {
                    "role": "TARGET",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": obj["object_quote"],
                    "entity_id": canonical_entity_id,
                }
            )
        if predicate == "REQUESTS":
            anchors.append(
                {
                    "role": "OUTCOME",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": obj["object_quote"],
                    "entity_id": None,
                }
            )
        bindings.append({"assertion_id": assertion_id, "anchors": anchors})

    semantic_output = {
        "mantra_id": packet.citation,
        "assertions": assertions,
        "no_claim_reasons": [],
        "ontology_gaps": [],
        "object_schema_version": "rigveda-semantic-object-v1",
        "prompt_version": "rigveda-semantic-extraction-v3",
    }
    return semantic_output, bindings


def author_and_import(
    *,
    run_id: str,
    passage_id: str,
    intermediate_path: Path,
    attempt: int = 1,
) -> dict[str, Any]:
    experiment = build_stability_experiment()
    contract = experiment.run_a if run_id == experiment.run_a.run_id else experiment.run_b
    if contract.run_id != run_id:
        raise RuntimeError(f"unknown run id {run_id}")
    from vedagraph.semantic.codex_direct import task_id_for

    store = ExecutionStore(RUN_ROOTS[run_id] / "store")
    task = store.load_task(task_id_for(run_id, passage_id))

    intermediate = json.loads(intermediate_path.read_text("utf-8"))
    semantic_output, bindings = assemble_semantic_output(intermediate, task, contract)

    response_no_receipt = {"semantic_output": semantic_output, "assertion_bindings": bindings}
    response_sha256 = canonical_sha256(
        {
            "semantic_output": semantic_output,
            "assertion_bindings": bindings,
        }
    )
    attempt_id = f"attempt_{attempt:03d}"
    receipt = {
        "execution_contract_version": "codex-direct-semantic-v1",
        "execution_version": task.execution_version,
        "run_id": run_id,
        "task_id": task.task_id,
        "passage_id": passage_id,
        "requested_model": MODEL,
        "reported_model": MODEL,
        "runtime": RUNTIME,
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "task_sha256": task.task_sha256,
        "prompt_sha256": task.prompt_sha256,
        "schema_sha256": task.schema_sha256,
        "evidence_packet_sha256": task.evidence_packet_sha256,
        "response_sha256": response_sha256,
        "model_response_authored": True,
        "attempt_id": attempt_id,
        "authored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    response = ModelAuthoredResponse.model_validate({"receipt": receipt, **response_no_receipt})
    out_dir = RUN_ROOTS[run_id] / "responses"
    out_dir.mkdir(parents=True, exist_ok=True)
    response_path = out_dir / f"{task.task_id.replace(':', '_')}_{attempt_id}.json"
    response_path.write_text(
        json.dumps(response.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    validated = store.import_response(response_path, contract)
    return {
        "passage_id": passage_id,
        "task_id": task.task_id,
        "attempt_id": attempt_id,
        "assertions": len(validated.payload.assertions),
        "no_claim": bool(validated.payload.no_claim_reasons),
    }


if __name__ == "__main__":
    if sys.argv[1:2] == ["prepare"]:
        prepare_all()
    elif sys.argv[1:2] == ["import"]:
        _, _, run_id, passage_id, path, *rest = sys.argv
        attempt = int(rest[0]) if rest else 1
        result = author_and_import(
            run_id=run_id, passage_id=passage_id, intermediate_path=Path(path), attempt=attempt
        )
        print(json.dumps(result, indent=2))
    else:
        raise SystemExit(
            "usage: prepare | import <run_id> <passage_id> <intermediate.json> [attempt]"
        )
