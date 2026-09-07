# ADR-016: The execution runtime is recorded, never assumed

Status: Accepted
Date: 2026-09-07
Extends [ADR-014](ADR-014-llm-output-is-candidate-only.md).

## Context

`codex_direct.py` defines the contract under which an agent runtime authors a semantic
payload and Python validates it. Until now the contract also *was* its runtime:
`ModelExecutionReceipt.runtime` was `Literal["CODEX_DIRECT"]`, so every receipt written
under the contract asserted that a Codex agent produced it.

That was true while Codex was the only runtime. It stopped being true the moment a
Claude Opus 5 agent fleet was asked to author the 448-passage V3.2 candidate pilot. The
options were to record `CODEX_DIRECT` for work Codex did not do, or to generalize.

Recording `CODEX_DIRECT` for a Claude run would be the same defect as B03 — the one that
made the earlier V3 pilots look like Luna runs when they were regular expressions.
B03 was not a bug in a regular expression; it was provenance that looked like evidence
and was not. A wrong runtime string is that failure in one field.

## Decision

`ExecutionRuntime` is a two-member vocabulary: `CODEX_DIRECT` and `CLAUDE_CODE_DIRECT`.
Both mean "an agent runtime authored this payload and Python validated it"; neither is
provider-attested, and `provider_build_metadata` stays `UNAVAILABLE` for both.

`RunContract.runtime` and `ModelExecutionReceipt.runtime` both carry it, both default to
`CODEX_DIRECT`, and `validate_receipt` now checks the receipt's runtime against the run
contract exactly as it already checked model and reasoning. That check is a
strengthening, not a relaxation: a receipt can no longer be silently imported into a run
executed on a different runtime.

Defaulting is what keeps history intact. A `run_contract.json` written before the field
existed still loads as the Codex run it was, and every stored Luna receipt still
validates byte-identically. This is asserted by test, not by comment.

`model_requested` was already a free-form string and needed no change; the Luna pin that
remains in `full_run.py` (`MODEL_PROVENANCE`, `Freeze.model`) is untouched because the
448 pilot does not use `BatchStore`. That pin **will** block a non-Luna full-corpus run
and is recorded here as known future work rather than changed speculatively.

## Consequences

The bytes of `codex_direct.py` changed, so its hash changed:

| | sha256 |
|---|---|
| before | `398b22f27919113c1db671c45b930098f1a4f5c38f9b69b7c6e2aab340a2182a` |
| after | `f972cf43621a7daf87ad2e3129ef9956f11fe2989dd6d4a4daae56c2fd1af253` |

The sealed `vedagraph-rigveda-semantic-luna-v3.1-508` freeze pins the old value, so
re-running its seal script now reports frozen-input drift. That is the freeze working:
it is a detector, and it detected a real change to a real input. The sealed artefact
itself is untouched and its stored responses still validate under the new code. This is
the same class of event already recorded for the v3.2 policy revision in
`V3_2_MOVED_INPUTS`.

No predicate is unlocked, no candidate is promoted, no human gold is created, and no
historical validation is weakened.
