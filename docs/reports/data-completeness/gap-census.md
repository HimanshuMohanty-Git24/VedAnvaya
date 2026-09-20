# Post-V1 Data Completeness Campaign — Gap Census

Agent 1, Wave 0. The registry this report describes is `data/gap_registry.json`, which is
the campaign's source of truth; this document is its reading, not a second copy of it.

- Registry: **74 gaps**, schema version 1.0
- Baseline commit: `d6e93a92c4e3ff1a5682a17b20bf32c6ce8fa19c`
- Measured against the live system on 2026-09-15: API on 127.0.0.1:8000, frontend on 3000,
  Neo4j in Docker `vedagraph-neo4j`. Graph census unchanged from baseline (108,779 nodes,
  265,295 relationships), so every graph figure here is comparable to `BASELINE.md`.
- All Neo4j access was read-only. No CREATE, MERGE, SET or DELETE was issued.

Every gap cites where it was found: an API path, a frontend route, a Cypher query with its
result, or a `file:line`. Counts are real measurements. Where a population is genuinely not
yet knowable the count is `null` with the reason in `root_cause` — never `0`, because a zero
standing for *unknown* is the exact failure this campaign exists to prevent.

## By classification

| Classification | Count | Meaning |
|---|---|---|
| IMPLEMENTATION_GAP | 62 | It exists because the work was not done. Campaign tasks. |
| TRUE_SCOPE_FACT | 5 | A real, intentional, declared boundary. Keep it; it is proved below. |
| STALE | 7 | The text is wrong and the data is there. Disproofs below. |
| **Total** | **74** | |

## By domain

| Domain | Total | Implementation | Scope fact | Stale | Owner agents |
|---|---|---|---|---|---|
| attribution | 8 | 6 | 0 | 2 | 8 |
| ritual | 7 | 6 | 0 | 1 | 13 |
| entity_coverage | 7 | 6 | 0 | 1 | 8 |
| audio | 6 | 5 | 1 | 0 | 4, 5, 6, 7 |
| morphology | 6 | 5 | 0 | 1 | 9 |
| semantics | 6 | 6 | 0 | 0 | 9, 11, 14, 16 |
| translation | 5 | 5 | 0 | 0 | 3 |
| quality | 5 | 5 | 0 | 0 | 16 |
| product_surface | 5 | 5 | 0 | 0 | 8, 16 |
| other | 5 | 2 | 2 | 1 | 3, 7, 8, 16 |
| cross_veda | 4 | 4 | 0 | 0 | 10, 12 |
| formula | 3 | 3 | 0 | 0 | 12 |
| communities | 3 | 2 | 0 | 1 | 15 |
| samaveda_music | 2 | 1 | 1 | 0 | 5 |
| scholarship | 2 | 1 | 1 | 0 | 14 |
| **Total** | **74** | **62** | **5** | **7** | |

## By owner agent

| Agent | Remit | Gaps |
|---|---|---|
| 3 | translation | 6 — TRANSLATION-001, TRANSLATION-002, TRANSLATION-003, TRANSLATION-004, TRANSLATION-005, OTHER-004 |
| 4 | RV audio | 3 — AUDIO-004, AUDIO-005, AUDIO-006 |
| 5 | SV audio + music | 3 — AUDIO-001, SAMAVEDA_MUSIC-001, SAMAVEDA_MUSIC-002 |
| 6 | YV audio | 1 — AUDIO-003 |
| 7 | AV audio | 3 — AUDIO-002, OTHER-002, OTHER-003 |
| 8 | attribution / entity | 17 — ATTRIBUTION-001, ATTRIBUTION-002, ATTRIBUTION-003, ATTRIBUTION-004, ATTRIBUTION-005, ATTRIBUTION-006, ATTRIBUTION-007, ATTRIBUTION-008, ENTITY_COVERAGE-001, ENTITY_COVERAGE-002, ENTITY_COVERAGE-003, ENTITY_COVERAGE-004, ENTITY_COVERAGE-005, ENTITY_COVERAGE-006, ENTITY_COVERAGE-007, PRODUCT_SURFACE-001, OTHER-001 |
| 9 | morphology + semantic roles | 9 — MORPHOLOGY-001, MORPHOLOGY-002, MORPHOLOGY-003, MORPHOLOGY-004, MORPHOLOGY-005, MORPHOLOGY-006, SEMANTICS-001, SEMANTICS-003, SEMANTICS-005 |
| 10 | cross-Veda | 1 — CROSS_VEDA-001 |
| 11 | semantic resemblance | 1 — SEMANTICS-006 |
| 12 | formula / parallel / variant | 6 — CROSS_VEDA-002, CROSS_VEDA-003, CROSS_VEDA-004, FORMULA-001, FORMULA-002, FORMULA-003 |
| 13 | ritual | 7 — RITUAL-001, RITUAL-002, RITUAL-003, RITUAL-004, RITUAL-005, RITUAL-006, RITUAL-007 |
| 14 | scholarship | 3 — SEMANTICS-004, SCHOLARSHIP-001, SCHOLARSHIP-002 |
| 15 | deity communities | 3 — COMMUNITIES-001, COMMUNITIES-002, COMMUNITIES-003 |
| 16 | quality / gold | 11 — SEMANTICS-002, QUALITY-001, QUALITY-002, QUALITY-003, QUALITY-004, QUALITY-005, PRODUCT_SURFACE-002, PRODUCT_SURFACE-003, PRODUCT_SURFACE-004, PRODUCT_SURFACE-005, OTHER-005 |

## The IMPLEMENTATION_GAP list, ranked by missing_count

47 of the 62 implementation gaps have a countable missing population.
The other 15 are listed after them with `null`, because their population cannot be
counted until a prior decision is made — not because it is zero.

Ranking by `missing_count` is deliberately *not* a priority order. A large count can be cheap
(GAP-AUDIO-005 is 16,834 rows needing one metadata field) and a small one can be blocking
(GAP-OTHER-004 is 31 verses plus a recension identity that gates all Samavedic work).

