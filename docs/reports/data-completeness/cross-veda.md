# Cross-Veda connection completion

Agent 10, Wave 2. Owner's section K: all six unordered Veda pairs, every dimension
measured with a legitimate definition, no cell left `NOT_ESTABLISHED` because nobody ran
the computation.

Neo4j was read-only throughout: `MATCH`/`RETURN` only, no `CREATE`, `MERGE`, `SET` or
`DELETE`. Nothing here is live. `data/staging/cross_veda/` passes
`scripts/validate_staging_artifact.py --graph` at 100% evaluation coverage on all 15
checks.

**The headline is not new coverage.** It is that the cross-Veda layer was already nearly
complete and was being read through a directed query that turned it into a set of false
zeros. Every one of the 48 matrix cells now resolves, and 31 of them resolve to a positive
count that was in the graph all along.

---

## 1. The matrix — 6 pairs × 8 dimensions, 48 cells, none unresolved

Counts are **undirected**. Section 2 is why.

| Dimension | AV-RV | AV-SV | AV-YV | RV-SV | RV-YV | SV-YV |
|---|--:|--:|--:|--:|--:|--:|
| `EXACT_PARALLEL_OF` | 551 | 9 | 7 | 89 | 24 | 70 |
| `NEAR_PARALLEL_OF` | 752 | 326 | 162 | 1,180 | 473 | 156 |
| `VARIANT_OF` | 22 | 132 | 41 | 415 | 165 | 13 |
| `REUSES_TEXT_FROM` | DIR N/S | DIR N/S | DIR N/S | **1,684** | DIR N/S | DIR N/S |
| `SHARES_FORMULA_WITH` | N/A | N/A | N/A | N/A | N/A | N/A |
| `SHARES_ENTITY_VOCABULARY_WITH` | 1,176 | 84 | 136 | 421 | 291 | 33 |
| Concept overlap | 91 | 86 | 89 | 86 | 89 | 86 |
| Semantic resemblance | N/A | N/A | N/A | N/A | N/A | N/A |

| Status | Cells |
|---|--:|
| `MEASURED_COUNT` | 31 |
| `DIRECTION_NOT_SUPPORTED` | 5 |
| `NOT_APPLICABLE` | 12 |
| `VERIFIED_ZERO` | 0 |

Every cell in `proofs/matrix.json` carries its method, population, count, quality tier, an
evidence drill-down query and a measurement note. **No cell is a verified zero**, because
not one of the six pairs is empty in any dimension that applies to it.

`SHARES_FORMULA_WITH` is `NOT_APPLICABLE` as an edge and measured through the hub instead:

| Pair | Shared formulas | Passage pairs |
|---|--:|--:|
| AV-RV | 2,086 | 10,553 |
| AV-SV | 843 | 2,047 |
| AV-YV | 907 | 4,320 |
| RV-SV | 1,862 | 7,436 |
| RV-YV | 1,278 | 4,979 |
| SV-YV | 560 | 1,097 |

---

## 2. The Yajurvedic asymmetry — implementation artifact, and provably so

CORPUS_D07 is confirmed and explained. One query settles it:

```cypher
MATCH (a)-[r]->(b)
WHERE type(r) IN ['EXACT_PARALLEL_OF','NEAR_PARALLEL_OF','VARIANT_OF']
RETURN CASE WHEN a.veda < b.veda THEN 'ASCENDING'
            WHEN a.veda = b.veda THEN 'SAME_VEDA' ELSE 'DESCENDING' END AS ord,
       count(r)
```

`ASCENDING 4587`, `SAME_VEDA 256`, **`DESCENDING 0`**.

Every cross-Veda edge of the three symmetric types runs from the alphabetically earlier
Veda code to the later one, and not one runs the other way. The order is `AV < RV < SV <
YV`, so the Atharvaveda is always the subject and the Yajurveda never is. That is a
storage convention, and the relations are **declared symmetric** in
`src/vedagraph/enrich/predicates.py::SIGNATURES` (`symmetric=True` on all three). The
1,975 Yajurvedic mantras were not skipped: the run emitted 687 Yajurveda-touching edges
across all three of its pairs.

So corpus-audit §4's open question — *"whether the Yajurveda was assessed as a subject and
rejected, or never assessed as one, is not recorded"* — has an answer. It was assessed as a
**member of every pair it belongs to**, and it is never a subject for one reason: its code
sorts last. The verdict is **implementation artifact, not a finding about the Yajurveda**.

The remedy is not a data change. It is that a consumer must use `-[r]-`, not `-[r]->`. The
undirected coverage figures reproduce the baseline exactly, which is the second proof that
the baseline's numbers were right and only the directed reading was wrong:

| Veda | Undirected parallel/reuse coverage |
|---|--:|
| RV | 2,850 / 10,552 = 27.01% |
| SV | 1,677 / 1,844 = 90.94% |
| YV | 687 / 1,975 = 34.78% |
| AV | 1,332 / 5,839 = 22.81% |

