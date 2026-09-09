# V3.1 Wave 1 — `FormulaFamily` outward traversal and `SemanticAssertion` predicate normalization

**Agent:** E (Wave 1, deterministic graph plumbing)
**Branch:** `semantic-pilot-v1`, from `d456cce`
**Scope:** ROI ranks 4 and 5 only. Two loader functions, two projection-script
registrations, one test module, both layers projected live and verified.
**Status:** both tasks complete. One premise in the task brief was wrong and is corrected
below; two documented refusals in the codebase were honoured rather than overridden, which
is why Task 2 closes 10.8% of its gap and not 100%.

---

## 1. Headline numbers

| | before | after | delta |
|---|---|---|---|
| Relationships (all types) | 261,584 | **263,887** | +2,303 |
| Nodes (all labels) | 108,689 | **108,689** | 0 |
| `HAS_FORMULA` | 0 (type did not exist) | **2,037** | +2,037 |
| `MEMBER_OF_FAMILY` | 2,037 | 2,037 | 0 |
| `FormulaFamily` | 720 | 720 | 0 |
| `ASSERTION_PREDICATE` | 2,406 | **2,672** | +266 |
| `ActionPredicate` | 41 | **41** | 0 |
| `PERFORMS_ACTION` | 441 | 441 | 0 |
| `IS_ASKED_TO` | 224 | 224 | 0 |
| Edges with no `quality_tier` | 0 | **0** | 0 |

Edge delta reconciles exactly: `2,037 + 266 = 2,303`, and `261,584 + 2,303 = 263,887`. No
other relationship type moved, no node was created or deleted, and the graph-wide
"100% of edges carry grading metadata" invariant holds at the new total.

`PERFORMS_ACTION` and `IS_ASKED_TO` are unchanged on purpose and were checked because they
are the two aggregates derived *from* `ASSERTION_PREDICATE`. They are rebuilt from
assertions carrying a `frame`, and sealed assertions carry none, so the 266 new edges
cannot leak into a TIER_B aggregate. That was a real hazard, and the measurement is the
proof it did not fire.

## 2. Rows sent vs rows landed

Measured by the projection script itself, third consecutive run (i.e. after the layers were
already present — so these numbers are also the idempotence evidence):

```
before: 108689 nodes, 263887 relationships
  ok formula_family_outward     sent=2037     landed=2037
  ok sealed_predicate_edges     sent=266      landed=266
after:  108689 nodes, 263887 relationships
```

`sent` for the mirror is read **live from the graph** (`count` of `MEMBER_OF_FAMILY`), not
from `formula_family_members.jsonl`. Reconciling a mirror against the artifact would hide a
membership pass that landed short — the mirror's contract is with the rows that actually
exist.

`sent` for the predicate layer is the number of `MODEL_EXTRACTION` assertions whose
`semantic_predicate` is in the mapping table, counted before any write.

## 3. Task 1 — `FormulaFamily` outward traversal

### 3.1 A correction to the brief: nothing was declared

The brief states that `src/vedagraph/domain/ontology.py` "already anticipates the outward
predicate". **It does not.** Verified by enumerating every `REL_*` constant in the module
(52 of them) and grepping `ontology.py`, `schema.py`, `tiers.py` and `schemas/`:

- `FORMULA_MEMBER_OF` — the name in `KNOWLEDGE_MODEL_V3_FINAL_REPORT.md` (§395, item 7) —
  is declared **nowhere**. It exists only as prose in that report.
- `HAS_FORMULA` — the name in `V3_1_ROI_PLAN.md` (rank 4) — was likewise declared nowhere.
- `RELATIONSHIP_SIGNATURES` had one entry for the family layer, `MEMBER_OF_FAMILY:
  Formula -> FormulaFamily`, and no reverse.

So this was a **mint**, not the population of a declared-and-empty predicate. That matters
because minting is the thing `UNPOPULATED_BY_DESIGN` and the guard on
`DOMAIN_RELATIONSHIP_TYPES` exist to make deliberate, and because "declared, 0 edges" and
"not declared" are different backlog items with different costs.

