# Post-V1 Data Completeness Campaign — STATUS

**A new session should be able to resume from this file alone. Keep it current.**

- Branch: `phase-data-completeness-v2`
- Start commit: `d6e93a92c4e3ff1a5682a17b20bf32c6ce8fa19c`
- Product V1 tag: `vedanvaya-v1.0.0` — FROZEN, must not be altered
- Last updated: 2026-09-15, Wave 0 in flight

## Current wave

**WAVE 0 CLOSED** (`WAVE_0_CLOSURE.md`). **WAVE 1 CLOSED** (`WAVE_1_CLOSURE.md`).
**WAVE 2 in progress** -- 4 of 8 agents returned.

**Nothing is imported.** Graph unchanged at 108,779 / 265,295, re-counted after every
agent. Every coverage figure in this campaign is STAGED_PROJECTED_COVERAGE until Wave 3
ingests and reads the counts back out of the database (owner section F).

| Agent | Role | State |
|---|---|---|
| 1 | Gap census | DONE |
| 2 | Corpus audit | DONE |
| - | Source reconnaissance | DONE |
| 3-8 | Wave 1, all six | DONE, all validator PASS |
| 9 | Morphology + semantic roles | DONE -- four Vedas reached, PASS |
| 10 | Cross-Veda matrix | DONE -- 48 cells, none unresolved, PASS |
| 11 | Semantic resemblance | RUNNING |
| 12 | Formula / parallel / variant | DONE -- nothing stale, PASS |
| 13 | Ritual expansion | RUNNING |
| 14 | Scholarly disagreement | RUNNING |
| 15 | Deity communities | DONE -- computed and REFUSED, PASS |
| 16 | Quality reference set | RUNNING |

Ten staging domains, 55,602 rows, 54,847 strong. See `WAVE_3_INTEGRATION_PLAN.md`.

## Owner decisions in force

Recorded as an overlay in `data/staging/lead_overlays/wave1_decisions.json`, applied after
artifacts are read rather than by editing them. **The import must read overlays or it will
import rows the owner barred.**

- **A** -- RV 1.65-1.70 barred until the coordinate repair is applied. Repair artifact in
  `data/staging/rv_coordinate_repair/`, step 7 verified 10/10. NB the affected layer is
  translations; that span's audio is 61 of 61, all EXACT and text_verified.
- **C** -- 31 forced Yajurvedic addresses barred. Accepted recovery is 19, not 50.
- **E** -- audio import gate CLOSED. `data/staging/audio_review_queue.jsonl`, 1,021 rows,
  all `NEEDS_AUDIBLE_REVIEW`, **0 reviewed**. 793 carry a blind unlabelled neighbour pair.
  Zero segmented rows, so no boundary review is owed.
- **D** -- LOAR inventoried, 22 items, no coverage claimed. **No item is a Kauthuma arcika
  recitation**, so the Samavedic gap is not closed by it. Two findings outside the Samaveda:
  a CC0 Madhyandina Samhita recitation (rights blocker gone, granularity remains) and a
  Saunaka Atharvaveda at roughly one kanda per file.

#
#
 
R
e
g
i
s
t
r
y




`
d
a
t
a
/
g
a
p
_
r
e
g
i
s
t
r
y
.
j
s
o
n
`
 
-
-
 
*
*
8
0
 
g
a
p
s
*
*
:
 
6
7
 
I
M
P
L
E
M
E
N
T
A
T
I
O
N
_
G
A
P
,
 
8
 
S
T
A
L
E
,
 
5
 
T
R
U
E
_
S
C
O
P
E
_
F
A
C
T
.


A
l
l
 
`
O
P
E
N
`
;
 
n
o
t
h
i
n
g
 
c
l
o
s
e
s
 
u
n
t
i
l
 
W
a
v
e
 
3
 
i
m
p
o
r
t
s
 
a
n
d
 
