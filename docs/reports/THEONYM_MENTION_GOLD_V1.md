# The four-Veda theonym mention layer, measured

**Artifacts.** `data/gold/theonym_mention_gold_v1.jsonl` (575 rows, seed `20260909`),
`scripts/evaluate_theonym_gold.py`, `tests/unit/test_theonym_gold_evaluation.py`.
**Layer under test.** `MENTIONS_DEVATA`, **17,165 edges** (16,261 when the gold set was
frozen; bug **B1** was fixed between the two runs, see §6), built by
`src/vedagraph/domain/theonyms.py` and projected by
`vedagraph.domain.v3_loader.load_theonym_mentions`.
**Annotator.** `MODEL_ADJUDICATED`, `claude-opus-5`, run
`theonym-mention-gold-v1:claude-opus-5:2026-09-09`. **No human has reviewed any row of
this set.** The evaluator refuses to load a file that claims otherwise, and a test asserts
that it refuses.

Before this measurement the project's own scorecard rated semantic precision and semantic
recall 1/5 each, on the ground that no measurement existed anywhere in the repository.
This is that measurement. It is not flattering.

---

## 1. Headline

All figures below are the **live** graph, 17,165 edges, after bug **B1** was fixed. The
pre-fix figure from the same 574 rows is retained throughout as the before column, and
`scripts/evaluate_theonym_gold.py --frozen` reproduces it.

The two extraction paths are never blended. The Rigveda has the University of Zurich
manual morphosyntactic annotation, so a Rigvedic mention is a scholarly source stating
that this token's lemma is `índra-`. The Samaveda, Yajurveda and Atharvaveda have no
annotation, so a mention there is an adjudicated surface match. Those are different
claims and a single number would let the annotated corpus's accuracy stand in for the
unannotated ones'.

### Strict target: does this verse name this **god**?

| slice | precision | 95% Wilson | recall | F1 | tp / fp / fn / tn |
|---|---|---|---|---|---|
| **overall** (stratified) | **0.7928** | 0.75–0.83 | **0.8857** | **0.8367** | 310 / 81 / 40 / 143 |
| **`rv-lemma-annotation`** | **0.8226** | 0.75–0.88 | **0.9189** | **0.8681** | 102 / 22 / 9 / 68 |
| **SV/YV/AV surface** | **0.7790** | 0.72–0.83 | **0.8703** | **0.8221** | 208 / 59 / 31 / 75 |

### Weaker target: is a word of the deity's name-lemma in the verse at all?

| slice | precision | recall | F1 | tp / fp / fn / tn |
|---|---|---|---|---|
| overall | **0.9949** | 0.8512 | 0.9175 | 389 / 2 / 68 / 115 |
| `rv-lemma-annotation` | **1.0000** | 0.8611 | 0.9254 | 124 / 0 / 20 / 57 |
| SV/YV/AV surface | **0.9921** | 0.8462 | 0.9130 | 265 / 2 / 48 / 58 |

### Before and after the B1 fix, on the same 574 gold rows

| | frozen (16,261 edges) | live (17,165 edges) |
|---|---|---|
| overall precision | 0.7884 | **0.7928** |
| overall recall | 0.8514 | **0.8857** |
| overall F1 | 0.8187 | **0.8367** |
| surface path P / R / F1 | 0.7717 / 0.8201 / 0.7951 | **0.7790 / 0.8703 / 0.8221** |
| RV path P / R / F1 | 0.8226 / 0.9189 / 0.8681 | unchanged |
| name-lemma target P / R | 0.9947 / 0.8228 | **0.9949 / 0.8512** |
| false negatives | 52 | **40** |
| false positives | 80 | **81** |

**Precision rose while recall rose.** A recall fix that also raises precision is unusual
enough that a reader should suspect it, so the mechanism is worth stating: the fix did not
loosen a matching rule, it removed a gate that was rejecting *exact whole-token* matches
while admitting *substring* matches of the same forms. Everything it admitted was already
adjudicated, and 12 of the 13 rows it moved were mentions the layer should always have
had. The 13th is a pre-existing registry defect the fix merely exposed (**B7**, §6).

**This is the single most important number in the report.** Of 391 asserted rows, only
**2** attach to the wrong word. The layer is essentially never wrong about *which word*
it found — 79 of its 81 false positives are cases where the right word is present in the
wrong *sense*. Host intrusion, sandhi mis-segmentation and wrong-lemma matching, the
failure modes `theonyms.py` was designed against, are almost absent. What remains is the
homonym problem, which no amount of string discipline can solve.

### Unbiased precision (uniform strata only)

The stratified sample deliberately over-samples hard cells, so the figures above are
diagnostic, not corpus-representative. The `*_uniform` strata are plain uniform draws
from the live edge set and are the only unbiased estimates here. They contain no
negatives, so they give precision only.

| slice | precision | 95% Wilson | n |
|---|---|---|---|
| overall | **0.8514** | 0.79–0.90 | 175 |
| `rv-lemma-annotation` | **0.8909** | 0.78–0.95 | 55 |
| SV/YV/AV surface | **0.8333** | 0.76–0.89 | 120 |

Recall is **not** corpus-representative in either direction: the negative strata were
drawn from probe pools chosen to be likely misses. Section 6 gives a mechanical,
whole-corpus recall measurement instead.

---

## 2. Method

**Target definition.** `gold_label = MENTION` iff, in this verse, the word denotes the
deity as a divine being. The rules, applied uniformly and stated so they can be argued
with:

1. A vocative, or an argument of a verb of worship/invocation/offering → MENTION.
2. Agent or patient of a divine or mythic act; a member of a list of gods; a bearer of a
   divine epithet (`deva`, `devī`, `rājan`, `patiḥ`); a kinship relation to a god → MENTION.
3. NO_MENTION where the word functions as its homonymous common noun: an `iva`/`na`
   simile on the ordinary sense (`mitram iva` "like a friend"); the plural of an
   `INDIVIDUAL`-structure deity denoting a class (`rudrāḥ` "the Rudras"); a bodily faculty
   or human utterance (`vāce svāhā` in a list with eye, ear, mind); a substance pressed,
   mixed, drunk or measured in a verse whose object of praise is another deity; a pure
   location, extent, route or time-marker; a theonym inside a compound the compound does
   not denote; a form of a homonymous *different* lexeme.
4. Agni as the kindled ritual fire that receives oblations → MENTION (the tradition
   identifies them). Agni as heat or flame in a factual statement or physical simile →
   NO_MENTION.
