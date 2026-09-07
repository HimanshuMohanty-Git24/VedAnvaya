# Rigveda semantic V3.2 — Claude Opus 5 448 candidate run: engineering audit

> **NO HUMAN GOLD EXISTS.**
> **MODEL SELF-AGREEMENT IS NOT ACCURACY.**
> **CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
> **ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**
> **50/448 PASSAGES LACK TRANSLATION ANCHOR COVERAGE UNDER THE CURRENT SEMANTIC CONTRACT.**

Run: `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`
Provenance bucket: `CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION`
Output seal: `cd45b1752cae62dd7d364d571235aa0db3c58ace8be829369dc9c013274465ec`

This document audits the **execution**, not the semantics. It asks whether the pipeline
recorded what it claims to have recorded. What the assertions mean, and whether they are
right, is not decidable here and no number in this file should be read as accuracy.

---

## 1. Provenance separation

The previous attempt at this selection ran under a Luna run identity. Claude-authored
candidates may not be stored under it, so a new run identity was created and the
provenance layer was generalized to make the distinction expressible rather than implied.

| | Abandoned attempt | This run |
|---|---|---|
| run id | `…user-selected-luna-v3.2-448-new-v1` | `…claude-opus5-v3.2-448-new-v1` |
| `model_requested` | `gpt-5.6-luna` | `claude-opus-5` |
| `runtime` | `CODEX_DIRECT` | `CLAUDE_CODE_DIRECT` |
| provenance bucket | Luna/Sol historical | `CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION` |
| imported responses | 0 | 448 |
| seal | none | `cd45b175…` |

Because `task_id = sha256(run_id | passage_key)`, the two runs cannot collide in the
store even for the same passage. This is verified by test, not asserted.

### 1.1 The runtime generalization (ADR-016)

`ModelExecutionReceipt.runtime` was `Literal["CODEX_DIRECT"]`. Recording `CODEX_DIRECT`
for a Claude run would be the B03 defect in one field: provenance that looks like evidence
and is not. It is now a two-member `ExecutionRuntime` vocabulary, defaulted to
`CODEX_DIRECT`, and `validate_receipt` checks it against the run contract — a
strengthening, not a relaxation.

**No historical validation was weakened, and this was proven rather than promised.**
Every stored response in every existing run store was re-validated from scratch under the
changed code, through `validate_receipt`, `validate_candidate_invariants`,
`validate_v3_payload`, `validate_evidence_anchors` and `validate_bindings`:

| Run | Stored responses | Re-validated clean | Failures |
|---|---|---|---|
| `luna-v3.1-508` | 508 | 508 | 0 |
| `luna-v3.1-regression` | 60 | 60 | 0 |
| `luna-v3.2-stability-60-a` | 61 | 61 | 0 |
| `luna-v3.2-stability-60-b` | 60 | 60 | 0 |
| **Total historical** | **689** | **689** | **0** |

Recorded in `docs/manifests/rigveda_semantic_contract_generalization_verification.json`.

**Known consequence.** `codex_direct.py` changed bytes, so its hash moved from
`398b22f2…` to `f972cf43…`. The sealed v3.1-508 freeze pins the old value, so re-running
that seal script now reports frozen-input drift. That is the freeze working as a detector.
The sealed artefact itself is untouched and its responses still validate.

**Known remaining Luna pin, deliberately not changed.** `full_run.py` still hard-codes
`MODEL_PROVENANCE = "gpt-5.6-luna"` and `Freeze.model: Literal["gpt-5.6-luna"]`. That path
(`BatchStore`, full-corpus `Freeze`) is not used by this pilot, which seals through its own
script exactly as the 508 and smoke-8 pilots did. It **will** block a non-Luna
full-corpus run and is recorded as future work rather than changed speculatively.

---

## 2. The abandoned attempt

Classification: `ABORTED_BEFORE_IMPORT_EXECUTION_CAPACITY_EXHAUSTED`
Record: `docs/manifests/rigveda_semantic_abandoned_luna_448_attempt.json`

| Fact | Value |
|---|---|
| prepared tasks | 448 |
| persistence batches prepared | 19 |
| imported semantic responses | **0** |
| raw response receipts | **0** |
| attempt directories | **0** |
| `responses/` directory | does not exist |
| final seal | none |
| final report | none |
| semantic conclusions | none |
| partial author inputs | 10, totalling 46 assertions |
| files deleted | **0** |

All ten partial author inputs **do** contain semantic content, so they are classified
`UNTRUSTED_ABANDONED_AUTHOR_INPUT` and retained for forensic history only. They were not
imported, not compared against, not shown to any author, and not used as expected output.
Every one is preserved unmodified with its sha256 recorded.

**What was reused, and only after verification:** the EvidencePacket preparation. All 448
packets were loaded from the abandoned run's `packets.jsonl` and every `input_sha256`
re-verified against its `packet_build_manifest.json` before a single task was prepared.
Reuse scope is recorded as `EVIDENCE_PACKET_PREPARATION_ONLY`. Packets were **not** rebuilt,
because verification proved them intact.

