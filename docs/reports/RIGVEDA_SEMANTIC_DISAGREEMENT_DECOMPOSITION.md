# Rigveda semantic disagreement decomposition

**NO HUMAN GOLD EXISTS. Categories are diagnostic hypotheses, not adjudication.**

- Benchmark mantras: **120**
- Mantras with no diagnosed mismatch: **10**
- Mantras requiring decomposition: **110**
- Mantras with a contributing representation mismatch: **24**

## Primary mantra-level decomposition

- `REPRESENTATION_MISMATCH`: **0**
- `OBJECT_GRANULARITY_MISMATCH`: **6**
- `PREDICATE_MISMATCH`: **8**
- `ACTUAL_SEMANTIC_CONFLICT`: **16**
- `ONTOLOGY_GAP`: **4**
- `INSUFFICIENT_EVIDENCE`: **58**
- `UNRESOLVED_LEGACY_LABEL`: **18**

`ACTUAL_SEMANTIC_CONFLICT` means typed structures conflict after conservative
migration; only an expert can determine truth. One-sided cases are assigned to
`INSUFFICIENT_EVIDENCE` because model-model output cannot distinguish omission
from unsupported extraction. Sentence-like or coordinated legacy objects fail
closed as `UNRESOLVED_LEGACY_LABEL`.

## Cases

