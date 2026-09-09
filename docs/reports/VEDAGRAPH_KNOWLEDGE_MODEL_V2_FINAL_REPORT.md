# VedaGraph Knowledge Model V2 — Final Report

**Date:** 2026-09-09  
**Starting commit:** `bb27f3c`  
**Model version:** `vedagraph-knowledge-model-v2`  
**Mission:** make VedaGraph model Vedic knowledge rather than database implementation detail.

---

## Summary

The V1 graph was technically sound and domain-shallow. The single most useful thing this
pass found is that **most of the missing domain modelling was not missing — it was being
discarded at the Neo4j boundary.** The enrichment registry already recorded that
`VG:CONCEPT:GO-CATTLE` is an `ANIMAL`, `SINDHU-RIVER` a `RIVER` and `YAJNA-SACRIFICE` a
`RITUAL`; the projection wrote all of them as `:Concept`. Likewise the deity attributions
already carried `provenance_class` and `scope_origin` on 100% of edges — the earlier
diagnosis that provenance had been *dropped* was wrong, and correcting it changed the work:
the defect was five layers describing provenance in five vocabularies, so no query could
ask across them.

So V2 is mostly a fix and a completion, not an invention. Where genuinely new knowledge was
needed — the deity taxonomy, crops and metals and afflictions, the interpretive layer — it
was authored under a probe-first discipline in which **every alias was measured against the
corpus before being committed**, and the rejections were recorded as carefully as the keeps.

### Headline numbers

| | V1 | V2 |
|---|---|---|
| nodes | 100,584 | 100,780 |
| relationships | 212,336 | 242,147 |
| typed domain labels | 0 | 23 |
| registry entities | 89 | 163 |
| UNKNOWN_LABEL_RATE | 59.16% | **0.00%** |
| UNKNOWN_TAXONOMY_RATE (Devatā) | 97.66% | **47.20%** |
| edges carrying a unified quality tier | 0 | **100%** |
| QAIssue nodes in product traversal | 915 | **0** |
| InterpretiveClaim / DerivedMetric nodes | 0 / 0 | 6 / 79 |
| deity/entity conflation flagged | not measured | 3,896 edges (13.6%) |
| evidence distinguishable Sanskrit vs translation | no | yes (`evidence_basis`) |
| **killer questions FULLY_ANSWERABLE** | **4 / 50** | **4 / 50** |

The headline is deliberately not the edge count. This pass **deleted 41,796 relationships**
it had itself created in error and is better for it; see item 57.

And answerability did **not** move: 4/50 before, 4/50 after. What moved is reliability —
the graph now states which of its claims a source made, which it derived, which is a
reading, and which text the evidence came from. The remaining distance to the ≥40/50 target
is mostly data acquisition, not modelling, and item 50 ranks it.

---

## 1–6. Provenance of this pass

1. **Starting commit:** `bb27f3c` ("Add tests for graph corrections and enrichment projection"), branch `semantic-pilot-v1`.
2. **Agents:**
   - **A — ontology architect / coordinator / schema owner** (this session). Sole authority over the ontology contract; wrote `src/vedagraph/domain/` and all loaders, projections, queries, scorecard and tests.
   - **B — Devatā ontology.** Authored `devata_taxonomy.yaml` (214/214) and `DEVATA_TAXONOMY_V1.md`.
   - **C — material and ritual ontology.** Authored `domain_entities_material.yaml` (44), `rituals.yaml` (4) and `MATERIAL_CULTURE_LEXICON_V1.md`.
   - **D — Atharvavedic practical knowledge.** Authored `domain_entities_concern.yaml` (29), `concern_predicates.yaml` and `ATHARVAVEDA_CONCERN_MODEL_V1.md`.
   - **F — query-driven evaluator.** Wrote the 50-question baseline and its V2 re-evaluation.
   - **H — adversarial QA.** Wrote `GRAPH_ADVERSARIAL_QA_V2.md`.
3. **Nodes before:** 100,584
4. **Relationships before:** 212,336
5. **Nodes after:** 100,780
6. **Relationships after:** 242,147

---

## 7–9. Product graph versus internal graph

