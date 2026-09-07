# Rigveda semantic Luna v2 — 120-mantra pilot

**NO HUMAN GOLD EXISTS. All agreement numbers below are model-vs-model silver diagnostics, not human accuracy.**

## Silver agreement summary

- V2 assertions: **186**; Sol assertions: **229**.
- Exact relation matches: **14**.
- Partial matches: **34**.
- Silver agreement precision (exact / Luna): **7.5%**.
- Silver agreement recall (exact / Sol): **6.1%**.
- Relation-set agreement: **10/120**.
- No-claim agreement: **7/33** (21.2%).
- Entity compatibility: **59/186** (31.7%).
- Evidence agreement: **48/186** (25.8%).
- Comparison categories: `{'DISAGREEMENT_REQUIRES_EXPERT': 94, 'LUNA_MISSED_RELATION': 136, 'MATCH': 14, 'NO_CLAIM_AGREEMENT': 7, 'OVERINTERPRETATION': 2, 'PARTIAL_MATCH': 34, 'SOL_ONLY_RELATION': 3, 'WRONG_ENTITY': 31, 'WRONG_PREDICATE': 11}`.

## Predicate agreement

| Predicate | Sol | Luna v2 | Exact match |
|---|---:|---:|---:|
| `ASSOCIATED_WITH` | 0 | 0 | 0 |
| `CONTRASTS_WITH` | 0 | 0 | 0 |
| `DESCRIBES` | 23 | 22 | 5 |
| `DESCRIBES_ACTION` | 29 | 20 | 0 |
| `EXPRESSES` | 2 | 15 | 0 |
| `HAS_THEME` | 0 | 0 | 0 |
| `INVOKES` | 45 | 13 | 9 |
| `INVOLVES_OFFERING` | 11 | 11 | 0 |
| `INVOLVES_RITUAL` | 24 | 19 | 0 |
| `INVOLVES_SUBSTANCE` | 10 | 33 | 0 |
| `PRAISES` | 31 | 2 | 0 |
| `REFERS_TO_NATURAL_PHENOMENON` | 16 | 16 | 0 |
| `REFERS_TO_PLACE` | 4 | 14 | 0 |
| `REQUESTS` | 34 | 21 | 0 |

## Evidence assessments

`{'AMBIGUOUS': 138, 'SUFFICIENT': 48}`. Missing-token and missing-translation findings are
reported by the validator and remain zero for v2.

## Safety

These are silver comparisons only. `unlocked_predicates = []`; agreement cannot authorize
automatic acceptance or human acceptance.
