# RIGVEDA semantic v3 disagreement decomposition

**NO HUMAN GOLD EXISTS. All comparison values are model-vs-model silver diagnostics, not precision, recall, accuracy, or F1.**

One primary diagnostic category is assigned per benchmark mantra. Categories describe
why two model outputs differ; they do not label either model as correct.

Distribution: `{'ACTUAL_SEMANTIC_CONFLICT_CANDIDATE': 29, 'NO_CLAIM_AGREEMENT': 7, 'OBJECT_GRANULARITY_MISMATCH': 1, 'ONE_SIDED_EXTRACTION': 64, 'REPRESENTATION_MISMATCH': 6, 'UNRESOLVED_OBJECT': 13}`.

| Category | Meaning |
|---|---|
| REPRESENTATION_MISMATCH | Same evidence-level relation is represented differently. |
| OBJECT_GRANULARITY_MISMATCH | Typed structures differ by detail or outcome granularity. |
| PREDICATE_MISMATCH | Relation family differs. |
| ACTUAL_SEMANTIC_CONFLICT_CANDIDATE | Candidate object/predicate fields conflict; expert review required. |
| ONTOLOGY_GAP | A typed referent cannot be safely modeled. |
| ONE_SIDED_EXTRACTION | Only one model emitted a relation. |
| INSUFFICIENT_EVIDENCE | Packet evidence is not sufficient to resolve the disagreement. |
| UNRESOLVED_OBJECT | An occurrence remains unresolved by deterministic structure. |

Detailed rows are stored in `v3_vs_sol_structured_comparisons.jsonl`.
