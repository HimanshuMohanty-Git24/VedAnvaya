# Semantic execution v3.1 readiness

Corrective engineering, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing
output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was
performed: no Luna call, no 120 benchmark, no 508 pilot, no full Rigveda run.

## Final state

`CODEX_DIRECT_LUNA_EXECUTION_PATH_READY_FOR_BOUNDED_REGRESSION`

The full Rigveda run remains blocked. This state authorizes one bounded regression of 60
mantras under a new execution identity, nothing more.

## Starting health

`ruff format --check` (276 files), `ruff check` and `mypy --strict` (88 source files) all
passed; 426 unit tests passed with one optional OpenAI SDK test skipped. That baseline
included the B01, B02 and B03 defects: a green suite was never evidence that the extraction
path was sound, which is the substance of the B03 finding.

## B03 — provenance

`MODEL = "gpt-5.6-luna"` was a constant in a module whose payloads were produced by regular
expressions. Every V2/V3 object recorded it. The correction is stated in
`docs/architecture/SEMANTIC_V3_PROVENANCE_CORRECTION.md` and applied prospectively:

- the producer moved to `src/vedagraph/semantic/heuristic_baseline.py` and stamps
  `DETERMINISTIC_HEURISTIC_BASELINE` into every model field it writes;
- `src/vedagraph/semantic/v3.py` keeps the payload contract and the validator the sealed
  pilots were validated against, and can no longer produce a payload;
- `extract_packet` has no default run id, so a baseline payload always names its run;
- five historical runs are classified `HISTORICAL_HEURISTIC_ARTIFACT` in
  `docs/manifests/rigveda_semantic_historical_artifacts.json`. Not one byte of any sealed
  artefact was changed, and no old manifest or report was edited.

The 120-mantra replication result is reclassified as **heuristic pipeline replay**, not
model replication stability.

## The CODEX_DIRECT execution contract

`src/vedagraph/semantic/codex_direct.py`, contract version `codex-direct-semantic-v1`.

    packet -> PreparedTask -> (agent authors a response file) -> ModelExecutionReceipt
           -> ReceiptValidator -> SemanticPayloadValidator -> ValidatedResponse -> BatchStore

One mantra per task. Batching stays a persistence concern only; no semantic context ever
holds 24 packets.

**Prepare authors nothing.** A `PreparedTask` has thirteen fields and none of them can hold
a predicate, object, confidence or explicitness. The test asserts the field set and greps
the serialised task for semantic vocabulary.

**Import fabricates nothing.** `ExecutionStore.import_response` reads a file that already
exists; there is no branch that synthesises one. Missing file, or a task that was never
prepared, is a refusal.

Refusals, each covered by a test: tampered task hash, prompt hash, schema hash, packet hash
or response hash; wrong passage; wrong run; a run contract that disagrees with the task;
a payload for a different mantra; evidence not in the packet; a payload claiming a model the
run did not request (which is how baseline output is refused); an assertion with no binding
evidence.

## Model metadata: available and unavailable

Available and hashed: requested model, reported model, runtime `CODEX_DIRECT`, reasoning
setting, task hash, prompt hash, schema hash, evidence-packet hash, response hash, and the
exact authored response bytes.

Unavailable: an immutable provider build identifier. The receipt records
`provider_build_metadata: UNAVAILABLE`. Nothing is invented to fill it.

Consequently two matching future outputs may be reported only as **observed replication
agreement under a pinned task, prompt, schema and model configuration**. No claim of
cryptographic or model determinism may be made.

## Receipt immutability

`<store>/tasks/<task>/attempts/<attempt_id>/raw_response.json` holds the authored bytes and
is never rewritten. A different response under the same attempt id is refused; a retry uses
a new attempt id and the earlier attempt stays byte-identical. The validated, normalized
payload is written separately in the same attempt directory.

## B02 — evidence span anchoring

`src/vedagraph/semantic/spans.py` replaces substring matching. A span whose first character
is a word character may not begin inside a word, and likewise at its end; word-ness is
Unicode-aware and counts combining marks. An anchor occurring more than once is ambiguous
and must be resolved by explicit occurrence or refused — the baseline refuses, emitting no
span rather than the first match.

Regression results:

- all **14** audited substring anchors are refused by the span validator, checked one by
  one against the real Griffith strings;
- `man` no longer matches inside `manifested`, `many`, `Pavamana`, `woman` or `Aryaman`,
  each an explicit parametrized case;
- the repaired baseline produces **zero** defective anchors across all 508 pilot packets;
- 16 of the 508 sealed payloads now fail validation on their historical anchors, including
  RV 1.35.5 in batch_001. They are left as sealed and are no longer used as custody
  fixtures.

`src/vedagraph/semantic/evidence.py` walks every anchor recursively — assertion evidence,
object evidence, ontology-gap evidence — and every nested identifier: canonical,
beneficiary and target entity ids, event actor, patient and participant ids, and
`other_evidence_ids`. Identifier membership alone is no longer treated as sufficient.

## B01 — relation binding

No regex fix was attempted, because there is not one. The contract requires the model to
author assertion-specific evidence, and the validator then checks that the evidence is real
and local without pretending to read Sanskrit.

For every assertion: at least one binding anchor, quoted exactly and boundary-safe against
the packet translation, and never the whole verse. A `RELATION` anchor is mandatory.

For `INVOKES`, `PRAISES` and `DESCRIBES` with a canonical-entity object: a `TARGET` anchor
naming that exact entity id, which must be a supplied lexical mention, and whose span
differs from the relation anchor. A canonical entity that merely occurs somewhere else in
the verse no longer qualifies.

For `REQUESTS`: an `OUTCOME` anchor on the requested outcome itself. A request cue and the
word "Son" elsewhere in the verse can no longer combine.

