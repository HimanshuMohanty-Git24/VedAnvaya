# Post-V1 Data Completeness Campaign — Frozen Baseline

Recorded before any campaign work. Every figure below was measured against the live
system on this date, not copied from a previous report.

- Campaign branch: `phase-data-completeness-v2`
- Start commit: `d6e93a92c4e3ff1a5682a17b20bf32c6ce8fa19c`
- Product V1 tag (frozen, untouched): `vedanvaya-v1.0.0`
- Measured: 2026-09-15
- Neo4j snapshot: `D:\vedanvaya-backups\vedanvaya-v1.0.0-preflight-20260915T105606.dump`
  - 96,844,203 bytes
  - sha256 `98f71b641f608c8fd1aa3082ef4b88f7d983687d2996aa5b1c7528effc83b981`
  - Taken with the container stopped, verified by restarting and re-counting.

## Graph census

| Measure | Count |
|---|---|
| Nodes | 108,779 |
| Relationships | 265,295 |
| Works | 4 |
| Ontology version carried by the graph | `vedagraph-knowledge-model-v2` |

Matches the stated Product V1 baseline exactly.

## Core corpus — verification of the campaign's stated totals

`Passage` nodes total 22,537, of which 20,210 also carry `:Mantra`. The remaining 2,327
are structural containers (books, hymns, chapters), not mantras.

| Veda | Recension | Stated | Measured | Verdict |
|---|---|---|---|---|
| RV | Śākala | 10,552 | 10,552 | VERIFIED |
| SV | Kauthuma Ārcika | 1,844 | 1,844 | VERIFIED |
| YV | Mādhyandina (VSM) | 1,975 | 1,975 | VERIFIED |
| AV | Śaunaka | 5,839 | 5,839 | VERIFIED |
| **Total** | | **20,210** | **20,210** | **VERIFIED** |

## Dimension coverage at baseline

Counted as "mantras with at least one outgoing edge of the relevant type".

| Dimension | RV /10,552 | SV /1,844 | YV /1,975 | AV /5,839 |
|---|---|---|---|---|
| Translation | 10,502 | 0 | 1,903 | 4,878 |
| Rishi | 10,534 | 0 | 1,960 | 4,542 |
| Devata (`HAS_DEVATA`) | 10,552 | 0 | 0 | 0 |
| Chandas | 10,518 | 0 | 0 | 4,082 |
| Semantic assertion | 2,542 | 0 | 0 | 0 |
| Entity mention | 8,143 | 1,306 | 1,358 | 4,292 |
| Lemma | 6,560 | 0 | 0 | 0 |
| Formula | 5,103 | 1,311 | 1,214 | 2,946 |

### Translation gap
50 + 1,844 + 72 + 961 = **2,927**. The campaign brief stated 2,927. VERIFIED.

### Audio gap
From `/api/v1/audio/stats`: 16,834 records, all `MANTRA` / `RECITATION` / `EXACT` /
`AVAILABLE` / `PROXIED_STREAM`, 0 locally cached.

| Veda | Mapped | Total | Gap |
|---|---|---|---|
| RV | 10,402 | 10,552 | 150 |
| SV | 0 | 1,844 | 1,844 |
| YV | 1,752 | 1,975 | 223 |
| AV | 4,680 | 5,839 | 1,159 |
| **Total** | **16,834** | **20,210** | **3,376** |

The brief stated 16,834 mapped and ~3,376 uncovered. Both VERIFIED.

## Notable structural findings already visible at baseline

1. `HAS_DEVATA` exists for the Rigveda only. Dedication is unmodelled for SV, YV and AV —
   three quarters of the recensions, 9,658 mantras.
2. `HAS_SEMANTIC_ASSERTION` is Rigveda-only and covers 2,542 of 10,552 RV mantras
   (24.1%), so it is partial even there.
3. `MENTIONS_LEMMA` is Rigveda-only.
4. Chandas is absent for SV and YV entirely.
5. Samaveda has zero translations, zero audio, zero attribution of any kind. It is
   present as Sanskrit text, formula membership and entity mentions only.

None of these five is a scope decision on record. Each is unfinished work.

## Environment at baseline

| Service | Port | State |
|---|---|---|
| Frontend (Next dev) | 3000 | fresh |
| API (uvicorn) | 127.0.0.1:8000 | fresh, `/ready` true |
| Neo4j (Docker `vedagraph-neo4j`) | 7474 / 7687 | restarted, healthy, census re-verified |

A stale frontend was found serving port 3100 from an earlier session and was stopped;
the canonical port is 3000.
