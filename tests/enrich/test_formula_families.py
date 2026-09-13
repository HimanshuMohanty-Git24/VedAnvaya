"""Tests for the formula family layer.

Two halves, and they check different things.

The synthetic half builds tiny artifacts by hand -- a handful of formula rows and their
occurrence rows -- so that exactly one rule is in play and a failure names the rule that
broke. These are *artifact* rows, not a corpus: this layer reads what the Formula stage
wrote, so a synthetic input is a list of dicts and there is no transliteration, no share cap
and no padding to arrange.

The real-artifact half asserts invariants and accounting identities, never measured counts.
Pinning "720 families" here would turn every future corpus correction into a test failure
that says nothing; pinning "every member is either a core or contains one" and "members plus
unfamilied equals the formulas read" catches the regressions that would actually matter.

Two tests exist only to defend determinism, because it is the property most easily lost and
least visibly lost. One builds twice and compares bytes. The other permutes both input
artifacts and compares bytes, which is the test that would have caught a representative
chosen by ``max()`` over an unsorted dict.
"""

from __future__ import annotations

import itertools
import pathlib
import random
from typing import Any

import orjson
import pytest

from vedagraph.enrich.build import (
    FORMULA_OCCURRENCES_FILE,
    FORMULAS_FILE,
    PARALLELS_FILE,
    read_artifact,
)
from vedagraph.enrich.formula_families import (
    CLOSED_CLASS_ABOVE_GRAMMAR_LINE,
    DERIVATION_METHOD,
    FAMILY_MATCH_LEVEL,
    MAX_FAMILY_EVIDENCE_SPANS,
    MEMBERSHIP_METHOD_CORE,
    MEMBERSHIP_METHOD_EXPANSION,
    MEMBERSHIP_METHOD_VARIANT,
    MIN_FAMILY_MEMBERS,
    VARIANT_SIMILARITY_FLOOR,
    FormulaFamilyMemberRow,
    FormulaFamilyRow,
    MemberRole,
    build_formula_families,
    recommend_removals,
)
from vedagraph.enrich.provenance import AssertionState, TrustClass
from vedagraph.enrich.surfaces import MatchLevel

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Seed for the input-permutation test. Fixed so a failure is reproducible.
SHUFFLE_SEED = 20260909


# ---------------------------------------------------------------------------
# Synthetic artifact helpers
# ---------------------------------------------------------------------------


def _formula(normalized: str, passages: list[str], *, display: str = "") -> dict[str, Any]:
    """One Formula artifact row, with only the fields this layer reads.

    ``formula_id`` is derived from the text rather than passed in, so a test never has to
    keep two identifiers in step, and the ids are stable across a permuted input.
    """
    vedas = sorted({key.split(":")[1] for key in passages})
    counts: dict[str, int] = {}
    for key in passages:
        veda = key.split(":")[1]
        counts[veda] = counts.get(veda, 0) + 1
    return {
        "formula_id": f"F:{normalized.replace(' ', '_')}",
        "normalized": normalized,
        "display_form": display or normalized,
        "word_count": len(normalized.split()),
        "mantra_count": len(set(passages)),
        "vedas": vedas,
        "veda_counts": counts,
        "cross_veda": len(vedas) > 1,
    }


def _occurrences(formula: dict[str, Any], passages: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "formula_id": formula["formula_id"],
            "passage_key": key,
            "veda": key.split(":")[1],
            "source_form": formula["display_form"],
            "method": "formula-occurrence-word-aligned-v1",
        }
        for key in passages
    ]


