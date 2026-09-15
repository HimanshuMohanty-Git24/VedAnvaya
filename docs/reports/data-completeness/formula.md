# Formula / parallel / variant completion

Agent 12 of the Post-V1 Data Completeness Campaign, Wave 2, owner's section M. Every figure
below was produced by running code against the canonical corpus or by read-only Cypher
against the live graph on the date shown. Where a committed report and this one disagree,
both numbers appear and the measurement that produced this one is named.

- Measured: 2026-09-15
- Branch: `phase-data-completeness-v2`
- Access: `MATCH` / `RETURN` and `db.relationshipTypes()` only. **Nothing was written to the
  graph**, which stands unchanged at 108,779 nodes and 265,295 relationships.
- Write surface: `data/staging/formula/` and this file. No existing repo file was modified.
- Validator: `scripts/validate_staging_artifact.py data/staging/formula --graph` → **PASS**,
  every check at 100% evaluation coverage, 24 files checksummed.

---

## 0. The first finding is that nothing was stale

Re-running discovery on the current corpus was the mandate's first instruction, so it was
the first thing done, and the answer is that the committed artifacts reproduce **byte for
byte**:

| artifact | rebuilt | committed | digests equal |
|---|--:|--:|:--:|
| `formulas.jsonl` | 4,825 | 4,825 | yes |
| `formula_occurrences.jsonl` | 22,686 | 22,686 | yes |
| `cross_veda_parallels.jsonl` | 6,271 | 6,271 | yes |

The canonical corpus has not moved since those artifacts were built, so **the formula and
parallel gap is not staleness**. Formula coverage at RV 48.4% / SV 71.1% / YV 61.5% /
AV 50.5% is not a shortfall waiting for a re-run; it is what the declared thresholds emit
from this corpus. Every gap below is structural, and each one is named as a specific
structure rather than as a missing percentage.

The artifact also reconciles against the graph exactly: 6,271 cross-Veda rows + 256
within-Rigveda `EXACT_PARALLEL_OF` edges from the older `vedagraph.lexical` layer = the
6,527 parallel and reuse edges the graph holds. Rows sent equals rows landed.

---

## 1. The biggest risk was the text layer, and it is discharged

`proofs/search_derivative_hazard.json`.

The Atharvavedic `SEARCH_DERIVATIVE` layer deletes base letters, not only accents. Measured
here over all 5,839 AV mantras by an NFD base-letter multiset diff against `PRIMARY_TEXT`:

| measure | result |
|---|--:|
| AV mantras carrying a `SEARCH_DERIVATIVE` layer | 5,839 |
| AV mantras **losing at least one base letter** in it | **5,134** |
| deletions of `m` (the anusvāra) | 11,582 |
| deletions of `r` (vocalic ṛ) | 5,139 |

```
AVS 1.2.2  PRIMARY_TEXT       jyā̀ke pári ṇo namā́śmānaṃ tanvàṃ kr̥dhi | …
           SEARCH_DERIVATIVE  jyāke pari ṇo namāśmāna tanva kdhi …
AVS 1.2.3  PRIMARY_TEXT       vr̥kṣáṃ yád gā́vaḥ pariṣasvajānā́ anusphuráṃ śaráṃ árcanty r̥bhúm | …
           SEARCH_DERIVATIVE  vkṣa yad gāvaḥ pariṣasvajānā anusphura śara arcanty bhum …
```

This run never reads it. `vedagraph.enrich.corpus.PRIMARY_TEXT_ROLE` selects `PRIMARY_TEXT`
for RV/SV/AV and `EXTRACTED_FROM_CONTAINER` for the Yajurveda, and `load_corpus` raises if
any Veda yields no text. The proof records, beside each corrupted derivative, the string this
run actually compared — identical to `PRIMARY_TEXT` in both cases. The full layer census was
enumerated rather than assumed: `SEARCH_DERIVATIVE` exists for the Atharvaveda alone.

### 1.1 Accent was measured by name and base, never by codepoint block

`proofs/accent_measured_by_name_not_range.json`. A combining mark counts as a tone mark when
its Unicode **name** contains TONE, SVARITA, UDĀTTA or ANUDĀTTA, or when it is one of the
five Latin GRETIL/VedaWeb tone marks **and its base character is a vowel**.

| Veda | accented, by name and base | by a naive range-plus-acute scan | marks actually placed |
|---|--:|--:|---|
| RV | 10,552 | 7,194 | U+0331 ×101,175, U+030D ×74,801 |
| SV | **0** | 0 | none |
| YV | 1,974 | **780** | U+0952 ×24,329, U+0951 ×17,204, U+1CD4 ×1 |
| AV | 5,837 | 5,839 | U+0301 ×67,662, U+0300 ×1,271 |

Both traps in `MEMORY.md` reproduce and both are avoided. The naive scan's 780 Yajurvedic
"accented" texts are the mantras carrying U+1CEA or U+1CEC — **anusvāra** signs, not tone
marks. Its RV figure of 7,194 agrees with nothing: the RV's tone marks are U+0331 and U+030D,
in neither the Vedic Extensions block nor the acute/grave pair, so the 7,194 it counts are
`ś` characters and the agreement would have been accidental even had it been right. Two AV
mantras carry no tone mark on any vowel base; the naive scan counts all 5,839 because every
AV mantra contains an `ś`.

---

## 2. The four claims, kept four claims

The mandate's central distinction. Each is a different assertion, decided differently, and
no row in the artifact carries two of them.

| claim | what it asserts | how it is decided |
|---|---|---|
| **EXACT_PARALLEL** | these two verses are as identical as their two editions can be shown to be | string equality at the pair's **comparison ceiling** |
| **VARIANT** | the same verse, reached only *below* that ceiling | string equality at a weaker level, plus a `transformation_type` naming which step was needed |
| **NEAR_PARALLEL** | substantially the same verse, materially altered | identical at *no* level, and `0.5·char4gram_jaccard + 0.5·lcs_ratio ≥ 0.72` |
| **FORMULA_FAMILY** | a set of *formulas* related by containment | strict substring on the collapsed identity surface — not a passage relation at all, and it lives in `formula_families.jsonl` |

### 2.1 The comparison ceiling is what makes the distinction honest

A transformation type that ignores the ceiling misdescribes the corpus. An RV/SV pair
identical at `SCRIPT_FOLDED` is not "orthographically varied" — it is as identical as a
Devanagari edition and a Latin edition can be shown to be, because they share no code points.
So the ceiling is computed first, from script **and from the measured accent-notation class**:

| condition | ceiling |
|---|---|
| different script | `SCRIPT_FOLDED` |
| same script, different accent-notation class | `ACCENT_INSENSITIVE` |
| same script and notation, **both layers print their own address inline and the pair's whole `UNICODE_NORMALIZED` difference is digits** | `PUNCTUATION_NORMALIZED` |
| otherwise | `SOURCE_EXACT` |

The third condition was **not** in the first version of this layer. It was added by the
adversarial preflight in §13.5, which found 134 within-recension pairs typed `VARIANT` whose
entire difference is their own printed verse number. Read §13.5 before trusting any
`EXACT`-versus-`VARIANT` figure here.

The notation classes are derived from the marks actually placed, not declared:

| Veda | notation class |
|---|---|
| RV | `GRETIL_RV_ANUDATTA_SVARITA` (macron-below + vertical-line-above) |
| AV | `GRETIL_AV_ACUTE_GRAVE` (acute + grave) |
| YV | `DEVANAGARI_SVARA` (U+0951 / U+0952) |
| SV | `UNACCENTED` |

| ceiling | pairs |
|---|--:|
| `SOURCE_EXACT` (within recension) | 1,409 |
| `PUNCTUATION_NORMALIZED` (within recension, address printed inline) | 139 |
| `SCRIPT_FOLDED` (cross-script) | 3,023 |
| `ACCENT_INSENSITIVE` (same script, two notations) | 1,564 |

---

## 3. The identity ladder — and the within-recension layer that did not exist

Every one of the 20,095 comparable mantras was bucketed at all six levels. 2,205 identity
pairs, of which **1,538 are cross-recension — reproducing `crossveda`'s documented 1,538
exactly** — and **667 are within-recension**.

| level reached | cross-recension | within-recension |
|---|--:|--:|
| `SOURCE_EXACT` | 0 | 451 |
| `PUNCTUATION_NORMALIZED` | 0 | 158 — of which 134 are an address difference, §13.5 |
| `ACCENT_INSENSITIVE` | 150 | 23 |
| `SCRIPT_FOLDED` | 600 | 4 |
| `SANDHI_INSENSITIVE` | 788 | 31 |
| **total** | **1,538** | **667** |

**Before this run, only the Rigveda had any within-recension parallel edge at all**: 252
`EXACT_PARALLEL_OF` at `SOURCE_EXACT`, 4 more on a lemma criterion, and 69 `PARALLEL_TO`. The
Samaveda, Yajurveda and Atharvaveda had zero. The 252 reproduce here exactly; the 415 SV/YV/AV
pairs are new.

| Veda | within-recension identity pairs found | already in the graph | new |
|---|--:|--:|--:|
| RV | 252 | 252 | 0 |
| SV | 204 | 0 | **204** |
| AV | 131 | 0 | **131** |
| YV | 80 | 0 | **80** |

### 3.1 A correction to CORPUS_D11: 587 understates it by 380 mantras

The brief and `corpus-audit.md` record 190 RV / 349 SV / 6 YV / 42 AV mantras sharing
identical Sanskrit within one recension — 587, measured by `content_sha256` within one
`text_role`. That is **byte** identity. The ladder also reaches identity after editorial
apparatus, accent placement, orthography and word division are set aside:

| Veda | by `content_sha256` | by the ladder | difference |
|---|--:|--:|--:|
| RV | 190 | 190 | 0 |
| SV | 349 | **405** | +56 |
| YV | 6 | **128** | +122 |
| AV | 42 | **244** | +202 |
| **total** | **587** | **967** | **+380** |

The Rigvedic figure agrees exactly, and that is the control: one consistently-spelled edition
has nothing below byte identity to find. The other three do, and the Yajurvedic 6 is the
extreme case — its source prints editorial apparatus and word divisions inconsistently, so
byte identity finds 3 pairs where the ladder finds 80.

### 3.2 A correction to the Samavedic characterisation: the concentration is not Āraṇya

The brief and `corpus-audit.md` say the Samavedic cases "concentrate on Āraṇya-versus-
Uttarārcika pairs". Measured, the 204 SV-SV identity pairs join:

| segments joined | pairs |
|---|--:|
| **CHANDA ↔ UTTARA** | **191** |
| ĀRAṆYA ↔ UTTARA | 8 |
| UTTARA ↔ UTTARA | 5 |

The concentration is the **Chandas-ārcika (Pūrvārcika) against the Uttarārcika**, which is the
textually expected pattern — the Uttarārcika restates Pūrvārcika verses in ritual sequence.
The Āraṇya parvan holds 55 of the Samaveda's 1,844 verses (ĀRAṆYA 55, CHANDA 585,
MAHĀNĀMNYĀ 10, UTTARA 1,194), so it could not have carried the concentration. 8 of its 55
verses are in an identity pair, which is a high *rate* and a small *count*, and the committed
sentence reads the rate as the count.

### 3.3 Zero false duplicates, tested rather than assumed

`proofs/false_duplicate_test.json`. All 667 within-recension pairs, discriminated on
`canonical_citation`, parent and `sequence_in_parent`:

| verdict | pairs |
|---|--:|
| same `canonical_citation` (an ingestion duplicate) | **0** |
| same parent, adjacent sequence (an off-by-one cut) | **0** |
| same parent, non-adjacent sequence | 18 (11 YV, 6 AV, 1 RV) |
| distinct parents | 649 |

Every pair joins two distinct printed addresses. The 18 same-parent pairs are a refrain
repeating inside one adhyāya or hymn — repetition, not duplication.

**A defect of my own, recorded.** The first version of this test compared `structural_path`,
which is null for the Rigveda, so all 252 RV pairs came back `SAME_ADDRESS_INGESTION_DUPLICATE`
while the printed examples plainly showed different maṇḍalas (RV 1.13.9 against RV 5.5.8). A
null-equals-null comparison is not a match. Rebuilt on citation, parent and sequence.

---

## 4. Accent-only differences: 150 refused, 23 kept

`proofs/accent_only_false_family_test.json`. This is the hazard the mandate named, and it has
two edges, not one.

173 pairs become identical only once accents are stripped. Classifying them by measured
notation class:

| case | pairs | reading |
|---|--:|---|
| `INCOMPATIBLE_NOTATION_CLASSES` | **150** (81 AV-RV, 69 SV-YV) | the accent difference is a *notation* difference. `ACCENT_INSENSITIVE` is these pairs' ceiling, so no accent claim is possible and none is made. The live graph types all 150 `EXACT_PARALLEL_OF` and **is correct**. |
| `SAME_NOTATION_DIFFERENT_ACCENTUATION` | **21** (15 AV-AV, 6 YV-YV) | one edition, one notation, different marks placed. Real accent variants. |
| `SAME_NOTATION_SAME_MARK_COUNTS` | 2 | same inventory and same per-mark totals, so the difference is in mark *position*. Still a real variant; the per-mark counter cannot name it and that limit is stated. |

Had I typed all 173 as accent variants I would have invented 150 that are artefacts of GRETIL
marking the Atharvaveda with acute/grave and the Rigveda with macron-below/vertical-line, and
of the Samavedic source marking nothing at all. Had I typed none, I would have erased 21 real
ones. All 21 are printed in the proof beside their marks:

```
AVS 2.33.1   akṣī́bhyāṃ te nā́sikābhyāṃ … yákṣmaṃ  śīrṣaṇyàṃ  mastíṣkā…   ACUTE ×9,  GRAVE ×1
AVS 20.96.17 akṣī́bhyāṃ te nā́sikābhyāṃ … yákṣmaṃ  śī́rṣaṇyàṃ mastíṣk…   ACUTE ×10, GRAVE ×1
```

---

## 5. Orthographic variation, named at the codepoint

`proofs/transformation_typology.json` § `orthographic_variation_named_at_the_codepoint`.

475 identity pairs agree only after the transcription fold, 470 of them AV-RV. Diffing the
`ACCENT_INSENSITIVE` surface — the level at which they *fail* — names the cause exactly:

| occurrences | AV side | RV side | Unicode |
|--:|---|---|---|
| 763 | `ṃ` | `ṁ` | COMBINING DOT BELOW → COMBINING DOT ABOVE |
| 493 | `r̥` | `ṛ` | COMBINING RING BELOW → COMBINING DOT BELOW |
| 27 | `cch` | `ch` | the `cch`/`ch` fold |
| 6 | `ṃ` | `m̐` | dot below → candrabindu |

```
AVS 1.4.1   ambayo yanty adhvabhir jāmayo adhvarīyatām  pr̥ñcatīr  madhunā payaḥ
RV  1.23.16 ambayo yanty adhvabhir jāmayo adhvarīyatām  pṛñcatīr  madhunā payaḥ
```

**The GRETIL Atharvaveda transcribes in ISO 15919 and the GRETIL Rigveda in IAST.** That is a
transmission fact about two editions, not noise, and the 470 pairs are the same verse in two
transcription schemes.

The remaining 5 are Devanagari-internal and were read individually:

```
SV CHANDA 5.8.7 ~ SV UTTARA 7.3.10.1   ्ऋ  ↔ ृ    virāma + LETTER VOCALIC R vs VOWEL SIGN VOCALIC R
SV UTTARA 9.1.5.2 ~ VSM 15.45           ृ  ↔ ्ऋ    the same, the other way round
VSM 3.14 ~ VSM 12.52                    ृ  ↔ ्ऋ
VSM 13.37 ~ VSM 33.4                    ऽ  deleted twice   DEVANAGARI SIGN AVAGRAHA
VSM 18.31 ~ VSM 33.52                   ऽऽ ↔ a space
```

Three are the Wikisource sources spelling vocalic ṛ two ways, two are avagraha present on one
side only. `FOUR_VEDA_NORMALIZATION_POLICY` §8.3 records avagraha as deliberately **not**
folded — it is a real orthographic sign, not editorial apparatus — so these survive as
variants by design rather than by omission.

---

## 6. Near parallels within recension, on a floor re-measured here

`proofs/near_parallel_floor_calibration.json`. 16,550 within-recension candidate pairs from
MinHash banding over character 4-grams; largest band bucket 54 against a cap of 800, so
nothing was skipped.

| stage | pairs |
|---|--:|
| candidates | 16,550 |
| already identical | 667 |
| lossless prune by the n-gram bound | 13,342 |
| lossless prune by the length bound | 3 |
| below the 0.72 floor | 1,101 |
| cleared the floor | 1,437 |
| dropped by the both-sided degree cap | 562 |
| **kept** | **875** (AV 674, RV 70, SV 68, YV 63) |

`667 + 13,342 + 3 + 1,101 + 1,437 = 16,550`, and `1,437 = 562 + 875`. The 1,101 floor
rejections and all 562 cap drops are written out individually in `rejected_pairs.jsonl` with
their similarity, so both costs are enumerable rather than aggregate.

### 6.1 Recalibrating the floor, and what the recalibration actually showed

The 0.72 floor is imported from this repository's cross-Veda policy, and a threshold measured
on a different population is not a threshold. 40,000 random same-recension pairs per Veda:

| Veda | mean | p99 | p99.9 | p99.99 | max |
|---|--:|--:|--:|--:|--:|
| RV | 0.163 | 0.220 | 0.247 | 0.345 | 0.378 |
| SV | 0.163 | 0.227 | 0.268 | 0.353 | 0.636 |
| YV | 0.153 | 0.217 | 0.318 | 0.611 | **0.740** |
| AV | 0.156 | 0.217 | 0.248 | 0.664 | **0.918** |

Read as a null distribution this says the floor fails: a random Yajurvedic pair reached 0.740
and a random Atharvavedic pair 0.918, both at or above 0.72. **Reading the tail shows that
reading is wrong.** Every top-of-sample pair is a genuine near parallel:

```
0.918  AVS 16.8.20 ~ AVS 16.8.11   jitamasmākamudbhinnamasmākam…  (the same litany)
0.740  VSM 28.42   ~ VSM 28.43     devonarāśaṃsodevamindraṃ… / devovanaspatirdevamindraṃ…
```

In a corpus this repetitive a random sample is not a null sample, and the sample's maximum is
signal. The usable statistic is the p99.9, and the floor sits **2.3× to 2.9× above every
Veda's p99.9**. Decision: keep 0.72 — not imported on trust, re-measured, and the measurement
read rather than reported.

**A defect of my own, recorded.** My first pass read the random maximum as a null maximum and
concluded the floor was unsafe on the Yajurveda and Atharvaveda. That conclusion was wrong and
it was wrong in the direction that would have produced a made-up threshold.

