/**
 * The world artifact: what it contains, and how it is read.
 *
 * The file this loads is built by `scripts/export_graph_world.py` and
 * `scripts/build-world.mjs`. It holds the whole public graph - 35,370 nodes and 185,693
 * relationships - as typed arrays with a settled 3D position for every node.
 *
 * ## Why the world is a file rather than a query
 *
 * The served graph API answers "what is attached to this one thing", capped at depth 2 and
 * 400 nodes, and measurement showed it returns only edges incident to the root: a depth-1
 * response for Indra carries 262 edges, none of which joins two of its neighbours. A force
 * layout over that draws a star. It is the right answer for a reader's apparatus and the
 * wrong one for a world, and asking it 35,370 times is not an alternative - at the measured
 * 1.1 KB per node that is about 120 MB of JSON.
 *
 * Packed, the same graph is 715 KB of geometry and 294 KB of labels over the wire. The graph
 * is frozen, so there is no freshness cost to paying for it at build time instead.
 */

export type WorldSection = {
    name: string;
    offset: number;
    length: number;
    type: string;
};

export type WorldManifest = {
    version: number;
    generated: string;
    source: { nodes: number; edges: number };
    counts: { nodes: number; edges: number };
    /** Half-width of the cube the layout was normalised into. */
    extent: number;
    ticks: number;
    /**
     * Edges below this index carry meaning; above it they are containment and metre.
     *
     * The array is sorted at build time so the split can be a draw range rather than a filter.
     * Optional because an artifact built before this field existed is still readable; the
     * renderer falls back to drawing everything.
     */
    semanticEdges?: number;
    /** Semantic group names, indexed by `nodeGroup`. Colour comes from `--va-group-*`. */
    groups: string[];
    types: string[];
    edgeTypes: string[];
    sections: WorldSection[];
    /**
     * Nodes worth naming before anything is selected, most connected first.
     *
     * Held out of this index: passages, and the reified record types. The busiest nodes in
     * this graph by raw degree are metres - triṣṭup is attached to 4,195 verses - and a world
     * whose visible labels are four metre names has described the prosody of the corpus
     * rather than its subject.
     */
    hubs: number[];
    maxDegree: number;
    /** How the communities were found, and how many survived into regions. */
    communities?: {
        algorithm: string;
        resolution: number;
        modularity: number;
        detected: number;
        drawn: number;
        minSize: number;
        unattached: number;
    };
    /**
     * The drawn regions, in `nodeRegion` order.
     *
     * A name is present only where the metrics carried it: a Veda holding at least sixty per
     * cent of the members, or a leading member at least twice as connected as the next. Where
     * neither holds the constellation keeps its number, which is the honest description of a
     * group that is genuinely mixed rather than a failure to describe it.
     */
    constellations?: Constellation[];
};

export type Constellation = {
    id: number;
    community: number;
    name: string | null;
    size: number;
    veda: { name: string; count: number; share: number } | null;
    group: { name: string; count: number; share: number } | null;
    central: number[];
    bridges: number[];
    connectedShare: number | null;
    centre: [number, number, number];
    radius: number;
};

export type World = {
    manifest: WorldManifest;
    /** xyz per node, laid out offline. */
    positions: Float32Array;
    nodeType: Uint8Array;
    nodeGroup: Uint8Array;
    nodeDegree: Uint16Array;
    /** Which drawn region a node belongs to; 65535 means none. */
    nodeRegion: Uint16Array;
    /** Two node indices per edge. */
    edgePairs: Uint32Array;
    edgeType: Uint8Array;
    /** 1 where an edge joins two different regions. Bridges are how the corpus hangs together. */
    edgeBridge: Uint8Array;
    /**
     * Edge indices grouped by node, and where each node's run starts.
     *
     * Built once on load so that "which edges touch node i" is a slice rather than a scan of
     * 185,693 edges. Selection, neighbourhood expansion and focus all ask that question, and
     * asking it linearly is the difference between a hover that lands in a frame and one that
     * does not.
     */
    adjacencyStart: Uint32Array;
    adjacency: Uint32Array;
};

export type WorldLabels = {
    ids: string[];
    labels: string[];
};

const CONSTRUCTORS: Record<string, Float32ArrayConstructor | Uint8ArrayConstructor | Uint16ArrayConstructor | Uint32ArrayConstructor> = {
    Float32Array,
    Uint8Array,
    Uint16Array,
    Uint32Array,
};

function view(buffer: ArrayBuffer, section: WorldSection) {
    const Ctor = CONSTRUCTORS[section.type];
    if (!Ctor) throw new Error(`world artifact: unknown section type ${section.type}`);
    return new Ctor(buffer, section.offset, section.length);
}

