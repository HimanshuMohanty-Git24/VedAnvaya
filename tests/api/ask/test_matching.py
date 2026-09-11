"""Name matching: the fold ladder, and the substring trap it was built to close.

Two live defects are encoded here.

*The unreachable node.* The registry spells cosmic order ``ṛta`` and a researcher types
``rta``. Without folding, ``VG:CONCEPT:RTA-ORDER`` -- the node the question is about -- is
unreachable by the spelling a keyboard produces, and the pipeline answers "no evidence"
from a matching artefact.

*The mortar.* The obvious repair, substring containment, resolved "what connects Varuna
with rta" onto ``VG:DEVATA:ULUKHALAM``, *the mortar*, because ``rta`` is a substring of it.
Containment is therefore over whole folded tokens, and that is what these tests pin.
"""

from __future__ import annotations

import pytest

from vedagraph.api.ask.matching import (
    FOLD_LADDER,
    fold_name,
    fold_query_name,
    fold_query_name_vocalic,
    token_match,
)


@pytest.mark.parametrize(
    ("raw", "folded"),
    [
        ("Ṛta", "rta"),
        ("viśvāmitra", "visvamitra"),
        ("rakṣas", "raksas"),
        ("Ṛgveda", "rgveda"),
        # ṃ and ḥ have no canonical decomposition, and they are exactly the characters a
        # transliterated Sanskrit noun ends in.
        ("purohitaṃ", "purohitam"),
        ("agniḥ", "agnih"),
        ("  AGNI  ", "agni"),
    ],
)
def test_fold_name_strips_diacritics_and_case(raw: str, folded: str) -> None:
    assert fold_name(raw) == folded


def test_folding_does_not_strip_the_vedic_pitch_accent() -> None:
    """A measured limit, not an oversight.

    ``DIACRITIC_FOLD`` covers IAST transliteration diacritics and deliberately not the
    acute/grave pitch marks carried inline in the Rigvedic and Atharvavedic Sanskrit. That
    is the same bound ``retriever.SURFACE_LIMITS`` states for the lexical channel: an
    unaccented query term matches only where the accents fall outside it. Pinned here so
    the constraint is visible rather than rediscovered from a silent miss.
    """
    assert fold_name("puróhitaṃ") == "puróhitam"
    assert token_match("purohitam", "puróhitaṃ") is False


@pytest.mark.parametrize(
    ("typed", "folded"),
    [
        # The digraph fold: applied to the question only, never to a stored label.
        ("Vishvamitra", "visvamitra"),
        ("rakshas", "raksas"),
        ("Shiva", "siva"),
    ],
)
def test_fold_query_name_folds_ascii_digraphs(typed: str, folded: str) -> None:
    assert fold_query_name(typed) == folded


def test_fold_query_name_is_strictly_more_aggressive_than_fold_name() -> None:
    """The asymmetry is the design: a folded question meets a folded label."""
    assert fold_name("rakshas") == "rakshas"
    assert fold_query_name("rakshas") == "raksas"
    assert fold_query_name("rakṣas") == fold_name("rakṣas") == "raksas"


@pytest.mark.parametrize(
    ("typed", "folded"),
    [
        ("Brihaspati", "brhaspati"),
        ("Rigveda", "rgveda"),
        ("Prithvi", "prthvi"),
    ],
)
def test_fold_query_name_vocalic_undoes_inserted_vowels(typed: str, folded: str) -> None:
    assert fold_query_name_vocalic(typed) == folded


def test_the_vocalic_fold_is_lossy_which_is_why_it_is_a_fallback() -> None:
    """It rewrites the ordinary syllable *ri* too, so it must never outrank an exact hit."""
    assert fold_query_name_vocalic("sarira") == "sarra"
    assert fold_query_name("sarira") == "sarira"


def test_fold_ladder_is_ordered_strictest_first() -> None:
    assert FOLD_LADDER[0] is fold_query_name
    assert FOLD_LADDER[-1] is fold_query_name_vocalic


# ---------------------------------------------------------------------------
# The substring trap
# ---------------------------------------------------------------------------


def test_rta_does_not_match_inside_mortar() -> None:
    """The defect that made this a module: character containment picked a kitchen
    implement as the subject of a question about cosmic order."""
    assert token_match("rta", "the mortar") is False


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("rta", "cosmic order (ṛta)"),
        ("takman", "fever (takman)"),
        ("soma", "Soma-Pusan"),
        ("rta", "Ṛta"),
        ("visvamitra", "Viśvāmitra"),
    ],
)
def test_a_whole_token_matches(name: str, label: str) -> None:
    assert token_match(name, label) is True


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("ap", "appear"),
        ("ap", "Does Indra appear here"),
        ("soma", "Somapa"),
        ("agni", "agnihotra"),
    ],
)
def test_a_bare_substring_does_not_match(name: str, label: str) -> None:
    assert token_match(name, label) is False
