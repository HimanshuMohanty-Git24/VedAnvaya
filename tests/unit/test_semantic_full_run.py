"""Readiness-audit records and offline full-run batch custody. No extraction happens here."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.full_run import (
    BatchStore,
    Checkpoint,
    Freeze,
    Plan,
    digest,
    file_hash,
    make_plan,
    validate_ids,
    validate_recorded_payload,
)
from vedagraph.semantic.readiness import (
    GapAudit,
    ParallelAudit,
    ReviewAudit,
    readiness_state,
)

PILOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
MANIFESTS = Path("docs/manifests")
REPORTS = Path("docs/reports")
RUN_ID = "vedagraph-rigveda-semantic-luna-v3-508"
#: The v3 draft freeze is preserved untouched and is now correctly stale: the extraction
#: contract changed, which is exactly what a freeze is meant to detect. The v3.1 draft is
#: preserved and stale for the same reason since the v3.2 prompt-policy revision moved the
#: execution contract and the batch operations file; see the staleness test below.
FULL_RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-full-1.0.0-rc1"
LEGACY_FULL_RUN_ID = "vedagraph-rigveda-semantic-luna-v3-full-1.0.0-rc1"

#: The frozen inputs the v3.2 policy revision moved. No full run was ever dispatched under
#: the v3.1 draft, so nothing is invalidated; the draft simply now names older bytes.
V3_2_MOVED_INPUTS = (
    "src/vedagraph/semantic/codex_direct.py",
    "src/vedagraph/semantic/full_run.py",
)


def audit() -> dict[str, Any]:
    text = (MANIFESTS / "rigveda_semantic_readiness_audit.json").read_text(encoding="utf-8")
    return json.loads(text)


def freeze_draft() -> Freeze:
    path = MANIFESTS / "rigveda_semantic_execution_v3_1_freeze.draft.json"
    text = path.read_text(encoding="utf-8")
    return Freeze.model_validate_json(text)


def current_freeze() -> Freeze:
    """The preserved v3.1 draft with its file hashes recomputed from the working tree.

    The draft on disk pins the pre-v3.2 execution contract and is deliberately left that
    way. Rebuilding the hashes here keeps ``Freeze.verify``'s success path under test
    without reissuing a full-corpus freeze, which no session may do while the full run is
    blocked.
    """
    draft = freeze_draft()
    row = draft.model_dump(mode="json")
    row["files"] = {name: file_hash(Path(name)) for name in draft.files}
    return Freeze.model_validate(row)


def historical_payloads() -> dict[str, SemanticExtractionV3]:
    """The sealed 508 payloads, by citation. Read only; never rewritten."""
    return {
        p.mantra_id: p
        for line in (PILOT / "v3_extractions.jsonl").read_text(encoding="utf-8").splitlines()
        if line
        for p in [SemanticExtractionV3.model_validate_json(line)]
    }


def batch_packets(batch_id: str) -> list[EvidencePacket]:
    directory = PILOT / "batches" / batch_id
    return [
        EvidencePacket.model_validate_json(line)
        for line in (directory / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]


#: batch_001 is not used for custody exercises: it contains RV 1.35.5, whose sealed gap
#: anchor lands inside "manifested" and is now correctly refused (B02). Custody tests need
#: a batch that passes validation and carries assertions, so that a failure means what the
#: test says it means. batch_002 is entirely no-claim, so batch_005 is the first usable one.
CUSTODY_BATCH = "batch_005"


def pilot_batch() -> tuple[list[EvidencePacket], list[SemanticExtractionV3]]:
    """A sealed pilot batch of 24 real packets with their recorded payloads."""
    packets = batch_packets(CUSTODY_BATCH)
    payloads = historical_payloads()
    return packets, [payloads[p.citation] for p in packets]


def store(root: Path, packets: list[EvidencePacket], batch_size: int = 24) -> BatchStore:
    ids = sorted(p.passage_key for p in packets)
    return BatchStore(root, make_plan(RUN_ID, ids, digest("freeze"), batch_size=batch_size))


# --- audit records -------------------------------------------------------------------


def test_gap_audit_rejects_unknown_classification_and_keeps_diagnostic_provenance() -> None:
    with pytest.raises(ValidationError):
        GapAudit(
            case_id="g",
            passage_ids=["VG:RV:SAK:M01:S005:V003"],
            classification="PROBABLY_FINE",  # type: ignore[arg-type]
            person_ref="USEFUL",
            rationale="r",
            decision="DOES_NOT_BLOCK_FULL_RUN",
        )
    ok = GapAudit(
        case_id="g",
        passage_ids=["VG:RV:SAK:M01:S005:V003"],
        classification="TRUE_SCHEMA_GAP",
        person_ref="USEFUL",
        rationale="r",
        decision="DOES_NOT_BLOCK_FULL_RUN",
    )
    assert ok.provenance == "ENGINEERING_DIAGNOSTIC"


def test_parallel_and_review_classifications_are_closed_vocabularies() -> None:
    with pytest.raises(ValidationError):
        ParallelAudit(
            case_id="p",
            passage_ids=["a"],
            classification="LOOKS_DIFFERENT",  # type: ignore[arg-type]
            rationale="r",
            decision="DOES_NOT_BLOCK_FULL_RUN",
        )
    with pytest.raises(ValidationError):
        ReviewAudit(
            case_id="r",
            passage_ids=["a"],
            classification="ONTOLOGY_GAP",
            secondary_tags=["NEEDS_A_SCHOLAR"],  # type: ignore[list-item]
            rationale="r",
            decision="DOES_NOT_BLOCK_FULL_RUN",
        )


@pytest.mark.parametrize(
    ("decision", "blockers"),
    [("BLOCKS_FULL_RUN", []), ("DOES_NOT_BLOCK_FULL_RUN", ["B01"])],
)
def test_blocking_requires_a_named_engineering_blocker(decision: str, blockers: list[str]) -> None:
    with pytest.raises(ValidationError, match="concrete engineering blocker"):
        ReviewAudit(
            case_id="r",
            passage_ids=["a"],
            classification="PHILOLOGY_REQUIRED",
            rationale="a scholar could read this more deeply",
            blocker_ids=blockers,
            decision=decision,  # type: ignore[arg-type]
        )


def test_readiness_state_blocks_on_blockers_or_missing_operations() -> None:
    ready = readiness_state([], frozen=True, operations_ready=True)
    assert ready == "FULL_RIGVEDA_V3_CANDIDATE_RUN_READY"
    blocked = "FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED"
    assert readiness_state(["B01"], frozen=True, operations_ready=True) == blocked
    assert readiness_state([], frozen=False, operations_ready=True) == blocked
    assert readiness_state([], frozen=True, operations_ready=False) == blocked


def test_audit_covers_every_pilot_gap_pair_and_queue_case_with_known_blockers() -> None:
    record = audit()
    summary = record["summary"]
    assert len(record["gaps"]) == 70
    assert len(record["parallels"]) == 13
    assert len(record["review_queue"]) == 50
    assert sum(summary["gap_counts"].values()) == 70
    assert sum(summary["triage_counts"].values()) == 50
    known = set(summary["blockers"])
    entries = record["gaps"] + record["parallels"] + record["review_queue"]
    for entry in entries:
        assert set(entry["blocker_ids"]) <= known
        blocking = entry["decision"] == "BLOCKS_FULL_RUN"
        assert bool(entry["blocker_ids"]) is blocking
    assert summary["final_state"] == readiness_state(
        sorted(known), frozen=True, operations_ready=True
    )
    assert summary["ontology_decision"] == "KEEP_GAPS_FOR_FULL_RUN"
    assert summary["parallel_decision"] == "PARALLEL_EXTRACTION_BUG_FOUND"


def test_audit_reports_exist_and_state_the_blocked_gate() -> None:
    names = [
        "RIGVEDA_SEMANTIC_FULL_RUN_READINESS.md",
        "RIGVEDA_SEMANTIC_508_ONTOLOGY_AUDIT.md",
        "RIGVEDA_SEMANTIC_508_PARALLEL_AUDIT.md",
        "RIGVEDA_SEMANTIC_508_REVIEW_TRIAGE.md",
        "RIGVEDA_SEMANTIC_FULL_RUN_OPERATIONS.md",
    ]
    for name in names:
        text = (REPORTS / name).read_text(encoding="utf-8")
        assert "unlocked_predicates = []" in text
        assert "CANDIDATE / NEEDS_REVIEW" in text
    readiness = (REPORTS / "RIGVEDA_SEMANTIC_FULL_RUN_READINESS.md").read_text(encoding="utf-8")
    assert "FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED" in readiness
    assert "FULL_RIGVEDA_V3_CANDIDATE_RUN_READY" not in readiness


# --- freeze contract and full ID set -------------------------------------------------


def test_freeze_draft_pins_the_full_corpus_and_every_required_role() -> None:
    freeze = freeze_draft()
    assert freeze.run_id == FULL_RUN_ID
    assert len(freeze.passage_ids) == len(set(freeze.passage_ids)) == 10_552
    assert freeze.passage_ids == sorted(freeze.passage_ids)
    for role in ("prompt", "schema", "object_ontology", "packet_schema", "runtime_lock"):
        assert freeze.files[freeze.roles[role]]


def test_freeze_is_candidate_only_and_cannot_unlock_predicates() -> None:
    draft = freeze_draft().model_dump(mode="json")
    assert draft["unlocked_predicates"] == []
    assert draft["candidate_status"] == "CANDIDATE / NEEDS_REVIEW"
    assert draft["provenance"] == "LLM_EXTRACTED / MODEL_CANDIDATE"
    assert draft["human_gold_status"] == "UNANNOTATED"
    for field, value in [
        ("unlocked_predicates", ["REQUESTS"]),
        ("candidate_status", "HUMAN_GOLD"),
        ("provenance", "SOURCE_EXPLICIT"),
        ("human_gold_status", "ANNOTATED"),
    ]:
        with pytest.raises(ValidationError):
            Freeze.model_validate(draft | {field: value})


def test_the_preserved_v3_1_draft_freeze_detects_the_v3_2_contract_change() -> None:
    """A stale draft is the freeze mechanism working, not a defect to be papered over."""
    draft = freeze_draft()
    assert [name for name, value in draft.files.items() if file_hash(Path(name)) != value] == list(
        V3_2_MOVED_INPUTS
    )
    with pytest.raises(ValueError, match="require new extraction version"):
        draft.verify(Path.cwd(), list(draft.passage_ids))
    assert draft.run_id == FULL_RUN_ID


def test_freeze_verify_detects_changed_inputs_and_a_changed_ID_set(tmp_path: Path) -> None:
    freeze = current_freeze()
    freeze.verify(Path.cwd(), list(freeze.passage_ids))
    with pytest.raises(ValueError, match="full corpus ID set changed"):
        freeze.verify(Path.cwd(), [*freeze.passage_ids[:-1], "VG:RV:SAK:M10:S191:V009"])
    name, _ = next(iter(freeze.files.items()))
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_bytes(b"drifted")
    with pytest.raises(ValueError, match="require new extraction version"):
        freeze.verify(tmp_path, list(freeze.passage_ids))


def test_full_id_set_rejects_gaps_duplicates_and_malformed_keys() -> None:
    ids = freeze_draft().passage_ids
    validate_ids(list(ids), expected_count=10_552)
    with pytest.raises(ValueError, match="incomplete or duplicate"):
        validate_ids(ids[:-1], expected_count=10_552)
    with pytest.raises(ValueError, match="incomplete or duplicate"):
        validate_ids([*ids[:-1], ids[0]], expected_count=10_552)
    with pytest.raises(ValueError, match="invalid mantra ID"):
        validate_ids([*ids[:-1], "VG:RV:SAK:M11:S001:V001"], expected_count=10_552)


# --- deterministic batch plan --------------------------------------------------------


def test_batch_plan_is_deterministic_ordered_and_covers_every_ID_once() -> None:
    ids = freeze_draft().passage_ids
    plan = make_plan(FULL_RUN_ID, list(reversed(ids)), digest("freeze"), batch_size=24)
    assert len(plan.batches) == 440
    assert [b.batch_id for b in plan.batches][:2] == ["batch_0001", "batch_0002"]
    assert len(plan.batches[-1].mantra_ids) == 16
    flat = [key for batch in plan.batches for key in batch.mantra_ids]
    assert flat == sorted(ids)
    assert digest(plan.model_dump(mode="json")) == digest(
        make_plan(FULL_RUN_ID, list(ids), digest("freeze"), batch_size=24).model_dump(mode="json")
    )


def test_batch_plan_refuses_oversized_batches_and_tampered_slices() -> None:
    ids = freeze_draft().passage_ids[:60]
    with pytest.raises(ValidationError):
        make_plan(FULL_RUN_ID, list(ids), digest("freeze"), batch_size=40)
    plan = make_plan(FULL_RUN_ID, list(ids), digest("freeze"), batch_size=20).model_dump(
        mode="json"
    )
    plan["batches"][0]["mantra_ids"][0] = plan["batches"][1]["mantra_ids"][0]
    with pytest.raises(ValidationError, match="batch plan changed or duplicates"):
        Plan.model_validate(plan)


# --- checkpoint manifest -------------------------------------------------------------


def checkpoint(**overrides: Any) -> Checkpoint:
    base: dict[str, Any] = {
        "run_id": RUN_ID,
        "batch_id": "batch_0001",
        "mantra_ids": ["VG:RV:SAK:M01:S005:V003"],
        "packet_hashes": {"VG:RV:SAK:M01:S005:V003": "0" * 64},
        "plan_hash": "1" * 64,
    }
    return Checkpoint.model_validate(base | overrides)


def test_checkpoint_statuses_require_their_own_evidence() -> None:
    assert checkpoint().status == "PENDING"
    with pytest.raises(ValidationError, match="completed output needs a hash"):
        checkpoint(status="EXTRACTED")
    with pytest.raises(ValidationError, match="requires clean validation"):
        checkpoint(status="VALIDATED", output_hash="2" * 64)
    with pytest.raises(ValidationError, match="failure needs a diagnostic"):
        checkpoint(status="FAILED")
    with pytest.raises(ValidationError, match="packet coverage mismatch"):
        checkpoint(packet_hashes={})
    sealed = checkpoint(status="SEALED", output_hash="2" * 64, completed_timestamp="2026-09-05")
    assert sealed.validator_result == []


# --- custody, resume and seal prerequisites ------------------------------------------


def test_prepare_commit_produces_a_validated_resumable_checkpoint(tmp_path: Path) -> None:
    packets, payloads = pilot_batch()
    bench = store(tmp_path / "run", packets)
    prepared = bench.prepare("batch_0001", packets)
    assert prepared.status == "PENDING"
    assert prepared.packet_hashes == {p.passage_key: p.input_sha256 for p in packets}
    committed = bench.commit("batch_0001", payloads)
    assert committed.status == "VALIDATED"
    assert committed.validator_result == []
    assert committed.completed_timestamp
    # A fresh process over the same directory re-verifies without re-extraction.
    resumed = store(tmp_path / "run", packets).recover("batch_0001")
    assert resumed.status == "VALIDATED"
    assert resumed.output_hash == committed.output_hash
    aggregate = json.loads(
        store(tmp_path / "run", packets).regenerate().read_text(encoding="utf-8")
    )
    assert [row["mantra_id"] for row in aggregate] == [p.citation for p in packets]


def test_duplicate_commit_and_reordered_or_mutated_packets_are_refused(tmp_path: Path) -> None:
    packets, payloads = pilot_batch()
    bench = store(tmp_path / "run", packets)
    bench.prepare("batch_0001", packets)
    bench.commit("batch_0001", payloads)
    with pytest.raises(ValueError, match="already processed"):
        bench.commit("batch_0001", payloads)
    with pytest.raises(ValueError, match="batch packet IDs/order mismatch"):
        bench.prepare("batch_0001", list(reversed(packets)))
    mutated = packets[0].model_copy(update={"input_sha256": "9" * 64})
    with pytest.raises(ValueError, match="packet hash mismatch"):
        store(tmp_path / "other", packets).prepare("batch_0001", [mutated, *packets[1:]])


def test_tampered_output_fails_closed_and_retry_archives_the_failed_attempt(
    tmp_path: Path,
) -> None:
    packets, payloads = pilot_batch()
    root = tmp_path / "run"
    bench = store(root, packets)
    bench.prepare("batch_0001", packets)
    bench.commit("batch_0001", payloads)
    output = root / "batch_0001" / "output.json"
    output.write_text(json.dumps([payloads[0].model_dump(mode="json")]), encoding="utf-8")
    with pytest.raises(ValueError, match="completed batch verification failed"):
        store(root, packets).recover("batch_0001")


def test_invalid_payload_fails_the_batch_then_retry_restores_a_pending_slot(
    tmp_path: Path,
) -> None:
    packets, payloads = pilot_batch()
    root = tmp_path / "run"
    bench = store(root, packets)
    bench.prepare("batch_0001", packets)
    foreign = payloads[0].model_dump(mode="json")
    foreign["assertions"] = []
    foreign["ontology_gaps"] = []
    foreign["no_claim_reasons"] = ["no supported relation"]
    broken = [SemanticExtractionV3.model_validate(foreign), *payloads[1:]]
    failed = bench.commit("batch_0001", broken[: len(payloads) - 1])
    assert failed.status == "FAILED"
    assert failed.validator_result
    archived = root / "batch_0001" / f"failed-{file_hash(root / 'batch_0001' / 'output.json')}.json"
    retried = bench.retry_failed("batch_0001")
    assert retried.status == "PENDING"
    assert retried.output_hash is None
    assert archived.exists()
    assert not (root / "batch_0001" / "output.json").exists()
    assert bench.commit("batch_0001", payloads).status == "VALIDATED"


def test_recorded_payload_validation_rejects_a_foreign_run_or_stray_anchor() -> None:
    packets, payloads = pilot_batch()
    packet, payload = next(
        (packet, payload)
        for packet, payload in zip(packets, payloads, strict=True)
        if payload.assertions
    )
    assert validate_recorded_payload(payload, packet, RUN_ID) == []
    assert "assertion run ID differs from checkpoint" in validate_recorded_payload(
        payload, packet, "some-other-run"
    )
    stray = payload.model_dump(mode="json")
    stray["assertions"][0]["evidence"][0]["token_ids"] = ["VG:RV:TOK:MADE:UP:0001"]
    errors = validate_recorded_payload(SemanticExtractionV3.model_validate(stray), packet, RUN_ID)
    assert "invalid token anchor" in errors


def test_seal_requires_validated_batches_and_a_matching_freeze(tmp_path: Path) -> None:
    packets, payloads = pilot_batch()
    root = tmp_path / "run"
    freeze = current_freeze()
    plan = make_plan(
        RUN_ID,
        sorted(p.passage_key for p in packets),
        digest(freeze.model_dump(mode="json")),
        batch_size=24,
    )
    bench = BatchStore(root, plan)
    with pytest.raises(ValueError):  # nothing extracted yet
        bench.regenerate()
    bench.prepare("batch_0001", packets)
    bench.commit("batch_0001", payloads)
    # Run ID and the pinned 10,552-ID set must both match before a seal is written.
    with pytest.raises(ValueError, match="freeze/plan mismatch"):
        bench.seal(freeze, Path.cwd(), list(freeze.passage_ids))
    assert not (root / "seal.json").exists()


def test_existing_plan_hash_mismatch_refuses_to_reopen_a_run(tmp_path: Path) -> None:
    packets, _ = pilot_batch()
    root = tmp_path / "run"
    store(root, packets)
    with pytest.raises(ValueError, match="existing plan hash mismatch"):
        store(root, packets, batch_size=20)
