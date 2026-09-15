# Post-V1 Data Completeness Campaign — STATUS

**Resume from this file. Rewrite it whole; never splice sections in.**
Guard: `python scripts/validate_status_report.py`

- Branch `phase-data-completeness-v2` · start commit `d6e93a9` · tag `vedanvaya-v1.0.0` FROZEN
- Last rewritten 2026-09-16, after the Wave 3 canonical import and its readback

## Where the campaign is

**Wave 3 is imported, read back clean, and the graph's own quality gates pass.** The first
canonical write of this campaign has happened. Seven of fourteen domains landed; seven are
withheld, each for a named reason.

Two independent gates agree:

- `scripts/wave3_readback.py` → `READBACK_CLEAN`. Census matches the dry-run's promise on
  both figures, the four corpus totals hold, nine closure tests pass with every field their
  claim covers asserted, 0 withheld identities are present and 0 written nodes are
  unreachable.
- `scripts/graph_quality_scorecard.py` → **9 of 9 integrity gates PASS**, including the two
  that were red for everything this wave wrote until the contracts were met.

Coverage figures from the imported domains are now **canonical readback figures** rather
than `STAGED_PROJECTED_COVERAGE`. The withheld domains' figures are still projected and may
not reach the frontend, API or any public report.

## Canonical graph

| | Before Wave 3 | After Wave 3 |
|---|---:|---:|
| Nodes | 108,779 | **122,986** |
| Relationships | 265,295 | **288,051** |

Core corpus unchanged and asserted every run: RV 10,552 · SV 1,844 · YV 1,975 · AV 5,839.

## Done

Owner round two is applied in full; the decisions and their rationale are in
`OWNER_DECISIONS.md` sections 11–17. Do not re-ask them.

- **Folding is not identity.** `FOLD_FIX_BREAKS_REFERENT_IDENTITY` resolved by option B: the
  comparison surfaces got their own fold and the identity fold is untouched. All 3,819
  released referent digests reproduce byte for byte, including the five Yajurvedic keys an
  in-place fix would have drifted. Cross-Veda identity baseline re-recorded 1,538 → 1,735.
- **M6 replaced by M6′.** Three homogeneous populations on the schema's own closed enums,
  1,423 rows, every subject asserted on grain. `scope_type` is on 0 nodes and 0
  relationships, so the card's `ADDITIVE = false` had been recorded against a population
  that does not exist.
- **SOMA-PRESSING kept, three aliases retired** on a measured criterion. 117
  `MENTIONS_ENTITY` and 108 `ABOUT_CONCEPT` edges retired, 21 updated, all read back.
- **The audible-review harness exists.** `scripts/audio_review_harness.py`, resumable,
  append-only log, three refusals enforced at the endpoint and tested.
- **`CROSS_VEDA_DEVATA_IDENTITY_BRIDGE` registered and sized**, not built on a guess.

## Wave 3 — what landed

Element-level, planned by `scripts/wave3_import_plan.py` and read back by
`scripts/wave3_readback.py`.

| | Planned | Landed |
|---|---:|---:|
| Nodes created | 14,221 | 14,207 |
| Nodes labelled or updated | 5,647 | — |
| Relationships created | 22,982 | 22,982 |
| Relationships retired | 226 | 226 |
| Property writes | 51,215 | 51,215 |

Domains imported: `communities` · `cross_veda` · `formula` · `quality` · `ritual` ·
`scholarship` · `semantic_roles`.

New labels: `RoleFiller` `RitualStep` `QualityVerdict` `ScholarlyDisagreement` `Scholar`
`ScholarlyWork` `DeityCommunity`, plus `Ritual` `RitualRole` `Action` `Object` `Substance`
`Offering` extended with new registry entities.

`:ScholarlyDisagreement` and not `:InterpretiveClaim`, which it was until the API suite
failed: that label is a curated product object whose contract promises an `about` enum and
a `falsifier`, and a recorded disagreement between two named asserters has neither.

New predicates: `ASSERTION_ROLE` `REFERS_TO` `SHARES_FORMULA_WITH` `HAS_RITUAL_STEP`
`QUALITY_VERDICT_ABOUT` `SCHOLARLY_CLAIM_ABOUT` `ASSERTED_BY` `POSITION_STATED_IN`
`REPORTED_IN` `ATTESTED_IN` `SPECIALIZED_FORM_OF`, and the four rite predicates.

