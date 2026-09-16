# Wave 4 — independent adversarial QA and data-completeness closure

Written for: the project owner, reading to decide whether to release.

Branch `phase-data-completeness-v2` · Wave 4 baseline `df102bf` · 13 commits · 2026-09-16

---

## A. Verdict

**`VEDANVAYA_DATA_COMPLETENESS_NOT_COMPLETE`**

**`RELEASE_CANDIDATE = NO`**

The claim that the data-completeness campaign is finished is false, and it is false for a
reason no green gate could have shown: the registry that the claim rested on had **no closed
state**. 84 of its 85 entries read `OPEN`, 67 carried `causation_status:
HYPOTHESIS_NOT_YET_MEASURED` with all 14 addressing diagnostics `NOT_RUN`, and there was no
vocabulary for closure and no field to hold one. A registry in that shape cannot report
completion, because nothing in it can ever be complete.

Now that every entry terminates, the count is:

| | entries |
|---|---:|
| data-completeness closures | **37** |
| separately tracked execution blockers | **8** |
| **still implementation-fixable** | **40** |

Forty entries describe work over material this repository already holds, and the owner's rule
for those is "fix it or report NOT_READY." Wave 4 fixed eleven defects at their generators —
which closed six entries outright — and terminated the rest by measurement, mostly by
discovering that a claim had gone stale because the layer it described had since been built.
It cannot build forty unbuilt layers, and relabelling them `CLOSED_SCOPE_DECISION` was
available and is barred: the audit refuses an uncited scope decision for exactly that reason.

The verdict is **not** `COMPLETE_WITH_EXTERNAL_SOURCE_BLOCKERS`, because the blockers are not
external. Three entries are genuinely source-blocked with all five required evidence fields.
Five are blocked on **owner decisions that were never made**, holding material that was
acquired, staged and then not imported.

---

## B. The largest finding: closure was recorded for work that never landed

The registry records `GAP-TRANSLATION-002` as *"Closed via the Wayback Machine, 944 of 961."*

Measured: the graph holds 4,878 of 5,839 Atharvavedic translations — **exactly the
pre-closure figure**. All 2,254 accepted rows in `data/staging/translation/rows.jsonl` target
mantras that exist in the graph, and **not one of them carries a translation**:

```text
of the staged keys: {'found': 2254, 'with_tr': 0}
```

1,242 of those are **Samavedic**, against `GAP-TRANSLATION-001`, which records the Samaveda as
source-blocked. It is not. The addressing works — the rows are keyed to this corpus's own
canonical keys — and the import gate is shut behind `OWNER_DECISION_A_RV_SPAN` and
`OWNER_DECISION_C_FORCED_ADDRESSES`, with Gate B `UNKNOWN` and Gate C `NOT_RUN` in
`wave3_eligibility.json`. The same pattern holds for the audio and Samaveda-music domains
behind `OWNER_DECISION_E_AUDIO_GATE`.

This is not lost data and it is not dishonesty in the staging work, which is careful and
well-evidenced. It is a **reporting defect with a large consequence**: a reader of the registry
would conclude the Samaveda has no translation because none exists, when 1,242 are sitting one
owner decision away.

Recorded as `BLOCKED_OWNER_DECISION_REQUIRED`, counted apart from the closures, never as one.

---

## C. Defects found and fixed at the generating source

Eleven, each with the generator named and the symptom measured.

