# VedaGraph V3.1 — Final Independent Adversarial Pass

**Agent F. Strictly read-only.** No `CREATE`/`MERGE`/`SET`/`DELETE`/`REMOVE` was executed,
no source file was edited, no data file was edited. This document is the only file written.

| Field | Value |
| --- | --- |
| Auditor role | Agent F — final independent adversarial pass. Implemented none of this. |
| Branch / commit | `semantic-pilot-v1`, working tree clean at audit start |
| Database | `bolt://localhost:7687`, Neo4j 5.26, APOC + GDS |
| **Graph measured** | **108,777 nodes / 266,757 relationships** (see F-13 — this moved during the audit) |
| Query catalogue | 90 named queries, all executed |
| Integrator gate | `scripts/check_live_invariants.py`: 0 failing, 3 warning, 17 checked |
| Method | Rows, not reports. Value spaces enumerated, not grepped. Worst case per alias / per entity, never the average. |

## Verdict

| Severity | Count |
| --- | --- |
| **CRITICAL** | **1** |
| MAJOR | 7 |
| MINOR | 6 |

**The gate for this session was 0 CRITICAL. It is not met.** One finding qualifies:
`deities_by_axis` returns `UNSPECIFIED` as the top-ranked functional axis of the Vedic
pantheon on two claimed-cleared questions, while its own caveat states that those 101
deities "do not appear here". The fix is a one-line `WHERE` clause that makes the query do
what its caveat already promises.

Everything else is MAJOR or below, and the graph's factual layers — `Work.scope`, the
attribution/mention separation, the formula twins, the assertion layer separation, the
QAIssue reversal, the ṛṣi-family evidence chain — held up under direct row-level attack.

---

## The CRITICAL

### F-1 (CRITICAL) — `UNSPECIFIED` tops the deity-axis leaderboard on Q38 and Q46, and the caveat denies it

`UNSPECIFIED` is not a null. It is a materialised `:DeityAxis` node with 101 `HAS_AXIS`
edges into it, so it sorts like a real functional role — and it wins, by 5×.

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
RETURN ax.axis AS axis, count(dv) AS deities
ORDER BY deities DESC LIMIT 6
```

```
UNSPECIFIED       101      <-- rank 1
WARRIOR            20
TERRESTRIAL        18
FIRE_MEDIUM        14
RITUAL_SUBSTANCE   13
ATMOSPHERIC        12
```

`deities_by_axis` serves **Q20, Q38, Q41, Q46**. Q38 and Q46 are both on the claimed-cleared
list. Its `cypher` has no filter on `ax.axis`, and its caveat reads:

> "Axes are curated interpretation (TIER_D), not source statements. 101 of 214 deities are
> deliberately [UNSPECIFIED] and **do not appear here**."

They appear at rank 1. The caveat asserts the negation of what the query returns, so even
the reader who *does* read the caveat is misled — which removes the usual "a caveat is not
a defence" argument in both directions.

The bucket is also not a bucket of deities. Its members include humans, animals, objects
and a hymn title, all typed `:Devata`:

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(:DeityAxis {axis:'UNSPECIFIED'})
RETURN dv.display_label, dv.devata_subtype, dv.is_classified LIMIT 12
```

```
the All-Gods · Svanaya Bhavayavya · the horses · Sasiyasi, queen of Taranta · the gods
the bestower of goods · the steeds · the married pair · the sacrifice and the sacrificer
the two bow-tips · praise of the gift of Sudas son of Pijavana · Brbu the carpenter
```

All carry `devata_subtype = 'UNKNOWN'` and `is_classified = false`, so the graph knows they
are unclassified — the query simply does not ask.

**Why this is CRITICAL and not MAJOR.** It is a wrong top-ranked member (the first canonical
`MISLEADING` shape) *and* wrong class membership (the third), on two questions the reports
claim cleared, delivered by the obvious named query, with a caveat that actively denies it.

**And the same defect on the same question was explicitly claimed fixed.**
`V3_1_CLOSURE_STRIKE_FINAL_REPORT.md` §9 lists Q38 under root cause `INTERPRETATION_LEAK`
with the fix "Composites excluded from the per-deity leaderboard" and the evidence "was
topped by Mitra-Varuṇa with 0 attributions; now Indra (2,869) and Agni (1,988)". That is
true of `deity_widest_range`, which I ran and which is correctly topped by Indra. Q38 has
**two** serving queries. The second one, `deities_by_axis`, is a leaderboard still topped by
a non-answer — the identical root-cause class, on the identical question, left unfixed
because the fix was applied per query rather than per question.

This is also the third instance in this session of the pattern the closure report itself
names: "A shipped caveat asserted something the same database disproved" (§8, on
`agni_and_indra_together`). F-4 and F-5 are the other two, both found after that fix landed.

**Fix, one line:** add `WHERE ax.axis <> 'UNSPECIFIED'` to `deities_by_axis`. The count is
already reported honestly in the caveat; the query just has to match it. This is the single
thing I would fix first.

---

## MAJOR findings

### F-2 (MAJOR) — the flagship four-Veda deity query never consumes `DEITY_PROBABLE`, so the artifact zeros are still on the page

`devatas_named_in_all_four_vedas` serves **Q1, Q21, Q34, Q36, Q44**. Its `certain` column is
`count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_CERTAIN' THEN p END)`. The new
three-way scheme is not used at all — `DEITY_PROBABLE` appears nowhere in the query.

```cypher
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata)
WITH dv, p.veda AS veda, count(DISTINCT p) AS passages,
     count(DISTINCT CASE WHEN m.referent_certainty='DEITY_CERTAIN' THEN p END) AS certain
WITH dv, collect([veda,passages,certain]) AS per_veda, count(veda) AS vedas,
     sum(passages) AS total, sum(certain) AS total_certain
WHERE vedas = 4 AND dv.display_label IN ['Agni','Indra']
RETURN dv.display_label, total, total_certain, per_veda
```

```
Agni   2543   831    [[AV,476,0],[YV,276,0],[SV,187,0],[RV,1604,831]]
Indra  3566  3566    [[AV,635,635],[YV,221,221],[SV,405,405],[RV,2305,2305]]
```

The obvious reading is that Agni's entire non-Rigvedic presence is unverified while Indra's
is fully verified. That is an artifact of the annotation layer (only the RV has the lemma
annotation; outside it `CERTAIN` is granted only to non-homonym names), not a fact about the
text — and `DEITY_PROBABLE` was created this session precisely to remove it: Agni has 170
AV / 97 YV / 82 SV `PROBABLE` edges that this query cannot see.

Not escalated to CRITICAL only because none of Q1/Q21/Q34/Q36/Q44 is on the claimed-cleared
list. The mitigation is product-safe: add a `probable` column, or a `default_scope` column
over `CERTAIN + PROBABLE`, as `deity_mention_surface_forms` already does per form.

### F-3 (MAJOR) — the affliction inventory is still topped by a demon; `condition_kind` was never written

`V3_1_MISLEADING_DIAGNOSIS.md` item 15 recorded this as a live `MISLEADING` defect, assigned
to `AGENT_D_RISHI_MATERIAL` at cost XS, with the fix "either two labels or one
`condition_kind` property". **The property does not exist.** Enumerated over the full key
space of all 36 `Condition` nodes rather than grepped for:

```cypher
MATCH (c:Condition) UNWIND keys(c) AS k RETURN k, count(*) AS n ORDER BY n DESC
```

18 keys, none of them `condition_kind`, and no second label. The inventory is unchanged:

```cypher
MATCH (c:Condition)
RETURN c.display_label, size([(p)-[:MENTIONS_ENTITY]->(c)|p]) AS mentions
ORDER BY mentions DESC LIMIT 5
```

```
demon (rakṣas)       160   <-- rank 1 of the "afflictions"
consumption (yakṣma)  89
witchcraft (kṛtyā)    65
poison (viṣa)         63
fever (takman)        33
```

`conditions_treated` asks "Which **afflictions** do passages address" and serves Q12, Q15,
Q47. It returns causes and agents — `rakṣas`, `kṛtyā`, `abhiśasti`, `durhārd` — as
afflictions. Wrong class membership, on the third canonical `MISLEADING` shape. MAJOR rather
than CRITICAL because the diagnosis left it explicitly open and assigned; no report claims
it cleared.

### F-4 (MAJOR) — `conditions_treated`'s caveat asserts the opposite of what the graph holds

This one is new; nobody recorded it. The caveat on `conditions_treated` (Q12, Q15, Q47):

> "There is deliberately **no separate 'fever' entity**: takman- forms sit in
> YAKSMA-DISEASE because splitting them would have put 39% of the paradigm under 'fever'
> and 61% under 'disease' invisibly."

