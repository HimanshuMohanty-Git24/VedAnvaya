"""The alignment-confidence derivation, and the shapes it must refuse to grade.

GAP-TRANSLATION-005 asks for a per-translation alignment confidence where all 18,415 are
null. The risk in filling a field on eighteen thousand rows is that the fill is a default
wearing a value's clothes, so the derivation raises on any shape it does not recognise, and
these tests pin both directions.
"""

import importlib.util
import pathlib

import pytest

_MOD = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data/staging/final_closure_sprint/agent7/alignment_confidence.py"
)


def _load():
    """Import the derivation without running its ``main`` (which reads the live store)."""
    spec = importlib.util.spec_from_file_location("agent7_alignment_confidence", _MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def grade():
    if not _MOD.exists():
        pytest.skip("Agent 7 staging artifact not present")
    return _load().grade


# ------------------------------------------------------------------ GOOD, each branch ---
def test_a_reused_rendering_grades_as_reuse(grade) -> None:
    assert grade({"alignment_level": "MANTRA", "reuse_kind": "REUSED_RENDERING"}) == (
        "REUSED_SURFACE_IDENTICAL"
    )


def test_hymn_grain_is_the_158_population(grade) -> None:
    assert grade({"alignment_level": "HYMN"}) == "HYMN_GRAIN_ONLY"


def test_a_declared_range_grades_as_a_range(grade) -> None:
    assert grade({"alignment_level": "MANTRA_RANGE", "covers_canonical_keys": ["a", "b"]}) == (
        "DECLARED_RANGE"
    )


def test_an_address_verification_outranks_a_bare_locator(grade) -> None:
    assert grade({
        "alignment_level": "MANTRA",
        "address_verification": "checked against Griffith's own Rigveda rendering",
        "source_locator": "x",
        "snapshot_sha256": "deadbeef",
    }) == "CONTENT_VERIFIED_MANTRA"


def test_a_located_and_hashed_row_grades_as_source_labelled(grade) -> None:
    assert grade({
        "alignment_level": "MANTRA",
        "source_locator": "book page wyvbk12.htm, printed label '107'",
        "snapshot_sha256": "67559e80",
    }) == "SOURCE_LABELLED_MANTRA"


def test_a_bulk_aligned_row_says_so_rather_than_claiming_more(grade) -> None:
    assert grade({"alignment_level": "MANTRA"}) == "MACHINE_ALIGNED_NO_PER_ROW_CONTROL"


# ------------------------------------------------------------------- BAD, must raise ----
def test_an_unknown_alignment_level_raises_rather_than_defaulting(grade) -> None:
    """A value silently coerced to a default is how one axis gets three disagreeing writers."""
    with pytest.raises(ValueError):
        grade({"alignment_level": "PADA"})


def test_a_missing_alignment_level_raises(grade) -> None:
    with pytest.raises(ValueError):
        grade({})


def test_a_range_with_no_covered_keys_is_ungradable(grade) -> None:
    """A MANTRA_RANGE that does not say what it covers discloses nothing, so it cannot be
    graded as if it did."""
    with pytest.raises(ValueError):
        grade({"alignment_level": "MANTRA_RANGE"})


def test_the_vocabulary_is_closed_and_the_grades_come_from_it(grade) -> None:
    mod = _load()
    values = {v for v, _ in mod.VOCABULARY}
    for shape in (
        {"alignment_level": "MANTRA"},
        {"alignment_level": "HYMN"},
        {"alignment_level": "MANTRA_RANGE", "covers_canonical_keys": ["a"]},
        {"alignment_level": "MANTRA", "reuse_kind": "REUSED_RENDERING"},
    ):
        assert grade(shape) in values
