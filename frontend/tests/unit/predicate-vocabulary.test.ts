import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * One source for what a relationship is called.
 *
 * The words on a graph edge are curated scholarship, not a string transformation. They live in
 * `PREDICATE_SEMANTICS` in the API's graph service, they reach the served API as `label` on every
 * edge, and they reach the canvases through `world.predicates.json`, exported from that same
 * Python table by `scripts/export_predicate_semantics.py`.
 *
 * The alternative was to retype the table in TypeScript, and it would have been wrong on the day
 * it was written: this codebase's general enum humaniser turns `HAS_RISHI` into "has rishi" where
 * the curated phrase is "is ascribed to the seer", and it disagrees on 44 of the 57 traversable
 * predicates. Two copies of one lookup have drifted apart twice in this repository.
 *
 * These assertions are what stop a third copy appearing, and what stops the export falling behind
 * the artifact it has to describe.
 */

const ROOT = process.cwd();

type Semantics = {
    phrase: string;
    asserts: string;
    limit: string;
    direction: "DIRECTED" | "SYMMETRIC" | "UNDECLARED";
    basis: "CURATED" | "DERIVED_FROM_NAME";
};

const exported = JSON.parse(
    readFileSync(join(ROOT, "public", "world", "world.predicates.json"), "utf8"),
) as { source: string; predicates: Record<string, Semantics> };

const manifest = JSON.parse(
    readFileSync(join(ROOT, "public", "world", "world.json"), "utf8"),
) as { edgeTypes: string[] };

describe("the exported relationship vocabulary", () => {
    it("covers every predicate the artifact can draw", () => {
        /* An edge whose predicate is missing here would be drawn with a name derived from its
           own token, silently, and nobody would know the curated phrase had been lost. */
        const missing = manifest.edgeTypes.filter((type) => !exported.predicates[type]);
        expect(missing).toEqual([]);
    });

    it("names the Python symbol it came from", () => {
        expect(exported.source).toBe(
            "vedagraph.api.services.graph_service.PREDICATE_SEMANTICS",
        );
    });

    it("carries the curated phrasing, not a mechanical humanisation", () => {
        /* The specific disagreements that make a second table dangerous. If these ever equal
           the underscore-stripped token, the export has stopped reading the curated source. */
        expect(exported.predicates.HAS_RISHI.phrase).toBe("is ascribed to the seer");
        expect(exported.predicates.HAS_CHANDAS.phrase).toBe("is in the metre");
        expect(exported.predicates.CO_OCCURS_WITH.phrase).toBe("co-occurs with");

        /*
         * Asserted in aggregate rather than per predicate, because thirteen curated phrases
         * legitimately equal their own token - "contrasts with" really is the right wording for
         * CONTRASTS_WITH, and demanding that every phrase differ would be demanding that the
         * scholarship be gratuitously unlike the predicate name.
         *
         * What matters is that the great majority do differ. If the export ever fell back to
         * humanising tokens wholesale this count would collapse, which is the failure worth
         * catching.
         */
        const curated = Object.entries(exported.predicates).filter(
            ([, entry]) => entry.basis === "CURATED",
        );
        const differing = curated.filter(
            ([name, entry]) => entry.phrase !== name.toLowerCase().replaceAll("_", " "),
        );
        expect(differing.length).toBeGreaterThanOrEqual(40);
        expect(differing.length / curated.length).toBeGreaterThan(0.7);
    });

    it("says what every curated relationship does not establish", () => {
        /* The half a reader is most often missing, and the reason the inspector exists. A
           curated predicate with an empty limit is a claim presented without its bounds. */
        for (const [name, entry] of Object.entries(exported.predicates)) {
            if (entry.basis !== "CURATED") continue;
            expect(entry.asserts.length, `${name} asserts nothing`).toBeGreaterThan(0);
            expect(entry.limit.length, `${name} states no limit`).toBeGreaterThan(0);
        }
    });

    it("admits where nobody wrote an explanation", () => {
        /* Structural predicates are in the artifact and are not traversable, so the curated
           table does not cover them. The export must say so rather than generating a sentence
           in the same voice as the ones a scholar wrote. */
        const derived = Object.entries(exported.predicates)
            .filter(([, entry]) => entry.basis === "DERIVED_FROM_NAME")
            .map(([name]) => name);
        expect(derived.length).toBeGreaterThan(0);
        for (const name of derived) {
            expect(exported.predicates[name].phrase).toBe(
                name.toLowerCase().replaceAll("_", " "),
            );
        }
    });

    it("only claims a direction the ontology declares", () => {
        /* Most predicates are stored one way round because something had to be, not because the
           corpus claims a direction - every symmetric type has zero mirrored rows. Deriving
           direction from storage order would put an arrowhead on an assertion nobody made. */
        const declared = Object.values(exported.predicates).filter(
            (entry) => entry.direction !== "UNDECLARED",
        );
        expect(declared.length).toBeGreaterThan(0);
        expect(declared.length).toBeLessThan(Object.keys(exported.predicates).length);
        for (const entry of Object.values(exported.predicates)) {
            expect(["DIRECTED", "SYMMETRIC", "UNDECLARED"]).toContain(entry.direction);
        }
    });

    it("is short enough to sit on an edge", () => {
        /* These are drawn on a line in a diagram, not read in a paragraph. A phrase that wraps
           turns the map into a wall of text. */
        for (const type of manifest.edgeTypes) {
            expect(
                exported.predicates[type].phrase.length,
                `${type} is too long to draw`,
            ).toBeLessThanOrEqual(40);
        }
    });

    it("is the only copy of this vocabulary", () => {
        /* `humanizePredicate` is a general enum humaniser and has legitimate uses - match
           levels, entity type names. It must never be pointed at a graph edge, because it
           disagrees with the curated phrasing on most predicates. */
        const sources = [
            "src/lib/world/edge-labels.ts",
            "src/lib/world/edge-label-view.ts",
            "src/components/world/relationship-inspector.tsx",
        ].map((path) => readFileSync(join(ROOT, path), "utf8"));

        for (const source of sources) {
            expect(source).not.toContain("humanizePredicate");
        }
        // Nor may any of them hold an inline phrase table keyed by predicate name.
        for (const source of sources) {
            expect(source).not.toMatch(/HAS_RISHI"?\s*:\s*"/);
        }
    });
});
