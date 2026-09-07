# Rigveda semantic Luna v2 — 120-mantra pilot

**NO HUMAN GOLD EXISTS. All agreement numbers below are model-vs-model silver diagnostics, not human accuracy.**

## Counts

| Measure | v1 | v2 |
|---|---:|---:|
| Assertions | 16 | 186 |
| No-claim mantras | 104 | 31 |
| Semantic entity candidates | 0 | 48 |
| Assertions/mantra | 0.133 | 1.550 |
| Validator rejection rate | 0/16 | 0/186 |
| Evidence error rate | 0/16 | 0/186 |

## Coverage

- V1 predicates: `{'INVOKES': 16}`
- V2 predicates: `{'DESCRIBES': 22, 'DESCRIBES_ACTION': 20, 'EXPRESSES': 15, 'INVOKES': 13, 'INVOLVES_OFFERING': 11, 'INVOLVES_RITUAL': 19, 'INVOLVES_SUBSTANCE': 33, 'PRAISES': 2, 'REFERS_TO_NATURAL_PHENOMENON': 16, 'REFERS_TO_PLACE': 14, 'REQUESTS': 21}`
- V1 node types: `{'CANONICAL_ENTITY': 16}`
- V2 node types: `{'ACTION': 20, 'CANONICAL_ENTITY': 37, 'CONCEPT': 15, 'NATURAL_PHENOMENON': 16, 'OFFERING': 11, 'PLACE': 14, 'RITUAL': 19, 'STATE': 21, 'SUBSTANCE': 33}`
- V1 explicitness: `{'EXPLICIT': 16}`
- V2 explicitness: `{'EXPLICIT': 15, 'STRONG_INFERENCE': 171}`
- Exact relation-set agreement per mantra: **35/120**.
- V2 added **174** normalized relation keys and retained **12** v1/v2 relation keys; it dropped **4** v1 keys.

The v2 increase is evaluated for evidence validity and ontology discipline, not for
matching a target assertion count.
