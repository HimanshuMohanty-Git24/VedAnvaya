# Graph Adversarial QA — Knowledge Model V2

Adversarial review of the live Neo4j graph at `bolt://localhost:7687` against the ten
attacks in the V2 acceptance brief. The goal was not to find crashes but to find queries
that return confident, evidence-bearing rows a Vedic scholar would call wrong.

Every finding below carries a count and a query. Where a suspicion could not be
substantiated it is marked **UNPROVEN** rather than dropped or asserted.

## 0. Snapshot integrity — read this first

The graph and the ontology source both changed **while this audit was running**. Counts in
this report are pinned to the snapshot noted against each finding.

| observation | at audit start | at audit end |
|---|---|---|
| nodes | 100,779 | 100,780 |
| relationships | 241,548 | 242,147 |
| `MENTIONS_ENTITY` | 37,693 | 37,675 |
| `:Concept` / `:DomainEntity` nodes | 162 | 163 |
| distinct relationship types | 39 | 44 |
| `RELATIONSHIP_SIGNATURES['MENTIONS_ENTITY']` object set | `{DomainEntity}` | `{DomainEntity, Devata}` |

A second write pass landed mid-session and populated nine previously-empty V2 predicates
(`ADDRESSES_CONCERN` 219, `PROTECTS_FROM` 182, `USED_FOR_RITE` 96, `TREATS` 87,
`USES_OBJECT` 11, `PERFORMED_BY` 6, `INVOKES_DEVATA` 5, `USES_SUBSTANCE` 4,
`PERFORMED_FOR` 4, `USES_OFFERING` 3 = +617 edges). Separately,
`src/vedagraph/domain/ontology.py` was modified at 12:50:09 local, widening the
`MENTIONS_ENTITY` signature so that the 9,000 `-> :Devata` edges became legal. The whole
of `src/vedagraph/domain/` is untracked in git (`git status` reports
`?? src/vedagraph/domain/`), so this change leaves no diff.

**Finding I1 (MAJOR).** No count published from this database is reproducible, and a
signature table that is edited to match the data cannot function as a check on the data.
An acceptance gate needs a frozen snapshot and a committed ontology.

```cypher
// snapshot fingerprint — re-run before trusting any number below
MATCH (n) RETURN count(n) AS nodes;
MATCH ()-[r]->() RETURN count(r) AS rels;
MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC;
```

---

## 1. Findings table, ranked by severity

| # | severity | finding | affected |
|---|---|---|---|
| C1 | **CRITICAL** | `theonym_ambiguous` is computed against deity *stem labels*, not the inflected aliases it tests, so it misses every non-stem form — above all the vocative. The graph asserts the impersonal reading of `agni` 2,095 times with 146 flags. | 2,454 unflagged edges that meet the documented rule verbatim; 1,052 AGNI-FIRE edges whose only evidence is a vocative theonym, 0 flagged |
| C2 | **CRITICAL** | Every deity-bearing predicate is Rigveda-only or near-zero outside it. "Is Indra in the Atharvaveda?" answers **15 passages** where the graph's own stored Sanskrit contains `indra` in **571**. No disclosure at the point of use. | 15 vs 571 AV passages (97.4% under-report); 4 predicates × 3 Vedas at zero |
| C3 | **CRITICAL** | 21,246 `ABOUT_CONCEPT` edges rest solely on matching an English word in Griffith 1896, and carry `knowledge_layer=L2_DETERMINISTIC_DERIVED` / `quality_tier=TIER_B` — identical grading to the Sanskrit-grounded edges. | 21,246 of 47,542 (44.7%) of the largest product predicate |
| M1 | MAJOR | Naive and `PER_PASSAGE` Ṛṣi leaderboards disagree almost completely, and `Devata.profile_top_rishis` publishes the naive one. The `PER_PASSAGE` view is *also* unrepresentative — Agni's top "Ṛṣi" becomes `devāḥ`, "the gods". | Indra 2/10 top-10 overlap; Agni 1/10; 8,329 + 10,093 inherited edges |
| M2 | MAJOR | `Devata` nodes carry no `:DomainEntity` marker, so 9,000 `MENTIONS_ENTITY` edges (23.9%) are invisible to `-[:MENTIONS_ENTITY]->(:DomainEntity)`. | 9,000 edges; 0 of 214 Devata carry the marker |
| M3 | MAJOR | 14,944 product-facing edges across 18 undeclared relationship types, while the V2 predicates written to replace them have 0 edges. The ontology declares the fix and the graph does not apply it. | 14,944 edges; 14 V2 types at 0 with no `UNPOPULATED_BY_DESIGN` entry |
| M4 | MAJOR | `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED.method` asserts the mention layer "flags every edge whose entire alias evidence is theonymous". It does not, by 2,454 edges. Same field cites "30 of 89 registry entities" against a 163-entity registry. | 1 claim, 2 false statements |
| M5 | MAJOR | `VG:CLAIM:CONCEPT-LAYER-LEANS-ON-TRANSLATION.claim_text` says the V2 layer "reaches 78.0% of Rigvedic mantras". Its own cited metric says 0.7937 and the graph says 8,375/10,552 = 79.37%. | 1 claim, 1.37pp mismatch |
| M6 | MAJOR | `is_composite = false` on all 214 `Devata` nodes, contradicting `structure` = PAIR/GROUP on 71 of them and 28 live `COMPOSED_OF` edges. | 214 nodes; 71 self-contradictory |
| M7 | MAJOR | 104 edges carry `quality_tier=TIER_B` under `knowledge_layer=L4_INTERPRETIVE_CLAIM`, violating `TIER_BY_LAYER` in the over-confident direction. | `MEASURES` 76, `COMPOSED_OF` 28 |
| I1 | MAJOR | Live graph and ontology mutated mid-audit; `src/vedagraph/domain/` untracked. | see §0 |
| N1 | MINOR | 736 `L3_LLM_EXTRACTED` edges graded `TIER_D` where `TIER_BY_LAYER` says `TIER_C`. Over-conservative, so not misleading. | 736 edges |
| N2 | MINOR | 617 edges lack `attribution_precision`, which the V2 contract requires on every edge. All 617 are from the mid-audit write pass. | 617 of 242,147 (0.25%) |
| N3 | MINOR | 4,576 evidence spans (SV 2,333 + YV 2,243) cite passages whose only stored text is Devanagari while the quote is IAST. The evidence is not checkable against any stored surface. | 4,576 of 28,675 spans (16.0%) |
| N4 | MINOR | 14 evidence quotes degeminate `cch` → `ch`, so a reader's copy-paste search fails. | 14 of 24,099 (0.058%) |
| N5 | MINOR | 101 of 214 deities are wired by `HAS_AXIS` to an `UNSPECIFIED` axis node, so an edge-based count of classified deities returns 214/214 where the property-based count is 113/214. | 101 edges |
| N6 | MINOR | 57 of 71 PAIR/GROUP deities have no `COMPOSED_OF` edge, so "who is in this pair" is unanswerable for 80% of pairs. | 57 nodes |
| N7 | MINOR | 3 declared `PRODUCT_LABELS` have 0 nodes (`Region`, `RishiFamily`, `Theme`) while `HAS_THEME` has 8 edges pointing at `:Concept` instead. | 3 labels, 8 mistyped edges |
| N8 | MINOR | `sakhā` (114 edges) maps *sákhi* "friend, a person" onto `SAKHYA-FRIENDSHIP`, an abstract. 92% of translated rows render it "Friend"/"companion", 0% "friendship". | 114 edges |
| N9 | MINOR | English-surface `ABOUT_CONCEPT` evidence quotes are truncated mid-word (`"h terror like a dart shot forth"` for "He strikes with terror…"). | sampled across 21,246 |

**Severity counts: 3 CRITICAL, 8 MAJOR, 9 MINOR, 13 CLEAN.**

---

## 2. CRITICAL findings in detail

### C1 — The theonym-ambiguity flag misses the forms that most certainly mean the deity

`VG:CONCEPT:AGNI-FIRE.short_description` reads, verbatim:

> Fire as the ritual and natural phenomenon: the flame kindled on the altar and the burning
> that consumes, warms and carries. **NOT the deity Agni, which is VG:DEVATA:AGNIH.**

2,095 `MENTIONS_ENTITY` edges point at that node. 915 of them are supported by the single
alias `agne` — the **vocative**, "O Agni!", a form that by definition addresses an animate
addressee. Not one is flagged.

