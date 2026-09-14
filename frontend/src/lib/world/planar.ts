import { edgesOf, otherEnd, type World } from "./artifact";

/**
 * The planar view: a manuscript diagram you can pull apart.
 *
 * This is not the 3D view flattened, and it is emphatically not a fallback. It answers a
 * different question. The world map answers "where does this sit in the corpus"; this answers
 * "what is attached to this, and how tightly" - and for that, being able to take hold of a
 * subject and feel its neighbours resist is worth more than depth.
 *
 * ## Why a live simulation here and a precomputed layout there
 *
 * The world is 35,370 nodes, which is far past what a browser can settle in a frame budget, so
 * its positions are computed once offline. A neighbourhood is a few hundred, which is well
 * inside it. So this runs a real simulation every frame: masses, springs, repulsion, damping.
 * Nothing is faked, and that is what makes dragging a hub feel like dragging something that is
 * attached to things.
 *
 * ## Why it comes to rest
 *
 * A graph that jitters forever is unreadable and looks like a screensaver. Energy enters only
 * when the reader puts it in - a drag, a selection, a new neighbourhood - and decays. Below a
 * threshold the simulation stops stepping entirely rather than continuing to compute
 * imperceptible motion, so an untouched diagram is perfectly still and costs nothing.
 */

export type PlanarNode = {
    /** Index into the world artifact, so every view names subjects the same way. */
    id: number;
    x: number;
    y: number;
    vx: number;
    vy: number;
    /** Heavier nodes move less when pulled, which reads as "this one is more established". */
    mass: number;
    radius: number;
    group: number;
    degree: number;
    /** Depth from the root: 0 is the subject itself, 1 its neighbours, 2 theirs. */
    ring: number;
    /** Held by the pointer. A held node ignores forces and is moved directly. */
    held: boolean;
    /** Pinned nodes resist but are not immovable; the root is pinned softly. */
    anchorX: number | null;
    anchorY: number | null;
};

export type PlanarEdge = {
    a: number;
    b: number;
    /** Index into the world edge arrays, so the inspector can look the relationship up. */
    edge: number;
    rest: number;
    bridge: boolean;
};

export type PlanarGraph = {
    nodes: PlanarNode[];
    edges: PlanarEdge[];
    index: Map<number, number>;
    rootId: number | null;
};

/*
 * Tuned against a real neighbourhood, not chosen for tidiness.
 *
 * Agni has 5,385 connections; the first ring alone is capped at sixty and every one of them
 * springs toward the same centre. With the first numbers tried - repulsion 5,200 against a
 * spring constant of 0.035 - a spring stretched a hundred units pulled at 3.5 while repulsion
 * at fifty units apart pushed at 2.1, so the ring collapsed into a knot at the rest radius and
 * the diagram was unreadable. Repulsion has to dominate at the distances nodes actually sit
 * at, and the spring has to be weak enough that it positions rather than compresses.
 */
const SPRING = 0.012;
const REPULSION = 210;
const DAMPING = 0.86;
const CENTRE_PULL = 0.0009;
/** Below this total kinetic energy the graph is considered at rest and stops stepping. */
const SLEEP_ENERGY = 0.055;

/**
 * Build a neighbourhood around one subject.
 *
 * Two rings, with the second capped. A deity with 7,347 edges has a second ring larger than
 * anything a person can read, and drawing it would turn the diagram back into the hairball
 * the world view already handles better. The cap keeps the busiest neighbours, which are the
 * ones most likely to be the reason a reader is here.
 */