`HAS_RITUAL_STEP` rather than the existing `HAS_STEP`, whose 3 edges point at an `:Action`:
widening its range would change what an existing predicate means, and the readback asserts
it still holds exactly 3.

## Remaining — withheld, with the reason

| Domain | Rows | Why |
|---|---:|---|
| `attribution` | 23,003 | Gates B and C were never run. A Wave-1 domain that never entered the adversarial programme. **The largest single piece of remaining work.** |
| `semantic_resemblance` | 19,088 | A step-5 dependent re-derivation, not an import: two of its four inputs landed in this wave. Tier B refused pending the Devatā bridge. |
| `translation` | 2,254 | Gates B and C never run, plus owner decisions A and C bar 31 forced addresses and the RV 1.65–1.70 span. |
| `audio_av` | 771 | Audible review. 0 of 1,021 heard. |
| `samaveda_music` | 1,471 | Audible review, and migrations M2–M4 wait with it. |
| `audio_rv` | 150 | Audible review. |
| `audio_yv` | 33 | Audible review. |

## Blocking

Nothing blocks a resumed session. Four named pieces of work remain, in this order:

1. **Seven API contract tests fail, and five of them should.** `tests/api` asserts the
   frozen Product-V1 census of 108,779 / 265,295 and a ritual total of 8, and its own
   docstring says drift is worth failing over: *"every measured caveat in the API is
   describing a graph that no longer exists"*. That is now true. The caveats must be
   **re-derived, not bumped** — a constant edited to match is a caveat nobody measured.
   `scripts/wave3_dependency_invalidation.py` lists which consumers moved and what rebuilds
   each.
2. **Dependent re-derivation (owner section 13).** Eight of nine named consumers read
   something this wave wrote. Nothing has been rebuilt. Do not regenerate the frontend
   design, and do not re-grade the Ask benchmark speculatively — a daily quota is burned by
   a retry.
3. **`attribution` gates B and C.** 23,003 rows, no semantic review and no adversarial test.
   The largest single piece of remaining work.
4. **The 1,021 audible reviews.** `python scripts/audio_review_harness.py`.

## Registry

`data/gap_registry.json` — **81 gaps**. `GAP-CROSS-VEDA-DEVATA-IDENTITY-BRIDGE-001` opened
this round with `causation_status: MEASURED`. No gap closes until its own closure test passes
against canonical readback, and the seven imported domains' closure tests are in
`wave3_readback.json`.

## Current wave artifacts

```
data/staging/integration/wave3_import_plan.json      element-level plan
data/staging/integration/wave3_dry_run_v2.json       the GO, with its 16 conditions
data/staging/integration/wave3_import_receipt.json   what landed, per group
data/staging/integration/wave3_readback.json         read out of the database
data/staging/integration/wave3_scope_grain.json      M6-prime populations
data/staging/integration/wave3_soma_pressing_correction.json
data/staging/integration/wave3_devata_identity_bridge.json
```

## What the import cost, and why

Five passes and four rollbacks. Every defect was mine rather than the artifacts', and none
was visible offline — the database, the quality scorecard and the API contract tests each
found things no amount of reading the plan would have.

| Found by | Defect |
|---|---|
| census diff | a referent's key carried onto the referrer destroyed `entity_key` uniqueness and fanned 387 edges into 4,564 |
| census diff | `MERGE (n:Label {key})` matches on label AND properties, so it created twins instead of finding existing nodes |
| per-group check | `count(r)` over an `UNWIND` counts operations, so three groups reported landing more than they were sent |
| census diff | a "already modelled as" redirect stopped at the nodes; 6 edges matched nothing |
| census diff | the dry-run promised 5 edges the correction was never going to write |
| readback | 12,033 nodes arrived with no relationship — three whole relation families were missing from the plan |
| readback | two closure tests I wrote measured their own failure and passed, asserting a different field |
| API suite | `:InterpretiveClaim` overloaded; `/insights` returned `about: None` against its own schema |
| API suite | `ASSERTED_BY` reused, whose signature is `InterpretiveClaim → Source` |
| API suite | `SET n += row` overwrote 102 curated `display_label`s; `AYAS-METAL` lost "(ayas)" |
| scorecard | 22,981 edges with no `quality_tier` and 14,209 nodes with no `display_label` |

