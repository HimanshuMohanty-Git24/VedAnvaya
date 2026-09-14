import { describe, expect, it } from "vitest";
import type { World, WorldLabels, WorldManifest } from "@/lib/world/artifact";
import { FOCUS_LINE_CAP, focusNeighbourhood } from "@/lib/world/focus";
import {
    PLANAR_TUNING,
    SPATIAL_REPULSION_FACTOR,
    SPATIAL_TUNING,
    createField,
    fieldAtRest,
    minSeparation,
    relaxOverlaps,
    stepField,
    tuningFor,
} from "@/lib/world/local-physics";
import {
    LEAF_ORB_RADIUS,
    PICK_TARGET,
    RESPACE_STEP,
    SEPARATION_MIN,
    SEPARATION_PAD,
    buildFocusScene,
    buildWorldScene,
    constellationCaption,
    markRadius,
    pickPlanar,
    preroll,
    respaceFocusScene,
    settleSlots,
    worstSeparation,
} from "@/lib/world/planar";

/**
 * The extracted simulation, and the separation the 2D layout promises.
 *
 * ## Why the promise is asserted here and not described in a comment
 *
 * Because the thing this phase replaced had the description and not the promise. Its comments
 * said the ring radius grew with how many had to fit on it, and it did - in graph units, which
 * `fit` then resolved to 0.33, so every Focus leaf was drawn 3.85 px across at every viewport
 * and every subject measured. Nothing was lying; nothing was checked either.
 *
 * So the invariant is `d >= max(SEPARATION_MIN, r_a + r_b + SEPARATION_PAD)` in CSS px, and it
 * is asserted over the real range of neighbour counts - the median subject's six as much as the
 * curated forty and the expansion ceiling's two hundred - at both the desktop and the phone
 * band, on the *settled* arrangement rather than the authored one.
 *
 * `tests/unit/planar-physics.test.ts` is the other half of this file's job and is deliberately
 * untouched: it asserts the model's behaviour through `planar.ts`'s own exports, so it passing
 * unmodified is what says the extraction to `local-physics.ts` changed nothing.
 */

const PREDICATES = [
    "HAS_DEVATA",
    "HAS_RISHI",
    "OCCURS_WITH",
    "EXACT_PARALLEL_OF",
    "MENTIONS",
    "MEASURES",
];

/**
 * A hub with `neighbours` distinct neighbours, some parallel edges and some cross-links.
 *
 * Built by hand rather than loaded, so the assertions do not move when the artifact is rebuilt.
 * Unlike the fixture in `planar-physics.test.ts` this one carries `manifest.edgeTypes`, because
 * it is read through `focus.ts` - which is exactly why that fixture cannot be rewritten to use
 * the curated path and why `buildNeighbourhood` survives for it.
 */
function makeWorld(neighbours: number): { world: World; labels: WorldLabels } {
    const count = neighbours + 1;
    const pairs: Array<[number, number, number]> = [];
    for (let i = 1; i <= neighbours; i += 1) pairs.push([0, i, i % PREDICATES.length]);
    // A second relationship on every fifth neighbour, so `spokes` exceeds `shown`.
    for (let i = 5; i <= neighbours; i += 5) pairs.push([0, i, (i + 2) % PREDICATES.length]);
    // Links among the neighbours, so `between` is not empty.
    for (let i = 1; i < neighbours; i += 3) pairs.push([i, i + 1, 2]);

    const edgePairs = new Uint32Array(pairs.length * 2);
    const edgeType = new Uint8Array(pairs.length);
    const degree = new Uint16Array(count);
    const counts = new Uint32Array(count);
    pairs.forEach(([a, b, type], i) => {
        edgePairs[i * 2] = a;
        edgePairs[i * 2 + 1] = b;
        edgeType[i] = type;
        degree[a] += 1;
        degree[b] += 1;
        counts[a] += 1;
        counts[b] += 1;
    });

    const adjacencyStart = new Uint32Array(count + 1);
    let running = 0;
    for (let i = 0; i < count; i += 1) {
        adjacencyStart[i] = running;
        running += counts[i];
    }
    adjacencyStart[count] = running;
    const cursor = adjacencyStart.slice();
    const adjacency = new Uint32Array(running);
    pairs.forEach(([a, b], i) => {
        adjacency[cursor[a]++] = i;
        adjacency[cursor[b]++] = i;
    });

    const nodeGroup = new Uint8Array(count);
    for (let i = 0; i < count; i += 1) nodeGroup[i] = i % 5;

    const manifest = {
        version: 2,
        counts: { nodes: count, edges: pairs.length },
        extent: 1000,
        groups: ["deity", "passage", "person", "idea", "record"],
        types: ["Devata", "Passage", "Person", "Concept", "Evidence"],
        edgeTypes: PREDICATES,
        hubs: [0],
        maxDegree: degree[0],
        sections: [],
    } as unknown as WorldManifest;

    const world: World = {
        manifest,
        positions: new Float32Array(count * 3),
        nodeType: new Uint8Array(count),
        nodeGroup,
        nodeDegree: degree,
        nodeRegion: new Uint16Array(count),
        edgePairs,
        edgeType,
        edgeBridge: new Uint8Array(pairs.length),
        adjacencyStart,
        adjacency,
    };
    const labels: WorldLabels = {
        ids: Array.from({ length: count }, (_, i) => `VG:N:${i}`),
        labels: Array.from({ length: count }, (_, i) => (i === 0 ? "Indra" : `Subject ${i}`)),
    };
    return { world, labels };
}

