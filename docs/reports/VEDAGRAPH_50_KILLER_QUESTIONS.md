# VedaGraph — 50 Killer Questions: Answerability Baseline

**Purpose.** This is the driving deliverable of KNOWLEDGE MODEL V2. It fixes an honest, measured baseline of what the graph can and cannot answer today, so that later ontology work can be measured against it rather than asserted. Every classification below was checked against the live database, not inferred from the schema.

| Field | Value |
| --- | --- |
| Baseline date | 2026-09-09 |
| Commit | `bb27f3c` |
| Branch | `semantic-pilot-v1` |
| Database | `bolt://localhost:7687` (local Neo4j, GDS present — 423 procedures) |
| Graph size | 100,584 nodes / 212,336 relationships |
| Probes executed | 78 Cypher probes across the 50 questions |

## Summary

| Status | Count | Share |
| --- | --- | --- |
| ANSWERABLE_NOW | 4 | 8% |
| PARTIALLY_ANSWERABLE | 35 | 70% |
| NOT_ANSWERABLE | 11 | 22% |
| **Total** | **50** | **100%** |

The four ANSWERABLE_NOW questions (6, 8, 29, 50) are all served by the layers that were built deterministically with full evidence: the cross-Veda parallel/reuse layer, the formula layer, and the provenance vocabulary carried on enrichment edges. Every question that depends on *meaning* — deity function, ritual purpose, human concern, named entities — is at best partial.

## Classification rules used

To keep 50 verdicts consistent:

- **ANSWERABLE_NOW** — a single Cypher query returns a substantively useful, non-misleading result over the corpus the question names, with evidence or provenance attached.
- **PARTIALLY_ANSWERABLE** — a query returns usable rows, but a careful researcher must attach a stated caveat (wrong corpus scope, unknown recall, proxy dimension, tiny N).
- **NOT_ANSWERABLE** — there is no graph element that even proxies the dimension, or the only available proxy is the *wrong sense* of the concept and its rows would be read as an answer they are not.

Two rules follow from measurements made during this audit and are applied throughout:

1. **Any answer resting solely on `ABOUT_CONCEPT` is capped at PARTIALLY.** `ABOUT_CONCEPT` is hard-truncated at 4 edges per passage (`max(n) = 4`, `avg = 2.63`), 4,475 of 22,537 passages (19.9%) have zero concept edges, and 21,246 of 47,542 edges (44.7%) are English-translation-alias matches at `confidence = 0.42`. Recall is therefore unknown and all frequency or prominence claims built on it are unsound as absolute statements.
2. **Any answer resting on the LLM semantic pilot is capped at PARTIALLY.** All 736 pilot edges are `state = 'CANDIDATE'`, `trust = 'LLM_EXTRACTED'`, cover 363 distinct mantras (1.8% of 20,210), and are **Atharvaveda + Yajurveda only** (AV 321 edges / 157 mantras, YV 415 edges / 207 mantras) — not Rigvedic, contrary to the working assumption. The pilot is frozen.

---

## The 50 Questions

### 1. How does Indra's role differ across the four Vedas?

- **Status**: NOT_ANSWERABLE
- **Why**: `HAS_DEVATA` to `VG:DEVATA:INDRAH` returns 2,869 edges, all Rigveda. There is no Indra node reachable from any SV, YV or AV passage except through 222 `INVOKES` candidate edges, of which Indra holds 26 — and none of those are Samavedic. There is no Indra `Concept` node at all (probe returned 0 rows), so the cross-Veda concept layer offers no substitute.
- **Blocking gap**: knowledge layer is RV-only, so cross-Veda deity comparison has no SV/YV/AV side; and no deity-role/function dimension exists in any Veda.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'})
  RETURN p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  1 row: `RV 2869`. The SV/YV/AV rows the question requires do not exist.

### 2. Which Rishi families invoke Agni most?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The join works and returns plausible rows, but it returns *individuals*, not families. `Rishi` has exactly three properties (`entity_key`, `preferred_label`, `occurrence_count`) and `preferred_label` bundles patronymic and personal name into one inflected string — `gāthino viśvāmitraḥ`, `bārhaspatyo bharadvājaḥ`. Grouping by family requires parsing Sanskrit patronymics out of a display string. `occurrence_count` is 0 on all 367 Rishi nodes (dead property).
- **Blocking gap**: no `RishiFamily`/gotra node and no `MEMBER_OF_FAMILY` edge; 95.5% of `HAS_RISHI` is `SUKTA_WIDE` inheritance.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_RISHI]->(r:Rishi), (m)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})
  RETURN r.preferred_label AS rishi, count(DISTINCT m) AS mantras ORDER BY mantras DESC LIMIT 5
  ```
  Top rows: `gāthino viśvāmitraḥ 179`, `bārhaspatyo bharadvājaḥ 173`, `gautamo vāmadevaḥ 171`, `maitrāvaruṇirvasiṣṭhaḥ 140`, `śāktyaḥ parāśaraḥ 91`. These are the Viśvāmitra, Bharadvāja, Vāmadeva/Gotama and Vasiṣṭha family books read through individual seer names — the right answer is visible to a Sanskritist and invisible to a query.

### 3. Which concepts are most strongly associated with Varuna?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Co-occurrence of `HAS_DEVATA` and `ABOUT_CONCEPT` returns a recognisable Varuṇa profile, but N is tiny and the shape is partly an artefact of the concept cap. Varuṇa has only 95 mantras via `HAS_DEVATA`; the top concept, `kingship`, appears 20 times. `VG:DEVATA:VARUNAH` has zero `DEVATA_ASSOCIATED_WITH` edges, so the only deity-to-concept edge type in the graph does not cover him.
- **Blocking gap**: no `Devata`→`Concept` association layer with coverage (`DEVATA_ASSOCIATED_WITH` is 101 edges and is a *name-identity* mapping, not an association — see Q41); concept recall capped at 4/passage; RV-only.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:VARUNAH'}),
        (m)-[:ABOUT_CONCEPT]->(c:Concept)
  RETURN c.preferred_label_en AS concept, count(*) AS c ORDER BY c DESC LIMIT 6
  ```
  `kingship 20`, `heaven 14`, `praise 10`, `waters 10`, `earth 9`, `insight 8`. Note `ordinance 8` and `cosmic order 7` further down — the ṛta/dhárman association a scholar would expect ranks below `praise`, which is a liturgical artefact rather than a Varuṇa fact.

### 4. What offerings are associated with each deity?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The concept ontology contains exactly two `OFFERING` nodes — `oblation` (havis) and `priestly fee` (dakṣiṇā). Co-occurrence gives `agniḥ`/oblation 160, `indraḥ`/oblation 57, `indraḥ`/priestly fee 20. That is a two-column answer to a question about a rich offering repertoire (ghṛta, puroḍāśa, soma, paśu, dhānā). The typed `INVOLVES_OFFERING` edge exists but has 14 edges, and in 9 of the 14 the mantra has no deity attached at all.
- **Blocking gap**: no `Devata`→`Offering` edge; the `Offering` vocabulary is 2 items; `INVOLVES_OFFERING` is AV/YV candidate-only and its passages fall outside the RV-only deity layer, so the two halves of the question cannot be joined.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:INVOLVES_OFFERING]->(o:Concept)
  OPTIONAL MATCH (m)-[:HAS_DEVATA|INVOKES]->(d:Devata)
  RETURN m.canonical_citation AS cit, o.preferred_label_en AS off, d.preferred_label AS deity LIMIT 14
  ```
  14 rows; `deity` is `null` in 9 of them (e.g. `AVS 8.3.1 / clarified butter / null`).

### 5. Which rituals invoke both Agni and Indra?

- **Status**: NOT_ANSWERABLE
- **Why**: Two independent failures. There is no `Ritual` entity — `db.labels()` returns 14 labels and none is a rite; `RITUAL` exists only as a `node_type` value on 2 concepts (`sacrifice`, `soma pressing`). And the deity side returns nothing: **zero** mantras carry both `AGNIH` and `INDRAH`, because the Anukramaṇī encodes the joint invocation as a single opaque composite deity `VG:DEVATA:INDRAGNI` (117 mantras) that is never decomposed into its components.
- **Blocking gap**: no `Ritual`/`Rite` node; composite `Devata` nodes have no `COMPONENT_OF` decomposition (and `is_composite` is `false` on all 214 nodes including `indrāgnī` and `mitrāvaruṇau`, so the flag is wrong as well as unused).
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})
  MATCH (m)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'})
  RETURN count(DISTINCT m) AS c
  ```
  `0`. The same query restricted to mantras about `YAJNA-SACRIFICE` also returns `0`.

### 6. Which Rigvedic verses are reused in Samaveda?

- **Status**: ANSWERABLE_NOW
- **Why**: This is the graph's strongest layer. `REUSES_TEXT_FROM` is directional SV→RV, 1,684 edges linking 1,662 distinct SV verses to 1,421 distinct RV verses. 1,662 of 1,844 SV mantras (90.1%) have a Rigvedic link. Every edge carries `similarity`, `edit_ratio`, `lcs_ratio`, `token_jaccard`, `ngram_jaccard`, `match_level`, `method`, `trust = DETERMINISTIC_DERIVED`, and an `evidence` array holding both normalised strings with locators.
- **Blocking gap**: none for the question as asked. (Recall against the Bhāradvāja/Bṛhaddevatā concordances is unverified — there is no gold set — but the layer is self-documenting.)
- **Probe**:
  ```cypher
  MATCH (sv:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(rv:Passage {veda:'RV'})
  RETURN count(DISTINCT rv) AS rv_verses, count(DISTINCT sv) AS sv_verses, count(r) AS edges
  ```
  `rv_verses 1421, sv_verses 1662, edges 1684`. Sample: `SV ARANYA 1.5 → RV 9.97.58`, similarity 0.957.

