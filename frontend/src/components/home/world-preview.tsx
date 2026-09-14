"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Color } from "three";
import { composeWorld } from "@/lib/world/artifact";
import { probeCapability } from "@/lib/world/capability";
import { WorldEngine } from "@/lib/world/engine";
import { GROUP_NAMES, useScopedGraphPalette } from "@/lib/world/palette";

/**
 * The front door: a real piece of the Knowledge World, turning slowly.
 *
 * ## What this replaces, and why replacing rather than adjusting was the only option
 *
 * The homepage carried a hand-built diagram - twenty-four invented nodes on a drafting grid,
 * deities as diamonds and everything else as squares, its own palette, its own physics loop. It
 * was carefully made, and its own docstring argued against using three.js on the grounds that
 * the thing it drew was not three-dimensional. That was true of what it drew and false of what
 * the product is. A reader met an abstract diagram, clicked through, and arrived somewhere with
 * no visual relationship to it: different shapes, different colours, different behaviour. The
 * front door described a product that did not exist.
 *
 * ## How continuity is guaranteed rather than intended
 *
 * This does not reimplement the world's look. It builds a fifty-node `World` and hands it to
 * `WorldEngine` - the same class, shaders, sizing rule and palette the graph page runs. There is
 * no second renderer that could drift, because there is no second renderer. If the graph's nodes
 * change size or its groups change colour, this changes with them, without anyone remembering to.
 *
 * The nodes are real: real ids, real groups, real corpus degrees, and the coordinates the offline
 * layout gave them among all 35,370. Clicking one opens that subject in the graph. Nothing here
 * is representative of the data - it *is* the data.
 *
 * ## What it deliberately does not do
 *
 * It does not zoom. OrbitControls takes the wheel, and a hero that swallows the wheel traps a
 * reader trying to scroll past it. Dragging to turn is offered; scrolling belongs to the page.
 *
 * It stops when it is not being looked at. The diagram this replaces ran its physics loop
 * unconditionally - measured at 4 to 5 per cent of a core, forever, including while scrolled
 * past and while the tab was in the background - and kept redrawing even under
 * `prefers-reduced-motion`. Both are fixed here rather than inherited.
 */

export type HeroSliceNode = {
    id: string;
    label: string;
    group: string;
    degree: number;
    x: number;
    y: number;
    z: number;
};

export type HeroSlice = {
    groups: string[];
    nodes: HeroSliceNode[];
    edges: Array<{ a: number; b: number; predicate: string }>;
};

/**
 * Unit coordinates, enlarged to the scale the engine is tuned for.
 *
 * Node sizes in the shader are world units divided by view depth, tuned against an artifact whose
 * half-extent is 1000. Handing the engine a cloud of radius 1 would not produce a small graph, it
 * would produce fifty enormous discs, because the camera would sit correspondingly close.
 */
const WORLD_RADIUS = 420;

function toWorld(slice: HeroSlice) {
    const count = slice.nodes.length;
    const positions = new Float32Array(count * 3);
    const nodeGroup = new Uint8Array(count);
    const nodeDegree = new Uint16Array(count);

    slice.nodes.forEach((node, i) => {
        positions[i * 3] = node.x * WORLD_RADIUS;
        positions[i * 3 + 1] = node.y * WORLD_RADIUS;
        positions[i * 3 + 2] = node.z * WORLD_RADIUS;
        /* Indexed against the palette's own group order rather than the slice's, so a colour is
           looked up the same way here as everywhere else. An unknown group falls to "other"
           rather than to index zero, which would silently paint it as a deity. */
        const group = GROUP_NAMES.indexOf(node.group as (typeof GROUP_NAMES)[number]);
        nodeGroup[i] = group >= 0 ? group : GROUP_NAMES.indexOf("other");
        // Uint16 caps at 65,535 and the busiest node in the corpus has 7,347 connections, so
        // the real figure fits and node size means the same thing it means in the graph.
        nodeDegree[i] = Math.min(node.degree, 65535);
    });

    const edgeTypes = [...new Set(slice.edges.map((edge) => edge.predicate))].sort();
    const edgeTypeIndex = new Map(edgeTypes.map((name, i) => [name, i]));
    const edgePairs = new Uint32Array(slice.edges.length * 2);
    const edgeType = new Uint8Array(slice.edges.length);
    slice.edges.forEach((edge, i) => {
        edgePairs[i * 2] = edge.a;
        edgePairs[i * 2 + 1] = edge.b;
        edgeType[i] = edgeTypeIndex.get(edge.predicate) ?? 0;
    });

    return composeWorld({
        groups: [...GROUP_NAMES],
        // No node types are carried in the slice, and an empty list is how that is said. Filling
        // it would make `nodeType[i]` index a name nobody established.
        types: [],
        edgeTypes,
        positions,
        nodeGroup,
        nodeDegree,
        edgePairs,
        edgeType,
    });
}

