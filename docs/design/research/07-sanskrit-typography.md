# 07 - Sanskrit and Indic typography, transliteration, and normalization

Agent 7 research note for **VedAnvaya** (Next.js 16 / React 19 frontend over the frozen VedaGraph API).
Date: 2026-09-13. Backend at `http://127.0.0.1:8000`, API version 1.0.0.

**Status: COMPLETE. Five tasks answered. Two recommendations change shipped code.**

Headline results, each backed by measurement rather than by reading a font's marketing page:

1. The brand brief's Devanagari choice is **correct and is vindicated by measurement**. Noto Sans Devanagari and Noto Serif Devanagari cover 100% of the Vedic codepoints this corpus actually contains. No change is required. One optional upgrade (Tiro Devanagari Sanskrit) is justified for display sizes only, on conjunct quality, not on Vedic coverage.
2. The brand brief's Latin choice is **wrong for the verse text, and the code that shipped is worse**. The fonts currently loaded (Geist, Newsreader) cannot render the opening line of the Rigveda. Inter and Fraunces cannot either. This is a live defect, not a theoretical one.
3. **Derived Devanagari for the Rigveda and Atharvaveda must not ship** on the library we were asked to evaluate. The failure is not that accents are dropped. It is that they are silently replaced by a different and wrong notation.

---

## Method, and why this note contains numbers instead of adjectives

Font vendors and transliteration libraries both describe themselves generously. Every claim below was checked against an artifact:

- **Font coverage** was read from the actual `cmap` of the actual binary, pulled from `github.com/google/fonts` at `main`, using `fontTools` 4.65.0.
- **Rendering** was checked by shaping real corpus strings through **HarfBuzz** (`uharfbuzz` 0.56.1), the same shaper Chrome, Firefox and Safari use. A `.notdef` count of zero means the font can render the string; anything above zero means the browser will fall back for those characters and split the cluster.
- **Transliteration** was checked by installing the package and converting **1,083 real IAST surfaces from 478 live passages** fetched from the running API, not by converting one hand-picked example.
- **The corpus itself** was censused rather than assumed. 263 Devanagari passages and 478 IAST passages were fetched and every codepoint counted.

The distinction between *round-trip lossless* and *correctly rendered* is load-bearing throughout this note, and Task 3 contains a case where a library scores 97.4% on the first while failing 100% on the second. A metric that looks like success is not the same as success.

---

## What the corpus actually contains

This is the ground truth everything else is measured against. It was read from the API, not from the design brief.

### The two romanised surfaces are not one convention, they are two

Every Rigveda passage carries two IAST surfaces, and they encode the Vedic pitch accents **differently**:

| Surface | Witness | Accent marks used |
|---|---|---|
| `PRIMARY` | `GRETIL.RV.AUFRECHT` | **U+0331** combining macron below (anudatta), **U+030D** combining vertical line above (svarita), U+0310 combining candrabindu |
| `PARALLEL_WITNESS` | `VEDAWEB.AUFRECHT` | **U+0301** combining acute (udatta), **U+0325** combining ring below (vocalic r) |

The Atharvaveda `PRIMARY` (`GRETIL.AVS.SAUNAKA.ACCENTED`) uses the **U+0301 acute** convention, like VedaWeb and unlike the Rigveda primary.

Measured from RV 1.1.1:

```
PRIMARY  : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||
           U+030D x6, U+0331 x6
PARALLEL : agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam
           U+0301 x1, U+0325 x1
```

**All corpus text is already NFC.** Verified across every sample: `normalize('NFC', text) == text` was true in every case. Nothing in the pipeline needs to normalize on the way in. This matters a great deal in Tasks 3 and 5.

### The Devanagari corpus needs exactly six Vedic codepoints

Censused over 461 Devanagari surfaces from 263 live passages:

| Codepoint | Occurrences | Name |
|---|---|---|
| U+0951 | 1,861 | DEVANAGARI STRESS SIGN UDATTA |
| U+0952 | 2,618 | DEVANAGARI STRESS SIGN ANUDATTA |
| U+1CEA | 105 | VEDIC SIGN ANUSVARA BAHIRGOMUKHA |
| U+1CEC | 1 | VEDIC SIGN ANUSVARA VAMAGOMUKHA WITH TAIL |
| U+1CED | 105 | VEDIC SIGN TIRYAK |
| U+A8F3 | 113 | DEVANAGARI SIGN CANDRABINDU VIRAMA |

Three of these six live **outside the main Devanagari block**: U+1CEA, U+1CEC and U+1CED are in **Vedic Extensions (U+1CD0..U+1CFF)** and U+A8F3 is in **Devanagari Extended (U+A8E0..U+A8FF)**. A font that covers only U+0900..U+097F will render four distinct marks as tofu. This is the concrete requirement, and it is why "does it have Devanagari" is the wrong question to ask a font.

A real Yajurveda line showing all four of the exotic marks at once:

```
VSM 1.1  इ॒षे त्वो॒र्जे त्वा॑ वा॒यव॑ स्थ ... माघश॑ᳪं᳭सो ...
         U+0951 x16, U+0952 x19, U+1CEA x1, U+1CED x1
```

The cluster `ᳪं᳭` is U+1CEA + U+0902 + U+1CED, a three-character Vedic nasal notation. It is the single most demanding thing in the corpus typographically.

**The Samaveda in this build carries no accent marks at all.** Of 63 Samaveda Devanagari surfaces sampled, zero contained U+0951, U+0952, or any Devanagari Extended combining digit. The Samaveda's characteristic numeric svara notation (U+A8E0..U+A8F1) **does not occur in this corpus**. Any design that promises to show Samavedic musical notation would be promising something the data does not hold.

---

## TASK 1 - Vedic accent rendering on the web

### The decisive test

Nine strings were shaped through HarfBuzz against every candidate: the real VSM 1.1 and VSM 40.1 lines, an isolated U+A8F3 cluster, udatta and anudatta on a bare consonant, the Samavedic numeric svara, three Vedic tone marks, the Atharvavedic independent svarita, and five conjuncts. A font passes only if **`.notdef` is zero on all nine**.

### Results

| Font | Licence | WOFF2 | Google Fonts | U+0951/0952 | Vedic Ext (of 48) | Dev Ext (of 32) | Conjunct ratio | mark/mkmk | notdef | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **Noto Sans Devanagari** | OFL 1.1 | yes | yes | **YES / YES** | **41** | **32** | 0.68 | Y / Y | **0** | **PASS. Ship for UI and body.** |
| **Noto Serif Devanagari** | OFL 1.1 | yes | yes | **YES / YES** | **41** | **32** | 0.68 | Y / Y | **0** | **PASS. Ship for display.** |
| **Tiro Devanagari Sanskrit** | OFL 1.1 | yes | yes | **YES / YES** | **43** | 30 | **0.94** | N / N (abvm+blwm) | **0** | **PASS. Best conjuncts and widest Vedic coverage.** |
| Shobhika | OFL 1.1 | yes | no (IIT Bombay) | YES / YES | 41 | 6 | **0.94** | N / N | 3 (U+A8E1..E3) | Near-pass. Fails Samavedic digits only. |
| Tiro Devanagari **Hindi** | OFL 1.1 | yes | yes | YES / YES | **0** | 4 | 0.91 | N / N | **10** | **FAIL. Not the Sanskrit cut.** |
| Annapurna SIL | OFL 1.1 | yes | yes | YES / YES | **0** | 32 | 0.71 | N / N | 6 | FAIL on Vedic Extensions. |
| Mukta | OFL 1.1 | yes | yes | YES / YES | 39 | 1 | 0.88 | N / N | 4 | FAIL on U+A8F3 and digits. |
| Eczar | OFL 1.1 | yes | yes | YES / YES | 0 | 1 | 0.82 | Y / Y | 9 | FAIL. |
| Pragati Narrow | OFL 1.1 | yes | yes | YES / YES | 4 | 28 | 0.74 | Y / Y | 6 | FAIL. |
| Vesper Libre | OFL 1.1 | yes | yes | YES / YES | 0 | 0 | 0.76 | Y / N | 10 | FAIL. |
| Yantramanav | OFL 1.1 | yes | yes | YES / YES | 0 | 0 | **0.59** | N / N | 10 | FAIL. Worst conjuncts too. |
| Sahitya | OFL 1.1 | yes | yes | YES / YES | 0 | 0 | 0.76 | Y / Y | 10 | FAIL. |
| Martel / Halant | OFL 1.1 | yes | yes | YES / YES | 0 | 0 | - | N / N | - | FAIL. |
| Noto **Serif** (Latin) | OFL 1.1 | yes | yes | no | 0 | 0 | - | Y / Y | - | No Devanagari at all. Not the same font as Noto Serif Devanagari. |
| Adishila, Sahadeva, Siddhanta, Chandas, Uttara, BharatiVaidika | see note | - | no | unverified | unverified | unverified | - | - | - | Not distributed via Google Fonts. Recorded as **unverified**, not guessed. See note below. |

