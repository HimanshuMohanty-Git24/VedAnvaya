# Proof: the 33 `text_mismatch` were our instrument, not the source's absence

Reconnaissance called the 33 "the signature of a numbering divergence". It is not a numbering
divergence. It is two defects in our own matcher, and both are cross-cutting — they affect every
Veda this pipeline touches, not only the Yajurveda.

## Step 0 — the offset hypothesis, tested and disproved

For each of the 33, our text was scored against **all 1,975** source rows, not only the
coordinate-aligned one. If a numbering offset existed, the correct recording would sit at a
neighbouring or displaced coordinate and would score far higher there.

**For 30 of the 33, the coordinate-aligned row is itself the global best match**, and the
runner-up anywhere in the corpus scores at or below 0.64. Examples:

```
VG:YV:VSM:A01:V016  at 1.1.16 = 0.679   runner-up 1.1.20 = 0.173
VG:YV:VSM:A09:V034  at 9.1.34 = 0.632   runner-up 19.1.79 = 0.087
VG:YV:VSM:A21:V040  at 21.1.40 = 0.204  runner-up 28.1.11 = 0.089
```

There is no offset. The coordinates were always right; the *text check* was failing.

The three exceptions are informative rather than contradictory. `A23:V030` has 23.1.31 at 0.8552
against 23.1.30's 0.8114 — neither clears threshold, so the source's own 23.30/23.31 boundary is
in doubt; it is staged `UNVERIFIED`. `A25:V047` and `A33:V056` each match a *different* source
coordinate at 0.99 (15.1.48 and 7.1.8) because VSM recycles mantras across adhyāyas — which is
exactly why a text-only search must never override a coordinate, and neither was mapped there.

## Defect 1 — visarga written as an ASCII colon

`skeleton()` transliterates Devanagari to IAST, strips combining marks, and keeps `[a-z]`.
Under that instrument:

- U+0903 DEVANAGARI SIGN VISARGA → `ḥ` → decomposes to **`h`, which is kept**.
- ASCII `:` is not a letter → **dropped entirely**.

And the two editions disagree on which glyph they use:

| | rows containing an ASCII colon |
|---|--:|
| our stored YV text | **893 of 1,975** |
| the source's YV text | **0 of 1,975** |

So for 893 of our verses, every visarga is an `h` present on the source's side and absent on
ours. On a long mantra that is dozens of missing letters in text that is word-for-word
identical.

**That the colon really is a visarga glyph, not punctuation:** every colon in all 1,975 stored
texts is preceded by a Devanagari or Vedic-extension character. Count of colons *not* so
preceded: **0**. There is no reading on which this is punctuation.

Folding it — `":" → U+0903` before `skeleton()` — took the 33 from 0 clearing threshold to 13,
with the newly-clearing scores landing at 0.99+ rather than creeping over the line:

```
VG:YV:VSM:A01:V016   0.6790 -> 0.9908
VG:YV:VSM:A05:V007   0.7775 -> 0.9976
VG:YV:VSM:A09:V034   0.6321 -> 0.9982
VG:YV:VSM:A14:V009   0.4541 -> 0.9967
```

A fold that turns 0.45 into 0.9967 is not loosening a threshold. It is removing noise that was
never linguistic.

## Defect 2 — `difflib` autojunk, and this is the larger one

`similarity()` in `src/vedagraph/product/audio/vedsearch.py` reads:

```python
return difflib.SequenceMatcher(None, left, right).ratio()
```

`SequenceMatcher` defaults to `autojunk=True`. On a second sequence of 200 elements or more it
treats any element occurring in more than 1% of it as "popular" and ignores it. A verse skeleton
is 200–1,100 characters drawn from a ~30-letter alphabet, so **every letter exceeds 1%** and the
comparison is made against almost nothing. The ratio it returns for long verses is noise.

The proof is a single flag. Same strings, `autojunk=False`:

