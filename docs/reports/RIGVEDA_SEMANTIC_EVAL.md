# Rigveda Semantic Evaluation

Evaluation version: `rigveda-semantic-evaluation-v1`
Gold worksheet: [`data/gold/rigveda_semantic_gold_v1.jsonl`](../../data/gold/rigveda_semantic_gold_v1.jsonl)

**No human-gold evaluation has been run.** The gold subset is not annotated. The
Codex-direct pilot has produced review candidates, but those suggestions are not labels
and are not scored as gold.

---

## Current state

| measure | value |
|---|---|
| gold mantras selected | 120 |
| gold mantras annotated | **0** |
| Codex-direct pilot extractions | **508** |
| vendor API extractions | **0** |
| predicates unlocked for automatic acceptance | **0 of 14** |

Every figure below is therefore a specification, not a finding. There is no
"precision so far", and nothing in this repository reports one.

---

## What is measured

Against the annotated gold subset only:

| metric | definition |
|---|---|
| entity precision / recall | proposed entity labels vs. annotated ones, on the normalized label |
| relation precision / recall | (predicate, object) pairs, **per predicate** |
| evidence correctness | share of assertions whose cited evidence survives structural validation |
| unsupported assertion rate | assertions rejected by the validator, over all assertions |
| wrong-entity rate | right predicate, wrong object |
| wrong-predicate rate | right object, wrong relation name |
| explicitness overstatement | claims graded more literal than the annotator graded them |
| **rejected-relation emissions** | claims the annotator explicitly marked tempting-and-unsupported |
| duplicate-concept rate | normalization-queue groups per accepted entity |
| parallel consistency | agreement between extractions of verbatim-identical mantras |

### Precision is reported per predicate, never as an average

The acceptance policy is per predicate, so a global average would hide a predicate at
60% behind one at 99% and unlock both. `PredicateScore` is computed and reported
separately for each of the fourteen.

### Rejected relations measure restraint

A gold annotation may record a relation as `rejected: true` — something a careful reader
would be drawn to and which the text does not support. Emitting one is a false positive
that a naive evaluation never sees, because it is not merely "absent from gold". Counting
these separately is the only way to measure whether the model **declines** when it should,
and declining is most of what this layer asks of it.

### An unannotated worksheet is not a gold set of zero

The evaluator skips rows marked `UNANNOTATED`. Scoring against them would read an empty
file as "the annotator says none of these relations are present" and report a precision
of zero — a number that looks like a measurement and is not one. An empty gold set
unlocks nothing, which is the correct consequence of not having measured.

---

## Readiness target

**Accepted-assertion precision ≥ 95% per predicate**, for any predicate intended for
automatic acceptance.

A predicate that misses it is **not** unlocked. The response to missing the target is to
restrict the auto-accepted predicate set, never to lower the threshold: a target adjusted
to fit a result measures nothing except willingness to adjust it. `PRECISION_TARGET` is a
constant in `evaluate.py` with that written next to it.

A predicate absent from the gold subset is likewise never unlocked. No evidence is not
the same as good evidence.

Precision is preferred to recall throughout. A missing edge is found by extending
coverage; a wrong edge is found by someone who trusted it.

---

## Reasoning-effort comparison (planned, not run)

`gpt-5.6-luna` supports `none, low, medium, high, xhigh, max`; `medium` is the provider
default. The plan is to run the **same fixed subset** — the 120 gold mantras — at
`medium` and at `high`, and compare cost, latency, precision, recall and output size.

The selection rule is the lowest-cost configuration that meets the quality target, not
the highest score. There is no assumption that `high` is better: more reasoning on a
task whose main requirement is *restraint* can as easily produce more confident
over-reading, and that is a hypothesis to test rather than to assume in either direction.

Until this comparison runs, the pinned configuration is `medium`, chosen as the
provider's own default rather than on evidence — and labelled that way in
`ExtractionConfig`.

---

## Parallel consistency (planned, not run)

45 pilot mantras are exact textual parallels. After extraction their results are compared
pairwise and `compare_exact_parallels` reports agreement.

Disagreement is a **finding, not a defect to repair**. Two identical lines in two hymns
genuinely can carry different claims, because context differs. What the number is for is
stability: an extractor that disagrees with itself on identical input is telling you its
output is noise, whatever a single pass's precision looks like. Nothing is ever copied
between parallels, and a test asserts that.

---

## What a passing evaluation would authorise

A gold evaluation meeting the target for a given predicate unlocks **that predicate**,
for `EXPLICIT` claims only, subject to that predicate's confidence floor and to every
structural check. It authorises nothing else.

In particular it does not authorise full-corpus extraction. That is a separate decision,
made by a person, after reading the cost report and this one.
