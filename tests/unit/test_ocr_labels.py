"""The corrupt-label reader, and the cases it must refuse.

Every test here has a partner: a GOOD case the rule accepts and a BAD case it must reject.
A rule with only positive tests is a rule that would pass if it returned its input, and this
project has shipped exactly that once -- a tiling heuristic that fired on eight hymns and was
wrong on all eight because nothing asked it to refuse.
"""

import pytest

from vedagraph.ingest.ocr_labels import (
    GLYPH_TO_DIGIT,
    readings,
    resolve_corrupt_label,
    sole_free_slot,
)

SECTION = "§"


# --------------------------------------------------------------------------- readings ----
def test_a_literal_number_reads_as_itself() -> None:
    assert readings("29") == [29]
    assert readings("30.") == [30]


def test_the_rv_8_93_29_token_reads_as_29() -> None:
    """The real token in the held Wikisource snapshot: 2 followed by a section sign."""
    assert readings("2" + SECTION) == [29]


def test_a_token_with_no_digit_reading_returns_nothing() -> None:
    # BAD case. "the" is not a number under any substitution in the map, and a rule that
    # wanted to be helpful here would start renaming words into verse labels.
    assert readings("the") == []
    assert readings("Satakratu") == []
    assert readings("") == []


def test_a_glyph_outside_the_map_is_not_invented() -> None:
    # BAD case. The map is closed on purpose: every entry was observed in these bytes.
    assert "#" not in GLYPH_TO_DIGIT
    assert readings("2#") == []


def test_an_ambiguous_token_reports_both_readings_rather_than_choosing() -> None:
    # "IS" reads literally as nothing and under substitution as 15. The real sweep over the
    # imported corpus hit this on RV 2.12.14 and RV 8.102.14, where "is" is the English word.
    # The rule's job is to surface both, not to pick.
    assert readings("Is") == [15]


# ------------------------------------------------------------- resolve_corrupt_label -----
def _rv_8_93_29(**over):
    kwargs = dict(
        preceding_label=28,
        following_label=30,
        printed_unit_count=34,
        canonical_verse_count=34,
    )
    kwargs.update(over)
    return resolve_corrupt_label("2" + SECTION, **kwargs)


def test_good_rv_8_93_29_is_forced_by_its_neighbours() -> None:
    assert _rv_8_93_29() == 29


def test_bad_refuses_when_the_print_and_the_spine_disagree_on_length() -> None:
    """A recovered label must not paper over a missing or an extra printed unit.

    This is the adhyaya-12 shape: 118 printed units against a 117-verse spine. Reading a
    label there would bind text one place out and look like a better result.
    """
    assert _rv_8_93_29(printed_unit_count=33) is None
    assert _rv_8_93_29(canonical_verse_count=35) is None


def test_bad_refuses_when_more_than_one_slot_sits_between_the_neighbours() -> None:
    # Labels 28 and 32 leave three free slots; the token is not forced by them.
    assert _rv_8_93_29(following_label=32) is None


def test_bad_refuses_a_token_that_does_not_read_as_the_forced_slot() -> None:
    """The neighbours forcing slot 29 is not on its own a licence to write 29 there."""
    assert resolve_corrupt_label(
        "4" + SECTION,
        preceding_label=28,
        following_label=30,
        printed_unit_count=34,
        canonical_verse_count=34,
    ) is None


# ------------------------------------------------------------------- sole_free_slot ------
def test_good_one_free_slot_is_returned() -> None:
    assert sole_free_slot([1, 2, 3, 5], 5) == 4


def test_bad_two_free_slots_refuse() -> None:
    assert sole_free_slot([1, 2, 5], 5) is None


def test_bad_no_free_slot_refuses() -> None:
    assert sole_free_slot([1, 2, 3, 4, 5], 5) is None


# ------------------------------------------------- the permutation that was mis-applied --
def test_the_valakhilya_permutation_is_why_wave_1_read_the_wrong_page() -> None:
    """RV 8.93.29 was refused as 'the Valakhilya permutation, refused rather than guessed'.

    The refusal read sacred-texts ``rv08093.htm``, which under Griffith's appended order is
    canonical RV 8.49, not 8.93 -- so the page it inspected was the wrong hymn entirely. The
    repo has carried the transform as data all along.
    """
    from vedagraph.editions import griffith_page

    assert griffith_page(8, 93) == 82, "canonical 8.93 is Griffith's hymn page 82"
    assert griffith_page(8, 49) == 93, "Griffith's page 93 is canonical 8.49"
    # And the naive identity, which is what reading rv08093.htm for 8.93 assumes, is wrong.
    assert griffith_page(8, 93) != 93
