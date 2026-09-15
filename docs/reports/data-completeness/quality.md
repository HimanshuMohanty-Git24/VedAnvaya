# Quality, Reference Set and Reliability

Agent 16 of the Post-V1 Data Completeness Campaign. Every figure below was measured on
2026-09-15 against the live graph with read-only Cypher, and against a published
human-annotated treebank fetched the same day.

- Branch: `phase-data-completeness-v2`
- Access: `MATCH` / `RETURN` only, `bolt://localhost:7687`, database `neo4j`
- Graph at measurement: 108,779 nodes / 265,295 relationships, unchanged
- Artifacts: `data/staging/quality/` — `rows.jsonl`, `rejected.jsonl`, `sources.jsonl`,
  `manifest.json`, `proofs/`

---

## 0. The one-sentence answer

**The `confidence` property is not a probability, and this report proves it three ways:**
50,468 of 76,050 confidence-bearing edges carry exactly `1.0`; five predicates stamp one
value on every edge they have; and within a single nominal `1.0` the measured accuracy
ranges from **71.4% to 97.6%** depending on a tier the number does not mention.

---

## 1. What human annotation exists, and what it covers

The campaign's starting position was that nothing in `data/gold/` is human gold. That is
confirmed and unchanged. But human annotation of the *Vedic text* does exist, it is
published, it is licence-clean, and it reaches three of our four recensions.

**UD_Sanskrit-Vedic, the Treebank of Vedic Sanskrit** (CC BY-SA 4.0). 27,182 sentences,
206,440 words, 57 texts. Annotated by Salvatore Scarlata, Elia Ackermann, Oliver Hellwig,
Erica Biagetti and Sven Sellmer, whose initials are on every token in the `Annotator`
field. Its own machine-readable metadata declares `Lemmas: converted from manual`,
`Features: converted from manual`, `Relations: manual native`, and `UPOS: automatic with
corrections` — so it is **human-validated published annotation**, which is not the same
thing as annotation typed from scratch by a human, and the distinction is recorded on
every source row rather than smoothed over.

| Recension | Sentences in the treebank | Aligned to our verses | Distinct mantras reached |
|---|--:|--:|--:|
| Ṛgveda (ṚV) | 4,352 | 4,057 | 2,026 |
| Atharvaveda Śaunaka (AVŚ) | 2,175 | 1,787 | 886 |
| Yajurveda Mādhyandina (VSM) | 622 | 423 | 160 |
| Sāmaveda | **0** | — | **0** |
| **Total** | **7,149** | **6,267** | **3,072** |

The Samavedic zero is the third independent negative, after DCS (271 corpora) and VedaWeb
(7 texts) in Wave 0. Wave 0's candidate `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE` for
Samavedic morphology is now supported by three sources rather than two, and this agent
adds a consequence Wave 0 did not state: **1,844 Samavedic mantras carry 8,559
enrichment edges — 3,036 `USES_FORMULA`, 2,161 `MENTIONS_ENTITY`, 2,027 `ABOUT_CONCEPT` and
1,335 `MENTIONS_DEVATA` — and not one of them can be adjudicated against any published
annotation that exists.** The
Samaveda is not merely unannotated; it is unscoreable.

**VedaWeb / Zurich** was not fetched, because it is already inside the graph. Every
Rigvedic `MENTIONS_DEVATA` edge carries its Zurich lemma and case verbatim in its own
evidence quote (`agním (agní-; ACC/SG/M)`), and 10,031 `:Lemma` nodes carry the Zurich
lemma inventory. That is used here for two things: the deity-to-lemma bridge, and as a
second independent witness on the verse address.

### The Yajurveda was only reachable after transliteration

The first alignment pass put all 622 VSM sentences below the floor, because the Yajurvedic
and Samavedic canonical texts are Devanagari-only and the treebank is Latin-only.
Transliterating Devanagari to IAST before comparison recovered 423 of them. Without that
step the Yajurveda would have been reported as uncovered by published annotation, for the
wrong reason.

---

## 2. The reference set: what it is, and what it is not

`data/staging/quality/rows.jsonl`

**Type: `INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET`.** Not human gold. The word *gold*
appears in no row. Every row states why:

> no human annotated any VedaGraph claim. The human annotation is of the Vedic text, and
> this agent derived the verdict from it mechanically.

That is one step removed from human review of our own assertions, and it is the strongest
thing obtainable without commissioning an annotator. Three adjudicators are used, and
every row names which one decided it:

| Adjudicator | What it decides | Claims |
|---|---|--:|
| `PUBLISHED_HUMAN_TREEBANK` | is this word in this verse, and which word is it | 9,808 |
| `DETERMINISTIC_TEXT_DERIVATION` | does the verse's syllable count match its metre | 1,402 |
| `INDEPENDENT_MODEL` | does the verse support this semantic predicate | see §8 |

