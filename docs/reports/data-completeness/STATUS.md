# Post-V1 Data Completeness Campaign — STATUS

**Resume from this file. Rewrite it whole; never splice sections in.**
Guard: `python scripts/validate_status_report.py`

- Branch `phase-data-completeness-v2` · start commit `d6e93a9` · tag `vedanvaya-v1.0.0` FROZEN
- Last rewritten 2026-09-15, Wave 2 closing

## Canonical graph — unchanged

**108,779 nodes / 265,295 relationships.** No canonical write has occurred in this
campaign. Every coverage figure is **STAGED_PROJECTED_COVERAGE** until Wave 3 imports and
reads counts back out of the database. None may reach the frontend, API, release docs or
any public report before then.

## Owner decisions in force

Full text and rationale in `OWNER_DECISIONS.md`. Do not re-ask these.

| | Decision |
|---|---|
| Soma / Pavamāna | **Specialized form, separate analytical nodes.** Predicate `SPECIALIZED_FORM_OF`, only this edge migrated, staged not applied |
| Fold vs identity | **Normalization never establishes identity alone.** It generates candidates. `NORMALIZED_EQUIVALENCE` ≠ `CANONICAL_IDENTITY` ≠ `TEXTUAL_VARIANT` |
| Schema migrations | **Four additive extensions approved** subject to migration cards showing all five flags, `OLD_PREDICATE_MEANING_CHANGED = false` |
| Human gold | **Not required** where source adjudication is strongest available. A documented evaluation limitation, not an implementation gap |
| SV morphology | Annotation source absent; **process all 1,844 anyway**. `PUBLISHED_HUMAN_ANNOTATION = unavailable`, `MORPHOLOGICAL_ANALYSIS = processed` |
| A — RV 1.65–1.70 | Barred until the coordinate repair applies. Affected layer is **translations**; that span's audio is 61/61 EXACT and text-verified |
| B — RV 150 audio | `REMOTE_DIRECT` accepted. Range supported; caching blocked by rights |
| C — forced YV addresses | 31 barred. Accepted recovery **19, not 50** |
| E — audio gate | **CLOSED.** 1,021 rows `NEEDS_AUDIBLE_REVIEW`, 0 reviewed. Text comparison, metadata, waveform and ASR are none of them listening review |

## Wave 2 — 7 of 8 domains staged

All staged artifacts pass the structural gate. Three gates per domain, never averaged;
`scripts/wave3_eligibility_ledger.py` is the live view.

| Agent | Domain | A | B | C | Status |
|---|---|---|---|---|---|
| 9 | semantic_roles | PASS | PASS | SURVIVED | **ELIGIBLE** |
| 12 | formula | PASS | PASS | SURVIVED | **ELIGIBLE** |
| 10 | cross_veda | PASS | PASS* | SURVIVED | BLOCKED — fold fix |
| 15 | communities | PASS | PASS | SURVIVED | needs re-check post-decision |
| 13 | ritual | PASS | see below | lead-tested | pending |
| 14 | scholarship | PASS | see below | lead-tested | pending |
| 16 | quality | PASS | see below | lead-tested | pending |
| 11 | semantic_resemblance | — | — | — | **RE-RUNNING** — first run produced no artifact |

Agents 13, 14 and 16 finished without reporting; their artifacts were found on disk,
static for two hours, and validated by the lead.

## Adversarial results — 7 of 7 tested, 7 defects found

The hit rate is the finding. A validator pass proves an artifact is well-formed and says
nothing about whether its headline is true.

| Domain | Defect found | Outcome |
|---|---|---|
| semantic_roles | 24.8% of role fillers wrong from cross-clause leakage | Restaged. Fillers 51,231 → **2,052**, triples 5,219 → **341**, all treebank-backed |
| cross_veda | 396 of 6,271 transformation types wrong; root cause was dead code | Restaged. Fold fix blocked on identity |
| formula | 134 pairs typed as edition variants where the difference was an inline address | Restaged. `EDITORIAL_APPARATUS` eliminated as a type |
| communities | Its decisive claim rested on a prior the graph contradicts | Withdrawn, refusal re-founded on 8 measured grounds |
| ritual | **24 rows rest only on the generic yajña** — 10.8% of Saṃhitā-typed claims | Needs re-typing |
| scholarship | **1 of 92 disagreements has the same asserter on both sides** | Needs removal |
| quality | Of 11,210 verdicts: 1,402 diverge, 1,283 confirm only via an unsound alias, 143 refuted | Finding, not a defect in the artifact |