---

## 3. Direction — measured for all six, supportable for one

Direction was not left blank. Three structural signatures were measured for every pair
against a **degree-preserving permutation null**, 400 draws, seed 20260915
(`proofs/direction_null.json`). Both signatures that looked decisive turned out to be
confounded, and saying so is the result.

### Containment is corpus-size arithmetic

| Pair | Observed containment | Expected from size alone | **Excess** |
|---|--:|--:|--:|
| AV-RV | 1.94× | 1.81× | 1.08× |
| AV-SV | 3.28× | 3.17× | 1.04× |
| AV-YV | 2.94× | 2.96× | 0.99× |
| RV-SV | 6.69× | 5.72× | **1.17×** |
| RV-YV | 5.73× | 5.34× | 1.07× |
| SV-YV | 1.19× | 1.07× | 1.11× |

For `L` links spread anywhere, coverage of a corpus is about `L/|corpus|`, so the ratio of
two coverages is about the ratio of two corpus sizes before any reuse has happened. **The
Samaveda's 90.1% parallel coverage — the figure that makes the RV/SV direction look
self-evident, and which BASELINE.md and corpus-audit both highlight as the highest of any
Veda — is 5.72× explained by 1,844 verses against 10,552.** The excess is 1.17×.
Containment establishes no direction for any pair, including the one pair where a direction
is asserted.

### Contiguity is real, significant, and symmetric

| Pair | Lower Veda observed | Higher Veda observed | Null | z (lo / hi) |
|---|--:|--:|--:|---|
| AV-RV | 83.23% | 83.81% | ~0.14% | +740 / +690 |
| AV-SV | 74.16% | 67.98% | ~0.54% | +158 / +122 |
| AV-YV | 65.71% | 55.68% | ~0.55% | +71 / +76 |
| RV-SV | 75.20% | 56.51% | ~0.11% | +616 / +620 |
| RV-YV | 81.14% | 47.54% | ~0.22% | +258 / +263 |
| SV-YV | 59.70% | 47.19% | ~0.57% | +59 / +62 |

Random rewiring destroys block structure completely — the null sits near 0.5% — so the
finding is strong and it is a **new** one: the Vedas share **runs of adjacent verses**, not
just isolated verses, in all six pairs. But the significance is comparable on **both sides
of every pair**, and the raw rate difference is confounded by unequal coverage: the
low-coverage side's adjacent-and-both-covered verse pairs are a self-selected set. So
contiguity is a symmetric result and yields no direction.

### Verdict

**No size-independent structural signature in anything this project holds distinguishes
borrower from source for any pair.** The one direction the graph asserts, `REUSES_TEXT_FROM`
SV→RV over 1,684 edges, rests **entirely** on the witness in
`predicates.py::ESTABLISHED_REUSE` — the Kauthuma Ārcika being an arrangement of Rigvedic
verses for chanting, named as such by its own tradition. That is a legitimate witness and
the right one. It is not a measurement.

The five `DIRECTION_NOT_SUPPORTED` cells and why:

| Pair | Why direction is not supported |
|---|---|
| AV-RV | No witness names a borrower, and the structure is symmetric on every signature: excess containment 1.08×, contiguity 83.81% against 83.23%. This is the strongest "genuinely undirected" verdict of the six. |
| AV-SV | No witness. Excess containment 1.04×. |
| AV-YV | No witness. Excess containment 0.99× — below parity. |
| RV-YV | No witness. Excess containment 1.07×. The contiguity gap is the widest of the six (81.14% against 47.54%) and points RV→YV, but it is the confounded statistic and a scholarly position on Yajurvedic quotation is not a fact about this corpus. Recorded with its measurement, not promoted. |
| SV-YV | No witness. Excess containment 1.11×. |

Each of these is a resolved cell: it names its method, its population, the three measured
statistics and the specific thing that is missing — a witness, not a computation. That is
`GAP-CROSS_VEDA-001` closed as measured rather than filled.

### One defect this exposed

All 1,684 `REUSES_TEXT_FROM` edges carry `trust=DETERMINISTIC_DERIVED`,
`evidence_basis=SANSKRIT`, and two Sanskrit quotes as their stored `evidence`. **The
pairing is derived from the Sanskrit; the direction is not.** The edge records one evidence
axis where it has two, so an auditor reading the edge sees Sanskrit evidence offered for a
claim the Sanskrit cannot support. This is the two-axis hazard already on record for
`evidence_basis`, in a new place.

---

## 4. Transformation type — `GAP-CROSS_VEDA-002` closed, and reframed

The gap says none of 6,527 parallel and reuse edges records how the text was transformed.
Two corrections before the fix.

1. **1,538 of them already did**, through `match_level`: 750 `EXACT_PARALLEL_OF` (600 at
   `SCRIPT_FOLDED`, 150 at `ACCENT_INSENSITIVE`) and 788 `VARIANT_OF` (all at
   `SANDHI_INSENSITIVE`). The edges genuinely carrying nothing are the 3,049 near parallels
   and the 1,180 reuse edges co-emitted over them.
