"""Optional Graph Data Science analytics over the enriched graph.

These are derived insights, never facts. PageRank does not tell you that Indra is
important to the Rigveda; it tells you that Indra's node has a lot of weighted in-edges in
*this projection*, which is a statement about how the graph was built at least as much as
about the corpus. So every number this module produces is written under an ``analytics_``
prefix, kept in its own artifact, and stamped with the projection and parameters that
produced it. Nothing downstream treats any of it as evidence.

Three properties make the results reproducible despite GDS being a concurrent engine:

* ``concurrency: 1`` on every algorithm. GDS's parallel implementations sum floating-point
  contributions in whatever order threads finish, so a multi-threaded PageRank differs in
  the last few digits between runs and a multi-threaded Louvain can differ in actual
  community assignment. Single-threaded is slower and the graph is small.
* An explicit seed wherever the algorithm accepts one. GDS 2.13's Louvain does not: it
  rejects ``randomSeed`` as an unknown key, and its determinism comes from
  ``concurrency: 1`` alone. Betweenness does take ``samplingSeed`` and is given one.
* A named, versioned projection. Community ids are only meaningful relative to the graph
  they were computed on, and silently changing which edges are projected while keeping the
  ids would be the most misleading thing this module could do.

GDS is optional. :func:`gds_available` is checked before anything here runs, and the
enrichment pipeline's own analytics in :mod:`vedagraph.enrich.analytics` are computed in
Python and do not depend on it. If the plugin is absent the report says so and the release
is unaffected.
"""

from __future__ import annotations

import logging
from typing import Any, Final

logger = logging.getLogger(__name__)

#: Bumped when the projected node labels or relationship types change. Community ids from
#: two different projection versions are not comparable and must not be diffed.
PROJECTION_VERSION: Final = "vedagraph-enrichment-gds-v1"

#: The in-memory graph name. Dropped and rebuilt on every run rather than reused, because a
#: stale projection silently answers questions about a graph that no longer exists.
GRAPH_NAME: Final = "vedagraph_enrichment"

#: What gets projected. Deliberately not the whole graph: TextVersion and Translation are
#: leaves that carry text, and including them makes every mantra's centrality a function of
#: how many editions happen to have been ingested for it rather than of anything in the
#: corpus. The projection is the semantic and structural skeleton.
PROJECTED_NODES: Final[tuple[str, ...]] = (
    "Passage",
    "Devata",
    "Rishi",
    "Chandas",
    "Concept",
    "Formula",
)

PROJECTED_RELATIONSHIPS: Final[tuple[str, ...]] = (
    "CONTAINS",
    "HAS_DEVATA",
    "HAS_RISHI",
    "HAS_CHANDAS",
    "USES_FORMULA",
    "ABOUT_CONCEPT",
    "EXACT_PARALLEL_OF",
    "NEAR_PARALLEL_OF",
    "VARIANT_OF",
    "PARALLEL_TO",
)


def gds_available(session: Any) -> str:
    """Return the installed GDS version, or an empty string if the plugin is absent."""
    try:
        record = session.run("RETURN gds.version() AS version").single()
    except Exception as exc:
        # Any driver or server error here means the same thing: no GDS on this server.
        logger.info("GDS not available: %s", type(exc).__name__)
        return ""
    return str(record["version"]) if record else ""


def drop_projection(session: Any) -> None:
    """Drop the in-memory projection if it exists."""
    session.run(
        "CALL gds.graph.drop($name, false) YIELD graphName RETURN graphName",
        name=GRAPH_NAME,
    )


def _present(session: Any) -> tuple[list[str], list[str]]:
    """Which of the intended labels and relationship types the database actually has.

    ``gds.graph.project`` refuses the whole projection if any named label is absent, and a
    label is absent whenever a layer has not been loaded yet -- ``Concept`` and ``Formula``
    do not exist before the enrichment load. Filtering here means the analytics run against
    the structural graph alone rather than failing outright, and the caller is told exactly
    what was left out instead of silently getting a smaller graph.
    """
    labels = {record["label"] for record in session.run("CALL db.labels() YIELD label")}
    types = {
        record["relationshipType"]
        for record in session.run("CALL db.relationshipTypes() YIELD relationshipType")
    }
    return (
        [label for label in PROJECTED_NODES if label in labels],
        [rel for rel in PROJECTED_RELATIONSHIPS if rel in types],
    )


