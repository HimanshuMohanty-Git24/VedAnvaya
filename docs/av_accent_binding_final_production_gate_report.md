# AV Accent Binder — Final Production Gate (5-line gold)

**Session date**: 2026-09-08
**Branch**: `semantic-pilot-v1`
**Starting commit**: `c5de01d` — *av: place the accent bands off line pitch, and verify against a second line*
**Scope**: add exactly three independently adjudicated gold lines, rerun the existing
calibration, decide. The full 478-leaf transcription was explicitly NOT started.

---

## Verdict

**`ATHARVAVEDA_TRANSCRIPTION_METHOD_NEEDS_REVISION`**

`FULL_478_LEAF_TRANSCRIPTION` is **NOT AUTHORIZED**.

One predeclared gate fails: `word_binding_acc` = **0.85454** against a threshold of
**0.95**. `PRODUCTION_READY` requires all predetermined gates to pass, so it is not
available regardless of the fact that gold coverage now meets the 5-line minimum.
This is the verdict the runner's own predeclared decision logic emits; it was not
argued down to a softer label.

---

## 1. What the three new lines were, and why they were chosen

Selection was recorded **before any crop was rendered or read**
(`gold_selection_rationale.md`, reproduced in this repo's session scratch). All three
were drawn from the already-frozen 81-line calibration set, so the
`FROZEN_BEFORE_CALIBRATION` policy holds.

| Line | Stratum | Axis it was chosen for | Difficulty signal |
|---|---|---|---|
| `c430 / l05` | `kanda20_area` | late / Book-20 material | pre-flagged difficult; 11 marks |
| `c159 / l02` | `middle_kandas` | different line pitch / layout | pitch **209 px**, the sole outlier vs 171–179 |
| `c411 / l09` | `kanda19_area` | typography / noise-heavy | **17** rule spans, tied 3rd-most fragmented |

*Correction to the selection note:* 17 spans is **tied 3rd**, not "second-highest"
(baseline top: 20 @ c249/l17, 19 @ c231/l09, then 17 @ c357/l09 and 17 @ c411/l09).
The pitch-209 property of c159 is a **leaf** property, shared with c159/l09. Neither
error affects the selection's validity — all three lines are in the frozen set and carry
the intended axes — but the rationale overstated two of the signals.

Selection used only *difficulty* signals from the already-published baseline extractor
output (`marks_detected`, `word_spans_count`, `line_pitch`). Selecting for **high** mark
count, **high** span fragmentation and **anomalous** pitch selects against easy lines.

**Coverage expansion vs the previous gold set** (which was 2 lines on a *single* leaf):

| | before | after |
|---|---|---|
| leaves | 1 (c032) | 4 (c032, c159, c411, c430) |
| strata | `gold_verified` only | + `middle_kandas`, `kanda19_area`, `kanda20_area` |
| line pitch | 174 | 174, 175, 209 |
| Book 20 | no | yes |

**Disclosed exposure**: because selection used the detector's aggregate output, the
adjudicator knew the *detected* mark counts (c430/l05 6+5, c159/l02 6+4, c411/l09 6+5)
before adjudicating. Mitigation committed to in advance and honoured: the adjudicator
did not inspect per-mark x positions or binder output for these lines until the gold was
written and frozen. **The nine readers had no exposure to any of these numbers.** The
strongest evidence that the gold was not fitted to the detector is that
**c411/l09 gold = 12 marks against 11 detected** — the readers found a mark the pipeline
misses.

---

## 2. Independent reading

Nine readers, three per line, each working alone from the BSB/MDZ crop with an identical
brief, no sight of each other's work, and an explicit prohibition on GRETIL / TITUS /
VedaWeb / Orlandi / any translation / any web resource, and on reading the extractor,
the binder, the calibration output or another reader's probe.

Each recorded: Devanagari skeleton with accents in place, anudātta count, svarita count,
per-mark carrier (word + akṣara index), the measured y-bands, and an explicit
boundary interpretation.

**Result — all three readers on each line produced identical
`(word_index, aksara_index, type)` tuples for every mark, *as derived from their
`text_devanagari`*, which is the only field the runner reads:**

| Line | Readers | Marks | Mark-tuple agreement |
|---|---|---|---|
| `c430/l05` | R1, R2, R3 | 6 anudātta + 5 svarita = 11 | identical |
| `c159/l02` | S1, S2, S3 | 6 anudātta + 4 svarita = 10 | identical |
| `c411/l09` | T1, T2, T3 | 6 anudātta + 6 svarita = 12 | identical |

Re-derivable from the verbatim pre-adjudication readings preserved in
`accent_probe/raw_readings/**`, which the runner's non-recursive `glob("*.json")` does
not pick up.

**Qualification, found by adversarial review.** The agreement is exact for tuples derived
from `text_devanagari`. It is **not** exact for the readers' *declared* `carriers` field:
on c159/l02 S2 numbers the akṣara cells of `ऽवदन्नृतानि` as 1/3/5 where S1 and S3 use
0/2/4, because S2 counts the avagraha as a cell and they do not. That is a counting
convention, not a disagreement about which glyph carries which mark, and it is
metrically inert because the runner re-derives indices from the text. Two ironies worth
recording: `aksara_clusters("ऽवदन्नृतानि")` returns
`['ऽ','व','द','न्नृ','ता','नि']`, so **S2's convention is the one the pipeline itself
uses** and the 2-1 majority's is not; and this is the same reader whose skeleton reading
was overruled. Statements of the form "identical tuples for all marks" in the probe
`adjudication` fields should be read as scoped to the text-derived tuples.

Notable independent convergences (each found separately by readers who could not see
one another):

- **c411/l09**: all three isolated a svarita at x≈690 in `इन्द्रं` that *merges with the
  anusvāra dot* into one ink component at low threshold and separates only at a higher
  one. The extractor binarises at `INK = 128` and misses it. T1 and T3 produced
  byte-identical `text_devanagari`.
- **c159/l02**: all three found the sixth anudātta bar set ~14–16 px *below* its five
  siblings, because the printer had to clear the vocalic-ṛ hook of `न्नृ`. S1
  corroborated the habit on line 3 of the same leaf (bars under `तृ`, `वृ` dropped the
  same way).
- Readers repeatedly followed the ink against their own memory of the text and said so
  (R1 on `स्तोम` with no anusvāra; T2 on `सधी` vs `सध्री`).

---

## 3. Adjudication

Disagreements were resolved from the scan by magnified same-line composites, not by vote.

- **`c159/l02` word 3 — `अनयन्वाचो` adopted, OVERRIDING a 2-1 majority.** S1 and S2 read
  `अनयद्वाचो`; S3 read `अनयन्वाचो`. Composite of the conjunct at x966–1070 against plain
  **न** (x1550–1628), plain **द** (x2195–2262) and plain **व** (x2128–2196) from the same
  printed line: the conjunct's upper member is a left blob with a horizontal bar running
  right — identical to plain न — while plain द on this line is a hook curving down-left
  with **no rightward bar**. S1 had justified `द्व` by claiming the upper member repeats
  "the left wedge plus rightward bar of the plain द"; that feature is diagnostic of न, not
  द. Both S1 and S2 had already flagged this conjunct as their least certain glyph.
- **`c159/l02` word 4 — `अग्रं` adopted** (majority and image agree). The disputed glyph
  has an open upper-left hook plus a bold diagonal descending below the body — a subscript
  र — where the certain `य` on the same line is a compact bowl with a thin crescent
  counter joining the stem horizontally at the foot.
- **`c430/l05` word 1 — readers split 1-1-1** (`ह्यस्य` / `हस्य` / `अस्य`). The conjunct
  reading `ह्य` is **ruled out on width**: all three measured the akṣara at 79–83 px, and
  every consonant+य conjunct on this line is 114–120 px (`स्य` 114, `म्या` 120) while the
  single consonant `च` is 82 px. Between `ह` and `अ` the 2024 px raster does not settle
  it; `ह` was adopted as the majority-supported reading with R1's subjoined य removed, and
  **R3's `अ` is recorded as unresolved dissent** with the akṣara still flagged unclear.
- **`c411/l09`** — `सध्री` (2-1) and spaced `॥ १७ ॥` (2-1) adopted; T2's dissent preserved.
  The spacing is *not* cosmetic: it moves the whitespace token count from 11 to 9 and so
  changes what the alignment guard sees. Reported rather than smoothed.

Every disputed locus was verified to leave the mark tuples unchanged, so **no adjudication
decision moved a metric.**

### Provenance honesty

Each probe carries `text_devanagari`, `text_devanagari_initial`,
`conceded_on_adjudication` and `dissent`, and the verbatim originals are additionally
preserved under `accent_probe/raw_readings/`. Adversarial review confirmed
`text_devanagari == text_devanagari_initial` in all 9 probes — **nothing was overwritten
and reader agreement is not inflated**; `gold_agreement` reports
`mark_positions_agree`, which is the accurate label.

**But the adjudication is therefore not what the gate measured.** Because dissenting
readers keep their own text, no line has three identical texts, so `_reconcile_gold`
falls through to `probes[0]` — i.e. whichever file `glob()` yields first. For c430/l05
that is R1's `ह्यस्य`, the reading ruled out on width; for c159/l02 it is S1's
`अनयद्वाचो` / `अयं`, both of which were overruled at the scan. Substituting the
adjudicated texts and re-running changes **no metric at all** (only `gold_agreement`
becomes `exact`), because every disputed locus was verified mark-tuple-neutral. So the
adjudication is metrically inert here — but "three independently adjudicated gold lines"
is a process claim with **no representation in the measured artifact**, and that is a
latent hazard the moment a future dispute is *not* tuple-neutral.

---

## 4. Gold count

**5** — `c032/l12`, `c032/l19` (pre-existing) + `c430/l05`, `c159/l02`, `c411/l09` (new).

---

## 5. Pipeline change — one genuine defect, fixed

**The pipeline DID change.** `scripts/extract_atharvaveda_accents.py`,
`_word_spans_from_rule`.

`_WORD_GAP_MIN_PX = 14` is named a gap and documented as one — *"Minimum gap width
(pixels) to be treated as a word boundary rather than intra-word ink variation … word gaps
are 28-60px; intra-word dark spots never exceed 8px"* — but the code applied it to the
width of the **inked run**:

```python
if x - start >= _WORD_GAP_MIN_PX:  # x - start is the SPAN's width, not the gap
    spans.append((start, x - 1))
```

So gaps of 1–11 px, which the comment explicitly says must not be word boundaries, split
words anyway. Canvas 32 cannot detect the error — its rule never breaks inside a word —
which is exactly why a calibration whose gold was two lines of canvas 32 certified it.
The three new lines expose it: a 2 px break inside `सध्रीचीर्विश्वा` (c411/l09), an 11 px
break after the avagraha (c159/l02), a 5 px break in the double danda (c430/l05).

Because spans are paired to tokens left-to-right by position, each spurious break shifted
every carrier after it by one word.

**Why this is a defect fix and not tuning:** the constant's **value is unchanged (14)**;
the fix makes the code do what its own name, docstring and comment already specified. The
independent check that it is right rather than merely favourable: under the corrected
semantics the span count becomes **exactly equal to the token count on 4 of the 5 gold
lines**, where the buggy version was off by 1 to 6 — including the two pre-existing gold
lines (c032/l12 14→12 spans vs 12 tokens; c032/l19 13→12 vs 12).

### Scope of the change, stated honestly

The fix altered `word_spans_count` on **60 of 81 calibration lines** (56 down, 4 up) —
not merely the three narrow breaks the code comment names. `marks_detected` is unchanged
on **81 of 81**, so the accent detector itself is untouched; only word segmentation moved.

Of those 60 lines, **55 have no gold**, so the change is verified only where gold exists.
Where it exists it is unambiguously right (span count becomes exactly the token count on
4/5 lines; the baseline was wrong on all five; no gold line under-counts).

The fix also had a second effect that the comment does not mention: the old width test
was simultaneously **discarding short inked runs**, and removing it lets small specks
become spans. The clearest case is `c015/l02`, which goes from 5 spans to 15 with widths
`[2, 42, 9, 5, 32, 12, 9, 49, 47, 10, 11, 37, 6, 16, 7]` — a line carrying 0 marks, so it
affects no binding today, but it is the strongest candidate for a hidden regression on the
55 unverified lines. No minimum-width parameter was reintroduced, because choosing one
without gold to justify it would be tuning. **This is a further reason not to authorize a
full-corpus run on the strength of this session.**

### What was deliberately NOT fixed

The remaining failure is `span_to_token`, an identity map in
`src/vedagraph/ingest/av_accent_binder.py`:

```python
span_to_token = {si: ti for ti, si in enumerate(range(min(n_tokens, n_spans)))}
```

It assumes the i-th rule span is the i-th whitespace token. On c411/l09 the two
free-standing visarga dot-pairs (x1007–1027, x1399–1420) have ink in the rule band but no
corresponding token, so every carrier after them shifts. That is a **stated design
assumption**, not a coding slip, and repairing it means redesigning the alignment step.
Doing that *after* learning it is a remaining blocker would be tuning to the evaluation
case, which the gate forbids. It is therefore reported, not fixed.

`_filter_artifact_spans` does not catch these spans and cannot be made to without
changing a threshold: span 4 is 21 px wide against neighbours of 224 px and 297 px, giving
a ratio of **10.7 against `_ARTIFACT_RATIO = 20.0`**. Lowering that constant is exactly
the threshold change this gate prohibits.

**Correction, established by adversarial review: this is not the only remaining cause.**
An oracle run that merges the two visarga spans into their owning words — i.e. the best
a perfect `span_to_token` could do — lifts c411/l09 from 0.2727 to **0.6364**, giving a
5-line mean of **0.92727, still short of 0.95.** The second, independent cause is that
`run_av_calibration.py:202-212` pairs bindings to gold marks **by position**
(`gw, gak, _ = gold_marks[i]`), so the one undetected svarita on `इन्द्रं` misaligns every
later comparison. Marks 2 and 3 are in fact bound *correctly* but are scored against
`gold[2]`/`gold[3]`; one later mark then scores "correct" by accident. Any remediation
plan that addresses only the span alignment **will not clear this gate.**

---

## 6. Predeclared metrics — final run

Thresholds were **not** touched. Verified unchanged: `THRESHOLD` dict,
`BOUNDARY_MARGIN` 0.15, `MAX_TOKEN_SPAN_MISMATCH` 0.30, `SPAN_EDGE_TOLERANCE` 20,
`_ARTIFACT_RATIO` 20.0, `ANUDATTA_BAND` (0.50, 0.80), `SVARITA_BAND` (-0.25, 0.0),
`SHAPES`, `INK` 128, and the frozen 81-line calibration set.

| Gate | Threshold | Value | Result |
|---|---|---|---|
| `detection_recall` | ≥ 0.90 | **0.98334** | PASS |
| `detection_precision` | ≥ 0.85 | **1.00000** | PASS |
| `class_accuracy` | = 1.00 | **1.00000** | PASS |
| `word_binding_acc` | ≥ 0.95 | **0.85454** | **FAIL** |
| `auto_promote_frac` | ≥ 0.50 | **0.84728** | PASS |
| `source_ambiguous_gold` | = 0 | **0** | PASS |
| `extractor_success_rate` | ≥ 0.95 | **0.98765** (80/81) | PASS |
| `ACCENTED_LINE_EXACT_MATCH_RATE` | (reported) | **0.2000** (1/5) | — |

Per line:

| Line | gold | det | recall | prec | class | word | akṣara | auto | exact | states |
|---|---|---|---|---|---|---|---|---|---|---|
| c032/l12 | 10 | 10 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0000 | 0.8000 | **True** | 8 EXACT, 2 MC |
| c032/l19 | 11 | 11 | 1.0 | 1.0 | 1.0 | 1.0 | 0.8182 | 0.7273 | False | 8 EXACT, 3 MC |
| c159/l02 | 10 | 10 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9000 | 0.8000 | False | 8 EXACT, 2 MC |
| c411/l09 | 12 | 11 | 0.9167 | 1.0 | 1.0 | **0.2727** | **0.1818** | **1.0000** | False | **11 EXACT** |
| c430/l05 | 11 | 11 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9091 | 0.9091 | False | 10 EXACT, 1 MC |

No regression on the pre-existing gold: c032/l12 is byte-identical to baseline;
c032/l19 improved (akṣara 0.7273 → 0.8182, auto 0.6364 → 0.7273).

### These numbers are not reproducible in principle — a second blocking defect

`c032/l19`'s gold is 2-reader and `gold_agreement = "split"`, so the runner uses
`probes[0]`, which is filesystem glob order. Q1 and Q2 differ **only** in danda spacing,
and that changes the whitespace token count from **12 to 6**. Measured both ways:

| `probes[0]` | tokens | spans | mismatch | allowed | `SOURCE_AMBIGUOUS` | word_acc | 5-line mean |
|---|---|---|---|---|---|---|---|
| Q1 (what ran) | 12 | 12 | 0 | 4 | 0 | 1.0 | 0.85454 |
| Q2 | 6 | 12 | 6 | 4 | **11** | 0.0 | 0.65454 |

Under Q2 the **zero-tolerance `source_ambiguous_gold` gate also fails.** One of the five
gold lines contributes a pass only because `glob()` happened to return Q1 first. This was
flagged as a pre-existing weakness before the run, but the run has now shown it can flip
a gate, which is a stronger claim: **the gate result is order-dependent and must not be
treated as reproducible until c032/l19 is re-adjudicated.** Left unfixed here only
because the two original gold lines were outside this task's remit.

### Two of the passing gates measure less than they appear to

- `detection_precision` is computed as `min(detected, gold)` per class over
  `total_detected` (`run_av_calibration.py:167-173`). It detects **over**-detection only;
  it says nothing about whether a detected mark is in the right *place*. The 1.0 is not
  evidence of positional correctness.
- `class_accuracy` applies `misclassified // 2` (`:179`), which floors a single-class
  count discrepancy to zero. This is precisely why c411/l09 scores `class_accuracy = 1.0`
  while **missing a mark entirely**.

Neither 1.0 should be quoted as evidence that the accent layer is correct.

### The instrument self-contradicted during this gate

`_verdict()` computes `ok = value >= threshold` (`run_av_calibration.py:239`). Applied to
`source_ambiguous_gold`, whose threshold is 0, it prints `PASS` for **any** value. The
pre-fix log shows it live: `[PASS] source_ambiguous_gold (must be 0): 11 (threshold 0)`
printed two lines above `Failed gates: word_binding_acc, source_ambiguous_gold`. The
`fails` list is computed separately and correctly, so **no decision was wrong** — but one
of the seven gates has no working display, and a reader skimming the gate table would
have recorded a pass.

---

## 7. The most important finding: a silent failure mode

**c411/l09 reports `auto_promote_frac = 1.0` with all 11 detected marks `BOUND_EXACT`,
while its word-binding accuracy is 0.2727 and its akṣara-binding accuracy is 0.1818.**

The binder is *maximally confident and mostly wrong*. This directly contradicts the design
claim that the pipeline "surfaces rather than hides uncertainty" and has "zero silent
ambiguities": on this line there is nothing for a human reviewer to review, because
every mark is marked auto-promotable.

Worse, and this must be stated plainly: **before the gap fix this line failed loudly**
(`SOURCE_AMBIGUOUS`, 11 marks, i.e. the pipeline correctly refused to answer). The gap fix
is correct on its own terms, but it brought the token/span mismatch back inside the
alignment guard's tolerance and thereby **converted a loud, safe failure into a silent,
unsafe one.** The alignment guard had been accidentally catching the visarga
misalignment, and no longer does.

This is the single strongest reason not to authorize a 478-leaf run: the pipeline's safety
property does not hold on typography carrying free-standing visarga or avagraha, and
`auto_promote_frac` is not a trustworthy proxy for correctness.

Related, pre-existing measurement gap: `aksara_binding_acc` is **not** one of the seven
gates, and it is materially weaker than the gated word-level metric on 4 of 5 lines. The
gate as declared cannot see akṣara-level error.

---

## 8. Corrections to the previous gate report

`docs/av_accent_binding_production_gate_report.md` contains two statements the code does
not support:

1. **Item 13** claims `ACCENTED_LINE_EXACT_MATCH_RATE` = "0/2 = 0.0000" and marks
   c032/l12 `exact=False`. The runner actually emitted **1/2 = 0.5000** with c032/l12
   `exact=True`. The report's prose applied a stricter criterion than the code (the code's
   test does not require `AUTO_PROMOTE` state, only a correct akṣara). Report error, not a
   code error.
