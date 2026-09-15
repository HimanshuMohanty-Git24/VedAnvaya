# Deity communities and network analytics — derived co-occurrence, not theology

**Agent 15, Wave 2** · branch `phase-data-completeness-v2` · baseline commit `04b94035`
**Adversarial preflight: complete — §10. One headline claim withdrawn; the refusal stands.**
**Validator PASS on 17 checks at 100% coverage, including the domain's own subject at 157/157.**
**Staging artifact**: `data/staging/communities/` — validator **PASS**, every check at 100% coverage with `--graph`
**Graph**: read-only throughout. Re-counted after the run at 108,779 nodes / 265,295 relationships, **unchanged**.

---

## 0. The verdict first

**A deity community partition now exists where none did. It must not be published as a
product surface, and the reason is not the seed.**

The reference partition is *perfectly* seed-stable: 200 seeds, 200 identical partitions,
mean pairwise adjusted Rand index **1.0000**, every one of 123 deities in its consensus
community on every single run. If seed stability were the test, this would pass outright.

It fails a harder test. Every other discretionary choice in the specification moves the
answer, and the one that matters most moves it completely:

| What is varied | ARI against the reference | So |
|---|--:|---|
| the random seed (200 of them) | **1.0000** | irrelevant |
| which of 42 ABSTRACT labels count as deities | 0.958 – 0.971 | nearly irrelevant |
| Louvain instead of Leiden | 1.000 on the consensus | irrelevant to the answer; not to the method — see §4 |
| the edge weighting (raw / Jaccard / cosine) | **0.584 – 0.879** | material |
| resolution γ outside 0.8–1.5 | down to **0.278** | material |
| co-**dedication** instead of co-**mention** | **0.013** | total |

An ARI of 0.013 is chance. Asking "which deities belong together" of the dedication layer
and of the mention layer gives two unrelated answers over the 35 deities both layers reach,
and there is nothing in the data that says which question the user meant.

And half the communities are not groups of deities at all. **Six of the twelve have every
internal edge from a single hymn** — they are that hymn's list of dedicatees. **Five of the
twelve are whole connected components**, which any method at any resolution with any seed
returns for free. Seven communities are structure actually detected inside the main
component, and one of those seven is a liturgical running order.

Two further limits, both found by the adversarial preflight in §10 and neither in the
artifact before it:

- **The projection is structurally blind to the deity identity the graph itself declares.**
  10 of the 11 `EPITHET_VARIANT_OF` pairs share no hymn at all, so a deity and its own
  declared variant name can only ever be joined by coincidence of neighbourhood — and 4 of
  the 6 testable pairs are split by every method.
- **It is eightfold uneven across maṇḍalas.** 0.207 of maṇḍala 4's hymns carry two or more
  dedicatees against 0.026 of maṇḍala 9's, so the entire Pavamāna Soma collection — 114 of
  the 1,028 dedication-bearing hymns — is very nearly unseen.

**One claim in an earlier draft of this report has been withdrawn.** It read that all six
methods separate Bṛhaspati from Brahmaṇaspati, "two names for the same deity", and called
that the decisive defect. The registry pins the two apart *on purpose*. §10 has the probe
and the correction; the verdict is unchanged without it.

`data/staging/communities/manifest.json` carries the verdict as
`NOT_STABLE_ENOUGH_TO_PUBLISH_AS_A_PRODUCT_SURFACE`, and the artifact is offered as the
measured basis for that judgement rather than as a layer to import.

**Nothing here is an ancient theological category.** Every community record, every one of
the 1,185 rows and every community's `interpretation_warning` says so in those terms. No
community is named, and naming one would convert a co-occurrence count into a claim about
Vedic religion. Every deity row also carries
`not_a_positive_membership_assignment`, in those words: `community_id` is a reproducible
output of the algorithm, seed and projection named beside it, and of nothing else.

---

## 1. Three measurements that changed the brief

The brief specified co-dedication and warned it would be structurally RV+AV only. Measured,
all three parts of that premise need correcting, and the first is fatal to the obvious
approach.

**1. Co-dedication within a mantra does not exist.** Of 10,552 Rigvedic mantras carrying
`HAS_DEVATA`, **10,546 carry exactly one deity and 6 carry two.** A mantra-scope
co-dedication graph has six edges. This is not a sparsity problem to work around; the
Anukramaṇī simply does not dedicate a single verse to two deities.

**2. The Atharvavedic half does not join, so the projection is Rigveda-only.**
`HAS_DEVATA_ASCRIPTION` runs to **324 `:DevataAscription` nodes, and 0 of them is also a
`:Devata`** — that is `GAP-ATTRIBUTION-002`, open and agent 8's. 549 Atharvavedic mantras do
carry two or more ascriptions, so an Atharvavedic partition *is* computable, and it would be
a partition over **ascription descriptors**, not deities: `abdevatyam`, "having the waters
as its deity", is a statement about a verse. Merging the two would assert an identity
between a descriptor and a deity that nothing in the graph supports. The 324 are carried as
**`unresolved` candidates** and enumerated one per line with the reason in
`proofs/av_ascription_unresolved.jsonl`, so the Atharvavedic limit is a counted population
rather than a sentence. The Samaveda and Yajurveda have no dedication predicate at all.

**3. `CO_OCCURS_WITH` is 306, and I can now say exactly what it is.** The committed
scorecard's 0 is wrong and agent 1's 306 is right — 306 edges over 306 unordered pairs and
36 deity endpoints, none reciprocated. Independently recomputed: the layer is the four-Veda
theonym **co-mention** graph over `MENTIONS_DEVATA`, thresholded at **5 shared mantras**, and
all 306 of its `passage_count` values are reproduced exactly from the mention edges.
At support ≥ 1 that graph has 538 pairs; at ≥ 5 it has exactly the 306 in the graph.
`proofs/existing_co_occurs_with_reproduction.json`. It is a pairwise statistic, not a
partition, and it is mention, not dedication.

---

## 2. The eligible population, and the ABSTRACT call made explicitly

### Agent 8's exclusions, verified rather than redone

29 of the 214 `:Devata` nodes are not deities — 22 curated `HUMAN` and 7 `PATRON_PRAISE` —
and they carry **171 dedications** between them (85 + 86). Agent 8's figure reproduced to the
unit. Taken from each node's own curated `structure`, never from a name heuristic.

This is not a hypothetical contamination. `GAP-COMMUNITIES-001`'s own registry entry records
that this question *was already graded MISLEADING once*, when a deity-pair co-occurrence
table was substituted for a community answer and "that table's top-ranked members turned out
to be human patrons carried in the deity registry". The failure mode is live in the
projection I built: `dānastuti`, "praise of a patron's gift", has 50 dedications across 15
hymns and would have carried edges to **9** partners. **44 of the 57 excluded nodes would
have carried edges**, and each rejected row records which partners went with it.

