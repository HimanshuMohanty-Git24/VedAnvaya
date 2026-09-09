"""Derived statistics, the relationship matrix, and the invariant checks."""

from __future__ import annotations

import pathlib

from vedagraph.enrich.analytics import (
    PairStat,
    concept_by_veda,
    concept_connection_matrix,
    cross_veda_matrix,
    formula_sharing_matrix,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    TrustClass,
)
from vedagraph.enrich.records import (
    ConceptAssertionRow,
    FormulaRow,
    ParallelRow,
    veda_pair,
)
from vedagraph.enrich.validate import validate_artifacts

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_PROV = Provenance(
    trust=TrustClass.DETERMINISTIC_DERIVED,
    method="test",
    score=1.0,
    evidence=(EvidenceSpan("k", "SOURCE_EXACT", "text"),),
    state=AssertionState.ACCEPTED,
)


def _parallel(subject: str, obj: str, sv: str, ov: str, predicate: str) -> ParallelRow:
    return ParallelRow(
        predicate=predicate,
        subject_key=subject,
        object_key=obj,
        subject_veda=sv,
        object_veda=ov,
        veda_pair=veda_pair(sv, ov),
        match_level="SCRIPT_FOLDED",
        levels_reached=("SCRIPT_FOLDED",),
        similarity=1.0,
        token_jaccard=1.0,
        ngram_jaccard=1.0,
        lcs_ratio=1.0,
        edit_ratio=1.0,
        provenance=_PROV,
    )


def _assertion(passage: str, veda: str, concept: str) -> ConceptAssertionRow:
    return ConceptAssertionRow(
        passage_key=passage, veda=veda, concept_id=concept, confidence=0.9, provenance=_PROV
    )


def test_the_veda_pair_label_is_order_independent() -> None:
    """Otherwise RV-SV and SV-RV become two cells of a six-cell matrix."""
    assert veda_pair("SV", "RV") == veda_pair("RV", "SV") == "RV-SV"


def test_the_relationship_matrix_aggregates_by_pair_and_predicate() -> None:
    rows = [
        _parallel("a", "b", "RV", "SV", "EXACT_PARALLEL_OF"),
        _parallel("c", "d", "SV", "RV", "EXACT_PARALLEL_OF"),
        _parallel("e", "f", "RV", "AV", "NEAR_PARALLEL_OF"),
    ]
    matrix = cross_veda_matrix(rows)
    assert matrix["RV-SV"] == {"EXACT_PARALLEL_OF": 2, "distinct_pairs": 2}
    assert matrix["AV-RV"] == {"NEAR_PARALLEL_OF": 1, "distinct_pairs": 1}


def test_the_matrix_reports_distinct_pairs_so_mirrored_rows_are_not_double_counted() -> None:
    """A directed reuse row restates a symmetric one; the predicate columns cannot be summed.

    Live, this is 1,684 of the 3,368 RV-SV relationships, so a reader adding the columns
    counts every Samavedic borrowing twice.
    """
    rows = [
        _parallel("a", "b", "RV", "SV", "EXACT_PARALLEL_OF"),
        _parallel("b", "a", "SV", "RV", "REUSES_TEXT_FROM"),
    ]
    cell = cross_veda_matrix(rows)["RV-SV"]
    assert cell["EXACT_PARALLEL_OF"] + cell["REUSES_TEXT_FROM"] == 2
    assert cell["distinct_pairs"] == 1


def test_a_concept_bridges_a_pair_once_however_often_it_is_attested() -> None:
    """A concept in 900 RV passages and 2 YV ones is one bridge, not eighteen hundred."""
    rows = [_assertion(f"p{i}", "RV", "C1") for i in range(50)]
    rows += [_assertion("q1", "YV", "C1"), _assertion("q2", "YV", "C1")]
    assert concept_connection_matrix(rows) == {"RV-YV": 1}


def test_concept_distribution_reports_every_veda_a_concept_reaches() -> None:
    rows = [
        _assertion("p1", "RV", "C1"),
        _assertion("p2", "AV", "C1"),
        _assertion("p3", "RV", "C2"),
    ]
    by_concept = {row["concept_id"]: row for row in concept_by_veda(rows)}
    assert by_concept["C1"]["cross_veda"] is True
    assert by_concept["C1"]["veda_counts"] == {"AV": 1, "RV": 1}
    assert by_concept["C2"]["cross_veda"] is False


def test_formula_sharing_counts_each_veda_pair_a_formula_spans() -> None:
    formula = FormulaRow(
        formula_id="F1",
        normalized="x",
        display_form="x",
        word_count=2,
        char_count=12,
        occurrence_count=9,
        mantra_count=9,
        vedas=("RV", "SV", "AV"),
        veda_counts={"RV": 5, "SV": 2, "AV": 2},
        cross_veda=True,
        source_forms=("x",),
        derivation_method="test",
        provenance=_PROV,
    )
    assert formula_sharing_matrix([formula], []) == {"AV-RV": 1, "AV-SV": 1, "RV-SV": 1}


