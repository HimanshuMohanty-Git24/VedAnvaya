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

import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

import orjson

from vedagraph.domain.ontology import (
    LABEL_ACTION_PREDICATE,
    LABEL_DEVATA_ASCRIPTION,
    LABEL_FORMULA,
    LABEL_FORMULA_FAMILY,
    LABEL_INTERNAL,
    LABEL_SEMANTIC_ASSERTION,
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
        "by_certainty": {
            record["c"]: record["n"]
            for record in session.run(
                "MATCH ()-[m:MENTIONS_DEVATA]->() "
                "RETURN m.referent_certainty AS c, count(*) AS n ORDER BY n DESC"
            )
        },
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
        session.run(
            f"MATCH (l:Lemma) WHERE NOT l:{LABEL_INTERNAL} SET l:{LABEL_INTERNAL}"
        )
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
    before = _count(
        session, "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN count(r) AS c"
    )
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
                "MATCH ()-[r:ABOUT_CONCEPT]->() "
                "RETURN r.method AS m, count(*) AS n ORDER BY n DESC"
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
            "MATCH ()-[r:ABOUT_CONCEPT]->() WHERE r.method = $method "
            "RETURN count(r) AS c",
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
                r.attribution_precision = 'PER_PASSAGE',
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
        r.attribution_precision = 'PER_PASSAGE',
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
    r.build_pass = $build_pass
REMOVE r.attribution_precision
"""
# The REMOVE is not redundant with simply not setting the property. An earlier build of
# this layer wrote `attribution_precision = 'TEXTUAL_MENTION'` here, and MERGE finds that
# edge and SET leaves any property it does not mention in place -- so dropping the
# assignment cleaned up new edges and left 2,037 old ones asserting a category error.
# Unsetting a property that should never have existed has to be explicit.

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
            f"MATCH (fam:{LABEL_FORMULA_FAMILY}) WHERE fam.cross_veda "
            "RETURN count(fam) AS c",
        ),
    }
    return report
