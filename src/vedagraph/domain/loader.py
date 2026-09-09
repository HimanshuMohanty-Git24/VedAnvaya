"""Write the V2 domain layer into Neo4j, and report what actually landed.

Every function here returns rows *sent* alongside rows *landed*, and they are not assumed
equal. A projection that reports only what it sent cannot distinguish a successful write
from one whose ``MATCH`` found no endpoint, and an edge whose subject key does not resolve
produces no row, no error and no edge -- the quietest failure in the system. Three real
defects in this repository's history were of exactly that shape, so the difference between
the two numbers is the primary output of this module rather than a diagnostic extra.

**Existing edges are extended, not overwritten.** ``MENTIONS_ENTITY`` already carries
9,000 Rigvedic deity mentions written by the lexical layer from manual morphological
annotation, and those rows hold provenance this layer cannot reconstruct -- an
``annotation_layer_id`` naming the Zurich annotation. So every MERGE here separates
``ON CREATE SET``, which writes the full envelope for a new edge, from ``ON MATCH SET``,
which adds only the V2 grade to an edge that already existed. Extending deity mentions
from one Veda to four must not cost the provenance of the one that was already right.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from vedagraph.domain.claims import InterpretiveClaim
from vedagraph.domain.ontology import (
    DOMAIN_MODEL_VERSION,
    LABEL_DEITY_AXIS,
    LABEL_DEITY_GROUP,
    LABEL_DERIVED_METRIC,
    LABEL_DOMAIN_ENTITY,
    LABEL_EPITHET,
    LABEL_INTERPRETIVE_CLAIM,
    AttributionPrecision,
    KnowledgeLayer,
    QualityTier,
    labels_for_node_type,
)
from vedagraph.domain.profiles import DerivedMetric, DevataProfile
from vedagraph.domain.taxonomy import DevataTaxonomyEntry, axis_row, group_row
from vedagraph.enrich.records import ConceptRow

#: Rows per transaction. Matches the V1 loader so that memory behaviour is predictable
#: across both.
BATCH_SIZE: int = 500


class Session(Protocol):
    def run(self, query: str, /, **kwargs: Any) -> Any: ...


@dataclass
class LoadReport:
    """What one load step sent and what landed."""

    step: str
    sent: int = 0
    landed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.sent == self.landed

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "detail": self.detail,
        }


def _batches(rows: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [list(rows[i : i + BATCH_SIZE]) for i in range(0, len(rows), BATCH_SIZE)]


def _write(
    session: Session, query: str, rows: Sequence[dict[str, Any]], **parameters: Any
) -> None:
    for batch in _batches(rows):
        session.run(query, rows=batch, **parameters)


# ---------------------------------------------------------------------------
# Domain entity nodes
# ---------------------------------------------------------------------------


def load_entities(session: Session, entities: Sequence[ConceptRow]) -> LoadReport:
    """MERGE every registry entity as a node carrying its real type labels.

    Grouped by label set because Cypher cannot parameterise a label. There are about
    twenty distinct sets, which is far cheaper than a round trip per entity and avoids
    making the loader depend on APOC for something the type system already knows.

    V1 created these nodes as bare ``:Concept``. This writes the same identity with the
    type labels attached, so a re-run over an existing graph converges rather than
    duplicating -- ``entity_key`` is the MERGE key and it equals the V1 ``concept_id``.
    """
    report = LoadReport(step="entities", sent=len(entities))
    if not entities:
        return report

    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for entity in entities:
        labels = labels_for_node_type(entity.node_type)
        grouped.setdefault(labels, []).append(
            {
                "entity_key": entity.concept_id,
                "concept_id": entity.concept_id,
                "node_type": entity.node_type,
                "preferred_label_sa": entity.preferred_label_sa,
                "preferred_label_en": entity.preferred_label_en,
                "definition": entity.definition,
                "short_description": entity.definition,
                "aliases_sa": list(entity.aliases_sa),
                "aliases_en": list(entity.aliases_en),
                "display_label": (
                    f"{entity.preferred_label_en} ({entity.preferred_label_sa})"
                    if entity.preferred_label_en and entity.preferred_label_sa
                    else entity.preferred_label_en or entity.preferred_label_sa
                ),
                "display_type": labels[0],
                "domain_model_version": DOMAIN_MODEL_VERSION,
            }
        )

    for labels, rows in sorted(grouped.items()):
        clause = ":".join(labels)
        _write(
            session,
            f"UNWIND $rows AS row "
            f"MERGE (e:Concept {{concept_id: row.concept_id}}) "
            f"SET e:{clause}, e += row",
            rows,
        )

    # Registry-stated edges. SOURCE_EXPLICIT rather than derived: nothing was computed, a
    # person wrote the statement down and the definition is the evidence.
    _write(
        session,
        f"""
        UNWIND $rows AS row
        MATCH (parent:{LABEL_DOMAIN_ENTITY} {{entity_key: row.parent}})
        MATCH (child:{LABEL_DOMAIN_ENTITY} {{entity_key: row.child}})
        MERGE (parent)-[r:BROADER_THAN]->(child)
        ON CREATE SET r.knowledge_layer = $layer, r.quality_tier = $tier,
                      r.grade_basis = 'stated by the entity registry'
        """,
        [
            {"parent": parent, "child": entity.concept_id}
            for entity in entities
            for parent in entity.broader
        ],
        layer=str(KnowledgeLayer.L1_SOURCE_EXPLICIT),
        tier=str(QualityTier.TIER_A),
    )
    _write(
        session,
        f"""
        UNWIND $rows AS row
        MATCH (dv:Devata {{entity_key: row.devata}})
        MATCH (e:{LABEL_DOMAIN_ENTITY} {{entity_key: row.entity_key}})
        MERGE (dv)-[r:DEVATA_ASSOCIATED_WITH]->(e)
        ON CREATE SET r.knowledge_layer = $layer, r.quality_tier = $tier,
                      r.grade_basis = 'stated by the entity registry'
        """,
        [
            {"devata": devata, "entity_key": entity.concept_id}
            for entity in entities
            for devata in entity.related_devatas
        ],
        layer=str(KnowledgeLayer.L1_SOURCE_EXPLICIT),
        tier=str(QualityTier.TIER_A),
    )

    report.landed = session.run(
        f"MATCH (e:{LABEL_DOMAIN_ENTITY}) WHERE e.entity_key IS NOT NULL "
        "RETURN count(e) AS c"
    ).single()["c"]
    report.detail = {
        "label_sets": {":".join(labels): len(rows) for labels, rows in sorted(grouped.items())},
        "broader_than_edges": session.run(
            "MATCH ()-[r:BROADER_THAN]->() RETURN count(r) AS c"
        ).single()["c"],
        "devata_associated_edges": session.run(
            "MATCH ()-[r:DEVATA_ASSOCIATED_WITH]->() RETURN count(r) AS c"
        ).single()["c"],
    }
    return report


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------

_MENTION_QUERY = f"""
UNWIND $rows AS row
MATCH (p:Passage {{canonical_key: row.passage_key}})
MATCH (e:{LABEL_DOMAIN_ENTITY} {{entity_key: row.entity_key}})
MERGE (p)-[m:MENTIONS_ENTITY]->(e)
ON CREATE SET m.mention_id = row.mention_id,
              m.matched_aliases = row.matched_aliases,
              m.alias_count = row.alias_count,
              m.theonym_ambiguous = row.theonym_ambiguous,
              m.trust = row.trust,
              m.method = row.method,
              m.score = row.score,
              m.evidence = row.evidence,
              m.evidence_count = row.evidence_count,
              m.state = row.state,
              m.pipeline_version = row.pipeline_version,
              m.run_id = row.run_id,
              m.domain_model_version = row.domain_model_version,
              m.knowledge_layer = $layer,
              m.quality_tier = $tier,
              m.attribution_precision = $precision,
              m.grade_basis = 'domain mention: Sanskrit alias matched in this passage',
              m.build_pass = $build_pass