### 7. How are those verses transformed?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: You can *measure* the transformation but not *name* it. The edge carries five numeric similarity metrics plus both texts, so a human can read the difference; and `match_level` gives a coarse three-way split. But there is no transformation taxonomy — no distinction between sāman-specific insertion, phonetic lengthening, word substitution, pada reordering or metrical adaptation.
- **Blocking gap**: no transformation typology on parallel edges; the categorical field that exists (`match_level`) is the empty string on 1,180 of 1,684 RV–SV reuse edges.
- **Probe**:
  ```cypher
  MATCH (:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(:Passage {veda:'RV'})
  RETURN r.match_level AS ml, count(*) AS c ORDER BY c DESC
  ```
  `'' 1180`, `SANDHI_INSENSITIVE 415`, `SCRIPT_FOLDED 89`. Similarity buckets: `identical 504`, `0.95–1.0 164`, `0.90–0.95 395`, `0.80–0.90 470`, `<0.80 151` — so 1,180 verses (70%) are demonstrably altered and the graph cannot say how.

### 8. Which formulas occur across multiple Vedas?

- **Status**: ANSWERABLE_NOW
- **Why**: 3,643 of 4,825 `Formula` nodes have `cross_veda = true`; each carries a `vedas` array, `veda_counts`, `occurrence_count`, `mantra_count`, `word_count`, `evidence` and `trust`. 229 formulas occur in all four Vedas. 22,686 `USES_FORMULA` edges cover all four corpora (RV 9,729 / AV 6,844 / YV 3,077 / SV 3,036).
- **Blocking gap**: none for the question as asked.
- **Probe**:
  ```cypher
  MATCH (f:Formula) WHERE size(f.vedas)=4
  RETURN f.display_form AS form, f.occurrence_count AS occ ORDER BY occ DESC LIMIT 5
  ```
  `pāta svastibhiḥ sadā naḥ 93`, `viśvā bhuvanā 60`, `parame vyoman 53`, `brahmaṇas pate 38`, `viśvā bhuvanāni 32`. Distribution over `vedas` combinations: `[RV,SV] 802`, `[RV,AV] 798`, `[RV,SV,AV] 550`, `[RV,YV,AV] 509`, `[RV,SV,YV,AV] 229`.

### 9. Which crops occur in each Veda?

- **Status**: NOT_ANSWERABLE
- **Why**: The concept ontology has no crop. `node_type IN ['PLANT','SUBSTANCE']` returns 8 nodes total: `plants`, `tree`, `food`, `clarified butter`, `gold`, `honey`, `milk`, `soma juice`. There is no yava (barley), vrīhi (rice), dhānā, tila, māṣa or godhūma. `OSADHI-PLANTS` is the generic herb concept with aliases `herb, herbs, plant, plants` — it does not name species.
- **Blocking gap**: no domain-specific agricultural vocabulary; more broadly, no taxonomic depth below the 89 generic concepts.
- **Probe**:
  ```cypher
  MATCH (c:Concept) WHERE c.node_type IN ['PLANT','SUBSTANCE'] RETURN c.concept_id, c.preferred_label_en
  ```
  8 rows, listed above. A query would answer `plants: AV 193, RV 124, YV 65, SV 4` — true, but not an answer to the question.

### 10. Which metals occur in each Veda?

- **Status**: NOT_ANSWERABLE
- **Why**: Exactly one metal exists as a concept: `VG:CONCEPT:HIRANYA-GOLD`. There is no `ayas` (iron/copper), no `loha`, no `rajata`, and no `METAL` node_type. A query returns rows, and that is precisely the danger: it would report "gold only", which is false for the corpus and would silently erase the ayas evidence that is central to Vedic material-culture argument.
- **Blocking gap**: no domain-specific material/metal vocabulary; no `Material` type in the 15-value `node_type` space.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept {concept_id:'VG:CONCEPT:HIRANYA-GOLD'})
  RETURN p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  `RV 190, AV 66, YV 35, SV 6`. Recorded here as a warning, not as an answer.

