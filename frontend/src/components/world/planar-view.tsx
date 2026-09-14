"use client";

import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import type { World, WorldLabels } from "@/lib/world/artifact";
import { EdgeLabelView } from "@/lib/world/edge-label-view";
import {
    LABEL_FRACTIONS,
    LABEL_STRIDE,
    edgeLabelBudget,
    pickEdgeLabels,
    type EdgeLabelPick,
} from "@/lib/world/edge-labels";
import { focusBudgetForBand, useFocusNeighbourhood } from "@/lib/world/focus";
import { GESTURE_SLOP, type PointerKind } from "@/lib/world/gesture";
import { GROUP_NAMES, useGraphPalette, type GraphPalette } from "@/lib/world/palette";
import {
    PREROLL_LIMIT,
    buildFocusScene,
    buildWorldScene,
    isAtRest,
    markRadius,
    pickPlanar,
    planarBounds,
    preroll,
    respaceFocusScene,
    settleSlots,
    stepPlanar,
    type PlanarGraph,
    type PlanarNode,
} from "@/lib/world/planar";
import { usePredicateSemantics } from "@/lib/world/predicates";

/**
 * The planar view.
 *
 * Canvas 2D rather than WebGL, deliberately. The scene is a few dozen marks, so the GPU has
 * nothing to do that the 2D context cannot; what the 2D context has instead is real line joins,
 * real antialiasing, and the browser's own text rendering, which matters because half of what
 * is drawn here is Sanskrit with combining marks. A WebGL version of this would be more
 * impressive to describe and worse to read.
 *
 * ## Everything here is measured in CSS pixels
 *
 * Both scenes are authored in px at scale 1 - see `planar.ts` - so `fit` translates and does
 * not scale, the drawn radius and the hit target come from the same function, and the
 * separation the layout promises is the separation on the glass. The previous version authored
 * in graph units and let `fit` resolve to 0.317-0.339, which is how every Focus leaf came out
 * at 3.85 px with a 2-5 px hit target regardless of viewport.
 */

export type PlanarSelection = { index: number; node: number };

/**
 * What the page may ask this canvas to do.
 *
 * Deliberately one verb. A canvas is told what to draw through props, and the only thing the
 * chrome can usefully ask of it that is not a prop is to rearrange what is already there - a
 * request about the drawing rather than about the data. Anything that changes *what* is shown
 * goes through `root`, the budget and `focus.ts`, so there is no second path to the same state.
 */
export type PlanarActions = {
    /**
     * Re-space the current focus neighbourhood. Does not change what is shown.
     *
     * Cycles: each call pushes the slots further out, and the call that would take the diagram
     * past what the band can hold returns it to the authored layout. So there is no disabled
     * state to keep in step and no press that does nothing. See `respaceFocusScene`.
     */
    respaceFocus(): void;
};

/**
 * One pair of zoom limits, read by the wheel, the pinch and `fit`.
 *
 * There were three, and they disagreed: `fit` capped the scale at 2.4, the wheel clamped to
 * [0.18, 3.2], and the painter multiplied the radius by `clamp(scale, 0.7, 1.6)` - so the mark
 * stopped growing at 1.6 while the diagram kept growing to 3.2, and stopped shrinking at 0.7
 * while the diagram shrank to 0.18. The floor is 0.35 rather than 0.18 because an authored
 * scene starts at 1 and 0.18 of a Focus diagram is a smudge; a reader who wants the whole of an
 * expanded 200-orb scene can still reach it.
 */
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 3.2;

/**
 * Names drawn on a Focus scene besides the subject and whatever is under the pointer.
 *
 * There were three hand-picked line alphas here - 0.5, 0.72, 0.9 over `--va-text-tertiary` -
 * chosen because the previous `--va-line-strong` hairline at 0.34 measured 1.14:1 light and
 * 1.18:1 dark and no alpha could have saved it: that token is 1.51:1 against the page even fully
 * opaque. They are gone, and nothing here composites a line any more. Every stroke is one of the
 * three relation tokens at full opacity, each of which was derived for the job it now does, and
 * the weight that separates them is line width and paint order. An alpha chosen in a renderer is
 * an alpha no audit can see - `--va-graph-alpha-*` exists for the ones that survive, and none of
 * these needed to.
 */
const FOCUS_NAME_CAP = 8;

/**
 * Widths an aggregate line may be drawn at, in px.
 *
 * A ladder rather than a continuous function, and only because of the batching in `draw`: a
 * continuous width is one stroke per line, and this artifact has 515 constellation pairs. Four
 * classes over a weight range of 1 to 3,303 is more resolution than a reader takes off a line
 * width in any case, and the exact figure belongs in text.
 */
const AGGREGATE_WIDTHS = [0.8, 1.4, 2.2, 3.2];

/**
 * Which width class a line of this weight falls in.
 *
 * Logarithmic against the heaviest line in the scene. Linear, the busiest pair of
 * constellations - 3,303 bridge relationships against a median of 56 - would be the only
 * visible line and the other 514 would all be hairlines.
 */
function aggregateClass(weight: number, heaviest: number): number {
    if (weight <= 1 || heaviest <= 1) return 0;
    const share = Math.log2(weight) / Math.log2(heaviest);
    return Math.min(AGGREGATE_WIDTHS.length - 1, Math.floor(share * AGGREGATE_WIDTHS.length));
}

/** Canvas size change, in px, worth re-laying the scene out for. */
const RESIZE_STEP = 8;

