# Semantic resemblance — a layer that ships one tier and refuses two

Agent 11 of the Post-V1 Data Completeness Campaign, Wave 2. Owner's section L: *do not
deploy a generic embedding model without evaluation.* Fourteen candidate representations
were compared against one adjudicated sample before any relation was written, and the
three findings that matter most are all negative results about candidates and filters that
lost.

- Measured: 2026-09-15
- Branch `phase-data-completeness-v2`, code commit `10dd879`
- Graph access: `MATCH` / `RETURN` only, through a keyword guard that raises on
  `CREATE` / `MERGE` / `SET` / `DELETE` / `REMOVE` / `DROP`
- Graph at start and at end: **108,779 nodes / 265,295 relationships** — unchanged,
  re-counted, and matching `WAVE_1_CLOSURE.md` exactly. No canonical write occurred.
- Write surface used: `data/staging/semantic_resemblance/` and this file. Nothing else.

**Headline.** A new non-lexical predicate, `THEMATICALLY_RESEMBLES`, over **43,006
symmetric edges on 19,088 mantras**. Of those, **26,953 are importable** at a measured
test precision of **0.955 on 22 gold pairs, 95% CI [0.782, 0.992]**; **16,053 are staged
and not importable** at **0.615 on 13 pairs, CI [0.355, 0.823]**; and a third population of
**138,054 candidate pairs is refused outright** because the evidence that defends the
predicate does not exist in comparable form for them. No human has looked at any of it.

---

## 1. Three things that were inherited, and what verifying them cost

A previous run of this domain left `data/staging/semantic_resemblance/proofs/` — an empty
directory — plus a report on disk and, in the session scratch, its full working set:
a 20,210-row corpus dump, four ONNX embedding matrices, a 1.1-million-pair candidate pool
with scores, a 486-pair sample and 324 LLM adjudications. That is a great deal of
salvageable work and it was salvaged. It was also wrong in one place that would have
invalidated every per-pair number in this report.

| Inherited artifact | Check | Result |
|---|---|---|
| graph state | re-count nodes and relationships | 108,779 / 265,295 — matches Wave 1 |
| `SHARES_ENTITY_VOCABULARY_WITH` veda-pair split | recomputed | AV-RV 1,176, RV-SV 421, RV-YV 291, AV-YV 136, AV-SV 84, SV-YV 33, **within one Veda 0** — reproduces |
| vector indexes | `SHOW INDEXES` | 84 `RANGE`, 2 `FULLTEXT`, 2 `LOOKUP`, **0 `VECTOR`** — reproduces |
| Sanskrit text dump | seeded 400-key re-read of `TextVersion.text_nfc` at the recorded `text_role` | **400 of 400 string-identical** |
| translation dump | same 400 keys against `Translation` at `alignment_level: MANTRA` | **0 mismatches** |
| the 31 misaligned RV translations | re-read `rv_coordinate_repair/repair_table.jsonl` by key | 25 `MISATTACHED` + 6 `CORRECT_UNIT_UNDECLARED_SCOPE`, **0 leaked** into any translation channel |
| four embedding matrices | re-encode a seeded 300-row sample and compare | min cosine to stored **1.000000** on all four; they still describe the current corpus |
| **`pool_scores.npz`** | length against `pool.npy` | **1,133,112 against 1,133,311 — misaligned** |

### 1.1 The inherited pair scores were aligned to a pool that no longer existed

The previous run rebuilt its corpus at 14:55, re-encoded the Sanskrit through to 15:06, and
regenerated the candidate pool at 15:08 — but never re-ran the pair scorer, which last ran
at 14:34. So the score arrays on disk were 199 pairs shorter than the pool and, past the
first divergence, positionally attached to the wrong pairs.

| candidate | positions compared | differing | max abs diff |
|---|--:|--:|--:|
| `C_LEXICAL_CHAR4` | 1,133,112 | 1,037,092 | 1.0000 |
| `R4_FRAME_IDF` | 1,133,112 | 912,336 | 1.0000 |
| `R6_E5_SANSKRIT_CENTRED` | 1,133,112 | 1,133,049 | 1.2921 |
| `R2_ENTITY_IDF` | 1,133,112 | 749,667 | 1.0000 |

Every per-pair figure would have been noise. The aggregate, however, barely moved:
`R6_E5_SANSKRIT` at cosine ≥ 0.8 read 1,133,101 on the stale file and reads 1,133,302 on
the correct one. **An aggregate survived a defect that destroyed every row underneath it**,
which is why the length check and not the plausibility of the table is what caught it. All
scores here are recomputed; the stale file is kept in `proofs/` as the evidence.

One inherited figure is also corrected: `C_LEXICAL_CHAR4` has **94,040** dimensions on the
current corpus, not the 91,738 the previous report recorded from a superseded build.

### 1.2 One inherited claim retracted

The previous report called `SHARES_FORMULA_WITH`'s zero "an empty declaration" and "a
correction nobody had recorded." Agent 10 is right and that reading is wrong. The rationale
**is** recorded, as data rather than prose, at
`src/vedagraph/enrich/predicates.py::UNPOPULATED_BY_DESIGN`: the `Formula` hub carries the
relation losslessly in two hops, the largest formula spans 93 passages, and materialising
it would add 87,296 edges where the layer currently adds 27,511. The count was right, the
reading was not, and the retraction is recorded here so the same zero is not rediscovered
a third time.

---

## 2. Where this layer had to fit

`GAP-SEMANTICS-006` is real: of 66 relationship types, none is a resemblance predicate,
there is no `RELATED_TO`, and there are zero vector indexes. But the shape of the absence
matters more than its existence. `SHARES_ENTITY_VOCABULARY_WITH`, the nearest neighbour of
this layer, holds 2,141 edges and **every single one crosses a Veda boundary**. Within one
Veda the graph has no relatedness predicate except textual parallelism. A reader asking
"what else in the Rigveda says this" had exactly one instrument, and it answered on wording.

Four measurements of the graph's own semantic layers shaped the design, and each is a
finding in its own right:

- **The graph's lemma layer is a theonym index.** `MENTIONS_LEMMA` reaches 39 distinct
  lemmas and all 39 are deity names, over 6,560 Rigvedic mantras; 9,992 of 10,031 `:Lemma`
  nodes carry no mantra edge. The real morphology — 164,758 tokens over 9,785 lemmas
  covering all 10,552 Rigvedic mantras, the Zurich/VedaWeb annotation — sits in
  `data/knowledge/rigveda_lexical_v1/tokens.jsonl` and was never projected. `R1` below is
  built from the file, not the graph.
- **`ABOUT_CONCEPT` is `MENTIONS_ENTITY` under a second name**: 24,905 of 24,969
  (mantra, label) pairs identical. Treating them as two signals double-weights one.
- **The entity layer is a controlled-vocabulary *lexical* layer.** All 28,227 mention edges
  were written by `domain-mention-v1:sanskrit-token` (27,713) or `:sanskrit-sandhi` (514).
  It is a dictionary match on the Sanskrit surface — better than raw characters, not
  independent of wording.
