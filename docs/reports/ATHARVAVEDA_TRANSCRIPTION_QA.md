# Atharvaveda transcription QA — calibration phase

**Work:** Atharvaveda Saṃhitā, Śaunaka recension (`VG:WORK:AV:SAU`)
**Source:** Roth & Whitney, *Atharva-Veda Sanhita*, Berlin: Dümmler 1856.
BSB/MDZ `bsb10219750`, artifact `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN`.
**Policy:** `bsb-1856-devanagari-v2`
**Measured:** 2026-09-08, branch `semantic-pilot-v1`

**Reading rule for this document.** Every number below was produced by running
`scripts/reconcile_atharvaveda_v2.py` over transcription files on disk. A gate
that could not be run says `NOT_RUN` and gives the reason. No gate is marked
PASSED because a build is absent, empty, or plausible.

---

## 1. Verdict

**The transcription method is not yet fit to produce a canonical corpus, and
the accent layer alone is what makes it unfit.**

The designated two-pass reconciliation over two calibration leaves produced
**zero release-eligible units out of 21**. Across every pairing of every
reading taken, **100% of accent-bearing units disagreed on accent placement**,
and the best-agreeing pair in the sample placed only 30.6% of its marks
identically.

This is not the v1 failure repeating. It is the next failure down. In v1 both
readers *dropped* the accent layer and therefore agreed with each other while
both were wrong. Here readers *record* the accent layer densely — and disagree
about it at close to chance. The band-rendering fix made the marks visible; it
did not make them assignable to the same syllable by two readers.

**The blocker moved from rendering to placement. It did not clear.**

Two further findings carry as much weight as the headline:

- **Segmentation and skeleton are close to solved; accents are not.** In the
  best-agreeing pair, unit boundaries matched exactly, 98.7% of skeleton
  characters matched, and 7 of 13 units matched skeleton-for-skeleton. Every
  one of those 7 was still blocked from release by its accents alone. The three
  layers of this transcription fail independently, and only one of them is
  failing badly.
- **Two passes cannot tell you which reader is wrong.** Leaf n32 was read three
  times; only the third reading revealed that one of the two designated readers
  was the outlier (§2.2). On a source this hard, disagreement is the ordinary
  case, so the Pass-3 adjudicator is load-bearing rather than exceptional — and
  a two-reader budget is a false economy.

---

## 2. What was measured

Five readings were made, by separate agents that never saw each other's files
and never consulted any other edition of the Atharvaveda.

| Reader | Protocol | Leaf | Units | Accent marks | `[?]` |
|---|---|---|---:|---:|---:|
| R1 | Full (128 tool calls, ~216k tok) | n15 | 8 | 107 | 1 |
| R2 | Bounded (7 tool calls, ~67k tok) | n15 | 8 | 78 | 0 |
| R1 | Full (128 tool calls, ~216k tok) | n32 | 13 | 199 | 1 |
| R2 | Bounded (7 tool calls, ~89k tok) | n32 | 13 | 115 | 2 |
| B1 | Bounded (12 tool calls, ~70k tok) | n32 | 13 | 172 | 0 |
| B1 | Bounded (14 tool calls, ~70k tok) | n430 | 15 | 163 | 2 |

Leaf n32 therefore carries **three** independent readings, which turns out to
be the most informative thing in this calibration (§2.2). Every reader reported
that the page, not the tool budget, was what limited them.

### 2.1 The designated two-pass reconciliation (R1 × R2, both leaves)

Output: `data/transcriptions/atharvaveda_bsb_1856/v2/calib/reconciled/` and
`reconciled_summary.json`.

| Metric | Value |
|---|---|
| Units read by both | 21 |
| Units read by one only | 0 |
| Units aligned across an unstated coordinate | 8 (see §3.1) |
| Boundary disagreement rate | 0.048 |
| Character disagreement, over skeleton characters | 0.071 |
| **Accent disagreement, over accent-bearing units** | **1.000** |
| Exact agreement rate | **0.000** |
| **Release-eligible units** | **0 of 21** |
| Status counts | 18 `CHARACTER_UNCERTAIN`, 2 `ACCENT_UNCERTAIN`, 1 `BOUNDARY_UNCERTAIN` |

