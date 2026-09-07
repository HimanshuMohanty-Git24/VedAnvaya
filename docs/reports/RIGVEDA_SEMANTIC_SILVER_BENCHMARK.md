# Rigveda semantic silver benchmark

**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, not human-gold accuracy.**

## Design and scope

- Run: `vedagraph-rigveda-semantic-silver-sol-v1`
- Provenance: `MODEL_REVIEWED_SILVER`
- Reviewer: `gpt-5.6-sol` via `CODEX_DIRECT`, reasoning effort `high`
- Exact selected benchmark mantras: **120**
- Batch plan: **8 batches x 15**, persisted and validated after each batch
- Human gold status: `UNANNOTATED`
- Unlocked predicates: `[]`
- Silver assertions remain review evidence; they authorize no accepted semantic edge.

## Independent results

- Sol no-claim count: **9**
- Sol assertion count: **229**
- Sol entities used: **210**
- Ontology gaps recorded: **8**
- Predicate distribution: `{'DESCRIBES': 23, 'DESCRIBES_ACTION': 29, 'EXPRESSES': 2, 'INVOKES': 45, 'INVOLVES_OFFERING': 11, 'INVOLVES_RITUAL': 24, 'INVOLVES_SUBSTANCE': 10, 'PRAISES': 31, 'REFERS_TO_NATURAL_PHENOMENON': 16, 'REFERS_TO_PLACE': 4, 'REQUESTS': 34}`

## Blind-review verification

The review loader accepted only files named `evidence.jsonl`; it rejected model-output
field names. All 120 rows were persisted before `blind_review_seal.json` was written.
The comparison entry point verified the selected-ID hash, the complete annotation-file
hash, every annotation hash, and every EvidencePacket hash before reading Luna output.
The seal records the later reveal separately. Human-gold files were not inputs to the
judgment stage and were not modified.

## Interpretation

This benchmark is suitable for prompt/ontology debugging and audit triage. It is not a
substitute for qualified Sanskrit/Vedic review and must never be reported as precision,
recall, or F1 against human truth.
