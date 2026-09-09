# VedaGraph Knowledge Model V3 — World-Class Scorecard (baseline pass)

**Rubric author and evaluator:** independent scorecard agent. Did **not** author V2 and did not
modify any code, registry, artifact or graph during this pass.
**Date:** 2026-09-09
**Commit:** `92f2539` · **Branch:** `semantic-pilot-v1`
**Database:** `bolt://localhost:7687` (Neo4j 5.26, container `vedagraph-neo4j`)
**Graph measured:** 100,780 nodes / 242,147 relationships / 42 labels / 49 relationship types
**Runner:** `scratchpad/cy.py` (thin Cypher shell) and four Python probes for
independent verification. Every number below was produced during this pass.

---

## 0. What this document is, and what it is for

This is two things bolted together, and the second matters more than the first.

The first is a score: twenty dimensions, 0–5 each, **53/100** for the graph as it stands today.

The second is **the rubric itself, which is being frozen.** A different evaluator will apply
these same twenty definitions, verbatim, to the finished V3 graph. That evaluator will not
have read the V2 report, will not have this session's context, and must not need it. So each
dimension below defines what 0, 1, 2, 3, 4 and 5 *mean*, in operational terms, with a
measurable threshold wherever a threshold can be stated. Where I could anchor a level to a
count, a ratio or a verification rate, I did. Where I could not, I said which artifact must
exist rather than describing a quality.

Three scoring rules were applied without exception.

1. **Declared-but-empty scores as empty.** A predicate with an endpoint signature, four
   indexes and zero edges is a zero, not a two. The graph declares 35 V2 predicates; 15 are
   empty; only one of those 15 is documented as empty-by-design. That gap is charged, not
   excused.
2. **Unmeasured cannot exceed 1.** Two dimensions — O (semantic precision) and P (semantic
   recall) — have no measurement anywhere in the repository. The gold file exists, is
   schema-valid, and every one of its 120 rows reads `annotator: UNANNOTATED` with zero
   entities and zero relations. An unmeasured dimension scores 1, and §O and §P explain
   exactly why 1 rather than 0 and why not 2.
3. **Do not deflate either.** V2 did some things unusually well and the scorecard says so.
   100% of 242,147 edges carry four independent self-description fields; the interpretive
   layer is structurally airtight; the internal/product boundary is written once and holds;
   and an independent 2,500-row verification of evidence quotes came back at 99.88%. Those
   are fours, and three dimensions score four.

Nothing here is taken from `VEDAGRAPH_KNOWLEDGE_MODEL_V2_FINAL_REPORT.md` on trust. Where I
quote a V2 figure it is because I re-measured it and it held; where re-measurement moved the
number, I report mine.

### Measurement environment, stated so it can be reproduced

| Fact | Value |
| --- | --- |
| Works | 4 (`VG:WORK:RV:SAK`, `AV:SAU`, `SV:KAU`, `YV:VSM`) |
| Passages / Mantras | 22,537 / 20,210 |
| Product nodes (`NOT n:Internal`) | 38,297 |
| Internal nodes | 62,483 |
| Uniqueness constraints | 22 |
| Indexes | 77 RANGE, 2 FULLTEXT, 2 LOOKUP |
| Live invariant tests | 52 passed (`VEDAGRAPH_LIVE_NEO4J=1 pytest tests/domain`), incl. 9 live-Neo4j gates |
| Named query catalogue | 48 queries, 48 executed without error, 48 carry a caveat |
| Catalogue latency | median **5.75 ms**, mean 200.2 ms, p95 78.7 ms, 46/48 < 200 ms, 1 > 1 s |

---

## A. Corpus coverage — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No verse-keyed corpus, or only fragments/pilots. |
| **1** | One Veda's saṃhitā, verse-keyed, with canonical citations. |
| **2** | Two or three Vedas' saṃhitās; **or** four Vedas where any one is below 80% of its own recension's attested verse count; **or** four Vedas with gaps not enumerated. |
| **3** | All four Vedas, one recension each, each ≥95% of that recension's attested verse count, every verse carrying a canonical citation, and **every shortfall enumerated with a stated cause**. No post-saṃhitā layer, no second recension. |
| **4** | Level 3, **plus** at least one second recension **or** one post-saṃhitā layer (Brāhmaṇa / Āraṇyaka / gāna) for at least one Veda, **and** the corpus scope of each Work stated as a machine-readable property on the `Work` node itself. |
| **5** | Level 4, plus ≥2 recensions for ≥2 Vedas **or** the Sāmavedic gāna corpus, **and** a translation for ≥95% of every Veda's verses. |

### Measured evidence

```cypher
MATCH (p:Passage) RETURN p.veda AS veda, count(*) AS passages,
  count(CASE WHEN p:Mantra THEN 1 END) AS mantras ORDER BY veda
```

| Veda | Recension | Passages | Mantras | Attested total | Coverage | Translations |
| --- | --- | --- | --- | --- | --- | --- |
| RV | Śākala | 11,590 | 10,552 | 10,552 | **100.0%** | 10,502 (99.5%) |
| AV | Śaunaka | 6,590 | 5,839 | ~5,977 | **97.7%** | 4,878 (83.5%) |
| SV | Kauthuma **ārcika** | 2,342 | 1,844 | 1,875 | **98.3%** | **0 (0.0%)** |
| YV | Vājasaneyi Mādhyandina | 2,015 | 1,975 | 1,975 | **100.0%** | 1,903 (96.4%) |

Shortfalls are enumerated with causes, which is what earns level 3 rather than 2:
`docs/reports/FULL_INGESTION_RELEASE_QA.md:411` reconciles Sāmaveda exactly —
`1,875 = 1,844 minted + 29 withheld printed verses + 2 unprinted`. The Atharvaveda
divergence is recorded in `docs/FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS.md:228` as
`OPEN_RESEARCH`, attributed to edition-relative verse totals, with a candidate mechanism
raised **and falsified**. 100% of passages carry `canonical_citation` and `canonical_urn`,
both under uniqueness constraints.

### Score 3 — why not 4

Two clauses of level 4 fail.

**No second recension and no post-saṃhitā layer.** There is no Paippalāda Atharvaveda, no
Taittirīya / Kāṭhaka / Maitrāyaṇī Yajurveda, no Brāhmaṇa, no Āraṇyaka, no Upaniṣad, and no
gāna. The Sāmavedic omission is the sharpest: `data/canonical/samaveda_arcika_v1/manifest.json`
states in its own rights block that the gramageya, aranyakageya, uhagana and uhyagana books
are *"a parallel and LARGER body that VG:WORK:SV:KAU cannot address"*.

**The Work node does not carry its own scope.** Measured:

```cypher
MATCH (w:Work) RETURN w
```

Each `Work` has exactly seven properties — `work_id`, `work_name`, `display_label`,
`display_type`, `veda`, `abbreviation`, `corpus_dir`. The Sāmaveda node reads
`display_label: "Samaveda Samhita"`. Its own source manifest says *"Never describe this
dataset as the complete Samaveda."* The warning lives in a JSON file on disk; the graph a
consumer queries does not have it. That is a level-4 blocker by definition and not a
rounding matter — it is the single most misleading string in the product graph.

### What prevents 4, precisely

1. Zero second recensions and zero post-saṃhitā material.
2. `Work` nodes carry no `scope`, `completeness`, `excluded_corpora` or `rights` property.

### Remediation

- Project the corpus manifest's scope and rights blocks onto the four `Work` nodes as
  first-class properties, and rename `VG:WORK:SV:KAU`'s display label to name the ārcika.
  This is a property write over four nodes and moves half of level 4 immediately.
- The cheapest real acquisition for the other half is the Paippalāda AV (digitally
  available) or the Aitareya Brāhmaṇa; the gāna corpus is the highest-value and the hardest.

---

## B. Cross-Veda balance — **2 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Knowledge edges exist for one Veda only. |
| **1** | >90% of non-plumbing knowledge edges sit on a single Veda. |
| **2** | All four Vedas carry knowledge edges, **but** ≥3 corpus-general predicate families are single-Veda, **or** the richest Veda's per-mantra knowledge-edge density exceeds the poorest by >3×. |
| **3** | All four carry knowledge edges; per-mantra density ratio (max/min) ≤3×; **at most 2** corpus-general predicate families are single-Veda; every Veda has a translation layer. |
| **4** | Density ratio ≤2×; **every** corpus-general predicate family populated in all four Vedas; each of the top-20 deities by attribution has a measured presence in ≥2 Vedas. |
| **5** | Density ratio ≤1.5×; per-Veda coverage of every predicate family within ±25% of the corpus mean. |

"Corpus-general" excludes predicates whose subject matter is genuinely single-corpus (e.g.
`REUSES_TEXT_FROM` from SV to RV) and excludes `MUSICALIZED_AS`.

### Measured evidence

```cypher
MATCH (m:Mantra) OPTIONAL MATCH (m)-[r]->()
WHERE NOT type(r) IN ['HAS_TEXT_VERSION','HAS_TRANSLATION','CONTAINS','HAS_QA_ISSUE']
WITH m, count(r) AS d RETURN m.veda AS veda, count(*) AS mantras, sum(d) AS edges,
  round(1.0*sum(d)/count(*),3) AS mean_degree, sum(CASE WHEN d=0 THEN 1 ELSE 0 END) AS zero
ORDER BY veda
```

| Veda | Mantras | Knowledge edges | Mean degree | Zero-degree | Distinct predicates |
| --- | --- | --- | --- | --- | --- |
| RV | 10,552 | **108,213** | **10.255** | 0 | 18 |
| AV | 5,839 | 28,083 | 4.810 | 469 | 25 |
| SV | 1,844 | 9,496 | 5.150 | 33 | **11** |
| YV | 1,975 | 10,673 | 5.404 | 85 | 21 |

Density ratio = 10.255 / 4.810 = **2.13×**, which passes level 3's ≤3× and fails level 4's ≤2×
only narrowly. The Rigveda holds 108,213 of 156,465 knowledge edges — **69.2%** — on 46.8% of
the corpus's mantras.

The level-3 blocker is the predicate census, not the density:

| Predicate family | RV | AV | SV | YV |
| --- | --- | --- | --- | --- |
| `HAS_DEVATA` | 10,558 | **0** | **0** | **0** |
| `HAS_RISHI` | 10,565 | **0** | **0** | **0** |
| `HAS_CHANDAS` | 10,523 | **0** | **0** | **0** |
| `MENTIONS_LEMMA` | 9,000 | **0** | **0** | **0** |
| `MENTIONS_ENTITY` → `Devata` | 9,000 | **0** | **0** | **0** |
| `PARALLEL_TO` | 69 | 0 | 0 | 0 |
| LLM layer (`DESCRIBES`, `INVOKES`, `REQUESTS`…) | **0** | 736 total | **0** | 736 total |
| `HAS_TRANSLATION` | 10,502 | 4,878 | **0** | 1,903 |

**Five** corpus-general families are 100% Rigvedic. The whole attribution apparatus — who
composed it, to whom, in what metre — is a Rigveda-only fact, so nineteen of the fifty
canonical research questions cannot be asked outside the Rigveda at all. Conversely the
model-extracted layer is 100% non-Rigvedic, which means no single Veda can be compared with
another using the same evidence class.

### Score 2 — why not 3

Level 3 caps single-Veda families at two; the measured count is five. Sāmaveda additionally
has **zero** translations and only 11 distinct predicate types against Atharvaveda's 25.

### What prevents 3

The absence of any non-Rigvedic attribution source. This is an acquisition, not a modelling
gap, and it is correctly named as such in the V2 backlog. Its documented partial substitute —
theonym `DomainEntity` records for Indra, Varuṇa, Rudra, Viṣṇu and Mitra so the four-Veda
mention layer can reach them — is confirmed still absent by direct probe (0 rows for any
`DomainEntity` whose label or alias contains those stems).

### Remediation

1. Build the four-Veda theonym mention layer with a per-alias, morphology-aware audit. This
   moves B toward 3 and simultaneously moves C, D, M and S.
2. Acquire or derive an Atharvavedic / Yajurvedic attribution layer (the AV has kāṇḍa-level
   ṛṣi/devatā traditions; the Bṛhaddevatā and the AV Anukramaṇī are candidate sources).
3. Ingest a Sāmaveda translation. Zero is the worst single cell in the table.

---

## C. Entity resolution — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No entity layer; surface strings only. |
| **1** | Entity nodes exist with no alias sets and no ambiguity marking. |
| **2** | Aliases and unique ids present, but ambiguity is unmarked **or** a known conflation class is unmeasured. |
| **3** | Unique ids under a database constraint on every entity type; alias sets **probed against the corpus** with rejections recorded; ambiguity flagged per edge with a **measured rate** overall and per entity; 0 duplicate ids; 0 orphan entities. |
| **4** | Level 3, **plus** the ambiguity flag demonstrably affects grade or state (a consumer filtering on `quality_tier` alone does **not** receive known-ambiguous edges); **plus** a human-adjudicated precision figure for the top-20 highest-volume aliases; **plus** every deity with attribution volume in the top 20 resolvable as a mention-layer entity. |
| **5** | Level 4, plus every flagged edge adjudicated (accepted or retired, none left flagged-and-accepted), and inflectional coverage measured against a morphological analyser rather than a hand-authored list. |

### Measured evidence

```cypher
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e:DomainEntity)
WITH e, count(*) AS total, sum(CASE WHEN r.theonym_ambiguous THEN 1 ELSE 0 END) AS amb
WHERE amb>0 RETURN e.entity_key, total, amb, round(100.0*amb/total,1) AS pct
ORDER BY amb DESC LIMIT 6
```

| Entity | Edges | Flagged | % |
| --- | --- | --- | --- |
| `VG:CONCEPT:AGNI-FIRE` | 2,095 | 1,205 | **57.5** |
| `VG:CONCEPT:SOMA-DRINK` | 1,570 | 841 | 53.6 |
| `VG:CONCEPT:SURYA-SUN` | 653 | 351 | 53.8 |
| `VG:CONCEPT:PRTHIVI-EARTH` | 742 | 318 | 42.9 |
| `VG:CONCEPT:BRAHMAN-FORMULATION` | 482 | 188 | 39.0 |
| `VG:CONCEPT:USAS-DAWN` | 283 | 129 | 45.6 |

