"""The quarter-verse parallel layer: its fold, its reach, and what it refuses.

GAP-CROSS_VEDA-004. Parallels were whole-verse only, so a verse sharing one of its four
quarters with another verse was reported without saying which quarter or not reported at
all. These tests pin the three things that could make the new layer wrong without looking
wrong: the fold, the scope, and the grouping.
"""

from __future__ import annotations

import collections
import json
import pathlib

import pytest

from vedagraph.enrich.pada_parallels import (
    COMPARISON_SURFACE,
    GRANULARITY_PADA,
    GRANULARITY_VERSE,
    MIN_TOKENS,
    VEDA_SCOPE,
    PadaToken,
    assert_no_accent_ambiguity,
    build_pada_groups,
    build_pada_units,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOKENS = PROJECT_ROOT / "data" / "knowledge" / "rigveda_lexical_v1" / "tokens.jsonl"

_CACHE: dict[str, object] = {}


def _tokens() -> list[PadaToken]:
    if "tokens" not in _CACHE:
        if not TOKENS.exists():
            pytest.skip("Rigvedic token annotation not present")
        rows = []
        with TOKENS.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                rows.append(
                    PadaToken(
                        passage_key=str(row["passage_key"]),
                        pada=str(row["pada"]),
                        sequence=int(row["sequence"]),
                        surface=str(row["normalized_surface"]),
                    )
                )
        _CACHE["tokens"] = rows
    result = _CACHE["tokens"]
    assert isinstance(result, list)
    return result


def _built() -> tuple[tuple[object, ...], object]:
    if "built" not in _CACHE:
        _CACHE["built"] = build_pada_groups(build_pada_units(_tokens()))
    result = _CACHE["built"]
    assert isinstance(result, tuple)
    return result  # type: ignore[return-value]


def test_a_pada_is_its_tokens_in_sequence_order_not_in_file_order() -> None:
    """Assembly order is the one thing that would silently produce plausible nonsense."""
    scrambled = [
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 3, "purohitam"),
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "agnim"),
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 2, "īḷe"),
    ]
    units = build_pada_units(scrambled)
    assert units[0].text == "agnim īḷe purohitam"


def test_the_fold_is_the_declared_comparison_form_and_not_the_raw_transcription_fold() -> None:
    """BAD -> FAIL. The first version of this module called the raw fold and under-folded.

    ``fold_transcription_cross_script`` does not apply CROSS_SCRIPT_SEPARATOR_MARKS, so the
    annotation's univerbation marker ``+`` survived into the comparison key and split
    quarters that are the same line. The key must not carry it.
    """
    units = build_pada_units(
        [
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "tābhiḥ"),
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 2, "u"),
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 3, "+"),
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 4, "su"),
        ]
    )
    assert "+" not in units[0].comparison_key
    assert "+" in units[0].text, "the readable text keeps the annotation's own marker"


def test_the_acute_guard_refuses_an_accented_edition() -> None:
    """BAD -> FAIL. The IAST acute is both the palatal sibilant and the udatta.

    This annotation carries none, which is why the fold is safe here. Substitute an
    accented edition and the same fold silently merges accented and unaccented quarters, so
    the guard raises instead of folding.
    """
    clean = build_pada_units(
        [
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "śata"),
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 2, "agnim"),
        ]
    )
    assert assert_no_accent_ambiguity(clean) == 0

    accented = build_pada_units(
        [
            PadaToken("VG:RV:SAK:M01:S001:V002", "a", 1, "agánim"),
            PadaToken("VG:RV:SAK:M01:S001:V002", "a", 2, "íḷe"),
        ]
    )
    with pytest.raises(ValueError, match="U\\+0301"):
        assert_no_accent_ambiguity(accented)


def test_the_precomposed_sibilant_is_a_letter_and_survives_the_fold() -> None:
    """The other direction of the same trap: over-folding would merge sa and sha."""
    units = build_pada_units(
        [
            PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "śatam"),
            PadaToken("VG:RV:SAK:M01:S001:V001", "b", 1, "satam"),
        ]
    )
    keys = {unit.pada: unit.comparison_key for unit in units}
    assert keys["a"] != keys["b"]


