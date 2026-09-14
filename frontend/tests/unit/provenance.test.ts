import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { Provenance } from "@/lib/provenance";

/**
 * The provenance dataset is generated from the committed registries by
 * `scripts/build_frontend_provenance.py`, and the sources page renders it without checking
 * anything. So the checks live here.
 *
 * Two different failures are guarded against. The first is drift: the generator refuses to
 * write if a shipped artifact is unaccounted for, but nothing stops the committed JSON from
 * being edited by hand or left stale, and a stale sources page is a page that names the wrong
 * edition. The second is shape: `src/lib/provenance.ts` types this file by hand, and a field
 * rename in the generator would render an empty section rather than fail.
 *
 * `uv run python scripts/build_frontend_provenance.py --check` is the drift half and belongs
 * in CI beside `make lint`. What is testable from here is that the file shipped in `public/`
 * is internally consistent and complete enough to render.
 */

const FILE = path.join(process.cwd(), "public", "data", "provenance.json");
const provenance = JSON.parse(readFileSync(FILE, "utf8")) as Provenance;

describe("the shipped provenance dataset", () => {
    it("names the generator and the registries it was built from", () => {
        expect(provenance.generator).toBe("scripts/build_frontend_provenance.py");
        expect(provenance.inputs).toContain("data/registry/sources.yaml");
        expect(provenance.inputs).toContain("data/registry/source_artifacts.yaml");
    });

    it("covers all four works, each with its recension, hierarchy and exclusions", () => {
        expect(provenance.works.map((work) => work.veda).sort()).toEqual(["AV", "RV", "SV", "YV"]);
        for (const work of provenance.works) {
            expect(work.recension, work.veda).toBeTruthy();
            expect(work.hierarchy.length, work.veda).toBeGreaterThan(0);
            expect(work.excluded_corpora.length, work.veda).toBeGreaterThan(0);
            expect(work.canonical_build, work.veda).toBeTruthy();
        }
    });

    it("gives every collection its own hierarchy rather than one shape with four labels", () => {
        const shapes = provenance.works.map((work) => work.hierarchy.join(" > "));
        expect(new Set(shapes).size).toBe(shapes.length);
    });

    it("places every entry in a declared layer", () => {
        const layers = new Set(provenance.layers.map((layer) => layer.id));
        for (const entry of provenance.entries) {
            expect(layers, entry.source_id).toContain(entry.layer);
        }
    });

    it("says what every source contributes, for which collections, on what terms", () => {
        expect(provenance.entries.length).toBeGreaterThan(0);
        for (const entry of provenance.entries) {
            expect(entry.name, entry.source_id).toBeTruthy();
            expect(entry.contributes.length, entry.source_id).toBeGreaterThan(30);
            expect(entry.vedas.length, entry.source_id).toBeGreaterThan(0);
            /* Terms are never blank. "No licence statement established" is an answer;
               an empty array would render as nothing and read as unrestricted. */
            expect(entry.rights_status.length, entry.source_id).toBeGreaterThan(0);
            expect(entry.evidence, entry.source_id).toMatch(/^data\//);
        }
    });

    it("carries a citable record for every artifact it lists", () => {
        const artifacts = provenance.entries.flatMap((entry) => entry.artifacts);
        expect(artifacts.length).toBe(provenance.totals.artifacts);
        for (const artifact of artifacts) {
            expect(artifact.artifact_id).toBeTruthy();
            expect(artifact.rights_status, artifact.artifact_id).toBeTruthy();
            expect(artifact.url ?? artifact.source_edition, artifact.artifact_id).toBeTruthy();
        }
    });

    it("keeps the file's own terms apart from the site's", () => {
        /* The registry records GRETIL as UNKNOWN and says why: do not infer a corpus-wide
           licence from a site being reachable. The Rigvedic file it serves declares
           CC BY-NC-SA in its own header. Printing the site's answer for the file would be
           strictly less true than the registry, so the two are separate fields, and at least
           one entry has to actually exercise the difference or the distinction is theatre. */
        const diverging = provenance.entries.filter(
            (entry) =>
                entry.site_rights_status && !entry.rights_status.includes(entry.site_rights_status),
        );
        expect(diverging.length).toBeGreaterThan(0);
    });

    it("reports the shipped set as a subset of the registered one", () => {
        expect(provenance.totals.sources).toBeLessThanOrEqual(provenance.totals.registered_sources);
        expect(provenance.totals.artifacts).toBeLessThanOrEqual(
            provenance.totals.registered_artifacts,
        );
        const distinct = new Set(provenance.entries.map((entry) => entry.source_id));
        expect(distinct.size).toBe(provenance.totals.sources);
    });

    it("distinguishes a source that supplies text from one only consulted against it", () => {
        const layers = provenance.entries.map((entry) => entry.layer);
        expect(layers).toContain("primary-text");
        expect(layers).toContain("comparison");
        /* A source consulted for comparison supplies no verse on the site. Listing it beside
           the text sources would let a reader conclude some of the corpus came from it. */
        const comparison = provenance.entries.filter((entry) => entry.layer === "comparison");
        expect(comparison.length).toBeGreaterThan(0);
    });
});
