# KNOWLEDGE_MODEL_V3_BASELINE_AUDIT

**Agent B — independent baseline evaluator.** I did not author Knowledge Model V2. This is a
forensic measurement of the graph as it stands at commit `92f2539`, frozen as
`KNOWLEDGE_MODEL_V3_BASELINE`. I changed no code, no registry, no data file and no node or
edge in the database; every statement below is either a query result printed in-line or a
file I read. Where a number is inherited from `BASELINE_FACTS.md` or from V2's own reporting
I say so, and I say whether my own re-measurement agreed.

Nothing here recommends implementation work. Where I found a defect I say what it costs a
researcher and stop there.

**Runner used for every Cypher block below:**

```
.venv/Scripts/python.exe scratchpad/cy.py -f <file.cypher>          # bolt://localhost:7687
```

**Headline.** I re-verified 26 published numbers and reproduced 20 of them exactly. Six I
could not reproduce, two of which invert the conclusion drawn from them. Five substantial
weaknesses appear in no prior report. The disagreement ledger is Appendix A.

---

## 1. Frozen identity

| field | value | how measured |
|---|---|---|
| git commit | `92f2539f90b320541b44e4db7efbc2dfdc3f6590` | `git rev-parse HEAD` |
| commit subject | `feat: Enhance concept loading and validation in Knowledge Model V2` | `git log -1 --format=%s` |
| commit date | 2026-09-09 13:37:05 +0530 | `git log -1 --format=%ci` |
| branch | `semantic-pilot-v1` | `git rev-parse --abbrev-ref HEAD` |
| working tree | clean (0 modified, 0 untracked) | `git status --porcelain` returned no output |
| audit date | 2026-09-09 | `date` |
| database | Neo4j Kernel 5.26.30, community edition | `CALL dbms.components()` |

`BASELINE_FACTS.md` records commit `92f2539` and a clean tree. Both re-verified. Note that
this session's opening git snapshot listed `bb27f3c` as HEAD with a large dirty tree; that
work was committed as `92f2539` before this audit began, so the baseline is a committed
state and not a working tree.

### Size

```cypher
MATCH (n) RETURN count(n) AS nodes;;
MATCH ()-[r]->() RETURN count(r) AS rels;;
CALL db.labels() YIELD label RETURN count(label);;
CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType)
```

| measure | measured | `BASELINE_FACTS` | agree? |
|---|---|---|---|
| nodes | **100,780** | 100,780 | yes |
| relationships | **242,147** | 242,147 | yes |
| node label *tokens* | **44** | 42 | **no** |
| relationship type *tokens* | **50** | 49 | **no** |

Both disagreements are real and are the first finding. `db.labels()` and
`db.relationshipTypes()` return the token store, which retains tokens for labels and types
that hold nothing. Three such ghost tokens exist:

```cypher
CALL db.labels() YIELD label
CALL { WITH label MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c }
RETURN label, c ORDER BY c DESC, label
```

| ghost token | kind | rows |
|---|---|---|
| `RishiFamily` | node label | 0 |
| `SourceArtifact` | node label | 0 |
| `SHARES_FORMULA_WITH` | relationship type | 0 |

42 labels and 49 relationship types are *populated*, which is what `BASELINE_FACTS` counted.
But the schema surface an API or a UI will enumerate is 44 and 50, so a client that builds a
label filter from `db.labels()` offers the user two labels that can never return a row.

### Node label inventory (populated)

`Internal` and `DomainEntity` are marker labels carried in addition to a type label, and
`Mantra`, `Concept`, `Place`, `Plant`, `Substance` and `Object` are super/sub-label pairs, so
the column sums to more than 100,780 by design.

| label | nodes | label | nodes | label | nodes |
|---|---|---|---|---|---|
| Internal | 62,483 | DeityAxis | 22 | Metal | 5 |
| TextVersion | 44,276 | Object | 19 | RitualRole | 5 |
| Passage | 22,537 | Epithet | 13 | Tribe | 5 |
| Mantra | 20,210 | NaturalPhenomenon | 13 | CosmicEntity | 4 |
| Translation | 17,283 | Plant | 13 | HumanConcern | 4 |
| Lemma | 10,031 | Animal | 12 | Ritual | 4 |
| Formula | 4,825 | Condition | 12 | SocialRite | 4 |
| QAIssue | 915 | PhilosophicalConcept | 11 | Work | 4 |
| Rishi | 367 | Place | 10 | Quality | 3 |
| Devata | 214 | Substance | 10 | State | 3 |
| Concept | 163 | Source | 9 | Weapon | 3 |
| DomainEntity | 163 | River | 7 | DeityGroup | 2 |
| DerivedMetric | 79 | InterpretiveClaim | 6 | Offering | 2 |
| Chandas | 34 | Action | 5 | Crop | 5 |

All 42 values match `BASELINE_FACTS` exactly; I re-verified every one in a single query.

### Relationship type inventory (populated)

| type | edges | type | edges | type | edges |
|---|---|---|---|---|---|
| ABOUT_CONCEPT | 47,542 | HAS_AXIS | 289 | HAS_EPITHET | 13 |
| HAS_TEXT_VERSION | 44,276 | DESCRIBES | 280 | MEMBER_OF | 13 |
| MENTIONS_ENTITY | 37,675 | INVOKES | 222 | INVOLVES_RITUAL | 11 |
| USES_FORMULA | 22,686 | ADDRESSES_CONCERN | 219 | USES_OBJECT | 11 |
| CONTAINS | 22,537 | PROTECTS_FROM | 182 | CONTRASTS_WITH | 8 |
| HAS_TRANSLATION | 17,283 | DEVATA_ASSOCIATED_WITH | 140 | HAS_THEME | 8 |
| HAS_RISHI | 10,565 | REQUESTS | 109 | CONCERNS | 7 |
| HAS_DEVATA | 10,558 | USED_FOR_RITE | 96 | SUPPORTED_BY | 7 |
| HAS_CHANDAS | 10,523 | TREATS | 87 | PERFORMED_BY | 6 |
| MENTIONS_LEMMA | 9,000 | MEASURES | 76 | SUPPORTED_BY_STATISTIC | 6 |
| NEAR_PARALLEL_OF | 3,049 | PARALLEL_TO | 69 | INVOKES_DEVATA | 5 |
| REUSES_TEXT_FROM | 1,684 | BROADER_THAN | 57 | REFERS_TO_NATURAL_PHENOMENON | 5 |
| EXACT_PARALLEL_OF | 1,006 | PRAISES | 38 | PERFORMED_FOR | 4 |
| HAS_QA_ISSUE | 915 | DESCRIBES_ACTION | 35 | USES_SUBSTANCE | 4 |
| VARIANT_OF | 788 | COMPOSED_OF | 28 | INVOLVES_SUBSTANCE | 3 |
| | | INVOLVES_OFFERING | 14 | REFERS_TO_PLACE | 3 |
| | | | | USES_OFFERING | 3 |
| | | | | CONTRADICTS | 2 |

All 49 match `BASELINE_FACTS` exactly.

---

## 2. Grading axes

### Quality tier, knowledge layer, state

```cypher
MATCH ()-[r]->() RETURN coalesce(r.quality_tier,'<null>') AS quality_tier, count(*) ORDER BY 2 DESC;;
MATCH ()-[r]->() RETURN coalesce(r.knowledge_layer,'<null>') AS knowledge_layer, count(*) ORDER BY 2 DESC;;
MATCH ()-[r]->() RETURN coalesce(r.state,'<null>') AS state, count(*) ORDER BY 2 DESC
```

| quality_tier | edges | knowledge_layer | edges | state | edges |
|---|---|---|---|---|---|
| TIER_B | 149,206 | L2_DETERMINISTIC_DERIVED | 149,206 | *(null)* | **136,118** |
| TIER_A | 91,163 | L1_SOURCE_EXPLICIT | 91,163 | ACCEPTED | 105,293 |
| TIER_D | 1,778 | L4_INTERPRETIVE_CLAIM | 1,042 | CANDIDATE | 736 |
| TIER_C | **0** | L3_LLM_EXTRACTED | 736 | | |
| *(null)* | 0 | *(null)* | 0 | | |

Tier coverage is genuinely 100%: `MATCH ()-[r]->() WHERE r.quality_tier IS NULL` returns 0
rows. V2's claim of complete tier coverage is **reproduced**. `state` is null on 136,118
edges (56.2%), so a state filter silently excludes the majority of the graph.

**But the tier axis violates the ontology's own mapping.** `ontology.TIER_BY_LAYER` maps
`L3_LLM_EXTRACTED` to `TIER_C`. The cross-tab says otherwise:

```cypher
MATCH ()-[r]->() RETURN r.knowledge_layer AS layer, r.quality_tier AS tier, count(*) AS n ORDER BY n DESC
```

| layer | tier | edges | contract expects |
|---|---|---|---|
| L2_DETERMINISTIC_DERIVED | TIER_B | 149,206 | TIER_B — agrees |
| L1_SOURCE_EXPLICIT | TIER_A | 91,163 | TIER_A — agrees |
| L4_INTERPRETIVE_CLAIM | TIER_D | 1,042 | TIER_D — agrees |
| **L3_LLM_EXTRACTED** | **TIER_D** | **736** | **TIER_C — violated** |

