"""The CODEX_DIRECT execution contract: prepare, receipts, import, and B01 binding.

Everything here is offline. No model is invoked, no full run is dispatched, and no
predicate is unlocked. The point of the suite is the negative space: what the importer
refuses, and that ``prepare`` cannot author a semantic claim even in principle.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from vedagraph.models.normalization import (
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
    TranslationSpan,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import (
    EXECUTION_CONTRACT_VERSION,
    EXECUTION_VERSION,
    PROVIDER_BUILD_METADATA_UNAVAILABLE,
    REGRESSION_RUN_ID,
    AssertionBinding,
    BindingAnchor,
    BindingRole,
    ExecutionStore,
    ModelAuthoredResponse,
    ModelExecutionReceipt,
    PreparedTask,
    load_run_contract,
    prepare_task,
    response_payload_sha256,
    task_id_for,
)
from vedagraph.semantic.full_run import BatchStore, digest, make_plan
from vedagraph.semantic.heuristic_baseline import BASELINE_PROVENANCE, extract_packet
from vedagraph.semantic.normalization import deterministic_object_candidate_id
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate
from vedagraph.semantic.spans import find_anchors
from vedagraph.semantic.v3 import PROMPT_VERSION

PILOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
ONTOLOGY = Path("src/vedagraph/semantic/ontology.py")
MODEL = "gpt-5.6-luna"

#: Audited B01 manifestations, by citation, from the readiness reports.
B01_CASES = (
    "RV 10.58.1",
    "RV 10.170.1",
    "RV 8.35.7",
    "RV 8.35.8",
    "RV 8.35.9",
    "RV 8.36.4",
    "RV 8.36.5",
    "RV 8.36.6",
    "RV 1.137.3",
    "RV 9.87.4",
    "RV 9.87.9",
    "RV 10.41.1",
    "RV 1.51.9",
)


@lru_cache(maxsize=1)
def pilot_packets() -> dict[str, EvidencePacket]:
    return {
        packet.citation: packet
        for path in sorted((PILOT / "batches").glob("batch_*/evidence.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for packet in [EvidencePacket.model_validate_json(line)]
    }


def contract(run_id: str = REGRESSION_RUN_ID) -> Any:
    return load_run_contract(
        run_id=run_id,
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        ontology_path=ONTOLOGY,
        model_requested=MODEL,
        reasoning_requested="high",
    )


def translation_text(packet: EvidencePacket) -> str:
    assert packet.translation is not None and packet.translation.text is not None
    return packet.translation.text


def translation_id(packet: EvidencePacket) -> str:
    assert packet.translation is not None
    return packet.translation.translation_id


def offsets(packet: EvidencePacket, phrase: str, occurrence: int = 1) -> tuple[int, int]:
    found = find_anchors(translation_text(packet), phrase)
    anchor = found[occurrence - 1]
    return anchor.start, anchor.end


def unique_phrase(packet: EvidencePacket) -> str:
    """The first word in the translation with exactly one boundary-safe occurrence."""
    text = translation_text(packet)
    for word in text.replace(",", " ").replace(";", " ").replace(".", " ").split():
        if len(word) >= 4 and len(find_anchors(text, word)) == 1:
            return word
    raise AssertionError(f"no unique anchor phrase in {packet.citation}")


def anchor(
    packet: EvidencePacket, role: BindingRole, phrase: str, *, entity_id: str | None = None
) -> BindingAnchor:
    start, end = offsets(packet, phrase)
    return BindingAnchor(
        role=role,
        translation_record_id=translation_id(packet),
        start=start,
        end=end,
        text=phrase,
        entity_id=entity_id,
    )


def assertion_for(
    packet: EvidencePacket,
    run_id: str,
    predicate: SemanticPredicate,
    *,
    kind: SemanticObjectKind,
    label: str,
    canonical_entity_id: str | None = None,
    phrase: str,
    model: str = MODEL,
    ordinal: int = 0,
) -> StructuredSemanticAssertion:
    """One well-formed assertion whose object evidence is a real span in the translation."""
    start, end = offsets(packet, phrase)
    evidence = [
        SemanticEvidenceAnchor(
            source_passage_id=packet.passage_key,
            translation_record_id=translation_id(packet),
            translation_span=TranslationSpan(start=start, end=end),
            passage_ids=[packet.passage_key],
        )
    ]
    candidate_id = deterministic_object_candidate_id(
        run_id=run_id,
        mantra_id=packet.passage_key,
        predicate=predicate,
        evidence=evidence,
        ordinal=ordinal,
        legacy_object_id=None,
    )
    candidate = SemanticObjectCandidate(
        candidate_id=candidate_id,
        object_kind=kind,
        normalized_head=None if canonical_entity_id else label,
        display_label=label,
        canonical_entity_id=canonical_entity_id,
        source_passage_id=packet.passage_key,
        evidence=evidence,
        extraction_model=model,
        prompt_version=PROMPT_VERSION,
        normalization_status=(
            SemanticObjectNormalizationStatus.CANONICAL_REF
            if canonical_entity_id
            else SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE
        ),
    )
    return StructuredSemanticAssertion(
        assertion_id=f"V31ASSERT:{candidate_id}",
        source_run_id=run_id,
        subject_id=packet.passage_key,
        predicate=predicate,
        object=candidate,
        evidence=evidence,
        explicitness=Explicitness.EXPLICIT,
    )


def response_bytes(
    task: PreparedTask,
    payload: SemanticExtractionV3,
    bindings: list[AssertionBinding],
    *,
    attempt_id: str = "attempt_001",
    receipt_overrides: dict[str, Any] | None = None,
) -> bytes:
    """Serialise a response the way the agent would write one, receipt hash included."""
    draft = ModelAuthoredResponse.model_construct(
        receipt=None,  # type: ignore[arg-type]
        semantic_output=payload,
        assertion_bindings=bindings,
    )
    receipt = ModelExecutionReceipt(
        execution_version=task.execution_version,
        run_id=task.run_id,
        task_id=task.task_id,
        passage_id=task.passage_id,
        requested_model=task.model_requested,
        reported_model=task.model_requested,
        reasoning=task.reasoning_requested,
        task_sha256=task.task_sha256,
        prompt_sha256=task.prompt_sha256,
        schema_sha256=task.schema_sha256,
        evidence_packet_sha256=task.evidence_packet_sha256,
        response_sha256=response_payload_sha256(draft),
        attempt_id=attempt_id,
        authored_at=datetime.now(UTC),
    )
    row = ModelAuthoredResponse(
        receipt=receipt, semantic_output=payload, assertion_bindings=bindings
    ).model_dump(mode="json")
    if receipt_overrides:
        row["receipt"].update(receipt_overrides)
    return json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def write_response(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def prepared(tmp_path: Path, citation: str, run_id: str = REGRESSION_RUN_ID) -> Any:
    packet = pilot_packets()[citation]
    store = ExecutionStore(tmp_path)
    task = prepare_task(packet, contract(run_id))
    store.write_task(task)
    return packet, store, task


# --- TASK 5: prepare authors nothing --------------------------------------------------


def test_prepare_generates_no_semantic_content_whatsoever(tmp_path: Path) -> None:
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    row = task.model_dump(mode="json")
    assert set(row) == {
        "execution_contract_version",
        "execution_version",
        "run_id",
        "task_id",
        "passage_id",
        "citation",
        "model_requested",
        "reasoning_requested",
        "prompt_sha256",
        "schema_sha256",
        "ontology_sha256",
        "evidence_packet_sha256",
        "evidence_packet",
    }
    serialised = json.dumps(row, ensure_ascii=False)
    for forbidden in (
        "predicate",
        "assertion",
        "explicitness",
        "confidence",
        "normalized_head",
        "INVOKES",
        "REQUESTS",
    ):
        assert forbidden not in serialised
    assert task.task_id == task_id_for(REGRESSION_RUN_ID, packet.passage_key)
    assert store.load_task(task.task_id).task_sha256 == task.task_sha256


def test_preparing_the_same_task_twice_is_idempotent_but_changing_it_is_refused(
    tmp_path: Path,
) -> None:
    _, store, task = prepared(tmp_path, "RV 8.35.7")
    store.write_task(task)  # same bytes: fine
    drifted = task.model_copy(update={"reasoning_requested": "medium"})
    with pytest.raises(ValueError, match="already prepared with different content"):
        store.write_task(drifted)


# --- TASK 7: no response, no semantic output ------------------------------------------


def test_import_refuses_when_no_model_authored_response_exists(tmp_path: Path) -> None:
    _, store, _ = prepared(tmp_path, "RV 8.35.7")
    with pytest.raises(FileNotFoundError, match="model-authored response is required"):
        store.import_response(tmp_path / "never-written.json", contract())


def test_import_refuses_a_response_for_a_task_that_was_never_prepared(tmp_path: Path) -> None:
    packet = pilot_packets()["RV 8.35.7"]
    task = prepare_task(packet, contract())
    payload = SemanticExtractionV3(mantra_id=packet.citation, no_claim_reasons=["nothing stated"])
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, []))
    with pytest.raises(FileNotFoundError, match="no prepared task"):
        ExecutionStore(tmp_path).import_response(path, contract())


# --- a well-formed round trip ---------------------------------------------------------


def valid_invokes(tmp_path: Path) -> tuple[Any, Any, Any, bytes]:
    """RV 8.35.7 with the address anchored, which is the shape B01 was missing."""
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.INVOKES,
        kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
        label="Asvins",
        canonical_entity_id="VG:DEVATA:ASVINAU",
        phrase="O Asvins",
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    binding = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[
            anchor(packet, BindingRole.RELATION, "come thrice"),
            anchor(packet, BindingRole.TARGET, "O Asvins", entity_id="VG:DEVATA:ASVINAU"),
        ],
    )
    return packet, store, task, response_bytes(task, payload, [binding])


def test_a_well_formed_response_imports_and_records_its_receipt(tmp_path: Path) -> None:
    _, store, task, raw = valid_invokes(tmp_path)
    path = write_response(tmp_path / "response.json", raw)
    validated = store.import_response(path, contract())
    assert validated.task.task_id == task.task_id
    assert validated.receipt.runtime == "CODEX_DIRECT"
    assert validated.receipt.model_response_authored is True
    assert validated.receipt.provider_build_metadata == PROVIDER_BUILD_METADATA_UNAVAILABLE
    assert validated.receipt.execution_contract_version == EXECUTION_CONTRACT_VERSION
    assert validated.receipt.execution_version == EXECUTION_VERSION
    stored = store.task_dir(task.task_id) / "attempts" / "attempt_001" / "raw_response.json"
    assert stored.read_bytes() == raw
    assert len(validated.payload.assertions) == 1


# --- TASK 8: every refusal ------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("task_sha256", "0" * 64, "task hash"),
        ("prompt_sha256", "1" * 64, "prompt hash"),
        ("schema_sha256", "2" * 64, "schema hash"),
        ("evidence_packet_sha256", "3" * 64, "evidence packet hash"),
        ("response_sha256", "4" * 64, "response hash"),
        ("passage_id", "VG:RV:SAK:M01:S001:V001", "passage id"),
        ("run_id", "some-other-run", "run id"),
        ("requested_model", "gpt-5.6-sol", "requested model"),
        ("reasoning", "low", "reasoning"),
        ("execution_version", "rigveda-semantic-execution-v9", "execution version"),
    ],
)
def test_import_refuses_a_tampered_receipt(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    _, store, _ = prepared(tmp_path, "RV 8.35.7")
    _, _, _, raw = valid_invokes(tmp_path)
    row = json.loads(raw.decode("utf-8"))
    row["receipt"][field] = value
    path = write_response(tmp_path / "tampered.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError, match=message):
        store.import_response(path, contract())


def test_import_refuses_a_response_whose_run_contract_does_not_match(tmp_path: Path) -> None:
    _, store, _, raw = valid_invokes(tmp_path)
    path = write_response(tmp_path / "response.json", raw)
    foreign = contract().model_copy(update={"schema_sha256": "9" * 64})
    with pytest.raises(ValueError, match="schema hash does not match the run contract"):
        store.import_response(path, foreign)


def test_import_refuses_fabricated_model_provenance(tmp_path: Path) -> None:
    """A payload claiming a model the run did not request is refused, baseline included."""
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.INVOKES,
        kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
        label="Asvins",
        canonical_entity_id="VG:DEVATA:ASVINAU",
        phrase="O Asvins",
        model=BASELINE_PROVENANCE,
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    binding = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[
            anchor(packet, BindingRole.RELATION, "come thrice"),
            anchor(packet, BindingRole.TARGET, "O Asvins", entity_id="VG:DEVATA:ASVINAU"),
        ],
    )
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, [binding]))
    with pytest.raises(ValueError, match="object claims model"):
        store.import_response(path, contract())


def test_import_refuses_a_payload_for_a_different_mantra(tmp_path: Path) -> None:
    _, store, task = prepared(tmp_path, "RV 8.35.7")
    payload = SemanticExtractionV3(mantra_id="RV 1.1.1", no_claim_reasons=["nothing stated"])
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, []))
    with pytest.raises(ValueError, match="different mantra"):
        store.import_response(path, contract())


def test_import_refuses_evidence_that_is_not_in_the_packet(tmp_path: Path) -> None:
    _, store, _, raw = valid_invokes(tmp_path)
    row = json.loads(raw.decode("utf-8"))
    row["semantic_output"]["assertions"][0]["evidence"][0]["token_ids"] = ["VG:RV:TOK:NOPE:0001"]
    path = write_response(tmp_path / "r.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError, match="token"):
        store.import_response(path, contract())


# --- TASK 9: receipt immutability and retries -----------------------------------------


def test_the_raw_receipt_is_never_overwritten_and_a_retry_keeps_the_first_attempt(
    tmp_path: Path,
) -> None:
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    _, _, _, first = valid_invokes(tmp_path)
    first_path = write_response(tmp_path / "first.json", first)
    store.import_response(first_path, contract())
    attempts = store.task_dir(task.task_id) / "attempts"
    assert (attempts / "attempt_001" / "raw_response.json").read_bytes() == first

    # A different response under the same attempt id is refused outright.
    row = json.loads(first.decode("utf-8"))
    row["receipt"]["reported_model"] = "gpt-5.6-luna "
    second_path = write_response(tmp_path / "second.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError):
        store.import_response(second_path, contract())
    assert (attempts / "attempt_001" / "raw_response.json").read_bytes() == first

    # A genuine retry is a new attempt id; the first attempt stays byte-identical.
    retry_payload = SemanticExtractionV3(
        mantra_id=packet.citation, no_claim_reasons=["on reflection, nothing is directly stated"]
    )
    retry = write_response(
        tmp_path / "retry.json",
        response_bytes(task, retry_payload, [], attempt_id="attempt_002"),
    )
    validated = store.import_response(retry, contract())
    assert validated.receipt.attempt_id == "attempt_002"
    assert (attempts / "attempt_001" / "raw_response.json").read_bytes() == first
    assert sorted(item.name for item in attempts.iterdir()) == ["attempt_001", "attempt_002"]


# --- TASK 15-17: B01 relation binding -------------------------------------------------


def test_every_assertion_needs_its_own_binding_evidence(tmp_path: Path) -> None:
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.INVOKES,
        kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
        label="Soma",
        canonical_entity_id="VG:DEVATA:SOMAH",
        phrase="the Soma",
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, []))
    with pytest.raises(ValueError, match="no assertion-specific binding evidence"):
        store.import_response(path, contract())


def test_a_whole_verse_anchor_is_not_assertion_specific_evidence(tmp_path: Path) -> None:
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    text = translation_text(packet)
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.INVOKES,
        kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
        label="Soma",
        canonical_entity_id="VG:DEVATA:SOMAH",
        phrase="the Soma",
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    binding = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[
            BindingAnchor(
                role=BindingRole.RELATION,
                translation_record_id=translation_id(packet),
                start=0,
                end=len(text),
                text=text,
            ),
            anchor(packet, BindingRole.TARGET, "the Soma", entity_id="VG:DEVATA:SOMAH"),
        ],
    )
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, [binding]))
    with pytest.raises(ValueError, match="whole-verse span is not"):
        store.import_response(path, contract())


def test_a_binding_anchor_must_quote_the_translation_exactly(tmp_path: Path) -> None:
    _, store, _, raw = valid_invokes(tmp_path)
    row = json.loads(raw.decode("utf-8"))
    row["assertion_bindings"][0]["anchors"][1]["text"] = "O Asvina"
    path = write_response(tmp_path / "r.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError, match="not the claimed"):
        store.import_response(path, contract())


def test_a_target_anchor_must_name_the_entity_the_assertion_is_about(tmp_path: Path) -> None:
    _, store, _, raw = valid_invokes(tmp_path)
    row = json.loads(raw.decode("utf-8"))
    row["assertion_bindings"][0]["anchors"][1]["entity_id"] = "VG:DEVATA:SOMAH"
    path = write_response(tmp_path / "r.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError, match="target anchor identifies"):
        store.import_response(path, contract())

    row = json.loads(raw.decode("utf-8"))
    row["assertion_bindings"][0]["anchors"][1]["entity_id"] = None
    path = write_response(tmp_path / "r2.json", json.dumps(row).encode("utf-8"))
    with pytest.raises(ValueError, match="does not name the entity"):
        store.import_response(path, contract())


def test_relation_and_target_anchors_may_not_be_the_same_span(tmp_path: Path) -> None:
    packet, store, task = prepared(tmp_path, "RV 8.35.7")
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.INVOKES,
        kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
        label="Asvins",
        canonical_entity_id="VG:DEVATA:ASVINAU",
        phrase="O Asvins",
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    binding = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[
            anchor(packet, BindingRole.RELATION, "O Asvins"),
            anchor(packet, BindingRole.TARGET, "O Asvins", entity_id="VG:DEVATA:ASVINAU"),
        ],
    )
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, [binding]))
    with pytest.raises(ValueError, match="same span"):
        store.import_response(path, contract())


def test_requests_needs_an_anchor_on_the_outcome_itself(tmp_path: Path) -> None:
    """RV 10.58.1: a return cue and the word Son must not combine into a request."""
    packet, store, task = prepared(tmp_path, "RV 10.58.1")
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        SemanticPredicate.REQUESTS,
        kind=SemanticObjectKind.REQUESTED_OUTCOME,
        label="offspring",
        phrase="Son",
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    only_a_cue = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[anchor(packet, BindingRole.RELATION, "We cause to come to thee again")],
    )
    path = write_response(tmp_path / "r.json", response_bytes(task, payload, [only_a_cue]))
    with pytest.raises(ValueError, match="anchor on the requested outcome"):
        store.import_response(path, contract())


@pytest.mark.parametrize("citation", B01_CASES)
def test_audited_b01_cases_cannot_be_asserted_without_relation_specific_evidence(
    tmp_path: Path, citation: str
) -> None:
    """The historical shape — a canonical target with only verse-level evidence — is refused.

    This does not assert what the correct reading of each verse is; a scholar has not been
    asked. It asserts that the mechanism which produced the audited failures no longer has
    a way through the importer.
    """
    packet = pilot_packets()[citation]
    store = ExecutionStore(tmp_path / citation.replace(" ", "_").replace(".", "_"))
    task = prepare_task(packet, contract())
    store.write_task(task)
    mention = next(iter(packet.mentions), None)
    predicate = SemanticPredicate.INVOKES if mention else SemanticPredicate.REQUESTS
    assertion = assertion_for(
        packet,
        REGRESSION_RUN_ID,
        predicate,
        kind=(
            SemanticObjectKind.CANONICAL_ENTITY_REF
            if mention
            else SemanticObjectKind.REQUESTED_OUTCOME
        ),
        label=mention.entity_label if mention else "offspring",
        canonical_entity_id=mention.entity_key if mention else None,
        phrase=unique_phrase(packet),
    )
    payload = SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion])
    path = write_response(
        tmp_path / f"{citation}.json".replace(" ", "_"), response_bytes(task, payload, [])
    )
    with pytest.raises(ValueError, match="binding evidence"):
        store.import_response(path, contract())


# --- TASK 19/20: the baseline and the historical artefacts ----------------------------


def test_the_heuristic_baseline_never_claims_a_model() -> None:
    packet = pilot_packets()["RV 8.35.7"]
    payload, trace = extract_packet(packet, run_id="test-baseline-run")
    assert BASELINE_PROVENANCE == "DETERMINISTIC_HEURISTIC_BASELINE"
    models = {item.object.extraction_model for item in payload.assertions}
    models |= {item.extraction_model for item in payload.ontology_gaps}
    assert models <= {BASELINE_PROVENANCE}
    assert MODEL not in json.dumps(payload.model_dump(mode="json"))
    assert trace["checklist_completed"] is True


def test_the_baseline_cannot_be_committed_to_a_model_provenanced_run(tmp_path: Path) -> None:
    packets = [pilot_packets()[citation] for citation in sorted(pilot_packets())[:24]]
    payloads = [extract_packet(packet, run_id="baseline")[0] for packet in packets]
    ordered = sorted(zip(packets, payloads, strict=True), key=lambda pair: pair[0].passage_key)
    store = BatchStore(
        tmp_path / "run",
        make_plan("baseline", [p.passage_key for p, _ in ordered], digest("freeze"), batch_size=24),
    )
    store.prepare("batch_0001", [p for p, _ in ordered])
    checkpoint = store.commit("batch_0001", [payload for _, payload in ordered])
    assert checkpoint.status == "FAILED"
    assert any("model differs from freeze" in item for item in checkpoint.validator_result)


def test_historical_runs_are_classified_and_left_unmodified() -> None:
    registry = json.loads(
        Path("docs/manifests/rigveda_semantic_historical_artifacts.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["artifacts_preserved_unmodified"] is True
    runs = {item["run_id"]: item for item in registry["runs"]}
    for run_id in (
        "vedagraph-rigveda-semantic-luna-v3-120",
        "vedagraph-rigveda-semantic-luna-v3-replication-120",
        "vedagraph-rigveda-semantic-luna-v3-508",
    ):
        assert runs[run_id]["classification"] == "HISTORICAL_HEURISTIC_ARTIFACT"
        assert runs[run_id]["declared_model_is_accurate"] is False
        assert runs[run_id]["artifact_mutated_by_this_registry"] is False
        assert "evidence of gpt-5.6-luna accuracy" in runs[run_id]["forbidden_uses"]
    correction = Path("docs/architecture/SEMANTIC_V3_PROVENANCE_CORRECTION.md").read_text(
        encoding="utf-8"
    )
    assert "HEURISTIC PIPELINE REPLAY" in correction
    assert "MODEL REPLICATION STABILITY" in correction


# --- TASK 21-23: the bounded regression set -------------------------------------------


def regression_config() -> dict[str, Any]:
    text = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml").read_text(
        encoding="utf-8"
    )
    rows: dict[str, Any] = {"mantras": []}
    for line in text.splitlines():
        if line.startswith("- passage_key: "):
            rows["mantras"].append({"passage_key": line.split(": ", 1)[1]})
        elif line.startswith("  stratum: ") and rows["mantras"]:
            rows["mantras"][-1]["stratum"] = line.split(": ", 1)[1]
        elif ": " in line and not line.startswith(" ") and not line.startswith("-"):
            key, value = line.split(": ", 1)
            rows[key] = value
    return rows


def test_the_regression_set_is_identifier_only_and_names_a_new_execution_identity() -> None:
    config = regression_config()
    assert config["run_id"] == REGRESSION_RUN_ID
    assert config["execution_version"] == EXECUTION_VERSION
    assert config["unlocked_predicates"] == "[]"
    assert config["human_gold_status"] == "UNANNOTATED"
    assert int(config["mantra_count"]) == len(config["mantras"])
    assert 40 <= len(config["mantras"]) <= 70
    text = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml").read_text(
        encoding="utf-8"
    )
    for forbidden in ("INVOKES", "PRAISES", "REQUESTS", "DESCRIBES", "confidence:", "explicitness"):
        assert forbidden not in text
    assert "assertions" not in text
    # The retired identities may not be reused.
    for retired in ("v3-120", "v3-508", "v3-replication"):
        assert retired not in config["run_id"]


def test_the_regression_set_covers_every_audited_blocker_case() -> None:
    keys = {row["passage_key"] for row in regression_config()["mantras"]}
    audit = json.loads(
        Path("docs/manifests/rigveda_semantic_readiness_audit.json").read_text(encoding="utf-8")
    )
    blocked = {
        key
        for record in [*audit["gaps"], *audit["parallels"], *audit["review_queue"]]
        if record["blocker_ids"]
        for key in record["passage_ids"]
    }
    blocked |= {item["passage_id"] for item in audit["anchor_defects"]}
    parallels = {key for record in audit["parallels"] for key in record["passage_ids"]}
    assert blocked <= keys
    assert parallels <= keys
    assert {pilot_packets()[citation].passage_key for citation in B01_CASES} <= keys


def test_regression_selection_is_deterministic() -> None:
    import hashlib

    config = regression_config()
    ordered = sorted(row["passage_key"] for row in config["mantras"])
    recomputed = hashlib.sha256(
        json.dumps(
            {
                "policy": "rigveda-semantic-codex-luna-regression-selection-v1",
                "ids": ordered,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert recomputed == config["selection_hash"]


def test_regression_config_serializer_round_trips_unsafe_reason_strings() -> None:
    import importlib.util

    import yaml

    script_path = Path("scripts/build_semantic_regression_v1.py")
    spec = importlib.util.spec_from_file_location("regression_builder", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    document = {
        "reasons": [
            "B01: relation binding",
            "B02: evidence span",
            "foo: bar # preserved",
            "quotes: \"single\" and 'double'",
            "Sanskrit: अग्निḥ — ऋत",
            "multiline: first line\nsecond line",
        ]
    }
    encoded = module.serialize_config_document(document)
    assert yaml.safe_load(encoded) == document


# --- TASK 24 and the standing gates ---------------------------------------------------


def test_batch_store_accepts_validated_receipts_and_rejects_a_foreign_batch(
    tmp_path: Path,
) -> None:
    _, store, _, raw = valid_invokes(tmp_path)
    path = write_response(tmp_path / "response.json", raw)
    validated = store.import_response(path, contract())
    packet = validated.task.evidence_packet
    plan = make_plan(REGRESSION_RUN_ID, [packet.passage_key], digest("freeze"), batch_size=20)
    batches = BatchStore(tmp_path / "run", plan)
    batches.prepare("batch_0001", [packet])
    with pytest.raises(ValueError, match="response IDs/order mismatch"):
        batches.commit_receipts("batch_0001", [])
    checkpoint = batches.commit_receipts("batch_0001", [validated])
    assert checkpoint.status == "VALIDATED"
    assert checkpoint.mantra_ids == [packet.passage_key]


def test_no_predicate_is_unlocked_and_no_full_run_is_dispatched() -> None:
    config = regression_config()
    assert config["unlocked_predicates"] == "[]"
    assert config["candidate_status"] == "CANDIDATE / NEEDS_REVIEW"
    freeze = json.loads(
        Path("docs/manifests/rigveda_semantic_execution_v3_1_freeze.draft.json").read_text(
            encoding="utf-8"
        )
    )
    assert freeze["unlocked_predicates"] == []
    assert freeze["human_gold_status"] == "UNANNOTATED"
    assert "BLOCKED draft" in freeze["runtime_version"]
    # The draft freeze remains a draft, while the explicitly authorized bounded regression
    # now has its own sealed run directory.
    assert not Path(f"data/semantic/{freeze['run_id']}").exists()
    regression = Path(f"data/semantic/{REGRESSION_RUN_ID}")
    assert regression.exists()
    packet_manifest = json.loads(
        (regression / "packet_build_manifest.json").read_text(encoding="utf-8")
    )
    assert packet_manifest["packet_count"] == 60
    assert packet_manifest["semantic_generation"] is False
