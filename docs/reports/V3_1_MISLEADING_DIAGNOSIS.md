# VedaGraph V3.1 — The Measured `MISLEADING` Diagnosis

**This document exists because the V3 close-out report's `25 MISLEADING` figure has no
per-question list behind it.** The close-out states that "twelve questions were probed directly
with Cypher; the remainder are classified by category and marked ESTIMATED in the evaluator's
working," and that working document was never committed. This pass replaces the estimate with a
per-question re-grade taken from rows read against the live database.

| Field | Value |
| --- | --- |
| Author role | Agent B — benchmark correctness diagnosis, read-only on database and source |
| Graph diagnosed | `d456cce` (branch `semantic-pilot-v1`), **108,689 nodes / 261,584 relationships** (verified live; matches the V3 close-out exactly) |
| Database | `bolt://localhost:7687`, Neo4j 5.26 |
| Benchmark | `VEDAGRAPH_100_QUESTION_BENCHMARK_V3.md`, frozen — wording and criteria applied verbatim |
| Prior evaluation re-graded | `VEDAGRAPH_100_QUESTION_BASELINE_V3.md` (commit `bb27f3c`): 5 / 29 / 15 / 51 |
| Verdicts `PROBED` | **97 of 100** |
| Verdicts `INHERITED` | **3** — Q8, Q16, Q98 (listed in §D with the reason) |
| Writes performed | **none.** No `CREATE`/`MERGE`/`SET`/`DELETE`/`REMOVE` was executed and no source file was edited. |

Five other agents were mutating disjoint predicate partitions of this graph while this diagnosis
ran. Every verdict here is therefore a diagnosis of the **starting** graph, per the write-partition
contract in `V3_1_ROI_PLAN.md` §4. The end-of-session benchmark run measures the delta; this
document is the baseline that run is measured against.

---

## A. Measured verdict counts, and the contradiction with the V3 close-out

| Verdict | Baseline `bb27f3c` | V3 close-out **claim** | **Measured now** | Delta vs claim |
| --- | --- | --- | --- | --- |
| `FULLY_ANSWERABLE` | 5 | 7 | **5** | −2 |
| `PARTIALLY_ANSWERABLE` | 29 | 44 | **52** | **+8** |
| `NOT_ANSWERABLE` | 15 | 24 | **8** | **−16** |
| `MISLEADING` | 51 | 25 | **35** | **+10** |

### The V3 close-out's `7 / 44 / 24 / 25` is contradicted on all four cells.

The largest single error is not the `MISLEADING` count — it is the `NOT_ANSWERABLE` count. The
close-out reports 24 questions as unanswerable; **8** are. V3 built layers that turned seven
baseline zeros into real answers (Q27, Q57, Q63, Q69, Q97 to `PARTIALLY_ANSWERABLE`; Q85 and Q86
to `MISLEADING`), and the close-out's category-level estimate did not see them. The `NOT` and
`PARTIAL` errors are of opposite sign and roughly cancel, which is exactly what an estimate that
never read rows would do.

**`MISLEADING` is 35, not 25 — 40% higher than reported.** The direction matters: the
close-out's own §84 calls "25 questions still return misleading answers" the chief product risk,
so the risk register understates the work by ten questions. Two of the ten are *new* failures
created by V3 itself (§E), which is the class of defect an estimate cannot detect by construction:
a question that was a clean `NOT_ANSWERABLE` at baseline cannot be re-estimated upward by
category, because the category improved.

### What the V3 close-out gets right, verified

Being sceptical of both reports cuts both ways. These close-out claims were probed and hold:

- **The sealed Rigvedic artifact is projected.** 4,865 `SemanticAssertion` nodes,
  `seal_status = VALIDATED`, `run_id` present, 2,406 carrying an `ASSERTION_PREDICATE` edge. The
  baseline's blocker **B21 is closed**, and the close-out is right that the independent evaluator's
  "never projected" claim was wrong. *(This is the second time in this project's history that an
  asserted absence was disproved by one query; see the memory note on verifying an evaluator's
  absences.)*
- **`evidence_basis` is now correct across the graph.** `UNSPECIFIED` is gone — zero edges. The
  census is `SANSKRIT 106,179 · STRUCTURAL 87,515 · SOURCE_METADATA 50,842 · MIXED 13,694 ·
  TRANSLATION 3,354`. Parallel edges are `SANSKRIT`, Anukramaṇī edges are `SOURCE_METADATA`, and
  the L3 slice carries `TRANSLATION`/`MIXED` rather than lying about its Whitney quotations. The
  baseline's blocker **B15 is closed** and it moved Q73 and Q74 off `MISLEADING` exactly as the
  baseline predicted it would — the one place where a named cheap fix converted into two verdicts.
- **The four-Veda theonym layer works and is the largest single source of movement.** 17,165
  `MENTIONS_DEVATA` edges; **35 of 42 deities are named in all four Vedas**. Indra: RV 2,305 /
  AV 635 / SV 405 / YV 221, every edge `DEITY_CERTAIN`. Blocker **B2 is closed** and blocker **B1
  is materially mitigated**.
- **`Work.scope` is still null on all four `Work` nodes** (close-out blocker 5), and
  **`RishiFamily` is still 0 nodes** (blocker 4). Both confirmed.

### Three close-out statements that are wrong on the measurement

1. **§75, "48 named queries."** `len(QUERIES)` is **86**. (Already recorded in
   `V3_1_ROI_PLAN.md` §0.2.)
2. **§84 blocker 7, "`FormulaFamily` membership is not traversable outward
   (`FORMULA_MEMBER_OF` = 0)."** Overstated. `MEMBER_OF_FAMILY` has **2,037** `Formula` →
   `FormulaFamily` edges, and Cypher traverses a relationship in either direction:
   `(ff:FormulaFamily)<-[:MEMBER_OF_FAMILY]-(f:Formula)` works, and the shipped
   `formula_family_*` queries already use it. This is a naming inconvenience, not a blocked
   traversal, and it should not be sequenced as one. *(Agent E has since added an explicit
   `HAS_FORMULA` twin, 2,037 edges, during this session; see §H.)*
3. **§74's answer to Q75 is now less bleak than the baseline's.** The source-explicit subset
   contains `MENTIONS_DEVATA 5,900` — a semantic assertion in the top tier, where baseline had
   none. `TIER_A` passage→`DomainEntity` is still 0, but the "everything semantic disappears"
   framing no longer holds.

### One hazard the close-out reports as a strength

§27 celebrates concept-layer agreement rising "from 55.3% to 94.4%". Measured:
`ABOUT_CONCEPT`/`SANSKRIT` 13,356 edges of which 11,903 are duplicated by `MENTIONS_ENTITY`
(89.1%), and `MIXED` 13,081 of which 13,044 (99.7%). Rising agreement between two layers built by
the same matcher over the same tokens is **increasing nesting, not increasing corroboration**.
Q76's frozen criterion demands mode *independence*, and the honest answer the graph supports is
still "these are one layer twice." Q76 remains `FULLY_ANSWERABLE` because the census itself is
complete and honest, but any report that quotes 24,947 as "corroborated" is repeating the defect
Q76 exists to expose.

---

## B. The per-question `MISLEADING` table — 35 questions, all `PROBED`

`Q#` · `current wrong behaviour (rows read)` · `root cause` · `class` · `layer / query` ·
`fix at root-cause level` · `owner` · `cost`

