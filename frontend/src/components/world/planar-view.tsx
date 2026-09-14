"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { World, WorldLabels } from "@/lib/world/artifact";
import { EdgeLabelView } from "@/lib/world/edge-label-view";
import {
    LABEL_FRACTIONS,
    LABEL_STRIDE,
    edgeLabelBudget,
    pickEdgeLabels,
    type EdgeLabelPick,
} from "@/lib/world/edge-labels";
import { GESTURE_SLOP, type PointerKind } from "@/lib/world/gesture";
import { GROUP_NAMES, useGraphPalette, type GraphPalette } from "@/lib/world/palette";
import { usePredicateSemantics } from "@/lib/world/predicates";
import { buildWorldProjection } from "@/lib/world/planar";
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

export type PlanarSelection = { index: number; node: number };

export function PlanarView({
    world,
    labels,
    root,
    scope,
    onSelect,
    onInspectEdge,
    safeArea,
}: {
    world: World;
    labels: WorldLabels | null;
    root: number | null;
    /**
     * What this canvas is drawing.
     *
     * "world" projects the whole composed corpus onto a plane; "focus" builds a live
     * neighbourhood around one subject. They share this component because they share a visual
     * language and an interaction model, and because a reader moving between them should feel
     * the same diagram deepening rather than two different tools.
     */
    scope: "world" | "focus";
    /**
     * A subject was chosen. Non-nullable on purpose.
     *
     * This used to accept null, and the canvas used to pass one on a tap into empty space. The
     * type is the guard: there is no longer a value this component can send that means "the
     * reader is finished with the subject", because it is not something a canvas knows.
     */
    onSelect: (node: number) => void;
    onInspectEdge: (edge: number | null) => void;
    /**
     * Canvas edges covered by chrome, so the diagram is centred in what a reader can see.
     *
     * Measured for both renderers since the phase that introduced it, and passed to one. On a
     * phone the graph chrome takes 226 px of the top and the subject sheet takes 120 px of the
     * bottom, so a diagram centred in the whole canvas puts the chosen subject behind the
     * sheet - at every one of its three heights.
     */
    safeArea?: { top?: number; right?: number; bottom?: number; left?: number };
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const stageRef = useRef<HTMLDivElement>(null);
    const graphRef = useRef<PlanarGraph | null>(null);
    /* Relationship labels, drawn by the same module the spatial view uses. Everything about
       them - the cap, the collision rule, the hysteresis, the words - is shared, so the two
       renderers cannot come to different conclusions about what a subject is attached to. */
    const labelViewRef = useRef<EdgeLabelView | null>(null);
    const labelSubjectRef = useRef<number | null>(null);
    const picksRef = useRef<EdgeLabelPick[]>([]);
    const planarEdgeRef = useRef<Map<number, number>>(new Map());
    const pointsRef = useRef<Float32Array>(new Float32Array(0));
    const namedBoxesRef = useRef<
        Array<{ key: number; text: string; x: number; y: number; width: number; height: number }>
    >([]);
    /*
     * The palette is a subscription, not a snapshot.
     *
     * Read once at mount, this canvas kept drawing carbon ink and a 3.5-pixel ivory halo
     * around every label after a switch to dark - the halo being the paper colour, stroked
     * behind text so it stays legible over a dense region. On a carbon page that is a glowing
     * outline around every name, which is the precise look this product is built to avoid.
     */
    const palette = useGraphPalette();
    const predicates = usePredicateSemantics();
    const predicatesRef = useRef(predicates);
    const inspectRef = useRef(onInspectEdge);
    /* The paint function reads this from inside the frame loop, which is outside React, so
       the current value is mirrored into a ref - in an effect, not during render. */
    const paletteRef = useRef<GraphPalette | null>(null);
    useEffect(() => {
        paletteRef.current = palette;
        predicatesRef.current = predicates;
        inspectRef.current = onInspectEdge;
    }, [palette, predicates, onInspectEdge]);
    const viewRef = useRef({ x: 0, y: 0, scale: 1, vx: 0, vy: 0 });
    const dragRef = useRef<{
        kind: "node" | "canvas";
        node: number | null;
        lastX: number;
        lastY: number;
        /** Where the press landed. The threshold is measured from here. */
        originX: number;
        originY: number;
        kindOfPointer: PointerKind;
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
        /*
         * Fitted into the visible band, not the canvas.
         *
         * The band is what is left after the chrome above and the sheet below, and on a phone
         * that is less than half the canvas. Centring in the canvas put the subject under the
         * sheet; centring in the band puts it where the reader is looking. A floor of 120 px
         * stops an expanded sheet from collapsing the band to nothing and taking the scale with
         * it - past that point there is no good answer, and the least bad one is to keep the
         * diagram at a legible size and let the reader lower the sheet.
         */
        const inset = {
            top: safeArea?.top ?? 0,
            right: safeArea?.right ?? 0,
            bottom: safeArea?.bottom ?? 0,
            left: safeArea?.left ?? 0,
        };
        const bandWidth = Math.max(160, width - inset.left - inset.right);
        const bandHeight = Math.max(120, height - inset.top - inset.bottom);
        const spanX = Math.max(1, maxX - minX);
        const spanY = Math.max(1, maxY - minY);
        const scale = Math.min((bandWidth * 0.82) / spanX, (bandHeight * 0.82) / spanY, 2.4);
        viewRef.current.scale = scale;
        viewRef.current.x =
            inset.left + bandWidth / 2 - ((minX + maxX) / 2) * scale;
        viewRef.current.y = inset.top + bandHeight / 2 - ((minY + maxY) / 2) * scale;
        viewRef.current.vx = 0;
        viewRef.current.vy = 0;
    }, [safeArea]);

    useEffect(() => {
        if (scope === "world") {
            /*
             * The world, projected rather than re-simulated.
             *
             * The composed layout already encodes everything this view is for - which
             * constellations there are, how big, how far apart, which edges bridge them - and
             * it took minutes to settle. Re-running a simulation in the browser would produce
             * a worse arrangement of the same graph and take the frame budget to do it. So the
             * plane is a projection of the existing x and y, and the reader is looking at the
             * same world the spatial view shows, from directly above it.
             */
            graphRef.current = buildWorldProjection(world);
            // Static: nothing to settle, so the simulation never starts.
            sleepingRef.current = true;
            fit();
            return;
        }
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
    }, [world, root, scope, fit]);

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
            const colour = palette.groupCss[node.group] ?? palette.inkSoft;

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
            if (GROUP_NAMES[node.group] === "passage") {
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

        /* Boxes the relationship labels must not land on, filled as the names are drawn. */
        const namedBoxes: Array<{
            key: number;
            text: string;
            x: number;
            y: number;
            width: number;
            height: number;
        }> = [];

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
                context.fillStyle = strong ? palette.ink : palette.inkSoft;
                context.textBaseline = "middle";
                const x = toScreenX(node.x) + node.radius + 7;
                const y = toScreenY(node.y);
                // Paper drawn under the letterforms keeps names legible over dense regions
                // without a box or a shadow behind each one.
                context.strokeStyle = palette.page;
                context.lineWidth = 3.5;
                context.lineJoin = "round";
                context.strokeText(text, x, y);
                context.fillText(text, x, y);
                const measured = context.measureText(text).width;
                const lineHeight = strong ? 16 : 13;
                namedBoxes.push({
                    key: -1,
                    text: "",
                    x,
                    y: y - lineHeight / 2,
                    width: measured,
                    height: lineHeight,
                });
            }
        }

        /*
         * What each connection is.
         *
         * The subject is whatever the pointer is on, or the root when it is on nothing - the
         * same precedence the spatial view uses, so moving between renderers does not change
         * which connections are being explained.
         *
         * The choice of which to name is recomputed only when that subject changes. It depends
         * on the graph, not on the camera; only the positions are per-frame, and those are an
         * affine transform of coordinates this function already has.
         */
        const labelView = labelViewRef.current;
        if (labelView) {
            const subject = hovered ?? (graph.rootId === null ? null : graph.index.get(graph.rootId) ?? null);

            if (subject !== labelSubjectRef.current) {
                labelSubjectRef.current = subject;
                if (subject === null) {
                    picksRef.current = [];
                    labelView.setLabels([]);
                } else {
                    /* Only the connections this diagram actually drew are eligible. The
                       neighbourhood is capped at two rings, so a subject has edges in the
                       artifact that are not lines on this canvas, and naming one of those would
                       put a phrase beside a line it does not belong to. */
                    const drawn = new Map<number, number>();
                    graph.edges.forEach((planarEdge, i) => {
                        if (planarEdge.a === subject || planarEdge.b === subject) {
                            drawn.set(planarEdge.edge, i);
                        }
                    });
                    planarEdgeRef.current = drawn;
                    const picks = pickEdgeLabels(
                        world,
                        predicatesRef.current,
                        graph.nodes[subject].id,
                        edgeLabelBudget(width),
                        [...drawn.keys()],
                    );
                    picksRef.current = picks;
                    pointsRef.current = new Float32Array(picks.length * LABEL_STRIDE);
                    labelView.setLabels(picks);
                }
            }

            const picks = picksRef.current;
            if (picks.length > 0) {
                const points = pointsRef.current;
                picks.forEach((pick, i) => {
                    const base = i * LABEL_STRIDE;
                    const planarIndex = planarEdgeRef.current.get(pick.edge);
                    if (planarIndex === undefined) {
                        points[base] = 0;
                        return;
                    }
                    const edge = graph.edges[planarIndex];
                    /* Oriented from the subject outward, so the fractions mean the same thing
                       here as they do in the spatial view: a label slides away from the thing
                       being described, not away from whichever end the artifact stored first. */
                    const from = edge.a === subject ? graph.nodes[edge.a] : graph.nodes[edge.b];
                    const to = edge.a === subject ? graph.nodes[edge.b] : graph.nodes[edge.a];
                    const ax = toScreenX(from.x);
                    const ay = toScreenY(from.y);
                    const bx = toScreenX(to.x);
                    const by = toScreenY(to.y);
                    LABEL_FRACTIONS.forEach((t, f) => {
                        points[base + 1 + f * 2] = ax + (bx - ax) * t;
                        points[base + 2 + f * 2] = ay + (by - ay) * t;
                    });
                    // This projection is affine, so unlike the spatial one there is no point
                    // that can land behind the viewer. Everything it produces is usable.
                    points[base] = 1;
                });
                namedBoxesRef.current = namedBoxes;
                labelView.update(points, { width, height });
            }
        }
    }, [labels, world]);

    /* The overlay outlives individual neighbourhoods; only its contents change. */
    useEffect(() => {
        const stage = stageRef.current;
        if (!stage) return;
        const view = new EdgeLabelView(
            stage,
            edgeLabelBudget(stage.clientWidth),
            (edge) => inspectRef.current(edge),
            // Filled during the draw pass, where the names' boxes are already known.
            () => namedBoxesRef.current,
        );
        labelViewRef.current = view;
        return () => {
            labelViewRef.current = null;
            view.destroy();
        };
    }, []);

    /* A new neighbourhood invalidates whatever was being named in the last one. */
    useEffect(() => {
        labelSubjectRef.current = null;
    }, [root, scope]);

    /* -------------------------------------------------------------- loop - */

    useEffect(() => {
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
                if (scope === "focus" && !sleepingRef.current) {
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
    }, [draw, scope]);

    /* A sleeping graph still has to repaint when the theme changes: the loop is running but
       the simulation is not, and nothing else would mark the canvas dirty. */
    useEffect(() => {
        if (palette) draw();
    }, [palette, draw]);

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
        /* In the world projection the positions are the artifact's, so a node cannot be
           dragged: moving one would claim the arrangement is live when it is precomputed, and
           the next reload would silently put it back. Panning still works. */
        const grabbable = scope === "focus" && hit !== null;
        if (grabbable && hit !== null) {
            graph.nodes[hit].held = true;
            sleepingRef.current = false;
        }
        dragRef.current = {
            kind: grabbable ? "node" : "canvas",
            node: grabbable ? hit : null,
            lastX: screenX,
            lastY: screenY,
            originX: screenX,
            originY: screenY,
            kindOfPointer:
                event.pointerType === "touch" || event.pointerType === "pen"
                    ? event.pointerType
                    : "mouse",
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
        /*
         * Travel from the press, not between two moves.
         *
         * This read `Math.abs(dx) > 1 || Math.abs(dy) > 1` on the per-event delta, and that was
         * a release blocker rather than an imprecision. A slow pan - a careful trackbad drag, a
         * finger, or any pan whose moves the browser coalesced - arrives one pixel at a time, so
         * the flag never latched, the release was classified as a click, the click hit empty
         * canvas, and a reader who was only panning was returned to the whole corpus. The
         * thresholds are in `gesture.ts` with the platform sources for them.
         */
        if (
            Math.hypot(screenX - drag.originX, screenY - drag.originY) >
            GESTURE_SLOP[drag.kindOfPointer]
        ) {
            drag.moved = true;
        }

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

    /*
     * A cancelled gesture completes nothing.
     *
     * `onPointerCancel` was wired straight to the release handler, so whenever the browser took
     * a gesture over - which it does every time a reader scrolls past with a finger that landed
     * here - the handler ran with `moved` still false and cleared the reader's subject. It also
     * released a capture the browser had already dropped, which throws.
     */
    const onPointerCancel = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        const drag = dragRef.current;
        dragRef.current = null;
        if (graph && drag?.node !== null && drag?.node !== undefined) {
            graph.nodes[drag.node].held = false;
            sleepingRef.current = false;
        }
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
        }
    };

    const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        const drag = dragRef.current;
        dragRef.current = null;
        if (!graph || !drag) return;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
        }
        if (drag.node !== null) {
            graph.nodes[drag.node].held = false;
            sleepingRef.current = false;
            // A release with no movement is a click, not a throw.
            if (!drag.moved) onSelect(graph.nodes[drag.node].id);
        } else if (!drag.moved) {
            /*
             * A tap that moved nothing. In the world projection nodes are not draggable, so a
             * tap on one still has to select it.
             *
             * A tap on empty canvas used to call `onSelect(null)`, and that single line was the
             * reported release blocker: it reached a state transition that demoted Focus to
             * World, so a stray tap - or, through the threshold bug above, a slow pan -
             * discarded the subject a reader was studying. A canvas has no business deciding
             * that the reader has finished with a subject. Leaving one is a control in the
             * chrome and the Escape key, both owned by the page.
             *
             * The inspected relationship is still dismissed, because that *is* about the
             * canvas: it annotates a line, and tapping away from the line is done with it.
             */
            const { x, y } = toGraph(event);
            const hit = pickPlanar(graph, x, y);
            if (hit !== null) onSelect(graph.nodes[hit].id);
            else onInspectEdge(null);
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
        <div className="va-planar" ref={stageRef}>
            <canvas
                aria-label="The selected subject and its connections as a diagram. The same connections are listed beside it."
                className="va-planar-canvas"
                onPointerCancel={onPointerCancel}
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
            {scope === "focus" && root === null && (
                <p className="va-planar-empty">
                    Choose a subject to pull its connections apart. Search above, or open the
                    world to find one spatially.
                </p>
            )}
        </div>
    );
}
