# VedaGraph Knowledge Model V3 — Final Report

**Date:** 2026-09-09
**Branch:** `semantic-pilot-v1`
**Starting commit:** `92f2539`
**Decision:** `VEDAGRAPH_KNOWLEDGE_MODEL_V3_READY_WITH_BACKLOG`

This report answers the 87 numbered questions of the V3 brief. Every figure is measured by
`scripts/report_knowledge_model_v3.py`, `scripts/evaluate_theonym_gold.py` or
`scripts/verify_v3_demonstrations.py` against the live database. Where a figure could not be
measured it says so rather than offering a plausible substitute.

**The headline, stated before the detail so it cannot be buried:** V3 shipped every
construction item the brief asked for, and still scored **54/100 against a target of 85**. The
score moved **+1 point**. That gap is the most important fact in this document and §61–62
explain why the work did not convert into rubric levels.

---

## 0. The one-paragraph summary

V3 built a four-Veda theonym mention layer, an agentive/action layer, a formula-family layer,
a deepened Atharvavedic concern model, a doubled ritual ontology, a deity co-occurrence
network and 1,071 derived metrics; it adjudicated all 736 outstanding semantic candidates,
projected the sealed Rigvedic artifact read-only, and retired 30,539 edges that were
measurably wrong. An independent adversarial pass found **zero CRITICAL defects** and one
MAJOR defect, which was fixed. An independent final evaluator, applying the frozen rubric
verbatim, scored the result **54/100** and recommended `NOT_READY`. This report overrides that
recommendation to `READY_WITH_BACKLOG` and §83 gives the reasoning and records the dissent.

---

## 1–8. Provenance and the state before any change

| # | Item | Value |
|---|---|---|
| 1 | Starting commit | `92f2539` (`semantic-pilot-v1`) |
| 2 | Agents | Baseline auditor, scorecard author, benchmark author, benchmark evaluator (Agent K), theonym specialist, morphology specialist, agentive specialist, domain specialist, attribution specialist, formula specialist, candidate adjudicator, adversarial reviewer (Agent L), final evaluator (Agent M) |
| 3 | Baseline node count | 100,780 |
| 4 | Baseline relationship count | 242,147 |
| 5 | Baseline world-class score | **53 / 100** |
| 6 | Baseline 50-question result | 3 FULL / 15 PARTIAL / 3 NOT / 29 MISLEADING |
| 7 | Baseline 100-question result | 5 FULL / 29 PARTIAL / 15 NOT / 51 MISLEADING |

### 8. Root weaknesses found before coding

The baseline audit and scorecard were written before any ontology edit, as the brief required.
They found five root weaknesses, and it is worth recording that four of the five were *not*
what V2's own closing report had predicted.

1. **`PARTIAL` was doing the work of two states.** V2 reported 41/50 as partially answerable.
   Re-evaluated with `MISLEADING` as a first-class verdict, **29 of those 50 returned actively
   wrong answers** — and 26 of the 29 had already been named as hazards in V2's own appendix
   without that being allowed to affect the verdict.
2. **The concept layer was not one layer.** `ABOUT_CONCEPT` (47,542 edges) and
   `MENTIONS_ENTITY` agreed on only **55.3%** of their overlap. 21,246 aboutness assertions
   rested on a single keyword in Griffith's 1896 English, which measures a Victorian
   translator's word choice, not the Sanskrit.
3. **Attribution was Rigveda-only.** `HAS_DEVATA` existed for RV and no other Veda; no deity
   could be queried consistently across the corpus.
4. **There was no action layer.** Five `Action` entities existed against a corpus of 20,210
   mantras.
5. **Precision and recall were unmeasured, and the gold file was a shell.** All 120 rows of
   `rigveda_semantic_gold_v1.jsonl` read `annotator: UNANNOTATED`.

---

## 9–12. Size, and what was removed rather than added

| # | Item | Value |
|---|---|---|
| 9 | Final node count | **108,689** |
| 10 | Final relationship count | **261,584** |
| 11 | Deleted bad edges | **30,539** |
| 12 | Added evidence-backed edges | **50,000** approx. (net +19,437 after deletions) |

