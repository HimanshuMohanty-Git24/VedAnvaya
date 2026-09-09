# VedaGraph V3.1 — Adversarial Re-attack

**Agent F, second pass.** Companion to `V3_1_ADVERSARIAL_FINAL.md`, which is unmodified and
remains the record of the first pass. Strictly read-only: no `CREATE`/`MERGE`/`SET`/`DELETE`/
`REMOVE`, no source or data edits. This is the only file written.

| Field | Value |
| --- | --- |
| Scope | Verify the four claimed fixes; re-attack classes 1 and 2; re-run timing and invariants |
| **Graph measured** | **108,777 nodes / 265,289 relationships** — matches the coordinator's figure exactly |
| Delta from pass 1 | −1,468 relationships, and **only** those (see R-5/R-6) |
| Invariant gate | 0 failing, 2 warning, **18** checked (was 17) |

## Answer to the three questions asked

1. **Is the CRITICAL genuinely cleared?** **Yes.** F-1 as I raised it is properly fixed, and
   the fix is better than the one-line change I proposed.
2. **Did the changes introduce anything new?** One new **CRITICAL** and one new **MAJOR**. The
   CRITICAL was not *introduced* by the fix — it was **exposed** by it, in the column the fix
   added, and it is the same defect class on the same query and the same claimed-cleared
   questions.
3. **Would I sign off a 0-CRITICAL verdict?** **No.** Plainly: the gate is still unmet.

| Severity | Pass 1 | Fixed | New | **Now** |
| --- | --- | --- | --- | --- |
| CRITICAL | 1 | 1 | 1 | **1** |
| MAJOR | 7 | 4 | 1 | **4** |
| MINOR | 6 | 0 | 4 | **10** |

---

## Part 1 — the four claimed fixes, verified against rows

### F-1 — VERIFIED FIXED, and the fix improved on my proposal

I ran the query as written rather than the fragment, because the thing most likely to defeat
it is `UNION ALL` row ordering — an `ORDER BY` inside a union branch orders within the
branch, and if the reconciling row surfaced first the fix would be undone.

It does not. 22 rows, and the reconciling row is index **21**, last:

```
[0]  WARRIOR                                              20
[1]  TERRESTRIAL                                          18
...
[20] NOCTURNAL                                             2
[21] NO_AXIS_ASSIGNED (not an axis; reported so the 214 reconcile)   101
```

Reconciliation checked independently: 214 `Devata`, all 214 carry an axis, and
`unspecified_AND_a_real_axis` = **0**, so the 21 ranked rows cover 113 deities and the final
row covers 101. 113 + 101 = 214. Correct.

The added `structures` column and the caveat's `dv.structure = 'INDIVIDUAL'` pointer are a
better response than the filter I asked for — they name the real problem rather than hiding
the symptom. That is also what surfaced R-1 below.

### F-2 — VERIFIED FIXED, and the catalogue swept

Agni's row now reads, per Veda, `[passages, certain, probable, ambiguous, default_scope]`:

```
Agni    2543 naming / 1708 default / 831 certain / 877 probable / 835 ambiguous
        [AV 476, 0, 170, 306, 170] [YV 276, 0, 97, 179, 97] [SV 187, 0, 82, 105, 82]
Indra   3566 / 3566 / 3566 / 0 / 0
```

The bare `0` beside 476 is gone, all three tiers are visible so no column can be read as
presence or absence alone, and the ranking is on `default_scope` (Agni rank 2 at 1,708).

**Catalogue sweep, as asked.** Six queries touch `referent_certainty`:

| query | serves | certainty handling | verdict |
|---|---|---|---|
| `devatas_named_in_all_four_vedas` | 1,21,34,36,44 | all 3 tiers + `$tiers` default | fixed |
| `devata_mention_certainty_by_veda` | 29,30,45,46 | certainty is a returned dimension, no filter | correct |
| `deity_mention_surface_forms` | 42,45,46 | certainty per surface form | correct |
| `rv_family_books_versus_outer_books` | 24,30,36 | `IN $tiers` = CERTAIN+PROBABLE | correct |
| `rudra_profile_no_shiva` | 43 | all 3 tiers | correct |
| `soma_certainty_across_the_corpus` | 17,**45**,**46** | CERTAIN + AMBIGUOUS only — **PROBABLE dropped** | **R-2, MAJOR** |

