# VedaGraph V3.2 — Final Ontology Closure

**Scope.** Four named ontology defects, closed. No new knowledge, no new sources, no new
extraction, no V4. This session is a closure of uncertainty, not an enrichment.

| # | Item | Value |
|---|---|---|
| 1 | Starting commit | `e192a81` (branch `semantic-pilot-v1`), working tree clean |
| 2 | Agents | 4: **A** integrator (this report), **B** Devatā identity + epithet closure (read-only), **C** Condition + attribution contract (read-only), **D** final independent evaluator (read-only, post-freeze) |
| 3 | Seal | No file inside the semantic seal was touched. The seal's `frozen_hashes` covers seven files, all under `src/vedagraph/semantic/`; every edit here is in `domain/`, `enrich/`, `data/registry/` or `data/domain/`. Verified before the first edit, not after. |

---

## 0. Two corrections to the brief's own starting figures

Both were checked before any change was made, because a baseline that is wrong makes every
later delta unreadable.

**The brief's relationship count was stale.** It states V3.1 achieved 266,757 relationships.
The live graph held **265,289**. This is not drift: `V3_1_ADVERSARIAL_REATTACK.md` and
`V3_1_ADVERSARIAL_THIRD_PASS.md` both independently measured 265,289 and the third pass calls
it "unchanged from pass 2, freeze held". 266,757 is the pass-1 figure, superseded twice
before this session began. **All deltas below are against 265,289.**

**A committed artifact was stale, and the rebuild corrected it.** `devata_profiles.jsonl`
changed in 20 of its 25 rows on rebuild, with figures like Agni's top concept "fire (agni)"
moving 1,019 → 422. This was investigated rather than accepted, because a large unexplained
movement in a regenerated artifact is exactly what a silent regression looks like. It is not
one:

- `ABOUT_CONCEPT`, `HAS_DEVATA`, `MENTIONS_DEVATA` and `MENTIONS_ENTITY` all hold **exactly**
  their baseline edge counts (24,969 / 10,558 / 17,165 / 28,223). Nothing was deleted.
- Probed live, the Agni figure decomposes as 422 rows over 422 distinct passages over 422
  distinct edges — one edge per passage, no duplication. **422 is what the graph says.**
- The committed 1,019 predates V3's retirement of the 21,539 translation-only aboutness
  edges (47,976 → 24,969 kept, 52%). The per-concept kept-ratios (Agni fire 41%, Sūrya sun
  44%, Uṣas dawn 82%) vary exactly as they should, since English-only evidence was
  concentrated unevenly across concepts.

So the artifact committed at `e192a81` was **stale by a whole V3 retirement** and was never
regenerated. V3.2's rebuild is the correction. Anyone who quoted a top-concept count from
that file was quoting evidence the project had already withdrawn.

---

## Fix A — EPITHET_VARIANT_OF coverage

**Method.** Agent B did not sweep the graph labels; it went to the printed source, because
the registry's evidence rule is the source label and nothing else. The Anukramaṇī data is in
the repo at `data/raw/wsc2023/2026-09-04/*.txt` (`hymn.verses.seer.divinity.meter`). Parsing
all ten maṇḍalas yields 212 distinct divinity tokens against 214 node labels — effectively
1:1 — so the sweep ran against what the editors actually printed.

**The orthographic rule the sweep established, and which decides two rows.** In this source
a hyphen is the editors' **co-ordination marker** between separate names and is never an
epithet join: the complete inventory of hyphenated divinity tokens is ten strings, and nine
are unambiguously lists of distinct deities or patrons (`agniḥ-marutaḥ`, `indraḥ-marutaḥ`,
`vāk-āpaḥ`, `iḻā-sarasvatī-mahī`, …). Every epithet-qualified label in the same source is
printed with a space (`jātavedā agniḥ`) or solid (`rakṣohāgniḥ`). That is a label-only test,
which is the evidence class the registry demands.

| | Before | After |
|---|---|---|
| `EPITHET_VARIANT_OF` edges | 6 | **11** |
| Registry rows | 11 | **25** |
| ASSERTED / REFUSED / NOT_IN_SCOPE | 6 / 3 / 2 | **11 / 10 / 4** |