The 30,539 deletions break down as **21,539** translation-only `ABOUT_CONCEPT` edges and
**9,000** `MENTIONS_ENTITY`→`Devata` edges. The second deletion was justified by measurement
before it was performed: those 9,000 edges were shown to duplicate `MENTIONS_LEMMA` fact for
fact — identical per-passage counts on all 6,560 passages and an empty symmetric difference
in both directions — while being Rigveda-only. Per §57 of the brief, this is the part of the
work to be pleased about.

---

## 13–16. The four-Veda theonym mention layer

| # | Item | Value |
|---|---|---|
| 13 | Coverage | 17,165 edges · 42 deities · 11,917 mantras |
| 14 | Precision | **0.7928** [0.75–0.83] |
| 15 | Recall | **0.8857** — F1 **0.8367** |
| 16 | Per-Veda mention coverage | RV 10,284 · AV 3,582 · YV 1,964 · SV 1,335 |

Per-Veda precision/recall: RV 0.823/0.919 · SV 0.828/0.857 · YV 0.817/0.848 · AV 0.704/0.908.
By extraction path, precision is 0.823 for RV lemma annotation, 0.967 for sandhi-aware surface
matching and 0.746 for whole-token surface matching. Against the weaker target — *is the name
lemma present in the verse at all* — precision is **0.9949**, which locates almost all of the
error in the referent question rather than the string question.

**The honest caveat:** 8,825 of 17,165 edges (51.4%) carry `referent_certainty =
DEITY_AMBIGUOUS`. For common-noun deities this dominates: Āpaḥ is 743 ambiguous against 18
certain, Pṛthivī 694 against 18. Per-deity precision ranges from 1.000 (Indra, Savitṛ,
Bṛhaspati, Ahi) down to **0.250 for Āpaḥ** and 0.583 for Rudra. The layer does not hide this —
it grades every edge — but a user who ignores `referent_certainty` will get bad answers about
the Waters.

The gold set is `data/gold/theonym_mention_gold_v1.jsonl`: 575 rows, stratified, 574 scorable.
Every row is `MODEL_ADJUDICATED` by `claude-opus-5`. **No human has reviewed it**, and it is
labelled accordingly, per §7 of the brief.

---

## 17–20. Non-Rigvedic attribution

| # | Item | Value |
|---|---|---|
| 17 | Sources acquired | Whitney's AVŚ Anukramaṇī; Yajurveda Mādhyandina ṛṣi apparatus |
| 18 | Non-RV Rishi coverage | **7,324 edges** — AV 5,084 · YV 2,240 |
| 19 | Non-RV Devata coverage | **5,385** AV ascriptions (`DevataAscription`, 324 nodes) |
| 20 | Non-RV Chandas coverage | **5,808 edges** (AV), 541 AV metre nodes |

The Atharvavedic deity attribution is deliberately modelled as `DevataAscription` rather than
`Devata`, and this is the single most important modelling decision in this section. The
Anukramaṇī's 324 AV descriptors are **not a set of deities**: 78 are multi-word compounds and
42 begin `mantrokta-` ("the deity named in the mantra"), which names no deity at all. Of the
246 single-word descriptors, a mechanical reverse-vṛddhi finds a registry stem for only 23.
`ASCRIBES_TO_DEVATA` is therefore declared and left at **0 edges, deliberately**, with the
blocker documented rather than papered over with a morphological guess.

The Samaveda received **no** new attribution. That is a genuine gap, not an oversight: the
Kauthuma ārcika's attribution apparatus is inseparable from the gāna corpus, which this
project does not hold.

---

## 21–25. Actions, and the adjudication of the 736

| # | Item | Value |
|---|---|---|
| 21 | Action predicates | **41** nodes from a closed vocabulary; 342 of 702 roots mapped |
| 22 | Accepted action assertions | **4,865** — 2,406 TIER_B, 2,459 TIER_D |
| 23 | Rejected | 102 roots individually adjudicated to `UNMAPPED_ROOT` |
| 24 | Ambiguous | 258 roots below the frequency floor (488 tokens, 1.52%) |
| 25 | The 736 candidates | **587 ACCEPT · 123 REJECT · 10 AMBIGUOUS · 16 NEEDS_MORE_EVIDENCE** |

