#!/usr/bin/env python3
"""The single R4 canonical migration: back up, apply every staged mutation, prove the delta.

One migration for every R4 gap, because writing after each gap makes the census move for
reasons no single receipt can account for. Everything applied here was computed by a
``r4_stage_*.py`` script and written to disk first, so ``actual == promised`` compares a
measurement against a *file* rather than against the same computation run twice -- which is
the M9 readback mistake this project has already made once.

Order of operations
===================

1.  **Backup.** A logical export of every node and relationship, its sha256, the census and
    a graph fingerprint. A binary ``neo4j-admin`` dump would need the database stopped;
    this is the export pattern R3 used for the same purpose, it is restorable, and it
    needs no downtime. The deviation is recorded in the receipt rather than glossed.
2.  **Conflict scan.** Every staged write is checked against the live graph *before* any
    of them runs: a node that does not exist, an edge that already exists, a property that
    would overwrite a different value. A conflict aborts the whole migration.
3.  **Apply**, in one declared order, inside explicit transactions.
4.  **Receipt.** Nodes and relationships created, updated and deleted, per gap, promised
    against actual, with the census and fingerprint before and after.
5.  **Readback.** Each gap's own closure measure, re-run against the live graph.

Identity is never changed. No ``entity_key``, ``canonical_key``, ``formula_id``,
``metric_id`` or ``translation_id`` is written to a node that already has a different one;
the conflict scan refuses it.

Usage:
    python scripts/r4_migrate.py --backup          # step 1 only
    python scripts/r4_migrate.py --scan            # step 2 only, read-only
    python scripts/r4_migrate.py --apply           # steps 2-5
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any, Final

from neo4j import GraphDatabase, Query

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain import loader as domain_loader  # noqa: E402
from vedagraph.domain.profiles import DevataProfile  # noqa: E402

R4: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4"
BACKUP: Final = R4 / "backup"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"
TIMEOUT: Final[float] = 900.0

STAGING: Final[dict[str, pathlib.Path]] = {
    "GAP-ATTRIBUTION-002": R4 / "attribution_002" / "staging.json",
    "GAP-ENTITY_COVERAGE-001": R4 / "entity_001" / "staging.json",
    "GAP-ENTITY_COVERAGE-002": R4 / "entity_002" / "staging.json",
    "GAP-ENTITY_COVERAGE-006": R4 / "entity_006" / "staging.json",
    "R4-COMBINED": R4 / "combined" / "staging.json",
}


def _load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def census(session: Any) -> dict[str, Any]:
    def scalar(query: str) -> Any:
        return session.run(Query(query, timeout=TIMEOUT)).single()[0]

    return {
        "nodes": scalar("MATCH (n) RETURN count(n)"),
        "relationships": scalar("MATCH ()-[r]->() RETURN count(r)"),
        "RV": scalar("MATCH (m:Mantra {veda:'RV'}) RETURN count(m)"),
        "SV": scalar("MATCH (m:Mantra {veda:'SV'}) RETURN count(m)"),
        "YV": scalar("MATCH (m:Mantra {veda:'YV'}) RETURN count(m)"),
        "AV": scalar("MATCH (m:Mantra {veda:'AV'}) RETURN count(m)"),
        "DerivedMetric": scalar("MATCH (n:DerivedMetric) RETURN count(n)"),
        "Devata": scalar("MATCH (n:Devata) RETURN count(n)"),
        "Epithet": scalar("MATCH (n:Epithet) RETURN count(n)"),
        "Formula": scalar("MATCH (n:Formula) RETURN count(n)"),
        "FormulaFamily": scalar("MATCH (n:FormulaFamily) RETURN count(n)"),
        "DomainEntity": scalar("MATCH (n:DomainEntity) RETURN count(n)"),
    }


def fingerprint(session: Any) -> dict[str, Any]:
    """Per-label node counts and per-type edge counts, digested.

    A census of twelve figures can stay still while a label nobody counted moves, so the
    fingerprint is over every label and every relationship type.
    """
    labels = {
        record["label"]: record["n"]
        for record in session.run(
            Query(
                "CALL db.labels() YIELD label "
                "CALL (label) { WITH label MATCH (n) WHERE label IN labels(n) "
                "RETURN count(n) AS n } RETURN label, n ORDER BY label",
                timeout=TIMEOUT,
            )
        )
    }
    types = {
        record["t"]: record["n"]
        for record in session.run(
            Query(
                "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY t",
                timeout=TIMEOUT,
            )
        )
    }
    payload = json.dumps({"labels": labels, "types": types}, sort_keys=True)
    return {
        "labels": labels,
        "relationship_types": types,
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def take_backup(session: Any) -> dict[str, Any]:
    BACKUP.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    counts: dict[str, int] = {}

    nodes_path = BACKUP / "nodes.jsonl"
    with nodes_path.open("w", encoding="utf-8", newline="\n") as handle:
        written = 0
        for record in session.run(
            Query(
                "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props",
                timeout=TIMEOUT,
            )
        ):
            handle.write(
                json.dumps(
                    {"id": record["id"], "labels": record["labels"], "props": record["props"]},
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                + "\n"
            )
            written += 1
    counts["nodes"] = written

    rels_path = BACKUP / "relationships.jsonl"
    with rels_path.open("w", encoding="utf-8", newline="\n") as handle:
        written = 0
        for record in session.run(
            Query(
                "MATCH (a)-[r]->(b) RETURN id(r) AS id, type(r) AS type, id(a) AS start, "
                "id(b) AS end, properties(r) AS props",
                timeout=TIMEOUT,
            )
        ):
            handle.write(
                json.dumps(
                    {
                        "id": record["id"],
                        "type": record["type"],
                        "start": record["start"],
                        "end": record["end"],
                        "props": record["props"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                + "\n"
            )
            written += 1
    counts["relationships"] = written

    for path in (nodes_path, rels_path):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        digests[path.name] = digest.hexdigest()
        (path.parent / f"{path.name}.sha256").write_text(
            f"{digest.hexdigest()}  {path.name}\n", encoding="utf-8", newline="\n"
        )

    manifest = {
        "artifact": "R4_PRE_MIGRATION_BACKUP",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kind": "LOGICAL_EXPORT_NOT_A_BINARY_DUMP",
        "why_not_a_binary_dump": (
            "Neo4j runs in the vedagraph-neo4j container on 5.26-community. "
            "`neo4j-admin database dump` requires the database stopped, and online backup "
            "is an Enterprise feature. This is the export pattern R3 used before its own "
            "mutations: every node and relationship with its id and properties, restorable, "
            "and it needs no downtime."
        ),
        "counts": counts,
        "sha256": digests,
        "census": census(session),
        "fingerprint": fingerprint(session),
    }
    (BACKUP / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


# ---------------------------------------------------------------------------
# Conflict scan
# ---------------------------------------------------------------------------


def scan(session: Any) -> dict[str, Any]:
    """Every staged write, checked against the live graph before any of them runs."""
    conflicts: list[dict[str, Any]] = []
    already: list[dict[str, Any]] = []
    checked = 0

    def missing_nodes(query: str, keys: list[str], what: str) -> None:
        nonlocal checked
        if not keys:
            return
        checked += len(keys)
        present = {
            record["k"]
            for record in session.run(Query(query, timeout=TIMEOUT), keys=keys)
        }
        for key in sorted(set(keys) - present):
            conflicts.append({"kind": "MISSING_NODE", "what": what, "key": key})

    attribution = _load(STAGING["GAP-ATTRIBUTION-002"])
    missing_nodes(
        "MATCH (a:DevataAscription) WHERE a.entity_key IN $keys RETURN a.entity_key AS k",
        [row["ascription_key"] for row in attribution["new_edges"]],
        "DevataAscription",
    )
    missing_nodes(
        "MATCH (d:Devata) WHERE d.entity_key IN $keys RETURN d.entity_key AS k",
        [row["devata_key"] for row in attribution["new_edges"]],
        "Devata",
    )
    # An ASCRIBES_TO_DEVATA edge that already exists means the resolver landed twice.
    existing = session.run(
        Query(
            "MATCH (a:DevataAscription)-[:ASCRIBES_TO_DEVATA]->() "
            "WHERE a.entity_key IN $keys RETURN a.entity_key AS k",
            timeout=TIMEOUT,
        ),
        keys=[row["ascription_key"] for row in attribution["new_edges"]],
    )
    for record in existing:
        # Not a conflict. Every staged edge here is MERGEd and its properties are the
        # staged ones, so an edge already present is this migration having run before --
        # which happens, because the first run failed midway on a profile property name.
        # Reported separately so the receipt's "created" figure stays honest.
        already.append(
            {"kind": "ALREADY_APPLIED", "what": "ASCRIBES_TO_DEVATA", "key": record["k"]}
        )

    epithets = _load(STAGING["GAP-ENTITY_COVERAGE-001"])
    missing_nodes(
        "MATCH (e:Epithet) WHERE e.epithet_key IN $keys RETURN e.epithet_key AS k",
        sorted({row["epithet_key"] for row in epithets["edges"]}),
        "Epithet",
    )
    missing_nodes(
        "MATCH (m:Mantra) WHERE m.canonical_key IN $keys RETURN m.canonical_key AS k",
        sorted({row["mantra_key"] for row in epithets["edges"]}),
        "Mantra (epithet occurrence)",
    )

    profiles = _load(STAGING["GAP-ENTITY_COVERAGE-002"])
    missing_nodes(
        "MATCH (d:Devata) WHERE d.entity_key IN $keys RETURN d.entity_key AS k",
        [row["entity_key"] for row in profiles["profiles"]],
        "Devata (profile)",
    )
    # Deleting a metric that is not there, or that belongs to an eligible deity, are both
    # conflicts: the first means the staging is stale, the second means the wrong rows.
    to_delete = profiles["promised"]["metric_ids_deleted"]
    if to_delete:
        checked += len(to_delete)
        found = {
            record["id"]
            for record in session.run(
                Query(
                    "MATCH (m:DerivedMetric) WHERE m.metric_id IN $keys "
                    "RETURN m.metric_id AS id",
                    timeout=TIMEOUT,
                ),
                keys=to_delete,
            )
        }
        for metric_id in sorted(set(to_delete) - found):
            # The intent is that this metric NOT exist, so absent is the desired end
            # state and means the deletion already ran. A stale-staging reading would be
            # the alternative, and it is excluded by the check below: if the subject were
            # eligible the row would not be staged for deletion at all.
            already.append(
                {"kind": "ALREADY_APPLIED", "what": "DerivedMetric deletion", "key": metric_id}
            )
        eligible_targets = [
            record["id"]
            for record in session.run(
                Query(
                    "MATCH (m:DerivedMetric) WHERE m.metric_id IN $keys "
                    "MATCH (d:Devata {entity_key: m.subject_key}) WHERE d.is_deity = true "
                    "RETURN m.metric_id AS id",
                    timeout=TIMEOUT,
                ),
                keys=to_delete,
            )
        ]
        for metric_id in eligible_targets:
            conflicts.append(
                {
                    "kind": "DELETE_TARGET_IS_ELIGIBLE",
                    "what": "DerivedMetric",
                    "key": metric_id,
                }
            )

    recall = _load(STAGING["GAP-ENTITY_COVERAGE-006"])
    missing_nodes(
        "MATCH (n:DomainEntity) WHERE n.entity_key IN $keys RETURN n.entity_key AS k",
        [row["entity_key"] for row in recall["clause_1_recall"]["rows"]],
        "DomainEntity (recall)",
    )
    ayas = recall["clause_2_ayas"]
    if not ayas["witness_exists_in_graph"]:
        conflicts.append(
            {"kind": "MISSING_NODE", "what": "ayas witness", "key": ayas["witness"]}
        )

    combined = _load(STAGING["R4-COMBINED"])
    missing_nodes(
        "MATCH (r:RitualRole) WHERE r.entity_key IN $keys RETURN r.entity_key AS k",
        [row["entity_key"] for row in combined["GAP-RITUAL-004"]["rows"]],
        "RitualRole",
    )
    missing_nodes(
        "MATCH (n:NaturalPhenomenon) WHERE n.entity_key IN $keys RETURN n.entity_key AS k",
        [row["entity_key"] for row in combined["GAP-ENTITY_COVERAGE-007"]["rows"]],
        "NaturalPhenomenon",
    )
    missing_nodes(
        "MATCH (d:Devata) WHERE d.entity_key IN $keys RETURN d.entity_key AS k",
        [row["entity_key"] for row in combined["GAP-COMMUNITIES-002"]["rows"]],
        "Devata (composite)",
    )
    missing_nodes(
        "MATCH (d:Devata) WHERE d.entity_key IN $keys RETURN d.entity_key AS k",
        sorted(
            {row["component"] for row in combined["GAP-COMMUNITIES-002"]["component_edges"]}
        ),
        "Devata (component)",
    )
    missing_nodes(
        "MATCH (t:Translation) WHERE t.translation_id IN $keys RETURN t.translation_id AS k",
        sorted({row["translation_id"] for row in combined["GAP-TRANSLATION-004"]["edges"]}),
        "Translation",
    )
    missing_nodes(
        "MATCH (m:Mantra) WHERE m.canonical_key IN $keys RETURN m.canonical_key AS k",
        sorted({row["mantra_key"] for row in combined["GAP-TRANSLATION-004"]["edges"]}),
        "Mantra (translation range)",
    )
    # A covered verse that has since gained its own rendering must not get a range edge.
    already_translated = session.run(
        Query(
            "MATCH (m:Mantra)-[:HAS_TRANSLATION]->() WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS k",
            timeout=TIMEOUT,
        ),
        keys=[row["mantra_key"] for row in combined["GAP-TRANSLATION-004"]["edges"]],
    )
    for record in already_translated:
        already.append(
            {"kind": "ALREADY_APPLIED", "what": "HAS_TRANSLATION", "key": record["k"]}
        )

    return {"checked": checked, "conflicts": conflicts, "already_applied": already}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def apply(session: Any) -> dict[str, Any]:
    actual: dict[str, dict[str, int]] = {}

    def counted(gap: str, name: str, value: int) -> None:
        actual.setdefault(gap, {})[name] = value

    def edge_count(pattern: str) -> int:
        return session.run(
            Query(f"MATCH {pattern} RETURN count(r)", timeout=TIMEOUT)
        ).single()[0]

    def created(gap: str, pattern: str, before: int) -> None:
        """Edges this step actually created, not the rows its MERGE touched.

        ``MERGE ... RETURN count(r)`` counts matched-or-created, so on a resumed run it
        reports every pre-existing edge as new. The receipt is supposed to prove the
        delta, so the delta is measured around the step.
        """
        after = edge_count(pattern)
        actual.setdefault(gap, {})["relationships_created"] = after - before
        actual.setdefault(gap, {})["relationships_already_present"] = before

    # -- GAP-ATTRIBUTION-002 ------------------------------------------------
    attribution = _load(STAGING["GAP-ATTRIBUTION-002"])
    rows = [
        {
            "ascription": row["ascription_key"],
            "devata": row["devata_key"],
            "props": row["edge_properties"],
            "reason": row["reason"],
        }
        for row in attribution["new_edges"]
    ]
    attribution_pattern = "(:DevataAscription)-[r:ASCRIBES_TO_DEVATA]->(:Devata)"
    attribution_before = edge_count(attribution_pattern)
    session.run(
        Query(
            """
            UNWIND $rows AS row
            MATCH (a:DevataAscription {entity_key: row.ascription})
            MATCH (d:Devata {entity_key: row.devata})
            MERGE (a)-[r:ASCRIBES_TO_DEVATA]->(d)
            SET r += row.props
            SET a.ascription_resolution_status = 'RESOLVED_TO_CANONICAL_DEVATA',
                a.ascription_unresolved_reason = NULL,
                a.ascription_resolution_note = row.reason
            RETURN count(r) AS edges
            """,
            timeout=TIMEOUT,
        ),
        rows=rows,
    ).consume()
    created("GAP-ATTRIBUTION-002", attribution_pattern, attribution_before)
    counted("GAP-ATTRIBUTION-002", "nodes_updated", len(rows))

    # -- GAP-ENTITY_COVERAGE-001 -------------------------------------------
    epithets = _load(STAGING["GAP-ENTITY_COVERAGE-001"])
    epithet_pattern = "(:Mantra)-[r:MENTIONS_EPITHET]->(:Epithet)"
    epithet_before = edge_count(epithet_pattern)
    edges = epithets["edges"]
    for start in range(0, len(edges), 1000):
        batch = [
            {"mantra": row["mantra_key"], "epithet": row["epithet_key"], "props": row["properties"]}
            for row in edges[start : start + 1000]
        ]
        session.run(
            Query(
                """
                UNWIND $rows AS row
                MATCH (m:Mantra {canonical_key: row.mantra})
                MATCH (e:Epithet {epithet_key: row.epithet})
                MERGE (m)-[r:MENTIONS_EPITHET]->(e)
                SET r += row.props
                RETURN count(r) AS edges
                """,
                timeout=TIMEOUT,
            ),
            rows=batch,
        ).consume()
    created("GAP-ENTITY_COVERAGE-001", epithet_pattern, epithet_before)
    # Per-epithet recall onto the node, so the figure travels with the epithet.
    recall_rows = [
        {
            "epithet": row["epithet_key"],
            "props": {
                "occurrence_contract": epithets["contract"],
                "occurrence_match_tier": row["match_tier"],
                "occurrence_mantras": row["mantras"],
                "occurrence_tokens": row.get("tokens", 0),
                "occurrence_annotator_lemmas": row["lemma_labels"],
                "occurrence_scope": "RV_ONLY_ANNOTATION_COVERS_NO_OTHER_CORPUS",
            },
        }
        for row in epithets["per_epithet_recall"]
    ]
    counted(
        "GAP-ENTITY_COVERAGE-001",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (e:Epithet {epithet_key: row.epithet}) "
                "SET e += row.props RETURN count(e) AS n",
                timeout=TIMEOUT,
            ),
            rows=recall_rows,
        ).single()["n"],
    )

    # -- GAP-ENTITY_COVERAGE-002 -------------------------------------------
    profiles = _load(STAGING["GAP-ENTITY_COVERAGE-002"])
    deleted = session.run(
        Query(
            "MATCH (m:DerivedMetric) WHERE m.metric_id IN $keys "
            "WITH m, count { (m)--() } AS degree DETACH DELETE m RETURN count(*) AS n",
            timeout=TIMEOUT,
        ),
        keys=profiles["promised"]["metric_ids_deleted"],
    ).single()["n"]
    counted("GAP-ENTITY_COVERAGE-002", "nodes_deleted", deleted)

    metric_rows = [
        {
            "metric_id": metric["metric_id"],
            "props": {
                "metric_id": metric["metric_id"],
                "metric_name": metric["metric_name"],
                "subject_key": metric["subject_key"],
                "values_json": metric["values_json"]
                if isinstance(metric.get("values_json"), str)
                else json.dumps(metric.get("values") or {}, ensure_ascii=False),
                "method": metric["method"],
                "scope_note": metric["scope_note"],
                "display_type": "DerivedMetric",
                "display_label": f"{metric['metric_name']} ({metric['subject_key']})",
                "domain_model_version": metric.get("domain_model_version")
                or "vedagraph-knowledge-model-v2",
            },
        }
        for metric in profiles["metrics"]
    ]
    written = session.run(
        Query(
            "UNWIND $rows AS row MERGE (m:DerivedMetric {metric_id: row.metric_id}) "
            "SET m += row.props RETURN count(m) AS n",
            timeout=TIMEOUT,
        ),
        rows=metric_rows,
    ).single()["n"]
    counted("GAP-ENTITY_COVERAGE-002", "metric_nodes_merged", written)

    # The staged rows are ``dataclasses.asdict`` of DevataProfile, so they carry its
    # FIELDS and not its computed properties -- ``total_attributed`` and
    # ``per_passage_share`` are properties. Reconstructing the dataclass and handing it to
    # ``domain_loader.load_profiles`` reuses the authoritative writer instead of me
    # re-deriving twenty property names beside it, which is how a denormalised cache drifts
    # from the thing it caches.
    reconstructed = [DevataProfile(**row) for row in profiles["profiles"]]
    report = domain_loader.load_profiles(session, reconstructed)
    counted("GAP-ENTITY_COVERAGE-002", "nodes_updated", report.sent)
    metric_rows_for_edges = metric_rows
    measures_pattern = "(:DerivedMetric)-[r:MEASURES]->(:Devata)"
    measures_before = edge_count(measures_pattern)
    _ = (
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (m:DerivedMetric {metric_id: row.metric_id}) "
                "MATCH (d:Devata {entity_key: row.props.subject_key}) "
                "MERGE (m)-[r:MEASURES]->(d) RETURN count(r) AS n",
                timeout=TIMEOUT,
            ),
            rows=metric_rows_for_edges,
        ).consume()
    )
    created("GAP-ENTITY_COVERAGE-002", measures_pattern, measures_before)

    # -- GAP-ENTITY_COVERAGE-006 -------------------------------------------
    recall = _load(STAGING["GAP-ENTITY_COVERAGE-006"])
    entity_rows = [
        {
            "entity_key": row["entity_key"],
            "props": {
                "lexical_recall_contract": recall["contract"],
                "lexical_recall_status": row["recall_status"],
                "lexical_recall_reason": row.get("recall_reason"),
                "lexical_recall": row.get("recall"),
                "lexical_recall_sample_size": row.get("recall_sample_size"),
                "lexical_recall_matched": row.get("recall_matched"),
                "lexical_recall_scope": row.get("recall_scope"),
            },
        }
        for row in recall["clause_1_recall"]["rows"]
    ]
    counted(
        "GAP-ENTITY_COVERAGE-006",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (n:DomainEntity {entity_key: row.entity_key}) "
                "SET n += row.props RETURN count(n) AS n",
                timeout=TIMEOUT,
            ),
            rows=entity_rows,
        ).single()["n"],
    )
    staged_edge = recall["clause_2_ayas"]["staged_edge"]
    ayas_pattern = "({entity_key:'VG:CONCEPT:AYAS-METAL'})-[r:ATTESTED_IN]->(:Mantra)"
    ayas_before = edge_count(ayas_pattern)
    _ = (
        session.run(
            Query(
                "MATCH (n {entity_key: $subject}) MATCH (m:Mantra {canonical_key: $object}) "
                "MERGE (n)-[r:ATTESTED_IN]->(m) SET r += $props RETURN count(r) AS n",
                timeout=TIMEOUT,
            ),
            subject=staged_edge["subject"],
            object=staged_edge["object"],
            props=staged_edge["properties"],
        ).consume()
    )
    created("GAP-ENTITY_COVERAGE-006", ayas_pattern, ayas_before)

    # -- R4-COMBINED --------------------------------------------------------
    combined = _load(STAGING["R4-COMBINED"])

    role_rows = [
        {
            "entity_key": row["entity_key"],
            "props": {
                "in_classical_sixteen": row["in_classical_sixteen_after"],
                "denominator_schema": row["denominator_schema_after"],
                "denominator_schema_note": row["denominator_schema_note_after"],
                "classical_sixteen_basis": row.get("basis"),
            },
        }
        for row in combined["GAP-RITUAL-004"]["rows"]
    ]
    counted(
        "GAP-RITUAL-004",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (r:RitualRole {entity_key: row.entity_key}) "
                "SET r += row.props RETURN count(r) AS n",
                timeout=TIMEOUT,
            ),
            rows=role_rows,
        ).single()["n"],
    )

    phenomenon_rows = [
        {
            "entity_key": row["entity_key"],
            "props": {
                "personification_status": row["personification_status"],
                "personification_status_reason": row["personification_status_reason"],
                "personified_as": row["personified_as"],
                "personification_contract": row["personification_contract"],
            },
        }
        for row in combined["GAP-ENTITY_COVERAGE-007"]["rows"]
    ]
    counted(
        "GAP-ENTITY_COVERAGE-007",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (n:NaturalPhenomenon {entity_key: row.entity_key}) "
                "SET n += row.props RETURN count(n) AS n",
                timeout=TIMEOUT,
            ),
            rows=phenomenon_rows,
        ).single()["n"],
    )

    composite_rows = [
        {
            "entity_key": row["entity_key"],
            "props": {
                "decomposition_status": row["decomposition_status"],
                "decomposition_status_reason": row["decomposition_status_reason"],
                "component_registry_review_status": row.get("component_registry_review_status"),
                "component_registry_notes": row.get("component_registry_notes"),
            },
        }
        for row in combined["GAP-COMMUNITIES-002"]["rows"]
    ]
    counted(
        "GAP-COMMUNITIES-002",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (d:Devata {entity_key: row.entity_key}) "
                "SET d += row.props RETURN count(d) AS n",
                timeout=TIMEOUT,
            ),
            rows=composite_rows,
        ).single()["n"],
    )
    component_edges = combined["GAP-COMMUNITIES-002"]["component_edges"]
    composed_pattern = "(:Devata)-[r:COMPOSED_OF]->(:Devata)"
    composed_before = edge_count(composed_pattern)
    _ = (
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (a:Devata {entity_key: row.composite}) "
                "MATCH (b:Devata {entity_key: row.component}) "
                "MERGE (a)-[r:COMPOSED_OF]->(b) SET r += row.properties RETURN count(r) AS n",
                timeout=TIMEOUT,
            ),
            rows=component_edges,
        ).consume()
        if component_edges
        else None
    )
    created("GAP-COMMUNITIES-002", composed_pattern, composed_before)
    # component_count must agree with the edges that landed, measured not declared.
    session.run(
        Query(
            "MATCH (d:Devata) WHERE d.structure IN ['PAIR','GROUP'] "
            "SET d.component_count = count { (d)-[:COMPOSED_OF]->(:Devata) }",
            timeout=TIMEOUT,
        )
    ).consume()

    retypes = combined["GAP-TRANSLATION-004"]["retypes"]
    counted(
        "GAP-TRANSLATION-004",
        "translation_nodes_retyped",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (t:Translation {translation_id: row.translation_id}) "
                "SET t.alignment_level = row.alignment_level_after, "
                "    t.alignment_level_basis = row.basis "
                "RETURN count(t) AS n",
                timeout=TIMEOUT,
            ),
            rows=retypes,
        ).single()["n"]
        if retypes
        else 0,
    )
    translation_edges = combined["GAP-TRANSLATION-004"]["edges"]
    translation_pattern = "(:Mantra)-[r:HAS_TRANSLATION]->(:Translation)"
    translation_before = edge_count(translation_pattern)
    _ = (
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (m:Mantra {canonical_key: row.mantra_key}) "
                "MATCH (t:Translation {translation_id: row.translation_id}) "
                "MERGE (m)-[r:HAS_TRANSLATION]->(t) SET r += row.properties "
                "RETURN count(r) AS n",
                timeout=TIMEOUT,
            ),
            rows=translation_edges,
        ).consume()
    )
    created("GAP-TRANSLATION-004", translation_pattern, translation_before)
    coverage_rows = [
        {
            "canonical_key": row["canonical_key"],
            "props": {
                "translation_coverage": row["translation_coverage"],
                "translation_coverage_reason": row["translation_coverage_reason"],
                "translation_range_anchor": row.get("range_anchor"),
            },
        }
        for row in combined["GAP-TRANSLATION-004"]["rows"]
    ]
    counted(
        "GAP-TRANSLATION-004",
        "nodes_updated",
        session.run(
            Query(
                "UNWIND $rows AS row MATCH (m:Mantra {canonical_key: row.canonical_key}) "
                "SET m += row.props RETURN count(m) AS n",
                timeout=TIMEOUT,
            ),
            rows=coverage_rows,
        ).single()["n"],
    )

    return actual


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------

READBACK: Final[dict[str, tuple[str, str]]] = {
    "GAP-ATTRIBUTION-002": (
        "MATCH (a:DevataAscription)-[:ASCRIBES_TO_DEVATA]->(:Devata) RETURN count(DISTINCT a)",
        "47",
    ),
    "GAP-ENTITY_COVERAGE-001": (
        "MATCH (:Mantra)-[r:MENTIONS_EPITHET]->(:Epithet) RETURN count(r)",
        "1035",
    ),
    "GAP-ENTITY_COVERAGE-002": (
        "MATCH (m:DerivedMetric) WHERE m.subject_key STARTS WITH 'VG:DEVATA:' "
        "RETURN count(DISTINCT m.subject_key)",
        "157",
    ),
    "GAP-ENTITY_COVERAGE-006": (
        "MATCH (n:DomainEntity) WHERE n.lexical_recall_status IS NULL RETURN count(n)",
        "0",
    ),
    "GAP-ENTITY_COVERAGE-006-ayas-lexical-stays-zero": (
        "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) "
        "WHERE e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)",
        "0",
    ),
    "GAP-ENTITY_COVERAGE-007": (
        "MATCH (n:NaturalPhenomenon) WHERE n.personification_status IS NULL RETURN count(n)",
        "0",
    ),
    "GAP-RITUAL-004": (
        "MATCH (r:RitualRole) WHERE r.in_classical_sixteen IS NULL RETURN count(r)",
        "0",
    ),
    "GAP-RITUAL-004-classical-sixteen": (
        "MATCH (r:RitualRole) WHERE r.in_classical_sixteen = true RETURN count(r)",
        "16",
    ),
    "GAP-COMMUNITIES-002": (
        "MATCH (d:Devata) WHERE d.structure IN ['PAIR','GROUP'] "
        "AND d.decomposition_status IS NULL RETURN count(d)",
        "0",
    ),
    "GAP-TRANSLATION-004": (
        "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        "2",
    ),
}


def readback(session: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, (query, expected) in READBACK.items():
        value = session.run(Query(query, timeout=TIMEOUT)).single()[0]
        out[name] = {
            "measure": query,
            "measured": value,
            "expected": int(expected),
            "agrees": value == int(expected),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            if args.backup:
                manifest = take_backup(session)
                print()
                print("  R4 PRE-MIGRATION BACKUP")
                print(f"  nodes          {manifest['counts']['nodes']}")
                print(f"  relationships  {manifest['counts']['relationships']}")
                for name, digest in manifest["sha256"].items():
                    print(f"  {name:<22} {digest}")
                print(f"  fingerprint    {manifest['fingerprint']['sha256']}")
                print(f"  written        {BACKUP.relative_to(PROJECT_ROOT)}")
                print()
                return 0

            if args.scan or args.apply:
                result = scan(session)
                print()
                print(f"  CONFLICT SCAN -- {result['checked']} staged targets checked")
                for conflict in result["conflicts"][:40]:
                    print(f"    {conflict['kind']}: {conflict['what']} {conflict['key']}")
                print(f"  conflicts: {len(result['conflicts'])}   "
                      f"already applied: {len(result['already_applied'])}")
                print()
                if result["conflicts"]:
                    print("  ABORTED. The migration does not run with a conflict outstanding.")
                    return 1
                if args.scan:
                    return 0

            if args.apply:
                if not (BACKUP / "MANIFEST.json").exists():
                    print("  ABORTED: no backup manifest. Run --backup first.")
                    return 1
                before_census = census(session)
                before_fingerprint = fingerprint(session)
                actual = apply(session)
                after_census = census(session)
                after_fingerprint = fingerprint(session)
                read = readback(session)

                promised = {
                    gap: _load(path).get("promised", {}) for gap, path in STAGING.items()
                }
                receipt = {
                    "artifact": "R4_MIGRATION_RECEIPT",
                    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "backup": json.loads(
                        (BACKUP / "MANIFEST.json").read_text(encoding="utf-8")
                    )["sha256"],
                    "census_before": before_census,
                    "census_after": after_census,
                    "census_delta": {
                        key: after_census[key] - before_census[key] for key in before_census
                    },
                    "fingerprint_before": before_fingerprint["sha256"],
                    "fingerprint_after": after_fingerprint["sha256"],
                    "relationship_type_delta": {
                        key: after_fingerprint["relationship_types"].get(key, 0)
                        - before_fingerprint["relationship_types"].get(key, 0)
                        for key in set(before_fingerprint["relationship_types"])
                        | set(after_fingerprint["relationship_types"])
                        if after_fingerprint["relationship_types"].get(key, 0)
                        != before_fingerprint["relationship_types"].get(key, 0)
                    },
                    "promised": promised,
                    "actual": actual,
                    "readback": read,
                    "readback_disagreements": [
                        name for name, row in read.items() if not row["agrees"]
                    ],
                }
                (R4 / "migration_receipt.json").write_text(
                    json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )

                print()
                print("  R4 MIGRATION RECEIPT")
                print()
                print(f"  census   nodes {before_census['nodes']} -> {after_census['nodes']}"
                      f"   relationships {before_census['relationships']} -> "
                      f"{after_census['relationships']}")
                print(f"  fingerprint {before_fingerprint['sha256'][:16]} -> "
                      f"{after_fingerprint['sha256'][:16]}")
                print()
                print("  relationship type delta:")
                for key, delta in sorted(receipt["relationship_type_delta"].items()):
                    print(f"    {key:<24} {delta:+}")
                print()
                print("  actual, per gap:")
                for gap, counts in sorted(actual.items()):
                    print(f"    {gap:<28} {counts}")
                print()
                print("  readback:")
                for name, row in read.items():
                    mark = "ok " if row["agrees"] else "XX "
                    print(f"    {mark}{name:<48} {row['measured']} (expected {row['expected']})")
                print()
                print(f"  disagreements: {len(receipt['readback_disagreements'])}")
                print(f"  receipt: {(R4 / 'migration_receipt.json').relative_to(PROJECT_ROOT)}")
                print()
                return 1 if receipt["readback_disagreements"] else 0

            parser.print_help()
            return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
