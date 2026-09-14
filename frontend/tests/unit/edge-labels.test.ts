import { describe, expect, it } from "vitest";
import { composeWorld } from "@/lib/world/artifact";
import {
    EdgeLabelLayout,
    edgeLabelBudget,
    MAX_EDGE_LABELS,
    MAX_EDGE_LABELS_COMPACT,
    pickEdgeLabels,
    type LabelAnchor,
    type PlacedLabel,
} from "@/lib/world/edge-labels";
import { describePredicate, type PredicateTable } from "@/lib/world/predicates";

/**
 * The invariants behind "what is this line".
 *
 * Two separate claims are protected here, and they fail in different ways.
 *
 * The first is about *which* connections get named. A hub in this corpus has thousands of edges
 * and almost all of them are the same kind, so the obvious rank - by the neighbour's importance -
 * produces a screen full of one phrase repeated. The tests below assert the opposite behaviour:
 * every distinct kind is named once before any kind is named twice.
 *
 * The second is about the words themselves never being invented here. The phrases come from a
 * table exported from the API's own curated source, and a predicate the table has not heard of
 * must be named without being explained.
 */

/* ------------------------------------------------------------------ fixtures */

/**
 * A subject with a very lopsided neighbourhood, which is what the corpus actually looks like.
 *
 * Node 0 is the hub. Forty edges of one common kind, then one each of three rarer kinds - the
 * shape that defeats ranking by degree.
 */
function lopsidedWorld() {
    const edgeTypes = ["HAS_RISHI", "EXACT_PARALLEL_OF", "CO_OCCURS_WITH", "HAS_CHANDAS"];
    const common = 40;
    const rare = 3;
    const nodes = 1 + common + rare;
    const edges = common + rare;

    const edgePairs = new Uint32Array(edges * 2);
    const edgeType = new Uint8Array(edges);
    const nodeDegree = new Uint16Array(nodes);
    nodeDegree[0] = edges;

    for (let i = 0; i < edges; i += 1) {
        edgePairs[i * 2] = 0;
        edgePairs[i * 2 + 1] = i + 1;
        // The rare kinds are last, and are attached to the *least* connected neighbours, so any
        // rule that ranks by the far node's degree will drop them.
        edgeType[i] = i < common ? 0 : i - common + 1;
        nodeDegree[i + 1] = i < common ? 500 - i : 1;
    }

    return composeWorld({
        groups: ["deity", "passage"],
        types: [],
        edgeTypes,
        positions: new Float32Array(nodes * 3),
        nodeGroup: new Uint8Array(nodes),
        nodeDegree,
        edgePairs,
        edgeType,
    });
}

const TABLE: PredicateTable = {
    version: 1,
    generated: "",
    source: "test",
    predicates: {
        HAS_RISHI: {
            phrase: "is ascribed to the seer",
            asserts: "a",
            limit: "b",
            direction: "UNDECLARED",
            basis: "CURATED",
        },
        EXACT_PARALLEL_OF: {
            phrase: "is an exact parallel of",
            asserts: "a",
            limit: "b",
            direction: "SYMMETRIC",
            basis: "CURATED",
        },
        CO_OCCURS_WITH: {
            phrase: "co-occurs with",
            asserts: "a",
            limit: "b",
            direction: "UNDECLARED",
            basis: "CURATED",
        },
        HAS_CHANDAS: {
            phrase: "is in the metre",
            asserts: "a",
            limit: "b",
            direction: "UNDECLARED",
            basis: "CURATED",
        },
    },
};

/* -------------------------------------------------------------- what is named */

