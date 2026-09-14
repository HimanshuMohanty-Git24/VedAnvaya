import { describe, expect, it } from "vitest";
import { composeWorld } from "@/lib/world/artifact";
import {
    FOCUS_COMPACT_WIDTH,
} from "@/lib/world/focus";
import {
    FOCUS_LABEL_CAP,
    FOCUS_LABEL_CAP_COMPACT,
    GUTTER,
    LABEL_COMPACT_WIDTH,
    LABEL_TIER,
    LabelLayout,
    NAME_QUADRANTS,
    PATH_LABEL_CAP,
    REENTRY_COOLDOWN_MS,
    TOTAL_LABEL_CAP,
    TOTAL_LABEL_CAP_COMPACT,
    TOUCH_MIN,
    WORLD_LABEL_CAP,
    countOverlaps,
    describeRelations,
    edgeLabelBudget,
    nameKey,
    nodeNameAnchors,
    pathLabelBudget,
    pickEdgeLabels,
    spokeEdges,
    totalLabelCap,
    type LabelAnchor,
    type LabelRect,
} from "@/lib/world/edge-labels";
import { describePredicate, type PredicateTable } from "@/lib/world/predicates";

/**
 * The invariants behind "what is this line" and "what is that dot".
 *
 * Three separate claims are protected here, and they fail in different ways.
 *
 * The first is about *which* connections get named. A hub in this corpus has thousands of edges
 * and almost all of them are the same kind, so the obvious rank - by the neighbour's importance -
 * produces a screen full of one phrase repeated. The tests below assert the opposite behaviour:
 * every distinct kind is named once before any kind is named twice, and rarity is judged against
 * the corpus rather than against whatever subset the renderer happened to pass in.
 *
 * The second is that the words themselves are never invented here. The phrases come from a table
 * exported from the API's own curated source, and a predicate the table has not heard of must be
 * named without being explained.
 *
 * The third is new to this phase and is the one that matters most, because its failure mode is not
 * a crash: **no two labels of either class may overlap**. Two previous escapes let a label through
 * in collision, and both were asserted here as desired behaviour. They are gone, and what replaces
 * them is a single priority order in which a name can lose to a phrase - which the old two-pass
 * design could not express - plus the hysteresis that stops the trade happening at frame rate.
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

/**
 * A hub whose predicate histogram is steep in the corpus and *flat* in any curated subset.
 *
 * Twenty of the common kind and two each of two rarer kinds. A per-predicate cap of two - which is
 * what curation does - hands the label pass two of each, so the three group sizes tie at two and
 * the only thing left to order them is the tie-break. This is the fixture for the defect the
 * rarity fix exists to close.
 */
function tiedSubsetWorld() {
    // Deliberately alphabetical-first for the *common* kind, so a `localeCompare` tie-break puts
    // the wrong one in front and the test can tell the difference.
    const edgeTypes = ["AAA_COMMON", "ZZZ_RARE", "ZZY_RARE"];
    const counts = [20, 2, 2];
    const edges = counts.reduce((a, b) => a + b, 0);
    const nodes = edges + 1;

    const edgePairs = new Uint32Array(edges * 2);
    const edgeType = new Uint8Array(edges);
    const nodeDegree = new Uint16Array(nodes);
    nodeDegree[0] = edges;

    let e = 0;
    counts.forEach((count, type) => {
        for (let i = 0; i < count; i += 1) {
            edgePairs[e * 2] = 0;
            edgePairs[e * 2 + 1] = e + 1;
            edgeType[e] = type;
            nodeDegree[e + 1] = 10;
            e += 1;
        }
    });

    return composeWorld({
        groups: ["deity"],
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
        /* The whole point. Ranked by the neighbour's degree, the first picks would all be
           HAS_RISHI and a reader would learn one fact ten times. */
        const picks = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP);
        const firstFour = picks.slice(0, 4).map((pick) => pick.predicate);
        expect(new Set(firstFour).size).toBe(4);
    });

    it("keeps the rare kinds even though their neighbours are the least connected", () => {
        const picks = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP);
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
        const picks = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP);
        const firstRound = picks.slice(0, 4);
        const later = picks.slice(4);
        const lowestOfFirst = Math.min(...firstRound.map((pick) => pick.priority));
        const highestOfLater = Math.max(...later.map((pick) => pick.priority));
        expect(lowestOfFirst).toBeGreaterThan(highestOfLater);
    });

    it("only considers the connections it is told are drawn", () => {
        /* A subject's edges are not all lines on the canvas, so naming one outside the drawn set
           would put a phrase beside a line that is not there. */
        const picks = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP, [0, 1, 2]);
        expect(picks.map((pick) => pick.edge).sort()).toEqual([0, 1, 2]);
    });

    it("is stable: the same subject gives the same answer twice", () => {
        const once = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP).map((p) => p.edge);
        const twice = pickEdgeLabels(world, TABLE, 0, FOCUS_LABEL_CAP).map((p) => p.edge);
        expect(once).toEqual(twice);
    });

    it("says nothing about a subject that is not in the world", () => {
        expect(pickEdgeLabels(world, TABLE, -1)).toHaveLength(0);
        expect(pickEdgeLabels(world, TABLE, 9_999)).toHaveLength(0);
    });
});

