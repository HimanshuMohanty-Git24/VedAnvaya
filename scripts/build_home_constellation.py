"""Cut a homepage-sized slice out of the world graph.

The homepage teaser must not pay for the World View. `world-graph.json` is 886 KB and 1,307
nodes, which is the right size for a surface built to explore and the wrong size for a
first-paint ornament that has to earn its place in the LCP budget.

So this takes a representative slice: the busiest deities, the entities they actually relate
to, and only the edges that join two members of the slice. The result is a few kilobytes and
it is real data, which matters more than it sounds. A teaser drawn from invented nodes would
be a picture of a graph rather than a picture of this graph, and the one thing the homepage
is trying to establish is that there is something real underneath.

Positions are not computed here. The teaser runs its own drift in the browser from a seeded
layout, because a frozen layout cannot respond to a pointer and responding to a pointer is
the whole interaction.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "frontend" / "public" / "data" / "world-graph.json"
OUT = REPO_ROOT / "frontend" / "public" / "data" / "home-constellation.json"

# Enough to read as a field, few enough to draw every frame without a worker.
DEITY_COUNT = 14
ENTITY_COUNT = 24
# Edges are the thing that gets away from you. A first cut kept every edge between chosen
# nodes and returned 686 of them across 44 nodes, which is not a constellation, it is a
# hairball, and at 88 KB it cost more than the rest of the homepage's data put together.
# Each node now keeps its strongest few and the rest are dropped.
MAX_EDGES_PER_NODE = 3

# Entity types the teaser prefers, in order. Selecting entities purely by how many deities
# they touch returns nothing but ACTION_PREDICATE, because a verb like MOVES_TO attaches to
# every god in the pantheon. True, and a picture of the corpus made entirely of verbs tells a
# reader nothing about what is in it. So the slice is diversified by type, with a cap on each.
PREFERRED_TYPES: tuple[str, ...] = (
    "CONCEPT",
    "RITUAL",
    "OFFERING",
    "SUBSTANCE",
    "NATURAL_PHENOMENON",
    "RIVER",
    "WEAPON",
    "PLANT",
    "ANIMAL",
    "DEITY_AXIS",
    "EPITHET",
    "OBJECT",
    "RITUAL_ROLE",
    "COSMIC_ENTITY",
    "PHILOSOPHICAL_CONCEPT",
)
MAX_PER_TYPE = 4

# ACTION_PREDICATE is excluded from the list above rather than merely deprioritised. Its
# members carry internal labels, MOVES_TO and BLESSES and "unmapped verbal root", which are
# the pipeline talking to itself. They belong in a graph a reader has chosen to open and not
# on the front of the site.

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"  missing {args.source}. Run scripts/build_world_graph.py first.")
        return 1

    world = json.loads(args.source.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in world["nodes"]}
    edges = world["edges"]

    adjacency: dict[str, list[dict]] = defaultdict(list)
    for edge in edges:
        adjacency[edge["s"]].append(edge)
        adjacency[edge["t"]].append(edge)

    # Deities first, by how much of the corpus actually names them, so the slice is led by
    # the figures a reader would recognise rather than by whoever happens to have the most
    # edges in this projection.
    deities = sorted(
        (n for n in world["nodes"] if n["type"] == "DEVATA"),
        key=lambda n: -(n.get("metadata", {}).get("mentions") or n.get("degree") or 0),
    )[:DEITY_COUNT]
    chosen = {n["id"] for n in deities}

    # Then the entities those deities reach, preferring ones reached by more than one, since
    # a node shared between two deities is what makes the picture look like a field rather
    # than like sixteen separate stars.
    shared: dict[str, int] = defaultdict(int)
    for deity in deities:
        for edge in adjacency[deity["id"]]:
            other = edge["t"] if edge["s"] == deity["id"] else edge["s"]
            if other not in chosen:
                shared[other] += 1

    per_type: dict[str, int] = defaultdict(int)
    rank = {name: index for index, name in enumerate(PREFERRED_TYPES)}
    candidates = sorted(
        shared.items(),
        key=lambda kv: (rank.get(nodes[kv[0]]["type"], len(rank)), -kv[1]),
    )
    for entity_id, _ in candidates:
        if len(chosen) - DEITY_COUNT >= ENTITY_COUNT:
            break
        kind = nodes[entity_id]["type"]
        if kind not in rank or per_type[kind] >= MAX_PER_TYPE:
            continue
        label = nodes[entity_id]["label"]
        # A second guard on the label itself, because a readable type can still hold an
        # unreadable member.
        if label.isupper() or "unmapped" in label.lower():
            continue
        per_type[kind] += 1
        chosen.add(entity_id)

    # Keep each node's strongest few edges rather than every edge between chosen nodes.
    # "Strongest" here is simply the busiest partner, which surfaces the relations a reader
    # would recognise and drops the long tail that turns the picture into a mesh.
    inside = [e for e in edges if e["s"] in chosen and e["t"] in chosen]
    degree_in_world = {i: nodes[i].get("degree") or 0 for i in chosen}
    per_node: dict[str, int] = defaultdict(int)
    kept_edges: list[dict] = []
    for edge in sorted(
        inside, key=lambda e: -(degree_in_world[e["s"]] + degree_in_world[e["t"]])
    ):
        if per_node[edge["s"]] >= MAX_EDGES_PER_NODE or per_node[edge["t"]] >= MAX_EDGES_PER_NODE:
            continue
        per_node[edge["s"]] += 1
        per_node[edge["t"]] += 1
        kept_edges.append({"s": edge["s"], "t": edge["t"], "p": edge["p"]})

    payload = {
        "note": (
            "A representative slice of the entity graph for the homepage teaser, cut by "
            "scripts/build_home_constellation.py. Not the whole graph and not a sample of "
            "it in any statistical sense: the busiest deities and the entities they reach."
        ),
        "nodes": [
            {
                "id": n["id"],
                "type": n["type"],
                "label": n["label"],
                "deity": bool(n.get("is_deity")),
                "degree": sum(1 for e in kept_edges if n["id"] in (e["s"], e["t"])),
            }
            for n in (nodes[i] for i in chosen)
        ],
        "edges": kept_edges,
    }

    # Drop anything the slice left unconnected. In the World View an isolated node is a
    # finding worth drawing; here it would just be a dot with nothing to say, on a surface
    # whose only job is to show that things connect.
    connected = {e["s"] for e in kept_edges} | {e["t"] for e in kept_edges}
    payload["nodes"] = [n for n in payload["nodes"] if n["id"] in connected]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    size = args.out.stat().st_size
    print(f"  {len(payload['nodes'])} nodes, {len(kept_edges)} edges, {size / 1024:.1f} KB")
    print(f"  {args.out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