### B1. `AMBIGUOUS_THEONYM` — 6 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **26** | `rivers_mentioned` returns `sindhu` 236 of 247 total river mentions (**95.5% of the table's mass**) against `paruṣṇī 3, sarayu 2, vipāś 2, yamunā 2, sarasvatī 2, gaṅgā 1, śutudrī 1`. Sarasvatī **is** now `:River` (`VG:CONCEPT:SARASVATI-RIVER`) — with **2 mentions**, while `VG:DEVATA:SARASVATI` holds **213**. `rivers_and_tribes` returns **0 rows**. | The registry fix landed but the mention layer did not follow it: the theonym matcher consumes every `sarasvatī` token as a deity, so the river node is starved and the most-named river in the Rigveda still reads as absent. `sindhu`, the generic noun for "river", is untyped as generic, so a hydronym distribution is a common-noun count. A 0-row tribe join reads as "no river is associated with any clan" in a corpus containing RV 7.18. | `rivers_mentioned`, `rivers_and_tribes`; `MENTIONS_ENTITY`→`River`; `MENTIONS_DEVATA` | Route ambiguous `sarasvatī` tokens to **both** candidate senses with a per-occurrence certainty, rather than letting the deity matcher win by precedence; flag `sindhu` as `is_generic_noun` so it is excluded from hydronym tables by default. For `rivers_and_tribes`, an empty result must return `INSUFFICIENT_EVIDENCE` with the reason "no asserted river↔clan predicate exists", not 0 rows. | `AGENT_C_DEITY` (precedence) + `AGENT_D_RISHI_MATERIAL` (generic flag) | M |
| **45** | `MENTIONS_ENTITY.theonym_ambiguous` on `VG:CONCEPT:SOMA-DRINK` is **still the sandhi-inconsistent legacy field**: `somam` true (156) / `somaṃ` false (143); `somaḥ` true (115) / `somo` false (208). The replacement field is no better on its own terms: `referent_certainty` for `VG:DEVATA:SOMAH` splits by **extraction path, not context** — `rv-lemma-annotation` gives AMBIGUOUS 710 / CERTAIN 240, `sanskrit-surface-token` gives AMBIGUOUS 562 / **CERTAIN 0**. | Two rival sense fields, neither a sense decision. The old one partitions by orthography; the new one partitions by which matcher saw the token, so **no soma occurrence outside the Rigveda can be called certain-deity at all**. A researcher filtering either field believes they have separated deity from substance and has selected a pipeline branch. No accuracy figure exists per sense. | `theonym_ambiguous_mentions`, `soma_certainty_across_the_corpus`, `soma_deity_versus_substance`; `MENTIONS_ENTITY.theonym_ambiguous`; `MENTIONS_DEVATA.referent_certainty` | Retire `theonym_ambiguous` outright (it is a strictly worse duplicate). Make `referent_certainty` a function of verse context, not extraction path, with a third `DEITY_PROBABLE` bucket, and publish a per-deity accuracy figure in the row. Where context cannot decide, the row must say `SENSE_UNDECIDED` — a truthful refusal — rather than carry a filterable flag. | `AGENT_C_DEITY` | M |
| **46** | Agni is named in all four Vedas (RV 1,604 / AV 476 / YV 276 / SV 187), but `deity_certain` is **831 in the RV and 0 in AV, SV and YV**. Filtering to `DEITY_CERTAIN` — the safe default the certainty field invites — produces **three wrong zeros**. The three-way split the question asks for does not exist: the field is two-valued, there is no `ritual medium` sense, and `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED` is still live at `confidence: HIGH`. | Common-noun deities are marked AMBIGUOUS wholesale outside the RV because only the RV has lemma annotation. This reproduces the baseline's *absent-layer-as-absent-text* failure **inside the certainty field**, one layer deeper than where the baseline found it. | as Q45, plus `agni_deity_fire_medium`; `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED` | Same certainty fix as Q45, plus a third `RITUAL_MEDIUM` sense value. The standing claim must be either retracted with evidence or amended to say it does not block a context-based decision — the frozen criterion names this explicitly and it is currently neither. | `AGENT_C_DEITY` | M |
| **85** | **Regression: baseline `NOT_ANSWERABLE`.** The class defect is fixed (Sarasvatī is `:River`) and the answer got worse. The obvious per-occurrence query now returns a complete-looking decision: `sindhu` false 224 / true 12, and **`false` on 100% of all six named hydronyms**; Sarasvatī-as-deity is AMBIGUOUS 195 / CERTAIN 18 while Sarasvatī-as-river has 2 mentions. A researcher reads "Sarasvatī is essentially always the goddess and essentially never the river." | Adding the node without routing the mentions converted a visible absence into a confident wrong answer. There is still no per-occurrence deity/geography decision and no accuracy figure; the two flags that look like one disagree with each other and neither was calibrated. | `MENTIONS_ENTITY.theonym_ambiguous` on `:River`; `MENTIONS_DEVATA.referent_certainty` on `VG:DEVATA:SARASVATI` | One per-occurrence sense field spanning the deity/geography axis for every hydronym, with a measured accuracy figure; until it exists, the query must return `INSUFFICIENT_EVIDENCE` rather than a 100%-`false` column. | `AGENT_C_DEITY` | M |
| **87** | Same probes as Q45. The strictest form of the sense question is answered by a field that partitions by matcher, and the RV cross-tab (deity-named 1,604 / fire-word) is a matcher disagreement. `human_gold_status` is `UNANNOTATED` on 2,459 assertions and `null` on 2,406; `review_state` is `UNREVIEWED` on every one. | No per-token sense label exists. The field that appears to be one is not internally consistent and has no accuracy figure against human annotation — the criterion's central demand. | as Q45 | as Q45; the accuracy figure is the binding clause and it requires annotation, so the honest interim state is an explicit `SENSE_UNDECIDED` on 100% of soma tokens. | `AGENT_C_DEITY`, then `HUMAN_BLOCKED` for the accuracy figure | M |
| **88** | Same probes as Q46, three-way rather than two-way. `referent_certainty` has exactly two values corpus-wide: `DEITY_AMBIGUOUS 8,825 / DEITY_CERTAIN 8,340`. | as Q46. | as Q46 | as Q46. | `AGENT_C_DEITY`, then `HUMAN_BLOCKED` | M |

**These six share one fix.** A three-way, context-driven `referent_certainty` with a per-deity
accuracy figure, plus retirement of the legacy `theonym_ambiguous` field, clears the binding
constraint on Q45, Q46, Q85, Q87, Q88 and half of Q26. It also removes a live hazard on Q43 and
Q70 (§F). This is the highest-return single fix in the table.