5. Soma as the addressed or praised subject of a pavamāna-type hymn → MENTION. Soma as
   the object drunk in a hymn to another deity → NO_MENTION. This is the
   Jamison–Brereton "Soma" / "soma" distinction, not an invention of this report.
6. AMBIGUOUS where the Sanskrit is corrupt or obscure, or two readings are equally
   supported. Excluded from every denominator and counted.

`name_lemma_present` is deliberately *mechanical* at the lemma-string level: true iff a
word whose lemma is the deity's name-lemma occurs, in whichever sense. It is false only
for host intrusion, a preverb, or a genuinely different lexeme.

**Rows where rules 3(d), 3(e), 4 or 5 decided the call, or where a competent reader could
take the other view, are flagged `borderline: true`** — 44 rows. Section 5 gives every
metric with them removed so a reader who disagrees with the policy can see the effect
rather than take it on trust.

**Adjudication was against the Sanskrit.** Each row carries `sanskrit` (the
`unicode_normalized` source surface: accented IAST for RV and AV, Devanagari for SV and
YV) and `sanskrit_iast` (the same text rendered readable). For Rigvedic rows the Zurich
annotation's lemma, part of speech, case, number and gender for every token of that lemma
are recorded in `rv_annotation_tokens`; that settles morphology but never sense, and every
Rigvedic homonym row was read. Griffith and Whitney were consulted only to confirm a
*class* of reading; where a translation and the Sanskrit disagreed the Sanskrit governed —
at RV 6.61.6 Griffith prints the masculine "Sarasvad" where the text reads `devi sarasvati`,
feminine vocative, and the gold follows the text. Nine Samavedic and Yajurvedic readings
were settled by locating the Rigvedic parallel in this corpus (recorded in the row's
`reasoning`); two of them, RV 6.48.1 and RV 7.81.1, produced the false positives in §4.

**Circularity, stated.** For Rigvedic rows on a deity whose name is *not* also a common
noun (Indra, Varuṇa, Marut, Bṛhaspati, Viṣṇu, Tvaṣṭṛ, Parjanya, …), gold and layer share
the same annotation, so precision there is close to tautological — the informative
Rigvedic numbers are the homonym rows and the recall rows. This is why the report never
quotes the RV figure alone.

---

## 3. Stratification

| stratum | rows | edges asserted | gold MENTION |
|---|---|---|---|
| `P1_rv_uniform` | 55 | 55 | 49 |
| `P2_sv_token_uniform` | 25 | 25 | 21 |
| `P3_sv_sandhi_uniform` | 25 | 25 | 24 |
| `P4_yv_uniform` | 30 | 30 | 24 |
| `P5_av_uniform` | 40 | 40 | 31 |
| `P6_ambiguous_noun` | 86 | 86 | 58 |
| `P7_minor_deity` | 61 | 61 | 46 |
| `P8_morph_variety` | 57 | 57 | 45 |
| `N1_name_present_no_edge` (SV/YV/AV) | 72 | 0 | 37 |
| `N2_rv_name_present_no_edge` | 35 | 0 | 4 |
| `N3_false_positive_host` | 35 | 0 | 9 |
| `N4_rejected_form` | 30 | 0 | 1 |
| `N5_structural_exclusion` | 24 | 0 | 1 |
| **total** | **575** | **379** | **350** |

Coverage: all four Vedas (RV 201, AV 140, SV 119, YV 115); all three extraction paths
(`rv-lemma-annotation` 124, `sanskrit-surface-token` 225, `sanskrit-surface-sandhi` 30);
**49 distinct deities**; 14 major deities and the whole long tail down to
`VG:DEVATA:APAM-NAPAT` (1 edge in the entire graph); all seven ambiguous common nouns the
brief names, including `VG:DEVATA:RATHAH` (8 rows) and `VG:DEVATA:KAH` (3 rows), which the
layer refuses by design; morphological variety (vocative, sandhi-fused, compound-initial,
dual, ablative, locative, instrumental, unknown); 379 positives and 196 negatives.

Sampling is deterministic: seed `20260909`, `random.Random(seed).sample` over
lexicographically sorted candidate pools, recorded per row in `sample_seed`. The pools it
drew from were large — 2,364 Rigvedic and 3,168 non-Rigvedic name-present-no-edge
candidates, 3,836 host-string candidates, 5,177 rejected-form candidates — so the draw is
a sample, not an enumeration, and re-running the builder reproduces it exactly.

**Exclusion bucket: 1 row.** `TMG-0379` (AVS 6.31.3, `vāk pataṅgo aśiśriyat`), where
Whitney marks the verse difficult and the Sanskrit does not settle goddess against
"voice". One exclusion in 575 is not a finding; a large bucket would have been.

---

## 4. Per-cell metrics

### Per Veda (live, with the pre-fix figure in brackets)

| Veda | precision | recall | F1 | tp / fp / fn / tn |
|---|---|---|---|---|
| RV | 0.8226 (=) | 0.9189 (=) | 0.8681 (=) | 102 / 22 / 9 / 68 |
| SV | 0.8276 (=) | 0.8571 (=) | 0.8421 (=) | 72 / 15 / 12 / 20 |
| YV | **0.8171** (0.8101) | **0.8481** (0.8101) | **0.8323** (0.8101) | 67 / 15 / 12 / 21 |
| **AV** | **0.7041** (0.6818) | **0.9079** (0.7895) | **0.7931** (0.7317) | 69 / 29 / 7 / 35 |

**The Atharvaveda moved most, exactly as predicted.** Its recall went 0.7895 → **0.9079**
and its F1 0.7317 → 0.7931; 10 of the 13 rows the fix moved are Atharvavedic and 3 are
Yajurvedic. Not one Rigvedic or Samavedic cell changed by a single row, which is the
right signature for a fix to a condition that could only ever have starved AV and YV. The
Atharvaveda is still the worst cell on precision (0.7041) — it is the largest unannotated
corpus at 5,839 mantras, its accented IAST edition fuses and elides freely, and no form's
substring licence is granted for it — but it is no longer the worst on recall.

### Per extraction path, edges only (precision of what the layer asserts)

| path | precision | 95% Wilson | n |
|---|---|---|---|
| `sanskrit-surface-sandhi` | **0.9667** | 0.83–0.99 | 30 |
| `rv-lemma-annotation` | 0.8226 | 0.75–0.88 | 124 |
| `sanskrit-surface-token` | **0.7455** | 0.68–0.80 | 224 |
| *(13 rows the fix moved)* | 0.9231 | 0.66–0.99 | 13 |

