# Rigveda semantic normalized comparison v1

**NO HUMAN GOLD EXISTS. These are model-model diagnostics, not accuracy.** The sealed
legacy artifacts are unchanged and no model was executed.

## Historical metric retained

- Legacy exact string/signature matches: **14**
- Legacy partial matches: **34**
- Historical exact-match precision: **7.5%**
- Historical exact-match recall: **6.1%**

## Structured comparison

- Exact structured matches: **30**
  - exact canonical entity: **14**
  - exact normalized object: **16**
- Compatible matches: **0**
- Partial object overlap: **0**
- Object granularity differences: **10**
- Predicate conflicts: **10**
- Object-type conflicts: **0**
- Other conflicting objects: **19**
- Real/conflicting object total (candidate, not adjudicated): **19**
- Unresolved / one-sided / expert-required rows: **257**
- No-claim agreements: **7**
- Newly recoverable representational alignments: **26** across
  **24** mantras

Full category counts: `{'CONFLICTING_OBJECT': 19, 'EXACT_CANONICAL_ENTITY': 14, 'EXACT_NORMALIZED_OBJECT': 16, 'GRANULARITY_DIFFERENCE': 10, 'LEFT_ONLY': 97, 'NO_CLAIM_AGREEMENT': 7, 'PREDICATE_DIFFERENCE': 10, 'RIGHT_ONLY': 140, 'UNRESOLVED': 20}`.

`label_equality_signal` is recorded for audit only. It never decides exactness. No fuzzy
model or embedding was used.

## Legacy migration coverage

| Source | Assertions | Canonical refs | Normalized candidates | Unresolved legacy objects |
|---|---:|---:|---:|---:|
| Luna v1 | 16 | 16 | 0 | 0 |
| Luna v2 | 186 | 37 | 149 | 0 |
| Sol silver | 229 | 99 | 90 | 40 |

V1 kinds: `{'CANONICAL_ENTITY_REF': 16}`.

V2 kinds: `{'CANONICAL_ENTITY_REF': 37, 'EVENT': 20, 'NATURAL_PHENOMENON_REF': 16, 'OFFERING_REF': 11, 'PLACE_REF': 14, 'REQUESTED_OUTCOME': 21, 'RITUAL_EVENT': 19, 'STATE_REF': 15, 'SUBSTANCE_REF': 33}`.

Sol kinds: `{'CANONICAL_ENTITY_REF': 99, 'EVENT': 29, 'NATURAL_PHENOMENON_REF': 16, 'OFFERING_REF': 11, 'PLACE_REF': 4, 'REQUESTED_OUTCOME': 34, 'RITUAL_EVENT': 24, 'STATE_REF': 2, 'SUBSTANCE_REF': 10}`.

Migration copies concise legacy heads but does not infer event arguments, split opaque
coordinated labels, or canonicalize semantic concepts. `NORMALIZED_CANDIDATE` is an
occurrence status, not acceptance.

## Safety

`unlocked_predicates = []`. Original output files are immutable inputs. Human gold was
not opened or modified.
