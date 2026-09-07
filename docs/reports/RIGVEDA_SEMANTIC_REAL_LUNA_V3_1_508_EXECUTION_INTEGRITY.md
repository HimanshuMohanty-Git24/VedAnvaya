# Real Luna 508 execution integrity

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts and were not used to author this run.

## Seal

- seal: `data/semantic/vedagraph-rigveda-semantic-luna-v3.1-508/output_seal.json`
- seal SHA-256: `4441736f3aa7b2c0b7eaa6bdd22b5f86b96170d905ac5a79314cbe5ed3133126`
- execution version: `rigveda-semantic-execution-v3.1`
- execution contract: `codex-direct-semantic-v1`
- prepared tasks: 508
- terminal validated tasks: 508
- authored receipts including preserved failed attempts: 516
- final imports: 508
- failed import events preserved: 8
- heuristic contamination: 0
- human gold: `UNANNOTATED`
- unlocked predicates: `[]`
- canonical promotion: `false`

## Periodic engineering QA

| Completed batches | Tasks complete | Imports | Refusals | Retries | Failed import events | Evidence failures | Binding failures | Receipt failures | Canonical-target failures | Span failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 120 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10 | 240 | 240 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 15 | 360 | 360 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 20 | 480 | 480 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| 22 | 508 | 508 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 0 |

Performance timings are recorded only where exposed: packet preparation is recorded in the packet build manifest; task preparation, per-task import/validation, aggregation, reporting, and total orchestration timings were not captured. API invocation is `false`; API/token cost and provider latency are not reported.

## Frozen inputs

| Input | SHA-256 |
| --- | --- |
| evidence_validator_sha256 | 0932564ad228c9dfa87caa945ac7aeece7aca1338a2deb165378f88ee3c1eaee |
| execution_contract_sha256 | 398b22f27919113c1db671c45b930098f1a4f5c38f9b69b7c6e2aab340a2182a |
| object_ontology_sha256 | ca2129760d01b7b6f672f794d58e2517065e9326d04f835799c88b3c2d1577cd |
| prompt_sha256 | b8cc7d3df061ec928947b1723b3df3a7d4cf3e3d9c53af53ab55ccc5852cfafb |
| schema_sha256 | 26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2 |
| semantic_ontology_sha256 | cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce |
| span_validator_sha256 | e16817714b2e8e1c23785176586a9e6bfb2e3de4be726758b81ba8d6a2ef8626 |

All accepted responses were rechecked against the existing receipt, candidate, V3, evidence, and binding validators. Final invalid spans, binding failures, provenance failures, and heuristic contamination are all zero. Provider build metadata is `UNAVAILABLE`; no value was invented.
