/**
 * Figures typed into prose are the unchecked ones.
 *
 * Every table on this site reads from the API, so a paragraph's hand-typed number is the
 * only figure nothing can catch. Three of them had drifted against artifacts sitting in
 * `public/` in this same repository:
 *
 *   - `world-preview-panel.tsx` said "a graph of 35,370 subjects" while
 *     `public/world/world.json` shipped `counts.nodes = 35648`. The build script even
 *     records the join: "35,370 assignments onto 35,648 nodes without complaint".
 *   - `relationship-inspector.tsx` asserted "8 of 60 predicates, verified against
 *     world.predicates.json and the artifact's 48 edge types". The artifact says 68
 *     predicates, 17 directed, 4 symmetric, and world.json says 55 edge types. That
 *     comment had already been wrong once before and was re-verified wrong.
 *   - `lab.ts` said no community assignment "was computed" while `world.json` ships a
 *     Louvain partition with 36 drawn constellations that the map draws.
 *
 * So this file does the only durable thing: it reads the shipped artifacts and fails if a
 * source file re-acquires a literal that contradicts them. It asserts against the file a
 * browser downloads -- `frontend/public/**` -- and not against an intermediate, because a
 * fix that never reaches the shipped artifact is not a fix.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "../..");

const read = (relative: string) => readFileSync(path.join(ROOT, relative), "utf8");
const readJson = (relative: string) => JSON.parse(read(relative));

/** Every source file whose prose a reader sees, plus the comments that misled authors. */
const SOURCES = [
    "src/lib/lab.ts",
    "src/components/home/world-preview-panel.tsx",
    "src/components/world/relationship-inspector.tsx",
    "src/app/vedas/page.tsx",
    "src/app/vedas/[veda]/page.tsx",
];

describe("the shipped world artifacts", () => {
    it("are present and carry the counts the copy would otherwise guess at", () => {
        const world = readJson("public/world/world.json");
        const predicates = readJson("public/world/world.predicates.json");
        expect(world.counts.nodes).toBeGreaterThan(0);
        expect(world.edgeTypes.length).toBeGreaterThan(0);
        expect(predicates.counts.predicates).toBeGreaterThan(0);
    });

    it("carry a community partition, so no copy may say none was computed", () => {
        const world = readJson("public/world/world.json");
        // The artifact the browser downloads. If this ever becomes absent, the sentence in
        // lab.ts becomes true again and this test is where that is noticed.
        expect(world.communities?.algorithm).toBeTruthy();
        expect(world.constellations.length).toBeGreaterThan(0);

        const lab = read("src/lib/lab.ts");
        expect(lab).not.toContain("none was computed");
        // What it must say instead: the partition exists, over the world graph, and is not
        // a grouping of deities.
        expect(lab).toContain("No deity carries a community membership");
    });
});

describe("no source file states a world figure the artifact contradicts", () => {
    const world = readJson("public/world/world.json");
    const predicates = readJson("public/world/world.predicates.json");

    /**
     * Figures that were typed into source and have drifted at least once. Each entry is a
     * number the artifact does NOT support; finding it in source is the failure.
     */
    const forbidden: Array<{ literal: string; why: string }> = [
        { literal: "35,370", why: `world.json counts.nodes is ${world.counts.nodes}` },
        { literal: "35370", why: `world.json counts.nodes is ${world.counts.nodes}` },
        {
            literal: "8 of 60",
            why: `world.predicates.json declares ${predicates.counts.predicates} predicates`,
        },
        {
            literal: "48 edge types",
            why: `world.json carries ${world.edgeTypes.length} edge types`,
        },
    ];

    for (const source of SOURCES) {
        const text = read(source);
        for (const { literal, why } of forbidden) {
            it(`${source} does not say "${literal}"`, () => {
                expect(
                    text.includes(literal),
                    `${source} contains the literal "${literal}", but ${why}. ` +
                        "Read the figure from the artifact rather than typing it.",
                ).toBe(false);
            });
        }
    }
});

describe("the Samavedic hierarchy is stated one way", () => {
    /**
     * It was stated three ways: "Collection -> Parvan -> Dasati -> Verse" on the index,
     * "Collection -> Prapathaka -> Dasati -> Verse" on the detail page, and a five-level
     * form in the provenance artifact the four-corpora plate renders. Measured against the
     * graph, "Parvan" occurs nowhere in the Samaveda at all, and the deepest and most
     * common shape is the five-level one.
     */
    const pages = ["src/app/vedas/page.tsx", "src/app/vedas/[veda]/page.tsx"];

    it("agrees with the provenance artifact a browser downloads", () => {
        const provenance = readJson("public/data/provenance.json");
        const sv = JSON.stringify(provenance).includes("Prapathaka");
        expect(sv).toBe(true);
    });

    for (const page of pages) {
        it(`${page} does not invent a Parvan`, () => {
            expect(read(page)).not.toContain("Parvan");
        });
        it(`${page} states the deepest measured shape`, () => {
            /*
             * The levels, in order, with diacritics folded away.
             *
             * Pinned as a literal string until this pass, which failed the moment the
             * pages started spelling the divisions properly -- "Ārcika → Prapāṭhaka →
             * Ardha → Daśati → Verse" is the same claim as "Collection → Prapathaka →
             * Ardha → Dasati → Verse" and a better rendering of it. What the test is for
             * is that both pages state the *same* five-level shape and neither quietly
             * loses a level, so that is what it now asserts. The top division is left out
             * of the sequence deliberately: "Ārcika" and "Collection" are both true of it
             * and the choice between them is editorial.
             */
            expect(levelsIn(read(page))).toEqual([
                "prapathaka",
                "ardha",
                "dasati",
                "verse",
            ]);
        });
    }

    it("states it the same way on both pages", () => {
        const [index, detail] = pages.map((page) => levelsIn(read(page)));
        expect(index).toEqual(detail);
    });
});

/** The Samavedic divisions a page names, in the order it names them, diacritics folded. */
function levelsIn(source: string): string[] {
    const folded = source.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
    const arrow = folded.indexOf("prapathaka");
    if (arrow < 0) return [];
    const line = folded.slice(arrow, folded.indexOf(String.fromCharCode(10), arrow));
    return line
        .split("→")
        .map((part) => part.replace(/[^a-z]/g, ""))
        .filter(Boolean);
}
