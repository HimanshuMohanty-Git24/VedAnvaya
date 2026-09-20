#!/usr/bin/env python3
"""Script folding and token similarity for the translation Gate B/C packet.

This module exists because the Samaveda populations' whole case rests on a claim of the
form "this Kauthuma verse's Sanskrit is surface-identical to that Rigveda verse's", and
the two texts are not in the same script: the Kauthuma Samhita is held as unaccented
Devanagari (WIKISOURCE_SA) and the Rigveda as accent-marked IAST (GRETIL/VEDAWEB). A
similarity between them is therefore never a raw string comparison, and the packet has to
state exactly what was folded away before it calls anything identical.

What is folded, and why each is safe:

- Devanagari is transliterated to IAST. This is a round-trippable mapping of the same
  phonemes, not a normalisation that discards information.
- Vedic pitch accents are removed: U+030D (udatta, vertical line above) and U+0331
  (anudatta, macron below) in the Latin text, plus U+0951/U+0952 and the Vedic Extensions
  block on the Devanagari side. This IS a real loss -- pitch is phonemic in Vedic -- but
  the Kauthuma text carries no accents at all (`accented: false`), so the comparison could
  not use them from either side even in principle.
- Danda, double danda and Latin punctuation become word breaks.

What is NOT folded, because folding it would manufacture identity:

- Vowel length (ā vs a), retroflexion (ṣ/ṭ/ḍ/ṇ vs s/t/d/n), aspiration and visarga are all
  preserved. An earlier attempt at this fold stripped every Unicode Mn character before
  transliterating, which deleted the Devanagari matras and turned प्रेष्ठं into
  "paraṣaṭha"; it then scored two genuinely identical verses at 0.19 and would have failed
  every true row in the population. The lesson is that `unicodedata.category(c) == "Mn"`
  is not a synonym for "diacritic noise" in either script.

`sandhi_insensitive` is offered separately and is never the default: Samavedic and Rigvedic
witnesses of one verse routinely differ only in word division (viśvasya/viśvasya vs
viśvasyā arāteḥ), and a reader deciding whether to trust a row is entitled to see both the
strict number and the permissive one rather than one blended figure.
"""

from __future__ import annotations

import re
import unicodedata

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Pitch/accent marks only. Everything else combining is phonemic and stays.
#
# U+0301 is deliberately NOT here, and that is the whole point of the comment. An earlier
# draft included it as "the acute accent", which is true of many scripts and only half true
# of IAST: ś (U+015B), the palatal sibilant, decomposes to s + U+0301, so stripping every
# acute folded viśvasya into visvasya and manufactured identity between two verses that
# differ in exactly that sibilant. It is handled context-sensitively in strip_accents()
# instead, by the base letter it sits on. U+0300 (grave) IS here, because unlike the acute
# it carries no phonemic job in IAST -- it marks the anudatta after an elided vowel (hy
# àsya) and nothing else. The inventory was measured across every primary text version in
# this graph rather than assumed.
VEDIC_ACCENTS = {
    "̍",  # combining vertical line above  -- udatta, as GRETIL writes it
    "̱",  # combining macron below         -- anudatta
    "̀",  # combining grave                -- anudatta after an elided vowel (hy àsya)
    "॑",  # devanagari stress sign udatta
    "॒",  # devanagari stress sign anudatta
}
VEDIC_EXT = range(0x1CD0, 0x1D00)

# Anusvara is written two ways by the two source families and means one thing in both:
# GRETIL/VEDAWEB use ṁ (U+1E41, dot above), the Devanagari-to-IAST transliteration produces
# ṃ (U+1E43, dot below). Unifying them is a convention fix, not a phonemic loss, and it is
# listed separately from the accents so the packet can say which of the two it applied.
ANUSVARA_UNIFY = {"ṁ": "ṃ", "ྃ": "ṃ"}

