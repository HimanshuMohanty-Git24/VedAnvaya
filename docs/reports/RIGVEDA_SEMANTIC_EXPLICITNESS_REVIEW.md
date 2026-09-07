# Rigveda semantic explicitness review

**Policy analysis only. Sol was not used as ground truth and legacy assertions were
not relabelled.**

V2 stored explicitness: `{'EXPLICIT': 15, 'STRONG_INFERENCE': 171}`.

## Diagnosis

- `SHOULD_HAVE_BEEN_EXPLICIT`: **144**
- `CORRECTLY_STRONG_INFERENCE`: **22**
- `TOO_INTERPRETIVE_TO_EMIT`: **6**
- `SCHEMA_AMBIGUITY`: **14**

The dominant mechanical cause is the v2 instruction: a claim entailed mainly by a
supplied translation was labelled `STRONG_INFERENCE`. Under the revised policy, a
supplied translation is direct evidence. Inference depends on the reasoning step,
not the language of the evidence.

## Predicate breakdown

| Predicate | Should explicit | Correctly strong | Too interpretive | Schema ambiguity |
|---|---:|---:|---:|---:|
| `DESCRIBES` | 0 | 22 | 0 | 0 |
| `DESCRIBES_ACTION` | 20 | 0 | 0 | 0 |
| `EXPRESSES` | 9 | 0 | 6 | 0 |
| `INVOKES` | 13 | 0 | 0 | 0 |
| `INVOLVES_OFFERING` | 11 | 0 | 0 | 0 |
| `INVOLVES_RITUAL` | 19 | 0 | 0 | 0 |
| `INVOLVES_SUBSTANCE` | 33 | 0 | 0 | 0 |
| `PRAISES` | 2 | 0 | 0 | 0 |
| `REFERS_TO_NATURAL_PHENOMENON` | 16 | 0 | 0 | 0 |
| `REFERS_TO_PLACE` | 0 | 0 | 0 | 14 |
| `REQUESTS` | 21 | 0 | 0 | 0 |

## Revised future-v3 policy

- `EXPLICIT`: relation and target are directly supportable from supplied Sanskrit
  or translation evidence.
- `STRONG_INFERENCE`: exactly one limited, named inferential step is required.
- Broad thematic, symbolic, theological, or narrative interpretation: do not emit.
- The target distribution should be dominated by `EXPLICIT`; no quota or artificial
  relabelling is permitted.

The row-level audit is stored locally as `explicitness_review.jsonl` and keeps every
legacy value unchanged.