11,210 adjudicated claims, folded to **3,951 rows** — one row per verse per reference,
because the ingestion contract admits one row per `(canonical_key, source_id)` and a
second row for the same pair is indistinguishable from a duplicate that lost its context.
The claim count lives in the payload, not in row multiplicity. 2,568 rows are typed
`EXACT` and 1,383 `PROBABLE`; **1,166 of 3,072 verse addresses are confirmed by a second
independent annotation** (below).

### Stratification

Rows carry a `stratum` block and are stratified across: **four Vedas** (three reached, the
Samavedic zero recorded as a row-less negative rather than omitted); **six predicate
families** (`MENTIONS_DEVATA`, `MENTIONS_ENTITY`, `ABOUT_CONCEPT`, `HAS_CHANDAS`,
`SEMANTIC_ASSERTION_LLM`, `SEMANTIC_ASSERTION_MORPHOLOGY`); **certainty levels**
(`DEITY_CERTAIN` / `DEITY_PROBABLE` / `DEITY_AMBIGUOUS`, and the five distinct
`referent_basis` rules under them); **quality tiers** (`TIER_A` / `TIER_B` ×
`PER_PASSAGE` / `CONTAINER_INHERITED`); **confidence values** (0.55 through 1.0);
**ambiguity** (each row carries the surface class of the alias that produced it —
unambiguous, ambiguous or unattested); and **difficult negatives** — the 570 aliases that
never occur as a word in 206,440 human-annotated words are carried in `rejected.jsonl`
with that reason, because an alias that cannot fire correctly is the hardest negative
there is.

### How honest the addresses are

A treebank sentence cites a hymn, never a verse, so every address was established by text
similarity: containment of the sentence's de-accented, de-spaced skeleton in a verse of
the cited hymn, accepted above 0.62 and only when the winner beat the runner-up by 0.06.
That alone does not earn `EXACT`, so two checks were applied.

- **Monotonicity.** Treebank sentences are ordered within a hymn, so the verse numbers they
  align to must not go backwards. 5,541 adjacent pairs, **90 backwards jumps (1.62%)**.
  Both sides of every jump were quarantined — 176 sentences — because the evidence says
  one of the two is misaddressed and does not say which.
- **A second annotation.** For the Rigveda the graph already cites the Zurich lemma verse
  by verse. A row where the treebank annotation and the Zurich citation name the same
  lemma for the same canonical key has been addressed identically by two unrelated
  annotation projects. Only those rows are typed `EXACT`; the rest are `PROBABLE` and by
  the ingestion contract are staged and not importable.

805 sentences were refused as `AMBIGUOUS_MARGIN` and 77 as `BELOW_FLOOR`. They are in
`rejected.jsonl` with the reason, not forced onto a best guess, because a wrong verse
address resolves exactly as cleanly as a right one.

### The bridge, and why it is written down

Our registry prints the deity of the waters as `āpaḥ`; the treebank prints its lemma as
`ap`. Same word, two citation conventions. A first scoring pass reported **196 Rigvedic
deity mentions as refuted** and almost all of them were that. No string rule separates
that case from a genuine wrong-word match without also merging words that differ, so the
reconciliation is a file — `data/staging/quality/bridge_allomorphs.json` — with the human
token count beside every entry, its grounds, and the two entries that were **considered and
refused** (`pṛthivī`/`bhūmi`, `vāta`/`vāyu`). It is typed `MODEL_ADJUDICATED_BRIDGE`, it
decides only whether two *labels* are the same word, and it decides nothing about any
graph claim.

---

## 3. Precision, recall, F1

Measured on the 3,072 mantras a human annotated. Recall is computed only over the 1,074
mantras whose annotation covers at least 80% of the verse, because a partly-analysed verse
manufactures false negatives — and only over the entities whose own word could be bridged
to a human lemma: **71 of 214 deities and 203 of 229 concepts.** The 143 unbridged deities
are the composites and the rare ones, which carry no alias list and no Zurich lemma, so
their recall is unmeasured rather than measured as zero. The recall denominator admits an
entity's *own* word only; the synonym aliases of §3 are deliberately excluded from it, so
no false negative is manufactured by a registry grouping.

Two precisions are reported, and the difference between them is the whole point.

- **Lexical precision** — is the word the pipeline matched actually a word of this verse,
  and is it the word that surface form is everywhere else? This is the claim the layer's
  own `method` field makes.