**Cases resolved.** Across the 72 `INDIVIDUAL` nodes the strict test returns eight hits: five
were already asserted, two are pure orthographic accidents (`puruṣaḥ` ends in the letters of
`uṣāḥ`; `rātriḥ` in those of the ṛṣi `atriḥ`), and **one is new** — and it is the case the
V3.1 report named:

- `VG:DEVATA:MARUTVANINDRAH → VG:DEVATA:INDRAH`, `EPITHET_QUALIFIED`. The label
  `marutvānindraḥ` carries the base `indraḥ` unaltered as its second compound member, with
  no sandhi adjustment at all. 19 attributions, RV 1.165 and 1.171. Deliberately **not** also
  linked to `MARUTAH`: RV 1.171 prints `(1-2)marutaḥ,(3-6)marutvānindraḥ`, so the editors
  themselves keep the Maruts and Marutvān-Indra apart in one hymn.

Nine new REFUSED rows were added so each absence is a recorded decision rather than a gap:
`INDRASYASVAU`, `APAM-NAPAT`, `SARASVAN`, `SAVITRI-SURYA`→`SAVITA`, `BRAHMANASPATIH`,
`RATHAGOPAH`, `YAMAH`/`YAMI`, `DADHIKRAH` (refused *as an epithet* and routed to Fix C). The
refusals matter as much as the assertion: `brahmaṇaspatiḥ`/`bṛhaspatiḥ` is the standard
scholarly identification and is refused precisely because it rests wholly on secondary
literature and no shared printed substring.

**Unresolved variants: exactly one.**

`VG:DEVATA:APTRNAH-SURYAH` (`aptṛṇaḥ-sūryaḥ`, 16 attributions, RV 1.191). Its label contains
`sūryaḥ` as a whole printed word, making it the strongest-looking candidate in the corpus,
and the hyphen rule places it out of scope as a composite. It is recorded `NOT_IN_SCOPE`,
asserting no edge and destroying nothing. Two things a reader must know:

- It **reverses a standing project decision.** The node's `display_label` reads "Surya, with
  the epithet aptrna" and `devata_taxonomy.yaml` stores `label_iast: aptṛṇaḥ sūrya` **with a
  space** — the taxonomy normalised away the very hyphen that carries the evidence. That
  gloss is a project reading, not a source label, so it cannot count as evidence here; but
  the two artifacts disagree and that is now written down instead of latent.
- **Both readings agree on the outcome** — keep the entity separate, assert no edge — which
  is why nothing was changed. The live residual: `deities_by_axis` reports it as a third
  `INDIVIDUAL` deity on the solar axis beside `sūryaḥ` and `sāvitrī sūryā`.
- **What would settle it:** the printed devatā slot for RV 1.191 in an edition other than
  WSC2023, showing a three-member dvandva against a bahuvrīhi epithet. One line of one
  printed edition closes it.

---

## Fix B — Condition taxonomy

A new **required** property `condition_kind` on every `:Condition`.

| `condition_kind` | Nodes |
|---|---|
| `AFFLICTION` | **26** |
| `THREAT` | **8** |
| `PATHOGEN_OR_CAUSE` | **2** (worms, poison) |
| total | **36** |

**Three values, not the five suggested.** `STATE` and `UNSPECIFIED` were both considered and
both refused, each with zero members. `STATE` had three candidates — greying, madness,
debility — and all three lose on their own definitions (the corpus prints a remedy compound
for the first two; the third is borne by a body). It would also collide with the live `:State`
label and the live `STATE` node type, putting two unrelated meanings on one token in one
graph. `UNSPECIFIED` is refused on this repository's own precedent: a live `UNSPECIFIED` on
the adjacent axis reached 61,861 edges, 25.5% of the graph, because a declared shrug is
always used. Instead the field is **required and the load fails without it** — verified to
raise on a missing kind, an invalid kind, and a kind on a non-Condition.

The check runs **after** `NODE_TYPE_OVERRIDES`, not before. `RAKSAS-DEMON` is authored
`node_type: CONCEPT` and retyped to `CONDITION` during the merge, so validating the authored
type would have waved through the demon — the one entity whose misclassification created this
defect.