### 6.2 The weakest accepted pairs, read by hand

All six pairs at 0.720–0.721, and **0 of 6 are false positives**:

```
0.720  RV 10.58.4  ~ RV 10.58.7    yatte catasraḥ pradiśo / yatte apo yadoṣadhīr — same refrain, one pāda substituted
0.721  AVS 3.26.3  ~ AVS 3.26.4    the direction-formula series
0.721  VSM 28.37   ~ VSM 28.40     the metre series
0.721  AVS 15.11.6 ~ AVS 15.11.10  the vrātya catechism, one word varied
```

Shorter side of an accepted pair: min 20 characters, p10 54, median 91.

### 6.3 The existing Rigvedic layer is not retracted

69 `PARALLEL_TO` edges exist from `vedagraph.lexical`. 40 of them are also found here; 29 are
not. Those 29 are the difference between two *declared* policies — the lexical layer accepts
on ordered token similarity ≥ 0.80 with token Jaccard ≥ 0.70, edit similarity ≥ 0.80 and
length ratio ≥ 0.60; this run scores characters. Neither is a defect in the other, and this
run retracts none of them.

---

## 7. Transformation typology — 6,135 rows, 0 untyped

> Revised by §13.5. The counts below are post-fix: 134 rows moved from `EDITORIAL_APPARATUS`
> to `NONE_AT_COMPARISON_CEILING` once the third ceiling axis was added.

`GAP-CROSS_VEDA-002` recorded 0 of 6,527 parallel edges carrying a transformation type. The
vocabulary was declared before any row was produced, 11 closed members, and every row carries
its `comparison_ceiling` beside its type.

| claim | scope | type | rows |
|---|---|---|--:|
| IDENTITY | cross | `WORD_DIVISION` | 788 |
| IDENTITY | cross | `ORTHOGRAPHIC_VARIATION` | 471 |
| IDENTITY | cross | `NONE_AT_COMPARISON_CEILING` | 279 |
| IDENTITY | within | `NONE_AT_COMPARISON_CEILING` | 591 |
| IDENTITY | within | `WORD_DIVISION` | 31 |
| IDENTITY | within | `EDITORIAL_APPARATUS` | 24 |
| IDENTITY | within | `ACCENT_PLACEMENT` | 23 |
| IDENTITY | within | `ORTHOGRAPHIC_VARIATION` | 4 |
| NEAR | cross | `SUBSTITUTION` | 1,778 |
| NEAR | cross | `MIXED` | 882 |
| NEAR | cross | `INSERTION` | 279 |
| NEAR | cross | `DELETION` | 96 |
| NEAR | cross | `REORDERING` | 14 |
| NEAR | within | `MIXED` | 441 |
| NEAR | within | `SUBSTITUTION` | 367 |
| NEAR | within | `INSERTION` | 36 |
| NEAR | within | `DELETION` | 27 |
| NEAR | within | `REORDERING` | 4 |

Every near-parallel row carries up to four difference spans as evidence, taken from
`SequenceMatcher` opcodes with `autojunk=False` — the trap `MEMORY.md` records, which on a
character sequence declares the ordinary vowels of Sanskrit to be junk.

**One vocabulary member is unused and it is a verified zero.** `UNICODE_NORMALIZATION` fires
on 0 pairs: no two verses in this corpus differ only in NFC, consistent with
`FOUR_VEDA_NORMALIZATION_POLICY` §3 measuring 0 non-NFC-stable records in 21,936.

**A defect of my own, recorded.** My first typology special-cased accent notation instead of
deriving a ceiling, which labelled 129 cross-*script* identities
`ACCENT_NOTATION_INCOMPARABLE` — a statement about accent for pairs whose difference is script.
Rebuilt around the ceiling.

### 7.1 515 retype recommendations, and they are recommendations

| existing edge | proposed | type | rows |
|---|---|---|--:|
| `EXACT_PARALLEL_OF` | `VARIANT_OF` | `ORTHOGRAPHIC_VARIATION` | 470 AV-RV, 1 SV-YV |
| `PARALLEL_TO` | `NEAR_PARALLEL_OF` | substitution / mixed / deletion / reordering | 40 RV-RV |
| `EXACT_PARALLEL_OF` | `NEAR_PARALLEL_OF` | substitution / mixed | 4 RV-RV |

The existing edges are not wrong on their own terms. `crossveda.identity_predicate` splits
identity at word division, so everything above `SANDHI_INSENSITIVE` becomes
`EXACT_PARALLEL_OF`; this artifact proposes splitting at the comparison ceiling instead, which
is what makes an orthographic difference visible. `VARIANT_OF`'s own docstring — *"the same
verse differing only in how the two editions write it: accent notation, word division,
orthography"* — describes the 471 precisely. **Nothing is applied.** Each row carries
`retype_is_a_recommendation: true` and the lead decides.

---

## 8. `SHARES_FORMULA_WITH` — GAP-FORMULA-001, closed

`proofs/shares_formula_with_policy.json`.

**The absence is deliberate and was already documented in code.**
`vedagraph.enrich.predicates.UNPOPULATED_BY_DESIGN` names `SHARES_FORMULA_WITH` and gives the
reason: the `USES_FORMULA` hub carries the fact in two hops. The registry's "designed and
never populated" is true of the data and false of the intent, and the registry's own closure
test is the right one — *a declared selectivity policy with a stated ranking key*.

**A figure in that rationale is wrong.** It states materialising would add 87,296 edges.
87,296 reproduces exactly — as the sum over formulas of C(n,2), which counts a passage pair
once per formula it shares. As *edges* a pair is one edge however many formulas it shares, and
the distinct-pair count is **53,167**. The stated cost of materialising was 64% too high.

**The policy**, following the precedent the registry names (`SHARES_ENTITY_VOCABULARY_WITH`,
materialised at 2,141 edges with distinctiveness as its ranking key):

- **Ranking key:** `distinctiveness = Σ ln(20210 / mantra_df(formula))` over the shared
  formulas — an IDF sum on the same scale as the entity-vocabulary layer's, so the two do not
  disagree about what "distinctive" means.
- **Eligibility:** at least 2 shared formulas.
- **Selectivity:** top 3 per passage per Veda, both-sided intersection — the cut
  `crossveda` proves is an actual degree bound, unlike keep-if-either-side-wants-it.