```cypher
// 915 assertions of "fire, not the deity", every one evidenced by a vocative address to the deity
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e {entity_key:'VG:CONCEPT:AGNI-FIRE'})
WHERE r.matched_aliases = ['agne']
RETURN count(*) AS edges, sum(CASE WHEN r.theonym_ambiguous THEN 1 ELSE 0 END) AS flagged;
// => edges = 915, flagged = 0
```

Widening to every vocative form of the theonym (`agne`, `agna`, `jātavedaḥ`, `jātavedas`):

```cypher
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e {entity_key:'VG:CONCEPT:AGNI-FIRE'})
WHERE ALL(a IN r.matched_aliases WHERE a IN ['agne','agna','jātavedaḥ','jātavedas'])
RETURN count(*) AS edges, sum(CASE WHEN r.theonym_ambiguous THEN 1 ELSE 0 END) AS flagged;
// => edges = 1052 (50.2% of the entity), flagged = 0
```

**Reader-checkable example.** RV 1.1.1, the first verse of the corpus:

```cypher
MATCH (p:Passage {canonical_key:'VG:RV:SAK:M01:S001:V001'})
      -[r:MENTIONS_ENTITY]->(e {entity_key:'VG:CONCEPT:AGNI-FIRE'})
RETURN r.matched_aliases, r.theonym_ambiguous, r.quality_tier;
// => ['agnim'], false, 'TIER_B'
```

Griffith: *"I laud Agni, the chosen Priest, God, minister of sacrifice."* The graph records
this at TIER_B as a mention of fire-the-phenomenon-not-the-deity, unflagged.

**Root cause, exactly.** `scripts/build_domain_v2.py:114` builds the theonym set from
`label_iast`:

```python
devata_labels = [entry.label_iast or entry.entity_key for entry in taxonomy]
```

`src/vedagraph/domain/mentions.py:341` then tests concept aliases against it:

```python
ambiguous = bool(aliases) and all(alias in index.theonyms for alias in aliases)
```

`Devata.label_iast` for Agni is the *stem* `agni`. The concept aliases being tested are
*inflected*: `agne`, `agna`, `agnir`, `agniṃ`, `agnim`, `agnaye`. Only forms that fold to
the stem match. Measured over all 28,675 edges:

| | count |
|---|---|
| flagged `theonym_ambiguous = true` | 1,092 |
| **not** flagged, yet every matched alias is **verbatim** in some `Devata.aliases_iast` | **2,454** |
| not flagged, every alias reaches a deity alias only after sandhi folding | 1,194 |
| flagged where no alias is a declared deity alias (false positives) | 157 |

Against the rule the docstring states, the flag has a **72.4% false-negative rate**
(2,454 missed of 3,389 that qualify on exact match) and recall of **23.8%** if sandhi
variants are included.

The mechanism is visible per alias: `agniḥ` (146/158 flagged), `soma` (402/416),
`sūrya` (102/104) and `pṛthivī` (181/193) fold to the stem and *are* caught, while
`agne` (0/915), `agna` (0/141), `agnir` (0/312), `agniṃ` (0/229), `somo` (0/208),
`somam` (0/167), `somasya` (0/148), `sūryasya` (0/131) and `pṛthivyā` (0/140) are not.

47 concept aliases are verbatim declared Devatā aliases; **only 7 of them are also equal
to a `Devata.label_iast`** — and `label_iast` is the only set the flag tests.

```cypher
// the collision surface the flag does not see
MATCH (d:Devata) UNWIND d.aliases_iast AS da WITH collect(DISTINCT da) AS deity_aliases
MATCH ()-[r:MENTIONS_ENTITY]->(e:DomainEntity)
WHERE r.theonym_ambiguous = false
  AND size(r.matched_aliases) > 0
  AND ALL(a IN r.matched_aliases WHERE a IN deity_aliases)
RETURN e.entity_key, count(*) AS unflagged ORDER BY unflagged DESC;
// AGNI-FIRE 1059, SOMA-DRINK 439, SURYA-SUN 249, PRTHIVI-EARTH 137, USAS-DAWN 123, ... total 2454
```

**Consequence.** 1,052 passages carry `HAS_DEVATA -> Agni` *and* an unflagged
`MENTIONS_ENTITY -> AGNI-FIRE` from the same word:

```cypher
MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'})
MATCH (p)-[m:MENTIONS_ENTITY]->({entity_key:'VG:CONCEPT:AGNI-FIRE'})
WHERE m.theonym_ambiguous = false
RETURN count(DISTINCT p);   // => 1052
```

This contradicts the project's own claim `VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED`,
which states the corpus does not lexically distinguish the two. The claim layer says the
distinction cannot be drawn from the word; the mention layer draws it 2,095 times and
flags 146.

### C2 — The graph will deny a deity's presence in the Atharvaveda

Every predicate that reaches a `:Devata` node, by Veda:

```cypher
MATCH (p:Passage)-[r]->(:Devata)
RETURN type(r) AS rel, p.veda AS veda, count(*) AS c ORDER BY rel, veda;
```

| predicate | RV | SV | YV | AV |
|---|---|---|---|---|
| `HAS_DEVATA` | 10,558 | 0 | 0 | 0 |
| `MENTIONS_ENTITY` → Devata | 9,000 | 0 | 0 | 0 |
| `INVOKES` | 0 | 0 | 123 | 99 |
| `DESCRIBES` | 0 | 0 | 64 | 58 |
| `PRAISES` | 0 | 0 | 25 | 13 |

So a reader asking the obvious question gets an answer that is wrong by two orders of
magnitude, measured **against the graph's own stored text**:

```cypher
// what the graph asserts
MATCH (p:Passage {veda:'AV'})-->(d:Devata {entity_key:'VG:DEVATA:INDRAH'})
RETURN count(DISTINCT p);                                             // => 15
// what the graph's own Sanskrit says
MATCH (p:Passage {veda:'AV'})-[:HAS_TEXT_VERSION]->(t:TextVersion)
WHERE toLower(t.text_nfc) CONTAINS 'indra' RETURN count(DISTINCT p);  // => 571
// what the graph's own translation says
MATCH (p:Passage {veda:'AV'})-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.text CONTAINS 'Indra' RETURN count(DISTINCT p);               // => 451
```

| deity | AV passages via any deity edge | AV Sanskrit hits | AV translation hits | under-report |
|---|---|---|---|---|
| Indra | 15 | 571 | 451 | 97.4% |
| Agni | 24 | 275 | 459 | 91.3% |
| Soma | 3 | 179 | 142 | 98.3% |
| Varuṇa | 4 | 108 | 5 | 96.3% |
| Rudra | 3 | 27 | 55 | 88.9% |

**Checkable example.** AV 1.2.3 (`VG:AV:SAU:K01:S002:V003`) — *"keep away from us, O Indra,
the shaft"* — a direct vocative address to Indra, with no edge to the Indra node.

**Is the hazard disclosed at the point of use?** No.

- `Work` nodes carry no attribution-coverage property: keys are
  `display_label, work_id, display_type, corpus_dir, abbreviation, work_name, veda`.
- `HAS_DEVATA` edges carry `source_id: WSC2023` but no coverage statement.
- `DevataProfile` does the right thing — `profile_attribution_scope: ['RV']` — **but only
  25 of 214 Devatā nodes carry a profile at all**. The other 189, including Rudra, Vāyu and
  Pūṣan, carry no `profile_*` key, so absence of the scope note is silent.
- The metric `ATTRIBUTION_PRECISION_CORPUS` carries an honest
  `scope_note: "Rigveda only: the Anukramani attribution layer does not cover SV, YV or AV"`
  — but its `subject_key` is `VG:CORPUS:FOUR-VEDA` and the note is not reachable from any
  deity query.

```cypher
MATCH (d:Devata) RETURN count(*) AS all_devata,
  sum(CASE WHEN d.profile_attribution_scope IS NOT NULL THEN 1 ELSE 0 END) AS with_scope_note;
// => 214, 25
```

### C3 — 21,246 TIER_B assertions about the Vedas rest on a Victorian English translation

```cypher
MATCH ()-[r:ABOUT_CONCEPT]->()
RETURN r.method AS method, r.knowledge_layer AS layer, r.quality_tier AS tier, count(*) AS c
ORDER BY c DESC;
```

