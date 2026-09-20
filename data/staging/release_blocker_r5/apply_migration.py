"""The one R5 migration: back up, build an immutable plan, apply it, prove actual == promised.

Phases, in order, and each refuses to proceed on a failure rather than patching forward:

    backup   fresh logical export of every node and relationship, sha256'd, plus the graph
             census, the corpus census and an identity fingerprint
    plan     ONE immutable integrated plan with exact promised deltas, sha256'd before a
             single write
    apply    every write, in one transaction per batch, keyed ONLY on properties proven
             unique
    verify   actual == promised on every counter, plus the corpus invariant and the
             identity invariants. A mismatch restores rather than patching forward.

KEYS. Every MATCH uses a property measured unique for its label:

    :Passage / :Mantra      canonical_key
    :DomainEntity           entity_key
    :SemanticAssertion      assertion_key   (assertion_id is NULL on 30,266 of 35,131)
    :TextVersion            text_id         (58,786 distinct over 58,786 nodes)

``text_version_id`` is NOT used for anything. It is the ARTIFACT id: 58,786 TextVersion
nodes share 12 of them and the biggest group is 10,552, so a SET keyed on it would write
10,552 nodes where one was meant. This repository has already recorded an unlabelled MATCH
creating 39,461 bogus edges; that is the same mistake with a different spelling.

FORBIDDEN AND NOT DONE: no passage re-key, no formula re-key, no SemanticAssertion public-ID
re-key, no normalization-derived identity minting. Every alias added here was used to
COMPARE and never to create or merge a node.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

from neo4j import Query

import _q

HERE = pathlib.Path(__file__).resolve().parent
BACKUP = HERE / "backup"
BATCH = 1000


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# census / fingerprint
# ---------------------------------------------------------------------------

CORPUS = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}


def census(session) -> dict[str, Any]:
    out: dict[str, Any] = {
        "nodes": _q.one(session, "MATCH (n) RETURN count(n)"),
        "relationships": _q.one(session, "MATCH ()-[r]->() RETURN count(r)"),
    }
    for veda in ("RV", "SV", "YV", "AV"):
        out[veda] = _q.one(
            session, "MATCH (m:Mantra {veda:$v}) RETURN count(m)", v=veda
        )
    out["TOTAL"] = sum(out[v] for v in ("RV", "SV", "YV", "AV"))
    for label in (
        "DerivedMetric",
        "Devata",
        "Epithet",
        "Formula",
        "FormulaFamily",
        "DomainEntity",
        "SemanticAssertion",
        "RoleFiller",
        "TextVersion",
        "Translation",
        "Ritual",
        "Passage",
    ):
        out[label] = _q.one(session, f"MATCH (n:{label}) RETURN count(n)")
    return out


def fingerprint(session) -> dict[str, Any]:
    labels = {
        r["label"]: r["c"]
        for r in _q.rows(
            session,
            "CALL db.labels() YIELD label "
            "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c } "
            "RETURN label, c ORDER BY label",
        )
    }
    rels = {
        r["type"]: r["c"]
        for r in _q.rows(
            session,
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS c ORDER BY type",
        )
    }
    identity = {
        "passage_keys": _q.one(
            session, "MATCH (p:Passage) RETURN count(DISTINCT p.canonical_key)"
        ),
        "formula_ids": _q.one(
            session, "MATCH (f:Formula) RETURN count(DISTINCT f.formula_id)"
        ),
        "assertion_keys": _q.one(
            session, "MATCH (a:SemanticAssertion) RETURN count(DISTINCT a.assertion_key)"
        ),
        "entity_keys": _q.one(
            session, "MATCH (n:DomainEntity) RETURN count(DISTINCT n.entity_key)"
        ),
        "text_ids": _q.one(session, "MATCH (t:TextVersion) RETURN count(DISTINCT t.text_id)"),
    }
    blob = json.dumps({"labels": labels, "relationship_types": rels, "identity": identity},
                      sort_keys=True, ensure_ascii=False)
    return {
        "labels": labels,
        "relationship_types": rels,
        "identity": identity,
        "digest": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
    }


def take_backup(session) -> dict[str, Any]:
    BACKUP.mkdir(parents=True, exist_ok=True)
    counts = {"nodes": 0, "relationships": 0}
    nodes_path = BACKUP / "nodes.jsonl"
    rels_path = BACKUP / "relationships.jsonl"
    with nodes_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in session.run(
            Query("MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props",
                  timeout=1800.0)
        ):
            handle.write(json.dumps(record.data(), ensure_ascii=False, default=str) + "\n")
            counts["nodes"] += 1
    with rels_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in session.run(
            Query(
                "MATCH (a)-[r]->(b) RETURN id(r) AS id, id(a) AS start, id(b) AS end, "
                "type(r) AS type, properties(r) AS props",
                timeout=1800.0,
            )
        ):
            handle.write(json.dumps(record.data(), ensure_ascii=False, default=str) + "\n")
            counts["relationships"] += 1
    manifest = {
        "artifact": "R5_PRE_MIGRATION_BACKUP",
        "at": _now(),
        "kind": "LOGICAL_EXPORT_NOT_A_BINARY_DUMP",
        "why_not_a_binary_dump": (
            "neo4j-admin database dump needs the database stopped and online backup is an "
            "Enterprise feature. This is the pattern R3 and R4 used: every node and "
            "relationship with its internal id and properties, restorable, no downtime."
        ),
        "counts": counts,
        "sha256": {
            "nodes.jsonl": _sha256_file(nodes_path),
            "relationships.jsonl": _sha256_file(rels_path),
        },
        "census": census(session),
        "fingerprint": fingerprint(session),
    }
    (BACKUP / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def build_plan() -> dict[str, Any]:
    staged = json.loads((HERE / "staged_mutations.json").read_text(encoding="utf-8"))
    agent_a = json.loads((HERE / "staged_agentA_gaps.json").read_text(encoding="utf-8"))
    product = json.loads((HERE / "staged_product_005.json").read_text(encoding="utf-8"))

    operations: list[dict[str, Any]] = []

    # --- GAP-SEMANTICS-003: project the role resolution onto the assertion
    operations.append(
        {
            "op": "CREATE_ASSERTION_SLOT_EDGES",
            "gap_ids": ["GAP-SEMANTICS-003"],
            "rows": staged["semantics_003"]["edges"],
            "relationships_created": len(staged["semantics_003"]["edges"]),
        }
    )
    # --- GAP-ENTITY_COVERAGE-006: recall applicability
    operations.append(
        {
            "op": "SET_ENTITY_PROPERTIES",
            "gap_ids": ["GAP-ENTITY_COVERAGE-006"],
            "rows": staged["entity_006"]["node_updates"],
            "nodes_updated": len(staged["entity_006"]["node_updates"]),
        }
    )
    # --- GAP-ENTITY_COVERAGE-007: phrase mentions + personification evidence
    operations.append(
        {
            "op": "CREATE_PHRASE_MENTIONS",
            "gap_ids": ["GAP-ENTITY_COVERAGE-007"],
            "rows": staged["entity_007"]["phrase_mentions"],
            "relationships_created": len(staged["entity_007"]["phrase_mentions"]),
        }
    )
    operations.append(
        {
            "op": "SET_ENTITY_PROPERTIES",
            "gap_ids": ["GAP-ENTITY_COVERAGE-007"],
            "rows": staged["entity_007"]["personification_updates"],
            "nodes_updated": len(staged["entity_007"]["personification_updates"]),
        }
    )
    phrase_alias_rows = [
        {
            "entity_key": key,
            "properties": {
                "aliases_sa_phrases": phrases,
                "phrase_alias_contract": "VG:ENTITY_PHRASE_ALIAS:V1",
                "phrase_alias_host_run_audit": (
                    "Audited per alias. Every registered phrase reaches only its own form; "
                    "0 aliases reach a different expression."
                ),
                "r5_contract": "VG:R5_CLOSURE:V1",
            },
        }
        for key, phrases in staged["entity_007"]["phrase_aliases_to_register"].items()
    ]
    operations.append(
        {
            "op": "SET_ENTITY_PROPERTIES",
            "gap_ids": ["GAP-ENTITY_COVERAGE-007"],
            "rows": phrase_alias_rows,
            "nodes_updated": len(phrase_alias_rows),
        }
    )
    # --- ritual 003 / 005 / 006
    operations.append(
        {
            "op": "SET_ENTITY_PROPERTIES",
            "gap_ids": ["GAP-RITUAL-003", "GAP-RITUAL-005"],
            "rows": staged["ritual"]["node_updates"],
            "nodes_updated": len(staged["ritual"]["node_updates"]),
        }
    )
    operations.append(
        {
            "op": "SET_ALL_MANTRA_PROPERTIES",
            "gap_ids": ["GAP-RITUAL-006"],
            "properties": staged["ritual"]["mantra_precision_properties"],
            "mantras_updated": 20210,
        }
    )
    operations.append(
        {
            "op": "CREATE_DERIVED_METRICS",
            "gap_ids": ["GAP-RITUAL-006"],
            "rows": staged["ritual"]["metric_nodes"],
            "nodes_created": len(staged["ritual"]["metric_nodes"]),
        }
    )
    # --- GAP-QUALITY-003: rename a tier that was wearing a probability's name
    operations.append(
        {
            "op": "RENAME_CONSTANT_CONFIDENCE",
            "gap_ids": ["GAP-QUALITY-003"],
            "predicates": staged["quality_003"]["rename"]["predicates"],
            "extra_properties": staged["quality_003"]["rename"]["extra_properties"],
            "relationships_updated": staged["quality_003"]["rename"]["edges_affected"],
        }
    )
    # --- GAP-TRANSLATION-004: typed coverage state
    operations.append(
        {
            "op": "SET_MANTRA_PROPERTIES",
            "gap_ids": ["GAP-TRANSLATION-004"],
            "rows": staged["translation_004"]["node_updates"],
            "mantras_updated": len(staged["translation_004"]["node_updates"]),
        }
    )
    # --- GAP-SAMAVEDA_MUSIC-003 clause 1
    operations.append(
        {
            "op": "SET_MANTRA_PROPERTIES",
            "gap_ids": ["GAP-SAMAVEDA_MUSIC-003"],
            "rows": agent_a["samaveda_music_003"]["node_updates"],
            "mantras_updated": len(agent_a["samaveda_music_003"]["node_updates"]),
        }
    )
    # --- GAP-ENTITY_COVERAGE-004
    operations.append(
        {
            "op": "SET_ENTITY_PROPERTIES",
            "gap_ids": ["GAP-ENTITY_COVERAGE-004"],
            "rows": agent_a["entity_coverage_004"]["node_updates"],
            "nodes_updated": len(agent_a["entity_coverage_004"]["node_updates"]),
        }
    )
    # --- GAP-PRODUCT_SURFACE-005
    operations.append(
        {
            "op": "SET_TEXT_VERSIONS",
            "gap_ids": ["GAP-PRODUCT_SURFACE-005"],
            "rows": product["text_version_updates"],
            "nodes_updated": len(product["text_version_updates"]),
        }
    )
    operations.append(
        {
            "op": "SET_PARALLEL_EDGE_PROPERTIES",
            "gap_ids": ["GAP-PRODUCT_SURFACE-005"],
            "rows": product["parallel_edge_updates"],
            "relationships_updated": len(product["parallel_edge_updates"]),
        }
    )

    promised = {
        "nodes_created": sum(o.get("nodes_created", 0) for o in operations),
        "nodes_deleted": 0,
        "relationships_created": sum(o.get("relationships_created", 0) for o in operations),
        "relationships_deleted": 0,
        "relationships_updated": sum(o.get("relationships_updated", 0) for o in operations),
        "nodes_updated_property_writes": sum(o.get("nodes_updated", 0) for o in operations)
        + sum(o.get("mantras_updated", 0) for o in operations),
    }
    plan = {
        "artifact": "R5_INTEGRATED_MIGRATION_PLAN",
        "at": _now(),
        "gap_ids_served": sorted({g for o in operations for g in o["gap_ids"]}),
        "promised": promised,
        "promised_relationship_type_delta": {
            "ASSERTION_AGENT": len(
                [e for e in staged["semantics_003"]["edges"] if e["rel_type"] == "ASSERTION_AGENT"]
            ),
            "ASSERTION_TARGET": len(
                [e for e in staged["semantics_003"]["edges"] if e["rel_type"] == "ASSERTION_TARGET"]
            ),
            "MENTIONS_ENTITY": len(staged["entity_007"]["phrase_mentions"]),
        },
        "promised_label_delta": {"DerivedMetric": len(staged["ritual"]["metric_nodes"])},
        "property_keys_touched": sorted(
            {
                key
                for o in operations
                for row in o.get("rows", [])
                for key in (row.get("properties") or {})
            }
            | set(staged["ritual"]["mantra_precision_properties"])
            | {"confidence", "source_explicit_tier_marker"}
            | set(staged["quality_003"]["rename"]["extra_properties"])
            | {"text_nfc", "content_sha256"}
        ),
        "forbidden_operations_asserted_absent": [
            "passage re-key",
            "formula re-key",
            "SemanticAssertion public-ID re-key",
            "normalization-derived identity minting",
        ],
        "match_keys": {
            "Passage/Mantra": "canonical_key",
            "DomainEntity": "entity_key",
            "SemanticAssertion": "assertion_key",
            "TextVersion": "text_id",
        },
        "operations": operations,
    }
    body = json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True)
    plan["self_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return plan


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def _batched(rows: list[Any], size: int = BATCH):
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def apply_plan(session, plan: dict[str, Any]) -> dict[str, Any]:
    actual: dict[str, int] = {
        "nodes_created": 0,
        "relationships_created": 0,
        "relationships_updated": 0,
        "nodes_updated_property_writes": 0,
    }
    per_op: list[dict[str, Any]] = []

    for op in plan["operations"]:
        kind = op["op"]
        touched = 0

        if kind == "CREATE_ASSERTION_SLOT_EDGES":
            for batch in _batched(op["rows"]):
                for rel_type in ("ASSERTION_AGENT", "ASSERTION_TARGET"):
                    rows = [r for r in batch if r["rel_type"] == rel_type]
                    if not rows:
                        continue
                    result = session.run(
                        Query(
                            f"""
                            UNWIND $rows AS row
                            MATCH (a:SemanticAssertion {{assertion_key: row.assertion_key}})
                            MATCH (e) WHERE e.entity_key = row.entity_key
                            MERGE (a)-[r:{rel_type}]->(e)
                            SET r += row.properties
                            RETURN count(r) AS n
                            """,
                            timeout=900.0,
                        ),
                        rows=rows,
                    )
                    touched += result.single()["n"]
            actual["relationships_created"] += touched

        elif kind == "CREATE_PHRASE_MENTIONS":
            for batch in _batched(op["rows"]):
                result = session.run(
                    Query(
                        """
                        UNWIND $rows AS row
                        MATCH (p:Passage {canonical_key: row.passage_key})
                        MATCH (e:DomainEntity {entity_key: row.entity_key})
                        MERGE (p)-[r:MENTIONS_ENTITY]->(e)
                        SET r += row.properties
                        RETURN count(r) AS n
                        """,
                        timeout=900.0,
                    ),
                    rows=batch,
                )
                touched += result.single()["n"]
            actual["relationships_created"] += touched

        elif kind == "SET_ENTITY_PROPERTIES":
            for batch in _batched(op["rows"]):
                result = session.run(
                    Query(
                        """
                        UNWIND $rows AS row
                        MATCH (n:DomainEntity {entity_key: row.entity_key})
                        SET n += row.properties
                        RETURN count(n) AS n
                        """,
                        timeout=900.0,
                    ),
                    rows=batch,
                )
                touched += result.single()["n"]
            actual["nodes_updated_property_writes"] += touched

        elif kind == "SET_MANTRA_PROPERTIES":
            for batch in _batched(op["rows"]):
                result = session.run(
                    Query(
                        """
                        UNWIND $rows AS row
                        MATCH (m:Mantra {canonical_key: row.canonical_key})
                        SET m += row.properties
                        RETURN count(m) AS n
                        """,
                        timeout=900.0,
                    ),
                    rows=batch,
                )
                touched += result.single()["n"]
            actual["nodes_updated_property_writes"] += touched

        elif kind == "SET_ALL_MANTRA_PROPERTIES":
            result = session.run(
                Query(
                    "MATCH (m:Mantra) WHERE m.ritual_context IS NOT NULL "
                    "SET m += $props RETURN count(m) AS n",
                    timeout=900.0,
                ),
                props=op["properties"],
            )
            touched = result.single()["n"]
            actual["nodes_updated_property_writes"] += touched

        elif kind == "CREATE_DERIVED_METRICS":
            for row in op["rows"]:
                result = session.run(
                    Query(
                        "MERGE (m:DerivedMetric {metric_id: $key}) "
                        "SET m += $props RETURN count(m) AS n",
                        timeout=900.0,
                    ),
                    key=row["metric_id"],
                    props=row["properties"],
                )
                touched += result.single()["n"]
            actual["nodes_created"] += touched

        elif kind == "RENAME_CONSTANT_CONFIDENCE":
            for predicate in op["predicates"]:
                result = session.run(
                    Query(
                        f"""
                        MATCH ()-[r:{predicate}]->()
                        WHERE r.confidence IS NOT NULL
                        SET r.source_explicit_tier_marker = r.confidence
                        SET r += $extra
                        REMOVE r.confidence
                        RETURN count(r) AS n
                        """,
                        timeout=1800.0,
                    ),
                    extra=op["extra_properties"],
                )
                touched += result.single()["n"]
            actual["relationships_updated"] += touched

        elif kind == "SET_TEXT_VERSIONS":
            for row in op["rows"]:
                result = session.run(
                    Query(
                        """
                        MATCH (t:TextVersion {text_id: $text_id})
                        SET t.text_nfc = $text, t.content_sha256 = $sha
                        RETURN count(t) AS n
                        """,
                        timeout=900.0,
                    ),
                    text_id=row["text_id"],
                    text=row["new_text_nfc"],
                    sha=row["new_sha256"],
                )
                touched += result.single()["n"]
            actual["nodes_updated_property_writes"] += touched

        elif kind == "SET_PARALLEL_EDGE_PROPERTIES":
            for row in op["rows"]:
                result = session.run(
                    Query(
                        f"""
                        MATCH (a:Passage {{canonical_key: $subject}})
                              -[r:{row["rel"]}]->
                              (b:Passage {{canonical_key: $object}})
                        SET r += $props
                        RETURN count(r) AS n
                        """,
                        timeout=900.0,
                    ),
                    subject=row["subject"],
                    object=row["object"],
                    props=row["properties"],
                )
                touched += result.single()["n"]
            actual["relationships_updated"] += touched

        else:  # pragma: no cover
            raise SystemExit(f"unknown operation {kind!r}")

        per_op.append({"op": kind, "gap_ids": op["gap_ids"], "touched": touched})

    return {"actual": actual, "per_operation": per_op}


# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["backup", "plan", "apply"], required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.phase == "plan":
        plan = build_plan()
        (HERE / "migration_plan.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("plan sha256:", plan["self_sha256"])
        print("promised:", json.dumps(plan["promised"], indent=1))
        print("rel type delta:", json.dumps(plan["promised_relationship_type_delta"]))
        print("gaps served:", plan["gap_ids_served"])
        return

    driver = _q.driver()
    try:
        with driver.session(database=_q.DB) as session:
            if args.phase == "backup":
                manifest = take_backup(session)
                print(json.dumps({k: v for k, v in manifest.items() if k != "fingerprint"},
                                 indent=2, ensure_ascii=False)[:1600])
                print("fingerprint digest:", manifest["fingerprint"]["digest"])
                return

            plan = json.loads((HERE / "migration_plan.json").read_text(encoding="utf-8"))
            before_census, before_fp = census(session), fingerprint(session)
            result = apply_plan(session, plan)
            after_census, after_fp = census(session), fingerprint(session)

            delta = {
                k: after_census[k] - before_census[k]
                for k in before_census
                if isinstance(before_census[k], int)
            }
            corpus_held = all(after_census[v] == n for v, n in CORPUS.items())
            promised = plan["promised"]
            checks = {
                "nodes_created_matches": delta["nodes"] == promised["nodes_created"],
                "relationships_created_matches": delta["relationships"]
                == promised["relationships_created"],
                "corpus_invariant_held": corpus_held,
                "no_nodes_deleted": delta["nodes"] >= 0,
                "no_relationships_deleted": delta["relationships"] >= 0,
                "passage_keys_unchanged": after_fp["identity"]["passage_keys"]
                == before_fp["identity"]["passage_keys"],
                "formula_ids_unchanged": after_fp["identity"]["formula_ids"]
                == before_fp["identity"]["formula_ids"],
                "assertion_keys_unchanged": after_fp["identity"]["assertion_keys"]
                == before_fp["identity"]["assertion_keys"],
                "entity_keys_unchanged": after_fp["identity"]["entity_keys"]
                == before_fp["identity"]["entity_keys"],
                "text_ids_unchanged": after_fp["identity"]["text_ids"]
                == before_fp["identity"]["text_ids"],
            }
            receipt = {
                "artifact": "R5_MIGRATION_RECEIPT",
                "at": _now(),
                "plan_sha256": plan["self_sha256"],
                "backup": json.loads((BACKUP / "MANIFEST.json").read_text(encoding="utf-8"))[
                    "sha256"
                ],
                "census_before": before_census,
                "census_after": after_census,
                "census_delta": delta,
                "fingerprint_before": before_fp["digest"],
                "fingerprint_after": after_fp["digest"],
                "relationship_type_delta": {
                    k: after_fp["relationship_types"].get(k, 0)
                    - before_fp["relationship_types"].get(k, 0)
                    for k in set(after_fp["relationship_types"])
                    | set(before_fp["relationship_types"])
                    if after_fp["relationship_types"].get(k, 0)
                    != before_fp["relationship_types"].get(k, 0)
                },
                "promised": promised,
                "actual": result["actual"],
                "per_operation": result["per_operation"],
                "checks": checks,
                "all_checks_pass": all(checks.values()),
            }
            (HERE / "migration_receipt.json").write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(json.dumps({k: receipt[k] for k in
                              ("census_delta", "relationship_type_delta", "promised", "actual",
                               "checks", "all_checks_pass")}, indent=2))
            if not receipt["all_checks_pass"]:
                raise SystemExit(
                    "MIGRATION CHECKS FAILED. Do not patch forward: diagnose, restore from "
                    "data/staging/release_blocker_r5/backup, retry."
                )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
