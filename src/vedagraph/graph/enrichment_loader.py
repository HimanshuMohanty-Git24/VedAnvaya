"""Batched MERGE of the enrichment layer into Neo4j.

Reads the flat rows produced by :mod:`vedagraph.graph.enrichment` and writes them, in
batches of 500, with the same ``UNWIND $rows AS row`` shape the corpus loader uses. Four
properties of this module are load-bearing and each of them exists because the obvious
implementation is wrong in a way that is hard to see afterwards.

**A relationship type never comes from a data file.**
Cypher cannot parameterise a relationship type, so a loader handling twenty-odd predicates
is under constant pressure to build the query with an f-string over a value it read off
disk. That is a Cypher injection: a crafted ``predicate`` field would write an arbitrary
type, and with a closing brace it would write arbitrary Cypher. Instead every query in
this module is generated *at import time* from the frozen enums in
:mod:`vedagraph.enrich.predicates`, checked against
:data:`~vedagraph.enrich.predicates.CONTROLLED_PREDICATES` and against a strict identifier
pattern as it is generated, and stored in a dict. At load time a row's predicate is only
ever used as a **dict key**. A predicate the tables do not contain raises
:class:`UncontrolledPredicateError` and aborts the load. There is no code path from a file
to a query string.

**Enrichment edges never overwrite the lexical layer's.**
``EXACT_PARALLEL_OF`` and ``PARALLEL_TO`` already exist in the graph from the
within-Rigveda lexical layer (256 and 69 edges). This layer writes ``EXACT_PARALLEL_OF``
too, and that is intended -- the claim is the same claim. But a bare
``MERGE (a)-[r:EXACT_PARALLEL_OF]->(b)`` would match an existing lexical edge and then
``SET`` the enrichment envelope over it, destroying ``methods``, ``strongest_method`` and
``status`` with no error and no way to tell afterwards. So ``pipeline_version`` is part of
the MERGE pattern::

    MERGE (a)-[r:EXACT_PARALLEL_OF {pipeline_version: row.pipeline_version}]->(b)

The lexical edges have no ``pipeline_version`` property at all, so the pattern cannot
match them, and where both layers assert the same pair the graph holds two edges that each
say who found it. Separating them in a query is one predicate::

    MATCH ()-[r:EXACT_PARALLEL_OF]->()
    WHERE r.pipeline_version = 'vedagraph-graph-enrichment-v1'   // enrichment layer
    // ... or: WHERE r.pipeline_version IS NULL                  // lexical layer

``run_id`` narrows further, to one build of that layer. It is deliberately *not* in the
MERGE key: keying on it would make every re-run create a fresh parallel edge set.

**Counts are distinct edges, not rows read.**
Every merge query ends ``RETURN count(DISTINCT r) AS merged`` and the reported number is
what the database says it wrote, not what the loader sent. Rows are de-duplicated on
``(predicate, subject_key, object_key)`` before batching, so a count taken from the input
would exceed the edge count whenever the artifacts contain a duplicate pair -- which they
legitimately do -- and the difference reads as silently lost edges. The corpus loader
learned this the same way: see ``_merge_rdc_rels``'s note about a phantom four-edge
shortfall.

**A row whose endpoints are missing is counted, never dropped.**
``MATCH ... MATCH ... MERGE`` silently produces nothing when either endpoint is absent, so
the difference between the batch size and the returned merge count is exactly the number
of rows that found no endpoint. That difference is accumulated per predicate and returned
in the result dict under ``unmatched_<PREDICATE>``. Missing endpoints are expected and
informative -- a semantic candidate naming a concept the lexicon does not define, a
parallel against a Veda that has not been loaded -- and the number is the honest measure
of what the enrichment layer is not showing.
"""

from __future__ import annotations

import logging
import pathlib
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.enrich.predicates import (
    CONTROLLED_PREDICATES,
    REFUSED_PREDICATES,
    SEMANTIC_PREDICATES,
    StructuralPredicate,
    TextualPredicate,
)
from vedagraph.semantic.ontology import SemanticNodeType

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


class UncontrolledPredicateError(ValueError):
    """An artifact named a relationship type this layer is not permitted to write.

    Raised rather than logged and skipped. A stage that emits an unknown predicate
    disagrees with the frozen vocabulary about what this layer is, and continuing would
    produce a graph that is missing edges nobody counted while looking complete. The
    corpus loader's ``logger.warning`` and ``continue`` is the right call for a *known*
    type appearing in the wrong file; it is the wrong call for a name that does not exist.
    """


