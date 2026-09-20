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
    /**
     * The hash of the public export all four artifact files were built from.
     *
     * Present in `world.json`, `world.labels.json` and `world.predicates.json`, and the reason
     * a browser can be told it is holding a mismatched set rather than quietly drawing one.
     */
    inputPublicExportHash?: string;
    /** `world.bin`'s length in bytes, as written. */
    worldBinBytes?: number;
    /** `world.bin`'s SHA-256, as written. Not verified at runtime; see `readWorld`. */
    worldBinSha256?: string;
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
    /** The export hash this label set was built from. Checked against the manifest's. */
    inputPublicExportHash?: string;
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

/**
 * The artifact, fetched and decoded exactly once per page.
 *
 * Memoised for a structural reason rather than to save a fetch. The planar canvas could not
 * exist until the *spatial* engine had finished starting, because the page took its `world` and
 * `labels` from the 3D view's ready callback - so a cold `?renderer=2d` link waited on a
 * renderer it was never going to use, and on the 1.9 MB label file besides. That is the worst
 * available first impression for the fallback renderer, which is the one a weak device is sent
 * to. With the load memoised the page can ask for the artifact itself and hand it to whichever
 * canvas is drawing, and the two callers share one fetch and one decode.
 *
 * The decode is the part worth not repeating: `buildAdjacency` walks 185,693 edges twice to
 * build the CSR index, and doing that a second time on the same bytes would be pure waste.
 *
 * ## Why the signal is not passed to the shared fetch
 *
 * A cached promise has many consumers and one of them aborting must not fail the others. So the
 * fetch runs unaborted and each caller checks its own signal *after* awaiting, which is what
 * `world-view.tsx` already does. A rejected load clears the cache so that a later mount retries
 * rather than inheriting the failure for the life of the page.
 */
let worldCache: Promise<World> | null = null;
let labelCache: Promise<WorldLabels> | null = null;

export function loadWorld(signal?: AbortSignal): Promise<World> {
    if (!worldCache) {
        worldCache = readWorld().catch((reason) => {
            worldCache = null;
            throw reason;
        });
    }
    /* Awaited here rather than returned raw so a caller that has since been aborted gets the
       rejection it expects instead of a world it will not use. */
    return worldCache.then((world) => {
        signal?.throwIfAborted();
        return world;
    });
}

/**
 * The manifest, always fresh, and the address every other artifact file is fetched from.
 *
 * The four files under `/world` have stable names and are served
 * `Cache-Control: public, max-age=31536000, immutable`, which is correct about their contents
 * and wrong about their names: a rebuilt artifact is a new set of bytes at the same URL, so a
 * browser holding last week's `world.bin` has no reason to ever ask again. Worse, the entries
 * are evicted independently and `world.bin` is 4 MB against the manifest's 28 KB, so the pair
 * a reader ends up with is not guaranteed to be a pair at all. A mismatched pair does not
 * error: the section offsets still resolve, and `nodeGroup[i]` returns the group of whichever
 * node happened to sit at that index in the other build. Every label in the graph is then
 * confidently the wrong kind of thing.
 *
 * So the manifest is fetched with `cache: "no-cache"` - revalidated every time, 28 KB - and
 * its `inputPublicExportHash` is appended to the addresses of the files that are large enough
 * to be worth caching hard. A rebuilt artifact changes the hash, which changes those URLs,
 * which is a cache miss by construction rather than by header.
 */
