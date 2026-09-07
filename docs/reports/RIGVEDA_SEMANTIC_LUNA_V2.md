# Rigveda semantic Luna v2 — 120-mantra pilot

**NO HUMAN GOLD EXISTS. All agreement numbers below are model-vs-model silver diagnostics, not human accuracy.**

## Scope and starting health

- Run: `vedagraph-rigveda-semantic-luna-v2-120`
- Benchmark: **120** mantras, exactly 8 batches x 15.
- Starting v1 diagnostic supplied for this pilot: 16 assertions, all `INVOKES`, with a documented semantic extraction recall gap against Sol silver. This is a model-vs-model diagnostic.
- Human gold status: `UNANNOTATED`; no human gold was read or modified.
- No 508-mantra or full 10,552-mantra run was performed.

## V2 prompt changes

V2 replaces the single-safest-relation instruction with an explicit independent checklist
covering all 14 allowed predicate families. It separates `REQUESTS` from `INVOKES`,
`PRAISES` from factual `DESCRIBES`, and ritual/ offering/ substance layers; permits
packet-supported `SemanticEntityCandidate` rows; keeps canonical reuse and ontology-gap
preservation; and retains the closed predicate set and no-predicate-unlocking policy.

## Blindness and sealing verification

- Extraction read only v2 EvidencePackets and the v2 prompt/policy.
- v1 candidate files and Sol annotations were opened only after `v2_output_seal.json` was written.
- V2 seal complete-extraction hash: `cad120c19a8320a8670f9ff7671a1da9af5cc14099e3521129ff1c3c723f4b2e`.
- Checklist traces: **120/120** complete, with all fourteen families recorded per mantra.
- V2 packet/output hashes and selected-id hash are recorded in the seal.

## V2 output

| Measure | Result |
|---|---:|
| Assertions | 186 |
| Assertions/mantra | 1.550 |
| No-claim mantras | 31 |
| Semantic entity candidates | 48 |
| Validator rejections | 0 |
| Evidence errors | 0 |
| Explicitness | `{'EXPLICIT': 15, 'STRONG_INFERENCE': 171}` |
| Predicate distribution | `{'DESCRIBES': 22, 'DESCRIBES_ACTION': 20, 'EXPRESSES': 15, 'INVOKES': 13, 'INVOLVES_OFFERING': 11, 'INVOLVES_RITUAL': 19, 'INVOLVES_SUBSTANCE': 33, 'PRAISES': 2, 'REFERS_TO_NATURAL_PHENOMENON': 16, 'REFERS_TO_PLACE': 14, 'REQUESTS': 21}` |
| Node-type distribution | `{'ACTION': 20, 'CANONICAL_ENTITY': 37, 'CONCEPT': 15, 'NATURAL_PHENOMENON': 16, 'OFFERING': 11, 'PLACE': 14, 'RITUAL': 19, 'STATE': 21, 'SUBSTANCE': 33}` |

## Validation and evidence quality

All v2 assertions passed deterministic structural/evidence validation. The validator
rejection rate is **0/186**; evidence-error rate is
**0/186**. These are pipeline validity measures,
not human truth measures.

## Ontology gaps

V2 preserved **29** packet-local ontology-gap observations rather than forcing
human/person, kinship, patron, ancestor, or opaque referents into an existing type.
The sealed Sol review records **8** ontology gaps for later expert audit.

## Final state

`unlocked_predicates = []`; all assertions remain candidates/`NEEDS_REVIEW`. No human gold
exists, and no model output became gold.

## Final decision

`SEMANTIC_LUNA_V2_NEEDS_REVISION`: v2 materially broadened coverage and preserved 100%
deterministic evidence validity, but silver agreement remains low and the disagreement
queue is too large to justify a larger semantic run. Revise relation/object label policy
and inspect the proposed audit subset before another pilot.