Worth recording the converse: the existing 306-edge `CO_OCCURS_WITH` layer is *clean* of
patrons — its 36 endpoints are 50 INDIVIDUAL, 10 GROUP, 8 PAIR, 4 ABSTRACT and no HUMAN or
PATRON_PRAISE — because the theonym mention layer only reaches 42 real deities. The historical
defect does not reproduce there. It reproduces in a co-dedication table, which is what this
agent built.

**Yajurvedic ritual implements were not excluded**, per agent 8's constraint from
Kātyāyana's own opening sūtra admitting implements as *pratimābhūta*. Eight are retained and
named in `proofs/population_cleaning.json` — `barhiḥ`, `yūpaḥ`, `grāvāṇaḥ`, `ulūkhalam`,
`ulūkhalamusale`, `devīrdvāraḥ`, `havirdhāne śakaṭe`, `vanaspatiḥ` — and they are not noise
in the result. Six of the eight are placed: `barhiḥ`, `devīrdvāraḥ` and `vanaspatiḥ` are
core members of the āprī community, and `grāvāṇaḥ`, `ulūkhalam` and `ulūkhalamusale` sit in
the Indra community. `yūpaḥ` and `havirdhāne śakaṭe` are unplaceable, each being dedicated
only ever alone.

### The ABSTRACT decision: ruled per label, *and* run all three ways

Agent 8 flagged 42 `ABSTRACT`/`UNSPECIFIED` labels and deliberately left the call open. I
made it, per label, with a reason on each, in
`data/staging/communities/abstract_label_rulings.json` — and then ran the partition three
ways anyway, because a judgement that drives a published partition should be shown not to be
load-bearing before it is trusted.

**The rule applied** is not invented here. It is the line `DEVATA_TAXONOMY_V1` already drew
in its own sections 7 and 8: *does the label name an addressee with a domain, or does it name
the hymn's subject or its intended effect?* That file reserved `SPEECH` for deities whose
domain is speech and withheld it from bare ritual utterances, and refused the charm-purpose
labels `HEALER` because "the slot names the intended act, not an agent with a domain". Using
the same line keeps one rule rather than two.

| ruling | count | examples |
|---|--:|---|
| **DEITY** | 9 | Śraddhā (vocative throughout RV 10.151), Manyu (`manyo`, RV 10.83–84), Nirṛti, Mṛtyu (`paraṃ mṛtyo anu parehi`), Dakṣiṇā, Ka, Asunīti (`asunīte`), Pathyā Svasti, *śunaḥ* the dog |
| **UNDECIDED — kept** | 5 | Ātmā (30 dedications, the largest footprint of the 42), Annam, Brahma, Rāti, Śacī |
| **NOT_DEITY — excluded** | 28 | the charm-purpose group (`yakṣmanāśanaḥ`, `sapatnaghnarūpo arthaḥ`, …), the occasion labels (`sūryāvivāhaḥ`, `pitṛmedhaḥ`), the ritual utterances (`svāhākṛtayaḥ`, `hotrāśiṣaḥ`), and `liṅgoktāḥ` |

**Five labels are ruled UNDECIDED and are kept in the population.** An undecided label
removed is a decision made by default.

Three of the rulings are worth stating in prose because they are findings, not judgements:

- **`VG:DEVATA:LINGOKTAH`, "the deities indicated by the wording", is not an abstraction —
  it is the Anukramaṇī's own deferral marker materialised as a deity node.** *Liṅgokta*
  means "stated by the characteristic mark in the mantra"; agent 8 counted 102 of these
  deferrals in Kātyāyana's Yajurvedic sūtra and correctly treated them as unresolved. Here
  the same marker is a node with 3 dedications across 2 hymns. A community containing "the
  deities indicated by the wording" is a community containing a null value. **This is a
  modelling defect for the lead, not a curation call.**
- **`VG:DEVATA:BHAVAVRTTAM` and `VG:DEVATA:BHAVAVRTTHAM` are the same label spelled two
  ways**, carrying 15 and 7 dedications. A duplicate-entity defect, independent of my
  ruling on either.
- **`VG:DEVATA:SVAHAKRTAYAH`, the svāhā calls, is the costliest exclusion in the file** — 9
  dedications across 9 hymns, sitting inside the āprī sequence, removing 10 partner edges.
  Recorded as such rather than buried, because it is the one exclusion that visibly changes
  the graph's densest region.

**And the decision turns out not to matter much.** The three variants agree at ARI
**0.958–0.971**:

| variant | eligible | placed | unplaceable | communities |
|---|--:|--:|--:|--:|
| V-ALL — all 42 kept | 185 | 141 | 44 | 15 |
| **V-RULED — 28 removed, 5 UNDECIDED kept** (reference) | **157** | **123** | **34** | **12** |
| V-NONE — all 42 removed | 143 | 115 | 28 | 12 |

A reader who disagrees with every one of my 28 rulings gets substantially the same partition.
That is the honest thing to know about a curation judgement, and it is the reason for running
all three rather than defending one.

One mechanical guard is worth naming. The build raises if a ruling key does not resolve to a
`:Devata` node, or if the ruling file does not cover the ABSTRACT population exactly. That
guard earned itself immediately: the first run silently applied only 27 of 28 rulings and
reported 158 eligible instead of 157, because one ruling was keyed `VG:DEVATA:SAMJNANAM`
against the graph's `VG:DEVATA:SANJNANAM`. Nothing said so. A ruling that matches nothing is
not applied and not reported.

### `occurrence_count` was not used

Null on all 214 `:Devata` nodes, re-measured (`GAP-QUALITY-006`). Every weight in this
artifact is derived from edges.

### The registry's own denominator needs correcting

`/api/v1/insights/capabilities` reports `eligible_deities: 192`, which is 214 minus the 22
HUMAN. The registry entry itself already anticipates the problem — "it still carries 7
dānastuti labels and one non-divine subject" — and this run confirms and extends it: **192 →
185** after the 7 `PATRON_PRAISE`, **→ 157** after the abstract ruling, and **only 123 of
those are placeable at all**. The denominator a coverage figure would be computed against is
wrong by up to 69.

---

## 3. The projection, stated so it can be re-derived

Without this block the partition is unreproducible and therefore worthless. It travels in
full inside every row's `payload.partition.projection`, inside every community record, and in
`proofs/projection_definition.json`.