class UnknownObjectKindError(ValueError):
    """A semantic candidate named an object kind with no label to match it against."""


# ---------------------------------------------------------------------------
# Query construction. Everything below runs at import time, from the enums.
# ---------------------------------------------------------------------------

#: A Neo4j relationship type, spelled the way this project spells them. Predicates are
#: already restricted to a frozen set, so this is redundant -- and it is here anyway,
#: because it is the check that holds if a future edit ever builds a table from something
#: less trustworthy than an enum. Anchored with \A and \Z rather than ^ and $, which in
#: Python also match at a newline and would accept "SAFE\nDETACH DELETE".
_REL_TYPE_PATTERN: Final = re.compile(r"\A[A-Z][A-Z0-9_]{0,62}\Z")


def _relationship_type(predicate: str) -> str:
    """Validate ``predicate`` as a relationship type, or refuse to produce one."""
    if predicate not in CONTROLLED_PREDICATES:
        reason = REFUSED_PREDICATES.get(predicate)
        detail = f": {reason}" if reason else ""
        raise UncontrolledPredicateError(
            f"{predicate!r} is not a controlled enrichment predicate{detail}"
        )
    if not _REL_TYPE_PATTERN.match(predicate):
        raise UncontrolledPredicateError(
            f"{predicate!r} is in the controlled set but is not a legal relationship type"
        )
    return predicate


#: The provenance envelope, written on every enrichment relationship. Ten properties, the
#: same ten ``Provenance.as_edge_properties`` produces, so "why are these connected?" is
#: answerable from the edge alone with no second lookup and no join.
_PROVENANCE_ASSIGNMENTS: Final[tuple[str, ...]] = (
    "r.trust = row.trust",
    "r.method = row.method",
    "r.score = row.score",
    "r.evidence = row.evidence",
    "r.evidence_count = row.evidence_count",
    "r.state = row.state",
    "r.pipeline_version = row.pipeline_version",
    "r.run_id = row.run_id",
    "r.model = row.model",
    "r.prompt_policy = row.prompt_policy",
)

_PASSAGE_SUBJECT: Final = "(a:Passage {canonical_key: row.subject_key})"
_PASSAGE_OBJECT: Final = "(b:Passage {canonical_key: row.object_key})"
_FORMULA_OBJECT: Final = "(b:Formula {formula_id: row.object_key})"
_CONCEPT_SUBJECT: Final = "(a:Concept {concept_id: row.subject_key})"
_CONCEPT_OBJECT: Final = "(b:Concept {concept_id: row.object_key})"
_DEVATA_SUBJECT: Final = "(a:Devata {entity_key: row.subject_key})"
_DEVATA_OBJECT: Final = "(b:Devata {entity_key: row.object_key})"


def _rel_query(rel_type: str, subject: str, object_: str, extra: Iterable[str] = ()) -> str:
    """Build one batched MERGE query for a validated relationship type.

    ``rel_type`` goes through :func:`_relationship_type` here rather than at the call site,
    so that no caller in this module can construct a query without the check.
    ``pipeline_version`` is inside the MERGE pattern; see the module docstring.
    """
    checked = _relationship_type(rel_type)
    assignments = [f"r.{name} = row.{name}" for name in extra]
    assignments.extend(_PROVENANCE_ASSIGNMENTS)
    set_clause = ",\n            ".join(assignments)
    return f"""
        UNWIND $rows AS row
        MATCH {subject}
        MATCH {object_}
        MERGE (a)-[r:{checked} {{pipeline_version: row.pipeline_version}}]->(b)
        SET {set_clause}
        RETURN count(DISTINCT r) AS merged
    """


_PARALLEL_EDGE_PROPERTIES: Final[tuple[str, ...]] = (
    "parallel_id",
    "subject_veda",
    "object_veda",
    "veda_pair",
    "match_level",
    "levels_reached",
    "similarity",
    "token_jaccard",
    "ngram_jaccard",
    "lcs_ratio",
    "edit_ratio",
)