- **Strict precision** — and is that word the one this entity names? A row that passes
  lexical and fails strict fired on a *synonym* the registry chose to list, not on a
  parsing error.

| Layer | Edges scored | Adjudicated | Lexical P | Strict P | Recall | F1 (lexical) | F1 (strict) |
|---|--:|--:|--:|--:|--:|--:|--:|
| `MENTIONS_DEVATA` | 2,725 | 2,413 | **0.994** | 0.994 | 0.507 | 0.671 | 0.671 |
| `MENTIONS_ENTITY` | 4,561 | 3,917 | **0.984** | 0.814 | 0.543 | 0.700 | 0.651 |
| `ABOUT_CONCEPT` | 4,024 | 3,478 | **0.982** | 0.804 | 0.443 | 0.610 | 0.571 |

Per Veda:

| Layer | RV lexical P | AV lexical P | YV lexical P | RV recall | AV recall | YV recall |
|---|--:|--:|--:|--:|--:|--:|
| `MENTIONS_DEVATA` | 0.996 | 0.983 | 1.000 | 0.581 | 0.439 | 0.389 |
| `MENTIONS_ENTITY` | 0.979 | 0.995 | 0.994 | 0.527 | 0.556 | 0.487 |
| `ABOUT_CONCEPT` | 0.977 | 0.993 | 1.000 | 0.476 | 0.417 | 0.436 |

**The shape of this result is the finding.** Precision is high everywhere and recall is
roughly a coin toss everywhere. The product's coverage figures count edges that exist; the
recall column counts the ones that should. A user reading "77.2% of Rigvedic mantras carry
entity mentions" is reading a statement about mantras touched at least once, not about
entities found.

### False-positive classes

| Class | `MENTIONS_DEVATA` | `MENTIONS_ENTITY` | `ABOUT_CONCEPT` | What it is |
|---|--:|--:|--:|---|
| `REGISTRY_ALIAS_NOT_THE_ENTITY_LEMMA` | 0 | 666 | 617 | the word is there and it is a different word the registry chose to group under this entity |
| `AMBIGUOUS_SURFACE_WRONG_WORD` | 8 | 34 | 33 | the surface is there, and here it is a different word from the one that surface usually is |
| `MATCHED_INSIDE_A_WORD_NOT_A_WORD` | 7 | 30 | 31 | the string is not a word of this verse; the match was inside one |

The first class is not a bug, it is a **visible editorial layer that nothing currently
surfaces**. 314 of 1,668 registry aliases resolve, in the human corpus, to a lemma that is
not the entity's own word: `ājya` under *ghṛta*, `adhvara` under *yajña*, `yaśas` under
*śravas*, `dhana` and `rādhas` under *rayi*, `bala` and `śavas` and `sahas` under *ojas*.
Every one of those is a defensible scholarly choice and none of them is stated to the
reader. Two look like genuine defects rather than choices: **`vāyu` is listed under
`VG:CONCEPT:VATA-WIND` for 173 human-annotated tokens** while the graph maintains
`VG:DEVATA:VAYUH` as a separate entity, and `VG:CONCEPT:VI-BIRD` carries the two-character
label `vi` with `suparṇa`, `vayas` and `śyena` beneath it.

The third class is small but it is the one with a named cause: it is concentrated in the
`sandhi` methods, which match inside a de-spaced string — `concept-alias-v1:sanskrit-sandhi`
(476 edges) and `formula-occurrence-sandhi-substring-v1` (2,109 edges).

### False-negative classes

| Class | `MENTIONS_DEVATA` | `MENTIONS_ENTITY` | `ABOUT_CONCEPT` |
|---|--:|--:|--:|
| `INFLECTION_ABSENT_FROM_ALIAS_LIST` | 480 | 637 | 661 |
| `ALIAS_LISTED_BUT_NOT_MATCHED` | 208 | 358 | 552 |

The first is the dominant one and it names the fix: **the alias lists are partial
inflection tables, not paradigms.** `AGNI-FIRE` carries seventeen forms of a stem that has
far more, and the human annotation shows the word present under a form the list does not
hold. This is a recall ceiling built into the registry, and it is repairable without any
new source — the graph already holds the Zurich lemma inventory (§6).

The second class is a genuine pipeline miss: the form *is* listed, the human annotation
shows it in the verse, and no edge exists. One alternative cause this measurement cannot
exclude is recorded in the proof: the merged alias namespace refuses an alias claimed by
two entities, so some of these may be edges that exist and point elsewhere.

### Per alias, because per row cannot see it

An earlier audit in this project found two random samples reporting 97%+ while a single
alias was 82.9% wrong. So every alias with at least five adjudicated edges is scored
individually — 631 of them, in `proofs/alias_soundness.json`. Inside layers measuring
98%, these aliases measure:

| Layer | Entity | Alias | Adjudicated | Lexical P |
|---|---|---|--:|--:|
| `ABOUT_CONCEPT` | `SOMA-PRESSING` | `sute` | 12 | **0.333** |
| `MENTIONS_ENTITY` | `SOMA-PRESSING` | `sute` | 9 | **0.333** |
| `MENTIONS_ENTITY` | `SOMA-DRINK` | `indur` | 5 | **0.400** |
| `MENTIONS_ENTITY` | `AHAN-DAY` | `divā` | 5 | 0.600 |
| `ABOUT_CONCEPT` | `SOMA-PRESSING` | `sutāsaḥ` | 6 | 0.667 |
| `ABOUT_CONCEPT` | `GO-CATTLE` | `gāḥ` | 6 | 0.667 |

A layer-level 98% contains aliases that are wrong two times in three. The per-row rate
cannot see that and the per-alias table can.

---

## 4. The central finding: the confidence constants are not probabilities

`proofs/calibration.json`

### Ground one — the value is mostly a constant

76,050 edges carry a `confidence`. **50,468 of them carry exactly `1.0`**; 12,782 carry
0.85 and 11,310 carry 0.80. Those three values cover 98.0%. Five predicates —
`HAS_RISHI` (17,889), `HAS_CHANDAS` (16,331), `HAS_DEVATA` (10,558),
`HAS_DEVATA_ASCRIPTION` (5,385) and `BELONGS_TO_FAMILY` (305) — stamp **one value on every
edge they have**. A `min_confidence` threshold over those 50,468 edges either keeps all of
them or none, and keeping them is not evidence of anything.

The product's own graph service already says this, in `CONFIDENCE_FILTER_CAVEAT`. What it
could not say, because no evaluation set existed, is what the number costs a reader. That
is ground two.

### Ground two — one nominal value spans 26 points of measured accuracy

`HAS_CHANDAS` is the layer to test, because a metre name is a claim about syllable count
and the verse settles it with no opinion involved. Each verse's syllables were counted and
compared with the **median count of every verse carrying the same metre name**, which
cancels the systematic under-count that sandhied saṃhitā spelling produces — a correct
triṣṭubh routinely counts 43 rather than 44, and a fixed nominal target would report a
whole metre as divergent when the bias is in the counter.

**Every edge in this table says `confidence: 1.0`.**

| Bucket | Adjudicated | Observed accuracy |
|---|--:|--:|
| RV, `TIER_B` / `CONTAINER_INHERITED` | 6,266 | **0.976** |
| RV, `TIER_A` / `PER_PASSAGE` | 4,206 | **0.962** |
| AV, `TIER_A` / `PER_PASSAGE` | 725 | **0.924** |
| AV, `TIER_B` / `CONTAINER_INHERITED` | 3,615 | **0.714** |

One nominal value; 71.4% to 97.6% observed. **A reader who filters `confidence >= 1.0` on
Atharvavedic metre is accepting a bucket that is wrong more than one time in four, and the
number they filtered on told them it was certain.** The axis that does carry the signal —
`quality_tier` with `attribution_precision` — is already on every edge, and in the
Atharvaveda it separates the buckets by 21 points.

**The median method validates itself.** Each metre's median count lands on its canonical
nominal, or one short of it where restoration accounts for the difference:
`ānuṣṭubham` 32 (nominal 32), `gāyatram` 24 (24), `trāiṣṭubham` 43 (44), `jagatī` 47 (48).
A syllable counter that agreed with no canonical total would be measuring itself.

**And the Atharvavedic divergence is concentrated, which makes it actionable.** Of the
1,033 divergent inherited edges, 571 are labelled `trāiṣṭubham` and 416 `ānuṣṭubham` —
95.6% under two labels — with deviations running from −37 to +38 syllables. These are
verses assigned a fixed-count metre by hymn-wide inheritance whose own length is nowhere
near it. Since the Atharvavedic Anukramaṇī names a per-verse metre *precisely when* it
differs from the hymn's, these 987 verses are very likely the ones whose explicit metre
was never extracted — the kāṇḍa-20 absence and the tail-grammar residuals Wave 1 recorded.
The syllable count is therefore not only a defect detector here; it is a **worklist**, and
it is ordered by how far each verse sits from its claimed metre.

### Ground three — where the value does vary, it does not order accuracy

`ABOUT_CONCEPT` is the only high-volume predicate whose confidence varies at all.

