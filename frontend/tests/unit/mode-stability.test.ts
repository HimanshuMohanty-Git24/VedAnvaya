import { describe, expect, it } from "vitest";
import {
    DEFAULT_STATE,
    RENDERERS,
    VIEWS,
    graphStateToQuery,
    parseGraphState,
    resolveInitialState,
    selectRegion,
    selectSubject,
    setRenderer,
    setView,
    type GraphState,
} from "@/lib/world/modes";

/**
 * The invariant this phase exists to establish.
 *
 * A reviewer found that interacting with the 3D graph sometimes returned them to a different
 * view. The cause was a state model that carried one `mode` for two different questions -
 * what is being explored, and how it is drawn - so a URL written in one state could be read
 * back as another. Everything below asserts the same rule from a different direction:
 *
 *   nothing the reader does to the graph may change the renderer,
 *   except asking for a different renderer, or the renderer failing.
 */

const round = (state: GraphState) =>
    parseGraphState(new URLSearchParams(graphStateToQuery(state).replace(/^\?/, "")));

const at = (over: Partial<GraphState> = {}): GraphState => ({ ...DEFAULT_STATE, ...over });

describe("the URL round trip is lossless", () => {
    it("survives every view and renderer pairing", () => {
        for (const view of VIEWS) {
            for (const renderer of RENDERERS) {
                const state = at({
                    view,
                    renderer,
                    node: "VG:DEVATA:AGNIH",
                    from: view === "PATH" ? "VG:DEVATA:AGNIH" : null,
                    to: view === "PATH" ? "VG:DEVATA:INDRAH" : null,
                });
                const back = round(state);
                expect(back.view, `${view}/${renderer} lost its view`).toBe(view);
                expect(back.renderer, `${view}/${renderer} lost its renderer`).toBe(renderer);
            }
        }
    });

    it("writes the defaults rather than omitting them", () => {
        /* The specific regression. Omitting WORLD because it was the default is what made a
           selected subject read back as a different view: `?node=X` alone is ambiguous, and
           the application was producing it. */
        const query = graphStateToQuery(at({ node: "VG:DEVATA:AGNIH" }));
        expect(query).toContain("view=world");
        expect(query).toContain("renderer=3d");
    });

    it("keeps a canonical id intact through encoding", () => {
        expect(round(at({ node: "VG:DEVATA:AGNIH" })).node).toBe("VG:DEVATA:AGNIH");
    });

    it("still opens a hand-written link that names only a subject", () => {
        // Every deep link in the product before this phase was `?node=X`, and those links
        // must keep working: a subject with nothing else said is a request to focus on it.
        const state = parseGraphState(new URLSearchParams("node=VG%3ADEVATA%3AAGNIH"));
        expect(state.node).toBe("VG:DEVATA:AGNIH");
        expect(state.view).toBe("FOCUS");
    });

    it("reads two endpoints as a trace", () => {
        const state = parseGraphState(
            new URLSearchParams("from=VG%3ADEVATA%3AAGNIH&to=VG%3ADEVATA%3AINDRAH"),
        );
        expect(state.view).toBe("PATH");
    });

    it("never lets an inference contradict something the URL states", () => {
        /* A URL carrying a node AND an explicit view must obey the view. This is what stops
           the old failure returning in another form. */
        const state = parseGraphState(
            new URLSearchParams("view=world&renderer=2d&node=VG%3ADEVATA%3AAGNIH"),
        );
        expect(state.view).toBe("WORLD");
        expect(state.renderer).toBe("2d");
    });

    it("ignores a renderer or view it does not have", () => {
        const state = parseGraphState(new URLSearchParams("view=hyperbolic&renderer=vr"));
        expect(VIEWS).toContain(state.view);
        expect(RENDERERS).toContain(state.renderer);
    });
});

