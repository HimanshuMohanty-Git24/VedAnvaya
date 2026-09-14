"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Color } from "three";
import { composeWorld, edgesOf } from "@/lib/world/artifact";
import { probeCapability } from "@/lib/world/capability";
import { pickEdgeLabels } from "@/lib/world/edge-labels";
import { WorldEngine } from "@/lib/world/engine";
import { GROUP_NAMES, useScopedGraphPalette } from "@/lib/world/palette";
import { loadPredicateSemantics, type PredicateTable } from "@/lib/world/predicates";

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
 * layout gave them among all 35,370. Nothing here is representative of the data - it *is* the
 * data.
 *
 * ## What a reader can do with it, and where that stops
 *
 * Four subjects are named on the field, two on a phone. Without them this is fifty coloured
 * discs, and a diagram nobody can name is a texture: the reader has no way to discover that the
 * thing they are looking at contains Indra. The names are chosen by corpus degree, dropped when
 * they would collide, and re-placed on a timer rather than per frame - see the placement effect.
 *
 * Hovering a subject draws that subject's own connections and names it in the readout. Tapping
 * one holds it, and the held subject spells its connections out in words - "co-occurs with
 * Agni" - from the same curated table the API serves. Those words are fetched on the first
 * contact with a subject and not before: the file is 21 kB and most visitors never point at
 * anything.
 *
 * Going to the graph is a separate sentence the reader has to mean. A tap used to navigate,
 * which was wrong at the end of every orbit, and nothing on this canvas navigates now.
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

/**
 * How many subjects are named on the field at once.
 *
 * Four, and two where the panel is a phone's width. The ceiling is the point: the graph page
 * shows up to twenty-two names because the canvas is the page, and the same density in a 537 by
 * 430 panel is a paragraph of overlapping type laid over a diagram. Four names over fifty discs
 * says "these are subjects, and here are some you know" without becoming the content.
 */
const KEY_LABELS = 4;
const KEY_LABELS_COMPACT = 2;

/**
 * The canvas width below which the panel is treated as compact, in CSS pixels.
 *
 * Measured: the panel is 537 px wide at a 1440 px viewport and 350 px at 390 px, so this sits
 * between the two rather than at a round number nothing corresponds to.
 */
const COMPACT_CANVAS = 420;

/**
 * A name this close to a name already placed is not placed at all, in CSS pixels.
 *
 * Wider than it is tall by six to one, because these are single lines of text: two names
 * eighteen pixels apart vertically are two legible lines, and two names eighteen pixels apart
 * horizontally are one illegible one.
 */
const COLLIDE_X = 116;
const COLLIDE_Y = 18;

/**
 * Where on the canvas a name may be anchored at all.
 *
 * Not the whole of it. The panel carries a link at the top inline end and a scrim with the
 * readout at the foot, and both paint above this layer, so a name anchored under either is a
 * name nobody can read. Measured against the panel at 1440: the link's row is 24 px of type
 * inside a 16 px inset, and the scrim's opaque half is about 50 px.
 *
 * Refusing an anchor costs nothing, because four names are chosen from fifty candidates in
 * degree order - the next subject down simply takes the place.
 */
const LABEL_ROOM = { top: 44, bottom: 56, edge: 6 };

/**
 * How close to the trailing edge a name flips to the other side of its disc, in pixels.
 *
 * A name is drawn to the right of the subject it belongs to, and the layer clips, so a name
 * anchored inside this band arrives as "sacrifice (ya…". The flip is along the label's own
 * axis rather than a nudge: it stays attached to the same disc and no other.
 */
const LABEL_FLIP = 132;

/** How often the names are re-placed. The graph page's own interval, for the same reason. */
const PLACE_MS = 160;

/**
 * How many of a held subject's connections are spelled out.
 *
 * `pickEdgeLabels` deals these out one kind at a time before repeating a kind, so four rows on
 * a subject with four kinds of relationship are four different relationships rather than the
 * commonest one four times.
 */
const RELATIONS_SHOWN = 4;
const RELATIONS_SHOWN_COMPACT = 2;

