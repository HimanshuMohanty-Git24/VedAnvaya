# Rigveda semantic expert audit queue

**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, not human-gold accuracy.**

This is a proposed expert-audit queue, not human gold. The configuration contains
**25** IDs selected to maximize disagreement, predicate, evidence,
ontology-gap, and Maṇḍala coverage. The 20 highest-value cases are summarized here
without bulk verse text.

1. `VG:RV:SAK:M10:S030:V003` — predicates `INVOLVES_OFFERING, INVOLVES_RITUAL, INVOLVES_SUBSTANCE, REFERS_TO_PLACE`; entities `oblations, reservoir, somaḥ, worship and Soma pressing at the reservoir`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
2. `VG:RV:SAK:M07:S083:V009` — predicates `DESCRIBES_ACTION, INVOKES, PRAISES, REQUESTS`; entities `destroying Vrtras and maintaining holy laws, indrāvaruṇau, protection`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
3. `VG:RV:SAK:M05:S080:V002` — predicates `DESCRIBES, REFERS_TO_NATURAL_PHENOMENON`; entities `dawn, uṣāḥ`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
4. `VG:RV:SAK:M01:S154:V006` — predicates `EXPRESSES, REFERS_TO_PLACE`; entities `desire to reach the dwelling, the widely-striding Bull's sublimest mansion`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
5. `VG:RV:SAK:M09:S068:V010` — predicates `INVOKES, INVOLVES_RITUAL, REQUESTS`; entities `Soma pouring, dyāvāpṛthivyau, pavamānaḥ somaḥ, somaḥ, vigour and heroic riches`; categories `LUNA_MISSED_RELATION, PARTIAL_MATCH`; evidence `SUFFICIENT`. Review value: tests conservative-recall policy.
6. `VG:RV:SAK:M08:S046:V027` — predicates `none`; entities `none`; categories `NO_CLAIM_AGREEMENT`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence.
7. `VG:RV:SAK:M06:S013:V001` — predicates `INVOKES, PRAISES, REFERS_TO_NATURAL_PHENOMENON`; entities `agniḥ, rain and flowing waters`; categories `LUNA_MISSED_RELATION, WRONG_PREDICATE`; evidence `AMBIGUOUS`. Review value: tests conservative-recall policy, direct model disagreement.
8. `VG:RV:SAK:M03:S035:V011` — predicates `DESCRIBES_ACTION, INVOKES, PRAISES`; entities `indraḥ, slaying the Vrtras and gathering riches`; categories `LUNA_MISSED_RELATION, MATCH`; evidence `SUFFICIENT`. Review value: tests conservative-recall policy.
9. `VG:RV:SAK:M04:S034:V006` — predicates `INVOKES, INVOLVES_OFFERING, INVOLVES_RITUAL, INVOLVES_SUBSTANCE`; entities `meath, meath offered for drinking, sacrifice, ṛbhavaḥ`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
10. `VG:RV:SAK:M02:S017:V005` — predicates `DESCRIBES_ACTION, REFERS_TO_NATURAL_PHENOMENON`; entities `downward-rushing waters, stabilizing hills, earth, and heaven and directing waters`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
11. `VG:RV:SAK:M10:S085:V028` — predicates `DESCRIBES_ACTION, INVOLVES_RITUAL`; entities `binding the husband in bonds, marriage rite`; categories `LUNA_MISSED_RELATION, SOL_ONLY_RELATION`; evidence `packet-only`. Review value: ontology gap, tests conservative-recall policy.
12. `VG:RV:SAK:M08:S046:V021` — predicates `REFERS_TO_NATURAL_PHENOMENON`; entities `morning dawn`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence, tests conservative-recall policy.
13. `VG:RV:SAK:M09:S063:V016` — predicates `INVOKES, INVOLVES_RITUAL, INVOLVES_SUBSTANCE, REQUESTS`; entities `flowing to the sieve, pavamānaḥ somaḥ, somaḥ, wealth`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
14. `VG:RV:SAK:M10:S102:V002` — predicates `DESCRIBES_ACTION`; entities `Mudgalani winning the chariot battle prize`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: ontology gap, tests conservative-recall policy.
15. `VG:RV:SAK:M07:S101:V003` — predicates `none`; entities `none`; categories `NO_CLAIM_AGREEMENT`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence.
16. `VG:RV:SAK:M06:S075:V009` — predicates `none`; entities `none`; categories `NO_CLAIM_AGREEMENT`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence.
17. `VG:RV:SAK:M01:S164:V010` — predicates `none`; entities `none`; categories `NO_CLAIM_AGREEMENT`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence.
18. `VG:RV:SAK:M01:S122:V008` — predicates `none`; entities `none`; categories `NO_CLAIM_AGREEMENT`; evidence `packet-only`. Review value: ontology gap, ambiguous packet evidence.
19. `VG:RV:SAK:M10:S107:V008` — predicates `DESCRIBES, INVOLVES_RITUAL, PRAISES`; entities `dakṣiṇā, sacrificial guerdon`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.
20. `VG:RV:SAK:M10:S025:V001` — predicates `INVOKES, INVOLVES_SUBSTANCE, REQUESTS`; entities `a good mind, energy, and mental power, somaḥ, sweet juice`; categories `LUNA_MISSED_RELATION`; evidence `packet-only`. Review value: tests conservative-recall policy.

The expert should adjudicate these packet-bounded claims; they should not be asked to
annotate all 120 mantras from scratch.