2. **Item 27** claims "895 tests — 895 pass, 0 fail, 2 skip", which is internally
   inconsistent. The suite at the starting commit was **894 passed, 2 skipped** (896
   collected).
3. **Item 28** claims "Ruff: All checks passed" — true, but the invocation covered only
   4 files and never linted `tests/unit/test_av_accent_binder.py`, which carries 7
   pre-existing violations (see §9).
4. **Item 25/§ gold**: `c032/l19`'s gold is 2-reader and `gold_agreement = "split"`.
   `_reconcile_gold` returns `"split"` and the runner then silently uses `probes[0]`,
   i.e. whichever file `glob()` yields first. One of the two original gold lines therefore
   rests on an unadjudicated, arbitrarily chosen reader. Left as-is under the
   do-not-change constraint; flagged here.

---

## 9. Tests, lint, types

- **AV accent binder + extractor tests**
  (`test_av_accent_binder.py` + `test_atharvaveda_transcription.py`):
  **110 passed, 0 failed** (was 97 at the starting commit; +13 new).
- **Full suite** (`python -m pytest tests/`): **907 passed, 2 skipped, 0 failed**.
  The starting commit measured **894 passed, 2 skipped**; the delta is exactly the 13
  regression tests added below, so **zero regressions**. The 2 skips are the pre-existing
  live-network test and an `openai`-import test.