Corpus-wide flag rate: **3,896 / 28,675 = 13.59%**. Level 3's clauses all pass: 22 uniqueness
constraints; 0 duplicate `entity_key`; 0 orphan `DomainEntity`; 1,336 Sanskrit and 330 English
aliases, all probed (the material lexicon records that bare `ayas` token-matches nothing and
substring-matches 645 times inside `payasā`, and ships six read-and-verified inflected forms
instead); 214 Devatā, 66 with 136 probed `aliases_iast`.

### Score 3 — why not 4

Three clauses of level 4 fail on measurement.

**The flag changes nothing a query can filter on.**

```cypher
MATCH ()-[r:MENTIONS_ENTITY]->(:DomainEntity) WHERE r.theonym_ambiguous
RETURN r.quality_tier AS tier, r.state AS state, count(*) AS n
```
→ `TIER_B / ACCEPTED / 3896`. All 3,896 known-hazardous edges carry the identical grade and
state as the 24,779 unflagged ones. A consumer filtering `quality_tier IN ['TIER_A','TIER_B']`
— the obvious filter, and the one the whole tier system trains a consumer to use — receives
every one of them, including 1,205 edges asserting that a passage mentions *fire* on the sole
evidence of a vocative address to the *god*.

**No adjudicated per-alias precision exists.** Confirmed in §O.

**The major theonyms are still unreachable.** 0 `DomainEntity` for Indra / Varuṇa / Rudra /
Viṣṇu / Mitra, and the legacy `MENTIONS_ENTITY → Devata` layer reaches only **40 of 214**
Devatā and is Rigveda-only.

Three further resolution defects, measured, that bear on the score:

- **96.9% of mention edges rest on a single alias hit** (`alias_count = 1` on 27,780 of
  28,675). Corroboration is the exception, not the rule.
- **`brahman` is the `preferred_label_sa` of two distinct entities** (`BRAHMAN-FORMULATION`
  and `BRAHMAN-PRIEST`) — the exact pair whose sandhi leak V2 had to suppress.
- **The ṛṣi layer is unresolved.** 322 of 367 `Rishi.display_label` values are multi-word
  bundled Anukramaṇī strings (`agastyāntevāsī brahmacārī`, `aindraḥ vasukraḥ`), and
  `occurrence_count = 0` on all 367. `RishiFamily` is a declared label with **0 nodes** and
  a uniqueness constraint.
- **12 domain-entity aliases collide exactly with a Devatā stem** (`soma`, `sūrya`, `uṣas`,
  `pṛthivī`, `rātrī`, `svasti`, `dakṣiṇā`, `ātman`, `śraddhā`, `jyā`, `sītā`, `nadī`).

### Remediation

1. Downgrade flagged edges to a distinct tier or set `state = CANDIDATE`, so that the tier
   filter is sufficient. One loader change; it is the highest-leverage fix on this dimension.
2. Author the five missing theonym entities under the per-alias audit discipline V2 proved.
3. Split the bundled ṛṣi strings into individual `Rishi` nodes and populate `RishiFamily`.

---

## D. Devatā knowledge depth — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No deity layer. |
| **1** | Deity nodes with names only. |
| **2** | Deity nodes plus a single-valued type field with ≥50% unknown/unspecified. |
| **3** | Every deity carries a structural fact and a **multi-valued** role vocabulary; ≥50% carry ≥1 non-unspecified role; all of the top 20 by attribution classified; identity relations (composition, group membership, epithets) exist and are populated for at least some deities. |
| **4** | ≥80% of deities carry ≥1 non-unspecified role; **every** structural `PAIR` decomposed and **every** `GROUP` has members; each of the top 20 carries ≥3 distinct outbound relation types besides `HAS_AXIS`; each of the top 20 has measured presence in ≥2 Vedas. |
| **5** | Level 4, plus **per-Veda (or per-maṇḍala) role profiles** rather than one global assertion per deity, and epithets locatable in the corpus (each `Epithet` node reachable from ≥1 passage). |

### Measured evidence

214 Devatā. 214/214 carry `structure`, `label_en`, `short_description`, `attribution_scope`
and `attribution_scope_note`. `is_classified = true` on **113/214 (52.8%)**; the
`UNSPECIFIED` axis holds **101 deities**, making it the single largest axis in the vocabulary.
Mean axes per deity = 289/214 = **1.35**.

```cypher
MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata) WITH d, count(*) AS attributed
ORDER BY attributed DESC LIMIT 20
OPTIONAL MATCH (d)-[:HAS_AXIS]->(a:DeityAxis) WITH d, attributed, collect(a) AS axes
OPTIONAL MATCH (d)-[:HAS_EPITHET]->(ep) WITH d, attributed, axes, count(ep) AS ep
OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(d)
RETURN d.entity_key, attributed, size(axes) AS n_axes, ep,
  count(DISTINCT p.veda) AS vedas, count(p) AS mentions ORDER BY attributed DESC
```

| Devatā | Attributed | Axes | Epithets | Vedas via mention | Mentions |
| --- | --- | --- | --- | --- | --- |
| INDRAH | 2,869 | 3 | 5 | **1** | 2,305 |
| AGNIH | 1,988 | 3 | 4 | **1** | 1,604 |
| PAVAMANAH-SOMAH | 1,087 | 1 | 0 | **0** | **0** |
| VISVEDEVAH | 805 | 1 | 0 | **0** | **0** |
| ASVINAU | 631 | 2 | 3 | 1 | 439 |
| MARUTAH | 428 | 2 | 0 | 1 | 401 |
| MITRAVARUNAU | 184 | 2 | 0 | 1 | 92 |
| ADITYAH | 100 | 2 | 0 | **0** | **0** |
| RBHAVAH | 96 | 1 | 0 | **0** | **0** |
| INDRAVARUNAU | 70 | 3 | 0 | **0** | **0** |

**Zero of the 214 deities has measured presence in more than one Veda.** Six of the top twenty
have no mention-layer evidence at all. Only two of the top twenty carry an epithet.

Outbound relation vocabulary from `Devata`, entire:

| Predicate | Edges | Distinct deities |
| --- | --- | --- |
| `HAS_AXIS` | 289 | 214 |
| `DEVATA_ASSOCIATED_WITH` | 140 | 105 |
| `COMPOSED_OF` | 28 | 14 |
| `HAS_EPITHET` | 13 | 4 |
| `MEMBER_OF` | 13 | 13 |

`PERSONIFIES`, `WIELDS`, `RECEIVES_OFFERING`, `PERFORMS_ACTION`, `ASSOCIATED_WITH_CONCEPT`,
`ASSOCIATED_WITH_PHENOMENON`, `ASSOCIATED_WITH_SUBSTANCE` and `CO_OCCURS_WITH` are all
**declared with endpoint signatures and all zero**. Their work is done by one untyped
`DEVATA_ASSOCIATED_WITH` edge whose 140 instances carry no relation property — so "Indra
wields the vajra" and "Rudra is associated with healing" are the same edge type with no way
to tell them apart.

Structural completeness:

```cypher
MATCH (d:Devata {structure:'PAIR'}) OPTIONAL MATCH (d)-[:COMPOSED_OF]->(c)
WITH d, count(c) AS n RETURN count(*) AS pairs, sum(CASE WHEN n=0 THEN 1 ELSE 0 END) AS undecomposed
```
→ **24 of 38 pairs undecomposed**. `INDRAVARUNAU` (attribution 70, degree 70) still has zero
components, confirming V2 backlog item 9 as open. **30 of 33 `GROUP` deities have no
`MEMBER_OF` edge**; the two `DeityGroup` nodes hold 4 and 9 members between them.

### Score 3 — why not 4

Every clause of level 4 fails: 52.8% classified against a required 80%; 24 undecomposed
pairs and 30 memberless groups against a required zero; the top twenty carry at most 3
outbound relation types *including* `HAS_AXIS`, so none reaches "≥3 besides"; and zero
deities have two-Veda presence.

### What prevents 4

The 101 `UNSPECIFIED` deities are largely one-off abstract and patron labels, and V2's
decision to record a justified refusal rather than invent an axis is correct — but the
rubric measures the graph, not the process, and a 47.2% unspecified rate is a 3. The
two-Veda clause is blocked by the same missing theonym layer as B and C.

### Remediation

1. Retire `DEVATA_ASSOCIATED_WITH` in favour of the five declared typed predicates. The
   registry already records the relation kind; the projection discards it — precisely the
   flattening defect V2 fixed for node types and left in place for this edge type.
2. Decompose the remaining 24 pairs and populate `MEMBER_OF` for the 30 groups. Both are
   bounded authoring tasks over ≤54 rows.
3. Link the 13 `Epithet` nodes to passages (currently **0 passage links**), which is also
   the sole blocker on question 42.

---

## E. Ritual knowledge depth — **1 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No ritual entity of any kind. |
| **1** | Fewer than 5 rites modelled, **or** rites modelled with **no step/sequence structure at all**. |
| **2** | 5–9 rites, each with ≥3 apparatus edges (offering / substance / object / role / purpose), and ≥1 rite with an ordered step sequence. |
| **3** | ≥10 rites, each with ≥3 apparatus edges, ≥3 with ordered step sequences, and each rite linked to the passages that describe it by a dedicated predicate (not by lexical co-occurrence). |
| **4** | ≥25 rites; ordered steps on ≥10; a description predicate populated for every rite; purposes distinguishable from outcomes; and a measured per-rite passage recall. |
| **5** | Level 4, plus rite variants across recensions, and a Śrauta/Gṛhya (or equivalent) distinction carried as data rather than prose. |

### Measured evidence

```cypher
MATCH (r:Ritual) OPTIONAL MATCH (r)-[e]->(x)
RETURN r.entity_key, count(e) AS out_edges, collect(DISTINCT type(e)) AS preds
```

| Ritual | Apparatus edges | Predicates |
| --- | --- | --- |
| `YAJNA-SACRIFICE` | 21 | `BROADER_THAN`, `USES_OFFERING`, `USES_SUBSTANCE`, `USES_OBJECT`, `INVOKES_DEVATA`, `PERFORMED_BY`, `PERFORMED_FOR` |
| `SOMA-PRESSING` | 10 | `USES_SUBSTANCE`, `USES_OBJECT`, `INVOKES_DEVATA`, `PERFORMED_BY` |
| `AGNIHOTRA` | 3 | `INVOKES_DEVATA`, `USES_OBJECT`, `USES_OFFERING` |
| `DIKSA-CONSECRATION` | **1** | `PERFORMED_BY` |

**4 `Ritual` nodes. 35 apparatus edges in total. `HAS_STEP` = 0. `DESCRIBED_IN` = 0.** All 35
edges are `TIER_D`. The only passage→ritual paths are `MENTIONS_ENTITY` (1,512) and
`ABOUT_CONCEPT` (2,299), both of which assert lexical presence of a word, not that a passage
describes a rite.

Adjacent structure exists and is also thin: 4 `SocialRite` nodes (marriage 41 passages,
house-building 30, childbirth 15, funerary 10), 5 `RitualRole` nodes (223 mentions),
2 `Offering` nodes (havis 401, dakṣiṇā 66), 4 `HumanConcern` nodes (219 edges).

### Score 1 — why not 2

Level 2 needs 5–9 rites and at least one ordered sequence. There are 4 rites and **zero**
step edges anywhere in the graph. `HAS_STEP` is declared with an endpoint signature
(`Ritual → Action`) and is empty; under the declared-but-empty rule that is a zero, not a
partial credit.

This is the score most likely to be argued with, so the justification is stated plainly:
this graph contains the entire Vājasaneyi Saṃhitā — 1,975 verses of a ritual manual — plus
the Sāmavedic ārcika, which exists to be sung at rites. Four rites and no sequencing is the
bottom of the scale for a corpus of that content, and calling it a 2 because the schema is
elegant would be exactly the inflation this rubric forbids.

### What prevents 2

Authoring, not acquisition. Nothing in the corpus or the contract blocks a 25-rite model
with ordered steps. `RELATIONSHIP_SIGNATURES` already declares `HAS_STEP` and `DESCRIBED_IN`
with correct endpoints; both are unpopulated.

### Remediation

1. Author the core Śrauta rites from the Yajurveda (agnyādheya, darśapūrṇamāsa, agniṣṭoma,
   vājapeya, rājasūya, aśvamedha, agnicayana) and the domestic rites from the Atharvaveda,
   each with ordered `HAS_STEP` edges onto `Action` entities and `DESCRIBED_IN` onto the
   verses. Probe every rite name against the corpus first, as V2 did — and note that V2
   already found and recorded that `aśvamedha`'s single token hit (RV 5.27.5) is the *patron*,
   not the rite, which is the kind of finding this work must keep producing.
2. Populate `DESCRIBED_IN` for the existing four rites from the passage citations already
   present in `data/domain/vedagraph_domain_v2/rituals.yaml`. That is a load, not research.

---

## F. Material-culture depth — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No material entities. |
| **1** | <20 material entities (animal / plant / object / substance / metal / crop / weapon / offering), **or** entities with no per-Veda distribution. |
| **2** | 20–49 material entities, each with probed aliases and per-Veda mention counts. |
| **3** | 50–99 material entities; ≥80% reaching ≥2 Vedas; alias sets read against the text with **rejections recorded**; sublabels implying their superlabel so the general question stays askable. |
| **4** | ≥150 material entities; ≥90% with ≥5 mentions; a human-adjudicated per-entity precision on a sample; **and** material entities related to one another (made-of / part-of / used-in), not only to passages. |
| **5** | ≥300 entities with a materials-and-technology sub-ontology (metal → artefact → use), and cross-Veda distribution tested for significance. |