- **The mention layers collapse sense rather than disambiguating it.** Of 302 mantras where
  `MENTIONS_DEVATA` fires on *vāc*, **81.5%** also carry the thing-sense entity
  `speech (vāc)`; for *soma* it is **50.2%** of 1,618. So the deity-mention layer cannot
  serve as referent evidence for exactly the words the adversarial set is built on. It is
  the trap, not the defence.

The defence that does exist is **dedication** — `HAS_DEVATA` (RV, 10,552 of 10,552) and
`HAS_DEVATA_ASCRIPTION` (AV, 4,160 of 5,839), from the Anukramaṇī, naming the deity a hymn
is *addressed to* independently of the words in the verse. The Samaveda and Yajurveda have
none. That single fact ends up bounding this entire layer, and §7 is about it.

---

## 3. Fourteen candidate representations, compared before anything was written

Each is an L2-normalised vector space over all 20,210 mantras, scored by cosine.
`C_LEXICAL_CHAR4` is a **control**, not a candidate: it exists so that lexical similarity
can be measured and excluded rather than assumed absent.

| id | what it is | dims | mantras populated |
|---|---|--:|--:|
| `R1_LEMMA_TFIDF` | Zurich/VedaWeb Sanskrit content lemmas, sublinear TF-IDF | 4,893 | 10,552 (RV only) |
| `R2_ENTITY_IDF` | entity + theonym mention sets, IDF-weighted | 259 | 17,540 |
| `R3_TRANSLATION_TFIDF` | English content words, translator-habit stoplist applied | 9,209 | 17,091 |
| `R3b_TRANSLATION_RAW` | same, habit words kept — the ablation's other arm | 9,248 | 17,093 |
| `R4_FRAME_IDF` | typed frame: dedication, assertion predicates, typed relations, classes | 913 | 19,284 |
| `R5_MULTILING_SANSKRIT` (+ centred) | `paraphrase-multilingual-MiniLM-L12-v2` on the Sanskrit | 384 | 20,210 |
| `R6_E5_SANSKRIT` (+ centred) | `multilingual-e5-small` on the same Sanskrit | 384 | 20,210 |
| `R7_E5_TRANSLATION` (+ centred) | `multilingual-e5-small` on the English | 384 | 17,094 |
| `R8_ENMINI_TRANSLATION` (+ centred) | `all-MiniLM-L6-v2` on the English | 384 | 17,094 |
| `C_LEXICAL_CHAR4` *(control)* | character 4-grams of the unaccented Devanagari | 94,040 | 20,210 |

`R6` and `R7` are one encoder on two channels, which is the controlled comparison the
translation ablation needs. Weights are public ONNX exports, checksummed in
`sources.jsonl`, installed into a throwaway directory: `pyproject.toml` is inside the
semantic seal and was not touched, and `.venv` still has no `numpy`.

Usable mantra-aligned translations, after excluding the 31 misaligned and the 158
hymn-level-only Rigvedic keys: **RV 10,313 + YV 1,903 + AV 4,878 = 17,094 of 20,210.**
The live graph holds **zero** Samavedic translations.

### 3.1 Raw cosine from these encoders cannot carry a threshold

Pairs at or above a threshold, out of the 1,133,311-pair candidate pool:

| candidate | ≥0.3 | ≥0.5 | ≥0.7 | ≥0.8 | ≥0.9 |
|---|--:|--:|--:|--:|--:|
| `R6_E5_SANSKRIT` | 1,133,311 | 1,133,311 | 1,133,311 | **1,133,302** | 670,943 |
| `R6_…_CENTRED` | 246,604 | 30,642 | 7,748 | **5,663** | 3,561 |
| `R7_E5_TRANSLATION` | 959,448 | 959,448 | 959,448 | **942,035** | 100,631 |
| `R7_…_CENTRED` | 191,720 | 14,135 | 2,718 | **1,594** | 783 |
| `R5_MULTILING_SANSKRIT` | 1,092,197 | 934,050 | 609,181 | 394,142 | 163,403 |
| `R5_…_CENTRED` | 449,554 | 302,037 | 114,761 | 53,529 | 18,655 |
| `R8_ENMINI_TRANSLATION` | 779,110 | 315,281 | 18,531 | 2,260 | 1,044 |
| `R2_ENTITY_IDF` | 380,574 | 259,536 | 162,559 | 111,508 | 87,504 |
| `R4_FRAME_IDF` | 411,905 | 264,438 | 168,343 | 124,918 | 81,927 |
| `R1_LEMMA_TFIDF` | 17,099 | 1,202 | 418 | 306 | 261 |
| `R3_TRANSLATION_TFIDF` | 17,370 | 3,855 | 2,136 | 1,472 | 755 |
| `C_LEXICAL_CHAR4` *(control)* | 13,110 | 8,909 | 5,911 | 4,073 | 2,289 |

**A cosine of 0.8 on raw `multilingual-e5-small` selects 1,133,302 of 1,133,311 pool
pairs.** Deployed at the threshold an engineer would reach for, that model asserts that
every Vedic verse resembles every other. Centring moves the same threshold by a factor of
200. `R2` and `R4` fail in the opposite direction — at 259 and 913 dimensions they
saturate, with 87,504 and 81,927 pairs at cosine ≥ 0.9.

### 3.2 Sanskrit is not what these encoders were trained on

Subword tokens per whitespace word, over a seeded 400-mantra sample: the two XLM-R
vocabulary models produce **2.66** subwords per Vedic word against 1.71 on the English
gloss, and `all-MiniLM-L6-v2`'s English BERT vocabulary produces **3.48**. No
Sanskrit-trained sentence encoder with an ONNX export was found. "Sanskrit-compatible
embeddings" is recorded as **not viable from public artifacts at this time** rather than
approximated and presented as though it were.

### 3.3 How each candidate scored against the adjudicated sample

AUC, positive class = `SAME_CONTENT` ∪ `SAME_TOPIC_DIFFERENT_CLAIM`. Dev chooses,
test reports, nothing is tuned on test.

| candidate | AUC dev | AUC test | P.test | R.test |
|---|--:|--:|--:|--:|
| **`C_LEXICAL_CHAR4` — the control** | **0.8090** | **0.7445** | 0.700 | 0.857 |
| `R4_FRAME_IDF` | 0.8028 | 0.7357 | 0.678 | 0.816 |
| `R6_E5_SANSKRIT_CENTRED` | 0.7405 | 0.7215 | 0.692 | 0.755 |
| `R6_E5_SANSKRIT` | 0.7371 | 0.7067 | 0.646 | 0.837 |
| `R7_E5_TRANSLATION_CENTRED` | 0.6379 | 0.6810 | 0.642 | 0.969 |
| `R8_ENMINI_TRANSLATION_CENTRED` | 0.6452 | 0.6687 | 0.640 | 0.959 |
| `R2_ENTITY_IDF` | 0.7464 | 0.6627 | 0.683 | 0.704 |
| `R3_TRANSLATION_TFIDF` | 0.6078 | 0.6379 | 0.587 | 1.000 |
| `R5_MULTILING_SANSKRIT_CENTRED` | 0.5891 | 0.6356 | 0.588 | 0.918 |
| `R7_E5_TRANSLATION` | 0.5839 | 0.6345 | 0.587 | 1.000 |
| `R3b_TRANSLATION_RAW` | 0.6066 | 0.6190 | 0.587 | 1.000 |
| `R8_ENMINI_TRANSLATION` | 0.6009 | 0.6091 | 0.587 | 1.000 |
| `R5_MULTILING_SANSKRIT` | 0.6002 | 0.5944 | 0.586 | 0.939 |
| `R1_LEMMA_TFIDF` | 0.5832 | 0.5769 | 0.587 | 1.000 |

