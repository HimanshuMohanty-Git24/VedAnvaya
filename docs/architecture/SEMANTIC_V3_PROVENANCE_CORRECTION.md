# Semantic V3 provenance correction

Engineering correction, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing
output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was
performed, and no sealed artefact was altered, relabelled or deleted.

## What was wrong

The V3 semantic pilots were run through a module whose model constant read
`MODEL = "gpt-5.6-luna"`, and every object they emitted recorded that string in its
`extraction_model` field. The payloads themselves were produced by deterministic Python:
regular expressions over Griffith's English, with cue lists, an outcome inventory and a
substring span finder. No model was invoked at any point, and no model-authored response
was ever consumed.

The model field is provenance. It is a claim about who produced a record, and it was
false. This document states the correction; it does not fix it by editing history.

## What the historical artefacts are, and are not

These runs are classified `HISTORICAL_HEURISTIC_ARTIFACT` in
`docs/manifests/rigveda_semantic_historical_artifacts.json` and
`docs/reports/RIGVEDA_SEMANTIC_HISTORICAL_ARTIFACT_REGISTRY.md`:

- `vedagraph-rigveda-semantic-luna-v2-120`
- `vedagraph-rigveda-semantic-luna-v3-120`
- `vedagraph-rigveda-semantic-luna-v3-replication-120`
- `vedagraph-rigveda-semantic-luna-v3-508`
- `vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1`

They remain genuinely useful, and are still used by this repository's tests: they exercise
the typed semantic object schema, the normalization and comparison architecture, the
evidence validators, and the whole batching, custody, recovery and seal path. Being
byte-reproducible makes them a better fixture than a model could be.

They are not evidence about `gpt-5.6-luna`. In particular the 120-mantra replication run
reproduced the 120-mantra pilot exactly, and that result means:

> **HEURISTIC PIPELINE REPLAY** — the same regular expressions, run twice over the same
> packets, produced the same bytes.

It does not mean, and must never be reported as:

> ~~MODEL REPLICATION STABILITY~~

Any earlier report that reads a zero-disagreement figure as a statement about model
behaviour is wrong on that point. Those reports are left as written; this correction is the
record of how to read them.

## What changed prospectively

- The deterministic producer moved to `src/vedagraph/semantic/heuristic_baseline.py` and
  stamps `DETERMINISTIC_HEURISTIC_BASELINE` into every model field it writes. It has no
  default run identifier, so a payload it produces always knows which run authored it.
- `src/vedagraph/semantic/v3.py` keeps only the payload contract and the validator that the
  sealed pilots were validated against. It cannot produce a payload.
- `src/vedagraph/semantic/codex_direct.py` is the real execution path: Python prepares a
  frozen task, a model authors a response file with an execution receipt, and Python
  validates and imports it. There is no branch in which Python writes the semantic content.
- `BatchStore.commit_receipts` accepts only a `ValidatedResponse`, a type constructible
  only by the importer. The heuristic baseline cannot produce one, and its payloads fail
  the model-provenance check in `validate_recorded_payload` besides.
- Execution version `rigveda-semantic-execution-v3.1` supersedes the V3 identities. The
  V3 pilot, replication and 508 run identifiers are retired and may not be reused.

## What the new path can and cannot guarantee

Guaranteed, because it is hashed and checked at import:

- the requested model and reasoning setting,
- the runtime (`CODEX_DIRECT`),
- the prompt, schema, ontology and evidence-packet bytes the task was pinned to,
- the exact bytes of the authored response, kept immutably per attempt.

Not guaranteed, because the runtime does not expose it:

- an immutable provider build identifier. The receipt records
  `provider_build_metadata: UNAVAILABLE` rather than inventing one.

Consequently, two matching future outputs may be reported only as **observed replication
agreement under a pinned task, prompt, schema and model configuration**. They are never
evidence of model determinism, and no claim of cryptographic or model-level determinism may
be made about a model-authored payload.
