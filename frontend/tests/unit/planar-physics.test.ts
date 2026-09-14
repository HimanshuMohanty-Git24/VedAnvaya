import { describe, expect, it } from "vitest";
import type { World, WorldManifest } from "@/lib/world/artifact";
import {
    buildNeighbourhood,
    isAtRest,
    pickPlanar,
    planarBounds,
    stepPlanar,
} from "@/lib/world/planar";

/**
 * The planar simulation.
 *
 * Coordinates are not asserted anywhere here. A force layout's exact output is a function of
 * its tuning constants, and a test that pins positions fails on every tuning change while
 * catching nothing a reader would notice. What is asserted is the behaviour the view promises:
 * that it comes to rest, that dragging a subject moves what is attached to it, that nothing
 * escapes, and that a held node stays under the pointer.
 */

/** A star with a dense centre and a tail, built by hand. */
function makeWorld(nodeCount = 24): World {
    const edges: Array<[number, number]> = [];
    for (let i = 1; i < nodeCount; i += 1) edges.push([0, i]);
    // A few links among the neighbours, so the graph is not a pure star.
    for (let i = 1; i < nodeCount - 1; i += 3) edges.push([i, i + 1]);

    const positions = new Float32Array(nodeCount * 3);
    const edgePairs = new Uint32Array(edges.length * 2);
    edges.forEach(([a, b], i) => {
        edgePairs[i * 2] = a;
        edgePairs[i * 2 + 1] = b;
    });

    const degree = new Uint16Array(nodeCount);
    for (const [a, b] of edges) {
        degree[a] += 1;
        degree[b] += 1;
    }

    const adjacencyStart = new Uint32Array(nodeCount + 1);
    const counts = new Uint32Array(nodeCount);
    for (const [a, b] of edges) {
        counts[a] += 1;
        counts[b] += 1;
    }
    let running = 0;
    for (let i = 0; i < nodeCount; i += 1) {
        adjacencyStart[i] = running;
        running += counts[i];
    }
    adjacencyStart[nodeCount] = running;
    const cursor = adjacencyStart.slice();
    const adjacency = new Uint32Array(running);
    edges.forEach(([a, b], i) => {
        adjacency[cursor[a]++] = i;
        adjacency[cursor[b]++] = i;
    });

    const manifest = {
        counts: { nodes: nodeCount, edges: edges.length },
        groups: ["deity", "unresolved-deity", "passage", "person", "idea"],
    } as unknown as WorldManifest;

    return {
        manifest,
        positions,
        nodeType: new Uint8Array(nodeCount),
        nodeGroup: new Uint8Array(nodeCount),
        nodeDegree: degree,
        nodeRegion: new Uint16Array(nodeCount),
        edgePairs,
        edgeType: new Uint8Array(edges.length),
        edgeBridge: new Uint8Array(edges.length),
        adjacencyStart,
        adjacency,
    };
}

function settle(graph: ReturnType<typeof buildNeighbourhood>, steps = 600) {
    let energy = Infinity;
    for (let i = 0; i < steps; i += 1) energy = stepPlanar(graph);
    return energy;
}

describe("building a neighbourhood", () => {
    it("puts the chosen subject at the centre and rings the rest around it", () => {
        const world = makeWorld();
        const graph = buildNeighbourhood(world, 0);
        const root = graph.nodes.find((node) => node.id === 0);
        expect(root?.ring).toBe(0);
        expect(graph.nodes.filter((node) => node.ring === 1).length).toBeGreaterThan(0);
    });

    it("caps how much is drawn, however connected the subject is", () => {
        /* A deity with thousands of edges must not try to draw them: the world view already
           answers "how much is attached", and a diagram of five thousand marks answers
           nothing. */
        const world = makeWorld(400);
        const graph = buildNeighbourhood(world, 0, { ringOne: 20, ringTwo: 10 });
        expect(graph.nodes.length).toBeLessThanOrEqual(31);
    });

    it("only includes edges whose ends are both drawn", () => {
        const world = makeWorld(60);
        const graph = buildNeighbourhood(world, 0, { ringOne: 8, ringTwo: 4 });
        for (const edge of graph.edges) {
            expect(graph.nodes[edge.a]).toBeDefined();
            expect(graph.nodes[edge.b]).toBeDefined();
        }
    });
});