def test_a_group_needs_two_mantras_not_two_padas_of_one_verse() -> None:
    """A verse repeating its own refrain is a fact about that verse, not a parallel."""
    same_verse = [
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "agnim"),
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 2, "īḷe"),
        PadaToken("VG:RV:SAK:M01:S001:V001", "c", 1, "agnim"),
        PadaToken("VG:RV:SAK:M01:S001:V001", "c", 2, "īḷe"),
    ]
    groups, _ = build_pada_groups(build_pada_units(same_verse))
    assert groups == ()

    two_verses = [
        *same_verse[:2],
        PadaToken("VG:RV:SAK:M01:S002:V005", "d", 1, "agnim"),
        PadaToken("VG:RV:SAK:M01:S002:V005", "d", 2, "īḷe"),
    ]
    groups, _ = build_pada_groups(build_pada_units(two_verses))
    assert len(groups) == 1
    assert groups[0].distinct_mantras == 2


def test_a_one_token_pada_is_refused() -> None:
    """One word is a lexical fact the mention layer already holds."""
    tokens = [
        PadaToken("VG:RV:SAK:M01:S001:V001", "a", 1, "indraḥ"),
        PadaToken("VG:RV:SAK:M01:S002:V001", "a", 1, "indraḥ"),
    ]
    groups, report = build_pada_groups(build_pada_units(tokens))
    assert groups == ()
    assert report.rejected["pada_below_token_floor"] == 2
    assert MIN_TOKENS == 2


def test_granularity_is_typed_distinctly_from_the_verse_layer() -> None:
    """The closure test's second clause, as a constant rather than as a convention."""
    assert GRANULARITY_PADA == "PADA"
    assert GRANULARITY_VERSE == "VERSE"
    assert GRANULARITY_PADA != GRANULARITY_VERSE


def test_every_group_row_states_its_single_corpus_reach() -> None:
    """A pada layer presented as corpus-wide is the useful-looking, untrue object."""
    groups, report = _built()
    assert VEDA_SCOPE == ("RV",)
    assert report.as_row()["veda_scope"] == ["RV"]  # type: ignore[union-attr]
    for group in groups[:50]:
        row = group.as_row()  # type: ignore[union-attr]
        assert row["veda_scope"] == ["RV"]
        assert row["veda_scope_reason"]
        assert row["granularity"] == GRANULARITY_PADA
        assert row["comparison_surface"] == COMPARISON_SURFACE


def test_the_real_annotation_produces_groups_and_no_group_merges_different_wordings() -> None:
    """GOOD -> PASS, and the over-fold direction measured rather than assumed.

    Under-folding splits one quarter into two groups; over-folding merges two quarters into
    one. The second is the dangerous one because it produces a *better looking* result, so
    it is measured: no group may contain two members whose readable text differs by
    anything other than word breaks and the annotation's own marker.
    """
    groups, report = _built()
    units = {unit.pada_key: unit for unit in build_pada_units(_tokens())}
    assert report.groups > 0  # type: ignore[union-attr]
    assert report.accent_ambiguous_padas == 0  # type: ignore[union-attr]
    merged = [
        group
        for group in groups
        if len(
            {
                "".join(units[key].text.replace("+", " ").split())
                for key in group.member_keys  # type: ignore[union-attr]
            }
        )
        > 1
    ]
    assert merged == [], f"{len(merged)} groups merge quarters that are not the same words"


def test_grouping_is_cheaper_than_the_pairs_it_implies() -> None:
    """Why this is a group layer: one refrain would otherwise cost thousands of edges."""
    groups, report = _built()
    memberships = report.memberships  # type: ignore[union-attr]
    implied = report.implied_verse_pairs  # type: ignore[union-attr]
    assert implied > memberships * 2
    biggest = max(groups, key=lambda group: group.member_count)  # type: ignore[union-attr]
    assert biggest.implied_verse_pairs() > 3_000


def test_the_layer_is_deterministic_over_a_permuted_input() -> None:
    """Row order must not reach the output: a group id is a function of its text."""
    tokens = _tokens()
    forward, _ = build_pada_groups(build_pada_units(tokens))
    reverse, _ = build_pada_groups(build_pada_units(list(reversed(tokens))))
    assert [group.as_row() for group in forward] == [group.as_row() for group in reverse]


def test_group_ids_are_unique_and_derived_from_the_comparison_key() -> None:
    groups, _ = _built()
    ids = [group.group_id for group in groups]  # type: ignore[union-attr]
    assert len(ids) == len(set(ids))
    duplicates = collections.Counter(
        group.comparison_key
        for group in groups  # type: ignore[union-attr]
    )
    assert all(count == 1 for count in duplicates.values())