The grid was measured before the cell was chosen:

| min shared | K | edges | passages reached |
|--:|--:|--:|--:|
| 1 | 5 | 23,204 | 9,952 |
| 1 | 3 | 17,086 | 9,528 |
| 2 | 5 | 7,640 | 4,673 |
| **2** | **3** | **6,148** | **4,491** |
| 3 | 3 | 2,838 | 2,281 |

| outcome | value |
|---|--:|
| edges emitted | 6,148 |
| passages reached | 4,491 of the 10,574 with any formula sharing |
| pairs sharing exactly one formula, excluded | 33,401 |
| pairs cut by the top-K | 13,618 |
| kept pairs **not** already joined by a parallel edge | 3,545 (58%) |

By Veda pair: RV-SV 1,050, AV-RV 1,043, RV-RV 988, AV-AV 854, RV-YV 555, AV-SV 395, AV-YV 374,
YV-YV 369, SV-SV 300, SV-YV 220.

**The recall cost, stated plainly.** 6,083 passages with formula sharing get no edge. They
lose nothing: the edge is an *index* over `USES_FORMULA`, not a new fact, and the two-hop
traversal is unchanged. An edge covering all 53,167 pairs would defeat the hub it indexes,
which is the reason the type was left empty in the first place. 58% of the kept pairs share
distinctive phraseology *without* being a textual parallel, which is exactly the population
the edge exists to make findable.

---

## 9. Formula nesting — GAP-FORMULA-003, closed

`proofs/formula_nesting_contract.json`. The closure test asks that every formula either have
no strict-substring relation or carry an explicit nesting type. One contract, applied once,
over all 4,825:

| `nesting_type` | formulas |
|---|--:|
| `INDEPENDENT` | 2,788 |
| `CONTAINS_ANOTHER` | 934 |
| `NESTED_IN_ANOTHER` | 918 |
| `NESTED_AND_CONTAINING` | 185 |
| **total** | **4,825** |

`2,788 + 934 + 918 + 185 = 4,825`; none is untyped. Measured on the **collapsed identity
surface** — the surface `formula_id` is derived from and the surface `formulas.py`'s own
maximality rule tests — 1,593 containment pairs, 1,103 formulas strictly contained in another,
1,119 strictly containing another, 2,037 in a relation. Every one of those reproduces
`GRAPH_ENRICHMENT_V1` §M2 and `FORMULA_FAMILY_RECONSTRUCTION_V3` §1 exactly, and the count of
distinct collapsed identities is 4,825 of 4,825, so no two formulas collapse together.

Each row also carries `contains_formula_ids`, `contained_in_formula_ids` and its `family_id`,
so a frequency ranking can state which nesting policy it applies rather than leaving three
readings available. **Nothing is deleted**: the nesting type records the relation, it does not
decide whether a nested formula should exist.

---

## 10. Short high-frequency phrases and formulaic boilerplate

`proofs/boilerplate_and_short_phrase_test.json`.

**Did short phrases merge anything here? No.** The identity layer is exact string equality,
which cannot over-merge. The near-parallel layer's shortest accepted pair has 20 characters on
its shorter side, median 91, and its six weakest pairs were read by hand (§6.2).

**The boilerplate rule, enumerated not hand-written.** Exactly 9 tokens exceed
`MAX_FORMULA_CORPUS_SHARE = 0.08` per-Veda document frequency: `ā na te tvā ca no indra pra
sa`. A two-word formula half of which is a closed-class token above that line:

| measure | count |
|---|--:|
| formulas | 59 |
| `USES_FORMULA` rows | 296 |
| of those making a cross-Veda claim | 50 |
| the same rule including `indra` | 97 |

`indra` is excluded and the exclusion is stated: it is the one *content* word above the line
and its pairs are attested vocative formulae (`maghavann indra`, `indra girvaṇaḥ`), not a word
plus its grammar. This reproduces `FORMULA_FAMILY_RECONSTRUCTION_V3` §4.5 to the row. It is a
**recommendation list with per-row evidence, not a deletion** — `formula_nesting.jsonl` carries
all 4,825 and flags these 59. False positives are present inside it and are not hidden:
`pra maṃhiṣṭhāya` is genuinely from `pra maṃhiṣṭhāya gāyata`.

---

## 11. Thresholds and what they cost in recall

`proofs/threshold_recall_cost.json`.

| threshold | value | recall cost | enumerable? |
|---|---|---|---|
| `MIN_COMPARABLE_LENGTH` | 20 chars | 115 mantras excluded (AV 114, SV 1); **exactly 6 identity pairs lost** | yes — all 6 staged |
| `NEAR_PARALLEL_FLOOR` | 0.72 | 1,101 within-recension pairs | yes — all written out |
| `MAX_NEAR_PARALLELS_PER_MANTRA` | 5, both-sided | 562 pairs that cleared the floor | yes — all written out |
| `MIN_FORMULA_WORDS` | 2 | 0 emitted formulas have both tokens ≤ 5 folded chars | yes |
| `MIN_FORMULA_CHARS` | 12 | no emitted formula sits at the floor (min 13) | yes |
| `MIN_FORMULA_OCCURRENCES` | 3 | **an upper bound only — see below** | no |
| n-gram / length bounds | 0.44 | **none** — provably lossless | n/a |

The lossless prunes are counted separately from real floor rejections so the distinction stays
visible: since `similarity = 0.5·ngram + 0.5·lcs` with both terms bounded by 1, a pair below
`(0.72 − 0.5)/0.5 = 0.44` on either term cannot reach the floor however perfect the other.

### 11.1 The six pairs the length floor hides, named

All six are staged in `relations.jsonl` with `importable: false` and a reason:

```
AVS 5.9.1  == AVS 5.9.5    divesvāhā          9 chars
AVS 5.9.2  == AVS 5.9.6    pṛthivyaisvāhā    14
AVS 5.9.3  == AVS 5.9.4    antarikṣāyasvāhā  16
AVS 15.15.1 == AVS 15.18.1 tasyavrātyasya    14
```

The identity is exact and the claim is weak: a nine-character ritual exclamation recurring is
not evidence of a textual parallel. Staged and flagged rather than either imported or silently
dropped, so the floor's cost is a list and not a percentage.

### 11.2 `MIN_FORMULA_OCCURRENCES = 3` — measured, and still not decided

`FORMULA_FAMILY_RECONSTRUCTION_V3` §8 named lowering this floor to 2 as its highest-value
follow-up. Measured here:

| measure | count |
|---|--:|
| mined spans with word-aligned document frequency **exactly 2** | 109,118 |
| of those, clearing `MIN_FORMULA_CHARS` | 94,452 |
| distinct collapsed forms among them | 93,501 |
| of those, spanning two or more Vedas | 66,086 |

**This is an upper bound and is labelled one.** These are raw spans with no maximality pass,
so one long repetition contributes all of its sub-spans, and the longest of them are 70–85
characters — whole pādas and verses the parallel layer already holds as parallels:

```
ghṛtavatī bhuvanānām abhiśriyorvī pṛthvī madhudughe supeśasā dyāvāpṛthivī varuṇasya dharmaṇā
```

So the honest statement is narrower than "lowering the floor would surface 66,086 cross-Veda
formulae": it is that lowering the floor would emit tens of thousands of spans dominated by
verse-length repetition that is already recorded elsewhere, and deciding needs a maximality
pass this run did not make. The V3 report's specific case — RV 1.1.1's three Samavedic spans —
remains real and remains excluded.

---

## 12. `match_level` — the fact was never missing

`proofs/uses_formula_match_level_backfill.json`. `USES_FORMULA` is blank on 22,686 of 22,686
edges. All 22,686 are recoverable from each occurrence row's **own evidence surface**, not
re-derived and not guessed:

| `match_level` | rows | detection method |
|---|--:|---|
| `SCRIPT_FOLDED` | 20,577 | `formula-occurrence-word-aligned-v1` |
| `SANDHI_INSENSITIVE` | 2,109 | `formula-occurrence-sandhi-substring-v1` |

This is a projection defect, not a derivation one. The weaker level now says what it means:
2,109 occurrences prove the letters are in that order, not that the edition divides its words
there.

**GAP-FORMULA-002's closure test cannot be met as written and should be amended.** It requires
"no edge has a blank `match_level`". The 3,049 `NEAR_PARALLEL_OF` edges are blank **by design**
— a near parallel is identical at no level, and naming the surface it was *scored* on reads as
an identity claim. `crossveda` records that leaving it populated once inflated an identity
tally from 2,042 to 5,432. Satisfying that clause for those edges would mean making a false
claim.

### 12.1 GAP-CROSS_VEDA-003 is a name collision, not an absence

The 256 `EXACT_PARALLEL_OF` edges with no `parallel_id` are the *same* 256 with a null
`match_level`. They are not missing the fact. They carry `strongest_method = SOURCE_EXACT`
(252) or `LEMMA_SEQUENCE_EXACT` (4) and a `methods` array, written by the RV lexical layer
under a different property name than the enrichment layer's `match_level`. One axis, two
names. A backfill should therefore **map `ParallelMethod` onto `MatchLevel`, not re-derive**;
`relations.jsonl` supplies the `MatchLevel` value for 252 of the 256, and the other 4 rest on
a lemma-sequence criterion no surface ladder can reach — correct edges this run cannot
corroborate, not misses.

---

## 13. Coverage, before and after

**Formula membership does not move, and that is the finding**, not a shortfall:

| Veda | `USES_FORMULA` mantras | reaching a `FormulaFamily` |
|---|---|---|
| RV | 5,103 (48.4%) — unchanged | 2,206 (20.9%) |
| SV | 1,311 (71.1%) — unchanged | 637 (34.5%) |
| YV | 1,214 (61.5%) — unchanged | 672 (34.0%) |
| AV | 2,946 (50.5%) — unchanged | 1,428 (24.5%) |

720 families over 2,037 of 4,825 formulas, unchanged. What this artifact adds to the formula
layer is a nesting type on all 4,825, a `match_level` on all 22,686 occurrence edges, a
`family_id` surface on all 720 families, and 6,148 selective sharing edges — not new members.

**Parallel and reuse coverage does move**, and almost all of it is the Atharvaveda:

| Veda | before | after, if imported | delta |
|---|--:|--:|--:|
| RV | 2,850 (27.0%) | 2,866 (27.2%) | +16 |
| SV | 1,677 (90.9%) | 1,692 (91.8%) | +15 |
| YV | 687 (34.8%) | 774 (39.2%) | **+87** |
| AV | 1,332 (22.8%) | 1,871 (32.0%) | **+539** |

Mantras gaining a `SHARES_FORMULA_WITH` edge: RV 1,762, AV 1,275, SV 808, YV 646.

### 13.1 The artifact

```
data/staging/formula/
  manifest.json                      accepted 5,636 + rejected 14,574 = 20,210 considered
  rows.jsonl                    5,636  one row per MANTRA that gains something
  relations.jsonl               6,135  1,252 new · 4,368 typology backfill · 515 retype proposals · 6 not importable
  formula_nesting.jsonl         4,825  one row per Formula, one nesting type each
  uses_formula_match_level.jsonl 22,686
  shares_formula_with.jsonl     6,148
  formula_families.jsonl          720  family_id surface
  rejected.jsonl               14,574  one row per mantra with no delta, each with its own reason
  rejected_pairs.jsonl          1,663  every floor rejection and every cap drop, with its similarity
  proofs/                          12  the tests above
```

Accounting closes on both axes. Per mantra: 5,636 + 14,574 + 0 unresolved = 20,210 — the whole
corpus, because the whole corpus was read. Per candidate pair, separately, because a pair is
not a mantra and adding the two would make the arithmetic unauditable:
`667 + 13,342 + 3 + 1,101 + 1,437 = 16,550` and `1,437 = 562 + 875`.

Of the 14,574 rejected mantras, 14,473 are a **verified zero over an assessed population** —
identical to no other mantra, reaching no pair at the floor — and 101 are `NOT_APPLICABLE`
because the detector declined to assess them. The second is not the first, and the rows say
which.

---

## 13.5 Adversarial preflight — the ceiling was missing an axis, and 134 rows were mistyped

`proofs/adversarial_preflight_comparison_ceiling.json`. Requested by the coordinator before
Wave 3, and it found a sixth self-inflicted case.

**The assumption under test: the comparison ceiling.** Everything in §2, §3, §5 and §7 is
defined relative to it, so if it is computed wrong for one layer combination, edges move
between `EXACT_PARALLEL` and `VARIANT` wholesale. The 150-pair accent finding in §4 was a
result *about pairs*, not a test *of the function*. The function makes two claims that had
never been tested.

