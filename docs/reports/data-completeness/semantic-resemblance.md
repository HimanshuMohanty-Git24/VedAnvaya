# Semantic resemblance — building an absent layer, and measuring it first

Agent 11 of the Post-V1 Data Completeness Campaign, Wave 2. Owner's section L: *do not
deploy a generic embedding model without evaluation.* That instruction is the whole of this
report. Thirteen candidate representations were built and scored against each other on the
same 486-pair adjudicated sample before one relationship was written, and the finding that
matters most is about the candidates that lost.

- Measured: 2026-09-15
- Branch: `phase-data-completeness-v2`
- Graph access: `MATCH` / `RETURN` only, `bolt://localhost:7687`, database `neo4j`
- Graph at start and at end: **108,779 nodes / 265,295 relationships** — unchanged, and
  re-counted after the run. No canonical write occurred.
- Write surface used: `data/staging/semantic_resemblance/`, this file. Nothing else.

---

## 1. The starting position, verified rather than inherited

`GAP-SEMANTICS-006` says no non-lexical resemblance measure exists. Four independent
checks, because an absence is the claim most worth re-measuring:

| Check | Result |
|---|---|
| `CALL db.relationshipTypes()` | 66 types, none a resemblance predicate. No `RELATED_TO`. |
| `SHOW INDEXES` by type | 84 `RANGE`, 2 `FULLTEXT`, 2 `LOOKUP`, **0 `VECTOR`** |
| `CALL db.propertyKeys()` matching embed/vector/resembl/similar | one key, `similarity`, and it lives on the textual-parallel edges |
| `SHARES_FORMULA_WITH` | declared in the type vocabulary and carrying **zero relationships** |

The registry was right. The layer is absent, and the last row is a correction nobody had
recorded: the type vocabulary advertises a passage-to-passage formula predicate that has
never had an edge in it. Passage-level formula membership is `USES_FORMULA` alone, as the
corpus audit found, and `SHARES_FORMULA_WITH` is an empty declaration beside it.

One more measurement changes what "absent" means here. `SHARES_ENTITY_VOCABULARY_WITH`,
the nearest existing neighbour of this layer, holds 2,141 edges and **every one of them
joins two different Vedas**:

| veda pair | AV-RV | RV-SV | RV-YV | AV-YV | AV-SV | SV-YV | within one Veda |
|---|--:|--:|--:|--:|--:|--:|--:|
| edges | 1,176 | 421 | 291 | 136 | 84 | 33 | **0** |

So within a single Veda there is no relatedness predicate of any kind except textual
parallelism. A reader asking "what else in the Rigveda says this" has, before this work,
exactly one instrument, and it answers on wording.

---

## 2. What the graph's own semantic layers actually are

Five layers looked like candidate signals. Measuring them changed the plan three times.

### 2.1 The lemma layer in the graph is a theonym index, not a lemma layer

`MENTIONS_LEMMA` covers 6,560 Rigvedic mantras — 62.2% by the corpus audit's count — over
9,000 edges. It reaches **39 distinct lemmas**, and all thirty-nine are deity names:
`índra-` (2,305 mantras), `agní-` (1,604), `sóma-` (950), down to `ásamāti-` (2). There are
10,031 `:Lemma` nodes, so 9,992 of them carry no mantra edge at all.

A Sanskrit lemma representation built on the graph would therefore be a second copy of the
theonym layer. The real morphology is in the repository and not in the graph:
`data/knowledge/rigveda_lexical_v1/tokens.jsonl` holds **164,758 tokens over 9,785 distinct
normalised lemmas, covering all 10,552 Rigvedic mantras** — the University of Zurich
morphosyntactic annotation published in the VedaWeb TEI, `MANUAL_SCHOLARLY_ANNOTATION`.
That file, not the graph, is what `R1_LEMMA_TFIDF` below is built from.

This is a sharper statement of `GAP-MORPHOLOGY` than "the Rigveda has lemmas and the other
three do not": the Rigveda has a complete scholarly lemma layer that was never projected,
and what was projected instead is 0.4% of its vocabulary.

### 2.2 `ABOUT_CONCEPT` is `MENTIONS_ENTITY` under a second name

24,969 `ABOUT_CONCEPT` edges and 28,227 `MENTIONS_ENTITY` edges. Compared as
(mantra, label) pairs: **24,905 identical, 64 only in `ABOUT_CONCEPT`, 3,322 only in
`MENTIONS_ENTITY`**. `ABOUT_CONCEPT` is a 91-label subset of the 229-label entity layer with
essentially no independent content. Treating them as two signals would have double-weighted
one.

