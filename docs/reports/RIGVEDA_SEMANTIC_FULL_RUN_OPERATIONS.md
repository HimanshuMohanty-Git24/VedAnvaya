# Full Rigveda V3 operations — blocked draft

Engineering diagnostics, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was performed in this audit.

## ROUGH ENGINEERING PROJECTIONS

| Measure | Observed / 508 | Linear capacity analogue / 10,552 |
| --- | --- | --- |
| Candidate assertions | 917 | 19048 |
| No-claim mantras | 143 | 2970 |
| Ontology-gap objects | 70 | 1454 |
| Canonical-reference assertion objects (not unique entities) | 256 | 5318 |
| Top-50 queue capacity analogue | 50 | 1039 |

Multiplier 10,552/508 = 20.771654. These are capacity scenarios, not statistical predictions.
The pilot is selected, includes correlated parallels and uses a deterministic heuristic producer;
an actual model run may differ substantially. No confidence interval or corpus semantic truth is claimed.
The top-50 queue is capped by construction, so about 1,039 is a review-capacity analogue, not a predicted
flag prevalence. Keep the complete uncapped risk ledger; deduplicate overlapping flags. A conservative
storage/workflow upper bound is 10,552 mantra-level review entries, with potentially multiple reasons.

## Review policy

1. Tier 1: validate every packet and payload, including gap anchors and all nested canonical IDs;
   reject schema/ID/evidence failures, duplicate IDs, canonical contradictions and structural type
   leakage. All rejected batches remain FAILED; final seal requires zero unresolved failures.
   Deterministic validation cannot establish semantic entailment.
2. Tier 2: retain all risk flags: gaps, opaque referents, exact/near disagreements, predicates with
   fewer than 10 full-run occurrences, heads occurring once, more than 6 assertions per mantra,
   four or more predicate families, and rare family combinations (fewer than 5 occurrences).
   Compute rarity after aggregation; do not bias extraction from previous semantic results.
   Deduplicate by mantra then reason, preserve every underlying assertion/pair ID, and stratify
   by mandala, predicate, object kind and gap code. Never silently drop overflow beyond top 50.
3. Tier 3: optional independent Sol/high review of at most 200 deterministic targeted cases plus
   50 hash-selected ordinary cases as an initial diagnostic budget. Never all 10,552. Sample by
   ascending SHA256(run_id + passage_id) within strata; persist IDs and selection-policy hash.
   Escalate repeated shared failure mechanisms, not isolated interpretive disagreements.
4. Tier 4: domain experts receive high-value unresolved identity/philology disputes only (initial
   budget 20). Review budgets are operational choices, not acceptance thresholds or a prerequisite
   for producing candidates. Gold requires actual human annotation, outside this audit.

## Freeze before any future extraction

Draft file: docs/manifests/rigveda_semantic_full_run_freeze.draft.json.
It pins corpus/traditional/lexical manifests AND their materialized JSON/JSONL files, morphology
tokens plus lexical manifest source snapshot hashes, prompt, schema, both ontologies, explicitness
policy (object ontology and prompt), normalization, EvidencePacket schema/model/builder, typed models,
semantic implementation and validation, operations code, project dependencies and exact full ID set.
The source snapshot hashes are the ten VEDAWEB snapshot IDs in the pinned lexical manifest.
Before launch, add the verified Codex build/model execution receipt format and exact installed
dependency lock; current draft explicitly records host build UNVERIFIED. Model alias behavior cannot
be cryptographically pinned: preserve returned model/build metadata and each raw response receipt.

Any changed frozen file, model, reasoning, runtime, source or passage-ID hash requires a NEW extraction
version/run ID and plan. Do not resume across drift; a draft is not an executable authorization.
Full ID set: 10,552 unique mantra IDs enumerated directly from canonical passages, not fabricated
range arithmetic. No full-corpus EvidencePackets were built and no candidates were extracted.

Freeze hash: `67149b2dca2c8146b5cc6d44d787f99fe76c7893a31698549b83f4f5020f65fd`.
ID-list hash: `5270614db1fd2b68642c535e0b3f81fb2dc471902674a8063acd26ca38861da2`.
Plan hash: `55eb8c6277eeb658131b7cdd0541914069279959d241da74b7181c42dd341673`.

