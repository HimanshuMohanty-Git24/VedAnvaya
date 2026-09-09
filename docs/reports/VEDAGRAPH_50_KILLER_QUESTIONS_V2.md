# VedaGraph — 50 Killer Questions: Second Pass (Knowledge Model V2)

**Purpose.** This re-runs the answerability audit of `VEDAGRAPH_50_KILLER_QUESTIONS.md` against the graph as it stands after the Knowledge Model V2 pass. Same 50 questions, same numbering, same classification rules. Every verdict below was checked against the live database on the date shown; nothing is inferred from the schema, from `queries.py`, or from the V2 change log.

| Field | Value |
| --- | --- |
| Report date | 2026-09-09 |
| Commit | `bb27f3c` |
| Branch | `semantic-pilot-v1` |
| Database | `bolt://localhost:7687` |
| Graph size | 100,780 nodes / 241,530 relationships (V1: 100,584 / 212,336) |
| Product nodes | 38,297 (`NOT n:Internal`), 100% with `display_label` and `display_type` |
| Internal nodes | 62,483 |
| Probes executed | 71 Cypher probes across the 50 questions |

## Summary

| Status | V1 | V2 | Change |
| --- | --- | --- | --- |
| ANSWERABLE_NOW | 4 | **4** | 0 |
| PARTIALLY_ANSWERABLE | 35 | **41** | +6 |
| NOT_ANSWERABLE | 11 | **5** | −6 |
| **Total** | **50** | **50** | |

### Transition matrix

| From → To | Count | Questions |
| --- | --- | --- |
| NOT_ANSWERABLE → PARTIALLY_ANSWERABLE | 6 | 5, 9, 10, 13, 26, 28 |
| NOT_ANSWERABLE → NOT_ANSWERABLE | 5 | 1, 30, 39, 42, 43 |
| PARTIALLY_ANSWERABLE → PARTIALLY_ANSWERABLE | 35 | all V1 partials |
| PARTIALLY_ANSWERABLE → ANSWERABLE_NOW | **0** | — |
| ANSWERABLE_NOW → ANSWERABLE_NOW | 4 | 6, 8, 29, 50 |
| Regressions (any downgrade) | **0** | — |
| **Unchanged** | **44** | |

**The headline is that V2 moved six questions off the floor and carried none over the line.** That is not a criticism of the work — the substrate under nearly every question improved materially, and three of the V1 top-six blocking gaps are now partly or largely closed. It is a statement about where the remaining distance is. The 41 partials are not 41 near-misses: they cluster on four blockers, and the largest two of those (Rigveda-only attribution, and attribution that is sūkta-scoped rather than per-verse) were explicitly out of scope for V2 and are unchanged.

### Classification rules (unchanged from V1, plus three V2 rules)

- **ANSWERABLE_NOW** — a single Cypher query returns a substantively useful, non-misleading result over the corpus the question names, with evidence or provenance attached.
- **PARTIALLY_ANSWERABLE** — a query returns usable rows, but a careful researcher must attach a stated caveat.
- **NOT_ANSWERABLE** — no graph element even proxies the dimension, or the only proxy is the wrong sense and its rows would be read as an answer they are not.

Rules carried from V1:

1. **Any answer resting solely on the 736-edge LLM pilot slice is capped at PARTIALLY.** Confirmed unchanged: 736 edges, all `state = CANDIDATE`, all `quality_tier = TIER_D`, AV+YV only, over 364 passages.
2. **Any answer that presents `CONTAINER_INHERITED` attribution as a per-verse fact is capped at PARTIALLY** — and named as a hazard.

Rules added for this pass:

3. **Recall on the new mention layer is unmeasured, so it is capped at PARTIALLY for any frequency, prominence, centrality or similarity claim.** The 4-edge cap that capped `ABOUT_CONCEPT` in V1 is gone, and English evidence is gone, which are both real fixes. But there is still no gold set, 20.6–33.2% of mantras carry no mention at all, and the mean mention degree is 1.884 — so a count is still a lower bound of unknown tightness.
4. **A curated TIER_D assertion is an answer the project is giving, not an answer the corpus is giving.** Axes, `TREATS`, `PROTECTS_FROM` and the ritual apparatus edges are all TIER_D by design. They are honest and they are useful; they are not evidence, and a question they alone answer is PARTIALLY at best.
5. **A handful of rows is PARTIALLY.** 13 epithets, 4 rituals, 42 tribe mentions, 21 metal mentions, 10 named-river mentions.

### What the layer census actually looks like

| Layer | V1 | V2 | Corpus |
| --- | --- | --- | --- |
| `ABOUT_CONCEPT` | 47,542, capped at 4/passage | **47,542, still capped at 4/passage, unchanged** | 4 Vedas, 89 of 163 entities |
| `MENTIONS_ENTITY` → `DomainEntity` | — | 28,675, uncapped (max degree 11), Sanskrit-only | 4 Vedas, 163 of 163 entities |
| `MENTIONS_ENTITY` → `Devata` | 9,000 | **9,000, unchanged, RV-only** | RV only |
| `HAS_DEVATA` | 10,558 | 10,558 (2,229 `PER_PASSAGE`) | RV only |
| `HAS_RISHI` | 10,565 | 10,565 (472 `PER_PASSAGE`) | RV only |
| `HAS_CHANDAS` | 10,523 | 10,523 (4,247 `PER_PASSAGE`) | RV only |
| `MENTIONS_LEMMA` | 9,000 | **9,000, unchanged, RV-only** | RV only |
| LLM pilot predicates | 736 CANDIDATE | **736 CANDIDATE, unchanged** | AV+YV |
| New AV concern predicates | — | `ADDRESSES_CONCERN` 219 (B), `PROTECTS_FROM` 182 (D), `USED_FOR_RITE` 96 (B), `TREATS` 87 (D) | mostly AV |
| New ritual apparatus | — | 33 edges total, all TIER_D | curated |
| Interpretive layer | — | 6 `InterpretiveClaim`, 79 `DerivedMetric`, 1 `CONTRADICTS` pair | about the dataset |

Two facts from that table drive several verdicts below.

First, **`MENTIONS_ENTITY` is an overloaded relationship type.** 28,675 of its 37,675 edges are the new Sanskrit-only four-Veda layer to `DomainEntity`; the other 9,000 are the legacy RV-only layer to `Devata`, which carries no `matched_aliases`, no `evidence` and no `theonym_ambiguous`. `MATCH (p)-[:MENTIONS_ENTITY]->(e)` silently mixes them.

Probe:
```cypher
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e)
WITH CASE WHEN e:DomainEntity THEN 'DomainEntity' ELSE 'Devata' END AS cls, p.veda AS veda, count(*) AS c
RETURN cls, veda, c ORDER BY cls, c DESC
```
5 rows: `Devata/RV 9000`; `DomainEntity/RV 16369`, `DomainEntity/AV 7730`, `DomainEntity/SV 2333`, `DomainEntity/YV 2243`.

Second, **`ABOUT_CONCEPT` was not retired and reaches only 89 of the 163 entities.** So the graph now holds two rival passage→`Concept` layers with different semantics, different coverage and different counts for the same question, and the label does not distinguish them.

Probe:
```cypher
MATCH ()-[:ABOUT_CONCEPT]->(c:Concept) WITH count(DISTINCT c) AS via_about
MATCH ()-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH via_about, count(DISTINCT e) AS via_mention
MATCH (c:Concept) RETURN count(c) AS total, via_about, via_mention
```
`total 163, via_about 89, via_mention 163`. And `ABOUT_CONCEPT` is still `max degree 4`, `avg 2.632`, over 18,062 passages, with 20,350 of 47,542 edges at `confidence = 0.42`. Of the 42 newly typed entities (`Crop`/`Metal`/`Tribe`/`River`/`Condition`/`SocialRite`/`RitualRole`), 42 have mention edges and **1** has an `ABOUT_CONCEPT` edge.

---

## The 50 Questions

### 1. How does Indra's role differ across the four Vedas?

- **V1**: NOT_ANSWERABLE · **V2**: NOT_ANSWERABLE
- **What changed**: Indra gained an identity model (`structure = INDIVIDUAL`, `axes = [WARRIOR, COSMIC_SOVEREIGN, ATMOSPHERIC]`, 5 epithets, denormalised profile arrays) and not a single non-Rigvedic edge. There is no Indra `DomainEntity`, so the new four-Veda mention layer cannot reach him at all.
- **Probe**:
  ```cypher
  MATCH (e:DomainEntity) WHERE any(x IN ['indra','varuṇ','rudra','viṣṇ','mitra','maruts']
    WHERE toLower(e.display_label) CONTAINS x) RETURN e.display_label
  ```
  **0 rows.** `MATCH (p:Passage)-[r]->(d:Devata) WHERE d.entity_key CONTAINS 'INDRA' RETURN p.veda, count(*)` is RV-only (`INDRAH 2305`, `INDRAGNI 93`, `INDRABRHASPATI 6`, all via the legacy RV-only mention layer). By contrast the lexicalised deities do reach four Vedas — `fire (agni)` RV 1365 / SV 129 / YV 143 / AV 458; `soma juice` RV 1020 / SV 248 / YV 99 / AV 203; `sun (sūrya)` RV 345 / SV 58 / YV 70 / AV 180. That sharpens the finding rather than softening it: the mention layer can proxy Agni, Soma and Sūrya cross-Veda because those words are also things. Indra is only ever a god, so he has no proxy.
- **Remaining gap**: attribution layer is RV-only; no Indra entity in the mention registry; `axes` are one global assertion per deity rather than a per-Veda profile, so even a curated answer could not be differential.

### 2. Which Rishi families invoke Agni most?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Nothing that bears on the question. A `RishiFamily` label now appears in `db.labels()` and has **zero nodes**. `Rishi` still has five properties, `display_label` is still the bundled inflected Anukramaṇī string, and `occurrence_count` is still `0` on all 367.
- **Probe**:
  ```cypher
  MATCH (f:RishiFamily) RETURN count(*) AS nodes
  ```
  `0`. `MATCH (a)-[r]-(b:RishiFamily) RETURN type(r), count(*)` → 0 rows. The strict Agni join is now writable and nearly empty:
  ```cypher
  MATCH (m:Mantra)-[rr:HAS_RISHI]->(r:Rishi), (m)-[rd:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})
  WHERE rr.attribution_precision='PER_PASSAGE' AND rd.attribution_precision='PER_PASSAGE'
  RETURN r.display_label, count(DISTINCT m) ORDER BY 2 DESC
  ```
  4 rows: `devāḥ 14`, `gāthino viśvāmitraḥ 7`, `agnivaruṇasomāḥ 1`, `brahma 1`.
- **Remaining gap**: `RishiFamily` is declared and empty; no gotra field; no `MEMBER_OF_FAMILY`. Populating a gotra property on 367 nodes is a small bounded acquisition that would also serve Q26 and Q35.

### 3. Which concepts are most strongly associated with Varuna?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Much better substrate, same verdict. Varuṇa now carries `axes = [COSMIC_SOVEREIGN, GUARDIAN_OF_ORDER, AQUATIC]`, `MEMBER_OF → adityah`, and `profile_top_concepts`; the neighbourhood can be computed on Sanskrit evidence only.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:Devata {entity_key:'VG:DEVATA:VARUNAH'})
  MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity)
  RETURN e.display_label AS entity, count(*) AS c ORDER BY c DESC LIMIT 8
  ```
  `fire (agni) 55`, `heaven (dyaus) 45`, `kingship (rājan) 34`, `soma juice 31`, `earth (pṛthivī) 30`, `river (sindhu) 29`, `cosmic order (ṛta) 26`, `protection (śarman) 25`. Restricted to attributed mantras the N is *smaller* than V1: `kingship 12`, `heaven 9`, `ordinance (vrata) 7`. `profile_attributed_total 99`, `profile_attributed_per_passage 17`.
- **Remaining gap**: 17 verse-specific attributions is not a base for an association claim; the top mention co-entity is `fire`, a co-invocation artefact; RV-only. `ṛta` now ranks third rather than below `praise`, which is a real gain from dropping English evidence.

### 4. What offerings are associated with each deity?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The `Offering` vocabulary is still exactly two items but is now four-Veda and Sanskrit-evidenced, and `USES_OFFERING` links two of them to rituals.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[rd:HAS_DEVATA]->(d:Devata), (m)-[:MENTIONS_ENTITY]->(o:Offering)
  RETURN d.display_label AS deity, o.display_label AS off, count(*) AS n,
    sum(CASE rd.attribution_precision WHEN 'PER_PASSAGE' THEN 1 ELSE 0 END) AS per_passage
  ORDER BY n DESC LIMIT 8
  ```
  `Agni/havis 80 (14)`, `Indra/havis 16 (4)`, `the Asvins/havis 15 (1)`, `Indra/dakṣiṇā 15 (2)`, `the All-Gods/havis 10 (0)`, `Ka, the Who/havis 9 (0)`, `Vanaspati/havis 8 (8)`, `the Maruts/havis 8 (3)`. Distribution: `havis` RV 218 / AV 111 / YV 55 / SV 17; `dakṣiṇā` RV 34 / AV 19 / YV 9 / SV 4.