| # | Defect | Fixed at | Evidence |
|---|---|---|---|
| 1 | The chandas builder still emitted 33 bracket fragments as metre names | `build_atharvaveda_anukramani.py` | 0 compound values in the regenerated artifact; 39 tests pin 19 malformed strings refused and 16 real metre names with `3-av.`/`6-p.` qualifiers surviving |
| 2 | That builder swapped `sys.stdout` at import time, so pytest could not import it — which is **why** its documented residual shipped | same, moved to `use_utf8_console()` | the module is now testable, and is tested |
| 3 | 28 retired metre identities were public in the world export | M10 marked `:Internal` | public nodes 39,692 → 39,664; 28 literals intact; 33 M9 records still resolving |
| 4 | The orphan gate swept one label family and reported 0 while 28 public orphans sat edgeless | `graph_quality_scorecard.py` | new `orphan_public_nodes` gate over all product labels |
| 5 | `/api/v1/entities/{type}` bypassed the product filter, serving 575 chandas against the inventory's 547 | `entity_service.py`, via `product_filter()` | asserted per registered type, not for chandas alone |
| 6 | A live API caveat denied the Atharvaveda's whole deity-ascription layer (5,385 edges) | `domain/queries.py` | the caveat now names both predicates and the identity-bridge gap |
| 7 | The Rigveda's live scope statement claimed a Padapatha we do not hold | `works.yaml` | all 44,276 `TextVersion` rows carry `text_form: SAMHITA` |
| 8 | 214 `:Devata` nodes told Ask the Atharvaveda has no attribution layer — and `ask/evidence.py` reads that property as an absence qualifier | `domain/taxonomy.py`, propagated by M11 | 0 nodes carry the false fragment |
| 9 | 256 `EXACT_PARALLEL_OF` edges served a null `match_level` while carrying it under `strongest_method` | `graph/lexical.py`, propagated by M12 | 252 renamed, 4 typed absent, 0 left; enrichment's 750 unmoved, checked by value |
| 10 | 15 declared predicates had no endpoint signature, so the signature gate's universe omitted them | `enrich/predicates.py` | 90 of 90 constrained, 0 violations |
| 11 | 8 predicates fell into the Focus view's "Other", including a rite's 3,121 procedural steps | `frontend/src/lib/world/focus.ts` | `pnpm test` 434 passed |

### The chain that mattered most

M10 fixed the graph. The export was re-run and dropped the 28. And
`frontend/public/world/world.labels.json` — **the file a browser downloads** — still carried
all 28 to every reader, because:

1. Both world consumers had recorded `frontend/.world/world.raw.json` as their output. That is
   an *intermediate*, and it is the *same* one for both, so the Lab stage was judged on a file
   its own build never touches: permanently `CURRENT`. The four shipped files and the
   constellation partition were declared by nothing.
2. `build-world.mjs` joins the partition **by position** and never checked its length. It read
   35,370 assignments onto 35,648 nodes without complaint — every node past the first
   divergence taking another node's constellation, and the last 278 reading `undefined` out of
   the end of a typed array.
3. `world.predicates.json` has its own builder and was in no consumer's hash.

All three fixed, the bundle rebuilt, and 0 of 28 malformed labels remain in any shipped
artifact.

---

## D. Gates that could not fail, and what replaced them

| Gate | How it could not fail | Now |
|---|---|---|
| `orphan_entities` | scoped to `:DomainEntity` | `orphan_public_nodes` over every product label, with `ORPHANED_BY_DESIGN` carrying a reason per exempt label |
| `signature_violations` | universe was 75 of 90 predicates; `check_signature` fell through on a missing signature | 90 of 90; the fallthrough is a `raise` and an assert pins `SIGNATURES == CONTROLLED_PREDICATES` |
| `UNPOPULATED_BY_DESIGN` | a claim about the graph that nothing checked against the graph | new `falsely_declared_unpopulated` gate over **both** declaration maps, proven BAD → FAIL twice |
| the Lab dependency consumer | judged on another consumer's output | declares the four shipped files; `classify()` names the file that moved |
| the world bundle build | silent positional mis-join | refuses on a length mismatch, proven BAD → FAIL |
| one API test | began **skipping** when its subject was fixed | inverted to assert the closure |

The ontology reference had the same blind spot the scorecard had in round four, still live: it
read one declaration slice and published *"relationship types live but not declared: 39"* —
`HAS_DEVATA`, `CONTAINS`, `EXACT_PARALLEL_OF` among them — printing "not declared" beside their
endpoints. Now 0.

Scorecard: **11 of 11.**

---

## E. My own errors, recorded

Four, each caught by a check built to catch it rather than by rereading.

1. **The registry audit declared `531` for a transformation count that measures `4,368`.** My
   earlier probe had scoped it to one predicate; it spans three. The ruling was *declared
   before* the measurement, so the disagreement surfaced instead of being reconciled.
2. **It declared `4,865` unreviewed assertions and measured `0`** — the property is
   `review_state`, not `review_status`. A ruling written after the measurement would have
   recorded a triumphant zero.
3. **The reproducibility harness classified my own registry audit `DEFECTIVE_REGENERATION`.**
   It was not: its two runs differed only by a timestamp. The harness treated a non-zero exit
   as a failed build, and that script's exit code is a *verdict*. Acceptable exit codes are now
   declared per builder.