So there was one I was asked to look for, and it is not the legitimate case it was believed
to be. See R-2.

### F-7 — VERIFIED FIXED, and the generalisation is clean

`ABOUT_CONCEPT` now has exactly one `run_id` (`…42e33f1e03a7310e`) at **24,969**, and the
relationship total fell by exactly 1,468. The new invariant
`predicates_carrying_more_than_one_run_id` is present and reports 0.

I did not stop at the invariant, since it was written by the person I am auditing. I ran the
generalisation the coordinator asked for, over both relationships and nodes, and over
`build_pass` and `pipeline_version` as well as `run_id`:

```cypher
MATCH ()-[r]->() WHERE r.run_id IS NOT NULL
WITH type(r) AS t, collect(DISTINCT r.run_id) AS runs
WHERE size(runs) > 1 RETURN t, runs
```
→ **0 rows.** Same query over nodes → one hit, `SemanticAssertion` with two run_ids
(`…agentive-assertions:6cbe63b2` and `…semantic-claude-opus5-v3.2-448-new-v1`). That is two
genuinely different layers, and it matches the TIER_B/TIER_D separation I verified as clean
in pass 1 (2,406 SANSKRIT vs 2,459 TRANSLATION). Legitimate, not a survivor set.

`pipeline_version` over nodes → 0 rows with more than one value. `build_pass` → see R-5,
which is a caution about the property rather than a defect.

**No other layer has the F-7 shape.**

### F-4 and F-5 — VERIFIED FIXED