**The lexical control has the highest AUC of all fourteen, on both splits.** Character
4-grams of the Devanagari beat every semantic representation, including the scholarly
lemma layer and all six sentence-encoder variants. That single row decided what the rest of
this report had to be: a layer cannot be called semantic until it is shown to add something
over that control, and §5 is that test.

A second consequence: the candidates disagree about who each verse's nearest neighbour is.
`R1_LEMMA_TFIDF` and `R5_MULTILING_SANSKRIT` agree on the rank-1 neighbour of **264 of
20,210** mantras (1.3%); `R2_ENTITY_IDF` and `R4_FRAME_IDF` agree on 2,620 (13.0%).
The choice of representation is not a detail, and no candidate can be ground truth for
another.

### 3.4 The hybrid, and a channel choice made against the numbers

Greedy forward selection on dev AUC, with the control excluded by name:

| step | added | dev AUC |
|---|---|--:|
| 1 | `R4_FRAME_IDF` | 0.8028 |
| 2 | `R6_E5_SANSKRIT` | 0.8247 |
| 3 | `R8_ENMINI_TRANSLATION_CENTRED` | 0.8398 |
| 4 | `R2_ENTITY_IDF` | 0.8546 |

| hybrid | AUC dev | AUC test |
|---|--:|--:|
| greedy four-channel | 0.8546 | **0.8228** |
| translation-free three — **the predicate** | 0.8340 | 0.7737 |

**The predicate is defined on the translation-free three, which score 0.049 AUC worse on
test.** The reason is structural and was fixed before these numbers were read: the live
graph holds zero Samavedic translations, so a translation channel leaves an entire Veda
unscoreable on the channel that defines the predicate; and Wave 3 may import 173 Samavedic
translations that are Griffith's *Rigveda* renderings used cross-corpus, which would make
every RV-SV translation-channel score circular by construction. The translation-channel
score is carried on every emitted edge as
`translation_channel_z_not_used_in_the_predicate`, so the decision is auditable and
reversible rather than hidden.

---

## 4. The adjudicated sample: what it is, and what it is not

- **486 pairs**, stratified per representation across rank-1 / rank-2-3 / rank-4-10 bands,
  plus a 30-pair uniform-random stratum for the base rate, plus the whole 172-case
  adversarial set.