async function readManifest(): Promise<WorldManifest> {
    const response = await fetch("/world/world.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("The world could not be read.");
    return (await response.json()) as WorldManifest;
}

let manifestCache: Promise<WorldManifest> | null = null;

function sharedManifest(): Promise<WorldManifest> {
    if (!manifestCache) {
        manifestCache = readManifest().catch((reason) => {
            manifestCache = null;
            throw reason;
        });
    }
    return manifestCache;
}

/** An artifact file's address, versioned by the export every file was built from. */
export function artifactUrl(file: string, manifest: Pick<WorldManifest, "inputPublicExportHash">) {
    const version = manifest.inputPublicExportHash;
    return version ? `/world/${file}?v=${version}` : `/world/${file}`;
}

async function readWorld(): Promise<World> {
    const manifest = await sharedManifest();
    const binaryResponse = await fetch(artifactUrl("world.bin", manifest));
    if (!binaryResponse.ok) {
        throw new Error("The world could not be read.");
    }
    const buffer = await binaryResponse.arrayBuffer();

    /*
     * The cheap half of the integrity check, and it is the half that catches the real failure.
     * A stale `world.bin` is a different length from the one this manifest describes, and
     * saying so is better than drawing 71,773 subjects out of 35,648 nodes' worth of bytes.
     * The manifest also carries `worldBinSha256`; hashing 4 MB in the browser would catch
     * corruption as well as staleness, and is deliberately not done on the critical path -
     * `tests/unit/public-identity.test.ts` verifies the digest where the cost is free.
     */
    if (manifest.worldBinBytes !== undefined && buffer.byteLength !== manifest.worldBinBytes) {
        throw new Error(
            `The world is out of step with itself: world.bin is ${buffer.byteLength} bytes, ` +
                `and this build describes ${manifest.worldBinBytes}. Reload to fetch it again.`,
        );
    }

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
export function loadWorldLabels(signal?: AbortSignal): Promise<WorldLabels> {
    if (!labelCache) {
        labelCache = readWorldLabels().catch((reason) => {
            labelCache = null;
            throw reason;
        });
    }
    return labelCache.then((labels) => {
        signal?.throwIfAborted();
        return labels;
    });
}

async function readWorldLabels(): Promise<WorldLabels> {
    const manifest = await sharedManifest();
    const response = await fetch(artifactUrl("world.labels.json", manifest));
    if (!response.ok) throw new Error("The world labels could not be read.");
    const raw = (await response.json()) as WorldLabels;

    /*
     * Labels and geometry have to be the same build, and until this check they simply were not
     * required to be. Both files carry the hash of the public export they were written from,
     * and both are already asserted equal at build time - but a build-time assertion says
     * nothing about which two files a given browser is holding.
     *
     * The count is checked too, because an artifact predating the hash field would otherwise
     * pass unverified, and a label array of a different length than the node array is the same
     * defect announcing itself in a way that does not need the hash.
     */
    const expected = manifest.inputPublicExportHash;
    if (expected && raw.inputPublicExportHash && raw.inputPublicExportHash !== expected) {
        throw new Error(
            "The world labels are from a different build than the world. Reload to fetch them again.",
        );
    }
    if (raw.ids.length !== manifest.counts.nodes) {
        throw new Error(
            `The world labels are out of step with the world: ${raw.ids.length} names for ` +
                `${manifest.counts.nodes} subjects. Reload to fetch them again.`,
        );
    }

    return {
        inputPublicExportHash: raw.inputPublicExportHash,
        ids: raw.ids,
        labels: readableLabels(raw.labels, raw.ids),
    };
}

/** A pipeline vocabulary constant, written the way it is stored: BINDS, IS_OR_BECOMES. */
const SHOUTED = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$/;
/** A metric label carrying the graph id of what it measures, in either stored shape. */
const METRIC_WITH_ID = /^([A-Z][A-Z0-9_]*)\s*(?:\(([^)]*)\)|\/\s*(\S+))$/;

function humanise(constant: string): string {
    const words = constant.toLowerCase().replaceAll("_", " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * Two label families in this artifact are pipeline vocabulary rather than words.
 *
 * Measured over the shipped 71,773 labels: exactly 40 are a shouted constant and all 40 are
 * `:ActionPredicate` nodes - `BINDS`, `IS_OR_BECOMES`, `MOVES_TO`. Exactly 746 carry a raw
 * graph id and all 746 are `:DerivedMetric` - `DEVATA_ATTRIBUTION_BY_VEDA (VG:DEVATA:INDRAH)`,
 * `ANIMAL_MENTION_DISTRIBUTION / VG:WORK:AV:SAU`. Nothing else in the file matches either
 * shape, so this rewrite is total over those two families and touches no other label.
 *
 * They matter because they are not rare on screen. Eight of the twelve idea seats in Indra's
 * focus scene are action predicates, so a reader who clicked a deity met `IS_OR_BECOMES` and
 * `ESTABLISHES` shouting beside `the Maruts`; and a bare `VG:DEVATA:INDRAH` in a drawn row is
 * an internal identifier on a normal product page.
 *
 * Done here, once, at the single point the labels are read, rather than at the six places they
 * are rendered - the canvas, the search hits, the hub list, the path endpoints, the edge
 * labels and the focus rows - because five of the six would have been fixed and one forgotten.
 *
 * ## Why the id is not simply dropped
 *
 * A metric's name is not unique: `ANIMAL_MENTION_DISTRIBUTION` is recorded once per work, so
 * dropping the id would give four rows one name. The focus rounds deduplicate by label, so
 * three of those four would silently stop being drawable. Colliding names therefore keep a
 * scope, and only genuinely unique ones lose it.
 *
 * The scope is the *label* of the thing the id names, not the id: every one of those ids is
 * itself a node in this artifact, so `DEVATA_ATTRIBUTION_BY_VEDA (VG:DEVATA:INDRAH)` resolves
 * to "Devata attribution by veda - Indra" rather than trading one identifier for a tidier one.
 * An id that does not resolve keeps its segments, because a scope a reader cannot read still
 * beats two rows that claim to be the same measurement.
 */
export function readableLabels(labels: readonly string[], ids: readonly string[]): string[] {
    const out = labels.slice();
    const metricAt: number[] = [];
    const nameCount = new Map<string, number>();

    for (let i = 0; i < out.length; i += 1) {
        const label = out[i];
        if (!label) continue;
        if (SHOUTED.test(label)) {
            out[i] = humanise(label);
            continue;
        }
        const metric = METRIC_WITH_ID.exec(label);
        if (!metric) continue;
        metricAt.push(i);
        const name = humanise(metric[1]);
        nameCount.set(name, (nameCount.get(name) ?? 0) + 1);
    }

    const indexOfId = new Map<string, number>();
    for (let i = 0; i < ids.length; i += 1) indexOfId.set(ids[i], i);

    for (const i of metricAt) {
        const metric = METRIC_WITH_ID.exec(out[i]);
        if (!metric) continue;
        const name = humanise(metric[1]);
        if ((nameCount.get(name) ?? 0) <= 1) {
            out[i] = name;
            continue;
        }
        const id = (metric[2] ?? metric[3] ?? "").trim();
        const named = indexOfId.get(id);
        const scope =
            named === undefined || !labels[named]
                ? id.split(":").filter(Boolean).slice(1).join(" ")
                : labels[named];
        out[i] = scope ? `${name} - ${scope}` : name;
    }
    return out;
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