```
projection_id       RV_CODEDICATION_HYMN_V1
unit of co-occurrence   the RV sūkta (entity_type=HYMN), reached as the mantra's parent_key
nodes               (:Devata), cleaned -- see population_filter
edge rule           undirected {a,b} where some RV sūkta has a mantra dedicated to a
                    and a mantra dedicated to b
cypher              MATCH (m:Mantra {veda:'RV'})-[:HAS_DEVATA]->(d:Devata)
                    RETURN m.canonical_key, m.parent_key, d.entity_key
population_filter   exclude curated structure in ('HUMAN','PATRON_PRAISE')  [29, agent 8]
                    exclude the 28 ABSTRACT/UNSPECIFIED ruled NOT_DEITY
                    keep the 5 ruled UNDECIDED; keep every ritual implement
variant             V-RULED
weighting           COSINE  =  |hymns(a) ∩ hymns(b)| / sqrt(|hymns(a)| · |hymns(b)|)
min_pair_weight     1
vedas reached       RV only
algorithm           leiden, vg-deity-communities-v1, γ = 1.0
seed                consensus over seeds 0-199 at co-assignment threshold 0.5
```

**Why hymn scope is not a fallback.** 79% of Rigvedic verse-level dedication is a sūkta-wide
value read down onto its verses (agent 8's matrix: 8,329 DERIVED against 2,223
SOURCE_EXPLICIT of 10,552). Grouping back to the sūkta recovers the granularity the index
actually states. The 153 sūktas with two or more dedicatees are the hymns where the
Anukramaṇī genuinely assigns different verses to different deities.

**The graph.** 1,028 sūktas carry dedication; **875 are dedicated to a single deity**. After
cleaning: 157 eligible deities, **123 placed**, 475 edges, density 0.063, **6 connected
components** of sizes 109 / 4 / 4 / 2 / 2 / 2. **34 eligible deities are unplaceable**,
typed `NO_EDGE_IN_PROJECTION_DEGREE_ZERO` and enumerated in
`proofs/unplaceable_deities.json`. They are **not** given singleton communities, because a
singleton would let a reader count them as communities and would put Indra and a one-verse
charm label on the same footing.

**They are two kinds, and the preflight in §10 is what separated them.** **31 are isolated
in the source** — every hymn dedicated to them is dedicated to them alone. **3 are
collateral of our own filters**: Urvaśī's only co-dedicatee in the entire Rigveda is
Purūravas, a HUMAN exclusion; Agni-Sūrya's only partner was the dānastuti label; and
*akṣāḥ*, the dice, lost both of its partners to this agent's own abstract rulings. For those
three, "unplaceable" is a consequence of our cleaning and not a silence in the Anukramaṇī,
and they now carry `isolation_class: COLLATERAL_OF_OUR_OWN_EXCLUSIONS`.

### Weighting: three computed, one designated, the cost of each stated

The brief's warning is right — raw counts let Indra (2,869 dedications across 273 hymns) and
Agni (1,988 / 223) dominate. Modularity's null model is already degree-corrected, so raw is
not as bad as it sounds, but it is still the weighting under which the partition partly
describes which deities are frequent.

| weighting | formula | what it costs |
|---|---|---|
| RAW | shared hymns | frequency leaks into the structure |
| JACCARD | ∩ / ∪ | *suppresses* a genuine hub-to-hub link: Agni and Indra can share 40 hymns and still score near zero because each appears in hundreds. Pushes the hubs to their own communities' edges |
| **COSINE** (Ochiai) | ∩ / √(\|a\|·\|b\|) | degree-corrected, less punitive to the hubs; the conventional co-occurrence association measure |

**COSINE is the reference, and the grounds are reported separately because only one of them
is honest on its own.** *A priori*: Ochiai is the conventional degree-corrected measure and
does not punish hub-to-hub links. *Posterior, and learned only after all three had been
run*: it is measurably the most seed-stable. Choosing a weighting because its partition came
out tidiest is the same defect as choosing a lucky seed, so the order is disclosed and every
node's membership under **all six** algorithm × weighting consensus partitions is written out
in `proofs/membership_under_every_method.json`. Raw shared-hymn counts stay on every edge
record whichever weighting drives the algorithm.

---

## 4. Louvain against Leiden, over 200 seeds each

Pure-Python, stdlib-only, deterministic under a fixed seed.
`data/staging/communities/community_algorithms.py`. 200 seeds × 2 algorithms × 3 weightings.

| method | k (consensus) | Q mean | Q max | ARI mean | ARI min | identical runs | nodes < 0.9 stable | nodes < 0.5 | disconnected runs |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **leiden \| COSINE** | **12** | **0.6251** | 0.6251 | **1.0000** | **1.0000** | **100%** | **0** | 0 | 0 |
| louvain \| COSINE | 12 | 0.6235 | 0.6251 | 0.9079 | 0.4847 | 40% | 29 | 0 | 0 |
| leiden \| JACCARD | 13 | 0.5613 | 0.5614 | 0.9264 | 0.6532 | 69% | 15 | 0 | 0 |
| louvain \| JACCARD | 12 | 0.5612 | 0.5614 | 0.8587 | 0.6532 | 25% | 25 | **16** | 0 |
| leiden \| RAW | 10 | 0.5515 | 0.5526 | 0.9450 | 0.6146 | 86% | 1 | 0 | 0 |
| louvain \| RAW | 10 | 0.5434 | 0.5526 | 0.7783 | 0.4548 | 18% | 51 | 0 | 0 |

"nodes < 0.9 stable" is the literal answer to *how often do nodes change community*: for each
node, the fraction of the 200 runs in which it sits in its consensus community, after each
run's arbitrary community ids are matched to the consensus by maximum overlap.

Three things this table says:

- **Leiden beats Louvain on every weighting, on both mean modularity and every stability
  measure.** Not asserted from the literature — measured here and separately verified on the
  karate club.
- **Louvain + Jaccard is the cautionary case.** Its community count looks stable (13 on 195
  of 200 runs) and its mean ARI of 0.859 looks healthy, while **16 nodes are in their
  consensus community less than half the time and one is there on 4.5% of runs.** A single
  stability number would have hidden that, which is why the count distribution, the ARI
  distribution and the per-node figure are all reported.
- **Louvain never produced an internally disconnected community on this graph.** Measured
  over all 600 Louvain runs, not assumed from its reputation. Its known defect is real; it
  simply does not bite on a graph this sparse.

### Resolution sensitivity

γ swept over 14 points from 0.25 to 8.0 (`proofs/resolution_sensitivity.json`), Leiden |
COSINE:

| γ | 0.25 | 0.4 | 0.5 | 0.65 | 0.8 | **1.0** | 1.25 | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 | 6.0 | 8.0 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| communities | 9 | 9 | 10 | 11 | 11 | **12** | 12 | 12 | 28 | 29 | 30 | 31 | 34 | 38 |
| largest | 75 | 75 | 59 | 57 | 33 | **31** | 31 | 31 | 31 | 22 | 17 | 17 | 12 | 8 |
| singletons | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 14 | 14 | 14 | 14 | 14 | 15 |
| ARI vs γ=1 | 0.408 | 0.408 | 0.598 | 0.631 | 0.969 | **1.000** | 1.000 | 1.000 | 0.858 | 0.646 | 0.550 | 0.553 | 0.406 | 0.278 |

There is a real **plateau at γ ∈ [0.8, 1.5]**: 11–12 communities, ARI ≥ 0.969, identical at
1.0, 1.25 and 1.5. Outside it the partition moves substantially, and past γ = 2 it starts
shedding 14 deities into singletons. A plateau is a genuine result — it means γ = 1 was not a
lucky pick within its band — but it is a narrow band, and a reader who prefers γ = 0.5 gets
a partition sharing ARI 0.598 with this one.

### GDS as a cross-check, and why nothing depends on it

GDS 2.13.12 is installed. It was run over a Cypher projection of the same co-dedication
pattern (123 nodes, 950 directed relationships = 475 undirected edges, weighted by raw shared
hymns) and compared against the RAW-weighted partitions, not the cosine reference — comparing
against COSINE would price a weighting difference as an implementation disagreement.

| | GDS k | mine k | ARI vs mine, over three runs | 5 identical repeat calls returned k = |
|---|--:|--:|---|---|
| Louvain | 10 | 10 | **0.978** on every run | 10, 10, 10, 10, 10 — every run |
| Leiden | 9 or 10 | 10 | **0.762 / 0.879 / 1.000** | 9,9,9,10,9 · 9,10,10,10,9 · 9,10,10,10,10 |

Independent corroboration of the implementation — and the Leiden row is the *only* figure in
this report that does not reproduce, which is exactly why the rule exists. Across three runs
of the identical script against an unchanged partition of mine, `gds.leiden.stream` with
`randomSeed: 42` returned 9 or 10 communities and an ARI of 0.762, 0.879 and 1.000.
`gds.louvain.stream` returned 10 on all five repeats in all three runs and ARI 0.978 every
time. A server-side algorithm's determinism is not part of this artifact and cannot be
asserted from outside it, so it was measured rather than assumed. Quote GDS figures from
`proofs/gds_cross_check.json` as of the run that produced them, never from this table.

**Read-only accounting.** `gds.graph.project` writes to the in-memory catalog only; the entry
is dropped in the same function; node and relationship totals were re-counted after the run
and are unchanged at 108,779 / 265,295. No `CREATE`, `MERGE`, `SET` or `DELETE` was issued
against the store at any point. If that reading of "read-only" is not accepted, deleting the
GDS function changes no published number.

### The machinery was validated against a published answer, and it was wrong twice

Two of the three recorded defects are here; the third is an interpretive one in this
report's own headline, found by the adversarial preflight and written up in §10.

`data/staging/communities/self_test.py`, result in `proofs/self_test.json`. This is the QA for
this domain, and it is the right QA: every accepted row is a deterministic restatement of
`HAS_DEVATA` edges that already exist, so sampling rows would only re-measure the graph.
Where a defect can hide is the machinery — and a defect in the machinery produces numbers
that look entirely reasonable. Modularity 0.37 over a Vedic graph is as plausible as 0.62;
nothing about the Rigveda tells you which is right.

So the implementation is run against Zachary's karate club, whose modularity optimum is a
published number, and against published betweenness values. It found two real defects.

1. **The graph aggregation double-counted between-community edge weight.** Each edge is
   walked from both endpoints and only the internal half was being halved, so the level-2
   aggregate graph reported total weight **111.0 against the graph's true 78.0** and every
   modularity above the first level was wrong. Before the fix the best partition found on
   karate was **Q = 0.3718 at k = 2**; after it, **Q = 0.4198 at k = 4**, which is the
   published optimum. Had this shipped, the Vedic figures would have looked completely
   plausible and been wrong.
2. **Local moving never offered a node an empty community.** Candidates were drawn only from
   the communities a node's neighbours were already in, so a node could never leave a
   community *by itself* — and a community that has become internally disconnected can only
   split if one node goes solo first. This was caught by the module's own assertion that
   Leiden must never return an internally disconnected community: it fired on the Vedic
   projection. Fixing it also revealed that the connectivity guarantee is a property of the
   **converged** partition, not of one pass, so Leiden now iterates from its own output until
   the partition stops changing. After both fixes Leiden reaches Q = 0.4198 on every one of
   50 karate seeds, mean = max, pairwise ARI 1.000.

The self-test also asserts what the report leans on: determinism under a fixed seed, total
weight preserved at every aggregation level, Leiden never disconnected, Leiden's mean
modularity and seed stability at least Louvain's, community count monotone in resolution, and
betweenness matching the published karate values (node 1: computed 0.43764 against 0.43763).

---

## 5. What the communities actually are — and this is the section that decides the verdict

`proofs/communities_that_are_one_hymn.json` measures, per community, how many **distinct**
sūktas supply its internal edges. The result deflates the headline twice over.

| community | size | hymns behind it | one hymn? | whole component? | largest members |
|--:|--:|--:|:--|:--|---|
| 0 | 31 | 38 | no | no | the All-Gods, the Aśvins, Mitra-and-Varuṇa, Uṣas, the Ādityas, the Ṛbhus |
| 3 | 25 | 29 | no | no | Indra, the Maruts, Indra-and-Agni, Soma, Bṛhaspati, Rudra |
| 2 | 18 | 12 | no | no | Varuṇa, Savitṛ, Indra-and-Varuṇa, Heaven-and-Earth, Viṣṇu |
| **5** | **16** | **1** | **yes** | no | Brahmaṇaspati, the arrows, the chariot, the bow-tips, the quiver |
| 1 | 14 | 15 | no | no | Agni, Tvaṣṭṛ, the divine doors, Dawn-and-Night, Vanaspati, barhis |
| 11 | 4 | 2 | no | **yes** | Yama, the Fathers, Yamī, Saramā's two dogs |
| **8** | **4** | **1** | **yes** | **yes** | Kṣetrapati, Sītā the Furrow, Śunā-and-Sīra, the dog |
| **7** | **3** | **1** | **yes** | no | the parts of the chariot, Sasarparī the Voice, Indra-and-Parvata |
| 10 | 2 | 2 | no | **yes** | Soma Pavamāna, Agni Pavamāna |
| **4** | **2** | **1** | **yes** | no | the serpent, Ahi Budhnya |
| **6** | **2** | **1** | **yes** | **yes** | the married pair, the sacrifice and the sacrificer |
| **9** | **2** | **1** | **yes** | **yes** | the Paṇis, Saramā |

