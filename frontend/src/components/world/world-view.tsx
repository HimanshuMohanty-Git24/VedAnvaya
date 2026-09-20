"use client";

import { Color } from "three";
import { useEffect, useRef, useState } from "react";
import {
    loadWorld,
    loadWorldLabels,
    neighboursOf,
    type World,
    type WorldLabels as WorldLabelData,
} from "@/lib/world/artifact";
import { EdgeLabelView } from "@/lib/world/edge-label-view";
import {
    LABEL_STRIDE,
    edgeLabelBudget,
    pickEdgeLabels,
    type EdgeLabelPick,
} from "@/lib/world/edge-labels";
import { WorldEngine, type EngineStats } from "@/lib/world/engine";
import {
    FAMILY_INDEX,
    FOCUS_BUDGET,
    focusBudgetForBand,
    useFocusNeighbourhood,
} from "@/lib/world/focus";
import { useGraphPalette } from "@/lib/world/palette";
import { usePredicateSemantics } from "@/lib/world/predicates";

/**
 * The World View.
 *
 * React holds selection, mode and the panel. The engine holds transforms, buffers and the
 * frame loop. Nothing crosses that line per frame: a simulation tick never reaches
 * reconciliation, and a re-render never rebuilds a buffer. That separation is the reason this
 * is an imperative class behind a thin component rather than a scene expressed as JSX.
 */

