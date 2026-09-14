/**
 * What the reader is exploring, and how it is drawn. Two axes, never one.
 *
 * ## The bug this file was rewritten to fix
 *
 * The previous model had a single `mode` of WORLD | 3D | 2D | PATH, which mixes a semantic
 * level with a renderer, and that conflation was a release blocker rather than an
 * inelegance. WORLD was the default, so it was omitted from the URL; a URL carrying only
 * `?node=X` was then read back as 3D, because a bare subject looks like a request to go and
 * look at one. So selecting anything in the world wrote a URL that meant something different
 * from the state that wrote it, and the reader was moved into a view they had not asked for.
 * A round trip through the URL has to be lossless, and a state model where two different
 * states serialise identically cannot be.
 *
 * Split in two, the question does not arise. `view` says WORLD, FOCUS or PATH. `renderer`
 * says 3d or 2d. Selecting a subject changes `view`; nothing about selection can reach
 * `renderer`, which is the hard invariant this phase exists to establish.
 *
 * ## Precedence
 *
 * One owner, one order, written down so that effects cannot quietly disagree:
 *
 *   1. an explicit user action           - always wins, always remembered
 *   2. a valid deep link                 - what the URL says, if it says anything
 *   3. a remembered preference           - the reader's last explicit choice
 *   4. the capability default            - what this device can actually draw
 *
 * A runtime failure may override the renderer, and only the renderer, and only loudly.
 */

export const VIEWS = ["WORLD", "FOCUS", "PATH"] as const;
export type GraphView = (typeof VIEWS)[number];

export const RENDERERS = ["3d", "2d"] as const;
export type GraphRenderer = (typeof RENDERERS)[number];

/**
 * Why the state changed. Required on every write, and not decorative.
 *
 * ## The bug this exists to make impossible
 *
 * A reader who selected Indra and explored its neighbourhood was returned to the whole corpus
 * without asking to be. Three separate mechanisms could do it, and none of them recorded that
 * it had: a planar pan whose threshold never latched released into a cleared selection, the
 * spatial canvas never wrote a selection to the state at all so the view stayed WORLD
 * underneath a panel that said otherwise, and clearing a selection demoted FOCUS silently.
 *
 * The common property is that a state change had no stated cause. So a cause is now a
 * parameter, it is a closed union rather than a string, and `isReaderIntent` divides the
 * union in two. Only the reader's half may change `view`. Everything else - a boot, a
 * renderer failure, a history navigation - may change what it is entitled to change and is
 * refused if it reaches for the semantic axis.
 *
 * A physics tick, a settling simulation, a camera move, a hover, a theme change and a frame
 * sample are all absent from this union by design. There is no reason for them to be here,
 * which is the same thing as saying they may not change this state.
 */
export const READER_INTENTS = [
    /** The World / Focus / Path control. */
    "reader:view-control",
    /** The 3D / 2D control, or the offer in a fallback notice. */
    "reader:renderer-control",
    /** A subject picked out of a canvas, by tap or by keyboard. */
    "reader:select-subject",
    /** A subject picked from the panel, the search results or the relationship inspector. */
    "reader:select-listed",
    /** Escape, or an explicit close on the subject panel. */
    "reader:clear-selection",
    /** The explicit way back out of a subject - "see where it sits". */
    "reader:return-to-world",
    "reader:select-region",
    "reader:trace-path",
    "reader:search",
    /** The reader asked for more of a curated neighbourhood. */
    "reader:expand-neighbourhood",
] as const;

export const SYSTEM_CAUSES = [
    /** Once, on mount, when precedence between the URL, a preference and the device settles. */
    "boot:resolve-precedence",
    /** The browser moved through history, or another page linked in. Adopted, not fought. */
    "history:navigated",
    /** A lost WebGL context. May change the renderer and nothing else. */
    "fallback:renderer-lost",
] as const;

export type ReaderIntent = (typeof READER_INTENTS)[number];
export type SystemCause = (typeof SYSTEM_CAUSES)[number];
export type TransitionReason = ReaderIntent | SystemCause;

/** Whether this cause is the reader acting. The only kind that may move the semantic axis. */
export function isReaderIntent(reason: TransitionReason): reason is ReaderIntent {
    return (READER_INTENTS as readonly string[]).includes(reason);
}

export const VIEW_COPY: Record<GraphView, { label: string; note: string }> = {
    WORLD: { label: "World", note: "The whole corpus, arranged by what connects to what" },
    FOCUS: { label: "Focus", note: "One subject and what it is attached to" },
    PATH: { label: "Path", note: "How one subject reaches another" },
};

export const RENDERER_COPY: Record<GraphRenderer, { label: string; note: string }> = {
    "3d": { label: "3D", note: "Spatial, with depth" },
    "2d": { label: "2D", note: "Planar, and physical to the touch" },
};