/**
 * The band, rounded to `RESIZE_STEP`.
 *
 * The neighbour budget and the slot radii are both functions of the band, and the band is now a
 * function of the subject panel's measured height - which, since the panel's inner scroller was
 * removed, grows and shrinks with its content. Quantising means a panel that settles four pixels
 * taller does not re-select the neighbourhood and re-lay the scene out; only a change a reader
 * could see does.
 */
function bucket(value: number): number {
    return Math.round(value / RESIZE_STEP) * RESIZE_STEP;
}

export function PlanarView({
    world,
    labels,
    root,
    scope,
    onSelect,
    onInspectEdge,
    inspectedEdge = null,
    safeArea,
    ref,
}: {
    world: World;
    labels: WorldLabels | null;
    root: number | null;
    /**
     * What this canvas is drawing.
     *
     * "world" draws the composed corpus as its constellations; "focus" draws one subject and
     * the neighbours `focus.ts` curated for it. They share this component because they share a
     * visual language and an interaction model, and because a reader moving between them should
     * feel the same diagram deepening rather than two different tools.
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
    /** The relationship the reader has an explanation open on. See the note in `WorldView`. */
    inspectedEdge?: number | null;
    /**
     * Canvas edges covered by chrome, so the diagram is centred in what a reader can see.
     *
     * Measured for both renderers since the phase that introduced it, and passed to one. On a
     * phone the graph chrome takes 226 px of the top and the subject sheet takes 120 px of the
     * bottom, so a diagram centred in the whole canvas puts the chosen subject behind the
     * sheet - at every one of its three heights. It is also what the neighbour budget is
     * derived from, because the band and the viewport differ by more than a factor of two and
     * the band is the one a finger has to reach into.
     */
    safeArea?: { top?: number; right?: number; bottom?: number; left?: number };
    /** See `PlanarActions`. */
    ref?: React.Ref<PlanarActions>;
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
    const nameOrderRef = useRef<{
        graph: PlanarGraph | null;
        always: Array<{ node: PlanarNode; index: number }>;
        ranked: Array<{ node: PlanarNode; index: number }>;
    }>({ graph: null, always: [], ranked: [] });
    /*
     * The palette is a subscription, not a snapshot.
     *
     * Read once at mount, this canvas kept drawing carbon ink and a 3.5-pixel ivory halo
     * around every label after a switch to dark, the halo being the paper colour stroked
     * behind text. On a carbon page that is a glowing outline around every name, which is the
     * precise look this product is built to avoid.
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
    /**
     * Every pointer currently down, by id.
     *
     * A single `dragRef` with `setPointerCapture` was not a multi-touch limitation, it was a
     * corruption: a second finger overwrote the first's record, so the node the first finger
     * was holding stayed held for ever and the release attributed to the wrong pointer. The map
     * also makes the pinch below possible at all.
     */
    const pointersRef = useRef(new Map<number, { x: number; y: number; kind: PointerKind }>());
    const dragRef = useRef<{
        pointerId: number;
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
    const pinchRef = useRef<{ distance: number; midX: number; midY: number } | null>(null);
    const hoverRef = useRef<number | null>(null);
    const frameRef = useRef(0);
    const sleepingRef = useRef(false);
    /**
     * Whether the reader has asked for less motion, and whether the canvas owes a repaint.
     *
     * Both were written and never read. `reducedRef` meant `prefers-reduced-motion` had no
     * effect on this view at all - the spring simulation ran and the inertial pan ran - and
     * `dirtyRef` did not exist, so `draw` was called on every animation frame whatever the
     * state of the simulation. An untouched 2D world repainted its whole scene at 60 Hz for
     * ever, under a docstring that said a diagram nobody is touching costs nothing.
     */
    const reducedRef = useRef(false);
    const dirtyRef = useRef(true);

    const [hoverLabel, setHoverLabel] = useState<string | null>(null);
    const [surface, setSurface] = useState({ width: 0, height: 0 });
    /** Whether the canvas has been measured. Nothing is laid out against a guess. */
    const measured = surface.width > 0;
    /*
     * Whether this artifact can be drawn as a world at all.
     *
     * Derived here rather than recorded from the built scene. It is a fact about the artifact,
     * so a state variable set inside the layout effect would be the same fact held twice, one
     * render apart.
     */
    const constellations = world.manifest.constellations?.length ?? 0;

    const markDirty = useCallback(() => {
        dirtyRef.current = true;
    }, []);

    const insetTop = safeArea?.top ?? 0;
    const insetRight = safeArea?.right ?? 0;
    const insetBottom = safeArea?.bottom ?? 0;
    const insetLeft = safeArea?.left ?? 0;

    /* ------------------------------------------------------------- the band - */

    /**
     * What a reader can actually see and reach, which is neither the canvas nor the viewport.
     *
     * Both the layout and the neighbour budget are derived from this. Measured on a 390x844
     * phone, the chrome takes 225.6 px before anything is drawn and a half-raised sheet leaves
     * 183.1 px of band, which seats twelve orbs at a finger pitch against the sixteen a budget
     * chosen from the viewport would have drawn.
     */
    const band = useMemo(
        () => ({
            width: Math.max(160, bucket(surface.width - insetLeft - insetRight)),
            height: Math.max(120, bucket(surface.height - insetTop - insetBottom)),
        }),
        [surface.width, surface.height, insetTop, insetRight, insetBottom, insetLeft],
    );

    const fit = useCallback(() => {
        const canvas = canvasRef.current;
        const graph = graphRef.current;
        if (!canvas || !graph) return;
        const { minX, minY, maxX, maxY } = planarBounds(graph);
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const bandWidth = Math.max(160, width - insetLeft - insetRight);
        const bandHeight = Math.max(120, height - insetTop - insetBottom);
        /*
         * An authored scene is not scaled. At all.
         *
         * This is what makes the separation guarantee unconditional. `FOCUS_BUDGET_MAX` is 200
         * and one spoke per shown neighbour is not discretionary, so a reader on a narrow band
         * can ask for a scene that does not fit in it - 200 orbs at a 44 px pitch is a 722 px
         * diagram. The two available answers are to shrink the marks until they do fit, which
         * makes a picture that lies about being touchable, or to let the diagram be larger than
         * the band and let the reader pan and zoom out by choice. The second is honest, so it
         * is the one taken: what is given up is "the whole scene is visible at once", and it is
         * given up out loud rather than traded for a broken invariant.
         */
        const spanX = Math.max(1, maxX - minX);
        const spanY = Math.max(1, maxY - minY);
        const scale = graph.authored
            ? 1
            : Math.min((bandWidth * 0.82) / spanX, (bandHeight * 0.82) / spanY, ZOOM_MAX);
        viewRef.current.scale = scale;
        viewRef.current.x = insetLeft + bandWidth / 2 - ((minX + maxX) / 2) * scale;
        viewRef.current.y = insetTop + bandHeight / 2 - ((minY + maxY) / 2) * scale;
        viewRef.current.vx = 0;
        viewRef.current.vy = 0;
        markDirty();
    }, [insetTop, insetRight, insetBottom, insetLeft, markDirty]);

    /**
     * The canvas measures itself, rather than being told once at build time.
     *
     * There was no observer here at all: `fit` ran only when the graph was rebuilt, so rotating
     * a phone, raising the subject sheet or dragging a desktop window left the diagram off
     * centre until the reader selected something else. The threshold stops a sub-pixel
     * measurement loop from relaying out the scene, and a repaint is marked either way because
     * the backing store has to be resized whatever the layout does.
     */
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const measure = () => {
            const width = canvas.clientWidth;
            const height = canvas.clientHeight;
            setSurface((previous) =>
                Math.abs(previous.width - width) > RESIZE_STEP ||
                Math.abs(previous.height - height) > RESIZE_STEP
                    ? { width, height }
                    : previous,
            );
            fit();
        };
        measure();
        const observer = new ResizeObserver(measure);
        observer.observe(canvas);
        return () => observer.disconnect();
    }, [fit]);

    useEffect(() => {
        const query = window.matchMedia("(prefers-reduced-motion: reduce)");
        const read = () => {
            reducedRef.current = query.matches;
        };
        read();
        query.addEventListener("change", read);
        return () => query.removeEventListener("change", read);
    }, []);

    /* ---------------------------------------------------- the neighbourhood - */

    /**
     * The curated set, from the one module both renderers read.
     *
     * Memoised on the subject and the budget, never called from a frame callback: `selectFocus`
     * is O(degree) rather than O(budget), so Indra costs 1.3-2.9 ms whichever budget is asked
     * for, and the compact mobile budget is not the cheap path it looks like.
     *
     * `root` is withheld until the canvas has measured itself, so the neighbourhood is selected
     * once at the budget the band can seat rather than twice - once at a guess and once for
     * real.
     */
    const budget = useMemo(
        () => focusBudgetForBand(band.width, band.height),
        [band.width, band.height],
    );
    const neighbourhood = useFocusNeighbourhood({
        world,
        labels,
        root: scope === "focus" && measured ? root : null,
        budget,
    });

    useEffect(() => {
        if (!measured) return;
        if (scope === "world") {
            /*
             * The corpus as its constellations, relaxed in the plane.
             *
             * Not the 2,600 busiest nodes, which is what this drew: 76% of them were passages,
             * their projected nearest-neighbour separation was 0.45 px at the 5th percentile,
             * and of 22,095 eligible edges it kept the first 5,200 *by artifact index*. The
             * reasoning for that arrangement - the offline layout already encodes where things
             * are, so do not re-simulate it - was right, and it survives: the disc centres are
             * the artifact's own, moved only as far as not overlapping requires.
             */
            graphRef.current = buildWorldScene(world, band);
            // Static: nothing to settle, so the simulation never starts.
            sleepingRef.current = true;
            fit();
            return;
        }
        if (!neighbourhood) {
            graphRef.current = null;
            markDirty();
            return;
        }
        const graph = buildFocusScene(world, neighbourhood, band);
        graphRef.current = graph;
        /* Settled before the first paint, so the diagram arrives arranged rather than arriving
           scrambled and sorting itself out. Slot anchors converge in far fewer steps than the
           loose rings this replaced, so the preroll stops when the field is at rest instead of
           always running a fixed sixty. */
        const used = preroll(graph);
        sleepingRef.current = reducedRef.current || used < PREROLL_LIMIT;
        fit();
    }, [world, scope, neighbourhood, band, measured, fit, markDirty]);

    /**
     * The one thing the chrome may ask of this canvas.
     *
     * The neighbours it settles back onto are the ones already shown; nothing here consults
     * `focus.ts`, so there is no path from this control to a wider curated set. Under reduced
     * motion it is applied in a single frame, because a diagram that travels outward over a
     * second is exactly the motion that was asked not to happen.
     */
    useImperativeHandle(
        ref,
        () => ({
            respaceFocus: () => {
                const graph = graphRef.current;
                if (!graph || graph.rootId === null) return;
                const instant = reducedRef.current;
                respaceFocusScene(graph, band, { instant });
                if (instant) {
                    preroll(graph);
                    settleSlots(graph);
                    sleepingRef.current = true;
                } else {
                    sleepingRef.current = false;
                }
                dirtyRef.current = true;
            },
        }),
        [band],
    );

    /* ------------------------------------------------------------- the paint - */

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

        /*
         * Lines, in three weights, back to front.
         *
         * A relationship that touches what the pointer is on is drawn in ink; a relationship to
         * the subject itself is a spoke; a line between two neighbours is context. Three
         * weights is enough to read structure and few enough that the diagram never becomes a
         * wash, which is what happens when every edge gets its own encoding. The order is
         * painted rather than sorted: context, then spokes, then the hovered line, so the line
         * a reader is asking about is never underneath one they are not.
         */
        context.lineCap = "round";
        /*
         * One stroke per style, not one per line.
         *
         * Measured on the arrangement this replaced: 5,472 `beginPath`/`stroke` pairs per
         * repaint across three style buckets, at a 49.9 ms median frame interval - the slowest
         * thing in the product, in the renderer that exists for the devices least able to
         * afford it. A canvas path holds any number of disjoint segments, so a bucket is a
         * bucket: a whole Focus scene is three strokes, and the world map is three plus one per
         * aggregate width class.
         */
/*
         * Three tokens, each measured for the line it draws.
         *
         * `relationSecondary` for a line between two neighbours - 2.76:1 against the canvas, and
         * the only token in the system with a two-sided gate, 2.0 <= r < 3.0, because "present
         * but not asserted" may neither vanish into the page nor start claiming to be
         * information. `relationPrimary` for a spoke, which is the relationship the reader asked
         * about: rubric-700 at 6.79:1, and rubric rather than the accent because the accent
         * measures dE00 4.1 from the deity fill and a relation drawn in it reads as a deity.
         * `relationHover` for the line under the pointer, 9.93:1 light and 12.69:1 dark, one step
         * off the focus ring so a hovered relation and a selected subject are not the same mark.
         *
         * `edgeQuiet` is deliberately not used. It is the resting weight of a field of up to
         * 185,693 edges and is sub-threshold by design at 1.04:1 for one stroke, on the argument
         * that structure emerges from crossings - six of them stack to 1.23:1. A scene of 41 to
         * 515 lines has no accumulation to lend it, so that token here would just be an
         * invisible line, which is the defect this paragraph replaced.
         */
        const heaviest = graph.edges.length === 0 ? 1 : graph.edges[graph.edges.length - 1].weight;
        /* The world scene's lines ARE aggregated bridge relationships, so they take the token
           measured for a bridge - 4.29:1 against the canvas, and the one line whose whole point
           is that it is visible. In Focus the same bucket carries context between neighbours. */
        const quietInk = graph.rootId === null ? palette.edgeBridge : palette.relationSecondary;
        const buckets: Array<{
            colour: string;
            alpha: number;
            width: number;
            points: number[];
        }> = [
            ...AGGREGATE_WIDTHS.map((width) => ({
                colour: quietInk,
                alpha: 1,
                width,
                points: [] as number[],
            })),
            { colour: palette.relationPrimary, alpha: 1, width: 1.4, points: [] },
            { colour: palette.relationHover, alpha: 1, width: 2, points: [] },
        ];
        const spokeBucket = buckets[AGGREGATE_WIDTHS.length];
        const hoverBucket = buckets[AGGREGATE_WIDTHS.length + 1];
        for (const edge of graph.edges) {
            const a = graph.nodes[edge.a];
            const b = graph.nodes[edge.b];
            const into =
                hovered !== null && (edge.a === hovered || edge.b === hovered)
                    ? hoverBucket
                    : a.ring === 0 || b.ring === 0
                      ? spokeBucket
                      : buckets[aggregateClass(edge.weight, heaviest)];
            into.points.push(toScreenX(a.x), toScreenY(a.y), toScreenX(b.x), toScreenY(b.y));
        }
        for (const bucket of buckets) {
            if (bucket.points.length === 0) continue;
            context.strokeStyle = bucket.colour;
            context.globalAlpha = bucket.alpha;
            context.lineWidth = bucket.width;
            context.beginPath();
            for (let i = 0; i < bucket.points.length; i += 4) {
                context.moveTo(bucket.points[i], bucket.points[i + 1]);
                context.lineTo(bucket.points[i + 2], bucket.points[i + 3]);
            }
            context.stroke();
        }
        context.globalAlpha = 1;

        /*
         * Orbs, opaque, with the subject painted last.
         *
         * ## Why there is no transparency here any more
         *
         * A recessive node was drawn at alpha 0.55 and a normal one at 0.94. Measured against
         * this product's page colour, the nine group fills at 0.55 reach **1.97:1 light and
         * 2.38:1 dark** - so a recessive node could not clear WCAG 1.4.11's 3:1 *for any
         * palette*, and no colour work could have fixed it. Opaque they measure 3.95:1 and
         * 5.10:1. ARB-5 settles it: the orbs are opaque and recession comes from the four other
         * channels - size, whether the mark is named, the weight of the lines that reach it,
         * and paint order.
         *
         * ## The keyline is paper, not a stroke
         *
         * Its ratio against any fill *is* that fill's ratio against the page, so the fill gate
         * carries it: 3.95:1 at worst light, 5.10:1 dark. It is also the manuscript idiom,
         * where two forms are separated by the paper between them.
         */
        const rings: Array<{ index: number; width: number }> = [];
        for (let i = 0; i < graph.nodes.length; i += 1) {
            const node = graph.nodes[i];
            if (node.ring === 0) continue;
            paintOrb(context, node, toScreenX(node.x), toScreenY(node.y), view.scale, palette);
            if (i === hovered) rings.push({ index: i, width: 1.6 });
        }
        for (let i = 0; i < graph.nodes.length; i += 1) {
            const node = graph.nodes[i];
            if (node.ring !== 0) continue;
            paintOrb(context, node, toScreenX(node.x), toScreenY(node.y), view.scale, palette);
            rings.push({ index: i, width: 2.6 });
        }
        /*
         * The ring that says "this one".
         *
         * Two strokes: paper outside, `focusRing` inside. `theme.css` records that this view
         * drew it in `--va-accent-base` and measured **1.18:1 light and 1.07:1 dark over the
         * node it was marking** - the ring that says "this is the one" was invisible on the one.
         * `--va-graph-focus-ring` is the token derived for exactly this and it is the theme's
         * extreme primitive, carbon in light and paper in dark, measured at **3.12:1 over the
         * worst fill and 15.68:1 against the canvas**. This drew it in `labelInk` for one
         * commit, while the token existed in the stylesheet but not yet on `GraphPalette`, and
         * the cost of that stand-in was measurable: `labelInk` is the same value in light but
         * one step short in dark, where it measures **2.88:1** over the `thing` fill and
         * therefore fails.
         *
         * The paper keyline outside it is kept rather than dropped. Its ratio against any fill
         * *is* that fill's ratio against the canvas, so the fill gate carries it at 3.95:1 light
         * and 5.10:1 dark, and two concentric strokes read as one mark - which means neither
         * stroke has to carry the mark alone on a fill nobody has measured yet.
         */
        for (const { index, width } of rings) {
            const node = graph.nodes[index];
            const r = markRadius(node, view.scale);
            traceOrb(context, node, toScreenX(node.x), toScreenY(node.y), r + width);
            context.strokeStyle = palette.orbKeyline;
            context.lineWidth = width;
            context.stroke();
            traceOrb(context, node, toScreenX(node.x), toScreenY(node.y), r);
            context.strokeStyle = palette.focusRing;
            context.lineWidth = width;
            context.stroke();
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

        /*
         * Names.
         *
         * The subject always, whatever is under the pointer, the marks that carry their own
         * caption, and then the most connected of the rest up to a cap. The cap came down from
         * eighteen to eight because suppressing a name is now one of the channels carrying
         * hierarchy, and because eighteen names over a 41-mark scene collided with each other
         * and with the relationship labels.
         */
        /* The ranking depends on the graph, not on the camera, so it is computed when the graph
           changes and not per frame. It was per frame: 2,600 objects allocated and a full sort,
           sixty times a second, to produce the same eighteen names. */
        if (nameOrderRef.current.graph !== graph) {
            nameOrderRef.current = {
                graph,
                always: graph.nodes
                    .map((node, index) => ({ node, index }))
                    .filter(({ node }) => node.ring === 0 || node.labelled),
                ranked: graph.nodes
                    .map((node, index) => ({ node, index }))
                    .filter(({ node }) => node.ring === 1 && !node.labelled)
                    .sort((a, b) => b.node.degree - a.node.degree),
            };
        }
        const order = nameOrderRef.current;
        const named = [...order.always];
        if (hovered !== null && !named.some((entry) => entry.index === hovered)) {
            named.push({ node: graph.nodes[hovered], index: hovered });
        }
        if (labels && scope === "focus") {
            const ceiling = order.always.length + FOCUS_NAME_CAP;
            for (const entry of order.ranked) {
                if (named.length >= ceiling) break;
                if (entry.index !== hovered) named.push(entry);
            }
        }
        for (const { node, index } of named) {
            const text = node.caption ?? labels?.labels[node.id] ?? "";
            if (!text) continue;
            const strong = node.ring === 0 || index === hovered;
            context.font = strong
                ? '500 14px "Charis SIL", Georgia, serif'
                : '400 11.5px "Charis SIL", Georgia, serif';
            context.textBaseline = "middle";
            const x = toScreenX(node.x) + markRadius(node, view.scale) + 7;
            const y = toScreenY(node.y);
            const measured = context.measureText(text).width;
            const lineHeight = strong ? 16 : 13;
            /*
             * A plate, not a halo.
             *
             * The paper was stroked *under* the letterforms at 3.5 px, which is partial
             * coverage: measured over the nine fills it leaves the ink at 7.6:1 light and 7.0:1
             * dark where the stroke covers and at the fill's own ratio where it does not, so a
             * name crossing a dense region is legible in places and not in others. `world.css`
             * records this already having been measured out of the other renderer in favour of a
             * plate, and the same answer here costs one `fillRect`.
             *
             * Drawn at `alphas.plate` rather than opaque, because that is the alpha
             * `--va-graph-plate-ink` was measured against - ink on a plate composited over the
             * worst fill it can sit on, which is 15.27:1 light and 13.40:1 dark. A plate audited
             * against itself reads 16.94 and does not see the 1.67 points the bleed-through
             * costs. Opaque here would be a better ratio than the gate measures, which is a
             * different kind of drift from a worse one and still drift.
             */
            context.globalAlpha = palette.alphas.plate;
            context.fillStyle = palette.plate;
            context.fillRect(x - 3, y - lineHeight / 2 - 1, measured + 6, lineHeight + 2);
            context.globalAlpha = 1;
            context.fillStyle = strong ? palette.plateInk : palette.plateInkQuiet;
            context.fillText(text, x, y);
            namedBoxes.push({
                key: -1,
                text: "",
                x: x - 3,
                y: y - lineHeight / 2 - 1,
                width: measured + 6,
                height: lineHeight + 2,
            });
        }
        namedBoxesRef.current = namedBoxes;

        /*
         * What each connection is.
         *
         * Focus only. A line between two constellations is an aggregate standing for up to
         * 3,303 relationships, and captioning it with one of their predicates would be a phrase
         * beside a line it does not describe - so the world scene draws no relationship labels
         * rather than plausible ones.
         *
         * The subject is whatever the pointer is on, or the root when it is on nothing - the
         * same precedence the spatial view uses, so moving between renderers does not change
         * which connections are being explained. The choice of which to name is recomputed only
         * when that subject changes; only the positions are per-frame, and those are an affine
         * transform of coordinates this function already has.
         */
        const labelView = labelViewRef.current;
        if (labelView && scope === "focus") {
            const subject =
                hovered ?? (graph.rootId === null ? null : graph.index.get(graph.rootId) ?? null);

            if (subject !== labelSubjectRef.current) {
                labelSubjectRef.current = subject;
                if (subject === null) {
                    picksRef.current = [];
                    labelView.setLabels([]);
                } else {
                    /* Only the connections this diagram actually drew are eligible. The scene
                       is curated, so a subject has edges in the artifact that are not lines on
                       this canvas, and naming one of those would put a phrase beside a line it
                       does not belong to. */
                    const drawn = new Map<number, number>();
                    graph.edges.forEach((planarEdge, i) => {
                        if (planarEdge.edge < 0) return;
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
                    /* The candidate budget above is read from the live width every time; the
                       layer's own cap was read once, when it was constructed. Both have to move
                       when the canvas does, or a narrowed window keeps laying out for a wide
                       one. Idempotent, so saying it on every re-pick costs nothing. */
                    labelView.setRelationCap(edgeLabelBudget(width));
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
                labelView.update(points, { width, height });
                /* The assignment waits for stillness, so a settled diagram has to offer one
                   more frame or the deadline never arrives. Bounded by the view itself: it
                   stops asking the moment it has placed what it has. */
                if (labelView.pending) markDirty();
            }
        } else if (labelView && labelSubjectRef.current !== null) {
            labelSubjectRef.current = null;
            picksRef.current = [];
            labelView.setLabels([]);
        }
    }, [labels, scope, world, markDirty]);

    /*
     * The open explanation, told to the layer that has to keep its phrase on screen.
     *
     * `markDirty` because this canvas only repaints when something asks it to, and a phrase
     * changing tier is not motion the draw loop would otherwise notice - the same reason the
     * label deadline needed one. Without it, closing an explanation left its phrase pinned
     * until the next thing that happened to redraw.
     */
    useEffect(() => {
        const labelView = labelViewRef.current;
        if (!labelView) return;
        labelView.setInspected(inspectedEdge);
        markDirty();
    }, [inspectedEdge, markDirty]);

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

    /*
     * A new neighbourhood invalidates whatever was being named in the last one - and so does
     * the arrival of the words.
     *
     * `predicates` is fetched after the geometry, so on a cold load the first paint happens
     * before the curated phrasing exists. The pick is memoised on the subject, and the paint
     * only runs while the canvas is dirty, so without `predicates` in this list the sequence
     * was: paint with no table, record the subject as done, settle, and never name anything.
     * Measured on a production build - the spatial view showed eight phrases and the planar
     * view showed nought, with its label spans allocated, empty and at opacity zero.
     *
     * The spatial view never had this, because there the pick is a React effect with
     * `predicates` among its dependencies. Here the pick lives inside the frame loop, so the
     * dependency has to be declared by hand. The palette already does exactly this a few lines
     * below; the table was the one asynchronous input nobody had connected.
     */
    useEffect(() => {
        labelSubjectRef.current = null;
        markDirty();
    }, [root, scope, predicates, markDirty]);

    /* -------------------------------------------------------------- loop - */

    useEffect(() => {
        const loop = () => {
            frameRef.current = requestAnimationFrame(loop);
            const graph = graphRef.current;
            let dirty = dirtyRef.current;
            if (graph) {
                /*
                 * Energy in, energy out.
                 *
                 * The simulation stops stepping once the graph is still and does not start
                 * again until something disturbs it - and, now, the canvas stops *painting*
                 * too. Those were two different claims and only the first was true: `draw` ran
                 * unconditionally, so an untouched world repainted its whole scene sixty times
                 * a second for as long as the tab was open. A diagram nobody is touching costs
                 * nothing, which is what this comment used to say and now describes.
                 */
                if (scope === "focus" && !sleepingRef.current) {
                    const energy = stepPlanar(graph);
                    dirty = true;
                    if (isAtRest(energy) && !dragRef.current) {
                        sleepingRef.current = true;
                        /* A re-space widens the slot clamps so the anchor springs can carry the
                           marks outward; coming to rest is when they are narrow again, and the
                           separation the layout promises is a promise about rest. */
                        settleSlots(graph);
                    }
                }
                const view = viewRef.current;
                if (
                    !reducedRef.current &&
                    !dragRef.current &&
                    (Math.abs(view.vx) > 0.05 || Math.abs(view.vy) > 0.05)
                ) {
                    /* Inertial pan: the canvas keeps moving after the pointer leaves and slows
                       the way something with mass slows. Suppressed under reduced motion, where
                       a surface that carries on moving after the reader has stopped is the
                       whole of what was asked not to happen. */
                    view.x += view.vx;
                    view.y += view.vy;
                    view.vx *= 0.92;
                    view.vy *= 0.92;
                    dirty = true;
                }
            }
            if (!dirty) return;
            dirtyRef.current = false;
            draw();
        };
        frameRef.current = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(frameRef.current);
    }, [draw, scope]);

    /* A sleeping graph still has to repaint when the theme changes: the loop is running but
       the simulation is not, and nothing else would mark the canvas dirty. */
    useEffect(() => {
        if (palette) markDirty();
    }, [palette, markDirty]);

    /* ---------------------------------------------------------- pointers - */

    const zoomAbout = useCallback((px: number, py: number, next: number) => {
        const view = viewRef.current;
        const scale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next));
        const before = { x: (px - view.x) / view.scale, y: (py - view.y) / view.scale };
        view.scale = scale;
        // Zoom about the pointer rather than the centre, so the thing under the cursor stays
        // under the cursor.
        view.x = px - before.x * scale;
        view.y = py - before.y * scale;
        dirtyRef.current = true;
    }, []);

    /**
     * The wheel listener is installed by hand, and not passively.
     *
     * React attaches `wheel` at the root as a passive listener, so a synthetic `onWheel`
     * handler cannot call `preventDefault` - and `body` is only `overflow: hidden` below 48rem,
     * so on a desktop every wheel-zoom also scrolled the page out from under the canvas. The
     * spatial view never had this because OrbitControls installs its own non-passive listener,
     * which is exactly what this now does.
     */
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const onWheel = (event: WheelEvent) => {
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            zoomAbout(
                event.clientX - rect.left,
                event.clientY - rect.top,
                viewRef.current.scale * Math.exp(-event.deltaY * 0.0016),
            );
        };
        canvas.addEventListener("wheel", onWheel, { passive: false });
        return () => canvas.removeEventListener("wheel", onWheel);
    }, [zoomAbout]);

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

    const kindOf = (pointerType: string): PointerKind =>
        pointerType === "touch" || pointerType === "pen" ? pointerType : "mouse";

    const release = (graph: PlanarGraph | null, node: number | null) => {
        if (!graph || node === null) return;
        graph.nodes[node].held = false;
        sleepingRef.current = false;
        if (reducedRef.current) {
            /* Under reduced motion the arrangement settles without being watched settling. */
            preroll(graph);
            sleepingRef.current = true;
            dirtyRef.current = true;
        }
    };

    const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        if (!graph) return;
        const { x, y, screenX, screenY } = toGraph(event);
        const kind = kindOf(event.pointerType);
        pointersRef.current.set(event.pointerId, { x: screenX, y: screenY, kind });

        if (pointersRef.current.size > 1) {
            /* A second pointer is a pinch or a two-finger pan. Nothing after it is a tap, and
               whatever the first finger was holding is let go: a node dragged by one finger of
               a pinch follows a midpoint it has no relationship to. */
            const drag = dragRef.current;
            if (drag) {
                release(graph, drag.node);
                drag.moved = true;
                drag.kind = "canvas";
                drag.node = null;
            }
            pinchRef.current = null;
            return;
        }

        event.currentTarget.setPointerCapture(event.pointerId);
        const hit = pickPlanar(graph, x, y, { scale: viewRef.current.scale, pointer: kind });
        /* In the world scene the positions are derived from the artifact, so a mark cannot be
           dragged: moving one would claim the arrangement is live when it is precomputed, and
           the next reload would silently put it back. Panning still works. */
        const grabbable = scope === "focus" && hit !== null;
        if (grabbable && hit !== null) {
            graph.nodes[hit].held = true;
            sleepingRef.current = false;
        }
        dragRef.current = {
            pointerId: event.pointerId,
            kind: grabbable ? "node" : "canvas",
            node: grabbable ? hit : null,
            lastX: screenX,
            lastY: screenY,
            originX: screenX,
            originY: screenY,
            kindOfPointer: kind,
            moved: false,
        };
    };

    const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        if (!graph) return;
        const { x, y, screenX, screenY } = toGraph(event);
        const pointers = pointersRef.current;
        const tracked = pointers.get(event.pointerId);
        if (tracked) {
            tracked.x = screenX;
            tracked.y = screenY;
        }

        if (pointers.size >= 2) {
            /*
             * Pinch, and two-finger pan from the midpoint.
             *
             * The 2D view had no pinch at all, and `touch-action: none` in the stylesheet
             * disables the browser's own, so this diagram could not be zoomed on a phone by any
             * means - in the renderer that is the fallback when WebGL is unavailable. The
             * midpoint is translated first and the scale applied about it second, so the two
             * fingers stay on the same two points of the diagram.
             */
            const [first, second] = [...pointers.values()];
            const distance = Math.hypot(first.x - second.x, first.y - second.y);
            const midX = (first.x + second.x) / 2;
            const midY = (first.y + second.y) / 2;
            const pinch = pinchRef.current;
            if (!pinch || pinch.distance < 1) {
                pinchRef.current = { distance, midX, midY };
                return;
            }
            const view = viewRef.current;
            view.x += midX - pinch.midX;
            view.y += midY - pinch.midY;
            zoomAbout(midX, midY, view.scale * (distance / pinch.distance));
            pinchRef.current = { distance, midX, midY };
            return;
        }

        const drag = dragRef.current;
        if (!drag) {
            const hit = pickPlanar(graph, x, y, {
                scale: viewRef.current.scale,
                pointer: kindOf(event.pointerType),
            });
            if (hit !== hoverRef.current) {
                hoverRef.current = hit;
                const node = hit === null ? null : graph.nodes[hit];
                setHoverLabel(
                    node === null ? null : node.caption ?? labels?.labels[node.id] ?? null,
                );
                dirtyRef.current = true;
            }
            return;
        }
        if (drag.pointerId !== event.pointerId) return;

        const dx = screenX - drag.lastX;
        const dy = screenY - drag.lastY;
        drag.lastX = screenX;
        drag.lastY = screenY;
        /*
         * Travel from the press, not between two moves.
         *
         * This read `Math.abs(dx) > 1 || Math.abs(dy) > 1` on the per-event delta, and that was
         * a release blocker rather than an imprecision. A slow pan - a careful trackpad drag, a
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
            dirtyRef.current = true;
        }
    };

    const forget = (event: React.PointerEvent<HTMLCanvasElement>) => {
        pointersRef.current.delete(event.pointerId);
        if (pointersRef.current.size < 2) pinchRef.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
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
        forget(event);
        if (!drag || drag.pointerId !== event.pointerId) return;
        dragRef.current = null;
        release(graph, drag.node);
    };

    const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
        const graph = graphRef.current;
        const drag = dragRef.current;
        forget(event);
        if (!graph || !drag || drag.pointerId !== event.pointerId) return;
        dragRef.current = null;
        /* One finger left of a pinch keeps panning rather than becoming a fresh press, and it
           can never become a tap: the travel that made it a pinch is not forgotten. */
        const remaining = [...pointersRef.current.entries()][0];
        if (remaining) {
            const [pointerId, pointer] = remaining;
            dragRef.current = {
                pointerId,
                kind: "canvas",
                node: null,
                lastX: pointer.x,
                lastY: pointer.y,
                originX: pointer.x,
                originY: pointer.y,
                kindOfPointer: pointer.kind,
                moved: true,
            };
        }

        if (drag.node !== null) {
            release(graph, drag.node);
            // A release with no movement is a click, not a throw.
            if (!drag.moved) onSelect(graph.nodes[drag.node].id);
            return;
        }
        if (drag.moved) return;
        /*
         * A tap that moved nothing. In the world scene marks are not draggable, so a tap on one
         * still has to select it.
         *
         * A tap on empty canvas used to call `onSelect(null)`, and that single line was the
         * reported release blocker: it reached a state transition that demoted Focus to World,
         * so a stray tap - or, through the threshold bug above, a slow pan - discarded the
         * subject a reader was studying. A canvas has no business deciding that the reader has
         * finished with a subject. Leaving one is a control in the chrome and the Escape key,
         * both owned by the page.
         *
         * The inspected relationship is still dismissed, because that *is* about the canvas: it
         * annotates a line, and tapping away from the line is done with it.
         */
        const { x, y } = toGraph(event);
        const hit = pickPlanar(graph, x, y, {
            scale: viewRef.current.scale,
            pointer: drag.kindOfPointer,
        });
        if (hit !== null) onSelect(graph.nodes[hit].id);
        else onInspectEdge(null);
    };

    return (
        <div className="va-planar" ref={stageRef} style={{ overscrollBehavior: "contain" }}>
            <canvas
                aria-label="The selected subject and its connections as a diagram. The same connections are listed beside it."
                className="va-planar-canvas"
                onPointerCancel={onPointerCancel}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
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
            {scope === "world" && constellations === 0 && (
                <p className="va-planar-empty">
                    This world map is drawn from the corpus&rsquo;s constellations, and the
                    artifact loaded does not carry them. Rebuild the world artifact, or open a
                    subject to see its connections.
                </p>
            )}
        </div>
    );
}