export function WorldPreview({ slice }: { slice: HeroSlice }) {
    const router = useRouter();
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const engineRef = useRef<WorldEngine | null>(null);
    const [named, setNamed] = useState<HeroSliceNode | null>(null);
    /*
     * Whether this device can draw the spatial preview at all.
     *
     * Derived once at first render rather than discovered in an effect: it is a fact about the
     * machine, not a subscription to anything, and setting it from an effect would render the
     * WebGL branch and then immediately replace it.
     */
    const [flat, setFlat] = useState(
        () => typeof window !== "undefined" && !probeCapability().webgl,
    );
    /* The panel is carbon in both themes, so the colours are read from inside it rather than
       from the page. Read from the page, the preview cleared to ivory inside a carbon frame -
       the same disagreement between a canvas and its surroundings that the graph page had to be
       corrected for. */
    const [scope, setScope] = useState<HTMLDivElement | null>(null);
    const palette = useScopedGraphPalette(scope);

    /* Paused unless the canvas is both on screen and in a visible tab. Held in a ref because the
       engine is built asynchronously and the observers may fire before it exists. */
    const wanted = useRef(false);

    const open = useCallback(
        (node: HeroSliceNode | null) => {
            const target = node
                ? `/graph?view=focus&renderer=3d&node=${encodeURIComponent(node.id)}`
                : "/graph?view=world&renderer=3d";
            router.push(target);
        },
        [router],
    );

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !palette) return;

        if (flat) return;

        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        let engine: WorldEngine;
        try {
            engine = new WorldEngine({
                canvas,
                world: toWorld(slice),
                groupColours: palette.groups,
                background: new Color(palette.page),
                edgeColour: new Color(palette.line),
                accentColour: new Color(palette.accent),
                reducedMotion: reduced,
                /* Twice the rotation per frame at half the frame rate, because OrbitControls
                   advances `autoRotate` per update call rather than per second. Same drift. */
                controls: { zoom: false, pan: false, autoRotate: 0.64 },
                maxFps: 30,
                // Fifty lines, not 185,693, so they carry the weight of drawn strokes rather
                // than of ink accumulating.
                edgeWeight: 14,
                events: {
                    onHover: (index) => setNamed(index === null ? null : slice.nodes[index]),
                    // A lost context on the homepage is not worth a notice. The panel keeps its
                    // heading and its link, which is the whole of what it has to do.
                    onLost: () => setFlat(true),
                },
            });
        } catch {
            /* Constructing the renderer threw - a driver refusing a context, a shader failing to
               compile. That is the same class of event as `onLost` above and is reported the same
               way; the lint rule cannot tell a failure report from ordinary effect state, and
               falling back to the flat drawing is the correct response to both. */
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setFlat(true);
            return;
        }

        engineRef.current = engine;
        engine.setPaused(!wanted.current);
        engine.start();
        // Frames the slice rather than trusting the default camera distance, which is set for a
        // world a thousand units across.
        engine.fitNodes(
            slice.nodes.map((_, i) => i),
            0,
            // Tighter than the path default, and with no distance floor: this is a small cloud
            // in a small panel, and the path's framing leaves it adrift in the middle of it.
            { spread: 1.45, floor: 0 },
        );

        const onResize = () => engine.resize();
        window.addEventListener("resize", onResize);

        return () => {
            window.removeEventListener("resize", onResize);
            engineRef.current = null;
            engine.dispose();
        };
    }, [palette, slice, flat]);

    /*
     * Draw only while visible.
     *
     * Two independent reasons to stop - scrolled out of view, and the tab in the background -
     * combined into one wish, so neither can switch the loop back on while the other still wants
     * it off.
     */
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        let onScreen = false;
        const apply = () => {
            const next = onScreen && document.visibilityState === "visible";
            wanted.current = next;
            engineRef.current?.setPaused(!next);
        };

        const observer = new IntersectionObserver(
            ([entry]) => {
                onScreen = entry.isIntersecting;
                apply();
            },
            { threshold: 0.05 },
        );
        observer.observe(canvas);
        document.addEventListener("visibilitychange", apply);

        return () => {
            observer.disconnect();
            document.removeEventListener("visibilitychange", apply);
        };
    }, [flat]);

    if (flat) return <WorldPreviewFlat slice={slice} onOpen={open} />;

    return (
        <div className="va-world-preview" ref={setScope}>
            <canvas
                ref={canvasRef}
                className="va-world-preview-canvas"
                /* The list beside this canvas is the real content for a screen reader; a canvas
                   has nothing to offer one. */
                aria-hidden="true"
                onPointerMove={(event) => {
                    const rect = event.currentTarget.getBoundingClientRect();
                    engineRef.current?.hover(
                        event.clientX - rect.left,
                        event.clientY - rect.top,
                    );
                }}
                onPointerLeave={() => setNamed(null)}
                onClick={(event) => {
                    const rect = event.currentTarget.getBoundingClientRect();
                    const index = engineRef.current?.pick(
                        event.clientX - rect.left,
                        event.clientY - rect.top,
                    );
                    open(index === null || index === undefined ? null : slice.nodes[index]);
                }}
            />
            <p className="va-world-preview-readout" aria-hidden="true">
                {named ? (
                    <>
                        <span className="va-world-preview-name">{named.label}</span>
                        <span className="va-world-preview-kind">
                            {named.group.replace(/-/g, " ")} · {named.degree.toLocaleString()}{" "}
                            connections
                        </span>
                    </>
                ) : (
                    <span className="va-world-preview-kind">
                        Drag to turn. Click any subject to open it.
                    </span>
                )}
            </p>
        </div>
    );
}

