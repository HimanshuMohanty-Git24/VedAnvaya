#!/usr/bin/env node
/**
 * Compose the world, and pack it for the browser.
 *
 * ## Why the layout is not computed in the browser
 *
 * A force simulation is O(n log n) per tick with Barnes-Hut and needs hundreds of ticks to
 * settle. At 35,370 nodes that is minutes of arithmetic, and the published practical ceiling
 * for an interactive in-browser force layout is five to ten thousand nodes. Every tool that
 * draws graphs this size - Gephi, Graphistry, Cosmograph - computes the layout somewhere other
 * than the frame loop and ships coordinates. Doing it here also buys something a runtime
 * layout cannot: the world is in the same place on every visit, which matters when a reader is
 * meant to learn where things are.
 *
 * The browser still runs a live simulation, but only over the few hundred nodes a reader is
 * touching, which is well inside what settles smoothly.
 *
 * ## Why the layout is in two levels
 *
 * The first version of this ran one simulation over everything and produced a ball: uniformly
 * dense, no interior structure, sixty frames a second of nothing. A force layout expresses
 * whatever grouping it is given, and it was given none. So the constellation graph is laid out
 * first - a few dozen bodies, not thirty-five thousand - and each constellation is then filled
 * in locally, in its own frame, and translated into place.
 *
 * Usage:
 *   python scripts/export_graph_world.py      # frozen store  -> .world/world.raw.json
 *   node scripts/build-constellations.mjs     # communities   -> .world/constellations.json
 *   node scripts/build-world.mjs              # composition   -> public/world/*
 */

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validatePublicGraph, exportHash } from "./public-identity-contract.mjs";
import { forceCenter, forceLink, forceManyBody, forceSimulation } from "d3-force-3d";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const OUT_DIR = join(ROOT, "public", "world");

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
    args.set(process.argv[i].replace(/^--/, ""), process.argv[i + 1]);
}
const TICKS = Number(args.get("ticks") ?? 320);
const IN = resolve(ROOT, args.get("in") ?? ".world/world.raw.json");
const CONSTELLATIONS = resolve(ROOT, args.get("constellations") ?? ".world/constellations.json");
/** A community has to reach this size before it is drawn as a region of its own. */
const REGION_MIN = Number(args.get("region-min") ?? 24);
/*
 * There is no axis compression, and there was.
 *
 * A previous build multiplied every z by 0.42, on the theory that a sphere seen from outside
 * is a disc from every angle and that a plane with thickness would read better. Measured, the
 * result was a pancake: attached extents of 1.000 : 0.879 : 0.345, and sixteen of thirty-three
 * constellation centres sitting closer to z=0 than their own radius. It did not read as depth,
 * it read as a squashed shell, and orbiting it revealed less rather than more.
 *
 * The multiplier also reached somewhere subtle. Region radii were measured in the compressed
 * metric, so the spacing floor between regions was computed from a distance that was not the
 * one they would be drawn at - removing the compression from positions alone would have left
 * regions under-spaced and overlapping through z. It is gone from all five places at once.
 */

const GROUPS = [
    "deity",
    "unresolved-deity",
    "passage",
    "person",
    "idea",
    "rite",
    "thing",
    "wording",
    "derived",
    "record",
    "other",
];

/*
 * One table, read from disk.
 *
 * This mapping was inline here, and the constellation step needs exactly the same answer. A
 * second copy is how the two semantic colour tables this rebuild had to reconcile came about.
 */
const TYPE_TO_GROUP = new Map(
    Object.entries(JSON.parse(readFileSync(join(HERE, "world-groups.json"), "utf8"))),
);

function groupOf(node) {
    if (node.type === "Devata") return node.deity === true ? "deity" : "unresolved-deity";
    return TYPE_TO_GROUP.get(node.type) ?? "other";
}

/* ------------------------------------------------------------------ read - */

for (const [path, how] of [
    [IN, "python scripts/export_graph_world.py"],
    [CONSTELLATIONS, "node scripts/build-constellations.mjs"],
]) {
    if (!existsSync(path)) {
        console.error(`Missing ${path}.\nRun:  ${how}\nfirst.`);
        process.exit(1);
    }
}

