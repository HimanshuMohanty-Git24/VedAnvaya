# 07 - Sanskrit and Indic typography, transliteration, and normalization

Agent 7 research note for **VedAnvaya** (Next.js 16 / React 19 frontend over the frozen VedaGraph API).
Date: 2026-09-13. Backend at `http://127.0.0.1:8000`, API version 1.0.0.

**Status: COMPLETE. Five tasks answered. Four recommendations change shipped code.**

Headline results, each backed by a measurement against an artifact rather than by a vendor's claim:

1. The brand brief's **Devanagari** choice is **correct and is vindicated by measurement**. Noto Sans Devanagari and Noto Serif Devanagari cover 100% of the Vedic codepoints this corpus actually contains, and the Google CDN serves all of them. No change required. Tiro Devanagari Sanskrit is a justified display-only upgrade.
2. The brand brief's **Latin** choice is wrong for the verse text, and **the code that shipped is worse**. Newsreader fails on 34.1% of IAST character occurrences in the real corpus and Geist on 49.7%. Inter fails on 28.9%. Fraunces has no mark-positioning table at all.
3. **The Google Fonts CDN silently strips the Vedic accent marks from every Latin font.** Verified at binary level: not Noto Serif, not Charis SIL, not Gentium Plus serves U+0331, U+030D or U+0325. The fonts contain them; the served subsets do not. This means `next/font/google` cannot deliver a working IAST verse face and **the Latin verse font must be self-hosted**. Devanagari via the CDN is fine, which makes the trap easy to miss.
4. **Derived Devanagari for the Rigveda and Atharvaveda must not ship** on the library we were asked to evaluate. The failure is not that accents are dropped; it is that they are silently replaced by a different and wrong notation.
5. **This note disagrees with `08-typography-coverage-test.md` on one point and the disagreement is decided by measurement.** That note proposes Tiro Devanagari Sanskrit as the single face for all Sanskrit. Tiro **lacks U+030D**, the GRETIL svarita, which occurs 450,981 times and appears in the primary surface of every accented Rigveda verse, and it renders six tofu boxes on RV 1.1.1. See *Reconciliation* in Task 2. The two notes agree on everything else.

---

## Method, and why this note contains numbers instead of adjectives

Font vendors and transliteration libraries both describe themselves generously. Inter's own site claims support for "combining diacritical marks," and that claim is false for the ones this corpus needs. Every claim below was therefore checked against an artifact:

- **Font coverage** was read from the actual `cmap` of the actual binary (`fontTools` 4.65.0), for both the upstream TTF and, separately, **the WOFF2 the Google CDN actually serves**. Those two are not the same font, and the difference is Task 2's biggest finding.
- **Rendering** was checked by shaping real corpus strings through **HarfBuzz**, the shaper Chrome, Firefox and Safari all use, and by rasterising the output to count overlapping ink. Bounding-box overlap is not collision; a first pass flagged Noto and Tiro as colliding on `ka + ii-matra + udatta` and rasterisation showed zero overlapping pixels. Every collision reported below is pixel-verified.
- **Transliteration** was checked by installing the package and converting **1,083 real IAST surfaces from 478 live passages**, not by converting one hand-picked example.
- **The corpus itself** was censused rather than assumed: 263 Devanagari passages and 478 IAST passages through the API, plus a direct scan of the corpus files.

The distinction between *round-trip lossless* and *correctly rendered* is load-bearing throughout, and Task 3 contains a case where a library scores 97.4% on the first while failing 100% on the second.

---

## What the corpus actually contains

### The two romanised surfaces are not one convention, they are two

Every Rigveda passage carries two IAST surfaces, and they encode the Vedic pitch accents **differently**:

| Surface | Witness | Accent marks used |
| --- | --- | --- |
| `PRIMARY` | `GRETIL.RV.AUFRECHT` | **U+0331** combining macron below, **U+030D** combining vertical line above, U+0310 combining candrabindu |
| `PARALLEL_WITNESS` | `VEDAWEB.AUFRECHT` | **U+0301** combining acute, **U+0325** combining ring below |

The Atharvaveda `PRIMARY` (`GRETIL.AVS.SAUNAKA.ACCENTED`) uses the **U+0301 acute** convention, like VedaWeb and unlike the Rigveda primary.

Measured from RV 1.1.1:

```text
PRIMARY  : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||
           U+030D x6, U+0331 x6
PARALLEL : agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam
           U+0301 x1, U+0325 x1
```

Corpus-wide counts of the five accent marks, from a direct scan of `data/**/*.jsonl`:

| Mark | Occurrences |
| --- | --- |
| U+0331 combining macron below | **606,126** |
| U+030D combining vertical line above | **450,981** |
| U+0301 combining acute | 153,488 |
| U+0325 combining ring below | 52,517 |
| U+0310 combining candrabindu | 9,056 |

**All corpus text is already NFC.** Verified across every sample. Nothing needs to normalize on the way in, which matters a great deal in Tasks 3 and 5.

A terminology note worth carrying, because it affects how the UI should label things. The Unicode proposal that created these characters records that U+0951 *"would, if it were being encoded today, have been named VEDIC TONE SVARITA, since that is its primary use."* U+0951 marks **svarita in the Rigveda but udatta in some schools**. The name of the codepoint is not a safe guide to what the mark means in a given text, and any tooltip should say which tradition it is describing.

### The Devanagari corpus needs exactly six Vedic codepoints

Censused over 461 Devanagari surfaces from 263 live passages:

| Codepoint | Occurrences | Name |
| --- | --- | --- |
| U+0951 | 1,861 | DEVANAGARI STRESS SIGN UDATTA |
| U+0952 | 2,618 | DEVANAGARI STRESS SIGN ANUDATTA |
| U+1CEA | 105 | VEDIC SIGN ANUSVARA BAHIRGOMUKHA |
| U+1CEC | 1 | VEDIC SIGN ANUSVARA VAMAGOMUKHA WITH TAIL |
| U+1CED | 105 | VEDIC SIGN TIRYAK |
| U+A8F3 | 113 | DEVANAGARI SIGN CANDRABINDU VIRAMA |

Three of these six live **outside the main Devanagari block**: U+1CEA, U+1CEC and U+1CED are in **Vedic Extensions (U+1CD0..U+1CFF)** and U+A8F3 is in **Devanagari Extended (U+A8E0..U+A8FF)**. A font covering only U+0900..U+097F renders four distinct marks as tofu. This is why "does it have Devanagari" is the wrong question to ask a font.

```text
VSM 1.1  इ॒षे त्वो॒र्जे त्वा॑ वा॒यव॑ स्थ ... माघश॑ᳪं᳭सो ...
         U+0951 x16, U+0952 x19, U+1CEA x1, U+1CED x1
```

The cluster `ᳪं᳭` is U+1CEA + U+0902 + U+1CED, a three-character Vedic nasal notation, and it is the most demanding thing in the corpus typographically.

**The Samaveda in this build carries no accent marks at all.** Of 63 Samaveda Devanagari surfaces sampled, zero contained U+0951, U+0952 or any Devanagari Extended combining digit. The Samaveda's characteristic numeric svara notation (U+A8E0..U+A8F1) **does not occur in this corpus**. Any design promising Samavedic musical notation would be promising something the data does not hold.

### The accent ordering in this corpus is correct

Unicode's core specification rule **R10** requires the order `syllable + visarga/anusvara + svara`, so `नः॑` and never `न॑ः`. Shaping VedaGraph's real accented text through HarfBuzz against every candidate font produced **zero dotted circles**. A naive heuristic flags 836 apparent violations; shaping proves every one a false positive, because the Yajurveda `U+1CEA + U+0902 + U+1CED` gomukha sequence is valid. **No action needed, and no reordering should be attempted.**

Worth knowing for anyone tempted to be lenient about ordering: every font tested, including the otherwise most complete one, emits a dotted circle for the wrong order under HarfBuzz. Reports that some fonts "forgive" it come from DirectWrite on Windows, not from the shaper browsers use. The UTC declined to change this rule in 2021.

---

## TASK 1 - Vedic accent rendering on the web

### The test

Nine strings were shaped against every candidate: the real VSM 1.1 and VSM 40.1 lines, an isolated U+A8F3 cluster, udatta and anudatta on a bare consonant, the Samavedic numeric svara, three Vedic tone marks, the Atharvavedic independent svarita, and a conjunct set. A font passes only if **`.notdef` is zero on all nine** and ink collisions are zero.

Coverage is against **assigned** codepoints: Vedic Extensions has 43 assigned of 48; Devanagari Extended has 32. "Sama" is U+A8E0..U+A8F1, the combining digits that carry Samavedic notation.

### Results

