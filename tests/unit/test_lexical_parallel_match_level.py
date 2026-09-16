"""The two-writer collision on EXACT_PARALLEL_OF, pinned. Wave 4, GAP-CROSS_VEDA-003.

256 of 1,006 ``EXACT_PARALLEL_OF`` edges served a reader a null ``match_level`` while carrying
the level under ``strongest_method``, because the predicate has two writers and only the
enrichment one knew the property existed. Every count taken over ``match_level`` was therefore
measuring one writer's output and reporting it as the predicate's.

The tests that matter here are the ones that stop the fix from becoming a conversion. The
lexical pipeline's method vocabulary overlaps the surface vocabulary by name in three places
and diverges in two, and the two that diverge are not weaker surfaces -- they are a different
axis. A row whose strongest method is ``LEMMA_SEQUENCE_EXACT`` is NOT identical at any text
surface, so every ``MatchLevel`` value is false of it. Asserting one would be exactly the
"never convert a normalization into an identity" failure.
"""

from __future__ import annotations

import pathlib

import pytest

from vedagraph.enrich.surfaces import LEVEL_ORDER, MatchLevel
from vedagraph.graph import lexical

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = PROJECT_ROOT / "data" / "knowledge" / "rigveda_lexical_v1" / "mantra_parallels.jsonl"


def test_every_mapped_method_names_a_real_surface_level() -> None:
    """The map's values must be members of the enum the property is read against.

    A string that merely looks like a level would load, serve, and silently fail every
    comparison against ``MatchLevel``.
    """
    for method, level in lexical._METHOD_TO_MATCH_LEVEL.items():
        assert isinstance(level, MatchLevel), f"{method} maps to a non-member {level!r}"
        assert level in LEVEL_ORDER


def test_the_map_is_a_rename_and_not_a_reinterpretation() -> None:
    """Each mapped pair must mean the same thing, which is why the names match.

    ``SOURCE_EXACT`` -> ``SOURCE_EXACT`` is the whole justification for copying the value
    across. The other two are the same claim under the other pipeline's older spelling. If a
    future edit added a pair whose two halves did not correspond, this is what refuses it.
    """
    assert lexical._METHOD_TO_MATCH_LEVEL == {
        "SOURCE_EXACT": MatchLevel.SOURCE_EXACT,
        "NFC_EXACT": MatchLevel.UNICODE_NORMALIZED,
        "ACCENTLESS_EXACT": MatchLevel.ACCENT_INSENSITIVE,
    }


@pytest.mark.parametrize("method", ["TOKEN_EXACT", "LEMMA_SEQUENCE_EXACT"])
def test_a_non_surface_method_is_never_given_a_level(method: str) -> None:
    """The boundary of the fix, asserted rather than left to the data.

    Token identity and lemma-sequence identity are not text surfaces. A pair reaching only
    one of them differs at every surface, so no level is true of it.
    """
    assert method not in lexical._METHOD_TO_MATCH_LEVEL


def test_the_generator_levels_or_types_absent_every_row_and_never_both() -> None:
    """Read from the real artifact: a unit test on the map could pass while the caller
    applied it in the wrong place, or not at all."""
    if not SOURCE.exists():
        pytest.skip("RV lexical parallel artifact not present in this checkout")
    rows = list(lexical.iter_exact_parallel_rels(PROJECT_ROOT))
    assert rows, "no rows produced, so this test proves nothing"
    for row in rows:
        has_level = bool(row.get("match_level"))
        has_absence = bool(row.get("match_level_absence"))
        assert has_level != has_absence, (
            f"{row['subject_key']} -> {row['object_key']} is "
            f"{'both levelled and typed absent' if has_level else 'neither'}"
        )
        assert row.get("parallel_id"), "every row needs an id under the one convention"
        if has_level:
            assert row["match_level"] in {str(level) for level in LEVEL_ORDER}


def test_the_id_convention_is_the_enrichment_one() -> None:
    """One namespace for the property, or the two writers collide again in a new way.

    Asserted against ``stable_id`` directly, so a future edit that mints ids some other way
    fails here rather than producing a second convention nobody notices.
    """
    if not SOURCE.exists():
        pytest.skip("RV lexical parallel artifact not present in this checkout")
    from vedagraph.enrich.provenance import stable_id

    rows = list(lexical.iter_exact_parallel_rels(PROJECT_ROOT))
    for row in rows[:25]:
        assert row["parallel_id"] == stable_id(
            "parallel", row["predicate"], row["subject_key"], row["object_key"]
        )
    assert len({row["parallel_id"] for row in rows}) == len(rows), "ids must be unique"


def test_the_exact_parallel_population_is_the_one_the_gap_recorded() -> None:
    """A fixture that drifts turns the rest of this file into a no-op.

    252 renamed and 4 typed absent is the whole of the 256 the registry recorded, so the
    split is pinned rather than trusted.
    """
    if not SOURCE.exists():
        pytest.skip("RV lexical parallel artifact not present in this checkout")
    exact = [
        row
        for row in lexical.iter_exact_parallel_rels(PROJECT_ROOT)
        if row["predicate"] == "EXACT_PARALLEL_OF"
    ]
    assert len(exact) == 256
    assert sum(1 for row in exact if row.get("match_level")) == 252
    assert sum(1 for row in exact if row.get("match_level_absence")) == 4