The 13 rows the fix moved are broken out separately because `refresh_from_live` recomputes
*whether* an edge exists but does not repopulate the edge's properties, so those rows carry
no `extraction_path` or `referent_certainty` from the frozen snapshot. Queried directly
against the live graph they are all `sanskrit-surface-token`, all `TIER_B`, and split
6 `DEITY_CERTAIN` / 7 `DEITY_AMBIGUOUS`. Folding them in gives the token path 237 rows at
precision **0.7553** and leaves the ranking below unchanged.

The ranking is the opposite of the layer's own score assignment (`0.99` annotation,
`0.90` token, `0.60` sandhi). The Samavedic substring pass is the *most* precise pass in
the layer, because its per-form licensing is tight and it is restricted to deities the
token pass did not already reach; the whole-token pass is the least precise, because it
is where the ambiguous common nouns land. The `0.60` score on the sandhi path is
pessimistic by roughly 0.37 and the `0.90` on the token path optimistic by roughly 0.15.
Those scores are not calibrated and should not be read as probabilities.

### Per deity (only where n ≥ 8; 29 deities had too few rows and are named, not scored)

| deity | precision | recall | tp / fp / fn / tn | moved by the fix |
|---|---|---|---|---|
| SARASVATI | 1.0000 | 1.0000 | 9 / 0 / 0 / 0 | |
| SAVITA | 1.0000 | **1.0000** | 15 / 0 / 0 / 1 | R 0.7333 → 1.0000 |
| BRHASPATIH | 1.0000 | **1.0000** | 5 / 0 / 0 / 3 | R 0.8000 → 1.0000 |
| INDRAH | 1.0000 | **0.9600** | 48 / 0 / 2 / 0 | R 0.8800 → 0.9600 |
| AHIH | 1.0000 | 1.0000 | 5 / 0 / 0 / 12 | |
| YAMAH | 1.0000 | 1.0000 | 1 / 0 / 0 / 24 | |
| MARUTAH | 1.0000 | **0.8889** | 8 / 0 / 1 / 3 | R 0.7778 → 0.8889 |
| USAH | 1.0000 | 0.8125 | 13 / 0 / 3 / 15 | |
| AGNIH | 0.9565 | **0.8302** | 44 / 2 / 9 / 1 | R 0.8113 → 0.8302 |
| ASVINAU | 0.9000 | **1.0000** | 9 / 1 / 0 / 6 | R 0.8889 → 1.0000 |
| PAVAMANAH-SOMAH | 0.9286 | 1.0000 | 13 / 1 / 0 / 0 | |
| MITRAH | 0.7692 | 0.7692 | 10 / 3 / 3 / 1 | |
| SURYAH | 0.7222 | — | 13 / 5 / 0 / 0 | |
| **SOMAH** | **0.6486** | — | 24 / 13 / 0 / 4 | P 0.6667 → 0.6486 (**B7**) |
| PRTHIVI | 0.6000 | 0.4737 | 9 / 6 / 10 / 2 | |
| RUDRAH | 0.5833 | — | 7 / 5 / 0 / 0 | |
| **APAH** | **0.2500** | 0.5000 | 4 / 12 / 4 / 29 | |
| **VAK** | **0.0000** | — | 0 / 10 / 0 / 11 | |
| RATHAH | — (0 asserted) | — | 0 / 0 / 0 / 8 | |

Seven deities moved. Six moved on **recall only** — Savitṛ and Bṛhaspati to 1.0000, the
Aśvins to 1.0000, Indra to 0.9600, the Maruts to 0.8889, Agni to 0.8302 — and their
precision was already 1.0000 or 0.9565 and stayed there. **Soma is the only deity whose
precision fell** (0.6667 → 0.6486), and the cause is **B7**, not the fix.

**The four cells that most need reading did not move, and they are the open problem.**
`VAK`, `APAH`, `RUDRAH` and `PRTHIVI` are unchanged, because their failure is sense
selection, which B1 had nothing to do with.

Too few rows for a figure (n < 8), listed rather than scored: ADITIH 5, ADITYAH 2,
APAM-NAPAT 2, ARANYANI 4, ASHVAH 4, ATMA 1, BRAHMANASPATIH 6, CANDRAMAH 1, DEVAH 5,
DYAVAPRTHIVYAU 4, HARIH 2, INDRAGNI 1, INDRAVAYU 4, KAH 3, MANYUH 5, MITRAVARUNAU 3,
MRTYUH 6, NIRRTIH 5, PARJANYAH 5, PITARAH 5, PURUSAH 7, PUSA 5, RATRIH 7, RBHAVAH 5,
TVASTA 4, VARUNAH 4, VISNUH 3, VISVAKARMA 6, VISVEDEVAH 6.

`VG:DEVATA:VAK` at **precision 0.0000 on 10 asserted rows — zero true positives — is the
largest single finding in this report, it is unaffected by the B1 fix, and it is open.**
Every Vāc edge in the sample is the common noun: `vāce svāhā` in a list of bodily faculties
beside eye, ear and mind (VSM 22.23), `tisro vāca ud īrate` "three ritual utterances rise"
(SV, = RV 9.33.4), `vācam aṣṭāpadīm ... mame` "I measured out an eight-footed speech"
(SV UTTARA 3.2.9.3), `vācaḥ yantṛ` "controller of speech" (VSM 18.37), `pra vadāti vācam`
of a war-drum (AVS 5.20.8). The graph node describes Vāc as "Speech as a goddess, who
declares in her own voice that she moves with all the gods" — a real but rare figure,
essentially RV 10.125 and a handful of others. **The layer asserts her on 302 passages.
On this sample none of them are her.** A user querying Vāc today gets a wrong answer on
every row unless they filter `referent_certainty = DEITY_CERTAIN`, which happens to
exclude all ten. That filter is the only thing standing between this deity and a
confidently wrong result, and it is not the documented default.

### The layer's own confidence signal

| `referent_certainty` | asserted | wrong | error rate |
|---|---|---|---|
| `DEITY_CERTAIN` | 139 | 4 | **0.0288** |
| `DEITY_AMBIGUOUS` | 252 | 77 | **0.3056** |