### 3.2 The name: `HAS_FORMULA`, and why not the close-out's name

I used `HAS_FORMULA` and **did not** adopt `FORMULA_MEMBER_OF`. Reported per instruction
rather than renamed silently: `FORMULA_MEMBER_OF` reads subject-first as *"the formula is a
member of"*, which is the direction that **already existed**. A predicate whose plain
reading contradicts its declared signature is how a query gets written backwards.
`HAS_FORMULA` reads in the direction it points and matches the `HAS_`-prefix convention
every other container-to-contained predicate in this ontology already uses. A test pins
this (`test_the_name_reads_in_the_direction_it_points`).

### 3.3 A finding worth the integrator's attention: "dead end" was overstated

Cypher traverses a relationship in **either** direction at equal cost, so
`MATCH (fam:FormulaFamily)<-[:MEMBER_OF_FAMILY]-(f:Formula)` always worked. The family was
never *unreachable*.

What was true is that the family was not **navigable** in any *directed* reading of the
graph: the generated ontology reference, which is built from `RELATIONSHIP_SIGNATURES`,
listed `FormulaFamily` with no outward predicate, so a reader asking "what can I do from a
family?" was told — correctly, from the declared contract — nothing. That is a real defect
and worth fixing. But the integrator should know that the fix is **denormalization for the
sake of the declared contract and the directed surfaces**, not the removal of a traversal
blocker, and it costs 2,037 duplicate edges. If the project would rather pay nothing and
fix the *generator* to render inbound predicates on a sink label, this change is
reversible in one `DELETE` and one ontology entry. I did the work as ranked and frozen, and
I am flagging the trade rather than re-deciding it.

### 3.4 Design: a mirror, not a re-derivation

`load_formula_family_outward(session)` copies the `MEMBER_OF_FAMILY` edges **that are in
the graph**:

```cypher
MATCH (f:Formula)-[m:MEMBER_OF_FAMILY]->(fam:FormulaFamily)
MERGE (fam)-[h:HAS_FORMULA]->(f)
SET h = properties(m),
    h.asserts = $outward_asserts,
    h.mirrors = 'MEMBER_OF_FAMILY',
    h.build_pass = $build_pass
```

Four properties of this are load-bearing:

1. **`SET h = properties(m)` is a *replacing* assignment.** Grading parity is structural,
   not restated. The four similarity-threshold `VARIANT` rows stay `TIER_D` outward
   because they are `TIER_D` inward, not because a second `CASE` reproduced the split. A
   restated grade is a second opinion, and a directionality repair is not entitled to one.
   It also means a property the inbound edge *stops* carrying disappears from the mirror on
   the next pass, rather than lingering — the hazard the existing
   `REMOVE r.attribution_precision` in the membership query exists for, solved structurally
   instead of by remembering to unset each casualty by name.
2. **Both `MATCH` clauses are labelled and both endpoints keyed.** "Copy every membership
   edge" is exactly the shape that invites `MATCH ()-[m:MEMBER_OF_FAMILY]->()`, which is
   the pattern that once created 39,461 bogus edges here. A test asserts the query text
   contains no `()`.
3. **`build_pass` is overwritten after the copy.** The inbound edge's own `build_pass`
   arrives inside `properties(m)`; left there, the sweep could never distinguish a mirror
   this pass wrote from one a previous pass left.
4. **Mark and sweep.** `MERGE` adds and never retracts, so a membership that disappears
   upstream must take its mirror with it. `retired_stale_mirrors` = **0** on this run
   (nothing to retract yet), and the mechanism is tested by the same route the membership
   pass's sweep is.

`asserts` is the one property the mirror restates, because the inbound text is written from
the formula's side and read off the outward edge it would be the wrong way round. It is
prose, not a grade; every graded field is copied untouched, and a test enumerates which
fields the query may assign (`asserts`, `mirrors`, `build_pass` — and nothing else).

### 3.5 Verified: grading parity and usefulness

