# V3.1 Wave 1 — integrator-executed items

Agent A's own Wave 1 tasks: the ones ranked XS in `V3_1_ROI_PLAN.md` and the slow-query
profile. Formula families and assertion predicates were Agent E's; the deity and ṛṣi
layers were Agents C and D.

| Field | Value |
| --- | --- |
| Starting commit | `d456cce` |
| Graph at start | 108,689 nodes / 261,584 relationships |
| Items | ROI tasks 6 (`Work.scope`), 7 (`QAIssue`), 8 (slow query, profiled), plus live invariants |

---

## Task 6 — `Work.scope`: done, and it fixed a misleading string

**The defect.** Each of the four `Work` nodes carried seven properties and not one of them
said what the corpus *is*. The Sāmavedic node's `display_label` read **"Samaveda
Samhita"** over a corpus that is the Kauthuma **ārcika only** — 1,844 keyed verses beside
a gāna body of roughly 2,639 ganas that this `work_id` cannot address. The corpus's own
manifest says, in the file on disk, *"Never describe this dataset as the complete
Samaveda."* The graph a consumer queries did not have that sentence. The V3 scorecard
called it "the single most misleading string in the product graph" and it was right.

**What landed.** Six properties per work, from `data/registry/works.yaml`, projected by
`vedagraph.domain.work_scope` and registered as the `work_scope` layer in
`scripts/build_knowledge_model_v3.py`:

| Property | What it is for |
| --- | --- |
| `scope` | prose: what this `work_id` addresses and what it does not |
| `completeness` | the **measured** figure with its shortfall enumerated |
| `excluded_corpora` | the same fact as `scope`, as a list a query can filter on |
| `rights` | the manifest's own rights block, passed through verbatim |
| `scope_evidence` | which repository file licenses each claim |
| `display_label_override` | the scope-honest product label |

Measured after projection: `sent=4 landed=4`, all six properties present on all four
works, `unscoped_works()` empty, three of four labels overridden.

| Work | product label now reads |
| --- | --- |
| `VG:WORK:RV:SAK` | Rigveda Samhita *(unchanged — it is accurate)* |
| `VG:WORK:SV:KAU` | Samaveda Samhita - Kauthuma arcika only (gana corpus NOT included) |
| `VG:WORK:YV:VSM` | Vajasaneyi Samhita - Shukla Yajurveda, Madhyandina recension (Krishna Yajurveda NOT included) |
| `VG:WORK:AV:SAU` | Atharvaveda Samhita - Saunaka recension, working corpus (Paippalada NOT included) |

**Three design decisions worth stating, because each avoided a worse fix.**

*The traditional name was not edited.* `work_name` is projected from
`data/canonical/*/works.jsonl`, and those files are hashed into their corpus manifest's
`generated_files` block. Rewriting the name in place would have broken a manifest hash
*and* destroyed a true fact — the corpus really is called the Sāmaveda Saṃhitā. So the
traditional name stays exactly as the artifact records it and the honest label is an
overlay beside it. Fix by overlay outside the seal, never in place.

*The scope statements went in `data/registry/works.yaml`, which nothing hashes.* Verified
rather than assumed: all five `data/semantic/*/input_freeze.json` and the V3.2 output seal
were checked for `works.yaml`, `pyproject.toml`, `queries.py`, `v3_loader.py` and
`models/core.py`; none appears in any of them. `build_config_sha256` is
`file_sha256(config_path)` over the build config alone, so the registry is not inside it
either. The only references to `works.yaml` under `data/` are prose comments.

*The two loaders were made order-independent.* `upgrade.set_display_properties`
recomputes every product node's `display_label` from `_DISPLAY_SOURCES`, and its `Work`
entry read `coalesce(n.work_name, n.abbreviation)`. Whichever loader ran last would have
won, so "Samaveda Samhita" would have silently returned on the next projection.
`display_label_override` is therefore written onto the node as well as applied, and
`_DISPLAY_SOURCES` now coalesces it first. `test_work_scope.py` pins that ordering with a
failure message explaining why, because the next person to touch that tuple will not
otherwise know.

