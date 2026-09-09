# VedaGraph — 100-Question Baseline Evaluation (Knowledge Model V3)

**Purpose.** This is the measured baseline for the frozen benchmark in
`VEDAGRAPH_100_QUESTION_BENCHMARK_V3.md`. Every one of the 100 verdicts below was produced by running
Cypher against the live database and reading the rows. Nothing is inferred from the schema, from
`src/vedagraph/domain/queries.py`, from the V2 report, or from any change log. Where a V2 verdict is
contradicted, the contradiction is stated.

| Field | Value |
| --- | --- |
| Report date | 2026-09-09 |
| Commit | `bb27f3c` (branch `semantic-pilot-v1`) |
| Database | `bolt://localhost:7687`, Neo4j 5.26, GDS present (446 procedures) |
| Graph size | 100,780 nodes / 242,147 relationships (re-measured, matches baseline) |
| Node labels / relationship types | 44 labels / 51 declared types (49 populated; `SHARES_FORMULA_WITH` and `PARALLEL_TO`-adjacent declarations partly empty) |
| Probes executed | 118 Cypher statements across 16 batches |
| Evaluator | Agent K (did not author Knowledge Model V2) |

---

## Summary — all 100 questions

| Verdict | Count | Share |
| --- | --- | --- |
| `FULLY_ANSWERABLE` | **5** | 5% |
| `PARTIALLY_ANSWERABLE` | **29** | 29% |
| `NOT_ANSWERABLE` | **15** | 15% |
| `MISLEADING` | **51** | 51% |
| **Total** | **100** | **100%** |

## Summary — the existing 50 (Q1–Q50), re-evaluated

| Verdict | V1 | V2 | V3 (this pass) |
| --- | --- | --- | --- |
| `FULLY_ANSWERABLE` | 4 | 4 | **3** |
| `PARTIALLY_ANSWERABLE` | 35 | 41 | **15** |
| `NOT_ANSWERABLE` | 11 | 5 | **3** |
| `MISLEADING` | not a state | not a state | **29** |
| **Total** | 50 | 50 | **50** |

## Summary — the new 50 (Q51–Q100)

| Verdict | Count |
| --- | --- |
| `FULLY_ANSWERABLE` | **2** |
| `PARTIALLY_ANSWERABLE` | **14** |
| `NOT_ANSWERABLE` | **12** |
| `MISLEADING` | **22** |
| **Total** | **50** |

### What the fourth state changes

V2 reported 4 `FULLY` / 41 `PARTIAL` / 5 `NOT` on the same 50 questions and separately listed 26 of
them in a "questions at risk of misleading answers" table. This pass promotes that table to a
verdict. The result is that **29 of the 50 questions V2 counted as mostly-working are, at the query
surface, actively wrong** — and 26 of those 29 were already named as hazards in V2's own appendix. The
headline movement V1→V2→V3 is therefore not `PARTIAL` count going up; it is the discovery that
`PARTIAL` was doing the work of two different states, one of which is safe with a caveat and one of
which is not safe at all.

Three questions moved *up* relative to V2 and it is worth saying so: **Q10** (metals) is no longer
misleading because `hiraṇya` now carries the `Metal` label, giving 105 metal mentions across four
Vedas instead of 21; **Q9** (crops) is no longer misleading because the zero cells turn out to be
correct — *vrīhi*, *tila* and *māṣa* really are absent from the Rigveda; and **Q15** gained *takman* as
a searchable string. Q15 nevertheless stays `MISLEADING`, for a new reason given in its entry.

Three verdicts are harsher than V2's on questions V2 passed: **Q50** drops from `ANSWERABLE_NOW` to
`PARTIALLY_ANSWERABLE` because directional transformation edges exist for exactly one of the six Veda
pairs.

### Classification rules applied

The four definitions are as printed in the frozen benchmark. Two operating rules were used to keep 100
verdicts consistent:

1. **`MISLEADING` requires substantive error, not merely a needed caveat.** A verdict of `MISLEADING`
   was assigned only where the obvious answer's top-ranked members, its zeros, or its class membership
   are wrong. Where the content is directionally right but thin, one-Veda, or visibly small-N, the
   verdict is `PARTIALLY_ANSWERABLE`.
2. **The frozen acceptance criterion binds the evaluator.** Q79 and Q80 both return complete,
   correct censuses and both were graded `PARTIALLY_ANSWERABLE` because the criteria written before
   the evaluation demand one clause each that the graph does not satisfy. Q80's criterion requires a
   per-container homogeneity marker; Q79's requires structural zeros to be distinguishable from low
   coverage inside the matrix itself.

---

# PART 1 — Q1 to Q50

### 1. How does Indra's role differ across the four Vedas? — `MISLEADING`
```cypher
MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata {entity_key:'VG:DEVATA:INDRAH'})
RETURN p.veda AS veda, count(*) AS c ORDER BY c DESC
```
**Result:** exactly one row, `RV 2869`. A second probe confirms `0` `DomainEntity` nodes whose key or
Sanskrit label contains `indra`.
**Why misleading:** the single row reads as "Indra occurs 2,869 times in the Rigveda and not at all in
the other three Vedas". The absence is the absence of the annotation layer, not of Indra. `Devata`
nodes carry `attribution_scope = ['RV']` on all 214, but no deity query returns that field.
**Blocker:** B1 — the attribution layer is Rigveda-only.

### 2. Which Rishi families invoke Agni most? — `MISLEADING`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'}), (p)-[rr:HAS_RISHI]->(r:Rishi)
RETURN r.display_label, count(*) ORDER BY 2 DESC
```
**Result naive:** `gāthino viśvāmitraḥ 179`, `bārhaspatyo bharadvājaḥ 173`, `gautamo vāmadevaḥ 171`,
`maitrāvaruṇirvasiṣṭhaḥ 140`. **Result strict** (`attribution_precision='PER_PASSAGE'` on both edges):
`devāḥ 14`, `gāthino viśvāmitraḥ 7`, `agnivaruṇasomāḥ 1`, `brahma 1` — four rows, and the top one is
not a seer.
**Why misleading:** a 179 becomes a 7; the leaderboard is a table of hymn-level labels projected onto
verses. `RishiFamily` has 0 nodes, so no query returns families at all.
**Blocker:** B3 — attribution is sūkta-scoped (95.5% of `HAS_RISHI` is `CONTAINER_INHERITED`).

### 3. Which concepts are most strongly associated with Varuna? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:VARUNAH'}), (p)-[:MENTIONS_ENTITY]->(e)
RETURN e.display_label, count(*) ORDER BY 2 DESC LIMIT 8
```
**Result naive:** `kingship 12, heaven 9, ordinance 7, earth 5, sun 5, people 4, waters 4, river 4`.
**Strict:** `kingship 6, noose 2, heaven 2, ordinance 2, resolve 1, cosmic order 1`.
**Why misleading:** ranks 2–8 change completely under strict filtering, and `pāśa` — Varuṇa's
defining instrument — only becomes visible when the inherited edges are removed. The answer is also
silently Rigveda-only over a 99-passage base in a 22,537-passage corpus.
**Blocker:** B3.

### 4. What offerings are associated with each deity? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(o:Offering)
RETURN d.label_en, o.display_label, count(*) ORDER BY 3 DESC LIMIT 8
```
**Result:** `Agni/havis 80`, `Indra/havis 16`, `Aśvins/havis 15`, `Indra/dakṣiṇā 15`. Strict:
`Agni 14`, `Vanaspati 8`, `Indra 6`. There are exactly **2** `Offering` nodes in the registry
(`havis`, `dakṣiṇā`), and `RECEIVES_OFFERING` has 0 instances.
**Why misleading:** "associated with" is same-verse co-occurrence, not an offering relation, and the
whole answer collapses to one of two nouns. A researcher reads a deity→offering mapping and is given a
co-mention count over a two-item vocabulary.
**Blocker:** B4 — no agentive or verb-argument layer; `RECEIVES_OFFERING` unpopulated.

### 5. Which rituals invoke both Agni and Indra? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'}),
      (p)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'}) RETURN count(DISTINCT p)
```
**Result:** `0`. Meanwhile `VG:DEVATA:INDRAGNI` has inbound degree 217 and decomposes via
`COMPOSED_OF` to Indra and Agni.
**Why misleading:** a zero reads as "Agni and Indra are never jointly invoked". They are jointly
invoked 217 times, under a compound Anukramaṇī label. A verse-level probe shows 10,546 of 10,552 RV
mantras carry exactly one `HAS_DEVATA` edge and 6 carry two — the data model effectively forbids the
pattern the question asks about.
**Blocker:** B19 — deity co-occurrence exists only as compound-label decomposition.

### 6. Which Rigvedic verses are reused in Samaveda? — `FULLY_ANSWERABLE`
```cypher
MATCH (sv:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(rv:Passage {veda:'RV'})
RETURN count(*), count(DISTINCT sv), count(DISTINCT rv)
```
**Result:** `1684 edges, 1662 SV passages, 1421 RV passages` — 1,662 of the SV's 1,844 mantras (90.1%)
have an RV source. `lcs_ratio`, `token_jaccard`, `edit_ratio` and `similarity` are non-null on 1,684 of
1,684, and each edge carries `evidence` and `parallel_id`.
**Verdict basis:** directional, corpus-complete for the pair the question names, metric-bearing,
evidence-bearing, and the coverage fraction is retrievable. Carried from V2's `ANSWERABLE_NOW`.

### 7. How are those verses transformed? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(:Passage {veda:'RV'})
RETURN r.match_level, count(*) ORDER BY 2 DESC
```
**Result:** `'' 1180`, `SANDHI_INSENSITIVE 415`, `SCRIPT_FOLDED 89`. The typology has three values, one
of which is the empty string on 70.1% of edges.
**Blocker:** B12 — no transformation typology beyond string-normalisation level; no word-substitution,
insertion or metre-change category.

### 8. Which formulas occur across multiple Vedas? — `FULLY_ANSWERABLE`
```cypher
MATCH (f:Formula) RETURN size(coalesce(f.vedas,[])) AS nvedas, count(*) ORDER BY 1 DESC
```
**Result:** `4 vedas: 229`, `3: 1374`, `2: 2040`, `1: 1182`; `cross_veda = true` on 3,643 of 4,825.
Every formula carries `vedas`, `veda_counts`, `occurrence_count`, `mantra_count`, `normalized`,
`source_forms` and `evidence`. Top four-Veda formula: `pāta svastibhiḥ sadā naḥ`, 93 occurrences.
**Verdict basis:** corpus-complete over all four Vedas, per-Veda occurrence vector on every node,
locators retrievable. Carried from V2.

### 9. Which crops occur in each Veda? — `PARTIALLY_ANSWERABLE` *(up from V2's MISLEADING)*
```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Crop) RETURN e.display_label, p.veda, count(*)
```
**Result:** 10 rows. `yava` RV 19 / AV 15 / SV 2 / YV 2; `dhānya` AV 13 / RV 12 / YV 1; `vrīhi` AV 3;
`tila` AV 5; `māṣa` AV 2. Total 74 mentions over 5 crops.
**Why not misleading:** V2 read the zero cells as probe artefacts. They are not — *vrīhi*, *tila* and
*māṣa* are genuinely absent from the Rigveda, and the AV-only distribution is the accepted picture.
**Blocker:** B5 — 5 crops, no measured recall, alias lists of 3–5 members.

### 10. Which metals occur in each Veda? — `PARTIALLY_ANSWERABLE` *(up from V2's MISLEADING)*
```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Metal) RETURN e.display_label, p.veda, count(*)
```
**Result:** 11 rows, 105 mentions. `hiraṇya` RV 38 / AV 34 / SV 6 / YV 6; `ayas` RV 8 / AV 3;
`sīsa` AV 4 / YV 3; `rajata` AV 1 / YV 1; `loha` YV 1.
**Why not misleading:** `hiraṇya` now carries `["Substance","Metal"]`. V2's decisive hazard — gold
invisible to the metal query — is closed in the current graph.
**Blocker:** B5 — 5 metals, no measured recall.

### 11. Which animals are associated with wealth? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(a:Animal), (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:VASU-WEALTH'})
RETURN a.display_label, count(DISTINCT p) ORDER BY 2 DESC
```
**Result:** `go 27, aśva 8, vi 5, vṛṣabha 4, mṛga 2, maṇḍūka 1, ahi 1`.
**Blocker:** B4 — the relation is same-verse co-occurrence, not an asserted association; no
`ASSOCIATED_WITH_CONCEPT` instances exist.