/**
 * Two shapes, not eleven.
 *
 * A passage is a diamond and everything else is a disc. More shapes were tried and they turn
 * the diagram into a legend puzzle: a reader ends up decoding the key instead of reading the
 * structure. One distinction earns its place because passages are the thing you leave the graph
 * to go and read, and there are twenty thousand of them.
 */
function traceOrb(
    context: CanvasRenderingContext2D,
    node: PlanarNode,
    x: number,
    y: number,
    r: number,
) {
    context.beginPath();
    if (GROUP_NAMES[node.group] === "passage") {
        context.moveTo(x, y - r);
        context.lineTo(x + r, y);
        context.lineTo(x, y + r);
        context.lineTo(x - r, y);
        context.closePath();
        return;
    }
    context.arc(x, y, r, 0, Math.PI * 2);
}

function paintOrb(
    context: CanvasRenderingContext2D,
    node: PlanarNode,
    x: number,
    y: number,
    scale: number,
    palette: GraphPalette,
) {
    const r = markRadius(node, scale);
    traceOrb(context, node, x, y, r);
    /* A mark with no single group - a constellation stands for up to 3,880 subjects across
       every group there is - is drawn in one neutral ink rather than by its dominant group.
       ARB-6's condition, on Jianu et al.: encoding group membership over a node-link diagram
       measured about 25% worse accuracy on network tasks. */
    context.fillStyle =
        node.group < 0
            ? palette.relationSecondary
            : palette.groupCss[node.group] ?? palette.relationSecondary;
    /*
     * Opaque, and the token says so.
     *
     * `--va-graph-alpha-planar` is 1 and exists to state that rather than to scale anything.
     * Read rather than assumed, so the gate and this function cannot come to different
     * conclusions about what is on screen - which is how four of the eleven light fills came to
     * sit under 3:1 while every contrast check in the repository reported a pass.
     */
    context.globalAlpha = palette.alphas.planar;
    context.fill();
    context.globalAlpha = 1;
    if (r >= 5) {
        /* A line of paper between two orbs rather than a stroke, which is the manuscript idiom
           and the one keyline that needs no tuning: drawn in the canvas colour its ratio against
           any fill *is* that fill's ratio against the canvas. */
        context.strokeStyle = palette.orbKeyline;
        context.lineWidth = 1.5;
        context.stroke();
    }
}