| check | result |
|---|---|
| `HAS_FORMULA` edges | 2,037 |
| …with `quality_tier` / `grade_basis` / `evidence_basis` / `knowledge_layer` / `role` | 2,037 / 2,037 / 2,037 / 2,037 / 2,037 |
| **grading parity failures** (role, tier, basis, layer or `membership_id` differing from the inbound twin) | **0** |
| ungraded mirrors | 0 |
| families reachable outward | **720 / 720** |
| outward by role | `CORE` 914, `EXPANSION` 1,119, `VARIANT` 4 |
| outward by tier | `TIER_B` 2,032, `TIER_D` 5 |

The tier split is `2,032 / 5`, not the `2,033 / 4` the loader docstrings quote. That is not
drift I introduced — it is the inbound distribution, copied exactly. The fifth `TIER_D` row
is an `EXPANSION` graded down by the `NOT row.has_containment_support` branch of
`_MEMBER_TIER_CASE` rather than by the `similarity` branch, so both numbers are right about
different things and the prose in `load_formula_families` quotes only the similarity four.
Minor and pre-existing; noted so it is not later read as a mirror bug.

Structure is genuinely useful, not merely connected. Navigation checked live:

- **Representative navigation (Q60):** all **720** families reach their
  `representative_formula_id` in one outward hop, and the representative's role is `CORE`
  in **720 / 720** cases. `representatives_unresolvable` = 0.
- **Core/variant navigation (Q8, Q58):** the largest 4-Veda family resolves to
  `viśvā bhuvanā` ("all beings") as `CORE` with `abhi yo viśvā bhuvanā`,
  `bhayante viśvā bhuvanā`, `imā viśvā bhuvanāni`, `te viśvā bhuvanāni` and others as
  `EXPANSION`. Correct and legible.
- **Two-hop reach (Q81):** `(:FormulaFamily)-[:HAS_FORMULA]->(:Formula)<-[:USES_FORMULA]-(:Passage)`
  works; the top 4-Veda families reach 93, 60, 53, 48 and 41 distinct passages.
- The 5 `TIER_D` rows surface with their method and similarity on the edge
  (`formula-family-variant-by-similarity-v1`, 0.763–0.858), so the weak rows remain
  filterable from the family side.

### 3.6 Counts-block drift: none found

This is the repository's known defect class, so it was measured per family against the
edges that actually landed, not sampled:

| recorded field | families disagreeing with real edges |
|---|---|
| `member_count` | **0 / 720** |
| `core_count` | **0 / 720** |
| `variant_count` | **0 / 720** |

`representative_coverage` was not audited: it is a ratio over occurrence counts, not a
count of edges, so there is no edge population it summarises. `secondary_core_count` and
`expansion_count` are deliberately excluded from the drift check — `SECONDARY_CORE` is not
a stored `role` value, so the node field and the edge field are not the same partition and
a mismatch between them would not be drift. Both exclusions are documented in
`_FAMILY_COUNT_FIELDS`.

The audit is not a one-off script: `_counts_block_drift` runs inside the loader on every
projection and reports the offending `family_id`s (capped at 20 per field), not just a
total. A drift report that says only *how many* families disagree repeats the
"read the audit block instead of the rows" mistake one level up.

## 4. Task 2 — `SemanticAssertion` predicate normalization

### 4.1 The gap was real, and the diagnosis in the brief was right

- 4,865 `:SemanticAssertion` nodes: 2,406 `MORPHOLOGY_RULE`/`TIER_B`, 2,459
  `MODEL_EXTRACTION`/`TIER_D`.
- `ASSERTION_PREDICATE` reached exactly the first 2,406. The 2,459 carry their predicate as
  the node property `semantic_predicate`.
- Checked that this was not already covered elsewhere: relationship types `DESCRIBES`,
  `INVOKES`, `REQUESTS` etc. **do** exist in the graph, but every one of them carries
  `run_id = vedagraph-graph-enrichment-v1:semantic:fc3293cc…` — an older, separate
  enrichment layer, not the sealed run. The sealed layer's predicate axis genuinely had no
  edge representation.

### 4.2 `semantic_predicate` is a closed 13-value vocabulary — and it is not the action axis

Measured, not assumed:

| sealed `semantic_predicate` | assertions | disposition |
|---|---:|---|
| `DESCRIBES` | 734 | withheld |
| `DESCRIBES_ACTION` | 553 | withheld |
| `REQUESTS` | 395 | withheld |
| **`INVOKES`** | **211** | **mapped** |
| `REFERS_TO_PLACE` | 122 | withheld |
| `INVOLVES_SUBSTANCE` | 117 | withheld |
| `REFERS_TO_NATURAL_PHENOMENON` | 100 | withheld |
| `INVOLVES_RITUAL` | 78 | withheld |
| **`PRAISES`** | **55** | **mapped** |
| `INVOLVES_OFFERING` | 46 | withheld |
| `EXPRESSES` | 27 | withheld |
| `ASSOCIATED_WITH` | 17 | withheld |
| `CONTRASTS_WITH` | 4 | withheld |
| | **2,459** | |

Because the property is a closed controlled vocabulary, projecting it needs **no
judgement about individual assertions** — the only judgement is per-vocabulary-value, 13
decisions, which is what the brief's timebox anticipated.

The decisive fact is that the two halves **do not share a predicate axis**:

- The sealed 13 are *discourse relations between a passage and a referent*. No verbal root,
  no morphological argument frame.
- `:ActionPredicate` is a closed set of 40 *verbal-root action classes* from
  `data/registry/action_predicates.yaml`, each with an `argument_frame` over
  morphological cases, plus `UNMAPPED_ROOT` (41 nodes).

Exactly two names occur in both sets.

### 4.3 Mapped: 2 of 13, 266 edges

| sealed value | registry gloss | assertions | edges landed |
|---|---|---:|---:|
| `INVOKES` | "calls a divine being to attend" | 211 | **211** |
| `PRAISES` | "sings, extols or magnifies" | 55 | **55** |
| | | | **266** |

Both are name-identical **and** gloss-compatible with sealed usage (the 211 `INVOKES`
assertions are overwhelmingly `object_kind = CANONICAL_ENTITY_REF` resolving to a deity,
which is precisely "calls a divine being to attend"). That makes the mapping deterministic
rather than interpretive.

### 4.4 Unmapped residual: 2,193 of 2,459 (89.2%), each refused with a reason

I did **not** mint predicate nodes for the other eleven. Three independent reasons, none of
them a shortage of effort, all recorded in `_SEALED_PREDICATE_WITHHELD` and echoed into the
run report so a reader can disagree with them:

1. **`REQUESTS` (395) — the registry rules against it by name.**
   `action_predicates.yaml` states: *"REQUESTS_FROM is not a predicate here. It is a
   grammatical frame, not a verb class … Modelling it as a predicate would force every
   request to lose its content (Indra REQUESTS_FROM ???)."* The agentive layer already
   carries the same fact as `frame = REQUESTED`, orthogonal to the predicate. Minting a
   `REQUESTS` predicate node would reintroduce the exact confusion the registry documents
   rejecting.

2. **`DESCRIBES_ACTION` (553) — `sealed_semantics.py` records a reasoned refusal.**
   These are the assertions whose `object_kind` is `EVENT` and whose verb is a free-text
   `action_head`. The module docstring's "One deliberate refusal" says: *"502 distinct
   action heads for 559 events … The mapping would be a fresh interpretation of frozen
   output, which is exactly what 'do not reopen the freeze to make it fit' forbids."*
   Overturning that from a loader is not where that decision belongs. **This is the single
   largest block of the residual and the one an architect could plausibly reopen** — it
   would need the `action_root_map.yaml` route and an explicit decision to reinterpret
   sealed output, which is a wave of its own, not a rank-5 XS task.

3. **The remaining nine (1,245) are not actions at all.** `DESCRIBES`, `REFERS_TO_PLACE`,
   `INVOLVES_SUBSTANCE`, `REFERS_TO_NATURAL_PHENOMENON`, `INVOLVES_RITUAL`,
   `INVOLVES_OFFERING`, `EXPRESSES`, `ASSOCIATED_WITH`, `CONTRASTS_WITH` are
   passage-to-referent (or passage-to-passage) relations with no verbal root and no
   argument frame. There is no registry class any of them is a weaker or stronger form of.
   `ASSOCIATED_WITH` is the clearest case against forcing: it is the relation this graph
   spent a V2 pass *splitting* into `ASSOCIATED_WITH_CONCEPT`, `_PHENOMENON` and
   `_SUBSTANCE`, and giving it a predicate node would re-flatten that.