### 12. Which deities are associated with healing? — `MISLEADING`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:BHESAJA-HEALING'})
RETURN d.label_en, count(DISTINCT p) ORDER BY 2 DESC
```
**Result naive:** `Aśvins 7, the Waters 6, All-Gods 4, Rudra 4, Maruts 2, Agni 1`.
**Strict:** `the Waters 3, Heaven and Earth 1, the Aśvins 1` — the Aśvins, the healer gods, fall from
first to joint-last, and the AV, which carries almost all the healing material, contributes nothing
because it has no deity attribution.
**Blocker:** B1, compounded by B3.

### 13. Which Atharvaveda passages concern marriage? — `MISLEADING`
```cypher
MATCH (p:Passage {veda:'AV'})-[:USED_FOR_RITE]->(:SocialRite {entity_key:'VG:CONCEPT:VIVAHA-MARRIAGE'})
RETURN substring(p.canonical_key,10,4) AS kanda, count(*) ORDER BY 2 DESC
```
**Result:** 25 AV passages, `K14: 14`, then singletons across K01, K03, K04, K08, K09, K10, K11, K12,
K18. AV Kāṇḍa 14 — the marriage book — has **141** passages, so recall on the gold-standard book is
9.9%.
**Why misleading:** the 25 rows read as the AV's marriage verse set. They are one verse in ten of the
one book that is entirely about marriage.
**Blocker:** B5 — no measured recall on the rite layer.

### 14. Which concern childbirth? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:USED_FOR_RITE]->(s:SocialRite) RETURN s.display_label, p.veda, count(*)
```
**Result:** `sūṣā` AV 11 / YV 3 / RV 1; also `pitṛyāṇa` AV 9 / RV 1, `śālā` AV 30, `vivāha` AV 25 /
RV 16.
**Verdict basis:** graded one step above Q13 only because no gold book was measured for childbirth; the
recall is unknown rather than known-bad.
**Blocker:** B5.

### 15. Which concern disease? — `MISLEADING`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(c:Condition) RETURN c.display_label, count(*) ORDER BY 2 DESC
```
**Result:** 12 rows, topped by `kṛtyā (witchcraft) 65` and `viṣa (poison) 63`, then `krimi 25`,
`duṣvapnya 22`, `kṣetriya 22`. **`takman` returns nothing under the `Condition` label.**
**Why misleading, and why differently from V2:** *takman* now exists — as one of ten aliases on
`VG:CONCEPT:YAKSMA-DISEASE`, which is labelled `State`, not `Condition`. So the AV's central fever is
(a) invisible to the disease-inventory query and (b) conflated with *yakṣma*, *amīvā* and *rapaḥ* under
a single node. Its 13 mentions (`takman` 7, `takmā` 5, `takmānam` 1, all AV) cannot be separated from
the generic disease word. The top two rows remain causes rather than afflictions.
**Blocker:** B8 — registry shallow and mis-typed exactly where the question lands.

### 16. Which concern enemies/protection? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(e) WHERE e.entity_key IN ['VG:CONCEPT:SATRU-ENEMY','VG:CONCEPT:SARMAN-PROTECTION','VG:CONCEPT:RAKSAS-DEMON','VG:CONCEPT:SAPATNA-RIVAL-OVERCOMING']
RETURN e.display_label, p.veda, count(*)
```
**Result:** 16 rows. `śatru` RV 147 / AV 78 / SV 10 / YV 7; `śarman` RV 165 / AV 67 / YV 24 / SV 16;
`sapatna` AV 87 / YV 7 / RV 6 / SV 1; `rakṣas` RV 68 / AV 68 / SV 13 / YV 11. The vocabulary does
distinguish human rival from demonic enemy from protection.
**Blocker:** B5 — no normalisation in the default query, no measured recall.

### 17. What concepts and actions surround Soma? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:SOMA-DRINK'}), (p)-[:MENTIONS_ENTITY]->(o)
WHERE o.entity_key<>'VG:CONCEPT:SOMA-DRINK' RETURN o.display_label, count(DISTINCT p) ORDER BY 2 DESC
```
**Result:** `savana 216, dyaus 91, rayi 80, go 74, agni 68, vāc 68, dhī 52, yajña 52, sūrya 50, rājan 43`.
**Blocker:** B4 — the "actions" available are five abstract nouns; and the soma sense is undecided
(841 of 1,570 mentions flagged `theonym_ambiguous`, inconsistently — see Q45).

### 18. What actions does Indra perform most often? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:INDRAH'}), (p)-[:MENTIONS_ENTITY]->(a:Action)
RETURN a.display_label, count(DISTINCT p) ORDER BY 2 DESC
```
**Result:** `stoma (praise) 112, janman (birth) 46, dāna (liberality) 44, yudh (battle) 43, namas (homage) 13`.
**Why misleading:** the top-ranked "action Indra performs" is *praise*, which is what the poet does to
Indra. Two of the five nouns are the worshipper's acts. Nothing in the graph records Vṛtra-slaying,
vajra-hurling, cow-releasing or waters-freeing; `PERFORMS_ACTION` has 0 instances.
**Blocker:** B4.

### 19. Who are the Rishis most associated with Indra? — `MISLEADING`
```cypher
// naive vs strict, both run
```
**Result naive:** `gāthino viśvāmitraḥ 217, gautamo vāmadevaḥ 194, bārhaspatyo bharadvājaḥ 165, maitrāvaruṇirvasiṣṭhaḥ 163, śaunako gṛtsamadaḥ 141`.
**Strict:** `kāṇvau medhātithimedhyātithī 27, gautamo vāmadevaḥ 9, bhāgavo nemaḥ 8, aindro vasukraḥ 6, indraḥ 6`.
**Why misleading:** the first-placed seer under the default query does not appear in the strict top
five; the strict leader does not appear in the naive top five. The two answers share one name out of
five.
**Blocker:** B3.

### 20. What roles does Agni have besides physical fire? — `MISLEADING`
```cypher
MATCH (:Devata {entity_key:'VG:DEVATA:AGNIH'})-[:HAS_AXIS]->(x) RETURN x.display_label
```
**Result:** `priestly`, `fire medium`, `terrestrial` — three constants on the node.
**Why misleading:** three axis labels read as a role inventory derived from the corpus. They are a
curated per-node constant (`HAS_AXIS` is 289 edges, all `TIER_D` / `L4_INTERPRETIVE_CLAIM`), identical
in every passage, and Rigveda-scoped. No occurrence anywhere is labelled with a role.
**Blocker:** B17 — no per-occurrence role assignment.

### 21. Which concepts bridge Rigveda and Atharvaveda? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH e, collect(DISTINCT p.veda) AS v
WHERE 'RV' IN v AND 'AV' IN v RETURN count(*)
```
**Result:** `134` of 163 entities occur in both. A rival count from `ABOUT_CONCEPT` reaches only 89
entities in total, so it cannot produce the same list.
**Blocker:** B5 (no recall), compounded by B6 (two rival layers) and B13 (no chance baseline).

### 22. Which passages are lexically different but conceptually similar? — `MISLEADING`
```cypher
MATCH (a:Passage)-[r:PARALLEL_TO]->(b:Passage) RETURN r.veda_pair, count(*)
```
**Result:** 69 edges, `veda_pair` **null on all 69**, `knowledge_layer = L4_INTERPRETIVE_CLAIM`,
`quality_tier = TIER_D`. There is no vector index on the database (`SHOW INDEXES`: 81 indexes, 2
FULLTEXT on `Concept` and `Formula`, **0 VECTOR**), and no fulltext index on `TextVersion` or
`Translation`.
**Why misleading:** the 69 `PARALLEL_TO` edges present themselves as conceptual parallels. They are
TIER_D curated assertions with no Veda pairing, and the only scalable alternative — shared-entity
overlap — is lexical by construction.
**Blocker:** B10 — no non-lexical similarity measure, no text index.

### 23. What deity communities emerge from the corpus? — `MISLEADING`
```cypher
MATCH (c:Devata)-[:COMPOSED_OF]->(a:Devata), (c)-[:COMPOSED_OF]->(b:Devata) WHERE a.entity_key<b.entity_key
MATCH (p)-[:HAS_DEVATA]->(c) RETURN a.label_en, b.label_en, count(*) ORDER BY 3 DESC
```
**Result:** `Mitra–Varuna 184, Agni–Indra 118, Indra–Vayu 33, Indra–Soma 17, Agni–Soma 12`.
**Why misleading:** every pair is manufactured by decomposing a compound label through 28
`COMPOSED_OF` edges over 14 composites. Direct co-attribution is 6 mantras in 10,552. A Louvain run on
the undirected mention+deity projection returns communities whose members are compound Anukramaṇī
names ("Agni, Surya and Anila", "Agni and the Maruts", "Agni, Mitra-Varuna, Ratri and Savitr"), i.e.
the label vocabulary, not the pantheon.
**Blocker:** B19.

### 24. What differs between Rigvedic family books and later material? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p:Passage {veda:'RV', entity_type:'MANTRA'}) RETURN substring(p.canonical_key,10,3) AS m, count(*) ORDER BY m
```
**Result:** `M01 2006, M02 429, M03 617, M04 589, M05 727, M06 765, M07 841, M08 1716, M09 1108, M10 1754`.
Maṇḍala is recoverable only by substring: `structural_path` and `native_labels` are empty arrays on RV
passages, and `Passage` has no `layer`, `strat`, `period` or `date` key.
**Blocker:** B11 — no diachronic dimension; maṇḍala position is being used as a stand-in for stratum.

### 25. Which ritual objects recur most? — `MISLEADING`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(o:Object) RETURN o.display_label, count(*) ORDER BY 2 DESC
```
**Result:** 19 rows led by `ratha (chariot) 473` and `vajra (thunderbolt) 275`, then `barhis 195`,
`grāvan 164`, `pavitra 103`. `vedi 17`, `sruc 11`, `ulūkhala 6`, `yūpa 6`.
**Why misleading:** the two commonest rows of a "ritual objects" table are a vehicle and a weapon. The
`Weapon` sub-label exists but contains `jyā`, `pāśa` and `svadhiti` only, so it does not remove the
conflation it was created for. `yūpa 6` and `vedi 17` across 22,537 passages including the entire
Yajurveda read as scarcity in the text.
**Blocker:** B8.

### 26. Which rivers occur with which clans? — `MISLEADING`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(r:River) RETURN r.display_label, p.veda, count(*) ORDER BY 3 DESC
;; MATCH (p)-[:MENTIONS_ENTITY]->(r:River), (p)-[:MENTIONS_ENTITY]->(t:Tribe) RETURN r.display_label, t.display_label, count(*)
```
**Result:** river table led by `sindhu` RV 181 / AV 32 / SV 15 / YV 8 (236 total), then 6 named
hydronyms with 1–2 mentions each. The river↔tribe query returns **0 rows**. Sarasvatī exists only as
`VG:DEVATA:SARASVATI` and is invisible to `:River`.
**Why misleading:** *sindhu* is the generic noun for "river" and supplies 96% of the table's mass, so
the distribution reads as a hydronym distribution and is a common-noun count. The most-named river in
the Rigveda is absent from the river class. And a 0-row tribe join reads as "no river is associated
with any clan" in a corpus containing RV 7.18.
**Blocker:** B8.

### 27. Which formula families spread across Vedas? — `NOT_ANSWERABLE`
```cypher
MATCH (f:Formula) RETURN [x IN keys(f) WHERE x CONTAINS 'famil' OR x CONTAINS 'clust' OR x CONTAINS 'parent'] LIMIT 1
;; MATCH ()-[r:SHARES_FORMULA_WITH]->() RETURN count(*)
```
**Result:** `[]` and `0`. No family, cluster or parent property exists on `Formula`;
`SHARES_FORMULA_WITH` is a declared relationship type with zero instances.
**Blocker:** B12.

### 28. Where do competing interpretations exist? — `MISLEADING`
```cypher
MATCH (a:InterpretiveClaim)-[:CONTRADICTS]->(b:InterpretiveClaim) RETURN a.claim_id, a.status, b.claim_id, b.status
```
**Result:** one pair (reported twice, both directions): `VG:CLAIM:SV-IDENTITY-IS-MELODIC`
(`RESEARCH_HYPOTHESIS`) against `VG:CLAIM:SV-PREDOMINANTLY-RV-REUSE` (`MODEL_SYNTHESIS`).
**Why misleading:** a `competing_interpretations` result reads as a record of scholarly disagreement
about the Vedas. All 6 `InterpretiveClaim` nodes are about this dataset's construction, and the single
contradiction is a methodological argument about whether textual overlap understates Sāmavedic
independence.
**Blocker:** B16.

### 29. Which graph claims are textual and which are interpretive? — `FULLY_ANSWERABLE`
```cypher
MATCH ()-[r]->() RETURN count(*) AS all, count(r.knowledge_layer) AS with_layer,
  count(r.trust) AS with_trust, count(r.provenance_class) AS with_pc, count(r.quality_tier) AS with_tier
```
**Result:** `all 242147, with_layer 242147, with_trust 106029, with_pc 49971, with_tier 242147`. The
partition: `L2_DETERMINISTIC_DERIVED 149,206 · L1_SOURCE_EXPLICIT 91,163 · L4_INTERPRETIVE_CLAIM 1,042
· L3_LLM_EXTRACTED 736`.
**Verdict basis:** one field partitions 100% of relationships, correctly and completely, and a
per-type breakdown is retrievable. Residual traps, named but not disqualifying: `EXACT_PARALLEL_OF`
still splits across `trust` (750) and `provenance_class` (256), so an audit written on either legacy
field misses part of it; and `TIER_C = 0` reads as "no medium-quality edges" when it means the tier is
unexercised. Carried from V2.