### 2.3 The entity layer is a controlled-vocabulary *lexical* layer

Every one of the 28,227 mention edges was written by `domain-mention-v1:sanskrit-token`
(27,713) or `domain-mention-v1:sanskrit-sandhi` (514). The layer is a dictionary match on
the Sanskrit surface. It is a much better signal than raw characters because the dictionary
is curated and IDF-weighted, but it is not independent of wording, and a resemblance layer
resting on it alone would be a lexical layer wearing a semantic name. That is precisely the
error `SHARES_ENTITY_VOCABULARY_WITH` was renamed to avoid.

### 2.4 The two mention layers do not disambiguate sense — they collapse it

This is the measurement that decided the design.

| Ambiguous word | `MENTIONS_DEVATA` fires on | of which also carry the thing-sense entity | share |
|---|--:|--:|--:|
| *vāc* → `Vac, Speech` vs `speech (vāc)` | 302 | 246 | **81.5%** |
| *soma* → `Soma` / `Soma Pavamana` vs `soma juice (soma)` | 1,618 | 813 | **50.2%** |

The registry is right to hold two entries. The *mention* layers both fire on the same token
and neither records which sense is meant. So the graph's deity-mention layer cannot be used
as referent evidence for these words: it is the trap, not the defence against it.

The defence that does exist is dedication — `HAS_DEVATA` (RV, 10,552 of 10,552) and
`HAS_DEVATA_ASCRIPTION` (AV, 4,160 of 5,839) — which comes from the Anukramani and names
the deity a hymn is *addressed to*, independently of the words in the verse. The Samaveda
and Yajurveda have none, a fact that bounds this whole layer and is stated as such in §8.

### 2.5 The assertion layer is thin and half of it is unreviewed

4,926 `HAS_SEMANTIC_ASSERTION` edges, all Rigvedic. 2,406 are `ACCEPTED` with a predicate
(`agentive-morphology-v1`, over 2,228 mantras); 2,520 are `CANDIDATE` and carry no
`predicate` property at all. Only the accepted ones enter any representation here. Outside
`ABOUT_CONCEPT`, the typed relation layer is 2,275 edges over four Vedas — `PROTECTS_FROM`
659, `USED_FOR_RITE` 517, `ADDRESSES_CONCERN` 326, and a long tail mostly at
`state: CANDIDATE`, which is excluded.

---

## 3. The translation confound, measured three ways

The brief warned that translations in this corpus are not independent of each other. They
are worse than that, and one of the stated figures does not reproduce.

### 3.1 Duplicate English: 53, 231 or 72, depending on the question

| Definition | Groups | Rows | Composition |
|---|--:|--:|---|
| Byte-identical English, mantra-aligned, live graph | 53 | 111 | RV 27, AV 15, YV 11 — all within one Veda |
| Case- and punctuation-folded, live graph | **231** | 482 | **RV–YV 146**, RV 49, YV 19, AV 17 |
| The brief's figure of 72 | — | — | not a live-graph figure |

The 72 comes from Agent 3's Wave 1 *staged* artifact
(`docs/reports/data-completeness/translation.md:323`), where 72 of 75 duplicate-English
groups were reclassified as the corpus repeating itself. It is a correct figure about a
staged file. It is not the live graph's, and the live graph's is the one that matters to
anybody embedding translations today.

The live figure that matters is the third column: **146 folded-duplicate groups are RV–YV
pairs.** Griffith translated both the Rigveda and the White Yajurveda, and where the
Yajurveda quotes the Rigveda he reprints his own English, modulo capitalisation and
punctuation. Any translation-based resemblance measure will find those 146 and they are
evidence about a translator's practice, not about the Vedas.

For reference, identical Sanskrit surface — accent, punctuation and whitespace folded, one
recension's roles collapsed — gives **630 groups over 1,356 mantras, 213 of them
cross-Veda**. The corpus audit's CORPUS_D11 counted within-recension-within-role and got
587 mantras; both are right, and the definitions differ.

### 3.2 The 31 misaligned Rigvedic translations are excluded, by name