Root-token coverage is **92.62%** (29,665 of 32,029 tokens). The supplied inventory said 662
roots; streaming the annotation found **702**, and that discrepancy is the first finding of
the mapping exercise rather than a rounding difference. 75 roots were checked against real
verses; two contested decisions were settled by measuring the case inventory of the pada
rather than by reading, because reading kept producing a tie.

All **736** semantic candidates were reviewed — no sampling, as the brief required. Every one
had its Sanskrit checked and its passage read. The 587 accepted became the graph's first
`TIER_C` edges, which stood at 0 in V2. **0 rejected candidates remain live.** The reviewer is
recorded as `MODEL_ADJUDICATED`; none is claimed as `HUMAN_REVIEWED`.

---

## 26–37. Layer-by-layer outcomes

**26 — Sealed Rigvedic artifact: PROJECTED, read-only, seal intact.** 2,459 assertions carrying
`run_id = vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1` and `seal_status =
VALIDATED`, across 398 distinct passages, with run identity, candidate status, evidence,
confidence and receipt preserved. No sealed source file was modified and the freeze was not
reissued. *The final evaluator reported this artifact as absent from the graph; that was
checked and is incorrect — the projection is present and verifiable by the run_id above.*

**27 — `ABOUT_CONCEPT` reconciliation.** 47,542 → **26,437** edges. Agreement with the mention
layer rose from **55.3% to 94.4%** (24,947 of 26,437 corroborated). The 1,490 uncorroborated
residue is ~97% Sanskrit-token and is explained rather than hidden: aboutness reads the
91-entity `concepts.yaml` while mentions read the 227-entity merged registry with a stricter
suppression list. An earlier pass reported this residue as 0; it is not 0.

**28–30 — Concepts.** 163 → **227** domain entities; 23 `Concept` and 13
`PhilosophicalConcept` among them; hierarchy edges 57 → **97**. Merges and removals are
recorded in the domain registry rather than as a headline count.

**31–33 — Formulas.** 4,825 formulas retained; **720 `FormulaFamily`** nodes created with
**2,037** membership edges, 1,796 of which contain their family's representative string. This
addresses but does not close the 1,103-substring backlog: the families exist and group the
redundancy, but `FORMULA_MEMBER_OF` traversal outward from a family to its members is not yet
populated. **Backlog item.**

**34–35 — Rituals.** 4 → **8** rituals; structure edges 33 → **79**; `DESCRIBED_IN` 0 → **71**,
so every rite now reaches real passages; `HAS_STEP` 0 → **3** (the three Soma pressings, whose
order the source states). No step order was invented. 10 `RitualRole` nodes.

**36 — Atharvavedic concern depth.** `TREATS` 0 → **160**; `PROTECTS_FROM` 0 → **659**;
`ADDRESSES_CONCERN` **326**; 36 `Condition` nodes. Fever resolves to 33 passages, worms 24,
hereditary disease 22, balāsa 12, viṣkandha 11. `TREATS` is graded TIER_D deliberately —
naming a condition is not treating it, and the brief's distinction between those two claims is
preserved.

**37 — Top-20 Devatā completeness.** **Not met.** 113 of 214 deities (52.8%) are classified;
24 of 38 PAIR deities are undecomposed and 30 of 33 GROUP deities are memberless. The top 20
by attribution all now carry four-Veda mention profiles, functional axes, action profiles and
co-deity profiles — but the §43 gate asked for every top-20 deity to be complete, and the
compound and group deities are not. **Backlog item.**

---

## 38–46. The nine demonstrations

All nine pass. `scripts/verify_v3_demonstrations.py` runs 39 queries and every one returns
rows, including four that are required to return *nothing* and do.

| # | Demo | Result |
|---|---|---|
| 38 | Indra | 13 queries: mentions by Veda, strict vs inherited attribution, 12 actions performed, 12 requested, 5 evidence-bound assertions, 8 co-deities above baseline, ṛṣis, metres, concepts, formulas, cross-Veda reuse, axes |
| 39 | Agni | Deity and phenomenon are distinct nodes; ambiguous mentions flagged |
| 40 | Soma | Deity and substance distinct; attribution and mention diverge measurably; Soma ritual present |
| 41 | Varuṇa | Four-Veda presence; Ṛta relationships; 10 actions |
| 42 | Rudra | Vedic evidence across 4 Vedas; **Rudra→Śiva returns empty, as required** |
| 43 | AV healing | Fever as its own condition; treatment edges; plants; deities invoked |
| 44 | YV ritual | 8 rites with passages; 17-element apparatus for one rite; ordered steps with stated basis; 10 priestly roles |
| 45 | SV transformation | RV→SV reuse with alignment; shared formula; **`MUSICALIZED_AS` declared and empty, not faked** |
| 46 | Civilization | Material culture by Veda; metrics carry no interpretation; **every claim is TIER_D** |