### 11. Which animals are associated with wealth?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Real, defensible rows come back — cattle and horse dominate exactly as the philology predicts — but from an inventory of five animals (`serpent`, `horse`, `cattle`, `livestock`, `bird`) with no goat, sheep, ox, dog, buffalo or ant. And `Concept.node_type='ANIMAL'` is a *property*, not a label, so the query cannot be written as `MATCH (:Animal)`.
- **Blocking gap**: 5-item animal vocabulary; `node_type` not projected as a Neo4j label; association is bare co-occurrence with no typed `SIGNIFIES_WEALTH` predicate.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(a:Concept) WHERE a.node_type='ANIMAL'
  MATCH (p)-[:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:VASU-WEALTH'})
  RETURN a.preferred_label_en AS animal, p.veda AS veda, count(*) AS c ORDER BY c DESC LIMIT 5
  ```
  `cattle/RV 87`, `horse/RV 79`, `cattle/AV 10`, `cattle/YV 8`, `horse/YV 5`.

### 12. Which deities are associated with healing?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The result is scholarly plausible — Aśvins first, then Waters, Rudra, Maruts — but the counts are single digits and the query only sees the Rigveda. The Atharvaveda, the healing Veda, contributes zero rows because it has no deity attribution: `BHESAJA-HEALING` has 59 AV passages and none of them can be joined to a deity.
- **Blocking gap**: knowledge layer is RV-only, so the Veda that actually answers this question has no deity side; no `Devata`→function/domain edge.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:BHESAJA-HEALING'}),
        (m)-[:HAS_DEVATA]->(d:Devata)
  RETURN d.preferred_label AS deity, count(*) AS c ORDER BY c DESC LIMIT 6
  ```
  `aśvinau 9`, `āpaḥ 6`, `viśvedevāḥ 5`, `rudraḥ 5`, `marutaḥ 3`, `agniḥ 2`. Total across all deities is 37 — for a question a Vedicist would answer with hundreds of passages.

### 13. Which Atharvaveda passages concern marriage?

- **Status**: NOT_ANSWERABLE
- **Why**: No marriage concept exists. A probe over all 89 concepts for any alias in `marriage, bride, wedding, wife, husband, spouse` returned **0 rows**. The structural handle exists — AV Kāṇḍa 14 is the marriage book and it is present as a `SECTION` node (`AVS 14`, `structural_path '["14"]'`) — but it carries no topical label, no title, and no `CONCERNS` edge. `entity_type` values for AV are only `MANTRA` (5,839), `HYMN` (731) and `SECTION` (20).
- **Blocking gap**: no `HumanConcern` / life-event layer, and no hymn-level topic or title property to fall back on.
- **Probe**:
  ```cypher
  MATCH (c:Concept) WHERE any(a IN c.aliases_en WHERE toLower(a) IN
    ['marriage','bride','wedding','wife','husband','spouse']) RETURN c.concept_id
  ```
  0 rows.

### 14. Which concern childbirth?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: One usable proxy and one trap. `PRAJA-OFFSPRING` ("progeny and continuity of the line") is the right sense and gives 200 AV passages. `JANMAN-BIRTH` gives 280 AV passages but its own definition reads "birth, begetting and **the generation of the world in the cosmogonic hymns**" — using it for childbirth conflates parturition with cosmogony. There is no `garbha`, `sūtī`, midwifery or safe-delivery concept.
- **Blocking gap**: no `HumanConcern`/life-event layer; the nearest concept is sense-conflated with cosmogony.
- **Probe**:
  ```cypher
  MATCH (p:Passage {veda:'AV'})-[:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.preferred_label_en IN ['birth','offspring'] RETURN c.preferred_label_en AS en, count(*) AS c
  ```
  `birth 280`, `offspring 200`. Only the second is on-topic.

### 15. Which concern disease?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: `YAKSMA-DISEASE` is correctly scoped and AV-heavy — 108 AV passages against 55 RV, mean edge confidence 0.644, with 62 AV passages at confidence ≥ 0.8. But it is a single undifferentiated bucket: no takman (fever), balāsa, kṣetriya, jāyānya, apacit, kilāsa or harimā. A researcher asking about the takman hymns gets the whole disease corpus undivided.
- **Blocking gap**: no named-disease vocabulary; no `Disease` type in the `node_type` space (disease sits under `STATE`).
- **Probe**:
  ```cypher
  MATCH (p:Passage {veda:'AV'})-[r:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:YAKSMA-DISEASE'})
  RETURN count(*) AS c, avg(r.confidence) AS avgconf
  ```
  `c 108, avgconf 0.644`. Top-confidence rows: `AVS 1.25.1–3` (the takman hymn) at 0.85 — the right passages surface, unnamed.

### 16. Which concern enemies/protection?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The best-served of the four AV concern questions. `SATRU-ENEMY` 247 AV passages, `SARMAN-PROTECTION` 231, `RAKSAS-DEMON` 103 — right senses, useful magnitudes. Short of ANSWERABLE_NOW only by rule 1: the concept layer's 4-edge truncation means these counts are a lower bound of unknown tightness, and there is no directional structure (protection *from* what, *for* whom, *by* whose agency).
- **Blocking gap**: unknown recall from the truncated concept layer; no relational structure on abhicāra/protection (no `PROTECTS_AGAINST`, no `Adversary` role).
- **Probe**:
  ```cypher
  MATCH (p:Passage {veda:'AV'})-[:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.concept_id IN ['VG:CONCEPT:SATRU-ENEMY','VG:CONCEPT:SARMAN-PROTECTION','VG:CONCEPT:RAKSAS-DEMON']
  RETURN c.preferred_label_en AS en, count(*) AS c ORDER BY c DESC
  ```
  `enemy 247`, `protection 231`, `demon 103`.

### 17. What concepts and actions surround Soma?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Concept co-occurrence around `SOMA-DRINK` produces a coherent semantic neighbourhood: soma pressing 333, wealth 127, cattle 123, heaven 115, praise 112, river 96, honey 91. But every edge is undifferentiated `ABOUT_CONCEPT` co-occurrence — the graph cannot say that soma *is pressed by* stones, *flows into* vats, or *is mixed with* milk. `ACTION` is a node_type on 5 concepts (`liberality, birth, homage, praise, battle`); pressing, filtering, flowing and mixing are not among them.
- **Blocking gap**: no verb/process layer — actions are nouns in the concept list, and there is no argument structure (agent, instrument, product).
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:SOMA-DRINK'}),
        (p)-[:ABOUT_CONCEPT]->(c:Concept) WHERE c.concept_id <> 'VG:CONCEPT:SOMA-DRINK'
  RETURN c.preferred_label_en AS concept, c.node_type AS t, count(*) AS c ORDER BY c DESC LIMIT 6
  ```
  `soma pressing/RITUAL 333`, `wealth 127`, `cattle 123`, `heaven 115`, `praise 112`, `river/RIVER 96`.

### 18. What actions does Indra perform most often?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The answer that comes back — praise 416, battle 221, liberality 203, birth 89, homage 27 — is not a list of Indra's actions. It is a list of five nouns that co-occur with Indra hymns, and two of the top three (`praise`, `homage`) are things the *poet* does, not Indra. The typed layer that would fix this, `DESCRIBES_ACTION`, has 35 edges over 4 concepts, and only 3 of them have Indra attached.
- **Blocking gap**: no agentive predicate layer at scale — no `Devata`-as-subject verb edges (vṛtrahatya, vajra-hurling, cow-releasing, waters-freeing); the `ACTION` vocabulary is 5 nouns.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'}),
        (m)-[:ABOUT_CONCEPT]->(c:Concept) WHERE c.node_type='ACTION'
  RETURN c.preferred_label_en AS action, count(*) AS c ORDER BY c DESC
  ```
  5 rows: `praise 416, battle 221, liberality 203, birth 89, homage 27`.

### 19. Who are the Rishis most associated with Indra?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: A query returns rows, and this is the sharpest demonstration in the audit of why that is not enough. The naive join reports Viśvāmitra 217, Vāmadeva 194, Bharadvāja 165 — but 100% of those pairings are two sūkta-wide labels inherited independently down to the same mantra. Filtering both edges to `provenance_class = 'SOURCE_EXPLICIT'` produces a *completely different* leaderboard.
- **Blocking gap**: only 347 of 10,558 `HAS_DEVATA` edges (3.3%) and 90 of 10,565 `HAS_RISHI` edges (0.9%) are `SINGLE_MANTRA`; there is no per-mantra attribution to join.
- **Probe** (naive vs. provenance-filtered):
  ```cypher
  MATCH (m:Mantra)-[rd:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'})
  MATCH (m)-[rr:HAS_RISHI]->(r:Rishi)
  WHERE rd.provenance_class='SOURCE_EXPLICIT' AND rr.provenance_class='SOURCE_EXPLICIT'
  RETURN r.preferred_label AS rishi, count(DISTINCT m) AS mantras ORDER BY mantras DESC LIMIT 5
  ```

  | Naive (no provenance filter) | Provenance-filtered (`SOURCE_EXPLICIT`) |
  | --- | --- |
  | gāthino viśvāmitraḥ 217 | kāṇvau medhātithimedhyātithī 27 |
  | gautamo vāmadevaḥ 194 | gautamo vāmadevaḥ 9 |
  | bārhaspatyo bharadvājaḥ 165 | bhāgavo nemaḥ 8 |
  | maitrāvaruṇirvasiṣṭhaḥ 163 | aindro vasukraḥ 6 |
  | śaunako gṛtsamadaḥ 141 | indraḥ 6 |

  Only one name survives in both lists.

### 20. What roles does Agni have besides physical fire?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The co-occurrence profile does gesture at the roles — `priest` 219 (hotṛ), `sacrifice` 316, `oblation` 160, `house` 134 (gṛhapati), `speech` 111, `cosmic order` 115 — so the material for the answer is in the graph. But `role` is not a modelled dimension: there is no `HAS_ROLE` edge, no `Role` node, and the evidence is undifferentiated co-occurrence, so "Agni is the domestic priest" is something the reader infers, not something the graph asserts.
- **Blocking gap**: no `Devata`→`Role`/function layer; roles must be reconstructed from concept co-occurrence.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'}),
        (m)-[:ABOUT_CONCEPT]->(c:Concept)
  RETURN c.preferred_label_en AS concept, count(*) AS c ORDER BY c DESC LIMIT 8
  ```
  `fire 1100, sacrifice 316, wealth 232, priest 219, praise 201, heaven 179, oblation 160, people 156`.

### 21. Which concepts bridge Rigveda and Atharvaveda?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: All 89 concepts appear in both RV and AV, so the literal answer — "all of them" — is uninformative. The useful version, differential prominence, does work and produces a genuinely interesting result: `breath` is 90.8% Atharvavedic (RV 15 / AV 148), a real prāṇa-doctrine signal. But with 89 concepts the "bridge" set has no resolution, and the shares inherit the 4-edge truncation.
- **Blocking gap**: concept inventory too small and too generic to distinguish shared from distinctive; no diachronic layer to interpret "bridge" as inheritance vs. independent development.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept) WHERE p.veda IN ['RV','AV']
  WITH c, sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS rv,
          sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS av
  WHERE rv+av>100 RETURN c.preferred_label_en AS en, rv, av,
    round(toFloat(av)/(rv+av),3) AS av_share ORDER BY av_share DESC LIMIT 5
  ```
  `breath 15/148 = 0.908`, `disease 55/108 = 0.663`, `ancestors 91/151 = 0.624`, `midspace 114/180 = 0.612`, `plants 124/193 = 0.609`. Concepts present in both RV and AV: 89 of 89.

### 22. Which passages are lexically different but conceptually similar?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The query runs and the shape is right — subtract the parallel layer from the concept-overlap layer — but the concept layer cannot carry it. Because `ABOUT_CONCEPT` is capped at 4 per passage, a 5-concept overlap is arithmetically impossible: the probe at `shared >= 5` returned **0 pairs**. At `shared >= 4` (both passages saturated and identical) it returns 33 pairs; at `shared >= 3` it returns 5,194, which is too loose to be a similarity claim.
- **Blocking gap**: no semantic embedding or conceptual-similarity measure; the 4-edge concept cap makes overlap-count a degenerate similarity function.
- **Probe**:
  ```cypher
  MATCH (a:Mantra {veda:'RV'})-[:ABOUT_CONCEPT]->(c:Concept)<-[:ABOUT_CONCEPT]-(b:Mantra {veda:'AV'})
  WITH a,b,count(DISTINCT c) AS shared WHERE shared>=4
    AND NOT (a)-[:NEAR_PARALLEL_OF|EXACT_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM]-(b)
  RETURN count(*) AS pairs
  ```
  `shared>=5: 0` · `shared>=4: 33` · `shared>=3: 5194`.

### 23. What deity communities emerge from the corpus?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: There is no deity-to-deity edge in the graph, so no community can be read directly. Two projections are available and GDS is installed (423 procedures, including `gds.louvain.stream`, `gds.betweenness.stream`, `gds.pageRank.stream`, `gds.graph.project`). The mantra-level co-occurrence projection is useless — only **4** deity pairs exist, because the Anukramaṇī assigns one devatā per mantra. The shared-Rishi projection is usable and produces recognisable pairings, but it is RV-only, built on sūkta-inherited labels, and treats composites as atoms.
- **Blocking gap**: no `Devata`↔`Devata` edge of any kind (`MATCH (a:Devata)-[r]-(b:Devata)` returns 0 rows); no composite decomposition; RV-only.
- **Probe**:
  ```cypher
  MATCH (d1:Devata)<-[:HAS_DEVATA]-(:Mantra)-[:HAS_RISHI]->(r:Rishi)
        <-[:HAS_RISHI]-(:Mantra)-[:HAS_DEVATA]->(d2:Devata)
  WHERE d1.entity_key < d2.entity_key
  RETURN d1.preferred_label AS a, d2.preferred_label AS b, count(DISTINCT r) AS shared_rishis
  ORDER BY shared_rishis DESC LIMIT 5
  ```
  `aśvinau–indraḥ 26`, `agniḥ–indraḥ 25`, `indraḥ–viśvedevāḥ 22`, `agniḥ–aśvinau 21`, `agniḥ–pavamānaḥ somaḥ 18`. Direct mantra co-occurrence, by contrast: 4 pairs, max count 3.

### 24. What differs between Rigvedic family books and later material?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The maṇḍala partition is recoverable but only by string surgery: RV `structural_path` is the literal string `'[]'` and `native_labels` is `'[]'` — both empty, unlike AV/SV/YV which populate them. Maṇḍala must be extracted with `substring(canonical_key,10,3)` or by parsing the `hierarchy` JSON string. Once done, the contrast is mostly flat because the concept layer is too coarse: the highest family-book share is 0.527. The one strong signal (`soma juice` at 0.233) is just Maṇḍala 9 being the Soma book — a structural fact, not a finding.
- **Blocking gap**: no corpus-layer/stratum dimension; RV structural properties are empty, so the partition is not a first-class query surface.
- **Probe**:
  ```cypher
  MATCH (m:Mantra {veda:'RV'})-[:ABOUT_CONCEPT]->(c:Concept)
  WITH c, substring(m.canonical_key,10,3) AS mnd, count(*) AS n
  WITH c, sum(CASE WHEN mnd IN ['M02','M03','M04','M05','M06','M07'] THEN n ELSE 0 END) AS fam,
          sum(CASE WHEN mnd IN ['M01','M08','M09','M10'] THEN n ELSE 0 END) AS other
  WHERE fam+other>150 RETURN c.preferred_label_en AS concept, fam, other,
    round(toFloat(fam)/(fam+other),3) AS family_share ORDER BY family_share DESC LIMIT 3
  ```
  Highest: `homage 0.527`, `wellbeing 0.526`, `fire 0.516`. Lowest: `soma juice 0.233`, `ocean 0.246`, `heart 0.255`. Maṇḍala mantra counts confirmed: M01 2006, M02 429, M03 617, M04 589, M05 727, M06 765, M07 841, M08 1716, M09 1108, M10 1754.

### 25. Which ritual objects recur most?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: `node_type='OBJECT'` has exactly 6 members and returns a clean cross-Veda table. But three of the six (`chariot`, `thunderbolt`, `weapon`) are not ritual objects at all — they are mythological and martial — while the actual ritual inventory (vessels, ladles, pressing-boards, the yūpa post, the vedi, the śruc/śruva, the droṇakalaśa) is entirely absent. The query answers "which of these six words recur", not the question.
- **Blocking gap**: no ritual-implement vocabulary; `OBJECT` conflates ritual implement, weapon and vehicle with no sub-typing; `node_type` is a property, not a label.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept) WHERE c.node_type='OBJECT'
  RETURN c.preferred_label_en AS obj,
    sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV, sum(CASE p.veda WHEN 'SV' THEN 1 ELSE 0 END) AS SV,
    sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS YV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV,
    count(*) AS total ORDER BY total DESC
  ```

  | obj | RV | SV | YV | AV | total |
  | --- | --- | --- | --- | --- | --- |
  | chariot | 549 | 38 | 25 | 90 | 702 |
  | thunderbolt | 234 | 31 | 9 | 78 | 352 |
  | weapon | 160 | 8 | 41 | 127 | 336 |
  | sacred grass | 207 | 23 | 48 | 43 | 321 |
  | stone | 162 | 22 | 10 | 27 | 221 |
  | kindling | 78 | 12 | 19 | 38 | 147 |

### 26. Which rivers occur with which clans?

- **Status**: NOT_ANSWERABLE
- **Why**: Both sides of the question are missing, and the graph documents its own gap. There is exactly one river node, `VG:CONCEPT:SINDHU-RIVER`, whose definition states: *"A flowing river, named generically; the specific named rivers stay in the place layer rather than here."* **There is no place layer.** `node_type IN ['PLACE','RIVER']` returns 4 nodes: `house`, `field`, `mountain`, `river`. No Sarasvatī, no Sindhu-as-entity, no Vipāś, Śutudrī, Yamunā or Gaṅgā. On the clan side there is no clan node either (see Q2).
- **Blocking gap**: no named-entity layer for places, rivers, clans or kings — a whole missing tier that an existing concept definition already forward-references.
- **Probe**:
  ```cypher
  MATCH (c:Concept) WHERE c.node_type IN ['PLACE','RIVER'] RETURN c.concept_id, c.preferred_label_en
  ```
  4 rows: `GRHA-HOUSE`, `KSETRA-FIELD`, `PARVATA-MOUNTAIN`, `SINDHU-RIVER`. The nearest available substitute — river-concept co-occurrence with individual seers (`gautamo vāmadevaḥ 28`, `āṅgirasaḥ kutsaḥ 26`, `maitrāvaruṇirvasiṣṭhaḥ 26`) — answers neither half of the question.

### 27. Which formula families spread across Vedas?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Individual formulas are fully cross-Veda queryable (Q8), but *families* are not modelled. There is no `family`, `cluster`, `group` or `parent` property on `Formula` (a probe over all keys returned 0 matches), and `SHARES_FORMULA_WITH` is a **declared relationship type with 0 instances** — the grouping edge was designed and never populated. Nesting can be approximated by substring containment (159 two-word formulas nested inside four-word formulas) but that is a lexical accident, not a family.
- **Blocking gap**: no `FormulaFamily` node and no populated `SHARES_FORMULA_WITH`; no variant grouping over the 4,825 formulas.
- **Probe**:
  ```cypher
  MATCH ()-[r:SHARES_FORMULA_WITH]->() RETURN count(r) AS c
  ```
  `0`. And: `MATCH (f1:Formula),(f2:Formula) WHERE f1.word_count=2 AND f2.word_count=4 AND f2.normalized CONTAINS f1.normalized RETURN count(*)` → `159`.

### 28. Where do competing interpretations exist?

- **Status**: NOT_ANSWERABLE
- **Why**: Nowhere, because the graph holds exactly one interpretation per passage. All 17,283 `HAS_TRANSLATION` edges are 1:1 — the probe grouping passages by translation count returns a single row, `n=1, passages=17283`. There are two translators but they partition the corpus rather than overlapping: Griffith holds RV (10,502) and YV (1,903), Whitney/Lanman holds AV (4,878), and **Samaveda has zero translations**. No `Claim`, `Interpretation` or `Position` node exists.
- **Blocking gap**: no interpretation/claim layer; single-witness translation coverage with no second opinion anywhere in 100,584 nodes.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:HAS_TRANSLATION]->(t:Translation)
  WITH p, count(t) AS n RETURN n, count(*) AS passages ORDER BY n DESC
  ```
  1 row: `n 1, passages 17283`.

