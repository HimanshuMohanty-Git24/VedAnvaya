"use client";

import { Color } from "three";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { useGraphPalette } from "@/lib/world/palette";
import { usePredicateSemantics } from "@/lib/world/predicates";
import { WorldLabels } from "./world-labels";

/**
 * The World View.
 *
 * React holds selection, mode and the panel. The engine holds transforms, buffers and the
 * frame loop. Nothing crosses that line per frame: a simulation tick never reaches
 * reconciliation, and a re-render never rebuilds a buffer. That separation is the reason this
 * is an imperative class behind a thin component rather than a scene expressed as JSX.
 */

export type WorldSelection = {
    index: number;
    id: string;
    label: string;
    group: string;
    type: string;
    degree: number;
    neighbours: number[];
};

export function WorldView({
    onSelect,
    onReady,
    initialNodeId,
    pathNodes,
    pathHops,
    onRendererLost,
    onInspectEdge,
    safeArea,
    paused = false,
}: {
    onSelect?: (selection: WorldSelection | null) => void;
    /** Called once the geometry, the labels and the engine are all available. */
    onReady?: (world: World, labels: WorldLabelData, engine: WorldEngine) => void;
    initialNodeId?: string | null;
    /** Node indices along a traced route, emphasised and framed together. */
    pathNodes?: number[];
    /** The phrase for each step of that route, from the service that traced it. */
    pathHops?: string[];
    /** Raised only on a real renderer failure, never on a slow frame. */
    onRendererLost?: (detail: string) => void;
    /** Canvas edges covered by chrome, so the camera frames into what is actually visible. */
    safeArea?: { top?: number; right?: number; bottom?: number; left?: number };
    /** A relationship label was clicked. The index is into the world edge arrays. */
    onInspectEdge?: (edge: number) => void;
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
    const palette = useGraphPalette();
    const predicates = usePredicateSemantics();
    /* The engine is built once, so the newest palette and failure handler travel through refs
       rather than through the construction effect's dependency list. */
    const paletteRef = useRef(palette);
    const lostRef = useRef(onRendererLost);
    const inspectRef = useRef(onInspectEdge);
    const pausedRef = useRef(paused);
    useEffect(() => {
        paletteRef.current = palette;
        lostRef.current = onRendererLost;
        inspectRef.current = onInspectEdge;
        pausedRef.current = paused;
    });

    const describe = useCallback((index: number): WorldSelection | null => {
        const world = worldRef.current;
        if (!world) return null;
        const labels = labelsRef.current;
        return {
            index,
            id: labels?.ids[index] ?? String(index),
            label: labels?.labels[index] ?? "",
            group: world.manifest.groups[world.nodeGroup[index]],
            type: world.manifest.types[world.nodeType[index]],
            degree: world.nodeDegree[index],
            neighbours: Array.from(neighboursOf(world, index)),
        };
    }, []);

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
                        onSelect: (index) => {
                            setSelected(index);
                            const described = index === null ? null : describe(index);
                            setNeighbours(described?.neighbours ?? []);
                            onSelect?.(described);
                        },
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
                        () => {
                            const stage = stageRef.current;
                            if (!stage) return [];
                            const origin = stage.getBoundingClientRect();
                            return [...stage.querySelectorAll(".va-world-label")].map((node) => {
                                const box = node.getBoundingClientRect();
                                return {
                                    key: -1,
                                    text: "",
                                    x: box.left - origin.left,
                                    y: box.top - origin.top,
                                    width: box.width,
                                    height: box.height,
                                };
                            });
                        },
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

                observer = new ResizeObserver(() => engine?.resize());
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

                if (initialNodeId) {
                    const index = labels.ids.indexOf(initialNodeId);
                    if (index >= 0) {
                        engine.select(index);
                        engine.focusNode(index);
                    }
                }
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
        if (pathNodes && pathNodes.length > 1) current.fitNodes(pathNodes);
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
    }, [selected, hovered, predicates, labelsReady, pathNodes, pathHops]);

    /*
     * A drag is an orbit, not a hover and not a click.
     *
     * Both mattered. While the button is down the pointer sweeps across the whole scene, so
     * hovering during a drag re-aimed the relationship labels at every node the cursor happened
     * to cross on the way. And the browser fires a click at the end of a drag regardless of how
     * far it travelled, so letting go after turning the world selected whatever was underneath -
     * measured: orbiting away from Indra ended up selected on an unrelated assertion record.
     *
     * Three pixels of travel is the threshold. Below that it is a click with a shaky hand.
     */
    const dragRef = useRef<{ x: number; y: number; moved: boolean } | null>(null);

    const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
        dragRef.current = { x: event.clientX, y: event.clientY, moved: false };
    };

    const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const engine = engineRef.current;
        if (!engine) return;
        const drag = dragRef.current;
        if (drag) {
            if (
                Math.abs(event.clientX - drag.x) > 3 ||
                Math.abs(event.clientY - drag.y) > 3
            ) {
                drag.moved = true;
            }
            return;
        }
        const rect = event.currentTarget.getBoundingClientRect();
        const node = engine.hover(event.clientX - rect.left, event.clientY - rect.top);
        // Hovering draws the subject's own edges. Without this the lines being named are
        // frequently not on screen at all: the world tier draws 24,000 of 185,693 edges.
        engine.setEmphasis(node);
    };

    const onPointerUp = () => {
        // Cleared after the click handler has had its chance to read `moved`.
        window.setTimeout(() => {
            dragRef.current = null;
        }, 0);
    };

    const onPointerLeave = () => {
        dragRef.current = null;
        engineRef.current?.setEmphasis(null);
    };

    const onClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        const engine = engineRef.current;
        if (!engine) return;
        if (dragRef.current?.moved) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const node = engine.pick(event.clientX - rect.left, event.clientY - rect.top);
        engine.select(node);
        if (node !== null) engine.focusNode(node);
    };

    const hoveredLabel = hovered !== null && labelData ? labelData.labels[hovered] : null;

    return (
        <div className="va-world" data-phase={phase} ref={stageRef}>
            <canvas
                aria-label="The knowledge graph as a spatial map. A searchable, keyboard-navigable list of the same nodes and their connections is beside it."
                className="va-world-canvas"
                onClick={onClick}
                onPointerCancel={onPointerUp}
                onPointerDown={onPointerDown}
                onPointerLeave={onPointerLeave}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
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

            <WorldLabels
                engine={engine}
                key={labelsReady}
                labels={labelData?.labels ?? null}
                neighbours={neighbours}
                selected={selected}
                world={worldData}
            />

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