**Six of twelve are a single hymn's cast list, covering 29 of the 123 placed deities. Five
of twelve are whole connected components.** Seven communities are structure detected inside
the main 109-node component.

The three that a reader would find most striking are the three that most need the caveat:

- **Community 5 is RV 6.75, the weapons hymn.** Brahmaṇaspati with the bow, the bowstring,
  the arrows, the quiver, the hand-guard, the bow-tips, the chariot, the goad, the charioteer
  and the reins and the war drum. Internal support 120 against 7 external — **the most
  modular community in the graph and the least meaningful as a grouping of deities.** It is
  one hymn's inventory of deified war gear.
- **Community 1 is the āprī sequence of the animal offering.** Agni, Tvaṣṭṛ, the divine
  doors, Dawn-and-Night, Vanaspati, the sacred grass, the two divine Hotṛs and the goddess
  triad — the same nine entities `DEVATA_TAXONOMY_V1` minted `VG:DEITYGROUP:APRIDEVATAH` for
  and then recorded as a dangling key with no registry entity. The algorithm recovers it
  because the ten āprī hymns recite it in order. **That is a real, checkable result, and it
  is a liturgical running order, not a pantheon.** It is also the best evidence in this
  artifact that the projection is measuring something rather than nothing.
- **Community 8 is RV 4.57**, the field hymn: Kṣetrapati, Sītā the Furrow, plough-and-
  ploughshare, and the dog. Community 11 is the funeral hymns RV 10.10 and 10.14 — Yama, the
  Fathers, Yamī and Saramā's two dogs — and is the one small community that is arguably
  thematic as well as liturgical.

The structural cause is measurable and it is not going away: 875 of 1,028 dedication-bearing
sūktas have a single dedicatee, so the entire co-dedication signal lives in 153 hymns, and a
good number of those are one-off liturgical inventories rather than recurring associations.

### The co-mention comparison, and why its small community count means nothing

Computed but never merged. `MENTIONS_DEVATA` over all four Vedas: 17,165 edges, 11,917
mantras, 3,620 of them mentioning two or more deities — and it reaches **42 of 214**
`:Devata` nodes. Among those 42 the graph has **density 0.690**: most of them co-occur with
most of the others. A near-complete graph has almost no modular structure to find, so its 4
communities are a property of the layer's reach, not a statement that the Vedic gods fall
into four groups. `proofs/projection_density.json` records this explicitly so the figure
cannot be quoted on its own.

That is also the honest reading of the ARI 0.013 between the two projections. It is not that
one is right; it is that a 6%-dense dedication graph over 123 deities and a 69%-dense
mention graph over 40 are different objects, and "deity community" does not pick out one of
them.

---

## 6. Network analytics over the same declared projection

`proofs/network_analytics.json`. Deterministic, pure Python, computed over **the same**
projection as the partition, so no figure belongs to a graph the partition does not also
describe.

| deity | betweenness | participation | within-module z | partners | dedications | community |
|---|--:|--:|--:|--:|--:|--:|
| Indra | 0.2733 | 0.661 | 0.09 | 47 | 2,869 | 3 |
| Agni | 0.1424 | 0.609 | −0.76 | 41 | 1,988 | 1 |
| the All-Gods | 0.1267 | 0.471 | 0.15 | 29 | 805 | 0 |
| **the chariot** | **0.1115** | 0.157 | −1.36 | 18 | **4** | 5 |
| Soma | 0.0931 | 0.526 | 1.90 | 27 | 80 | 3 |
| **Brahmaṇaspati** | 0.0667 | 0.157 | **−3.53** | 18 | 48 | 5 |
| the Aśvins | 0.0632 | 0.553 | −0.10 | 26 | 631 | 0 |

Two reasons this is reported with the caveat attached rather than as a ranking:

**The chariot is fourth by betweenness on four dedications.** *Ratha* sits between the
weapons hymn's cluster and the rest of the graph, so shortest chains of co-dedication run
through it. That is a structural accident of one hymn's membership, not a statement about the
chariot's importance in Vedic religion, and a "most central deities" surface built on this
column would publish it as though it were.

**Betweenness is computed unweighted, deliberately.** On a co-occurrence graph a weighted
shortest path is the path of *least* association, which is the opposite of what a reader
assumes a strong edge does.

`participation_coefficient` and `within_module_degree_z` (Guimerà–Amaral) are the more honest
bridging measures once a partition exists, because they are defined *relative to that
partition* and therefore carry its caveats instead of looking like properties of the deity.
Brahmaṇaspati's z of **−3.53** is the most extreme value in the graph: it says he is the
worst-connected member of his own community, which is what you would expect of the one member
with 48 dedications in a community where twelve of the sixteen have exactly one. The next
subsection takes that apart.

### Deity identity: what this projection can and cannot see

An earlier draft of this report put a claim here that has since been withdrawn — that
separating Bṛhaspati from Brahmaṇaspati was the decisive defect. It was an imported
scholarly prior, not a measurement, and §10 sets out the probe that removed it. What
replaces it is stronger, because it is drawn entirely from the graph's own identity model.

The graph declares deity identity with `EPITHET_VARIANT_OF`, 11 edges. Swept against all
six method consensuses (`proofs/adversarial_preflight.json`, TEST A2):

