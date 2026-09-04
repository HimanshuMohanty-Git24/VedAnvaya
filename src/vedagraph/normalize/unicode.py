"""Lossless Unicode normalization and explicit comparison profiles."""

import unicodedata
from enum import StrEnum


class ComparisonProfile(StrEnum):
    ACCENT_PRESERVING = "ACCENT_PRESERVING"
    ACCENTLESS = "ACCENTLESS"
    SEARCH = "SEARCH"


class ComparisonForm(StrEnum):
    """Named comparison surfaces. Stored source text is never one of these."""

    SOURCE_ORIGINAL = "SOURCE_ORIGINAL"
    NFC = "NFC"
    ACCENT_PRESERVING_NORMALIZED = "ACCENT_PRESERVING_NORMALIZED"
    ACCENT_STRIPPED_COMPARISON = "ACCENT_STRIPPED_COMPARISON"
    SEARCH_NORMALIZED = "SEARCH_NORMALIZED"


# Vedic tone marks. This deliberately excludes ordinary Sanskrit combining signs.
# GRETIL's Aufrecht file marks anudatta with U+0331 and svarita with U+030D; VedaWeb's
# Latin versions instead mark udatta with U+0301. Both notations live here so that an
# accent-stripped surface is comparable across the two conventions.
VEDIC_ACCENT_CODEPOINTS = frozenset(
    chr(codepoint)
    for start, end in ((0x0951, 0x0954), (0x1CD0, 0x1CFF))
    for codepoint in range(start, end + 1)
) | frozenset({"̀", "́", "̍", "̱"})

# Editorial and structural marks that carry no phonetic value. They are removed only on
# a derived comparison surface, never in stored text.
#
# Two kinds, because they behave differently. Separators stand between words and become a
# space. Deleted marks sit inside a word and must vanish without splitting it: GRETIL
# writes the independent svarita as an in-word numeral (i1tthA) and VedaWeb writes the same
# phenomenon with a leading full stop, and neither digit is a letter of the text.
SEPARATOR_MARKS = frozenset("|/-_=()[]{}*,.;:?!'\"।॥‘’“”")  # noqa: RUF001
DELETED_MARKS = frozenset("0123456789०१२३४५६७८९​‌‍")  # noqa: RUF001
EDITORIAL_MARKS = SEPARATOR_MARKS | DELETED_MARKS

# Transcription systems that write the same Vedic sound with different code points.
# Folding them is lossy and exists only so that IAST (GRETIL) and ISO 15919 (VedaWeb)
# surfaces can be compared. The Rigveda has no vocalic l, so folding the retroflex
# lateral spellings together does not merge two distinct sounds in this corpus.
_VOCALIC_R = ""
_VOCALIC_R_LONG = ""
_RETROFLEX_L = ""
_ANUSVARA = ""

TRANSCRIPTION_EQUIVALENCES: tuple[tuple[str, str], ...] = (
    ("ṝ", _VOCALIC_R_LONG),  # r with dot below and macron
    ("r̥̄", _VOCALIC_R_LONG),  # r + ring below + macron above
    ("ṛ", _VOCALIC_R),  # r with dot below
    ("r̥", _VOCALIC_R),  # r + ring below
    ("ḷ", _RETROFLEX_L),  # l with dot below
    ("ḻ", _RETROFLEX_L),  # l with line below (GRETIL convention)
    ("l̥", _RETROFLEX_L),  # l + ring below
    ("ṁ", _ANUSVARA),  # m with dot above
    ("ṃ", _ANUSVARA),  # m with dot below
    ("m̐", _ANUSVARA),  # m + candrabindu
    # GRETIL writes the cluster after a short vowel geminated (gacchati); the VedaWeb
    # Latin layers write it single (gachati). Same cluster, different spelling convention.
    ("cch", "ch"),
)


def normalize_nfc(source_original: str) -> str:
    """Return NFC without mutating or replacing the caller's original field."""
    source_original.encode("utf-8", errors="strict")
    return unicodedata.normalize("NFC", source_original)


def has_vedic_accents(text: str) -> bool:
    """True when removing tone marks would change the text."""
    return strip_vedic_accents(text) != unicodedata.normalize("NFC", text)


VOWELS = frozenset("aeiouAEIOU")
# Only these four marks are ambiguous. The Devanagari svara marks (U+0951-U+0954 and the
# Vedic Extensions block) are never letter-forming, so they are always accents.
LATIN_LETTER_FORMING_MARKS = frozenset({"̀", "́", "̍", "̱"})


def _strip_cluster(base: str, marks: list[str]) -> str:
    """Decide, for one base letter and its combining marks, which marks are accents.

    Several tone marks double as spelling components of ordinary letters: U+0301 builds
    s-acute, U+0331 builds GRETIL's retroflex lateral. In this transcription the two uses
    are separable without guessing:

    * on a vowel base, a mark from the tone set is always an accent;
    * on a consonant base carrying exactly one mark, that mark is the letter itself;
    * on a consonant base carrying more than one mark, the extra tone mark is an accent.
      This is the vocalic-sonorant case: r plus U+0325 or U+0323 is the vowel r, so an
      acute or a line below on top of it is the Vedic tone, not part of the letter.
    """
    ambiguous = base not in VOWELS and len(marks) == 1 and marks[0] in LATIN_LETTER_FORMING_MARKS
    if ambiguous:
        return base + marks[0]
    return base + "".join(mark for mark in marks if mark not in VEDIC_ACCENT_CODEPOINTS)


def strip_vedic_accents(text: str) -> str:
    """Remove Vedic tone marks only; every other combining sign and letter survives."""
    decomposed = unicodedata.normalize("NFD", text)
    output: list[str] = []
    base = ""
    marks: list[str] = []
    for char in decomposed:
        if unicodedata.combining(char):
            if base:
                marks.append(char)
            else:
                output.append(char)
            continue
        if base:
            output.append(_strip_cluster(base, marks))
        base, marks = char, []
    if base:
        output.append(_strip_cluster(base, marks))
    return unicodedata.normalize("NFC", "".join(output))


def fold_transcription(text: str) -> str:
    """Fold IAST and ISO 15919 spelling variants onto shared comparison sentinels."""
    folded = unicodedata.normalize("NFC", text)
    for variant, sentinel in TRANSCRIPTION_EQUIVALENCES:
        folded = folded.replace(unicodedata.normalize("NFC", variant), sentinel)
    return folded


def strip_editorial_marks(text: str) -> str:
    kept = "".join(
        "" if char in DELETED_MARKS else " " if char in SEPARATOR_MARKS else char for char in text
    )
    return " ".join(kept.split())


def comparison_normalize(text: str, profile: ComparisonProfile) -> str:
    normalized = normalize_nfc(text)
    if profile == ComparisonProfile.ACCENT_PRESERVING:
        return normalized
    accentless = strip_vedic_accents(normalized)
    if profile == ComparisonProfile.ACCENTLESS:
        return accentless
    return " ".join(fold_transcription(accentless).casefold().split())


def comparison_form(text: str, form: ComparisonForm) -> str:
    """Derive one named comparison surface from stored source text."""
    if form == ComparisonForm.SOURCE_ORIGINAL:
        return text
    normalized = normalize_nfc(text)
    if form == ComparisonForm.NFC:
        return normalized
    stripped = strip_editorial_marks(normalized)
    if form == ComparisonForm.ACCENT_PRESERVING_NORMALIZED:
        return stripped
    accentless = strip_vedic_accents(stripped)
    if form == ComparisonForm.ACCENT_STRIPPED_COMPARISON:
        return accentless
    return " ".join(fold_transcription(accentless).casefold().split())
