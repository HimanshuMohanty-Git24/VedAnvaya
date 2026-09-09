"""Provenance, comparison surfaces and the controlled predicate vocabulary."""

from __future__ import annotations

import pathlib

import pytest

from vedagraph.enrich.guards import top_k
from vedagraph.enrich.predicates import (
    CONTROLLED_PREDICATES,
    REFUSED_PREDICATES,
    NodeKind,
    check_signature,
    reuse_direction,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    TrustClass,
    stable_id,
)
from vedagraph.enrich.surfaces import (
    LEVEL_ORDER,
    MatchLevel,
    build_surfaces,
    reachable_levels,
    strongest_level,
)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_SPAN = (EvidenceSpan("VG:RV:SAK:M01:S001:V001", "SOURCE_EXACT", "agnim ile"),)


def _provenance(**overrides: object) -> Provenance:
    base: dict[str, object] = {
        "trust": TrustClass.DETERMINISTIC_DERIVED,
        "method": "test",
        "score": 0.5,
        "evidence": _SPAN,
    }
    base.update(overrides)
    return Provenance(**base)  # type: ignore[arg-type]


# --- provenance ------------------------------------------------------------------


def test_an_enrichment_record_without_evidence_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="requires evidence"):
        _provenance(evidence=())


def test_a_model_extracted_row_can_never_be_written_as_accepted() -> None:
    """The 'never make LLM output canonical' policy, enforced by the type."""
    with pytest.raises(ValueError, match="may not be ACCEPTED"):
        _provenance(
            trust=TrustClass.LLM_EXTRACTED,
            model="claude-opus-5",
            state=AssertionState.ACCEPTED,
        )


def test_a_model_name_is_required_for_llm_rows_and_forbidden_on_deterministic_ones() -> None:
    with pytest.raises(ValueError, match="model is required"):
        _provenance(trust=TrustClass.LLM_EXTRACTED)
    with pytest.raises(ValueError, match="model is required"):
        _provenance(model="claude-opus-5")


def test_score_outside_the_unit_interval_is_refused() -> None:
    with pytest.raises(ValueError, match="outside"):
        _provenance(score=1.4)


def test_edge_properties_are_all_neo4j_storable_scalars() -> None:
    props = _provenance().as_edge_properties()
    assert isinstance(props["evidence"], str), "Neo4j cannot store a nested map"
    assert props["evidence_count"] == 1
    assert set(props) >= {"trust", "method", "score", "evidence", "state", "pipeline_version"}


def test_stable_ids_are_deterministic_and_input_sensitive() -> None:
    assert stable_id("formula", "a", 1) == stable_id("formula", "a", 1)
    assert stable_id("formula", "a", 1) != stable_id("formula", "a", 2)


# --- surfaces --------------------------------------------------------------------


def test_a_cross_script_pair_can_never_claim_a_byte_level_match() -> None:
    """Latin and Devanagari share no code points, so the strong levels are unreachable."""
    same = reachable_levels("Latin", "Latin")
    cross = reachable_levels("Latin", "Devanagari")
    assert same == LEVEL_ORDER
    assert MatchLevel.SOURCE_EXACT not in cross
    assert MatchLevel.ACCENT_INSENSITIVE not in cross
    assert cross[0] is MatchLevel.SCRIPT_FOLDED


def test_devanagari_and_latin_readings_of_one_verse_match_once_script_folded() -> None:
    latin = build_surfaces("A", "RV", "Latin", "agním īḷe puróhitaṁ")
    devanagari = build_surfaces("B", "YV", "Devanagari", "अग्निम् ईळे पुरोहितं")
    level = strongest_level(latin, devanagari)
    assert level is MatchLevel.SCRIPT_FOLDED


def test_a_sandhi_written_verse_matches_only_at_the_word_boundary_free_level() -> None:
    """The Samaveda writes as one word what the Rigveda writes as two."""
    spaced = build_surfaces("A", "RV", "Latin", "devīr abhiṣṭaye")
    joined = build_surfaces("B", "SV", "Latin", "devīrabhiṣṭaye")
    assert strongest_level(spaced, joined) is MatchLevel.SANDHI_INSENSITIVE