### 29. Which graph claims are textual and which are interpretive?

- **Status**: ANSWERABLE_NOW
- **Why**: This is answerable, and it is the graph's quiet strength. Every semantic and knowledge edge carries a provenance vocabulary, so the graph can be partitioned by epistemic status in one query. `trust` covers the enrichment edges (`DETERMINISTIC_DERIVED` 76,499 / `LLM_EXTRACTED` 736 / `SOURCE_EXPLICIT` 119); `provenance_class` covers the knowledge and annotation edges (`SOURCE_EXPLICIT` 6,948 / `SOURCE_DERIVED_SCOPE` 24,698 / `DETERMINISTIC_DERIVED` 18,325). Only the four purely structural types — `HAS_TEXT_VERSION` 44,276, `CONTAINS` 22,537, `HAS_TRANSLATION` 17,283, `HAS_QA_ISSUE` 915 — carry neither, which is correct.
- **Blocking gap**: none for answerability, but one real defect: **two parallel vocabularies for the same idea**, and `EXACT_PARALLEL_OF` is split across both (750 edges written with `trust`, 256 with `provenance_class`), which means a single-property audit of that relationship type silently misses a quarter of it. This should be unified in V2.
- **Probe**:
  ```cypher
  MATCH ()-[r]->() WHERE r.trust IS NULL AND r.provenance_class IS NULL
  RETURN type(r) AS t, count(*) AS c ORDER BY c DESC
  ```
  4 rows, all structural. And `MATCH ()-[r]->() WHERE r.provenance_class IS NOT NULL RETURN type(r), r.provenance_class, count(*)` → 10 rows including `HAS_DEVATA/SOURCE_DERIVED_SCOPE 8329` against `HAS_DEVATA/SOURCE_EXPLICIT 2229`.

### 30. What evidence supports a civilizational/evolutionary claim?

- **Status**: NOT_ANSWERABLE
- **Why**: The ingredients exist but the claim layer does not. `Source` nodes carry a real `authority_tier` vocabulary (`PRIMARY_TRADITIONAL`, `SCHOLARLY_EDITION`, `HISTORICAL_TRANSLATION`, `AGGREGATOR`, `COMMUNITY_TRANSCRIPTION`) across 9 sources, and enrichment edges carry `evidence` arrays with locators and quotes. But there is no `Claim` node, no `SUPPORTS`/`CONTRADICTS` edge, and — decisively — no diachronic model: a probe for any property containing `layer`, `strat`, `period`, `date` or `chron` across `Passage` returned **0 rows**. An evolutionary claim cannot be evidenced by a graph with no time axis.
- **Blocking gap**: no `Claim`/argument layer; no diachronic or stratigraphic dimension anywhere in the graph.
- **Probe**:
  ```cypher
  MATCH (p:Passage) WITH p LIMIT 5000 UNWIND keys(p) AS k WITH DISTINCT k
  WHERE toLower(k) CONTAINS 'layer' OR toLower(k) CONTAINS 'strat'
     OR toLower(k) CONTAINS 'period' OR toLower(k) CONTAINS 'date' OR toLower(k) CONTAINS 'chron'
  RETURN k
  ```
  0 rows.