describe("the simulation comes to rest", () => {
    it("loses energy until it is still", () => {
        /* The invariant that keeps a diagram readable. A graph that never settles is a
           screensaver, and it is unreadable while it moves. */
        const graph = buildNeighbourhood(makeWorld(), 0);
        const early = stepPlanar(graph);
        const late = settle(graph);
        expect(late).toBeLessThan(early);
        expect(isAtRest(late)).toBe(true);
    });

    it("wakes when something is dragged, and settles again after it is let go", () => {
        const graph = buildNeighbourhood(makeWorld(), 0);
        settle(graph);

        const dragged = graph.nodes.find((node) => node.ring === 1);
        expect(dragged).toBeDefined();
        if (!dragged) return;
        dragged.held = true;
        dragged.x += 900;
        dragged.y -= 700;
        stepPlanar(graph);
        dragged.held = false;

        const disturbed = stepPlanar(graph);
        expect(isAtRest(disturbed)).toBe(false);
        expect(isAtRest(settle(graph, 900))).toBe(true);
    });
});

describe("pulling a subject moves what is attached to it", () => {
    it("drags its neighbours after it", () => {
        const world = makeWorld();
        const graph = buildNeighbourhood(world, 0);
        settle(graph);

        const hub = graph.nodes.find((node) => node.ring === 0);
        const neighbour = graph.nodes.find((node) => node.ring === 1);
        expect(hub && neighbour).toBeTruthy();
        if (!hub || !neighbour) return;

        const before = { x: neighbour.x, y: neighbour.y };
        hub.held = true;
        hub.x += 1200;
        for (let i = 0; i < 140; i += 1) stepPlanar(graph);

        const moved = Math.hypot(neighbour.x - before.x, neighbour.y - before.y);
        // Not a coordinate assertion: only that the spring transmitted the pull at all.
        expect(moved).toBeGreaterThan(1);
    });

    it("leaves a held node exactly where it is put", () => {
        const graph = buildNeighbourhood(makeWorld(), 0);
        const node = graph.nodes[3];
        node.held = true;
        node.x = 321;
        node.y = -654;
        for (let i = 0; i < 40; i += 1) stepPlanar(graph);
        expect(node.x).toBe(321);
        expect(node.y).toBe(-654);
        expect(node.vx).toBe(0);
        expect(node.vy).toBe(0);
    });
});

describe("nothing escapes and nothing overlaps", () => {
    it("keeps every node within a finite bound", () => {
        const graph = buildNeighbourhood(makeWorld(40), 0);
        settle(graph, 900);
        for (const node of graph.nodes) {
            expect(Number.isFinite(node.x)).toBe(true);
            expect(Number.isFinite(node.y)).toBe(true);
        }
        const { minX, maxX } = planarBounds(graph);
        expect(maxX - minX).toBeLessThan(40000);
    });

    it("separates nodes that start on top of each other", () => {
        /* Coincident nodes have no direction to push apart along, so the step function nudges
           them deterministically. Without that they stay welded together for good. */
        const graph = buildNeighbourhood(makeWorld(12), 0);
        for (const node of graph.nodes) {
            node.x = 0;
            node.y = 0;
            node.vx = 0;
            node.vy = 0;
        }
        settle(graph, 400);
        const stacked = graph.nodes.filter(
            (node) => Math.hypot(node.x, node.y) < 0.5 && node.ring !== 0,
        );
        expect(stacked.length).toBe(0);
    });
});

describe("picking", () => {
    it("finds a node under the point and nothing under empty space", () => {
        const graph = buildNeighbourhood(makeWorld(), 0);
        settle(graph);
        const target = graph.nodes[2];
        expect(pickPlanar(graph, target.x, target.y)).toBe(2);
        expect(pickPlanar(graph, 99999, 99999)).toBeNull();
    });
});