| Font | Licence | RFN | Google Fonts | U+0951/0952 | VedicExt /43 | DevExt /32 | Sama /18 | Conjunct ligs | Ink collisions | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Tiro Devanagari Sanskrit** | OFL 1.1 | no | yes | **CONFIRMED** | **43** | 30 | 18 | **860** | **0 / 8** | **PASS. Best overall.** |
| **Noto Serif Devanagari** | OFL 1.1 | no | yes | **CONFIRMED** | 41 | **32** | 18 | 293 | **0 / 8** | **PASS. Ship for display.** |
| **Noto Sans Devanagari** | OFL 1.1 | no | yes | **CONFIRMED** | 41 | **32** | 18 | 297 | **0 / 8** | **PASS. Ship for UI and body.** |
| Adishila Vedic | **no redistribution** | - | no | CONFIRMED | **43** | **32** | 18 | - | 0 | **LICENCE-BLOCKED.** |
| Shobhika | OFL 1.1 | no | **no** | CONFIRMED | 41 | 6 | **0** | **1362** | 3 | Near-pass. No Samaveda. |
| Siddhanta | **CC BY-NC-ND 3.0** | - | no | CONFIRMED | 37 | 28 | 18 | - | - | **NonCommercial. Blocked.** |
| Annapurna SIL | OFL 1.1 | **YES** | yes | CONFIRMED | **0** | 32 | 18 | 365 | 1 | **FAIL. 2,627 tofu on this corpus.** |
| Mukta | OFL 1.1 | no | yes | CONFIRMED | 39 | 1 | 0 | 595 | 0 / 8 | FAIL. |
| Pragati Narrow | OFL 1.1 | no | yes | CONFIRMED | 4 | 28 | 18 | 327 | 0 / 8 | FAIL. |
| Chandas | GPL, no font exception | - | no | CONFIRMED | **0** | **0** | 0 | - | - | FAIL. 278 PUA codepoints. |
| Uttara | GPL, no font exception | - | no | CONFIRMED | **0** | **0** | 0 | - | - | FAIL. 210 PUA codepoints. |
| Sahadeva | GPL-2.0+ | - | no | CONFIRMED | **0** | **0** | 0 | - | - | FAIL. Predates the block. |
| Eczar | OFL 1.1 | no | yes | CONFIRMED | 0 | 1 | 0 | 353 | **3 / 8** | FAIL. |
| Vesper Libre | OFL 1.1 | no | yes | CONFIRMED | 0 | 0 | 0 | 254 | **2 / 8** | FAIL. |
| Yantramanav | OFL 1.1 | no | yes | CONFIRMED | 0 | 0 | 0 | 199 | **3 / 8** (76% overlap) | FAIL. Worst tested. |
| Tiro Devanagari **Hindi** | OFL 1.1 | no | yes | CONFIRMED | **0** | 4 | 0 | 476 | 0 / 8 | **FAIL. Not the Vedic cut.** |
| Sahitya, Martel, Halant | OFL 1.1 | no | yes | CONFIRMED | 0 | 0 | 0 | - | - | FAIL. |
| Noto **Serif** (Latin) | OFL 1.1 | no | yes | no Devanagari | 0 | 0 | 0 | - | - | Not the same font as Noto Serif Devanagari. |
| **BharatiVaidika** | - | - | - | **does not exist** | - | - | - | - | - | See below. |

**Every font tested has U+0951 and U+0952. None is ABSENT.** The discriminator is the *extended* blocks and positioning quality, not the two base marks. Any evaluation that stopped at "does it have udatta and anudatta" would have passed Yantramanav.

### The findings that matter

**Noto Sans Devanagari and Noto Serif Devanagari are complete for this corpus.** Both cover all six Vedic codepoints the data uses, both shape all nine test strings with zero `.notdef` and zero ink collisions, and both carry full `mark` + `mkmk` + `abvm` + `blwm` + `ccmp`. The brand brief is correct.

This holds **through the CDN**, which was verified separately by downloading every served WOFF2 subset and reading its cmap:

```text
Noto Sans Devanagari   (3 served subsets, 67,324 bytes total)
  U+0951 SERVED   U+0952 SERVED   U+1CEA SERVED   U+1CED SERVED   U+A8F3 SERVED
Noto Serif Devanagari  (3 served subsets, 69,904 bytes total)
  U+0951 SERVED   U+0952 SERVED   U+1CEA SERVED   U+1CED SERVED   U+A8F3 SERVED
```

The declared `unicode-range` for the devanagari subset is `U+0900-097F, U+1CD0-1CF9, ..., U+A8E0-A8FF`. Note it stops at **U+1CF9**, so U+1CFA is lost via the CDN though present in the self-hosted TTF. **This does not matter here: U+1CFA does not occur in the corpus.** Verified by census, not assumed.

**Tiro Devanagari Sanskrit is the strongest font tested, and the Sanskrit/Hindi difference is not what it is usually said to be.** The common claim is that the cuts differ in i-matra width variants. They do not: both have exactly 4 and both select identically. The real differences are:

- **Vedic coverage: Sanskrit 43/43, Hindi 0/43.** The Hindi cut renders `.notdef` for U+1CDA and U+1CE1 and fails the real VSM 40.1 line on U+1CEA and U+1CED. **Tiro Devanagari Hindi is not a Vedic font.**
- **Conjuncts: 860 ligatures against 476.** `क्ष्ण` gives **one** glyph in the Sanskrit cut and two in the Hindi cut.

Tiro Sanskrit is the only font tested with **43/43 Vedic Extensions**, the only one carrying U+1CF7 ATIKRAMA and U+1CFA. Its 20 omissions from U+0900..097F are all Kashmiri, Marwari and Sindhi letters plus U+0953/U+0954 (DEVANAGARI GRAVE/ACUTE ACCENT, which are **not** the Vedic pitch marks). Its only two gaps in the extended blocks are U+A8FE/U+A8FF (AY, Kashmiri). No Vedic loss. Designed by John Hudson and Fiona Ross, originating in the Murty Classical Library of India face and, in the OFL release, "extended to support additional characters, including signs for Vedic texts."

Three real caveats:

1. **Weight 400 only.** Regular and Italic, no bold. The Italic has full 43/43 Vedic parity. A design needing a bold Devanagari cannot use Tiro alone.
2. **Clipping risk.** Accented stacks reach ink top 1266/1000 em against a `usWinAscent` of 1091. Noto stays inside its own winAscent (1278 against 1407) and is safer. Tiro needs generous `line-height` and no `overflow: hidden` on verse containers.
3. Pair it with Noto Serif Devanagari wherever weight range is needed.

**Bonus, and it is a real one:** Tiro Devanagari Sanskrit is the **only Devanagari font tested that also covers the IAST Latin set** (ṣ ḥ ṁ ṇ ṛ ṭ). Noto Serif and Noto Sans Devanagari lack all of them. For a UI that shows Devanagari and transliteration together in one label, that is one font instead of two.

**Annapurna SIL's reputation does not survive measurement, and SIL agrees.** It has **0/43 Vedic Extensions**, confirmed in the binary, and SIL's own FAQ states: *"We do not currently have plans to add full Vedic support to Annapurna."* It has no MarkToMark lookups at all, producing a 38% ink collision on `ka + candrabindu + udatta`. Shaped against VedaGraph's real corpus it emits **2,627 tofu glyphs**, because the Yajurveda text uses U+1CEA and U+1CED. It also carries **Reserved Font Names** "Annapurna" and "SIL", so a self-hosted WOFF2 subset is a modification and **must be renamed**. It is the only candidate with that constraint. Do not ship it.

**Shobhika is very close and its own claim is precisely accurate.** It says it carries the Vedic accents "required for the proper typesetting of **rgveda and yajurveda**," and that wording is exactly right: 41/43 Vedic Extensions but **6/32 Devanagari Extended and 0/18 Samavedic digits**. It cannot typeset Samaveda. Highest conjunct count measured (1,362). Its practical problems are distribution (not on Google Fonts; `ofl/shobhika` is 404) and weak positioning: only 2 MarkToBase and 2 MarkToMark lookups, no `dist`, no `kern`, giving pixel-verified collisions of 40% of accent ink for U+1CD2 over `kii`.

**The traditional scholar fonts are resolved, and two premises in the brief were wrong.** Chandas and Uttara are by **Mihail Bayaryn**, not Ulrich Stiehl (Stiehl funded and hosts them; his own font is Sanskrit 2003). Sahadeva is by **John Smith** of Cambridge, GPL-2.0+.

- **Chandas** (5,081 glyphs) and **Uttara** (5,092): **0/43 Vedic Extensions, 0/32 Devanagari Extended**, with 278 and 210 PUA codepoints respectively. They encode Vedic accents in the Private Use Area and cannot render U+1CD0..U+1CFF at all.
- **Siddhanta**: **37/43, 28/32, 18/18.** It does map the real codepoints, which corrects the widely repeated claim that all the Bayaryn-lineage fonts are PUA-based. But **CC BY-NC-ND 3.0** blocks commercial use and blocks derivatives, which a WOFF2 subset is.
- **Sahadeva**: 0/43, 0/32. Predates Unicode 5.2.
- **Adishila Vedic** is technically the most complete font tested, **43/43 and 32/32 with zero PUA**. Its licence forbids exactly what is needed: *"you are not allowed to sell, rent, host or distribute them."* Self-hosting a WOFF2 is hosting and distributing. **Disqualified without written permission.**
- **BharatiVaidika does not exist.** Zero hits across GitHub code, repository and filename search, sanskritdocuments.org, wazu.jp and the INDOLOGY archives. It appears to be a conflation of the "Bharati" name with Bayaryn's **Vaidika** IME, which is a keyboard layout and not a font.