### B2. `INSUFFICIENT_DATA` — 11 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **13** | AV Kāṇḍa 14 contains **141** passages. `USED_FOR_RITE`→`vivāha` tags **14** of them. Recall on the gold-standard marriage book is **9.9%** — unchanged from baseline. The corpus-wide `vivāha` tag reaches 25 AV passages, of which one K14 passage is tagged `śālā` instead. | The rite layer has no measured recall and no book-level prior. 25 rows present themselves as the AV's marriage verse set; they are one verse in ten of the one book that is entirely about marriage. | `passages_used_for_a_rite`, `social_rites`; `USED_FOR_RITE`→`SocialRite` | Seed rite assignment from the AV's own kāṇḍa structure (K14 = marriage, K18 = funerary) as a stated prior, then report measured recall against that book **in the returned row**. A rite query whose recall is under a stated floor must return the recall figure or refuse. | `AGENT_E_RITUAL_FORMULA` | M |
| **22** | `SHOW INDEXES`: 82 RANGE, 2 FULLTEXT, **0 VECTOR**. `conceptually_similar_not_reused` now returns **25 confident-looking cross-Veda pairs** (top: `AVS 9.10.14 / VSM 23.62`, 6 shared entities) computed by shared-entity overlap — the exact measure the criterion excludes. Baseline returned 0 rows here; the threshold was lowered to `shared >= 3`, so the failure changed shape from a wrong zero to a plausible wrong table. | No non-lexical similarity measure exists. Lowering the threshold made the output look like an answer. The caveat ("Treat as a candidate list, not a finding") is not sufficient — the reader who runs the obvious query never sees the caveat, which is the benchmark's stated reason `MISLEADING` is a distinct state. | `conceptually_similar_not_reused`; no vector index; `PARALLEL_TO` (69 edges, all same-Veda) | Either build an embedding/asserted-resemblance population, or rename the query to what it measures (`lexical_overlap_candidates`) and have it return an explicit `measure: LEXICAL_OVERLAP` column plus `INSUFFICIENT_EVIDENCE` for the conceptual-similarity question. Renaming is XS and clears the misleading state honestly. | `AGENT_A_QUERIES` (containment); real measure `DATA_BLOCKED` | S |
| **49** | Same query, same 25 rows. Mean `MENTIONS_ENTITY` degree is ~1.9 over 28,227 edges and 227 entities; at that degree shared-entity overlap cannot separate similarity from chance, and the criterion says so in terms. | as Q22. | as Q22 | as Q22 — one fix covers both. | `AGENT_A_QUERIES` | S |
| **56** | The YV richness ranking is `yajña 17 apparatus / 37 edges`, `savana 6/12`, `graha 3/7`, `dīkṣā 1/1`, `citi 1/1`. **`aśvamedha` does not appear at all** in the YV mention-derived table, and has 2 asserted apparatus edges corpus-wide — for the rite that occupies VSM 22–25. `vājapeya`, `rājasūya`, `darśapūrṇamāsa` and `cāturmāsya` are absent from the 8-node `Ritual` class. | The rite inventory doubled (4 → 8) but is still an order of magnitude below the corpus's named rites, and the richness ranking is topped by the generic word for "sacrifice". A reader concludes the aśvamedha is not among the richest Yajurvedic ritual networks, which inverts the answer. | `ritual_profile`, `rituals_described_in_passages`; `Ritual` (8 nodes); `USES_OBJECT`/`USES_OFFERING`/`USES_SUBSTANCE` (38 edges) | Expand `Ritual` to the corpus's actually named rites and attach apparatus per rite with per-verse or named-manual evidence. Until the inventory is at corpus scale the richness measure must carry an explicit `inventory_coverage` column so a low rank cannot be read as a low apparatus. | `AGENT_E_RITUAL_FORMULA` | M |
| **58** | No `Passage` or `Formula` property matching `func*` exists (checked). The per-Veda entity profile of a reused formula is identical by construction, so the query answers "semantic function never changes under reuse" — a tautology of the measure. | Function is inferred from the tokens, and the tokens are what was reused. There is no function or role assignment independent of wording anywhere in the graph. | `formula_family_*`; `USES_FORMULA`; `MENTIONS_ENTITY` | Add a token-independent function assignment (ritual application, addressee, speech act) per occurrence. Absent that, the question must return `INSUFFICIENT_EVIDENCE` — "no function assignment independent of the token inventory exists" — because "never" is a wrong answer and a caveat does not stop a reader believing it. | `AGENT_E_RITUAL_FORMULA` | L |
| **60** | `vivāha` **788** cross-Veda pairs, `sūṣā` 94, `sabhā` 46, `pitṛyāṇa` 18. The 788 is the cross-product of 25 AV × 16 RV marriage-tagged passages in both directions, on a probe with 9.9% recall (Q13). Improving recall makes the number grow quadratically. | The pair count scales with the square of a bad probe, so there is no reading under which it is evidence. Nothing in the row discloses the cross-product. | `USED_FOR_RITE` self-join | Report distinct passages per side and the rite-layer recall, not the raw pair count; correct for the cross-product explicitly, as the criterion demands. Fixing Q13's recall is the prerequisite. | `AGENT_E_RITUAL_FORMULA` | S |
| **71** | `hiraṇya` RV 38 / AV 34 / YV 6 / SV 6; `ayas` RV 8 / AV 3 — **11 total mentions, still the sole basis for any metallurgy statement**; `vrīhi` AV 3 only. There is no recall figure, no significance statement and no falsifier attached to any of these counts. Horse and chariot rates continue to fall monotonically RV→SV→AV→YV, tracking annotation density. | Unmeasured alias-list recall on material-culture entities, which is where the recall requirement is strictest because the claims are historical. `ayas` at n=11 is either a finding about metallurgy or a six-alias artefact and nothing in the graph distinguishes the two. | `metals_by_veda`, `crops_by_veda`, `animals_by_veda`; `MENTIONS_ENTITY`→`Metal`/`Crop` | Measure recall per alias list per Veda against a concordance sample and return it in the row; attach a named falsifier to each material-culture claim. A count without a recall figure must not be returned for a historical question. | `AGENT_D_RISHI_MATERIAL` | M |
| **81** | Cross-Veda relatedness is **7,527 edges, 100% `L2_DETERMINISTIC_DERIVED` and 100% lexical**: `NEAR_PARALLEL_OF 3,049 · REUSES_TEXT_FROM 1,684 · EXACT_PARALLEL_OF 1,006 · VARIANT_OF 788` plus within-Veda `PARALLEL_TO 69`. The literal/semantic partition returns **100 / 0**. `PARALLEL_TO` was reclassified from `TIER_D`/`L4` to `L2`/`SANSKRIT` and is entirely same-Veda, so it does not enter the partition at all. | Both categories must exist for the partition to mean anything. 100/0 reads as a finding about the corpus — that cross-Veda relatedness is purely textual — when it is a statement that no non-lexical resemblance measure was ever built. | `EXACT_PARALLEL_OF`/`NEAR_PARALLEL_OF`/`REUSES_TEXT_FROM`/`VARIANT_OF`/`PARALLEL_TO` | Build the non-lexical population, or return the partition labelled as a **method census** with an explicit `semantic_resemblance_population: NOT_BUILT` row rather than a `0`. A structural zero must be typed as one. | `AGENT_A_QUERIES` (typing); real measure `DATA_BLOCKED` | S |
| **84** | `Passage` carries **no** key matching `ritual*`, `litur*`, `context*`, `strat*`, `layer*` or `period*` — the key list is empty on all 22,537 passages. Ritual context can only be inferred from whether one of 8 `Ritual` entities is named in the same verse, which is almost never, so a crop/metal × context table reads **`ritual_ctx = false` on every row** in an almost entirely liturgical corpus. | Ritual context is not a property of the passage. The criterion requires it to be independent of same-verse rite mentions, and the graph offers only the disqualified inference. | `MENTIONS_ENTITY`→`Ritual` used as a context proxy; `Passage` | Add a passage-level ritual-context property sourced from liturgical position (the YV/SV liturgical index is the cheapest source, since those corpora are ordered liturgically). Until it exists the context column must be omitted, not filled with `false`. | `AGENT_E_RITUAL_FORMULA` | M |
| **92** | Deity-specificity over the four-Veda mention layer ranks `ulūkhala` (mortar) **2 deities / 5 passages** first, `dundubhi` 3/9 second — while `vajra` shows **19 deities / 204 passages** at rank 12 and `barhis` 28/139 last. There is no chance baseline for object↔deity: `CO_OCCURS_WITH` (306 edges, carrying `lift`) exists for `Devata`↔`Devata` **only**. | Without an expected value, "1 deity at n=5" and "1 deity at n=200" rank identically, so the ranking is a rarity ranking wearing a specificity label. The corpus's most deity-specific object ranks near the bottom. | `MENTIONS_DEVATA` × `MENTIONS_ENTITY`→`Object`; `CO_OCCURS_WITH` | Extend the existing `lift`/`baseline_mantras` machinery already built for `Devata`↔`Devata` to `Devata`↔`Object`, and rank on lift with an n floor. The machinery exists; it is a second application of it. | `AGENT_C_DEITY` | S |
| **100** | The compound four-dimension join returns **3 rows over 2 passages** (RV 2, YV 1) and **zero rows for AV and SV**. Substituting `Substance` for the 2-node `Offering` class and `PROTECTS_FROM` for `ADDRESSES_CONCERN` gives 88 rows across all four Vedas — so the collapse is the ontology, not the corpus. The row set carries nothing that explains this. | Four thin dimensions multiplied: `Offering` = **2 nodes**, `HumanConcern` = **7 nodes**, `ADDRESSES_CONCERN` = 326 edges. The criterion demands "order hundreds of rows" and that the row count's relationship to each dimension's coverage be stated so a small result cannot be misread as a small phenomenon. Neither holds. | `MENTIONS_DEVATA` × `Offering` × `ADDRESSES_CONCERN` | Expand `Offering` beyond `havis`/`dakṣiṇā` (the `INVOLVES_OFFERING` predicate already reaches `ghṛta`, `anna`, `paśu`, `aśva`, `go`, `soma` — those targets are typed `Substance`, not `Offering`, which is the whole defect) and expand `HumanConcern`. Any degenerate join must emit a per-dimension coverage row alongside the result. | `AGENT_E_RITUAL_FORMULA` | M |

### B3. `ONTOLOGY_COLLISION` — 5 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **15** | `Condition` grew 12 → **36 nodes** and **`takman` is now its own entity** (`VG:CONCEPT:TAKMAN-FEVER`, 33 AV mentions, 33 `TREATS`) — the baseline's decisive defect is fixed. The inventory is still wrong at the top: `rakṣas` (demon) **160**, `yakṣma` 89, `kṛtyā` (witchcraft) 65, `viṣa` (poison) 63, then `takman` 33. Eight members of the class are causes or agents, not afflictions: `rakṣas`, `kṛtyā`, `abhicāra`, `abhiśasti`, `śapatha`, `durṇāman`, `arāya`, `durhārd`. | The frozen criterion requires that "causes (sorcery, ill-named beings) are typed separately from afflictions." They share one label, so a named-disease inventory is topped by a demon. Class membership is wrong, which is the third canonical `MISLEADING` shape. | `conditions_treated`, `condition_neighbourhood`; `Condition` label | Split `Condition` into affliction and affliction-cause — either two labels or one `condition_kind` property — and default disease queries to afflictions. This is a registry edit over 36 nodes. | `AGENT_D_RISHI_MATERIAL` | XS |
| **25** | `ritual_objects_recurring` is still led by `ratha` (chariot) **473** and `vajra` (thunderbolt) **275**, then `barhis` 195, `grāvan` 164. `vedi` **17**, `sruc` **11**, `yūpa` **6**, `ulūkhala` **6** across 22,537 passages including the whole Yajurveda. `Object` has 23 members and there is no `RitualImplement` class; `Weapon` (5) is a sub-label of `Object`, so weapons are not excluded from the implement table. | The class conflates vehicle, weapon, ornament and implement. The two commonest rows of a "ritual objects" table are a vehicle and a weapon, and the Yajurvedic apparatus is an order of magnitude below the text. | `ritual_objects_recurring`; `Object` label | Add a `RitualImplement` sub-label (or `object_kind` on the 23 nodes) and default the ritual-object query to it, excluding `Weapon` and vehicles. Separately, the yūpa/vedi alias lists need recall work — but the typing alone stops the table inverting. | `AGENT_D_RISHI_MATERIAL` | S |
| **38** | `deity_widest_range` is **still topped by `Agni, Mitra-Varuna, Ratri and Savitr` — 4 axes, `attributed: 0`** — a compound Anukramaṇī label attested nowhere, inheriting the union of its constituents' axes. Then Indra (3, 2,869), Agni (3, 1,988), Varuna (3, 99), Pusan (3, 77), Brhaspati (3, 74), `Indra and Varuna` (3, 70), `Agni and the Maruts` (3, **0**). Measured: **22 of 38 PAIR deities and 30 of 33 GROUP deities have no decomposition or membership edge at all.** | Range is a per-node constant (`HAS_AXIS`, 289 edges, all `TIER_D`) so it cannot vary with the corpus, and compound labels are not excluded or resolved. The criterion requires both. The `attributed: 0` column is an honest addition but the row is still rank 1. | `deity_widest_range`, `deities_by_axis`; `HAS_AXIS`; `Devata.structure` | Complete `COMPOSED_OF`/`MEMBER_OF` for the 52 undecomposed PAIR/GROUP deities and exclude composites from range leaderboards by `structure`, or resolve them to constituents. Then derive range from per-occurrence evidence rather than the node constant. | `AGENT_C_DEITY` | S (exclusion) / L (per-occurrence range) |
| **86** | **Regression: baseline `NOT_ANSWERABLE`.** `DEVATA_ASSOCIATED_WITH` is now populated (160 edges) so the query returns rows — and the rows are wrong. "fire (agni)" is reported with **5 personifications**: `Agni`, `Agni Jatavedas`, `Agni Pavamana`, `Agni the slayer of demons`, `the self of Agni`. "weapon (āyudha)" gets `the bow`, `the arrows`, `the quiver`; "bowstring (jyā)" gets `the bow`, `the bowstring`, `the two bow-tips`; "horse (aśva)" gets `the horse`, `the horses`, `the steeds`. | Epithet-qualified and number-variant `Devata` nodes are counted as distinct personifications because they are not linked to a base deity. The criterion names this failure exactly — that "Heaven and Earth", "Heaven, Earth and the Aśvins" and "Earth and the midspace" must not be three personifications of earth. The multi-personification count is inflated by unresolved duplicates, so the class membership of the answer is wrong. | `DEVATA_ASSOCIATED_WITH`; `Devata` epithet-qualified nodes; `Devata.structure` | Link epithet-qualified and number-variant `Devata` nodes to their base deity (a `VARIANT_OF_DEITY`/`EPITHET_OF` edge), then count personifications per base deity. Same fix as Q38's decomposition, applied to the epithet axis. | `AGENT_C_DEITY` | M |
| **90** | `RitualRole` grew 5 → **10** and **`udgātṛ` was added** — with **1 mention** (RV). **`hotṛ` is still `["Concept","DomainEntity"]` with no `RitualRole` label, and has 321 mentions (RV 208, YV 50, SV 41, AV 22)** — five times the next priest. `ritual_roles` therefore returns `yajamāna 40`, `brahman 29`, `adhvaryu 21`, `potṛ 13`, ... and never the hotṛ. `PERFORMED_BY` (16 edges) omits it too. | The baseline named five registry edits as the cheapest high-reach fix. Four were made (takman, Sarasvatī-as-River, vajra-as-Weapon, āyudha-as-Weapon, udgātṛ); **the fifth — typing `hotṛ` — was missed, and it is the one with 321 mentions.** A Vedic priestly-role table that omits the officiant of the Rigveda is not incomplete, it inverts the answer: a reader concludes the adhvaryu or the yajamāna is the central Vedic officiant. | `ritual_roles`, `ritual_officiants_and_purposes`; `VG:CONCEPT:HOTR-PRIEST`; `RitualRole` label | Add the `RitualRole` label to `VG:CONCEPT:HOTR-PRIEST`. **One label on one node.** Then attach `PERFORMED_BY` from the rites the hotṛ officiates. | `AGENT_E_RITUAL_FORMULA` | **XS** |

