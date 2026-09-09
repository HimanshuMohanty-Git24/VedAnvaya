# Formula Family Reconstruction — Knowledge Model V3

**Scope.** Resolve the formula-redundancy backlog carried unchanged since V1 by building a
`FormulaFamily` layer over the 4,825 `Formula` nodes and 22,686 `USES_FORMULA` edges.

**Runtime.** `CLAUDE_CODE_DIRECT`. Nothing was written to the graph; the graph was read for
the before-measurements only.

**Deliverables.**

| file | what |
|---|---|
| `src/vedagraph/enrich/formula_families.py` | the builder |
| `scripts/build_formula_families.py` | the driver |
| `tests/enrich/test_formula_families.py` | 38 tests |
| `data/enrichment/vedagraph_enrichment_v1/formula_families.jsonl` | 720 rows |
| `data/enrichment/vedagraph_enrichment_v1/formula_family_members.jsonl` | 2,037 rows |

**Headline.** 720 families over 2,037 formulas; 2,788 formulas left unfamilied. The
utility gain is real for two of the three test questions and **zero for the third**, and
the third's failure is upstream of this layer.

---

## 1. The substring-redundancy figure: 1,103 is correct, and the audit measured the wrong surface

This is the first thing to report because it changes a backlog verdict.

`GRAPH_ENRICHMENT_V1.md` §M2 stated 1,103 of 4,825 formulas are strict substrings of
another. `KNOWLEDGE_MODEL_V3_BASELINE_AUDIT.md` §B7 re-ran it, got 1,039 and 984, and
recorded the verdict as *"VERIFIED_STILL_OPEN — number **not reproducible** (1,039, not
1,103)"*, adding that *"the defect is real, the number is 6.2% high."*

I re-measured on all three surfaces
(`scratchpad/formulas/m1_redundancy.py`, whole-artifact pairwise containment):

| surface measured | unique strings | exact duplicates | strict substrings of another | share |
|---|---|---|---|---|
| `normalized` | 4,825 | 0 | 1,039 | 21.5% |
| `display_form` | 4,825 | 0 | 984 | 20.4% |
| **collapsed identity** | **4,825** | **0** | **1,103** | **22.9%** |

**V1's 1,103 reproduces exactly on the collapsed identity surface.** The audit's numbers
are also right — about the surfaces they measured. The disagreement is not an arithmetic
error on either side, and the identity surface is the one that governs:

- `formulas.py` derives `formula_id` from the *sandhi-collapsed folded form*, with the
  stated reason that "two word divisions of the same letters are one formula, not two".
- Its own maximality rule tests containment on that same collapsed form
  (`formula.collapsed in other.collapsed`).
- `normalized` carries word breaks, so it misses a sub-formula written with a different
  word division. `display_form` is one edition's spelling, so it misses a sub-formula whose
  container is quoted from a different edition.

**Correction to the backlog:** B7's "not reproducible" verdict should be withdrawn. The
defect is open; the number was never wrong. The lesson is the one already in
`MEMORY.md` about auditing the selected witness — here, three surfaces exist and only one
is the formula's identity, and a re-measurement that lands lower is not thereby a
correction.

Derived counts on the identity surface, for the record:

| measure | result |
|---|---|
| strict containment pairs | 1,593 |
| formulas that are a strict substring of another | 1,103 |
| formulas that strictly contain another | 1,119 |
| formulas in at least one containment relation | 2,037 |
| formulas in **no** containment relation | 2,788 |
| `USES_FORMULA` rows on a contained formula | 8,502 of 22,686 (37.5%) |
| longest containment chain | 4 levels |

The prior report's "8,159 of 22,686 (36.0%)" for the third row was measured on
`normalized`; on the identity surface it is 8,502 (37.5%).

### 1.1 `match_level` blankness — the brief's ~70% understates the formula layer

```cypher
MATCH ()-[r]->() WHERE type(r) IN ['REUSES_TEXT_FROM','EXACT_PARALLEL_OF',
  'NEAR_PARALLEL_OF','VARIANT_OF','USES_FORMULA']
RETURN type(r) AS rel, count(r) AS edges,
       sum(CASE WHEN r.match_level IS NULL OR r.match_level = '' THEN 1 ELSE 0 END) AS blank
ORDER BY edges DESC
```

| rel | edges | blank | share |
|---|---|---|---|
| `USES_FORMULA` | 22,686 | **22,686** | **100.0%** |
| `NEAR_PARALLEL_OF` | 3,049 | 3,049 | 100.0% |
| `REUSES_TEXT_FROM` | 1,684 | 1,180 | 70.1% |
| `EXACT_PARALLEL_OF` | 1,006 | 256 | 25.4% |
| `VARIANT_OF` | 788 | 0 | 0.0% |

