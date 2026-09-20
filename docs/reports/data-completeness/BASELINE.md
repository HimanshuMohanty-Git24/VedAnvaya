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
| Devata (`HAS_DEVATA_ASCRIPTION`) | 0 | 0 | 0 | 4,160 |
| **Dedication, either mechanism** | **10,552** | **0** | **0** | **4,160** |
| Chandas | 10,518 | 0 | 0 | 4,082 |
| Semantic assertion | 2,542 | 0 | 0 | 0 |
| Entity mention | 8,143 | 1,306 | 1,358 | 4,292 |
| Lemma (see the warning below) | 6,560 | 0 | 0 | 0 |
| Formula | 5,103 | 1,311 | 1,214 | 2,946 |

### The Lemma row is true and misleading. Read this before using it.

`6,560` is the number of Rigvedic mantras carrying at least one `MENTIONS_LEMMA` edge. It
is arithmetically correct. It also invites the inference that the Rigveda has 62%
lemma coverage, and that is false.

| Measure | Count |
|---|---|
| `:Lemma` nodes | 10,031 |
| `:Lemma` nodes with no edge in either direction | 9,992 (99.6%) |
| `MENTIONS_LEMMA` edges | 9,000 |
| **Distinct lemmas those edges reach** | **39** |

Every one of the 39 is a theonym: `índra-` (2,305 edges), `agní-` (1,604), `sóma-` (950),
`aśvín-`, `marút-`, `váruṇa-`, `sū́rya-`, `uṣás-`, `pr̥thivī́-`, `mitrá-`, `savitár-`,
`áditi-` and so on. So `MENTIONS_LEMMA` is not a lemma layer. It is a theonym mention
index wearing a lemma layer's name, and 9,992 of the 10,031 lemma nodes are inert.

This matters twice over. It is the largest single overstatement in this baseline, and it is
the exact failure this campaign was convened to prevent -- a row whose every figure is
right and whose meaning is wrong -- sitting in the campaign's own frozen baseline. It was
found by an independent census agent, not by the lead who wrote the row.

The correct reading: morphological coverage is not 62% of the Rigveda. It is 39 lemmas
across the whole corpus, and there is no morphology layer for any of the four recensions.


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

Findings 1 and 5 were corrected after Agent 2's independent audit. Both original
statements are kept visible rather than quietly rewritten, because the way they were
wrong is instructive.

1. **CORRECTED.** This baseline first said dedication was unmodelled for SV, YV and AV --
   9,658 mantras. That was wrong, and wrong in a way this project has been caught by
   before: the attribution axis has more than one mechanism, and counting only the obvious
   one under-reports the data that exists. `HAS_DEVATA` is indeed Rigveda-only, but the
   Atharvaveda carries dedication through `HAS_DEVATA_ASCRIPTION` on 4,160 of its 5,839
   mantras.

   | Veda | Dedicated, either mechanism | Total | Unmodelled |
   |---|---|---|---|
   | RV | 10,552 (`HAS_DEVATA`) | 10,552 | 0 |
   | SV | 0 | 1,844 | 1,844 |
   | YV | 0 | 1,975 | 1,975 |
   | AV | 4,160 (`HAS_DEVATA_ASCRIPTION`) | 5,839 | 1,679 |

   True unmodelled dedication population: **5,498**, not 9,658. Any query on this
   dimension must read both predicates.

2. `HAS_SEMANTIC_ASSERTION` is Rigveda-only and covers 2,542 of 10,552 RV mantras
   (24.1%), so it is partial even there.

3. `MENTIONS_LEMMA` is Rigveda-only, and carries no run provenance at all -- neither the
   6,560 Rigvedic positives nor the zeros elsewhere can be explained from the graph.

4. Chandas is absent for SV and YV entirely; AV has 4,082 of 5,839.

5. **CORRECTED.** Samaveda has zero translations, zero audio, zero Rishi, zero Devata and
   zero Chandas. But it is not bare, as this baseline first implied: it also carries 1,035
   mantras with `MENTIONS_DEVATA` and 1,677 with a parallel or reuse relation -- 90.9%,
   the *highest* parallel coverage of the four recensions. The Samaveda's gap is in its
   attribution, translation and audio layers specifically, not across the board.

None of these five is a scope decision on record. Each is unfinished work.

## The finding that constrains the whole campaign

Section 32 of the campaign brief requires that optional dimensions reach 100% *assessed*,
even where no positive result is expected. The graph cannot currently report that number.

Run provenance (`run_id`, `pipeline_version`, `method`) is written only onto the artifact
a run produced -- the edge, or the `SemanticAssertion` or `Formula` node. It is never
written onto the `:Mantra` that was examined. A `:Mantra` carries 15 properties and none
records an enrichment run, there is no assessed-set node, and the 1,072 `DerivedMetric`
nodes hold aggregate distributions rather than examined populations.

So for almost every dimension, "no edge" is indistinguishable between *assessed and
found nothing* and *never assessed*. Recoverable state, per dimension:

| Dimension | What can be recovered |
|---|---|
| Audio | Fully resolved -- the catalogue is an enumerated file, not an edge |
| Entity mentions, `MENTIONS_DEVATA`, formula | Which *Vedas* a run touched; not which mantras |
| Parallels | One run, subjects in RV/SV/AV; whether YV was assessed and rejected is not recorded |
| Semantic assertion | Two runs, both RV |
| Chandas, Rishi, Devata | Positives describe how they were derived, not who was examined |
| Lemma | Nothing. No run_id, no pipeline_version, no method |

This cannot be reconstructed from the current graph. It has to be written down at
assessment time, which makes an assessed-set artifact a Wave 1 prerequisite rather than a
reporting detail -- otherwise the campaign cannot honestly close section 32.


## Environment at baseline

| Service | Port | State |
|---|---|---|
| Frontend (Next dev) | 3000 | fresh |
| API (uvicorn) | 127.0.0.1:8000 | fresh, `/ready` true |
| Neo4j (Docker `vedagraph-neo4j`) | 7474 / 7687 | restarted, healthy, census re-verified |

A stale frontend was found serving port 3100 from an earlier session and was stopped;
the canonical port is 3000.