- **Remaining gap**: two offerings for a repertoire of ghṛta, puroḍāśa, paśu, dhānā, apūpa; `MATCH ()-[r:OFFERED_TO|RECEIVES_OFFERING]->()` returns 0 rows, so "associated with" is co-occurrence; and the per-passage column shows most rows are inherited.

### 5. Which rituals invoke both Agni and Indra?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Both V1 failures moved. `Ritual` is a real label with four nodes and curated apparatus; and the composite-deity blocker is closed — `COMPOSED_OF` decomposes 14 dual/composite labels, so `VG:DEVATA:INDRAGNI` now resolves to Agni and Indra.
- **Probe** (ritual side):
  ```cypher
  MATCH (r:Ritual)-[:INVOKES_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})
  MATCH (r)-[:INVOKES_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'})
  RETURN r.display_label
  ```
  **0 rows** — `INVOKES_DEVATA` is 5 edges in total (`yajña→Agni`; `savana→Soma, Soma Pavamāna, Indra`; `agnihotra→Agni`). **Probe** (deity side, now working):
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata) OPTIONAL MATCH (d)-[:COMPOSED_OF]->(part:Devata)
  WITH m, collect(DISTINCT coalesce(part,d)) AS ds WHERE size(ds)>1
  UNWIND ds AS d1 UNWIND ds AS d2 WITH d1,d2 WHERE d1.entity_key<d2.entity_key
  RETURN d1.display_label, d2.display_label, count(*) ORDER BY 3 DESC LIMIT 5
  ```
  `Mitra–Varuna 184`, `Agni–Indra 118`, `Indra–Vayu 33`, `Indra–Soma 17`, `Agni–Soma 12`. Mention-level: `savana`+Indra 231 mantras, `yajña`+Agni 169, `yajña`+Indra 76.
- **Remaining gap**: 4 rituals and 5 `INVOKES_DEVATA` edges, all TIER_D curation. What would make it full: a devatā-per-rite table from the Śrautasūtra apparatus, giving tens of rites with sourced invocation lists.

### 6. Which Rigvedic verses are reused in Samaveda?

- **V1**: ANSWERABLE_NOW · **V2**: ANSWERABLE_NOW
- **What changed**: The layer is unchanged; it now also carries `knowledge_layer = L2_DETERMINISTIC_DERIVED` and `quality_tier = TIER_B` on every edge, so its epistemic status is queryable rather than only documented.
- **Probe**:
  ```cypher
  MATCH (sv:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(rv:Passage {veda:'RV'})
  RETURN count(DISTINCT rv) AS rv_verses, count(DISTINCT sv) AS sv_verses, count(r) AS edges,
         collect(DISTINCT r.quality_tier) AS tier
  ```
  `rv_verses 1421, sv_verses 1662, edges 1684, tier [TIER_B]`. 90.1% of SV mantras have an identified Rigvedic source.
- **Remaining gap**: none for the question as asked. Recall against the traditional concordances is still unverified for want of a gold set.

### 7. How are those verses transformed?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: **Nothing.** No transformation typology was added.
- **Probe**:
  ```cypher
  MATCH (:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(:Passage {veda:'RV'})
  RETURN r.match_level AS ml, count(*) AS c ORDER BY c DESC
  ```
  3 rows: empty string 1180, `SANDHI_INSENSITIVE` 415, `SCRIPT_FOLDED` 89. `REUSES_TEXT_FROM` now has 25 property keys; the five new ones are all grading (`knowledge_layer`, `quality_tier`, `attribution_precision`, `grade_basis`, `levels_reached`) and none is a transformation class.
- **Remaining gap**: no typology (sāman insertion, phonetic lengthening, word substitution, pada reordering, metrical adaptation); 70% of reuse edges have an empty `match_level`.

### 8. Which formulas occur across multiple Vedas?

- **V1**: ANSWERABLE_NOW · **V2**: ANSWERABLE_NOW
- **What changed**: Nothing material; unchanged and now graded.
- **Probe**:
  ```cypher
  MATCH (f:Formula) WHERE size(f.vedas)=4
  RETURN f.display_form AS form, f.occurrence_count AS occ ORDER BY occ DESC LIMIT 5
  ```
  229 four-Veda formulas; `pāta svastibhiḥ sadā naḥ 93`, `viśvā bhuvanā 60`, `parame vyoman 53`, `brahmaṇas pate 38`, `viśvā bhuvanāni 32`.
- **Remaining gap**: none for the question as asked; families are Q27.

### 9. Which crops occur in each Veda?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A `Crop` label with five members exists, so `MATCH (:Crop)` returns rows where V1's probe returned nothing at all.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Crop)
  RETURN c.display_label AS crop,
    sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV, sum(CASE p.veda WHEN 'SV' THEN 1 ELSE 0 END) AS SV,
    sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS YV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV,
    count(*) AS total ORDER BY total DESC
  ```

  | crop | RV | SV | YV | AV | total |
  | --- | --- | --- | --- | --- | --- |
  | barley (yava) | 19 | 2 | 2 | 15 | 38 |
  | grain (dhānya) | 12 | 0 | 1 | 13 | 26 |
  | sesame (tila) | 0 | 0 | 0 | 5 | 5 |
  | rice (vrīhi) | 0 | 0 | 0 | 3 | 3 |
  | beans (māṣa) | 0 | 0 | 0 | 2 | 2 |

- **Remaining gap**: 74 mention edges corpus-wide. Rice at three and beans at two cannot support a distributional statement, and the `RV 0` cells read as absence rather than as a thin alias probe. No godhūma, priyaṅgu, āṇu/śyāmāka; no ploughing or harvest vocabulary to situate them. What would make it full: an agricultural lexicon with attested inflected forms per crop, plus a recall measurement against the Atharvavedic agricultural hymns.

### 10. Which metals occur in each Veda?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A `Metal` label with four members exists, and `ayas` — the absence V1 called decisive — is present.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(m:Metal)
  RETURN m.display_label AS metal, sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV,
    sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS YV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV,
    count(*) AS total ORDER BY total DESC
  ```

  | metal | RV | YV | AV | total |
  | --- | --- | --- | --- | --- |
  | metal (ayas) | 8 | 0 | 3 | 11 |
  | lead (sīsa) | 0 | 3 | 4 | 7 |
  | silver (rajata) | 0 | 1 | 1 | 2 |
  | copper (loha) | 0 | 1 | 0 | 1 |

- **Remaining gap**: 21 mention edges, plus a taxonomy defect that makes the typed query *worse* than the V1 one. **Gold is labelled `Substance`, not `Metal`** — `MATCH (e:DomainEntity) WHERE e.display_label CONTAINS 'gold' RETURN labels(e)` returns `[Concept, DomainEntity, Substance]` — so `MATCH (:Metal)` omits the corpus's most frequent metal. See the misleading-answers section. What would make it full: label `hiraṇya` as `Metal`, and re-probe `ayas` with a real inflected-form list; 8 hits across 10,552 RV mantras is implausibly low.

### 11. Which animals are associated with wealth?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The animal inventory went from 5 to 12 — every gap V1 named (goat, sheep, buffalo, dog, bull, wild beast) is now present — and `MATCH (:Animal)` works as a label match rather than a property filter.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(a:Animal)
  MATCH (p)-[:MENTIONS_ENTITY]->(:DomainEntity {concept_id:'VG:CONCEPT:VASU-WEALTH'})
  RETURN a.display_label AS animal, p.veda AS veda, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 6
  ```
  `cattle/RV 24`, `horse/RV 7`, `cattle/SV 2`, `bull/RV 2`, `bird/RV 2`, `wild animal/RV 1`. Animal totals: `cattle 757`, `horse 234`, `bull 201`, `bird 106`, `serpent 68`, `livestock 57`, `sheep 46`, `wild animal 41`, `buffalo 40`, `goat 17`, `frog 6`, `dog 4`.
- **Remaining gap**: the wealth join fell from 87/79 (V1, English-admitting, capped) to 24/7 (V2, Sanskrit-only) — the shape is right and the N is now too small to rank anything below the top two. Still bare co-occurrence with no typed `SIGNIFIES_WEALTH`; no ant, ass, camel or boar.

### 12. Which deities are associated with healing?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A `HEALER` axis now exists and returns the philologically correct answer directly, which is a genuine new capability.
- **Probe**:
  ```cypher
  MATCH (d:Devata)-[:HAS_AXIS]->(:DeityAxis {axis:'HEALER'})
  RETURN d.display_label AS deity, d.structure AS st, d.profile_attributed_total AS attributed
  ORDER BY attributed DESC
  ```
  7 rows: `the Asvins / PAIR / 631`, `the Waters / GROUP / 45`, `Rudra / INDIVIDUAL / 38`, then four composite labels with `attributed = null` (`the Maruts, Rudra and Visnu`; `Heaven, Earth and the Asvins`; `Soma and Rudra`; `the healing plants`). The corpus-evidenced route is worse: deity × (`Condition` or `Plant`) mentions gives `Indra 36`, `Agni 32`, `the All-Gods 18` at the top, a corpus-size artefact.
- **Remaining gap**: seven curated TIER_D rows, four of which are composite labels with no attribution count. The Atharvaveda — the healing Veda — still has no deity side, so the 87 `TREATS` and 182 `PROTECTS_FROM` edges cannot be joined to any agent. There is no `healing` `HumanConcern`; healing is reachable only as `Condition` + `Plant`.

### 13. Which Atharvaveda passages concern marriage?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A `SocialRite` entity `vivāha` exists with a `USED_FOR_RITE` edge type (TIER_B, Sanskrit mention plus curated whitelist). V1's probe for any marriage concept returned 0 rows; V2 returns 41 edges corpus-wide.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r:USED_FOR_RITE]->(s:SocialRite)
  RETURN s.display_label AS rite, p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  `house building/AV 30`, `marriage/AV 25`, `marriage/RV 16`, `childbirth/AV 11`, `funerary/AV 9`, `childbirth/YV 3`, `funerary/RV 1`, `childbirth/RV 1`.
- **Remaining gap**: recall on the one book that *is* the answer is under 10%. `MATCH (p:Passage {veda:'AV'}) WHERE p.canonical_citation STARTS WITH 'AVS 14.' RETURN count(*)` returns **141**; of those, the number carrying a marriage `USED_FOR_RITE` edge is **14**. Eleven of the 25 AV marriage edges fall outside Kāṇḍa 14 entirely (AVS 9.3.24, 3.10.4, 4.20.3, 12.1.24 …). The structural handle is still untitled: `MATCH (p:Passage {veda:'AV', entity_type:'SECTION'}) RETURN p.display_label, p.native_labels` gives `AVS 14 / ["Kanda"]`. A count over this layer reads as "the Atharvaveda has 25 marriage verses", which is off by an order of magnitude. What would make it full: hymn-level topical labels for the AV kāṇḍas (the Kauśika-sūtra ritual assignments are the natural source), which would also carry Q14, Q15 and Q47.

### 14. Which concern childbirth?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A real fix to the V1 sense-conflation. `sūṣā` (childbirth) exists as a `SocialRite` and `garbha` (embryo) as a `State`, so parturition is now separable from `janman`, which V1 showed conflates birth with cosmogony.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r]->(e:DomainEntity)
  WHERE e.concept_id IN ['VG:CONCEPT:SUSA-CHILDBIRTH','VG:CONCEPT:GARBHA-EMBRYO',
                         'VG:CONCEPT:PRAJA-OFFSPRING','VG:CONCEPT:JANMAN-BIRTH']
  RETURN e.display_label AS ent, type(r) AS rel, p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  On-topic: `embryo/MENTIONS_ENTITY` RV 91 / AV 59 / YV 20 / SV 12; `childbirth/USED_FOR_RITE` AV 11 / YV 3 / RV 1; `offspring/MENTIONS_ENTITY` AV 144 / RV 122 / YV 46 / SV 7. Off-topic and still the largest rows: `birth (janman)/ABOUT_CONCEPT` RV 372 / AV 280.
- **Remaining gap**: 15 childbirth rite edges. No sūtī, no midwifery, no safe-delivery vocabulary. `janman` still outranks every on-topic entity, so the V1 trap is still the first thing a naive query finds.

### 15. Which concern disease?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Twelve named `Condition` entities where V1 had one undifferentiated `yakṣma` bucket, plus a `TREATS` predicate.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Condition)
  RETURN c.display_label AS cond, count(*) AS total,
    sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV
  ORDER BY total DESC
  ```
  `witchcraft (kṛtyā) 65 (0/65)`, `poison (viṣa) 63 (14/49)`, `worms (krimi) 25 (0/24)`, `evil dream 22 (0/21)`, `hereditary disease (kṣetriya) 22 (0/22)`, `ill-named beings 17 (2/15)`, `seizure (grāhi) 15 (1/14)`, `balāsa 12 (0/12)`, `viṣkandha 11 (0/11)`, `cough 7 (0/7)`, `jaundice 6 (2/4)`, `flux (āsrāva) 4 (0/4)`. Generic `yakṣma` remains at AV 62 / RV 24 / YV 6.
- **Remaining gap**: **takman is absent.** A probe of every entity id and Sanskrit alias for `takm` returns only `VG:CONCEPT:YAKSMA-DISEASE`. Fever is the central Atharvavedic disease, and the hymns V1 surfaced by confidence score (AVS 1.25 and relatives) are still unnamed. Two of the twelve conditions (`kṛtyā`, `durṇāman`) are causes rather than diseases and they top the disease table. No apacit, jāyānya, kilāsa, harimā-as-distinct or rājayakṣma.

### 16. Which concern enemies/protection?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The directional structure V1 said was missing now exists — `PROTECTS_FROM`, 182 edges — and the mention side is Sanskrit-only and uncapped. This is the closest miss in the audit.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r:PROTECTS_FROM]->(e)
  RETURN e.display_label AS target, p.veda AS veda, count(*) AS c, collect(DISTINCT r.quality_tier) AS tier
  ORDER BY c DESC
  ```
  `witchcraft/AV 65`, `poison/AV 49`, `evil dream/AV 21`, `ill-named beings/AV 15`, `seizure/AV 14`, `poison/RV 14`, `ill-named/RV 2`, `evil dream/SV 1`, `seizure/RV 1` — all `TIER_D`. Mention side: `protection (śarman)` RV 165 / AV 67 / YV 24 / SV 16 = 272; `enemy (śatru)` RV 147 / AV 78 / YV 7 / SV 10 = 242; `demon (rakṣas)` RV 68 / AV 68 / YV 11 / SV 13 = 160; plus `overcoming rivals (sapatna)` via `ADDRESSES_CONCERN`, AV 87 / YV 7 / RV 6 / SV 1.
- **Remaining gap**: it fails on two specifics. First, `PROTECTS_FROM` targets only the five affliction-type conditions — **there is no `PROTECTS_FROM` edge to `śatru`, `rakṣas` or `sapatna`** — so protection against human and demonic enemies, which is what the question asks, still has no directional edge. Second, the adversary lexicon is two entities where the corpus uses `amitra`, `dviṣ`, `arāti`, `abhimātin`, `durhārd`, `dasyu` and `paṇi`; 242 hits is an unmeasured lower bound on a much larger set. What would make it full: `PROTECTS_FROM` extended to adversary entities, a wider adversary lexicon, and a recall figure.

### 17. What concepts and actions surround Soma?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The neighbourhood is now Sanskrit-only, uncapped and typed by domain label, and the ritual apparatus names the physical process.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:DomainEntity {concept_id:'VG:CONCEPT:SOMA-DRINK'})
  MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity) WHERE e.concept_id<>'VG:CONCEPT:SOMA-DRINK'
  RETURN e.display_label AS ent, [l IN labels(e) WHERE l<>'Concept' AND l<>'DomainEntity'] AS typ,
         count(DISTINCT p) AS n ORDER BY n DESC LIMIT 8
  ```
  `soma pressing [Ritual] 216`, `heaven [CosmicEntity] 91`, `wealth 80`, `cattle [Animal] 74`, `fire [NaturalPhenomenon] 68`, `speech [PhilosophicalConcept] 68`, `insight 52`, `sacrifice [Ritual] 52`. `savana` `USES_OBJECT` → `grāvan`, `ulūkhala`, `pavitra`, `kalaśa`, `camasa`.
- **Remaining gap**: the process is an inventory, not a process — 11 `USES_OBJECT` edges, TIER_D, with no argument structure (agent, instrument, product, sequence). `Action` is still five nouns (`praise`, `birth`, `liberality`, `battle`, `homage`); pressing, filtering, flowing and mixing are still not actions in the graph. `DESCRIBES_ACTION` is still 35 CANDIDATE edges over those same four nouns.

### 18. What actions does Indra perform most often?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The epithet layer records five Indra actions propositionally — `vṛtrahan` "slayer of Vṛtra", `vajrin` "wielder of the vajra", `maghavan`, `puruhūta`, `śakra` — which is exactly the dimension V1 said was absent. Those epithets have no reach into any passage.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[rd:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'}), (m)-[:MENTIONS_ENTITY]->(a:Action)
  RETURN a.display_label AS action, count(*) AS n,
    sum(CASE rd.attribution_precision WHEN 'PER_PASSAGE' THEN 1 ELSE 0 END) AS per_passage ORDER BY n DESC
  ```
  5 rows: `praise 112 (24)`, `birth 46 (5)`, `liberality 44 (5)`, `battle 43 (9)`, `homage 13 (3)`. `praise` and `homage` are still what the poet does. And `MATCH (e:Epithet)-[r]-(x) RETURN type(r), labels(x), count(*)` returns **one row**: `HAS_EPITHET / [Devata] / 13`. There is no `Passage`→`Epithet` edge, and only two FULLTEXT indexes exist (on `Concept` and `Formula`), so the epithets cannot be located in the text either.
- **Remaining gap**: no agentive predicate layer at scale; the epithets that name Indra's deeds cannot be found in a verse. What would make it full: an epithet occurrence pass over the Sanskrit, which would also carry Q42.

### 19. Who are the Rishis most associated with Indra?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The hazard is now first-class. `attribution_precision` is on 100% of edges and `queries.py` ships `rishis_invoking_deity` alongside `rishis_invoking_deity_strict`. The underlying data is unchanged.
- **Probe** (naive and strict, side by side):
  ```cypher
  MATCH (m:Mantra)-[rd:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'})
  MATCH (m)-[rr:HAS_RISHI]->(r:Rishi)
  WITH r, count(DISTINCT m) AS naive, count(DISTINCT CASE WHEN rd.attribution_precision='PER_PASSAGE'
        AND rr.attribution_precision='PER_PASSAGE' THEN m END) AS strict
  RETURN r.display_label, naive, strict ORDER BY naive DESC LIMIT 6
  ```

  | rishi | naive | strict |
  | --- | --- | --- |
  | gāthino viśvāmitraḥ | 217 | 1 |
  | gautamo vāmadevaḥ | 194 | 9 |
  | bārhaspatyo bharadvājaḥ | 165 | 0 |
  | maitrāvaruṇirvasiṣṭhaḥ | 163 | 0 |
  | śaunako gṛtsamadaḥ | 141 | 0 |
  | kāṇvo medhātithiḥ | 81 | 0 |

  The strict leaderboard is a different list: `kāṇvau medhātithimedhyātithī 27`, `gautamo vāmadevaḥ 9`, `bhāgavo nemaḥ 8`, `aindro vasukraḥ 6`, `indraḥ 6`, `kākṣīvataḥ sukīrtiḥ 5`.
- **Remaining gap**: 472 of 10,565 `HAS_RISHI` edges (4.5%) are `PER_PASSAGE`. The property and the strict variant document the hazard; they do not create the missing data. Note also that `Devata.profile_top_rishis` — the denormalised array a product surface would read — holds the **naive** list.

### 20. What roles does Agni have besides physical fire?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The most substantive single improvement in the deity model. Role is now an explicit dimension rather than something the reader infers.
- **Probe**:
  ```cypher
  MATCH (d:Devata {entity_key:'VG:DEVATA:AGNIH'})
  OPTIONAL MATCH (d)-[:HAS_AXIS]->(a:DeityAxis) OPTIONAL MATCH (d)-[:HAS_EPITHET]->(e:Epithet)
  RETURN d.structure, collect(DISTINCT a.axis) AS axes, collect(DISTINCT e.label_iast) AS epithets,
         d.short_description AS desc
  ```
  `INDIVIDUAL`; axes `[PRIESTLY, FIRE_MEDIUM, TERRESTRIAL]`; epithets `[havyavāhana, tanūnapāt, jātavedas, vaiśvānara]`; description "The sacrificial fire, at once the carrier of the offering up to the gods and the divine priest who performs the rite."
- **Remaining gap**: three axis labels, asserted at TIER_D, with no corpus evidence attached to the assertion and no `HAS_ROLE` edge from any passage. `gṛhapati` — Agni as lord of the house, which V1's co-occurrence profile surfaced as `house 134` — is neither an axis nor an epithet. The graph now states three roles confidently and cannot show where any of them is exercised. What would make it full: per-axis evidence passages, so an axis is a claim with a citation rather than a label.

### 21. Which concepts bridge Rigveda and Atharvaveda?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Real resolution where V1 had none. V1's literal answer was "all 89 of 89", which was uninformative; V2 has 163 entities with a genuine distribution.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
  WITH e, count(DISTINCT p.veda) AS vedas RETURN vedas, count(*) AS entities ORDER BY vedas DESC
  ```
  `4 vedas: 100 entities`, `3: 19`, `2: 22`, `1: 22`. Differential prominence RV vs AV, Sanskrit-only: `witchcraft (kṛtyā) 0/65 = 1.000`, `amulet (maṇi) 1/85 = 0.988`, `breath (prāṇa) 3/83 = 0.965`, `overcoming rivals (sapatna) 6/87 = 0.935`, `noose (pāśa) 6/60 = 0.909`, `ascetic heat (tapas) 11/55 = 0.833`.
- **Remaining gap**: recall unmeasured, so a zero-in-RV cell cannot be distinguished from a thin alias probe; and "bridge" implies inheritance rather than parallel development, which needs the diachronic axis the graph does not have (Q36).

### 22. Which passages are lexically different but conceptually similar?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The arithmetic degeneracy is gone — mention degree is no longer capped at 4 (max 11) — but the distribution is now so skewed low that overlap count is still a poor similarity function.
- **Probe**:
  ```cypher
  MATCH (a:Mantra {veda:'RV'})-[:MENTIONS_ENTITY]->(e:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Mantra {veda:'AV'})
  WITH a,b,count(DISTINCT e) AS shared WHERE shared>=5
    AND NOT (a)-[:NEAR_PARALLEL_OF|EXACT_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM|PARALLEL_TO]-(b)
  RETURN count(*) AS pairs
  ```
  `shared>=5: 0 pairs` · `shared>=4: 29 pairs`. Degree distribution over 15,220 mantras with mentions: `1: 6846`, `2: 4914`, `3: 2277`, `4: 857`, `5: 242`, `6: 65`, `7: 14`, `8: 3`, `9: 1`, `11: 1`; mean 1.884.
- **Remaining gap**: no embedding and no vector index — `SHOW INDEXES YIELD type WHERE type='VECTOR'` returns **0 rows**. Overlap count over a 163-entity vocabulary at mean degree 1.9 cannot express conceptual similarity.

### 23. What deity communities emerge from the corpus?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The V1 blocker — zero edges of any type between two `Devata` nodes — is closed. `COMPOSED_OF` gives 28 directed edges over 14 composites, so a deity-to-deity projection exists and GDS can run on it.
- **Probe**: query as in Q5. `Mitra–Varuna 184`, `Agni–Indra 118`, `Indra–Vayu 33`, `Indra–Soma 17`, `Agni–Soma 12`, `Brhaspati–Indra 11`, `Agni–the Maruts 9`, `Indra–Pusan 6`. `MEMBER_OF` adds two groups: `adityah → [Mitra, Pusan, Savitr, Varuna]` and `apridevatah → [barhis, the two divine Hotṛs, the divine doors, Iḷā-Sarasvatī-Mahī, the svāhā calls, Tvaṣṭṛ, Vanaspati]` — the Āprī litany, correctly captured.
- **Remaining gap**: every pair above comes from a dual-deity *label*, not from co-invocation, so the projection pictures the Anukramaṇī's compounding conventions rather than devotional practice. Direct co-attribution is still 6 mantras. Only 14 composites are decomposed, and the registry disagrees with `devata_components.yaml` about `MITRAVARUNAU` (the shipped query's caveat says so). RV-only. No `CO_INVOKED_WITH` derived from textual co-mention.

### 24. What differs between Rigvedic family books and later material?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Nothing structural. RV `structural_path` and `native_labels` are still empty, so maṇḍala still requires string surgery.
- **Probe**:
  ```cypher
  MATCH (m:Mantra {veda:'RV'}) RETURN m.structural_path AS sp, m.native_labels AS nl, count(*) AS c
  ```
  1 row: `[] / [] / 10552`. Contrast on the mention layer is slightly sharper than V1: highest family-book share `wellbeing (svasti) 0.674`, `homage 0.608`, `sacred formulation (brahman) 0.557`, `hero 0.547`; lowest `lifespan (āyus) 0.192`, `soma juice 0.227`, `ocean 0.236`, `stone (grāvan) 0.257`.
- **Remaining gap**: no corpus-stratum dimension; maṇḍala is not a first-class query surface; the strongest signal is still Maṇḍala 9 being the Soma book, a structural fact rather than a finding.

### 25. Which ritual objects recur most?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The largest vocabulary gain in the pass. `Object` went from 6 to 19 and the implement set V1 listed as entirely absent is present: `vedi`, `yūpa`, `sruc`, `camasa`, `kalaśa`, `ulūkhala`, `pavitra`, plus `maṇi`, `varman`, `dundubhi`.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(o:Object)
  RETURN o.display_label AS obj, count(*) AS total,
    sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS RV, sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS AV
  ORDER BY total DESC
  ```

  | obj | total | RV | AV |
  | --- | --- | --- | --- |
  | chariot (ratha) | 473 | 369 | 55 |
  | thunderbolt (vajra) | 275 | 182 | 56 |
  | sacred grass (barhis) | 195 | 127 | 33 |
  | stone (grāvan) | 164 | 113 | 21 |
  | strainer (pavitra) | 103 | 57 | 6 |
  | kindling (samidh) | 98 | 50 | 24 |
  | weapon (āyudha) | 86 | 33 | 39 |
  | amulet (maṇi) | 86 | 1 | 85 |
  | noose (pāśa) | 67 | 6 | 60 |
  | armour (varman) | 53 | 10 | 35 |
  | jar (kalaśa) | 41 | 28 | 4 |
  | altar (vedi) | 17 | 7 | 8 |
  | offering ladle (sruc) | 11 | 8 | 2 |
  | cup (camasa) | 10 | 5 | 4 |
  | mortar (ulūkhala) | 6 | 4 | 2 |
  | sacrificial post (yūpa) | 6 | 2 | 4 |

  (plus `drum 17`, `bowstring 7`, `axe 6`.)
- **Remaining gap**: the question asks about ritual objects and the top two rows are still `chariot` and `thunderbolt`. `Weapon` sub-typing exists but is applied only to `axe`, `bowstring` and `noose` — **`vajra` and `āyudha` are not labelled `Weapon`** — so the sub-type does not do the separating it was added for. The genuinely ritual implements sit at 6–17 mentions, which for `yūpa` (ubiquitous in the Yajurveda) points at a thin alias probe rather than a corpus fact.

### 26. Which rivers occur with which clans?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Both halves now exist as entities — 7 `River` and 5 `Tribe` — where V1 had neither, and the `SINDHU-RIVER` definition's forward reference to "the place layer" is now satisfied by a 10-member `Place` label.
- **Probe** (same passage):
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River), (p)-[:MENTIONS_ENTITY]->(t:Tribe)
  RETURN r.display_label, t.display_label, count(*)
  ```
  **0 rows.** Lifted to hymn granularity it does work:
  ```cypher
  MATCH (h:Passage)-[:CONTAINS]->()-[:MENTIONS_ENTITY]->(r:River)
  MATCH (h)-[:CONTAINS]->()-[:MENTIONS_ENTITY]->(t:Tribe)
  RETURN count(DISTINCT [h.canonical_citation, r.display_label, t.display_label]) AS triples,
         count(DISTINCT h) AS hymns
  ```
  `triples 8, hymns 7`, and the rows are right: RV 3.33 pairs `Vipāś` and `sindhu` with the `Bharatas` — the Viśvāmitra river-crossing hymn — plus RV 3.53 and RV 5.11.
- **Remaining gap**: eight rows is a demonstration, not an answer, and the coverage beneath it distorts. Named-river mentions total **10** (`Paruṣṇī 3`, `Sarayu 2`, `Vipāś 2`, `Yamunā 2`, `Gaṅgā 1`, `Śutudrī 1`) against generic `sindhu` 236; tribes total **42**. **Sarasvatī is not in the `River` layer at all** — she exists only as a `Devata` — so the most-named river in the Rigveda is invisible to `MATCH (:River)`. The Five Peoples are incomplete (no Anu, no Druhyu) and there is no Dāsa, Dasyu, Paṇi, Kīkaṭa or Śimyu. What would make it full: a full Rigvedic onomasticon of hydronyms and ethnonyms, dual-labelled where a name is both river and goddess.

### 27. Which formula families spread across Vedas?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: **Nothing.**
- **Probe**:
  ```cypher
  MATCH ()-[r:SHARES_FORMULA_WITH]->() RETURN count(r) AS c
  ```
  `0`. `Formula` has 24 property keys and none is `family`, `cluster`, `group` or `parent`.
- **Remaining gap**: `SHARES_FORMULA_WITH` remains a declared relationship type with zero instances; no variant grouping over the 4,825 formulas.

### 28. Where do competing interpretations exist?

- **V1**: NOT_ANSWERABLE · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A claim layer now exists with the right shape: 6 `InterpretiveClaim` nodes carrying `claim_text`, `falsifier`, `confidence`, `asserted_by`, `evidence_passages` and `evidence_metrics`, joined by `SUPPORTED_BY` (7), `SUPPORTED_BY_STATISTIC` (6), `CONCERNS` (7) and `CONTRADICTS` (2 directed = 1 pair).
- **Probe**:
  ```cypher
  MATCH (a:InterpretiveClaim)-[:CONTRADICTS]->(b:InterpretiveClaim) RETURN a.claim_id, b.claim_id
  ```
  One genuine pair: `VG:CLAIM:SV-IDENTITY-IS-MELODIC` ↔ `VG:CLAIM:SV-PREDOMINANTLY-RV-REUSE`. Translation multiplicity is unchanged:
  ```cypher
  MATCH (p:Passage)-[:HAS_TRANSLATION]->(t:Translation) WITH p, count(t) AS n RETURN n, count(*)
  ```
  1 row: `n 1, passages 17283`.
- **Remaining gap**: all six claims are about *this dataset's method*, not about the Vedic text — `ANUKRAMANI-ATTRIBUTION-IS-SUKTA-SCOPED`, `CONCEPT-LAYER-LEANS-ON-TRANSLATION`, `AGNI-LEXICALLY-UNDIFFERENTIATED`, `RISHI-ATTRIBUTION-LEAST-VERSE-SPECIFIC`, and the two Sāmaveda claims. A researcher asking where the graph records interpretive disagreement gets one methodological argument about the Sāmaveda's independence. Textual interpretation still has a single witness per passage, two translators who partition rather than overlap, and zero Sāmavedic translation. What would make it full: a second translation for any part of the corpus, or claim nodes whose subject is a passage's meaning.

### 29. Which graph claims are textual and which are interpretive?

- **V1**: ANSWERABLE_NOW · **V2**: ANSWERABLE_NOW
- **What changed**: This was already the graph's strength and V2 made it materially stronger. The two rival V1 vocabularies are subsumed under one that covers every edge.
- **Probe**:
  ```cypher
  MATCH ()-[r]->() WHERE r.knowledge_layer IS NULL RETURN type(r) AS t, count(*) AS c
  ```
  **0 rows** — all 241,530 edges are graded. Layer × tier: `L2_DETERMINISTIC_DERIVED/TIER_B 149,102`, `L1_SOURCE_EXPLICIT/TIER_A 91,163`, `L4_INTERPRETIVE_CLAIM/TIER_D 1,042`, `L3_LLM_EXTRACTED/TIER_D 736`, `L4_INTERPRETIVE_CLAIM/TIER_B 104`. `attribution_precision`: `PER_PASSAGE 216,832` / `CONTAINER_INHERITED 24,698`.
- **Remaining gap**: none for answerability. Two residual defects worth recording. (a) The V1 defect is masked rather than fixed: `MATCH ()-[r:EXACT_PARALLEL_OF]->() RETURN count(r), count(r.trust), count(r.provenance_class), count(r.knowledge_layer)` returns `1006 / 750 / 256 / 1006`. The legacy split survives; it no longer breaks an audit because `knowledge_layer` covers all 1,006. (b) `TIER_C` is 0 only because the 736 model candidates are graded `TIER_D` on account of `state = CANDIDATE` — the tier is unexercised rather than clean.

### 30. What evidence supports a civilizational/evolutionary claim?

- **V1**: NOT_ANSWERABLE · **V2**: NOT_ANSWERABLE
- **What changed**: The apparatus arrived and the substance did not. Claim nodes now carry an explicit `falsifier`, and 79 `DerivedMetric` nodes hold `values_json`, `method` and `scope_note` joined by `MEASURES` — genuinely the right machinery. There is still no time axis, and none of the six claims is civilizational or evolutionary.
- **Probe**:
  ```cypher
  MATCH (p:Passage) WITH p LIMIT 5000 UNWIND keys(p) AS k WITH DISTINCT k
  WHERE toLower(k) CONTAINS 'layer' OR toLower(k) CONTAINS 'strat' OR toLower(k) CONTAINS 'period'
     OR toLower(k) CONTAINS 'date' OR toLower(k) CONTAINS 'chron' RETURN collect(k)
  ```
  `[]`. `Passage` has 15 property keys and none is temporal.
- **Remaining gap**: no diachronic or stratigraphic dimension anywhere. An evolutionary claim cannot be evidenced by a graph with no time axis, however good the claim scaffolding is. What would make it answerable: relative-chronology annotation (family books vs Maṇḍala 1/8/9/10; AV Kāṇḍa 8–18 vs 1–7; Paippalāda-only material; khila) as a first-class property, plus at least one claim whose subject is the corpus's history rather than the graph's build.

### 31. Which substances are offered to which deities?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The substance vocabulary went from 6 to 10 (adding `ayas`, `rajata`, `sīsa`, `loha`) and the join is now Sanskrit-only with the inherited share visible.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:MENTIONS_ENTITY]->(s:Substance)
  MATCH (m)-[rd:HAS_DEVATA]->(d:Devata)
  RETURN d.display_label AS deity, s.display_label AS subst, count(DISTINCT m) AS n,
    sum(CASE rd.attribution_precision WHEN 'PER_PASSAGE' THEN 1 ELSE 0 END) AS per_passage
  ORDER BY n DESC LIMIT 8
  ```
  `Soma Pavamana/soma 404 (23)`, `Indra/soma 307 (61)`, `Soma/soma 63 (16)`, `the Asvins/soma 49 (6)`, `Indra/food 45 (11)`, `Agni/ghṛta 44 (3)`, `the All-Gods/soma 31 (7)`, `the Asvins/madhu 28 (2)`.
