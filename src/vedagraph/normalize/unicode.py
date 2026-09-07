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
#
# U+032D is here because it is what a DERIVED surface actually contains, not because any
# source writes it: indic-transliteration renders Devanagari udatta (U+0951) as U+032D,
# while it renders anudatta (U+0952) as U+0331. Omitting U+032D made the two accents behave
# inconsistently after transliteration -- has_vedic_accents() returned False for udatta-
# accented text, i.e. it denied accents that were present, and strip_vedic_accents() left
# them in, so an accented and an unaccented reading of the same mantra compared EQUAL in
# Devanagari but UNEQUAL once transliterated. This matters for Yajurveda, Samaveda and
# Atharvaveda, which are all Devanagari-primary. Verified: 0 of the 21,936 canonical text
# records across all four Vedas contain U+032D, so adding it cannot alter stored data or any
# existing comparison; it only fixes the transliterated surface.
VEDIC_ACCENT_CODEPOINTS = frozenset(
    chr(codepoint)
    for start, end in ((0x0951, 0x0954), (0x1CD0, 0x1CFF))
    for codepoint in range(start, end + 1)
) | frozenset({"̀", "́", "̍", "̱", "̭"})

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
# surfaces can be compared.
#
# The whole lateral series folds onto ONE sentinel, which merges vocalic l with
# retroflex l. An earlier revision of this comment justified that by claiming the
# Rigveda has no vocalic l. That claim is false. The behaviour is nevertheless correct,
# for a stronger reason: U+1E37 (l with dot below) denotes OPPOSITE sounds in the two
# notations actually ingested, so no global code-point-to-sentinel table can be right.
#
# Measured over the 10,552 mantras of data/canonical/rigveda_full_v1, each version has
# exactly 671 laterals:
#   GRETIL  (IAST)       668 l-with-line-below +   3 l-with-dot-below + 0 l+ring-below
#   VedaWeb (ISO 15919)    0 l-with-line-below + 669 l-with-dot-below + 2 l+ring-below
# The 668<->669 and 3<->2 correspondence shows that l-with-dot-below is the VOCALIC l in
# GRETIL and the RETROFLEX l in VedaWeb. Mapping that one code point either way breaks
# the other notation, so this fold declines to distinguish the series at all. Splitting
# it was tried and measurably regressed RV 10.157.2 (cikl-pati) from ACCENT_ONLY to
# UNCLASSIFIED, because the two sources spell the same vocalic l with different marks.
#
# KNOWN LOSSINESS, carried deliberately: the derived search surface cannot tell vocalic l
# from retroflex l. That is harmless for the Rigveda but real for the Atharvaveda, whose
# accented GRETIL artifact writes vocalic l 15 times with l+ring-below. Resolving it
# needs a notation-aware fold (a scheme argument), not a bigger table; that is a contract
# change, recorded in docs/reports/FOUR_VEDA_NORMALIZATION_POLICY.md rather than guessed
# at here. Nothing in this module ever mutates stored source text.
_VOCALIC_R = ""
_VOCALIC_R_LONG = ""
_RETROFLEX_L = ""
_ANUSVARA = ""

# Devanagari nasal and visarga code points, named rather than inlined so the fold rules
# below stay legible. U+A8F3 and U+1CEA both spell the anusvara; U+1CED is the combining
# tiryak that accompanies the second spelling.
A8F3 = "ꣳ"  # DEVANAGARI SIGN CANDRABINDU VIRAMA
CEA = "ᳪ"  # VEDIC SIGN ANUSVARA BAHIRGOMUKHA (category Lo: a letter)
CED = "᳭"  # VEDIC SIGN TIRYAK (category Mn: combining)
ANUSVARA_SIGN = "ं"  # DEVANAGARI SIGN ANUSVARA
VISARGA = "ः"  # DEVANAGARI SIGN VISARGA  # noqa: RUF001

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
    # Devanagari anusvara, which the Latin rules above could not reach at all. The two
    # Vajasaneyi layers spell one nasal incompatibly: the unaccented layer writes U+A8F3
    # (77 occurrences in the pilot) and the accented layer writes U+1CEA + U+0902 + U+1CED
    # (70). Because U+1CED is a combining mark inside the Vedic Extensions range it is
    # already removed by strip_vedic_accents, while U+1CEA is category Lo and survives, so
    # the accented spelling arrives here as U+1CEA + U+0902 on an accent-stripped surface
    # and in full on an accent-preserving one. Both arrival forms are folded, longest
    # first, onto the SAME sentinel the Latin anusvara spellings already use, so a
    # Devanagari and a Latin reading of one nasal are comparable.
    #
    # Unlike the lateral series this is safe to fold: every spelling below denotes the
    # anusvara in Devanagari, and no source uses any of them for a different sound.
    (CEA + ANUSVARA_SIGN + CED, _ANUSVARA),
    (CEA + ANUSVARA_SIGN, _ANUSVARA),
    (CEA, _ANUSVARA),
    (A8F3, _ANUSVARA),
    (ANUSVARA_SIGN, _ANUSVARA),
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


