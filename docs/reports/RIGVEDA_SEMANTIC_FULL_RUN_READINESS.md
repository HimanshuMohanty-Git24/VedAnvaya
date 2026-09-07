# Full Rigveda V3 candidate readiness

Engineering diagnostics, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was performed in this audit.

## Final state

`FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED`

## Starting health

508 mantras, 917 assertions, 143 no-claim mantras, 70 gaps, 256 canonical-reference objects.
917 EXPLICIT, 0 STRONG_INFERENCE, 0 INTERPRETIVE. Legacy validator/evidence/type checks report zero
failures. Embedded 120 agrees exactly; all prior expert cases remain unannotated. These structural
and replay checks were reproduced by the relevant tests. They do not establish semantic entailment,
correct relation-to-entity binding, complete span validation or independent model replication.

## Ontology decision

`KEEP_GAPS_FOR_FULL_RUN`. Existing occurrence gaps are representable and reviewable. PERSON_REF is
optional later improvement, not a prerequisite. See RIGVEDA_SEMANTIC_508_ONTOLOGY_AUDIT.md for all 70.
Counts: {"CANONICAL_ENTITY_RESOLUTION_MISSED": 2, "EXPERT_PHILOLOGY_REQUIRED": 2, "EXTRACTION_OVERREACH": 4, "INTENTIONAL_OPAQUE_CASE": 1, "TRUE_SCHEMA_GAP": 60, "WRONG_GAP_CODE": 1}. 14 misleading substring spans.

## Parallel decision

`PARALLEL_EXTRACTION_BUG_FOUND`. Six near pairs share a false offspring request in RV 10.58.1;
five have legitimate waters/plants text differences. Both exact-partial cases are translation effects.
The relation-binding mechanism repeats in the review queue, so this is a systemic engineering blocker.
See RIGVEDA_SEMANTIC_508_PARALLEL_AUDIT.md for all 13 pair audits with deterministic metrics.

## Exact blockers and closure requirements

- **B01**: Repeated predicate-target binding failure: verse-wide cue matching creates unsupported requests and invokes/praises the wrong mentioned entity (10.58.1, 10.170.1, 8.35.7-9, 8.36.4-6). Correct the extraction execution path, preserve old artifacts, and verify these regressions before scaling. No semantic-schema expansion is needed.
- **B02**: Evidence anchoring and validation are incomplete: gap spans match inside unrelated words; legacy validation does not validate gap anchors, other_evidence_ids or nested entity IDs. The new offline import guard closes ID-membership holes, but the frozen producer still creates misleading spans. Correct producer anchoring and version the execution contract.
- **B03**: Provenance/readiness evidence mismatch: run_semantic_luna_v3_508.py calls the regex extract_packet implementation directly; model labels are constants and no independent model response receipt is consumed. Stable replay proves deterministic reproduction, not independent Luna replication. Establish an auditable actual Luna execution path and a bounded verification under its new execution version before authorizing the full model run. Do not relabel old data.

No blocker is an exhaustive-human-review requirement. No ontology or prompt/schema change is proven
necessary. This session adds only audit/custody infrastructure, not semantic extraction repairs.
The supplemental importer now checks nested identity and gap evidence membership but cannot certify
the meaning of an anchor. Old zero-failure reports remain unchanged and must be read with that limit.

## Queue and expert review

All 50 triaged: 19 blocking manifestations, 31 nonblocking.
Categories, reasons and secondary tags appear in RIGVEDA_SEMANTIC_508_REVIEW_TRIAGE.md. None is gold.
The three engineering blocker mechanisms, not the number of affected pairs/cases, determine the gate.

## Operations and immutability

Offline batch persistence, hash verification, duplicate prevention, failure recovery, atomic writes,
aggregate regeneration and seal prerequisites are implemented in semantic/full_run.py. Actual model
dispatch and response provenance are intentionally absent and remain a B03 requirement. See
RIGVEDA_SEMANTIC_FULL_RUN_OPERATIONS.md for four-tier review, projections and runtime limitations.

Proposed plan: 24 mantras, 440 batches (last 16). ID-only draft hash `55eb8c6277eeb658131b7cdd0541914069279959d241da74b7181c42dd341673`.
Frozen-current-files draft hash `67149b2dca2c8146b5cc6d44d787f99fe76c7893a31698549b83f4f5020f65fd`. Draft is blocked, not authorization.
Prompt and V3 schema remain byte-identical. No lower deterministic layer was changed.

## Quality and Git safety

Preflight: ruff format --check (267 files), ruff check, mypy --strict (86 source files) passed;
146 semantic tests passed and one optional OpenAI SDK test skipped. The initial shell wildcard pytest
invocation did not expand on PowerShell and was corrected to a collected semantic test selection.
Final checks and audit-specific regression outcomes are recorded in readiness_quality.json after execution.
The starting workspace was extensively dirty. All pre-existing src/prompt/schema/semantic artifacts
are protected by readiness_starting_files.json; no commit, reset, stash or cleanup was performed.

## Next-session configuration

Next session is corrective engineering and bounded regression verification, not full extraction.
Deferred extraction target: `vedagraph-rigveda-semantic-luna-v3-full-1.0.0-rc1`, model gpt-5.6-luna, reasoning high, runtime CODEX_DIRECT,
24-mantra checkpoints, one packet per semantic context, 440 batches. Complete runtime/receipt freeze,
resolve the exact blockers, issue a new execution version and rerun the gate before any model dispatch.
All outputs remain LLM_EXTRACTED / MODEL_CANDIDATE, CANDIDATE / NEEDS_REVIEW, unlocked_predicates [].