| Rank | Gap | Domain | Missing | Current | Expected | Owner | One sentence |
|---|---|---|---|---|---|---|---|
| 1 | `GAP-MORPHOLOGY-005` | morphology | **20,210** | 0 | 20,210 | 9 | No mantra is available in both scripts: 16,391 RV and AV verses are romanised only and 3,819 SV and YV verses are Devanagari only. |
| 2 | `GAP-RITUAL-006` | ritual | **20,210** | 0 | 20,210 | 13 | No passage carries a ritual-context assignment, so a mention of a crop, metal or animal cannot be distinguished as ritual or everyday. |
| 3 | `GAP-SEMANTICS-001` | semantics | **17,668** | 2,542 | 20,210 | 9 | The semantic assertion layer is Rigveda-only and covers 2,542 of 10,552 RV mantras, so 17,668 mantras carry no assertion. |
| 4 | `GAP-TRANSLATION-005` | translation | **17,283** | 0 | 17,283 | 3 | All 17,283 translations are single-witness and machine-aligned with no per-translation alignment confidence recorded. |
| 5 | `GAP-AUDIO-005` | audio | **16,834** | 0 | 16,834 | 4 | The entire recitation layer is proxied from one external host with nothing cached and no per-record checksum, duration, performer or licence. |
| 6 | `GAP-MORPHOLOGY-001` | morphology | **9,992** | 39 | 10,031 | 9 | The lemma layer is an inert registry: 10,031 Lemma nodes exist, only 39 of them are reached by any edge, and all 39 are deity names. |
| 7 | `GAP-QUALITY-005` | quality | **9,992** | 39 | 10,031 | 16 | The campaign's own baseline matrix reports a dimension in a unit that conceals its sparsity: the Lemma row's 6,560 counts mantras touched by 39 words. |
| 8 | `GAP-MORPHOLOGY-002` | morphology | **9,658** | 10,552 | 20,210 | 9 | Morphological annotation exists for the Rigveda only; 9,658 mantras in the other three corpora have no lemma layer. |
| 9 | `GAP-CROSS_VEDA-002` | cross_veda | **6,527** | 0 | 6,527 | 12 | None of the 6,527 parallel and reuse edges records how the text was transformed, so the product can say two verses are related but never how they differ. |
| 10 | `GAP-ATTRIBUTION-006` | attribution | **5,610** | 14,600 | 20,210 | 8 | Metre is absent for the Samaveda and Yajurveda entirely and partial for the Atharvaveda: 5,610 mantras carry no chandas. |
| 11 | `GAP-ATTRIBUTION-001` | attribution | **5,498** | 10,552 | 20,210 | 8 | Deity dedication resolved to a Devata node is Rigveda-only, and 5,498 mantras carry no dedication record at all. |
| 12 | `GAP-SEMANTICS-002` | semantics | **4,865** | 0 | 4,865 | 16 | Every one of the 4,865 semantic assertions is UNREVIEWED; no assertion in the graph has ever been checked by a human. |
| 13 | `GAP-SEMANTICS-003` | semantics | **4,865** | 0 | 4,865 | 9 | Not one of the 4,865 assertions carries a complete agent-predicate-target triple, 1,522 carry no role slot at all, and the role slots can only point at deities. |
| 14 | `GAP-TRANSLATION-001` | translation | **1,844** | 0 | 1,844 | 3 | The Samaveda has no translation at all: 0 of 1,844 mantras carry HAS_TRANSLATION. |
| 15 | `GAP-AUDIO-001` | audio | **1,844** | 0 | 1,844 | 5 | No Samavedic recitation is catalogued: 0 of 1,844 verses have audio. |
| 16 | `GAP-ATTRIBUTION-004` | attribution | **1,844** | 0 | 1,844 | 8 | The Samaveda has no seer attribution: 0 of 1,844 mantras carry HAS_RISHI. |
| 17 | `GAP-PRODUCT_SURFACE-004` | product_surface | **1,844** | 0 | 1,844 | 16 | Ask cannot retrieve Samavedic passages at all and cannot reach several insight endpoints, so it refuses or misleads on questions the API answers directly. |
| 18 | `GAP-ATTRIBUTION-005` | attribution | **1,297** | 4,542 | 5,839 | 8 | Every Atharvaveda seer attribution is a sukta label projected onto its verses, and 1,297 AV mantras have none at all. |
| 19 | `GAP-AUDIO-002` | audio | **1,159** | 4,680 | 5,839 | 7 | 1,159 Atharvaveda verses have no recitation. |
| 20 | `GAP-FORMULA-003` | formula | **1,103** | 3,722 | 4,825 | 12 | 1,103 of 4,825 formulas are strict substrings of another formula, so formula counts double-count nested wordings. |
| 21 | `GAP-TRANSLATION-002` | translation | **961** | 4,878 | 5,839 | 3 | 961 Atharvaveda mantras have no translation, and 958 of them are the whole of kanda 20. |
| 22 | `GAP-MORPHOLOGY-004` | morphology | **711** | 0 | 711 | 9 | 711 Rigvedic lexical tokens are left unresolved because no feature-conditioned alias mechanism exists, a deferral the architecture document itself calls the highest-value one. |
| 23 | `GAP-QUALITY-002` | quality | **575** | 0 | 575 | 16 | The only populated gold set is model-adjudicated: all 575 theonym rows were labelled by claude-opus-5, so no human-labelled evaluation data exists anywhere. |
| 24 | `GAP-ATTRIBUTION-007` | attribution | **427** | 302 | 729 | 8 | 427 of 729 seers are not resolved to a family. |
| 25 | `GAP-ATTRIBUTION-002` | attribution | **324** | 0 | 324 | 8 | The Atharvaveda's Anukramani deity ascription IS held, as 4,816 edges over 4,160 mantras, but none of its 324 descriptors resolves to a Devata node, so the product reports it as absent. |
| 26 | `GAP-CROSS_VEDA-003` | cross_veda | **256** | 750 | 1,006 | 12 | 256 of 1,006 EXACT_PARALLEL_OF edges carry no parallel_id, so the parallel group they belong to cannot be recovered. |
| 27 | `GAP-SEMANTICS-005` | semantics | **229** | 0 | 229 | 9 | All 229 DomainEntity nodes lack a domain assignment, so the entity population cannot be partitioned into ritual, cosmological or material spheres. |
| 28 | `GAP-AUDIO-003` | audio | **223** | 1,752 | 1,975 | 6 | 223 Yajurveda verses have no recitation. |
| 29 | `GAP-ENTITY_COVERAGE-007` | entity_coverage | **220** | 9 | 229 | 8 | Phrase matching was never built, and personification resolution is materialised for 9 NaturalPhenomenon nodes only, leaving the other 200-odd entities with no way to distinguish a refusal from a gap. |
| 30 | `GAP-ENTITY_COVERAGE-001` | entity_coverage | **210** | 4 | 214 | 8 | The epithet layer reaches 4 of 214 deities and no epithet is linked to a single passage, so no question about where an epithet occurs can be answered. |
| 31 | `GAP-COMMUNITIES-001` | communities | **192** | 0 | 192 | 15 | No community or partition structure exists anywhere in the graph, so deity communities cannot be returned or computed. |
| 32 | `GAP-ENTITY_COVERAGE-002` | entity_coverage | **189** | 25 | 214 | 8 | Deity profile statistics were materialised for only 25 of 214 deities, so 189 deity pages report null for every corpus. |
| 33 | `GAP-AUDIO-004` | audio | **150** | 10,402 | 10,552 | 4 | 150 Rigveda verses have no recitation, of which 80 are the eleven Valakhilya hymns RV 8.49-8.59. |
| 34 | `GAP-OTHER-003` | other | **138** | 5,839 | 5,977 | 7 | The Atharvaveda holds 5,839 mantras against roughly 5,977 attested and the divergence is unresolved, while a declared 1856 canonical corpus for the same work has passage_count 0 and qa_status FAILED over 478 inventoried leaves. |
| 35 | `GAP-QUALITY-001` | quality | **120** | 0 | 120 | 16 | The Rigveda semantic gold set is a 120-row empty scaffold: every row is UNANNOTATED with epoch-zero timestamp, no entities and no relations, and its declared adjudication and manifest files do not exist. |
| 36 | `GAP-FORMULA-002` | formula | **107** | 613 | 720 | 12 | Formula family matching is degraded by the script split, some edges predate match-level recording, and the diffusion endpoint returns no family id so the product cannot link a family to its own record. |
| 37 | `GAP-QUALITY-004` | quality | **89** | 11 | 100 | 16 | 89 of the 100 benchmark questions remain non-pass, and only 11 are fully answerable. |
| 38 | `GAP-TRANSLATION-003` | translation | **72** | 1,903 | 1,975 | 3 | 72 Yajurveda mantras have no translation. |
| 39 | `GAP-COMMUNITIES-002` | communities | **57** | 14 | 71 | 15 | 57 of 71 composite deities carry no components: every one of the 33 GROUP deities is undecomposed, and 24 of 38 PAIR deities are. |
| 40 | `GAP-TRANSLATION-004` | translation | **50** | 10,502 | 10,552 | 3 | 50 Rigveda mantras have no translation. |
| 41 | `GAP-OTHER-004` | other | **31** | 1,844 | 1,875 | 3 | 31 of the traditional 1,875 Samavedic verses carry no canonical key, and the printed edition's recension is not established - Griffith's preface assigns it to Ranayaniya rather than Kauthuma. |
| 42 | `GAP-PRODUCT_SURFACE-002` | product_surface | **14** | 7 | 21 | 16 | The limits catalogue publishes 7 of at least 21 structurally unanswerable dimensions, and says so rather than implying completeness. |
| 43 | `GAP-RITUAL-003` | ritual | **9** | 14 | 23 | 13 | Only 14 of 23 registry objects are linked to a rite, so mani at 86 mentions, dundubhi at 17 and the udumbara amulet are absent from the ritual-object ranking despite being genuine ritual objects. |
| 44 | `GAP-CROSS_VEDA-001` | cross_veda | **5** | 1 | 6 | 10 | Directed textual reuse was established for the RV-SV pair only; the other five corpus pairs have no direction at all despite carrying thousands of undirected parallel edges. |
| 45 | `GAP-RITUAL-004` | ritual | **5** | 11 | 16 | 13 | 11 ritual roles are modelled against the classical set of sixteen, and the hotr - the principal Rigvedic officiant - is wired to no rite at all. |
| 46 | `GAP-PRODUCT_SURFACE-005` | product_surface | **4** | 0 | null | 16 | The whole canonical corpus is gitignored, so no released corpus text is protected by version history, and 4 released Samavedic verses carry printed apparatus welded into the text. |
| 47 | `GAP-PRODUCT_SURFACE-003` | product_surface | **3** | 0 | 3 | 16 | Three visualizations are blocked by missing API aggregates: no per-book deity breakdown, no deity-by-metre aggregate, and dispersion capped at 200 passages per request. |

