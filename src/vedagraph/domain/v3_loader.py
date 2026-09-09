"""Land the V3 layers in Neo4j, and retire what they supersede.

Four layers, one loader, because they share a discipline that has to be applied uniformly:
every write is MERGE on a deterministic key, every layer that owns edges mark-and-sweeps
its own, and every layer verifies rows-landed against rows-sent rather than reporting rows
sent as success.

The layers:

**The four-Veda theonym mention layer** (``MENTIONS_DEVATA``). Rigvedic rows come from the
manual morphological annotation by lemma identity; Samavedic, Yajurvedic and Atharvavedic
rows from adjudicated surface forms. See :mod:`vedagraph.domain.theonyms`.

**The agentive layer** (``SemanticAssertion`` + ``ActionPredicate``), derived by rule from
the same annotation: who does what, to whom, with what, for whom, in which metrical line.
See :mod:`vedagraph.enrich.agentive`.

**The sealed Rigvedic model artifact**, projected read-only with its candidate status and
receipt intact. See :mod:`vedagraph.domain.sealed_semantics`.

**The Atharvavedic ascription layer** (``DevataAscription``), which is the Atharvaveda's
deity attribution and is *not* a set of deities.

Two things this loader deliberately deletes.

``MENTIONS_ENTITY`` edges onto ``:Devata`` -- 9,000 of them -- are retired. They were
measured to be the same 9,000 facts as ``MENTIONS_LEMMA``, fact for fact: identical
per-passage counts on all 6,560 passages and an empty symmetric difference in both
directions. They are also Rigveda-only, and ``MENTIONS_DEVATA`` replaces them with a
four-Veda layer that grades its evidence and records its referent certainty. Keeping both
would leave two layers answering "does this passage name Indra?" with different numbers,
which is the defect this pass exists to remove rather than reproduce.

Orphan ``Lemma`` nodes are **not** deleted, and the reasoning is worth stating because the
opposite is tempting. 9,992 of 10,031 carry no edge, so they render as empty nodes; but
they carry a real per-lemma frequency table over the whole Rigveda, and deleting a
measurement because nothing currently points at it is how a graph loses the thing that
would have answered the next question. They are marked ``:Internal`` instead, which keeps
them out of product traversal and available to a query that asks for them by name.
"""

from __future__ import annotations

import pathlib
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

import orjson
import yaml

from vedagraph.domain.ontology import (
    DOMAIN_MODEL_VERSION,
    LABEL_ACTION_PREDICATE,
    LABEL_CONCEPT,
    LABEL_DEVATA_ASCRIPTION,
    LABEL_FORMULA,
    LABEL_FORMULA_FAMILY,
    LABEL_INTERNAL,
    LABEL_OFFERING,
    LABEL_PASSAGE,
    LABEL_RISHI,
    LABEL_RISHI_FAMILY,
    LABEL_RITUAL,
    LABEL_RITUAL_ROLE,
    LABEL_SEMANTIC_ASSERTION,
    LABEL_SOCIAL_RITE,
    REL_BELONGS_TO_FAMILY,
    REL_HAS_FORMULA,
    REL_MEMBER_OF_FAMILY,
)
from vedagraph.domain.sealed_semantics import SealedProjection
from vedagraph.enrich.agentive import (
    FRAME_ASSERTED,
    FRAME_REQUESTED,
    UNMAPPED,
    ActionVocabulary,
    AgentiveAssertion,
)

_BATCH = 2_000


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


@dataclass
class LoadReport:
    """Rows sent against rows that actually landed, per step."""

    step: str
    sent: int = 0
    landed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.landed >= self.sent

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "detail": self.detail,
        }


def _batches(rows: Sequence[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), _BATCH):
        yield list(rows[start : start + _BATCH])


def _count(session: Session, query: str, **parameters: Any) -> int:
    record = session.run(query, **parameters).single()
    return int(record["c"]) if record else 0


# ---------------------------------------------------------------------------
# Theonym mentions
# ---------------------------------------------------------------------------

_THEONYM_QUERY = """
UNWIND $rows AS row
MATCH (p:Passage {canonical_key: row.passage_key})
MATCH (d:Devata {entity_key: row.devata_id})
MERGE (p)-[m:MENTIONS_DEVATA]->(d)
SET m.mention_id = row.mention_id,
    m.veda = row.veda,
    m.extraction_path = row.extraction_path,
    m.morphological_roles = row.morphological_roles,
    m.matched_forms = row.matched_forms,
    m.occurrences = row.occurrences,
    m.referent_certainty = row.referent_certainty,
    m.referent_basis = row.referent_basis,
    m.attribution_support = row.attribution_support,
    m.attribution_precision = row.attribution_precision,
    m.evidence_basis = row.evidence_basis,
    m.quality_tier = row.quality_tier,
    m.grade_basis = row.grade_basis,
    m.domain_model_version = row.domain_model_version,
    m.trust = row.trust,
    m.method = row.method,
    m.score = row.score,
    m.evidence = row.evidence,
    m.evidence_count = row.evidence_count,
    m.state = row.state,
    m.pipeline_version = row.pipeline_version,
    m.run_id = row.run_id,
    m.knowledge_layer = CASE row.quality_tier
        WHEN 'TIER_A' THEN 'L1_SOURCE_EXPLICIT'
        ELSE 'L2_DETERMINISTIC_DERIVED' END,
    m.build_pass = $build_pass
"""
# SET, not ON CREATE SET. Every field here is computed by this layer, so preserving an
# existing value would freeze a recomputation -- the exact failure that left 28,675
# mention edges carrying a stale ambiguity flag through a rebuild that reported success.


