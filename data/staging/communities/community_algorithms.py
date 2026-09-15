"""Louvain and Leiden over a weighted undirected graph, in pure Python, deterministically.

Why this exists rather than a call to GDS or a library.

GDS 2.13.12 *is* installed in this project's Neo4j and it does have ``gds.louvain.stream``
and ``gds.leiden.stream``. Nothing in this artifact may depend on it, for two reasons the
campaign has already paid for: a partition computed inside a database that the specialist
is forbidden to write cannot be re-derived by a reader who has only the staged files, and a
server-side algorithm's seed and tie-breaking are not part of the artifact. So GDS is used
as an independent cross-check and never as the source of a published number.

Neither ``networkx``, ``numpy``, ``igraph`` nor ``leidenalg`` is installed in this venv, and
adding a dependency to run one report is not a trade this project makes. Everything here is
stdlib.

The two algorithms are genuinely different, and the difference is the point of running both:

* **Louvain** (Blondel et al. 2008) moves nodes greedily to the neighbouring community with
  the best modularity gain, then contracts each community to a single node and repeats. It
  is fast and it has a known defect -- a community it produces can be internally
  *disconnected*, because a node that joined early can be stranded when its bridge later
  moves away. A disconnected "community" is not a community.
* **Leiden** (Traag, Waltman and van Eck 2019) adds a refinement pass between the
  local-moving and the aggregation: inside each community it restarts from singletons and
  merges only into subsets that are sufficiently well connected to the rest of the
  community. Aggregation is then done over the *refined* partition while the coarse
  partition is kept as the starting point. That is what guarantees every community is
  internally connected, and it is what makes Leiden's partitions less seed-dependent.

:func:`communities_are_connected` checks that guarantee on every partition this module
produces. If a Leiden run ever returns a disconnected community, the implementation is
wrong and the check says so rather than the numbers quietly being believed.

Resolution is the gamma of the standard modularity

    Q = (1 / 2m) * sum_ij [ A_ij - gamma * k_i * k_j / (2m) ] * delta(c_i, c_j)

so gamma = 1 is ordinary modularity, higher gamma finds more and smaller communities, and
the resolution sweep in the report is a sweep of exactly this parameter.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

Edge = tuple[str, str, float]


# --------------------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Graph:
    """A weighted undirected simple graph with a fixed node order.

    The node order is fixed and sorted because every seeded shuffle in this module permutes
    *that* order. Two runs with the same seed over the same projection must produce the
    same partition, and they cannot if the node order arrives from a dict whose insertion
    order depends on a Cypher result.

    ``self_loops`` exists because the aggregated graphs built during both algorithms carry
    the internal weight of a contracted community as a self-loop, and modularity counts a
    self-loop's weight twice in the degree. Getting that factor wrong silently shifts every
    modularity value, which is why it is stated here rather than inlined.
    """

    nodes: tuple[str, ...]
    adjacency: dict[str, dict[str, float]]
    self_loops: dict[str, float]

    @classmethod
    def from_edges(cls, nodes: Iterable[str], edges: Iterable[Edge]) -> Graph:
        ordered = tuple(sorted(set(nodes)))
        index = set(ordered)
        adjacency: dict[str, dict[str, float]] = {n: {} for n in ordered}
        self_loops: dict[str, float] = {n: 0.0 for n in ordered}
        for a, b, w in edges:
            if a not in index or b not in index:
                raise KeyError(f"edge ({a}, {b}) has an endpoint outside the node set")
            if w <= 0:
                raise ValueError(f"edge ({a}, {b}) has non-positive weight {w}")
            if a == b:
                self_loops[a] += w
                continue
            adjacency[a][b] = adjacency[a].get(b, 0.0) + w
            adjacency[b][a] = adjacency[b].get(a, 0.0) + w
        return cls(nodes=ordered, adjacency=adjacency, self_loops=self_loops)

    def degree(self, node: str) -> float:
        """Weighted degree, counting a self-loop twice as modularity requires."""
        return sum(self.adjacency[node].values()) + 2.0 * self.self_loops[node]

    @property
    def total_weight(self) -> float:
        """m, the sum of edge weights; a self-loop contributes its weight once."""
        return 0.5 * sum(self.degree(n) for n in self.nodes)

    def isolates(self) -> list[str]:
        return [n for n in self.nodes if not self.adjacency[n] and self.self_loops[n] == 0.0]

    def subgraph(self, keep: Iterable[str]) -> Graph:
        keepset = set(keep)
        edges = [
            (a, b, w)
            for a in sorted(keepset)
            for b, w in sorted(self.adjacency[a].items())
            if b in keepset and a < b
        ]
        edges += [(n, n, self.self_loops[n]) for n in sorted(keepset) if self.self_loops[n] > 0]
        return Graph.from_edges(keepset, edges)


# --------------------------------------------------------------------------------------
# Modularity
# --------------------------------------------------------------------------------------


def modularity(graph: Graph, partition: dict[str, int], resolution: float = 1.0) -> float:
    m = graph.total_weight
    if m == 0:
        return 0.0
    internal: dict[int, float] = defaultdict(float)
    total: dict[int, float] = defaultdict(float)
    for node in graph.nodes:
        community = partition[node]
        total[community] += graph.degree(node)
        internal[community] += 2.0 * graph.self_loops[node]
        for neighbour, weight in graph.adjacency[node].items():
            if partition[neighbour] == community:
                internal[community] += weight
    return sum(internal[c] / (2.0 * m) - resolution * (total[c] / (2.0 * m)) ** 2 for c in total)


def communities_are_connected(graph: Graph, partition: dict[str, int]) -> list[int]:
    """Return the ids of communities that are internally disconnected.

    Leiden guarantees this list is empty. Louvain does not. Reporting it is how the two
    algorithms' difference is made visible as data rather than asserted from the literature.
    """
    members: dict[int, list[str]] = defaultdict(list)
    for node, community in partition.items():
        members[community].append(node)
    broken: list[int] = []
    for community, nodes in sorted(members.items()):
        if len(nodes) < 2:
            continue
        inside = set(nodes)
        start = sorted(nodes)[0]
        seen = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbour in graph.adjacency[current]:
                if neighbour in inside and neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        if len(seen) != len(inside):
            broken.append(community)
    return broken


def renumber(partition: dict[str, int], order: Sequence[str]) -> dict[str, int]:
    """Relabel communities 0..k-1 in order of first appearance along a fixed node order.

    Community *ids* carry no meaning, so they must be canonicalised before two partitions
    are compared or a partition is written to an artifact; otherwise an identical partition
    serialises differently on every run and a diff reports a change that did not happen.
    """
    mapping: dict[int, int] = {}
    out: dict[str, int] = {}
    for node in order:
        community = partition[node]
        if community not in mapping:
            mapping[community] = len(mapping)
        out[node] = mapping[community]
    return out


# --------------------------------------------------------------------------------------
# Local moving, shared by both algorithms
# --------------------------------------------------------------------------------------


def _local_move(
    graph: Graph,
    partition: dict[str, int],
    resolution: float,
    rng: random.Random,
    *,
    max_passes: int = 100,
) -> tuple[dict[str, int], bool]:
    """Greedy node moving until no single move improves modularity.

    The gain from moving node i into community C, dropping the constant terms that are the
    same for every candidate C, is

        k_{i,C} - resolution * k_i * sum_tot(C) / (2m)

    where k_{i,C} is i's edge weight into C and sum_tot(C) is C's total degree with i
    already removed. Ties are broken by the lowest community id, which is what makes a
    seeded run reproducible rather than dependent on dict ordering.

    An **empty** community is always among the candidates, and it has to be. Without it a
    node can only ever move to a community one of its neighbours is already in, so it can
    never leave a community by itself -- and then a community that has become internally
    disconnected can never split, because splitting it starts with one node going solo.
    Leaving that candidate out is the second defect this module's own connectivity guard
    caught: a Leiden run on the Vedic projection returned a disconnected community, which
    the algorithm is not allowed to do.
    """
    m = graph.total_weight
    if m == 0:
        return dict(partition), False
    two_m = 2.0 * m

    total: dict[int, float] = defaultdict(float)
    for node in graph.nodes:
        total[partition[node]] += graph.degree(node)

    assignment = dict(partition)
    improved_ever = False
    order = list(graph.nodes)
    vacant = max(partition.values(), default=0) + 1

    for _ in range(max_passes):
        rng.shuffle(order)
        moved = False
        for node in order:
            degree = graph.degree(node)
            current = assignment[node]
            total[current] -= degree

            weights: dict[int, float] = defaultdict(float)
            weights[current] += 0.0
            for neighbour, weight in graph.adjacency[node].items():
                weights[assignment[neighbour]] += weight
            weights[vacant] += 0.0  # total[vacant] is 0.0, so this is "go it alone"

            best_community = current
            best_gain = weights[current] - resolution * degree * total[current] / two_m
            for community in sorted(weights):
                gain = weights[community] - resolution * degree * total[community] / two_m
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_community = community

            total[best_community] += degree
            if best_community != current:
                assignment[node] = best_community
                moved = True
                improved_ever = True
                if best_community == vacant:
                    vacant += 1
        if not moved:
            break

    return assignment, improved_ever


def _aggregate(graph: Graph, partition: dict[str, int]) -> tuple[Graph, dict[int, list[str]]]:
    """Contract each community to one node; internal weight becomes a self-loop."""
    members: dict[int, list[str]] = defaultdict(list)
    for node in graph.nodes:
        members[partition[node]].append(node)

    labels = {c: f"c{c}" for c in members}
    between: dict[tuple[str, str], float] = defaultdict(float)
    loops: dict[str, float] = defaultdict(float)
    # Every edge is walked twice, once from each endpoint, so every contribution is halved.
    # Halving only the internal ones -- which reads naturally, because an internal edge is
    # "obviously" seen from both sides -- inflates the aggregate graph's total weight, and
    # then every modularity computed above the first level is wrong by a factor nobody sees.
    # That defect was in this function and the karate-club self-test in build_proofs.py is
    # what caught it: two levels of aggregation reported m = 111.0 against the graph's 78.0.
    for node in graph.nodes:
        source = labels[partition[node]]
        loops[source] += graph.self_loops[node]
        for neighbour, weight in graph.adjacency[node].items():
            target = labels[partition[neighbour]]
            if source == target:
                loops[source] += weight / 2.0
            elif source < target:
                between[(source, target)] += weight / 2.0
            else:
                between[(target, source)] += weight / 2.0

    edges: list[Edge] = [(a, b, w) for (a, b), w in between.items()]
    edges += [(n, n, w) for n, w in loops.items() if w > 0]
    return Graph.from_edges(labels.values(), edges), {c: sorted(v) for c, v in members.items()}


# --------------------------------------------------------------------------------------
# Louvain
# --------------------------------------------------------------------------------------


def louvain(graph: Graph, resolution: float = 1.0, seed: int = 0) -> dict[str, int]:
    rng = random.Random(seed)
    current = graph
    mapping: dict[str, str] = {n: n for n in graph.nodes}  # original node -> current node
    final: dict[str, int] = {n: i for i, n in enumerate(graph.nodes)}

    for _ in range(50):
        singletons = {n: i for i, n in enumerate(current.nodes)}
        moved, improved = _local_move(current, singletons, resolution, rng)
        if not improved:
            break
        for original, coarse in mapping.items():
            final[original] = moved[coarse]
        aggregated, _ = _aggregate(current, moved)
        labels = {c: f"c{c}" for c in set(moved.values())}
        mapping = {original: labels[moved[mapping[original]]] for original in mapping}
        current = aggregated
        if len(current.nodes) == 1:
            break

    return renumber(final, graph.nodes)


# --------------------------------------------------------------------------------------
# Leiden
# --------------------------------------------------------------------------------------


def _refine(
    graph: Graph,
    partition: dict[str, int],
    resolution: float,
    rng: random.Random,
) -> dict[str, int]:
    """The Leiden refinement pass: inside each community, merge singletons conservatively.

    A node is only merged into a subset of its own community when the subset is *well
    connected* to the rest of that community -- the condition that rules out the stranded
    bridge that lets Louvain emit a disconnected community. Nodes are visited in a seeded
    random order and a node already merged into a non-singleton subset is not revisited,
    which is what keeps the refined partition a strict subpartition of the input.
    """
    m = graph.total_weight
    if m == 0:
        return dict(partition)
    two_m = 2.0 * m

    members: dict[int, list[str]] = defaultdict(list)
    for node in graph.nodes:
        members[partition[node]].append(node)

    refined: dict[str, int] = {}
    next_id = 0

    for community in sorted(members):
        inside = sorted(members[community])
        inside_set = set(inside)
        community_degree = sum(graph.degree(n) for n in inside)

        local: dict[str, int] = {}
        subset_total: dict[int, float] = {}
        subset_members: dict[int, list[str]] = {}
        for node in inside:
            local[node] = next_id
            subset_total[next_id] = graph.degree(node)
            subset_members[next_id] = [node]
            next_id += 1

        order = list(inside)
        rng.shuffle(order)
        for node in order:
            own = local[node]
            # Only a node still alone in its subset is a candidate to move. This is what
            # keeps the result a subpartition rather than a second local-moving pass.
            if len(subset_members[own]) != 1:
                continue
            degree = graph.degree(node)

            weights: dict[int, float] = defaultdict(float)
            for neighbour, weight in graph.adjacency[node].items():
                if neighbour in inside_set:
                    weights[local[neighbour]] += weight

            best_target = own
            best_gain = 0.0
            for target in sorted(weights):
                if target == own:
                    continue
                # "Well connected to the rest of the community": the target subset must
                # have at least as much weight leaving it, within the community, as chance
                # would give it. This is the condition Louvain lacks.
                rest = community_degree - subset_total[target]
                connection = 0.0
                for member in subset_members[target]:
                    for neighbour, weight in graph.adjacency[member].items():
                        if neighbour in inside_set and local[neighbour] != target:
                            connection += weight
                if connection < resolution * subset_total[target] * rest / two_m:
                    continue
                gain = weights[target] - resolution * degree * subset_total[target] / two_m
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_target = target

            if best_target != own:
                subset_members[own].remove(node)
                subset_total[own] -= degree
                if not subset_members[own]:
                    del subset_members[own]
                    del subset_total[own]
                local[node] = best_target
                subset_members[best_target].append(node)
                subset_total[best_target] += degree

        refined.update(local)

    return refined


def _leiden_pass(
    graph: Graph, start: dict[str, int], resolution: float, rng: random.Random
) -> dict[str, int]:
    """One multi-level Leiden pass from a given starting partition."""
    current = graph
    mapping: dict[str, str] = {n: n for n in graph.nodes}
    coarse: dict[str, int] = dict(start)
    final = dict(start)

    for _ in range(50):
        moved, improved = _local_move(current, coarse, resolution, rng)
        for original in mapping:
            final[original] = moved[mapping[original]]

        refined = _refine(current, moved, resolution, rng)
        # Stop when neither pass changed anything: local moving found no improving move and
        # refinement left every node a singleton, so aggregation would reproduce the graph.
        if not improved and len(set(refined.values())) == len(current.nodes):
            break

        aggregated, groups = _aggregate(current, refined)
        labels = {c: f"c{c}" for c in set(refined.values())}
        # The aggregate starts from the *coarse* partition, not from singletons. This is the
        # step that makes Leiden Leiden: refinement supplies the aggregate's nodes, while
        # local moving's result supplies their starting communities.
        coarse = {labels[c]: moved[groups[c][0]] for c in groups}
        mapping = {original: labels[refined[mapping[original]]] for original in mapping}
        current = aggregated
        if len(current.nodes) == 1:
            break

    return renumber(final, graph.nodes)


def leiden(
    graph: Graph, resolution: float = 1.0, seed: int = 0, iterations: int = 12
) -> dict[str, int]:
    """Leiden, iterated to convergence rather than run once.

    The connectivity guarantee is a property of the *converged* partition, not of a single
    pass: after one pass the local-moving phase can still leave a community disconnected,
    and it is the next pass -- which starts from that partition rather than from singletons
    -- that splits it. Running one pass and asserting the guarantee is how this function
    first failed on the Vedic projection. So the pass is repeated from its own output until
    the partition stops changing, which is also what `n_iterations = -1` means in the
    reference implementation.
    """
    rng = random.Random(seed)
    partition = {n: i for i, n in enumerate(graph.nodes)}
    for _ in range(iterations):
        nxt = _leiden_pass(graph, partition, resolution, rng)
        if nxt == partition:
            break
        partition = nxt

    # Guard the algorithm's own guarantee. A disconnected community here is a bug in this
    # file, not a property of the data, and it must not be reported as a finding.
    broken = communities_are_connected(graph, partition)
    if broken:
        raise AssertionError(
            f"leiden produced {len(broken)} internally disconnected community(ies): {broken}. "
            "That contradicts the algorithm's guarantee, so this implementation is wrong."
        )
    return partition


# --------------------------------------------------------------------------------------
# Comparing partitions
# --------------------------------------------------------------------------------------


def contingency(a: dict[str, int], b: dict[str, int]) -> dict[tuple[int, int], int]:
    table: dict[tuple[int, int], int] = defaultdict(int)
    for node in a:
        table[(a[node], b[node])] += 1
    return dict(table)


def adjusted_rand_index(a: dict[str, int], b: dict[str, int]) -> float:
    """ARI. 1.0 is identical, 0.0 is chance, negative is worse than chance.

    The right statistic for seed stability because it corrects for the number of
    communities: two random partitions into five groups agree on a lot of pairs by
    accident, and the uncorrected Rand index would call that stability.
    """
    n = len(a)
    if n < 2:
        return 1.0
    table = contingency(a, b)
    rows: dict[int, int] = defaultdict(int)
    cols: dict[int, int] = defaultdict(int)
    for (i, j), count in table.items():
        rows[i] += count
        cols[j] += count

    def c2(x: int) -> float:
        return x * (x - 1) / 2.0

    index = sum(c2(v) for v in table.values())
    expected = sum(c2(v) for v in rows.values()) * sum(c2(v) for v in cols.values()) / c2(n)
    maximum = 0.5 * (sum(c2(v) for v in rows.values()) + sum(c2(v) for v in cols.values()))
    if maximum == expected:
        return 1.0
    return (index - expected) / (maximum - expected)


def normalised_mutual_information(a: dict[str, int], b: dict[str, int]) -> float:
    n = len(a)
    if n == 0:
        return 1.0
    table = contingency(a, b)
    rows: dict[int, int] = defaultdict(int)
    cols: dict[int, int] = defaultdict(int)
    for (i, j), count in table.items():
        rows[i] += count
        cols[j] += count

    mutual = 0.0
    for (i, j), count in table.items():
        mutual += (count / n) * math.log((count * n) / (rows[i] * cols[j]))
    entropy_a = -sum((v / n) * math.log(v / n) for v in rows.values())
    entropy_b = -sum((v / n) * math.log(v / n) for v in cols.values())
    if entropy_a == 0.0 and entropy_b == 0.0:
        return 1.0
    if entropy_a == 0.0 or entropy_b == 0.0:
        return 0.0
    return mutual / math.sqrt(entropy_a * entropy_b)


def co_assignment(
    partitions: Sequence[dict[str, int]], nodes: Sequence[str]
) -> dict[tuple[str, str], float]:
    """For every node pair, the fraction of runs placing them in the same community.

    Label-free, so it is the only stability measure that does not need partitions matched
    up first, and it is what the consensus partition is built from.
    """
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for partition in partitions:
        for i, first in enumerate(nodes):
            for second in nodes[i + 1 :]:
                if partition[first] == partition[second]:
                    counts[(first, second)] += 1
    runs = len(partitions)
    return {pair: count / runs for pair, count in counts.items()}


def consensus_partition(
    partitions: Sequence[dict[str, int]], nodes: Sequence[str], threshold: float = 0.5
) -> dict[str, int]:
    """Connected components of the graph of pairs co-assigned in more than `threshold` runs.

    Deliberately the simplest consensus rule that exists, because a clever one would be a
    third algorithm whose own stability nobody has measured.
    """
    shared = co_assignment(partitions, nodes)
    adjacency: dict[str, set[str]] = {n: set() for n in nodes}
    for (a, b), value in shared.items():
        if value > threshold:
            adjacency[a].add(b)
            adjacency[b].add(a)
    seen: set[str] = set()
    out: dict[str, int] = {}
    label = 0
    for node in nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in sorted(adjacency[current]):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        for member in component:
            out[member] = label
        label += 1
    return renumber(out, nodes)


# --------------------------------------------------------------------------------------
# Network analytics over the same projection
# --------------------------------------------------------------------------------------


def connected_components(graph: Graph) -> list[list[str]]:
    seen: set[str] = set()
    out: list[list[str]] = []
    for node in graph.nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in sorted(graph.adjacency[current]):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        out.append(sorted(component))
    return sorted(out, key=lambda c: (-len(c), c[0]))


def betweenness_centrality(graph: Graph) -> dict[str, float]:
    """Brandes (2001), unweighted shortest paths, normalised for an undirected graph.

    Deliberately unweighted, and the reason has to travel with the number. On a weighted
    co-occurrence graph a "shortest path" would mean the path of least association, which is
    the opposite of what a reader assumes a strong edge does. Unweighted betweenness answers
    a question that is at least well posed: how often does this deity lie on a shortest
    chain of co-dedication between two others.

    The registry's own note on this gap warns that the obvious projection -- passages and
    entities, directed and bipartite -- gives betweenness 0.0 for every node and therefore
    "a full sortable ranking of zeros". This projection is deity-to-deity and undirected, so
    the measure is not degenerate here; that is a property of having declared a projection
    rather than picking one at query time.
    """
    betweenness = {n: 0.0 for n in graph.nodes}
    for source in graph.nodes:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {n: [] for n in graph.nodes}
        sigma = {n: 0.0 for n in graph.nodes}
        distance = {n: -1 for n in graph.nodes}
        sigma[source] = 1.0
        distance[source] = 0
        queue = [source]
        head = 0
        while head < len(queue):
            current = queue[head]
            head += 1
            stack.append(current)
            for neighbour in sorted(graph.adjacency[current]):
                if distance[neighbour] < 0:
                    queue.append(neighbour)
                    distance[neighbour] = distance[current] + 1
                if distance[neighbour] == distance[current] + 1:
                    sigma[neighbour] += sigma[current]
                    predecessors[neighbour].append(current)
        delta = {n: 0.0 for n in graph.nodes}
        while stack:
            current = stack.pop()
            for predecessor in predecessors[current]:
                delta[predecessor] += (sigma[predecessor] / sigma[current]) * (1.0 + delta[current])
            if current != source:
                betweenness[current] += delta[current]
    # Undirected, so every pair is accumulated from both endpoints: halve, then normalise
    # by the number of ordered pairs a node could lie between.
    size = len(graph.nodes)
    scale = 2.0 / ((size - 1) * (size - 2)) if size > 2 else 1.0
    return {n: (v / 2.0) * scale for n, v in betweenness.items()}


def participation_coefficient(graph: Graph, partition: dict[str, int]) -> dict[str, float]:
    """Guimera and Amaral's P: 1 - sum over communities of (k_iC / k_i)^2.

    0 means every edge a node has goes to its own community; near 1 means its edges are
    spread evenly across communities. This, not betweenness, is the honest "bridge" measure
    once a partition exists, because it is defined relative to that partition and therefore
    carries the partition's caveats with it instead of looking like a property of the deity.
    """
    out: dict[str, float] = {}
    for node in graph.nodes:
        total = sum(graph.adjacency[node].values())
        if total == 0:
            out[node] = 0.0
            continue
        by_community: dict[int, float] = defaultdict(float)
        for neighbour, weight in graph.adjacency[node].items():
            by_community[partition[neighbour]] += weight
        out[node] = 1.0 - sum((v / total) ** 2 for v in by_community.values())
    return out


def within_module_degree_z(graph: Graph, partition: dict[str, int]) -> dict[str, float]:
    """The other half of the Guimera-Amaral pair: how well connected a node is inside its own
    community, in standard deviations of that community's internal-degree distribution."""
    internal: dict[str, float] = {}
    for node in graph.nodes:
        internal[node] = sum(
            weight
            for neighbour, weight in graph.adjacency[node].items()
            if partition[neighbour] == partition[node]
        )
    members: dict[int, list[str]] = defaultdict(list)
    for node, community in partition.items():
        members[community].append(node)
    out: dict[str, float] = {}
    for nodes in members.values():
        values = [internal[n] for n in nodes]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        deviation = math.sqrt(variance)
        for node in nodes:
            out[node] = 0.0 if deviation == 0 else (internal[node] - mean) / deviation
    return out


def match_to_reference(partition: dict[str, int], reference: dict[str, int]) -> dict[str, int]:
    """Relabel `partition` so its community ids line up with `reference` by max overlap.

    Needed to answer "how often does a node change community" literally: community ids are
    arbitrary per run, so without this every node would look like it changed every time.
    """
    table = contingency(partition, reference)
    pairs = sorted(table.items(), key=lambda kv: (-kv[1], kv[0]))
    used_source: set[int] = set()
    used_target: set[int] = set()
    mapping: dict[int, int] = {}
    for (source, target), _count in pairs:
        if source in used_source or target in used_target:
            continue
        mapping[source] = target
        used_source.add(source)
        used_target.add(target)
    spare = max(reference.values(), default=0) + 1
    for source in sorted(set(partition.values())):
        if source not in mapping:
            mapping[source] = spare
            spare += 1
    return {node: mapping[community] for node, community in partition.items()}