| key | skeleton length | shipped | `autojunk=False` |
|---|--:|--:|--:|
| `A05:V023` | 269 | 0.2342 | **0.9777** |
| `A21:V040` | 341 | 0.2032 | **0.9956** |
| `A22:V033` | 399 | 0.3529 | **0.9795** |
| `A38:V018` | 229 | 0.5099 | **0.9802** |
| `A16:V046` | 205 | 0.6357 | **0.9927** |
| `A03:V042` | 73 | 0.8022 | 0.8022 |
| `A09:V006` | 118 | 0.5254 | 0.5254 |

Note the last two rows: verses under 200 characters are unaffected, which is the autojunk
threshold showing itself exactly where the documentation says it will.

`A05:V023` is the clearest specimen. Ours and the source's skeletons are both 269 characters and
differ only in five places where one edition writes `valaga` and the other `balaga`. The shipped
instrument scored that pair **0.2342** — below the 0.462 the module's own docstring reports as
the maximum for *deliberately mispaired* verses. Two near-identical strings were being scored as
less similar than two unrelated ones.

**Why this never showed up in the 1,752 that mapped.** `verse_matches()` short-circuits:
`if left == right: return True, 1.0`. Most true pairs are exactly equal after `skeleton()` and
never reach `similarity()` at all. The fuzzy path is only taken by pairs with a genuine
orthographic difference — and that is precisely the population autojunk destroys. The module's
recorded calibration ("median 0.995, p5 0.973 over all 1,975") was itself computed with the
broken comparator, and it looked healthy because the median is carried by the exact-equality
short-circuit.

## Recalibration of the corrected instrument

Instrument = `skeleton()` + colon-as-visarga + private-use-area drop + `autojunk=False`.
Threshold left at 0.90, unchanged.

| population | n | median | p5 / p99 | extreme |
|---|--:|--:|--:|--:|
| coordinate-aligned | 1,975 | **1.0000** | p5 0.9862 | min 0.2769 |
| deliberately mispaired, seed 20260915 | 800 | 0.2514 | p99 0.4125 | **max 0.5690** |

The worst wrong pair reaches 0.5690 against a threshold of 0.90. The two populations do not
overlap and do not approach. Of the aligned pairs, 1,949 are at or above 0.97 and only 17 sit in
[0.90, 0.97).

**Regression check, which is the one that matters.** Every verse the shipped matcher accepted
was re-scored under the corrected instrument:

- mapped before and not after: **0**
- newly mapped: **25**

The fix is strictly additive. Nothing in the existing 1,752-row catalogue loses its mapping.

## Result

`text_mismatch` for the Yajurveda falls from **33 to 8**, and the 8 that remain are not instrument
failures — they are four source-side dittographies, two source-side truncations, one inverted
hemistich order, and one defect in *our own* mantra text. Each is typed on its row in
`rows.jsonl` under `payload.unverified_reason_code`.

## Two things the lead must act on outside this write surface

**1. The AV's 495 `text_mismatch` are very likely the same two defects.** The AV gap is 1,159 of
which 495 are recorded `text_mismatch`, and the identical instrument produced that number. The
autojunk defect is length-dependent and Atharvavedic mantras are long. Rerunning the AV
alignment with these two corrections costs one script invocation and should precede any AV audio
acquisition. Reconnaissance guessed ~43% of the AV gap "may be ours"; on this evidence that
guess is probably right and probably conservative. **This is a prediction, not a measurement —
I did not run the AV, because it is not my write surface.**

**2. `VG:YV:VSM:A07:V003`'s stored mantra text contains a Sanskrit commentary.** 1,138 skeleton
letters against the source's 184, the excess being running commentary — `iti pāṭhaḥ`,
`iti śrutiḥ`, `iti śeṣaḥ`, `chandasi yakāra-lopaḥ`. The `wikisource-sa-vsm` extraction spilled
bhāṣya into the mantra. `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS.md` records that 36 of the 1,975
boundaries fall back to accent-presence inference rather than a declared header; this looks like
one of them. It is a text-layer defect that surfaced through audio, and it belongs to whoever
owns the YV primary text.