Conjunct ratio is the fraction of 34 real Sanskrit conjuncts (ksa, jna, tra, dva, hma, sta, ddha, stra and others) that shape to a **single ligated glyph** rather than to half-forms or a visible halant. Higher is more traditional.

### The findings that matter

**Noto Sans Devanagari and Noto Serif Devanagari are complete for this corpus.** Both cover all six Vedic codepoints the data actually uses, both shape all nine test strings with zero `.notdef`, and both carry full `mark` + `mkmk` + `abvm` + `blwm` + `ccmp` positioning. The brand brief is correct and needs no change on Vedic grounds.

This is confirmed independently by what Google actually serves. The `@font-face` block returned by the Google Fonts CSS2 API for Noto Sans Devanagari declares:

```
unicode-range: U+0900-097F, U+1CD0-1CF9, U+200C-200D, U+20A8, U+20B9, U+20F0,
               U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B09;
```

Vedic Extensions and Devanagari Extended are both in the served subset. Note the range stops at **U+1CF9**, so U+1CFA (VEDIC SIGN DOUBLE ANUSVARA ANTARGOMUKHA, added in Unicode 12) is absent. **This does not matter here: U+1CFA does not occur in the corpus.** Verified by census, not assumed.

**Tiro Devanagari Sanskrit is the real discovery, but not for the reason expected.** John Hudson's Sanskrit cut is measurably better at conjuncts than Noto (**0.94 versus 0.68**, a 38% relative improvement on true ligature formation) and has the widest Vedic Extensions coverage of anything tested (43/48, including U+1CF7 ATIKRAMA and U+1CFA, both of which Noto lacks). It shapes every test string cleanly.

Its apparent weakness is a mirage. Tiro Sanskrit covers only 108 of 128 Devanagari-block codepoints, but **every one of the 20 it omits is a non-Sanskrit letter**: OE, OOE, AW, UE, UUE, ZHA, GGA, JJA, GLOTTAL STOP, MARWARI DDA, DDDA, BBA, and the U+0953/U+0954 transliteration accents. These are Kashmiri, Sindhi, Marwari and Bihari extensions. None occurs in Vedic Sanskrit. The census confirms Tiro covers 100% of what this corpus contains. The narrow charset is a deliberate Sanskrit scoping, not a gap.

**The Hindi cut is genuinely different, and the difference is exactly Vedic.** Tiro Devanagari **Hindi** has **0/48** Vedic Extensions against the Sanskrit cut's 43/48, and fails 10 of the shaping tests including the real VSM 40.1 line (missing U+1CEA, U+1CED) and U+A8F3. Choosing the wrong Tiro cut would silently break the Yajurveda. If Tiro is adopted, the family name must be pinned to `Tiro Devanagari Sanskrit`.

**Annapurna SIL's reputation does not survive measurement.** It is widely recommended for Sanskrit and it does carry all 32 Devanagari Extended codepoints, but it has **0/48 Vedic Extensions** and fails on U+1CEA, U+1CED, U+1CD0..U+1CD2 and U+1CE1. It cannot render the Yajurveda line in this corpus.

**Shobhika (Sandhi, IIT Bombay) is very close.** OFL, ties Tiro on conjuncts at 0.94, covers 41/48 Vedic Extensions, and shapes the real Yajurveda line cleanly. It fails only on the Samavedic combining digits U+A8E1..U+A8E3, which **this corpus does not contain**. Its practical disqualifier is distribution, not quality: it is not on Google Fonts, so it must be self-hosted and converted to WOFF2 by hand, and it lacks `mark`/`mkmk`.

**On the traditional scholar fonts** (Adishila, Sahadeva, Siddhanta, Chandas, Uttara, BharatiVaidika): none is distributed through Google Fonts, so none was evaluated as a binary here and **their coverage is recorded as unverified rather than guessed**. They are also the wrong tool for this job regardless of quality. They are desktop faces from the pre-webfont era, several predate the Vedic Extensions block entirely (added in Unicode 5.2, 2009), several encode Vedic marks in the Private Use Area rather than at their Unicode codepoints, and their licences are generally "free to use" grants rather than OFL, which is not the same as a licence to redistribute a WOFF2 from your own origin. Since the two Noto faces already cover 100% of the corpus, there is no coverage gap for them to fill.

### Recommendation

**(a) Prominent Sanskrit display (verse openings, hero text, passage headings)**

Use **Noto Serif Devanagari**, as the brief specifies. It is complete for this corpus, it has full mark positioning, and it is already a `next/font/google` import away.

*Optional upgrade, justified but not required:* **Tiro Devanagari Sanskrit** at display sizes only. The concrete improvement is conjunct formation: 32 of 34 test conjuncts ligate properly against Noto's 23 of 34. At 32px and above this is the difference between a text that looks set and one that looks assembled, and specifically the difference between ksa rendering as a single traditional ligature and rendering as ka-halant plus sa. This is a **typographic quality** improvement, not a Vedic correctness improvement, and it should be described that way. If adopted, it must be `Tiro Devanagari Sanskrit`, never the Hindi cut, and it must not be used below about 20px where its low-contrast, narrow-set Sanskrit proportions lose legibility.

**(b) Body Sanskrit (the reading column)**

Use **Noto Serif Devanagari** to match the reading serif, or **Noto Sans Devanagari** if the reading column stays sans. Both are complete. Do not switch to Tiro here: its dense conjuncts plus its lack of `mark`/`mkmk` makes accented Vedic text harder to read at body size, and explicit mark positioning is worth more than ligature elegance when a line carries nineteen anudattas.

**(c) Compact Sanskrit in UI chrome and graph labels**