ON MATCH SET  m.build_pass = $build_pass,
              m.mention_id = row.mention_id,
              m.matched_aliases = row.matched_aliases,
              m.alias_count = row.alias_count,
              m.theonym_ambiguous = row.theonym_ambiguous,
              m.method = row.method,
              m.score = row.score,
              m.evidence = row.evidence,
              m.evidence_count = row.evidence_count,
              m.run_id = row.run_id,
              m.domain_model_version = row.domain_model_version,
              m.knowledge_layer = coalesce(m.knowledge_layer, $layer),
              m.quality_tier = coalesce(m.quality_tier, $tier),
              m.attribution_precision = coalesce(m.attribution_precision, $precision)
"""
# ON MATCH refreshes the fields this layer computes, and only those.
#
# The first version coalesced everything, on the reasoning that an existing edge might
# carry provenance this layer cannot reconstruct. That reasoning is right for the lexical
# layer's 9,000 Rigvedic deity mentions -- but this MERGE cannot reach them, because it
# matches on `:DomainEntity` and those edges point at `:Devata`. So the conservatism
# protected nothing and silently froze a computed field: after `theonym_ambiguous` was
# fixed to test inflected forms, a rebuild recomputed every row correctly and then wrote
# none of them, because all 28,675 edges already existed and took the ON MATCH branch.
# The flag stayed at its old value and the rebuild reported success.
#
# MERGE does not only fail to forget; it also fails to update unless told to.


def load_mentions(session: Session, rows: Sequence[dict[str, Any]]) -> LoadReport:
    """MERGE domain mention edges, preserving earlier layers and retiring stale ones.

    The reconciliation pass is not housekeeping. When an alias is removed from the
    lexicon, MERGE alone leaves every edge it produced in place, and the graph goes on
    asserting a mention the current lexicon no longer supports -- with full evidence
    attached, so it looks checkable. This was caught in the build: seven ``SVAN-DOG``
    edges survived the removal of the alias ``śvā``, which had been dropped precisely
    because the elision of initial *a-* makes ``aśvā`` ("mare") spell itself ``śvā``, so
    it was matching horses. Retiring them is what makes the lexicon's *rejections*
    effective rather than advisory.

    Only edges this layer owns are touched. The lexical layer's 9,000 Rigvedic deity
    mentions carry no ``mention_id``, so they are outside the delete's reach by
    construction rather than by a filter someone has to remember.
    """
    report = LoadReport(step="mentions", sent=len(rows))
    if not rows:
        return report
    build_pass = uuid.uuid4().hex
    before = session.run(
        f"MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:{LABEL_DOMAIN_ENTITY}) "
        "RETURN count(m) AS c"
    ).single()["c"]
    for batch in _batches(rows):
        session.run(
            _MENTION_QUERY,
            rows=batch,
            layer=str(KnowledgeLayer.L2_DETERMINISTIC_DERIVED),
            tier=str(QualityTier.TIER_B),
            precision=str(AttributionPrecision.PER_PASSAGE),
            build_pass=build_pass,
        )

    # Mark and sweep rather than "delete what is not in this list": the list is 28,693
    # ids and a `NOT IN` over 37,700 edges is a billion string comparisons. Every edge the
    # pass touched carries build_pass; anything this layer owns without it is stale.
    retired = session.run(
        f"""
        MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:{LABEL_DOMAIN_ENTITY})
        WHERE m.mention_id IS NOT NULL
          AND (m.build_pass IS NULL OR m.build_pass <> $build_pass)
        DELETE m
        RETURN count(*) AS retired
        """,
        build_pass=build_pass,
    ).single()["retired"]
    after = session.run(
        f"MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:{LABEL_DOMAIN_ENTITY}) "
        "RETURN count(m) AS c"
    ).single()["c"]
    stamped = session.run(
        f"MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:{LABEL_DOMAIN_ENTITY}) "
        "WHERE m.mention_id IS NOT NULL RETURN count(m) AS c"
    ).single()["c"]
    report.landed = stamped
    report.detail = {
        "edges_before": before,
        "edges_after": after,
        "newly_created": after - before,
        "carrying_mention_id": stamped,
        "retired_stale": retired,
        "theonym_ambiguous": session.run(
            f"MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:{LABEL_DOMAIN_ENTITY}) "
            "WHERE m.theonym_ambiguous RETURN count(m) AS c"
        ).single()["c"],
    }
    return report


# ---------------------------------------------------------------------------
# Devata taxonomy
# ---------------------------------------------------------------------------


def load_devata_taxonomy(
    session: Session, entries: Sequence[DevataTaxonomyEntry]
) -> LoadReport:
    """Apply the overlay: Devatā properties, axis/epithet/group nodes, and their edges."""
    report = LoadReport(step="devata_taxonomy", sent=len(entries))
    if not entries:
        return report

    axes = sorted({axis for entry in entries for axis in entry.axes}, key=str)
    _write(
        session,
        f"UNWIND $rows AS row MERGE (a:{LABEL_DEITY_AXIS} {{axis_key: row.axis_key}}) "
        "SET a += row",
        [axis_row(axis) for axis in axes],
    )
    groups = sorted({key for entry in entries for key in entry.member_of})
    _write(
        session,
        f"UNWIND $rows AS row MERGE (g:{LABEL_DEITY_GROUP} {{group_key: row.group_key}}) "
        "SET g += row",
        [group_row(key) for key in groups],
    )
    epithets = {
        epithet.epithet_key: epithet.as_row()
        for entry in entries
        for epithet in entry.epithets
    }
    _write(
        session,
        f"UNWIND $rows AS row MERGE (e:{LABEL_EPITHET} {{epithet_key: row.epithet_key}}) "
        "SET e += row",
        [epithets[key] for key in sorted(epithets)],
    )

    _write(
        session,
        "UNWIND $rows AS row MATCH (dv:Devata {entity_key: row.entity_key}) SET dv += row",
        [entry.as_row() for entry in entries],
    )

    _write(
        session,
        f"""
        UNWIND $rows AS row
        MATCH (dv:Devata {{entity_key: row.entity_key}})
        MATCH (a:{LABEL_DEITY_AXIS} {{axis_key: row.axis_key}})
        MERGE (dv)-[r:HAS_AXIS]->(a)
        ON CREATE SET r.grade_basis = 'curated deity axis from the V2 overlay',
                      r.curation_confidence = row.confidence
        """,
        [
            {
                "entity_key": entry.entity_key,
                "axis_key": f"VG:DEITYAXIS:{axis}",
                "confidence": entry.confidence,
            }
            for entry in entries
            for axis in entry.axes
        ],
    )
    session.run(
        "MATCH ()-[r:HAS_AXIS]->() SET r.knowledge_layer = $layer, r.quality_tier = $tier",
        layer=str(KnowledgeLayer.L4_INTERPRETIVE_CLAIM),
        tier=str(QualityTier.TIER_D),
    )

    _write(
        session,
        f"""
        UNWIND $rows AS row
        MATCH (dv:Devata {{entity_key: row.entity_key}})
        MATCH (e:{LABEL_EPITHET} {{epithet_key: row.epithet_key}})
        MERGE (dv)-[r:HAS_EPITHET]->(e)
        ON CREATE SET r.grade_basis = 'curated epithet from the V2 overlay'
        """,
        [
            {"entity_key": entry.entity_key, "epithet_key": epithet.epithet_key}
            for entry in entries
            for epithet in entry.epithets
        ],
    )
    _write(
        session,
        f"""
        UNWIND $rows AS row
        MATCH (dv:Devata {{entity_key: row.entity_key}})
        MATCH (g:{LABEL_DEITY_GROUP} {{group_key: row.group_key}})
        MERGE (dv)-[r:MEMBER_OF]->(g)
        """,
        [
            {"entity_key": entry.entity_key, "group_key": key}
            for entry in entries
            for key in entry.member_of
        ],
    )
    _write(
        session,
        """
        UNWIND $rows AS row
        MATCH (whole:Devata {entity_key: row.entity_key})
        MATCH (part:Devata {entity_key: row.component})
        MERGE (whole)-[r:COMPOSED_OF]->(part)
        ON CREATE SET r.grade_basis = 'dual or composite label decomposed into components'
        """,
        [
            {"entity_key": entry.entity_key, "component": component}
            for entry in entries
            for component in entry.composed_of
        ],
    )
    # COMPOSED_OF is TIER_B and the other two are TIER_D, which is a real distinction
    # rather than an oversight: decomposing `mitravarunau` into Mitra and Varuna follows
    # from the dual form of the label, while an epithet or a group membership is a curated
    # judgement about the deity.
    for rel_type, tier in (
        ("HAS_EPITHET", QualityTier.TIER_D),
        ("MEMBER_OF", QualityTier.TIER_D),
        ("COMPOSED_OF", QualityTier.TIER_B),
    ):
        session.run(
            f"MATCH ()-[r:{rel_type}]->() SET r.quality_tier = $tier", tier=str(tier)
        )

    report.landed = session.run(
        "MATCH (dv:Devata) WHERE dv.structure IS NOT NULL RETURN count(dv) AS c"
    ).single()["c"]
    report.detail = {
        "axis_nodes": len(axes),
        "group_nodes": len(groups),
        "epithet_nodes": len(epithets),
        "has_axis_edges": session.run(
            "MATCH ()-[r:HAS_AXIS]->() RETURN count(r) AS c"
        ).single()["c"],
        "has_epithet_edges": session.run(
            "MATCH ()-[r:HAS_EPITHET]->() RETURN count(r) AS c"
        ).single()["c"],
        "member_of_edges": session.run(
            "MATCH ()-[r:MEMBER_OF]->() RETURN count(r) AS c"
        ).single()["c"],
        "composed_of_edges": session.run(
            "MATCH ()-[r:COMPOSED_OF]->() RETURN count(r) AS c"
        ).single()["c"],
    }
    return report


# ---------------------------------------------------------------------------
# Ritual structure and the Atharvavedic concern model
# ---------------------------------------------------------------------------

#: Ritual YAML key -> (relationship type, allowed object labels).
_RITUAL_EDGES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("uses_offering", "USES_OFFERING", ("Offering",)),
    ("uses_substance", "USES_SUBSTANCE", ("Substance", "Plant")),
    ("uses_object", "USES_OBJECT", ("Object",)),
    ("invokes_devata", "INVOKES_DEVATA", ("Devata",)),
    ("performed_by", "PERFORMED_BY", ("RitualRole",)),
    ("performed_for", "PERFORMED_FOR", ("HumanConcern", "Concept", "State")),
)


def load_rituals(session: Session, rituals: Sequence[dict[str, Any]]) -> LoadReport:
    """Project curated ritual structure: what a rite uses, invokes and is performed for.

    Every edge is TIER_D. That is not a hedge about the sources -- the authoring file
    cites a verse for each apparatus item -- but about what the edge asserts: "the yajna
    uses the ladle" is a statement about the rite as an institution, assembled from
    passages, and no single passage says it. The passages themselves remain reachable as
    mentions at TIER_B.
    """
    report = LoadReport(step="rituals", sent=0)
    if not rituals:
        return report

    for key, rel_type, labels in _RITUAL_EDGES:
        rows = [
            {"ritual_id": str(r["ritual_id"]), "target": target}
            for r in rituals
            for target in (r.get(key) or [])
        ]
        report.sent += len(rows)
        if not rows:
            report.detail[rel_type] = {"sent": 0, "landed": 0}
            continue
        # One write per allowed object label: an unlabelled MATCH on a shared property
        # is how 39,461 bogus edges were once produced here.
        for label in labels:
            _write(
                session,
                f"""
                UNWIND $rows AS row
                MATCH (rt:Ritual {{entity_key: row.ritual_id}})
                MATCH (t:{label} {{entity_key: row.target}})
                MERGE (rt)-[r:{rel_type}]->(t)
                ON CREATE SET r.knowledge_layer = $layer, r.quality_tier = $tier,
                              r.grade_basis = 'curated ritual structure, V2 overlay'
                """,
                rows,
                layer=str(KnowledgeLayer.L4_INTERPRETIVE_CLAIM),
                tier=str(QualityTier.TIER_D),
            )
        landed = session.run(
            f"MATCH (:Ritual)-[r:{rel_type}]->() RETURN count(r) AS c"
        ).single()["c"]
        report.landed += landed
        report.detail[rel_type] = {"sent": len(rows), "landed": landed}
    return report


#: Concern whitelist key -> (relationship type, object labels, tier).
#:
#: The tier split follows the authoring file's own strength ordering rather than treating
#: the four predicates alike. ``ADDRESSES_CONCERN`` and ``USED_FOR_RITE`` are TIER_B
#: because naming what you want is wanting it, and the rite vocabulary occurs nowhere but
#: the occasion -- the typed edge asserts no more than the mention does. ``TREATS`` and
#: ``PROTECTS_FROM`` are TIER_D because they assert a *function*: that the passage acts on
#: the affliction rather than merely naming it, which is a reading of the charm.
_CONCERN_EDGES: tuple[tuple[str, str, tuple[str, ...], QualityTier], ...] = (
    ("addresses_concern", "ADDRESSES_CONCERN", ("HumanConcern",), QualityTier.TIER_B),
    ("used_for_rite", "USED_FOR_RITE", ("SocialRite",), QualityTier.TIER_B),
    ("treats", "TREATS", ("Condition",), QualityTier.TIER_D),
    (
        "protects_from",
        "PROTECTS_FROM",
        ("Condition", "HumanConcern"),
        QualityTier.TIER_D,
    ),
)


def load_concern_predicates(
    session: Session, whitelists: dict[str, list[str]]
) -> LoadReport:
    """Type the Atharvavedic mentions the whitelist admits, and only those.

    A typed edge is derived from a mention plus membership of a curated whitelist. The
    whitelist is the whole point: it is shorter than the entity list on purpose, and an
    entity absent from every list stays a mention. Emitting a typed edge for it would be
    wrong rather than merely generous.
    """
    report = LoadReport(step="concern_predicates", sent=0)
    if not whitelists:
        return report

    for key, rel_type, labels, tier in _CONCERN_EDGES:
        keys = [str(k) for k in whitelists.get(key) or []]
        report.sent += len(keys)
        if not keys:
            report.detail[rel_type] = {"entities": 0, "edges": 0}
            continue
        for label in labels:
            session.run(
                f"""
                MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(e:{label})
                WHERE e.entity_key IN $keys
                MERGE (p)-[r:{rel_type}]->(e)
                ON CREATE SET r.knowledge_layer = $layer,
                              r.quality_tier = $tier,
                              r.derived_from_mention = m.mention_id,
                              r.grade_basis =
                                'deterministic mention, typed by curated whitelist'
                """,
                keys=keys,
                layer=str(
                    KnowledgeLayer.L2_DETERMINISTIC_DERIVED
                    if tier is QualityTier.TIER_B
                    else KnowledgeLayer.L4_INTERPRETIVE_CLAIM
                ),
                tier=str(tier),
            )
        edges = session.run(
            f"MATCH (:Passage)-[r:{rel_type}]->() RETURN count(r) AS c"
        ).single()["c"]
        report.landed += len(keys)
        report.detail[rel_type] = {
            "entities": len(keys),
            "edges": edges,
            "tier": str(tier),
        }
    return report


# ---------------------------------------------------------------------------
# Profiles, metrics, claims
# ---------------------------------------------------------------------------


def load_profiles(session: Session, profiles: Sequence[DevataProfile]) -> LoadReport:
    """Denormalise top-N profile summaries onto the Devatā node for display.

    Only summaries. The underlying counts stay in the graph, and a display property is
    never the authority for anything -- it is a cache with a short list in it, so that an
    explorer can render a deity page without twelve aggregations.
    """
    report = LoadReport(step="profiles", sent=len(profiles))
    if not profiles:
        return report
    rows = [
        {
            "entity_key": profile.entity_key,
            "profile_attributed_total": profile.total_attributed,
            "profile_attributed_per_passage": profile.attributed_per_passage,
            "profile_attributed_inherited": profile.attributed_inherited,
            "profile_per_passage_share": profile.per_passage_share,
            "profile_top_rishis": [label for label, _ in profile.top_rishis],
            "profile_top_chandas": [label for label, _ in profile.top_chandas],
            "profile_top_concepts": [label for label, _ in profile.top_concepts],
            "profile_co_devatas": [label for label, _ in profile.co_devatas],
            "profile_formula_count": profile.formula_count,
            "profile_attribution_scope": list(profile.attribution_scope),
        }
        for profile in profiles
    ]
    _write(
        session,
        "UNWIND $rows AS row MATCH (dv:Devata {entity_key: row.entity_key}) SET dv += row",
        rows,
    )
    report.landed = session.run(
        "MATCH (dv:Devata) WHERE dv.profile_attributed_total IS NOT NULL "
        "RETURN count(dv) AS c"
    ).single()["c"]
    return report


def load_metrics(session: Session, metrics: Sequence[DerivedMetric]) -> LoadReport:
    """MERGE DerivedMetric nodes and their MEASURES edges."""
    report = LoadReport(step="metrics", sent=len(metrics))
    if not metrics:
        return report
    _write(
        session,
        f"UNWIND $rows AS row "
        f"MERGE (m:{LABEL_DERIVED_METRIC} {{metric_id: row.metric_id}}) SET m += row",
        [metric.as_row() for metric in metrics],
    )
    # The subject may be a Devata, a domain entity, a Work, or the corpus pseudo-subject
    # which deliberately has no node. One write per subject kind, each label-scoped.
    #
    # An unlabelled `MATCH (s) WHERE s.entity_key = $k OR s.work_id = $k` was tried first
    # and produced 2,418 MEASURES edges from 79 metrics. Every Passage carries a
    # `work_id`, so a metric whose subject is VG:WORK:SV:KAU matched all 2,342 Samavedic
    # passages as well as the Work. Label-scoping is not an optimisation here; it is the
    # difference between one correct edge and two thousand wrong ones.
    subjects = [
        {"metric_id": metric.metric_id, "subject_key": metric.subject_key}
        for metric in metrics
    ]
    for match_clause in (
        f"MATCH (s:{LABEL_DOMAIN_ENTITY} {{entity_key: row.subject_key}})",
        "MATCH (s:Devata {entity_key: row.subject_key})",
        "MATCH (s:Work {work_id: row.subject_key})",
    ):
        _write(
            session,
            f"""
            UNWIND $rows AS row
            MATCH (m:{LABEL_DERIVED_METRIC} {{metric_id: row.metric_id}})
            {match_clause}
            MERGE (m)-[r:MEASURES]->(s)
            """,
            subjects,
        )
    session.run(
        "MATCH ()-[r:MEASURES]->() SET r.quality_tier = $tier",
        tier=str(QualityTier.TIER_B),
    )
    report.landed = session.run(
        f"MATCH (m:{LABEL_DERIVED_METRIC}) RETURN count(m) AS c"
    ).single()["c"]
    report.detail = {
        "measures_edges": session.run(
            "MATCH ()-[r:MEASURES]->() RETURN count(r) AS c"
        ).single()["c"],
        "metrics_without_subject_node": session.run(
            f"MATCH (m:{LABEL_DERIVED_METRIC}) WHERE NOT (m)-[:MEASURES]->() "
            "RETURN count(m) AS c"
        ).single()["c"],
    }
    return report


def load_claims(session: Session, claims: Sequence[InterpretiveClaim]) -> LoadReport:
    """MERGE InterpretiveClaim nodes and every edge that supports or relates one."""
    report = LoadReport(step="claims", sent=len(claims))
    if not claims:
        return report
    _write(
        session,
        f"UNWIND $rows AS row "
        f"MERGE (c:{LABEL_INTERPRETIVE_CLAIM} {{claim_id: row.claim_id}}) SET c += row",
        [claim.as_row() for claim in claims],
    )

    edge_specs: list[tuple[str, str, str, list[dict[str, Any]]]] = [
        (
            "SUPPORTED_BY",
            "MATCH (t:Passage {canonical_key: row.target})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.supported_by
            ],
        ),
        (
            "SUPPORTED_BY_STATISTIC",
            f"MATCH (t:{LABEL_DERIVED_METRIC} {{metric_id: row.target}})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.supported_by_statistic
            ],
        ),
        # Three label-scoped clauses rather than one unlabelled disjunction. The
        # unlabelled form produced 39,461 CONCERNS edges from 9 targets: `t.work_id =
        # 'VG:WORK:RV:SAK'` is true of every one of the 11,590 Rigvedic Passages, not just
        # of the Work. A claim that concerns the Rigveda does not concern each of its
        # verses individually, and an edge saying so is worse than no edge.
        (
            "CONCERNS",
            f"MATCH (t:{LABEL_DOMAIN_ENTITY} {{entity_key: row.target}})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.concerns
            ],
        ),
        (
            "CONCERNS",
            "MATCH (t:Devata {entity_key: row.target})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.concerns
            ],
        ),
        (
            "CONCERNS",
            "MATCH (t:Work {work_id: row.target})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.concerns
            ],
        ),
        (
            "CONTRADICTS",
            f"MATCH (t:{LABEL_INTERPRETIVE_CLAIM} {{claim_id: row.target}})",
            "t",
            [
                {"claim_id": c.claim_id, "target": key}
                for c in claims
                for key in c.contradicts
            ],
        ),
    ]
    landed: dict[str, int] = {}
    for rel_type, match_clause, alias, rows in edge_specs:
        if not rows:
            landed[rel_type] = 0
            continue
        _write(
            session,
            f"""
            UNWIND $rows AS row
            MATCH (c:{LABEL_INTERPRETIVE_CLAIM} {{claim_id: row.claim_id}})
            {match_clause}
            MERGE (c)-[r:{rel_type}]->({alias})
            """,
            rows,
        )
        session.run(
            f"MATCH ()-[r:{rel_type}]->() SET r.quality_tier = $tier",
            tier=str(QualityTier.TIER_D),
        )
        landed[rel_type] = session.run(
            f"MATCH (:{LABEL_INTERPRETIVE_CLAIM})-[r:{rel_type}]->() RETURN count(r) AS c"
        ).single()["c"]
        landed[f"{rel_type}_sent"] = len(rows)

    report.landed = session.run(
        f"MATCH (c:{LABEL_INTERPRETIVE_CLAIM}) RETURN count(c) AS c"
    ).single()["c"]
    report.detail = dict(sorted(landed.items()))
    return report


def summarise(reports: Sequence[LoadReport]) -> dict[str, Any]:
    return {
        "steps": [report.as_dict() for report in reports],
        "all_complete": all(report.complete for report in reports),
    }
