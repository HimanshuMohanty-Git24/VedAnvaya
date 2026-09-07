# V3.2 prompt-policy implementation

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

Readiness state: `V3_2_TWO_RUN_60_STABILITY_TEST_COMPLETE`.

The later execution phase completed and sealed both 60-mantra Luna runs. The stability
result is a policy-consistency diagnostic, not accuracy; the 508 rerun and the full
10,552-mantra run remain separate, unauthorised decisions.

## Why V3.2 exists

Two genuine GPT-5.6 Luna v3.1 runs processed the same 60 EvidencePackets under a
byte-identical execution contract — same prompt, schema, ontology, model, reasoning, and
packet hashes.

**Execution integrity was not the problem.** The replication audit recorded 0 contradictory
canonical targets, 0 receipt failures, 0 packet or hash failures, 0 binding failures, and 0
imported invalid spans. Engineering adjudication revised the old comparator's 42 HIGH
differences down to 0 CRITICAL, 2 HIGH, 46 MEDIUM, 3 LOW, 9 NO_DIFFERENCE; the dominant
component was supported emit-vs-omit variance, not semantic contradiction.

**The finding was run-level.** Over the identical 60 packets:

| Metric | Run A | Run B |
| --- | --- | --- |
| Assertions | 57 | 33 |
| No-claim passages | 10 | 38 |
| No-claim rate | 0.167 | 0.633 |
| Assertions per passage | 0.95 | 0.55 |
| `DESCRIBES_ACTION` | 21 | 0 |
| `REQUESTS` | 21 | 15 |

Run B was internally consistent with its other 448 passages (no-claim rate 0.614, density
0.516 there), so this is not adequately explained as independent per-assertion noise. The
diagnosis is that the v3.1 prompt admits at least two internally coherent readings of when a
directly evidenced relation must be emitted. That is a prompt-policy underspecification, and
V3.2 is the minimal revision that closes it.

This is **observed run-level emission-regime divergence**. Two runs cannot establish how many
latent regimes exist, and neither regime is correct: neither Luna run is truth, historical
heuristic output is not truth, Sol silver is not truth, and traditional Devatā metadata is not
semantic truth.

## What V3.2 changes, and what it does not

New prompt policy: `rigveda-semantic-extraction-v3.2`, at
[prompts/semantic_extraction_v3.2.md](../../prompts/semantic_extraction_v3.2.md).
V3.1 is not mutated. `prompts/semantic_extraction_v3.md` is byte-identical to the file the
sealed runs were pinned to.

| Input | SHA-256 | Status |
| --- | --- | --- |
| `prompts/semantic_extraction_v3.md` | `b8cc7d3df061ec928947b1723b3df3a7d4cf3e3d9c53af53ab55ccc5852cfafb` | unchanged |
| `prompts/semantic_extraction_v3.2.md` | `e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1` | new |
| `schemas/semantic_extraction_v3.schema.json` | `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2` | unchanged |
| `src/vedagraph/semantic/ontology.py` | `cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce` | unchanged |
| `src/vedagraph/semantic/object_ontology.py` | `ca2129760d01b7b6f672f794d58e2517065e9326d04f835799c88b3c2d1577cd` | unchanged |
| `src/vedagraph/semantic/evidence.py` | `0932564ad228c9dfa87caa945ac7aeece7aca1338a2deb165378f88ee3c1eaee` | unchanged |
| `src/vedagraph/semantic/spans.py` | `e16817714b2e8e1c23785176586a9e6bfb2e3de4be726758b81ba8d6a2ef8626` | unchanged |
| `src/vedagraph/semantic/v3.py` | unchanged | unchanged |
| `src/vedagraph/semantic/codex_direct.py` | `531595357b893c1291d11c6d02d122a723d24b2c1c6bb62e412b7ac7d9ab66a6` | **changed** (was `398b22f2…`) |
| `src/vedagraph/semantic/full_run.py` | `dfb3f56d8b15e05a4e7e694d811ac346699f4b5ca458e1a252e5ecc058563fd1` | **changed** (batch-side policy version) |

`src/vedagraph/semantic/replication_diagnosis.py` gained the run-level comparators and
`src/vedagraph/semantic/v3_2.py` is new. Neither is a frozen run input, so neither is listed
by hash here; both are diagnostic code that no extraction depends on.

Preserved without modification: the semantic payload schema, the fourteen-predicate ontology,
the typed-object schema, the EvidencePacket structure, the CODEX_DIRECT contract shape, span
validation, evidence validation, assertion-binding validation, candidate-only status,
`unlocked_predicates = []`, no canonical promotion, and the absence of any human-gold
assumption.

### The one execution-contract change

`src/vedagraph/semantic/codex_direct.py` gained exactly two things:

1. `read_prompt_version(path)` — reads `prompt_version` from a prompt file's front matter and
   fails closed if absent, so a run's declared policy comes from the same bytes it hashes.
2. `RunContract.prompt_version`, defaulted to `rigveda-semantic-extraction-v3`. The
   object-level prompt-version check in `validate_candidate_invariants` now compares against
   the run's policy instead of a module constant.

`PreparedTask` is deliberately untouched. Adding a field there would change every
`task_sha256` and invalidate every sealed receipt. Because `RunContract` is not part of the
task hash and the new field is defaulted, a `run_contract.json` stored before the field
existed still loads as exactly what it was.

`src/vedagraph/semantic/full_run.py` took the same treatment on the batch side:
`validate_recorded_payload` and `BatchStore` accept a `prompt_version`, defaulted to the v3
policy, so recorded pilot payloads keep meaning what they meant.

The `execution_contract_sha256` recorded in the sealed v3.1 manifests therefore no longer
matches the current file. That is expected and is recorded here rather than hidden: the
sealed manifests are historical records of which bytes produced which output. Reproducibility
was verified the way that matters — **all 568 sealed v3.1 responses (60 regression + 508
pilot) re-validate with 0 failures under the current code, and every sealed `task_sha256`
still matches its manifest entry.** A future re-run of a v3.1 seal script would correctly
report the drift and stop; those runs are complete and are not to be re-sealed.

### The v3.1 full-run freeze draft is now correctly stale

`docs/manifests/rigveda_semantic_execution_v3_1_freeze.draft.json` pins 71 files, two of
which this revision moved: `codex_direct.py` and `full_run.py`. The draft is left untouched
and `Freeze.verify` now refuses it with *"frozen input changed … require new extraction
version"*. That is the freeze mechanism working, and a test asserts exactly this outcome
rather than hiding it — the same treatment the older v3 draft already carries. No v3.2
full-corpus freeze was issued, because no full run is authorised.

## The seven policy rules

Each appears in the prompt under its own `### Rule N — Title` heading and is asserted by test.

1. **Emit-vs-omit floor.** After the fourteen-family inspection, emit every relation whose
   relation force *and* target/object are both directly supported and bindable. Do not omit an
   independently supported relation because another was already emitted. "Optional" means the
   evidence leaves a policy boundary unresolved; it never licenses skipping a directly
   evidenced relation. Conservatism is preserved in the other direction: do not infer
   unsupported semantics to raise density.
2. **REQUESTS force.** Imperative, optative, prohibitive wish, explicit
   grant/give/bring/send/bestow constructions, and expressed desired results of the *may X
   occur* / *may we receive* / *may you cause* form all carry request force when the speaker
   seeks an outcome from an addressee. The requested outcome is the desired resulting state or
   action, not automatically the grammatical object of the request verb. No invented addressee
   or beneficiary.
3. **REQUESTS outcome splitting.** One assertion per independently coordinated desired
   outcome. Split only where each conjunct stands alone as a separately desired result; a
   modifier or beneficiary qualifying one result stays inside it; an unresolved relative
   phrase is not an extra outcome unless independently anchored. Both over-collapsing and
   over-splitting are named as failures.
4. **DESCRIBES precedence.** `DESCRIBES` covers an entity-level state, quality, property,
   role, or depiction. A clause whose only content is an action emits `DESCRIBES_ACTION`
   without a redundant `DESCRIBES`. Where a passage independently states both, both may be
   emitted with their own evidence and binding anchors.
5. **DESCRIBES_ACTION scope.** Only for an action asserted or narrated as occurring. A
   commanded or wished-for action is a desired future action and belongs to `REQUESTS`; an
   imperative directed at an addressee is not by itself a narrated action. If the passage
   separately states the action occurs, `DESCRIBES_ACTION` may also be supported. Relation
   force stays distinct from grammatical surface form.
6. **Material and ritual co-emission.** A material, substance, offering, or ritual relation may
   coexist with `REQUESTS`, `DESCRIBES`, `DESCRIBES_ACTION`, `INVOKES`, `PRAISES` or another
   allowed family only where each independently carries direct local evidence. Repeated
   mentions do not duplicate a passage-level predicate/object; separate assertions need
   distinct typed roles or independently supported qualifiers.
7. **No-claim criterion.** `no_claim` only after all fourteen families were inspected and none
   passed the direct relation-force-plus-supported-object test. Not permitted out of
   difficulty or caution when a supported relation is available. The reason names the failed
   family or boundary where useful, invents no semantics, and remains model-authored
   diagnostic metadata rather than canonical knowledge.

## Fourteen-family inspection

The prompt numbers all fourteen families in repo-authoritative order — the order of
`PREDICATE_CHECKS` in `src/vedagraph/semantic/v3.py` — and requires the inspection before
finalising *any* result, not only before a no-claim:

`INVOKES`, `PRAISES`, `REQUESTS`, `DESCRIBES`, `DESCRIBES_ACTION`, `INVOLVES_RITUAL`,
`INVOLVES_OFFERING`, `INVOLVES_SUBSTANCE`, `REFERS_TO_NATURAL_PHENOMENON`, `REFERS_TO_PLACE`,
`EXPRESSES`, `HAS_THEME`, `ASSOCIATED_WITH`, `CONTRASTS_WITH`.

It is stated as a checklist and explicitly not a quota: a family that fails the test
contributes nothing, and no family is owed an assertion. Each family carries its own evidence
policy in the Object selection section, unchanged from v3.

## Explicitness

Unchanged and not relaxed. `EXPLICIT` requires the relation and target to be directly
supportable from supplied Sanskrit or supplied translation evidence. `STRONG_INFERENCE`
remains restricted to exactly one named limited inferential step and is refused for broad
narrative, symbolic, theological, thematic or culturally remembered readings. `INTERPRETIVE`
is prohibited. The prompt says so directly: the Rule 1 emission floor applies only to
relations that already meet this bar and never lowers it.

## Anti-overfitting

The prompt contains no benchmark passage ID, no citation, no `RV `/`VG:RV:` string, no
`10.58` rule, and no handcrafted output target. Two tests enforce it:

- every one of the 60 selection passage IDs and citations is absent from the prompt text;
- every distinctive multi-word answer either sealed run produced — object `normalized_head`,
  `display_label`, event `action_head`, and every binding-anchor text — is absent from the
  prompt text.

Rule 2's vocabulary (grant, give, bring, send, bestow, *may*) is general grammatical policy
language, not benchmark wording.

## Validator authorship boundary

Unchanged and re-tested under the V3.2 path. No deterministic regex semantics were added.
Python still cannot add an assertion, rewrite a predicate, split a `REQUESTS` outcome, create
a semantic object, convert a no-claim into assertions, convert `DESCRIBES` into
`DESCRIBES_ACTION`, or synthesise a missing relation. Validators only validate structure,
provenance, spans, evidence references, target bindings and typed-object compatibility, and
reject what fails.

Tested directly: a V3.2 `PreparedTask` serialises with no field capable of holding a semantic
claim; `import_response` on a missing file raises rather than producing output; running all
four validators over a payload leaves its serialisation byte-identical; and the deterministic
heuristic baseline is refused from V3.2 custody on both its model provenance and its prompt
version.

## Run and batch provenance

Every validated result already carried the fields needed to trace it. `ExtractionProvenance`
in `src/vedagraph/semantic/v3_2.py` reads them together and checks completeness rather than
duplicating them: run ID, task ID, attempt ID, passage ID, packet hash, prompt hash, prompt
policy version, schema hash, ontology hash, requested and reported model, runtime, reasoning,
response hash, raw response hash, and the batch ID where a batch store was involved.

The purpose is stated in the code: a future corpus analysis that averages assertions across
runs occupying different emission regimes would report a distribution no run produced, and it
would look well-formed. No regime label is assigned prospectively — a run's regime is only
observable after the run.

`BatchStore` and `validate_recorded_payload` in `full_run.py` take the same
`prompt_version`, defaulted to the v3 policy, so recorded pilot payloads keep meaning what
they meant.

## Completed two-run 60 experiment

Completed and sealed. See the
[experiment definition](RIGVEDA_SEMANTIC_V3_2_STABILITY_EXPERIMENT.md) and the
[final stability result](RIGVEDA_SEMANTIC_V3_2_STABILITY_RESULT.md).

## Why one V3.2 run is insufficient

The defect V3.2 targets is invisible within a single run. Run B was internally consistent
across all 508 of its passages; nothing inside it looked wrong. A regime is only detectable by
comparing independent runs over identical inputs, so a single V3.2 pass would demonstrate
nothing about whether the ambiguity is closed — it would simply occupy whichever regime it
occupied and look coherent doing so.

## Why the full 10,552 remains a separate decision

The narrow run-level stability question is now resolved: V3.2 passed its predeclared gate.
Three limits still prevent treating that pass as blanket corpus authorization:

1. Both V3.2 runs are dramatically denser than the V3.1 observations (392/388 assertions
   versus 57/33). Historical output is not truth, so this is a calibration warning rather
   than proof of over-extraction, but it needs candidate review before scaling.
2. There is no human gold set, so no output of any size can be scored for accuracy.
3. A corpus-scale run still needs replicated calibration samples and run-level monitoring;
   a stable 60-passage pair does not guarantee that a longer run cannot drift.

The 508 rerun and full-corpus run are therefore not automatically authorised by this result.