- **Remaining gap**: `MATCH ()-[r:OFFERED_TO|RECEIVES_OFFERING]->()` returns 0 rows, so "offered to" is still co-occurrence — nothing distinguishes a substance offered *to* a deity from one the deity *is* (soma) or *carries* (Agni and ghṛta). The top row remains a tautology. The four new substances are metals with 21 mentions between them, so the addition does not help this question. Deity side RV-only.

### 32. What purposes are rituals performed for?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Purpose is now attached to a ritual, which V1 said was impossible because there were no rituals. Three routes exist.
- **Probe** (ritual purpose):
  ```cypher
  MATCH (r:Ritual)-[:PERFORMED_FOR]->(p) RETURN r.display_label, collect(p.display_label)
  ```
  1 row: `sacrifice (yajña) → [wealth (rayi), wellbeing (svasti), lifespan (āyus), offspring (prajā)]` — 4 edges, TIER_D. **Probe** (human concern, TIER_B):
  ```cypher
  MATCH (p:Passage)-[:ADDRESSES_CONCERN]->(h:HumanConcern)
  RETURN h.display_label AS concern, p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  13 rows: `overcoming rivals/AV 87`, `thriving/AV 47`, `thriving/RV 33`, `thriving/YV 12`, `freedom from debt/AV 9`, `freedom from debt/RV 8`, `overcoming rivals/YV 7`, `overcoming rivals/RV 6`, `concord/AV 5`, `thriving/SV 2`, … . `REQUESTS` is unchanged at 109 edges, all `state = CANDIDATE`, `TIER_D`.
- **Remaining gap**: purpose is attached to exactly one of four rituals, by four curated edges. The `HumanConcern` vocabulary is four items (`puṣṭi`, `ṛṇa`, `saṃjñāna`, `sapatna`) and does not include victory, rain, cattle-winning, healing, long life or a son — the standard kāmya list. So the graph knows what one rite is for and what 219 verses want, from a four-item want-vocabulary.

### 33. Which deities co-occur?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Same as Q23 — composite decomposition makes mantra-level pairs computable for the first time.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata) WITH m, count(DISTINCT d) AS n WHERE n>1 RETURN count(*)
  ```
  `6` mantras carry more than one attributed deity. After `COMPOSED_OF` decomposition the pair table is `Mitra–Varuna 184`, `Agni–Indra 118`, `Indra–Vayu 33`, `Indra–Soma 17`, `Agni–Soma 12`.