### Implementation gaps whose population is not yet knowable

| Gap | Domain | Owner | Why the count is null |
|---|---|---|---|
| `GAP-SAMAVEDA_MUSIC-002` | samaveda_music | 5 | Not countable until a gana corpus exists: the population is the number of verse-to-saman assignments, and it depends on a corpus not held. |
| `GAP-MORPHOLOGY-006` | morphology | 9 | The dimension is per-text-version, not per-mantra, so there is no single figure. Its countable components are 1,844 SV mantras with no accented text and 139 YV mantras with no unaccented text. |
| `GAP-SEMANTICS-004` | semantics | 14 | Not countable until a stratum scheme is chosen; the count would be a property of the scheme, not of the corpus. |
| `GAP-SEMANTICS-006` | semantics | 11 | Not countable until a resemblance measure and threshold are declared: the edge count is entirely a function of the threshold. |
| `GAP-CROSS_VEDA-004` | cross_veda | 12 | Not countable until a pada-level detector runs; the population depends on the similarity threshold at pada scale. |
| `GAP-FORMULA-001` | formula | 12 | Not countable without a selectivity policy. Materialising every passage pair sharing any formula is a join over 22,686 USES_FORMULA edges across 4,825 formulas, so the population is a policy choice rather than a fact. |
| `GAP-RITUAL-001` | ritual | 13 | Not countable until it is decided what counts as a rite named by the Samhitas. That is a curation question, and a hard ceiling sits above it: the prose describing the srauta rites is not in the corpus. |
| `GAP-RITUAL-002` | ritual | 13 | Not countable because a rite's step count is a property of the text that describes it, and that text is excluded by scope. |
| `GAP-RITUAL-005` | ritual | 13 | Not countable until it is decided which deity-offering associations the Samhitas actually support. |
| `GAP-SCHOLARSHIP-001` | scholarship | 14 | Not countable until a commentarial corpus is chosen: Sayana alone would give a very different count from a modern survey. |
| `GAP-ENTITY_COVERAGE-003` | entity_coverage | 8 | Not countable because the set of remedy entities worth curating has never been enumerated, and the graph holds no remedy class against which to measure a shortfall. |
| `GAP-ENTITY_COVERAGE-004` | entity_coverage | 8 | Not countable by construction: the missing thing IS the declared expectation, so there is nothing to measure a shortfall against until one exists. That is the gap. |
| `GAP-ENTITY_COVERAGE-006` | entity_coverage | 8 | Not countable because no recall figure exists for ABOUT_CONCEPT or MENTIONS_ENTITY anywhere in the graph. One cell is known false by hand; the general shortfall is unmeasured. |
| `GAP-QUALITY-003` | quality | 16 | Not countable until predicates are selected for calibration and a labelled sample size is chosen. |
| `GAP-PRODUCT_SURFACE-001` | product_surface | 8 | A correctness defect in one response block rather than a missing population, so a count does not apply. |

## The six findings a later session should read first

These were not in `BASELINE.md`, `STATUS.md` or the `/limits` page, and each changes what
some other gap is worth doing.

