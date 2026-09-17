import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
// Build-time JavaScript contract is shared by both consumer importers.
import { validatePublicGraph, exportHash } from "../../scripts/public-identity-contract.mjs";

const rawBytes = readFileSync(join(process.cwd(), ".world/world.raw.json"));
const raw = JSON.parse(rawBytes.toString("utf8"));

describe("public identity publication contract", () => {
    it("gives a passage and every assertion belonging to it different public IDs", () => {
        const passage = "VG:RV:SAK:M01:S007:V003";
        expect(raw.nodes.some((n: { id: string }) => n.id === passage)).toBe(true);
        const assertions = raw.nodes.filter((n: { id: string }) => n.id.startsWith(`semantic-assertion:${passage}:`));
        expect(assertions.length).toBeGreaterThan(0);
        for (const assertion of assertions) expect(assertion.id).not.toBe(passage);
    });

    it("imports a real public graph with globally unique IDs and known endpoints", () => {
        expect(validatePublicGraph(raw)).toEqual({ nodes: raw.nodes.length, edges: raw.edges.length,
            duplicateIdentifiers: 0, unknownReferences: 0 });
    });

    it("rejects duplicate, empty and unknown-reference inputs in both importers", () => {
        expect(() => validatePublicGraph({ nodes: [{ id: "x" }, { id: "x" }], edges: [] })).toThrow(/duplicate/);
        expect(() => validatePublicGraph({ nodes: [{ id: "" }], edges: [] })).toThrow(/empty/);
        expect(() => validatePublicGraph({ nodes: [{ id: "x" }], edges: [[0, 1, "edge"]] })).toThrow(/unknown/);
    });

    it("preserves exactly the export IDs in the browser bundle and pins its input hash", () => {
        const labels = JSON.parse(readFileSync(join(process.cwd(), "public/world/world.labels.json"), "utf8"));
        const manifest = JSON.parse(readFileSync(join(process.cwd(), "public/world/world.json"), "utf8"));
        expect(labels.ids).toEqual(raw.nodes.map((n: { id: string }) => n.id));
        expect(new Set(labels.ids).size).toBe(labels.ids.length);
        expect(manifest.inputPublicExportHash).toBe(exportHash(rawBytes));
    });
});