Lead-tested attacks that came back **clean**: ritual's core/supplementary boundary (0 rows
keyed outside the four recensions); scholarship's reporting-source problem (73 rows typed
`ASCRIPTION_DISPUTED_BY_THE_REPORTING_SOURCE`); quality's evaluation independence (three
layers adjudicated by a treebank that did not build them, metre checked by counting the
text).

## The campaign's recurring error

Absence assumed at the source where the defect was in our own addressing. Seven instances.
**Measure the cause before working the remedy** — three registry prescriptions sent this
campaign to acquire material it already held.

Registry now enforces it: a source-absence claim is refused while any of 14 addressing
checks is unrun.

## Registry

`data/gap_registry.json` — **80 gaps**, **0 closed**, which is expected before readback.
13 carry `causation_status: MEASURED`; 67 are untested hypotheses. 6 disproven hypotheses
preserved and marked. 25-type closed root-cause taxonomy.

## Open blockers

`data/staging/integration/blockers.json`

1. `FOLD_FIX_BREAKS_REFERENT_IDENTITY` — **awaiting owner decision.** The cross-Veda fix is
   correct and cannot be applied in place: `referent.py` computes `comparison_sha256`
   through the fold, so it trips the referent-drift gate on 5 Yajurvedic keys. A migration
   would assert a referent change that did not happen. Three options; lead recommends B
   (separate comparison fold). Four regression tests held as strict xfail.
2. `NAME_COLLISION_SCOPE_TYPE` — lead action. Namespace at import; must not be resolved by
   precedence.
3. `CURATION_CONTRADICTION_SOMA_PAVAMANA` — **RESOLVED**, see decisions above.

## Environment

```
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
```
Frontend 3000 · API 127.0.0.1:8000 · Neo4j 7474/7687 (Docker `vedagraph-neo4j`, managed
outside the repo).

Graph: `docker exec vedagraph-neo4j cypher-shell -u neo4j -p vedagraph_dev --format plain "<Q>"`
Gate: `.venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/<domain> --graph`

## Rollback, tested not assumed

`D:\vedanvaya-backups\vedanvaya-v1.0.0-preflight-20260915T105606\neo4j.dump`
(96,844,203 bytes, sha256 `98f71b64…83b981`). The dump must be named `neo4j.dump` inside a
timestamped directory — `neo4j-admin database load` matches by database name, which is how
the first restore attempt failed.

```
docker stop vedagraph-neo4j
docker run --rm -v infra_neo4j_data:/data -v /d/vedanvaya-backups/<stamp>:/backups \
  neo4j:5.26-community \
  neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
docker start vedagraph-neo4j
```
Proven by loading into a scratch volume, serving on spare ports and re-counting exact.

## Next order — do not reorder

A finish Wave 2 (agent 11) · B adversarial-review all 8 · C restage failures ·
D resolve dependency invalidation · E validate migration cards · F collision audit ·
G **Wave 3 dry-run** · H owner review of dry-run · I canonical import · J readback ·
K dependent re-derivation · L Wave 4 independent QA.

**I must not precede G and H.**

## Rules a resuming session must not break

1. No canonical mutation outside a lead-run, idempotent, checksummed import that reads its
   counts back out of the database.
2. Never turn NOT ASSESSED into VERIFIED ZERO.
3. Never map another recension onto the one we hold — Jaiminīya is not Kauthuma, Taittirīya
   and Kāṇva are not Mādhyandina, Paippalāda is not Śaunaka.
4. Never attach a long recording to an exact mantra without verified boundaries.
5. Never let a model invent a disagreement, an attribution or a timestamp.
6. A limitation card is removed only when data proves closure.
7. Do not commit a specialist's staging directory until it reports. Notifications fire more
   than once, and three agents finished without reporting at all.
8. Generate a manifest **last**, write nothing between it and the validation covering it,
   and read the **checksum count** rather than the word PASS. One agent withdrew five
   PASSes for racing its own gate.
9. Write each fix behind an assertion about its blast radius **before** applying it. That
   practice caught eight agent defects; reading one's own output afterwards caught none.
10. Enumerate a field's value space before concluding it is empty. A lead probe reported
    92 missing attributions that were all present under a different field name.