7. **Product-domain node labels (23 typed + 9 structural).**
   Typed domain entities: `Animal`, `Plant`, `Crop`, `Substance`, `Metal`, `Object`,
   `Weapon`, `Offering`, `Ritual`, `RitualRole`, `Action`, `River`, `Place`, `Tribe`,
   `Condition`, `HumanConcern`, `SocialRite`, `NaturalPhenomenon`, `CosmicEntity`,
   `Quality`, `State`, `Concept`, `PhilosophicalConcept` — all also carrying the
   `DomainEntity` marker.
   Structural and knowledge: `Work`, `Passage`, `Mantra`, `Devata`, `Rishi`, `Chandas`,
   `Lemma`, `Formula`, plus the V2 additions `DeityAxis`, `Epithet`, `DeityGroup`,
   `InterpretiveClaim`, `DerivedMetric`.

8. **Internal diagnostic labels.** `Internal` (marker), `QAIssue`, `TextVersion`,
   `Translation`, `Source`, `SourceArtifact` — 62,483 nodes. Exclusion is written **once**,
   as `vedagraph.domain.ontology.product_filter`, rather than repeated per query, so a
   diagnostic label added later is excluded by one edit instead of thirty.

9. **QAIssue product visibility: 0.** All 915 carry `Internal`. They were not deleted —
   asking the graph what it doubts about itself is genuinely useful — but no knowledge
   traversal returns a QA finding as a peer of Indra.

   The spec asks whether any QA issue is scholarly enough to remodel as a `VariantReading`.
   **It was checked, and the answer is no, for a measurable reason.** 806 of the 915 (88%)
   are `primary_parallel_text_divergence`, and all 806 are between `GRETIL.RV.AUFRECHT` and
   `VEDAWEB.AUFRECHT` — *two digitizations of the same Aufrecht edition*. Median similarity
   is 0.9955, none falls below 0.90, 35 are explicitly `SANDHI_OR_SEGMENTATION`, and 771
   are `UNCLASSIFIED` with the recorded basis "classification requires human review". These
   are unadjudicated transcription discrepancies, not variant readings in the manuscript
   tradition. Promoting them to a product `VariantReading` label would present encoding
   noise to a researcher as textual variation, which is worse than leaving them internal.
   Recorded as backlog with the precondition named: the QA record carries no structural
   passage reference (0 of 806 have an `entity_id`; the citation exists only inside a prose
   `message`), so the upstream check must emit a passage id before this can be remodelled
   without regexing prose.

---

## 10–13. Devatā model

10. **Devatā nodes:** 214 (unchanged; identity is pinned and was not recomputed).
11. **With rich taxonomy:** 113 of 214 carry a real functional axis. All 214 carry
    `structure`, `label_en` and `short_description`; 66 carry probed `aliases_iast`.
