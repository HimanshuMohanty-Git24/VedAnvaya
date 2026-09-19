import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
    edgesOf,
    loadWorld,
    loadWorldLabels,
    neighboursOf,
    otherEnd,
    type World,
    type WorldLabels,
} from "@/lib/world/artifact";
import {
    ACCOUNTED_FAMILIES,
    BETWEEN_PER_NODE,
    FOCUS_BUDGET,
    FOCUS_BUDGET_COMPACT,
    FOCUS_BUDGET_CRAMPED,
    FOCUS_BUDGET_MAX,
    FOCUS_EXPAND_STEP,
    FOCUS_LINE_CAP,
    GROUP_CEILING,
    PREDICATE_FAMILY,
    RELATIONSHIP_FAMILIES,
    SPOKE_CAP,
    betweenCap,
    betweenEdges,
    expandFocusBudget,
    familyOfPredicate,
    focusBudget,
    focusBudgetForBand,
    focusGroupRows,
    focusNeighbourhood,
    focusRingSeats,
    selectFocus,
    type FocusNeighbour,
} from "@/lib/world/focus";

/**
 * FOCUS curation, against the real artifact.
 *
 * A fixture cannot test this. The whole design is a response to measured shapes in *this*
 * graph - that Indra has 7,347 connections to 5,544 subjects of which 4,702 are passages, that
 * the median node has six neighbours, that five of the twelve relationship families are absent
 * on a deity - and a hand-built five-node world would pass every assertion below while telling
 * us nothing about whether a reader can read the scene. So these load `public/world`.
 *
 * The cost is that a rebuilt artifact can fail these tests. That is the intended behaviour:
 * the budgets are derived from the corpus's degree distribution, and a corpus whose
 * distribution has moved needs the budgets re-derived rather than the assertions relaxed.
 */

/* -------------------------------------------------------------- the real artifact - */

/**
 * The packed world, read off disk through the shipped loader.
 *
 * `loadWorld` fetches, so fetch is stubbed to serve the files - rather than reimplementing the
 * CSR construction here, which is the one part of the decode that has already been wrong once
 * and is what `world-artifact.test.ts` exists to pin. A second copy of it in this file would
 * be a second thing to get right.
 *
 * `globalThis.fetch` is swapped directly and restored in a `finally` instead of going through
 * `vi.stubGlobal`, so it cannot leak into a later test file's expectations.
 */
let loaded: Promise<{ world: World; labels: WorldLabels }> | null = null;

function realWorld(): Promise<{ world: World; labels: WorldLabels }> {
    if (loaded) return loaded;
    loaded = (async () => {
        const dir = join(process.cwd(), "public", "world");
        const read = (name: string) => readFileSync(join(dir, name));
        const binary = read("world.bin");
        // A fresh ArrayBuffer, because a Buffer's byteOffset is rarely zero and the section
        // offsets in the manifest are absolute.
        const buffer = binary.buffer.slice(
            binary.byteOffset,
            binary.byteOffset + binary.byteLength,
        ) as ArrayBuffer;
        const json = (name: string) => JSON.parse(read(name).toString("utf8")) as unknown;

        const previous = globalThis.fetch;
        globalThis.fetch = (async (url: RequestInfo | URL) => {
            /* The loader versions these addresses with the export hash, so the stub matches the
               filename rather than the whole URL. */
            const path = String(url).split("?")[0];
            if (path.endsWith("world.bin")) {
                return { ok: true, arrayBuffer: async () => buffer } as unknown as Response;
            }
            if (path.endsWith("world.labels.json")) {
                return { ok: true, json: async () => json("world.labels.json") } as unknown as Response;
            }
            if (path.endsWith("world.json")) {
                return { ok: true, json: async () => json("world.json") } as unknown as Response;
            }
            return { ok: false } as unknown as Response;
        }) as typeof globalThis.fetch;
        try {
            const world = await loadWorld();
            const labels = await loadWorldLabels();
            return { world, labels };
        } finally {
            globalThis.fetch = previous;
        }
    })();
    return loaded;
}

/** By id, never by index: indices move between builds and these ids are frozen. */
function nodeById(labels: WorldLabels, id: string): number {
    const index = labels.ids.indexOf(id);
    expect(index, `${id} is not in the artifact`).toBeGreaterThanOrEqual(0);
    return index;
}

const INDRA = "VG:DEVATA:INDRAH";
/* The worst case for coverage, and not the same node as the busiest one. */
const AGNI = "VG:DEVATA:AGNIH";

/* ------------------------------------------------------------------ the families - */