- **Remaining gap**: the pairs are compounding conventions, not co-invocations. The V1 hymn-level route still gives the Āprī cluster and is still RV-only. What would make it full: a co-mention layer over the Sanskrit deity names across all four Vedas, which is the same acquisition as Q1.

### 34. Which concepts co-occur?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The single reason V1 capped this question — the 4-edge truncation — is gone on the new layer, and English evidence is gone.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e1:DomainEntity), (p)-[:MENTIONS_ENTITY]->(e2:DomainEntity)
  WHERE e1.concept_id < e2.concept_id
  RETURN e1.display_label AS a, e2.display_label AS b, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 8
  ```
  `heaven–earth 262` (dyāvāpṛthivī), `soma juice–soma pressing 216`, `fire–sacrifice 140`, `fire–priest 131`, `fire–heaven 124`, `fire–wealth 113`, `heaven–sun 97`, `heaven–soma juice 91`. Every edge carries `matched_aliases` and `evidence` (28,675 of 28,675).
- **Remaining gap**: this is the second-closest miss, and it fails on rule 3 plus one structural problem. Recall is unmeasured: 20.6–33.2% of mantras have no mention at all, mean degree is 1.884, and 6,846 of 15,220 mantras have degree 1 and therefore contribute no pair. And **two rival layers answer this question with different numbers**: `ABOUT_CONCEPT` gives `heaven–earth 499` for the same pair, is still capped at 4, still holds 20,350 edges at `confidence = 0.42`, and reaches only 89 of the 163 entities. Nothing in the graph tells a reader which layer to use. What would make it full: a measured recall figure, and either retiring `ABOUT_CONCEPT` or renaming it so the two layers cannot be confused.

### 35. Which deities are connected through common Rishis?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The traversal can now be filtered on all four hops, which shows how little of the V1 answer survives.
- **Probe**:
  ```cypher
  MATCH (d1:Devata)<-[a:HAS_DEVATA]-(:Mantra)-[b:HAS_RISHI]->(r:Rishi)
        <-[c:HAS_RISHI]-(:Mantra)-[e:HAS_DEVATA]->(d2:Devata)
  WHERE d1.entity_key<d2.entity_key AND a.attribution_precision='PER_PASSAGE'
    AND b.attribution_precision='PER_PASSAGE' AND c.attribution_precision='PER_PASSAGE'
    AND e.attribution_precision='PER_PASSAGE'
  RETURN d1.display_label, d2.display_label, count(DISTINCT r) ORDER BY 3 DESC LIMIT 6
  ```
  6 rows, all at 1 or 2 shared seers: `Agni–Indra 2`, then `Soma–Varuna`, `Agni–Varuna`, `Indra–Soma`, `Agni–Soma`, `Indra–Varuna` at 1. The naive version still reports `Aśvins–Indra 26`.
- **Remaining gap**: the naive answer is essentially all inheritance, and the strict answer is essentially empty. No `RishiFamily` to aggregate to (0 nodes). RV-only.

### 36. Which concepts increase/decrease in relative prominence by corpus layer?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The numbers now come from Sanskrit-only evidence over 163 entities rather than 89 alias-matched buckets. "Corpus layer" is still not modelled.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
  WITH e, sum(CASE p.veda WHEN 'RV' THEN 1 ELSE 0 END) AS rv,
          sum(CASE p.veda WHEN 'YV' THEN 1 ELSE 0 END) AS yv,
          sum(CASE p.veda WHEN 'AV' THEN 1 ELSE 0 END) AS av
  RETURN e.display_label, round(1000.0*rv/16369,2) AS rv1k, round(1000.0*yv/2243,2) AS yv1k,
         round(1000.0*av/7730,2) AS av1k ORDER BY (1000.0*av/7730 - 1000.0*rv/16369) DESC LIMIT 6
  ```
  `earth (pṛthivī) 19.73 / 44.58 / 36.74`, `world (loka) 1.65 / 10.25 / 15.78`, `sacred formulation (brahman) 12.83 / 17.83 / 24.97`, `offspring (prajā) 7.45 / 20.51 / 18.63`, `amulet (maṇi) 0.06 / 0.00 / 11.00`, `overcoming rivals (sapatna) 0.37 / 3.12 / 11.25`.