### 2.2 Three readings of one page, and why that matters

Leaf n32 was read three times independently — R1 under the full protocol, R2
and B1 under the bounded protocol. All three pairings, on the same 13 units:

| Pair | Skeleton divergence | Boundary | Accent agreement (union) | Identical skeletons |
|---|---:|---:|---:|---:|
| **R1 (full) × B1 (bounded)** | **0.013** | **0.000** | **0.306** | **7 / 13** |
| R1 (full) × R2 (bounded) | 0.065 | 0.077 | 0.109 | 1 / 13 |
| R2 (bounded) × B1 (bounded) | 0.061 | 0.077 | 0.098 | 0 / 13 |

**R1 and B1 converge; R2 is the outlier.** Two independent readings agreeing to
98.7% of skeleton characters with 7 of 13 units identical is not chance
agreement. R2 diverges from *both* of them at about the same rate (6.5% and
6.1%), and recorded far fewer accent marks than either (115, against B1's 172
and R1's 199 — and on n15, 78 against R1's 107).

This is not "bounded is worse than full": B1 is bounded and is the reading that
agrees closely with R1. It is one reading being weaker than the other two.

**The methodological consequence is the important part.** A two-pass protocol
can detect that two readings disagree; it cannot say which of them is wrong.
Only the third reading identified R2 as the outlier. On a source this
difficult, the Pass-3 adjudicator named in the contract is therefore not a
fallback for rare disputes — it is load-bearing for the ordinary case, because
disagreement is the ordinary case.

**It also removes the protocol confound in the wrong direction.** The clean
same-protocol pair (R2 × B1, bounded × bounded) is *worse* than the
cross-protocol pair, not better. Protocol difference is therefore not what is
producing the disagreement.

### 2.3 The accent layer, position by position

| Quantity | Leaf n15 (R1 × R2) | Leaf n32, best pair (R1 × B1) |
|---|---:|---:|
| Marks recorded by reader A | 107 | 199 |
| Marks recorded by reader B | 78 | 172 |
| Marks at identical position **and** type | **19** | **87** |
| **Agreement over the union** | **0.114** | **0.306** |

Every reader sees that the page is accented and records marks densely. None of
them agree on which syllable carries which mark. **Even the best-agreeing pair
in the sample reaches only 30.6%, and still releases zero units.**

### 2.4 The finding, stated precisely

The three layers of the transcription do **not** fail together, and that
distinction is the most useful result of this calibration. Ranges below span
all pairings; the strong end is the best-agreeing pair.

| Layer | Status |
|---|---|
| **Unit segmentation** | **Reliable at best, mostly reliable otherwise.** Boundary disagreement 0.000 in the best pair, 0.077 elsewhere. No unit was ever seen by only one reader. |
| **Consonant-vowel skeleton** | **Nearly reliable.** 98.7% of skeleton characters agree in the best pair (93.5–94% in pairs involving the outlier reader). 7 of 13 units on n32 matched exactly. |
| **Accent layer** | **Unusable.** 100% of accent-bearing units disagree in *every* pairing; readers place only 9.8–30.6% of marks identically. |

Zero units reached release in any pairing, and the accent layer is what blocked
every one of them — including the 7 units on n32 whose consonant-vowel text two
readers reproduced identically.

### 2.5 What the disagreements look like

Sūkta 1, mantra 1 — accent placement differs across nearly the whole line, and
one conjunct is read two ways:

```
R1: ये त्रि॑ष॒प्ताः प॑रि॒यन्ति॒ विश्वा॑ रू॒पाणि॒ बिभ्र॑तः ।
R2: ये त्रि॒ष्प्णाः परि॒यन्ति विश्वा॑ रूपाणि बिभ्र॑तः ।
```

Sūkta 1, mantra 3 — a substantive skeleton disagreement (`आर्त्नी` vs
`ज्यालनी`) alongside a conjunct rendering difference (`यछतु` vs `यच्छतु`):