The governing constraint is the registry's own header: *"A root that does not map into one
of these classes is recorded as UNMAPPED_ROOT and produces no predicate edge. **Adding a
class is a deliberate ontology change, not something an extractor may do because a verse
needed it.**"* A projection that MERGEd eleven new `:ActionPredicate` nodes would have
enlarged a closed, architect-owned vocabulary from inside a loader, and the coverage number
would have looked like progress. Coverage went from 49.5% to **54.9%** of the assertion
layer, and that is the honest number.

Two structural guards make this a decision rather than an omission:

- The edge query **`MATCH`es** the predicate node and never `MERGE`s it. A sealed value
  with no registry node lands nothing and appears in the residual instead of silently
  minting a 42nd `:ActionPredicate`. Verified live: `ActionPredicate` = **41**, distinct
  `vocabulary_version` = **1**.
- `unadjudicated_predicates` is reported every run, and a test reads the sealed artifact
  via `iter_sealed_assertions` and asserts every predicate the run *actually uses* is
  either mapped or explicitly withheld. If the sealed vocabulary ever changes, that test
  fails instead of quietly filing the new value under "unmapped". Current value: **`[]`**.

### 4.5 The layers remain separable — the hard constraint

This was the requirement that most shaped the change. `queries.py` documents that summing
the two assertion layers is "the specific misleading answer this graph exists to refuse",
and before this change `ASSERTION_PREDICATE` carried **`derivation = null` and a uniform
`TIER_B`** on all 2,406 edges — so the type had no way to say which layer an edge came
from even before I touched it.

`load_sealed_predicate_edges` therefore regrades **both** populations from their source
assertion (2,672 edges regraded), not only the 266 it created. Grading only its own
additions would have left the older half depending on `vedagraph.domain.upgrade` — a pass
outside the V3 projection — for a grade the projection is now responsible for.

Measured after the change:

| `derivation` | edges | tier | evidence basis | state | passages | distinct predicates |
|---|---:|---|---|---|---:|---:|
| `MORPHOLOGY_RULE` | 2,406 | `TIER_B` | `SANSKRIT` | `ACCEPTED` | **2,228** | 40 |
| `MODEL_EXTRACTION` | 266 | `TIER_D` | `TRANSLATION` | `CANDIDATE` | **199** | 2 |

Edges missing `derivation` or `quality_tier`: **0**. The reach asymmetry the brief warned
about is not merely preserved but now *visible from the edge*: 2,406 over 2,228 passages
against 266 over 199, and `review_state` rides along too. Every existing query keeps
filtering the layers apart, and can now do it in one hop without reaching the node.
`ASSERTION_PREDICATE` was added to `tiers.LAYER_OWNED_GRADES` so the generic stamper can no
longer re-flatten it — the identical treatment `HAS_SEMANTIC_ASSERTION` already had, for the
identical reason.

### 4.6 Seal verification: intact

Nothing sealed was modified. Verified by re-running the repository's own hash checks rather
than by inspection:

| check | result |
|---|---|
| `output_seal.json` vs recorded `output_seal.sha256` | `8b744be51f27ccff…` = `8b744be51f27ccff…` **MATCH** |
| 448-run `input_freeze.frozen_hashes` (7 entries) resolved to live files by content hash | **7 / 7 unmodified** |
| `git status` on `data/semantic/`, `data/enrichment/`, `data/registry/action_predicates.yaml`, `pyproject.toml` | **clean** |
| files I edited that appear in any hash seal | **none** |

The 7 frozen inputs resolve to: `src/vedagraph/semantic/evidence.py`,
`src/vedagraph/semantic/codex_direct.py`, `src/vedagraph/semantic/object_ontology.py`,
`prompts/semantic_extraction_v3.2.md`, `schemas/semantic_extraction_v3.schema.json`,
`src/vedagraph/semantic/ontology.py`, `src/vedagraph/semantic/spans.py` — all unmodified.