## Batch plan and checkpoint custody

Recommend **24 mantras**, **440 batches**: 439 x 24 + 16. Lexicographically ordered fixed-width
canonical IDs, consecutive slices; the entire plan includes freeze hash and has a canonical JSON hash.
One EvidencePacket per model context is preferred, with 24 as persistence/scheduling unit. Never
hundreds of packets per context. Keep semantic extraction packet-local even if a batch dispatches
several independent calls. Do not carry previous semantic outputs into the next packet's context.

src/vedagraph/semantic/full_run.py provides offline custody with PENDING, EXTRACTED, VALIDATED,
FAILED and SEALED checkpoints. Each has run_id, batch_id, mantra_ids, packet_hashes, plan_hash,
output_hash, validator_result and completed_timestamp. Packet hashes are recomputed before staging
and resume. Full packet hashes are accumulated per staged batch and included in the final seal;
the preparation sources are frozen first. Output files are atomically replaced only within a
single-writer transaction; flush/fsync precedes replace. The 508 runner lacked verified skipping,
atomic writes and a resumable state machine, and has deliberately not been modified or reused.

Workflow for a future separately authorized execution adapter:

1. Verify the Freeze against on-disk inputs and canonical full IDs before dispatch and each resume.
2. Construct BatchStore from the exact hashed Plan. prepare(batch_id, packets) freezes packet
   hashes and rejects reordered, missing, duplicate or mutated input. Verify all completed outputs
   with recover before deciding what needs work. A live single-writer lock prevents overlap.
3. Only PENDING with no output is eligible for model dispatch. Persist actual response receipts
   in the future execution adapter; the store accepts already-authored payloads, never invokes Luna.
4. commit writes output, then EXTRACTED checkpoint, then validates. It refuses duplicate commits.
   An output/checkpoint interruption is recovered by re-reading and validating the existing output,
   without re-extraction. FAILED attempts require explicit retry_failed; prior output is archived by
   content hash. Failed attempts must never be silently overwritten.
5. Completed batches are rehashed and revalidated. Mismatch fails closed. A stale writer lock requires
   operator confirmation that the process is dead before manual removal; no time-based automatic theft.
6. regenerate rebuilds aggregate data from validated batch files without extraction. Reports can read
   that aggregate independently. seal verifies the full freeze/IDs, every batch, all hashes and duplicate
   IDs, then writes a full-run output seal and marks checkpoints SEALED. Candidate-only fields are fixed.

Local fsync/atomic replace protects process interruption; network-filesystem durability and power-loss
recovery are not certified. A process killed after a model response but before local receipt persistence
cannot promise exactly-once remote execution: the future adapter needs provider request IDs/idempotency
where available. Do not claim the offline store solves remote execution. The live adapter/provenance
remains blocked under B03; existing regex producer must not be connected as a substitute.

## Validation and reporting cadence

Per packet: strict V3 shape and complete evidence/identity membership checks. Per batch: coverage,
candidate-only status, no unlocking, raw response receipt, hashes and fourteen-family trace verification.
Every 10 validated batches: regenerate counts, failures and risk metrics without showing prior semantic
outputs to the extractor. Pause on any repeated relation-binding failure or evidence corruption.
At completion: 10,552 exact unique IDs, no unresolved failed batches, matching freeze, sealed aggregate,
distributions, no-claim/gap inventories, all deterministic parallel comparisons and uncapped risk ledger.
No full candidate enters canonical knowledge, HUMAN_GOLD or SOURCE_EXPLICIT automatically.

## Next session

Do not execute the full run. Resolve B01/B02/B03, wire and verify the actual model adapter and complete
runtime/receipt pinning in a new execution contract. Retain frozen V3 prompt/schema unless a separate
architecture finding requires change. Re-run readiness after bounded regression verification.
The deferred target is Luna gpt-5.6-luna, high reasoning, CODEX_DIRECT, packet-local contexts,
24-mantra checkpoints, 440 batches, candidate-only. `vedagraph-rigveda-semantic-luna-v3-full-1.0.0-rc1` is a proposed unused ID; execution
changes before sealing the draft require a freshly named version, never reuse pilot identity.
