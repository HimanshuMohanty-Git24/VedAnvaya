"""Constraints and indexes for the V2 domain layer.

Additive by construction. Every statement here is ``IF NOT EXISTS``, no V1 constraint is
dropped, and no node loses a label -- which is a deliberate choice with a cost worth
stating, because the obvious alternative looks tidier.

The obvious alternative was to strip ``:Concept`` from the 54 registry entities whose
``node_type`` is not a concept type, so that ``MATCH (c:Concept)`` would stop returning
rivers and goats. It was rejected. ``:Concept`` is the MERGE key the enrichment loader
creates these nodes by, the carrier of the ``concept_id`` uniqueness constraint, the match
target of ``BROADER_THAN`` and ``DEVATA_ASSOCIATED_WITH``, the subject of fifteen insight
queries, and the subject of a live invariant that asserts every ``ABOUT_CONCEPT`` edge
points at a ``:Concept``. Removing it would have broken all of that to deliver no
capability that adding the type labels does not already deliver: ``MATCH (a:Animal)`` is
what the killer questions need, and it works either way.

So ``:Concept`` keeps its V1 meaning of "entity from the concept registry", the true type
arrives as an additional label, and :data:`~vedagraph.domain.ontology.LABEL_DOMAIN_ENTITY`
plus ``display_type`` give the narrow question ("only the actual concepts") an answer that
does not require a label change. The one thing this leaves imperfect is the *name*
``Concept`` reading as a type when it now denotes a provenance, which is recorded here
rather than silently tolerated.

``entity_key`` is introduced as a uniform identity property across the whole domain layer.
V1 identity is spread over ``concept_id``, ``entity_key`` and ``formula_id`` depending on
which layer built the node, so "look up this domain entity" needed to know its layer
first. Registry entities keep ``concept_id`` as well; nothing is renamed.
"""

from __future__ import annotations

from typing import Final

from vedagraph.domain.ontology import (
    LABEL_DEITY_AXIS,
    LABEL_DEITY_GROUP,
    LABEL_DERIVED_METRIC,
    LABEL_DOMAIN_ENTITY,
    LABEL_EPITHET,
    LABEL_FORMULA_FAMILY,
    LABEL_INTERPRETIVE_CLAIM,
    LABEL_RISHI_FAMILY,
)

#: Uniform identity across the domain layer, plus identity for the labels V2 introduces.
DOMAIN_CONSTRAINTS: Final[list[str]] = [
    f"CREATE CONSTRAINT domain_entity_key_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_DOMAIN_ENTITY}) REQUIRE n.entity_key IS UNIQUE",
    f"CREATE CONSTRAINT deity_axis_key_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_DEITY_AXIS}) REQUIRE n.axis_key IS UNIQUE",
    f"CREATE CONSTRAINT deity_group_key_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_DEITY_GROUP}) REQUIRE n.group_key IS UNIQUE",
    f"CREATE CONSTRAINT epithet_key_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_EPITHET}) REQUIRE n.epithet_key IS UNIQUE",
    f"CREATE CONSTRAINT rishi_family_key_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_RISHI_FAMILY}) REQUIRE n.family_key IS UNIQUE",
    f"CREATE CONSTRAINT interpretive_claim_id_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_INTERPRETIVE_CLAIM}) REQUIRE n.claim_id IS UNIQUE",
    f"CREATE CONSTRAINT derived_metric_id_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_DERIVED_METRIC}) REQUIRE n.metric_id IS UNIQUE",
    f"CREATE CONSTRAINT formula_family_id_unique IF NOT EXISTS "
    f"FOR (n:{LABEL_FORMULA_FAMILY}) REQUIRE n.family_id IS UNIQUE",
]

