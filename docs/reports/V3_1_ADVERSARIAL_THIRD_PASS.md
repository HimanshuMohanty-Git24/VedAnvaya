# VedaGraph V3.1 — Adversarial Third Pass (narrow)

**Agent F, third pass.** Companions: `V3_1_ADVERSARIAL_FINAL.md` (pass 1) and
`V3_1_ADVERSARIAL_REATTACK.md` (pass 2), both unmodified. Strictly read-only; this is the
only file written this round.

**Scope, as set:** verify R-1, R-2, R-3; confirm `deities_by_axis` and `deity_widest_range`
give one answer for Q38; judge the R-4 withdrawal; look once for the R-1 *shape* elsewhere in
the `Devata` population. Nothing already cleared twice was re-audited.

| Field | Value |
| --- | --- |
| Graph measured | **108,777 nodes / 265,289 relationships** — unchanged from pass 2, freeze held |
| `HAS_AXIS` edges | 289 |

## Verdict

| Severity | Pass 2 | Closed | New | **Now** |
| --- | --- | --- | --- | --- |
| **CRITICAL** | 1 | **1** | 0 | **0** |
| MAJOR | 4 | 1 | 1 | **4** |
| MINOR | 10 | 2 | 4 | **12** |

**I will sign off 0 CRITICAL.** There is no third CRITICAL underneath this one. I say why, and
how I tested for one, in §5 — because I found the same defect *family* one level down and
deliberately did not escalate it, and that decision should be auditable rather than taken on
trust.

---

## 1. R-1 — CONFIRMED FIXED, and the fix is right in kind

Re-ranking rather than filtering was the correct choice, and it survives the checks I could
think of to break it.

**Ranking.** Ranks on `individual_deities`. `TERRESTRIAL` 7 leads; then
`ABSTRACT_PERSONIFICATION` 6, `COSMIC_SOVEREIGN` 6, `SOLAR` 6, four at 5. **WARRIOR is absent
from the top eleven** at 3 individual / 20 subjects.

**Nothing dropped.** Summing the returned rows:

```
rows = 22
sum all_subjects       = 289    <-- equals the HAS_AXIS edge count exactly
sum individual_deities = 101
sum pair+group+other   = 188
rows where individual+pair+group+other <> all_subjects : []
```

289 = 289, and every one of the 22 rows reconciles internally. The inflation is returned as
data, not suppressed.

**Three things I tried in order to break it, all clean:**

- **Column inflation from duplicate edges.** `count(CASE WHEN … THEN dv END)` is not
  `count(DISTINCT …)`, so a repeated `(deity, axis)` edge would inflate silently.
  `MATCH (dv:Devata)-[r:HAS_AXIS]->(ax) WITH dv, ax, count(r) AS n WHERE n>1 RETURN count(*)`
  → **0**. Safe.
- **NULL leakage into the example lists.** `collect(CASE WHEN … END)` collects a NULL per
  non-matching row in some engines. Checked every row of both list columns → **0 NULLs**.
- **`UNION ALL` re-ordering the reconciling row to the top.** It is row 21 of 22, last.
  (Standing caution: a `LIMIT` added to this query later would truncate that row and silently
  break the 214 reconciliation.)

## 2. R-2 and R-3 — CONFIRMED FIXED

**R-2.** `soma_certainty_across_the_corpus` now returns `deity_probable`, and every row
reconciles against the rows I measured independently in pass 2:

```
RV  240 + 22 + 688 = 950 ✓     SV  0 + 97 + 116 = 213 ✓
AV    0 + 26 + 178 = 204 ✓     YV  0 + 36 + 109 = 145 ✓
```

The 97 Sāmavedic `PROBABLE` mentions — 46% of SV Soma, the largest PROBABLE count Soma has
anywhere — are now visible instead of falling between two columns.

**R-3.** The caveat's breakdown now sums correctly, and I re-enumerated the value space rather
than checking the arithmetic: `ABSTRACT 29 · HUMAN 22 · INDIVIDUAL 22 · GROUP 16 ·
PATRON_PRAISE 7 · PAIR 4 · UNSPECIFIED 1` = **101**. The seventh value is named.

## 3. Q38 — one answer. Requirement HOLDS, with one latent hazard

The caveat asserts "`structure` is the reliable discriminator, and it is what
`deity_widest_range` uses, so the two queries now agree on what a deity is." That claim is
**true but not for the stated reason**, because `deity_widest_range` filters on
`dv.is_composite = false AND dv.structure = 'INDIVIDUAL'` — it still uses `is_composite`.