2. **The population of 6,527 conflates two layers.** It counts all 1,006
   `EXACT_PARALLEL_OF` edges, but 256 of those are intra-Rigvedic (§6).

All 6,596 edges of all five types now carry a derived transformation type, from the stored
text, on the strongest surface the two scripts can reach. Cross-Veda only:

| Transformation | Total | AV-RV | AV-SV | AV-YV | RV-SV | RV-YV | SV-YV |
|---|--:|--:|--:|--:|--:|--:|--:|
| `SINGLE_CONTIGUOUS_SUBSTITUTION` | 1,390 | 297 | 109 | 31 | 792 | 131 | 30 |
| `SCATTERED_SUBSTITUTIONS` | 1,295 | 215 | 103 | 67 | 745 | 107 | 58 |
| `WORD_DIVISION_ONLY` | 1,203 | 22 | 132 | 41 | 830 | 165 | 13 |
| `TWO_CONTIGUOUS_SUBSTITUTIONS` | 1,143 | 176 | 75 | 39 | 695 | 122 | 36 |
| `SCRIPT_CONVENTION_ONLY` | 471 | 470 | 0 | 0 | 0 | 0 | 1 |
| `INTERIOR_INSERTION` | 245 | 29 | 22 | 17 | 59 | 93 | 25 |
| `NO_CHANGE_OBSERVABLE_AT_REACHABLE_LEVEL` | 218 | 0 | 9 | 7 | 178 | 24 | 0 |
| `ACCENT_NOTATION_ONLY` | 150 | 81 | 0 | 0 | 0 | 0 | 69 |
| `INTERIOR_DELETION` | 114 | 23 | 13 | 4 | 59 | 13 | 2 |
| `TAIL_EXTENSION` | 22 | 3 | 3 | 2 | 4 | 7 | 3 |
| `SHARED_SEGMENT_ONLY` | 9 | 5 | 0 | 2 | 2 | 0 | 0 |
| `TAIL_TRUNCATION` | 8 | 2 | 1 | 0 | 4 | 0 | 1 |
| `PADA_REORDER` | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| `HEAD_EXTENSION` | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Total** | **6,271** | 1,325 | 467 | 210 | 3,368 | 662 | 239 |

Two deliberate restraints:

- **`NO_CHANGE_OBSERVABLE_AT_REACHABLE_LEVEL`, not "identical."** For a cross-script pair
  `SCRIPT_FOLDED` is the strongest surface reachable at all, so a difference below it is
  not observable. 218 edges are typed this way rather than claimed identical. The 471
  `SCRIPT_CONVENTION_ONLY` are the same finding where both editions are in one script and
  the claim *is* available.
- **Token-level operations are withheld for 4,074 of the 6,271** — every pair touching the
  Samaveda. Measured reason: for genuine near parallels the Samavedic token Jaccard median
  is 0.4615 against 0.6667 for every pair that does not touch it, and four stored near
  parallels have a token Jaccard of exactly 0. The Kauthuma Ārcika writes continuous sandhi,
  so a "reordered word" there is an artifact of the edition. Those edges carry
  `transformation_scope: CHARACTER_LEVEL`; the other 2,197 carry
  `CHARACTER_AND_TOKEN_LEVEL`. `PADA_REORDER` is therefore only ever asserted on AV-RV, and
  it fires twice.

A verification fell out of this: re-deriving the identity level from the text agrees with
the stored `match_level` on **every one of the 750 cross-Veda `EXACT_PARALLEL_OF` edges,
1,203 `SANDHI_INSENSITIVE` and 689 `SCRIPT_FOLDED`**. The cross-Veda pipeline reproduces
exactly.

---

## 5. Thresholds, calibrated on this population and not inherited

The brief warned that `vedsearch.similarity`'s all-Veda mispaired maximum of 0.8413 must
not be inherited, and that Agent 7 measured 0.4859 for the Atharvaveda alone. Neither
figure was adopted. The ceiling was re-measured here, per pair, over **20,000 random
unlinked pairs each — 120,000 draws** (`proofs/calibration.json`), with the same comparator
this report uses: a character LCS ratio over the sandhi-insensitive surface with
`autojunk=False`.

| Pair | mean | p99 | p99.9 | **max** | ≥0.72 |
|---|--:|--:|--:|--:|--:|
| AV-RV | 0.2236 | 0.3596 | 0.4112 | 0.4810 | 0 |
| AV-SV | 0.2260 | 0.3680 | 0.4144 | 0.4952 | 0 |
| AV-YV | 0.2160 | 0.3582 | 0.4100 | 0.5185 | 0 |
| RV-SV | 0.2312 | 0.3738 | 0.4220 | 0.4954 | 0 |
| RV-YV | 0.2199 | 0.3594 | 0.4040 | 0.4714 | 0 |
| SV-YV | 0.2217 | 0.3636 | 0.4068 | **0.5225** | 0 |

