# ADR-015: Semantic relation objects are typed, evidenced occurrences

Status: Accepted
Date: 2026-09-05
Extends [ADR-014](ADR-014-llm-output-is-candidate-only.md).

## Context

The first two semantic extraction schemas represented non-canonical relation objects as
reusable semantic-entity candidates. Their comparison identity was effectively a
normalized generated label. This conflates an occurrence (“this mantra requests
protection”) with a possible global concept (`PROTECTION`) and makes wording variation
look like either identity or disagreement.

## Decision

Semantic relation targets are occurrence-level `SemanticObjectCandidate` records with a
predicate-appropriate object kind and deterministic evidence anchors. Canonical registry
entities are referenced directly. Events, requested outcomes, ritual events, offerings,
substances, phenomena, places, states, qualities, concepts, opaque referents, and
ontology gaps remain distinct.

An assertion signature combines subject, locked predicate, typed object structure, and
evidence structure. Display labels are excluded from identity. Fuzzy or embedding
similarity may never establish equivalence.

Occurrence IDs are deterministic within an extraction artifact but do not identify a
canonical concept. Canonical semantic concepts remain a later reviewed layer.

Legacy outputs are migrated only for diagnosis and remain immutable. Ambiguous or
sentence-like labels fail closed as `UNRESOLVED_LEGACY_OBJECT`. Historical metrics are
preserved beside structured metrics.

## Consequences

Comparison can recognize identical canonical keys across spellings, compare action roles
independently, ignore requested-outcome ordering, and preserve ritual/offering/substance
and deity/phenomenon boundaries. More cases become explicitly unresolved; this is a
feature, because representation cannot manufacture a philological decision.

No predicate is unlocked and no model-model agreement becomes acceptance or human gold.