describe("nothing but an explicit request may change the renderer", () => {
    const cases: Array<[string, (state: GraphState) => GraphState]> = [
        ["selecting a subject", (s) => selectSubject(s, "VG:DEVATA:AGNIH")],
        ["clearing a selection", (s) => selectSubject(s, null)],
        ["selecting a constellation", (s) => selectRegion(s, 4)],
        ["clearing a constellation", (s) => selectRegion(s, null)],
        ["moving to the world", (s) => setView(s, "WORLD")],
        ["moving to focus", (s) => setView(s, "FOCUS")],
        ["starting a trace", (s) => setView(s, "PATH")],
    ];

    for (const renderer of RENDERERS) {
        for (const [what, act] of cases) {
            it(`${what} keeps ${renderer}`, () => {
                const before = at({ renderer, node: "VG:DEVATA:INDRAH" });
                expect(act(before).renderer).toBe(renderer);
            });
        }
    }

    it("changes the renderer only when asked", () => {
        expect(setRenderer(at({ renderer: "3d" }), "2d").renderer).toBe("2d");
        expect(setRenderer(at({ renderer: "2d" }), "3d").renderer).toBe("3d");
    });

    it("leaves everything else alone when the renderer changes", () => {
        /* The other half of the invariant: switching how the graph is drawn must not lose the
           reader's place. A multi-view tool feels like several tools exactly when it does. */
        const before = at({
            view: "PATH",
            renderer: "3d",
            node: "VG:DEVATA:AGNIH",
            region: 7,
            from: "VG:DEVATA:AGNIH",
            to: "VG:DEVATA:INDRAH",
            query: "agni",
        });
        const after = setRenderer(before, "2d");
        expect(after.view).toBe("PATH");
        expect(after.node).toBe("VG:DEVATA:AGNIH");
        expect(after.region).toBe(7);
        expect(after.from).toBe("VG:DEVATA:AGNIH");
        expect(after.to).toBe("VG:DEVATA:INDRAH");
        expect(after.query).toBe("agni");
    });
});

describe("selecting changes depth, not renderer", () => {
    it("takes the world to focus", () => {
        expect(selectSubject(at({ view: "WORLD" }), "VG:X").view).toBe("FOCUS");
    });

    it("returns focus to the world when the selection is cleared", () => {
        expect(selectSubject(at({ view: "FOCUS", node: "VG:X" }), null).view).toBe("WORLD");
    });

    it("does not abandon a trace when a stop on it is inspected", () => {
        const tracing = at({ view: "PATH", from: "VG:A", to: "VG:B" });
        const after = selectSubject(tracing, "VG:MIDDLE");
        expect(after.view).toBe("PATH");
        expect(after.from).toBe("VG:A");
        expect(after.to).toBe("VG:B");
    });
});

describe("where the opening renderer comes from", () => {
    const url = (search: string) => new URLSearchParams(search);

    it("obeys the URL above everything else", () => {
        const { state, rendererSource } = resolveInitialState({
            url: url("view=world&renderer=2d"),
            remembered: "3d",
            capability: "FULL_3D",
        });
        expect(state.renderer).toBe("2d");
        expect(rendererSource).toBe("url");
    });

    it("obeys a remembered choice above the device default", () => {
        const { state, rendererSource } = resolveInitialState({
            url: url(""),
            remembered: "2d",
            capability: "FULL_3D",
        });
        expect(state.renderer).toBe("2d");
        expect(rendererSource).toBe("remembered");
    });

    it("falls back to the device only when nothing else has an answer", () => {
        expect(
            resolveInitialState({ url: url(""), remembered: null, capability: "FLAT" }).state
                .renderer,
        ).toBe("2d");
        expect(
            resolveInitialState({ url: url(""), remembered: null, capability: "FULL_3D" }).state
                .renderer,
        ).toBe("3d");
    });

    it("never lets a weak device overrule an explicit request", () => {
        /* A reader on a slow machine is still entitled to ask for the spatial view. The
           product may advise; it may not decide. */
        const { state } = resolveInitialState({
            url: url("view=world&renderer=3d"),
            remembered: null,
            capability: "FLAT",
        });
        expect(state.renderer).toBe("3d");
    });
});