#: Passage-to-Passage parallels, one query per textual predicate. Keyed by the predicate
#: string; the key is the only thing a data file ever supplies.
_PARALLEL_QUERIES: Final[dict[str, str]] = {
    str(predicate): _rel_query(
        str(predicate), _PASSAGE_SUBJECT, _PASSAGE_OBJECT, _PARALLEL_EDGE_PROPERTIES
    )
    for predicate in TextualPredicate
}

_USES_FORMULA_QUERIES: Final[dict[str, str]] = {
    str(StructuralPredicate.USES_FORMULA): _rel_query(
        str(StructuralPredicate.USES_FORMULA),
        _PASSAGE_SUBJECT,
        _FORMULA_OBJECT,
        ("veda", "source_form"),
    )
}

_BROADER_QUERIES: Final[dict[str, str]] = {
    str(StructuralPredicate.BROADER_THAN): _rel_query(
        str(StructuralPredicate.BROADER_THAN), _CONCEPT_SUBJECT, _CONCEPT_OBJECT
    )
}

_DEVATA_CONCEPT_QUERIES: Final[dict[str, str]] = {
    str(StructuralPredicate.DEVATA_ASSOCIATED_WITH): _rel_query(
        str(StructuralPredicate.DEVATA_ASSOCIATED_WITH), _DEVATA_SUBJECT, _CONCEPT_OBJECT
    )
}

_ABOUT_CONCEPT_QUERIES: Final[dict[str, str]] = {
    str(StructuralPredicate.ABOUT_CONCEPT): _rel_query(
        str(StructuralPredicate.ABOUT_CONCEPT),
        _PASSAGE_SUBJECT,
        _CONCEPT_OBJECT,
        ("assertion_id", "veda", "confidence"),
    )
}

_SEMANTIC_EDGE_PROPERTIES: Final[tuple[str, ...]] = (
    "candidate_id",
    "veda",
    "confidence",
    "object_kind",
    "object_label",
)

#: Semantic candidates are routed by predicate *and* by object label, because the same
#: predicate can point at a Concept or at a registry Devata and the two are matched on
#: different properties. The composite key keeps the injection guarantee intact: it is
#: still a dict lookup, and both halves are validated before they reach it.
_SEMANTIC_QUERIES: Final[dict[str, str]] = {
    f"{predicate}|{label}": _rel_query(
        predicate, _PASSAGE_SUBJECT, object_pattern, _SEMANTIC_EDGE_PROPERTIES
    )
    for predicate in (str(p) for p in SEMANTIC_PREDICATES)
    for label, object_pattern in (("Concept", _CONCEPT_OBJECT), ("Devata", _DEVATA_OBJECT))
}

#: Which node label a semantic candidate's ``object_kind`` resolves to. Every
#: ``SemanticNodeType`` is a Concept -- the frozen ontology has no deity type and files
#: gods under ``COSMIC_ENTITY`` -- and ``DEVATA`` is accepted for a proposal that names a
#: registry deity directly. Unrecognised kinds raise rather than defaulting to Concept: a
#: default here would attach an edge to the wrong label and report it as a success.
_OBJECT_LABELS: Final[dict[str, str]] = {
    **{str(node_type): "Concept" for node_type in SemanticNodeType},
    "CONCEPT": "Concept",
    "DEVATA": "Devata",
}


def _semantic_group(row: dict[str, Any]) -> str:
    kind = str(row.get("object_kind", "")).upper()
    label = _OBJECT_LABELS.get(kind)
    if label is None:
        raise UnknownObjectKindError(
            f"semantic candidate {row.get('candidate_id', '')!r} names object_kind "
            f"{row.get('object_kind', '')!r}, which resolves to no node label; "
            f"known kinds: {sorted(_OBJECT_LABELS)}"
        )
    return f"{row.get('predicate', '')}|{label}"


def _predicate_group(row: dict[str, Any]) -> str:
    return str(row.get("predicate", ""))


# ---------------------------------------------------------------------------
# Batched merge engine
# ---------------------------------------------------------------------------