def test_lift_is_reported_alongside_the_marginals_it_depends_on() -> None:
    """A raw co-occurrence count is uninterpretable without both totals."""
    stat = PairStat("A", "B", support=10, subject_total=20, object_total=40, lift=2.5)
    row = stat.as_row()
    assert row["support"] == 10
    assert row["subject_total"] == 20 and row["object_total"] == 40
    assert row["lift"] == 2.5


# --- validation ------------------------------------------------------------------


def test_validation_rejects_an_edge_whose_endpoints_share_a_veda() -> None:
    rows = [_parallel("a", "b", "RV", "RV", "EXACT_PARALLEL_OF").as_row()]
    result = validate_artifacts(rows, [], [], [], [], [])
    assert not result.passed
    assert any(f.check == "cross_veda_pairs_span_two_vedas" for f in result.errors)


def test_validation_rejects_a_concept_assertion_with_no_concept_node() -> None:
    rows = [_assertion("p", "RV", "MISSING").as_row()]
    result = validate_artifacts([], [], [], [], rows, [])
    assert not result.passed
    assert any(f.check == "concept_assertions_resolve" for f in result.errors)


def test_validation_rejects_an_uncontrolled_predicate() -> None:
    row = _parallel("a", "b", "RV", "SV", "EXACT_PARALLEL_OF").as_row()
    row["predicate"] = "SYMBOLIZES"
    result = validate_artifacts([row], [], [], [], [], [])
    assert not result.passed
    assert any(f.check == "controlled_predicates" for f in result.errors)


def test_validation_rejects_an_edge_with_empty_evidence_in_either_encoding() -> None:
    """Artifacts carry a list; graph rows carry a JSON string. Both must be caught."""
    for empty in ([], "[]", ""):
        row = _parallel("a", "b", "RV", "SV", "EXACT_PARALLEL_OF").as_row()
        row["evidence"] = empty
        result = validate_artifacts([row], [], [], [], [], [])
        assert any(f.check == "parallels_carry_evidence" for f in result.errors), empty


def test_validation_rejects_a_model_row_marked_accepted() -> None:
    """Provenance blocks this at construction; validation blocks it in a hand-edited file."""
    row = _assertion("p", "RV", "C1").as_row()
    row["trust"] = str(TrustClass.LLM_EXTRACTED)
    row["state"] = str(AssertionState.ACCEPTED)
    row["model"] = "some-model"
    result = validate_artifacts([], [], [], [{"concept_id": "C1"}], [row], [])
    assert any(f.check == "llm_output_is_never_accepted" for f in result.errors)


def test_the_real_artifacts_pass_every_offline_invariant() -> None:
    from vedagraph.enrich.build import (
        CONCEPT_ASSERTIONS_FILE,
        CONCEPTS_FILE,
        FORMULA_OCCURRENCES_FILE,
        FORMULAS_FILE,
        PARALLELS_FILE,
        SEMANTIC_CANDIDATES_FILE,
        read_artifact,
    )

    parallels = read_artifact(PROJECT_ROOT, PARALLELS_FILE)
    if not parallels:
        import pytest

        pytest.skip("enrichment artifacts not built; run scripts/build_enrichment.py")

    result = validate_artifacts(
        parallels,
        read_artifact(PROJECT_ROOT, FORMULAS_FILE),
        read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE),
        read_artifact(PROJECT_ROOT, CONCEPTS_FILE),
        read_artifact(PROJECT_ROOT, CONCEPT_ASSERTIONS_FILE),
        read_artifact(PROJECT_ROOT, SEMANTIC_CANDIDATES_FILE),
    )
    assert result.passed, [f.as_dict() for f in result.errors]
    assert len(set(result.checks_run)) >= 20


def test_every_controlled_predicate_is_covered_by_the_live_relationship_checks() -> None:
    """A predicate missing here is checked as a node label and always reports zero.

    That is what happened to the fourteen semantic predicates: `validate_live` fell through
    to `MATCH (n:DESCRIBES)`, found no such label, and reported "wrote 280, database holds
    0" for 736 edges that had loaded correctly. Deriving the tuple fixes it; this test stops
    it from being hand-written again.
    """
    from vedagraph.enrich.predicates import CONTROLLED_PREDICATES, StructuralPredicate
    from vedagraph.enrich.validate import _ENRICHMENT_TYPES

    expected = CONTROLLED_PREDICATES - {str(StructuralPredicate.QA_ISSUE_ON)}
    assert set(_ENRICHMENT_TYPES) == expected
    for semantic in ("DESCRIBES", "INVOKES", "REQUESTS", "PRAISES", "CONTRASTS_WITH"):
        assert semantic in _ENRICHMENT_TYPES
