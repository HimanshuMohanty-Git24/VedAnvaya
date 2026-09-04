# Rigveda semantic pilot — Codex/Luna direct extraction

Run ID: `vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1`

The 508-mantra pilot was processed from deterministic EvidencePackets in 22 batches.
The extractor runtime was `CODEX_DIRECT`: the Codex/Luna agent authored structured
payloads locally, and Python only parsed, validated, routed, and reported them.

## Results

- Pilot mantras: **508**
- Successfully processed: **508**
- No-claim mantras: **435**
- Candidate semantic entities: **0**
- Candidate semantic assertions: **76**
- Structurally valid: **76**
- Validation rejected: **0**
- Needs review: **76**
- Auto-accepted: **0**
- Assertions per mantra: **0.150**
- Entities per mantra: **0.000**

All valid candidates are review-only because `unlocked_predicates=[]` and the gold
status is `UNANNOTATED`. No precision percentage is claimed.

## Semantic distribution

Predicate distribution:

- `INVOKES`: 68
- `PRAISES`: 8

Node-type distribution:

- `CANONICAL_ENTITY`: 76

Explicitness: `{'EXPLICIT': 76}`

Evidence-linkage failures: **0**

Fabricated token references: **0**

Unsupported claims detected by deterministic validator: **0**

Traditional-metadata context conflicts flagged for review: **25**

## Batch results

- Batch 001: 24 mantras, 3 candidates, 0 rejected, 3 needs review
- Batch 002: 24 mantras, 0 candidates, 0 rejected, 0 needs review
- Batch 003: 24 mantras, 4 candidates, 0 rejected, 4 needs review
- Batch 004: 24 mantras, 6 candidates, 0 rejected, 6 needs review
- Batch 005: 24 mantras, 11 candidates, 0 rejected, 11 needs review
- Batch 006: 24 mantras, 5 candidates, 0 rejected, 5 needs review
- Batch 007: 24 mantras, 3 candidates, 0 rejected, 3 needs review
- Batch 008: 24 mantras, 4 candidates, 0 rejected, 4 needs review
- Batch 009: 24 mantras, 2 candidates, 0 rejected, 2 needs review
- Batch 010: 24 mantras, 6 candidates, 0 rejected, 6 needs review
- Batch 011: 24 mantras, 3 candidates, 0 rejected, 3 needs review
- Batch 012: 24 mantras, 8 candidates, 0 rejected, 8 needs review
- Batch 013: 24 mantras, 1 candidates, 0 rejected, 1 needs review
- Batch 014: 24 mantras, 0 candidates, 0 rejected, 0 needs review
- Batch 015: 24 mantras, 6 candidates, 0 rejected, 6 needs review
- Batch 016: 24 mantras, 2 candidates, 0 rejected, 2 needs review
- Batch 017: 24 mantras, 1 candidates, 0 rejected, 1 needs review
- Batch 018: 24 mantras, 2 candidates, 0 rejected, 2 needs review
- Batch 019: 24 mantras, 5 candidates, 0 rejected, 5 needs review
- Batch 020: 24 mantras, 3 candidates, 0 rejected, 3 needs review
- Batch 021: 24 mantras, 1 candidates, 0 rejected, 1 needs review
- Batch 022: 4 mantras, 0 candidates, 0 rejected, 0 needs review

## Spend and readiness

- API calls: **0**
- Direct API cost: **$0**
- Gold status: **UNANNOTATED**
- Final state: `RIGVEDA_SEMANTIC_PILOT_COMPLETE_AWAITING_HUMAN_GOLD`

This pilot does not authorize semantic extraction over the remaining 10,044 mantras.
