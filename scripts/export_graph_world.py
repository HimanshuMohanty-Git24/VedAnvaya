"""
Export the public knowledge graph as a flat world file, for the 3D World View to lay out.

## Why this exists rather than a new API endpoint

The served graph API is deliberately neighbourhood-scoped: depth is capped at 2, a response is
capped at 400 nodes, and - measured - it returns only edges incident to the root. A depth-1
response for Indra carries 262 edges and not one of them joins two neighbours to each other.
That shape is correct for the reader's apparatus, where the question is always "what is
attached to this one thing", and it is the wrong shape for a world: a force layout over a tree
draws a star, and the structure a reader is meant to see is exactly the part that is missing.

Rather than add a bulk endpoint to a mature read API, the world is exported once, offline,
from the same frozen store the API reads. The graph is frozen at 108,779 nodes / 265,295
relationships, so there is no freshness argument against a build artifact, and a build
artifact can carry things the API cannot compute per-request: a settled 3D layout, a degree
for every node, and a cluster assignment.

Nothing here writes. No schema operation is performed.

## What "public" means

Two thirds of the store is `:Internal` - text versions, translations, lemmas, QA issues - and
none of it is a subject anyone browses. 72,514 of 108,779 nodes carry that label. The world is
the remainder, 36,265 nodes, joined by the 193,821 relationships whose two ends are both
public. The API enforces this already; it is restated here because this script bypasses the
API and must not become the one place the rule is forgotten.

Usage:
    python scripts/export_graph_world.py [--out frontend/.world/world.raw.json]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from collections import Counter

from neo4j import GraphDatabase, Query

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "frontend" / ".world" / "world.raw.json"

# Publication identity is shared with the served graph API.
import sys
sys.path.insert(0, str(REPO / "src"))
from vedagraph.graph.public_identity import ID_PROPERTIES, public_id_cypher

ID_KEYS = ID_PROPERTIES
_coalesce = public_id_cypher


NODE_QUERY = f"""
MATCH (n)
WHERE NOT n:Internal
WITH n, {_coalesce("n")} AS id
RETURN id,
       coalesce(n.display_type, head(labels(n))) AS type,
       coalesce(n.display_label, n.preferred_label, n.label_en, n.canonical_citation,
                n.label_iast, id) AS label,
       n.veda AS veda,
       coalesce(n.is_deity, n.is_classified) AS is_deity,
       n.canonical_citation AS citation
ORDER BY id
"""

# Both ends public. The relationship type travels; nothing else does, because a renderer
# cannot draw evidence, and the evidence for any edge a reader actually asks about is one
# call away on /graph/relationships/{id}.
EDGE_QUERY = f"""
MATCH (a)-[e]->(b)
WHERE NOT a:Internal AND NOT b:Internal
WITH a, e, b,
     {_coalesce("a")} AS sid,
     {_coalesce("b")} AS tid
WHERE sid IS NOT NULL AND tid IS NOT NULL 
RETURN sid, tid, type(e) AS type
ORDER BY sid, tid, type
"""


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()

    env = load_env(REPO / ".env")
    driver = GraphDatabase.driver(
        env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"])
    )

    started = time.monotonic()
    with driver.session(default_access_mode="READ") as session:
        print("reading nodes ...", flush=True)
        nodes = [
            {
                "id": r["id"],
                "type": r["type"],
                "label": r["label"],
                **({"veda": r["veda"]} if r["veda"] else {}),
                **({"deity": True} if r["is_deity"] is True else {}),
                **({"cite": r["citation"]} if r["citation"] else {}),
            }
            for r in session.run(Query(NODE_QUERY, timeout=args.timeout))
        ]
        print(f"  {len(nodes):,} public nodes", flush=True)

        identifiers = [node["id"] for node in nodes]
        duplicates = {key: count for key, count in Counter(identifiers).items() if count > 1}
        if any(not key for key in identifiers) or duplicates:
            raise ValueError(f"Public identity contract violated: null/empty IDs or {len(duplicates)} duplicate IDs")
        print("reading relationships ...", flush=True)
        index = {node["id"]: i for i, node in enumerate(nodes)}
        edges: list[list[int | str]] = []
        dropped = 0
        for record in session.run(Query(EDGE_QUERY, timeout=args.timeout)):
            source = index.get(record["sid"])
            target = index.get(record["tid"])
            if source is None or target is None:
                # An end whose id key this script does not know. Counted, never guessed.
                dropped += 1
                continue
            edges.append([source, target, record["type"]])
        print(f"  {len(edges):,} public relationships ({dropped:,} dropped: unknown id key)")

    driver.close()

    if dropped:
        raise ValueError(f"Public export has {dropped} unknown endpoint references")

    # Degree is computed here because the API carries it for one node type only, and a world
    # needs it for all of them: it is what decides which nodes are drawn first and labelled.
    degree = [0] * len(nodes)
    for source, target, _ in edges:
        degree[source] += 1  # type: ignore[index]
        degree[target] += 1  # type: ignore[index]
    for node, value in zip(nodes, degree):
        node["deg"] = value

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": {"nodes": len(nodes), "edges": len(edges), "dropped_edges": dropped},
        "nodes": nodes,
        "edges": edges,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    size = args.out.stat().st_size
    isolated = sum(1 for d in degree if d == 0)
    print(
        f"\nwrote {args.out.relative_to(REPO)}  {size / 1e6:.1f} MB  "
        f"in {time.monotonic() - started:.1f}s"
    )
    print(f"  isolated nodes: {isolated:,}   max degree: {max(degree):,}")


if __name__ == "__main__":
    main()