### B4. `QUERY_SEMANTICS` — 4 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **5** | `agni_and_indra_together` returns **one row** — `dual entity indragni, 117 mantras`. Its second route ("both singly attributed") returns nothing, **and the shipped caveat states: "The second route returns zero, and that is the finding rather than a gap."** Measured against `MENTIONS_DEVATA`, Agni and Indra are named in the same verse in **157 passages across all four Vedas** (RV 89, AV 31, YV 30, SV 7). | The query and its caveat were written against `HAS_DEVATA` (Rigveda-only, one addressee per mantra by construction) and were not revised when the four-Veda mention layer landed. The caveat now asserts as a finding about the corpus something the same database disproves in one query. This is the most direct instance in the catalogue of a shipped statement contradicted by the shipped data. | `agni_and_indra_together`, and its `caveat` string | Add a `MENTIONS_DEVATA` co-mention route to the query and rewrite the caveat to say what is actually true: the Anukramaṇī names one addressee per mantra, *and* 157 verses name both deities. The zero must be typed as a property of the attribution source, not of the text. | `AGENT_A_QUERIES` | XS |
| **37** | There is **no stored centrality anywhere** (no node carries a `central*`/`betweenness*`/`pagerank*`/`louvain*`/`community*` key), **Q37 has no named query at all** (`questions_served()` skips 37), and the natural GDS projection over `Passage`/`DomainEntity` with `MENTIONS_ENTITY` is directed and bipartite, so it still returns **betweenness 0.0 for every node** — a full, sortable ranking of zeros. | The default projection a competent user writes produces a ranking that is entirely an artefact of orientation, and nothing in the graph or the catalogue steers them away from it. The rival-concept-layer problem is separately unresolved: `MENTIONS_ENTITY` (28,227 edges / 227 entities) and `ABOUT_CONCEPT` (26,437 / 91) still carry **no authority marker** (checked: no `auth*`/`canon*`/`primary*` key on either). | GDS projection; `MENTIONS_ENTITY` vs `ABOUT_CONCEPT`; no named query | Compute centrality once on one layer declared authoritative, store it on the node, and ship a named query that reads the stored value. A stored score cannot be silently mis-projected. Mark one concept layer authoritative with a property, so "which layer" stops being a coin flip. | `AGENT_A_QUERIES` | S |
| **43** | `rudra_profile_no_shiva` — the named query for this question — returns **`vedas: ["RV"]`, `attributed_mantras: 38`, `source_stated: 8`**, because it reads `HAS_DEVATA`. The same database has Rudra named in all four Vedas via `MENTIONS_DEVATA`: RV 128, AV 42, YV 41, SV 5, and normalised **YV 20.76/1k against RV 12.13/1k** — Rudra is *denser* in the Yajurveda, which is the Śatarudriya effect the baseline said was invisible. The data exists; the query does not read it. | Stale query semantics. Worse, the safe fallback is also broken: **every non-RV Rudra edge is `DEITY_AMBIGUOUS`** (RV alone has 33 certain), so a researcher who filters on certainty gets the RV-only answer back. Both the default and the cautious path return the wrong Veda profile. | `rudra_profile_no_shiva`, `deity_profile`, `deity_actions_performed`, `deity_asserted_versus_requested`; `HAS_DEVATA` vs `MENTIONS_DEVATA` | Add a four-Veda `MENTIONS_DEVATA` per-Veda block with corpus-size normalisation to every deity-profile query, and type the `HAS_DEVATA` zero as `layer absent (RV-only Anukramaṇī)` in the row itself. Depends on the Q45/Q46 certainty fix to make the cautious path safe too. | `AGENT_A_QUERIES` (query) + `AGENT_C_DEITY` (certainty) | XS (query) |
| **96** | As Q37: no stored centrality, all-zero default directed projection, no authoritative concept layer. One thing improved and it should be recorded: the two rival layers now **agree** on the top entities (`MENTIONS_ENTITY`: dyaus 1,206 / soma 1,169 / agni 1,028 / rayi 885 / yajña 839; `ABOUT_CONCEPT`: agni 1,971 / soma 1,509 / dyaus 1,182 / rayi 873 / yajña 833 — same membership, `stoma` no longer intrudes), and the deity layer is no longer one-Veda. What remains missing is the criterion's core clause: a **rank-correlation figure** between the layers. | The robustness clause is the question. Without a stored ranking on a declared layer and a reported rank correlation, a centrality answer is a statement about annotation history. | as Q37 | as Q37, plus compute and store the rank correlation between the two concept layers as a `DerivedMetric`. The layers now agree enough that this is likely to be a *good* number — which is an argument for measuring it. | `AGENT_A_QUERIES` | M |

