# Rigveda Genuine Luna V3.2 Calibration (16) — Preflight Stop

**Status: NOT EXECUTED — model identity unverified.**

`NO HUMAN GOLD EXISTS.`  
`MODEL SELF-AGREEMENT IS NOT ACCURACY.`  
`THIS IS A 16-PASSAGE CALIBRATION, NOT AN ACCURACY BENCHMARK.`  
`MODEL IDENTITY MUST NOT BE INFERRED FROM REQUESTED-MODEL METADATA ALONE.`

## 1. Starting health

The worktree was already substantially dirty. No reset, clean, checkout, or destructive
operation was performed. The repository preflight completed without semantic execution.

## 2. Actual current model identity and verification

Not established. The current Codex tool/runtime surface did not expose an externally or
runtime-attested active model ID. The Codex app thread metadata exposed task identity and
host (`local`), but no model selection. Computer-use guidance also prohibits automating the
Codex app UI itself.

## 3. Requested versus actual/reported model

- Requested model: `gpt-5.6-luna`
- Actual current Codex/model selection: **not exposed / unverified**
- Reported model from the active semantic runtime: **none exposed**
- Configured repository model constant: `gpt-5.6-luna` (configuration only; not proof)
- Runtime requested by the task: `CODEX_DIRECT`
- Reasoning requested by the task: `high`

## 4. Provenance limitation

The repository CODEX_DIRECT contract states that Codex does not expose an immutable server
build identifier and records `provider_build_metadata: UNAVAILABLE`. Its receipt fields are
requested/reported provenance fields, not an independent attestation of the backend that
authored the response. No current-session mechanism was available to distinguish Luna from
another configured model. Therefore no semantic task was prepared or authored.

## 5. V3.2 hash verification

Passed, without regeneration or modification:

| Input | SHA-256 | Result |
|---|---|---|
| `prompts/semantic_extraction_v3.2.md` | `e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1` | match |
| `schemas/semantic_extraction_v3.schema.json` | `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2` | match |
| `src/vedagraph/semantic/ontology.py` | `cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce` | match |

Prompt policy verified as `rigveda-semantic-extraction-v3.2` by the repository checks.

## 6. 16-ID selection and hash

Not performed. The required model-authorship gate failed before subset preparation. The
existing parent selection was read-only verified as 60 unique IDs with selection hash
`26d2f85aec91e621d43444931d40fc81e08a7c9d533bdce820c86945c398783c`.

## 7. EvidencePacket verification

Not performed for this calibration. No calibration EvidencePackets were built or reused.

## 8. Run A identity

Not created/executed. The requested identity would have been
`vedagraph-rigveda-semantic-luna-v3.2-calibration-16-a`.

## 9. Run B identity

Not created/executed. The requested identity would have been
`vedagraph-rigveda-semantic-luna-v3.2-calibration-16-b`.

## 10. Run A final task count

`0/16` — not executed.

## 11. Run B final task count

`0/16` — not executed.

## 12. Attempts/retries

Semantic attempts: `0`. Validation retries: `0`.

## 13. Integrity failures

The semantic integrity gate was not entered. Blocking failure: model identity unverified.
No receipt, packet, evidence, span, binding, ontology/type, duplicate-final-attempt, or
missing-task counts were generated.

## 14–25. Semantic distributions and passage comparison

Not applicable. No semantic responses, assertions, bindings, receipts, seals, or comparison
targets were created. Accordingly there are no assertion counts, densities, no-claim rates,
predicate/object distributions, canonical-target results, passage-level agreements, or
lightweight support-audit flags to report.

## 26. Comparison with genuine V3.1 Luna

Not performed. Existing historical artifacts were not modified or relabelled. Their
repository documentation already records provenance limitations and was treated as
historical context only.

## 27. Comparison with previous Sol V3.2

Not performed. No Sol output was used as Luna output, and no statistics were merged.

## 28. Model identity separation

`MODEL_IDENTITY_SEPARATED = true`

## 29. Cost-aware recommendation

Do not execute the calibration, 508, or 10,552-task runs until the Codex execution surface
provides a truthful Luna authorship mechanism or an independently verifiable runtime
attestation. Once that gate exists, resume with the requested 16-passage calibration before
considering any larger candidate pilot. Agreement alone must not authorize promotion.

## 30. Tests / Ruff / mypy

- Repo-pinned Ruff: **passed** — `uv run ruff check .`
- Strict mypy: **passed** — `uv run mypy`; 94 source files
- Targeted tests: **passed** — 79 tests in `tests/unit/test_semantic_v3_2.py` and
  `tests/unit/test_semantic_codex_direct.py`
- API calls: none initiated

## 31. Git and sealed-artifact safety

The starting branch was `semantic-pilot-v1` with pre-existing dirty tracked and untracked
changes. No existing sealed V3.1 run, historical heuristic artifact, V3.2 implementation,
receipt, raw response, manifest, or seal was modified. This report and its machine-readable
status manifest are the only new calibration-status artifacts created by this turn.

## 32. Exact final decision

`GENUINE_LUNA_V3_2_CALIBRATION_NOT_EXECUTED_MODEL_IDENTITY_UNVERIFIED`
