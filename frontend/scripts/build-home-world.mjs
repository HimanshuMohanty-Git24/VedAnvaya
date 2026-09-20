/**
 * Cut a small, real piece of the Knowledge World for the front door.
 *
 * ## Why a slice and not a drawing
 *
 * The homepage used to carry a hand-built diagram: twenty-four invented nodes, its own shapes,
 * its own palette, its own physics. It was competent and it was a lie of a particular kind -
 * it showed the *idea* of a graph rather than the graph, so the first real thing a reader saw
 * after clicking through bore no relation to what they had been looking at.
 *
 * This takes the actual artifact the World View draws, selects sixty-odd nodes from it, and
 * ships their real identifiers, real groups, real degrees and real coordinates. Every node in
 * the hero is a node you can click through to. Nothing is invented, so nothing can drift.
 *
 * ## Why the obvious selection does not work
 *
 * Taking the most-connected entities gives a dust cloud. Measured: the top sixty by degree have
 * eighty-six edges between them and thirty-three of the sixty have none at all - because a
 * deity's five thousand connections are overwhelmingly to *passages*, and passages are excluded
 * here (a hero full of "RV 1.32.5" names nothing a newcomer recognises).
 *
 * So the set is grown rather than ranked: start from the most connected entity, walk outward
 * along entity-to-entity edges only, and keep what is reachable. That produces a piece of the
 * corpus that genuinely hangs together.
 *
 * Growing it unrestricted has the opposite failure - forty-nine of sixty-four came back
 * deities, which in the world's palette is one colour, and four fifths of the edges were a
 * single predicate. A hero that is one colour and one relationship describes the corpus badly.
 * Per-group caps hold the shape open, and the edge budget is dealt out predicate by predicate
 * so the rarer kinds survive alongside the common one.
 *
 * ## Why a subject can be refused for standing too close to one already taken
 *
 * The coordinates are the world's own, and the world was laid out for 35,370 subjects in a
 * canvas the size of a page. At the size of a hero panel that layout does not separate:
 * measured on the running panel, fifteen to eighteen of the fifty nearest-neighbour distances
 * came in under six CSS pixels, and the closest pair was 2.3 px apart at 1440 and 1.4 px at
 * 390. The camera cannot fix it - the sweep from 1.6 to 2.6 times the cloud radius moved the
 * closest pair between 1.0 and 2.0 px and never changed the count under six - because framing
 * scales every distance at once.
 *
 * Two subjects a pixel apart are one disc with two meanings, and the rear one cannot even be
 * picked: the picker scores by depth as well as distance, so whichever is nearer the camera
 * wins every time. The pairs turned out to be the deity-and-word doublets the layout had every
 * reason to place together - "Agni" the deity on top of "fire (agni)" the thing, "Soma" on
 * "soma juice (soma)", "the Waters" on "waters (āpaḥ)" - so the front door was showing the
 * same subject twice as a smudge.
 *
 * So a candidate standing within `MIN_SEPARATION` of one already admitted is refused, and the
 * growth takes the next neighbour instead. Nothing is moved: a coordinate here is still the
 * one the offline simulation produced, which is the whole claim this file rests on. Measured,
 * the rule costs no subjects at all - the neighbourhood is deep enough to supply fifty either
 * way - and it replaces the doublets with Rudra, Visnu, Usas, the Sarasvati river and kingship.
 *
 * Usage:
 *     node scripts/build-home-world.mjs
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(HERE, "..");
const WORLD_DIR = join(FRONTEND, "public", "world");
const OUT = join(FRONTEND, "public", "data", "home-world.json");

/*
 * Which groups may appear, and how many of each.
 *
 * Passages are out because their names are citations, and a reader who has not arrived yet has
 * no use for "AVS 6.17.3". `record` and `derived` are out because they are the graph's own
 * bookkeeping - reified ascriptions and per-Veda attribution counters - which are real nodes
 * and not subjects anyone browses.
 *
 * The caps are the shape of the thing, not a quota: deities are the corpus's densest entities
 * and should lead, but twenty of them rather than fifty leaves room for the rites, ideas and
 * substances that make the picture legible as a *world* rather than as a pantheon.
 */
const GROUP_CAPS = {
    deity: 20,
    rite: 9,
    idea: 9,
    thing: 9,
    person: 6,
    wording: 4,
    "unresolved-deity": 3,
};