- `VG:RV:SAK:M01:S005:V003` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M01:S014:V004` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, GRANULARITY_DIFFERENCE, LEFT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M01:S025:V016` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S035:V005` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S036:V018` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, EXACT_CANONICAL_ENTITY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M01:S043:V006` — `UNRESOLVED_LEGACY_LABEL`; structured: UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M01:S051:V009` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, EXACT_CANONICAL_ENTITY, LEFT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M01:S058:V001` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S061:V003` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S062:V008` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S094:V013` — `OBJECT_GRANULARITY_MISMATCH`; structured: GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M01:S101:V005` — `PREDICATE_MISMATCH`; structured: PREDICATE_DIFFERENCE. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M01:S104:V005` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S127:V002` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S136:V007` — `UNRESOLVED_LEGACY_LABEL`; structured: UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M01:S148:V004` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S154:V006` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M01:S157:V005` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M01:S162:V021` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S164:V010` — `ONTOLOGY_GAP`; structured: LEFT_ONLY. The sealed Sol annotation explicitly records an ontology gap.
- `VG:RV:SAK:M01:S173:V006` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_CANONICAL_ENTITY, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M01:S179:V001` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M02:S008:V006` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M02:S017:V005` — `OBJECT_GRANULARITY_MISMATCH`; structured: GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M03:S035:V011` — `UNRESOLVED_LEGACY_LABEL`; structured: EXACT_CANONICAL_ENTITY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M04:S001:V008` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M04:S011:V006` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M04:S022:V006` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M04:S032:V015` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_CANONICAL_ENTITY, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M04:S033:V003` — `OBJECT_GRANULARITY_MISMATCH`; structured: EXACT_NORMALIZED_OBJECT, GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M04:S034:V006` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M04:S035:V009` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M05:S003:V008` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M05:S017:V001` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, EXACT_CANONICAL_ENTITY, LEFT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M05:S020:V001` — `PREDICATE_MISMATCH`; structured: PREDICATE_DIFFERENCE, RIGHT_ONLY. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M05:S029:V006` — `PREDICATE_MISMATCH`; structured: LEFT_ONLY, PREDICATE_DIFFERENCE, RIGHT_ONLY. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M05:S049:V003` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M05:S053:V016` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M05:S068:V001` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M05:S073:V006` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M05:S074:V009` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M05:S080:V002` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M06:S013:V001` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, PREDICATE_DIFFERENCE, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M06:S039:V002` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M06:S042:V004` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M06:S044:V012` — `PREDICATE_MISMATCH`; structured: GRANULARITY_DIFFERENCE, PREDICATE_DIFFERENCE. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M06:S045:V019` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M06:S068:V006` — `UNRESOLVED_LEGACY_LABEL`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M06:S069:V007` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M07:S004:V010` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_CANONICAL_ENTITY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M07:S032:V020` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M07:S044:V002` — `OBJECT_GRANULARITY_MISMATCH`; structured: GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M07:S060:V012` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M07:S077:V005` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M07:S083:V009` — `UNRESOLVED_LEGACY_LABEL`; structured: EXACT_NORMALIZED_OBJECT, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M08:S001:V017` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M08:S005:V014` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S005:V015` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M08:S006:V013` — `UNRESOLVED_LEGACY_LABEL`; structured: GRANULARITY_DIFFERENCE, LEFT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M08:S009:V012` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S010:V006` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S021:V014` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S022:V014` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M08:S026:V008` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S037:V002` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_CANONICAL_ENTITY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S043:V024` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S046:V021` — `ONTOLOGY_GAP`; structured: LEFT_ONLY, RIGHT_ONLY. The sealed Sol annotation explicitly records an ontology gap.
- `VG:RV:SAK:M08:S051:V007` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S052:V008` — `PREDICATE_MISMATCH`; structured: PREDICATE_DIFFERENCE, RIGHT_ONLY. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M08:S060:V011` — `OBJECT_GRANULARITY_MISMATCH`; structured: EXACT_CANONICAL_ENTITY, GRANULARITY_DIFFERENCE. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M08:S067:V006` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S073:V002` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M08:S080:V004` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, EXACT_CANONICAL_ENTITY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M08:S089:V005` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S093:V001` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S093:V005` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S093:V024` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M08:S096:V007` — `PREDICATE_MISMATCH`; structured: PREDICATE_DIFFERENCE, RIGHT_ONLY. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M09:S002:V008` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S004:V009` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S040:V001` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S061:V001` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S062:V003` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S063:V016` — `UNRESOLVED_LEGACY_LABEL`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M09:S066:V028` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M09:S067:V004` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M09:S068:V010` — `UNRESOLVED_LEGACY_LABEL`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M09:S074:V001` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M09:S086:V004` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S087:V009` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, PREDICATE_DIFFERENCE, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M09:S095:V004` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S104:V005` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M09:S109:V022` — `UNRESOLVED_LEGACY_LABEL`; structured: CONFLICTING_OBJECT, LEFT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M10:S010:V014` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S014:V001` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S025:V001` — `ACTUAL_SEMANTIC_CONFLICT`; structured: CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. Typed objects select conflicting heads or object families; this is a candidate real conflict, not an adjudicated truth claim.
- `VG:RV:SAK:M10:S030:V003` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M10:S039:V011` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S040:V001` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S045:V008` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S058:V012` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S085:V028` — `ONTOLOGY_GAP`; structured: RIGHT_ONLY. The sealed Sol annotation explicitly records an ontology gap.
- `VG:RV:SAK:M10:S087:V025` — `INSUFFICIENT_EVIDENCE`; structured: EXACT_CANONICAL_ENTITY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S089:V008` — `PREDICATE_MISMATCH`; structured: LEFT_ONLY, PREDICATE_DIFFERENCE, RIGHT_ONLY. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M10:S091:V003` — `PREDICATE_MISMATCH`; structured: PREDICATE_DIFFERENCE. Structured object alignment exposes a predicate-boundary disagreement.
- `VG:RV:SAK:M10:S102:V002` — `ONTOLOGY_GAP`; structured: LEFT_ONLY, RIGHT_ONLY. The sealed Sol annotation explicitly records an ontology gap.
- `VG:RV:SAK:M10:S107:V008` — `OBJECT_GRANULARITY_MISMATCH`; structured: GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. Typed heads overlap by strict component subset without equivalence.
- `VG:RV:SAK:M10:S108:V001` — `UNRESOLVED_LEGACY_LABEL`; structured: LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. At least one legacy object is coordinated, sentence-like, or unmapped.
- `VG:RV:SAK:M10:S118:V001` — `INSUFFICIENT_EVIDENCE`; structured: RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
- `VG:RV:SAK:M10:S146:V005` — `INSUFFICIENT_EVIDENCE`; structured: LEFT_ONLY, RIGHT_ONLY. One model emitted no counterpart; the stored artifacts cannot decide whether this is omission or unsupported extraction.