| declared variant → canonical | shared hymns | outcome |
|---|--:|---|
| Soma Pavamāna → Soma | 0 | **split by every method** |
| Agni Pavamāna → Agni | 0 | **split by every method** |
| Dadhikrāḥ → Dadhikrā | 0 | **split by every method** |
| Sasarparī-Vāk → Vāc | 0 | **split by every method** |
| Marutvān-Indra → Indra | 0 | kept together by every method |
| the two divine Hotṛs → the two divine Hotṛs | 0 | kept together by every method |
| 5 more (Agni's variants, *bhavavṛttam*, Viśve-devāḥ) | 0–1 | not testable — one endpoint outside the partition |

**10 of the 11 pairs share no hymn.** That is not sparsity, it is what the dedication layer
*is*: a name and its variant are alternative labels for the same slot, so the Anukramaṇī
never dedicates a hymn to both. **The co-dedication projection is therefore blind to deity
identity by construction** — a variant can only be joined to its canonical form by
coincidence of neighbourhood, and 4 of the 6 testable pairs are not. A deity-community
surface would scatter a deity's own declared variant names across communities, structurally
rather than occasionally.

And the sweep found a registry contradiction the hand-picked test missed. `EPITHET_VARIANT_OF`
asserts that Soma Pavamāna *is* Soma, while `DEVATA_TAXONOMY_V1` states that the two "differ
substantively, not just by key", gives them different axes, and partitions their aliases
"deliberately so the two do not silently collect each other's mantras". Both cannot be
followed, and which is right decides whether that split is a defect or correct behaviour.
It is the same shape of defect the taxonomy already flagged for Mitrāvaruṇau, and it is
handed to the lead rather than resolved here.

### Why Brahmaṇaspati is with the quiver — the part that is measured

`within_module_degree_z` of **−3.53**, the most extreme value in the graph, says he is the
worst-connected member of his own community. The cause needs no identity claim: **15 of his
18 co-dedication partners come from the single hymn RV 6.75.** A deity with 48 dedications
across 8 hymns has his community decided by one of them. That is the single-hymn finding
demonstrated on a well-attested individual deity rather than on a two-member community, and
it is a better plank than the one it replaced.

`proofs/diagnostic_pairs.json` now computes its verdict column from `EPITHET_VARIANT_OF`
rather than from a prior, and records the change and why.

---

## 7. The artifact

```
data/staging/communities/
  manifest.json                    candidates 1,566 = 1,185 + 57 + 324
  rows.jsonl                       1,185 rows in TWO declared grains:
                                     1,028 PASSAGE -- one per RV dedication-bearing sūkta
                                       157 ENTITY  -- one per eligible :Devata, the subject
  rejected.jsonl                   57, every one with a reason and its removed partners
  sources.jsonl                    3
  communities.jsonl                12 -- THE DEITY-GRAINED DELIVERABLE
  abstract_label_rulings.json      42 rulings, one reason each
  community_algorithms.py          Louvain, Leiden, modularity, ARI, NMI, consensus,
                                   betweenness, participation, z-score -- stdlib only
  self_test.py                     karate-club validation; run this first
  build_communities_staging.py     regenerates everything
  proofs/
    self_test.json                     the known-answer validation, PASS
    projection_definition.json         the primary and the comparison, and why mantra
                                       scope was rejected (6 edges)
    population_cleaning.json           214 -> 185 -> 157 -> 123, and the 8 implements kept
    method_comparison.json             6 methods x 200 seeds, full stability block
    resolution_sensitivity.json        14 gammas, both algorithms
    partition_sensitivity.json         weighting, population variant, projection
    node_stability.json                per-deity, 200 seeds
    membership_under_every_method.json every node under all six consensuses
    communities_that_are_one_hymn.json the six, and the five whole components
    adversarial_preflight.json         the four preflight probes and what they returned
    diagnostic_pairs.json              pairs a reader can judge; verdict computed from
                                       EPITHET_VARIANT_OF, not from a scholarly prior
    network_analytics.json             betweenness, participation, z, components
    projection_density.json            why co-mention's small k means nothing
    unplaceable_deities.json           the 34, split 31 source-isolated / 3 collateral
    edge_list.json                     all 475 edges with raw, Jaccard and cosine
    existing_co_occurs_with_reproduction.json   306 confirmed and reproduced
    av_ascription_unresolved.jsonl      all 324, one per line, with the reason
    av_partition_would_be_a_different_object.json
    gds_cross_check.json               ARI/NMI, the repeat-call non-determinism, read-only
                                       accounting
```

### Section 32 / Section I

`candidates_considered 1,566 = accepted 1,185 + rejected 57 + unresolved 324`, with
`verified_zero 880` and `not_applicable 21` over the passage rows, and
`entity_rows_with_a_community 123` / `entity_rows_typed_absent 34` over the entity rows.
The two grains are never pooled into one coverage figure. The 214 `:Devata` nodes split
cleanly: **157 accepted as entity rows + 57 rejected**.

**The ledger is mixed-grain and the manifest says so** rather than letting the arithmetic
compare unlike things. `accepted` counts RV sūkta assessments; `rejected` counts `:Devata`
nodes removed from the eligible population; `unresolved` counts the 324
`:DevataAscription` descriptors that cannot enter a `:Devata` partition at all. Every
rejected and unresolved row carries a `candidate_unit` field naming its grain.

Every row carries `source_snapshot`, `algorithm_version`, `config_hash`, `code_commit`, the
graph snapshot, `population`, `processed_count`, `positive_count`, the evaluation block, and
the full projection definition. Every community record carries `algorithm`, `version`,
`seed`, `resolution`, `weighting` and the projection definition.

### The contract limit this domain ran into — flagged, fixed by the lead, now used

An earlier version of this artifact **could not put its primary object in `rows.jsonl`**.
`graph.canonical_key_resolves` required every `canonical_key` to resolve to a `:Passage`; a
`:Devata` carries `entity_key`, has no `canonical_key` and no `:Passage` label. So the
deity-grained membership went into a sidecar and `rows.jsonl` held 1,028 hymn-grained rows.
That was flagged here as a contract limit rather than worked around silently.

**The lead has since extended the validator**, with `subject_kind: ENTITY` plus
`subject_id_property` and `subject_label` — and its docstring names that exact workaround as
the defect it fixes: two agents *"worked around it by moving their real output into a sidecar
file and filling `rows.jsonl` with passage-grained proxies. The artifacts passed, which is
the problem: the check reported full coverage over rows that were not the domain's subject."*
This agent was one of the two.

**So the artifact now uses it.** `rows.jsonl` carries two declared grains:

| grain | rows | subject | role |
|---|--:|---|---|
| `PASSAGE` | 1,028 | an RV sūkta carrying `HAS_DEVATA` | the projection's **evidence** — which deities the Anukramaṇī places in this hymn, which pairs it contributes, where each landed |
| `ENTITY` | 157 | `:Devata`, resolved by `entity_key`, label asserted | the domain's **subject** — per-deity membership, or a typed absence with its reason |

The validator counts them as separate checks rather than pooling them, so a domain cannot
hide unresolved entities behind a wall of passage proxies. Both resolve at 100%.

Each entity row carries its community, that community's size, whether that community is a
single hymn's cast list or a whole connected component, the deity's stability over 200
seeds, its co-dedication partners, **the partners our own cleaning removed**, its membership
under all six methods, its evidence hymns, and — where it is unplaceable — which of the two
kinds of unplaceable it is and why.

`communities.jsonl` stays, because it is a third object again: the community-grained view,
12 records with internal and external support and example hymns.

The hymn rows stay too. They are not proxies; they are the evidence from which every edge in
the projection is re-derivable, and a sūkta that contributes no edge is a measured zero with
a typed role rather than an absent row.

### Validator

```
$ .venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/communities --graph

  communities (agent 15): 1185 row(s), 3 source(s)
  [OK] manifest.counts_balance · manifest.file_checksums · row.required_fields
  [OK] row.evidence_layer_closed · row.quality_class_closed · row.mapping_confidence_closed
  [OK] row.source_id_resolves · row.source_locator_substantive · row.recension_verified_present
  [OK] row.no_zero_for_unknown · row.no_duplicate_key_source · manifest.accepted_matches_rows
  [OK] rejected.has_reason (57/57) · graph.canonical_key_resolves (1028/1028)
  [OK] graph.veda_agrees (1028/1028)
  [OK] graph.entity_subject_resolves (157/157) · graph.entity_label_agrees (157/157)

  PASS. Every check evaluated every eligible row and found no defect.
```

### QA

`qa.human_reviewed` is **0**. Model adjudication by claude-opus-5 acting as Agent 15;
section 26 forbids calling it gold. No accepted row was sampled, and that is deliberate — the
rows are a deterministic restatement of existing edges. What was validated is the machinery
(three defects, below) and the judgements: all 42 ABSTRACT rulings and all 29
exclusions were read one at a time and are written one per line with a reason, so a human can
re-check every one of them in an hour. **The 42 rulings are the part most in need of a
human**, and the variant sensitivity above is the reason a reviewer's disagreement would be
cheap.

---

## 8. Gaps: what moved, what was corrected, what was not worked

**`GAP-COMMUNITIES-001` — advanced, not closed, and deliberately not proposed for import.**
A partition exists where none did. Its closure test is "deity nodes carry a stored community
assignment whose projection is declared, modularity is recorded, and
`/api/v1/insights/capabilities` no longer returns `deity_communities` as NOT_BUILT". The
first two halves are satisfiable from this artifact. **The third should not be done**, for
the reasons in section 0. If the lead wants a surface anyway, the only honest one is a
*methods-and-sensitivity* page: here is a projection, here is what it finds, here is how much
it moves when you change the specification. The existing typed refusal is better than a
partition presented as a fact.
Its stated population of **192 also needs correcting to 157 eligible / 123 placeable.**

**`GAP-COMMUNITIES-003` — disproven, and now explained.** 306 confirmed independently, and
the layer identified as the four-Veda co-mention graph thresholded at 5 shared mantras with
all 306 `passage_count` values reproduced. The scorecard's 0 is wrong; its *verdict* (that a
pairwise layer is not a partition) remains right, which is the combination the census agent
warned was dangerous.