const NODE_BUDGET = 60;
/** Enough to read as a fabric, few enough to stay a diagram at panel size. */
const EDGE_BUDGET = 110;

/**
 * How far apart two admitted subjects must stand, as a fraction of the unit cube's half-edge.
 *
 * 0.08 buys a closest pair of 16.9 CSS px at a 1440 viewport and 10.3 px at 390, measured off
 * the running panel at the framing it ships with. Below 0.06 the smallest gap drops under ten
 * pixels on a phone; above 0.10 the growth starts running out of eligible neighbours and the
 * idea and thing groups come back short, which is the one-colour failure the caps exist to
 * prevent - 47 nodes at 0.10 and 32 at 0.15.
 */
const MIN_SEPARATION = 0.08;

/* ------------------------------------------------------------------ read - */

function readArtifact() {
    const manifest = JSON.parse(readFileSync(join(WORLD_DIR, "world.json"), "utf8"));
    const buffer = readFileSync(join(WORLD_DIR, "world.bin"));
    const bytes = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
    const constructors = { Float32Array, Uint8Array, Uint16Array, Uint32Array };
    const sections = {};
    for (const section of manifest.sections) {
        sections[section.name] = new constructors[section.type](
            bytes,
            section.offset,
            section.length,
        );
    }
    const labels = JSON.parse(readFileSync(join(WORLD_DIR, "world.labels.json"), "utf8"));
    return { manifest, sections, labels };
}

const { manifest, sections, labels } = readArtifact();
const { positions, nodeGroup, nodeDegree, edgePairs, edgeType } = sections;

const groupName = (node) => manifest.groups[nodeGroup[node]];
const eligible = (node) => GROUP_CAPS[groupName(node)] !== undefined;

/* --------------------------------------------------------------- adjacency */

/*
 * Entity-to-entity adjacency only.
 *
 * Built over the whole edge list once. Six hundred and eighty-four of the corpus's 185,693
 * edges join two eligible entities, which is the real surface a hero can be cut from and is
 * why this file exists rather than a live query.
 */
const adjacency = new Map();
for (let edge = 0; edge < manifest.counts.edges; edge += 1) {
    const a = edgePairs[edge * 2];
    const b = edgePairs[edge * 2 + 1];
    if (a === b || !eligible(a) || !eligible(b)) continue;
    if (!adjacency.has(a)) adjacency.set(a, []);
    if (!adjacency.has(b)) adjacency.set(b, []);
    adjacency.get(a).push(b);
    adjacency.get(b).push(a);
}

const intraDegree = (node) => adjacency.get(node)?.length ?? 0;

/* --------------------------------------------------------------- selection */

/*
 * Grow outward from the densest entity, breadth first, honouring the caps.
 *
 * Breadth first rather than best first so the result is a neighbourhood and not a chain: each
 * ring is exhausted before the next begins, which keeps the selection compact enough that the
 * edges between its members are dense. Neighbours are considered in order of their own
 * connectedness so that within a ring the substantial nodes are taken before the incidental
 * ones, and ties break on the canonical id so a rebuild cannot silently reorder the hero.
 */
const seed = [...adjacency.keys()].sort(
    (a, b) => intraDegree(b) - intraDegree(a) || labels.ids[a].localeCompare(labels.ids[b]),
)[0];

/**
 * The centroid of a set and its widest per-axis distance from it.
 *
 * The reach is the divisor that lands the slice in a unit cube, so it is also the ruler the
 * separation rule has to be measured against: `MIN_SEPARATION` is a fraction of the unit cube
 * and the artifact's coordinates are not.
 */
function extent(nodes) {
    const centre = [0, 0, 0];
    for (const node of nodes) {
        for (let k = 0; k < 3; k += 1) centre[k] += positions[node * 3 + k];
    }
    for (let k = 0; k < 3; k += 1) centre[k] /= nodes.length;

    let reach = 0;
    for (const node of nodes) {
        for (let k = 0; k < 3; k += 1) {
            reach = Math.max(reach, Math.abs(positions[node * 3 + k] - centre[k]));
        }
    }
    return { centre, reach };
}

function distance(a, b) {
    let sum = 0;
    for (let k = 0; k < 3; k += 1) {
        const d = positions[a * 3 + k] - positions[b * 3 + k];
        sum += d * d;
    }
    return Math.sqrt(sum);
}