| method | layer | tier | count |
|---|---|---|---|
| `concept-alias-v1:english` | `L2_DETERMINISTIC_DERIVED` | **TIER_B** | **21,246** |
| `concept-alias-v1:english+sanskrit-token` | `L2_DETERMINISTIC_DERIVED` | TIER_B | 13,015 |
| `concept-alias-v1:sanskrit-token` | `L2_DETERMINISTIC_DERIVED` | TIER_B | 12,808 |
| `concept-alias-v1:sanskrit-sandhi` | `L2_DETERMINISTIC_DERIVED` | TIER_B | 473 |

44.7% of the graph's largest product predicate rests on no Sanskrit evidence at all, and
`knowledge_layer`, `quality_tier` and `grade_basis` (`trust=DETERMINISTIC_DERIVED`) are
byte-identical to the Sanskrit-grounded rows. The distinction survives only in the
free-text `method` string and in the `evidence[].surface` field (`"translation_en"`),
neither of which a tier filter touches.

**Checkable example.** RV 1.66.4 asserts `ABOUT_CONCEPT -> VG:CONCEPT:AYUDHA-WEAPON` at
TIER_B, from Griffith's *"e'en like an archer's arrow tipped with flame"* — an inference
from a translator's word choice, graded the same as a Sanskrit token match:

```cypher
MATCH (p:Passage {canonical_key:'VG:RV:SAK:M01:S066:V004'})
      -[r:ABOUT_CONCEPT]->(e {entity_key:'VG:CONCEPT:AYUDHA-WEAPON'})
RETURN r.quality_tier, r.knowledge_layer, r.grade_basis, r.method, r.evidence;
// TIER_B | L2_DETERMINISTIC_DERIVED | 'trust=DETERMINISTIC_DERIVED' | 'concept-alias-v1:english'
```

Distribution: RV 14,260 / AV 4,150 / YV 2,836 / SV 0 (SV has no translation, so the
English path correctly cannot fire there).

The project *has* documented this, at TIER_D, in
`VG:CLAIM:CONCEPT-LAYER-LEANS-ON-TRANSLATION`. The defect is that the disclosure lives in
the claim layer while the edges a query returns carry no trace of it.

---

## 3. Attack 1 — scope-inherited attribution presented as fact

Snapshot: `HAS_DEVATA` 8,329/10,558 (78.9%) `CONTAINER_INHERITED`; `HAS_RISHI`
10,093/10,565 (95.5%); `HAS_CHANDAS` 6,276/10,523 (59.6%). All three figures match the
stored `ATTRIBUTION_PRECISION_CORPUS` metric exactly.

```cypher
// naive leaderboard — no precision filter
MATCH (p:Passage)-[d:HAS_DEVATA]->(dev:Devata {entity_key:'VG:DEVATA:INDRAH'})
MATCH (p)-[ri:HAS_RISHI]->(rs:Rishi)
RETURN rs.display_label AS rishi, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 10;

// PER_PASSAGE-only leaderboard
MATCH (p:Passage)-[d:HAS_DEVATA]->(dev:Devata {entity_key:'VG:DEVATA:INDRAH'})
WHERE d.attribution_precision = 'PER_PASSAGE'
MATCH (p)-[ri:HAS_RISHI]->(rs:Rishi)
WHERE ri.attribution_precision = 'PER_PASSAGE'
RETURN rs.display_label AS rishi, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 10;
```

**Indra** — 2,869 passages naive, 655 `PER_PASSAGE` (22.8% survive):

| rank | naive | n | PER_PASSAGE | n |
|---|---|---|---|---|
| 1 | gāthino viśvāmitraḥ | 217 | kāṇvau medhātithimedhyātithī | 27 |
| 2 | gautamo vāmadevaḥ | 194 | gautamo vāmadevaḥ | 9 |
| 3 | bārhaspatyo bharadvājaḥ | 165 | bhāgavo nemaḥ | 8 |
| 4 | maitrāvaruṇirvasiṣṭhaḥ | 163 | aindro vasukraḥ | 6 |
| 5 | śaunako gṛtsamadaḥ | 141 | indraḥ | 6 |
| 6 | kāṇvo medhātithiḥ | 81 | kākṣīvataḥ sukīrtiḥ | 5 |
| 7 | vaiśvāmitro madhucchandāḥ | 75 | ghauraḥ pragāthaḥ | 2 |
| 8 | āṅgirasaḥ savyaḥ | 72 | agnivaruṇasomāḥ | 1 |
| 9 | bārhaspatyaḥ śaṁyuḥ | 68 | bandhuḥ śrutabandhuḥ… | 1 |
| 10 | rāhūgaṇo gotamaḥ | 57 | gāthino viśvāmitraḥ | 1 |

**Rank overlap:** top-5 = **1/5** shared (`gautamo vāmadevaḥ`); top-10 = **2/10**
(`gautamo vāmadevaḥ`, `gāthino viśvāmitraḥ`).

**Verdict on the prior audit's claim.** The earlier finding that the two Indra lists share
exactly ONE name is **confirmed at top-5 and refuted at top-10**, where they share two.
The prior claim was true but its cut-off was not stated.

**Agni** — 1,988 passages naive, 200 `PER_PASSAGE` (10.1% survive). The `PER_PASSAGE`
list has only **four** entries in total:

| rank | naive | n | PER_PASSAGE | n |
|---|---|---|---|---|
| 1 | gāthino viśvāmitraḥ | 179 | **devāḥ** ("the gods") | 14 |
| 2 | bārhaspatyo bharadvājaḥ | 173 | gāthino viśvāmitraḥ | 7 |
| 3 | gautamo vāmadevaḥ | 171 | agnivaruṇasomāḥ | 1 |
| 4 | maitrāvaruṇirvasiṣṭhaḥ | 140 | brahma | 1 |

top-10 overlap **1/10**; top-5 overlap **1/5**.

**The finding cuts both ways, and this matters.** The naive list is not simply wrong: the
Anukramaṇī genuinely assigns whole sūktas to Ṛṣis, so a sūkta-scoped leaderboard is a
defensible scholarly answer. But the `PER_PASSAGE` list — the one the precision property
invites a careful reader to prefer — is **worse**, because `PER_PASSAGE` Ṛṣi edges exist
only where the Anukramaṇī split a sūkta by mantra. That is 4.5% of Ṛṣi attributions and a
systematically unrepresentative slice: it makes `devāḥ`, "the gods", the top composer of
Agni verses.

Nothing in the graph warns that `PER_PASSAGE` coverage is not a random sample. There is
no property that says so, and the two views are freely comparable in Cypher.

**`Devata.profile_top_rishis` publishes the naive list**, verbatim and unqualified:

```cypher
MATCH (d:Devata {entity_key:'VG:DEVATA:AGNIH'})
RETURN d.profile_top_rishis[0..3] AS top, d.profile_per_passage_share AS pps;
// => ['gāthino viśvāmitraḥ','bārhaspatyo bharadvājaḥ','gautamo vāmadevaḥ'], 0.1006
```

Mitigation, and it is real: the same node carries `profile_per_passage_share` (0.1006 for
Agni, 0.2283 for Indra), `profile_attributed_total` and `profile_attributed_per_passage`,
so the inherited share is disclosed *adjacent to* the list. Graded **MAJOR, not CRITICAL**,
for that reason.

---

## 4. Attack 2 — deity/concept collapse, per entity

The named entity pairs are distinct nodes with distinct labels. They are **not** distinct
in the mention evidence: the same alias strings feed both.

```cypher
// mention-set overlap and shared alias strings for a deity/concept pair
MATCH (p:Passage)-[:MENTIONS_ENTITY|HAS_DEVATA]->(:Devata {entity_key:$d})
WITH collect(DISTINCT p.canonical_key) AS D
MATCH (q:Passage)-[:MENTIONS_ENTITY]->(:DomainEntity {entity_key:$c})
WITH D, collect(DISTINCT q.canonical_key) AS C
RETURN size(D) AS deity_passages, size(C) AS concept_passages,
       size([x IN D WHERE x IN C]) AS both;
```

| deity | concept | deity passages | concept passages | both | Jaccard | shared alias strings |
|---|---|---|---|---|---|---|
| `SOMAH` | `SOMA-DRINK` | 968 | 1,570 | 821 | 0.478 | `soma, somam, somasya, somaḥ, somāsaḥ, somāya` |
| `AGNIH` | `AGNI-FIRE` | 2,327 | 2,095 | 1,351 | 0.440 | `agnaye, agne, agnim, agniḥ` |
| `SURYAH` | `SURYA-SUN` | 406 | 653 | 343 | 0.479 | `sūrya, sūryam, sūryasya, sūryaḥ` |
| `PRTHIVI` | `PRTHIVI-EARTH` | 321 | 742 | 294 | 0.382 | `pṛthivī, pṛthivīm, pṛthivyāḥ` |
| `VAK` | `VAC-SPEECH` | 3 | 651 | 2 | **0.003** | `vācaṃ, vāco, vāk` |