describe("rarity is judged against the corpus, not against the subset", () => {
    const world = tiedSubsetWorld();
    /* What curation hands over: a per-predicate cap of two. The three group sizes now tie, which
       is precisely the state in which the old `picks.length` sort fell through to an alphabetical
       tie-break and silently decided which rare relationship led. */
    const curated = [0, 1, 20, 21, 22, 23];

    it("leads with the kind that is rare in the corpus even when the subset sizes tie", () => {
        const picks = pickEdgeLabels(world, TABLE, 0, 3, curated);
        expect(picks[0].predicate).not.toBe("AAA_COMMON");
        // Both rare kinds lead, in name order between themselves; the common one comes last.
        expect(picks.map((pick) => pick.predicate)).toEqual([
            "ZZY_RARE",
            "ZZZ_RARE",
            "AAA_COMMON",
        ]);
    });

    it("still orders by the subset when the subset is the whole neighbourhood", () => {
        const picks = pickEdgeLabels(world, TABLE, 0, 3);
        expect(picks.map((pick) => pick.predicate)).toEqual([
            "ZZY_RARE",
            "ZZZ_RARE",
            "AAA_COMMON",
        ]);
    });

    it("does not put a predicate that is absent from the incident set in front", () => {
        /* A caller may pass edges that are not in `edgesOf` at all - the planar view passes its
           own projection's list - and a corpus count of zero must not outrank a genuinely unique
           kind. The subset size is the floor. */
        const picks = pickEdgeLabels(world, TABLE, 0, 3, [20, 21, 22, 23, 0, 1]);
        expect(picks).toHaveLength(3);
        expect(picks[0].predicate).not.toBe("AAA_COMMON");
    });

    it("reads focus.ts's spokes without importing its types", () => {
        const spokes = [{ edge: 7 }, { edge: 3 }, { edge: 1 }];
        expect([...spokeEdges(spokes)]).toEqual([7, 3, 1]);
    });
});

/* ------------------------------------------------------------------ the caps */

describe("the caps", () => {
    it("shows fewer on a narrow canvas than on a wide one, per mode", () => {
        expect(edgeLabelBudget(390)).toBe(FOCUS_LABEL_CAP_COMPACT);
        expect(edgeLabelBudget(1440)).toBe(FOCUS_LABEL_CAP);
        expect(edgeLabelBudget(1440, "WORLD")).toBe(WORLD_LABEL_CAP);
        expect(edgeLabelBudget(1440, "PATH")).toBe(PATH_LABEL_CAP);
        expect(totalLabelCap(390)).toBe(TOTAL_LABEL_CAP_COMPACT);
        expect(totalLabelCap(1440)).toBe(TOTAL_LABEL_CAP);
    });

    it("names every step of a short route and caps a long one", () => {
        expect(pathLabelBudget(1440, 3)).toBe(3);
        expect(pathLabelBudget(1440, 40)).toBe(PATH_LABEL_CAP);
        expect(pathLabelBudget(390, 40)).toBeLessThan(PATH_LABEL_CAP);
    });

    it("becomes compact at the same width as everything else in the product", () => {
        /* It was 720 here and 768 everywhere else, so a phone in landscape got the desktop cap
           inside the mobile layout. Asserted against `focus.ts` rather than against a literal, so
           the two cannot drift apart again without a failure here. */
        expect(LABEL_COMPACT_WIDTH).toBe(FOCUS_COMPACT_WIDTH);
        expect(edgeLabelBudget(FOCUS_COMPACT_WIDTH - 1)).toBe(FOCUS_LABEL_CAP_COMPACT);
        expect(edgeLabelBudget(FOCUS_COMPACT_WIDTH)).toBe(FOCUS_LABEL_CAP);
    });
});

/* ---------------------------------------------------------------- the words */