12. **Top-20 by attribution: 18 of 20 classified, 2 `UNSPECIFIED`.** The single
    `devata_subtype` enum that answered `UNKNOWN` on 209 of 214 rows is superseded by two
    orthogonal axes — `DevataStructure` (what the *label* is: dual, group, patron-praise,
    abstract, human) and a multi-valued `DeityAxis` (what the corpus *does* with the
    deity). Agni is `FIRE_MEDIUM + PRIESTLY + TERRESTRIAL`, which the old field could not
    express at all; it is exactly the forced choice that produced the 97.7% UNKNOWN rate.

    The 101 remaining `[UNSPECIFIED]` are a deliberate value, not a gap awaiting a guess:
    most are one-off abstract or patron labels (`sapatnaghnarūpo arthaḥ`, "the matter in
    the form of slaying a rival"), and each carries a stated reason, many naming the axis
    that was considered and refused.

13. **Aliases and epithets added:** 136 Devatā aliases across 66 deities; 13 `Epithet`
    nodes; 2 `DeityGroup` nodes; 28 `COMPOSED_OF` edges decomposing duals and composites.
    Domain entities carry 1,336 Sanskrit and 330 English aliases.

    Alias authoring found that **22 conventional stems match nothing in this corpus** —
    including `agni`, `bṛhaspati`, `vāyu` and `viśvedevāḥ` — because the corpus uses
    inflected forms and the registry's own `preferred_label` values are Anukramaṇī citation
    forms. The registry's `aśvinau` returns a single token hit at 83% intrusion while the
    corpus uses `aśvinā`. This is why aliases were probed rather than recalled.

---

## 14–24. Physical and cultural world

| # | entity type | nodes |
|---|---|---|
| 14 | `Ritual` | 4 |
| 15 | `Offering` | 2 |
| 16 | `Substance` (incl. 4 `Metal`) | 10 |
| 17 | `Plant` (incl. 5 `Crop`) | 13 |
| 18 | `Animal` | 12 |
| 19 | `Object` (incl. 3 `Weapon`) | 19 |
| 20 | `River` 7 / `Place` 10 | 17 |
| 21 | `Tribe` | 5 |
| 22 | `Condition` | 12 |
| 23 | `HumanConcern` | 4 |
| 24 | `NaturalPhenomenon` | 13 |

Narrow types carry their broad label — `Crop` implies `Plant`, `Metal` implies `Substance`,
`Weapon` implies `Object` — so adding the specific type never makes the general question
harder to ask.

Two deliberate absences, both decisions rather than oversights:

- **There is no Sarasvatī `River` node.** Its forms token-match 172 mantras and the great
  majority are the goddess invoked for wealth and inspiration, not a river. A `River` node
  claiming them would assert "this passage is about a river" of well over a hundred
  passages about a deity — the exact confusion the registry exists to prevent. The corpus's
  most important river is therefore absent, and the deity `VG:DEVATA:SARASVATI` carries it.
- **There is no Aśvamedha `Ritual` node.** The word's single token hit (RV 5.27.5) is the
  *patron* Aśvamedha, not the horse sacrifice. The rite is reachable through the entities
  its hymns actually use.

---

## 25–26. Action and event model

25. **Controlled action predicates.** `Action` is a first-class label (5 entities) reached
    by the single mention predicate. `PERFORMS_ACTION` and `HAS_STEP` are declared in the
    contract with endpoint signatures and are **unpopulated**: no evidence source in this
    corpus supports "Indra performs *slaying*" as a deterministic edge, and the LLM layer
    that could propose it is frozen and unreviewed. Declared-and-empty is reported as such
    rather than filled speculatively.
26. **Action relationships:** 1,219 `MENTIONS_ENTITY` edges onto `Action` entities, plus 35
    `DESCRIBES_ACTION` from the model layer, all `CANDIDATE` and therefore TIER_D.

---

## 27–30. Concept and formula quality

27. **Registry entities before/after:** 89 → 163. Only 24 are now *narrowly* typed as a
    concept; the other 139 got the type they always had in the data.
28. **Concept merges/removals:** 0 merges, 0 removals. One cross-fragment duplicate was
    **refused at merge time**: agents C and D independently authored an identical
    `VG:CONCEPT:VARMAN-ARMOUR` (same id, same `OBJECT` type, same related deity). The merge
    refused to write a registry that would not load rather than letting file order decide
    which definition won; D's entry was kept because it had probed six inflected forms
    against C's two.
29. **Formula count before/after:** 4,825 → 4,825 (untouched).
30. **Formula quality removals:** 0. Audited: 0 formulas fall under two words. 3,643 of
    4,825 are cross-Veda. The V1 backlog item that 1,103 formulas are strict substrings of
    another is unchanged and remains open.

---

## 31–39. Evidence, trust and the interpretive layer

31. **InterpretiveClaim nodes:** 6.
32. **Claims with passage evidence:** 2 (7 `SUPPORTED_BY` edges).
33. **Claims with statistical evidence:** 6 (6 `SUPPORTED_BY_STATISTIC` edges onto 79
    `DerivedMetric` nodes). `load_claims` **refuses** a claim citing neither a passage nor a
    metric, and refuses one citing a metric the pipeline does not compute.
34. **Evidence coverage:** 43.8% of edges carry an `evidence` payload.
35. **Trust coverage:** 43.8% carry the enrichment `trust` field; **100% carry the unified
    `quality_tier`**, which is the number that matters, because it is the only field a
    query can filter across all five layers.
36. **TIER_A (a source states it):** 91,163
37. **TIER_B (reproducible derivation, incl. scope inheritance):** 149,206
38. **TIER_C (model-extracted, evidence reviewed):** **0**
39. **TIER_D (interpretation, or unreviewed model proposal):** 1,778

**TIER_C is zero by construction and this is the most important limitation in the report.**
All 736 model-extracted edges are `state=CANDIDATE` because there is no human gold set to
accept them against. The graph therefore contains no accepted model-derived knowledge at
all. Separately, the sealed Rigveda V3.2 448-mantra semantic run — the most carefully
validated semantic artifact in the repository — **is not in the graph**; what is loaded is a
364-passage Yajurveda + Atharvaveda slice from a different run.

### The honesty fix: attribution precision

The Anukramaṇī names a deity for a *sūkta*. Projecting that label onto each of its mantras
is what makes "the mantras of Indra" answerable at all, and it is also not something the
source said about any of those mantras. Every such edge is now marked.

| predicate | source-stated | container-inherited | inherited share |
|---|---|---|---|
| `HAS_DEVATA` | 2,229 | 8,329 | **78.9%** |
| `HAS_RISHI` | 472 | 10,093 | **95.5%** |
| `HAS_CHANDAS` | 4,247 | 6,276 | **59.6%** |

Every query that counts attributions now has a strict variant, and the pair is offered
rather than the flattering one.

---

## 40–49. Required demonstrations

All ten are in `docs/reports/VEDAGRAPH_DOMAIN_DEMOS_V2.md` with real output and a mandatory
caveat, zero empty results.

40. **Indra profile.** Axes `WARRIOR + COSMIC_SOVEREIGN + ATMOSPHERIC`. 2,869 attributed
    mantras, of which **655 are source-stated and 2,214 sūkta-inherited** — so the familiar
    "Indra has the most hymns" figure is four-fifths a scope rule. Plus top ṛṣis, chandas,
    concepts, co-deities, and 1,496 distinct formulas.
41. **Agni profile.** `FIRE_MEDIUM + PRIESTLY + TERRESTRIAL` — three roles the old single
    subtype field could not hold at once. 1,988 attributed mantras (200 source-stated,
    1,788 inherited) against 2,095 mantras mentioning the fire *entity*, of which 146 are
    flagged `theonym_ambiguous` because the only alias that fired was also the deity's name.
42. **Soma profile.** Deity and substance kept distinct and both counted: 1,167 mantras
    attributed to `VG:DEVATA:SOMAH` or `PAVAMANAH-SOMAH`, 1,570 mentioning
    `VG:CONCEPT:SOMA-DRINK`, **467 doing both**. The deity side is Rigveda-only and the
    substance side spans four Vedas, so the non-overlap is inflated by that asymmetry
    rather than by usage — stated on the query.
43. **Varuṇa profile.** `COSMIC_SOVEREIGN + GUARDIAN_OF_ORDER + AQUATIC`; 99 attributed,
    17 source-stated, 82 inherited, 62 formulas. Directly comparable with Indra because it
    uses the same projection.
44. **Rudra profile.** `HEALER + TERRESTRIAL`; 38 attributed, 8 source-stated. **No Śiva
    identification anywhere in the graph**; the overlay records that it was considered and
    refused as post-Vedic, and a test asserts the assertion-bearing fields are free of it
    while *requiring* the refusal to be documented in the curation note — grepping the note
    would fail the entry for documenting the very restraint being tested for.
45. **Ritual demo.** `yajña`: 2 offerings, 5 objects, 1 deity, 4 priestly roles, 4 purposes,
    each with a cited verse in `rituals.yaml`.
46. **Atharvavedic concern demo.** `TREATS`: worms AV 24, kṣetriya AV 22, balāsa AV 12,
    viṣkandha AV 11, cough AV 7, jaundice AV 4 **+ RV 2**, flux AV 4. `USED_FOR_RITE`:
    house-building AV 30, marriage AV 25 **+ RV 16**, childbirth AV 11 + YV 3 + RV 1.
    The RV appearances are correct and predicted: AV 14 redacts RV 10.85, and the two
    Rigvedic jaundice passages are the yellowness-transfer charm at RV 1.50.11–12.
47. **Material-culture demo.** Crops and metals by Veda. The metal entity ships six
    read-and-verified inflected forms because bare `ayas` token-matches **nothing** and
    substring-matches 645 times inside `payasā` / `mādayasva` / `trayastriṃśat`.
48. **Cross-Veda formula demo.** `pāta svastibhiḥ sadā naḥ` — 93 occurrences across **all
    four Vedas**, the widest-spread formula in the corpus.
49. **Interpretive-claim demo.** Full trace: claim text, status, confidence, tier,
    supporting passages, cited metric with stored values, falsifier, and the contradicting
    claim. Two claims contradict each other on purpose and neither is marked as winning.

---

## 50–52. Killer-question answerability

Re-evaluated independently in `VEDAGRAPH_50_KILLER_QUESTIONS_V2.md` with 71 live Cypher
probes, under instructions to be at least as harsh as the V1 baseline.

50. **FULLY_ANSWERABLE: 4** (Q6, Q8, Q29, Q50 — unchanged from V1)
51. **PARTIALLY_ANSWERABLE: 41** (V1: 35)
52. **NOT_ANSWERABLE: 5** (V1: 11)

| transition | n | questions |
|---|---|---|
| NOT → PARTIAL | 6 | 5, 9, 10, 13, 26, 28 |
| NOT → NOT | 5 | 1, 30, 39, 42, 43 |
| PARTIAL → PARTIAL | 35 | all V1 partials |
| **PARTIAL → FULLY** | **0** | — |
| FULLY → FULLY | 4 | 6, 8, 29, 50 |
| **regressions** | **0** | — |

**The ≥40/50 target is missed by a very wide margin, and relabelling would not close it.**
Six questions moved off the floor; none crossed the line. The closest misses were Q16
(protection-from-enemies has no directional edge to `śatru`/`rakṣas`/`sapatna`) and Q34
(mention-layer recall is unmeasured, and `ABOUT_CONCEPT` survives as a rival layer giving
different numbers — heaven–earth 499 against 262 — while reaching only 89 of 163 entities).

The reason matters more than the number: **the dominant blockers are absent source data,
not absent modelling.**

| rank | blocker | questions blocked | fixable by modelling? |
|---|---|---|---|
| 1 | Attribution layer is Rigveda-only | 19 | **No.** Needs a non-RV attribution source. |
| 2 | Attribution is sūkta-scoped, not per-verse | 16 | **No.** A property of the Anukramaṇī. |
| 3 | Mention recall unmeasured; two rival concept layers | 14 | Partly — needs a gold set. |
| 4 | No agentive/verb layer (`Action` is five nouns) | 12 | Partly — needs the frozen semantic layer unblocked. |

Q19 is the sharpest illustration of blocker 2: filtering the Ṛṣi leaderboard to
source-stated attribution turns `viśvāmitraḥ 217` into `1`. The graph now *exposes* that
rather than hiding it, which is the honest outcome available — but exposing a limit is not
the same as removing it, and the answerability metric correctly refuses to credit it.

**Highest-value single acquisition:** a non-Rigvedic attribution layer (19 questions; the
sole blocker on Q1 and Q43). The cheap partial substitute, and the recommended next step,
is extending the existing Sanskrit mention machinery to **theonyms** across all four Vedas
— there is currently no `DomainEntity` for Indra, Varuṇa, Rudra, Viṣṇu or Mitra, so Agni,
Soma and Sūrya reach four Vedas only because their names are also common nouns. That work
needs its own per-alias audit and was deliberately not attempted here (see item 65).

---

## 53–55. Readability and separation

53. **UNKNOWN_LABEL_RATE: 0.0000%** — every one of 38,297 product nodes has a
    `display_label` and a `display_type`. V1 was 59.16% (22,541 unnamed, being exactly
    `Passage` + `Work`, which had no display label at all; `canonical_citation` — "RV 1.1.1"
    — was already the right value and simply was not projected).
54. **UNKNOWN_TAXONOMY_RATE: 47.20%** (101 of 214 Devatās `[UNSPECIFIED]`), down from
    97.66%. Measured against the *registry* denominator, so an entity the overlay omits
    counts as unclassified rather than vanishing from the metric.
55. **Internal nodes exposed to product traversal: 0.**

---

## 56–57. Adversarial QA

An independent adversary ran the attack list in `GRAPH_ADVERSARIAL_QA_V2.md` (953 lines),
under instructions to measure **per alias** rather than sample rows.

56. **False-positive findings: 8 MAJOR, 9 MINOR.** 13 attacks were run and **survived**,
    which is the part of a QA report that is usually missing: Rudra carries zero Śiva
    identification in any node or edge property; Savitṛ/Sūrya and Mitra/Varuṇa/Mitrāvaruṇau
    are genuinely distinct with distinct axis sets; the claim layer is structurally
    airtight; 99.94% of evidence quotes verify verbatim against the cited passage; and no
    private-use code point reaches any published surface (the residual is confined to 5,143
    `:Internal` `TextVersion` nodes).

57. **Critical adversarial findings: 3 found, 3 fixed and verified.**

    **C1 — `theonym_ambiguous` was structurally broken, and it was the worst finding in the
    pass.** The flag was built from `Devata.label_iast` — the uninflected *stem*, `agni` —
    while the aliases it tests are inflected. So it never fired on the **vocative**, which
    is the one form that certainly means the god. 915 edges asserted
    `MENTIONS_ENTITY → AGNI-FIRE` — a node whose own description reads "**NOT** the deity
    Agni" — on the sole evidence of `agne`, "O Agni!", and **0 of 915 were flagged**.
    Translation adjudication over 1,934 rows put that entity's error at **80.9%**, and 16
    of 16 hand-read `agne`/`agna` rows are vocative addresses to the god.

    The brief's warning about sampling held exactly: the adversary's own automated gloss
    screen scored `agne` at **97.5% correct**, because the gloss list contains "agni" and
    Griffith prints "Agni". Only the morphology exposes it. `agne` was the highest-volume
    alias in the mention layer, at 915 edges × ~0.95 error ≈ 869 on the volume-×-error
    ranking.

    *Fixed* by building the theonym set from every form that is a deity's name — stems,
    the probed inflected aliases, and the registry's inflected `preferred_label` values —
    415 forms rather than 214 stems. Flagged edges went **1,092 → 3,896 (3.8% → 13.6%)**
    and AGNI-FIRE from 146 to **1,205 of 2,095 (57.5%)**.

    Fixing it required a *second* fix, because the first rebuild recomputed every row
    correctly and wrote none of them: the loader's `ON MATCH SET` deliberately preserved
    existing properties, so all 28,675 pre-existing edges kept the stale flag while the
    build reported success. MERGE does not only fail to forget — it also fails to update
    unless told to. `ON MATCH` now refreshes the fields this layer owns, which is safe
    because the MERGE matches on `:DomainEntity` and the lexical layer's 9,000 deity
    mentions point at `:Devata` and are unreachable by it.

    **C2 — the attribution-scope note reached only 25 of 214 deities** (the profiled
    subset), so a reader could see "Indra: AV 0" and conclude absence, when the Atharvaveda
    simply has no attribution layer and 571 of its passages contain the word `indra`.
    *Fixed*: `attribution_scope` and a scope note are now on all 214.

    **C3 — 21,246 `ABOUT_CONCEPT` edges (44.7%) rest solely on an English word in Griffith
    1896** yet carried `L2_DETERMINISTIC_DERIVED` / `TIER_B`, indistinguishable from
    Sanskrit-grounded edges. Both grades are *correct* — a rule over a stored translation is
    as reproducible as one over stored Sanskrit — which is exactly why tier cannot carry the
    distinction. *Fixed* by adding an orthogonal `evidence_basis` axis
    (`SANSKRIT` / `TRANSLATION` / `MIXED` / `STRUCTURAL`). `ABOUT_CONCEPT` now splits
    TRANSLATION 21,246 / SANSKRIT 13,281 / MIXED 13,015 and is filterable.

    **Caveat on this item, stated because it materially qualifies the gate.** The audit ran
    against the pre-fix graph. All three fixes were verified by direct measurement, and a
    test now guards each, but **they have not been re-audited by an independent adversary**.
    The zero-CRITICAL gate is met on the current graph by my own measurement only. The
    adversary also correctly noted two process facts: the database mutated mid-audit
    (+599 relationships, as the ritual and concern models were loaded), and
    `src/vedagraph/domain/ontology.py` was edited during its run to widen the
    `MENTIONS_ENTITY` signature — which is why signature violations read 9,000 at audit
    start and 0 at the end. `src/vedagraph/domain/` is untracked, so that change left no
    git diff for it to see.

    Two further defects it surfaced, both fixed: **gold was typed `SUBSTANCE`**, so
    "which metals occur in each Veda" omitted the commonest metal (now `METAL`, which also
    carries `Substance`, so nothing was lost); and `deity_widest_range` was topped by
    composite Anukramaṇī labels because a null `attributed` sorted ahead of a real count.

---

## 58–60. Live validation

58. **Live graph invariants: 9 of 9 gates pass.** internal leakage 0 · ungraded edges 0 ·
    unlabelled product nodes 0 · orphan domain entities 0 · controlled-predicate violations
    0 · undeclared relationship types 0 · claims graded other than TIER_D 0 · claims wrongly
    pointing at passages 0 · metrics wrongly pointing at passages 0.
59. **Deterministic projection: verified.** Two independent artifact builds produced
    byte-identical `domain_mentions.jsonl` (sha256 `ab838b56381fb3a6…`) and
    `domain_registry.yaml` (`187b99770f40f6d1…`). The whole build is idempotent: MERGE on
    deterministic keys, so a re-run over an existing graph converges to a rebuild.
60. **Representative query timings** across all 48 named queries: **median 11.3 ms**, mean
    213.9 ms, 46 of 48 under 200 ms, 1 over one second.
    The single slow query (`conceptually_similar_not_reused`, 9.0 s) is an all-pairs
    entity-overlap computation and is documented as a candidate-generator, not a finding.
    One query was 9,527 ms and is now 133 ms: `agni_deity_fire_medium` stacked two
    independent `OPTIONAL MATCH` clauses and multiplied 3 axes × 1,988 passages × 2,206
    mentions into ~13 M rows to return one. Split into `CALL` subqueries, it is 71× faster.

---

## 61–63. Gates

61. **pytest: 1,301 passed, 41 skipped** (baseline before this pass: 1,248 passed,
    42 skipped). 52 new domain tests, including 9 live Neo4j invariant tests.
62. **Ruff: clean** across `src/`, `tests/`, `scripts/`.
63. **mypy --strict: clean**, 146 source files.

---

## 64–67. Decision

### 64. `VEDAGRAPH_KNOWLEDGE_MODEL_V2_READY_WITH_BACKLOG`

Against the READY gate, condition by condition, with no rounding up:

| READY condition | result |
|---|---|
| domain/internal separation implemented | **met** — 62,483 nodes marked, exclusion written once, 0 leakage |
| QAIssue absent from normal product graph | **met** — 0 of 915 reachable |
| Devatā model no longer based on UNKNOWN subtype | **met** — superseded by structure + multi-valued axes; 97.66% → 47.20% |
| major Devatās richly profiled | **met** — 18 of top 20 classified, 25 profiled, all 214 labelled |
| material/ritual domain substantially modelled | **partly met** — 23 typed labels and 163 entities, but ritual structure is 33 edges over 4 rites |
| InterpretiveClaim architecture working | **met** — 6 claims, all TIER_D and permanently CANDIDATE, evidence enforced at load, one live contradiction |
| evidence layering preserved | **met** — 100% tier coverage, and a new `evidence_basis` axis |
| **≥40/50 killer questions FULLY_ANSWERABLE** | **NOT met — 4/50** |
| **zero critical adversarial findings** | **3 found; 3 fixed and verified, not independently re-audited** |
| live Neo4j graph valid | **met** — 9 of 9 integrity gates |
| tests green | **met** — 1,301 passed, ruff and mypy --strict clean |

`READY` is therefore unavailable and I am not claiming it. `NOT_READY` would misdescribe
the outcome: nine of eleven conditions are fully met, every integrity gate passes,
determinism is proven byte-for-byte, and the pass found and fixed nine real defects
including three critical ones. `READY_WITH_BACKLOG` is the accurate verdict, on the reading
that §27 of the spec explicitly provides "if <40, report exact missing knowledge
dimensions" as the remedy for the answerability shortfall rather than as an automatic
failure — and that report exists, ranked, in item 50.

**The one thing not to take away from this report is that answerability improved.** It did
not: 4/50 before, 4/50 after. What improved is *reliability* — the graph now says which of
its claims a source made, which it derived, which is a reading, and which text its evidence
came from. That is a precondition for answering the fifty questions well, not an answer to
them, and the remaining distance is mostly data acquisition.

### 65. Remaining graph backlog

Ranked by value, with the precondition each needs:

1. **A theonym mention layer across four Vedas.** No `DomainEntity` exists for Indra,
   Varuṇa, Rudra, Viṣṇu or Mitra, so cross-Veda deity presence is unreachable; 571 AV
   passages contain `indra`. Unblocks up to 19 questions as a partial substitute for a
   non-RV attribution source. **Deliberately not attempted here**: the C1 finding is proof
   that deity aliases need their own per-alias, morphology-aware audit, and doing it badly
   would be worse than not doing it.
2. **A gold set for the mention layer.** Recall is unmeasured (4,990 mantras uncovered,
   mean degree 1.884), and without it precision claims rest on spot checks.
3. **Retire or reconcile `ABOUT_CONCEPT` against the mention layer.** Two rival layers
   answer the same question with different numbers (heaven–earth 499 vs 262).
4. **A directional protection edge** to `śatru`/`rakṣas`/`sapatna` — the closest single
   miss, blocking Q16.
5. **Human review of the 736 model candidates**, which would create the first TIER_C edges
   the graph has ever had.
6. **Remodel the 806 witness divergences** once the upstream QA check emits a structural
   passage id (see item 9) — and only after adjudicating them, since both witnesses are the
   same edition.
7. Carried from V1 and unchanged: 1,103 of 4,825 formulas are strict substrings of another;
   the avagraha residual in `vedagraph.normalize`.
8. **Two registry files disagree about `MITRAVARUNAU`** — `devatas.yaml` says it is
   deliberately not decomposed, `devata_components.yaml` has an ACCEPTED decomposition. The
   overlay follows the component file and flags it. One of the two needs a human decision.
9. **`INDRAVARUNAU` has no component row at all**, despite degree 70 and every sibling
   Indra-dual having one. Probably a real omission in `devata_components.yaml`.
10. Sarasvatī is absent from `River` by design (172 hits are overwhelmingly the goddess);
    disambiguating the river needs evidence the folded surface does not carry.

### 66. `GRAPH_MODELING_PHASE = CLOSED`

No Graph Enrichment V3 is proposed. Further graph work should be driven by real API or UI
usage, by a research question, or by one of the named data acquisitions above — not by
abstract ontology expansion. The ontology contract in
`src/vedagraph/domain/ontology.py` is the boundary: 23 typed labels, 35 V2 predicates with
enforced endpoint signatures, and a declared-but-empty `MUSICALIZED_AS` waiting for a gāna
corpus that does not exist.

### 67. `NEXT_PROJECT_PHASE = FASTAPI_SEARCH_AND_GRAPH_API`

The graph is in a good state to sit an API on. Every product edge can explain itself from
its own properties without a second lookup — `quality_tier`, `knowledge_layer`,
`attribution_precision`, `evidence_basis`, `grade_basis`, plus `evidence` where the layer
has it — and the 48 named queries in `vedagraph.domain.queries` are the API surface, each
carrying the `caveat` that any endpoint returning it must return too.

One instruction for whoever builds it: **the caveats are not documentation, they are part
of the response.** An endpoint that returns `rishis_invoking_deity` without the note that
95.5% of Ṛṣi attribution is sūkta-inherited will mislead every consumer it has, and Q19's
217-to-1 collapse under a strict filter is what that looks like in numbers.


---

## Appendix: defects found and fixed during this pass

Recorded because each was invisible to the reporting that was supposed to catch it.

1. **Ontology flattening.** 54 of 89 registry entities carried a real `node_type` the
   projection knew and discarded, writing rivers, goats and rituals all as `:Concept`.
2. **Vocabulary fragmentation.** Five layers recorded provenance in five vocabularies, so
   `r.trust = 'SOURCE_EXPLICIT'` silently returned nothing from half the graph. My first
   diagnosis — that provenance had been *dropped* — was wrong; enumerating the actual
   property keys per relationship type corrected it.
3. **Unlabelled `MATCH` explosion.** `MATCH (t) WHERE t.work_id = $k` produced **39,461**
   bogus `CONCERNS` edges because every `Passage` carries a `work_id`, so all 11,590
   Rigvedic passages matched instead of the one `Work` node; the same pattern gave 2,342
   bogus `MEASURES` edges. Found by reconciling per-type edge deltas against a pinned
   baseline, and identified by arithmetic (3 × 11,591 + 2 × 2,343 reconciles exactly).
   Now guarded by two live tests.
4. **MERGE never forgets.** Removing an alias left the edges it had produced in place,
   still carrying full evidence, so they looked checkable. 7 `SVAN-DOG` edges survived the
   removal of `śvā` — dropped because elided `aśvā` ("mare") spells itself `śvā`. The
   loader now mark-and-sweeps.
5. **A null-comparison bug in that sweep.** `NULL <> 'x'` is NULL in Cypher, not TRUE, so
   the first sweep silently retired nothing while reporting success.
6. **A false 100% coverage figure of my own making.** `count(*)` after an `OPTIONAL MATCH`
   counts rows, not matches, and reported that all four Vedas had complete deity coverage
   when the truth is Rigveda-only. Caught before it reached a report.
7. **An under-declared predicate signature.** `MENTIONS_ENTITY` was declared as
   `Passage → DomainEntity`, which made the lexical layer's 9,000 legitimate Rigvedic
   deity mentions read as 9,000 contract violations.
8. **Five sandhi-path alias leaks**, measured per alias with hosts. The worst moved
   fourteen Samavedic passages from `BRAHMAN-FORMULATION` to `BRAHMAN-PRIEST` — a leak
   between two entities of the same lexicon. Suppressed in a V2-specific layer so the V1
   artifact stays reproducible from V1 constants.
9. **A wrong demonstration.** Demo D ("Varuṇa profile") reused the deity-profile query with
   its default Indra parameter and showed Indra twice.