r
e
-
r
e
a
d
s
.




*
*
1
1
 
e
n
t
r
i
e
s
 
n
o
w
 
c
a
r
r
y
 
`
c
a
u
s
a
t
i
o
n
_
s
t
a
t
u
s
:
 
M
E
A
S
U
R
E
D
`
*
*
 
w
i
t
h
 
o
b
s
e
r
v
e
d
_
g
a
p
,
 
s
u
s
p
e
c
t
e
d
_
c
a
u
s
e
,


m
e
a
s
u
r
e
d
_
c
a
u
s
e
 
a
n
d
 
c
l
o
s
u
r
e
_
m
e
t
h
o
d
 
s
e
p
a
r
a
t
e
d
,
 
a
n
d
 
*
*
6
 
d
i
s
p
r
o
v
e
n
 
p
r
e
s
c
r
i
p
t
i
o
n
s
 
a
r
e
 
w
i
t
h
d
r
a
w
n
*
*


(
o
w
n
e
r
 
s
e
c
t
i
o
n
 
G
)
.
 
E
a
c
h
 
o
r
i
g
i
n
a
l
 
h
y
p
o
t
h
e
s
i
s
 
i
s
 
p
r
e
s
e
r
v
e
d
 
r
a
t
h
e
r
 
t
h
a
n
 
o
v
e
r
w
r
i
t
t
e
n
.




T
h
e
 
c
a
m
p
a
i
g
n
 
g
o
t
 
t
h
e
 
s
a
m
e
 
k
i
n
d
 
o
f
 
g
u
e
s
s
 
w
r
o
n
g
 
r
e
p
e
a
t
e
d
l
y
:
 
i
t
 
a
s
s
u
m
e
d
 
a
b
s
e
n
c
e
 
a
t
 
t
h
e
 
s
o
u
r
c
e


w
h
e
r
e
 
t
h
e
 
d
e
f
e
c
t
 
w
a
s
 
i
n
 
o
u
r
 
o
w
n
 
a
d
d
r
e
s
s
i
n
g
.
 
F
o
u
r
 
a
u
d
i
o
 
a
n
d
 
t
r
a
n
s
l
a
t
i
o
n
 
g
a
p
s
,
 
t
h
e
 
Y
a
j
u
r
v
e
d
i
c


p
a
r
a
l
l
e
l
 
a
s
y
m
m
e
t
r
y
,
 
a
n
d
 
a
 
l
e
m
m
a
 
l
a
y
e
r
 
t
h
a
t
 
w
a
s
 
n
e
v
e
r
 
a
 
l
e
m
m
a
 
l
a
y
e
r
.




## Registry

`data/gap_registry.json` - **80 gaps**: 67 IMPLEMENTATION_GAP, 8 STALE, 5 TRUE_SCOPE_FACT.
All `OPEN`; nothing is closed until Wave 3 imports and re-reads the counts.

Wave 0 registered 74; the lead folded in 6 more that Wave 1 discovered, because specialists
are scoped away from the registry to keep six agents out of one file. An unregistered
finding escapes the section 43 gate silently.

Three registry prescriptions were measured and found wrong - see WAVE_1_CLOSURE.md. A gap
entry is a hypothesis about a cause, and working one without measuring it first is how a
campaign spends a week acquiring material it already held.


## Registry

`data/gap_registry.json` - **79 gaps**: 66 IMPLEMENTATION_GAP, 8 STALE, 5 TRUE_SCOPE_FACT.
All `OPEN`. 19 populations `null` with a stated reason; the 10 zeros are measured zeros on
STALE findings, not unknowns.

Wave 0 registered 74. The lead folded in 5 more that Wave 1 discovered, because specialists
are scoped away from the registry to keep six agents out of one file - which makes folding
their findings in the lead's job, not an optional tidy-up. An unregistered finding escapes
the section 43 gate silently.