### Measured evidence

```cypher
MATCH (e:DomainEntity) WHERE e:Animal OR e:Plant OR e:Object OR e:Substance OR e:Offering
OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e)
WITH e, count(p) AS m, count(DISTINCT p.veda) AS v
RETURN count(*) AS material_entities, sum(CASE WHEN v>=2 THEN 1 ELSE 0 END) AS two_plus,
  round(100.0*sum(CASE WHEN v>=2 THEN 1 ELSE 0 END)/count(*),1) AS pct,
  sum(CASE WHEN v=4 THEN 1 ELSE 0 END) AS four_veda,
  sum(CASE WHEN m<5 THEN 1 ELSE 0 END) AS under5, round(avg(m),1) AS mean_mentions
```
→ **56 material entities · 49 reach ≥2 Vedas (87.5%) · 27 reach all four · 6 under 5
mentions · mean 120.7 mentions.**

| Family | Entities | Mentions | Mean |
| --- | --- | --- | --- |
| Object (incl. 3 Weapon) | 19 | 1,721 | 90.6 |
| Plant (incl. 5 Crop) | 13 | 528 | 40.6 |
| Animal | 12 | 1,577 | 131.4 |
| Substance (incl. 5 Metal) | 10 | 2,465 | 246.5 |
| Offering | 2 | 467 | 233.5 |

Real distributional results land. Metals by Veda:
gold RV 38 / AV 34 / SV 6 / YV 6 · `ayas` RV 8 / AV 3 · lead AV 4 / YV 3 · silver AV 1 / YV 1 ·
copper YV 1. Crops: barley all four Vedas (RV 19, AV 15, SV 2, YV 2); rice **AV only** (3);
sesame **AV only** (5); beans **AV only** (2). That rice and sesame appear only in the
Atharvaveda while barley spans all four is a genuine, checkable, non-obvious result of the
kind this dimension is meant to reward. Sublabels behave: `Crop ⊂ Plant`, `Metal ⊂ Substance`,
`Weapon ⊂ Object`, confirmed via `SUPERLABELS`, so "which plants" still finds the crops.
Rejections are recorded — bare `ayas` matching nothing, and the six inflected forms shipped
in its place.

### Score 3 — why not 4

Three clauses of level 4 fail. **56 entities against a required 150.** **No per-entity
precision measurement** (§O). And material entities are almost entirely unrelated to each
other:

```cypher
MATCH (a:DomainEntity)-[r]->(b:DomainEntity)
WHERE a:Animal OR a:Plant OR a:Object OR a:Substance OR a:Offering
RETURN type(r) AS rel, count(*) AS n
```
→ **`BROADER_THAN`, 24 edges. Nothing else.** There is no `MADE_OF`, no `PART_OF`, no
`USED_IN`. A chariot and a wheel and a horse are three unrelated mention targets.

### What prevents 4

Registry volume and the absence of any lateral material predicate in the contract. Note the
counts also make the thin end visible: crops average 14.8 mentions, metals 21.0, weapons 26.7
— defensible for a probed lexicon, but 6 entities sit under 5 mentions and one metal (copper)
rests on a single passage.

### Remediation

1. Triple the material registry toward 150+ entities, prioritising the Atharvaveda's
   domestic and agricultural vocabulary where the corpus is richest and the graph thinnest.
2. Add `MADE_OF` / `PART_OF` / `USED_IN` to the contract with endpoint signatures, and
   populate them from the lexicon's existing curation notes.

---

## G. Human / social knowledge depth — **2 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No ṛṣi, tribe, role or social-rite representation. |
| **1** | Ṛṣi names as opaque strings with no verse attribution, **or** zero social entities. |
| **2** | Ṛṣis attributed to verses, plus 10–24 social entities (tribe / role / rite / concern); family layer absent or declared-and-empty. |
| **3** | A **populated** ṛṣi family layer joined to ṛṣis; ≥25 social entities; ≥3 social-structure predicates populated (family, tribe, role, patronage). |
| **4** | Family and tribe layers populated and joined to passages; ≥100 social entities; an occupational / varṇa vocabulary measured against the corpus; per-Veda social distribution available. |
| **5** | Level 4, plus genealogy (ṛṣi → ṛṣi descent) and a patron / dānastuti layer with passage evidence. |

### Measured evidence

367 `Rishi` nodes, all with verse attribution (max 836 mantras, 0 with zero attribution).
That is the whole of what is populated.

| Element | Measured |
| --- | --- |
| `RishiFamily` nodes | **0** (label declared, uniqueness constraint and index present) |
| `BELONGS_TO_FAMILY` | **0** |
| `ASSOCIATED_WITH_TRIBE` | **0** |
| `Rishi` → non-passage edges | **0** |
| `Rishi.occurrence_count` | **0 on all 367** |
| `Tribe` entities / mentions | 5 / **42 total** (max: Turvaśa 15) |
| `RitualRole` entities / mentions | 5 / 223 (yajamāna 94, brahman 67, adhvaryu 24, purohita 20, brahmacārin 18) |
| `SocialRite` entities / passages | 4 / 96 |
| `HumanConcern` entities / passages | 4 / 219 (sapatna 101, puṣṭi 94, ṛṇa 18, saṃjñāna 6) |
| **Total social entities** | **18** |

### Score 2 — why not 3

Level 3 requires a populated family layer, ≥25 social entities and ≥3 populated
social-structure predicates. Measured: family layer has **zero nodes**, 18 social entities,
and **zero** social-structure predicates (`USED_FOR_RITE` and `ADDRESSES_CONCERN` are
passage→entity topical edges, not social structure — a passage being *for* a marriage does
not encode who marries whom, or that a ṛṣi belongs to a gotra).

### What prevents 3

`RishiFamily` is the clearest declared-but-empty case in the graph: it has a label in
`PRODUCT_LABELS`, a uniqueness constraint, a range index, and no rows. The blocking
precondition is real and named in C: 322 of 367 ṛṣi display labels are bundled Anukramaṇī
strings, so the family cannot be derived without first splitting the strings.

### Remediation

1. Split the 322 multi-word `Rishi` labels into individual persons; derive the gotra from
   the patronymic morphology; populate `RishiFamily` and `BELONGS_TO_FAMILY`. This alone
   unblocks questions 2, 19, 24 and 35 and moves G to 3.
2. Populate `Rishi.occurrence_count` — it is trivially derivable from the 10,565 `HAS_RISHI`
   edges already present and is currently a field that lies by omission.
3. Expand the tribe registry (42 total mentions across 5 tribes is a rounding error against
   a corpus with the Battle of the Ten Kings in it) and add a patron / dānastuti layer —
   note that `VG:DEVATA:DANASTUTIH` already has 50 attributed mantras waiting for it.

---

## H. Agentive / action semantics — **1 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No representation of action or event of any kind. |
| **1** | Action **nouns** as entities, reachable only by a mention or co-occurrence predicate; **no** assertion anywhere carries an agent role slot. |
| **2** | ≥1 populated predicate whose subject is an agent and whose object is an action or patient, with ≥100 evidence-backed instances. |
| **3** | ≥1,000 role-bearing assertions (actor + action + patient) spanning ≥2 Vedas, each evidence-cited and each carrying a quality tier. |
| **4** | Level 3, plus an action-head / verb inventory derived from morphology; ≥5,000 assertions; and a measured precision ≥0.85 on a human-adjudicated sample. |
| **5** | Level 4, plus event identity (the same event referenced from multiple passages) and negation / modality marking. |

### Measured evidence

```cypher
MATCH ()-[r]->() WHERE r.actor_entity_id IS NOT NULL OR r.actor IS NOT NULL
  OR r.agent IS NOT NULL OR r.patient IS NOT NULL RETURN count(*) AS edges_with_role_slots
```
→ **0.** Neo4j additionally reports all four property keys as non-existent in the store.
There is no agent, actor or patient slot anywhere in this graph.

| Element | Measured |
| --- | --- |
| `Action` nodes | 5 (stoma 402 mentions, janman 345, namas 240, yudh 123, dāna 109) |
| `PERFORMS_ACTION` | **0** (declared `Devata → Action`) |
| `HAS_STEP` | **0** (declared `Ritual → Action`) |
| `DESCRIBES_ACTION` | 35, all `TIER_D` / `state=CANDIDATE`, AV 15 + YV 20 |
| Verb lemmas | **0** — `parts_of_speech` values are `nominal stem` 8,897, `root` 702, `invariable` 406, `pronoun` 26 |
| `Devata → Action` edges of any type | **0** |

So "what does Indra do" reduces to co-occurrence:

```cypher
MATCH (m:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'}),
      (m)-[:MENTIONS_ENTITY]->(a:Action)
RETURN a.display_label, count(*) ORDER BY 2 DESC
```
→ praise 112, birth 46, liberality 44, battle 43, homage 13. Every one of those is "a mantra
attributed to Indra also contains this noun". None asserts that Indra *did* anything.

**The asset that would fix this exists and is not loaded.** The sealed artifact
`vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1` (`seal_status: VALIDATED`, 0 of 11
integrity counters non-zero) holds 2,459 assertions over 448 Rigvedic mantras including
**554 `EVENT` objects carrying `actor_entity_id`, `patient`, `other_participants` and
`action_head`**, plus 553 `DESCRIBES_ACTION` and 395 `REQUESTED_OUTCOME`. Confirmed absent:

```cypher
MATCH ()-[r]->() WHERE r.run_id IS NOT NULL RETURN r.run_id, count(*) ORDER BY 2 DESC
```
→ the only semantic run in the graph is `vedagraph-graph-enrichment-v1:semantic:fc3293cc…`
with 736 edges (AV+YV). The 448-mantra Rigvedic artifact is nowhere in the store.

### Score 1 — why not 2

Level 2 needs a populated agent-subject predicate with ≥100 instances. The only agentive-
sounding predicate, `DESCRIBES_ACTION`, has 35 instances, a *passage* subject rather than an
agent, and no role slots. Zero edges in the graph carry an actor.

Not 0 because 5 `Action` entities with 1,219 mention edges and 35 model-proposed action edges
do exist and are gradeable — the representation is present and merely non-agentive.

### What prevents 2

A load, not research. The blocker is upstream: `full_run.py` is Luna-pinned, so a non-Luna
full-corpus semantic run is blocked, and the 448-mantra artifact is `CANDIDATE / NEEDS_REVIEW`
with `human_gold_status: UNANNOTATED`. But projecting it as `TIER_C`-eligible candidates does
not require the full run and does not require gold — it requires a projection.

### Remediation

1. **Project the sealed 448 artifact.** 554 EVENT objects with actor/patient/action_head
   becomes the graph's first role-bearing layer, its first Rigvedic model layer, and its
   first `TIER_C` candidate population. Highest single-action payoff in this scorecard.
2. Add `PERFORMS_ACTION` population from those events (the contract already declares it).
3. Derive an action-head inventory from the 702 `root` lemmas, which are already in the graph
   and currently connected to nothing.

---

## I. Concept ontology quality — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Free-text tags; no controlled vocabulary. |
| **1** | A flat entity list with no types and no definitions. |
| **2** | Typed entities with definitions, but no hierarchy, **or** a hierarchy covering <25% of entities. |
| **3** | Typed entities; 100% definition coverage; unique ids; a **closed node-type enum enforced at load** (an unknown type raises rather than defaulting); hierarchy covering ≥25% of entities. |
| **4** | Level 3, plus hierarchy depth ≥3 covering ≥60% of entities; **a single authoritative passage→concept layer** (no rival layer answering the same question with a materially different number); ≥300 entities. |
| **5** | Level 4, plus lateral relations (part-of, opposite-of, instrument-of) at scale, and ≥1,000 entities. |

### Measured evidence

163 `DomainEntity` across 23 node types. **0 entities without a `definition` or
`short_description`** (mean definition length 102.5 characters). 0 duplicate `concept_id` or
`entity_key`, both constrained. `labels_for_node_type` raises `ValueError` on an unknown type
rather than defaulting to `Concept`, which is the enforcement level 3 requires and is the
direct fix for the V1 flattening.

Hierarchy:
```cypher
MATCH (a)-[:BROADER_THAN]->(b) RETURN count(*) AS edges, count(DISTINCT a) AS parents, count(DISTINCT b) AS children
;; MATCH path=(a)-[:BROADER_THAN*]->(b) RETURN max(length(path)) AS max_depth
;; MATCH (e:DomainEntity) WHERE NOT (e)-[:BROADER_THAN]-() RETURN count(e) AS outside
```
→ **57 edges · 15 parents · 57 children · max depth 2 · 92 of 163 entities (56.4%) outside
the hierarchy.** Coverage = 43.6%, which clears level 3's 25% and fails level 4's 60%.

**The rival-layer problem is measured, and it is the largest finding on this dimension.**

```cypher
MATCH (c:Concept) WHERE ()-[:ABOUT_CONCEPT]->(c) AND ()-[:MENTIONS_ENTITY]->(c)
OPTIONAL MATCH (a:Passage)-[:ABOUT_CONCEPT]->(c) WITH c, collect(DISTINCT a.entity_id) AS A
OPTIONAL MATCH (m:Passage)-[:MENTIONS_ENTITY]->(c) WITH c, A, collect(DISTINCT m.entity_id) AS M
WITH c, size(A) AS nA, size(M) AS nM, size([x IN A WHERE x IN M]) AS both
RETURN count(*) AS shared_entities, sum(nA) AS about, sum(nM) AS mention, sum(both) AS agree,
  round(100.0*sum(both)/sum(nA),1) AS pct_about_confirmed,
  round(100.0*sum(both)/sum(nM),1) AS pct_mention_confirmed
```
→ **89 shared entities · 47,542 `ABOUT_CONCEPT` links · 26,642 mention links · 26,296
agreeing · only 55.3% of `ABOUT_CONCEPT` links confirmed by a Sanskrit mention · 98.7% of
mention links confirmed by `ABOUT_CONCEPT`.**