### 31. Which substances are offered to which deities?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Co-occurrence gives strong, correct-looking rows: `pavamānaḥ somaḥ`/soma juice 460, `indraḥ`/soma juice 401, `agniḥ`/food 107, `pavamānaḥ somaḥ`/milk 77. But "offered to" is not what the edges say — `ABOUT_CONCEPT` + `HAS_DEVATA` says only "this substance word and this deity label appear in the same mantra". Nothing distinguishes a substance offered *to* a deity from one the deity *is* (soma) or *carries* (Agni and ghṛta). The 3 `INVOLVES_SUBSTANCE` edges cannot help.
- **Blocking gap**: no `OFFERED_TO` / `Devata`↔`Substance` typed edge; 6-item substance vocabulary; RV-only deity side.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata), (m)-[:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.node_type='SUBSTANCE'
  RETURN d.preferred_label AS deity, c.preferred_label_en AS subst, count(*) AS n ORDER BY n DESC LIMIT 4
  ```
  `pavamānaḥ somaḥ/soma juice 460`, `indraḥ/soma juice 401`, `agniḥ/food 107`, `indraḥ/food 104`. The top row is a tautology, not an offering.

### 32. What purposes are rituals performed for?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: `REQUESTS` is the only purpose-bearing predicate in the graph and it is genuinely the right shape — wealth 30, protection 24, wellbeing 9, help 8, offspring 8, lifespan 7, hero 7 reads exactly like a Vedic desiderata list. But it is 109 edges over AV+YV candidates only, and it attaches to mantras, not to rituals (there are no rituals — Q5, Q39). So the graph knows what 109 verses ask for, and nothing about what any rite is for.
- **Blocking gap**: no `Ritual` node to attach purpose to; `REQUESTS` covers 0.5% of mantras and is frozen candidate data.
- **Probe**:
  ```cypher
  MATCH (m)-[:REQUESTS]->(c:Concept)
  RETURN c.preferred_label_en AS requested, count(*) AS n ORDER BY n DESC LIMIT 7
  ```
  `wealth 30, protection 24, wellbeing 9, help 8, offspring 8, lifespan 7, hero 7` (109 edges total).

### 33. Which deities co-occur?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: At mantra granularity the answer is effectively empty — **4 pairs**, the largest at count 3 — because the Anukramaṇī assigns one devatā per mantra and joint invocations are collapsed into composite nodes. Lifting to hymn granularity via `CONTAINS` recovers a real structure (the top pairs `agniḥ–tvaṣṭā` 12 and the cluster `devīrdvāraḥ / uṣāsānaktā / vanaspatiḥ / daivyau hotārau` are the correct Āprī litany), but only 41 hymns have 4 or more distinct devatās, and it is RV-only.
- **Blocking gap**: composite `Devata` nodes never decomposed; no `CO_INVOKED_WITH` edge; RV-only.
- **Probe**:
  ```cypher
  MATCH (h:Passage {entity_type:'HYMN'})-[:CONTAINS]->(m:Mantra)-[:HAS_DEVATA]->(d:Devata)
  WITH h, collect(DISTINCT d) AS ds WHERE size(ds)>1
  UNWIND ds AS d1 UNWIND ds AS d2 WITH d1,d2 WHERE d1.entity_key < d2.entity_key
  RETURN d1.preferred_label AS a, d2.preferred_label AS b, count(*) AS hymns ORDER BY hymns DESC LIMIT 4
  ```
  `agniḥ–tvaṣṭā 12`, `devīrdvāraḥ–tvaṣṭā 10`, `uṣāsānaktā–vanaspatiḥ 10`, `tvaṣṭā–uṣāsānaktā 10`. Mantra-level equivalent: 4 pairs total.

### 34. Which concepts co-occur?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: This works well and the top pairs are philologically sound — `heaven–earth` 499 (dyāvāpṛthivī), `soma juice–soma pressing` 333, `fire–sacrifice` 260, `horse–cattle` 173. Capped at PARTIALLY by rule 1: with at most 4 concepts per passage, the co-occurrence matrix is a heavily truncated sample of the true one, so ranks are indicative and magnitudes are not comparable across concepts of different base rates.
- **Blocking gap**: unknown recall from the 4-edge cap; no concept-to-concept relational layer beyond 18 `BROADER_THAN` edges.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c1:Concept), (p)-[:ABOUT_CONCEPT]->(c2:Concept)
  WHERE c1.concept_id < c2.concept_id
  RETURN c1.preferred_label_en AS a, c2.preferred_label_en AS b, count(DISTINCT p) AS n
  ORDER BY n DESC LIMIT 5
  ```
  `heaven–earth 499`, `soma juice–soma pressing 333`, `fire–sacrifice 260`, `fire–wealth 202`, `fire–priest 177`.

### 35. Which deities are connected through common Rishis?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The traversal works and gives the numbers reported in Q23. The caveat is severe: because 95.5% of `HAS_RISHI` and 78.9% of `HAS_DEVATA` are sūkta-wide inheritance, "connected through a common Rishi" mostly means "both labels were inherited into some mantra of some hymn attributed to that Rishi" — a statement about the Anukramaṇī's hymn-level bookkeeping, not about a seer's devotional range.
- **Blocking gap**: no per-mantra attribution to ground the connection; no `RishiFamily` to aggregate to; RV-only.
- **Probe**: see Q23. `aśvinau–indraḥ 26 shared rishis` is the top row; the same query restricted to `SOURCE_EXPLICIT` on both hops would drop the population to 472 rishi edges and 2,229 devatā edges.

### 36. Which concepts increase/decrease in relative prominence by corpus layer?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: "Corpus layer" is not modelled — the only available proxies are Veda (4 values) and RV maṇḍala (via string surgery, Q24). Normalising per 1,000 concept edges per Veda does produce a defensible diachronic-looking signal: `breath` 0.50 → 9.16 → 13.81 per 1k from RV to YV to AV, `ancestors` 3.06 → 10.38 → 14.09, `midspace` 3.84 → 5.90 → 16.80. But Veda is not a chronological layer, and the reading depends on the truncated concept layer.
- **Blocking gap**: no diachronic/stratigraphic dimension (no `CorpusLayer`, no relative dating, no khila/appendix marking); Veda used as a stand-in for time.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept)
  WITH c, sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS rv,
          sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS yv,
          sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS av
  RETURN c.preferred_label_en AS concept, round(1000.0*rv/29713,2) AS rv_per1k,
    round(1000.0*yv/4914,2) AS yv_per1k, round(1000.0*av/10715,2) AS av_per1k
  ORDER BY av_per1k - rv_per1k DESC LIMIT 4
  ```
  `plants 4.17 / 13.23 / 18.01`, `birth 12.52 / 15.47 / 26.13`, `breath 0.50 / 9.16 / 13.81`, `midspace 3.84 / 5.90 / 16.80`.

### 37. Which mantras are central bridges between concept communities?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: GDS is installed and `gds.betweenness.stream`, `gds.louvain.stream`, `gds.pageRank.stream` and `gds.graph.project` are all available, so centrality is computable today. But the concept-degree distribution makes "central bridge" meaningless: degree is capped at 4, and 5,730 mantras sit at the ceiling simultaneously. A betweenness ranking over that graph ranks a truncation artefact, and 4,475 passages are isolated in the concept projection entirely.
- **Blocking gap**: the 4-edge concept cap flattens the degree distribution, so graph-theoretic centrality has no discriminating power; no confidence weighting in the projection.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:ABOUT_CONCEPT]->(c:Concept) WITH m, count(DISTINCT c) AS cd
  RETURN cd, count(*) AS n ORDER BY cd
  ```
  `1: 3939`, `2: 4496`, `3: 3897`, `4: 5730`. Maximum degree in the whole graph is 4.

### 38. Which deities have the widest functional range?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: A breadth query returns a clean and superficially convincing ranking — but it is measuring corpus size, not function. `viśvedevāḥ` tops it at 88 of 89 concepts, and 12 deities all reach `type_breadth = 15`, the full node_type space. That is what happens when a deity has enough mantras to saturate an 89-concept vocabulary: breadth here is a proxy for `count(mantras)`, and "function" is not modelled at all (Q20).
- **Blocking gap**: no `Devata`→`Role`/function layer, so breadth of *function* is unmeasurable; concept vocabulary too small to saturate-proof the metric.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata), (m)-[:ABOUT_CONCEPT]->(c:Concept)
  RETURN d.preferred_label AS deity, count(DISTINCT c.node_type) AS type_breadth,
    count(DISTINCT c) AS concept_breadth, count(DISTINCT m) AS mantras
  ORDER BY concept_breadth DESC LIMIT 5
  ```

  | deity | type_breadth | concept_breadth | mantras |
  | --- | --- | --- | --- |
  | viśvedevāḥ | 15 | 88 | 770 |
  | agniḥ | 15 | 87 | 1943 |
  | indraḥ | 15 | 87 | 2750 |
  | pavamānaḥ somaḥ | 15 | 86 | 1039 |
  | aśvinau | 15 | 81 | 613 |

  Note the ordering inversion: `viśvedevāḥ` outranks `indraḥ` on breadth with 28% of the mantras, which is exactly the saturation artefact.

### 39. Which rituals have the most complex dependency structure?

- **Status**: NOT_ANSWERABLE
- **Why**: There are no rituals and no dependencies. `RITUAL` is a `node_type` on 2 concepts. A probe for `PRECEDES`, `FOLLOWS`, `REQUIRES`, `PART_OF` or `DEPENDS_ON` returns **0 rows** — none of these relationship types exists in the database. The two ritual concepts have almost no typed structure: `YAJNA-SACRIFICE` has 1,570 `ABOUT_CONCEPT` edges, 10 `INVOLVES_RITUAL`, 2 `DEVATA_ASSOCIATED_WITH`, and nothing else.
- **Blocking gap**: no `Ritual`/`Rite` entity, no procedural structure (sequence, prerequisite, sub-rite, officiant role, paraphernalia), and no link from the Yajurveda's procedural content to any structured representation.
- **Probe**:
  ```cypher
  MATCH ()-[r]->() WHERE type(r) IN ['PRECEDES','FOLLOWS','REQUIRES','PART_OF','DEPENDS_ON']
  RETURN type(r) AS t, count(*) AS c
  ```
  0 rows.

### 40. Which objects/weapons belong to which deity narratives?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: This produces the single best-looking co-occurrence result in the audit: `indraḥ–thunderbolt 199`, `aśvinau–chariot 138`, `agniḥ–kindling 67`, `indraḥ–weapon 66`, `pavamānaḥ somaḥ–stone 35`. Every one is philologically correct. But it is still undifferentiated co-occurrence over a 6-item object vocabulary with no narrative dimension — the graph has no `WIELDS`, no `Narrative`/`Myth` node, and cannot separate Indra's vajra from a vajra merely mentioned in an Indra hymn.
- **Blocking gap**: no `WIELDS`/`ATTRIBUTE_OF` edge and no narrative/myth layer; 6-item object vocabulary; RV-only deity side.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata), (m)-[:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.node_type='OBJECT'
  RETURN d.preferred_label AS deity, c.preferred_label_en AS obj, count(*) AS n ORDER BY n DESC LIMIT 5
  ```
  `indraḥ/thunderbolt 199`, `aśvinau/chariot 138`, `indraḥ/chariot 134`, `agniḥ/kindling 67`, `indraḥ/weapon 66`.

