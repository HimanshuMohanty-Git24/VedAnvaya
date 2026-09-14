/**
 * One graph product, four ways of looking at it.
 *
 * Before this there were two graph experiences: a 2D explorer at `/graph` that the rest of the
 * product linked to, and a 3D world at `/graph/world` that nothing linked to and nobody would
 * find. That is not two features, it is one feature and one orphan. The modes below are views
 * over a single piece of state - the same selection, the same search, the same path - so that
 * switching is a change of viewpoint rather than a change of application.
 *
 * The state lives in the URL, which makes every view of the graph a thing you can send to
 * someone. Camera position deliberately does not: it changes on every frame of an orbit, and a
 * link that restores an exact camera angle restores the one thing the recipient was going to
 * change first anyway.
 */

export const GRAPH_MODES = ["WORLD", "3D", "2D", "PATH"] as const;
export type GraphMode = (typeof GRAPH_MODES)[number];

export const MODE_COPY: Record<GraphMode, { label: string; note: string }> = {
    WORLD: {
        label: "World",
        note: "The whole corpus, arranged by what connects to what",
    },
    "3D": {
        label: "3D",
        note: "Free spatial exploration of one region",
    },
    "2D": {
        label: "2D",
        note: "A planar diagram you can pull apart",
    },
    PATH: {
        label: "Path",
        note: "How one subject reaches another",
    },
};

export type GraphState = {
    mode: GraphMode;
    /** Canonical id of the selected subject, not its index: indices change between builds. */
    node: string | null;
    /** Constellation id, when a region rather than a subject is in focus. */
    region: number | null;
    from: string | null;
    to: string | null;
    query: string | null;
};

export const EMPTY_STATE: GraphState = {
    mode: "WORLD",
    node: null,
    region: null,
    from: null,
    to: null,
    query: null,
};

function readMode(value: string | null): GraphMode | null {
    if (!value) return null;
    const upper = value.toUpperCase();
    return (GRAPH_MODES as readonly string[]).includes(upper) ? (upper as GraphMode) : null;
}

/**
 * Read graph state out of a URL.
 *
 * `?node=` is honoured without a mode, because every deep link written before this phase used
 * exactly that and those links are in the product's own pages. A node without a mode means a
 * subject someone wants to look at, which is 3D.
 */
export function parseGraphState(params: URLSearchParams): GraphState {
    const node = params.get("node");
    const from = params.get("from");
    const to = params.get("to");
    const explicit = readMode(params.get("mode"));
    const implied: GraphMode = from && to ? "PATH" : node ? "3D" : "WORLD";
    return {
        mode: explicit ?? implied,
        node,
        region: params.has("region") ? Number(params.get("region")) : null,
        from,
        to,
        query: params.get("q"),
    };
}

/** Only what differs from the default is written, so a shared link stays readable. */
export function graphStateToQuery(state: GraphState): string {
    const params = new URLSearchParams();
    if (state.mode !== "WORLD") params.set("mode", state.mode.toLowerCase());
    if (state.node) params.set("node", state.node);
    if (state.region !== null && Number.isFinite(state.region)) {
        params.set("region", String(state.region));
    }
    if (state.from) params.set("from", state.from);
    if (state.to) params.set("to", state.to);
    if (state.query) params.set("q", state.query);
    const query = params.toString();
    return query ? `?${query}` : "";
}

/**
 * What survives a change of mode.
 *
 * Everything that is about the graph rather than about the viewpoint. A reader who has found
 * Agni in the world and switches to 2D to pull its neighbourhood apart has not asked to go
 * back to the beginning, and the most common way a multi-view tool feels like several tools is
 * that each view starts over.
 *
 * The one thing that is dropped is a path's endpoints when leaving PATH, because a traced
 * route is a question that was asked and answered; carrying it into 2D would redraw an answer
 * nobody is looking at any more. The selected node is kept, so the reader arrives in the new
 * mode standing at one end of the path they were just reading.
 */
export function switchMode(state: GraphState, mode: GraphMode): GraphState {
    if (mode === state.mode) return state;
    const carried: GraphState = { ...state, mode };
    if (mode !== "PATH") {
        carried.from = null;
        carried.to = null;
    }
    if (mode === "PATH") {
        // Entering PATH from a selection offers that subject as the starting point, which is
        // almost always what someone means by tracing a path from where they are.
        carried.from = state.from ?? state.node;
    }
    return carried;
}

/**
 * Which mode a device should open in.
 *
 * Never used to override an explicit choice, and never silent: where this returns something
 * other than what was asked for, the interface says so and offers the other one. A reader on a
 * machine that cannot hold a frame rate is better served by a 2D diagram that works than by a
 * 3D one that stutters, but they are entitled to know that decision was made for them.
 */
export type Capability = "FULL_3D" | "REDUCED_3D" | "FLAT";

export function defaultModeFor(capability: Capability, requested: GraphMode | null): GraphMode {
    if (requested) return requested;
    return capability === "FLAT" ? "2D" : "WORLD";
}

export function isSpatial(mode: GraphMode) {
    return mode === "WORLD" || mode === "3D" || mode === "PATH";
}