### B5. `ATTRIBUTION_CONFUSION` — 4 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **2** | `rishis_invoking_deity` (Agni) returns `gāthino viśvāmitraḥ 179 / source_stated 7`, `bārhaspatyo bharadvājaḥ 173 / 0`, `gautamo vāmadevaḥ 171 / 0`, `maitrāvaruṇirvasiṣṭhaḥ 140 / 0` — **the strict column is 0 for seven of the top eight**. The strict query's own leader is **`devāḥ` (14) — "the gods", not a seer** — followed by `agnivaruṇasomāḥ` and `brahma`. `RishiFamily` = **0 nodes**; `Rishi` has no `patronymic`, `personal_name` or `gotra` property and `occurrence_count` = 0 on all 729. The deity join reads `HAS_DEVATA`, so the **5,084 AV and 2,240 YV `HAS_RISHI` edges are invisible** to it. | Three compounding defects: the default ranking is container-inherited (`HAS_RISHI` is 15,177 inherited / 2,712 per-passage), the strict alternative's top rows are non-personal labels typed as seers, and the family level the criterion requires does not exist. Co-presenting `mantras` and `source_stated` in one row is a real improvement and is why this is a near-miss rather than a gross failure — but the top-ranked member is still wrong under the precision the question demands. | `rishis_invoking_deity`, `rishis_invoking_deity_strict`; `HAS_RISHI`; `RishiFamily` | Populate `RishiFamily` from the Anukramaṇī patronymic (per `V3_1_ROI_PLAN.md` §0.4 the vṛddhi derivation is a grammatical marker, not a string resemblance), add `is_personal_name: false` to `devāḥ`, `indraḥ`, `brahma`, `agnivaruṇasomāḥ` and their kind, and route the deity side through `MENTIONS_DEVATA` so AV and YV seers can appear. | `AGENT_D_RISHI_MATERIAL` | M |
| **3** | `varuna_profile` returns `top_concepts` = `kingship, dyaus, vrata, pṛthivī, āpaḥ, sakhya, āyus, jana, sindhu, sūrya` — **byte-for-byte the baseline's naive ranking**, now frozen onto the `Devata` node as a stored property with no strict alternative and no recall figure. `pāśa` (the noose), Varuṇa's defining instrument and rank 2 under verse-specific filtering, is absent from the list. `attributed 99 / per_passage 17 / inherited 82`, `attribution_scope: ["RV"]`. | Materialising the inherited-inclusive ranking as a node property removed the reader's ability to recompute it strictly. Ranks 2–8 change completely under `attribution_precision = 'PER_PASSAGE'` and the profile offers only the inherited view. | `varuna_profile`, `deity_profile`; `Devata.profile_top_concepts`; `HAS_DEVATA.attribution_precision` | Store **both** rankings (`profile_top_concepts` and `profile_top_concepts_strict`) or store neither and compute at query time. A single stored ranking whose precision basis is not in the property name is a trap. | `AGENT_C_DEITY` | S |
| **19** | Same query pair as Q2, for Indra. The naive/strict divergence the criterion names is now **surfaced in one row**, which satisfies the criterion's explicit test — but the default ordering is still the inherited one, which the criterion forbids in terms ("the inherited-inclusive leaderboard must not be the default answer"), and the strict ranking's top rows are non-seers. | as Q2. | as Q2 | Order by the strict column by default and show the inherited figure alongside; type the non-personal labels. This is the cheapest of the four in this group. | `AGENT_D_RISHI_MATERIAL` | S |
| **62** | The strict deity-range leaderboard is computed on **2,712 of 17,889 seer edges (15.2% — up from the baseline's 4.5%, because the YV apparatus is 100% per-passage)** and its joint leaders still include `agnivaruṇasomāḥ` (three gods) and `indraḥ` (a god). `RishiFamily` = 0 so no roll-up is possible; `Rishi.occurrence_count` = 0 on all 729. | The criterion requires strict and naive reported together **with** the strict coverage stated as a fraction, non-personal labels typed, and a family roll-up. None of the three is available; the coverage fraction is not returned by any query. | `HAS_RISHI`; `RishiFamily`; `Rishi.occurrence_count` | as Q2, plus return the strict coverage fraction in the row. Note the coverage tripled on its own when the YV apparatus landed — the fraction is now worth stating rather than hiding. | `AGENT_D_RISHI_MATERIAL` | M |

### B6. `SCOPE_CONFUSION` — 3 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **28** | `competing_interpretations` returns **one pair**: `VG:CLAIM:SV-IDENTITY-IS-MELODIC` (RESEARCH_HYPOTHESIS, LOW) against `VG:CLAIM:SV-PREDOMINANTLY-RV-REUSE` (MODEL_SYNTHESIS, MEDIUM). All **6** `InterpretiveClaim` nodes are about this dataset's construction; there is still no `CONTRADICTED_BY` relationship type. | A `competing_interpretations` result reads as a record of scholarly disagreement about the Vedas. The content is a methodological argument about whether textual overlap understates Sāmavedic independence. The claims did gain populated `falsifier` fields (6 of 6), which is a genuine improvement and is why Q99 stays `PARTIAL` — but it does not change what the claims are *about*. | `competing_interpretations`, `claim_evidence_trace`; `InterpretiveClaim`; `CONTRADICTS` | Add an `about: DATASET \| VEDIC_TEXT` discriminator on `InterpretiveClaim` and have the query return `INSUFFICIENT_EVIDENCE` for the Vedic-text question while exposing the dataset claims under their own name. A truthful "the graph holds no scholarly disagreement about the Vedic text" clears the misleading state; twelve attributed scholarly positions would answer the question, and that is acquisition. | `DATA_BLOCKED` (real answer); `AGENT_A_QUERIES` (XS containment) | XS / L |
| **30** | `claim_evidence_trace` returns the full shape a civilizational-evidence record has — claim, statement, `SUPPORTED_BY` passages (`RV 10.187.3`, `SV ARANYA 1.7`), `SUPPORTED_BY_STATISTIC` → `DerivedMetric`, falsifier — for six claims titled `AGNI-LEXICALLY-UNDIFFERENTIATED`, `ANUKRAMANI-ATTRIBUTION-IS-SUKTA-SCOPED`, `CONCEPT-LAYER-LEANS-ON-TRANSLATION`, `RISHI-ATTRIBUTION-LEAST-VERSE-SPECIFIC`, `SV-IDENTITY-IS-MELODIC`, `SV-PREDOMINANTLY-RV-REUSE`. | as Q28. The shape is right and the content is a methodology note. Compounded by the absence of any stratigraphic dimension (`Passage` has no `layer`/`strat`/`period`/`date` key — confirmed). | as Q28 | as Q28. | `DATA_BLOCKED` | XS / L |
| **72** | Same single `CONTRADICTS` pair, with `SUPPORTED_BY_STATISTIC` on both sides pointing at the same `SV_REUSE_OF_RV` metric. No `CONTRADICTED_BY` type exists. The criterion asks for "at least a dozen claims about Vedic content". | as Q28. | as Q28 | as Q28. | `DATA_BLOCKED` | XS / L |

### B7. `INTERPRETATION_LEAK` — 2 questions

| Q | Current wrong behaviour (measured) | Root cause | Affected query / layer / predicate | Fix at root-cause level | Owner | Cost |
|---|---|---|---|---|---|---|
| **52** | The per-division axis distribution still computes cleanly and still varies across maṇḍalas — and axes are constants on the `Devata` node (`HAS_AXIS` 289 edges, all `TIER_D`), so **no deity's profile changes anywhere**; the variation is entirely the variation in which deity is attributed where. The action layer that *could* supply per-occurrence function is **RV-only** (all 4,865 `SemanticAssertion` nodes are RV; `layer_veda_scope` on the layer reads `["RV"]`), and outside the RV there are only 262 AV + 306 YV `TIER_C` action-ish edges and **nothing for the SV**. | A curated per-node constant, presented through a divisional aggregation, reads as measured profile change. The criterion says constant axis vectors fail by construction, and they do. | `deities_by_axis`; `HAS_AXIS`; `SemanticAssertion` (RV-only) | Assign function per occurrence, or aggregate the existing per-occurrence **action** frames by division instead of the node constants — the `PERFORMS_ACTION`/`IS_ASKED_TO` frames are a defensible proxy and already exist for the RV. Extend to AV/YV/SV before publishing a cross-divisional divergence statistic; until then the divisional axis table must not be returned. | `AGENT_C_DEITY` | L |
| **77** | `confidence >= 0.8` now selects **76,593** relationships (baseline: 57,993). **75,692 of 77,213 confidence-bearing edges — 98.0% — sit at exactly one of three constants**: `1.0` (`HAS_RISHI` 17,889, `HAS_CHANDAS` 16,331, `HAS_DEVATA` 10,558, `HAS_DEVATA_ASCRIPTION` 5,385), `0.85` (`ABOUT_CONCEPT` 12,610), `0.80` (`ABOUT_CONCEPT` 12,597). There is **no evaluation set in the graph** (probe for any node carrying a `gold`/`precision`/`recall` key returns only `SemanticAssertion`, whose `human_gold_status` is `UNANNOTATED` on 2,459 and `null` on 2,406, `review_state` `UNREVIEWED` on all). No reliability diagram exists. | The field is named `confidence`, is filterable, and now supports a larger "high-confidence" selection than at baseline. Nothing about it is calibrated. The baseline's 0.42 cluster was removed and replaced with a 1.0 cluster of 50,163 edges, so the constant-value problem **got worse, not better**. A researcher who filters on it believes they have raised precision and has selected a pipeline branch. | `confidence` on `HAS_RISHI`/`HAS_CHANDAS`/`HAS_DEVATA`/`HAS_DEVATA_ASCRIPTION`/`ABOUT_CONCEPT` | Rename the pipeline constant to what it is (`pipeline_prior`) and reserve `confidence` for a value validated against a labelled set with a reliability curve; add a constant-value guard so a single value cannot cover a majority of a predicate. The rename alone clears the misleading state honestly, because it stops supporting a filter that means nothing. The calibrated number itself needs human annotation. | `HUMAN_BLOCKED` (calibration); `AGENT_A_QUERIES` (rename + guard, XS) | XS / XL |

---

## C. Root-cause leaderboard

### C1. By assigned class (each question counted once, against its binding cause)

| Rank | Root cause class | Questions blocked | IDs | Single fix that clears the group | Owner |
| --- | --- | --- | --- | --- | --- |
| 1 | `INSUFFICIENT_DATA` | **11** | 13, 22, 49, 56, 58, 60, 71, 81, 84, 92, 100 | No single fix — see C2, where this class decomposes into four separable clusters | mixed |
| 2 | `AMBIGUOUS_THEONYM` | **6** | 26, 45, 46, 85, 87, 88 | Three-way context-driven `referent_certainty` + retire legacy `theonym_ambiguous` + per-deity accuracy figure | `AGENT_C_DEITY` |
| 3 | `ONTOLOGY_COLLISION` | **5** | 15, 25, 38, 86, 90 | Registry typing: split affliction/cause, add `RitualImplement`, type `hotṛ`, link epithet-variant and compound `Devata` nodes to their base | `AGENT_D` + `AGENT_C` + `AGENT_E` |
| 4= | `QUERY_SEMANTICS` | **4** | 5, 37, 43, 96 | Re-point deity-joined queries at `MENTIONS_DEVATA`; store centrality on one declared-authoritative layer; correct the stale caveats | `AGENT_A_QUERIES` |
| 4= | `ATTRIBUTION_CONFUSION` | **4** | 2, 3, 19, 62 | Populate `RishiFamily`; order by the strict column; type non-personal seer labels; store both strict and inherited concept profiles | `AGENT_D_RISHI_MATERIAL` |
| 6 | `SCOPE_CONFUSION` | **3** | 28, 30, 72 | `about: DATASET \| VEDIC_TEXT` discriminator on `InterpretiveClaim`, and refuse the Vedic-text question | `DATA_BLOCKED` |
| 7 | `INTERPRETATION_LEAK` | **2** | 52, 77 | Stop presenting curated per-node constants and pipeline constants as measured values (`HAS_AXIS`, `confidence`) | `AGENT_C` + `AGENT_A` |
| — | `MENTION_VS_ATTRIBUTION`, `TRANSLATION_DEPENDENCE`, `WRONG_DIRECTIONALITY`, `OTHER` | **0** | — | Not binding on any question. `TRANSLATION_DEPENDENCE` was binding on two at baseline (Q73, Q74) and is now closed. | — |

### C2. By shared single fix — the ranking to execute against

This is the more useful ordering, because two classes decompose and two overlap. Overlapping
questions are marked; a question is listed under every cluster whose fix it needs, with its
binding cluster in **bold**.

| # | One fix | Clears | Also unblocks / de-risks | Owner | Cost |
| --- | --- | --- | --- | --- | --- |
| **1** | **Three-way `referent_certainty` driven by verse context, legacy `theonym_ambiguous` retired, per-deity accuracy published in the row** | **45, 46, 85, 87, 88** (5) + half of **26** | Q43 (the cautious path currently re-zeroes Rudra outside the RV), Q70 (same hazard for Rudra and Viṣṇu), Q1/Q44 (0-certain columns for Agni, Soma, Vāc, Sūrya, Mitra, Āpaḥ, Pṛthivī) | `AGENT_C_DEITY` | M |
| **2** | **Registry typing pass — 4 edits over ~60 nodes**: `hotṛ` → `RitualRole`; `Condition` split affliction/cause; `Object` → add `RitualImplement`; epithet-variant + compound `Devata` → link to base | **15, 25, 86, 90** (4) + **38** | Q47, Q94 (affliction/cause separation), Q23/Q33/Q63 (compound-pair typing), Q92 | `AGENT_D` (15, 25) · `AGENT_E` (90) · `AGENT_C` (38, 86) | S total; **Q90 is XS and is the single cheapest verdict in the table** |
| **3** | **Deity-query re-pointing + caveat correction across the catalogue** | **5, 43** (2) | Q2, Q19, Q35, Q62 (AV 5,084 + YV 2,240 seer edges are invisible to `HAS_DEVATA`-joined queries); also fixes the 13 caveats quoting stale `16,261 / 8,485` against live `17,165 / 8,825` | `AGENT_A_QUERIES` | XS |
| **4** | **Rishi layer: populate `RishiFamily`, type non-personal labels, default to strict ordering, return strict coverage** | **2, 19, 62** (3) | Q35, and close-out blocker 4 (holds rubric dimension G at 2 on its own) | `AGENT_D_RISHI_MATERIAL` | M |
| **5** | **Type the non-lexical similarity absence honestly**: rename `conceptually_similar_not_reused`, add an explicit `measure` column, and report the literal/semantic partition as a method census with `semantic_resemblance_population: NOT_BUILT` | **22, 49, 81** (3) | Nothing else. This is a refusal fix, not a capability fix, and it is the correct outcome per the brief: a truthful "this measure is lexical" beats 25 confident wrong pairs. | `AGENT_A_QUERIES` | S |
| **6** | **Ritual/offering ontology depth**: expand `Ritual` to the corpus's named rites, expand `Offering` past 2 nodes, add a passage-level ritual-context property | **56, 84, 100** (3) | Q32, Q39, Q91, Q95, Q61, Q4, Q31 | `AGENT_E_RITUAL_FORMULA` | M–L |
| **7** | **Measure and publish rite-layer and alias-list recall in the returned row; correct the cross-product** | **13, 60, 71** (3) | Q9, Q10, Q14, Q16, Q64, Q65, Q83 (all `PARTIAL` on unmeasured recall) | `AGENT_E` (rite) · `AGENT_D` (material) | M |
| **8** | **`about: DATASET \| VEDIC_TEXT` on `InterpretiveClaim` + refuse the Vedic-text question** | **28, 30, 72** (3) | Q99 | `AGENT_A_QUERIES` for containment; the real answer is `DATA_BLOCKED` | XS |
| **9** | **Store centrality on one declared-authoritative concept layer + ship a named query + report the rank correlation** | **37, 96** (2) | Q34, Q48, Q54, Q97; closes close-out §48 | `AGENT_A_QUERIES` | M |
| **10** | **Per-occurrence functional role (or aggregate the existing action frames by division)** | **52, 58** (2) | Q20, Q38, Q69 | `AGENT_C` + `AGENT_E` | L |
| **11** | **Extend the `CO_OCCURS_WITH` lift machinery to `Devata`↔`Object`** | **92** (1) | Q25, Q40 | `AGENT_C_DEITY` | S |
| **12** | **Rename `confidence` → `pipeline_prior`; add a constant-value guard** | **77** (1) | Every question that a reader might "filter to high confidence" for — which is all of them | `AGENT_A_QUERIES` for the rename; calibration is `HUMAN_BLOCKED` | XS / XL |
| **13** | **Store both strict and inherited deity concept profiles** | **3** (1) | Q44 | `AGENT_C_DEITY` | S |

**Reading of the leaderboard.** Fixes 1–3 clear or de-risk **11 of the 35** for M + S + XS, and
fix 2 contains the single cheapest item on the board: one label on `VG:CONCEPT:HOTR-PRIEST`
clears Q90. Fixes 5, 8 and 12 clear a further **7** by making the graph refuse honestly rather
than answer confidently — which the brief authorises and which is the right call, because in
every one of those seven the capability the criterion demands does not exist and cannot be built
in this session.

**Owner totals across binding assignments:** `AGENT_C_DEITY` 11 · `AGENT_A_QUERIES` 9 ·
`AGENT_E_RITUAL_FORMULA` 7 · `AGENT_D_RISHI_MATERIAL` 6 · `DATA_BLOCKED` 3 ·
`HUMAN_BLOCKED` 1 (Q77 calibration; the rename is `AGENT_A`). Sum exceeds 35 where a fix is
split between owners.

---

## D. Questions I could not grade, and questions marked `INHERITED`

**Could not grade: none.** All 100 carry a verdict.

**`INHERITED` — 3 questions.** For these I accepted the baseline's reasoning without running a
question-specific probe, and they are labelled so a later reader can close the gap:

| Q | Verdict | Why `INHERITED` |
| --- | --- | --- |
| **8** | `FULLY_ANSWERABLE` | I probed the `FormulaFamily` layer (720 nodes, 107 four-Veda, 2,037 `MEMBER_OF_FAMILY` edges) but did **not** re-run the per-`Formula` `vedas` / `veda_counts` census the baseline's verdict rests on. The 4,825 `Formula` node count is confirmed; the per-Veda occurrence vector on every node is not re-verified. Low risk: nothing in V3's changelog touches `Formula` properties. |
| **16** | `PARTIALLY_ANSWERABLE` | I probed the adjacent `PROTECTS_FROM` layer (659 edges, 4 Vedas, `rakṣas` AV 68 / RV 68 / SV 13 / YV 11) but did not re-run the baseline's specific four-entity enemy/protection probe (`śatru`, `śarman`, `sapatna`, `rakṣas`) with per-Veda counts. The binding blocker (unmeasured recall, no normalisation in the default query) is confirmed independently. |
| **98** | `NOT_ANSWERABLE` | I probed for stored centrality and community keys and for narrative/theme node types, both absent, but did not probe specifically for a path-scoring or interpretability property. The baseline's finding (3,252 two-hop paths from one verse, no scoring facility, no human-judged path sample) is accepted. The absence of any human-judged set anywhere in the graph — confirmed by the Q77 probe — makes the calibration clause unsatisfiable regardless. |

**One methodological caveat on the other 97.** `PROBED` here means I ran Cypher and read rows
bearing on the binding clause of the frozen criterion. It does **not** mean I re-verified every
clause of every criterion — for a `PARTIAL` verdict I probed the clause that keeps it below
`FULL` and the clause that would push it to `MISLEADING`, and stopped. The 35 `MISLEADING`
entries in §B each cite the rows they rest on and are the ones to audit first.

---

## E. Every verdict I moved off the baseline, with the direction and the reason

25 questions moved. **18 down from `MISLEADING`, 5 up from `NOT_ANSWERABLE` to `PARTIAL`, and
2 up from `NOT_ANSWERABLE` into `MISLEADING`.**

### E1. `MISLEADING` → `PARTIALLY_ANSWERABLE` (18) — improvements

| Q | Why it moved |
| --- | --- |
| **1** | The zero rows are gone. Indra is named in all four Vedas — RV 2,305 / AV 635 / SV 405 / YV 221 — and every edge is `DEITY_CERTAIN`, so the *absent-layer-as-absent-text* failure no longer fires. Stays `PARTIAL`: functional characterisation per Veda is RV-only (all 4,865 assertions are RV; the SV has none at all), and normalisation is not in any named query. |
| **4** | The naive/strict inversion is gone: `substances_offered_to_deities` now leads with `Indra/soma 285`, which is the ordering the baseline's strict filter produced. Stays `PARTIAL` on the same grounds the baseline used for Q61: still same-verse co-occurrence over a 2-node `Offering` class, still RV-only. Graded consistently with Q61 rather than above it. |
| **12** | Healing passages now carry deities in every Veda that has healing material: AV 47 passages / 12 deities, YV 31 / 14, RV 28 / 11. The Aśvins-fall-to-last inversion and the AV zero are both gone. |
| **18** | The verb-argument layer is real and the canonical deeds are in it. Measured: Indra `DESTROYS vṛtrám` (RV 1.61.10, 8 occurrences of the patient), `SLAYS áhim` (RV 2.15.1, 5.29.3), `DESTROYS valám` (RV 2.11.20), `DESTROYS púraḥ` (RV 1.130.7), `RELEASES` (RV 5.30.10) — with `frame`, `agent_surface`, `patient`, `instrument`, `beneficiary` and a per-verse locator. "Praise" is no longer the top-ranked action Indra performs. Stays `PARTIAL`: RV-only, and `patient` is a Sanskrit surface string rather than an entity, so it cannot be aggregated. |
| **20** | The three `HAS_AXIS` labels for Agni (`FIRE_MEDIUM`, `PRIESTLY`, `TERRESTRIAL`) are still per-node constants, which fails a clause — but they are substantively *correct*, and the action layer now supplies real per-occurrence deeds beside them. Failing a clause without a substantive error is `PARTIAL` by the baseline's own operating rule. |
| **23** | `CO_OCCURS_WITH` (306 `Devata`↔`Devata` edges) is computed from genuine same-verse co-naming across all four Vedas and carries `lift`, `baseline_mantras`, `per_veda_counts` and example citations. Compound-label pairs are separately available via `deity_composition`. The top result — `Mitra/Varuna, lift 13.19, 279 shared passages across four Vedas` — is correct. Stays `PARTIAL`: communities are not computed or stored. |
| **31** | as Q4. |
| **33** | as Q23. Verse-level multi-deity co-naming is now real: 2,623 passages name two deities, 624 name three, 226 name four, up to one naming thirteen — against the baseline's `nd=2: 6`. |
| **40** | `vajra` and `āyudha` now carry the `Weapon` label. `weapons_and_deities` leads with `thunderbolt (vajra) / Indra / 163 mantras / kind: Weapon`. The table that inverted its own answer now gets it right. Stays `PARTIAL`: no instrument role or narrative layer ties weapon to deity as anything but co-mention. |
| **41** | `DEVATA_ASSOCIATED_WITH` links deities to natural phenomena for 20 pairs, and the two the baseline said were silently dropped are now present (`rātri` → `Ratri, Night`; `āpaḥ` → `Apam Napat` and one other). The remaining zeros — `ahan`, `jyotis`, `samudra`, `tamas` — are defensible rather than artefacts of inflected string matching. Stays `PARTIAL`: the relation is association, not personification, and it is `TIER_D`. |
| **44** | Both deities are now named across all four Vedas (Indra 3,566 passages, Varuṇa 589, all `DEITY_CERTAIN` for both), so the volume asymmetry is measurable and normalisable per Veda instead of being reported as a profile difference from RV-only attribution. Stays `PARTIAL`: the axis vectors are still curated constants. |
| **47** | The `quality_tier` now travels **in the returned row** (`concerns_addressed_versus_protected_from` returns `tier` per row), which is the criterion's central demand, and `takman` is present as its own entity with 33 `TREATS` edges. Stays `PARTIAL`: the practice vocabulary covers amulet (`maṇi`), plant (22 `Plant` nodes) and water (`āpaḥ`) but has no spell class, and `TREATS` is still the project's judgement rather than a source-stated treatment. |
| **51** | Both deities now have per-occurrence action profiles with argument frames — Indra 37 distinct actions, Varuṇa 16 — over a 41-member closed action vocabulary rather than five abstract nouns, and "praise" is no longer top for either. Stays `PARTIAL`: no distinctiveness statistic controlling for the base rate, which is the criterion's core clause. |
| **66** | The join has inverted correctly. `TREATS` reaches **AV 139 passages with 15 deities named**, RV 2, YV 1. The reading "in the Rigveda healing is always accompanied by divine invocation; in the Atharvaveda essentially never" is no longer producible. Stays `PARTIAL`: `TREATS` is graded `TIER_D` precisely because naming a condition is not treating it, so the healing-act relation is still not distinct from mentioning an affliction. |
| **70** | This is the largest single improvement in the benchmark. The prominence series now computes across all four Vedas on per-verse mention evidence, normalised: Indra RV 218.4/1k → SV 219.6 → YV 111.9 → AV 108.8; **Rudra RV 12.1 → YV 20.8** (rises); **Viṣṇu RV 9.3 → YV 21.8** (rises). The most-cited diachronic claim about the Vedic pantheon is now supported by measured rows rather than unlooked-at. Stays `PARTIAL`: no confidence intervals, no graph-recorded falsifier, and "division" is still Veda rather than time. **Live hazard, recorded here because it is not visible in the row:** every non-RV Rudra edge is `DEITY_AMBIGUOUS`, so a researcher filtering to `DEITY_CERTAIN` gets Rudra RV 33 and nothing else, and the trend inverts. Fix 1 in §C2 removes this. |
| **73** | `evidence_basis` is now correct across the graph — zero `UNSPECIFIED` edges. The L3 slice carries `TRANSLATION`/`MIXED` matching its Whitney/Griffith quotations, and the translation-dependency census (3,354 `TRANSLATION` + 13,694 `MIXED` = 17,048) no longer silently under-reports. Blocker B15 closed. Stays `PARTIAL`: no per-question withdrawal simulation. |
| **74** | The Sanskrit-only projection now **retains** the layers it used to delete: `MENTIONS_ENTITY 28,227`, `USES_FORMULA 22,686`, `MENTIONS_DEVATA 17,165`, `ABOUT_CONCEPT 13,356`, `MENTIONS_LEMMA 9,000`, and all four cross-Veda parallel types. The Anukramaṇī layer is correctly `SOURCE_METADATA` rather than being silently discarded as `UNSPECIFIED`. Stays `PARTIAL`: no per-question delta report. |
| **89** | The 3-against-651 artefact is gone: Vāc-as-deity now reaches **302 passages across four Vedas** against 651 for the noun, and an explicit `DEVATA_ASSOCIATED_WITH` edge links `VG:DEVATA:VAK` to `VG:CONCEPT:VAC-SPEECH` — the criterion's two central demands. Stays `PARTIAL`: `referent_certainty` is `DEITY_AMBIGUOUS` on **all 302** Vāc mentions and 0 are certain, so the per-occurrence sense decision exists as a field that declines to decide, with no accuracy figure. |

### E2. `NOT_ANSWERABLE` → `PARTIALLY_ANSWERABLE` (5) — layers that landed

| Q | Why it moved |
| --- | --- |
| **27** | The family construct exists: **720 `FormulaFamily` nodes**, 2,037 membership edges, roles typed (`CORE` 914, `EXPANSION` 1,119, `VARIANT` 4) with a named, reproducible relatedness derivation per role (`formula-family-core-v1`, `-expansion-by-containment-v1`, `-variant-by-similarity-v1`). 107 families span all four Vedas. Stays `PARTIAL`: 2,037 memberships over 4,825 formulas means 58% of the inventory is in no family. |
| **57** | Same layer, and the per-Veda distribution is on the family (`occurrences_per_veda`, e.g. `viśvā bhuvanā` 14 members / 148 occurrences / `{AV:14, RV:39, SV:2, YV:5}`). Stays `PARTIAL` on the same 42% membership coverage. |
| **63** | A chance baseline now exists. `CO_OCCURS_WITH` carries `lift`, `baseline_mantras`, `mantras_a`, `mantras_b`, `rv_passage_count`, `non_rv_passage_count` and `per_veda_counts` over verses that genuinely attest more than one deity, and compound-derived pairs are separately reported. Stays `PARTIAL`: `lift` is a ratio, not a significance statistic; `observed` and `expected` are null on every edge; there is no multiple-comparison correction — all three named in the criterion. |
| **69** | Role is still a `Devata`-node property, but **action** is now a property of the occurrence: 4,865 reified `SemanticAssertion` nodes with `frame`, `agent_surface`, `patient`, `instrument`, `beneficiary` and a passage key, so within-deity variation across passages is retrievable (Indra `IS_OR_BECOMES` in 55 passages, `CREATES` in 40, `SLAYS` in 19). Stays `PARTIAL`: RV-only, no measured accuracy, and action is a proxy for role rather than role. |
| **97** | The top quality tier now holds semantic content: `TIER_A` contains **`MENTIONS_DEVATA` 5,900** alongside `HAS_CHANDAS` 5,932, `HAS_RISHI` 2,712, `HAS_DEVATA` 2,229. Communities computed on it would be thematic, not merely bibliographic. Stays `PARTIAL`: `TIER_A` passage→`DomainEntity` is still **0**, no communities are computed or stored, and no partition-similarity figure exists. |

### E3. `NOT_ANSWERABLE` → `MISLEADING` (2) — regressions created by V3

These are the two the brief's instruction to deep-probe the `NOT_ANSWERABLE` set was written to
catch: in each, a layer added since `bb27f3c` turned a clean zero into a confident wrong answer.

| Q | Why it moved, and in which direction |
| --- | --- |
| **85** | **Worse.** Baseline `NOT_ANSWERABLE` because Sarasvatī was absent from the `River` class and there was no per-occurrence sense field, so no query returned anything. Sarasvatī is now `:River` — with **2 mentions** against 213 as a deity — and the per-occurrence query returns a complete-looking table with `theonym_ambiguous = false` on **100% of all six named hydronyms**. The reader now gets an answer, and the answer is that Sarasvatī is essentially never geography. Full entry in §B1. |
| **86** | **Worse.** Baseline `NOT_ANSWERABLE` because `PERSONIFIES` had 0 instances. `DEVATA_ASSOCIATED_WITH` is now populated, so the query returns rows — and it reports "fire (agni)" with **5 personifications** (`Agni`, `Agni Jatavedas`, `Agni Pavamana`, `Agni the slayer of demons`, `the self of Agni`), "horse (aśva)" with 3 (`the horse`, `the horses`, `the steeds`), "bowstring (jyā)" with 3 (`the bow`, `the bowstring`, `the two bow-tips`). Every inflation is an epithet-qualified or number-variant `Devata` node not linked to its base — which is the exact failure the frozen criterion names. Full entry in §B3. |

### E4. Verdicts held against the baseline (75)

Not enumerated line by line, but two groups are worth naming because a reader may expect them to
have moved and they did not:

- **The registry-fix questions where the fix landed but the answer did not change.** Q13 (marriage
  recall still 9.9% on AV K14 — 14 tagged of 141), Q25 (`vajra`/`āyudha` typed as `Weapon` but
  `Object` still conflates them into the ritual-implement table), Q26 (Sarasvatī typed as `River`
  but with 2 mentions), Q90 (`udgātṛ` added, `hotṛ` still untyped). Four of the baseline's five
  named "cheapest high-reach" registry edits were made; the fifth was missed, and the four that
  landed cleared only Q40 and Q47 on their own.
- **The five `FULLY_ANSWERABLE` questions are the same five as at baseline** — Q6, Q8, Q29, Q75,
  Q76. The V3 close-out's claim of 7 is not reproducible and the report does not say which two it
  counted. `FULLY_ANSWERABLE` against a target of 60 is therefore **5**, not 7, and it did not
  move at all in V3.

---

## F. Two live hazards that are not `MISLEADING` today but will be if a filter is applied

Recorded because they are invisible in the row set and because a later agent adding a
"default safe" filter would create four new `MISLEADING` verdicts in one commit.

1. **Filtering to `referent_certainty = DEITY_CERTAIN` re-creates the RV-only graph for every
   common-noun deity.** Measured per-deity, non-RV certain counts: **Agni 0, Soma 0, Sūrya 0,
   Mitra 0, Savitṛ 0, Uṣas 0, Vāyu 0, the Waters 0, Pṛthivī 0, the Ādityas 0, Heaven-and-Earth 0,
   Vāc 0 in every Veda including the RV.** Indra, Varuṇa, the Maruts, the Fathers, Bṛhaspati,
   Aditi and Viṣṇu are 100% certain everywhere. So the certainty field partitions the pantheon by
   *whether the theonym is also a common noun*, not by whether the referent is decidable, and the
   cautious analyst gets a worse answer than the careless one. This would move Q1, Q12, Q44, Q66,
   Q70 and Q89 back to `MISLEADING`. It is the reason fix 1 in §C2 is ranked first.

2. **Rising concept-layer agreement is being read as corroboration.** §A already states the
   measurement. Any V3.1 artefact that quotes "94.4% agreement" or "24,947 corroborated" without
   the word *nested* is reproducing the defect Q76 exists to detect, and Q76 is one of only five
   `FULLY_ANSWERABLE` questions — it is worth not losing.

---

## G. Provenance of this diagnosis

- Probes were run through two read-only harnesses written into the session scratchpad, never into
  the project: a batch Cypher runner with a write-keyword guard, and a runner that executes the
  shipped `DomainQuery` objects with their declared default parameters. Named queries were
  preferred wherever `questions_served()` supplies one; for Q37 and all of Q51–Q100 no named query
  exists and **the Cypher was authored by me**, written as the obvious query a competent user
  would write against the frozen question wording, and is quoted or described in each entry.
- Every `MISLEADING` entry in §B cites counts or rows read from the live database at
  `d456cce`, not figures carried from either prior report. Where a prior report's figure is
  reproduced it is marked as confirmed.
- Grading applied the frozen four states and the baseline's own operating rule: `MISLEADING`
  requires substantive error — wrong top-ranked members, wrong zeros, or wrong class membership —
  and directionally-right-but-thin is `PARTIALLY_ANSWERABLE`. Where that rule made me lenient
  (Q4, Q31, Q20, Q23, Q33) or harsh (Q19, Q56, Q86) relative to a plausible alternative reading,
  the entry says so.
- No fix proposed in this document special-cases a question number or hard-codes an answer.
  Seven of the 35 (Q22, Q28, Q30, Q49, Q72, Q77, Q81) are cleared by making the graph return
  `INSUFFICIENT_EVIDENCE` or by renaming a field to what it measures, because the capability the
  criterion demands does not exist — a truthful refusal, per the brief.

---

## H. Referred to me mid-session: `attribution_precision` NULL on the formula-family twins

The integrator routed a decision to me about 4,074 edges carrying no `attribution_precision`.
**Two corrections on routing before the judgement.** First, I am read-only for this whole phase
under `V3_1_ROI_PLAN.md` §4, so I have applied nothing and will not; the formula-family layer is
`AGENT_E_RITUAL_FORMULA`'s partition. Second, the message describes `HAS_FORMULA` as "your new
edges" — those edges did not exist when I took my census (my relationship-type census at
`d456cce` has no `HAS_FORMULA` at all), and they exist now, so they were created by Agent E
during this session. The decision belongs to Agent E and the write does too.