**`GAP-COMMUNITIES-002` — not worked, and its blocking relation needs revising.** The gap
census records `GAP-COMMUNITIES-001` as blocked on it, on the ground that "an undecomposed
dual or group label cannot be placed in a community". **Measured, that blocker is not
binding.** A dual is placed by its own co-dedication footprint without being decomposed:
Mitra-and-Varuṇa (184 dedications, 35 hymns, 26 partners) and Indra-and-Agni sit in
communities on their own edges. **59 of the 71 composite labels are placed** — 31 of 38 PAIR
and 28 of 33 GROUP — and the 12 that are not are unplaceable for the ordinary reason
(dedicated only ever alone), not because they are undecomposed. The blocker matters for
**interpreting** a community — community 0 contains both Mitra-and-Varuṇa and Mitra, so it
double-counts a deity — not for computing one. The dependency should be re-typed from *gates*
to *constrains interpretation*.

**`GAP-ATTRIBUTION-002` — supplied with its measured consequence.** All 324 unresolvable
Atharvavedic ascription descriptors enumerated with reasons, plus the fact that this gap is
what makes a co-dedication partition Rigveda-only rather than RV+AV.

### Canonical writes for the lead — proof supplied, the write is not mine

1. **`VG:DEVATA:LINGOKTAH` should not be a `:Devata` node.** It is the Anukramaṇī's
   *liṅgokta* deferral marker, i.e. a null value, materialised as a deity with 3 dedications
   across 2 hymns. Whatever it should become — a typed absence on those verses, most likely —
   it should not be eligible to join a community.
2. **`VG:DEVATA:BHAVAVRTTAM` and `VG:DEVATA:BHAVAVRTTHAM` are one label spelled twice**,
   15 and 7 dedications. Duplicate entity.
3. **`VG:DEITYGROUP:APRIDEVATAH` has no registry entity**, which `DEVATA_TAXONOMY_V1`
   already reported as a dangling key. This run is the independent evidence that the group is
   real: the āprī sequence is recovered from the co-dedication graph without being told it
   exists.
4. **`eligible_deities: 192` in the capabilities response is wrong** — 185 after the
   `PATRON_PRAISE` labels the registry note already suspected, 157 after the abstract ruling,
   123 placeable.

## 9. What I could not do, and would not

1. **No Atharvavedic partition.** Computable over 324 descriptors, refused because it is not
   the same object. `GAP-ATTRIBUTION-002` first.
2. **No Samavedic or Yajurvedic partition.** No dedication predicate exists for either
   corpus, so this is not a gap in the analysis; it is the absence of the input. A co-mention
   partition *is* computable for all four Vedas and would be a partition of 40 deities over a
   69%-dense graph, which is why it is offered as a comparison and nothing else.
3. **No human validated anything**, least of all the 42 rulings.
4. **No partition was named.** Twelve communities, twelve `community_id`s and no labels. The
   moment "the āprī community" or "the Indra community" appears in a product surface, a
   co-occurrence count has become a theological claim, and the caveat text in every record
   exists to make that harder to do by accident.
5. **The 34 unplaceable deities stay unplaceable.** A deity dedicated only ever alone has no
   co-dedication partner. That is a typed absence over an assessed population, not something
   to fill.

---

## 10. Adversarial preflight — mandatory, before Wave 3

`proofs/adversarial_preflight.json` carries all four probes and their outputs. The campaign
has found five cases where an apparent source absence was our own addressing or modelling
error, and the instruction was to assume a sixth. **There was one, and it was in this
report's own headline.**

This domain's headline is a *refusal*, and a refusal can be wrong in both directions. An
assumption that inflates the case against publishing is as much a defect as one that hides
it — so the assumption tested first is the one that was doing the most work with the least
measurement behind it.

### TEST A — the load-bearing one: an entity-identity assumption

**The assumption.** That Bṛhaspati and Brahmaṇaspati are one deity, so a partition
separating them is defective. It carried the most weight because it was the single check
that moved the verdict from "unstable" to "do not publish", and the only plank of the
refusal that needed no statistics — maximum rhetorical force, minimum measurement behind it.

