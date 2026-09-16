# Post-V1 Data Completeness Campaign — STATUS

**Resume from this file. Rewrite it whole; never splice sections in.**
Guard: `python scripts/validate_status_report.py`

- Branch `phase-data-completeness-v2` · start commit `d6e93a9` · tag `vedanvaya-v1.0.0` FROZEN
- Last rewritten 2026-09-16, after owner round three: M7, attribution, dependent rebuilds

## Where the campaign is

**Wave 3 is closed. The attribution census is imported. Six of nine dependents are CURRENT.**

Three independent gates, two of them not mine:

- `scripts/attribution_import.py --readback` → `READBACK_CLEAN`, 0 findings
- `scripts/graph_quality_scorecard.py` → **9 of 9**, now including a gate that could
  previously not fail at all
- `pytest tests/api` → **1,366 passed, 0 failed**; `pnpm test` → **434 passed**

Do not reopen Wave 3. This graph is the baseline; a verified dump of it exists.

## Canonical graph

| | Product V1 | After Wave 3 | Now |
|---|---:|---:|---:|
| Nodes | 108,779 | 116,825 | **116,838** |
| Relationships | 265,295 | 281,290 | **281,290** |

The last +13 is `:DerivedMetric`, from the coverage rebuild. Core corpus unchanged and
asserted on every run: RV 10,552 · SV 1,844 · YV 1,975 · AV 5,839 = 20,210.

Backup: `D:\vedanvaya-backups\wave3-final-baseline-20260916T101224\neo4j.dump`
117,924,267 bytes · sha256 `6da4d69f…a980ce`. Taken before any round-three mutation.

## Round three — what changed

### M7 · `:RitualStep` product identity

The grain was **measured, not chosen**, over 3,123 importable rows:

| grain | distinct | values covering rows that **disagree** |
|---|---:|---:|
| `SOURCE_OCCURRENCE` | 2,767 | 308 |
| `RITE_SPECIFIC_OCCURRENCE` | 3,122 | 1 |
| `POSITION_BASED` | 1,137 | 680 |

Source-occurrence would merge 308 identities standing for different claims — one sutra is
cited for several rites. Position-based fails outright: `step_position` restarts inside every
work. So the grain is **rite-specific occurrence**, and the `step_key` Wave 3 already staged
is exactly that: rite + work + printed source coordinate, with a canonical URN and
`uuid5(7c8cde94-…, urn)` reproduced byte-identically for all 3,123 rows.

No identity was invented. M7 writes one property, `display_type = "RITUAL_STEP"`, on 3,121
nodes — 0 node and 0 relationship delta. `HAS_RITUAL_STEP` is now traversable and a step
resolves by its own id; it is **not** a path predicate, because a path hopping rite → step →
rite would assert a relation between two rites that share only a sutra collection.

One collision stays withheld and is now a registered gap: SankhSS 16.15.13 prints two sutras
under one citation, so the locator cannot separate them. The graph holds 0 collisions of any
kind.

### Attribution · census imported, Whitney withheld

23,003 rows, two populations that share a file and nothing else. Gates B and C were both run
from scratch; nothing was inherited from the domain's own report.

| population | rows | outcome |
|---|---:|---|
| Census (`DETERMINISTIC_DERIVED`) | 22,537 | **imported** as 3 properties per passage |
| Whitney index (`SOURCE_EXPLICIT`) | 466 | **withheld**, `RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT` |

- **Gate B**, 18 checks, one finding: all 466 Whitney rows carry
  `entity_resolution_method = VERBATIM_SOURCE_STRING_NOT_RESOLVED`. The object of each is a
  printed Sanskrit string resolving to no node, and an edge needs a node at the far end.
- **Gate C**, adversarial: the census claims to describe this graph, so the graph was used
  against it. All **67,611** state assertions checked against the edges that actually exist,
  stratified 38 ways by Veda × dimension × state — **0 contradictions**. The Whitney rows
  were checked against their own printed source: every stated verse address appears verbatim
  in the bracket, every address covers the verse it claims, no address overruns its hymn.

The import wrote 97,114 properties across 22,537 passages and created nothing. What it buys
is a distinction the graph could not previously make:

| dimension | `NEVER_ASSESSED` | `ASSESSED_SOURCE_ABSENT` | `NOT_APPLICABLE` |
|---|---:|---:|---:|
| rishi | 2,945 | 1,446 | 568 |
| devata | 4,920 | 1,832 | 568 |
| chandas | 4,920 | 1,984 | 568 |

Before this, all three read as one silence, and a consumer counting attributed mantras could
not tell a source that says nothing from a source nobody has opened.

### The ritual procedure reaches the product

The rituals page rendered only the Samhita layer, so **102 of 103 rites displayed "not built"
for order** while the graph held 3,121 sutra-attested steps for them. That is a stale
limitation caused by unfinished implementation, not by evidence, and it is now removed.

The new section groups by source work and is styled deliberately unlike the numbered run
above it. That block renders a sequence; this layer is not one, and borrowing its visual
grammar would assert through layout what the prose beside it denies.

## Dependents — 6 CURRENT, 1 not applicable, 2 blocked

`scripts/rebuild_ledger.py --status`. `CURRENT` means a recorded rebuild whose input hash
still equals the current one, scoped to the labels and predicates that consumer declares it
reads — a measurement, not a flag.

