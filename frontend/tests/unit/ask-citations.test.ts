import { describe, expect, it } from "vitest";
import {
    extractCitedIds,
    parseAnswer,
    parseAnswerSegments,
    type AnswerCitationSegment,
} from "@/lib/ask-citations";

const citations = (text: string) =>
    parseAnswerSegments(text).filter(
        (segment): segment is AnswerCitationSegment => segment.kind === "citation",
    );

const texts = (text: string) =>
    parseAnswerSegments(text)
        .filter((segment) => segment.kind === "text")
        .map((segment) => (segment.kind === "text" ? segment.text : ""));

describe("citation marker parsing", () => {
    it("reads a single marker and keeps the prose either side of it", () => {
        const segments = parseAnswerSegments("Agni is invoked first [E1] in the collection.");
        expect(segments).toEqual([
            { kind: "text", text: "Agni is invoked first " },
            { kind: "citation", ids: ["E1"] },
            { kind: "text", text: " in the collection." },
        ]);
    });

    it("reads a comma-grouped marker as one marker holding both ids", () => {
        expect(citations("Indra and Agni share the hymn [E2, E3].")).toEqual([
            { kind: "citation", ids: ["E2", "E3"] },
        ]);
    });

    it("reads a semicolon-grouped marker without spaces", () => {
        expect(citations("The wording recurs [E4;E5].")).toEqual([
            { kind: "citation", ids: ["E4", "E5"] },
        ]);
    });

    it("reads 'and' inside a group without needing a pattern per spelling", () => {
        expect(citations("Both verses carry it [E6 and E7].")).toEqual([
            { kind: "citation", ids: ["E6", "E7"] },
        ]);
    });

    it("reads adjacent markers as two markers with no empty text between them", () => {
        const segments = parseAnswerSegments("The dedication differs [E1][E2]");
        expect(segments).toEqual([
            { kind: "text", text: "The dedication differs " },
            { kind: "citation", ids: ["E1"] },
            { kind: "citation", ids: ["E2"] },
        ]);
        expect(segments.some((s) => s.kind === "text" && s.text === "")).toBe(false);
    });

    it("does NOT treat a bracketed aside as a citation", () => {
        expect(citations("As noted [see above], the term is not attested here.")).toEqual([]);
        expect(texts("As noted [see above], the term is not attested here.")).toEqual([
            "As noted [see above], the term is not attested here.",
        ]);
    });

    it("keeps a non-citation bracket inline while still reading a real one", () => {
        const segments = parseAnswerSegments("Fever [takman] is addressed directly [E9].");
        expect(segments).toEqual([
            { kind: "text", text: "Fever [takman] is addressed directly " },
            { kind: "citation", ids: ["E9"] },
            { kind: "text", text: "." },
        ]);
    });

    it("does not read an embedded capital E word as an id", () => {
        expect(citations("[Edition B] and [Ecosystem] are not citations.")).toEqual([]);
        expect(citations("[E12]")).toEqual([{ kind: "citation", ids: ["E12"] }]);
    });

    it("collapses a repeated id inside one group so two chips never overstate one item", () => {
        expect(citations("[E1, E1]")).toEqual([{ kind: "citation", ids: ["E1"] }]);
    });

    it("splits the answer on blank lines and drops the empty blocks", () => {
        const paragraphs = parseAnswer("First claim [E1].\n\n\nSecond claim [E2].\n");
        expect(paragraphs).toHaveLength(2);
        expect(paragraphs[0].segments).toEqual([
            { kind: "text", text: "First claim " },
            { kind: "citation", ids: ["E1"] },
            { kind: "text", text: "." },
        ]);
        expect(paragraphs[1].segments.at(-1)).toEqual({ kind: "text", text: "." });
    });

    it("survives an answer with no markers and an empty answer", () => {
        expect(parseAnswer("No evidence was retrieved for this question.")).toHaveLength(1);
        expect(parseAnswer("")).toEqual([]);
        expect(extractCitedIds("")).toEqual([]);
    });
});

describe("extractCitedIds", () => {
    it("reports every cited id once, in first-appearance order", () => {
        const answer = "Indra leads [E3, E1]. Agni follows [E2]. Indra again [E1][E4].";
        expect(extractCitedIds(answer)).toEqual(["E3", "E1", "E2", "E4"]);
    });

    it("ignores bracketed prose", () => {
        expect(extractCitedIds("[see above] [ibid.] [E7]")).toEqual(["E7"]);
    });

    it("agrees with the segment parser about what was cited", () => {
        const answer = "A [E1, E2] and B [see below] and C [E2;E5].";
        const fromSegments = parseAnswer(answer)
            .flatMap((paragraph) => paragraph.segments)
            .flatMap((segment) => (segment.kind === "citation" ? segment.ids : []));
        expect([...new Set(fromSegments)]).toEqual(extractCitedIds(answer));
    });
});
