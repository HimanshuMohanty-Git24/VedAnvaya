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
    if (node === null) {
        return { ...state, node: null, view: state.view === "FOCUS" ? "WORLD" : state.view };
    }
    return {
        ...state,
        node,
        view: state.view === "PATH" ? "PATH" : "FOCUS",
    };
}

/** Select a constellation. Same rule: the renderer is not involved. */
export function selectRegion(state: GraphState, region: number | null): GraphState {
    return { ...state, region, node: region === null ? state.node : null };
}

export type Capability = "FULL_3D" | "REDUCED_3D" | "FLAT";

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

/** WORLD and PATH are both drawn spatially in 3D; FOCUS is the neighbourhood view. */
export function usesWorldGeometry(view: GraphView) {
    return view === "WORLD" || view === "PATH";
}