#: Node indexes. ``display_type`` is indexed because it is the property that answers the
#: narrow-type question the retained ``:Concept`` label cannot.
DOMAIN_NODE_INDEXES: Final[list[str]] = [
    f"CREATE INDEX domain_entity_display_type IF NOT EXISTS "
    f"FOR (n:{LABEL_DOMAIN_ENTITY}) ON (n.display_type)",
    f"CREATE INDEX domain_entity_display_label IF NOT EXISTS "
    f"FOR (n:{LABEL_DOMAIN_ENTITY}) ON (n.display_label)",
    "CREATE INDEX devata_structure IF NOT EXISTS FOR (n:Devata) ON (n.structure)",
    f"CREATE INDEX derived_metric_name IF NOT EXISTS "
    f"FOR (n:{LABEL_DERIVED_METRIC}) ON (n.metric_name)",
    f"CREATE INDEX interpretive_claim_status IF NOT EXISTS "
    f"FOR (n:{LABEL_INTERPRETIVE_CLAIM}) ON (n.status)",
    # Both support the questions the family layer exists to answer: "which formula
    # families span three or four Vedas?" and "which families are largest?".
    f"CREATE INDEX formula_family_cross_veda IF NOT EXISTS "
    f"FOR (n:{LABEL_FORMULA_FAMILY}) ON (n.cross_veda)",
    f"CREATE INDEX formula_family_veda_span IF NOT EXISTS "
    f"FOR (n:{LABEL_FORMULA_FAMILY}) ON (n.veda_span)",
    f"CREATE INDEX formula_family_member_count IF NOT EXISTS "
    f"FOR (n:{LABEL_FORMULA_FAMILY}) ON (n.member_count)",
]

#: Relationship property indexes for the unified grade. Without these, "show me only
#: source-explicit edges" is a full relationship scan, which is the shape of query the
#: whole grading layer exists to make cheap.
DOMAIN_REL_INDEXES: Final[list[str]] = [
    "CREATE INDEX rel_quality_tier_devata IF NOT EXISTS "
    "FOR ()-[r:HAS_DEVATA]-() ON (r.quality_tier)",
    "CREATE INDEX rel_precision_devata IF NOT EXISTS "
    "FOR ()-[r:HAS_DEVATA]-() ON (r.attribution_precision)",
    "CREATE INDEX rel_quality_tier_rishi IF NOT EXISTS FOR ()-[r:HAS_RISHI]-() ON (r.quality_tier)",
    "CREATE INDEX rel_quality_tier_chandas IF NOT EXISTS "
    "FOR ()-[r:HAS_CHANDAS]-() ON (r.quality_tier)",
    "CREATE INDEX rel_quality_tier_mentions IF NOT EXISTS "
    "FOR ()-[r:MENTIONS_ENTITY]-() ON (r.quality_tier)",
    "CREATE INDEX rel_member_of_family_role IF NOT EXISTS "
    "FOR ()-[r:MEMBER_OF_FAMILY]-() ON (r.role)",
    # The outward mirror carries the same ``role``, and the family-to-formula direction is
    # the one a reader browses ("show me this family's core phrase"), so it needs the index
    # at least as much as the inbound edge does.
    "CREATE INDEX rel_has_formula_role IF NOT EXISTS FOR ()-[r:HAS_FORMULA]-() ON (r.role)",
    # Indexed on ``method`` and not on ``quality_tier``, because every one of the 306 ṛṣi
    # memberships is TIER_B and the tier therefore partitions nothing. ``method`` is the
    # property that does: it separates the 291 patronymics the Anukramaṇī printed as their
    # own word from the 15 where this layer supplied the word boundary, which is the filter
    # a sceptical reader actually wants.
    "CREATE INDEX rel_belongs_to_family_method IF NOT EXISTS "
    "FOR ()-[r:BELONGS_TO_FAMILY]-() ON (r.method)",
]


def all_domain_schema_cypher() -> list[str]:
    """Every V2 constraint and index, in application order."""
    return DOMAIN_CONSTRAINTS + DOMAIN_NODE_INDEXES + DOMAIN_REL_INDEXES
