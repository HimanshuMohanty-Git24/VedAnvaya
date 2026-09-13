# Graph Enrichment V1 — Adversarial QA

**Agent G. Adversarial review of `data/enrichment/vedagraph_enrichment_v1/` and the live
graph at `bolt://localhost:7687`.** The brief was to find what is wrong, not to confirm that
it works. Everything below is measured; where an attack found nothing, the number that shows
it is given rather than an impression.

All scratch scripts ran read-only. No `src/`, `tests/` or artifact file was modified.

---

## Summary

**What survived, with the numbers.**

| Layer | Attack | Result |
|---|---|---|
| Cross-Veda near parallels | 60 pairs hand-read across three score bands | **60/60 true positives.** 0 false positives at the 0.72 floor. |
| Cross-Veda near parallels | refrain-collision test over all 3,049 rows | **0 refrain collisions.** Worst-case pair is still a real parallel. |
| EXACT / VARIANT | exhaustive re-verification of all 1,538 identity claims | **1,538/1,538 hold.** 0 defects. |
| Determinism | full pipeline re-run, byte-level digest comparison | **All 5 artifacts bit-reproducible.** |
| Guards | every cap and floor re-checked against the artifacts | **All bind exactly.** 0 violations. |
| Projection | rows-sent vs rows-landed for all three edge families | **0 missing, 0 extra** across 76,711 edges. |
| Base graph | Passage / Translation / QAIssue counts, duplicate keys | **All correct.** 0 duplicate `canonical_key`. |
| Concept precision | independent random n=60, stratified by evidence path | **97.8% loose / 97.7% strict** (path-weighted). |