```
R1: इ॒हैवाभि वि त॑नू॒भे आर्त्नी॑ इव॒ ज्यया॑ । वा॒चस्पति॒र्नि य॑छतु ...
R2: इ॒हैवा॑भि वि त॒न्नुभे ज्याल॑नी इ॒व ज्यया॑ । वाचस्पति॒नि यच्छ॑तु ...
```

---

## 3. Two defects found and fixed this phase

### 3.1 The reconciler manufactured false structural disagreements

**Severity: DEFECT. Fixed, with tests.**

Leaf n15 is the first text page and prints no running head. R1 followed the
brief literally and recorded `kanda: null` because the page does not print it.
R2 carried the kāṇḍa over from context and recorded `kanda: 1`. Both are honest
readings of the same eight units.

`unit_key` included `kanda`, so the two readings keyed differently and **every
one of the eight units was graded `STRUCTURAL_REVIEW_REQUIRED` as read by one
reader only**. The first reconciliation run reported 16 units, 0 read by both,
and measured nothing at all — while appearing to run successfully.

This would have recurred on every leaf where one reader reads a coordinate off
the head and the other records that the page does not print it.

The fix aligns units across a coordinate one reader left unstated, and *only*
that:

- a `null` against a stated value aligns, and the stated value is carried;
- two *different stated* values do **not** align and remain a structural
  disagreement;
- an ambiguous rescue (more than one candidate) is refused;
- a genuinely one-sided unit stays one-sided;
- every rescued pair is counted in the summary as
  `units_aligned_across_an_unstated_coordinate`, so the alignment is never
  silent, and is still graded on its text.

Seven tests pin this behaviour, including that tolerating a null coordinate
does not tolerate a text disagreement.

### 3.2 The uncertainty backlog was not actionable

**Severity: DEFECT. Fixed.**

The machine-readable backlog recorded each unit's status and a prose reason,
but not the two readings that produced them. An adjudicator could not act on a
backlog item without opening the reconciled file by hand. The backlog now
carries `r1_text`, `r2_text`, and `coordinate_note` alongside the verdict.

### 3.3 The build asserted its own QA verdict

**Severity: DEFECT. Fixed, with tests.**

Running the build for the first time against real reconciled data — it had
never been executed against any until now — surfaced two problems in one line.
It crashed on `QAStatus.PASS`, which is not a member of the enum (`PASSED` is);
and the value was **hardcoded**, so the release would have been published
carrying a passing QA status no matter what the two readers produced. On this
very data that would have stamped a pass on a corpus with zero released units.

That is exactly the vacuous pass this project's QA rule forbids. `qa_status()`
now derives the verdict: `NOT_RUN` when nothing was reconciled, `FAILED` when
nothing reached release, `PASSED_WITH_WARNINGS` when units were left behind,
`PASSED` only when the whole reconciliation released. Four tests pin it.

The build's own manifest for this calibration data now reads
`"qa_status": "FAILED"`, which is the correct verdict.

### 3.4 Verification that the pipeline runs end to end

With the fixes above, the build completes against the reconciled calibration
data and behaves correctly under failure:

| Field | Value |
|---|---|
| `units_reconciled` | 21 |
| `units_released` | **0** |
| `backlog_units` | **21** |
| `prohibited_source_contamination` | **0** |
| `deterministic_rebuild` | **true** (`--check`, byte-identical) |
| `qa_status` | **FAILED** |

The pipeline correctly refuses to release a single unit and routes all 21 to an
actionable backlog. The infrastructure is sound; the transcription input is
what is not.

---

## 4. Gate results

