"use client";

import { useEffect, useRef, useState } from "react";

/**
 * The homepage constellation: a small, live, pointer-reactive field drawn from the real
 * entity graph.
 *
 * ## Why canvas and not a graph library
 *
 * The whole surface is 24 nodes and 27 edges. A force layout over that is about sixty lines
 * and a few hundred microseconds a frame. Reaching for three.js would add roughly 200 KB to
 * the front door of the site to draw something that is not three-dimensional, and reaching
 * for the Cytoscape instance the graph page already uses would bring its full interaction
 * model and a visual language built for a different job. Neither earns its weight here.
 *
 * ## Why it does not glow
 *
 * The obvious rendering of a knowledge graph on a dark ground is bright nodes with bloom and
 * a bright edge haze. That picture has an owner already: it reads as a crypto dashboard, and
 * a Vedic corpus rendered that way would look like it was trying to be a technology product.
 *
 * So the drawing vocabulary is the brand's own: a faint drafting grid, hairline edges, and
 * nodes as small filled marks rather than spheres. Deities are diamonds, because the diamond
 * is the mark in the emblem; everything else is a square. Nothing is lit. What separates the
 * foreground from the background is weight and hue, which is how it is separated on paper.
 */

type Node = { id: string; type: string; label: string; deity: boolean; degree: number };
type Edge = { s: string; t: string; p: string };
type Slice = { nodes: Node[]; edges: Edge[] };

type Body = {
    node: Node;
    x: number;
    y: number;
    vx: number;
    vy: number;
    /** Radius in layout units, from degree. Mass follows it, so hubs drift less. */
    r: number;
};

const PADDING = 34;

/**
 * A small deterministic PRNG so the field has the same starting shape on the server-rendered
 * first frame and on every reload. `Math.random` would give a different composition each
 * time, which on a homepage reads as instability rather than as life.
 */
function seeded(seed: number) {
    let state = seed >>> 0;
    return () => {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 0x100000000;
    };
}