| Nominal confidence | Method | Adjudicated | Lexical P | Strict P |
|--:|---|--:|--:|--:|
| 0.80 | `concept-alias-v1:sanskrit-token` | 1,245 | 0.963 | 0.728 |
| 0.85 | `concept-alias-v1:english+sanskrit-token` | 2,132 | 0.992 | 0.852 |
| 0.89 | `concept-alias-v1:english+sanskrit-token` | 69 | 1.000 | **0.739** |

0.80 to 0.85 moves lexical precision in the right direction, by 3 points for 5 points of
nominal confidence. But 0.89 — nominally the most confident bucket in the layer — measures
**below 0.85 on the strict reading**, and the ordering inverts. What the value actually
encodes is which code path fired: 0.80 for a Sanskrit token match, 0.85 when an English
gloss agreed as well, 0.55 for a sandhi-insensitive match. It is a **pipeline prior**, and
the product's own backlog already names the rename. This report supplies the measurement
that the rename was waiting for.

### And the certainty labels do not order accuracy either

`MENTIONS_DEVATA` carries a `referent_certainty` of `DEITY_CERTAIN`, `DEITY_PROBABLE` or
`DEITY_AMBIGUOUS`. Against the human annotation:

| Certainty | Adjudicated | Lexical P |
|---|--:|--:|
| `DEITY_CERTAIN` | 1,132 | 0.995 |
| `DEITY_PROBABLE` | 282 | 0.997 |
| `DEITY_AMBIGUOUS` | 999 | 0.992 |

Flat. That is not a defect in itself: the certainty axis is about the *referent* — whether
`agní` here is the god or the fire — and a lemma annotation cannot settle that. What it
means is that **nothing in the graph orders the thing a reader thinks `DEITY_AMBIGUOUS`
warns them about**, and the label's own criterion can be tested. The `certain` basis is a
vocative address, and against hand-annotated case:

| Certainty and basis | Tokens found | Human says vocative |
|---|--:|--:|
| `DEITY_CERTAIN` / `certain` | 986 | **52.1%** |
| `DEITY_PROBABLE` / `R2_address_morphology` | 46 | **97.8%** |
| `DEITY_PROBABLE` / `R1_anukramani_corroboration` | 195 | 0.0% |
| `DEITY_AMBIGUOUS` / `identity_only` | 759 | 0.3% |

The tier labelled merely *probable* satisfies the vocative criterion 97.8% of the time; the
tier labelled *certain* satisfies it 52.1% of the time. **The certainty ordering is
inverted against its own stated basis.** Ordering by the number is worse than not ordering.

---

## 5. Three defects, one of which corrects a confirmed finding

### 5.1 Private Use Area codepoints in the canonical text

`proofs/pua_encoding_defect.json`

`corpus-audit.md` CORPUS_D01, confirmed by the lead, reads the Atharvavedic
`SEARCH_DERIVATIVE` layer as *"stripping the base letter along with its combining mark"*,
storing `kr̥dhi` as `kdhi`. **Nothing is stripped.** `VG:AV:SAU:K01:S002:V002` holds:

```
U+006B U+E000 U+0064 U+0068 U+0069
```

The two codepoints `r` + U+0325 were replaced by the *single* Private Use Area codepoint
U+E000, which has no glyph — so every terminal, browser and report renders it as nothing,
which is why two independent readers saw `kdhi` and inferred deletion. The same happened to
`tanvàṃ`: `ṃ` (U+1E43) became U+E003.

It is the same defect class Wave 0 rejected `Samved.xlsx` for — *"private-use-area
font-hack codepoints instead of Unicode accents"* — and it is inside the shipped corpus.

| Surface | Records carrying a PUA codepoint |
|---|--:|
| AV `SEARCH_DERIVATIVE` text | **5,123** of 5,839 |
| YV `PARALLEL_TEXT` text | **20** |
| `SemanticAssertion.root` | **393** of 2,406 (46 distinct roots) |
| Translations, aliases, lemmas, formulae, evidence quotes | 0 |

**The correction changes the remedy, and for the better.** The committed reading implies
the information is gone and the layer must be rebuilt from source. It is not gone: one
letter became one codepoint, and because every Atharvavedic mantra carries a clean
`PARALLEL_TEXT` beside the corrupted layer, the substitution table can be *derived* rather
than guessed. Aligning 5,123 pairs:

| PUA codepoint | Restores to | Observations | Agreement |
|---|---|--:|--:|
| U+E000 | `ṛ` (U+1E5B) | 5,076 | 0.9994 |
| U+E003 | `ṃ` (U+1E43) | 11,560 | 0.9994 |
| U+E001 | `ṝ` (U+1E5D) | 40 | 1.0000 |
| U+E002 | `ḷ` (U+1E37) | 10 | 1.0000 |

