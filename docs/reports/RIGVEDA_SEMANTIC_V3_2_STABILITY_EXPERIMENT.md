# V3.2 two-run 60-mantra stability experiment

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

Execution state: **COMPLETE — 60/60 in Run A and 60/60 in Run B; both runs sealed.**

The final engineering stability gate passed. Results, custody qualifications, comparison
counts, and seal hashes are recorded in
[RIGVEDA_SEMANTIC_V3_2_STABILITY_RESULT.md](RIGVEDA_SEMANTIC_V3_2_STABILITY_RESULT.md).
The experiment remains defined in `src/vedagraph/semantic/v3_2.py` and its comparators in
`src/vedagraph/semantic/replication_diagnosis.py`.

## Question

Does the V3.2 prompt policy remove the run-level emission-regime split observed under v3.1?

That is the only question this experiment can answer. It is a **policy stability** question,
not a scholarly correctness question. Two runs agreeing does not make either right; there is
no gold set to score against, and none of this promotes any candidate to canonical knowledge.

## Design

Two independent runs over the identical existing bounded selection.

| Field | Value |
| --- | --- |
| Run A | `vedagraph-rigveda-semantic-luna-v3.2-stability-60-a` |
| Run B | `vedagraph-rigveda-semantic-luna-v3.2-stability-60-b` |
| Model | `gpt-5.6-luna` |
| Runtime | `CODEX_DIRECT` |
| Reasoning | `high` |
| Execution version | `rigveda-semantic-execution-v3.2` |
| Prompt policy | `rigveda-semantic-extraction-v3.2` |
| Prompt SHA-256 | `e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1` |
| Schema SHA-256 | `26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2` |
| Ontology SHA-256 | `cddd5a20ca11cf64269d2f877ce4dbb829d0b1eb9fcd56c3718821a47ee228ce` |
| Selection | `data/builds/rigveda_semantic_codex_luna_regression_v1.yaml`, unchanged |
| Selection hash | `26d2f85aec91e621d43444931d40fc81e08a7c9d533bdce820c86945c398783c` |
| Passages | 60 |
| Output status | `CANDIDATE / NEEDS_REVIEW`, `unlocked_predicates = []` |

Both runs use one mantra per reasoning context, the same frozen prompt, schema, ontology and
EvidencePackets, and keep independent immutable raw responses, receipts and manifests. The
selection is the exact bounded real-Luna 60 already used by the v3.1 regression; re-drawing it
would make the v3.1 and v3.2 observations incomparable, which is the one thing the experiment
needs.

`build_stability_experiment()` loads both run contracts independently from the same files, so
`contract_differences()` is a real check on the inputs rather than a restatement of one
object. It returns `[]` today, and a test asserts it: **the two runs differ in run identity
and in nothing else.** Their derived task IDs are disjoint, and both cover exactly the 60
sealed passage IDs.

## What gets measured

### Run-level metrics

Total assertions; assertions per passage; no-claim count; no-claim rate; predicate frequency
distribution; number of predicates with extreme one-sided presence; object-kind distribution;
canonical-reference count.

`emission_regime(outcomes)` derives all of these from what a run actually emitted, passage by
passage, rather than from hand-assembled totals — a run-level number counted by hand is the
kind that quietly disagrees with the artefacts it describes. `compare_regimes` then pairs two
regimes.

### Passage-level agreement

`passage_agreement` over an identical passage set — it refuses a differing one, because an
agreement rate computed over an intersection silently rewards a run for the passages it
skipped. It reports exact assertion-set agreement, predicate-presence agreement, no-claim
agreement, canonical-entity agreement, typed-object agreement and evidence-anchor agreement.

### Engineering safety

Receipt failures, packet/hash failures, evidence failures, span failures, binding failures,
ontology/type failures, heuristic contamination, and canonical-target contradictions —
`IntegrityCounts`. Any non-zero value makes the semantic comparison meaningless and fails the
gate on its own.

### Difference taxonomy

Reused unchanged from the replication audit: `EXACT_ASSERTION`,
`SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE`, `SAME_PREDICATE_COMPATIBLE_OBJECT`,
`OBJECT_GRANULARITY_DIFFERENCE`, `PREDICATE_BOUNDARY_DIFFERENCE`, `TARGET_DIFFERENCE`,
`A_ONLY`, `B_ONLY`, `UNRESOLVED`; and for one-sided rows `SUPPORTED_OMISSION_VARIANCE`,
`PLAUSIBLE_BUT_OPTIONAL`, `UNSUPPORTED_EXTRACTION`, `PREDICATE_POLICY_AMBIGUITY`,
`OBJECT_POLICY_AMBIGUITY`, `EXPERT_REQUIRED`, `UNRESOLVED`.