/**
 * Grow the selection outward from the seed, honouring the caps and the separation rule.
 *
 * `ruler` converts artifact units into unit-cube units. Null runs without the separation rule,
 * which is how the ruler itself is established: the scale is a property of the set chosen, so
 * the first pass chooses a set and the second uses its reach to keep subjects apart. The two
 * passes disagree about the ruler by well under a per cent, which is why this is two lines
 * rather than a fixed point iteration.
 */
function grow(ruler) {
    const taken = new Map(Object.keys(GROUP_CAPS).map((group) => [group, 0]));
    const selected = [];
    const seen = new Set();

    const admit = (node) => {
        const group = groupName(node);
        if (taken.get(group) >= GROUP_CAPS[group]) return false;
        if (ruler !== null) {
            for (const other of selected) {
                if (distance(node, other) / ruler < MIN_SEPARATION) return false;
            }
        }
        taken.set(group, taken.get(group) + 1);
        seen.add(node);
        selected.push(node);
        return true;
    };

    admit(seed);
    const queue = [seed];
    while (queue.length > 0 && selected.length < NODE_BUDGET) {
        const current = queue.shift();
        const neighbours = [...new Set(adjacency.get(current))]
            .filter((node) => !seen.has(node))
            .sort(
                (a, b) =>
                    intraDegree(b) - intraDegree(a) || labels.ids[a].localeCompare(labels.ids[b]),
            );
        for (const node of neighbours) {
            if (selected.length >= NODE_BUDGET) break;
            /* A node rejected for a full group or for standing too close is not marked seen: a
               later ring may still want it if the caps change, and leaving it unmarked keeps
               this loop's behaviour obvious. */
            if (admit(node)) queue.push(node);
        }
    }
    return selected;
}

const selected = grow(extent(grow(null)).reach);

const index = new Map(selected.map((node, i) => [node, i]));

/* ------------------------------------------------------------------ edges - */

const candidates = [];
for (let edge = 0; edge < manifest.counts.edges; edge += 1) {
    const a = edgePairs[edge * 2];
    const b = edgePairs[edge * 2 + 1];
    if (a === b || !index.has(a) || !index.has(b)) continue;
    candidates.push({ a, b, predicate: manifest.edgeTypes[edgeType[edge]] });
}

/*
 * Deal the edge budget out predicate by predicate.
 *
 * The same rule the graph uses to decide which connections to name, for the same reason: one
 * predicate here accounts for four fifths of the candidates, and a hero drawn by taking the
 * densest edges first would show a single relationship repeated a hundred times. Round-robin
 * over the kinds means every kind present survives into the picture before any kind repeats.
 */
const byPredicate = new Map();
for (const candidate of candidates) {
    if (!byPredicate.has(candidate.predicate)) byPredicate.set(candidate.predicate, []);
    byPredicate.get(candidate.predicate).push(candidate);
}
const dealOrder = [...byPredicate.entries()]
    .map(([predicate, list]) => ({
        predicate,
        list: list.sort(
            (x, y) =>
                nodeDegree[y.a] + nodeDegree[y.b] - (nodeDegree[x.a] + nodeDegree[x.b]) ||
                labels.ids[x.a].localeCompare(labels.ids[y.a]),
        ),
    }))
    .sort((x, y) => x.list.length - y.list.length || x.predicate.localeCompare(y.predicate));

const edges = [];
for (let round = 0; edges.length < EDGE_BUDGET; round += 1) {
    let dealt = 0;
    for (const { list } of dealOrder) {
        if (edges.length >= EDGE_BUDGET) break;
        const candidate = list[round];
        if (!candidate) continue;
        edges.push(candidate);
        dealt += 1;
    }
    if (dealt === 0) break;
}

/* -------------------------------------------------------------- positions - */

/*
 * The world's own coordinates, recentred and scaled to a unit cube.
 *
 * Not a fresh layout. These sixty nodes sit where the offline force simulation put them among
 * all 35,370, so the hero is a window onto the world rather than a picture resembling it - turn
 * the hero and you are turning the same arrangement the graph page opens on. Scaling is uniform
 * across the three axes, because scaling each to fill its own range would stretch the slice
 * into a shape the corpus does not have. That is exactly the flattening a previous phase had to
 * be torn out for.
 */
const { centre, reach } = extent(selected);
const scale = reach > 0 ? 1 / reach : 1;
const round3 = (value) => Math.round(value * 1000) / 1000;