- **Regression tests added**: 13, in
  `tests/unit/test_atharvaveda_transcription.py::TestWordSpansSplitOnGapsNotOnRunWidth`:
  - 3 synthetic unit tests pinning the exact gap semantics — a sub-threshold gap does not
    split, a gap at the threshold does, and a narrow inked run is still a span (which the
    old width test silently deleted).
  - 5 parametrized invariant cases over every gold line: no two spans sit closer than
    `_WORD_GAP_MIN_PX`.
  - 4 parametrized two-sided cases: span count **equals** the adjudicated gold's token
    count on c032/l12, c032/l19, c159/l02, c430/l05.
  - 1 guard case on c411/l09.

  Two of these were strengthened in response to adversarial review, which was right on
  both counts: the invariant test is a restatement of the bridging loop's postcondition
  and cannot fail, so it could not detect **over**-merging — the actual new risk the fix
  introduces. The span-count-equals-token-count cases fail in both directions and close
  that gap. And the c411/l09 case originally asserted `len(spans) == 13`, hard-coding a
  count known to be wrong (11 true tokens) so that a correct future visarga fix would
  have broken the test; it now asserts against the alignment guard instead.
- **Ruff**: clean on `av_accent_binder.py`, `extract_atharvaveda_accents.py`,
  `build_av_calibration_set.py`, `run_av_calibration.py`,
  `test_atharvaveda_transcription.py` — i.e. every file this session touched plus the
  entire set the previous report audited. **7 pre-existing violations remain in
  `tests/unit/test_av_accent_binder.py`** (E402, I001, F401, F841, 3×RUF003); that file
  was last modified before this session's work and was never in the previously linted set.
  Not fixed here: out of scope for a bounded gate, and it is the test file of the
  component under evaluation.
