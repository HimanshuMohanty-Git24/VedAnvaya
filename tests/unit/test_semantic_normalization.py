from __future__ import annotations

from datetime import UTC, datetime
from itertools import count

import pytest
from pydantic import ValidationError

from vedagraph.models.normalization import (
    ActionEvent,
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticNormalizationManifest,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
    StructuredSemanticComparison,
    TranslationSpan,
)
from vedagraph.models.silver import SilverEvidenceReference, SilverSemanticAssertion
from vedagraph.semantic.normalization import (
    assertion_signature,
    compare_assertion_sets,
    compare_semantic_objects,
    deterministic_object_candidate_id,
    migrate_sol_assertion,
    select_refined_expert_audit_ids,
)
from vedagraph.semantic.object_ontology import (
    PREDICATE_OBJECT_RULES,
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
    SemanticOntologyGapCode,
    StructuredComparisonCategory,
)
from vedagraph.semantic.ontology import Explicitness, SemanticNodeType, SemanticPredicate

KEY = "VG:RV:SAK:M01:S001:V001"
TRANSLATION = "translation-1"
AGNI = "VG:DEVATA:AGNIH"
USAS = "VG:DEVATA:USAH"
SOMA = "VG:DEVATA:SOMAH"
PAVAMANA = "VG:DEVATA:PAVAMANAH-SOMAH"
_IDS = count()


def anchor(*, token: str | None = None) -> SemanticEvidenceAnchor:
    return SemanticEvidenceAnchor(
        source_passage_id=KEY,
        translation_record_id=TRANSLATION,
        token_ids=[token] if token else [],
        passage_ids=[KEY],
    )


def semantic_object(
    kind: SemanticObjectKind,
    *,
    head: str | None = "protection",
    label: str | None = None,
    canonical: str | None = None,
    qualifiers: list[str] | None = None,
    event: ActionEvent | None = None,
    beneficiary: str | None = None,
    target: str | None = None,
    status: SemanticObjectNormalizationStatus | None = None,
) -> SemanticObjectCandidate:
    if kind is SemanticObjectKind.CANONICAL_ENTITY_REF:
        status = SemanticObjectNormalizationStatus.CANONICAL_REF
        head = None
    return SemanticObjectCandidate(
        candidate_id=f"VG:SEMOBJ:{next(_IDS):020X}",
        object_kind=kind,
        normalized_head=head,
        display_label=label or canonical or head or "unmodeled referent",
        qualifiers=qualifiers or [],
        canonical_entity_id=canonical,
        beneficiary_entity_id=beneficiary,
        target_entity_id=target,
        event=event,
        source_passage_id=KEY,
        evidence=[anchor()],
        extraction_model="test-model",
        prompt_version="test-prompt",
        normalization_status=status or SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE,
    )


def assertion(
    predicate: SemanticPredicate,
    obj: SemanticObjectCandidate,
    *,
    assertion_id: str,
    explicitness: Explicitness = Explicitness.EXPLICIT,
    inference_step: str | None = None,
) -> StructuredSemanticAssertion:
    return StructuredSemanticAssertion(
        assertion_id=assertion_id,
        source_run_id="test-run",
        subject_id=KEY,
        predicate=predicate,
        object=obj,
        evidence=obj.evidence,
        explicitness=explicitness,
        inference_step=inference_step,
    )


def test_typed_object_requires_evidence_and_canonical_status() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        SemanticObjectCandidate(
            candidate_id="VG:SEMOBJ:" + "A" * 20,
            object_kind=SemanticObjectKind.STATE_REF,
            normalized_head="fear",
            display_label="fear",
            source_passage_id=KEY,
            evidence=[],
            extraction_model="test",
            prompt_version="test",
            normalization_status=SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE,
        )
    with pytest.raises(ValidationError, match="CANONICAL_REF"):
        SemanticObjectCandidate(
            candidate_id="VG:SEMOBJ:" + "B" * 20,
            object_kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
            display_label="Agni",
            canonical_entity_id=AGNI,
            source_passage_id=KEY,
            evidence=[anchor()],
            extraction_model="test",
            prompt_version="test",
            normalization_status=SemanticObjectNormalizationStatus.NEEDS_REVIEW,
        )


def test_source_span_anchor_validates_offsets() -> None:
    item = SemanticEvidenceAnchor(
        source_passage_id=KEY,
        translation_record_id=TRANSLATION,
        translation_span=TranslationSpan(start=2, end=12),
        passage_ids=[KEY],
    )
    assert item.translation_span == TranslationSpan(start=2, end=12)
    with pytest.raises(ValidationError, match="translation record"):
        SemanticEvidenceAnchor(
            source_passage_id=KEY,
            translation_span=TranslationSpan(start=2, end=12),
            passage_ids=[KEY],
        )