/** The width at which home.css restacks the hero into one column. Held here as one number. */
const COMPACT_QUERY = "(max-width: 47.99rem)";

/**
 * How far out the camera sits, as a multiple of the cloud's radius.
 *
 * Measured rather than chosen, through `__vedaHero.refit`, and it has to be this far out for
 * a reason the arithmetic gives away: at a 45 degree field of view the visible half-height at
 * distance d is 0.414d, so a cloud of radius r is only contained vertically once d exceeds
 * 2.41r - and the panel is 5:4, so the vertical is the binding axis. The sweep agrees. At 1.6
 * the discs spanned 127 per cent of the panel's height and two of the fifty were outside the
 * frame with their edges running off the corners, which reads as a crop of something larger
 * rather than as a field with a shape. 2.2 is the first distance at which all fifty are inside;
 * they span about four fifths of the height, and the link at the head and the readout at the
 * foot both sit over ground rather than over the diagram.
 */
const FRAMING_SPREAD = 2.2;

/** One name placed on the field. */
type KeyLabel = {
    index: number;
    text: string;
    x: number;
    y: number;
    /** The held subject, set apart from the ambient names rather than merely listed among them. */
    strong: boolean;
    /** Drawn to the left of its disc, because the right would run out of canvas. */
    flipped: boolean;
};

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
    /**
     * The subject chosen inside the preview. Local, and it is the point.
     *
     * A tap used to navigate. That was wrong twice over: it navigated at the end of every orbit,
     * because a mouse drag always ends in a click; and releasing over empty space - which is
     * where an orbit usually ends - navigated to the whole graph, because a pick of nothing was
     * read as a request for everything. A preview exists so that people can handle it, and a
     * surface that leaves the page when handled cannot be handled.
     *
     * So a tap selects, here, and going to the graph is a thing the reader asks for in words.
     */
    const [chosen, setChosen] = useState<{ index: number; node: HeroSliceNode } | null>(null);
    /* The engine is built once, so its callbacks reach the current handler through a ref rather
       than through the construction effect's dependency list. */
    const chooseRef = useRef<(index: number | null) => void>(() => {});
    const [keyLabels, setKeyLabels] = useState<KeyLabel[]>([]);
    /* The placement timer outlives any one render, so it reads the held subject from a ref. A
       closure over the state would keep naming whatever was held when the timer was started. */
    const heldRef = useRef<number | null>(null);
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

    /*
     * Whether this panel is a phone's width, decided at the breakpoint home.css restacks the
     * hero at. One number for how many names go on the field and how many connections the
     * selection spells out, so the two cannot disagree about how much room there is.
     */
    const [compact, setCompact] = useState(
        () => typeof window !== "undefined" && window.matchMedia(COMPACT_QUERY).matches,
    );
    useEffect(() => {
        const query = window.matchMedia(COMPACT_QUERY);
        const apply = () => setCompact(query.matches);
        query.addEventListener("change", apply);
        return () => query.removeEventListener("change", apply);
    }, []);

    /**
     * The relationship vocabulary, fetched on the first contact with a subject.
     *
     * Not `usePredicateSemantics`, which is what the graph page uses and which fetches at mount.
     * The file is 21 kB of curated phrasing and most visitors to a homepage never point at the
     * field at all, so it is spent on the first hover and on the first tap - the tap because a
     * hoverless device never raises the other one, and a phone would otherwise be the only
     * place these words never arrive.
     *
     * Null is a usable state, not a gate: the selection counts the connections until the words
     * land, and never guesses at them. There is a local enum humaniser in this codebase and it
     * disagrees with the curated phrasing on 44 of 57 predicates, so a guess here would be a
     * second, wrong vocabulary on the front door.
     */
    const [predicates, setPredicates] = useState<PredicateTable | null>(null);
    const asked = useRef(false);
    const wantPredicates = useCallback(() => {
        if (asked.current) return;
        asked.current = true;
        loadPredicateSemantics()
            .then(setPredicates)
            .catch(() => {
                /* The connections keep their count. Only the words are missing, and the
                   selection says so by counting rather than by naming. */
            });
    }, []);

    /* One `World` for the engine and for the words. Built here rather than inside the
       construction effect so that naming a connection cannot read a different graph from the
       one being drawn. */
    const world = useMemo(() => toWorld(slice), [slice]);

    /**
     * Which subjects are worth naming, most substantial first.
     *
     * By corpus degree, not by degree inside this cut: a name is here so that a newcomer
     * recognises something, and Indra is Indra whether the slice kept four of his connections
     * or forty. Ties break on the label so a rebuild of the artifact cannot silently reorder
     * which names the front door shows.
     */
    const ranked = useMemo(
        () =>
            slice.nodes
                .map((_, index) => index)
                .sort(
                    (a, b) =>
                        slice.nodes[b].degree - slice.nodes[a].degree ||
                        slice.nodes[a].label.localeCompare(slice.nodes[b].label),
                ),
        [slice],
    );

    /**
     * The held subject's connections, in words.
     *
     * Deliberately not restricted to `engine.drawnEdgesOf`, which is what the graph page has to
     * do: that overlay buffer is sized to the graph's own maximum degree and truncates past it,
     * so a hub there has connections on screen and connections not. Here the buffer is sized
     * from the same maximum - 7,347, the busiest node in the corpus, whose degree travels in the
     * slice - against a cut holding 110 edges in total. Every incident edge is drawn, so every
     * one of them is nameable, and reading the engine out of a ref during render would be a
     * hazard bought for nothing.
     */
    const relations = useMemo(() => {
        if (!chosen || !predicates) return null;
        return pickEdgeLabels(
            world,
            predicates,
            chosen.index,
            compact ? RELATIONS_SHOWN_COMPACT : RELATIONS_SHOWN,
        );
    }, [chosen, compact, predicates, world]);

    /* How many connections the held subject has *here*, which is not its corpus degree and must
       never be printed as though it were. */
    const drawnHere = useMemo(
        () => (chosen ? edgesOf(world, chosen.index).length : 0),
        [chosen, world],
    );

    const choose = useCallback(
        (index: number | null) => {
            setChosen(index === null ? null : { index, node: slice.nodes[index] });
        },
        [slice],
    );

    /* Clearing the subject is two writes, not one: the engine has to be told as well, or the
       card goes and the dimmed world and the accent edges stay. */
    const release = useCallback(() => {
        engineRef.current?.select(null);
        setChosen(null);
    }, []);

    /* Written in an effect, not during render: a ref assignment during render is a write React
       does not know about, and under a re-entrant render it can publish a handler for a slice
       that is no longer the one on screen. */
    useEffect(() => {
        chooseRef.current = choose;
        heldRef.current = chosen?.index ?? null;
    });

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
                world,
                groupColours: palette.groups,
                background: new Color(palette.page),
                edgeColour: new Color(palette.line),
                accentColour: new Color(palette.accent),
                reducedMotion: reduced,
                /* Twice the rotation per frame at half the frame rate, because OrbitControls
                   advances `autoRotate` per update call rather than per second. Same drift. */
                controls: { zoom: false, pan: false, autoRotate: 0.64 },
                /*
                 * A finger here must still be able to scroll the page.
                 *
                 * OrbitControls sets `touch-action: none` on whatever element it is given,
                 * unconditionally, and inline style beats the stylesheet. On a phone this panel
                 * is about a third of the fold, so a finger landing in it could neither scroll
                 * past nor pinch to zoom - the page simply refused. `pan-y pinch-zoom` keeps
                 * both and leaves the horizontal axis, which is the one a turntable needs.
                 */
                touchAction: "pan-y pinch-zoom",
                maxFps: 30,
                // Fifty lines, not 185,693, so they carry the weight of drawn strokes rather
                // than of ink accumulating.
                edgeWeight: 14,
                events: {
                    onHover: (index) => {
                        setNamed(index === null ? null : slice.nodes[index]);
                        // The first time a reader points at a subject, and not at mount.
                        if (index !== null) wantPredicates();
                        /* The lines a name refers to have to be on screen for the name to mean
                           anything. The graph page learned this in the previous phase; the
                           preview was left hovering over nothing. */
                        engineRef.current?.setEmphasis(index);
                    },
                    /*
                     * A real tap, classified by `installGestures` inside the engine rather than
                     * by a `click` this canvas cannot trust. It selects and it does not
                     * navigate - not even on a tap into empty space, which merely clears.
                     */
                    onTap: (index) => {
                        const current = engineRef.current;
                        current?.select(index);
                        chooseRef.current(index);
                        // The only contact a hoverless device ever makes. Without this the
                        // words would arrive on every desktop and on no phone.
                        if (index !== null) wantPredicates();
                    },
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
        const frame = (spread: number) =>
            // Frames the slice rather than trusting the default camera distance, which is set
            // for a world a thousand units across.
            engine.fitNodes(
                slice.nodes.map((_, i) => i),
                0,
                // No distance floor: the path default puts the camera 700 units out, which for
                // a cloud of radius 420 in a 537 px panel leaves it adrift in the middle.
                { spread, floor: 0 },
            );
        frame(FRAMING_SPREAD);

        const onResize = () => engine.resize();
        window.addEventListener("resize", onResize);

        /*
         * A handle for the tests and for the framing sweep. Nothing in the application reads
         * this.
         *
         * The offscreen pause is only provable as an equality - a count of frames before, a
         * scroll away, the same count after - and a "fewer than a handful" assertion passes
         * with the defect present. `screenOf` exists because the one drag a naive `pick() !==
         * null` guard still gets wrong is the drag that *ends on a subject*, and a test cannot
         * aim at a subject it cannot locate. `refit` is how `FRAMING_SPREAD` was chosen; it is
         * the same lever `setEdgeBudgetOverride` gives the world benchmark.
         */
        const handle = {
            drawCount: () => engine.drawCount,
            paused: () => engine.isPaused,
            count: slice.nodes.length,
            screenOf: (index: number) => engine.screenPositionOf(index),
            refit: frame,
        };
        (window as unknown as Record<string, unknown>).__vedaHero = handle;

        return () => {
            window.removeEventListener("resize", onResize);
            if ((window as unknown as Record<string, unknown>).__vedaHero === handle) {
                delete (window as unknown as Record<string, unknown>).__vedaHero;
            }
            engineRef.current = null;
            engine.dispose();
        };
    }, [palette, slice, wantPredicates, world, flat]);

    /*
     * Names on the field, re-placed on a timer rather than inside the frame loop.
     *
     * Placement is React state, and a `setState` per frame would put the reconciler back into
     * the frame budget the engine exists to keep it out of. A name does not need to move at
     * thirty hertz to look attached to a disc drifting at about two degrees a second: over one
     * interval a disc 200 px from the centre travels well under a pixel.
     *
     * Nothing is written when nothing moved. That is what makes `prefers-reduced-motion` mean
     * still here rather than merely slower - the camera does not move, so the placement is
     * identical, so the DOM is not touched at all. It is also why scrolling past does not leave
     * this re-rendering four spans six times a second behind the reader's back.
     */
    useEffect(() => {
        if (flat) return;
        let timer = 0;
        let last: KeyLabel[] = [];

        const place = () => {
            timer = window.setTimeout(place, PLACE_MS);
            const engine = engineRef.current;
            const canvas = canvasRef.current;
            if (!engine || !canvas || !wanted.current) return;

            const width = canvas.clientWidth;
            const height = canvas.clientHeight;
            const limit = width < COMPACT_CANVAS ? KEY_LABELS_COMPACT : KEY_LABELS;
            const shown: KeyLabel[] = [];
            const consider = (index: number, strong: boolean) => {
                if (shown.length >= limit) return;
                const at = engine.screenPositionOf(index);
                if (!at) return;
                if (at.x < LABEL_ROOM.edge || at.x > width - LABEL_ROOM.edge) return;
                if (at.y < LABEL_ROOM.top || at.y > height - LABEL_ROOM.bottom) return;
                for (const other of shown) {
                    if (
                        Math.abs(other.x - at.x) < COLLIDE_X &&
                        Math.abs(other.y - at.y) < COLLIDE_Y
                    ) {
                        return;
                    }
                }
                shown.push({
                    index,
                    text: slice.nodes[index].label,
                    x: at.x,
                    y: at.y,
                    strong,
                    flipped: at.x > width - LABEL_FLIP,
                });
            };

            /* The held subject is named whatever its degree, and named differently: a reader who
               chose it is owed the tie between the card and the disc it describes. */
            const held = heldRef.current;
            if (held !== null) consider(held, true);
            for (const index of ranked) consider(index, false);

            const same =
                shown.length === last.length &&
                shown.every((label, i) => {
                    const was = last[i];
                    return (
                        was.index === label.index &&
                        was.strong === label.strong &&
                        was.flipped === label.flipped &&
                        Math.abs(was.x - label.x) < 0.5 &&
                        Math.abs(was.y - label.y) < 0.5
                    );
                });
            if (same) return;
            last = shown;
            setKeyLabels(shown);
        };

        /* Started on a timer rather than called: the first placement has to happen after the
           engine has drawn a frame, and a `setState` in an effect body is a render React has
           to throw away. */
        timer = window.setTimeout(place, 0);
        return () => window.clearTimeout(timer);
    }, [flat, ranked, slice]);

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
            />

            {/*
              * Names on the field, so this is a diagram of subjects and not a texture.
              *
              * Duplicated to assistive technology by the list in the panel around this, which is
              * the whole of the fifty and each one a link, so this layer is hidden from it - and
              * it takes no pointer, because a name that swallowed a press would be a hole in the
              * surface the reader turns.
              */}
            {keyLabels.length > 0 && (
                <div aria-hidden="true" className="va-world-preview-labels">
                    {keyLabels.map((label) => (
                        <span
                            className={[
                                "va-world-preview-label",
                                label.strong ? "is-held" : "",
                                label.flipped ? "is-flipped" : "",
                            ]
                                .filter(Boolean)
                                .join(" ")}
                            key={label.index}
                            style={{
                                /* The second translate is a fraction of the label's own width,
                                   which only the browser knows, so the flip has to happen in
                                   the transform rather than in the placement arithmetic. */
                                transform: label.flipped
                                    ? `translate3d(${label.x}px, ${label.y}px, 0) translateX(-100%)`
                                    : `translate3d(${label.x}px, ${label.y}px, 0)`,
                            }}
                        >
                            {label.text}
                        </span>
                    ))}
                </div>
            )}

            {/*
              * Everything written over the foot of the field, stacked rather than layered.
              *
              * The held subject's card and the hover readout used to be two absolutely
              * positioned blocks both anchored to the bottom, which put one on top of the other
              * the moment a subject was held. One column, one scrim, and the card - the thing
              * with the substance in it - sits above the line that answers the pointer.
              */}
            <div className="va-world-preview-foot">
                {/*
                  * The held subject, in words, and the one thing here that navigates.
                  *
                  * Not inside the readout: that paragraph is aria-hidden and pointer-events:
                  * none, and a link inside an aria-hidden subtree is a link nobody using
                  * assistive technology can reach.
                  */}
                {chosen && (
                    <div
                        className="va-world-preview-chosen"
                        data-node-id={chosen.node.id}
                        data-testid="hero-selection"
                    >
                        <div className="va-world-preview-chosen-head">
                            <p className="va-world-preview-chosen-title">
                                <span className="va-world-preview-name">{chosen.node.label}</span>
                                {/*
                                  * A way out that does not depend on finding bare ground.
                                  *
                                  * Tapping the field clears the subject, and on a 537 px panel
                                  * that is enough. Measured at 390, where the panel is 350 by
                                  * 263, this card takes about two thirds of it - so "tap the
                                  * ground to let it go" was an instruction about a strip of
                                  * canvas some forty pixels tall, and a reader who missed it
                                  * hit the card instead and nothing happened. A surface that
                                  * cannot be let go of is the same defect as one that cannot
                                  * be held, arrived at from the other side.
                                  *
                                  * On the name's own row rather than after the kind line: given
                                  * its own row it made the card taller, which is the opposite
                                  * of the problem it was added to solve.
                                  */}
                                <button
                                    className="va-world-preview-release"
                                    onClick={release}
                                    type="button"
                                >
                                    Let go
                                    <span className="sr-only"> of {chosen.node.label}</span>
                                </button>
                            </p>
                            <p className="va-world-preview-kind">
                                {chosen.node.group.replace(/-/g, " ")} ·{" "}
                                {chosen.node.degree.toLocaleString()} connections in the corpus
                            </p>
                        </div>

                        {relations && relations.length > 0 ? (
                            <ul className="va-world-preview-relations">
                                {relations.map((relation) => {
                                    const other = (
                                        <span
                                            className="va-world-preview-other"
                                            key="other"
                                        >
                                            {slice.nodes[relation.other].label}
                                        </span>
                                    );
                                    const phrase = (
                                        <span
                                            className="va-world-preview-predicate"
                                            key="phrase"
                                        >
                                            {relation.text}
                                        </span>
                                    );
                                    /*
                                     * Written in the order the edge is stored, which is the
                                     * relationship inspector's own rule and for its reason: ten
                                     * of fifty-seven predicates declare a direction, so leading
                                     * every row with the held subject would assert a direction
                                     * the ontology does not. Where the held subject is the
                                     * stored target, the far name leads and the phrase runs
                                     * back to it.
                                     */
                                    return (
                                        <li key={relation.edge}>
                                            {relation.outgoing ? [phrase, other] : [other, phrase]}
                                        </li>
                                    );
                                })}
                            </ul>
                        ) : (
                            /* The vocabulary has not arrived, so the connections are counted
                               rather than named. "Here" is load-bearing: this is the count
                               inside a fifty-node cut, not the corpus degree printed twice. */
                            <p className="va-world-preview-relations-absent">
                                {drawnHere === 1 ? "One connection" : `${drawnHere} connections`}{" "}
                                drawn here.
                            </p>
                        )}

                        <Link
                            className="va-world-preview-explore"
                            data-testid="hero-explore"
                            href={`/graph?view=focus&renderer=3d&node=${encodeURIComponent(chosen.node.id)}`}
                        >
                            Explore {chosen.node.label} in the Knowledge World
                            <span aria-hidden="true"> →</span>
                        </Link>
                    </div>
                )}

                {/*
                  * What is under the pointer.
                  *
                  * Hover only, now that a held subject has a card of its own. It used to prefer
                  * the held subject over the hovered one, which meant that once anything was
                  * held the readout stopped answering the pointer: hovering a second subject
                  * drew that subject's connections and named the first one.
                  *
                  * The copy used to say "click any subject to open it", which was an accurate
                  * description of a defect - a click left the page, and so did the click that
                  * ended an orbit.
                  */}
                {/* Not rendered at all while a subject is held and nothing is under the
                    pointer: the card says what is held and carries its own way out, so a line
                    repeating the instruction was one more row of a panel that has 263 px of
                    height on a phone. */}
                {(named || !chosen) && (
                    <p className="va-world-preview-readout" aria-hidden="true">
                        {named ? (
                            <>
                                <span className="va-world-preview-name">{named.label}</span>
                                <span className="va-world-preview-kind">
                                    {named.group.replace(/-/g, " ")} ·{" "}
                                    {named.degree.toLocaleString()} connections
                                </span>
                            </>
                        ) : (
                            <span className="va-world-preview-kind">
                                Drag to turn it. Tap a subject to hold it.
                            </span>
                        )}
                    </p>
                )}
            </div>
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
            {/* The same foot as the spatial branch, so the scrim and the inset are declared
                once rather than twice with a chance of disagreeing. */}
            <div className="va-world-preview-foot">
                <p className="va-world-preview-readout" aria-hidden="true">
                    <span className="va-world-preview-kind">
                        Drawn flat on this device.{" "}
                        <button type="button" onClick={() => onOpen(null)}>
                            Open the graph
                        </button>
                    </span>
                </p>
            </div>
        </div>
    );
}