I tested whether the extra clause changes anything:

```cypher
MATCH (dv:Devata) WHERE dv.structure = 'INDIVIDUAL' AND dv.is_composite = true
RETURN dv.display_label
```
→ **0 rows.** `is_composite = true` occurs only on `structure = 'PAIR'` (14 of 38). So on
this data the conjunction is exactly equivalent to `structure = 'INDIVIDUAL'` alone, and the
two queries genuinely do agree. **Requirement met.**

But it holds by a coincidence of the data, not by construction — see **T-4**.

**Residual the two queries share (so they still agree):** `Indra accompanied by the Maruts`
is `structure = INDIVIDUAL`, so it counts as an individual deity in `deities_by_axis` and
appears at rank 6 of `deity_widest_range` with `attributed = 0`, alongside `Indra` at rank 1.
Indra therefore occupies two rows of the Q38 leaderboard and is counted twice on
`COSMIC_SOVEREIGN` and `ATMOSPHERIC`.

**My judgement, as asked.** Do not retype the registry row. `indra marutvān` is a *qualified*
ascription whose referent is Indra himself, not a dyad of co-equals, so `INDIVIDUAL` is
defensible and arguably correct. The problem is that it is a second node for one deity — which
is precisely what `EPITHET_VARIANT_OF` exists to express, and it already carries the
comparably periphrastic `the self of Agni` → `Agni`. So this is a **missing edge in the
epithet layer**, not a typing error, which is both better scoped and a loader change rather
than a query change. It folds into T-1.

## 4. R-4 — the withdrawal is honest, not a dodge

I verified the replacement claim independently rather than reading it:

```
90 queries, 0 errors
worst 3: textual_versus_interpretive 338.8 · model_adjudicated_edges 205.2 · model_adjudicated_review_trail 190.0
under 240 ms: 89 of 90
median: 4.1 ms
```

**"89 of 90 under 240 ms" is true**, with the second-worst query at 205–216 ms across runs, and
the median claim (4.4 ms) matches my 4.1–4.9 ms.

The caveat does four things a dodge would not: it names the false claim and states it "is
therefore false and is not made"; it gives the measured range (222–361 ms) rather than a
flattering single figure; it explains the mechanism (`MATCH ()-[r]->()` over 265,289 edges,
cost proportional to the graph, cannot be indexed away); and it cites the adversarial
measurement that refuted it. It also substitutes a bound that is actually meaningful for this
project (well under the 1 s batch-label threshold). **Adequate.** Closed.

## 5. The shape sweep — and why there is no third CRITICAL

I swept all 39 queries over the `Devata` population for the R-1 shape: counting or ranking
subjects without discriminating individual deities. One query flagged (`action_predicate_breadth`,
T-2), and inside `deities_by_axis` itself I found the same defect family one level down.

**`individual_deities` has two further inflation mechanisms beyond composites.**

*Epithet variants.* `EPITHET_VARIANT_OF` (6 edges) is not resolved:

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
WHERE ax.axis <> 'UNSPECIFIED' AND dv.structure = 'INDIVIDUAL'
OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
RETURN ax.axis AS axis, count(dv) AS as_ranked_now,
       count(DISTINCT coalesce(base, dv)) AS epithet_resolved
ORDER BY as_ranked_now DESC
```

```
FIRE_MEDIUM        5 → 2    members: Agni, Apam Napat, Agni Jatavedas, Agni Pavamana,
                                     Agni the slayer of demons   <-- Agni counted 4×
RITUAL_SUBSTANCE   5 → 4
SPEECH             5 → 4
```

*Registry duplicates.* Six `Devata` labels exist as two nodes with two `entity_key`s, at
least four of them pure orthographic variants:

```
Dadhikra              DADHIKRA / DADHIKRAH              both INDIVIDUAL, both on DAWN_TIME
the two divine Hotrs  DAIVYAU-HOTARAU / DEVYAU-HOTARAU  both PAIR, both on PRIESTLY
Heaven and Earth      DYAVABHUMI / DYAVAPRTHIVYAU       both PAIR, both on TERRESTRIAL
Agni and the Maruts   AGNIH-MARUTAH / AGNAMARUTAH       both PAIR
the All-Gods          VISVEDEVAH / VISVE-DEVAH          both GROUP
the course of becoming BHAVAVRTTAM / BHAVAVRTTHAM       both ABSTRACT
```

**So why is this MAJOR and not CRITICAL?** Because I applied the same test I applied in pass 2
— does the correction move the top-ranked member? — and this time the answer is no. Fully
corrected for *both* mechanisms at once:

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
WHERE ax.axis <> 'UNSPECIFIED' AND dv.structure = 'INDIVIDUAL'
OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
RETURN ax.axis AS axis, count(dv) AS as_ranked_now,
       count(DISTINCT coalesce(base.display_label, dv.display_label)) AS fully_corrected
ORDER BY fully_corrected DESC, axis
```

