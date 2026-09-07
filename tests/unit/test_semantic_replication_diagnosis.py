"""Tests for the truth-neutral real-Luna replication diagnosis model.

These tests assert classification behavior only.  Nothing here treats either sealed
run, model agreement, or any historical heuristic artifact as human gold.
"""

import json
from pathlib import Path

from vedagraph.semantic.replication_diagnosis import (
    AlignmentCategory,
    AnchorAssessment,
    ComparableAssertion,
    DiagnosticSet,
    EmissionRegime,
    NoClaimAssessment,
    OneSidedAssessment,
    SeverityV2,
    align_assertions,
    candidate_provenance_label,
    canonical_entity_contradiction,
    diagnostic_set_for,
    exchangeable_one_sided_probability,
    no_claim_assessment,
    regime_divergence,
    severity_v2,
)

DIAGNOSIS = Path("docs/manifests/rigveda_semantic_real_luna_replication_diagnosis.json")
ADJUDICATION = Path("docs/manifests/rigveda_semantic_real_luna_replication_adjudication.json")


def assertion(
    assertion_id: str,
    predicate: str = "REQUESTS",
    *,
    object_kind: str = "OPAQUE_REFERENT",
    normalized_head: str | None = "wealth",
    canonical_entity_id: str | None = None,
    qualifiers: tuple[str, ...] = (),
    evidence_references: tuple[str, ...] = ("TRANSLATION:T:0:10",),
) -> ComparableAssertion:
    """Build one comparison view for alignment tests."""
    return ComparableAssertion(
        assertion_id=assertion_id,
        predicate=predicate,
        object_kind=object_kind,
        normalized_head=normalized_head,
        canonical_entity_id=canonical_entity_id,
        qualifiers=qualifiers,
        beneficiary_entity_id=None,
        target_entity_id=None,
        event_action_head=None,
        event_actor_entity_id=None,
        event_patient_entity_id=None,
        event_participants=(),
        evidence_references=evidence_references,
        binding_anchors=(("RELATION", "grant", 0, 5),),
    )


# --- assertion alignment -------------------------------------------------------


def test_identical_assertions_align_as_exact() -> None:
    rows = align_assertions([assertion("A1")], [assertion("B1")])
    assert [row.category for row in rows] == [AlignmentCategory.EXACT_ASSERTION]


def test_same_object_different_evidence_is_not_exact() -> None:
    rows = align_assertions(
        [assertion("A1")],
        [assertion("B1", evidence_references=("TRANSLATION:T:20:30",))],
    )
    assert rows[0].category is AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE


def test_predicate_boundary_difference_over_same_object() -> None:
    rows = align_assertions([assertion("A1")], [assertion("B1", predicate="DESCRIBES")])
    assert rows[0].category is AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE


def test_object_granularity_difference_uses_qualifier_subset() -> None:
    rows = align_assertions([assertion("A1")], [assertion("B1", qualifiers=("abundant",))])
    assert rows[0].category is AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE


def test_unmatched_assertions_become_one_sided_rows() -> None:
    rows = align_assertions(
        [assertion("A1", normalized_head="wealth")],
        [assertion("B1", normalized_head="chariot")],
    )
    assert {row.category for row in rows} == {AlignmentCategory.A_ONLY, AlignmentCategory.B_ONLY}


def test_alignment_does_not_synonym_normalize() -> None:
    """Distinct heads never collapse through a synonym or embedding rule."""
    rows = align_assertions(
        [assertion("A1", normalized_head="riches")],
        [assertion("B1", normalized_head="wealth")],
    )
    assert all(row.category in {AlignmentCategory.A_ONLY, AlignmentCategory.B_ONLY} for row in rows)


def test_empty_side_yields_only_one_sided_rows() -> None:
    rows = align_assertions([assertion("A1")], [])
    assert [row.category for row in rows] == [AlignmentCategory.A_ONLY]


# --- canonical contradiction distinction ---------------------------------------


def test_different_canonical_ids_are_a_contradiction() -> None:
    left = assertion(
        "A1", object_kind="CANONICAL_ENTITY_REF", canonical_entity_id="VG:DEVATA:AGNIH"
    )
    right = assertion(
        "B1", object_kind="CANONICAL_ENTITY_REF", canonical_entity_id="VG:DEVATA:INDRAH"
    )
    assert canonical_entity_contradiction(left, right) is True


def test_omission_is_not_a_canonical_contradiction() -> None:
    left = assertion(
        "A1", object_kind="CANONICAL_ENTITY_REF", canonical_entity_id="VG:DEVATA:AGNIH"
    )
    right = assertion("B1", object_kind="CANONICAL_ENTITY_REF", canonical_entity_id=None)
    assert canonical_entity_contradiction(left, right) is False


def test_same_canonical_target_under_two_predicates_is_not_a_contradiction() -> None:
    left = assertion(
        "A1",
        predicate="INVOKES",
        object_kind="CANONICAL_ENTITY_REF",
        canonical_entity_id="VG:DEVATA:INDRAH",
    )
    right = assertion(
        "B1",
        predicate="PRAISES",
        object_kind="CANONICAL_ENTITY_REF",
        canonical_entity_id="VG:DEVATA:INDRAH",
    )
    assert canonical_entity_contradiction(left, right) is False


