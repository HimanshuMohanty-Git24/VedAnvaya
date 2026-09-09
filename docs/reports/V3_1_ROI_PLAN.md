# VedaGraph V3.1 — ROI Plan and Frozen Task Order

**This document is the frozen task order for the V3.1 closure strike.** It was written
before any code was changed, from measurements taken against the live database at the
starting commit. Once frozen, tasks are executed in the order given here; a task may be
*dropped* for stated cause but may not be *promoted* past a higher-ranked task.

| Field | Value |
| --- | --- |
| Starting commit | `d456cce` (branch `semantic-pilot-v1`) |
| Measured graph | 108,689 nodes / 261,584 relationships (verified live, matches V3 close-out) |
| Database | `bolt://localhost:7687`, Neo4j 5.26, container `vedagraph-neo4j` healthy |
| Audit timebox | 20 minutes — respected |
| Mandate | `MISLEADING` to 0 is priority #1; quality gain per unit time, not graph size |

---

## 0. What the audit found that changes the plan

Five measurements taken during the audit contradict or sharpen the V3 close-out report's
own backlog, and the task order below is built on the measurements rather than the report.

**1. The 25 surviving `MISLEADING` question IDs are not recorded anywhere.** The V3 final
report states `7 / 44 / 24 / 25` and adds that "twelve questions were probed directly with
Cypher; the remainder are classified by category and marked ESTIMATED in the evaluator's
working." That working document was never committed — `grep -rl ESTIMATED docs/reports`
returns only the final report itself. **There is therefore no per-question list of what is
currently wrong.** The single highest-value act in this session is to produce one, and it
must be produced by reading rows, not by inheriting the estimate. Wave 2 cannot be
executed against a number; it needs IDs.

**2. The query catalogue is 86 queries, not 48 — but it serves only 49 of 100 questions.**
`len(QUERIES)` is 86 and every one carries a caveat. The backlog item "query catalogue is
48 of a targeted 100" is stale on the count and *understates* the real defect: the `serves`
mapping covers Q1–Q50 minus Q37, and **not one of Q51–Q100 has a named query at all**.
Chasing a query count is therefore explicitly the wrong target, exactly as the brief says.
The right target is question coverage: 51 uncovered questions.

**3. `referent_certainty` already exists on every mention edge, but only as a two-way
split.** All 17,165 `MENTIONS_DEVATA` edges carry `referent_certainty`, distributed
`DEITY_AMBIGUOUS` 8,825 / `DEITY_CERTAIN` 8,340. There is no `DEITY_PROBABLE`. So 51.4% of
the deity mention layer is currently in a bucket that default analytics should exclude
wholesale — which is safe but blunt, and is the direct cause of several misleading deity
answers. The brief's three-way scheme is a *refinement of an existing property*, not new
ontology, which makes it far cheaper than it looks.

**4. `RishiFamily` is not data-blocked. The evidence is already in the node labels.** The
367 Rigvedic rishi entries are Anukramani strings of the form *patronymic + personal name*:
`bhāradvājaḥ pāyuḥ`, `bhārgavaḥ kaviḥ`, `aucathyo dīrghatamāḥ`, `bhāmyaśvo mudgalaḥ`. The
patronymic is a vrddhi-derived gotra adjective, and vrddhi is a *grammatical* marker of
descent, not a string resemblance — `bhṛgu` to `bhārgava` is a stated derivation, not a
similar spelling. The V3 report treats this layer as requiring research it does not
require. There is no `gotra` field anywhere in the repo (the single `grep` hit in
`source_assertions.jsonl` is the word inside a verse), so the extraction must come from the
Anukramani string, conservatively and with coverage reported.

**5. The slow query is `conceptually_similar_not_reused`, measured at 5,995 ms.** Timing all
86 queries puts the next slowest at 400 ms and the median at well under 20 ms, so this is
one query, not a systemic latency problem. Its shape is a passage-by-passage self-join
through `MENTIONS_ENTITY` with no degree bound, which is the accidental-Cartesian shape the
brief names. One query, one fix.

