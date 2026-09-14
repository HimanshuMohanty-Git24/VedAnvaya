import { describe, expect, it } from "vitest";
import {
    EMPTY_STATE,
    GRAPH_MODES,
    defaultModeFor,
    graphStateToQuery,
    isSpatial,
    parseGraphState,
    switchMode,
} from "@/lib/world/modes";

/**
 * The mode state machine.
 *
 * What is under test is the property that makes four views one product rather than four tools:
 * that moving between them carries the reader's place along. A reader who has found Agni in
 * the world and switches to the planar diagram has not asked to start again, and the most
 * common way a multi-view tool feels like several tools is that each view begins empty.
 */

const q = (search: string) => parseGraphState(new URLSearchParams(search));

describe("reading state from a URL", () => {
    it("defaults to the world when nothing is asked for", () => {
        expect(q("").mode).toBe("WORLD");
    });

    it("honours an explicit mode, whatever its case", () => {
        expect(q("mode=2d").mode).toBe("2D");
        expect(q("mode=PATH").mode).toBe("PATH");
        expect(q("mode=3D").mode).toBe("3D");
    });

    it("ignores a mode it does not have", () => {
        // A stale or hand-edited link should land somewhere real rather than on nothing.
        expect(q("mode=hyperbolic").mode).toBe("WORLD");
    });

    it("reads a bare node link as a request to look at that subject", () => {
        /* Every deep link written before this phase was `/graph?node=X`, and those links are in
           the product's own pages. A subject with no mode means someone wants to see it. */
        const state = q("node=VG%3ADEVATA%3AAGNIH");
        expect(state.node).toBe("VG:DEVATA:AGNIH");
        expect(state.mode).toBe("3D");
    });

    it("reads two endpoints as a request to trace between them", () => {
        const state = q("from=VG%3ADEVATA%3AAGNIH&to=VG%3ADEVATA%3AINDRAH");
        expect(state.mode).toBe("PATH");
        expect(state.from).toBe("VG:DEVATA:AGNIH");
        expect(state.to).toBe("VG:DEVATA:INDRAH");
    });
});

describe("writing state back", () => {
    it("writes only what differs from the default", () => {
        expect(graphStateToQuery(EMPTY_STATE)).toBe("");
        expect(graphStateToQuery({ ...EMPTY_STATE, mode: "2D" })).toBe("?mode=2d");
    });

    it("round-trips every mode", () => {
        for (const mode of GRAPH_MODES) {
            const query = graphStateToQuery({ ...EMPTY_STATE, mode });
            expect(q(query.replace(/^\?/, "")).mode).toBe(mode);
        }
    });

    it("round-trips a selected subject without mangling its colons", () => {
        const state = { ...EMPTY_STATE, mode: "3D" as const, node: "VG:DEVATA:AGNIH" };
        const back = q(graphStateToQuery(state).replace(/^\?/, ""));
        expect(back.node).toBe("VG:DEVATA:AGNIH");
        expect(back.mode).toBe("3D");
    });

    it("does not serialise the camera", () => {
        /* Deliberate: a camera angle changes on every frame of an orbit, and a link that
           restores one restores the single thing the recipient will change first. */
        const query = graphStateToQuery({ ...EMPTY_STATE, mode: "3D", node: "VG:X" });
        expect(query).not.toMatch(/camera|zoom|rot|eye/i);
    });
});

describe("switching mode", () => {
    it("carries the selected subject across", () => {
        const state = { ...EMPTY_STATE, mode: "WORLD" as const, node: "VG:DEVATA:AGNIH" };
        expect(switchMode(state, "2D").node).toBe("VG:DEVATA:AGNIH");
        expect(switchMode(state, "3D").node).toBe("VG:DEVATA:AGNIH");
    });

    it("offers the selected subject as the start of a path", () => {
        const state = { ...EMPTY_STATE, mode: "3D" as const, node: "VG:DEVATA:AGNIH" };
        expect(switchMode(state, "PATH").from).toBe("VG:DEVATA:AGNIH");
    });

    it("keeps an existing start point rather than overwriting it", () => {
        const state = {
            ...EMPTY_STATE,
            mode: "PATH" as const,
            from: "VG:DEVATA:SOMAH",
            node: "VG:DEVATA:AGNIH",
        };
        expect(switchMode(state, "PATH").from).toBe("VG:DEVATA:SOMAH");
    });

    it("drops a traced route on leaving path, but keeps where the reader is standing", () => {
        const state = {
            ...EMPTY_STATE,
            mode: "PATH" as const,
            from: "VG:A",
            to: "VG:B",
            node: "VG:A",
        };
        const next = switchMode(state, "2D");
        expect(next.from).toBeNull();
        expect(next.to).toBeNull();
        expect(next.node).toBe("VG:A");
    });

    it("is a no-op on the mode already in use", () => {
        const state = { ...EMPTY_STATE, mode: "2D" as const, node: "VG:A" };
        expect(switchMode(state, "2D")).toBe(state);
    });
});

describe("choosing a mode for a device", () => {
    it("never overrides what was explicitly asked for", () => {
        /* A reader on a weak device is still allowed to ask for the spatial view; the product
           may advise, and must not decide. */
        expect(defaultModeFor("FLAT", "3D")).toBe("3D");
        expect(defaultModeFor("FLAT", "WORLD")).toBe("WORLD");
    });

    it("opens the planar view where nothing can be drawn spatially", () => {
        expect(defaultModeFor("FLAT", null)).toBe("2D");
    });

    it("opens the world everywhere else", () => {
        expect(defaultModeFor("FULL_3D", null)).toBe("WORLD");
        expect(defaultModeFor("REDUCED_3D", null)).toBe("WORLD");
    });
});

describe("which modes use the spatial engine", () => {
    it("is every mode except the planar one", () => {
        expect(isSpatial("WORLD")).toBe(true);
        expect(isSpatial("3D")).toBe(true);
        expect(isSpatial("PATH")).toBe(true);
        expect(isSpatial("2D")).toBe(false);
    });
});
