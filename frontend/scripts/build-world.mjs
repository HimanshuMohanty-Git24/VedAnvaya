#!/usr/bin/env node
/**
 * Lay out the public graph once, offline, and pack it for the World View to load.
 *
 * ## Why the layout is not computed in the browser
 *
 * A force simulation is O(n log n) per tick with Barnes-Hut and needs a few hundred ticks to
 * settle. At 35,370 nodes that is minutes of arithmetic, and the published practical ceiling
 * for an interactive in-browser force layout is around five to ten thousand nodes. Every tool
 * that draws graphs this size - Gephi, Graphistry, Cosmograph - computes the layout somewhere
 * other than the frame loop and ships coordinates. Doing it here also buys something a runtime
 * layout cannot: the world is in the same place on every visit, which matters when a reader is
 * meant to learn where things are.
 *
 * The frame loop still runs a live simulation, but only over the few hundred nodes of a
 * neighbourhood, which is well inside what a browser settles smoothly.
 *
 * ## What comes out
 *
 *   world.bin     positions, degrees, types, and the edge list, as typed arrays
 *   world.json    the manifest: type tables, counts, extent, and the hub index
 *   world.labels.json  labels, separately, because geometry should paint before text arrives
 *
 * Usage:  node scripts/build-world.mjs [--ticks 320] [--in ../.world/world.raw.json]
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
    forceCenter,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    forceZ,
} from "d3-force-3d";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const OUT_DIR = join(ROOT, "public", "world");

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
    args.set(process.argv[i].replace(/^--/, ""), process.argv[i + 1]);
}
const TICKS = Number(args.get("ticks") ?? 320);
const IN = resolve(ROOT, args.get("in") ?? ".world/world.raw.json");

/**
 * The semantic groups, and the ontology types that fall in each.
 *
 * This is the single mapping. It replaces the copy that lived in `graph-canvas.tsx` beside a
 * hard-coded light/dark hex pair per group, which had drifted from the `--va-group-*` tokens
 * the theme declares for exactly these ten names. Colour now comes from the token layer at
 * render time; this file decides only which group a type belongs to, and the group ids are
 * baked into the artifact so the client does not re-derive them for 35,370 nodes on load.
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

const TYPE_TO_GROUP = new Map(
    Object.entries({
        Devata: "deity",
        MANTRA: "passage",
        HYMN: "passage",
        SECTION: "passage",
        STRUCTURAL_CONTAINER: "passage",
        PASSAGE: "passage",
        Rishi: "person",
        RishiFamily: "person",
        Tribe: "person",
        Ritual: "rite",
        RitualRole: "rite",
        SocialRite: "rite",
        Offering: "rite",
        Formula: "wording",
        FormulaFamily: "wording",
        Chandas: "wording",
        DerivedMetric: "derived",
        InterpretiveClaim: "derived",
        DevataAscription: "record",
        SemanticAssertion: "record",
        AgentiveAssertion: "record",
        Object: "thing",
        Weapon: "thing",
        Substance: "thing",
        Plant: "thing",
        Animal: "thing",
        Metal: "thing",
        Crop: "thing",
        River: "thing",
        Place: "thing",
        Concept: "idea",
        PhilosophicalConcept: "idea",
        ActionPredicate: "idea",
        Action: "idea",
        Condition: "idea",
        HumanConcern: "idea",
        Quality: "idea",
        State: "idea",
        DeityAxis: "idea",
        Epithet: "idea",
        NaturalPhenomenon: "idea",
        CosmicEntity: "idea",
    }),
);

function groupOf(node) {
    if (node.type === "Devata") return node.deity === true ? "deity" : "unresolved-deity";
    return TYPE_TO_GROUP.get(node.type) ?? "other";
}

/* ------------------------------------------------------------------ read - */

if (!existsSync(IN)) {
    console.error(
        `No world export at ${IN}.\nRun:  python scripts/export_graph_world.py\nfirst; it reads the frozen store and writes that file.`,
    );
    process.exit(1);
}

console.log(`reading ${IN} ...`);
const raw = JSON.parse(readFileSync(IN, "utf8"));
const nodes = raw.nodes;
const edges = raw.edges;
console.log(`  ${nodes.length.toLocaleString()} nodes, ${edges.length.toLocaleString()} edges`);

const types = [...new Set(nodes.map((n) => n.type))].sort();
const typeIndex = new Map(types.map((t, i) => [t, i]));
const edgeTypes = [...new Set(edges.map((e) => e[2]))].sort();
const edgeTypeIndex = new Map(edgeTypes.map((t, i) => [t, i]));

/* ---------------------------------------------------------------- layout - */

/*
 * Link strength falls with the degree of the busier endpoint.
 *
 * Indra has 7,347 edges and the metre triṣṭup has 4,195. At uniform strength those two pull
 * a fifth of the corpus into a single knot and the rest of the structure disappears behind
 * it. Dividing by the heavier endpoint's degree is d3's own default heuristic and it is the
 * difference between a hairball and a figure with arms.
 */