console.log(`reading ${IN} ...`);
const rawBytes = readFileSync(IN);
const raw = JSON.parse(rawBytes.toString("utf8"));
const identityAudit = validatePublicGraph(raw);
const inputPublicExportHash = exportHash(rawBytes);
const nodes = raw.nodes;
const edges = raw.edges;
const detected = JSON.parse(readFileSync(CONSTELLATIONS, "utf8"));

/*
 * The partition is joined BY POSITION, so it has to have been computed over this world.
 *
 * `community[i]` is the constellation of `nodes[i]` and nothing in the file says which world
 * it was measured on. Wave 4 found the consequence: `world.raw.json` was re-exported after 28
 * malformed metre identities were marked internal, the partition was not recomputed, and the
 * build joined 35,370 assignments onto 35,648 nodes without complaint -- every node past the
 * first divergence taking another node's constellation, and the last 278 reading `undefined`
 * out of the end of a typed array.
 *
 * The exact public-export hash and assignment count must both match. Equal-size exports
 * can contain different identities or node order; a length check alone cannot detect that.
 */
if (detected.inputPublicExportHash !== inputPublicExportHash) {
    throw new Error("Constellation partition input hash does not match this public export; rebuild it");
}
if (detected.community.length !== nodes.length) {
    console.error(
        `\nConstellation partition does not fit this world.\n` +
            `  ${CONSTELLATIONS} holds ${detected.community.length.toLocaleString()} assignments\n` +
            `  ${IN} holds ${nodes.length.toLocaleString()} nodes\n\n` +
            `The partition is joined by position, so a length mismatch silently gives nodes\n` +
            `another node's constellation. Recompute it:\n\n` +
            `  node scripts/build-constellations.mjs\n`,
    );
    process.exit(1);
}
const community = Int32Array.from(detected.community);
const degree = nodes.map((n) => n.deg ?? 0);
console.log(
    `  ${nodes.length.toLocaleString()} nodes, ${edges.length.toLocaleString()} edges, ` +
        `${detected.counts.communities.toLocaleString()} communities (modularity ${detected.modularity.toFixed(3)})`,
);

const types = [...new Set(nodes.map((n) => n.type))].sort();
const typeIndex = new Map(types.map((t, i) => [t, i]));
const edgeTypes = [...new Set(edges.map((e) => e[2]))].sort();
const edgeTypeIndex = new Map(edgeTypes.map((t, i) => [t, i]));

/* ------------------------------------------------------ regions from communities - */

const sizes = new Map();
for (let i = 0; i < nodes.length; i += 1) {
    sizes.set(community[i], (sizes.get(community[i]) ?? 0) + 1);
}
const regionIds = [...sizes.entries()]
    .filter(([, size]) => size >= REGION_MIN)
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
const regionIndex = new Map(regionIds.map((id, i) => [id, i]));
console.log(`  ${regionIds.length} regions of ${REGION_MIN}+ members`);

/*
 * Every remaining node joins the region it has most links into.
 *
 * A node in a five-member community is not homeless; its group is simply too small to be a
 * place. Sending it to its best-connected region keeps it beside the things it is related to
 * and keeps the number of drawn regions small enough to compose deliberately.
 */
const linksToRegion = new Map();
for (const [source, target] of edges) {
    for (const [from, to] of [
        [source, target],
        [target, source],
    ]) {
        if (regionIndex.has(community[from])) continue;
        const region = regionIndex.get(community[to]);
        if (region === undefined) continue;
        const key = `${from}:${region}`;
        linksToRegion.set(key, (linksToRegion.get(key) ?? 0) + 1);
    }
}
const bestRegion = new Map();
for (const [key, count] of linksToRegion) {
    const [node, region] = key.split(":").map(Number);
    const current = bestRegion.get(node);
    if (!current || count > current.count) bestRegion.set(node, { region, count });
}

