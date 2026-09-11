import { describe, expect, it } from "vitest";
import { GROUP_STYLE, semanticGroup } from "@/components/graph-canvas";

describe("graph semantic grouping", () => {
    it("keeps a resolved deity and an unresolved devata slot in different groups", () => {
        expect(semanticGroup({ type: "DEVATA", is_deity: true })).toBe("deity");
        expect(semanticGroup({ type: "DEVATA", is_deity: false })).toBe("unresolved-deity");
        expect(semanticGroup({ type: "DEVATA", is_deity: null })).toBe("unresolved-deity");
    });

    it("never puts a human subject in the deity group", () => {
        // A human patron carried in the devata registry arrives as is_deity=false.
        const humanPatron = { type: "DEVATA", is_deity: false };
        expect(semanticGroup(humanPatron)).not.toBe("deity");
        expect(semanticGroup({ type: "RISHI", is_deity: null })).toBe("person");
        expect(semanticGroup({ type: "TRIBE", is_deity: null })).toBe("person");
    });

    it("gives each group a distinct shape as well as a colour", () => {
        const groups = Object.keys(GROUP_STYLE) as Array<keyof typeof GROUP_STYLE>;
        const deityShape = GROUP_STYLE.deity.shape;
        const passageShape = GROUP_STYLE.passage.shape;
        expect(deityShape).not.toBe(passageShape);
        for (const group of groups) {
            expect(GROUP_STYLE[group].label).toBeTruthy();
            expect(GROUP_STYLE[group].shape).toBeTruthy();
            expect(GROUP_STYLE[group].light).not.toBe(GROUP_STYLE[group].dark);
        }
    });

    it("never draws a reified record as Vedic subject matter", () => {
        // An Anukramani ascription descriptor is not a deity name.
        expect(semanticGroup({ type: "DEVATA_ASCRIPTION", is_deity: null })).toBe("record");
        expect(semanticGroup({ type: "SEMANTIC_ASSERTION" })).toBe("record");
        expect(GROUP_STYLE.record.label).toBe("Evidence record");
        expect(GROUP_STYLE.record.shape).not.toBe(GROUP_STYLE.deity.shape);
    });

    it("labels a derived metric as derived rather than as a fact", () => {
        expect(semanticGroup({ type: "DERIVED_METRIC" })).toBe("derived");
        expect(GROUP_STYLE.derived.label).toBe("Derived metric");
    });

    it("places every common entity type in a real group", () => {
        const types = [
            "MANTRA",
            "PASSAGE",
            "RISHI",
            "CONCEPT",
            "RITUAL",
            "OFFERING",
            "FORMULA_FAMILY",
            "CHANDAS",
            "CONDITION",
            "PLANT",
            "METAL",
            "RIVER",
        ];
        for (const type of types) {
            expect(semanticGroup({ type })).not.toBe("other");
        }
    });
});
