"""Apply the V2 domain contract to a graph built by the V1 loaders.

Four things happen here, and each is idempotent, so running this twice is the same as
running it once. That matters more than it sounds: a migration that is only correct on a
clean database is a migration nobody dares re-run, and one nobody dares re-run stops being
tested.

**Internal marking.** ``QAIssue``, ``TextVersion``, ``Translation``, ``Source`` and
``SourceArtifact`` gain :data:`~vedagraph.domain.ontology.LABEL_INTERNAL`. Nothing is
deleted -- asking the graph what it doubts about itself is genuinely useful -- but a
knowledge traversal stops returning a QA finding as a peer of Indra.

**Type projection.** The registry already knew that ``VG:CONCEPT:GO-CATTLE`` is an
``ANIMAL`` and ``VG:CONCEPT:SINDHU-RIVER`` is a ``RIVER``; the V1 projection wrote both as
``:Concept`` and dropped the distinction. Here the ``node_type`` each node already carries
becomes a real label, so ``MATCH (a:Animal)`` works.

**Grade stamping.** See :mod:`vedagraph.domain.tiers`. The subtlety is *how*: the grading
decision table is Python, and re-expressing it as a dozen hand-written Cypher ``SET``
statements would put the same policy in two places and let them drift -- which is the
failure this repository is otherwise carefully built to avoid. Instead the distinct
provenance signatures actually present in the graph are discovered first (there are a few
dozen), each is graded **once** by calling :func:`~vedagraph.domain.tiers.grade_edge`, and
one bulk update is issued per signature. One source of truth, and bulk speed.

**Display properties.** Every product node gains ``display_label`` and ``display_type``,
because a graph explorer should not have to know that a Devatā's name lives in
``preferred_label`` while a concept's lives in ``preferred_label_en`` and a formula's in
``display_form``.

Every step returns rows *sent* alongside rows *landed*. They are not the same number and
the difference is where the defects are: a projection that reports only what it sent
cannot tell a successful write from a silently unmatched one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from vedagraph.domain.ontology import (
    INTERNAL_LABELS,
    LABEL_DOMAIN_ENTITY,
    LABEL_INTERNAL,
    NULL_LABEL_SENTINELS,
    labels_for_node_type,
)
from vedagraph.domain.schema import all_domain_schema_cypher
from vedagraph.domain.tiers import LAYER_OWNED_GRADES, grade_edge


class Session(Protocol):
    """The slice of a Neo4j session this module uses."""

    def run(self, query: str, /, **kwargs: Any) -> Any: ...


@dataclass
class StepReport:
    """What one upgrade step sent and what actually landed."""

    step: str
    sent: int = 0
    landed: int = 0
    skipped: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return not self.skipped and self.sent == self.landed

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "skipped": self.skipped,
            "detail": self.detail,
        }


def apply_schema(session: Session) -> StepReport:
    """Create the V2 constraints and indexes."""
    report = StepReport(step="schema")
    for statement in all_domain_schema_cypher():
        session.run(statement)
        report.sent += 1
        report.landed += 1
    return report


def mark_internal(session: Session) -> StepReport:
    """Add the ``Internal`` marker to every non-domain label.

    The marker rather than deletion, and a marker rather than an exclusion list repeated
    in each query: one label, one filter, and a new diagnostic label added later is
    excluded by marking it here instead of by remembering to edit thirty queries.
    """
    report = StepReport(step="mark_internal")
    for label in sorted(INTERNAL_LABELS - {LABEL_INTERNAL}):
        before = session.run(
            f"MATCH (n:{label}) WHERE NOT n:{LABEL_INTERNAL} RETURN count(n) AS c"
        ).single()["c"]
        session.run(f"MATCH (n:{label}) SET n:{LABEL_INTERNAL}")
        after = session.run(
            f"MATCH (n:{label}) WHERE NOT n:{LABEL_INTERNAL} RETURN count(n) AS c"
        ).single()["c"]
        total = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
        report.sent += before
        report.landed += before - after
        report.detail[label] = {"total": total, "newly_marked": before - after}
    return report


def project_entity_types(session: Session) -> StepReport:
    """Turn each registry entity's ``node_type`` into a real Neo4j label.

    Labels cannot be parameterised in Cypher, so this groups the work by label set and
    issues one statement per distinct set. There are about twenty, which is cheaper than
    the alternatives: a per-node round trip is 89 transactions, and ``apoc.create.addLabels``
    would make the loader depend on a plugin for something the type system already knows.

    ``entity_key`` is set here rather than at creation time so that V1 artifacts do not
    have to be rebuilt to gain the uniform identity property.
    """
    report = StepReport(step="project_entity_types")
    node_types = [
        record["node_type"]
        for record in session.run(
            "MATCH (c:Concept) WHERE c.node_type IS NOT NULL "
            "RETURN DISTINCT c.node_type AS node_type ORDER BY node_type"
        )
    ]
    for node_type in node_types:
        labels = labels_for_node_type(node_type)
        clause = ":".join(labels)
        sent = session.run(
            "MATCH (c:Concept {node_type: $nt}) RETURN count(c) AS c", nt=node_type
        ).single()["c"]
        # display_type is set here, where the label is known, so that it reads "Animal"
        # rather than "ANIMAL" and matches the form used for Devatā and Ṛṣi. A UI showing
        # both spellings of a type is a UI that will group them separately.
        session.run(
            f"MATCH (c:Concept {{node_type: $nt}}) "
            f"SET c:{clause}, c.entity_key = c.concept_id, c.display_type = $dt",
            nt=node_type,
            dt=labels[0],
        )
        landed = session.run(
            f"MATCH (c:Concept {{node_type: $nt}}) WHERE c:{clause.split(':')[0]} "
            f"AND c.entity_key IS NOT NULL RETURN count(c) AS c",
            nt=node_type,
        ).single()["c"]
        report.sent += sent
        report.landed += landed
        report.detail[node_type] = {"nodes": sent, "labels": list(labels), "landed": landed}
    return report


#: Where each product label's readable name lives, and what its type should read as.
#:
#: The name is a ``coalesce`` chain, first present wins, so a V2 overlay property takes
#: precedence over the V1 field it supersedes without the V1 field being removed. The type
#: is an expression rather than a constant because ``Passage`` covers a mantra, a sūkta and
#: a maṇḍala, and calling all three "Passage" in a UI throws away the distinction the
#: corpus was built to preserve.
_DISPLAY_SOURCES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("Devata", ("label_en", "label_iast", "preferred_label"), "'Devata'"),
    # label_iast first because the two rsi registries are written in different scripts:
    # the Rigvedic one in IAST, the Yajurvedic index verbatim in Devanagari. Preferring
    # the transliteration makes one leaderboard readable instead of half of it.
    ("Rishi", ("label_iast", "preferred_label"), "'Rishi'"),
    ("Chandas", ("preferred_label",), "'Chandas'"),
    ("Formula", ("display_form", "normalized"), "'Formula'"),
    ("Lemma", ("lemma", "normalized_lemma"), "'Lemma'"),
    # canonical_citation is "RV 1.1.1": already the form a reader cites, so nothing is
    # constructed here that the corpus did not already settle.
    ("Passage", ("canonical_citation", "canonical_key"), "coalesce(n.entity_type, 'Passage')"),
    ("Work", ("work_name", "abbreviation"), "'Work'"),
)


def set_display_properties(session: Session) -> StepReport:
    """Give every product node a ``display_label`` and a ``display_type``.

    Domain entities from the registry are handled separately from Devatās and Ṛṣis,
    because for the registry the readable name is the English label with the Sanskrit in
    parentheses -- "cattle (go)" -- while for a deity the Sanskrit *is* the name.
    """
    report = StepReport(step="set_display_properties")

    sent = session.run(
        f"MATCH (n:{LABEL_DOMAIN_ENTITY}) RETURN count(n) AS c"
    ).single()["c"]
    session.run(
        f"""
        MATCH (n:{LABEL_DOMAIN_ENTITY})
        SET n.display_type = coalesce(n.display_type, n.node_type, 'DomainEntity'),
            n.display_label = CASE
                WHEN n.preferred_label_en IS NOT NULL AND n.preferred_label_sa IS NOT NULL
                    THEN n.preferred_label_en + ' (' + n.preferred_label_sa + ')'
                WHEN n.preferred_label_en IS NOT NULL THEN n.preferred_label_en
                WHEN n.preferred_label_sa IS NOT NULL THEN n.preferred_label_sa
                ELSE n.entity_key END,
            n.short_description = coalesce(n.definition, n.short_description)
        """
    )
    landed = session.run(
        f"MATCH (n:{LABEL_DOMAIN_ENTITY}) WHERE n.display_label IS NOT NULL "
        f"AND n.display_type IS NOT NULL RETURN count(n) AS c"
    ).single()["c"]
    report.sent += sent
    report.landed += landed
    report.detail[LABEL_DOMAIN_ENTITY] = {"nodes": sent, "landed": landed}

    for label, sources, type_expression in _DISPLAY_SOURCES:
        expression = "coalesce(" + ", ".join(f"n.{name}" for name in sources) + ", n.entity_key)"
        count = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
        if not count:
            report.detail[label] = {"nodes": 0, "landed": 0}
            continue
        session.run(
            f"MATCH (n:{label}) "
            f"SET n.display_label = {expression}, n.display_type = {type_expression}"
        )
        landed = session.run(
            f"MATCH (n:{label}) WHERE n.display_label IS NOT NULL RETURN count(n) AS c"
        ).single()["c"]
        report.sent += count
        report.landed += landed
        report.detail[label] = {"nodes": count, "landed": landed}
    return report


#: Provenance properties that together determine an edge's grade. Discovered as a group so
#: that one bulk update can cover every edge sharing a signature.
_SIGNATURE_FIELDS: tuple[str, ...] = (
    "trust",
    "state",
    "provenance_class",
    "scope_origin",
    # method is included because it is the only place an edge records WHICH text its
    # evidence came from, and 44.7% of concept edges turn out to rest on a translation.
    "method",
)


def _discover_signatures(session: Session) -> list[dict[str, Any]]:
    """Every distinct combination of grading-relevant properties present in the graph."""
    returns = ", ".join(f"coalesce(r.{name}, '') AS {name}" for name in _SIGNATURE_FIELDS)
    keys = ", ".join(_SIGNATURE_FIELDS)
    records = session.run(
        f"""
        MATCH ()-[r]->()
        WITH type(r) AS rel_type, {returns}
        RETURN rel_type, {keys}, count(*) AS edges
        ORDER BY edges DESC
        """
    )
    return [dict(record) for record in records]


def stamp_grades(session: Session) -> StepReport:
    """Write the unified grade onto every edge in the graph.

    One bulk update per discovered signature, with the grade computed in Python by the
    single decision table in :mod:`vedagraph.domain.tiers`.
    """
    report = StepReport(step="stamp_grades")
    signatures = _discover_signatures(session)
    per_tier: dict[str, int] = {}
    per_precision: dict[str, int] = {}
    per_evidence: dict[str, int] = {}

    skipped: dict[str, int] = {}
    for signature in signatures:
        rel_type = str(signature["rel_type"])
        edges = int(signature["edges"])
        # A layer that computes a grade the generic rules cannot derive owns it. See
        # vedagraph.domain.tiers.LAYER_OWNED_GRADES.
        if rel_type in LAYER_OWNED_GRADES:
            skipped[rel_type] = skipped.get(rel_type, 0) + edges
            continue
        properties = {
            name: signature[name] for name in _SIGNATURE_FIELDS if signature[name] != ""
        }
        grade = grade_edge(rel_type, properties)
        conditions = " AND ".join(
            f"coalesce(r.{name}, '') = ${name}" for name in _SIGNATURE_FIELDS
        )
        parameters: dict[str, Any] = {
            name: signature[name] for name in _SIGNATURE_FIELDS
        }
        parameters.update(grade.as_edge_properties())
        session.run(
            f"""
            MATCH ()-[r:{rel_type}]->()
            WHERE {conditions}
            SET r.knowledge_layer = $knowledge_layer,
                r.quality_tier = $quality_tier,
                r.attribution_precision = $attribution_precision,
                r.grade_basis = $grade_basis,
                r.evidence_basis = $evidence_basis
            """,
            **parameters,
        )
        report.sent += edges
        per_tier[str(grade.tier)] = per_tier.get(str(grade.tier), 0) + edges
        per_precision[str(grade.precision)] = per_precision.get(str(grade.precision), 0) + edges
        key = str(grade.evidence_basis)
        per_evidence[key] = per_evidence.get(key, 0) + edges

    report.landed = session.run(
        "MATCH ()-[r]->() WHERE r.quality_tier IS NOT NULL RETURN count(r) AS c"
    ).single()["c"]
    report.detail = {
        "signatures": len(signatures),
        "layer_owned_grades_skipped": skipped,
        "by_tier": dict(sorted(per_tier.items())),
        "by_precision": dict(sorted(per_precision.items())),
        "by_evidence_basis": dict(sorted(per_evidence.items())),
    }
    return report


def unknown_label_rate(session: Session) -> dict[str, Any]:
    """Share of product nodes whose ``display_label`` is missing or a null sentinel.

    The scorecard metric for whether the graph is readable. Counted over product nodes
    only: an internal node has no reader to confuse.
    """
    sentinels = sorted(NULL_LABEL_SENTINELS)
    record = session.run(
        f"""
        MATCH (n) WHERE NOT n:{LABEL_INTERNAL}
        WITH count(n) AS total,
             sum(CASE WHEN n.display_label IS NULL
                       OR trim(toString(n.display_label)) IN $sentinels
                      THEN 1 ELSE 0 END) AS unnamed
        RETURN total, unnamed
        """,
        sentinels=sentinels,
    ).single()
    total = int(record["total"])
    unnamed = int(record["unnamed"])
    return {
        "product_nodes": total,
        "without_meaningful_label": unnamed,
        "unknown_label_rate": round(unnamed / total, 6) if total else 0.0,
    }


def upgrade(session: Session) -> list[StepReport]:
    """Run every V2 upgrade step in order, returning one report each."""
    return [
        apply_schema(session),
        mark_internal(session),
        project_entity_types(session),
        set_display_properties(session),
        stamp_grades(session),
    ]


def summarise(reports: Sequence[StepReport]) -> dict[str, Any]:
    """Fold step reports into one dict, for a manifest or a report table."""
    return {
        "steps": [report.as_dict() for report in reports],
        "all_complete": all(report.complete for report in reports),
    }