Two Vedic verses in the same register share about 22% of their characters by subsequence
before any reuse is involved. **Not one of 120,000 mispaired draws reaches 0.72, and none
reaches 0.53.** So the existing `NEAR_PARALLEL_FLOOR` of 0.72 is retained — but on this
evidence, sitting 0.1975 above the worst false positive this population produced, not on
the say-so of the module that set it. The inherited 0.8413 is not reproducible here and
belongs to a different comparator on a different population.

### The stated floor is not the operating point

Re-deriving this comparator on the 3,049 near parallels the layer **accepted**:

| | min | p01 | p05 | p25 | median | max |
|---|--:|--:|--:|--:|--:|--:|
| accepted near parallels | 0.6196 | 0.8692 | 0.9026 | 0.9540 | **0.9767** | 0.9966 |

The declared floor is 0.72; the revealed operating point is about 0.90. Anything graded
against 0.72 would be admitted four times weaker than the layer's own median. Every new
candidate in this artifact is therefore graded against the **revealed** boundary, and the
distinction is recorded on each row.

---

## 6. What `PARALLEL_TO` and `EXACT_PARALLEL_OF` currently mean

Establishing this before adding anything was a condition of the mandate, and it found a
name collision.

| Type | Edges | Layer | Meaning | Provenance |
|---|--:|---|---|---|
| `EXACT_PARALLEL_OF` | 750 | cross-Veda | identical text on the strongest reachable surface | run `5bf3c9ce73209098`, carries `parallel_id` |
| `EXACT_PARALLEL_OF` | 252 | intra-Rigvedic | identical **stored** text (`SOURCE_EXACT`) | no `run_id`, no `pipeline_version`, no `parallel_id` |
| `EXACT_PARALLEL_OF` | **4** | intra-Rigvedic | identical **lemma sequence** — the text differs | as above; stored similarity 0.617–0.878 |
| `PARALLEL_TO` | 69 | intra-Rigvedic | `HIGH_CONFIDENCE_NEAR_PARALLEL`; **not a cross-Veda relation at all** | as above |
| `NEAR_PARALLEL_OF` | 3,049 | cross-Veda | substantially the same verse, materially altered | run `5bf3c9ce73209098` |
| `VARIANT_OF` | 788 | cross-Veda | same verse, different editorial spelling | run `5bf3c9ce73209098` |
| `REUSES_TEXT_FROM` | 1,684 | cross-Veda | directed borrowing, SV→RV only | run `5bf3c9ce73209098` |

Two consequences.

**`GAP-CROSS_VEDA-003` is not a cross-Veda gap.** All 256 `EXACT_PARALLEL_OF` edges without
a `parallel_id` are RV-to-RV, from a layer that carries `parallel_id` on no edge and never
did. Asking them for "the parallel group they belong to" is a category error, and the
sentinel test at `tests/api/test_graph.py:805-814` is waiting for something that will not
arrive.

**The live defect in those 256 is narrower and worse.** Four of them mean `EXACT` in the
sense of lemma-sequence identity:

| Subject | Object | `strongest_method` | Stored similarity |
|---|---|---|--:|
| `VG:RV:SAK:M09:S033:V003` | `VG:RV:SAK:M09:S034:V002` | `LEMMA_SEQUENCE_EXACT` | 0.617 |
| `VG:RV:SAK:M09:S036:V004` | `VG:RV:SAK:M09:S064:V005` | `LEMMA_SEQUENCE_EXACT` | 0.639 |
| `VG:RV:SAK:M09:S036:V005` | `VG:RV:SAK:M09:S064:V006` | `LEMMA_SEQUENCE_EXACT` | 0.683 |
| `VG:RV:SAK:M10:S159:V004` | `VG:RV:SAK:M10:S174:V004` | `LEMMA_SEQUENCE_EXACT` | 0.878 |

A reader asking for exact parallels gets four rows whose texts differ — the last by a
single `ā`/`aḥ`, the first three by three separate edits each — and nothing in the
relationship type says the match was made on lemmas. Either type them by what was matched
or surface `strongest_method`; a filter labelled "exact" must not answer with 0.617.

---

## 7. `SHARES_FORMULA_WITH` — the zero is a decision, and `GAP-FORMULA-001` should be withdrawn

`GAP-FORMULA-001` records that `SHARES_FORMULA_WITH` is the only declared relationship type
with zero edges, counted individually rather than read off a census — so a real absence
rather than a census artifact. The counting is right. The conclusion is wrong.

The zero is **deliberate and already recorded as data**, not only as prose, at
`src/vedagraph/enrich/predicates.py::UNPOPULATED_BY_DESIGN`: the Formula hub carries the
relation losslessly in two hops, `(a)-[:USES_FORMULA]->(f)<-[:USES_FORMULA]-(b)`, and
materialising it would add 87,296 edges in place of 27,511 — the widest formula spans 93
passages and would emit 4,278 edges by itself. That map's own docstring anticipates exactly
this audit: *"an audit enumerating `db.relationshipTypes()` found a type with no rows and
correctly reported it as an undocumented dead filter option — the rationale existed, in a
place nothing querying the database would look."*