**The probe.** Read both nodes' curated `structure`, aliases and `curation_note`; look for
any declared relation between them; enumerate every `EPITHET_VARIANT_OF` edge in the graph;
measure their shared hymns and the Jaccard overlap of their co-dedication neighbourhoods.

**The expectation.** If they share no hymn and their neighbourhoods are disjoint, then no
co-dedication method could have joined them, and the diagnostic was measuring the
projection's blindness rather than the method's failure.

**What the test returned.**

| probe | result |
|---|---|
| shared hymns | **2** — RV 2.23 and 2.24, so a direct edge *does* exist |
| neighbourhood Jaccard | **0.0667** — 2 shared partners out of 31 |
| `EPITHET_VARIANT_OF` edge between them | **absent**, while 11 such edges exist elsewhere |
| registry declares them distinct on purpose | **yes** |

And the decisive line is Brahmaṇaspati's own `curation_note`, verbatim from the node:

> "The tradition largely identifies him with Bṛhaspati; **the registry pins them as two
> entities and this overlay keeps them apart rather than asserting the identification.**"

with Bṛhaspati's matching it: *"brahmanaspati is a separate registry entity rather than an
epithet slot."*

**Outcome: the assumption was wrong and the claim is withdrawn.** I imported the standard
scholarly view as if it were the graph's model, then graded the partition defective for
respecting the project's own curation. The graph *has* a declared vocabulary for "same deity
under another name" and these two are deliberately outside it. That is precisely the class
of error this campaign exists to catch — and it was mine, in the sentence I had called
decisive.

**The refusal survives, on better evidence and one fewer claim.** The same probe established
the replacement: **15 of Brahmaṇaspati's 18 co-dedication partners come from the single hymn
RV 6.75.** A deity with 48 dedications across 8 hymns has his community decided by one of
them. No identity claim required.

### TEST A2 — the generalisation that should have been written first

Five hand-picked pairs answer a question about five pairs. So: sweep **every** pair the
graph declares to be one deity — all 11 `EPITHET_VARIANT_OF` edges — against all six method
consensuses. The table is in §6. Two findings the hand-picked test missed:

1. **10 of the 11 pairs share no hymn at all.** The projection is blind to declared deity
   identity *by construction*, and 4 of the 6 testable pairs are split by every method. This
   is the argument the withdrawn claim was reaching for, in a form that rests on the graph's
   own model rather than on a prior — and it is stronger.
2. **There is exactly one genuine split-identity case, and it is not the one I claimed.**
   `EPITHET_VARIANT_OF` asserts Soma Pavamāna is Soma; every method separates them. But
   `DEVATA_TAXONOMY_V1` holds the two apart deliberately. **A registry contradiction**,
   handed to the lead, the same shape as the Mitrāvaruṇau conflict the taxonomy flagged.

### TEST B — are the 34 degree-zero deities collateral of our own exclusions?

**Probe:** rebuild the projection over the uncleaned 214-node population and ask, for each
of the 34, whether it had any partner there. **Result: 3 of 34 are collateral** — Urvaśī
(lost Purūravas, a HUMAN exclusion), Agni-Sūrya (lost the dānastuti label), and *akṣāḥ* the
dice (lost both partners to my own abstract rulings). 31 are isolated in every variant. The
coordinator's hypothesis was right and small; the three are now typed apart. **Confirmed,
and corrected.**

### TEST C — is hymn-scope co-dedication uniform across the Rigveda?

**Probe:** multi-dedicatee hymn share per maṇḍala.

| maṇḍala | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| hymns | 191 | 43 | 62 | 58 | 87 | 75 | 104 | 103 | 114 | 191 |
| with ≥2 dedicatees | 22 | 8 | 6 | 12 | 9 | 4 | 21 | 18 | **3** | 24 |
| share | .115 | .186 | .097 | **.207** | .103 | .053 | .202 | .175 | **.026** | .126 |

**Confirmed as a real limit, an eightfold spread.** Maṇḍala 9 — the entire Pavamāna Soma
collection, 114 hymns — contributes three multi-dedicatee hymns. So the partition is
disproportionately a picture of maṇḍalas 1, 2, 4, 7, 8 and 10 and is very nearly blind to
the Soma corpus. This was not in the artifact before the preflight. **It strengthens the
refusal.**

### TEST D — does the null marker actually join a community?

**Probe:** place `VG:DEVATA:LINGOKTAH` in the V-ALL projection, where it is not excluded.
**Result: degree 5, joins community 5, and its five partners span 3 different communities.**
So the Anukramaṇī's own *liṅgokta* deferral marker is not a stray singleton — it sits in the
projection as an **inter-community bridge**, the position where a spurious node does a
partition the most damage. It is excluded from the reference partition, so no published
figure moves; but retiring the node is now a firmer recommendation than it was.
**Confirmed, and worse than stated.**

### Net effect

One claim withdrawn, three new limits found, and the refusal ends on firmer ground than it
started. `manifest.json.qa.defects_found` moves **1 → 3**: the withdrawn identity claim and
the mis-typed degree-zero population join the aggregation bug already recorded.

**One thing was restaged, deliberately.** While this ran, the lead extended the validator
with `subject_kind: ENTITY` — the fix for the contract limit §7 had flagged — and its
docstring names this artifact's sidecar workaround as the defect it addresses. So the 157
deity-grained membership rows moved into `rows.jsonl` as first-class rows, `accepted` went
1,028 → 1,185, `candidates_considered` 1,409 → 1,566, and the validator now resolves the
domain's actual subject at 157/157 instead of reporting full coverage over hymn proxies.
Leaving that unchanged would have meant leaving a stale limitation asserted in the report
and the domain's subject unvalidated.

**Nothing else already correct was restaged.** `rejected.jsonl` — the one payload file
carrying neither a timestamp nor a commit stamp — is byte-identical to the pre-preflight
build at `3d02030b7adf2c9d`. `rows.jsonl` and `communities.jsonl` re-stamped only because HEAD moved
from `7c9d32e` to `04b9403` under a sibling agent's commit while this ran; two consecutive
rebuilds at the fixed HEAD are byte-identical, so the partition and the population are
unchanged. Validator re-run with `--graph`: **PASS**, 15 checks, 100% coverage.

**The publication verdict is unchanged**, and it now rests on six measurements, not one of
which is a scholarly prior: ARI 0.013 between the dedication and mention projections;
weighting sensitivity 0.584–0.879; 6 of 12 communities being one hymn's cast list and 5 of
12 whole connected components; a well-attested deity's community decided by 1 of his 8
hymns; an eightfold per-maṇḍala imbalance; and structural blindness to the deity identity
the graph itself declares.