The five: `GAP-QUALITY-006` (occurrence_count), `GAP-ATTRIBUTION-009` (attribution_scope),
`GAP-SAMAVEDA_MUSIC-003` (the missing arcika-gana join key), `GAP-OTHER-006` (the
comparator defects), `GAP-ENTITY_COVERAGE-008` (registry contamination).


## Registry

`data/gap_registry.json` — 74 gaps: 62 IMPLEMENTATION_GAP, 7 STALE, 5 TRUE_SCOPE_FACT.
All `OPEN`. Owners 3-16 assigned. 17 populations `null` with a stated reason; the nine
zeros are measured zeros on STALE findings, not unknowns.

## What Wave 0 changed about the plan

- AV translation gap is **one acquisition**: 958 of 961 are kanda 20, plus exactly three
  strays (3.9.4, 5.12.11, 10.8.30). Verified.
- YV's 72 may not be a gap at all -- concentrated in adhyaya 12 (25) and 23 (13), plausibly
  Griffith's own cross-references. **Check two local snapshots before sourcing anything.**
- ~43% of the AV audio gap is probably ours: 495 of 1,159 are recorded `text_mismatch`,
  the signature of a numbering offset. Same pattern on 33 YV rows.
- Samaveda audio is **not source-blocked** -- 475 licence-clean Ogg files on Commons, none
  fetched -- but every one is `PAGE_LEVEL` and they are gana performances, not arcika
  recitation. Needs boundary verification plus a separate gana Work identity.
- SV morphology is genuinely unavailable: three independent negatives (DCS, UD, VedaWeb).
- No layer may be called human gold: 120/120 semantic gold rows are `UNANNOTATED`, and the
  only populated set was adjudicated by the model family that would be scored.

## Done


## Done

- Stale servers cleared. A frontend was found on port 3100 from an earlier session;
  canonical is 3000. All of 3000–3299, 4000, 5000, 5173, 8000–8888 were confirmed clear
  before restart.
- Neo4j container restarted; census re-verified after restart.
- Pre-campaign snapshot taken and **restore-tested**:
  `D:\vedanvaya-backups\vedanvaya-v1.0.0-preflight-20260915T105606\neo4j.dump`
  (96,844,203 bytes, sha256 `98f71b641f608c8fd1aa3082ef4b88f7d983687d2996aa5b1c7528effc83b981`).

  The dump is kept in a timestamped *directory* under the name `neo4j.dump`, because
  `neo4j-admin database load` matches the archive by database name. A dump renamed to
  describe itself fails with "No matching archives found" -- which is how the first
  restore attempt failed, and why the restore is tested rather than assumed.

  Rollback, verified on a throwaway volume rather than trusted:

  ```
  docker stop vedagraph-neo4j
  docker run --rm -v infra_neo4j_data:/data -v /d/vedanvaya-backups/<stamp>:/backups \
    neo4j:5.26-community \
    neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
  docker start vedagraph-neo4j
  ```

  Proven by loading into a scratch volume, serving it on spare ports and re-counting:
  108,779 nodes, 265,295 relationships, RV 10,552 / SV 1,844 / YV 1,975 / AV 5,839.
  The scratch volume and container were then removed; the live database was never
  touched by the test.
- Baseline frozen in `BASELINE.md`. **Every figure in the campaign brief was measured
  against the live system and verified**: graph census, all four corpus totals, the 20,210
  mantra total, the 2,927 translation gap, the 3,376 audio gap.

## How to bring the environment up

```
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
```
Frontend 3000, API 127.0.0.1:8000, Neo4j 7474/7687 (Docker `vedagraph-neo4j`, started
outside the repo — `start-product.ps1` checks it and never starts or mutates it).

Graph queries: `docker exec vedagraph-neo4j cypher-shell -u neo4j -p vedagraph_dev --format plain "<QUERY>"`

## Graph census