def _artifact(
    spec: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a formula artifact and its occurrence artifact from ``{normalized: passages}``."""
    formulas: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    for normalized, passages in spec.items():
        row = _formula(normalized, passages)
        formulas.append(row)
        occurrences.extend(_occurrences(row, passages))
    return formulas, occurrences


def _rv(*ordinals: int) -> list[str]:
    return [f"VG:RV:SAK:M01:S001:V{ordinal:03d}" for ordinal in ordinals]


def _sv(*ordinals: int) -> list[str]:
    return [f"VG:SV:KAU:CHANDA:P01:D01:V{ordinal:02d}" for ordinal in ordinals]


def _by_core(rows: list[FormulaFamilyRow]) -> dict[str, FormulaFamilyRow]:
    return {row.representative_normalized: row for row in rows}


def _members_of(
    rows: list[FormulaFamilyMemberRow], family: FormulaFamilyRow
) -> list[FormulaFamilyMemberRow]:
    return [row for row in rows if row.family_id == family.family_id]


# ---------------------------------------------------------------------------
# What makes a family
# ---------------------------------------------------------------------------


def test_a_formula_in_no_containment_relation_is_left_unfamilied() -> None:
    formulas, occurrences = _artifact({"agnim ile": _rv(1, 2, 3), "somam pibatu": _rv(4, 5, 6)})
    families, members, report = build_formula_families(formulas, occurrences)
    assert families == []
    assert members == []
    assert report.rejected["formula_in_no_containment_relation"] == 2


def test_containment_makes_a_family_even_when_occurrence_sets_barely_overlap() -> None:
    """The commonest refrain in the corpus has this exact shape, at a coverage of 0.032."""
    formulas, occurrences = _artifact(
        {
            "pata svastibhih": _rv(*range(1, 31)),
            "yuyam pata svastibhih": _rv(1, 2, 3),
        }
    )
    families, members, _ = build_formula_families(formulas, occurrences)
    assert len(families) == 1
    assert families[0].representative_normalized == "pata svastibhih"
    assert families[0].member_count == 2
    assert {row.role for row in members} == {str(MemberRole.CORE), str(MemberRole.EXPANSION)}


def test_a_family_needs_more_than_one_member() -> None:
    formulas, occurrences = _artifact({"agnim ile": _rv(1, 2, 3)})
    families, _, _ = build_formula_families(formulas, occurrences)
    assert families == []
    assert MIN_FAMILY_MEMBERS == 2


def test_two_formulas_joined_by_a_shared_container_are_one_family() -> None:
    """Two distinct cores meeting inside one longer phrase: 157 real families do this."""
    formulas, occurrences = _artifact(
        {
            "tasya devasya": _rv(1, 2, 3, 4),
            "ya evam vidvamsam": _rv(5, 6, 7),
            "tasya devasya kruddhasya ya evam vidvamsam": _rv(1, 5),
        }
    )
    families, members, report = build_formula_families(formulas, occurrences)
    assert len(families) == 1
    assert families[0].member_count == 3
    assert families[0].core_count == 2
    assert families[0].secondary_core_count == 1
    assert report.rejected["secondary_core_below_variant_similarity_floor"] == 1
    roles = {row.normalized: row.role for row in _members_of(members, families[0])}
    assert roles["tasya devasya"] == str(MemberRole.CORE)
    assert roles["ya evam vidvamsam"] == str(MemberRole.CORE)
    assert roles["tasya devasya kruddhasya ya evam vidvamsam"] == str(MemberRole.EXPANSION)


def test_word_division_does_not_split_a_family() -> None:
    """Containment runs on the collapsed form, so a differently-divided sub-span still joins."""
    formulas, occurrences = _artifact(
        {
            "devir abhistaye": _rv(1, 2, 3),
            "de virabhistaye somam": _rv(1, 2),
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    assert len(families) == 1
    assert families[0].member_count == 2


def test_two_formulas_collapsing_to_one_identity_is_an_error() -> None:
    formulas, occurrences = _artifact({"agnim ile": _rv(1, 2, 3)})
    twin = dict(formulas[0])
    twin["formula_id"] = "F:twin"
    twin["normalized"] = "agni mile"
    with pytest.raises(ValueError, match="collapsed identity"):
        build_formula_families([*formulas, twin], occurrences)


# ---------------------------------------------------------------------------
# The representative
# ---------------------------------------------------------------------------


def test_the_representative_is_the_widest_recurring_member() -> None:
    formulas, occurrences = _artifact(
        {
            "agnim ile purohitam": _rv(1, 2),
            "agnim ile": _rv(1, 2, 3, 4, 5),
            "agnim ile purohitam yajnasya": _rv(1),
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    assert families[0].representative_normalized == "agnim ile"
    assert families[0].min_word_count == 2
    assert families[0].max_word_count == 4


def test_the_representative_breaks_a_tie_on_length_then_on_the_form_itself() -> None:
    """Equal mantra counts must not let the choice fall through to input order."""
    formulas, occurrences = _artifact(
        {
            "bbbb cccc dddd": _rv(1, 2, 3),
            "aaaa eeee": _rv(1, 2, 3),
            "aaaa eeee bbbb cccc dddd": _rv(1, 2, 3),
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    # Both two-member candidates have three mantras; the shorter collapsed form wins.
    assert families[0].representative_normalized == "aaaa eeee"


def test_no_member_is_ever_strictly_contained_in_the_representative() -> None:
    """The minimality the rank key is supposed to deliver, checked on the real artifact."""
    families, members, report = _real()
    assert "member_contained_in_representative" not in report.rejected
    cores = {row.family_id: row.normalized for row in members if row.role == str(MemberRole.CORE)}
    assert len(cores) <= len(families)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_an_expansion_links_to_its_immediate_parent_not_to_the_core() -> None:
    formulas, occurrences = _artifact(
        {
            "usasa suryena": _rv(1, 2, 3, 4),
            "sajosasa usasa suryena": _rv(1, 2, 3),
            "sajosasa usasa suryena ca": _rv(1, 2),
        }
    )
    families, members, _ = build_formula_families(formulas, occurrences)
    assert families[0].containment_depth == 3
    links = {row.normalized: row.linked_formula_id for row in members}
    assert links["sajosasa usasa suryena"] == "F:usasa_suryena"
    assert links["sajosasa usasa suryena ca"] == "F:sajosasa_usasa_suryena"


def test_a_second_spelling_of_a_core_is_a_variant_not_a_second_core() -> None:
    """``vayaṃ dviṣmas`` beside ``vayaṃ dviṣmaḥ``: neither contains the other."""
    formulas, occurrences = _artifact(
        {
            "yo asman dvesti": _rv(*range(1, 12)),
            "vayam dvismah": _rv(1, 2, 3, 4, 5),
            "vayam dvismas": _rv(6, 7, 8),
            "yo asman dvesti vayam dvismah": _rv(1, 2),
            "yo asman dvesti vayam dvismas": _rv(6, 7),
        }
    )
    families, members, _ = build_formula_families(formulas, occurrences)
    assert len(families) == 1
    roles = {row.normalized: row.role for row in members}
    assert roles["yo asman dvesti"] == str(MemberRole.CORE)
    assert roles["vayam dvismah"] == str(MemberRole.CORE)
    assert roles["vayam dvismas"] == str(MemberRole.VARIANT)
    variant = next(row for row in members if row.role == str(MemberRole.VARIANT))
    assert variant.similarity >= VARIANT_SIMILARITY_FLOOR
    assert variant.match_level == str(MatchLevel.SANDHI_INSENSITIVE)


def test_containment_classifies_every_member_of_every_real_family() -> None:
    """The property the whole taxonomy rests on: nothing is left over."""
    _, members, report = _real()
    assert "member_unclassified_by_containment" not in report.rejected
    assert {row.role for row in members} <= {str(role) for role in MemberRole}


def test_each_role_carries_its_own_method_and_the_right_confidence() -> None:
    _, members, _ = _real()
    expected = {
        str(MemberRole.CORE): MEMBERSHIP_METHOD_CORE,
        str(MemberRole.EXPANSION): MEMBERSHIP_METHOD_EXPANSION,
        str(MemberRole.VARIANT): MEMBERSHIP_METHOD_VARIANT,
    }
    for row in members:
        assert row.provenance.method == expected[row.role]
        if row.role == str(MemberRole.EXPANSION):
            assert row.similarity == 1.0
        if row.role == str(MemberRole.VARIANT):
            assert VARIANT_SIMILARITY_FLOOR <= row.similarity <= 1.0


# ---------------------------------------------------------------------------
# Cross-Veda spread is a family property
# ---------------------------------------------------------------------------


def test_family_veda_counts_are_a_union_of_mantras_not_a_sum_of_members() -> None:
    """Members overlap by construction; summing would inflate every family."""
    formulas, occurrences = _artifact(
        {
            "somam pibatu": [*_rv(1, 2, 3), *_sv(1)],
            "indra somam pibatu": [*_rv(1, 2), *_sv(1)],
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    family = families[0]
    assert family.mantra_count == 4
    assert family.veda_counts == {"RV": 3, "SV": 1}
    assert family.veda_span == 2
    assert family.cross_veda is True
    # Seven occurrence rows across two members for four distinct mantras: the
    # double-counting the family layer exists to resolve, reported rather than hidden.
    assert family.occurrence_count == 7


def test_a_family_reaches_a_veda_none_of_its_members_reaches_alone() -> None:
    formulas, occurrences = _artifact(
        {
            "somam pibatu": _rv(1, 2, 3),
            "somam pibatu indra": _sv(1, 2, 3),
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    assert families[0].vedas == ("RV", "SV")
    assert formulas[0]["vedas"] == ["RV"]
    assert formulas[1]["vedas"] == ["SV"]


def test_representative_coverage_falls_below_one_when_a_core_misses_a_mantra() -> None:
    formulas, occurrences = _artifact(
        {
            "tasya devasya": _rv(1, 2, 3, 4),
            "ya evam vidvamsam": _rv(9),
            "tasya devasya ya evam vidvamsam": _rv(1, 9),
        }
    )
    families, _, _ = build_formula_families(formulas, occurrences)
    assert families[0].mantra_count == 5
    assert families[0].representative_coverage == pytest.approx(4 / 5)


def test_parallel_corroboration_needs_a_cross_veda_pair_inside_the_family() -> None:
    formulas, occurrences = _artifact(
        {
            "somam pibatu": [*_rv(1), *_sv(1)],
            "indra somam pibatu": [*_rv(1), *_sv(1)],
        }
    )
    parallels = [{"subject_key": _sv(1)[0], "object_key": _rv(1)[0]}]
    with_parallel, _, _ = build_formula_families(formulas, occurrences, parallels)
    without, _, _ = build_formula_families(formulas, occurrences, [])
    assert with_parallel[0].parallel_corroborated is True
    assert without[0].parallel_corroborated is False


def test_a_single_veda_family_is_never_corroborated() -> None:
    formulas, occurrences = _artifact(
        {"somam pibatu": _rv(1, 2, 3), "indra somam pibatu": _rv(1, 2)}
    )
    parallels = [{"subject_key": _rv(1)[0], "object_key": _rv(2)[0]}]
    families, _, _ = build_formula_families(formulas, occurrences, parallels)
    assert families[0].cross_veda is False
    assert families[0].parallel_corroborated is False


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def _payload(families: list[FormulaFamilyRow], members: list[FormulaFamilyMemberRow]) -> bytes:
    rows = [row.as_row() for row in families] + [row.as_row() for row in members]
    return b"".join(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n" for row in rows)


def test_two_runs_over_one_artifact_are_byte_identical() -> None:
    formulas, occurrences = _artifact(
        {
            "usasa suryena": _rv(1, 2, 3, 4),
            "sajosasa usasa suryena": _rv(1, 2, 3),
            "sajosasa usasa suryena ca": [*_rv(1, 2), *_sv(1)],
            "vayam dvismah": _rv(5, 6, 7),
            "yo asman dvesti vayam dvismah": _rv(5, 6),
        }
    )
    first = build_formula_families(formulas, occurrences)
    second = build_formula_families(formulas, occurrences)
    assert _payload(first[0], first[1]) == _payload(second[0], second[1])


def test_the_representative_does_not_depend_on_input_order() -> None:
    """Every permutation of a family's rows must name the same core.

    Exhaustive over permutations rather than sampled, because the failure this guards
    against -- a ``max()`` or a ``set`` deciding a tie -- shows up on one specific ordering
    and a sampled test would find it only sometimes. The family is built so that two members
    tie on mantra count, which is the only situation in which order could matter.
    """
    spec = {
        "aaaa bbbb": _rv(1, 2, 3),
        "cccc dddd": _rv(4, 5, 6),
        "aaaa bbbb cccc dddd": _rv(1, 4),
        "eeee aaaa bbbb cccc dddd": _rv(1),
    }
    formulas, occurrences = _artifact(spec)
    baseline = build_formula_families(formulas, occurrences)
    assert len(baseline[0]) == 1
    for permutation in itertools.permutations(range(len(formulas))):
        permuted = [formulas[index] for index in permutation]
        families, members, _ = build_formula_families(permuted, occurrences)
        assert families[0].representative_normalized == (baseline[0][0].representative_normalized)
        assert _payload(families, members) == _payload(baseline[0], baseline[1])


def test_a_permuted_real_artifact_produces_byte_identical_output() -> None:
    formulas = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    occurrences = read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE)
    if not formulas:
        pytest.skip("enrichment artifacts not built")
    baseline = build_formula_families(formulas, occurrences)
    rng = random.Random(SHUFFLE_SEED)
    shuffled_formulas, shuffled_occurrences = list(formulas), list(occurrences)
    rng.shuffle(shuffled_formulas)
    rng.shuffle(shuffled_occurrences)
    permuted = build_formula_families(shuffled_formulas, shuffled_occurrences)
    assert _payload(permuted[0], permuted[1]) == _payload(baseline[0], baseline[1])


def test_output_is_sorted_by_content_not_by_rank() -> None:
    """A content ordering, so adding one formula upstream does not reshuffle the diff."""
    families, members, _ = _real()
    identities = [row.representative_normalized.replace(" ", "") for row in families]
    assert identities == sorted(identities)
    grouped = [row.family_id for row in members]
    assert len(set(grouped)) == len(families)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_every_row_carries_a_complete_provenance_envelope() -> None:
    families, members, _ = _real()
    for row in [*families, *members]:
        provenance = row.provenance
        assert provenance.trust is TrustClass.DETERMINISTIC_DERIVED
        assert provenance.state is AssertionState.ACCEPTED
        assert provenance.evidence
        assert provenance.run_id
        assert not provenance.model
        assert 0.0 <= provenance.score <= 1.0
        for span in provenance.evidence:
            assert span.locator
            assert span.surface
            assert span.quote


def test_family_evidence_proves_the_cross_veda_claim_from_the_node_alone() -> None:
    """Every Veda a family claims must appear in the family's own evidence spans.

    The regression this pins: evidence drawn from the core alone cannot prove a Veda that
    only a non-core member reaches, and a four-Veda family then shipped three-Veda evidence.
    """
    families, _, _ = _real()
    multi = [row for row in families if row.veda_span >= 2]
    assert multi
    for row in families:
        vedas = {span.locator.split(":")[1] for span in row.provenance.evidence}
        assert vedas <= set(row.vedas)
        assert len(row.provenance.evidence) <= MAX_FAMILY_EVIDENCE_SPANS
        assert len(vedas) == min(row.veda_span, MAX_FAMILY_EVIDENCE_SPANS)


def test_every_member_row_names_the_surface_it_was_measured_on() -> None:
    _, members, _ = _real()
    assert {row.match_level for row in members} == {str(FAMILY_MATCH_LEVEL)}
    assert FAMILY_MATCH_LEVEL is MatchLevel.SANDHI_INSENSITIVE


def test_the_derivation_method_is_named_on_every_family() -> None:
    families, _, _ = _real()
    assert {row.derivation_method for row in families} == {DERIVATION_METHOD}


# ---------------------------------------------------------------------------
# The removal recommendation
# ---------------------------------------------------------------------------


def test_the_recommendation_flags_a_content_word_plus_a_grammar_token() -> None:
    formulas, _ = _artifact(
        {
            "no mitravaruna": _rv(1, 2, 3),
            "agnim hotaram": _rv(4, 5, 6),
            "no mitravaruna somam": _rv(1, 2),
        }
    )
    shares = {"no": 0.1075, "mitravaruna": 0.006, "agnim": 0.0145, "hotaram": 0.0029}
    recommendations = recommend_removals(formulas, {}, shares)
    assert [item.normalized for item in recommendations] == ["no mitravaruna"]
    assert recommendations[0].grammar_token == "no"
    assert recommendations[0].grammar_token_share == pytest.approx(0.1075)
    assert "MAX_FORMULA_CORPUS_SHARE" in recommendations[0].rule


def test_the_recommendation_never_touches_a_longer_formula() -> None:
    """At three words the same rule flags 314 real refrains, so it is out of scope."""
    formulas, _ = _artifact({"no mitravaruna somam": _rv(1, 2, 3)})
    assert recommend_removals(formulas, {}, {"no": 0.1075}) == ()


def test_indra_is_deliberately_absent_from_the_closed_class_set() -> None:
    assert "indra" not in CLOSED_CLASS_ABOVE_GRAMMAR_LINE
    assert {"ā", "na", "te", "tvā", "ca", "no", "pra", "sa"} == set(CLOSED_CLASS_ABOVE_GRAMMAR_LINE)


def test_the_recommendation_is_returned_and_never_applied() -> None:
    families, members, report = _real()
    recommended = {
        item.formula_id
        for item in recommend_removals(read_artifact(PROJECT_ROOT, FORMULAS_FILE), {}, _shares())
    }
    assert recommended
    still_present = {row.formula_id for row in members} & recommended
    assert still_present, "a recommended formula must still be in the layer, not deleted"
    assert report.notes["removal_recommendations"] == len(recommended)
    assert families


# ---------------------------------------------------------------------------
# The real artifact
# ---------------------------------------------------------------------------


def _shares() -> dict[str, float]:
    """Just enough of the corpus token shares to size the recommendation in a test."""
    return {
        "ā": 0.1821,
        "na": 0.1647,
        "te": 0.1490,
        "tvā": 0.1246,
        "ca": 0.1202,
        "no": 0.1075,
        "pra": 0.0861,
        "sa": 0.0827,
    }


@pytest.fixture(scope="module")
def _real_artifact() -> tuple[list[FormulaFamilyRow], list[FormulaFamilyMemberRow], Any]:
    formulas = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    occurrences = read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE)
    if not formulas:
        pytest.skip("enrichment artifacts not built")
    parallels = read_artifact(PROJECT_ROOT, PARALLELS_FILE)
    return build_formula_families(formulas, occurrences, parallels, _shares())


_CACHE: dict[str, Any] = {}


def _real() -> tuple[list[FormulaFamilyRow], list[FormulaFamilyMemberRow], Any]:
    """The real build, computed once for the whole module.

    A plain function rather than a fixture so the invariant tests can call it without
    every one of them taking a parameter it does not otherwise use.
    """
    if "built" not in _CACHE:
        formulas = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
        occurrences = read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE)
        if not formulas:
            pytest.skip("enrichment artifacts not built")
        parallels = read_artifact(PROJECT_ROOT, PARALLELS_FILE)
        _CACHE["built"] = build_formula_families(formulas, occurrences, parallels, _shares())
    result = _CACHE["built"]
    assert isinstance(result, tuple)
    return result


def test_real_artifact_accounts_for_every_formula_it_read() -> None:
    """Members plus unfamilied must equal the formulas read. Nothing may go missing."""
    _, members, report = _real()
    assert (
        len(members) + report.rejected["formula_in_no_containment_relation"]
        == report.notes["formulas_read"]
    )
    assert report.notes["formulas_accounted_for"] == report.notes["formulas_read"]


def test_real_artifact_reproduces_the_v1_substring_figure_on_the_identity_surface() -> None:
    """1,103 is V1's number and it is right; the audit that could not reproduce it
    measured ``normalized`` and ``display_form`` instead of the collapsed identity."""
    _, _, report = _real()
    assert report.notes["formulas_strictly_contained_in_another"] == 1103


def test_real_artifact_resolves_more_rows_than_it_leaves_for_the_three_veda_question() -> None:
    """The question the layer exists to answer must return fewer, better rows."""
    families, _, report = _real()
    formulas = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    before = sum(1 for row in formulas if len(row["vedas"]) >= 3)
    after = report.notes["families_reaching_three_or_more_vedas"]
    assert after < before
    assert after == sum(1 for row in families if row.veda_span >= 3)


def test_real_artifact_families_are_mostly_corroborated_by_the_parallel_layer() -> None:
    """A second opinion from a different derivation. A collapse here is the signal."""
    _, _, report = _real()
    cross = report.notes["cross_veda_families"]
    corroborated = report.notes["cross_veda_families_parallel_corroborated"]
    assert cross > 0
    assert corroborated / cross > 0.5


def test_real_artifact_never_puts_one_formula_in_two_families() -> None:
    _, members, _ = _real()
    seen: dict[str, str] = {}
    for row in members:
        previous = seen.setdefault(row.formula_id, row.family_id)
        assert previous == row.family_id


def test_real_artifact_gives_every_family_exactly_one_representative() -> None:
    families, members, _ = _real()
    for family in families:
        own = _members_of(members, family)
        assert len(own) == family.member_count
        assert sum(1 for row in own if row.formula_id == family.representative_formula_id) == 1
        assert family.core_count + family.expansion_count + family.variant_count == len(own)


def test_real_artifact_family_mantra_count_never_exceeds_its_occurrence_count() -> None:
    families, _, _ = _real()
    for family in families:
        assert 0 < family.mantra_count <= family.occurrence_count
        assert family.veda_span == len(family.vedas)
        assert 0.0 < family.representative_coverage <= 1.0


def test_real_artifact_display_strings_are_free_of_folding_sentinels() -> None:
    families, members, _ = _real()
    texts = [row.representative_normalized for row in families]
    texts += [row.representative_display_form for row in families]
    texts += [row.normalized for row in members]
    texts += [span.quote for row in families for span in row.provenance.evidence]
    for text in texts:
        assert not any(0xE000 <= ord(char) <= 0xF8FF for char in text), repr(text)