A caution on sanskritdocuments.org as a source: it carries no licence statements, and every Devanagari font listed there is legacy 8-bit and non-Unicode.

**One trap in the Noto family.** Plain **Noto Sans** (the Latin face) advertises Vedic Extensions coverage it does not have: 0/43 in the binary. This is a known open issue in the Google Fonts tracker. The Vedic carriers are Noto Sans **Devanagari** and Noto Serif **Devanagari**, and there is no separate "Noto Sans Vedic Extensions" font. Google does not split Vedic out.

### Recommendation for Devanagari

**(a) Prominent Sanskrit display.** Use **Noto Serif Devanagari**, as the brief specifies. Complete, full mark positioning, safe inside its own vertical metrics, available through `next/font/google` and correctly served by the CDN.

*Optional upgrade, justified but not required:* **Tiro Devanagari Sanskrit** at display sizes only. The measured improvement is conjunct formation, 860 ligatures against 293, which at 32px and above is the difference between a text that looks set and one that looks assembled. This is a **typographic quality** improvement, not a Vedic correctness improvement, and it should be described that way. If adopted it must be pinned to `Tiro Devanagari Sanskrit`, it brings only weight 400, and it needs `line-height >= 1.9` with no `overflow: hidden` because its accented stacks exceed its own `usWinAscent`.

**(b) Body Sanskrit.** **Noto Serif Devanagari** to match a reading serif, or **Noto Sans Devanagari** if the reading column stays sans. Both complete. Do not use Tiro here: dense conjuncts plus no `mark`/`mkmk` makes accented Vedic harder to read at body size, and explicit mark positioning is worth more than ligature elegance when a line carries nineteen anudattas.

**(c) Compact Sanskrit in UI chrome and graph labels.** **Noto Sans Devanagari**, which is what ships today. Complete, most compact of the passing faces, real mark positioning, which matters most when marks are small. Do not use Tiro or Shobhika here.

**Net change to the brand brief: none.** The Noto Serif Devanagari / Noto Sans Devanagari pairing is correct and is the recommendation.

### Shipping sizes

Vedic-only subsets (U+0900..097F, 1CD0..1CFF, A8E0..A8FF, ZWJ/ZWNJ, dotted circle, ASCII) with `--layout-features='*'`, as WOFF2:

| Font | Subset size |
| --- | --- |
| Noto Sans Devanagari, static instance at wght=400 | **52 KB** |
| Noto Serif Devanagari, static instance at wght=400 | **54 KB** |
| Shobhika | 187 KB |
| Tiro Devanagari Sanskrit | 197 KB |

Instancing the Noto variable fonts before subsetting cuts them from roughly 244 KB to 54 KB. The CDN route is also fine for Devanagari at 67 to 70 KB across all three served subsets.

---

## TASK 2 - IAST accent rendering in Latin type

This task found **two live defects** and **one systemic trap that would have shipped silently**.

### Defect 1: the app cannot render its own corpus

`src/app/globals.css` sets:

```css
.sanskrit {
    font-family: var(--font-reading), var(--font-devanagari), Georgia, serif;
}
```

`--font-reading` is **Newsreader**, loaded in `src/app/layout.tsx`. So every romanised Rigveda and Atharvaveda verse renders in Newsreader first. Both shipped Latin faces are missing **15 of 20 core IAST letters**, every retroflex and dotted form: ṛ ṝ ḷ ḹ ṅ ṭ ḍ ṇ ṣ ḥ ṁ ṃ ḻ.

Weighted against real character occurrences in the corpus:

| Font | IAST character occurrences it cannot render |
| --- | --- |
| **Geist** (UI) | **49.73%** |
| **Newsreader** (verse) | **34.10%** |
| Inter | **28.85%** |
| Fraunces | 17.22% |
| Source Serif 4 | 17.02% |
| Charis SIL, Gentium Plus, Doulos SIL, Andika, Junicode 2, Noto Serif, Noto Sans | **0.00%** |

Shaping the opening of RV 1.1.1:

```text
Newsreader  a̱gnim ī̍ḻe   notdef=1   MISSING U+030D, U+1E3B   mark y-offsets = [0, 0]
Geist       a̱gnim ī̍ḻe   notdef=3   MISSING U+030D, U+0331, U+1E3B
Inter       a̱gnim ī̍ḻe   notdef=2   MISSING U+030D, U+0331
```

Newsreader's measured mark y-offsets of **[0, 0]** mean both marks land at the same vertical position and **collide**.

**NFD normalization cannot rescue Newsreader.** Re-encoding to decomposed form improves its failure rate from 34.10% to 13.22%, but U+030D (450,981 occurrences), U+0325 and U+0310 are pure combining marks with no precomposed escape. The font must be replaced.

### Defect 2: the Google Fonts CDN strips the Vedic marks from every Latin font

This is the finding that would have shipped silently, because it makes a correct font choice fail anyway.

Every served WOFF2 subset for each candidate was downloaded and its cmap read:

```text
Noto Serif    (8 served subsets, 155,124 bytes total)
  U+0331  ** NOT SERVED **   combining macron below      (GRETIL anudatta, 606,126 in corpus)
  U+030D  ** NOT SERVED **   combining vertical line     (GRETIL svarita,  450,981 in corpus)
  U+0325  ** NOT SERVED **   combining ring below        (VedaWeb vocalic r)
  U+0310  SERVED            combining candrabindu
  U+0301  SERVED            combining acute
  U+1E5B / U+1E41 / U+1E3B  SERVED

Charis SIL    (5 served subsets, 140,748 bytes total)
  U+0331, U+030D, U+0325, U+0310  ** ALL NOT SERVED **
  U+0301, U+1E5B, U+1E41, U+1E3B  SERVED

Gentium Plus  (7 served subsets, 167,112 bytes total)
  U+0331, U+030D, U+0325, U+0310  ** ALL NOT SERVED **
  U+0301, U+1E5B, U+1E41, U+1E3B  SERVED
```

The `latin-ext` range is `U+0100-02BA, U+02BD-02C5, ..., U+1E00-1E9F, ...`. It covers the **precomposed** IAST letters and skips the **combining** block entirely, except for U+0304, U+0308 and U+0329 individually. Noto Serif picks up U+0310 only incidentally, through its `math` subset, whose range reads `U+032F-0330, U+0332-0333` and so deliberately skips U+0331.

**Consequence:** the Rigveda's `PRIMARY` display surface uses U+0331 and U+030D, and **neither is served by the CDN for any Latin font.** The font on disk has them; the font the browser receives does not. `next/font/google` downloads exactly these subsets at build time, so it inherits the gap.

**The Devanagari fonts are unaffected**, which is what makes this easy to miss: a developer verifying "does the CDN serve the Vedic marks" would check Noto Sans Devanagari, see all five served, and conclude the CDN is fine.

**The fix is to self-host the Latin verse face** via `next/font/local`, subsetting from the upstream TTF/WOFF2 with an explicit unicode range that includes U+0300..U+036F. SIL ships WOFF2 in its own release zips. Subsetting locally preserves `mark` and `mkmk` (verified). Charis SIL subsets to roughly **48 KB**.

### Coverage and stacking, measured

Stacking is the second mark's y-displacement in em. `COLLIDE` means the mark lands at y=0, on top of the first.

| Font | ccmp / mark / mkmk | ṛ + U+0331 | ā + U+0301 | ī + U+030D | Corpus loss | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **Charis SIL** | Y / Y / Y | −0.20 | +0.18 | +0.18 | 0.00% | **PASS** |
| **Gentium Plus / Book Plus** | Y / Y / Y | −0.24 | +0.19 | +0.18 | 0.00% | **PASS** |
| **Doulos SIL** | Y / Y / Y | −0.20 | +0.18 | +0.18 | 0.00% | **PASS** |
| **Andika** | Y / Y / Y | −0.20 | +0.17 | +0.17 | 0.00% | **PASS** |
| **Junicode 2.226** | Y / Y / Y | −0.20 | +0.12 | +0.12 | 0.00% | **PASS** (307 mkmk mark glyphs, highest tested) |
| **Noto Serif / Noto Sans** | Y / Y / Y | −0.18 | +0.14 | +0.14 | 0.00% | **PASS** |
| Libertinus Serif | Y / Y / Y | COLLIDE | +0.03 | COLLIDE | 0.00% | FAIL, collision |
| EB Garamond | . / Y / . | COLLIDE | COLLIDE | COLLIDE | 0.00% | FAIL, collision |
| Cardo | Y / Y / . | COLLIDE | COLLIDE | COLLIDE | 0.10% | FAIL, collision |
| Source Serif 4 | Y / Y / Y | −0.18 | +0.16 | **no glyph** | 17.02% | FAIL |
| **Fraunces** | **. / . / .** | COLLIDE | COLLIDE | **no glyph** | 17.22% | **FAIL** |
| **Inter 4.001** | Y / Y / Y | **no glyph** | +0.18 | **no glyph** | **28.85%** | **FAIL** |
| IBM Plex Serif | Y / Y / . | no glyph | COLLIDE | no glyph | 49.73% | FAIL |
| **Brill** | - | - | - | - | - | **Legally unusable on the web. See below.** |