**Disease/affliction query sanity, measured live.**

- `conditions_treated` now returns **26 distinct conditions, THREAT/PATHOGEN leakage NONE**,
  with *takman* present as its own entity. Before, it answered an affliction question over
  all 36: of the 718 `MENTIONS_ENTITY` edges reaching a Condition, **314 reach a THREAT and
  88 a PATHOGEN_OR_CAUSE**, so demons, sorcery, curses, worms and poison ranked as diseases.
  Benchmark Q15's acceptance criterion names this defect in terms.
- `passages_protecting_against` **stays broad and still returns the demon** (rakṣas, 68 AV /
  68 RV), now self-labelling as `THREAT` rather than showing a bare `display_type: Condition`.
  `condition_neighbourhood` and `concerns_addressed_versus_protected_from` also stay broad,
  each gaining one additive column.
- `medicinal_plants` splits its column into `co_afflictions` and `co_threats` rather than
  filtering, because a plant co-named with a demon is a real finding for the
  counter-witchcraft herbs.

**The filter is on `condition_kind`, never on `[:TREATS]`, and that is load-bearing.**
Measured: `TREATS` is 135 AFFLICTION / 25 PATHOGEN / **0 THREAT**, but `PROTECTS_FROM` is 314
THREAT / **181 AFFLICTION** / 63 PATHOGEN / 101 non-Condition. The two predicates are
whitelists graded on *evidence strength* — whether the corpus prints an explicit remedy
compound — not on what kind of thing the target is. Filtering by predicate would have dropped
six afflictions reachable only through `PROTECTS_FROM`, **consumption among them**: the
corpus's most-attested disease. `condition_kind` is orthogonal to the predicate split and the
two must not be reconciled.

Ten rows are flagged ARGUABLE in the source with both readings stated. The sharpest is
`DUSVAPNYA-BAD-DREAM`, where the entity's own definition ("treated as an affliction")
contradicts the V1 file header (which groups it with the causes); it is filed `AFFLICTION` on
its own words, and the disagreement is recorded rather than smoothed.

---

## Fix C — Duplicate-label Devatā pairs

**The reproducing query** (the obvious `v.label` returns nothing — that property does not
exist; `preferred_label` gives zero collisions and `label_iast` a different four):

```cypher
MATCH (v:Devata)
WITH toLower(trim(v.display_label)) AS lbl, collect(v.entity_key) AS keys, count(*) AS n
WHERE n > 1 AND lbl IS NOT NULL
RETURN lbl, n, keys ORDER BY n DESC, lbl;
```

**Root cause, stated because it will recur.** The `entity_key` slug folds diacritics but
preserves ASCII letters and word boundaries. So a source spelling slip **merges silently**
when it differs only in a diacritic and **forks into a pinned duplicate** otherwise. The proof
is `sarasvati-iḻā-bhāratī`: the one source token with no matching node label, because it
merged into `sarasvatī-iḻā-bhāratī` on a macron.

| Pair | Classification | Resolution |
|---|---|---|
| `VISVE-DEVAH` / `VISVEDEVAH` | **SAME_ENTITY** | `ORTHOGRAPHIC_VARIANT` edge (10 attributions beside 805) |
| `DEVYAU-HOTARAU` / `DAIVYAU-HOTARAU` | **SAME_ENTITY** | `ORTHOGRAPHIC_VARIANT` edge |
| `BHAVAVRTTHAM` / `BHAVAVRTTAM` | **SAME_ENTITY** | `ORTHOGRAPHIC_VARIANT` edge |
| `DADHIKRAH` / `DADHIKRA` | **SAME_ENTITY** | `ORTHOGRAPHIC_VARIANT` edge |
| `AGNAMARUTAH` / `AGNIH-MARUTAH` | **COMPOSITE_DISTINCT** | **preserved**, distinct `display_label` |
| `DYAVABHUMI` / `DYAVAPRTHIVYAU` | **COMPOSITE_DISTINCT** | **preserved**, distinct `display_label` |

No pair is `HOMONYM_DISTINCT` and none is `UNRESOLVED`. **Nothing was merged and no node was
deleted**; `entity_key` is pinned identity in this project.