The mention layer is very nearly a **subset** of the concept layer. Per entity the divergence
is severe: `DANA-LIBERALITY` 708 vs 109 (15.3% overlap), `YUDH-BATTLE` 509 vs 123 (24.2%),
`ASVA-HORSE` 918 vs 234 (25.2%), `STOMA-PRAISE` 1,367 vs 402 (29.3%). `ABOUT_CONCEPT` remains
capped at max degree 4 (avg 2.632, 18,062 passages), reaches only **89 of 163** entities, and
carries `confidence = 0.42` on 20,350 of its 47,542 edges — all 20,350 of which are
`evidence_basis = TRANSLATION`, resting on an English word in Griffith 1896.

One further residual: **all 163 `DomainEntity` also carry `:Concept`.** The V1 defect was
that the projection wrote rivers and rituals as `:Concept`; V2 added the specific label and
did not remove the flat one, so `MATCH (c:Concept)` still returns cattle, the Indus and the
yajña. Additive labelling is defensible, but it means the flat query is still wrong and the
V2 report's framing of that defect as fixed is half true.

### Score 3 — why not 4

Four clauses fail: depth 2 (<3); 43.6% coverage (<60%); 163 entities (<300); and two live
rival layers disagreeing by 45 percentage points on the same question.

### Remediation

1. **Adjudicate the rival layers on a sample and retire one.** The measured 55.3% / 98.7%
   asymmetry is the whole argument: either `ABOUT_CONCEPT` has ~45% precision error or the
   mention layer has ~45% recall loss, and until a gold sample decides, every frequency claim
   in the graph has two answers. This is the same unlock as O and P.
2. Deepen `BROADER_THAN` to ≥3 levels and bring the 92 unhierarchised entities in.
3. Grow the registry toward 300 entities.

---

## J. Textual reuse / formula quality — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No parallel or formula layer. |
| **1** | Parallels asserted with no similarity measure and no evidence. |
| **2** | Parallels with a similarity score but a single method or a single Veda pair; **or** formulas with no length / spread metadata. |
| **3** | ≥3 reuse or parallel predicates populated, each edge carrying similarity, method and Veda pair; **all six** Veda pairs represented; formulas carrying word count, occurrence count and a cross-Veda flag; ≥90% of the derivative corpus's reuse located. |
| **4** | Level 3, plus reuse predicates **matching the declared contract** (no declared reuse predicate empty while undeclared ones carry the load); a stated minimum unit length with the sub-threshold population removed or flagged; symmetric traversal guaranteed (or explicitly documented as directed); and `match_level` populated on 100% of edges. |
| **5** | Level 4, plus direction of borrowing argued from evidence rather than assumed from corpus identity, and a measured precision on a philologist-adjudicated sample. |

### Measured evidence

Five populated reuse predicates, 6,596 edges:

| Predicate | Edges | Per-edge metrics |
| --- | --- | --- |
| `NEAR_PARALLEL_OF` | 3,049 | similarity, edit_ratio, lcs_ratio, token_jaccard, ngram_jaccard, match_level, veda_pair |
| `REUSES_TEXT_FROM` | 1,684 | same |
| `EXACT_PARALLEL_OF` | 1,006 | similarity, methods, strongest_method |
| `VARIANT_OF` | 788 | same as NEAR |
| `PARALLEL_TO` | 69 | similarity, methods (RV-internal only) |

**All six Veda pairs are represented** (RV-SV 1,595, AV-RV 774, RV-YV 638, AV-SV 458,
AV-YV 203, SV-YV 169, mean similarity 0.90–0.94). Sāmavedic reuse of the Rigveda is located
for **1,662 of 1,844 SV mantras = 90.1%**, exactly at level 3's threshold. Formulas: 4,825,
**0 unused**, all carrying `word_count`, `occurrence_count`, `cross_veda`, `veda_counts`;
3,643 cross-Veda, 229 in all four, max 93 occurrences.

### Score 3 — why not 4

All four level-4 clauses fail, and one of them is a contract violation.

**The declared reuse predicate is empty and five undeclared ones do its work.**
`TEXTUALLY_REUSED_AS` is declared in `DOMAIN_RELATIONSHIP_TYPES` with the signature
`Passage → Passage` and has **0** edges. `SHARES_FORMULA_WITH` has **four range indexes** and
**0** edges. Meanwhile `EXACT_PARALLEL_OF`, `NEAR_PARALLEL_OF`, `REUSES_TEXT_FROM`,
`VARIANT_OF` and `PARALLEL_TO` are all outside the V2 contract entirely.

**`match_level` is blank on 70.1% of `REUSES_TEXT_FROM`:**
```cypher
MATCH (s:Passage)-[r:REUSES_TEXT_FROM]->(t:Passage)
RETURN r.match_level AS level, count(*) AS n, round(avg(r.similarity),3) AS avg_sim
```
→ `"" / 1,180 / 0.884` · `SANDHI_INSENSITIVE / 415 / 1.000` · `SCRIPT_FOLDED / 89 / 1.000`.
The 1,180 non-exact reuse claims are the ones whose level matters most and they carry none.

**No minimum unit length, and the sub-threshold population is large.** 1,977 of 4,825
formulas (**41.0%**) are two tokens, and 1,557 of those are flagged cross-Veda. The
widest-spread "formulas" in the corpus, by occurrence:

| Formula | Words | Uses |
| --- | --- | --- |
| `pāta svastibhiḥ sadā naḥ` | 4 | 93 |
| `viśvā bhuvanā` | **2** | 60 |
| `parame vyoman` | **2** | 53 |
| `brahmaṇas pate` | **2** | 38 |
| `viśvā bhuvanāni` | **2** | 32 |
| `asya bhuvanasya` | **2** | 24 |

Eight of the top twelve four-Veda "formulas" are two-word strings. Some (`brahmaṇas pate`)
are genuine formulaic vocatives; others (`asya bhuvanasya`, "of this world") are ordinary
syntax. The graph offers `word_count` so a researcher *can* filter, which is why this is a
3 and not a 2 — but nothing marks the distinction, so the default answer to "which formulas
span all four Vedas" is dominated by n-grams. The V1 finding that **1,103 of 4,825 formulas
are strict substrings of another** is carried unchanged.

**Traversal is one-way.** `MATCH (a)-[r:EXACT_PARALLEL_OF]->(b) WHERE (b)-[:EXACT_PARALLEL_OF]->(a)`
returns **0**; the same for `NEAR_PARALLEL_OF`. Every parallel edge exists in one direction
only and no property documents that, so a consumer writing a directed match silently sees
half the graph.

### Remediation

1. Reconcile the contract: either declare the five live reuse predicates or migrate them onto
   `TEXTUALLY_REUSED_AS` with a `reuse_kind` property. Drop the four `SHARES_FORMULA_WITH`
   indexes or populate the type.
2. Backfill `match_level` on the 1,180 blank edges.
3. Set a minimum formula length (≥3 tokens is the defensible default) and either retire or
   flag the 1,977 two-token entries. Resolve the 1,103 substring redundancies.
4. Document the one-way direction as an edge property, or materialise the reciprocal.

---

## K. Evidence / provenance quality — **4 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No provenance field on any edge. |
| **1** | A confidence score only. |
| **2** | A trust or layer field on a subset; vocabulary differs between producers so no single query spans the graph. |
| **3** | **100%** of edges carry a graded tier from one closed enum **and** a knowledge layer; the tier is a function of layer, never of confidence. |
| **4** | Level 3, plus 100% also carry an **evidence basis** and a **grade basis** — four-field self-description, no second lookup needed; evidence payloads **name the textual surface they quote**; and an independent evaluator verifies **≥95%** of a ≥1,000-row evidence sample verbatim against stored text. |
| **5** | Level 4, plus every source-explicit edge cites the source record or line it came from; `evidence_basis` is never `UNSPECIFIED` where a basis exists; `grade_basis` is a closed enum; and ≥95% of edges are independently re-verifiable using only code the repository exports. |

### Measured evidence

```cypher
MATCH ()-[r]->() RETURN sum(CASE WHEN r.quality_tier IS NOT NULL AND r.knowledge_layer IS NOT NULL
  AND r.evidence_basis IS NOT NULL AND r.grade_basis IS NOT NULL THEN 1 ELSE 0 END)
  AS fully_self_describing, count(*) AS total
```
→ **242,147 / 242,147 = 100.00%.** Every edge in this graph states its tier, its layer, the
kind of evidence it rests on, and the reason it was graded that way, without a join. That is
the clause that earns the 4 and it is not a common property of knowledge graphs.

Tier and layer map cleanly, with **no edge ungraded**:

| Layer | Tier | Edges |
| --- | --- | --- |
| `L1_SOURCE_EXPLICIT` | TIER_A | 91,163 |
| `L2_DETERMINISTIC_DERIVED` | TIER_B | 149,206 |
| `L4_INTERPRETIVE_CLAIM` | TIER_D | 1,042 |
| `L3_LLM_EXTRACTED` | TIER_D | 736 |

`evidence_basis`: STRUCTURAL 85,650 · UNSPECIFIED 61,861 · SANSKRIT 60,375 · TRANSLATION
21,246 · MIXED 13,015. Evidence payload on 106,029 edges (43.79%).

**Independent verbatim verification — my own, not carried.** I sampled 2,500 mention edges
whose passage carries a Latin-script `TextVersion`, folded every text token with the
repository's own `vedagraph.enrich.concepts.fold_alias`, and checked each edge's
`matched_aliases` against the folded token set:

| Veda | Grounded | Sample | Rate |
| --- | --- | --- | --- |
| AV | 778 | 778 | **100.00%** |
| RV | 1,719 | 1,722 | **99.83%** |
| **Total** | **2,497** | **2,500** | **99.88%** |

The three misses are private-use-codepoint tokenisation residue (`kṇvanto` for
`kṛṇvanto`) — the avagraha/accent residual already on the V1 backlog, not a false assertion.

That check was only possible because the evidence records **name their own surface**. My first
attempt compared quotes against raw `text_nfc` and returned 20.4%, which looked like a
catastrophic defect and was my error: the evidence says `"surface":"script_folded"`, and
applying the stated folding moves it to 99.88%. An evidence envelope that tells an auditor
which normalisation to apply is a real design win and is why level 4 names that clause.

### Score 4 — why not 5

Three level-5 clauses fail, each measured.

**TIER_A cites almost nothing.** Evidence coverage by tier:

| Tier | Edges | With evidence | % |
| --- | --- | --- | --- |
| TIER_A | 91,163 | **119** | **0.13%** |
| TIER_B | 149,206 | 105,174 | 70.49% |
| TIER_D | 1,778 | 736 | 41.40% |

The most-trusted tier is the least-evidenced. Much of TIER_A is structural containment where
"the evidence is the edition", but the attribution layer is not: all 31,646
`HAS_DEVATA` / `HAS_RISHI` / `HAS_CHANDAS` edges carry `evidence_basis = UNSPECIFIED` and no
evidence payload, so no query can show the Anukramaṇī line that produced a deity attribution.
`UNSPECIFIED` covers **61,861 edges (25.5%)**.

**`grade_basis` is prose, not a vocabulary.** `count(DISTINCT r.grade_basis)` = **32**,
mixing machine-parseable (`provenance_class=SOURCE_EXPLICIT, scope_origin=SINGLE_MANTRA`,
1,014 edges) with English sentences (`corpus structure as printed by the edition`, 84,096
edges). It explains to a human and cannot be filtered on. Relatedly `provenance_class` is
null on 192,176 edges (79.4%) and `state` is null on 136,118 (56.2%).

**16.0% of the mention layer is not independently verifiable with exported code.**
4,576 mention edges — every SV (2,333) and YV (2,243) edge — sit on passages with **no
Latin-script `TextVersion`**. Their aliases are IAST; their texts are Devanagari-only; and
`fold_alias` does not transliterate Devanagari, so an outside evaluator using the repository's
own exported folding cannot check them. Spot inspection shows the assertions are correct
(`इन्दवो` really is `indavo`), so this is an auditability gap, not an accuracy one — but
level 5 asks for auditability.

### Remediation

1. Attach the Anukramaṇī line as evidence on the 31,646 attribution edges and set their
   `evidence_basis`. That single change removes half the `UNSPECIFIED` population and raises
   TIER_A evidence coverage from 0.13% to ~35%.
2. Make `grade_basis` a closed enum with the prose moved to a `grade_note`.
3. Export a Devanagari→IAST folding path so SV and YV evidence is checkable by the same
   function that checks RV and AV.

---

## L. Interpretation-vs-fact separation — **4 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Interpretation and textual fact are indistinguishable. |
| **1** | A confidence number is the only signal separating them. |
| **2** | Interpretive assertions carry a distinct type but share a traversal with textual facts and carry no tier. |
| **3** | Interpretive assertions are a distinct node type on a distinct tier; model output carries a distinct state; a query can return **only** source-stated facts; repository self-audit is excluded from product traversal. |
| **4** | Level 3, plus **every** interpretive claim carries a falsifier and cites either a passage or a computed metric, **enforced at load**; ≥1 live contradiction is held without adjudication; container-inherited attribution is marked and a **strict variant of every counting query exists**. |
| **5** | Level 4, plus a **populated** reviewed-model tier (TIER_C) validated against a human gold set, and ≥1 interpretive claim attributed to a named external commentator. |

### Measured evidence

Level 4 passes in every clause, measured:

| Clause | Measured |
| --- | --- |
| Distinct node type on a distinct tier | 6 `InterpretiveClaim`, **6/6 `TIER_D`** |
| Falsifier on every claim | **6/6** carry a non-null `falsifier` |
| Evidence on every claim | 2 with passage evidence (7 `SUPPORTED_BY`), 6 with metric evidence (6 `SUPPORTED_BY_STATISTIC`); `load_claims` refuses a claim citing neither |
| Live unadjudicated contradiction | 1 `CONTRADICTS` pair (2 edges), neither marked as winning |
| Model output distinctly stated | 736 edges, **all** `state = CANDIDATE`, all TIER_D |
| Claims never masquerade as facts | `MATCH (p:Passage)-[r]->(c:InterpretiveClaim)` → **0 rows** |
| Self-audit excluded | 915 `QAIssue`, **all** `:Internal`, **0** in product traversal |
| Container inheritance marked | 100% of edges carry `attribution_precision`: PER_PASSAGE 217,449 / CONTAINER_INHERITED 24,698 |
| Strict variant available | `rishis_invoking_deity` 15 rows vs `rishis_invoking_deity_strict` **4 rows**, both catalogued, both caveated |

