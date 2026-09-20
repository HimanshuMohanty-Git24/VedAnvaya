import { describe, expect, it } from "vitest";
import type { World, WorldManifest } from "@/lib/world/artifact";
import { buildPathScene, worstSeparation } from "@/lib/world/planar";

/**
 * The planar route scene.
 *
 * This exists because of a defect that rendered perfectly and was wrong. The graph shell
 * computed the planar canvas's scope as
 *
 *     view === "FOCUS" && selected ? "focus" : "world"
 *
 * so choosing PATH in 2D fell through the ternary and drew the whole corpus as its
 * constellations. The route was nowhere on the canvas, no error was raised, and the reader
 * was shown a map of everything in answer to a question about two subjects. It survived
 * because the 3D renderer had drawn routes since the feature shipped: the capability
 * worked, in one of its two renderers, and every test of it exercised the one that worked.
 *
 * So what is asserted here is the *scene*: that a route produces a scene of its own kind,
 * that every stop and every step is in it, and that the order the service found is the
 * order drawn. `tests/e2e/graph-path.spec.ts` asserts the other half - that the shell
 * actually asks for this scene in both renderers.
 */

function makeWorld(nodeCount = 40): World {
    const edges: Array<[number, number]> = [];
    for (let i = 1; i < nodeCount; i += 1) edges.push([0, i]);

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

    return {
        manifest: {
            counts: { nodes: nodeCount, edges: edges.length },
            groups: ["deity", "passage", "idea"],
        } as unknown as WorldManifest,
        positions: new Float32Array(nodeCount * 3),
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

const BAND = { width: 1000, height: 700 };

describe("buildPathScene", () => {
    it("declares itself a route, so no branch has to infer it from rootId", () => {
        /* The renderer used to read `rootId === null` as "this is the world map". A route has
           a rootId and is not a Focus scene, so every branch keyed on that test would have
           drawn it with Focus's ink and Focus's label rules. */
        const scene = buildPathScene(makeWorld(), [0, 5, 9], BAND);
        expect(scene.kind).toBe("path");
    });

    it("draws every stop on the route and nothing else", () => {
        const route = [0, 5, 9, 12];
        const scene = buildPathScene(makeWorld(), route, BAND);
        expect(scene.nodes).toHaveLength(route.length);
        expect(scene.nodes.map((node) => node.id)).toEqual(route);
    });

    it("draws one line per step, in route order", () => {
        const route = [0, 5, 9, 12];
        const scene = buildPathScene(makeWorld(), route, BAND);
        expect(scene.edges).toHaveLength(route.length - 1);
        scene.edges.forEach((edge, i) => {
            expect(scene.nodes[edge.a].id).toBe(route[i]);
            expect(scene.nodes[edge.b].id).toBe(route[i + 1]);
        });
    });

    it("keys each step negatively, so the inspector knows it is a hop and not an artifact edge", () => {
        /* A hop is not one edge in the world file. The negative key is the same convention the
           spatial view uses, and it is what stops the relationship inspector looking it up. */
        const scene = buildPathScene(makeWorld(), [0, 5, 9], BAND);
        expect(scene.edges.map((edge) => edge.edge)).toEqual([-1, -2]);
    });

    it("names every stop, because five labels is not a label budget", () => {
        const scene = buildPathScene(makeWorld(), [0, 5, 9, 12, 17], BAND);
        expect(scene.nodes.every((node) => node.labelled)).toBe(true);
    });

    it("draws the two endpoints larger than the waypoints between them", () => {
        const scene = buildPathScene(makeWorld(), [0, 5, 9, 12], BAND);
        const [first, second, third, last] = scene.nodes;
        expect(first.radius).toBeGreaterThan(second.radius);
        expect(last.radius).toBeGreaterThan(third.radius);
        expect(first.ring).toBe(0);
        expect(last.ring).toBe(0);
        expect(second.ring).toBe(1);
    });

    it("anchors the route with no slack, because the order is the answer", () => {
        const scene = buildPathScene(makeWorld(), [0, 5, 9], BAND);
        for (let i = 0; i < scene.nodes.length; i += 1) {
            expect(scene.field.slack[i]).toBe(0);
        }
    });

    it("seats the stops far enough apart for a hop phrase to be set between them", () => {
        /* The guarantee is the pitch floor, and the floor is what a phrase needs: a label the
           layout cannot fit is a label it drops, and a route of unexplained dots is what a
           reader is left with. */
        const scene = buildPathScene(makeWorld(), [0, 5, 9, 12], BAND);
        expect(scene.guarantee).not.toBeNull();
        /* `worstSeparation` reports the closest pair anywhere in the scene, which on a
           single-row route is a consecutive pair and is exactly the pitch. */
        expect(worstSeparation(scene).distance).toBeGreaterThanOrEqual(
            scene.guarantee as number,
        );
    });

    it("wraps a long route rather than running it off the edge of a narrow band", () => {
        const narrow = { width: 480, height: 700 };
        const scene = buildPathScene(makeWorld(), [0, 5, 9, 12, 17], narrow);
        const rows = new Set(scene.nodes.map((node) => Math.round(node.y)));
        expect(rows.size).toBeGreaterThan(1);
        /* And still inside the band it was given. */
        for (const node of scene.nodes) {
            expect(Math.abs(node.x)).toBeLessThanOrEqual(narrow.width / 2);
        }
    });

    it("draws nothing for an empty route rather than throwing", () => {
        const scene = buildPathScene(makeWorld(), [], BAND);
        expect(scene.nodes).toHaveLength(0);
        expect(scene.edges).toHaveLength(0);
        expect(scene.rootId).toBeNull();
    });
});