Vāc is separate only because `VG:DEVATA:VAK` has 3 passages; the alias sets still collide.

### Per-entity error estimate, from the English translation

Method: for each entity's mention passages, test whether the translation renders the token
as a capitalised proper name (deity reading) or a lower-case common noun (the reading the
concept node asserts). `deity_only` = the translation names the god and never uses the
common noun. This is a **conservative lower bound**: rows tagged `both` may also be deity
readings.

```cypher
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e {entity_key:'VG:CONCEPT:AGNI-FIRE'})
MATCH (p)-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.text =~ '.*\\bAgni\\b.*' AND NOT t.text =~ '.*\\b(fire|flame|blaze)\\b.*'
RETURN count(DISTINCT p);
```

| entity | edges | with translation | deity only | both | element only | neither | **error estimate** |
|---|---|---|---|---|---|---|---|
| `AGNI-FIRE` | 2,095 | 1,934 | 1,565 | 104 | 132 | 133 | **80.9%** |
| `SOMA-DRINK` | 1,570 | 1,241 | 761 | 121 | 280 | 79 | **61.3%** (see caveat) |
| `SURYA-SUN` | 653 | 555 | 157 | 1 | 154 | 243 | **28.3%** |
| `PRTHIVI-EARTH` | 742 | 688 | 136 | 7 | 520 | 25 | **19.8%** |
| `BRAHMAN-FORMULATION` | 482 | 417 | 46 | 10 | 189 | 172 | **11.0%** |
| `VAC-SPEECH` | 651 | 524 | 15 | 3 | 460 | 46 | **2.9%** |

**Hand adjudication of AGNI-FIRE.** 16 randomly drawn `agne`/`agna` rows were read in
full. 16 of 16 are vocative addresses to the deity, and Griffith renders every one as a
proper name: RV 1.58.8 *"O Agni, Son of Strength"*; RV 10.87.16 *"O Agni,-tear off the
heads of such"*; RV 7.7.2 *"come hither, Agni, joyous"*; RV 8.11.3 *"O Jatavedas Agni,
fight and drive our foes"*; AV 9.5.19 *"all that of ours, O Agni"*; AV 7.110.1 *"O Agni,
together with Indra"*; YV 15.44 *"Agni, with lauds this day may we bring thee"*.

**SOMA-DRINK caveat — marked partly UNPROVEN.** Griffith capitalises "Soma" for the drink
as well as the god, so the 61.3% figure is not a reliable error estimate for this entity.
What *is* established: 402 of the 1,570 edges (25.6%) are supported by `soma` alone, the
vocative, and the node's own description says "the substance, **not the deity of the same
name**". Those 402 *are* flagged `theonym_ambiguous` — this is the one high-volume case the
flag catches, because `soma` folds to the deity's stem. The true error rate for SOMA-DRINK
is between 25.6% and 61.3% and this audit cannot narrow it further from translations alone.

**PRTHIVI-EARTH / SURYA-SUN / VAC-SPEECH / DYAUS-HEAVEN are graded lower** because their
node descriptions are neutral ("The earth as the lower world…") and do not exclude the
deity, so a deity-address matching them is not self-contradictory in the way AGNI-FIRE and
SOMA-DRINK are.

---

## 5. Attack 3 — per-alias precision (the central table)

Method, in three passes, because per-row sampling cannot see this:

1. **Automated gloss screen** over the top 45 aliases by volume: does the English
   translation of each mention passage contain any expected gloss of the target entity?
2. **Hand reading** of a sample of every alias that failed the screen, to separate a
   genuine mismatch from a gloss-list gap or a Griffith abridgement.
3. **Morphological test** for the theonym cases: a vocative form addresses an animate
   addressee, so an entity node that excludes the deity cannot be its referent. This test
   is objective and does not depend on a translation.

**The gloss screen is exactly the trap the brief warns about.** It scores `agne` at
**97.5% "correct"** — because the gloss list for `AGNI-FIRE` contains the word "agni", and
Griffith prints "Agni" in 97.5% of those passages. A per-row precision audit would report
the same. Only the morphological test reveals that the same 915 rows are 100% wrong about
*which* Agni.

Precision is reported on two questions, because they diverge:

- **P(token)** — does the passage contain the word the alias claims? This is what a
  per-row sample measures.
- **P(referent)** — is the entity the graph names the actual referent, judged against that
  entity node's own `short_description`? This is what a reader is misled by.

| # | alias | vol | target entity | P(token) | P(referent) | error | **vol × error** | basis |
|---|---|---|---|---|---|---|---|---|
| **1** | **`agne`** | **915** | AGNI-FIRE | 0.98 | **0.05** | **0.95** | **869** | vocative; 16/16 hand-read as "O Agni"; 0/915 flagged |
| **2** | **`soma`** | **416** | SOMA-DRINK | 0.99 | **0.35** | 0.65 | **270** | vocative; 402/416 flagged (the flag works here) |
| 3 | `agnir` | 312 | AGNI-FIRE | 0.99 | 0.30 | 0.70 | 218 | nominative; often "Agni is the hotar" |
| 4 | `agniṃ` | 229 | AGNI-FIRE | 0.99 | 0.35 | 0.65 | 149 | accusative; "I laud Agni" |
| 5 | `agna` | 141 | AGNI-FIRE | 0.98 | 0.05 | 0.95 | 134 | vocative variant; 8/8 hand-read as "O Agni" |
| 6 | `somo` | 208 | SOMA-DRINK | 0.99 | 0.45 | 0.55 | 114 | nominative; deity/substance undecidable |
| 7 | `agniḥ` | 158 | AGNI-FIRE | 0.98 | 0.35 | 0.65 | 103 | nominative; 146/158 flagged |
| 8 | `sakhā` | 114 | SAKHYA-FRIENDSHIP | 0.97 | 0.30 | 0.70 | 80 | *sákhi* "friend" (person) vs *sakhya* (abstract); 92% render "Friend" |
| 9 | `somam` | 167 | SOMA-DRINK | 0.99 | 0.60 | 0.40 | 67 | accusative; 0/167 flagged |
| 10 | `agnim` | 117 | AGNI-FIRE | 0.99 | 0.45 | 0.55 | 64 | accusative; 0/117 flagged |
| 11 | `somasya` | 148 | SOMA-DRINK | 0.99 | 0.65 | 0.35 | 52 | genitive; 0/148 flagged |
| 12 | `sūryasya` | 131 | SURYA-SUN | 0.98 | 0.70 | 0.30 | 39 | genitive; 0/131 flagged; entity neutral |
| 13 | `somaḥ` | 128 | SOMA-DRINK | 0.99 | 0.75 | 0.25 | 32 | nominative |
| 14 | `sūrya` | 104 | SURYA-SUN | 0.98 | 0.72 | 0.28 | 29 | vocative; 102/104 flagged |
| 15 | `somaṃ` | 143 | SOMA-DRINK | 0.99 | 0.82 | 0.18 | 26 | accusative sandhi form |
| 16 | `pṛthivī` | 193 | PRTHIVI-EARTH | 0.99 | 0.88 | 0.12 | 23 | 181/193 flagged; entity neutral |
| 17 | `brahma` | 204 | BRAHMAN-FORMULATION | 0.98 | 0.92 | 0.08 | 16 | 4.2% render "Priesthood"/"Brahma" (YV/AV late strata) |
| 18 | `divi` | 210 | DYAUS-HEAVEN | 0.99 | 0.93 | 0.07 | 15 | 4.5% render "on the day" (*div* = sky *and* day) |
| 19 | `apo` | 126 | AP-WATERS | 0.98 | 0.90 | 0.10 | 13 | 7.2% are *ápas* "work/deed" not *ā́paḥ* "waters" |
| 20 | `ṛtasya` | 236 | RTA-ORDER | 0.99 | 0.96 | 0.04 | 9 | 17.8% gloss-miss was a gloss gap: Griffith renders *ṛta* "sacrifice" |
| 21 | `hotā` | 213 | HOTR-PRIEST | 0.99 | 0.97 | 0.03 | 6 | 12.0% gloss-miss was "Herald"; office-holder is Agni, in scope per description |
| 22 | `sūryo` | 97 | SURYA-SUN | 0.98 | 0.94 | 0.06 | 6 | |
| 23 | `divaḥ` | 177 | DYAUS-HEAVEN | 0.99 | 0.97 | 0.03 | 5 | |
| 24 | `pṛthivyā` | 140 | PRTHIVI-EARTH | 0.99 | 0.97 | 0.03 | 4 | 0% gloss-miss |
| 25 | `brahmaṇā` | 106 | BRAHMAN-FORMULATION | 0.98 | 0.96 | 0.04 | 4 | 38.6% gloss-miss was a gloss gap: "incantation/charm/spell" |
| 26 | `rājā` | 163 | RAJAN-KINGSHIP | 0.99 | 0.98 | 0.02 | 3 | divine sovereignty explicitly in scope ("equally to men and to Varuna") |
| 27 | `divo` | 299 | DYAUS-HEAVEN | 0.99 | 0.99 | 0.01 | 3 | 0% homograph rate measured |
| 28 | `dyām` | 113 | DYAUS-HEAVEN | 0.99 | 0.98 | 0.02 | 2 | |
| 29 | `manasā` | 192 | MANAS-MIND | 0.99 | 0.99 | 0.01 | 2 | |
| 30 | `vasu` | 140 | VASU-WEALTH | 0.99 | 0.99 | 0.01 | 1 | gloss gap: "good (vásu)" |
| 31 | `śarma` | 146 | SARMAN-PROTECTION | 0.99 | 0.99 | 0.01 | 1 | gloss gap: "stronghold" |
| 32–45 | `yajñaṃ` 179, `rayiṃ` 193, `yajñam` 146, `ojasā` 132, `jyotir` 129, `haviṣā` 122, `ūtaye` 121, `rathaṃ` 121, `giraḥ` 116, `dhiyā` 108, `yajñasya` 105, `rayim` 103, `vājaṃ` 98, `sute` 97 | | | ≥0.98 | ≥0.98 | ≤0.02 | ≤4 each | 0–9% gloss-miss, all traced to gloss gaps or Griffith abridgements |