### 41. Which natural phenomena are personified as deities?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: `DEVATA_ASSOCIATED_WITH` gives a clean 9-row mapping and it is the only deity-to-concept edge in the graph. But its `method` is `concept-lexicon-related-devata` — it links a deity to a concept when the *deity's name is the concept's Sanskrit lemma*. It is a name-identity mapping, not an assertion of personification, and it therefore cannot capture the interesting cases (Indra and lightning, Viṣṇu and the sun's stride) or distinguish `agniḥ` the god from `agni` the fire. All 101 edges are RV-Anukramaṇī derived and only 30 of 214 devatās are covered.
- **Blocking gap**: no `PERSONIFIES` predicate; the only available edge is lexical identity mislabelled as association; no cross-Veda side.
- **Probe**:
  ```cypher
  MATCH (d:Devata)-[:DEVATA_ASSOCIATED_WITH]->(c:Concept) WHERE c.node_type='NATURAL_PHENOMENON'
  RETURN c.preferred_label_en AS phen, collect(d.preferred_label) AS deities
  ```
  9 rows: `fire → [agniḥ, agnerātmā, jātavedā agniḥ, rakṣohāgniḥ, pavamāno agniḥ]`, `sun → [savitā, sāvitrī sūryā, sūryaḥ]`, `dawn → [uṣāḥ, uṣāsānaktā, ādityoṣasaḥ]`, `lightning → [parjanyaḥ, marutaḥ]`, `rain → [parjanyaḥ]`, plus `waters`, `moon`, `night`, `wind`.

### 42. Which deity names/epithets occur in which contexts?

- **Status**: NOT_ANSWERABLE
- **Why**: There is no epithet layer and no name-variant layer. `Devata` has four properties — `entity_key`, `preferred_label`, `devata_subtype`, `is_composite` — with no English label, no alias list and no epithet set. `preferred_label` is the raw inflected Anukramaṇī form (`indraḥ`, `agniḥ`, `pavamānaḥ somaḥ`). And there is **no edge of any type between two `Devata` nodes**, so the 11 Agni-family and 15 Indra-family nodes sit unlinked: `jātavedā agniḥ`, `rakṣohāgniḥ` and `pavamāno agniḥ` are epithet-qualified Agni and the graph does not know they are Agni. `devata_subtype` is `UNKNOWN` on 209 of 214 (97.7%), and `is_composite` is `false` on all 214 including `indrāgnī` and `mitrāvaruṇau` — the flag is not merely unused, it is wrong.
- **Blocking gap**: no epithet/alias layer on `Devata`, no `SAME_AS`/`EPITHET_OF`/`COMPONENT_OF` edges, no English labels, `devata_subtype` unpopulated.
- **Probe**:
  ```cypher
  MATCH (a:Devata)-[r]-(b:Devata) RETURN type(r) AS t, count(*) AS c
  ```
  0 rows. And `MATCH (d:Devata) WHERE d.entity_key CONTAINS 'AGNI' RETURN d.entity_key, d.preferred_label` → 11 rows, all mutually unlinked.

### 43. How does Rudra's corpus profile differ by Veda?

- **Status**: NOT_ANSWERABLE
- **Why**: Rudra exists in the graph only as a Rigvedic Anukramaṇī label with 38 `HAS_DEVATA` edges (plus `somārudrau` 4 and `marudrudraviṣṇavaḥ` 1). The Yajurveda's Śatarudriya — the single most important Rudra text in the Vedic corpus — contributes nothing, because YV has no deity attribution. There is no Rudra `Concept` node. The `rudrá-` lemma exists with `mantra_count 128`, but `MENTIONS_LEMMA` is Rigveda-only (all 9,000 edges), so even the lexical route is RV-bounded.
- **Blocking gap**: knowledge layer is RV-only, so the Veda that would answer this has no Rudra side; the lemma layer is RV-only too.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata) WHERE d.entity_key CONTAINS 'RUDRA'
  RETURN d.entity_key AS k, p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  3 rows, all `RV`: `RUDRAH 38`, `SOMARUDRAU 4`, `MARUDRUDRAVISNAVAH 1`.

