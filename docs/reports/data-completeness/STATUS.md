# Post-V1 Data Completeness Campaign — STATUS

**A new session should be able to resume from this file alone. Keep it current.**

- Branch: `phase-data-completeness-v2`
- Start commit: `d6e93a92c4e3ff1a5682a17b20bf32c6ce8fa19c`
- Product V1 tag: `vedanvaya-v1.0.0` — FROZEN, must not be altered
- Last updated: 2026-09-15, Wave 0 in flight

## Current wave

**WAVE 0** — gap census, corpus audit, source reconnaissance. No canonical graph mutation.

| Agent | Role | State |
|---|---|---|
| 1 | Gap census / product miner | RUNNING |
| 2 | Corpus / structural metadata audit | RUNNING |
| — | Source reconnaissance | RUNNING |

Waves 1-4 not started. The staging contract and its validator are in place, so
Wave 1 can open as soon as the registry is frozen.

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

None yet.

## Next exact command

Wait for the three Wave 0 agents. On completion: reconcile their three reports into
`data/gap_registry.json` as the single source of truth, assign owners, then open Wave 1
(agents 3–8) against the frozen registry.

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