const regionOf = new Int32Array(nodes.length).fill(-1);
for (let i = 0; i < nodes.length; i += 1) {
    const own = regionIndex.get(community[i]);
    if (own !== undefined) regionOf[i] = own;
    else if (bestRegion.has(i)) regionOf[i] = bestRegion.get(i).region;
}
const marginal = [];
for (let i = 0; i < nodes.length; i += 1) if (regionOf[i] < 0) marginal.push(i);
console.log(`  ${marginal.length.toLocaleString()} nodes attach to no region`);

/* ------------------------------------- level one: inside each region - */

/*
 * Interiors are laid out first, and that ordering is the whole composition.
 *
 * The first version placed the regions against each other and then filled them in, which put
 * region centres about 240 units apart while a region of 3,512 members spreads over a radius
 * of several hundred. Every region overlapped every neighbour and the result was the ball
 * again, just built out of pieces. Laying the interiors out first means each region's real
 * radius is known, and the arrangement can then be told to keep them apart by it.
 */

const positions3 = new Float64Array(nodes.length * 3);
const localPositions = regionIds.map(() => null);
const membersOf = regionIds.map(() => []);
for (let i = 0; i < nodes.length; i += 1) {
    if (regionOf[i] >= 0) membersOf[regionOf[i]].push(i);
}

/* Edges bucketed by region in one pass: 185,693 edges times 33 regions would be six million
   comparisons done thirty-three times. */
const localEdges = regionIds.map(() => []);
for (const [source, target] of edges) {
    const r = regionOf[source];
    if (r >= 0 && r === regionOf[target]) localEdges[r].push([source, target]);
}

console.log("laying out region interiors ...");
const localStarted = Date.now();
const radii = [];
for (let r = 0; r < regionIds.length; r += 1) {
    const members = membersOf[r];
    if (!members.length) {
        radii.push(0);
        localPositions[r] = [];
        continue;
    }
    const local = new Map(members.map((id, i) => [id, i]));
    const localNodes = members.map((id, i) => ({ index: i, node: id }));
    const links = localEdges[r].map(([source, target]) => ({
        source: local.get(source),
        target: local.get(target),
    }));

    const sim = forceSimulation(localNodes, 3)
        .numDimensions(3)
        .force(
            "link",
            forceLink(links)
                .id((d) => d.index)
                .distance(16)
                .strength((link) => {
                    const a = degree[link.source.node ?? 0] || 1;
                    const b = degree[link.target.node ?? 0] || 1;
                    // Capped at 60 so a hub inside a region still holds its own members
                    // together instead of letting them float off.
                    return 1 / Math.min(a, b, 60);
                }),
        )
        .force("charge", forceManyBody().strength(-26).theta(0.9).distanceMax(420))
        .force("centre", forceCenter(0, 0, 0).strength(0.08))
        .stop();
    const ticks = Math.min(TICKS, 90 + Math.round(Math.sqrt(members.length) * 5));
    for (let i = 0; i < ticks; i += 1) sim.tick();

    /* The radius that matters is not the outermost stray node but where the region actually
       is: the 92nd percentile, so one escaped member does not reserve empty space for the
       whole arrangement. */
    const distances = localNodes
        .map((n) => Math.hypot(n.x, n.y, n.z))
        .sort((a, b) => a - b);
    const radius = distances[Math.min(distances.length - 1, Math.floor(distances.length * 0.92))];
    radii.push(Math.max(radius, 40));
    localPositions[r] = localNodes.map((n) => ({ node: n.node, x: n.x, y: n.y, z: n.z }));

    if ((r + 1) % 10 === 0) {
        process.stdout.write(
            `  ${r + 1}/${regionIds.length}  (${((Date.now() - localStarted) / 1000).toFixed(0)}s)
`,
        );
    }
}
console.log(`
  interiors settled in ${((Date.now() - localStarted) / 1000).toFixed(1)}s`);

/* ----------------------------------- level two: arranging the regions - */

const regionWeight = new Map();
for (const [a, b, weight] of detected.between) {
    const ra = regionIndex.get(a);
    const rb = regionIndex.get(b);
    if (ra === undefined || rb === undefined || ra === rb) continue;
    const key = ra < rb ? `${ra}:${rb}` : `${rb}:${ra}`;
    regionWeight.set(key, (regionWeight.get(key) ?? 0) + weight);
}