export function WorldView({
    onTap,
    onReady,
    selectedIndex,
    pathNodes,
    pathHops,
    onRendererLost,
    onInspectEdge,
    inspectedEdge = null,
    safeArea,
    chromeBoxes,
    paused = false,
}: {
    /**
     * The reader tapped the canvas. An event, reported upward and acted on by the owner of the
     * state - never by this component, which does not know what a selection means.
     *
     * Null means the background was tapped. The graph page deliberately does nothing with that:
     * "nothing is under the pointer" is not a request to leave the subject you are reading.
     */
    onTap?: (node: number | null) => void;
    /** Called once the geometry, the labels and the engine are all available. */
    onReady?: (world: World, labels: WorldLabelData, engine: WorldEngine) => void;
    /**
     * The selected subject, as state flowing down. Not an opening value.
     *
     * It was `initialNodeId` and it was applied once, at construction. So a subject chosen in
     * the planar view and then looked at spatially was never selected in this scene, and
     * neither was one arrived at through the browser's back button. The scene followed the
     * reader for exactly one frame of the session and then stopped.
     */
    selectedIndex?: number | null;
    /** Node indices along a traced route, emphasised and framed together. */
    pathNodes?: number[];
    /** The phrase for each step of that route, from the service that traced it. */
    pathHops?: string[];
    /** Raised only on a real renderer failure, never on a slow frame. */
    onRendererLost?: (detail: string) => void;
    /** Canvas edges covered by chrome, so the camera frames into what is actually visible. */
    safeArea?: { top?: number; right?: number; bottom?: number; left?: number };
    /**
     * Where the chrome is standing on the stage, so no label is placed under it.
     *
     * Rectangles in canvas coordinates. Distinct from `safeArea`, which is what the camera
     * centres inside and is top-and-bottom only on purpose: a phrase behind the right-hand
     * rail is not off-centre, it is gone, and only the label layer can do anything about it.
     */
    chromeBoxes?: ReadonlyArray<{ x: number; y: number; w: number; h: number }>;
    /** A relationship label was clicked. The index is into the world edge arrays. */
    onInspectEdge?: (edge: number) => void;
    /**
     * Which relationship the reader currently has an explanation open on, or null.
     *
     * The label layer pins that phrase at the top tier so the collision pass cannot drop the
     * one thing the reader just asked about. It learns of a *click on a phrase* by itself, but
     * not of the two other ways the state moves - the explanation being closed, and one being
     * opened from the panel's relations list, which is the keyboard path. Without this the
     * label of a closed explanation stayed pinned until the subject changed.
     */
    inspectedEdge?: number | null;
    /** True while another renderer is the visible one. The scene is kept, not drawn. */
    paused?: boolean;
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const stageRef = useRef<HTMLDivElement>(null);
    const engineRef = useRef<WorldEngine | null>(null);
    /* The edge-label overlay and the three buffers it needs. All refs: these are written and
       read inside the frame loop, where a state update would be a re-render per frame. */
    const labelViewRef = useRef<EdgeLabelView | null>(null);
    const picksRef = useRef<EdgeLabelPick[]>([]);
    const segmentsRef = useRef<Uint32Array>(new Uint32Array(0));
    const pointsRef = useRef<Float32Array>(new Float32Array(0));
    const worldRef = useRef<World | null>(null);
    const labelsRef = useRef<WorldLabelData | null>(null);
    /* Also held in state: the label layer and the hover caption read these during
       render, and a ref read during render does not schedule one. */
    const [labelData, setLabelData] = useState<WorldLabelData | null>(null);
    const [engine, setEngine] = useState<WorldEngine | null>(null);
    /* The artifact, as a render input.
       Its one previous consumer was the `<WorldLabels>` element, which is gone - names are now
       placed by the unified label pass and reach it through `EdgeLabelView.setScene`. It is read
       again because curating the neighbourhood is a memoised derivation from the artifact and the
       selection, and a `useMemo` cannot key on a ref. `worldRef` stays for the frame path, where
       a render input would be the wrong thing entirely. */
    const [worldData, setWorldData] = useState<World | null>(null);

    const [phase, setPhase] = useState<"loading" | "ready" | "failed">("loading");
    const [failure, setFailure] = useState<string | null>(null);
    const [stats, setStats] = useState<EngineStats | null>(null);
    const [hovered, setHovered] = useState<number | null>(null);
    /* Held in state rather than read from a ref so the label layer re-runs placement when the
       selection changes; the engine itself never reads these. */
    const [selected, setSelected] = useState<number | null>(null);
    const [neighbours, setNeighbours] = useState<number[]>([]);
    const [labelsReady, setLabelsReady] = useState(0);
    /*
     * The band a subject can actually be drawn into, in CSS pixels.
     *
     * Not the viewport, and the two differ by more than a factor of two on a phone: measured on
     * a 390x844 device the graph chrome takes 225.6 px before anything is drawn, leaving 434.4 px
     * under a collapsed sheet and 183.1 px under a half-raised one. A budget chosen from the
     * viewport height draws sixteen orbs into room for eleven, and a slab sized to the canvas
     * puts half of itself behind the sheet.
     */
    const [band, setBand] = useState({ width: 0, height: 0 });
    const palette = useGraphPalette();
    const predicates = usePredicateSemantics();
    /* The engine is built once, so the newest palette and failure handler travel through refs
       rather than through the construction effect's dependency list. */
    const paletteRef = useRef(palette);
    const lostRef = useRef(onRendererLost);
    const tapRef = useRef(onTap);
    /*
     * The open explanation, told to the layer that has to keep its phrase on screen.
     *
     * Keyed on `engine` as well as the edge because the label layer is built inside the async
     * initialisation, long after the first render: an effect that ran only on the edge would
     * find the ref still null on a cold load and never fire again, which is the exact shape of
     * the `setPaused` defect recorded a few lines below.
     */
    useEffect(() => {
        labelViewRef.current?.setInspected(inspectedEdge);
    }, [engine, inspectedEdge]);

    const inspectRef = useRef(onInspectEdge);
    const pausedRef = useRef(paused);
    useEffect(() => {
        paletteRef.current = palette;
        lostRef.current = onRendererLost;
        tapRef.current = onTap;
        inspectRef.current = onInspectEdge;
        pausedRef.current = paused;
    });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const controller = new AbortController();
        let engine: WorldEngine | null = null;
        let observer: ResizeObserver | null = null;

        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

        void (async () => {
            try {
                const world = await loadWorld(controller.signal);
                const initial = paletteRef.current;
                if (!initial) return;
                if (controller.signal.aborted) return;
                worldRef.current = world;
                setWorldData(world);

                engine = new WorldEngine({
                    canvas,
                    world,
                    groupColours: initial.groups,
                    background: new Color(initial.page),
                    edgeColour: new Color(initial.line),
                    accentColour: new Color(initial.accent),
                    reducedMotion: reduced.matches,
                    events: {
                        onLost: (detail) => lostRef.current?.(detail),
                        onHover: setHovered,
                        /* Forwarded, not interpreted. What a tap means is the state owner's
                           decision, and this component holding an opinion about it is how the
                           scene and the address bar came to disagree. */
                        onTap: (index) => tapRef.current?.(index),
                        onStats: setStats,
                        /*
                         * Label positions are written here, after the render, because that is
                         * when the camera's matrices are current - and they are written to the
                         * DOM directly rather than to state, so sixty frames a second of
                         * movement costs no reconciliation.
                         */
                        onFrame: () => {
                            const view = labelViewRef.current;
                            const segments = segmentsRef.current;
                            if (!view || segments.length === 0 || !engine) return;
                            view.update(
                                engine.projectSegmentPoints(segments, pointsRef.current),
                                engine.viewport(),
                            );
                        },
                    },
                });
                engineRef.current = engine;
                /*
                 * The pause is applied at construction, not only by the effect that watches it.
                 *
                 * The engine is built after the artifact loads, which is long after the first
                 * render. So an effect that calls `setPaused` on mount finds `engineRef.current`
                 * still null, does nothing, and never fires again - because `paused` has not
                 * changed. Opening straight into the planar renderer therefore left the spatial
                 * engine running unseen: measured at 88 frames in three seconds, drawing 35,370
                 * nodes nobody was looking at, on exactly the weak devices the planar renderer
                 * exists to help.
                 */
                engine.setPaused(pausedRef.current);
                if (stageRef.current) {
                    labelViewRef.current = new EdgeLabelView(
                        stageRef.current,
                        edgeLabelBudget(engine.viewport().width),
                        (edge) => inspectRef.current?.(edge),
                        /* Nothing on this canvas is inked before the label pass runs, so there
                           are no immovable obstacles to declare. The names used to be - placed
                           by `world-labels.tsx` on its own 160 ms timer, then read back out of
                           the DOM here with up to 41 `getBoundingClientRect` calls every 150 ms,
                           a forced layout flush nearly seven times a second. That is the
                           two-pass design ARB-3 replaced: under it a phrase could only ever give
                           way to a name and never the other way round. */
                        undefined,
                        /* The projection, and nothing else. Which subjects are named, in which
                           quadrant, at which tier and under which cap is decided by
                           `nodeNameAnchors` and the one collision pass; this supplies the single
                           fact the engine holds and the layout does not. */
                        (node) => engineRef.current?.screenPositionOf(node) ?? null,
                    );
                }
                engine.start();
                const startedEngine = engine;
                setEngine(engine);
                /* A handle for `scripts/bench-world.mjs`. The edge budget and the level-of-
                   detail thresholds have to be set from measurements on real hardware, and a
                   benchmark driving a real page needs something to hold. Nothing in the
                   application reads this. */
                (window as unknown as Record<string, unknown>).__vedaWorld = engine;
                setPhase("ready");

                observer = new ResizeObserver(() => {
                    engine?.resize();
                    if (!engine) return;
                    const size = engine.viewport();
                    /* The phrase cap is a function of the width and was being read once, at
                       construction. A rotation from portrait to landscape more than doubles the
                       room and a window narrowed past 768 halves it, and in both directions the
                       layer went on budgeting for the width it was born at. */
                    labelViewRef.current?.setRelationCap(edgeLabelBudget(size.width));
                    setBand((previous) =>
                        previous.width === size.width ? previous : { ...previous, width: size.width },
                    );
                });
                observer.observe(canvas);

                /* Labels are fetched after the geometry is already drawing. They are needed
                   for the panel and for naming hubs, and neither is wanted in the way of the
                   first frame. */
                const labels = await loadWorldLabels(controller.signal);
                if (controller.signal.aborted) return;
                labelsRef.current = labels;
                setLabelData(labels);
                setLabelsReady((n) => n + 1);
                // Announced only once everything a caller needs is in hand: the geometry, the
                // names, and a running engine. Splitting it meant the page had to guard three
                // separate half-ready states.
                onReady?.(world, labels, startedEngine);

            } catch (reason) {
                if (controller.signal.aborted) return;
                setFailure(
                    reason instanceof Error ? reason.message : "The world could not be drawn.",
                );
                setPhase("failed");
            }
        })();

        const onMotionChange = () => engine?.setReducedMotion(reduced.matches);
        reduced.addEventListener("change", onMotionChange);

        return () => {
            controller.abort();
            reduced.removeEventListener("change", onMotionChange);
            observer?.disconnect();
            labelViewRef.current?.destroy();
            labelViewRef.current = null;
            engine?.dispose();
            engineRef.current = null;
        };
        // Mounted once. Data and handlers travel through refs, not through the dependency
        // list, because re-creating a WebGL context on a prop change is not a thing to do.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [palette !== null]);

    useEffect(() => {
        engineRef.current?.setPaused(paused);
    }, [paused]);

    useEffect(() => {
        engineRef.current?.setSafeArea(safeArea ?? {});
    }, [safeArea]);

    /* The chrome's boxes, so no phrase and no name is laid behind a panel. */
    useEffect(() => {
        labelViewRef.current?.setObstacles(chromeBoxes ?? []);
    }, [chromeBoxes]);

    /* Re-measured on both of its causes: the canvas changing size, and the chrome over it
       changing height. In PATH the band carries two fields and a paragraph of caveats, so the
       second happens without the first. */
    useEffect(() => {
        const current = engineRef.current;
        if (!current) return;
        const { width, height } = current.viewport();
        setBand({
            width,
            height: Math.max(0, height - (safeArea?.top ?? 0) - (safeArea?.bottom ?? 0)),
        });
    }, [safeArea, engine, phase]);

    /*
     * The curated neighbourhood, memoised, and never derived in a frame.
     *
     * `selectFocus` on Indra costs between 1.3 and 2.9 ms - a frame, or fifty-five of them at the
     * rate this canvas draws - so the derivation happens here, once per subject, and the engine
     * is handed the answer. The hook keys on primitives so that an inline options object cannot
     * defeat the memo, which is the whole cost it exists to pay once.
     *
     * It is derived whatever the view is. Focus composes a slab from it; World uses the same set
     * to decide what to brighten, which is how a reader who selects Indra in the world gets a
     * neighbourhood rather than one sixth of the corpus lit at once.
     */
    const focusNeighbourhood = useFocusNeighbourhood({
        world: worldData,
        labels: labelData,
        root: selectedIndex ?? null,
        budget: band.width > 0 ? focusBudgetForBand(band.width, band.height) : FOCUS_BUDGET,
    });

    useEffect(() => {
        const current = engineRef.current;
        if (!current) return;
        if (!focusNeighbourhood) {
            current.setFocus(null);
            return;
        }
        current.setFocus({
            root: focusNeighbourhood.subject.index,
            /* One family per orb, because a sector is an angular partition and a member cannot
               be in two of them. The first is the artifact's own order, so the choice is the
               record's rather than this component's. */
            members: focusNeighbourhood.shown.map((neighbour) => ({
                node: neighbour.node,
                family: FAMILY_INDEX.get(neighbour.families[0] ?? "OTHER") ?? 0,
            })),
            spokes: focusNeighbourhood.spokes,
            between: focusNeighbourhood.between,
        });
    }, [focusNeighbourhood, engine]);

    /*
     * The scene follows the selected subject, for as long as there is a session.
     *
     * This is the correction to a one-shot. The subject used to be applied at construction and
     * never again, guarded by a ref on the page as well, so the spatial scene tracked the
     * reader for one frame and then went deaf: choose a subject in the planar view and switch
     * to 3D, or press the browser's back button, and the scene still showed whatever had been
     * in the URL when the page first loaded.
     *
     * `engine.select` returns early when the subject has not changed, so this is idempotent -
     * which matters, because the camera flight below must not restart on an unrelated re-render.
     */
    const framed = useRef<number | null>(null);
    const nextSelection = selectedIndex ?? null;
    useEffect(() => {
        const current = engineRef.current;
        if (!current) return;
        current.select(nextSelection);
        setSelected(nextSelection);
        const world = worldRef.current;
        setNeighbours(
            nextSelection !== null && world ? Array.from(neighboursOf(world, nextSelection)) : [],
        );
        /* Framed once per subject. A re-render is not a request to fly the camera again, and a
           camera that re-flies under a reader who is orbiting is the thing this phase is
           correcting rather than a thing to add. */
        if (nextSelection !== null && framed.current !== nextSelection) {
            framed.current = nextSelection;
            current.focusNode(nextSelection);
        }
        if (nextSelection === null) framed.current = null;
    }, [nextSelection, engine]);

    /* A theme change rewrites the buffers rather than rebuilding the scene. Recreating the
       renderer would drop the camera, the selection and a two-megabyte artifact along with it. */
    useEffect(() => {
        if (!palette) return;
        engineRef.current?.setPalette({
            groupColours: palette.groups,
            background: new Color(palette.page),
            edgeColour: new Color(palette.line),
            accentColour: new Color(palette.accent),
        });
    }, [palette]);

    /* A traced route takes over the view: the nodes along it are lifted, everything else
       recedes, and the camera frames the whole run rather than any one end of it. */
    useEffect(() => {
        const current = engineRef.current;
        if (!current) return;
        current.setPath(pathNodes ?? []);
        if (pathNodes && pathNodes.length > 1) {
            /*
             * A closer floor than `fitNodes` defaults to, and the reason is what PATH does to
             * the rest of the scene.
             *
             * The 700 default exists so that framing two subjects which happen to sit near
             * each other does not put the camera inside the cloud, where every edge crosses
             * the viewport. In PATH there is no cloud: `setPath` drops every node off the
             * route to alpha 0.06 and draws only the hops. Measured on Agni to takman, a
             * three-node route whose world positions span well under the default's 269-unit
             * threshold: at 700 the whole route drew inside 40 px with its two hop phrases
             * stacked on top of each other, which is the route being *rendered* and not being
             * *shown*. At 240 the same route fills the stage and both phrases sit on their
             * own line.
             */
            current.fitNodes(pathNodes, 900, { spread: 3.4, floor: 240 });
        }
    }, [pathNodes]);

    /*
     * Naming the connections under the pointer.
     *
     * The subject whose edges are named is the selected one if there is one, and the hovered one
     * otherwise - the same precedence the engine uses to decide whose edges to draw, because the
     * words have to be about the lines that are on screen.
     *
     * Recomputed only when that subject changes. Which sixteen connections are worth naming does
     * not depend on where the camera is; only where the words go does, and that is done per frame
     * in `onFrame` without touching React.
     */
    useEffect(() => {
        const view = labelViewRef.current;
        const engine = engineRef.current;
        const world = worldRef.current;
        if (!view || !engine || !world) return;

        /* The scene the names are drawn from. Facts, not placements - see `LabelScene`. It is set
           here rather than in the frame callback because none of it can change within a frame. */
        view.setScene({
            world,
            labels: labelsRef.current,
            selected,
            hovered,
            neighbours,
        });

        /*
         * A traced route names its own steps.
         *
         * In PATH the drawn lines are the hops, not a subject's neighbourhood, so the labels
         * describe those and the words come from the service that found the route. The keys are
         * negative, which is how the inspector knows these are hops rather than artifact edges:
         * a hop is not one edge in the world file, and the explanation for each is already set
         * out in the list beside the canvas.
         */
        if (pathNodes && pathNodes.length > 1) {
            const steps = pathNodes.length - 1;
            const picks: EdgeLabelPick[] = [];
            const pairs: number[] = [];
            for (let i = 0; i < steps; i += 1) {
                const text = pathHops?.[i] ?? "";
                /* A step with no phrase is skipped here rather than filtered afterwards: the
                   points buffer is indexed in step with `picks`, so removing an entry from one
                   and not the other would put every later label on the wrong line. */
                if (!text) continue;
                pairs.push(pathNodes[i], pathNodes[i + 1]);
                picks.push({
                    edge: -1 - i,
                    other: pathNodes[i + 1],
                    outgoing: true,
                    predicate: "",
                    text,
                    // Earlier steps first, so a long route loses its tail rather than its head.
                    priority: 1 - i / steps,
                });
            }
            picksRef.current = picks;
            segmentsRef.current = new Uint32Array(pairs);
            pointsRef.current = new Float32Array(picks.length * LABEL_STRIDE);
            view.setLabels(picks);
            return;
        }

        const subject = selected ?? hovered;
        if (subject === null) {
            picksRef.current = [];
            segmentsRef.current = new Uint32Array(0);
            view.setLabels([]);
            return;
        }

        const picks = pickEdgeLabels(
            world,
            predicates,
            subject,
            edgeLabelBudget(engine.viewport().width),
            engine.drawnEdgesOf(subject),
        );
        picksRef.current = picks;
        const segments = new Uint32Array(picks.length * 2);
        picks.forEach((pick, i) => {
            segments[i * 2] = subject;
            segments[i * 2 + 1] = pick.other;
        });
        segmentsRef.current = segments;
        pointsRef.current = new Float32Array(picks.length * LABEL_STRIDE);
        view.setLabels(picks);
    }, [selected, hovered, neighbours, predicates, labelsReady, pathNodes, pathHops]);

    /*
     * There is no pointer pipeline here any more.
     *
     * Forty-seven lines of drag tracking used to live at this spot, and a second copy lived on
     * the homepage with no threshold at all and a third in the planar view with a broken one.
     * They are one decision - was that a click or the end of an orbit - and it is now taken
     * once, in `installGestures`, which the engine installs on its own canvas. See that file
     * for why the copy that lived here also failed on touch.
     */

    const hoveredLabel = hovered !== null && labelData ? labelData.labels[hovered] : null;

    return (
        <div className="va-world" data-phase={phase} ref={stageRef}>
            <canvas
                aria-label="The knowledge graph as a spatial map. A searchable, keyboard-navigable list of the same nodes and their connections is beside it."
                className="va-world-canvas"
                ref={canvasRef}
                role="img"
            />

            {phase === "loading" && (
                <p className="va-world-status" role="status">
                    Reading the world…
                </p>
            )}

            {phase === "failed" && (
                <div className="va-world-status is-failed" role="alert">
                    <p>{failure}</p>
                    <p className="va-world-status-note">
                        The list beside this map is the same graph and does not need the map to
                        work.
                    </p>
                </div>
            )}

            {hoveredLabel && (
                <p aria-hidden="true" className="va-world-hover">
                    {hoveredLabel}
                </p>
            )}

            {stats && phase === "ready" && (
                <p aria-hidden="true" className="va-world-stats">
                    {stats.drawnNodes.toLocaleString("en-GB")} nodes ·{" "}
                    {stats.drawnEdges.toLocaleString("en-GB")} edges · {stats.fps} fps ·{" "}
                    {stats.frameMs.toFixed(1)} ms frame · {stats.jsMs.toFixed(1)} ms js
                </p>
            )}
        </div>
    );
}