**A fourth `relation` value, `ORTHOGRAPHIC_VARIANT`, was added and the decision is recorded.**
The three existing values are all false of these rows: there is no qualifier, so
`EPITHET_QUALIFIED` and `PART_OF_DEITY` would record one no reviewer could find, and
`NUMBER_VARIANT` is wrong because `structure` is identical on both sides — which is exactly
what distinguishes them from the `gāvaḥ`/`gauḥ` rows the file already declines. The
`EPITHET_VARIANT_OF` edge is nevertheless the right carrier: its only job in every consumer
is "resolve me to my canonical base before counting", and the `relation` property exists
precisely so a consumer can narrow — the pre-existing `PART_OF_DEITY` row is already not an
epithet. The alternative, a distinct `display_label` alone, would have hidden the doubled
string while leaving the doubled count: the worse of the two failures, because it makes the
defect invisible without making it false.

**The deity-counting contract, verified live:**

```
resolved labels mapping to >1 deity: 0
```

Four raw duplicate `display_label`s remain, and that is correct: they are the four
same-entity pairs, which *should* render one string because they are one being, and every
counting query resolves them through the edge. The two composite-distinct pairs now render
distinctly. **No product query double-counts a deity because duplicate nodes exist.**

Three loader invariants were added, because a one-hop resolver fails silently otherwise: an
unknown `relation` raises; a variant asserted to two bases raises (it makes `coalesce` order-
dependent); and a base that is itself a variant raises, because every consumer writes
`coalesce(base, dv)` and none walks `EPITHET_VARIANT_OF*`, so a two-link chain would resolve
to the middle and still double-count while looking resolved. All three verified to fire.

---

## Fix D — The attribution contract

**Architecture chosen: an explicit `NOT_AN_ATTRIBUTION` sentinel.** The contract is now
*every edge carries `attribution_precision`; a live NULL is a defect.*

**Why, and the argument is the repository's own history rather than principle.** The
alternative — leave the property absent on non-attributions — is not hypothetical here. It was
the status quo for `MEMBER_OF_FAMILY` and `HAS_FORMULA`, and it failed twice inside one
module:

- The absence had to be created by an explicit `REMOVE`, and the comment says why: an earlier
  build wrote `TEXTUAL_MENTION` there, and MERGE-plus-SET leaves an unmentioned property in
  place, so dropping the assignment cleaned new edges and left **2,037 old ones asserting a
  category error**. Under absence, every future casualty must be remembered by name.
- Five hundred lines later the same file reaches the **opposite** verdict on the identical
  category error. `BELONGS_TO_FAMILY` is `Rishi → RishiFamily`, has no passage endpoint, and
  carries `CONTAINER_INHERITED` — conceding in comment that "the property should be absent"
  and then overruling it because "the invariant that every edge carries full grading metadata
  wins, and once the property has to hold something the only safe value is the inherited
  one." It therefore minted an inheritance claim about a container that does not exist. **The
  sentinel is the option that comment was reaching for**: the invariant is kept in full and no
  false value has to be minted to keep it.
- An undeclared value was already live and nothing caught it: `EPITHET_VARIANT_OF` carried
  `REGISTRY_STATED`, never a member of the enum, through three adversarial passes. There was
  no closed-world check on this property anywhere in the codebase.

**The defining test**, applied mechanically to all 65 live types: *an edge is
attribution-bearing iff one endpoint is a `:Passage` and the edge attaches a claim to it that
could in principle have arrived from the enclosing sūkta instead — so that "of this verse, or
of its container, or does the verse's own Sanskrit say it?" is well-formed with more than one
answer.*

| Value | Types | Edges before | Edges after |
|---|---|---|---|
| `NOT_AN_ATTRIBUTION` | 37 | 0 | **105,858** |
| `TEXTUAL_MENTION` | 5 | 17,471 | **102,043** |
| `CONTAINER_INHERITED` | 5 | 39,714 | **39,709** |
| `PER_PASSAGE` | 22 | 203,904 | **17,684** |