The graph holds `VG:CONCEPT:TAKMAN-FEVER`, display label **"fever (takman)"**, with 33
`MENTIONS_ENTITY` and 33 `TREATS` edges, alongside a *separate* `VG:CONCEPT:YAKSMA-DISEASE`
at 89. The diagnosis itself records the split as done ("`takman` is now its own entity … the
baseline's decisive defect is fixed"). The caveat was not updated and now states a falsehood
about the data it annotates. A reader who trusts it will believe no fever entity exists
while the query is returning one two rows above.

### F-5 (MAJOR) — `rivers_and_tribes`' caveat understates river coverage by 20×

The zero itself is real and I confirmed it. The figure justifying it is not.

```cypher
MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(r:River)
RETURN count(m) AS river_mentions, count(DISTINCT p) AS passages
```
→ `river_mentions: 249, passages: 243`

The caveat says: "42 tribe mentions and **12 river mentions** exist, and no mantra carries
one of each." Tribes are exactly 42 — correct. Rivers are **249**, not 12, dominated by
`river (sindhu)` at 236. A reader is told rivers are barely present in the corpus when they
are present in 243 passages. This is the same defect class as ROI Task 13 ("stale caveat
figures"), which was executed but did not reach this caveat.

The zero is genuine: `MATCH (p)-[:MENTIONS_ENTITY]->(:River), (p)-[:MENTIONS_ENTITY]->(:Tribe)`
returns 0 rows, and all 249 river mentions land on `:Mantra` nodes so it is not a granularity
artifact.

### F-6 (MAJOR) — `passages_used_for_a_rite` attaches an Atharvavedic recall figure to Rigvedic rows

The Wave 2 report's stated design principle is that recall must be a column, "because the
frozen criterion requires the figure and the reader who runs the obvious query never sees a
caveat." The column is rite-level, the rows are per-Veda, so the scoping is wrong:

```cypher
MATCH (p:Passage)-[u:USED_FOR_RITE]->(rite:SocialRite)
WHERE u.attribution_precision IN ['PER_PASSAGE']
RETURN rite.display_label AS rite, p.veda AS veda, count(DISTINCT p) AS passages,
       rite.strict_recall_against_locus AS recall, rite.locus_book AS locus
ORDER BY rite, passages DESC
```

```
marriage (vivāha)   AV   25   0.0993   K14
marriage (vivāha)   RV   16   0.0993   K14      <-- RV row, AV kāṇḍa, AV-only recall
house building      AV   30   0.0611   K09
assembly (sabhā)    AV   12   null     null
childbirth (sūṣā)   AV   11   null     null
funerary rites      AV    9   null     null
```

The Rigvedic marriage row carries `locus_book = 'K14'` — an Atharvavedic kāṇḍa — and a recall
of 9.93% measured only over AV tags. "RV marriage recall against AV kāṇḍa 14" is a category
error presented as a measurement. Four of the six rites carry no recall at all, so the "recall
is a column" guarantee holds for two rites out of six.

Not CRITICAL: the underlying counts are right, and the mismatch is visible in the same row
(an AV kāṇḍa printed beside `veda: RV`). Mitigation: null the recall/locus columns on rows
whose veda is not the locus's veda, or aggregate the rite rows.

### F-7 (MAJOR) — `ABOUT_CONCEPT` carries 1,468 edges from a superseded run that a rebuild did not sweep

The `SHARES_ENTITY_VOCABULARY_WITH` bug found earlier this session is not the only one.

```cypher
MATCH ()-[r:ABOUT_CONCEPT]->() RETURN r.run_id AS run_id, count(*) AS c ORDER BY c DESC
```

```
vedagraph-graph-enrichment-v1:concepts:42e33f1e03a7310e   24969
vedagraph-graph-enrichment-v1:concepts:11f3aaad2a292373    1468
```

I tested the two obvious innocent explanations and both fail:

- **Not duplicates.** `MATCH (a)-[r1:ABOUT_CONCEPT]->(c)<-[r2:ABOUT_CONCEPT]-(a) WHERE r1.run_id <> r2.run_id RETURN count(*)` → **0**. The node pairs are disjoint.
- **Not a complementary pass.** Both runs use the same `method` values
  (`concept-alias-v1:sanskrit-token`, `…:english+sanskrit-token`), the same `quality_tier`
  (`TIER_B`), the same `knowledge_layer` (`L2_DETERMINISTIC_DERIVED`), the same
  `"surface":"script_folded"` evidence generation, and both span all four Vedas. 13 concepts
  carry edges from both run_ids.

Two runs of one identical extractor over one identical population, with disjoint results and
no sweep, is the signature of surviving output from a superseded build. Either the 1,468 are
stale — in which case the concept layer over-reports by 5.6% — or the sweep predicate is
correct and the second run_id needs a recorded reason it exists. Neither is currently
answerable from the graph, which is itself the defect.

### F-8 (MAJOR) — the entire ṛṣi-family layer is unreachable from the query catalogue

87 `RishiFamily` nodes and 305 `BELONGS_TO_FAMILY` edges were built as ROI Task 10, scored
against Q2/Q19/Q26/Q62. **Not one of the 90 named queries references `BELONGS_TO_FAMILY` or
`RishiFamily`.** Verified by scanning `q.cypher` for both tokens across `QUERIES` — zero
hits. The report's own §6 supplies a "Written spec for the integrator —
`src/vedagraph/domain/queries.py`"; the spec was not implemented. The layer is correct (see
F-14) and unlocks zero benchmark questions as delivered.

The five queries that do traverse `HAS_RISHI` (`rishis_invoking_deity`,
`rishis_invoking_deity_strict`, `deities_through_common_rishis`, `rishi_layer_reach_by_veda`,
`attribution_precision_audit`) all work at the individual-ṛṣi level, so no family question is
answerable through the product surface.

---

## MINOR findings

### F-9 (MINOR) — four claimed-cleared questions have no named query at all

`questions_served` covers **Q86, Q87, Q88, Q90** with nothing. Verified by intersecting every
`q.serves` tuple against the claimed-cleared list:

```
Q86: *** NO NAMED QUERY SERVES THIS CLAIMED-CLEARED QUESTION ***
Q87: *** NO NAMED QUERY SERVES THIS CLAIMED-CLEARED QUESTION ***
Q88: *** NO NAMED QUERY SERVES THIS CLAIMED-CLEARED QUESTION ***
Q90: *** NO NAMED QUERY SERVES THIS CLAIMED-CLEARED QUESTION ***
```

`V3_1_DEITY_LAYER.md` §6 says Q86 is "resolved for the named failure" and treats Q87/Q88 as
addressed alongside Q45/Q46; `V3_1_WAVE2_RITUAL_DEPTH.md` §2 says "Q90 — the hotar.
Cleared." The underlying graph work for all four is real and I verified Q90's part of it
(11 `RitualRole` nodes, `hotṛ` 300 / `potṛ` 19 after the split). But `serves` is the
measurement instrument, so a benchmark run driven by it will score these four as uncovered,
and a reader cannot reach the clearance. MINOR rather than MAJOR because the fix is a
`serves` tuple edit, not new work.

### F-10 (MINOR) — 11 `BELONGS_TO_FAMILY` edges state a vṛddhi derivation where no vṛddhi occurred

The layer's stated rule is "a token … equals one of the finitely many inflected surfaces of a
**vṛddhi** patronymic." Four family nodes carry a `vrddhi_derivation` string in which the
first vowel is unchanged, so the derivation named is not vṛddhi:

```cypher
MATCH (f:RishiFamily) WHERE f.patronymic_iast STARTS WITH substring(f.eponym_iast,0,3)
RETURN f.eponym_iast, f.patronymic_iast, f.vrddhi_derivation, f.member_count
ORDER BY f.member_count DESC
```

```
atharvan  → atharvaṇa   "vṛddhi patronymic: atharvan → atharvaṇa"    6 members
vāmadeva  → vāmadevya   "vṛddhi patronymic: vāmadeva → vāmadevya"    3
gāthin    → gāthina     "vṛddhi patronymic: gāthin → gāthina"        1
śyāvāśva  → śyāvāśvi    "vṛddhi patronymic: śyāvāśva → śyāvāśvi"     1
```

(`sthūra → sthaura` also matched my prefix test but *is* vṛddhi, ū→au.) These are real
patronymics — `-ya` and `-i` are legitimate patronymic suffixes — so the *memberships* are
defensible and I am not calling them fabrication. What is wrong is the stated mechanism on
11 edges, quoted verbatim on the edge as `derivation`. Notably `ATHARVANA` is keyed on the
non-vṛddhi surface with the vṛddhi form demoted to `source_variants: ['ātharvaṇa']` — the
table has that pair backwards.

### F-11 (MINOR) — `source_variants` is an undisclosed emendation channel, and it emends what §4 refused to emend

Four families carry a `source_variants` entry:

```cypher
MATCH (f:RishiFamily) WHERE size(f.source_variants) > 0
RETURN f.patronymic_iast, f.source_variants, f.member_count ORDER BY f.member_count DESC
```

```
ātreya      ['atreya']      42
atharvaṇa   ['ātharvaṇa']    6
paurukutsa  ['paurukutsya']  2
śaunaka     ['śāunaka']      1
```

The five-step derivation rule in §1 lists `SURFACE_INDEX`, `DECLINED_INDEX`, the fused split
and one explicit compound table. It does not mention a variant channel. Consequence: the row
`atreyaḥ` (short initial *a*) becomes a member of `ātreya` via the variant `atreya` — while
§4 declines `bhāgavo nemaḥ` and four others *by name* on the stated principle that "'one
vowel out' is exactly the distance between `bharadvāja` and `bhāradvāja`, and emending here
would license emending anywhere." `atreya → ātreya` is one vowel out and was emended. The
code's own docstring for the field says variants hold "spellings the *source* uses … never a
spelling this module guessed", which is the right rule; the report does not disclose that the
rule exists or that it fires.

### F-12 (MINOR) — 17 memberships make a bare patronymic a member of the family it names

```cypher
MATCH (r:Rishi)-[e:BELONGS_TO_FAMILY]->(f:RishiFamily)
WHERE r.personal_name_iast IS NULL OR trim(r.personal_name_iast) = ''
RETURN r.label_iast, r.registry_namespace, f.patronymic_iast, r.occurrence_count
ORDER BY r.occurrence_count DESC
```

17 rows, worst first: `āṅgirasa` (32 sūktas) → family `āṅgirasa`; `bhāradvāja` (30) →
`bhāradvāja`; `vaikhānasa` (14) → `vaikhānasa`; `āgastya` (11); `atharvaṇa` (7); `ātreya`
(7); then `Gārgya`, `Kāṇva`, `Kāuçika` ×2, `Bhārgava` ×3, `gautama`, `vaidarbhi`, `atreyaḥ`,
`vasiṣṭhaputrāḥ`.

I checked the sharper form of this hazard and it is clean — no ṛṣi node is the *eponym* of
the family it joins (`toLower(r.label_iast) = toLower(f.eponym_iast)` → 0 rows), and no
`is_seer = false` row has a family (→ 0 rows). The residual is that a family-level ascription
with no personal name is projected as one individual member, so it is double-counted: once as
a ṛṣi with 32 sūktas and once inside `member_count = 51`. Reading "a member of this family
whose personal name the index withholds" is defensible; the graph just cannot distinguish it
from a named person. No named query surfaces it today (see F-8), which is why this is MINOR.

### F-13 (MINOR) — the graph was mutated during the audit that was promised a frozen graph

I observed `SHARES_ENTITY_VOCABULARY_WITH` change `run_id` between two reads in my own
read-only session, on the same 2,141 edges:

```
first read:  entity-vocabulary-overlap-v3.1:74a00b352f4d480f855c54ff684ff35f   2141
later read:  entity-vocabulary-overlap-v3.1:330652ddf9d74ed98e2311cb7e020287   2141
```

Relationship count moved 266,754 → 266,757 over the same interval and then held stable, and
`check_live_invariants.py` independently reported 266,757. So the vocabulary-overlap layer
was rebuilt mid-audit. My earliest measurements were therefore taken against a marginally
different graph than my later ones; nothing in this report depends on the three edges, but
the "frozen for the duration of your audit" premise did not hold and a future audit should
verify it rather than assume it.

### F-14 (MINOR) — the accidental-Cartesian shape is still undefended, though the catalogue is safe

All 90 named queries are safe (see the timing table below). The *shape* is not. I made it
blow up on the first attempt, in 4.5 seconds:

```cypher
MATCH (a:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Passage)
WHERE a.veda <> b.veda
WITH a, b, collect(DISTINCT e.entity_key) AS shared
WHERE size(shared) >= 3 AND NOT (a)-[:SHARES_ENTITY_VOCABULARY_WITH]-(b)
RETURN count(*) AS pairs
```

```
Neo.TransientError.General.MemoryPoolOutOfMemoryError:
The allocation of an extra 2.0 MiB would use more than the limit 1.4 GiB.
```

This is the natural query for "which cross-Veda passages share vocabulary but are not
already linked", and there is no degree bound anywhere to stop it. The `SHARES_ENTITY_VOCABULARY_WITH`
edge (2,141, pre-computed) *is* the intended mitigation and is good design — Task 8 fixed the
one named query rather than the shape, which was the right call for the timebox. Recorded so
the residual is not forgotten.

---

## Attack classes: what I ran and what I found

### 1. Misleading benchmark answers — 20 claimed-cleared questions

I resolved each claimed-cleared question to its serving queries via `q.serves`, executed all
of them, and read the top row of each. Findings: **F-1 (CRITICAL, Q38/Q46)**, F-6 (Q13/Q60),
F-9 (Q86/Q87/Q88/Q90 uncovered). Clean: Q5, Q22, Q28, Q30, Q37, Q43, Q45, Q46 (except the
axis row), Q49, Q72, Q77, Q81, Q96.

Two clean results worth naming because I expected them to break:

- **Q43** — the claim was that the cautious path no longer re-zeroes Rudra outside the RV.
  Verified per Veda: `PROBABLE` present in all four (RV 24, AV 13, YV 12, SV 2). Hazard
  genuinely removed.
- **Q45/Q46** — `deity_mention_surface_forms` returns `certainty` **per surface form** rather
  than aggregating, which is the right shape and puts the worst alias in the reader's hand.
- **Q86** — the closure report claims `EPITHET_VARIANT_OF` took fire from 5 personifications
  to 1. Verified live: `fire (agni)` → **1** (`Agni`). All six `EPITHET_VARIANT_OF` edges are
  real epithet-to-base pairs (`Agni Jatavedas`, `Agni Pavamana`, `Agni the slayer of demons`,
  `the self of Agni` → `Agni`; `Soma Pavamana` → `Soma`; `Sasarpari, the Voice` → `Vac`).
  The one row above 1 is `sun (sūrya)` at 3 — `Savitr`, `Surya`, `Surya daughter of Savitr` —
  which is the merge the report explicitly **refused** as three distinct figures, and the
  refusal is correct. Q86's substance is genuinely fixed; only its `serves` mapping is
  missing (F-9).

### 2. Ambiguous theonym leakage

`referent_certainty` value space enumerated, not grepped:

```cypher
MATCH ()-[m:MENTIONS_DEVATA]->() RETURN m.referent_certainty AS rc, count(*) AS c ORDER BY c DESC
```
→ `DEITY_CERTAIN 8340 / DEITY_AMBIGUOUS 6806 / DEITY_PROBABLE 2019`, total 17,165, **0 without
the property**. Matches the brief exactly. No fourth value, no null.

Per deity per Veda for all ten named deities, `CERTAIN / PROBABLE / AMBIGUOUS`: my
measurements reproduce `V3_1_DEITY_LAYER.md` §3's table **cell for cell**. The residual zeros
under the new `CERTAIN + PROBABLE` default are real and are exactly the ones the report names
and refuses to inflate:

```
Pṛthivī SV  0/0/26      Uṣas YV  0/0/14      Vāc AV 0/0/103
Vāc SV  0/0/25          Vāc YV   0/0/47      Āpaḥ SV/YV/AV all 0/0/x
```

That is honest, not hidden: `mention_verdict` types them `INSUFFICIENT_EVIDENCE` and the
report enumerates all 21 such cells. **No default query returns an AMBIGUOUS-driven answer** —
`theonym_ambiguous_mentions` is explicitly the exploratory query and labels its column
`ambiguous_mentions`.

The leakage is the opposite of what the brief anticipated: the problem is not AMBIGUOUS
getting in, it is `PROBABLE` never getting out — **F-2**.

Worst alias, reported rather than averaged: `SURYAH/sūrya` at 2/3 precision over 71 live
edges, Wilson 0.21–0.94. The report names it, names the single false positive by ID
(`TMG-0427`, SV UTTARA 1.2.16.2), and states the exposure is not closed. I confirm the 71
edges exist and that no edge property carries the pre-consonantal share needed to filter
them, so the exposure is real and correctly described.

### 3. Scope confusion

All four `Work` nodes carry `scope`, `completeness`, `excluded_corpora`, `rights` and
`scope_evidence`. I checked every quantitative claim in every `completeness` string against
rows. **All correct, to the digit:**

```cypher
MATCH (m:Mantra) OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
WITH m.veda AS veda, m, count(t) AS nt
RETURN veda, count(m) AS mantras, sum(CASE WHEN nt>0 THEN 1 ELSE 0 END) AS with_translation,
       round(100.0*sum(CASE WHEN nt>0 THEN 1 ELSE 0 END)/count(m),1) AS pct
```

```
AV 5839 / 4878 / 83.5    RV 10552 / 10502 / 99.5    SV 1844 / 0 / 0.0    YV 1975 / 1903 / 96.4
```

Claimed: AV 83.5%, RV 99.5%, SV zero, YV 96.4%. Exact.

The two per-Veda attribution claims also hold exactly — YV "every one of this work's 2,240
seer attributions is source-stated" and AV "every one of this work's 5,084 … is a sūkta label
projected downward":

```
AV CONTAINER_INHERITED 5084 | RV CONTAINER_INHERITED 10093, PER_PASSAGE 472 | YV PER_PASSAGE 2240
```

Canonical-citation coverage is 100% in all four. **No scope statement is false or
unsupported.** This is the strongest layer in the audit.

On Sāmavedic zeros: the SV is well covered in the entity layer (2,161 mentions over 1,306 of
1,844 passages, 70.8%), so an SV zero there is meaningful rather than an absent layer. The SV
has zero translations and zero seer attributions, and the SV `Work.scope` states the
translation fact in terms — "an SV zero in any translation-derived layer is an absent layer,
not an absent text" — but does **not** mention the absent seer layer. Recorded as an
observation rather than a finding, because no named query returns a bare SV seer zero without
a caveat that mentions SV (`deities_through_common_rishis` and `rishi_layer_reach_by_veda`
both do).

### 4. Attribution versus mention

```cypher
MATCH (p:Passage)-[h:HAS_DEVATA]->() RETURN p.veda AS veda, count(*) AS c
```
→ `RV 10558` and nothing else. `HAS_DEVATA` is RV-only as claimed.
`HAS_DEVATA_ASCRIPTION` → `AV 5385`, 100% `CONTAINER_INHERITED`.
`MENTIONS_DEVATA` spans all four (RV 10,284 / AV 3,582 / YV 1,964 / SV 1,335).

`HAS_DEVATA` splits `CONTAINER_INHERITED 8329 / PER_PASSAGE 2229`, so the inheritance is on
the edge and filterable. `agni_and_indra_together` (Q5) returns `layer` as a column with the
value `'HAS_DEVATA (Anukramani ascription)'` — the conflation is named in the output rather
than hidden. **No query conflates them.** All 17,165 `MENTIONS_DEVATA` edges land on `:Mantra`
nodes, so no container-inherited mention is presented as per-verse. Clean.

### 5. PAIR/GROUP decomposition

14 of 214 `Devata` carry `is_composite = true`. Every one has `COMPOSED_OF` components that
exist as `Devata` nodes and match its own display label:

```
Indra and Agni → [Indra, Agni] (157 mentions) · Mitra and Varuna → [Mitra, Varuna] (152)
Indra and Vayu → [Vayu, Indra] (29) · 11 more, all 0 mentions
```

**No decomposition is unsupported.** **No composite tops any per-deity leaderboard** — the
mention leaderboard runs Indra 3566, Agni 2543, Soma 1512, the Waters 761, …, with the first
composite ("Indra and Agni", 157) around rank 20. Minor observation: 11 of the 14 composites
have zero mentions, so the decomposition is real but inert for those.

### 6. Translation-derived claims

`evidence_basis` value space enumerated across every relationship in the graph:

```
SANSKRIT 110627 · STRUCTURAL 85528 · SOURCE_METADATA 51147 · MIXED 13694
TRANSLATION 3620 · SHARED_REGISTRY_ENTITIES 2141
```

The 3,620 translation-derived edges are confined to `HAS_SEMANTIC_ASSERTION` (2,459) plus its
`ASSERTION_TARGET`/`ASSERTION_PREDICATE`/`ASSERTION_AGENT` satellites — and they are
**100% Rigvedic**:

```cypher
MATCH (p:Passage)-[r]->() WHERE r.evidence_basis='TRANSLATION'
RETURN type(r) AS t, p.veda AS veda, count(*) AS c
```
→ a single row: `HAS_SEMANTIC_ASSERTION, RV, 2459`.

**No Sāmavedic answer is translation-dependent**, because the SV has no assertion layer at
all. Separately: **zero of the 90 named queries traverse `HAS_TRANSLATION` or `:Translation`**,
so no catalogue answer rests on Griffith's English. The concept layer's method space contains
no English-only method (`english+sanskrit-token` is graded `MIXED`; there is no
`english-token`), confirming the V1 English-only assertions were genuinely retired. Clean.

### 7. RishiFamily false inference

The hardest layer, attacked five ways.

- **Evidence chain.** All 305 edges carry all eight required properties. `source_token` is a
  substring of `evidence` on 302 of 305; the three exceptions are the AV orthography fold the
  rule declares (`Kāuçika`→`kauśika`, `Vāidarbhi`→`vaidarbhi`) and are legitimate.
- **Method mix** matches the report: 290 token-equality, 14 fused-split, 1 explicit-descent.
- **Eponym in his own family** → 0 rows. **Non-seer with a family** → 0 rows.
- **`member_count` drift** → 0 rows.
- **Name resemblance.** I dumped every distinct `source_token` per family (87 groups) and
  inspected the ones in non-initial position (22 rows) individually. Every one is a genuine
  patronymic in patronymic or apposition position. `praskaṇvaḥ` matching `kaṇva` as a
  substring is a test artifact, not an edge: the actual edge is licensed by the separate
  token `kāṇvaḥ` in `kāṇvaḥ praskaṇvaḥ`.

**I found no membership resting on name resemblance.** The two residuals are F-10 (11 edges
misdescribe the grammatical mechanism) and F-12 (17 bare-patronymic self-memberships) —
neither is fabrication. The 113 non-seer rows are correctly excluded, and the account of the
`cākṣuṣa` family being retired by mark-and-sweep is consistent with the live 87.

The real defect in this layer is that it is unreachable — **F-8**.

### 8. Formula directionality

```cypher
MATCH (f:Formula)-[:MEMBER_OF_FAMILY]->(fam:FormulaFamily) WHERE NOT (fam)-[:HAS_FORMULA]->(f) RETURN count(*)
```
→ **0**. And the reverse → **0**. 2,037 each way.

Property agreement on `role`, `quality_tier`, `knowledge_layer` across the twins → **0
disagreeing**.

Count blocks against rows:
```cypher
MATCH (fam:FormulaFamily) OPTIONAL MATCH (f:Formula)-[m:MEMBER_OF_FAMILY]->(fam)
WITH fam, count(f) AS actual_members,
     sum(CASE WHEN m.role='CORE' THEN 1 ELSE 0 END) AS actual_core,
     sum(CASE WHEN m.role='VARIANT' THEN 1 ELSE 0 END) AS actual_variant
WHERE fam.member_count <> actual_members
   OR (fam.core_count IS NOT NULL AND fam.core_count <> actual_core)
   OR (fam.variant_count IS NOT NULL AND fam.variant_count <> actual_variant)
RETURN fam.family_key
```
→ **0 rows.** Fully clean. The mirror is a true mirror.

### 9. QAIssue leakage

- `HAS_QA_ISSUE` in the old direction → **0**. The type is gone from
  `db.relationshipTypes()` entirely.
- All 915 `QAIssue` nodes carry `:Internal`, and every edge touching one is
  `(QAIssue:Internal)-[:QA_ISSUE_ON]->(Work)` — 915, no other shape.
- **Narrow check:** `MATCH (p)-[*1..2]->(q:QAIssue) WHERE NOT p:Internal` → **0 rows**. No
  product traversal reaches the diagnostic layer.
- **The integrator's BROAD-form claim is CONFIRMED exactly, and I verified it by decomposing
  the number rather than accepting it:**

```cypher
MATCH (p)-[r]->(i:Internal) WHERE NOT p:Internal
RETURN [l IN labels(i) WHERE l <> 'Internal'] AS internal_kind, type(r) AS via, count(*) AS c
```

```
TextVersion  via HAS_TEXT_VERSION  44276
Translation  via HAS_TRANSLATION   17283
Lemma        via MENTIONS_LEMMA     9000
                             total 70559
```

70,559 exactly, and the label decomposition contains **only** the three sub-entity kinds that
must stay reachable — no `QAIssue`, no `DerivedMetric`. The claim that the broad form is
legitimately noisy is true, and the reason given for it is the right reason.

### 10. Predicate-edge mismatch

Layers separable — the hard constraint — **CONFIRMED**:

```cypher
MATCH (p:Passage)-[h:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion)
RETURN h.quality_tier AS tier, h.knowledge_layer AS layer, h.evidence_basis AS eb, count(*) AS c
```
```
TIER_D / L2_DETERMINISTIC_DERIVED / TRANSLATION  2459
TIER_B / L2_DETERMINISTIC_DERIVED / SANSKRIT     2406
```

Predicate edges, by tier: TIER_B 2,406 all have one; TIER_D 266 have one, 2,193 do not. Sums
to the claimed 2,672 / 2,193.

**Is the 89.2% refusal honest?** I tested the strongest counter-hypothesis: every one of the
11 refused `semantic_predicate` values has an identically-named relationship type already
live in the graph (`DESCRIBES` 199, `DESCRIBES_ACTION` 35, `REQUESTS` 89, `CONTRASTS_WITH` 8,
`INVOLVES_SUBSTANCE` 3, `INVOLVES_RITUAL` 9, `INVOLVES_OFFERING` 11, `REFERS_TO_PLACE` 1,
`REFERS_TO_NATURAL_PHENOMENON` 5), all from the same enrichment run. So a mapping target
exists by name. **The refusal is nonetheless honest**, because `ASSERTION_PREDICATE` targets
`:ActionPredicate` — a closed, architect-owned vocabulary of 41 verb classes with a single
`vocabulary_version` — and those nine values are passage-to-referent relations with no verbal
root, not action classes. The mapped 266 are exactly `INVOKES 211 + PRAISES 55`, the only two
of the 13 that name a verb. The load query `MATCH`es the predicate node and never `MERGE`s
it, so an unmapped value lands nothing rather than minting a 42nd class; I confirmed
`ActionPredicate = 41`. Honest refusal, correctly structured.

### 11. Stale MERGE artifacts

I enumerated `run_id`, `pipeline_version` and `build_pass` value spaces across **every**
relationship type, rather than checking the layers I expected to be dirty.

**F-7** is the finding: `ABOUT_CONCEPT` with two run_ids and no sweep.

Everything else resolved:

- `SHARES_ENTITY_VOCABULARY_WITH` → one run_id, 2,141 edges. The fix held (but see F-13).
- `MEMBER_OF_FAMILY` / `HAS_FORMULA` → one run_id each, matching, 2,037.
- `MENTIONS_DEVATA`, `MENTIONS_ENTITY`, `USES_FORMULA`, the parallels layer → one run_id each.
- `USED_FOR_RITE` has two generations (110 TIER_B/L2/`PER_PASSAGE`/no `build_pass`; 419
  TIER_D/L4/`CONTAINER_INHERITED`/stamped). I initially took this for a stale survivor set.
  It is not — `V3_1_WAVE2_RITUAL_DEPTH.md` §1 and §4.1 declare exactly this split, by design,
  and the query defaults to strict. Residual worth one line of note: the 110 strict edges
  carry only 6 properties and **no** `build_pass`, `run_id`, `source_id` or `evidence`, so
  that generation is unauditable.
- `PERFORMED_BY` two `build_pass` values (16 + 3) matches the declared 16 → 19 growth.
- `SHARES_FORMULA_WITH` survives in `db.relationshipTypes()` with 0 edges — a Neo4j type-token
  residue, not an edge. Cosmetic.
- Edges with an empty-string `run_id` (`BROADER_THAN` 18, `DEVATA_ASSOCIATED_WITH` 101) and
  edges with no `run_id` at all (`EXACT_PARALLEL_OF` 256 of 1,006, `BROADER_THAN` 79 of 97,
  `DEVATA_ASSOCIATED_WITH` 59 of 160). These are pre-provenance generations, not stale
  duplicates — no run_id collision, no double-counting — but they cannot be swept by run_id
  if they ever need to be. Recorded, not escalated.

### 12. Cartesian query blowups

All 90 named queries executed with their declared `parameters`. **0 errors, 0 over 300 ms,
median 5.7 ms, max 296.1 ms.**

```
296.1 ms  textual_versus_interpretive              (6 rows)
201.3 ms  model_adjudicated_edges                 (18)
198.7 ms  ritual_profile                           (8)
185.5 ms  model_adjudicated_review_trail          (30)
166.0 ms  confidence_is_a_pipeline_constant       (18)
163.8 ms  cross_veda_relatedness_method_census     (6)
158.5 ms  rv_family_books_versus_outer_books      (25)
 71.4 ms  deity_profile                            (1)
```

The claim "all under 300 ms with a median near 6 ms" is **CONFIRMED**, though 296.1 ms leaves
almost no margin on the worst query. `conceptually_similar_not_reused` no longer exists.

Three queries return zero rows: `unlabelled_product_nodes` (0 is the pass condition),
`orphan_domain_entities` (0 is good), and `rivers_and_tribes` — whose zero I verified is real
but whose caveat is wrong (**F-5**).

Blowup attempt: succeeded on the first try — **F-14**.

### 13. Counts-block drift

Systematically: `member_count` on `RishiFamily` (0 drift), `member_count`/`core_count`/
`variant_count` on `FormulaFamily` (0 drift), the `Work.completeness` figures (4/4 exact), the
per-Veda `MENTIONS_DEVATA` caveat figures in `devatas_named_in_all_four_vedas` (RV 10,284 /
AV 3,582 / YV 1,964 / SV 1,335 — exact), the mantra denominators in the same caveat (RV
10,552 / AV 5,839 / YV 1,975 / SV 1,844 — exact against `:Mantra`), the 21
`INSUFFICIENT_EVIDENCE` cells, the `2,672 / 2,193 / 266` predicate split, the
`8,340 / 2,019 / 6,806` certainty split, `ActionPredicate = 41`.

Drift found: **F-5** (rivers 12 vs 249) and **F-4** (the takman caveat asserting the negation
of the data). Also `V3_1_WAVE2_RITUAL_DEPTH.md` records a total of 266,769 relationships
against a live 266,757; given F-13 I attribute the −12 to later session activity rather than
to a mis-count, and do not raise it as a finding.

Given this repository's history — nine recorded corrections of which one had been written — I
note that this pass found **no** case of a recorded fix that had not been applied to the data.
The two drifts are both stale *caveats*, not phantom corrections.

### 14. The new predicates and properties

**`SHARES_ENTITY_VOCABULARY_WITH` (2,141).** `method = 'entity-co-mention-idf'`,
`evidence_basis = 'SHARED_REGISTRY_ENTITIES'`, and it carries `shared_entity_keys`,
`shared_entities`, `distinctiveness`, `rarest_shared_df`, `veda_pair` and `score`. The name
and the properties describe entity-vocabulary overlap with IDF weighting and nothing more; it
names its shared entities as evidence and never claims conceptual similarity. **Claims exactly
what it can support.** Endpoints are `Mantra`→`Mantra` only.

**`centrality_degree` on 227 `DomainEntity`.** `centrality_measure =
'DEGREE_OVER_PASSAGE_CO_MENTION'`. My first test compared it against raw node degree and
found 214 mismatches; that was my error, because that is not what the measure claims. Against
the measure it actually declares:

```
centrality_degree != live MENTIONS_ENTITY distinct-passage count: 0 of 227
```

**Exact for all 227.** `centrality_bridging` is a string stating `NOT_BUILT` with the reason
(no community structure exists), rather than a column of zeros — the right call.

**Spearman rho = 0.964 over 91 shared members — CONFIRMED, verified three ways.** (i) The
module's `derive()` recomputes 0.964 against the live graph, so the stored value is not
stale. (ii) I recomputed the d²-shortcut independently on its inputs: 0.964. (iii) Because
the shortcut is invalid under ties, I recomputed the tie-corrected Pearson-on-ranks form: also
**0.964** (2 ties in A, 5 in B — too few to matter). The 91 is right too: exactly 91 nodes
bear `ABOUT_CONCEPT` edges against 227 bearing `MENTIONS_ENTITY`, a strict subset, so
`only_in_rival = 0` is correct.

One overstatement, MINOR and folded into the table below rather than numbered: the module's
`AUTHORITY_BASIS` string — stored on a `DerivedMetric` and returned by
`concept_layer_rank_correlation` (Q37, Q96) — frames the two as "rival layers" that "overlap
heavily in membership" and calls the choice "a coin flip that changed the answer". They are
two edge types over **one identical node set**: `MATCH (n:Concept) RETURN count(n),
count(CASE WHEN n:DomainEntity THEN 1 END)` → `227, 227`, and 0 nodes bear `ABOUT_CONCEPT`
without `MENTIONS_ENTITY`. The choice cannot change membership at all, only coverage
(227 vs 91). The rho is a real measurement; the framing around it claims more than it can.

**`InterpretiveClaim.about` on 6 claims.** `DATASET` 3, `VEDIC_TEXT` 2,
`TRADITIONAL_APPARATUS` 1 — 6 total, all `TIER_D`. Matches the claim exactly, and
`competing_interpretations` uses it to type a disagreement as
`CROSS_CATEGORY__VEDIC_TEXT_VERSUS_DATASET`, which is the point of the field. Clean.

---

## Claims checked

| # | Claim | Source | Verdict |
|---|---|---|---|
| 1 | `referent_certainty` splits 8,340 / 2,019 / 6,806, all 17,165 edges carry it | brief, deity layer | **CONFIRMED** (exact, value space enumerated) |
| 2 | The ten deities' per-Veda C/P/A table | `V3_1_DEITY_LAYER.md` §3 | **CONFIRMED** cell for cell |
| 3 | Eight of ten deities fixed in all three unannotated corpora; Uṣas YV, Pṛthivī SV, Āpaḥ and Vāc still zero | §3 | **CONFIRMED** — the disclosure is accurate |
| 4 | Worst `PROBABLE` alias is `sūrya` at 2/3 over 71 live edges, exposure not closed | §4 | **CONFIRMED** |
| 5 | No default query returns an AMBIGUOUS-driven answer | §8 | **CONFIRMED** |
| 6 | The default scope (CERTAIN+PROBABLE) is what the queries use | §8 policy | **CONTRADICTED** — the flagship four-Veda query uses CERTAIN only (F-2) |
| 7 | All four `Work` nodes carry scope/completeness/excluded_corpora/rights | integrator | **CONFIRMED** |
| 8 | Every quantitative claim inside `Work.completeness` | integrator | **CONFIRMED** — 4/4 translation figures, both attribution figures, all citation coverage, exact |
| 9 | `HAS_DEVATA` is RV-only Anukramaṇī ascription | brief | **CONFIRMED** (10,558, all RV) |
| 10 | `MENTIONS_DEVATA` is four-Veda textual mention | brief | **CONFIRMED** (RV 10,284 / AV 3,582 / YV 1,964 / SV 1,335) |
| 11 | No query conflates attribution with mention | — | **CONFIRMED** |
| 12 | No container-inherited attribution presented per-verse | — | **CONFIRMED** (all 17,165 land on `:Mantra`) |
| 13 | `is_composite` true on 14 of 200 | brief | **CONFIRMED** (14 of 214 `Devata`) |
| 14 | Every decomposition supported by the component registry | deity layer §7 | **CONFIRMED** 14/14 |
| 15 | No composite tops a per-deity leaderboard | §7 | **CONFIRMED** (first composite ≈ rank 20) |
| 16 | No conclusion rests on Griffith's English presented as textual fact | — | **CONFIRMED** — translation-derived edges confined to the RV assertion layer; 0 named queries traverse `:Translation` |
| 17 | No SV answer is silently translation-dependent | — | **CONFIRMED** (SV has no assertion layer) |
| 18 | 87 families / 305 edges / 302 of 729 ṛṣis | rishi report §2 | **CONFIRMED** exactly |
| 19 | Membership derived ONLY from stated vṛddhi patronymics, never resemblance | §1 | **CONTRADICTED in the mechanism, not the substance** — 11 edges state a non-vṛddhi derivation as vṛddhi (F-10) and an undisclosed `source_variants` channel emends what §4 refuses to emend (F-11). No membership rests on resemblance. |
| 20 | No non-seer row has a family | §5 | **CONFIRMED** (0 rows) |
| 21 | No eponym is a member of his own family | brief hazard | **CONFIRMED** (0 rows); 17 bare-patronymic self-memberships are the weaker residual (F-12) |
| 22 | `RishiFamily.member_count` agrees with the rows | §2 | **CONFIRMED** (0 drift) |
| 23 | The ṛṣi-family layer unblocks Q2/Q19/Q26/Q62 | ROI Task 10 | **CONTRADICTED** — 0 of 90 queries touch it (F-8) |
| 24 | `MEMBER_OF_FAMILY` and `HAS_FORMULA` agree edge-for-edge, 2,037 each | formula report §3.4 | **CONFIRMED** (0 either way, 0 property disagreement) |
| 25 | No `FormulaFamily` count-block drift | §3.6 | **CONFIRMED** (0 rows) |
| 26 | 0 `HAS_QA_ISSUE` remain in the old direction | integrator Task 7 | **CONFIRMED** |
| 27 | No product traversal reaches the diagnostic layer | Task 7 | **CONFIRMED** (0 rows at depth 1–2) |
| 28 | The BROAD check's ~70,559 hits are all legitimate sub-entities | integrator | **CONFIRMED** — exactly 70,559 = TextVersion 44,276 + Translation 17,283 + Lemma 9,000, and nothing else |
| 29 | 2,193 assertions still have no predicate edge; 266 of 2,459 mapped | formula report §4 | **CONFIRMED** exactly |
| 30 | The 89.2% refusal is principled, not hidden work | §4.4 | **CONFIRMED** — targets exist by name but not as `:ActionPredicate` classes; `MATCH`-not-`MERGE` guard verified, `ActionPredicate = 41` |
| 31 | TIER_B and TIER_D assertion layers remain separable | §4.5 | **CONFIRMED** (2,459 / 2,406 clean split on tier, layer and evidence basis) |
| 32 | `SHARES_ENTITY_VOCABULARY_WITH` stale survivors were retired on `run_id` | this session's fix | **CONFIRMED** (one run_id live) |
| 33 | No other layer has stale MERGE survivors | assumed false by the brief | **CONTRADICTED** — `ABOUT_CONCEPT` has 1,468 unswept edges from a superseded run (F-7) |
| 34 | All 90 named queries under 300 ms, median near 6 ms | catalogue | **CONFIRMED** (max 296.1, median 5.7, 0 errors) |
| 35 | The Cartesian blowup shape is fixed | ROI Task 8 | **CONFIRMED for the named query, CONTRADICTED for the shape** (F-14) |
| 36 | Spearman rho = 0.964 over 91 shared members | `queries.py` | **CONFIRMED** three ways, including tie-corrected |
| 37 | `centrality_degree` stored on 227 nodes is correct | centrality module | **CONFIRMED** (0 of 227 mismatch against its declared measure) |
| 38 | `MENTIONS_ENTITY` and `ABOUT_CONCEPT` are rival layers overlapping heavily in membership | `AUTHORITY_BASIS` | **CONTRADICTED** — identical 227-node set; the difference is coverage (227 vs 91), not membership |
| 39 | `SHARES_ENTITY_VOCABULARY_WITH` measures entity-vocabulary overlap and not conceptual similarity | brief | **CONFIRMED** — name and properties both stay within what it can support |
| 40 | `InterpretiveClaim.about` on 6 claims across three values | brief | **CONFIRMED** (3/2/1, all TIER_D) |
| 41 | `Condition` split into affliction and cause | diagnosis item 15 fix | **CONTRADICTED** — `condition_kind` absent from the full key space of all 36 nodes (F-3) |
| 42 | Q90 cleared | Wave 2 §2 | **CONFIRMED in the graph, CONTRADICTED in the catalogue** — the `RitualRole` split landed (11 nodes, `hotṛ` 300 / `potṛ` 19) but no query serves Q90 (F-9) |
| 43 | Q86/Q87/Q88 cleared | deity layer §6 | **CONFIRMED in the graph, CONTRADICTED in the catalogue** — Q86's fire count is now 1 and the three refused merges are correctly refused, but no query serves any of the three (F-9) |
| 43a | Q38 cleared: "composites excluded from the per-deity leaderboard" | closure report §9 | **CONFIRMED for `deity_widest_range`, CONTRADICTED for `deities_by_axis`** — same question, same root-cause class, second query unfixed (F-1) |
| 43b | Q15 "partially addressed or untouched — reported as remaining" | closure report §9 | **CONFIRMED** — honestly open, which is why F-3 is MAJOR and not CRITICAL |
| 43c | Q1/Q21/Q34/Q36/Q44 cleared | — | **NOT CLAIMED** anywhere; this is why F-2 is held at MAJOR |
| 44 | Q13/Q60 cleared, "recall is a column, not a caveat" | Wave 2 §4 | **PARTIALLY CONTRADICTED** — the column exists for 2 of 6 rites and is mis-scoped onto non-locus Vedas (F-6) |
| 45 | `Rudra` is `ATTESTED` in all four Vedas after the fix (Q43) | deity layer §6 | **CONFIRMED** (PROBABLE in all four) |
| 46 | The graph is frozen for the duration of this audit | brief | **CONTRADICTED** — the vocabulary-overlap layer was rebuilt mid-audit (F-13) |
| 47 | `check_live_invariants.py`: 0 failing | integrator | **CONFIRMED** (0 failing, 3 warning, 17 checked) |

---

## Negative findings — hypotheses I tested that came back clean

Each of these was a real suspicion, several of them the brief's own, and each is worth
recording so the next audit does not spend the time again.

1. **Griffith leaking into a Sāmavedic answer.** Enumerated `evidence_basis` across every
   edge in the graph; the 3,620 `TRANSLATION` edges are RV-only and confined to the assertion
   layer. Zero named queries traverse `:Translation`. Clean.
2. **English-only concept assertions surviving the V3 retirement.** Method value space on
   `ABOUT_CONCEPT` and `MENTIONS_ENTITY` holds no english-only method. Clean.
3. **Container-inherited mentions presented as per-verse.** All 17,165 `MENTIONS_DEVATA`
   edges land on `:Mantra` nodes; not one attaches to a sūkta-level `Passage`. Clean.
4. **The four-Veda query's caveat denominators being stale.** ROI Task 13 had just fixed one
   such figure, so I expected more. RV 10,552 / AV 5,839 / YV 1,975 / SV 1,844 are exact
   against `:Mantra`, and the per-Veda edge figures are exact too. Clean.
5. **A composite topping a deity leaderboard.** Checked the mention leaderboard directly.
   Clean.
6. **A ṛṣi-family membership resting on name resemblance.** 87 token groups inspected, all 22
   non-initial-position matches read individually. Clean — this is the layer the brief called
   most exposed to fabrication, and it is not fabricated.
7. **A non-seer or an eponym inside a family.** Both queries return 0 rows. Clean.
8. **The formula twins disagreeing.** 0 either direction, 0 on properties. Clean.
9. **`FormulaFamily` or `RishiFamily` count blocks drifting from rows.** 0 rows each. Clean.
10. **`DerivedMetric` or `QAIssue` reachable from a product node.** 0 rows. The `Internal`
    label really does do double duty, and the integrator's account of it is exact. Clean.
11. **The predicate refusal hiding a mapping that should exist.** The strongest
    counter-hypothesis — that identically-named relationship types already exist — is true and
    still does not make the refusal dishonest, because `ASSERTION_PREDICATE` targets a closed
    verb-class vocabulary. Clean.
12. **`USED_FOR_RITE`'s two generations being a stale survivor set.** Declared by design in
    Wave 2 §4.1, with the strict layer defaulted. Clean (one unauditable-provenance residual
    noted).
13. **`centrality_degree` being wrong.** My own first test was the wrong test. Against the
    declared measure it is exact for all 227. Clean.
14. **The rho being stale or tie-inflated.** Recomputed three ways including tie-corrected
    Pearson-on-ranks. 0.964 every time. Clean.
15. **`rivers_and_tribes`' zero being a projection artifact** (Sarasvatī routed to the deity,
    or a granularity mismatch). The zero is genuine at mantra level. Only the caveat's figure
    is wrong. Clean on the zero.