The brief's "~70% of reuse edges" reproduces on the four *parallel* types alone (4,485
blank of 6,527 = 68.7%). On `USES_FORMULA` it is **100%**, on all 22,686 edges. The
underlying fact is not missing — every occurrence row in the source artifact records
`SCRIPT_FOLDED` or `SANDHI_INSENSITIVE` inside its evidence JSON — so this is a projection
defect, not a derivation one. Out of scope here (I do not touch the projection), but noted:
every one of my 2,037 member rows carries `match_level` as a first-class scalar property.

### 1.2 Word-count distribution

| tokens | formulas | share |
|---|---|---|
| 2 | 2,038 | 42.2% |
| 3 | 1,249 | 25.9% |
| 4 | 614 | 12.7% |
| 5 | 345 | 7.2% |
| 6 | 241 | 5.0% |
| 7 | 185 | 3.8% |
| 8 | 153 | 3.2% |

42.2% at two tokens, confirming the brief's figure. What that means is §4.

---

## 2. Design, and the measurements that chose it

### 2.1 What makes a family: containment alone

The design question was whether containment needs a shared-occurrence condition to stop a
frequent short formula chaining unrelated phrases into a blob. It does not, and the reason
is a proof rather than a preference.

Detection in the Formula layer is substring search on the sandhi-collapsed surface. If *A*
is a strict substring of *B*, every mantra containing *B* contains *A*, so `occ(B) ⊆
occ(A)`. Measured over every pair:

> **pairs where `occ(container)` is not a subset of `occ(contained)`: 0 of 1,593.**

A shared-occurrence condition is therefore not an independent test — containment already
implies the strongest form of it. The only thing such a condition can express is the
frequency *ratio* of the two members, and measured, that ratio cuts real phraseology:

| rule | pairs kept | families | members | unfamilied | max family |
|---|---|---|---|---|---|
| **containment alone** | **1,593** | **720** | **2,037** | **2,788** | **14** |
| + coverage ≥ 0.05 | 1,591 | 720 | 2,036 | 2,789 | 14 |
| + coverage ≥ 0.10 | 1,544 | 721 | 2,021 | 2,804 | 12 |
| + coverage ≥ 0.20 | 1,471 | 735 | 1,988 | 2,837 | 10 |
| + coverage ≥ 0.30 | 1,372 | 735 | 1,923 | 2,902 | 10 |
| + coverage ≥ 0.50 | 1,146 | 692 | 1,714 | 3,111 | 8 |

where coverage = `|occ(expansion)| / |occ(core)|`. A floor buys at most 15 extra families
and costs up to 323 members. And the first links it cuts are the best phraseology in the
corpus — the four lowest-coverage pairs are:

| coverage | core | expansion |
|---|---|---|
| 0.032 | `pāta svastibhiḥ sadā naḥ` (93m) | `me yūyam pāta svastibhiḥ sadā naḥ` (3m) |
| 0.037 | `yūyam pāta svastibhiḥ sadā naḥ` (82m) | `me yūyam pāta svastibhiḥ sadā naḥ` (3m) |
| 0.050 | `viśvā bhuvanā` (60m) | `ca viśvā bhuvanāni` (3m) |
| 0.050 | `viśvā bhuvanā` (60m) | `abhi yo viśvā bhuvanā` (3m) |

These are the same refrain with one more word in front. Coverage is low only because the
core is very frequent, which is not evidence of anything.

The blob never materialises either: the largest containment component has **14** members,
and it is `viśvā bhuvanā` with thirteen expansions — exactly one piece of phraseology.
Component sizes: `{2: 430, 3: 155, 4: 69, 5: 27, 6: 11, 7: 13, 8: 5, 9: 4, 10: 2, 11: 2,
12: 1, 14: 1}`.

**Decision: containment on the collapsed identity surface, grouped by connected component.**

### 2.2 The representative, and why it cannot depend on input order

Monotonicity turns "the shortest form that recurs independently" into a computation with no
free parameters. Because `occ` only shrinks as a string grows, the member with the largest
distinct-mantra count is always a **minimal** element: if a shorter member *A* were
contained in the argmax *M*, then `|occ(A)| ≥ |occ(M)|`, so `occ(A) = occ(M)`, and the
Formula layer's maximality rule would already have collapsed *A* into *M*.

So the rule is: **largest distinct-mantra count, then shortest collapsed form, then the
collapsed form itself.** The last component is the member's own identity, so no two members
can swap places between runs. The minimality is asserted rather than trusted:

> `member_contained_in_representative`: **0** occurrences on the real artifact.

`test_the_representative_does_not_depend_on_input_order` checks all 24 permutations of a
four-member family built so two members tie on mantra count, and
`test_a_permuted_real_artifact_produces_byte_identical_output` shuffles both real artifacts
and compares bytes.

### 2.3 Roles — and a design error I made and corrected

My first version defined `EXPANSION` as "strictly contains the *representative*" and swept
everything else into `VARIANT` under the similarity floor. It rejected 188 of 241
"variants". Inspecting them showed the error: **188 of those 188 are strict substrings of
some non-core member**, so their membership was justified by exact containment and the
floor was discarding the strongest evidence in the layer. Example: `puraḥ pitaraṃ ca`
scored 0.220 against the representative and is a literal substring of the family member
`āyaṃ gauḥ pṛśnirakramīdasadanmātaraṃ puraḥ pitaraṃ ca prayantsvaḥ`.