- **mypy** `--strict --ignore-missing-imports` on `src/vedagraph/ingest/av_accent_binder.py`:
  **Success, no issues.**

---

## 10. Source integrity

**FIREWALL INTACT.** No GRETIL, TITUS, VedaWeb, Orlandi, Whitney translation, or any web
resource was consulted by any of the nine readers or by the adjudicator. The only evidence
used was the BSB/MDZ `bsb10219750` page images. Image source decision unchanged:
**BSB_MDZ_SELECTED**, native width 2024 px is the optical ceiling; the archive.org
alternate remains **PROVENANCE_UNVERIFIABLE**.

---

## 11. What revision is actually required

Bounded and specified, in priority order:

Bounded and specified. Items 1–3 are all required to clear `word_binding_acc`; **no one
of them is sufficient**, which is the main correction adversarial review forced on this
report.

1. **Fix the span→token alignment** so that rule spans carrying no whitespace token
   (free-standing visarga dot-pairs, avagraha, multi-stroke dandas) attach to their owning
   word instead of consuming a token slot. Worth +0.0727 on the gate mean (0.85454 →
   0.92727), measured. Not sufficient alone.
2. **Stop pairing gold to bindings by position** (`run_av_calibration.py:202-212`). One
   missed detection currently corrupts every later comparison on the line, scoring correct
   bindings as wrong and one wrong binding as correct. Pair by x-position or by carrier
   instead. This is a *measurement* defect: it makes the reported `word_binding_acc`
   untrustworthy in both directions whenever recall < 1.
3. **Recover the merged svarita** — the c411/l09 mark at x≈690 that fuses with the
   anusvāra dot at `INK = 128` and separates at 170. The only detection miss in 54 gold
   marks, and all three readers found it independently. Needs a second binarisation pass
   or a split of touching components, not a threshold nudge.
4. **Restore the safety property.** `auto_promote_frac = 1.0` on a line that is 73% wrong
   is unacceptable; the binder needs a confidence signal that does not rest on the
   token/span count guard alone.
5. **Promote `aksara_binding_acc` to a gate**, and fix `class_accuracy`'s
   `misclassified // 2` flooring and `detection_precision`'s inability to see positional
   error. Three of the seven current gates cannot detect the failures this session found.
6. **Fix `_verdict()`** so a `= 0` gate cannot print PASS at any value.
7. **Re-adjudicate `c032/l19` to three readers** to remove the `"split"` state and with it
   the glob-order dependence that currently decides a gate.

Only after 1–6 should this gate be rerun. Item 7 should be done first, because until it
is, the gate's own result is not reproducible.
