import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
    edgesOf,
    loadWorld,
    loadWorldLabels,
    neighboursOf,
    otherEnd,
    type WorldManifest,
} from "@/lib/world/artifact";

/**
 * The world artifact.
 *
 * What is worth testing here is the decoding, not the picture. Positions are the output of a
 * force simulation and asserting them would be asserting a random seed; the adjacency index
 * built over them is pure arithmetic, it is read on every hover and every selection, and if
 * it is wrong the map silently shows the wrong neighbours - which looks exactly like a map
 * showing the right ones.
 */

/** A graph small enough to check by hand: a triangle, a tail, and an isolated node. */
function tinyWorld() {
    const nodes = 5;
    const positions = new Float32Array([
        0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0, 10, 500, 500, 500,
    ]);
    const nodeType = new Uint8Array([0, 1, 1, 2, 2]);
    const nodeGroup = new Uint8Array([0, 2, 2, 4, 10]);
    const nodeDegree = new Uint16Array([3, 2, 2, 1, 0]);
    /* 0-1, 0-2, 1-2 (triangle), 0-3 (tail). Node 4 is isolated.
       Edge types mirror the real artifact's ordering rule: the two semantic edges come first
       and the two structural ones last, so `semanticEdges` is the boundary between them. */
    const edgePairs = new Uint32Array([0, 1, 0, 2, 1, 2, 0, 3]);
    const edgeType = new Uint8Array([0, 0, 1, 1]);

    const sections: WorldManifest["sections"] = [];
    let offset = 0;
    const parts: Array<[string, ArrayBufferView]> = [
        ["positions", positions],
        ["nodeType", nodeType],
        ["nodeGroup", nodeGroup],
        ["nodeDegree", nodeDegree],
        ["edgePairs", edgePairs],
        ["edgeType", edgeType],
    ];
    for (const [name, array] of parts) {
        offset = Math.ceil(offset / 8) * 8;
        sections.push({
            name,
            offset,
            length: (array as unknown as { length: number }).length,
            type: array.constructor.name,
        });
        offset += array.byteLength;
    }
    const buffer = new ArrayBuffer(offset);
    const bytes = new Uint8Array(buffer);
    parts.forEach(([, array], i) => {
        bytes.set(
            new Uint8Array(array.buffer, array.byteOffset, array.byteLength),
            sections[i].offset,
        );
    });

    const manifest: WorldManifest = {
        version: 1,
        generated: "2026-09-14T00:00:00Z",
        source: { nodes, edges: 4 },
        counts: { nodes, edges: 4 },
        extent: 1000,
        ticks: 10,
        semanticEdges: 2,
        groups: [
            "deity",
            "unresolved-deity",
            "passage",
            "person",
            "idea",
            "rite",
            "thing",
            "wording",
            "derived",
            "record",
            "other",
        ],
        types: ["Devata", "MANTRA", "Concept"],
        edgeTypes: ["MENTIONS_DEVATA", "CONTAINS"],
        sections,
        hubs: [0],
        maxDegree: 3,
    };
    return { manifest, buffer };
}

