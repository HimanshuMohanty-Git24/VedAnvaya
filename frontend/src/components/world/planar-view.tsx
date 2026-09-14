"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { World, WorldLabels } from "@/lib/world/artifact";
import {
    buildNeighbourhood,
    isAtRest,
    pickPlanar,
    planarBounds,
    stepPlanar,
    type PlanarGraph,
} from "@/lib/world/planar";

/**
 * The planar view.
 *
 * Canvas 2D rather than WebGL, deliberately. The scene is a few hundred marks, so the GPU has
 * nothing to do that the 2D context cannot; what the 2D context has instead is real line joins,
 * real antialiasing, and the browser's own text rendering, which matters because half of what
 * is drawn here is Sanskrit with combining marks. A WebGL version of this would be more
 * impressive to describe and worse to read.
 */

const GROUP_TOKENS = [
    "deity",
    "unresolved-deity",
    "passage",
    "person",
    "idea",
    "rite",
    "thing",
    "wording",
    "derived",
    "record",
    "other",
];

type Palette = {
    groups: string[];
    ink: string;
    line: string;
    faint: string;
    accent: string;
    paper: string;
};

function readPalette(): Palette {
    const probe = document.createElement("span");
    probe.style.display = "none";
    document.body.appendChild(probe);
    const read = (token: string, fallback: string) => {
        probe.style.color = `var(${token})`;
        return getComputedStyle(probe).color || fallback;
    };
    const palette: Palette = {
        groups: GROUP_TOKENS.map((group) => read(`--va-group-${group}-fill`, "#8c9490")),
        ink: read("--va-text-primary", "#171815"),
        line: read("--va-line-strong", "#b9c2bd"),
        faint: read("--va-text-tertiary", "#6b7169"),
        accent: read("--va-accent-base", "#bd4f32"),
        paper: read("--va-surface-page", "#f4f0e7"),
    };
    probe.remove();
    return palette;
}

export type PlanarSelection = { index: number; node: number };

