# RIGVEDA semantic Luna v3 internal quality

**NO HUMAN GOLD EXISTS.** This is a v3-internal extraction report; no model comparison
source was opened when it was generated.

## Run

- Benchmark: **120** mantras, exactly **8 batches × 15**.
- Assertions: **211** (1.758/mantra).
- No-claim mantras: **28**.
- Ontology-gap objects: **29**.
- Canonical entity references: **57**.
- Non-canonical semantic object candidates: **183**.

## Predicate distribution

| Predicate | Count |
|---|---:|
| `INVOKES` | 22 |
| `PRAISES` | 7 |
| `REQUESTS` | 27 |
| `DESCRIBES` | 28 |
| `DESCRIBES_ACTION` | 20 |
| `INVOLVES_RITUAL` | 19 |
| `INVOLVES_OFFERING` | 10 |
| `INVOLVES_SUBSTANCE` | 33 |
| `REFERS_TO_NATURAL_PHENOMENON` | 16 |
| `REFERS_TO_PLACE` | 14 |
| `EXPRESSES` | 15 |
| `HAS_THEME` | 0 |
| `ASSOCIATED_WITH` | 0 |
| `CONTRASTS_WITH` | 0 |

## Object-kind distribution

| Object kind | Count |
|---|---:|
| `CANONICAL_ENTITY_REF` | 57 |
| `EVENT` | 20 |
| `NATURAL_PHENOMENON_REF` | 16 |
| `OFFERING_REF` | 10 |
| `PLACE_REF` | 14 |
| `REQUESTED_OUTCOME` | 27 |
| `RITUAL_EVENT` | 19 |
| `STATE_REF` | 15 |
| `SUBSTANCE_REF` | 33 |

Ontology gaps: `{'PATRON_ROLE_UNMODELED': 3, 'PERSON_LIKE_REFERENT_UNMODELED': 26}`.

## Explicitness and validity

- EXPLICIT: **211**.
- STRONG_INFERENCE: **0**.
- INTERPRETIVE emitted: **0** (refused by the v3 contract).
- Validator rejections: **0**.
- Evidence failures: **0**.
- Average evidence anchors/assertion: **1.000**.

## Representation QA

- Sentence-length display labels (>8 words): **0**.
- Coordinated normalized heads: **0**.
- REQUESTS assertions: **27**; request-structure violations: **0**.
- Natural-phenomenon objects carrying canonical entity ids: **0** (must be 0).
- Ritual/offering/substance/place structural boundary violations: **0** (must be 0).

No predicate is unlocked: `unlocked_predicates = []`.