describe("the relationship families", () => {
    it("assigns every predicate in both vocabularies to exactly one family", () => {
        /*
         * Totality over BOTH files, which are different lengths: `world.json#edgeTypes` is the
         * 48 predicates the artifact can draw, and `world.predicates.json` declares 60 - the
         * twelve extra are curated but carry no rows today.
         *
         * Asserted here rather than trusted because the failure is silent. A predicate this
         * table has not heard of falls into OTHER, which is correct behaviour and invisible: the
         * coverage round still shows it, the sidebar still counts it, and nobody learns that a
         * newly-ontologised relationship is being filed under "Other" next to the unknowns.
         */
        const dir = join(process.cwd(), "public", "world");
        const manifest = JSON.parse(
            readFileSync(join(dir, "world.json"), "utf8"),
        ) as { edgeTypes: string[] };
        const vocabulary = JSON.parse(
            readFileSync(join(dir, "world.predicates.json"), "utf8"),
        ) as { predicates: Record<string, unknown> };

        const declared = [...new Set([...manifest.edgeTypes, ...Object.keys(vocabulary.predicates)])];
        expect(declared.length).toBeGreaterThanOrEqual(60);

        const unmapped = declared.filter((predicate) => !PREDICATE_FAMILY.has(predicate));
        expect(unmapped).toEqual([]);
        for (const predicate of declared) {
            expect(familyOfPredicate(predicate)).not.toBe("OTHER");
        }
    });

    it("counts an unmapped predicate rather than dropping it", () => {
        /* OTHER is a bucket, not a discard. A lookup that returned null or undefined would
           invite callers to skip the edge, and the sidebar's family totals would then stop
           summing to the subject's degree with nothing on screen to say why. */
        expect(familyOfPredicate("SOMETHING_THE_ONTOLOGY_HAS_NOT_INVENTED")).toBe("OTHER");
        expect(familyOfPredicate("")).toBe("OTHER");
        expect(RELATIONSHIP_FAMILIES).toContain("OTHER");
        expect(RELATIONSHIP_FAMILIES).toHaveLength(13);
        expect(ACCOUNTED_FAMILIES).toHaveLength(12);
        expect(ACCOUNTED_FAMILIES).not.toContain("OTHER");
    });
});

/* -------------------------------------------------------------------- the budgets - */

describe("the budgets", () => {
    it("computes the mobile budget from the visible band, not the viewport", async () => {
        /*
         * The numbers are the measured mobile stage on a 390x844 phone: the graph chrome takes
         * 225.6px before anything is drawn, leaving a 434.4px canvas band under a collapsed
         * sheet and 183.1px under a half-raised one. A budget chosen from the 844px viewport
         * height draws sixteen orbs into space for eleven.
         */
        expect(focusBudgetForBand(390, 434.4)).toBe(FOCUS_BUDGET_COMPACT);
        expect(focusBudgetForBand(390, 183.1)).toBe(FOCUS_BUDGET_CRAMPED);
        /* The ring arithmetic the drop is derived from, and no hardcoded threshold at all.
           The band at which the compact budget first becomes seatable is found by walking the
           arithmetic, so it moves when the budget is re-derived. The literal 250px that used
           to stand here went stale the moment the coverage floor moved off 16, and a literal
           asserts nothing about derivation anyway - the inverse below is what does. */
        expect(focusRingSeats(183.1)).toBe(11);
        let compactBand = 1;
        while (focusRingSeats(compactBand) < FOCUS_BUDGET_COMPACT) compactBand += 1;
        expect(focusRingSeats(compactBand)).toBeGreaterThanOrEqual(FOCUS_BUDGET_COMPACT);
        expect(focusRingSeats(compactBand - 1)).toBeLessThan(FOCUS_BUDGET_COMPACT);
        // At that band the coverage floor binds; one pixel below it, geometry binds instead.
        expect(focusBudgetForBand(1440, compactBand)).toBe(FOCUS_BUDGET_COMPACT);
        expect(focusBudgetForBand(1440, compactBand - 1)).toBeLessThan(FOCUS_BUDGET_COMPACT);

        // No phone is assumed: a short band on a wide window is still a short band.
        expect(focusBudgetForBand(1440, 900)).toBe(FOCUS_BUDGET);
        expect(focusBudgetForBand(1440, 300)).toBeLessThan(FOCUS_BUDGET);
        expect(focusBudgetForBand(1440, 300)).toBeGreaterThanOrEqual(FOCUS_BUDGET_CRAMPED);

        // The width-only convenience delegates, and cannot see the sheet.
        expect(focusBudget(390)).toBe(FOCUS_BUDGET_COMPACT);
        expect(focusBudget(1440)).toBe(FOCUS_BUDGET);
        expect(focusBudget(767)).toBe(FOCUS_BUDGET_COMPACT);
        expect(focusBudget(768)).toBe(FOCUS_BUDGET);
    });

    it("expands in steps and stops", () => {
        expect(expandFocusBudget(FOCUS_BUDGET)).toBe(FOCUS_BUDGET + FOCUS_EXPAND_STEP);
        expect(expandFocusBudget(FOCUS_BUDGET_MAX)).toBe(FOCUS_BUDGET_MAX);
        expect(expandFocusBudget(FOCUS_BUDGET_MAX - 1)).toBe(FOCUS_BUDGET_MAX);
    });

    it("shows every relationship kind and group the worst case has at the compact budget", async () => {
        /*
         * 22 is the measured coverage floor: over the 471 nodes the curation engages on, the
         * smallest budget still showing every predicate, family and node group is 3 at the
         * median, 14 at the 99th percentile, and 22 at the single worst case, which is Agni.
         * If this fails, 22 has stopped being the floor and the constant is no longer derived.
         *
         * Both deities are asserted because they bind on different axes and only one of them
         * is the floor. Indra and Agni each lose HAS_DEVATA at 16, so predicate coverage on
         * its own would put the budget at 17; Agni additionally has `thing` and
         * `unresolved-deity` neighbours that no scene below 22 reaches. Asserting Indra alone
         * is what let the budget sit at 17 while Agni was quietly missing two whole groups.
         */
        const { world, labels } = await realWorld();
        for (const id of [INDRA, AGNI]) {
            const root = nodeById(labels, id);
            const everyPredicate = new Set<string>();
            for (const edge of edgesOf(world, root)) {
                everyPredicate.add(world.manifest.edgeTypes[world.edgeType[edge]]);
            }
            const everyGroup = new Set<string>();
            for (const neighbour of neighboursOf(world, root)) {
                everyGroup.add(world.manifest.groups[world.nodeGroup[neighbour]]);
            }
            const selection = selectFocus(world, labels, root, FOCUS_BUDGET_COMPACT);
            const covered = new Set(selection.shown.flatMap((n) => n.predicates));
            const coveredGroups = new Set(selection.shown.map((n) => n.group));
            for (const predicate of everyPredicate) expect(covered, id).toContain(predicate);
            for (const group of everyGroup) expect(coveredGroups, id).toContain(group);
            expect(everyPredicate.size).toBeGreaterThanOrEqual(13);
        }
        /* Derived, not merely sufficient. One budget lower and the worst case loses a group;
           without this the constant could drift upward unnoticed and still pass. */
        const agni = nodeById(labels, AGNI);
        const groups = new Set<string>();
        for (const neighbour of neighboursOf(world, agni)) {
            groups.add(world.manifest.groups[world.nodeGroup[neighbour]]);
        }
        const tighter = selectFocus(world, labels, agni, FOCUS_BUDGET_COMPACT - 1);
        const reached = new Set(tighter.shown.map((neighbour) => neighbour.group));
        expect([...groups].some((group) => !reached.has(group))).toBe(true);
    });
});