**A near-miss worth recording.** The sealed `semantic_ontology_sha256` covers
`src/vedagraph/semantic/ontology.py`. The file I edited is
`src/vedagraph/domain/ontology.py`. Two files named `ontology.py`, one directory apart, one
inside the seal and one outside it. Editing the wrong one would have broken the seal while
looking like exactly the right change.

Two **pre-existing** mismatches were found while sweeping every freeze manifest, and they
are not mine: `docs/manifests/rigveda_semantic_execution_v3_1_freeze.draft.json` (71 files,
2 mismatched: `semantic/codex_direct.py`, `semantic/full_run.py`) and
`rigveda_semantic_full_run_freeze.draft.json` (67 files, 2 mismatched:
`semantic/full_run.py`, `semantic/v3.py`). Both are **draft** manifests for the Luna v3/v3.1
runs, not the sealed 448 run, and all three files hash **identically at `HEAD` and in the
working tree** — so the drafts are stale relative to `HEAD` and predate this wave. Note that
`codex_direct.py` matches the 448 run's `execution_contract_sha256` exactly, so it is the
*draft* that is out of date, not the file.

## 5. Code changes

| file | change | diff |
|---|---|---|
| `src/vedagraph/domain/ontology.py` | `REL_HAS_FORMULA` declared with rationale; added to `DOMAIN_RELATIONSHIP_TYPES` and to `RELATIONSHIP_SIGNATURES` as `FormulaFamily -> Formula` | +31 |
| `src/vedagraph/domain/schema.py` | `rel_has_formula_role` index on `HAS_FORMULA(role)` | +5 |
| `src/vedagraph/domain/tiers.py` | `HAS_FORMULA` and `ASSERTION_PREDICATE` added to `LAYER_OWNED_GRADES`, with the reasoning for each | +21 |
| `src/vedagraph/domain/v3_loader.py` | `load_formula_family_outward`, `_counts_block_drift`, `load_sealed_predicate_edges`, `_SEALED_PREDICATE_MAP`, `_SEALED_PREDICATE_WITHHELD` and their queries | +475 |
| `scripts/build_knowledge_model_v3.py` | layers `formula_family_outward` and `sealed_predicate_edges` registered in `LAYERS` and in `steps`; run-order docstring extended with constraints 4 and 5 | +21 |
| `tests/domain/test_v3_1_formula_and_assertion.py` | new: 11 offline contract tests, 4 live | 341 lines |

Line counts are **my additions only**. The working-tree diff on `v3_loader.py` and
`build_knowledge_model_v3.py` is larger because other Wave 1 agents added loaders and
layer registrations to the same two files concurrently; my two registrations were
re-verified present after their edits landed.

Both layers are reachable through `--only` and re-run idempotently. Run order is documented
in the script's module docstring as constraints 4 and 5, alongside the three that were
already there.

Gates: `ruff check` clean, `mypy --strict` clean (156 source files).

## 6. Tests added

**Offline (11, run in the default suite):**

- `test_has_formula_is_declared_as_the_exact_reverse_of_member_of_family` — the signature is
  the *swap* of its twin's, not a copy. A mirror declared with the same signature is not a
  mirror, and would typecheck and load.
- `test_has_formula_is_a_registered_domain_predicate_with_an_index`
- `test_the_name_reads_in_the_direction_it_points`
- `test_the_outward_mirror_copies_the_grade_instead_of_writing_one` — asserts
  `SET h = properties(m)` and that the query assigns **exactly** `{asserts, mirrors,
  build_pass}` and no graded property. This is the test that keeps a future edit from
  reintroducing a second opinion about tier.
- `test_the_mirror_query_never_uses_an_unlabelled_match`
- `test_both_mirrored_directions_are_owned_grades`
- `test_the_sealed_mapping_only_ever_targets_the_closed_registry_vocabulary` — parses
  `action_predicates.yaml` and asserts the mapping never names a predicate the registry
  does not define.
