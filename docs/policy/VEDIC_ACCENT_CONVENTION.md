# Frozen rule: the Vedic accent convention for Devanagari corpora

**Status:** FROZEN. Settled from repository and source evidence; no human
adjudication was required. Closes the accent-convention item that had been
blocking Atharvaveda accent comparison.

## The two conventions

**A — udātta unmarked.** Anudātta and svarita are marked; udātta is left
bare. This is the marking system of the European Vedic editions and of the
printed Devanagari the project holds.

| Mark | Codepoint | Unicode's name for it | Its function in convention A |
|---|---|---|---|
| bar below the akṣara | `U+0952` | DEVANAGARI STRESS SIGN ANUDATTA | anudātta |
| stroke above the akṣara | `U+0951` | DEVANAGARI STRESS SIGN UDATTA | **svarita** |
| (no mark) | — | — | udātta, and unaccented |

**B — udātta marked.** Udātta (`U+0301`) and independent svarita (`U+0300`)
are marked; anudātta is bare. The project holds this only in Latin
transliterations (VedaWeb RV, GRETIL AV). **No Devanagari corpus in this
repository uses convention B.**

## The rule

1. Devanagari corpora store **convention A, exactly as printed**. `U+0952`
   is the bar below and means anudātta; `U+0951` is the stroke above and
   means svarita.
2. `text_original` is the source reading and is **never** rewritten by a
   normalizer. `text_nfc` is `normalize_nfc(text_original)` and nothing
   else.
3. Accent folding is a **derived comparison form only**
   (`ACCENT_STRIPPED_COMPARISON`, `SEARCH_NORMALIZED`).
   `comparison_form(..., SOURCE_ORIGINAL)` is the identity function.
4. The stripping set in `src/vedagraph/normalize/unicode.py` contains the
   codepoints of **both** conventions, so accent-stripping is
   convention-blind by construction and needs no per-corpus branch.

## Which convention each corpus actually stores

Measured from the canonical records, not from documentation.

| Corpus | Script | Evidence | Convention |
|---|---|---|---|
| RV `GRETIL.RV.AUFRECHT.TEI.2019` | Latin | `U+030D` ×74,801, `U+0331` ×100,507 | A |
| RV `VEDAWEB.RV.BOOK01-10` | Latin | `U+0301` ×28,825, `U+0300` ×422 | B |
| YV `WIKISOURCE_SA.YV.VSM` | Devanagari | `U+0951` ×17,204, `U+0952` ×24,329 | A |
| AV Roth & Whitney 1856 | Devanagari | bar below / stroke above, udātta bare | A |

The Yajurveda's convention was established **structurally, not from its
labels**: across the 1,974 accented VSM records the akṣara following a
`U+0952` is unmarked 23,220 times and carries `U+0951` only 47 times, and
the distance from a `U+0952` to the next `U+0951` is exactly 2 in 12,797 of
17,204 cases. That intervening unmarked akṣara is the udātta, which is the
signature of convention A. The same signature appears in GRETIL's Latin RV
and is absent from both convention-B corpora.

## Yajurveda side gate

The Yajurveda comparison convention **is** the one the Atharvaveda pipeline
needs. Both are convention A in Devanagari with the same two codepoints, so
the AV corpus can be compared against the existing normalization path with
no new convention and no change to the YV corpus.

## A naming trap worth stating once

Unicode names `U+0951` *DEVANAGARI STRESS SIGN UDATTA*, but under convention
A that glyph is the **svarita**. Prose in this repository refers to it as
svarita and gives the Unicode name alongside, so that a reader who looks the
codepoint up does not conclude the code is wrong. No code branches on the
label.
