# RIGVEDA semantic Luna v2 vs v3

**NO HUMAN GOLD EXISTS. All comparison values are model-vs-model silver diagnostics, not precision, recall, accuracy, or F1.**

The v3 seal was verified before v2 or Sol data was opened. Both runs use the same 120
selected ids. v3 uses native typed occurrence objects; v2 is migrated offline solely for
diagnostic comparison.

| Measure | V2 | V3 |
|---|---:|---:|
| Assertions | 186 | 211 |
| No-claim mantras | 31 | 28 |
| Canonical entity objects | 37 | 57 |
| Typed event objects | 20 | 20 |
| EXPLICIT | 15 | 211 |
| STRONG_INFERENCE | 171 | 0 |

V2→V3 structured comparison categories: `{'CONFLICTING_OBJECT': 2, 'EXACT_CANONICAL_ENTITY': 27, 'LEFT_ONLY': 28, 'NO_CLAIM_AGREEMENT': 28, 'PREDICATE_DIFFERENCE': 7, 'RIGHT_ONLY': 3, 'UNRESOLVED': 147}`.

Relation-set differences using typed signatures (not labels): **V2-only 157**, **V3-only 182**. These are diagnostic differences, not truth judgements.

The v3 run keeps `unlocked_predicates = []`.
