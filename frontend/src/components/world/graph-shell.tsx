"use client";

import Link from "next/link";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { encoded } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";
import {
    describeSubject,
    loadWorld,
    loadWorldLabels,
    type World,
    type WorldLabels,
} from "@/lib/world/artifact";
import type { WorldEngine } from "@/lib/world/engine";
import { useGraphState } from "@/lib/world/graph-state";
import {
    RENDERERS,
    RENDERER_COPY,
    VIEWS,
    VIEW_COPY,
    type ReaderIntent,
} from "@/lib/world/modes";
import {
    FAMILY_COPY,
    FOCUS_EXPAND_STEP,
    expandFocusBudget,
    focusBudgetForBand,
    useFocusNeighbourhood,
} from "@/lib/world/focus";
import { usePredicateSemantics } from "@/lib/world/predicates";
import { RelationshipInspector } from "./relationship-inspector";
import { PathTrace } from "./path-trace";
import { PlanarView } from "./planar-view";
import { WorldView } from "./world-view";

/**
 * One graph, on two axes.
 *
 * What the reader is exploring - the world, one subject, a route between two - and how it is
 * drawn. They were one control and one state field, and that conflation was a release
 * blocker: a URL written while looking at the world read back as a request for a different
 * renderer, so selecting anything moved the reader somewhere they had not asked to go.
 *
 * All state now comes from `useGraphState`, which owns the precedence between the URL, a
 * remembered preference and what the device can draw, and resolves it once. Nothing in this
 * component writes to the URL directly, and there is no path from a selection to a renderer.
 */

const GROUP_LABEL: Record<string, string> = {
    deity: "Deity",
    "unresolved-deity": "Unresolved devata slot",
    passage: "Passage",
    person: "Seer",
    idea: "Idea",
    rite: "Rite",
    thing: "Thing",
    wording: "Wording",
    derived: "Derived metric",
    record: "Evidence record",
    other: "Other",
};

function fold(value: string) {
    return value
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();
}

type Hit = { index: number; label: string; group: string };

/**
 * How many subjects the non-visual alternative names before a reader has searched.
 *
 * The artifact's hub index holds six hundred, ordered by connectedness and with passages and
 * reified records already held out of it. Sixty is enough to be a genuine way into the corpus and
 * short enough to be read rather than skipped.
 */
const HUB_ALTERNATIVE_COUNT = 60;

type SheetHeight = "collapsed" | "half" | "expanded";

/** The cycle, written once so the control and its label cannot disagree about what is next. */
const SHEET_NEXT: Record<SheetHeight, SheetHeight> = {
    collapsed: "half",
    half: "expanded",
    expanded: "collapsed",
};

const SHEET_COPY: Record<SheetHeight, string> = {
    collapsed: "Show less",
    half: "Show more",
    expanded: "Show all of it",
};