Two further measurements confirm the report: `Work` carries no `scope` key at all (not even
null), and `MEMBER_OF_FAMILY` runs `Formula`-to-`FormulaFamily` only, with no outward edge.
`HAS_QA_ISSUE` is `Work`-to-`QAIssue`, and the `QAIssue` nodes *are* already labelled
`Internal` — so the leak is the edge out of a product node, not an unlabelled node.

---

## 1. Scoring method

`IMPACT` 0–5 on graph trustworthiness. `PRODUCT_VALUE` 0–5 on what a reader can do.
`QUESTIONS_UNBLOCKED` counts benchmark questions the task is a necessary condition for.
`COST` and `RISK` are converted to divisors so the brief's formula can be computed rather
than asserted: XS=1, S=2, M=4, L=8, XL=16; LOW=1, MEDIUM=2, HIGH=4.

PRIORITY = (IMPACT x PRODUCT_VALUE x max(QUESTIONS_UNBLOCKED, 1)) / (COST x RISK)

The ranking is used as a *sort*, not as a truth claim; where the formula and the brief's
explicit priority order in section 18 disagree, section 18 wins and the disagreement is
noted.

---

## 2. The ranked table

| # | Task | IMPACT | COST | RISK | QUESTIONS_UNBLOCKED | SCORE_POINTS | PRODUCT_VALUE | PRIORITY | Wave |
|---|------|--------|------|------|---------------------|--------------|---------------|----------|------|
| 1 | **Diagnose the real `MISLEADING` set** — probe all 51 baseline-misleading questions live, record ID + root-cause class | 5 | M(4) | LOW(1) | 51 (all of them) | 0 directly, gates ~10 | 5 | **319** | 2 |
| 2 | **Three-way `referent_certainty` + default ambiguity policy** | 5 | M(4) | LOW(1) | 12 (Q20,41,45,46,84,87,88,89,92,3,33,38) | ~2 (O,D) | 5 | **75** | 2 |
| 3 | **Named queries for Q51–Q100 + Q37** | 4 | M(4) | LOW(1) | 51 | ~3 (M,R,T) | 5 | **255** | 1/2 |
| 4 | **`FormulaFamily` outward traversal** (`HAS_FORMULA`) | 3 | XS(1) | LOW(1) | 4 (Q8,58,60,81) | ~1 (J) | 4 | **48** | 1 |
| 5 | **`SemanticAssertion` predicate normalization** (2,459) | 3 | S(2) | LOW(1) | 3 (Q18,51,100) | ~1 (H,N) | 3 | **13.5** | 1 |
| 6 | **`Work.scope` x 4** | 2 | XS(1) | LOW(1) | 2 (Q79,80) | **3 (A,R,T level 4)** | 3 | **12** | 1 |
| 7 | **`Work`-to-`QAIssue` out of product traversal** | 2 | XS(1) | LOW(1) | 1 | ~1 (T) | 3 | **6** | 1 |
| 8 | **Slow-query fix** (5,995 ms to under 300 ms) | 2 | S(2) | LOW(1) | 2 (Q22,49) | ~1 (T) | 4 | **8** | 1 |
| 9 | **Top-20 Devata profile completion + PAIR/GROUP decomposition** | 4 | L(8) | MEDIUM(2) | 8 (Q1,3,12,38,43,44,52,70) | ~2 (D) | 5 | **10** | 2 |
| 10 | **`RishiFamily` from Anukramani patronymics** | 3 | M(4) | MEDIUM(2) | 4 (Q2,19,26,62) | **~1–2 (G)** | 4 | **6** | 3 |
| 11 | **Material-culture four-Veda recall audit** | 2 | M(4) | LOW(1) | 4 (Q9,10,11,84) | ~1 (F, recover regression) | 3 | **6** | 3 |
| 12 | **Ritual depth, Yajurveda-first** | 3 | L(8) | MEDIUM(2) | 4 (Q5,56,90,4) | ~1 (E) | 4 | **3** | 3 |
| 13 | **Stale caveat figures** (queries quote 16,261 / 8,485 against live 17,165 / 8,825) | 2 | XS(1) | LOW(1) | 0 | 0 | 3 | **6** | 1 |
| 14 | Samaveda `DERIVED_PARALLEL_TRANSLATION` | 2 | M(4) | **HIGH(4)** | 3 (Q6,7,43) | ~1 (B) | 2 | **0.75** | DEFER |
| 15 | Human-adjudicated gold set | 5 | XL(16) | — | 0 | +6 | 5 | **HUMAN_BLOCKED** | — |