/* ----------------------------------------------------------------- write - */

/*
 * The lineage this file ships 50 real node positions on.
 *
 * `source: "public/world/world.bin"` named the input and recorded nothing identifying it,
 * which left the homepage the one graph-derived artifact under public/ that nothing pins:
 * a slice taken from one export, served beside a world rebuilt from another, and every
 * coordinate a real coordinate of the wrong world. The manifest already carries both
 * hashes, so this carries them through -- the export the world was built from, and the
 * binary the positions were read out of.
 */
const inputPublicExportHash = manifest.inputPublicExportHash;
const inputWorldBinSha256 = manifest.worldBinSha256;
if (!inputPublicExportHash || !inputWorldBinSha256) {
    throw new Error(
        "public/world/world.json carries no inputPublicExportHash or worldBinSha256; " +
            "rebuild the world before slicing the homepage out of it",
    );
}

const payload = {
    version: 1,
    generated: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
    source: "public/world/world.bin",
    inputPublicExportHash,
    inputWorldBinSha256,
    note: "A real slice of the world artifact. Coordinates are the world's own, recentred and uniformly scaled into a unit cube; nothing is moved. Subjects standing within 0.08 of one already selected are refused rather than repositioned, so the slice is sparser than the world at this scale but every position in it is the world's.",
    minSeparation: MIN_SEPARATION,
    groups: manifest.groups,
    nodes: selected.map((node) => ({
        id: labels.ids[node],
        label: labels.labels[node],
        group: manifest.groups[nodeGroup[node]],
        // The degree in the whole corpus, not in this slice: node size should say how
        // substantial a subject is, not how much of it this small cut happened to keep.
        degree: nodeDegree[node],
        x: round3((positions[node * 3] - centre[0]) * scale),
        y: round3((positions[node * 3 + 1] - centre[1]) * scale),
        z: round3((positions[node * 3 + 2] - centre[2]) * scale),
    })),
    edges: edges.map((edge) => ({
        a: index.get(edge.a),
        b: index.get(edge.b),
        predicate: edge.predicate,
    })),
};

writeFileSync(OUT, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

/* ------------------------------------------------------------- diagnostics */

const groupCounts = new Map();
for (const node of payload.nodes) {
    groupCounts.set(node.group, (groupCounts.get(node.group) ?? 0) + 1);
}
const predicateCounts = new Map();
for (const edge of payload.edges) {
    predicateCounts.set(edge.predicate, (predicateCounts.get(edge.predicate) ?? 0) + 1);
}
const degrees = new Map(payload.nodes.map((_, i) => [i, 0]));
for (const edge of payload.edges) {
    degrees.set(edge.a, degrees.get(edge.a) + 1);
    degrees.set(edge.b, degrees.get(edge.b) + 1);
}
const isolated = [...degrees.values()].filter((value) => value === 0).length;

const spans = [0, 1, 2].map((k) => {
    const axis = payload.nodes.map((node) => [node.x, node.y, node.z][k]);
    return Math.max(...axis) - Math.min(...axis);
});
const widest = Math.max(...spans);

console.log(`Wrote ${OUT}`);
console.log(`  ${payload.nodes.length} nodes, ${payload.edges.length} edges, seeded at "${labels.labels[seed]}"`);
console.log(
    `  groups: ${[...groupCounts.entries()].map(([g, c]) => `${g} ${c}`).join(", ")}`,
);
console.log(
    `  predicates: ${[...predicateCounts.entries()]
        .sort((x, y) => y[1] - x[1])
        .map(([p, c]) => `${p} ${c}`)
        .join(", ")}`,
);
console.log(`  isolated nodes: ${isolated}`);

/* The number the separation rule exists to move. Reported because a threshold nobody measures
   the effect of is a constant with an opinion attached. */
const separations = payload.nodes
    .map((a, i) =>
        Math.min(
            ...payload.nodes
                .filter((_, j) => j !== i)
                .map((b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)),
        ),
    )
    .sort((x, y) => x - y);
console.log(
    `  nearest neighbour, unit space: min ${separations[0].toFixed(3)}, ` +
        `median ${separations[Math.floor(separations.length / 2)].toFixed(3)}`,
);
console.log(`  axis spans (x:y:z): ${spans.map((s) => (s / widest).toFixed(3)).join(" : ")}`);
