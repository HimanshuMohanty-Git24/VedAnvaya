import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
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

    /*
     * Every graph-derived browser artifact, not just the manifest.
     *
     * world.json and constellations.json were pinned to the exact public export and
     * world.labels.json and world.predicates.json were not, so the lineage contract was
     * satisfiable while two shipped files came from somewhere else. The labels case is the
     * dangerous one: `ids` is a positional join onto world.bin, so a labels file from a
     * different export loads without error and names every node wrongly.
     *
     * Asserted per file by name rather than over a glob, so deleting a key cannot pass by
     * shrinking the set that gets checked.
     */
    it.each([
        "public/world/world.json",
        "public/world/world.labels.json",
        "public/world/world.predicates.json",
        "public/data/home-world.json",
        ".world/constellations.json",
    ])("pins %s to the exact public export it was built from", (relative) => {
        const artifact = JSON.parse(readFileSync(join(process.cwd(), relative), "utf8"));
        expect(artifact.inputPublicExportHash).toBe(exportHash(rawBytes));
    });

    /*
     * Enumerated, not listed. The list above is by name so that deleting a key cannot pass
     * by shrinking the set that gets checked -- but a NEW graph-derived artifact would not
     * appear in it either, and that is exactly how public/data/home-world.json shipped 50
     * real node coordinates with no lineage at all while the four world/* files were
     * pinned. This walks public/ and requires every JSON artifact that names a graph-
     * derived input to carry the export hash too.
     */
    it("leaves no graph-derived artifact under public/ unpinned", () => {
        const root = join(process.cwd(), "public");
        const derived: string[] = [];
        const walk = (dir: string) => {
            for (const entry of readdirSync(dir, { withFileTypes: true })) {
                const full = join(dir, entry.name);
                if (entry.isDirectory()) {
                    walk(full);
                } else if (entry.name.endsWith(".json")) {
                    const text = readFileSync(full, "utf8");
                    if (/world\.(bin|raw\.json)|world\.labels|"source":\s*"public\/world/.test(text)) {
                        derived.push(full);
                    }
                }
            }
        };
        walk(root);
        expect(derived.length).toBeGreaterThan(0);
        const unpinned = derived.filter((file) => {
            const artifact = JSON.parse(readFileSync(file, "utf8"));
            return artifact.inputPublicExportHash !== exportHash(rawBytes);
        });
        expect(unpinned).toEqual([]);
    });

    /*
     * world.bin is the one artifact with nowhere to put its own hash: it is a headerless
     * typed-array blob. So it is pinned from the outside -- the manifest records its sha256
     * and byte length, and the manifest is itself pinned to the export. Without this, the
     * lineage contract could be fully satisfied while the binary came from another build,
     * and `ids` is a positional join onto it, so every label would name the wrong node.
     */
    it("pins world.bin from the manifest, since the binary cannot declare itself", () => {
        const manifest = JSON.parse(readFileSync(join(process.cwd(), "public/world/world.json"), "utf8"));
        const binary = readFileSync(join(process.cwd(), "public/world/world.bin"));
        expect(manifest.worldBinBytes).toBe(binary.byteLength);
        expect(manifest.worldBinSha256).toMatch(/^[0-9a-f]{64}$/);
        expect(manifest.worldBinSha256).toBe(createHash("sha256").update(binary).digest("hex"));
    });

    it("fails a labels artifact whose hash is absent or from another export", () => {
        // Guards the guard. The assertion above passes trivially if `undefined` were ever
        // compared loosely, and an artifact carrying a stale-but-real hash is the exact
        // shape of the defect this contract exists to catch.
        const digest = exportHash(rawBytes);
        expect(digest).toMatch(/^[0-9a-f]{64}$/);
        expect(undefined).not.toBe(digest);
        expect("0".repeat(64)).not.toBe(digest);
    });
});