So `TIER_C = 0` does not mean what `BASELINE_FACTS` line 75 says it means ("the graph
contains no accepted model-derived knowledge"). The graph contains 736 model-derived edges;
they are graded one tier below the tier the contract assigns them. All 736 are
`state = CANDIDATE`, spread over 12 predicates (`DESCRIBES` 280, `INVOKES` 222, `REQUESTS`
109, `PRAISES` 38, `DESCRIBES_ACTION` 35, `INVOLVES_OFFERING` 14, `INVOLVES_RITUAL` 11,
`HAS_THEME` 8, `CONTRASTS_WITH` 8, `REFERS_TO_NATURAL_PHENOMENON` 5, `REFERS_TO_PLACE` 3,
`INVOLVES_SUBSTANCE` 3).

The cost to a researcher: `TIER_D` is the reader-facing grade for "interpretive". Filtering
out TIER_D to get textual claims drops 736 model extractions and 1,042 genuine interpretive
edges together, with nothing on the edge distinguishing the two kinds.

**Second tier defect: 403 edges are TIER_D because grading failed, not because they are
interpretive.**

```cypher
MATCH ()-[r]->() WHERE r.grade_basis STARTS WITH 'ungraded'
RETURN type(r) AS t, r.knowledge_layer AS layer, r.quality_tier AS tier, count(*) AS n ORDER BY n DESC
```

| type | layer | tier | edges | `grade_basis` |
|---|---|---|---|---|
| EXACT_PARALLEL_OF | L4_INTERPRETIVE_CLAIM | TIER_D | 256 | `ungraded: EXACT_PARALLEL_OF records no recognised provenance vocabulary` |
| PARALLEL_TO | L4_INTERPRETIVE_CLAIM | TIER_D | 69 | same shape |
| BROADER_THAN | L4_INTERPRETIVE_CLAIM | TIER_D | 39 | same shape |
| DEVATA_ASSOCIATED_WITH | L4_INTERPRETIVE_CLAIM | TIER_D | 39 | same shape |

Inspecting one of the 256:

```cypher
MATCH ()-[r:EXACT_PARALLEL_OF]->() WITH r LIMIT 1 RETURN properties(r)
```

```
provenance_class: "DETERMINISTIC_DERIVED", similarity: 1.0, strongest_method: "SOURCE_EXACT",
methods: ["SOURCE_EXACT","NFC_EXACT","ACCENTLESS_EXACT","TOKEN_EXACT","LEMMA_SEQUENCE_EXACT"],
knowledge_layer: "L4_INTERPRETIVE_CLAIM", quality_tier: "TIER_D"
```

The edge records `provenance_class = DETERMINISTIC_DERIVED`, similarity 1.0 and five
concurring exact-match methods, and is graded *interpretive*, because
`KNOWLEDGE_TIER_BY_PROVENANCE` contains only `SOURCE_EXPLICIT` and `SOURCE_DERIVED_SCOPE`.
The other 750 `EXACT_PARALLEL_OF` edges carry the same fact on a *different property*
(`trust = DETERMINISTIC_DERIVED`) and are graded TIER_B/L2. Split by Veda pair:

```cypher
MATCH (a:Passage)-[r:EXACT_PARALLEL_OF]->(b:Passage)
RETURN r.quality_tier, r.knowledge_layer, a.veda, b.veda, count(*) ORDER BY 5 DESC
```

| tier / layer | a.veda to b.veda | edges |
|---|---|---|
| TIER_B / L2 | AV to RV | 551 |
| **TIER_D / L4** | **RV to RV** | **256** |
| TIER_B / L2 | RV to SV | 89 |
| TIER_B / L2 | SV to YV | 70 |
| TIER_B / L2 | RV to YV | 24 |
| TIER_B / L2 | AV to SV | 9 |
| TIER_B / L2 | AV to YV | 7 |

The 256 mis-graded edges are exactly the intra-Rigvedic exact parallels. A tier-filtered
query for reliable textual parallels returns every cross-Veda parallel and none of the
Rigveda-internal ones.

**Third tier defect: identical derivations get different tiers per predicate.** Four
predicates in the Atharvavedic concern layer all carry a `derived_from_mention` pointer into
the same lexical mention layer:

```cypher
MATCH ()-[r:ADDRESSES_CONCERN|PROTECTS_FROM|TREATS|USED_FOR_RITE]->()
RETURN type(r), r.quality_tier, r.knowledge_layer, r.evidence_basis, count(*) ORDER BY 1
```

| predicate | tier | layer | evidence_basis | edges |
|---|---|---|---|---|
| ADDRESSES_CONCERN | TIER_B | L2_DETERMINISTIC_DERIVED | SANSKRIT | 219 |
| USED_FOR_RITE | TIER_B | L2_DETERMINISTIC_DERIVED | SANSKRIT | 96 |
| **PROTECTS_FROM** | **TIER_D** | **L4_INTERPRETIVE_CLAIM** | **STRUCTURAL** | 182 |
| **TREATS** | **TIER_D** | **L4_INTERPRETIVE_CLAIM** | **STRUCTURAL** | 87 |

`grade_basis` on all four reads `"<PREDICATE>: tier follows from the predicate (V2 domain
layer)"` — the tier is a per-predicate constant, not a function of how the claim was
reached. That contradicts the ontology's own docstring: *"Tier is how a claim was reached,
never how confident it sounds."* 269 edges are graded interpretive and 315 deterministic on
the strength of the predicate name alone, from one derivation.

### `evidence_basis` — the 61,861 UNSPECIFIED edges are not plumbing

`BASELINE_FACTS` line 50 says: *"UNSPECIFIED = 61,861 is itself a finding: mostly
HAS_TEXT_VERSION/HAS_TRANSLATION plumbing."* **That is false, and measurably so.**

```cypher
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED'
  AND type(r) IN ['HAS_TEXT_VERSION','HAS_TRANSLATION'] RETURN count(*)
```

Result: **0**. All 44,276 `HAS_TEXT_VERSION` and all 17,283 `HAS_TRANSLATION` edges carry
`evidence_basis = STRUCTURAL`. Not one of the 61,861 is plumbing.

| evidence_basis | edges |
|---|---|
| STRUCTURAL | 85,650 |
| UNSPECIFIED | 61,861 |
| SANSKRIT | 60,375 |
| TRANSLATION | 21,246 |
| MIXED | 13,015 |
| *(null)* | 0 |

All five totals match `BASELINE_FACTS`. The per-type breakdown, which nobody published, is
where the finding actually is:

```cypher
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED'
RETURN type(r) AS t, r.quality_tier AS tier, count(*) AS n ORDER BY n DESC
```

| family | relationship types | edges | share of 61,861 |
|---|---|---|---|
| Anukramaṇī attribution | HAS_RISHI 10,565 / HAS_DEVATA 10,558 / HAS_CHANDAS 10,523 | 31,646 | 51.2% |
| formula reuse | USES_FORMULA | 22,686 | 36.7% |
| textual parallels | NEAR_PARALLEL_OF 3,049 / REUSES_TEXT_FROM 1,684 / EXACT_PARALLEL_OF 1,006 / VARIANT_OF 788 / PARALLEL_TO 69 | 6,596 | 10.7% |
| model semantics (L3) | 12 predicates, see above | 736 | 1.2% |
| deity association | DEVATA_ASSOCIATED_WITH 140 / BROADER_THAN 57 | 197 | 0.3% |
| **total** | | **61,861** | **100.0%** |

Every one of the 61,861 is a product knowledge edge. **7,048 of them are TIER_A** — the top
grade, "a source states it" — with no statement of what evidence supports it:

| TIER_A edges with `evidence_basis = UNSPECIFIED` | edges |
|---|---|
| HAS_CHANDAS | 4,247 |
| HAS_DEVATA | 2,229 |
| HAS_RISHI | 472 |
| DEVATA_ASSOCIATED_WITH | 101 |
| BROADER_THAN | 18 |

And the 736 L3 edges declare `UNSPECIFIED` while *carrying a populated evidence payload*:

```cypher
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED' AND r.knowledge_layer='L3_LLM_EXTRACTED'
RETURN count(*) AS l3_unspecified, count(r.evidence) AS with_evidence_payload, count(r.run_id) AS with_run_id
```

Result: `736 / 736 / 736`. Every one has an evidence quote, a locator and a run id, and
declares its evidence basis unspecified. `evidence_basis` is therefore not a claim about
whether evidence exists; on 61,861 edges it is a claim about nothing.

### `attribution_precision` per predicate

```cypher
MATCH ()-[r]->() WITH type(r) AS t, coalesce(r.attribution_precision,'<null>') AS ap, count(*) AS n
RETURN t, ap, n ORDER BY t, ap
```

Totals: PER_PASSAGE 217,449, CONTAINER_INHERITED 24,698, null 0. Only three predicates carry
any inheritance; the other 46 are 100% PER_PASSAGE:

| predicate | PER_PASSAGE | CONTAINER_INHERITED | inherited share |
|---|---|---|---|
| HAS_DEVATA | 2,229 | 8,329 | **78.9%** |
| HAS_RISHI | 472 | 10,093 | **95.5%** |
| HAS_CHANDAS | 4,247 | 6,276 | **59.6%** |
| all other 46 predicates | 210,501 | 0 | 0% |

Matches `BASELINE_FACTS` on all six numbers.

The axis is however applied where it has no meaning. `HAS_TEXT_VERSION` (44,276),
`HAS_TRANSLATION` (17,283), `CONTAINS` (22,537) and `HAS_QA_ISSUE` (915) all carry
`attribution_precision = PER_PASSAGE` — 84,916 edges, 35.1% of the graph — on which "did the
source say this about this passage or about its container" is not a question. The 78.9% /
95.5% / 59.6% rates are the real content of this axis, and they dilute to a graph-wide 10.2%
when the plumbing is counted in.

### `grade_basis` vocabulary

32 distinct values. Three cover 97.9% of the graph:

| grade_basis | edges |
|---|---|
| `trust=DETERMINISTIC_DERIVED` | 105,174 |
| `corpus structure as printed by the edition` | 84,096 |
| `provenance_class=SOURCE_DERIVED_SCOPE, scope_origin=SUKTA_WIDE` | 24,698 |

Of the remaining 29, nineteen have the form `"<PREDICATE>: tier follows from the predicate
(V2 domain layer)"` (1,058 edges) and four have the form `"ungraded: <PREDICATE> records no
recognised provenance vocabulary"` (403 edges). 1,461 edges are graded either by predicate
name or by grader failure.

---

## 3. Per-Veda coverage across every measurable ontology dimension

```cypher
MATCH (p:Passage) RETURN p.veda, count(*) AS passages, count(CASE WHEN p:Mantra THEN 1 END) AS mantras;;
MATCH (p:Passage)-[r]->() WITH p.veda AS veda, type(r) AS t, count(*) AS edges, count(DISTINCT p) AS passages_with
RETURN veda, t, edges, passages_with ORDER BY t, veda;;
MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t)
RETURN p.veda, t.script, t.text_role, t.accented, count(*) ORDER BY 1, 5 DESC
```

Corpus shape:

| | RV | AV | SV | YV | total |
|---|---|---|---|---|---|
| work_id | VG:WORK:RV:SAK | VG:WORK:AV:SAU | VG:WORK:SV:KAU | VG:WORK:YV:VSM | 4 |
| passages | 11,590 | 6,590 | 2,342 | 2,015 | 22,537 |
| of which MANTRA | 10,552 | 5,839 | 1,844 | 1,975 | 20,210 |
| container passages | 1,038 | 751 | 498 | 40 | 2,327 |
| text versions | 21,104 | 17,517 | 1,844 | 3,811 | 44,276 |
| text script | **Latin** | **Latin** | **Devanagari** | **Devanagari** | — |
| mantras with Latin text | 10,552 (100%) | 5,839 (100%) | **0** | **0** | 16,391 |
| translations | 10,502 Griffith | 4,878 Whitney | **0** | 1,903 Griffith | 17,283 |
| mantras untranslated | 50 | 961 | **1,844 (100%)** | 72 | 2,927 |

Knowledge dimensions. Two figures per cell: *edges* / *distinct passages carrying at least
one*.

| dimension | RV | AV | SV | YV |
|---|---|---|---|---|
| HAS_DEVATA | 10,558 / 10,552 | **0** | **0** | **0** |
| HAS_RISHI | 10,565 / 10,534 | **0** | **0** | **0** |
| HAS_CHANDAS | 10,523 / 10,518 | **0** | **0** | **0** |
| MENTIONS_LEMMA | 9,000 / 6,560 | **0** | **0** | **0** |
| MENTIONS_ENTITY (all) | 25,369 / 9,434 | 7,730 / 4,167 | 2,333 / 1,358 | 2,243 / 1,320 |
| — of which to `:Devata` | 9,000 | **0** | **0** | **0** |
| — of which to `:DomainEntity` | 16,369 | 7,730 | 2,333 | 2,243 |
| ABOUT_CONCEPT | 29,713 / 10,144 | 10,715 / 4,775 | 2,200 / 1,322 | 4,914 / 1,821 |
| — English-only evidence share | 14,260 (48.0%) | 4,150 (38.7%) | **0** | 2,836 (57.7%) |
| USES_FORMULA | 9,729 / 5,103 | 6,844 / 2,946 | 3,036 / 1,311 | 3,077 / 1,214 |
| EXACT_PARALLEL_OF (outbound) | 369 / 207 | 567 / 535 | 70 / 63 | 0 |
| NEAR_PARALLEL_OF (outbound) | 1,653 / 1,359 | 1,240 / 897 | 156 / 137 | 0 |
| REUSES_TEXT_FROM (outbound) | 0 | 0 | 1,684 / 1,662 | 0 |
| VARIANT_OF (outbound) | 580 / 475 | 195 / 136 | 13 / 13 | 0 |
| PARALLEL_TO (outbound) | 69 / 29 | 0 | 0 | 0 |
| ADDRESSES_CONCERN | 48 / 48 | 148 / 146 | 3 / 3 | 20 / 20 |
| PROTECTS_FROM | 17 / 17 | 164 / 163 | 1 / 1 | 0 |
| TREATS | 2 / 2 | 84 / 82 | 0 | 1 / 1 |
| USED_FOR_RITE | 18 / 18 | 75 / 72 | 0 | 3 / 3 |
| INVOLVES_RITUAL | 0 | 6 / 6 | 0 | 5 / 5 |
| DESCRIBES_ACTION | **0** | 15 / 15 | 0 | 20 / 20 |
| L3 semantic assertions, all 12 predicates | **0** | 321 / 157 | **0** | 415 / 207 |
| passages with **zero** knowledge edges | 1,038 (9.0%) | 1,220 (18.5%) | 531 (22.7%) | 125 (6.2%) |

Query for the last row (any edge other than `CONTAINS`, `HAS_TEXT_VERSION`,
`HAS_TRANSLATION`, `HAS_QA_ISSUE`):

```cypher
MATCH (p:Passage) OPTIONAL MATCH (p)-[r]->()
WHERE NOT type(r) IN ['CONTAINS','HAS_TEXT_VERSION','HAS_TRANSLATION','HAS_QA_ISSUE']
WITH p, count(r) AS knowledge_deg
RETURN p.veda, count(p), sum(CASE WHEN knowledge_deg=0 THEN 1 ELSE 0 END) ORDER BY 1
```

2,914 passages (12.9% of the corpus) carry no knowledge edge of any kind. They have text and
in three of four corpora a translation, and nothing else.

Three structural facts fall out of this table that the per-Veda table in `BASELINE_FACTS`
does not show:

1. **The Sāmaveda has no translation at all.** 1,844 mantras, 0 `HAS_TRANSLATION`. It is also
   the only corpus with one text version per mantra (1,844/1,844) where RV has 2.0, AV 3.0
   and YV 1.93.
2. **The Sāmaveda and Yajurveda store Devanagari only.** Their concept layer is therefore
   Sanskrit-token-matched while RV/AV/YV's is 38–58% English-matched (§6.2), and their
   evidence quotes, written in IAST, cannot be checked against anything stored (§6.5).
3. **The L3 semantic layer covers AV and YV only, with zero Rigveda.** Detail in §6.4.

Dimensions with no per-Veda row because they are corpus-independent or empty: `Ritual`
(4 nodes, 33 edges across `USES_OBJECT` 11, `PERFORMED_BY` 6, `INVOKES_DEVATA` 5,
`USES_SUBSTANCE` 4, `PERFORMED_FOR` 4, `USES_OFFERING` 3 — V2's "33 edges over 4 rites"
**reproduced exactly**); `Action` (5 nodes, `PERFORMS_ACTION` and `HAS_STEP` both empty);
`RishiFamily`, `Region`, `Theme` (0 nodes each).

---

## 4. Current query timings

All 48 entries of `vedagraph.domain.queries.QUERIES` were imported and executed against the
live graph with their own default `parameters`, three repetitions each. Harness:
`scratchpad/agentB/time_queries.py`, which does

```python
from vedagraph.domain.queries import QUERIES
for q in QUERIES:
    for _ in range(3):
        t0 = time.perf_counter(); rows = list(session.run(q.cypher, **q.parameters))
```

`QUERIES` has 48 entries, 48 distinct names. **All 48 executed with zero errors.**
Per-query timing below is the median of three runs ("warm"); the first run is reported
separately as "cold".

| statistic | warm (median of 3) | cold (first run) |
|---|---|---|
| median across 48 queries | **6.6 ms** | 8.4 ms |
| mean across 48 queries | **200.3 ms** | 210.8 ms |
| p95 across 48 queries | **87.3 ms** | 128.9 ms |
| minimum | 2.1 ms (`deity_epithets`, `varuna_profile`) | 2.3 ms |
| maximum | **8,737.7 ms** | 8,737.7 ms |
| total wall time, all 48 | **9,612.1 ms** | — |

The mean is 30x the median because one query dominates. Slowest three:

| rank | query | warm median | cold | rows | share of total |
|---|---|---|---|---|---|
| 1 | `conceptually_similar_not_reused` | **8,737.7 ms** | 8,737.7 ms | 25 | **90.9%** |
| 2 | `textual_versus_interpretive` | 266.9 ms | 365.2 ms | 4 | 2.8% |
| 3 | `concepts_bridging_vedas` | 87.3 ms | 128.9 ms | 30 | 0.9% |

Next five, for shape: `attribution_precision_audit` 51.6 ms, `unlabelled_product_nodes`
46.5 ms, `entity_distribution_by_veda` 44.4 ms, `theonym_ambiguous_mentions` 42.7 ms,
`product_graph_census` 27.5 ms. The remaining 40 queries all run under 22 ms.

`conceptually_similar_not_reused` is the only query in the set that traverses
`(:Passage)-[:MENTIONS_ENTITY]->(:DomainEntity)<-[:MENTIONS_ENTITY]-(:Passage)`. With 28,675
`MENTIONS_ENTITY` edges to 163 shared entities and a top entity at 2,095 mentions, that
pattern materialises on the order of tens of millions of passage pairs before the
`shared >= 3` filter, and no warming helps: cold and warm are identical to the tenth of a
millisecond. It is a single-query problem, not a graph-wide one.

**Four queries return zero rows.** Three are pass-condition checks, one is a real gap:

| query | rows | reading |
|---|---|---|
| `internal_leakage_check` | 0 | **pass** — no internal label reaches product traversal |
| `unlabelled_product_nodes` | 0 | **pass** — UNKNOWN_LABEL_RATE is 0 on `display_label` |
| `orphan_domain_entities` | 0 | **pass, but narrowly scoped** — see §6.3 |
| `rivers_and_tribes` | 0 | **real gap**, correctly caveated: no mantra carries both a River and a Tribe mention |

Two properties of the query set matter for answerability more than the timings do:

- **All 48 carry a non-empty `caveat`** (mean 181 characters). This is the strongest thing in
  the V2 deliverable and it re-verifies exactly.
- **11 of 48 (22.9%) contain an RV-only predicate** in their Cypher (`HAS_DEVATA`,
  `HAS_RISHI`, `HAS_CHANDAS` or `MENTIONS_LEMMA`), so they cannot return a non-Rigvedic row
  by construction: `deity_co_occurrence`, `deities_through_common_rishis`,
  `rishis_invoking_deity`, `rishis_invoking_deity_strict`, `weapons_and_deities`,
  `agni_and_indra_together`, `substances_offered_to_deities`, `attribution_precision_audit`,
  `soma_deity_versus_substance`, `agni_deity_fire_medium`, `rudra_profile_no_shiva`.
- 49 of the 50 killer questions are served by at least one query; **Q37 is served by none**.
  Five queries serve no killer question (they are the four self-checks plus
  `devata_taxonomy_coverage`).
- Nine queries have neither a `LIMIT` nor an aggregation, so their result size is
  data-dependent and unbounded: `deity_profile`, `varuna_profile`, `deity_composition`,
  `deity_epithets`, `natural_phenomena_personified`, `claim_evidence_trace`,
  `competing_interpretations`, `soma_deity_versus_substance`, `orphan_domain_entities`. All
  currently return 25 rows or fewer.

---

## 5. Known V2 backlog, independently verified

V2's own backlog is §65 of `VEDAGRAPH_KNOWLEDGE_MODEL_V2_FINAL_REPORT.md`, ten items. I
probed each against the live graph without reusing V2's probe.

### B1 — A theonym mention layer across four Vedas. **VERIFIED_STILL_OPEN, but the stated
reason is wrong and the stated consequence is only two-thirds true.**

V2: *"No `DomainEntity` exists for Indra, Varuṇa, Rudra, Viṣṇu or Mitra, so cross-Veda deity
presence is unreachable; 571 AV passages contain `indra`."*

The `DomainEntity` half reproduces. The conclusion drawn from it does not.

```cypher
MATCH (e:DomainEntity) WHERE toLower(e.entity_key) CONTAINS 'indra'
   OR toLower(coalesce(e.display_label,'')) CONTAINS 'indra' RETURN e.entity_key, e.display_label
```

0 rows — same as `BASELINE_FACTS` line 72. But the probe uses the wrong label. The ontology's
`RELATIONSHIP_SIGNATURES` explicitly admits `:Devata` as a legal `MENTIONS_ENTITY` range:

```cypher
MATCH (e) WHERE (e:Devata OR e:DomainEntity) AND (toLower(e.entity_key) CONTAINS 'indra'
  OR toLower(e.entity_key) CONTAINS 'varun' OR toLower(e.entity_key) CONTAINS 'rudra'
  OR toLower(e.entity_key) CONTAINS 'visnu' OR toLower(e.entity_key) CONTAINS 'mitra')
OPTIONAL MATCH ()-[m:MENTIONS_ENTITY]->(e)
RETURN e.entity_key, labels(e), count(m) AS mentions ORDER BY mentions DESC
```

| entity | labels | MENTIONS_ENTITY edges |
|---|---|---|
| VG:DEVATA:INDRAH | `Devata` | **2,305** |
| VG:DEVATA:VARUNAH | `Devata` | **392** |
| VG:DEVATA:MITRAH | `Devata` | **317** |
| VG:DEVATA:RUDRAH | `Devata` | **128** |
| VG:DEVATA:VISNUH | `Devata` | **98** |
| VG:DEVATA:INDRAGNI | `Devata` | 93 |
| VG:DEVATA:MITRAVARUNAU | `Devata` | 92 |
| VG:DEVATA:INDRABRHASPATI | `Devata` | 6 |
| 17 further Indra/Mitra/Rudra/Viṣṇu duals and groups | `Devata` | 0 each |

A theonym mention layer exists and carries 3,240 mentions for those five deities alone. What
does not exist is a *cross-Veda* one:

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(d:Devata) RETURN p.veda, count(*) ORDER BY 2 DESC
```

One row: `RV 9000`. Every deity mention in the graph is Rigvedic. Meanwhile the text itself:

```cypher
MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv) WHERE toLower(tv.text_nfc) CONTAINS 'indra'
RETURN p.veda, count(DISTINCT p);;
MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv) WHERE tv.text_nfc CONTAINS 'इन्द्र'
RETURN p.veda, count(DISTINCT p)
```

| Veda | passages whose stored text contains an Indra string | deity mentions in the graph |
|---|---|---|
| RV | 1,605 (Latin) | 2,305 |
| AV | **571** (Latin) | **0** |
| SV | **309** (Devanagari) | **0** |
| YV | **355** (Devanagari) | **0** |

V2's "571 AV passages contain `indra`" **reproduces exactly**. V2 could not have counted SV
or YV at all, because a Latin `CONTAINS 'indra'` finds nothing in a Devanagari corpus; the
Devanagari search adds 664 more passages. The real cross-Veda base is 1,235 non-Rigvedic
passages, not 571.

The graph's answer to "is Indra in the Atharvaveda" is 15:

```cypher
MATCH (p:Passage {veda:'AV'})-[r]->(x) WHERE x.entity_key='VG:DEVATA:INDRAH' RETURN count(DISTINCT p)
```

15 — all from the L3 semantic layer; `HAS_DEVATA` and `MENTIONS_ENTITY` each return 0. That
reproduces the prior adversarial run's C2 figure exactly.

### B2 — A gold set for the mention layer. **VERIFIED_STILL_OPEN. V2's two supporting
numbers reproduce only under two different denominators.**

V2: *"Recall is unmeasured (4,990 mantras uncovered, mean degree 1.884)."*

```cypher
MATCH (m:Mantra) OPTIONAL MATCH (m)-[r:MENTIONS_ENTITY]->(:DomainEntity) WITH m, count(r) AS d
RETURN count(m), sum(CASE WHEN d=0 THEN 1 ELSE 0 END), round(avg(d),4);;
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity) WITH p, count(*) AS d
RETURN count(p) AS covered_passages, round(avg(d),4)
```

| population | uncovered | mean degree |
|---|---|---|
| all 20,210 Mantra nodes, edges to `:DomainEntity` only | **4,990** | 1.4189 |
| the 15,220 passages that have at least one such edge | 0 by definition | **1.884** |
| all 20,210 Mantra nodes, any `MENTIONS_ENTITY` | 3,931 | 1.864 |
| all 22,537 Passage nodes, any `MENTIONS_ENTITY` | 6,258 | 1.672 |

Both of V2's numbers are real, and each comes from a different population. "4,990 uncovered"
is over all mantras; "mean degree 1.884" is over covered passages only. On one population,
uncovered 4,990 and mean 1.4189; presented together they read as a mention layer 33% denser
than it is. `BASELINE_FACTS`'s degree bands (0: 6,258 / 1-2: 10,518 / 3-5: 5,216 / 6+: 545)
**re-verify exactly**.

No gold set exists in the graph: 0 edges carry a human-adjudication property, and
`human_gold_status` in the sealed artifact reads `UNANNOTATED`. Still open.

### B3 — Retire or reconcile `ABOUT_CONCEPT` against the mention layer. **VERIFIED_STILL_OPEN,
and worse than V2 describes. V2's cited numbers do not reproduce.**

V2: *"Two rival layers answer the same question with different numbers (heaven–earth 499 vs
262)."*

```cypher
MATCH (e:Concept) WHERE toLower(e.display_label) CONTAINS 'heaven' OR toLower(e.display_label) CONTAINS 'earth'
OPTIONAL MATCH (pa:Passage)-[:ABOUT_CONCEPT]->(e) WITH e, count(DISTINCT pa) AS ac
OPTIONAL MATCH (pm:Passage)-[:MENTIONS_ENTITY]->(e) WITH e, ac, count(DISTINCT pm) AS me
RETURN e.entity_key, e.display_label, ac, me
```

| entity | ABOUT_CONCEPT passages | MENTIONS_ENTITY passages |
|---|---|---|
| VG:CONCEPT:DYAUS-HEAVEN | 1,659 | 1,206 |
| VG:CONCEPT:PRTHIVI-EARTH | 1,206 | 742 |

**499 and 262 appear nowhere.** No combined heaven-and-earth entity exists (only these two).
The true divergence is 3.3x larger than the one V2 reports as its illustration. Full rival
table in §6.2. Still open, and the disagreement is not only numeric: 74 of 163 concepts have
no `ABOUT_CONCEPT` edge at all.

### B4 — A directional protection edge to śatru / rakṣas / sapatna. **VERIFIED_STILL_OPEN.**

```cypher
MATCH ()-[:PROTECTS_FROM]->(t) RETURN t.entity_key, t.display_label, labels(t), count(*) ORDER BY 4 DESC
```

All 182 `PROTECTS_FROM` edges reach five `Condition` nodes: `KRTYA-SORCERY` 65,
`VISA-POISON` 63, `DUSVAPNYA-BAD-DREAM` 22, `DURNAMAN-ILL-NAMED-BEINGS` 17,
`GRAHI-SEIZURE` 15. Nothing reaches `śatru`, `rakṣas` or `sapatna`, although both entities
exist and carry mentions (`enemy (śatru)` 242 mention-passages, `overcoming rivals
(sapatna)` 101). Still open.

### B5 — Human review of the 736 model candidates, to create the first TIER_C edges.
**VERIFIED_STILL_OPEN, with a correction.**

```cypher
MATCH ()-[r]->() WHERE r.quality_tier='TIER_C' RETURN count(*)
```

0. And 736 edges carry `state = CANDIDATE`, none reviewed. But as §2 shows, the 736 are
already graded `TIER_D`, not awaiting a TIER_C grade — so a review would have to *re-grade*
them, not promote them from ungraded. Still open, and the item as written understates the
work.

### B6 — Remodel the 806 witness divergences. **VERIFIED_STILL_OPEN.**

```cypher
MATCH (q:QAIssue) RETURN q.check_id, q.severity, count(*) ORDER BY 3 DESC LIMIT 15
```

`primary_parallel_text_divergence` WARNING, **806** — exact. The next-largest check is
`STRUCTURAL_AMBIGUITY` at 21. All 915 QAIssue nodes remain `:Internal` and 0 reach product
traversal (`internal_leakage_check` returns 0 rows). Still open.

### B7 — 1,103 of 4,825 formulas are strict substrings of another. **VERIFIED_STILL_OPEN as a
defect; the number does not reproduce on any field.**

Measured with a full pairwise containment pass in `scratchpad/agentB/formula3.py` over
`MATCH (f:Formula) RETURN f.normalized, f.display_form`:

| field | unique strings | strict substrings of another | share |
|---|---|---|---|
| `normalized` | 4,825 | **1,039** | 21.5% |
| `display_form` | 4,825 | **984** | 20.4% |

Neither is 1,103. All 4,825 `normalized` values and all 4,825 `display_form` values are
distinct (0 exact duplicates). V2 §30 states the V1 figure "is unchanged and remains open"
without re-measuring it; the defect is real, the number is 6.2% high. Full treatment in
§6.6.

### B8 — Two registry files disagree about `MITRAVARUNAU`. **VERIFIED_STILL_OPEN, and the
graph contradicts itself on one node.**

```cypher
MATCH (d:Devata) WHERE d.entity_key IN ['VG:DEVATA:MITRAVARUNAU','VG:DEVATA:INDRAVARUNAU']
OPTIONAL MATCH (d)-[c:COMPOSED_OF]->(x)
RETURN d.entity_key, d.is_composite, d.structure, collect(x.entity_key), size([(d)--()|1])
```

| entity | `is_composite` | `structure` | COMPOSED_OF targets | degree |
|---|---|---|---|---|
| VG:DEVATA:MITRAVARUNAU | **false** | PAIR | `[MITRAH, VARUNAH]` | 288 |
| VG:DEVATA:INDRAVARUNAU | false | PAIR | `[]` | **77** |

`MITRAVARUNAU` carries `is_composite: false` *and* two `COMPOSED_OF` edges naming its
components. A client that reads the property gets one answer and a client that traverses the
edge gets the other. Note also that the prior adversarial run's conflation table grades
"Mitra vs Varuṇa vs Mitrāvaruṇau" as **CLEAN, exemplary**, citing the `COMPOSED_OF`
decomposition as the evidence — the same decomposition V2's backlog §65.8 says is
unadjudicated. Two V2-era documents in the same commit disagree about whether this is a
defect or a showpiece.

### B9 — `INDRAVARUNAU` has no component row. **VERIFIED_STILL_OPEN; degree is 77, not 70.**

Same query as B8. `INDRAVARUNAU` has `structure: PAIR`, degree 77, and no `COMPOSED_OF`
edge. V2 cites degree 70. Still open.

### B10 — Sarasvatī is absent from `River` by design. **VERIFIED_STILL_OPEN.**

```cypher
MATCH (n) WHERE toLower(coalesce(n.display_label,'')) CONTAINS 'sarasvat'
   OR toLower(coalesce(n.entity_key,'')) CONTAINS 'SARASVAT'
