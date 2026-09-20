"""Derived text surfaces -- GAP-MORPHOLOGY-006.

Every test here is a pair: a BAD input that must fail and a GOOD input that must pass. A
test that can only pass proves nothing, and this layer's whole defect was a surface nobody
could see the reach of.
"""

from __future__ import annotations

import pytest

from vedagraph.enrich.text_derivatives import (
    ACCENT_SOURCE_DERIVED,
    ACCENT_SOURCE_WITNESS,
    accent_stripped_surface,
    search_surface,
)
from vedagraph.normalize.unicode import ComparisonForm, comparison_form

# One accented Latin mantra (GRETIL Rigveda) and one accented Devanagari mantra
# (Wikisource Vajasaneyi). Both are real stored text, trimmed.
RV_LATIN = "a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m"
YV_DEVANAGARI = "इ॒षे त्वो॒र्जे त्वा॑ वा॒यव॑ स्थ दे॒वो व॑: सवि॒ता"
SV_DEVANAGARI = "इन्द्र ज्येष्ठं न आ भर ओजिष्ठं पुपुरि श्रवः"


def test_unknown_script_raises_rather_than_passing_the_text_through() -> None:
    """BAD -> FAIL. A silent pass-through emits a row that reports as searchable and is not."""
    with pytest.raises(ValueError, match="no declared search-surface transform"):
        search_surface("kimcit", "Bengali")


def test_declared_scripts_are_transformed() -> None:
    """GOOD -> PASS, the same call on a script the module declares."""
    assert search_surface(RV_LATIN, "Latin").text
    assert search_surface(YV_DEVANAGARI, "Devanagari").text


def test_a_devanagari_source_lands_in_latin_not_devanagari() -> None:
    """BAD -> FAIL: leaving Devanagari alone is what made one query unable to reach SV/YV.

    Asserted from both sides -- the surface must contain no Devanagari, and it must be
    non-empty, because an empty string also contains no Devanagari.
    """
    derived = search_surface(SV_DEVANAGARI, "Devanagari")
    assert derived.script == "Latin"
    assert derived.text
    assert not any(0x0900 <= ord(char) <= 0x097F for char in derived.text)
    assert "to_iast" in derived.derivation_steps


def test_a_latin_source_takes_no_transliteration_step() -> None:
    """The Atharvavedic instrument, unchanged. Adding a step would rewrite 5,839 live rows."""
    derived = search_surface(RV_LATIN, "Latin")
    assert derived.derivation_steps == ("comparison_form:SEARCH_NORMALIZED",)
    assert derived.text == comparison_form(RV_LATIN, ComparisonForm.SEARCH_NORMALIZED)


def test_one_accent_bearing_query_reaches_a_latin_and_a_devanagari_corpus() -> None:
    """The third clause of the closure test, on a two-corpus fixture.

    BAD -> FAIL: the accented query against the *stored* texts, which is the behaviour
    before this module existed. GOOD -> PASS: the same query folded by the same instrument
    against the derived surfaces.
    """
    query = "devásya"
    folded = comparison_form(query, ComparisonForm.SEARCH_NORMALIZED)
    assert folded != query, "the probe must actually carry an accent or it tests nothing"

    stored_hits = sum(1 for text in (RV_LATIN, YV_DEVANAGARI) if query in text)
    assert stored_hits == 0

    surfaces = [
        search_surface(RV_LATIN, "Latin").text,
        search_surface(YV_DEVANAGARI, "Devanagari").text,
    ]
    assert sum(1 for text in surfaces if "devo" in text) == 1
    assert all(isinstance(text, str) and text for text in surfaces)


def test_the_search_surface_strips_the_accent_it_is_asked_to_strip() -> None:
    """BAD -> FAIL if an accented character survives onto the search surface."""
    derived = search_surface(RV_LATIN, "Latin")
    assert "̱" not in derived.text and "̍" not in derived.text
    assert "́" not in derived.text
    assert "agnim" in derived.text


def test_accent_stripped_surface_keeps_the_source_script() -> None:
    """A reading aid for one corpus, not a cross-corpus comparison surface."""
    derived = accent_stripped_surface(YV_DEVANAGARI, "Devanagari")
    assert derived.script == "Devanagari"
    assert any(0x0900 <= ord(char) <= 0x097F for char in derived.text)
    assert "॑" not in derived.text and "॒" not in derived.text


def test_accent_stripping_an_unknown_script_raises() -> None:
    """BAD -> FAIL."""
    with pytest.raises(ValueError, match="no declared accent-stripping transform"):
        accent_stripped_surface("kimcit", "Telugu")


def test_the_two_accent_source_markers_are_distinct_strings() -> None:
    """The whole point of the pair: a derivative must never read as a second edition."""
    assert ACCENT_SOURCE_DERIVED != ACCENT_SOURCE_WITNESS
    assert "DERIVED" in ACCENT_SOURCE_DERIVED


def test_the_digest_is_of_the_derived_text_not_the_source() -> None:
    """BAD -> FAIL: digesting the source would make two different surfaces look identical."""
    from hashlib import sha256

    derived = search_surface(RV_LATIN, "Latin")
    assert derived.content_sha256 == sha256(derived.text.encode("utf-8")).hexdigest()
    assert derived.content_sha256 != sha256(RV_LATIN.encode("utf-8")).hexdigest()