### Ranking notes, where the formula misleads

- **Task 1 dominates by construction** and that is correct: without the ID list, Wave 2 is
  guesswork, and the brief's priority #1 is stated in terms of those IDs.
- **Task 3 scores second** on the formula because it divides 51 questions by a medium cost.
  That is real — 51 questions have no query — but it is *plumbing for measurement* rather
  than a truth fix, so it is sequenced with Task 1 rather than ahead of Task 2.
- **Task 6 scores low (12) and is executed anyway**, immediately. Four property writes
  unblock three rubric dimensions at level 4. The formula undervalues it because
  `QUESTIONS_UNBLOCKED` is the wrong denominator for a rubric-gated item.
- **Task 14 is deferred, not dropped.** RISK=HIGH because the failure mode is presenting a
  Rigvedic translation as Samavedic evidence, which is the exact class of defect this
  session exists to remove. It is admitted only if Task 1 shows a `MISLEADING` verdict that
  nothing else can clear, per the brief's section 10 "otherwise defer".
- **Task 15 is not attempted.** Per brief section 11, `MODEL_ADJUDICATED` is not
  `HUMAN_REVIEWED`, and no further pseudo-gold process will be run. It is reported as
  `HUMAN_BLOCKED`.

---

## 3. Frozen execution order

**Wave 1 — deterministic, 60–90 min.** Tasks 6, 7, 4, 5, 8, 13. Integrator-executed for
the XS items; Agent E for 4, 5 and the start of 3.

**Wave 2 — the misleading strike, 2–3 h.** Task 1 first and read-only (Agent B), then Task
2 (Agent C), Task 9 (Agent C), Task 3 completion (Agent E), then root-cause fixes assigned
from Task 1's output.

**Wave 3 — depth, 1–2 h.** Tasks 10 and 11 (Agent D), Task 12 (Agent E) only if Task 1
shows a ritual question that needs it.

**Close.** One full benchmark run, full pytest / ruff / mypy, Agent F hostile pass.

## 4. Write-partition contract, so six agents can share one database

Concurrent mutation of one Neo4j instance is the main coordination hazard in this plan. It
is handled by partitioning the graph by predicate, not by locking:

| Agent | May write | Must not touch |
| --- | --- | --- |
| A (integrator) | `Work.scope`, `HAS_QA_ISSUE`, query module | everything else |
| B | **nothing — read-only for its whole diagnosis phase** | all writes |
| C | `MENTIONS_DEVATA` props, `Devata`, `DeityGroup`, `COMPOSED_OF`, `HAS_AXIS` | rishi, formula, assertion layers |
| D | `RishiFamily`, `MEMBER_OF`, `DomainEntity` mentions | deity layers, formula layers |
| E | `FormulaFamily`/`HAS_FORMULA`, `ASSERTION_PREDICATE`, ritual nodes | deity and rishi layers |
| F | **nothing — audit runs against a frozen graph** | all writes |

Agent B's diagnosis is deliberately scheduled against the *starting* graph. Its verdicts
are a diagnosis of `d456cce`, and the final benchmark run at the end of the session is what
measures the delta — not a moving re-grade underneath the fixes.