**Measured read-only, just now:** `HAS_FORMULA` 2,037 NULL, `MEMBER_OF_FAMILY` 2,037 NULL,
**4,074 total, and no other predicate in the graph is NULL on this property.** Value space is
`PER_PASSAGE 203,052 · CONTAINER_INHERITED 39,290 · TEXTUAL_MENTION 17,471 · null 4,074`. Total
relationships have moved to **263,887** under concurrent mutation. `MEMBER_OF_FAMILY` carries the
other four grading fields on 2,037 of 2,037 — only `attribution_precision` is missing, which is
consistent with the property having been treated as inapplicable rather than forgotten.

**My judgement: (a) is semantically right and (b) is operationally right for this session, and
the reason is a value-space hazard rather than a semantic one.**

The integrator's argument for (a) is correct on the semantics: `attribution_precision` records
whether an *attribution*'s scope is the verse or the container, and a formula-to-family membership
makes no attribution. There is even schema precedent — `TEXTUAL_MENTION` was already added as a
third value to say "this is a token occurrence, not an attribution", so the field is already doing
kind-of-claim work as well as scope work.

What defeats (a) *as a two-predicate patch* is that the graph has an existing, unbroken convention
that contradicts it. I enumerated the non-attribution predicates and every one of them carries
`PER_PASSAGE`: `HAS_TEXT_VERSION` 44,276, `CONTAINS` 22,537, `USES_FORMULA` 22,686,
`MENTIONS_ENTITY` 28,227, `EXACT_PARALLEL_OF` 1,006, `BROADER_THAN` 97, `COMPOSED_OF` 28. A
passage-to-its-text-version edge is not an attribution either, and it says `PER_PASSAGE`. So
setting `NOT_AN_ATTRIBUTION` on 4,074 edges while ~90,000 equally non-attributional edges keep
`PER_PASSAGE` does not make the field honest — it makes it *two* conventions, and it introduces a
fourth value that only two predicates in the whole graph carry.

