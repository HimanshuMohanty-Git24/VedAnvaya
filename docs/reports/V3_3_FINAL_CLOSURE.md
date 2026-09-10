# VedaGraph V3.3 — Final Three-Question Closure

| Field | Value |
| --- | --- |
| Starting commit | `01fa006` (branch `semantic-pilot-v1`) |
| Scope | Q10, Q23, Q25 only — the three questions V3.2 graded `MISLEADING` |
| Benchmark graded | `docs/reports/VEDAGRAPH_100_QUESTION_BENCHMARK_V3.md`, frozen, criteria as printed |
| Re-graded record | `docs/reports/V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl` |
| Carried over unchanged | the 97 questions V3.2 did not grade `MISLEADING` |

**Final totals: 11 `FULLY_ANSWERABLE` / 68 `PARTIALLY_ANSWERABLE` / 21 `NOT_ANSWERABLE` / 0 `MISLEADING`.**

The target was never `FULLY_ANSWERABLE`. It was *not `MISLEADING`*. Two of the three landed
below `FULL` and that is the correct outcome, not a shortfall.

---

## Q10 — Which metals occur in each Veda?

**Previous failure.** The corpus's own stored Sanskrit named a sixth metal with no node —
`trapu` (tin) at AVS 11.3.8, the same brahman-odana passage from which lead was harvested.
`metals_by_veda` returned five metals and silently omitted it.

**Root cause.** `ENTITY_RESOLUTION` — class-membership gap producing a silent absence.

**Fix.** Two things, and the second matters more than the first.

*Roster.* Registered `TRAPU-TIN` (`trapu`) and `SYAMA-DARK-METAL` (`śyāmaṃ`, `śyāmam`).
Registering tin alone would have re-broken the question by its own argument: VSM 18.13
enumerates *hiraṇya, ayas, **śyāma**, loha, sīsa, trapu*, and AVS 11.3.7 — one verse before
the tin witness — reads `śyāmám áyo 'sya māṃsāni` and carried no mention edge at all. Only
exact attested inflections are admitted: the bare stem `śyāma` token-matches a verb form at
RV 6.5.7 and sits inside `aśyāma` 22 times, which is the `ayas` rejection policy applied
again.

*Shape.* `metals_by_veda` now returns a complete Metal × Veda grid. This is the reusable
part. A cell that matched nothing says `NO_LEXICAL_MATCH` **in its own row** instead of
going missing, so absence is always readable as a fact about the matcher and never as a
fact about the text. Per-1000-mantra normalisation and the `corpus_mantras` denominator
were added; the normalisation is load-bearing rather than cosmetic, since it reorders gold
from RV-first raw (38 v 34) to AV-first normalised (3.601 v 5.823).

**One cell is knowingly wrong and knowingly disclosed.** The Yajurveda names `ayas` at
VSM 18.13, but the Devanagari writes it with avagraha elision (`मेऽयश् च`), folding to the
token `yaśca` — the relative pronoun in 11 of its 12 corpus occurrences. `ayo` fails the
same precision test at 6 hits, about half of them the metal. Neither could be registered
without manufacturing wrong-sense mentions, so that cell reads `NO_LEXICAL_MATCH`, and the
caveat names the verse and the reason.

**Final verdict: `FULLY_ANSWERABLE`.**

---

## Q23 — What deity communities emerge from the corpus?

**Previous failure.** No community structure exists anywhere in the graph, and the obvious
query returned a confident four-row `deity_a / deity_b` table whose rank-1 and rank-4
members — Rathaviti Darbhya, Vasukra — are typed `structure='HUMAN'` in the registry itself.
A reader got a plausible table where the honest answer was a zero.

**Root cause.** `SCOPE_CONFUSION` compounded by `ENTITY_RESOLUTION` — a pair table
substituted for an absent partition, with non-deities in the deity column.

**Fix.** A new `deity_community_capability` query solely serves Q23 and returns a status
row: `INSUFFICIENT_EVIDENCE`, `assigned_deities`, `eligible_deities`, `pairwise_edges`, and
an `evidence_scope` column that refuses the substitution in the row rather than in a caveat.
Q23 was removed from the three pair queries' `serves`, and those queries now exclude
`structure='HUMAN'`.

**Honest limits of the fix.** Two of those three filters are no-ops — `CO_OCCURS_WITH`
carries zero HUMAN endpoints (306 pairs with the filter, 306 without) — so only the
`deity_co_occurrence` guard does work, cutting it from 4 rows to 2. `eligible_deities: 192`
is the registry minus the 22 HUMAN entries, and still carries 7 dānastuti topic labels and
one non-divine subject; it is a denominator, not a census, and the caveat now says so.

**Final verdict: `NOT_ANSWERABLE`** — the correct grade. The dimension the question asks
about is absent from the graph, and the output now says exactly that.

---

## Q25 — Which ritual objects recur most?