/* ------------------------------------------------------------------ the selection - */

describe("choosing what to draw", () => {
    it("shows a low-degree node whole, and pads nothing", async () => {
        /*
         * The typical case, and it is overwhelming: the median node in this artifact has six
         * distinct neighbours and only 377 of 34,373 connected nodes have more than forty. The
         * curation must be invisible here - no truncation, no filler, and every neighbour
         * drawn - because otherwise a layout tuned for forty orbs is being applied to 99% of
         * the corpus.
         */
        const { world, labels } = await realWorld();
        let root = -1;
        for (let i = 0; i < world.nodeDegree.length; i += 1) {
            const distinct = neighboursOf(world, i).length;
            if (distinct > 0 && distinct < 10) {
                root = i;
                break;
            }
        }
        expect(root).toBeGreaterThanOrEqual(0);
        const distinct = neighboursOf(world, root).length;
        const selection = selectFocus(world, labels, root, FOCUS_BUDGET);
        expect(selection.truncated).toBe(false);
        expect(selection.total).toBe(distinct);
        expect(selection.shown).toHaveLength(distinct);
        expect(selection.shown.length).toBeLessThan(FOCUS_BUDGET);
        for (const neighbour of selection.shown) expect(neighbour.reason).toBe("ALL");
        // Every real neighbour is present; nothing invented to reach the budget.
        const drawn = new Set(selection.shown.map((neighbour) => neighbour.node));
        for (const neighbour of neighboursOf(world, root)) expect(drawn).toContain(neighbour);
    });

    it("covers every node group and reaches other constellations", async () => {
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const everyGroup = new Set<string>();
        for (const neighbour of neighboursOf(world, root)) {
            everyGroup.add(world.manifest.groups[world.nodeGroup[neighbour]]);
        }
        const selection = selectFocus(world, labels, root, FOCUS_BUDGET);
        const covered = new Set(selection.shown.map((neighbour) => neighbour.group));
        for (const group of everyGroup) expect(covered).toContain(group);

        /* A pure-salience forty reaches 12 of the 33 constellations Indra touches; the
           reserve takes that to 17. Asserting "more than one" is the floor - a scene that
           reaches only the subject's own region shows a star, not a position in the corpus. */
        const regions = new Set(selection.shown.map((neighbour) => neighbour.region));
        expect(regions.size).toBeGreaterThan(5);
        expect(selection.shown.some((neighbour) => neighbour.bridge)).toBe(true);
    });

    it("never draws a subject twice, nor two orbs with the same words on them", async () => {
        /*
         * Two neighbours can genuinely share a label - the artifact has duplicate display
         * strings across different ids - and two orbs reading "agniḥ" side by side is read as
         * a rendering fault, not as two records. De-duplication runs in every round, so a
         * later round cannot reintroduce what an earlier one rejected.
         */
        const { world, labels } = await realWorld();
        for (const id of [INDRA, "VG:DEVATA:AGNIH", "VG:CONCEPT:YAJNA"]) {
            const index = labels.ids.indexOf(id);
            if (index < 0) continue;
            const selection = selectFocus(world, labels, index, FOCUS_BUDGET);
            const nodes = selection.shown.map((neighbour) => neighbour.node);
            expect(new Set(nodes).size).toBe(nodes.length);
            const shownLabels = selection.shown
                .map((neighbour) => neighbour.label)
                .filter((label) => label !== "");
            expect(new Set(shownLabels).size).toBe(shownLabels.length);
        }
    });

    it("holds no node group above its ceiling, and never fills with derived metrics", async () => {
        /*
         * Indra's neighbours are 4,702 passages and 796 evidence records against 38 deities.
         * Without the ceiling the fill rounds hand the scene to whichever of those is largest;
         * with it, no group exceeds 30% of the budget. DerivedMetric nodes carry prior 0 and are
         * never filled - their labels embed a raw graph id - but MEASURES is a real relationship
         * kind, so coverage still shows one, and it must be the coverage round that did it.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const selection = selectFocus(world, labels, root, FOCUS_BUDGET);
        const counts = new Map<string, number>();
        for (const neighbour of selection.shown) {
            counts.set(neighbour.group, (counts.get(neighbour.group) ?? 0) + 1);
        }
        const ceiling = Math.floor(FOCUS_BUDGET * GROUP_CEILING);
        for (const [group, count] of counts) {
            expect(count, `${group} holds ${count} of ${FOCUS_BUDGET}`).toBeLessThanOrEqual(ceiling);
        }
        const derived = selection.shown.filter((neighbour) => neighbour.group === "derived");
        expect(derived.length).toBeGreaterThan(0);
        for (const neighbour of derived) {
            expect(["PREDICATE", "CATEGORY", "CONSTELLATION", "PINNED"]).toContain(neighbour.reason);
        }
    });

    /*
     * ------------------------------------------------------------------------------------
     * The scene a reader gets when they click a deity.
     *
     * Reported after the completeness campaign: "clicking Indra yields approximately one
     * useful connection where the older product used to expose many". Measured, the
     * neighbourhood was never one node - it was forty, of which twenty-one were verses and
     * evidence records and six were other deities. That is a faithful picture of the degree
     * distribution and a poor answer to "what is Indra connected to", and it got worse
     * rather than better when the public-identity repair restored 35,131 semantic-assertion
     * nodes to the export and handed the fill round 820 new candidates on Indra alone.
     *
     * These pin the shape of the repair rather than its numbers: subjects outnumber
     * apparatus, the apparatus keeps its tighter ceilings, and the sparse case still fills.
     * ------------------------------------------------------------------------------------
     */

    /** Groups that are Vedic subject matter, as opposed to apparatus around it. */
    const SUBJECT_GROUPS = new Set([
        "deity",
        "person",
        "idea",
        "rite",
        "thing",
        "wording",
        "unresolved-deity",
    ]);

    const MAJOR_DEITIES = [
        "VG:DEVATA:INDRAH",
        "VG:DEVATA:VARUNAH",
        "VG:DEVATA:AGNIH",
        "VG:DEVATA:SOMAH",
        "VG:DEVATA:MARUTAH",
    ];

    for (const id of MAJOR_DEITIES) {
        it(`${id} is drawn as a neighbourhood of subjects, not of verses`, async () => {
            const { world, labels } = await realWorld();
            const selection = selectFocus(
                world,
                labels,
                nodeById(labels, id),
                FOCUS_BUDGET,
            );
            const counts = new Map<string, number>();
            for (const neighbour of selection.shown) {
                counts.set(neighbour.group, (counts.get(neighbour.group) ?? 0) + 1);
            }
            const subjects = [...counts.entries()]
                .filter(([group]) => SUBJECT_GROUPS.has(group))
                .reduce((total, [, count]) => total + count, 0);

            const shape = [...counts.entries()].map(([g, c]) => `${g}:${c}`).join(" ");
            expect(subjects, `${id} drew ${shape}`).toBeGreaterThan(selection.shown.length / 2);

            /*
             * Against the general ceiling, not the tight one.
             *
             * `groupCeiling("passage")` is 0.15 and governs the *fill* round; the rank
             * round that follows it deliberately relaxes to GROUP_CEILING once every
             * subject group is at its own cap, because leaving seats empty beside four
             * thousand available verses is not a better scene. Asserting the tight figure
             * here would pin an internal round rather than what a reader sees, and it
             * fails on Varuna, who has 12 deities, 12 ideas and nothing else to give the
             * remaining seats to.
             */
            const general = Math.floor(FOCUS_BUDGET * GROUP_CEILING);
            expect(counts.get("passage") ?? 0, shape).toBeLessThanOrEqual(general);
            expect(counts.get("record") ?? 0, shape).toBeLessThanOrEqual(general);

            /* More than one *kind* of subject, which is the assertion a count survives: a
               scene of forty deities would pass the line above and still be a star. */
            const subjectKinds = [...counts.keys()].filter((group) =>
                SUBJECT_GROUPS.has(group),
            );
            expect(subjectKinds.length, shape).toBeGreaterThan(1);

            /* And more than one kind of relationship, for the same reason. */
            const predicates = new Set(
                selection.shown.flatMap((neighbour) => neighbour.predicates),
            );
            expect(predicates.size, `${id} drew predicates ${[...predicates]}`).toBeGreaterThan(1);
        });
    }

    it("still fills the scene for a subject whose neighbours are all of one kind", async () => {
        /*
         * Every one of the 729 seers is attached to passages and to nothing else, and so are
         * the metres. A ceiling meant to protect diversity has nothing to protect there, and
         * an early version of this repair drew such a subject twelve neighbours out of a
         * possible forty while reporting the other 824 as hidden.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, "VG:RISHI:MAITRAVARUNIRVASISTHAH");
        const selection = selectFocus(world, labels, root, FOCUS_BUDGET);
        expect(selection.total).toBeGreaterThan(FOCUS_BUDGET);
        expect(selection.shown.length).toBe(FOCUS_BUDGET);
    });

    it("only ever adds when the reader asks for more", async () => {
        /*
         * Measured before the PINNED round existed: the 40-set was not a subset of the 48-set,
         * because the weighted fill re-apportioned and dropped a subject the reader was looking
         * at. "Show twenty more" that takes something away is not an expansion.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        let pinned: number[] = [];
        for (const budget of [16, 36, 56, 76]) {
            const selection = selectFocus(world, labels, root, budget, { pinned });
            const nodes = selection.shown.map((neighbour) => neighbour.node);
            expect(selection.shown).toHaveLength(budget);
            for (const previous of pinned) expect(nodes).toContain(previous);
            pinned = nodes;
        }
    });

    it("gives the same answer twice", async () => {
        /*
         * Every comparison in every round ends in a node index, an edge-type index or a name,
         * so there is no tie a second run can break differently. A scene that reshuffles on
         * re-render reads as the graph moving by itself, and a test that samples it would be
         * flaky rather than failing.
         */
        const { world, labels } = await realWorld();
        for (const id of [INDRA, "VG:DEVATA:SARASVATI"]) {
            const index = labels.ids.indexOf(id);
            if (index < 0) continue;
            const first = selectFocus(world, labels, index, FOCUS_BUDGET);
            const second = selectFocus(world, labels, index, FOCUS_BUDGET);
            expect(second.shown).toEqual(first.shown);
            expect(second.trace).toEqual(first.trace);
        }
    });

    it("defaults the lane round-robin off, and it buys no coverage when on", async () => {
        /*
         * Measured over Indra, Agni, Sarasvati and sacrifice at budgets 24, 40 and 48: coverage
         * was identical in all twelve comparisons, while between-neighbour edges fell by 15% to
         * 29%. This asserts the default and the measured equivalence, so a future change that
         * flips it has to say what it measured.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const off = selectFocus(world, labels, root, FOCUS_BUDGET);
        const on = selectFocus(world, labels, root, FOCUS_BUDGET, { laneRoundRobin: true });
        const kinds = (shown: FocusNeighbour[]) => ({
            predicates: new Set(shown.flatMap((n) => n.predicates)).size,
            families: new Set(shown.flatMap((n) => n.families)).size,
            groups: new Set(shown.map((n) => n.group)).size,
        });
        expect(kinds(on.shown)).toEqual(kinds(off.shown));
        expect(selectFocus(world, labels, root, FOCUS_BUDGET, { laneRoundRobin: false }).shown).toEqual(
            off.shown,
        );
    });
});

/* --------------------------------------------------------------- lines in the scene - */

describe("the lines drawn", () => {
    it("gives a multiply-attested pair its rarest line, not its lowest-numbered one", async () => {
        /*
         * The guaranteed spoke used to be `neighbour.edges[0]`, the lowest edge index, so on a
         * pair joined by two relationships the drawn line was whichever the build happened to
         * write first. A rare relationship sitting at a higher index could be absent from the
         * scene entirely - the same failure the artifact's notes record for the planar world
         * projection, where 16,895 edges were dropped by index order rather than by importance.
         *
         * Indra is the case that matters: 1,803 of its pairs carry two edges, and its
         * predicates run from 3,566 `MENTIONS_DEVATA` down to a single `EPITHET_VARIANT_OF`.
         * Where a pair carries both, the epithet is the line worth drawing.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const scene = focusNeighbourhood(world, labels, root, FOCUS_BUDGET);

        const frequency = new Map<number, number>();
        const incident = edgesOf(world, root);
        for (let i = 0; i < incident.length; i += 1) {
            const type = world.edgeType[incident[i]];
            frequency.set(type, (frequency.get(type) ?? 0) + 1);
        }

        /* One spoke per shown neighbour is guaranteed; those are the ones under test. */
        const firstFor = new Map<number, number>();
        for (const spoke of scene.spokes) {
            if (!firstFor.has(spoke.node)) firstFor.set(spoke.node, spoke.edge);
        }

        let multiplyAttested = 0;
        for (const neighbour of scene.shown) {
            if (neighbour.edges.length < 2) continue;
            multiplyAttested += 1;
            const drawn = firstFor.get(neighbour.node);
            expect(drawn, `${neighbour.label} has no guaranteed line`).toBeDefined();
            const rarest = Math.min(
                ...Array.from(neighbour.edges, (edge) => frequency.get(world.edgeType[edge]) ?? 0),
            );
            expect(
                frequency.get(world.edgeType[drawn as number]) ?? 0,
                `${neighbour.label}: drew a ${world.manifest.edgeTypes[world.edgeType[drawn as number]]} ` +
                    `line where a rarer kind was available`,
            ).toBe(rarest);
        }

        /* Without this the loop above can pass by never running, which is the failure mode
           this suite's own cost test also guards against. */
        expect(
            multiplyAttested,
            "no shown neighbour carries two relationships, so nothing was actually tested",
        ).toBeGreaterThan(0);
    });

    it("draws every one of a pair's lines when there is room, and none of them twice", async () => {
        /* The parallel pass skipped index zero on the assumption that the first pass had taken
           it. Once the first pass chooses by rarity that assumption is false, and skipping by
           index would draw the representative again and drop whatever sat at zero. */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const scene = focusNeighbourhood(world, labels, root, FOCUS_BUDGET);
        const seen = new Set(scene.spokes.map((spoke) => spoke.edge));
        expect(seen.size).toBe(scene.spokes.length);
    });

    it("bounds the edges between neighbours, and never mistakes a spoke for one", async () => {
        /*
         * Unbounded there are 67 lines among Indra's forty, and a top-forty-by-degree set with
         * no coverage rules has 294 - the hairball the whole module avoids. The per-node cap is
         * doing most of the work: without it the lines concentrate on the few most connected
         * neighbours and read as a second hub inside the scene.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const selection = selectFocus(world, labels, root, FOCUS_BUDGET);
        const between = betweenEdges(world, root, selection.shown, {
            betweenCap: betweenCap(FOCUS_BUDGET),
        });
        expect(between.length).toBeLessThanOrEqual(betweenCap(FOCUS_BUDGET));
        const shownNodes = new Set(selection.shown.map((neighbour) => neighbour.node));
        const touched = new Map<number, number>();
        const pairs = new Set<string>();
        for (const edge of between) {
            expect(edge.a).not.toBe(root);
            expect(edge.b).not.toBe(root);
            expect(shownNodes).toContain(edge.a);
            expect(shownNodes).toContain(edge.b);
            expect(otherEnd(world, edge.edge, edge.a)).toBe(edge.b);
            const key = edge.a < edge.b ? `${edge.a}:${edge.b}` : `${edge.b}:${edge.a}`;
            expect(pairs.has(key)).toBe(false);
            pairs.add(key);
            touched.set(edge.a, (touched.get(edge.a) ?? 0) + 1);
            touched.set(edge.b, (touched.get(edge.b) ?? 0) + 1);
        }
        for (const [node, count] of touched) {
            expect(count, `neighbour ${node}`).toBeLessThanOrEqual(BETWEEN_PER_NODE);
        }
    });

    it("keeps the whole scene under the line cap, trimming context before relationships", async () => {
        /*
         * Measured over every curated node: a budget-40 scene draws at worst 116 spokes and 123
         * lines; at 48 it is 140 and 147. SPOKE_CAP 128 therefore clears the default with 10% of
         * headroom and binds on expansion, which is where a reader has asked for more and the
         * hairball is the failure mode.
         */
        const { world, labels } = await realWorld();
        for (const id of [INDRA, "VG:DEVATA:AGNIH"]) {
            const index = labels.ids.indexOf(id);
            if (index < 0) continue;
            for (const budget of [FOCUS_BUDGET_COMPACT, FOCUS_BUDGET, FOCUS_BUDGET_MAX]) {
                const scene = focusNeighbourhood(world, labels, index, budget);
                /* `max(shown, cap)` and not `cap`: one line per neighbour is not
                   discretionary, and FOCUS_BUDGET_MAX of 200 exceeds both caps on its own. A
                   neighbour drawn with no line to the subject is an unattached dot in a view
                   whose whole claim is what the subject is attached to. */
                expect(scene.spokes.length).toBeLessThanOrEqual(
                    Math.max(scene.shown.length, SPOKE_CAP),
                );
                expect(scene.spokes.length + scene.between.length).toBeLessThanOrEqual(
                    Math.max(scene.shown.length, FOCUS_LINE_CAP),
                );
                // Every neighbour has at least one line, at every budget.
                expect(new Set(scene.spokes.map((spoke) => spoke.node)).size).toBe(
                    scene.shown.length,
                );
                // Nothing is lost silently: what is not drawn is counted.
                let carried = 0;
                for (const neighbour of scene.shown) carried += neighbour.edges.length;
                expect(scene.spokes.length + scene.collapsedSpokes).toBe(carried);
                expect(scene.droppedBetween).toBeGreaterThanOrEqual(0);
            }
        }
    });
});

/* ----------------------------------------------------------------- sidebar rows - */

describe("the family rows", () => {
    it("renders an absent family as an absent row rather than omitting it", async () => {
        /*
         * The hard requirement. Four of the twelve families are absent on Indra - PARALLEL,
         * FORMULA, PROSODY and CONTAINMENT - and a sidebar listing only his present
         * families reads as a complete account, from which a reader infers that Indra has no
         * metre. What is true is that metre is a property of a passage and no deity node in this
         * graph carries one: a fact about the shape of the record, not about Indra.
         *
         * This is the same trap this project has documented twice as "type absence in the row,
         * not the caveat" - a result set of only positive rows lets the reader infer a false
         * zero, and a caveat elsewhere on the page does not undo it.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const rows = focusGroupRows(world, root);

        for (const family of ACCOUNTED_FAMILIES) {
            const row = rows.find((candidate) => candidate.family === family);
            expect(row, `${family} has no row`).toBeDefined();
        }
        const absent = rows.filter((row) => !row.present);
        expect(absent.map((row) => row.family).sort()).toEqual(
            ["CONTAINMENT", "FORMULA", "PARALLEL", "PROSODY"].sort(),
        );
        for (const row of absent) {
            expect(row.edges).toBe(0);
            expect(row.subjects).toBe(0);
            expect(row.predicates).toEqual([]);
            // An absent row says so in its own words, and claims nothing about why.
            expect(row.absent).not.toBe("");
            expect(row.heading).not.toBe("");
        }
        // Absent rows sort last: sorted by their zero they would read as the quietest present
        // family rather than as a checked-and-empty axis.
        const lastPresent = rows.findIndex((row) => !row.present);
        expect(rows.slice(lastPresent).every((row) => !row.present)).toBe(true);
    });

    it("accounts for every recorded connection exactly once", async () => {
        /*
         * The arithmetic that makes the absent rows trustworthy: if the family rows do not sum
         * to the degree, a reader cannot tell an absent family from a mis-filed one. Checked on
         * a deity, a passage, a metre and a rite, which between them cover every family.
         */
        const { world, labels } = await realWorld();
        for (const id of [INDRA, "VG:DEVATA:AGNIH", "VG:CONCEPT:YAJNA"]) {
            const index = labels.ids.indexOf(id);
            if (index < 0) continue;
            const rows = focusGroupRows(world, index);
            const sum = rows.reduce((running, row) => running + row.edges, 0);
            expect(sum, labels.labels[index]).toBe(world.nodeDegree[index]);
        }
        /*
         * And on a verse, which is where PROSODY and CONTAINMENT are present - the two families
         * no deity node in this graph can carry. HAS_CHANDAS joins only passages to wordings;
         * without a case that has one, the absent-row assertion above would pass over a family
         * that no subject ever fills, which proves nothing.
         */
        const verse = nodeById(labels, "VG:RV:SAK:M01:S007:V003");
        const verseRows = focusGroupRows(world, verse);
        expect(verseRows.reduce((running, row) => running + row.edges, 0)).toBe(
            world.nodeDegree[verse],
        );
        expect(verseRows.find((row) => row.family === "PROSODY")?.present).toBe(true);
        expect(verseRows.find((row) => row.family === "CONTAINMENT")?.present).toBe(true);
        expect(verseRows.find((row) => row.family === "PROSODY")?.edges).toBeGreaterThan(0);

        /*
         * And on a mandala, whose only family is CONTAINMENT. Eleven of the twelve rows are
         * absent, which is the case the requirement is really about: a sidebar that omitted
         * them would show a structural container as a subject with one relationship and no
         * indication that eleven other axes had been checked and found empty.
         */
        const mandala = nodeById(labels, "VG:RV:SAK:M01");
        const mandalaRows = focusGroupRows(world, mandala);
        expect(mandalaRows.reduce((running, row) => running + row.edges, 0)).toBe(
            world.nodeDegree[mandala],
        );
        expect(mandalaRows.filter((row) => row.present).map((row) => row.family)).toEqual([
            "CONTAINMENT",
        ]);
        expect(mandalaRows.filter((row) => !row.present)).toHaveLength(11);
    });

    it("counts subjects and connections as different numbers", async () => {
        /* Indra's 826 evidence edges reach 799 distinct records, because a record can be both
           the agent and the target of an assertion. Reported as one figure, either overstates
           how many records there are or understates how much is recorded about them. */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const rows = focusGroupRows(world, root, null);
        const evidence = rows.find((row) => row.family === "EVIDENCE");
        expect(evidence?.edges).toBeGreaterThan(evidence?.subjects ?? 0);
        for (const row of rows) {
            expect(row.subjects).toBeLessThanOrEqual(row.edges);
            const predicateEdges = row.predicates.reduce((running, p) => running + p.edges, 0);
            expect(predicateEdges).toBe(row.edges);
        }
    });

    it("says how much of each family is on screen", async () => {
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const scene = focusNeighbourhood(world, labels, root, FOCUS_BUDGET);
        expect(scene.total).toBe(neighboursOf(world, root).length);
        expect(scene.subject.degree).toBe(world.nodeDegree[root]);
        for (const row of scene.rows) {
            expect(row.shown).toBeLessThanOrEqual(Math.min(row.subjects, FOCUS_BUDGET));
            if (!row.present) expect(row.shown).toBe(0);
        }
        // Every shown neighbour is accounted for by at least one family row.
        const shownSomewhere = scene.rows.reduce((running, row) => running + row.shown, 0);
        expect(shownSomewhere).toBeGreaterThanOrEqual(scene.shown.length);
    });
});

/* ------------------------------------------------------------------ the cost of it - */

describe("cost", () => {
    /** Best of N. Contention inflates a sample; it cannot make one faster than the work. */
    function best(work: () => unknown, samples = 60): number {
        for (let i = 0; i < 20; i += 1) work();
        let fastest = Number.POSITIVE_INFINITY;
        for (let i = 0; i < samples; i += 1) {
            const started = performance.now();
            work();
            fastest = Math.min(fastest, performance.now() - started);
        }
        return fastest;
    }

    it("curates the worst node in the corpus in a few passes over its adjacency", async () => {
        /*
         * ## Why this is a ratio and not a millisecond count
         *
         * Because a millisecond count is not portable and this assertion has to fail for one
         * specific reason. Measured on this machine the same work came out at p50 2.35, 2.60 and
         * 4.60 ms on three consecutive runs of the same suite - a 2x spread from nothing but
         * machine load - which is wider than the regression it has to catch. An absolute ceiling
         * tight enough to catch the 7 ms version would fail on a loaded run, and one loose
         * enough to survive a loaded run would not catch it.
         *
         * So the unit is `neighboursOf(Indra)`: one pass over the same 7,347 edges building a
         * Set of the 5,544 distinct neighbours. That is the irreducible work - any curation must
         * at least look at every edge once - and it scales with the machine exactly as the thing
         * being measured does.
         *
         * ## The number
         *
         * Measured over four runs the current implementation is 2.81x to 4.57x that baseline,
         * best-case 1.34 to 2.91 ms absolute. The version this replaced was 6.99 ms against a
         * 0.50 ms baseline, about 14x. Three things got it from there to here, each measured:
         *
         *   - the candidate record stopped being two `Set`s per neighbour and became two 32-bit
         *     words of edge-type bits plus one of family bits: 2.97 ms -> 0.76 ms for the same
         *     5,544 candidates, bit-for-bit the same set;
         *   - the per-predicate, per-group and per-region lists stopped being sorted separately
         *     - about fifty sorts of slices of the same array - and now inherit one sort of the
         *     whole array, 0.88 ms;
         *   - the result formatter stopped walking the root's adjacency once per shown
         *     neighbour, which at budget 40 is 294,000 `otherEnd` calls and was on its own the
         *     entire 6.99 ms.
         *
         * 8x is that with better than 1.7x of headroom over the worst run, and less than
         * two-thirds of the way back to the version it replaced. If this fails, read it as
         * "someone reintroduced a Set per candidate, a per-group sort, or a per-neighbour
         * adjacency walk" - not as flakiness.
         *
         * Nothing here may be called from a frame callback at either figure: even 1.3 ms is a
         * fifth of a 60Hz budget spent on something whose inputs cannot change within a frame.
         * The hook memoises it per selection and the renderers read the arrays.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        expect(world.nodeDegree[root]).toBeGreaterThan(7000);
        expect(neighboursOf(world, root).length).toBeGreaterThan(5000);

        // Interleaved, so a slow window cannot land on one side of the ratio only.
        let baseline = Number.POSITIVE_INFINITY;
        let curation = Number.POSITIVE_INFINITY;
        for (let round = 0; round < 3; round += 1) {
            baseline = Math.min(baseline, best(() => neighboursOf(world, root)));
            curation = Math.min(curation, best(() => selectFocus(world, labels, root, FOCUS_BUDGET)));
        }
        const ratio = curation / baseline;
        expect(
            ratio,
            `${curation.toFixed(3)} ms is ${ratio.toFixed(2)}x one pass over the adjacency (${baseline.toFixed(3)} ms)`,
        ).toBeLessThan(8);
        // A floor under the ratio, in case the baseline itself regresses. Deliberately loose:
        // the worst best-case observed was 2.91 ms and this only has to exclude the absurd.
        expect(curation).toBeLessThan(20);
    });

    it("costs the same at the mobile budget as at the desktop one", async () => {
        /*
         * Counter-intuitive and load-bearing, so it is pinned rather than left as a comment.
         *
         * The cost is O(degree), not O(budget): building and sorting the 5,544 candidates is the
         * whole bill, and the six rounds then spend a budget's worth of slots out of an index
         * that already exists. Measured interleaved over 200 alternating calls, budget 16 and
         * budget 40 came out at p50 2.601 vs 2.679 ms, 2.347 vs 2.364, and 4.600 vs 4.607 - the
         * same number three times. Budget 1 and budget 200 measure the same as well.
         *
         * It matters because the compact mobile budget looks like the cheap path and is not, so
         * a phone does not get a faster selection by drawing fewer orbs; it gets a faster
         * selection by selecting a subject with fewer neighbours, and almost every subject has
         * six. An earlier reading of 4.32 ms at budget 16 against 3.32 at budget 40 suggested
         * the coverage rounds dominated the fill rounds; repeated interleaved, it was noise.
         */
        const { world, labels } = await realWorld();
        const root = nodeById(labels, INDRA);
        const compact = best(() => selectFocus(world, labels, root, FOCUS_BUDGET_COMPACT), 40);
        const full = best(() => selectFocus(world, labels, root, FOCUS_BUDGET), 40);
        expect(compact / full).toBeGreaterThan(0.5);
        expect(compact / full).toBeLessThan(2);
    });
});