The corrected taxonomy needs no threshold for membership at all:

| role | definition | measured |
|---|---|---|
| `CORE` | a minimal element — strictly contains no other member | 914 |
| `EXPANSION` | strictly contains at least one member, hence at least one core | 1,119 |
| `VARIANT` | a minimal element close enough to a core to be a second *spelling* of it | 4 |

> **members classified by containment: 2,037 of 2,037. Left over: 0.** Checked on every
> run (`member_unclassified_by_containment`, never fires).

`occurrence` is deliberately **not** a role here: one passage using one member is already a
`USES_FORMULA` row, and re-emitting 22,686 of them would say nothing new. Families carry
the aggregate instead, which is the thing no member row can answer.

Each `EXPANSION` links to its **immediate parent** — the longest member it strictly
contains — so the member rows reconstruct the family's containment tree rather than a star
around the core. Depth distribution: `{2: 589, 3: 115, 4: 16}`.

### 2.4 The similarity threshold, and the honest size of its job

`VARIANT` is the one role that needs a measurement, and it separates "a second spelling of
this core" from "a second, different core". Metric and floor are both **imported, not
chosen**: the blend is `crossveda`'s `0.5 * ngram_jaccard + 0.5 * lcs_ratio`, and the floor
is `NEAR_PARALLEL_FLOOR = 0.72`, already this repository's answer to *"below this, two texts
are not related, only in the same register"*. The surface is named on every member row and
is `SANDHI_INSENSITIVE`, because that is the surface containment ran on.

Distribution of a minimal element's best similarity to an already-assigned core:

| | value |
|---|---|
| variants (≥ 0.72) | **4** — range 0.763 to 0.858 |
| secondary cores (< 0.72) | **194** — median 0.565 |

The four variants are the visarga/sibilant residual `formulas.py` documents one level down:
`vayaṃ dviṣmas` beside `vayaṃ dviṣmaḥ` is the clearest — neither contains the other because
they differ in their last character.

**Needing this role for four members of 2,037 is the honest result and I report it as
such.** A layer that needed it for hundreds would be a clustering layer wearing a
containment layer's name.

### 2.5 A family may have more than one core — stated, not resolved

157 of 720 families carry a secondary core, 194 in total, because two independently
recurring short forms meet inside one longer attested phrase:

```
component of 11, 3 cores — the AV/YV imprecation
     8x 'vayaṃ dviṣmas'                          VARIANT
    52x 'vayaṃ dviṣmaḥ'                          CORE (secondary)
    63x 'yo smān dveṣṭi'                         CORE (representative)
    46x 'yaṃ vayaṃ dviṣmaḥ'                      EXPANSION
    ... 7 more expansions
```

**208 expansions contain more than one core**, so there is no non-arbitrary way to split
such a family, and inventing one would make membership depend on a tie-break. Reported as
`secondary_core_count` on the family row and `families_with_a_secondary_core` in the run
report. This is a fact about the corpus, not residual redundancy.

### 2.6 Cross-Veda spread as a family property, checked against a second derivation

`veda_counts` on a family is the **union** of its members' mantras bucketed by Veda, not
the sum of member counts — members overlap by construction, so summing would inflate every
family by roughly its member count. `veda_span` and `cross_veda` follow.

Because the layer's whole purpose is to answer a cross-Veda question, the claim is checked
against a different derivation: `parallel_corroborated` is true when
`cross_veda_parallels.jsonl` independently connects two of the family's own mantras across
a Veda boundary.

> **534 of 615 cross-Veda families (86.8%) are corroborated by the parallel layer.**

The 81 that are not are the shape a spurious cross-Veda claim would have, and they are
findable by property rather than by re-derivation.