1. **`GAP-MORPHOLOGY-001` — the lemma layer reaches 39 words.** 10,031 `:Lemma` nodes exist;
   `MENTIONS_LEMMA` carries 9,000 edges and they reach **39 distinct lemmas, every one a
   theonym** (indra- 2,305, agni- 1,604, soma- 950, down to asamati- 2). 9,992 lemma nodes have
   zero edges in either direction. The layer was built as the instrument behind the Rigvedic
   deity mention count, never as a lexical index. This is the largest overstatement in the
   product's own numbers and it is recorded in the campaign baseline — see `GAP-QUALITY-005`.

2. **`GAP-ATTRIBUTION-002` — the Atharvaveda's deity ascription is held and reported absent.**
   4,816 `HAS_DEVATA_ASCRIPTION` edges over 4,160 AV mantras reach 324 `:DevataAscription`
   descriptors from `AV_WHITNEY_ANUKRAMANI`, and **none of the 324 resolves to a `:Devata`**.
   The descriptors are transparently deity-denoting adjectives — agneyam, aindram, saumyam,
   varunam. So the product tells readers the AV has no dedication apparatus while holding one.
   This also splits the campaign's stated 9,658-mantra dedication gap into two different jobs:
   5,498 mantras with no apparatus at all (`GAP-ATTRIBUTION-001`) and 4,160 with an unresolved
   one, and it makes one live API caveat false (`GAP-ATTRIBUTION-003`).

3. **`GAP-QUALITY-001` — the semantic gold set is an empty scaffold.**
   `data/gold/rigveda_semantic_gold_v1.jsonl` has 120 rows. All 120 carry
   `annotator: "UNANNOTATED"`, `annotated_at: "1970-01-01T00:00:00Z"`, `entities: []` and
   `relations: []`. Its two declared companion files do not exist on disk. The only populated
   gold set, 575 theonym rows, is `MODEL_ADJUDICATED` by claude-opus-5. Across 695 gold rows
   there are **zero human annotations**, which is why nothing in the graph is calibrated.

4. **`GAP-MORPHOLOGY-003` — a live API claim about the Padapatha is false.** Every insights
   endpoint that reports the Rigveda serves the scope sentence *"Padapatha and the accented
   samhitapatha are carried as text versions of these same mantras"*. Enumerating the value
   space rather than grepping for the expected value: all 44,276 `:TextVersion` nodes have
   `text_form = 'SAMHITA'`, all 8 distinct `text_version_id` values are samhitapatha editions,
   and the only `pada` property in the database is an a/b/c/d verse-quarter label on
   `:SemanticAssertion`. There is no padapatha anywhere.

5. **`GAP-AUDIO-001` — the Samavedic audio is identified, licence-cleared and never fetched.**
   The gap is not source-blocked, which contradicts the natural reading of the audio stats.
   `four_veda_source_matrix.yaml:1233-1279` declares a SELECTED row: *"474 Ogg files,
   licence-checked PER FILE ... 458 CC BY-SA 4.0, 16 CC0, 0 missing"*, `mirror_local: true`,
   *"THIS IS THE ONLY MIRRORABLE AUDIO ACROSS ALL FOUR VEDAS"*. The inventory holds 475 rows
   with `found_on_commons: true` on every one and **`sha256_of_bytes: null` on every one** —
   not a byte was fetched. The real dependency is gana-to-arcika boundary verification, not
   acquisition.

6. **`GAP-FORMULA-001` — `SHARES_FORMULA_WITH` is the only declared type with zero edges.**
   Counting every type returned by `db.relationshipTypes()` individually rather than reading
   the populated census, exactly one comes back at 0. Separately, `MUSICALIZED_AS` is
   documented in the ontology reference with *"edges: 0"* but is **not in the type store at
   all**, so the documentation is ahead of the schema (`GAP-SAMAVEDA_MUSIC-002`).

## Every STALE finding, with its disproof (7)

Each of these would make a campaign agent build something that exists, or trust a false
statement. Two are served live by the API; five are in reports a later session would consult.

### `GAP-ATTRIBUTION-003` — A live API caveat asserts that AV carries no Anukramani deity ascription, which the graph disproves: AV carries 4,816 such edges.

- **Surface:** GET /api/v1/insights/devatas/VG:DEVATA:INDRAH -> caveats[source=has_devata_layer_scope]
- **Disproof:** The served caveat reads: "HAS_DEVATA is Rigveda-only: 10,558 edges, every one on the RV. A zero for SV/YV/AV means those corpora carry no Anukramani deity ascription, not that the deity is absent from them." The second clause is false for AV: MATCH (p:Mantra)-[:HAS_DEVATA_ASCRIPTION]->(:DevataAscription) WHERE p.veda='AV' returns 4,816 edges over 4,160 mantras, all from registry_namespace AV_WHITNEY_ANUKRAMANI, which is precisely an Anukramani deity ascription.
- **Why it is wrong:** The caveat was written about the HAS_DEVATA predicate and then generalised into a claim about the corpora. The AV descriptor layer was added later and the caveat was never revised. The effect is the inverse of the failure this product normally guards against: instead of showing a zero that reads as textual absence, it describes held data as absent.
- **What to do:** Rewrite the caveat to say that resolved dedication is RV-only while AV carries an unresolved Anukramani descriptor layer of 4,816 edges. The same sentence appears in the derived metric DEVATA_ATTRIBUTION_BY_VEDA scope_note and in frontend copy at frontend/src/app/sources/page.tsx:317, so all three surfaces must change together.
- **Owner:** agent 8

### `GAP-ATTRIBUTION-008` — A report claims RishiFamily is empty and all 729 seers unresolved; the live graph holds 87 families, 305 edges and 302 resolved seers.

- **Surface:** docs/reports/KNOWLEDGE_MODEL_V3_FINAL_REPORT.md:392
- **Disproof:** The report states "RishiFamily is 0 nodes / 0 edges. Holds G at 2 on its own; 729 rsis unresolved." Disproof: MATCH (f:RishiFamily) RETURN count(f), sum(degree) -> 87 nodes, 305 edges; MATCH (r:Rishi) ... with_family -> 302 of 729 resolved. The label census confirms RishiFamily at 87 nodes.
- **Why it is wrong:** The claim described the state at the V3 baseline audit and the layer was built afterwards. It is a historical report, but it is the document a later session is most likely to consult for the rishi layer, and its figure would make the campaign build something that already exists.
- **What to do:** NONE. Record the correction; the real remaining work is GAP-ATTRIBUTION-007's 427 unresolved seers, not 729.
- **Owner:** agent 8

### `GAP-MORPHOLOGY-003` — The Rigveda scope statement, served live by the API, claims a Padapatha text version is carried; no padapatha exists anywhere in the graph.