So: `NOT_APPLICABLE` as an edge in all six cells, and the dimension measured through the
hub in all six (§1). **The registry's prescription to populate it should be withdrawn.** The
real surface fix is that a consumer browsing relationship types cannot see the rationale;
the ontology reference should read `UNPOPULATED_BY_DESIGN`.

---

## 8. Concept overlap is measured, positive, and cannot discriminate

All six cells are `MEASURED_COUNT`. They are also nearly identical, and that is the finding.

| Pair | Shared concepts | Jaccard |
|---|--:|--:|
| AV-RV | 91 | 1.0000 |
| AV-YV | 89 | 0.9780 |
| RV-YV | 89 | 0.9780 |
| SV-YV | 86 | 0.9663 |
| AV-SV | 86 | 0.9451 |
| RV-SV | 86 | 0.9451 |

`ABOUT_CONCEPT` reaches only **91 of the 229** Concept nodes in the graph, and every Veda
touches nearly all 91. The pairwise Jaccard therefore runs 0.9451 to 1.0 and separates
nothing: a reader shown "AV and RV share 100% of their concepts" would conclude something
about the corpora when the figure is a property of a 91-node registry.

The passage-pair count this generates is worse and must not be published: 1,639,722 for
AV-RV. It is the combinatorial product of two concept-tagged sets, not a connection count.
The cell records the concept-level number and says so.

`MENTIONS_ENTITY` reaches all 229 entities and would give a higher-resolution version of
this dimension. It was not substituted, because swapping the population under a dimension
name is how a figure stops being comparable to the one it replaces. Recorded as the obvious
next measurement.

---

## 9. Adversarial QA — 11 cases, all four referent traps

`proofs/adversarial.json`. Each case names real canonical keys and runs the real comparator.

| Case | Trap | Verdict |
|---|---|---|
| ADV-A1 | accent-only difference read as a change in the text | **REJECTED** |
| ADV-A2 | formulaic boilerplate shared across Vedas | **EXPOSED** → §10 |
| ADV-A3 | common high-frequency Sanskrit as the only shared material | **REJECTED** |
| ADV-A4 | byte-identical translations on two verses | **REJECTED** |
| ADV-A5 | same concept, different vocabulary | **EXPOSED** → §10 |
| ADV-A6 | Samavedic repetition — best match is not a counterpart | **CONTAINED** |
| ADV-A7 | same words, different meaning | **CONTAINED** (scope boundary) |
| ADV-B1 | Soma the deity vs soma the substance | **CONTAINED** |
| ADV-B2 | Agni the deity vs physical fire | **CONTAINED** |
| ADV-B3 | Vāc the deity vs speech | **CONTAINED** |
| ADV-B4 | Indra in a simile vs Indra as dedicatee | **CONTAINED** |

**ADV-A3** is the clean rejection: the highest-scoring pair of 120,000 random unlinked
cross-Veda draws is `VG:SV:KAU:UTTARA:P04:R01:D13:V02` / `VG:YV:VSM:A33:V010` at 0.5225,
against a floor of 0.72.

**ADV-A4** has no instance to fire on, and the reason is worth recording rather than
glossing: 46 translation strings over 60 characters are shared by more than one mantra, and
**0 of those cross a Veda boundary**. It could not fire in any case — every textual
dimension records `evidence_basis: SANSKRIT` and the stored `evidence` on each edge is the
two Sanskrit quotes. The translation layer is never an input.

**ADV-A6** is the Samavedic tie problem the mandate named. **357 of 472 multi-candidate
slots have their top two candidates within 0.01 similarity, and 250 of those touch the
Samaveda.** Worked example: `VG:RV:SAK:M09:S061:V011` in RV-SV scores 0.9098 against
`VG:SV:KAU:UTTARA:P01:R01:D08:V03` and **0.9098** against `VG:SV:KAU:ARANYA:D01:V08` — a
gap of exactly 0.0000. The layer is safe here by construction: it stores every candidate
above the floor rather than electing a winner, so no single counterpart is asserted
anywhere. A best-match design would have silently picked one of the two. All 357 slots are
published on their rows as `AMBIGUOUS_COUNTERPART` with both candidates and the gap.

Separately, `MAX_NEAR_PARALLELS_PER_MANTRA = 5` binds on **3 of 5,574** (mantra, pair)
slots — RV-SV 2, RV-YV 1 — so the cap is not materially truncating the Samaveda.

### The four referent traps

The ontology separates referents at the node level, and the vocabulary dimension is built
from Concept keys only, so no Devatā key enters it:

| Trap | Deity node | Concept node | Concept labels | Dedicated | Mention concept | **Both** |
|---|---|---|---|--:|--:|--:|
| B1 Soma | `VG:DEVATA:SOMAH` | `VG:CONCEPT:SOMA-DRINK` | Offering, Substance | 80 | 1,169 | **19** |
| B2 Agni | `VG:DEVATA:AGNIH` | `VG:CONCEPT:AGNI-FIRE` | NaturalPhenomenon | 1,988 | 1,028 | **448** |
| B3 Vāc | `VG:DEVATA:VAK` | `VG:CONCEPT:VAC-SPEECH` | PhilosophicalConcept | 3 | 651 | **2** |

Each deity/concept pair is two distinct nodes joined by `DEVATA_ASSOCIATED_WITH`, which
records the connection without asserting identity — the one edge the frozen ontology
provides for this, and the reason it refuses `IDENTIFIES_WITH` and `REPRESENTS` by name.

The "both" column is the trap's live surface and it is not small: **448 mantras are
dedicated to Agni the deity and also tagged with fire the natural phenomenon.** The trap is
contained rather than absent, and it is contained by typing: 406 vocabulary edges cite
`AGNI-FIRE` and **0 rest on it alone**, and every such edge carries its own statement that
vocabulary overlap is not a claim that the two passages express the same idea. No dimension
in this matrix reads a shared concept as a same-referent claim.

**B4** is the cleanest: 1,821 mantras mention Indra without being dedicated to him, against
2,869 that are. The two facts sit on different predicates, `MENTIONS_DEVATA` and
`HAS_DEVATA`, and **0** `SHARES_ENTITY_VOCABULARY_WITH` edges cite a Devatā key at all, so
the vocabulary dimension cannot collapse the distinction. The residual exposure is a
consumer that queries the union of the two predicates without saying which one answered.

**ADV-A7 is a scope boundary, not a passed test.** "Same words, different meaning" is not a
false positive for a textual dimension: two verses with the same words in the same order
*are* the same verse, and `EXACT_PARALLEL_OF` / `NEAR_PARALLEL_OF` / `VARIANT_OF` claim
nothing about meaning. The trap bites only a dimension that asserts shared sense, and this
agent asserts none — semantic resemblance is Agent 11's and is marked `PENDING_AGENT_11` in
all six cells rather than approximated from word overlap.

---

## 10. The two EXPOSED cases found missed parallels, not false ones — and they are marginal

ADV-A2 and ADV-A5 were built to show that boilerplate-only and concept-only pairs are
refused. Both found something else: unlinked pairs scoring **above** the floor. At 0.86 LCS
these are not false positives, they are parallels the candidate generator never proposed.

So the probe was run properly, over two candidate channels that share nothing with MinHash
char-4gram banding, exhaustively rather than sampled:

| Channel | Population | Already linked | Assessed | Below floor | **Above floor** |
|---|--:|--:|--:|--:|--:|
| `FORMULA_HUB` | 21,302 | 3,495 | 17,807 | 17,506 | 301 |
| `VOCAB_EDGE` | 2,141 | 19 | 2,122 | 2,096 | 26 |

**305 distinct unlinked cross-Veda pairs at or above 0.72**, in all six pairs. Diagnosis
(`proofs/recall_diagnosis.json`): 300 were never proposed at all, 4 lost a top-5 contest, 1
is below the generator's stated sensitivity. 237 sit at 4-gram Jaccard ≥ 0.44, the level the
module's docstring says the banding proposes in full.

**And then the claim has to be deflated, because comparing my score to their threshold
would be comparing two scales.** Graded against the layer's *revealed* boundary (§5):

| Discovered pairs scoring at least as high as… | Count | of 305 |
|---|--:|--:|
| the weakest edge the layer accepted (0.6196) | 305 | 100.0% |
| its 5th percentile (0.9026) | 10 | 3.3% |
| its 25th percentile (0.9540) | **4** | 1.3% |
| its median (0.9767) | 0 | 0.0% |

The 305 have median 0.8168 against the accepted median of 0.9767. **They are a real but
marginal tail, not 305 obvious misses.** Only 4 clear the 25th percentile and are staged as
importable — 2 RV-SV and 2 RV-YV. The other 301 are staged as `STRONG_CANDIDATE` (6) or
`MARGINAL_CANDIDATE` (295) and are explicitly not importable.

The 4, all verified by eye:

| A | B | LCS | Difference |
|---|---|--:|---|
| `VG:RV:SAK:M03:S022:V005` | `VG:YV:VSM:A12:V051` | 0.9751 | one letter: RV `iḻā-`, VS `iḍā-` |
| `VG:RV:SAK:M03:S023:V005` | `VG:YV:VSM:A12:V051` | 0.9751 | as above |
| `VG:RV:SAK:M03:S022:V005` | `VG:SV:KAU:CHANDA:P01:D08:V04` | 0.9751 | SV prefixes a cue syllable `dra` |
| `VG:RV:SAK:M03:S023:V005` | `VG:SV:KAU:CHANDA:P01:D08:V04` | 0.9751 | as above |

---

## 11. Two encoding findings, one of them a retraction

### Real: the Vājasaneyi anusvāra cluster folds to two sentinels where everything else folds to one