export function PlanarView({
    world,
    labels,
    root,
    onSelect,
    onInspectEdge,
}: {
    world: World;
    labels: WorldLabels | null;
    root: number | null;
    onSelect: (node: number | null) => void;
    onInspectEdge: (edge: number | null) => void;
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const graphRef = useRef<PlanarGraph | null>(null);
    const paletteRef = useRef<Palette | null>(null);
    const viewRef = useRef({ x: 0, y: 0, scale: 1, vx: 0, vy: 0 });
    const dragRef = useRef<{
        kind: "node" | "canvas";
        node: number | null;
        lastX: number;
        lastY: number;
        moved: boolean;
    } | null>(null);
    const hoverRef = useRef<number | null>(null);
    const frameRef = useRef(0);
    const sleepingRef = useRef(false);
    const reducedRef = useRef(false);

    const [hoverLabel, setHoverLabel] = useState<string | null>(null);

    /* ------------------------------------------------------------ layout - */

    const fit = useCallback(() => {
        const canvas = canvasRef.current;
        const graph = graphRef.current;
        if (!canvas || !graph) return;
        const { minX, minY, maxX, maxY } = planarBounds(graph);
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const spanX = Math.max(1, maxX - minX);
        const spanY = Math.max(1, maxY - minY);
        const scale = Math.min((width * 0.82) / spanX, (height * 0.82) / spanY, 2.4);
        viewRef.current.scale = scale;
        viewRef.current.x = width / 2 - ((minX + maxX) / 2) * scale;
        viewRef.current.y = height / 2 - ((minY + maxY) / 2) * scale;
        viewRef.current.vx = 0;
        viewRef.current.vy = 0;
    }, []);

    useEffect(() => {
        if (root === null) {
            graphRef.current = null;
            return;
        }
        graphRef.current = buildNeighbourhood(world, root);
        sleepingRef.current = false;
        // Let the simulation take the edge off the ring placement before the first paint, so
        // the diagram arrives settling rather than arriving scrambled.
        for (let i = 0; i < 60; i += 1) stepPlanar(graphRef.current);
        fit();
    }, [world, root, fit]);

    /* ------------------------------------------------------------- paint - */

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        const graph = graphRef.current;
        const palette = paletteRef.current;
        if (!canvas || !palette) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        const ratio = Math.min(window.devicePixelRatio, 2);
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
            canvas.width = width * ratio;
            canvas.height = height * ratio;
        }
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        context.clearRect(0, 0, width, height);

        if (!graph) return;
        const view = viewRef.current;
        const toScreenX = (x: number) => x * view.scale + view.x;
        const toScreenY = (y: number) => y * view.scale + view.y;

        const hovered = hoverRef.current;
        const hoveredNode = hovered === null ? null : graph.nodes[hovered];

        /*
         * Edges first, in three weights.
         *
         * A relationship that touches what the pointer is on is drawn in ink; a relationship
         * to the subject itself is drawn a little darker than the rest; everything else is a
         * hairline. Three weights is enough to read structure and few enough that the diagram
         * never becomes a wash - which is what happens when every edge gets its own encoding.
         */
        context.lineCap = "round";
        for (const edge of graph.edges) {
            const a = graph.nodes[edge.a];
            const b = graph.nodes[edge.b];
            const touchesHover =
                hovered !== null && (edge.a === hovered || edge.b === hovered);
            const touchesRoot = a.ring === 0 || b.ring === 0;
            context.beginPath();
            context.moveTo(toScreenX(a.x), toScreenY(a.y));
            context.lineTo(toScreenX(b.x), toScreenY(b.y));
            if (touchesHover) {
                context.strokeStyle = palette.accent;
                context.globalAlpha = 0.72;
                context.lineWidth = 1.5;
            } else if (touchesRoot) {
                context.strokeStyle = palette.line;
                context.globalAlpha = 0.85;
                context.lineWidth = 1.1;
            } else {
                context.strokeStyle = palette.line;
                context.globalAlpha = 0.34;
                context.lineWidth = 0.7;
            }
            context.stroke();
        }
        context.globalAlpha = 1;

        for (const node of graph.nodes) {
            const x = toScreenX(node.x);
            const y = toScreenY(node.y);
            const r = node.radius * Math.min(1.6, Math.max(0.7, view.scale));
            const colour = palette.groups[node.group] ?? palette.faint;

            context.beginPath();
            /*
             * Two shapes, not eleven.
             *
             * A passage is a diamond and everything else is a disc. More shapes were tried and
             * they turn the diagram into a legend puzzle: a reader ends up decoding the key
             * instead of reading the structure. One distinction earns its place because
             * passages are the thing you leave the graph to go and read, and there are twenty
             * thousand of them.
             */
            if (GROUP_TOKENS[node.group] === "passage") {
                context.moveTo(x, y - r);
                context.lineTo(x + r, y);
                context.lineTo(x, y + r);
                context.lineTo(x - r, y);
                context.closePath();
            } else {
                context.arc(x, y, r, 0, Math.PI * 2);
            }
            context.fillStyle = colour;
            context.globalAlpha = node.ring === 2 ? 0.55 : 0.94;
            context.fill();
            context.globalAlpha = 1;

            if (node.ring === 0 || node === hoveredNode) {
                // Ink outline rather than a glow: the mark is being pointed at, not lit up.
                context.lineWidth = node.ring === 0 ? 2 : 1.4;
                context.strokeStyle = node.ring === 0 ? palette.accent : palette.ink;
                context.stroke();
            }
        }

        /* Labels: the subject, its hovered neighbour, and the busiest of the first ring. */
        if (labels) {
            const named = graph.nodes
                .map((node, index) => ({ node, index }))
                .filter(({ node, index }) => node.ring === 0 || index === hovered || node.ring === 1)
                .sort((a, b) => b.node.degree - a.node.degree)
                .slice(0, 18);
            for (const { node, index } of named) {
                const text = labels.labels[node.id];
                if (!text) continue;
                const strong = node.ring === 0 || index === hovered;
                context.font = strong
                    ? '500 14px "Charis SIL", Georgia, serif'
                    : '400 11.5px "Charis SIL", Georgia, serif';
                context.fillStyle = strong ? palette.ink : palette.faint;
                context.textBaseline = "middle";
                const x = toScreenX(node.x) + node.radius + 7;
                const y = toScreenY(node.y);
                // Paper drawn under the letterforms keeps names legible over dense regions
                // without a box or a shadow behind each one.
                context.strokeStyle = palette.paper;
                context.lineWidth = 3.5;
                context.lineJoin = "round";
                context.strokeText(text, x, y);
                context.fillText(text, x, y);
            }
        }
    }, [labels]);

    /* -------------------------------------------------------------- loop - */

    useEffect(() => {
        paletteRef.current = readPalette();
        reducedRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const loop = () => {
            frameRef.current = requestAnimationFrame(loop);
            const graph = graphRef.current;
            if (graph) {
                /*
                 * Energy in, energy out.
                 *
                 * The simulation stops stepping once the graph is still, and does not start
                 * again until something disturbs it. A diagram nobody is touching costs
                 * nothing and, more importantly, holds perfectly still while it is being read.
                 */
                if (!sleepingRef.current) {
                    const energy = stepPlanar(graph);
                    if (isAtRest(energy) && !dragRef.current) sleepingRef.current = true;
                }
                const view = viewRef.current;
                if (!dragRef.current && (Math.abs(view.vx) > 0.05 || Math.abs(view.vy) > 0.05)) {
                    // Inertial pan: the canvas keeps moving after the pointer leaves, and
                    // slows the way something with mass slows.
                    view.x += view.vx;
                    view.y += view.vy;
                    view.vx *= 0.92;
                    view.vy *= 0.92;
                }
            }
            draw();
        };
        frameRef.current = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(frameRef.current);
    }, [draw]);

    /* ---------------------------------------------------------- pointers - */

    const toGraph = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const view = viewRef.current;
        return {
            x: (event.clientX - rect.left - view.x) / view.scale,
            y: (event.clientY - rect.top - view.y) / view.scale,
            screenX: event.clientX - rect.left,
            screenY: event.clientY - rect.top,
        };
    };

    const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        if (!graph) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        const { x, y, screenX, screenY } = toGraph(event);
        const hit = pickPlanar(graph, x, y);
        if (hit !== null) {
            graph.nodes[hit].held = true;
            sleepingRef.current = false;
        }
        dragRef.current = {
            kind: hit === null ? "canvas" : "node",
            node: hit,
            lastX: screenX,
            lastY: screenY,
            moved: false,
        };
    };

    const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        if (!graph) return;
        const { x, y, screenX, screenY } = toGraph(event);
        const drag = dragRef.current;

        if (!drag) {
            const hit = pickPlanar(graph, x, y);
            if (hit !== hoverRef.current) {
                hoverRef.current = hit;
                setHoverLabel(
                    hit === null || !labels ? null : labels.labels[graph.nodes[hit].id] || null,
                );
            }
            return;
        }

        const dx = screenX - drag.lastX;
        const dy = screenY - drag.lastY;
        drag.lastX = screenX;
        drag.lastY = screenY;
        if (Math.abs(dx) > 1 || Math.abs(dy) > 1) drag.moved = true;

        if (drag.kind === "node" && drag.node !== null) {
            const node = graph.nodes[drag.node];
            node.x = x;
            node.y = y;
            sleepingRef.current = false;
        } else {
            const view = viewRef.current;
            view.x += dx;
            view.y += dy;
            view.vx = dx;
            view.vy = dy;
        }
    };

    const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        const drag = dragRef.current;
        dragRef.current = null;
        if (!graph || !drag) return;
        event.currentTarget.releasePointerCapture(event.pointerId);
        if (drag.node !== null) {
            graph.nodes[drag.node].held = false;
            sleepingRef.current = false;
            // A release with no movement is a click, not a throw.
            if (!drag.moved) onSelect(graph.nodes[drag.node].id);
        } else if (!drag.moved) {
            onSelect(null);
            onInspectEdge(null);
        }
    };

    const onWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
        const view = viewRef.current;
        const rect = event.currentTarget.getBoundingClientRect();
        const px = event.clientX - rect.left;
        const py = event.clientY - rect.top;
        const before = { x: (px - view.x) / view.scale, y: (py - view.y) / view.scale };
        const next = Math.min(3.2, Math.max(0.18, view.scale * Math.exp(-event.deltaY * 0.0016)));
        view.scale = next;
        // Zoom about the pointer rather than the centre, so the thing under the cursor stays
        // under the cursor.
        view.x = px - before.x * next;
        view.y = py - before.y * next;
    };

    return (
        <div className="va-planar">
            <canvas
                aria-label="The selected subject and its connections as a diagram. The same connections are listed beside it."
                className="va-planar-canvas"
                onPointerCancel={onPointerUp}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onWheel={onWheel}
                ref={canvasRef}
                role="img"
            />
            {hoverLabel && (
                <p aria-hidden="true" className="va-world-hover">
                    {hoverLabel}
                </p>
            )}
            {root === null && (
                <p className="va-planar-empty">
                    Choose a subject to pull its connections apart. Search above, or open the
                    world to find one spatially.
                </p>
            )}
        </div>
    );
}