/**
 * The same slice, drawn flat, where there is no WebGL to draw it with.
 *
 * Not a placeholder and not a different picture: the same fifty nodes, the same group colours,
 * the same sizing, projected along z. A reader without a GPU sees the corpus, not an apology.
 * It does not turn - a rotation here would be re-implementing the engine's camera on a 2D canvas,
 * which is the duplication this whole component exists to avoid.
 */
function WorldPreviewFlat({
    slice,
    onOpen,
}: {
    slice: HeroSlice;
    onOpen: (node: HeroSliceNode | null) => void;
}) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [scope, setScope] = useState<HTMLDivElement | null>(null);
    const palette = useScopedGraphPalette(scope);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !palette) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        const ratio = Math.min(window.devicePixelRatio, 2);
        const { clientWidth: width, clientHeight: height } = canvas;
        canvas.width = Math.round(width * ratio);
        canvas.height = Math.round(height * ratio);
        context.setTransform(ratio, 0, 0, ratio, 0, 0);

        const radius = Math.min(width, height) * 0.42;
        const at = (node: HeroSliceNode) => ({
            x: width / 2 + node.x * radius,
            y: height / 2 - node.y * radius,
        });

        context.fillStyle = palette.page;
        context.fillRect(0, 0, width, height);

        context.strokeStyle = palette.line;
        context.lineWidth = 1;
        context.globalAlpha = 0.5;
        for (const edge of slice.edges) {
            const a = at(slice.nodes[edge.a]);
            const b = at(slice.nodes[edge.b]);
            context.beginPath();
            context.moveTo(a.x, a.y);
            context.lineTo(b.x, b.y);
            context.stroke();
        }

        context.globalAlpha = 0.85;
        // Back to front, so the nearer subjects sit over the further ones as they do in the
        // spatial view.
        for (const node of [...slice.nodes].sort((x, y) => x.z - y.z)) {
            const group = GROUP_NAMES.indexOf(node.group as (typeof GROUP_NAMES)[number]);
            const point = at(node);
            context.fillStyle = palette.groupCss[group >= 0 ? group : GROUP_NAMES.length - 1];
            context.beginPath();
            context.arc(point.x, point.y, 2.5 + Math.cbrt(node.degree) * 0.7, 0, Math.PI * 2);
            context.fill();
        }
    }, [palette, slice]);

    return (
        <div className="va-world-preview" data-flat="true" ref={setScope}>
            <canvas ref={canvasRef} className="va-world-preview-canvas" aria-hidden="true" />
            <p className="va-world-preview-readout" aria-hidden="true">
                <span className="va-world-preview-kind">
                    Drawn flat on this device.{" "}
                    <button type="button" onClick={() => onOpen(null)}>
                        Open the graph
                    </button>
                </span>
            </p>
        </div>
    );
}
