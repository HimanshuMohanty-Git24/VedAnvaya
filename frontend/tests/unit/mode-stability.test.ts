import { describe, expect, it } from "vitest";
import {
    DEFAULT_STATE,
    RENDERERS,
    VIEWS,
    graphStateToQuery,
    parseGraphState,
    resolveInitialState,
    isReaderIntent,
    returnToWorld,
    selectRegion,
    selectSubject,
    setRenderer,
    setView,
    READER_INTENTS,
    SYSTEM_CAUSES,
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

    it("does NOT return focus to the world when the subject is cleared", () => {
        /*
         * This assertion is the inverse of the one it replaces, and the inversion is the fix.
         *
         * `selectSubject(state, null)` used to demote FOCUS to WORLD, and the old test asserted
         * that it did. But the transition made every caller who could pass a null into an
         * unauthorised writer of `view`, and one of those callers was a tap on empty canvas.
         * A reader panning the planar diagram slowly enough that no single pointer event moved
         * more than a pixel was classified as having clicked, the click hit nothing, and a
         * Focus session on Indra became the whole projected corpus. That was the release
         * blocker the product owner reported twice.
         *
         * Clearing a subject now clears the subject. Leaving Focus is `returnToWorld`, which
         * has two callers and both of them are the reader saying so.
         */
        const cleared = selectSubject(at({ view: "FOCUS", node: "VG:X" }), null);
        expect(cleared.view).toBe("FOCUS");
        expect(cleared.node).toBeNull();
    });

    it("leaves focus only when explicitly asked", () => {
        const left = returnToWorld(at({ view: "FOCUS", node: "VG:X" }));
        expect(left.view).toBe("WORLD");
        expect(left.node).toBeNull();
    });

    it("refuses a focus with no subject", () => {
        /* Focus is about a subject. `view=focus&node=` is a view whose own copy promises "one
           subject and what it is attached to" with no subject to show, and the write that
           followed it computed from a state that meant nothing. */
        expect(setView(at({ view: "WORLD", node: null }), "FOCUS").view).toBe("WORLD");
        expect(setView(at({ view: "WORLD", node: "VG:X" }), "FOCUS").view).toBe("FOCUS");
    });

    it("does not write an undefined subject", () => {
        /* An index past the end of the label table yields `undefined`, and a `=== null` guard
           let that through to be written as a subject. */
        const state = selectSubject(at({ view: "FOCUS", node: "VG:X" }), undefined as never);
        expect(state.node).toBeNull();
    });

    it("does not abandon a trace when a stop on it is inspected", () => {
        const tracing = at({ view: "PATH", from: "VG:A", to: "VG:B" });
        const after = selectSubject(tracing, "VG:MIDDLE");
        expect(after.view).toBe("PATH");
        expect(after.from).toBe("VG:A");
        expect(after.to).toBe("VG:B");
    });
});

describe("nothing but an explicit request may change what is being explored", () => {
    /*
     * The mirror of the renderer table above, and the reason this phase exists.
     *
     * That table asserts "nothing the reader does to the graph may change the renderer" for
     * every mutator, in fourteen cases. The identical table for the *other* axis was never
     * written - and the axis nobody tested is the axis that broke. The previous phase was
     * reported as "interacting with the 3D graph sometimes returned them to a different view",
     * was diagnosed as a renderer problem, was fixed as a renderer problem, and was tested
     * exhaustively as a renderer problem. The reader kept losing their view.
     *
     * So: for every view, every mutator that is not about the view must leave it alone.
     */
    const cases: Array<[string, (state: GraphState) => GraphState]> = [
        ["selecting a subject", (s) => selectSubject(s, "VG:DEVATA:AGNIH")],
        ["clearing a subject", (s) => selectSubject(s, null)],
        ["selecting a constellation", (s) => selectRegion(s, 4)],
        ["clearing a constellation", (s) => selectRegion(s, null)],
        ["changing the renderer to 2d", (s) => setRenderer(s, "2d")],
        ["changing the renderer to 3d", (s) => setRenderer(s, "3d")],
    ];

    for (const view of VIEWS) {
        for (const [what, act] of cases) {
            /* Selecting a subject from WORLD is the one legitimate deepening, and it is the
               only exception in the table. Everything else must be inert. */
            if (view === "WORLD" && what === "selecting a subject") continue;
            it(`${what} keeps ${view}`, () => {
                const before = at({ view, node: "VG:DEVATA:INDRAH" });
                expect(act(before).view).toBe(view);
            });
        }
    }

    it("takes the world to focus when a subject is chosen, and only then", () => {
        expect(selectSubject(at({ view: "WORLD" }), "VG:X").view).toBe("FOCUS");
    });
});