RETURN labels(n), coalesce(n.entity_key, n.display_label), size([(n)--()|1])
```

22 rows: three `:Devata` (`SARASVATI` degree 103, `SARASVATI-ILA-BHARATI` 12,
`ILA-SARASVATI-MAHI` 3) and nineteen `:Formula`. No `:River`, no `:Place`, no
`:DomainEntity`. Still open, and it is a deliberate refusal rather than an omission, as V2
says.

### Backlog summary

| item | verdict |
|---|---|
| B1 cross-Veda theonym layer | VERIFIED_STILL_OPEN — but the "no mention layer exists" framing is refuted for RV |
| B2 mention gold set | VERIFIED_STILL_OPEN — supporting numbers reproduce only on two different populations |
| B3 reconcile ABOUT_CONCEPT | VERIFIED_STILL_OPEN — cited numbers (499 vs 262) **not reproducible** |
| B4 directional protection edge | VERIFIED_STILL_OPEN |
| B5 review 736 candidates | VERIFIED_STILL_OPEN — plus a tier-mapping violation V2 did not report |
| B6 806 witness divergences | VERIFIED_STILL_OPEN |
| B7 formula strict substrings | VERIFIED_STILL_OPEN — number **not reproducible** (1,039, not 1,103) |
| B8 MITRAVARUNAU disagreement | VERIFIED_STILL_OPEN — and self-contradictory on one node |
| B9 INDRAVARUNAU no components | VERIFIED_STILL_OPEN — degree 77, not 70 |
| B10 Sarasvatī not a River | VERIFIED_STILL_OPEN |
| — | 0 ALREADY_CLOSED, 0 CANNOT_VERIFY |

---

## 6. Root weaknesses found before any coding

My own findings, ranked by how much research answerability they cost. Where the prior
adversarial run (`GRAPH_ADVERSARIAL_QA_V2.md`) already found something I say so — an
independent reproduction is worth recording, but I am not claiming the discovery.

### 6.1 (rank 1) Two relationship types carry the same 9,000 facts, and 9,992 nodes exist only to be disconnected

**Not reported anywhere.** This is the largest single piece of dead structure in the graph
and the prior orphan audit walked past it.

```cypher
MATCH (n) WHERE NOT n:Internal WITH n, size([(n)--()|1]) AS d
RETURN sum(CASE WHEN d=0 THEN 1 ELSE 0 END) AS product_deg0,
       sum(CASE WHEN d=1 THEN 1 ELSE 0 END) AS product_deg1, count(*) AS product_nodes