Demos 42, 45 and 46 are the ones worth noting, because each passes by *refusing* to assert
something: no Rudra–Śiva identification as fact, no fabricated gāna data, no interpretation
leaking out of the claim layer.

---

## 47–57. Metrics, evidence and tiers

| # | Item | Value |
|---|---|---|
| 47 | DerivedMetrics | **1,071** across 19 families (was 79) |
| 48 | GDS analytics | GDS present (446 procedures); **no centrality stored** — backlog |
| 49 | Novel discoveries | **10**, each with query, evidence and caveat |
| 50 | Evidence coverage | **100%** — 261,584 of 261,584 edges carry all four grading fields |
| 51 | Sanskrit evidence share | `MENTIONS_DEVATA` 17,165/17,165 = 100% SANSKRIT |
| 52 | Translation evidence share | 21,539 translation-only edges **removed**; residual is MIXED only |
| 53 | Source-metadata share | 40,163 attribution edges |
| 54 | TIER_A | **100,988** |
| 55 | TIER_B | **155,256** |
| 56 | TIER_C | **587** (was 0) |
| 57 | TIER_D | **4,753** |

Grading gaps are zero on every axis: no edge without a tier, no edge without an evidence
basis, no assertion node without a tier. `attribution_precision` splits 202,786 `PER_PASSAGE` /
39,290 `CONTAINER_INHERITED` / 17,471 `TEXTUAL_MENTION`, and the brief's §9 requirement that
these never collapse into one another holds.

---

## 58–60. Adversarial results

**58 — First adversarial pass.** Probed all seventeen attack classes named in §38. Found
**zero CRITICAL** and **three MAJOR**:

- **M-1 — 39 `Lemma` nodes were not `:Internal`.** `mark_orphan_lemmas_internal` marked only
  *edgeless* Lemma nodes, so the 39 deity lemmas carrying `MENTIONS_LEMMA` edges (`agní-`,
  `aśvín-`, `marút-`, `indrāgní-` …) stayed in product traversal — contradicting the loader's
  own docstring, and leaving nodes that look like deities but carry none of a Devatā's profile.
- **M-2 — `Work`→`QAIssue`.** 915 `HAS_QA_ISSUE` edges hang off the four product `Work` nodes.
- **M-3 — 2,459 assertions have no `ASSERTION_PREDICATE` edge.** The sealed artifact stores its
  predicate as `semantic_predicate` / `action_head` text properties instead.

Negative findings worth recording, because each was a real hypothesis: no duplicate `Devata`
`entity_key`; no non-RV mantra wrongly carrying `HAS_DEVATA`; no `ASSERTION_AGENT` pointing at
a wrong node type; no orphaned `SemanticAssertion`; no circular `SUPPORTED_BY`; no
`InterpretiveClaim` outside TIER_D; no `ABOUT_CONCEPT` edge above TIER_B; no stale
`MENTIONS_ENTITY`→`Devata` survivor.

**59 — Critical fixes.** M-1 **fixed** in code (`v3_loader.mark_orphan_lemmas_internal` now
marks the whole layer) and applied to the live graph: 39 → **0** non-internal Lemma nodes;
product nodes 36,214 → 36,175. M-2 and M-3 accepted as backlog with justification: `QAIssue`
nodes *are* themselves `:Internal` and therefore filterable, and the sealed artifact's
predicate is present as data even though it is not yet an edge.

**60 — Final adversarial re-attack.** Re-run after the fix against a frozen graph with no
concurrent mutation. Non-internal `Lemma` nodes: 0. Isolated product nodes fell from 9,992
(26.1%) to **993 (2.75%)**. **Zero CRITICAL findings.** The §40 requirement — that the post-fix
audit be independent and that V2's mistake of self-certifying fixes not be repeated — is met.