- **324 adjudicated** by `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter, at
  temperature 0, in 29 batched calls of 12.
- **162 typed `UNADJUDICATED_QUOTA_EXHAUSTED`** in the row. The provider's daily allowance
  was exhausted mid-run and was **not retried in a loop**. One single availability probe
  this session returned `daily_exhausted: true` again, and that is the total additional
  spend: **30 calls in this domain, all recorded.**
- **There is no human gold here or anywhere in this project.** 0 of 43,006 edges, 0 of 324
  labels, 0 of 172 adversarial cases were checked by a person. Section 22 is not satisfied
  and nothing in the artifact claims it is.

| label | count | role |
|---|--:|---|
| `SAME_CONTENT` | 50 | positive |
| `SAME_TOPIC_DIFFERENT_CLAIM` | 138 | positive — the class this layer is for |
| `SHARED_PHRASING_ONLY` | 8 | negative — the lexical trap |
| `UNRELATED` | 128 | negative |

The 30-pair uniform-random stratum gives the base rate: **18 `UNRELATED`, 2
`SAME_TOPIC_DIFFERENT_CLAIM`** among the 20 that were adjudicated. So roughly one random
pair in ten shares a topic — the corpus is formulaic, and precision figures must be read
against that floor rather than against zero.

### 4.1 Evaluation independence, stated precisely rather than claimed

| who | did what |
|---|---|
| deterministic code (no model) | `R1`–`R4`, `C_LEXICAL_CHAR4` |
| three public ONNX encoders | `R5`–`R8`; each ran inference only and labelled nothing |
| `nvidia/nemotron-3-ultra-550b-a55b` | the gold labels. **Built none of the representations.** |
| `claude-opus-5` (this agent) | wrote the pipeline; second-opinion labels on 26 pairs |

The primary adjudicator is fully independent of every representation. The second opinion is
**not**: the same model family authored the code that builds them, so it is a check on the
labels and not an independent validation of the layer. It was taken blind — all 26
judgements were written before the first adjudicator's labels were revealed.

### 4.2 Inter-adjudicator agreement, and the boundary that is not reproducible

| measure | value |
|---|--:|
| four-way agreement, stratified sample | 18 of 26 (0.692), Cohen's κ **0.567** |
| binary positive/negative agreement | 18 of 26 (0.692), Cohen's κ **0.366** |
| population-reweighted agreement | **0.770** |

Per label, the picture is sharp:

| adjudicator 1's label | sampled | in population | agreement |
|---|--:|--:|--:|
| `SAME_CONTENT` | 6 | 50 | **1.000** |
| `SAME_TOPIC_DIFFERENT_CLAIM` | 8 | 138 | 0.750 |
| `UNRELATED` | 8 | 128 | 0.750 |
| `SHARED_PHRASING_ONLY` | 4 | 8 | **0.000** |

The two adjudicators agree on every `SAME_CONTENT` pair and disagree on every
`SHARED_PHRASING_ONLY` pair. **The one label boundary that is not reproducible is exactly
the boundary this layer sits on** — shared-phrasing negative against same-topic positive.
The raw binary κ of 0.366 is depressed by the stratification, which deliberately drew 15.4%
of the sample from a class that is 2.5% of the population; reweighted agreement is 0.770.
Either way, every precision figure below carries adjudicator-specific variance that no
confidence interval computed on the labels can express.

---

## 5. The seven attacks, including the ones that came back clean

### Attack 3 — lexical leakage. **The most serious, and it is survived, not dismissed.**

Assertion declared before the test: *if this layer is semantic, the hybrid residualised
against the lexical control must still separate the classes — residual AUC strictly above
0.5. If it falls to 0.5, the layer is lexical similarity under a semantic name.*

| measurement | value |
|---|--:|
| Pearson, hybrid against the control, on the gold sample | 0.7562 |
| Pearson, **on the full 1.13M pool** | 0.3874 |
| AUC, hybrid | 0.8377 |
| AUC, control alone | 0.7758 |
| **AUC, hybrid residualised on the control** | **0.7371** |
| AUC, control residualised on the hybrid | **0.4025** |

The assertion held. And the second-to-last pair of rows is the stronger result: once the
hybrid is known the control carries no additional positive signal at all (0.4025, below
chance), while once the control is known the hybrid still separates at 0.7371. The hybrid
subsumes the control; the reverse is false.

The product question is sharper still — does it work where wording does *not* overlap?

| subset of the adjudicated sample | n | positives | AUC hybrid | AUC control | AUC `R4_FRAME_IDF` |
|---|--:|--:|--:|--:|--:|
| lexical cosine **< 0.10** | 231 | 111 | **0.8161** | 0.7209 | 0.7663 |
| lexical cosine < 0.20 | 257 | 127 | 0.8068 | 0.7044 | 0.7658 |
| lexical cosine **≥ 0.20** | 67 | 61 | **0.5738** | 0.7541 | 0.4413 |

Read the last row carefully. Above a lexical cosine of 0.20, 61 of 67 pairs are positive —
there is almost nothing left to discriminate, the semantic signal collapses to 0.574, and
the typed frame goes *below* chance at 0.441. Below 0.10, where 71% of the sample lives,
the hybrid is at 0.816 and the control at 0.721. **The layer's value is entirely in the
low-lexical-overlap region, and the high-overlap region is already somebody else's fact.**
That is why a lexical ceiling of 0.20 is part of the predicate's definition rather than a
tuning knob.

Per channel, correlation with the control over the full pool: `R6_E5_SANSKRIT_CENTRED`
0.427, `R3b_TRANSLATION_RAW` 0.385, `R6_E5_SANSKRIT` 0.385, `R2_ENTITY_IDF` 0.182,
`R4_FRAME_IDF` **0.154**, `R7_E5_TRANSLATION` −0.020. The typed frame is the least lexical
thing in the hybrid and also its single strongest channel.

**A caveat this attack found in my own comparison surface.** Agent 10 reported that the
Vājasaneyi anusvāra cluster and the candrabindu survive a cross-script fold. My surface
transliterates RV/AV from Latin to Devanagari and leaves SV/YV in Devanagari, so any Vedic
sign not in the tone list survives on the SV/YV side with no counterpart on the other.
Predicted blast radius: confined to SV and YV, zero in RV and AV. Measured: **780 YV verses
carry U+1CEA + U+1CED, 141 carry U+0901 candrabindu, 873 YV verses (44.2%) and 3 SV verses
in total, and 0 in RV and AV.** The prediction held, and it reproduces agent 10's 780
exactly. The lexical *control* is therefore misaligned on 873 Yajurvedic verses. Does the
leakage finding depend on it? Excluding every Yajurvedic endpoint: hybrid AUC **0.8447**,
control 0.784 — the finding is if anything stronger without them. Clean.

### Attack 1 — translation circularity. **Clean, and the ablation is the reason.**

Assertion declared before the test: *if the English channels measure shared meaning rather
than shared translator, one encoder run on the Sanskrit and on the English must agree above
chance, and removing the translator's habit words must not raise AUC.*

| measurement | value |
|---|--:|
| `R6_E5_SANSKRIT` AUC | 0.7195 |
| `R7_E5_TRANSLATION` AUC — same encoder, English channel | 0.6085 |
| **Spearman between the two, on the gold sample** | **0.1039** |
| Spearman between the two, on the pool | **0.0570** |
| `R3` (habit words removed) AUC | 0.6209 |
| `R3b` (habit words kept) AUC | 0.6121 |
| AUC gained by removing 60 habit words | **+0.0088** |

One encoder reading a verse and reading its own English gloss produces **almost
uncorrelated orderings** (ρ = 0.057 over a million pairs). The English channel is not a
proxy for the Sanskrit, and whichever you pick changes the answer for most verses. And the
translator-habit stoplist — the obvious defence — is worth 0.009 AUC. The circularity is
not in Griffith's sixty favourite words.

Where the confound is real is in the population, not the scorer:

| | n | positive rate | AUC hybrid | AUC `R7` |
|---|--:|--:|--:|--:|
| same translator on both sides | 185 | **0.6054** | 0.7798 | 0.7298 |
| different translators | 78 | **0.3718** | **0.8557** | 0.8023 |

Same-translator pairs are 1.63× more likely to be adjudicated positive — but the scorer
discriminates *worse* on them, not better. In this corpus "same translator" is very nearly
"same Veda" (Griffith the RV and YV, Whitney the AV), so the elevated positive rate is
corpus structure, not phrasing habit.

**The decisive ablation:** the translation-free hybrid scores **0.803** against the full
hybrid's **0.8377** on the adjudicated sample. The layer works without any translation at
all, and it is the translation-free version that ships. The adjudicator's own self-report
agrees: it judged 177 of 324 pairs on the Sanskrit alone, 112 on both, 35 on the English,
and marked only 5 pairs "phrasing-driven" — **of which 0 were labelled positive.**

### Attack 2 — duplicate translations. **Clean, and mostly by exclusion.**

| measurement | value |
|---|--:|
| 31 known-bad RV 1.65–1.70 translations | excluded by key, 0 leaked (verified) |
| 158 hymn-level-only RV translations | excluded (`CORPUS_D10`) |
| gold pairs with fold-identical English | **1**, labelled `SAME_CONTENT` — correctly |
| gold pairs with fold-identical Sanskrit | **27**, and **all 27** labelled `SAME_CONTENT` |
| Samavedic translations in the live graph | **0** |

All 27 identical-Sanskrit pairs were labelled correctly by the adjudicator, and all 27 are
refused by this layer's novelty filter because they are agent 12's fact. **Instruction for
the lead:** the moment Wave 3 imports the 173 staged Samavedic translations, every
translation-channel RV-SV score becomes partly circular. This predicate does not use a
translation channel, so no *edge* here is affected; the audit score on each edge would be.

### Attack 4 — entity-layer lexical leakage. **Clean, and the opposite of what was feared.**

Assertion declared before the test: *if the signal is mostly co-mentioned theonyms, the
hybrid must lose most of its separation once every pair sharing a devata mention or a
dedication is removed. Predicted: separation drops but survives above 0.5.*

| | n | positive rate | AUC hybrid |
|---|--:|--:|--:|
| gold pairs sharing a theonym or dedication | 145 | 0.8276 | 0.7147 |
| gold pairs sharing **none** | 179 | 0.3799 | **0.8041** |

The hybrid separates *better* where no theonym is shared. The prediction was wrong in the
right direction. Two supporting figures: `R2_ENTITY_IDF` alone reaches 0.7048, and removing
it from the hybrid moves AUC from 0.8377 to **0.8323** — the entity channel that greedy
selection picked fourth is worth 0.005 and is very nearly redundant. And **1 of 324** gold
pairs already carries a `SHARES_ENTITY_VOCABULARY_WITH` edge, so this layer is almost
entirely disjoint from the existing entity-vocabulary predicate.

### Attack 5 — corpus mean and embedding anisotropy. **The most quantitatively damning, on the candidates that lost.**

200,000 pairs drawn uniformly at random from the 204,211,945-pair mantra product, seeded,
independent of the candidate pool:

| candidate | mean | p50 | p95 | share ≥0.5 | share ≥0.8 |
|---|--:|--:|--:|--:|--:|
| `R6_E5_SANSKRIT` | **0.8883** | 0.8895 | 0.9134 | **1.0000** | **0.9999** |
| `R7_E5_TRANSLATION` | 0.5974 | 0.8227 | 0.8674 | 0.7163 | 0.6652 |
| `R5_MULTILING_SANSKRIT` | 0.5988 | 0.6108 | 0.8827 | 0.7014 | 0.1600 |
| `R8_ENMINI_TRANSLATION` | 0.2143 | 0.2436 | 0.4576 | 0.0224 | 0.0000 |
| `R6_…_CENTRED` | −0.0004 | −0.0079 | 0.1839 | 0.0002 | 0.0000 |
| `R7_…_CENTRED` | 0.0001 | 0.0000 | 0.1425 | 0.0001 | 0.0000 |
| `R4_FRAME_IDF` | 0.0502 | 0.0000 | 0.3161 | 0.0180 | 0.0027 |
| `R2_ENTITY_IDF` | 0.0261 | 0.0000 | 0.2242 | 0.0126 | 0.0025 |
| `C_LEXICAL_CHAR4` | 0.0048 | 0.0000 | 0.0214 | 0.0001 | 0.0000 |
| `R1_LEMMA_TFIDF` | 0.0039 | 0.0000 | 0.0309 | 0.0000 | 0.0000 |

**99.99% of uniformly random Vedic verse pairs sit at cosine ≥ 0.8 under raw
`multilingual-e5-small`, and 66.5% do under the same encoder on the English.** This is the
attack the owner named and it lands on exactly the deployment it warned against: a generic
multilingual encoder plus the obvious threshold produces a graph in which everything
resembles everything. Centring removes it completely (0.0002 at ≥0.5).

The predicate's own score on the same random draw, against the pool it is thresholded on:

| distribution of the defining hybrid, in z units | mean | p50 | p99 | p99.99 | max |
|---|--:|--:|--:|--:|--:|
| **uniformly random corpus pairs** | −0.7592 | −0.7854 | 0.2567 | 1.4434 | 3.1064 |
| the candidate pool | 0.0000 | −0.0637 | 1.5298 | — | 3.4538 |

A random pair scores three-quarters of a standard deviation below the pool mean, and the
threshold of z = 0 sits above the 99th percentile of random pairs. That is the honest
statement of separation, and it is why §6 reports the pool-recall bound rather than only
in-sample recall.

### Attack 6 — near-duplicate is agent 12's territory. **Clean by construction, and the arithmetic is given.**

Assertion declared before the test: *if this layer adds something beyond a near duplicate,
the majority of pairs it accepts must not already be reachable by an existing predicate.*

Reachability over the 324 gold pairs: `shared_formula` 75, `lexical cosine ≥ 0.20` 67,
`in agent 12's relations` 42, `existing textual parallel` 27, `identical folded Sanskrit`
27 — **87 pairs by at least one route.** Over the full pool the novelty filter removes
**29,052 of 1,133,311 pairs**, every one attributed:

| removal reason | pairs |
|---|--:|
| shared formula, reachable via the `USES_FORMULA` hub | 19,047 |
| existing textual parallel | 4,912 |
| above the declared lexical ceiling of 0.20 | 3,837 |
| in agent 12's staged relations | 1,256 |
| **unattributed** | **0** |

The assertion held: at the threshold, before the filter, 133 gold pairs are accepted of
which 64 are novel and 69 already reachable — and the label mix separates the two
populations cleanly. The already-reachable accepted pairs are **41 `SAME_CONTENT`** and 20
`SAME_TOPIC_DIFFERENT_CLAIM`; the novel accepted pairs are **48
`SAME_TOPIC_DIFFERENT_CLAIM`** and 3 `SAME_CONTENT`. The existing predicates find the
same-content pairs. This one finds the same-topic pairs. They are different facts and the
labels say so.

### The correlation against agent 12's layer, measured directly

All **6,139** of agent 12's staged relations are present in this run's candidate pool —
a 100% intersection, so the comparison is over their whole layer and not a sample.

| measurement | value |
|---|--:|
| Pearson, my score against their stored `similarity` | **0.2588** |
| Spearman | **0.3432** |
| Pearson on the 42-pair gold overlap | 0.2746 |

A **low** correlation is the result this layer needs. A high one would mean it is
re-deriving a textual comparator under a semantic name. ρ = 0.343 over 6,139 pairs is a
weak monotone relationship of the sign you would expect — textually related verses do tend
to be thematically related — and it is nowhere near the collinearity that would make the
predicate redundant.

### Attack 7 — cross-Veda source reuse. **Clean, and the Samavedic case is answered by exclusion.**

| veda pair | gold pairs | positive rate | AUC | already a textual parallel | in agent 12 | novel |
|---|--:|--:|--:|--:|--:|--:|
| RV (within) | 118 | 0.6186 | 0.7778 | 2 | 2 | 104 |
| AV (within) | 76 | 0.6579 | 0.7577 | 0 | 15 | 43 |
| AV-RV | 85 | 0.4706 | 0.8417 | 17 | 17 | 62 |
| AV-YV | 17 | 0.3529 | 0.8182 | 1 | 1 | 13 |
| **RV-SV** | 12 | **0.7500** | 0.9259 | **5** | **5** | **3** |
| RV-YV | 11 | 0.5455 | 0.6000 | 1 | 1 | 9 |
| AV-SV | 5 | 0.8000 | 1.0000 | 1 | 1 | 3 |

The owner's concern is exact: RV-SV has the second-highest positive rate of any pair, and
**5 of its 12 gold pairs are already stored textual parallels** — inheritance, not
conceptual affinity. Only 3 of 12 survive the novelty filter. Every one of those 5 is
refused by this layer because the Samaveda taking a verse from the Rigveda is
`REUSES_TEXT_FROM`, a predicate that already exists and already says it. Of the 43,006
emitted edges, 2,592 are RV-SV and every one of them is a pair that is **not** a stored
parallel, not a shared-formula co-member, and below the lexical ceiling. The inheritance is
excluded by name rather than by hope.

---

## 6. The predicate, and the three filters that define it

```
THEMATICALLY_RESEMBLES(a, b)
```

> These two passages make comparable statements about a shared referent, on evidence that
> is not their shared wording. Symmetric, emitted once in ascending `canonical_key` order.

It is deliberately none of the four things the campaign-wide invariant separates:

| it is not | because |
|---|---|
| `NORMALIZED_EQUIVALENCE` | no folded equality asserts an edge here. Accent stripping, transliteration to Devanagari and whitespace folding build comparison surfaces that **generate candidates** and nothing more. |
| `CANONICAL_IDENTITY` | nothing here says two passages are the same passage. A folded equality is a **reason to refuse** an edge, not to assert one. |
| `TEXTUAL_VARIANT` | transmission differences are `VARIANT_OF` and `NEAR_PARALLEL_OF`, and every pair carrying one is refused. |
| a near duplicate | `EXACT_PARALLEL_OF`, `USES_FORMULA` co-membership, identical folded surface, agent 12's relations and a lexical ceiling of 0.20 all refuse by construction. |