- **Surface:** GET /api/v1/insights/cross-veda -> scope_statements[RV].scope, served live on every insights endpoint that reports RV; data/registry/works.yaml:16
- **Disproof:** The served RV scope statement claims: "Padapatha and the accented samhitapatha are carried as text versions of these same mantras, not as separate works." Disproof, by enumerating the value space rather than grepping for the expected value: MATCH (t:TextVersion) RETURN t.text_form, count(*) -> SAMHITA for all 44,276, no other value. The 8 distinct text_version_id values are GRETIL.RV.AUFRECHT, VEDAWEB.AUFRECHT, GRETIL.AVS.SAUNAKA.ACCENTED, GRETIL.AVS.SAUNAKA.UNACCENTED, VEDAGRAPH.AVS.SEARCH_NORMALIZED, WIKISOURCE_SA.YV.VSM.ACCENTED, WIKISOURCE_SA.SV.KAU.ARCIKA_MULA, WIKISOURCE_SA.YV.VSM.UNACCENTED - all samhitapatha. CALL db.propertyKeys() matching 'pada' returns exactly one key, and it is a verse-quarter label (values a/b/c/d) on 2,406 SemanticAssertion nodes, not padapatha text.
- **Why it is wrong:** The claim conflates the accented samhitapatha (which IS carried, twice over, from GRETIL and VedaWeb) with the padapatha (which is not). VedaWeb does publish a padapatha, so the source was in hand and the sentence was probably written from the source's contents rather than from what was ingested. It is the most consequential stale claim found because it is served on every insights endpoint reporting the Rigveda, and a reader would reasonably expect to be able to query word-segmented text.
- **What to do:** Either correct works.yaml:16 to say the accented samhitapatha only, or ingest the padapatha as a distinct text_form so the claim becomes true. Correcting the text is the immediate obligation; ingesting is optional.
- **Owner:** agent 9

### `GAP-RITUAL-007` — A diagnosis report says asvamedha does not appear at all; it is one of the eight modelled rites.

- **Surface:** docs/reports/V3_1_MISLEADING_DIAGNOSIS.md:132
- **Disproof:** The diagnosis states "asvamedha does not appear at all ... vajapeya, rajasuya, darsapurnamasa and caturmasya are absent from the 8-node Ritual class." Disproof for the first: MATCH (r:Ritual) WHERE toLower(r.entity_key) CONTAINS 'asvamedha' RETURN r.entity_key -> VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE exists, with display_label "horse sacrifice (asvamedha)". The other four named rites are confirmed still absent.
- **Why it is wrong:** The horse sacrifice was added after the V3.1 diagnosis was written. The rest of the sentence is still accurate, which is what makes the claim hazardous: a session reading it would trust the whole list and add a duplicate asvamedha node while correctly adding the other four.
- **What to do:** NONE. The live gap is the four remaining rites, tracked as GAP-RITUAL-001.
- **Owner:** agent 13

### `GAP-COMMUNITIES-003` — A scorecard claims CO_OCCURS_WITH is empty; it carries 306 deity-pair edges.

- **Surface:** docs/reports/KNOWLEDGE_MODEL_V3_WORLD_CLASS_SCORECARD.md:1493
- **Disproof:** The scorecard states: "Deity community structure is effectively absent: CO_OCCURS_WITH is 0." Disproof: MATCH (a:Devata)-[r:CO_OCCURS_WITH]->(b) RETURN count(r) -> 306. The whole-graph relationship census lists CO_OCCURS_WITH at 306, and /api/v1/insights/capabilities reports pairwise_co_occurrence_edges 306 as a measured value.
- **Why it is wrong:** The co-occurrence layer was built after the scorecard was written. The conclusion the scorecard drew - that community structure is absent - happens to remain true for the right reason (a pairwise layer is not a partition), so the claim is stale in its evidence while accidentally correct in its verdict. That combination is the dangerous kind: a session confirming the verdict would leave the false evidence in place.
- **What to do:** NONE. The live gap is GAP-COMMUNITIES-001, and its evidence is the absent partition, not an absent co-occurrence layer.
- **Owner:** agent 15

### `GAP-ENTITY_COVERAGE-005` — The benchmark records tin as attested but unregistered; a Metal node for trapu exists with 2 mentions.

- **Surface:** docs/reports/V3_2_FINAL_100_QUESTION_BENCHMARK.md:226 and :147
- **Disproof:** The benchmark states "trapu (tin) attested and unregistered ... there is no Metal node for it", and grades Q10 MISLEADING partly on it. Disproof: MATCH (m:Metal) RETURN m.entity_key, m.display_label, mentions -> VG:CONCEPT:TRAPU-TIN, "tin (trapu)", 2 mentions. The Metal class now holds 7 nodes: hiranya 84, ayas 11, sisa 7, rajata 2, trapu 2, syama 2, loha 1.
- **Why it is wrong:** The node was added when the Q10 defect was fixed, which the V3.3 re-grade reflects by moving Q10 to FULLY_ANSWERABLE. The V3.2 markdown still carries the original finding. It matters because trapu is cited in several later documents as the canonical example of registry invisibility - the example is now historical, though the class of defect it illustrates is real and is tracked as GAP-ENTITY_COVERAGE-004.
- **What to do:** NONE. Keep trapu as the illustrative case for the missing expected-entity manifest, but not as an open registry gap.
- **Owner:** agent 8

### `GAP-OTHER-005` — A report lists all four Work.scope properties as null; all four are populated and served live by the API.

- **Surface:** docs/reports/KNOWLEDGE_MODEL_V3_FINAL_REPORT.md:394
- **Disproof:** The report lists among its remaining blockers: "All four Work.scope properties are null." Disproof: MATCH (w:Work) RETURN w.work_id, w.scope IS NOT NULL, size(w.scope), size(w.excluded_corpora) -> RV scope 381 chars with 4 exclusions; SV 595 chars with 7; YV 540 chars with 7; AV 559 chars with 3. All four are populated, and they are served live in the scope_statements block of every insights endpoint.
- **Why it is wrong:** The scope statements were authored after the V3 final report and are now among the strongest parts of the product - they are the text that tells a reader the Krishna Yajurveda is not held at all. The stale claim matters because a session reading that report would conclude the scope apparatus does not exist and rebuild it, overwriting the statements that the frontend not-held copy and three HTTP-boundary tests depend on.
- **What to do:** NONE. Note in passing that the RV scope statement, while populated, contains the false Padapatha claim tracked as GAP-MORPHOLOGY-003, so it needs correcting rather than creating.
- **Owner:** agent 16

Two of the seven are live product surfaces rather than stale reports, and they fail in opposite
directions. `GAP-MORPHOLOGY-003` claims data the graph does not hold. `GAP-ATTRIBUTION-003`
denies data the graph does hold. The second is the more interesting failure: this product is
carefully built so that a zero never reads as textual absence, and here a caveat written to
protect a reader from misreading a zero ended up describing 4,816 held edges as absent.