(Live figures, with the 13 refreshed rows' certainty read directly from the graph: 6
`DEITY_CERTAIN`, all correct, and 7 `DEITY_AMBIGUOUS`, one wrong. Pre-fix the split was
133 / 4 = 0.0301 and 245 / 76 = 0.3102, so the fix left the signal's separation intact.)

**The signal works.** A tenfold separation on 391 rows is the strongest positive result
here: `theonyms.py`'s central design decision — record the certainty rather than resolve
it, and refuse to honour a `VOCATIVE` label outside the Rigveda — is doing exactly what it
was built to do. A consumer filtering on `referent_certainty = DEITY_CERTAIN` gets 0.97
precision from a layer whose unfiltered precision is 0.79. That should be the documented
default for product traversal, and on the evidence of the VAK result above it is the
difference between a usable answer and a wrong one.

The four `DEITY_CERTAIN` errors are worth naming because they are the residual: `TMG-0248`
(RV 10.92.14, `áditim` is the adjective "unbounded" qualifying Agni, not the goddess),
`TMG-0471` (AVS 12.3.33, `tvaṣṭreva` "like an ARTISAN" — `tvaṣṭṛ-` in its common-noun
sense, and TVASTA is registered `UNAMBIGUOUS`), `TMG-0352` (AVS 9.9.10, the riddle hymn's
"three fathers" are cosmic principles, not the ancestral Pitaraḥ), `TMG-0550`
(RV 10.31.10, `pitroḥ` is the dual "the two parents", heaven and earth).

### Ambiguity failure rate

Among the 287 asserted rows whose surface form is an ambiguous common noun, **77 pick the
wrong sense: 0.2683** (pre-fix 76 of 280, 0.2714). Attachment errors are excluded from
that numerator by construction, so this is a pure sense-error rate. The fix barely moved
it, which is the point: B1 was a recall defect and the sense problem is untouched.

By ambiguity class over all scorable rows:

| class | n | precision | recall |
|---|---|---|---|
| `UNAMBIGUOUS` | 145 | 0.9626 | 0.9196 |
| `GEOGRAPHIC_HOMONYM` (Sarasvatī) | 9 | 1.0000 | 1.0000 |
| `DIFFERENT_LEMMA_HOMONYM` | 49 | 0.8571 | 0.9231 |
| `COMMON_NOUN_HOMONYM` | 352 | **0.7016** | 0.8700 |

The registry's own ambiguity classification predicts the error rate: an unambiguous name
is right 96% of the time and a common-noun homonym 70%. The `GEOGRAPHIC_HOMONYM` class
(Sarasvatī, the river) scored 9/9 — the feared river-versus-goddess confusion did not
appear once, because in this corpus `sarasvatī` is almost always accompanied by `devī` or
a vocative.

---

## 5. Errors

**81 false positives.** 79 are sense errors; 2 are attachment errors. Concentration
(path, deity): surface-token SOMAH 12, surface-token VAK 8, annotation APAH 6,
surface-token APAH 6, surface-token PRTHIVI 5, surface-token PURUSAH 5, surface-token
RUDRAH 4, surface-token MANYUH 4. The named classes:

1. **The substance, not the god** (≈30 rows). `somam` as the pressed drink Indra swallows
   (`TMG-0214` RV 3.32.9 `sadyo yaj jāto apibo ha somam`; `TMG-0312` VSM 12.55 `somaṃ
   śrīṇanti pṛśnayaḥ`, the cows mixing it with milk); `apām/apsu` as the water soma is
   mixed into (`TMG-0241` RV 9.86.25 `apām upasthe`, `TMG-0411` RV 9.97.48 `apsu
   svādiṣṭhaḥ`). The layer flagged every one of these `DEITY_AMBIGUOUS`, so it is not
   asserting them confidently; it is asserting them.
2. **The abstraction or faculty, not the goddess** (≈17 rows). Every VAK error above, plus
   `manyu` = wrath (`TMG-0511` VSM 18.4 `manyuśca me bhāmaśca me`, in a list of the
   speaker's own qualities; `TMG-0464` AVS 6.116.3, the Fathers' anger), `puruṣa` = a man
   (`TMG-0461` AVS 5.7.2 `puruṣaṃ parirāpiṇam` "a wheedling man"; `TMG-0465`, `TMG-0473`),
   `rātri` = a counted night (`TMG-0480` RV 1.116.24 `daśa rātrīr ... nava dyūn`;
   `TMG-0517` VSM 36.11 `ahāni śaṃ bhavantu naḥ śaṃ rātrīḥ`).
3. **`iva`/`na` similes on the ordinary sense** (4 rows, all clear-cut). `TMG-0417`
   SV CHANDA 1.4.1 = RV 6.48.1 `priyam mitraṃ na śaṃsiṣam` "as a dear FRIEND", asserted as
   Mitra; `TMG-0270` SV UTTARA 5.1.18.1 `mitram iva priyam agne`, likewise; `TMG-0471`
   `tvaṣṭreva` "like an artisan"; `TMG-0427` SV UTTARA 1.2.16.2 `sūrya ivopadṛk` "like the
   sun in appearance".
4. **Plural of an `INDIVIDUAL` deity denoting a class** (≈5 rows). `VG:DEVATA:RUDRAH` has
   `structure: INDIVIDUAL` and is described as "father of the Maruts", but `ādityā rudrā
   vasavaḥ` (AVS 5.3.9, AVS 6.68.1, VSM 29.8) and `te rudrāsaḥ ... avantu` (RV 5.87.7)
   name the Rudra *troop*. Also `viśvakarmāṇaḥ` NOM/PL "men of all works" (AVS 12.1.13)
   and `vāyubhiḥ` "with the winds" (RV 9.84.4). See bug **B4**.
5. **Compound-internal, where the compound denotes something else** (≈6 rows).
   `apsuṣadam ... ghṛtasadaṃ vyomasadam` "water-seated, ghee-seated, heaven-seated"
   (VSM 9.2, asserted as APAH); `soma-pṛṣṭhāya ... agnaye` "to soma-backed AGNI"
   (VSM 20.78, asserted as SOMAH); `sūryaśritaḥ` "sun-resorting" (AVS 6.49.3);
   `soma-pītaye` (SV UTTARA 6.2.2.2); `manyu-śamana-` "fury-appeaser" (AVS 6.43.2);
   `puruṣa-jīvanī-` "man-life-giving" (AVS 8.7.4, AVS 19.44.3).
6. **A different lexeme sharing a lemma or a string** (5 rows, and these are the ones that
   would have needed morphology to catch). `TMG-0216` RV 4.2.5 `gomāṃ agne vimāṃ aśvī
   yajñaḥ` — `aśvī` is NOM/**SG** of `aśvín-` as the adjective "horse-possessing", third in
   the series `gomān / avimān / aśvī` describing the sacrifice; the Aśvin twins are always
   dual (bug **B3**). `TMG-0248` `áditim` masculine, the adjective (bug **B3**).
   `TMG-0481` RV 1.121.2 `ṛbhuḥ` NOM/SG as an epithet of Indra, where the Ṛbhus are a
   plural triad. `TMG-0474` AVS 20.62.6 `viśvakarmā viśvadevo mahāṃ asi` — a predicate
   epithet of Indra. `TMG-0299` SV UTTARA 7.1.12.2 `agnir ṛṣiḥ pavamānaḥ pāñcajanyaḥ
   purohitaḥ` — `pavamānaḥ` is an adjective of **Agni** in a series of Agni epithets, but
   the edge asserts `VG:DEVATA:PAVAMANAH-SOMAH`. `theonyms.py` warns of exactly this for
   the Atharvaveda; it occurs in the Samaveda. **It occurs once in 89 SV Pavamāna edges**,
   so the per-form licence is doing its job and this is a residual, not a hole.
7. **The two attachment errors**, both `áp-`:
   - `TMG-0348` AVS 7.48.1 `sīvyatv apaḥ sūcyā achidyamānayā`. Whitney: "let her sew the
     WORK with a needle". `apaḥ` here is ACC/SG of `ápas-` n. "work", a different lexeme
     from `áp-` f. "water" sharing the surface string. The Rigvedic path gets the identical
     string right at RV 1.54.8 (`TMG-0073`, `apasā santu` = "through their work") and at
     RV 5.42.12 (`TMG-0162`, `apásaḥ` "the artisans"), because it lemmatises rather than
     matches.
   - `TMG-0420` SV CHANDA 4.2.1 `apo mahī vṛṇute cakṣuṣā tamo`. The Rigvedic parallel
     RV 7.81.1 reads `apo mahi vyayati cakṣase tamo` — `apa` is the **preverb** governing
     `vyayati`/`vṛṇute` "uncovers", and the object is `mahi tamaḥ` "the great darkness".
     There is no form of `áp-` in the verse. The Rigvedic path avoids the same trap at
     RV 8.18.9 (`TMG-0090`, `arapā apa sridhaḥ`).

**40 false negatives** (52 before the fix), classified mechanically by whether the deity's
registry forms match a whole printed token in that passage:

| mechanism | pre-fix | live |
|---|---|---|
| fused, elided or simply unlisted spelling | 23 | 23 |
| `DVANDVA_MEMBER` (a modelling choice, not a defect) | 13 | 13 |
| **`ACCEPTED_SANDHI_SV` gate** (bug **B1**) | 12 | **0 — fixed** |
| `DELIBERATE_EXCLUSION` (`MRTYUH` vocative-only; `CANDRAMAH` routed out) | 2 | 2 |
| RV lemma variant absent from the registry (bug **B2**, open) | 1 | 1 |
| compound member (`marutsakhā`) | 1 | 1 |

**Every one of the 12 rows the B1 classification predicted would recover, recovered, and
no others did.** The `SANDHI_ONLY_FORM_GATE` bucket went to zero and the other five
buckets are unchanged to the row. That is the validation: the gold set was frozen before
the fix existed, so the 12 rows were labelled without any knowledge of which mechanism
would later be repaired, and the mechanism turned out to partition them exactly.

The fused-spelling class is the Samavedic and Yajurvedic editions doing what
`theonyms.py` documents them as doing: `pratyagne` (SV CHANDA 1.10.5), `tvamagne`
(SV UTTARA 6.3.14.1, VSM 3.19), `adribudhnamagne` (VSM 13.42), `janitramagne` (VSM 13.50),
`ihaivāgne`/`kṣatramagne` (VSM 27.4), `stomamagnau` (VSM 15.25), `aśvinoruṣāḥ`
(SV UTTARA 8.3.6.2), `utāpaḥ` (VSM 20.19), `cāpo` (AVS 10.7.11). Each is a plain vocative
or dative to a major deity that a whole-token index cannot see. `agne` is 4 folded
characters, below `MIN_SANDHI_ALIAS_CHARS`, so the substring pass cannot reach it either:
**the most frequent vocative in the Veda is on neither path when it is printed fused.**
Two further rows are the reverse case, a multi-word name — `viśve devāḥ` printed as two
words where the registry holds only the single token `viśvedevāsaḥ` (SV ARANYA 3.9,
VSM 33.53).

**Nine false negatives are Rigvedic**, and seven of those are the dvandva class, one is
`marutsakhā`, and one is the genuine lemma-variant miss. Excluding the modelling classes,
**the Rigvedic path missed one mention in 103** in this sample (`TMG-0103`, bug **B2**'s
cousin: the lemma variant `pūṣáṇa-` at RV 10.93.4).

### Every metric with the 44 borderline rows removed (live)

| slice | precision | recall | F1 | n |
|---|---|---|---|---|
| overall | 0.8108 | 0.9317 | 0.8671 | 530 |
| `rv-lemma-annotation` | 0.8487 | **0.9902** | 0.9140 | 186 |
| surface | 0.7928 | 0.9045 | 0.8450 | 344 |

Removing the policy calls moves overall precision by +0.018 and Rigvedic recall from
0.9189 to 0.9902. The strict headline in §1 is therefore the conservative reading, and
the policy is not carrying the result.

### Unbiased precision is unchanged

The `*_uniform` strata (175 rows) score **0.8514** overall, **0.8909** on the annotation
path and **0.8333** on the surface path — identical to the pre-fix figures, because those
strata were drawn from edges that already existed and the fix only added edges. The
unbiased precision estimate is therefore not a before/after measurement, and the +0.0044
overall precision gain in §1 comes entirely from the negative strata.

---

## 6. Bugs found

**B1 is FIXED and validated. B2 through B7 are OPEN.** The gold set and this measurement
were produced without touching `theonyms.py`; the B1 fix was made afterwards by another
hand, and the numbers above are this gold set scoring it.

| | status |
|---|---|
| **B1** `ACCEPTED_SANDHI_SV` on no path outside the Samaveda | **FIXED, validated** |
| **B2** two `rv_lemma` values ASCII-flattened, match nothing | **OPEN** |
| **B3** lemma path ignores number and gender (`aśvín-`, `áditi-`) | **OPEN** |
| **B4** plurals asserted onto `structure: INDIVIDUAL` deities | **OPEN** |
| **B5** `occurrences` and roles wrong on the sandhi path | **OPEN** |
| **B6** surface-path roles record the Rigvedic paradigm, not the token | **OPEN** |
| **B7** `somapā-` accepted as a SOMAH form | **OPEN** (newly exposed by the B1 fix) |

### B1 — FIXED. `ACCEPTED_SANDHI_SV` forms were on no path at all outside the Samaveda. **877 predicted, 904 landed.**

`TheonymForm.admits_token` requires `decision ∈ {ACCEPTED_TOKEN,
ACCEPTED_TOKEN_AMBIGUOUS}`; `ACCEPTED_SANDHI_SV` is not in that set, so those 82 forms
reach the graph only through `_sandhi_hits`, which runs only when
`mantra.veda in form.sandhi_vedas` — normally `{"SV"}`. **A form accepted for the
Samavedic substring pass therefore cannot match even an exact whole token in the
Atharvaveda or Yajurveda.** The affected forms are the commonest nominal forms of the
biggest deities: `indraḥ`, `indram`, `indrasya`, `indrāya`, `indreṇa`, `indras`, `indraś`,
`savitā`, `aśvinā`, `aśvinor`, `bṛhaspatiḥ`, `viṣṇoḥ`, `agnaye`, `pavamānaḥ`, `ādityān`.

Mechanically measured over the whole corpus: **877 (passage, deity) pairs** where a whole
printed token is *exactly* a registry-accepted form of that deity and no edge exists,
across 35 (Veda, deity) cells.

| cell | missing | cell | missing |
|---|---|---|---|
| AV INDRAH | **313** | YV SAVITA | 42 |
| AV SAVITA | 73 | AV VARUNAH | 32 |
| AV ASVINAU | 60 | AV VISNUH | 28 |
| AV BRHASPATIH | 59 | AV SOMAH | 23 |
| YV INDRAH | 57 | AV TVASTA | 22 |

AV INDRAH had 322 edges; this one gate lost 313 more. Against 5,977 non-RV edges, 877
missing pairs was **a 14.7% under-count of the non-Rigvedic layer from a single
condition**, and it was invisible to any test that only checks the edges that exist.

**The fix.** `_ADMITS_TOKEN` now includes `ACCEPTED_SANDHI_SV` alongside
`ACCEPTED_TOKEN` and `ACCEPTED_TOKEN_AMBIGUOUS`. The entailment is that a form adjudicated
safe as a *substring* in the one corpus whose edition does not divide words reliably has
already passed a strictly harder test than matching as an exact whole token, where the
word boundary rules out host intrusion by construction. Admitting the weaker match while
refusing the stronger one was backwards. The sandhi path stays Samaveda-only: nothing
about *where a substring match is defensible* changed.

**Result.** 16,261 → **17,165 edges, +904** against a mechanical prediction of 877. The
27-edge excess is expected: the prediction counted (passage, deity) pairs reachable by an
exact whole-token match, while the rebuild also lets a newly-admitted form contribute to
pairs that another form already partly covered.

**Validation, and why it is unusually strong.** The gold set was frozen at 16,261 edges,
before this fix existed. Its labels are judgements about the *text* — whether a verse
refers to a deity — so they stayed valid across the rebuild, and the same 574 rows measure
both states. Scored live: **12 recovered true positives against 1 new false positive**,
recall 0.8514 → 0.8857, precision 0.7884 → 0.7928, F1 0.8187 → 0.8367. 10 of the 13 rows
are Atharvavedic and 3 Yajurvedic — precisely the corpora the condition could starve — and
no Rigvedic or Samavedic row moved. The 12 recovered rows are exactly the 12 the
pre-fix error classification had assigned to this mechanism, and no row from any other
bucket moved. A gold set that predates a fix and then partitions its effect to the row is
about as good a check as this project can get without a human annotator.

The recovered rows, for the record: `TMG-0003`/`TMG-0006` (AVS 6.58.1, 7.73.7, `devaḥ
savitā kṛṇotu` / `savitā sāviṣan`), `TMG-0005` (AVS 6.130.4, vocative `maruta`),
`TMG-0007`/`TMG-0021`/`TMG-0024`/`TMG-0117` (AVS 8.4.13, 20.34.7, 20.137.7, 20.34.12,
`indrasya` and `indraḥ` — including the refrain `sa janāsa indraḥ`), `TMG-0010`
(AVS 10.6.12, `bṛhaspatir`), `TMG-0014` (AVS 14.1.36, vocative dual `aśvinā`), `TMG-0054`/
`TMG-0067` (VSM 11.3, 35.3, `savitā`), `TMG-0063` (VSM 24.23, `agnaye`).

### B7 — OPEN. `somapā-` "soma-drinker" is an accepted SOMAH form. **22 non-RV edges.**

The single false positive the B1 fix introduced, `TMG-0022` (AVS 20.47.9), is not a fault
of the fix. `somapām indra sominaḥ sutāvanto havāmahe` — "we, having pressed soma, call on
Indra the SOMA-DRINKER". `somapā-` is a compound epithet of **Indra**; `soma` inside it
denotes the drink and the compound denotes Indra. It is nonetheless an accepted form of
`VG:DEVATA:SOMAH` in the registry, and once whole-token matching was opened it started
firing. Measured across the live graph, non-Rigvedic SOMAH edges resting on this family:
`somapā` 11, `somapāḥ` 5, `somapām` 4, `somapa` 2 — **22 edges**, and every one asserts
Soma on a verse that names Indra by an epithet.

This is a registry defect, not a matcher defect: the forms should be `REJECTED` with
`somapā-` named as the host, exactly as `tanūnapāt` and `ūrjo napāt` are named as hosts
for `APAM-NAPAT`. Note that the Rigvedic path already refuses it — the annotation
lemmatises `somapā́-` as its own stem, which is why §6's lemma-variant survey lists
`somapā` (27 tokens) among the correctly-unindexed compounds. The two paths now disagree
about the same word, and the annotated one is right.

### B2 — OPEN. Two registry `rv_lemma` values are ASCII-flattened and match nothing.

`VG:DEVATA:MRTYUH` carries `rv_lemma: mrtyu` (plain Latin `r`) while the annotation folds
`mṛtyú-` to `mtyu` with the `ṛ` sentinel; `VG:DEVATA:SRADDHA` carries
`rv_lemma: sraddha` against the annotation's `śraddhā`. Both are `LEMMA_ANNOTATION` and
both match **zero** of the annotation's 16 `mṛtyú-` and 19 `śraddhā́-` nominal tokens.
Both are `ACCEPTED_VOCATIVE_ONLY`, so the loss is the 1 vocative Mṛtyu passage
(RV 10.18.1, `pareta mṛtyo`) and the 3 vocative Śraddhā ones (RV 10.151). Small in count,
but this is why `VG:DEVATA:SRADDHA` is the one accepted deity with **zero edges anywhere
in the graph** — the layer's own report lists it under `deities_accepted_but_unused` and
the cause is a transliteration slip, not an absence in the corpus. The other 37 lemmas
carry their sentinels correctly, so this is a two-row data defect, checkable by asserting
that every `rv_lemma` matches at least one annotated nominal token.

### B3 — OPEN. The Rigvedic lemma path does not use number or gender, and two lemmas need it.

- `aśvín-` is both the Aśvin twins and the adjective "horse-possessing". **19 of 440
  Rigvedic ASVINAU passages rest only on non-dual tokens** (16 SG/M, 2 PL/M, 1 SG/N). The
  twins are always dual, so a non-dual token of `aśvín-` can never be them. `TMG-0216` is
  the sampled instance.
- `áditi-` is both the goddess and the adjective "unbounded". Aditi is feminine; the
  annotation carries exactly **1 masculine `áditi-` token**, and it is the false positive
  at `TMG-0248`.

Both are one-line filters on data the annotation already supplies. Note what this bug is
*not*: the annotation is not wrong, and the surface path gets `aśvinam` right (`TMG-0036`,
where the registry's rejection of the singular holds). The lemma path is the looser of the
two here, which is the reverse of the layer's design intent.

### B4 — OPEN. Plural forms are asserted onto `structure: INDIVIDUAL` deities.

**State this bluntly: 40 of 128 Rigvedic `VG:DEVATA:RUDRAH` passages — 31% — rest only on
plural `rudrá-` tokens and are asserting the wrong deity.** The node is
`structure: INDIVIDUAL` and its own description reads "the feared archer of the wilds,
**father of the Maruts**". A plural `rudrāḥ` denotes the Rudra troop, which is that god's
*sons*, not that god. The graph already distinguishes group deities from individuals —
`MARUTAH`, `ADITYAH` and `APAH` all carry `structure: GROUP` — so this is not a modelling
gap, it is a filter the layer does not apply. It is unaffected by the B1 fix: `RUDRAH`
scored precision 0.5833 before and after, and 5 of its 12 asserted rows in this sample are
this error (AVS 5.3.9, AVS 6.68.1, VSM 29.8, AVS 20.99.1, RV 5.87.7 — `ādityā rudrā
vasavaḥ` and `te rudrāsaḥ ... avantu`).

Adjacent and less clear-cut: 113 of 950 Rigvedic SOMAH passages rest only on plural
`sóma-` (the draughts) and 27 of 1,604 AGNIH passages only on plural `agní-` (the ritual
fires). Plural `uṣás-` (101 passages) is *not* a defect — the Rigveda routinely pluralises
the goddess Dawn. The distinction is whether the graph holds a separate node for the class,
and for Rudra it does.

### B5 — OPEN. `occurrences` and `morphological_roles` are wrong on the sandhi path.

`load_theonyms` appends to `index.sandhi` without de-duplicating on `(devata_id,
normalized)`, so 12 of 82 entries are duplicates — `VG:DEVATA:ASVINAU` alone has **six
entries whose folded string is identical** (`aśvinā`, `aśvínā`, `áśvinā`, … all fold to
one string). `_sandhi_hits` then calls `_Occurrence.add` once per entry, so one textual
word yields `occurrences = 6`. At SV CHANDA 2.8.10 the text is `uta svarājo aśvinā` — one
word — and the edge records `occurrences = 6` and
`morphological_roles = [ACCUSATIVE, INSTRUMENTAL, NOMINATIVE, VOCATIVE]`, the union of six
unrelated paradigm labels. Measured: **15 of 249 sandhi edges over-count `occurrences`**
and **54 of 249 carry more than one role** for what is usually a single token. A nested
spelling (`indraṃ` inside a longer accepted string) does the same without needing an exact
duplicate.

### B6 — OPEN. Surface-path `morphological_roles` records the Rigvedic paradigm, not the token.

`_surface_hits` copies `form.morphological_role` — a label taken from the *Rigvedic*
paradigm of that spelling — onto a Samavedic, Yajurvedic or Atharvavedic token. For a
thematic a-stem the vocative singular and the sandhi-reduced nominative singular are the
same string, so the label is frequently false: `mitra īkṣamāṇaḥ` (AVS 9.7.23) is
`mitraḥ` + `īkṣamāṇaḥ`, a nominative, recorded `VOCATIVE`; `soma āha` (SV UTTARA 9.2.6.1)
is `somaḥ` + `āha`, recorded `VOCATIVE`; `amṛtaḥ soma induḥ` (VSM 19.95) is nominative,
recorded `VOCATIVE`; `uṣasaḥ` ACC/PL at AVS 7.22.2 is recorded `VOCATIVE`; `indrā yāhi`
(AVS 20.84.2, SV UTTARA 4.2.5.2) is a metrically lengthened vocative singular, recorded
`DUAL`; `rudrā` and `ādityā` NOM/PL are recorded `DUAL`; `tisro vācaḥ` NOM/PL is recorded
`GENITIVE`; `uṣasām idhānaḥ` (VSM 12.22), two words the edition joins, is recorded
`COMPOUND_INITIAL`; `mitram iva`, likewise, `COMPOUND_INITIAL`.

**1,501 of 5,977 surface-path edges carry `VOCATIVE` among their roles** (AV 811, SV 418,
YV 272). `theonyms.py` is explicit that it does not grant *certainty* from those labels,
and §4 confirms the certainty grading is sound — so this is not a precision bug. It is a
data-quality bug in a published field: any consumer that reads
`morphological_roles` outside the Rigveda is reading the registry's paradigm guess, not
the text. The field should be null, or renamed, outside the annotated corpus.

### Two non-defects worth recording as measurements

**The Rigvedic path's specificity against host intrusion is total.** 1,174 nominal tokens
across 1,092 Rigvedic passages carry a lemma within one character of a theonym lemma —
`stóma-` beside `sóma-` (210 tokens), `citrá-` beside `mitrá-` (147), `mánu-` beside
`manyú-` (73), `dáma-` beside `yamá-` (51), `avitár-` beside `savitár-` (46), `aruṇá-`
beside `váruṇa-` (35). The annotation path ignores every one. **31 of the 35 `N2` rows are
true negatives** — the other four are the dvandva class and the lemma variant, not host
intrusion — on strings like `aryamaṇam` (Aryaman, containing `yama`), `jamadagnayaḥ`
(Jamadagni, containing `agna`), `amítra-` "enemy", `arvāñc-` containing `vāk`, `tvāyú-`
containing `vāyu`, and the *verb* `yamam` "I brandished", which the part-of-speech tagging
keeps out. **Not one `N2` row is a host-intrusion false negative or false positive.** This
is the layer's central design claim and it is now measured rather than asserted. The `N3`
host stratum adds 26 true negatives in 35 rows; its nine positives are all dvandva members
or B1 misses, never a mis-rejected host.

**The structural refusals are correct.** 23 of 24 `N5` rows and 29 of 30 `N4`
rejected-form rows scored as the registry predicted: `ratham` is a vehicle at RV 1.49.2,
4.36.1, 8.9.8 and 10.39.4; `katamaḥ`/`kim` is interrogative at AVS 10.7.19 and RV 9.69.6;
`harivas`/`haribhyām` are Indra's bay horses; `aśvasya retaḥ` is the aśvamedha stallion;
`devāḥ` is the generic class term; `savitave` at AVS 6.17.1 is an infinitive of `sū-` "to
give birth" and not Savitṛ; `tanūnapāt` and `ūrjo napāt` are Agni epithets and not Apāṃ
Napāt; `apásaḥ` is "artisans". The `mislabelled_passages_avoided` counts in the registry
(3,656 for `KAH`, 3,652 for `DEVAH`, 2,122 for `HARIH`, 1,297 for `RATHAH`) are earned.
The two exceptions are not mis-rejections: `TMG-0170` (VSM 20.19) is a genuine Waters
mention the layer loses through a *different*, fused spelling, and `TMG-0175`
(AVS 14.1.24, vocative `candramas`) is the deliberate `CANDRAMAH` exclusion.

### One modelling question, not a bug

**13 false negatives are dvandva members.** `indravāyū` names Indra, `dyāvāpṛthivī` names
Pṛthivī, `mitrāvaruṇā` names Mitra — and the layer routes each to its own dual-deity node
(`INDRAVAYU`, `DYAVAPRTHIVYAU`, `MITRAVARUNAU`) and emits no member edge. Whether "does
this verse name Indra?" should be true of `indravāyū` is a decision about the graph, not a
fact about the Sanskrit, so those rows are flagged `borderline` and §5 gives the numbers
without them. If the answer is "yes", this is the largest remaining recall gap after B1.

---

## 7. What this gold set does **not** cover

- **It is not human-reviewed.** Every label is one model's reading. On the classes where
  the Sanskrit is unambiguous (vocatives, god-lists, explicit `devī`) that is unlikely to
  matter; on the 44 borderline rows it matters a great deal, and a second independent
  adjudicator would very likely disagree with some of them. There is no inter-annotator
  agreement figure because there is only one annotator. **Nothing here should be quoted as
  a scholarly result.**
- **Corpus-level recall is not estimated from the sample.** The negative strata were drawn
  from probe pools chosen to be likely misses, so the 0.8857 recall figure describes the
  sample, not the corpus. The one whole-corpus recall statement this report could make
  mechanically was B1's 877 pairs, and that defect is now fixed. **No mechanical bound
  exists for the recall that remains** — 23 of the 40 surviving false negatives are
  fused, elided or unlisted spellings, and nothing here sizes that class over the whole
  corpus. It is very likely the largest remaining recall defect, and it is unmeasured.
- **No per-Veda precision on the sandhi path.** All 249 sandhi edges are Samavedic and only
  30 were sampled; the 0.9667 figure rests on 30 rows and its interval runs to 0.83.
- **29 of 49 sampled deities have no per-deity figure**, including Varuṇa, Viṣṇu, Aditi,
  Tvaṣṭṛ and the Ādityas. Sizing the remaining deities to n ≥ 8 each would need roughly
  200 more rows.
- **`AGNIH` recall is measured only where a probe stem hit.** Agni is the most fused-in-print
  deity in the corpus and the 10 sampled Agni false negatives are all fused vocatives; the
  true Agni recall loss is not bounded here.
- **Only 8 rows test `RATHAH` and 3 test `KAH`**, so the refusal classes are confirmed but
  not tightly bounded. All 11 scored as the registry predicts.
- **No `Devata` node coverage claim.** 43 deities are accepted in the registry and 42 appear
  in the graph; the gold set says nothing about deities the *registry* omits entirely, which
  is a different question (recall against the Anukramaṇī's devata vocabulary) and a
  different measurement.
- **`attribution_support` is untested.** The gold set records it per row but never scores
  it; whether the Anukramaṇī signal predicts correctness is a separate question this set
  could answer and this report does not.
- **The gold set's `graph_asserts` column is now historical.** It records what the layer
  claimed at 16,261 edges and is deliberately left frozen; the evaluator recomputes the
  column from the live graph on every run and reads past it. So the file no longer
  describes the current graph, only the current *text*, which is the half of it that was
  ever meant to be durable. `--frozen` scores the historical column.
- **The 13 rows the fix moved carry stale edge properties.** `refresh_from_live` recomputes
  edge existence but not `extraction_path`, `referent_certainty`, `quality_tier` or
  `matched_forms`, so those 13 rows are absent from the per-path and per-certainty
  breakdowns unless queried directly (§4 does query them). A second freeze of the gold set
  would fix this; re-freezing it now would destroy the before/after comparison, which is
  worth more.
- **Nothing here re-measures the layer after B2–B7 are fixed.** The B1 validation shows the
  gold set can score a fix it predates, so the same 574 rows will serve for those too, but
  each fix moves the graph and the numbers in this report describe the graph at 17,165
  edges only.

---

## 8. Reproducing

```
.venv/Scripts/python.exe scripts/evaluate_theonym_gold.py                    # live: the §1 headline
.venv/Scripts/python.exe scripts/evaluate_theonym_gold.py --frozen           # the pre-fix column
.venv/Scripts/python.exe scripts/evaluate_theonym_gold.py --no-graph         # no database needed
.venv/Scripts/python.exe -m pytest tests/unit/test_theonym_gold_evaluation.py
```

**Live is the default and `--frozen` is the opt-out.** That is the right way round and it
was not how this evaluator originally worked: it scored the frozen `graph_asserts` column
and merely *warned* that rows had drifted. On the first post-fix run that produced a
headline which did not move at all beside a quiet note that 13 rows disagreed — a stale
number with a footnote, which a reader would reasonably have taken as current. A warning
next to a wrong headline is not a safeguard. The invariant that makes live-by-default safe
is the one `refresh_from_live` documents: `gold_label` is a judgement about the text and
never goes stale, `graph_asserts` is a snapshot of the layer and goes stale immediately, so
only the second is recomputed.

The evaluator is read-only on the database and on every existing data file, and the gold
file is unmodified since freezing. 27 tests cover the metric arithmetic on hand-built
fixtures — including that an undefined rate returns `None` and never `0.0` — and the gold
file's schema, among them a test that `load_gold` raises if any row claims
`HUMAN_REVIEWED`. `ruff check` and `mypy --strict` are clean.