const regionNodes = regionIds.map((_, i) => ({ index: i }));
const regionLinks = [...regionWeight.entries()].map(([key, weight]) => {
    const [source, target] = key.split(":").map(Number);
    return { source, target, weight };
});

console.log(`arranging ${regionIds.length} regions ...`);
const regionSim = forceSimulation(regionNodes, 3)
    .numDimensions(3)
    .force(
        "link",
        forceLink(regionLinks)
            .id((d) => d.index)
            /*
             * Two regions never sit closer than their radii plus a margin.
             *
             * This is the line that stops the map collapsing. Weight still matters - heavily
             * linked regions sit at the near end of what the radii allow - but it can only
             * ever pull them to touching, never through each other.
             */
            .distance((link) => {
                const a = radii[link.source.index ?? link.source];
                const b = radii[link.target.index ?? link.target];
                const floor = (a + b) * 1.95 + 260;
                return floor + 1400 / Math.sqrt(link.weight);
            })
            .strength((link) => Math.min(0.22, link.weight / 2600)),
    )
    /* Repulsion scales with the region's actual extent rather than with its member count, so
       a sparse region of 500 claims the room it visually occupies. */
    .force(
        "charge",
        forceManyBody()
            .strength((d) => -900 - radii[d.index] * 52)
            .theta(0.85),
    )
    .force("centre", forceCenter(0, 0, 0).strength(0.008))
    .stop();
for (let i = 0; i < 900; i += 1) regionSim.tick();

/* Translate each interior into its region's place. */
for (let r = 0; r < regionIds.length; r += 1) {
    const centre = regionNodes[r];
    for (const point of localPositions[r]) {
        positions3[point.node * 3] = centre.x + point.x;
        positions3[point.node * 3 + 1] = centre.y + point.y;
        positions3[point.node * 3 + 2] = centre.z + point.z;
    }
}

const marginalPlaced = marginal;

/*
 * The unattached, on a shell outside everything else.
 *
 * These nodes have no public relationship at all. They are real subjects and dropping them
 * would misreport the corpus, but the structure implies no position for them, so they go on a
 * wide sphere around the whole arrangement - visibly outside the structure, which is exactly
 * what having no connections means. A Fibonacci spiral spreads them evenly rather than
 * clumping them at the poles.
 */
let worldRadius = 0;
for (let r = 0; r < regionNodes.length; r += 1) {
    worldRadius = Math.max(
        worldRadius,
        Math.hypot(regionNodes[r].x, regionNodes[r].y, regionNodes[r].z) + radii[r],
    );
}
const shell = worldRadius * 1.22 + 260;
for (let i = 0; i < marginalPlaced.length; i += 1) {
    const t = (i + 0.5) / marginalPlaced.length;
    const phi = Math.acos(1 - 2 * t);
    const theta = Math.PI * (1 + Math.sqrt(5)) * i;
    const id = marginalPlaced[i];
    positions3[id * 3] = shell * Math.sin(phi) * Math.cos(theta);
    positions3[id * 3 + 1] = shell * Math.sin(phi) * Math.sin(theta);
    positions3[id * 3 + 2] = shell * Math.cos(phi);
}

/* ------------------------------------------------------------- normalise - */

let extent = 0;
for (let i = 0; i < nodes.length * 3; i += 1) extent = Math.max(extent, Math.abs(positions3[i]));
const scale = extent > 0 ? 1000 / extent : 1;

const positions = new Float32Array(nodes.length * 3);
for (let i = 0; i < nodes.length * 3; i += 1) positions[i] = positions3[i] * scale;

/* ------------------------------------------------------------------ pack - */

