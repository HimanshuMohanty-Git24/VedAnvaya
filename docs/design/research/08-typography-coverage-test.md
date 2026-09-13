# Font coverage, measured against the corpus's own bytes

Run during Phase 1. Method: load each candidate from Google Fonts in Edge (Chromium), render
each character to a canvas twice, once with the face first in the stack and once with only
Times New Roman, and compare the alpha channel. Identical pixels mean the face did not supply
the glyph and the browser fell back. Reproduce with
`frontend/.tmp/brandcheck/raster2.mjs`.

Test strings are not invented. They are the bytes the live API returns for RV 1.1.1,
AVS 1.1.1, VSM 1.1 and SV CHANDA 1.1.1.

## Result

`+` the face has the glyph. `X` the browser fell back.

| Face | IAST | Devanagari | Vedic marks |
|---|---|---|---|
| Fraunces | **missing ṁ (U+1E41) and ṅ (U+1E45)** | none | none |
| Inter | complete | none | none |
| **Tiro Devanagari Sanskrit** | **complete** | **complete** | **complete** |
| Gentium Book Plus | complete | none | none |
| Noto Serif Devanagari | **missing ṛ ṝ ḷ ṣ ṭ ḍ ṇ ṁ ṃ ṅ ḥ ḻ ḹ** | complete | complete |
| Noto Sans Devanagari | same as Noto Serif | complete | complete |

IAST set tested: a ā ī ū ṛ ṝ ḷ ś ṣ ṭ ḍ ṇ ṁ ṃ ṅ ñ ḥ ḻ ḹ.
Devanagari set: अ आ क ष त्र ज्ञ क्ष्म्य ॐ.
Vedic marks tested on अ: U+0951 udātta, U+0952 anudātta, U+1CDA, U+1CE1, U+A8E0, U+1CF5.

## What this changes

### Fraunces cannot set Sanskrit, and the failure is not local

Two missing glyphs sounds survivable. It is not, because of what a mid-word fallback does to
the rest of the word. Rendering RV 1.1.1 in Fraunces produced `víśva‾rupā́ṇi` where every other
face produced `víśvā rūpā́ṇi`: the macron came off the ā, floated up, and landed between the
words. `Vāyú` rendered with the macron sitting over the **y**.

The cause is that ṁ and ṅ force a run break, and Chromium's HarfBuzz-driven fallback
re-resolves mark attachment across that break. So a single missing character corrupts marks on
characters the face does have. Anusvāra is in almost every verse in the corpus.

**Rule: Sanskrit is never set in Fraunces, in any size, including headings.** Fraunces is the
English display face. A heading reading "Ṛgveda" or "vaiśvāmitro madhucchandāḥ" is Sanskrit and
takes the Sanskrit face. Adding a designed fallback after Fraunces does not fix this; it
relocates the run break rather than removing it.

### The brand board's Devanagari pair cannot set the Rigveda

The board names Noto Serif Devanagari and Noto Sans Devanagari for Sanskrit. Measured, neither
carries the IAST letters with a dot below. The Rigveda and the Atharvaveda, which are 16,391
of the corpus's 20,210 mantras, are held **in IAST only**. So the board's Sanskrit faces are
exactly the wrong faces for four fifths of the corpus's Sanskrit.

### Tiro Devanagari Sanskrit is the only face that covers the whole corpus

It carries complete IAST, complete Devanagari with conjuncts, and the Vedic Extensions block,
in one family. That matters beyond convenience: it is the only way to guarantee that an
accented verse is shaped by a single font, which is the condition for the marks landing where
they belong.

It is by Fiona Ross and John Hudson, the Murty Classical Library face, OFL, and served as
WOFF2 from Google Fonts. It has one weight, 400, and an italic.

## The type system this settles on

| Role | Face | Notes |
|---|---|---|
| Display, English only | Fraunces | Variable. Hold `SOFT` at 0 and `WONK` at 0, bind `opsz` to the rendered size, cap weight below 700. Never Sanskrit. |
| UI, body, metadata, controls | Inter | Variable, `opsz` 14 to 32. Carries full IAST, so entity names in chrome are safe. |
| All Sanskrit, both scripts, verse and display | Tiro Devanagari Sanskrit | One weight. Emphasis comes from size and colour, not from bolding a face that has no bold. |

Noto Serif Devanagari and Noto Sans Devanagari are dropped. Keeping one of them for compact
Devanagari would reintroduce a second Sanskrit face for no coverage gain and would put two
different Devanagari designs on the same page.

Gentium Book Plus is held in reserve as an IAST fallback only, not loaded.

## Loading

Tiro's Google subsets are 180 KB for Devanagari, 13 KB latin-ext, 26 KB latin. `next/font`
preserves the per-subset `unicode-range`, so the 180 KB file is requested only by a page that
actually renders a Devanagari character. The homepage hero does render one, वेदान्वय, so the
homepage pays it. Whether that wordmark should instead be drawn as paths is left to the
performance phase, measured rather than guessed.

## Carried into the CSS, from the brand research

Three defaults break Devanagari and all three have to be set explicitly rather than inherited:
`letter-spacing` must be 0 on Devanagari, because tracking fragments the śirorekhā into
visible gaps; ligatures must not be disabled, because conjuncts are implemented as
substitutions; and line-height on verse must be at least 2.0, because anudātta sits below the
baseline and svarita above the headline and both can land on one akṣara.
