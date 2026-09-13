"""Neo4j graph loader: apply schema, batch-merge nodes and relationships."""

from __future__ import annotations

import logging
import pathlib
import uuid
from collections.abc import Iterator
from typing import Any

from vedagraph.graph.corrections import CorrectionApplier

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


def _batched(it: Iterator[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for item in it:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def apply_schema(session: Any) -> None:
    """Create all constraints and indexes against an open Neo4j session."""
    from vedagraph.graph.schema import all_schema_cypher

    for cypher in all_schema_cypher():
        session.run(cypher)
    logger.info("Schema applied")


def drop_schema(session: Any) -> None:
    """Drop every project constraint and index.

    Required before a rebuild: deleting nodes leaves constraints behind, so a stale
    uniqueness constraint from a previous schema version would reject the new load.
    Constraints are dropped first because dropping one also drops its backing index.
    LOOKUP indexes are server-owned and are left alone.
    """
    for record in list(session.run("SHOW CONSTRAINTS YIELD name RETURN name")):
        session.run(f"DROP CONSTRAINT {record['name']} IF EXISTS")

    for record in list(session.run("SHOW INDEXES YIELD name, type RETURN name, type")):
        if record["type"] == "LOOKUP":
            continue
        session.run(f"DROP INDEX {record['name']} IF EXISTS")

    logger.info("Schema dropped")


def _merge_works(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_work_nodes

    total = 0
    for batch in _batched(iter_work_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (w:Work {work_id: row.work_id})
            SET w.veda = row.veda,
                w.abbreviation = row.abbreviation,
                w.work_name = row.work_name,
                w.corpus_dir = row.corpus_dir
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d Work nodes", total)
    return total


def _merge_passages(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_passage_nodes

    total = 0
    for batch in _batched(iter_passage_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (p:Passage {canonical_key: row.canonical_key})
            SET p.canonical_urn = row.canonical_urn,
                p.entity_id = row.entity_id,
                p.entity_type = row.entity_type,
                p.work_id = row.work_id,
                p.veda = row.veda,
                p.hierarchy = row.hierarchy,
                p.sequence_in_parent = row.sequence_in_parent,
                p.canonical_citation = row.canonical_citation,
                p.status = row.status,
                p.parent_key = row.parent_key,
                p.structural_path = row.structural_path,
                p.native_labels = row.native_labels
            WITH p, row
            CALL {
                WITH p, row
                FOREACH (_ IN CASE WHEN row.entity_type = 'MANTRA' THEN [1] ELSE [] END |
                    SET p:Mantra
                )
            }
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d Passage nodes", total)
    return total


def _merge_text_versions(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_text_version_nodes

    total = 0
    for batch in _batched(iter_text_version_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (tv:TextVersion {text_id: row.text_id})
            SET tv.passage_id = row.passage_id,
                tv.language = row.language,
                tv.script = row.script,
                tv.text_form = row.text_form,
                tv.text_role = row.text_role,
                tv.text_version_id = row.text_version_id,
                tv.text_nfc = row.text_nfc,
                tv.accented = row.accented,
                tv.source_id = row.source_id,
                tv.source_artifact_id = row.source_artifact_id,
                tv.rights_status = row.rights_status,
                tv.content_sha256 = row.content_sha256
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d TextVersion nodes", total)
    return total


def _merge_translations(
    session: Any, project_root: pathlib.Path, applier: CorrectionApplier
) -> int:
    from vedagraph.graph.projection import iter_translation_nodes

    total = 0
    for batch in _batched(iter_translation_nodes(project_root, applier), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (t:Translation {translation_id: row.translation_id})
            SET t.passage_id = row.passage_id,
                t.language = row.language,
                t.text = row.text,
                t.translator = row.translator,
                t.year = row.year,
                t.alignment_level = row.alignment_level,
                t.quality_status = row.quality_status,
                t.rights_status = row.rights_status,
                t.source_id = row.source_id,
                t.work_edition = row.work_edition,
                t.upstream_correction_id = row.upstream_correction_id,
                t.upstream_correction_reason = row.upstream_correction_reason
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d Translation nodes", total)
    return total


def _merge_sources(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_source_nodes

    total = 0
    for batch in _batched(iter_source_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (s:Source {source_id: row.source_id})
            SET s.name = row.name,
                s.organization = row.organization,
                s.url = row.url,
                s.authority_tier = row.authority_tier,
                s.bulk_ingestion_status = row.bulk_ingestion_status
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d Source nodes", total)
    return total


def _merge_entity_nodes(session: Any, project_root: pathlib.Path) -> dict[str, int]:
    from vedagraph.graph.entities import iter_chandas_nodes, iter_devata_nodes, iter_rishi_nodes

    counts: dict[str, int] = {}

    total = 0
    for batch in _batched(iter_rishi_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (r:Rishi {entity_key: row.entity_key})
            SET r.preferred_label = row.preferred_label,
                r.occurrence_count = row.occurrence_count,
                r.registry_namespace = row.registry_namespace,
                r.label_iast = row.label_iast,
                r.normalized_name = row.normalized_name
            """,
            rows=batch,
        )
        total += len(batch)
    counts["Rishi"] = total
    logger.info("Merged %d Rishi nodes", total)

    total = 0
    for batch in _batched(iter_devata_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (d:Devata {entity_key: row.entity_key})
            SET d.preferred_label = row.preferred_label,
                d.devata_subtype = row.devata_subtype,
                d.is_composite = row.is_composite
            """,
            rows=batch,
        )
        total += len(batch)
    counts["Devata"] = total
    logger.info("Merged %d Devata nodes", total)

    total = 0
    for batch in _batched(iter_chandas_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (c:Chandas {entity_key: row.entity_key})
            SET c.preferred_label = row.preferred_label,
                c.registry_namespace = row.registry_namespace,
                c.label_iast = row.label_iast,
                c.normalized_name = row.normalized_name
            """,
            rows=batch,
        )
        total += len(batch)
    counts["Chandas"] = total
    logger.info("Merged %d Chandas nodes", total)

    return counts


def _merge_lemmas(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.lexical import iter_lemma_nodes

    total = 0
    for batch in _batched(iter_lemma_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (l:Lemma {lemma: row.lemma})
            SET l.normalized_lemma = row.normalized_lemma,
                l.mantra_count = row.mantra_count,
                l.token_count = row.token_count,
                l.parts_of_speech = row.parts_of_speech,
                l.lemma_ids = row.lemma_ids
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d Lemma nodes", total)
    return total


def _merge_qa_issues(session: Any, project_root: pathlib.Path) -> int:
    """Merge QAIssue nodes and attach them to the Work that raised them.

    A caveat the corpus records about itself is only useful where the data is. Kept as a
    node rather than a property so one finding can attach to a Work and to the Passage it
    names without being duplicated, and so severity is filterable.
    """
    from vedagraph.graph.projection import iter_qa_issue_nodes

    total = 0
    for batch in _batched(iter_qa_issue_nodes(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (q:QAIssue {issue_id: row.issue_id})
            SET q.veda = row.veda,
                q.check_id = row.check_id,
                q.severity = row.severity,
                q.message = row.message,
                q.details = row.details,
                q.scope_key = row.scope_key,
                q.sequence = row.sequence
            WITH q, row
            MATCH (w:Work {work_id: row.work_id})
            MERGE (q)-[:QA_ISSUE_ON]->(w)
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d QAIssue nodes", total)
    return total


def _merge_contains_rels(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_contains_rels

    total_work = 0
    total_passage = 0
    work_batch: list[dict[str, Any]] = []
    passage_batch: list[dict[str, Any]] = []

    def _flush_work(b: list[dict[str, Any]]) -> None:
        if not b:
            return
        session.run(
            """
            UNWIND $rows AS row
            MATCH (w:Work {work_id: row.from_work_id})
            MATCH (p:Passage {canonical_key: row.to_passage_key})
            MERGE (w)-[r:CONTAINS]->(p)
            SET r.sequence = row.sequence
            """,
            rows=b,
        )

    def _flush_passage(b: list[dict[str, Any]]) -> None:
        if not b:
            return
        session.run(
            """
            UNWIND $rows AS row
            MATCH (parent:Passage {canonical_key: row.from_passage_key})
            MATCH (child:Passage {canonical_key: row.to_passage_key})
            MERGE (parent)-[r:CONTAINS]->(child)
            SET r.sequence = row.sequence
            """,
            rows=b,
        )

    for rel in iter_contains_rels(project_root):
        if rel["rel_type"] == "WORK_CONTAINS":
            work_batch.append(rel)
            total_work += 1
            if len(work_batch) >= _BATCH_SIZE:
                _flush_work(work_batch)
                work_batch = []
        else:
            passage_batch.append(rel)
            total_passage += 1
            if len(passage_batch) >= _BATCH_SIZE:
                _flush_passage(passage_batch)
                passage_batch = []

    _flush_work(work_batch)
    _flush_passage(passage_batch)
    total = total_work + total_passage
    logger.info(
        "Merged %d CONTAINS relationships (%d Work→Passage, %d Passage→Passage)",
        total,
        total_work,
        total_passage,
    )
    return total


def _merge_text_version_rels(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.projection import iter_has_text_version_rels

    total = 0
    for batch in _batched(iter_has_text_version_rels(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Passage {entity_id: row.passage_entity_id})
            MATCH (tv:TextVersion {text_id: row.text_id})
            MERGE (p)-[r:HAS_TEXT_VERSION]->(tv)
            SET r.language = row.language, r.text_form = row.text_form
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d HAS_TEXT_VERSION relationships", total)
    return total


def _merge_translation_rels(
    session: Any, project_root: pathlib.Path, applier: CorrectionApplier
) -> int:
    from vedagraph.graph.projection import iter_has_translation_rels

    total = 0
    for batch in _batched(iter_has_translation_rels(project_root, applier), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Passage {entity_id: row.passage_entity_id})
            MATCH (t:Translation {translation_id: row.translation_id})
            MERGE (p)-[r:HAS_TRANSLATION]->(t)
            SET r.language = row.language, r.translator = row.translator
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d HAS_TRANSLATION relationships", total)
    return total


def _merge_rdc_rels(session: Any, project_root: pathlib.Path) -> dict[str, int]:
    from vedagraph.graph.entities import iter_rishi_devata_chandas_rels

    # Counted as distinct (subject, object) pairs, not as rows read. The knowledge layer
    # legitimately emits one assertion twice when two overlapping anukramani range scopes
    # cover the same mantra -- RV 8.46.25-28 Pragathah is asserted by two ranges -- and
    # MERGE collapses them. Reporting rows read would show 10,527 HAS_CHANDAS against
    # 10,523 edges in the database and read as four silently lost edges.
    counts: dict[str, int] = {"HAS_RISHI": 0, "HAS_DEVATA": 0, "HAS_CHANDAS": 0}
    seen: dict[str, set[tuple[str, str]]] = {k: set() for k in counts}
    duplicate_rows: dict[str, int] = {k: 0 for k in counts}
    batches: dict[str, list[dict[str, Any]]] = {k: [] for k in counts}

    # Stamped and swept. This function is the only writer of all three predicates, so the
    # layer owns every one of them -- and without a sweep, correcting the *source* index
    # changes nothing in the graph. That was measured: cleaning eight OCR-corrupt
    # Atharvavedic metre labels out of the registry left all eight nodes and their edges in
    # place, still asserting metres the corrected index no longer prints, because MERGE
    # adds and never retracts. A registry whose corrections cannot reach the graph is a
    # registry nobody can fix.
    build_pass = uuid.uuid4().hex
    queries = {
        "HAS_RISHI": """
            UNWIND $rows AS row
            MATCH (p:Passage {canonical_key: row.subject_key})
            MATCH (r:Rishi {entity_key: row.object_key})
            MERGE (p)-[rel:HAS_RISHI]->(r)
            SET rel.confidence = row.confidence,
                rel.provenance_class = row.provenance_class,
                rel.scope_origin = row.scope_origin,
                rel.source_id = row.source_id,
                rel.build_pass = $build_pass
        """,
        "HAS_DEVATA": """
            UNWIND $rows AS row
            MATCH (p:Passage {canonical_key: row.subject_key})
            MATCH (d:Devata {entity_key: row.object_key})
            MERGE (p)-[rel:HAS_DEVATA]->(d)
            SET rel.confidence = row.confidence,
                rel.provenance_class = row.provenance_class,
                rel.scope_origin = row.scope_origin,
                rel.source_id = row.source_id,
                rel.build_pass = $build_pass
        """,
        "HAS_CHANDAS": """
            UNWIND $rows AS row
            MATCH (p:Passage {canonical_key: row.subject_key})
            MATCH (c:Chandas {entity_key: row.object_key})
            MERGE (p)-[rel:HAS_CHANDAS]->(c)
            SET rel.confidence = row.confidence,
                rel.provenance_class = row.provenance_class,
                rel.scope_origin = row.scope_origin,
                rel.source_id = row.source_id,
                rel.build_pass = $build_pass
        """,
    }

    def _flush(pred: str) -> None:
        b = batches[pred]
        if not b:
            return
        session.run(queries[pred], rows=b, build_pass=build_pass)
        batches[pred] = []

    for rel in iter_rishi_devata_chandas_rels(project_root):
        pred = rel["predicate"]
        if pred not in batches:
            continue
        pair = (rel["subject_key"], rel["object_key"])
        if pair in seen[pred]:
            duplicate_rows[pred] += 1
            continue
        seen[pred].add(pair)
        batches[pred].append(rel)
        counts[pred] += 1
        if len(batches[pred]) >= _BATCH_SIZE:
            _flush(pred)

    for pred in list(batches):
        _flush(pred)

    # Sweep, then drop whatever the sweep orphaned. The node deletion is scoped to nodes
    # with no remaining attribution edge, so a rsi or metre still asserted anywhere
    # survives; only an entity the corrected index no longer references at all is removed.
    # Both counts are returned alongside the merge counts, because a rebuild that silently
    # deleted rows would be worse than one that silently kept them.
    for pred in ("HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"):
        retired = session.run(
            f"""
            MATCH (:Passage)-[rel:{pred}]->()
            WHERE rel.build_pass IS NULL OR rel.build_pass <> $build_pass
            DELETE rel
            RETURN count(*) AS c
            """,
            build_pass=build_pass,
        ).single()["c"]
        counts[f"retired_{pred}"] = int(retired)

    for label, incoming in (("Rishi", "HAS_RISHI"), ("Chandas", "HAS_CHANDAS")):
        orphaned = session.run(
            f"""
            MATCH (n:{label})
            WHERE NOT (n)<-[:{incoming}]-()
            DELETE n
            RETURN count(*) AS c
            """
        ).single()["c"]
        counts[f"retired_orphan_{label}"] = int(orphaned)

    for pred, count in counts.items():
        if duplicate_rows.get(pred):
            logger.info(
                "Merged %d %s relationships (%d duplicate source rows collapsed)",
                count,
                pred,
                duplicate_rows[pred],
            )
        else:
            logger.info("Merged %d %s relationships", count, pred)
    return counts


def _merge_mentions_lemma_rels(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.lexical import iter_mentions_lemma_rels

    total = 0
    for batch in _batched(iter_mentions_lemma_rels(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Passage {canonical_key: row.subject_key})
            MATCH (l:Lemma {lemma: row.lemma})
            MERGE (p)-[r:MENTIONS_LEMMA]->(l)
            SET r.occurrence_count = row.occurrence_count,
                r.provenance_class = row.provenance_class
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d MENTIONS_LEMMA relationships", total)
    return total


def _merge_mentions_entity_rels(session: Any, project_root: pathlib.Path) -> int:
    from vedagraph.graph.lexical import iter_mentions_entity_rels

    total = 0
    for batch in _batched(iter_mentions_entity_rels(project_root), _BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Passage {canonical_key: row.subject_key})
            MATCH (d:Devata {entity_key: row.object_key})
            MERGE (p)-[r:MENTIONS_ENTITY]->(d)
            SET r.occurrence_count = row.occurrence_count,
                r.provenance_class = row.provenance_class,
                r.annotation_layer_id = row.annotation_layer_id
            """,
            rows=batch,
        )
        total += len(batch)
    logger.info("Merged %d MENTIONS_ENTITY relationships", total)
    return total


def _merge_parallel_rels(session: Any, project_root: pathlib.Path) -> dict[str, int]:
    """Merge parallels, keeping EXACT_PARALLEL_OF and PARALLEL_TO distinct.

    mantra_parallels.jsonl carries both predicates. Collapsing them would assert that
    a high-confidence near parallel is a verbatim match, so each is loaded under its
    own relationship type.
    """
    from vedagraph.graph.lexical import iter_exact_parallel_rels

    queries = {
        "EXACT_PARALLEL_OF": """
            UNWIND $rows AS row
            MATCH (a:Passage {canonical_key: row.subject_key})
            MATCH (b:Passage {canonical_key: row.object_key})
            MERGE (a)-[r:EXACT_PARALLEL_OF]->(b)
            SET r.methods = row.methods,
                r.strongest_method = row.strongest_method,
                r.similarity = row.similarity,
                r.status = row.status,
                r.provenance_class = row.provenance_class
        """,
        "PARALLEL_TO": """
            UNWIND $rows AS row
            MATCH (a:Passage {canonical_key: row.subject_key})
            MATCH (b:Passage {canonical_key: row.object_key})
            MERGE (a)-[r:PARALLEL_TO]->(b)
            SET r.methods = row.methods,
                r.strongest_method = row.strongest_method,
                r.similarity = row.similarity,
                r.status = row.status,
                r.provenance_class = row.provenance_class
        """,
    }

    # Distinct-pair counting, for the same reason as in _merge_rdc_rels: the reported
    # number must be the number of edges in the database, not the number of rows read.
    counts: dict[str, int] = {"EXACT_PARALLEL_OF": 0, "PARALLEL_TO": 0}
    seen: dict[str, set[tuple[str, str]]] = {k: set() for k in counts}
    duplicate_rows: dict[str, int] = {k: 0 for k in counts}
    batches: dict[str, list[dict[str, Any]]] = {k: [] for k in counts}

    def _flush(pred: str) -> None:
        if batches[pred]:
            session.run(queries[pred], rows=batches[pred])
            batches[pred] = []

    for rel in iter_exact_parallel_rels(project_root):
        pred = rel["predicate"]
        if pred not in batches:
            logger.warning("Skipping unknown parallel predicate %r", pred)
            continue
        pair = (rel["subject_key"], rel["object_key"])
        if pair in seen[pred]:
            duplicate_rows[pred] += 1
            continue
        seen[pred].add(pair)
        batches[pred].append(rel)
        counts[pred] += 1
        if len(batches[pred]) >= _BATCH_SIZE:
            _flush(pred)

    for pred in list(batches):
        _flush(pred)

    for pred, count in counts.items():
        if duplicate_rows[pred]:
            logger.info(
                "Merged %d %s relationships (%d duplicate source rows collapsed)",
                count,
                pred,
                duplicate_rows[pred],
            )
        else:
            logger.info("Merged %d %s relationships", count, pred)
    return counts


def load_all(session: Any, project_root: pathlib.Path) -> dict[str, Any]:
    """Full graph load pipeline. Returns counts dict."""
    from vedagraph.graph.corrections import verify_corrections_applied
    from vedagraph.graph.projection import build_correction_applier

    counts: dict[str, Any] = {}

    # One applier for the whole load: the Translation nodes and the HAS_TRANSLATION edges
    # must be corrected identically, and sharing the instance is also what lets the run
    # assert afterwards that every declared correction actually reached a row.
    applier = build_correction_applier(project_root)

    # Schema
    apply_schema(session)

    # Nodes
    counts["Work"] = _merge_works(session, project_root)
    counts["Passage"] = _merge_passages(session, project_root)
    counts["TextVersion"] = _merge_text_versions(session, project_root)
    counts["Translation"] = _merge_translations(session, project_root, applier)
    counts["Source"] = _merge_sources(session, project_root)

    entity_counts = _merge_entity_nodes(session, project_root)
    counts.update(entity_counts)

    counts["Lemma"] = _merge_lemmas(session, project_root)
    counts["QAIssue"] = _merge_qa_issues(session, project_root)

    # Relationships
    counts["CONTAINS"] = _merge_contains_rels(session, project_root)
    counts["HAS_TEXT_VERSION"] = _merge_text_version_rels(session, project_root)
    counts["HAS_TRANSLATION"] = _merge_translation_rels(session, project_root, applier)

    rdc_counts = _merge_rdc_rels(session, project_root)
    counts.update(rdc_counts)

    counts["MENTIONS_LEMMA"] = _merge_mentions_lemma_rels(session, project_root)
    counts["MENTIONS_ENTITY"] = _merge_mentions_entity_rels(session, project_root)
    counts.update(_merge_parallel_rels(session, project_root))

    verify_corrections_applied(applier)
    counts["upstream_corrections_applied"] = len(applier.outcomes)

    return counts
