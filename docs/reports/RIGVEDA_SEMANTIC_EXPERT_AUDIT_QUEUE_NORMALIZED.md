# Rigveda semantic expert audit queue — normalized v1

This refines the historical 25-case v2 queue after structured decomposition. It is
a proposed expert-review package, not human gold. Pure string/order matches and
known representational-only cases are excluded.

Selected cases: **24**.

1. `VG:RV:SAK:M10:S030:V003` — LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
2. `VG:RV:SAK:M07:S083:V009` — EXACT_NORMALIZED_OBJECT, RIGHT_ONLY, UNRESOLVED. **Question:** Does the verse explicitly invoke, praise, or merely describe the referent?
3. `VG:RV:SAK:M05:S080:V002` — EXACT_NORMALIZED_OBJECT, RIGHT_ONLY. **Question:** Does the phrase explicitly refer to a natural phenomenon, a deity/personified entity, or both as distinct supported relations?
4. `VG:RV:SAK:M01:S154:V006` — CONFLICTING_OBJECT, RIGHT_ONLY. **Question:** Does the phrase denote an explicit place, only a spatial/cosmological description, or an opaque referent?
5. `VG:RV:SAK:M09:S087:V009` — CONFLICTING_OBJECT, LEFT_ONLY, PREDICATE_DIFFERENCE, RIGHT_ONLY. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
6. `VG:RV:SAK:M04:S032:V015` — EXACT_CANONICAL_ENTITY, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the verse explicitly invoke, praise, or merely describe the referent?
7. `VG:RV:SAK:M02:S008:V006` — LEFT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
8. `VG:RV:SAK:M06:S068:V006` — CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
9. `VG:RV:SAK:M03:S035:V011` — EXACT_CANONICAL_ENTITY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the verse explicitly invoke, praise, or merely describe the referent?
10. `VG:RV:SAK:M10:S085:V028` — RIGHT_ONLY. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
11. `VG:RV:SAK:M01:S164:V010` — LEFT_ONLY. **Question:** Does the phrase denote an explicit place, only a spatial/cosmological description, or an opaque referent?
12. `VG:RV:SAK:M09:S068:V010` — CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
13. `VG:RV:SAK:M08:S001:V017` — LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
14. `VG:RV:SAK:M10:S108:V001` — LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
15. `VG:RV:SAK:M09:S074:V001` — CONFLICTING_OBJECT, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
16. `VG:RV:SAK:M08:S046:V021` — LEFT_ONLY, RIGHT_ONLY. **Question:** Does the phrase explicitly refer to a natural phenomenon, a deity/personified entity, or both as distinct supported relations?
17. `VG:RV:SAK:M04:S035:V009` — CONFLICTING_OBJECT, GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
18. `VG:RV:SAK:M09:S104:V005` — LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
19. `VG:RV:SAK:M04:S022:V006` — LEFT_ONLY, RIGHT_ONLY. **Question:** Does the phrase explicitly refer to a natural phenomenon, a deity/personified entity, or both as distinct supported relations?
20. `VG:RV:SAK:M01:S094:V013` — GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
21. `VG:RV:SAK:M09:S063:V016` — EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY, UNRESOLVED. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
22. `VG:RV:SAK:M04:S033:V003` — EXACT_NORMALIZED_OBJECT, GRANULARITY_DIFFERENCE, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, an offering role, a substance, or more than one of these?
23. `VG:RV:SAK:M04:S034:V006` — CONFLICTING_OBJECT, EXACT_NORMALIZED_OBJECT, LEFT_ONLY, RIGHT_ONLY. **Question:** Does the evidenced phrase denote the ritual action, the offered item in its offering role, the physical substance, or more than one independently?
24. `VG:RV:SAK:M10:S102:V002` — LEFT_ONLY, RIGHT_ONLY. **Question:** Does the phrase explicitly refer to a natural phenomenon, a deity/personified entity, or both as distinct supported relations?

The local `expert_review_package.jsonl` supplies citation, rights-bounded Sanskrit
and translation, traditional metadata, deterministic lexical tokens/mentions, both
structured interpretations, and the domain question. It never asks which model is
correct. No expert review was sought or fabricated.