| Spelling | Folds to | Length |
|---|---|--:|
| Latin `ṁ` (U+1E41) | `U+E003` | 1 |
| Latin `ṃ` (U+1E43) | `U+E003` | 1 |
| Devanagari anusvāra (U+0902) | `U+E003` | 1 |
| **Vājasaneyi cluster U+1CEA + U+0902 + U+1CED** | **`U+E003 U+E003`** | **2** |

**780 of 1,975 Yajurvedic verses carry U+1CEA or U+1CED**, so 39.5% of the Yajurveda is one
character out of alignment per anusvāra in every cross-script comparison. It depresses
similarity — RV-YV and AV-YV near parallels are being scored a little low — and it does not
invert an ordering. Those are the same 780 verses that corpus-audit §5 records a naive
codepoint scan misreading as accented; the signs are not accents, and they are not
harmless either.

Narrower, and **not** a defect: the GRETIL Rigveda's U+1E3B (`ḻ`, 671 occurrences in 638
verses) folds to `U+E002` while Devanagari `ड` folds to `ḍ`. They are different letters and
equating them is a position on the Rigvedic intervocalic alternation, not a normalisation —
so the fold is right to keep them apart. It costs 9 of the 305 discovered pairs some
similarity, and mapping `ḻ`→`ḍ` raises the score on 9 of 9.

### Retracted: the fold does not delete vocalic r

A probe of mine reported that the comparison fold deletes vocalic r, `kr̥dhi` → `kdhi` —
**the exact signature this campaign records as the AV `SEARCH_DERIVATIVE` corruption.** It
was wrong. Devanagari `ृ`, Latin `ṛ` and Latin `r̥` all fold to `U+E000` and **agree across
both scripts**, which is correct script-neutral behaviour, and `surfaces.py` carries
`contains_private_use()` for exactly it. The "deletion" was the console dropping an
unprintable private-use character.

Recorded because it is a trap the next agent will hit: **88% of every Veda's folded surface
contains a private-use character** (RV 88.12%, SV 87.96%, YV 89.47%, AV 87.74%), so any
probe that prints a folded surface will show the same false defect. Never display a folded
surface without `render_for_display()`.

---

## 11a. Semantic resemblance, and one disagreement with Agent 11

The mandate was to consume Agent 11's semantic resemblance if it landed and otherwise mark
the cell pending. At the time of this run it has not landed in a consumable form:

| Probe | Result |
|---|---|
| `SEMANTICALLY_RESEMBLES` / `RESEMBLES` / `SIMILAR_MEANING_TO` / `PARALLELS_IDEA_IN` across a Veda boundary | no such relationship type exists |
| `data/staging/semantic_resemblance/` | present, but holds `proofs/` only — no `manifest.json`, no `rows.jsonl` |

So all six cells are `NOT_APPLICABLE` with `PENDING_AGENT_11` as the reason, and nothing
was approximated from word overlap to fill them. That agent's own report is on disk and
independently confirms the containing facts — 0 vector indexes, and
`SHARES_ENTITY_VOCABULARY_WITH` at 2,141 edges of which every one crosses a Veda boundary,
which matches this report's row exactly.

**One disagreement the lead should reconcile.** Agent 11's report describes
`SHARES_FORMULA_WITH` as *"an empty declaration"* and *"a correction nobody had recorded:
the type vocabulary advertises a passage-to-passage formula predicate that has never had an
edge in it."* The count is right and the reading is not. The rationale **is** recorded, as
data rather than prose, at `src/vedagraph/enrich/predicates.py::UNPOPULATED_BY_DESIGN`, and
§7 above gives it. Two agents in one wave independently found the same zero and neither
found the reason by looking at the database — which is precisely what that map's docstring
predicts will keep happening until the ontology reference reads it.

---

## 12. The artifact

`data/staging/cross_veda/`. The row unit is the **mantra**, not the pair, because that is
what the campaign is missing: corpus-audit §4 records that for every inherently optional
dimension the graph cannot distinguish "assessed and came back empty" from "never assessed",
and that the assessed population cannot be recovered after the fact. All 20,210 canonical
mantras appear here, so the parallel dimension now has the assessed-set record it has never
had.

| | Count |
|---|--:|
| `candidates_considered` | 20,210 |
| `accepted` (rows.jsonl) | 7,021 |
| `rejected` — assessed, no connection established | 13,074 |
| `unresolved` — below `MIN_COMPARABLE_LENGTH` | 115 |
| `verified_zero` | **0** |
| `not_applicable` (matrix cells) | 12 |

Accepted per Veda: RV 3,054, SV 1,687, AV 1,530, YV 750.

**`verified_zero` is 0 deliberately.** No exhaustive all-pairs scan of the 127,852,257-pair cross-Veda product was run, so a mantra with no connection is recorded as *assessed under
three named channels* — the MinHash generator, the Formula hub and the entity-vocabulary
layer — and not as a verified zero. Promoting it would be turning `NOT ASSESSED` into
`VERIFIED ZERO`, which the contract forbids. The matrix contains no `VERIFIED_ZERO` cell
either, because all 31 measured cells are positive.