```
axis                      as_ranked_now   fully_corrected
TERRESTRIAL                     7               7
ABSTRACT_PERSONIFICATION        6               6
COSMIC_SOVEREIGN                6               6
SOLAR                           6               6
AQUATIC                         5               5
ATMOSPHERIC                     4               4
```

**The top six are identical.** In pass 2 the same test moved WARRIOR from rank 1 to outside
the top eight — a wrong top-ranked member, the shape the frozen benchmark's `MISLEADING`
verdict turns on, and I escalated. Here the leader and the whole head of the leaderboard are
stable, the affected rows are mid-table, and the query's own `individual_examples` column
prints `Agni, Agni Jatavedas, Agni Pavamana, Agni the slayer of demons` side by side so the
inflation is visible in the output rather than concealed. That is a wrong count, not a wrong
answer.

I want this distinction on the record because it is the only thing standing between a
0-CRITICAL and a third NOT_READY, and it is a test, not a judgement call: the identical query
run against the identical criterion returned "leader moves" in pass 2 and "leader stable" in
pass 3.

---

## 6. New findings

### T-1 (MAJOR) — `individual_deities` is not deduplicated: FIRE_MEDIUM reports 5 individual deities where there are 2

`deities_by_axis` (Q20, Q38, Q41, Q46) ranks on `individual_deities` without resolving
`EPITHET_VARIANT_OF` or the six duplicate-label registry pairs. `FIRE_MEDIUM` reads 5 and is
2 — Agni counted four times, under `Agni`, `Agni Jatavedas`, `Agni Pavamana` and `Agni the
slayer of demons`. `RITUAL_SUBSTANCE` 5→4, `SPEECH` 5→4, `DAWN_TIME` inflated by the
`Dadhikra`/`Dadhikraḥ` pair, and Indra double-counted on `COSMIC_SOVEREIGN` and `ATMOSPHERIC`
via `Indra accompanied by the Maruts`.

Two reasons this is a MAJOR rather than a MINOR despite not moving the leader:

1. **The mechanism already exists and is already used in the same module.**
   `natural_phenomena_personified` (Q41, Q46 — overlapping questions) does
   `OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base) WITH n, coalesce(base, dv) AS resolved`,
   and that is exactly how the closure report's Q86 fix took fire from 5 personifications to
   1. So one query over the deity population resolves epithets and the query that *ranks* does
   not — the same two-conventions-for-one-question pattern as R-1, one layer down.
2. A 150% overstatement on a named row (5 vs 2) is a figure a reader would quote.

**Fix:** `count(DISTINCT coalesce(base.display_label, dv.display_label))` with the
`OPTIONAL MATCH` already used by the sibling query, plus one `EPITHET_VARIANT_OF` edge from
`Indra accompanied by the Maruts` → `Indra` in the loader. Apply to `deity_widest_range` in
the same change, or Q38 diverges again.

### T-2 (MINOR) — `action_predicate_breadth` counts 31 "deities" of which 20 are individual

Serves Q18, **Q38, Q46**. Its Devata population is 24 INDIVIDUAL, 5 PAIR, 5 GROUP, 2 ABSTRACT.
`MOVES_TO` reads `deities: 31`, of which 20 are individual deities.

Not escalated: the top-ranked member is `MOVES_TO` under all three measures (31 as ranked, 20
individual-only, 31 epithet-resolved), and the substantive answer to "which actions spread
across many deities" is unchanged. Mid-table reorders modestly (`PERCEIVES` 8th → 5th). The
caveat is otherwise unusually careful — it explains the `count(DISTINCT)` choice, distinguishes
"narrow because specific" from "narrow because uncovered", and states the RV-only scope — it
simply does not say the 31 mixes subjects with deities. One clause would fix it.

### T-3 (MINOR) — the `is_composite` diagnosis understated itself: false on 24 of 38 PAIRs, not five