| consumer | status | note |
|---|---|---|
| cross-Veda matrices | CURRENT | enrichment rebuilt, 26 offline checks, 6,285 parallels |
| formula / parallel / variant | CURRENT | byte-identical output; not stale in effect |
| entity coverage | CURRENT | `DerivedMetric` 1,072 → 1,085 |
| quality evaluation | CURRENT | scorecard 9/9 |
| Visualization Lab | CURRENT | 38,244 public nodes, 196,128 public edges |
| Knowledge World | CURRENT | same projection |
| ritual aggregates | NOT_APPLICABLE | no aggregate exists to rebuild |
| semantic resemblance | BLOCKED | see below |
| Ask retrieval | BLOCKED | see below |

## Blocking

1. **Semantic resemblance is not re-derived.** The staged artifact is pre-Wave-3
   `semantic-resemblance-hybrid-v2`, and owner section 8 bars importing an old score artifact
   because it exists. Re-derivation needs the embedding pipeline against the final snapshot
   plus its full validity report — pool size, corpus-product recall, dev/test metrics,
   lexical-control comparison, translation-confound exclusions, threshold, refusal
   conditions. **0 rows imported.** Verified refusal is an acceptable outcome; an unverified
   import is not.
2. **The Ask benchmark is not re-graded.** Retrieval reads the graph live — there is no index
   artifact — and its 280 contract tests pass against the final graph. Only the graded run is
   stale, and re-grading burns a daily quota, so it needs a deliberate run.
3. **466 Whitney attributions need entity resolution.**
   `GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001`. The rows are correct; what is missing is a
   way to resolve a verbatim printed string to an identity on evidence other than surface
   equality.
4. **The 1,021 audible reviews.** 0 heard. Parallel track; it blocks nothing here.
5. **Six Wave 3 labels are still undeclared as product labels** — `RoleFiller`,
   `QualityVerdict`, `ScholarlyDisagreement`, `Scholar`, `ScholarlyWork`, `DeityCommunity`.
   Only `RitualStep` was declared, because only it needed to be. They are invisible to
   `/api/v1/entities` until declared.

## Two gates that could not fail

Both were passing while measuring nothing. Recorded because the pattern recurs.

- **Undeclared relationship types.** `declared = ONTOLOGY | everything in the graph`, then
  "which graph types are missing from `declared`?" — structurally empty. It reported 0 for a
  whole wave while eleven Wave 3 predicates went unclassified. Now measured against the API's
  product contract, which a live test holds complete.
- **Dependency staleness.** Computed from wave stamps that never come off, so every consumer
  read `STALE_INPUT` for ever and a rebuild could not be expressed at all.

## Registry

`data/gap_registry.json` — **83 gaps**. Two opened this round, both `MEASURED` and both
produced by a gate that tried to falsify the data:
`GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001`, `GAP-RITUAL-STEP-LOCATOR-COLLISION-001`.

## Artifacts

In `data/staging/integration/`: `ritual_step_identity_probe.json`,
`m7_ritual_step_identity_receipt.json`, `corpus_deletion_audit.json`,
`attribution_gate_b.json`, `attribution_gate_c.json`, `attribution_plan.json`,
`attribution_import_receipt.json`, `attribution_readback.json`, `rebuild_ledger.json`,
`dependency_status.json`, plus the Wave 3 set.

## Corpus deletions, ratified and enumerated

41 nodes, all created by this campaign, all unsupported after the importability filter, all
edgeless, all recoverable. **None this round.** Reconstructed rather than remembered by
`scripts/corpus_deletion_audit.py`, which replays both versions of the reachability rule and
exits non-zero if the ratified split stops reproducing.

| batch | n | reason |
|---|---:|---|
| evidence not imported | 12 | attested only in a Brāhmaṇa or Śrautasūtra |
| attestation without locator | 2 | `samhita_attested` with no example; the file has no such field |
| reachable only via a refused edge | 27 | named only by a rite edge staged `PROBABLE` |

## Next

A semantic resemblance re-derivation · B Whitney entity resolution · C Ask re-grade ·
D audible reviews. **Wave 4 must not begin** until A–C resolve and every importable domain is
readback-complete.

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
named `neo4j.dump` inside a timestamped directory.

## Rules a resuming session must not break

1. An importer's own per-group report is not evidence. Only the census diff and the readback
   caught the two worst Wave 3 defects.
2. A gate that cannot fail is worse than no gate. Two were found this round; before writing a
   membership test, check that the reference set is not derived from the thing under test.
3. Every mutation the writer performs must be in the promise. One registry that raises on an
   undeclared entry, never two lists.
4. `count(r)` over an `UNWIND … MERGE` counts operations. Landed > sent is impossible.
5. `MERGE (n:Label {key})` matches on label **and** properties — it creates a twin.
6. Never carry a referent's identity key onto the referrer.
7. A node nothing points at is not imported data; compute reachability over the edges that
   will exist, not the rows.
8. A finding must report a breakdown of its own set. One counted 27 and printed a breakdown
   summing to 40.
9. `x or -1` turns a correct 0 into a failure. The passing value is often the falsy one.
10. Normalization is a comparison instrument, never identity evidence. No join on display
    labels, across scripts or otherwise.
11. Never turn NOT ASSESSED into VERIFIED ZERO. The graph can now tell them apart — keep it
    that way.
12. Never map another recension onto the one we hold — Jaiminīya is not Kauthuma, Taittirīya
    and Kāṇva are not Mādhyandina, Paippalāda is not Śaunaka.
13. Never attach a long recording to an exact mantra without verified boundaries, and
    automated matching is not audible verification.
14. Enumerate a field's value space before concluding it is empty.