const DESKTOP = { width: 1440, height: 760 };
const PHONE = { width: 390, height: 620 };

function focusScene(neighbours: number, band: { width: number; height: number }) {
    const { world, labels } = makeWorld(neighbours);
    const neighbourhood = focusNeighbourhood(world, labels, 0, neighbours);
    const graph = buildFocusScene(world, neighbourhood, band);
    return { world, labels, neighbourhood, graph };
}

describe("the axis count is a parameter, not two copies of the loop", () => {
    it("reproduces the planar trajectory exactly when a 3D field is flat", () => {
        /* The parity that makes one module defensible. Same tuning, same bodies, same springs,
           with z pinned at zero: if the 2D and 3D paths disagree on x and y then the extraction
           has a per-axis assumption in it somewhere. */
        const build = (dims: 2 | 3) => {
            const field = createField({ dims, count: 12, edges: 11, tuning: tuningFor(2) });
            for (let i = 0; i < 12; i += 1) {
                const angle = (i / 12) * Math.PI * 2;
                field.pos[i * dims] = Math.cos(angle) * 140;
                field.pos[i * dims + 1] = Math.sin(angle) * 140;
                field.radius[i] = 8;
                field.mass[i] = 1 + i * 0.1;
                field.seed[i] = i * 7 + 1;
            }
            for (let e = 0; e < 11; e += 1) {
                field.edgeA[e] = 0;
                field.edgeB[e] = e + 1;
                field.edgeRest[e] = 120;
            }
            return field;
        };
        const flat = build(2);
        const deep = build(3);
        for (let step = 0; step < 200; step += 1) {
            stepField(flat);
            stepField(deep);
        }
        for (let i = 0; i < 12; i += 1) {
            expect(deep.pos[i * 3]).toBeCloseTo(flat.pos[i * 2], 4);
            expect(deep.pos[i * 3 + 1]).toBeCloseTo(flat.pos[i * 2 + 1], 4);
            expect(deep.pos[i * 3 + 2]).toBe(0);
        }
    });

    it("carries the 3D tuning the spatial binding needs", () => {
        expect(SPATIAL_TUNING.repulsion).toBeCloseTo(
            PLANAR_TUNING.repulsion * SPATIAL_REPULSION_FACTOR,
            6,
        );
        // A centre pull in 3D collapses the arrangement; the shell is what replaces it.
        expect(SPATIAL_TUNING.centrePull).toBe(0);
        expect(SPATIAL_TUNING.shell).not.toBeNull();
    });

    it("holds a 3D field on its shell instead of flattening it", () => {
        const shell = SPATIAL_TUNING.shell;
        expect(shell).not.toBeNull();
        if (!shell) return;
        const field = createField({ dims: 3, count: 40, edges: 0, tuning: tuningFor(3) });
        for (let i = 0; i < 40; i += 1) {
            /* Seeded on a spiral so the start is neither a ball nor a plane: a test that starts
               spherical cannot tell a shell constraint from having done nothing. */
            const t = (i + 0.5) / 40;
            const angle = i * 2.399;
            field.pos[i * 3] = Math.cos(angle) * 200 * t;
            field.pos[i * 3 + 1] = Math.sin(angle) * 200 * t;
            field.pos[i * 3 + 2] = (t - 0.5) * 60;
            field.radius[i] = 11;
            field.seed[i] = i + 1;
        }
        for (let step = 0; step < 1200; step += 1) stepField(field);

        let closest = Number.POSITIVE_INFINITY;
        let deepest = 0;
        for (let i = 0; i < 40; i += 1) {
            const radius = Math.hypot(
                field.pos[i * 3],
                field.pos[i * 3 + 1],
                field.pos[i * 3 + 2],
            );
            closest = Math.min(closest, radius);
            deepest = Math.max(deepest, Math.abs(field.pos[i * 3 + 2]));
        }
        expect(closest).toBeGreaterThan(shell.radius * 0.6);
        expect(deepest).toBeGreaterThan(40);
    });
});