export type GraphState = {
    view: GraphView;
    renderer: GraphRenderer;
    /** Canonical id, not an index: indices change between builds, ids do not. */
    node: string | null;
    /** Constellation id, when a region rather than a subject is in focus. */
    region: number | null;
    from: string | null;
    to: string | null;
    query: string | null;
};

export const DEFAULT_STATE: GraphState = {
    view: "WORLD",
    renderer: "3d",
    node: null,
    region: null,
    from: null,
    to: null,
    query: null,
};

function readView(value: string | null): GraphView | null {
    if (!value) return null;
    const upper = value.toUpperCase();
    return (VIEWS as readonly string[]).includes(upper) ? (upper as GraphView) : null;
}

function readRenderer(value: string | null): GraphRenderer | null {
    if (!value) return null;
    const lower = value.toLowerCase();
    return (RENDERERS as readonly string[]).includes(lower) ? (lower as GraphRenderer) : null;
}

/**
 * Read state out of a URL.
 *
 * Both axes are written explicitly by `graphStateToQuery`, so a URL this application produced
 * always states both and nothing is inferred. Inference exists only for a URL a person wrote
 * or was sent - `?node=X`, which every link in the product used before this phase - and it
 * only ever fills in what is absent. It can no longer contradict what is present, which is
 * the whole of the fix.
 */
/**
 * The previous single-axis `?mode=` parameter, translated.
 *
 * That parameter is gone, and links carrying it are not: they were the shape every shared and
 * bookmarked graph URL took before this phase. Dropping them would be a silent 404 into the
 * default view, which is a worse failure than the one this refactor was done to fix. Read only
 * when neither new axis is present, so it can never contradict an explicit request.
 */
function readLegacyMode(
    params: URLSearchParams,
    hasNode: boolean,
): { view: GraphView; renderer: GraphRenderer } | null {
    const legacy = params.get("mode");
    if (!legacy || params.has("view") || params.has("renderer")) return null;
    switch (legacy.toLowerCase()) {
        case "world":
            return { view: "WORLD", renderer: "3d" };
        case "3d":
            // `mode=3d` meant "look at this subject spatially", which is FOCUS with a node.
            return { view: hasNode ? "FOCUS" : "WORLD", renderer: "3d" };
        case "2d":
            return { view: hasNode ? "FOCUS" : "WORLD", renderer: "2d" };
        case "path":
            return { view: "PATH", renderer: "3d" };
        default:
            return null;
    }
}

export function parseGraphState(params: URLSearchParams): GraphState {
    const node = params.get("node");
    const from = params.get("from");
    const to = params.get("to");
    const region = params.has("region") ? Number(params.get("region")) : null;
    const legacy = readLegacyMode(params, Boolean(node));

    const view =
        readView(params.get("view")) ??
        legacy?.view ??
        (from && to ? "PATH" : node ? "FOCUS" : "WORLD");

    return {
        view,
        renderer: readRenderer(params.get("renderer")) ?? legacy?.renderer ?? DEFAULT_STATE.renderer,
        node,
        region: region !== null && Number.isFinite(region) ? region : null,
        from,
        to,
        query: params.get("q"),
    };
}

/**
 * Write state into a URL.
 *
 * Both axes are always written, even when they equal the default. That is the correction: a
 * shorter link is worth nothing next to a link that means what produced it, and omitting the
 * default was precisely how one state came to serialise as another.
 */
export function graphStateToQuery(state: GraphState): string {
    const params = new URLSearchParams();
    params.set("view", state.view.toLowerCase());
    params.set("renderer", state.renderer);
    if (state.node) params.set("node", state.node);
    if (state.region !== null && Number.isFinite(state.region)) {
        params.set("region", String(state.region));
    }
    if (state.from) params.set("from", state.from);
    if (state.to) params.set("to", state.to);
    if (state.query) params.set("q", state.query);
    return `?${params.toString()}`;
}

/**
 * Change what is being explored. The renderer is untouched, by construction.
 *
 * There is no code path from a view change to a renderer change, and that is deliberate
 * rather than incidental: the reported bug was exactly such a path existing by accident.
 */
export function setView(state: GraphState, view: GraphView): GraphState {
    if (view === state.view) return state;
    /*
     * Focus is about a subject, so focus without one is not a state.
     *
     * It was reachable, and it was half of the reported confusion: pressing Focus with nothing
     * selected wrote `view=focus&node=` - a view whose own copy promises "one subject and what
     * it is attached to" with no subject to show. The next write then computed from a state
     * that meant nothing and the control snapped back, which looked exactly like Focus
     * resetting itself. The control is disabled in the chrome for the same reason; this is the
     * floor under it, so no other caller can reach the state either.
     */
    if (view === "FOCUS" && !state.node) return state;
    const next: GraphState = { ...state, view };
    if (view !== "PATH") {
        next.from = null;
        next.to = null;
    } else {
        // Entering a trace from a selection offers that subject as the starting point, which
        // is almost always what "trace a path from here" means.
        next.from = state.from ?? state.node;
    }
    return next;
}