Every row carries `source_snapshot`, `algorithm_version`, `config_hash`, `code_commit`,
`population`, `processed_count`, `positive_count` and an `evaluation` block. `proofs/` holds
the matrix, the permutation null, the calibration, the adversarial cases, the recall probe
and its diagnosis, the revealed-boundary measurement and all 6,596 transformation records.

```
$ .venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/cross_veda --graph
  cross_veda (agent 10): 7021 row(s), 4 source(s)
  ... 15 checks, all [OK], every one at full coverage ...
  PASS. Every check evaluated every eligible row and found no defect.
```

### Every figure in this report was recomputed, and three were wrong

Every table above is read out of an artifact, so the figures that needed checking were the
ones a writer added up or a writer typed. Every one is recomputed against the
measurements and diffed, and the result — the count, each claim, each recomputation — is
in `proofs/figure_check.json`. It caught three things, all of them mine:

1. **Two hand-added column totals.** All 14 transformation rows and all 84 of their pair
   cells were correct; the grand-total row was not — 15 had been transposed between the
   RV-SV and SV-YV columns. The check now parses that row out of the report instead of
   restating it, because restating it is how a wrong table passes its own check.
2. **An invented population figure.** The cross-Veda pair product was written as
   127,795,000 in the manifest and "127.8 million" in the report. It is 127,852,257. The
   rounded form is also what `crossveda.py`'s own docstring carries.
3. **A stale background job overwrote a verified result.** An earlier, slower version of
   the adversarial suite was left running, finished after the corrected 11-case run, and
   silently replaced its output with its own 9 cases — so the manifest briefly reported 9
   cases and 4 rejections against a report describing 11 and 3. Nothing failed; a file
   changed under a finished measurement. The suite's case ids and verdicts are now diffed
   between the report and the artifact in both directions.

---

## 13. What this did not do

- **Nobody read a single pair.** 0 of 6,596 transformation types and 0 of 305 discovered
  pairs were checked by a person. Section 22 is not satisfied, and the four discovered
  pairs graded importable rest on my eye alone.
- **No canonical write occurred.** Neo4j was read-only.
- **No exhaustive all-pairs scan.** The recall probe is exhaustive over two channels
  totalling 23,443 pairs, not over 127,852,257. A third channel would find more, and the
  305 is a floor on the recall gap, not its size.
- **Semantic resemblance is untouched.** All six cells are `PENDING_AGENT_11`. Nothing was
  approximated from word overlap to fill them.
- **`GAP-CROSS_VEDA-004` is still open** and still not countable. A pada-level detector was
  not run because no pada segmentation exists anywhere in the graph to run it on
  (CORPUS_D05), so its dependency is structural rather than a matter of threshold.
- **Direction for RV-YV was not asserted**, though its contiguity asymmetry is the widest
  of the six. What is missing is a witness, and this agent did not go looking for one
  outside the repository.

## 14. For the lead, in the order they matter

1. **Fix the query, not the data, for CORPUS_D07.** Any surface reporting parallel coverage
   must use `-[r]-`. A directed query reports a false zero for all 1,975 Yajurvedic mantras
   and for Rigvedic reuse. This is the one item that changes what a reader sees today.
2. **Withdraw `GAP-FORMULA-001` and reframe `GAP-CROSS_VEDA-003`.** Both prescribe work
   that should not be done: one would materialise 87,296 edges against a recorded design
   decision, the other would attach `parallel_id` to an intra-Rigvedic layer that never had
   one. Wave 1 already found three registry entries prescribing the wrong remedy; these are
   two more.
3. **Split or expose `EXACT_PARALLEL_OF`.** Four edges answer an "exact" filter at 0.617
   text similarity because they matched on lemmas. Smallest honest fix: surface
   `strongest_method` wherever the type is filtered on.
4. **Record direction on its own evidence axis.** The 1,684 `REUSES_TEXT_FROM` edges claim
   `evidence_basis: SANSKRIT` for a direction the Sanskrit does not establish. Add the axis
   before any second pair is ever given a direction.
5. **Collapse the Vājasaneyi anusvāra cluster to one sentinel** and re-run the near-parallel
   stage. 780 of 1,975 Yajurvedic verses are mis-aligned by one character per anusvāra, and
   RV-YV and AV-YV are the two pairs whose scores this depresses.
6. **Stop quoting the Samaveda's 90.9% as evidence of anything about reuse.** It is 5.72×
   corpus-size arithmetic with an excess of 1.17×. It is a true figure that supports a false
   inference, which is the class of defect this campaign exists to catch.
7. **Decide on the 301 marginal discovered pairs.** They are real signal below the layer's
   operating point. Importing them would loosen a boundary that is currently tight;
   discarding them loses a measured recall extension. Either is defensible; leaving them
   unlabelled is not.