### 30. What evidence supports a civilizational/evolutionary claim? — `MISLEADING`
```cypher
MATCH (c:InterpretiveClaim)-[r]->(x) RETURN c.claim_id, type(r), coalesce(x.display_label,x.metric_name,x.canonical_key)
```
**Result:** 22 rows. `SUPPORTED_BY` points at passages (`RV 10.187.3`, `SV ARANYA 1.7`),
`SUPPORTED_BY_STATISTIC` at `DerivedMetric` nodes. Every one of the 6 claims is about the dataset:
`AGNI-LEXICALLY-UNDIFFERENTIATED`, `ANUKRAMANI-ATTRIBUTION-IS-SUKTA-SCOPED`,
`CONCEPT-LAYER-LEANS-ON-TRANSLATION`, `RISHI-ATTRIBUTION-LEAST-VERSE-SPECIFIC`,
`SV-IDENTITY-IS-MELODIC`, `SV-PREDOMINANTLY-RV-REUSE`.
**Why misleading:** the shape — claim, statement, supporting passages, supporting statistic — is
exactly the shape of a civilizational-evidence record. The content is a methodology note.
**Blocker:** B11 and B16.

### 31. Which substances are offered to which deities? — `MISLEADING`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(s:Substance)
RETURN d.label_en, s.display_label, count(DISTINCT p) ORDER BY 3 DESC
```
**Result naive:** `Soma Pavamana/soma 404, Indra/soma 307, Soma/soma 63, Aśvins/soma 49, Indra/anna 45, Agni/ghṛta 44`.
**Strict:** `Indra/soma 61, Soma Pavamana/soma 23, Soma/soma 16, Indra/anna 11`.
**Why misleading:** the naive leader (`Soma Pavamana`, 404) falls to third under strict filtering, and
the relation is co-occurrence, not offering. `USES_SUBSTANCE` has 4 instances, all curated TIER_D
ritual-inventory edges.
**Blocker:** B3 and B4.

### 32. What purposes are rituals performed for? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (r:Ritual)-[:PERFORMED_FOR]->(x) RETURN r.display_label, collect(x.display_label)
```
**Result:** one row — `yajña → [rayi, prajā, svasti, āyus]`. `PERFORMED_FOR` has 4 instances, all on
one of the 4 `Ritual` nodes, all `TIER_D` / `L4_INTERPRETIVE_CLAIM`.
**Blocker:** B9 and B8 — 4 rituals in the registry, purposes on one of them.

### 33. Which deities co-occur? — `MISLEADING`
Same query and result as Q23. `Mitra–Varuna 184`, `Agni–Indra 118`. Verse-level probe:
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata) WITH p, count(d) AS nd RETURN nd, count(*) ORDER BY nd
```
→ `nd=1: 10546`, `nd=2: 6`.
**Why misleading:** the pair table looks like co-invocation evidence and is compound-label
decomposition. 99.94% of RV mantras carry exactly one deity label.
**Blocker:** B19.

### 34. Which concepts co-occur? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(a), (p)-[:MENTIONS_ENTITY]->(b) WHERE a.entity_key<b.entity_key
WITH a,b,count(DISTINCT p) AS c WHERE c>150 RETURN a.display_label, b.display_label, c ORDER BY c DESC
```
**Result:** exactly 2 pairs above 150 — `dyaus–pṛthivī 262` and `soma–savana 216`. The rival layer
reports `dyaus–pṛthivī` differently because `ABOUT_CONCEPT` is capped at 4 edges per passage and
reaches 89 of 163 entities.
**Blocker:** B5, compounded by B6 and B13.

### 35. Which deities are connected through common Rishis? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (d1:Devata)<-[:HAS_DEVATA]-(:Passage)-[:HAS_RISHI]->(r:Rishi)<-[:HAS_RISHI]-(:Passage)-[:HAS_DEVATA]->(d2:Devata)
WHERE d1.entity_key<d2.entity_key RETURN d1.label_en, d2.label_en, count(DISTINCT r) ORDER BY 3 DESC
```
**Result:** `Aśvins–Indra 26, Agni–Indra 25, Indra–All-Gods 22, Agni–Aśvins 21, Agni–Soma Pavamana 18`.
**Blocker:** B1 (Rigveda only), B3 (95.5% inherited seer edges), B20 (`RishiFamily` empty).

### 36. Which concepts increase/decrease in relative prominence by corpus layer? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p:Passage {entity_type:'MANTRA'}) WITH p.veda AS veda, count(*) AS m
MATCH (q:Passage {veda:veda})-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:YAJNA-SACRIFICE'})
RETURN veda, m, count(*) AS hits, round(1000.0*count(*)/m,2) AS per1k ORDER BY per1k DESC
```
**Result:** `YV 58.73/1k, RV 44.83, SV 37.96, AV 30.83`. Real, normalised, and reproducible for any
entity.
**Blocker:** B11 — "corpus layer" is being operationalised as "Veda", which is a genre distinction,
not a chronological one; no significance statement is available.

### 37. Which mantras are central bridges between concept communities? — `MISLEADING`
```cypher
CALL gds.graph.project('g', ['Passage','DomainEntity'], {MENTIONS_ENTITY:{}})  // directed, the natural projection
CALL gds.betweenness.stream('g', {samplingSize:2000}) ...
```
**Result:** **betweenness 0.0 for every node**, because the natural projection is directed and
bipartite. Re-run with `orientation:'UNDIRECTED'` and `HAS_DEVATA` added, the top nodes are
`Indra 4,028,469` and `Agni 3,056,381` — both `Devata` nodes that exist for the Rigveda only. Degree
centrality on the concept side maxes at 11 (`RV 10.65.11`).
**Why misleading:** the default projection returns a full ranking of zeros that a researcher can sort
and read; the corrected projection returns a ranking dominated by the one annotation layer that covers
one Veda and is 78.9% container-inherited.
**Blocker:** B6, compounded by B1 and B5.

### 38. Which deities have the widest functional range? — `MISLEADING`
```cypher
MATCH (d:Devata)-[:HAS_AXIS]->(x) WHERE x.display_label<>'unspecified' WITH d, count(*) AS axes
MATCH (p)-[:HAS_DEVATA]->(d) RETURN d.label_en, axes, count(*) AS attrib ORDER BY axes DESC, attrib DESC
```
**Result:** first row `Agni, Mitra-Varuna, Ratri and Savitr — 4 axes, 1 attestation`; then Indra
(3 axes, 2,869), Agni (3, 1,988), Varuna (3, 99), Pusan (3, 77).
**Why misleading:** the widest-functional-range leaderboard is topped by a compound Anukramaṇī label
attested once, which inherits the union of its constituents' axes. Range is also a per-node constant,
so it cannot vary with the corpus.
**Blocker:** B17.

### 39. Which rituals have the most complex dependency structure? — `NOT_ANSWERABLE`
```cypher
MATCH (a:Ritual)-[r]->(b:Ritual) RETURN type(r), a.display_label, b.display_label
```
**Result:** 2 rows, both `BROADER_THAN` (`yajña → savana`, `yajña → agnihotra`). `PRECEDES`,
`FOLLOWS`, `REQUIRES`, `PART_OF`, `DEPENDS_ON`, `HAS_STEP` and `SUB_RITE_OF` all have zero instances.
**Blocker:** B9.

### 40. Which objects/weapons belong to which deity narratives? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(w:Weapon) RETURN d.label_en, w.display_label, count(*) ORDER BY 3 DESC
```
**Result:** 7 rows — `Varuna/pāśa 3`, `the horse/svadhiti 2`, `the bowstring/jyā 1`,
`Soma Pavamana/pāśa 1`, `Maruts/pāśa 1`, `Agni/pāśa 1`, `Agni/svadhiti 1`. A second probe on `Object`
returns `Indra/vajra 163`.
**Why misleading:** a weapon table for the Vedic pantheon that returns 10 edges and omits the
`vajra` entirely — because `vajra` is typed `Object`, not `Weapon` — inverts the answer. `āyudha`,
literally "weapon", is also `Object`.
**Blocker:** B8, compounded by B4 (no narrative or instrument role).

### 41. Which natural phenomena are personified as deities? — `MISLEADING`
```cypher
MATCH (n:NaturalPhenomenon) OPTIONAL MATCH (d:Devata) WHERE toLower(d.label_iast)=toLower(n.preferred_label_sa)
RETURN n.display_label, collect(d.label_en)
```
**Result:** 13 rows; matches only for `agni→Agni`, `candramas→the Moon`, `sūrya→Surya`,
`uṣas→Usas`. Empty for `rātri`, `vāta`, `āpaḥ`, `vidyut`, `tamas`, `jyotis`, `samudra`, `vṛṣṭi`, `ahan`.
Direct probe: `VG:DEVATA:RATRIH` (`label_iast = 'rātrī'`) and `VG:DEVATA:APAH` (`'āpas'`) both exist.
**Why misleading:** `PERSONIFIES` has 0 instances, so the only available answer is inflected string
matching, which silently drops Night and the Waters — both of which are `Devata` nodes — because their
deity labels carry different inflectional endings from the concept labels. The result reads as "these
nine phenomena are not personified".
**Blocker:** B8 — no personification relation.

### 42. Which deity names/epithets occur in which contexts? — `NOT_ANSWERABLE`
```cypher
MATCH (p:Passage)-[r]->(e:Epithet) RETURN count(*)
;; MATCH (e:Epithet)-[r]->(x) RETURN type(r), count(*)
```
**Result:** `0` and `0 rows`. `Epithet` has exactly one inbound edge type (`HAS_EPITHET` from
`Devata`, 13 edges) and no outbound edges and no passage reach. No fulltext index on `TextVersion` or
`Translation` exists to locate an epithet in the text.
**Blocker:** B10.

### 43. How does Rudra's corpus profile differ by Veda? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata) WHERE d.label_en CONTAINS 'Rudra' RETURN p.veda, d.label_en, count(*)
```
**Result:** 3 rows, all `RV`: `Rudra 38`, `Soma and Rudra 4`, `the Maruts, Rudra and Visnu 1`.
**Why misleading:** an RV-only 38 with no other rows reads as "Rudra is a marginal Rigvedic deity
absent from the later Vedas". The Yajurveda's Śatarudriya is one of the most extensive Rudra texts in
the corpus and contributes zero rows because the YV has no deity attribution and Rudra has no
`DomainEntity` to be mentioned as.
**Blocker:** B1, compounded by B2.

### 44. How does Varuna's corpus profile differ from Indra's? — `MISLEADING`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(d:Devata) WHERE d.entity_key IN ['VG:DEVATA:INDRAH','VG:DEVATA:VARUNAH']
RETURN d.label_en, rd.attribution_precision, count(*)
```
**Result:** `Indra CONTAINER_INHERITED 2214 / PER_PASSAGE 655`; `Varuna CONTAINER_INHERITED 82 /
PER_PASSAGE 17`. Axes: Indra `[cosmic sovereign, atmospheric, warrior]`, Varuna `[aquatic, cosmic
sovereign, guardian of order]`.
**Why misleading:** a 29:1 volume ratio, of which 77% and 83% respectively is hymn-level inheritance,
is presented as a difference in profile. The axis vectors are curated constants and do not derive from
the comparison.
**Blocker:** B1, B3, B17.

### 45. How does Soma behave as deity vs substance? — `MISLEADING`
```cypher
MATCH ()-[r:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:SOMA-DRINK'})
UNWIND r.matched_aliases AS a RETURN a, r.theonym_ambiguous, count(*) ORDER BY 3 DESC
```
**Result:** `soma / true / 405`, `somo / false / 208`, `somam / true / 156`, `somasya / true / 143`,
**`somaṃ` / false / 143**, `somaḥ / true / 115`. Corpus totals: `true 841`, `false 729`.
**Why misleading, and this is a new finding:** `theonym_ambiguous` reads as a sense decision. It is a
per-alias-string annotation and it is **internally inconsistent across sandhi variants of the same
form** — `somam` is flagged ambiguous and `somaṃ` is not; `soma` is flagged and `somo` is not. A
researcher filtering on the flag partitions the corpus by orthography, not by sense. A separate
cross-tab against `HAS_DEVATA` gives `deity+word 467`, `deity only 700`, `word only 553` in the RV.
**Blocker:** B7.

### 46. How does Agni behave as deity vs fire vs ritual medium? — `MISLEADING`
```cypher
MATCH (p:Passage {veda:'RV'}) OPTIONAL MATCH (p)-[:HAS_DEVATA]->(d:Devata {entity_key:'VG:DEVATA:AGNIH'})
OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity {entity_key:'VG:CONCEPT:AGNI-FIRE'})
RETURN d IS NOT NULL AS deity, e IS NOT NULL AS word, count(DISTINCT p) ORDER BY 3 DESC
```
**Result:** `F/F 9338`, `T/T 1101`, `T/F 887`, `F/T 264`.
**Why misleading:** the cross-tab reads as a three-way sense split. It is a disagreement between two
matchers — 887 RV verses attributed to Agni with no *agni* token (hymn-level inheritance) and 264 with
the token and no attribution. The graph's own `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED` states that
the distinction is not derivable, which is honest and is not a decision.
**Blocker:** B7.

### 47. Which passages support healing practices? — `MISLEADING`
```cypher
MATCH (p)-[r:TREATS]->(c) RETURN c.display_label, p.veda, r.quality_tier, count(*) ORDER BY 4 DESC
```
**Result:** 9 rows, every one `TIER_D`: `krimi/AV 24`, `kṣetriya/AV 22`, `balāsa/AV 12`,
`viṣkandha/AV 11`, `kāsa/AV 7`, `āsrāva/AV 4`, `hariman/AV 4`, `hariman/RV 2`, `krimi/YV 1`.
**Why misleading:** every row is `L4_INTERPRETIVE_CLAIM` — the project's judgement that a verse naming
an affliction treats it — and the returned row is typographically identical to a source-stated fact.
The grade is on the edge and does not travel into the result. *takman*, the AV's central affliction, is
absent from the table because it is folded into a `State`-labelled node.
**Blocker:** B8; secondarily, the grade is an audit facility rather than a reader-facing field.

### 48. Which passages concern prosperity/cattle/agriculture? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(e) WHERE e.entity_key IN ['VG:CONCEPT:GO-CATTLE','VG:CONCEPT:VASU-WEALTH','VG:CONCEPT:PUSTI-THRIVING','VG:CONCEPT:KSETRA-FIELD']
RETURN e.display_label, p.veda, count(*)
```
**Result:** 16 rows. `rayi` RV 581 / AV 154 / SV 95 / YV 55; `go` RV 458 / AV 190 / SV 76 / YV 33;
`puṣṭi` AV 47 / RV 33 / YV 12 / SV 2; `kṣetra` AV 20 / RV 17 / SV 1 / YV 1.
**Blocker:** B6 — the rival `ABOUT_CONCEPT` layer returns different numbers for the same four entities
(`agni 2206` vs `2095`, `soma 1841` vs `1570`) and nothing marks which is authoritative; recall
unmeasured on both.