Four entries repair the whole layer losslessly. It also explains the symptom the lead
disproved: a *symmetric* substitution means query and index pass through the same mapping,
so search still matches — which is exactly what the lead measured and Agent 2 did not
expect.

### 5.2 1,176 mantras carry two contradictory metres at identical confidence

`proofs/attribution_tier_conflict.json`

| Predicate | Mantras with >1 value | Spanning tiers | At one confidence |
|---|--:|--:|--:|
| `HAS_CHANDAS` | 1,200 | **1,176** | 1,200 |
| `HAS_RISHI` | 307 | 0 | 307 |
| `HAS_DEVATA` | 6 | 0 | 6 |

An Anukramaṇī names a per-verse metre precisely when it differs from the hymn's, so the
disagreement is the index working. The defect is that **the inherited edge was not withdrawn
when the explicit one arrived.** A consumer reading `HAS_CHANDAS` on `VG:AV:SAU:K06:S073:V001`
is handed `bhurij` and `trāiṣṭubham` at `confidence: 1.0` each, with `quality_tier` as the
only thing that could break the tie and nothing in the API contract obliging a reader to
look at it. This is specific to metre — dedication and seer have no cross-tier conflicts at
all — so the fix is scoped.

### 5.3 `morphological_roles` is a closed vocabulary that is not closed

`proofs/morphological_role_vocabulary.json`

The mention layer writes a case onto every edge. Against the treebank's hand-annotated
`Case`:

| Measurement | Pairs | Agreement |
|---|--:|--:|
| As the strings stand | 1,951 | **0.616** |
| After folding the two vocabularies | 1,921 | **0.988** |

The 37-point gap is entirely one case under two names. The Rigvedic branch writes `NOM`,
`ACC`, `GEN`, `DAT`, `LOC`, `INS`; the Atharvavedic and Yajurvedic branch writes
`NOMINATIVE`, `ACCUSATIVE`, `GENITIVE`, `DATIVE`, `LOCATIVE`, `INSTRUMENTAL`. `VOCATIVE` is
the one value both spell the same way, which is why the problem hid. A query filtering
`morphological_roles CONTAINS 'NOM'` returns the Rigveda and reports an Atharvavedic zero —
the same false reading the AV deity caveat once served.

Two things follow. First, this agent nearly reported a vocabulary split as a 37-point accuracy
defect; it is the third time in this project's recorded history that an un-enumerated value
space produced a false reading, and the lesson held only because the mismatches were read
rather than counted. Second, **the real accuracy is 98.8%** — the mention layer's morphology
is good, and nothing in the graph's confidence says so while the vocabulary split makes a
naive consumer measure it at 61.6%.

The residual 24 genuine disagreements have named classes, the largest being `VOCATIVE`
claimed where the human annotation says nominative (7 edges). Five further value names are not a case
at all — `SANDHI_FUSED`, `PLURAL_OBLIQUE`, `COMPOUND_INITIAL`, `COMPOUND_FINAL` and
`UNKNOWN`, 30 instances among the pairs measured — which are informative labels on a
different axis, sharing one field with the cases.

---

## 6. `MENTIONS_LEMMA` scored as what it is

Scoring this as a morphology layer would be a category error, so it is scored as a theonym
mention index — and against the inventory **the graph already holds**, which needs no
external reference at all.

| Measure | Value |
|---|--:|
| `:Lemma` nodes | 10,031 |
| Mantra–lemma pairs implied by those nodes' own `mantra_count` | **154,261** |
| `MENTIONS_LEMMA` edges built | 9,000 |
| Distinct lemmas wired | 39 |
| Recall against the graph's own inventory | **5.8%** |
| Recall within the 39 lemmas it attempted | **99.94%** |

The layer is near-perfect at what it attempted and reaches 5.8% of what the graph can
already address. The inventory is not a wish list: 8,897 nominal stems, 702 roots, 406
invariables and 26 pronouns, each carrying its own token and mantra counts. **A Rigvedic
morphology layer is latent in the graph and 9,992 of its 10,031 nodes are isolated.** This
is also the fix for the dominant false-negative class in §3: the inflection tables the
alias lists lack are derivable from lemma nodes that are already present.

---

## 7. The semantic assertion layers

### The morphology-rule layer, against hand-annotated morphology

2,406 assertions carry `derivation: MORPHOLOGY_RULE`. 485 fall on annotated verses; 364 of
those had their verb token found by the human annotators.

| Measure | Value |
|---|--:|
| Root agrees with the human lemma | 299 |
| Root disagrees | 65 |
| Person agrees | 363 of 485 |
| Human annotation says the token is not a verb | **0** |