describe("the words come from the exported table, never from here", () => {
    it("uses the curated phrase rather than the predicate name", () => {
        const picks = pickEdgeLabels(lopsidedWorld(), TABLE, 0, 4);
        const rishi = picks.find((pick) => pick.predicate === "HAS_RISHI");
        expect(rishi?.text).toBe("is ascribed to the seer");
        // Specifically not the generic humanisation, which disagrees with the curated wording
        // on most of the vocabulary.
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

/* ----------------------------------------------- recorded against shown */

describe("the panel's counts come from the canvas's own selection pass", () => {
    const world = lopsidedWorld();

    it("states the denominator, the drawn set and the named set as three numbers", () => {
        const summary = describeRelations({
            world,
            labels: null,
            table: TABLE,
            node: 0,
            drawn: [0, 1, 2, 40, 41, 42],
            limit: 3,
        });
        expect(summary.recorded).toBe(43);
        expect(summary.kinds).toBe(4);
        expect(summary.drawn).toBe(6);
        expect(summary.named).toBe(3);
    });

    it("lists every drawn relationship, not only the named ones", () => {
        /* A list of only the named ones would tell the reader that three relationships exist. */
        const summary = describeRelations({
            world,
            labels: null,
            table: TABLE,
            node: 0,
            drawn: [0, 1, 2, 40, 41, 42],
            limit: 3,
        });
        expect(summary.rows).toHaveLength(6);
        expect(summary.rows.filter((row) => row.named)).toHaveLength(3);
    });

    it("marks a relationship the table does not explain as unexplained", () => {
        const summary = describeRelations({ world, labels: null, table: null, node: 0, limit: 4 });
        expect(summary.rows.every((row) => row.explained)).toBe(false);
        expect(summary.rows.every((row) => row.phrase.length > 0)).toBe(true);
    });

    it("agrees with pickEdgeLabels exactly, because it is the same call", () => {
        const drawn = [0, 1, 2, 40, 41, 42];
        const summary = describeRelations({
            world,
            labels: null,
            table: TABLE,
            node: 0,
            drawn,
            limit: 4,
        });
        const picks = pickEdgeLabels(world, TABLE, 0, 4, drawn);
        expect(summary.rows.filter((row) => row.named).map((row) => row.edge).sort()).toEqual(
            picks.map((pick) => pick.edge).sort(),
        );
    });

    it("says nothing about a subject that is not in the world", () => {
        const summary = describeRelations({ world, labels: null, table: TABLE, node: -1 });
        expect(summary).toEqual({ recorded: 0, kinds: 0, drawn: 0, named: 0, rows: [] });
    });
});

/* --------------------------------------------------------------- placement */

describe("placing the words, both classes, one pass", () => {
    const viewport = { width: 1440, height: 900 };
    // A fixed size per character, so the expected geometry is arithmetic rather than a guess.
    const measure = (text: string) => ({ width: text.length * 6, height: 16 });

    const relation = (
        key: number,
        x: number,
        y: number,
        weight: number,
        extra: Partial<LabelAnchor> = {},
    ): LabelAnchor => ({
        key,
        kind: "relation",
        tier: LABEL_TIER.RELATION,
        weight,
        text: `label ${key}`,
        candidates: [{ x, y }],
        usable: true,
        ...extra,
    });

    const name = (
        node: number,
        x: number,
        y: number,
        tier: number,
        extra: Partial<LabelAnchor> = {},
    ): LabelAnchor => ({
        key: nameKey(node),
        kind: "name",
        tier,
        weight: 1,
        text: `subject ${node}`,
        candidates: [{ x, y }],
        usable: true,
        ...extra,
    });

    const place = (
        anchors: LabelAnchor[],
        options: Partial<{
            reserved: LabelRect[];
            total: number;
            relationBudget: number;
            now: number;
        }> = {},
    ) => new LabelLayout().place({ anchors, viewport, measure, ...options });

    it("never places two labels on top of each other", () => {
        const anchors = [0, 1, 2, 3].map((i) => relation(i, 700, 450, 1 - i * 0.1));
        const frame = place(anchors);
        expect(frame.placed).toHaveLength(1);
        expect(frame.overlaps).toBe(0);
    });

    it("collides on the 44 px touch pad, not on the ink", () => {
        /*
         * The defect class this has to prevent, stated as arithmetic. Two chips 25 px apart look
         * comfortably separated - their 16 px ink boxes do not touch - but their pads, each padded
         * out to the 44 px touch minimum, overlap by 19 px, and the one later in the document wins
         * the tap. It has shipped twice in this product already.
         */
        const frame = place([relation(0, 700, 400, 1), relation(1, 700, 425, 0.9)]);
        expect(frame.placed).toHaveLength(1);
        for (const label of frame.placed) {
            expect(label.hitHeight).toBeGreaterThanOrEqual(TOUCH_MIN);
            expect(label.hitWidth).toBeGreaterThanOrEqual(label.width + GUTTER * 2);
        }
    });

    it("keeps a legibility gutter even where the boxes are wider than the touch minimum", () => {
        const frame = place([relation(0, 300, 400, 1)]);
        const label = frame.placed[0];
        expect(label.hitWidth - label.width).toBeCloseTo(GUTTER * 2, 5);
    });

    it("slides a label along its own edge rather than dropping it", () => {
        /* Three candidates on one line. The second label cannot take the first position and must
           take the next one *on its own edge* - moving it sideways would put it on a different
           line and make it describe the wrong relationship. */
        const frame = place([
            relation(0, 700, 450, 1),
            relation(1, 700, 450, 0.9, {
                candidates: [
                    { x: 700, y: 450 },
                    { x: 700, y: 650 },
                ],
            }),
        ]);
        expect(frame.placed).toHaveLength(2);
        const ys = frame.placed.map((label) => label.y).sort((a, b) => a - b);
        expect(ys[1] - ys[0]).toBeGreaterThan(100);
    });

    it("drops the lower weight label when neither can move", () => {
        const frame = place([relation(0, 700, 450, 0.2), relation(1, 700, 450, 0.9)]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].key).toBe(1);
        expect(frame.dropped).toBe(1);
    });

    it("ignores a label the renderer says is unusable", () => {
        expect(place([relation(0, 700, 450, 1, { usable: false })]).placed).toHaveLength(0);
    });

    it("skips a candidate position that has left the canvas but keeps the label", () => {
        const frame = place([
            relation(0, 700, 450, 1, {
                candidates: [
                    { x: 700, y: 450, usable: false },
                    { x: 300, y: 200, usable: true },
                ],
            }),
        ]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].candidate).toBe(1);
    });

    it("keeps every label inside the canvas", () => {
        const frame = place([relation(0, -500, -500, 1), relation(1, 5_000, 5_000, 0.9)]);
        for (const label of frame.placed) {
            expect(label.x).toBeGreaterThanOrEqual(0);
            expect(label.y).toBeGreaterThanOrEqual(0);
            expect(label.x + label.width).toBeLessThanOrEqual(viewport.width);
            expect(label.y + label.height).toBeLessThanOrEqual(viewport.height);
        }
    });

    it("keeps the touch pad for the labels that are targets, and off the ones that are not", () => {
        /*
         * The 44 px floor is a property of being clickable, not of being a label. A name is
         * `pointer-events: none`, so there is nothing to hit and nothing to keep clear of - and
         * applying the floor to both classes was measured against the real scene as the cause of
         * two defects at once: one phrase placed against a cap of ten on desktop, and two labels
         * of any kind on a phone. See `TOUCH_MIN`.
         */
        const frame = place([relation(0, 300, 200, 1), name(4, 900, 600, LABEL_TIER.NEIGHBOUR_NAME)]);
        const phrase = frame.placed.find((label) => label.kind === "relation");
        const subject = frame.placed.find((label) => label.kind === "name");
        expect(phrase?.hitHeight).toBeGreaterThanOrEqual(TOUCH_MIN);
        expect(subject?.hitHeight).toBeLessThan(TOUCH_MIN);
        expect(subject!.hitHeight - subject!.height).toBeCloseTo(GUTTER * 2, 5);
    });

    it("reserves the phrases' share of the total rather than letting the names take it", () => {
        /*
         * Two budgets, not one blended - ARB-8's correction, applied to the label classes. Names
         * outrank plain relations, so under one shared total they place first and take all of it:
         * measured on Indra at 1440x900, nine names and one phrase against a phrase cap of ten.
         */
        const anchors: LabelAnchor[] = [];
        for (let i = 0; i < 10; i += 1) anchors.push(relation(i, 120 + i * 130, 780, 0.9 - i * 0.01));
        for (let i = 0; i < 20; i += 1) {
            anchors.push(name(i, 120 + (i % 10) * 130, 120 + Math.floor(i / 10) * 90, LABEL_TIER.NEIGHBOUR_NAME));
        }
        const frame = place(anchors, { total: 14, relationBudget: 6 });
        const phrases = frame.placed.filter((label) => label.kind === "relation").length;
        const names = frame.placed.filter((label) => label.kind === "name").length;
        expect(phrases).toBe(6);
        expect(names).toBe(8);
    });

    it("gives the slack to the other class rather than leaving slots empty", () => {
        /* A subject with two relationships must not hold four empty phrase slots while names go
           unplaced. */
        const anchors: LabelAnchor[] = [relation(0, 200, 780, 0.9), relation(1, 600, 780, 0.8)];
        for (let i = 0; i < 12; i += 1) {
            anchors.push(name(i, 120 + (i % 6) * 200, 120 + Math.floor(i / 6) * 90, LABEL_TIER.NEIGHBOUR_NAME));
        }
        const frame = place(anchors, { total: 10, relationBudget: 6 });
        expect(frame.placed.filter((label) => label.kind === "relation")).toHaveLength(2);
        expect(frame.placed.filter((label) => label.kind === "name")).toHaveLength(8);
    });

    it("honours the total cap across both classes together", () => {
        const anchors: LabelAnchor[] = [];
        for (let i = 0; i < 10; i += 1) anchors.push(relation(i, 100 + i * 200, 100, 0.9));
        for (let i = 0; i < 10; i += 1) {
            anchors.push(name(i, 100 + i * 120, 500, LABEL_TIER.NEIGHBOUR_NAME));
        }
        expect(place(anchors, { total: 6 }).placed.length).toBeLessThanOrEqual(6);
    });
});

/* ------------------------------------------------------------- the tier order */

describe("one priority order, so a name can lose to a phrase", () => {
    const viewport = { width: 1440, height: 900 };
    const measure = (text: string) => ({ width: text.length * 6, height: 16 });
    const at = (key: number, kind: "relation" | "name", tier: number): LabelAnchor => ({
        key,
        kind,
        tier,
        weight: 0.5,
        text: kind === "name" ? "Agni" : "co-occurs with",
        candidates: [{ x: 700, y: 450 }],
        usable: true,
    });
    const place = (anchors: LabelAnchor[]) =>
        new LabelLayout().place({ anchors, viewport, measure });

    it("gives the contested position to a hovered relation over a neighbour's name", () => {
        /* The inversion the unified pass exists for. Under two passes the name was always already
           on the canvas and the phrase could only ever give way; measured, that cut the visible
           phrases on a real hub from five to two. */
        const frame = place([
            at(nameKey(3), "name", LABEL_TIER.NEIGHBOUR_NAME),
            at(11, "relation", LABEL_TIER.HOVERED_RELATION),
        ]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].kind).toBe("relation");
    });

    it("gives it to a neighbour's name over an off-pointer relation", () => {
        const frame = place([
            at(nameKey(3), "name", LABEL_TIER.NEIGHBOUR_NAME),
            at(11, "relation", LABEL_TIER.RELATION),
        ]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].kind).toBe("name");
    });

    it("never loses the name of the subject the reader has chosen", () => {
        /* Tier 100 is above every relationship tier, including the reserved ones, so the chosen
           subject's own name survives an open inspector and a traced route at the same spot. */
        const frame = place([
            at(nameKey(3), "name", LABEL_TIER.SELECTED_NAME),
            at(11, "relation", LABEL_TIER.HOVERED_RELATION),
            at(12, "relation", LABEL_TIER.INSPECTED_RELATION),
            at(-1, "relation", LABEL_TIER.PATH_STEP),
        ]);
        expect(frame.placed.filter((label) => label.kind === "name")).toHaveLength(1);
    });

    it("keeps a hovered name over every relation the reader has not asked about", () => {
        /* The weaker of the two claims, and the exact one the tier table makes. A hovered name at
           80 outranks a hovered relation at 70 and an off-pointer one at 40, but it yields to the
           two reserved tiers above it - the relationship whose explanation is open, and the steps
           of a route. Both of those are things the reader asked for out loud, and the name is not
           lost so much as deferred: it is still the subject under the pointer, which the hover
           readout in the corner also states. */
        const frame = place([
            at(nameKey(3), "name", LABEL_TIER.HOVERED_NAME),
            at(11, "relation", LABEL_TIER.HOVERED_RELATION),
        ]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].kind).toBe("name");

        const deferred = place([
            at(nameKey(3), "name", LABEL_TIER.HOVERED_NAME),
            at(12, "relation", LABEL_TIER.INSPECTED_RELATION),
        ]);
        expect(deferred.placed).toHaveLength(1);
        expect(deferred.placed[0].kind).toBe("relation");
    });

    it("places a reserved tier even when nothing is clear, and says it was clamped", () => {
        /* Tiers at or above PATH_STEP are the answer to a question the reader just asked out
           loud. Dropping one is the interface declining to answer, so it is clamped instead. */
        const tiny = { width: 60, height: 30 };
        const frame = new LabelLayout().place({
            anchors: [
                at(nameKey(3), "name", LABEL_TIER.SELECTED_NAME),
                at(-1, "relation", LABEL_TIER.PATH_STEP),
            ],
            viewport: tiny,
            measure,
        });
        expect(frame.placed).toHaveLength(2);
        expect(frame.placed.every((label) => label.clamped)).toBe(true);
    });

    it("drops the world hub names first", () => {
        const frame = place([
            at(nameKey(1), "name", LABEL_TIER.WORLD_HUB_NAME),
            at(nameKey(2), "name", LABEL_TIER.NEIGHBOUR_NAME),
        ]);
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].tier).toBe(LABEL_TIER.NEIGHBOUR_NAME);
    });
});

