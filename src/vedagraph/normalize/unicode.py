"""Lossless Unicode normalization and explicit comparison profiles."""

import re
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
    #: SEARCH_NORMALIZED plus the folds that are only correct once a Devanagari text
    #: has been transliterated. Derived on read by the cross-Veda, parallel and formula
    #: layers; never an input to identity. See CROSS_SCRIPT_EQUIVALENCES.
    CROSS_SCRIPT_COMPARISON = "CROSS_SCRIPT_COMPARISON"


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


# Vedic and Devanagari nasal signs that reach only the CROSS-SCRIPT surface, named here so
# the table below stays legible.
CEC = "ᳬ"  # VEDIC SIGN ANUSVARA VAMAGOMUKHA WITH TAIL (category Lo: a letter)
A8F7 = "ꣷ"  # DEVANAGARI SIGN CANDRABINDU AVAGRAHA
#: What indic-transliteration renders U+0901 DEVANAGARI SIGN CANDRABINDU as: a bare ASCII
#: tilde. It exists in no source text held here -- verified, 0 occurrences of U+007E in the
#: stored text of all four corpora -- so this spelling can only ever arrive by
#: transliteration, which is why folding it is safe and why it belongs on this table alone.
TRANSLITERATED_CANDRABINDU = "~"

#: Folds that are correct ONLY on a transliterated comparison surface, or that would move
#: an already-released identity digest. Applied by :func:`fold_transcription_cross_script`
#: and never by :func:`fold_transcription`.
#:
#: WHY THERE ARE TWO TABLES. ``referent.text_fingerprints`` computes ``comparison_sha256``
#: through ``SEARCH_NORMALIZED``, so a rule added to ``TRANSCRIPTION_EQUIVALENCES``
#: changes the digest of already-released canonical keys -- measured: the sentinel-run
#: collapse alone moves 5 Yajurvedic keys, the U+1CEC rules 4 more and the U+A8F7 rule 1.
#: The referent gate then reports drift, which would assert that the source occurrence
#: moved. It did not; the normalisation that computes the digest did. Recording that as a
#: referent migration would be a false statement of exactly the kind the gate exists to
#: prevent, so the comparison fold is separated from the identity fold instead. This is
#: option B of FOLD_FIX_BREAKS_REFERENT_IDENTITY, and it is the owner's campaign-wide
#: invariant seen from the other side: normalisation is a comparison instrument and never
#: identity evidence, so a comparison fold must be free to change while identity is not.
#:
#: Each rule is keyed on a form MEASURED to arrive, not on one predicted to. The staged
#: patch proposed ``(CEA + U+1E43)`` and ``(CEA + U+1E41)``; both are redundant, because
#: each component already folds to the sentinel on its own and the run collapse below
#: merges them. Enumerating what actually survives found three forms the patch did not
#: name, and one that must NOT be folded -- see UNRESOLVED_PRIVATE_USE_IN_SOURCE.
CROSS_SCRIPT_EQUIVALENCES: tuple[tuple[str, str], ...] = (
    # U+1CEC is Unicode-named an ANUSVARA and the unaccented Vajasaneyi layer writes it
    # exactly where that layer writes U+1CEA -- 4 records, e.g. apaCECam sisur. The
    # transliterator passes both through unchanged, so a Devanagari-keyed rule does reach
    # this surface. Longest first, as in the table above.
    (CEC + ANUSVARA_SIGN, _ANUSVARA),
    (CEC, _ANUSVARA),
    # One occurrence, in a line that also carries U+A8F3: vayAM sasavA8F7so. The table
    # above already folds every other candrabindu spelling onto the anusvara sentinel
    # (U+A8F3 and m-plus-candrabindu), so treating this one differently would be the
    # inconsistency, not the fold.
    (A8F7, _ANUSVARA),
    (TRANSLITERATED_CANDRABINDU, _ANUSVARA),
)