`THEMATICALLY_RESEMBLES` is **not** in `CONTROLLED_PREDICATES` and is not one of the 14
frozen semantic predicates. It is proposed for addition, not assumed. It does not collide
with `ADDRESSES_CONCERN` or `CONCERNS`, which are passage-to-`Concept`, nor with any of the
five predicates refused by name in `vedagraph.semantic.ontology`. It is not
`RELATED_TO`-shaped: it means one thing, it carries `method`, `model`, `version`, `score`,
`evidence_basis`, a tier and a referent-guard state on every edge, and it is refused
outright wherever it cannot be defended.

Threshold selection, on the population the predicate is actually asserted over, with a
**precision floor of 0.85 declared on dev before the sweep**:

| z | dev tp | dev fp | dev P | dev R | pool pairs asserted |
|--:|--:|--:|--:|--:|--:|
| −0.30 | 27 | 8 | 0.771 | 0.931 | 431,106 |
| −0.10 | 26 | 8 | 0.765 | 0.897 | 372,078 |
| **0.00** | **24** | **4** | **0.857** | **0.828** | **336,418** |
| +0.20 | 21 | 3 | 0.875 | 0.724 | 278,852 |
| +0.50 | 15 | 3 | 0.833 | 0.517 | 195,239 |
| +1.00 | 3 | 1 | 0.750 | 0.103 | 77,443 |

z = 0.00 is the lowest threshold meeting the floor. **Say plainly what then does the real
work:** 336,418 pool pairs clear the threshold, the guard and the novelty filter, and the
per-mantra cap of 5 reduces that to 43,006 — it removes **293,412 pairs, 87.2%**, and
15,017 of the 19,088 mantras touched sit exactly at the cap. **The operative selector is
the cap, not the threshold.** This layer is a top-5 conceptual-neighbours index and should
be read as one.

### Recall, bounded honestly

| measure | value |
|---|--:|
| recall on the asserted dev population | 24 of 29 = **0.828** |
| recall on the asserted test population | 29 of 36 = **0.806** |
| share of random pairs qualifying on score, guard and ceiling | 0.02665 |
| implied qualifying pairs corpus-wide | ~5,442,248 |
| pairs the candidate pool contains | 1,133,311 |
| pairs the layer emits | 43,006 |
| **implied pool-recall upper bound** | **0.0079** |

The 0.806 is recall *inside the candidate pool*, which is the union of each
representation's top-10 neighbours and is not exhaustive. Extrapolating the independent
random draw, something like 5.4 million pairs corpus-wide would clear score, guard and
ceiling, so recall over the full product is **under 1%**. Both numbers are true and they
mean different things; quoting only the first would be the ordinary way to mislead here.

---

## 7. The referent traps, and the tier that had to be refused

### 7.1 The adversarial set

172 cases, with ground truth from **source-explicit dedication** (Anukramaṇī `HAS_DEVATA` /
`HAS_DEVATA_ASCRIPTION`) against the entity registry's own sense typing. No model opinion
enters any label.

**Score alone, on the 52 referent triples** — anchor to same-sense must score *strictly*
above anchor to other-sense, a tie counted as a failure:

| trap | triples | ordering correct |
|---|--:|--:|
| Soma the deity vs *soma* the pressed substance | 20 | **14** |
| Agni the deity vs physical fire | 20 | **15** |
| Vāc the goddess vs speech the faculty | 12 | **9** |
| **total** | **52** | **38 (73.1%)** |

73.1% is not good enough, and at the threshold the score alone would have emitted **9 of
the 52 other-sense pairs**. That is the measurement that carries evidence about the
representation, and it is a partial failure.

Why the score is worse at this than the typed frame alone: an ablation from the first run of
this domain, re-used here, shows the referent discrimination lives entirely in the
dedication.

| representation | traps passed |
|---|--:|
| `R4_FRAME_IDF` — dedication + mentions + predicates + classes | **45 / 52** |
| `R4b` — mentions + predicates + classes, **no dedication** | 27 / 52 |
| `R4c` — predicates + classes, no referent feature at all | 19 / 52 |
| `R4d` — dedication only | 41 / 52 |

Diluting `R4` with the Sanskrit encoder and the entity channel costs trap accuracy, because
§2's finding bites: the *mention* layers fire on the ambiguous token and record no sense.

### 7.2 The referent guard, with its circularity declared

The owner has ruled that `EPITHET_VARIANT_OF` asserting "Soma Pavamāna is Soma" is too
strong, and that deity identity is therefore not settled in this graph. So the predicate
carries a constraint rather than a classifier:

> No resemblance edge may be asserted between two passages whose source-explicit
> dedications are both known, drawn from the same mechanism, and disjoint.

**This cannot be validated by the trap set, and it is not offered as though it could.** The
triples take their ground truth from the same dedication layer the guard reads, so the
guard passes them by construction. The figure that carries evidence is the 38/52 above. The
guard is a scope restriction on what the predicate is allowed to mean, and its cost is
reported: over the gold set it refuses **38 pairs the score would have emitted, 20 of them
adjudicated positive.** Two passages can share a theme while their dedications disagree,
and this layer declines to assert it on a score alone.

### 7.3 A defect in my own guard, found by an implausible zero

`TIER_A` came back with **zero cross-Veda edges**, which is not a plausible fact about the
Vedas. The cause: `corpus.jsonl` merges two different graph mechanisms into one
`devata_attr` list.

| mechanism | distinct labels | edges | example values |
|---|--:|--:|---|
| `HAS_DEVATA` (RV) | 210 | 10,558 | `Indra`, `Agni`, `Soma Pavamana`, `the Asvins` |
| `HAS_DEVATA_ASCRIPTION` (AV) | 324 | 4,816 | `āgneyam`, `vānaspatyam`, `rohitādityadevatyam` |
| **intersection** | **0** | — | — |

English display labels on one side, Sanskrit adjectival ascription forms on the other. A set
intersection across them can never be non-empty, so my guard was reporting `VIOLATED` —
refuse — for every RV-AV pair with a dedication on both sides, **for a vocabulary reason
dressed as an evidential one.** This is the same failure as an attribution axis written by
three disagreeing mechanisms, and it was caught by a zero that looked wrong, not by reading
the code.

The fix, with its blast radius asserted before it was applied:

| assertion | prediction | measured | held |
|---|---|---|:-:|
| **B1** | only cross-mechanism pairs change, and every one currently reads `VIOLATED` | 138,054 changed, all `VIOLATED → NOT_APPLICABLE_VOCABULARY_NOT_COMPARABLE`, all AV-RV | ✓ |
| **B2** | the `UPHELD` count is exactly unchanged | 243,785 before and after | ✓ |
| **B3** | the edge count may only rise, and every new edge is `TIER_B` | 43,006 → 44,511, but 4,897 edges were *displaced* (3,740 of them `TIER_A`) because the per-mantra cap is a global competition | **✗** |
| **B4** | no trap regression: other-sense pairs emitted stays 0 | **0 → 10**, because 20 of the 52 other-sense pairs cross the RV-AV boundary and the guard can no longer speak about them | **✗** |
| **G1** *(earlier)* | the guard is applicable to fewer than half the pool | 67.6% — the pool is RV-heavy and the RV is 100% dedicated | **✗** |
| **G3** *(earlier)* | every novelty removal attributable to a named predicate | 29,052 removals, 0 unattributed | ✓ |
| **G4** *(earlier)* | the cap reduces monotonically and creates no new edge | 336,418 → 43,006, all survivors above threshold | ✓ |

