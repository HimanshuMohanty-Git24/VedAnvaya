# Rigveda semantic user-selected Luna V3.2 smoke test — 8 passages

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

MODEL PROVENANCE = USER_SELECTED_MODEL_UNATTESTED.

THIS RUN IS NOT RUNTIME-ATTESTED AS LUNA.

THIS IS A SMALL ENGINEERING SMOKE TEST.

## Decision

`USER_SELECTED_LUNA_V3_2_SMOKE_HEALTHY`

The decision means only that this tiny experiment did or did not expose a major engineering failure. It establishes no accuracy, corpus stability, scholarly correctness, or canonical validity.

## Starting health and provenance

- Starting repository health: dirty but preserved; no reset, clean, destructive checkout, or external API was used.
- User-selected model: `gpt-5.6-luna`.
- Requested model: `gpt-5.6-luna`.
- Runtime: `CODEX_DIRECT`.
- Reasoning: `high`.
- Provider build metadata: `UNAVAILABLE`.
- Independent runtime model attestation: `UNAVAILABLE`.
- Provenance classification: `USER_SELECTED_MODEL_UNATTESTED`.

## Frozen V3.2 inputs

- Prompt policy: `rigveda-semantic-extraction-v3.2`.
- Prompt SHA-256: `e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1`.
- Schema SHA-256: `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2`.
- Ontology SHA-256: `cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce`.
- Parent selection hash: `26d2f85aec91e621d43444931d40fc81e08a7c9d533bdce820c86945c398783c`.
- Deterministic 8-ID subset hash: `be4cccec008e824e6ceeeb319e64190eee52968c51cee5dc268b22d4d535637c`.

Selected IDs were chosen from the frozen 60 using engineering strata and existing engineering diagnostic case labels only; no prior semantic outputs or counts were used for membership.

| Passage | Stratum | Smoke coverage lens | Selection reason |
|---|---|---|---|
| `VG:RV:SAK:M04:S022:V011` | `PARALLEL_CONTROL` | `REQUESTS_sensitive` | PAR-01 TRANSLATION_VARIANT_EFFECT engineering diagnostic; parallel-control member. |
| `VG:RV:SAK:M10:S058:V001` | `B01_RELATION_BINDING` | `REQUESTS_sensitive` | PAR-03 EXTRACTION_INCONSISTENCY engineering diagnostic; B01 relation-binding member. |
| `VG:RV:SAK:M10:S018:V008` | `B02_EVIDENCE_SPAN` | `DESCRIBES_DESCRIBES_ACTION_sensitive` | B02 evidence-span member selected for action-boundary smoke coverage. |
| `VG:RV:SAK:M08:S036:V006` | `B01_RELATION_BINDING` | `DESCRIBES_DESCRIBES_ACTION_sensitive` | REV-10 CANONICAL_ENTITY_RISK / predicate-boundary engineering diagnostic; B01 member. |
| `VG:RV:SAK:M08:S035:V008` | `B01_RELATION_BINDING` | `canonical_target_sensitive` | REV-05 CANONICAL_ENTITY_RISK engineering diagnostic; B01 member. |
| `VG:RV:SAK:M08:S035:V009` | `B01_RELATION_BINDING` | `substance_ritual_offering_sensitive` | REV-06 CANONICAL_ENTITY_RISK engineering diagnostic with offering-sensitive wording; B01 member. |
| `VG:RV:SAK:M09:S004:V009` | `B02_EVIDENCE_SPAN` | `previous_emission_no_claim_risk` | REV-02 ONTOLOGY_GAP engineering diagnostic explicitly records cautious no-claim risk; B02 member. |
| `VG:RV:SAK:M06:S042:V004` | `CLEAN_CONTROL` | `clean_control` | Frozen CLEAN_CONTROL member with no B01 or B02 selection record. |

## EvidencePackets and task identities

- EvidencePackets: expected 8, unique 8, missing 0, duplicates 0, hashes valid.
- Semantic outputs from V3.1, Sol, historical heuristic artifacts, and previous comparisons were not included in the packet custody.
- Run A: `vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-a`; sealed before comparison with seal `6c2106215e664e7550ded15f4074fb76b37e661d64e069b31a01b485ba092625`.
- Run B: `vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-b`; sealed before comparison with seal `116386f4837cc40f5b784b4ac330d2b66e68c4dc57bb06176661d738e1d3cdcd`.
- Maximum intended semantic final tasks: `16`; completed final tasks: `16`.

## Completion, retries, and integrity

| Metric | Run A | Run B |
|---|---:|---:|
| Final tasks | 8/8 | 8/8 |
| Retries | 2 | 0 |
| Receipt failures | 0 | 0 |
| Packet-hash failures | 0 | 0 |
| Evidence failures | 0 | 0 |
| Span failures | 0 | 0 |
| Binding failures | 0 | 0 |
| Ontology/type failures | 0 | 0 |
| Heuristic contamination | 0 | 0 |
| Missing final tasks | 0 | 0 |

The two preserved Run A failed raw responses are counted as retries, not integrity failures; validation was not weakened.

## Run behaviour