## Every TRUE_SCOPE_FACT, with its justification (5)

These are kept, not closed. Each is declared in `data/registry/works.yaml` or
`PRODUCT_V1_SCOPE.md`, surfaced to the reader, and in three cases asserted by a test at the
HTTP boundary. A campaign agent must not close any of them by ingesting material into an
existing work identifier — that would silently change what every existing per-Veda
denominator means.

### `GAP-AUDIO-006` — Audio is mapped at verse granularity only; no word- or pada-level timing exists, and the AudioSegment entity is declared but empty.

- **Surface:** PRODUCT_V1_SCOPE.md:212-221; GET /api/v1/audio/stats -> by_scope_type {"MANTRA": 16834}; schemas/audio_segment.schema.json
- **Proof it is declared:** PRODUCT_V1_SCOPE.md:212-221 "No audio sub-verse ... there is no word- or pada-level timing and none was invented." audio/stats reports only MANTRA scope. All 21 data/canonical/**/audio_segments.jsonl files are 0 bytes; the AudioSegment schema's AlignmentMethod (4 values) and ReviewStatus (4 values) enums have zero instances between them.
- **Justification:** A recorded V1 decision, and the right one: sub-verse timing cannot be derived from proxied streams without forced alignment, and inventing timings was explicitly refused. The expected population is not knowable because it depends on an alignment that has never been run; writing 0 here would assert that no sub-verse boundary exists in the recordings.
- **What closing it would require:** Forced alignment requires local audio, which GAP-AUDIO-005 shows this product does not hold. / NONE for V1. Closing it requires local audio plus a Sanskrit forced aligner, in that order.

### `GAP-SAMAVEDA_MUSIC-001` — The gana collections (roughly 2,639 ganas against 1,875 arcika verses) are a declared exclusion from this work identifier, and the product says so in its own scope statement.

- **Surface:** GET /api/v1/works -> VG:WORK:SV:KAU excluded_corpora; frontend /vedas/samaveda "What this collection does not hold"; /limits card samavedic_melodic_layer
- **Proof it is declared:** works.yaml:63-70 excluded_corpora: SAMAVEDA_GRAMAGEYA_GANA, SAMAVEDA_ARANYAKAGEYA_GANA, SAMAVEDA_UHAGANA, SAMAVEDA_UHYAGANA, SECOND_SAMAVEDIC_RECENSION, SAMAVEDIC_BRAHMANA, UPANISAD. Scope text: "ARCIKA ONLY. THIS IS NOT THE COMPLETE SAMAVEDA. ... Any claim that VedaGraph 'has the Samaveda' while holding only the arcika is FALSE." works.yaml:46 carries coverage_status INCOMPLETE_BOUNDED, the only work that does.
- **Justification:** An on-record scope decision, correctly declared at four surfaces and carrying its own coverage_status field. It is a real boundary, not an oversight: works.yaml:290-297 states "The ganas need their own work_id; Sanskrit Wikisource carries all four gana books, so this is real future work and not a hypothetical." It is recorded here as a TRUE_SCOPE_FACT because the V1 boundary is genuine and declared, while noting that the corpus itself is identified and available.
- **What closing it would require:** The four gana books are on Sanskrit Wikisource; data/source_registry/samaveda_gana_page_inventory.jsonl already inventories 733 pages, with content_snapshotted false on all 733. / A separate gana work_id. The ganas must not be ingested under VG:WORK:SV:KAU: that would silently change what every existing SV count denominates.

### `GAP-SCHOLARSHIP-002` — No post-Samhita layer is held for any Veda: no Brahmana, Aranyaka or Upanisad, and no commentary.

- **Surface:** GET /api/v1/works -> every work's excluded_corpora; frontend /vedas/[veda] "What this collection does not hold"
- **Proof it is declared:** All four works declare UPANISAD in excluded_corpora. RV excludes RIGVEDIC_BRAHMANA and RIGVEDIC_ARANYAKA; SV excludes SAMAVEDIC_BRAHMANA; YV excludes SATAPATHA_BRAHMANA; AV excludes GOPATHA_BRAHMANA. PRODUCT_V1_SCOPE.md:24 states it plainly: "No Brahmana, no Aranyaka, no Upanisad." No commentarial work is declared or held.
- **Justification:** A declared and consistently applied scope decision, stated at four work identifiers and in the product scope document, and correctly surfaced per Veda on the frontend. It is recorded here as a TRUE_SCOPE_FACT because it is a genuine boundary - but it is the boundary that causes GAP-RITUAL-002 and constrains GAP-SCHOLARSHIP-001, so the campaign should know that two of its ritual and scholarship gaps are downstream of this one decision rather than independently fixable.
- **What closing it would require:** The post-Samhita corpora themselves, most of which are public domain. / A new work identifier per corpus. These must not be ingested under an existing Samhita work_id: doing so would change what every existing per-Veda denominator means.

### `GAP-OTHER-001` — Only the Shukla Yajurveda in the Madhyandina recension is held; the entire Krishna Yajurveda and the Kanva recension are not.

- **Surface:** GET /api/v1/works -> VG:WORK:YV:VSM excluded_corpora and scope_honest_label; frontend /vedas/yajurveda "What this collection does not hold"
- **Proof it is declared:** works.yaml:323-330 excluded_corpora: KRISHNA_YAJURVEDA_TAITTIRIYA, KRISHNA_YAJURVEDA_KATHAKA, KRISHNA_YAJURVEDA_MAITRAYANI, KRISHNA_YAJURVEDA_KAPISTHALA, SHUKLA_YAJURVEDA_KANVA_RECENSION, SATAPATHA_BRAHMANA, UPANISAD. Scope text: "the KRISHNA (Black) Yajurveda is NOT HELD AT ALL ... This is the exclusion most likely to mislead, because 'the Yajurveda' in ordinary use covers both." Asserted at the HTTP boundary by tests/api/test_works.py:305-308.
- **Justification:** A declared, tested and correctly surfaced boundary, and the one the product itself flags as most likely to mislead - rightly, since 'the Yajurveda' ordinarily covers both and the Krishna recensions interleave prose brahmana passages with the mantras that have no counterpart here. Campaign rule 3 forbids mapping Taittiriya material onto Madhyandina.
- **What closing it would require:** The Krishna Yajurveda recensions, each of which would need its own work identifier. / NONE for V1.

### `GAP-OTHER-002` — Only the Saunaka Atharvaveda is held, as a working private corpus; the Paippalada recension is not held and is not a minor variant.