- **Remaining gap**: no `CorpusLayer`, no relative dating, no khila marking (see Q30). Veda is still standing in for time, and the RV→YV→AV ordering is an assumption the graph cannot support.

### 37. Which mantras are central bridges between concept communities?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The V1 objection — degree capped at 4 with 5,730 mantras tied at the ceiling, so centrality ranks a truncation artefact — is gone. The new distribution is genuine, and thin.
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH m, count(DISTINCT e) AS deg
  RETURN max(deg) AS maxdeg, avg(deg) AS avgdeg, count(*) AS mantras
  ```
  `maxdeg 11, avgdeg 1.884, mantras 15220`. Coverage by Veda: RV 8,375/10,552 (79.4%), SV 1,358/1,844 (73.6%), AV 4,167/5,839 (71.4%), YV 1,320/1,975 (66.8%). GDS is still installed and `gds.betweenness.stream` / `gds.louvain.stream` / `gds.pageRank.stream` are available.
- **Remaining gap**: 4,990 mantras are isolated in the projection and 6,846 more have degree 1, so 78% of the corpus contributes at most one entity. Betweenness over a 163-node entity graph at mean degree 1.9 has little to discriminate. No confidence weighting (score is 0.9 on 28,164 edges and 0.6 on 511, i.e. effectively binary).

### 38. Which deities have the widest functional range?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: A real functional dimension arrived — 22 `DeityAxis` nodes, 289 `HAS_AXIS` edges — which is precisely what V1 said was unmeasurable. It also introduced a *new* artefact in place of the old one.
- **Probe**:
  ```cypher
  MATCH (d:Devata)-[:HAS_AXIS]->(a:DeityAxis) WHERE a.axis<>'UNSPECIFIED'
  WITH d, count(a) AS axes, collect(a.axis) AS axl
  RETURN d.display_label, axes, axl, d.profile_attributed_total AS attributed
  ORDER BY axes DESC, attributed DESC LIMIT 8
  ```

  | deity | axes | attributed |
  | --- | --- | --- |
  | Agni, Mitra-Varuna, Ratri and Savitr | 4 | null |
  | Agni and the Maruts | 3 | null |
  | Agni, Surya and Anila | 3 | null |
  | Indra accompanied by the Maruts | 3 | null |
  | Soma and Varuna | 3 | null |
  | the Maruts, Rudra and Visnu | 3 | null |
  | the Brahmana, the Fathers, Soma, Heaven-and-Earth and Pusan | 3 | null |
  | Indra and Brhaspati | 3 | null |

  Axis-count distribution: `0 axes: 101 deities`, `1: 54`, `2: 44`, `3: 14`, `4: 1`. Indra and Agni have 3 each and appear nowhere near the top of the ordering.
- **Remaining gap**: the V1 saturation artefact (breadth as a proxy for corpus size) is replaced by a composite-label artefact — a compound name inherits the union of its parts' axes, so the widest-range leaderboard is a list of compounds with no attribution count at all. 47% of deities have no real axis. What would make it full: restrict the ranking to `structure = INDIVIDUAL`, and attach per-axis evidence so range is measured rather than asserted.

### 39. Which rituals have the most complex dependency structure?

- **V1**: NOT_ANSWERABLE · **V2**: NOT_ANSWERABLE
- **What changed**: A ritual *inventory* dimension arrived — this is why Q5 and Q32 moved — but the *procedural* dimension the question names did not. There are 33 apparatus edges across 4 rituals and zero ordering edges.
- **Probe**:
  ```cypher
  MATCH ()-[r]->() WHERE type(r) IN ['PRECEDES','FOLLOWS','REQUIRES','PART_OF','DEPENDS_ON',
    'HAS_STEP','SUB_RITE_OF'] RETURN type(r) AS t, count(*) AS c
  ```
  **0 rows.** The only ritual-to-ritual edge is `BROADER_THAN` (2 pairs: `yajña ⊃ savana`, `yajña ⊃ agnihotra`). Full apparatus census: `USES_OBJECT 11`, `PERFORMED_BY 6`, `INVOKES_DEVATA 5`, `USES_SUBSTANCE 4`, `PERFORMED_FOR 4`, `USES_OFFERING 3` — all `TIER_D` / `L4_INTERPRETIVE_CLAIM`. Ranking 4 rituals by apparatus out-degree gives `yajña 15`, `savana 9`, `agnihotra 3`, `dīkṣā 1`.
- **Remaining gap**: "complexity of dependency structure" has nothing to rank. Out-degree over four curated inventories is not procedure — there is no sequence, no prerequisite, no sub-rite ordering, no officiant-per-step assignment, and no link from the Yajurveda's procedural content to any structured representation. What would make it answerable: a step-level model of even two or three śrauta rites (darśapūrṇamāsa, agnihotra) with `PRECEDES` and `REQUIRES` edges.

### 40. Which objects/weapons belong to which deity narratives?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The object vocabulary tripled and the epithet layer now records one deity-object relation propositionally (`vajrin`, "wielder of the vajra").
- **Probe**:
  ```cypher
  MATCH (m:Mantra)-[:MENTIONS_ENTITY]->(o:Object)
  MATCH (m)-[rd:HAS_DEVATA]->(d:Devata)
  RETURN d.display_label AS deity, o.display_label AS obj, count(DISTINCT m) AS n,
    sum(CASE rd.attribution_precision WHEN 'PER_PASSAGE' THEN 1 ELSE 0 END) AS per_passage
  ORDER BY n DESC LIMIT 8
  ```
  `Indra/vajra 163 (25)`, `the Asvins/ratha 118 (14)`, `Indra/ratha 83 (14)`, `Soma Pavamana/pavitra 52 (4)`, `Indra/grāvan 46 (9)`, `Agni/samidh 45 (10)`, `Agni/ratha 32 (4)`, `the All-Gods/ratha 27 (4)`.
- **Remaining gap**: `MATCH ()-[r]->() WHERE type(r) IN ['WIELDS','ATTRIBUTE_OF','HAS_ATTRIBUTE','NARRATES']` returns 0 rows. No narrative or myth node, so Indra's vajra still cannot be separated from a vajra merely mentioned in an Indra hymn, and 138 of the 163 top rows are `CONTAINER_INHERITED`. The epithet that would carry the claim has no passage reach (Q18).

### 41. Which natural phenomena are personified as deities?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The axis layer supplies the dimension `DEVATA_ASSOCIATED_WITH` could not. V1's objection was that a name-identity mapping cannot capture Indra-and-lightning or Viṣṇu-and-the-sun's-stride; the axes do exactly that.
- **Probe**:
  ```cypher
  MATCH (d:Devata)-[:HAS_AXIS]->(a:DeityAxis)
  WHERE a.axis IN ['SOLAR','ATMOSPHERIC','AQUATIC','DAWN_TIME','LUNAR','NOCTURNAL','TERRESTRIAL',
                   'CHTHONIC','FIRE_MEDIUM']
  RETURN a.axis AS axis, count(d) AS n, collect(d.display_label)[0..6] AS deities ORDER BY n DESC
  ```
  `TERRESTRIAL 18`, `FIRE_MEDIUM 14`, `ATMOSPHERIC 12` (incl. Indra-with-the-Maruts, Vāyu, Parjanya), `SOLAR 11` (incl. Viṣṇu, Pūṣan, Savitṛ, Sūrya), `AQUATIC 8` (incl. Varuṇa, Sarasvatī, Sarasvān, Apāṃ Napāt), `DAWN_TIME 8`, `CHTHONIC 3`, `LUNAR 3`, `NOCTURNAL 2`. The V1 route is unchanged at 9 rows.
- **Remaining gap**: no `PERSONIFIES` predicate — the axes are a cosmological classification, not an assertion that a phenomenon *is* personified, and they are TIER_D curation with no evidence link. `DEVATA_ASSOCIATED_WITH` is still 101 lexical-identity edges over 30 of 214 deities and still mislabelled as association. No cross-Veda side.

### 42. Which deity names/epithets occur in which contexts?

- **V1**: NOT_ANSWERABLE · **V2**: NOT_ANSWERABLE
- **What changed**: The name half was transformed; the context half has no route whatsoever. `Devata` now has `label_en`, `aliases_iast`, `short_description` and `axes` on **214 of 214** nodes; `structure` is populated (`UNSPECIFIED` fell from 209/214 to **1**/214); 13 `Epithet` nodes exist with glosses; `COMPOSED_OF` links composites to parts.
- **Probe**:
  ```cypher
  MATCH (e:Epithet)-[r]-(x) RETURN type(r) AS t, labels(x) AS lx, count(*) AS c
  ```
  **1 row**: `HAS_EPITHET / [Devata] / 13`. There is no edge from any `Passage` to any `Epithet`, and there is no full-text index on `TextVersion` or `Translation` (the only two FULLTEXT indexes are on `Concept` and `Formula`), so an epithet cannot be located in the corpus by any query. The unification defect also survives: `MATCH (d:Devata) WHERE d.entity_key CONTAINS 'AGNI'` returns 11 nodes, and `VG:DEVATA:JATAVEDA-AGNIH` ("Agni Jatavedas") has **no** edge to `VG:DEVATA:AGNIH` even though `jātavedas` is registered as an Agni `Epithet`. Likewise `PAVAMANO-AGNIH` and `RAKSOHAGNIH`.
- **Remaining gap**: no `SAME_AS` / `EPITHET_OF` between `Devata` nodes; 13 epithets over 4 of 214 deities; zero epithet occurrences. What would make it answerable: an epithet occurrence pass over the Sanskrit (a `MENTIONS_EPITHET` layer built the same way as `MENTIONS_ENTITY`), plus `SAME_AS` from the ten epithet-qualified Agni/Indra/Soma nodes to their base deity.

### 43. How does Rudra's corpus profile differ by Veda?

- **V1**: NOT_ANSWERABLE · **V2**: NOT_ANSWERABLE
- **What changed**: Rudra gained `axes = [HEALER, TERRESTRIAL]`, `structure = INDIVIDUAL` and an attribution breakdown, and not one usable non-Rigvedic edge.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r]->(d:Devata) WHERE d.entity_key CONTAINS 'RUDRA'
  RETURN type(r) AS rel, d.entity_key AS k, p.veda AS veda, count(*) AS c ORDER BY c DESC
  ```
  7 rows: `MENTIONS_ENTITY/RUDRAH/RV 128`, `HAS_DEVATA/RUDRAH/RV 38`, `HAS_DEVATA/SOMARUDRAU/RV 4`, `DESCRIBES/RUDRAH/AV 2`, `DESCRIBES/RUDRAH/YV 1`, `HAS_DEVATA/MARUDRUDRAVISNAVAH/RV 1`, `INVOKES/RUDRAH/AV 1`. Outside the Rigveda, Rudra is reachable by **four edges, all from the frozen 736-edge CANDIDATE slice**. `MENTIONS_LEMMA` is still 9,000 edges, RV-only, with `rudrá-` at 128 RV occurrences and nothing elsewhere.