def test_person_like_referent_is_exposed_as_ontology_gap() -> None:
    gap = SemanticObjectCandidate(
        candidate_id="VG:SEMOBJ:" + "C" * 20,
        object_kind=SemanticObjectKind.ONTOLOGY_GAP_REF,
        display_label="unmodeled patron",
        source_passage_id=KEY,
        evidence=[anchor()],
        extraction_model="test",
        prompt_version="test",
        normalization_status=SemanticObjectNormalizationStatus.ONTOLOGY_GAP,
        ontology_gap_code=SemanticOntologyGapCode.PATRON_ROLE_UNMODELED,
    )
    assert gap.ontology_gap_code is SemanticOntologyGapCode.PATRON_ROLE_UNMODELED
    assert gap.canonical_entity_id is None


def test_deterministic_candidate_id_uses_sorted_evidence_not_list_order() -> None:
    first = anchor(token="token-2")
    second = anchor(token="token-1")
    fields = {
        "run_id": "run",
        "mantra_id": KEY,
        "predicate": SemanticPredicate.REQUESTS,
        "ordinal": 0,
        "legacy_object_id": "legacy",
    }
    assert deterministic_object_candidate_id(evidence=[first, second], **fields) == (
        deterministic_object_candidate_id(evidence=[second, first], **fields)
    )


def test_assertion_signature_excludes_display_label_but_includes_structure() -> None:
    left = assertion(
        SemanticPredicate.INVOKES,
        semantic_object(
            SemanticObjectKind.CANONICAL_ENTITY_REF,
            label="Agni",
            canonical=AGNI,
        ),
        assertion_id="left",
    )
    right = assertion(
        SemanticPredicate.INVOKES,
        semantic_object(
            SemanticObjectKind.CANONICAL_ENTITY_REF,
            label="agniḥ",
            canonical=AGNI,
        ),
        assertion_id="right",
    )
    assert assertion_signature(left) == assertion_signature(right)


def test_canonical_entity_key_is_exact_regardless_of_display_label() -> None:
    left = semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, label="Agni", canonical=AGNI)
    right = semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, label="agniḥ", canonical=AGNI)
    assert (
        compare_semantic_objects(left, right) is StructuredComparisonCategory.EXACT_CANONICAL_ENTITY
    )


def test_requested_outcome_assertion_sets_are_order_independent() -> None:
    left = [
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection"),
            assertion_id="left-protection",
        ),
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="wealth"),
            assertion_id="left-wealth",
        ),
    ]
    right = [
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="wealth"),
            assertion_id="right-wealth",
        ),
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection"),
            assertion_id="right-protection",
        ),
    ]
    rows = compare_assertion_sets(left, right)
    assert [item.category for item in rows] == [
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
    ]


def test_multi_outcome_legacy_label_is_not_equated_to_two_outcomes() -> None:
    combined = semantic_object(
        SemanticObjectKind.REQUESTED_OUTCOME,
        head="protection and wealth",
        status=SemanticObjectNormalizationStatus.UNRESOLVED_LEGACY_OBJECT,
    )
    left = [
        assertion(SemanticPredicate.REQUESTS, combined, assertion_id="combined"),
    ]
    right = [
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection"),
            assertion_id="protection",
        ),
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="wealth"),
            assertion_id="wealth",
        ),
    ]
    categories = {item.category for item in compare_assertion_sets(left, right)}
    assert StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT not in categories
    assert categories == {
        StructuredComparisonCategory.UNRESOLVED,
        StructuredComparisonCategory.RIGHT_ONLY,
    }


def test_event_fields_are_compared_independently() -> None:
    detailed = semantic_object(
        SemanticObjectKind.EVENT,
        head="slay",
        event=ActionEvent(
            action_head="slay", actor_entity_id="VG:DEVATA:INDRAH", patient_entity_id="VRTRA"
        ),
    )
    fewer_roles = semantic_object(
        SemanticObjectKind.EVENT,
        head="slay",
        event=ActionEvent(action_head="slay", actor_entity_id="VG:DEVATA:INDRAH"),
    )
    different_head = semantic_object(
        SemanticObjectKind.EVENT,
        head="destroy",
        event=ActionEvent(
            action_head="destroy",
            actor_entity_id="VG:DEVATA:INDRAH",
            patient_entity_id="VRTRA",
        ),
    )
    assert (
        compare_semantic_objects(detailed, fewer_roles)
        is StructuredComparisonCategory.GRANULARITY_DIFFERENCE
    )
    assert (
        compare_semantic_objects(detailed, different_head)
        is StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP
    )