/* ------------------------------------------------------------- the hysteresis */

describe("hysteresis, so a label near the threshold does not toggle at frame rate", () => {
    const viewport = { width: 1440, height: 900 };
    const measure = (text: string) => ({ width: text.length * 6, height: 16 });
    const anchor = (key: number, x: number, weight: number): LabelAnchor => ({
        key,
        kind: "relation",
        tier: LABEL_TIER.RELATION,
        weight,
        text: `label ${key}`,
        candidates: [{ x, y: 450 }],
        usable: true,
    });

    it("makes a newcomer clear a larger zone than an incumbent has to", () => {
        /* Asymmetric padding. The threshold to get on screen sits strictly above the threshold to
           stay there, which is what stops two labels whose boxes graze trading one slot forever. */
        const layout = new LabelLayout();
        const first = layout.place({ anchors: [anchor(0, 700, 0.5)], viewport, measure, now: 1_000 });
        expect(first.placed).toHaveLength(1);

        // Far enough apart that an incumbent's plain gutter clears, but not the newcomer's 1.5x.
        const grazing = first.placed[0].hitWidth * 1.1;
        const second = layout.place({
            anchors: [anchor(0, 700, 0.5), anchor(1, 700 + grazing, 0.9)],
            viewport,
            measure,
            now: 1_050,
        });
        expect(second.placed.map((label) => label.key)).toEqual([0]);
    });

    it("does not let a dropped label come straight back", () => {
        /* Been et al.'s one-active-interval rule, in the cooldown-gated form documented on the
           layout: a label may return, but not within REENTRY_COOLDOWN_MS of being dropped. */
        const layout = new LabelLayout();
        layout.place({ anchors: [anchor(0, 700, 0.1)], viewport, measure, now: 1_000 });
        /* Beaten at the same spot by a rival whose weight clears the incumbency bonus. Incumbency
           is +0.5 and weights are normalised to 0..1, so an incumbent at 0.1 can be taken and an
           incumbent at 0.5 cannot - which is the whole point of the bonus. */
        layout.place({
            anchors: [anchor(0, 700, 0.1), anchor(1, 700, 0.9)],
            viewport,
            measure,
            now: 1_050,
        });
        // The rival is gone, but the cooldown is still running.
        const during = layout.place({
            anchors: [anchor(0, 700, 0.1)],
            viewport,
            measure,
            now: 1_100,
        });
        expect(during.placed).toHaveLength(0);
        const after = layout.place({
            anchors: [anchor(0, 700, 0.1)],
            viewport,
            measure,
            now: 1_100 + REENTRY_COOLDOWN_MS + 1,
        });
        expect(after.placed).toHaveLength(1);
    });

    it("forgets a label's cooldown once it stops being offered at all", () => {
        /* Presence intervals. Leaving a subject and coming back must not find the old cooldowns
           still running, or the second visit shows fewer labels than the first. */
        const layout = new LabelLayout();
        layout.place({ anchors: [anchor(0, 700, 0.1)], viewport, measure, now: 1_000 });
        layout.place({
            anchors: [anchor(0, 700, 0.1), anchor(1, 700, 0.9)],
            viewport,
            measure,
            now: 1_050,
        });
        // Nothing offered: the interval ends.
        layout.place({ anchors: [], viewport, measure, now: 1_060 });
        const back = layout.place({
            anchors: [anchor(0, 700, 0.1)],
            viewport,
            measure,
            now: 1_070,
        });
        expect(back.placed).toHaveLength(1);
    });

    it("forgets its incumbents when the subject changes", () => {
        const layout = new LabelLayout();
        layout.place({ anchors: [anchor(0, 700, 0.5)], viewport, measure, now: 1_000 });
        layout.reset();
        const after = layout.place({
            anchors: [anchor(1, 700, 0.9), anchor(0, 700, 0.5)],
            viewport,
            measure,
            now: 1_100,
        });
        expect(after.placed).toHaveLength(1);
        expect(after.placed[0].key).toBe(1);
    });

    it("never lets incumbency promote a label past a tier", () => {
        /* Incumbency is +0.5 of weight, and the smallest tier gap is 10. An incumbent name at
           tier 50 must still lose the position to a hovered relation at 70. */
        const layout = new LabelLayout();
        const held: LabelAnchor = {
            key: nameKey(4),
            kind: "name",
            tier: LABEL_TIER.NEIGHBOUR_NAME,
            weight: 0.99,
            text: "Soma",
            candidates: [{ x: 700, y: 450 }],
            usable: true,
        };
        const rival: LabelAnchor = {
            key: 9,
            kind: "relation",
            tier: LABEL_TIER.HOVERED_RELATION,
            weight: 0,
            text: "label 9",
            candidates: [{ x: 700, y: 450 }],
            usable: true,
        };
        layout.place({ anchors: [held], viewport, measure, now: 1_000 });
        const contested = layout.place({
            anchors: [held, rival],
            viewport,
            measure,
            now: 1_050,
        });
        expect(contested.placed).toHaveLength(1);
        expect(contested.placed[0].kind).toBe("relation");
    });

    it("latches a name's quadrant so it never swaps sides mid-view", () => {
        const layout = new LabelLayout();
        const quadrants = (x: number, y: number) =>
            NAME_QUADRANTS.map((quadrant) => ({
                x: x + quadrant.dx,
                y: y + quadrant.dy,
                anchorX: quadrant.anchorX,
                anchorY: quadrant.anchorY,
            }));
        const subject: LabelAnchor = {
            key: nameKey(7),
            kind: "name",
            tier: LABEL_TIER.NEIGHBOUR_NAME,
            weight: 0.9,
            text: "Agni",
            candidates: quadrants(700, 450),
            usable: true,
        };
        const first = layout.place({ anchors: [subject], viewport, measure, now: 1_000 });
        const chosen = first.placed[0].candidate;

        /* A rival arrives beside the latched quadrant. Without the latch, the name would take a
           clear quadrant on the other side of its own orb and appear to jump across it. */
        const rival: LabelAnchor = {
            key: 55,
            kind: "relation",
            tier: LABEL_TIER.RELATION,
            weight: 0.1,
            text: "x",
            candidates: [{ x: 900, y: 700 }],
            usable: true,
        };
        const second = layout.place({
            anchors: [subject, rival],
            viewport,
            measure,
            now: 1_050,
        });
        const again = second.placed.find((label) => label.key === nameKey(7));
        expect(again?.candidate).toBe(chosen);
    });
});