describe("every cause of a state change is declared", () => {
    /*
     * The state model requires a reason on every write, and divides the reasons in two: the
     * reader acting, and everything else. Only the reader's half may move the semantic axis.
     *
     * That division is what makes the release blocker unrepresentable rather than merely
     * fixed. A physics tick, a settling simulation, a camera move, a hover, a frame sample and
     * a theme change are all absent from the union, which is the same thing as saying none of
     * them can do this - and a new one cannot be added without someone writing it down here.
     */
    it("counts the reader's causes and the system's separately", () => {
        expect(READER_INTENTS.every((reason) => isReaderIntent(reason))).toBe(true);
        expect(SYSTEM_CAUSES.some((reason) => isReaderIntent(reason))).toBe(false);
    });

    it("has no cause for a camera, a simulation, a hover or a theme", () => {
        const all = [...READER_INTENTS, ...SYSTEM_CAUSES].join(" ");
        for (const forbidden of ["camera", "physics", "settle", "hover", "theme", "frame"]) {
            expect(all).not.toContain(forbidden);
        }
    });

    it("allows a renderer failure to change the renderer and nothing else", () => {
        /* The only system cause that touches state at all after boot. It is not a reader
           intent, so the state owner refuses a view change from it even if one were computed. */
        expect(isReaderIntent("fallback:renderer-lost")).toBe(false);
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

describe("links written before the two-axis split still work", () => {
    /*
     * Found by the mobile audit, which reported that every pre-existing `?mode=` link had
     * become a silent fall-through to the default view. Those links were the shape every
     * shared and bookmarked graph URL took, so dropping them is a worse failure than the one
     * the refactor was done to fix.
     */
    const legacy = (search: string) => parseGraphState(new URLSearchParams(search));

    it("reads mode=world", () => {
        expect(legacy("mode=world").view).toBe("WORLD");
        expect(legacy("mode=world").renderer).toBe("3d");
    });

    it("reads mode=2d with a subject as a planar focus", () => {
        const state = legacy("mode=2d&node=VG%3ADEVATA%3AAGNIH");
        expect(state.renderer).toBe("2d");
        expect(state.view).toBe("FOCUS");
        expect(state.node).toBe("VG:DEVATA:AGNIH");
    });

    it("reads mode=3d with a subject as a spatial focus", () => {
        const state = legacy("mode=3d&node=VG%3ADEVATA%3AAGNIH");
        expect(state.renderer).toBe("3d");
        expect(state.view).toBe("FOCUS");
    });

    it("reads mode=path with endpoints", () => {
        const state = legacy("mode=path&from=VG%3AA&to=VG%3AB");
        expect(state.view).toBe("PATH");
        expect(state.from).toBe("VG:A");
    });

    it("never lets the old parameter contradict the new ones", () => {
        /* A URL carrying both is either hand-edited or half-rewritten. The explicit axes win;
           the legacy reader is a fallback, not a competing source. */
        const state = legacy("mode=2d&view=world&renderer=3d");
        expect(state.view).toBe("WORLD");
        expect(state.renderer).toBe("3d");
    });

    it("ignores a mode value that never existed", () => {
        expect(legacy("mode=hyperbolic").view).toBe("WORLD");
        expect(legacy("mode=hyperbolic").renderer).toBe("3d");
    });
});
