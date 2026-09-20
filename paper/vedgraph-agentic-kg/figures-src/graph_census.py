"""Live Neo4j census for the VedGraph manuscript.

Read-only. Emits JSON on stdout and writes paper/vedgraph-agentic-kg/supplementary/
census_*.csv. Every number quoted in the manuscript that describes the graph is
produced here, so that a reviewer can re-derive it with one command.

    python figures-src/graph_census.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "supplementary"


def main() -> int:
    load_dotenv(ROOT / ".env")
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {}

    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as s:
        result["nodes_total"] = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        result["relationships_total"] = s.run(
            "MATCH ()-[r]->() RETURN count(r) AS c"
        ).single()["c"]

        labels = s.run(
            "MATCH (n) UNWIND labels(n) AS l "
            "RETURN l AS label, count(*) AS n ORDER BY n DESC"
        ).data()
        result["labels"] = labels

        rels = s.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC"
        ).data()
        result["relationship_types"] = rels

        # Label-set signatures: a node's full label combination, which is what the
        # public/internal partition is actually expressed in.
        sigs = s.run(
            "MATCH (n) WITH apoc.text.join(apoc.coll.sort(labels(n)),'+') AS sig "
            "RETURN sig, count(*) AS n ORDER BY n DESC"
        ).data() if _has_apoc(s) else s.run(
            "MATCH (n) WITH labels(n) AS ls RETURN ls AS sig, count(*) AS n "
            "ORDER BY n DESC"
        ).data()
        result["label_signatures"] = sigs[:60]

    driver.close()

    _write_csv(OUT / "census_node_labels.csv", ["label", "n"], result["labels"])
    _write_csv(
        OUT / "census_relationship_types.csv", ["type", "n"], result["relationship_types"]
    )
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    return 0


def _has_apoc(session) -> bool:
    try:
        session.run("RETURN apoc.version()").single()
        return True
    except Exception:
        return False


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row[c] for c in cols})


if __name__ == "__main__":
    raise SystemExit(main())
