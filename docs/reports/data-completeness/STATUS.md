# Post-V1 Data Completeness Campaign — STATUS

**A resuming session should be able to work from this file alone. Keep it current, and
rewrite it rather than splicing sections into it — see the note at the end.**

- Branch: `phase-data-completeness-v2`
- Start commit: `d6e93a92c4e3ff1a5682a17b20bf32c6ce8fa19c`
- Product V1 tag: `vedanvaya-v1.0.0` — FROZEN, must not be altered
- Last rewritten: 2026-09-15, Wave 2 in progress

## Where the campaign is

**WAVE 0 CLOSED** (`WAVE_0_CLOSURE.md`) · **WAVE 1 CLOSED** (`WAVE_1_CLOSURE.md`) ·
**WAVE 2 in progress**, 4 of 8 agents returned.

**Nothing is imported.** The graph stands at 108,779 nodes / 265,295 relationships,
re-counted after every agent. Every coverage figure in this campaign is
**STAGED_PROJECTED_COVERAGE** until Wave 3 ingests and reads the counts back out of the
database (owner section F). None of it may reach the frontend, API, release docs or any
public report before then.

| Agent | Role | State |
|---|---|---|
| 1 | Gap census | DONE — 74 gaps |
| 2 | Corpus audit | DONE — 20,210 rows, 11 defects |
| — | Source reconnaissance | DONE — 67 sources |
| 3 | Translation | DONE — 1,514 stageable |
| 4 | Rigveda audio | DONE — 150 of 150 |
| 5 | Samaveda audio + music | DONE — melodic layer created |
| 6 | Yajurveda audio | DONE — 25 recovered |
| 7 | Atharvaveda audio | DONE — 764 recovered |
| 8 | Attribution / entity | DONE |
| 9 | Morphology + semantic roles | DONE — four Vedas reached |
| 10 | Cross-Veda matrix | DONE — 48 cells, none unresolved |
| 11 | Semantic resemblance | RUNNING |
| 12 | Formula / parallel / variant | DONE — nothing stale |
| 13 | Ritual expansion | RUNNING |
| 14 | Scholarly disagreement | RUNNING |
| 15 | Deity communities | DONE — computed and REFUSED |
| 16 | Quality reference set | RUNNING |

All ten returned artifacts pass `validate_staging_artifact.py --graph` at 100% evaluation
coverage: 55,602 rows, 54,847 strong (`EXACT` or `VERIFIED_SEGMENT`).

Wave 3 is planned but not started — `WAVE_3_INTEGRATION_PLAN.md`.

## Owner decisions in force

Recorded as an overlay in `data/staging/lead_overlays/wave1_decisions.json`, applied after
artifacts are read rather than by editing them, because artifacts are immutable and
checksummed. **The import must read overlays, or it will import rows the owner barred.**

- **A** — RV 1.65–1.70 barred until the coordinate repair is applied. Artifact in
  `data/staging/rv_coordinate_repair/`; step 7 verified 10/10 by hand-chosen anchors. Note
  the affected layer is **translations**: that span's audio is 61 of 61, all `EXACT` and
  `text_verified`.
- **B** — `REMOTE_DIRECT` accepted for the Rigvedic 150. Range supported
  (`accept-ranges: bytes`, 206 verified). Caching blocked by the source's written-agreement
  requirement, so `local_copy_permitted` is false.
- **C** — the 31 forced Yajurvedic addresses barred. Accepted recovery is **19, not 50**.
- **D** — LOAR inventoried (`loar-inventory.md`), 22 items, **no coverage claimed**. No item
  is a Kauthuma ārcika recitation, so the Samavedic gap is not closed by it.
- **E** — **audio import gate CLOSED.** `data/staging/audio_review_queue.jsonl`, 1,021 rows,
  all `NEEDS_AUDIBLE_REVIEW`, **0 reviewed**. 793 carry a blind unlabelled neighbour pair.
  Zero segmented rows, so no boundary review is owed.
- **F** — staged figures stay staged. See above.
- **G** — registry causation separated; see below.

## Registry

`data/gap_registry.json` — **80 gaps**: 67 `IMPLEMENTATION_GAP`, 8 `STALE`,
5 `TRUE_SCOPE_FACT`. All `OPEN`; nothing closes until Wave 3 imports and re-reads.

**11 entries carry `causation_status: MEASURED`**, with `observed_gap`, `suspected_cause`,
`measured_cause` and `closure_method` separated and the original hypothesis preserved
rather than overwritten. **6 disproven prescriptions are withdrawn.**

Wave 0 registered 74; the lead folded in 6 more that later waves discovered. Specialists
are scoped away from the registry to keep eight agents out of one file, which makes folding
their findings in the lead's job — an unregistered finding escapes the section 43 gate
silently.

## The campaign's recurring error

It assumed absence at the source where the defect was in our own addressing. Five instances
so far, and a resuming session should expect a sixth:

| Looked like | Actually was |
|---|---|
| 223 Yajurvedic verses with no recitation | our comparator, discarding nearly the whole alphabet |
| 1,159 Atharvavedic verses with no recitation | our coordinates, against a source dividing the corpus into 754 sūktas where ours has 731 |
| 72 Yajurvedic mantras with no translation | OCR digit-confusion in our own stage labels |
| 1,975 Yajurvedic mantras with no outgoing parallel | alphabetical Veda-code ordering in the writer, on types declared symmetric |
| 62% Rigvedic lemma coverage | a theonym index of 39 words wearing a lemma layer's name |

**Measure the cause before working the remedy.** Three registry prescriptions sent the
campaign to acquire material it already held.

## Live product defects found, not yet fixed

- **25 shipped translations are on the wrong verse** (RV 1.65–1.70).
  `RV_1_65_TO_1_70_MISALIGNMENT.md`.
- **`occurrence_count`**: null on all 214 `:Devata` and 575 `:Chandas`; two incompatible
  conventions on `:Rishi`, with all 367 Rigveda-only seers at 0 over a complete layer. Ask
  states the figure whenever it is not null.
- **All 1,903 Yajurvedic translations cite a `:Source` that does not exist.**
- **`attribution_scope: ["RV"]` on all 214 `:Devata`** — true of the node, false of the
  corpus.
- **The AV `SEARCH_DERIVATIVE` layer deletes base letters** across 5,839 mantras (`kr̥dhi`
  stored as `kdhi`). Real, but *not* a search outage — query and index are mangled
  identically, so retrieval still works and snippets and precision suffer.
- **The comparator defects are fixed** at `30ba692`, with the invalid calibration replaced.

## Environment

```
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
```
Frontend 3000, API 127.0.0.1:8000, Neo4j 7474/7687 (Docker `vedagraph-neo4j`, managed
outside the repo; the start script checks it and never starts or mutates it).

Graph queries: `docker exec vedagraph-neo4j cypher-shell -u neo4j -p vedagraph_dev --format plain "<QUERY>"`

Before any import: `.venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/<domain> --graph`

## Rollback, tested not assumed

`D:\vedanvaya-backups\vedanvaya-v1.0.0-preflight-20260915T105606\neo4j.dump`
(96,844,203 bytes, sha256 `98f71b641f608c8fd1aa3082ef4b88f7d983687d2996aa5b1c7528effc83b981`).

The dump lives as `neo4j.dump` inside a timestamped directory because
`neo4j-admin database load` matches the archive by database name — a dump renamed to
describe itself fails with "No matching archives found", which is how the first restore
attempt failed.

```
docker stop vedagraph-neo4j
docker run --rm -v infra_neo4j_data:/data -v /d/vedanvaya-backups/<stamp>:/backups \
  neo4j:5.26-community \
  neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
docker start vedagraph-neo4j
```

Proven by loading into a scratch volume, serving it on spare ports and re-counting:
108,779 nodes, 265,295 relationships, RV 10,552 / SV 1,844 / YV 1,975 / AV 5,839. The
scratch volume and container were removed; the live database was never touched.

## Blocking issues

1. **`sacred-texts.com` returns 403** from this host — a Cloudflare bot challenge, not
   transient. It supplied all 1,903 Yajurvedic translations. Routed around via the Internet
   Archive Wayback Machine, which served 144 Atharvavedic pages successfully.
2. **The audio import gate is closed** and needs an audio-capable reviewer. 1,021 queued.
3. **Section 32 needs the assessed set written at assessment time.** Run provenance is
   recorded onto produced artifacts, never onto the mantra examined, so "assessed and empty"
   cannot be distinguished from "never assessed" for any dimension but audio. Wave 1 and 2
   artifacts emit it; the graph still cannot.
4. **No human gold exists anywhere** — 695 rows, 120 `UNANNOTATED`, 575 adjudicated by the
   model family that would be scored. No precision figure in this campaign rests on human
   judgement.

## Rules a resuming session must not break

1. Never mutate the canonical graph outside a lead-run, idempotent, checksummed import that
   reads its counts back out of the database.
2. Never turn NOT ASSESSED into VERIFIED ZERO.
3. Never map another recension onto the one we hold — Jaiminīya is not Kauthuma, Taittirīya
   and Kāṇva are not Mādhyandina, Paippalāda is not Śaunaka.
4. Never attach a long recording to an exact mantra without verified boundaries.
5. Never let a model invent a scholarly disagreement, a translation attribution or a
   timestamp.
6. A limitation card is removed only when data proves closure, never to tidy the copy.
7. **Do not commit a specialist's staging directory until it has reported.** A task
   notification can fire more than once; the Samaveda directory was committed mid-flight and
   three finished files needed a second pickup.
8. **Do not splice sections into this file programmatically.** Successive
   find-the-heading-and-replace edits accumulated duplicates until STATUS.md had grown from
   242 to 935 lines with three `## Registry` sections and two `## Done`. Rewrite the whole
   file, and check its line count afterwards.