describe("choosing which connections to name", () => {
    const world = lopsidedWorld();

    it("names every kind before it repeats any kind", () => {
        /* The whole point. Ranked by the neighbour's degree, the first sixteen picks would all
           be HAS_RISHI and a reader would learn one fact sixteen times. */
        const picks = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS);
        const firstFour = picks.slice(0, 4).map((pick) => pick.predicate);
        expect(new Set(firstFour).size).toBe(4);
    });

    it("keeps the rare kinds even though their neighbours are the least connected", () => {
        const picks = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS);
        const kinds = new Set(picks.map((pick) => pick.predicate));
        for (const rare of ["EXACT_PARALLEL_OF", "CO_OCCURS_WITH", "HAS_CHANDAS"]) {
            expect(kinds, `${rare} was dropped`).toContain(rare);
        }
    });

    it("never exceeds the budget it is given", () => {
        expect(pickEdgeLabels(world, TABLE, 0, 8)).toHaveLength(8);
        expect(pickEdgeLabels(world, TABLE, 0, 1)).toHaveLength(1);
        expect(pickEdgeLabels(world, TABLE, 0, 0)).toHaveLength(0);
    });

    it("ranks the first example of each kind above the second example of any kind", () => {
        const picks = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS);
        const firstRound = picks.slice(0, 4);
        const later = picks.slice(4);
        const lowestOfFirst = Math.min(...firstRound.map((pick) => pick.priority));
        const highestOfLater = Math.max(...later.map((pick) => pick.priority));
        expect(lowestOfFirst).toBeGreaterThan(highestOfLater);
    });

    it("only considers the connections it is told are drawn", () => {
        /* The spatial overlay truncates past its capacity, so naming an edge outside that
           prefix would put a phrase beside a line that is not on screen. */
        const picks = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS, [0, 1, 2]);
        expect(picks.map((pick) => pick.edge).sort()).toEqual([0, 1, 2]);
    });

    it("is stable: the same subject gives the same answer twice", () => {
        const once = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS).map((p) => p.edge);
        const twice = pickEdgeLabels(world, TABLE, 0, MAX_EDGE_LABELS).map((p) => p.edge);
        expect(once).toEqual(twice);
    });

    it("says nothing about a subject that is not in the world", () => {
        expect(pickEdgeLabels(world, TABLE, -1)).toHaveLength(0);
        expect(pickEdgeLabels(world, TABLE, 9_999)).toHaveLength(0);
    });

    it("shows fewer on a narrow canvas than on a wide one", () => {
        expect(edgeLabelBudget(390)).toBe(MAX_EDGE_LABELS_COMPACT);
        expect(edgeLabelBudget(1440)).toBe(MAX_EDGE_LABELS);
    });
});

/* ---------------------------------------------------------------- the words */

describe("the words come from the exported table, never from here", () => {
    it("uses the curated phrase rather than the predicate name", () => {
        const picks = pickEdgeLabels(lopsidedWorld(), TABLE, 0, 4);
        const rishi = picks.find((pick) => pick.predicate === "HAS_RISHI");
        expect(rishi?.text).toBe("is ascribed to the seer");
        // Specifically not the generic humanisation, which disagrees with the curated wording
        // on 44 of 57 predicates.
        expect(rishi?.text).not.toBe("has rishi");
    });

    it("names an unknown predicate without explaining it", () => {
        const unknown = describePredicate(TABLE, "SOMETHING_NEW");
        expect(unknown?.phrase).toBe("something new");
        /* Empty rather than a generated sentence: an invented explanation on a graph edge is
           fabricated scholarship, and the interface checks this to decide whether to offer one. */
        expect(unknown?.asserts).toBe("");
        expect(unknown?.limit).toBe("");
        expect(unknown?.basis).toBe("DERIVED_FROM_NAME");
    });

    it("falls back to readable words when the table has not arrived yet", () => {
        const picks = pickEdgeLabels(lopsidedWorld(), null, 0, 4);
        expect(picks.every((pick) => pick.text.length > 0)).toBe(true);
        expect(picks.every((pick) => !pick.text.includes("_"))).toBe(true);
    });
});

/* --------------------------------------------------------------- placement */

