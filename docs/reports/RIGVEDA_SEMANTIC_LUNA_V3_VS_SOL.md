# RIGVEDA semantic Luna v3 vs Sol silver

**NO HUMAN GOLD EXISTS. All comparison values are model-vs-model silver diagnostics, not precision, recall, accuracy, or F1.**

The sealed structured comparator aligns predicates and typed object fields. It does not
require display-label equality and uses no fuzzy similarity.

- V3 assertions: **211**; Sol assertions: **229**.
- Structured comparison categories: `{'CONFLICTING_OBJECT': 18, 'EXACT_CANONICAL_ENTITY': 19, 'EXACT_NORMALIZED_OBJECT': 16, 'GRANULARITY_DIFFERENCE': 10, 'LEFT_ONLY': 116, 'NO_CLAIM_AGREEMENT': 7, 'PREDICATE_DIFFERENCE': 12, 'RIGHT_ONLY': 134, 'UNRESOLVED': 20}`.
- EXACT_CANONICAL_ENTITY: **19**.
- EXACT_NORMALIZED_OBJECT: **16**.
- COMPATIBLE_OBJECT: **0**.
- PARTIAL_OBJECT_OVERLAP: **0**.
- GRANULARITY_DIFFERENCE: **10**.
- PREDICATE_DIFFERENCE: **12**.
- OBJECT_TYPE_DIFFERENCE: **0**.
- CONFLICTING_OBJECT: **18**.
- UNRESOLVED: **20**.
- LEFT_ONLY: **116**; RIGHT_ONLY: **134**.
- NO_CLAIM_AGREEMENT: **7**.

Legacy string-comparator categories are preserved for historical reference only: `{'DISAGREEMENT_REQUIRES_EXPERT': 94, 'LUNA_MISSED_RELATION': 136, 'MATCH': 14, 'NO_CLAIM_AGREEMENT': 7, 'OVERINTERPRETATION': 2, 'PARTIAL_MATCH': 34, 'SOL_ONLY_RELATION': 3, 'WRONG_ENTITY': 31, 'WRONG_PREDICATE': 11}`.

These values are model-vs-model silver diagnostics. They do not establish correctness,
human precision/recall, or predicate acceptance. `unlocked_predicates = []`.