- **Remaining gap**: the Yajurveda's Śatarudriya — the single most important Rudra text in the corpus — still contributes nothing. There is no Rudra `DomainEntity`, so the four-Veda mention layer cannot reach him. `profile_attributed_total = 38` with `per_passage = 8`. What would make it answerable: the same acquisition as Q1 — a non-Rigvedic attribution layer, or a Sanskrit theonym mention layer covering deity names in SV/YV/AV.

### 44. How does Varuna's corpus profile differ from Indra's?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The axes now state the contrast the question is after, cleanly and for the first time.
- **Probe**:
  ```cypher
  MATCH (d:Devata) WHERE d.entity_key IN ['VG:DEVATA:VARUNAH','VG:DEVATA:INDRAH']
  RETURN d.display_label, d.axes, d.profile_attributed_total AS tot,
         d.profile_attributed_per_passage AS pp
  ```
  `Varuna / [COSMIC_SOVEREIGN, GUARDIAN_OF_ORDER, AQUATIC] / 99 / 17`; `Indra / [WARRIOR, COSMIC_SOVEREIGN, ATMOSPHERIC] / 2869 / 655`. Corpus differential on the mention layer: `ordinance (vrata) 7/8 = 0.467`, `kingship 12/41 = 0.226`, `earth 5/66 = 0.070`, `sun 5/84 = 0.056`, `heaven 9/173 = 0.049`.
- **Remaining gap**: the curated half is 3 axis labels against 3, with `COSMIC_SOVEREIGN` shared — which is defensible but is the project's assertion, not the corpus's. The evidenced half remains 29:1 asymmetric (17 verse-specific Varuṇa attributions against 655 for Indra), so every Varuṇa cell is single-digit. `māyā` (`wile`) is in the registry but `pāśa` (the noose) is typed `Object`/`Weapon` and is AV-dominant, so the Varuṇa-noose association a scholar would look for is not reachable through the deity side at all.

### 45. How does Soma behave as deity vs substance?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The V1 defect is now labelled. `theonym_ambiguous` marks mentions reached only through an alias that is also a deity name, and the mention layer admits no English evidence.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(:DomainEntity {concept_id:'VG:CONCEPT:SOMA-DRINK'})
  RETURN r.theonym_ambiguous AS ambiguous, count(*) AS c ORDER BY c DESC
  ```
  `false 1168`, `true 402` — 25.6% of soma mentions are flagged. Cross-tab against the deity side:
  ```cypher
  MATCH (m:Mantra) WITH m,
    EXISTS {(m)-[:HAS_DEVATA]->(d:Devata) WHERE d.entity_key IN
      ['VG:DEVATA:SOMAH','VG:DEVATA:PAVAMANAH-SOMAH']} AS as_deity,
    EXISTS {(m)-[:MENTIONS_ENTITY]->(:DomainEntity {concept_id:'VG:CONCEPT:SOMA-DRINK'})} AS as_subst
  RETURN as_deity, as_subst, count(*) AS n ORDER BY n DESC
  ```
  `F/F 17940`, `F/T 1103`, `T/F 700`, `T/T 467`.
- **Remaining gap**: the flag documents the conflation; it does not resolve it. 700 mantras are Soma-as-deity with no soma mention at all, which is the signature of two incompletely overlapping matchers rather than two senses. The deity side is RV-only against a four-Veda substance side (RV 1,020 / SV 248 / AV 203 / YV 99), so the cross-tab compares unlike corpora. What would make it full: a sense-tagged decision per occurrence rather than a corpus-level ambiguity flag.

### 46. How does Agni behave as deity vs fire vs ritual medium?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Two genuine improvements, neither of which is an answer. `FIRE_MEDIUM` is now a real axis (14 deities), so "ritual medium" is a modelled sense for the first time. And `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED` states in the graph that the corpus does not distinguish the god from the fire and that the project's separation is "an editorial imposition that helps a reader navigate, not a distinction the text draws."
- **Probe**:
  ```cypher
  MATCH (m:Mantra) WITH m,
    EXISTS {(m)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})} AS is_deity,
    EXISTS {(m)-[:MENTIONS_ENTITY]->(:DomainEntity {concept_id:'VG:CONCEPT:AGNI-FIRE'})} AS is_fire,
    EXISTS {(m)-[:MENTIONS_ENTITY]->(:Ritual {concept_id:'VG:CONCEPT:YAJNA-SACRIFICE'})} AS is_yajna
  RETURN is_deity, is_fire, is_yajna, count(*) AS n ORDER BY n DESC
  ```
  8 rows: `F/F/F 16605`, `T/T/F 1008`, `F/T/F 947`, `T/F/F 811`, `F/F/T 623`, `T/T/T 93`, `T/F/T 76`, `F/T/T 47`. The diagnostic cell V1 named — Agni as deity with no fire word — is **811**, slightly larger than V1's 739. `theonym_ambiguous` flags 146 of 2,095 `agni` mentions (7.0%).
- **Remaining gap**: no word-sense disambiguation. The graph's own claim node says the distinction is not derivable, which is honest and is not the answer the question asks for. `FIRE_MEDIUM` is a property of the deity, not of an occurrence, so it cannot partition passages.

### 47. Which passages support healing practices?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: Two new layers. `TREATS` (87 edges) names an affliction a passage addresses, and eight named medicinal plants exist where V1 had one generic `oṣadhi`.
- **Probe** (treatment):
  ```cypher
  MATCH (p:Passage)-[r:TREATS]->(c:Condition)
  RETURN c.display_label AS cond, p.veda AS veda, count(*) AS c, collect(DISTINCT r.quality_tier) AS tier
  ORDER BY c DESC
  ```
  9 rows: `worms/AV 24`, `kṣetriya/AV 22`, `balāsa/AV 12`, `viṣkandha/AV 11`, `cough/AV 7`, `flux/AV 4`, `jaundice/AV 4`, `jaundice/RV 2`, `worms/YV 1` — **every row `TIER_D` / `L4_INTERPRETIVE_CLAIM`**. **Probe** (materia medica):
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(pl:Plant), (p)-[:MENTIONS_ENTITY]->(c:Condition)
  RETURN pl.display_label, c.display_label, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 6
  ```
  `jaṅgiḍa–viṣkandha 6`, `oṣadhi–poison 3`, `oṣadhi–witchcraft 2`, `vanaspati–balāsa 1`, `oṣadhi–worms 1`, `jaṅgiḍa–witchcraft 1`. Plant totals: `oṣadhi 216`, `vanaspati 144`, `darbha 40`, `kuṣṭha 19`, `jaṅgiḍa 16`, `apāmārga 8`, `arundhatī 7`, `gulgulu 4`.
