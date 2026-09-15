# Attribution — ṛṣi, devatā, chandas, entity coverage

**Agent 8, Wave 1** · branch `phase-data-completeness-v2` · baseline commit `564d43f`
**Staging artifact**: `data/staging/attribution/` — validator **PASS**, every check at 100% coverage
**Graph**: read-only throughout. Re-counted after the run at 108,779 nodes / 265,295 relationships, unchanged.

---

## 0. What this wave found, in one page

**The Atharvavedic builder was already fully run, and it was discarding the best data on the page.** Re-running `scripts/build_atharvaveda_anukramani.py --dry-run` reproduced all 3,252 assertions exactly, and every one of them is already in the graph. Reconnaissance's "the devatā half is not ingested" is stale — the deity half landed on 2026-09-09 and is the 4,160 mantras Wave 0 confirmed. So the expected yield from *running what exists* was zero.

The real yield was in what the builder throws away. Its tail loop carries this line:

```python
if not value or not METRE_STEM.search(value):
    continue  # a per-verse devatā exception, not a metre
```

It identifies per-verse **deity** exceptions, drops them, and does not record the drop — so the discarded population is invisible in the provenance sidecar too. Whitney's brackets address individual verses by deity constantly:

> `Bṛhaddiva Atharvan.—ekādaçakam. āgneyam: 1, 2. agnim astāut; 3, 4. devān; 5. draviṇodādiprārthanam; 6, 9, 10. vāiçvadevī; 7. sāumī; 8, 11. āindrī. trāiṣṭubham: 2. bhurij; 10. virāḍjagatī.`

Eleven verses, seven distinct deity ascriptions, none of it in the graph. Recovering that branch takes Atharvavedic **source-explicit** deity attribution from **0 mantras to 83**.

**A second defect strands 383 verses of source-explicit metre on their hymn.** The builder emits 85 metre assertions at `MANTRA_RANGE` scope, keyed to the hymn's `passage_id` with `start_sequence`/`end_sequence` beside it. The import dropped the bounds and created the edge on the hymn. 85 rows became **77 edges** — `MERGE` collapsed eight onto an existing `(hymn, metre)` pair — and not one of the 394 verse slots the source addresses received anything. Exactly the rows-sent-versus-rows-landed failure the contract warns about.

**The five "never assessed" Atharvavedic hymns are all assessed and typed.** The builder reports AVS 2.20–2.23 and 10.5 as having no bracket. All five were read on the page. Four are the tradition's own back-reference: Whitney prints no bracket for ii.20–23 and says so — *"For the Anukr. descriptions of the meter, and for the use by Kāuç., see under hymn 19."* The fifth, AVS 10.5, does have a bracket, but the Anukramaṇī divides the hymn into four parts ascribed to **different authors**, and it sits in a different template wrapper. None is a parser defect and none is an unknown.

**The 427-unresolved-seer figure is right and it is not a gap.** 421 of the 427 already carry a stated reason for having no family; **6** are unresolved for an unresolved reason.

---

## 1. Coverage before and after, with the source-explicit split

Mantra scope, all four Vedas. **The "has a value" column is the sum of the first two, and reporting only that sum is the misreading this table exists to prevent.**

### Devatā — read *both* predicates or under-report by 4,160

| Veda | mantras | SOURCE_EXPLICIT | DERIVED | has a value | assessed, absent | never assessed |
|---|--:|--:|--:|--:|--:|--:|
| RV | 10,552 | **2,223** (21%) | 8,329 | 10,552 (100%) | 0 | 0 |
| SV | 1,844 | 0 | 0 | 0 | 0 | **1,844** |
| YV | 1,975 | 0 | 0 | 0 | 0 | **1,975** |
| AV | 5,839 | **0 → 83** | 4,160 | 4,160 → 4,193 | 721 | 958 |

RV runs through `HAS_DEVATA` → `:Devata`; AV through `HAS_DEVATA_ASCRIPTION` → `:DevataAscription`. Counting only the first reports the Atharvaveda as having no dedication at all, which is the error the lead's own baseline made. **Unmodelled dedication: 5,498 → 5,465.**

