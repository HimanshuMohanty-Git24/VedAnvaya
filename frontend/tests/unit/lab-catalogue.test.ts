import { describe, expect, it } from "vitest";
import { CORPORA, corpusValue, count, NOT_DRAWN, PLATES, PLATES_BY_SLUG, rate } from "@/lib/lab";

/**
 * The Lab's catalogue is a contract, not a list of copy.
 *
 * Section 6 of the phase brief says a visualization that cannot answer five questions does not
 * ship. Those five are fields on `PlateLabel`, so a plate written without one of them is a type
 * error — but a plate written with `""` in one of them is not, and a plate whose wall label
 * repeats its summary is not either. That is what these check.
 */

describe("the plate catalogue", () => {
    it("has a unique slug per plate and an entry in the lookup for each", () => {
        const slugs = PLATES.map((plate) => plate.slug);
        expect(new Set(slugs).size).toBe(slugs.length);
        for (const plate of PLATES) {
            expect(PLATES_BY_SLUG[plate.slug]).toBe(plate);
        }
    });

    it.each(PLATES.map((plate) => [plate.slug, plate] as const))(
        "%s answers all five questions of the visualization standard",
        (_slug, plate) => {
            for (const [field, value] of Object.entries(plate.label)) {
                expect(value, `${plate.slug}.label.${field}`).toBeTruthy();
                /* A one-clause answer is a placeholder. The shortest real one in the set is
                   the scope line, and it runs to about forty characters. */
                expect(
                    value.length,
                    `${plate.slug}.label.${field} is too short to be an answer`,
                ).toBeGreaterThan(40);
            }
        },
    );

    it.each(PLATES.map((plate) => [plate.slug, plate] as const))(
        "%s states a question, a summary and a caution that are not the same sentence",
        (_slug, plate) => {
            expect(plate.question.endsWith("?")).toBe(true);
            expect(plate.summary).not.toBe(plate.caution);
            expect(plate.label.notInfer).not.toBe(plate.caution);
            expect(plate.reads).toBeTruthy();
        },
    );

    it("never promises a plate the router cannot serve", () => {
        /* `PlateSlug` is a closed union and the route's switch is exhaustive over it, so a
           catalogue entry outside the union fails to compile. This asserts the other
           direction: the union has not grown past the catalogue. */
        const slugs = new Set(PLATES.map((plate) => plate.slug));
        expect(slugs.size).toBe(Object.keys(PLATES_BY_SLUG).length);
    });

    it("records what was considered and refused, with a reason and a route onward", () => {
        expect(NOT_DRAWN.length).toBeGreaterThan(0);
        for (const item of NOT_DRAWN) {
            expect(item.why.length).toBeGreaterThan(60);
            expect(item.href).toBeTruthy();
        }
    });
});

describe("corpus figures", () => {
    it("lists the four collections in traditional order, always all four", () => {
        expect(CORPORA.map((corpus) => corpus.code)).toEqual(["RV", "SV", "YV", "AV"]);
    });

    it("reads a per-corpus row by its lower-case key", () => {
        const row = { rv: 10, sv: null, yv: 3, av: undefined };
        expect(corpusValue(row, "RV")).toBe(10);
        expect(corpusValue(row, "YV")).toBe(3);
    });

    it("returns null rather than zero for a corpus the layer did not reach", () => {
        /* The single most important line in this file. `null` from these endpoints means "not
           reached"; turning it into 0 here is how a missing layer becomes a claim about the
           Vedas. */
        expect(corpusValue({ rv: 10, sv: null }, "SV")).toBeNull();
        expect(corpusValue({ rv: 10 }, "AV")).toBeNull();
        expect(corpusValue(null, "RV")).toBeNull();
    });

    it("keeps a measured zero as a zero", () => {
        expect(corpusValue({ rv: 0 }, "RV")).toBe(0);
        expect(count(0)).toBe("0");
    });
});

describe("number formatting", () => {
    it("groups thousands and returns null for an absent figure", () => {
        expect(count(10552)).toBe("10,552");
        expect(count(null)).toBeNull();
        expect(count(undefined)).toBeNull();
    });

    it("gives a rate the precision its underlying counts can carry", () => {
        expect(rate(0.57)).toBe("0.57");
        expect(rate(219.63)).toBe("219.6");
        expect(rate(null)).toBeNull();
    });
});