```

`product_deg0 = 9,992`, `product_deg1 = 116`, `product_nodes = 38,297`. Every one of the
9,992 is a `Lemma`:

```cypher
MATCH (n) WHERE NOT n:Internal AND NOT (n)--() RETURN labels(n), count(*) ORDER BY 2 DESC
```

One row: `["Lemma"] 9992`. So **99.61% of the 10,031 `Lemma` nodes have degree zero.** The
`MENTIONS_LEMMA` layer's 9,000 edges reach exactly 39 lemmas:

```cypher
MATCH ()-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l), count(*)
```

`39 / 9000`. And those 39 are all deity stems, with degrees that match the
`MENTIONS_ENTITY`-to-`Devata` counts to the unit: `índra-` 2,305 = Indra 2,305, `agní-`
1,604 = Agni 1,604, `sóma-` 950 = Soma 950, `aśvín-` 439, `marút-` 401, `váruṇa-` 392,
`sū́rya-` 378, `uṣás-` 353, `pr̥thivī́-` 319, `mitrá-` 317. That is not a coincidence:

```cypher
MATCH (p:Passage)-[:MENTIONS_LEMMA]->(l:Lemma) WITH p, count(*) AS lc
MATCH (p)-[:MENTIONS_ENTITY]->(d:Devata) WITH p, lc, count(*) AS dc
RETURN sum(CASE WHEN lc=dc THEN 1 ELSE 0 END) AS passages_equal_count,
       count(p) AS passages_with_both, sum(lc) AS lemma_edges, sum(dc) AS devata_mention_edges;;
MATCH (p:Passage)-[:MENTIONS_LEMMA]->() WHERE NOT (p)-[:MENTIONS_ENTITY]->(:Devata) RETURN count(DISTINCT p);;
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:Devata) WHERE NOT (p)-[:MENTIONS_LEMMA]->() RETURN count(DISTINCT p)
```

| measure | result |
|---|---|
| passages carrying both | 6,560 |
| passages where the two per-passage counts are **equal** | **6,560 (all of them)** |
| `MENTIONS_LEMMA` edges | 9,000 |
| `MENTIONS_ENTITY` to `:Devata` edges | 9,000 |
| passages with lemma mentions but no devata mentions | **0** |
| passages with devata mentions but no lemma mentions | **0** |

`MENTIONS_LEMMA` and `MENTIONS_ENTITY`-to-`Devata` are the same 9,000 facts written twice.
18,000 edges (7.4% of the graph) encode 9,000 assertions, and 23.9% of the flagship
`MENTIONS_ENTITY` predicate is a duplicate of another predicate.

**Cost to answerability.** A researcher counting "how often is a deity named in the corpus"
gets 18,000 if they union both predicates and 9,000 if they pick one, with nothing in the
graph or the query set telling them the two are identical. Ten of the 48 named queries touch
one of the two. And a UI that offers a `Lemma` browser presents 10,031 entries of which
9,992 open to an empty page.

**Why the existing check misses it.** `orphan_domain_entities` reads
`MATCH (e:DomainEntity) WHERE NOT (e)--()`. `Lemma` is not a `DomainEntity`, so the query
returns 0 and reads as a pass.

### 6.2 (rank 2) 44.7% of the largest knowledge layer has no Sanskrit evidence, and the two mention layers cover disjoint entity sets

The English-evidence share was found by the prior adversarial run as finding C3. What was not
reported is that the split is **exact and one-directional**, and that the two layers'
*entity* coverage barely overlaps.

`Concept` and `DomainEntity` are the same 163 nodes:

```cypher
MATCH (c:Concept) RETURN count(c), count(CASE WHEN c:DomainEntity THEN 1 END)
```

`163 / 163`. So `ABOUT_CONCEPT` (47,542) and `MENTIONS_ENTITY`-to-`Concept` (28,675) are two
edge layers over one node set. Pair-level overlap:

```cypher
MATCH (p:Passage)-[:ABOUT_CONCEPT]->(e:Concept) WHERE (p)-[:MENTIONS_ENTITY]->(e) RETURN count(*);;
MATCH (p:Passage)-[:ABOUT_CONCEPT]->(e:Concept) WHERE NOT (p)-[:MENTIONS_ENTITY]->(e) RETURN count(*);;
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Concept) WHERE NOT (p)-[:ABOUT_CONCEPT]->(e) RETURN count(*)
```

| (passage, entity) pairs | count |
|---|---|
| in both layers | 26,296 |
| `ABOUT_CONCEPT` only | **21,246** |
| `MENTIONS_ENTITY` only | 2,379 |

21,246 is exactly the `concept-alias-v1:english` edge count. Joining method to corroboration
confirms it is not a coincidence:

```cypher
MATCH (p:Passage)-[r:ABOUT_CONCEPT]->(e:Concept)
WITH r.method AS method, size([(p)-[:MENTIONS_ENTITY]->(e)|1]) AS me
RETURN method, CASE WHEN me>0 THEN 'corroborated' ELSE 'about_concept_only' END, count(*) ORDER BY 1
```

| `ABOUT_CONCEPT` method | corroborated by MENTIONS_ENTITY | uncorroborated |
|---|---|---|
| `concept-alias-v1:english` | **0** | **21,246** |
| `concept-alias-v1:english+sanskrit-token` | 13,015 | 0 |
| `concept-alias-v1:sanskrit-token` | 12,808 | 0 |
| `concept-alias-v1:sanskrit-sandhi` | 473 | 0 |

**A perfect partition, zero exceptions in either direction.** `ABOUT_CONCEPT` is
`MENTIONS_ENTITY`(Sanskrit) plus 21,246 matches on an English word in a 19th-century
translation and nothing else. All 47,542 are graded `TIER_B / L2_DETERMINISTIC_DERIVED /
state ACCEPTED`, indistinguishably.

**Entity coverage is 45% disjoint:**

```cypher
MATCH (e:Concept)
OPTIONAL MATCH (pa:Passage)-[:ABOUT_CONCEPT]->(e) WITH e, count(DISTINCT pa) AS ac
OPTIONAL MATCH (pm:Passage)-[:MENTIONS_ENTITY]->(e) WITH e, ac, count(DISTINCT pm) AS me
RETURN count(*) AS entities, sum(CASE WHEN ac>me THEN 1 ELSE 0 END) AS ac_gt_me,
       sum(CASE WHEN me>ac THEN 1 ELSE 0 END) AS me_gt_ac, sum(CASE WHEN ac=me THEN 1 ELSE 0 END) AS equal,
       sum(CASE WHEN ac=0 THEN 1 ELSE 0 END) AS ac_zero, sum(CASE WHEN me=0 THEN 1 ELSE 0 END) AS me_zero