# --- no-claim disagreement classification --------------------------------------


def test_supported_assertion_against_no_claim() -> None:
    assert (
        no_claim_assessment([OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE])
        is NoClaimAssessment.SUPPORTED_CLAIM_VS_OMISSION
    )


def test_unsupported_assertion_against_no_claim() -> None:
    assert (
        no_claim_assessment([OneSidedAssessment.UNSUPPORTED_EXTRACTION])
        is NoClaimAssessment.UNSUPPORTED_CLAIM_VS_NOCLAIM
    )


def test_ambiguous_assertion_against_no_claim() -> None:
    assert (
        no_claim_assessment([OneSidedAssessment.PREDICATE_POLICY_AMBIGUITY])
        is NoClaimAssessment.AMBIGUOUS_CLAIM_VS_NOCLAIM
    )


def test_supported_claim_outranks_a_co_occurring_unsupported_one() -> None:
    assert (
        no_claim_assessment(
            [
                OneSidedAssessment.UNSUPPORTED_EXTRACTION,
                OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE,
            ]
        )
        is NoClaimAssessment.SUPPORTED_CLAIM_VS_OMISSION
    )


# --- severity v2 taxonomy ------------------------------------------------------


def test_canonical_contradiction_is_critical() -> None:
    assert (
        severity_v2(AlignmentCategory.TARGET_DIFFERENCE, canonical_contradiction=True)
        is SeverityV2.CRITICAL
    )


def test_integrity_and_ontology_failures_are_critical() -> None:
    assert severity_v2(AlignmentCategory.A_ONLY, integrity_failure=True) is SeverityV2.CRITICAL
    assert severity_v2(AlignmentCategory.A_ONLY, ontology_violation=True) is SeverityV2.CRITICAL


def test_unsupported_extraction_is_high() -> None:
    assert (
        severity_v2(AlignmentCategory.A_ONLY, one_sided=OneSidedAssessment.UNSUPPORTED_EXTRACTION)
        is SeverityV2.HIGH
    )


def test_supported_emit_vs_omit_is_medium_not_high() -> None:
    """The old comparator scored this HIGH; omission is not contradiction."""
    assert (
        severity_v2(
            AlignmentCategory.A_ONLY, one_sided=OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE
        )
        is SeverityV2.MEDIUM
    )


def test_alternate_valid_evidence_anchor_is_low() -> None:
    assert (
        severity_v2(
            AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE,
            anchor=AnchorAssessment.SAME_SEMANTIC_SUPPORT_ALTERNATE_SPAN,
        )
        is SeverityV2.LOW
    )


def test_broader_versus_narrower_valid_span_is_low() -> None:
    assert (
        severity_v2(
            AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE,
            anchor=AnchorAssessment.BROADER_VS_NARROWER_VALID_SPAN,
        )
        is SeverityV2.LOW
    )


# --- diagnostic set calculation ------------------------------------------------


def test_stable_core_requires_both_runs_to_emit() -> None:
    assert diagnostic_set_for(AlignmentCategory.EXACT_ASSERTION) is DiagnosticSet.STABLE_CORE
    assert (
        diagnostic_set_for(AlignmentCategory.A_ONLY, OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE)
        is not DiagnosticSet.STABLE_CORE
    )


def test_one_run_supported_calculation() -> None:
    assert (
        diagnostic_set_for(AlignmentCategory.B_ONLY, OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE)
        is DiagnosticSet.ONE_RUN_SUPPORTED
    )


def test_policy_ambiguity_classification_schema() -> None:
    for assessment in (
        OneSidedAssessment.PREDICATE_POLICY_AMBIGUITY,
        OneSidedAssessment.OBJECT_POLICY_AMBIGUITY,
        OneSidedAssessment.PLAUSIBLE_BUT_OPTIONAL,
    ):
        assert (
            diagnostic_set_for(AlignmentCategory.A_ONLY, assessment)
            is DiagnosticSet.POLICY_AMBIGUOUS
        )


def test_suspect_and_expert_required_sets() -> None:
    assert (
        diagnostic_set_for(AlignmentCategory.A_ONLY, OneSidedAssessment.UNSUPPORTED_EXTRACTION)
        is DiagnosticSet.SUSPECT_ASSERTION
    )
    assert (
        diagnostic_set_for(AlignmentCategory.A_ONLY, OneSidedAssessment.EXPERT_REQUIRED)
        is DiagnosticSet.EXPERT_REQUIRED
    )
    assert diagnostic_set_for(AlignmentCategory.UNRESOLVED) is DiagnosticSet.EXPERT_REQUIRED


# --- no candidate promotion ----------------------------------------------------


def test_stable_core_stays_a_review_candidate() -> None:
    label, lifecycle = candidate_provenance_label(DiagnosticSet.STABLE_CORE)
    assert label == "REPLICATION_SUPPORTED_MODEL_CANDIDATE"
    assert lifecycle == "CANDIDATE_NEEDS_REVIEW"