### On Inter, Fraunces and Brill specifically

**Inter 4.001** is good UI type and is not a candidate for verse. It has 66 of 112 combining marks but is missing essentially the entire *below* range: **U+0331, U+0325, U+0329, U+0332 all absent**, plus U+030D. The known issue about `ā` + U+0301 is genuinely fixed; the broader issue covering IPA and complex diacritics remains open and labelled work-in-progress, and the maintainer is still undecided on a stacking system.

**Fraunces fails in a way that is easy to miss.** It has only 21 of 112 combining marks and **no GPOS `mark` table at all**, so no mark-to-base and no mark-to-mark. Every mark it does carry is placed at the default position with no attachment, and every measured y-offset is 0. It will render `ṛ̱` with both marks piled on each other. It also lacks ṁ, ṅ, ṝ and ḹ. This is normal for a display face; it simply must never be given accented Sanskrit.

**Brill is technically excellent and legally unusable here.** Its EULA clause 6 forbids linking to the fonts "through program instructions (including Cascading Style Sheets)" and clause 8 states "embedding the Font in HTML web pages is not allowed." Open Access counts as commercial use and modification (subsetting) is banned. A paid web licence would be required.

### Recommendation for the romanised verse

**Use a dedicated, self-hosted face for the IAST verse text. Do not use the UI face, and do not load it from the CDN.**