def test_accent_notation_alone_does_not_prevent_a_match() -> None:
    accented = build_surfaces("A", "RV", "Latin", "a̱gnim ī̍ḻe")
    plain = build_surfaces("B", "AV", "Latin", "agnim īḻe")
    level = strongest_level(accented, plain)
    assert level is not None
    assert LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(MatchLevel.ACCENT_INSENSITIVE)


def test_a_fragment_too_short_to_be_distinctive_is_not_offered_for_matching() -> None:
    assert not build_surfaces("A", "RV", "Latin", "agnim").is_comparable()
    assert build_surfaces("B", "RV", "Latin", "agním īḷe puróhitaṁ yajñásya").is_comparable()


def test_unrelated_verses_reach_no_level() -> None:
    a = build_surfaces("A", "RV", "Latin", "agním īḷe puróhitaṁ yajñásya devám")
    b = build_surfaces("B", "AV", "Latin", "yé triṣaptā́ḥ pariyánti víśvā rūpā́ṇi")
    assert strongest_level(a, b) is None


# --- predicates ------------------------------------------------------------------


def test_the_predicate_vocabulary_is_closed_and_names_its_refusals() -> None:
    assert "EXACT_PARALLEL_OF" in CONTROLLED_PREDICATES
    assert "USES_FORMULA" in CONTROLLED_PREDICATES
    assert "ABOUT_CONCEPT" in CONTROLLED_PREDICATES
    for refused in ("CAUSES", "IDENTIFIES_WITH", "PROTECTS_FROM", "ELABORATES"):
        assert refused in REFUSED_PREDICATES
        assert refused not in CONTROLLED_PREDICATES


def test_every_refusal_carries_a_reason() -> None:
    for name, reason in REFUSED_PREDICATES.items():
        assert len(reason) > 40, f"{name} is refused without a usable reason"


def test_domain_and_range_are_enforced() -> None:
    check_signature("USES_FORMULA", NodeKind.PASSAGE, NodeKind.FORMULA)
    with pytest.raises(ValueError, match="object"):
        check_signature("USES_FORMULA", NodeKind.PASSAGE, NodeKind.CONCEPT)
    with pytest.raises(ValueError, match="subject"):
        check_signature("BROADER_THAN", NodeKind.PASSAGE, NodeKind.CONCEPT)


def test_an_uncontrolled_predicate_is_rejected_with_its_refusal_reason() -> None:
    with pytest.raises(ValueError, match="mythological narrative"):
        check_signature("CAUSES", NodeKind.PASSAGE, NodeKind.CONCEPT)
    with pytest.raises(ValueError, match="not a controlled"):
        check_signature("INVENTED_BY_A_STAGE", NodeKind.PASSAGE, NodeKind.CONCEPT)


def test_reuse_direction_is_asserted_only_where_the_corpus_establishes_it() -> None:
    """Samaveda-from-Rigveda is what the Samaveda is; every other pair stays undirected."""
    direction = reuse_direction("RV", "SV")
    assert direction is not None
    borrower, source, reason = direction
    assert (borrower, source) == ("SV", "RV")
    assert "Rigvedic verses" in reason
    assert reuse_direction("RV", "AV") is None
    assert reuse_direction("YV", "AV") is None


# --- guards ----------------------------------------------------------------------


def test_top_k_keeps_the_strongest_and_reports_what_it_dropped() -> None:
    result = top_k([(0.9, "a"), (0.5, "b"), (0.7, "c")], 2)
    assert result.kept == ("a", "c")
    assert result.dropped == 1


def test_top_k_breaks_ties_on_the_item_not_on_input_order() -> None:
    """Input order comes from dict iteration; letting it decide makes runs differ."""
    forward = top_k([(0.5, "b"), (0.5, "a")], 1)
    backward = top_k([(0.5, "a"), (0.5, "b")], 1)
    assert forward.kept == backward.kept == ("a",)
