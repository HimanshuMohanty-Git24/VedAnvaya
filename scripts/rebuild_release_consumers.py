"""Rebuild read-only live-graph consumers without re-keying enrichment artifacts.

Cross-Veda uses the served API's typed matrix. Formula consumption snapshots the
frozen published nodes and their relationships; it does not run formula discovery
or create DerivedMetric nodes. Large reproducible output follows data/derived policy.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from neo4j import GraphDatabase
from export_graph_world import load_env
from vedagraph.api.services.insight_service import InsightService
from vedagraph.domain.queries import QUERIES_BY_NAME
from vedagraph.graph.public_identity import public_id_cypher

OUT = ROOT / "data/derived/release_blocker_r1"
RECEIPT = ROOT / "data/staging/release_blocker_r1/graph_consumer_rebuild_receipt.json"


class ReadOnlyRepository:
    def __init__(self, session):
        self.session = session
        self.queries = []

    def run(self, query, /, **parameters):
        # Reject a mutation before it reaches the driver, even on a standalone server
        # where READ routing alone is not an authorization boundary.
        stripped = re.sub(r"//[^\n]*|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "", query)
        if re.search(r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|LOAD|FOREACH)\b", stripped, re.I):
            raise RuntimeError("Consumer attempted a graph mutation")
        self.queries.append(hashlib.sha256(query.encode()).hexdigest())
        return self.session.run(query, **parameters).data()

    def run_one(self, query, /, **parameters):
        rows = self.run(query, **parameters)
        return rows[0] if rows else None

    def run_named(self, name, /, **parameters):
        query = QUERIES_BY_NAME[name]
        return self.run(query.cypher, **{**query.parameters, **parameters})


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(repository):
    cross = InsightService(repository).cross_veda_matrix().model_dump(mode="json")
    nodes = repository.run(
        "MATCH (n) WHERE n:Formula OR n:FormulaFamily "
        "RETURN " + public_id_cypher("n") + " AS id, labels(n) AS labels, properties(n) AS properties ORDER BY id"
    )
    edges = repository.run(
        "MATCH (a)-[r]->(b) WHERE (a:Formula OR a:FormulaFamily OR b:Formula OR b:FormulaFamily) "
        "AND NOT a:Internal AND NOT b:Internal RETURN "
        + public_id_cypher("a") + " AS source, " + public_id_cypher("b")
        + " AS target, type(r) AS type, properties(r) AS properties ORDER BY source, target, type"
    )
    edges.sort(key=lambda row: json.dumps(row, sort_keys=True))
    public_ids = {row["id"] for row in repository.run(
        "MATCH (n) WHERE NOT n:Internal RETURN " + public_id_cypher("n") + " AS id"
    )}
    assert len({n["id"] for n in nodes}) == len(nodes)
    assert all(e["source"] in public_ids and e["target"] in public_ids for e in edges)
    return cross, {"nodes": nodes, "edges": edges, "counts": {"nodes": len(nodes), "edges": len(edges)},
                   "duplicate_identifiers": 0, "unknown_references": 0}


def main():
    env = load_env(ROOT / ".env")
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]), notifications_min_severity="OFF")
    with driver.session(default_access_mode="READ") as session:
        repo = ReadOnlyRepository(session)
        census = {"nodes": repo.run_one("MATCH (n) RETURN count(n) AS n")["n"],
                  "relationships": repo.run_one("MATCH ()-[r]->() RETURN count(r) AS n")["n"]}
        assert census == {"nodes": 164201, "relationships": 508042}
        cross, formula = build(repo)
        cross_again, formula_again = build(repo)
        assert cross == cross_again and formula == formula_again
    driver.close()
    receipt = {"graph_census": census, "graph_mutation": False, "two_builds_identical": True,
               "query_hashes": sorted(set(repo.queries)), "consumers": {}}
    for name, filename, payload in [("cross-Veda matrices", "cross_veda_matrix.json", cross),
                                    ("formula / parallel / variant relations", "formula_consumer.json", formula)]:
        path = OUT / filename
        receipt["consumers"][name] = {"status": "CURRENT", "output": path.relative_to(ROOT).as_posix(),
                                      "output_hash": write(path, payload)}
    write(RECEIPT, receipt)
    print(json.dumps(receipt["consumers"]))


if __name__ == "__main__":
    main()