**Primary recommendation: Charis SIL, self-hosted via `next/font/local`.** It passes every stacked case with real displacement, carries 104 of 112 combining marks and all 256 Latin Extended Additional characters, loses **0.00%** of the corpus, has the most vertical headroom of the SIL set (its stacked ink fits inside its own metrics, which Gentium's does not), and subsets to about 48 KB WOFF2. It was designed by SIL for exactly this job and it holds up at small sizes.

**Alternatives, all defensible:**

- **Gentium Plus / Gentium Book Plus** if the design wants the verse column to read as a critical edition. Equally complete, slightly more literary. **Set `line-height` explicitly**: its stacked ink (1.325em) exceeds its own default line box (1.465em is the box, but the default leading does not clear it comfortably). Gentium **Book** Plus is the heavier cut and the better choice for screen body text.
- **Junicode 2** is the most scholarly option, with the highest mkmk mark-glyph count of anything tested, at 712 KB subsetted.
- **Noto Serif** is the safe institutional choice and has the additional benefit of being metrically a sibling of Noto Serif Devanagari, which makes Task 4 trivial. **It must still be self-hosted**, for the CDN reason above.

**Do not use** Source Serif 4, EB Garamond, Cardo, Libertinus Serif or IBM Plex Serif.

Keep **Geist or Inter for UI chrome** where no Sanskrit appears. Keep **Fraunces for display Latin only**.

### Reconciliation with `08-typography-coverage-test.md`

A sibling research note reaches a different conclusion and should be read together with this one. It proposes **Tiro Devanagari Sanskrit as the single face for all Sanskrit in both scripts**, dropping Noto Serif Devanagari and Noto Sans Devanagari, on the argument that one face is "the only way to guarantee that an accented verse is shaped by a single font."

**That plan fails on the Rigveda's primary display surface, and the measurement is unambiguous.**

```text
TiroDevanagariSanskrit
  RV 1.1.1 PRIMARY  (GRETIL, U+030D + U+0331)
     notdef = 6   missing = U+030D COMBINING VERTICAL LINE ABOVE
     mark y-offsets = [0, 0, 0, 0, 0, 0]
  RV 1.1.1 PARALLEL (VedaWeb, U+0301 + U+0325)
     notdef = 0

CharisSIL
  RV 1.1.1 PRIMARY   notdef = 0   mark y-offsets = [0, 181, 0, 0, 0, 0, 0, -195, 0, 181, 0, 0]
  RV 1.1.1 PARALLEL  notdef = 0   mark y-offsets = [0, 181]
```

Tiro Devanagari Sanskrit **lacks U+030D**, the GRETIL svarita, which occurs **450,981 times** in the corpus and appears in the `PRIMARY` surface of every accented Rigveda verse. It renders six tofu boxes on the opening line of the Rigveda. Beyond that gap it carries only **19 of 112** combining marks and **54 of 256** Latin Extended Additional characters, and it has **no `mark` and no `mkmk` GPOS at all**. Its GPOS features are `abvm blwf blwm dist kern`: `abvm` and `blwm` are the *Indic* mark-positioning features and apply to Devanagari clusters, not to a Latin base carrying a combining mark. That is why all six mark offsets above are 0 even for the marks it does have.

**Why the sibling test did not catch it, which is the more useful lesson.** Its IAST set was `a ā ī ū ṛ ṝ ḷ ś ṣ ṭ ḍ ṇ ṁ ṃ ṅ ñ ḥ ḻ ḹ`, all **precomposed** letters, and its Vedic marks were tested **on अ**, a Devanagari base. No test placed a Vedic accent mark on a **Latin** base. That combination is not an edge case here; it is what 16,391 of the 20,210 mantras in this corpus are made of. Testing the two alphabets separately cannot find a defect that only exists where they meet.

**What both notes agree on, and it is most of it:**

- Fraunces cannot set Sanskrit. Sibling 08 found mid-word mark corruption (`víśva‾rupā́ṇi`); this note found the cause, which is that Fraunces has no GPOS `mark` table at all. The two findings are the same defect seen from opposite ends.
- Noto Serif Devanagari and Noto Sans Devanagari do not carry the IAST letters. Both notes measured this. It is not an argument against them, because they are Devanagari faces and the romanised verse needs its own Latin face regardless.
- Tiro Devanagari Sanskrit is an excellent **Devanagari** face, the best tested, and its conjunct quality is real.
- `letter-spacing: 0` on Devanagari, ligatures never disabled, verse `line-height` at least 2.0.

**The correction is narrow.** Tiro's coverage claim holds for Devanagari and for *precomposed* IAST. It does not hold for the Vedic accent marks on Latin bases. So the single-face plan should become a two-face plan: **Tiro Devanagari Sanskrit (or Noto Serif Devanagari) for Devanagari, and a dedicated Latin face with full combining-mark support and working `mkmk` for the romanised verse.** The "one font per verse" goal is still satisfied, because no single verse in this corpus mixes the two scripts: the Rigveda and Atharvaveda are romanised only, the Samaveda and Yajurveda are Devanagari only. **One face per verse does not require one face for the corpus.**

### CSS, and what actually matters

```css
.sanskrit,
.verse-iast {
    /* Self-hosted. The CDN does not serve U+0331 or U+030D for any Latin font. */
    font-family: var(--font-verse), var(--font-devanagari), Georgia, serif;

    /* Measured stacked ink of the real RV 1.1.1 line:
       Gentium Plus 1.306em, Gentium Book Plus 1.316em,
       Charis SIL 1.247em, Noto Serif 1.220em.
       1.9 clears all of them with comfortable leading. Minimum safe is 1.5. */
    line-height: 1.9;

    letter-spacing: 0;   /* never track accented Sanskrit */
    hyphens: none;
    overflow-wrap: break-word;
    word-break: normal;
}

/* Diacritics are INK OVERFLOW: they are clipped at the padding edge, not the
   content edge, so an ancestor with overflow:hidden will cut them even when
   line-height is adequate. Clipping was reproduced at line-height: 1.0. */
.verse-iast {
    padding-block: 0.15em;
    overflow: visible;
}
```

**What does nothing:**

- **`text-rendering`.** In Blink it toggles only kerning and ligatures; it never emits `mark` or `mkmk`. It is discouraged generally and has a long bug tail in WebKit. Leave it at `auto`.
- **`font-kerning`.** No effect on mark positioning.
- Naming `ccmp`, `mark` or `mkmk` in `font-feature-settings`. They are in HarfBuzz's default feature set and are normative defaults in CSS Fonts 4.

**What actively breaks it:**

- **`font-feature-settings: "mark" 0`** does reach HarfBuzz and does break mark positioning. The collision was reproduced in Chromium. Setting an unrelated feature does not reset the defaults, so the risk is only from switching `mark` or `mkmk` off explicitly. Do not.

**On font fallback, with a correction.** The received wisdom that fallback "splits the cluster" is only half true, and the half that is true is browser-specific. **Chrome and Safari move the base and its marks together** to the fallback font. **Firefox still splits per character**, a bug open for sixteen years. Either way the result is visible damage: a Chromium screenshot of `a̱gnim` rendered in Inter shows `a̱` in a serif fallback while `gnim` stays in Inter sans, so the typeface changes **inside one word**. The only reliable fix is a first font that has every mark, which is what the recommendation above delivers.

---

## TASK 3 - IAST to Devanagari transliteration: is it honest and is it lossless?

**Verdict: (c) DO NOT SHIP.** Not because accents are lost, but because they are silently replaced by a **different and wrong notation**, and because the base text is corrupted on the most famous verse in the corpus.

### The package

`@indic-transliteration/sanscript`

| Property | Value |
| --- | --- |
| Version tested | **1.3.3**, published 2025-06-08 (latest) |
| Cadence | 1.3.0 Dec 2023, 1.3.1 Feb 2024, 1.3.2 and 1.3.3 both Jun 2025. Maintained, slow. |
| Licence | MIT |
| Declared deps | `toml ^2.3.6`, `@indic-transliteration/common_maps ^1.0.2` |
| Actual runtime deps | **none**. `sanscript.js` contains **zero `require()` calls**. All 82 schemes are inlined across 10,078 lines. The declared deps are never loaded. |
| Module format | **CJS only.** `main: sanscript.js`, no `module`, no `exports` map, no ESM build. |
| ESM named imports | **FAIL.** `import { t } from '...'` throws `SyntaxError: Named export 't' not found`. Default import works. |
| TypeScript types | Yes, hand-written `types/sanscript.d.ts` is shipped. |
| Size | raw **184 KB**, gzip **30.8 KB**, brotli **19.2 KB** |
| Tree-shaking | **impossible.** Single CJS file, all 82 scripts in one module scope. |
| React 19 / Next 16 | Compatible. Pure functions, no React, no DOM, no Node APIs. Costs are CJS interop and 30.8 KB gzip that cannot be shaken. |

### The decisive question, answered

**Does Sanscript round-trip the Vedic accent marks? No. Across 1,083 real corpus surfaces and three candidate schemes, it produced U+0951 zero times and U+0952 zero times.**

The mechanism is in the library's own scheme table. Printing `Sanscript.schemes.iast.accents`:

```text
DEVANAGARI U+0951 (udatta)      <->  roman side U+032D  COMBINING CIRCUMFLEX ACCENT BELOW
DEVANAGARI U+0952 (anudatta)    <->  roman side U+0952  (the Devanagari character ITSELF)
DEVANAGARI U+1CE1 (AV svarita)  <->  roman side U+0300  COMBINING GRAVE
DEVANAGARI U+A8E1 (Samavedic combining digit ONE) <-> roman side U+0301 COMBINING ACUTE
DEVANAGARI U+A8E2 <-> U+00B2 ... through U+A8F1
```

Three facts follow, and together they settle it:

1. **Sanscript expects U+032D for udatta. Our corpus uses U+030D and U+0301.** There is no mapping for U+030D or U+0331 anywhere in the table. The GRETIL primary surface uses nothing the library recognises as an accent.
2. **Anudatta on the roman side is the literal Devanagari character U+0952.** Latin-to-Devanagari can only produce one if the input already contained one.
3. **The acute is bound to U+A8E1, the Samavedic combining digit one.** This is the fatal one. VedaWeb and the Atharvaveda primary both use the acute for **udatta**. Sanscript converts it to the **Samavedic numeric svara**, a different notation belonging to a different Veda.

### Real test output

String 1, the GRETIL primary surface of RV 1.1.1:

```text
INPUT : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||
INPUTcp: U+0061 U+0331 U+0067 U+006E U+0069 U+006D U+0020 U+012B U+030D U+1E3B ...

--- iast -> devanagari
    OUT : अ̱ग्निम् ई̍ऴे पु̱रोहि̍तꣳ य̱ज्ञस्य̍ दे̱वम् ऋ̱त्विज̍म् । होता̍रꣳ रत्न̱धात̍मम् ॥
    cp  : U+0905 U+0331 U+0917 U+094D U+0928 U+093F U+092E U+094D U+0020 U+0908 U+030D U+0934 ...
    U+0951 udatta: false   U+0952 anudatta: false
    untransliterated-Latin-residue: U+0331 U+030D U+0331 U+030D U+0331 U+030D U+0331 U+0331 U+030D U+030D U+0331 U+030D
```

Read the codepoints. The output is `अ` followed by **U+0331 COMBINING MACRON BELOW**, a *Latin* combining mark, stacked on a Devanagari akshara. Every accent survives as a Latin mark on a Devanagari base. That is not transliteration, it is two scripts fused into one cluster.

String 2, the VedaWeb parallel surface:

```text
INPUT : agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam

--- iast -> devanagari
    OUT : अग्नि꣡म् ईऌए पुरो꣡हितꣳ यज्ञ꣡स्य देव꣡म् ऋत्वि꣡जम् हो꣡तारꣳ रत्नधा꣡तमम्
    cp  : U+0905 U+0917 U+094D U+0928 U+093F U+A8E1 U+092E ...
    U+0951 udatta: false   U+0952 anudatta: false
```

Every acute has become **U+A8E1**. A reader who knows the notation would see a Rigvedic verse annotated in Samavedic musical numerals. That is not a lost accent, it is a false statement about the text.

### The base text is also wrong, on the first word of the Rigveda

```text
īḷe   ->  ईऌए    (U+0908 U+090C U+090F)      should be ईळे
ḷ     ->  ऌ      (U+090C VOCALIC L vowel)    should be ळ (U+0933 retroflex LA)
ḻ     ->  ऴ्     (U+0934 + dangling virama)  should be ळ
ṁ     ->  ꣳ      (U+A8F3 CANDRABINDU VIRAMA) should be ं (U+0902)
```

`īḷe` is the second word of RV 1.1.1. Sanscript maps the retroflex `ḷ` to the **vocalic ḷ vowel**, and because a vowel cannot take a following matra the `e` is forced out as an independent `ए`. Two cascading errors in one syllable, in the most quoted line in the corpus, under every scheme tested.

For balance: `ratnadhātamam`, `viśvā`, `triṣaptāḥ`, `sūnave`, `svastaye` and `ṛtvijam` all convert cleanly. The base transliteration is largely sound. It breaks on `ḷ`, `ḻ`, `ṁ`, and every accent.

### Corpus-scale measurement, and the trap in it

1,083 real IAST surfaces from 478 live passages:

```text
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

**Now the trap.** The same corpus through the `iso` scheme:

```text
## SCHEME: iso
  GRETIL.RV.AUFRECHT
     round-trip IAST->Deva->IAST identical : 342/351  (97.4%)
     output contains stray LATIN chars     : 351/351  (100.0%)
```

**97.4% round-trip fidelity coexists with 100% visual corruption.** The round-trip succeeds *because* the stray Latin marks pass through untouched in both directions. A pipeline that never converts a character round-trips it perfectly. Round-trip fidelity is therefore the wrong acceptance test, and had it been the only test run, this feature would have shipped.

Measuring rendering correctness instead, by counting characters that are simply wrong for Vedic Sanskrit:

```text
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

`iso` scores better on round-trip and worse on truth. Because ISO 15919 writes long e as `ē` and short e as `e`, feeding it IAST (where `e` is always long) turns **every** long e and o into a short Dravidian matra, and `ṛ` into `ड़`, the Hindi flap consonant.

**The only clean configuration in the whole matrix** is scheme `iast` on **unaccented** input: 100% round-trip, 0 to 3.1% wrong characters. But **the Rigveda has no unaccented surface.** Both of its surfaces are accented. For the flagship corpus, 10,552 mantras, there is no clean input at all.

### Can a pre-map rescue it? Partly, and the failure is instructive

The pipe itself is sound when fed Sanscript's own convention:

```text
probe: a॒gnim hotā̭ram   (U+0952 for anudatta, U+032D for udatta)
   -> अ॒ग्निम् होता॑रम्
   U+0951 present: true   U+0952 present: true
```

So it is a convention mismatch, not a missing capability. But applying the pre-map to real corpus text breaks something else:

```text
premap: U+0331 -> U+0952,  U+030D -> U+032D  (applied on NFD, then recomposed)
  input  : a̱gnim ī̍ḻe pu̱rohi̍taṁ ...
  output : अ॒ग्निम् ई॑ल्॒ए पु॒रोहि॑तꣳ ...
  U+0951: true   U+0952: true   Latin residue: NONE
```

The accents now work. But `ḻe` became `ल्॒ए`: **la + virama + anudatta + independent E**. The cause is that **U+0331 is overloaded**. It is both the GRETIL anudatta mark *and* the second half of the precomposed letter `ḻ` (U+1E3B). Decomposing to NFD to find the accents also decomposes `ḻ`, and the pre-map turns a letter's own diacritic into a pitch accent. Any repair built on decomposing this text hits the same wall: the accent and the letter are the same codepoint.

### Aksharamukha: the capability exists, the shipping vehicle does not

`aksharamukha` on npm, version **2.3.0-32**, published 2026-05-25. Tested empirically for completeness.

It is **materially better** on the Rigveda primary surface:

```text
GRETIL.RV.AUFRECHT  n=351
   produced U+0951 udatta   : 351/351  (100%)
   produced U+0952 anudatta : 351/351  (100%)
   stray Latin in output    : 0/351    (0.0%)
   round-trip identical once two cosmetic conventions are folded: 351/351 (100.0%)
```

The two folded conventions are the anusvara spelling `ṁ` against `ṃ` and the danda spelling `|` against `.`. Nothing else differs. Sample output, which is publication-quality Vedic Devanagari:

```text
IN  : i̱hendrā̱gnī upa̍ hvaye̱ tayo̱r it stoma̍m uśmasi | tā soma̍ṁ soma̱pāta̍mā ||
DEV : इ॒हेन्द्रा॒ग्नी उप॑ ह्वये॒ तयो॒र् इत् स्तोम॑म् उश्मसि । ता सोमं॑ सोम॒पात॑मा ॥
```

**But it cannot ship, and it does not solve the Atharvaveda either.**

| Blocker | Measurement |
| --- | --- |
| **Licence** | **GPL-3.0-only.** Shipping it in a Next.js client bundle carries copyleft obligations over the frontend. |
| **Size** | **16.8 MB** package, **29.5 MB** with dependencies. |
| **Runtime** | Depends on `pyodide ^0.28.3`. A full CPython WASM runtime, not a JS library. |
| **Init cost** | **6,360 ms measured** to first conversion, warm local Node process. |
| **Coverage gap** | On the **acute-accent** surfaces (VedaWeb, and the Atharvaveda PRIMARY) it converts **0** accents and leaves **100%** stray Latin, exactly like Sanscript. It solves the Rigveda primary surface only. |

The licence point deserves precision: running a GPL tool to *produce data* does not make the data GPL. Output is not a derivative work of the tool. Aksharamukha is therefore legitimate as an **offline, build-time** generator. It is not legitimate as a client-side dependency.

### Unicode NFC vs NFD

**Sanscript requires NFC input and silently corrupts NFD input.** It does not merely mishandle accents; it destroys base letters.

```text
S1 GRETIL via iast: NFC-in and NFD-in give identical output? false
   NFC-out: अ̱ग्निम् ई̍ऴे पु̱रोहि̍तꣳ ...
   NFD-out: अ̱ग्निम् इ̄̍ल्̱ए पु̱रोहि̍तꣳ ...
   NFC-out normalized == NFD-out normalized? false
```

Under NFD, `ī` (U+012B) decomposes to `i` + U+0304 and Sanscript renders `इ` plus a stray macron instead of `ई`. `ā` loses its matra. The two outputs are **not** equivalent even after re-normalizing, so this is genuine data loss.

The Devanagari-to-roman direction is normalization-insensitive, because Devanagari has no canonical decompositions for these characters.

The corpus is already NFC, so this is safe today. **It becomes a defect the moment anything normalizes to NFD**, which is exactly what a naive accent-stripper does. See Task 5.

### Recommendation and disclosure wording

**Recommendation: (c) do not ship derived Devanagari for the Rigveda or the Atharvaveda.**

The reasoning is not that the feature is imperfect:

- If accents were **dropped**, option (a) would be right. A note saying they are not carried would be true and the reader would be correctly informed.
- What actually happens is that accents are **replaced by a different notation** (U+A8E1, Samavedic numeric svara) or **rendered as Latin marks on Devanagari aksharas**. A reader who can read Devanagari would be shown a specific, wrong claim about the text. No disclosure makes that honest, because it would have to say "the marks you see are not the marks in the text and mean something else," at which point there is no reason to show them.
- The base text is additionally wrong on `īḷe`, the second word of RV 1.1.1.
- For a product whose ethic is that a derived rendering is never presented as a witness, and whose API reports `NOT_BUILT` rather than `null` on purpose, shipping visibly wrong Devanagari would cost more credibility than the feature is worth.

**Option (b), unaccented-only, is not available for the Rigveda.** Both Rigveda surfaces are accented. It would be available for the Atharvaveda alone, where `GRETIL.AVS.SAUNAKA.UNACCENTED` converts at 100% round-trip and 3.1% wrong characters. Shipping derived Devanagari for one Veda and not the other, on a site whose argument is that the four Samhitas are one corpus, is worse than shipping neither.

**What to do instead:** keep reporting `devanagari: NOT_BUILT` and keep the existing caveat, which is already honest and already precise:

> No passage in this corpus carries both scripts: 16,391 Rigvedic and Atharvavedic mantras are held in romanised transliteration only and 3,819 Samavedic and Yajurvedic ones in Devanagari only. A missing script is a property of what was ingested for that corpus and not of the text, which is why it is reported as NOT_BUILT and not as null.

**If a future backend phase wants this feature**, the path is named and measured: run **Aksharamukha offline as a build-time step** over the GRETIL Rigveda primary surface, where it is 100% correct and 100% lossless; store the result as a new labelled surface; serve it as data. Solve the acute-accent convention separately, because no library tested handles it. Do not put a transliterator in the browser.

**Exact user-facing disclosure wording**, for use only if a corrected derived rendering is ever shipped. No em-dashes:

> This Devanagari is derived. It was generated from the romanised text this archive holds, and no manuscript or printed witness in Devanagari exists for this passage in this build. The romanised line above it is the text of record. Where the two disagree, the romanised line is correct. Read this rendering as an aid to recognition, not as evidence.

If it were ever shipped in a state where accents did not carry, a second paragraph would be required:

> The Vedic pitch accents are not carried in this derived rendering. The accented romanised text above is the only place in this build where the udatta, anudatta and svarita of this passage are recorded.

---

## TASK 4 - Multiscript typographic alignment

### Measured metrics

Normalised to a 1000-unit em, read from the actual binaries.

| Font | upem | x-height/em | cap-height/em | hhea asc | hhea desc | winAsc+winDesc | measured ink, real accented line |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Geist | 1000 | 0.5300 | 0.7100 | 1.0050 | −0.2950 | 1.350 | - |
| Newsreader | 2000 | 0.4260 | 0.6700 | 0.7350 | −0.2650 | 1.429 | 1.154 |
| Inter | 2048 | 0.5459 | 0.7275 | 0.9688 | −0.2412 | 1.430 | 1.122 |
| Fraunces | 2000 | 0.4820 | 0.7000 | 0.9780 | −0.2550 | 1.475 | - |
| **Charis SIL** | 2048 | 0.4819 | 0.6709 | 1.1963 | −0.4395 | 1.636 | **1.247** |
| **Gentium Plus** | 2048 | 0.4541 | 0.6152 | 1.0986 | −0.3662 | 1.465 | **1.306** |
| **Noto Serif** | 1000 | 0.5360 | 0.7140 | 1.0690 | −0.2930 | 1.458 | **1.220** |
| **Noto Sans Devanagari** | 1000 | 0.5360 | 0.6220 | 0.8960 | −0.4080 | **1.906** | **1.184** |
| **Noto Serif Devanagari** | 1000 | 0.6230 | 0.7150 | 0.9300 | −0.6250 | **2.199** | **1.169** |
| Tiro Devanagari Sanskrit | 1000 | 0.4780 | 0.6990 | 0.7550 | −0.2450 | 1.636 | 1.203 |
| Shobhika | 1000 | 0.5000 | 0.7000 | 1.1300 | −0.6000 | 1.730 | 1.474 |

"Measured ink" is the real vertical extent of the shaped RV 1.1.1 accented IAST line, or the VSM 40.1 accented Devanagari line, from glyph bounding boxes plus HarfBuzz y-offsets. It is the number that decides clipping.

### The two findings

**1. Noto Serif Devanagari asks for a 2.199em line box and the shipped CSS gives it 2.1em.**

```css
.devanagari { line-height: 2.1; }   /* current */
```

With Noto Sans Devanagari (1.906em) this is fine. **If the display face moves to Noto Serif Devanagari, 2.1 is below its 2.199em ink box** and stacked vowel signs can clip against any ancestor with `overflow: hidden`. Raise it.

**2. The Latin and Devanagari x-heights are close for the Noto pair and far apart for the current pair.**

`size-adjust` needed to make the Devanagari x-height match the Latin:

| Latin face | Noto Sans Dev | Noto Serif Dev | Tiro Dev Sanskrit |
| --- | --- | --- | --- |
| Geist (0.5300) | 98.9% | 85.1% | 110.9% |
| **Newsreader (0.4260)** | **79.5%** | **68.4%** | 89.1% |
| Inter (0.5459) | 101.8% | 87.6% | 114.2% |
| **Noto Serif (0.5360)** | **100.4%** | 86.0% | 112.1% |
| Charis SIL (0.4819) | 89.9% | 77.4% | 100.8% |
| Gentium Plus (0.4541) | 84.7% | 72.9% | 94.9% |

Newsreader against Noto Serif Devanagari needs a **68.4%** correction. That is why mixed lines currently look pasted together: the Devanagari is effectively set 46% larger than the Latin beside it.

**Noto Serif against Noto Sans Devanagari needs 100.4%, which is to say none at all.** If the design values effortless multiscript alignment over scholarly character, that is the argument for Noto Serif as the verse face. Charis SIL needs a modest 89.9% and is still the better face for the verse; the correction is one line of CSS.

### Configuration

```tsx
// src/app/layout.tsx
import localFont from "next/font/local";
import { Geist, Noto_Sans_Devanagari, Noto_Serif_Devanagari } from "next/font/google";

// UI chrome. No Sanskrit ever renders in this face.
const geist = Geist({ variable: "--font-ui", subsets: ["latin"], display: "swap" });

// The romanised verse column. MUST be self-hosted: the Google CDN does not
// serve U+0331 or U+030D for ANY Latin font, and next/font/google downloads
// exactly those subsets. Subset locally from the SIL release WOFF2 with an
// explicit unicode-range that includes U+0300-036F. ~48 KB.
const verse = localFont({
    variable: "--font-verse",
    display: "swap",
    src: [
        { path: "../fonts/CharisSIL-Regular.subset.woff2", weight: "400", style: "normal" },
        { path: "../fonts/CharisSIL-Italic.subset.woff2",  weight: "400", style: "italic" },
        { path: "../fonts/CharisSIL-Bold.subset.woff2",    weight: "700", style: "normal" },
    ],
    // Measured against Charis SIL so the fallback occupies the same space.
    adjustFontFallback: "Times New Roman",
});

// Devanagari. The CDN IS correct for these: all six Vedic codepoints served.
const devSans = Noto_Sans_Devanagari({
    variable: "--font-devanagari",
    subsets: ["devanagari", "latin"],
    display: "swap",
});
const devSerif = Noto_Serif_Devanagari({
    variable: "--font-devanagari-display",
    subsets: ["devanagari", "latin"],
    display: "swap",
});
```

The subsetting command, which must not drop the layout tables:

```bash
pyftsubset CharisSIL-Regular.ttf \
  --output-file=CharisSIL-Regular.subset.woff2 --flavor=woff2 \
  --layout-features='*' \
  --unicodes="U+0000-00FF,U+0100-024F,U+0300-036F,U+1E00-1EFF,U+2000-206F,U+2C60-2C7F,U+A720-A7FF"
```

`--layout-features='*'` is not optional. Dropping it removes `mark` and `mkmk` and reintroduces the collision the font was chosen to avoid.

```css
:root {
    /* Charis SIL x-height 0.4819 vs Noto Sans Devanagari 0.5360 -> 89.9%.
       Noto Serif Devanagari 0.6230 -> 77.4%. */
    --dev-body-adjust: 0.90;
    --dev-display-adjust: 0.77;
}

.sanskrit,
.verse-iast {
    font-family: var(--font-verse), var(--font-devanagari), Georgia, serif;
    font-size: clamp(1.18rem, 0.95rem + 0.9vw, 1.65rem);
    line-height: 1.9;          /* Charis ink 1.247em, Gentium 1.306em */
    letter-spacing: 0;
    hyphens: none;
    padding-block: 0.15em;
}

.devanagari {
    font-family: var(--font-devanagari), sans-serif;
    line-height: 2.0;          /* Noto Sans Devanagari winBox 1.906em */
    font-size: calc(1em * var(--dev-body-adjust));
    letter-spacing: 0;
}

.devanagari-display {
    font-family: var(--font-devanagari-display), var(--font-devanagari), serif;
    line-height: 2.25;         /* Noto Serif Devanagari winBox 2.199em. 2.1 DOES NOT clear it. */
    font-size: calc(1em * var(--dev-display-adjust));
}

.chip .devanagari,
.graph-label .devanagari {
    line-height: 1.6;          /* floor: below this the udatta touches the line above */
    font-size: 0.95em;
}
```

`display: "swap"` plus `adjustFontFallback` is what prevents layout shift: Next emits an `@font-face` for a metric-matched local fallback with `size-adjust`, `ascent-override` and `descent-override`. Next does not synthesise a **Devanagari** fallback, which is why the Devanagari face must be loaded rather than left to a system font.

### On baseline versus shirorekha

Devanagari does not align to the Latin baseline in any meaningful visual sense. Its optical anchor is the **shirorekha**, the headstroke along the top of the akshara, and the reader's eye tracks that the way it tracks the x-height in Latin.

The consequence: matching cap-heights or baselines produces a pairing that measures correct and looks wrong. **Match the Latin x-height to the Devanagari body height**, the distance from baseline to shirorekha, which is what `sxHeight` approximates in these fonts and what the `size-adjust` table above is computed from. That is why the Noto Serif / Noto Sans Devanagari pair at 100.4% works untouched: their x-heights already agree, so the Latin x-line and the Devanagari shirorekha sit at the same optical height.

Do not correct with the CSS `font-size-adjust` property. It is widely supported now but operates per element and interacts badly with the `clamp()` sizing above. Prefer `size-adjust` inside `@font-face`, or an explicit multiplier as shown, because both are inspectable in one place.

---

## TASK 5 - Unicode normalization and search

### The recorded trap, restated precisely

The project memory records that "inline accents break literal quote matching." The mechanism is now measurable, and it is worse than a matching failure: **the obvious fix corrupts the text.**

### Rule 1: strip combining marks from NFC, never from NFD

The single most important recommendation in this section.

```text
input                     : a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | ...
strip-from-NFC  (CORRECT) : agnim īḻe purohitaṁ yajñasya devam ṛtvijam | ...
strip-from-NFD  (WRONG)   : agnim ile purohitam yajnasya devam rtvijam | ...
```

The NFD strip destroys **every IAST distinction in the corpus**:

```text
ḻ U+1E3B -> NFC-strip 'ḻ' | NFD-strip 'l'
ṛ U+1E5B -> NFC-strip 'ṛ' | NFD-strip 'r'
ṁ U+1E41 -> NFC-strip 'ṁ' | NFD-strip 'm'
ṣ U+1E63 -> NFC-strip 'ṣ' | NFD-strip 's'
ḥ U+1E25 -> NFC-strip 'ḥ' | NFD-strip 'h'
ā U+0101 -> NFC-strip 'ā' | NFD-strip 'a'
```

**Why the NFC rule is correct and not merely lucky:** in NFC, anything that *can* compose already *has*. A combining mark that survives NFC composition is, by construction, one with no precomposed form with its base. In this corpus that is precisely the set of Vedic accent marks. Stripping from the NFC form therefore removes exactly the accents and nothing else, with no codepoint list to maintain and no risk of a future accent being missed.

**The one exception, and its fix.** `r̥` (U+0072 + U+0325), which VedaWeb uses for vocalic r, has no precomposed form, so the NFC strip collapses it to plain `r`. Fold it **before** stripping:

```ts
// src/lib/sanskrit-text.ts
const VOCALIC_FOLD: Array<[RegExp, string]> = [
    [/r̥̄/g, "ṝ"],    // r + ring + macron -> ṝ   (longest first)
    [/r̥/g, "ṛ"],          // r + ring below    -> ṛ
    [/l̥/g, "ḷ"],          // l + ring below    -> ḷ
];

export function toNfc(s: string): string {
    return s.normalize("NFC");
}

/**
 * Remove Vedic pitch accents while preserving every IAST letter.
 * Strips from NFC, never from NFD: in NFC a surviving combining mark is by
 * construction one with no precomposed form, which here is exactly the accents.
 */
export function stripVedicAccents(s: string): string {
    let t = s.normalize("NFC");
    for (const [re, to] of VOCALIC_FOLD) t = t.replace(re, to);
    return t.replace(/\p{Mn}/gu, "").normalize("NFC");
}

/**
 * Aggressive fold for MATCHING ONLY. Never render this.
 * Deliberately destroys IAST distinctions so "rtvijam" finds "ṛtvijam".
 */
export function foldForMatch(s: string): string {
    return stripVedicAccents(s)
        .normalize("NFD")
        .replace(/\p{Mn}/gu, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}

/** PUA codepoints cannot be rendered by any font. Drop them at render time. */
export function stripPua(s: string): string {
    return s.replace(/[-]/gu, "");
}
```

### Rule 2: three forms, three jobs, and they must not be confused

| Form | Function | Used for | Never used for |
| --- | --- | --- | --- |
| **Display** | `toNfc(text)`, unchanged | Rendering the verse | Matching |
| **Copy** | `toNfc(text)` by default; `stripVedicAccents(text)` on the affordance | Clipboard | Rendering, matching |
| **Match** | `foldForMatch(text)` | Client highlight, quote verification, search-as-you-type | Rendering, clipboard |

The bug the memory records happens when a checker compares a **display** string against a **quoted** string that took a different path. The fix is that any literal comparison runs `foldForMatch` on **both sides**, always. A comparison where only one side is folded is a bug even when it happens to pass.

### Rule 3: there are roughly 34,000 Private Use Area characters in the corpus

This is a corpus defect that no font choice can fix, and it was found by census rather than inspection. A direct scan of `data/**/text_versions.jsonl` finds PUA codepoints in both `text_original` **and** `text_nfc`, concentrated in `atharvaveda_saunaka_digital_working_v1`. They are legacy font-specific encodings of IAST letters, and all but one decode unambiguously from context:

| PUA | Decodes to | Order of magnitude | Evidence |
| --- | --- | --- | --- |
| U+E003 | **ṁ** (U+1E41) | ~12,000 to 24,000 | `iya`, `teṣā`, `sa`, `prathama` |
| U+E000 | **ṛ** (U+1E5B) | ~5,000 to 11,000 | `pthivyā`, `bhaspatir`, `amtāni` |
| U+E001 | **ṝ** (U+1E5D) | ~45 to 90 | `pitn`, `dātṇām` |
| U+E002 | **ḷ** (U+1E37) | ~11 to 22 | `cākpa`, `kptās`, `acīkpat` |
| U+F15C | Devanagari anusvara **ं**, unconfirmed | ~25 to 50 | `पृथिव्या शतेन`, `त्वेडे` |

Counts differ between scans because they cover different field sets; the decodings are consistent across both. **U+F15C is recorded as unverified**, with the anusvara reading being the most likely but not established.

Two of these reach the frontend:

**(a) The `NORMALIZED_FOR_SEARCH` surface carries the sentinels, and the backend already guards it.** The API returns that surface with `is_displayable: false`, and the OpenAPI description says plainly that it "is an accent-stripped matching form and is wrong to display as the text." Sampled through the API:

```text
UNACCENTED : 'vidmā śarasya pitaraṃ parjanyaṃ śatavṛṣṇyaṃ | tenā te tanve śaṃ ...'
NORMALIZED : 'vidmā śarasya pitara parjanya śatavṣṇya tenā te tanve śa ...'
```

**The frontend must honour `is_displayable`.** At present `src/app/passage/[key]/page.tsx` filters alternates only on `surface.text && surface.text !== primary?.text`, which does **not** check it:

```ts
const alternates = (reader.text.surfaces ?? []).filter(
    (surface) => surface.is_displayable && surface.text && surface.text !== primary?.text,
);
```

**(b) At least one PUA character sits in a surface that IS marked displayable.**

```text
VG:YV:VSM:A07:V003  [PARALLEL_WITNESS]  is_displayable=True
  PUA: U+F15C
  context: ...ेभ्यस् त्वा मरीचिपेभ्यः । देवाशो यस्मै त्वेडे तत् सत्यम् उप...
```

U+F15C is unassigned in Unicode and no font can legitimately cover it, so it renders as a tofu box. The backend is frozen, so apply `stripPua` **in the text-rendering component**, not in the fetch layer, so the raw API response stays faithful to what the backend returned.

### Rule 4: the copy-to-clipboard affordance

Offer two actions, labelled so the difference is obvious and the default is faithful:

- **Copy verse** (default). NFC text exactly as displayed, accents intact. What a scholar citing the passage needs.
- **Copy without accents**. `stripVedicAccents(text)`. What someone pasting into a search box, a database that mangles combining marks, or a system with a limited font needs.

Both write `text/plain`. Do not offer "copy as Devanagari"; per Task 3 there is no derived Devanagari to copy.

Helper text under the control, no em-dashes:

> Copying without accents removes the Vedic pitch marks and keeps the letters. Use it when pasting into a system that cannot show combining marks. The version with accents is the text of record.

### Rule 5: normalize at the boundary, assert in a test

The corpus is NFC today, verified across every sample. Depend on that, but verify rather than assume, because Task 3 showed NFD input silently destroys base letters and a future ingest could change the invariant without warning.

```ts
// src/lib/api.ts, where passage text enters the app
const text = raw.normalize("NFC");
```

```ts
it("every text surface the API returns is already NFC", async () => {
    const p = await getPassage("VG:RV:SAK:M01:S001:V001");
    for (const s of p.text.surfaces) {
        expect(s.text.normalize("NFC")).toBe(s.text);
    }
});

it("stripping accents preserves every IAST letter", () => {
    expect(stripVedicAccents("a̱gnim ī̍ḻe")).toBe("agnim īḻe");   // not "agnim ile"
});
```

---

## Summary of changes this note recommends to shipped code

| # | File | Change | Why |
| --- | --- | --- | --- |
| 1 | `src/app/layout.tsx` | Add a **self-hosted** `--font-verse` (Charis SIL subset) via `next/font/local` | Newsreader fails 34.1% of IAST characters, Geist 49.7%. And the CDN does not serve U+0331 or U+030D for **any** Latin font, so `next/font/google` cannot fix it. |
| 2 | `src/app/globals.css` | `.sanskrit` uses `var(--font-verse)` first, not `var(--font-reading)` | Same. This is the live defect. |
| 3 | `src/app/globals.css` | `.devanagari` line-height 2.0; add `.devanagari-display` at 2.25; add x-height multipliers | Noto Serif Devanagari needs a 2.199em box and the current 2.1 is below it. |
| 4 | `src/app/passage/[key]/page.tsx` | Filter alternates on `surface.is_displayable` | `NORMALIZED_FOR_SEARCH` carries PUA sentinels and is flagged not displayable. |
| 5 | `src/lib/sanskrit-text.ts` (new) | `toNfc`, `stripVedicAccents`, `foldForMatch`, `stripPua` | Strip from NFC not NFD; fold both sides before any literal comparison; drop unrenderable PUA. |
| 6 | - | **Do not** add `@indic-transliteration/sanscript` | Zero correct accents over 1,083 real surfaces. |
| 7 | - | **Keep** `Noto_Sans_Devanagari` exactly as it is | 100% coverage of all Devanagari and Vedic codepoints in the corpus, correctly served by the CDN. |
| 8 | `docs/design/research/08-typography-coverage-test.md` | Amend the single-face type system: Tiro for Devanagari, a separate Latin face for the romanised verse | Tiro lacks U+030D and has no `mark`/`mkmk`; it renders 6 tofu boxes on RV 1.1.1. See *Reconciliation* in Task 2. |

---

## Appendix: how to reproduce

```bash
pip install fonttools uharfbuzz brotli pillow
# fonts from https://raw.githubusercontent.com/google/fonts/main/ofl/<dir>/<file>.ttf
# Shobhika from https://github.com/Sandhi-IITBombay/Shobhika/releases (v1.05)
# SIL fonts from https://software.sil.org/<family>/download/

# What the CDN ACTUALLY serves, which is not what the repo contains
curl -A "Mozilla/5.0 ... Chrome/131" \
  "https://fonts.googleapis.com/css2?family=Charis+SIL&display=swap"
# then download each woff2 in the response and read its cmap

npm install @indic-transliteration/sanscript   # 1.3.3, MIT
npm install aksharamukha                       # 2.3.0-32, GPL-3.0, 16.8 MB

curl "http://127.0.0.1:8000/api/v1/passages/VG:RV:SAK:M01:S001:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:YV:VSM:A01:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:AV:SAU:K01:S001:V001"
curl "http://127.0.0.1:8000/api/v1/passages/VG:SV:KAU:CHANDA:P05:D09:V02"
```

Sample sizes: 1,083 IAST surfaces from 478 passages for transliteration; 461 Devanagari surfaces from 263 passages for the codepoint census; 2,956 real accented lines shaped per Devanagari candidate; 241,865 corpus rows scanned for mark frequency; 34 conjuncts and 9 Vedic shaping strings per font across 17 Devanagari faces and 13 Latin faces.

### Sources

- Google Fonts repository, `github.com/google/fonts` at `main` (binaries, `OFL.txt`, `METADATA.pb`, `DESCRIPTION.en_us.html`)
- Google Fonts CSS2 API, `fonts.googleapis.com/css2`, and the WOFF2 subsets it serves
- `github.com/Sandhi-IITBombay/Shobhika` release v1.05 and its `OFL.txt`
- `github.com/TiroTypeworks/Indigo`; `tiro.com/fonts/tiro-devanagari-sanskrit`
- `software.sil.org/annapurna/support/faq/` (SIL's own statement that Annapurna has no Vedic plans); `software.sil.org/fonts/faq/` (SIL's warning about CDN subsets)
- `adishila.com/fonts` (redistribution prohibition); Debian copyright for `fonts-sahadeva` (GPL-2.0+); `sanskritweb.net/itrans` (Stiehl)
- Unicode Vedic Extensions proposal **L2/07-343 = WG2 N3366**, superseding L2/07-230; Unicode 17.0 core specification chapter 12; L2/21-054 and L2/21-112 on cluster validity
- `github.com/google/fonts` issues #1767 (Noto Sans advertises Vedic coverage it lacks) and #1901 (CDN subset ranges); `github.com/rsms/inter` issues #155, #534, discussion #555; `harfbuzz` issue #2017; Mozilla bug 543200 (Firefox per-character fallback)
- HarfBuzz `common_features[]` in `src/hb-ot-shape.cc`; CSS Fonts 4 section 7.1; CSS Overflow 3 on ink overflow; Chromium Blink fonts README
- `registry.npmjs.org/@indic-transliteration/sanscript`; `registry.npmjs.org/aksharamukha`; `github.com/indic-transliteration/sanscript.js` (README documents "lossy scheme" only in terms of script letters and **makes no mention of Vedic accents at all**, so the behaviour reported above is undocumented upstream)
- Brill font EULA, clauses 6 and 8
- Unicode 16.0 character database via Python `unicodedata`; the live VedaGraph API, version 1.0.0