### 49. Which cross-Veda passages express similar ideas without textual reuse? — `MISLEADING`
```cypher
MATCH (a:Passage)-[:MENTIONS_ENTITY]->(e)<-[:MENTIONS_ENTITY]-(b:Passage)
WHERE a.veda='RV' AND b.veda='AV' AND NOT (b)-[:REUSES_TEXT_FROM|EXACT_PARALLEL_OF|NEAR_PARALLEL_OF]-(a)
WITH a,b,count(DISTINCT e) AS shared WHERE shared>=5 RETURN count(*)
```
**Result:** `0`. The distribution of shared-entity counts over RV×AV pairs is
`8:1, 7:1, 6:7, 5:11, 4:77, 3:1482, 2:56892, 1:2090418`.
**Why misleading:** a zero reads as "there are no non-textual conceptual parallels between the Rigveda
and the Atharvaveda", which is false of the corpus and true only of this measure. At a mean mention
degree of 1.88, shared-entity overlap cannot separate similarity from chance: over two million pairs
share exactly one entity and twenty pairs share five or more, all of which turn out to be textual
parallels anyway.
**Blocker:** B10.

### 50. What are the strongest evidence-backed transformations across the four Vedas? — `PARTIALLY_ANSWERABLE` *(down from V2's ANSWERABLE_NOW)*
```cypher
MATCH ()-[r:REUSES_TEXT_FROM]->() RETURN r.veda_pair, count(*)
;; MATCH ()-[r:NEAR_PARALLEL_OF]->() RETURN r.veda_pair, count(*) ORDER BY 2 DESC
```
**Result:** `REUSES_TEXT_FROM` is `RV-SV 1684` and nothing else. `NEAR_PARALLEL_OF` covers all six
pairs (`RV-SV 1180, AV-RV 752, RV-YV 473, AV-SV 326, AV-YV 162, SV-YV 156`) but is symmetric and
carries no transformation type. `match_level` is empty on 1,180 of 1,684.
**Why downgraded:** "across the four Vedas" invites a six-pair answer. Directional, typed
transformation exists for one pair, and its typology is 70% unlabelled. Similarity metrics for the
other five pairs are present, which keeps this above `NOT`.
**Blocker:** B12 and B22.

---

# PART 2 — Q51 to Q100

### 51. Which actions most distinguish Indra from Varuṇa? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata) WHERE d.entity_key IN ['VG:DEVATA:INDRAH','VG:DEVATA:VARUNAH']
MATCH (p)-[:MENTIONS_ENTITY]->(a:Action) RETURN d.label_en, a.display_label, count(*) ORDER BY 1,3 DESC
```
**Result:** 7 rows. Indra: `stoma 112, janman 46, dāna 44, yudh 43, namas 13`. Varuna: `stoma 2,
namas 2`. Nothing else. `Devata` has no outbound action edge of any kind (`HAS_AXIS 289`,
`DEVATA_ASSOCIATED_WITH 140`, `COMPOSED_OF 28`, `HAS_EPITHET 13`, `MEMBER_OF 13`).
**Why misleading:** the table looks like a differential deed profile and is a base-rate artefact —
Indra has 2,869 attributions to Varuṇa's 99 — over a five-noun "action" vocabulary in which the
top-ranked item for both deities is the worshipper's own act of praise. No distinctiveness statistic
is computable and none is offered.
**Blocker:** B4.

### 52. Which deity changes functional profile most across corpus divisions? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(:Devata)-[:HAS_AXIS]->(x:DeityAxis)
RETURN substring(p.canonical_key,10,3) AS div, x.display_label, count(*) ORDER BY div, 3 DESC
```
**Result:** a clean per-maṇḍala axis distribution (M01: `warrior 714, atmospheric 679, cosmic
sovereign 625, terrestrial 484, fire medium 476, priestly 455, dawn time 301, healer 238, …`), and no
rows at all for AV, SV or YV divisions.
**Why misleading:** the table varies across divisions and therefore reads as functional-profile
change. Axes are constants on the `Devata` node, so *no deity's profile changes anywhere* — the
variation is entirely the variation in which deity is attributed to which maṇḍala. The question cannot
be answered wrongly-but-informatively; it can only be answered with a restatement of the deity mix.
**Blocker:** B17.

### 53. Which concepts connect Agni and Soma without simple lexical overlap? — `NOT_ANSWERABLE`
```cypher
MATCH (e1:DomainEntity)-[r]->(e2:DomainEntity) RETURN type(r), count(*) ORDER BY 2 DESC
```
**Result:** the entire concept-to-concept relation inventory is `BROADER_THAN 57`, `USES_OBJECT 11`,
`PERFORMED_BY 6`, `USES_SUBSTANCE 4`, `PERFORMED_FOR 4`, `USES_OFFERING 3` — 85 edges, of which 57 are
taxonomic and 28 are the curated ritual inventory. There are 0 vector indexes. The only scalable route
between two concepts is same-verse co-occurrence, which is the route the question excludes.
**Blocker:** B10.

### 54. Which entities act as bridges between ritual and cosmology? — `PARTIALLY_ANSWERABLE`
```cypher
// passages mentioning a Ritual/Offering/RitualRole ∩ passages mentioning a CosmicEntity, then their other entities
```
**Result:** `ritual_passages 2074`, `cosmic_passages 1922`, `both 149`. Bridge entities in the
intersection: `soma 18, agni 16, janman 9, ojas 7, āpaḥ 6, vedi 6, brahman 6, sūrya 5`.
**Verdict basis:** real rows, plausible content, and the intersection is meaningful. But the
"ritual" side is 11 entities and the "cosmology" side is 4, out of a 163-entity registry, so the
partition is 9% of the ontology, and betweenness on the same graph is dominated by the RV-only deity
layer (see Q96).
**Blocker:** B8.

### 55. Which human concerns dominate the Atharvaveda, normalised per 1,000 mantras? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p:Passage {entity_type:'MANTRA'}) WITH p.veda AS veda, count(*) AS m
MATCH (q:Passage {veda:veda})-[:ADDRESSES_CONCERN]->(c:HumanConcern)
RETURN veda, c.display_label, count(*) AS hits, round(1000.0*count(*)/m,2) AS per1k ORDER BY 2, 4 DESC
```
**Result:** 13 rows. `sapatna` AV 14.90/1k vs RV 0.57 (a 26× ratio); `puṣṭi` AV 8.05 vs RV 3.13;
`ṛṇa` AV 1.54 vs RV 0.76; `saṃjñāna` AV 0.86 vs RV 0.09. All `TIER_B` / `L2_DETERMINISTIC_DERIVED`.
**Verdict basis:** the normalisation works, the AV/RV contrast is large and directionally correct, and
the edges are deterministic rather than curated. But the registry contains exactly **4**
`HumanConcern` nodes. The AV's disease, sorcery, statecraft, dice, snakebite, hair-growth and
sleep material is not represented as concern at all, so "which concerns dominate" is answered over 4
of an appropriate several dozen.
**Blocker:** B8.

### 56. Which Yajurvedic rituals have the richest object/offering networks? — `MISLEADING`
```cypher
MATCH (p:Passage {veda:'YV'})-[:MENTIONS_ENTITY]->(r:Ritual) WITH r, collect(DISTINCT p) AS ps
MATCH (p2:Passage {veda:'YV'})-[:MENTIONS_ENTITY]->(o) WHERE (o:Object OR o:Offering OR o:Substance) AND p2 IN ps
RETURN r.display_label, count(DISTINCT o) AS apparatus, count(*) AS edges ORDER BY 2 DESC
```
**Result:** 3 rows — `yajña 16 apparatus / 38 edges`, `savana 3 / 11`, `dīkṣā 1 / 1`.
**Why misleading:** this reads as a richness ranking over Yajurvedic rites. The registry contains 4
`Ritual` nodes in total; *agnicayana*, *aśvamedha*, *vājapeya*, *rājasūya*, *darśapūrṇamāsa*,
*cāturmāsya* and the rest of the corpus's actual named rites are absent. A three-row ranking of a
ritual corpus, led by the generic word for "sacrifice", presents an ontology gap as a finding about
the Yajurveda.
**Blocker:** B8, compounded by B9.

### 57. Which formula families occur in three or four Vedas? — `NOT_ANSWERABLE`
Same probes as Q27: no `family`/`cluster`/`parent` property on `Formula`, `SHARES_FORMULA_WITH = 0`.
The 229 four-Veda and 1,374 three-Veda counts are per-string, not per-family, and answer Q8 instead.
**Blocker:** B12.

### 58. Which lexical forms are reused while semantic function changes? — `MISLEADING`
```cypher
MATCH (f:Formula)<-[:USES_FORMULA]-(p:Passage) WHERE size(f.vedas)>=3
MATCH (p)-[:MENTIONS_ENTITY]->(e) WITH f, p.veda AS veda, collect(DISTINCT e.display_label) AS ents
WITH f, collect({veda:veda, ents:ents}) AS byveda WHERE size(byveda)>=3 RETURN f.display_label, byveda
```
**Result:** the per-Veda entity profiles of a reused formula are near-identical by construction, e.g.
`abhi gotrāṇi sahasā gāhamāno` → YV `[vīra, ojas]`, RV `[vīra, ojas]`, SV `[ojas, vīra]`,
AV `[ojas]`.
**Why misleading:** the query answers "semantic function never changes under reuse". That is a
tautology of the measure — function is inferred from the tokens, and the tokens are what was reused.
There is no function assignment independent of wording anywhere in the graph.
**Blocker:** B17.

### 59. Which passage pairs have the strongest evidence of *directional* reuse? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (a)-[r:REUSES_TEXT_FROM]->(b) RETURN r.match_level, r.lcs_ratio, r.token_jaccard, a.canonical_citation, b.canonical_citation ORDER BY r.lcs_ratio DESC
;; MATCH ()-[r:REUSES_TEXT_FROM]->() RETURN count(CASE WHEN r.lcs_ratio IS NULL THEN 1 END), count(*)
```
**Result:** top pairs `SV ARANYA 3.2 ← RV 1.91.18` (lcs 1.0, jaccard 0.526), `SV ARANYA 2.3 ← RV 1.7.2`
(1.0 / 0.727), etc. `lcs_ratio` non-null on 1,684 of 1,684.
**Verdict basis:** direction, metrics and spans are all present — for one Veda pair. The direction is
a global pipeline prior (SV borrows from RV) applied uniformly, not a per-pair inference, and no
reason-for-direction field exists on the edge. The other five Veda pairs have only symmetric edges.
**Blocker:** B22.

### 60. Which passage pairs share ritual function without sharing text? — `MISLEADING`
```cypher
MATCH (a)-[:USED_FOR_RITE]->(s:SocialRite)<-[:USED_FOR_RITE]-(b) WHERE a.veda<>b.veda
AND NOT (a)-[:REUSES_TEXT_FROM|EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF]-(b)
RETURN s.display_label, count(*) ORDER BY 2 DESC
```
**Result:** `vivāha 788 pairs`, `sūṣā 94`, `pitṛyāṇa 18`.
**Why misleading:** 788 reads as a substantial cross-Veda ritual-function network. It is the
cross-product of 25 AV × 16 RV marriage-tagged passages (both directions), where the AV tagging has
9.9% recall on the marriage book (Q13). The number scales with the square of a bad probe, so improving
recall would make it look worse, not better, and there is no way to read the pair count as evidence.
**Blocker:** B5.