**The single alias doing the most damage: `agne`.** 915 edges, ~869 of them wrong about the
referent. It is the highest-volume alias in the entire mention layer, its target node
explicitly disclaims the deity, and its false-negative rate on the ambiguity flag is
**915/915**. A random sample of matched rows would have reported it as clean.

The three Agni vocative aliases together (`agne` 915, `agna` 141, `jātavedaḥ` 59) account
for 1,115 alias-hits and **1,052 whole edges** whose entire evidence is an address to the
god.

**`sute` — UNPROVEN, discriminator invalid.** The screen flagged 70.5% of `sute` rows as
rendering the pressed *drink* rather than the pressing *act*. On reading, `sute` is a
locative absolute, "when [the soma] is pressed", which is precisely the "act and occasion"
the `SOMA-PRESSING` node describes. The discriminator was wrong, not the data. Precision
estimated ≥0.90.

**Not auditable per alias: the 9,000 `MENTIONS_ENTITY -> :Devata` edges.** They carry no
`matched_aliases`, no `evidence` and no `score` — only
`annotation_layer_id: 'VEDAWEB.ZURICH'` and `grade_basis: 'lexical match over annotated
tokens'`. They share the predicate and the `TIER_B` grade with the alias-matched layer but
have an incompatible evidence schema, so `r.evidence` is null for 23.9% of the predicate.

---

## 6. Attack 4 — controlled-predicate violations