Each is now guarded by a test on the spec, so it fails offline rather than in the database.
**The lesson, in one line: an importer's own per-group report is not evidence.** All five
passes printed a clean table.

## Rollback, tested three times

```
D:\vedanvaya-backups\wave3-pre-import-20260915T155144\neo4j.dump
96,841,712 bytes · sha256 a0ab27b6…d6957
```
Restored four times during this session, and verified exact every time: 108,779 / 265,295, four
corpora exact, 0 Wave 3 residue, 0 shared `entity_key`. The dump must be named `neo4j.dump`
inside a timestamped directory — `neo4j-admin database load` matches by database name.

```
docker stop vedagraph-neo4j
docker run --rm -v infra_neo4j_data:/data -v /d/vedanvaya-backups/<stamp>:/backups \
  neo4j:5.26-community \
  neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
docker start vedagraph-neo4j
```

On Git Bash, prefix the `docker run` with `MSYS_NO_PATHCONV=1` or `/backups` is rewritten to
a Windows path and the command fails with "is not an existing directory".

## Backlog, measured

- **The label-less RELATIONSHIP endpoint match is still O(rows × nodes).** Node groups now
  create an index on their own key and probe label-scoped first, which fixed the node side —
  a 9,255-key probe had taken 3m40s and one labelling pass 4m42s. The relationship groups
  that match an endpoint without a label still cannot use an index. Giving them
  `start_label="DomainEntity"` would use `domain_entity_key_unique`, and the plan's
  provided-by-this-plan set already covers the nodes that do not exist yet.
- **9 ritual `step_key`s each cover two distinct steps** under one canonical URN and one
  UUIDv5. Withheld from import rather than merged. The ritual domain needs to restage its
  step identity.
- **16 registry rows claim `PROPOSED_NEW` for a key the graph already holds** — 11 materials
  and 5 offerings. The plan resolves against the graph rather than the marking, so no
  duplicate was created, but the artifact's marking is wrong.
- **The concept cap's tie-break is corpus-wide**, so withdrawing an alias from one concept
  reshuffles which concepts survive the per-passage cap on unrelated passages: 29 assertions
  across 17 other concepts. Held for its own decision and not imported.
- **24 further aliases across 18 entities** meet the SOMA-PRESSING retirement criterion.
  Reported, not applied.

## Next

A dependent re-derivation · B `attribution` gates B and C · C audible reviews ·
D Wave 4 independent QA. **Wave 4 must not begin until every importable Wave 3 domain is
readback-complete.**

## Environment

```
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
```
Frontend 3000 · API 127.0.0.1:8000 · Neo4j 7474/7687 (Docker `vedagraph-neo4j`).

Graph: `docker exec vedagraph-neo4j cypher-shell -u neo4j -p vedagraph_dev --format plain "<Q>"`

## Rules a resuming session must not break

1. An importer's own per-group report is not evidence. Three Wave 3 attempts printed a clean
   25-group table; the first over-wrote by 5,930 relationships, the second landed 11 short
   and left 12,033 unreachable nodes. Only the census diff and the readback found either.
2. `count(r)` over an `UNWIND … MERGE` counts operations, not elements. Landed greater than
   sent is impossible, not a success.
3. `MERGE (n:Label {key: X})` matches on label **and** properties, so it does not find an
   existing node carrying X under another label — it creates a twin.
4. Never carry a referent's identity key onto the referrer. It destroyed `entity_key`
   uniqueness and fanned 387 edges into 4,564.
5. A "do not create, already modelled as Y" decision must propagate to the edges pointing at
   the retired key.
6. A node nothing points at is not imported data. Check for it; exempt the deliberate cases
   by name.
7. A closure test must assert every field its own claim covers. Two of mine measured their
   own failure and passed.
8. Never turn NOT ASSESSED into VERIFIED ZERO.
9. Never map another recension onto the one we hold — Jaiminīya is not Kauthuma, Taittirīya
   and Kāṇva are not Mādhyandina, Paippalāda is not Śaunaka.
10. Never attach a long recording to an exact mantra without verified boundaries.
11. Enumerate a field's value space before concluding it is empty.
12. Measure the cause before working the remedy.
