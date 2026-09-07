# V3.2 two-run 60-mantra stability result

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

Result: **PASS — `POLICY_STABILITY_ONLY_NOT_ACCURACY`**.

Both independent GPT-5.6 Luna / high / CODEX_DIRECT runs completed all 60 frozen
EvidencePackets and were sealed before comparison. The gate is an engineering policy-
stability diagnostic only. It does not establish philological correctness and it promotes
no assertion to canonical knowledge.

## Input custody and completion

- Run A: 60/60 selected final responses; seal `86dbf929c2f33d74f466b91fa187d680ce11e2fc86027e8a2ec7aa9416372cd1`.
- Run B: 60/60 selected final responses; seal `cdad8832972c7b61e1176b7be56993f083e524fb060458845fdb1c47bd9da69d`.
- Prompt/schema/ontology and selection contracts match across the runs.
- Final-attempt rule: `LEXICALLY_LOWEST_VALID_ATTEMPT_ID`; it was fixed without inspecting
  semantic agreement.
- Run A contains one surplus schema-valid attempt left by overlapping earlier sessions. It
  is preserved and hashed, but excluded deterministically by the final-attempt rule.
- Unimported authored response files are preserved and hashed: Run A
  5, Run B
  2.
- Final selected responses revalidated with 0 receipt, hash, evidence, span, binding, or
  ontology/type failures.

## Run-level emission regimes

| Metric | Run A | Run B |
| --- | ---: | ---: |
| Assertions | 392 | 388 |
| Assertions per passage | 6.533 | 6.467 |
| No-claim passages | 2 | 2 |
| No-claim rate | 0.033 | 0.033 |
| Canonical-reference assertions | 62 | 56 |

Observed gaps: no-claim rate `0.000`
(gate threshold `0.200`); assertion density
`0.067` (threshold
`0.300`). Predicate-presence Jaccard is
`1.000`.

## Predicate counts

| Predicate | Run A | Run B |
| --- | ---: | ---: |
| `ASSOCIATED_WITH` | 19 | 12 |
| `DESCRIBES` | 78 | 71 |
| `DESCRIBES_ACTION` | 92 | 93 |
| `EXPRESSES` | 6 | 5 |
| `HAS_THEME` | 1 | 3 |
| `INVOKES` | 31 | 33 |
| `INVOLVES_OFFERING` | 8 | 8 |
| `INVOLVES_RITUAL` | 11 | 12 |
| `INVOLVES_SUBSTANCE` | 13 | 17 |
| `PRAISES` | 12 | 10 |
| `REFERS_TO_NATURAL_PHENOMENON` | 20 | 21 |
| `REFERS_TO_PLACE` | 28 | 31 |
| `REQUESTS` | 73 | 72 |

No gate-significant one-sided predicate remains.

## Passage-level replication agreement

- Exact assertion-set agreement: 6/60.
- Predicate-presence agreement: 21/60.
- No-claim agreement: 60/60.
- Canonical-entity agreement: 57/60.
- Typed-object agreement: 5/60.
- Evidence-anchor agreement: 3/60.
- Contradictory canonical target passages: 0.

Exact agreement is not the gate objective; V3.2 targets the run-level emission-regime split.
The remaining assertion-level differences stay model candidates requiring review.

## Assertion alignment

| Category | Count |
| --- | ---: |
| `A_ONLY` | 202 |
| `B_ONLY` | 198 |
| `EXACT_ASSERTION` | 52 |
| `OBJECT_GRANULARITY_DIFFERENCE` | 48 |
| `PREDICATE_BOUNDARY_DIFFERENCE` | 4 |
| `SAME_PREDICATE_COMPATIBLE_OBJECT` | 0 |
| `SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE` | 79 |
| `TARGET_DIFFERENCE` | 7 |
| `UNRESOLVED` | 0 |

## Stability gate

Gate failures: None.

The observed V3.1 split (57 vs 33 assertions; 10 vs 38 no-claims; 21 vs 0
`DESCRIBES_ACTION`) failed this same gate. The completed V3.2 pair passes because the two
runs have comparable density/no-claim behavior and no extensive one-sided predicate.

Both V3.2 runs are much denser than either V3.1 run (392/388 assertions versus 57/33).
That comparison is a distribution-shift warning, not an accuracy verdict: V3.1 is not
truth either. The stability pass therefore clears the narrow regime-consistency question
but does not clear the policy for corpus-scale use without candidate review/calibration.

## Decision and limits

`V3_2_POLICY_STABILITY_GATE_PASSED`

This supports retaining the V3.2 policy for the next candidate-only phase. It does not
authorize accepted graph edges, does not create human gold, and does not make intersection
or union truth. The 508 rerun and 10,552-mantra corpus extraction remain separate decisions;
if undertaken, keep full run/task/attempt provenance and use replicated calibration samples
to monitor regime drift.