### 61. Which Devatās are associated with which offerings, on per-verse source-stated evidence? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(o:Offering)
WHERE rd.attribution_precision='PER_PASSAGE' RETURN d.label_en, o.display_label, count(*) ORDER BY 3 DESC
```
**Result:** `Agni/havis 14, Vanaspati/havis 8, Indra/havis 4, the svāhā calls/havis 4, Yama/havis 4,
praise of a patron's gift/dakṣiṇā 3, Maruts/havis 3, the chariot/havis 3`.
**Verdict basis:** the strict filter works and the rows are honest. But "association" is still
same-verse co-occurrence over a two-node offering vocabulary, and the result is Rigveda-only.
**Blocker:** B4.

### 62. Which Rishis show the broadest deity range, after removing sūkta-inherited attribution? — `MISLEADING`
```cypher
// naive and strict deity-range per Rishi
```
**Result naive:** `maitrāvaruṇirvasiṣṭhaḥ 49, śaunako gṛtsamadaḥ 32, kāṇvo medhātithiḥ 30, gāthino viśvāmitraḥ 29, aucathyo dīrghatamāḥ 27`.
**Strict:** `gāthino viśvāmitraḥ 4, agnivaruṇasomāḥ 4, bandhuḥ śrutabandhurviprabandhugaupāyanāḥ 4, indraḥ 3, bhāgavo nemaḥ 2`.
**Why misleading:** the strict answer looks like an answer and is computed on 4.5% of the seer edges.
Its joint leaders include `agnivaruṇasomāḥ` (three gods) and `indraḥ` (a god), which are not seers;
Vasiṣṭha, first by a wide margin naively, does not appear at all. `RishiFamily` has 0 nodes, so no
roll-up is possible, and `Rishi.occurrence_count` is 0 on all 367.
**Blocker:** B3, compounded by B20.

### 63. Which deity pairs co-occur significantly above a chance baseline? — `NOT_ANSWERABLE`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata) WITH p, count(d) AS nd RETURN nd, count(*) ORDER BY nd
```
**Result:** `nd=1: 10546`, `nd=2: 6`. There is no expected-value, chance-model or significance
facility anywhere in the graph, and the population that would supply the observed counts is six
mantras.
**Blocker:** B13, compounded by B19.

### 64. Which concepts are attested in exactly one Veda, and which in all four, at equal evidence strength? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH e, collect(DISTINCT p.veda) AS vs
RETURN size(vs) AS n_vedas, count(*) ORDER BY 1 DESC
```
**Result:** `4 vedas: 100 entities`, `3: 19`, `2: 22`, `1: 22`. The one-Veda set: AV 14 (`āsrāva`,
`balāsa`, `kāsa`, `kṛtyā`, `kṣetriya`, `viṣkandha`, `māṣa`, `tila`, `vrīhi`, `arundhatī`, `gulgulu`,
`jaṅgiḍa`, …), RV 7 (`gaṅgā`, `sarayu`, `śutudrī`, `vipāś`, `yamunā`, `tṛtsu`, `yadu`), YV 1 (`loha`).
**Verdict basis:** the AV-specific set is genuinely informative — the AV's disease and plant
vocabulary really is AV-native. The RV-specific set is not: every member has 1–2 mentions, so
"RV-specific" there means "n=1". Mean mentions per entity is 175.9 with a range of 1–2,095, and 29
entities have fewer than 10. No threshold, no recall figure, no theonyms in the registry.
**Blocker:** B5.

### 65. Which material-culture entities shift distribution across the Vedas, normalised? — `PARTIALLY_ANSWERABLE`
```cypher
// per-1000-mantra rates for Metal / Crop / Animal / Object by Veda
```
**Result:** `Animal` RV 89.7 / SV 80.3 / AV 68.5 / YV 42.0; `Object` SV 97.1 / RV 95.6 / AV 78.1 /
YV 39.0; `Metal` AV 7.2 / YV 5.6 / RV 4.4 / SV 3.3; `Crop` AV 6.5 / RV 2.9 / YV 1.5 / SV 1.1.
**Verdict basis:** the matrix computes, and two of the four shifts are the expected ones (crops and
metals rise in the AV). Two facts keep it from `FULLY`: `Object` at 39.0/1k in the Yajurveda — the
ritual-apparatus Veda — is implausible and is an annotation-density artefact, and the `Object` class
conflates chariots and thunderbolts with ladles and altars. No recall figure, no significance
statement.
**Blocker:** B5.

### 66. Which passages connect a healing act with a named divine invocation in the same verse? — `MISLEADING`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:BHESAJA-HEALING'})
OPTIONAL MATCH (p)-[:HAS_DEVATA]->(d:Devata) OPTIONAL MATCH (p)-[:INVOKES]->(d2:Devata)
RETURN p.veda, count(*) AS healing, count(d) AS with_devata, count(d2) AS with_invokes
```
**Result:** `AV 47 healing / 0 with_devata / 1 with_invokes`; `YV 32 / 0 / 2`; `RV 28 / 28 / 0`;
`SV 2 / 0 / 0`.
**Why misleading:** the join reads as "in the Rigveda, healing is always accompanied by divine
invocation; in the Atharvaveda, essentially never". The AV's healing hymns are addressed to the
Waters, to plants, to Agni and to Rudra throughout; the zero is the absence of the AV attribution
layer. The RV's 28/28 is a tautology — every RV mantra has a `HAS_DEVATA` edge.
**Blocker:** B1.

### 67. Which ritual actions link a substance, an object and a Devatā in one asserted event? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(:Substance), (p)-[:MENTIONS_ENTITY]->(:Object), (p)-[:HAS_DEVATA]->(:Devata)
RETURN count(DISTINCT p)
```
**Result:** `180` passages. But these are three independent edges hanging off one passage, not an
event. The nearest thing to an event representation is the 736-edge `L3_LLM_EXTRACTED` slice
(`DESCRIBES 280`, `INVOKES 222`, `REQUESTS 109`, `PRAISES 38`, `DESCRIBES_ACTION 35`, …), which carries
`object_kind` (`Devata 382`, `Concept 354`), `confidence`, and per-verse evidence with translation
quotes — but all 736 are `state = CANDIDATE`, `TIER_D`, and confined to AV (157 passages) and YV
(207 passages). The sealed RV V3.2 artifact with 554 `EVENT` objects carrying
`actor_entity_id`/`patient`/`action_head` is **not projected**: `MATCH ()-[r]->() WHERE r.run_id
CONTAINS 'v3.2' OR r.run_id CONTAINS '448'` returns 0 rows.
**Blocker:** B4, compounded by B21.

### 68. Which deity epithets cluster with which actions? — `NOT_ANSWERABLE`
`0` epithet→passage edges (Q42) and no verb-argument layer (Q18, Q51). Both sides of the join are
absent.
**Blocker:** B10.

### 69. Where does the same deity occur under different functional roles? — `NOT_ANSWERABLE`
```cypher
MATCH ()-[r:HAS_DEVATA]->() RETURN keys(r), count(*) ORDER BY 2 DESC LIMIT 3
```
**Result:** the property set is `evidence_basis, knowledge_layer, attribution_precision, scope_origin,
quality_tier, provenance_class, grade_basis, source_id, confidence` — no role, no sense, no function.
The same holds for `MENTIONS_ENTITY` (checked for `sense`/`role`/`sem` substrings: `[]`). Roles exist
only as `HAS_AXIS` on the deity node.
**Blocker:** B17.