16. **Stale run_ids across the whole graph.** Enumerated `run_id`, `pipeline_version` and
    `build_pass` value spaces on every relationship type rather than the layers I expected to
    be dirty. One finding (F-7); every other MERGE-written layer is single-generation or
    declared.

---

## Final verdict

**CRITICAL: 1.** The session gate of 0 CRITICAL is **not met**.

`deities_by_axis` returns `UNSPECIFIED` — a materialised axis holding 101 unclassified
entities, among them humans, animals, objects and a hymn title — as the top-ranked functional
role of the Vedic pantheon on Q38 and Q46, both claimed cleared, while its own caveat states
those deities "do not appear here". It is the wrong-top-ranked-member and wrong-class-membership
shapes together, delivered by the obvious query, with a caveat that misleads the careful
reader too. Q38's *other* serving query had exactly this defect and the closure report
records fixing it; the fix was scoped to one query rather than to the question, and this one
was missed.

The fix is `WHERE ax.axis <> 'UNSPECIFIED'`. Once that lands, the gate is met on my findings:
nothing else here is a confidently wrong answer to a question the reports claim cleared.

I want to be explicit about what I did **not** escalate, because a false CRITICAL costs as
much as a soft one. F-2 (the flagship query's `CERTAIN`-only column) is the finding closest to
the line — it is an artifact-driven zero next to a non-zero, which is precisely the shape the
session existed to remove — and I held it at MAJOR only because none of the five questions it
serves is on the claimed-cleared list. If the closing benchmark run grades Q1, Q21, Q34, Q36
or Q44 as cleared, F-2 becomes CRITICAL and should be fixed in the same pass as F-1.

The layers that survived the hardest attack are worth saying plainly: `Work.scope` is true to
the digit on every quantitative claim; the attribution/mention separation is clean in both the
data and the queries; the formula mirror is a true mirror; the QAIssue reversal is complete and
its noisy broad-form check is honestly described; the assertion layers are separable and the
89.2% predicate refusal is principled; and the ṛṣi-family layer — the one flagged as most
exposed to fabrication — contains no fabricated membership. Its defect is that nobody can
reach it.