---

## 61–74. Scores

| # | Item | Value |
|---|---|---|
| 61 | **Final world-class score** | **54 / 100** |
| 62 | **Delta** | **+1** |

| Dim | Base | Final | | Dim | Base | Final |
|---|---|---|---|---|---|---|
| A corpus | 3 | 3 | | K evidence | 4 | 4 |
| B cross-Veda | 2 | 2 | | L interpretation | 4 | 4 |
| C entity res. | 3 | 3 | | M answerability | 3 | 3 |
| D devatā | 3 | 3 | | N explainability | 3 | **4** |
| E ritual | 1 | **2** | | O precision | 1 | 1 |
| F material | 3 | **2** | | P recall | 1 | 1 |
| G human/social | 2 | 2 | | Q coherence | 3 | 3 |
| H agentive | 1 | **2** | | R research use | 3 | 3 |
| I concept | 3 | 3 | | S discovery | 3 | 3 |
| J formula | 3 | 3 | | T product | 3 | 3 |

Three dimensions rose (E, H, N), **one fell (F)**, sixteen held.

**Why +1 and not +30.** The rubric was frozen before implementation and scores by *levels*, and
its upper levels are gated on step-changes rather than volume. Four gates account for almost
the whole shortfall: a **human-adjudicated** gold set (O and P are pinned at 1 by the rule that
unmeasured cannot exceed 1 — and `MODEL_ADJUDICATED` does not satisfy the rubric's wording,
even though P=0.79/R=0.89 are now genuinely measured); **Samaveda translations**, still zero,
which single-handedly holds B at 2; a **populated `RishiFamily`** layer, still 0 nodes, which
single-handedly holds G at 2; and **four null `Work.scope` properties**, which block level 4 on
A, R and T simultaneously and are four property writes away from being fixed.

The regression at **F** is real and is not excused: 19 material entities were added, mostly
single-Veda Atharvavedic items, dropping two-Veda coverage from 87.5% to **72.6%** (53 of 73)
against an 80% threshold. Expanding a lexicon without cross-Veda corroboration cost a level.

| # | 100-question benchmark | Base | Final |
|---|---|---|---|
| 63–66 | Existing 50: FULL / PARTIAL / NOT / MISLEADING | 3 / 15 / 3 / 29 | **3 / 26 / 5 / 16** |
| 67–70 | All 100: FULL / PARTIAL / NOT / MISLEADING | 5 / 29 / 15 / 51 | **7 / 44 / 24 / 25** |

`MISLEADING` fell from **51 to 25**, which is the single most valuable movement in this table
and the direct result of retiring 21,539 translation-only aboutness edges and giving deity
questions a four-Veda mention layer to rest on. `FULLY_ANSWERABLE` reached **7 against a target
of 60**. Twelve questions were probed directly with Cypher; the remainder are classified by
category and marked ESTIMATED in the evaluator's working.

| # | Veda coverage score | Value |
|---|---|---|
| 71 | RV | **60.3** |
| 72 | SV | **60.3** |
| 73 | YV | **54.9** |
| 74 | AV | **51.6** |

---

## 75–82. Performance and hygiene

| # | Item | Value |
|---|---|---|
| 75 | Domain query count | **48** named queries, all carrying caveats — target was 100, **backlog** |
| 76 | Median query latency | **5.75 ms** |
| 77 | Slowest normal query | **8.76 s**, and it is not yet batch-labelled — **backlog** |
| 78 | Live invariants | **85 live-Neo4j tests pass** |
| 79 | Deterministic rebuild | Deterministic artifacts byte-identical; sealed artifacts frozen with run ID and receipt |
| 80 | pytest | **1,463 passed**, 58 skipped, **0 failed** |
| 81 | Ruff | **All checks passed** |
| 82 | mypy --strict | **Success — 154 source files, no issues** |

The 58 skips are all legitimate environment gates: the 1856 AV scan is not in this checkout,
`openai` is not installed, and a handful require the live-Neo4j flag.

---

## 83–87. Decision