`RV_1_65_TO_1_70_MISALIGNMENT.md`: 25 `MISATTACHED` and 6 `CORRECT_UNIT_UNDECLARED_SCOPE`
verses carry a translation that renders different verses. All 31 are excluded from every
translation channel by key, read from
`data/staging/rv_coordinate_repair/repair_table.jsonl`, not re-derived. A further 158
Rigvedic mantras carry only a `HYMN`-level translation (CORPUS_D10) and are excluded too:
a hymn's translation is not this verse's gloss. Usable mantra-aligned translations:
**RV 10,313 + YV 1,903 + AV 4,878 = 17,094 of 20,210.**

### 3.3 The Samavedic circularity is a future hazard, not a present one

The brief warns that 173 Samavedic translations staged in Wave 1 are Griffith's *Rigveda*
renderings used cross-corpus. Verified: `data/staging/translation/rows.jsonl` holds exactly
173 SV rows at `VERIFIED_SEGMENT`, and they are what the brief says. But the live graph
holds **zero** Samavedic translations, so no RV–SV resemblance measured here can be
circular through them.

**Instruction for the lead:** if Wave 3 imports those 173, every translation-channel RV–SV
score in this layer becomes partly circular, because the same English would then be
attached to both endpoints. Either exclude those 173 keys from the translation channel on
re-derivation, or re-derive the layer without it. The `evidence_basis` on every relation
records whether a translation channel contributed, so the affected edges are findable.

---

## 4. The thirteen candidate representations

Each is an L2-normalised vector space over all 20,210 mantras, scored by cosine. `C_` is a
control, not a candidate: it is the lexical axis, built so that lexical similarity can be
measured and excluded rather than assumed absent.

| id | what it is | dimensions | mantras populated |
|---|---|--:|--:|
| `R1_LEMMA_TFIDF` | Zurich/VedaWeb Sanskrit content lemmas, sublinear TF-IDF | 4,893 | 10,552 (RV only) |
| `R2_ENTITY_IDF` | registry entity + theonym mention sets, IDF-weighted | 259 | 17,540 |
| `R3_TRANSLATION_TFIDF` | English content words, translator-habit stoplist applied | 9,209 | 17,091 |
| `R3b_TRANSLATION_RAW` | same, habit words kept — the ablation's other arm | 9,248 | 17,093 |
| `R4_FRAME_IDF` | typed frame: dedication, assertion predicates, typed relations, ontological classes | 913 | 19,284 |
| `R5_MULTILING_SANSKRIT` | `paraphrase-multilingual-MiniLM-L12-v2` on the Sanskrit, folded to Devanagari | 384 | 20,210 |
| `R5_…_CENTRED` | same, corpus mean direction removed | 384 | 20,210 |
| `R6_E5_SANSKRIT` | `multilingual-e5-small` on the same Sanskrit | 384 | 20,210 |
| `R6_…_CENTRED` | same, centred | 384 | 20,210 |
| `R7_E5_TRANSLATION` | `multilingual-e5-small` on the English | 384 | 17,094 |
| `R7_…_CENTRED` | same, centred | 384 | 17,094 |
| `R8_ENMINI_TRANSLATION` | `all-MiniLM-L6-v2` on the English | 384 | 17,094 |
| `R8_…_CENTRED` | same, centred | 384 | 17,094 |
| `C_LEXICAL_CHAR4` | character 4-grams of the unaccented Devanagari — **control** | 91,738 | 20,210 |

`R6` and `R7` are the same model on the two channels, which is the controlled comparison
the translation ablation needs: one encoder, Sanskrit on one side and its English gloss on
the other.

The models are public ONNX exports run on CPU through `onnxruntime`; weights are checksummed
in `sources.jsonl`. They were installed into a throwaway directory, never into the project
environment: `pyproject.toml` is inside the semantic seal and `.venv` is unchanged (verified
after install — `protobuf` still 5.29.6, `numpy` still absent from the project interpreter).

### 4.1 Sanskrit is not what these encoders were trained on, and the fertility says so

Subword tokens per whitespace word, over a seeded 400-mantra sample:

| model | Vedic Sanskrit (Devanagari) | English gloss |
|---|--:|--:|
| `paraphrase-multilingual-MiniLM-L12-v2` (XLM-R vocabulary) | 2.66 | 1.71 |
| `multilingual-e5-small` (XLM-R vocabulary) | 2.66 | 1.71 |
| `all-MiniLM-L6-v2` (English BERT vocabulary) | 3.48 | 1.64 |