Rigvedic dedication is 100% complete and **79% of it is inheritance** — 8,329 of 10,552 are a sūkta-wide value read down onto a verse. Atharvavedic dedication was **100% inheritance** before this artifact.

### Chandas

| Veda | mantras | SOURCE_EXPLICIT | DERIVED | has a value | assessed, absent | never assessed |
|---|--:|--:|--:|--:|--:|--:|
| RV | 10,552 | 4,242 (40%) | 6,276 | 10,518 (99.7%) | 34 | 0 |
| SV | 1,844 | 0 | 0 | 0 | 0 | **1,844** |
| YV | 1,975 | 0 | 0 | 0 | 0 | **1,975** |
| AV | 5,839 | **1,588 → 1,963** | 2,494 | 4,082 → 4,199 | 799 | 958 |

**Metre gap: 5,610 → 5,493.** Of the 383 verses that gain a verse-level metre, 117 had no metre value at all, 258 upgrade from inherited to source-stated, and 8 already carried a verse-level value.

### Ṛṣi

| Veda | mantras | SOURCE_EXPLICIT | DERIVED | has a value | assessed, absent | never assessed |
|---|--:|--:|--:|--:|--:|--:|
| RV | 10,552 | 467 (4%) | 10,067 | 10,534 (99.8%) | 18 | 0 |
| SV | 1,844 | 0 | 0 | 0 | 0 | **1,844** |
| YV | 1,975 | **1,960** (99.2%) | 0 | 1,960 | 15 | 0 |
| AV | 5,839 | 0 | 4,542 | 4,542 (78%) | 339 | 958 |

The Yajurvedic ṛṣi layer is the only non-Rigvedic layer that is wholly source-explicit at verse level, and the reason is worth naming because it decides the Yajurvedic verdict below: its source, the Wikisource `ऋषिसूची`, prints **explicit numeric ranges** (`अत्रिः ८.१५–२२, २४-३०`). Rigvedic ṛṣi, by contrast, is 96% inheritance — the weakest source-explicit rate of any populated cell in the matrix.

### Container scope

Reported separately, because the first matrix this run produced counted 1,606 containers as missing attribution, which would have inflated every gap. Three different facts were being conflated:

- **568 containers are `NOT_APPLICABLE`.** No anukramaṇī ascribes a deity, a seer or a metre to a maṇḍala, a kāṇḍa, a prapāṭhaka or an adhyāya. 10 RV maṇḍalas, 20 AV kāṇḍas, 40 YV sections, 498 SV structural containers.
- **1,028 Rigvedic hymns are empty by our own ingest design.** The WSC2023 index *does* state the triad at sūkta scope; the projection wrote it onto the sūkta's mantras instead. The source is not silent at those keys — our graph is.
- **AV hymns are genuinely populated at hymn scope**, which is the source's native granularity: 505 of 731 carry a deity ascription, 542 a seer, 465 a metre, and 143 are kāṇḍa 20.

---

## 2. The Samavedic sāman-scope decision

**Decision: Samavedic attribution is asserted at *sāman* (gāna-rendering) scope. No verse-level Samavedic attribution row is staged, and 16 extracted triads are recorded as `unresolved` rather than projected.**

Three independent blockers, each measured, each alone sufficient.

**1. Scope — and it is worse than a widening.** Reconnaissance warned that projecting a sāman's triad onto its yoni-verse is a widening. Sampling the pages showed it is also **multi-valued and self-contradictory**. One page, `सामवेदः/कौथुमीया/संहिता/ग्रामगेयः/प्रपाठकः १७/सफम्(पवस्व)`, prints five gāna renderings of ārcika **578**, four of which carry a triad, and the four disagree:

| rendering | printed triad | ṛṣi | chandas | devatā |
|---|---|---|---|---|
| 578.1 | `वासिष्ठम् । वसिष्ठः ककुप् सोमः` | vasiṣṭha | kakup | **soma** |
| 578.2 | `सफे द्वे । द्वयोर्देवाः ककुप् इन्द्रसोमौ` | devāḥ of the two | kakup | **indra-soma** |
| 578.3 | *no triad printed* | — | — | — |
| 578.4 | `वासिष्ठम् । वसिष्ठः ककुप् सोमेन्द्रौ` | vasiṣṭha | kakup | **soma-indra** |
| 578.5 | `सफम् । देवाः ककुप् सोमः` | devāḥ | kakup | **soma** |