| | Nodes | Relationships |
|---|---|---|
| Product V1 baseline | 108,779 | 265,295 |
| Current | 108,779 | 265,295 |
| Delta | 0 | 0 |

## The largest known gaps, measured

| Gap | Missing | Owner |
|---|---|---|
| SV translations | 1,844 of 1,844 — none exist | 3 |
| SV audio | 1,844 of 1,844 — none catalogued | 5 |
| Non-RV Devata dedication | 9,658 mantras — `HAS_DEVATA` is RV-only | 8 |
| SV + YV Chandas | 3,819 — absent entirely | 8 |
| AV audio | 1,159 | 7 |
| AV translations | 961 | 3 |
| YV audio | 223 | 6 |
| RV audio | 150 | 4 |
| YV translations | 72 | 3 |
| RV translations | 50 | 3 |
| Samavedic melodic layer | no layer of any kind exists | 5 |
| Semantic resemblance | no such predicate exists | 11 |
| Semantic assertions outside RV | RV-only, and 2,542/10,552 even there | 9 |
| Lemma / morphology outside RV | RV-only | 9 |
| Scholarly disagreement layer | does not exist | 14 |
| Deity communities | no partition exists | 15 |
| Ritual layer | ~8 rites, 3 step edges, 14 implements | 13 |

## Lead-owned machinery in place

- `docs/reports/data-completeness/INGESTION_CONTRACT.md` -- the staging contract every
  specialist artifact must satisfy before import.
- `scripts/validate_staging_artifact.py` -- enforces it. Reports coverage of its own
  checks rather than just their pass rate, and reports unknown enum values rather than
  defaulting them. Run it with `--graph` before any import: that resolves every canonical
  key against the live store and checks the row's claimed veda against the node's.
  Exercised against both a ten-defect fixture and a conformant one before use.

## Blocking issues

1. **`sacred-texts.com` returns 403 from this host.** Re-probed by the lead: 403 direct and
   403 after following its own www redirect. It supplied the 1,903 YV translations from
   snapshots taken 2026-09-07, and the AV kanda-20 acquisition depends on it. **Wave 1
   step 1 is a reachability re-probe;** if it stays down, kanda 20 needs an independent
   host.
2. **IGNCA's 40 `SYMS_CHAP_*.mp3` are still 404**, re-verified 17 months on. YV Madhyandina
   audio would have to be commissioned -- a genuine external unavailability, and a
   candidate for BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE once three avenues are documented.
3. **Section 32 is unreportable as the graph stands.** Run provenance is written onto
   produced artifacts, never onto the mantra examined, so "assessed and empty" cannot be
   told from "never assessed" for any dimension but audio. Every Wave 1 artifact must
   therefore emit its assessed set, not just its positives.


## Next exact command

Wave 1 is running as agents 3-8 against the frozen registry. Each writes to
`data/staging/<domain>/` and nothing else, and must satisfy the ingestion contract.

Before importing any Wave 1 artifact:

```
.venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/<domain> --graph
```

`--graph` is not optional for an import: it resolves every canonical key against the live
store and checks the row's claimed veda against the node's.

Wave 1's own first step, before acquisition: re-probe `sacred-texts.com`, and read the two
local snapshots that settle whether the YV 72 are real gaps or Griffith cross-references.


## Rules a resuming session must not break

1. Never mutate the canonical Neo4j graph outside a lead-run, idempotent, checksummed
   import. Specialists write to `data/staging/<domain>/` only.
2. Never turn NOT ASSESSED into VERIFIED ZERO.
3. Never map another recension's material onto the one we hold — Jaiminīya is not
   Kauthuma, Taittirīya is not Mādhyandina, Paippalāda is not Śaunaka.
4. Never attach a long recording to an exact mantra without verified boundaries.
5. Never let a model invent a scholarly disagreement, a translation attribution, or an
   audio timestamp.
6. A limitation card is removed only when data proves closure, never to tidy the copy.