The conclusion (do not use `is_composite`) is right and I confirm it. The supporting figure is
low by a factor of five:

```cypher
MATCH (dv:Devata) WHERE dv.structure = 'PAIR' AND dv.is_composite = false
RETURN dv.display_label ORDER BY dv.display_label
```
→ **24 rows**, not 5. The five named are the Indra-dyads; the list also holds `Heaven and
Earth`, `the Asvins`, `Dawn and Night`, `Agni and Surya`, `Vac and the Waters`, `Suna and
Sira`, `the mortar and pestle`, `the two dogs of Sarama`, `the two oblation carts` and more.
`is_composite` is unusable across 63% of the PAIR population, not 13%. Flagged only so the
closure report does not carry "five".

### T-4 (MINOR) — `deity_widest_range`'s `is_composite = false` clause is a latent Q38 divergence

It is currently a no-op (§3: zero nodes are `INDIVIDUAL` and `is_composite = true`), so the
two queries agree today. But the caveat now *asserts* they agree on the basis of `structure`,
while one of them still gates on a property the same caveat calls unreliable. A single
registry pass setting `is_composite = true` on an `INDIVIDUAL` row — or on
`Indra accompanied by the Maruts`, which is the obvious candidate — silently gives Q38 two
answers again, with no invariant to catch it. Delete the redundant clause so the agreement is
structural rather than incidental.

### T-5 (MINOR) — the `Devata` registry holds 6 duplicate-label pairs, so "214 deities" is ~208 entities

Listed in §5. Four are plain orthographic variants (`DADHIKRA`/`DADHIKRAH`,
`VISVEDEVAH`/`VISVE-DEVAH`, `BHAVAVRTTAM`/`BHAVAVRTTHAM`, `AGNIH-MARUTAH`/`AGNAMARUTAH`); two
are alternative dvandva forms of one referent. They inflate every denominator over the
`Devata` population, including the new `individual_deities` and `pair_subjects` columns
(`PRIESTLY`'s `pair_subjects = 4` counts `the two divine Hotrs` twice; `TERRESTRIAL`'s
`pair_subjects = 7` counts `Heaven and Earth` twice), and the headline "14 of 214 composite".
A data-layer finding, not a query one, and no effect on any top-ranked answer.

---

## 7. Standing open, unchanged

MAJOR: **F-3** (`Condition` never split into affliction and cause), **F-6** (rite recall
mis-scoped onto non-locus Vedas), **F-8** (the ṛṣi-family layer unreachable from the
catalogue), **T-1**.

MINOR: **F-9** (`serves` gaps on Q86/87/88/90), **F-10**, **F-11** (the vṛddhi claim and the
`source_variants` channel), **F-12**, **F-14** (the Cartesian shape undefended), **R-5**
(`build_pass` is a per-run nonce), **R-6** (the freeze breach — held this round), **R-7**
(`attribution_precision` conventions), **T-2**, **T-3**, **T-4**, **T-5**.

Closed this pass: **R-1** (CRITICAL), **R-2** (MAJOR), **R-3** (MINOR), **R-4** (MINOR, by
honest withdrawal).

## 8. Sign-off

**CRITICAL: 0. MAJOR: 4. MINOR: 12. I sign off the 0-CRITICAL verdict.**

No named query in the catalogue now returns a confidently wrong answer to a benchmark question
the reports claim cleared. The three passes converged the way an adversarial process should:
each fix exposed the next layer of the same defect, and the last layer changes counts without
changing answers.

Two things I would fix before anyone quotes this catalogue in print, neither gate-blocking:
**T-1**, because a 5-vs-2 count is quotable and the fix is one `OPTIONAL MATCH` already
written elsewhere in the same file; and **T-4**, because Q38's single answer currently rests on
data coincidence rather than construction.

The one structural lesson worth carrying out of all three passes is the one now stated in the
closure report: this project's fixes have repeatedly been scoped to the *defect instance* —
one query, one caveat, one bucket — where the defect was a *class*. The UNSPECIFIED bucket,
then the composites underneath it, then the epithet variants underneath those, were three
strata of one question: what counts as a deity. Each was fixed correctly and each revealed the
next. The generalising moves this session made — the query-time census in `rivers_and_tribes`,
the `predicates_carrying_more_than_one_run_id` invariant — are the right pattern, and there is
no equivalent guard yet for "a query counting the `Devata` population must say which subjects
it counts."