#: The same phoneme, two romanisation standards, and both are in this graph. Vocalic r and l
#: are written with a ring below in ISO 15919 (r̥ = r + U+0325), which is what the GRETIL
#: Atharvaveda edition uses, and with a dot below in IAST (ṛ = U+1E5B = r + U+0323), which
#: is what the GRETIL Rigveda edition uses. Unifying them is a convention fix like the
#: anusvara one -- but it has to be conditioned on the base letter, because a dot below is
#: phonemic on every other consonant it appears on (ṣ ṭ ḍ ṇ ḥ), so a blanket swap would
#: merge s with ṣ. Applied only to r and l.
VOCALIC_RL_BASES = {"r", "l", "R", "L"}
RING_BELOW = "̥"
DOT_BELOW = "̣"

#: The third and last notation split between these editions. The nasal that appears before a
#: following vowel or sibilant (mahām̐ś / mahāṃś, devām̐ / devāṃ) is written by the GRETIL
#: Rigveda with a candrabindu (m + U+0310) and by the Atharvaveda and Samaveda witnesses with
#: an anusvara dot (ṃ). Measured across every primary text version in this graph, U+0310
#: occurs 153 times and attaches to `m` in every single one, always in that sandhi position
#: -- so folding it to ṃ is a romanisation fix, not a phonological claim. It is counted
#: separately in the packet because a reader is entitled to know how many identity findings
#: depend on it.
CANDRABINDU = "̐"

#: A nasalised vowel is written three ways across these editions: with a candrabindu on a
#: following m (mahām̐ś), with a plain anusvara m (mahāṃś), and with a combining tilde on the
#: vowel itself (vājā̃ for vājāṃ). The third form appears 187 times. Folding it means
#: *inserting* the anusvara consonant rather than deleting a mark, which is a more assertive
#: transform than the others here, so it is named and counted on its own.
COMBINING_TILDE = "̃"
ANUSVARA_LETTER = "ṃ"
#: And a fourth spelling of the same sound, which only exists because of the transliterator:
#: `indic_transliteration` renders the Devanagari candrabindu ँ (U+0901) as an ASCII tilde,
#: so a nasalised vowel that was written ँ in the Kauthuma Devanagari arrives here as
#: "vājā~" and no combining-mark rule can see it. Two occurrences in this corpus, one of
#: them inside a row whose entire case is an identity claim.
POST_TRANSLITERATION_TILDE = "~"

#: Word-final m and anusvara are one sound, and the editions disagree about which to print:
#: GRETIL's Rigveda gives "ny ū ṣu vācam pra mahe" where its Atharvaveda gives "vācaṃ pra
#: mahe" for the same verse. Sanskrit orthography converts a final labial nasal to anusvara
#: before a following consonant and editors apply that inconsistently. Without unifying
#: them, RV 1.53.1 and AV 20.21.1 -- one verse, attested in both corpora and translated
#: separately by Griffith in each volume -- compare as different texts, and a duplication
#: check built on Sanskrit identity reports his two honest renderings as generator
#: duplication.
#:
#: This is applied ONLY in `sandhi_insensitive`, never in the strict fold, and the reason is
#: worth recording because the obvious placement is wrong. Conditioning the substitution on
#: a word boundary and then discarding word boundaries are incompatible: "tvām id" folds to
#: "tvāṃ id" and joins to "tvāṃid", while the other witness's already-joined "tvāmid" has no
#: final m to convert and stays "tvāmid". Putting it in the strict fold therefore broke 196
#: identity comparisons that had been matching -- it turned a 526/528 reproduction rate into
#: 330/528. In the permissive form word division is already gone, so every m is unified and
#: the two spellings of one sound agree however the editor set them.
_ANY_NASAL = re.compile(r"m")

#: The independent svarita is written as a digit attached to the preceding letter (ukthya1ṃ,
#: pathyā3). Measured across every primary text version there are 33 such letter-adjacent
#: digits in total, and the two editions disagree on which digit to use for the same syllable
#: -- one writes ukthya1ṃ where the other writes ukthya3ṃ. They are pitch notation, so they
#: go the same way as the other accents.
_ACCENT_DIGIT = re.compile(r"(?<=[^\W\d_])\d")

_PUNCT = re.compile(r"[|।॥/,.;:!?\"'`()\[\]{}<>*‘’“”–—-]+")
_WS = re.compile(r"\s+")
#: Editions print the verse number inside the text ("||1||"). Once the dandas are folded to
#: spaces that leaves a bare "1" token, which would count as a shared or unshared word and
#: move the score for a reason that has nothing to do with the verse.
_BARE_NUMBER = re.compile(r"\b\d+\b")