The inheritance figures are the honest ones and they are exposed rather than hidden:
`HAS_DEVATA` 78.9% inherited, `HAS_RISHI` **95.5%** inherited, `HAS_CHANDAS` 59.6%.

### Score 4 — why not 5

Both level-5 clauses fail, and each is a single measured zero.

**`TIER_C` = 0.** `MATCH ()-[r]->() WHERE r.quality_tier='TIER_C' RETURN count(*)` → **0**.
The graph contains no accepted model-derived knowledge at all, because there is no human gold
set to accept anything against (§O, §P). This is the same blocker as O, P and H.

**`ASSERTED_BY` = 0.** No claim is attributed to a named external commentator; the manifest
records `claims.with_external_source: 0`. All six claims are this project's own
`MODEL_SYNTHESIS` (4) or `RESEARCH_HYPOTHESIS` (2). So the interpretive layer is airtight and
self-referential — it separates *this project's* readings from text, and has no mechanism
carrying Sāyaṇa, Geldner or Jamison as a distinguishable voice.

One residual worth naming although it does not change the score: **75 of 79 `DerivedMetric`
nodes are cited by no claim** (`MATCH (m:DerivedMetric) WHERE NOT (m)<-[:SUPPORTED_BY_STATISTIC]-()`
→ 75). The metrics layer is 95% unconsumed by the layer it exists to support.

### Remediation

1. Annotate a gold set, review the 736 candidates, and create the graph's first `TIER_C`
   edges. That single act moves L to 5, O and P off the floor, and H's ceiling upward.
2. Add ≥1 externally attributed claim through `ASSERTED_BY` onto a `Source` node — the
   predicate and signature already exist.
3. Either wire the 75 orphan metrics into claims or mark them as standalone measurements.

---

## M. Query answerability — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No query catalogue; ad-hoc Cypher only. |
| **1** | A catalogue exists but ≥25% of its queries error or return zero rows unintentionally. |
| **2** | Catalogue runs clean; <8% of a named ≥50-question set fully answerable. |
| **3** | Catalogue runs clean; **every** query carries a mandatory caveat; ≥8% of the named question set fully answerable and ≥80% at least partially; 0 regressions against the previous pass. |
| **4** | ≥40% fully answerable, verified by an evaluator who did not build the graph, **and** the misleading-answer state explicitly assessed with 0 questions in it. |
| **5** | ≥80% fully answerable, each with a measured precision on the answer. |

### Measured evidence

I executed all 48 catalogued queries with their declared default parameters:

| Metric | Measured |
| --- | --- |
| Executed without error | **48 / 48** |
| Carrying a caveat | **48 / 48** (shortest 22 chars, longest 541) |
| Returning 0 rows | 4 — of which **3 are pass-condition invariant checks** (`internal_leakage_check`, `orphan_domain_entities`, `unlabelled_product_nodes`) and 1 is a genuine empty (`rivers_and_tribes`) |
| Questions with ≥1 serving query | **49 / 50** (question 37 unserved) |

The carried verdict is 4 FULLY (8%) / 41 PARTIAL (82%) / 5 NOT, with 0 regressions. I
re-probed a stratified sample of 12 questions independently:

| Q | V2 verdict | My probe | Verdict |
| --- | --- | --- | --- |
| 6 SV reuse of RV | FULLY | 1,662/1,844 SV mantras (90.1%), similarity-scored, evidence-bearing | **confirmed FULLY** |
| 29 textual vs interpretive | FULLY | 100% four-field self-description over 242,147 edges | **confirmed FULLY** |
| 50 evidence-backed transformations | FULLY | all 6 Veda pairs, mean similarity 0.90–0.94, per-edge metrics | **confirmed FULLY** |
| 8 cross-Veda formulas | FULLY | 3,643 cross-Veda, but 1,557 of them 2-token; 8 of top-12 four-Veda "formulas" are 2 words | **FULLY with a precision hazard** |
| 1 Indra across four Vedas | NOT | 0 Indra `DomainEntity`; all Indra edges RV-only | **confirmed NOT** |
| 2 ṛṣi families and Agni | PARTIAL | `RishiFamily` = **0 nodes**, `BELONGS_TO_FAMILY` = 0 | **I would say NOT** |
| 39 ritual dependency structure | NOT | `HAS_STEP` = 0, 4 rites, 35 apparatus edges | **confirmed NOT** |
| 42 epithets in context | NOT | 13 `Epithet` nodes, **0** passage links | **confirmed NOT** |
| 43 Rudra by Veda | NOT | RUDRAH 38 mantras, RV only; 0 non-RV rows | **confirmed NOT** |
| 23 deity communities | PARTIAL | **4 distinct deity pairs** co-occur on a mantra; `CO_OCCURS_WITH` = 0 | **I would say NOT** |
| 24 / 36 corpus layer & drift | PARTIAL | **0 nodes carry `stratum`, `period` or `chronology`**; only maṇḍala number available | **PARTIAL, generously** |
| 37 central bridges | PARTIAL | **0 nodes carry `pagerank`, `betweenness` or `centrality`**; also the one unserved question | **I would say NOT** |

My independent sample therefore agrees with V2 on the four FULLY and on three of five NOT,
and would move three PARTIALs down. It found **no** question V2 under-rated. So the carried
8% FULLY is if anything generous, and the true figure is 4/50 with three borderline partials.

### Score 3 — why not 4

Level 3 passes in every clause: clean catalogue, 100% caveat coverage, 8% ≥ 8%, 82% ≥ 80%,
0 regressions. Level 4 fails on the headline — **8% against a required 40%** — and on its
second clause: **the misleading-answer state is still not assessed as a state.** V2's own
report records this omission. My probes found two concrete misleading surfaces that a
misleading-state assessment would have caught: the `Work` node calling an ārcika-only corpus
"Samaveda Samhita" (§A), and 3,896 known-ambiguous mention edges carrying the same TIER_B
that a consumer is trained to trust (§C).

### What prevents 4

The four ranked blockers are unchanged and the top two are acquisitions, not modelling:
Rigveda-only attribution (19 questions), sūkta-scoped rather than per-verse attribution (16),
unmeasured mention recall with two rival concept layers (14), and no agentive layer (12).

### Remediation

1. Add MISLEADING as a fourth verdict state and re-run the fifty, so the metric can register
   the difference between "cannot answer" and "answers wrongly".
2. Serve question 37 (add a centrality query, or state that it needs GDS).
3. `PROTECTS_FROM` currently reaches only 5 `Condition` targets (witchcraft 65, poison 63,
   evil dream 22, ill-named beings 17, seizure 15) while `SATRU-ENEMY`, `RAKSAS-DEMON`,
   `SAPATNA-RIVAL-OVERCOMING` and `ENAS-SIN` **all exist as entities with no protection edge
   reaching them**. Question 16 — the closest single miss in the whole set — is now blocked
   only by writing that edge, because V2 already created its endpoints.

---

## N. Explainability — **4 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Ids only; nothing renderable to a reader. |
| **1** | <75% of product nodes carry a display label. |
| **2** | ≥95% display coverage, but an edge cannot explain its own grade without a second lookup. |
| **3** | **100%** of product nodes carry a non-sentinel display label **and** display type; 100% of edges carry tier and layer; every catalogued query carries a caveat. |
| **4** | Level 3, plus 100% of edges self-describe in four fields; every entity important enough to have a page carries a description; **the reason** a grade was assigned is on the edge; and the caveat is contractually part of the response rather than documentation. |
| **5** | Level 4, plus every assertion renders a human-readable justification a non-specialist can read, and the display layer is tested against a real consumer. |

### Measured evidence

```cypher
MATCH (n) WHERE NOT n:Internal RETURN count(*) AS product_nodes,
  sum(CASE WHEN n.display_label IS NULL OR n.display_label='' THEN 1 ELSE 0 END) AS no_label,
  sum(CASE WHEN n.display_type IS NULL THEN 1 ELSE 0 END) AS no_type
```
→ **38,297 / 0 / 0.** `UNKNOWN_LABEL_RATE = 0.0000%`, against 59.16% in V1, and no value
falls in `NULL_LABEL_SENTINELS`. All 377 `DomainEntity` + `Devata` nodes carry a
`short_description`. All 242,147 edges carry tier, layer, evidence basis and grade basis. All
48 queries carry a caveat, and the design instruction that "the caveats are not documentation,
they are part of the response" is recorded as a contract on the query object rather than in
prose. `grade_basis` states the actual reason — e.g.
`provenance_class=SOURCE_DERIVED_SCOPE, scope_origin=SUKTA_WIDE` on 24,698 edges, so an
inherited deity attribution explains its own inheritance in situ.

### Score 4 — why not 5

Both level-5 clauses fail, and one measured defect makes the display layer misleading.

**There is no consumer to test against.** `find src -iname '*api*'` returns the Typer CLI and
one ingest adapter; there is no FastAPI, no HTTP surface, no UI. The display contract is
correct by construction and untested by use.

**9,992 product nodes are isolated and still render.**
```cypher
MATCH (n) WHERE NOT n:Internal WITH n, size([(n)--() | 1]) AS d
RETURN sum(CASE WHEN d=0 THEN 1 ELSE 0 END) AS isolated, count(*) AS product_nodes
```
→ **9,992 isolated of 38,297 (26.1%)** — the `Lemma` layer, of which only **39 of 10,031** are
connected to anything (`MATCH (l:Lemma) WHERE (l)--() RETURN count(*)` → 39). Every one carries
a `display_label` and a `display_type`, so a label census, an autocomplete or an entity browser
built on the display contract would surface 9,992 dead ends as first-class Vedic entities.

**322 of 367 ṛṣi labels are not reader-grade.** They are bundled Anukramaṇī citation strings
(`agastyāntevāsī brahmacārī`, `aindraḥ prājapatyaḥ`, `agnivaruṇasomāḥ`). They satisfy the
letter of the display contract and fail its purpose.

**`grade_basis` is 32 free-text values.** Excellent for a human reader; not machine-checkable,
so an interface cannot group or localise the explanation.

### Remediation

1. Either connect the `Lemma` layer to the mention/entity layer or mark it `:Internal`. It is
   currently the single largest population in the product graph after `Passage`/`Mantra` and
   contributes nothing a traversal can reach.
2. Split the bundled ṛṣi labels (shared fix with C and G).
3. Build the API and let a real consumer exercise the display and caveat contract, which is
   already the declared next project phase.

---

## O. Semantic precision — **1 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No notion of precision anywhere: no flag, no score, no gold set, and known-bad assertions indistinguishable from good ones. |
| **1** | Precision is **unmeasured**. No human-adjudicated sample of any assertion layer exists, so no precision figure can be quoted. Hazards may be flagged by rule, but the flag has never been calibrated against adjudicated truth. |
| **2** | Precision measured on ≥1 assertion layer by a **≥100-item human-adjudicated sample**, reported with its denominator and a per-predicate or per-alias breakdown. |
| **3** | Precision measured per assertion layer, ≥0.85 on the mention layer and ≥0.85 on the concept layer, per-alias for the top-20 highest-volume aliases, adjudicated sample ≥500. |
| **4** | ≥0.90 on every populated layer, measured per alias and per predicate, inter-annotator agreement reported, and sub-threshold edges **retired or downgraded** rather than merely flagged. |
| **5** | ≥0.95 on every layer, with a standing regression suite that fails a build on drift. |

### Measured evidence

**The finding is the absence.**

```
wc -l data/gold/rigveda_semantic_gold_v1.jsonl  →  120
```
```python
collections.Counter(annotator) → {'UNANNOTATED': 120}   entities=0   relations=0
```

All 120 gold rows carry `annotator: "UNANNOTATED"`, `annotated_at: "1970-01-01T00:00:00Z"`,
and empty `entities` and `relations` arrays. The scaffolding is complete and correct — five
JSON schemas (`semantic_gold_annotation`, `_adjudication`, `_entity_annotation`,
`_evidence_reference`, `_review_metadata`), a protocol document, a reviewer guide and a
worksheet — and **not one item has been annotated by a human.** Every build file records
`human_gold_status: UNANNOTATED`.

`data/domain/vedagraph_domain_v2/manifest.json` contains no precision figure. The
`by_precision` key there is `attribution_precision` — a scope descriptor (PER_PASSAGE vs
CONTAINER_INHERITED), not a measurement.

What the graph has instead is a **rule**, not a measurement: `theonym_ambiguous`, set where an
alias that fired is also a deity's name. It marks 3,896 of 28,675 mention edges (13.59%),
with per-entity rates up to 57.5% (`AGNI-FIRE`). That is a genuinely valuable hazard flag and
it is not precision: it says "this alias is morphologically ambiguous", not "this assertion
is wrong". All 3,896 remain `TIER_B / ACCEPTED`.

My own independent 2,500-row check (§K) measured **99.88% alias grounding** — that the alias
really occurs in the cited text. That is a strictly weaker property than precision and the
distinction is load-bearing: `agne` is perfectly grounded in RV 1.1.1 and still means the
*god*, not *fire*. V2's own translation adjudication over 1,934 rows put `AGNI-FIRE`'s error
at **80.9%**, and V2 also recorded that an automated gloss screen scored the same alias at
**97.5% correct** — a 78-point gap between two automated proxies for the same quantity, which
is the sharpest possible demonstration that proxies cannot substitute for adjudication here.

### Score 1 — why not 0, why not 2

