import json
from pathlib import Path

import pytest

from vedagraph.models.normalization import (
    ActionEvent,
    EventParticipant,
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.heuristic_baseline import HISTORICAL_V3_120_RUN_ID, extract_packet
from vedagraph.semantic.normalization import (
    StructuredComparisonCategory,
    compare_assertion_sets,
    compare_semantic_objects,
    select_refined_expert_audit_ids,
)
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
    object_kind_is_allowed,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate


def anchor() -> SemanticEvidenceAnchor:
    return SemanticEvidenceAnchor(
        source_passage_id="VG:RV:SAK:M01:S005:V003",
        passage_ids=["VG:RV:SAK:M01:S005:V003"],
    )


def candidate(kind: SemanticObjectKind, *, head: str = "slay") -> SemanticObjectCandidate:
    return SemanticObjectCandidate(
        candidate_id="VG:SEMOBJ:ABCDEF0123456789ABC0",
        object_kind=kind,
        normalized_head=None if kind is SemanticObjectKind.CANONICAL_ENTITY_REF else head,
        display_label=head,
        canonical_entity_id="VG:DEVATA:AGNIH"
        if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
        else None,
        event=ActionEvent(action_head=head) if kind is SemanticObjectKind.EVENT else None,
        source_passage_id="VG:RV:SAK:M01:S005:V003",
        evidence=[anchor()],
        extraction_model="gpt-5.6-luna",
        prompt_version="rigveda-semantic-extraction-v3",
        normalization_status=(
            SemanticObjectNormalizationStatus.ONTOLOGY_GAP
            if kind is SemanticObjectKind.ONTOLOGY_GAP_REF
            else SemanticObjectNormalizationStatus.CANONICAL_REF
            if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
            else SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE
        ),
        ontology_gap_code=(
            "PERSON_LIKE_REFERENT_UNMODELED"
            if kind is SemanticObjectKind.ONTOLOGY_GAP_REF
            else None
        ),
    )


def test_v3_schema_is_execution_schema_and_refuses_interpretive() -> None:
    schema = json.loads(Path("schemas/semantic_extraction_v3.schema.json").read_text())
    assert "INTERPRETIVE" not in schema["$defs"]["Explicitness"]["enum"]
    assertion = StructuredSemanticAssertion(
        assertion_id="a",
        source_run_id="run",
        subject_id="VG:RV:SAK:M01:S005:V003",
        predicate=SemanticPredicate.DESCRIBES_ACTION,
        object=candidate(SemanticObjectKind.EVENT),
        evidence=[anchor()],
        explicitness=Explicitness.INTERPRETIVE,
    )
    with pytest.raises(ValueError):
        SemanticExtractionV3(mantra_id="RV 1.5.3", assertions=[assertion])


def test_all_typed_object_kinds_are_enumerated() -> None:
    assert len(SemanticObjectKind) == 16
    assert all(candidate(kind) for kind in SemanticObjectKind)
    assert object_kind_is_allowed(SemanticPredicate.REQUESTS, SemanticObjectKind.REQUESTED_OUTCOME)
    assert not object_kind_is_allowed(SemanticPredicate.REQUESTS, SemanticObjectKind.EVENT)


def test_packet_extraction_splits_request_outcomes_and_cites_offsets() -> None:
    packet = EvidencePacket.model_validate(
        json.loads(
            Path(
                "data/semantic/vedagraph-rigveda-semantic-luna-v3-120/batches/batch_001/evidence.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
    )
    payload, trace = extract_packet(packet, run_id=HISTORICAL_V3_120_RUN_ID)
    requests = [item for item in payload.assertions if item.predicate is SemanticPredicate.REQUESTS]
    assert {item.object.normalized_head for item in requests} == {"wealth", "presence", "strength"}
    assert all(item.object.object_kind is SemanticObjectKind.REQUESTED_OUTCOME for item in requests)
    assert all(item.evidence[0].translation_span is not None for item in requests)
    assert trace["checklist_completed"] is True
    assert len(trace["families"]) == 14


def test_canonical_reuse_uses_supplied_mention_identity() -> None:
    path = Path(
        "data/semantic/vedagraph-rigveda-semantic-luna-v3-120/batches/batch_002/evidence.jsonl"
    )
    packets = [
        EvidencePacket.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    extracted = [
        (packet, extract_packet(packet, run_id=HISTORICAL_V3_120_RUN_ID)[0]) for packet in packets
    ]
    packet, payload = next(
        (packet, payload)
        for packet, payload in extracted
        if any(
            item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
            for item in payload.assertions
        )
    )
    canonical = [
        item
        for item in payload.assertions
        if item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
    ]
    assert canonical
    assert all(
        item.object.canonical_entity_id in {mention.entity_key for mention in packet.mentions}
        for item in canonical
    )


def test_event_has_absent_roles_when_not_directly_evidenced() -> None:
    path = Path(
        "data/semantic/vedagraph-rigveda-semantic-luna-v3-120/batches/batch_001/evidence.jsonl"
    )
    packet = next(
        EvidencePacket.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    )
    payload, _ = extract_packet(packet, run_id=HISTORICAL_V3_120_RUN_ID)
    for assertion in payload.assertions:
        if assertion.predicate is SemanticPredicate.DESCRIBES_ACTION:
            assert assertion.object.event is not None
            assert assertion.object.event.actor_entity_id is None
            assert assertion.object.event.patient_entity_id is None


def test_event_schema_preserves_actor_patient_and_participant_roles() -> None:
    event = candidate(SemanticObjectKind.EVENT).model_copy(
        update={
            "event": ActionEvent(
                action_head="slay",
                actor_entity_id="VG:DEVATA:INDRAH",
                patient_entity_id="VG:ENTITY:ENEMY",
                other_participants=[EventParticipant(role="instrument", normalized_head="weapon")],
            )
        }
    )
    assertion = StructuredSemanticAssertion(
        assertion_id="event",
        source_run_id="run",
        subject_id="VG:RV:SAK:M01:S005:V003",
        predicate=SemanticPredicate.DESCRIBES_ACTION,
        object=event,
        evidence=[anchor()],
        explicitness=Explicitness.EXPLICIT,
    )
    assert assertion.object.event is not None
    assert assertion.object.event.actor_entity_id == "VG:DEVATA:INDRAH"
    assert assertion.object.event.patient_entity_id == "VG:ENTITY:ENEMY"
    assert assertion.object.event.other_participants[0].role == "instrument"


def test_strong_inference_requires_named_rationale() -> None:
    assertion = StructuredSemanticAssertion(
        assertion_id="a",
        source_run_id="run",
        subject_id="VG:RV:SAK:M01:S005:V003",
        predicate=SemanticPredicate.DESCRIBES_ACTION,
        object=candidate(SemanticObjectKind.EVENT),
        evidence=[anchor()],
        explicitness=Explicitness.STRONG_INFERENCE,
    )
    with pytest.raises(ValueError):
        SemanticExtractionV3(mantra_id="RV 1.5.3", assertions=[assertion])


def test_ontology_gap_and_type_boundaries() -> None:
    gap = candidate(SemanticObjectKind.ONTOLOGY_GAP_REF)
    assert gap.object_kind is SemanticObjectKind.ONTOLOGY_GAP_REF
    assert object_kind_is_allowed(
        SemanticPredicate.INVOLVES_RITUAL, SemanticObjectKind.RITUAL_EVENT
    )
    assert not object_kind_is_allowed(
        SemanticPredicate.INVOLVES_RITUAL, SemanticObjectKind.OFFERING_REF
    )


def test_comparator_does_not_fuzzy_equate_synonyms() -> None:
    left = candidate(SemanticObjectKind.REQUESTED_OUTCOME, head="protection")
    right = candidate(SemanticObjectKind.REQUESTED_OUTCOME, head="safety")
    assert compare_semantic_objects(left, right).value == "CONFLICTING_OBJECT"


def test_structured_comparator_is_order_independent() -> None:
    left = StructuredSemanticAssertion(
        assertion_id="left",
        legacy_assertion_id="left",
        source_run_id="run",
        subject_id="VG:RV:SAK:M01:S005:V003",
        predicate=SemanticPredicate.REQUESTS,
        object=candidate(SemanticObjectKind.REQUESTED_OUTCOME, head="wealth"),
        evidence=[anchor()],
        explicitness=Explicitness.EXPLICIT,
    )
    right = left.model_copy(update={"assertion_id": "right", "legacy_assertion_id": "right"})
    rows = compare_assertion_sets([left], [right])
    assert len(rows) == 1
    assert rows[0].category is StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT


def test_seal_blind_gate_and_no_predicate_unlocking() -> None:
    seal_path = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120/v3_output_seal.json")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal["selected_count"] == 120
    assert seal["comparison_sources_opened"] is False
    assert seal["human_gold_status"] == "UNANNOTATED"
    assert seal["unlocked_predicates"] == []
    assert Path(
        "data/semantic/vedagraph-rigveda-semantic-luna-v3-120/comparison_sources_opened.marker"
    ).exists()


def test_disagreement_decomposition_and_expert_queue_are_refined() -> None:
    decomposition = Path(
        "docs/reports/RIGVEDA_SEMANTIC_V3_DISAGREEMENT_DECOMPOSITION.md"
    ).read_text(encoding="utf-8")
    queue = Path("docs/reports/RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V3.md").read_text(
        encoding="utf-8"
    )
    assert "REPRESENTATION_MISMATCH" in decomposition
    assert "ACTUAL_SEMANTIC_CONFLICT_CANDIDATE" in decomposition
    assert "queue contains **20** cases" in queue
    comparisons = [
        type("Row", (), {"mantra_id": "m1", "category": StructuredComparisonCategory.LEFT_ONLY})(),
        type(
            "Row",
            (),
            {"mantra_id": "m2", "category": StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT},
        )(),
    ]
    assert select_refined_expert_audit_ids(["m1", "m2"], comparisons, target_max=20) == ["m1"]