`representative_coverage` (also the family's provenance score) is the share of the family's
mantras the core alone accounts for: median 1.000, 594 of 720 families at exactly 1.0,
minimum 0.438. Below 1.0 exactly when a variant or secondary core is attested where the
representative is not.

---

## 3. Before / after utility — the required comparison

### Q1 — "Which formula families spread across three or four Vedas?"

**BEFORE** (live graph):

```cypher
MATCH (f:Formula) WHERE size(f.vedas) >= 3
RETURN size(f.vedas) AS vedas, count(*) AS formulas ORDER BY vedas DESC
```
```
{"vedas": 4, "formulas": 229}
{"vedas": 3, "formulas": 1374}
```

1,603 rows. The top ten of them, with the family each turns out to belong to:

| mantras | Vedas | formula | belongs to |
|---|---|---|---|
| 93 | 4 | `pāta svastibhiḥ sadā naḥ` | family `pāta svastibhiḥ sadā naḥ` |
| 60 | 4 | `viśvā bhuvanā` | family `viśvā bhuvanā` |
| 53 | 4 | `parame vyoman` | family `parame vyoman` |
| 46 | 3 | `nabhantām anyake` | family `nabhantām anyake` |
| 39 | 3 | `bhuvanāni viśvā` | family `bhuvanāni viśvā` |
| 39 | 3 | `haviṣā vidhema` | family `haviṣā vidhema` |
| 38 | 4 | `brahmaṇas pate` | family `brahmaṇas pate` |
| 33 | 3 | `somasya pītaye` | family `somasya pītaye` |
| 32 | 4 | `viśvā bhuvanāni` | **duplicate** of `viśvā bhuvanā` |
| 29 | 3 | `kasmai devāya haviṣā vidhema` | **duplicate** of `haviṣā vidhema` |

The before top-20 contains 20 rows covering **16** distinct phraseologies.

**AFTER** (family artifact):

```python
fam = read_artifact(root, "formula_families.jsonl")
sorted(fam, key=lambda f: (-f["veda_span"], -f["mantra_count"]))
```

| Vedas | families |
|---|---|
| 4 | 107 |
| 3 | 296 |

403 families, plus 735 unfamilied formulas that reach 3+ Vedas on their own = **1,138 rows
against 1,603**. The 868 rows that were family members collapse into 403 families: a
**3.98x** reduction on the redundant part, and a 29% reduction on the whole answer.

The after rows also carry what the question actually needs — `member_count`,
`parallel_corroborated`, `secondary_core_count` — so a reader can tell a 14-member family
from a bare formula:

```
4V   93m  6mem corrob=True  'pāta svastibhiḥ sadā naḥ'
4V   60m 14mem corrob=True  'viśvā bhuvanā'
4V   53m  4mem corrob=True  'parame vyoman'
4V   48m 12mem corrob=True  'indra girvaṇaḥ'
4V   41m  7mem corrob=True  'brahmaṇas pate'
4V   35m 10mem corrob=True  'asya bhuvanasya'
4V   33m  5mem corrob=True  'no mitro varuṇo'
4V   30m  5mem corrob=True  'varuṇo mitro aryamā'
4V   28m  7mem corrob=True  'stotṛbhya ā bhara'
4V   27m 10mem corrob=True  'somam indrāya'
```

**Verdict: improved, materially.**

### Q2 — "What are the ten most widely-shared formulae in the corpus?"

**BEFORE:**

```cypher
MATCH (f:Formula) RETURN f.normalized AS formula, f.mantra_count AS mantras, f.vedas AS vedas
ORDER BY f.mantra_count DESC, f.normalized LIMIT 10
```

| mantras | formula | actually |
|---|---|---|
| 93 | `pāta svastibhiḥ sadā naḥ` | phraseology 1 |
| 82 | `yūyam pāta svastibhiḥ sadā naḥ` | phraseology 1 again |
| 63 | `yo smān dveṣṭi` | phraseology 2 |
| 61 | `yo smān dveṣṭi yaṃ` | phraseology 2 again |
| 60 | `viśvā bhuvanā` | phraseology 3 |
| 55 | `bhavati ya evaṃ` | phraseology 4 |
| 54 | `bhavati ya evaṃ veda` | phraseology 4 again |
| 53 | `parame vyoman` | phraseology 5 |
| 52 | `vayaṃ dviṣmaḥ` | phraseology 2 again |
| 51 | `yo smān dveṣṭi yaṃ vayaṃ` | phraseology 2 again |

**Ten rows covering five phraseologies.** Five of the ten slots are spent on two phrases.

**AFTER** — families and unfamilied formulas ranked together:

| mantras | name | kind | Vedas |
|---|---|---|---|
| 93 | `pāta svastibhiḥ sadā naḥ` | family / 6 members | RV SV YV AV |
| 63 | `yo smān dveṣṭi` | family / 11 members | YV AV |
| 60 | `viśvā bhuvanā` | family / 14 members | RV SV YV AV |
| 55 | `bhavati ya evaṃ` | family / 7 members | AV |
| 53 | `parame vyoman` | family / 4 members | RV SV YV AV |
| 48 | `indra girvaṇaḥ` | family / 12 members | RV SV YV AV |
| 46 | `nabhantām anyake` | family / 9 members | RV SV AV |
| 46 | `viśvasmād indra uttaraḥ` | single formula | RV AV |
| 45 | `haviṣā vidhema` | family / 11 members | RV YV AV |
| 41 | `brahmaṇas pate` | family / 7 members | RV SV YV AV |

**Ten rows covering ten phraseologies.** Exactly double the information for the same
result-set size, and two phrases that could not appear before —
`indra girvaṇaḥ` (48 mantras once its 12 members are unioned) and the unfamilied
`viśvasmād indra uttaraḥ` — are now visible at their true rank.

**Verdict: improved, and this is the layer's strongest result.**

### Q3 — "Which formulae does RV 1.1.1 share with the Samaveda?"

**BEFORE:**

```cypher
MATCH (p:Passage)-[:USES_FORMULA]->(f:Formula)
WHERE p.canonical_key = 'VG:RV:SAK:M01:S001:V001' AND 'SV' IN f.vedas
RETURN f.normalized, f.mantra_count, f.vedas ORDER BY f.normalized
```
```
### 37.2ms  rows=0
```

**0 rows.** RV 1.1.1 uses exactly **one** formula in the whole graph, `devam ṛtvijam`
(3 mantras, RV only).

**AFTER: 0 rows. No improvement whatsoever.**

`devam ṛtvijam` is in no containment relation, so it is one of the 2,788 unfamilied
formulas and there is no family to widen the answer with.

**This is a legitimate negative result and the cause is upstream of this layer.** I measured
every word n-gram of RV 1.1.1 against the whole corpus on the sandhi surface:

| mantras containing it | Vedas | span | verdict |
|---|---|---|---|
| 3 | RV | `devam ṛtvijam` | formula-eligible — the one that exists |
| **2** | **RV, SV** | `purohitaṃ yajñasya` | below `MIN_FORMULA_OCCURRENCES` |
| **2** | **RV, SV** | `yajñasya devam` | below floor |
| **2** | **RV, SV** | `purohitaṃ yajñasya devam` | below floor |
| 1 | RV | `agnim īḷe purohitaṃ` | below floor |

RV 1.1.1's genuine Samavedic sharing sits in three spans that occur in exactly **two**
mantras — RV 1.1.1 and SV ĀRAṆYA 3.4 — and `MIN_FORMULA_OCCURRENCES = 3` excludes them by
policy, with the stated reason that "two occurrences is a coincidence of sandhi as often as
it is a formula". A family layer groups formulas that exist; it cannot create one that was
never emitted.

The relationship is not lost from the graph — it is recorded at the layer built for
two-occurrence repetitions:

```cypher
MATCH (p:Passage)-[r]-(q:Passage) WHERE p.canonical_key='VG:RV:SAK:M01:S001:V001'
RETURN type(r), q.canonical_citation, r.match_level, r.similarity
```
```
{"type(r)": "REUSES_TEXT_FROM", "q.canonical_citation": "SV ARANYA 3.4",
 "r.match_level": "", "r.similarity": 0.830827}
{"type(r)": "NEAR_PARALLEL_OF",  "q.canonical_citation": "SV ARANYA 3.4",
 "r.match_level": "", "r.similarity": 0.830827}
```

So the honest answer to Q3 is: *"none, and asking the Formula layer was the wrong question —
ask the parallel layer."*

**How general is this?** I measured every Rigvedic passage:

> **RV passages where the family layer adds at least one Samavedic link: 20 of 5,103
> (0.4%).**

The best single case is RV 10.53.8: 0 of its formulas are tagged SV, but its family
`sakhāyo anu saṃ` reaches all four Vedas and is parallel-corroborated — one link gained.
For questions of the form "what does *this passage* share with *that Veda*", this layer is
**near-useless**, and a family layer nobody needs for that question is worth saying out
loud. Its value is in the aggregate questions Q1 and Q2, not the per-passage one.

### 3.1 Summary of the three

| question | before | after | verdict |
|---|---|---|---|
| Q1 families across 3–4 Vedas | 1,603 rows, 4 duplicates in the top 20 | 1,138 rows, 403 of them families, no duplicates | improved 3.98x on the redundant part |
| Q2 ten most widely-shared | 10 rows = 5 phraseologies | 10 rows = 10 phraseologies | improved 2x |
| Q3 RV 1.1.1 ∩ Samaveda | 0 rows | **0 rows** | **no improvement; cause is `MIN_FORMULA_OCCURRENCES`** |

---

## 4. Do two-token formulas deserve to be in the graph?

**Recommendation: keep all 2,038, and flag 59 of them for the architect's decision.**

The brief's premise was that 41% at two tokens "is short enough that many are shared
function words rather than formulae". Measured, that premise does not hold.

### 4.1 Reading 20 of them

Sampled deterministically at even intervals down the mantra-count ranking
(`scratchpad/formulas/m4_twotoken.py`), with three occurrences of each read against the
corpus. A representative selection:

| formula | mantras | Vedas | one occurrence in context |
|---|---|---|---|
| `agniḥ pṛthivyā` | 6 | RV YV AV | `mūrdhā divo nābhir **agniḥ pṛthivyā** athābhavad aratī rodasyoḥ` |
| `uktham indrāya` | 6 | RV SV AV | `**uktham indrāya** śaṁsyaṁ vardhanam puruniṣṣidhe` |
| `hariḥ pavitre` | 5 | RV SV | `devo devebhyaḥ sutaḥ **hariḥ pavitre** arṣati` |
| `asurasya vīrāḥ` | 4 | RV AV | `ime bhojā aṅgiraso virūpā divas putrāso **asurasya vīrāḥ**` |
| `pavasva madhumattamaḥ` | 4 | RV SV | `indrāyendo marutvate **pavasva madhumattamaḥ**` |
| `vīravatīm iṣam` | 4 | RV SV | `rayiṁ **vīravatīm iṣam** īśānaḥ soma viśvataḥ` |
| `viṣurūpe ahanī` | 3 | RV SV | `apānyad ety abhy anyad eti **viṣurūpe ahanī** saṁ carete` |
| `tapasā brahmacārī` | 3 | AV | `te rakṣati **tapasā brahmacārī** tasmin devāḥ` |
| `sanutar yuyota` | 3 | RV | `yūyaṁ dveṣāṁsi **sanutar yuyota**` |
| `indro vṛtrasya` | 3 | RV | `**indro vṛtrasya** taviṣīṁ nir ahan sahasā sahaḥ` |

**Not one of the twenty is a function-word pair.** They are noun phrases, vocative
formulae, and verb-plus-object collocations — ordinary Vedic phraseology. The weakest in the
sample is `asmabhyaṃ tvā` (3 mantras, RV/SV), and even that is the real shared phrase
`asmabhyaṁ tvā sadhamādam`.

### 4.2 Why the premise fails: `MIN_FORMULA_CHARS` already excludes function-word pairs

The floor is 12 characters on the *collapsed* form. Measured over all 2,038:

- 2-token formulas whose **both** tokens are ≤ 5 folded characters: **0**.
- shortest token of a 2-token formula, folded length: min 1, p10 4, median 6, max 23.

Two Sanskrit particles fold to well under twelve characters, so the pair can never clear the
floor. The guard the brief worried about was already doing its job.

### 4.3 They are collocations, not accidents

Observed adjacency against chance adjacency (`obs / (count(w1)·count(w2)/total_tokens)`)
over 292,874 corpus tokens:

| percentile | lift |
|---|---|
| min | 2.2x |
| p1 | 9x |
| p5 | 33x |
| p25 | 258x |
| median | **1,144x** |

Every one of the 2,038 is attested adjacently, and the *least* surprising of them is still
twice chance.

### 4.4 They are not resting on weak evidence

| tokens | formulas with **no** word-aligned occurrence anywhere |
|---|---|
| 2 | **0 of 2,038** |
| 3–8 | **0 of 2,787** |

Every formula in the layer has at least one occurrence where a real edition divides its
words at both ends of the span. There is no "letters-only" subset to drop. 2-token
occurrence methods split 8,738 word-aligned / 1,203 sandhi-substring; for 3+ tokens,
11,839 / 906.

### 4.5 What *is* wrong: 59 formulas that are one content word plus one token of grammar

The real defect in the short formulas is a different shape. Exactly **nine** tokens in the
corpus exceed `MAX_FORMULA_CORPUS_SHARE = 0.08` per-Veda document frequency:

| token | max per-Veda share | RV / SV / YV / AV | class |
|---|---|---|---|
| `ā` | .1821 | .1821 / .1198 / .0719 / .0971 | preverb |
| `na` | .1647 | .1647 / .1546 / .0785 / .0805 | negation |
| `te` | .1490 | .1082 / .0710 / .1256 / .1490 | enclitic pronoun |
| `tvā` | .1246 | .0458 / .0651 / .1246 / .0611 | enclitic pronoun |
| `ca` | .1202 | .0729 / .0493 / .0896 / .1202 | conjunction |
| `no` | .1075 | .1075 / .0889 / .0795 / .0800 | enclitic pronoun |
| `indra` | .0896 | .0896 / .0564 / .0137 / .0478 | **theonym** |
| `pra` | .0861 | .0861 / .0835 / .0370 / .0587 | preverb |
| `sa` | .0827 | .0730 / .0624 / .0435 / .0827 | pronoun |

The set is nine items, so this is an enumeration produced by measurement, not a
hand-written stoplist.

**The rule.** *A two-word formula one of whose tokens exceeds `MAX_FORMULA_CORPUS_SHARE`
per-Veda document frequency and is closed-class.* This is the guards' own reasoning applied
one level down: if a span above 8% of a Veda is that Veda's grammar, then a two-word span
half of which is above that line is half grammar, and the node carries one word of content.

**The count: 59 formulas, 296 `USES_FORMULA` rows, 50 of them making a cross-Veda claim.**
The worst offenders show the pathology plainly — one word, five separate "formulae", four of
them claiming three or four Vedas:

| mantras | formula | Vedas | grammar token |
|---|---|---|---|
| 16 | `no mitrāvaruṇā` | RV SV YV AV | `no` |
| 16 | `ā mitrāvaruṇā` | RV SV YV AV | `ā` |
| 4 | `no mitrāvaruṇāv` | RV AV | `no` |
| 15 | `te dyāvāpṛthivī` | YV AV | `te` |
| 10 | `dyāvāpṛthivī ā` | RV YV AV | `ā` |
| 9 | `no dyāvāpṛthivī` | RV YV AV | `no` |
| 15 | `bṛhaspatiḥ sa` | RV YV AV | `sa` |
| 6 | `bṛhaspatiḥ pra` | RV YV AV | `pra` |
| 7 | `antarikṣam sa` | RV YV AV | `sa` |
| 8 | `brahmāṇas tvā` | RV SV AV | `tvā` |

The family layer cannot fix these: `ā mitrāvaruṇā` and `no mitrāvaruṇā` contain each other
nowhere, so containment leaves them as two separate four-Veda families. They are in the Q1
after-list above, and they should not be.

**`indra` is excluded from the rule, and the exclusion is stated rather than buried.** It is
the one content word above the line, and its pairs are attested vocative formulae rather
than a word plus its grammar: `maghavann indra` stands in 19 mantras of all four Vedas,
`sakhāya indra` in 20, `indra girvaṇaḥ` in 21, `indra vṛtrahan` in 13. Including it would
take the recommendation from **59 to 97 formulas**, from 296 to 533 edges, and from 50 to 83
cross-Veda claims. Both counts are given so the architect can decide either way.

**Frequency alone cannot make this decision, and that is the finding.** I tested a
neighbour-entropy discriminator to separate promiscuous particles from theonyms
automatically; it works only at a threshold of 9.0 bits, which sits in the 0.05-bit gap
between `indra` (8.97) and `pra` (9.02). A threshold fitted that tightly to spare four
probes I chose myself is taste wearing a measurement's clothes, so I am not proposing it.
The nine-token enumeration with one stated exception is the honest form of this rule.

**59 false positives are present in that list and I am not hiding them.** `pra maṃhiṣṭhāya`
(RV/SV/AV) is genuinely from `pra maṃhiṣṭhāya gāyata`; `vardhantu tvā` and
`na śravasyavaḥ` are real. That is exactly why this is a recommendation list with
per-row evidence — `grammar_token`, `grammar_token_share`, `mantra_count`,
`occurrence_count`, `vedas`, `cross_veda` — and not a deletion. **No formula was removed
from any source artifact.** `test_the_recommendation_is_returned_and_never_applied`
asserts that recommended formulas are still present in the built layer.

The rule is deliberately not extended to longer formulas: at three words it flags 314 nodes
and 1,530 edges, most of them real refrains in which a particle is genuinely part of the
phrase.

---

## 5. What was produced

```
720 families, 2,037 member rows
rejected  formula_in_no_containment_relation              2788
rejected  secondary_core_below_variant_similarity_floor    194
note      formulas_read                                   4825
note      formulas_accounted_for                          4825
note      containment_pairs                               1593
note      formulas_strictly_contained_in_another          1103
note      members_by_role          {'CORE': 914, 'EXPANSION': 1119, 'VARIANT': 4}
note      families_with_a_secondary_core                   157
note      families_by_containment_depth       {2: 589, 3: 115, 4: 16}
note      families_by_veda_span   {1: 105, 2: 212, 3: 296, 4: 107}
note      cross_veda_families                              615
note      cross_veda_families_parallel_corroborated        534
note      families_reaching_three_or_more_vedas            403
note      mantras_covered_by_a_family                     4943
note      occurrence_rows_covered_by_a_family            12172
note      removal_recommendations                           59
```

`2,037 members + 2,788 unfamilied = 4,825 formulas read.` The accounting closes exactly, and
`test_real_artifact_accounts_for_every_formula_it_read` asserts it.

### 5.1 Formulas left unfamilied, and why

**2,788 of 4,825 (57.8%).** A formula in no containment relation with any other formula is
not a family of one; it is a formula, and calling it a single-member family would make every
family count meaningless. They are counted as a rejection rather than emitted, and they
remain fully queryable as `Formula` nodes. This is the expected majority: only 2,037
formulas were ever nested, and the layer's job is the nested ones.

### 5.2 Known residual: containment is blind to word order

Two families can be the same phraseology reordered, and containment cannot merge them
because neither string contains the other.

- Measured exactly: **2 groups / 4 families** whose cores are the same tokens in a different
  order — `daivyā hotārā` (17m) beside `hotārā daivyā` (5m), and `haribhir yāhi` (9m)
  beside `yāhi haribhir` (4m).
- Reordering *plus* inflection is not counted by that test and is visible in the Q1/Q2
  output: `viśvā bhuvanā` (60m, 14 members) and `bhuvanāni viśvā` (39m, 9 members) are one
  phrase in two families.

Fixing this needs a bag-of-tokens or alignment criterion, which is a different derivation
and would need its own floor and its own justification. Not attempted; reported.

### 5.3 Determinism

Three independent guarantees, all checked:

1. `--verify-determinism` builds twice over the same input and compares SHA-256 of both
   artifacts. Passes.
2. `--shuffle-input` permutes both source artifacts with a fixed seed and compares digests.
   Passes — `formula_family_members.jsonl` digest
   `0510000bb604313cd31945edb0c60c7f574f904ab6ae33c3e20b0da2e4de8508` is identical across
   permutation.
3. `test_the_representative_does_not_depend_on_input_order` is exhaustive over all
   permutations of a deliberately tie-heavy family, not sampled.

Every intermediate is sorted before it can reach the output, the union-find always attaches
the larger identity to the smaller, and no set or dict iteration order is observable.

---

## 6. Checks

| check | result |
|---|---|
| `ruff check src tests scripts` | **0 errors in the three files I wrote** (`ruff check` on those three paths: *All checks passed*). 36 errors repo-wide, none of them mine: 27 in `src/vedagraph/domain/` (`tiers.py` E501 ×20, `theonyms.py` I001/E501/RUF005, `ontology.py` F602), 6 in other agents' untracked `scripts/`, plus `enrich/agentive.py` ×2 and `graph/entities.py` ×1. |
| `mypy` (strict, 152 files) | **0 errors in my files.** 5 remaining, all in untracked `src/vedagraph/domain/theonyms.py`. |
| `pytest tests/enrich/test_formula_families.py -q` | **38 passed** |
| `pytest tests/enrich -q` (whole package) | **174 passed** — nothing pre-existing regressed |

**Concurrency note.** The repository has other agents active in it during this session, so
the repo-wide lint counts are a moving target: the total fell from 38 to 36 while I worked,
and `src/vedagraph/enrich/corpus.py`, `src/vedagraph/graph/loader.py`,
`src/vedagraph/graph/entities.py`, `data/registry/concepts.yaml` and the `domain/` modules
carry another agent's uncommitted changes (the non-RV attribution work). **I modified no
existing file.** `git status` shows exactly four additions from me:
`src/vedagraph/enrich/formula_families.py`, `scripts/build_formula_families.py`,
`tests/enrich/test_formula_families.py`, and this report. The `corpus.py` change is not
mine and does not affect this layer's measurements — the only thing I read from the corpus
is `surfaces.script_folded`, and that change touches traditional attribution.

Two of those 38 tests failed on first run and both failures were real, not fixture noise:

- `test_family_evidence_...` caught **a defect in my own evidence code**: evidence drawn
  from the representative alone cannot prove a Veda that only a non-core member reaches, so
  the family `agnirmūrdhā divaḥ kakutpatiḥ pṛthivyā` claimed four Vedas and shipped
  three-Veda evidence.
  `_family_evidence` now draws from every member, preferring the core within each Veda, and
  the test asserts `len(vedas) == min(veda_span, MAX_FAMILY_EVIDENCE_SPANS)` on all 720
  families.
- `test_a_second_spelling_...` was a bad fixture of mine (two disconnected components), now
  built to mirror the real `yo smān dveṣṭi` structure.

---

## 7. Errors found in prior reports

| claim | source | verdict |
|---|---|---|
| "1,103 strict substrings" | `GRAPH_ENRICHMENT_V1.md` §M2 | **correct** — reproduces exactly on the collapsed identity surface |
| "number **not reproducible** (1,039, not 1,103) … the number is 6.2% high" | `KNOWLEDGE_MODEL_V3_BASELINE_AUDIT.md` §B7, §6.6 | **withdraw** — measured `normalized` and `display_form`, neither of which is the formula's identity. Both figures are right about their own surface. |
| "8,159 of 22,686 (36.0%) `USES_FORMULA` edges hang off a contained formula" | `BASELINE_AUDIT` §6.6 | **8,502 (37.5%)** on the identity surface |
| "`match_level` blank on ~70% of reuse edges" | this brief | **understates it** — 70.1% is right for `REUSES_TEXT_FROM` and 68.7% for the four parallel types, but `USES_FORMULA` is blank on **22,686 of 22,686 (100%)** |
| "`cross_veda = true` on 3,643 of 4,825 (75.5%)" | V2, reproduced by `BASELINE_AUDIT` | **reproduces exactly** |
| "longest containment chain: 4 levels" | `BASELINE_AUDIT` §6.6 | **reproduces exactly** — `{1: 3722, 2: 920, 3: 164, 4: 19}` |
| "the `yo 'smān dveṣṭi` family alone occupies six nodes … 326 `USES_FORMULA` edges" | `GRAPH_ENRICHMENT_V1_ADVERSARIAL_QA.md` Attack 4 | **understates the family** — it is **11** members and 359 occurrence rows once containment is closed over the component; the six nodes listed are the six largest |

---

## 8. What this layer does not do

- **It does not touch the graph, the ontology, any registry, or any existing module.** New
  files only, plus this report. Loading is the architect's.
- **It does not delete anything.** The 59 removal candidates are a recommendation list with
  per-row evidence and they are still present in the built layer.
- **It does not fix `MIN_FORMULA_OCCURRENCES = 3`,** which is the actual blocker on Q3 and
  on per-passage cross-Veda formula questions generally. Lowering it to 2 would surface
  RV 1.1.1's three Samavedic spans, and the guard's stated reason for refusing —
  "two occurrences is a coincidence of sandhi as often as it is a formula" — has never been
  measured against a gold set. That is a decision for the architect and it is the single
  highest-value follow-up this work identified.
- **It does not merge word-order variants** (§5.2), and it does not split the 157
  multi-core families (§2.5). Both are stated with counts rather than papered over.