@pytest.mark.parametrize(
    ("left_kind", "right_kind"),
    [
        (SemanticObjectKind.RITUAL_EVENT, SemanticObjectKind.OFFERING_REF),
        (SemanticObjectKind.OFFERING_REF, SemanticObjectKind.SUBSTANCE_REF),
        (SemanticObjectKind.RITUAL_EVENT, SemanticObjectKind.SUBSTANCE_REF),
    ],
)
def test_ritual_offering_substance_boundaries_are_not_collapsed(
    left_kind: SemanticObjectKind, right_kind: SemanticObjectKind
) -> None:
    left = semantic_object(left_kind, head="soma")
    right = semantic_object(right_kind, head="soma")
    assert (
        compare_semantic_objects(left, right) is StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE
    )


def test_natural_phenomenon_is_not_a_canonical_devata() -> None:
    deity = semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, label="Uṣā", canonical=USAS)
    phenomenon = semantic_object(
        SemanticObjectKind.NATURAL_PHENOMENON_REF, head="dawn", label="dawn"
    )
    assert (
        compare_semantic_objects(deity, phenomenon)
        is StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE
    )


def test_soma_and_pavamana_canonical_granularity_remains_distinct() -> None:
    soma = semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, canonical=SOMA)
    pavamana = semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, canonical=PAVAMANA)
    assert (
        compare_semantic_objects(soma, pavamana) is StructuredComparisonCategory.CONFLICTING_OBJECT
    )


def test_legacy_coordinated_object_fails_closed_even_when_labels_match() -> None:
    legacy = SilverSemanticAssertion(
        assertion_id="silver-1",
        subject=KEY,
        predicate=SemanticPredicate.REQUESTS,
        object_label="protection and wealth",
        object_node_type=SemanticNodeType.CONCEPT,
        explicitness=Explicitness.EXPLICIT,
        evidence=[SilverEvidenceReference(kind="TRANSLATION", reference_id=TRANSLATION)],
        rationale_code="TEXT_EXPLICIT",
        confidence=0.9,
    )
    first = migrate_sol_assertion(legacy, run_id="run", ordinal=0)
    second = migrate_sol_assertion(legacy, run_id="run", ordinal=0)
    assert (
        first.object.normalization_status
        is SemanticObjectNormalizationStatus.UNRESOLVED_LEGACY_OBJECT
    )
    assert (
        compare_semantic_objects(first.object, second.object)
        is StructuredComparisonCategory.UNRESOLVED
    )


def test_qualifier_subset_is_granularity_not_exact() -> None:
    broad = semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection")
    qualified = semantic_object(
        SemanticObjectKind.REQUESTED_OUTCOME,
        head="protection",
        qualifiers=["from enemies"],
    )
    assert (
        compare_semantic_objects(broad, qualified)
        is StructuredComparisonCategory.GRANULARITY_DIFFERENCE
    )


def test_compatible_object_is_distinct_from_exact() -> None:
    broad = semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection")
    beneficiary = semantic_object(
        SemanticObjectKind.REQUESTED_OUTCOME,
        head="protection",
        beneficiary="VG:RISHI:RECIPIENT",
    )
    assert (
        compare_semantic_objects(broad, beneficiary)
        is StructuredComparisonCategory.COMPATIBLE_OBJECT
    )


def test_no_fuzzy_or_synonym_auto_equivalence() -> None:
    slay = semantic_object(
        SemanticObjectKind.EVENT,
        head="slay",
        event=ActionEvent(action_head="slay"),
    )
    destroy = semantic_object(
        SemanticObjectKind.EVENT,
        head="destroy",
        event=ActionEvent(action_head="destroy"),
    )
    assert (
        compare_semantic_objects(slay, destroy) is StructuredComparisonCategory.CONFLICTING_OBJECT
    )


def test_unrelated_cross_predicate_objects_are_not_forced_into_a_pair() -> None:
    luna = assertion(
        SemanticPredicate.EXPRESSES,
        semantic_object(SemanticObjectKind.STATE_REF, head="need"),
        assertion_id="luna-state",
    )
    sol = assertion(
        SemanticPredicate.PRAISES,
        semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, canonical=AGNI),
        assertion_id="sol-entity",
    )
    rows = compare_assertion_sets([luna], [sol])
    assert {row.category for row in rows} == {
        StructuredComparisonCategory.LEFT_ONLY,
        StructuredComparisonCategory.RIGHT_ONLY,
    }