```

`entities 163, ac_gt_me 88, me_gt_ac 74, equal 1, ac_zero 74, me_zero 0`. **74 of 163
concepts (45.4%) have zero `ABOUT_CONCEPT` edges**, and no concept has zero
`MENTIONS_ENTITY` edges. The 74 are the V2-added Atharvavedic and material vocabulary that
never entered the concept alias registry: `bull (vṛṣabha)` 201 mention-passages / 0
`ABOUT_CONCEPT`, `embryo (garbha)` 182/0, `strainer (pavitra)` 103/0, `overcoming rivals
(sapatna)` 101/0, `amulet (maṇi)` 86/0, `noose (pāśa)` 67/0, `witchcraft (kṛtyā)` 65/0,
`poison (viṣa)` 63/0, `armour (varman)` 53/0, `marriage (vivāha)` 41/0.

**Rival-numbers table, top 25 shared entities.** Distinct passages per entity per layer:

```cypher
MATCH (e:Concept)
OPTIONAL MATCH (pa:Passage)-[:ABOUT_CONCEPT]->(e) WITH e, count(DISTINCT pa) AS ac_passages
OPTIONAL MATCH (pm:Passage)-[:MENTIONS_ENTITY]->(e) WITH e, ac_passages, count(DISTINCT pm) AS me_passages
WHERE ac_passages > 0 AND me_passages > 0
RETURN e.display_label, e.display_type, ac_passages, me_passages, ac_passages - me_passages AS delta
ORDER BY ac_passages DESC LIMIT 25
```

| entity | kind | ABOUT_CONCEPT | MENTIONS_ENTITY | delta | disagreement |
|---|---|---|---|---|---|
| fire (agni) | NaturalPhenomenon | 2,206 | 2,095 | +111 | 5.0% |
| soma juice (soma) | Substance | 1,841 | 1,570 | +271 | 14.7% |
| heaven (dyaus) | CosmicEntity | 1,659 | 1,206 | +453 | 27.3% |
| wealth (rayi) | Concept | 1,601 | 885 | +716 | 44.7% |
| sacrifice (yajña) | Ritual | 1,570 | 839 | +731 | 46.6% |
| praise (stoma) | Action | 1,367 | 402 | +965 | **70.6%** |
| cattle (go) | Animal | 1,339 | 757 | +582 | 43.5% |
| earth (pṛthivī) | CosmicEntity | 1,206 | 742 | +464 | 38.5% |
| might (ojas) | Quality | 1,044 | 526 | +518 | 49.6% |
| horse (aśva) | Animal | 918 | 234 | +684 | **74.5%** |
| waters (āpaḥ) | NaturalPhenomenon | 900 | 396 | +504 | 56.0% |
| help (avas) | Concept | 895 | 408 | +487 | 54.4% |
| speech (vāc) | PhilosophicalConcept | 824 | 651 | +173 | 21.0% |
| oblation (havis) | Offering | 813 | 401 | +412 | 50.7% |
| friendship (sakhya) | Concept | 781 | 439 | +342 | 43.8% |
| protection (śarman) | Concept | 775 | 272 | +503 | 64.9% |
| birth (janman) | Action | 763 | 345 | +418 | 54.8% |
| people (jana) | Concept | 761 | 478 | +283 | 37.2% |
| enemy (śatru) | Concept | 757 | 242 | +515 | 68.0% |
| sun (sūrya) | NaturalPhenomenon | 746 | 653 | +93 | 12.5% |
| soma pressing (savana) | Ritual | 729 | 656 | +73 | 10.0% |
| insight (dhī) | PhilosophicalConcept | 721 | 421 | +300 | 41.6% |
| liberality (dāna) | Action | 708 | 109 | +599 | **84.6%** |
| chariot (ratha) | Object | 702 | 473 | +229 | 32.6% |
| food (anna) | Substance | 691 | 251 | +440 | 63.7% |

Every delta is positive. The three worst — `liberality (dāna)` 84.6%, `horse (aśva)` 74.5%,
`praise (stoma)` 70.6% — are cases where an English word in Griffith is common and the
Sanskrit alias set is narrow.

**Cost to answerability.** For 25 of the most-asked-about entities in the corpus, the graph
holds two answers to "how many passages concern X" that differ by 5% to 85%, with identical
tier, layer and state, and no edge property that ranks them. And because SV has no
translation, SV's `ABOUT_CONCEPT` count is Sanskrit-only (2,200 edges, 0 English) while RV's
is 48% English — so cross-Veda concept comparison measures the four corpora with two
different instruments.

### 6.3 (rank 3) `theonym_ambiguous` is an orthographic accident, is absent where it matters most, and carries almost no information

The flag's stem-vs-inflection defect is the prior adversarial run's C1. Three things beyond
that are new here.

```cypher
MATCH ()-[m:MENTIONS_ENTITY]->() RETURN m.theonym_ambiguous, count(*) ORDER BY 2 DESC
```

| value | edges |
|---|---|
| `false` | 24,779 |
| *(null)* | **9,000** |
| `true` | 3,896 |

**(a) The flag is null on exactly the 9,000 edges whose target is a deity.** The caveat "some
words are both a deity and a thing" is applied only to the *thing* side of every pair and
never to the deity side. A query filtering `WHERE NOT m.theonym_ambiguous` keeps all 9,000
deity mentions, including the ones reached through an alias that is also a common noun.

**(b) The flag is decided per inflected surface form, and the forms are split
inconsistently.**

```cypher
MATCH ()-[m:MENTIONS_ENTITY]->(e:DomainEntity {display_label:'fire (agni)'})
RETURN m.theonym_ambiguous, m.matched_aliases, count(*) ORDER BY 3 DESC LIMIT 20
```

| matched alias | flag | edges | note |
|---|---|---|---|
| `agne` (vocative) | **true** | 863 | |
| `agnir` | **false** | 283 | sandhi form of `agniḥ` |
| `agniṃ` | **false** | 197 | accusative sg. |
| `agniḥ` | **true** | 146 | same nominative as `agnir` |
| `agna` | false | 136 | |
| `agnim` | **true** | 97 | **same accusative sg. as `agniṃ`** |
| `agnaye` | true | 46 | dative |
| `agnau` | false | 33 | locative |
| `agnayaḥ` | false | 26 | |
| `agninā` | false | 8 | instrumental |

`agnim` is flagged and `agniṃ` is not; they are the same accusative singular differing only
in whether the nasal is written `m` or `ṃ`. `agniḥ` is flagged and `agnir` is not; same
nominative before different sandhi. The boundary between 3,896 flagged and 24,779 unflagged
edges is orthographic, not semantic.

**(c) The flag has a 10-point lift over doing nothing.** The checkable correlate is whether
the same passage also carries an Anukramaṇī deity attribution of the same stem:

```cypher
MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(:DomainEntity {display_label:'fire (agni)'})
WITH p, max(CASE WHEN m.theonym_ambiguous THEN 1 ELSE 0 END) AS flagged
OPTIONAL MATCH (p)-[:HAS_DEVATA]->(d:Devata) WHERE d.entity_key CONTAINS 'AGNI'
WITH flagged, p, count(d) AS agni_dev
RETURN flagged, count(p) AS passages, sum(CASE WHEN agni_dev>0 THEN 1 ELSE 0 END) AS with_agni_devata
```

| population | passages | also `HAS_DEVATA` to an Agni | rate |
|---|---|---|---|
| flagged `theonym_ambiguous = true` | 1,205 | 706 | **58.6%** |
| unflagged `theonym_ambiguous = false` | 890 | 429 | **48.2%** |
| all RV passages (base rate) | 11,590 | 2,150 | 18.6% |

Both populations sit far above the 18.6% base rate — the *entity* is highly informative. The
*flag* separates them by 10.4 points. It cannot be used as a filter: dropping flagged
mentions removes 706 passages that do sit under an Agni hymn and keeps 429 that also do.

**(d) The flag is nonetheless mostly defensible where it fires,** which is worth recording
because it is easy to dismiss the odd-looking entries. Of 14 flagged entities whose English
gloss looks non-theophoric, 11 have a matching `:Devata` node:

```cypher
UNWIND ['VARMAN','BARHIS','DAKSINA','SRADDHA','SVASTI','MANDUKA','DUNDUBHI','YUPA',
        'ULUKHALA','GRAVAN','KSETRA','ADHVAN','JYA','SVAN'] AS stem