At 2.66 subwords per word the multilingual models have no whole-word grip on Vedic
vocabulary; at 3.48 the English model has essentially none. No Sanskrit-trained sentence
encoder with an ONNX export was found, so "Sanskrit-compatible embeddings" is recorded as
**not viable from public artifacts at this time**, rather than approximated and presented as
if it were.

### 4.2 Raw cosine from these encoders cannot carry a threshold

Pairs at or above a threshold, out of the 1,133,112-pair candidate pool:

| candidate | ≥0.3 | ≥0.5 | ≥0.7 | ≥0.8 | ≥0.9 |
|---|--:|--:|--:|--:|--:|
| `R6_E5_SANSKRIT` | 1,133,112 | 1,133,112 | 1,133,112 | **1,133,101** | 674,005 |
| `R6_…_CENTRED` | 247,552 | 30,877 | 7,378 | **5,153** | 3,184 |
| `R7_E5_TRANSLATION` | 960,214 | 960,214 | 960,214 | **942,608** | 100,766 |
| `R7_…_CENTRED` | 191,797 | 14,142 | 2,721 | **1,594** | 783 |
| `R5_MULTILING_SANSKRIT` | 1,090,987 | 927,018 | 593,300 | 377,173 | 151,973 |
| `R5_…_CENTRED` | 443,945 | 297,242 | 110,465 | 50,500 | 17,177 |
| `R8_ENMINI_TRANSLATION` | 779,707 | 315,958 | 18,539 | 2,260 | 1,044 |
| `R8_…_CENTRED` | 254,120 | 25,772 | 2,516 | 1,447 | 817 |
| `R2_ENTITY_IDF` | 382,065 | 260,216 | 162,695 | 111,584 | 87,573 |
| `R4_FRAME_IDF` | 413,300 | 265,146 | 168,698 | 125,113 | 82,013 |
| `R1_LEMMA_TFIDF` | 17,106 | 1,202 | 418 | 306 | 261 |
| `R3_TRANSLATION_TFIDF` | 17,356 | 3,855 | 2,136 | 1,471 | 755 |
| `C_LEXICAL_CHAR4` *(control)* | 13,093 | 8,737 | 5,516 | 3,720 | 2,119 |

**A cosine of 0.8 on raw `multilingual-e5-small` selects every pair in the pool** — 1,133,101
of 1,133,112. Deployed with the threshold an engineer would reach for, that model asserts
that every Vedic verse resembles every other. Centring it — removing the corpus mean
direction and renormalising — moves the same threshold to 5,153 pairs, a factor of 220. The
registry's own note that "the edge count depends entirely on the threshold" is exactly right,
and the threshold's meaning depends entirely on the geometry nobody had looked at.

`R2` and `R4` fail in the opposite direction: at 259 and 913 dimensions they saturate, and
87,573 and 82,013 pairs sit at cosine ≥ 0.9 because they share a small identical feature set.
Their mean rank-1 similarity is 0.810 and 0.896. They discriminate poorly at the top.

### 4.3 The candidates disagree about who each verse's nearest neighbour is

Rank-1 neighbour agreement, out of 20,210 mantras. Within a family, centring moves 18–38%
of nearest neighbours; across families, agreement is 3–15%.

| pair | agree |
|---|--:|
| `R3_TRANSLATION_TFIDF` vs `R3b` (stoplist on/off) | 16,536 (81.8%) |
| `R6_E5_SANSKRIT` vs centred | 15,366 (76.0%) |
| `R8_ENMINI_TRANSLATION` vs centred | 14,800 (73.2%) |
| `R7_E5_TRANSLATION` vs centred | 14,421 (71.4%) |
| `R5_MULTILING_SANSKRIT` vs centred | 12,531 (62.0%) |
| `R6_E5_SANSKRIT` vs `C_LEXICAL_CHAR4` | 8,060 (39.9%) |
| `R7_E5_TRANSLATION` vs `R3_TRANSLATION_TFIDF` | 6,844 (33.9%) |
| `R2_ENTITY_IDF` vs `R4_FRAME_IDF` | 2,620 (13.0%) |
| `R1_LEMMA_TFIDF` vs `R5_MULTILING_SANSKRIT` | 264 (1.3%) |

Two things follow. The choice of representation is not a detail — it changes the answer for
most verses. And no single candidate can be treated as ground truth for another, which is
why the evaluation below is against an adjudicated sample rather than against a baseline
representation.
