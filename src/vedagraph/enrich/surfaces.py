"""Comparison surfaces that make four differently-encoded Vedas comparable.

The four canonical corpora do not share a script, an accent notation, or a word-division
convention, and the differences are not cosmetic:

===  =========== ============ ================================================
Veda script      accents      word division
===  =========== ============ ================================================
RV   Latin       GRETIL marks spaced by word
SV   Devanagari  none         continuous sandhi, few breaks
YV   Devanagari  Vedic svara  spaced, some ASCII stand-ins for Devanagari signs
AV   Latin       GRETIL marks spaced by word
===  =========== ============ ================================================

Two consequences drive the whole design of this module.

**A cross-script pair can never match at the source level.** ``agním`` and ``अग्निम्`` are
the same word and share no code point. Any honest cross-Veda matcher must therefore
report *which* surface a match was reached on, and must not present a script-folded match
as though the editions agreed byte for byte. :class:`MatchLevel` is that report, ordered
strongest first, and :func:`reachable_levels` states up front which levels a given pair of
Vedas can possibly reach -- so a level that is absent because it is impossible is
distinguishable from a level that is absent because the texts differ.

**Word division is a source convention, not a fact about the verse.** The Samaveda
Wikisource text writes ``देवीरभिष्टये`` where the Rigveda GRETIL text writes ``devīr
abhiṣṭaye``. These are the same two words. A token-based comparison sees zero overlap and a
character-based one sees an exact match, so the sandhi-insensitive surface is not an
optional extra here: without it RV/SV parallel discovery, which is the single largest body
of genuine cross-Veda reuse in the corpus, mostly does not work.

Nothing here mutates stored text. Every surface is derived on read, and the level a match
was reached on is stored with the match as evidence.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from vedagraph.normalize import ComparisonForm, comparison_form, normalize_nfc
from vedagraph.normalize.unicode import fold_devanagari_source_conventions
from vedagraph.transliteration import DevanagariToIAST

_TRANSLITERATOR = DevanagariToIAST()

#: Scripts the canonical corpora are stored in, by Veda code. Read from the corpus rather
#: than assumed by callers; see :func:`veda_script`.
LATIN: Final = "Latin"
DEVANAGARI: Final = "Devanagari"


class MatchLevel(StrEnum):
    """Surfaces a textual match can be reached on, strongest first.

    "Strongest" means "asserts the most". A ``SOURCE_EXACT`` match says the two editions
    print identical bytes. A ``SANDHI_INSENSITIVE`` match says only that the two verses
    have the same letters in the same order once script, accent, punctuation and word
    division are all set aside. Both are real findings; they are not the same finding, and
    collapsing them would be the single most misleading thing this layer could do.
    """

    #: Identical stored text. Only possible within one script and one edition convention.
    SOURCE_EXACT = "SOURCE_EXACT"
    #: Identical after Unicode NFC. Separates a normalization artefact from a real variant.
    UNICODE_NORMALIZED = "UNICODE_NORMALIZED"
    #: Identical after editorial marks (dandas, brackets, verse numerals) are removed.
    PUNCTUATION_NORMALIZED = "PUNCTUATION_NORMALIZED"
    #: Identical once Vedic tone marks are removed. The Samaveda carries no accents at
    #: all, so every SV match is at best this level.
    ACCENT_INSENSITIVE = "ACCENT_INSENSITIVE"
    #: Identical once Devanagari is transliterated to IAST and IAST/ISO spellings are
    #: folded. The strongest level a cross-script pair can reach.
    SCRIPT_FOLDED = "SCRIPT_FOLDED"
    #: Identical once word boundaries are also dropped. Catches the sandhi-writing
    #: differences between editions; says nothing about how either edition divides words.
    SANDHI_INSENSITIVE = "SANDHI_INSENSITIVE"


#: Strongest first. A pair is reported at every level it reaches, and ``strongest`` is the
#: first entry it satisfies.
LEVEL_ORDER: Final[tuple[MatchLevel, ...]] = (
    MatchLevel.SOURCE_EXACT,
    MatchLevel.UNICODE_NORMALIZED,
    MatchLevel.PUNCTUATION_NORMALIZED,
    MatchLevel.ACCENT_INSENSITIVE,
    MatchLevel.SCRIPT_FOLDED,
    MatchLevel.SANDHI_INSENSITIVE,
)

#: Levels below this one compare code points directly and are therefore unreachable
#: between a Latin corpus and a Devanagari one.
_FIRST_CROSS_SCRIPT_LEVEL: Final = MatchLevel.SCRIPT_FOLDED


def reachable_levels(script_a: str, script_b: str) -> tuple[MatchLevel, ...]:
    """Levels a pair of texts in these scripts could reach, ignoring their content.

    Used to keep a report honest: RV/SV shows no ``SOURCE_EXACT`` matches because Latin
    and Devanagari share no code points, not because the two Vedas never repeat a verse.
    """
    if script_a == script_b:
        return LEVEL_ORDER
    start = LEVEL_ORDER.index(_FIRST_CROSS_SCRIPT_LEVEL)
    return LEVEL_ORDER[start:]


@functools.lru_cache(maxsize=32768)
def to_iast(text: str, script: str) -> str:
    """Return ``text`` in Latin script, transliterating only when it is not already.

    Cached because the cross-Veda matcher reads the same 22k texts through several
    stages, and ``indic-transliteration`` is the slowest step in the pipeline.
    """
    if script != DEVANAGARI:
        return normalize_nfc(text)
    return _TRANSLITERATOR.transliterate(text)


def _drop_word_boundaries(text: str) -> str:
    return "".join(text.split())


#: Comparison sentinels back to a printable IAST letter.
#:
#: ``fold_transcription`` maps four sounds onto private-use code points U+E000-U+E003 so
#: that IAST and ISO 15919 spellings compare equal. Those code points are *unassigned*:
#: they are a comparison device, and they must never reach a human. When they did, 88.6% of
#: published parallel evidence and 31.9% of concept-assertion evidence carried them, and
#: because an unassigned code point usually renders as nothing the damage was invisible and
#: worse than mojibake -- ``pṛñcatīr`` printed as ``pñcatīr``, and ``ṛtasya`` printed as
#: ``tasya``, which is a different Sanskrit word. Evidence that silently misquotes the text
#: is worse than no evidence, because it looks checkable.
#:
#: The mapping is injective, so rendering cannot merge two distinct folded strings. It is
#: nonetheless **lossy in the same way the fold is**: the whole lateral series collapsed
#: onto one sentinel, so this always prints the retroflex, and the ``cch``/``ch`` fold is
#: not undone. A rendered string is therefore a readable depiction of a comparison surface,
#: not a quotation of any edition. Callers that need the edition's own words should quote
#: ``TextSurfaces.source``.
_SENTINEL_TO_IAST: Final[dict[str, str]] = {
    "": "ṛ",  # vocalic r
    "": "ṝ",  # long vocalic r
    "": "ḷ",  # the folded lateral series, always printed retroflex
    "": "ṃ",  # anusvara
}
_SENTINEL_TABLE: Final = str.maketrans(_SENTINEL_TO_IAST)


def render_for_display(folded: str) -> str:
    """Render a folded comparison string as printable IAST.

    Apply this to anything a person will read -- evidence quotes, notes, display forms.
    Never apply it before a comparison: it undoes the fold that makes two spellings equal.
    """
    return folded.translate(_SENTINEL_TABLE)


def contains_private_use(text: str) -> bool:
    """True if ``text`` carries a private-use code point that should never be published."""
    return any(0xE000 <= ord(char) <= 0xF8FF for char in text)


@dataclass(frozen=True)
class TextSurfaces:
    """Every surface of one text, computed once.

    Built per mantra and reused by exact matching, near matching and formula extraction,
    which would otherwise each pay for transliteration separately.
    """

    passage_key: str
    veda: str
    script: str
    source: str
    unicode_normalized: str
    punctuation_normalized: str
    accent_insensitive: str
    script_folded: str
    sandhi_insensitive: str

    @property
    def tokens(self) -> tuple[str, ...]:
        """Word tokens of the script-folded surface.

        Only meaningful where the edition divides words. The Samaveda largely does not,
        which is why token overlap is a supporting signal in this layer and never the
        deciding one.
        """
        return tuple(self.script_folded.split())

    def surface(self, level: MatchLevel) -> str:
        return str(getattr(self, _SURFACE_ATTRIBUTE[level]))

    def is_comparable(self) -> bool:
        """False for a text too short to say anything about.

        A three-syllable fragment matches dozens of unrelated verses; admitting it would
        fill the graph with noise that looks like discovery.
        """
        return len(self.sandhi_insensitive) >= MIN_COMPARABLE_LENGTH


#: A mantra shorter than this on the sandhi-insensitive surface is not offered for
#: matching. Chosen from the corpus rather than by taste: the shortest genuine Rigvedic
#: mantra bodies run to roughly this length, and everything below it in the four corpora is
#: a fragment, a refrain marker or a structural stub.
MIN_COMPARABLE_LENGTH: Final = 20

_SURFACE_ATTRIBUTE: Final[dict[MatchLevel, str]] = {
    MatchLevel.SOURCE_EXACT: "source",
    MatchLevel.UNICODE_NORMALIZED: "unicode_normalized",
    MatchLevel.PUNCTUATION_NORMALIZED: "punctuation_normalized",
    MatchLevel.ACCENT_INSENSITIVE: "accent_insensitive",
    MatchLevel.SCRIPT_FOLDED: "script_folded",
    MatchLevel.SANDHI_INSENSITIVE: "sandhi_insensitive",
}

assert set(_SURFACE_ATTRIBUTE) == set(MatchLevel), "every match level needs a surface"


def build_surfaces(passage_key: str, veda: str, script: str, source_text: str) -> TextSurfaces:
    """Derive every comparison surface for one stored text.

    The order matters and mirrors :mod:`vedagraph.normalize`: transliteration happens
    *after* accent stripping would have, because ``indic-transliteration`` renders the
    Devanagari svara marks as Latin combining marks that the accent stripper already
    knows how to remove. Doing it the other way round leaves a Devanagari-origin text
    carrying accents that a Latin-origin text has had removed, and the two then never
    compare equal.

    Devanagari source conventions are folded *before* transliteration, and that ordering is
    not cosmetic. The accented Vajasaneyi layer types visarga as an ASCII colon in 893 of
    its 1,975 mantras. ``fold_devanagari_source_conventions`` rewrites that to U+0903, but
    it is gated on the text actually containing Devanagari -- correctly, since a colon in a
    Latin text is punctuation. Transliterating first defeats that gate: the output has no
    Devanagari left, the colon survives unfolded, and ``strip_editorial_marks`` then deletes
    it as a separator. The result was that a colon-visarga mantra and a real-visarga mantra
    compared *equal* on the accent-stripped Devanagari surface and *unequal* once folded --
    on the only surfaces a cross-script pair can be compared on at all.

    Measured: folding first raises exact cross-Veda identity from 1,404 pairs to 1,538,
    almost all of it in the Yajurveda cells (RV-YV 90 to 189, AV-YV 21 to 48).
    """
    nfc = normalize_nfc(source_text)
    punctuation = comparison_form(source_text, ComparisonForm.ACCENT_PRESERVING_NORMALIZED)
    accentless = comparison_form(source_text, ComparisonForm.ACCENT_STRIPPED_COMPARISON)
    folded = comparison_form(
        to_iast(fold_devanagari_source_conventions(normalize_nfc(source_text)), script),
        ComparisonForm.SEARCH_NORMALIZED,
    )
    return TextSurfaces(
        passage_key=passage_key,
        veda=veda,
        script=script,
        source=source_text,
        unicode_normalized=nfc,
        punctuation_normalized=punctuation,
        accent_insensitive=accentless,
        script_folded=folded,
        sandhi_insensitive=_drop_word_boundaries(folded),
    )


def strongest_level(a: TextSurfaces, b: TextSurfaces) -> MatchLevel | None:
    """The strongest level at which two texts are identical, or ``None``.

    Levels are tried strongest first and the first hit wins.

    **The levels are not strictly nested, and callers must not assume they are.** It is
    tempting to reason that each surface is derived from the one above, so a match at a
    strong level implies a match at every weaker one and comparing the weakest surface
    alone would find everything. That is false on this corpus, measured in 35 places: two
    Devanagari mantras can be identical once accents are stripped and then *diverge* once
    transliterated and folded, because the fold is lossy in ways the Devanagari surface is
    not -- the whole lateral series collapses onto one sentinel, and ``cch`` folds to
    ``ch``. Bucketing on the sandhi-insensitive surface alone silently loses those pairs.
    :func:`levels_reached` is therefore the honest report, and this function tries every
    reachable level rather than short-circuiting from the weakest.
    """
    for level in reachable_levels(a.script, b.script):
        if a.surface(level) == b.surface(level):
            return level
    return None


def levels_reached(a: TextSurfaces, b: TextSurfaces) -> tuple[MatchLevel, ...]:
    """Every level at which two texts are identical, strongest first."""
    return tuple(
        level
        for level in reachable_levels(a.script, b.script)
        if a.surface(level) == b.surface(level)
    )