Two classes moved. Structural, analytic, taxonomic, reification and self-audit edges took the
sentinel: `CONTAINS` had claimed per-passage attribution over the corpus's own containment
tree, `HAS_TEXT_VERSION` over the edition's typesetting, `QA_ISSUE_ON` over this repository's
self-audit. And four mention-class types — `MENTIONS_ENTITY`, `ABOUT_CONCEPT`, `USES_FORMULA`,
`MENTIONS_LEMMA` — moved to `TEXTUAL_MENTION`, because they are the same act of naming that
`MENTIONS_DEVATA` already recorded that way; grading `MENTIONS_ENTITY` differently from its
own narrowing to deities was the incoherence at the centre of the defect.

**Root cause fixed, not papered over.** `grade_edge` had eight return sites and seven
hardcoded `PER_PASSAGE`; only the `scope_origin` branch consulted anything. It is now wrapped
so the layer, tier, basis and evidence axes come from what the edge records, while the
attribution axis is looked up by relationship type — because it is a fact about the *endpoints*
that no property on the edge can witness. **A type absent from the contract raises**, which is
the whole point of preferring a sentinel: `stamp_grades` discovers types from the live graph,
so a new type must fail the build rather than default to looking correct.

Four `MIXED` types (`HAS_DEVATA`, `HAS_RISHI`, `HAS_CHANDAS`, `USED_FOR_RITE`) are excluded by
name and left to `scope_origin`. This is not a theoretical hazard: a generic sweep once
flattened all 529 `USED_FOR_RITE` edges and turned 419 book-locus priors into per-verse
statements.

**A sequencing defect was found and fixed while verifying.** After the first rebuild, six
types still held `PER_PASSAGE`. `stamp_grades` runs inside the domain build, but the V3
projection rebuilds `PERFORMS_ACTION`, `IS_ASKED_TO` and the assertion spokes *afterwards*,
overwriting it with literals. Two things were done: the literals were corrected at source, and
a final `apply_attribution_contract` step now runs **last** in the V3 projection, one
relationship type per statement (never an unlabelled `MATCH` — that pattern once created
39,461 bogus edges here). It reports `sent=0` on a clean graph, which is the desired steady
state.

**Attribution invariant result.** The old check demanded the property from every
passage-touching edge, which was itself unsound — `CONTAINS`, `HAS_TEXT_VERSION` and
`QA_ISSUE_ON` all touch a passage and attribute nothing. It is replaced by three:

| Invariant | Result |
|---|---|
| `edges_without_attribution_precision` | **0** |
| `attribution_precision_outside_the_declared_enum` | **0** |
| `attribution_claimed_on_an_edge_with_no_passage` | **0** (was 4,235) |

The third checks endpoint truth independently of the contract table, so the table cannot
certify itself. Verified: all 65 live types conform.

---

## Rebuild, reconciliation and idempotence

| | Before | After |
|---|---|---|
| Nodes | 108,777 | **108,777** |
| Relationships | **265,289** | **265,294** |

**The +5 reconciles exactly and to nothing else:** `EPITHET_VARIANT_OF` 6 → 11. No other edge
type moved by a single edge.

- **Projection reconciliation:** every layer reports `sent == landed` — 14 domain-build steps
  and all 24 V3 layers, including the new `apply_attribution_contract`.
- **Idempotence:** a second full projection over the unchanged tree returns the graph to
  108,777 / 265,294 with all layers still `sent == landed`. (Within a cycle the domain build
  dips to 265,291 and the V3 build restores it; the cycle is the fixed point.)
- **0 stale MERGE survivors**, **0 product QAIssue leakage** (0 product→QAIssue edges, 0
  QAIssue nodes unmarked `Internal`), **0 duplicate-count regressions**.

---

## Targeted adversarial check — modified areas only

| Area | Result |
|---|---|
| Deity counting | resolved labels mapping to >1 deity: **0** |
| Epithet variants | 11 edges, all 11 registry-backed; no chains, no forks, no unknown relations |
| Duplicate labels | 4 same-entity pairs resolve to one; 2 composite pairs display distinctly |
| Condition filtering | `conditions_treated` 26 afflictions, **0** threat/pathogen leakage; broad queries still reach the demon |
| Attribution semantics | all 65 types conform; 0 NULL, 0 undeclared, 0 attribution-without-passage |
| Product/internal boundary | **0** leakage |

