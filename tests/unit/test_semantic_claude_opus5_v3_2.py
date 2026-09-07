"""The Claude Opus 5 V3.2 run: provenance separation, partition, and mechanical assembly.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.

These tests defend three properties:

* a Claude-authored candidate can never be stored under Luna provenance,
* the runtime generalization did not weaken any historical validation, and
* the assembler authors nothing -- it refuses bad author input rather than repairing it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic import claude_opus5_v3_2 as claude
from vedagraph.semantic.codex_direct import (
    ExecutionRuntime,
    ModelExecutionReceipt,
    RunContract,
    prepare_task,
    task_id_for,
    validate_receipt,
)

ABANDONED = Path("data/semantic/vedagraph-rigveda-semantic-user-selected-luna-v3.2-448-new-v1")
RUN_DIR = Path("data/semantic/vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1")


@pytest.fixture(scope="module")
def packet() -> EvidencePacket:
    line = (ABANDONED / "packets.jsonl").read_text(encoding="utf-8").splitlines()[0]
    return EvidencePacket.model_validate_json(line)


@pytest.fixture(scope="module")
def contract() -> RunContract:
    return claude.contract(Path("."))


# --------------------------------------------------------------------------------------
# Provenance separation
# --------------------------------------------------------------------------------------


def test_the_run_never_claims_luna(contract: RunContract) -> None:
    assert contract.run_id == claude.RUN_ID != claude.ABANDONED_RUN_ID
    assert contract.model_requested == "claude-opus-5"
    assert "luna" not in contract.run_id
    assert "luna" not in contract.model_requested
    assert contract.runtime is ExecutionRuntime.CLAUDE_CODE_DIRECT
    assert claude.PROVENANCE_BUCKET == "CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION"


def test_the_run_reuses_the_frozen_v3_2_policy_unchanged(contract: RunContract) -> None:
    assert contract.prompt_version == "rigveda-semantic-extraction-v3.2"
    assert (
        contract.prompt_sha256 == "e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1"
    )
    assert (
        contract.schema_sha256 == "26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2"
    )
    assert (
        contract.ontology_sha256
        == "cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce"
    )


def test_a_stored_luna_contract_still_loads_as_codex_direct() -> None:
    """The runtime field is defaulted, so a contract written before it existed is unchanged."""
    stored = json.loads((ABANDONED / "store/run_contract.json").read_text(encoding="utf-8"))
    assert "runtime" not in stored
    contract = RunContract.model_validate(stored)
    assert contract.runtime is ExecutionRuntime.CODEX_DIRECT
    assert contract.model_requested == "gpt-5.6-luna"


def test_a_receipt_from_the_wrong_runtime_is_refused(
    packet: EvidencePacket, contract: RunContract
) -> None:
    task = prepare_task(packet, contract)
    receipt = ModelExecutionReceipt(
        execution_version=task.execution_version,
        run_id=task.run_id,
        task_id=task.task_id,
        passage_id=task.passage_id,
        requested_model=task.model_requested,
        reported_model=task.model_requested,
        runtime=ExecutionRuntime.CODEX_DIRECT,
        reasoning=task.reasoning_requested,
        task_sha256=task.task_sha256,
        prompt_sha256=task.prompt_sha256,
        schema_sha256=task.schema_sha256,
        evidence_packet_sha256=task.evidence_packet_sha256,
        response_sha256="0" * 64,
        attempt_id="attempt_001",
        authored_at="2026-01-01T00:00:00Z",
    )
    errors = validate_receipt(receipt, task, contract, computed_response_sha256="0" * 64)
    assert any("runtime" in message for message in errors)


def test_prepare_authors_nothing(packet: EvidencePacket, contract: RunContract) -> None:
    task = prepare_task(packet, contract)
    text = json.dumps(task.model_dump(mode="json"))
    for banned in ("predicate", "explicitness", "assertion_id", "candidate_id", "REQUESTS"):
        assert banned not in text
    assert task.task_id == task_id_for(claude.RUN_ID, packet.passage_key)


def test_claude_and_luna_task_ids_never_collide(packet: EvidencePacket) -> None:
    assert task_id_for(claude.RUN_ID, packet.passage_key) != task_id_for(
        claude.ABANDONED_RUN_ID, packet.passage_key
    )


# --------------------------------------------------------------------------------------
# Partition
# --------------------------------------------------------------------------------------


def test_partition_is_deterministic_disjoint_and_complete() -> None:
    ids = [f"VG:RV:SAK:M01:S{n // 20 + 1:03d}:V{n % 20 + 1:03d}" for n in range(448)]
    groups = claude.partition(ids, 6)
    members = [item for value in groups.values() for item in value]
    assert sorted(members) == sorted(ids)
    assert len(members) == len(set(members)) == 448
    assert claude.partition(ids, 6) == groups
    assert claude.partition(list(reversed(ids)), 6) == groups
    assert max(len(v) for v in groups.values()) - min(len(v) for v in groups.values()) <= 1


def test_partition_hash_changes_with_membership() -> None:
    ids = [f"VG:RV:SAK:M01:S001:V{n + 1:03d}" for n in range(24)]
    assert claude.partition_hash(claude.partition(ids, 4)) != claude.partition_hash(
        claude.partition(ids, 6)
    )


# --------------------------------------------------------------------------------------
# Author view carries evidence only
# --------------------------------------------------------------------------------------


def test_author_view_holds_no_semantics(packet: EvidencePacket) -> None:
    view = claude.author_view(packet)
    text = json.dumps(view, ensure_ascii=False)
    for banned in (
        "assertion",
        "predicate",
        "explicitness",
        "candidate_id",
        "no_claim",
        "REQUESTS",
        "PRAISES",
    ):
        assert banned not in text
    assert view["packet_sha256"] == packet.input_sha256


# --------------------------------------------------------------------------------------
# Assembly refuses rather than repairs
# --------------------------------------------------------------------------------------


def assertion(**overrides: Any) -> dict[str, Any]:
    row = {
        "predicate": "REQUESTS",
        "explicitness": "EXPLICIT",
        "relation_quote": "May he",
        "relation_occurrence": 1,
        "object": {
            "object_kind": "REQUESTED_OUTCOME",
            "display_label": "standing by us",
            "normalized_head": "stand by us",
            "object_quote": "stand by us in our need and in abundance for our wealth",
        },
    }
    row.update(overrides)
    return row


def test_assemble_produces_a_valid_payload(packet: EvidencePacket, contract: RunContract) -> None:
    task = prepare_task(packet, contract)
    output, bindings = claude.assemble({"assertions": [assertion()]}, task, contract)
    assert output["mantra_id"] == packet.citation
    assert output["prompt_version"] == "rigveda-semantic-extraction-v3"
    only = output["assertions"][0]
    assert only["object"]["extraction_model"] == "claude-opus-5"
    assert only["object"]["prompt_version"] == "rigveda-semantic-extraction-v3.2"
    assert only["source_run_id"] == claude.RUN_ID
    roles = {anchor["role"] for anchor in bindings[0]["anchors"]}
    assert roles == {"RELATION", "OUTCOME"}


def test_candidate_ids_differ_across_passages_and_ordinals() -> None:
    first = claude.candidate_id_for(
        run_id="r", passage_id="p1", predicate="REQUESTS", spans=(0, 5, 6, 9), ordinal=1
    )
    other_passage = claude.candidate_id_for(
        run_id="r", passage_id="p2", predicate="REQUESTS", spans=(0, 5, 6, 9), ordinal=1
    )
    other_ordinal = claude.candidate_id_for(
        run_id="r", passage_id="p1", predicate="REQUESTS", spans=(0, 5, 6, 9), ordinal=2
    )
    assert first != other_passage != other_ordinal
    assert first.startswith("VG:SEMOBJ:") and len(first) == len("VG:SEMOBJ:") + 20


def test_ambiguous_quote_is_refused_not_guessed(
    packet: EvidencePacket, contract: RunContract
) -> None:
    task = prepare_task(packet, contract)
    row = assertion()
    del row["relation_occurrence"]
    with pytest.raises(claude.AuthorInputError, match="occurs 2 times"):
        claude.assemble({"assertions": [row]}, task, contract)


def test_a_mid_word_anchor_is_refused(packet: EvidencePacket, contract: RunContract) -> None:
    task = prepare_task(packet, contract)
    with pytest.raises(claude.AuthorInputError, match="no boundary-safe occurrence"):
        claude.assemble(
            {"assertions": [assertion(relation_quote="ay he", relation_occurrence=None)]},
            task,
            contract,
        )


def test_an_unsupplied_canonical_entity_is_refused(
    packet: EvidencePacket, contract: RunContract
) -> None:
    task = prepare_task(packet, contract)
    row = assertion(predicate="PRAISES")
    row["object"] = {
        "object_kind": "CANONICAL_ENTITY_REF",
        "display_label": "Indra",
        "canonical_entity_id": "VG:DEVATA:INDRAH",
        "object_quote": "strength",
    }
    with pytest.raises(claude.AuthorInputError, match="not a supplied lexical mention"):
        claude.assemble({"assertions": [row]}, task, contract)


def test_no_claim_may_not_coexist_with_assertions(
    packet: EvidencePacket, contract: RunContract
) -> None:
    task = prepare_task(packet, contract)
    with pytest.raises(claude.AuthorInputError, match="may not coexist"):
        claude.assemble(
            {"no_claim": True, "no_claim_reasons": ["x"], "assertions": [assertion()]},
            task,
            contract,
        )


def test_no_claim_needs_a_reason(packet: EvidencePacket, contract: RunContract) -> None:
    task = prepare_task(packet, contract)
    with pytest.raises(claude.AuthorInputError, match="at least one non-empty reason"):
        claude.assemble({"no_claim": True, "no_claim_reasons": []}, task, contract)


def test_an_empty_result_is_refused(packet: EvidencePacket, contract: RunContract) -> None:
    task = prepare_task(packet, contract)
    with pytest.raises(claude.AuthorInputError, match="non-empty assertions list"):
        claude.assemble({"assertions": []}, task, contract)


def test_interpretive_explicitness_is_refused(
    packet: EvidencePacket, contract: RunContract
) -> None:
    task = prepare_task(packet, contract)
    with pytest.raises(claude.AuthorInputError, match="EXPLICIT or STRONG_INFERENCE"):
        claude.assemble({"assertions": [assertion(explicitness="INTERPRETIVE")]}, task, contract)


# --------------------------------------------------------------------------------------
# The abandoned attempt stays abandoned
# --------------------------------------------------------------------------------------


def test_the_abandoned_attempt_is_preserved_and_never_imported() -> None:
    record = json.loads(
        Path("docs/manifests/rigveda_semantic_abandoned_luna_448_attempt.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["classification"] == "ABORTED_BEFORE_IMPORT_EXECUTION_CAPACITY_EXHAUSTED"
    assert record["imported_semantic_responses"] == 0
    assert record["final_seal"] is None
    assert record["partial_author_inputs"]["classification"] == "UNTRUSTED_ABANDONED_AUTHOR_INPUT"
    assert record["partial_author_inputs"]["imported_into_any_run"] is False
    assert record["preserved"] is True and record["deleted_files"] == 0
    # The files themselves are still on disk, unmodified.
    assert len(list(ABANDONED.glob("author_inputs/*/*.json"))) == 10
    assert len(list((ABANDONED / "store/tasks").glob("TASK_*/task.json"))) == 448
    assert not list(ABANDONED.glob("**/raw_response.json"))


def test_the_claude_run_reuses_packets_but_not_semantics() -> None:
    manifest = json.loads((RUN_DIR / "run_selection_manifest.json").read_text(encoding="utf-8"))
    assert manifest["packet_reuse_scope"] == "EVIDENCE_PACKET_PREPARATION_ONLY"
    assert manifest["abandoned_author_inputs_imported"] == 0
    assert manifest["abandoned_author_inputs_read_by_authors"] is False
    assert manifest["selected_count"] == 448
    assert manifest["human_gold_status"] == "UNANNOTATED"
    assert manifest["unlocked_predicates"] == []
    assert manifest["canonical_promotion"] is False
    assert manifest["model_self_agreement_is_accuracy"] is False
    frozen = json.loads((ABANDONED / "packet_build_manifest.json").read_text(encoding="utf-8"))
    assert manifest["packet_hashes"] == {
        key: value
        for key, value in frozen["packet_hashes"].items()
        if key in manifest["selected_ids"]
    }


# --------------------------------------------------------------------------------------
# Retry categorisation
# --------------------------------------------------------------------------------------


def coordinator() -> Any:
    """The coordinator script, loaded by path: scripts/ is not an importable package."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("claude448", Path("scripts/claude448.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("receipt runtime does not match the prepared task: 'a' != 'b'", "PROVENANCE_RETRY"),
        ("receipt requested model does not match the prepared task", "PROVENANCE_RETRY"),
        ("receipt evidence packet hash does not match the prepared task", "RECEIPT_RETRY"),
        ("L1: no anchor identifies the relation wording", "BINDING_RETRY"),
        ("A1 RELATION anchor: span 3:9 begins inside a word", "BINDING_RETRY"),
        ("A1: predicate/object type boundary violation", "ONTOLOGY_TYPE_RETRY"),
        ("A1: fabricated token evidence", "EVIDENCE_RETRY"),
        ("semantic output names a different mantra than the task", "SEMANTIC_RETRY"),
    ],
)
def test_validator_refusals_are_categorised(message: str, expected: str) -> None:
    assert coordinator().classify_failure(message) == expected