beforeEach(() => {
    const { manifest, buffer } = tinyWorld();
    vi.stubGlobal(
        "fetch",
        vi.fn(async (url: string) => {
            if (String(url).endsWith("world.json")) {
                return { ok: true, json: async () => manifest } as unknown as Response;
            }
            if (String(url).endsWith("world.bin")) {
                return { ok: true, arrayBuffer: async () => buffer } as unknown as Response;
            }
            if (String(url).endsWith("world.labels.json")) {
                return {
                    ok: true,
                    json: async () => ({
                        ids: ["VG:DEVATA:AGNIH", "VG:RV:1", "VG:RV:2", "VG:CONCEPT:X", "VG:LONE"],
                        labels: ["agniḥ", "RV 1.1.1", "RV 1.1.2", "fire", "unattached"],
                    }),
                } as unknown as Response;
            }
            return { ok: false } as unknown as Response;
        }),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("decoding the world", () => {
    it("builds typed-array views over the packed buffer", async () => {
        const world = await loadWorld();
        expect(world.manifest.counts).toEqual({ nodes: 5, edges: 4 });
        expect(world.positions).toBeInstanceOf(Float32Array);
        expect(world.positions.length).toBe(15);
        expect(world.edgePairs.length).toBe(8);
        // Section boundaries are 8-byte aligned, so a view can be taken rather than a copy.
        for (const section of world.manifest.sections) {
            expect(section.offset % 8).toBe(0);
        }
    });

    it("reads every node's own values back, not a neighbour's", async () => {
        const world = await loadWorld();
        expect(Array.from(world.nodeDegree)).toEqual([3, 2, 2, 1, 0]);
        expect(world.manifest.groups[world.nodeGroup[0]]).toBe("deity");
        expect(world.manifest.types[world.nodeType[0]]).toBe("Devata");
        expect(world.manifest.groups[world.nodeGroup[4]]).toBe("other");
    });
});

describe("the adjacency index", () => {
    it("finds every edge touching a node, in either direction", async () => {
        const world = await loadWorld();
        // Node 0 is the source of all three of its edges; node 2 is a target twice.
        expect(Array.from(edgesOf(world, 0)).sort()).toEqual([0, 1, 3]);
        expect(Array.from(edgesOf(world, 2)).sort()).toEqual([1, 2]);
        expect(Array.from(edgesOf(world, 3))).toEqual([3]);
    });

    it("returns nothing for an isolated node rather than the next node's run", async () => {
        /* The failure this guards is an off-by-one in the CSR offsets, which does not throw:
           it silently hands back a neighbour's edges, and a map showing the wrong connections
           looks exactly like one showing the right ones. */
        const world = await loadWorld();
        expect(edgesOf(world, 4).length).toBe(0);
        expect(neighboursOf(world, 4).length).toBe(0);
    });

    it("agrees with the degree recorded at build time", async () => {
        const world = await loadWorld();
        for (let i = 0; i < world.manifest.counts.nodes; i += 1) {
            expect(edgesOf(world, i).length, `node ${i}`).toBe(world.nodeDegree[i]);
        }
    });

    it("walks an edge to its other end from either side", async () => {
        const world = await loadWorld();
        expect(otherEnd(world, 0, 0)).toBe(1);
        expect(otherEnd(world, 0, 1)).toBe(0);
    });

    it("lists first-degree neighbours", async () => {
        const world = await loadWorld();
        expect(Array.from(neighboursOf(world, 0)).sort()).toEqual([1, 2, 3]);
        expect(Array.from(neighboursOf(world, 1)).sort()).toEqual([0, 2]);
    });

    it("covers every edge exactly twice across all nodes", async () => {
        const world = await loadWorld();
        let seen = 0;
        for (let i = 0; i < world.manifest.counts.nodes; i += 1) seen += edgesOf(world, i).length;
        expect(seen).toBe(world.manifest.counts.edges * 2);
    });
});

describe("the level-of-detail split", () => {
    it("puts the semantic edges before the structural ones", async () => {
        const world = await loadWorld();
        const semantic = world.manifest.semanticEdges ?? world.manifest.counts.edges;
        expect(semantic).toBeLessThan(world.manifest.counts.edges);
        const structuralIndex = world.manifest.edgeTypes.indexOf("CONTAINS");
        // Everything at or past the split is structural; nothing before it is.
        for (let i = 0; i < semantic; i += 1) {
            expect(world.edgeType[i]).not.toBe(structuralIndex);
        }
        for (let i = semantic; i < world.manifest.counts.edges; i += 1) {
            expect(world.edgeType[i]).toBe(structuralIndex);
        }
    });

    it("names only nodes worth naming in the hub index", async () => {
        const world = await loadWorld();
        for (const hub of world.manifest.hubs) {
            const group = world.manifest.groups[world.nodeGroup[hub]];
            // Passages and reified records are excluded by construction: the busiest nodes by
            // raw degree are metres and verses, and a world labelled with those describes the
            // prosody of the corpus rather than its subject.
            expect(group).not.toBe("passage");
            expect(group).not.toBe("record");
        }
    });
});

describe("labels", () => {
    it("arrive separately and line up with the node order", async () => {
        const world = await loadWorld();
        const labels = await loadWorldLabels();
        expect(labels.ids.length).toBe(world.manifest.counts.nodes);
        expect(labels.labels.length).toBe(world.manifest.counts.nodes);
        expect(labels.labels[0]).toBe("agniḥ");
        expect(labels.ids[0]).toBe("VG:DEVATA:AGNIH");
    });
});

describe("a world that cannot be read", () => {
    it("fails with a sentence rather than a stack", async () => {
        vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false }) as unknown as Response));
        await expect(loadWorld()).rejects.toThrow(/could not be read/i);
    });
});
