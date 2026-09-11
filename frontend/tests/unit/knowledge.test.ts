import { describe, expect, it } from "vitest";
import {
    attributionCopy,
    certaintyBand,
    certaintyCopy,
    conditionLabel,
    conditionNote,
    defaultDeityTotal,
    entityHref,
    evidenceBasisCopy,
    humanizePredicate,
    isNonDeityDevataSlot,
    isPublicGraphNode,
    isRenderedAsDeity,
    matchLevelCopy,
    parallelKindCopy,
    statusCopy,
    trustTierCopy,
} from "@/lib/knowledge";

describe("knowledge status vocabulary", () => {
    it("never renders NO_LEXICAL_MATCH as an occurrence count", () => {
        const copy = statusCopy("NO_LEXICAL_MATCH");
        expect(copy.label).toBe("No lexical match");
        expect(copy.description).toMatch(/not an occurrence count/i);
        expect(copy.label).not.toMatch(/\b0\b|zero occurrences/i);
        expect(copy.description).not.toMatch(/does not occur/i);
    });

    it("never renders INSUFFICIENT_EVIDENCE as an absence", () => {
        const copy = statusCopy("INSUFFICIENT_EVIDENCE");
        expect(copy.label).toBe("Insufficient evidence");
        expect(copy.description).toMatch(/not the same as an absence/i);
        expect(copy.description).not.toMatch(/\babsent\b|does not occur|no occurrences/i);
    });

    it("distinguishes a measured zero from a missing layer", () => {
        expect(statusCopy("MEASURED_ZERO").label).toBe("Measured zero");
        expect(statusCopy("NOT_BUILT").label).toBe("Not yet modelled");
        expect(statusCopy("NOT_BUILT").description).toMatch(/has not been built/i);
        expect(statusCopy("MEASURED_ZERO").tone).not.toBe(statusCopy("NOT_BUILT").tone);
    });

    it("gives every status a tone so colour is not the only signal", () => {
        for (const status of [
            "SUPPORTED",
            "PARTIAL",
            "INSUFFICIENT_EVIDENCE",
            "NOT_BUILT",
            "NO_LEXICAL_MATCH",
        ]) {
            expect(statusCopy(status).label).toBeTruthy();
            expect(statusCopy(status).tone).toBeTruthy();
        }
    });

    it("degrades gracefully for an unknown status", () => {
        expect(statusCopy(undefined).label).toBe("Status not supplied");
        expect(statusCopy("SOMETHING_NEW").label).toBe("Something new");
    });
});

describe("internal bookkeeping never reaches the graph explorer", () => {
    it.each(["QAIssue", "QA_ISSUE", "Internal", "SourceArtifact", "TextVersion", "Translation"])(
        "hides %s",
        (type) => {
            expect(isPublicGraphNode({ type })).toBe(false);
        },
    );

    it("keeps real subject matter", () => {
        for (const type of ["DEVATA", "MANTRA", "RISHI", "CONCEPT", "RITUAL"]) {
            expect(isPublicGraphNode({ type })).toBe(true);
        }
    });
});

describe("deity resolution", () => {
    it("only draws a resolved deity as a deity", () => {
        expect(isRenderedAsDeity({ type: "DEVATA", is_deity: true })).toBe(true);
        expect(isRenderedAsDeity({ type: "DEVATA", is_deity: false })).toBe(false);
        expect(isRenderedAsDeity({ type: "DEVATA", is_deity: null })).toBe(false);
    });

    it("marks an unresolved devata slot, which is where human patrons sit", () => {
        expect(isNonDeityDevataSlot({ type: "DEVATA", is_deity: false })).toBe(true);
        expect(isNonDeityDevataSlot({ type: "RISHI", is_deity: false })).toBe(false);
    });

    it("excludes ambiguous mentions from the default total", () => {
        const certainty = { certain_count: 831, probable_count: 877, ambiguous_count: 835 };
        expect(defaultDeityTotal(certainty)).toBe(1708);
        expect(defaultDeityTotal(certainty)).not.toBe(
            certainty.certain_count + certainty.probable_count + certainty.ambiguous_count,
        );
    });

    it("bands every certainty tier the API can send", () => {
        expect(certaintyBand("DEITY_CERTAIN")).toBe("certain");
        expect(certaintyBand("DEITY_PROBABLE")).toBe("probable");
        expect(certaintyBand("DEITY_AMBIGUOUS")).toBe("ambiguous");
        expect(certaintyCopy("DEITY_AMBIGUOUS")).toBe("Ambiguous");
        expect(certaintyBand(null)).toBe("unknown");
    });
});