const degree = nodes.map((n) => n.deg ?? 0);
const simNodes = nodes.map((n, i) => ({ index: i }));
const simLinks = edges.map(([s, t]) => ({ source: s, target: t }));

console.log(`laying out, ${TICKS} ticks ...`);
const started = Date.now();
const sim = forceSimulation(simNodes, 3)
    .numDimensions(3)
    .force(
        "link",
        forceLink(simLinks)
            .id((d) => d.index)
            .distance(28)
            .strength((link) => {
                const a = degree[link.source.index ?? link.source] || 1;
                const b = degree[link.target.index ?? link.target] || 1;
                return 1 / Math.min(a, b);
            }),
    )
    /*
     * theta 0.9 rather than the 0.8 default: this runs offline over a graph with a very long
     * degree tail, and the looser Barnes-Hut approximation costs accuracy no one can see at
     * this scale while taking a noticeable fraction off a build that runs in minutes.
     */
    /*
     * Repulsion is strong and long-range, and the pull to the centre is nearly absent.
     *
     * The first settings produced a sphere: a uniformly dense ball with no visible interior
     * structure, which is what a force layout gives you when the centring force is strong
     * enough to overwhelm the differences between regions. It rendered at sixty frames a
     * second and told the reader nothing, which is the failure mode this phase is meant to
     * avoid rather than the one it is meant to measure.
     *
     * Raising repulsion and letting `distanceMax` reach most of the cloud lets groups that
     * are only weakly linked drift apart instead of being packed together, and cutting the
     * axis springs to a tenth keeps them from being pulled back. The origin forces are not
     * removed entirely because 997 nodes have no edges at all and nothing else would stop
     * them leaving.
     */
    .force("charge", forceManyBody().strength(-120).theta(0.9).distanceMax(2600))
    .force("centre", forceCenter(0, 0, 0).strength(0.04))
    .force("x", forceX(0).strength(0.0012))
    .force("y", forceY(0).strength(0.0012))
    .force("z", forceZ(0).strength(0.0012))
    .stop();

for (let i = 0; i < TICKS; i += 1) {
    sim.tick();
    if ((i + 1) % 40 === 0) {
        const pct = Math.round(((i + 1) / TICKS) * 100);
        process.stdout.write(`  ${pct}%  (${((Date.now() - started) / 1000).toFixed(0)}s)\r`);
    }
}
console.log(`\n  settled in ${((Date.now() - started) / 1000).toFixed(1)}s`);

/* ------------------------------------------------------------- normalise - */

// Scale the settled cloud into a fixed cube so the camera has one set of distances to work
// with regardless of how the simulation happened to spread out on a given build.
let extent = 0;
for (const node of simNodes) {
    extent = Math.max(extent, Math.abs(node.x), Math.abs(node.y), Math.abs(node.z));
}
const scale = extent > 0 ? 1000 / extent : 1;

const positions = new Float32Array(nodes.length * 3);
for (let i = 0; i < simNodes.length; i += 1) {
    positions[i * 3] = simNodes[i].x * scale;
    positions[i * 3 + 1] = simNodes[i].y * scale;
    positions[i * 3 + 2] = simNodes[i].z * scale;
}

/* ------------------------------------------------------------------ pack - */

const nodeType = new Uint8Array(nodes.length);
const nodeGroup = new Uint8Array(nodes.length);
// Degree is clamped to 65,535; the real maximum is 7,347, so nothing is lost today and a
// future build with a busier hub degrades to "very busy" rather than wrapping to zero.
const nodeDegree = new Uint16Array(nodes.length);
for (let i = 0; i < nodes.length; i += 1) {
    nodeType[i] = typeIndex.get(nodes[i].type) ?? 0;
    nodeGroup[i] = GROUPS.indexOf(groupOf(nodes[i]));
    nodeDegree[i] = Math.min(65535, degree[i]);
}

/*
 * Edges are ordered so the ones worth drawing at world scale come first.
 *
 * This is the artifact's main concession to the frame budget, and it exists because of a
 * measurement. Drawing something at alpha 0.012 costs exactly what drawing it at alpha 1.0
 * costs: the fragment is still shaded and still blended. The first build drew all 185,693
 * edges every frame, most of them structural and invisible, and an Intel Iris Xe held 15 fps.
 *
 * `CONTAINS` and `HAS_CHANDAS` join a verse to the book that holds it and to its metre. There
 * are 38,794 of them, they are true, and they say nothing a reader came to a map to find:
 * every verse has a parent and a metre, so the relationship carries no information about any
 * particular verse. Sorted to the back, they can be excluded from the draw range entirely at
 * world scale and brought back the moment something is selected, which is when a verse's own
 * container genuinely matters.
 */
const STRUCTURAL = new Set(["CONTAINS", "HAS_CHANDAS", "HAS_TEXT_VERSION", "HAS_TRANSLATION"]);