One ārcika verse, four deity values, three seer values, and one rendering that states nothing. A verse-level projection would have to pick one and could not say why.

**2. Identity.** `VG:WORK:SV:KAU`'s own `scope` property states verbatim that the gāna collections *"are a PARALLEL AND LARGER body (roughly 2,639 gānas against 1,875 ārcika verses) which requires its own work_id."* No such Work exists, no `:Saman` label exists, and the contract requires every row's `canonical_key` to resolve. A gāna-scoped claim has nowhere to land. The project had already settled this question in the Work scope; my job was to stop rather than to route around it.

**3. Join.** No Samavedic mantra carries a running ārcika number. The spine is `ARANYA` / `CHANDA` / `UTTARA` / `MAHANAMNYA` with dasati and verse; `keys(m)` on any SV mantra returns no running-number property. The gāna page's join key is exactly that running number (`[…/s/3fr ४६१]`, `५७८`), so even at sāman scope the number cannot be resolved to a canonical key until a running-number index is built over the 1,844 mantras **and** reconciled against the 1,844-vs-1,875 delta.

### A capacity correction to reconnaissance

Reconnaissance describes 726 gāna pages carrying the triads and leaves the fill rate unverified. I fetched a stratified sample of **33 pages** (seed 20260915; non-redirect, ≥2,000 bytes; 517 eligible), revision-pinned with the sha256 of each page's wikitext, in `proofs/sv_gana_page_sample.jsonl`. The inventory's `content_snapshotted` is `false` on all 733 rows, so these are the first 33 whose bytes exist locally.

Every triad found was on a **Grāmageya** or **Āraṇyakageya** page. All 16 sampled **Ūhagāna** and **Ūhyagāna** pages carried none. That is structurally expected — *ūha* means "modification", and the ūha/ūhya gānas are derived renderings of the grāmageya and āraṇyakageya sāmans, so they inherit rather than restate. **The attributable page population is about 276 (190 + 86), not 726.**

**I do not report a per-saman fill rate.** Automated triad detection over this wikitext produces false positives, because the gāna notation is delimited with the same daṇḍa pair as the triad: two of the seven ārcika numbers my detector reached were notation, not attribution. Reporting a ratio from a detector I can see to be wrong would be the "validator that silently skips" failure in a different costume. The 33 pinned pages are handed on so the next pass can measure it without refetching.