**0 CRITICAL.**

One finding was raised by Agent B and **dismissed on measurement**: `is_composite` looked out
of sync with `structure` (14 of 38 `PAIR` nodes true). It is not a defect — `is_composite`
means "has a reviewed decomposition in `devata_components.yaml`", set from the component
count, and `queries.py` already carries an explicit "DO NOT filter on `is_composite` for
this". An alarm verified and closed is worth as much as one raised.

---

## Test, lint and type results

| Gate | Result |
|---|---|
| `pytest -m "not live and not api"` | **1,551 passed, 39 skipped, 0 failed** (18m27s). Baseline was 1,548; the three new tests assert the contract covers every declared relationship, that an uncontracted type raises, and that no contract row holds a value outside the enum. |
| `mypy --strict` | **Success: no issues found in 159 source files** |
| `ruff check` | **All checks passed** |
| `ruff format --check` | 36 files would be reformatted — **entirely pre-existing**. Verified by diffing the file list against a stashed baseline: the lists were **identical**, so this session introduced zero new drift. Not fixed, per the brief. |

---

## The independent 100-question benchmark

Graded by Agent D, which made no code change, no graph write, and saw the graph only after
the freeze. Canonical result: `docs/reports/V3_2_FINAL_100_QUESTION_BENCHMARK.jsonl`
(companion prose in the `.md`). I validated the JSONL structurally before reading its
conclusions: 100 rows, `Q1`–`Q100` complete with no duplicates, every verdict in the legal
set, and no row missing evidence, reason or the query that produced it.

| Verdict | Count | Baseline `bb27f3c` | Measured at `d456cce` |
|---|---|---|---|
| `FULLY_ANSWERABLE` | **10** | 5 | 5 |
| `PARTIALLY_ANSWERABLE` | **67** | 29 | 52 |
| `NOT_ANSWERABLE` | **20** | 15 | 8 |
| `MISLEADING` | **3** | 51 | 35 |

| Method | Count |
|---|---|
| `PROBED` | **100** |
| `MANUALLY_EVIDENCE_REVIEWED` | 0 |
| `ESTIMATED_BY_CATEGORY` | **0** |

`FULLY_ANSWERABLE` moved for the first time in the project's history: it had been frozen at
the same five questions across baseline and V3, and is now ten (Q6, Q8, Q13, Q19, Q27, Q29,
Q33, Q43, Q57, Q62).

**Freeze held.** The graph measured 108,777 / 265,294 before and after evaluation, and the
only repository files that changed during it were the two report files. **Agent D found no
CRITICAL defect, so this is not a freeze failure.**

### The three MISLEADING questions, with exact cause

**None of the three is in any of the four areas this session repaired.** Agent D independently
re-verified all four fixes against the frozen graph and they hold.

| Q | Cause |
|---|---|
| **Q10** — metals per Veda | `trapu` (tin) is named in the graph's own stored Sanskrit at **AVS 11.3.8** and has no `:Metal` node — though lead (*sīsa*) was registered from that same passage. `metals_by_veda` returns five metals and silently reports tin as absent. The criterion's first clause, "every metal named in the corpus carries the `Metal` label", is measurably false. A **class-roster** gap, not a count error: the five counts returned are correct. |
| **Q23** — deity communities | No community structure exists anywhere (0 nodes carry community/louvain/partition). The obvious query, `deity_co_occurrence`, instead returns a confident four-row table whose **first and fourth rows are human patrons** — `DARBHYAH-RATHAVITIH` and `VASUKRAH`, both `structure='HUMAN'` in the registry — with no caveat disclosing that the `Devata` class contains humans. A clean zero would have been better than a plausible table. |
| **Q25** — recurring ritual objects | `ritual_objects_recurring` runs over a flat 23-member `:Object` class and returns **chariot (473 mantras) and thunderbolt (275)** as the corpus's most-recurring *ritual objects* — the exact two items the criterion names as disqualifying — while `yūpa` sits at 6 and `iṣṭakā` at 1. Its entire caveat is "Lexical mentions only." There is no ritual-implement subtype. |

Each is a genuine wrong implication and none was reclassified as `PARTIAL` to protect the
number. All three are bounded and named, and none requires reopening the four closed items.