def build_projection(session: Any) -> dict[str, Any]:
    """Create the named in-memory projection, replacing any existing one.

    Projected UNDIRECTED. Centrality on the enriched graph should not depend on which way
    round a symmetric relationship happened to be written: ``EXACT_PARALLEL_OF`` between
    two mantras is one fact, and storing it as A->B rather than B->A is an artifact of
    sorting the pair by canonical key. Left directed, PageRank would systematically favour
    whichever key sorts later.
    """
    drop_projection(session)
    nodes, rels = _present(session)
    if not nodes or not rels:
        raise RuntimeError("no projectable labels or relationship types in this database")
    record = session.run(
        """
        CALL gds.graph.project($name, $nodes, $rels)
        YIELD graphName, nodeCount, relationshipCount
        RETURN nodeCount AS nodes, relationshipCount AS rels
        """,
        name=GRAPH_NAME,
        nodes=nodes,
        rels={rel: {"orientation": "UNDIRECTED"} for rel in rels},
    ).single()
    if record is None:
        raise RuntimeError("GDS projection returned no result")
    counts: dict[str, Any] = {
        "nodes": int(record["nodes"]),
        "relationships": int(record["rels"]),
        "projected_labels": nodes,
        "projected_types": rels,
        "absent_labels": [label for label in PROJECTED_NODES if label not in nodes],
        "absent_types": [rel for rel in PROJECTED_RELATIONSHIPS if rel not in rels],
    }
    logger.info("GDS projection %s: %s", GRAPH_NAME, counts)
    return counts


def pagerank(session: Any, limit: int = 50) -> list[dict[str, Any]]:
    """Top nodes by PageRank over the undirected enriched projection."""
    return [
        {
            "labels": sorted(record["labels"]),
            "key": record["key"],
            "label_text": record["label_text"],
            "score": round(float(record["score"]), 8),
        }
        for record in session.run(
            """
            CALL gds.pageRank.stream($name, {concurrency: 1, maxIterations: 20,
                                              dampingFactor: 0.85, tolerance: 1e-7})
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS n, score
            RETURN labels(n) AS labels,
                   coalesce(n.canonical_key, n.entity_key, n.concept_id, n.formula_id) AS key,
                   coalesce(n.canonical_citation, n.preferred_label, n.preferred_label_en,
                            n.display_form, '') AS label_text,
                   score
            ORDER BY score DESC, key ASC
            LIMIT $limit
            """,
            name=GRAPH_NAME,
            limit=limit,
        )
    ]


def degree_centrality(session: Any, limit: int = 50) -> list[dict[str, Any]]:
    """Top nodes by undirected degree."""
    return [
        {
            "labels": sorted(record["labels"]),
            "key": record["key"],
            "label_text": record["label_text"],
            "score": round(float(record["score"]), 4),
        }
        for record in session.run(
            """
            CALL gds.degree.stream($name, {concurrency: 1})
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS n, score
            RETURN labels(n) AS labels,
                   coalesce(n.canonical_key, n.entity_key, n.concept_id, n.formula_id) AS key,
                   coalesce(n.canonical_citation, n.preferred_label, n.preferred_label_en,
                            n.display_form, '') AS label_text,
                   score
            ORDER BY score DESC, key ASC
            LIMIT $limit
            """,
            name=GRAPH_NAME,
            limit=limit,
        )
    ]


def louvain_communities(session: Any, top_communities: int = 25) -> dict[str, Any]:
    """Louvain community detection, summarised rather than dumped.

    Returns the community size distribution and a representative sample of members per
    community. The full assignment is 90k rows and is not useful in a report; what a reader
    wants is "what kind of thing is in community 7", which the samples answer.

    The community ids are meaningful only within one run of one projection version. They
    are not stable identifiers and must never be stored as though they were.
    """
    rows = list(
        session.run(
            """
            CALL gds.louvain.stream($name, {concurrency: 1, maxLevels: 10,
                                            tolerance: 1e-7})
            YIELD nodeId, communityId
            WITH communityId, gds.util.asNode(nodeId) AS n
            RETURN communityId AS community,
                   count(*) AS size,
                   collect(coalesce(n.preferred_label, n.preferred_label_en, n.display_form,
                                    n.canonical_citation, n.canonical_key))[0..8] AS sample
            ORDER BY size DESC, community ASC
            LIMIT $limit
            """,
            name=GRAPH_NAME,
            limit=top_communities,
        )
    )
    total = session.run(
        """
        CALL gds.louvain.stats($name, {concurrency: 1})
        YIELD communityCount, modularity
        RETURN communityCount AS communities, modularity AS modularity
        """,
        name=GRAPH_NAME,
    ).single()
    return {
        "community_count": int(total["communities"]) if total else 0,
        "modularity": round(float(total["modularity"]), 6) if total else 0.0,
        "largest": [
            {
                "community": int(r["community"]),
                "size": int(r["size"]),
                "sample": [s for s in r["sample"] if s],
            }
            for r in rows
        ],
    }