export function Constellation({ slice }: { slice: Slice }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [hovered, setHovered] = useState<Node | null>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const random = seeded(0x5eed);
        const index = new Map(slice.nodes.map((n, i) => [n.id, i]));

        let width = 0;
        let height = 0;
        let bodies: Body[] = [];
        const pointer = { x: 0, y: 0, inside: false };
        let hoveredIndex = -1;
        let frame = 0;
        let settling = 0;

        const edges = slice.edges
            .map((e) => ({ a: index.get(e.s) ?? -1, b: index.get(e.t) ?? -1 }))
            .filter((e) => e.a >= 0 && e.b >= 0);

        const layout = () => {
            const rect = canvas.getBoundingClientRect();
            const ratio = Math.min(window.devicePixelRatio || 1, 2);
            width = rect.width;
            height = rect.height;
            canvas.width = Math.round(width * ratio);
            canvas.height = Math.round(height * ratio);
            context.setTransform(ratio, 0, 0, ratio, 0, 0);
        };

        const seed = () => {
            /* Start on a ring rather than at random points. A random cloud takes hundreds of
               frames to stop looking like a random cloud, and the first thing a visitor sees
               should already be a structure that is settling, not noise that is resolving. */
            bodies = slice.nodes.map((node, i) => {
                const angle = (i / slice.nodes.length) * Math.PI * 2 + random() * 0.4;
                const spread = node.deity ? 0.34 : 0.46;
                const radius = Math.min(width, height) * spread * (0.72 + random() * 0.4);
                return {
                    node,
                    x: width / 2 + Math.cos(angle) * radius,
                    y: height / 2 + Math.sin(angle) * radius * 0.78,
                    vx: 0,
                    vy: 0,
                    r: 3 + Math.min(node.degree, 5) * 0.9,
                };
            });
        };

        const step = () => {
            const centreX = width / 2;
            const centreY = height / 2;

            for (let i = 0; i < bodies.length; i++) {
                const a = bodies[i];
                for (let j = i + 1; j < bodies.length; j++) {
                    const b = bodies[j];
                    const dx = b.x - a.x;
                    const dy = b.y - a.y;
                    const distanceSq = dx * dx + dy * dy || 0.01;
                    const distance = Math.sqrt(distanceSq);
                    const push = 950 / distanceSq;
                    const ux = (dx / distance) * push;
                    const uy = (dy / distance) * push;
                    a.vx -= ux;
                    a.vy -= uy;
                    b.vx += ux;
                    b.vy += uy;
                }
                /* Pull toward the centre, weakly, so the field cannot slowly evacuate the
                   frame. Vertical pull is stronger because the panel is wider than it is
                   tall and an isotropic well would leave the corners empty. */
                a.vx += (centreX - a.x) * 0.0028;
                a.vy += (centreY - a.y) * 0.0042;
            }

            for (const edge of edges) {
                const a = bodies[edge.a];
                const b = bodies[edge.b];
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const distance = Math.sqrt(dx * dx + dy * dy) || 0.01;
                const force = (distance - 74) * 0.0034;
                const ux = (dx / distance) * force;
                const uy = (dy / distance) * force;
                a.vx += ux;
                a.vy += uy;
                b.vx -= ux;
                b.vy -= uy;
            }

            if (pointer.inside && !reduced) {
                /* The pointer nudges rather than grabs. A strong attractor turns the field
                   into a toy and pulls the labels into a pile under the cursor; this is just
                   enough for the field to acknowledge that someone is there. */
                for (const body of bodies) {
                    const dx = pointer.x - body.x;
                    const dy = pointer.y - body.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    if (distance > 180 || distance < 1) continue;
                    const pull = (1 - distance / 180) * 0.05;
                    body.vx += dx * pull * 0.1;
                    body.vy += dy * pull * 0.1;
                }
            }

            const damping = settling < 220 ? 0.86 : 0.93;
            for (const body of bodies) {
                body.vx *= damping;
                body.vy *= damping;
                body.x += body.vx;
                body.y += body.vy;
                body.x = Math.max(PADDING, Math.min(width - PADDING, body.x));
                body.y = Math.max(PADDING, Math.min(height - PADDING, body.y));
            }
            settling++;
        };

        /* The three busiest deities in the slice, resolved once. */
        const named = slice.nodes
            .map((node, i) => ({ i, node }))
            .filter((entry) => entry.node.deity)
            .sort((a, b) => b.node.degree - a.node.degree)
            .slice(0, 3)
            .map((entry) => entry.i);

        const styles = getComputedStyle(canvas);
        const labelFont =
            styles.getPropertyValue("--va-font-ui").trim() || "system-ui, sans-serif";
        const ink = styles.getPropertyValue("--va-constellation-ink").trim() || "#E9E3D6";
        const line = styles.getPropertyValue("--va-constellation-line").trim() || "#3A3B33";
        const rubric = styles.getPropertyValue("--va-constellation-accent").trim() || "#C9694F";
        const gold = styles.getPropertyValue("--va-constellation-gold").trim() || "#B49A62";

        const draw = () => {
            context.clearRect(0, 0, width, height);

            /* The drafting grid, at the threshold of visible. It is the same device as the
               brand's paper textures: construction lines that were never erased. */
            context.strokeStyle = line;
            context.globalAlpha = 0.35;
            context.lineWidth = 1;
            context.beginPath();
            for (let x = 0; x <= width; x += 56) {
                context.moveTo(Math.round(x) + 0.5, 0);
                context.lineTo(Math.round(x) + 0.5, height);
            }
            for (let y = 0; y <= height; y += 56) {
                context.moveTo(0, Math.round(y) + 0.5);
                context.lineTo(width, Math.round(y) + 0.5);
            }
            context.stroke();
            context.globalAlpha = 1;

            const active = hoveredIndex >= 0 ? hoveredIndex : -1;
            const connected = new Set<number>();
            if (active >= 0) {
                connected.add(active);
                for (const edge of edges) {
                    if (edge.a === active) connected.add(edge.b);
                    if (edge.b === active) connected.add(edge.a);
                }
            }

            context.lineWidth = 1;
            for (const edge of edges) {
                const a = bodies[edge.a];
                const b = bodies[edge.b];
                const lit = active >= 0 && (edge.a === active || edge.b === active);
                context.strokeStyle = lit ? rubric : line;
                context.globalAlpha = active >= 0 ? (lit ? 0.95 : 0.22) : 0.6;
                context.beginPath();
                context.moveTo(a.x, a.y);
                context.lineTo(b.x, b.y);
                context.stroke();
            }
            context.globalAlpha = 1;

            /*
             * A few names are drawn at rest, not only on hover.
             *
             * Without them the panel is an abstract scatter, and an abstract scatter beside a
             * headline about the Vedas is decoration. Three names make it legibly a picture of
             * this corpus, and three is few enough that the field still reads as a field.
             * Anything requiring a pointer to discover is also unavailable on a touch screen,
             * where most first visits happen.
             */
            context.font = `500 11px ${labelFont}`;
            context.textAlign = "center";
            for (const i of named) {
                if (active >= 0 && !connected.has(i)) continue;
                const body = bodies[i];
                context.fillStyle = ink;
                context.globalAlpha = i === active ? 1 : 0.72;
                context.fillText(body.node.label, body.x, body.y - body.r - 8);
            }
            context.globalAlpha = 1;

            for (let i = 0; i < bodies.length; i++) {
                const body = bodies[i];
                const dim = active >= 0 && !connected.has(i);
                context.globalAlpha = dim ? 0.3 : 1;
                context.fillStyle = body.node.deity ? (i === active ? rubric : gold) : ink;
                const r = body.r + (i === active ? 2 : 0);

                if (body.node.deity) {
                    context.beginPath();
                    context.moveTo(body.x, body.y - r);
                    context.lineTo(body.x + r, body.y);
                    context.lineTo(body.x, body.y + r);
                    context.lineTo(body.x - r, body.y);
                    context.closePath();
                    context.fill();
                } else {
                    const s = r * 1.5;
                    context.fillRect(body.x - s / 2, body.y - s / 2, s, s);
                }
            }
            context.globalAlpha = 1;
        };

        let raf = 0;
        const loop = () => {
            /* Once settled, step at a third of the frame rate. The drift is meant to be
               almost imperceptible, and running the simulation flat out to produce
               imperceptible movement is the definition of wasted battery. */
            if (!reduced || settling < 220) {
                if (settling < 220 || frame % 3 === 0) step();
            }
            draw();
            frame++;
            raf = requestAnimationFrame(loop);
        };

        const onPointerMove = (event: PointerEvent) => {
            const rect = canvas.getBoundingClientRect();
            pointer.x = event.clientX - rect.left;
            pointer.y = event.clientY - rect.top;
            pointer.inside = true;

            let nearest = -1;
            let best = 26 * 26;
            for (let i = 0; i < bodies.length; i++) {
                const dx = bodies[i].x - pointer.x;
                const dy = bodies[i].y - pointer.y;
                const d = dx * dx + dy * dy;
                if (d < best) {
                    best = d;
                    nearest = i;
                }
            }
            if (nearest !== hoveredIndex) {
                hoveredIndex = nearest;
                setHovered(nearest >= 0 ? bodies[nearest].node : null);
            }
        };

        const onPointerLeave = () => {
            pointer.inside = false;
            hoveredIndex = -1;
            setHovered(null);
        };

        layout();
        seed();
        const observer = new ResizeObserver(() => {
            const before = { w: width, h: height };
            layout();
            if (before.w === 0) seed();
            else
                for (const body of bodies) {
                    body.x = (body.x / before.w) * width;
                    body.y = (body.y / before.h) * height;
                }
        });
        observer.observe(canvas);
        canvas.addEventListener("pointermove", onPointerMove);
        canvas.addEventListener("pointerleave", onPointerLeave);
        raf = requestAnimationFrame(loop);

        return () => {
            cancelAnimationFrame(raf);
            observer.disconnect();
            canvas.removeEventListener("pointermove", onPointerMove);
            canvas.removeEventListener("pointerleave", onPointerLeave);
        };
    }, [slice]);

    return (
        <div className="va-constellation">
            <canvas aria-hidden="true" className="va-constellation-canvas" ref={canvasRef} />
            <p className="va-constellation-readout" aria-live="polite">
                {hovered ? (
                    <>
                        <span className="va-constellation-name">{hovered.label}</span>
                        <span className="va-constellation-kind">
                            {hovered.deity ? "deity" : hovered.type.toLowerCase().replace(/_/g, " ")}
                        </span>
                    </>
                ) : (
                    <span className="va-constellation-kind">
                        {slice.nodes.length} named things, and what joins them
                    </span>
                )}
            </p>
        </div>
    );
}
