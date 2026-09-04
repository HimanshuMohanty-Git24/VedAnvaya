# ADR-014: A language model may produce candidates, and only candidates

Status: Accepted
Date: 2026-09-05
Supersedes nothing. Extends [ADR-006](ADR-006-no-llm-canonical-output.md).

## Context

ADR-006 established that no language model output reaches the canonical corpus. That
settled the text. It did not settle what happens when we actually want a model's
judgement — which is the whole point of a semantic layer, because "this hymn asks for
rain" is not derivable from lemma identifiers and never will be.

The tempting shape is: model produces assertions, a confidence threshold filters them,
the survivors become edges. That shape fails for a reason worth naming precisely. The
confidence score is produced by the same process that produced the claim. It carries no
information independent of the claim, so thresholding on it selects for *fluency*, not
for truth. A model that is confidently wrong about RV 10.129 clears 0.9 exactly as
easily as one that is right about RV 1.1.

The second failure is subtler and is specific to this corpus. The Rigveda has several
incompatible commentarial traditions. A `SYMBOLIZES` edge does not record a fact about
the text; it records which school the extractor happened to be trained on, with the
school's name stripped off.

## Decision

**A model may write exactly one status: `CANDIDATE`.** Every other status —
`AUTO_ACCEPTED`, `HUMAN_ACCEPTED`, `VALIDATION_REJECTED`, `NEEDS_REVIEW` — is written by
a deterministic stage or by a person.

Four consequences follow, and none of them is optional:

**Evidence is checkable or the claim is discarded.** Every assertion names the passage
and the tokens it rests on, and the validator checks those against the packet the model
was actually sent. A cited token the model was never shown is a fabricated citation, it
is decidable, and it is rejected. This is the single most valuable check in the layer.

**The predicate vocabulary is closed, and the refusals are named.** Fourteen predicates
are allowed. `SYMBOLIZES`, `REPRESENTS`, `IS_GOD_OF`, `MEANS` and `CAUSES` are in the
enum *so that they can be refused by name*, with a recorded reason, rather than omitted
and silently re-invented as `ASSOCIATED_WITH`.

**Confidence is a floor inside a predicate's rule and nothing else.** Acceptance requires
that the predicate has been *unlocked* by a measured gold precision of ≥ 95%. Until then,
a confidence of 1.0 is accepted at the same rate as 0.4: not at all.

**Similarity may ask; only identity may merge.** A proposed concept reaching a registry
row by normalized label or reviewed alias is that row. A proposal that merely resembles
one becomes a review candidate and creates nothing. No embedding similarity merges
anything in this phase.

## Consequences

Recall is lower than it could be, on purpose, and a first run auto-accepts nothing at
all. That is the intended state of an unmeasured pipeline: acceptance is earned by
measurement, and no measurement has been made.

Building the gold set is now a human bottleneck that cannot be worked around. An
LLM-authored gold set would measure agreement between two model passes — not precision,
and worse than no measurement, because it produces a number that looks like one.

The three deterministic layers are unaffected. They are opened read-only, and the
semantic layer is reconstructable from its committed pilot config, prompt, ontology and
schemas without any of its outputs being committed.