const nodeType = new Uint8Array(nodes.length);
const nodeGroup = new Uint8Array(nodes.length);
// Degree clamps at 65,535; the real maximum is 7,347, so nothing is lost today and a busier
// future hub degrades to "very busy" rather than wrapping to zero.
const nodeDegree = new Uint16Array(nodes.length);
// -1 becomes 65,535 here and is read back as "no region" by the client.
const nodeRegion = new Uint16Array(nodes.length);
for (let i = 0; i < nodes.length; i += 1) {
    nodeType[i] = typeIndex.get(nodes[i].type) ?? 0;
    nodeGroup[i] = GROUPS.indexOf(groupOf(nodes[i]));
    nodeDegree[i] = Math.min(65535, degree[i]);
    nodeRegion[i] = regionOf[i] < 0 ? 65535 : regionOf[i];
}

/*
 * Edges are ordered so the ones worth drawing at world scale come first.
 *
 * Measured: a fragment shaded at alpha 0.01 costs exactly what one at alpha 1.0 costs, so
 * drawing invisible structural edges was paying full price for nothing. Sorted to the back,
 * they can be left out of the draw range at world scale and brought back on selection.
 *
 * Within the semantic edges the rank is the degree of the *less* connected endpoint. Ranking
 * by the busier end would put Indra's 7,347 spokes first and the first ten thousand edges
 * drawn would be three hubs' worth of star. Ranking by the quieter end asks whether *both*
 * ends are well connected, which draws the structure between major subjects first.
 */
const STRUCTURAL = new Set(["CONTAINS", "HAS_CHANDAS", "HAS_TEXT_VERSION", "HAS_TRANSLATION"]);
const rank = (edge) => Math.min(degree[edge[0]] ?? 0, degree[edge[1]] ?? 0);
const order = edges
    .map((_, index) => index)
    .sort((a, b) => {
        const sa = STRUCTURAL.has(edges[a][2]) ? 1 : 0;
        const sb = STRUCTURAL.has(edges[b][2]) ? 1 : 0;
        if (sa !== sb) return sa - sb;
        return rank(edges[b]) - rank(edges[a]);
    });
const semanticEdgeCount = edges.filter((edge) => !STRUCTURAL.has(edge[2])).length;

const edgePairs = new Uint32Array(edges.length * 2);
const edgeType = new Uint8Array(edges.length);
// An edge joining two regions is a bridge, and bridges are the part of the picture that shows
// how the corpus hangs together. Flagged here so the renderer can lift them without a lookup.
const edgeBridge = new Uint8Array(edges.length);
for (let i = 0; i < order.length; i += 1) {
    const edge = edges[order[i]];
    edgePairs[i * 2] = edge[0];
    edgePairs[i * 2 + 1] = edge[1];
    edgeType[i] = edgeTypeIndex.get(edge[2]) ?? 0;
    const ra = regionOf[edge[0]];
    const rb = regionOf[edge[1]];
    edgeBridge[i] = ra >= 0 && rb >= 0 && ra !== rb ? 1 : 0;
}

const sections = [
    ["positions", positions],
    ["nodeType", nodeType],
    ["nodeGroup", nodeGroup],
    ["nodeDegree", nodeDegree],
    ["nodeRegion", nodeRegion],
    ["edgePairs", edgePairs],
    ["edgeType", edgeType],
    ["edgeBridge", edgeBridge],
];

let offset = 0;
const layout = [];
for (const [name, array] of sections) {
    // Each section starts on an 8-byte boundary so the client can build typed-array views over
    // the buffer instead of copying every section out of it.
    offset = Math.ceil(offset / 8) * 8;
    layout.push({ name, offset, length: array.length, type: array.constructor.name });
    offset += array.byteLength;
}
const buffer = Buffer.alloc(offset);
for (let i = 0; i < sections.length; i += 1) {
    Buffer.from(sections[i][1].buffer, sections[i][1].byteOffset, sections[i][1].byteLength).copy(
        buffer,
        layout[i].offset,
    );
}

/*
 * The hub index: names worth showing before anything is selected.
 *
 * Drawn from degree, but not from degree alone. The busiest nodes in this graph by raw count
 * are metres - triṣṭup is attached to 4,195 verses - and a world whose visible labels are four
 * metre names has described the prosody of the corpus rather than its subject.
 */