**Not 0** because the graph is not naive about precision: the hazard is named, per-entity
rates are computed and published, `evidence_basis` separates Sanskrit-grounded from
translation-grounded assertions, and 43.79% of edges carry a checkable evidence payload. The
machinery for measurement is in place.

**Not 2, and cannot be**, because level 2's minimum is a ≥100-item human-adjudicated sample
and the adjudicated sample size is **zero**. No arrangement of the existing artifacts produces
a precision number. This is the rule the brief states and it is also simply true: a graph that
cannot say how often it is right does not get credit for being right.

### What prevents 2

One artifact: 100+ human-annotated gold items. Everything else — schemas, protocol, reviewer
guide, worksheet, the 120-row frame, the sealed 448-mantra candidate set to score against —
already exists.

### Remediation

1. Annotate ≥300 passages exhaustively (entities and relations) against the existing schemas.
   Prioritise the 448 mantras of the sealed artifact so the annotation scores a real candidate
   set rather than an abstraction.
2. Measure per-alias precision for the top-20 highest-volume aliases first — `agne`, at 915
   edges and near-total error, is the documented proof that volume × error ranking is the
   right prioritisation.
3. Then **act** on the measurement: retire or downgrade sub-threshold edges instead of
   flagging them. Flag-and-accept is what caps C at 3 as well.

---

## P. Semantic recall — **1 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No notion of coverage; no denominator stated anywhere. |
| **1** | Recall is **unmeasured**. No gold set enumerates what *should* have been found, so no recall figure exists. Coverage is reported as "share of units carrying ≥1 assertion", a proxy of unknown tightness. |
| **2** | Recall measured on ≥1 layer against a **≥100-passage exhaustively annotated** gold set. |
| **3** | Recall ≥0.70 per assertion layer against a ≥300-passage gold set, reported per Veda. |
| **4** | Recall ≥0.85 per layer per Veda, with a **named residual class** for every miss. |
| **5** | ≥0.95 per layer per Veda with a standing regression suite. |

### Measured evidence

Same empty gold file as §O. What exists is coverage, which is a numerator over a *corpus*
denominator rather than over a *truth* denominator:

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:DomainEntity) WITH p.veda AS v, count(DISTINCT p) AS covered
MATCH (m:Mantra) WHERE m.veda=v
RETURN v, covered, count(m) AS mantras, round(100.0*covered/count(m),1) AS pct ORDER BY v
```

| Veda | Mantras with ≥1 mention | Mantras | Coverage |
| --- | --- | --- | --- |
| RV | 8,375 | 10,552 | 79.4% |
| SV | 1,358 | 1,844 | 73.6% |
| AV | 4,167 | 5,839 | 71.4% |
| YV | 1,320 | 1,975 | 66.8% |

Corpus-wide: **6,258 of 22,537 passages (27.8%) carry no mention at all**; mean mention degree
over all passages **1.672**; 2,177 Rigvedic mantras have no entity mention. **27,780 of 28,675
edges (96.9%) rest on a single alias hit.** The registry is 163 entities against ~20,000
mantras.

The one internal cross-check available is the rival-layer comparison from §I, and it is the
most informative number on this dimension:

| Direction | Measured |
| --- | --- |
| `ABOUT_CONCEPT` links confirmed by a Sanskrit mention | **55.3%** |
| Mention links confirmed by `ABOUT_CONCEPT` | **98.7%** |

The mention layer is a near-subset of the concept layer. So **either** `ABOUT_CONCEPT` is
substantially right and the mention layer's recall on the 89 shared entities is around 55%,
**or** the mention layer is right and `ABOUT_CONCEPT`'s precision is around 55%. The graph
contains no evidence that decides which. Per entity the gap reaches 6.5× (`DANA-LIBERALITY`:
708 `ABOUT_CONCEPT` links, 109 mentions, 15.3% overlap).

### Score 1 — why not 0, why not 2

**Not 0** because coverage denominators are stated, per Veda, and the report that publishes
them explicitly caps every frequency, prominence and centrality claim at PARTIALLY on account
of unmeasured recall. Naming the limit is worth the point.

**Not 2** because level 2 needs an exhaustively annotated ≥100-passage gold set, and the
annotated count is zero. Coverage of 71–79% tells you how often the pipeline fired; it tells
you nothing about how often it should have. With mean degree 1.672 over a corpus whose verses
routinely name half a dozen entities, the proxy's looseness is likely large and is not
bounded.

### What prevents 2

The same single artifact as O. O and P are one unlock, not two.

### Remediation

1. Annotate 300 passages **exhaustively** — every entity and relation a reader would mark,
   not just confirmations of what the pipeline found. Exhaustiveness is what makes the set
   usable for recall; a confirmation-only set measures precision alone.
2. Stratify by Veda so recall is reportable per corpus; YV at 66.8% coverage is the likeliest
   worst case and the smallest to annotate.
3. Use the result to decide the `ABOUT_CONCEPT` question. That decision is currently blocking
   I, M, O, P and S simultaneously.

---

## Q. Graph coherence — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | No constraints; duplicate ids; contradictory assertions unflagged. |
| **1** | Uniqueness on some keys; orphans and predicate-signature violations unmeasured. |
| **2** | Uniqueness constraints on the main entity types; a build-time signature check exists but the **live** graph is not gated. |
| **3** | Uniqueness on every entity type; endpoint signatures enforced; **a live invariant suite that passes against the running database**; 0 duplicate ids; 0 unlabelled nodes; 0 self-loops; 0 contradictory pairs on the same predicate. |
| **4** | Level 3, plus ≤1% of product nodes isolated; **every** declared predicate either populated or documented as empty-by-design; **every** live predicate declared in the contract; symmetric predicates traversable in both directions or documented as directed. |
| **5** | Level 4, plus a machine-checked equivalence between contract and live graph that fails CI on drift, and every edge delta reconciled against a pinned baseline. |

### Measured evidence

Level 3 passes cleanly and with credit:

| Gate | Measured |
| --- | --- |
| Uniqueness constraints | **22**, covering every entity type incl. the empty ones |
| Indexes | 77 RANGE + 2 FULLTEXT + 2 LOOKUP |
| Duplicate `entity_key` | **0** |
| Unlabelled nodes | **0** |
| Self-loops | **0** |
| Orphan `DomainEntity` | **0** |
| Passages both `TREATS` and `PROTECTS_FROM` the same target | **0** |
| **Live invariant suite** | `VEDAGRAPH_LIVE_NEO4J=1 pytest tests/domain` → **52 passed**, incl. 9 live-Neo4j gates |

Determinism is proven upstream (two independent artifact builds producing byte-identical
`domain_mentions.jsonl` and `domain_registry.yaml`, sha256-pinned) and the loader MERGEs on
deterministic keys, so a rebuild converges.

### Score 3 — why not 4

**All four level-4 clauses fail.**

**26.1% of product nodes are isolated**, against a required ≤1%: 9,992 of 38,297, being the
`Lemma` layer (39 of 10,031 connected).

**15 of 35 declared predicates are empty; only 1 is documented as empty-by-design.**

| Declared and empty | | |
| --- | --- | --- |
| `ASSERTED_BY` | `ASSOCIATED_WITH_CONCEPT` | `ASSOCIATED_WITH_PHENOMENON` |
| `ASSOCIATED_WITH_SUBSTANCE` | `ASSOCIATED_WITH_TRIBE` | `BELONGS_TO_FAMILY` |
| `CO_OCCURS_WITH` | `DESCRIBED_IN` | `HAS_STEP` |
| `MUSICALIZED_AS` *(documented)* | `PERFORMS_ACTION` | `PERSONIFIES` |
| `RECEIVES_OFFERING` | `TEXTUALLY_REUSED_AS` | `WIELDS` |

**21 live predicate types are outside the V2 contract**, and two of those substitutions are
structurally significant rather than cosmetic: `DEVATA_ASSOCIATED_WITH` (140 edges, no
relation property) does the work of five declared-and-empty typed deity predicates; and five
undeclared reuse types (6,596 edges) do the work of the declared-and-empty
`TEXTUALLY_REUSED_AS`. So the contract and the graph disagree about how the graph's two most
substantive non-lexical layers are shaped. `SHARES_FORMULA_WITH` compounds this with four
indexes and zero edges. Three declared product labels — `Region`, `RishiFamily`, `Theme` —
have zero nodes while carrying constraints and indexes.

**No symmetric traversal.** 0 reciprocal `EXACT_PARALLEL_OF` and 0 reciprocal
`NEAR_PARALLEL_OF`; nothing documents the direction.

Three structural incompletenesses also sit here rather than under D, because they are
consistency failures against the graph's own declared structure: 24 of 38 `PAIR` deities
undecomposed, 30 of 33 `GROUP` deities memberless, and `INDRAVARUNAU` — attribution 70, every
sibling Indra-dual decomposed — with no `COMPOSED_OF` row.

### Remediation

1. Reconcile contract and graph in one pass: declare the 21 live types (or migrate them),
   split `DEVATA_ASSOCIATED_WITH` into its five typed successors, and either populate or
   document each of the 14 undocumented empty predicates.
2. Connect or internalise the `Lemma` layer — a single decision that takes isolation from
   26.1% to ~0.3%.
3. Add a test asserting `set(live relationship types) ⊆ contract ∪ documented-legacy` so the
   drift cannot recur, which is also most of level 5.

---

## R. Research usefulness — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Supports no question a researcher would ask. |
| **1** | Descriptive counts only; every result is already available from a printed concordance. |
| **2** | Counts plus ≥1 non-trivial cross-corpus join, but no result is stated with a falsifier or a quantified limit. |
| **3** | ≥3 distinct multi-hop research joins returning evidence-bearing results; **the graph states its own limits as queryable data** so a researcher can bound a claim; ≥1 recorded finding carries a falsifier. |
| **4** | ≥25 recorded findings with falsifiers and computed metrics; the limit is queryable per-edge **and** per-query; a researcher can measure a claim's sensitivity to layer choice; **and every Work's corpus scope is machine-readable.** |
| **5** | Level 4, plus the graph has produced a result a specialist would cite, with a reproducible query and an adjudicated evidence sample. |

### Measured evidence

Level 3 passes, and not thinly.

**Multi-hop joins return real results.** Measured:

| Join | Result |
| --- | --- |
| Cross-Veda parallel pairs that also share a domain entity | **6,450** |
| Entity pairs sharing ≥1 passage | **3,841** (521 with ≥10 shared, max 262) |
| Cross-Veda formulas | 3,643 (229 four-Veda) |
| SV mantras located in the RV | 1,662 (90.1% of SV) |
| Entities with ≥100 mentions | 74 |

**The graph states its own limits as data**, which is the clause that most distinguishes this
dimension from a search index. `attribution_precision` on 100% of edges means any deity or
ṛṣi ranking can be re-run strictly; measured, `rishis_invoking_deity` returns 15 rows and
`rishis_invoking_deity_strict` returns 4. `evidence_basis` means a researcher can exclude the
21,246 concept edges resting only on Griffith's English. 79 `DerivedMetric` nodes carry stored
values across 7 metric families, and at least one is a citable non-obvious result:
`DEVATA_ATTRIBUTION_PRECISION` for Indra reads
`{"container_inherited": 2214, "per_passage": 655, "per_passage_share": 0.2283}` — the
familiar "Indra has the most hymns" figure is 77% a scope rule, and the graph can prove it.
6 of 6 claims carry falsifiers.

The material distribution results from §F are of the same kind: barley in all four Vedas,
rice and sesame in the Atharvaveda alone, on probed and read alias sets.

### Score 3 — why not 4

**Only 6 recorded findings, against 25.** And 75 of 79 metrics are cited by no claim, so the
computed evidence base is 95% unconsumed.

**No Work's corpus scope is machine-readable** (§A). A researcher who queries this graph for
Sāmavedic distribution will get numbers over the ārcika and will find nothing in the graph
telling them the gāna books — a larger body — are absent. That is the highest-consequence
research hazard in the graph and it is one property write away from fixed.

**No sensitivity-to-layer analysis is possible for the concept layer** because the two rival
layers are not reconciled (§I): a prominence claim has two answers 45 points apart and no way
to choose.

**No diachronic axis exists.** `MATCH (n) WHERE n.stratum IS NOT NULL OR n.period IS NOT NULL
OR n.chronology IS NOT NULL` → **0**, with all three keys reported non-existent. Only the
maṇḍala number is available, so the family-books question and every "increases over time"
question is out of reach by construction.

And the graph's best semantic asset is not in it: the sealed 448-mantra Rigvedic artifact,
2,459 assertions at 0 integrity failures, verified absent by `run_id` probe (§H).

### Remediation

1. Write scope, rights and completeness onto the four `Work` nodes.
2. Grow the claim layer to ≥25 falsifiable findings, wiring in the 75 orphan metrics.
3. Project the sealed 448 artifact.
4. Add a coarse stratigraphic property (family books vs maṇḍala 1/8/9/10; AV kāṇḍa groups)
   even as an explicitly TIER_D scholarly convention — flagged as interpretation, which this
   graph is unusually well equipped to do.

---

## S. Discovery potential — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | A flat index; no structure to traverse. |
| **1** | One assertion layer; no join produces a fact absent from either input. |
| **2** | ≥2 joinable layers, but hub concentration or sparsity leaves most joins empty; <1,000 non-trivial 2-hop results. |
| **3** | ≥4 joinable layers (attribution, mention, formula, parallel); ≥1,000 non-trivial 2-hop results; ≥1 candidate-generator query existing **and labelled as such**; top-10 node share of the densest layer <50%. |
| **4** | Level 3, plus ≥1 **role-bearing** predicate spanning all four Vedas; a **stored** graph-analytic measure (centrality or community) so structural questions do not need a fresh analytics run; and a diachronic or stratigraphic axis. |
| **5** | Level 4, plus an embedding or similarity space over passages enabling retrieval of unlabelled analogues, evaluated against a gold set. |

### Measured evidence

Level 3 passes on every clause.

Four joinable layers: attribution (`HAS_DEVATA`/`HAS_RISHI`/`HAS_CHANDAS`, 31,646), mention
(`MENTIONS_ENTITY`, 37,675), formula (`USES_FORMULA`, 22,686), parallel (5 types, 6,596).
2-hop yield measured at **6,450** cross-Veda parallel pairs sharing an entity and **3,841**
entity co-occurrence pairs — comfortably over 1,000. `conceptually_similar_not_reused` exists,
returns 25 rows in 8,758 ms, and is **explicitly documented as a candidate-generator, not a
finding** — an unusual and correct piece of discipline. Hub concentration:

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e) WITH e, count(*) AS deg ORDER BY deg DESC
WITH collect(deg) AS degs RETURN round(100.0*reduce(s=0,d IN degs[0..10]|s+d)/reduce(s=0,d IN degs|s+d),1)
```
→ top 10 entities hold 12,953 of 37,675 edges = **34.4%**, under the 50% bar.