Three of seven assertions failed, and the two failures that mattered changed the design.
B4's failure is the reason the next section exists.

### 7.4 `TIER_B` is refused, not shipped

Fixing the guard's vocabulary defect created a fourth state and therefore a third tier. Its
measurements decide its fate:

| tier | definition | pool pairs | test precision (95% CI) | disposition |
|---|---|--:|---|---|
| **A** `DEDICATION_AGREES` | both dedications known, same mechanism, intersecting | 243,785 | **0.955** (21/22) [0.782, 0.992] | **emitted, importable** |
| **B** `REFERENT_EVIDENCE_NOT_COMPARABLE` | both known, mechanisms not comparable | 138,054 | **0.444** (4/9) [0.189, 0.733] | **refused, no edge** |
| **C** `NO_REFERENT_EVIDENCE_EXISTS` | at least one endpoint undedicated | 366,936 | **0.615** (8/13) [0.355, 0.823] | **emitted, not importable** |
| — `REFERENT_GUARD_VIOLATED` | both known, same mechanism, disjoint | 384,536 | — | **refused, no edge** |

`TIER_B` is refused on two independent grounds: its measured precision is the worst of the
three, with 5 of its 9 gold pairs labelled `UNRELATED`, and assertion B4 shows that
admitting it lets 10 of 52 referent traps through. Unlocking it is an ontology decision this
agent does not own — it requires a mapping between the 210 `HAS_DEVATA` display labels and
the 324 `HAS_DEVATA_ASCRIPTION` forms, which is precisely the kind of "these two names are
the same deity" claim the owner has just ruled is too strong to make casually.

`TIER_C` is emitted but not importable. Its precision is 0.615, and worse, **the adversarial
set cannot be run on it at all**: the traps require a dedication on both sides, which is the
defining absence of the tier. It is the verification queue, and it is exactly the Samaveda
and the Yajurveda — 0 of 1,844 and 0 of 1,975 dedicated — plus the 1,679 Atharvavedic verses
without an ascription.

### 7.5 The adversarial classes under the full rule

| class | cases | emitted | how the rest were rejected |
|---|--:|--:|---|
| formulaic boilerplate | 40 | **0** | novelty filter 24, score 10, tier 6 |
| accent- or surface-identical | 40 | **0** | novelty filter 37, tier 3 |
| common-high-frequency-vocabulary only | 40 | **9** | score 25, tier 6 |
| referent triples, other-sense side | 52 | **0** | score 27, guard violated 15, tier B 10 |

Two honest qualifications. First, the boilerplate and accent classes are rejected by the
**novelty filter**, not by the score — the score put 22 of 40 boilerplate pairs and **40 of
40** accent-identical pairs above the threshold. A semantic score cannot tell a refrain from
a claim, and the filter is what saves the layer here. Second, of the 9 surviving
high-frequency cases, 7 are `TIER_C` (not importable) and 2 are `TIER_A`: RV 1.132.1/RV
3.35.6 sharing only *yajña* at z = 0.504, and AV 18.3.52/AV 18.4.5 sharing only *pṛthivī* at
z = 0.630. The second of those is a pair of verses from the same funeral book with the same
ascription, so the adversarial case's "expected: REJECT" — which was derived from entity
Jaccard, not from adjudication — may itself be too strict. Either way, 2 importable edges
out of 40 constructed traps is the residual, and it is named rather than rounded away.

---

## 8. The artifact

`data/staging/semantic_resemblance/`. The row unit is the **mantra**, following agent 10's
precedent, so the assessed-set record covers all 20,210 — corpus-audit §4 records that the
graph cannot otherwise distinguish "assessed and came back empty" from "never assessed".

| | mantra grain | pair grain |
|---|--:|--:|
| `candidates_considered` | 20,210 | 1,133,311 |
| `accepted` | 19,088 | 43,006 |
| `rejected` | 359 | 1,090,305 |
| `unresolved` | **763** | 0 |
| `verified_zero` | **0** | 0 |

Both balance independently. `rejected.jsonl` holds all 1,122 no-edge mantras; the 763
flagged `unresolved: true` are counted under `unresolved` because they carry **neither a
typed frame nor an entity-registry mention**, so two of the three defining channels are
empty for them and the predicate has no non-lexical basis to assert either way. The
remaining 359 were scored and came back empty. Neither is a verified zero, and
`verified_zero` is 0 deliberately.

The pair-grain accounting is `proofs/pair_counts.json`:

| first reason that applies | pairs |
|---|--:|
| accepted | 43,006 |
| referent guard violated (same mechanism, disjoint) | 384,536 |
| per-mantra cap of 5 | 293,412 |
| below threshold | 253,840 |
| TIER_B, vocabularies not comparable | 138,054 |
| novelty: shared formula via the `USES_FORMULA` hub | 12,198 |
| novelty: existing textual parallel | 3,883 |
| lexical ceiling of 0.20 | 2,639 |
| novelty: identical folded Sanskrit surface | 915 |
| novelty: in agent 12's staged relations | 828 |
| **total** | **1,133,311** |

Each pair is charged to the **first** reason that applies in that order, so these are not
the same as §5's per-filter counts, which measure each filter over the whole pool
independently of the others. Both are correct under their stated attribution and the
manifest says which is which. `proofs/pair_ledger_sample.jsonl` holds a seeded reservoir
sample of up to 2,500 pairs per reason (19,243 rows); the exhaustive one-line-per-pair
version was 246 MB of two canonical keys and a reason code, which is disproportionate to a
43,006-edge layer, so the counts above are exhaustive and the per-pair detail is sampled.

**43,006 edges on 19,088 mantras**, by tier and Veda pair:

| | RV | AV | AV-RV | RV-SV | RV-YV | AV-YV | AV-SV | SV | YV | SV-YV | total |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| TIER_A | 20,312 | 6,641 | — | — | — | — | — | — | — | — | **26,953** |
| TIER_C | — | 1,778 | 2,035 | 2,592 | 2,201 | 1,907 | 1,670 | 1,262 | 1,679 | 929 | **16,053** |

Score distribution of the emitted edges, in z units: min 0.0001, p10 0.368, p25 0.670,
p50 1.048, p75 1.403, p95 1.797, max 2.451. Degree distribution: 15,017 mantras at the cap
of 5, then 1,202 at 4, 1,132 at 3, 986 at 2, 751 at 1.

Every edge carries `predicate`, `version`, `score`, the three channel cosines and their
z values, `evidence_basis`, `referent_guard`, `shared_dedication`, `resemblance_tier`,
`importable`, `not_importable_reason`, the unused translation-channel score and the
lexical-control cosine. Every row carries `method`, `model` (with the ONNX sha256),
`version`, `source_snapshot`, `algorithm_version`, `config_hash`, `code_commit`,
`population`, `processed_count`, `positive_count`, the assessed-population record and the
evaluation block. The method card, symmetry convention, normalisation role and
`not_reachable_by` list are identical for all 43,006 edges and live once in
`proofs/config.json#method_card` rather than 86,012 times — the first emission repeated
them and cost 223 MB of the same prose.