const NAMEABLE = new Set(["deity", "person", "idea", "rite", "thing", "wording"]);
const hubs = nodes
    .map((_, index) => ({ index, group: GROUPS[nodeGroup[index]], degree: degree[index] }))
    .filter((entry) => NAMEABLE.has(entry.group))
    .sort((a, b) => b.degree - a.degree)
    .slice(0, 600)
    .map((entry) => entry.index);

/* The constellations, in the renderer's region order, with their centres in world units. */
const byId = new Map(detected.constellations.map((c) => [c.id, c]));
const constellations = regionIds.map((id, i) => {
    const described = byId.get(id) ?? {};
    const centre = regionNodes[i];
    return {
        id: i,
        community: id,
        name: described.name ?? null,
        size: membersOf[i].length,
        veda: described.veda ?? null,
        group: described.group ?? null,
        central: described.central ?? [],
        bridges: described.bridges ?? [],
        connectedShare: described.connectedShare ?? null,
        centre: [centre.x * scale, centre.y * scale, centre.z * scale].map((v) =>
            Number(v.toFixed(1)),
        ),
        radius: Number((radii[i] * scale).toFixed(1)),
    };
});

/*
 * world.bin is the one artifact that cannot declare its own lineage: it is a headerless
 * typed-array blob, so there is nowhere in it to put a hash. It is pinned from the outside
 * instead -- the manifest records its sha256 and its byte length, and the manifest is
 * itself pinned to the public export. That closes the chain: a world.bin from a different
 * build no longer matches the manifest that ships beside it, and `ids` is a positional join
 * onto it, so the alternative is a silent mislabelling of every node.
 */
const worldBinSha256 = createHash("sha256").update(buffer).digest("hex");

const manifest = {
    version: 2,
    inputPublicExportHash,
    worldBinSha256,
    worldBinBytes: buffer.byteLength,
    identityAudit,
    generated: raw.generated,
    source: { nodes: raw.counts.nodes, edges: raw.counts.edges },
    counts: { nodes: nodes.length, edges: edges.length },
    extent: 1000,
    ticks: TICKS,
    semanticEdges: semanticEdgeCount,
    groups: GROUPS,
    types,
    edgeTypes,
    sections: layout,
    hubs,
    maxDegree: Math.max(...degree),
    communities: {
        algorithm: detected.algorithm,
        resolution: detected.resolution,
        modularity: detected.modularity,
        detected: detected.counts.communities,
        drawn: regionIds.length,
        minSize: REGION_MIN,
        unattached: marginal.length,
    },
    constellations,
};

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(join(OUT_DIR, "world.bin"), buffer);
writeFileSync(join(OUT_DIR, "world.json"), JSON.stringify(manifest));
/*
 * The labels sidecar carries the public-export hash for the same reason world.json does.
 *
 * world.json and constellations.json were pinned to the exact public export and this file
 * was not, which left one shipped browser artifact outside the lineage contract: a
 * labels file built from a different export would still load, and every label would be a
 * real label -- of the wrong node. `ids` is a positional join onto world.bin, so that
 * failure is silent and reads as data rather than as a build error.
 */
const labels = {
    inputPublicExportHash,
    ids: nodes.map((n) => n.id),
    labels: nodes.map((n) => n.label ?? ""),
};
writeFileSync(join(OUT_DIR, "world.labels.json"), JSON.stringify(labels));

/* ----------------------------------------------------------------- report - */

const named = constellations.filter((c) => c.name).length;
console.log("\nwrote public/world/");
for (const [name, bytes] of [
    ["world.bin", buffer.byteLength],
    ["world.json", Buffer.byteLength(JSON.stringify(manifest))],
    ["world.labels.json", Buffer.byteLength(JSON.stringify(labels))],
]) {
    console.log(`  ${name.padEnd(20)} ${(bytes / 1e6).toFixed(2)} MB`);
}
console.log(`\n  ${constellations.length} constellations drawn, ${named} named from metrics`);
console.log(`  ${semanticEdgeCount.toLocaleString()} semantic edges before the structural tail`);
console.log(`  ${edgeBridge.reduce((a, b) => a + b, 0).toLocaleString()} bridge edges between regions`);
console.log(`  bytes per node (geometry only): ${(buffer.byteLength / nodes.length).toFixed(1)}`);