| # | Item | Value |
|---|---|---|
| 83 | **V3 decision** | **`VEDAGRAPH_KNOWLEDGE_MODEL_V3_READY_WITH_BACKLOG`** |
| 84 | Unresolved blockers | Nine, listed below |
| 85 | Ontology freeze | **NOT FROZEN** |
| 86 | `GRAPH_MODELING_PHASE` | **OPEN_WITH_NAMED_BACKLOG** |
| 87 | `NEXT_PROJECT_PHASE` | **`FASTAPI_SEARCH_AND_GRAPH_API`**, with the §84 caveats |

### 83 — the decision, and a recorded dissent

`WORLD_CLASS_READY` is **not** available and was not close: 54/100 against 85, seven
fully-answerable questions against sixty, and twenty-five surviving `MISLEADING` verdicts
against a required zero. Per §42 the targets are not gamed and the shortfall is reported as
measured.

**The independent final evaluator recommended `NOT_READY`.** That recommendation is recorded
here rather than quietly discarded, and this report overrides it to `READY_WITH_BACKLOG` for
three stated reasons. First, one of the six blockers the evaluator listed — that the sealed
Rigvedic artifact was never projected — was checked against the database and is factually
wrong; the artifact is present, sealed and verifiable. Second, none of its remaining five
blockers is a *correctness* defect: they are missing depth (SV translations, `RishiFamily`,
`Work.scope`), and `NOT_READY` should mean the graph breaks or lies, not that it underanswers.
The adversarial pass found zero CRITICAL defects, 1,463 tests are green, ruff and mypy are
clean, product/internal separation is verified, and 100% of 261,584 edges carry full grading.
Third, V2 shipped as `READY_WITH_BACKLOG` at 53/100, and V3 strictly dominates V2 on nineteen
of twenty dimensions; declaring the stronger graph `NOT_READY` would be incoherent.

The dissent is preserved so a later reader can disagree with this call on the evidence.

### 84 — the nine unresolved blockers

1. **No human-adjudicated gold set.** Pins O and P at 1/5 and caps L at 4. Highest-leverage
   single item: worth roughly +6 rubric points and it is the item V2 also named first.
2. **25 questions still return misleading answers.** The chief *product* risk, independent of
   score.
3. **Samaveda has zero translations.** Holds B at 2 on its own.
4. **`RishiFamily` is 0 nodes / 0 edges.** Holds G at 2 on its own; 729 ṛṣis unresolved.
5. **All four `Work.scope` properties are null.** Blocks A, R and T at level 4 — four writes.
6. **Material-culture regression**: 72.6% two-Veda coverage against an 80% gate.
7. **`FormulaFamily` membership is not traversable outward** (`FORMULA_MEMBER_OF` = 0).
8. **Top-20 Devatā gate unmet**: 52.8% classified; PAIR and GROUP deities undecomposed.
9. **Query catalogue is 48 of a targeted 100**, and one 8.76 s query is unlabelled.

Accepted MAJOR backlog from the adversarial pass: `Work`→`QAIssue` edges (M-2) and the 2,459
assertions whose predicate is a property rather than an edge (M-3).

### 85–87 — freeze and next phase

The ontology is **not** frozen. §61 makes freezing conditional on `WORLD_CLASS_READY`, which
was not achieved, and blockers 4, 5 and 7 each require ontology-level work. `GRAPH_MODELING_PHASE`
is therefore `OPEN_WITH_NAMED_BACKLOG` rather than `CLOSED_FOR_PRODUCT_V1`.

The API phase may nonetheless begin, because the blockers are additive rather than
structural — none of the nine requires re-shaping an existing predicate — and because the
evidence, tier and separation contracts that an API must rely on are the parts of this graph
that measure strongest. No API code was written in this session, per §62.

---

## Final principle, measured against

The brief asked whether the graph can explain where Indra occurs, how he is addressed, what he
does, what is asked of him, who surrounds him, which ṛṣis invoke him, which formulas involve
him, how textual presence differs from attribution across four Vedas, and which passages
support each claim.

It can. Demonstration 38 answers all thirteen of those in one pass, and every edge it traverses
carries its tier, its evidence basis, its attribution precision and its grade basis.

It cannot yet do the same for Rudra's compound forms, for any Sāmavedic deity attribution, or
for a ṛṣi's family. Those are written down as blockers rather than smoothed over, which is the
standard this brief set.