def bridge_passages(session: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Passages that connect otherwise separate parts of the graph.

    Betweenness on 22k nodes is expensive and GDS's exact implementation is worse than
    quadratic, so this samples with ``samplingSize``. That makes the ranking approximate,
    which is stated here rather than implied by a precise-looking number: a sampled
    betweenness score is a rank hint, not a measurement.

    Restricted to ``:Mantra``. Without that filter the top of this list is Mandala and
    Sukta containers, whose betweenness is enormous because ``CONTAINS`` routes every path
    between their children through them. That is a fact about the hierarchy, not a
    discovery about the text, and it crowds out the leaf passages that genuinely bridge
    clusters.
    """
    return [
        {
            "key": record["key"],
            "citation": record["citation"],
            "veda": record["veda"],
            "score": round(float(record["score"]), 4),
        }
        for record in session.run(
            """
            CALL gds.betweenness.stream($name, {concurrency: 1, samplingSize: 2000,
                                                samplingSeed: 42})
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS n, score
            WHERE n:Mantra AND score > 0
            RETURN n.canonical_key AS key, n.canonical_citation AS citation,
                   n.veda AS veda, score
            ORDER BY score DESC, key ASC
            LIMIT $limit
            """,
            name=GRAPH_NAME,
            limit=limit,
        )
    ]


def node_similarity(session: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Passage pairs that share neighbours without necessarily sharing text.

    This is the query behind "passages semantically similar but lexically different": two
    mantras with the same deity, metre and concepts but no textual parallel. The topK bound
    is what keeps it from being an all-pairs similarity, which is exactly the graph
    explosion the brief forbids.
    """
    return [
        {
            "from_key": record["from_key"],
            "to_key": record["to_key"],
            "from_citation": record["from_citation"],
            "to_citation": record["to_citation"],
            "from_veda": record["from_veda"],
            "to_veda": record["to_veda"],
            "similarity": round(float(record["similarity"]), 6),
        }
        for record in session.run(
            """
            CALL gds.nodeSimilarity.stream($name, {concurrency: 1, topK: 3,
                                                   similarityCutoff: 0.6})
            YIELD node1, node2, similarity
            WITH gds.util.asNode(node1) AS a, gds.util.asNode(node2) AS b, similarity
            WHERE a:Passage AND b:Passage AND a.veda <> b.veda
              AND NOT (a)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF|PARALLEL_TO]-(b)
            RETURN a.canonical_key AS from_key, b.canonical_key AS to_key,
                   a.canonical_citation AS from_citation, b.canonical_citation AS to_citation,
                   a.veda AS from_veda, b.veda AS to_veda, similarity
            ORDER BY similarity DESC, from_key ASC, to_key ASC
            LIMIT $limit
            """,
            name=GRAPH_NAME,
            limit=limit,
        )
    ]


def run_analytics(session: Any) -> dict[str, Any]:
    """Run the whole optional analytics suite, or report why it did not run.

    Never raises for an absent plugin. An analytics layer that can take down a graph build
    is not optional in any sense that matters.
    """
    version = gds_available(session)
    if not version:
        return {
            "available": False,
            "reason": "the graph-data-science plugin is not installed on this server",
            "projection_version": PROJECTION_VERSION,
        }

    result: dict[str, Any] = {
        "available": True,
        "gds_version": version,
        "projection_version": PROJECTION_VERSION,
        "projected_nodes": list(PROJECTED_NODES),
        "projected_relationships": list(PROJECTED_RELATIONSHIPS),
    }
    try:
        result["projection"] = build_projection(session)
        result["pagerank"] = pagerank(session)
        result["degree_centrality"] = degree_centrality(session)
        result["communities"] = louvain_communities(session)
        result["bridge_passages"] = bridge_passages(session)
        result["node_similarity"] = node_similarity(session)
    finally:
        drop_projection(session)
    return result
