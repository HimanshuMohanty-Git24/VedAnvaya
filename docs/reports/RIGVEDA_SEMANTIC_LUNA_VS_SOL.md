# Rigveda semantic Luna vs Sol

**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, not human-gold accuracy.**

## Agreement summary

- Luna assertions in the 120-mantra subset: **16**
- Sol assertions: **229**
- Exact matches: **11**
- Partial matches: **1**
- Silver agreement precision (exact / Luna): **68.750%**
- Silver agreement recall (exact / Sol): **4.803%**
- Relation-set agreement: **9/120**
- No-claim agreement: **9/104** union cases (8.654%)
- Entity agreement among Luna assertions: **16/16** (100.000%)
- Evidence agreement: **12/16** (75.000%)
- Disagreement rate across comparison rows: **91.597%**
- Comparison categories: `{'LUNA_MISSED_RELATION': 210, 'MATCH': 11, 'NO_CLAIM_AGREEMENT': 9, 'PARTIAL_MATCH': 1, 'SOL_ONLY_RELATION': 3, 'WRONG_PREDICATE': 4}`

## Predicate-by-predicate agreement

| Predicate | Sol | Luna | Exact match |
|---|---:|---:|---:|
| `ASSOCIATED_WITH` | 0 | 0 | 0 |
| `CONTRASTS_WITH` | 0 | 0 | 0 |
| `DESCRIBES` | 23 | 0 | 0 |
| `DESCRIBES_ACTION` | 29 | 0 | 0 |
| `EXPRESSES` | 2 | 0 | 0 |
| `HAS_THEME` | 0 | 0 | 0 |
| `INVOKES` | 45 | 16 | 11 |
| `INVOLVES_OFFERING` | 11 | 0 | 0 |
| `INVOLVES_RITUAL` | 24 | 0 | 0 |
| `INVOLVES_SUBSTANCE` | 10 | 0 | 0 |
| `PRAISES` | 31 | 0 | 0 |
| `REFERS_TO_NATURAL_PHENOMENON` | 16 | 0 | 0 |
| `REFERS_TO_PLACE` | 4 | 0 | 0 |
| `REQUESTS` | 34 | 0 | 0 |

## Evidence findings

- Evidence assessments: `{'AMBIGUOUS': 4, 'SUFFICIENT': 12}`
- Missing cited token IDs: **0**
- Missing translation IDs: **0**
- Metadata-only Luna support: **0**
- Textual-overreach findings: **0**
- Ambiguous relation support: **4**

## Safety

`unlocked_predicates = []`. Silver agreement does not authorize `AUTO_ACCEPTED` or
`HUMAN_ACCEPTED`; all semantic outputs remain candidate/review material.