describe("condition kinds", () => {
    it("never calls a threat a disease", () => {
        expect(conditionLabel("THREAT")).toBe("Threat");
        expect(conditionNote("THREAT")).toMatch(/not a disease/i);
        expect(conditionLabel("THREAT")).not.toMatch(/affliction|disease/i);
    });

    it("keeps afflictions and named causes apart", () => {
        expect(conditionLabel("AFFLICTION")).toBe("Affliction");
        expect(conditionLabel("PATHOGEN_OR_CAUSE")).toBe("Named cause or agent");
        expect(conditionNote("PATHOGEN_OR_CAUSE")).toMatch(/not a modern pathogen/i);
    });
});

describe("grade vocabulary is translated for readers", () => {
    it("never surfaces a raw tier name as the reader-facing phrase", () => {
        expect(trustTierCopy("TIER_A")).toBe("Textual");
        expect(trustTierCopy("TIER_B")).toBe("Derived");
        expect(trustTierCopy("TIER_C")).toBe("Reviewed semantic relationship");
        expect(trustTierCopy("TIER_D")).toBe("Interpretive");
        for (const tier of ["TIER_A", "TIER_B", "TIER_C", "TIER_D"]) {
            expect(trustTierCopy(tier)).not.toMatch(/TIER_/);
        }
    });

    it("separates a statement of the source from a projection of the build", () => {
        expect(evidenceBasisCopy("SOURCE_STATED").label).toBe("Stated in the source");
        expect(evidenceBasisCopy("CONTAINER_INHERITED").label).toBe("Inherited from the hymn");
        expect(evidenceBasisCopy("CONTAINER_INHERITED").detail).toMatch(
            /not stated verse by verse/i,
        );
        expect(evidenceBasisCopy("MODEL_ADJUDICATED").detail).toMatch(/interpretive/i);
    });

    it("says what an attribution attributes", () => {
        expect(attributionCopy("PER_PASSAGE")).toBe("Stated for this verse");
        expect(attributionCopy("CONTAINER_INHERITED")).toBe("Inherited from the hymn");
        expect(attributionCopy("NOT_AN_ATTRIBUTION")).toBe("Not an attribution");
    });
});

describe("parallel vocabulary", () => {
    it("does not present shared vocabulary as shared wording", () => {
        const overlap = parallelKindCopy("ENTITY_VOCABULARY_OVERLAP");
        expect(overlap.label).toBe("Shared vocabulary");
        expect(overlap.detail).toMatch(/not shared wording/i);
    });

    it("names the folding a cross-script match depends on", () => {
        expect(matchLevelCopy("SANDHI_INSENSITIVE")).toBe("Matched after sandhi folding");
        expect(matchLevelCopy(null)).toBe("Match level not recorded");
    });
});

describe("routing", () => {
    it("routes each kind to its own surface", () => {
        expect(entityHref("DEVATA", "VG:DEVATA:INDRAH")).toBe("/devatas/VG%3ADEVATA%3AINDRAH");
        expect(entityHref("MANTRA", "VG:RV:SAK:M01:S001:V001")).toMatch(/^\/passage\//);
        expect(entityHref("RITUAL", "VG:CONCEPT:YAJNA-SACRIFICE")).toMatch(/^\/rituals\//);
        expect(entityHref("FORMULA_FAMILY", "VG:X")).toMatch(/^\/formula-families\//);
        expect(entityHref("CONDITION", "VG:CONCEPT:TAKMAN-FEVER")).toBe(
            "/entities/condition/VG%3ACONCEPT%3ATAKMAN-FEVER",
        );
    });

    it("humanises a screaming-snake predicate", () => {
        expect(humanizePredicate("MENTIONS_DEVATA")).toBe("mentions devata");
        expect(humanizePredicate(null)).toBe("not supplied");
    });
});