/*
 * Within the semantic edges, the backbone comes first.
 *
 * The ranking key is the degree of the *less* connected endpoint, descending, and the choice
 * between that and the more connected one is the whole difference between a skeleton and a
 * star. Ranking by the busier end puts Indra's 7,347 edges at the front, and the first ten
 * thousand edges drawn are then all the spokes of two or three hubs - which is exactly the
 * shape the neighbourhood API already produces and the reason this artifact exists.
 *
 * Ranking by the quieter end asks instead: are *both* of these things well connected? An edge
 * from Indra to a single verse scores that verse's degree, which is small. An edge from Indra
 * to Agni, or from a metre to a seer family, scores high. Taking edges in that order draws the
 * structure the corpus has between its major subjects first and fills in the long tail of
 * leaf attachments last, which is precisely what a level-of-detail cut wants.
 */
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
for (let i = 0; i < order.length; i += 1) {
    const edge = edges[order[i]];
    edgePairs[i * 2] = edge[0];
    edgePairs[i * 2 + 1] = edge[1];
    edgeType[i] = edgeTypeIndex.get(edge[2]) ?? 0;
}

const sections = [
    ["positions", positions],
    ["nodeType", nodeType],
    ["nodeGroup", nodeGroup],
    ["nodeDegree", nodeDegree],
    ["edgePairs", edgePairs],
    ["edgeType", edgeType],
];

let offset = 0;
const layout = [];
for (const [name, array] of sections) {
    // Each section starts on an 8-byte boundary so the client can build typed-array views
    // directly over the ArrayBuffer instead of copying every section out of it.
    offset = Math.ceil(offset / 8) * 8;
    layout.push({
        name,
        offset,
        length: array.length,
        type: array.constructor.name,
    });
    offset += array.byteLength;
}
const buffer = Buffer.alloc(offset);
for (let i = 0; i < sections.length; i += 1) {
    Buffer.from(
        sections[i][1].buffer,
        sections[i][1].byteOffset,
        sections[i][1].byteLength,
    ).copy(buffer, layout[i].offset);
}

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(join(OUT_DIR, "world.bin"), buffer);

/*
 * The hub index: the nodes worth naming before a reader has selected anything.
 *
 * Drawn from degree, but not from degree alone. The busiest nodes in this graph by raw count
 * are metres - triṣṭup is attached to 4,195 verses - and a world whose visible labels are
 * four metre names describes the prosody of the corpus rather than its subject matter. So
 * passages and the reified record types are held out of the index, and what is left is the
 * deities, seers, ideas and rites a reader would recognise as the things the corpus is about.
 */
const NAMEABLE = new Set(["deity", "person", "idea", "rite", "thing", "wording"]);
const hubs = nodes
    .map((node, index) => ({ index, group: GROUPS[nodeGroup[index]], degree: degree[index] }))
    .filter((entry) => NAMEABLE.has(entry.group))
    .sort((a, b) => b.degree - a.degree)
    .slice(0, 600)
    .map((entry) => entry.index);

const manifest = {
    version: 1,
    generated: raw.generated,
    source: { nodes: raw.counts.nodes, edges: raw.counts.edges },
    counts: { nodes: nodes.length, edges: edges.length },
    extent: 1000,
    ticks: TICKS,
    /**
     * Edges before this index carry meaning a reader is looking for; the rest are structural
     * containment and metre. The renderer draws the first run at world scale and the whole
     * array once something is selected.
     */
    semanticEdges: semanticEdgeCount,
    groups: GROUPS,
    types,
    edgeTypes,
    sections: layout,
    hubs,
    maxDegree: Math.max(...degree),
};
writeFileSync(join(OUT_DIR, "world.json"), JSON.stringify(manifest));
writeFileSync(
    join(OUT_DIR, "world.labels.json"),
    JSON.stringify({
        ids: nodes.map((n) => n.id),
        labels: nodes.map((n) => n.label ?? ""),
    }),
);

/* ----------------------------------------------------------------- report - */

const sizes = {
    "world.bin": buffer.byteLength,
    "world.json": Buffer.byteLength(JSON.stringify(manifest)),
    "world.labels.json": Buffer.byteLength(
        JSON.stringify({ ids: nodes.map((n) => n.id), labels: nodes.map((n) => n.label ?? "") }),
    ),
};
console.log("\nwrote public/world/");
let total = 0;
for (const [name, bytes] of Object.entries(sizes)) {
    total += bytes;
    console.log(`  ${name.padEnd(20)} ${(bytes / 1e6).toFixed(2)} MB`);
}
console.log(`  ${"total".padEnd(20)} ${(total / 1e6).toFixed(2)} MB`);
console.log(
    `\n  bytes per node (geometry only): ${(buffer.byteLength / nodes.length).toFixed(1)}`,
);
console.log(`  groups: ${GROUPS.length}, node types: ${types.length}, edge types: ${edgeTypes.length}`);
console.log(`  hub index: ${hubs.length} nameable nodes`);