- `test_every_sealed_predicate_is_either_mapped_or_refused_with_a_reason` — reads the sealed
  artifact and asserts full adjudication, so a change to the sealed vocabulary fails loudly
  instead of growing the residual.
- `test_a_mapped_predicate_is_never_also_refused`
- `test_every_refusal_carries_a_substantive_reason`
- `test_assertion_predicate_grade_is_layer_owned`

**Live (4, marked `live` and gated on `VEDAGRAPH_LIVE_NEO4J`, matching
`test_v3_layers.py`):** one mirror per membership with identical grading; no family count
disagreeing with the landed edges; the two assertion layers separable on the predicate edge;
the closed vocabulary not enlarged.

Results: **11 passed, 4 skipped** offline; **15 passed** with
`VEDAGRAPH_LIVE_NEO4J=1`. Targeted regression on `test_domain_layer.py`,
`test_v3_layers.py`, `test_being_and_nonbeing.py` and the ontology/guard selection:
**134 passed, 15 skipped, 0 failed**. The full suite was left to the integrator per the
wave instructions.

## 7. Deliberately not done

- **No re-derivation of formula membership.** No substring or containment relationship was
  recomputed. The 241 members that do not directly contain their family's representative
  stay exactly as the membership layer graded them; the mirror copies, it does not
  adjudicate. The brief asked for bounded repair and this is the boundary.
- **`DESCRIBES_ACTION`'s 553 assertions were not mapped** onto the action vocabulary. See
  §4.4(2): `sealed_semantics.py` records a reasoned refusal and a loader is not the place to
  overturn it. This is the largest single unlock still available on the assertion layer.
- **No new `:ActionPredicate` nodes minted.** See §4.4. If the architect wants the eleven
  discourse relations as first-class vocabulary nodes, my recommendation is a **separate
  label** with its own registry rather than additions to `:ActionPredicate`, whose own
  docstring defines it as "one member of the closed action-predicate vocabulary in
  `data/registry/action_predicates.yaml`". That is an ontology change and outside both this
  task's rank and my write partition.
- **`queries.py` untouched**, per the write partition — so no query was updated to *use*
  `HAS_FORMULA`. The predicate, its index and its grading are in place and verified; adding
  a family-first query function is a follow-up for whoever owns that module. Q8/Q58/Q60/Q81
  are unblocked at the graph level and the traversals are demonstrated in §3.5, but no
  named query function ships in this change.
- **No touch to** `MENTIONS_DEVATA`, `Devata`, `DeityGroup`, `DeityAxis`, `Rishi`,
  `RishiFamily`, `DomainEntity`, `Work`, `HAS_QA_ISSUE`. Confirmed by the before/after count
  table: no label or relationship type outside my partition moved.
- **No licensing analysis** (private local project).

## 8. Two hazards for the integrator

1. **Five agents are sharing one working tree, not just one database.** During this wave
   `data/registry/works.yaml`, `src/vedagraph/models/core.py`, `src/vedagraph/domain/upgrade.py`,
   `src/vedagraph/enrich/predicates.py`, `src/vedagraph/graph/*` and others changed under
   me, and another agent twice overwrote files at my scratchpad paths. There is no merge
   step here — last writer per file wins — so `scripts/build_knowledge_model_v3.py`, which
   every agent registering a layer must edit, is the highest-risk file in the wave. Worth
   confirming that every agent's layer registration survived.
2. **`ruff format` is not clean at baseline** — 22 files under `src/` would be reformatted
   at `HEAD`. Running it on the five files I edited (line-length 100 joins the repo's
   split implicit-concatenation strings) therefore produced formatter-only churn beyond my
   additions: roughly 12 lines in `v3_loader.py`, 29 in `build_knowledge_model_v3.py`, 13 in
   `ontology.py`, 6 in `tiers.py`, 2 in `schema.py`. Those files are now `ruff format`
   clean; the rest of the repo is not. If the wave wants a minimal diff, that churn is
   separable, and either way the project should decide whether `ruff format` is a gate,
   because right now it is documented as one and is not met.
