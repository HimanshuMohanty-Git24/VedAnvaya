# RIGVEDA semantic v3 type-boundary QA

**NO HUMAN GOLD EXISTS.** This report tests structural boundaries, not model correctness.

- Ritual assertions: **19**, expected object kind `RITUAL_EVENT`.
- Offering assertions: **10**, expected object kind `OFFERING_REF`.
- Substance assertions: **33**, expected object kind `SUBSTANCE_REF`.
- Natural-phenomenon assertions: **16**, expected object kind `NATURAL_PHENOMENON_REF`.
- Place assertions: **14**, expected object kind `PLACE_REF`.
- Structural cross-kind leakage: **0**.
- Devata/phenomenon identity reuse: **0**.

Result: **PASS** when both counts are zero. Semantic boundary ambiguity remains eligible
for expert review even when structure is valid.