describe("overlap relaxation terminates, and says so", () => {
    it("separates a stack of bodies and reports convergence", () => {
        const field = createField({ dims: 2, count: 24, edges: 0 });
        for (let i = 0; i < 24; i += 1) {
            field.pos[i * 2] = (i % 6) * 4;
            field.pos[i * 2 + 1] = Math.floor(i / 6) * 4;
            field.anchor[i * 2] = field.pos[i * 2];
            field.anchor[i * 2 + 1] = field.pos[i * 2 + 1];
            field.radius[i] = 10;
            field.seed[i] = i + 1;
        }
        const out = relaxOverlaps(field, { pad: 8 });
        expect(out.converged).toBe(true);
        /* A force field would settle wherever repulsion and the anchor balanced, which is a
           number nobody chose. A separation constraint terminates on the guarantee. */
        expect(minSeparation(field).gap).toBeGreaterThanOrEqual(8 - out.worst - 1e-6);
    });

    it("works in three axes too", () => {
        const field = createField({ dims: 3, count: 16, edges: 0, tuning: tuningFor(3) });
        for (let i = 0; i < 16; i += 1) {
            field.radius[i] = 9;
            field.seed[i] = i + 1;
            field.pos[i * 3] = i % 2;
            field.pos[i * 3 + 1] = i % 3;
            field.pos[i * 3 + 2] = i % 4;
            field.anchor[i * 3] = field.pos[i * 3];
            field.anchor[i * 3 + 1] = field.pos[i * 3 + 1];
            field.anchor[i * 3 + 2] = field.pos[i * 3 + 2];
        }
        expect(relaxOverlaps(field, { pad: 6 }).converged).toBe(true);
        expect(minSeparation(field).gap).toBeGreaterThan(5.9);
    });
});

describe("the focus layout keeps its separation in CSS pixels", () => {
    /*
     * The whole range, not the design case.
     *
     * 6 is the median subject in this artifact and 12 the 90th percentile, so those two are the
     * layout's real job; 40 is the desktop budget, at which curation engages on 1.10% of
     * connected nodes; 200 is `FOCUS_BUDGET_MAX`, where one spoke per neighbour is still
     * unconditional. 1 and 3 are in because a ring of one and a triangle are where a layout
     * tuned only for forty falls apart.
     */
    for (const neighbours of [1, 3, 6, 12, 40, 200]) {
        for (const [name, band] of [
            ["desktop", DESKTOP],
            ["phone", PHONE],
        ] as const) {
            it(`holds d >= max(${SEPARATION_MIN}, r_a + r_b + ${SEPARATION_PAD}) at ${neighbours} on ${name}`, () => {
                const { graph } = focusScene(neighbours, band);
                preroll(graph);
                const worst = worstSeparation(graph);
                expect(graph.nodes.length).toBe(neighbours + 1);
                if (graph.nodes.length < 2) return;
                expect(worst.slack).toBeGreaterThanOrEqual(-1e-6);
                expect(worst.distance).toBeGreaterThanOrEqual(graph.guarantee ?? 0);
            });
        }
    }

    it("draws an orb a finger can find, at every viewport", () => {
        for (const band of [DESKTOP, PHONE]) {
            const { graph } = focusScene(40, band);
            preroll(graph);
            for (const node of graph.nodes) {
                /* The number this replaces is 3.85 px, measured on the real artifact at every
                   viewport tried, because the radius was in graph units and `fit` was 0.33. */
                expect(markRadius(node, 1) * 2).toBeGreaterThanOrEqual(14);
            }
            const leaves = graph.nodes.filter((node) => node.ring === 1);
            expect(Math.max(...leaves.map((node) => node.radius))).toBeLessThanOrEqual(
                LEAF_ORB_RADIUS,
            );
        }
    });

    it("is authored at scale 1, so nothing squashes it", () => {
        const { graph } = focusScene(40, PHONE);
        expect(graph.authored).toBe(true);
        expect(graph.guarantee).toBe(2 * LEAF_ORB_RADIUS + SEPARATION_PAD);
    });
});

