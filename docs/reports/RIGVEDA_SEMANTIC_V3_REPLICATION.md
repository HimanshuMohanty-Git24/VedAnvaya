# RIGVEDA SEMANTIC V3 REPLICATION

**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** This report documents an independent second extraction over the same 120-mantra benchmark. It is not accuracy or truth evaluation.

## Input freeze

- Selected IDs: **120**; selected-ID hash: `4825dcc81b9ca57ecacfe9021511cb89067832b8fab4822d7aeae9daedfcc88a`.
- Prompt hash: `b8cc7d3df061ec928947b1723b3df3a7d4cf3e3d9c53af53ab55ccc5852cfafb`; schema hash: `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2`.
- EvidencePacket hashes: **120**, sealed before comparison.
- Comparison sources opened during extraction/sealing: **false**.

## Configuration

- Model: `gpt-5.6-luna`; reasoning: `high`; runtime: `CODEX_DIRECT`; API invocation: `False`.
- Batch structure: **8 × 15**; human gold: **UNANNOTATED**; unlocked predicates: `[]`.

## Replication-only QA

| Measure | V3-A | V3-B |
|---|---:|---:|
| Assertions | 211 | 211 |
| No-claim mantras | 28 | 28 |
| Assertions/mantra | 1.758 | 1.758 |
| Canonical refs | 57 | 57 |
| Non-canonical assertion objects | 183 | 183 |
| Ontology gaps | 29 | 29 |
| EXPLICIT | 211 | 211 |
| STRONG_INFERENCE | 0 | 0 |
| Validator rejections | 0 | 0 |
| Evidence failures | 0 | 0 |

## Stability

- Exact assertion-set agreement: **92**.
- Partial assertion-set agreement: **0**.
- Different assertion-set: **0**.
- No-claim agreement: **28**; no-claim disagreement: **0**.
- Evidence references: same **211**, different valid **0**, invalid A/B **0/0**.
- Explicitness switches EXPLICIT ↔ STRONG_INFERENCE: **0**.
- Severity rows: low **211**, medium **0**, high **0**.

## Scorecard

| Scorecard item | Result |
|---|---:|
| Mantra exact-set stability | 92/120 |
| Predicate-presence stability | see predicate report |
| Canonical-entity stability | 0 contradictions |
| Typed-object stability | see object report |
| Evidence-anchor stability | 211 same / 0 different valid |
| No-claim stability | 28/120 agreement |
| High-severity disagreement count | 0 |

## Gate

Recommendation: **V3_STABLE_ENOUGH_FOR_508_CANDIDATE_PILOT**.

This does not unlock predicates, create human gold, auto-accept assertions, or make V3 truth. Any future 508 run remains candidate-only and expert-review cases remain flagged.

## Slow deterministic rebuild

- Knowledge-layer byte-identical rebuild: **PASS**.
- Lexical-layer byte-identical rebuild: **NOT_COMPLETED** after a separate practical wait; it was interrupted.
- Unicode-normalization checks: **PASS**.