/** Change how it is drawn. Nothing about what is being explored moves. */
export function setRenderer(state: GraphState, renderer: GraphRenderer): GraphState {
    return renderer === state.renderer ? state : { ...state, renderer };
}

/**
 * Select a subject.
 *
 * Selecting deepens the view from WORLD to FOCUS, because that is what selecting means; it
 * cannot touch the renderer. Selecting while tracing a path leaves the trace alone - the
 * reader is inspecting a stop on the route, not abandoning it.
 */
export function selectSubject(state: GraphState, node: string | null): GraphState {
    /*
     * Clearing the subject clears the subject. It does not decide what the reader is exploring.
     *
     * This line used to read `view: state.view === "FOCUS" ? "WORLD" : state.view`, and that
     * conditional was the release blocker. It coupled "no subject" to "leave Focus", which made
     * every caller able to pass a null into an unauthorised writer of `view` - and one of them
     * was a tap on empty canvas. A reader panning the planar diagram slowly enough that no
     * single pointer event moved more than a pixel was classified as having clicked, the click
     * hit nothing, the nothing was passed through here, and a Focus session on Indra became the
     * whole projected corpus. Nobody had asked for the corpus.
     *
     * Leaving Focus is now a separate verb with a separate name, because it is a separate
     * decision. `returnToWorld` is called from the view control and from Escape, and from
     * nothing that can happen by accident.
     *
     * `node === null` rather than a falsy test on purpose: an out-of-range label lookup yields
     * `undefined`, and a `=== null` guard let that through to be written as a subject.
     */
    if (node === null || node === undefined) return { ...state, node: null };
    return {
        ...state,
        node,
        view: state.view === "PATH" ? "PATH" : "FOCUS",
    };
}

/**
 * Step back out to the whole corpus. The only thing that may leave Focus.
 *
 * Separate from clearing a selection so that the transition has exactly two callers - the view
 * control and the Escape key - and so that a reader reading this file can see that there are
 * only two. The subject is dropped with it: returning to the world while still holding one
 * would leave the panel open over a view that is no longer about it.
 */
export function returnToWorld(state: GraphState): GraphState {
    return { ...state, view: "WORLD", node: null, from: null, to: null };
}

/** Select a constellation. Same rule: the renderer is not involved. */
export function selectRegion(state: GraphState, region: number | null): GraphState {
    return { ...state, region, node: region === null ? state.node : null };
}

/**
 * What the device classifier concluded. Two classes, because two is all any consumer reads.
 *
 * There was a third, `REDUCED_3D`, for a device reporting two gigabytes or less. It never
 * reached the one branch below - `FLAT` against everything else - so the low-memory Android it
 * was written for opened in the same renderer as a workstation, and had done since the class was
 * added. The signal behind it cannot carry a tier either: `navigator.deviceMemory` is Chromium
 * and secure-context only, so it is absent on every browser on iOS and in Firefox, and where it
 * is present it reports installed RAM quantised to a power of two rather than anything about the
 * GPU. A class that fires on some cheap Androids and on no iPhone at all is not a
 * reduced-capability path; it is a Chromium path with a misleading name.
 *
 * If a per-device budget is wanted, key it on viewport area, which every device reports
 * honestly. See `capability.ts`.
 */
export type Capability = "FULL_3D" | "FLAT";

/**
 * The renderer to open with, when the reader has not said.
 *
 * Never consulted where the URL or a remembered preference has an answer; this is the last
 * rung of the precedence ladder, not the first.
 */
export function defaultRendererFor(capability: Capability): GraphRenderer {
    return capability === "FLAT" ? "2d" : "3d";
}

/**
 * Resolve the opening state from every source, in one place.
 *
 * Written as a single function returning one answer, rather than as effects that each write
 * part of the state, because effects that each write part of the state are how the previous
 * version ended up with the URL, a classifier and a stored preference disagreeing about which
 * view the reader was in.
 */
export function resolveInitialState({
    url,
    remembered,
    capability,
}: {
    url: URLSearchParams;
    remembered: GraphRenderer | null;
    capability: Capability;
}): { state: GraphState; rendererSource: "url" | "remembered" | "capability" } {
    const parsed = parseGraphState(url);
    if (url.has("renderer")) {
        return { state: parsed, rendererSource: "url" };
    }
    if (remembered) {
        return { state: { ...parsed, renderer: remembered }, rendererSource: "remembered" };
    }
    return {
        state: { ...parsed, renderer: defaultRendererFor(capability) },
        rendererSource: "capability",
    };
}

