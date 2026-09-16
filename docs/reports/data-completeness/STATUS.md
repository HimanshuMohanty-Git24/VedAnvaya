# Post-V1 Data Completeness Campaign — STATUS

**Resume from this file. Rewrite it whole; never splice sections in.**
Guard: `python scripts/validate_status_report.py`

- Branch `phase-data-completeness-v2` · start commit `d6e93a9` · tag `vedanvaya-v1.0.0` FROZEN
- Last rewritten 2026-09-16, after owner round four: integrity gates, labels, Whitney, semantics

## Where the campaign is

**Both release-integrity gates are real and adversarially tested. The public label leak is
closed. Whitney and semantic resemblance are both defensibly refused, with no graph
mutation.** Wave 4 has not started.

| gate | result |
|---|---|
| `attribution_import.py --readback` | `READBACK_CLEAN`, 0 findings |
| `graph_quality_scorecard.py` | **9 of 9**, two of them previously unable to fail |
| `pytest tests/api` | **1,372 passed** |
| `pytest tests/unit` | **1,147 passed**, 41 skipped |
| `pnpm test` | **434 passed** |

## Canonical graph

| | Product V1 | After Wave 3 | Now |
|---|---:|---:|---:|
| Nodes | 108,779 | 116,825 | **116,838** |
| Relationships | 265,295 | 281,290 | **281,290** |
| Public nodes (`NOT n:Internal`) | — | 44,324 | **39,692** |

Core corpus invariant and asserted every run: RV 10,552 · SV 1,844 · YV 1,975 · AV 5,839 =
20,210. Round four's only mutation was M8, which adds one label and creates nothing.

Backup: `D:\vedanvaya-backups\round4-pre-m8-20260916T112837\neo4j.dump`
sha256 `13eaef62…6698`.

## Round four — what changed

### Two gates that could not fail, replaced

**Relationship declarations.** Third version; the first two are recorded in the code so the
mistake is not repeatable.

| version | reference set | why it could not fail |
|---|---|---|
| v1 | `ontology ∪ every type in the graph` | membership is tautological |
| v2 | the API's traversable/refused lists | a product decision, not a schema declaration |
| v3 | `ontology.all_declared_relationship_types()` | composes layer authorities; the graph is not an input |

Measured before the repair: **18 populated relationship types declared by nothing.** Ten were
this campaign's; eight were pre-existing corpus and metadata predicates carrying 138,143
edges, whose constants sat in the ontology under the comment *"listed so the closed vocabulary
is complete"* and reached no declared set. Now: declared 90 · populated 76 · **undeclared 0**
· declared-but-unused 14 · system exceptions 0.

The signature gate was widened with them, then again: `all_endpoint_signatures()` composes
all three declaring layers. It had iterated `RELATIONSHIP_SIGNATURES` only, so 18 predicates
carrying **141,264 edges** had their endpoints checked by nothing. Coverage is now 63 of 76
populated predicates, and the uncovered 15 are pinned as an exact set.

**Dependency staleness.** Counts are unchanged by a swap of equal size, so labels now digest
sorted identity keys and predicates sorted endpoint pairs; declared **file** inputs and the
**builder's** own source are inputs too. `built_at` is metadata, and a test greps
`classify()` for `built_at`, `wave3_` and `datetime.now`.

**42 tests**, including one that reconstructs the original tautology and shows it reports
nothing for the very input the repaired gate catches.

### The label leak was live

All six Wave 3 labels were declared by no authoritative source, and
`frontend/.world/world.raw.json` held **2,568 `:QualityVerdict` nodes** — this repository's
assessment of its own passages — as the **fourth-largest type in the public world**, ahead of
`:Rishi`. "Public" is one clause, `NOT n:Internal`, and nothing had marked them.