- **Remaining gap**: the layer that makes this look answerable is the interpretive one. `TREATS` and `PROTECTS_FROM` are TIER_D by design — the project's judgement that a verse addressing an affliction is treating it — so an answer built on them is an interpretation presented as a passage list. The corpus-evidenced part, plant × condition, is 10 rows with a maximum of 6. There is still no `Practice`/procedure layer, and no takman (Q15), so the fever hymns that dominate the Atharvavedic healing corpus are unreachable by name.

### 48. Which passages concern prosperity/cattle/agriculture?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: `puṣṭi` (thriving) joined as a `HumanConcern` and five crops joined as `Crop`, so the agricultural leg is no longer a single conflated node.
- **Probe**:
  ```cypher
  MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
  WHERE e:Crop OR e.concept_id IN ['VG:CONCEPT:GO-CATTLE','VG:CONCEPT:VASU-WEALTH',
    'VG:CONCEPT:KSETRA-FIELD','VG:CONCEPT:PASU-LIVESTOCK','VG:CONCEPT:ANNA-FOOD','VG:CONCEPT:PUSTI-THRIVING']
  RETURN e.display_label AS ent, ... per-Veda ... , count(*) AS total ORDER BY total DESC
  ```

  | ent | RV | SV | YV | AV | total |
  | --- | --- | --- | --- | --- | --- |
  | wealth (rayi) | 581 | 95 | 55 | 154 | 885 |
  | cattle (go) | 458 | 76 | 33 | 190 | 757 |
  | food (anna) | 161 | 10 | 17 | 63 | 251 |
  | thriving (puṣṭi) | 33 | 2 | 12 | 47 | 94 |
  | livestock (paśu) | 17 | 0 | 5 | 35 | 57 |
  | field (kṣetra) | 17 | 1 | 1 | 20 | 39 |
  | barley (yava) | 19 | 2 | 2 | 15 | 38 |
  | grain (dhānya) | 12 | 0 | 1 | 13 | 26 |
  | sesame (tila) | 0 | 0 | 0 | 5 | 5 |
  | rice (vrīhi) | 0 | 0 | 0 | 3 | 3 |
  | beans (māṣa) | 0 | 0 | 0 | 2 | 2 |

- **Remaining gap**: two of three legs are strong; agriculture is 113 mention edges across six entities. `kṣetra` fell from 85 `ABOUT_CONCEPT` edges to 39 Sanskrit-only mentions. There is still no ploughing, sowing, harvest, furrow, plough, irrigation or granary vocabulary, so "agriculture" is a crop list rather than an agricultural practice.

### 49. Which cross-Veda passages express similar ideas without textual reuse?

- **V1**: PARTIALLY · **V2**: PARTIALLY_ANSWERABLE
- **What changed**: The anti-join now runs to completion on the new layer where the V1 all-pairs version exhausted the transaction memory pool, because mention degree is low. That is a performance improvement, not an answerability one.
- **Probe**:
  ```cypher
  MATCH (a:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Mantra {veda:'SV'})
  WITH a,b,count(DISTINCT e) AS shared WHERE shared>=3
    AND NOT (a)-[:NEAR_PARALLEL_OF|EXACT_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM|PARALLEL_TO]-(b)
  RETURN count(*) AS pairs
  ```
  `40` (V1 gave 82 on the capped English-admitting layer). The negative side is unchanged and excellent: 6,271 evidence-bearing cross-Veda parallel edges to subtract.
- **Remaining gap**: no embedding, no vector index. A 3-entity overlap over a 163-item vocabulary at mean degree 1.9 still means "both passages named the same few generic things".

### 50. What are the strongest evidence-backed transformations across the four Vedas?

- **V1**: ANSWERABLE_NOW · **V2**: ANSWERABLE_NOW
- **What changed**: Unchanged in substance; now uniformly graded.
- **Probe**:
  ```cypher
  MATCH (a:Passage)-[r:NEAR_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM|EXACT_PARALLEL_OF|PARALLEL_TO]->(b:Passage)
  WHERE a.veda<>b.veda AND r.evidence IS NOT NULL
  RETURN count(*) AS edges, collect(DISTINCT r.quality_tier) AS tiers
  ```
  `edges 6271, tiers [TIER_B]`, all `L2_DETERMINISTIC_DERIVED`. Ranked by lowest token overlap at high character similarity: `RV 1.84.14 → SV UTTARA 3.1.8.2` (sim 0.842, token_jaccard 0.0), `RV 1.18.6 → SV CHANDA 2.8.7` (0.778 / 0.0), `AVS 20.41.2 → SV UTTARA 3.1.8.2` (0.808 / 0.0), `RV 9.66.27 → SV UTTARA 5.2.11.3` (0.776 / 0.0) — the Sāmavedic re-syllabification signature, fully evidenced.
- **Remaining gap**: none for the question as asked. Naming the transformation class is Q7 and is not answerable.

---

## MISSING KNOWLEDGE DIMENSIONS (V2)

Ranked by the number of the 50 questions each gap still blocks or materially degrades. Counts are of questions where the gap is the binding constraint on the verdict, not of questions the gap merely touches.

| # | Missing dimension | Blocks | Questions |
| --- | --- | --- | --- |
| 1 | **The attribution layer is still Rigveda-only.** `HAS_DEVATA` 10,558, `HAS_RISHI` 10,565, `HAS_CHANDAS` 10,523 and `MENTIONS_LEMMA` 9,000 all have **zero** edges on SV, YV and AV. The four-Veda mention layer does not substitute, because it reaches `DomainEntity` only: there is no `DomainEntity` for Indra, Varuṇa, Rudra, Viṣṇu, Mitra or the Maruts, so those deities are literally unreachable outside the Rigveda. Where a deity's name is also a common noun (`agni`, `soma`, `sūrya`, `uṣas`, `vāta`) a lexical proxy exists; where it is not, nothing does. | 19 | 1, 2, 3, 4, 5, 12, 19, 20, 23, 31, 33, 35, 38, 40, 41, 43, 44, 45, 46 |
| 2 | **Attribution is sūkta-scoped, not per-verse.** 2,229 of 10,558 `HAS_DEVATA` (21.1%) and 472 of 10,565 `HAS_RISHI` (4.5%) are `PER_PASSAGE`. Every deity-to-anything count is dominated by labels projected from the hymn onto each of its verses, and the divergence is not marginal — the Indra/ṛṣi leaderboard changes almost completely under a strict filter (Q19). | 16 | 2, 3, 4, 12, 18, 19, 20, 23, 31, 33, 35, 38, 40, 44, 45, 46 |
| 3 | **The mention layer has no measured recall, and it has a rival.** 28,675 edges, uncapped, Sanskrit-only, `evidence` and `matched_aliases` on 100% — a real improvement over V1's capped English-admitting layer. But 4,990 mantras have no mention at all (RV 20.6% / SV 26.4% / AV 28.6% / YV 33.2% uncovered), mean degree is 1.884, `score` is effectively binary (0.9 on 28,164 edges, 0.6 on 511), and there is no gold set. Meanwhile `ABOUT_CONCEPT` survives unchanged at 47,542 edges, still capped at 4/passage, still 20,350 edges at `confidence = 0.42`, and reaches only 89 of the 163 entities — so two layers answer the same question with different numbers and nothing marks which is authoritative. | 14 | 3, 11, 16, 17, 21, 22, 24, 34, 36, 37, 44, 47, 48, 49 |
| 4 | **No agentive or verb-argument layer.** `Action` is still five nouns (`praise`, `birth`, `liberality`, `battle`, `homage`), two of which are what the poet does. The 736-edge LLM slice is unchanged and frozen at `state = CANDIDATE`. The new typed predicates are real but thin or interpretive: `ADDRESSES_CONCERN` 219 and `USED_FOR_RITE` 96 at TIER_B; `PROTECTS_FROM` 182, `TREATS` 87 and the 33 ritual apparatus edges at TIER_D. Nothing anywhere records a deity as the subject of a deed with an object — no vṛtrahatya, no vajra-hurling, no cow-releasing, no waters-freeing. | 12 | 1, 4, 5, 17, 18, 20, 31, 32, 39, 40, 45, 46 |
| 5 | **Domain vocabulary is now broad but shallow exactly where the questions land.** 89 → 163 entities with typed labels is the pass's biggest single gain, and four specific holes still decide four verdicts: **no takman** (the central Atharvavedic disease); **gold labelled `Substance` and not `Metal`**, so the metal query omits the corpus's commonest metal; **Sarasvatī absent from `River`**, so the river query omits the Rigveda's most-named river; and `vajra`/`āyudha` outside `Weapon` while `axe` is inside it. Volumes: 21 metal mentions, 42 tribe mentions, 74 crop mentions, 10 named-river mentions. 24 of 163 entities carry no typed domain label at all. | 9 | 9, 10, 13, 15, 25, 26, 32, 47, 48 |
| 6 | **No diachronic or stratigraphic dimension.** `Passage` has 15 property keys and none contains `layer`, `strat`, `period`, `date` or `chron`. RV `structural_path` and `native_labels` are still empty arrays, so maṇḍala still requires `substring(canonical_key,10,3)`. Veda is being used as a stand-in for time with no warrant. | 5 | 21, 24, 30, 36, 43 |
| 7 | **No procedural ritual structure.** `PRECEDES`, `FOLLOWS`, `REQUIRES`, `PART_OF`, `DEPENDS_ON`, `HAS_STEP` and `SUB_RITE_OF` all have zero instances. Four `Ritual` nodes hold 33 apparatus edges (inventory) and two `BROADER_THAN` pairs (containment). The Yajurveda's procedural content still has no structured representation. | 4 | 5, 25, 32, 39 |
| 8 | **Names and epithets have no occurrence reach, and there is no text index.** `Epithet` has exactly one edge type (`HAS_EPITHET` from `Devata`, 13 edges) and zero passage links. The only two FULLTEXT indexes are on `Concept` and `Formula`; there are **zero** VECTOR indexes. So neither an epithet nor a free-text phrase can be located in `TextVersion` or `Translation`, and non-lexical similarity has no measure. | 4 | 18, 22, 42, 49 |
| 9 | **`RishiFamily` is declared and empty.** 0 nodes, 0 edges. `Rishi` still bundles patronymic and personal name into one inflected `display_label`, and `occurrence_count` is still 0 on all 367. | 3 | 2, 26, 35 |
| 10 | **No word-sense disambiguation.** `theonym_ambiguous` now flags 1,092 of 28,675 mentions (3.8%; 402 of 1,570 for soma, 146 of 2,095 for agni) and `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED` states in the graph that the distinction is not derivable. Both are honest labelling of the problem, not a solution: the ambiguity is recorded per entity, not decided per occurrence. | 2 | 45, 46 |
| 11 | **No interpretation layer over the text.** 6 claims exist and all six are about this dataset's construction. Translation is still 1:1 on all 17,283 `HAS_TRANSLATION` edges, two translators partition rather than overlap, and the Sāmaveda has zero translations. | 2 | 28, 30 |
| 12 | **No transformation typology and no formula-family grouping.** `match_level` is empty on 1,180 of 1,684 RV–SV reuse edges; `SHARES_FORMULA_WITH` is still a declared relationship type with **0** instances; `Formula` has no family/cluster/parent property. | 2 | 7, 27 |

### Against the V1 top six