### On the two recorded residuals, and one correction to the evaluator

- **`natural_phenomena_personified` sun = 3** — Agent D judged this a **correct association
  reading, not a misleading count**, and I accept that: all three are genuinely solar, the
  names print beside the integer so the membership is inspectable, and the edge is
  `L1_SOURCE_EXPLICIT`. The residual hazard is the *column name*, not the number.
- **`APTRNAH-SURYAH`** — Agent D reported this "slightly worse than recorded", stating that
  `deities_by_axis` returns SOLAR `individual_deities = 6` "when the resolved count is 5",
  and therefore violates that query's own guarantee that epithet variants are collapsed.
  **I re-measured, and that framing overstates it.** The reported 6 and the resolved count
  are *both* 6: nothing on the solar axis carries an `EPITHET_VARIANT_OF` edge, so resolution
  is a no-op there and no guarantee is broken. The query collapses what the registry asserts,
  and the registry deliberately asserts nothing for this label. The true position is the one
  recorded under Fix A: the count is 6 where a resolved reading would give 5, and it is 6
  because the variant is unproven rather than because the machinery failed. The three
  Surya-labelled rows are visible in the output, so the reader can see the question.

### Three further defects Agent D surfaced (backlog, not verdicts)

1. `rivers_mentioned` carries a caveat stating "There is deliberately no Sarasvati RIVER node"
   while its own rows return `VG:CONCEPT:SARASVATI-RIVER`. The same shape of stale caveat that
   was repaired in `conditions_treated` at V3.1.
2. `varuna_profile` returns `co_deities: []` although Mitra–Varuṇa is the graph's strongest
   pair (lift 13.189, 279 shared passages).
3. The known property-only predicate warning quantified exactly: 2,193 property-no-edge /
   2,406 edge-no-property / 266 both — **45% of the assertion layer is invisible to
   predicate-level traversal**, which depresses Q18, Q51 and Q67.

---

## Final decision

### Engineering readiness

**`VEDAGRAPH_ONTOLOGY_WORLD_CLASS_ENGINEERING_READY` is NOT DECLARED.**

The gate requires `MISLEADING = 0` and the independent measurement is **3**. Every other
condition of the gate is met:

| Gate condition | Met? |
|---|---|
| Final independent benchmark reproducible | **yes** — 100/100 probed, every row carries its query and rows |
| `MISLEADING = 0` | **NO — 3** (Q10, Q23, Q25) |
| 0 CRITICAL adversarial findings | yes |
| Four ontology closure items resolved | yes, all four, independently re-verified |
| Top Devatā counting contract safe | yes — 0 resolved labels map to >1 deity |
| Condition semantics safe | yes — 0 threat/pathogen leakage into the affliction query |
| Attribution contract coherent | yes — all 65 types conform, 0 NULL, 0 undeclared |
| Product/internal separation clean | yes — 0 leakage |
| Projection idempotent | yes |
| Live invariants pass | yes — 0 failing |
| Tests pass | yes — 1,551 passed, 0 failed |

The honest reading: **the session's four named repairs are complete and verified, and the
gate still fails**, because the gate is a property of the whole graph and three defects sit
outside the four areas the brief scoped. Declaring readiness anyway would be exactly the
move this project has been burned by before — a close-out asserting a figure the database
disproves.

### Ontology freeze

```
VEDAGRAPH_ONTOLOGY_FROZEN_FOR_PRODUCT_V1 = false
GRAPH_MODELING_PHASE                     = OPEN, narrowed to three named defects
NEXT_PROJECT_PHASE                       = close Q10, Q23, Q25; re-grade those three
                                           against the frozen benchmark; then freeze and
                                           proceed to FASTAPI_SEARCH_AND_GRAPH_API
```

The freeze is withheld rather than the criterion relaxed. What remains is small, bounded and
fully specified — a `:Metal` node for *trapu* with its AVS 11.3.8 witness; a disclosed or
excluded `structure='HUMAN'` population in the deity-pair queries; and a ritual-implement
distinction (or a truthful caveat and column name) for `ritual_objects_recurring`. None
reopens the four items closed here, and none requires new source acquisition or a new
extraction run.