Zero is the notable number there: the rule never mistook a non-verb for a verb. Of the 65
root disagreements, a large part are the PUA roots of §5.1 — `kariṣyási` stored as `k`+U+E000
— which is an encoding defect masquerading as a morphology defect, and the remainder are
genuine granularity differences where the treebank lemmatises a causative or intensive to
its base (`ávartayat` → `vartay` against a claimed `vṛt`).

### The LLM layer, and the 17-versus-0 discrepancy resolved

| Derivation | Slots 0 | 1 | 2 | 3 |
|---|--:|--:|--:|--:|
| `MODEL_EXTRACTION` (claude-opus-5) | **1,522** | 730 | 190 | **17** |
| `MORPHOLOGY_RULE` | 0 | 0 | **2,406** | 0 |

`agent-1-verification.md` records that benchmark Q67 claimed 17 assertions carry three role
slots and that the live measurement was 0. **Both figures are right and neither report was
wrong.** 17 assertions carry three role *edges*; 0 carry one edge of each of the three
*types*. The disagreement was in the predicate, not the count, and the 1,522 figure both
reports give is exact. Agent 1's schema limit is also confirmed: `ASSERTION_AGENT` points
only at `:Devata` (2,502 edges), `ASSERTION_TARGET` only at `:Devata` (799), and
`ASSERTION_PREDICATE` only at `:ActionPredicate` (2,672).

All 2,459 `MODEL_EXTRACTION` nodes carry `human_gold_status: UNANNOTATED`,
`review_state: UNREVIEWED` and `state: CANDIDATE`, so the layer has never claimed to be
reviewed. §8 is the first independent scoring it has had.

---

## 8. Evaluation independence

Campaign section 26 forbids the same model both creating an assertion and declaring it
correct. That constraint bites hard here, because the 2,459 LLM assertions were extracted
by **claude-opus-5**, and this agent **is** claude-opus-5. So:

| What was scored | Who scored it | Why that is independent |
|---|---|---|
| `MENTIONS_DEVATA`, `MENTIONS_ENTITY`, `ABOUT_CONCEPT` | published human treebank | no model of this project contributed to any verdict |
| `HAS_CHANDAS` | a syllable count | no model and no annotation; the text settles it |
| `morphological_roles` | hand-annotated `Case` | as above |
| `MENTIONS_LEMMA` | the graph's own Zurich inventory | the reference predates and is independent of the layer |
| `SemanticAssertion` (`MODEL_EXTRACTION`) | the provider configured in `.env` | different vendor, different family, different weights |
| the entity↔lemma bridge, the error-class taxonomy | claude-opus-5, this agent, **declared** | judgements about *labels*, never about a graph claim |
| `theonym_mention_gold_v1` | **not re-adjudicated** | it was written by claude-opus-5; §9 tests it against human annotation instead |

The LLM adjudication is capped and recorded rather than open-ended: `CALL_CAP = 22` calls
of 5 assertions each, `temperature = 0.0`, sample seed 20260915, stratified by predicate
and slot count. **A quota or rate-limit error is recorded and the run stops — it is never
retried in a loop**, per the standing lesson that retrying a daily quota burns it. The
model id, the call count and the stopping reason are in the manifest and in
`proofs/precision_recall.json`.

---

## 9. The three existing gold files

`proofs/existing_gold_audit.json`

| File | Rows | Annotator | Verdict |
|---|--:|---|---|
| `rigveda_semantic_gold_v1.jsonl` | 120 | `UNANNOTATED` × 120 | **empty scaffold** |
| `theonym_mention_gold_v1.jsonl` | 575 | `MODEL_ADJUDICATED` × 575 (claude-opus-5) | **model adjudication** |
| `ask_benchmark_v1.jsonl` | 60 | *(no annotator field)* | **not an annotated set at all** |

The semantic set holds 0 entities and 0 relations across all 120 rows, every
`annotated_at` is `1970-01-01T00:00:00Z`, and its two declared companion files do not
exist. It is a sampling frame — and the right 120 verses to annotate — carrying no
annotation.

The Ask benchmark is 60 questions with no expected answer and no reference. Whatever graded
the Ask product, it was not this file.