---

## 3. Frozen policy custody

The V3.2 extraction policy was reused byte-identically. All three spec-declared hashes
matched on inspection and again at seal:

| Input | sha256 |
|---|---|
| `prompts/semantic_extraction_v3.2.md` | `e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1` |
| `schemas/semantic_extraction_v3.schema.json` | `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2` |
| `src/vedagraph/semantic/ontology.py` | `cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce` |
| `object_ontology.py` | `ca2129760d01b7b6f672f794d58e2517065e9326d04f835799c88b3c2d1577cd` |
| `spans.py` | `e16817714b2e8e1c23785176586a9e6bfb2e3de4be726758b81ba8d6a2ef8626` |
| `evidence.py` | `0932564ad228c9dfa87caa945ac7aeece7aca1338a2deb165378f88ee3c1eaee` |
| `codex_direct.py` | `f972cf43621a7daf87ad2e3129ef9956f11fe2989dd6d4a4daae56c2fd1af253` |

No prompt, schema or ontology was created, edited or version-bumped for this run.

### 3.1 Scope extension, recorded not hidden

The frozen prompt's own front matter declares `execution_scope: BOUNDED_60_STABILITY_ONLY`
and `execution_status: NOT_APPROVED_FOR_508_OR_FULL_CORPUS`, while this run applies it to
448 passages. Editing the front matter would change `prompt_sha256` and destroy the one
property the pilot exists to test. The deviation is therefore recorded in
`docs/manifests/rigveda_semantic_v3_2_scope_extension.json` as
`RECORDED_SCOPE_EXTENSION_PROMPT_BYTES_UNCHANGED`, and the prompt is untouched.

The interrupted Luna attempt pinned the same prompt at the same 448 size and never
recorded this deviation. That omission is now closed.

---

## 4. Selection integrity

Pure set subtraction, re-derived and re-verified:

| Check | Required | Observed |
|---|---|---|
| source set | 508 | 508 |
| excluded frozen set | 60 | 60 |
| overlap(source, excluded) | 60 | 60 |
| result | 448 | 448 |
| unique | 448 | 448 |
| invalid passage IDs | 0 | 0 |
| overlap(result, frozen 60) | 0 | 0 |

- selection ids sha256: `aa9538fbb18927ab4c3eeb10aee63b151af513930da8cfc7bf1b8783f1078079`
- historical selection file sha256: `5ce6faea5ab057bdc85aaea3df5ac1eb5a6eba0e7b40b44ecf6414b3303691ef`

The historical selection artefact was **not modified**. A provenance-specific
`run_selection_manifest.json` referencing the same 448 IDs was created instead
(`33f2839c…`).

---

## 5. Multi-agent topology and the single-writer rule

- Coordinator: 1 (this session). Sole importer, validator, sealer.
- Author groups: 6 (A–F), deterministic round-robin over the sorted selection.
- Author contexts: **448**, one isolated context per passage. No context ever saw two passages.
- Orchestration workflows: 4 authoring (canary 24 + 3 chunks of 142/141/141), 1 calibration, 1 deep audit.
- Partition rule: `sorted(passage_ids)[i] -> GROUP[i % 6]`, hash `f6b8db0a…`
- Assignment manifest hash: `cbc4321d…`

Round-robin rather than contiguous blocks was chosen deliberately: contiguous blocks would
have handed one group most of Mandala 9, and any per-group difference would then measure
Mandalas rather than agents. The partition also balanced translation coverage without
being asked to (65–68 translation-bearing per group).

**Single-writer held.** Author agents ran `render` and `check`, both read-only, and wrote
only their own intermediate file. No author agent invoked `import`, wrote to
`store/tasks/`, or touched the run manifest. Every canonical write — task preparation,
raw-response custody, receipts, `ValidatedResponse`, seal — was performed by the
coordinator process.

**No duplicate authoring.** Verified programmatically: 448 unique passages authored, 0
passages authored in more than one group, 0 files outside the assignment, and a maximum of
one terminal validated response per task.

### 5.1 Isolation, audited from transcripts rather than assumed

Agent transcripts were parsed for every tool call. For the canary cohort (24 agents, fully
audited): 24/24 read the frozen V3.2 prompt, 24/24 read the author brief, 24/24 ran
`render`, 24/24 ran `check`, and **0 accessed any forbidden path** — no `docs/reports/`,
no historical Luna/Sol/heuristic artefact, no other passage, no other author's output, and
no abandoned author input.

---

## 6. Execution integrity

Every counter below is from the seal, which re-runs all five validators from scratch on
the stored bytes rather than trusting the import that accepted them.