### 44. How does Varuna's corpus profile differ from Indra's?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The comparison runs and the differential does isolate the right concepts — `ordinance` at 0.50 Varuṇa-share, `sin` at 0.286, `kingship` at 0.22 against a far lower base rate — which is recognisably the dhárman / énas / kṣatrá profile. But it is asymmetric to the point of fragility: Varuṇa has 95 mantras against Indra's 2,750, so every Varuṇa cell is single-digit, and the concepts that define Varuṇa in the literature (vrata, māyā-as-sovereign-power, the noose, the waters as cosmic bond) are either absent from the 89-concept vocabulary or present only generically.
- **Blocking gap**: no deity-role layer; concept vocabulary too coarse for a sovereignty/ṛta profile; N too small on the Varuṇa side after the RV-only restriction.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata)
  WHERE d.entity_key IN ['VG:DEVATA:VARUNAH','VG:DEVATA:INDRAH']
  MATCH (m)-[:ABOUT_CONCEPT]->(c:Concept)
  WITH c, sum(CASE d.entity_key WHEN 'VG:DEVATA:VARUNAH' THEN 1 ELSE 0 END) AS var,
          sum(CASE d.entity_key WHEN 'VG:DEVATA:INDRAH' THEN 1 ELSE 0 END) AS ind
  WHERE var>=4 RETURN c.preferred_label_en AS concept, var, ind,
    round(toFloat(var)/(var+ind),3) AS varuna_share ORDER BY varuna_share DESC LIMIT 5
  ```
  `ordinance 8/8 = 0.500`, `sin 6/15 = 0.286`, `kingship 20/71 = 0.220`, `wile 5/32 = 0.135`, `bird 4/26 = 0.133`.

### 45. How does Soma behave as deity vs substance?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: A cross-tab is computable and looks informative: 1,167 mantras have Soma as devatā, 1,841 have the `SOMA-DRINK` substance concept, 522 have both. But the separation is illusory. `SOMA-DRINK`'s alias list contains `soma, somaḥ, somam, somasya, somāya, some, somo, somebhiḥ, somāsaḥ` — the full nominal paradigm — so the "substance" matcher fires on every mention of the god as well. Its definition says "the substance, not the deity of the same name" while its aliases guarantee the opposite. And the deity side is RV-only while the substance side spans all four Vedas (RV 1,260 / SV 246 / AV 218 / YV 117).
- **Blocking gap**: no word-sense disambiguation between deity and substance readings; concept aliases contradict concept definitions; asymmetric corpus coverage between the two sides.
- **Probe**:
  ```cypher
  MATCH (c:Concept {concept_id:'VG:CONCEPT:SOMA-DRINK'}) RETURN c.aliases_sa AS sa, c.definition AS d
  ```
  `sa` includes `soma, somaḥ, somam, somasya, somāya`. Cross-tab: `as_deity 1167, as_substance 1841, both 522`.

### 46. How does Agni behave as deity vs fire vs ritual medium?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The same defect as Q45, documented even more explicitly. A three-way cross-tab returns eight populated cells which read as a clean sense partition. It is not. `AGNI-FIRE`'s definition states *"Fire as the ritual and natural phenomenon … **NOT the deity Agni, which is VG:DEVATA:AGNIH**"* — and its Sanskrit alias list is `agna, agnau, agnayaḥ, agnaye, agne, agnibhiḥ, agnim, agninā, agnir, agniḥ, agniṃ, agniṣ, agnī, jātavedasam, jātavedase, jātavedaḥ, …`, i.e. exactly the vocatives and nominatives used to *address the god*. The concept asserts a distinction its own matcher cannot make. "Ritual medium" is not a modelled sense at all.
- **Blocking gap**: no word-sense disambiguation; alias sets contradict definitions; no `Role`/medium dimension.
- **Probe**:
  ```cypher
  MATCH (m:Mantra) WITH m,
    EXISTS { (m)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'}) } AS is_deity,
    EXISTS { (m)-[:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:AGNI-FIRE'}) } AS is_fire,
    EXISTS { (m)-[:ABOUT_CONCEPT]->(:Concept {concept_id:'VG:CONCEPT:YAJNA-SACRIFICE'}) } AS is_yajna
  RETURN is_deity, is_fire, is_yajna, count(*) AS n ORDER BY n DESC
  ```
  8 rows. `F/F/F 15955`, `F/F/T 1161`, `F/T/F 1013`, `T/T/F 933`, `T/F/F 739`, `T/T/T 167`, `T/F/T 149`, `F/T/T 93`. The `T/F/F 739` cell — Agni as deity with no fire concept — is the clearest sign the two layers are not measuring two senses but two incompletely overlapping string matchers.

### 47. Which passages support healing practices?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Filtering to `confidence >= 0.8` gives a defensible working set: AV `plants` 111, `disease` 62, `healing` 47; RV `plants` 71, `healing` 28, `disease` 24; YV `healing` 31. Right senses, right Veda skew, evidence quotes on every edge. Short of ANSWERABLE_NOW because "practice" is not modelled — there is no procedure, no materia medica, no named remedy, and no way to distinguish a hymn used *in* a healing rite from one that merely mentions herbs.
- **Blocking gap**: no `Practice`/procedure layer; no materia medica vocabulary (Q9); unknown recall from the truncated concept layer.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.concept_id IN ['VG:CONCEPT:BHESAJA-HEALING','VG:CONCEPT:OSADHI-PLANTS','VG:CONCEPT:YAKSMA-DISEASE']
    AND r.confidence >= 0.8
  RETURN c.preferred_label_en AS en, p.veda AS veda, count(*) AS c ORDER BY c DESC LIMIT 6
  ```
  `plants/AV 111`, `plants/RV 71`, `disease/AV 62`, `healing/AV 47`, `healing/YV 31`, `plants/YV 30`.

### 48. Which passages concern prosperity/cattle/agriculture?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: Prosperity and cattle are well covered — `wealth` 1,601 and `cattle` 1,339 edges across all four Vedas, with a sensible RV skew. Agriculture is not: the only agricultural concept is `KSETRA-FIELD` with 85 edges corpus-wide (RV 46 / AV 30 / YV 8 / SV 1), and its Sanskrit aliases quietly bundle four different things — `kṣetra` (field), `kṛṣi` (ploughing), `lāṅgala` (plough) and `sītā` (furrow). Two of the three legs of the question are strong; the third is one conflated 85-edge node.
- **Blocking gap**: no agricultural-practice or crop vocabulary (Q9); `KSETRA-FIELD` conflates place, activity and implement.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept)
  WHERE c.concept_id IN ['VG:CONCEPT:GO-CATTLE','VG:CONCEPT:VASU-WEALTH','VG:CONCEPT:KSETRA-FIELD',
                         'VG:CONCEPT:PASU-LIVESTOCK','VG:CONCEPT:ANNA-FOOD']
  RETURN c.preferred_label_en AS en,
    sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV, sum(CASE p.veda WHEN 'SV' THEN 1 ELSE 0 END) AS SV,
    sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS YV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV
  ```

  | en | RV | SV | YV | AV |
  | --- | --- | --- | --- | --- |
  | wealth | 1139 | 93 | 161 | 208 |
  | cattle | 802 | 76 | 86 | 375 |
  | food | 483 | 10 | 92 | 106 |
  | field | 46 | 1 | 8 | 30 |
  | livestock | 23 | 0 | 10 | 49 |

### 49. Which cross-Veda passages express similar ideas without textual reuse?

- **Status**: PARTIALLY_ANSWERABLE
- **Why**: The query shape is exactly right — anti-join the parallel layer against the concept layer — and the negative side is excellent (6,271 evidence-bearing cross-Veda parallel edges to subtract). The positive side collapses: with concept degree capped at 4, "conceptually similar" degenerates into "both saturated on the same 3–4 generic concepts". A bounded YV–SV probe returns 82 pairs at `shared >= 3`; the unbounded all-Veda-pairs version **exhausted the 1.4 GiB transaction memory pool** and could not complete, which is itself a finding about using overlap-count as a similarity function.
- **Blocking gap**: no semantic embedding or vector index on `Passage`/`TextVersion`/`Translation` to provide a real non-lexical similarity; the concept cap makes the available proxy both degenerate and computationally explosive.
- **Probe**:
  ```cypher
  MATCH (a:Mantra {veda:'YV'})-[:ABOUT_CONCEPT]->(c:Concept)<-[:ABOUT_CONCEPT]-(b:Mantra {veda:'SV'})
  WITH a,b,count(DISTINCT c) AS shared WHERE shared>=3
    AND NOT (a)-[:NEAR_PARALLEL_OF|EXACT_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM|PARALLEL_TO]-(b)
  RETURN count(*) AS pairs
  ```
  `82` (YV–SV). The same query over all Veda pairs failed with `Neo.TransientError.General.MemoryPoolOutOfMemoryError`.

### 50. What are the strongest evidence-backed transformations across the four Vedas?

- **Status**: ANSWERABLE_NOW
- **Why**: 6,271 cross-Veda parallel/reuse/variant edges carry a populated `evidence` array plus five independent similarity metrics, `trust = DETERMINISTIC_DERIVED`, `state = ACCEPTED`, `method`, `run_id` and `pipeline_version`. You can rank by any metric, read both source strings from the edge, and cite the locator. Veda-pair coverage is broad: RV–SV 1,180 near-parallels + 415 variants + 89 exact, AV–RV 752 + 22 + 551, RV–YV 473 + 165 + 24, AV–SV 326 + 132 + 9, AV–YV 162 + 41 + 7, SV–YV 156 + 13 + 70.
- **Blocking gap**: none for the question as asked. The adjacent question "*what kind* of transformation" is Q7 and is not answerable.
- **Probe**:
  ```cypher
  MATCH (a:Passage)-[r:NEAR_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM]->(b:Passage)
  WHERE a.veda <> b.veda AND r.similarity >= 0.7
  RETURN a.canonical_citation AS a, b.canonical_citation AS b, r.veda_pair AS pair,
         r.similarity AS sim, r.edit_ratio AS edit, r.token_jaccard AS tokjac
  ORDER BY r.token_jaccard ASC LIMIT 4
  ```
  `SV UTTARA 5.2.11.3 → RV 9.66.27` (sim 0.775, edit 0.911, token_jaccard 0.0); `SV CHANDA 2.8.7 → RV 1.18.6` (0.778 / 0.932 / 0.0); `RV 1.84.14 ↔ SV UTTARA 3.1.8.2` (0.842 / 0.966 / 0.0); `RV 10.90.4 → SV ARANYA 4.4` (0.817 / 0.937 / 0.05). Character-level near-identity with zero token overlap is the signature of Sāmavedic re-syllabification — the strongest transformation class in the corpus, and fully evidenced. Count of evidence-bearing cross-Veda edges: `6271`.

---

## MISSING KNOWLEDGE DIMENSIONS

Ranked by the number of the 50 questions each gap blocks or materially degrades. This ranking is the actionable output of the document: it says what to build first.

| # | Missing dimension | Blocks | Questions |
| --- | --- | --- | --- |
| 1 | **Concept-layer recall is unknown and structurally capped.** `ABOUT_CONCEPT` is hard-truncated at 4 edges/passage (`max = 4`, `avg = 2.63`); 4,475 of 22,537 passages (19.9%) have zero concept edges; 21,246 of 47,542 edges (44.7%) are English-translation-alias matches at `confidence = 0.42`. Every frequency, prominence, centrality and similarity claim in the graph rests on this. | 20 | 3, 4, 11, 15, 16, 17, 21, 22, 24, 25, 31, 32, 34, 36, 37, 38, 44, 47, 48, 49 |
| 2 | **Knowledge layer is Rigveda-only.** `HAS_DEVATA` / `HAS_RISHI` / `HAS_CHANDAS` / `MENTIONS_ENTITY` / `MENTIONS_LEMMA` exist only on RV mantras. SV (1,844), YV (1,975) and AV (5,839) mantras have no deity, seer, meter or lemma attribution, so every cross-Veda deity comparison has no non-RV side. | 19 | 1, 2, 3, 4, 5, 12, 19, 23, 31, 33, 35, 38, 40, 41, 42, 43, 44, 45, 46 |
| 3 | **No genuine per-mantra attribution.** Only 347 of 10,558 `HAS_DEVATA` edges (3.3%) and 90 of 10,565 `HAS_RISHI` edges (0.9%) are `SINGLE_MANTRA`. 78.9% of deity and 95.5% of seer attributions are sūkta-wide labels inherited down to every verse of the hymn. The provenance is recorded — it is simply not what the questions need. | 16 | 2, 3, 4, 12, 18, 19, 20, 23, 31, 33, 35, 38, 40, 44, 45, 46 |
| 4 | **No domain-specific vocabulary.** The ontology is 89 generic concepts. No crops, no metals beyond gold, no named diseases, no ritual implements, no named places or rivers, no kinship terms, no materia medica. Existing definitions forward-reference layers that do not exist (`SINDHU-RIVER`: "the specific named rivers stay in the place layer"). | 13 | 9, 10, 11, 13, 14, 15, 25, 26, 32, 39, 40, 47, 48 |
| 5 | **No typed semantic predicate layer at scale.** `INVOKES` / `PRAISES` / `DESCRIBES` / `DESCRIBES_ACTION` / `REQUESTS` / `INVOLVES_*` total 736 edges over 363 mantras (1.8%), all `state = CANDIDATE`, AV+YV only, frozen. Everything else is undifferentiated co-occurrence, so the graph can say two things appear together but never how they relate. | 13 | 1, 3, 4, 5, 17, 18, 20, 31, 32, 39, 40, 45, 46 |
| 6 | **`Devata` identity model is absent.** No English label, no aliases, no epithets, no `SAME_AS` / `EPITHET_OF` / `COMPONENT_OF` — **zero edges of any type between two `Devata` nodes**. `devata_subtype` is `UNKNOWN` on 209/214 (97.7%); `is_composite` is `false` on all 214 including `indrāgnī` and `mitrāvaruṇau`, so the flag is wrong as well as unused. 11 Agni-family and 15 Indra-family nodes sit mutually unlinked. | 12 | 1, 5, 23, 33, 35, 38, 41, 42, 43, 44, 45, 46 |
| 7 | **`node_type` is a property, not a label.** 15 real ontology types (`ANIMAL`, `RIVER`, `RITUAL`, `SUBSTANCE`, `OFFERING`, `NATURAL_PHENOMENON`, …) are flattened into the single Neo4j label `Concept`, so type-scoped traversal and typed GDS projections require a property filter rather than a label match. | 9 | 9, 10, 11, 25, 31, 34, 37, 40, 41 |
| 8 | **No `HumanConcern` / life-event / purpose layer.** Marriage, childbirth, disease-by-name, protection-from-X and prosperity-as-intent have no representation. AV Kāṇḍa 14 exists as a `SECTION` node with no topical label; `entity_type` for AV is only `MANTRA` / `HYMN` / `SECTION`. | 7 | 13, 14, 15, 16, 32, 47, 48 |
| 9 | **No diachronic / stratigraphic dimension.** No property containing `layer`, `strat`, `period`, `date` or `chron` exists on `Passage`. RV `structural_path` and `native_labels` are empty strings (unlike AV/SV/YV), so even maṇḍala requires `substring(canonical_key,10,3)`. Veda is being used as a stand-in for time. | 6 | 21, 24, 30, 36, 43, 50 |
| 10 | **No `Ritual` / `Rite` entity and no procedural structure.** `RITUAL` is a `node_type` on 2 concepts. `PRECEDES`, `FOLLOWS`, `REQUIRES`, `PART_OF` and `DEPENDS_ON` do not exist in the database. The Yajurveda's procedural content has no structured representation. | 5 | 4, 5, 25, 32, 39 |
| 11 | **No named-entity layer for places, rivers, clans, kings.** 4 `PLACE`/`RIVER` concepts, all generic. `Rishi` has 3 properties and bundles patronymic with personal name in one inflected display string; `occurrence_count` is 0 on all 367. No gotra, no `RishiFamily`, no `MEMBER_OF`. | 5 | 2, 24, 26, 30, 35 |
| 12 | **No word-sense disambiguation; alias sets contradict definitions.** `AGNI-FIRE` says "NOT the deity Agni" while listing `agniḥ`, `agne`, `jātavedaḥ` as aliases. `SOMA-DRINK` says "the substance, not the deity" while listing the full `soma-` paradigm. `JANMAN-BIRTH` conflates parturition with cosmogony; `KSETRA-FIELD` conflates field, ploughing and plough. | 5 | 14, 20, 45, 46, 48 |
| 13 | **No transformation typology and no formula-family grouping.** 6,271 evidence-bearing cross-Veda edges carry only numeric similarity; `match_level` is empty on 70% of RV–SV reuse edges. `SHARES_FORMULA_WITH` is a declared relationship type with **0 instances** — the grouping edge was designed and never populated. | 3 | 7, 27, 50 |
| 14 | **No interpretation / claim layer.** Exactly one translation per passage across all 17,283 `HAS_TRANSLATION` edges; two translators partition rather than overlap; **Samaveda has zero translations**. No `Claim`, `Interpretation`, `Position`, `SUPPORTS` or `CONTRADICTS`. | 3 | 28, 29, 30 |
| 15 | **No semantic embedding or vector index.** No non-lexical similarity measure over `Passage`, `TextVersion` or `Translation`, so conceptual similarity must be faked with concept-overlap counts — which is degenerate under the 4-edge cap and exhausted the 1.4 GiB transaction memory pool on an all-Veda-pairs query. | 2 | 22, 49 |

### Reading of the ranking

Gaps 1–3 are not new content; they are **corrections to layers that already exist**. Lifting the `ABOUT_CONCEPT` cap and recording real recall (gap 1), extending the knowledge layer to SV/YV/AV (gap 2), and obtaining per-mantra attribution (gap 3) together unblock or materially improve 37 of the 50 questions, and none of the three requires inventing a new ontology — they require finishing three existing ones.

Gaps 4–6 are the first genuinely new modelling work. Gap 7 (`node_type` → label) touches 9 questions for near-zero design cost and is already scoped for V2. Gap 12 is a data-quality fix rather than a modelling one: four concepts assert distinctions in their `definition` text that their own `aliases_sa` lists actively defeat, and those four concepts (`AGNI-FIRE`, `SOMA-DRINK`, `JANMAN-BIRTH`, `KSETRA-FIELD`) carry 2,206 + 1,841 + 763 + 85 = 4,895 edges, i.e. 10.3% of the whole concept layer.

---

## QUESTIONS AT RISK OF MISLEADING ANSWERS

These are the questions where a query returns rows **today** and a researcher reading those rows would draw a false conclusion. They are more dangerous than the NOT_ANSWERABLE set, because a null result is self-announcing and a plausible-looking table is not.

| Q | The rows you get | Why they mislead |
| --- | --- | --- |
| **19** | `gāthino viśvāmitraḥ 217`, `gautamo vāmadevaḥ 194`, `bārhaspatyo bharadvājaḥ 165` | 100% of these pairings are two independently inherited sūkta-wide labels meeting in the same mantra. Filtering both edges to `SOURCE_EXPLICIT` yields a leaderboard with **one name in common** (`kāṇvau medhātithimedhyātithī 27`, `gautamo vāmadevaḥ 9`, `bhāgavo nemaḥ 8`). The naive answer is an artefact of hymn-level bookkeeping. |
| **2, 3, 12, 18, 20, 31, 33, 35, 38, 40, 44, 45, 46** | Any deity-to-anything count | The same defect: 78.9% of `HAS_DEVATA` and 95.5% of `HAS_RISHI` are `SUKTA_WIDE`. A query that does not filter `provenance_class` presents a sūkta-wide inherited label as a per-mantra fact. The provenance is on the edge — it is simply ignored by the obvious query. |
| **10** | `HIRANYA-GOLD: RV 190, AV 66, YV 35, SV 6` | Reads as "gold is the metal of the Vedas". The graph has exactly one metal concept; `ayas` is absent. These rows do not under-report a distribution, they erase an entire material category. |
| **9, 25** | `plants: AV 193, RV 124, YV 65, SV 4`; the 6-row `OBJECT` table | Both read as inventories. Neither is: `plants` is one generic herb node standing in for all flora, and 3 of the 6 "ritual objects" (`chariot`, `thunderbolt`, `weapon`) are not ritual objects, while the actual implement set is absent. |
| **45, 46** | `Soma: as_deity 1167, as_substance 1841, both 522`; the 8-cell Agni cross-tab | These read as sense disambiguations and are not. `SOMA-DRINK` aliases include the full `soma-` nominal paradigm; `AGNI-FIRE` aliases include `agniḥ`, `agne`, `jātavedaḥ` — the vocatives used to address the god — while its definition explicitly claims it excludes the deity. The concepts assert a distinction their own matchers cannot make, so the cross-tab measures two overlapping string matchers, not two senses. |
| **14** | `birth: 280 AV passages` | `JANMAN-BIRTH`'s own definition is "birth, begetting and the generation of the world in the cosmogonic hymns". Used for childbirth it silently mixes parturition with cosmogony. Only the companion `offspring` (200) is on-topic. |
| **38** | `viśvedevāḥ` ranked above `indraḥ` for functional range; 12 deities all at `type_breadth 15` | Breadth here is a proxy for mantra count against an 89-item vocabulary that saturates. `viśvedevāḥ` beats `indraḥ` with 28% of the mantras. The metric measures corpus size, not function — and function is not modelled at all. |
| **21, 34, 36, 37** | Concept prominence, co-occurrence and centrality tables | All computed over a relationship capped at 4 per passage, with 19.9% of passages absent and 44.7% of edges at confidence 0.42. Ranks are indicative; magnitudes are not comparable across concepts with different base rates; and the degree distribution is too flat (5,730 mantras tied at the ceiling) for any centrality measure to discriminate. Treating the 47,542 `ABOUT_CONCEPT` edges as a dense semantic layer — a mean of 534 edges per concept — overstates what 89 alias-matched buckets can support. |
| **22, 49** | `shared >= 3: 5194 pairs`, `shared >= 5: 0 pairs` | Concept-overlap count is presented as conceptual similarity. Under a 4-edge cap it is degenerate: a 5-concept overlap is arithmetically impossible, and a 3-concept overlap means only "both passages saturated on the same generic vocabulary". |
| **23, 33** | `4` deity co-occurrence pairs at mantra level | Reads as "Vedic deities are almost never invoked together", which is false. It is an encoding artefact: joint invocations are collapsed into opaque composite nodes such as `VG:DEVATA:INDRAGNI` (117 mantras) that are never decomposed. |
| **41** | 9 clean `natural phenomenon → deities` rows | Reads as a personification finding. The `method` is `concept-lexicon-related-devata`: the edge exists because the deity's *name* is the concept's Sanskrit lemma. It is lexical identity presented as semantic association, covering only 30 of 214 devatās. |
| **29** | A per-relationship-type provenance audit | The one ANSWERABLE_NOW question with a trap of its own: two vocabularies (`trust`, `provenance_class`) describe the same idea, and `EXACT_PARALLEL_OF` is split across both (750 edges with `trust`, 256 with `provenance_class`). An audit that queries one property misses a quarter of that relationship type. |

### One further hazard, not tied to a single question

`MENTIONS_LEMMA` and `MENTIONS_ENTITY` both have **exactly 9,000 edges** over **exactly 6,560** of the 10,552 RV mantras (62.2%), with identical mean degree (1.372) on both. Two independently derived annotation layers landing on the same round number with the same coverage is the signature of a truncated export, not a natural distribution. Any lexical-coverage claim built on these two relationships should be treated as unverified until the loader is checked.

---

## Appendix: corrections to prior assumptions

Three working assumptions held before this audit were wrong, and V2 planning should use the corrected facts.

| Assumption | Measured reality |
| --- | --- |
| `HAS_DEVATA` / `HAS_RISHI` / `HAS_CHANDAS` have 0% provenance on the edge; the loader discards `provenance_class` and `scope_origin`. | **Both properties are present on 100% of these edges.** `HAS_DEVATA`: `SOURCE_DERIVED_SCOPE/SUKTA_WIDE` 8,329, `SOURCE_EXPLICIT/MANTRA_RANGE` 1,882, `SOURCE_EXPLICIT/SINGLE_MANTRA` 347. `HAS_RISHI`: 10,093 / 382 / 90. `HAS_CHANDAS`: 6,276 / 3,670 / 577. The gap is not that provenance is missing; it is that per-mantra attribution barely exists (3.3% of deity edges) and that the obvious query ignores the property that is there. |
| The LLM semantic pilot covered 448 Rigvedic mantras. | The pilot edges in the live graph are **Atharvaveda and Yajurveda only** — YV 415 edges over 207 mantras, AV 321 edges over 157 mantras, 363 distinct mantras and 736 edges in total. Zero Rigvedic, zero Samavedic. All are `state = CANDIDATE`. |
| `ABOUT_CONCEPT`'s 47,542 edges are the Rigvedic concept layer. | The concept layer is **fully cross-Veda** — RV 29,713, AV 10,715, YV 4,914, SV 2,200 — and carries `confidence`, `trust`, `method`, `evidence` and `state` on every edge. It is the only semantic layer that spans all four Vedas, which makes its 4-edge-per-passage cap the highest-leverage defect in the graph. |