| Gate | Result | Evidence |
|---|---|---|
| Unit test suite | **PASS** — 839 passed, 1 skipped | `pytest tests/unit` (828 before this phase, +11 new) |
| Ruff lint | **PASS** | `ruff check` on all AV scripts and tests |
| Strict mypy | **PASS** (exit 0) | `mypy` on `vedagraph` package |
| Deterministic build | **PASS** | fixed `BUILD_TIMESTAMP`, no clock read |
| Contamination firewall | **PASS** | `assert_no_contamination()`; no GRETIL/TITUS/VedaWeb/Orlandi source consulted |
| Cross-Veda key collision | **PASS** | `test_the_four_vedas_do_not_collide_in_key_or_uuid_space` |
| Accent convention frozen | **PASS** | convention A; YV side gate passed, no YV change needed |
| OCR route | **REJECTED** | 0 Devanagari codepoints from 317 chars; recorded in `method_calibration_ocr.json` |
| **Two-pass transcription fidelity** | **FAIL** | 0 of 21 release-eligible units across two leaves; 100% accent disagreement in every pairing |
| Full-corpus transcription | `NOT_RUN` | 458 leaves not transcribed; blocked by §1 |
| Adversarial release QA | `NOT_RUN` | no canonical release exists to adversarially QA |
| Mantra total reconciliation | `NOT_RUN` | derivable only from a completed transcription |

---

## 5. Method selection: deferred, not made

The calibration was designed to choose between the full and bounded protocols
on measured fidelity. **That choice is premature and this report does not make
it.** Throughput is not the binding constraint if no protocol produces
release-eligible text.

The three-way comparison in §2.2 also shows the choice was posed wrongly.
Protocol was not the dominant variable: the bounded reading B1 agreed with the
expensive full reading R1 to 98.7%, while the other bounded reading R2 diverged
from both. **Reader-to-reader variance within a protocol exceeded the
difference between protocols.** Selecting a protocol therefore cannot fix
fidelity here — the leverage is in how many readings are taken and how they are
adjudicated (§6.1), not in how long each one looks.

For the record, the throughput figures stand: the full protocol costs ~216k
tokens per leaf-pass (~197M for the corpus at two passes) and the bounded
protocol ~70k (~64M). Both exceed one session budget by a wide margin, and both
are moot until §1 is resolved.

---

## 5A. The source artifact is 2024px, not 4000px

**Severity: overturns a recorded project claim. Found 2026-09-08.**

`scripts/fetch_atharvaveda_bsb_scan.py` carried this justification for its
`IMAGE_WIDTH = 4000`:

> At width 2000 the Vedic accent marks of this fount sit on akṣara BOUNDARIES
> and cannot be assigned to a specific akṣara without guessing […] At width
> 4000 the same marks are unambiguously attached to their akṣara. The IIIF
> 'full' size is only 2025px, so the width must be requested explicitly; 4000
> is a real derivative, not an upscale.

**The last sentence is false, and it is load-bearing.** The IIIF service
reports canvas n32 as `"width": 2024, "height": 2992`, lists no size above
2024, and advertises `sizeAboveFull` — which is precisely why a request for
4000 returns an image instead of an error.

Measured, not inferred:

| Comparison | Mean absolute difference |
|---|---|
| Stored 4000px, downscaled to 2024, vs native 2024 | 1.48 / 255 (0.6%) |
| **Native 2024, Lanczos-upscaled to 4000, vs stored 4000** | **1.51 / 255 (0.6%)** |

The second row is decisive. Had the 4000px file held real optical detail beyond
2024, a plain upscale of the native rendering could not have reproduced it to
within JPEG noise. **The entire 458-leaf 4000px corpus is a server-side upscale
of a 2024px master and carries no additional information.**

### Consequences

1. **2024px is the resolution ceiling of this artifact.** At that scale the
   text block is roughly 1592 px wide carrying about 40 lines, so an accent
   mark is a few pixels. Whatever the accent layer's true legibility is, this
   is all of it there is.
2. **The prior diagnosis was wrong about its own cause.** The v1 accent failure
   was attributed to acquisition resolution and declared fixed by re-fetching
   at 4000. No acquisition improvement occurred. Any gain between the 2000px
   and 4000px passes was interpolation plus the genuine perceptual benefit of
   rendering glyphs larger — not recovered detail.
3. **Option (b) cannot be delivered from this artifact.** Accent fidelity
   cannot be raised by re-fetching or re-cropping `bsb10219750`. Raising it
   requires a *different and higher-resolution digitisation* of the 1856
   edition. That is a source-acquisition task, and it is now the critical path.