/**
 * CSR adjacency, built in two passes.
 *
 * First pass counts the degree of every node to find where each run begins; the second fills
 * the runs. This is the standard compressed-sparse-row construction and it is used here in
 * preference to an array of arrays because 35,370 sub-arrays is 35,370 allocations, and the
 * whole point of the packed artifact is to arrive as a small number of large buffers.
 */
function buildAdjacency(nodeCount: number, edgePairs: Uint32Array) {
    const edgeCount = edgePairs.length / 2;
    const counts = new Uint32Array(nodeCount + 1);
    for (let i = 0; i < edgeCount; i += 1) {
        counts[edgePairs[i * 2]] += 1;
        counts[edgePairs[i * 2 + 1]] += 1;
    }
    const start = new Uint32Array(nodeCount + 1);
    let running = 0;
    for (let i = 0; i < nodeCount; i += 1) {
        start[i] = running;
        running += counts[i];
    }
    start[nodeCount] = running;

    const cursor = start.slice();
    const adjacency = new Uint32Array(running);
    for (let i = 0; i < edgeCount; i += 1) {
        const a = edgePairs[i * 2];
        const b = edgePairs[i * 2 + 1];
        adjacency[cursor[a]] = i;
        cursor[a] += 1;
        adjacency[cursor[b]] = i;
        cursor[b] += 1;
    }
    return { adjacencyStart: start, adjacency };
}

/**
 * Assemble a world in memory, from arrays rather than from the packed file.
 *
 * The homepage preview is the reason. It shows fifty real nodes cut from this same artifact,
 * and the way to guarantee it looks like the graph is to make it *be* the graph: build a small
 * `World` and hand it to the same `WorldEngine`. One renderer, one set of shaders, one sizing
 * rule, one palette. A second preview renderer would have started identical and diverged on the
 * first change to either - which is precisely how the teaser this replaces ended up with its own
 * shapes and its own colours.
 *
 * Everything that carries a claim is required rather than defaulted. `edgeType` in particular:
 * filling it with zeros would have every edge assert it is `edgeTypes[0]`, and an edge that
 * confidently names the wrong relationship is worse than one that names none. Where a caller
 * genuinely has no node types it passes an empty `types` array, so `nodeType[i]` indexes nothing
 * and reads as absent instead of as the first entry.
 *
 * A node with no region is 65535, the same sentinel the packed file uses, so downstream code
 * cannot tell the two kinds of world apart.
 */
export function composeWorld(input: {
    groups: string[];
    types: string[];
    edgeTypes: string[];
    positions: Float32Array;
    nodeGroup: Uint8Array;
    nodeDegree: Uint16Array;
    edgePairs: Uint32Array;
    edgeType: Uint8Array;
}): World {
    const nodes = input.nodeGroup.length;
    const edges = input.edgePairs.length / 2;
    const { adjacencyStart, adjacency } = buildAdjacency(nodes, input.edgePairs);
    let maxDegree = 0;
    for (let i = 0; i < nodes; i += 1) maxDegree = Math.max(maxDegree, input.nodeDegree[i]);

    return {
        manifest: {
            version: 2,
            generated: "",
            source: { nodes, edges },
            counts: { nodes, edges },
            extent: 1000,
            ticks: 0,
            // Every edge in a composed world is semantic: the structural backbone is not cut
            // from the artifact, so there is no range above which meaning stops.
            semanticEdges: edges,
            groups: input.groups,
            types: input.types,
            edgeTypes: input.edgeTypes,
            sections: [],
            hubs: [],
            maxDegree,
        },
        positions: input.positions,
        nodeType: new Uint8Array(nodes),
        nodeGroup: input.nodeGroup,
        nodeDegree: input.nodeDegree,
        nodeRegion: new Uint16Array(nodes).fill(65535),
        edgePairs: input.edgePairs,
        edgeType: input.edgeType,
        // No regions, so no edge can bridge two of them.
        edgeBridge: new Uint8Array(edges),
        adjacencyStart,
        adjacency,
    };
}

