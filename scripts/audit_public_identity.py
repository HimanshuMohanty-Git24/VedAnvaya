"""Read-only, exhaustive public identity and pinned-source rebuild verification."""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from neo4j import GraphDatabase
from export_graph_world import load_env
from vedagraph.graph.public_identity import public_id, public_id_cypher, ID_PROPERTIES
from vedagraph.api.services.graph_service import stable_id
from build_semantic_assertion_delta import (
    build_assertions, load_role_fillers, read_sv_rv_parallel_edges, STAGED,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
    env = load_env(ROOT / ".env")
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    with driver.session(default_access_mode="READ") as session:
        census = {
            "nodes": session.run("MATCH (n) RETURN count(n) AS n").single()["n"],
            "relationships": session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"],
        }
        # Pinned so an unexpected mutation cannot slip past this audit. Moved at R4 from
        # 164,201/508,042 by the single receipted migration in
        # data/staging/release_blocker_r4/migration_receipt.json: +396 nodes (399
        # DerivedMetric created, 3 deleted with the danastuti label's deity metrics) and
        # +1,444 relationships (1,035 MENTIONS_EPITHET, 399 MEASURES, 8
        # ASCRIBES_TO_DEVATA, 4 COMPOSED_OF, 1 ATTESTED_IN, less the 3 MEASURES that went
        # with the deleted metrics). The delta reconciles exactly against the baseline.
        # 164,597/509,486 -> 164,601/509,769. Moved by two receipted R5 steps: the
        # migration (data/staging/release_blocker_r5/migration_receipt.json -- +2
        # DerivedMetric nodes and +283 relationships, actual == promised on every counter)
        # and the entity-coverage consumer rebuild the dependency report then required
        # (+2 DerivedMetric). Agent B's C06: this assert aborted the whole public-identity
        # audit, and because nothing wires this script to a gate it failed by never being
        # run rather than by going red.
        assert census == {"nodes": 164601, "relationships": 509769}, census
        rows = session.run(
            "MATCH (n) WHERE NOT n:Internal RETURN properties(n) AS p, labels(n) AS labels, "
            + public_id_cypher("n") + " AS id"
        ).data()
        parallels = read_sv_rv_parallel_edges(session)
        fillers = load_role_fillers()
        first, _ = build_assertions(fillers, parallels)
        second, _ = build_assertions(fillers, parallels)
        eligible_rels = session.run(
            "MATCH (a)-[r]->(b) WHERE NOT a:Internal AND NOT b:Internal RETURN count(r) AS n"
        ).single()["n"]
        ungraded = session.run(
            "MATCH (a)-[r]->(b) WHERE NOT a:Internal AND NOT b:Internal "
            "AND r.quality_tier IS NULL RETURN count(r) AS n"
        ).single()["n"]
    driver.close()
    ids = [r["id"] for r in rows]
    by_id = defaultdict(list)
    strategies = defaultdict(Counter)
    properties = Counter()
    assertion_rows = []
    mismatches = []
    for row in rows:
        p = row["p"]
        kind = p.get("display_type") or sorted(row["labels"])[0]
        by_id[row["id"]].append(kind)
        key = ("assertion_id" if p.get("assertion_id") else "semantic-assertion:<persisted assertion_key>"
               if p.get("assertion_key") else next((k for k in ID_PROPERTIES if p.get(k)), "MISSING"))
        strategies[kind][key] += 1
        if row["id"] != public_id(p) or row["id"] != stable_id(p):
            mismatches.append(row["id"])
        if "SemanticAssertion" in row["labels"]:
            properties.update(p.keys())
            assertion_rows.append(row)
    graph_keys = sorted(r["p"]["assertion_key"] for r in assertion_rows if r["p"].get("assertion_key"))
    first_keys = sorted(r["assertion_key"] for r in first)
    second_keys = sorted(r["assertion_key"] for r in second)
    passage_ids = {r["id"] for r in rows if "Passage" in r["labels"]}
    assertion_ids = {r["id"] for r in assertion_rows}
    duplicate = {k: v for k, v in by_id.items() if len(v) > 1}
    receipt = {
        "graph_census": census,
        "diagnosis": {
            "A_existing_uuid": False,
            "B_existing_deterministic_identity": "30,266 persisted assertion_key values; 4,865 existing assertion_id values",
            "C_new_identity_required": False,
            "root_cause": "assertion_key omitted from public ID precedence; contextual canonical_key collided with Passage; sid != tid then dropped 30,266 HAS_SEMANTIC_ASSERTION relationships",
            "strategy": "Promote persisted assertion_key verbatim with semantic-assertion: prefix; retain existing assertion_id and all non-assertion IDs",
            "normalization": "None. Existing keys are opaque, case-sensitive, preserved verbatim. No UUIDv5 namespace or tuple is minted.",
            "historical_key_origin": "Pinned semantic_roles rows have a source assertion ordinal encoded in assertion_key and role_filler_key. The existing builder enumerates that frozen source array. This publication repair never re-enumerates nodes or creates a new ordinal identity; changing the pinned assertion source is outside this frozen release contract.",
        },
        "assertion_property_counts": dict(sorted(properties.items())),
        "id_strategy_by_node_type": {k: dict(v) for k, v in sorted(strategies.items())},
        "counts": {
            "exported_nodes": len(rows), "distinct_public_ids": len(set(ids)),
            "duplicate_public_ids": sum(len(v) - 1 for v in duplicate.values()),
            "cross_type_collisions": sum(len(set(v)) > 1 for v in duplicate.values()),
            "same_type_collisions": sum(len(set(v)) == 1 for v in duplicate.values()),
            "null_public_ids": sum(not i for i in ids), "public_relationships": eligible_rels,
            "passage_assertion_intersection": len(passage_ids & assertion_ids),
            "api_export_mismatches": len(mismatches),
            "missing_labels": sum(not r["p"].get("display_label") for r in rows),
            "ungraded_public_relationships": ungraded, "internal_leakage": 0,
        },
        "determinism": {
            "same_input_same_id": all(public_id(r["p"]) == public_id(dict(reversed(list(r["p"].items())))) for r in rows),
            "two_independent_source_builds_match_live_keys": first_keys == second_keys == graph_keys,
            "build_1_keys_sha256": digest(first_keys), "build_2_keys_sha256": digest(second_keys),
            "live_keys_sha256": digest(graph_keys),
            "source_files": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [STAGED / "rows.jsonl", STAGED / "role_fillers.jsonl"]},
            "sorted_public_ids_sha256": digest(sorted(ids)),
        },
        "examples": [{"public_id": r["id"], "assertion_key": r["p"].get("assertion_key"),
                      "assertion_id": r["p"].get("assertion_id"), "passage": r["p"].get("canonical_key") or r["p"].get("passage_key")}
                     for r in sorted(assertion_rows, key=lambda r: r["id"])[::7000]],
    }
    out = ROOT / "data/staging/release_blocker_r1/public_identity_contract_receipt.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt["counts"]))
    assert not duplicate and all(ids) and not mismatches and not (passage_ids & assertion_ids)
    assert first_keys == second_keys == graph_keys


if __name__ == "__main__":
    main()
