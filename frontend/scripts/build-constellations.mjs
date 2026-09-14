#!/usr/bin/env node
/**
 * Find the constellations, and describe them honestly.
 *
 * Phase 6 laid the whole public graph out with one force simulation and got a ball: uniformly
 * dense, no interior structure, sixty frames a second of nothing. The cause is not the
 * simulation but the absence of any grouping for it to express. This step supplies one.
 *
 * ## Louvain, and why not the others
 *
 * Louvain maximises modularity by repeatedly moving nodes to the neighbouring community that
 * most improves it, then contracting each community to a node and repeating. It is O(n log n)
 * in practice, it is the method the rest of the field is measured against, and at 35,370
 * nodes it finishes in seconds.
 *
 * Leiden fixes a real Louvain defect - it can leave a community internally disconnected - and
 * would be the better choice if one were available in JavaScript; there is no maintained
 * implementation, and writing one to draw a picture is not a good trade. The disconnection
 * defect is checked for rather than assumed away: every community's internal connectivity is
 * measured below and reported, so a bad split shows up in the build log instead of silently
 * in the map. Label propagation is faster and much less stable between runs, which is
 * disqualifying for a layout that has to be identical on every build. Infomap has no
 * JavaScript implementation either.
 *
 * ## What a constellation is allowed to be called
 *
 * A name is only generated when the metrics support it. If one Veda holds most of a
 * community and one node is far more central than the rest, the community can be called after
 * them, because both facts are countable. Otherwise it keeps a number and carries its
 * description in structured fields. The failure this avoids is the one where a clustering
 * algorithm's output is dressed in confident thematic prose that nothing in the data
 * supports.
 *
 * Nothing here is written to Neo4j. Community membership is a property of this drawing, not
 * of the corpus, and the ontology is frozen.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import Graph from "graphology";
import louvain from "graphology-communities-louvain";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
    args.set(process.argv[i].replace(/^--/, ""), process.argv[i + 1]);
}
const IN = resolve(ROOT, args.get("in") ?? ".world/world.raw.json");
const OUT = resolve(ROOT, args.get("out") ?? ".world/constellations.json");
/* Fixed, so a build is reproducible. Louvain's node traversal order changes its output, and a
   world that rearranges itself between deploys is a world nobody can learn. */
const SEED = "vedanvaya-world-v1";
/*
 * Resolution below 1 merges; above 1 splits.
 *
 * Swept over 0.6 to 1.6 against this graph. Below 0.9 the corpus collapses toward a handful
 * of enormous groups that say little; above 1.3 it shatters into hundreds of fragments too
 * small to name or to lay out as regions. The value here is where the largest community stays
 * under about a fifth of the corpus while the count stays small enough to compose.
 */
const RESOLUTION = Number(args.get("resolution") ?? 1.05);

/* Relationships that exist for every verse carry no information about any particular one, and
   at 38,794 of them they dominate modularity: left in, Louvain groups the corpus by metre. */
const STRUCTURAL = new Set(["CONTAINS", "HAS_CHANDAS", "HAS_TEXT_VERSION", "HAS_TRANSLATION"]);

console.log(`reading ${IN} ...`);
const raw = JSON.parse(readFileSync(IN, "utf8"));
const nodes = raw.nodes;
const edges = raw.edges;
console.log(`  ${nodes.length.toLocaleString()} nodes, ${edges.length.toLocaleString()} edges`);

/* ------------------------------------------------------------- detection - */

const graph = new Graph({ type: "undirected", multi: false });
for (let i = 0; i < nodes.length; i += 1) graph.addNode(String(i));
let used = 0;
for (const [source, target, type] of edges) {
    if (STRUCTURAL.has(type)) continue;
    const a = String(source);
    const b = String(target);
    if (a === b) continue;
    // Merge parallel relationships into one weighted link: two subjects joined by three
    // different predicates are more strongly tied than two joined by one.
    if (graph.hasEdge(a, b)) {
        graph.setEdgeAttribute(a, b, "weight", graph.getEdgeAttribute(a, b, "weight") + 1);
    } else {
        graph.addEdge(a, b, { weight: 1 });
        used += 1;
    }
}
console.log(`  ${used.toLocaleString()} distinct semantic links used for detection`);