/* ------------------------------------------------------------- the annealing */

describe("the annealing finish", () => {
    const viewport = { width: 1440, height: 900 };
    const measure = (text: string) => ({ width: text.length * 6, height: 16 });

    /** A crowded scene: twenty phrases radiating from one point, three positions each. */
    const crowd = (): LabelAnchor[] =>
        Array.from({ length: 20 }, (_, i) => {
            const angle = (i / 20) * Math.PI * 2;
            return {
                key: i,
                kind: "relation" as const,
                tier: LABEL_TIER.RELATION,
                weight: 1 - i / 20,
                text: "is ascribed to the seer",
                candidates: [0.44, 0.62, 0.8].map((t) => ({
                    x: 720 + Math.cos(angle) * 380 * t,
                    y: 450 + Math.sin(angle) * 380 * t,
                })),
                usable: true,
            };
        });

    it("leaves no overlapping pair behind", () => {
        const frame = new LabelLayout().place({ anchors: crowd(), viewport, measure });
        expect(frame.overlaps).toBe(0);
        expect(countOverlaps(frame.placed)).toBe(0);
    });

    it("runs, and reports what it did", () => {
        const frame = new LabelLayout().place({ anchors: crowd(), viewport, measure });
        expect(frame.anneal.stages).toBeGreaterThan(0);
        expect(frame.anneal.moves).toBeGreaterThan(0);
        expect(frame.anneal.stages).toBeLessThanOrEqual(50);
    });

    it("is deterministic: the same scene anneals to the same answer twice", () => {
        /* Not a nicety. A layout seeded from a clock moves every label on an unrelated re-render,
           and makes the end-to-end collision gate a coin toss. */
        const a = new LabelLayout().place({ anchors: crowd(), viewport, measure, now: 1_000 });
        const b = new LabelLayout().place({ anchors: crowd(), viewport, measure, now: 5_000 });
        expect(a.placed.map((label) => [label.key, label.candidate])).toEqual(
            b.placed.map((label) => [label.key, label.candidate]),
        );
    });

    it("cannot end worse than the greedy answer it was given", () => {
        /* Best-so-far retention. Plain Metropolis accepts a late uphill move and never undoes it;
           without this the finish could hand back a state with overlaps in it. */
        const frame = new LabelLayout().place({ anchors: crowd(), viewport, measure });
        expect(frame.placed.length).toBeGreaterThan(0);
        expect(frame.overlaps).toBe(0);
    });
});