OPTIONAL MATCH (d:Devata) WHERE d.entity_key CONTAINS stem
RETURN stem, collect(d.entity_key)
```

Matched: `DAKSINA`, `SRADDHA`, `PATHYASVASTIH`, `MANDUKAH`, `DUNDUBHIH`, `YUPAH`,
`ULUKHALAM`, `GRAVANAH`, `KSETRAPATIH`, `JYA`, four `SVAN`-stems. Unmatched, therefore
probable false positives: **`VARMAN`, `BARHIS`, `ADHVAN`** (3 of 14, 21%).

### 6.4 (rank 4) The only model-extracted layer in the graph covers the two Vedas with no attribution layer, and the sealed Rigvedic artifact is absent

**Not reported anywhere, and it inverts the reading of the semantic layer.**

```cypher
MATCH ()-[r]->() WHERE r.knowledge_layer='L3_LLM_EXTRACTED'
RETURN r.run_id, r.pipeline_version, r.model, r.method, r.prompt_policy, count(*);;
MATCH (p)-[r]->() WHERE r.knowledge_layer='L3_LLM_EXTRACTED'
RETURN p.veda, count(*), count(DISTINCT p) ORDER BY 2 DESC
```

| field | value |
|---|---|
| run_id | `vedagraph-graph-enrichment-v1:semantic:fc3293ccaa469753` |
| pipeline_version | `vedagraph-graph-enrichment-v1` |
| model | `claude-opus-5` |
| method | `semantic-extraction/rigveda-semantic-ontology-v1` |
| prompt_policy | `vedagraph-enrichment-semantic-prompt-v1` |
| edges | 736 |

| source Veda | edges | distinct passages |
|---|---|---|
| YV | 415 | 207 |
| AV | 321 | 157 |
| **RV** | **0** | **0** |
| **SV** | **0** | **0** |

364 passages of 22,537 — **1.6% semantic coverage** — and none of it Rigvedic, despite the
`method` string naming `rigveda-semantic-ontology-v1`.

I read the sealed artifact directly
(`data/semantic/vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1/output_seal.json`).
Every fact `BASELINE_FACTS` records about it **re-verifies exactly**: `run_id`
`vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`, `seal_status VALIDATED`,
`candidate_status "CANDIDATE / NEEDS_REVIEW"`, `human_gold_status UNANNOTATED`, `runtime
CLAUDE_CODE_DIRECT`, `model_reported claude-opus-5` with
`model_provenance_classification AGENT_RUNTIME_SELF_REPORTED_UNATTESTED` and
`independent_runtime_model_attestation UNAVAILABLE`, 448 passages, 2,459 assertions, and all
eleven integrity counters at zero (`binding_failures`, `cross_passage_duplicate_ids`,
`duplicate_final_passages`, `evidence_failures`, `heuristic_contamination`,
`missing_final_tasks`, `ontology_type_failures`, `packet_hash_failures`,
`provenance_mismatch`, `receipt_failures`, `span_failures`). Two facts not in
`BASELINE_FACTS`: `no_claim_passages = 50` (11.2% of the 448 produced no assertion) and
`canonical_promotion = false`.

The seal's predicate mix and the graph's do not match, which is the proof they are different
artifacts:

| predicate | sealed RV artifact | live graph (L3) |
|---|---|---|
| DESCRIBES | 734 | 280 |
| DESCRIBES_ACTION | 553 | 35 |
| REQUESTS | 395 | 109 |
| INVOKES | 211 | 222 |
| REFERS_TO_PLACE | 122 | 3 |
| INVOLVES_SUBSTANCE | 117 | 3 |
| REFERS_TO_NATURAL_PHENOMENON | 100 | 5 |
| INVOLVES_RITUAL | 78 | 11 |
| PRAISES | 55 | 38 |
| INVOLVES_OFFERING | 46 | 14 |
| **EXPRESSES** | **27** | **0 — type does not exist in the graph** |
| **ASSOCIATED_WITH** | **17** | **0 — type does not exist in the graph** |
| CONTRASTS_WITH | 4 | 8 |
| HAS_THEME | — | 8 |
| **total** | **2,459** | **736** |

`BASELINE_FACTS` line 78's claim that the sealed artifact is not projected is **confirmed**.
What it does not say is that a *different, unsealed* 736-edge run is in the graph in its
place, and that it lands on exactly the two corpora that have no `HAS_DEVATA`, `HAS_RISHI`
or `HAS_CHANDAS` layer.

**Cost to answerability.** The Rigveda has the complete attribution apparatus, Latin text,
Griffith translation and a VALIDATED 2,459-assertion semantic artifact, and zero semantic
edges. The Yajurveda has no attribution apparatus, Devanagari-only text, and is the
best-covered corpus in the semantic layer (415 edges). Any "which Veda does the graph know
most about" comparison will invert depending on which layer is asked.

### 6.5 (rank 5) Evidence verifies at 92.9% after re-deriving a fold that is not stored, and 0% for the Sāmaveda and Yajurveda

I sampled 1,536 edges carrying an evidence payload — 400 `MENTIONS_ENTITY`, 400
`ABOUT_CONCEPT`, all 736 L3 — parsed 1,631 evidence items, resolved each `locator` to a
passage by `canonical_key`, and tested the `quote` against every stored
`TextVersion.text_nfc` and `Translation.text` on that passage. Harness:
`scratchpad/agentB/verify2.py`, seed 20260909. Three verdicts: exact substring; substring
after NFC decomposition, combining-accent removal, `ṁ`/`ṃ` unification, avagraha removal and
punctuation stripping; substring only of the Sanskrit-plus-translation concatenation.

**Payload availability first.** Not every edge has evidence:

```cypher
MATCH ()-[m:MENTIONS_ENTITY]->() RETURN count(*), count(m.evidence), count(m.matched_aliases), count(m.occurrence_count);;
MATCH ()-[r:ABOUT_CONCEPT]->() RETURN count(*), count(r.evidence), count(r.score)
```

| predicate | edges | with `evidence` | with `matched_aliases` | with `occurrence_count` |
|---|---|---|---|---|
| MENTIONS_ENTITY | 37,675 | **28,675 (76.1%)** | 28,675 | 9,000 |
| ABOUT_CONCEPT | 47,542 | 47,542 (100%) | — | — |

The 9,000 `MENTIONS_ENTITY` edges without evidence are exactly the deity-target duplicates of
§6.1; they carry an `occurrence_count` instead. So 23.9% of the mention layer has no evidence
quote at all.

**Verification result, 1,631 items:**

| layer | surface | items | exact | after fold | concat only | not found | verified |
|---|---|---|---|---|---|---|---|
| MENTIONS_ENTITY | `script_folded` | 394 | 73 | 270 | 0 | 51 | 87.1% |
| MENTIONS_ENTITY | `sandhi_insensitive` | 6 | 0 | 0 | 0 | 6 | **0.0%** |
| ABOUT_CONCEPT | `translation_en` | 270 | **270** | 0 | 0 | 0 | **100.0%** |
| ABOUT_CONCEPT | `script_folded` | 219 | 40 | 137 | 0 | 42 | 80.8% |
| ABOUT_CONCEPT | `sandhi_insensitive` | 6 | 0 | 0 | 0 | 6 | **0.0%** |
| L3 semantic | `packet:<hash>` | 736 | 702 | 0 | 24 | 10 | 98.6% |
| **all** | | **1,631** | **1,085** | **407** | **24** | **115** | **92.9%** |

**Strictly exact: 66.5%. Verified by any route: 92.9%. Unverifiable against anything stored:
7.1%.**

The 115 failures are not wrong quotes; they are a script mismatch:

| Veda | surface | items | exact | after fold | not found | verified |
|---|---|---|---|---|---|---|
| AV | `script_folded` | 152 | 113 | 39 | 0 | **100.0%** |
| RV | `script_folded` | 369 | 0 | 368 | 1 | **99.7%** |
| **SV** | `script_folded` | 43 | 0 | 0 | **43** | **0.0%** |
| **SV** | `sandhi_insensitive` | 12 | 0 | 0 | **12** | **0.0%** |
| **YV** | `script_folded` | 49 | 0 | 0 | **49** | **0.0%** |

104 of the 115 failures are SV/YV, whose quotes are IAST while their only stored text is
Devanagari. One example, verbatim from the run:

```
VG:SV:KAU:UTTARA:P04:R02:D01:V06   quote: "somāso gobhirañjate yajño na sapta"
stored: "राजानो न प्रशस्तिभिः सोमासो गोभिरञ्जते । यज्ञो न सप्त धातृभिः"   (no translation)
```

The quote is a faithful transliteration of the stored line, and there is no surface in the
graph in the same script to check it against. This is the prior adversarial run's N3
(4,576 unverifiable spans, all SV + YV) reproduced from a different sample — I confirm both
the cause and the population.

Two things the prior run did not report:

- **The RV needs a fold too.** 0 of 369 RV `script_folded` items are exact substrings of
  stored text; all 368 verifiable ones need accent stripping. The RV stores only accented
  Latin (`PRIMARY_TEXT` and `PARALLEL_TEXT`, both `accented: true`), while the AV also stores
  a `SEARCH_DERIVATIVE` (`accented: false`, 5,839 rows) which is why AV verifies at 113/152
  exact. The folded surface the matcher used is persisted for one corpus of four.
- **The L3 `packet:` surface is unreconstructable.** All 736 L3 quotes cite
  `surface: "packet:<32-hex>"`, and no node in the graph holds a packet. 702 happen to be
  substrings of the translation, 24 verify only against a Sanskrit-plus-translation
  concatenation — one reads `"ní dadhmasi ||4|| In the parrots, in the ''ropaṇā́kās'',"`,
  crossing the Sanskrit/English boundary mid-quote — and 10 verify against nothing. A reader
  auditing an L3 assertion must guess the concatenation rule.

### 6.6 (rank 6) `Formula` is 21.5% nested n-grams, and a third of formula-bearing passages double-count

**Properly measured.** V2 §30 carries V1's figure of 1,103 without re-measuring; I did the
full pairwise containment pass (`scratchpad/agentB/formula.py`, `formula2.py`).

| measure | result |
|---|---|
| Formula nodes | 4,825 |
| distinct `normalized` strings | 4,825 (0 exact duplicates) |
| **strict substrings of another formula** | **1,039 (21.5%)** |
| same measure on `display_form` | 984 (20.4%) |
| `USES_FORMULA` edges hanging off a contained formula | 8,159 of 22,686 (**36.0%**) |
| **longest containment chain** | **4 levels** |
| `word_count` range | 2 to 8 (2-word 2,038, 3-word 1,249, 4-word 614, 5-word 345, 6-word 241, 7-word 185, 8-word 153) |
| `cross_veda = true` | 3,643 of 4,825 (75.5%) — V2's figure, **reproduced exactly** |
| orphan Formula nodes | 0 (minimum degree 3) |

The longest chain:

```
'uṣasā sūryeṇa'  (13 chars)
  ⊂ 'sajoṣasā uṣasā sūryeṇa'  (22)
    ⊂ 'sajoṣasā uṣasā sūryeṇa ca'  (25)
      ⊂ 'sacābhuvā sajoṣasā uṣasā sūryeṇa ca somam pibatam aśvinā'  (56)
```

The answerability cost is not the node count, it is the per-passage double-count:

```cypher
MATCH (p:Passage)-[:USES_FORMULA]->(f:Formula) RETURN p.canonical_citation, f.normalized
```
then containment within each passage's own formula set:

| measure | result |
|---|---|
| passages with at least one formula | 10,574 |
| passages where one formula is a strict substring of a sibling on the same passage | **3,342 (31.6%)** |
| edges attributable to same-passage nesting | **5,720 of 22,686 (25.2%)** |

Worst case, `AVS 10.6.9`: 12 `USES_FORMULA` edges, 9 of them strict substrings of a sibling.
Its formula list contains `'bhūyobhūyaḥ śvaḥśvas tena'`, `'duhe bhūyobhūyaḥ śvaḥśvas tena'`,
`'id duhe bhūyobhūyaḥ śvaḥśvas tena'`, `'bhūyobhūyaḥ śvaḥśvas tena tvaṃ dviṣato jahi'`,
`'duhe bhūyobhūyaḥ śvaḥśvas tena tvaṃ dviṣato jahi'` and `'id duhe bhūyobhūyaḥ śvaḥśvas tena
tvaṃ dviṣato jahi'` — six nested windows on one word sequence. "How many formulas does AVS
10.6.9 share with other passages" answers 12; the honest answer is 3 maximal formulas.

### 6.7 (rank 7) 15 of 35 declared V2 predicates are empty, and one predicate's declared range label has no nodes

Reconciled programmatically (`scratchpad/agentB/contract.py`) by importing
`ontology.DOMAIN_RELATIONSHIP_TYPES`, `PRODUCT_LABELS`, `INTERNAL_LABELS` and
`UNPOPULATED_BY_DESIGN` and diffing against `db.relationshipTypes()` and `db.labels()`.

| measure | result |
|---|---|
| declared V2 predicates | 35 |
| of those, populated | **20** |
| of those, empty | **15 (42.9%)** |
| of the 15, documented in `UNPOPULATED_BY_DESIGN` | **1** (`MUSICALIZED_AS`) |
| populated types not in `DOMAIN_RELATIONSHIP_TYPES` | 29 |
| **signature violations across all 20 populated V2 predicates** | **0** |

The 14 undocumented empty predicates: `ASSERTED_BY`, `ASSOCIATED_WITH_CONCEPT`,
`ASSOCIATED_WITH_PHENOMENON`, `ASSOCIATED_WITH_SUBSTANCE`, `ASSOCIATED_WITH_TRIBE`,
`BELONGS_TO_FAMILY`, `CO_OCCURS_WITH`, `DESCRIBED_IN`, `HAS_STEP`, `PERFORMS_ACTION`,
`PERSONIFIES`, `RECEIVES_OFFERING`, `TEXTUALLY_REUSED_AS`, `WIELDS`. This exactly reproduces
the prior adversarial run's "dead declared vocabulary" list. **What is new is that V2's final
report §66 states the boundary as "35 V2 predicates with enforced endpoint signatures, and a
declared-but-empty `MUSICALIZED_AS`"** — singular, as if it were the only one. Two V2-era
documents in the same commit disagree by fourteen predicates.

Declared `PRODUCT_LABELS` with zero nodes: `Region`, `RishiFamily`, `Theme` (3 of 40). The
`Theme` case is a live inconsistency rather than dead weight:

```cypher
MATCH ()-[r:HAS_THEME]->(t) RETURN labels(t), t.display_label, count(*);;
MATCH (n:Theme) RETURN count(n)
```

`HAS_THEME` has 8 edges, all pointing at `healing (bheṣaja)`, a `Concept/DomainEntity`; the
`Theme` label has 0 nodes. The predicate that needs the label fires while the label is
absent, and because `HAS_THEME` is not in `DOMAIN_RELATIONSHIP_TYPES` no signature check
catches it. Same for the other 11 L3 semantic predicates.

**What the contract gets right, and it is worth stating plainly.** I checked every populated
V2 predicate against its `RELATIONSHIP_SIGNATURES` entry:

```python
for rt, (src, dst) in RELATIONSHIP_SIGNATURES.items():
    MATCH (a)-[r:rt]->(b) WHERE NOT (a:<any src>) OR NOT (b:<any dst>) RETURN count(r)
```

**0 violations across all 20 populated predicates, 39,033 edges.** Also clean: 0 reciprocal
edges on `EXACT_PARALLEL_OF`, `NEAR_PARALLEL_OF`, `VARIANT_OF`, `REUSES_TEXT_FROM`,
`PARALLEL_TO` and `CONTAINS` (no double-counting from bidirectional storage); 0 duplicate
edges on `MENTIONS_ENTITY`, `ABOUT_CONCEPT`, `USES_FORMULA` and `HAS_DEVATA`; 0 orphans in
every product label except `Lemma`; 0 null `quality_tier`; 0 internal-label leakage.

### 6.8 (rank 8) `MENTIONS_ENTITY` reaches 203 entities, not 163, and the distribution is defensible

The brief's premise is 163 entities. Measured:

```cypher
MATCH ()-[:MENTIONS_ENTITY]->(e) RETURN count(DISTINCT e);;
MATCH ()-[:MENTIONS_ENTITY]->(e:Devata) RETURN count(DISTINCT e), count(*)
```

**203 distinct targets** — 163 `DomainEntity` (all of them; 0 are never mentioned) plus **40
`Devata`** carrying 9,000 edges. The ontology admits both ranges, so this is not a defect,
but any per-entity analysis built on 163 omits 23.9% of the layer.

Concentration:

```cypher
MATCH ()-[:MENTIONS_ENTITY]->(e) WITH e, count(*) AS n ORDER BY n DESC
WITH collect(n) AS ns, sum(n) AS total
RETURN total, size(ns), reduce(s=0,x IN ns[0..1]|s+x) AS top1, reduce(s=0,x IN ns[0..5]|s+x) AS top5,
       reduce(s=0,x IN ns[0..10]|s+x) AS top10, reduce(s=0,x IN ns[0..20]|s+x) AS top20, ns[size(ns)/2] AS median
```

| measure | value |
|---|---|
| total edges | 37,675 |
| entities | 203 |
| top 1 (`Indra`, 2,305) | **6.1%** |
| top 5 | 23.3% |
| top 10 | 34.4% |
| top 20 | 48.3% |
| median entity | 83 mentions |
| minimum | 1 mention (4 entities) |