console.log(`running Louvain (resolution ${RESOLUTION}) ...`);
const started = Date.now();
const assignment = louvain(graph, {
    resolution: RESOLUTION,
    getEdgeWeight: "weight",
    rng: makeRng(SEED),
});
const modularity = louvain.detailed(graph, {
    resolution: RESOLUTION,
    getEdgeWeight: "weight",
    rng: makeRng(SEED),
}).modularity;
console.log(`  settled in ${((Date.now() - started) / 1000).toFixed(1)}s`);

/** A small deterministic PRNG, so the same input always produces the same communities. */
function makeRng(seed) {
    let h = 2166136261;
    for (let i = 0; i < seed.length; i += 1) {
        h ^= seed.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return () => {
        h += 0x6d2b79f5;
        let t = h;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

/* ------------------------------------------------------------ describing - */

const community = new Int32Array(nodes.length);
for (let i = 0; i < nodes.length; i += 1) community[i] = assignment[String(i)] ?? -1;

const members = new Map();
for (let i = 0; i < nodes.length; i += 1) {
    const id = community[i];
    const bucket = members.get(id);
    if (bucket) bucket.push(i);
    else members.set(id, [i]);
}

const degree = nodes.map((n) => n.deg ?? 0);

/* Internal and external degree per node, which is what makes a bridge identifiable: a bridge
   is a node most of whose connections leave its own community. */
const inside = new Int32Array(nodes.length);
const outside = new Int32Array(nodes.length);
for (const [source, target, type] of edges) {
    if (STRUCTURAL.has(type)) continue;
    if (community[source] === community[target]) {
        inside[source] += 1;
        inside[target] += 1;
    } else {
        outside[source] += 1;
        outside[target] += 1;
    }
}

/** Links between communities, which become the edges of the constellation graph. */
const between = new Map();
for (const [source, target, type] of edges) {
    if (STRUCTURAL.has(type)) continue;
    const a = community[source];
    const b = community[target];
    if (a === b) continue;
    const key = a < b ? `${a}:${b}` : `${b}:${a}`;
    between.set(key, (between.get(key) ?? 0) + 1);
}

function dominant(values) {
    const counts = new Map();
    for (const value of values) {
        if (value == null) continue;
        counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    if (!counts.size) return null;
    const [name, count] = [...counts].sort((a, b) => b[1] - a[1])[0];
    const total = [...counts.values()].reduce((a, b) => a + b, 0);
    return { name, count, share: count / total };
}

/**
 * Is this community actually one connected piece?
 *
 * Louvain does not guarantee it, and a community that is really two unrelated groups would be
 * drawn as one region of the map and read as one subject. Measured rather than trusted.
 */
function connectedShare(ids) {
    const set = new Set(ids);
    const seen = new Set();
    let largest = 0;
    for (const start of ids) {
        if (seen.has(start)) continue;
        let size = 0;
        const stack = [start];
        seen.add(start);
        while (stack.length) {
            const node = stack.pop();
            size += 1;
            if (!graph.hasNode(String(node))) continue;
            for (const neighbour of graph.neighbors(String(node))) {
                const index = Number(neighbour);
                if (set.has(index) && !seen.has(index)) {
                    seen.add(index);
                    stack.push(index);
                }
            }
        }
        largest = Math.max(largest, size);
    }
    return ids.length ? largest / ids.length : 1;
}

const GROUP_OF_TYPE = JSON.parse(
    readFileSync(join(HERE, "world-groups.json"), "utf8"),
);

const constellations = [...members.entries()]
    .map(([id, ids]) => {
        const sorted = [...ids].sort((a, b) => degree[b] - degree[a]);
        const veda = dominant(ids.map((i) => nodes[i].veda));
        const group = dominant(ids.map((i) => GROUP_OF_TYPE[nodes[i].type] ?? "other"));
        const nonPassage = sorted.filter(
            (i) => (GROUP_OF_TYPE[nodes[i].type] ?? "other") !== "passage",
        );
        const bridges = [...ids]
            .filter((i) => outside[i] > 0 && outside[i] >= inside[i] && degree[i] >= 8)
            .sort((a, b) => outside[b] - outside[a])
            .slice(0, 6);
        return {
            id,
            size: ids.length,
            members: ids,
            /* The named members are the ones a reader could recognise: passages are excluded
               because a constellation of twenty thousand verses would be described by three
               arbitrary verse numbers. */
            central: nonPassage.slice(0, 8),
            bridges,
            veda,
            group,
            connectedShare: Number(connectedShare(ids).toFixed(4)),
            internalEdges: ids.reduce((sum, i) => sum + inside[i], 0) / 2,
            externalEdges: ids.reduce((sum, i) => sum + outside[i], 0),
        };
    })
    .sort((a, b) => b.size - a.size);

/* ------------------------------------------------------------------ name - */

const GROUP_NOUN = {
    deity: "deity",
    "unresolved-deity": "devata slot",
    passage: "passage",
    person: "seer",
    idea: "idea",
    rite: "rite",
    thing: "thing",
    wording: "wording",
    derived: "metric",
    record: "record",
    other: "subject",
};
const VEDA_NAME = { RV: "Rigvedic", SV: "Samavedic", YV: "Yajurvedic", AV: "Atharvavedic" };

/**
 * A name only where the numbers carry it.
 *
 * Two thresholds, both arbitrary in the sense that any threshold is, but both stated: a Veda
 * has to hold at least sixty per cent of a community before the community is called after it,
 * and the leading member has to be at least twice as connected as the next before it is
 * called after that member. Where neither holds the constellation keeps its number, which is
 * not a failure - it is the honest description of a group that is genuinely mixed.
 */
function nameOf(constellation) {
    const parts = [];
    if (constellation.veda && constellation.veda.share >= 0.6) {
        parts.push(VEDA_NAME[constellation.veda.name] ?? constellation.veda.name);
    }
    const [first, second] = constellation.central;
    const lead =
        first !== undefined &&
        (second === undefined || degree[first] >= degree[second] * 2) &&
        degree[first] >= 40
            ? nodes[first].label
            : null;
    if (lead) parts.push(lead);
    else if (constellation.group && constellation.group.share >= 0.5) {
        parts.push(`${GROUP_NOUN[constellation.group.name] ?? constellation.group.name} cluster`);
    }
    if (!parts.length) return null;
    return parts.join(" · ");
}

for (const constellation of constellations) {
    constellation.name = nameOf(constellation);
}

/* ---------------------------------------------------------------- report - */

console.log(`\n  ${constellations.length} communities, modularity ${modularity.toFixed(4)}`);
const largest = constellations[0];
console.log(
    `  largest ${largest.size.toLocaleString()} (${((largest.size / nodes.length) * 100).toFixed(1)}% of the corpus)`,
);
const tiny = constellations.filter((c) => c.size < 10).length;
console.log(`  fewer than 10 members: ${tiny}`);

console.log("\n  the twenty largest");
console.log(
    "   #   size   conn   veda        group      name / central members",
);
for (const c of constellations.slice(0, 20)) {
    const veda = c.veda ? `${c.veda.name} ${(c.veda.share * 100).toFixed(0)}%` : "mixed";
    const group = c.group ? `${c.group.name}` : "-";
    const label =
        c.name ?? `Constellation ${c.id} · ${c.central.slice(0, 3).map((i) => nodes[i].label).join(", ")}`;
    console.log(
        `  ${String(c.id).padStart(3)} ${String(c.size).padStart(6)} ` +
            `${(c.connectedShare * 100).toFixed(0).padStart(5)}% ${veda.padEnd(11)} ${group.padEnd(10)} ${label.slice(0, 60)}`,
    );
}

const disconnected = constellations.filter((c) => c.size >= 20 && c.connectedShare < 0.9);
if (disconnected.length) {
    console.log(
        `\n  WARNING: ${disconnected.length} communities of 20+ are under 90% connected.` +
            " Louvain can leave a community internally split; these are the candidates.",
    );
}

writeFileSync(
    OUT,
    JSON.stringify({
        generated: new Date().toISOString(),
        algorithm: "louvain",
        resolution: RESOLUTION,
        seed: SEED,
        modularity,
        counts: { nodes: nodes.length, communities: constellations.length },
        community: Array.from(community),
        between: [...between.entries()].map(([key, weight]) => {
            const [a, b] = key.split(":").map(Number);
            return [a, b, weight];
        }),
        constellations: constellations.map((c) => ({
            id: c.id,
            size: c.size,
            name: c.name,
            veda: c.veda,
            group: c.group,
            central: c.central,
            bridges: c.bridges,
            connectedShare: c.connectedShare,
            internalEdges: c.internalEdges,
            externalEdges: c.externalEdges,
        })),
    }),
    "utf8",
);
console.log(`\nwrote ${OUT}`);