def test_no_diagnostic_set_is_ever_accepted_knowledge() -> None:
    for diagnostic in DiagnosticSet:
        _, lifecycle = candidate_provenance_label(diagnostic)
        assert lifecycle == "CANDIDATE_NEEDS_REVIEW"


def test_audit_manifest_declares_no_gold_and_no_promotion() -> None:
    adjudication = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    assert adjudication["human_gold"] is False
    assert adjudication["canonical_promotion"] is False


# --- no historical heuristic truth usage ---------------------------------------


def test_audit_declares_its_truth_rules() -> None:
    rules = " ".join(json.loads(ADJUDICATION.read_text(encoding="utf-8"))["truth_rules"]).casefold()
    assert "no human gold exists." in rules
    for forbidden in ("heuristic", "sol silver", "devata", "pretrained"):
        assert forbidden in rules


def test_audit_excludes_every_non_evidence_truth_source() -> None:
    excluded = json.loads(ADJUDICATION.read_text(encoding="utf-8"))["audit_scope"][
        "excluded_truth_sources"
    ]
    text = " ".join(excluded).casefold()
    for forbidden in ("heuristic", "sol silver", "devata", "pretrained", "self-agreement"):
        assert forbidden in text


def test_audit_compares_only_the_two_sealed_runs() -> None:
    runs = json.loads(ADJUDICATION.read_text(encoding="utf-8"))["audit_scope"]["runs_compared"]
    assert runs == [
        "vedagraph-rigveda-semantic-luna-v3.1-regression",
        "vedagraph-rigveda-semantic-luna-v3.1-508",
    ]


# --- run-level emission regime -------------------------------------------------


def regime(assertions: int, no_claim: int, action: int, passages: int = 60) -> EmissionRegime:
    """Build one run's emission regime for regime tests."""
    return EmissionRegime(
        passages=passages,
        assertions=assertions,
        no_claim_passages=no_claim,
        predicate_counts={"DESCRIBES_ACTION": action, "REQUESTS": assertions - action},
    )


def test_regime_rates_and_shares() -> None:
    run = regime(assertions=57, no_claim=10, action=21)
    assert run.density == 57 / 60
    assert run.no_claim_rate == 10 / 60
    assert run.share_of("DESCRIBES_ACTION") == 21 / 57
    assert run.share_of("ABSENT_PREDICATE") == 0.0


def test_empty_regime_does_not_divide_by_zero() -> None:
    run = EmissionRegime(passages=0, assertions=0, no_claim_passages=0, predicate_counts={})
    assert run.density == 0.0
    assert run.no_claim_rate == 0.0
    assert run.share_of("REQUESTS") == 0.0


def test_one_sided_predicate_skew_is_improbable() -> None:
    assert exchangeable_one_sided_probability(21, 0) < 1e-5


def test_shared_predicate_use_is_not_a_skew() -> None:
    assert exchangeable_one_sided_probability(12, 9) == 1.0


def test_no_occurrences_is_not_a_skew() -> None:
    assert exchangeable_one_sided_probability(0, 0) == 1.0


def test_regime_divergence_detects_the_observed_split() -> None:
    """A 21-vs-0 DESCRIBES_ACTION split with a 0.47 no-claim gap is run-level."""
    assert (
        regime_divergence(
            regime(assertions=57, no_claim=10, action=21),
            regime(assertions=33, no_claim=38, action=0),
            predicate="DESCRIBES_ACTION",
        )
        is True
    )


def test_similar_runs_do_not_diverge() -> None:
    assert (
        regime_divergence(
            regime(assertions=50, no_claim=12, action=10),
            regime(assertions=48, no_claim=14, action=9),
            predicate="DESCRIBES_ACTION",
        )
        is False
    )


# --- audit output invariants ---------------------------------------------------


def test_diagnosis_manifest_reports_no_contradiction_or_integrity_failure() -> None:
    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert data["summary"]["revised_passage_severity"]["CRITICAL"] == 0
    assert data["custody"]["packet_hash_mismatches"] == 0
    assert data["custody"]["receipt_failures"] == 0


def test_diagnosis_manifest_regime_matches_sealed_counts() -> None:
    regimes = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))["summary"]["emission_regime"]
    assert regimes["a"]["passages"] == 60
    assert regimes["b"]["passages"] == 60
    assert regimes["a"]["predicate_counts"].get("DESCRIBES_ACTION", 0) == 21
    assert regimes["b"]["predicate_counts"].get("DESCRIBES_ACTION", 0) == 0
    assert regimes["regime_divergence"] is True


def test_root_failure_distribution_covers_every_non_exact_alignment() -> None:
    summary = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))["summary"]
    diagnosed = sum(item["count"] for item in summary["failure_modes"].values())
    non_exact = sum(
        count
        for category, count in summary["alignment_counts"].items()
        if category != AlignmentCategory.EXACT_ASSERTION.value
    )
    assert diagnosed == non_exact