def _batched(it: Iterator[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for item in it:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


@dataclass
class RelMergeResult:
    """What one relationship artifact actually did, per predicate.

    ``merged`` is distinct edges in the database. ``unmatched`` is rows whose subject or
    object node was not found. ``duplicate_rows`` is rows collapsed by de-duplication
    before they were sent. The three together account for every row read, which is the
    property that makes the load auditable: ``merged + unmatched + duplicate_rows`` equals
    the row count of the artifact, and any other arithmetic means a row went missing.
    """

    merged: dict[str, int] = field(default_factory=dict)
    unmatched: dict[str, int] = field(default_factory=dict)
    duplicate_rows: dict[str, int] = field(default_factory=dict)

    @property
    def total_merged(self) -> int:
        return sum(self.merged.values())

    @property
    def total_unmatched(self) -> int:
        return sum(self.unmatched.values())


def _merged_count(result: Any) -> int:
    """Read ``count(DISTINCT r)`` back out of a driver result.

    Tolerates a result with no records, which a driver may produce for a batch that
    matched nothing, and treats a null aggregate as zero. Never falls back to the batch
    size: the whole point of asking the database is that its answer is the one that counts.
    """
    total = 0
    for record in result:
        value = record["merged"]
        if value is not None:
            total += int(value)
    return total


def _merge_grouped_rels(
    session: Any,
    rows: Iterator[dict[str, Any]],
    queries: dict[str, str],
    artifact: str,
    group_of: Callable[[dict[str, Any]], str] = _predicate_group,
) -> RelMergeResult:
    """Merge relationship rows, grouped so each group runs its own pre-built query.

    The grouping exists because a relationship type cannot be a parameter: rows have to be
    partitioned by type and each partition run against the query built for that type. The
    group key is looked up, never interpolated. A key the table does not contain is fatal
    -- either the predicate is outside the controlled vocabulary, or it is a controlled
    predicate appearing in an artifact that has no query for it, and both are writer bugs
    that a warning would let through.

    Rows stream, so an artifact with a bad predicate past the first batch boundary will
    have written the batches before it by the time the raise happens. That is a
    transaction-scope question, not a vocabulary one -- run the load inside an explicit
    transaction if a partial write is unacceptable -- and it does not weaken the guarantee
    that matters: the offending predicate never becomes part of a query.
    """
    result = RelMergeResult()
    seen: set[tuple[str, str, str]] = set()
    batches: dict[str, list[dict[str, Any]]] = {}

    def flush(group: str) -> None:
        batch = batches.get(group)
        if not batch:
            return
        merged = _merged_count(session.run(queries[group], rows=batch))
        result.merged[group] = result.merged.get(group, 0) + merged
        result.unmatched[group] = result.unmatched.get(group, 0) + (len(batch) - merged)
        batches[group] = []

    for row in rows:
        group = group_of(row)
        if group not in queries:
            predicate = str(row.get("predicate", ""))
            if predicate not in CONTROLLED_PREDICATES:
                reason = REFUSED_PREDICATES.get(predicate)
                detail = f": {reason}" if reason else ""
                raise UncontrolledPredicateError(
                    f"{artifact}: {predicate!r} is not a controlled enrichment "
                    f"predicate{detail}"
                )
            raise UncontrolledPredicateError(
                f"{artifact}: {predicate!r} is a controlled predicate but has no loader "
                f"query in this artifact (resolved group {group!r}); "
                f"expected one of {sorted(queries)}"
            )
        key = (group, str(row["subject_key"]), str(row["object_key"]))
        if key in seen:
            result.duplicate_rows[group] = result.duplicate_rows.get(group, 0) + 1
            continue
        seen.add(key)
        result.merged.setdefault(group, 0)
        result.unmatched.setdefault(group, 0)
        batches.setdefault(group, []).append(row)
        if len(batches[group]) >= _BATCH_SIZE:
            flush(group)

    for group in list(batches):
        flush(group)

    for group, count in sorted(result.merged.items()):
        logger.info(
            "%s: merged %d %s edges (%d unmatched, %d duplicate rows collapsed)",
            artifact,
            count,
            group,
            result.unmatched.get(group, 0),
            result.duplicate_rows.get(group, 0),
        )
    return result


def _merge_nodes(
    session: Any,
    rows: Iterator[dict[str, Any]],
    query: str,
    id_field: str,
    label: str,
) -> tuple[int, int]:
    """Merge node rows, returning ``(distinct nodes, duplicate rows collapsed)``.

    De-duplicated on the identity field for the same reason the relationship merge is:
    the reported count has to be the number of nodes in the database, so that a later
    ``MATCH (n:Formula) RETURN count(n)`` agrees with the load report instead of prompting
    a hunt for the difference.
    """
    seen: set[str] = set()
    distinct = 0
    duplicates = 0

    def _unique() -> Iterator[dict[str, Any]]:
        nonlocal distinct, duplicates
        for row in rows:
            identity = str(row[id_field])
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            distinct += 1
            yield row

    for batch in _batched(_unique(), _BATCH_SIZE):
        session.run(query, rows=batch)
    logger.info("Merged %d %s nodes (%d duplicate rows collapsed)", distinct, label, duplicates)
    return distinct, duplicates


_CONCEPT_NODE_QUERY: Final = """
    UNWIND $rows AS row
    MERGE (c:Concept {concept_id: row.concept_id})
    SET c.preferred_label_sa = row.preferred_label_sa,
        c.preferred_label_en = row.preferred_label_en,
        c.node_type = row.node_type,
        c.aliases_sa = row.aliases_sa,
        c.aliases_en = row.aliases_en,
        c.definition = row.definition
"""

_FORMULA_NODE_QUERY: Final = """
    UNWIND $rows AS row
    MERGE (f:Formula {formula_id: row.formula_id})
    SET f.normalized = row.normalized,
        f.display_form = row.display_form,
        f.word_count = row.word_count,
        f.char_count = row.char_count,
        f.occurrence_count = row.occurrence_count,
        f.mantra_count = row.mantra_count,
        f.vedas = row.vedas,
        f.veda_counts = row.veda_counts,
        f.cross_veda = row.cross_veda,
        f.source_forms = row.source_forms,
        f.derivation_method = row.derivation_method,
        f.trust = row.trust,
        f.method = row.method,
        f.score = row.score,
        f.evidence = row.evidence,
        f.evidence_count = row.evidence_count,
        f.state = row.state,
        f.pipeline_version = row.pipeline_version,
        f.run_id = row.run_id,
        f.model = row.model,
        f.prompt_policy = row.prompt_policy
"""


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def apply_enrichment_schema(session: Any) -> None:
    """Create the enrichment constraints and indexes against an open session."""
    from vedagraph.graph.enrichment_schema import all_enrichment_schema_cypher

    for cypher in all_enrichment_schema_cypher():
        session.run(cypher)
    logger.info("Enrichment schema applied")


def merge_concept_nodes(session: Any, project_root: pathlib.Path) -> tuple[int, int]:
    """Merge Concept nodes. Returns ``(distinct nodes, duplicate rows)``."""
    from vedagraph.graph.enrichment import iter_concept_nodes

    return _merge_nodes(
        session, iter_concept_nodes(project_root), _CONCEPT_NODE_QUERY, "concept_id", "Concept"
    )


def merge_formula_nodes(session: Any, project_root: pathlib.Path) -> tuple[int, int]:
    """Merge Formula nodes. Returns ``(distinct nodes, duplicate rows)``."""
    from vedagraph.graph.enrichment import iter_formula_nodes

    return _merge_nodes(
        session, iter_formula_nodes(project_root), _FORMULA_NODE_QUERY, "formula_id", "Formula"
    )


def merge_concept_hierarchy_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge Concept-to-Concept BROADER_THAN edges from the lexicon."""
    from vedagraph.graph.enrichment import iter_concept_hierarchy_rels

    return _merge_grouped_rels(
        session, iter_concept_hierarchy_rels(project_root), _BROADER_QUERIES, "concepts.broader"
    )


def merge_devata_concept_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge Devata-to-Concept DEVATA_ASSOCIATED_WITH edges from the lexicon."""
    from vedagraph.graph.enrichment import iter_devata_concept_rels

    return _merge_grouped_rels(
        session,
        iter_devata_concept_rels(project_root),
        _DEVATA_CONCEPT_QUERIES,
        "concepts.related_devatas",
    )


def merge_formula_occurrence_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge Passage-to-Formula USES_FORMULA edges."""
    from vedagraph.graph.enrichment import iter_formula_occurrence_rels

    return _merge_grouped_rels(
        session,
        iter_formula_occurrence_rels(project_root),
        _USES_FORMULA_QUERIES,
        "formula_occurrences.jsonl",
    )


def merge_cross_veda_parallel_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge cross-Veda Passage-to-Passage parallels, one query per textual predicate."""
    from vedagraph.graph.enrichment import iter_cross_veda_parallel_rels

    return _merge_grouped_rels(
        session,
        iter_cross_veda_parallel_rels(project_root),
        _PARALLEL_QUERIES,
        "cross_veda_parallels.jsonl",
    )


def merge_concept_assertion_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge Passage-to-Concept ABOUT_CONCEPT edges."""
    from vedagraph.graph.enrichment import iter_concept_assertion_rels

    return _merge_grouped_rels(
        session,
        iter_concept_assertion_rels(project_root),
        _ABOUT_CONCEPT_QUERIES,
        "concept_assertions.jsonl",
    )


def merge_semantic_candidate_rels(session: Any, project_root: pathlib.Path) -> RelMergeResult:
    """Merge Passage-to-object semantic candidate edges.

    Grouped by predicate *and* resolved object label, so the counts come back keyed
    ``PRAISES|Concept``. :func:`load_enrichment` folds those back to the predicate for its
    report; the split is kept here because an unmatched ``PRAISES|Devata`` and an unmatched
    ``PRAISES|Concept`` fail for different reasons and diagnosing them needs both.
    """
    from vedagraph.graph.enrichment import iter_semantic_candidate_rels

    return _merge_grouped_rels(
        session,
        iter_semantic_candidate_rels(project_root),
        _SEMANTIC_QUERIES,
        "semantic_candidates.jsonl",
        group_of=_semantic_group,
    )


def _fold(counts: dict[str, int]) -> dict[str, int]:
    """Collapse ``PREDICATE|Label`` keys back to ``PREDICATE``."""
    folded: dict[str, int] = {}
    for key, value in counts.items():
        predicate = key.split("|", 1)[0]
        folded[predicate] = folded.get(predicate, 0) + value
    return folded


def load_enrichment(session: Any, project_root: pathlib.Path) -> dict[str, int]:
    """Load the whole enrichment layer. Returns distinct-entity counts.

    Keys are node labels and relationship types for what was written, plus
    ``unmatched_<TYPE>`` for rows whose endpoints were not in the graph,
    ``unmatched_total``, and ``duplicate_rows_total``. Every count is distinct entities in
    the database, never rows read, so the returned dict can be compared directly against
    ``MATCH ()-[r:TYPE]->() RETURN count(r)`` without reconciliation.

    Order matters in one place: Concept and Formula nodes are merged before any edge that
    points at them, because the edge merges ``MATCH`` their endpoints rather than creating
    them. That is deliberate. A ``MERGE`` on the endpoint would let a typo'd concept id in
    an assertion file silently conjure an empty Concept node, and an empty Concept node is
    indistinguishable in a query from a real one.

    Applying the schema first is not optional either: without the uniqueness constraint on
    ``Concept.concept_id``, the node MERGE has no index to seek on and the load degrades
    to a label scan per batch.
    """
    counts: dict[str, int] = {}
    unmatched: dict[str, int] = {}
    duplicates = 0

    apply_enrichment_schema(session)

    concepts, concept_dupes = merge_concept_nodes(session, project_root)
    formulas, formula_dupes = merge_formula_nodes(session, project_root)
    counts["Concept"] = concepts
    counts["Formula"] = formulas
    duplicates += concept_dupes + formula_dupes

    results = (
        merge_concept_hierarchy_rels(session, project_root),
        merge_devata_concept_rels(session, project_root),
        merge_formula_occurrence_rels(session, project_root),
        merge_cross_veda_parallel_rels(session, project_root),
        merge_concept_assertion_rels(session, project_root),
        merge_semantic_candidate_rels(session, project_root),
    )

    for result in results:
        for predicate, value in _fold(result.merged).items():
            counts[predicate] = counts.get(predicate, 0) + value
        for predicate, value in _fold(result.unmatched).items():
            unmatched[predicate] = unmatched.get(predicate, 0) + value
        duplicates += sum(result.duplicate_rows.values())

    for predicate, value in sorted(unmatched.items()):
        counts[f"unmatched_{predicate}"] = value
    counts["unmatched_total"] = sum(unmatched.values())
    counts["duplicate_rows_total"] = duplicates

    if counts["unmatched_total"]:
        logger.warning(
            "Enrichment load left %d rows unmatched: %s",
            counts["unmatched_total"],
            {k: v for k, v in sorted(unmatched.items()) if v},
        )
    return counts