def load_theonym_mentions(session: Session, rows: Sequence[dict[str, Any]]) -> LoadReport:
    """MERGE the theonym mention layer and retire its own stale edges."""
    report = LoadReport(step="theonym_mentions", sent=len(rows))
    if not rows:
        return report
    build_pass = uuid.uuid4().hex
    for batch in _batches(rows):
        session.run(_THEONYM_QUERY, rows=batch, build_pass=build_pass)
    retired = _count(
        session,
        """
        MATCH (:Passage)-[m:MENTIONS_DEVATA]->(:Devata)
        WHERE m.build_pass IS NULL OR m.build_pass <> $build_pass
        DELETE m RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    report.landed = _count(
        session, "MATCH (:Passage)-[m:MENTIONS_DEVATA]->(:Devata) RETURN count(m) AS c"
    )
    report.detail = {
        "retired_stale": retired,
        "by_path": {
            record["path"]: record["n"]
            for record in session.run(
                "MATCH ()-[m:MENTIONS_DEVATA]->() "
                "RETURN m.extraction_path AS path, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_tier": {
            record["tier"]: record["n"]
            for record in session.run(
                "MATCH ()-[m:MENTIONS_DEVATA]->() "
                "RETURN m.quality_tier AS tier, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_referent_basis": {
            record["b"]: record["n"]
            for record in session.run(
                "MATCH ()-[m:MENTIONS_DEVATA]->() "
                "RETURN m.referent_basis AS b, count(*) AS n ORDER BY n DESC"
            )
        },
        # Counted after the load, not derived from the rows sent. A three-way split that
        # reports itself from its own input would not notice a SET clause that never
        # reached the property -- which is the failure mode that once left 28,675 edges
        # carrying a stale ambiguity flag through a rebuild that reported success.
        "by_certainty": {
            record["c"]: record["n"]
            for record in session.run(
                "MATCH ()-[m:MENTIONS_DEVATA]->() "
                "RETURN m.referent_certainty AS c, count(*) AS n ORDER BY n DESC"
            )
        },
    }
    return report


#: The reviewed authority for componenthood, and the file whose ``review_status:
#: ACCEPTED`` rows are the only licence for a ``COMPOSED_OF`` edge.
COMPONENT_REGISTRY: Final = pathlib.Path("data") / "registry" / "devata_components.yaml"

#: Epithet-qualified deity labels resolved to the base deity they qualify.
VARIANT_REGISTRY: Final = pathlib.Path("data") / "registry" / "devata_variants.yaml"

#: Only these rows produce an edge. ``REFUSED`` and ``NOT_IN_SCOPE`` are recorded in the
#: registry so that the absence of an edge is a decision, and they must not create one.
_VARIANT_ASSERTED: Final = "ASSERTED"

#: The closed value space of ``relation`` on an ``EPITHET_VARIANT_OF`` edge, enumerated
#: rather than left open. A registry row whose ``relation`` is outside this set is a typo
#: that would otherwise land as a live edge property no consumer knows how to filter, and
#: the failure would be silent: the loader MERGEs on the endpoints, not on the relation.
#:
#: ``ORTHOGRAPHIC_VARIANT`` is the V3.2 addition and is the only one of the four that is
#: not a semantic qualification at all -- it records that two pinned entities are one
#: being under two spellings of one source label. It shares this edge rather than getting
#: its own type because every consumer uses the edge for exactly one thing, resolving a
#: node to its canonical base before counting, and that is what an orthographic variant
#: needs too. See the long note in ``devata_variants.yaml``.
_VARIANT_RELATIONS: Final = frozenset(
    {"EPITHET_QUALIFIED", "PART_OF_DEITY", "NUMBER_VARIANT", "ORTHOGRAPHIC_VARIANT"}
)


def _validate_variant_rows(rows: list[dict[str, str]]) -> None:
    """Refuse a variant registry that a one-hop resolver would silently mis-answer.

    Three checks, each for a failure that is invisible in the loaded graph rather than
    loud. An unknown ``relation`` is a typo that still produces an edge. A variant
    asserted to two different bases makes ``coalesce(base, dv)`` return whichever row the
    planner reached first, so the same query gives different answers on different runs.
    And a base that is itself an asserted variant forms a chain, which matters because
    every consumer resolves exactly **one** hop: ``natural_phenomena_personified``,
    ``deities_by_axis`` and ``deity_widest_range`` all write ``coalesce(base, dv)`` and
    none of them walks ``EPITHET_VARIANT_OF*``. A two-link chain would therefore resolve
    to the middle node and still double-count, while looking resolved.
    """
    unknown = sorted({row["relation"] for row in rows if row["relation"] not in _VARIANT_RELATIONS})
    if unknown:
        raise ValueError(
            f"devata_variants.yaml: relation values outside the closed set: {unknown}. "
            f"Permitted: {sorted(_VARIANT_RELATIONS)}."
        )

    by_variant: dict[str, set[str]] = {}
    for row in rows:
        by_variant.setdefault(row["variant_entity_id"], set()).add(row["base_entity_id"])
    forked = sorted(key for key, bases in by_variant.items() if len(bases) > 1)
    if forked:
        raise ValueError(
            f"devata_variants.yaml: these variants are ASSERTED to more than one base, "
            f"which makes one-hop resolution non-deterministic: {forked}."
        )

    bases = {row["base_entity_id"] for row in rows}
    chained = sorted(bases & set(by_variant))
    if chained:
        raise ValueError(
            f"devata_variants.yaml: these keys are both an asserted variant and an "
            f"asserted base, forming a resolution chain that every consumer's one-hop "
            f"coalesce would leave half-resolved: {chained}."
        )


_VARIANT_QUERY: Final = """
UNWIND $rows AS row
MATCH (v:Devata {entity_key: row.variant_entity_id})
MATCH (b:Devata {entity_key: row.base_entity_id})
MERGE (v)-[r:EPITHET_VARIANT_OF]->(b)
SET r.relation = row.relation,
    r.evidence = row.evidence,
    r.grade_basis = row.grade_basis,
    r.quality_tier = 'TIER_C',
    r.knowledge_layer = 'L3_LLM_EXTRACTED',
    r.evidence_basis = 'SANSKRIT',
    r.attribution_precision = 'NOT_AN_ATTRIBUTION',
    r.method = 'devata-variant-registry-v1',
    r.review_state = 'UNREVIEWED',
    r.domain_model_version = $model_version,
    r.build_pass = $build_pass
"""


def load_devata_variants(session: Session, project_root: pathlib.Path) -> LoadReport:
    """Link epithet-qualified deity labels to the base deity, from the stated registry.

    ``QUESTION_UNLOCKED = Q86`` (which natural phenomena are personified as deities;
    currently graded MISLEADING). **The defect, measured.** ``DEVATA_ASSOCIATED_WITH``
    reports "fire (agni)" with five personifications -- ``Agni``, ``Agni Jātavedas``,
    ``Agni Pavamāna``, ``Agni the slayer of demons`` and ``the self of Agni`` -- because the
    Anukramaṇī's devatā slot records the *qualified* label a hymn uses, the registry
    correctly pins each distinct slot value as its own entity, and nothing then said that
    four of the five are one god. A count of personifications was counting labels. The
    benchmark criterion names this failure in terms.

    **Why a new relationship type rather than reusing one.** ``COMPOSED_OF`` is the wrong
    relation and asserting it here would be a real error: ``jātavedā agniḥ`` is not made
    *of* Agni the way ``mitrāvaruṇau`` is made of Mitra and Varuṇa, and a consumer walking
    ``COMPOSED_OF`` to enumerate a compound's members would start returning Agni as a
    member of himself. ``HAS_EPITHET`` is also wrong: it points at an ``:Epithet`` node,
    and these are ``:Devata`` nodes with attributions, mentions and axes of their own that
    must not be collapsed into an epithet string.

    **Nothing is merged.** The variant keeps its own identity, its own attributions and its
    own mentions -- ``VG:DEVATA:PAVAMANAH-SOMAH`` carries 1,087 Anukramaṇī attributions
    against Soma's 80, and collapsing the two would destroy the maṇḍala 9 signal. The edge
    only lets a query that must not double-count resolve to the base first.

    **Graded for what it is.** ``TIER_C`` / ``L3_LLM_EXTRACTED``, because no human has
    reviewed the registry. The three ``REFUSED`` rows -- ``sāvitrī sūryā``, which is a
    different figure and not Sūrya under an epithet; ``ahirbudhnyaḥ``; and ``pavamānaḥ``
    alone, refused on the evidence rule rather than on the reading -- create nothing, which
    is why they are in the file: a shared substring is not identity, and the refusals are
    the record that stops someone acting on one.
    """
    report = LoadReport(step="devata_variants")
    document = yaml.safe_load((project_root / VARIANT_REGISTRY).read_text(encoding="utf-8"))
    all_rows = list((document or {}).get("variants", []))
    asserted = [
        {
            "variant_entity_id": str(row["variant_entity_id"]),
            "base_entity_id": str(row["base_entity_id"]),
            "relation": str(row["relation"]),
            "evidence": " ".join(str(row["evidence"]).split()),
            "grade_basis": (
                "devata_variants.yaml states this qualified label resolves to this base "
                "deity, on the evidence of the source label alone"
            ),
        }
        for row in all_rows
        if str(row.get("review_status")) == _VARIANT_ASSERTED
    ]
    _validate_variant_rows(asserted)
    report.sent = len(asserted)
    if not asserted:
        return report
    build_pass = uuid.uuid4().hex
    session.run(
        _VARIANT_QUERY,
        rows=asserted,
        build_pass=build_pass,
        model_version=DOMAIN_MODEL_VERSION,
    )
    # Sweep by build_pass, so a row downgraded from ASSERTED to REFUSED in the registry
    # loses its edge on the next run. MERGE alone never forgets a superseded value, and a
    # refusal that leaves its edge behind is worse than never having recorded it.
    retired = _count(
        session,
        """
        MATCH (:Devata)-[r:EPITHET_VARIANT_OF]->(:Devata)
        WHERE r.build_pass IS NULL OR r.build_pass <> $build_pass
        DELETE r RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    report.landed = _count(
        session,
        """
        MATCH (:Devata)-[r:EPITHET_VARIANT_OF]->(:Devata)
        WHERE r.build_pass = $build_pass
        RETURN count(r) AS c
        """,
        build_pass=build_pass,
    )
    report.detail = {
        "retired_stale": retired,
        "by_relation": {
            record["rel"]: record["n"]
            for record in session.run(
                "MATCH ()-[r:EPITHET_VARIANT_OF]->() "
                "RETURN r.relation AS rel, count(*) AS n ORDER BY n DESC"
            )
        },
        "registry_rows": len(all_rows),
        "not_asserted": {
            str(row["variant_entity_id"]): str(row.get("review_status"))
            for row in all_rows
            if str(row.get("review_status")) != _VARIANT_ASSERTED
        },
        # The number Q86 turns on: how many distinct *base* deities the inflated
        # personification classes collapse to once variants resolve.
        "personifications_before_and_after": [
            {
                "phenomenon": record["phenomenon"],
                "labels": record["labels"],
                "distinct_bases": record["bases"],
            }
            for record in session.run(
                """
                MATCH (dv:Devata)-[:DEVATA_ASSOCIATED_WITH]->(c)
                OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
                WITH c, dv, coalesce(base, dv) AS resolved
                WITH coalesce(c.display_label, c.concept_id) AS phenomenon,
                     count(DISTINCT dv) AS labels,
                     count(DISTINCT resolved) AS bases
                WHERE labels > bases
                RETURN phenomenon, labels, bases ORDER BY labels DESC
                """
            )
        ],
    }
    return report


def _accepted_components(project_root: pathlib.Path) -> dict[str, list[str]]:
    """Composite -> components, for ``ACCEPTED`` rows of the component registry only."""
    document = yaml.safe_load((project_root / COMPONENT_REGISTRY).read_text(encoding="utf-8"))
    return {
        str(row["composite_entity_id"]): [str(k) for k in row.get("component_entity_ids") or []]
        for row in (document or {}).get("components", [])
        if str(row.get("review_status")) == "ACCEPTED"
    }


def reconcile_devata_composition(
    session: Session, project_root: pathlib.Path | None = None
) -> LoadReport:
    """Make ``Devata.is_composite`` agree with the reviewed decomposition in the graph.

    **The contradiction this resolves, measured.** 14 ``:Devata`` nodes carry
    ``COMPOSED_OF`` edges projected from the ``review_status: ACCEPTED`` rows of
    ``data/registry/devata_components.yaml``, which the taxonomy overlay names as "the
    reviewed authority for componenthood". Every one of those 14 nodes also carried
    ``is_composite = false``, and so did the other 200: **0 of 214 deities were flagged
    composite while 14 were decomposed.** So the graph simultaneously stated that
    ``VG:DEVATA:MITRAVARUNAU`` is Mitra and Varuṇa and that it is not a compound, and the
    navigation question "which deities are compounds?" returned nothing at all.

    The cause is that ``is_composite`` comes from ``is_composite_label``, a deliberate
    label-shape heuristic that looks for the source editors' hyphen and documents that it
    will *not* recognise a dual such as ``mitrāvaruṇau`` because doing so needs morphology.
    That restraint is right for a label heuristic and wrong as the final value of the
    property, because a reviewed decomposition is exactly the evidence the heuristic said
    it was waiting for. This step therefore derives the flag from the reviewed edges rather
    than from the spelling.

    **The flag is written on every deity, not only on the composites.** A ``false`` here
    means "no ACCEPTED decomposition exists for this deity", which is a decision the
    registry records -- ``VG:DEVATA:VISVEDEVAH`` is ``REJECTED`` and
    ``VG:DEVATA:DYAVAPRTHIVYAU`` is ``NEEDS_REVIEW`` -- and leaving the property absent
    would make the decision look like an oversight. ``component_count`` is landed beside it
    so a consumer never has to trust the boolean alone.

    **It also diffs the graph against the registry, because the two can diverge and did.**
    ``COMPOSED_OF`` is not projected from ``data/registry/devata_components.yaml`` -- the
    file the taxonomy overlay itself names as "the reviewed authority for componenthood".
    It is projected from a *second* copy of the same data, the ``composed_of`` field of
    ``data/domain/vedagraph_domain_v2/devata_taxonomy.yaml``, which the overlay maintains by
    hand. Two files holding one fact means a row can be added to the authority and never
    reach the graph, with every loader reporting success. So the delta is measured here and
    named in ``registry_only`` / ``graph_only`` rather than left to be discovered later.

    Nothing is inferred and nothing new is decomposed: the flag reads ``COMPOSED_OF``, and
    the diff reads the registry without writing from it -- an ACCEPTED row this step found
    missing is reported for review, never MERGEd, because creating the edge here would make
    this loader a second decomposition authority and there are already two too many.
    """
    report = LoadReport(step="devata_composition")
    report.sent = _count(session, "MATCH (dv:Devata) RETURN count(dv) AS c")
    session.run(
        """
        MATCH (dv:Devata)
        OPTIONAL MATCH (dv)-[:COMPOSED_OF]->(part:Devata)
        WITH dv, count(part) AS components
        SET dv.component_count = components,
            dv.is_composite = components > 0
        """
    )
    report.landed = _count(
        session, "MATCH (dv:Devata) WHERE dv.component_count IS NOT NULL RETURN count(dv) AS c"
    )
    composite = _count(session, "MATCH (dv:Devata) WHERE dv.is_composite RETURN count(dv) AS c")
    decomposed = _count(
        session, "MATCH (dv:Devata) WHERE (dv)-[:COMPOSED_OF]->() RETURN count(DISTINCT dv) AS c"
    )
    report.detail = {
        "flagged_composite": composite,
        "with_composed_of_edges": decomposed,
        # These two must be equal. They are reported rather than asserted because a
        # loader's job here is to make the discrepancy visible, and the discrepancy this
        # step was written for was 0 against 14.
        "agrees": composite == decomposed,
        "contradictions_before": _count(
            session,
            """
            MATCH (dv:Devata)-[:COMPOSED_OF]->(:Devata)
            WHERE dv.is_composite = false
            RETURN count(DISTINCT dv) AS c
            """,
        ),
        "undecomposed_pair_or_group": _count(
            session,
            """
            MATCH (dv:Devata)
            WHERE dv.structure IN ['PAIR', 'GROUP'] AND NOT (dv)-[:COMPOSED_OF]->()
            RETURN count(dv) AS c
            """,
        ),
    }
    if project_root is not None:
        accepted = _accepted_components(project_root)
        in_graph = {
            str(record["k"]): sorted(str(part) for part in record["parts"])
            for record in session.run(
                """
                MATCH (whole:Devata)-[:COMPOSED_OF]->(part:Devata)
                RETURN whole.entity_key AS k, collect(part.entity_key) AS parts
                """
            )
        }
        report.detail["registry_diff"] = {
            "accepted_rows": len(accepted),
            "composites_in_graph": len(in_graph),
            "registry_only": sorted(set(accepted) - set(in_graph)),
            "graph_only": sorted(set(in_graph) - set(accepted)),
            "component_set_differs": sorted(
                key
                for key in set(accepted) & set(in_graph)
                if sorted(accepted[key]) != in_graph[key]
            ),
        }
    return report


def retire_superseded_devata_mentions(session: Session) -> LoadReport:
    """Delete ``MENTIONS_ENTITY`` edges onto ``:Devata``, superseded by ``MENTIONS_DEVATA``.

    Measured before deleting, and the measurement is the justification: these edges are
    Rigveda-only and duplicate ``MENTIONS_LEMMA`` fact for fact. The replacement covers
    four Vedas, grades its evidence, and records whether the occurrence certainly denotes
    the deity. Two layers answering one question with different numbers is worse than
    either layer alone.
    """
    report = LoadReport(step="retire_superseded_devata_mentions")
    before = _count(session, "MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:Devata) RETURN count(m) AS c")
    report.sent = before
    if not before:
        return report
    overlap = _count(
        session,
        """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:Devata)
        WHERE (p)-[:MENTIONS_DEVATA]->(:Devata)
        RETURN count(DISTINCT p) AS c
        """,
    )
    session.run("MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:Devata) DELETE m")
    after = _count(session, "MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:Devata) RETURN count(m) AS c")
    report.landed = before - after
    report.detail = {
        "deleted": before - after,
        "remaining": after,
        "passages_also_reached_by_the_replacement": overlap,
    }
    return report


def mark_orphan_lemmas_internal(session: Session) -> LoadReport:
    """Move ALL ``Lemma`` nodes out of product traversal without destroying them.

    The original implementation only marked edgeless (orphan) Lemma nodes as Internal,
    leaving the 39 deity Lemma nodes that carry MENTIONS_LEMMA edges in product traversal.
    That contradicted the stated intent in the module docstring: the whole Lemma layer is a
    research/internal layer now that MENTIONS_DEVATA supersedes it as the product-facing
    deity-mention layer. Deity lemmas (agni-, indra-, etc.) appearing as product nodes also
    creates a misleading impression — they look like Devata nodes but lack the full profile.
    """
    report = LoadReport(step="mark_orphan_lemmas_internal")
    to_mark = _count(
        session,
        f"MATCH (l:Lemma) WHERE NOT l:{LABEL_INTERNAL} RETURN count(l) AS c",
    )
    report.sent = to_mark
    if to_mark:
        session.run(f"MATCH (l:Lemma) WHERE NOT l:{LABEL_INTERNAL} SET l:{LABEL_INTERNAL}")
    report.landed = to_mark - _count(
        session,
        f"MATCH (l:Lemma) WHERE NOT l:{LABEL_INTERNAL} RETURN count(l) AS c",
    )
    report.detail = {
        "marked_internal": report.landed,
        "lemmas_still_in_product": _count(
            session, f"MATCH (l:Lemma) WHERE NOT l:{LABEL_INTERNAL} RETURN count(l) AS c"
        ),
    }
    return report


# ---------------------------------------------------------------------------
# Action predicates and the agentive assertion layer
# ---------------------------------------------------------------------------


def load_action_predicates(session: Session, vocabulary: ActionVocabulary) -> LoadReport:
    """MERGE one node per member of the closed action vocabulary.

    ``UNMAPPED_ROOT`` gets a node too. A root the registry does not cover produces an
    assertion rather than silence, so the gap is countable in the graph instead of being
    visible only in the registry.
    """
    rows = [
        {
            "predicate": predicate,
            "display_label": predicate,
            "argument_frame": list(vocabulary.argument_frames.get(predicate, ())),
            "root_count": sum(1 for m in vocabulary.by_label.values() if m.predicate == predicate),
            "root_tokens": sum(
                m.tokens for m in vocabulary.by_label.values() if m.predicate == predicate
            ),
        }
        for predicate in sorted(vocabulary.predicates)
    ]
    rows.append(
        {
            "predicate": UNMAPPED,
            "display_label": "unmapped verbal root",
            "argument_frame": [],
            "root_count": 0,
            "root_tokens": 0,
        }
    )
    report = LoadReport(step="action_predicates", sent=len(rows))
    session.run(
        f"""
        UNWIND $rows AS row
        MERGE (a:{LABEL_ACTION_PREDICATE} {{predicate: row.predicate}})
        SET a.display_label = row.display_label,
            a.display_type = 'ActionPredicate',
            a.argument_frame = row.argument_frame,
            a.root_count = row.root_count,
            a.root_tokens = row.root_tokens,
            a.vocabulary_version = $version
        """,
        rows=rows,
        version="vedagraph-action-predicates-v1",
    )
    report.landed = _count(session, f"MATCH (a:{LABEL_ACTION_PREDICATE}) RETURN count(a) AS c")
    report.detail = {
        "predicates_with_no_root": list(vocabulary.unused_predicates),
        "roots_mapped": len(vocabulary.by_label),
    }
    return report


_AGENTIVE_QUERY = f"""
UNWIND $rows AS row
MATCH (p:Passage {{canonical_key: row.passage_key}})
MATCH (d:Devata {{entity_key: row.devata_id}})
MATCH (a:{LABEL_ACTION_PREDICATE} {{predicate: row.predicate}})
MERGE (s:{LABEL_SEMANTIC_ASSERTION} {{assertion_id: row.assertion_id}})
SET s += row.properties
MERGE (p)-[:HAS_SEMANTIC_ASSERTION]->(s)
MERGE (s)-[:ASSERTION_AGENT]->(d)
MERGE (s)-[:ASSERTION_PREDICATE]->(a)
WITH s, row
SET s.build_pass = $build_pass
"""


def load_agentive(session: Session, assertions: Sequence[AgentiveAssertion]) -> LoadReport:
    """MERGE the agentive assertion layer, then rebuild its one-hop aggregates."""
    report = LoadReport(step="agentive_assertions", sent=len(assertions))
    if not assertions:
        return report
    build_pass = uuid.uuid4().hex
    rows = []
    for assertion in assertions:
        row = assertion.as_row()
        rows.append(
            {
                "assertion_id": row["assertion_id"],
                "passage_key": row["passage_key"],
                "devata_id": row["devata_id"],
                "predicate": row["predicate"],
                "properties": {
                    key: value
                    for key, value in row.items()
                    if key not in {"roles", "evidence"} and not isinstance(value, (dict, list))
                }
                | {
                    "display_label": (
                        f"{row['devata_id'].removeprefix('VG:DEVATA:')} "
                        f"{row['predicate']} ({row['frame'].lower()})"
                    ),
                    "display_type": "SemanticAssertion",
                    "derivation": "MORPHOLOGY_RULE",
                    "review_state": "UNREVIEWED",
                    # Graded here, on the node, because it was graded nowhere: all 2,406
                    # of these carried no `quality_tier` and no `evidence_basis` at all,
                    # so a reader filtering the assertion layer by tier got them whatever
                    # they asked for. TIER_B is the right grade and not a courtesy: the
                    # assertion is produced by a fixed rule over the University of Zurich
                    # *manual scholarly* morphological annotation, so it is derived from
                    # something a source states and is recomputable from it. The rule is
                    # not a model and read no translation, which is why the basis is
                    # SANSKRIT rather than TRANSLATION -- the distinction that separates
                    # this half of the label from the model-extracted half.
                    "quality_tier": "TIER_B",
                    "evidence_basis": "SANSKRIT",
                    "attribution_precision": "PER_PASSAGE",
                    "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                    "grade_basis": (
                        "applied by rule to the Zurich manual morphological annotation; "
                        "recomputable from the annotation"
                    ),
                    "evidence": row["evidence"],
                    "roles_json": _roles_json(row["roles"]),
                    "preverbs": row["preverbs"],
                    "morphological_roles_present": [filler["role"] for filler in row["roles"]],
                },
            }
        )
    for batch in _batches(rows):
        session.run(_AGENTIVE_QUERY, rows=batch, build_pass=build_pass)

    retired = _count(
        session,
        f"""
        MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{derivation: 'MORPHOLOGY_RULE'}})
        WHERE s.build_pass IS NULL OR s.build_pass <> $build_pass
        DETACH DELETE s RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    report.landed = _count(
        session,
        f"MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{derivation: 'MORPHOLOGY_RULE'}}) "
        "RETURN count(s) AS c",
    )
    report.detail = {
        "retired_stale": retired,
        "aggregates": _rebuild_action_aggregates(session),
    }
    return report


def _roles_json(roles: Sequence[dict[str, str]]) -> str:
    import json

    return json.dumps(list(roles), ensure_ascii=False)


#: Node label -> the incoming edge whose per-Veda spread defines that node's scope.
#:
#: Every entry is a layer where **a zero is ambiguous**: it can mean "this corpus does not
#: do this" or "this corpus has no such annotation", and those are opposite conclusions.
#: The Rigveda carries a manual scholarly morphological annotation the other three Vedas
#: do not, so any layer derived from it is Rigveda-only as a matter of *source coverage*,
#: not of Vedic practice -- and a reader who reads `Gayatri: SV 0` as "the Samaveda does
#: not use the gayatri metre" has been misled by the graph rather than by the text.
#:
#: ``Devata`` is absent on purpose: it already carries ``attribution_scope`` and
#: ``attribution_scope_note`` written by the taxonomy overlay, and that property is
#: specifically about the Anukramani ascription rather than about every route to a deity.
#: Writing a second, similar-sounding scope onto it would leave two properties to keep in
#: step.
_SCOPE_SOURCES: Final[tuple[tuple[str, str], ...]] = (
    ("Chandas", "HAS_CHANDAS"),
    ("Rishi", "HAS_RISHI"),
    ("DevataAscription", "HAS_DEVATA_ASCRIPTION"),
    (LABEL_SEMANTIC_ASSERTION, "HAS_SEMANTIC_ASSERTION"),
)


def stamp_layer_veda_scope(session: Session) -> LoadReport:
    """Record, on each node, which Vedas its layer actually reaches.

    **Measured from the graph, never declared.** An earlier hard-coded scope note is
    exactly how this class of defect persists: the note in the query catalogue said
    ``HAS_RISHI`` and ``HAS_CHANDAS`` had zero non-Rigvedic edges, and by the time it was
    read that was false by 7,324 and 5,797 edges respectively -- so the graph was telling
    researchers a question was unanswerable while holding the answer. Computing the scope
    from the edges means it cannot drift behind the data: acquire an Atharvavedic metre
    layer and the note updates itself on the next build.

    ``ActionPredicate`` is handled separately below because it is two hops from a passage.
    """
    report = LoadReport(step="layer_veda_scope")
    note = (
        "Vedas this layer actually reaches, measured from the graph. A Veda absent here "
        "means the layer has no coverage of that corpus -- NOT that the corpus lacks the "
        "thing. Layers derived from the Zurich manual morphological annotation are "
        "Rigveda-only because only the Rigveda is annotated."
    )
    for label, rel in _SCOPE_SOURCES:
        landed = _count(
            session,
            f"""
            MATCH (n:{label})
            OPTIONAL MATCH (p:Passage)-[:{rel}]->(n)
            WITH n, [v IN collect(DISTINCT p.veda) WHERE v IS NOT NULL] AS vedas
            SET n.layer_veda_scope = vedas,
                n.layer_veda_scope_note = $note,
                n.layer_veda_scope_source = $rel
            RETURN count(n) AS c
            """,
            note=note,
            rel=rel,
        )
        report.sent += landed
        report.landed += landed
        report.detail[label] = landed

    # Two hops: a predicate is reached from a passage only through an assertion, so the
    # single-pattern form above cannot express it.
    predicates = _count(
        session,
        f"""
        MATCH (a:{LABEL_ACTION_PREDICATE})
        OPTIONAL MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->
                       (:{LABEL_SEMANTIC_ASSERTION})-[:ASSERTION_PREDICATE]->(a)
        WITH a, [v IN collect(DISTINCT p.veda) WHERE v IS NOT NULL] AS vedas
        SET a.layer_veda_scope = vedas,
            a.layer_veda_scope_note = $note,
            a.layer_veda_scope_source = 'ASSERTION_PREDICATE'
        RETURN count(a) AS c
        """,
        note=note,
    )
    report.sent += predicates
    report.landed += predicates
    report.detail[LABEL_ACTION_PREDICATE] = predicates
    report.detail["distinct_scopes"] = {
        str(record["s"]): record["n"]
        for record in session.run(
            "MATCH (n) WHERE n.layer_veda_scope IS NOT NULL "
            "RETURN n.layer_veda_scope AS s, count(*) AS n ORDER BY n DESC"
        )
    }
    return report


#: The ``ABOUT_CONCEPT`` method string that rests on the stored English translation alone.
#:
#: The concept layer writes four method strings: ``:english``, ``:sanskrit-token``,
#: ``:sanskrit-sandhi`` and ``:english+sanskrit-token``. Only the first is translation-only;
#: the fourth is the corroborated case, where an alias matched in *both* the Sanskrit and
#: the translation independently.
_TRANSLATION_ONLY_ABOUTNESS: Final = "concept-alias-v1:english"


def reconcile_about_concept(session: Session) -> LoadReport:
    """Retire aboutness claims that rest only on a nineteenth-century English translation.

    ``ABOUT_CONCEPT`` is supposed to mean *this passage is substantively about this
    concept*, which is a stronger claim than ``MENTIONS_ENTITY``'s *this passage names
    it*. The V3 brief is explicit that the edge must not exist merely because an English
    translation contains one keyword -- and 21,539 of 47,976 edges were exactly that: a
    single word matched in Griffith's 1896 prose, with nothing in the Sanskrit.

    Why that is worse than thin. Griffith translates freely and repeats his own English
    vocabulary across unrelated verses, so a translation-only aboutness edge measures *his
    word choice*, not the passage. It also made the layer look independent of the mention
    layer when it is not: with the translation-only edges gone, every surviving edge is
    corroborated by a Sanskrit-grounded mention of the same entity, which is the honest
    description of what this layer is -- a *salience ranking over the mention layer*,
    capped at four per passage, not a second opinion about it.

    What is deliberately kept. ``:english+sanskrit-token`` survives, because two paths
    firing independently is corroboration rather than a translation artefact, and the
    evidence basis records it as ``MIXED`` so a reader can still exclude anything a
    translation touched. Sanskrit-only and Sanskrit-sandhi survive unconditionally.
    Retiring the whole English path instead -- including the corroborated half -- would
    discard 13,081 edges whose Sanskrit evidence is exactly as good as the rest.

    Like every other retirement in this module it is measured, not assumed: the report
    carries the before count, the after count, the per-method survival table, and the
    share of survivors corroborated by a mention.
    """
    report = LoadReport(step="about_concept_reconciliation")
    before = _count(session, "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN count(r) AS c")
    if not before:
        return report

    # `sent` is what this step intends to *retire*, not the size of the layer, and
    # `landed` is what it actually retired. A retirement step whose `sent` was the layer
    # size reported itself incomplete every time it succeeded -- landed is necessarily
    # smaller than the layer -- which would teach a reader to ignore the flag.
    report.sent = _count(
        session,
        "MATCH ()-[r:ABOUT_CONCEPT]->() WHERE r.method = $method RETURN count(r) AS c",
        method=_TRANSLATION_ONLY_ABOUTNESS,
    )

    retired = _count(
        session,
        """
        MATCH (:Passage)-[r:ABOUT_CONCEPT]->()
        WHERE r.method = $method
        DELETE r
        RETURN count(*) AS c
        """,
        method=_TRANSLATION_ONLY_ABOUTNESS,
    )
    after = _count(session, "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN count(r) AS c")
    report.landed = retired

    corroborated = _count(
        session,
        """
        MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c)
        WHERE (p)-[:MENTIONS_ENTITY]->(c)
        RETURN count(*) AS c
        """,
    )
    report.detail = {
        "edges_before": before,
        "edges_after": after,
        "retired_translation_only": retired,
        "surviving_by_method": {
            record["m"]: record["n"]
            for record in session.run(
                "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN r.method AS m, count(*) AS n ORDER BY n DESC"
            )
        },
        "corroborated_by_a_mention": corroborated,
        # Not zero, and the residue is not a defect. Measured: the survivors that carry no
        # matching MENTIONS_ENTITY are ~97% `sanskrit-token`, aimed overwhelmingly at
        # NaturalPhenomenon and Substance entities -- so they are Sanskrit-grounded, and
        # what they lack is agreement from the *other* lexicon. The two layers read
        # different files: aboutness comes from the 91 entities of `concepts.yaml` under
        # the frozen semantic whitelist, while mentions come from the 227-entity merged
        # domain registry, which carries its own stricter alias-suppression list. An alias
        # the domain layer suppresses and the concept layer does not produces exactly this
        # shape. Reported per-method so the asymmetry stays visible instead of being
        # rounded to "100% corroborated", which is what a previous pass claimed.
        "uncorroborated": after - corroborated,
        "uncorroborated_by_method": {
            record["m"]: record["n"]
            for record in session.run(
                "MATCH (p:Passage)-[r:ABOUT_CONCEPT]->(c) "
                "WHERE NOT (p)-[:MENTIONS_ENTITY]->(c) "
                "RETURN r.method AS m, count(*) AS n ORDER BY n DESC"
            )
        },
        "translation_only_remaining": _count(
            session,
            "MATCH ()-[r:ABOUT_CONCEPT]->() WHERE r.method = $method RETURN count(r) AS c",
            method=_TRANSLATION_ONLY_ABOUTNESS,
        ),
    }
    return report


def reconcile_assertion_edge_grades(session: Session) -> LoadReport:
    """Make ``HAS_SEMANTIC_ASSERTION`` carry the grade of the assertion it points at.

    The ``:SemanticAssertion`` label holds two layers that are not comparable, and the
    edge into them was flattening the difference. 2,406 assertions are derived by rule
    from a manual scholarly morphological annotation (TIER_B, SANSKRIT); 2,459 are
    unreviewed model extractions, most of them over the stored **English translation**
    (TIER_D, TRANSLATION). Every ``HAS_SEMANTIC_ASSERTION`` edge into both was stamped
    ``TIER_B`` / ``STRUCTURAL``, on the reasoning that "this passage has this assertion"
    is a structural fact about the graph.

    That reasoning is defensible about the *edge* and catastrophic in *use*, because the
    documented way to exclude model output from a result is to filter ``quality_tier`` --
    and with a uniform TIER_B on the edge, that filter returned Griffith paraphrase
    alongside Zurich morphology with no way to tell them apart. An adversarial pass found
    it by asking for TIER_B and getting ``"bright shining among the Bharadvajas"`` back.

    So the edge inherits its target's tier and basis. The traversal reads the same either
    way; the filter now means what the documentation says it means. ``derivation`` is
    copied onto the edge as well, so the two layers are separable in one hop without
    having to reach the node.
    """
    report = LoadReport(step="assertion_edge_grades")
    report.sent = _count(
        session,
        f"MATCH (:Passage)-[r:HAS_SEMANTIC_ASSERTION]->(:{LABEL_SEMANTIC_ASSERTION}) "
        "RETURN count(r) AS c",
    )
    if not report.sent:
        return report
    session.run(
        f"""
        MATCH (:Passage)-[r:HAS_SEMANTIC_ASSERTION]->(s:{LABEL_SEMANTIC_ASSERTION})
        SET r.quality_tier = coalesce(s.quality_tier, 'TIER_D'),
            r.evidence_basis = coalesce(s.evidence_basis, 'MODEL_INTERPRETATION'),
            r.derivation = s.derivation,
            r.review_state = s.review_state,
            r.attribution_precision = 'PER_PASSAGE',
            r.grade_basis =
              'inherited from the assertion this edge points at; the label carries two '
              + 'layers of unequal strength and the edge must not flatten them'
        """
    )
    report.landed = _count(
        session,
        f"MATCH (:Passage)-[r:HAS_SEMANTIC_ASSERTION]->(:{LABEL_SEMANTIC_ASSERTION}) "
        "WHERE r.quality_tier IS NOT NULL AND r.derivation IS NOT NULL "
        "RETURN count(r) AS c",
    )
    report.detail = {
        "by_derivation_and_tier": {
            f"{record['d']}/{record['t']}": record["n"]
            for record in session.run(
                "MATCH (:Passage)-[r:HAS_SEMANTIC_ASSERTION]->() "
                "RETURN r.derivation AS d, r.quality_tier AS t, count(*) AS n "
                "ORDER BY n DESC"
            )
        },
        "assertion_nodes_ungraded": _count(
            session,
            f"MATCH (s:{LABEL_SEMANTIC_ASSERTION}) WHERE s.quality_tier IS NULL "
            "RETURN count(s) AS c",
        ),
    }
    return report


def _rebuild_action_aggregates(session: Session) -> dict[str, int]:
    """Rebuild ``PERFORMS_ACTION`` and ``IS_ASKED_TO`` from the assertion nodes.

    Derived, never authored: the aggregate exists so that "which actions does Indra
    perform" is one hop instead of two, and rebuilding it from the assertions is what
    stops it drifting from them. Deleted and recomputed rather than MERGEd, because a
    count is not idempotent under MERGE -- an aggregate that kept a stale
    ``assertion_count`` would be worse than no aggregate.
    """
    session.run("MATCH ()-[r:PERFORMS_ACTION]->() DELETE r")
    session.run("MATCH ()-[r:IS_ASKED_TO]->() DELETE r")
    counts: dict[str, int] = {}
    for frame, predicate in ((FRAME_ASSERTED, "PERFORMS_ACTION"), (FRAME_REQUESTED, "IS_ASKED_TO")):
        counts[predicate] = _count(
            session,
            f"""
            MATCH (d:Devata)<-[:ASSERTION_AGENT]-(s:{LABEL_SEMANTIC_ASSERTION})
                  -[:ASSERTION_PREDICATE]->(a:{LABEL_ACTION_PREDICATE})
            WHERE s.frame = $frame
            WITH d, a, count(s) AS assertions,
                 count(DISTINCT s.passage_key) AS passages,
                 collect(DISTINCT s.root_label)[0..8] AS roots
            MERGE (d)-[r:{predicate}]->(a)
            SET r.assertion_count = assertions,
                r.passage_count = passages,
                r.roots = roots,
                r.frame = $frame,
                r.quality_tier = 'TIER_B',
                r.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
                r.attribution_precision = 'NOT_AN_ATTRIBUTION',
                r.evidence_basis = 'SANSKRIT',
                r.grade_basis =
                  'aggregated from evidence-bound agentive assertions over the ' +
                  'University of Zurich morphological annotation'
            RETURN count(r) AS c
            """,
            frame=frame,
        )
    return counts


# ---------------------------------------------------------------------------
# The sealed model artifact
# ---------------------------------------------------------------------------

# MERGE on ``assertion_node_id``, not on ``assertion_id``, and the distinction is not
# cosmetic. A sealed assertion has two identifiers: the run's own ``assertion_id``
# (``C32A:VG:SEMOBJ:...``) and this projection's derived node id. The first version merged
# on ``assertion_id`` and then ran ``SET s += row.properties``, which **overwrote the merge
# key** with the run's id. Two failures followed from that one line: the entity-link pass
# looked the node up by node id and found nothing, so all 902 agent and target links
# silently failed; and the next run's MERGE matched nothing either, created 2,459 fresh
# nodes and swept the 2,459 previous ones, reporting a full load both times.
_SEALED_QUERY = f"""
UNWIND $rows AS row
MATCH (p:Passage {{canonical_key: row.passage_key}})
MERGE (s:{LABEL_SEMANTIC_ASSERTION} {{assertion_node_id: row.node_id}})
SET s += row.properties, s.build_pass = $build_pass
MERGE (p)-[:HAS_SEMANTIC_ASSERTION]->(s)
"""

#: One query per target label, deliberately. The first version used
#: ``MATCH (t) WHERE (t:Devata OR t:DomainEntity) AND ...``, which is an **unlabelled
#: match**: Neo4j cannot use an index for it, so it scans every node in the database once
#: per row. That pattern is also how the V2 pass created 39,461 bogus edges -- an
#: unlabelled ``MATCH (t) WHERE t.work_id = $k`` matched all 11,590 passages instead of the
#: one Work node -- so it is not used here even where it would only be slow.
_SEALED_LINK_QUERIES: Final[tuple[tuple[str, str], ...]] = (
    ("Devata", "entity_key"),
    ("DomainEntity", "entity_key"),
    ("DomainEntity", "concept_id"),
)


def _sealed_link_query(rel: str, label: str, key: str) -> str:
    return f"""
    UNWIND $rows AS row
    MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{assertion_node_id: row.node_id}})
    MATCH (t:{label} {{{key}: row.entity_key}})
    MERGE (s)-[r:{rel} {{role: row.role}}]->(t)
    SET r.quality_tier = 'TIER_D',
        r.knowledge_layer = 'L3_LLM_EXTRACTED',
        r.attribution_precision = 'NOT_AN_ATTRIBUTION',
        r.evidence_basis = 'TRANSLATION',
        r.state = 'CANDIDATE',
        r.grade_basis = 'entity resolved by the sealed run, unreviewed'
    """


def load_sealed(session: Session, projection: SealedProjection) -> LoadReport:
    """Project the sealed run read-only, with its candidate status and receipt intact."""
    # `sent` counts distinct assertion ids, not response rows. The sealed run's files hold
    # 2,474 rows carrying 2,459 distinct ids, and the seal itself declares 2,459 -- so
    # comparing landed nodes against row count would report a correct load as incomplete
    # forever. The 15 duplicates are reported in `detail` rather than hidden here.
    report = LoadReport(step="sealed_semantics", sent=len({row.node_id for row in projection.rows}))
    if not projection.rows:
        return report
    build_pass = uuid.uuid4().hex
    rows = [
        {
            "node_id": row.node_id,
            "passage_key": row.passage_key,
            "properties": {
                key: value
                for key, value in row.as_node_properties(projection.seal).items()
                if not isinstance(value, (dict,))
            },
        }
        for row in projection.rows
        if row.passage_key
    ]
    for batch in _batches(rows):
        session.run(_SEALED_QUERY, rows=batch, build_pass=build_pass)

    agents = [
        {"node_id": row.node_id, "entity_key": row.actor_entity_id, "role": "AGENT"}
        for row in projection.rows
        if row.actor_entity_id
    ]
    targets = [
        {"node_id": row.node_id, "entity_key": entity, "role": role}
        for row in projection.rows
        for entity, role in (
            (row.canonical_entity_id, "CANONICAL_REFERENT"),
            (row.target_entity_id, "TARGET"),
            (row.patient_entity_id, "PATIENT"),
        )
        if entity
    ]
    for rel, rows_to_link in (("ASSERTION_AGENT", agents), ("ASSERTION_TARGET", targets)):
        for label, key in _SEALED_LINK_QUERIES:
            for batch in _batches(rows_to_link):
                session.run(_sealed_link_query(rel, label, key), rows=batch)

    stale = _count(
        session,
        f"""
        MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{derivation: 'MODEL_EXTRACTION'}})
        WHERE s.build_pass IS NULL OR s.build_pass <> $build_pass
        RETURN count(s) AS c
        """,
        build_pass=build_pass,
    )
    if stale:
        session.run(
            f"""
            MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{derivation: 'MODEL_EXTRACTION'}})
            WHERE s.build_pass IS NULL OR s.build_pass <> $build_pass
            DETACH DELETE s
            """,
            build_pass=build_pass,
        )
    retired = stale
    report.landed = _count(
        session,
        f"MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{derivation: 'MODEL_EXTRACTION'}}) "
        "RETURN count(s) AS c",
    )
    distinct_ids = len({row.node_id for row in projection.rows})
    report.detail = {
        "run_id": projection.seal.run_id,
        "seal_status": projection.seal.seal_status,
        "assertion_rows_read": len(projection.rows),
        "distinct_assertion_ids": distinct_ids,
        # The seal declares 2,459 assertions and the response files hold 2,474 rows. The
        # difference is 15 assertion ids that occur twice, which MERGE collapses to one
        # node. Reported rather than smoothed: the seal's own integrity block records
        # `cross_passage_duplicate_ids: 0`, so the duplicates are within a passage, and
        # 2,459 is the count to compare a projection against.
        "duplicate_assertion_ids_collapsed": len(projection.rows) - distinct_ids,
        "seal_declared_assertions": projection.seal.assertions_declared,
        "agent_links_sent": len(agents),
        "target_links_sent": len(targets),
        "agent_links_landed": _count(
            session,
            f"MATCH (:{LABEL_SEMANTIC_ASSERTION} {{derivation:'MODEL_EXTRACTION'}})"
            "-[r:ASSERTION_AGENT]->() RETURN count(r) AS c",
        ),
        "target_links_landed": _count(
            session,
            f"MATCH (:{LABEL_SEMANTIC_ASSERTION} {{derivation:'MODEL_EXTRACTION'}})"
            "-[r:ASSERTION_TARGET]->() RETURN count(r) AS c",
        ),
        # Entity ids the sealed run resolved to that this graph's registries do not
        # contain. Reported, not silently dropped: a link that cannot land is a
        # disagreement between the frozen run and the current registry, and the freeze is
        # not reopened to settle it.
        "target_keys_unresolved": sorted(
            {
                entity
                for row in projection.rows
                for entity in (
                    row.canonical_entity_id,
                    row.target_entity_id,
                    row.patient_entity_id,
                )
                if entity
            }
            - {
                str(record["k"])
                for record in session.run(
                    "MATCH (d:Devata) RETURN d.entity_key AS k "
                    "UNION MATCH (e:DomainEntity) RETURN e.entity_key AS k "
                    "UNION MATCH (e:DomainEntity) RETURN e.concept_id AS k"
                )
            }
        )[:40],
        "retired_stale": retired,
    }
    return report


# ---------------------------------------------------------------------------
# Atharvavedic deity ascriptions
# ---------------------------------------------------------------------------


def load_devata_ascriptions(
    session: Session,
    entities: Sequence[dict[str, Any]],
    assertions: Sequence[dict[str, Any]],
) -> LoadReport:
    """MERGE the Atharvavedic ascription nodes and their passage edges.

    Separate from ``HAS_DEVATA`` on purpose. Whitney's brackets ascribe a hymn with an
    adjectival *descriptor* -- ``āgneyam`` "belonging to Agni" -- not with a deity name.
    Projecting 324 descriptors as deities would make every deity census in the graph
    wrong; dropping them would leave the Atharvaveda at zero deity attribution while its
    own index ascribes 507 hymns.

    **Mark-and-sweep, and it is load-bearing here rather than hygienic.** This layer is
    harvested from printed apparatus, and cleaning that harvest means *removing* rows --
    Whitney's text interleaves verse-count notes and pada references with real ascriptions,
    so an audit found the graph asserting that a hymn's deity-ascription was the number
    eighty-nine. Without a sweep, deleting those rows from the artifact changes nothing in
    the graph: MERGE adds and never retracts, so the corrected build reported 5,385 rows
    sent and 5,908 landed, the surplus being precisely the junk it had just removed. A
    cleanup that cannot delete is not a cleanup.
    """
    # `sent` counts the edges this step is asked to create, not edges plus nodes: mixing
    # them made a complete load report itself incomplete.
    report = LoadReport(step="devata_ascriptions", sent=len(assertions))
    if not entities:
        return report
    build_pass = uuid.uuid4().hex
    session.run(
        f"""
        UNWIND $rows AS row
        MERGE (a:{LABEL_DEVATA_ASCRIPTION} {{entity_key: row.entity_key}})
        SET a.display_label = row.preferred_label,
            a.display_type = 'DevataAscription',
            a.label_iast = row.label_iast,
            a.preferred_label = row.preferred_label,
            a.registry_namespace = row.registry_namespace,
            a.occurrence_count = row.occurrence_count,
            a.source_variants = row.source_variants,
            a.is_ascription_descriptor = true,
            a.short_description =
              'An Anukramani ascription descriptor, not a deity name.',
            a.build_pass = $build_pass
        """,
        rows=list(entities),
        build_pass=build_pass,
    )
    for batch in _batches(list(assertions)):
        session.run(
            f"""
            UNWIND $rows AS row
            MATCH (p:Passage {{canonical_key: row.subject_key}})
            MATCH (a:{LABEL_DEVATA_ASCRIPTION} {{entity_key: row.object_key}})
            MERGE (p)-[r:HAS_DEVATA_ASCRIPTION]->(a)
            SET r.provenance_class = row.provenance_class,
                r.scope_origin = row.scope_origin,
                r.scope_container_key = row.scope_container_key,
                r.source_id = row.source_id,
                r.source_label = row.source_label,
                r.source_locator = row.source_locator,
                r.confidence = row.confidence,
                r.build_pass = $build_pass
            """,
            rows=batch,
            build_pass=build_pass,
        )
    report.landed = _count(
        session,
        f"MATCH (:Passage)-[r:HAS_DEVATA_ASCRIPTION]->(:{LABEL_DEVATA_ASCRIPTION}) "
        "WHERE r.build_pass = $build_pass RETURN count(r) AS c",
        build_pass=build_pass,
    )
    retired_edges = _count(
        session,
        """
        MATCH (:Passage)-[r:HAS_DEVATA_ASCRIPTION]->()
        WHERE r.build_pass IS NULL OR r.build_pass <> $build_pass
        DELETE r
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    # Descriptors are swept after their edges, and only when they have none left. A
    # descriptor the corrected harvest no longer recognises is not merely unreferenced --
    # it is a node asserting that a non-ascription is an ascription, which is the thing
    # being removed.
    retired_nodes = _count(
        session,
        f"""
        MATCH (a:{LABEL_DEVATA_ASCRIPTION})
        WHERE (a.build_pass IS NULL OR a.build_pass <> $build_pass)
          AND NOT (a)<-[:HAS_DEVATA_ASCRIPTION]-()
        DELETE a
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    report.detail = {
        "ascription_nodes": _count(
            session, f"MATCH (a:{LABEL_DEVATA_ASCRIPTION}) RETURN count(a) AS c"
        ),
        "retired_stale_edges": retired_edges,
        "retired_stale_nodes": retired_nodes,
        "edges_by_scope": {
            record["s"]: record["n"]
            for record in session.run(
                "MATCH ()-[r:HAS_DEVATA_ASCRIPTION]->() "
                "RETURN r.scope_origin AS s, count(*) AS n ORDER BY n DESC"
            )
        },
    }
    return report


# ---------------------------------------------------------------------------
# Ritual-layer depth (V3.1)
# ---------------------------------------------------------------------------

#: The chosen thresholds behind :func:`load_ritual_depth`'s book-level rite priors, named
#: here because they are *chosen*. A threshold is a parameter someone picked rather than a
#: decidable relation, which is why every edge resting on one is ``TIER_D`` -- the same
#: grading rule this module already applies to the four similarity-derived formula
#: ``VARIANT`` rows. Declared as constants so a reader can see what they are without
#: reading the query, and so a test can pin them.
RITE_LOCUS_MIN_ENRICHMENT: Final = 20.0
RITE_LOCUS_MIN_TAGGED: Final = 5

#: Grade for the book-level rite prior. ``CONTAINER_INHERITED`` is the load-bearing value:
#: it says the *book* makes this claim, not the verse. The graph already carries the
#: Anukramaṇī's sūkta-wide deity labels this way rather than pretending they are per-verse,
#: and a rite prior over a kāṇḍa is the identical shape. A reader filtering to
#: ``PER_PASSAGE`` never sees these edges, which is the point.
_RITE_PRIOR_GRADE: Final = {
    "quality_tier": "TIER_D",
    "attribution_precision": "CONTAINER_INHERITED",
    "evidence_basis": "STRUCTURAL",
    "knowledge_layer": "L4_INTERPRETIVE_CLAIM",
    "state": "CANDIDATE",
    "derivation": "BOOK_LOCUS_PRIOR",
    "grade_basis": (
        "the book this passage sits in is the measured locus of this rite; the book makes "
        "the claim, not the verse, and the enrichment that identified the book rests on a "
        "chosen threshold"
    ),
}


def load_ritual_depth(session: Session, spec: dict[str, Any]) -> LoadReport:
    """Deepen the ritual layer where the repository already states the depth.

    Three blocks, three benchmark questions, and one rule shared by all of them: every
    assertion is checked against the graph before it is written. ``ritual_depth_v3_1.yaml``
    declares a witness for each typing claim -- a mention count, a taxonomic parent, an
    ``INVOLVES_OFFERING`` edge -- and a declaration whose witness is not in the graph
    produces **no label** and is reported under ``unwitnessed``. A curated typing file's
    characteristic failure is a plausible entry nobody re-measured, and the only defence is
    to make the loader disbelieve the file.

    **Block 1, Q90 -- the hotar.** ``VG:CONCEPT:HOTR-PRIEST`` is declared ``node_type:
    CONCEPT``, and ``PERFORMED_BY``'s signature is ``Ritual -> RitualRole``, so the rite
    loader's per-label ``MATCH`` found nothing and every officiant row naming the hotar
    landed silently. The office with 321 mention edges -- five times the next -- was absent
    from the priestly-role table, which does not shorten the answer, it inverts it: a
    reader concludes the adhvaryu or the patron is the central Vedic officiant. Adding
    ``:RitualRole`` is additive; the ten existing role nodes all carry ``:Concept`` too, so
    the node's 320 ``ABOUT_CONCEPT`` edges are untouched.

    **Block 2, Q100 -- the two-node offering class.** ``:Offering`` held ``havis`` and
    ``dakṣiṇā``. Nothing is acquired here: the label is added to nodes the repository
    already asserts are offered, and it is *added*, never substituted, because ghṛta is a
    substance and an offering both and substituting would break ``USES_SUBSTANCE`` -- the
    mirror of the error being fixed. ``witness_count`` rides on each node so a consumer can
    see that ghṛta has three witnesses and aśva has one.

    **Block 3, Q13/Q60 -- rite-layer recall.** The strict verse-level tags are left exactly
    as they are and their recall against each rite's measured locus book is computed and
    stored *on the rite node*, so a query can return it as a column rather than as a caveat
    the reader never reads. Tagging the whole locus book was refused: it would make recall
    100% by construction, which is circular, and would assert of 127 individual K14 verses
    something no source here says. The book-level prior is a separate
    ``CONTAINER_INHERITED`` layer instead.

    Every locus is **re-measured live** and compared against the figure the artifact
    records. A drifted figure is reported rather than trusted, because a stored measurement
    that no longer matches the rows is this repository's most repeated defect.
    """
    report = LoadReport(step="ritual_depth")
    build_pass = uuid.uuid4().hex
    detail: dict[str, Any] = {}

    detail["ritual_roles"] = _apply_ritual_role_typing(
        session, list(spec.get("ritual_role_typing") or [])
    )
    detail["hotr_alias_purity"] = _stamp_alias_purity(
        session,
        list(spec.get("alias_reassignment") or []),
        list(spec.get("alias_withdrawal") or []),
    )
    detail["officiants"] = _apply_performed_by(session, list(spec.get("rituals") or []), build_pass)
    detail["offerings"] = _apply_offering_typing(session, list(spec.get("offering_typing") or []))
    detail["rite_loci"] = _apply_rite_loci(session, list(spec.get("rite_loci") or []), build_pass)

    report.sent = (
        len(spec.get("ritual_role_typing") or [])
        + len(spec.get("rituals") or [])
        + len(spec.get("offering_typing") or [])
        + len(spec.get("rite_loci") or [])
    )
    report.landed = (
        detail["ritual_roles"]["labelled"]
        + detail["officiants"]["landed"]
        + detail["offerings"]["labelled"]
        + detail["rite_loci"]["loci_measured"]
    )
    report.detail = detail
    return report


def _apply_ritual_role_typing(session: Session, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Add ``:RitualRole`` where the registry retype says so and the graph bears it out."""
    labelled = 0
    unwitnessed: list[str] = []
    for row in rows:
        concept_id = str(row["concept_id"])
        witness = dict(row.get("witness") or {})
        # The witness is a mention count, and it is checked rather than trusted: a registry
        # drift that emptied this node must not silently promote an unmentioned office into
        # a priestly-role census.
        observed = _count(
            session,
            f"MATCH (:{LABEL_PASSAGE})-[r:MENTIONS_ENTITY]->"
            f"(c:{LABEL_CONCEPT} {{concept_id: $cid}}) RETURN count(r) AS c",
            cid=concept_id,
        )
        if observed < int(witness.get("at_least", 0)):
            unwitnessed.append(f"{concept_id}: {observed} mention edges")
            continue
        labelled += _count(
            session,
            f"""
            MATCH (c:{LABEL_CONCEPT} {{concept_id: $cid}})
            SET c:{LABEL_RITUAL_ROLE},
                c.ritual_role_typed_by = 'vedagraph-ritual-depth-v3.1',
                c.question_unlocked = 90
            RETURN count(c) AS c
            """,
            cid=concept_id,
        )
    return {
        "sent": len(rows),
        "labelled": labelled,
        "unwitnessed": unwitnessed,
        "ritual_role_nodes": _count(session, f"MATCH (n:{LABEL_RITUAL_ROLE}) RETURN count(n) AS c"),
    }


def _stamp_alias_purity(
    session: Session,
    reassignments: Sequence[dict[str, Any]],
    withdrawals: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Measure and store what fraction of a role's mention edges are really that role's.

    **This is a measurement, not a correction, and the distinction is deliberate.** The
    mention layer is built from the registry by ``scripts/build_domain_v2.py``; the alias
    split lives in ``data/registry/concepts.yaml`` and lands when that builder next runs.
    Rewriting 25 ``MENTIONS_ENTITY`` edges from here would be a second code path writing
    another layer's edges, and with several passes sharing one database that is how two
    conventions get established for one fact.

    So the corrected figure is published instead of imposed. ``hotṛ``'s alias list is a
    portmanteau -- 302 of its 321 edges are the hotar, 14 are the adhvaryu (an office with
    its own node three files away) and 11 are ``ṛtvij-``, any officiant at all -- and every
    one of those numbers is now on the node, so the priestly-role query can return the
    office's own count and its purity in the row. A role table that reported 321 would be
    7.8% wrong in favour of the very office this pass is promoting.
    """
    out: dict[str, Any] = {}
    for row in list(reassignments) + list(withdrawals):
        concept_id = str(row["from_concept_id"])
        foreign = [str(a) for a in (row.get("aliases_sa") or [])]
        measured = _count(
            session,
            f"""
            MATCH (:{LABEL_PASSAGE})-[r:MENTIONS_ENTITY]->
                  (c:{LABEL_CONCEPT} {{concept_id: $cid}})
            WHERE any(a IN r.matched_aliases WHERE a IN $foreign)
            RETURN count(r) AS c
            """,
            cid=concept_id,
            foreign=foreign,
        )
        entry = out.setdefault(concept_id, {"foreign_alias_edges": 0, "foreign_aliases": []})
        entry["foreign_alias_edges"] += measured
        entry["foreign_aliases"].extend(foreign)

    for concept_id, entry in out.items():
        total = _count(
            session,
            f"MATCH (:{LABEL_PASSAGE})-[r:MENTIONS_ENTITY]->"
            f"(c:{LABEL_CONCEPT} {{concept_id: $cid}}) RETURN count(r) AS c",
            cid=concept_id,
        )
        own = total - int(entry["foreign_alias_edges"])
        entry["mention_edges_total"] = total
        entry["mention_edges_own_alias"] = own
        entry["alias_purity"] = round(own / total, 4) if total else 0.0
        session.run(
            f"""
            MATCH (c:{LABEL_CONCEPT} {{concept_id: $cid}})
            SET c.mention_edges_total = $total,
                c.mention_edges_own_alias = $own,
                c.mention_edges_foreign_alias = $foreign_n,
                c.alias_purity = $purity,
                c.alias_purity_basis =
                  'measured per alias against the live mention layer; the foreign aliases '
                  + 'are split off in data/registry/concepts.yaml and land in the graph on '
                  + 'the next build_domain_v2 run'
            """,
            cid=concept_id,
            total=total,
            own=own,
            foreign_n=int(entry["foreign_alias_edges"]),
            purity=entry["alias_purity"],
        ).consume()
    return out


def _apply_performed_by(
    session: Session, rituals: Sequence[dict[str, Any]], build_pass: str
) -> dict[str, Any]:
    """Attach the officiant edges the rite artifacts already cite verses for.

    Only ``PERFORMED_BY``, and only ``Ritual -> RitualRole``. The rite loader in
    :mod:`vedagraph.domain.loader` owns the other five ritual edge types and sweeps them by
    ``build_pass``; reaching into them from here would put two passes in charge of one
    sweep. This adds the one edge type that was unreachable because its object had the
    wrong label, and leaves the rest to their owner.
    """
    rows = [
        {"ritual_id": str(r["ritual_id"]), "target": str(t)}
        for r in rituals
        for t in (r.get("performed_by") or [])
    ]
    if not rows:
        return {"sent": 0, "landed": 0}
    for batch in _batches(rows):
        session.run(
            f"""
            UNWIND $rows AS row
            MATCH (rt:{LABEL_RITUAL} {{entity_key: row.ritual_id}})
            MATCH (office:{LABEL_RITUAL_ROLE} {{entity_key: row.target}})
            MERGE (rt)-[r:PERFORMED_BY]->(office)
            SET r.quality_tier = 'TIER_D',
                r.knowledge_layer = 'L4_INTERPRETIVE_CLAIM',
                r.attribution_precision = 'NOT_AN_ATTRIBUTION',
                r.evidence_basis = 'SANSKRIT',
                r.grade_basis =
                  'curated ritual structure; the rite artifact cites the verse that names '
                  + 'this office in this rite',
                r.question_unlocked = 90,
                r.build_pass = $build_pass
            """,
            rows=batch,
            build_pass=build_pass,
        ).consume()
    landed = _count(
        session,
        f"MATCH (:{LABEL_RITUAL})-[r:PERFORMED_BY]->(:{LABEL_RITUAL_ROLE}) "
        "WHERE r.build_pass = $build_pass RETURN count(r) AS c",
        build_pass=build_pass,
    )
    return {
        "sent": len(rows),
        "landed": landed,
        "performed_by_total": _count(session, "MATCH ()-[r:PERFORMED_BY]->() RETURN count(r) AS c"),
    }


def _apply_offering_typing(session: Session, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Add ``:Offering`` to nodes the repository already asserts are offered.

    The witness is recomputed from the graph for every row, and a row whose witness the
    graph does not bear out gets no label. Two witness kinds count: a registry-declared
    ``BROADER_THAN`` from ``havis``, and an ``INVOLVES_OFFERING`` edge from a passage. Both
    are already in the graph, so this is a typing pass and not an acquisition -- which is
    what makes it legitimate under "invent no ritual procedure".
    """
    labelled = 0
    unwitnessed: list[str] = []
    per_node: dict[str, Any] = {}
    for row in rows:
        concept_id = str(row["concept_id"])
        record = session.run(
            f"""
            MATCH (c:{LABEL_CONCEPT} {{concept_id: $cid}})
            OPTIONAL MATCH (h:{LABEL_CONCEPT} {{concept_id: $havis}})-[:BROADER_THAN]->(c)
            OPTIONAL MATCH (:{LABEL_PASSAGE})-[io:INVOLVES_OFFERING]->(c)
            RETURN count(DISTINCT h) AS taxonomic, count(io) AS corpus_asserted
            """,
            cid=concept_id,
            havis="VG:CONCEPT:HAVIS-OBLATION",
        ).single()
        if record is None:
            unwitnessed.append(f"{concept_id}: node absent")
            continue
        taxonomic = int(record["taxonomic"])
        corpus = int(record["corpus_asserted"])
        witnesses = (1 if taxonomic else 0) + (1 if corpus else 0)
        if witnesses == 0:
            unwitnessed.append(f"{concept_id}: no taxonomic parent and no corpus edge")
            continue
        labelled += _count(
            session,
            f"""
            MATCH (c:{LABEL_CONCEPT} {{concept_id: $cid}})
            SET c:{LABEL_OFFERING},
                c.offering_witness_count = $witnesses,
                c.offering_witness_taxonomic = $taxonomic,
                c.offering_witness_corpus_edges = $corpus,
                c.offering_typed_by = 'vedagraph-ritual-depth-v3.1',
                c.question_unlocked = 100
            RETURN count(c) AS c
            """,
            cid=concept_id,
            witnesses=witnesses,
            taxonomic=bool(taxonomic),
            corpus=corpus,
        )
        per_node[concept_id] = {
            "witness_count": witnesses,
            "taxonomic": bool(taxonomic),
            "corpus_asserted_edges": corpus,
        }
    total = _count(session, f"MATCH (n:{LABEL_OFFERING}) RETURN count(n) AS c")
    return {
        "sent": len(rows),
        "labelled": labelled,
        "unwitnessed": unwitnessed,
        "per_node": per_node,
        "offering_nodes": total,
        # Reported on every run, and deliberately not a boolean the caller can forget to
        # read: eight nodes is not a Vedic offering vocabulary, and a join through this
        # class that returns few rows must not be read as a small phenomenon.
        "class_is_complete": False,
        "class_completeness_note": (
            f"{total} Offering nodes. Sufficient to stop the four-dimension join "
            "collapsing; not a corpus-scale offering vocabulary. Any ranking or row count "
            "through this class must publish this figure alongside it."
        ),
    }


def _apply_rite_loci(
    session: Session, rows: Sequence[dict[str, Any]], build_pass: str
) -> dict[str, Any]:
    """Re-measure each rite's locus book, publish its recall, and project the book prior.

    The measurement is the deliverable. ``strict_recall_against_locus`` lands **on the rite
    node**, because the criterion these questions fail is that a frequency or coverage
    claim must be accompanied by a measured figure, and a caveat in prose is read by nobody
    who runs the obvious query. A column in the row is read by everybody.

    Every figure the artifact records is recomputed here and compared, and a mismatch is
    reported rather than corrected. A stored count that has drifted from the rows it
    summarises is the defect class this repository has hit most often, and the only way the
    audit stays honest is if the loader reads the rows and not the stored block.
    """
    measured: list[dict[str, Any]] = []
    drift: list[dict[str, Any]] = []
    prior_edges = 0
    for row in rows:
        rite_id = str(row["rite_id"])
        veda = str(row["veda"])
        book = str(row["locus_book"])
        record = session.run(
            f"""
            MATCH (p:{LABEL_PASSAGE} {{veda: $veda}})
            WHERE p.canonical_key CONTAINS ':' + $book + ':'
            WITH collect(p) AS book_passages
            MATCH (q:{LABEL_PASSAGE} {{veda: $veda}})-[qr:USED_FOR_RITE]->
                  (:{LABEL_SOCIAL_RITE} {{entity_key: $rite}})
            // ONLY the strict verse-level layer. Counting this pass's own book priors
            // here made the loader non-idempotent and, worse, circular: on the second run
            // tagged_in_book was 141 of 141 and the recall figure this layer exists to
            // publish read 100%. The prior must never be its own denominator.
            WHERE qr.attribution_precision = 'PER_PASSAGE'
            WITH book_passages, collect(q) AS tagged
            RETURN size(book_passages) AS book_size,
                   size(tagged) AS tagged_in_veda,
                   size([x IN tagged WHERE x IN book_passages]) AS tagged_in_book
            """,
            veda=veda,
            book=book,
            rite=rite_id,
        ).single()
        if record is None:
            continue
        book_size = int(record["book_size"])
        tagged_in_book = int(record["tagged_in_book"])
        tagged_in_veda = int(record["tagged_in_veda"])
        veda_size = _count(
            session,
            f"MATCH (p:{LABEL_PASSAGE} {{veda: $veda}}) RETURN count(p) AS c",
            veda=veda,
        )
        outside_size = veda_size - book_size
        outside_tagged = tagged_in_veda - tagged_in_book
        rate_in = tagged_in_book / book_size if book_size else 0.0
        rate_out = outside_tagged / outside_size if outside_size else 0.0
        enrichment = round(rate_in / rate_out, 2) if rate_out else 0.0
        recall = round(rate_in, 4)

        entry = {
            "rite_id": rite_id,
            "locus_book": book,
            "book_size": book_size,
            "tagged_in_book": tagged_in_book,
            "tagged_in_veda": tagged_in_veda,
            "rate_in_book": round(rate_in, 4),
            "rate_outside_book": round(rate_out, 4),
            "enrichment": enrichment,
            "strict_recall_against_locus": recall,
            "passes_thresholds": (
                enrichment >= RITE_LOCUS_MIN_ENRICHMENT and tagged_in_book >= RITE_LOCUS_MIN_TAGGED
            ),
        }
        measured.append(entry)

        declared = dict(row.get("measured") or {})
        for field_name, live in (
            ("book_passages", book_size),
            ("strict_tagged_in_book", tagged_in_book),
            ("strict_tagged_in_veda", tagged_in_veda),
        ):
            if field_name in declared and int(declared[field_name]) != live:
                drift.append(
                    {
                        "rite_id": rite_id,
                        "field": field_name,
                        "declared": declared[field_name],
                        "live": live,
                    }
                )

        if not entry["passes_thresholds"]:
            continue

        # The recall figure goes on the rite node so a query returns it as a column.
        session.run(
            f"""
            MATCH (s:{LABEL_SOCIAL_RITE} {{entity_key: $rite}})
            SET s.locus_veda = $veda,
                s.locus_book = $book,
                s.locus_book_passages = $book_size,
                s.locus_tagged_passages = $tagged_in_book,
                s.strict_recall_against_locus = $recall,
                s.locus_enrichment = $enrichment,
                s.strict_tagged_passages_in_veda = $tagged_in_veda,
                s.recall_basis =
                  'strict verse-level USED_FOR_RITE tags counted against the measured '
                  + 'locus book. The locus is the book whose tag rate is most enriched '
                  + 'over the rest of the Veda; the enrichment threshold is chosen, so '
                  + 'the locus is TIER_D even though the recall figure itself is a count.',
                s.recall_is_measured = true,
                s.question_unlocked = '13,60'
            """,
            rite=rite_id,
            veda=veda,
            book=book,
            book_size=book_size,
            tagged_in_book=tagged_in_book,
            recall=recall,
            enrichment=enrichment,
            tagged_in_veda=tagged_in_veda,
        ).consume()

        # The book-level prior, as a separate CONTAINER_INHERITED layer. Untagged passages
        # only: an existing verse-level tag is stronger evidence and must not be
        # overwritten with an inherited one.
        #
        # The "already tagged" test keys on `derivation IS NULL` -- the strict layer's own
        # marker -- and NOT on `attribution_precision = 'PER_PASSAGE'`, because precision
        # is a property another pass can overwrite and one did. The shared domain rebuild
        # regrades every edge whose type is not in tiers.LAYER_OWNED_GRADES, and
        # USED_FOR_RITE was not in that set, so all 529 edges were flattened to
        # PER_PASSAGE. The priors then LOOKED like strict tags to this guard, none were
        # rewritten, and the sweep below deleted all 419 -- a two-step cascade from one
        # flattened property to a deleted layer. USED_FOR_RITE is now layer-owned, and
        # this guard no longer depends on a property it does not itself write.
        prior_edges += _count(
            session,
            f"""
            MATCH (p:{LABEL_PASSAGE} {{veda: $veda}})
            WHERE p.canonical_key CONTAINS ':' + $book + ':'
              AND NOT EXISTS {{
                MATCH (p)-[strict:USED_FOR_RITE]->
                      (:{LABEL_SOCIAL_RITE} {{entity_key: $rite}})
                WHERE strict.derivation IS NULL
              }}
            MATCH (s:{LABEL_SOCIAL_RITE} {{entity_key: $rite}})
            // Keyed on the derivation, so a prior is a distinct edge from a strict tag and
            // can never silently absorb one. Without the key, MERGE matched the prior it
            // wrote last run and the sweep then deleted it, so the layer oscillated
            // between 419 edges and 0.
            MERGE (p)-[r:USED_FOR_RITE {{derivation: 'BOOK_LOCUS_PRIOR'}}]->(s)
            SET r += $grade,
                r.locus_book = $book,
                r.question_unlocked = '13,60',
                r.build_pass = $build_pass
            RETURN count(r) AS c
            """,
            veda=veda,
            book=book,
            rite=rite_id,
            grade=_RITE_PRIOR_GRADE,
            build_pass=build_pass,
        )

    # Mark and sweep the prior layer only. The strict PER_PASSAGE tags carry no build_pass
    # from this pass and must survive it untouched -- which is exactly why the sweep is
    # keyed on the derivation as well as the pass.
    swept = _count(
        session,
        f"""
        MATCH (:{LABEL_PASSAGE})-[r:USED_FOR_RITE]->(:{LABEL_SOCIAL_RITE})
        WHERE r.derivation = 'BOOK_LOCUS_PRIOR'
          AND (r.build_pass IS NULL OR r.build_pass <> $build_pass)
        DELETE r
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    return {
        "loci_measured": len(measured),
        "measurements": measured,
        "declared_vs_live_drift": drift,
        "book_prior_edges": prior_edges,
        "retired_stale_priors": swept,
        "thresholds": {
            "min_enrichment": RITE_LOCUS_MIN_ENRICHMENT,
            "min_tagged_in_book": RITE_LOCUS_MIN_TAGGED,
        },
        "strict_layer_untouched": _count(
            session,
            f"MATCH (:{LABEL_PASSAGE})-[r:USED_FOR_RITE]->(:{LABEL_SOCIAL_RITE}) "
            "WHERE r.attribution_precision = 'PER_PASSAGE' RETURN count(r) AS c",
        ),
    }


# ---------------------------------------------------------------------------
# The sealed layer's predicate axis
# ---------------------------------------------------------------------------

#: Sealed ``semantic_predicate`` -> closed action-predicate vocabulary, and it is short on
#: purpose.
#:
#: The measured gap was that 2,459 of 4,865 ``:SemanticAssertion`` nodes -- the whole
#: ``MODEL_EXTRACTION`` half -- carry their predicate as a node *property* and reach no
#: ``:ActionPredicate`` node, so predicate-level traversal saw one layer and reported it as
#: the layer. Closing that gap by mapping the property onto the vocabulary looked like
#: bookkeeping. It is not, because **the two halves do not share a predicate axis.**
#:
#: The sealed run's ``semantic_predicate`` is a closed set of 13 values, every one of them
#: a *discourse relation between a passage and a referent*: ``DESCRIBES`` (734),
#: ``DESCRIBES_ACTION`` (553), ``REQUESTS`` (395), ``INVOKES`` (211), ``REFERS_TO_PLACE``
#: (122), ``INVOLVES_SUBSTANCE`` (117), ``REFERS_TO_NATURAL_PHENOMENON`` (100),
#: ``INVOLVES_RITUAL`` (78), ``PRAISES`` (55), ``INVOLVES_OFFERING`` (46), ``EXPRESSES``
#: (27), ``ASSOCIATED_WITH`` (17), ``CONTRASTS_WITH`` (4). ``:ActionPredicate`` is a closed
#: set of 40 *verbal-root action classes* from ``data/registry/action_predicates.yaml``,
#: each with an ``argument_frame`` over morphological cases, whose header states the
#: contract: "a root that does not map into one of these classes is recorded as
#: UNMAPPED_ROOT and produces no predicate edge. Adding a class is a deliberate ontology
#: change, not something an extractor may do because a verse needed it."
#:
#: Exactly two names appear in both sets, and for both the registry gloss and the sealed
#: usage agree, so both are mapped:
#:
#: * ``INVOKES`` -- registry gloss "calls a divine being to attend"; 211 sealed assertions,
#:   overwhelmingly with ``object_kind`` ``CANONICAL_ENTITY_REF`` resolving to a deity.
#: * ``PRAISES`` -- registry gloss "sings, extols or magnifies"; 55 sealed assertions.
#:
#: The other eleven get **no predicate node minted**, and the residual is reported rather
#: than closed. Three separate reasons, none of them a shortage of effort:
_SEALED_PREDICATE_MAP: Final[dict[str, str]] = {
    "INVOKES": "INVOKES",
    "PRAISES": "PRAISES",
}

#: Why each unmapped sealed predicate stays unmapped, keyed by the value it appears as.
#: Recorded in the loader and echoed into the run report, because "not mapped" and "nobody
#: looked" are indistinguishable in a coverage number and only one of them is acceptable.
_SEALED_PREDICATE_WITHHELD: Final[dict[str, str]] = {
    "REQUESTS": (
        "The registry rules on this one by name and rules against it: REQUESTS_FROM 'is "
        "not a predicate here. It is a grammatical frame, not a verb class ... Modelling "
        "it as a predicate would force every request to lose its content (Indra "
        "REQUESTS_FROM ???)'. The agentive layer carries the same fact as frame = "
        "REQUESTED, orthogonal to the predicate. Minting a REQUESTS predicate node would "
        "reintroduce the exact confusion the registry documents rejecting."
    ),
    "DESCRIBES_ACTION": (
        "These are the 553 assertions whose object_kind is EVENT and whose verb is a "
        "free-text action_head. sealed_semantics records a reasoned refusal to map them: "
        "'502 distinct action heads for 559 events ... The mapping would be a fresh "
        "interpretation of frozen output, which is exactly what do not reopen the freeze "
        "to make it fit forbids.' Mapping them here would overturn that refusal from a "
        "loader, which is not where that decision belongs."
    ),
    "DESCRIBES": (
        "Not an action. A passage-to-referent aboutness relation with no verbal root and "
        "no argument frame; there is no registry class it is a weaker or stronger form of."
    ),
    "REFERS_TO_PLACE": "Not an action: a passage-to-referent reference relation.",
    "INVOLVES_SUBSTANCE": "Not an action: a passage-to-referent reference relation.",
    "REFERS_TO_NATURAL_PHENOMENON": ("Not an action: a passage-to-referent reference relation."),
    "INVOLVES_RITUAL": "Not an action: a passage-to-referent reference relation.",
    "INVOLVES_OFFERING": "Not an action: a passage-to-referent reference relation.",
    "EXPRESSES": "Not an action: a passage-to-referent reference relation.",
    "ASSOCIATED_WITH": (
        "Not an action, and the vaguest of the thirteen. The relation this graph spent a "
        "V2 pass splitting into ASSOCIATED_WITH_CONCEPT, _PHENOMENON and _SUBSTANCE; "
        "giving it a predicate node would re-flatten that."
    ),
    "CONTRASTS_WITH": "Not an action: a passage-to-passage rhetorical relation.",
}

#: Deliberately **not** a ``MERGE`` on the predicate node. Both endpoints are matched, so a
#: sealed value whose registry node is missing lands nothing and shows up in the residual,
#: rather than quietly minting a 42nd ``:ActionPredicate`` and enlarging a closed
#: vocabulary from inside a projection.
_SEALED_PREDICATE_EDGE_QUERY: Final = f"""
UNWIND $rows AS row
MATCH (s:{LABEL_SEMANTIC_ASSERTION} {{assertion_node_id: row.node_id}})
MATCH (a:{LABEL_ACTION_PREDICATE} {{predicate: row.predicate}})
MERGE (s)-[r:ASSERTION_PREDICATE]->(a)
SET r.build_pass = $build_pass
"""

#: Every ``ASSERTION_PREDICATE`` edge inherits the grade of the assertion it starts from,
#: both halves, in one statement.
#:
#: The generic stamper graded the whole type ``TIER_B``/``STRUCTURAL`` on the reasoning that
#: "this assertion predicates this vocabulary member" is a structural fact about the graph.
#: That was harmless while only the rule layer reached ``:ActionPredicate`` and it stops
#: being harmless the moment the sealed layer does: ``derivation`` and ``quality_tier`` are
#: the documented way to keep the two apart, and a uniform ``TIER_B`` would hand back
#: unreviewed extraction over Griffith's English under a filter that promises Zurich
#: morphology. That is the same defect
#: :func:`reconcile_assertion_edge_grades` was written to fix one edge type over, and the
#: fix is the same: read the grade off the node, do not re-derive it from the type.
#:
#: Both populations are regraded, not only the rows this pass added. Grading only the new
#: edges would leave the older 2,406 depending on ``vedagraph.domain.upgrade`` -- a pass
#: outside this projection -- for a grade the projection is now responsible for.
_SEALED_PREDICATE_GRADE_QUERY: Final = f"""
MATCH (s:{LABEL_SEMANTIC_ASSERTION})-[r:ASSERTION_PREDICATE]->
      (:{LABEL_ACTION_PREDICATE})
SET r.quality_tier = coalesce(s.quality_tier, 'TIER_D'),
    r.evidence_basis = coalesce(s.evidence_basis, 'MODEL_INTERPRETATION'),
    r.derivation = s.derivation,
    r.review_state = s.review_state,
    r.state = coalesce(s.state, 'CANDIDATE'),
    r.knowledge_layer = coalesce(s.knowledge_layer, 'L3_LLM_EXTRACTED'),
    r.attribution_precision = 'NOT_AN_ATTRIBUTION',
    r.grade_basis =
      'inherited from the assertion this edge starts from; the label carries two layers '
      + 'of unequal strength and reach and the edge must not flatten them'
RETURN count(r) AS c
"""


def load_sealed_predicate_edges(session: Session) -> LoadReport:
    """Give the sealed model layer a predicate edge where the vocabulary honestly allows.

    ``ASSERTION_PREDICATE`` reached 2,406 of 4,865 assertions, and the 2,459 it missed were
    not a random shortfall -- they were precisely the ``MODEL_EXTRACTION`` layer, which
    stores its predicate as a node property. So "which predicates does this graph assert?"
    answered from the edges described the rule layer and called it the graph.

    What this does **not** do is close that gap to zero, and the reason is the point. The
    sealed layer's 13 predicates and the registry's 40 are two different axes: discourse
    relations between a passage and a referent, against verbal-root action classes with
    morphological argument frames. Two names occur in both with agreeing glosses and are
    mapped (``INVOKES``, ``PRAISES`` -- 266 assertions). The other eleven are left
    unlinked and named in ``detail`` with a reason each, because the registry reserves
    adding a class to a deliberate ontology change and because forcing 2,193 assertions
    onto classes that do not mean the same thing would have bought a coverage number with
    a wrong graph. See :data:`_SEALED_PREDICATE_WITHHELD`.

    The layers stay separable, which is the hard constraint on this change. The rule layer
    spreads 2,406 assertions over 2,228 passages and the model layer packs 2,459 into 398;
    summing them is the misleading answer this graph exists to refuse. Every
    ``ASSERTION_PREDICATE`` edge -- old and new -- now carries ``derivation``,
    ``quality_tier``, ``evidence_basis``, ``state`` and ``review_state`` copied from its
    assertion, so a query filters the halves apart on the edge without reaching the node.

    Nothing sealed is written. The mapping is a read of a projected node property against a
    registry file; no file under ``data/semantic`` is opened, and the assertion nodes
    themselves are not modified.
    """
    report = LoadReport(step="sealed_predicate_edges")
    candidates = [
        {"node_id": record["node_id"], "predicate": record["predicate"]}
        for record in session.run(
            f"""
            MATCH (s:{LABEL_SEMANTIC_ASSERTION})
            WHERE s.derivation = 'MODEL_EXTRACTION'
              AND s.semantic_predicate IN $mapped
              AND s.assertion_node_id IS NOT NULL
            RETURN s.assertion_node_id AS node_id,
                   $map[s.semantic_predicate] AS predicate
            """,
            mapped=sorted(_SEALED_PREDICATE_MAP),
            map=_SEALED_PREDICATE_MAP,
        )
    ]
    report.sent = len(candidates)
    build_pass = uuid.uuid4().hex
    for batch in _batches(candidates):
        session.run(_SEALED_PREDICATE_EDGE_QUERY, rows=batch, build_pass=build_pass).consume()
    report.landed = _count(
        session,
        f"""
        MATCH (s:{LABEL_SEMANTIC_ASSERTION})-[r:ASSERTION_PREDICATE]->
              (:{LABEL_ACTION_PREDICATE})
        WHERE r.build_pass = $build_pass AND s.derivation = 'MODEL_EXTRACTION'
        RETURN count(r) AS c
        """,
        build_pass=build_pass,
    )
    graded = _count(session, _SEALED_PREDICATE_GRADE_QUERY)

    unmapped = {
        record["p"]: record["n"]
        for record in session.run(
            f"""
            MATCH (s:{LABEL_SEMANTIC_ASSERTION})
            WHERE s.derivation = 'MODEL_EXTRACTION'
              AND NOT (s)-[:ASSERTION_PREDICATE]->(:{LABEL_ACTION_PREDICATE})
            RETURN s.semantic_predicate AS p, count(*) AS n ORDER BY n DESC
            """
        )
    }
    report.detail = {
        "predicate_edges": {"sent": report.sent, "landed": report.landed},
        "edges_regraded": graded,
        "mapped_vocabulary": dict(_SEALED_PREDICATE_MAP),
        "unmapped_by_predicate": unmapped,
        "unmapped_total": sum(unmapped.values()),
        "withheld_reasons": {
            predicate: _SEALED_PREDICATE_WITHHELD[predicate]
            for predicate in unmapped
            if predicate in _SEALED_PREDICATE_WITHHELD
        },
        # A sealed predicate that is neither mapped nor explicitly withheld means the
        # sealed vocabulary grew and nobody adjudicated the new value. Reported so it
        # cannot arrive silently inside the residual.
        "unadjudicated_predicates": sorted(
            predicate for predicate in unmapped if predicate not in _SEALED_PREDICATE_WITHHELD
        ),
        # The reach asymmetry, restated from the edges after the change. These two numbers
        # are what makes summing the layers wrong, so they are measured here rather than
        # trusted from the close-out report.
        "reach_by_derivation": {
            f"{record['d']}": {
                "assertions": record["n"],
                "passages": record["p"],
                "predicates": record["k"],
            }
            for record in session.run(
                f"""
                MATCH (s:{LABEL_SEMANTIC_ASSERTION})-[r:ASSERTION_PREDICATE]->
                      (a:{LABEL_ACTION_PREDICATE})
                RETURN r.derivation AS d, count(r) AS n,
                       count(DISTINCT s.passage_key) AS p,
                       count(DISTINCT a.predicate) AS k
                ORDER BY n DESC
                """
            )
        },
        "edges_ungraded": _count(
            session,
            f"""
            MATCH ()-[r:ASSERTION_PREDICATE]->(:{LABEL_ACTION_PREDICATE})
            WHERE r.quality_tier IS NULL OR r.derivation IS NULL
            RETURN count(r) AS c
            """,
        ),
    }
    return report


# ---------------------------------------------------------------------------
# Formula families
# ---------------------------------------------------------------------------

_FAMILY_NODE_QUERY = f"""
UNWIND $rows AS row
MERGE (fam:{LABEL_FORMULA_FAMILY} {{family_id: row.family_id}})
SET fam.display_label = row.representative_display_form,
    fam.display_type = 'FormulaFamily',
    fam.representative_formula_id = row.representative_formula_id,
    fam.representative_display_form = row.representative_display_form,
    fam.representative_normalized = row.representative_normalized,
    fam.representative_coverage = row.representative_coverage,
    fam.member_count = row.member_count,
    fam.core_count = row.core_count,
    fam.secondary_core_count = row.secondary_core_count,
    fam.expansion_count = row.expansion_count,
    fam.variant_count = row.variant_count,
    fam.containment_depth = row.containment_depth,
    fam.min_word_count = row.min_word_count,
    fam.max_word_count = row.max_word_count,
    fam.occurrence_count = row.occurrence_count,
    fam.mantra_count = row.mantra_count,
    fam.vedas = row.vedas,
    fam.veda_counts = row.veda_counts,
    fam.veda_span = row.veda_span,
    fam.cross_veda = row.cross_veda,
    fam.parallel_corroborated = row.parallel_corroborated,
    fam.derivation_method = row.derivation_method,
    fam.evidence = row.evidence,
    fam.evidence_count = row.evidence_count,
    fam.notes = row.notes,
    fam.quality_tier = $tier,
    fam.evidence_basis = 'SANSKRIT',
    fam.grade_basis = 'containment over the collapsed identity surface, decidable',
    fam.trust = row.trust,
    fam.method = row.method,
    fam.score = row.score,
    fam.state = row.state,
    fam.pipeline_version = row.pipeline_version,
    fam.run_id = row.run_id,
    fam.build_pass = $build_pass
"""

#: Membership derivation, per row, and the three are **not** equally strong.
#:
#: An adversarial audit measured this and it was the right catch: 198 of 2,037 member
#: edges do not directly contain, and are not contained by, the formula they cite, and 103
#: of those share no word with the family's representative at all. The original
#: ``grade_basis`` here read *"containment of one stored formula string in another"*,
#: which asserted a **direct** pairwise relation the layer does not have.
#:
#: What the layer actually has, verified by recomputation over all 720 families: every one
#: of the 2,037 members is linked to at least one *sibling* by direct containment, and zero
#: members are linked to none. So a family is a genuine **connected component** under
#: containment, and membership is transitive rather than pairwise. That is still decidable
#: and still recomputable from the stored strings, so it is still ``TIER_B`` -- but it is a
#: weaker statement than the one the edge was making, and the difference is exactly the
#: difference between "this phrase contains that one" and "these phrases belong to one
#: chain of expansions". ``CORE`` marks a *maximal* element of the component, of which a
#: component may have several, which is why 194 of the 198 are ``CORE``: two maximal
#: formulas in one chain need not contain each other.
#:
#: The four ``VARIANT`` rows are a different matter and are graded down. They come from
#: ``formula-family-variant-by-similarity-v1`` at similarity 0.76-0.86 -- a *chosen
#: threshold* over a similarity metric, not a decidable relation -- and one of them pairs
#: "who hates us" with "whom we hate", an agent reversal. A threshold is a parameter
#: someone picked, so these are ``TIER_D`` candidates, and carrying them at ``TIER_B``
#: under a containment basis was simply wrong.
_MEMBER_TIER_CASE: Final = """CASE
      WHEN row.method CONTAINS 'similarity' THEN 'TIER_D'
      WHEN NOT row.has_containment_support THEN 'TIER_D'
      ELSE 'TIER_B'
    END"""
_MEMBER_BASIS_CASE: Final = """CASE
      WHEN row.method CONTAINS 'similarity'
        THEN 'similarity above a chosen threshold, not containment: a candidate'
      WHEN NOT row.has_containment_support
        THEN 'in a containment component only by way of a similarity candidate, so ' +
             'no stronger than that candidate'
      ELSE 'membership of a containment component over the collapsed identity ' +
           'surface; transitive, not pairwise, and recomputable from the graph'
    END"""

_FAMILY_MEMBER_QUERY = f"""
UNWIND $rows AS row
MATCH (f:{LABEL_FORMULA} {{formula_id: row.formula_id}})
MATCH (fam:{LABEL_FORMULA_FAMILY} {{family_id: row.family_id}})
MERGE (f)-[r:{REL_MEMBER_OF_FAMILY}]->(fam)
SET r.membership_id = row.membership_id,
    r.role = row.role,
    r.similarity = row.similarity,
    r.match_level = row.match_level,
    r.linked_formula_id = row.linked_formula_id,
    r.word_count = row.word_count,
    r.mantra_count = row.mantra_count,
    r.evidence = row.evidence,
    r.evidence_count = row.evidence_count,
    r.derivation = row.method,
    r.containment_is_transitive = row.containment_is_transitive,
    r.contains_representative = row.contains_representative,
    r.has_containment_support = row.has_containment_support,
    r.quality_tier = {_MEMBER_TIER_CASE},
    r.evidence_basis = 'SANSKRIT',
    r.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
    r.grade_basis = {_MEMBER_BASIS_CASE},
    r.asserts = $member_asserts,
    r.trust = row.trust,
    r.method = row.method,
    r.score = row.score,
    r.state = row.state,
    r.pipeline_version = row.pipeline_version,
    r.run_id = row.run_id,
    r.attribution_precision = 'NOT_AN_ATTRIBUTION',
    r.build_pass = $build_pass
"""
# V3.2: the REMOVE became a SET of the sentinel, and the reason the REMOVE existed is the
# reason the sentinel is better. An earlier build of this layer wrote
# `attribution_precision = 'TEXTUAL_MENTION'` here, and MERGE finds that edge and SET
# leaves any property it does not mention in place -- so dropping the assignment cleaned up
# new edges and left 2,037 old ones asserting a category error. Unsetting a property that
# should never have existed had to be explicit, and every future casualty would have had to
# be remembered by name. An ordinary SET cannot fail that way.
#
# The absence contract is superseded rather than abandoned. It was never held consistently:
# `BELONGS_TO_FAMILY`, 500 lines below, is the identical category error and resolved it the
# opposite way, minting a false CONTAINER_INHERITED because "once the property has to hold
# something the only safe value is the inherited one". Both sites now say the same true
# thing instead of two different false ones.

#: No ``attribution_precision``. The axis is defined over *passages* -- whether a source
#: named this verse, inherited the claim from its hymn, or the verse names the entity
#: itself -- and neither endpoint of this edge is a passage. The original code set
#: ``TEXTUAL_MENTION`` here, which is a category error: it made a formula-to-family edge
#: claim something about textual attribution that the edge cannot be about.
_MEMBER_ASSERTS: Final = (
    "This formula belongs to this containment component. It does NOT assert that the "
    "formula contains, or is contained by, the family's representative: check "
    "contains_representative for that."
)


#: The outward mirror, and every property comes from the inbound edge by assignment rather
#: than by being restated here. ``h = properties(m)`` is a *replacing* assignment, not an
#: additive one, so a property the inbound edge stops carrying disappears from the mirror
#: on the next pass instead of lingering -- the same hazard the ``REMOVE
#: r.attribution_precision`` above exists for, solved structurally rather than by
#: remembering to unset each casualty by name.
#:
#: Both ``MATCH`` clauses are labelled and both endpoints are keyed. An unlabelled
#: ``MATCH`` in a mutation is how this repository once created 39,461 bogus edges, and the
#: mirror is the exact shape where it would be tempting: the rows to copy are "every
#: membership edge", which invites ``MATCH ()-[m:MEMBER_OF_FAMILY]->()``.
#:
#: ``build_pass`` is overwritten *after* the copy, on purpose. The inbound edge's own
#: ``build_pass`` arrives inside ``properties(m)``, and leaving it there would make the
#: mirror claim it was written by the membership pass -- so the sweep below could never
#: tell a mirror this pass wrote from one left by a previous one.
_FAMILY_OUTWARD_QUERY: Final = f"""
MATCH (f:{LABEL_FORMULA})-[m:{REL_MEMBER_OF_FAMILY}]->(fam:{LABEL_FORMULA_FAMILY})
MERGE (fam)-[h:{REL_HAS_FORMULA}]->(f)
SET h = properties(m),
    h.asserts = $outward_asserts,
    h.mirrors = '{REL_MEMBER_OF_FAMILY}',
    h.build_pass = $build_pass
RETURN count(h) AS c
"""

#: The inbound edge's ``asserts`` is written from the formula's side ("this formula belongs
#: to this component"), and read off the outward edge it would be the wrong way round. It
#: is the one property the mirror restates, because ``asserts`` is prose meant to be read
#: by whoever hit the edge and grading parity does not extend to a sentence whose subject
#: changed. Every graded field -- ``quality_tier``, ``evidence_basis``, ``grade_basis``,
#: ``knowledge_layer``, ``role``, ``trust``, ``score``, ``state`` -- is copied untouched.
_OUTWARD_ASSERTS: Final = (
    "This containment component includes this formula, with its part in the component on "
    "role. It does NOT assert that the family's representative contains, or is contained "
    "by, this formula: check contains_representative for that. Mirror of "
    "MEMBER_OF_FAMILY; the two directions of one membership are graded identically by "
    "construction."
)


def load_formula_family_outward(session: Session) -> LoadReport:
    """Mirror ``MEMBER_OF_FAMILY`` outward as ``HAS_FORMULA``, and audit the counts block.

    The family layer landed navigable in one direction. Cypher will walk a relationship
    either way, so nothing was *unreachable* -- but every surface that reads the graph as a
    directed thing saw ``:FormulaFamily`` as a sink: the generated ontology reference
    listed no outward predicate for it, and the four questions this unblocks all start at a
    family and ask for its formulas. Reachable is not navigable, and the fix is a mirror.

    It is a **mirror, not a derivation**, and the distinction is the whole design. Nothing
    is recomputed from ``formula_family_members.jsonl``: the rows copied are the
    ``MEMBER_OF_FAMILY`` edges that pass already landed, so the outward edge cannot
    disagree with the inbound one about ``role``, tier or basis even if the artifact and
    the graph have drifted. Re-deriving would have produced a second opinion about
    membership, and a second opinion is exactly what a directionality repair must not
    introduce. Run it after :func:`load_formula_families` -- against a graph with no
    membership edges it correctly writes nothing rather than failing.

    The counts audit rides along rather than living in its own step, because it is only
    answerable once both directions exist and it is the one question the mirror makes
    cheap: ``member_count``, ``core_count`` and ``variant_count`` are recorded *on the
    family node* and summarise edges stored elsewhere, which is the shape that has drifted
    from its rows before in this repository. Any family whose recorded numbers disagree
    with the edges that actually landed is named in ``detail``, not counted and forgotten.
    """
    report = LoadReport(step="formula_family_outward")
    # `sent` is the number of inbound edges to mirror, read live. Deliberately not
    # `len(members)` from the artifact: the mirror's contract is with the graph, and
    # reconciling against the artifact would hide a membership pass that landed short.
    report.sent = _count(
        session,
        f"MATCH (:{LABEL_FORMULA})-[r:{REL_MEMBER_OF_FAMILY}]->"
        f"(:{LABEL_FORMULA_FAMILY}) RETURN count(r) AS c",
    )
    if not report.sent:
        return report
    build_pass = uuid.uuid4().hex
    session.run(
        _FAMILY_OUTWARD_QUERY,
        build_pass=build_pass,
        outward_asserts=_OUTWARD_ASSERTS,
    ).consume()
    report.landed = _count(
        session,
        f"MATCH (:{LABEL_FORMULA_FAMILY})-[r:{REL_HAS_FORMULA}]->(:{LABEL_FORMULA}) "
        "WHERE r.build_pass = $build_pass RETURN count(r) AS c",
        build_pass=build_pass,
    )

    # Mark and sweep, for the same reason the membership pass has one: MERGE adds and never
    # retracts, so a membership that disappears upstream must take its mirror with it.
    stale = _count(
        session,
        f"""
        MATCH (:{LABEL_FORMULA_FAMILY})-[r:{REL_HAS_FORMULA}]->(:{LABEL_FORMULA})
        WHERE r.build_pass IS NULL OR r.build_pass <> $build_pass
        DELETE r
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )

    report.detail = {
        "outward_edges": {"sent": report.sent, "landed": report.landed},
        "retired_stale_mirrors": stale,
        # Zero is the only acceptable value and it is reported rather than asserted: a
        # mirror that has lost grading parity with its twin is a silent failure, because
        # both directions still traverse.
        "grading_parity_failures": _count(
            session,
            f"""
            MATCH (f:{LABEL_FORMULA})-[m:{REL_MEMBER_OF_FAMILY}]->
                  (fam:{LABEL_FORMULA_FAMILY})-[h:{REL_HAS_FORMULA}]->(f)
            WHERE h.role <> m.role
               OR h.quality_tier <> m.quality_tier
               OR h.evidence_basis <> m.evidence_basis
               OR h.grade_basis <> m.grade_basis
               OR h.knowledge_layer <> m.knowledge_layer
               OR h.membership_id <> m.membership_id
            RETURN count(*) AS c
            """,
        ),
        "ungraded_mirrors": _count(
            session,
            f"MATCH ()-[r:{REL_HAS_FORMULA}]->() "
            "WHERE r.quality_tier IS NULL OR r.grade_basis IS NULL "
            "RETURN count(r) AS c",
        ),
        "families_reachable_outward": _count(
            session,
            f"MATCH (fam:{LABEL_FORMULA_FAMILY}) "
            f"WHERE (fam)-[:{REL_HAS_FORMULA}]->(:{LABEL_FORMULA}) "
            "RETURN count(fam) AS c",
        ),
        "outward_by_role": {
            record["role"]: record["n"]
            for record in session.run(
                f"MATCH (:{LABEL_FORMULA_FAMILY})-[r:{REL_HAS_FORMULA}]->"
                f"(:{LABEL_FORMULA}) RETURN r.role AS role, count(*) AS n ORDER BY n DESC"
            )
        },
        "outward_by_tier": {
            record["tier"]: record["n"]
            for record in session.run(
                f"MATCH (:{LABEL_FORMULA_FAMILY})-[r:{REL_HAS_FORMULA}]->"
                f"(:{LABEL_FORMULA}) RETURN r.quality_tier AS tier, count(*) AS n "
                "ORDER BY n DESC"
            )
        },
        # The representative is the family's headline and it is stored as a bare id, so a
        # family whose representative is not among its own members would render a label
        # for a formula the family does not contain.
        "representatives_unresolvable": _count(
            session,
            f"""
            MATCH (fam:{LABEL_FORMULA_FAMILY})
            WHERE NOT EXISTS {{
                MATCH (fam)-[:{REL_HAS_FORMULA}]->
                      (rep:{LABEL_FORMULA} {{formula_id: fam.representative_formula_id}})
            }}
            RETURN count(fam) AS c
            """,
        ),
        "counts_block_drift": _counts_block_drift(session),
    }
    return report


#: Which recorded count each role is supposed to summarise. ``secondary_core_count`` and
#: ``expansion_count`` are not checked here: ``SECONDARY_CORE`` is not a stored ``role``
#: value, so the node field and the edge field are not the same partition and a mismatch
#: between them would not be drift.
_FAMILY_COUNT_FIELDS: Final[tuple[tuple[str, str | None], ...]] = (
    ("member_count", None),
    ("core_count", "CORE"),
    ("variant_count", "VARIANT"),
)


def _counts_block_drift(session: Session) -> dict[str, Any]:
    """Compare each family's recorded counts against the edges that actually landed.

    Measured against the outward mirror rather than the inbound edge, because the mirror is
    what a reader who started at the family will count, and the point of the audit is that
    the number on the node and the number a reader gets are the same number.

    Reported per field with the offending ``family_id``s, capped, rather than as a single
    total. "Eight of nine recorded corrections were never written into the data" happened
    in this repository because an audit block was read instead of the rows; a drift report
    that says only *how many* families disagree repeats that mistake one level up.
    """
    out: dict[str, Any] = {}
    for field_name, role in _FAMILY_COUNT_FIELDS:
        role_filter = "" if role is None else " {role: $role}"
        rows = list(
            session.run(
                f"""
                MATCH (fam:{LABEL_FORMULA_FAMILY})
                OPTIONAL MATCH (fam)-[r:{REL_HAS_FORMULA}{role_filter}]->(:{LABEL_FORMULA})
                WITH fam, count(r) AS landed
                WHERE coalesce(fam.{field_name}, -1) <> landed
                RETURN fam.family_id AS family_id,
                       fam.{field_name} AS recorded,
                       landed AS landed
                ORDER BY abs(coalesce(fam.{field_name}, -1) - landed) DESC, family_id
                LIMIT 20
                """,
                role=role,
            )
        )
        out[field_name] = {
            "families_disagreeing": len(rows),
            "examples": [
                {
                    "family_id": record["family_id"],
                    "recorded": record["recorded"],
                    "landed": record["landed"],
                }
                for record in rows
            ],
        }
    return out


def _property_safe(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten the two fields Neo4j cannot hold as properties.

    Neo4j properties are primitives or arrays of primitives, so a map and a list of
    objects both have to be stored as JSON text. The treatment matches
    ``iter_formula_nodes`` exactly, because these rows sit alongside the ``Formula`` nodes
    that function writes and a reader filtering on ``veda_counts`` should not have to know
    which loader produced the node:

    - ``veda_counts`` -- a map -- becomes a JSON string.
    - ``evidence`` -- a list of span objects -- becomes a JSON string, and its length is
      kept alongside as ``evidence_count`` so "how many spans support this?" stays a
      numeric comparison rather than a string parse.
    - ``vedas`` stays a native list, because ``'SV' IN fam.vedas`` is a query somebody
      will write and ``fam.veda_counts CONTAINS '"SV"'`` is not.
    """
    out = dict(row)
    if isinstance(out.get("veda_counts"), dict):
        out["veda_counts"] = orjson.dumps(out["veda_counts"]).decode()
    evidence = out.get("evidence")
    if isinstance(evidence, list):
        out["evidence"] = orjson.dumps(evidence).decode()
        out["evidence_count"] = len(evidence)
    out.setdefault("evidence_count", 0)
    return out


def _collapsed(text: str) -> str:
    """Whitespace-free identity, which is what ``match_level`` claims to compare on."""
    return "".join(str(text).split())


def _annotate_containment(
    members: Sequence[dict[str, Any]], families: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Annotate each member with the two facts its grade depends on.

    **``contains_representative``** -- whether this member directly contains, or is
    contained by, the family's representative. The family is a containment *component*, so
    a member need not: **241 of 2,037 do not** (194 ``CORE``, 43 ``EXPANSION``, 4
    ``VARIANT``). That is not a defect in the grouping, but a reader must be able to see
    it, because "belongs to the same chain of expansions as X" and "is a longer form of X"
    are different claims and only the second is what most people mean by a formula family.

    The 241 here and the 198 quoted in :data:`_MEMBER_BASIS_CASE` are **two different
    populations measured against two different witnesses**, and both numbers are right:
    198 is measured against the formula each edge cites in ``linked_formula_id``, 241
    against the family representative. Keeping them straight matters -- this repository has
    a standing lesson about auditing the witness you actually selected rather than the one
    you assumed.

    **``has_containment_support``** -- whether this member stands in direct containment
    with at least one sibling that is *itself* containment-derived. This exists because of
    a real leak found by testing: grading the four similarity-derived ``VARIANT`` rows
    ``TIER_D`` left one ``EXPANSION`` row at ``TIER_B`` whose *only* containment sibling
    was one of those candidates. Withdraw the candidate and the TIER_B row belongs to no
    component at all -- so its TIER_B was resting on a TIER_D claim, which is exactly the
    transitive trust the tier system exists to prevent. A member with no
    containment-derived support cannot outrank the candidate it depends on.
    """
    representative = {
        str(family["family_id"]): _collapsed(family.get("representative_normalized", ""))
        for family in families
    }
    by_family: dict[str, list[dict[str, Any]]] = {}
    for member in members:
        by_family.setdefault(str(member.get("family_id")), []).append(member)

    annotated: list[dict[str, Any]] = []
    for member in members:
        row = dict(member)
        family_id = str(row.get("family_id"))
        rep = representative.get(family_id, "")
        mine = _collapsed(row.get("normalized", ""))
        direct = bool(rep) and bool(mine) and (mine in rep or rep in mine)
        row["contains_representative"] = direct
        row["containment_is_transitive"] = not direct

        # Siblings that are themselves containment-derived. A similarity-derived sibling
        # is a candidate and cannot license a stronger grade than it holds itself.
        row["has_containment_support"] = any(
            sibling is not member
            and "similarity" not in str(sibling.get("method", ""))
            and (
                _collapsed(sibling.get("normalized", "")) in mine
                or mine in _collapsed(sibling.get("normalized", ""))
            )
            for sibling in by_family.get(family_id, ())
            if _collapsed(sibling.get("normalized", ""))
        )
        annotated.append(row)
    return annotated


def load_formula_families(
    session: Session,
    families: Sequence[dict[str, Any]],
    members: Sequence[dict[str, Any]],
) -> LoadReport:
    """Land the ``FormulaFamily`` layer over the existing flat ``Formula`` nodes.

    Membership is component membership under containment on the surface that already
    defines ``formula_id``: transitive, decidable, and recomputable from the graph's own
    data by anyone who doubts it. That earns ``TIER_B`` for the 2,033 containment-derived
    rows. It is deliberately *not* the claim that each member contains the family's
    representative -- 198 do not -- and ``contains_representative`` carries that per row
    so the stronger subset stays filterable. The four similarity-derived ``VARIANT`` rows
    rest on a chosen threshold instead of a decidable relation and are graded ``TIER_D``.
    See :data:`_MEMBER_BASIS_CASE` for the measurement behind both decisions.

    The layer is *additive*. Not one ``Formula`` node or ``USES_FORMULA`` edge is touched,
    and the 2,788 formulas in no family keep working exactly as before. That is deliberate:
    a passage's formula list is a statement about the passage, and rewriting it to point at
    families would replace a measured fact with a derived one. The family is a second way
    in, reached from the formula.
    """
    report = LoadReport(step="formula_families", sent=len(families) + len(members))
    if not families:
        return report
    build_pass = uuid.uuid4().hex
    tier = "TIER_B"

    for batch in _batches([_property_safe(row) for row in families]):
        session.run(_FAMILY_NODE_QUERY, rows=batch, tier=tier, build_pass=build_pass)
    annotated = _annotate_containment(members, families)
    for batch in _batches([_property_safe(row) for row in annotated]):
        session.run(
            _FAMILY_MEMBER_QUERY,
            rows=batch,
            build_pass=build_pass,
            member_asserts=_MEMBER_ASSERTS,
        )

    family_nodes = _count(
        session,
        f"MATCH (fam:{LABEL_FORMULA_FAMILY}) WHERE fam.build_pass = $build_pass "
        "RETURN count(fam) AS c",
        build_pass=build_pass,
    )
    member_edges = _count(
        session,
        f"MATCH (:{LABEL_FORMULA})-[r:{REL_MEMBER_OF_FAMILY}]->"
        f"(:{LABEL_FORMULA_FAMILY}) WHERE r.build_pass = $build_pass "
        "RETURN count(r) AS c",
        build_pass=build_pass,
    )
    report.landed = family_nodes + member_edges

    # Mark and sweep. A family that stops being derived, or a member that moves families,
    # must disappear rather than linger: MERGE adds and never retracts, so without this
    # a rebuilt layer would be the union of every layer ever built.
    stale_edges = _count(
        session,
        f"""
        MATCH (:{LABEL_FORMULA})-[r:{REL_MEMBER_OF_FAMILY}]->(:{LABEL_FORMULA_FAMILY})
        WHERE r.build_pass IS NULL OR r.build_pass <> $build_pass
        DELETE r
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    stale_nodes = _count(
        session,
        f"""
        MATCH (fam:{LABEL_FORMULA_FAMILY})
        WHERE fam.build_pass IS NULL OR fam.build_pass <> $build_pass
        DETACH DELETE fam
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    report.detail = {
        "family_nodes": {"sent": len(families), "landed": family_nodes},
        "member_edges": {"sent": len(members), "landed": member_edges},
        "retired_stale_edges": stale_edges,
        "retired_stale_nodes": stale_nodes,
        "members_by_role": {
            record["role"]: record["n"]
            for record in session.run(
                f"MATCH ()-[r:{REL_MEMBER_OF_FAMILY}]->() "
                "RETURN r.role AS role, count(*) AS n ORDER BY n DESC"
            )
        },
        "members_by_tier": {
            record["tier"]: record["n"]
            for record in session.run(
                f"MATCH ()-[r:{REL_MEMBER_OF_FAMILY}]->() "
                "RETURN r.quality_tier AS tier, count(*) AS n ORDER BY n DESC"
            )
        },
        # Reported because it is the number the containment claim turns on, and a silent
        # drift in it means the grouping method changed underneath the grade.
        "members_containing_representative": _count(
            session,
            f"MATCH ()-[r:{REL_MEMBER_OF_FAMILY}]->() "
            "WHERE r.contains_representative RETURN count(r) AS c",
        ),
        "members_transitive_only": _count(
            session,
            f"MATCH ()-[r:{REL_MEMBER_OF_FAMILY}]->() "
            "WHERE r.containment_is_transitive RETURN count(r) AS c",
        ),
        "formulas_unfamilied": _count(
            session,
            f"MATCH (f:{LABEL_FORMULA}) "
            f"WHERE NOT (f)-[:{REL_MEMBER_OF_FAMILY}]->() RETURN count(f) AS c",
        ),
        "cross_veda_families": _count(
            session,
            f"MATCH (fam:{LABEL_FORMULA_FAMILY}) WHERE fam.cross_veda RETURN count(fam) AS c",
        ),
    }
    return report


# ---------------------------------------------------------------------------
# Ṛṣi families
# ---------------------------------------------------------------------------

_RISHI_FAMILY_NODE_QUERY = f"""
UNWIND $rows AS row
MERGE (fam:{LABEL_RISHI_FAMILY} {{family_key: row.family_key}})
SET fam.display_label = row.display_label,
    fam.display_type = 'RishiFamily',
    fam.patronymic_iast = row.patronymic_iast,
    fam.eponym_iast = row.eponym_iast,
    fam.vrddhi_derivation = row.vrddhi_derivation,
    fam.source_variants = row.source_variants,
    fam.member_count = row.member_count,
    fam.namespaces = row.namespaces,
    fam.derivation_method = $derivation_method,
    fam.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
    fam.quality_tier = 'TIER_B',
    fam.evidence_basis = 'SOURCE_METADATA',
    fam.grade_basis =
      'one Anukramaṇī-stated vṛddhi patronymic, matched by equality against a ' +
      'hand-listed table of stems and their eponyms; recomputable from the registry',
    fam.build_pass = $build_pass
"""

#: The two derivations are recorded separately on the edge because they are not equally
#: direct, even though both are deterministic and both earn ``TIER_B``. Token equality
#: reads a patronymic the Anukramaṇī printed as its own word. A fused split reads one the
#: Anukramaṇī printed joined to the personal name by sandhi, so the *word boundary* is
#: supplied by this layer rather than by the source. All 16 splits over the three
#: registries were checked individually and all 16 were right -- but "checked by hand once"
#: is a different warrant from "printed as a separate word", and a reader filtering for
#: the stronger evidence must be able to.
_RISHI_MEMBER_BASIS_CASE: Final = """CASE row.method
      WHEN 'patronymic-token-equality-v1'
        THEN 'the source prints this patronymic as its own word; membership is equality ' +
             'against a hand-listed stem table, no similarity and no prefix matching'
      WHEN 'patronymic-fused-token-split-v1'
        THEN 'the source prints the patronymic fused to the personal name by sandhi; ' +
             'the word boundary is supplied by this layer, the patronymic surface is not'
      ELSE 'the label states descent in words (a -putra compound) rather than by vṛddhi'
    END"""

_RISHI_MEMBER_QUERY = f"""
UNWIND $rows AS row
MATCH (r:{LABEL_RISHI} {{entity_key: row.entity_key}})
MATCH (fam:{LABEL_RISHI_FAMILY} {{family_key: row.family_key}})
MERGE (r)-[m:{REL_BELONGS_TO_FAMILY}]->(fam)
SET m.source_label = row.source_label,
    m.source_token = row.source_token,
    m.evidence = row.source_label,
    m.evidence_count = 1,
    m.patronymic_iast = row.family_stem,
    m.derivation = row.derivation,
    m.method = row.method,
    m.registry_namespace = row.namespace,
    m.source_id = row.source_id,
    m.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
    m.quality_tier = 'TIER_B',
    m.evidence_basis = 'SOURCE_METADATA',
    m.provenance_class = 'SOURCE_DERIVED_SCOPE',
    m.attribution_precision = 'NOT_AN_ATTRIBUTION',
    m.scope_origin = 'SUKTA_WIDE',
    m.confidence = 1.0,
    m.grade_basis = {_RISHI_MEMBER_BASIS_CASE},
    m.asserts = $member_asserts,
    m.build_pass = $build_pass
"""

#: ``attribution_precision = 'NOT_AN_ATTRIBUTION'`` since V3.2, and the safeguard that the
#: old value was standing in for now rests on ``scope_origin`` where it belongs.
#:
#: Neither endpoint of this edge is a passage, so the axis does not apply and this used to
#: read ``CONTAINER_INHERITED`` -- chosen, in as many words, because "the invariant that
#: every edge in this graph carries full grading metadata wins, and once the property has
#: to hold *something* the only safe value is the inherited one". That argument was sound
#: and its conclusion was still false: it minted an inheritance claim about a container
#: this edge does not have. The sentinel is the option it was missing. The invariant is
#: kept in full, and nothing has to be asserted to keep it.
#:
#: **The safeguard is not lost, and this is the part worth checking rather than trusting.**
#: The reason the weaker value was wanted is that a ``Passage -> HAS_RISHI -> Rishi ->
#: BELONGS_TO_FAMILY -> RishiFamily`` walk can never be more precise than the sūkta-wide
#: attribution it starts from. That fact is carried by ``scope_origin = 'SUKTA_WIDE'``,
#: which every one of the 305 edges holds and which this change does not touch. Every one
#: of the three ṛṣi indices states its patronymic at
#: **container** level and never inside a verse: the Ṛgvedic Sarvānukramaṇī labels a sūkta
#: (10,093 of the RV's 10,565 ``HAS_RISHI`` edges are inherited), the Atharvavedic index
#: labels a sūkta in **all** 5,084 cases, and the Yajurvedic ṛṣisūcī is an index over the
#: whole Vājasaneyi Saṁhitā. So a leaderboard that walks Passage -> HAS_RISHI -> Rishi ->
#: BELONGS_TO_FAMILY can never be more precise than sūkta-wide, and stamping
#: ``PER_PASSAGE`` here would let a query advertising per-verse strictness quietly include
#: container-inherited evidence. ``scope_origin = 'SUKTA_WIDE'`` records the same fact in
#: the vocabulary ``PRECISION_BY_SCOPE_ORIGIN`` maps from, so the two cannot drift apart.
_RISHI_MEMBER_ASSERTS: Final = (
    "The Anukramaṇī states this patronymic for this seer, so he is of this gotra. It does "
    "NOT assert a generation, a birth order, or that two ṛṣis carrying one patronymic in "
    "different Vedas are the same man."
)

#: The Q2 decomposition, written onto the ``Rishi`` node itself rather than onto the
#: membership edge, because it is true of the *label* whether or not a family was created:
#: 57 theonymic and 14 titular patronymics are decomposed here and deliberately reify no
#: family. Q2's acceptance criterion asks for the seer name split into patronymic and
#: personal name, and half of that answer would be missing if it lived only on edges.
_RISHI_DECOMPOSITION_QUERY = f"""
UNWIND $rows AS row
MATCH (r:{LABEL_RISHI} {{entity_key: row.entity_key}})
SET r.patronymics_iast = row.patronymics,
    r.personal_names_iast = row.personal_names,
    r.patronymic_iast =
      CASE WHEN size(row.patronymics) > 0 THEN row.patronymics[0] ELSE null END,
    r.personal_name_iast =
      CASE WHEN size(row.personal_names) > 0 THEN row.personal_names[0] ELSE null END,
    r.decomposition_method = row.method,
    r.family_assignment_class = row.unassigned_class,
    r.non_seer_kind = row.non_seer_kind,
    r.is_seer = row.non_seer_kind IS NULL,
    r.decomposition_build_pass = $build_pass
"""

#: ``is_seer`` exists because a measured defect needed it: the strict per-passage ṛṣi
#: leaderboard's rank-1 entry was ``devāḥ`` -- "the gods" -- so a query enumerating the
#: Ṛgveda's most prolific poets was returning a deity group first. 113 of the 729 registry
#: rows are not people at all (deities, deity groups, abstractions, mythic beings, two
#: animals, an offering-ladle and the Atharvavedic hymn-class ``cātana``), and no property
#: on the node said so. It is stored as a boolean *and* as ``non_seer_kind`` so a query can
#: either exclude them in one predicate or ask what they are; the ṛṣi rows are **not**
#: deleted, because the tradition really does ascribe those hymns to those beings and
#: deleting the ascription would remove a true fact about the corpus.


def load_rishi_families(
    session: Session,
    families: Sequence[dict[str, Any]],
    memberships: Sequence[dict[str, Any]],
    decompositions: Sequence[dict[str, Any]],
) -> LoadReport:
    """Land the ``RishiFamily`` layer over the 729 existing ``Rishi`` nodes.

    Additive over ``Rishi``: not one node is created here and not one ``HAS_RISHI`` edge
    is touched. Every ``MATCH`` is on a label *and* a pinned ``entity_key``, which is not
    stylistic -- an unlabelled ``MATCH`` in a mutation once created 39,461 bogus edges in
    this graph, and a ``Rishi`` matched by name rather than key would silently pick up the
    Yajurvedic homonym of a Ṛgvedic seer and assert they are one man.

    ``sent`` counts family nodes plus membership edges plus decomposed ``Rishi`` nodes,
    and ``landed`` re-counts all three from the graph by ``build_pass`` rather than
    trusting the driver's summary counters: a loader in this repository has reported
    success while landing nothing, and a MERGE that finds an existing row reports no
    counter at all.

    The decomposition pass writes to *every* ṛṣi, including the 426 with no family, so
    that ``family_assignment_class`` is present on all 729 and "why does this seer have no
    family?" is answerable from the node instead of from a report file.
    """
    report = LoadReport(
        step="rishi_families",
        sent=len(families) + len(memberships) + len(decompositions),
    )
    if not families:
        return report
    build_pass = uuid.uuid4().hex
    derivation_method = "anukramani-patronymic-v1"

    for batch in _batches(list(families)):
        session.run(
            _RISHI_FAMILY_NODE_QUERY,
            rows=batch,
            build_pass=build_pass,
            derivation_method=derivation_method,
        )
    for batch in _batches(list(memberships)):
        session.run(
            _RISHI_MEMBER_QUERY,
            rows=batch,
            build_pass=build_pass,
            member_asserts=_RISHI_MEMBER_ASSERTS,
        )
    for batch in _batches(list(decompositions)):
        session.run(_RISHI_DECOMPOSITION_QUERY, rows=batch, build_pass=build_pass)

    family_nodes = _count(
        session,
        f"MATCH (fam:{LABEL_RISHI_FAMILY}) WHERE fam.build_pass = $build_pass "
        "RETURN count(fam) AS c",
        build_pass=build_pass,
    )
    member_edges = _count(
        session,
        f"MATCH (:{LABEL_RISHI})-[m:{REL_BELONGS_TO_FAMILY}]->(:{LABEL_RISHI_FAMILY}) "
        "WHERE m.build_pass = $build_pass RETURN count(m) AS c",
        build_pass=build_pass,
    )
    decomposed = _count(
        session,
        f"MATCH (r:{LABEL_RISHI}) WHERE r.decomposition_build_pass = $build_pass "
        "RETURN count(r) AS c",
        build_pass=build_pass,
    )
    report.landed = family_nodes + member_edges + decomposed

    # Mark and sweep. A patronymic removed from the table, or a stem whose reading
    # changed, has to *disappear*: MERGE adds and never retracts, so without this a
    # rebuilt layer would be the union of every table this project ever had -- and the one
    # thing a deliberately conservative layer must not do is accumulate the memberships it
    # later decided it could not support.
    stale_edges = _count(
        session,
        f"""
        MATCH (:{LABEL_RISHI})-[m:{REL_BELONGS_TO_FAMILY}]->(:{LABEL_RISHI_FAMILY})
        WHERE m.build_pass IS NULL OR m.build_pass <> $build_pass
        DELETE m
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )
    stale_nodes = _count(
        session,
        f"""
        MATCH (fam:{LABEL_RISHI_FAMILY})
        WHERE fam.build_pass IS NULL OR fam.build_pass <> $build_pass
        DETACH DELETE fam
        RETURN count(*) AS c
        """,
        build_pass=build_pass,
    )

    report.detail = {
        "build_pass": build_pass,
        "family_nodes": family_nodes,
        "membership_edges": member_edges,
        "rishis_decomposed": decomposed,
        "stale_edges_deleted": stale_edges,
        "stale_families_deleted": stale_nodes,
        # The denominator, reported next to the numerator so coverage cannot be quoted
        # without it. 729 ṛṣis exist; a minority of them state a gotra patronymic.
        "rishi_nodes": _count(session, f"MATCH (r:{LABEL_RISHI}) RETURN count(r) AS c"),
        "rishis_with_a_family": _count(
            session,
            f"MATCH (r:{LABEL_RISHI}) WHERE (r)-[:{REL_BELONGS_TO_FAMILY}]->() "
            "RETURN count(r) AS c",
        ),
        # Per method, because the fused split is the weaker of the two derivations and its
        # count is the number a sceptical reader should want to see.
        "memberships_by_method": {
            method: _count(
                session,
                f"MATCH ()-[m:{REL_BELONGS_TO_FAMILY}]->() WHERE m.method = $method "
                "RETURN count(m) AS c",
                method=method,
            )
            for method in sorted({str(row["method"]) for row in memberships})
        },
        # The graph-wide invariant this layer must not break: every edge carries full
        # grading metadata. Measured on this layer's own edges, after the write.
        "edges_missing_grading": _count(
            session,
            f"MATCH ()-[m:{REL_BELONGS_TO_FAMILY}]->() "
            "WHERE m.quality_tier IS NULL OR m.knowledge_layer IS NULL "
            "OR m.grade_basis IS NULL OR m.evidence_basis IS NULL "
            "RETURN count(m) AS c",
        ),
    }
    return report
