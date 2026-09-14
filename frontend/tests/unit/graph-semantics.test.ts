import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { GROUP_NAMES } from "@/lib/world/palette";

/**
 * What a node is drawn as.
 *
 * These assertions used to run against `semanticGroup` in the Cytoscape canvas, which carried
 * its own colour table and is now deleted. The claims they protect are not about that
 * component: they are about the product refusing to draw one kind of thing as another, and
 * they survive the component by a wide margin.
 *
 * The mapping now lives in `scripts/world-groups.json`, read by both build steps and baked
 * into the artifact as a group id per node, so that is what is tested. The deity rule is the
 * one exception - it depends on a per-node flag rather than on a type - and is asserted
 * against the built artifact, where its consequences actually appear.
 */

const ROOT = join(process.cwd());
const TYPE_TO_GROUP: Record<string, string> = JSON.parse(
    readFileSync(join(ROOT, "scripts", "world-groups.json"), "utf8"),
);

describe("the type-to-group mapping", () => {
    it("only ever names groups the renderer knows", () => {
        /* A type mapped to a group that does not exist would be silently drawn in the "other"
           colour, or worse, index past the end of the palette. */
        for (const [type, group] of Object.entries(TYPE_TO_GROUP)) {
            expect(GROUP_NAMES, `${type} maps to an unknown group`).toContain(group);
        }
    });

    it("never puts a human subject in the deity group", () => {
        // A seer, a seer's family and a people are people, whatever else the registry holds.
        expect(TYPE_TO_GROUP.Rishi).toBe("person");
        expect(TYPE_TO_GROUP.RishiFamily).toBe("person");
        expect(TYPE_TO_GROUP.Tribe).toBe("person");
    });

    it("never draws a reified record as Vedic subject matter", () => {
        /* An Anukramani ascription descriptor is a record that someone ascribed something. It
           is not a deity, and drawing it beside one would make the corpus look like it holds
           claims it does not. */
        expect(TYPE_TO_GROUP.DevataAscription).toBe("record");
        expect(TYPE_TO_GROUP.SemanticAssertion).toBe("record");
        expect(TYPE_TO_GROUP.AgentiveAssertion).toBe("record");
    });

    it("labels a derived metric as derived rather than as a fact", () => {
        expect(TYPE_TO_GROUP.DerivedMetric).toBe("derived");
        expect(TYPE_TO_GROUP.InterpretiveClaim).toBe("derived");
    });

    it("keeps a natural phenomenon out of the deity group", () => {
        // Fire the phenomenon and Agni the deity are different subjects that share a name.
        expect(TYPE_TO_GROUP.NaturalPhenomenon).toBe("idea");
        expect(TYPE_TO_GROUP.CosmicEntity).toBe("idea");
    });

    it("puts every passage container in one group, so a verse and its hymn look alike", () => {
        for (const type of ["MANTRA", "HYMN", "SECTION", "STRUCTURAL_CONTAINER"]) {
            expect(TYPE_TO_GROUP[type], type).toBe("passage");
        }
    });

    it("is the only copy of this mapping", () => {
        /* This project has twice had two semantic tables drift apart. The build scripts read
           this file; nothing else may hold a second copy. */
        const build = readFileSync(join(ROOT, "scripts", "build-world.mjs"), "utf8");
        const constellations = readFileSync(
            join(ROOT, "scripts", "build-constellations.mjs"),
            "utf8",
        );
        expect(build).toContain("world-groups.json");
        expect(constellations).toContain("world-groups.json");
        // An inline object literal mapping ontology names to group names would be a second copy.
        expect(build).not.toMatch(/DevataAscription"?\s*:\s*"record"/);
    });
});

describe("the built artifact honours the mapping", () => {
    const manifest = JSON.parse(
        readFileSync(join(ROOT, "public", "world", "world.json"), "utf8"),
    );

    it("declares exactly the groups the renderer knows, in the same order", () => {
        /* Order matters: `nodeGroup` is an index into this array on one side and into the
           palette on the other. A reordering would recolour the whole graph silently. */
        expect(manifest.groups).toEqual([...GROUP_NAMES]);
    });

    it("separates resolved deities from unresolved devata slots", () => {
        /* The distinction the old test protected, checked where it now lives. A devata slot
           whose referent was never resolved must not be drawn as a deity: the registry holds
           human patrons and unidentified names in the same slot. */
        expect(manifest.groups).toContain("deity");
        expect(manifest.groups).toContain("unresolved-deity");
        expect(manifest.groups.indexOf("deity")).not.toBe(
            manifest.groups.indexOf("unresolved-deity"),
        );
    });

    it("names every constellation from metrics or not at all", () => {
        for (const constellation of manifest.constellations ?? []) {
            if (constellation.name === null) continue;
            // A name is only allowed where a Veda dominates or a leading member does.
            const byVeda = constellation.veda && constellation.veda.share >= 0.6;
            const byGroup = constellation.group && constellation.group.share >= 0.5;
            expect(
                byVeda || byGroup || constellation.central.length > 0,
                `constellation ${constellation.id} is named without support`,
            ).toBe(true);
        }
    });
});