| label | n | disposition |
|---|---:|---|
| `Scholar` · `ScholarlyWork` · `ScholarlyDisagreement` | 17 · 17 · 113 | canonical product-visible |
| `QualityVerdict` | 2,568 | internal — a fact about the record |
| `RoleFiller` | 2,052 | internal — wiring, no `entity_key` |
| `DeityCommunity` | 12 | internal — an analytic partition with its refusal attached |

M8 marked 4,632 nodes; re-exported and verified **0 of each** in the world file. Final
undeclared public labels: **0**, exception list empty.

### Whitney 466 — withheld, and not for want of evidence

Four channels attempted, three refused with stated reasons. The permitted channel — the AV
registries' `source_variants`, generated from the same Whitney index — **works**: 405 of 477
proposals resolve, 0 ambiguous, 0 findings against any individual resolution.

**Nothing imported, because the adversarial pass was checking the wrong object.** Of 541
AV_WHITNEY `:Chandas` entities, a number are unsegmented fragments of Whitney's bracket
carrying a deity, a metre and a verse exception in one string. Three tests were written to
bound the share and they disagree: **17, 28, 39**. That disagreement is the finding —
separating a deity adjective from a metre name is philological adjudication, which may not act
as identity evidence, so a partial import cannot be made safe.

Found in data that was already canonical: **33 `HAS_CHANDAS` edges point at such fragments
today**. `GAP-AV-CHANDOMETRE-SEGMENTATION-001`, not repaired — re-segmenting a canonical
vocabulary re-identifies its entities.

### Semantic resemblance — outcome C, measured

**0 assertions imported.** The prior artifact declares a 108,779-node snapshot against this
graph's 116,838, so it is not importable. No semantic representation is computable here — no
`onnxruntime`, `transformers`, `sentence_transformers` or `.onnx` file — so none can be shown
to beat a control. The control was re-implemented and measured on current inputs: **AUC
0.754** over 279 adjudicated pairs (dev 0.774, test 0.736), character 4-grams over
accent-stripped Sanskrit, no model and no translation channel.

It does **not** reproduce the prior `C_LEXICAL_CHAR4` — 6 of 370 exact, 292 within 0.05 — so
no prior number is carried forward. `SHARED_PHRASING_ONLY` stays withheld on 7 adjudicated
labels of 486.

## Dependents

`scripts/dependency_state.py --status` — **6 CURRENT · 0 STALE_INPUT · 2 BLOCKED · 1
NOT_APPLICABLE · 0 unexplained**.

CURRENT: cross-Veda matrices · formula relations · entity coverage · quality evaluation ·
Visualization Lab · Knowledge World. `ritual aggregates` is NOT_APPLICABLE (no artifact
exists). `semantic resemblance` and `Ask retrieval` are BLOCKED, each with a concrete
blocker recorded in the ledger.

## Blocking

1. **`GAP-AV-CHANDOMETRE-SEGMENTATION-001`** — 33 canonical `HAS_CHANDAS` edges point at
   bracket fragments rather than metre names. Needs an owner decision: re-segment the registry
   (which re-identifies entities) or model the compound strings as evidence.
2. **466 Whitney rows** stay `RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT`, blocked behind (1).
3. **Semantic resemblance needs an embedding runtime** in the checkout plus adjudication
   capacity for the 162 unadjudicated gold pairs. The control's AUC 0.754 is the baseline any
   candidate must beat.
4. **The Ask formal regrade is incomplete.** The run reached 31 of 60 and stopped at Q32
   with an `APIConnectionError` from the provider — transient, not quota. Run identity is
   commit-keyed so the 31 cannot be resumed from a later commit; a fresh run is needed. On
   the 31: 115 citations, **0 invented citations surviving**, 2 uncited answers (Q05, Q20), 4
   safety probes fired and all four correctly refused their false premise. `MISLEADING` is
   adjudicated by reading, so **misleading = 0 is not claimed**.
5. **`GAP-SEMANTIC-SIGNATURE-COVERAGE-001`** — 15 declared predicates, the model-extracted
   semantic layer plus `QA_ISSUE_ON`, have no endpoint signature. Pinned as an exact set so
   the population cannot grow.