**Signature violations: 0** against the ontology as it stands at audit end. This is only
true because the `MENTIONS_ENTITY` signature was widened mid-audit (§0). Against the
signature as originally read, 9,000 edges violated it. The substantive defect survives the
widening and is recorded as **M2**: `Devata` nodes carry no `:DomainEntity` marker, so the
marker cannot do the job its docstring assigns it ("gives 'how big is the product graph' a
single label scan").

```cypher
MATCH ()-[r:MENTIONS_ENTITY]->(b) RETURN b:DomainEntity AS reachable, count(*) AS c;
// => true 28675, false 9000
MATCH (d:Devata) WHERE d:DomainEntity RETURN count(*);   // => 0 of 214
```

Any reader who follows `PRODUCT_NODE_FILTER`'s example and writes
`-[:MENTIONS_ENTITY]->(:DomainEntity)` silently loses every deity mention in the graph.

### Undeclared relationship types

18 product-facing types totalling **14,944 edges** appear in neither the V1 nor the V2
declared vocabulary. (A further 62,474 edges on `HAS_TEXT_VERSION`, `HAS_TRANSLATION` and
`HAS_QA_ISSUE` are undeclared but are internal plumbing to `:Internal` nodes; listed for
completeness, not counted as violations.)

```cypher
MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC;
```

| undeclared type | edges | the V2 predicate meant to replace it | its edge count |
|---|---|---|---|
| `NEAR_PARALLEL_OF` | 3,049 | `TEXTUALLY_REUSED_AS` | **0** |
| `REUSES_TEXT_FROM` | 1,684 | `TEXTUALLY_REUSED_AS` | **0** |
| `EXACT_PARALLEL_OF` | 1,006 | `TEXTUALLY_REUSED_AS` | **0** |
| `VARIANT_OF` | 788 | `TEXTUALLY_REUSED_AS` | **0** |
| `PARALLEL_TO` | 69 | `TEXTUALLY_REUSED_AS` / `MUSICALIZED_AS` | **0** |
| `DEVATA_ASSOCIATED_WITH` | 140 | `ASSOCIATED_WITH_CONCEPT` / `_PHENOMENON` / `_SUBSTANCE` | **0** |
| `DESCRIBES` | 280 | — | |
| `INVOKES` | 222 | `INVOKES_DEVATA` | 5 |
| `REQUESTS` | 109 | — | |
| `PRAISES` | 38 | — | |
| `DESCRIBES_ACTION` | 35 | `PERFORMS_ACTION` | **0** |
| `INVOLVES_OFFERING` | 14 | `USES_OFFERING` | 3 |
| `INVOLVES_RITUAL` | 11 | — | |
| `HAS_THEME` | 8 | — | |
| `CONTRASTS_WITH` | 8 | — | |
| `REFERS_TO_NATURAL_PHENOMENON` | 5 | `ASSOCIATED_WITH_PHENOMENON` | **0** |
| `REFERS_TO_PLACE` | 3 | — | |
| `INVOLVES_SUBSTANCE` | 3 | `USES_SUBSTANCE` | 4 |

The ontology docstring states the reason for the split, in terms:

> Kept distinct because "the same verse appears in Sāmaveda" and "the verse was set to a
> melody" are different claims with different evidence, and collapsing both into
> `PARALLEL_TO` is what made the Sāmaveda look like a duplicate corpus.

`PARALLEL_TO` has 69 live edges and `TEXTUALLY_REUSED_AS` has 0. **The stated fix is
declared and not applied.** Graded MAJOR rather than CRITICAL because the legacy types are
not themselves wrong — they are ungoverned. A reader gets an answer; the controlled
vocabulary simply does not control 14,944 edges.

### Dead declared vocabulary

14 declared V2 relationship types have 0 edges and no `UNPOPULATED_BY_DESIGN` entry:
`ASSERTED_BY`, `ASSOCIATED_WITH_CONCEPT`, `ASSOCIATED_WITH_PHENOMENON`,
`ASSOCIATED_WITH_SUBSTANCE`, `ASSOCIATED_WITH_TRIBE`, `BELONGS_TO_FAMILY`,
`CO_OCCURS_WITH`, `DESCRIBED_IN`, `HAS_STEP`, `PERFORMS_ACTION`, `PERSONIFIES`,
`RECEIVES_OFFERING`, `TEXTUALLY_REUSED_AS`, `WIELDS`. `MUSICALIZED_AS` is the fifteenth and
is the only one documented as empty on purpose — an honest placeholder with a written
reason. The other 14 are dead weight, and four of them (`BELONGS_TO_FAMILY`,
`ASSOCIATED_WITH_TRIBE`, plus the `RishiFamily` and `Region` labels) mean the Ṛṣi social
structure the V2 docstring cites for Q2/Q19/Q24/Q26/Q35 does not exist in the graph at all.

---

## 7. Attack 5 — named conflations

| pair the spec names | kept apart? | evidence |
|---|---|---|
| Soma deity vs Soma substance | **NO, effectively merged** | separate nodes, but 6 identical alias strings, 821 shared passages, Jaccard 0.478 |
| Agni deity vs fire | **NO, effectively merged** | 4 identical alias strings, 1,351 shared passages, Jaccard 0.440 |
| Vāc deity vs speech | nominally yes | Jaccard 0.003, but only because `VG:DEVATA:VAK` has 3 passages; the alias sets still collide on `vācaṃ, vāco, vāk` |
| **Savitṛ vs Sūrya** | **YES — CLEAN** | 0 shared `HAS_DEVATA` passages, no edge between them, disjoint aliases (`savitā/savituḥ/savitaḥ` vs `sūrya/sūryaḥ/sūryam/sūryasya`), distinct axes (Savitṛ adds `ABSTRACT_PERSONIFICATION`) |
| **Mitra vs Varuṇa vs Mitrāvaruṇau** | **YES — CLEAN** | three nodes; `MITRAVARUNAU` is `structure: PAIR` with `COMPOSED_OF` to both members; 0 passages carry both `MITRAH` and `MITRAVARUNAU`; disjoint alias sets |
| **Rudra with no Śiva identification** | **YES — CLEAN, exemplary** | 0 hits for `śiva\|shiva\|siva` across every string property of every node and every edge in the database |

```cypher
// Rudra/Siva: zero hits, whole database
MATCH (n) UNWIND keys(n) AS k WITH n,k
WHERE n[k] IS :: STRING AND toLower(n[k]) =~ '.*(śiva|shiva|\\bsiva)\\b.*'
RETURN labels(n), k LIMIT 10;                        // => 0 rows
MATCH ()-[r]->() UNWIND keys(r) AS k WITH r,k
WHERE r[k] IS :: STRING AND toLower(r[k]) =~ '.*(śiva|shiva|\\bsiva)\\b.*'
RETURN type(r), k LIMIT 10;                          // => 0 rows
```

`VG:DEVATA:RUDRAH.curation_note` states the refusal and its reasoning, including that the
epithet *tryambaka* was probed and returns zero token hits. This is the standard the rest
of the conflation handling should be held to.

---

## 8. Attack 6 — interpretive claims

**Structurally sound on every check.**

| check | result |
|---|---|
| all claims `TIER_D` | 6/6 |
| status values | `MODEL_SYNTHESIS` 4, `RESEARCH_HYPOTHESIS` 2 — none asserted as settled |
| anything outside the claim layer pointing INTO a claim | **0** (only `CONTRADICTS`, claim→claim) |
| claim carrying a domain label (`Passage`/`Devata`/`Concept`/`DomainEntity`) | **0** |
| `CONTRADICTS` pair present, symmetric, neither settled | yes — `SV-IDENTITY-IS-MELODIC` (LOW, hypothesis) ↔ `SV-PREDOMINANTLY-RV-REUSE` (MEDIUM, synthesis) |
| `SUPPORTED_BY_STATISTIC` targets exist | 6/6 resolve to a real `DerivedMetric` |
| `SUPPORTED_BY` targets exist | 7/7 resolve to a real `Passage` |

```cypher
MATCH (a)-[r]->(c:InterpretiveClaim) RETURN labels(a), type(r), count(*);
// => [['InterpretiveClaim'], 'CONTRADICTS', 2]  -- nothing else points into a claim
```

### Cited numbers, checked one by one

| claim | number asserted | graph says | verdict |
|---|---|---|---|
| `ANUKRAMANI-ATTRIBUTION-IS-SUKTA-SCOPED` | 8,329/10,558 `HAS_DEVATA`; 10,093/10,565 `HAS_RISHI`; 6,276/10,523 `HAS_CHANDAS` | identical | **✅ exact** |
| `RISHI-ATTRIBUTION-LEAST-VERSE-SPECIFIC` | 95.5% seer, 59.6% metre inherited | 10,093/10,565 = 95.53%; 6,276/10,523 = 59.64% | **✅ exact** |
| `SV-PREDOMINANTLY-RV-REUSE` | 1,662 of 1,844 SV mantras (90.1%) | 1,662 distinct SV mantras with `REUSES_TEXT_FROM`; 1,844 SV mantras; 90.13% | **✅ exact** |
| `CONCEPT-LAYER-LEANS-ON-TRANSLATION` | 21,246 of 47,542 (44.7%) | 21,246 `method='concept-alias-v1:english'`; 47,542 total | **✅ exact** |
| " | "the concept layer reported 96.1%" | 10,144/10,552 = 96.13% | **✅ exact** |
| " | "the V2 mention layer … **reaches 78.0%** of Rigvedic mantras" | 8,375/10,552 = **79.37%**; cited metric `values_json` says **0.7937** | **❌ M5 — MISMATCH** |
| `AGNI-LEXICALLY-UNDIFFERENTIATED` | "the mention layer **flags every edge** whose entire alias evidence is theonymous" | false by 2,454 edges (§C1) | **❌ M4 — FALSE** |
| " | "**30 of 89** registry entities carry at least one Sanskrit alias that is also a Devata label form" | the registry has **163** entities; 24 entities carry a verbatim deity-alias collision across 47 alias strings | **❌ M4 — stale denominator** |
| metric `THEONYM_AMBIGUITY` | `{mention_edges: 28675, theonym_ambiguous: 1092, share: 0.0381}` | 28,675 and 1,092 both exact; 1092/28675 = 0.03808 | **✅ exact** |

**The specific defect the brief asked me to hunt for — "a claim whose text asserts a number
the metric does not support" — exists, twice, and neither instance is the worst case.**

- **M5** is a 1.37pp understatement (78.0% vs 79.37%) that makes the claim's own case
  slightly *weaker* than the data. It is a defect, not a deception.
- **M4** is worse in kind and is what I would fix first: the AGNI claim's `method` field
  asserts a property of the graph (complete theonym flagging) that the graph does not have,
  and it is the very property a cautious reader would rely on to decide how much to trust
  the 2,095 AGNI-FIRE edges. The claim's *conclusion* is correct and well-argued; its
  *method* misdescribes the safeguard.

The metric `THEONYM_AMBIGUITY` is itself honest — its `method` says "every matched alias is
also a Devata **label form**", which is exactly what the code does, and its `scope_note`
correctly calls the figure "an upper bound on the deity/concept conflation, not a count of
errors". The claim built on top of it overstates it.

---

## 9. Attack 7 — orphans and dead ontology

| check | result | verdict |
|---|---|---|
| `DomainEntity` with zero edges | **0** | clean |
| `Devata` with zero edges | **0** of 214 | clean |
| `Rishi`, `Chandas`, `Epithet`, `DeityGroup`, `RitualRole`, `Tribe`, `HumanConcern`, `Condition`, `SocialRite`, `Ritual`, `Offering` orphans | **0** in every class | clean |
| `DeityAxis` nodes no deity uses | **0** of 22 | clean |
| declared `PRODUCT_LABELS` with 0 nodes | 3: `Region`, `RishiFamily`, `Theme` | **dead weight** |
| declared V2 rel types with 0 edges | 15, of which 1 documented | 1 honest placeholder, **14 dead weight** |

```cypher
MATCH (e:DomainEntity) WHERE NOT (e)--() RETURN count(*);            // => 0
MATCH (x:DeityAxis) WHERE NOT ()-[:HAS_AXIS]->(x) RETURN count(*);   // => 0
```

**Honest placeholder vs dead weight.** `MUSICALIZED_AS` is a placeholder with a written
justification in `UNPOPULATED_BY_DESIGN` — keep it. The `Theme` label is worse than dead:
`HAS_THEME` has 8 live edges and every one points at a `:Concept` node, so the label is
absent while the predicate that needs it fires. `RishiFamily` and `Region` are declared with
0 nodes and their two predicates (`BELONGS_TO_FAMILY`, `ASSOCIATED_WITH_TRIBE`) have 0
edges, so an entire declared subsystem is inert.

**N5 — the `UNSPECIFIED` axis is an honest placeholder that becomes a query trap.**

```cypher
MATCH (a:DeityAxis) RETURN a.axis, COUNT{()-[:HAS_AXIS]->(a)} AS deities ORDER BY deities DESC;
// UNSPECIFIED 101, WARRIOR 20, TERRESTRIAL 18, FIRE_MEDIUM 14, ...
MATCH (d:Devata)-[:HAS_AXIS]->() RETURN count(DISTINCT d);        // => 214  (100%)
MATCH (d:Devata) WHERE d.axes <> ['UNSPECIFIED'] RETURN count(*); // => 113  (52.8%)
```

The property view and the edge view of "how many deities are classified" differ by 101.
`is_classified: false` and `axes: ['UNSPECIFIED']` on those 101 nodes are exactly right;
the `HAS_AXIS` edge to an UNSPECIFIED node is what makes an edge-count answer wrong.

**N6 —** 57 of 71 PAIR/GROUP deities have no `COMPOSED_OF` edge, so "who are Agni and the
Maruts?" is unanswerable for 80% of composite labels. `VG:DEVATA:AGNIH-MARUTAH`,
`VG:DEVATA:AGNISOMAU`, `VG:DEVATA:DYAVAPRTHIVYAU` and 54 others have `aliases_iast: []` and
no members.

---

## 10. Attack 8 — graph explosion

**No explosion. The signature the brief describes does not recur.**

```cypher
MATCH (n) WHERE NOT n:Internal WITH n, COUNT{(n)--()} AS d
RETURN labels(n), coalesce(n.entity_key, n.canonical_key) AS k, d ORDER BY d DESC LIMIT 6;
```

| node | degree | plausible? |
|---|---|---|
| `VG:DEVATA:INDRAH` | 5,243 | yes — 2,869 attributed passages × several predicates |
| `VG:CONCEPT:AGNI-FIRE` | 4,307 | yes |
| `VG:CHANDAS:TRISTUP` | 4,195 | yes — Triṣṭubh is the commonest metre |
| `VG:DEVATA:AGNIH` | 3,684 | yes |
| `VG:CONCEPT:SOMA-DRINK` | 3,430 | yes |
| `VG:CONCEPT:DYAUS-HEAVEN` | 2,871 | yes |

**The unlabelled-`MATCH` bug is gone.** `CONCERNS` is 7 edges, all
`InterpretiveClaim -> Work` or `-> DomainEntity`, not the 39,461 that the
`MATCH (t) WHERE t.work_id = $k` pattern produced. I swept every relationship type for
counts that are exact multiples of a passage count:

- `CONTAINS` = 22,537 = exactly the `Passage` count. **Legitimate** — one parent edge per
  passage is the containment tree.
- `HAS_DEVATA` = 10,558 vs RV mantras 10,552 is a coincidence at 1.0006, not a multiple.
- No other type is within 0.1% of a multiple of 10,552 / 1,844 / 1,975 / 5,839 / 20,210 /
  22,537.

**One suspicious exact equality, investigated and cleared as truncation-free.**
`MENTIONS_LEMMA` = 9,000 and `MENTIONS_ENTITY -> :Devata` = 9,000 — two different
predicates with the same round number. I tested the cap hypothesis:

```cypher
MATCH (p:Passage) WHERE p.veda='RV'
WITH p, COUNT{(p)-[:MENTIONS_LEMMA]->()} AS ml, COUNT{(p)-[:MENTIONS_ENTITY]->(:Devata)} AS me
WHERE ml>0 OR me>0 RETURN ml = me AS equal, count(*) AS passages;
// => equal = true, passages = 6560   (for all 6,560)
```

Both layers are the *same* 9,000 rows over the *same* 6,560 passages, projected twice —
once onto `:Lemma` nodes and once onto `:Devata` nodes, from one VedaWeb Zurich morphology
pass over the 40 deity lemmas. Not a cap and not an explosion; the round number is
coincidence. The per-passage degree distribution is a clean long tail (4,872 passages with
1, down to 1 passage with 12), which a cap would not produce. **Marked as investigated and
cleared**, though the duplication means a naive "how many deity/lemma facts does the graph
hold" double-counts by 9,000.

---

## 11. Attack 10 — evidence integrity

**The private-use code point hazard is closed on every published surface.**

```cypher
// zero PUA code points in any edge property, anywhere
MATCH ()-[r]->() UNWIND keys(r) AS k WITH r,k
WHERE r[k] IS :: STRING AND r[k] =~ '.*[\\uE000-\\uF8FF].*'
RETURN type(r), k, count(*);       // => 0 rows
```

| surface | PUA code points found |
|---|---|
| `MENTIONS_ENTITY.evidence` (28,675 strings) | **0** |
| `MENTIONS_ENTITY.matched_aliases` | **0** |
| every string property on every edge in the database | **0** |
| every string property on every node | 5,143 hits, all `TextVersion.text_nfc` |

The residual is confined to `TextVersion.text_nfc` on 5,143 nodes, all of which carry
`:Internal` and are therefore outside product traversal. `ṛtasya` — the exact word the
hazard note names — appears 236 times as a published alias and is correct IAST in all 236.
**CLEAN, with a documented internal residual.**

### Do evidence quotes occur in the cited passage?

```cypher
MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e:DomainEntity) WHERE r.evidence IS NOT NULL
RETURN p.canonical_key, r.evidence;
// then, per span: is quote a substring of a Latin-script TextVersion of the cited locator,
// after full diacritic folding?
```

| | spans |
|---|---|
| quote occurs verbatim in the cited passage's stored Latin text | **24,085** |
| quote does **not** occur | **14** (0.058%) |
| cited locator has no Latin-script text to check against | 4,576 |
| evidence locator disagrees with the edge's own passage | **0** |

**99.94% of checkable evidence quotes are verifiable.** All 14 failures share one cause:
the evidence pipeline degeminates `cch` → `ch`.

```cypher
MATCH (p:Passage {canonical_key:'VG:RV:SAK:M10:S018:V012'})
      -[r:MENTIONS_ENTITY]->({entity_key:'VG:CONCEPT:PRTHIVI-EARTH'})
RETURN r.evidence;
// quote : "uchvañcamānā pṛthivī su tiṣṭhatu"
// stored: "ucchváñcamānā pr̥thivī́ sú tiṣṭhatu ..."
```

Also affected: `achā` for `acchā`, `uchocayann` for `ucchocayann`, `uchiṣṭe` for
`ucchiṣṭe`. Graded **MINOR (N4)** — 14 edges, one root cause, and the quote still locates
the right verse for a human reader.

**N3 —** the 4,576 unverifiable spans are all Sāmaveda (2,333) and Yajurveda (2,243), whose
only stored text is Devanagari while the evidence quote is IAST. The evidence is not
*wrong*; there is simply no stored surface in the same script to check it against. A reader
cannot audit 16.0% of the mention layer's evidence without re-transliterating.

---

## 12. False positive rate by relationship type

"False positive" is defined per predicate as the share of edges that assert something a
Vedic scholar would call wrong, given that predicate's own declared meaning. Estimates
carry the method that produced them; where no method was available I say so rather than
guess.

| relationship type | edges | est. FP rate | basis | confidence |
|---|---|---|---|---|
| `CONTAINS` | 22,537 | **~0%** | structural, one parent per passage, exact count match | high |
| `HAS_TEXT_VERSION` / `HAS_TRANSLATION` | 61,559 | **~0%** | provenance plumbing, `content_sha256` per text | high |
| `HAS_CHANDAS` | 10,523 | **~0% as stated** | metre is checkable by syllable count; 40.4% `PER_PASSAGE` | high |
| `HAS_DEVATA` | 10,558 | **~0% as stated / 78.9% over-precise** | source-explicit about the sūkta; 8,329 are per-mantra projections. Not wrong, wrongly scoped | high |
| `HAS_RISHI` | 10,565 | **~0% as stated / 95.5% over-precise** | same, worse | high |
| `MENTIONS_LEMMA` | 9,000 | **~1%** | VedaWeb Zurich morphological annotation, human-curated upstream | medium |
| `MENTIONS_ENTITY` → `:Devata` | 9,000 | **~1%** | same source as above | medium |
| `MENTIONS_ENTITY` → `:DomainEntity` | 28,675 | **~2% on P(token)** | 0.058% evidence-verification failure; gloss screen ≥93% on 42 of 45 top aliases | high |
| " | " | **~13% on P(referent)** | Σ(vol × error) over the top-45 alias table = 2,451 of 19,204 top-45 alias-hits; dominated by `agne`, `soma`, `agnir` | medium |
| " | *restricted to AGNI-FIRE* | **80.9%** | translation adjudication, 1,934 rows | high |
| " | *restricted to SOMA-DRINK* | **25.6%–61.3%** | lower bound = vocative-only subset; upper = translation screen, unreliable for Soma | low |
| `ABOUT_CONCEPT` (`sanskrit-token`/`sandhi`) | 13,281 | **~5%** | same matcher family as `MENTIONS_ENTITY`, weaker alias curation | medium |
| `ABOUT_CONCEPT` (`english+sanskrit`) | 13,015 | **~8%** | Sanskrit corroboration present | low |
| `ABOUT_CONCEPT` (`english` only) | 21,246 | **not estimated — see below** | | — |
| `REUSES_TEXT_FROM` / `EXACT_PARALLEL_OF` | 2,690 | **~5%** | `SANDHI_INSENSITIVE` surface, self-declared as the weakest level | low |
| `NEAR_PARALLEL_OF` | 3,049 | **not estimated** | requires verse-pair review not attempted here | — |
| `HAS_AXIS` | 289 | **~0% as stated** | L4/TIER_D, per-deity `curation_note`, 101 honest `UNSPECIFIED` | high |
| `COMPOSED_OF` | 28 | **~0%** | 14 pairs, all checked, all correct (`MITRAVARUNAU` → Mitra + Varuṇa) | high |
| `SUPPORTED_BY` / `SUPPORTED_BY_STATISTIC` / `CONCERNS` / `CONTRADICTS` | 22 | **0%** | all 22 targets resolve; all endpoints legal | high |
| `MEASURES` | 76 | **0% on content, 100% on grade** | values verified exact; but `TIER_B` under `L4` (M7) | high |
| `DESCRIBES` / `INVOKES` / `REQUESTS` / `PRAISES` / etc. (L3) | 731 | **not estimated** | V3.2 regex pilots, sealed heuristics; graded TIER_D so a reader is warned | — |
| `ADDRESSES_CONCERN` / `TREATS` / `PROTECTS_FROM` / `USED_FOR_RITE` | 584 | **not estimated** | landed mid-audit; 617 of them lack `attribution_precision` | — |

**Why `ABOUT_CONCEPT (english)` gets no FP rate.** The question is ill-posed for these
21,246 edges. Judged as "does Griffith's English contain a word glossing this concept",
their precision is near 1.0 by construction. Judged as "does the Sanskrit passage mention
this concept", they are untested and untestable from within the graph, because the surface
they matched is not the corpus. That is the finding (C3), and inventing a number for it
would obscure it. The graph's own TIER_D claim `CONCEPT-LAYER-LEANS-ON-TRANSLATION` reaches
the same conclusion and states its falsifier.

---

## 13. Attacks the graph SURVIVED

Attacked deliberately, found sound. This list is as load-bearing as the findings.

1. **Rudra carries no Śiva identification anywhere.** Zero hits for `śiva|shiva|siva`
   across every string property of every node *and* every edge in the database, plus an
   explicit `curation_note` explaining the refusal and recording that *tryambaka* was
   probed and returns zero hits. Best-handled conflation in the graph.
2. **Savitṛ and Sūrya are genuinely separate.** 0 shared `HAS_DEVATA` passages, no edge
   between them, disjoint alias sets, distinct axis sets.
3. **Mitra / Varuṇa / Mitrāvaruṇau are genuinely separate**, with `structure: PAIR`,
   `COMPOSED_OF` to both members, and 0 passages carrying both the pair and a member label.
4. **The interpretive claim layer is airtight structurally.** All 6 claims `TIER_D`; none
   `CANDIDATE`-and-asserted; nothing outside the claim layer points into a claim; no claim
   carries a domain label; the `CONTRADICTS` pair is symmetric with neither side settled;
   all 6 `SUPPORTED_BY_STATISTIC` and all 7 `SUPPORTED_BY` targets resolve.
5. **Four of six claim number-sets verify exactly** against the live graph, to the digit:
   the three attribution-precision splits, the two inherited shares, the SV reuse figures
   (1,662/1,844 = 90.13%), the 21,246/47,542 English-only count, the 96.1% V1 coverage, and
   the `THEONYM_AMBIGUITY` metric's own 1,092/28,675.
6. **No private-use code point reaches any published surface.** 0 in 28,675 evidence
   strings, 0 in `matched_aliases`, 0 across every edge property in the database. The named
   `ṛtasya` hazard is correct IAST in all 236 occurrences.
7. **Evidence quotes are real.** 24,085 of 24,099 checkable quotes (99.94%) occur verbatim
   in the cited passage's stored text after diacritic folding, and 0 evidence locators
   disagree with their edge's passage.
8. **No graph explosion, and the specific bug pattern is gone.** `CONCERNS` = 7, not
   39,461. Max non-internal degree is Indra at 5,243, which is proportionate. No
   relationship count is a suspicious multiple of a passage count except `CONTAINS`, which
   legitimately is one.
9. **The 9,000/9,000 equality is not a cap.** Tested and cleared: the two layers are the
   same rows projected onto two node types, with a clean long-tail degree distribution.
10. **No orphans anywhere in the domain layer.** 0 orphaned `DomainEntity`, `Devata`,
    `Rishi`, `Chandas`, `Epithet`, `DeityGroup`, `RitualRole`, `Tribe`, `HumanConcern`,
    `Condition`, `SocialRite`, `Ritual`, `Offering`; 0 unused `DeityAxis` nodes.
11. **`knowledge_layer`, `quality_tier` and `grade_basis` are present on 100% of 242,147
    edges.** Only `attribution_precision` has gaps, at 0.25%.
12. **The `UNSPECIFIED` axis and `is_classified: false` are honest.** 101 deities are
    explicitly recorded as unclassified rather than given an invented axis, and the
    `curation_note` on each explains what was considered and refused. The scorecard counts
    them as unclassified. This is the right behaviour; only the `HAS_AXIS` edge to the
    placeholder creates a counting trap.
13. **Griffith-abridgement and gloss-list artefacts, not data defects.** The four aliases
    with the worst automated gloss-miss rates (`brahmaṇā` 38.6%, `brahma` 36.4%, `ṛtasya`
    17.8%, `sūryasya` 13.8%) were all hand-read and all four are gloss-list gaps or
    Griffith "etc." abridgements, not mention errors. `divo` has a measured 0% homograph
    rate. Reported so the numbers are not mistaken for findings.

---

## 14. Bottom line

**There are 3 CRITICAL findings. The V2 acceptance gate requires zero, so the gate is NOT
met.**

The three are not equally hard to fix.

**C1 is a two-line fix with a large blast radius.** Build the theonym set from
`Devata.aliases_iast` (and their sandhi folds) rather than from `Devata.label_iast`, at
`scripts/build_domain_v2.py:114`. That converts at least 2,454 unflagged edges — and
specifically all 1,052 Agni-vocative edges — into flagged ones, and brings the graph into
line with what its own docstring, its own metric method and its own AGNI claim already say
it does. Nothing else in the model has to change.

**C3 is a grading fix, not a data fix.** The 21,246 English-only `ABOUT_CONCEPT` edges are
correctly evidenced at the span level (`surface: "translation_en"`) and correctly described
in a TIER_D claim. What is wrong is that they are graded `L2_DETERMINISTIC_DERIVED` /
`TIER_B`, identical to Sanskrit-grounded edges. They need their own layer or tier so that a
tier filter separates them. The ontology's own principle — "Tier is how a claim was
reached, never how confident it sounds" — is the argument for the change.

**C2 is the expensive one, and it is a coverage fact rather than a bug.** The Atharvaveda,
Sāmaveda and Yajurveda have no attribution layer and no deity mention layer, so every deity
question answers RV-only. There is no defect in the edges that exist. The defect is that
nothing at the point of use says so: `Work` nodes carry no coverage property, `HAS_DEVATA`
edges carry no coverage statement, and the one place the scope *is* disclosed
(`profile_attribution_scope: ['RV']`) exists on 25 of 214 deities. Until a deity layer
covers the other three Vedas, a coverage property on `Work` and on every `Devata` node
would convert a confidently wrong answer into an honestly incomplete one — which is the
distinction this whole model is built to preserve.

The MAJOR findings cluster around one theme worth naming: **the V2 model's contracts are
written more completely than they are enforced.** 14,944 edges run on undeclared predicates
while 14 declared replacements sit at zero; the `:DomainEntity` marker is absent from the
214 nodes that most need it; `is_composite` is `false` on all 214 Devatā nodes including
the 71 that are demonstrably composite; and the signature table was edited during this
audit to match the data rather than the data corrected to match the table. Every one of
those is cheap to fix and each one currently makes the ontology a description rather than a
constraint.