/* --------------------------------------------------- names against obstacles */

describe("names already inked on the canvas are obstacles, not candidates", () => {
    const viewport = { width: 1440, height: 900 };
    const measure = (text: string) => ({ width: text.length * 6, height: 16 });

    it("places a phrase clear of a name the caller has already drawn", () => {
        /* The planar view inks its names during its own draw pass, before this runs, so they are
           facts rather than candidates. A phrase moves along its own line to avoid one. */
        const inked: LabelRect = { x: 660, y: 430, width: 140, height: 20 };
        const frame = new LabelLayout().place({
            anchors: [
                {
                    key: 0,
                    kind: "relation",
                    tier: LABEL_TIER.RELATION,
                    weight: 1,
                    text: "co-occurs with",
                    candidates: [
                        { x: 720, y: 440 },
                        { x: 300, y: 200 },
                    ],
                    usable: true,
                },
            ],
            viewport,
            measure,
            reserved: [inked],
        });
        expect(frame.placed).toHaveLength(1);
        expect(frame.placed[0].candidate).toBe(1);
    });

    it("drops the phrase rather than printing it on top of an inked name", () => {
        /* The `tolerated` escape that used to accept exactly this is gone. Two overlapping pieces
           of text are both unreadable, and in the planar view the name cannot be asked to move. */
        const inked: LabelRect = { x: 660, y: 430, width: 140, height: 20 };
        const frame = new LabelLayout().place({
            anchors: [
                {
                    key: 0,
                    kind: "relation",
                    tier: LABEL_TIER.RELATION,
                    weight: 1,
                    text: "co-occurs with",
                    candidates: [{ x: 720, y: 440 }],
                    usable: true,
                },
            ],
            viewport,
            measure,
            reserved: [inked],
        });
        expect(frame.placed).toHaveLength(0);
    });
});