**Test A — is the ceiling ever too low?** Recompute it for all 2,211 identity rows and assert
`level ≥ ceiling` and that the stored label agrees. Expected 0. **Returned 0. Holds.**

**Test B — is the predicted ceiling actually reachable?** Per veda-pair, over every identity
row. Expected: reached at least once everywhere. It is — but the *rates* are the finding:

| veda pair | ceiling | reached |
|---|---|--:|
| RV-RV | `SOURCE_EXACT` | **252 / 252** |
| SV-SV | `SOURCE_EXACT` | 176 / 204 |
| AV-AV | `SOURCE_EXACT` | **26 / 137** |
| YV-YV | `SOURCE_EXACT` | **3 / 80** |

3-in-80 is not a fact about the Yajurveda. It is a fact about its text field.

**The defect.** The Atharvavedic and Yajurvedic layers **print each verse's own number inside
the stored text**, so two verses at different addresses can never be byte-identical however
identical their text. `AVS 2.32.3 ~ AVS 5.23.10` differ in exactly `'3'` → `'10'`. I had
typed 134 such pairs `VARIANT` / `EDITORIAL_APPARATUS` — a claim that two editions transmit
the verse differently, where the entire difference is the citation the row already carries in
two other fields.

This is the campaign's own pattern: an apparent difference that is our modelling.
`corpus-audit.md` §10 already records that `text_original` keeps `||18||` and `{11}` inline
*by design*. I read that and still let the numeral drive a claim.

**The third axis, derived rather than asserted.** Measured over the whole corpus by asking
whether the trailing numeral in each stored text equals that mantra's own verse number:

| Veda | self-addressing | prints its address inline |
|---|--:|:--:|
| YV | 1,964 / 1,975 (**99.44%**) | yes |
| AV | 5,513 / 5,839 (**94.42%**) | yes |
| RV | 58 / 10,552 (0.55%) | no |
| SV | 17 / 1,844 (0.92%) | no |

The Rigvedic 643 texts containing any digit are GRETIL's in-word pluti marks (`nya3trinam`),
not addresses — which is why RV-RV reaches `SOURCE_EXACT` 252/252 and is the control.

> **ceiling** = `SCRIPT_FOLDED` if the scripts differ; else `ACCENT_INSENSITIVE` if the
> accent-notation classes differ; else `PUNCTUATION_NORMALIZED` if both layers print their
> address inline **and** the pair's entire `UNICODE_NORMALIZED` difference is digits; else
> `SOURCE_EXACT`.

**And the probe itself had three bugs, each caught by an assertion rather than by reading:**

1. The first digit-only test **ignored whitespace**, which admitted 12 `WORD_DIVISION` pairs
   whose real difference is a space. Whitespace *is* word division. Strict: 139, not 151.
2. My first difference class **lumped digits with dandas**, which would have moved 18
   Samavedic rows containing no digit at all — they differ in ASCII `|` against Devanagari
   `।` (9) or an inserted space (9). Genuine apparatus; they stay `VARIANT`. (That the
   Samavedic source encodes the verse break two ways is itself a small new finding.)
3. The 6 sub-threshold *svāhā* rows carried an **asserted** `match_level` of `SOURCE_EXACT`
   that I hard-coded in the builder instead of measuring. **5 of 6 were wrong** and are
   `PUNCTUATION_NORMALIZED`.

**What moved.** 134 rows `VARIANT` → `EXACT_PARALLEL`; 24 correctly left as
`EDITORIAL_APPARATUS` (6 are address *plus* a real mark, 18 are Samavedic apparatus with no
numeral); 5 sub-threshold match levels corrected.

| claim | before | after |
|---|--:|--:|
| EXACT_PARALLEL | 736 | **870** (279 cross, 591 within) |
| VARIANT | 1,475 | **1,341** (1,259 cross, 82 within) |
| NEAR_PARALLEL | 3,924 | 3,924 |

**What did not move**, and the confinement is the reason the fix is safe: every
cross-recension figure (a cross ceiling is `ACCENT_INSENSITIVE` or `SCRIPT_FOLDED`, both
below `PUNCTUATION_NORMALIZED`, so an inline address cannot bind it), all 875 within-recension
near parallels, the 967 within-recension identical mantras, the 415 new identity pairs, the 23
accent variants, the 475 orthographic and 819 word-division variants, the 4,825 nesting types,
the 6,148 sharing edges, the 22,686 `match_level` backfills, and every per-Veda coverage
figure in §13. The blast radius was asserted before anything was touched, and the assertion
is what caught bugs 1 and 3.

**Invariants after the fix**, all re-run: 0 rows identical above their ceiling; 0
`EXACT_PARALLEL` rows not exactly *at* their ceiling; 0 of 23 `ACCENT_PLACEMENT` rows whose
difference is anything but a tone mark.

**Verdict: the assumption partly failed and is now fixed.** The function was right on the two
axes it modelled and blind to a third. Test A held outright; Test B held on reachability and
its *rates* are what exposed the missing axis — which is the argument for testing a function
rather than re-reading its outputs.

*On the coordinator's correction:* the 0.8413 all-Veda mispaired maximum is cited nowhere in
this domain and `vedsearch.similarity()` was not used. The blend here is `crossveda`'s own
`0.5·char4gram_jaccard + 0.5·lcs_ratio`, and its 0.72 floor was re-measured on this domain's
own within-recension population (§6.1).

---

### 13.6 The gate resolves `rows.jsonl`; these files resolve the rest

`proofs/sidecar_keys_resolve_against_the_live_store.json`. Commit `c39a34f` widened the
staging gate to an `ENTITY` grain because two agents had moved their real output into a
sidecar and filled `rows.jsonl` with passage-grained proxies, and the gate then reported full
coverage over rows that were not the domain's subject. That grain matches on `entity_key`.
Measured: `:Formula` has **0 of 4,825** nodes with an `entity_key` and `:FormulaFamily` **0 of
720** — their identities are `formula_id` and `family_id` — so neither the `PASSAGE` grain nor
the new `ENTITY` grain can resolve this domain's sidecar subjects.

`rows.jsonl` here is genuinely passage-grained and is not a proxy: it reports per-mantra
formula and parallel state, which is a real subject. A *pair* cannot be a `rows.jsonl` row at
all, because `row.no_duplicate_key_source` forbids two rows sharing a `canonical_key`. So
rather than let the sidecars pass unchecked behind a clean per-mantra result, every sidecar key
is resolved against the live store here:

| file | key | resolves |
|---|---|--:|
| `formula_nesting.jsonl` | `formula_id` → `:Formula` | 4,825 / 4,825 |
| `formula_nesting.jsonl` | `family_id` → `:FormulaFamily` | 720 / 720 |
| `formula_families.jsonl` | `family_id` → `:FormulaFamily` | 720 / 720 |
| `relations.jsonl` | subject + object → `:Passage` | 7,213 / 7,213 |
| `uses_formula_match_level.jsonl` | `passage_key` → `:Passage` | 10,574 / 10,574 |
| `uses_formula_match_level.jsonl` | `formula_id` → `:Formula` | 4,825 / 4,825 |
| `shares_formula_with.jsonl` | `a` + `b` → `:Passage` | 4,491 / 4,491 |
| `shares_formula_with.jsonl` | `shared_formula_ids` → `:Formula` | 3,663 / 3,663 |
| `uses_formula_match_level.jsonl` | every row targets a **live** `USES_FORMULA` edge | 22,686 / 22,686 |

Zero unresolved. The last row is the one that matters most: a `match_level` backfill that named
a `(passage, formula)` pair with no edge behind it would be a write with nowhere to land, and
that is the failure `load_enrichment_neo4j.py` exists to catch after the fact.

---

## 14. Nine defects in my own work, and what each would have shipped

Recorded because each was found by a check rather than by inspection, and three of them would
have shipped a confident wrong number.

1. **The comparison ceiling was missing a third axis** — 134 within-recension pairs whose
   entire difference is their own printed verse number were typed `VARIANT`. §13.5.
2. **The first digit-only probe ignored whitespace**, which would have moved 12
   `WORD_DIVISION` pairs whose real difference is a space.
3. **The first difference class lumped digits with dandas**, which would have moved 18
   Samavedic rows containing no digit at all.
4. **1,475 `VARIANT` rows quoted the surface on which the two texts *agree* and nothing on
   which they differ** — a variant claim proving its own negation. Every one now carries
   `difference_spans` with the differing codepoints named, computed on the surface the pair
   *fails* at, plus both quotes at that surface. 0 `VARIANT` rows lack one.
5. **`claim_confidence` read `NOT_APPLICABLE` on 4,103 rows** whose only delta is a
   `SHARES_FORMULA_WITH` edge — "this row makes no claim", about a row that makes one.
   Corrected; 0 staged rows now say `NOT_APPLICABLE`.
6. **The first transformation typology special-cased accent notation instead of deriving a
   ceiling**, which labelled 129 cross-*script* identities `ACCENT_NOTATION_INCOMPARABLE` —
   a statement about accent for pairs whose difference is script. Rebuilt around the ceiling.
7. **The first false-duplicate test compared `structural_path`, which is null for the
   Rigveda**, so all 252 RV pairs returned `SAME_ADDRESS_INGESTION_DUPLICATE` while the
   printed examples showed different maṇḍalas. A null-equals-null comparison is not a match.
8. **The first floor calibration read the random-pair maximum as a null maximum** and
   concluded the imported 0.72 floor was unsafe. Reading the tail showed the sample was
   contaminated by real signal. Had the number been accepted, a threshold would have been
   invented to fit it.

9. **The 6 sub-threshold *svāhā* rows carried a hard-coded `match_level`** of `SOURCE_EXACT`
   that I asserted in the builder instead of measuring. **5 of the 6 were wrong** and are
   `PUNCTUATION_NORMALIZED`. Caught by the same blast-radius assertion as 2 and 3.

Three of these nine were found only because the coordinator mandated an adversarial preflight,
and three more only because that fix was written with an assertion in front of it rather than
applied directly. The pattern is that reading rows found the cosmetic ones and asserting an
invariant found the substantive ones.

`proofs/report_figure_check.json` re-checks all 52 load-bearing figures in this document
against the artifacts they describe, because every table here reads from a file and a number
typed into a sentence is the only one nothing else can catch. 44 checks, 0 failures.

## 15. What this does not do

- **No canonical write.** Read-only Cypher throughout.
- **No word-order merge.** Containment cannot relate `daivyā hotārā` to `hotārā daivyā`, and
  reordering plus inflection keeps `viśvā bhuvanā` and `bhuvanāni viśvā` in two families.
  2 groups / 4 families, measured exactly by V3 §5.2, unfixed here.
- **No pada-level detection.** `GAP-CROSS_VEDA-004` untouched. It needs the RV-only pada tags
  and would produce a corpus-wide-looking layer covering one corpus.
- **No Samavedic cross-script improvement.** SV membership against the Latin corpora still
  bottoms out at `SANDHI_INSENSITIVE` because Devanagari and Latin share no code points. That
  is `GAP-MORPHOLOGY-005`'s dependency.
- **No human review.** Every adjudication above is model adjudication, which campaign §26
  forbids calling gold. Each adjudicated set is small enough to be re-read by hand and is
  printed verbatim in `proofs/`.
- **No retype applied.** The 515 recommendations carry their evidence and wait on the lead.

## 16. For the lead, in the order it matters

1. **Import the 415 within-recension identities and 831 near parallels** if the Samaveda,
   Yajurveda and Atharvaveda are to have a within-recension parallel layer at all. They are
   the cleanest thing here: exact string equality, 0 false duplicates, every pair joining two
   distinct printed addresses.
2. **Rule on the 470 AV-RV retypes.** They decide whether `EXACT_PARALLEL_OF` means "identical
   at the ceiling" or "identical above word division". Both are defensible; only one can be
   true of the graph.
3. **Backfill `match_level` by mapping, not re-deriving** — on `USES_FORMULA` from the
   occurrence evidence surface, and on the 256 RV edges from `strongest_method`.
4. **Amend GAP-FORMULA-002's closure test.** "No edge has a blank `match_level`" cannot hold
   for `NEAR_PARALLEL_OF` without asserting an identity that does not exist.
5. **Correct two committed figures**: CORPUS_D11's 587 (byte identity; the ladder finds 967),
   and the Samavedic "Āraṇya-versus-Uttarārcika" characterisation (it is Chandas-ārcika versus
   Uttarārcika, 191 of 204).
6. **Correct `predicates.py`'s 87,296**, or rather its reading: that is an incidence count,
   and the edge count is 53,167.