#: Editorial marks that only a Devanagari source uses and that SEPARATOR_MARKS does not
#: cover, so they survived onto the comparison surface and caused false INEQUALITY: an
#: editorial variant note ``(pundrnaci EN-DASH pathabhedah)``, an insertion marker
#: ``[ + tam pratnatha``, and a soft-hyphen stand-in ``kramataNOT-SIGNmuru``. Seven
#: occurrences across six records of 20,210. They are not added to SEPARATOR_MARKS,
#: because that set feeds the identity digest as well.
CROSS_SCRIPT_SEPARATOR_MARKS = frozenset("+\¬–—")  # noqa: RUF001

#: U+F15C, in the Private Use Area, appears in the stored text of 20 unaccented Vajasaneyi
#: records -- ``prthivyAF15C satena``, ``devAnAF15C samit`` -- in the position the same
#: layer elsewhere writes an anusvara. It is deliberately NOT folded. A private-use code
#: point has no Unicode identity, no source assertion defines it, and reading it as an
#: anusvara from its context is a transcription judgement rather than a normalisation.
#: Registered as a source-transcription defect instead; see the gap registry.
UNRESOLVED_PRIVATE_USE_IN_SOURCE = ""

#: Two or more adjacent anusvara sentinels denote one nasal in every source held here, and
#: a run is how the double-fold defect shows up: the Vajasaneyi cluster U+1CEA + U+0902
#: arrives as U+1CEA + U+1E43, and the table above folds each component separately, so one
#: nasal became two sentinels on 1,232 of 3,811 Yajurvedic text records. Kept out of the
#: replacement table because it is a post-condition on the folded string rather than a
#: spelling equivalence. Only the anusvara sentinel is collapsed, and the restriction is
#: load-bearing rather than cautious: a run of the OTHER three sentinels is two real
#: letters, and the Rigveda alone carries 419 such runs across 404 records -- 99 of them
#: (95 records) two adjacent vocalic r. Collapsing every sentinel run would silently
#: delete a vowel from each.
_ANUSVARA_RUN = re.compile(_ANUSVARA + "{2,}")


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


def fold_transcription_cross_script(text: str) -> str:
    """:func:`fold_transcription` plus the folds only a transliterated surface can need.

    Use this for comparing two texts. Never use it where a digest is compared against a
    released baseline: that is what :func:`fold_transcription` is for, and the two are
    separate so that correcting a comparison cannot read as a change of identity.

    The run collapse runs last and is why the two ``CEA``-plus-nasal rules the staged
    patch proposed are not in the table: the existing table already folds each component
    to the sentinel on its own, so the cluster arrives here as two adjacent sentinels and
    the collapse merges them. Asserted in the tests rather than assumed.
    """
    folded = fold_transcription(text)
    for variant, sentinel in CROSS_SCRIPT_EQUIVALENCES:
        folded = folded.replace(unicodedata.normalize("NFC", variant), sentinel)
    return _ANUSVARA_RUN.sub(_ANUSVARA, folded)


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


def strip_editorial_marks(text: str, extra_separators: frozenset[str] = frozenset()) -> str:
    """Remove editorial and structural marks from a derived surface.

    ``extra_separators`` widens the separator set for one surface only. It exists because
    SEPARATOR_MARKS feeds the identity digest, so a mark that must be dropped for
    comparison cannot simply be added to it. Default empty: every existing caller behaves
    exactly as before.
    """
    separators = SEPARATOR_MARKS | extra_separators
    kept = "".join(
        "" if char in DELETED_MARKS else " " if char in separators else char for char in text
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
    cross_script = form == ComparisonForm.CROSS_SCRIPT_COMPARISON
    stripped = strip_editorial_marks(
        normalized, CROSS_SCRIPT_SEPARATOR_MARKS if cross_script else frozenset()
    )
    if form == ComparisonForm.ACCENT_PRESERVING_NORMALIZED:
        return stripped
    accentless = strip_vedic_accents(stripped)
    if form == ComparisonForm.ACCENT_STRIPPED_COMPARISON:
        return accentless
    fold = fold_transcription_cross_script if cross_script else fold_transcription
    return " ".join(fold(accentless.casefold()).split())