Regression fixtures cover RV 10.58.1, 10.170.1, 8.35.7, 8.35.8, 8.35.9, 8.36.4, 8.36.5,
8.36.6, 1.137.3, 9.87.4, 9.87.9, 10.41.1 and 1.51.9. They assert that the mechanism which
produced the audited failures has no route through the importer. They do not encode a
scholar's reading of any verse; none has been obtained.

No semantic schema v4 was introduced. Binding evidence lives in the execution receipt
wrapper, so `schemas/semantic_extraction_v3.schema.json` is byte-identical.

## The heuristic baseline, kept and isolated

`vedagraph semantic heuristic-baseline` runs it explicitly. There is no
`vedagraph semantic luna`, and the baseline has no CODEX_DIRECT path. Its output is refused
by `validate_recorded_payload` on the model-provenance check, and it cannot construct a
`ValidatedResponse`, so `BatchStore.commit_receipts` is closed to it by type. A test commits
24 real baseline payloads to a `BatchStore` and asserts the batch fails.

## Bounded regression set

`data/builds/rigveda_semantic_codex_luna_regression_v1.yaml`, built by
`scripts/build_semantic_regression_v1.py` from the readiness audit records.

- **60** unique mantras.
- Selection hash `26d2f85aec91e621d43444931d40fc81e08a7c9d533bdce820c86945c398783c`.
- B01_RELATION_BINDING 24, B02_EVIDENCE_SPAN 13, PARALLEL_CONTROL 3, CLEAN_CONTROL 20.
- Covers every blocker-bearing audit record, both sides of all 13 audited parallel pairs
  (the six 10.58.1 inconsistency pairs, the five text-variant pairs, the two exact
  translation-variant pairs), and 20 hash-drawn clean controls spread over all ten
  Maṇḍalas.
- Identifiers, strata and reasons only. No semantic answer of any kind, asserted by test.

## Execution and full-run identity

Execution version `rigveda-semantic-execution-v3.1`; regression run
`vedagraph-rigveda-semantic-luna-v3.1-regression`. The V3 pilot, replication and 508
identities are retired and may not be reused.

The v3 full-run freeze draft is preserved and is now correctly stale: the extraction
contract changed, which is what `require new extraction version` means. A new draft was
issued rather than edited:

- `docs/manifests/rigveda_semantic_execution_v3_1_freeze.draft.json`, freeze hash
  `ebd736b7719e6a2ef0a327ce52ec23c2f0959b8e1c41b4bcfafa7e0121889e11`;
- `docs/manifests/rigveda_semantic_execution_v3_1_batch_plan.draft.json`, plan hash
  `bbd29b7b395eb1a62f306252c7c61d3b1280d9bf96767a88505a57ac57fc81e7`;
- 10,552 identifiers, 440 batches of 24, `unlocked_predicates: []`, runtime version marked
  `BLOCKED draft`.

Three freeze roles were added — `execution_contract`, `evidence_validator`, `span_validator`
— because those files are inputs to a run exactly as the prompt and schema are.

The 24-mantra persistence batches, 440-batch plan, atomic writes, resume state, single-writer
lock, hash verification, failure recovery, aggregate regeneration and seal prerequisites are
unchanged. Full-run dispatch is not connected.

## Quality

`ruff format --check` (287 files), `ruff check` and `mypy --strict` (92 source files) pass.
491 unit tests pass with one optional OpenAI SDK test skipped, up from 426; 65 of the new
tests are the span and execution-contract suites. Coverage on the new modules: `spans.py`
92%, `evidence.py` 82%, `codex_direct.py` 91%, `heuristic_baseline.py` 97%.

Two existing full-run tests were repointed rather than weakened: the custody fixtures moved
from batch_001 to batch_005 because batch_001 carries the RV 1.35.5 anchor defect that is
now correctly refused, and the freeze tests read the v3.1 draft.

## Git safety

No commit, reset, stash or clean was performed. The extensively dirty starting workspace is
intact; the CLI diff is 306 insertions and 0 deletions, and no pre-existing modified file
was touched. CRLF and LF line endings were preserved per file.

## The next session

Bounded Luna regression only. Do not run the 120 benchmark, the 508 pilot, or the full
corpus.

1. Build the 60 evidence packets for the identifiers in
   `data/builds/rigveda_semantic_codex_luna_regression_v1.yaml` and write them as one
   JSONL of `EvidencePacket` rows.
2. `vedagraph semantic execute prepare --packets <packets.jsonl>
   --run-id vedagraph-rigveda-semantic-luna-v3.1-regression --out-dir <store>`
   — this writes one frozen task per mantra plus `run_contract.json`, and authors nothing.
3. For each task in `<store>/tasks/<task_id>/task.json`: read that one task, in its own
   reasoning context, and author a response file containing a `receipt` and a
   `semantic_output`, plus an `assertion_bindings` entry for every assertion with its
   `RELATION` anchor, its `TARGET` anchor and entity id for a canonical-entity relation,
   and its `OUTCOME` anchor for a request. Record `reported_model` as reported and leave
   `provider_build_metadata` as `UNAVAILABLE`. Use `attempt_001`; a retry gets
   `attempt_002`.
4. `vedagraph semantic execute import-response <response.json> --store-dir <store>` per
   response. Refusals are results, not obstacles: record them.
5. Compare against the audited B01 and B02 cases and report agreement, disagreement and
   refusals. Report any output match as observed replication agreement under the pinned
   configuration, never as determinism.
6. Re-run the readiness gate. Only then consider the full run.

All outputs remain LLM_EXTRACTED / MODEL_CANDIDATE, CANDIDATE / NEEDS_REVIEW,
`unlocked_predicates: []`, `human_gold_status: UNANNOTATED`.