### Score 3 — why not 4

All three level-4 clauses fail, each with a measured zero.

**No role-bearing four-Veda predicate.** The only predicate spanning four Vedas is
`MENTIONS_ENTITY`, which carries no role (§H: 0 edges with an actor slot anywhere).

**No stored graph analytics.** `MATCH (n) WHERE n.pagerank IS NOT NULL OR n.betweenness IS NOT
NULL OR n.centrality IS NOT NULL` → **0**, all three keys non-existent. So question 37 —
central bridging mantras — needs a fresh GDS projection every time and is also the one
question with no serving query.

**No diachronic axis** (§R): 0 nodes with `stratum`, `period` or `chronology`.

Two measured facts make the discovery surface thinner than the layer count suggests.
**Deity community structure is effectively absent**: `CO_OCCURS_WITH` is 0, and only **4
distinct deity pairs** co-occur on the same mantra via `HAS_DEVATA` (6 pair instances total),
because the Anukramaṇī names essentially one deity per verse. Community detection over
deities has almost nothing to detect. And **26.1% of product nodes are isolated**, so any
random-walk, similarity or embedding method over the product graph samples dead ends at that
rate.

### Remediation

1. Project the sealed 448 artifact for the role-bearing layer, and extend it to four Vedas.
2. Materialise centrality and community properties from a GDS run and version them as
   `DerivedMetric`-style derived data with a stated method.
3. Build deity co-occurrence from the **mention** layer rather than the attribution layer,
   where 40 deities and 9,000 edges give real co-occurrence structure — and populate
   `CO_OCCURS_WITH`, which is declared and empty.
4. Connect or internalise the `Lemma` layer before any embedding work; 10,031 nominal stems
   and 702 roots joined to the entity layer would be a substantial discovery surface in itself
   and are currently inert.

---

## T. Product usability — **3 / 5**

### Rubric

| Level | Operational definition |
| --- | --- |
| **0** | Raw database; no separation of engineering from knowledge; no named queries. |
| **1** | Named queries exist, but engineering or QA artifacts appear as peers of knowledge nodes in normal traversal. |
| **2** | An internal/product boundary exists but is repeated per query; latency or unintended-empty rate makes an interface impractical. |
| **3** | The boundary is written **once** and enforced; 0 diagnostic nodes in product traversal; ≥90% of catalogued queries under 200 ms with a stated median; every query names the caveat a consumer must surface; rebuild is deterministic. |
| **4** | Level 3, plus a **served interface** over the catalogue that returns the caveat with the payload; every corpus's scope machine-readable at the `Work` node; no query over 1 s without being labelled a batch job; and the product graph free of isolated nodes (≤1%). |
| **5** | Level 4, plus measured real-consumer usage driving the catalogue, and pagination, auth and versioning on the served surface. |

### Measured evidence

Level 3 passes in every clause.

`PRODUCT_NODE_FILTER` and `product_filter(variable)` are defined once in
`src/vedagraph/domain/ontology.py` and interpolated by the catalogue, rather than
`WHERE NOT n:QAIssue` being repeated 48 times. 915 `QAIssue` nodes all carry `:Internal` and
`internal_leakage_check` returns **0 rows** (its pass condition). 62,483 Internal nodes marked.

Latency, measured across all 48 named queries with their declared parameters:

| Metric | Value |
| --- | --- |
| Median | **5.75 ms** |
| Mean | 200.2 ms |
| p95 | 78.7 ms |
| Under 200 ms | **46 / 48** |
| Over 1 s | **1** (8,758 ms — the labelled candidate-generator) |
| Errors | **0 / 48** |
| Carrying a caveat | **48 / 48** |

Rebuild determinism is proven byte-for-byte upstream and the loader MERGEs on deterministic
keys.

### Score 3 — why not 4

All four level-4 clauses fail.

**There is no served interface.** No FastAPI in `src/` or `pyproject.toml`; the only
`*app*`/`*api*` files are the Typer CLI and an ingest adapter. The API is the declared next
project phase, which is a correct plan and does not earn the point today.

**No `Work` carries its scope** (§A) — the highest-impact usability defect in the graph,
because the string a UI would render is `Samaveda Samhita` for a corpus its own manifest
forbids that name.

**9,992 isolated product nodes (26.1%)**, against a ≤1% bar.

**One catalogued query runs 8.76 s.** It is labelled a candidate-generator, which is why this
is a level-4 clause and not a level-3 failure, but it sits in the same catalogue an API would
expose and needs an explicit batch designation.

One nuance worth recording for whoever builds the API, because it is easy to misread the
"0 leakage" result:

```cypher
MATCH (n:Internal) WHERE (n)<-[]-(:Passage) RETURN count(*)
```
→ **61,559.** The internal/product separation is **query-side, not structural**. It is
correct, it is written once, it is gated by live tests, and it holds for every catalogued
query. But an unfiltered one-hop traversal from any passage returns 61,559 `TextVersion` and
`Translation` nodes. Any consumer that writes its own Cypher and forgets `product_filter` gets
plumbing back as knowledge. The mitigation is to serve the catalogue rather than the database.

### Remediation

1. Build the API over the 48 catalogued queries, returning `caveat` as a required response
   field rather than documentation. The V2 report's instruction on this point is correct and
   should be a schema constraint, not a note.
2. Write scope/rights/completeness onto the four `Work` nodes.
3. Connect or internalise the `Lemma` layer.
4. Mark the 8.76 s query as `batch: true` in the catalogue so an endpoint cannot expose it
   synchronously; add a serving query for question 37.

---

# Scores

| | Dimension | Score | One-line reason |
| --- | --- | :---: | --- |
| **A** | Corpus coverage | **3** | Four Vedas at 97.7–100% of one recension each, gaps enumerated; no second recension, no post-saṃhitā layer, `Work` scope not machine-readable |
| **B** | Cross-Veda balance | **2** | Density ratio 2.13× passes, but 5 corpus-general predicate families are 100% Rigvedic and SV has 0 translations |
| **C** | Entity resolution | **3** | Constraints, probed aliases, 13.59% ambiguity measured per entity; but all 3,896 flagged edges stay TIER_B/ACCEPTED and 5 major theonyms have no entity |
| **D** | Devatā knowledge depth | **3** | 214/214 labelled and top-20 classified; 47.2% UNSPECIFIED, 24 pairs undecomposed, 30 groups memberless, 0 deities with two-Veda presence |
| **E** | Ritual knowledge depth | **1** | 4 rites, 35 apparatus edges, `HAS_STEP` = 0, `DESCRIBED_IN` = 0, over a corpus containing the whole Vājasaneyi Saṃhitā |
| **F** | Material-culture depth | **3** | 56 entities, 87.5% reaching ≥2 Vedas, aliases read and rejections recorded; no lateral material relations, no per-entity precision |
| **G** | Human/social knowledge depth | **2** | 367 attributed ṛṣis and 18 social entities; `RishiFamily` = 0 nodes, both social-structure predicates = 0 |
| **H** | Agentive/action semantics | **1** | **0 edges anywhere carry an actor, agent or patient slot**; 0 verb lemmas; the 554-EVENT sealed artifact is not projected |
| **I** | Concept ontology quality | **3** | 100% definitions, enforced type enum; hierarchy depth 2 at 43.6%, 163 entities, and two rival layers disagreeing by 45 points |
| **J** | Textual reuse / formula quality | **3** | 5 reuse predicates, all 6 Veda pairs, 90.1% SV reuse located; declared predicate empty, `match_level` 70% blank, 41% of formulas are 2 tokens |
| **K** | Evidence / provenance quality | **4** | **100% four-field self-description over 242,147 edges** and **99.88% independently verified verbatim**; TIER_A cites 0.13%, `grade_basis` is 32 prose values |
| **L** | Interpretation-vs-fact separation | **4** | Every level-4 clause met — falsifiers, enforced evidence, a live unadjudicated contradiction, strict query variants; TIER_C = 0 and `ASSERTED_BY` = 0 |
| **M** | Query answerability | **3** | 48/48 clean, 48/48 caveated, 0 regressions; 8% fully answerable against 40%, and MISLEADING still unassessed as a state |
| **N** | Explainability | **4** | 0 unlabelled product nodes, 100% self-describing edges, caveat as contract; no consumer to test against and 9,992 isolated nodes still render |
| **O** | Semantic precision | **1** | **Unmeasured.** 120 gold rows, all `UNANNOTATED`, 0 entities, 0 relations. The flag is a rule, not a calibration |
| **P** | Semantic recall | **1** | **Unmeasured.** Same empty gold set. Coverage 66.8–79.4% is a proxy; the rival layer bounds it at ~55% or accuses itself |
| **Q** | Graph coherence | **3** | 22 constraints, 52/52 live invariant tests pass, 0 duplicates/self-loops; 26.1% isolated, 15 empty declared predicates, 21 undeclared live ones |
| **R** | Research usefulness | **3** | 6,450 evidence-bearing multi-hop results, limits queryable per edge, 6 falsifiable findings; 25 required, no `Work` scope, no diachronic axis |
| **S** | Discovery potential | **3** | 4 joinable layers, 34.4% hub share, a labelled candidate-generator; 0 stored centrality, 0 chronology, 4 deity pairs, no role-bearing predicate |
| **T** | Product usability | **3** | Boundary written once, 0 leakage, median 5.75 ms, 48/48 caveated, deterministic; no served interface, no `Work` scope, 26.1% isolated |

### **TOTAL: 53 / 100**

Distribution: three 4s (K, L, N) · eleven 3s · two 2s (B, G) · four 1s (E, H, O, P).
Median 3. Mean 2.65.

The shape is coherent and worth stating plainly: **this graph is strong at saying what it
knows and how it knows it, and weak at knowing things.** The three 4s are all
meta-dimensions — provenance, interpretation separation, explainability. The four 1s are all
substance: what people did (H), what rites they performed (E), and whether any of the graph's
assertions are right (O) or complete (P). That is not a criticism of the V2 pass, which set
out to fix reliability and did; it is the input to V3, which has to add knowledge.

---

# RUBRIC FROZEN

*Restated compactly. This block is sufficient on its own: the final evaluator can apply these
twenty scales to the V3 graph without reading anything above. Thresholds are inclusive.
"Declared-but-empty scores as empty" and "unmeasured cannot exceed 1" are binding.*

**A. Corpus coverage** — 0 none/pilots · 1 one Veda verse-keyed · 2 two–three Vedas, or four with any below 80% of its recension's attested verse count, or gaps not enumerated · 3 four Vedas, one recension each, each ≥95%, canonical citations on all, every shortfall enumerated with a cause · 4 +≥1 second recension or post-saṃhitā layer, and scope machine-readable on the `Work` node · 5 +≥2 recensions for ≥2 Vedas or the gāna corpus, and translations for ≥95% of every Veda.

**B. Cross-Veda balance** — 0 one Veda only · 1 >90% of knowledge edges on one Veda · 2 all four present but ≥3 corpus-general predicate families single-Veda, or per-mantra density ratio >3× · 3 ratio ≤3×, ≤2 single-Veda families, every Veda has translations · 4 ratio ≤2×, every corpus-general family in all four Vedas, top-20 deities each present in ≥2 Vedas · 5 ratio ≤1.5×, every family within ±25% of corpus mean.

**C. Entity resolution** — 0 surface strings · 1 entities, no aliases, no ambiguity marking · 2 aliases + ids but ambiguity unmarked or a conflation class unmeasured · 3 constrained unique ids, corpus-probed aliases with rejections recorded, per-edge ambiguity flag with measured overall and per-entity rates, 0 duplicates, 0 orphans · 4 +the flag changes tier or state (a `quality_tier` filter alone excludes known-ambiguous edges), +adjudicated precision for the top-20 aliases, +every top-20 deity resolvable as a mention entity · 5 +every flagged edge adjudicated, +inflection measured against a morphological analyser.

**D. Devatā knowledge depth** — 0 none · 1 names only · 2 single-valued type ≥50% unknown · 3 all deities carry a structural fact and a multi-valued role vocabulary, ≥50% non-unspecified, top-20 all classified, identity relations populated for some · 4 ≥80% non-unspecified, every PAIR decomposed and every GROUP with members, top-20 each with ≥3 outbound relation types besides `HAS_AXIS`, top-20 each present in ≥2 Vedas · 5 +per-Veda or per-maṇḍala role profiles, +every epithet reachable from ≥1 passage.

**E. Ritual knowledge depth** — 0 no ritual entity · 1 <5 rites, **or** no step/sequence structure at all · 2 5–9 rites with ≥3 apparatus edges each and ≥1 ordered sequence · 3 ≥10 rites with ≥3 apparatus edges each, ≥3 with ordered sequences, each linked to describing passages by a dedicated predicate (not lexical co-occurrence) · 4 ≥25 rites, ordered steps on ≥10, description predicate on every rite, purposes distinct from outcomes, measured per-rite passage recall · 5 +rite variants across recensions, +Śrauta/Gṛhya distinction as data.