| Metric | Run A | Run B |
|---|---:|---:|
| Assertions | 27 | 23 |
| Assertions/passsage | 3.375 (MODERATE) | 2.875 (SPARSE) |
| No-claim count | 0 | 0 |
| Canonical-reference assertions | 4 | 3 |

Density gap: `0.500` assertions/passage. These descriptors use smoke-test engineering bands (`<3 SPARSE`, `3-<5 MODERATE`, `5-<7 DENSE`, `>=7 VERY_DENSE`); they are not quality scores. The previous Sol-produced V3.2 experiment is descriptive only: `392/388` over 60 (`6.533/6.467` per passage), not a target.

### Predicate counts

| Predicate | Run A | Run B |
|---|---:|---:|
| `DESCRIBES` | 2 | 0 |
| `DESCRIBES_ACTION` | 5 | 6 |
| `INVOKES` | 3 | 3 |
| `INVOLVES_OFFERING` | 2 | 2 |
| `INVOLVES_SUBSTANCE` | 4 | 2 |
| `PRAISES` | 1 | 0 |
| `REFERS_TO_PLACE` | 1 | 1 |
| `REQUESTS` | 9 | 9 |

One-sided predicate observations: `{"DESCRIBES": [2, 0], "PRAISES": [1, 0]}`. `PRAISES` (1) and `DESCRIBES` (2) occur only in Run A; neither is a repeated major one-sided family in this n=8 smoke sample. No catastrophic one-sided predicate collapse was detected.

### Object-kind counts

| Object kind | Run A | Run B |
|---|---:|---:|
| `CANONICAL_ENTITY_REF` | 4 | 3 |
| `EVENT` | 5 | 6 |
| `OFFERING_REF` | 2 | 2 |
| `OPAQUE_REFERENT` | 2 | 0 |
| `PLACE_REF` | 1 | 1 |
| `REQUESTED_OUTCOME` | 9 | 9 |
| `SUBSTANCE_REF` | 4 | 2 |

## Passage-level agreement

- Exact assertion-set agreement: `3/8`.
- Predicate-presence agreement: `3/8`.
- No-claim agreement: `8/8`.
- Canonical-entity agreement: `7/8`.
- Typed-object agreement: `3/8`.
- Evidence-anchor agreement: `1/8`.

These are descriptive self-agreement measures only. They are not accuracy, recall, or gold scores.

## Canonical safety

- `OMISSION`: `1` passage-level difference.
- `SAME_TARGET_DIFFERENT_PREDICATE`: `0`.
- `CONTRADICTORY_CANONICAL_TARGET`: `0`.
    - Contradictory canonical target passages: `none`.

No contradictory canonical target was observed.

## Lightweight precision-risk inspection

This was not an exhaustive adjudication and no model output was rewritten.

- Unsupported extraction: NONE_OBVIOUS_FROM_STRUCTURAL_INSPECTION; no exhaustive adjudication performed.
- Duplicate assertion: `NONE`.
- Obvious predicate overlap: `["run_a:VG:RV:SAK:M08:S035:V008:come thrice, O Asvins:['INVOKES', 'REQUESTS']", "run_a:VG:RV:SAK:M08:S035:V009:come thrice, O Asvins:['INVOKES', 'REQUESTS']", "run_b:VG:RV:SAK:M08:S035:V008:come thrice, O Asvins:['INVOKES', 'REQUESTS']", "run_b:VG:RV:SAK:M08:S035:V009:come thrice, O Asvins:['INVOKES', 'REQUESTS']"]`.
- REQUESTS over-splitting: REVIEW_ONLY: two REQUESTS appear in RV 4.22.11 and RV 10.18.8; no obvious duplicate outcome was structurally established.
- Broad `ASSOCIATED_WITH`: NONE.
- Broad `HAS_THEME`: NONE.
- Suspicious `DESCRIBES` + `DESCRIBES_ACTION` duplication: `['run_a:VG:RV:SAK:M10:S018:V008', 'run_a:VG:RV:SAK:M10:S058:V001']`; this is a review flag, not an automatic quality verdict.

## Separated provenance buckets

`MODEL_IDENTITY_SEPARATED = true`

- Historical V3.1: kept in its recorded provenance terminology and not merged into this smoke statistic.
- Previous V3.2: `SOL_V3_2_ENGINEERING_EXPERIMENT`; 392/388 assertions over 60, approximately 6.533/6.467 per passage. This is a separate engineering bucket and is not called Luna here.
- Current experiment: `USER_SELECTED_LUNA_V3_2_UNATTESTED`; 27/23 assertions over 8, 3.375/2.875 per passage.

## Tests and repository safety

Targeted semantic tests, repo-pinned Ruff, and strict mypy are run after this report is materialized. Existing dirty files and sealed artifacts remain untouched; new artifacts are additive only.

## Cost-aware next semantic path

`RUN_SINGLE_PASS_448_NEW_LUNA_CANDIDATE_PILOT`

No duplicated 60-run is recommended, and 10,552 is not authorized.

## Final decision

`USER_SELECTED_LUNA_V3_2_SMOKE_HEALTHY`
