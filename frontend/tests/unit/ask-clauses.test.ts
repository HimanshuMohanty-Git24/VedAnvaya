import { describe, expect, it } from "vitest";
import { caveatSourceLabel, clauses } from "@/lib/ask";

/**
 * The contract on `clauses` is that it decides where a line ends and changes nothing else.
 *
 * The first test is the whole of it: rejoining the output has to reproduce the input. A
 * splitter that silently dropped a clause would make the product state a *weaker* limit than
 * the service reported, which is the single worst edit available to this surface, and it is
 * the kind of loss that reads as an improvement in a screenshot.
 */
describe("clauses", () => {
    const REAL = [
        "AVS 5.22.2 names the deity Agni. The passage names this deity in its own text. What it does not establish: The only deity predicate reaching all four corpora, and it reaches them by two different instruments.",
        "Counts reported here exclude referents graded ambiguous, so every figure is a lower bound.",
        "The drawing and dedication of the soma draughts, cup by cup. Distinct from the pressing, which is VS 18.21: VS 18.21 inventories the pressing gear and VS 18.19-20 inventories the twenty-four drawn cups.",
        "A lift figure over passage co-occurrence. It says nothing about a dual divinity or a shared cult; read 'lift' against the baseline the edge records.",
        "No edge in this graph is HUMAN_REVIEWED and none may claim to be (0 carry it); there is still no human gold set.",
    ];

    it("loses nothing: rejoining the clauses reproduces the input", () => {
        for (const text of REAL) {
            expect(clauses(text).join(" ")).toBe(text.trim());
        }
    });

    it("breaks a multi-sentence qualifier into its sentences", () => {
        const parts = clauses(REAL[0]);
        expect(parts.length).toBeGreaterThan(2);
        expect(parts[0]).toBe("AVS 5.22.2 names the deity Agni.");
    });

    it("does not split a citation at its internal full stop", () => {
        for (const part of clauses(REAL[2])) {
            expect(part).not.toMatch(/\bVS 18$/);
            expect(part).not.toMatch(/^21\b/);
        }
        expect(clauses(REAL[2]).some((part) => part.includes("VS 18.21"))) .toBe(true);
    });

    it("keeps a labelled clause as its own line", () => {
        expect(clauses(REAL[0])).toContain("What it does not establish:");
    });

    it("leaves a single sentence alone", () => {
        expect(clauses(REAL[1])).toEqual([REAL[1]]);
    });

    it("does not split on an abbreviation followed by a lower-case word", () => {
        const text = "Matched by alias, e.g. the surface token, and never by morphology.";
        expect(clauses(text)).toEqual([text]);
    });

    it("returns nothing for nothing, rather than an empty line", () => {
        expect(clauses("")).toEqual([]);
        expect(clauses(null)).toEqual([]);
        expect(clauses("   ")).toEqual([]);
    });
});

describe("caveatSourceLabel", () => {
    it("spells a registry key as words", () => {
        expect(caveatSourceLabel("certainty_scope")).toBe("certainty scope");
        expect(caveatSourceLabel("formula_family_span_census")).toBe(
            "formula family span census",
        );
    });

    it("says so when no source travelled with the caveat", () => {
        expect(caveatSourceLabel(null)).toBe("not recorded");
        expect(caveatSourceLabel("")).toBe("not recorded");
    });
});
