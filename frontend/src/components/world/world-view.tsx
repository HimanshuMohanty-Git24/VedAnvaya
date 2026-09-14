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
import { WorldEngine, type EngineStats } from "@/lib/world/engine";
import { useGraphPalette } from "@/lib/world/palette";
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
    onRendererLost,
    paused = false,
}: {
    onSelect?: (selection: WorldSelection | null) => void;
    /** Called once the geometry, the labels and the engine are all available. */
    onReady?: (world: World, labels: WorldLabelData, engine: WorldEngine) => void;
    initialNodeId?: string | null;
    /** Node indices along a traced route, emphasised and framed together. */
    pathNodes?: number[];
    /** Raised only on a real renderer failure, never on a slow frame. */
    onRendererLost?: (detail: string) => void;
    /** True while another renderer is the visible one. The scene is kept, not drawn. */
    paused?: boolean;
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const engineRef = useRef<WorldEngine | null>(null);
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
    /* The engine is built once, so the newest palette and failure handler travel through refs
       rather than through the construction effect's dependency list. */
    const paletteRef = useRef(palette);
    const lostRef = useRef(onRendererLost);
    useEffect(() => {
        paletteRef.current = palette;
        lostRef.current = onRendererLost;
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
                    },
                });
                engineRef.current = engine;
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

    const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const engine = engineRef.current;
        if (!engine) return;
        const rect = event.currentTarget.getBoundingClientRect();
        engine.hover(event.clientX - rect.left, event.clientY - rect.top);
    };

    const onClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        const engine = engineRef.current;
        if (!engine) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const node = engine.pick(event.clientX - rect.left, event.clientY - rect.top);
        engine.select(node);
        if (node !== null) engine.focusNode(node);
    };

    const hoveredLabel = hovered !== null && labelData ? labelData.labels[hovered] : null;

    return (
        <div className="va-world" data-phase={phase}>
            <canvas
                aria-label="The knowledge graph as a spatial map. A searchable, keyboard-navigable list of the same nodes and their connections is beside it."
                className="va-world-canvas"
                onClick={onClick}
                onPointerMove={onPointerMove}
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