# Case is folded BEFORE this table is applied, never after. Every spelling in
# TRANSCRIPTION_EQUIVALENCES is lower-case, so folding first left an upper-case variant
# unmatched and it only folded if the surface was normalized a second time -- which made
# the search surface non-idempotent and, worse, made two spellings of one sound compare
# unequal. Measured: reordering changes the surface for 0 of the 21,936 canonical text
# records across all four Vedas, and makes the GRETIL Atharvaveda artifacts idempotent.
def fold_transcription(text: str) -> str:
    """Fold IAST and ISO 15919 spelling variants onto shared comparison sentinels."""
    folded = unicodedata.normalize("NFC", text)
    for variant, sentinel in TRANSCRIPTION_EQUIVALENCES:
        folded = folded.replace(unicodedata.normalize("NFC", variant), sentinel)
    return folded


DEVANAGARI_RANGE = range(0x0900, 0x0980)


def has_devanagari(text: str) -> bool:
    return any(ord(char) in DEVANAGARI_RANGE for char in text)


def fold_devanagari_source_conventions(text: str) -> str:
    """Rewrite ASCII stand-ins that a Devanagari source uses for real Devanagari signs.

    One case, and it is a real source convention rather than a typo: the accented
    Vajasaneyi layer types visarga as an ASCII colon. There are 124 of them in the
    Yajurveda pilot's 271 records against 321 genuine U+0903, and the unaccented layer uses
    U+0903 throughout, so the two layers can never agree on those positions.

    This cannot be expressed as a TRANSCRIPTION_EQUIVALENCES rule, because ``:`` is in
    SEPARATOR_MARKS and ``strip_editorial_marks`` turns it into a space before
    ``fold_transcription`` ever sees it. It also must not be applied globally: in a Latin
    text a colon is ordinary punctuation, not a visarga. So the rewrite is gated on the text
    actually containing Devanagari, which is what makes it safe.

    Measured: of the 21,936 canonical text records across all four Vedas, only the 271
    Yajurveda records contain Devanagari at all, and Rigveda, Samaveda and Atharvaveda
    contain no ASCII colon in their text. This function is therefore a no-op for every
    non-Devanagari record.

    Derived surfaces only. Stored ``text_original`` is never touched.
    """
    if not has_devanagari(text):
        return text
    return text.replace(":", VISARGA)


def strip_editorial_marks(text: str) -> str:
    kept = "".join(
        "" if char in DELETED_MARKS else " " if char in SEPARATOR_MARKS else char for char in text
    )
    return " ".join(kept.split())


def comparison_normalize(text: str, profile: ComparisonProfile) -> str:
    normalized = normalize_nfc(text)
    if profile == ComparisonProfile.ACCENT_PRESERVING:
        return normalized
    normalized = fold_devanagari_source_conventions(normalized)
    accentless = strip_vedic_accents(normalized)
    if profile == ComparisonProfile.ACCENTLESS:
        return accentless
    return " ".join(fold_transcription(accentless.casefold()).split())


def comparison_form(text: str, form: ComparisonForm) -> str:
    """Derive one named comparison surface from stored source text."""
    if form == ComparisonForm.SOURCE_ORIGINAL:
        return text
    normalized = normalize_nfc(text)
    if form == ComparisonForm.NFC:
        return normalized
    # Source-convention folding happens before editorial stripping, or the colon would
    # already have become a space. SOURCE_ORIGINAL and NFC return above, untouched.
    normalized = fold_devanagari_source_conventions(normalized)
    stripped = strip_editorial_marks(normalized)
    if form == ComparisonForm.ACCENT_PRESERVING_NORMALIZED:
        return stripped
    accentless = strip_vedic_accents(stripped)
    if form == ComparisonForm.ACCENT_STRIPPED_COMPARISON:
        return accentless
    return " ".join(fold_transcription(accentless.casefold()).split())