**Nothing historical was invented.** Every exclusion is grounded in a file already in the
repository, named in `scope_evidence`: the coverage percentages and the "no second
recension, no post-saṃhitā layer" statement come from
`KNOWLEDGE_MODEL_V3_WORLD_CLASS_SCORECARD.md` §A; the Sāmavedic scope sentence is the
manifest's own `rights_summary.scope`, quoted not paraphrased; the Kāṇva, Taittirīya,
Kāṭhaka, Maitrāyaṇī, Śatapatha and Paippalāda bodies are named as known-and-not-held in
`data/source_registry/yajurveda_sources.yaml` and
`data/source_registry/atharvaveda_sources.yaml`. The Rigvedic entry deliberately says
"SECOND_RIGVEDIC_RECENSION" rather than naming Bāṣkala, because the repository does not
record that name anywhere and this task was not licensed to add historical claims.

Tests: `tests/domain/test_work_scope.py`, 10 passing, all offline.

---

## Task 7 — `Work`→`QAIssue`: fixed at root, not filtered

**The defect** (adversarial finding M-2, accepted as V3 backlog): 915 `HAS_QA_ISSUE` edges
hung off the four product `Work` nodes, so following edges outward from a product node
landed in the engineering layer. V3 justified deferring it on the grounds that `QAIssue`
nodes are themselves `:Internal` and therefore filterable — true, but the brief's
requirement is that *normal graph exploration must not reach it*, and a filter the reader
has to remember is not that.

**The fix.** The edge direction is reversed and the predicate renamed:
`(:Work)-[:HAS_QA_ISSUE]->(:QAIssue)` becomes `(:QAIssue)-[:QA_ISSUE_ON]->(:Work)`. This is
the truthful direction as well as the safe one — a QA finding is a fact about this
repository, not a property of the Rigveda — and outward traversal from a `Work` can no
longer reach the diagnostic layer at all. Changed in seven code sites
(`graph/schema.py`, `graph/loader.py`, `graph/insight_queries.py`, `domain/tiers.py` ×3,
`enrich/predicates.py`, `enrich/validate.py`, `scripts/generate_ontology_reference.py`,
one test); zero references to the old name remain.

Live migration, reconciled explicitly rather than by MERGE alone:

| | before | after |
| --- | --- | --- |
| `HAS_QA_ISSUE` | 915 | **0** |
| `QA_ISSUE_ON` | 0 | **915** |
| new edges missing grading metadata | — | **0** |
| product-node outward edges reaching a diagnostic node | 915 | **0** |

Properties were copied with `SET n = properties(r)` rather than recomputed, so the grading
invariant survives the migration; the old edges were `DELETE`d explicitly, because merging
the new direction alone would have left both in place forever.

---

## Task 8 — the slow query: profiled, diagnosed, and deliberately not patched in place

**Measured.** All 86 named queries were timed against the live graph. Exactly one is slow:

| query | best of 3 |
| --- | --- |
| `conceptually_similar_not_reused` | **5,322 ms** |
| next slowest (`deity_co_occurrence`) | 400 ms |
| median | well under 20 ms |

So this is one query, not a systemic latency problem, and the V3 report's 8.76 s figure is
now 5.3 s on a warm cache.

**Diagnosis — it is worse than slow.** The query is an exact all-pairs self-join,
`(a:Passage)-[:MENTIONS_ENTITY]->(e)<-[:MENTIONS_ENTITY]-(b:Passage)`, with the cross-Veda
predicate applied *after* expansion. The entity degree distribution is severely
hub-skewed — median 31, p95 526, maximum 1,206 (`heaven (dyaus)`), with `soma juice`
1,169 and `fire (agni)` 1,028 — so the pair space is roughly Σdeg²/2, on the order of 15
million pairs, to yield 2,575 qualifying pairs and 25 returned rows. Adding a single
`collect` to inspect which entities are shared **exceeds the 1.4 GiB transaction memory
limit and the query dies**, which makes this a stability hazard and not merely a latency
figure.