4. **The boundary sample reported 20 grade values outside their vocabulary.** I had typed the
   vocabulary out by hand, inventing `DERIVED` and omitting `TEXTUAL_MENTION`, which
   `ontology.py` declares at length. Both vocabularies now read from their enums. Same shape as
   casting a property into the wrong enum and reporting 44,778 edges as `UNKNOWN`.

---

## F. Rebuild reproducibility (Phase 2)

Each builder run **twice** and the bytes compared, with volatile patterns declared *before*
the comparison. The dependency ledger was not consulted: its own digest is the thing under
test.

| classification | n | which |
|---|---:|---|
| `REPRODUCIBLE` | 4 | scorecard, ontology reference, AV anukramani builder, world bundle |
| `NONDETERMINISTIC_BUT_SEMANTICALLY_EQUIVALENT` | 5 | world export, predicate semantics, constellations, registry audit, dependency reporter — all timestamp-only |
| `BLOCKED_EXTERNAL_SOURCE` | 1 | Ask benchmark (provider quota) |
| `NOT_APPLICABLE` | 2 | graph migrations M7–M12; semantic-resemblance re-derivation |
| `DEFECTIVE_REGENERATION` | **0** | — |

The migrations are single-shot receipted mutations that refuse to run twice. Re-running one to
measure its determinism would be a canonical mutation performed for a measurement, which the
standing rules bar; their receipts carry the before/after census, the additive flag and the
residual count.

---

## G. Dependency finality and the perturbation test (Phase 8)

```text
CURRENT=6  STALE_INPUT=0  BLOCKED=2  NOT_APPLICABLE=1   unexplained stale: none
```

Both `BLOCKED` reasons are concrete (`ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA`; the
semantic-resemblance re-derivation bar). The `NOT_APPLICABLE` reason is concrete (no ritual
aggregate artifact exists).

**Perturbation, receipted.** One byte appended to `frontend/.world/world.raw.json` moved
exactly the two consumers that declare it — the Knowledge World for a declared output, the Lab
for a declared file input — each naming its own reason, and no others. Byte-exact restore
reproduced the baseline report.

---

## H. Sampling where nothing points (Phase 5)

195 boundary rows (both edges of every corpus, both edges of all 74 top-level divisions, 49
rows in known-hazardous spans) plus 239 mantras drawn with a fixed seed from a **sorted** key
list, so the seed alone determines the selection.

Seven contradiction checks, each stating its falsifier before running and each asserting a
relation *between* two things the graph says. All seven pass over 434 rows: no untiered edge,
no colon-bearing public metre, no `veda` disagreeing with its own key, no internal corpus
verse, no text-less mantra, no mis-ranged translation edge, no container-inherited deity edge
outside the Rigveda.

---

## I. Audio (Phase 10)

**1,021 rows queued. 0 listened to. 0 verdicts. Nothing was played by any tool in this wave
and nothing was simulated.**

Generator fix: 804 of 1,021 rows named no source, because the builder read
`payload.source_name` and the staged payloads do not have that field — the source is on the
row as `source_id`, and its name is in the domain's `sources.jsonl` under two different field
names in two different files. A reviewer was handed a media URL and left to infer whose
recording it is, on the one surface whose entire purpose is a human judgement. Now 0 unnamed,
and each row carries its licence and attribution.

The harness's refusals were tested against the **live server** on a loopback port, not read
from its docstring: unknown verdict, anonymous verdict, `AUDIBLY_VERIFIED` with nothing
played, and an unknown `review_id` all return 400. **The control matters as much** —
`AUDIBLE_REVIEW_UNCERTAIN` with nothing played returns 200 — because if every verdict were
refused the four refusals would prove nothing. Resumability confirmed by reading the
append-only log off disk. Run against a synthetic `review_id` in a sandbox; the real queue
still holds 0 verdicts and the real decision log still does not exist.

The promotion check had to be **scoped by stratum**. Unscoped it reported 61 hits and said
nothing: those 61 are the RV 1.65–1.70 span, already shipped and queued for audible *re*-review
because the edition merges verse pairs there. Exempted by name with the reason, not tolerated
as a count. **0 of the 960 rows awaiting a first hearing have reached a reader.**

Owner sample: **100 rows**, stratified proportionally with a floor of one so the 6-row
Samavedic container stratum survives, seeded and reproducible, at
`data/staging/wave4/audio_owner_sample_manifest.json`. Every row is `NEEDS_AUDIBLE_REVIEW` and
the manifest has no verdict field at all.