describe("placing the words", () => {
    const viewport = { width: 800, height: 600 };
    // A fixed width per character, so the expected geometry is arithmetic rather than a guess.
    const measure = (text: string) => text.length * 6;

    const anchor = (
        key: number,
        x: number,
        y: number,
        priority: number,
        extra: Partial<LabelAnchor> = {},
    ): LabelAnchor => ({
        key,
        candidates: [{ x, y }],
        text: `label ${key}`,
        priority,
        usable: true,
        ...extra,
    });

    it("never places two labels on top of each other", () => {
        const layout = new EdgeLabelLayout();
        const anchors = [0, 1, 2, 3].map((i) => anchor(i, 400, 300, 1 - i * 0.1));
        const placed = layout.place(anchors, viewport, measure, 16);
        expect(placed).toHaveLength(1);
    });

    it("slides a label along its own edge rather than dropping it", () => {
        /* Three candidates on one line. The second label cannot take the first position and must
           take the next one *on its own edge* - moving it sideways would put it on a different
           line and make it describe the wrong relationship. */
        const layout = new EdgeLabelLayout();
        const placed = layout.place(
            [
                anchor(0, 400, 300, 1),
                {
                    key: 1,
                    candidates: [
                        { x: 400, y: 300 },
                        { x: 400, y: 500 },
                    ],
                    text: "label 1",
                    priority: 0.9,
                    usable: true,
                },
            ],
            viewport,
            measure,
            16,
        );
        expect(placed).toHaveLength(2);
        expect(placed[1].y).toBeGreaterThan(placed[0].y + 100);
    });

    it("drops the lower priority label when neither can move", () => {
        const layout = new EdgeLabelLayout();
        const placed = layout.place(
            [anchor(0, 400, 300, 0.2), anchor(1, 400, 300, 0.9)],
            viewport,
            measure,
            16,
        );
        expect(placed).toHaveLength(1);
        expect(placed[0].key).toBe(1);
    });

    it("ignores a label the renderer says is unusable", () => {
        const layout = new EdgeLabelLayout();
        const placed = layout.place(
            [anchor(0, 400, 300, 1, { usable: false })],
            viewport,
            measure,
            16,
        );
        expect(placed).toHaveLength(0);
    });

    it("keeps every label inside the canvas", () => {
        const layout = new EdgeLabelLayout();
        const placed = layout.place(
            [anchor(0, -500, -500, 1), anchor(1, 5_000, 5_000, 0.9)],
            viewport,
            measure,
            16,
        );
        for (const label of placed) {
            expect(label.x).toBeGreaterThanOrEqual(0);
            expect(label.y).toBeGreaterThanOrEqual(0);
            expect(label.x + label.width).toBeLessThanOrEqual(viewport.width);
            expect(label.y + label.height).toBeLessThanOrEqual(viewport.height);
        }
    });

    it("holds a label it has just shown, rather than blinking it out", () => {
        /* The hysteresis. A label whose position becomes contested a frame later stays for its
           dwell, because a phrase that flickers draws the eye to the flicker. */
        const layout = new EdgeLabelLayout();
        const first = layout.place([anchor(0, 100, 100, 0.5)], viewport, measure, 16, [], 1_000);
        expect(first).toHaveLength(1);

        const second = layout.place(
            [anchor(1, 100, 100, 0.9), anchor(0, 100, 100, 0.5)],
            viewport,
            measure,
            16,
            [],
            1_100,
        );
        expect(second.map((label) => label.key).sort()).toEqual([0, 1]);
    });

    it("forgets its incumbents when the subject changes", () => {
        const layout = new EdgeLabelLayout();
        layout.place([anchor(0, 100, 100, 0.5)], viewport, measure, 16, [], 1_000);
        layout.reset();
        const after = layout.place(
            [anchor(1, 100, 100, 0.9), anchor(0, 100, 100, 0.5)],
            viewport,
            measure,
            16,
            [],
            1_100,
        );
        expect(after).toHaveLength(1);
        expect(after[0].key).toBe(1);
    });

    it("prefers a position clear of the subject names, but never loses a label to one", () => {
        /* Names are a soft obstacle. Treated as a veto they cut the visible phrases on a real
           hub from five to two, because the names cluster exactly where the edges do. */
        const layout = new EdgeLabelLayout();
        const name: PlacedLabel = { key: -1, text: "", x: 380, y: 290, width: 120, height: 20 };

        const avoided = layout.place(
            [
                {
                    key: 0,
                    candidates: [
                        { x: 400, y: 300 },
                        { x: 200, y: 100 },
                    ],
                    text: "label 0",
                    priority: 1,
                    usable: true,
                },
            ],
            viewport,
            measure,
            16,
            [name],
        );
        expect(avoided).toHaveLength(1);
        expect(avoided[0].x).toBeLessThan(300);

        const cornered = new EdgeLabelLayout().place(
            [anchor(0, 400, 300, 1)],
            viewport,
            measure,
            16,
            [name],
        );
        expect(cornered, "a name must not silence a relationship").toHaveLength(1);
    });
});