**Four rewrites were measured.** Seeding the join on low-document-frequency entities and
intersecting per-passage entity lists reaches **108–128 ms** — but it drops the query's own
top row. That row is `AVS 9.10.14 / VSM 23.62`, sharing six entities, and it is a *good*
hit: both are riddle/cosmology passages and their shared entities include `altar (vedi)` at
document frequency 17. So the fast rewrite loses a real answer, and shipping it would trade
a latency number for recall.

One finding here is a defect in my own first rewrite and is recorded because it is a trap
anyone repeating this work will hit: enumerating pairs as `range(0,n-2) × range(i+1,n-1)`
produces each unordered pair in **one** ordering only, so the inherited `a.veda < b.veda`
predicate silently discarded roughly half of them. The original `MATCH` pattern generates
both orderings, which is why the same predicate is correct there and wrong here. It has to
become `veda_a <> veda_b` plus an explicit canonical swap.

**Decision: materialize, do not micro-optimise.** The correct fix is to precompute the
2,575 qualifying pairs into a derived layer and have the named query read it, which makes
the online cost trivial without changing the answer set. That is deferred to integration
for a stated reason rather than left undone: the computation's input is `MENTIONS_ENTITY`,
which **Agent D is mutating in this same session** under the material-culture recall audit.
Precomputing now would bake in a stale input. `QUESTION_UNLOCKED = Q22, Q49`.

A second improvement belongs with it. "Shares ≥ 3 entities" is weak evidence of a shared
idea when the shared entities are `heaven`, `sacrifice` and `soma`, which appear in a large
share of the corpus; the materialized edge should carry a distinctiveness measure over the
document frequencies of the shared entities, so a reader can tell a `vedi`-sharing pair
from a `soma`-sharing one. Q22 and Q49 are both graded `MISLEADING` in the baseline, and
undifferentiated hub-driven similarity is a plausible part of why.

---

## New: `scripts/check_live_invariants.py`

Sixteen contracts that are only observable against a populated database, each phrased as
the *defect* it would be rather than as the desired state, because every one of them
corresponds to something this repository has actually shipped. It is the integrator's
safety net while several agents mutate one database, and it is the source for the report's
live-invariants line.

State at the time of writing (mid-session, Agents C/D/E still working): **0 failing, 2
warning of 16**.

**One invariant had to be narrowed, and the reason is a finding.** The obvious form of the
product-boundary check — "no product node has an outgoing edge to an `:Internal` node" —
reports **70,559 violations**, and every one of them is legitimate: 44,276
`HAS_TEXT_VERSION` + 17,283 `HAS_TRANSLATION` + 9,000 `MENTIONS_LEMMA`. The `Internal`
label is doing **two different jobs**: it marks the *diagnostic* layer (`QAIssue`, which no
researcher should traverse into) and it marks *sub-entities that are not product entities
in their own right* (`TextVersion`, `Translation`, `Lemma`, `Source`, `SourceArtifact`,
which must stay reachable — a passage that could not reach its own text would be useless).
The invariant therefore names the diagnostic labels instead of the marker label. **This is
written down here because an adversarial auditor running the obvious form will report a
false CRITICAL**, and 70,559 is a number alarming enough to be believed.

## Over-claim found in the V3 close-out

The V3 final report states that "100% of 261,584 edges carry full grading". For
`quality_tier` and `grade_basis` that is confirmed — 0 edges lack either. For
`attribution_precision` it is **false**: 2,037 `MEMBER_OF_FAMILY` edges have never carried
it, and they predate this session. The scorecard's supporting figures
(PER_PASSAGE 217,449 + CONTAINER_INHERITED 24,698 = 242,147) sum to the *V2-era* edge
total, so the percentage was computed against a stale denominator and the gap was invisible.

Whether `attribution_precision` is even meaningful for a formula-to-family membership is a
real question — it describes whether an *attribution* is per-verse or container-inherited,
and a membership is not an attribution — so the resolution has been handed to Agent E, who
owns that layer, with the note that an explicit `NOT_AN_ATTRIBUTION` value would keep the
"every edge says" contract true without forcing a false `PER_PASSAGE`.