export function GraphShell() {
    const graph = useGraphState();
    const { state } = graph;

    const [world, setWorld] = useState<World | null>(null);
    const predicates = usePredicateSemantics();
    const [labels, setLabels] = useState<WorldLabels | null>(null);
    const [engine, setEngine] = useState<WorldEngine | null>(null);
    const [query, setQuery] = useState(state.query ?? "");
    const [pathNodes, setPathNodes] = useState<number[]>([]);
    const [pathHops, setPathHops] = useState<string[]>([]);
    /*
     * Where focus goes after a selection made from the keyboard.
     *
     * Measured before this: choosing a neighbour dropped focus to `<body>` on every hop, in both
     * renderers, because the list is keyed by node index and React unmounts the focused button
     * when the panel is rebuilt for the new subject. Neighbour traversal is the main keyboard
     * route through the graph, so it lost the reader once per step. Focus is moved deliberately
     * to the new subject's heading, which is also the right announcement.
     */
    const headingRef = useRef<HTMLHeadingElement>(null);
    const moveFocus = useRef(false);
    /*
     * How much of the phone screen the subject panel is taking.
     *
     * Only meaningful at narrow widths, where the panel is a sheet at the foot. It opens
     * collapsed so that choosing a subject does not bury it: the camera flies the selection to
     * the middle of the canvas, and a half-height sheet sits exactly there.
     */
    /*
     * How much of the canvas the chrome is sitting on.
     *
     * Measured from the live layout rather than assumed from the breakpoint, because the band's
     * height depends on what is in it - in PATH it carries two fields and a paragraph of caveats,
     * and a search with results is taller again. The camera uses this to frame a chosen subject
     * into the part of the canvas a reader can actually see.
     */
    const [safeArea, setSafeArea] = useState({ top: 0, right: 0, bottom: 0, left: 0 });
    /** The stage, measured. Written by the same observer that measures the chrome. */
    const [stageSize, setStageSize] = useState({ width: 0, height: 0 });
    const stageRef = useRef<HTMLDivElement>(null);

    const [sheetState, setSheetState] = useState<{
        at: string;
        height: SheetHeight;
    } | null>(null);
    const [hintDismissed, setHintDismissed] = useState(false);
    const deferred = useDeferredValue(query);

    const indexOfId = useCallback(
        (id: string | null) => {
            if (!id || !labels) return null;
            const index = labels.ids.indexOf(id);
            return index >= 0 ? index : null;
        },
        [labels],
    );

    /*
     * The selected subject, derived from the state rather than stored beside it.
     *
     * There used to be a `useState` here, written by the spatial canvas through an event. So
     * the panel was driven by what the canvas had said and the view control by what the URL
     * said, and the two were free to disagree - which they did, in both directions. Nothing is
     * kept in step now because there is nothing to keep in step: the id is in the state, and
     * every surface reads the same description from it.
     */
    const selectedIndex = indexOfId(state.node);
    const selection = useMemo(
        () =>
            world && selectedIndex !== null ? describeSubject(world, labels, selectedIndex) : null,
        [world, labels, selectedIndex],
    );

    /*
     * Selecting deepens the view. It cannot touch the renderer.
     *
     * Structural rather than careful: there is no call to `setRenderer` reachable from here,
     * and the state model refuses one anyway. What it *must* do, and did not, is write to the
     * state at all - the spatial canvas used to route a selection into a local variable and
     * leave the record of state saying the reader was looking at the whole corpus.
     *
     * The reason is a parameter because the state model requires one. A selection from a canvas
     * and a selection from a list are both the reader, and both say which they were.
     */
    const selectNode = useCallback(
        (node: number | null, reason: ReaderIntent) => {
            /* `?? null` rather than a truthy test: an index past the end of the label table
               yields `undefined`, and `undefined` written as a subject is a Focus on nothing. */
            const id = node !== null && labels ? (labels.ids[node] ?? null) : null;
            if (id === null) return;
            graph.select(id, reason);
        },
        [labels, graph],
    );

    /**
     * Step back out to the whole corpus.
     *
     * The only thing that leaves Focus, and it has exactly two callers: the World control and
     * the Escape key. Both are the reader saying so, which is the whole requirement.
     */
    const leaveFocus = useCallback(
        () => graph.returnToWorld("reader:clear-selection"),
        [graph],
    );

    /*
     * The engine is told which semantic view it is in.
     *
     * `setMode` existed on the engine and was called from nowhere: the field it writes was
     * initialised to WORLD and never moved, so World and Focus were rendered identically in
     * the spatial view and "Focus" was a camera position with some dimming. That is the other
     * half of the reported complaint - not only did Focus reset, it was never a mode.
     */
    useEffect(() => {
        engine?.setMode(state.view);
    }, [engine, state.view]);

    /*
     * The page reads the artifact itself, rather than being handed it by one of the canvases.
     *
     * It used to take `world` and `labels` from the spatial view's ready callback, which made
     * the planar canvas unmountable until the *3D* engine had finished starting - so a cold
     * `?renderer=2d` link waited on a renderer it was never going to use, and on the 1.9 MB
     * label file besides. The fallback renderer is the one a weak device is sent to; making it
     * queue behind WebGL is the worst available first impression.
     *
     * The loaders are memoised, so asking here costs nothing: both callers share one fetch and
     * one decode of the 185,693-edge adjacency index.
     */
    useEffect(() => {
        const controller = new AbortController();
        void (async () => {
            try {
                const loaded = await loadWorld(controller.signal);
                if (controller.signal.aborted) return;
                setWorld(loaded);
                const loadedLabels = await loadWorldLabels(controller.signal);
                if (controller.signal.aborted) return;
                setLabels(loadedLabels);
            } catch {
                /* The canvases report their own failure with the detail a reader needs; a
                   second notice from here would say the same thing twice. */
            }
        })();
        return () => controller.abort();
    }, []);

    /** The spatial engine, once it exists. The geometry no longer arrives with it. */
    const onReady = useCallback(
        (_loaded: World, _loadedLabels: WorldLabels, loadedEngine: WorldEngine) => {
            setEngine(loadedEngine);
        },
        [],
    );

    /* ------------------------------------------------------------ search - */

    const hits = useMemo<Hit[]>(() => {
        const needle = fold(deferred.trim());
        if (!world || !labels || needle.length < 2) return [];
        const out: Hit[] = [];
        const seen = new Set<number>();
        // Hubs first, so two letters surface Indra before a verse containing the same letters.
        const order = [
            ...world.manifest.hubs,
            ...Array.from({ length: labels.labels.length }, (_, i) => i),
        ];
        for (const index of order) {
            if (out.length >= 20) break;
            if (seen.has(index)) continue;
            seen.add(index);
            const label = labels.labels[index];
            if (!label || !fold(label).includes(needle)) continue;
            out.push({ index, label, group: world.manifest.groups[world.nodeGroup[index]] });
        }
        return out;
    }, [deferred, world, labels]);

    /*
     * How many connections the reader has asked to see.
     *
     * Derived against the subject it was raised for, like the sheet height and the inspected
     * relationship, so a new subject opens at the default without an effect racing the
     * selection to reset it.
     */
    const [expansion, setExpansion] = useState<{ at: string; budget: number } | null>(null);

    /*
     * The budget, from the band the reader can actually see.
     *
     * Not from the viewport: the chrome takes the top of the canvas and the sheet takes the
     * foot, and on a phone what is left is under half of it. `focusBudgetForBand` derives the
     * seat count from a 44 px touch pitch around the shorter axis rather than thresholding on a
     * width, so a short desktop band is treated as the short band it is.
     */
    const stageBand = useMemo(() => {
        /* Before the first measurement the stage has no size, and a budget derived from zero
           would be the floor rather than the default. A desktop-shaped guess is the honest
           placeholder: the observer corrects it within a frame, and nothing is drawn yet. */
        const width = stageSize.width || 1440;
        const height = stageSize.height || 900;
        return { width, height: Math.max(120, height - safeArea.top - safeArea.bottom) };
    }, [stageSize, safeArea]);

    const defaultBudget = focusBudgetForBand(stageBand.width, stageBand.height);
    const budget =
        expansion?.at === (state.node ?? "") ? expansion.budget : defaultBudget;

    /**
     * The curated neighbourhood. One computation, read by every surface.
     *
     * Both canvases, this panel, the counts and the non-visual list all read *this*, because
     * five callers each deriving their own is how a canvas and a panel come to disagree about
     * what a subject is attached to. It is memoised and must never be reached from a frame
     * callback: the cost is proportional to the subject's degree, not to the budget, so the
     * compact mobile budget looks like the cheap path and is not.
     */
    const focus = useFocusNeighbourhood({
        world,
        labels,
        root: state.view === "FOCUS" ? selectedIndex : null,
        budget,
    });

    /*
     * The list beside the canvas is the canvas, in words.
     *
     * It used to rank the whole adjacency by degree and take the first forty, which meant the
     * panel and the diagram were two different answers to the same question - and the panel was
     * the clearer of the two, which a reviewer noticed and reported as the graph being worse
     * than its own sidebar. They are one answer now. A neighbour that is on screen says so, and
     * the ones past the budget are reached by asking for more rather than by scrolling a
     * thousand rows in a narrow pane.
     */
    const neighbourRows = useMemo(() => {
        if (!focus || !world || !labels) return [];
        return focus.shown.map((neighbour) => ({
            index: neighbour.node,
            label: neighbour.label || neighbour.id,
            group: neighbour.group,
            degree: neighbour.degree,
            /* Why the curation kept it. Shown to nobody; useful in a review, and the reason the
               selection records one at all. */
            reason: neighbour.reason,
        }));
    }, [focus, world, labels]);

    const constellation = useMemo(() => {
        if (!selection || !world?.manifest.constellations) return null;
        const region = world.nodeRegion[selection.index];
        if (region === 65535) return null;
        return world.manifest.constellations[region] ?? null;
    }, [selection, world]);

    useEffect(() => {
        if (!moveFocus.current) return;
        moveFocus.current = false;
        headingRef.current?.focus();
    });


    /* The renderer decides which stage is shown; the view decides what it is showing. */
    const spatial = state.renderer === "3d";
    /*
     * Which relationship is being explained.
     *
     * Not in the URL: it is a reading aid attached to a subject the URL already names, not a
     * place in the corpus you would send someone to.
     *
     * Stored with the state it was opened against and *derived* stale, rather than cleared by an
     * effect watching the subject. An effect would be a second writer racing the first, and this
     * file exists because four of those once disagreed about which view the reader was in.
     */
    const [inspected, setInspected] = useState<{ edge: number; at: string } | null>(null);

    /* A relationship belongs to the subject and the view it was opened from. Move either and it
       is no longer the thing on screen, so it simply stops being current. */
    /* Derived against the subject it was raised for, so a new subject opens collapsed without an
       effect racing the selection to reset it. */
    const sheet = sheetState?.at === (state.node ?? "") ? sheetState.height : "collapsed";

    const inspectedAt = `${state.node ?? ""}|${state.view}|${state.renderer}`;
    const inspectedEdge = inspected?.at === inspectedAt ? inspected.edge : null;
    const inspectEdge = useCallback(
        (edge: number | null) => setInspected(edge === null ? null : { edge, at: inspectedAt }),
        [inspectedAt],
    );

    /*
     * Escape steps back out.
     *
     * The panel has up to forty-four focusable controls and had no dismissal at all, so a
     * keyboard reader who opened a subject had to tab through the whole of it to reach anything
     * else. The relationship explanation closes first, because it was opened last.
     *
     * Rebound whenever those change rather than reading them from refs: a listener that closes
     * over a stale selection is the same class of bug as two effects disagreeing about state,
     * and rebinding one key handler costs nothing.
     */
    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== "Escape") return;
            if (inspectedEdge !== null) {
                inspectEdge(null);
                return;
            }
            if (selection) leaveFocus();
        };
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [inspectedEdge, inspectEdge, selection, leaveFocus]);

    /*
     * Remeasured whenever the chrome can have changed size.
     *
     * A ResizeObserver on both pieces rather than a listener on the window: the band grows when
     * a search returns results and the sheet grows when the reader raises it, and neither is a
     * window resize. Only the top and bottom are reported - on a wide screen the panel is a rail
     * on one side, and shifting the camera sideways for it would be worse than leaving it.
     */
    useEffect(() => {
        const stage = stageRef.current;
        if (!stage) return;

        const measure = () => {
            const bounds = stage.getBoundingClientRect();
            if (bounds.width === 0 || bounds.height === 0) return;
            /* Recorded here because the observer already has the box, and because the neighbour
               budget is computed from it. Read from the ref during render instead, it would be a
               size React does not know changed - so a rotation or a raised sheet would leave the
               budget describing the previous layout. */
            setStageSize((current) =>
                current.width === Math.round(bounds.width) &&
                current.height === Math.round(bounds.height)
                    ? current
                    : { width: Math.round(bounds.width), height: Math.round(bounds.height) },
            );
            const narrow = bounds.width < 768;
            if (!narrow) {
                setSafeArea((current) =>
                    current.top === 0 && current.bottom === 0
                        ? current
                        : { top: 0, right: 0, bottom: 0, left: 0 },
                );
                return;
            }
            const heightOf = (selector: string) => {
                const node = stage.querySelector(selector);
                if (!node) return 0;
                const box = node.getBoundingClientRect();
                return box.height > 0 ? box.height : 0;
            };
            const next = {
                top: Math.round(heightOf(".va-graph-chrome")),
                right: 0,
                bottom: Math.round(heightOf(".va-world-panel")),
                left: 0,
            };
            setSafeArea((current) =>
                current.top === next.top && current.bottom === next.bottom ? current : next,
            );
        };

        measure();
        const observer = new ResizeObserver(measure);
        observer.observe(stage);
        for (const selector of [".va-graph-chrome", ".va-world-panel"]) {
            const node = stage.querySelector(selector);
            if (node) observer.observe(node);
        }
        return () => observer.disconnect();
    }, [selection, sheet, state.view]);

    return (
        <div
            className="va-graph"
            data-renderer={state.renderer}
            data-view={state.view}
            ref={stageRef}
        >
            {/* The spatial engine is mounted once and kept mounted across every change. A
                canvas that unmounts loses its context, its buffers and its camera, and a
                renderer switch would mean a blank flash and a reload of a 2 MB artifact. */}
            <div className="va-graph-stage" data-active={spatial}>
                <WorldView
                    onReady={onReady}
                    onRendererLost={(detail) =>
                        graph.reportRendererFailure("context-lost", detail)
                    }
                    onInspectEdge={inspectEdge}
                    /*
                     * A tap on a subject is a selection and goes into the record of state like
                     * every other. A tap on the background is not a request to leave the
                     * subject the reader is reading, so it does nothing at all: conflating
                     * those two is what returned a reader exploring Indra to the whole corpus.
                     */
                    onTap={(node) => node !== null && selectNode(node, "reader:select-subject")}
                    selectedIndex={selectedIndex}
                    pathHops={pathHops}
                    pathNodes={pathNodes}
                    safeArea={safeArea}
                    paused={!spatial}
                />
            </div>

            {state.renderer === "2d" && world && (
                <div className="va-graph-stage is-planar" data-active>
                    {/* The view decides what the planar canvas draws; the renderer only
                        decided that it is the one drawing. World and Focus are the same two
                        semantic levels here as in the spatial view. */}
                    <PlanarView
                        labels={labels}
                        /* The safe area was measured for both renderers and passed to one. So in
                           the planar view a chosen subject was centred in the whole canvas, which
                           on a phone is behind the sheet - at every one of its three heights. */
                        safeArea={safeArea}
                        onInspectEdge={inspectEdge}
                        onSelect={(node) => selectNode(node, "reader:select-subject")}
                        root={selectedIndex}
                        scope={state.view === "FOCUS" && selectedIndex !== null ? "focus" : "world"}
                        world={world}
                    />
                </div>
            )}

            <RelationshipInspector
                edge={inspectedEdge}
                labels={labels}
                onClose={() => inspectEdge(null)}
                onSelect={(node) => {
                    inspectEdge(null);
                    selectNode(node, "reader:select-listed");
                }}
                predicates={predicates}
                world={world}
            />

            {/*
             * What the canvas cannot say.
             *
             * The spatial canvas carried an `aria-label` promising "a searchable,
             * keyboard-navigable list of the same nodes" and, with nothing selected, measurement
             * found no list, no node buttons and no hidden text anywhere in the view - the list
             * only existed once you had already found something. A screen reader met a search box
             * and 35,370 unreachable subjects.
             *
             * The artifact ships an index of its most connected subjects for exactly this kind of
             * question, so it is rendered as real links. Not the whole graph - thirty-five
             * thousand list items would be its own kind of unusable - but a way in that exists
             * before the reader has guessed a name.
             */}
            {!selection && world && labels && (
                <div className="sr-only">
                    <h2>The most connected subjects</h2>
                    <p>
                        {world.manifest.counts.nodes.toLocaleString("en-GB")} subjects are drawn on
                        the map. These are the {HUB_ALTERNATIVE_COUNT} with the most connections;
                        search above to reach any of the others.
                    </p>
                    <ul>
                        {world.manifest.hubs.slice(0, HUB_ALTERNATIVE_COUNT).map((hub) => (
                            <li key={hub}>
                                <button onClick={() => selectNode(hub, "reader:select-listed")} type="button">
                                    {labels.labels[hub] || labels.ids[hub]}
                                </button>
                                , {world.manifest.groups[world.nodeGroup[hub]]},{" "}
                                {world.nodeDegree[hub].toLocaleString("en-GB")} connections
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/*
             * Selection, announced once.
             *
             * Choosing a subject replaces most of the page and, measured, said nothing at all -
             * there was no live region anywhere in the view. This is deliberately one short
             * sentence written only when the subject changes: an earlier region in this product
             * announced a running clock every second, and the lesson taken from it was that a
             * live region must carry an event, not a state.
             */}
            <p aria-live="polite" className="sr-only" role="status">
                {/*
                  * What was selected, and how much of it is on screen.
                  *
                  * The second sentence is the addition, and it is not decoration. The drawn view
                  * is curated, so a reader who cannot see the canvas is told what exists AND how
                  * much of it was chosen for display - the same two figures the panel shows.
                  * Announcing only the recorded count would describe a view nobody is looking
                  * at; announcing only the drawn count would understate the corpus.
                  */}
                {selection
                    ? `${selection.label || selection.id} selected. ` +
                      `${selection.degree.toLocaleString("en-GB")} recorded connections to ` +
                      `${selection.neighbours.length.toLocaleString("en-GB")} subjects.` +
                      (focus
                          ? focus.truncated
                              ? ` ${focus.shown.length} of them are drawn; the rest are in the list beside the map.`
                              : ` All of them are drawn.`
                          : "")
                    : ""}
            </p>

            {/* ------------------------------------------------------ chrome - */}

            <div className="va-graph-chrome">
                <header className="va-graph-head">
                    <p className="va-graph-kicker">The knowledge world</p>
                    <h1>
                        {world
                            ? `${world.manifest.counts.nodes.toLocaleString("en-GB")} subjects, connected`
                            : "The corpus, connected"}
                    </h1>
                </header>

                {/*
                 * Two rows, because there are two questions.
                 *
                 * The previous version put World, 3D, 2D and Path on one line, which said the
                 * four were alternatives - and the state behind it believed that too, which is
                 * what let a selection change the renderer. Separating them on screen is the
                 * same correction as separating them in the model.
                 */}
                <div className="va-graph-switch">
                    <nav aria-label="What to explore" className="va-graph-modes">
                        {VIEWS.map((view) => (
                            <button
                                aria-current={state.view === view ? "true" : undefined}
                                key={view}
                                /* Focus is about a subject, so the control is inert without
                                   one rather than writing a view that means nothing. */
                                disabled={view === "FOCUS" && !state.node}
                                onClick={() =>
                                    view === "WORLD"
                                        ? graph.returnToWorld("reader:view-control")
                                        : graph.setView(view, "reader:view-control")
                                }
                                title={VIEW_COPY[view].note}
                                type="button"
                            >
                                {VIEW_COPY[view].label}
                            </button>
                        ))}
                    </nav>
                    <nav aria-label="How it is drawn" className="va-graph-modes is-renderer">
                        {RENDERERS.map((renderer) => (
                            <button
                                aria-current={state.renderer === renderer ? "true" : undefined}
                                key={renderer}
                                onClick={() => graph.setRenderer(renderer, "reader:renderer-control")}
                                title={RENDERER_COPY[renderer].note}
                                type="button"
                            >
                                {RENDERER_COPY[renderer].label}
                            </button>
                        ))}
                    </nav>
                </div>

                {state.view !== "PATH" && (
                    <form
                        className="va-world-find"
                        onSubmit={(event) => {
                            event.preventDefault();
                            if (hits[0]) selectNode(hits[0].index, "reader:search");
                        }}
                        role="search"
                    >
                        <label htmlFor="graph-find">Find a subject</label>
                        <input
                            autoComplete="off"
                            id="graph-find"
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="A deity, a seer, an idea…"
                            type="search"
                            value={query}
                        />
                        {hits.length > 0 && (
                            <ul className="va-world-hits">
                                {hits.map((hit) => (
                                    <li key={hit.index}>
                                        <button onClick={() => selectNode(hit.index, "reader:search")} type="button">
                                            <span className="va-world-hit-name">{hit.label}</span>
                                            <span className="va-world-hit-kind">
                                                {GROUP_LABEL[hit.group] ?? hit.group}
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                        {deferred.trim().length >= 2 && hits.length === 0 && world && (
                            <p className="va-world-nohits">
                                No subject in this build answers to that. That is a limit of what
                                is held here, not a statement about the Vedas.
                            </p>
                        )}
                    </form>
                )}

                {state.view === "PATH" && world && (
                    <PathTrace
                        from={state.from}
                        labels={labels}
                        onEndpoints={(from, to) => graph.setEndpoints(from, to, "reader:trace-path")}
                        onPathNodes={(nodes, hops) => {
                            setPathNodes(nodes);
                            setPathHops(hops);
                        }}
                        to={state.to}
                        world={world}
                    />
                )}

                {/* A renderer chosen for the reader always says so and always offers the other
                    one. Nothing about how this graph is drawn changes quietly. */}
                {graph.fallback && (
                    <p className="va-graph-notice" role="status">
                        Drawing this flat: {graph.fallback.detail}.{" "}
                        <button onClick={() => graph.setRenderer("3d", "reader:renderer-control")} type="button">
                            Use the spatial view anyway
                        </button>
                    </p>
                )}

                {!hintDismissed && world && spatial && !selection && (
                    <p className="va-graph-hint">
                        {/* Two sentences because there are two devices. The previous copy said
                            "scroll to move through depth" to every reader, including the ones
                            holding a phone, which has no wheel and whose canvas refuses the
                            page its scroll. */}
                        <span className="va-graph-hint-fine">
                            Drag to orbit, scroll to move through depth, select to follow a
                            connection.
                        </span>
                        <span className="va-graph-hint-coarse">
                            Drag to turn it, pinch to move through depth, tap a subject to
                            follow its connections.
                        </span>
                        <button onClick={() => setHintDismissed(true)} type="button">
                            Got it
                        </button>
                    </p>
                )}
            </div>

            {/* ------------------------------------------------------- panel - */}

            {selection && (
                <aside
                    aria-label="The selected subject"
                    className="va-world-panel"
                    data-sheet={sheet}
                >
                    {/*
                      * The heading is a heading, and the control is a control.
                      *
                      * The h2 used to be a child of the handle button, and the intent was good -
                      * "the name you are reading is the control, no new furniture". But a button
                      * has presentational children in ARIA, so the heading was not exposed as one
                      * at all: the panel had no heading in the structure, the accessible name
                      * collapsed to "Deity Indra", and `headingRef.current?.focus()` - the fix
                      * that stops keyboard traversal dropping focus to the body on every hop -
                      * was moving focus onto a non-interactive element nested inside a button.
                      *
                      * Also `aria-expanded` is boolean and this control has three states, so it
                      * reported "expanded" at half height. The state is named in words instead,
                      * which is both true and more use than a boolean would have been.
                      */}
                    <div className="va-world-sheet-head">
                        <p className="va-world-panel-kind">
                            {GROUP_LABEL[selection.group] ?? selection.group}
                        </p>
                        <h2 ref={headingRef} tabIndex={-1}>
                            {selection.label || selection.id}
                        </h2>
                        <button
                            className="va-world-sheet-handle"
                            onClick={() =>
                                setSheetState({
                                    at: state.node ?? "",
                                    height: SHEET_NEXT[sheet],
                                })
                            }
                            type="button"
                        >
                            {SHEET_COPY[SHEET_NEXT[sheet]]}
                        </button>
                    </div>

                    {constellation && (
                        <p className="va-world-region">
                            in {constellation.name ?? `Constellation ${constellation.id}`}
                            <span>
                                {constellation.size.toLocaleString("en-GB")} subjects
                                {constellation.veda && constellation.veda.share >= 0.6
                                    ? `, mostly ${constellation.veda.name}`
                                    : ""}
                            </span>
                        </p>
                    )}

                    {/*
                      * Three figures, because they are three different things.
                      *
                      * The panel used to show one, "Recorded connections", and the list below it
                      * was headed "40 of 7,347" - which compares a count of subjects against a
                      * count of edges. They are not the same quantity: 1,803 of Indra's pairs
                      * are joined by two relationships, so the degree overstates the number of
                      * things by a fifth, and the fraction was nonsense in the reader's
                      * favour.
                      *
                      * And the drawn view is now curated, so the difference between what exists
                      * and what is on screen has to be on the page. A reader who sees forty orbs
                      * and no figure saying otherwise will conclude there are forty.
                      */}
                    <dl className="va-world-facts">
                        <div>
                            <dt>Recorded connections</dt>
                            <dd>{selection.degree.toLocaleString("en-GB")}</dd>
                        </div>
                        <div>
                            <dt>Connected subjects</dt>
                            <dd>{selection.neighbours.length.toLocaleString("en-GB")}</dd>
                        </div>
                        {focus && (
                            <div>
                                <dt>Shown in this view</dt>
                                <dd>
                                    {focus.shown.length.toLocaleString("en-GB")}
                                    {focus.truncated ? "" : " (all of them)"}
                                </dd>
                            </div>
                        )}
                        <div>
                            <dt>Type</dt>
                            <dd>{selection.type}</dd>
                        </div>
                    </dl>

                    <div className="va-world-ways">
                        {selection.group === "passage" ? (
                            <Link href={`/passage/${encoded(selection.id)}`}>
                                Read the passage
                            </Link>
                        ) : (
                            selection.id.startsWith("VG:") && (
                                <Link href={entityHref(selection.type, selection.id)}>
                                    Open the record
                                </Link>
                            )
                        )}
                        {/* Changing how the graph is drawn is the reader asking for it, so it
                            is remembered like any other explicit choice. */}
                        {/*
                          * Named for what it does.
                          *
                          * This button read "Pull its connections apart", which describes a
                          * spatial action on the neighbourhood. It switches the renderer. A
                          * control whose label promises one thing and performs another is worse
                          * than a plainly-named one, and re-spacing a neighbourhood is a real
                          * action that deserves its own name rather than borrowing this one.
                          */}
                        <button onClick={() => graph.setRenderer(spatial ? "2d" : "3d", "reader:renderer-control")} type="button">
                            {spatial ? "Lay it out flat" : "See it in space"}
                        </button>
                        <button
                            onClick={() => graph.setEndpoints(selection.id, state.to, "reader:trace-path")}
                            type="button"
                        >
                            Trace a path from here
                        </button>
                        <Link href={`/ask?entity=${encodeURIComponent(selection.id)}`}>
                            Ask about this
                        </Link>
                    </div>

                    {neighbourRows.length > 0 && (
                        <section className="va-world-neighbours">
                            <h3>
                                On screen
                                <span>
                                    {/* Subjects against subjects. The previous version read
                                        "40 of 7,347", which set a count of things against a
                                        count of relationships. */}
                                    {focus?.truncated
                                        ? `${neighbourRows.length} of ${focus.total.toLocaleString("en-GB")}`
                                        : `all ${neighbourRows.length}`}
                                </span>
                            </h3>
                            <ul>
                                {neighbourRows.map((row) => (
                                    <li key={row.index}>
                                        <button
                                            onClick={() => {
                                                moveFocus.current = true;
                                                selectNode(row.index, "reader:select-listed");
                                            }}
                                            type="button"
                                        >
                                            <span className="va-world-hit-name">{row.label}</span>
                                            <span className="va-world-hit-kind">
                                                {GROUP_LABEL[row.group] ?? row.group}
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                            {neighbourRows.length < selection.degree && (
                                <p className="va-world-neighbours-note">
                                    The most connected are listed first. The rest are on the
                                    record page.
                                </p>
                            )}
                            {/*
                              * More, in a step, from the same rounds.
                              *
                              * Deliberately not "show everything": a subject with seven thousand
                              * connections has no readable everything, and the tiers are nested
                              * because the previous set is pinned - so nothing a reader was
                              * already looking at disappears when they ask for more. That
                              * guarantee is what makes this safe to press twice.
                              */}
                            {focus?.truncated && (
                                <button
                                    className="va-world-more"
                                    onClick={() =>
                                        setExpansion({
                                            at: state.node ?? "",
                                            budget: expandFocusBudget(budget),
                                        })
                                    }
                                    type="button"
                                >
                                    Show {FOCUS_EXPAND_STEP} more
                                    <span>
                                        {(focus.total - neighbourRows.length).toLocaleString(
                                            "en-GB",
                                        )}{" "}
                                        not shown
                                    </span>
                                </button>
                            )}
                        </section>
                    )}

                    {/*
                      * What kind of connections these are, including the kinds there are none of.
                      *
                      * The absent rows are the point. A reader shown only the seven families a
                      * subject has will conclude those are the seven that exist, and on Indra
                      * five of the twelve are absent - on a single mandala, eleven of twelve
                      * are. A list that silently omits them lets someone infer that Indra has no
                      * recorded metre, when the truth is that a deity node never carries one.
                      *
                      * The absent sentence states a fact about the record, never about
                      * possibility, because the artifact carries no rule to check a claim about
                      * possibility against.
                      */}
                    {focus && focus.rows.length > 0 && (
                        <section className="va-world-families">
                            <h3>Kinds of connection</h3>
                            <dl>
                                {focus.rows.map((row) => (
                                    <div
                                        data-present={row.present}
                                        key={row.family}
                                    >
                                        <dt>{row.heading}</dt>
                                        <dd>
                                            {row.present ? (
                                                <>
                                                    {row.subjects.toLocaleString("en-GB")} subject
                                                    {row.subjects === 1 ? "" : "s"}
                                                    {row.shown > 0 && (
                                                        <span>
                                                            {row.shown} on screen
                                                        </span>
                                                    )}
                                                </>
                                            ) : (
                                                FAMILY_COPY[row.family].absent
                                            )}
                                        </dd>
                                    </div>
                                ))}
                            </dl>
                        </section>
                    )}
                </aside>
            )}
        </div>
    );
}