### 70. What evidence supports the claim that Indra's prominence declines and Rudra's or Viṣṇu's rises? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata) RETURN p.veda, count(DISTINCT d) AS deities, count(*) AS edges
```
**Result:** one row — `RV, 214 distinct deities, 10,558 edges`. Indra 2,869; Rudra 38 (+5 in
compounds); Viṣṇu 136 by total inbound degree. AV, SV and YV: no rows.
**Why misleading:** a prominence series that returns Rigvedic values and nothing else, for the three
deities whose relative trajectory is the most-cited diachronic claim about the Vedic pantheon, will be
read as evidence that the claim cannot be supported — when in fact the graph has not looked. None of
the three has a `DomainEntity`, so the four-Veda mention layer cannot substitute.
**Blocker:** B1, compounded by B2 and B11.

### 71. Which historical/civilizational claims are strongly supported? — `MISLEADING`
```cypher
// per-1000-mantra rates for aśva, ratha, ayas, vrīhi by Veda
```
**Result:** `ratha` RV 35.0/1k, SV 21.2, AV 9.4, YV 5.1; `aśva` RV 15.4, SV 10.3, AV 7.7, YV 4.1;
`ayas` RV 0.76, AV 0.51, SV 0, YV 0; `vrīhi` AV 0.51 only.
**Why misleading:** these are the rows a historian would use, and three things make them unsafe. The
horse and chariot rates fall monotonically RV→SV→AV→YV, which tracks overall annotation density
(`MENTIONS_ENTITY` per 1k: RV 2404, AV 1324, SV 1265, YV 1136) rather than material culture. `ayas`
at 11 total mentions is the output of a six-alias probe with no measured recall, and it is the sole
basis for any metallurgy statement. And `hiraṇya`'s 84 mentions sit under `Substance`+`Metal` while
`ayas` sits under the same labels, so gold and unspecified-metal are not distinguishable as
technologies.
**Blocker:** B5.

### 72. Which interpretive claims have conflicting evidence? — `MISLEADING`
Same as Q28: one `CONTRADICTS` pair between two claims about the dataset's construction, with
`SUPPORTED_BY_STATISTIC` on both sides pointing at the same `SV_REUSE_OF_RV` `DerivedMetric`. There is
no `CONTRADICTED_BY` relationship type at all.
**Blocker:** B16.

### 73. Which conclusions depend primarily on English translation, and how many edges would be lost? — `MISLEADING`
```cypher
MATCH ()-[r]->() WHERE r.evidence_basis IN ['TRANSLATION','MIXED'] RETURN type(r), r.evidence_basis, count(*) ORDER BY 3 DESC
;; MATCH ()-[r]->() WHERE r.knowledge_layer='L3_LLM_EXTRACTED' RETURN r.evidence_basis, count(*)
```
**Result:** the census returns exactly two rows — `ABOUT_CONCEPT/TRANSLATION 21246` and
`ABOUT_CONCEPT/MIXED 13015`, 34,261 edges, 72.1% of the concept layer. The second query returns
`UNSPECIFIED 736`.
**Why misleading:** the 736 `L3_LLM_EXTRACTED` edges carry `evidence_basis = UNSPECIFIED` while their
recorded `evidence` is an English quotation from Whitney or Griffith — inspected directly, e.g.
`{"locator":"VG:AV:SAU:K18:S004:V029","quote":"men-beholders look upon; whoso bestow ('pṛ') and
present"}`. So the translation-dependency audit under-reports by the whole LLM slice and presents
itself as complete. The number 34,261 is defensible; the claim that it is the total is not.
**Blocker:** B15.

### 74. Which conclusions survive Sanskrit-only filtering? — `MISLEADING`
```cypher
MATCH ()-[r]->() RETURN r.evidence_basis, count(*) ORDER BY 2 DESC
```
**Result:** `STRUCTURAL 85650`, `UNSPECIFIED 61861`, `SANSKRIT 60375`, `TRANSLATION 21246`,
`MIXED 13015`.
**Why misleading:** a Sanskrit-only projection (`evidence_basis='SANSKRIT'`) keeps 60,375 edges —
`MENTIONS_ENTITY 37675`, `ABOUT_CONCEPT 13281`, `MENTIONS_LEMMA 9000`, plus the small typed
predicates — and **silently deletes 27,646 Anukramaṇī edges** (`HAS_DEVATA`, `HAS_RISHI`,
`HAS_CHANDAS`, all `UNSPECIFIED`) and **all 6,271 cross-Veda parallel edges** (`NEAR_PARALLEL_OF`,
`REUSES_TEXT_FROM`, `EXACT_PARALLEL_OF`, `VARIANT_OF`, all `UNSPECIFIED`), every one of which is
computed on Sanskrit text. The surviving graph is a Sanskrit-only graph with the deity layer and the
reuse layer removed, and it will be read as "what rests on Sanskrit".
**Blocker:** B15.

### 75. Which connections disappear under source-explicit-only filtering? — `FULLY_ANSWERABLE`
```cypher
MATCH ()-[r]->() WHERE NOT type(r) IN ['CONTAINS','HAS_TEXT_VERSION','HAS_TRANSLATION','HAS_QA_ISSUE']
RETURN r.knowledge_layer, count(*) ORDER BY 2 DESC
;; MATCH (a)-[r]->(b) WHERE r.quality_tier='TIER_A' AND NOT type(r) IN ['CONTAINS','HAS_TEXT_VERSION','HAS_TRANSLATION']
RETURN type(r), labels(b), count(*) ORDER BY 3 DESC
;; MATCH (p:Passage)-[r]->(e:DomainEntity) WHERE r.quality_tier='TIER_A' RETURN count(*)
```
**Result:** of 156,001 non-plumbing relationships, `L2_DETERMINISTIC_DERIVED 148,291`,
`L1_SOURCE_EXPLICIT 7,067`, `L4_INTERPRETIVE_CLAIM 1,042`, `L3_LLM_EXTRACTED 736`. The 7,067
source-explicit edges are, exhaustively: `HAS_CHANDAS 4,247`, `HAS_DEVATA 2,229`, `HAS_RISHI 472`,
`DEVATA_ASSOCIATED_WITH 101`, `BROADER_THAN 18` — all Rigveda, all Anukramaṇī or curated. And
`TIER_A` passage→`DomainEntity` edges: **0**.
**Verdict basis:** a complete, correct, non-misleading census with the subset enumerated by type,
target class and Veda. The answer is that under source-explicit-only filtering **the entire concept
layer, the entire mention layer, the entire formula layer, the entire cross-Veda parallel layer and
all non-Rigvedic knowledge disappear**, leaving metre, seer and deity labels for one Veda. That is
uncomfortable and it is exactly what the question asked, and the graph supports it fully.

### 76. Which semantic relationships have independent corroboration from multiple passages and multiple evidence modes? — `FULLY_ANSWERABLE`
```cypher
MATCH (p)-[r1:MENTIONS_ENTITY]->(e:DomainEntity), (p)-[r2:ABOUT_CONCEPT]->(e)
RETURN r2.evidence_basis, count(*) ORDER BY 2 DESC
;; MATCH (p)-[r1:HAS_DEVATA]->(d:Devata) OPTIONAL MATCH (p)-[r2:INVOKES|PRAISES|DESCRIBES]->(d) RETURN count(*), count(r2)
;; MATCH (p)-[r1:MENTIONS_ENTITY]->(d:Devata) OPTIONAL MATCH (p)-[r2:HAS_DEVATA]->(d) RETURN count(*), count(r2)
```
**Result, and it is exact:** every `ABOUT_CONCEPT` edge whose basis is `SANSKRIT` (13,281) or `MIXED`
(13,015) is duplicated by a `MENTIONS_ENTITY` edge on the same passage–entity pair — 26,296 = 13,281 +
13,015, the complete `SANSKRIT`+`MIXED` population — and **none** of the 21,246 `TRANSLATION`-basis
edges has a Sanskrit counterpart. So the two "independent" concept layers are **nested, not
independent**: on the Sanskrit side they are the same matcher twice, and on the translation side there
is no corroboration at all. `0` of 10,558 `HAS_DEVATA` edges are corroborated by the LLM slice.
The one genuinely two-mode set: **4,397 of 9,000** legacy `MENTIONS_ENTITY`→`Devata` edges
(`grade_basis = "lexical match over annotated tokens"`) coincide with an Anukramaṇī `HAS_DEVATA` edge
(`grade_basis` from `scope_origin`, external source) — a lexical match and an external index agreeing,
which are independent modes.
**Verdict basis:** a complete corroboration census, mode independence demonstrated from graph-resident
fields (`grade_basis`, `run_id`, `evidence_basis`) rather than assumed, and the corroborated and
uncorroborated counts reported per layer. The answer is 4,397 deity attributions and zero concept
assertions.

### 77. Where is the graph uncertain — is there a calibrated, validated confidence? — `MISLEADING`
```cypher
MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN type(r), r.confidence, count(*) ORDER BY 1,3 DESC
;; MATCH ()-[r]->() WHERE r.confidence >= 0.8 RETURN count(*)
;; MATCH (n) WHERE any(k IN keys(n) WHERE toLower(k) CONTAINS 'gold' OR toLower(k) CONTAINS 'precision' OR toLower(k) CONTAINS 'recall') RETURN labels(n), count(*)
```
**Result:** `ABOUT_CONCEPT` carries 14 distinct confidence values over 47,542 edges, of which
**20,350 sit at exactly 0.42**, 12,530 at 0.85 and 12,495 at 0.80 — three constants covering 95.5%.
`confidence >= 0.8` selects **57,993** relationships. The gold/precision/recall probe returns **0
nodes**: there is no evaluation set in the graph.
**Why misleading:** the field is named `confidence`, is filterable, and supports a query that returns
57,993 "high-confidence" edges. Nothing about it is calibrated — a 0.85 has never been checked against
an annotation, and 43% of the concept layer shares a single value. A researcher who filters on it
believes they have raised precision and has only selected a pipeline branch.
**Blocker:** B14.

### 78. Which major entities have coverage too thin to support a claim? — `NOT_ANSWERABLE`
```cypher
MATCH (e:DomainEntity) OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(e) WITH e, count(p) AS n WHERE n<10 RETURN count(*)
;; MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH e, count(*) AS n ORDER BY n DESC LIMIT 20 RETURN e.display_label, n
```
**Result:** `29` entities under 10 mentions; the top 20 all exceed 400 (`agni 2095`, `soma 1570`,
`dyaus 1206`, … `stoma 402`).
**Why not answerable:** the entities with the worst coverage are the ones that are not in the registry
at all — Indra, Varuṇa, Rudra, Viṣṇu, Mitra, the Maruts, *takman* as itself, the Yajurvedic rite
names, *udgātṛ*. A query over the graph cannot return a row for an entity the graph does not have, so
the answer is structurally the wrong shape: it reports thin coverage and cannot report absent coverage.
No expected-entity manifest exists.
**Blocker:** B2, compounded by B8.

### 79. Which Veda is underrepresented in each ontology dimension, per 1,000 mantras? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p:Passage {entity_type:'MANTRA'}) WITH p.veda AS veda, count(*) AS m
CALL (veda) { MATCH (q:Passage {veda:veda})-[r]->() WHERE type(r) IN [ ...12 knowledge types... ] RETURN type(r) AS t, count(*) AS c }
RETURN t, veda, c, round(1000.0*c/m,1) AS per1k ORDER BY t, per1k DESC
```
**Result:** 30 rows. `ABOUT_CONCEPT` RV 2815.9 / YV 2488.1 / AV 1835.1 / SV 1193.1;
`MENTIONS_ENTITY` RV 2404.2 / AV 1323.9 / SV 1265.2 / YV 1135.7; `USES_FORMULA` SV 1646.4 / YV 1558.0 /
AV 1172.1 / RV 922.0; `HAS_DEVATA` RV 1000.6 and no other row; `HAS_RISHI` RV 1001.2 only;
`HAS_CHANDAS` RV 997.3 only; `MENTIONS_LEMMA` RV 852.9 only; `ADDRESSES_CONCERN` AV 25.3 / YV 10.1 /
RV 4.5 / SV 1.6; `TREATS` AV 14.4 / YV 0.5 / RV 0.2; `DESCRIBES` YV 79.0 / AV 21.2 only;
`INVOKES` YV 62.3 / AV 17.0 only.
**Verdict basis:** the matrix is correct, computes cleanly, and is genuinely the most useful single
answer in this baseline. It fails one clause of its own frozen acceptance criterion: **structural
zeros are not distinguished from low coverage inside the matrix.** An absent row for `HAS_DEVATA/AV`
is typographically identical to an absent row for a dimension that simply scored zero. The
distinction is recoverable for deities only (`Devata.attribution_scope = ['RV']` on all 214); `Rishi`
and `Chandas` nodes carry no scope field, and `MENTIONS_LEMMA` has no scope declaration anywhere.
**Blocker:** B1 — no graph-resident structural-absence marker for the seer, metre and lemma layers.

### 80. Which relationships are likely artifacts of inherited container metadata? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH ()-[r]->() WHERE r.attribution_precision='CONTAINER_INHERITED' RETURN type(r), count(*) ORDER BY 2 DESC
```
**Result:** exactly 3 types, 24,698 edges — `HAS_RISHI 10,093` (95.5% of the predicate),
`HAS_DEVATA 8,329` (78.9%), `HAS_CHANDAS 6,276` (59.6%). All other 46 populated predicates are
`PER_PASSAGE` on 100% of their edges. The corpus-level figures are also stored as a graph-resident
`DerivedMetric` (`ATTRIBUTION_PRECISION_CORPUS`) with a `scope_note` reading "Rigveda only: the
Anukramani attribution layer does not cover SV, YV or AV."
**Verdict basis:** the census is complete and correct and the inheritance is explicitly marked, which
is a real strength of this graph. It fails one clause of its frozen criterion: there is **no
per-container homogeneity measure**, so all 24,698 inherited edges are indistinguishable from one
another and a reader cannot separate "inherited from a hymn that is uniformly about Indra" from
"inherited from a hymn that changes addressee mid-way".
**Blocker:** B3 — no homogeneity marker on the inherited edge.

### 81. Which cross-Veda connections come from literal reuse versus semantic resemblance? — `MISLEADING`
```cypher
MATCH (a:Passage)-[r]->(b:Passage) WHERE type(r) IN ['EXACT_PARALLEL_OF','NEAR_PARALLEL_OF','REUSES_TEXT_FROM','VARIANT_OF','PARALLEL_TO'] AND a.veda<>b.veda
RETURN type(r), r.knowledge_layer, count(*) ORDER BY 3 DESC
```
**Result:** `NEAR_PARALLEL_OF 3049`, `REUSES_TEXT_FROM 1684`, `VARIANT_OF 788`,
`EXACT_PARALLEL_OF 750` — 6,271 edges, **all `L2_DETERMINISTIC_DERIVED`, all lexical**. The partition
returns 100% literal / 0% semantic.
**Why misleading:** 100/0 reads as a finding about the corpus — that cross-Veda relatedness is purely
textual — when it is a statement that no non-lexical resemblance measure was ever built. The only
candidate, `PARALLEL_TO` (69 edges, `TIER_D`), has `veda_pair` null on all 69 and so does not even
enter the cross-Veda partition.
**Blocker:** B10.

### 82. Which formula families transform in the Sāmaveda, and how? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (sv:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM]->(rv:Passage {veda:'RV'})
RETURN r.match_level, round(avg(r.token_jaccard),3), round(avg(r.edit_ratio),3), count(*) ORDER BY 4 DESC
```
**Result:** `'' — jaccard 0.452 / edit 0.963 / 1180 edges`; `SANDHI_INSENSITIVE — 0.544 / 1.000 / 415`;
`SCRIPT_FOLDED — 1.000 / 1.000 / 89`. The unlabelled bucket has the lowest token overlap, which is
where the real transformations are.
**Verdict basis:** the metrics separate the buckets and the low-jaccard set is retrievable, so
"something transforms and here it is" is answerable. But 70% of the edges have no type; there is no
family construct (Q57); the Sāmaveda's actual transformation dimension — sāman names, stobhas, gāna
assignment, vowel extension — has no representation in the graph at all; and the SV has **zero**
`Translation` nodes, so no gloss-level check is possible.
**Blocker:** B12, compounded by B24.

### 83. Which Atharvavedic concerns reuse Rigvedic material, and which are AV-native? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (av:Passage {veda:'AV'})-[:ADDRESSES_CONCERN]->(c:HumanConcern)
OPTIONAL MATCH (av)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF]-(rv:Passage {veda:'RV'})
RETURN c.display_label, count(DISTINCT av), count(DISTINCT rv) ORDER BY 2 DESC
```
**Result:** `sapatna 87 AV passages / 5 with an RV parallel`; `puṣṭi 47 / 1`; `ṛṇa 9 / 0`;
`saṃjñāna 5 / 0`. So the AV's rival-overcoming and thriving material is 94% and 98% AV-native by this
measure.
**Verdict basis:** the join works and the ratios are informative. Four concerns is not a concern
repertoire (Q55), and the AV-native claim rests on the parallel layer's unmeasured recall — an
undetected parallel and an absent parallel are the same row.
**Blocker:** B8.

### 84. Which crops, metals and animals occur in which Vedas and in which contexts? — `MISLEADING`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(e) WHERE e:Crop OR e:Metal
OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(r:Ritual)
RETURN e.display_label, p.veda, r IS NOT NULL AS ritual_ctx, count(DISTINCT p) ORDER BY 4 DESC
```
**Result:** twelve rows, **`ritual_ctx = false` on every one of them** — `hiraṇya` RV 35 / AV 32,
`yava` RV 19 / AV 15, `dhānya` AV 13 / RV 9, `ayas` RV 8, `tila` AV 5, `vrīhi` AV 3.
**Why misleading:** a clean two-column context split in which every row is "non-ritual" reads as a
finding that Vedic gold, barley and grain occur outside ritual contexts — in a corpus that is almost
entirely liturgical. Ritual context is being inferred from whether one of four `Ritual` entities
happens to be named in the same verse, which is almost never. There is no ritual-context property on
`Passage` and no liturgical-position index.
**Blocker:** B9, compounded by B8.

### 85. Which rivers are deity-like and which are geographic, per occurrence? — `NOT_ANSWERABLE`
```cypher
MATCH (p)-[r:MENTIONS_ENTITY]->(riv:River) RETURN riv.display_label, r.theonym_ambiguous, count(*) ORDER BY 3 DESC
```
**Result:** `sindhu / false / 224` and `sindhu / true / 12`; every one of the six named hydronyms
(`paruṣṇī 3`, `sarayu 2`, `vipāś 2`, `yamunā 2`, `gaṅgā 1`, `śutudrī 1`) is `false`. Sarasvatī — the
one river in the corpus that is unambiguously both goddess and geography — is not a `River` at all; it
exists only as `VG:DEVATA:SARASVATI`.
**Why not answerable:** the decisive case is missing from the class, the flag that would carry the
distinction is `false` on 100% of the named rivers, and there is no per-occurrence sense field.
**Blocker:** B8, compounded by B7.

### 86. Which concepts attach to more than one personification? — `NOT_ANSWERABLE`
```cypher
MATCH ()-[r:PERSONIFIES]->() RETURN count(*)
;; MATCH (d:Devata) WHERE toLower(d.label_en) CONTAINS 'earth' OR ... RETURN d.entity_key, d.label_en
```
**Result:** `PERSONIFIES = 0`. The "earth" probe alone returns five distinct unresolved `Devata`
nodes: `DYAVABHUMI` ("Heaven and Earth"), `DYAVAPRTHIVYAU` ("Heaven and Earth" — a second node with
the same gloss), `DYUBHUMYASVINAH`, `PRTHIVYANTARIKSE`, plus `BRAHMANAPITRSOMADYAVAPRTHIVIPUSANAH`.
Ten epithet-qualified `Devata` nodes are unlinked to their base deity, and `MEMBER_OF` covers only 13
deities across 2 groups.
**Blocker:** B8.

### 87. How is Soma-as-deity distinguished from soma-as-substance, per occurrence? — `MISLEADING`
Same probe and result as Q45, plus: no `sense`, `role` or `sem*` property exists on
`MENTIONS_ENTITY`. The RV cross-tab is `deity+word 467`, `deity only 700`, `word only 553`,
`neither 9,870`.
**Why misleading:** `theonym_ambiguous` is the only field that looks like a sense decision, it fires
on 841 of 1,570 soma mentions, and it disagrees with itself across sandhi variants of the same form
(`somam` true, `somaṃ` false). A per-occurrence decision does not exist and the field that appears to
be one partitions by orthography.
**Blocker:** B7.

### 88. How is Agni-as-deity distinguished from fire-as-phenomenon, per occurrence? — `MISLEADING`
Same probe and result as Q46 (`F/F 9338, T/T 1101, T/F 887, F/T 264`), plus 146 of 2,095 `agni`
mentions flagged `theonym_ambiguous`.
**Why misleading:** the 887-verse "deity with no fire word" cell is a matcher disagreement presented
as a sense category, and the graph's own `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED`
(`status = MODEL_SYNTHESIS`) states that the distinction is not derivable — a claim that remains
standing while the cross-tab remains queryable.
**Blocker:** B7.

### 89. How does Vāc-as-deity relate to speech-as-concept? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:VAK'}) WITH count(*) AS vac_deity
MATCH (p2)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:VAC-SPEECH'}) RETURN vac_deity, count(*) AS vac_word
;; // overlap
```
**Result:** `vac_deity_passages 3`, `vac_word_mentions 651`, `overlap 2`. There is no relationship of
any kind between `VG:DEVATA:VAK` and `VG:CONCEPT:VAC-SPEECH`.
**Why misleading:** a 3-against-651 ratio reads as "the goddess Vāc is vanishingly marginal beside the
common noun". The 3 is the count of RV sūktas the Anukramaṇī assigns to Vāc as devatā; it is a
granularity artefact of the attribution source, not a measure of the goddess's presence, and the AV's
substantial Vāc material contributes nothing because the AV has no attribution layer. The two nodes
are unlinked, so no relation can be characterised.
**Blocker:** B8, compounded by B1.

### 90. Which rituals use which priestly roles? — `MISLEADING`
```cypher
MATCH (r:Ritual)-[:PERFORMED_BY]->(role) RETURN r.display_label, collect(role.display_label)
;; MATCH (n:RitualRole) RETURN n.display_label
;; MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity {entity_key:'VG:CONCEPT:HOTR-PRIEST'}) RETURN p.veda, count(*)
```
**Result:** `yajña → [adhvaryu, brahman, purohita, yajamāna]`, `savana → [adhvaryu]`,
`dīkṣā → [yajamāna]`. The `RitualRole` class has 5 members: `adhvaryu`, `brahmacārin`, `brahman`,
`purohita`, `yajamāna`. **`hotṛ` is in the registry as `VG:CONCEPT:HOTR-PRIEST` with no typed label at
all**, and has 321 mentions (RV 208, YV 50, SV 41, AV 22). **`udgātṛ` does not exist** — an alias probe
for `udgat*` returns 0 entities.
**Why misleading:** a Vedic priestly-role table that omits the *hotṛ* — the officiant of the Rigveda,
and the most-mentioned priest in the corpus by a factor of five — and omits the *udgātṛ* entirely, the
officiant who defines the Sāmaveda, is not incomplete. It is a table that inverts the answer. A reader
concludes the *adhvaryu* is the central Vedic officiant.
**Blocker:** B8.

### 91. What actions happen inside each ritual, in order? — `NOT_ANSWERABLE`
`PRECEDES`, `FOLLOWS`, `REQUIRES`, `PART_OF`, `DEPENDS_ON`, `HAS_STEP` and `SUB_RITE_OF` all have zero
instances (Q39). The only ritual-internal structure is 2 `BROADER_THAN` containment edges and 33
apparatus edges, none of which carries an order.
**Blocker:** B9.

### 92. Which objects are deity-specific? — `MISLEADING`
```cypher
MATCH (p)-[rd:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(o:Object)
WHERE rd.attribution_precision='PER_PASSAGE' WITH o, count(DISTINCT d) AS deities, count(*) AS edges
WHERE edges>=3 RETURN o.display_label, deities, edges ORDER BY 2 ASC
```
**Result:** `ulūkhala 1 deity / 4 edges`, `dundubhi 2 / 3`, `kalaśa 2 / 4`, `samidh 2 / 11`,
`pāśa 2 / 3`, `vajra 3 / 28`, `pavitra 3 / 8`, `vedi 3 / 3`.
**Why misleading:** the deity-specificity ranking is led by a mortar with four attestations, and the
single most deity-specific object in the Vedic corpus — Indra's *vajra*, 163 co-attributions with
Indra naively — appears sixth with "3 deities" because the strict filter shrinks it to 28 edges and
because it is not typed as a weapon. There is no chance baseline, so "1 deity at n=4" and "1 deity at
n=163" would rank identically.
**Blocker:** B13, compounded by B8 and B3.

### 93. Which weapons occur in which narratives? — `NOT_ANSWERABLE`
```cypher
MATCH (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:VAJRA-THUNDERBOLT'}),
      (p)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:'VG:CONCEPT:AHI-SERPENT'}) RETURN count(DISTINCT p)
```
**Result:** `17` verses mention both the thunderbolt and the serpent — the raw material of the
Vṛtra-slaying — and there is nothing in the graph to attach them to. No narrative, myth, episode or
theme-cluster node type exists above the passage; `HAS_THEME` has 8 instances, all `TIER_D` and all
passage→`Concept`.
**Blocker:** B4.

### 94. Which conditions are treated by which Atharvavedic practices? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p:Passage {veda:'AV'})-[:TREATS]->(c:Condition)
OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(pr) WHERE pr:Plant OR pr.entity_key IN ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:AP-WATERS']
RETURN c.display_label, collect(DISTINCT pr.display_label), count(DISTINCT p) ORDER BY 3 DESC
```
**Result:** `krimi 24 → [āpaḥ, oṣadhi]`; `kṣetriya 22 → [tila, yava, apāmārga]`;
`balāsa 12 → [oṣadhi, vanaspati, jaṅgiḍa]`; `viṣkandha 11 → [jaṅgiḍa, maṇi]`; `kāsa 7 → []`;
`āsrāva 4 → []`; `hariman 4 → []`.
**Verdict basis:** this is one of the more genuinely useful results in the baseline — the
*kṣetriya*/*apāmārga* and *viṣkandha*/*jaṅgiḍa* pairings are the correct Atharvavedic associations.
Three limits keep it partial: all `TREATS` edges are `TIER_D`/`L4` and the grade does not appear in the
row; the practice side is co-mention, not an asserted treatment; and *takman* cannot appear because it
is folded into a `State`-labelled node (Q15).
**Blocker:** B8.

### 95. Which social rites connect to which concepts and deities? — `PARTIALLY_ANSWERABLE`
```cypher
MATCH (p)-[:USED_FOR_RITE]->(s:SocialRite) OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(e:DomainEntity)
OPTIONAL MATCH (p)-[:HAS_DEVATA]->(d:Devata)
RETURN s.display_label, count(DISTINCT p), count(DISTINCT e), count(DISTINCT d) ORDER BY 2 DESC
```
**Result:** `vivāha 41 passages / 23 concepts / 8 deities`; `śālā 30 / 22 / **0** deities`;
`sūṣā 15 / 13 / 1`; `pitṛyāṇa 10 / 13 / 1`.
**Verdict basis:** the concept column is real and usable. The deity column is not: `śālā`
(house-building) is a wholly Atharvavedic rite and its 0 is the AV attribution gap, and the rite layer
itself has ~10% recall (Q13).
**Blocker:** B1, compounded by B5.

### 96. Which entities are central bridges, and is the ranking robust to the concept layer? — `MISLEADING`
```cypher
CALL gds.graph.project('aK2', ['Passage','DomainEntity','Devata'],
  {MENTIONS_ENTITY:{orientation:'UNDIRECTED'}, HAS_DEVATA:{orientation:'UNDIRECTED'}})
CALL gds.betweenness.stream('aK2', {samplingSize:1500}) ...
```
**Result:** 22,914 nodes / 96,466 relationships. Betweenness: `Indra 4,028,469` · `Agni 3,056,381` ·
`the Aśvins 965,933` · `agni (concept) 925,753` · `dyaus 724,503` · `the Maruts 683,543` ·
`soma 681,412`. The naive **directed** projection — the one you get without specifying orientation —
returns `0.0` for every node. And the two rival concept layers disagree on the entity ranking:
`MENTIONS_ENTITY` gives `agni 2095, soma 1570, dyaus 1206, rayi 885, yajña 839, go 757, pṛthivī 742`
while `ABOUT_CONCEPT` gives `agni 2206, soma 1841, dyaus 1659, rayi 1601, yajña 1570, stoma 1367,
go 1339` — `stoma` enters the top seven in one layer and sits at rank 20 in the other.
**Why misleading:** the default projection yields a sortable ranking of zeros; the corrected one is
led by two `Devata` nodes that exist for one Veda and whose edges are 78.9% container-inherited. No
rank-correlation between the layers is available, and nothing marks either as authoritative.
**Blocker:** B6, compounded by B1.

### 97. Which communities emerge under high-confidence edges only? — `NOT_ANSWERABLE`
```cypher
MATCH (p:Passage)-[r]->(e:DomainEntity) WHERE r.quality_tier='TIER_A' RETURN count(*)
;; MATCH (a)-[r]->(b) WHERE r.quality_tier='TIER_A' AND NOT type(r) IN ['CONTAINS','HAS_TEXT_VERSION','HAS_TRANSLATION'] RETURN type(r), labels(b), count(*) ORDER BY 3 DESC
```
**Result:** `0` `TIER_A` passage→entity edges. The `TIER_A` semantic graph is `HAS_CHANDAS 4247`,
`HAS_DEVATA 2229`, `HAS_RISHI 472` plus 140 entity-level `DEVATA_ASSOCIATED_WITH`/`BROADER_THAN`
edges. `TIER_C` is 0 across the whole graph.
**Why not answerable:** restricting to high confidence removes every concept and every mention, so the
communities that emerge are metre groups, seer groups and deity-label groups. They would look
thematic — a Louvain run over metres and seers produces plausible-looking clusters — and they carry no
semantic content at all.
**Blocker:** B18 — the top quality tier holds no semantic assertions.

### 98. Which graph paths are meaningful versus accidental? — `NOT_ANSWERABLE`
```cypher
MATCH p=(a:Passage)-[:MENTIONS_ENTITY]->(:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Passage)
WHERE a.canonical_citation='RV 1.1.1' RETURN count(*)
```
**Result:** `3,252` two-hop paths from a single verse. No path-scoring, relevance, interpretability or
plausibility facility exists on any node or relationship, and there is no human-judged path sample to
calibrate one against.
**Blocker:** B23.

### 99. What are the ten most defensible novel discoveries VedaGraph can make? — `PARTIALLY_ANSWERABLE`
**Result:** running the underlying probes, four candidate corpus-level findings are defensible today:
229 formulas attested in all four Vedas with per-Veda occurrence vectors; the Sāmaveda is 90.1%
RV-derived by verse (1,662 of 1,844 mantras); the Atharvaveda's rival-overcoming concern runs at 26×
the Rigvedic rate per 1,000 mantras (14.90 vs 0.57) and is 94% AV-native; and the Anukramaṇī's three
dimensions differ sharply in verse-specificity (metre 40.4% verse-specific, deity 21.1%, seer 4.5%).
**Why only partial:** none carries a measured recall figure, none has a graph-recorded falsifier, and
there is no novelty record — the graph cannot say whether a finding is already in the literature. The
`InterpretiveClaim` layer that would hold such claims contains 6 nodes, all about this dataset's
construction. Of the four findings above, two (the third and fourth) are about the corpus and two are
about the corpus-as-digitised.
**Blocker:** B14, compounded by B16.

### 100. Can the graph answer a compound research question end-to-end? — `MISLEADING`
```cypher
MATCH (p)-[:HAS_DEVATA]->(d:Devata), (p)-[:MENTIONS_ENTITY]->(o:Offering), (p)-[:ADDRESSES_CONCERN]->(c:HumanConcern)
RETURN p.veda, d.label_en, o.display_label, c.display_label, count(*) ORDER BY 5 DESC
```
**Result:** **2 rows** — `RV / the Maruts / havis / puṣṭi / 1` and
`RV / Sarasvati / dakṣiṇā / puṣṭi / 1`. Dropping the deity dimension gives 4 rows across three Vedas.
**Why misleading:** two rows in a 22,537-passage corpus reads as a statement about the Vedas — that
the deity–offering–concern configuration is almost never attested. It is the product of four thin
dimensions multiplied together: deity attribution exists for one Veda (10,558 edges), the offering
vocabulary has 2 members, the concern vocabulary has 4 members, and `ADDRESSES_CONCERN` has 219 edges
of which 48 are Rigvedic. The join's collapse is arithmetic, and nothing in the result explains it.
**Blocker:** B1, compounded by B8 and B3.

---

## Ranked blocker table

"Blocked" counts questions where the blocker is the **binding constraint** on the verdict — the thing
that would have to change first. A question is counted once, against its primary blocker. The five
`FULLY_ANSWERABLE` questions (6, 8, 29, 75, 76) are not counted.

| Rank | Blocker | Questions blocked | Fixable by modelling? | Questions |
| --- | --- | --- | --- | --- |
| 1 | **B8 — Domain registry is shallow or mis-typed exactly where the questions land.** *hotṛ* untyped (321 mentions), *udgātṛ* absent, *takman* folded into a `State`-labelled `yakṣma` node with *amīvā* and *rapaḥ*, Sarasvatī not a `River`, `vajra`/`āyudha` not `Weapon`, 4 `HumanConcern`, 4 `Ritual`, 2 `Offering`, 5 `Action`, no `PERSONIFIES`, 24 of 163 entities untyped. | **15** | **Yes** — this is pure modelling and registry work, and it is the largest single win available. | 15, 25, 26, 40, 41, 47, 54, 55, 56, 83, 85, 86, 89, 90, 94 |
| 2 | **B5 — Mention-layer recall is unmeasured; there is no gold set.** Mean mention degree 1.88, 27.8% of passages carry no mention, `DOMAIN_MENTION_COVERAGE` 66.8–79.4% by Veda, `score` effectively binary, 0 gold/precision/recall nodes in the graph. | **11** | **Partly** — the annotation effort is acquisition, not modelling; but a graph-resident evaluation-set schema is modelling and is the prerequisite. | 9, 10, 13, 14, 16, 21, 34, 60, 64, 65, 71 |
| 3 | **B1 — The attribution layer is Rigveda-only.** `HAS_DEVATA` 10,558 / `HAS_RISHI` 10,565 / `HAS_CHANDAS` 10,523 / `MENTIONS_LEMMA` 9,000, all zero on AV, SV and YV. | **10** | **No** — requires acquiring a non-Rigvedic attribution source (Bṛhat-sarvānukramaṇī, Kauśika-sūtra, YV devatā assignments). A cheaper partial substitute is modelling: register the ~40 major theonyms as mention targets (see B2). | 1, 12, 35, 43, 44, 66, 70, 79, 95, 100 |
| 4 | **B4 — No agentive, verb-argument or event layer.** `Action` is 5 abstract nouns, two of which are the worshipper's acts; `PERFORMS_ACTION` 0; the 736-edge L3 slice is `CANDIDATE`/`TIER_D`/AV+YV only; the sealed RV V3.2 artifact's 554 `EVENT` objects are unprojected. | **8** | **Partly** — the schema is modelling; populating it at corpus scale is extraction. Projecting the sealed V3.2 EVENT layer is available immediately and would move Q18, Q51, Q67 off the floor. | 4, 11, 17, 18, 51, 61, 67, 93 |
| 5 | **B3 — Attribution is sūkta-scoped, not per-verse.** 24,698 `CONTAINER_INHERITED` edges: `HAS_RISHI` 95.5%, `HAS_DEVATA` 78.9%, `HAS_CHANDAS` 59.6%. Leaderboards invert under strict filtering (Q19: naive 217 vs strict 27, different seers). | **6** | **Partly** — verse-level truth needs a source, but a per-container *homogeneity* marker is pure modelling and would let a reader separate inherited-and-safe from inherited-and-doubtful. It is the blocker on Q80. | 2, 3, 19, 31, 62, 80 |
| 5= | **B10 — No epithet occurrence layer, no text index, no non-lexical similarity.** 0 epithet→passage edges; 2 FULLTEXT indexes (`Concept`, `Formula`) and **0 VECTOR** indexes; 0 concept→concept semantic relations beyond 57 `BROADER_THAN`. | **6** | **Yes** — a `MENTIONS_EPITHET` pass reuses the existing mention machinery, and a text/vector index is infrastructure. | 22, 42, 49, 53, 68, 81 |
| 7 | **B17 — No per-occurrence role assignment.** Roles exist only as 289 `HAS_AXIS` edges on `Devata` nodes, all `TIER_D`, constant across every occurrence. | 5 | **Yes** — the schema change is small; the labelling is extraction. | 20, 38, 52, 58, 69 |
| 7= | **B12 — No formula-family construct and no transformation typology.** `SHARES_FORMULA_WITH` 0; no `family`/`cluster`/`parent` property; `match_level` empty on 1,180 of 1,684 and only 3 values. | 5 | **Yes** | 7, 27, 50, 57, 82 |
| 9 | **B9 — No procedural ritual structure.** `PRECEDES`, `FOLLOWS`, `REQUIRES`, `PART_OF`, `DEPENDS_ON`, `HAS_STEP`, `SUB_RITE_OF` all 0; no ritual-context property on `Passage`. | 4 | **Partly** — the schema is modelling; the content needs a Śrautasūtra. | 32, 39, 84, 91 |
| 9= | **B7 — No word-sense disambiguation per occurrence.** `theonym_ambiguous` is per-alias-string and internally inconsistent across sandhi variants of one form (`somam` true / `somaṃ` false; `soma` true / `somo` false). | 4 | **Partly** — moving the flag to the occurrence is modelling; deciding the sense is annotation. Making the existing flag self-consistent is a bug fix. | 45, 46, 87, 88 |
| 11 | **B6 — Two rival passage→Concept layers with nothing marking authority.** `ABOUT_CONCEPT` 47,542 edges / 89 entities / capped at 4 per passage / 72.1% translation-based, against `MENTIONS_ENTITY` 28,675 / 163 entities / Sanskrit-only. They disagree on the entity ranking. | 3 | **Yes** — retire or rename one. | 37, 48, 96 |
| 11= | **B11 — No diachronic or stratigraphic dimension.** `Passage` has no `layer`/`strat`/`period`/`date` key; maṇḍala requires `substring(canonical_key,10,3)`; Veda is being used as a proxy for time. | 3 | **Partly** | 24, 30, 36 |
| 11= | **B19 — Deity co-occurrence is compound-label decomposition.** 10,546 of 10,552 RV mantras carry exactly one `HAS_DEVATA` edge; all reported pairs come from 28 `COMPOSED_OF` edges. | 3 | **Yes** — type the decomposition-derived pairs separately from co-attestation. | 5, 23, 33 |
| 14 | **B13 — No statistical baseline machinery.** No expected-value, chance-model, significance or multiple-comparison facility anywhere. | 2 | **Yes** | 63, 92 |
| 14= | **B14 — No calibrated confidence and no evaluation set.** 20,350 `ABOUT_CONCEPT` edges at exactly 0.42; three constants cover 95.5% of the layer; `confidence >= 0.8` selects 57,993 edges; 0 gold nodes. | 2 | **Partly** — a schema for evaluation sets and a constant-value guard are modelling; the labels are annotation. | 77, 99 |
| 14= | **B15 — Evidence-basis labelling is wrong on part of the graph.** All 736 `L3` edges carry `evidence_basis = UNSPECIFIED` while quoting Whitney/Griffith English; 27,646 Anukramaṇī edges and 6,271 Sanskrit-computed parallel edges are also `UNSPECIFIED`. 61,861 `UNSPECIFIED` in total. | 2 | **Yes** — a data-correction pass, and the cheapest item in this table. | 73, 74 |
| 14= | **B16 — The interpretive layer is about the dataset, not the Vedas.** All 6 `InterpretiveClaim` nodes; no `CONTRADICTED_BY` type; the single `CONTRADICTS` pair is a methodological argument. | 2 | **Partly** | 28, 72 |
| 18 | **B2 — No theonym mention layer.** 0 `DomainEntity` nodes for Indra, Varuṇa, Rudra, Viṣṇu, Mitra or the Maruts; deities are reachable in four Vedas only where the name is also a common noun. Also: no expected-entity manifest, so absent entities cannot appear as rows. | 1 (binding) / degrades 10 more | **Yes** — the same machinery as the existing 28,675-edge mention layer applied to a new entity class. Highest reach per unit of work in this table. | 78 (binding); degrades 1, 12, 43, 44, 51, 70, 78, 89, 92, 100 |
| 18= | **B18 — The top quality tier holds no semantic assertions.** 0 `TIER_A` passage→entity edges; `TIER_C` = 0 across the graph. | 1 | **Yes** | 97 |
| 18= | **B22 — Reuse direction is a global prior, not per-pair evidence.** `REUSES_TEXT_FROM` exists for `RV-SV` only; no reason-for-direction field. | 1 | **Yes** | 59 |
| 18= | **B23 — No path scoring.** 3,252 two-hop paths from one verse, no interpretability measure. | 1 | **Partly** | 98 |
| 18= | **B20 — `RishiFamily` is declared and empty.** 0 nodes; `Rishi` bundles patronymic and personal name in one inflected label; `occurrence_count` 0 on all 367. | 0 (binding) / degrades 3 | **Yes** | degrades 2, 35, 62 |
| 18= | **B21 — The sealed RV V3.2 semantic artifact is not projected.** `run_id` probe for `v3.2`/`448` returns 0 rows; 2,459 assertions including 554 `EVENT` objects with actor/patient/action-head sit outside the graph. | 0 (binding) / degrades 3 | **Yes** — projection only, no new modelling. | degrades 17, 18, 67 |
| 18= | **B24 — The Sāmaveda has zero translations; translators partition rather than overlap.** Griffith 12,405 (RV+YV), Whitney 4,878 (AV), SV 0. | 0 (binding) / degrades 2 | **No** — acquisition. | degrades 82, 49 |

### The three cheapest high-reach fixes, from the table above

1. **Register the ~40 major theonyms as `DomainEntity` mention targets (B2).** Same pipeline as the
   existing 28,675-edge layer. It is the binding constraint on Q78 and it degrades ten more questions,
   including Q1, Q43, Q44, Q70 and Q100. It ends the situation where Agni is reachable in four Vedas
   because his name is also a noun while Indra is reachable in one.
2. **Correct `evidence_basis` on the 736 L3 edges and the 33,917 Sanskrit-derived `UNSPECIFIED`
   edges (B15).** Two questions move off `MISLEADING` for the cost of a data-correction pass, and the
   two evidence-mode audits (Q73, Q74) become trustworthy.
3. **Type `hotṛ` as `RitualRole`, add `udgātṛ`, split `takman` out of `yakṣma`, add Sarasvatī to
   `River`, move `vajra` and `āyudha` into `Weapon` (B8).** Five registry edits. They are the decisive
   defect in Q15, Q26, Q40, Q85, Q90 and Q94 — six questions — and each one is currently returning a
   table that inverts its own answer.

---

## Appendix: what this pass corrects in the V2 report

| Item | V2 statement | Measured now |
| --- | --- | --- |
| Gold as `Metal` | "gold is labelled `Substance` and not `Metal`, so the typed query silently drops the corpus's most frequent metal" — listed as the worst new V2 hazard | `VG:CONCEPT:HIRANYA-GOLD` carries `["Substance","Metal"]`. The metal query returns 105 mentions across four Vedas including `hiraṇya` 84. Closed. |
| takman | "**takman is absent**, so the AV's central disease returns nothing" | `takman`, `takmā`, `takmānam` are aliases on `VG:CONCEPT:YAKSMA-DISEASE` (13 AV mentions). The node is labelled `State`, not `Condition`, and conflates *takman* with *yakṣma*, *amīvā* and *rapaḥ*. Half-closed, and the conflation is a new defect. |
| Crop zeros | "the zero cells read as absence from the Rigveda rather than as a five-term alias probe" | The zeros are correct: *vrīhi*, *tila* and *māṣa* are genuinely absent from the Rigveda. V2 was harsher than the data warranted here. |
| `theonym_ambiguous` on soma | "402 of 1,570 for soma" | `true 841 / false 729`, and the flag is inconsistent across sandhi variants of the same form (`somam` true, `somaṃ` false). The counts moved and the underlying defect is worse than V2 recorded. |
| `EXACT_PARALLEL_OF` provenance split | "split across `trust` (750) and `provenance_class` (256)" | Confirmed exactly. `trust` present on 106,029 of 242,147 edges; `provenance_class` on 49,971; `knowledge_layer` on all 242,147. |
| Q50 | `ANSWERABLE_NOW` | Downgraded to `PARTIALLY_ANSWERABLE`. `REUSES_TEXT_FROM` covers one of six Veda pairs and its typology is 70% unlabelled. |
| Sealed V3.2 artifact | not addressed | Confirmed **not projected**: a `run_id` probe for `v3.2` or `448` returns 0 rows. The 554-`EVENT` layer that would move Q18, Q51 and Q67 is sitting outside the graph. |
