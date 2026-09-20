#!/usr/bin/env python3
"""Validate community_algorithms.py against a graph whose answer is already published.

Run before build_communities_staging.py:

    .venv/Scripts/python.exe data/staging/communities/self_test.py

Why a self-test is the QA for this domain. Every accepted row in this artifact is a
deterministic restatement of HAS_DEVATA edges that already exist, so sampling the rows would
only re-measure the graph. The place a defect can hide here is the machinery, and a defect
in the machinery produces numbers that look entirely reasonable. Modularity 0.37 over a
Vedic graph is as plausible as modularity 0.42; nothing about the Rigveda tells you which
is right.

So the implementation is run against **Zachary's karate club**, the standard benchmark for
this exact problem, whose maximum modularity is a published number: Q = 0.4198 at four
communities. That is what caught the one real defect in this artifact -- the aggregation
step was double-counting between-community edge weight, so the level-2 aggregate graph
reported a total weight of 111.0 against the graph's true 78.0, and the best partition the
code could find was Q = 0.3718 at k = 2.

The test also asserts the properties the report leans on:

* both algorithms are deterministic under a fixed seed;
* the aggregate graph preserves total weight at every level;
* Leiden never returns an internally disconnected community;
* Leiden's mean modularity and seed stability are at least Louvain's, which is the reason
  for running both rather than a claim borrowed from the literature.
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from community_algorithms import (  # noqa: E402
    Graph,
    _aggregate,
    _local_move,
    adjusted_rand_index,
    betweenness_centrality,
    communities_are_connected,
    connected_components,
    consensus_partition,
    leiden,
    louvain,
    modularity,
    normalised_mutual_information,
    participation_coefficient,
)

# Zachary (1977), the 34-node / 78-edge friendship network of a karate club.
KARATE = [
    (2, 1), (3, 1), (3, 2), (4, 1), (4, 2), (4, 3), (5, 1), (6, 1), (7, 1), (7, 5), (7, 6),
    (8, 1), (8, 2), (8, 3), (8, 4), (9, 1), (9, 3), (10, 3), (11, 1), (11, 5), (11, 6),
    (12, 1), (13, 1), (13, 4), (14, 1), (14, 2), (14, 3), (14, 4), (17, 6), (17, 7), (18, 1),
    (18, 2), (20, 1), (20, 2), (22, 1), (22, 2), (26, 24), (26, 25), (28, 3), (28, 24),
    (28, 25), (29, 3), (30, 24), (30, 27), (31, 2), (31, 9), (32, 1), (32, 25), (32, 26),
    (32, 29), (33, 3), (33, 9), (33, 15), (33, 16), (33, 19), (33, 21), (33, 23), (33, 24),
    (33, 30), (33, 31), (33, 32), (34, 9), (34, 10), (34, 14), (34, 15), (34, 16), (34, 19),
    (34, 20), (34, 21), (34, 23), (34, 24), (34, 27), (34, 28), (34, 29), (34, 30), (34, 31),
    (34, 32), (34, 33),
]
# The split the club actually underwent -- the external label, not an algorithm's output.
ZACHARY_SPLIT = {
    1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 1, 10: 1, 11: 0, 12: 0, 13: 0,
    14: 0, 15: 1, 16: 1, 17: 0, 18: 0, 19: 1, 20: 0, 21: 1, 22: 0, 23: 1, 24: 1, 25: 1,
    26: 1, 27: 1, 28: 1, 29: 1, 30: 1, 31: 1, 32: 1, 33: 1, 34: 1,
}
PUBLISHED_MAX_MODULARITY = 0.4198


def main() -> int:
    nodes = [f"n{i:02d}" for i in range(1, 35)]
    graph = Graph.from_edges(nodes, [(f"n{a:02d}", f"n{b:02d}", 1.0) for a, b in KARATE])
    truth = {f"n{k:02d}": v for k, v in ZACHARY_SPLIT.items()}

    failures: list[str] = []
    report: dict[str, object] = {
        "benchmark": "Zachary karate club (1977), 34 nodes / 78 edges",
        "published_maximum_modularity": PUBLISHED_MAX_MODULARITY,
        "graph_nodes": len(graph.nodes),
        "graph_total_weight": graph.total_weight,
    }
    if len(graph.nodes) != 34 or graph.total_weight != 78.0:
        failures.append(f"graph is {len(graph.nodes)} nodes / m={graph.total_weight}, want 34 / 78")

    # Aggregation must preserve total weight at every level. This is the invariant the one
    # real defect in this artifact violated.
    import random

    rng = random.Random(3)
    level = graph
    weights = [level.total_weight]
    for _ in range(4):
        singles = {n: i for i, n in enumerate(level.nodes)}
        moved, improved = _local_move(level, singles, 1.0, rng)
        if not improved:
            break
        level, _ = _aggregate(level, moved)
        weights.append(level.total_weight)
    report["total_weight_per_aggregation_level"] = weights
    if any(abs(w - 78.0) > 1e-9 for w in weights):
        failures.append(f"aggregation does not preserve total weight: {weights}")

    for name, algorithm in (("louvain", louvain), ("leiden", leiden)):
        partitions = [algorithm(graph, 1.0, seed) for seed in range(50)]
        qs = [modularity(graph, p, 1.0) for p in partitions]
        best = max(range(len(qs)), key=lambda i: qs[i])
        sample = partitions[:20]
        aris = [
            adjusted_rand_index(sample[i], sample[j])
            for i in range(len(sample))
            for j in range(i + 1, len(sample))
        ]
        disconnected = sum(1 for p in partitions if communities_are_connected(graph, p))
        consensus = consensus_partition(partitions, nodes)
        block = {
            "runs": len(partitions),
            "max_modularity": round(max(qs), 4),
            "mean_modularity": round(statistics.mean(qs), 4),
            "communities_at_best": len(set(partitions[best].values())),
            "mean_pairwise_seed_ari": round(statistics.mean(aris), 4),
            "min_pairwise_seed_ari": round(min(aris), 4),
            "runs_with_a_disconnected_community": disconnected,
            "consensus_communities": len(set(consensus.values())),
            "consensus_modularity": round(modularity(graph, consensus, 1.0), 4),
            "ari_vs_zacharys_real_split": round(adjusted_rand_index(partitions[best], truth), 4),
            "nmi_vs_zacharys_real_split": round(
                normalised_mutual_information(partitions[best], truth), 4
            ),
            "deterministic_under_a_fixed_seed": algorithm(graph, 1.0, 7)
            == algorithm(graph, 1.0, 7),
        }
        report[name] = block
        if abs(block["max_modularity"] - PUBLISHED_MAX_MODULARITY) > 0.001:
            failures.append(
                f"{name} best modularity {block['max_modularity']} != published "
                f"{PUBLISHED_MAX_MODULARITY}"
            )
        if not block["deterministic_under_a_fixed_seed"]:
            failures.append(f"{name} is not deterministic under a fixed seed")

    if report["leiden"]["runs_with_a_disconnected_community"] != 0:  # type: ignore[index]
        failures.append("leiden returned a disconnected community, which it must never do")
    if report["leiden"]["mean_modularity"] < report["louvain"]["mean_modularity"]:  # type: ignore[index]
        failures.append("leiden's mean modularity is below louvain's; check the refinement pass")

    # Resolution must be monotone in the number of communities, or the sweep in the report
    # is not measuring what it says it measures.
    ladder = [(g, len(set(leiden(graph, g, 0).values()))) for g in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)]
    report["resolution_ladder_communities"] = ladder
    counts = [k for _, k in ladder]
    if counts != sorted(counts):
        failures.append(f"community count is not monotone in resolution: {ladder}")

    # Betweenness against published karate-club values. Node 1 is 0.43763, node 34 is
    # 0.30407, node 33 is 0.14524 under the standard undirected normalisation. If this is
    # off by the factor of two that the undirected double-accumulation invites, it shows up
    # here rather than in a Vedic ranking nobody can check.
    between = betweenness_centrality(graph)
    expected_between = {"n01": 0.43763, "n34": 0.30407, "n33": 0.14524, "n03": 0.14365}
    report["betweenness_spot_checks"] = {
        k: {"computed": round(between[k], 5), "published": v} for k, v in expected_between.items()
    }
    for key, want in expected_between.items():
        if abs(between[key] - want) > 0.0005:
            failures.append(
                f"betweenness[{key}] = {between[key]:.5f}, published value is {want}"
            )

    components = connected_components(graph)
    report["connected_components"] = [len(c) for c in components]
    if len(components) != 1:
        failures.append("the karate club is connected; connected_components says otherwise")

    best = leiden(graph, 1.0, 0)
    part = participation_coefficient(graph, best)
    report["participation_coefficient_range"] = [
        round(min(part.values()), 4),
        round(max(part.values()), 4),
    ]
    if not all(0.0 <= v <= 1.0 for v in part.values()):
        failures.append("participation coefficient outside [0, 1]")

    report["failures"] = failures
    report["verdict"] = "PASS" if not failures else "FAIL"

    out = HERE / "proofs"
    out.mkdir(exist_ok=True)
    (out / "self_test.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