**What broke.** Six findings at SERIOUS or above. The most important is not a wrong claim — it
is that **the evidence a reader will see is corrupted**, on 88.6% of parallel edges and 32.0%
of concept edges, by private-use comparison sentinels that leaked out of the normalisation
layer and are now live in Neo4j. The second most important is methodological: the concept
layer's errors are **structured, not random**, so the random-sample precision number above
(and Agent D's) is real but nearly blind to them — a targeted alias audit found one alias that
is wrong 96.7% of the time.

---

## Attack 1 — Cross-Veda false positives

### Method

```
NEAR_PARALLEL_OF rows: 3,049.  Bands: lo = score < 0.78 (231 rows),
mid = 0.85 <= score < 0.90 (593 rows), hi = score >= 0.95 (612 rows).
random.seed(20260909); random.sample(band, 20) for each band.
For each pair, both mantras were read in full: stored source, script-folded
surface (sentinels rendered back to IAST), and Griffith/Whitney translation
where one exists.
```

### Measured result

| Band | n | genuine parallels | refrain / formula collisions | measured FP rate |
|---|---|---|---|---|
| 0.721 – 0.78 | 20 | 20 | 0 | **0%** |
| 0.85 – 0.90 | 20 | 20 | 0 | **0%** |
| ≥ 0.95 | 20 | 20 | 0 | **0%** |

**Zero false positives in 60.** I expected the floor band to be the weak point and it is not.
Representative floor-band rows, all correct:

- `AVS 5.3.10` / `VSM 34.46`, score 0.7376, token Jaccard **0.280** — the low token overlap is
  entirely Devanagari-vs-Latin word division. Both read *ye naḥ sapatnā apa te bhavantu
  indrāgnibhyām ava bādhāmahe …* The AV has *ādityā rudrā* where the VS has *vasavo rudrā
  ādityā*: a real variant reading, not a collision.
- `AVS 7.53.7` / `VSM 27.10`, score 0.7309, token Jaccard **0.105** — *ud vayaṃ tamasas pari …
  devaṃ devatrā sūryam aganma jyotir uttamam*. The pada that differs (`nākam uttamam` vs
  `svaḥ paśyanta uttaram`) is exactly why this is NEAR and not EXACT.
- `RV 8.44.12` / `SV UTTARA 8.3.1.1`, score 0.7402 — *agniḥ pratnena **manmanā*** vs *agniḥ
  pratnena **janmanā***. One word substituted. Textbook near parallel.

### The RV↔SV sandhi worry, tested directly

The brief's specific concern was that SV continuous-sandhi writing makes character n-grams
agree for the wrong reason. It does not, because the scoring is LCS-dominated, not n-gram
dominated: across all 3,049 NEAR rows the **minimum `lcs_ratio` is 0.737 and the median is
0.96**, while `token_jaccard` runs as low as 0.105. A pair reaches the floor by having the same
letters in the same order over most of the verse, which sandhi rewriting does not manufacture.
In the low band, 98 of 231 rows are RV-SV and all 4 RV-SV rows I drew were correct.

### Refrain-collision test (exhaustive, all 3,049 rows)

A refrain collision has a characteristic signature: high LCS *subsequence* (the refrain plus
scattered case endings) but a short longest common *substring*. I computed the longest common
substring on the sandhi surface for every NEAR pair, as a fraction of the shorter verse.

```
min 0.193 | p05 0.349 | p25 0.519 | median 0.639 | max 1.000
pairs below 0.25: 9    below 0.40: 301    below 0.50: 658
```

I read all 12 of the lowest-fraction pairs. **All 12 are genuine parallels.** The low fraction
is caused by word-division differences chopping the run, not by a shared refrain. The single
worst case, `AVS 14.1.46` / `RV 10.40.10` at 0.19, is:

```
A  jīvaṃ rudanti vi nayanty  adhvaraṃ dīrghām anu prasitiṃ dīdhyur  naraḥ vāmaṃ pitṛbhyo …
B  jīvaṃ rudanti vi mayante  adhvare  dīrghām anu prasitiṃ dīdhiyur naraḥ vāmam pitṛbhyo …
```

That is the same verse with four variant readings. **0 of 3,049 near parallels are refrain
collisions.** The Formula layer is not being asked to do the parallel layer's job anywhere I
can find.

---

## Attack 2 — Are EXACT and VARIANT really exact?

### Method

Not a sample — **all 1,538 identity rows**, re-derived from the corpus. For each
`EXACT_PARALLEL_OF` row, recompute both endpoints' surface at the row's claimed `match_level`
and require byte equality. For each `VARIANT_OF` row, require equality on the
sandhi-insensitive surface **and** inequality on the script-folded surface (otherwise it should
have been EXACT).

### Measured result

| Claim | n | violations |
|---|---|---|
| EXACT identical on its claimed `match_level` | 750 | **0** |
| VARIANT identical on the sandhi surface | 788 | **0** |
| VARIANT that is *also* identical script-folded (mis-classified) | 788 | **0** |
| VARIANT that is only a re-spacing of an identical token multiset | 788 | **0** |
| identity rows with `similarity < 1.0` | 1,538 | **0** |
| self-loops, reciprocal duplicates, duplicate `parallel_id` | 6,271 | **0** |

Level split: EXACT = 600 `SCRIPT_FOLDED` + 150 `ACCENT_INSENSITIVE`; VARIANT = 788
`SANDHI_INSENSITIVE`. Clean.

### Second-order attack: is the identity manufactured by a lossy fold?

621 EXACT pairs are same-script (AV↔RV, both Latin), and 471 of those are identical only at
`SCRIPT_FOLDED`, i.e. the fold created the identity. I diffed the accent-stripped surfaces of
all 471 to see exactly which distinctions the fold erased:

```
('ṃ','ṁ')  762    ('r̥','ṛ')  488    ('','c')  27    ('ṃ','m̐')  6
('ṝ','r̥̄')   4    ('r̥ṃ','ṛṁ') 1    ('r̥','ṛc') 1    ('ृ','्ऋ') 1
```

Every one is a transcription-convention difference between GRETIL and the AV artifact
(anusvāra spelling, vocalic *r* spelling, GRETIL's geminated `cch`). **No pair is made identical
by the lateral fold**, which is the one genuinely dangerous collapse documented in
`normalize/unicode.py`. The EXACT claim is sound.

The shortest identity pairs — the ones most at risk of being a short refrain shared by accident
— are also fine: the shortest is 40 characters (`RV 9.67.16` / `SV UTTARA 9.1.17.1`, *pavasva
soma mandayann indrāya madhumattamaḥ*), a complete and genuinely shared verse.

### But `match_level` is wrong on the *other* 4,229 rows — see Finding S1.

---

## Attack 3 — Concept assertion precision, re-measured independently

### Method

```
random.seed(31415).  Stratified by evidence path (the `method` suffix):
  sanskrit-sandhi          15   (over-sampled: 473 rows exist, all SV — prime suspect)
  sanskrit-token           15
  english                  20
  english+sanskrit-token   10
                        n = 60
For each: read the concept definition and full alias list, the evidence span,
the full script-folded Sanskrit, and the full translation.
```

Two verdicts recorded per row. **Loose** = the concept genuinely applies to the passage.
**Strict** = the cited evidence span is the intended word in the intended sense.

### Measured result — my number

| Path | population | n | loose | strict |
|---|---|---|---|---|
| `sanskrit-token` | 12,758 (26.7%) | 15 | 15/15 | 15/15 |
| `sanskrit-sandhi` | 473 (1.0%) | 15 | 15/15 | **14/15** |
| `english` | 21,458 (44.9%) | 20 | **19/20** | **19/20** |
| `english+sanskrit-token` | 13,065 (27.4%) | 10 | 10/10 | 10/10 |
| **sample total** | 47,754 | **60** | **59/60 = 98.3%** | **58/60 = 96.7%** |
| **population-weighted** | | | **97.8%** | **97.7%** |

My loose number **reproduces Agent D's** (97.5%). My strict number is *higher* than Agent D's
87.5%, on a larger and independently drawn sample. I do not think that means the layer is
better than Agent D said. I think it means **random sampling is the wrong instrument for this
layer**, and the section after next shows why.

The two sample failures:

**FP-1 (loose and strict).** `RV 3.55.1` → `VG:CONCEPT:GRHA-HOUSE`, confidence 0.42, sole
evidence the English word `home`. Griffith: *"in the Cow's home was born the Great Eternal"*.
The Sanskrit is `pade goḥ` — "in the footstep/place of the cow". There is no dwelling in this
verse; the passage is about the first dawns and the great syllable. The concept is simply wrong.

**FP-2 (strict only).** `SV CHANDA 1.4.1` → `VG:CONCEPT:YAJNA-SACRIFICE` via the sandhi path,
matched alias `yajñāya`. The verse is `yajñāyajñā vo agnaye girāgirā ca dakṣase` — the
reduplicated *yajñā-yajñā* ("at sacrifice after sacrifice"). The substring `yajñāya` is found
**straddling the two words**: `yajñā` + `ya`(jñā). The concept is right; the alias the
provenance names is not in the text. This is exactly the failure mode the brief predicted for
the SV sandhi substring path. **1 of 15 = 6.7%** of that path in my sample.

### The sandhi path is much better than expected

The prime suspect turned out to be the strongest per-row layer I audited. 15/15 loose. The
mitigations in `concepts.py` (`MIN_SANDHI_ALIAS_CHARS = 6`, plus the 13-entry
`SANDHI_SUPPRESSED_ALIASES` table compiled by scanning the Samaveda's own vocabulary) are doing
real work: every match I read was either a whole word (`gobhir`, `ratha`, `hotāram`,
`samudram`, `barhiṣaḥ`) or a genuine compound member (`somapītaye`, `brahmayujā`,
`madhumattamaḥ`, `dakṣiṇāvate`). The path is also only **473 of 47,754 assertions (1.0%)**, so
even at 6.7% strict error it contributes ~32 bad spans.

### The attack that actually worked: audit the alias, not the row

The concept layer's errors are not spread evenly across 47,754 rows. They are concentrated in a
handful of the 254 English aliases, where the alias translates a *different Sanskrit word* than
the concept intends. I enumerated all 254, flagged the polysemous ones, and audited each
flagged alias's whole population.

**`realm` → `VG:CONCEPT:RAJAN-KINGSHIP` — audited exhaustively, all 35 assertions.**

Griffith uses "realm" almost exclusively for *rajas* (region, space), not for *rājan*.

```
RV 10.129.1  "there was no realm of air, no sky beyond it"        -> KINGSHIP
RV  9.37.3   "runs forth to the luminous realm of heaven"         -> KINGSHIP
RV  1.50.4   "Illuming all the radiant realm"                     -> KINGSHIP
RV  9.63.8   "To travel through the realm of air"                 -> KINGSHIP
AVS 18.4.31  "do thou go about in Yama's realm"                   -> KINGSHIP
```

| | count |
|---|---|
| total `realm` assertions | 35 |
| of those, correct (kingship really asserted) | 6 — and 5 of the 6 are rescued by a *different* alias firing (`rājā`, `rāṣṭram`, `kings`) |
| **wrong** | **29 / 35 = 82.9%** |
| where `realm` is the *sole* evidence | 30 |
| **wrong among sole-evidence rows** | **29 / 30 = 96.7%** |

The only sole-evidence `realm` row that is right is `RV 5.66.6`, *"the realm ye rule"*.

**`stone` → `VG:CONCEPT:ASMAN-PRESSING-STONE` — n=20 random of 73.** 7/20 are the soma press.
13/20 are an ordinary rock (`AVS 12.1.26` *"Rock is earth, stone, dust"*; `RV 1.191.15` *"I
crush the creature with a stone"*; `AVS 1.2.2` *"make thyself a stone"*) or Griffith's *"Caster
of the Stone"* for the vajra (`RV 1.80.7`, `RV 5.38.3`, `RV 5.54.3`, `RV 7.104.19`). **~62%
mis-sensed.** Mitigating: the concept's own definition says *"and stone generally as the hard
thing a god splits"*, so these are inside the written definition — but the label a reader sees
is "pressing stone", and 267 assertions carry it.

Plural `stones` is much better: 17/20 correct (`grāvāṇaḥ`/`adribhiḥ` corroborate most of them).

**`bow` → `AYUDHA-WEAPON` (67) and `way`/`ways` → `ADHVAN-PATH` (298).** ~21% mis-sensed each,
n=14 each. `bow` catches the verb (`VSM 12.35` *"To him bow down the nobly-wedded Matrons"*;
`RV 2.12.13` *"Even the Heaven and Earth bow down"*). `way` catches the adverbial (`AVS 14.1.27`
*"glistening in that evil way"*; `AVS 6.77.3` *"thy turners this way a thousand"*).

**Aliases I suspected and cleared.** `might` (588 assertions) — I expected the English modal
verb and found **0 in 14**; Griffith's register uses it only as a noun. `light` (531) — 14/14
the noun. `word`/`words` (88) — 14/14 correct. `born`, `golden`, `liberal`, `pressed`, `grass`,
`field` — no systematic problem visible.

**Sizing.** Summing the sole-evidence populations of the four demonstrably mis-sensed aliases
against their measured error rates gives roughly **128 wrong assertions out of 47,754 (0.27%)**.
Small in aggregate. But it is 96.7% inside the `realm` slice, and *no* random sample of 40 or 60
rows can see that — the expected number of `realm` rows in a 60-row draw is 0.04.

**One base-corpus defect leaking through.** `RV 9.86.32`'s stored Griffith translation reads
*"spinning, as he knows **bow**, the triply-twisted thread"* — an OCR error for "as he knows
how". That single character produces an `AYUDHA-WEAPON` assertion on a Soma Pavamāna verse. This
is a corpus data defect, not an enrichment defect, but the enrichment layer has no defence
against it.

---

## Attack 4 — Formula quality

### Are any "formulas" grammatical noise?

Largely no, and the top of the list is genuinely impressive — these are the phrases a Vedicist
would name:

```
93x  pāta svastibhiḥ sadā naḥ          RV SV YV AV
82x  yūyam pāta svastibhiḥ sadā naḥ    RV
54x  bhavati ya evaṃ veda              AV
53x  parame vyoman                     RV SV YV AV
46x  nabhantām anyake                  RV SV AV
38x  brahmaṇas pate                    RV SV YV AV
33x  sa janāsa indra(ḥ)                RV AV
```

Measured noise signals over all 4,825:

| signal | count | share |
|---|---|---|
| ends on a bare preverb (`… vi`, `… abhi`, `… pra`) | 146 | 3.03% |
| ends on a bare particle (`… ca`, `… yad`, `… na`) | 103 | 2.13% |
| union | 249 | **5.16%** |
| 2-word formulas (the shortest admitted) | 2,038 | 42.2% |

The 5.16% ending on a preverb or particle are window cuts, not formulas — `antarikṣaṃ vi`,
`bṛhaspatiḥ saṃ`, `vājasātaye vi`, `payasvān agna ā`. They carry 1,016 `USES_FORMULA` edges.
Among the 2-word formulas most are real collocations, but a visible minority are clause
fragments (`pūyamānaḥ abhi`, `oṣadhayaḥ pra`, `dadhat stotre`).

### Is `display_form` ever malformed?

Yes, and I measured the whole class the brief pointed at rather than just `gne`. Method: for
every mantra, collect every letter-run following an avagraha in the source, fold it, and keep
those that essentially never occur as a standalone word (618 of 901 fragments). Then check every
formula's `display_form` tokens against that set.

**34 of 4,825 formulas (0.70%) display a truncated non-word, carrying 429 of 22,686 occurrence
edges (1.89%).**

```
 67x  yo smān dveṣṭi                                   should be  yo 'smān …
 65x  yo smān dveṣṭi yaṃ
 51x  yo smān dveṣṭi yaṃ vayaṃ
 45x  yo smān dveṣṭi yaṃ vayaṃ dviṣmaḥ                 should be  yo 'smān dveṣṭi yaṃ vayaṃ dviṣmaḥ
 26x  mum āmuṣyāyaṇam amuṣyāḥ putram                   should be  amum …
 19x  devasya tvā savituḥ prasave śvinor bāhubhyāṃ     should be  … aśvinor bāhubhyāṃ
 18x  nehaso va ūtayaḥ suūtayo va ūtayaḥ               should be  anehaso …
 16x  rcann anu svarājyam                              should be  arcann …
  4x  no hir budhnyo                                   should be  no 'hir budhnyaḥ
  4x  jātavedo them
```

`yo 'smān dveṣṭi yaṃ vayaṃ dviṣmaḥ` is one of the most recognisable formulas in the
Yajurveda/Atharvaveda and it is displayed with a missing letter in five separate nodes. This
residual **is documented** in `formulas.py` (which quantifies `gne` at 62 mantras); what is new
here is the full measurement across all truncation sites and the occurrence-edge cost.

Also: `display_form` is **not unique** — see Finding S3.

### Does maximality keep both a formula and its superstring?

Yes, by design, and the design leaves more redundancy than the docstring implies. The rule
collapses a sub-formula only when its occurrence set is *identical* to the container's.

**1,103 of 4,825 surviving formulas (22.9%) are a strict substring of another surviving
formula.** Of those, **562 (11.6% of all formulas) add exactly one extra mantra** over their
container:

```
  6x  dūtaṁ vṛṇīmahe            <    5x  dūtaṁ vṛṇīmahe hotāraṁ
  5x  savitā bhagaḥ             <    4x  suvāti savitā bhagaḥ
  4x  namasā havirbhiḥ          <    3x  yajñair vidhema namasā havirbhiḥ
  4x  vṛṣaṇā juṣethām           <    3x  imāṁ suvṛktiṁ vṛṣaṇā juṣethām
 12x  tena tvaṃ dviṣato jahi    <   11x  bhūyobhūyaḥ śvaḥśvas tena tvaṃ dviṣato jahi
```

One extra attestation buys a whole extra hub node and its whole edge set. The `yo 'smān dveṣṭi`
family alone occupies six nodes (`vayaṃ dviṣmaḥ` 52x, `yaṃ vayaṃ dviṣmaḥ` 46x, `yo smān dveṣṭi`
67x, `… yaṃ` 65x, `… yaṃ vayaṃ` 51x, `… yaṃ vayaṃ dviṣmaḥ` 45x) for one piece of phraseology —
326 `USES_FORMULA` edges. The rule is defensible as written; the measured cost is 22.9% node
redundancy.

---

## Attack 5 — Do the guards actually bind?

I tried to find a cap that is decorative. I could not.

| Guard | value | measured in the artifact | binds? |
|---|---|---|---|
| `MAX_NEAR_PARALLELS_PER_MANTRA` | 5 | max observed **exactly 5**; 0 over | **yes, exactly** |
| `MAX_CONCEPTS_PER_PASSAGE` | 4 | max observed **exactly 4**; 0 over | **yes, exactly** |
| `MIN_FORMULA_WORDS` / `MAX` | 2 / 8 | range 2–8, 0 outside | yes |
| `MIN_FORMULA_CHARS` | 12 | min 13 | yes |
| `MIN_FORMULA_OCCURRENCES` | 3 | min `mantra_count` = 3 | yes |
| `MAX_FORMULA_CORPUS_SHARE` | 0.08 | max share **0.0167** (`vasuvane vasudheyasya`, YV 33/1975) | not binding |
| `MIN_COMPARABLE_LENGTH` | 20 | min endpoint length 34 | not binding |
| `NEAR_PARALLEL_FLOOR` | 0.72 | min score **0.721405** | yes |
| `MAX_NEAR_PARALLEL_EDGES` | 40,000 | 3,049 | headroom 13× |
| `MAX_FORMULA_NODES` / `EDGES` | 6,000 / 120,000 | 4,825 / 22,686 | headroom 1.2× / 5× |
| `MAX_CONCEPT_NODES` / `ASSERTIONS` | 150 / 60,000 | 89 / 47,754 | headroom 1.7× / 1.3× |

I also ran the shipped validator (`validate_artifacts`) against the shipped artifacts:
**passes, 0 error findings.** That is true and also the point of Finding S1 — the validator does
not check the things that are actually wrong (see "What the validator does not check").

**Can an all-pairs computation occur?** Not on this corpus. Candidate generation is MinHash LSH
with `MAX_LSH_BUCKET = 800`; the largest bucket observed is **54**, and the largest identity
bucket is **15**. Two unbounded-in-principle paths exist but neither is reachable here:
`identical_pairs` is quadratic inside a surface bucket with no cap of its own, and
`_apply_maximality` is quadratic inside an occurrence-set group (36,371 pre-maximality
candidates). Both are cost risks under a future corpus change, not correctness risks now. Worst
case admitted by the LSH cap is 32 bands × 800²/2 ≈ 10.2M pairs, which is bounded but is 570×
the 17,951 candidate pairs actually generated — so the circuit breaker is far looser than the
observed regime.

---

## Attack 6 — Provenance integrity

This is the attack the brief called the most important, so I did it **exhaustively** rather than
on 30 rows: every evidence span in every artifact, 112,522 of them, re-checked against the cited
passage's re-derived surfaces.

### Method

For each `(locator, surface, quote)`: look the passage up in a fresh `load_corpus()`, take the
surface the span names, and require the quote to be a substring. Translation spans are checked
against the passage's stored translations with whitespace collapsed (the pipeline collapses
newlines when it quotes; that is a formatting difference, not a provenance failure).

### Measured result

| Artifact | evidence spans | unresolvable locator | quote verified in the cited passage | **fails** |
|---|---|---|---|---|
| `cross_veda_parallels` | 12,542 | 0 | 12,542 (100.000%) | **0** |
| `concept_assertions` | 60,819 | 0 | 60,819 (100.000%) | **0** |
| `formulas` | 14,475 | 0 | 14,275 (98.618%) | **200** |
| `formula_occurrences` | 22,686 | 0 | 22,383 (98.664%) | **303** |

**Cross-Veda parallel and concept provenance is perfect.** Every quote is exactly the surface it
claims, at the passage it claims. No dangling locators anywhere.

**The 303 formula-occurrence failures are all one bug, and it is a real misquote.** 302 are
Yajurveda, 1 Samaveda, and 303/303 are recovered by ignoring visarga:

```
formula quote  :  abhi gotrāṇi sahasā gāhamāno dayo vīraḥ śatamanyurindra  duścyavanaḥ
VSM 17.39 reads:  abhi gotrāṇi sahasā gāhamāno dayo vīraḥ śatamanyurindraḥ duścyavanaḥ
                                                                        ^ dropped

formula quote  :  abhī ṣu ṇa  sakhīnāmavitā jaritṝṇām
VSM 27.41 reads:  abhī ṣu ṇaḥ sakhīnāmavitā jaritṝṇām
```

Root cause and full sizing in Finding S3.

### What the validator does not check

`validate.py` passes on these artifacts. It checks evidence *presence*, id uniqueness, predicate
vocabulary, referential integrity and every cap — all correctly. It does **not** check that an
evidence quote appears in the cited text, does not check for unassigned code points in any
string, does not check `match_level` against `levels_reached`, and does not check a Formula
node's `occurrence_count` against its edge count. Every SERIOUS finding in this report is in
that gap.

---

## Attack 7 — Live graph

The enrichment **is** loaded (it was not when the brief was written). Base and enrichment both
checked.

### Base layer — all correct

| check | expected | live | |
|---|---|---|---|
| `Passage` | 22,537 | **22,537** | ok |
| `Translation` | 17,283 | **17,283** | ok |
| `QAIssue` | 915 | **915** | ok |
| duplicate `canonical_key` | 0 | **0** | ok |
| nodes carrying `canonical_key` | — | 22,537 (all Passages) | ok |
| `RV 1.91.18` Griffith translations | 1 | **1** (`Ralph T. H. Griffith`) | ok |
| `RV 5.44.14` Griffith translations | 1 | **1** (`Ralph T. H. Griffith`) | ok |
| passages with >1 translation | 0 | **0** (max = 1) | ok |

### Projection fidelity — rows sent vs rows landed

Per the standing lesson that a projection must be diffed against the live store rather than
trusted:

| edge family | artifact | live | missing | extra |
|---|---|---|---|---|
| `ABOUT_CONCEPT` | 47,754 | 47,754 | **0** | **0** |
| `USES_FORMULA` | 22,686 | 22,686 | **0** | **0** |
| cross-Veda parallels (4 types, tagged) | 6,271 | 6,271 | **0** | **0** |
| `Formula` nodes | 4,825 | 4,825 | — | — |
| `Concept` nodes | 89 | 89 | — | — |

Also: 0 dangling `ABOUT_CONCEPT`/`USES_FORMULA`, 0 `Formula` with no edge, 0 `Concept` with no
edge, 0 same-Veda `NEAR_PARALLEL_OF`. **The load is clean.** The three defects that reached the
graph got there because they were in the artifacts, not because the loader lost anything.

### One collision — see Finding S2

`EXACT_PARALLEL_OF` in the live graph is **1,006 edges, not 750**.

---

## Attack 8 — Everything else

| attack | result |
|---|---|
| **Determinism** — full pipeline re-run, SHA-256 per artifact vs manifest vs disk | **all 5 bit-identical.** Reproducible. |
| Manifest digests vs actual file digests | 5/5 match |
| Manifest counts vs actual row counts | 5/5 match |
| Assertion whose `passage_key` does not exist | **0** of 47,754 |
| Occurrence edge whose `formula_id` or `passage_key` does not exist | **0** of 22,686 |
| `veda_pair` disagreeing with the two endpoints' actual Vedas | **0** of 6,271 |
| `subject_veda`/`object_veda` disagreeing with the corpus | **0** of 6,271 |
| Assertion `veda` disagreeing with the passage's Veda | **0** of 47,754 |
| `REUSES_TEXT_FROM` direction backwards | **0** — all 1,684 are SV→RV, which is correct, and the restriction to that one pair is deliberate and documented (`ESTABLISHED_REUSE`) |
| Duplicate ids (`parallel_id`, `formula_id`, `assertion_id`, `concept_id`) | **0** |
| Duplicate `(passage, concept)` / `(formula, passage)` pairs | **0** |
| `score` disagreeing with `similarity`/`confidence` | **0** |
| NEAR row with `similarity >= 1.0`, identity row with `< 1.0` | **0** / **0** |
| `notes` failing to name both citations | **0** of 6,271 |
| `trust`/`state` anomalies | **0** — uniformly `DETERMINISTIC_DERIVED` / `ACCEPTED` |
| Unicode: unassigned code points in output | **found — Finding B1** |
| Off-by-one in the per-passage cap | none; boundary is exact — but see Finding S4 for what happens *at* the boundary |

---

# Findings, severity ranked

## BLOCKER

### B1 — Private-use comparison sentinels leak into published evidence, and are live in Neo4j

`vedagraph.normalize` folds four sounds onto private-use code points so that GRETIL and VedaWeb
spellings compare equal: **U+E000** vocalic *r*, **U+E001** its long grade, **U+E002** the
lateral series, **U+E003** the anusvāra. `formulas.py` documents this hazard and renders the
sentinels back to IAST before publishing. `crossveda.py` and `concepts.py` do not.

Measured across the artifacts and confirmed in the live store:

| surface | rows containing U+E000–U+E003 | share |
|---|---|---|
| `cross_veda_parallels.jsonl` `evidence[].quote` | **5,554 / 6,271** | **88.6%** |
| `concept_assertions.jsonl` `evidence[].quote` | 15,229 / 47,754 | 31.9% |
| `concept_assertions.jsonl` `notes` | **4,657** | 9.8% |
| any of the above | 15,267 / 47,754 | 32.0% |
| **live** `NEAR/EXACT/VARIANT/REUSES.evidence` | **5,554 / 6,271** | **88.6%** |
| **live** `ABOUT_CONCEPT.evidence` | **15,229 / 47,754** | **31.9%** |
| `formulas.jsonl`, `formula_occurrences.jsonl`, `concepts.jsonl` | 0 | clean |

Sentinel frequency in the parallels file: U+E003 ×20,120, U+E000 ×10,434, U+E002 ×220, U+E001
×73.

Two distinct harms.

**(a) Unrenderable.** The very first row of `cross_veda_parallels.jsonl` quotes
`AVS 1.4.1 == RV 1.23.16` as:

```
ambayo yanty adhvabhir jāmayo adhvarīyatām p<U+E000>ñcatīr madhunā payaḥ
```

A reader sees `pñcatīr` or `p□ñcatīr` for `pṛñcatīr`. On 88.6% of parallel edges, the evidence
the UI contract rests on cannot be displayed.

**(b) It silently changes words.** The `notes` field prints matched aliases, and a stripped
sentinel turns a Sanskrit word into a *different* Sanskrit word:

| stored `notes` displays | actual alias |
|---|---|
| `matched aliases: law, tasya` (`RV 7.66.12`) | `ṛtasya` — `tasya` is a different word ("of that") |
| `matched aliases: ghe, house` (`AVS 15.13.4`) | `gṛhe` |
| `matched aliases: amtasya` (`RV 7.4.6`) | `amṛtasya` |
| `matched aliases: pthivī, pthivīm` (`SV UTTARA 2.1.11.1`) | `pṛthivī`, `pṛthivīm` |
| `matched aliases: ghtena` (`SV CHANDA 1.7.8`) | `ghṛtena` |

The underlying assertions are all correct. What is published as the reason for them is not
readable and, in 4,657 cases, is misleading. `formulas.py` already contains the fix
(`_readable`); it just is not applied on the other two paths.

---

## SERIOUS

### S1 — `match_level` asserts an identity that does not hold, on 4,229 of 6,271 rows (67.4%)

`MatchLevel.SANDHI_INSENSITIVE` is defined in `surfaces.py` as *"Identical once word boundaries
are also dropped."* Every `NEAR_PARALLEL_OF` row (3,049) and every `REUSES_TEXT_FROM` row derived
from one (1,180) carries `match_level: "SANDHI_INSENSITIVE"` — while the same row's
`levels_reached` is **`[]`**, correctly recording that the pair is identical at no level at all.

```json
"match_level": "SANDHI_INSENSITIVE",
"levels_reached": [],
"predicate": "NEAR_PARALLEL_OF"
```

Verified: `levels_reached == []` for all 3,049 NEAR rows, and `match_level ∉ levels_reached` for
4,229 rows. The two fields contradict each other inside one row.

Downstream, the manifest reports `rows_by_match_level: {SANDHI_INSENSITIVE: 5432, …}`, which
reads as "5,432 pairs are identical once word division is set aside". The true figure is
**788**. A consumer filtering on `match_level` to find identity-grade evidence gets a 7×
over-count.

### S2 — Live-graph relationship-type collision on `EXACT_PARALLEL_OF`

```cypher
MATCH ()-[r:EXACT_PARALLEL_OF]->() RETURN count(r)   -- 1006
```

The artifact has 750. The extra **256** are pre-existing **within-Rigveda** edges from the older
Rigveda parallel layer, and they are structurally incompatible:

| | enrichment edges (750) | legacy edges (256) |
|---|---|---|
| properties | `pipeline_version, run_id, method, veda_pair, match_level, levels_reached, similarity, token_jaccard, ngram_jaccard, lcs_ratio, edit_ratio, evidence, trust, state, notes, score` | `strongest_method, methods, similarity, provenance_class, status` |
| `pipeline_version` | `vedagraph-graph-enrichment-v1` | **null** |
| `veda_pair` | AV-RV / RV-SV / … | **null** |
| `evidence` | present | **absent** |
| endpoints | cross-Veda only | RV→RV only (e.g. `RV 1.13.9 → RV 5.5.8`) |

Consequences: (i) the headline "750 exact cross-Veda parallels" is not what the graph returns;
(ii) **256 `EXACT_PARALLEL_OF` edges in the live graph carry no evidence and no provenance at
all**, which is the one thing this release's contract says cannot happen; (iii) any UI reading
`r.evidence` or `r.veda_pair` nulls out on 25% of the type. The legacy layer's other edges use a
distinct type (`PARALLEL_TO`, 69 edges) with the same property shape, so the collision is on this
one name only.

### S3 — The formula display surface drops Yajurveda visarga, misquoting 303 edges and splitting a Formula node in two

`_build_views` in `formulas.py` builds the surface used for `display_form`, `source_forms` and
every `USES_FORMULA` evidence quote as:

```python
iast = comparison_form(
    to_iast(surfaces.source, surfaces.script), ComparisonForm.ACCENT_STRIPPED_COMPARISON
)
```

It omits `fold_devanagari_source_conventions`. That omission is the exact failure `surfaces.py`
was written to prevent — its docstring records that 893 of 1,975 Yajurveda mantras type visarga
as an **ASCII colon**, which `strip_editorial_marks` then deletes as a separator, and that
folding it to U+0903 first raised exact cross-Veda identity from 1,404 to 1,538 pairs. The
cross-Veda path got the fold; the formula path did not.

Measured corpus-wide by diffing the display surface against the folded surface, token by token
over all 20,210 mantras and 292,752 tokens:

- **1,305 tokens across 824 mantras lose their visarga** on the display/quote surface
  (`vaḥ`→`va`, `vasoḥ`→`vaso`, `viśvāyuḥ`→`viśvāyu`, `indraḥ`→`indra`, `ṇaḥ`→`ṇa`).
- **303 of 22,686 `USES_FORMULA` evidence quotes (1.34%) do not appear in the cited passage on
  any surface** — 302 YV, 1 SV, and 303/303 explained by exactly this.
- The token-count guard (`if len(display) != len(folded)`) does not catch it, because a
  word-final colon collapses without changing the token count. It fires on only 7 mantras.

It also splits a Formula node. `display_form` is supposed to be effectively unique; there is
**one duplicate**, and it is this bug:

```
VG:ENRICH:FORMULA:9e6dcf1be895fed13529c0d5420b171b  normalized "pataye namo nama"   6 mantras
VG:ENRICH:FORMULA:42fb2d3157aa97630835e58a6fa2c493  normalized "pataye namo namaḥ"  4 mantras
   both display_form = "pataye namo nama",  both source_forms = ["pataye namo nama"]
   both include VSM 16.17 and VSM 16.18 in their occurrence sets
```

Two hub nodes, identical displayed text, overlapping occurrence sets, for one Yajurveda refrain —
which is precisely what the Formula hub exists to prevent. Confirmed live:
`MATCH (f:Formula) WITH f.display_form AS k, count(*) AS c WHERE c>1 RETURN count(*)` → 1.

### S4 — The concept cap's tie-break is alphabetical, and it decides the outcome on 80% of capped passages

`MAX_CONCEPTS_PER_PASSAGE = 4`, and `top_k` breaks ties on the item's own ordering — here the
`concept_id` string — for reproducibility. That is the right call for determinism. The problem is
how often the tie-break is load-bearing: the confidence scale has only a handful of discrete
values (20,537 assertions sit at exactly 0.42, the single-alias English score).

Recomputed from the corpus, reproducing the manifest's 5,323 drops exactly:

```
passages over the 4-concept cap                          3,009
  ... where the keep/drop boundary is an exact score TIE  2,411   (80.1%)
tied candidates KEPT    : mean alphabetical rank 27.8 of 89   (n = 4,629)
tied candidates DROPPED : mean alphabetical rank 60.0 of 89   (n = 3,755)
```

For **8,384 tied candidates**, which concept a passage is recorded as being "about" is decided by
the alphabet. The bias is systematic and it costs the most central concepts the most:

```
most-dropped by the cap:
  YAJNA-SACRIFICE 425   STOMA-PRAISE 380   VASU-WEALTH 342   PRTHIVI-EARTH 239
  SARMAN-PROTECTION 131  YUDH-BATTLE 128   SVASTI-WELLBEING 127  SOMA-DRINK 126
```

Concepts sorting early (`ADHVAN`, `AGNI`, `AHI`, `AMRTA`, `ANNA`, `AP`, `ASMAN`, `ASVA`, `ATMAN`,
`AVAS`, `AYUDHA`) are systematically favoured over `YAJNA`, `YUDH`, `VASU`, `STOMA`, `SVASTI`.
Any downstream "what is the Rigveda about" analytic inherits an alphabetical prior.

The determinism requirement is real, but it does not require an *alphabetical* tie-break — a
tie-break on corpus frequency, on evidence-path rank, or a wider score scale would all be
deterministic without this bias.

### S5 — Structured English-alias sense errors that random sampling cannot find

Full detail in Attack 3. Summary:

| alias → concept | population | audited | measured wrong |
|---|---|---|---|
| `realm` → `RAJAN-KINGSHIP` | 35 (30 sole-evidence) | **all 35** | **29/35 = 82.9%**; **29/30 = 96.7%** of sole-evidence |
| `stone` → `ASMAN-PRESSING-STONE` | 73 (48 sole) | 20 | ~62% not the soma press |
| `way`/`ways` → `ADHVAN-PATH` | 298 (256 sole) | 14 | ~21% adverbial, not a road |
| `bow` → `AYUDHA-WEAPON` | 67 (33 sole) | 14 | ~21% the verb "bow down" |

Aggregate cost ≈ 128 assertions (0.27% of the layer). The finding is not the aggregate — it is
that **a 60-row random sample has a 4% chance of containing even one `realm` row**, so the 97.8%
headline and the 96.7%-wrong pocket are both true simultaneously. Precision on this layer should
be reported per-alias, not per-row.

---

## MINOR

### M1 — 60 Formula nodes report an `occurrence_count` they do not have edges for

`_apply_caps`'s own docstring: *"a Formula whose `mantra_count` says 40 while 12 `USES_FORMULA`
edges exist is a node lying about its own occurrence set."* 60 nodes meet that description,
because `occurrence_count` silently counts repetitions *within* a mantra while `mantra_count`,
`veda_counts` and the edges count distinct mantras.

```
makhāya tvā makhasya tvā śīrṣṇe   occurrence_count 23 | mantra_count 8 | veda_counts {YV:8} | edges 8
ca ma indraśca me                 occurrence_count 17 | mantra_count 3 | veda_counts {YV:3} | edges 3
rāṣṭradā rāṣṭramamuṣmai           occurrence_count 17 | mantra_count 3 | veda_counts {YV:3} | edges 3
priyā dhāmāny                     occurrence_count 10 | mantra_count 3 | veda_counts {RV:2,YV:1} | edges 3
```

`sum(node.occurrence_count) = 22,858` against **22,686** actual edges — a 172 gap. Because the
two fields are equal on the other 4,765 nodes, `occurrence_count` looks like a synonym for
`mantra_count` and quietly is not on 1.2% of nodes. No duplicate `(formula, passage)` edges
exist, so nothing is missing; the node property is just measuring something else without saying
so.

### M2 — 22.9% formula node redundancy after maximality

1,103 of 4,825 surviving formulas are strict substrings of another surviving formula; 562 (11.6%)
add exactly one extra mantra. Detail and examples in Attack 4.

### M3 — 34 formulas display an avagraha-truncated non-word

0.70% of nodes, 429 of 22,686 occurrence edges (1.89%). Includes
`yo smān dveṣṭi yaṃ vayaṃ dviṣmaḥ` and `devasya tvā savituḥ prasave śvinor bāhubhyāṃ pūṣṇo`.
This residual is **documented** in `formulas.py`; the full measurement is new. Detail in
Attack 4.

### M4 — Cross-Veda row count is inflated 26.9% by directed mirrors

1,684 of the 6,271 rows are `REUSES_TEXT_FROM` rows that mirror the 1,684 symmetric RV-SV rows
one-for-one (89 EXACT + 1,180 NEAR + 415 VARIANT). Keeping both is a deliberate, documented
choice. But `analytics.json`'s `relationship_matrix` then reports RV-SV as
`{EXACT 89, NEAR 1180, VARIANT 415, REUSES 1684}` = 3,368 relationships over 1,684 distinct
pairs, and the manifest's `rows_by_veda_pair` does the same. A reader totalling that matrix
double-counts every RV-SV parallel.

### M5 — `SHARES_FORMULA_WITH` is declared and registered but empty

The predicate is in `TextualPredicate`, has a signature in `SIGNATURES`, and is a registered
relationship type in the live database — with **0 edges**. Nothing in the manifest or analytics
says it was skipped. A consumer reading the vocabulary will write a query that always returns
nothing.

### M6 — `notes` is dropped when `ABOUT_CONCEPT` is projected into Neo4j

The artifact row carries `notes: "matched aliases: …"`, which is the only place the *reason* for
a concept assertion is recorded in human-readable form. The live edge's properties are
`[model, prompt_policy, assertion_id, veda, method, state, evidence_count, run_id,
pipeline_version, score, confidence, trust, evidence]` — no `notes`. The alias provenance is
artifact-only. (Ironically this also means B1's misleading `notes` never reached the graph.)

### M7 — `ASMAN-PRESSING-STONE`: label and definition disagree

The definition reads *"and stone generally as the hard thing a god splits or a press works
with"*, which legitimately covers `AVS 12.1.26` *"Rock is earth, stone, dust"*. The
`preferred_label_en` is **"pressing stone"** and the id is `ASMAN-PRESSING-STONE`. 267 assertions
carry the label; roughly 60% of them are not about the soma press. Either the label or the
definition should move.

### M8 — A base-corpus OCR error produces a wrong assertion

`RV 9.86.32` Griffith reads *"spinning, as he knows **bow**, the triply-twisted thread"* (for "as
he knows how"), producing `VG:CONCEPT:AYUDHA-WEAPON` at confidence 0.42 on a Soma Pavamāna verse.
Corpus defect, not enrichment defect — but it is the kind of thing an English-alias layer
amplifies, and 42 passages in the corpus carry a `bow` token in translation.

---

## COSMETIC

- **C1** — `SourceArtifact` label exists in the live schema with **0 nodes**. Pre-existing, not
  from this release.
- **C2** — `cross_veda_parallels.jsonl` is sorted by `(predicate, subject_key, object_key)` and
  `formula_occurrences.jsonl` by an internal order. Both are stable and the files are
  bit-reproducible, so this is not a determinism problem — but neither file is sorted by its own
  primary id, which makes a hand diff between two releases harder to read than the `write_jsonl`
  docstring implies.

---

# What I attacked and found nothing

Recording these because a clean attack is evidence, and the parent agent needs to know which
stones were turned over.

1. **Near-parallel false positives at the score floor.** 20 rows read at 0.72–0.78. 0 false
   positives. I expected this to be the weakest band and it is not.
2. **Near-parallel false positives mid and high band.** 20 + 20 read. 0 false positives.
3. **RV↔SV sandhi-driven agreement.** Specifically hunted. The scoring is LCS-dominated (min
   `lcs_ratio` 0.737 over all 3,049 rows) so character agreement alone cannot carry a pair over
   the floor. 0 cases found.
4. **Refrain collisions dressed up as parallels.** Exhaustive longest-common-substring test on
   all 3,049 NEAR rows; the 12 worst read by hand. 0 collisions.
5. **EXACT_PARALLEL_OF not actually exact.** All 750 re-verified mechanically. 0 defects.
6. **VARIANT_OF differing by more than word division.** All 788 re-verified. 0 defects.
7. **Lossy folding manufacturing false identities.** All 471 same-script fold-created identities
   diffed. Every erased distinction is a legitimate transcription convention; the dangerous
   lateral fold produced 0 of them.
8. **The Samaveda sandhi substring path.** Over-sampled 15/473 expecting carnage. 15/15 loose
   correct, 14/15 strict. `MIN_SANDHI_ALIAS_CHARS` and `SANDHI_SUPPRESSED_ALIASES` work.
9. **The English modal verb `might`.** 588 assertions, 14 read, 0 modal usages.
10. **`light`, `word`/`words`, `born`, `golden`, `liberal`, `pressed`, `grass`, `field`,
    `stones`.** Audited for sense errors; no systematic problem (`stones` ~15–20%, borderline).
11. **Determinism.** Full re-run, all five artifacts bit-identical to the shipped files and to
    the manifest digests. Not a single byte moved.
12. **Guards not binding.** Every cap and floor re-derived from the artifacts. Two bind exactly
    (5 and 4), the rest have headroom. 0 violations.
13. **All-pairs blowup.** LSH bucket cap 800 vs 54 observed; identity bucket 15. No reachable
    all-pairs path on this corpus.
14. **Cross-Veda and concept provenance.** 73,361 evidence spans checked exhaustively; 0
    unresolvable locators, 0 quotes that are not in the cited passage.
15. **Projection loss.** 76,711 edges diffed artifact-vs-live. 0 missing, 0 extra.
16. **Dangling references.** 0 assertions with a non-existent `passage_key`, 0 occurrence edges
    with an unknown `formula_id` or `passage_key`, 0 dangling `ABOUT_CONCEPT`/`USES_FORMULA` in
    the graph, 0 orphan `Formula`/`Concept` nodes.
17. **`veda_pair` / `subject_veda` / `object_veda` / assertion `veda` label disagreements.** 0 of
    6,271 and 0 of 47,754.
18. **`REUSES_TEXT_FROM` direction.** All 1,684 are SV→RV. Correct, and the refusal to direct
    RV-YV or AV-RV is a documented decision (`ESTABLISHED_REUSE`), not an oversight.
19. **Duplicate ids and duplicate pairs.** 0 across every artifact and the live graph.
20. **Base-graph counts and duplicate canonical keys.** All three counts exact, 0 duplicates,
    both named Rigveda passages carry exactly one Griffith translation.
21. **Manifest honesty.** All 5 digests and all 5 counts match the files on disk.
22. **Per-passage / per-mantra cap off-by-one.** Boundaries are exact (max = 5 and max = 4, none
    over). The problem at the boundary is S4, not an off-by-one.

---

## Reproduction

Every number above was produced from `D:\VedaGraph` with the project venv, read-only. The
non-obvious recipes:

```python
# Attack 1 sample
near  = [r for r in rows('cross_veda_parallels') if r['predicate']=='NEAR_PARALLEL_OF']
bands = {'lo': score<0.78, 'mid': 0.85<=score<0.90, 'hi': score>=0.95}
random.seed(20260909); random.sample(band, 20)

# Attack 3 sample
random.seed(31415); per-path sample sizes 15 / 15 / 20 / 10 by method suffix

# B1
re.compile(r'[\ue000-\uf8ff]').search(raw_json_line)

# S3
for every mantra: compare comparison_form(to_iast(source, script), ACCENT_STRIPPED_COMPARISON)
token-by-token against surfaces.script_folded with sentinels rendered back

# S4
recompute _sanskrit_token_hits / _sanskrit_sandhi_hits / _english_hits per mantra,
score them with the module's own band constants, sort by (-score, concept_id),
and compare the alphabetical rank of the kept vs dropped candidates at the tie boundary

# Determinism
build the five row lists in-process and sha256 the orjson OPT_SORT_KEYS serialisation;
compare against manifest['digests'] and against the file on disk
```