That is precisely the failure mode this project has already been burned by twice: an audit that
selects safe edges as `attribution_precision <> 'CONTAINER_INHERITED'` keeps the new value, an
audit that selects `IN ['PER_PASSAGE','TEXTUAL_MENTION']` silently drops 4,074 edges, and neither
audit's author will know which they wrote. Enumerate the value space, do not assume it.

**Recommendation to Agent E, in order:**

1. **Now, in this session:** set `attribution_precision = 'PER_PASSAGE'` on both
   `MEMBER_OF_FAMILY` and `HAS_FORMULA` (2,037 each; expected after-count for
   `edges_without_attribution_precision` is **0**, and `PER_PASSAGE` should rise 203,052 →
   207,126). It is wrong in the same way and to the same degree as the seven predicates already
   listed, which is what makes it safe: it adds no new partition and breaks no existing filter.
   Apply it to both twins in one statement so inbound and outbound cannot drift, and confirm with
   `scripts/check_live_invariants.py` rather than from the write's own report — the memory note on
   verifying projections against a live store applies.
2. **As a named backlog item, not in this session:** introduce `NOT_AN_ATTRIBUTION` (or better,
   split the field into `attribution_scope` and drop the property from predicates that make no
   attribution) across the **whole** class of non-attribution predicates in one commit, with the
   query catalogue's `attribution_precision` filters updated in the same commit. That is the
   honest end state and it is an ontology change, not a property backfill.

**On the over-claim:** the V3 close-out §50 states "Evidence coverage **100%** — 261,584 of
261,584 edges carry all four grading fields." That claim is *literally* true as worded, because
`attribution_precision` is not one of the four fields it names (`knowledge_layer`,
`quality_tier`, `evidence_basis`, `grade_basis` are all present on 2,037 of 2,037
`MEMBER_OF_FAMILY` edges — verified). What is false is §57's stronger claim that "Grading gaps are
zero on every axis" alongside an `attribution_precision` split of "202,786 / 39,290 / 17,471"
which sums to 259,547 against 261,584 relationships — a 2,037-edge shortfall that the report
prints and does not notice. The over-claim is therefore in the *arithmetic already on the page*,
which is a stronger finding than a missing property: the numbers in §57 do not add up to the
number in §9, and nothing in the report reconciles them. The integrator is recording this; I am
recording only the precise form of it, since "100% of four fields" and "zero gaps on every axis"
are different claims and only the second is wrong.