### 8.1 A residual: 255 edges that are not really non-lexical

| `evidence_basis` — which channels actually fired | edges | share |
|---|--:|--:|
| typed frame + entity registry + Sanskrit encoder | 35,740 | 83.1% |
| typed frame + Sanskrit encoder | 7,011 | 16.3% |
| **Sanskrit encoder alone** | **255** | **0.59%** |

Those 255 have no typed or registry evidence at all: they rest entirely on an anisotropic
sentence encoder over the Sanskrit surface, which is not what a layer defined as
non-lexical should assert. Applying the predicate's own definition consistently makes them
not importable whatever their tier, and they carry that reason on the edge.

All 255 fall in `TIER_C`, and **provably so rather than by luck**: `TIER_A` requires a
shared dedication, a dedication is itself an `R4_FRAME_IDF` feature, so a `TIER_A` edge
cannot have an empty frame channel. The importable set of 26,953 is unaffected.

### 8.2 A tooling defect of my own, because it cost an hour and would recur

`np.load` on an `.npz` returns a lazy archive handle: **every `Z[name]` access
decompresses the whole 1.13-million-element array out of the zip again.** A per-edge access
pattern did that 215,030 times and burned 913 seconds of CPU producing no output at all,
while the same work over materialised arrays is instant. Two earlier symptoms pointed the
wrong way — a stopped shell leaving an orphaned Python process, and `tail` holding the
pipeline's output until exit so the progress prints were invisible. The fix is one line;
finding it needed a timing probe rather than another guess.

### 8.3 Validation

```sh
.venv/Scripts/python.exe scripts/validate_staging_artifact.py \
    data/staging/semantic_resemblance --graph
```

**PASS.** Every check evaluated every eligible row and found no defect:
**20 of 20 file checksums**, `19,088/19,088` on all eight row checks,
`1,122/1,122` on `rejected.has_reason`, and `19,088/19,088` on both
`graph.canonical_key_resolves` and `graph.veda_agrees`. The manifest was written last and
nothing in the artifact was touched between it and this run.

The graph was re-counted after validation: **108,779 nodes / 265,295 relationships**, 66
relationship types, and `THEMATICALLY_RESEMBLES` is **not** among them. No canonical write
occurred.

Every load-bearing figure in this report is also checked mechanically against the artifact
it came from — `proofs/report_figure_check.json`, which reports **0 disagreements** over every
figure it covers. It found
two before this version: a rounded κ that was the checker's own fault, and one that was
real — `proofs/candidate_representations.json` still embedded the inherited
`C_LEXICAL_CHAR4` dimension of 91,738 that §1.1 corrects to 94,040. A proof file carrying
the number its own report calls wrong is exactly the drift the check exists to catch. The
proof was re-derived from the live build, the superseded value is kept beside it, and the
manifest was then regenerated and re-validated in that order.

A note on one field name, because this project has been bitten by it: the per-edge
`evidence_basis` here records **which non-lexical channels fired**. It is not the graph's
`evidence_basis` property (`SANSKRIT` / `ENGLISH`) and not a derivation enum, and the row
says so in `evidence_basis_axis`.

---

## 9. What this does not do

- **Nobody read anything.** 0 of 43,006 edges, 0 of 324 labels, 0 of 172 adversarial cases
  were reviewed by a person. Section 22 is not satisfied.
- **162 of 486 sampled pairs are unadjudicated**, typed `UNADJUDICATED_QUOTA_EXHAUSTED` in
  the row. The provider's daily allowance is exhausted and was not retried in a loop.
- **No verified zero is claimed anywhere.** The 1,122 rejected mantras are recorded as
  assessed under three named channels over a non-exhaustive pool.
- **Pool recall is under 1%** of the pairs that would qualify corpus-wide. This is a top-5
  neighbours index, not an exhaustive relation.
- **The Samaveda and the Yajurveda cannot reach `TIER_A` at all**, because neither has a
  dedication layer. All 8,563 edges touching them are `TIER_C` and not importable.
- **The 14 candidate representations were not tuned.** Each was built once, from a written
  specification, and compared. No hyperparameter search was run on any of them.

---

## 10. For the lead, in the order it matters

1. **Import `TIER_A` or don't, but decide on the interval, not the point.** 26,953 edges at
   a test precision of 0.955 measured on **22 gold pairs** — the 95% CI is [0.782, 0.992].
   Over 26,953 edges the lower bound is roughly 5,900 wrong. A human pass over 200 sampled
   `TIER_A` edges would tighten that CI to about ±0.03 and is the cheapest thing that would
   settle this.
2. **The `TIER_B` refusal needs your ontology ruling, not more modelling.** 138,054 RV-AV
   candidate pairs are refused because `HAS_DEVATA` and `HAS_DEVATA_ASCRIPTION` share 0 of
   210 and 324 label values. Mapping them is a "these two names are the same deity" claim,
   which is the claim you have just ruled is too strong in the `EPITHET_VARIANT_OF` case.
   Until it is ruled on, the honest state is a named refusal with a measured 0.444 precision.
3. **`THEMATICALLY_RESEMBLES` needs adding to `CONTROLLED_PREDICATES` before any import.**
   It is proposed here, not assumed, and `src/vedagraph/enrich/predicates.py` is not this
   agent's write surface.
4. **Store it symmetrically and document it.** Emitted once in ascending `canonical_key`
   order. A directed query returns a false zero for the second endpoint — the exact shape
   of `CORPUS_D07`, which cost agent 10 five matrix cells.
5. **Withdraw the previous run's `SHARES_FORMULA_WITH` reading.** §1.2. Agent 10 is right;
   two agents in one wave found the same zero and neither found the recorded reason by
   looking at the database.
6. **The Yajurvedic fold defect is still live in the shared module.** 873 of 1,975 YV verses
   carry a Vedic sign that survives this layer's fold with no counterpart on the
   transliterated RV/AV side. Agent 10 located the root cause in
   `enrich/surfaces.build_surfaces` and staged a patch. It does not change this layer's
   conclusions (measured: excluding YV *raises* the leakage AUC to 0.845) but it does bias
   the lexical control on those verses.
7. **If Wave 3 imports the 173 Samavedic translations**, no edge here changes, because the
   predicate uses no translation channel. The per-edge audit score would become partly
   circular for RV-SV, and the `evidence_basis` on every edge makes the affected ones
   findable.
8. **Section 22 remains the binding constraint on this domain**, as it does on every audio
   domain in Wave 1. 43,006 edges rest on 324 labels from one model and 26 from another,
   and the one label boundary the two disagree about is the boundary the layer sits on.


> **R5 correction.** The 173 Samavedic renderings are no longer future tense: they are in
> the live graph, and the table row reading "Samavedic translations in the live graph | 0"
> is superseded. All 173 carry `reuse_kind = REUSED_RENDERING`, so the Samaveda's
> independent English count remains 0 and the two figures are not in conflict -- they
> measure different things, which is why `GAP-TRANSLATION-004` gives the verse-level state
> its own terminal value.