Use **Noto Sans Devanagari**, which is what ships today. It is complete, it is the most compact of the passing faces (1,117 glyphs, 642 KB source TTF against Tiro's 1,835 and 762 KB), and it has real mark positioning which matters most when marks are small. **Do not use Tiro or Shobhika here.**

**Net change to the brand brief: none is required.** The brief's Noto Serif Devanagari / Noto Sans Devanagari pairing is correct. Tiro Devanagari Sanskrit is offered as an evidence-backed display-only option with a named, measured benefit and a named risk.

---

## TASK 2 - IAST accent rendering in Latin type

This task found a **live defect in shipped code**.

### The shipped fonts cannot render the first line of the Rigveda

`src/app/globals.css` currently sets:

```css
.sanskrit {
    font-family: var(--font-reading), var(--font-devanagari), Georgia, serif;
}
```

`--font-reading` is **Newsreader**, loaded in `src/app/layout.tsx`. So every romanised Rigveda and Atharvaveda verse on the site is rendered in Newsreader first. Shaping the opening of RV 1.1.1 through HarfBuzz:

```
Newsreader  a̱gnim ī̍ḻe   notdef=1   MISSING: U+030D, U+1E3B   mark y-offsets = [0, 0]
Geist       a̱gnim ī̍ḻe   notdef=3   MISSING: U+030D, U+0331, U+1E3B
```

Newsreader has no glyph for **U+030D** (the GRETIL svarita, which occurs 2,455 times in the 351-verse sample) and no glyph for **ḻ** (U+1E3B). Geist additionally lacks **U+0331** (the GRETIL anudatta, 3,273 occurrences in the same sample).

Two consequences, both visible:

1. The browser falls back **per character**. It renders the base letter from Newsreader and the combining mark from whatever fallback font the OS offers. The mark is then positioned by a font that never saw the base, so it lands wrong. This is the "fallback splits the cluster" failure, and it is the reason a mark can appear beside a letter rather than above it.
2. Where Newsreader does render two marks on one base, the measured mark y-offsets are **[0, 0]**: both marks are placed at the same vertical position, so they **collide**. Newsreader declares `mark` and `mkmk` but has only 24 of 112 combining marks, and the pair we need is not among them.

### Coverage of the marks this corpus actually uses

Rows are the marks measured from the live API, not a generic IAST inventory.

| Mark | Geist | Newsreader | Inter | Fraunces | Gentium Plus | Charis SIL | Noto Serif | EB Garamond | Source Serif 4 |
|---|---|---|---|---|---|---|---|---|---|
| U+030D vertical line above (GRETIL svarita) | NO | **NO** | **NO** | **NO** | YES | YES | YES | YES | NO |
| U+0331 macron below (GRETIL anudatta) | **NO** | YES | **NO** | YES | YES | YES | YES | YES | YES |
| U+0301 acute (VedaWeb udatta) | YES | YES | YES | YES | YES | YES | YES | YES | YES |
| U+0325 ring below (VedaWeb vocalic r) | NO | **NO** | **NO** | **NO** | YES | YES | YES | YES | NO |
| U+0310 candrabindu | NO | NO | NO | NO | YES | YES | YES | YES | NO |
| ḻ U+1E3B | NO | **NO** | YES | YES | YES | YES | YES | YES | YES |
| ṛ U+1E5B | NO | NO | YES | YES | YES | YES | YES | YES | YES |
| ṁ U+1E41 | NO | NO | YES | **NO** | YES | YES | YES | YES | NO |
| ṣ ḥ ṭ ḍ ṇ ṅ ḷ ṃ | NO | NO | YES | mostly | YES | YES | YES | YES | YES |
| ā ī ū ś ñ | YES | YES | YES | YES | YES | YES | YES | YES | YES |

| Font | `mark` | `mkmk` | `ccmp` | Combining U+0300..036F | Latin Ext Additional U+1E00..1EFF | RV 1.1.1 notdef |
|---|---|---|---|---|---|---|
| Geist | Y | Y | Y | 22/112 | 99/256 | **3** |
| Newsreader | Y | Y | N | 24/112 | 97/256 | **1** |
| Inter | Y | Y | Y | 66/112 | 255/256 | **2** |
| Fraunces | **N** | **N** | **N** | 21/112 | 154/256 | **1** |
| **Gentium Plus** | Y | Y | Y | **108/112** | **256/256** | **0** |
| **Gentium Book Plus** | Y | Y | Y | **108/112** | **256/256** | **0** |
| **Charis SIL** | Y | Y | Y | 104/112 | **256/256** | **0** |
| **Noto Serif** | Y | Y | Y | **112/112** | **256/256** | **0** |
| **Noto Sans** | Y | Y | Y | **112/112** | **256/256** | **0** |
| EB Garamond | Y | **N** | N | 75/112 | 256/256 | 0 (but marks collide) |
| Source Serif 4 | Y | Y | Y | 21/112 | 142/256 | **1** |

### On Inter and Fraunces specifically

The brief names these as the Latin faces. Neither can carry the verse text.

**Inter** is the better of the two and is perfectly good for UI. It has proper `mark` and `mkmk`, 255 of 256 Latin Extended Additional characters, and it renders every precomposed IAST letter correctly. But it carries only 66 of 112 combining marks and **lacks U+030D, U+0325 and U+0310**, which are exactly three of the five accent marks this corpus uses. It fails RV 1.1.1 with notdef=2.

**Fraunces is the worse case, and it fails in a way that is easy to miss.** It has **no `mark` and no `mkmk` GPOS at all**. Every combining mark it does carry is placed at the default position with no attachment. Measured mark y-offsets for Fraunces are **0 on every test**, including two marks stacked below one base, where the second should be displaced downward. So Fraunces will render `ṛ̱` with both marks piled on top of each other. It also lacks U+030D, U+0325, U+0310, ṁ, ṅ and ṝ. Fraunces is a display face and this is a normal thing for a display face to lack; it simply must not be given accented Sanskrit.

**Confirming the mark positioning works where it should.** The passing faces show real displacement, which is what `mkmk` is for:

```
Charis SIL    ṛ + macron-below   second mark y-offset = -195/1000 em  (pushed clear of the dot)
Charis SIL    ā + vertical-line  mark y-offset        = +181/1000 em  (raised clear of the macron)
Gentium Plus  ṛ + macron-below   second mark y-offset = -244/1000 em
Noto Serif    ṛ + macron-below   second mark y-offset = -183/1000 em
Fraunces      ṛ + macron-below   second mark y-offset =    0          COLLISION
EB Garamond   every test                              =    0          COLLISION
```

### Recommendation

**Use a dedicated face for the IAST verse text. Do not use the UI face.**

**Primary recommendation: Noto Serif.** It has the **most complete combining-mark coverage of anything tested (112/112)**, complete Latin Extended Additional (256/256), full `mark` + `mkmk` + `ccmp`, and zero notdef on real corpus strings. It is on Google Fonts, OFL, available as WOFF2 through `next/font/google`, and it is **metrically and stylistically a sibling of Noto Serif Devanagari**, which solves half of Task 4 for free. Choosing the Noto pair means the romanised verse and the Devanagari verse are designed to sit together.

**Equally defensible alternative: Gentium Plus or Gentium Book Plus (SIL).** 108/112 combining marks, 256/256 Latin Extended Additional, full mark positioning, zero notdef, OFL, on Google Fonts. Gentium was designed by SIL specifically for scholarly transcription of the world's languages and it looks the part: it reads as an academic edition rather than as a website. Gentium **Book** Plus is the heavier cut and is the better choice for screen body text; plain Gentium Plus is noticeably light at small sizes. Choose Gentium over Noto Serif if the design wants the verse column to feel like a critical edition; choose Noto Serif if it should feel like part of the same system as the Devanagari.

**Charis SIL** is the third option and the most robust for small sizes (it is a slab-ish Bitstream Charter derivative designed for low-quality reproduction). 104/112 combining, 256/256, full positioning, zero notdef.

**Do not use** Source Serif 4 (missing U+030D and U+0325) or EB Garamond (renders but has no `mkmk`, so stacked marks collide).

Keep **Geist or Inter for UI chrome** where no Sanskrit appears. Keep **Fraunces for display Latin only**, never for verse.

### Required CSS

```css
/* The verse column gets its own stack. The Devanagari fallback must come
   after the Latin face, because these surfaces are romanised, and it must
   be present so a mixed line never drops to a system font. */
.sanskrit,
.verse-iast {
    font-family: var(--font-verse), var(--font-devanagari), Georgia, serif;

    /* Do NOT set text-rendering: optimizeLegibility. mark/mkmk/ccmp are part
       of HarfBuzz's default feature set and are applied unconditionally in
       every current browser; optimizeLegibility adds nothing here and has a
       history of disabling kerning on large text in Blink. Leave it at auto. */
    text-rendering: auto;

    /* ccmp/mark/mkmk are on by default. Naming them is harmless documentation
       but changes nothing. What DOES matter is not switching them off. */
    font-variant-ligatures: common-ligatures;
    font-kerning: normal;

    /* Stacked marks are tall. Measured ink extent of the real RV 1.1.1 line:
       Gentium Plus 1.306em, Gentium Book Plus 1.316em, Charis SIL 1.247em,
       Noto Serif 1.220em. line-height must clear the tallest, with leading. */
    line-height: 1.9;

    /* Never let a cluster break. */
    overflow-wrap: break-word;
    word-break: normal;
    hyphens: none;
}

/* Ascenders and descenders of stacked marks can be clipped by an ancestor
   with overflow:hidden even when line-height is adequate. Give the verse
   block explicit room rather than relying on the line box. */
.verse-iast {
    padding-block: 0.15em;
    overflow: visible;
}
```

One practical warning that matters more than any CSS property: **the font stack must not fall back mid-cluster.** If the first font lacks U+030D, the browser takes the mark from a fallback and positions it with the wrong metrics. The only reliable fix is to put a font that has *all* the marks first. That is why the recommendation is a dedicated face rather than a longer fallback chain.

---

## TASK 3 - IAST to Devanagari transliteration: is it honest and is it lossless?

**Verdict: (c) DO NOT SHIP.** Not because accents are lost, but because they are silently replaced by a **different and wrong notation**, and because the base text is corrupted on the most famous verse in the corpus.

### The package

`@indic-transliteration/sanscript`

| Property | Value |
|---|---|
| Version tested | **1.3.3**, published 2025-06-08 (latest) |
| Release cadence | 1.3.1 Feb 2024, 1.3.2 and 1.3.3 both Jun 2025. Maintained but slow. |
| Licence | MIT |
| Declared deps | `toml ^2.3.6`, `@indic-transliteration/common_maps ^1.0.2` |
| Actual runtime deps | **none**. `sanscript.js` contains **zero `require()` calls**. All 82 schemes are inlined as literal objects across 10,078 lines. The two declared deps are never loaded at runtime. |
| Module format | **CJS only**. `main: sanscript.js`, no `module`, no `exports` map, no ESM build. |
| ESM named imports | **FAIL.** `import { t } from '...'` throws `SyntaxError: Named export 't' not found`. Default import works. |
| TypeScript types | Yes, hand-written `types/sanscript.d.ts` is shipped. |
| Size | raw **184 KB**, gzip **30.8 KB**, brotli **19.2 KB** |
| Tree-shaking | **impossible**. Single CJS file, all 82 scripts (Ahom, Tibetan, Khmer, Warang Citi and so on) in one module scope. Converting IAST to Devanagari pulls in all of them. |
| React 19 / Next 16 | Compatible. Pure functions, no React, no DOM, no Node APIs. The only costs are the CJS interop and the un-shakeable 30.8 KB gzip. |

### The decisive question, answered

**Does Sanscript round-trip the Vedic accent marks? No. Across 1,083 real corpus surfaces and three candidate schemes, it produced U+0951 zero times and U+0952 zero times.**

The mechanism is visible in the library's own scheme table. Printing `Sanscript.schemes.iast.accents` gives the Devanagari-to-roman mapping it uses:

```
DEVANAGARI U+0951 (udatta)      <->  roman side U+032D  COMBINING CIRCUMFLEX ACCENT BELOW
DEVANAGARI U+0952 (anudatta)    <->  roman side U+0952  (the Devanagari character ITSELF)
DEVANAGARI U+1CE1 (AV svarita)  <->  roman side U+0300  COMBINING GRAVE
DEVANAGARI U+A8E1 (Samavedic combining digit ONE) <-> roman side U+0301 COMBINING ACUTE
DEVANAGARI U+A8E2 <-> U+00B2 superscript two ... and so on through U+A8F1
```

Three facts follow, and together they settle the question:

1. **Sanscript expects U+032D for udatta. Our corpus uses U+030D and U+0301.** There is no mapping for U+030D or U+0331 anywhere in the table. The GRETIL primary surface uses nothing the library recognises as an accent.
2. **Sanscript represents anudatta on the roman side as the literal Devanagari character U+0952.** So Latin-to-Devanagari can only produce an anudatta if the input already contained one.
3. **The acute accent is bound to U+A8E1, the Samavedic combining digit one.** This is the fatal one. VedaWeb and the Atharvaveda primary both use the acute for **udatta**. Sanscript converts it to the **Samavedic numeric svara**, which is a different notation system belonging to a different Veda.

### Real test output

Input string 1, the GRETIL primary surface of RV 1.1.1:

```
INPUT : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||
INPUTcp: U+0061 U+0331 U+0067 U+006E U+0069 U+006D U+0020 U+012B U+030D U+1E3B ...

--- iast -> devanagari
    OUT : अ̱ग्निम् ई̍ऴे पु̱रोहि̍तꣳ य̱ज्ञस्य̍ दे̱वम् ऋ̱त्विज̍म् । होता̍रꣳ रत्न̱धात̍मम् ॥
    cp  : U+0905 U+0331 U+0917 U+094D U+0928 U+093F U+092E U+094D U+0020 U+0908 U+030D U+0934 ...
    U+0951 udatta: false   U+0952 anudatta: false
    untransliterated-Latin-residue: U+0331 U+030D U+0331 U+030D U+0331 U+030D U+0331 U+0331 U+030D U+030D U+0331 U+030D
```

Read the codepoints. The output is `अ` followed by **U+0331 COMBINING MACRON BELOW**, a *Latin* combining mark, stacked on a Devanagari akshara. Every accent in the verse survives as a Latin mark sitting on a Devanagari base. That is not transliteration, it is two scripts fused into one cluster.

Input string 2, the VedaWeb parallel surface:

```
INPUT : agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam

--- iast -> devanagari
    OUT : अग्नि꣡म् ईऌए पुरो꣡हितꣳ यज्ञ꣡स्य देव꣡म् ऋत्वि꣡जम् हो꣡तारꣳ रत्नधा꣡तमम्
    cp  : U+0905 U+0917 U+094D U+0928 U+093F U+A8E1 U+092E ...
    U+0951 udatta: false   U+0952 anudatta: false
```

Every acute has become **U+A8E1**, the Samavedic combining digit one. A reader who knows the notation would read a Rigvedic verse annotated in Samavedic musical numerals. That is not a lost accent, it is a false statement about the text.

### The base text is also wrong, on the first word of the Rigveda

Independently of accents:

```
īḷe   ->  ईऌए    (U+0908 U+090C U+090F)     should be ईळे
ḷ     ->  ऌ      (U+090C VOCALIC L vowel)   should be ळ (U+0933 retroflex LA)
ḻ     ->  ऴ्     (U+0934 + dangling virama) should be ळ
ṁ     ->  ꣳ      (U+A8F3 CANDRABINDU VIRAMA) should be ं (U+0902)
```

`īḷe` is the second word of RV 1.1.1, the first verse of the Rigveda. Sanscript maps the retroflex `ḷ` to the **vocalic ḷ vowel**, and because a vowel cannot take a following matra, the `e` is then forced out as an independent `ए`. Two cascading errors in one syllable, in the most quoted line in the corpus, under every scheme tested.

Words that Sanscript handles correctly, for balance: `ratnadhātamam`, `viśvā`, `triṣaptāḥ`, `sūnave`, `svastaye`, `ṛtvijam` all convert cleanly. The base transliteration is largely sound. It breaks specifically on `ḷ`, `ḻ`, `ṁ`, and every accent.

### Corpus-scale measurement, and the trap in it

1,083 real IAST surfaces from 478 live passages:

```
## SCHEME: iast
  GRETIL.RV.AUFRECHT  (n=351, the Rigveda PRIMARY display surface)
     round-trip IAST->Deva->IAST identical : 120/351  (34.2%)
     output contains stray LATIN chars     : 351/351  (100.0%)
     output contains U+0951 udatta         : 0/351
     output contains U+0952 anudatta       : 0/351
     most common stray Latin chars         : U+0331 x3273   U+030D x2455

  VEDAWEB.AUFRECHT  (n=351)
     output contains U+A8E1 (Samavedic 1)  : 351/351
     output contains U+0951 udatta         : 0/351

  GRETIL.AVS.SAUNAKA.ACCENTED  (n=127, the Atharvaveda PRIMARY surface)
     output contains U+A8E1 (Samavedic 1)  : 127/127
     output contains U+0951 udatta         : 0/127

  GRETIL.AVS.SAUNAKA.UNACCENTED  (n=127)
     round-trip identical                  : 127/127  (100.0%)
     output contains stray LATIN chars     : 4/127  (3.1%)
```

**Now the trap.** Run the same corpus through the `iso` scheme and the round-trip score jumps:

```
## SCHEME: iso
  GRETIL.RV.AUFRECHT
     round-trip IAST->Deva->IAST identical : 342/351  (97.4%)
     output contains stray LATIN chars     : 351/351  (100.0%)
```

**97.4% round-trip fidelity coexists with 100% visual corruption.** The round-trip succeeds *because* the stray Latin marks pass through untouched in both directions. A pipeline that never converts a character will round-trip it perfectly. Round-trip fidelity is therefore the wrong acceptance test, and had it been the only test run, this feature would have shipped.

Measuring rendering correctness instead, by counting characters that are simply wrong for Vedic Sanskrit:

```
## iso  (over all 1,083 surfaces)
   U+A8E1 x5791  COMBINING DEVANAGARI DIGIT ONE (Samavedic numeric svara)
   U+0946 x2490  SHORT E MATRA   (Sanskrit e is always long; this is Dravidian)
   U+094A x2297  SHORT O MATRA   (Sanskrit o is always long)
   U+095C x398   DDDHA / nukta RRA (the Hindi flap, NOT vocalic r)

   surfaces with at least one wrong char or stray Latin:
       GRETIL.RV.AUFRECHT              351/351  (100.0%)
       VEDAWEB.AUFRECHT                351/351  (100.0%)
       GRETIL.AVS.SAUNAKA.ACCENTED     127/127  (100.0%)
       GRETIL.AVS.SAUNAKA.UNACCENTED   127/127  (100.0%)
```

The `iso` scheme scores better on round-trip and worse on truth. Because ISO 15919 writes long e as `ē` and short e as `e`, feeding it IAST (where `e` is always long) converts **every** long e and o into a short Dravidian matra, and turns `ṛ` into `ड़`, the Hindi flap consonant.

**The only clean configuration found anywhere in the matrix** is scheme `iast` applied to **unaccented** input: 100% round-trip, 0 to 3.1% wrong characters. But **the Rigveda has no unaccented surface.** Both of its surfaces are accented. So for the flagship corpus, 10,552 mantras, there is no clean input at all.

### Can a pre-map rescue it? Partly, and the failure is instructive

Since the pipeline works when fed Sanscript's own convention, the obvious repair is to translate our marks into its marks first. Verified that the pipe itself is sound:

```
probe: a॒gnim hotā̭ram   (U+0952 for anudatta, U+032D for udatta)
   -> अ॒ग्निम् होता॑रम्
   U+0951 present: true   U+0952 present: true
```

So it is a convention mismatch, not a missing capability. But applying the pre-map to real corpus text breaks something else:

```
premap: U+0331 -> U+0952,  U+030D -> U+032D  (applied on NFD, then recomposed)
  input  : a̱gnim ī̍ḻe pu̱rohi̍taṁ ...
  output : अ॒ग्निम् ई॑ल्॒ए पु॒रोहि॑तꣳ ...
  U+0951: true   U+0952: true   Latin residue: NONE
```

The accents now work. But `ḻe` became `ल्॒ए`: **la + virama + anudatta + independent E**. The cause is that **U+0331 is overloaded**. It is both the GRETIL anudatta mark *and* the second half of the precomposed letter `ḻ` (U+1E3B LATIN SMALL LETTER L WITH LINE BELOW). Decomposing to NFD to find the accents also decomposes `ḻ`, and the pre-map then turns a letter's own diacritic into a pitch accent.

Any repair built on decomposing this text will hit the same wall. The accent and the letter are the same codepoint.

### Aksharamukha: the capability exists, the shipping vehicle does not

`aksharamukha` on npm, version **2.3.0-32**, published 2026-05-25. Tested empirically for completeness.

It is **materially better**. On the GRETIL Rigveda primary surface:

```
GRETIL.RV.AUFRECHT  n=351
   produced U+0951 udatta   : 351/351  (100%)
   produced U+0952 anudatta : 351/351  (100%)
   stray Latin in output    : 0/351    (0.0%)
   round-trip identical once the two cosmetic conventions are folded: 351/351 (100.0%)
```

(The two folded conventions are the anusvara spelling `ṁ` vs `ṃ` and the danda spelling `|` vs `.`. Nothing else differs.)

Sample output, which is publication-quality Vedic Devanagari:

```
IN  : i̱hendrā̱gnī upa̍ hvaye̱ tayo̱r it stoma̍m uśmasi | tā soma̍ṁ soma̱pāta̍mā ||
DEV : इ॒हेन्द्रा॒ग्नी उप॑ ह्वये॒ तयो॒र् इत् स्तोम॑म् उश्मसि । ता सोमं॑ सोम॒पात॑मा ॥
```

**But it cannot ship, and it does not solve the Atharvaveda either.**

| Blocker | Measurement |
|---|---|
| **Licence** | **GPL-3.0-only.** Shipping it in a Next.js client bundle carries copyleft obligations over the frontend. |
| **Size** | **16.8 MB** package, **29.5 MB** with dependencies. |
| **Runtime** | Depends on `pyodide ^0.28.3`. It is a full CPython WASM runtime, not a JS library. |
| **Init cost** | **6,360 ms measured** to first conversion, on a warm local Node process. |
| **Coverage gap** | On the **acute-accent** surfaces (VedaWeb, and the Atharvaveda PRIMARY) it converts **0** accents and leaves **100%** stray Latin, exactly like Sanscript. It solves the Rigveda primary surface only. |

The licence point deserves precision: running a GPL tool to *produce data* does not make the data GPL. Output is not a derivative work of the tool. So Aksharamukha is legitimate as an **offline, build-time** generator if this is ever wanted. It is not legitimate as a client-side dependency.

### Unicode NFC vs NFD

**Sanscript requires NFC input and silently corrupts NFD input.** It does not merely mishandle the accents; it destroys the base letters.

```
S1 GRETIL via iast: NFC-in and NFD-in give identical output? false
   NFC-out: अ̱ग्निम् ई̍ऴे पु̱रोहि̍तꣳ ...
   NFD-out: अ̱ग्निम् इ̄̍ल्̱ए पु̱रोहि̍तꣳ ...
   NFC-out normalized == NFD-out normalized? false
```

Under NFD, `ī` (U+012B) decomposes to `i` + U+0304 and Sanscript renders `इ` plus a stray macron instead of `ई`. `ā` loses its matra. The two outputs are **not** equivalent even after re-normalizing, so this is genuine data loss and not a representation difference.

The Devanagari-to-roman direction is normalization-insensitive (`true`), because Devanagari has no canonical decompositions for these characters.

**The corpus is already NFC, so this is safe today. It becomes a defect the moment anything in the pipeline normalizes to NFD**, which is exactly what a naive accent-stripper does. See Task 5.

### Recommendation and disclosure wording

**Recommendation: (c) do not ship derived Devanagari for the Rigveda or the Atharvaveda.**

The reasoning is not that the feature is imperfect. It is that the specific failure mode cannot be made honest by a disclosure:

- If accents were **dropped**, option (a) would be right. A note saying the accents are not carried would be true, and a reader would be correctly informed.
- What actually happens is that accents are **replaced by a different notation** (U+A8E1, Samavedic numeric svara) or **rendered as Latin marks on Devanagari aksharas**. A reader who can read Devanagari would be shown a specific, wrong claim about the text. No disclosure makes that honest, because the disclosure would have to say "the marks you see are not the marks in the text and mean something else," at which point there is no reason to show them.
- The base text is additionally wrong on `īḷe`, the second word of RV 1.1.1.
- For a product whose stated ethic is that a derived rendering is never presented as a witness, and whose API goes out of its way to report `NOT_BUILT` rather than `null`, shipping visibly wrong Devanagari would cost more credibility than the feature is worth.

**Option (b), unaccented-only, is not available for the Rigveda.** Both Rigveda surfaces are accented; there is no unaccented input to use. It would be available for the Atharvaveda alone, where `GRETIL.AVS.SAUNAKA.UNACCENTED` converts at 100% round-trip and 3.1% wrong characters. Shipping derived Devanagari for one Veda and not the other, on a site whose whole argument is that the four Samhitas are one corpus, is worse than shipping neither.

**What to do instead:** keep reporting `devanagari: NOT_BUILT` and keep the existing caveat, which is already honest and already precise. The API's own text is better than anything a derived rendering would add:

> No passage in this corpus carries both scripts: 16,391 Rigvedic and Atharvavedic mantras are held in romanised transliteration only and 3,819 Samavedic and Yajurvedic ones in Devanagari only. A missing script is a property of what was ingested for that corpus and not of the text, which is why it is reported as NOT_BUILT and not as null.

**If a future backend phase wants this feature**, the path is named and measured: run **Aksharamukha offline as a build-time step** over the GRETIL Rigveda primary surface, where it is 100% correct and 100% lossless; store the result as a new labelled surface in the corpus; serve it as data. Solve the acute-accent convention (VedaWeb, Atharvaveda primary) separately, because no library tested handles it. Do not put a transliterator in the browser.

**Exact user-facing disclosure wording**, for use only if a corrected derived rendering is ever shipped. No em-dashes, as required:

> This Devanagari is derived. It was generated from the romanised text this archive holds, and no manuscript or printed witness in Devanagari exists for this passage in this build. The romanised line above it is the text of record. Where the two disagree, the romanised line is correct. Read this rendering as an aid to recognition, not as evidence.

And, if it were ever shipped in a state where accents did not carry, the second paragraph would need to be:

> The Vedic pitch accents are not carried in this derived rendering. The accented romanised text above is the only place in this build where the udatta, anudatta and svarita of this passage are recorded.

---

## TASK 4 - Multiscript typographic alignment

### Measured metrics

All values normalised to a 1000-unit em, read from the actual binaries.

| Font | upem | x-height/em | cap-height/em | hhea asc | hhea desc | winAsc+winDesc | measured ink height, real accented line |
|---|---|---|---|---|---|---|---|
| Geist | 1000 | 0.5300 | 0.7100 | 1.0050 | -0.2950 | 1.350 | - |
| Newsreader | 2000 | 0.4260 | 0.6700 | 0.7350 | -0.2650 | 1.429 | 1.154 |
| Inter | 2048 | 0.5459 | 0.7275 | 0.9688 | -0.2412 | 1.430 | 1.122 |
| Fraunces | 2000 | 0.4820 | 0.7000 | 0.9780 | -0.2550 | 1.475 | - |
| **Noto Serif** | 1000 | 0.5360 | 0.7140 | 1.0690 | -0.2930 | 1.458 | **1.220** |
| **Gentium Plus** | 2048 | 0.4541 | 0.6152 | 1.0986 | -0.3662 | 1.465 | **1.306** |
| **Charis SIL** | 2048 | 0.4819 | 0.6709 | 1.1963 | -0.4395 | 1.636 | **1.247** |
| **Noto Sans Devanagari** | 1000 | 0.5360 | 0.6220 | 0.8960 | -0.4080 | **1.906** | **1.184** |
| **Noto Serif Devanagari** | 1000 | 0.6230 | 0.7150 | 0.9300 | -0.6250 | **2.199** | **1.169** |
| Tiro Devanagari Sanskrit | 1000 | 0.4780 | 0.6990 | 0.7550 | -0.2450 | 1.636 | 1.203 |
| Shobhika | 1000 | 0.5000 | 0.7000 | 1.1300 | -0.6000 | 1.730 | 1.474 |

"Measured ink height" is the real vertical extent of the shaped RV 1.1.1 accented IAST line, or the VSM 40.1 accented Devanagari line, computed from glyph bounding boxes plus HarfBuzz y-offsets. It is the number that decides clipping.

### The two findings

**1. Noto Serif Devanagari asks for a 2.199em line box, and the shipped CSS gives it 2.1em.**

```css
.devanagari { line-height: 2.1; }   /* current */
```

With Noto Sans Devanagari (winBox 1.906em) this is fine. **If the display face moves to Noto Serif Devanagari as recommended in Task 1, 2.1 is below its 2.199em ink box** and descenders on stacked vowel signs can clip against an ancestor with `overflow: hidden`. Raise it.

**2. The Latin and Devanagari x-heights are close for the Noto pair and far apart for the current pair.**

`size-adjust` needed to make the Devanagari x-height match the Latin x-height:

| Latin face | Noto Sans Dev | Noto Serif Dev | Tiro Dev Sanskrit |
|---|---|---|---|
| Geist (0.5300) | 98.9% | 85.1% | 110.9% |
| **Newsreader (0.4260)** | **79.5%** | **68.4%** | 89.1% |
| Inter (0.5459) | 101.8% | 87.6% | 114.2% |
| Noto Serif (0.5360) | **100.4%** | **86.0%** | 112.1% |
| Gentium Plus (0.4541) | 84.7% | 72.9% | 94.9% |

Newsreader against Noto Serif Devanagari needs a **68.4%** correction. That is an enormous mismatch, and it is why mixed lines currently look pasted together: the Devanagari is effectively set 46% larger than the Latin beside it.

**Noto Serif against Noto Sans Devanagari needs 100.4%, which is to say none at all.** This is the strongest practical argument for the Task 2 recommendation: adopting Noto Serif for the IAST verse makes the multiscript alignment problem disappear rather than requiring correction.

### Concrete configuration

```tsx
// src/app/layout.tsx
import { Geist, Noto_Serif, Noto_Sans_Devanagari, Noto_Serif_Devanagari } from "next/font/google";

// UI chrome. No Sanskrit ever renders in this face.
const geist = Geist({
    variable: "--font-ui",
    subsets: ["latin"],
    display: "swap",
});

// The romanised verse column. 112/112 combining marks, full mark+mkmk.
// Metrically a sibling of the Devanagari faces below.
const notoSerif = Noto_Serif({
    variable: "--font-verse",
    subsets: ["latin", "latin-ext"],   // latin-ext carries U+1E00..1EFF
    display: "swap",
    adjustFontFallback: true,
});

// Devanagari body and UI chrome.
const devSans = Noto_Sans_Devanagari({
    variable: "--font-devanagari",
    subsets: ["devanagari", "latin"],
    display: "swap",
});

// Devanagari display only.
const devSerif = Noto_Serif_Devanagari({
    variable: "--font-devanagari-display",
    subsets: ["devanagari", "latin"],
    display: "swap",
});
```

`next/font/google` self-hosts the WOFF2 at build time, so there is no third-party connection and no render-blocking stylesheet. **`display: "swap"` plus `adjustFontFallback: true` is what prevents layout shift**: Next computes a local fallback with matching metrics and emits `size-adjust`, `ascent-override` and `descent-override` on an `@font-face` for it. Leave `adjustFontFallback` at its default (true) on the Latin faces. Next does not synthesise a Devanagari fallback, which is the reason the Devanagari face must be loaded rather than relied on as a system font.

```css
:root {
    /* Measured: Noto Serif x-height 0.5360, Noto Sans Devanagari 0.5360.
       Ratio 100.4%, so no correction is needed for the body pairing.
       Noto Serif Devanagari is larger on the body and does need one. */
    --dev-display-adjust: 0.86;
}

/* Romanised verse (Rigveda, Atharvaveda). Latin first, Devanagari as a
   safety net so a stray Devanagari character never reaches a system font. */
.sanskrit,
.verse-iast {
    font-family: var(--font-verse), var(--font-devanagari), Georgia, serif;
    font-size: clamp(1.18rem, 0.95rem + 0.9vw, 1.65rem);
    /* Gentium 1.306em / Noto Serif 1.220em measured ink. 1.9 clears both. */
    line-height: 1.9;
    letter-spacing: 0;      /* never track accented Sanskrit */
    hyphens: none;
    text-rendering: auto;
}

/* Devanagari verse (Samaveda, Yajurveda), body size. */
.devanagari {
    font-family: var(--font-devanagari), sans-serif;
    /* Noto Sans Devanagari winBox 1.906em. 2.0 clears it with leading. */
    line-height: 2.0;
    letter-spacing: 0;
}

/* Devanagari at display size. */
.devanagari-display {
    font-family: var(--font-devanagari-display), var(--font-devanagari), serif;
    /* Noto Serif Devanagari winBox 2.199em. 2.25 clears it. 2.1 DOES NOT. */
    line-height: 2.25;
    /* x-height 0.6230 vs Noto Serif Latin 0.5360 -> scale down to match. */
    font-size: calc(1em * var(--dev-display-adjust));
}

/* Devanagari in UI chrome and graph labels: compact, but the marks still
   need room. Do not go below 1.6 or the udatta will touch the line above. */
.chip .devanagari,
.graph-label .devanagari {
    font-family: var(--font-devanagari), sans-serif;
    line-height: 1.6;
    font-size: 0.95em;   /* Noto Sans Dev runs slightly large beside Geist */
}
```

### On baseline versus shirorekha

A practical note, because this is where multiscript pairings usually go wrong. Devanagari does **not** align to the Latin baseline in any meaningful visual sense. Its optical anchor is the **shirorekha**, the headstroke along the top of the akshara, and the reader's eye tracks that line the way it tracks the x-height in Latin.

The consequence: matching cap-heights or baselines produces a pairing that measures correct and looks wrong. **Match the Latin x-height to the Devanagari body height** (the distance from baseline to shirorekha), which is what the `sxHeight` metric approximates in these fonts and what the `size-adjust` table above is computed from. That is why the Noto Serif / Noto Sans Devanagari pairing at 100.4% works without correction: their x-heights already agree, so the Latin x-line and the Devanagari shirorekha sit at the same optical height and the mixed line reads as one system.

Do not attempt to correct with `font-size-adjust` in CSS. It is now widely supported but it operates per-element and interacts badly with the `clamp()` sizing above. Prefer `size-adjust` inside `@font-face` (which `next/font` already emits for fallbacks) or an explicit `font-size` multiplier as shown, because both are inspectable in one place.

---

## TASK 5 - Unicode normalization and search

### The recorded trap, restated precisely

The project memory records that "inline accents break literal quote matching," where a citation checker failed because accented text did not match literally. The mechanism is now measurable, and it is worse than a matching failure: **the obvious fix corrupts the text.**

### Rule 1: strip combining marks from NFC, never from NFD

This is the single most important recommendation in this section.

```
input                     : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | ...
strip-from-NFC  (CORRECT) : agnim īḻe purohitaṁ yajñasya devam ṛtvijam | ...
strip-from-NFD  (WRONG)   : agnim ile purohitam yajnasya devam rtvijam | ...
```

The NFD strip destroys **every IAST distinction in the corpus**:

```
ḻ U+1E3B -> NFC-strip 'ḻ' | NFD-strip 'l'
ṛ U+1E5B -> NFC-strip 'ṛ' | NFD-strip 'r'
ṁ U+1E41 -> NFC-strip 'ṁ' | NFD-strip 'm'
ṣ U+1E63 -> NFC-strip 'ṣ' | NFD-strip 's'
ḥ U+1E25 -> NFC-strip 'ḥ' | NFD-strip 'h'
ā U+0101 -> NFC-strip 'ā' | NFD-strip 'a'
```

**Why the NFC rule is correct and not merely lucky:** in NFC, anything that *can* compose already *has*. So a combining mark that survives NFC composition is, by construction, one that has no precomposed form with its base. In this corpus that is precisely the set of Vedic accent marks. Stripping combining marks from the NFC form therefore removes exactly the accents and nothing else, with no list of codepoints to maintain and no risk of a future accent being missed.

**The one exception, and its fix.** `r̥` (U+0072 + U+0325 COMBINING RING BELOW), which the VedaWeb surface uses for vocalic r, has no precomposed form. The NFC strip removes the ring and collapses it to plain `r`, losing the vocalic distinction. Fold it to its precomposed equivalent **before** stripping:

```ts
// src/lib/sanskrit-text.ts
const VOCALIC_FOLD: Array<[RegExp, string]> = [
    [/r̥/g, "ṛ"],          // r + ring below   -> ṛ
    [/r̥̄/g, "ṝ"],    // r + ring + macron -> ṝ
    [/l̥/g, "ḷ"],          // l + ring below   -> ḷ
];

/** NFC is what the API already returns. Assert it rather than assume it. */
export function toNfc(s: string): string {
    return s.normalize("NFC");
}

/**
 * Remove Vedic pitch accents while preserving every IAST letter.
 * Strips from NFC, never from NFD: in NFC a surviving combining mark is
 * by construction one with no precomposed form, which in this corpus is
 * exactly the accent set.
 */
export function stripVedicAccents(s: string): string {
    let t = s.normalize("NFC");
    for (const [re, to] of VOCALIC_FOLD) t = t.replace(re, to);
    return t.replace(/\p{Mn}/gu, "").normalize("NFC");
}

/**
 * Aggressive fold for matching only. Never render this.
 * Deliberately destroys IAST distinctions so that a user typing "rtvijam"
 * finds "ṛtvijam".
 */
export function foldForMatch(s: string): string {
    return stripVedicAccents(s)
        .normalize("NFD")
        .replace(/\p{Mn}/gu, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}
```

### Rule 2: three forms, three jobs, and they must not be confused

| Form | Function | Used for | Never used for |
|---|---|---|---|
| **Display** | `toNfc(text)`, unchanged | Rendering the verse | Matching |
| **Copy** | `toNfc(text)` by default; `stripVedicAccents(text)` on the "copy without accents" affordance | Clipboard | Rendering, matching |
| **Match** | `foldForMatch(text)` | Client-side highlight, quote verification, search-as-you-type | Rendering, clipboard |

The specific bug the memory records happens when a checker compares a **display** string against a **quoted** string that went through a different path. The fix is that any literal comparison runs `foldForMatch` on **both sides**, always, with no exceptions. A comparison where only one side is folded is a bug even when it happens to pass.

### Rule 3: two Private Use Area hazards exist in the live data

Both were found by census, not by inspection, and both would render as tofu boxes.

**(a) The `NORMALIZED_FOR_SEARCH` surface contains PUA sentinels.** The backend's own accent-stripped form encodes folded characters as Private Use Area codepoints:

```
UNACCENTED : 'vidmā śarasya pitaraṃ parjanyaṃ śatavṛṣṇyaṃ | tenā te tanve śaṃ ...'
NORMALIZED : 'vidmā śarasya pitara parjanya śatavṣṇya tenā te tanve śa ...'

U+E003 substituted for ṃ   (310 occurrences in sample)
U+E000 substituted for ṛ   (114 occurrences)
U+E001 substituted for ṝ   (1 occurrence)
```

**The backend already guards this correctly**: that surface is returned with `is_displayable: false`, and the OpenAPI description says plainly that `NORMALIZED_FOR_SEARCH` "is an accent-stripped matching form and is wrong to display as the text." **The frontend must honour `is_displayable` and must not render any surface where it is false.** At present `src/app/passage/[key]/page.tsx` filters alternates only on `surface.text && surface.text !== primary?.text`, which does **not** check `is_displayable`. That should be:

```ts
const alternates = (reader.text.surfaces ?? []).filter(
    (surface) => surface.is_displayable && surface.text && surface.text !== primary?.text,
);
```

**(b) One PUA character exists in a surface that IS marked displayable.** Censused across 200 Yajurveda passages:

```
VG:YV:VSM:A07:V003  [PARALLEL_WITNESS]  is_displayable=True
  PUA: U+F15C
  context: ...ेभ्यस् त्वा मरीचिपेभ्यः । देवाशो यस्मै त्वेडे तत् सत्यम् उप...
```

This is a single character in a single passage and it will render as a tofu box in every font, because U+F15C is unassigned in Unicode and no font can legitimately cover it. It is almost certainly a leftover from the Wikisource source. The backend is frozen, so the frontend should **strip or replace unassigned PUA codepoints at render time** rather than display a box:

```ts
/** PUA codepoints cannot be rendered by any font. Drop them at the boundary. */
export function stripPua(s: string): string {
    return s.replace(/[-]/gu, "");
}
```

Apply this in the text-rendering component, not in the fetch layer, so the raw API response stays faithful to what the backend returned.

### Rule 4: the copy-to-clipboard affordance

Offer two actions, labelled so the difference is obvious and the default is faithful:

- **Copy verse** (default). Copies the NFC text exactly as displayed, accents intact. This is what a scholar citing the passage needs.
- **Copy without accents**. Copies `stripVedicAccents(text)`. This is what someone pasting into a search box, a database that mangles combining marks, or a system with a limited font needs.

Both write `text/plain`. Do not offer a "copy as Devanagari" action; per Task 3 there is no derived Devanagari to copy.

A short line of helper text under the control, with no em-dashes:

> Copying without accents removes the Vedic pitch marks and keeps the letters. Use it when pasting into a system that cannot show combining marks. The version with accents is the text of record.

### Rule 5: normalize at the boundary, assert in a test

The corpus is NFC today, verified across every sample. Depend on that, but verify rather than assume, because Task 3 showed that NFD input silently destroys base letters in any transliteration path and a future ingest could change the invariant without warning.

```ts
// src/lib/api.ts, at the point where passage text enters the app
const text = raw.normalize("NFC");
```

and a test that fails loudly if the invariant ever breaks:

```ts
it("every text surface the API returns is already NFC", async () => {
    const p = await getPassage("VG:RV:SAK:M01:S001:V001");
    for (const s of p.text.surfaces) {
        expect(s.text.normalize("NFC")).toBe(s.text);
    }
});
```

---

## Summary of changes this note recommends to shipped code

| # | File | Change | Why |
|---|---|---|---|
| 1 | `src/app/layout.tsx` | Add `Noto_Serif` as `--font-verse` | Geist and Newsreader cannot render RV 1.1.1. Measured notdef 3 and 1. |
| 2 | `src/app/globals.css` | `.sanskrit` uses `var(--font-verse)` first, not `var(--font-reading)` | Same. This is the live defect. |
| 3 | `src/app/globals.css` | `.devanagari` line-height 2.0; add `.devanagari-display` at 2.25 | Noto Serif Devanagari needs a 2.199em box; the current 2.1 is below it. |
| 4 | `src/app/passage/[key]/page.tsx` | Filter alternates on `surface.is_displayable` | `NORMALIZED_FOR_SEARCH` contains PUA sentinels and is flagged not displayable. |
| 5 | `src/lib/sanskrit-text.ts` (new) | `toNfc`, `stripVedicAccents`, `foldForMatch`, `stripPua` | Strip from NFC not NFD; fold both sides before any literal comparison. |
| 6 | - | **Do not** add `@indic-transliteration/sanscript` | Zero correct accents over 1,083 real surfaces. |

---

## Appendix: how to reproduce

```bash
# Font coverage and shaping
pip install fonttools uharfbuzz brotli
# fonts pulled from https://raw.githubusercontent.com/google/fonts/main/ofl/<dir>/<file>.ttf
# Shobhika from https://github.com/Sandhi-IITBombay/Shobhika/releases (v1.05)

# Google's actual served subset, which is the authority on what a browser receives
curl -A "Mozilla/5.0 ... Chrome/131" \
  "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400..700&display=swap"

# Transliteration
npm install @indic-transliteration/sanscript   # 1.3.3
npm install aksharamukha                       # 2.3.0-32, GPL-3.0, 16.8 MB

# Corpus
curl "http://127.0.0.1:8000/api/v1/passages/VG:RV:SAK:M01:S001:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:YV:VSM:A01:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:AV:SAU:K01:S001:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:SV:KAU:CHANDA:P05:D09:V02"
```

Sample sizes used: 1,083 IAST surfaces from 478 passages for the transliteration tests; 461 Devanagari surfaces from 263 passages for the codepoint census; 34 conjuncts and 9 Vedic shaping strings per font across 16 Devanagari faces and 11 Latin faces.

### Sources

- Google Fonts repository, `github.com/google/fonts` at `main` (font binaries, `OFL.txt`, `METADATA.pb`)
- Google Fonts CSS2 API, `fonts.googleapis.com/css2` (served `unicode-range` subsets)
- `github.com/Sandhi-IITBombay/Shobhika`, release v1.05
- `registry.npmjs.org/@indic-transliteration/sanscript` (version, dates, licence, dependencies)
- `github.com/indic-transliteration/sanscript.js` (README; note it documents "lossy scheme" only in terms of script letters and **makes no mention of Vedic accents at all**, so the behaviour reported above is undocumented upstream)
- `registry.npmjs.org/aksharamukha`
- Unicode 16.0 character database, via Python `unicodedata`
- The live VedaGraph API, version 1.0.0