describe("the curated set is what is drawn, and the mesh is gone", () => {
    it("draws one line per shown neighbour and bounded context, not the ring-to-ring mesh", () => {
        const { graph, neighbourhood } = focusScene(60, DESKTOP);
        expect(graph.nodes.length).toBe(neighbourhood.shown.length + 1);
        expect(graph.edges.length).toBe(
            neighbourhood.spokes.length + neighbourhood.between.length,
        );
        expect(graph.edges.length).toBeLessThanOrEqual(FOCUS_LINE_CAP);
        /* Every shown neighbour has a line to the subject. A neighbour with no line is an
           unattached dot in a view whose whole claim is what the subject is attached to. */
        const spoked = new Set<number>();
        for (const edge of graph.edges) {
            if (edge.a === 0) spoked.add(edge.b);
            if (edge.b === 0) spoked.add(edge.a);
        }
        expect(spoked.size).toBe(neighbourhood.shown.length);
    });

    it("keeps the subject at the centre and everything else on a ring", () => {
        const { graph } = focusScene(12, DESKTOP);
        const root = graph.nodes[0];
        expect(root.ring).toBe(0);
        expect(Math.hypot(root.x, root.y)).toBeLessThan(1);
        expect(graph.nodes.filter((node) => node.ring === 1).length).toBe(12);
    });
});

describe("re-spacing gives room without widening the set", () => {
    it("moves the same neighbours further out and keeps the invariant", () => {
        const { graph } = focusScene(6, DESKTOP);
        preroll(graph);
        const before = graph.nodes.map((node) => node.id);
        const reach = () => Math.max(...graph.nodes.map((node) => Math.hypot(node.x, node.y)));
        const wasReach = reach();

        const spacing = respaceFocusScene(graph, DESKTOP);
        expect(spacing).toBeCloseTo(RESPACE_STEP, 6);
        preroll(graph);
        settleSlots(graph);
        preroll(graph);

        expect(graph.nodes.map((node) => node.id)).toEqual(before);
        expect(reach()).toBeGreaterThan(wasReach * 1.2);
        expect(worstSeparation(graph).slack).toBeGreaterThanOrEqual(-1e-6);
    });

    it("returns to the authored layout rather than saturating", () => {
        const { graph } = focusScene(6, DESKTOP);
        preroll(graph);
        let spacing = graph.spacing;
        let presses = 0;
        /* Every press has to change something, or the control is a button that stops working.
           The cycle is what makes that true without a disabled state to keep in step. */
        while (presses < 40) {
            const next = respaceFocusScene(graph, DESKTOP, { instant: true });
            expect(next).not.toBe(spacing);
            spacing = next;
            presses += 1;
            if (spacing === 1) break;
        }
        expect(spacing).toBe(1);
        expect(presses).toBeGreaterThan(1);
        settleSlots(graph);
        preroll(graph);
        expect(worstSeparation(graph).slack).toBeGreaterThanOrEqual(-1e-6);
    });

    it("does nothing to a world scene, which has no subject to space around", () => {
        const world = makeWorld(4).world;
        const graph = buildWorldScene(world, DESKTOP);
        expect(respaceFocusScene(graph, DESKTOP)).toBe(1);
    });
});