| Gate | Count |
|---|---|
| expected selected passages | 448 |
| prepared tasks | 448 |
| final validated passages | **448** |
| unique final passages | **448** |
| missing | **0** |
| duplicate finals | **0** |
| receipt failures | **0** |
| packet hash failures | **0** |
| evidence failures | **0** |
| span failures | **0** |
| binding failures | **0** |
| ontology/type failures | **0** |
| provenance mismatch | **0** |
| heuristic contamination | **0** |
| cross-passage duplicate IDs | **0** |

### 6.1 Retries

| Category | Count |
|---|---|
| first-attempt successes | **446 / 448 (99.55%)** |
| `RECEIPT_RETRY` | 2 |
| `FORMAT_RETRY` | 0 |
| `SEMANTIC_RETRY` | 0 |
| `BINDING_RETRY` | 0 |
| `PROVENANCE_RETRY` | 0 |
| `SPAN_RETRY` | 0 |
| `EVIDENCE_RETRY` | 0 |
| `ONTOLOGY_TYPE_RETRY` | 0 |
| preserved failed attempt files | 2 |
| authored response files | 450 (448 terminal + 2 preserved failures) |

No validator was weakened at any point. Both retries succeeded on `attempt_002`; both
failed `attempt_001` artefacts are preserved on disk with their hashes in the seal.

Separately, 223 of the 448 author contexts needed at least one **pre-import** `check`
iteration to fix an anchoring format problem before submitting. Those never reached the
importer and are not import retries; they are the read-only validator doing its job inside
the author context.

### 6.2 A real defect found and fixed during execution

The two `RECEIPT_RETRY` failures were not transient. They exposed a genuine bug in the
import assembly: `response_sha256` was computed over the assembler's **raw dict**, while
`import_response` recomputes it over the **Pydantic-normalised dump**. When an author
supplies `event` as `{"action_head": "..."}`, validation fills four defaulted keys, the
two hashes diverge, and the receipt commits to bytes the validator never sees.

This was confirmed by direct reproduction, then fixed: the payload is now normalised
before the receipt hash is taken, so the two are equal by construction rather than by
luck. `validate_receipt` caught it correctly — the contract worked exactly as designed.

**The same raw-dict hashing exists in the pre-existing Luna import scripts**
(`import_user_selected_luna_v3_2_448.py`, `run_semantic_v3_2_stability_60.py`). It did not
corrupt anything — a divergence causes a hard import refusal, never a silent bad record —
but it is a latent execution hazard for any future run using those scripts. Recorded here
as a bounded engineering follow-up.

A second defect was found and fixed before it could fire: `import-all --attempt N` would
have re-imported already-terminal passages, leaving two terminal responses and breaking
the seal. The done-check is now unconditional; genuine retries go through the
single-passage `import` command.

---

## 7. Structural finding: translation anchor coverage

**50 of 448 packets (11.16%) carry no translation text.** The frozen binding contract
requires every assertion to carry a `RELATION` anchor — and where applicable `TARGET` /
`OUTCOME` anchors — as character spans of the packet translation. A packet with no
translation therefore cannot emit *any* assertion in *any* of the fourteen families,
regardless of what its Sanskrit says.

This is `STRUCTURAL_NO_TRANSLATION_ANCHOR`: an architectural property of the contract, not
model conservatism, and not a model omission.

| | Count |
|---|---|
| translation-bearing (assertion-capable) | **398** |
| translationless (structurally no-claim) | **50** |
| translationless that returned no-claim | **50 / 50** |
| translationless that emitted assertions | **0** |
| translation-bearing that returned no-claim | **0** |

The correspondence is exact in both directions. No author fabricated a Sanskrit-only
anchor to bypass the contract, and no author declined a passage it could have claimed.
The distribution is heavily concentrated: 38 of the 50 are in Mandala 1.

The diagnostic code is a **reporting classification only**. It is not written into any
candidate payload, because the frozen schema has no field for it and this run does not
change the schema.

---

## 8. Git and sealed-artifact safety

- No sealed artefact from any previous run was mutated, moved or deleted.
- No historical run directory was deleted; the abandoned attempt is fully preserved.
- No `git reset`, `clean`, `checkout` or branch operation was performed.
- Pre-existing dirty state was preserved. One pre-existing formatting drift in
  `scripts/compare_user_selected_luna_smoke_8.py` (untouched by this work) was found and
  deliberately **not** fixed, because it is outside this run's scope.
- No commit was made. All changes remain in the working tree for review.

---

## 9. Engineering conclusion

The execution layer performed to contract. 448/448 validated with every integrity counter
at zero, 99.55% first-attempt success, one real latent defect found by the validators
rather than by luck and fixed, provenance recorded honestly including a runtime the
codebase previously could not express, and 689 historical responses proven unaffected.

The one architectural limitation exposed — that 11% of the selection cannot participate in
semantic extraction at all under the current translation-anchor contract — is a coverage
constraint on the corpus layer, not a defect in the extraction policy.