- **Surface:** GET /api/v1/works -> VG:WORK:AV:SAU excluded_corpora; frontend /vedas/atharvaveda; PRODUCT_V1_SCOPE.md:22
- **Proof it is declared:** works.yaml:364-367 excluded_corpora: ATHARVAVEDA_PAIPPALADA_RECENSION, GOPATHA_BRAHMANA, UPANISAD. Scope text: "The PAIPPALADA recension is NOT HELD, and it is not a minor variant -- it is a substantially different collection with its own hymn order, so an Atharvavedic absence measured here is an absence from the Saunaka recension only." PRODUCT_V1_SCOPE.md:22 records that the AV is "held as a working private corpus". Asserted by tests/api/test_works.py:311-314.
- **Justification:** A declared and tested boundary, correctly qualified: the scope statement says an Atharvavedic absence measured here is an absence from Saunaka only, which is the honest reading. The working-private rights status is a separate real constraint on publication, not on completeness. Note that the AV also carries a genuine open question about its own total - 5,839 held against approximately 5,977 attested, recorded as OPEN_RESEARCH with one candidate mechanism raised and falsified - which is tracked separately as it is not a scope fact.
- **What closing it would require:** The Paippalada recension, which would need its own work identifier. / NONE for V1.

### Why these five and not more

The declared exclusion lists in `works.yaml` hold 21 values across the four works, and every
one of them is a genuine boundary with zero data by design. They are not registered as 21
separate gaps because they collapse into five decisions: no gana corpus, no Krishna
Yajurveda, no Paippalada, no post-Samhita layer, and no second recension of anything. Each
decision is recorded once.

Two of these scope facts are load-bearing for gaps elsewhere, and the campaign should know it
before planning work:

- `GAP-SCHOLARSHIP-002` (no Brahmana, Aranyaka or Upanisad) **causes** `GAP-RITUAL-002`. Ritual
  procedure is described in the Brahmana and Srautasutra prose. Three `HAS_STEP` edges in the
  whole graph is not a thin layer that can be thickened; it is the correct consequence of a
  scope decision, and the honest closure may be a clearer scope statement rather than data.
- `GAP-SAMAVEDA_MUSIC-001` (no gana corpus) **blocks** `GAP-ATTRIBUTION-004` and part of
  `GAP-ATTRIBUTION-001`. The Arseya Brahmana and the Devatadhyaya Brahmana both key to samans
  in the gana collections, so Samavedic seer and deity attribution are downstream of a corpus
  this work identifier excludes. `veda_coverage_v3.json` records that the deity join key
  "exists for 7.7% of verses".

## Gaps that are blocked on other gaps

Wave planning should respect these; several are not independently workable.

| Gap | Blocked on | Why |
|---|---|---|
| `GAP-ATTRIBUTION-004` (SV seers) | `GAP-SAMAVEDA_MUSIC-001` | The Arseya Brahmana keys to samans in the gana corpus. |
| `GAP-ATTRIBUTION-001` (SV dedication) | `GAP-SAMAVEDA_MUSIC-001` | The Devatadhyaya Brahmana keys to samans; join key covers 7.7% of verses. |
| `GAP-RITUAL-002` (procedure) | `GAP-SCHOLARSHIP-002` | Procedure is Brahmana and Srautasutra prose, excluded by scope. |
| `GAP-SCHOLARSHIP-001` (disagreement) | a commentarial corpus | Needs an external source; the largest external dependency after the SV sources. |
| `GAP-SEMANTICS-004` (dating) | `GAP-SCHOLARSHIP-001` | A stratum assignment is one scholar's position and needs an attributed-claim model first. |
| `GAP-QUALITY-003` (calibration) | `GAP-QUALITY-001` | There is nothing to calibrate against until a human-labelled sample exists. |
| `GAP-QUALITY-004` (benchmark roll-up) | most of the registry | A roll-up; re-measure after each wave rather than working it directly. |
| `GAP-SEMANTICS-001` (SV assertions) | `GAP-TRANSLATION-001` | The model half of the layer reads a translation the SV does not have. |
| `GAP-FORMULA-002` (cross-script matching) | `GAP-MORPHOLOGY-005` | RV in Latin against SV in Devanagari bottoms out at the weakest match surface. |
| `GAP-PRODUCT_SURFACE-003` (deity x metre) | `GAP-ATTRIBUTION-006` | The matrix would ship two-thirds hatched while metre misses SV and YV. |
| `GAP-COMMUNITIES-001` (partition) | `GAP-COMMUNITIES-002` | An undecomposed dual or group label cannot be placed in a community. |
| `GAP-TRANSLATION-001`, `GAP-ATTRIBUTION-004` | `GAP-OTHER-004` | Aligning to a witness of undetermined recension compounds the uncertainty. |

## What was searched and yielded nothing

Recorded so a later session does not repeat it.

**Graph structure, enumerated rather than sampled.**

- Every declared relationship type was counted individually via `db.relationshipTypes()` with
  a per-type count. **Exactly one** is declared with zero edges: `SHARES_FORMULA_WITH`. There
  is no second unpopulated predicate hiding in the schema, so predicate-level declared-but-empty
  auditing is complete and does not need redoing.
- `db.propertyKeys()` was filtered for `ritual_context`, `expected_source`, `manifest_source`,
  `transformation`, `stratum`, `chronolog`, `community`, `louvain`, `partition`, `embedding`,
  `vector`, `melod`, `gana`, `saman`, `svara`, `accent`, `pada`. Only `accented` and `pada`
  exist, and `pada` is a verse-quarter label. Every other dimension is absent at the property
  level, so none of them needs re-probing under a different name.
- `db.labels()` was filtered for `schol`, `comment`, `person`, `agent`, `author`, `asserter`,
  `melod`, `gana`, `saman`, `music`, `narrative`, `myth`, `episode`. **No match.** There is no
  scholar, commentator, melody or narrative entity under any naming convention.
- `SHOW INDEXES WHERE type='VECTOR'` returns 0. No embedding index exists.
- The full 65-type relationship census and 47-label node census were taken and reconciled
  against `BASELINE.md`. Node and relationship totals match the baseline exactly, so the graph
  was not mutated during this census.

**API surface.** All 44 endpoints in `openapi.json` were enumerated; 15 were called and their
responses parsed for `data_status`, `caveats`, null dimension blocks and typed-absence enums.
Four endpoints return `data_status: SUPPORTED` with no gap content at all — `/api/v1/stats`,
`/api/v1/works`, `/api/v1/devatas` and `/api/v1/insights/capabilities` (whose own status is
SUPPORTED because the *catalogue* is complete for what it probed, not the product). The six
`PARTIAL` insights endpoints carried 3 to 6 caveats each and were the richest single source in
this census; the graph-traversal endpoints (`/graph/*`, `/passages/{key}/*`) were not
individually swept because their gap content is per-passage rather than per-dimension.

**Frontend.** `frontend/src/` was grepped for 30 gap-language patterns across `.tsx` and `.ts`.
Two things worth recording:

- Almost every match is *typed-absence machinery*, not an undisclosed gap: `KnowledgeStatus`,
  `NOT_BUILT`, `INSUFFICIENT_EVIDENCE`, `<Caveat>`, `is-absent` and `tone-insufficient`. The
  frontend states absences it is given; it does not invent or hide them. No frontend copy was
  found asserting a capability the API does not support.
- The first grep over `frontend/` timed out at 120s on `node_modules` and `.next`. Scope any
  repeat to `frontend/src/`. Matches in `*.css` are noise — `insufficient` and `not established`
  appear there as design-token names.

**Registries.** All 23 files in `data/registry/`, 14 in `data/source_registry/`, and the
`data/gold`, `data/product`, `data/audio`, `data/domain`, `data/knowledge` and `schemas` trees
were inventoried. Findings worth not re-deriving:

- **No `*_sv.yaml` registry file of any kind exists**, where `chandas_av.yaml`, `rishis_av.yaml`,
  `rishis_yv.yaml` and `devata_ascriptions_av.yaml` all do. The Samavedic absence is structural
  at the registry level, not just the graph level.
- `data/knowledge/` holds 4 run directories. There is **no** `samaveda_*` run of any kind, and
  `*_lexical_v1` exists for the Rigveda only. `find data -iname '*samaveda*'` under
  `data/knowledge`, `data/domain`, `data/gold` and `data/product` returns nothing.
- `data/domain/vedagraph_domain_v2/veda_coverage_v3.json` declares 13 dimensions and holds 14
  work-by-dimension cells at `covered_mantras: 0`, each with a typed `ABSENT_FROM_SOURCE`
  reason. **These reasons are the single best source for whether a per-Veda zero is source-
  blocked or unfinished**, and they are what reclassified `GAP-TRANSLATION-001` and
  `GAP-ATTRIBUTION-004` from plain omissions into source-blocked gaps. Read this file before
  assuming any SV gap is merely unfinished. Note that `audio` is not one of its 13 dimensions,
  so the audio layer is absent from the coverage model rather than reported as zero in it.
- 12 of 52 files in `schemas/` have zero data instances anywhere. 5 of those 12 are the
  `semantic_gold_*` family, which is `GAP-QUALITY-001` seen from the schema side.
- 5 of 18 declared `source_id` values in `sources.yaml` occur in no ingested data file:
  `SANSKRIT_LIBRARY`, `DCS`, `WIKIMEDIA_COMMONS`, `VEDAVANI`, `ARCHIVE_ORG`. Three of the five
  are audio sources, which is why `GAP-AUDIO-002` records declared-but-unexplored routes.
  A sixth, `WIKISOURCE_GRIFFITH_SV`, exists as a `:Source` node in the graph and feeds zero
  `:Translation` nodes.

**Tests and benchmarks.** 48 Python skip sites and 2 Playwright skips were classified. **No
`xfail` marker remains anywhere**, and there is no `.only`, `.fixme`, `it.skip` or
`describe.skip` in `frontend/tests/`. Most skips are infrastructure gates (`VEDAGRAPH_LIVE_NEO4J`,
absent API keys, gitignored source snapshots) and are **not** data gaps; do not re-triage them.
The ones that are data-relevant are artifact-not-built gates, and the most useful single skip
is `tests/api/test_graph.py:805-814`, a self-closing sentinel for the 256 missing `parallel_id`
values that has not yet fired (`GAP-CROSS_VEDA-003`).

**Deliberately excluded from this census.** The following are real open items but are not data
completeness, and registering them would dilute the registry: `PERF_BACKLOG_01` (Ask latency is
provider-bound at 29.7-248.7s, of which at most 1.2s is VedaGraph), `UI_BL_01` (two design
tokens converged in the light theme), the `ASK_BL_*` family other than the retrieval defects
folded into `GAP-PRODUCT_SURFACE-004`, `/sources` page height at 390px, `world.bin`
precompression, the 710 K prefetch, and eight pre-existing `ruff` style findings. Also excluded:
the `ASK_BL_*` items already closed (`ASK_BL_06`, `07`, `09`, `11`, `TEST_BL_01`) and the
`MISLEADING = 0` gate, which is met.

**Not resolved, and flagged rather than guessed.** Two figures in existing documents do not
reproduce against the live graph and I could not determine which is right:

- Benchmark Q67 states "17 assertions carry three typed role edges out of 4,865". After
  verifying the edge directions first (all three point outward from `:SemanticAssertion`), the
  measured count of assertions carrying agent, predicate and target together is **0**, not 17.
  Recorded as measured in `GAP-SEMANTICS-003` with the discrepancy stated.
- The scorecard states "30 of 33 GROUP deities have no components"; the measurement is **33 of
  33**. Recorded as measured in `GAP-COMMUNITIES-002`.

Neither changes the classification, and in both cases the live measurement is the more
pessimistic one, so no gap is understated by the discrepancy.



## R5 correction — three census claims here are superseded

This file was the one document in this directory that R5's first stale-claim sweep missed.
Three of its claims are now false, and two were false before R5 touched anything.

**"the role slots can only point at deities"** (§ on the semantic layer). They can and do
point elsewhere. The declared RANGE of `ASSERTION_AGENT` and `ASSERTION_TARGET` has admitted
`{Devata, DomainEntity}` throughout; only the population was narrow, and
`GAP-SEMANTICS-003` populated it in R5 by projecting the `:RoleFiller` `REFERS_TO`
resolution that already existed one hop away. Measured now: **2,660** agents of which 58
non-deity, **918** targets of which 103 non-deity.

**"Not one of the 4,865 assertions carries a complete agent-predicate-target triple"** is
wrong twice over. **10** assertions now carry all three slots, and the denominator was
already wrong when written: `:SemanticAssertion` is **35,131** nodes, not 4,865. The 4,865
was the population before R1's identity repair restored the other 30,266, and the same
mis-denominator is recorded and corrected in `layer_figures.py`.

**"The Samaveda has no translation at all: 0 of 1,844 mantras carry HAS_TRANSLATION"** is
false as a statement about the edge and true as a statement about the thing that matters.
**173** Samavedic mantras carry a `HAS_TRANSLATION` edge. Every one of the 173 is a
`REUSED_RENDERING`: Griffith's Rigvedic English attached to a Samavedic verse whose Sanskrit
is verified character-identical. So the Samaveda's INDEPENDENT English translation count is
**0**, which is what this sentence was reaching for — and the corrected form of it is that
0 of 1,844 Samavedic verses have been translated as Samavedic verses, while 173 display
another corpus's rendering and say so. `GAP-TRANSLATION-004` types this per verse:
`REUSED_RENDERING` is a terminal state of its own and is excluded from
`INDEPENDENT_ENGLISH_STATES`, so no total can quietly report 173 as Samaveda English.