export function buildNeighbourhood(
    world: World,
    root: number,
    { ringOne = 48, ringTwo = 40 }: { ringOne?: number; ringTwo?: number } = {},
): PlanarGraph {
    const ring = new Map<number, number>([[root, 0]]);

    const byDegree = (a: number, b: number) => world.nodeDegree[b] - world.nodeDegree[a];

    const first: number[] = [];
    for (const edge of edgesOf(world, root)) {
        const other = otherEnd(world, edge, root);
        if (!ring.has(other)) first.push(other);
    }
    first.sort(byDegree);
    for (const node of first.slice(0, ringOne)) ring.set(node, 1);

    const second: number[] = [];
    for (const [node, depth] of [...ring]) {
        if (depth !== 1) continue;
        for (const edge of edgesOf(world, node)) {
            const other = otherEnd(world, edge, node);
            if (!ring.has(other)) second.push(other);
        }
    }
    second.sort(byDegree);
    for (const node of [...new Set(second)].slice(0, ringTwo)) {
        if (!ring.has(node)) ring.set(node, 2);
    }

    const ids = [...ring.keys()];
    const index = new Map(ids.map((id, i) => [id, i]));

    /*
     * Starting positions are rings, not random.
     *
     * A random start makes the first second of every selection a visible scramble while the
     * simulation untangles it. Placing each ring on a circle at the radius it will roughly
     * settle at means the diagram arrives nearly right and then relaxes, which reads as
     * settling rather than as sorting itself out.
     */
    const counts = [0, 0, 0];
    for (const depth of ring.values()) counts[depth] += 1;
    /*
     * The ring radius grows with how many have to fit on it.
     *
     * A subject with six neighbours and one with sixty should not put them on the same circle:
     * the second would have them overlapping shoulder to shoulder. Circumference scales with
     * the count, so the radius scales with it too.
     */
    const ringRadius = [
        0,
        Math.max(150, counts[1] * 13),
        Math.max(300, counts[1] * 13 + counts[2] * 9),
    ];
    const placed = [0, 0, 0];
    const nodes: PlanarNode[] = ids.map((id) => {
        const depth = ring.get(id) ?? 2;
        const radius = ringRadius[depth];
        const slot = placed[depth];
        placed[depth] += 1;
        const angle = (slot / Math.max(1, counts[depth])) * Math.PI * 2 + depth * 0.7;
        const degree = world.nodeDegree[id];
        return {
            id,
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius,
            vx: 0,
            vy: 0,
            // Mass rises with connectedness but slowly: a hub should feel weightier to pull,
            // not immovable.
            mass: 1 + Math.cbrt(degree) * 0.5,
            radius: 4 + Math.cbrt(degree) * 1.5,
            group: world.nodeGroup[id],
            degree,
            ring: depth,
            held: false,
            anchorX: depth === 0 ? 0 : null,
            anchorY: depth === 0 ? 0 : null,
        };
    });

    const seen = new Set<number>();
    const edges: PlanarEdge[] = [];
    for (const id of ids) {
        for (const edge of edgesOf(world, id)) {
            if (seen.has(edge)) continue;
            const a = world.edgePairs[edge * 2];
            const b = world.edgePairs[edge * 2 + 1];
            if (!index.has(a) || !index.has(b)) continue;
            seen.add(edge);
            const depth = Math.max(ring.get(a) ?? 0, ring.get(b) ?? 0);
            edges.push({
                a: index.get(a) as number,
                b: index.get(b) as number,
                edge,
                // Rest length follows the ring radius, so the springs agree with where the
                // nodes were placed instead of fighting the arrangement back to a knot.
                rest: depth === 1 ? ringRadius[1] * 0.82 : ringRadius[2] * 0.5,
                bridge: world.edgeBridge[edge] === 1,
            });
        }
    }

    return { nodes, edges, index, rootId: root };
}

/**
 * One step of the simulation.
 *
 * Semi-implicit Euler with velocity damping. Repulsion is all-pairs, which is O(n squared) and
 * entirely fine here: the neighbourhood is capped at about 150 nodes, so that is 22,000
 * distance calculations a frame, well under a millisecond. A Barnes-Hut tree would be correct
 * for the world and is pure overhead at this size.
 *
 * Returns the kinetic energy left in the system, which is what decides whether to step again.
 */
export function stepPlanar(graph: PlanarGraph, dt = 1): number {
    const { nodes, edges } = graph;

    for (const node of nodes) {
        if (node.held) continue;
        let fx = 0;
        let fy = 0;

        for (const other of nodes) {
            if (other === node) continue;
            let dx = node.x - other.x;
            let dy = node.y - other.y;
            let d2 = dx * dx + dy * dy;
            if (d2 < 0.01) {
                // Exactly coincident nodes have no direction to separate along; nudge one
                // deterministically rather than leaving them stuck together forever.
                dx = (node.id % 7) - 3 || 1;
                dy = (node.id % 5) - 2 || 1;
                d2 = dx * dx + dy * dy;
            }
            const d = Math.sqrt(d2);
            /*
             * Repulsion falls as 1/d, not 1/d squared.
             *
             * An inverse-square law is what gravity does, and it is the wrong shape for laying
             * out a graph: it is overwhelming at close range and negligible a little further
             * out, so nodes either sit on top of each other or ignore each other entirely,
             * and a neighbourhood settles into a knot with a few strays flung to the edge -
             * which is exactly what the first version produced. Fruchterman and Reingold's
             * k-squared-over-d falls off slowly enough to keep pushing at the distances the
             * nodes actually occupy, which is what spreads a ring evenly.
             */
            const touching = node.radius + other.radius + 8;
            const force = d < touching ? (REPULSION * 2.6) / d : REPULSION / d;
            fx += (dx / d) * force;
            fy += (dy / d) * force;
        }

        fx -= node.x * CENTRE_PULL * 60;
        fy -= node.y * CENTRE_PULL * 60;

        if (node.anchorX !== null && node.anchorY !== null) {
            // A soft anchor, not a pin: the subject can be dragged off centre and drifts back.
            fx += (node.anchorX - node.x) * 0.02;
            fy += (node.anchorY - node.y) * 0.02;
        }

        node.vx = (node.vx + (fx / node.mass) * dt) * DAMPING;
        node.vy = (node.vy + (fy / node.mass) * dt) * DAMPING;
    }

    for (const edge of edges) {
        const a = nodes[edge.a];
        const b = nodes[edge.b];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d = Math.hypot(dx, dy) || 0.01;
        const extension = d - edge.rest;
        /* Clamped: an edge to a node that has drifted a long way should pull it back steadily,
           not fling it through everything in between. Unclamped springs were what produced the
           long straight lines shooting off the first version of this view. */
        const force = Math.max(-60, Math.min(60, extension)) * SPRING;
        const ux = (dx / d) * force;
        const uy = (dy / d) * force;
        // Force is divided by mass on each end, so pulling a leaf barely moves the hub it
        // hangs from and pulling the hub swings the whole neighbourhood.
        if (!a.held) {
            a.vx += ux / a.mass;
            a.vy += uy / a.mass;
        }
        if (!b.held) {
            b.vx -= ux / b.mass;
            b.vy -= uy / b.mass;
        }
    }

    let energy = 0;
    for (const node of nodes) {
        if (node.held) {
            node.vx = 0;
            node.vy = 0;
            continue;
        }
        node.x += node.vx * dt;
        node.y += node.vy * dt;
        energy += (node.vx * node.vx + node.vy * node.vy) * node.mass;
    }
    return energy / Math.max(1, nodes.length);
}