6. **The 1,021 audible reviews.** 0 heard. Parallel track; blocks nothing here.

## Registry

`data/gap_registry.json` — **85 gaps**. Two opened this round,
`GAP-AV-CHANDOMETRE-SEGMENTATION-001` and `GAP-SEMANTIC-SIGNATURE-COVERAGE-001`, both
`MEASURED` and both produced by a check that tried to falsify its own result.

## Artifacts

In `data/staging/integration/`: `whitney_resolution.json`, `semantic_rederivation.json`,
`declaration_provenance.json`,
`m8_internal_boundary_receipt.json`, `dependency_ledger.json`, `dependency_status.json`,
`corpus_deletion_audit.json`, `ritual_step_identity_probe.json`,
`m7_ritual_step_identity_receipt.json`, `attribution_gate_b.json`,
`attribution_gate_c.json`, `attribution_readback.json`, plus the Wave 3 set.

## Corpus deletions

41 nodes, all ratified, all enumerated in `corpus_deletion_audit.json`, **none this round or
in round three**. The audit replays both versions of the reachability rule and exits non-zero
if the ratified 12 / 2 / 27 split stops reproducing.

## Next

A owner decision on the AV metre segmentation · B Whitney, behind A · C an embedding runtime
for semantics · D audible reviews. **Wave 4 is a separate adversarial round and must not
begin inside this work.**

## Environment

```
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
```
Frontend 3000 · API 127.0.0.1:8000 · Neo4j 7474/7687 (Docker `vedagraph-neo4j`).
Graph: `docker exec vedagraph-neo4j cypher-shell -u neo4j -p vedagraph_dev --format plain "<Q>"`
On Git Bash prefix `docker run` with `MSYS_NO_PATHCONV=1` or `/backups` is rewritten.

Restore: `docker stop vedagraph-neo4j`, then `docker run --rm -v infra_neo4j_data:/data -v
/d/vedanvaya-backups/<stamp>:/backups neo4j:5.26-community neo4j-admin database load neo4j
--from-path=/backups --overwrite-destination=true`, then `docker start`. The dump must be
named `neo4j.dump` inside a timestamped directory. Neo4j reinstalls its GDS plugin on start,
so allow a minute before the first query.

## Rules a resuming session must not break

1. **No gate may derive its allowed universe from the data it validates.** Three gates broke
   this rule; each was green while measuring nothing.
2. A gate that cannot fail is worse than no gate. Make it a pure function of (observed,
   declared) so a test can withdraw a declaration and watch it go red.
3. An importer's own report is not evidence. Only the census diff and the readback caught the
   two worst Wave 3 defects.
4. Every mutation the writer performs must be in the promise. One registry that raises on an
   undeclared entry, never two lists.
5. Counts are not a fingerprint. A swap of equal size leaves them unchanged.
6. A timestamp is never staleness truth. Content hashes are.
7. `count(r)` over an `UNWIND … MERGE` counts operations. Landed > sent is impossible.
8. `MERGE (n:Label {key})` matches on label **and** properties — it creates a twin.
9. A finding must report a breakdown of its own set, and a heuristic that cannot bound a
   population must say so rather than pick its most convenient estimate.
10. `x or -1` turns a correct 0 into a failure. The passing value is often the falsy one.
11. Normalization is a comparison instrument, never identity evidence — and a registry lookup
    is only independent evidence if the vocabulary it resolves into is sound.
12. Never turn NOT ASSESSED into VERIFIED ZERO. The graph can now tell them apart.
13. An unclassified label defaults to PUBLIC, so forgetting to classify exposes rather than
    hides. 2,568 internal verdicts shipped that way.
14. Never map another recension onto the one we hold — Jaiminīya is not Kauthuma, Taittirīya
    and Kāṇva are not Mādhyandina, Paippalāda is not Śaunaka.
15. Automated matching is not audible verification, and unlistened rows are never promoted.