The theonym set was not re-adjudicated by this agent, because section 26 forbids it. It was
tested against human annotation instead, wherever the treebank reaches the same verse:
**74 rows reachable, 72 decidable, and the model adjudication agrees with the human
annotation on 54 of them — 75%.** That figure needs three caveats stated plainly: n is 72,
the test is a proxy (does the human annotation carry a lemma in the claimed deity's lemma
set, and does that match the row's own label), and some of the divergence is by design —
the set deliberately includes borderline rows such as `DVANDVA_MEMBER`, where the model's
`NOT_MENTION` records a modelling choice rather than a factual claim. It is not 25% wrong.
It is 25% divergence on the only independent test available, which is more than enough to
say the set must not be promoted to gold without human review.

---

## 10. What could not be scored, and why

`proofs/negative_results.json`

| Layer | Status | Why |
|---|---|---|
| Anything Samavedic | `NO_REFERENCE_EXISTS` | third independent negative after DCS and VedaWeb; 8,559 Samavedic enrichment edges are unscoreable against any published annotation |
| Morphology as a layer | `THERE_IS_NO_LAYER_TO_SCORE` | 39 theonym lemmas against a 10,031-node inventory; §6 |
| Aboutness, as distinct from occurrence | `PARTLY_UNSCORABLE_BY_THIS_REFERENCE` | a lemma annotation settles which word is in a verse; it cannot settle whether a verse is *about* a concept. The lexical claim is scored, the aboutness question is left open rather than answered by this agent's opinion |
| Formula membership, parallels | `SCORED_STRUCTURALLY_ONLY, PREDATES_WAVE_2` | Agents 10 and 12 are rebuilding these in this wave |
| The referent decision (`DEITY_CERTAIN` vs the common noun) | `NO_REFERENCE_FOUND` | no published annotation distinguishes *Agni the god* from *agni the fire* at token level; its stated *criterion* is tested in §4 instead |

On formula and parallel, as they stand and not to be quoted against Wave 2's rebuild:
22,686 `USES_FORMULA` edges, all `TIER_B`, of which 2,109 come from a sandhi-substring
method of the same class as the concept layer's 0.55 tier; `SHARES_FORMULA_WITH` still has
zero edges; and 5,808 parallel edges across four predicates carry **no transformation type
at all**, confirming `CROSS_VEDA-002`. One thing worth keeping: the parallel layer carries
`similarity`, `edit_ratio`, `lcs_ratio`, `token_jaccard` and `ngram_jaccard` — the graph's
only genuinely continuous quality measures, and what `confidence` should have looked like.

---

## 11. What the lead must decide

1. **Rename `confidence` to `pipeline_prior`, or gate it.** The measurement the existing
   backlog item was waiting for is now in `proofs/calibration.json`: one nominal value
   spanning 71.4% to 97.6%. The rename is blocked by the semantic hash seal on
   `src/vedagraph/semantic/ontology.py`, where the same word means a model's own output —
   so the bounded move is to expose `quality_tier` and `attribution_precision` as the
   filter and leave `confidence` unfilterable, rather than to rename inside the seal.
2. **Repair the PUA layers by substitution, not rebuild.** Four table entries, 5,143
   records, derived and verified at ≥0.9994 agreement. Correct `corpus-audit.md` CORPUS_D01
   and `agent-2-verification.md` at the same time: the current diagnosis prescribes the
   wrong fix, and Wave 1 already showed what closing a gap against a wrong prescription
   costs.
3. **Withdraw the inherited metre where a source-explicit one exists.** 1,176 mantras,
   scoped to `HAS_CHANDAS` alone.
4. **Close the `morphological_roles` vocabulary** and make an unrecognised value raise. The
   value space is enumerated in `proofs/morphological_role_vocabulary.json`.
5. **Wire the lemma inventory.** 154,261 pairs are addressable from nodes already in the
   graph; it is simultaneously the morphology layer and the fix for the dominant
   false-negative class.
6. **Do not promote anything to `HUMAN_GOLD`.** Nothing here is human gold and this agent
   did not create any. The 120-verse semantic scaffold is the right frame and needs a human;
   the 575-row theonym set needs human review before it is called gold, and its 75%
   agreement with human annotation on 72 decidable rows is the reason.
7. **Rule on the registry synonym layer.** 314 aliases group a different word under an
   entity. Most are defensible and none is disclosed. `vāyu` under `VATA-WIND` and the
   two-character label `vi` under `VI-BIRD` should be treated as defects rather than
   choices.

## 12. What this agent did not do

- **No canonical write.** Read-only Cypher throughout.
- **No human reviewed anything.** Not one VedaGraph claim was read by a person and graded.
  The reference is published human annotation of the Vedic text, which is one step removed,
  and every row says so.
- **No Samavedic figure of any kind.** 0 of 1,844 mantras are covered by any published
  annotation, from any of three sources.
- **No reliability curve.** A reliability diagram needs a confidence that varies
  continuously; this one takes 16 values of which three cover 98%. Calibration in the
  proper sense is not merely unmeasured here — the field's shape forbids it.
- **No aboutness verdict.** The `ABOUT_CONCEPT` layer is scored on the lexical claim its
  own `method` field makes, and not on the interpretive claim its name makes.