Band distribution: 5 entities above 1,000 mentions (8,780 edges), 84 in 101–1,000 (25,372),
45 in 26–100 (2,883), 45 in 6–25 (568), 20 in 2–5 (68), 4 with exactly 1.

**Is the top entity defensible? Yes, and the question is a red herring.** No entity dominates:
the maximum is 6.1%, the top-20 is under half the layer, and the median entity carries 83
mentions. Indra being the most-mentioned entity in a Rigveda-weighted corpus is the expected
result, not a defect. The defensibility problem is one rank down and it is the theonym split:

| rank | entity | kind | mentions |
|---|---|---|---|
| 1 | Indra | Devata | 2,305 |
| 2 | **fire (agni)** | NaturalPhenomenon | **2,095** |
| 3 | **Agni** | Devata | **1,604** |
| 4 | **soma juice (soma)** | Substance | **1,570** |
| 6 | **Soma** | Devata | **950** |
| 12 | **sun (sūrya)** | NaturalPhenomenon | **653** |
| 29 | **Surya** | Devata | **378** |

Three of the corpus's four most-invoked deities appear twice in the top 30, split across a
`Devata` node and a common-noun `Concept` node, with 3,699 + 2,520 + 1,031 edges divided
between them on lexical grounds that §6.3 shows are orthographic. Neither node is the answer
to "how often does the corpus speak of Agni".

### 6.9 (rank 9) Near-orphan product nodes that render as dead ends

Beyond §6.1's 9,992 zero-degree Lemmas, `product_deg1 = 116` nodes have exactly one edge:

```cypher
MATCH (n) WHERE NOT n:Internal
WITH n, head([l IN labels(n) WHERE NOT l IN ['DomainEntity','Concept','Mantra','Passage']] + [head(labels(n))]) AS lab,
     size([(n)--()|1]) AS deg
RETURN lab, count(*) AS nodes, sum(CASE WHEN deg=0 THEN 1 ELSE 0 END) AS deg0,
       sum(CASE WHEN deg=1 THEN 1 ELSE 0 END) AS deg1, min(deg), max(deg) ORDER BY nodes DESC
```

(`lab` is the narrowest label, so counts differ from the §1 census where a node carries
several.)

| label | nodes | degree 0 | degree 1 | min | max |
|---|---|---|---|---|---|
| Lemma | 10,031 | **9,992** | 0 | 0 | 2,305 |
| **Epithet** | 13 | 0 | **13 (100%)** | 1 | 1 |
| **DerivedMetric** | 79 | 0 | **77 (97%)** | 1 | 3 |
| Rishi | 367 | 0 | 14 | 1 | 836 |
| Chandas | 34 | 0 | 10 | 1 | 4,195 |
| InterpretiveClaim | 6 | 0 | 1 | 1 | 8 |
| Substance | 10 | 0 | 1 | 1 | 3,430 |
| Passage | 22,537 | 0 | 0 | **2** | 192 |
| Formula | 4,825 | 0 | 0 | **3** | 93 |
| Devata | 214 | 0 | 0 | 2 | 5,243 |

All 13 `Epithet` nodes have degree exactly 1 — the inbound `HAS_EPITHET` and nothing else, so
an epithet page can show its deity and nothing further. 77 of 79 `DerivedMetric` nodes have a
single `MEASURES` edge with no `SUPPORTED_BY_STATISTIC` back-link. 14 `Rishi` and 10
`Chandas` nodes appear in exactly one hymn.

### 6.10 (rank 10) The interpretive layer's state does not match its documentation

V2's READY table says the interpretive claims are *"all TIER_D and permanently CANDIDATE"*.

```cypher
MATCH (ic:InterpretiveClaim)-[r]->() RETURN type(r), r.state, r.quality_tier, count(*);;
MATCH (ic:InterpretiveClaim) RETURN ic.claim_id, ic.status, ic.claim_type, ic.quality_tier, ic.asserted_by
```

All 22 claim edges (`SUPPORTED_BY` 7, `CONCERNS` 7, `SUPPORTED_BY_STATISTIC` 6,
`CONTRADICTS` 2) are `TIER_D` with **`state = null`**. Not one carries `CANDIDATE`; the only
736 `CANDIDATE` edges in the graph are the L3 semantic ones. The 6 nodes carry
`status` of `MODEL_SYNTHESIS` (4) or `RESEARCH_HYPOTHESIS` (2) — the right vocabulary, but
not the word the report uses — and **`asserted_by = ""` on all six**, an empty string that is
in `NULL_LABEL_SENTINELS`. `ASSERTED_BY` as a relationship type has 0 edges, so the 9 `Source`
nodes are not reachable from any claim. "Who asserts this claim" is unanswerable for all six.

The claims themselves re-verify as present and correctly graded:
`AGNI-LEXICALLY-UNDIFFERENTIATED`, `ANUKRAMANI-ATTRIBUTION-IS-SUKTA-SCOPED`,
`CONCEPT-LAYER-LEANS-ON-TRANSLATION`, `RISHI-ATTRIBUTION-LEAST-VERSE-SPECIFIC`,
`SV-IDENTITY-IS-MELODIC`, `SV-PREDOMINANTLY-RV-REUSE`. One of them,
`CONCEPT-LAYER-LEANS-ON-TRANSLATION`, is the graph asserting §6.2 about itself — which is the
best thing in the interpretive layer and is worth saying.

### Ranking rationale

| rank | weakness | answerability cost |
|---|---|---|
| 1 | `MENTIONS_LEMMA` duplicates `MENTIONS_ENTITY`; 9,992 orphan Lemmas | every deity-frequency count is 2x or 1x with no way to tell; 26% of product nodes render empty |
| 2 | 21,246 English-only `ABOUT_CONCEPT`; 74/163 concepts absent from it | the two largest layers give answers differing 5–85% for 25 top entities; cross-Veda concept comparison invalid |
| 3 | `theonym_ambiguous` orthographic, null on deity targets, 10-pt lift | deity/common-noun disambiguation is unavailable for the three most important deities |
| 4 | L3 layer is AV+YV only; sealed RV artifact absent | 1.6% semantic coverage, inverted against the corpus that has everything else |
| 5 | evidence 66.5% exact, 0% for SV/YV | 7.1% of sampled evidence unauditable; two corpora entirely so |
| 6 | 1,039 nested formulas; 31.6% of passages double-count | formula-sharing counts inflated up to 4x on one word sequence |
| 7 | 15/35 declared predicates empty; `Theme` label absent while `HAS_THEME` fires | an API enumerating the contract advertises 14 capabilities that return nothing |
| 8 | 203 mention targets, theonym split across two nodes | no single node answers "how often does the corpus speak of Agni" |
| 9 | 116 degree-1 product nodes | Epithet and DerivedMetric pages are dead ends |
| 10 | interpretive `state` null, `asserted_by` empty, `ASSERTED_BY` unpopulated | "who asserts this" unanswerable for all 6 claims |

---

## 7. Falsifiable statements about the baseline

Each is a measurement that holds at commit `92f2539` and that would measurably change if V3
addresses the corresponding weakness. Each is written so it can be re-run verbatim and
compared. I am not saying V3 should change them; I am saying these are the numbers that would
move if it did.

### F1 — Deity mentions exist only in the Rigveda

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(d:Devata) RETURN p.veda AS veda, count(*) AS n ORDER BY n DESC
```

**Baseline: exactly one row, `RV 9000`.** Any second row falsifies it. The upper bound
available from stored text is 1,235 further passages (AV 571 Latin, YV 355 Devanagari, SV 309
Devanagari; see §5/B1), so a cross-Veda theonym layer should produce three additional rows.
Paired check that the answer is not simply the AV alone:

```cypher
MATCH (p:Passage {veda:'AV'})-[r]->(x) WHERE x.entity_key='VG:DEVATA:INDRAH' RETURN count(DISTINCT p)
```

**Baseline: 15.** Stored AV text containing `indra`: 571.

### F2 — 21,246 ABOUT_CONCEPT edges are uncorroborated by any Sanskrit evidence, and the partition is perfect

```cypher
MATCH (p:Passage)-[r:ABOUT_CONCEPT]->(e:Concept)
WITH r.method AS method, size([(p)-[:MENTIONS_ENTITY]->(e)|1]) AS me
RETURN method, CASE WHEN me>0 THEN 'corroborated' ELSE 'about_concept_only' END AS status, count(*) AS n
ORDER BY method, status
```

**Baseline: 4 rows.** `concept-alias-v1:english / about_concept_only / 21246`, and the other
three methods 100% corroborated with zero uncorroborated rows. Falsified by any of: the
21,246 dropping; a `concept-alias-v1:english` row appearing under `corroborated`; a
Sanskrit-method row appearing under `about_concept_only`; or the layers being merged so the
query returns fewer than 4 rows. Companion measure — the disagreement should shrink:

```cypher
MATCH (e:Concept)
OPTIONAL MATCH (pa:Passage)-[:ABOUT_CONCEPT]->(e) WITH e, count(DISTINCT pa) AS ac
OPTIONAL MATCH (pm:Passage)-[:MENTIONS_ENTITY]->(e) WITH e, ac, count(DISTINCT pm) AS me
RETURN count(*) AS entities, sum(CASE WHEN ac=0 THEN 1 ELSE 0 END) AS ac_zero,
       max(abs(ac-me)) AS worst_absolute_gap
```

**Baseline: `163 / 74 / 965`** (the 965 is `praise (stoma)`, 1,367 vs 402).

### F3 — MENTIONS_LEMMA and MENTIONS_ENTITY-to-Devata are the same 9,000 facts, and 9,992 Lemma nodes are orphans

```cypher
MATCH (p:Passage)-[:MENTIONS_LEMMA]->(l:Lemma) WITH p, count(*) AS lc
MATCH (p)-[:MENTIONS_ENTITY]->(d:Devata) WITH p, lc, count(*) AS dc
RETURN count(p) AS passages_with_both, sum(CASE WHEN lc=dc THEN 1 ELSE 0 END) AS counts_equal,
       sum(lc) AS lemma_edges, sum(dc) AS devata_mention_edges;;
MATCH (l:Lemma) WHERE NOT (l)--() RETURN count(l) AS orphan_lemmas;;
MATCH ()-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l) AS distinct_lemma_targets
```

**Baseline: `6560 / 6560 / 9000 / 9000`; orphan_lemmas `9992`; distinct_lemma_targets `39`.**
Falsified if `counts_equal < passages_with_both` (the layers have diverged and now carry
different facts), if `orphan_lemmas` drops, or if `distinct_lemma_targets` rises above 39 (the
lemma layer now covers more than deity stems).

### F4 — No TIER_C edge exists, and 736 model-extracted edges are graded TIER_D in violation of TIER_BY_LAYER

```cypher
MATCH ()-[r]->() RETURN r.knowledge_layer AS layer, r.quality_tier AS tier, count(*) AS n ORDER BY n DESC
```

**Baseline: 4 rows, including `L3_LLM_EXTRACTED / TIER_D / 736`, and no row with
`tier = TIER_C`.** Falsified by any `TIER_C` row appearing, or by the `L3 / TIER_D` row
disappearing. The paired statement is that the graph currently holds no reviewed model
knowledge:

```cypher
MATCH ()-[r]->() WHERE r.knowledge_layer='L3_LLM_EXTRACTED' RETURN r.state AS state, count(*) AS n
```

**Baseline: one row, `CANDIDATE 736`.** Any `ACCEPTED` or `REJECTED` row means human review
has begun. And the second grading violation:

```cypher
MATCH ()-[r]->() WHERE r.grade_basis STARTS WITH 'ungraded' RETURN type(r) AS t, count(*) AS n ORDER BY n DESC
```

**Baseline: 4 rows totalling 403 edges** (`EXACT_PARALLEL_OF` 256, `PARALLEL_TO` 69,
`BROADER_THAN` 39, `DEVATA_ASSOCIATED_WITH` 39). Zero rows means the provenance vocabulary
has been unified.

### F5 — All 61,861 UNSPECIFIED-evidence edges are product knowledge, including 7,048 TIER_A edges

```cypher
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED' RETURN type(r) AS t, r.quality_tier AS tier, count(*) AS n ORDER BY n DESC;;
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED'
  AND type(r) IN ['HAS_TEXT_VERSION','HAS_TRANSLATION'] RETURN count(*) AS plumbing;;