**F. Material-culture depth** — 0 none · 1 <20 material entities or no per-Veda distribution · 2 20–49 with probed aliases and per-Veda counts · 3 50–99, ≥80% reaching ≥2 Vedas, aliases read against the text with rejections recorded, sublabels implying superlabels · 4 ≥150, ≥90% with ≥5 mentions, adjudicated per-entity precision on a sample, material entities related to each other (made-of/part-of/used-in) · 5 ≥300 with a materials-and-technology sub-ontology, cross-Veda distribution tested for significance.

**G. Human/social knowledge depth** — 0 none · 1 ṛṣi names opaque with no verse attribution, or 0 social entities · 2 ṛṣis attributed + 10–24 social entities, family layer absent or declared-and-empty · 3 populated ṛṣi family layer joined to ṛṣis, ≥25 social entities, ≥3 populated social-structure predicates · 4 family and tribe layers joined to passages, ≥100 social entities, occupational vocabulary measured, per-Veda social distribution · 5 +genealogy, +patron/dānastuti layer with passage evidence.

**H. Agentive/action semantics** — 0 no action or event representation · 1 action **nouns** reachable only by mention/co-occurrence; **no assertion carries an agent role slot** · 2 ≥1 populated agent-subject predicate with ≥100 evidence-backed instances · 3 ≥1,000 role-bearing assertions (actor+action+patient) over ≥2 Vedas, each evidence-cited and tiered · 4 +morphology-derived action-head inventory, ≥5,000 assertions, adjudicated precision ≥0.85 · 5 +event identity across passages, +negation/modality marking.

**I. Concept ontology quality** — 0 free-text tags · 1 flat list, no types, no definitions · 2 typed with definitions but no hierarchy, or hierarchy <25% · 3 typed, 100% definition coverage, unique ids, closed node-type enum **enforced at load** (unknown type raises), hierarchy ≥25% · 4 +depth ≥3 covering ≥60%, +a single authoritative passage→concept layer (no rival layer giving a materially different number), +≥300 entities · 5 +lateral relations at scale, +≥1,000 entities.

**J. Textual reuse / formula quality** — 0 none · 1 parallels with no similarity and no evidence · 2 similarity but one method or one Veda pair, or formulas with no length/spread metadata · 3 ≥3 reuse predicates with per-edge similarity/method/Veda pair, all six Veda pairs present, formulas with word count + occurrence count + cross-Veda flag, ≥90% of the derivative corpus's reuse located · 4 +reuse predicates match the declared contract (no declared reuse predicate empty while undeclared ones carry the load), +stated minimum unit length with sub-threshold population removed or flagged, +symmetric traversal guaranteed or explicitly documented as directed, +`match_level` on 100% of edges · 5 +borrowing direction argued from evidence, +philologist-adjudicated precision.

**K. Evidence / provenance quality** — 0 no provenance · 1 confidence score only · 2 trust/layer on a subset, vocabulary fragmented across producers · 3 100% of edges carry a graded tier from one closed enum **and** a knowledge layer, tier a function of layer not confidence · 4 +100% also carry evidence basis and grade basis (four-field self-description, no second lookup), +evidence payloads name the textual surface they quote, +an independent evaluator verifies ≥95% of a ≥1,000-row evidence sample verbatim against stored text · 5 +every source-explicit edge cites its source record/line, +`evidence_basis` never `UNSPECIFIED` where a basis exists, +`grade_basis` a closed enum, +≥95% of edges re-verifiable using only exported code.

**L. Interpretation-vs-fact separation** — 0 indistinguishable · 1 confidence number only · 2 distinct type but shared traversal and no tier · 3 distinct node type on a distinct tier, model output in a distinct state, a query can return only source-stated facts, self-audit excluded from product traversal · 4 +falsifier on every claim, +evidence (passage or computed metric) **enforced at load**, +≥1 live unadjudicated contradiction, +container inheritance marked with a strict variant of every counting query · 5 +a **populated** TIER_C validated against a human gold set, +≥1 claim attributed to a named external commentator.

**M. Query answerability** — 0 no catalogue · 1 catalogue with ≥25% erroring or unintentionally empty · 2 clean catalogue, <8% of a named ≥50-question set fully answerable · 3 clean catalogue, every query carries a mandatory caveat, ≥8% fully and ≥80% at least partially answerable, 0 regressions · 4 ≥40% fully answerable verified by a non-builder, **and** the misleading-answer state explicitly assessed with 0 questions in it · 5 ≥80% fully answerable each with a measured precision.

**N. Explainability** — 0 ids only · 1 <75% display coverage · 2 ≥95% coverage but edges need a second lookup to explain their grade · 3 100% of product nodes with non-sentinel display label **and** type, 100% of edges with tier + layer, every catalogued query caveated · 4 +100% four-field edge self-description, +descriptions on every page-worthy entity, +the grade **reason** on the edge, +caveat contractually part of the response · 5 +human-readable justification on every assertion, +display layer tested against a real consumer.

**O. Semantic precision** — 0 no notion of precision at all · 1 **unmeasured**: no human-adjudicated sample of any layer exists, so no precision figure can be quoted; rule-based hazard flags exist but are uncalibrated against truth · 2 measured on ≥1 layer by a **≥100-item human-adjudicated sample**, with denominator and per-predicate/per-alias breakdown · 3 measured per layer, ≥0.85 on mention and ≥0.85 on concept layers, per-alias for the top-20 by volume, sample ≥500 · 4 ≥0.90 on every populated layer per alias and per predicate, inter-annotator agreement reported, sub-threshold edges **retired or downgraded** not merely flagged · 5 ≥0.95 everywhere with a build-failing regression suite.

**P. Semantic recall** — 0 no coverage denominator anywhere · 1 **unmeasured**: no gold set enumerates what should have been found; only "share of units with ≥1 assertion", a proxy of unknown tightness · 2 measured on ≥1 layer against a **≥100-passage exhaustively annotated** gold set · 3 ≥0.70 per layer against a ≥300-passage gold set, reported per Veda · 4 ≥0.85 per layer per Veda with a named residual class for every miss · 5 ≥0.95 per layer per Veda with a standing regression suite.

**Q. Graph coherence** — 0 no constraints, duplicate ids, unflagged contradictions · 1 uniqueness on some keys, orphans and signature violations unmeasured · 2 constraints on main types, build-time signature check but the live graph ungated · 3 uniqueness on every entity type, signatures enforced, **a live invariant suite passing against the running database**, 0 duplicate ids, 0 unlabelled nodes, 0 self-loops, 0 contradictory same-predicate pairs · 4 +≤1% of product nodes isolated, +every declared predicate populated or documented empty-by-design, +every live predicate declared in the contract, +symmetric predicates bidirectional or documented as directed · 5 +machine-checked contract/graph equivalence failing CI on drift, +every edge delta reconciled against a pinned baseline.

**R. Research usefulness** — 0 supports no research question · 1 descriptive counts already in a printed concordance · 2 +≥1 non-trivial cross-corpus join but no falsifier and no quantified limit · 3 ≥3 distinct multi-hop joins returning evidence-bearing results, **the graph states its own limits as queryable data**, ≥1 recorded finding with a falsifier · 4 ≥25 recorded findings with falsifiers and computed metrics, limit queryable per-edge **and** per-query, sensitivity to layer choice measurable, **every Work's corpus scope machine-readable** · 5 +a result a specialist would cite, with a reproducible query and an adjudicated evidence sample.

**S. Discovery potential** — 0 flat index · 1 one layer; no join yields a new fact · 2 ≥2 joinable layers but <1,000 non-trivial 2-hop results · 3 ≥4 joinable layers, ≥1,000 non-trivial 2-hop results, ≥1 candidate-generator query existing **and labelled as such**, top-10 share of the densest layer <50% · 4 +≥1 **role-bearing** predicate spanning all four Vedas, +a **stored** centrality or community measure, +a diachronic or stratigraphic axis · 5 +a passage embedding/similarity space for unlabelled analogues, evaluated against a gold set.

**T. Product usability** — 0 raw database, no named queries · 1 named queries but engineering/QA artifacts appear as peers in normal traversal · 2 boundary exists but repeated per query; latency or empty rate makes an interface impractical · 3 boundary written **once** and enforced, 0 diagnostic nodes in product traversal, ≥90% of catalogued queries <200 ms with a stated median, every query names its consumer-facing caveat, deterministic rebuild · 4 +a **served interface** returning the caveat with the payload, +every Work's scope machine-readable, +no query >1 s without a batch label, +≤1% isolated product nodes · 5 +measured real-consumer usage driving the catalogue, +pagination, auth and versioning on the served surface.

---

# The five largest-headroom dimensions — input to V3 planning

Ranked by **maximum realistic gain**, with the precondition each needs. Realistic means
achievable in one V3 pass with the assets already in the repository or a bounded acquisition;
stretch means achievable but not safely plannable.

### 1. **P — Semantic recall: 1 → 4 (+3)**

**Precondition: a human-annotated gold set. That is the entire blocker.**
Everything else exists: five JSON schemas, a protocol document, a reviewer guide, a
worksheet, a 120-row frame, and a sealed 448-mantra candidate set to score against. All 120
rows read `annotator: UNANNOTATED` with zero entities and zero relations. Annotating 300
passages **exhaustively**, stratified by Veda, takes P from "no figure exists" to a measured
per-Veda recall, and level 4's "named residual class for every miss" is then a reporting
discipline this project has already demonstrated it has. Nothing about P requires new
modelling, new data acquisition, or a decision anyone is blocked on.

### 2. **O — Semantic precision: 1 → 4 (+3)**

**Same precondition, same artifact, same pass.** O and P are one unlock and should be planned
as one work item. The measurement target is already prioritised for you: `agne` at 915 edges
and ~95% error is the documented worst case, and V2's own two automated proxies for that same
alias disagreed by 78 percentage points (97.5% vs 19.1% correct), which is the proof that
adjudication cannot be substituted. Reaching 4 rather than 3 additionally requires **acting**
on the measurement — retiring or downgrading sub-threshold edges instead of flagging them —
which also lifts C from 3 to 4 for free, because all 3,896 currently-flagged edges sit at
`TIER_B / ACCEPTED`.

### 3. **H — Agentive/action semantics: 1 → 4 (+3)**

**Precondition: project the sealed 448-mantra artifact. It is a load, not a research
programme.** `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1` is `seal_status:
VALIDATED` with 0 of 11 integrity counters non-zero, and holds 2,459 assertions including
**554 EVENT objects carrying `actor_entity_id`, `patient`, `other_participants` and
`action_head`**, plus 553 `DESCRIBES_ACTION`, 395 `REQUESTED_OUTCOME` and 471
`CANONICAL_ENTITY_REF`, all with Griffith translation spans as evidence. It is verifiably
absent from the graph, which today has **zero** edges carrying any role slot. Loading it
creates the first role-bearing layer, the first Rigvedic model layer, and the first `TIER_C`
candidate population — so it also lifts **L from 4 to 5** and moves **S** and **B**. Reaching
H=4 needs the precision measurement from item 2 on top; H=3 needs only the projection.

### 4. **E — Ritual knowledge depth: 1 → 3 realistic, 4 stretch (+2 to +3)**

**Precondition: authoring, under the probe-first discipline V2 already proved.** Four rites
and 35 apparatus edges over a corpus containing the complete Vājasaneyi Saṃhitā is the widest
gap in this scorecard between what the corpus contains and what the graph models. `HAS_STEP`
and `DESCRIBED_IN` are declared with correct endpoint signatures and both are empty; the
existing four rites already have passage citations sitting in `rituals.yaml` that were never
loaded. Nothing is blocked: no acquisition, no gold set, no upstream pin. This is the largest
gain available that depends on no other item on this list, and it also moves G, R and M.

### 5. **B — Cross-Veda balance: 2 → 4 (+2)**

**Precondition: the four-Veda theonym mention layer — V2's own backlog item 1.**
Five corpus-general predicate families are 100% Rigvedic and no deity in the graph has
measured presence in more than one Veda. There is no `DomainEntity` for Indra, Varuṇa, Rudra,
Viṣṇu or Mitra, which is why Agni, Soma and Sūrya reach four Vedas and Indra reaches one:
their names are also common nouns and his is not. This one layer moves **B**, **C**
(theonym resolvability), **D** (two-Veda presence for the top 20), **M** (up to 19 questions)
and **S** (a four-Veda predicate). It was deliberately not attempted in V2 for a good reason —
the `agne` finding proves deity aliases need their own morphology-aware per-alias audit — and
that reason is now a specification rather than an obstacle, because items 1 and 2 provide the
gold set that audit needs.

### Runners-up, for completeness

| Dim | Gain | Precondition |
| --- | --- | --- |
| **G** Human/social | 2 → 4 (+2) | Split the 322 bundled ṛṣi labels; populate `RishiFamily` (label, constraint and index already exist with 0 nodes) |
| **Q** Coherence | 3 → 4 (+1) | Connect or internalise the `Lemma` layer (26.1% → 0.3% isolated); reconcile 15 empty declared and 21 undeclared live predicates |
| **A**/**R**/**T** | +1 each, shared | Write `scope` / `rights` / `completeness` onto four `Work` nodes. Four property writes. The `Samaveda Samhita` label on an ārcika-only corpus is the single most misleading string in the product graph |
| **I** Concept ontology | 3 → 4 (+1) | Adjudicate and retire one of the two rival passage→concept layers (measured 55.3% vs 98.7% mutual confirmation) — depends on items 1 and 2 |
| **M** Answerability | 3 → 4 (+1) | Hardest on this list: needs a non-Rigvedic attribution source, which does not exist. Add MISLEADING as a verdict state regardless — it is currently unassessed and my probes found two live misleading surfaces |

**If V3 does only one thing, it should be the gold set** — it is the sole precondition of items
1 and 2 (+6 between them), a precondition of item 5's audit, the blocker on `TIER_C` and hence
on L=5, and the deciding evidence for I's rival-layer question. **If V3 does only two things,
the second should be projecting the sealed 448 artifact** (+3 on H, +1 on L, movement on B, R
and S), because it is finished work sitting outside the graph.