#: Base letters on which a combining acute is a Vedic udatta rather than a phoneme.
#: In IAST the acute does two unrelated jobs, and which one it is doing depends entirely on
#: what it sits on: on a vowel (or vocalic r/l) it marks pitch, on `s` it makes the palatal
#: sibilant ś. The two GRETIL families in this graph happen to split along exactly that
#: line -- the Rigveda edition writes udatta as U+030D, the Atharvaveda edition writes it as
#: U+0301 -- so a fold that treats U+0301 as always-phonemic scores two identical verses at
#: 0.0, and one that treats it as always-accent merges viśva with visva. Both mistakes were
#: made in this order while building this module.
ACUTE_IS_ACCENT_ON = set("aeiouāīūēōr̥l̥rl")


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    out: list[str] = []
    base = ""
    for c in text:
        if c in VEDIC_ACCENTS or ord(c) in VEDIC_EXT:
            continue
        if c == "́":
            # Decide by the base letter this acute is attached to, skipping any combining
            # marks already emitted between them (NFD puts below-marks before above-marks).
            if base and base.lower() in ACUTE_IS_ACCENT_ON:
                continue
            out.append(c)
            continue
        if c == CANDRABINDU and base in {"m", "M"}:
            out.append(DOT_BELOW)
            continue
        if c == COMBINING_TILDE:
            # Nasalised vowel written as a tilde over the vowel; spell it as the anusvara
            # the other edition writes, so the two forms of one sound compare equal.
            out.append(ANUSVARA_LETTER)
            continue
        if c == RING_BELOW and base in VOCALIC_RL_BASES:
            # Vocalic r/l: fold the ISO 15919 ring to the IAST dot so the two editions'
            # spellings of one phoneme compare equal.
            out.append(DOT_BELOW)
            continue
        out.append(c)
        if unicodedata.category(c) != "Mn":
            base = c
    return unicodedata.normalize("NFC", "".join(out))


def fold_sanskrit(text: str, script: str | None) -> str:
    """Fold one Sanskrit witness to accent-free lowercase IAST word tokens."""
    if not text:
        return ""
    if (script or "").lower().startswith("dev"):
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
        text = text.replace(POST_TRANSLITERATION_TILDE, ANUSVARA_LETTER)
    text = strip_accents(text)
    text = unicodedata.normalize("NFC", text)
    for src, dst in ANUSVARA_UNIFY.items():
        text = text.replace(src, dst)
    text = _ACCENT_DIGIT.sub("", text)
    text = _PUNCT.sub(" ", text)
    text = _BARE_NUMBER.sub(" ", text)
    return _WS.sub(" ", text).strip().lower()


def fold_english(text: str) -> str:
    """Fold an English translation for token comparison. Accents kept out of the tokens."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip().lower()


def sandhi_insensitive(folded: str) -> str:
    """Collapse word division entirely: one character string, no spaces.

    Used only as a second opinion. Two verses identical except for where the editor broke
    a compound score 1.0 here and below 1.0 on tokens, and the difference between those
    two numbers is itself evidence about the row.

    Word division and the m/anusvara spelling are folded together here, deliberately: once
    the boundaries are gone the two spellings of one nasal cannot be told apart by position,
    so unifying them is the only self-consistent choice (see _ANY_NASAL).
    """
    return unicodedata.normalize(
        "NFC", _ANY_NASAL.sub(ANUSVARA_LETTER, folded.replace(" ", ""))
    )


def token_dice(a: str, b: str) -> float:
    """Sørensen-Dice over the token *sets* -- the measure the staging metadata used."""
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 0.0
    return round(2 * len(sa & sb) / (len(sa) + len(sb)), 4)


def char_ratio(a: str, b: str) -> float:
    """Character-level ratio on the sandhi-insensitive forms."""
    import difflib

    if not a and not b:
        return 0.0
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 4)


def exact_after_fold(a_text: str, a_script: str | None, b_text: str, b_script: str | None) -> bool:
    """True only when the two witnesses are character-identical after the stated fold."""
    return fold_sanskrit(a_text, a_script) == fold_sanskrit(b_text, b_script)