| V1 rank | V1 gap | Status after V2 | Evidence |
| --- | --- | --- | --- |
| 1 | Concept-layer recall unknown and capped at 4/passage (blocked 20) | **Partially closed** | A new uncapped, Sanskrit-only layer exists (28,675 edges, max degree 11). But `ABOUT_CONCEPT` was retained byte-for-byte — still `max degree 4`, `avg 2.632`, 20,350 edges at `confidence = 0.42` — and recall on the new layer is still unmeasured. Blocking count fell from 20 to 14. |
| 2 | Knowledge layer is Rigveda-only (blocked 19) | **Untouched** | `HAS_DEVATA` / `HAS_RISHI` / `HAS_CHANDAS` / `MENTIONS_LEMMA` remain 100% RV. Still blocks 19. Now the #1 gap. |
| 3 | No genuine per-mantra attribution (blocked 16) | **Untouched in data; closed in labelling** | Counts are identical to V1 (2,229 and 472 verse-specific). What changed is that `attribution_precision` is on every edge and `queries.py` ships strict variants. Still blocks 16. |
| 4 | No domain-specific vocabulary (blocked 13) | **Largely closed, with four decisive residual holes** | 89 → 163 entities; crops, metals, named diseases, ritual implements, named rivers, tribes and ritual roles all now exist. Blocking count fell from 13 to 9, held there by takman, gold-as-`Substance`, Sarasvatī-as-non-`River`, and the tiny volumes. |
| 5 | No typed semantic predicate layer at scale (blocked 13) | **Partially closed** | 584 new typed predicate edges (`ADDRESSES_CONCERN` 219, `PROTECTS_FROM` 182, `USED_FOR_RITE` 96, `TREATS` 87) plus 33 ritual apparatus edges. The 736 CANDIDATE slice is unchanged. No agentive verb layer. Blocking count fell from 13 to 12. |
| 6 | `Devata` identity model absent (blocked 12) | **Largely closed** | `label_en`, `aliases_iast`, `short_description` and `axes` on 214/214; `structure` populated (`UNSPECIFIED` 209/214 → 1/214); `COMPOSED_OF` 28 edges decomposing 14 composites; `HAS_EPITHET` 13; `MEMBER_OF` 13. Residual: 101/214 have no real axis, epithets have zero passage reach, and the ten epithet-qualified `Devata` nodes are still unlinked to their base deity. |
| 7 | `node_type` is a property, not a label (blocked 9) | **Closed** | 22 typed domain labels, all also `DomainEntity`; `MATCH (:Crop)` and `MATCH (:Metal)` work. The closure introduced two new mislabelling hazards (gold, Sarasvatī) and left 24 of 163 entities untyped. |

---

## QUESTIONS AT RISK OF MISLEADING ANSWERS (V2)

Questions where a query returns rows **today** and a researcher reading those rows would draw a false conclusion. A null result announces itself; a plausible table does not.

| Q | The rows you get | Why they mislead | New in V2? |
| --- | --- | --- | --- |
| **10** | `MATCH (:Metal)` → `ayas 11, sīsa 7, rajata 2, loha 1` (21 total) | Reads as "metal is marginal in the Vedas". Gold is labelled `Substance` and not `Metal`, so the typed query silently drops the corpus's most frequent metal. This is **worse than the V1 answer**, which at least surfaced 297 gold rows and could be recognised as incomplete. | **Yes** |
| **26** | `MATCH (:River)` → 6 named rivers, `Gaṅgā 1`, `Śutudrī 1` | Reads as "the Rigveda names six rivers". Sarasvatī — the most-named river in the corpus — exists only as a `Devata` and is invisible to the river label. The 10 named-river mentions against 236 generic `sindhu` also read as a distribution rather than as a probe artefact. | **Yes** |
| **38** | `deity_widest_range` → `Agni, Mitra-Varuna, Ratri and Savitr` (4 axes) above Indra and Agni (3 each) | A composite label inherits the union of its parts' axes, so the widest-functional-range leaderboard is a list of compound Anukramaṇī names, six of the top eight with `profile_attributed_total = null`. The V1 saturation artefact is replaced, not removed. | **Yes** |
| **15** | 12 named conditions, topped by `witchcraft (kṛtyā) 65` | Reads as a named-disease inventory. Two of the twelve are causes rather than diseases and they top the table, and **takman is absent**, so the AV's central disease returns nothing. A researcher would conclude the corpus's commonest affliction vocabulary is sorcery. | **Yes** |
| **13** | `marriage/AV 25` | Reads as "the Atharvaveda has 25 marriage verses". AV Kāṇḍa 14 has 141 passages and 14 of them carry the edge; 11 of the 25 lie outside Kāṇḍa 14. Recall on the gold-standard book is 9.9%. | **Yes** |
| **47** | `TREATS`: `worms/AV 24`, `kṣetriya/AV 22`, `balāsa/AV 12` … | Every row is `TIER_D` / `L4_INTERPRETIVE_CLAIM` — the project's judgement that a verse naming an affliction is treating it. Presented as a passage list it reads as a textual fact. `PROTECTS_FROM` (182) is the same. | **Yes** |
| **9** | `rice 0/0/0/3`, `sesame 0/0/0/5`, `beans 0/0/0/2` | The zero cells read as absence from the Rigveda rather than as a five-term alias probe with 74 total hits. | **Yes** |
| **34, 21, 36, 37, 24, 49** | Any entity frequency, prominence, co-occurrence or centrality table | Two rival passage→`Concept` layers give different answers for the same question. `ABOUT_CONCEPT` reports `heaven–earth 499`; `MENTIONS_ENTITY` reports `262`. `ABOUT_CONCEPT` reaches 89 of 163 entities, so a query written against it returns **nothing at all** for crops, metals, tribes, rivers, conditions, social rites and ritual roles. Nothing in the schema marks which layer is authoritative. | **Yes** |
| **2, 3, 4, 12, 18, 19, 20, 23, 31, 33, 35, 38, 40, 44, 45, 46** | Any deity-to-anything count | 78.9% of `HAS_DEVATA` and 95.5% of `HAS_RISHI` are `CONTAINER_INHERITED`. Unfiltered, a sūkta-wide label is presented as a per-verse fact. Q19 shows the size of the error: `gāthino viśvāmitraḥ` 217 naive against 1 strict. | No (V1) |
| **23, 33** | `Mitra–Varuna 184`, `Agni–Indra 118` | These now look like co-invocation evidence and are not: every pair is generated by decomposing a dual-deity *label*. Direct co-attribution is still 6 mantras out of 10,552. The V1 hazard (4 pairs reading as "deities are never invoked together") is replaced by the inverse hazard. | **Yes** |
| **45, 46** | `theonym_ambiguous false 1168 / true 402`; the 8-cell Agni cross-tab | The flag reads as disambiguation and is annotation. It is set per entity-alias, not decided per occurrence, and it fires on 3.8% of mentions corpus-wide. The `T/F/F 811` Agni cell — deity with no fire word — is larger than V1's 739, which is the same "two overlapping matchers" signature. | Partly |
| **28, 30** | `competing_interpretations` → 1 `CONTRADICTS` pair | Reads as a record of scholarly disagreement about the Vedas. All six claims are about this graph's construction; the one contradiction is a methodological argument about whether textual overlap understates Sāmavedic independence. | **Yes** |
| **42** | 13 epithets with glosses over 4 deities | Reads as an epithet inventory for the corpus. It is a curated sample covering 1.9% of the 214 deity labels, with zero occurrence data, and the ten epithet-qualified `Devata` nodes are not linked to their base deity. | **Yes** |
| **25** | `chariot 473`, `thunderbolt 275` at the top of a "ritual objects" table | Still the V1 hazard: the two commonest rows are not ritual objects. `Weapon` sub-typing exists but excludes `vajra` and `āyudha`, so it does not fix the conflation it was added for. `yūpa 6` and `vedi 17` are implausibly low for the Yajurveda and read as scarcity. | Partly |
| **29** | A per-relationship-type provenance audit | The V1 trap is masked, not removed: `EXACT_PARALLEL_OF` is still split across `trust` (750) and `provenance_class` (256). An audit written against either legacy property still misses part of it; only `knowledge_layer` covers all 1,006. Also `TIER_C = 0` reads as "no medium-quality edges" when it means "the tier is unexercised". | Partly |

### Do `attribution_precision` and the query `caveat` fields mitigate, or merely document?

They are a genuine improvement on V1, where the provenance was on the edge and nothing in the product surface used it. Three specific limits keep them on the documentation side of the line.

1. **The unsuffixed query is still the flattering one.** `rishis_invoking_deity` returns the inherited-inclusive leaderboard and `rishis_invoking_deity_strict` returns the sourced one; only two of the deity queries ship a strict twin, and `Devata.profile_top_rishis` — the denormalised array a product surface reads without writing Cypher — holds the naive list. Documentation that requires the reader to choose the second query does not protect the reader who ran the first.
2. **No caveat covers the hazards the typed-label surface newly created.** The `metals_by_veda` and `rivers_mentioned` caveats do not say that gold is not a `Metal` or that Sarasvatī is not a `River`. These are the two most consequential misreadings in the V2 graph and they are undocumented.
3. **The tier does not travel with the row.** `quality_tier` is on the edge, but a returned row shows `worms (krimi) / AV / 24` whether the edge is TIER_A source-stated or TIER_D interpretive. A row from `TREATS` and a row from `HAS_DEVATA` are typographically identical. Until the grade is projected into the result set, grading is an audit facility rather than a reader-facing safeguard.

What does work, and is worth saying plainly: `knowledge_layer` on 100% of 241,530 edges makes the V1 dual-vocabulary defect unable to break an audit again, and `theonym_ambiguous` puts a previously invisible hazard (Q45, Q46) on the edge where a query can filter it.

---

## What would move the most questions

Three acquisitions, in order of questions unblocked per unit of work.

**1. A non-Rigvedic attribution layer — 19 questions.** This is the single highest-value acquisition and it is not close. It is the binding constraint on Q1 and Q43 outright, and it degrades 17 more. Concretely, an Anukramaṇī-equivalent for the Atharvaveda (the Bṛhat-sarvānukramaṇī, with the Kauśika-sūtra for ritual occasion) plus devatā assignments for the Yajurveda's kaṇḍikās would give the SV/YV/AV side that every cross-Veda deity question currently lacks. A cheaper partial substitute that would move Q1, Q33 and Q43 on its own: extend the Sanskrit mention layer to **theonyms**, registering the ~40 major deities as mention targets with inflected alias lists across all four Vedas. That is the same machinery as the existing 28,675-edge layer applied to a new entity class, and it would end the situation where Agni is reachable in four Vedas because his name is also a noun while Indra is reachable in one.

**2. Verse-level attribution, or an explicit defensibility marking on inherited labels — 16 questions.** The data as it stands cannot support per-verse deity or ṛṣi claims: 21.1% of deity and 4.5% of ṛṣi attributions are verse-specific. Two routes. Acquire a per-mantra source (the Sarvānukramaṇī's mantra-range statements are already partly parsed — `SOURCE_EXPLICIT/MANTRA_RANGE` covers 1,882 deity edges — and pushing that parse further is bounded work). Or, if verse-level truth is not recoverable, mark each inherited label with whether the hymn is homogeneous, so a reader can distinguish "inherited and safe" from "inherited and doubtful" instead of treating all 24,698 `CONTAINER_INHERITED` edges alike.

**3. A recall gold set for the mention layer, plus retirement of `ABOUT_CONCEPT` — 14 questions.** A few hundred human-annotated mantras scored against the 163-entity registry would convert every frequency, prominence, co-occurrence and centrality claim from "unmeasured lower bound" to "measured at precision *p*, recall *r*". This is the only thing standing between Q16, Q21, Q34 and Q48 and an ANSWERABLE_NOW verdict. It should be paired with a decision on `ABOUT_CONCEPT`: either drop it, or rename it so that no query can silently mix a capped English-admitting layer that reaches 89 entities with an uncapped Sanskrit-only layer that reaches 163.

Two smaller items are worth naming because they are near-free relative to their reach. Labelling `hiraṇya` as `Metal` and adding Sarasvatī to `River` removes the two worst new misleading answers in the graph. And a `MENTIONS_EPITHET` pass, built exactly like the existing mention layer, would move Q42 off NOT_ANSWERABLE and materially improve Q18 and Q40.