**Previous failure.** `ritual_objects_recurring` ran over a flat 23-member `:Object` class
and returned chariot (473) and thunderbolt (275) as the corpus's most-recurring **ritual
objects** — the two items the criterion names as disqualifying — under a four-word caveat.

**Root cause.** `ONTOLOGY_SEMANTICS` — no ritual-implement class; a lexical ranking over a
flat class presented as a ritual one.

**Fix.** The query is now `Ritual-[:USES_OBJECT]->Object` intersected with the mention
layer. Chariot and thunderbolt are excluded *by construction* rather than by a blocklist —
both are `:Object` nodes with no `USES_OBJECT` edge. `registry_type` is surfaced per row (the
axe is registered a Weapon and is a ritual tool anyway), the count column is named
`matched_mantras_minimum`, and every row carries `PARTIAL_ALIAS_RECALL`.

The `USES_OBJECT` curation was **not** authored this session: `domain_entities_ritual_v3.yaml`
is unmodified in the working tree and landed at `d456cce`, two commits before the grading
that found Q25 misleading. The class is therefore a pre-existing contract, not a whitelist
reverse-engineered to pass.

**Measured, not assumed.** 11 mantras carry a yūpa-word (one the place-name Hariyūpīyā)
against 6 reached — and only 3 of those 6 are yūpa forms, the other 3 arriving through the
`svaravaḥ` alias; neither Yajurvedic witness (VSM 19.17, 25.29) is reached. `vedi` is ~30
attested against 17. `iṣṭakā` is 4 against 1. Factors under 2, so the criterion's
order-of-magnitude clause is met; the residual gap is disclosed in the caveat with these
figures.

**Final verdict: `PARTIALLY_ANSWERABLE`.**

---

## Neighbouring regressions

None. Q1, Q33, Q35, Q36 and Q40 all hold their V3.2 verdicts on live evidence.

Q33 was checked hardest, being the only `FULLY_ANSWERABLE` neighbour:
`deity_pairs_far_above_chance` returns the same 306 pairs topped by Mitra–Varuṇa at lift
13.189 (228 RV / 51 non-RV), byte-identical to the V3.2 record, because the HUMAN filter
matches nothing in that population.

`Devata.structure` was enumerated rather than grepped — INDIVIDUAL 72, ABSTRACT 41, PAIR 38,
GROUP 33, HUMAN 22, PATRON_PRAISE 7, UNSPECIFIED 1, no nulls — so the `<> 'HUMAN'` guard
drops no legitimate deity through a null or an unexpected value.

## Bounded backlog (not fixed here, deliberately out of scope)

1. `deity_profile` still returns `co_devatas: ['Vasukra']` for Indra — a `structure='HUMAN'`
   node in a deity field. It is a Q1 surface; §0 of the closure spec put Devata counting out
   of scope.
2. `deities_through_common_rishis` received no HUMAN or PATRON_PRAISE filter and still
   carries non-deity Anukramaṇī addressees. A Q35 surface.
3. `run_id` hashes only three integers, so two registries with identical counts collide.
4. The Q25 class is soma-centric: `maṇi` (86), `dundubhi` (17) and `audumbara` are genuine
   ritual objects absent only for want of a `USES_OBJECT` edge.

## Verification

| Gate | Result |
| --- | --- |
| Projection idempotence | two consecutive builds byte-identical; 108,779 → 108,779 nodes, 265,295 → 265,295 rels; `newly_created: 0` |
| `sent == landed` | all 14 steps |
| Artifact ↔ live reconciliation | 28,227 rows ↔ 28,227 edges, 0 either side, one `run_id` in both, 229 entities in both |
| Live invariants | 0 failing, 2 pre-existing warnings (M-3; single-constant confidence) |
| pytest | 1555 passed, 39 skipped, 0 failed (offline); 248 domain tests incl. live |
| ruff | clean; touched files formatted |
| mypy --strict | clean, 159 source files |

A provenance defect was caught and repaired during the session: two mention rows had been
hand-written carrying the `run_id` of an earlier 227-entity extraction run whose alias set
did not contain `trapu`. `run_id` is `blake2b(stage, |mantras|, |entities|, |tokens|)`, so
adding an entity must rotate it. A genuine rebuild rotated it honestly across all rows.

## Decisions

```
VEDAGRAPH_ONTOLOGY_WORLD_CLASS_ENGINEERING_READY = true
VEDAGRAPH_ONTOLOGY_FROZEN_FOR_PRODUCT_V1        = true
GRAPH_MODELING_PHASE                            = CLOSED_FOR_PRODUCT_V1
NEXT_PROJECT_PHASE                              = FASTAPI_SEARCH_AND_GRAPH_API
```

This is an engineering / Product-V1 freeze. It does **not** claim perfect Vedic scholarship,
human validation of the semantic extraction, or complete historical knowledge. Future
ontology change requires a reproduced correctness defect, new source data, a concrete
research question that cannot be represented, or a deficiency surfaced by real API/UI usage.
"Make the graph richer" is no longer sufficient. There is no V4.