**What would unblock it**, in order: a gāna Work identity plus a `:Saman` node type (a schema decision, the lead's); a running-ārcika-number index over the 1,844 mantras; and the **Ārṣeya Brāhmaṇa** as the attributing authority rather than the gāna page — the gāna pages cite it directly (`आर्षेयब्रा. ४.१२.६` on the Yājñaturam page), which is the correct citation target for a seer claim.

---

## 3. Yajurvedic attribution: my verdict

**Verdict: `NOT_EXTRACTABLE_AT_SOURCE_EXPLICIT`. Kātyāyana's Sarvānukramaṇa-sūtra cannot yield verse-level devatā or chandas by machine, and I did not attempt it.**

The verdict rests on counts taken from the local snapshot (`data/raw/wikisource_sa/2026-09-07/91203256…php`, revid in `proofs/yv_katyayana_measurement.json`), not on reconnaissance's characterisation. It is the **correct recension** — Mādhyandina, matching `VG:WORK:YV:VSM` — so this is not a recension mismatch.

| measurement | value |
|---|--:|
| characters of wikitext | 49,708 |
| numbered sūtra terminators | 168 |
| section headings | 0 |
| `अध्याय` / `अनुवाक` markers | 0 / 0 |
| **numeric mantra coordinates** | **0** |
| `लिङ्गोक्त` occurrences | **102** |
| `अनादिष्ट` occurrences | 1 |

Three obstacles, and the first is decisive:

1. **Zero numeric coordinates in 49,708 characters.** The Yajurvedic ṛṣi layer parsed *because* its source prints `अत्रिः ८.१५–२२`. Kātyāyana prints nothing of the kind: it addresses mantras by **pratīka** (incipit) — `इषेत्वा शाखानुष्टुब्विनियोगः`, `यो अग्न इदमाग्नेये`, `कस्त्वा प्राजापत्यं`. Joining that to our 1,975 keys means sandhi-splitting a continuous stream and matching incipits, which is an interpretive act, not a parse.
2. **102 liṅgokta deferrals.** In 102 places the sūtra does not name the deity; it says the deity is stated by the characteristic mark *in the mantra*. Resolving those means reading the mantra and judging.
3. **No field delimiters.** ṛṣi, devatā and chandas run together in sandhi-fused prose, so even a correctly segmented sūtra does not say which slot a token occupies.

Anything extracted would be `INTERPRETIVE_CLAIM` at best and `UNVERIFIED` confidence — staged, never imported. No LLM was used on this source and none may be.

**Three constraints the source imposes on any future ingest**, taken from its own opening sūtra:

- **chandas is legitimately asserted-absent** for many yajus: *yajuṣāṃ aniyatākṣaratvād ekeṣāṃ chando na vidyate*. That absence needs a reason code. It must not be ingested as unknown and it must not be filled.
- **the devatā co-domain includes ritual implements** as *pratimābhūta* — the sūtra names *anas* (cart), *śākhā*, *ukhā* (pot), *kapāla* (potsherd), *idhma*, *ulūkhala* (mortar). A shared RV/YV devatā enum would be a modelling error, and **Agent 15 must not treat a Yajurvedic ritual implement as contamination.**
- **the tradition keeps its own register of non-assignments**, *anādiṣṭa-devatādayaḥ*. A pipeline must reproduce those gaps, not fill them.

**The one lead that would change the verdict, and which I did not check.** Reconnaissance names it as unchecked and it remains unchecked: printed Indian editions commonly head each mantra with ऋषिः / देवता / छन्दः / स्वरः, with Weber 1852 (`in.ernet.dli.2015.345056`) and the Uvaṭa+Mahīdhara printings as candidates. It is a page-image inspection of a scan, not a fetch, and it is out of this agent's reach. **If one of them does print the apparatus per mantra it is the fastest route to Yajurvedic devatā and chandas** — with the caveat that a printed edition's headings are an *editorial* apparatus and not the Sarvānukramaṇī, the two can disagree, and whichever is used must be recorded as the attributing authority.

---

## 4. The assessed set, and why it is the main deliverable

The graph cannot distinguish *examined and the source says nothing* from *never examined*, for any dimension, because run provenance is written onto produced edges and never onto the passage examined. Section 32 requires 100% assessed coverage on optional dimensions, so that number was unreportable.

`rows.jsonl` enumerates it: one row per `:Passage`, 22,537 of them, with all three dimensions typed. Five states, and the boundary between the last three is the whole point:

| state | meaning |
|---|---|
`SOURCE_EXPLICIT_PRESENT` | a value the source states at *this* granularity
`DERIVED_PRESENT` | a value inherited from a container — not stated here
`ASSESSED_SOURCE_ABSENT` | examined; the source states nothing. **A measured zero.**
`NEVER_ASSESSED` | no index covering this passage has been read. **Unknown, not zero.**
`NOT_APPLICABLE_AT_THIS_GRANULARITY` | no anukramaṇī ascribes attribution to this level

Absence carries a code from a closed vocabulary of 14, in `proofs/absence_reason_codes.json`; the generator raises on a code not in it rather than letting free text onto a row. The heaviest classes:

| cells | code |
|--:|---|
| 5,532 | `SV_ATTRIBUTION_IS_AT_SAMAN_SCOPE_NOT_VERSE_SCOPE` — 1,844 mantras × 3 |
| 3,950 | `YV_KATYAYANA_IS_NOT_MECHANICALLY_RESOLVABLE` — 1,975 × devatā and chandas |
| 3,303 | `ABSENT_AT_SOURCE_KANDA_20` — (958 mantras + 143 hymns) × 3 |
| 3,084 | `CONTAINER_EMPTY_BY_INGEST_DESIGN` — 1,028 Rigvedic hymns × 3 |
| 1,704 | `SOURCE_DOES_NOT_ASSERT_AT_THIS_GRANULARITY` — 568 containers × 3 |
| 1,502 | `SOURCE_STATES_NO_{DEVATA,RSI,DEFAULT_METRE}_FOR_THIS_HYMN` |
| 384 | `BRACKET_REFUSED_BY_ALIGNMENT_GATE` — 128 mantras-and-hymns × 3 |
| 153 | `SOURCE_MULTI_PART_ASCRIPTION_OUTSIDE_THE_PARSED_ANCHOR` — AVS 10.5 |
| 72 | `SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED` — AVS 2.20–2.23 |
| 67 | `INDEX_READ…BUT_IT_STATES_NOTHING_AT_THIS_KEY` — RV 52, YV 15 |

Every cell of the 67,611 is accounted for: 14 codes are declared, 12 are used, and the two unused ones (`HYMN_ABSENT_…`, `BRACKET_PARSED_BUT_NO_EDGE_LANDED_…`) are retained because each names a state the next run could reach. The second is worth watching: it is the only absence class here that would indicate a defect on our side rather than a silence in the source, and it is currently **0**.

`edge_count` stays present even when `null`, because a null population is the campaign's signal for unknown and dropping it would let a consumer read the absence as a zero.

### Entity and deity matrices

`proofs/per_veda_attribution_matrix.json` carries the mantra-scope and container-scope matrices above. For the wider entity dimensions, measured per Veda so that no page reports a corpus as both in scope and uncovered:

| dimension | RV | SV | YV | AV |
|---|--:|--:|--:|--:|
| `MENTIONS_DEVATA` (mantras) | 7,099 | 1,035 | 1,167 | 2,616 |
| `MENTIONS_ENTITY` | 8,143 | 1,306 | 1,358 | 4,292 |
| `ABOUT_CONCEPT` | 7,968 | 1,267 | 1,238 | 3,785 |
| `USES_FORMULA` | 5,103 | 1,311 | 1,214 | 2,946 |
| `HAS_SEMANTIC_ASSERTION` | 2,542 | **0** | **0** | **0** |
| `USED_FOR_RITE` | 20 | **0** | 3 | 490 |
| `MENTIONS_LEMMA` | 6,560 | **0** | **0** | **0** |

**The `MENTIONS_LEMMA` row carries Agent 1's warning, not a morphology layer.** 6,560 is arithmetically exact and invites the reader to infer 62% morphological coverage of the Rigveda. The layer reaches **39 distinct lemmas, all theonyms**, and 9,992 of 10,031 `:Lemma` nodes are isolated. It is a theonym mention index under a lemma layer's name. Repeated here because this is the third report to print the figure and the first two printed it without the sentence.

**`MENTIONS_DEVATA` is not dedication.** 2,616 Atharvavedic mantras name a deity; 4,160 are dedicated to one; the two sets are not the same set and neither is a proxy for the other. The Samaveda and Yajurveda have 1,035 and 1,167 mantras that *mention* a deity and **zero** that record a dedication — which is precisely the shape that invites a false inference, and the reason the census row keeps mention and dedication in different cells.

---

## 5. The two stale live claims, closed with data

Proof in `proofs/stale_claim_disproofs.json`. **No product copy was edited — that is the lead's job in Wave 3.**

### `GAP-ATTRIBUTION-003` — DISPROVEN

A live API caveat states the Atharvaveda carries no Anukramaṇī deity ascription.

```
MATCH (m:Mantra {veda:'AV'})-[r:HAS_DEVATA_ASCRIPTION]->(d:DevataAscription)
RETURN count(DISTINCT m), count(r), count(DISTINCT d)
  -> 4160 mantras, 4816 edges, 324 descriptors
```

Plus 569 edges over 505 hymns at hymn scope. Provenance is `traditional_metadata.jsonl`, regenerated 2026-09-15 and byte-identical.

**The correction that still belongs on the caveat.** The honest replacement is neither "no ascription" nor "4,160 mantras have a deity", but: *the Atharvavedic deity layer covers 4,160 of 5,839 mantras, and before this artifact every one of them was a hymn-scope label read down onto its verses.* Removing the caveat without that sentence swaps an understatement for an overstatement.

**The same stale claim is also served from a node property, which is why the sweep missed it.** All 214 `:Devata` nodes carry `attribution_scope: ["RV"]` beside an `attribution_scope_note` reading *"The Anukramaṇī attribution layer covers the Rigveda only. A zero for SV, YV or AV means that corpus has no attribution layer, NOT that the deity is absent from it."* That sentence is true of the `:Devata` **node** and false of the **corpus**, and a reader cannot tell which is meant. Canonical node property; only the lead may write it.

### `GAP-ATTRIBUTION-008` — DISPROVEN, and the gap figure needs correcting twice

`RishiFamily` is reported as 0 nodes. It is **87 nodes, 305 edges, 302 seers resolved** of 729.

The "729 unresolved" figure is wrong — 729 is the node count. The **427** figure is arithmetically right and it is not a gap, because the layer already records *why* for every one of them:

| count | `is_seer` | `family_assignment_class` |
|--:|:--|:--|
| 170 | true | `NO_PATRONYMIC_STATED` |
| **113** | **false** | `NON_SEER_ASCRIPTION` — not a seer at all |
| 69 | true | `EPONYM_WITHOUT_STATED_PATRONYMIC` |
| 45 | true | `THEONYMIC_DESCENT` |
| 12 | true | `COLLECTIVE_LINEAGE_COMPOUND` |
| 8 | true | `TITULAR_NOT_DESCENT` |
| **5** | true | `SOURCE_SPELLING_OUTSIDE_TABLE` |
| 3 | true | `KINSHIP_NOT_DESCENT` |
| **1** | true | `ETYMON_UNCERTAIN` |
| 1 | true | `MYTHIC_DESCENT` |

**Report three numbers, not one: 427 lack a family edge; 421 lack one for a stated reason; 6 lack one for an unresolved reason.**

---

## 6. Contamination in the eligible deity population

`proofs/deity_population_contamination.json`. Exclusions are taken from each node's own curated `structure` property, not from a name heuristic, so the list is reproducible and every row carries the curator's reason. **Agent 15 needs this.**

**29 of 214 `:Devata` nodes are not deities, and they carry 171 dedications between them.**

- **22 `structure: HUMAN`** — human patrons and persons: *asamāti* (5 dedications), *asaṅga* (5), *bṛbus takṣan* "Bṛbu the carpenter" (3), *rathavīti dārbhya* (3), *maitrātithir upamaśravas* (4), *purūravas* (9), *keśin* (8), and 15 more.
- **7 `structure: PATRON_PRAISE`** — dānastuti gift-praise labels, e.g. *adhyetṛstuti* "praise of the reciter", whose own curation note reads *"PATRON_PRAISE is withheld because no patron and no gift are named; this is praise of a reciter."*

**42 `ABSTRACT` / `UNSPECIFIED` labels are flagged and NOT excluded.** An abstract noun in the devatā slot is not automatically contamination — Śraddhā, Manyu and Vāc are abstractions and genuine deities; *abhiśāpa* "the curse" is not. That is a curation judgement and this agent does not make it silently. The list is handed over with each node's own `curation_note`.

**113 of the 729 `:Rishi` nodes are marked `is_seer=false` by the layer itself** — 58 deities, 21 abstractions, 13 mythic beings, 11 deity groups, 5 plants or animals, 3 collectives, 2 objects. Correctly typed, and not an unresolved-seer gap.

**17 `:Chandas` entities carrying 20 edges are not metre names.** They are un-split bracket fragments where a per-verse *deity* exception ran into the metre list — `mantroktadevatyā. anuṣṭubham: 1. bhurik triṣṭubh`, `rāudryāu: 2. anuṣṭubh`. The builder names this residual in its own docstring. The deity halves are now staged as verse-scope ascriptions; the 17 fused entities still stand in the metre namespace and are the lead's to retire.

---

## 7. Entity aggregates: an absent property and a measured zero render alike

`proofs/entity_aggregate_gaps.json`. The brief asked that no entity page read as "not yet modelled" because an aggregate was never computed. Two different failures, and the second is the dangerous one.

**No aggregate exists at all.** `0 of 214` `:Devata` nodes and `0 of 575` `:Chandas` nodes carry an `occurrence_count` property, against 10,558 `HAS_DEVATA` and 16,331 `HAS_CHANDAS` edges. Every deity page and every metre page reads null. Two aggregates are wanted here and neither exists — **dedications** and **mentions** — and they must not be one number.

**An aggregate exists and is written to two disagreeing conventions.** All 729 `:Rishi` nodes carry `occurrence_count`:

| namespace | nodes | mantra-level edges | container-level edges | stored total | convention |
|---|--:|--:|--:|--:|---|
| `AV_WHITNEY_ANUKRAMANI` | 134 | 4,542 | 542 | 542 | **container** |
| `YV_VSM_RSISUCI` | 228 | 2,240 | 0 | 2,240 | **mantra** |
| `RV_WSC2023_ANUKRAMANI` | 367 | 10,565 | 0 | **0** | container — trivially |

The Rigvedic zero is *correct* under the Atharvavedic convention, because the Rigvedic layer has no container-level `HAS_RISHI` edge at all. **That is what makes it dangerous.** Every Rigvedic seer page reads "0 occurrences" over a complete 10,565-edge layer, and no figure in the row is wrong. This is the project's own recorded lesson — the attribution axis written by three mechanisms that disagreed — recurring on a count.

The fix is not "recompute `occurrence_count`". One property cannot carry a container-scope count for one Veda and a mantra-scope count for another and be read safely by a single UI. Either the scope travels with the number or there are two properties. Schema decision; the lead's.

---

## 8. The artifact

```
data/staging/attribution/
  manifest.json                          candidates 23,037 = 23,003 + 18 + 16
  rows.jsonl                             23,003 rows, 35.8 MB
  rejected.jsonl                         18, every one with a reason
  sources.jsonl                          3
  build_attribution_staging.py           regenerates rows/rejected/sources/manifest
  build_proofs.py                        regenerates proofs/ (run first)
  proofs/
    per_veda_attribution_matrix.json     mantra + container matrices, absence histogram
    absence_reason_codes.json            the closed vocabulary of 14
    sv_saman_scope_decision.json         the decision and its three blockers
    sv_gana_page_sample.jsonl            33 revision-pinned gana pages, sha256 each
    sv_saman_attribution_unresolved.jsonl  16 triads with nowhere to land
    yv_katyayana_measurement.json        the Yajurvedic verdict, measured
    deity_population_contamination.json  exclusions, flags, namespace contamination
    stale_claim_disproofs.json           ATTRIBUTION-003 and -008
    entity_aggregate_gaps.json           what no page can compute, and what it miscomputes
    generation_stats.json
```

Three row families, each with its own `source_id` so `(canonical_key, source_id)` stays unique per dimension:

| source_id | rows | evidence_layer | confidence |
|---|--:|---|---|
| `VG_ATTRIBUTION_CENSUS_2026_09_15` | 22,537 | `DETERMINISTIC_DERIVED` | `EXACT` |
| `WHITNEY_AV_PERVERSE_DEVATA` | 83 | `SOURCE_EXPLICIT` | `EXACT` |
| `WHITNEY_AV_PERVERSE_CHANDAS` | 383 | `SOURCE_EXPLICIT` | `EXACT` |

**Zero rows at `PROBABLE` or `UNVERIFIED`.** Everything staged is importable, and everything not importable was not staged — it is in `proofs/` as a typed blocker.

### Validator

```
$ .venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/attribution --graph

  attribution (agent 8): 23003 row(s), 3 source(s)
  [OK] manifest.counts_balance · manifest.file_checksums · row.required_fields
  [OK] row.evidence_layer_closed · row.quality_class_closed · row.mapping_confidence_closed
  [OK] row.source_id_resolves · row.source_locator_substantive · row.recension_verified_present
  [OK] row.no_zero_for_unknown · row.no_duplicate_key_source · manifest.accepted_matches_rows
  [OK] rejected.has_reason · graph.canonical_key_resolves (23003/23003)
  [OK] graph.veda_agrees (22537/22537)

  PASS. Every check evaluated every eligible row and found no defect.
```

### QA — 3 defects found by reading every accepted row, all fixed

`qa.human_reviewed` is **0**. This is model adjudication by claude-opus-5 acting as Agent 8, and section 26 forbids calling it gold. Every accepted deity row is printed verbatim beside its source bracket, so a human can re-check all 83 in an hour.

All 97 accepted deity rows were read against their printed brackets, twice. Three false positives, each a different failure mode:

1. **`virāt pathyābrhatī`** (AVS 8.1.8) stood as a deity. It is the metre *pathyā bṛhatī* printed without the vowel mark under the r, so neither the builder's stem list nor an exact lookup against the metre registry caught it. Fixed by folding combining marks before the registry lookup — *enumerate the field's value space, and normalise before comparing it.*
2. **`i-p`** (AVS 2.16.2) stood as a deity. It is an OCR reading of the pāda address `1-p`, and my digits-only address class let it through. Fixed by admitting `i` and `l`.
3. **`mārtvyaḥ`** (AVS 12.2, verses 21–33) stood as a deity across thirteen verses. Every filter passed, and Lanman's own note reads the Anukramaṇī's *mārtvī* as *"an ascription of authorship"*. Hand-refused and recorded as a lead for a per-verse **ṛṣi** claim instead.

The third is the one worth keeping. The first two are shape errors a better regex catches. The third was only catchable by reading what the editor said about his own text, and it is the failure mode with no mechanical guard: the bracket's slots are positional, and a patronymic standing where a deity usually stands looks exactly like a deity.

---

## 9. What I could not close, and why

**Named as unlocks with their populations, not worked around.**

1. **Kāṇḍa 20 — 143 hymns, 958 mantras.** Absent from this index at source; Whitney excluded it. No parsing reaches it. A different source is required, and those mantras' attribution is genuinely unknown.
2. **Six multi-part ascriptions — 66 mantras.** AVS 7.45, 7.54, 7.68, 7.72, 7.76 and 10.5 each print two or more part-scoped ascriptions in one bracket. Genuinely recoverable at `MANTRA_RANGE` scope — the ranges are printed (`A. (vss. 1-24)`, `1-2. Caṁtāti`) — and they need their own grammar. Not attempted, because a half-built grammar over six brackets would put one hymn's ṛṣi on another's verses.
3. **17 gate-refused hymns.** The builder's stated-verse-count gate refuses their bracket entirely. For the kāṇḍa 15 and 16 paryāya hymns the mismatch is systematic — the source counts paryāya subsections where our corpus counts verses (28 against 4, 26 against 9) — so it is a scope mismatch, not a numbering slip, and relaxing the gate would not recover it. Typed per mantra in the census.
4. **Tail-grammar recall.** The tail splits on `;` only, so where two per-verse statements are separated by a bare period inside one segment, only the first is reached (AVS 6.40 verse 3, `āindrī`, is the clear case). One comma-separated three-way list was refused whole (AVS 6.10, covering 3 verses) because the pairing cannot be recovered without guessing. These are misses, not wrong values, and I would rather report the recall limit than claim a completeness I did not measure.
5. **Samavedic attribution at any scope** — three blockers above, none of them mine to clear.
6. **Yajurvedic devatā and chandas** — not mechanically extractable, and the one lead that would change that (a printed edition's per-mantra apparatus) needs a page-image inspection I cannot perform.
7. **The unread Samavedic `छन्दःपदम्` index page**, plus `स्तोभपदम्` and four `गानस्य सूची` pages. Eleven pages, titles verified by enumeration, contents still unread — reconnaissance called this the cheapest high-value check left in the Samavedic domain and it is still outstanding. My 33-page fetch went to the gāna pages because the scope question had to be settled before a fill rate could mean anything.
8. **The 17 fused `:Chandas` entities** and the `attribution_scope: ["RV"]` property on all 214 `:Devata` nodes are canonical writes. Proof supplied; the write is the lead's.

**One honest caution about the headline.** The Atharvavedic source-explicit deity figure moves from 0 to 83 mantras — 1.4% of the corpus, and 2.0% of the mantras that have any deity value at all. It is a qualitative change, because the layer went from *no verse-level deity statement exists* to *some do and here they are with their brackets*. It is not a coverage change. The Atharvavedic deity layer is still 98% inheritance, and the matrix says so in both columns.