---

## J. Ask readiness (Phase 9)

Deterministic suites: `tests/api/ask` + `tests/product` **388 passed**, `tests/llm` **91
passed**.

The formal grade is reported in §L, because it is the last thing this wave runs and its
identity is keyed to the final commit. The earlier 31/60 run is **diagnostic only and is not
combined** with it, per the standing instruction.

---

## K. Verification chain

| check | result |
|---|---|
| `graph_quality_scorecard.py` | **11 of 11** |
| `pytest tests/unit` | **1,205 passed**, 41 skipped |
| `pytest tests/api` | **1,385 passed** |
| `pytest tests/domain` | **217 passed**, 31 skipped |
| `pytest tests/api/ask tests/product` | **388 passed** |
| `pytest tests/llm` | **91 passed** |
| `pnpm test` | **434 passed** |
| `pnpm typecheck` / `pnpm lint` | clean |
| `ruff` | clean on every file touched |
| `dependency_state.py --status` | `CURRENT=6 STALE_INPUT=0`, no unexplained stale |
| perturbation test | exactly the two declared consumers moved; byte-exact restore |
| registry closure audit | 85 entries, 0 `OPEN`, 40 not terminal |

**Census held throughout.** 116,838 nodes / 281,257 relationships at the Wave 4 baseline and at
its head. Every migration in this wave (M10, M11, M12) is additive — property and label writes
only, 0 node delta, 0 relationship delta — and each asserts the core corpus invariant: RV
10,552 · SV 1,844 · YV 1,975 · AV 5,839 = 20,210.

Public nodes: 39,692 → **39,664** (M10's 28). Public `:Chandas`: 575 → **547**.

---

## L. What has to happen before this is a release candidate

In the order that unblocks the most.

1. **Four owner decisions.** `OWNER_DECISION_A_RV_SPAN` and
   `OWNER_DECISION_C_FORCED_ADDRESSES` release 2,254 staged translations including the
   Samaveda's 1,242; `OWNER_DECISION_E_AUDIO_GATE` governs 954 staged audio rows and 1,471
   Samavedic notation rows. Gate B and Gate C have not been run for any of those four domains
   — `UNKNOWN` and `NOT_RUN` respectively — so the decision needs those first.
2. **The 40 implementation-fixable entries.** Enumerated with a measured basis each in
   `data/gap_registry.json`. The largest clusters: entity coverage (8), semantics (4),
   quality (5), ritual (5), morphology (3), product surface (5).
3. **A fresh 60/60 Ask grade at the final commit, with `misleading = 0`.** §L1 below.
4. **The audible review.** 1,021 rows, 0 heard. The harness is ready and tested; the work is a
   person's.
5. **`GAP-TRANSLATION-006`.** 25 of 31 shipped translations in RV 1.65–1.70 sit on the wrong
   verse. This is *wrong data on a public surface*, not missing data, and it is the one item on
   this list I would fix before any of the others.

### L1. Ask formal grade — `ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA` stands

Attempted at the final commit, on a clean tree:

```text
run_id      openrouter-nvidia_nemotron-3-ultra-550b-a55b:free-7d11e3b6f56b76ad
commit      b986193   questions 60
answered    0/60

STOPPING at Q01: LLMRateLimitError
  Rate limit reached for provider 'openrouter'.
  The daily allowance is exhausted; waiting will not clear it.
```

Only OpenRouter is credentialed; the Gemini and Anthropic adapters exist in code without keys,
and switching model would produce a different grade rather than a resumption. The earlier
19/60 and 31/60 runs are **diagnostic only and are not combined** with this one — and both are
keyed to earlier commits, so combining them would also be dishonest about which code was
graded.

**`misleading = 0` is not claimed.** None of the required figures — supported-correct,
partial-correct, correctly-refused, misleading, citation count, uncited factual answers,
invented citations — can be reported from 0 of 60 answers, and a deterministic suite is not a
formal grade. The blocker is recorded verbatim in the dependency ledger under `Ask retrieval`.

What *can* be said: the deterministic Ask suites pass (388 + 91), and the Wave 4 fixes that
touch Ask's evidence handling are real — the 214 deity notes it read as an absence qualifier,
and the caveat that denied the Atharvaveda's ascription layer. Whether those improve the grade
is exactly the question the grade would answer, so it is left open rather than assumed.
