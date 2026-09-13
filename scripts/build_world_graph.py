"""Crawl the public API into the static graph the World View renders.

## Why a build step rather than a fetch

`GET /graph/neighborhood/{id}` is bounded on purpose. It caps fan-out per predicate at 50,
holds a hard node budget of 400, and stops at depth 2 because depth 3 from Indra reaches
most of the Rigveda. Those bounds are correct for a reader opening one node. They make a
whole-graph view impossible to assemble at request time: the World View needs every entity
at once, which is roughly 2,600 requests, and no reader is going to wait for that.

So the crawl happens once, here, and the result ships as a static file. This touches no
backend code and invents no endpoint. It reads exactly the documented, bounded surface any
client may read, and it writes down what it saw.

## What is in the world, and what is not

The graph holds about 108,000 nodes, but most of them are mantras and most of its edges are
containment or text-surface edges. A view of those is the corpus's table of contents drawn
as a hairball. The World View is the **entity** layer instead: deities, seers and their
families, concepts, rites and roles, substances, objects, places, plants, animals, metals,
conditions, and the rest. Those are the things a reader would actually want to see related
to one another, and their relations are real predicates rather than containment.

Formulas are excluded: 4,825 of them would swamp everything else, and a formula's interest
is its reach across collections, which the formula surface already shows better than a point
in space can.

## The honesty this file has to carry

Two facts have to survive into the artifact or the view will lie.

**Truncation.** Where a node's fan-out on a predicate hit the cap, the edge list for that
node is a sample, not a census. Every such case is recorded per node and per predicate, so
the view can say "this node has more" rather than silently drawing a smaller star.

**Exclusion.** A reader looking at 2,600 nodes and told it is "the knowledge graph" will
reasonably conclude the corpus holds 2,600 things. The manifest records what was left out
and why, for the view to state in the view rather than in a footnote nobody opens.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "frontend" / "public" / "data" / "world-graph.json"

DEFAULT_BASE = "http://127.0.0.1:8000/api/v1"
PAGE_SIZE = 200  # the enumeration endpoints' documented maximum
FAN_OUT = 50  # MAX_NEIGHBOURS_PER_TYPE, the documented per-predicate cap

# Excluded from the world, with the reason carried into the manifest so the view can state it.
#
# The last two are excluded on a measured finding, not a preference. A first crawl that kept
# them returned 1,776 isolated nodes out of 2,602, and 1,295 of those were metres and formula
# families at exactly 100% isolation. They are not isolated in the corpus. They are isolated
# in *this projection*, because every relation a metre has runs to a mantra and every relation
# a formula family has runs to a formula, and this view excludes both. Drawing them anyway
# would put 1,295 points on screen whose visible meaning is "related to nothing", which is
# false. They keep their own surfaces, where their real relations are the subject.
EXCLUDED_TYPES: dict[str, str] = {
    "formula": (
        "4,825 recurring wordings. Their interest is how far each one reaches across the "
        "four collections, which the formula surface shows directly. As points in a spatial "
        "view they would outnumber every other kind of thing by three to one."
    ),
    "formula_family": (
        "720 families of shared wording. Every relation a family has runs to its formulas, "
        "which this view excludes, so all 720 would be drawn unconnected. That would read as "
        "a finding about the corpus and it is a fact about this projection."
    ),
    "chandas": (
        "575 metres. Every relation a metre has runs to the mantras composed in it, and this "
        "view holds no mantras, so all 575 would be drawn unconnected. The metre layer is "
        "worth seeing against the corpus rather than against the entity layer."
    ),
}

# Node types that are corpus locations rather than knowledge objects. An edge with one of
# these at either end is a statement about where something occurs, not about what it relates
# to, and the World View is about the latter.
PASSAGE_TYPES = frozenset(
    {"MANTRA", "HYMN", "SECTION", "WORK", "PASSAGE", "TEXT_VERSION", "TRANSLATION"}
)


@dataclass
class Node:
    id: str
    type: str
    label: str
    description: str | None = None
    is_deity: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    #: Predicates whose fan-out from this node hit the cap, so its edges here are a sample.
    truncated: list[str] = field(default_factory=list)
    #: The node's real degree over traversable predicates, as the API reported it.
    total_degree: int | None = None


def get(base: str, path: str, retries: int = 3) -> dict[str, Any] | None:
    """One GET, with a short retry. Returns None on a 404, which is a real answer here."""
    url = f"{base}{path}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(0.4 * (attempt + 1))
    return None


def enumerate_universe(base: str) -> tuple[list[Node], list[dict[str, Any]]]:
    """Every entity and deity the world will contain, plus the population census."""
    universe: dict[str, Node] = {}
    census: list[dict[str, Any]] = []

    # Deities are not served by the generic entity surface: the Anukramani's devata slot
    # holds human patrons and praise labels beside the gods, and only the deity endpoints
    # apply the contract that resolves them. So they are fetched from their own endpoint.
    offset = 0
    while True:
        page = get(base, f"/devatas?limit={PAGE_SIZE}&offset={offset}")
        items = (page or {}).get("items") or []
        for item in items:
            universe[item["id"]] = Node(
                id=item["id"],
                type="DEVATA",
                label=item.get("display_label") or item["id"],
                description=item.get("short_description"),
                is_deity=True,
                metadata={
                    "axes": item.get("axes") or [],
                    "structure": item.get("structure"),
                    "passage_count": item.get("passage_count"),
                    "mentions": item.get("mentions_default_total"),
                },
            )
        if len(items) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    census.append({"type": "DEVATA", "slug": "devata", "included": True, "count": len(universe)})

    types = (get(base, "/entities") or {}).get("types") or []
    for entry in types:
        slug, count = entry["slug"], entry.get("count") or 0
        if slug in EXCLUDED_TYPES:
            census.append(
                {
                    "type": entry["type"],
                    "slug": slug,
                    "included": False,
                    "count": count,
                    "excluded_because": EXCLUDED_TYPES[slug],
                }
            )
            continue

        before = len(universe)
        offset = 0
        while True:
            page = get(base, f"/entities/{slug}?limit={PAGE_SIZE}&offset={offset}")
            items = (page or {}).get("items") or []
            for item in items:
                stable = item.get("id") or item.get("entity_key")
                if not stable or stable in universe:
                    continue
                universe[stable] = Node(
                    id=stable,
                    # The item's own type, never the slug's. These slugs are query views over
                    # a shared `VG:CONCEPT:` namespace rather than a partition of it, and they
                    # overlap: `/entities/place` returns a RIVER, `/entities/substance`
                    # returns an OFFERING. Taking the slug's type instead collapsed fifteen
                    # distinct kinds into CONCEPT on a first run, because `concept` is crawled
                    # first and the dedup below then keeps its label for everything after.
                    type=item.get("type") or entry["type"],
                    label=item.get("display_label") or stable,
                    description=item.get("short_description") or item.get("subtitle"),
                    metadata={
                        "passage_count": item.get("passage_count"),
                        "label_iast": item.get("label_iast"),
                        "kind": item.get("kind"),
                    },
                )
            if len(items) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        census.append(
            {
                "type": entry["type"],
                "slug": slug,
                "included": True,
                "count": count,
                "collected": len(universe) - before,
            }
        )

    return list(universe.values()), census


def crawl(base: str, nodes: list[Node], workers: int) -> list[dict[str, Any]]:
    """Expand every node's depth-1 neighbourhood and keep the entity-to-entity edges."""
    index = {node.id: node for node in nodes}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    failures: list[str] = []

    def expand(node: Node) -> tuple[Node, dict[str, Any] | None]:
        quoted = urllib.parse.quote(node.id, safe="")
        try:
            payload = get(base, f"/graph/neighborhood/{quoted}?depth=1&limit_per_type={FAN_OUT}")
        except Exception:  # noqa: BLE001 - one bad node must not abandon 2,600 good ones
            return node, None
        return node, payload

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for node, payload in pool.map(expand, nodes):
            done += 1
            if done % 250 == 0:
                print(f"    {done}/{len(nodes)} expanded")
            if payload is None:
                failures.append(node.id)
                continue

            bounds = payload.get("bounds") or {}
            node.total_degree = bounds.get("total_degree")
            kinds = {item["id"]: item.get("type") for item in payload.get("nodes") or []}

            for edge in payload.get("edges") or []:
                source, target = edge.get("source"), edge.get("target")
                if source not in index or target not in index:
                    continue  # one end is a passage, or a node outside the world
                if kinds.get(source) in PASSAGE_TYPES or kinds.get(target) in PASSAGE_TYPES:
                    continue
                if source == target:
                    continue

                predicate = edge.get("type") or "RELATED_TO"
                # Undirected key: the same relation is reported from both endpoints, and a
                # world view drawing it twice would double the apparent density.
                pair = (source, target) if source < target else (target, source)
                key = (pair[0], pair[1], predicate)
                if key in edges:
                    continue
                edges[key] = {
                    "s": pair[0],
                    "t": pair[1],
                    "p": predicate,
                    "label": edge.get("label"),
                    "directed_from": source,
                    "confidence_basis": edge.get("confidence_basis"),
                    "score": edge.get("score"),
                }

            # Only record truncation on predicates that can produce an entity-to-entity edge.
            # HAS_DEVATA truncating at 50 says nothing about the world view, because every
            # one of those edges ends on a mantra and is dropped a few lines above.
            drawn = {e["p"] for e in edges.values() if node.id in (e["s"], e["t"])}
            node.truncated = sorted(set(bounds.get("truncated_types") or []) & drawn)

    if failures:
        print(f"    {len(failures)} nodes could not be expanded")
    return list(edges.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    started = time.perf_counter()
    print("  enumerating the entity population")
    nodes, census = enumerate_universe(args.base)
    print(f"    {len(nodes)} nodes across {sum(1 for c in census if c['included'])} types")

    print("  expanding neighbourhoods")
    edges = crawl(args.base, nodes, args.workers)

    degree: Counter[str] = Counter()
    for edge in edges:
        degree[edge["s"]] += 1
        degree[edge["t"]] += 1

    # Isolated nodes are kept. A concept the corpus names but never relates to anything else
    # is a true fact about this graph, and dropping it would quietly raise the apparent
    # connectedness of everything that survived.
    isolated = sum(1 for node in nodes if degree[node.id] == 0)
    by_predicate = Counter(edge["p"] for edge in edges)
    truncated_nodes = [node.id for node in nodes if node.truncated]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "manifest": {
                    "built_by": "scripts/build_world_graph.py",
                    "source": "the public read API, bounded exactly as any client reads it",
                    "fan_out_cap": FAN_OUT,
                    "depth": 1,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "isolated_nodes": isolated,
                    "nodes_with_truncated_predicates": len(truncated_nodes),
                    "edges_by_predicate": dict(by_predicate.most_common()),
                    "population_census": census,
                    "scope_statement": (
                        "This view holds the corpus's entity layer and the relations between "
                        "its members. It is not the whole graph: passages, their containment "
                        "and their text surfaces are excluded, and so are formulas. An "
                        "absence here is an absence from the entity layer only."
                    ),
                    "truncation_statement": (
                        "Where a node's fan-out on a predicate reached the API's cap of "
                        f"{FAN_OUT}, its edges on that predicate are a sample. Those nodes "
                        "and predicates are named on the node itself."
                    ),
                },
                "nodes": [
                    {
                        "id": node.id,
                        "type": node.type,
                        "label": node.label,
                        "description": node.description,
                        "is_deity": node.is_deity,
                        "degree": degree[node.id],
                        "total_degree": node.total_degree,
                        "truncated": node.truncated,
                        "metadata": {k: v for k, v in node.metadata.items() if v not in (None, [])},
                    }
                    for node in sorted(nodes, key=lambda n: -degree[n.id])
                ],
                "edges": edges,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    size = args.out.stat().st_size
    print(f"\n  {len(nodes)} nodes, {len(edges)} edges, {isolated} isolated")
    print(f"  {len(by_predicate)} predicates, busiest: {by_predicate.most_common(5)}")
    print(f"  {len(truncated_nodes)} nodes carry a truncated predicate")
    print(f"  {args.out.relative_to(REPO_ROOT)}  {size / 1024:.0f} KB")
    print(f"  built in {time.perf_counter() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