/* ------------------------------------------------------------ naming subjects */

describe("choosing which subjects to name", () => {
    const world = lopsidedWorld();
    const labels = {
        ids: Array.from({ length: 44 }, (_, i) => `VG:${i}`),
        labels: Array.from({ length: 44 }, (_, i) => `Subject ${i}`),
    };
    const positionOf = (node: number) => ({ x: 100 + node * 7, y: 100 + node * 3 });

    it("puts the chosen subject's name in a reserved tier and its neighbours below it", () => {
        const layer = nodeNameAnchors({
            world,
            labels,
            positionOf,
            selected: 0,
            hovered: null,
            neighbours: [1, 2, 3],
            viewport: { width: 1440, height: 900 },
        });
        expect(layer.mode).toBe("FOCUS");
        expect(layer.anchors[0].tier).toBe(LABEL_TIER.SELECTED_NAME);
        expect(layer.anchors.slice(1, 4).every((a) => a.tier === LABEL_TIER.NEIGHBOUR_NAME)).toBe(
            true,
        );
    });

    it("offers four quadrants per name, so a name can move without leaving its orb", () => {
        const layer = nodeNameAnchors({
            world,
            labels,
            positionOf,
            selected: 5,
            hovered: null,
            neighbours: [],
            viewport: { width: 1440, height: 900 },
        });
        expect(layer.anchors[0].candidates).toHaveLength(NAME_QUADRANTS.length);
    });

    it("marks a phrase as hover-driven only when nothing is selected", () => {
        const base = { world, labels, positionOf, viewport: { width: 1440, height: 900 } };
        expect(nodeNameAnchors({ ...base, selected: null, hovered: 2 }).relationTier).toBe(
            LABEL_TIER.HOVERED_RELATION,
        );
        expect(nodeNameAnchors({ ...base, selected: 1, hovered: 2 }).relationTier).toBe(
            LABEL_TIER.RELATION,
        );
        expect(nodeNameAnchors({ ...base, selected: null, hovered: null }).mode).toBe("WORLD");
    });

    it("does not offer a node behind the camera", () => {
        const layer = nodeNameAnchors({
            world,
            labels,
            positionOf: () => null,
            selected: 0,
            hovered: null,
            neighbours: [1],
            viewport: { width: 1440, height: 900 },
        });
        expect(layer.anchors.every((anchor) => !anchor.usable)).toBe(true);
    });

    it("bounds the offered set well below the artifact's hub index", () => {
        /* The annealer's cost is linear in the number offered and the tail cannot win a slot, so
           offering every hub costs measurements and moves for nothing. */
        const layer = nodeNameAnchors({
            world,
            labels,
            positionOf,
            selected: null,
            hovered: null,
            neighbours: Array.from({ length: 300 }, (_, i) => i + 1),
            viewport: { width: 390, height: 844 },
        });
        expect(layer.anchors.length).toBeLessThanOrEqual(totalLabelCap(390) * 2);
    });
});