describe("the hit target is in screen pixels", () => {
    it("offers a finger a larger target than a mouse, at the same scale", () => {
        const { graph } = focusScene(12, DESKTOP);
        preroll(graph);
        const leaf = graph.nodes[4];
        const reach = (pointer: "mouse" | "touch", away: number) =>
            pickPlanar(graph, leaf.x + away, leaf.y, { scale: 1, pointer });
        expect(reach("touch", PICK_TARGET.touch - 2)).toBe(4);
        expect(reach("mouse", PICK_TARGET.touch - 2)).toBeNull();
        expect(reach("mouse", PICK_TARGET.mouse - 2)).toBe(4);
    });

    it("does not shrink the target when the diagram is zoomed out", () => {
        /* The defect this replaces: the mark was drawn at `radius * clamp(scale, 0.7, 1.6)` and
           picked at `radius + 6` in graph units, so at the measured fit scale of 0.16-0.34 an
           11-23 px mark had a 2-5 px target. Both now come from the same px floor. */
        const { graph } = focusScene(12, DESKTOP);
        preroll(graph);
        const leaf = graph.nodes[4];
        const away = (PICK_TARGET.mouse - 2) / 0.4;
        expect(pickPlanar(graph, leaf.x + away, leaf.y, { scale: 0.4, pointer: "mouse" })).toBe(4);
    });
});

describe("the world scene", () => {
    it("draws nothing, and says nothing, where the artifact carries no constellations", () => {
        const graph = buildWorldScene(makeWorld(8).world, DESKTOP);
        expect(graph.nodes).toHaveLength(0);
        expect(graph.edges).toHaveLength(0);
    });

    it("leaves a mixed constellation unlabelled rather than naming it a passage cluster", () => {
        const base = {
            id: 7,
            community: 7,
            size: 100,
            veda: null,
            group: null,
            central: [3],
            bridges: [],
            connectedShare: null,
            centre: [0, 0, 0] as [number, number, number],
            radius: 10,
        };
        expect(constellationCaption({ ...base, name: "Rigvedic · Indra" })).toBe("Rigvedic · Indra");
        expect(constellationCaption({ ...base, name: "passage cluster" })).toBeNull();
        expect(constellationCaption({ ...base, name: "Atharvavedic · passage cluster" })).toBeNull();
        expect(constellationCaption({ ...base, name: null })).toBeNull();
    });

    it("separates every disc, and stands each one for a real subject", () => {
        const world = makeWorld(8).world;
        const centres: Array<[number, number, number]> = [
            [0, 0, 0],
            [4, 0, 200],
            [-4, 3, -200],
            [120, -90, 40],
        ];
        world.manifest.constellations = centres.map((centre, i) => ({
            id: i,
            community: i,
            name: i === 0 ? "Rigvedic · Indra" : "passage cluster",
            size: 400 + i * 900,
            veda: null,
            group: null,
            central: [i + 1],
            bridges: [],
            connectedShare: null,
            centre,
            radius: 40,
        }));
        const graph = buildWorldScene(world, DESKTOP);
        expect(graph.nodes).toHaveLength(4);
        /* The straight projection puts constellations 1 and 2 eight units apart on screen and
           four hundred apart in the world, which is why the discs are relaxed rather than
           projected. */
        expect(minSeparation(graph.field).gap).toBeGreaterThan(7.9);
        expect(graph.nodes.map((node) => node.id)).toEqual([1, 2, 3, 4]);
        expect(graph.nodes.map((node) => node.labelled)).toEqual([true, false, false, false]);
        // No fill by dominant group: ARB-6's condition on these discs shipping at all.
        expect(graph.nodes.every((node) => node.group === -1)).toBe(true);
    });
});

describe("sleep", () => {
    it("reports rest against the field's own threshold, not a caller's", () => {
        const field = createField({ dims: 2, count: 4, edges: 0 });
        expect(fieldAtRest(field, PLANAR_TUNING.sleepEnergy - 1e-6)).toBe(true);
        expect(fieldAtRest(field, PLANAR_TUNING.sleepEnergy)).toBe(false);
    });

    it("settles a slot-anchored focus scene well inside the preroll", () => {
        /* The preroll used to be a fixed sixty steps because the layout arrived as loose rings.
           Slot anchors converge faster, and the figure matters: it is what a reader waits for
           before the first paint of a selection. */
        const { graph } = focusScene(40, DESKTOP);
        expect(preroll(graph)).toBeLessThan(120);
    });
});