export function isAtRest(energy: number) {
    return energy < SLEEP_ENERGY;
}

/** The node under a point in graph coordinates, nearest first. */
export function pickPlanar(graph: PlanarGraph, x: number, y: number, slack = 6): number | null {
    let best: number | null = null;
    let bestD = Infinity;
    for (let i = 0; i < graph.nodes.length; i += 1) {
        const node = graph.nodes[i];
        const d = Math.hypot(node.x - x, node.y - y);
        if (d <= node.radius + slack && d < bestD) {
            bestD = d;
            best = i;
        }
    }
    return best;
}

/** The bounding box of the whole diagram, for fitting the viewport to it. */
export function planarBounds(graph: PlanarGraph) {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const node of graph.nodes) {
        minX = Math.min(minX, node.x - node.radius);
        minY = Math.min(minY, node.y - node.radius);
        maxX = Math.max(maxX, node.x + node.radius);
        maxY = Math.max(maxY, node.y + node.radius);
    }
    if (!Number.isFinite(minX)) return { minX: -100, minY: -100, maxX: 100, maxY: 100 };
    return { minX, minY, maxX, maxY };
}


/**
 * The whole world, projected onto a plane.
 *
 * Not a second layout. The composed artifact already encodes what this view exists to show -
 * which constellations there are, how large, how far apart, and which relationships bridge
 * them - and it took minutes of offline simulation to settle. Re-deriving that in the browser
 * would produce a worse arrangement of the same graph and spend the frame budget doing it. So
 * x and y are taken as they are, and the reader is looking at the same world the spatial view
 * draws, from directly above.
 *
 * What is drawn is a cut, not the whole: at world scale an individual verse is a speck among
 * twenty thousand, so this keeps the most connected subjects and the edges between the ones
 * that survive. The result is the backbone, which is what a map of a corpus is for.
 */
export function buildWorldProjection(
    world: World,
    { nodes: nodeBudget = 2600, edges: edgeBudget = 5200 }: { nodes?: number; edges?: number } = {},
): PlanarGraph {
    const count = world.manifest.counts.nodes;

    const ranked = Array.from({ length: count }, (_, i) => i)
        .filter((i) => world.nodeRegion[i] !== 65535)
        .sort((a, b) => world.nodeDegree[b] - world.nodeDegree[a])
        .slice(0, nodeBudget);
    const index = new Map(ranked.map((id, i) => [id, i]));

    const nodes: PlanarNode[] = ranked.map((id) => {
        const degree = world.nodeDegree[id];
        return {
            id,
            x: world.positions[id * 3],
            y: world.positions[id * 3 + 1],
            vx: 0,
            vy: 0,
            mass: 1,
            radius: 1.6 + Math.cbrt(degree) * 0.85,
            group: world.nodeGroup[id],
            degree,
            /* Ring is read by the painter as importance rather than as distance here: the
               busiest subjects are drawn at full weight and named, the rest recede. */
            ring: degree >= 60 ? 0 : degree >= 14 ? 1 : 2,
            held: false,
            anchorX: null,
            anchorY: null,
        };
    });

    const edges: PlanarEdge[] = [];
    const total = world.manifest.counts.edges;
    for (let i = 0; i < total && edges.length < edgeBudget; i += 1) {
        const a = index.get(world.edgePairs[i * 2]);
        const b = index.get(world.edgePairs[i * 2 + 1]);
        if (a === undefined || b === undefined) continue;
        edges.push({ a, b, edge: i, rest: 0, bridge: world.edgeBridge[i] === 1 });
    }

    return { nodes, edges, index, rootId: null };
}