A supported omission and an unsupported extraction stay distinct: they map to different
diagnostic sets (`ONE_RUN_SUPPORTED` against `SUSPECT_ASSERTION`) and different severities
(MEDIUM against HIGH). No diagnostic set is canonical knowledge — every one carries
`CANDIDATE_NEEDS_REVIEW`.

## Regime-divergence diagnostics

`compare_regimes` returns the no-claim rate gap, the assertion-density gap, per-predicate
counts for both runs, the predicates whose occurrences are entirely one-sided, the
predicate-presence Jaccard, and an exchangeable one-sided probability per predicate.

The probability is a diagnostic that a one-sided predicate skew over identical inputs is not
sampling noise. It is evidence about run behaviour, never about correctness. With n = 2 runs
nothing here establishes how many latent regimes exist; the finding this experiment can
support is **observed run-level emission-regime divergence**, or its absence.

## Stability gate

`stability_gate(comparison, integrity, thresholds)` fails when:

- any integrity count is non-zero (receipt, packet/hash, evidence, span, binding,
  ontology/type, heuristic contamination, or canonical-target contradiction);
- the no-claim rate gap exceeds the threshold — one run entered a different no-claim regime;
- the assertion-density gap exceeds the threshold;
- a predicate is present extensively in one run and absent from the other, either at or above
  the one-sided occurrence threshold or below the skew-probability threshold.

Success is explicitly **not** identical output. Local variance passes: a test feeds a pair
differing by 3 assertions, 2 no-claim passages and 2 `DESCRIBES_ACTION` occurrences and the
gate passes, while the observed v3.1 pair (57/33 assertions, 10/38 no-claim, 21/0
`DESCRIBES_ACTION`) fails on all three counts.

The result carries `claim = "POLICY_STABILITY_ONLY_NOT_ACCURACY"`. There is no 95% accuracy
threshold anywhere, and passing the gate is not an accuracy figure.

## Thresholds

`StabilityThresholds` is configurable and carries
`provenance = "engineering_default_not_truth_derived"` as a field of the type, so the label
travels with any recorded result.

| Threshold | Default | Basis |
| --- | --- | --- |
| `no_claim_rate_gap` | 0.20 | Separates the two already-observed v3.1 regimes (0.167 against 0.633). Not derived from any annotation. |
| `assertion_density_gap` | 0.30 | The v3.1 runs differed by 0.40 assertions per passage over identical packets. |
| `one_sided_predicate_occurrences` | 8 | Where the exchangeable one-sided probability falls below 0.01. |
| `one_sided_skew_probability` | 0.01 | Engineering default for treating a skew as run behaviour rather than noise. |

The 0.2 no-claim tolerance that the replication audit used is **not** treated as scientifically
validated. It is named `NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT`, labelled
`NO_CLAIM_RATE_GAP_PROVENANCE = "engineering_default_not_truth_derived"`, and every caller may
override it. Predicate distribution skew is inspected alongside it, not instead of it.

## Execution preconditions satisfied

1. The 60 EvidencePackets were reused from the frozen selection and their hashes match the
   sealed v3.1 packet hashes.
2. Each run was prepared separately with its own run ID against
   `prompts/semantic_extraction_v3.2.md`, execution version `rigveda-semantic-execution-v3.2`,
   model `gpt-5.6-luna`, reasoning `high`.
3. Each selected final response was authored in a one-mantra reasoning context and declares
   `prompt_version: rigveda-semantic-extraction-v3.2`. A pre-existing surplus valid Run-A
   attempt is preserved and excluded by the declared lowest-attempt-ID rule.
4. The two runs' raw responses, receipts, validated outputs, and seals remain independent.
5. Every v3.1 artefact remained untouched; the relevant sealed-artifact test passes.

## What a pass does and does not authorise

A pass says two runs of one prompt behaved as one policy over 60 packets. It does not
authorise the 508 rerun, does not authorise the full 10,552-mantra extraction, does not
establish accuracy, and does not promote any candidate. A failure identifies which boundary
the policy still leaves open and returns the work to prompt revision.
