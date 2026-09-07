# Rigveda semantic predicate coverage

**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, not human-gold accuracy.**

- Current ontology: `rigveda-semantic-ontology-v1` (unchanged)
- Allowed predicates: **14**
- Predicates represented by Sol: **11** — `['DESCRIBES', 'DESCRIBES_ACTION', 'EXPRESSES', 'INVOKES', 'INVOLVES_OFFERING', 'INVOLVES_RITUAL', 'INVOLVES_SUBSTANCE', 'PRAISES', 'REFERS_TO_NATURAL_PHENOMENON', 'REFERS_TO_PLACE', 'REQUESTS']`
- Predicates absent from Sol: **3** — `['ASSOCIATED_WITH', 'CONTRASTS_WITH', 'HAS_THEME']`
- Luna predicates in this subset: `{'INVOKES': 16}`
- Full Luna pilot predicate scope remains `INVOKES` and `PRAISES` only.
- `SEMANTIC_EXTRACTION_RECALL_GAP`: **flagged**
- Ontology gaps: **8**, dominated by missing human person/role typing
  and opaque referents.
- Ontology was not changed and no predicate was unlocked.

| Predicate | Sol assertions | Luna assertions | Exact matches |
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

Recommended next step: revise the extraction prompt to ask explicitly—but conservatively—
about each whitelisted low/medium-risk family, then run a second 120-mantra pilot and
send the proposed 25-case subset to a qualified Sanskrit/Vedic expert. Do not scale to
10,552 mantras before that review.
