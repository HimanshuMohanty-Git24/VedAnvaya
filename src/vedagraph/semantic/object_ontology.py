"""Versioned vocabulary for occurrence-level semantic objects.

This module does not extend or unlock the semantic predicate vocabulary.  It defines
how the *object* of an existing predicate is represented and compared.  In particular,
an occurrence candidate is not a global semantic concept and a display label is never
an identity key.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from vedagraph.semantic.ontology import SemanticPredicate

SEMANTIC_OBJECT_SCHEMA_VERSION = "rigveda-semantic-object-v1"
COMPARISON_POLICY_VERSION = "rigveda-semantic-object-comparison-v1"
EXPLICITNESS_POLICY_VERSION = "rigveda-semantic-explicitness-v2"


class SemanticObjectKind(StrEnum):
    """Occurrence-level object families; none is a canonical concept by itself."""

    CANONICAL_ENTITY_REF = "CANONICAL_ENTITY_REF"
    SEMANTIC_ENTITY_REF = "SEMANTIC_ENTITY_REF"
    EVENT = "EVENT"
    REQUESTED_OUTCOME = "REQUESTED_OUTCOME"
    RITUAL_EVENT = "RITUAL_EVENT"
    OFFERING_REF = "OFFERING_REF"
    SUBSTANCE_REF = "SUBSTANCE_REF"
    NATURAL_PHENOMENON_REF = "NATURAL_PHENOMENON_REF"
    PLACE_REF = "PLACE_REF"
    STATE_REF = "STATE_REF"
    QUALITY_REF = "QUALITY_REF"
    CONCEPT_REF = "CONCEPT_REF"
    ACTION_REF = "ACTION_REF"
    OPAQUE_REFERENT = "OPAQUE_REFERENT"
    OPAQUE_SPATIAL_REFERENT = "OPAQUE_SPATIAL_REFERENT"
    ONTOLOGY_GAP_REF = "ONTOLOGY_GAP_REF"


class SemanticObjectNormalizationStatus(StrEnum):
    """How far an occurrence has progressed toward reviewed normalization."""

    CANONICAL_REF = "CANONICAL_REF"
    NORMALIZED_CANDIDATE = "NORMALIZED_CANDIDATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    AMBIGUOUS = "AMBIGUOUS"
    ONTOLOGY_GAP = "ONTOLOGY_GAP"
    UNRESOLVED_LEGACY_OBJECT = "UNRESOLVED_LEGACY_OBJECT"


class SemanticOntologyGapCode(StrEnum):
    """Specific gaps exposed without forcing an incorrect ontology type."""

    PERSON_LIKE_REFERENT_UNMODELED = "PERSON_LIKE_REFERENT_UNMODELED"
    PATRON_ROLE_UNMODELED = "PATRON_ROLE_UNMODELED"
    ANCESTOR_ROLE_UNMODELED = "ANCESTOR_ROLE_UNMODELED"
    KINSHIP_ROLE_UNMODELED = "KINSHIP_ROLE_UNMODELED"
    OTHER_UNMODELED = "OTHER_UNMODELED"


class StructuredComparisonCategory(StrEnum):
    """Evidence-aware model-model outcomes; never human-gold verdicts."""

    EXACT_CANONICAL_ENTITY = "EXACT_CANONICAL_ENTITY"
    EXACT_NORMALIZED_OBJECT = "EXACT_NORMALIZED_OBJECT"
    COMPATIBLE_OBJECT = "COMPATIBLE_OBJECT"
    PARTIAL_OBJECT_OVERLAP = "PARTIAL_OBJECT_OVERLAP"
    GRANULARITY_DIFFERENCE = "GRANULARITY_DIFFERENCE"
    PREDICATE_DIFFERENCE = "PREDICATE_DIFFERENCE"
    OBJECT_TYPE_DIFFERENCE = "OBJECT_TYPE_DIFFERENCE"
    CONFLICTING_OBJECT = "CONFLICTING_OBJECT"
    UNRESOLVED = "UNRESOLVED"
    EXPERT_REQUIRED = "EXPERT_REQUIRED"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"
    NO_CLAIM_AGREEMENT = "NO_CLAIM_AGREEMENT"


class DisagreementDecomposition(StrEnum):
    """One primary diagnostic bucket for each benchmark mantra."""

    REPRESENTATION_MISMATCH = "REPRESENTATION_MISMATCH"
    OBJECT_GRANULARITY_MISMATCH = "OBJECT_GRANULARITY_MISMATCH"
    PREDICATE_MISMATCH = "PREDICATE_MISMATCH"
    ACTUAL_SEMANTIC_CONFLICT = "ACTUAL_SEMANTIC_CONFLICT"
    ONTOLOGY_GAP = "ONTOLOGY_GAP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED_LEGACY_LABEL = "UNRESOLVED_LEGACY_LABEL"


class ExplicitnessPolicyAssessment(StrEnum):
    """Policy audit categories, not retrospective edits to model output."""

    CORRECTLY_STRONG_INFERENCE = "CORRECTLY_STRONG_INFERENCE"
    SHOULD_HAVE_BEEN_EXPLICIT = "SHOULD_HAVE_BEEN_EXPLICIT"
    TOO_INTERPRETIVE_TO_EMIT = "TOO_INTERPRETIVE_TO_EMIT"
    SCHEMA_AMBIGUITY = "SCHEMA_AMBIGUITY"


@dataclass(frozen=True)
class PredicateObjectRule:
    """Preferred and review-only occurrence object kinds for one locked predicate."""

    preferred: frozenset[SemanticObjectKind]
    review_only: frozenset[SemanticObjectKind] = frozenset()


PREDICATE_OBJECT_RULES: dict[SemanticPredicate, PredicateObjectRule] = {
    SemanticPredicate.INVOKES: PredicateObjectRule(
        frozenset({SemanticObjectKind.CANONICAL_ENTITY_REF}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT, SemanticObjectKind.ONTOLOGY_GAP_REF}),
    ),
    SemanticPredicate.PRAISES: PredicateObjectRule(
        frozenset({SemanticObjectKind.CANONICAL_ENTITY_REF}),
        frozenset(
            {
                SemanticObjectKind.SEMANTIC_ENTITY_REF,
                SemanticObjectKind.OPAQUE_REFERENT,
                SemanticObjectKind.ONTOLOGY_GAP_REF,
            }
        ),
    ),
    SemanticPredicate.DESCRIBES: PredicateObjectRule(
        frozenset(
            {
                SemanticObjectKind.CANONICAL_ENTITY_REF,
                SemanticObjectKind.SEMANTIC_ENTITY_REF,
            }
        ),
        frozenset(
            {
                SemanticObjectKind.OPAQUE_REFERENT,
                SemanticObjectKind.ONTOLOGY_GAP_REF,
            }
        ),
    ),
    SemanticPredicate.REQUESTS: PredicateObjectRule(
        frozenset({SemanticObjectKind.REQUESTED_OUTCOME}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT, SemanticObjectKind.ONTOLOGY_GAP_REF}),
    ),
    SemanticPredicate.DESCRIBES_ACTION: PredicateObjectRule(
        frozenset({SemanticObjectKind.EVENT}),
        frozenset({SemanticObjectKind.ACTION_REF, SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.INVOLVES_RITUAL: PredicateObjectRule(
        frozenset({SemanticObjectKind.RITUAL_EVENT}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.INVOLVES_OFFERING: PredicateObjectRule(
        frozenset({SemanticObjectKind.OFFERING_REF}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.INVOLVES_SUBSTANCE: PredicateObjectRule(
        frozenset({SemanticObjectKind.SUBSTANCE_REF}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON: PredicateObjectRule(
        frozenset({SemanticObjectKind.NATURAL_PHENOMENON_REF}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.REFERS_TO_PLACE: PredicateObjectRule(
        frozenset({SemanticObjectKind.PLACE_REF}),
        frozenset(
            {
                SemanticObjectKind.OPAQUE_SPATIAL_REFERENT,
                SemanticObjectKind.OPAQUE_REFERENT,
            }
        ),
    ),
    SemanticPredicate.EXPRESSES: PredicateObjectRule(
        frozenset(
            {
                SemanticObjectKind.STATE_REF,
                SemanticObjectKind.QUALITY_REF,
                SemanticObjectKind.CONCEPT_REF,
                SemanticObjectKind.SEMANTIC_ENTITY_REF,
            }
        ),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.HAS_THEME: PredicateObjectRule(
        frozenset({SemanticObjectKind.CONCEPT_REF}),
        frozenset({SemanticObjectKind.OPAQUE_REFERENT}),
    ),
    SemanticPredicate.ASSOCIATED_WITH: PredicateObjectRule(
        frozenset(), frozenset(SemanticObjectKind)
    ),
    SemanticPredicate.CONTRASTS_WITH: PredicateObjectRule(
        frozenset(), frozenset(SemanticObjectKind)
    ),
}


def object_kind_is_allowed(predicate: SemanticPredicate, kind: SemanticObjectKind) -> bool:
    """Return whether the locked predicate can carry this kind in v3 candidate output."""
    rule = PREDICATE_OBJECT_RULES.get(predicate)
    return rule is not None and kind in rule.preferred | rule.review_only