def test_aligned_object_with_different_predicate_is_a_predicate_conflict() -> None:
    luna = assertion(
        SemanticPredicate.DESCRIBES,
        semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, canonical=AGNI),
        assertion_id="luna-describes",
    )
    sol = assertion(
        SemanticPredicate.INVOKES,
        semantic_object(SemanticObjectKind.CANONICAL_ENTITY_REF, canonical=AGNI),
        assertion_id="sol-invokes",
    )
    rows = compare_assertion_sets([luna], [sol])
    assert len(rows) == 1
    assert rows[0].category is StructuredComparisonCategory.PREDICATE_DIFFERENCE


def test_predicate_specific_object_schema_rejects_wrong_kind() -> None:
    assert (
        SemanticObjectKind.REQUESTED_OUTCOME
        in PREDICATE_OBJECT_RULES[SemanticPredicate.REQUESTS].preferred
    )
    with pytest.raises(ValidationError, match="REQUESTS cannot target STATE_REF"):
        assertion(
            SemanticPredicate.REQUESTS,
            semantic_object(SemanticObjectKind.STATE_REF, head="fear"),
            assertion_id="wrong-kind",
        )


def test_v3_explicitness_policy_validation() -> None:
    obj = semantic_object(SemanticObjectKind.REQUESTED_OUTCOME, head="protection")
    strong_without_step = assertion(
        SemanticPredicate.REQUESTS,
        obj,
        assertion_id="strong",
        explicitness=Explicitness.STRONG_INFERENCE,
    )
    with pytest.raises(ValidationError, match="named inference step"):
        SemanticExtractionV3(mantra_id=KEY, assertions=[strong_without_step])
    strong_with_step = assertion(
        SemanticPredicate.REQUESTS,
        obj,
        assertion_id="strong-named",
        explicitness=Explicitness.STRONG_INFERENCE,
        inference_step="Resolve an explicitly named beneficiary from the pronoun.",
    )
    assert SemanticExtractionV3(mantra_id=KEY, assertions=[strong_with_step]).assertions
    interpretive = assertion(
        SemanticPredicate.REQUESTS,
        obj,
        assertion_id="interpretive",
        explicitness=Explicitness.INTERPRETIVE,
    )
    with pytest.raises(ValidationError, match="not emitted"):
        SemanticExtractionV3(mantra_id=KEY, assertions=[interpretive])


def test_v3_no_claim_and_assertions_are_mutually_exclusive() -> None:
    row = assertion(
        SemanticPredicate.REQUESTS,
        semantic_object(SemanticObjectKind.REQUESTED_OUTCOME),
        assertion_id="request",
    )
    with pytest.raises(ValidationError, match="cannot coexist"):
        SemanticExtractionV3(
            mantra_id=KEY, assertions=[row], no_claim_reasons=["nothing else supported"]
        )


def test_audit_queue_filter_removes_representation_only_cases() -> None:
    ids = [f"mantra-{index}" for index in range(21)]
    rows = [
        StructuredSemanticComparison(
            mantra_id=ids[0],
            category=StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
            reasoning="representation only",
        )
    ]
    rows.extend(
        StructuredSemanticComparison(
            mantra_id=mantra_id,
            category=StructuredComparisonCategory.PREDICATE_DIFFERENCE,
            reasoning="real predicate boundary",
        )
        for mantra_id in ids[1:]
    )
    selected = select_refined_expert_audit_ids(ids, rows, target_max=20)
    assert selected == ids[1:]


def test_normalization_manifest_forbids_predicate_unlocking() -> None:
    fields = {
        "corpus_manifest_sha256": "a" * 64,
        "traditional_knowledge_manifest_sha256": "b" * 64,
        "lexical_knowledge_manifest_sha256": "c" * 64,
        "luna_v1_manifest_sha256": "d" * 64,
        "luna_v2_manifest_sha256": "e" * 64,
        "sol_silver_manifest_sha256": "f" * 64,
        "semantic_ontology_version": "ontology-v1",
        "input_hashes": {},
        "output_hashes": {},
        "record_counts": {},
        "created_at": datetime(2026, 9, 5, tzinfo=UTC),
    }
    assert SemanticNormalizationManifest.model_validate(fields).unlocked_predicates == []
    with pytest.raises(ValidationError):
        SemanticNormalizationManifest.model_validate(fields | {"unlocked_predicates": ["INVOKES"]})