`conditions_treated`'s caveat now names `VG:CONCEPT:TAKMAN-FEVER` and its 33 mentions,
states that the old text was denying an entity the same database returns, and converts the
original reasoning into a live hazard ("the takman- paradigm is split across two entities, so
a query filtering on either alone undercounts fever"). That is the right move — it preserves
the true part of the old caveat instead of just deleting it.

`rivers_and_tribes` now computes the census in the query. I verified every figure
independently:

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
WITH count(DISTINCT p) AS rp, count(DISTINCT r) AS rn
MATCH (p2:Passage)-[:MENTIONS_ENTITY]->(t:Tribe)
RETURN rn AS rivers, rp AS river_passages, count(DISTINCT t) AS tribes,
       count(DISTINCT p2) AS tribe_passages
```
→ `8 rivers / 243 passages / 5 tribes / 37 passages`, matching the returned census string
exactly. The substantive zero still holds. Because the figure is now computed rather than
written down, this caveat cannot go stale again — which is the general fix, not the local one.

---

## Part 2 — the new CRITICAL

### R-1 (CRITICAL) — `deities_by_axis` still returns a wrong top-ranked member: WARRIOR's 20 is 3 deities counted eleven ways

This is the coordinator's own stated worry, realised — but tighter than "scoped per query
rather than per question". It is scoped **per defect instance rather than per defect class,
inside a single query.** The UNSPECIFIED inflation was removed; the composite inflation
underneath it was not.

WARRIOR ranks first at 20. Only **3** of those 20 are `structure = 'INDIVIDUAL'`:

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis) WHERE ax.axis <> 'UNSPECIFIED'
WITH ax.axis AS axis, count(dv) AS all_structures,
     sum(CASE WHEN dv.structure = 'INDIVIDUAL' THEN 1 ELSE 0 END) AS individual_only,
     sum(CASE WHEN dv.structure IN ['PAIR','GROUP'] THEN 1 ELSE 0 END) AS composite
RETURN axis, all_structures, individual_only, composite ORDER BY all_structures DESC LIMIT 4
```

```
axis               all   individual   composite
WARRIOR             20        3          16
TERRESTRIAL         18        7          10
FIRE_MEDIUM         14        5           8
RITUAL_SUBSTANCE    13        5           7
```

The 20 members, in full — **thirteen are "Indra and X" dyads**:

```
INDIVIDUAL : Brhaspati · Indra · Indra accompanied by the Maruts
ABSTRACT   : Manyu, battle-fury
GROUP      : the Maruts · the Maruts, Rudra and Visnu
PAIR       : Agni and Indra · Agni and the Maruts · Indra and Agni · Indra and Brahmanaspati
             Indra and Brhaspati · Indra and Parvata · Indra and Pusan · Indra and Soma
             Indra and Usas · Indra and Varuna · Indra and Vayu · Indra and Visnu
             Indra and the Maruts · Rnancaya and Indra
```

**The double-count is provable from the graph, which is what removes the "a dyad does occupy
the role" defence:**

```cypher
MATCH (c:Devata)-[:HAS_AXIS]->(:DeityAxis {axis:'WARRIOR'}) WHERE c.structure IN ['PAIR','GROUP']
MATCH (c)-[:COMPOSED_OF]->(comp:Devata)-[:HAS_AXIS]->(:DeityAxis {axis:'WARRIOR'})
RETURN c.display_label AS composite, collect(comp.display_label) AS components_also_counted
```

```
Indra and the Maruts   → [the Maruts, Indra]      Indra and Brhaspati → [Brhaspati, Indra]
Indra and Soma         → [Indra]                  Indra and Pusan     → [Indra]
Indra and Vayu         → [Indra]                  Indra and Agni      → [Indra]
Indra and Brahmanaspati→ [Indra]                  Agni and Indra      → [Indra]
Agni and the Maruts    → [the Maruts]
```

Nine composites each re-count a component that is separately a member of the same axis. So
"WARRIOR: 20 deities" is Indra counted eleven times under different dyad labels, the Maruts
twice, and Brhaspati twice. It is not twenty deities.

**And the query's own caveat hands the reader the filter that reverses the ranking.** Applying
`dv.structure = 'INDIVIDUAL'`, exactly as the new caveat advises:

```
TERRESTRIAL 7 · ABSTRACT_PERSONIFICATION 6 · COSMIC_SOVEREIGN 6 · SOLAR 6
AQUATIC 5 · FIRE_MEDIUM 5 · RITUAL_SUBSTANCE 5 · SPEECH 5      ... WARRIOR 3
```

**WARRIOR leaves the top eight entirely.** The query ranks on a number its own documentation
tells you not to use, and returns `collect(DISTINCT dv.structure)` — a set, not counts — so
the reader cannot recover the corrected ranking from the output.

**Why CRITICAL.** `deities_by_axis` serves **Q20, Q38, Q41, Q46**; Q38 and Q46 are claimed
cleared. It is a wrong top-ranked member — the first canonical `MISLEADING` shape — on a
claimed-cleared question, delivered by the obvious named query. And
`V3_1_CLOSURE_STRIKE_FINAL_REPORT.md` §9 records the Q38 fix in these words: *"Composites
excluded from the per-deity leaderboard."* That is true of `deity_widest_range`, which I ran
and which is correctly topped by Indra. It is false of the second query answering the same
question, so the project's own declared standard is applied inconsistently between two
queries serving one benchmark question.

I have applied exactly the severity logic I used in pass 1. Softening this to protect the
result would be the failure mode I was hired to prevent.

**Fix, comparable in size to the last one:** return
`sum(CASE WHEN dv.structure = 'INDIVIDUAL' THEN 1 ELSE 0 END) AS individual_deities` beside
`deities`, and `ORDER BY individual_deities DESC`. No new ontology, no new data — `structure`
is already on all 214 nodes. Whatever ranking is chosen, the same choice must be made in
`deity_widest_range` and `deities_by_axis` together, or Q38 has two answers again.

---

## Part 3 — the new MAJOR

### R-2 (MAJOR) — `soma_certainty_across_the_corpus` drops the PROBABLE bucket, on Q45 and Q46

This is the query believed to be the one legitimate remaining CERTAIN-only case, "where the
certain/ambiguous contrast IS the question". It is not legitimate, for a reason the contrast
framing hides: it does not *contrast* three tiers down to two, it **omits** one, and it
returns a total that then fails to reconcile.

Live output:

```
veda  extraction_path          deity_certain  ambiguous  passages
RV    rv-lemma-annotation           240          688       950
SV    sanskrit-surface-token          0          116       213
AV    sanskrit-surface-token          0          178       204
YV    sanskrit-surface-token          0          109       145
```

Against the rows:

```cypher
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:SOMAH'})
RETURN p.veda AS veda, count(m) AS total,
       sum(CASE WHEN m.referent_certainty='DEITY_CERTAIN'   THEN 1 ELSE 0 END) AS certain,
       sum(CASE WHEN m.referent_certainty='DEITY_PROBABLE'  THEN 1 ELSE 0 END) AS probable,
       sum(CASE WHEN m.referent_certainty='DEITY_AMBIGUOUS' THEN 1 ELSE 0 END) AS ambiguous
```

```
SV  total 213  certain 0  probable  97  ambiguous 116     <-- 97 in no column, 46% of SV Soma
YV  total 145  certain 0  probable  36  ambiguous 109
AV  total 204  certain 0  probable  26  ambiguous 178
RV  total 950  certain 240 probable 22  ambiguous 688
```

For the Sāmaveda the columns read `0 certain / 116 ambiguous` beside `213 passages`. The
missing 97 are `DEITY_PROBABLE` — **inside the default scope** — and they are the largest
PROBABLE count Soma has anywhere. A reader computing the residual 213 − 116 = 97 will
attribute it to something unclassified, when those are precisely the mentions the V3.1 work
promoted to answerable.

The query's `question` field is *"Where is a deity's name certainly the deity, and where
cannot we tell?"* — a two-way framing that predates the three-way split and was never
revised. Its caveat does not mention `DEITY_PROBABLE` at all. It serves Q17 and the
claimed-cleared **Q45** and **Q46**.

MAJOR rather than CRITICAL: it is a missing column with a visible non-reconciliation rather
than a wrong top-ranked member, and the mitigation is a third `count(DISTINCT CASE …)` plus a
reworded question.

---

## Part 4 — new MINOR findings

### R-3 (MINOR) — the new `deities_by_axis` caveat's own breakdown is short by one

The caveat states: *"Of the 101, only 22 are structure = INDIVIDUAL: 29 are ABSTRACT, 22
HUMAN, 16 GROUP, 7 PATRON_PRAISE, 4 PAIR."* Those six figures sum to **100**, not 101. The
full value space, enumerated rather than assumed:

```cypher
MATCH (dv:Devata)-[:HAS_AXIS]->(:DeityAxis {axis:'UNSPECIFIED'})
RETURN dv.structure AS structure, count(*) AS c ORDER BY c DESC
```
```
ABSTRACT 29 · HUMAN 22 · INDIVIDUAL 22 · GROUP 16 · PATRON_PRAISE 7 · PAIR 4 · UNSPECIFIED 1
```

There is a **seventh** value, `structure = 'UNSPECIFIED'` with one member, which the caveat
does not name. Mitigated by the fact that the returned `structures` column does include it,
so the reader sees it even though the prose does not. Small, but it is a counts-block drift
inside a fix written to remove a counts-block drift — the exact recurrence pattern worth
recording.

### R-4 (MINOR) — "all 90 queries under 300 ms" is now false

Full re-run: 90 queries, 0 errors, median **4.9 ms**, one query over 300 ms. I timed the
offender seven times to separate variance from a regression:

```
textual_versus_interpretive, 7 runs (ms): [360.6, 307.4, 335.0, 291.0, 292.3, 326.3, 316.3]
min 291.0  max 360.6  over 300ms: 5 of 7
```

It straddles the threshold and exceeds it more often than not. This is **not** a regression
from the fixes — that query was not changed, and it measured 296.1 ms in pass 1, i.e. it was
always at the boundary. The claim simply has no margin and should be restated to a bound the
machine can actually hold. Everything else improved: `rv_family_books_versus_outer_books`
fell 158 → 68 ms and `ritual_profile` 199 → 27 ms.

Also noted: `rivers_and_tribes` is no longer a zero-row query (it returns the census row), so
the catalogue's zero-row set is now `unlabelled_product_nodes`, `internal_leakage_check` and
`orphan_domain_entities` — all three of which are checks where 0 is the pass condition.

### R-5 (MINOR) — `build_pass` is a per-run nonce and must not be used as a staleness signal

Every `build_pass` hash in the graph changed between my two passes while **every edge count
held constant** (verified across all 66 relationship types; the only delta in the entire graph
is `ABOUT_CONCEPT` 26,437 → 24,969). Examples: `MENTIONS_DEVATA` `aac8f41f` → `40cbeac6` at
17,165 both times; `BELONGS_TO_FAMILY` `39fb92cf` → `cf8625bb` at 305; `MEMBER_OF_FAMILY`
`37939843` → `c5a2ae87` at 2,037.

So `build_pass` is regenerated per projection regardless of whether output changed. Two
consequences:

- The new invariant is correctly built on **`run_id`**, not `build_pass`. If anyone extends
  it to `build_pass`, `PERFORMED_BY` will fire as a false positive: it holds two values
  (`9ac13cb…` 16 edges, `9f79b944…` 3 edges) because two *layers* write that predicate and
  only one re-ran, not because 3 edges are stale.
- `build_pass` cannot answer "was this edge produced by the current build", which is the
  question F-7 turned on. Only `run_id` can.

### R-6 (MINOR) — F-13 recurred: the projection re-ran inside the promised freeze

Between the statement "the graph is now genuinely frozen: nothing is writing to it" and my
re-attack, the V3 projection re-ran across roughly ten layers (R-5 is the evidence). I am
confident this is **benign and is the mechanism by which the fixes were applied** — a
loader-driven projection is the correct way to make these changes, and every count reconciles
with the coordinator's account to the edge. But it is the second pass in which the freeze
claim was made about a graph that had just been rewritten, and the first pass's F-13 was
accepted as a methodological breach on exactly this ground. Recording it so the pattern is
visible: a re-projection is a write, even when it is idempotent.

Nothing in this report depends on the distinction, because I re-measured everything after the
change.

### R-7 (MINOR) — two opposite conventions for `attribution_precision` on non-passage edges

The rescoped invariant's rationale is that `attribution_precision` on a
`Formula`→`FormulaFamily` edge is a category error, and the formula layer now explicitly
`REMOVE`s it — 2,037 + 2,037 edges without it. But `BELONGS_TO_FAMILY`
(`Rishi`→`RishiFamily`, equally without a Passage endpoint) **keeps** it:

```cypher
MATCH ()-[r:BELONGS_TO_FAMILY]->() RETURN r.attribution_precision AS ap, count(*) AS c
```
→ `CONTAINER_INHERITED, 305`

Both choices are argued in writing — the ṛṣi report defends keeping it on the grounds that
every ṛṣi index states its patronymic at container level, and the invariant comment defends
removing it as a category error. Neither is wrong on its own terms, but the graph now answers
"does a non-passage edge carry `attribution_precision`?" both ways depending on the layer.
One convention, applied twice, would be better than two defensible ones.

---

## Part 5 — re-attack on classes 1 and 2

### Class 1 — misleading answers on the changed queries

I re-ran **every** query serving Q20, Q38, Q41 and Q46, because per-question rather than
per-query scoping was the specific concern.

- **Q20** — `deity_profile` (Indra, correct), `deity_actions_performed` (tops Indra/`IS_OR_BECOMES`,
  correct), `agni_deity_fire_medium` (single-deity, returns `ambiguous_fire_mentions` as its
  own column — good), `deities_by_axis` → **R-1**.
- **Q41** — `natural_phenomena_personified` (tops `sun (sūrya)` at 3, which is the deliberate
  three-figure refusal I verified in pass 1), `av_deity_ascription_descriptors` (returns
  `precision` and `layer_veda_scope` as columns — correct), `deities_by_axis` → **R-1**.
- **Q38 / Q46** — `deity_widest_range` correctly topped by Indra; `deity_profile`,
  `deity_action_repertoire_breadth`, `action_predicate_breadth`, `deity_reach_named_versus_ascribed`,
  `agni_deity_fire_medium`, `theonym_ambiguous_mentions` all clean;
  `devatas_named_in_all_four_vedas` now fixed; `deities_by_axis` → **R-1**;
  `soma_certainty_across_the_corpus` → **R-2**.

So of the four questions touching the fixed query, all four still reach R-1, and two also
reach R-2.

### Class 2 — theonym leakage after the change

- `referent_certainty` value space re-enumerated: `DEITY_CERTAIN 8,340 / DEITY_AMBIGUOUS 6,806
  / DEITY_PROBABLE 2,019`, 17,165 total, 0 missing — unchanged by the fixes, and
  `mention_edges_with_retired_certainty_value` is 0, so no fourth value crept in.
- The per-deity per-Veda residual zeros are unchanged and still correctly typed
  `INSUFFICIENT_EVIDENCE` (Pṛthivī SV, Uṣas YV, Vāc ×3, Āpaḥ ×3). The F-2 fix did not widen a
  tier to make the table look complete, which was the specific hazard.
- The default scope now actually reaches the reader in `devatas_named_in_all_four_vedas` and
  `rv_family_books_versus_outer_books`. It still does not in
  `soma_certainty_across_the_corpus` (**R-2**).
- No default query returns an AMBIGUOUS-driven answer.

---

## Part 6 — negative findings from this pass

Recorded because each was a real suspicion about the fixes themselves.

1. **The rescoped invariant hiding the 4,074.** `edges_without_attribution_precision` (warn,
   4,074) became `passage_edges_without_attribution_precision` (ok, 0). Narrowing a check's
   surface until it passes is the exact shape that has falsely certified an absence in this
   repository twice, so I tested it. It is clean: all 4,074 remain in the graph and are
   **exactly** `HAS_FORMULA` 2,037 + `MEMBER_OF_FAMILY` 2,037, both with no `Passage`
   endpoint, and 0 passage-touching edges lack the property. The rationale in the source is
   better than the check it replaced, and records that a prior ad-hoc `SET` of `PER_PASSAGE`
   on those twins was correctly reverted by the reproducible projection. Genuine improvement,
   not a rescoping to pass.
2. **`UNION ALL` letting the reconciling row sort to the top.** Ran the exact query; it is
   row 21 of 22. Clean. (Caution for later: a `LIMIT` added to this query would truncate the
   reconciling row and break the 214.)
3. **The 214 failing to reconcile after the split.** 113 ranked + 101 unranked = 214, and 0
   deities carry both UNSPECIFIED and a real axis. Clean.
4. **The F-7 deletion taking innocent edges with it.** All 66 relationship type counts
   compared against pass 1: every one identical except `ABOUT_CONCEPT`, down by exactly
   1,468. Node count unchanged at 108,777. Clean.
5. **The F-7 shape surviving elsewhere.** Generalised sweep over `run_id`, `build_pass` and
   `pipeline_version`, on relationships and nodes. 0 predicates with >1 live `run_id`. The one
   node-level hit (`SemanticAssertion`, 2 run_ids) is two real layers matching the verified
   TIER_B/TIER_D split. Clean.
6. **Other CERTAIN-only filters beyond the one disclosed.** All six certainty-touching
   queries audited individually; five are correct and the sixth is R-2. No undisclosed
   additional case. Clean.
7. **A regression in query latency from the rewrites.** Both rewritten queries are fast
   (`deities_by_axis` and `devatas_named_in_all_four_vedas` both ~35 ms), and the only
   over-300 ms query was untouched and was already at the boundary. Clean.
8. **Q86's substance regressing.** Re-checked: `fire (agni)` still 1 personification, six
   `EPITHET_VARIANT_OF` edges intact. Clean.

---

## Verdict

**CRITICAL: 1. MAJOR: 4. MINOR: 10. I would not sign off a 0-CRITICAL verdict.**

The four fixes I was asked to verify are all real, and two of them (the query-time census in
`rivers_and_tribes`, the run-reconciliation invariant from F-7) fix the *class* rather than
the instance, which is the right instinct and worth saying.

But `deities_by_axis` still answers "which functional role do the most deities occupy" with
WARRIOR, and WARRIOR is first only because Indra is counted eleven times under eleven dyad
labels. That is a confidently wrong answer to Q38 and Q46, both claimed cleared, from the
obvious named query, and the closure report states in terms that composites were excluded
from the per-deity leaderboard for Q38. The fix I asked for was applied to the symptom I
named and the same wrong-top-ranked-member defect remained one layer down in the same query —
which is, precisely, the thing the coordinator said they were most worried about repeating.

**What I would fix first:** rank `deities_by_axis` on individual deities and make
`deity_widest_range` and `deities_by_axis` agree, in one change, so Q38 has one answer. Then
add the `probable` column to `soma_certainty_across_the_corpus` and reword its question to
the three-way scheme. Both are small; neither needs new data.

Remaining open, unchanged from pass 1 and accepted as backlog rather than claimed cleared:
F-3 (`Condition` never split), F-6 (rite recall mis-scoped onto non-locus Vedas), F-8 (the
ṛṣi-family layer unreachable from the catalogue), F-9 (`serves` gaps on Q86/87/88/90), F-10
and F-11 (the vṛddhi claim and the `source_variants` channel), F-12, F-14.