MATCH ()-[r]->() WHERE r.evidence_basis='UNSPECIFIED' AND r.quality_tier='TIER_A' RETURN count(*) AS tier_a_unspecified
```

**Baseline: 29 rows totalling 61,861; `plumbing = 0`; `tier_a_unspecified = 7048`.** Any
non-zero `plumbing` would mean I mismeasured; a drop in `tier_a_unspecified` means the
top-graded attribution layer has acquired an evidence basis.

### F6 — Evidence is 66.5% strictly verifiable in situ, and 0% for the Sāmaveda and Yajurveda

Re-run `scratchpad/agentB/verify2.py` (seed 20260909, 400 + 400 + 736 edges). **Baseline:
1,631 items, 1,085 exact (66.5%), 407 after fold, 24 concat-only, 115 not found (7.1%).
Per-Veda `script_folded`: AV 100.0%, RV 99.7%, SV 0.0%, YV 0.0%.** The single-query proxy
that would move first:

```cypher
MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t) WHERE t.script='Latin'
RETURN p.veda AS veda, count(DISTINCT p) AS passages_with_latin_text ORDER BY veda;;
MATCH (t:TextVersion) RETURN t.text_role AS role, t.accented AS accented, count(*) AS n ORDER BY n DESC
```

**Baseline: `AV 5839, RV 10552` and no SV or YV row; `SEARCH_DERIVATIVE / false / 5839` (AV
only).** An SV or YV row, or a `SEARCH_DERIVATIVE` count above 5,839, means the folded
surface the matcher relies on has been persisted for more than one corpus.

### F7 — 15 of 35 declared predicates are empty and only one is documented as such

```cypher
CALL db.relationshipTypes() YIELD relationshipType AS rt
CALL { WITH rt MATCH ()-[r]->() WHERE type(r)=rt RETURN count(r) AS c }
RETURN rt, c ORDER BY c, rt
```

diffed against `ontology.DOMAIN_RELATIONSHIP_TYPES` and `ontology.UNPOPULATED_BY_DESIGN`
(`scratchpad/agentB/contract.py`). **Baseline: 35 declared, 20 populated, 15 empty, 1
documented, 0 signature violations.** Falsified in the good direction by the empty count
falling or the documented count rising to match it; falsified in the bad direction by any
signature violation appearing. Paired label check:

```cypher
MATCH (n:Theme) RETURN count(n) AS theme_nodes;;
MATCH ()-[r:HAS_THEME]->(t) RETURN labels(t) AS target_labels, count(*) AS n
```

**Baseline: `theme_nodes = 0`, and 8 `HAS_THEME` edges pointing at
`["Concept","DomainEntity"]`.**

### F8 — Formula nesting inflates a third of formula-bearing passages

Re-run `scratchpad/agentB/formula.py` and `formula2.py`. **Baseline: 4,825 formulas, 1,039
strict substrings (21.5%), longest chain 4, 8,159 of 22,686 edges on contained formulas
(36.0%), 3,342 of 10,574 passages (31.6%) with same-passage nesting, 5,720 edges (25.2%)
attributable to it.** The single worst passage is `AVS 10.6.9` at 12 edges / 9 nested.

### F9 — 2,914 passages carry no knowledge edge at all

```cypher
MATCH (p:Passage) OPTIONAL MATCH (p)-[r]->()
WHERE NOT type(r) IN ['CONTAINS','HAS_TEXT_VERSION','HAS_TRANSLATION','HAS_QA_ISSUE']
WITH p, count(r) AS knowledge_deg
RETURN p.veda AS veda, count(p) AS passages, sum(CASE WHEN knowledge_deg=0 THEN 1 ELSE 0 END) AS zero ORDER BY veda
```

**Baseline: `AV 6590/1220`, `RV 11590/1038`, `SV 2342/531`, `YV 2015/125` — 2,914 total,
12.9%.**

### F10 — One query is 90.9% of the query set's total cost

Re-run `scratchpad/agentB/time_queries.py`. **Baseline: 48 queries, 0 errors, warm median
6.6 ms, mean 200.3 ms, p95 87.3 ms, total 9,612 ms, of which
`conceptually_similar_not_reused` is 8,738 ms (90.9%).** Falsified when the mean approaches
the median, which happens only when that one query changes.

---

## Appendix A — Disagreement ledger

Every published number I re-measured, with the verdict. "Published" means
`BASELINE_FACTS.md`, `VEDAGRAPH_KNOWLEDGE_MODEL_V2_FINAL_REPORT.md` (V2FR) or
`GRAPH_ADVERSARIAL_QA_V2.md` (AQA).

### Re-verified and agreeing (20)

| # | claim | source | my measurement |
|---|---|---|---|
| 1 | 100,780 nodes | BASELINE_FACTS | 100,780 |
| 2 | 242,147 relationships | BASELINE_FACTS | 242,147 |
| 3 | full 42-label node census | BASELINE_FACTS | all 42 exact |
| 4 | full 49-type relationship census | BASELINE_FACTS | all 49 exact |
| 5 | TIER_A 91,163 / TIER_B 149,206 / TIER_C 0 / TIER_D 1,778 | BASELINE_FACTS | exact |
| 6 | knowledge_layer L1 91,163 / L2 149,206 / L3 736 / L4 1,042 | BASELINE_FACTS | exact |
| 7 | state ACCEPTED 105,293 / CANDIDATE 736 | BASELINE_FACTS | exact |
| 8 | evidence_basis five-way split | BASELINE_FACTS | exact |
| 9 | attribution_precision per predicate (all 6 numbers) | BASELINE_FACTS | exact |
| 10 | per-Veda passages and mantras (8 numbers) | BASELINE_FACTS | exact |
| 11 | per-Veda coverage table (24 numbers, read as distinct passages) | BASELINE_FACTS | exact |
| 12 | mention degree bands 6,258 / 10,518 / 5,216 / 545 | BASELINE_FACTS | exact |
| 13 | Devata top-25 inbound degrees | BASELINE_FACTS | exact (Indra 5,234, Agni 3,675, ...) |
| 14 | zero HAS_DEVATA/HAS_RISHI/HAS_CHANDAS on SV, YV, AV | BASELINE_FACTS | exact |
| 15 | sealed artifact: 448 / 2,459 / 11 zero counters / VALIDATED / UNANNOTATED / CLAUDE_CODE_DIRECT / unattested model / 13-predicate mix | BASELINE_FACTS | exact, read from `output_seal.json` |
| 16 | sealed artifact is not projected into the graph | BASELINE_FACTS | confirmed, by run_id and predicate mix |
| 17 | 62,483 `Internal` nodes, 0 of 915 QAIssue reachable | V2FR | exact; `internal_leakage_check` returns 0 rows |
| 18 | devata_subtype UNKNOWN on 209 of 214 (97.66%); 113 classified / 101 UNSPECIFIED (47.20%) | V2FR | exact |
| 19 | ritual structure is 33 edges over 4 rites | V2FR | exact (11+6+5+4+4+3) |
| 20 | 3,643 of 4,825 formulas cross-Veda; 0 under two words | V2FR | exact; word_count range 2–8 |
| 21 | 571 AV passages contain `indra` | V2FR / AQA C2 | exact |
| 22 | "Is Indra in the AV" answers 15 | AQA C2 | exact |
| 23 | 21,246 English-only ABOUT_CONCEPT edges, graded identically | AQA C3 | exact, and the partition is perfect |
| 24 | 14 dead declared predicates + MUSICALIZED_AS | AQA | exact list |
| 25 | Region / RishiFamily / Theme have 0 nodes; HAS_THEME fires at a Concept | AQA | exact |
| 26 | 806 `primary_parallel_text_divergence` QAIssues | V2FR | exact |

(Numbered to 26; several published figures are bundles of many numbers.)

### Could not reproduce (6)

| # | claim | source | my measurement | assessment |
|---|---|---|---|---|
| D1 | *"UNSPECIFIED = 61,861 ... mostly HAS_TEXT_VERSION/HAS_TRANSLATION plumbing"* | BASELINE_FACTS L50 | **0** of 61,861 are those types; all 61,861 are product knowledge, 7,048 of them TIER_A | **refuted, and the conclusion inverts** — this is the single most consequential disagreement in the audit |
| D2 | *"No DomainEntity exists ... Confirms Indra, Varuna, Rudra, Visnu, Mitra have no theonym mention layer"* | BASELINE_FACTS L72-73 | the 0-row probe reproduces, but those five deities carry 3,240 `MENTIONS_ENTITY` edges on `:Devata` nodes, which the ontology declares a legal range | **premise reproduces, conclusion refuted for RV.** The gap is cross-Veda, not absolute |
| D3 | *"TIER_C = 0: the graph contains no accepted model-derived knowledge"* | BASELINE_FACTS L75 | 736 model-derived edges exist, graded TIER_D against `TIER_BY_LAYER`'s TIER_C | **misdescribed** — the layer exists and is mis-graded |
| D4 | *"heaven–earth 499 vs 262"* as the ABOUT_CONCEPT/mention divergence illustration | V2FR §65.3 | heaven 1,659 vs 1,206; earth 1,206 vs 742. 499 and 262 appear on no entity | **not reproducible.** True divergence is 3.3x larger |
| D5 | *"1,103 of 4,825 formulas are strict substrings of another"* | V2FR §30, §65.7 | 1,039 on `normalized`, 984 on `display_form` | **not reproducible on any field.** Carried from V1 unremeasured |
| D6 | *"4,990 mantras uncovered, mean degree 1.884"* | V2FR §65.2 | 4,990 over all 20,210 mantras; 1.884 over the 15,220 *covered* passages only. On one population: 4,990 and 1.4189 | **each reproduces, on a different denominator.** Presented together they read 33% denser than the layer is |

### Internal contradictions between V2-era documents (3)

| # | statement A | statement B |
|---|---|---|
| X1 | V2FR §66: the ontology boundary is *"35 V2 predicates ... and a declared-but-empty `MUSICALIZED_AS`"* | AQA §9: *"15 declared V2 rel types with 0 edges, of which 1 documented — 14 dead weight."* I measure 15 and 1. |
| X2 | V2FR §65.8: the `MITRAVARUNAU` decomposition is unadjudicated, *"one of the two needs a human decision"* | AQA §7: *"Mitra vs Varuṇa vs Mitrāvaruṇau — YES, CLEAN"*, citing the same `COMPOSED_OF` decomposition as proof. The node itself carries `is_composite: false` alongside two `COMPOSED_OF` edges. |
| X3 | V2FR READY table: interpretive claims are *"all TIER_D and permanently CANDIDATE"* | All 22 claim edges have `state = null`; the only 736 CANDIDATE edges in the graph are the L3 semantic ones. `asserted_by = ""` on all 6 claims and `ASSERTED_BY` has 0 edges. |

### New, in no prior report (5)

| # | finding | measurement |
|---|---|---|
| N1 | `MENTIONS_LEMMA` and `MENTIONS_ENTITY`-to-`Devata` are the same 9,000 facts; 9,992 of 10,031 `Lemma` nodes are orphans | 6,560 passages, identical per-passage counts on all of them, 0 in either symmetric difference; `distinct_lemma_targets = 39` |
| N2 | The L3 semantic layer covers YV (415) and AV (321) and zero RV/SV, from an unsealed run | 364 distinct passages, 1.6% of the corpus |
| N3 | 736 L3 edges violate `TIER_BY_LAYER`; 403 more are TIER_D by grader failure, including all 256 RV-internal exact parallels | see §2 |
| N4 | `theonym_ambiguous` is decided per orthographic variant (`agnim` true / `agniṃ` false) and lifts the Agni-attribution rate by only 10.4 points over unflagged | 58.6% vs 48.2% against an 18.6% base |
| N5 | Formula nesting double-counts on 31.6% of formula-bearing passages (5,720 edges), not merely 21.5% of nodes | worst case `AVS 10.6.9`, 12 edges / 9 nested |

Also new, minor: three ghost tokens in the store (`RishiFamily`, `SourceArtifact`,
`SHARES_FORMULA_WITH`) making the enumerable schema 44/50 rather than 42/49; the Sāmaveda has
zero translations; SV and YV store Devanagari only, so V2's Latin `indra` probe could not have
counted them (664 further passages); 2,914 passages carry no knowledge edge; 116 degree-1
product nodes including all 13 `Epithet` and 77 of 79 `DerivedMetric`; Q37 is served by no
named query.

---

## Appendix B — Reproduction

Scratch harnesses, all read-only:

| file | purpose |
|---|---|
| `scratchpad/agentB/q01`–`q29*.cypher` | the Cypher batches quoted above, in order |
| `scratchpad/agentB/time_queries.py` | §4 timings; imports `QUERIES`, 3 reps each |
| `scratchpad/agentB/contract.py` | §6.7 ontology-versus-live reconciliation |
| `scratchpad/agentB/sig.py` | signature violations, reciprocal edges, duplicate edges |
| `scratchpad/agentB/formula.py`, `formula2.py`, `formula3.py` | §6.6 containment measurement |
| `scratchpad/agentB/verify_evidence.py`, `verify2.py` | §6.5 evidence verification, seed 20260909 |

Verified no-write: the audit issued only `MATCH` / `RETURN` / `CALL db.*` /
`CALL dbms.components()` statements. Node and relationship counts at the end of the audit are
100,780 and 242,147, identical to the start.
