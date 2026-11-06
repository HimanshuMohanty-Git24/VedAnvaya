import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { worldNodeSize } from "@/lib/world/node-size";
import type { WorldManifest } from "@/lib/world/artifact";

// Test the shipped layout, where a disconnected outlier previously compressed 90% of
// the corpus into 6% of the world. These bounds allow the force layout to evolve.
const manifest: WorldManifest = JSON.parse(
    readFileSync(resolve("public/world/world.json"), "utf8"),
);
const bytes = readFileSync(resolve("public/world/world.bin"));
function section(name: string) {
    return manifest.sections.find((entry) => entry.name === name)!;
}
const p = section("positions");
const positions = new Float32Array(bytes.buffer, bytes.byteOffset + p.offset, p.length);
const r = section("nodeRegion");
const regions = new Uint16Array(bytes.buffer, bytes.byteOffset + r.offset, r.length);

describe("world legibility", () => {
    it("gives the connected corpus a substantial share of the world", () => {
        const radii: number[] = [];
        for (let i = 0; i < regions.length; i++) {
            if (regions[i] !== 65535)
                radii.push(Math.hypot(...positions.subarray(i * 3, i * 3 + 3)));
        }
        radii.sort((a, b) => a - b);
        expect(radii[Math.floor(radii.length * 0.5)] / manifest.extent).toBeGreaterThan(0.15);
        expect(radii[Math.floor(radii.length * 0.9)] / manifest.extent).toBeGreaterThan(0.35);
    });

    it("places unattached subjects in a volume instead of a decorative shell", () => {
        const radii: number[] = [];
        for (let i = 0; i < regions.length; i++) {
            if (regions[i] === 65535)
                radii.push(Math.hypot(...positions.subarray(i * 3, i * 3 + 3)));
        }
        if (radii.length < 20) return;
        radii.sort((a, b) => a - b);
        const low = radii[Math.floor(radii.length * 0.1)];
        const high = radii[Math.floor(radii.length * 0.9)];
        expect(high - low).toBeGreaterThan(manifest.extent * 0.2);
    });

    it("keeps record coverage below subject coverage at equal degree", () => {
        for (const degree of [0, 7, 50, 7500]) {
            const record = worldNodeSize(9, degree);
            const subject = worldNodeSize(4, degree);
            expect((record / subject) ** 2).toBeLessThan(0.2);
        }
    });

    it("never treats a subject linked to a drawn region as unattached", () => {
        const sectionPairs = section("edgePairs");
        const pairs = new Uint32Array(bytes.buffer, bytes.byteOffset + sectionPairs.offset, sectionPairs.length);
        let strandedEdges = 0;
        for (let i = 0; i < pairs.length; i += 2) {
            if ((regions[pairs[i]] === 65535) !== (regions[pairs[i + 1]] === 65535)) strandedEdges++;
        }
        expect(strandedEdges).toBe(0);
    });
});