4. Magnification still helps *perceptually* — attributing a bar to a line is a
   spatial judgement, and larger glyphs make it easier at fixed information
   content. §5B tests how much that alone is worth.

`IMAGE_WIDTH` is left at 4000 so the pinned `2026-09-07` snapshot stays
byte-stable, with the constant now documenting that it buys resolution which
does not exist.

---

## 6. Decisions taken by the project owner, 2026-09-08

Both open questions below were put to the project owner and are now settled.
They are recorded here as decisions, not recommendations.

| Question | Decision |
|---|---|
| What to do with the accent layer | **Fix accents first, then release.** Nothing is released until accent fidelity is raised and re-measured on the calibration leaves. The corpus lands complete or not at all. |
| Readings per leaf in production | **Three independent readings, majority adjudication.** Two passes detect disagreement without resolving it; the third reading is what made this calibration interpretable. |

**Consequences that follow directly:**

- Skeleton-only release (former option (a)) is **rejected**. The 9.5–54%
  partial corpus will not be published.
- The binding open risk is now **whether accent fidelity can be raised at
  all.** That is unproven. Nothing in this calibration shows the 1856 accent
  layer is readable to agreement by any method; it shows only that the current
  method cannot. This must be established on a small sample before any
  commitment to 458 leaves.
- Production cost rises to three bounded reads per leaf, ~210k tokens/leaf,
  ~96M for the corpus — but only after the accent question is answered, since
  a three-pass run against an unreadable accent layer fails three times as
  expensively.

### 6.1 Superseded guidance

1. **Move to three readings per leaf, or accept that disagreements cannot be
   resolved.** This is the firmest recommendation in the report and it is not
   the accent question. Two passes detected disagreement on every unit and
   could not adjudicate any of it; the third reading of n32 immediately
   identified which reader was weak. Budgeting two passes and a rare Pass-3 has
   the economics backwards for this source.

2. **Decide what the accent layer is for.** A project-owner decision, not one
   to infer. Three coherent options:
   - **(a) Release the skeleton, withhold the accents.** How much this actually
     releases depends sharply on reader quality, and the honest range is wide:
     under the designated R1 × R2 pairing it would release **2 of 21 units
     (9.5%)**; under the best-agreeing pair on n32 (R1 × B1) it would release
     **7 of 13 (54%)**. So this is not a shortcut to a corpus — it removes the
     accent blocker and leaves skeleton quality as the next binding constraint.
     Worth doing only together with (1).
   - **(b) Raise accent fidelity** with a targeted method — per-pāda crops at
     higher magnification, or an accent-only pass over an already-agreed
     skeleton — and re-measure before committing to 458 leaves. Attractive
     because segmentation is solved and the skeleton is close: only
     mark-to-syllable assignment needs the extra magnification.
   - **(c) Publish accents as a separate, explicitly uncertain layer**, never as
     verified canonical text.

   Options (a) and (b) compose: (a) can ship first and (b) can add the accent
   layer later without re-transcribing, since segmentation and skeleton would
   already be fixed.
3. **Do not begin production transcription until (1) and (2) are settled.** At
   ~64M tokens for the cheaper protocol, a full run against an unfit method is
   the single most expensive mistake available here.

---

## 7. Bearing on the four-Veda gate

`ALL_FOUR_VEDA_CANONICAL_CORPORA_READY_FOR_FREEZE` is **not** emitted.

The Atharvaveda has no canonical corpus from the 1856 scan, and the method for
producing one does not currently clear its own fidelity gate. The Ṛgveda,
Sāmaveda, and Yajurveda positions are unchanged by this report; see
`ATHARVAVEDA_CANONICAL_RELEASE.md` §"Four-Veda release gate assessment".

Note that the AV row in `FOUR_VEDA_QA_REPORT.md` (`atharvaveda_pilot_v1`, 174
passages, PASS) refers to the **rejected v1 corpus**, which is GRETIL-derived
and fails the independence firewall. It is not evidence about the 1856
transcription and must not be cited as such.