export async function loadWorld(signal?: AbortSignal): Promise<World> {
    const [manifestResponse, binaryResponse] = await Promise.all([
        fetch("/world/world.json", { signal }),
        fetch("/world/world.bin", { signal }),
    ]);
    if (!manifestResponse.ok || !binaryResponse.ok) {
        throw new Error("The world could not be read.");
    }
    const manifest = (await manifestResponse.json()) as WorldManifest;
    const buffer = await binaryResponse.arrayBuffer();

    const sections = new Map(manifest.sections.map((s) => [s.name, s]));
    const need = (name: string) => {
        const section = sections.get(name);
        if (!section) throw new Error(`world artifact: missing section ${name}`);
        return view(buffer, section);
    };

    const edgePairs = need("edgePairs") as Uint32Array;
    const { adjacencyStart, adjacency } = buildAdjacency(manifest.counts.nodes, edgePairs);

    return {
        manifest,
        positions: need("positions") as Float32Array,
        nodeType: need("nodeType") as Uint8Array,
        nodeGroup: need("nodeGroup") as Uint8Array,
        nodeDegree: need("nodeDegree") as Uint16Array,
        nodeRegion: need("nodeRegion") as Uint16Array,
        edgePairs,
        edgeType: need("edgeType") as Uint8Array,
        edgeBridge: need("edgeBridge") as Uint8Array,
        adjacencyStart,
        adjacency,
    };
}

/** Labels arrive after the geometry, so the world can paint before any text is parsed. */
export async function loadWorldLabels(signal?: AbortSignal): Promise<WorldLabels> {
    const response = await fetch("/world/world.labels.json", { signal });
    if (!response.ok) throw new Error("The world labels could not be read.");
    return (await response.json()) as WorldLabels;
}

/** Edge indices touching a node. A slice of the CSR array, not a scan. */
export function edgesOf(world: World, node: number): Uint32Array {
    return world.adjacency.subarray(world.adjacencyStart[node], world.adjacencyStart[node + 1]);
}

/** The node at the other end of an edge. */
export function otherEnd(world: World, edge: number, from: number) {
    const a = world.edgePairs[edge * 2];
    return a === from ? world.edgePairs[edge * 2 + 1] : a;
}

/**
 * First-degree neighbours of a node, each named once.
 *
 * Deduplicated, and that is not a tidying-up: two subjects can be joined by more than one
 * relationship - Agni is both invoked in a hymn and ascribed to it - and the adjacency index
 * is keyed by edge, so the naive version returns the same neighbour once per relationship.
 * Rendered as a list that is a duplicate React key, and read as a count it overstates how many
 * distinct things a subject is connected to. The degree is still the edge count, which is the
 * honest figure for "recorded connections"; this is the honest figure for "connected subjects",
 * and the two are different numbers on purpose.
 */
export function neighboursOf(world: World, node: number): Uint32Array {
    const edges = edgesOf(world, node);
    const seen = new Set<number>();
    for (let i = 0; i < edges.length; i += 1) seen.add(otherEnd(world, edges[i], node));
    return Uint32Array.from(seen);
}

/**
 * Everything a surface needs to name one subject.
 *
 * Here rather than in a component because two of them needed it and each had its own copy, and
 * the copies did not agree about what a selection *was*. The spatial view built one when its
 * canvas was clicked and handed it up as an event; the page stored that object and rendered the
 * subject panel from it. So the panel was driven by a thing the canvas had said, while the URL
 * was driven by something else, and a click on empty space cleared the first without touching
 * the second: the panel vanished while the address bar still read `view=focus`. A reader could
 * not tell that from Focus resetting itself, and neither could a test.
 *
 * A subject is a *derivation* from an id, so there is nothing to keep in step. The id is in the
 * state, the state is in the URL, and every surface computes the same description from it.
 */
export type Subject = {
    index: number;
    id: string;
    label: string;
    group: string;
    type: string;
    /** The edge count. The honest figure for "recorded connections". */
    degree: number;
    /** Distinct connected subjects, which is a different number from `degree`. */
    neighbours: number[];
};

export function describeSubject(world: World, labels: WorldLabels | null, index: number): Subject {
    return {
        index,
        id: labels?.ids[index] ?? String(index),
        label: labels?.labels[index] ?? "",
        group: world.manifest.groups[world.nodeGroup[index]],
        type: world.manifest.types[world.nodeType[index]],
        degree: world.nodeDegree[index],
        neighbours: Array.from(neighboursOf(world, index)),
    };
}

/** The region a node sits in, or null where it has no public connections. */
export function regionOf(world: World, node: number): number | null {
    const region = world.nodeRegion[node];
    return region === 65535 ? null : region;
}

/** Every node in a constellation. Scanned once and cached by the caller if needed. */
export function membersOfRegion(world: World, region: number): number[] {
    const out: number[] = [];
    for (let i = 0; i < world.nodeRegion.length; i += 1) {
        if (world.nodeRegion[i] === region) out.push(i);
    }
    return out;
}
