"use client";

import type { World, WorldLabels } from "./artifact";
import {
    FADE_MS,
    LABEL_FRACTIONS,
    LABEL_STRIDE,
    LABEL_TIER,
    LabelLayout,
    NAME_QUADRANTS,
    TOTAL_LABEL_CAP,
    countOverlaps,
    isNameKey,
    isPathKey,
    nodeNameAnchors,
    nodeOfNameKey,
    pathStepOf,
    resolveCandidate,
    totalLabelCap,
    type EdgeLabelPick,
    type LabelAnchor,
    type LabelCandidate,
    type LabelKind,
    type LabelRect,
    type PlacedLabel,
} from "./edge-labels";

/**
 * The words on the lines and the names on the orbs, as DOM, out of one pool.
 *
 * ## Why DOM and not sprites or a second canvas
 *
 * Measured, interleaved against a baseline under load, absolutely-positioned spans moved every
 * frame are the cheaper of the two available techniques, and they are also the one that gets the
 * project's real typefaces, its diacritics, its theme tokens and its opaque plate for nothing. A
 * texture atlas would have to reproduce all four and would still set Charis SIL's combining marks
 * worse than the browser does.
 *
 * The figures in the previous version of this comment - "+0.109 ms for sixteen spans, +0.292 ms
 * for sixteen `fillText` calls" - are **not reproducible from anything committed**. No script in
 * the repository produces them and no recorded run contains them. They are replaced by figures
 * from `scripts/bench-world.mjs --labels`, whose method is written down there: an interleaved
 * 0/16/0/16 paired delta, with the number of labels *actually placed* recorded alongside each
 * cap, because a cost measured "at cap 16" means nothing if only eight were placed.
 *
 * The usual objection - never one element per graph node - is about count, not technique. It
 * bites at hundreds. The cap here is twenty-four across both classes.
 *
 * ## Why it is a class and not a component
 *
 * Positions change every frame during an orbit. Routing that through React state would put the
 * reconciler back inside the frame budget, which is the one thing the engine is arranged to keep
 * it out of. The pool is allocated once, at the total cap, and thereafter only `textContent`,
 * `transform`, `className` and `opacity` are written - no elements are created, destroyed or
 * reordered while the camera moves.
 *
 * ## One pool for both classes
 *
 * Names used to be a separate React component, `world-labels.tsx`, placing itself on its own
 * 160 ms timer and handing its boxes to this file as obstacles. ARB-3 replaced that with one pass
 * over one priority order, which means one pool: a span is a name or a phrase depending on what
 * the layout put in it, and the two can genuinely trade places.
 *
 * ## The frame does not run the assignment
 *
 * Per frame, `update` looks up the current position of each *already placed* label and writes a
 * `transform`. The assignment - which labels, in which of their candidate positions - runs on a
 * debounced settle. Two reasons, both from ARB-3: the annealing finish cannot be afforded sixty
 * times a second, and a label placed against moving geometry ends up describing the line it was
 * beside two frames ago. Quiescence is measured here rather than taken on trust from a transition
 * callback, so a camera flight, a resize and a physics tick are all covered by one rule;
 * `requestAssignment` exists for a transition that knows better.
 *
 * That split is also what keeps the per-frame cost small. Only placed labels are projected, so a
 * frame does at most twenty-four position lookups. The full candidate set - up to forty-eight
 * names at four positions each, plus the phrases at three - is built once per settle.
 */

/** Reused for every measurement, so text width never costs a layout of the real pool. */
const RELATION_MEASURE_CLASS = "va-edge-label is-measuring";
const NAME_MEASURE_CLASS = "va-world-label is-measuring";

/**
 * How still the geometry has to be, and for how long, before an assignment runs.
 *
 * Two frames at sixty hertz is 33 ms and would fire in the middle of an eased camera flight,
 * where the geometry is briefly almost stationary at each end. A hundred and twenty is longer
 * than any such lull and shorter than a reader's patience for an unlabelled diagram. It also sits
 * inside the 300 ms crossfade, so the labels for a new pose have begun fading in before the
 * previous set has finished fading out.
 */
const SETTLE_MS = 120;

/** Below this the geometry counts as still. Sub-pixel drift is not movement. */
const STILL_PX = 0.75;

/** What the renderer tells this file about the scene. It supplies facts and places nothing. */
export type LabelScene = {
    world: World | null;
    labels: WorldLabels | null;
    /** The chosen subject. Its name is a reserved tier. */
    selected: number | null;
    /** The subject under the pointer. */
    hovered: number | null;
    /** Neighbours worth naming, most important first - `focus.ts`'s `shown` order. */
    neighbours: ArrayLike<number>;
};

const NO_SCENE: LabelScene = {
    world: null,
    labels: null,
    selected: null,
    hovered: null,
    neighbours: [],
};

/** A span in the pool, and what it is currently showing. */
type Cell = {
    span: HTMLSpanElement;
    key: number | null;
    /** When its fade-out ends. Until then the span is not available for a different label. */
    freeAt: number;
    /** Last written transform, so an unchanged frame writes nothing. */
    at: string;
    className: string;
};

export class EdgeLabelView {
    private readonly root: HTMLDivElement;
    private readonly pool: Cell[] = [];
    private readonly relationRuler: HTMLSpanElement;
    private readonly nameRuler: HTMLSpanElement;
    private readonly layout = new LabelLayout();
    private picks: EdgeLabelPick[] = [];
    /** Immovable boxes already inked by the caller. See `LabelLayout.place`. */
    private readonly obstacles?: () => LabelRect[];
    /** Screen position of an orb, from whoever owns the projection. */
    private readonly positionOf?: (node: number) => { x: number; y: number } | null;
    private scene: LabelScene = NO_SCENE;
    private relationCap: number;
    private capOverride: number | null = null;
    /** The relationship the inspector is open on. Tier 90. */
    private inspected: number | null = null;
    private relationTier: number = LABEL_TIER.RELATION;

    /** The last frame's projected points, so the benchmark can re-run either half. */
    private lastPoints: Float32Array<ArrayBufferLike> = new Float32Array(0);
    private lastViewportSize = { width: 0, height: 0 };

    /** The last assignment, and the anchors it was made from. */
    private placedList: PlacedLabel[] = [];
    private placedByKey = new Map<number, PlacedLabel>();
    private anchorsByKey = new Map<number, LabelAnchor>();
    private dirty = true;
    private lastSignature = 0;
    private stillSince = 0;
    private lastViewport = "";
    private onCount?: (count: number) => void;
    private lastCount = -1;

    constructor(
        container: HTMLElement,
        /** The relationship-phrase cap for the current mode and width. */
        max: number,
        onPick?: (edge: number) => void,
        obstacles?: () => LabelRect[],
        /**
         * How to project a node to the canvas, so that subject names can enter the one collision
         * pass as candidates rather than as obstacles.
         *
         * The spatial view supplies this. The planar view inks its names into the 2D context
         * during its own draw pass and passes them through `obstacles` instead; see
         * `LabelLayout.place` for why that asymmetry is real and what it costs.
         */
        positionOf?: (node: number) => { x: number; y: number } | null,
    ) {
        this.obstacles = obstacles;
        this.positionOf = positionOf;
        this.relationCap = max;
        this.root = document.createElement("div");
        this.root.className = "va-edge-labels";
        /* The canvas is already `aria-hidden` and the connections are listed as text in the panel
           beside it. Announcing two dozen fragments that appear and vanish under a moving pointer
           would be noise, and the same information is available in a form that can actually be
           navigated - which, since this phase, means the relationships themselves and not only
           the subjects they join. */
        this.root.setAttribute("aria-hidden", "true");

        /*
         * The pool is allocated at the total cap and never resized.
         *
         * It used to be allocated at the *current* width's cap, at construction, with no resize
         * path at all: rotating a phone or dragging a window across the breakpoint left an
         * eight-span pool while the layout was choosing sixteen labels, and the extra ones were
         * dropped with nothing to indicate it. Twenty-four spans is twenty-four spans, and an
         * unused one costs a single `opacity: 0`.
         */
        for (let i = 0; i < TOTAL_LABEL_CAP; i += 1) {
            const span = document.createElement("span");
            span.className = "va-edge-label";
            span.style.opacity = "0";
            span.dataset.shown = "false";
            if (onPick) {
                /*
                 * The label is the way in.
                 *
                 * A relationship in a 3D scene is a one-pixel line, and asking someone to hit one
                 * is asking them to fail. The word sitting on it is a large, obvious target that
                 * is already the thing they are reading, so clicking it is what opening its
                 * explanation should mean. On a phone that word is about 17 px tall, which is not
                 * a target either, so it carries an invisible pad out to 44 - and the collision
                 * layout runs against that pad rather than against the ink, or adjacent pads
                 * overlap and the later one silently steals the earlier one's taps.
                 *
                 * Kept out of the keyboard path deliberately: this layer is `aria-hidden` and
                 * these are not buttons, because two dozen controls appearing and vanishing under
                 * a moving pointer would be a hostile tab order. The keyboard path is the
                 * relations list in the panel, which is ordinary, stable markup built from the
                 * same selection pass - see `describeRelations`.
                 */
                span.dataset.pickable = "true";
                span.addEventListener("click", () => {
                    // A faded span keeps its last edge in the dataset; clicking through to it
                    // would open an explanation of a relationship no longer on screen.
                    if (span.dataset.shown !== "true") return;
                    const edge = span.dataset.edge;
                    if (edge === undefined || edge === "") return;
                    /* Held at tier 90 from here, optimistically. The reader has just asked what
                       this relationship establishes, so it is the one label the collision pass
                       must not then drop - and this is the only place that knows it happened
                       without a new prop being threaded from the page through the renderer. It is
                       cleared when the subject changes or the edge leaves the picks, and
                       `setInspected` lets whoever owns that state say so properly. */
                    this.inspected = Number(edge);
                    this.dirty = true;
                    onPick(Number(edge));
                });
            }
            this.root.appendChild(span);
            this.pool.push({ span, key: null, freeAt: 0, at: "", className: "va-edge-label" });
        }

        this.relationRuler = document.createElement("span");
        this.relationRuler.className = RELATION_MEASURE_CLASS;
        this.root.appendChild(this.relationRuler);
        this.nameRuler = document.createElement("span");
        this.nameRuler.className = NAME_MEASURE_CLASS;
        this.root.appendChild(this.nameRuler);

        container.appendChild(this.root);

        /*
         * A handle for `scripts/bench-world.mjs --labels` and for
         * `tests/e2e/graph-labels.spec.ts`. Nothing in the application reads it.
         *
         * The cap override is what lets the benchmark interleave 0/16/0/16 within one page rather
         * than measuring two runs and subtracting, and `shownLabels` is what lets it record how
         * many were actually placed at each cap.
         */
        (window as unknown as Record<string, unknown>).__vedaLabels = {
            setCapOverride: (value: number | null) => {
                this.capOverride = value;
                this.requestAssignment();
            },
            shownLabels: () => this.placedList.map((label) => ({ ...label })),
            overlaps: () => countOverlaps(this.placedList),
            /*
             * The two halves of the ARB-3 split, timed separately.
             *
             * The interleaved frame-interval delta this was meant to be measured with returns
             * noise on any machine whose frame interval is quantised to vsync: measured here, the
             * arms came back at 33.3 ms against 33.3 ms and 16.7 ms, so the paired delta was
             * -8.3 ms - a negative cost, which is the instrument reporting that the signal is two
             * orders of magnitude below its resolution. The method is right and the instrument
             * cannot see through it, so the two costs are timed directly instead.
             *
             * `assignment` is the per-settle cost: the greedy pass, the annealer, the hysteresis
             * bookkeeping and the span binding. `frame` is the per-frame cost: one position lookup
             * and one `transform` write per placed label, which is all a frame is allowed to do.
             */
            timeAssignment: (runs = 30) => {
                const samples: number[] = [];
                for (let i = 0; i < runs; i += 1) {
                    const anchors = this.buildAnchors(this.lastPoints, this.lastViewportSize);
                    const began = performance.now();
                    this.assign(anchors, this.lastViewportSize, performance.now());
                    samples.push(performance.now() - began);
                }
                return median(samples);
            },
            timeFrame: (runs = 200) => {
                const samples: number[] = [];
                for (let i = 0; i < runs; i += 1) {
                    const began = performance.now();
                    this.writeTransforms(this.lastPoints, this.lastViewportSize, performance.now());
                    samples.push(performance.now() - began);
                }
                return median(samples);
            },
            placed: () => this.placedList.length,
        };
    }

    /* -------------------------------------------------------------- what to say - */

    /**
     * Change which connections are named.
     *
     * Called when the hover or the selection moves, not per frame. Resets the layout's memory so
     * a new subject's labels are not judged against the last subject's incumbents, and so its
     * cooldowns are not still running when the reader comes back to it.
     */
    setLabels(picks: EdgeLabelPick[]) {
        this.picks = picks;
        if (this.inspected !== null && !picks.some((pick) => pick.edge === this.inspected)) {
            this.inspected = null;
        }
        this.layout.reset();
        this.placedList = [];
        this.placedByKey.clear();
        this.requestAssignment();
        if (picks.length === 0) this.releaseAll();
    }

    /**
     * The scene the names are drawn from.
     *
     * Facts only. Which of them get named, in which quadrant, at which tier and under which cap
     * is decided by `nodeNameAnchors` and `LabelLayout` - the renderer supplies the projection
     * and the membership and places nothing, which is the division ARB-3 sets out.
     */
    setScene(scene: LabelScene) {
        this.scene = scene;
        this.requestAssignment();
    }

    /** The relationship-phrase cap changed, because the mode or the width did. */
    setRelationCap(max: number) {
        if (this.relationCap === max) return;
        this.relationCap = max;
        this.requestAssignment();
    }

    /**
     * Which relationship the inspector is open on, so it is held at tier 90.
     *
     * The label a reader clicked to open an explanation must not then be the one the collision
     * pass drops, which is what happens when it is ranked like any other phrase.
     */
    setInspected(edge: number | null) {
        if (this.inspected === edge) return;
        this.inspected = edge;
        this.requestAssignment();
    }

    /**
     * Ask for an assignment as soon as the geometry is still, rather than waiting for something
     * to change.
     *
     * ARB-2 gives the FOCUS transition a stage boundary precisely so that labels arrive on
     * settled geometry; calling this at that boundary is strictly better than waiting for the
     * quiescence test to notice, and until something calls it the quiescence test covers the same
     * ground a little later.
     */
    requestAssignment() {
        this.dirty = true;
    }

    /** Told when the number on screen changes. Once per settle, never per frame. */
    onPlacedCount(listener: (count: number) => void) {
        this.onCount = listener;
    }

    /** What is on screen right now. The e2e gate and the benchmark read this. */
    shownLabels(): readonly PlacedLabel[] {
        return this.placedList;
    }

    /** The font changed, so every cached measurement is wrong. */
    invalidateMeasurements() {
        this.layout.invalidateMeasurements();
        this.requestAssignment();
    }

    /* ----------------------------------------------------------------- the frame - */

    /**
     * Place this frame's labels.
     *
     * `points` carries one `LABEL_STRIDE` run per pick, in the order `setLabels` was given: a
     * usable flag, then an x and a y for each of `LABEL_FRACTIONS`, in CSS pixels relative to the
     * container. Whoever projected them decides what usable means - behind the camera in the
     * spatial view, nothing in the planar one.
     */
    /**
     * Whether an assignment is still owed.
     *
     * A renderer that sleeps has to know. The assignment deliberately waits for the scene to
     * have been still for `SETTLE_MS`, because placing a phrase against moving geometry attaches
     * it to whichever line happens to pass underneath - so the last `update` of a settling
     * scene arrives when it has been still for roughly nothing, and the one that would cross the
     * deadline has to be asked for.
     *
     * The spatial view never needed this: its frame loop runs whether or not anything moved, so
     * the next call always came. The planar view stopped repainting a settled diagram - correctly,
     * it was burning sixty repaints a second on a still scene - and the two changes together
     * meant the deadline was never reached and nothing was ever placed. Measured on a production
     * build: eight phrases in the spatial view, nought in the planar one, with its label spans
     * allocated, empty and at opacity zero.
     */
    get pending() {
        return this.dirty;
    }

    update(points: Float32Array, viewport: { width: number; height: number }) {
        const now = performance.now();
        this.lastPoints = points;
        this.lastViewportSize = viewport;

        /*
         * Quiescence, from a cheap signature over the geometry that is actually driving labels:
         * the first candidate of every pick, plus the orb of every subject currently named. If it
         * has not moved by more than a pixel since the last frame the scene is still, and once it
         * has been still for SETTLE_MS an assignment may run.
         *
         * Deliberately one number for the whole scene rather than a test per label. A single node
         * still easing into place is enough to make the scene unsettled, which is the conservative
         * answer and the right one: the cost of waiting is 120 ms and the cost of not waiting is a
         * phrase attached to the wrong line.
         */
        let signature = 0;
        for (let i = 0; i < this.picks.length; i += 1) {
            const base = i * LABEL_STRIDE;
            signature += points[base + 1] + points[base + 2] * 3;
        }
        if (this.positionOf) {
            for (const label of this.placedList) {
                if (!isNameKey(label.key)) continue;
                const at = this.positionOf(nodeOfNameKey(label.key));
                if (at) signature += at.x + at.y * 3;
            }
        }

        const viewportKey = `${Math.round(viewport.width)}x${Math.round(viewport.height)}`;
        if (viewportKey !== this.lastViewport) {
            this.lastViewport = viewportKey;
            this.dirty = true;
            this.stillSince = now;
        }
        if (Math.abs(signature - this.lastSignature) > STILL_PX) {
            this.lastSignature = signature;
            this.stillSince = now;
            this.dirty = true;
        }

        if (this.dirty && now - this.stillSince >= SETTLE_MS) {
            this.assign(this.buildAnchors(points, viewport), viewport, now);
            this.dirty = false;
        }

        this.writeTransforms(points, viewport, now);
    }

    /* --------------------------------------------------------------- the anchors - */

    /**
     * The full candidate set, built once per settle.
     *
     * Relationship phrases first, capped by the mode's own budget, then the names - whose
     * selection, tiers and quadrants come from `nodeNameAnchors`. The total cap across both is
     * applied by the layout rather than here, because it is a property of the assignment and not
     * of either class.
     */
    private buildAnchors(
        points: Float32Array,
        viewport: { width: number; height: number },
    ): LabelAnchor[] {
        const anchors: LabelAnchor[] = [];
        const cap = this.capOverride ?? this.relationCap;

        for (let i = 0; i < this.picks.length && anchors.length < cap; i += 1) {
            const pick = this.picks[i];
            const base = i * LABEL_STRIDE;
            const projected = points[base] === 1;
            const candidates: LabelCandidate[] = [];
            let anyUsable = false;
            for (let f = 0; f < LABEL_FRACTIONS.length; f += 1) {
                const x = points[base + 1 + f * 2];
                const y = points[base + 2 + f * 2];
                /* Off screen is not a collision and must not consume a slot. The projection
                   reports depth validity; the viewport test belongs here, where the viewport is
                   known - and it is applied per candidate, so a position that has slid off the
                   canvas simply takes the next one along the same line rather than losing the
                   label. Marked rather than removed; see `LabelCandidate.usable`. */
                const usable =
                    projected && x >= 0 && y >= 0 && x <= viewport.width && y <= viewport.height;
                if (usable) anyUsable = true;
                candidates.push({ x, y, usable });
            }
            anchors.push({
                key: pick.edge,
                kind: "relation",
                tier: LABEL_TIER.RELATION,
                weight: Math.max(0, Math.min(pick.priority, 0.99)),
                text: this.textOf(pick),
                candidates,
                usable: anyUsable,
            });
        }

        if (this.positionOf && this.scene.world) {
            const names = nodeNameAnchors({
                world: this.scene.world,
                labels: this.scene.labels,
                positionOf: this.positionOf,
                selected: this.scene.selected,
                hovered: this.scene.hovered,
                neighbours: this.scene.neighbours,
                viewport,
            });
            this.relationTier = names.relationTier;
            for (const anchor of names.anchors) anchors.push(anchor);
        }

        /* The tier of a phrase depends on whether the scene is hover-driven, which is decided by
           the name layer, so it is applied after rather than during the loop above. See
           `NameLayer.relationTier` for why that decision lives there. */
        for (const anchor of anchors) {
            if (anchor.kind === "relation") anchor.tier = this.tierOf(anchor.key);
        }

        return anchors;
    }

    /**
     * Which tier a relationship sits in.
     *
     * Derived from the pick rather than passed in, so a renderer does not need to know the tier
     * table to get PATH right: the spatial view already keys a route's hops as `-1 - step`,
     * because a hop is not one edge in the world file, and that is enough to identify them.
     */
    private tierOf(edge: number): number {
        if (isPathKey(edge)) return LABEL_TIER.PATH_STEP;
        if (this.inspected === edge) return LABEL_TIER.INSPECTED_RELATION;
        return this.relationTier;
    }

    /**
     * The words, and for a route the step numeral in front of them.
     *
     * A route has a direction and the reader needs it, but an arrowhead is the wrong way to say
     * so, and no arrowhead exists anywhere in this product today. Of the sixty predicates the
     * exported vocabulary declares, **eight** declare a direction at all - five DIRECTED and
     * three SYMMETRIC - and all eight are among the forty-eight edge types the artifact can draw,
     * so all eight reach the drawable set. An arrowhead on a drawn line would therefore assert a
     * direction for the other fifty-two, which decline to state one, and a route can traverse a
     * symmetric edge backwards besides. The numeral carries traversal order without claiming that
     * the relationship has one.
     *
     * The figure to quote is **8 of 60**. The previous commit message said "ten of fifty-seven",
     * which was wrong in both numbers: 57 was the Python vocabulary's count before the export
     * grew to 60, and the 10 counted two predicates - one unpopulated by design - that do not
     * appear among the artifact's edge types at all. Verified against
     * `public/world/world.predicates.json` and the artifact manifest.
     */
    private textOf(pick: EdgeLabelPick): string {
        if (!isPathKey(pick.edge)) return pick.text;
        return `${pathStepOf(pick.edge)}. ${pick.text}`;
    }

    /* ----------------------------------------------------------- the assignment - */

    private assign(
        anchors: LabelAnchor[],
        viewport: { width: number; height: number },
        now: number,
    ) {
        const frame = this.layout.place({
            anchors,
            viewport,
            measure: (text, kind) => this.measure(text, kind),
            reserved: this.obstacles?.() ?? [],
            /* The benchmark's override bounds the total as well as the phrase cap, so its zero arm
               is genuinely zero labels rather than zero phrases beside an unchanged set of names.
               A paired delta against a moving control measures nothing. */
            total: Math.min(totalLabelCap(viewport.width), this.capOverride ?? Number.MAX_SAFE_INTEGER),
            /* The phrases' reserved share of the total. Without it the names, which outrank plain
               relations, take the whole total before one phrase is considered - measured at nine
               names and one phrase on Indra. See `LabelLayout.place`. */
            relationBudget: this.capOverride ?? this.relationCap,
            now,
        });
        this.placedList = frame.placed;
        this.placedByKey = new Map(frame.placed.map((label) => [label.key, label]));
        this.anchorsByKey = new Map(anchors.map((anchor) => [anchor.key, anchor]));

        /* Spans are bound to keys here and only here, so a label that keeps its place across a
           settle keeps its element too. That is what lets the crossfade mean anything, and it is
           the same object-constancy rule the FOCUS transition works under: a mark must never be
           reused to depict a different data point without a fade in between. */
        const held = new Map<number, Cell>();
        for (const cell of this.pool) if (cell.key !== null) held.set(cell.key, cell);

        const used = new Set<Cell>();
        for (const label of this.placedList) {
            const cell = held.get(label.key) ?? this.takeFree(now, used);
            if (!cell) continue;
            used.add(cell);
            this.write(cell, label);
        }
        for (const cell of this.pool) {
            if (used.has(cell) || cell.key === null) continue;
            // Leaving: hold the last position, fade out, and stay unavailable until it has.
            cell.key = null;
            cell.freeAt = now + FADE_MS;
            /* Untargetable the instant it starts to leave, not when the fade ends. A chip the
               reader can no longer read must not still be taking their clicks. */
            cell.span.dataset.shown = "false";
            if (cell.span.style.opacity !== "0") cell.span.style.opacity = "0";
        }

        this.report(this.placedList.length);
    }

    /** A span nobody is using whose fade has finished, or failing that the one freed longest ago. */
    private takeFree(now: number, used: Set<Cell>): Cell | null {
        let oldest: Cell | null = null;
        for (const cell of this.pool) {
            if (used.has(cell) || cell.key !== null) continue;
            if (cell.freeAt <= now) return cell;
            if (!oldest || cell.freeAt < oldest.freeAt) oldest = cell;
        }
        return oldest;
    }

    private write(cell: Cell, label: PlacedLabel) {
        const className = label.kind === "name" ? nameClass(label.tier) : "va-edge-label";
        if (cell.className !== className) {
            cell.span.className = className;
            cell.className = className;
        }
        if (cell.span.textContent !== label.text) cell.span.textContent = label.text;
        cell.span.dataset.edge = label.kind === "relation" ? String(label.key) : "";
        cell.span.dataset.tier = String(label.tier);
        /*
         * What makes the chip a target, and the only thing that does.
         *
         * It used to be `pointer-events: auto` on every pickable span in the pool, whether or not
         * it was showing anything - so a faded, empty, fully transparent chip still intercepted
         * clicks on the canvas underneath it. Playwright found it by refusing to click a label:
         * "<span data-pickable=true class=va-edge-label> intercepts pointer events", on an empty
         * span at opacity 0. A reader clicking where a retired label used to be hit nothing at
         * all, which is indistinguishable from the graph ignoring them.
         *
         * An attribute rather than reading the opacity, because CSS cannot test an inline opacity
         * and because the same flag then gates the touch pad: an invisible chip must not carry a
         * 44 px pad either.
         */
        cell.span.dataset.shown = "true";
        /* The invisible touch pad, written from the layout's own guard box, so the rectangle the
           browser hit-tests and the rectangle the layout kept clear are the same rectangle.
           Deriving them in two places is exactly how adjacent 44 px pads came to overlap by
           15.8 px elsewhere in this product. */
        /* Rounded up, not to nearest. The guard box is 44.0 and the ink 17.8, so the pad is 13.1
           on each side; rounding to nearest painted a 43.8 px target and made a claim of "44"
           false by 0.2 px, which measurement finds and a reader does not. */
        const padX = Math.ceil((label.hitWidth - label.width) / 2);
        /*
         * The exact half, not a ceiled one.
         *
         * `Math.ceil` was here to avoid landing under the floor and it guaranteed landing under
         * it: ceiling the half and then doubling can only produce an even total, so a chip of
         * 17.75 got 13 a side and a 43.75 px target - a quarter of a pixel short of a
         * requirement, twice measured. The guard box is already at least `TOUCH_MIN`, so half of
         * its excess is the right number and sub-pixel padding is something CSS handles.
         */
        const padY = (label.hitHeight - label.height) / 2;
        cell.span.style.setProperty("--va-label-pad-x", `${padX}px`);
        cell.span.style.setProperty("--va-label-pad-y", `${padY}px`);
        cell.key = label.key;
        cell.freeAt = 0;
        if (cell.span.style.opacity !== "1") cell.span.style.opacity = "1";
    }

    /* --------------------------------------------------------- the frame's work - */

    /**
     * Move what is already placed, and nothing else.
     *
     * The candidate index is latched by the layout, so a label follows its own chosen position
     * along its own line as the camera moves. It is not re-collided: two labels can drift into
     * each other between settles, and the alternative - re-collide every frame - is the six-hertz
     * toggle this phase exists to remove. The drift is bounded by SETTLE_MS, after which the
     * assignment runs again and resolves it properly.
     */
    private writeTransforms(
        points: Float32Array,
        viewport: { width: number; height: number },
        now: number,
    ) {
        for (const cell of this.pool) {
            if (cell.key === null) continue;
            const label = this.placedByKey.get(cell.key);
            if (!label) continue;
            const at = this.currentPosition(label, points);
            if (!at) {
                /* The position it was placed at has left the canvas. Fade rather than jump: a
                   label that teleports to a different part of its line reads as a different
                   label, which is the one thing object constancy forbids. */
                cell.key = null;
                cell.freeAt = now + FADE_MS;
                cell.span.dataset.shown = "false";
                cell.span.style.opacity = "0";
                this.dirty = true;
                continue;
            }
            const box = resolveCandidate(at, label.width, label.height, viewport);
            // Rounded to whole pixels: subpixel positions make text shimmer as the camera drifts,
            // and a label that shimmers is read as broken rather than as precise.
            const transform = `translate3d(${Math.round(box.x)}px, ${Math.round(box.y)}px, 0)`;
            if (cell.at !== transform) {
                cell.span.style.transform = transform;
                cell.at = transform;
            }
        }
    }

    /**
     * Where a placed label's latched candidate is this frame.
     *
     * The *index* is what was latched, not the coordinates: a name follows its orb and never
     * changes which side of it it sits on, and a phrase follows its own fraction along its own
     * line. Recomputing from the index rather than reusing the placed box is what makes the
     * per-frame half of the pipeline correct at sixty hertz without re-running the assignment.
     */
    private currentPosition(label: PlacedLabel, points: Float32Array): LabelCandidate | null {
        if (label.kind === "name") {
            if (!this.positionOf) return null;
            const at = this.positionOf(nodeOfNameKey(label.key));
            if (!at) return null;
            const quadrant = NAME_QUADRANTS[Math.min(label.candidate, NAME_QUADRANTS.length - 1)];
            return {
                x: at.x + quadrant.dx,
                y: at.y + quadrant.dy,
                anchorX: quadrant.anchorX,
                anchorY: quadrant.anchorY,
            };
        }

        const index = this.picks.findIndex((pick) => pick.edge === label.key);
        if (index < 0) return null;
        const base = index * LABEL_STRIDE;
        if (points[base] !== 1) return null;
        const f = Math.min(label.candidate, LABEL_FRACTIONS.length - 1);
        return { x: points[base + 1 + f * 2], y: points[base + 2 + f * 2] };
    }

    private releaseAll() {
        for (const cell of this.pool) {
            cell.key = null;
            cell.freeAt = 0;
            cell.span.dataset.shown = "false";
            if (cell.span.style.opacity !== "0") cell.span.style.opacity = "0";
        }
    }

    private report(count: number) {
        if (count === this.lastCount) return;
        this.lastCount = count;
        this.onCount?.(count);
    }

    /**
     * Text size, in the font the label is actually set in.
     *
     * A hidden span rather than canvas `measureText`, because the canvas would need the font
     * shorthand rebuilt by hand and would get letter-spacing and font-feature settings wrong. Two
     * rulers, because the two classes are set in different faces at different sizes: the name
     * placement this replaces measured every label against one fixed 132 x 20 rectangle, which
     * over-reserved by a factor of four for the word "Agni" and under-reserved for a long
     * constellation name against a `max-width` of 13rem. This costs one layout per distinct string
     * per class; the phrase set is the predicate vocabulary, about sixty strings for the whole
     * corpus, and `LabelLayout` caches by string.
     */
    private measure(text: string, kind: LabelKind): { width: number; height: number } {
        const ruler = kind === "name" ? this.nameRuler : this.relationRuler;
        ruler.textContent = text;
        return {
            width: ruler.offsetWidth,
            height: ruler.offsetHeight || (kind === "name" ? 17 : 16),
        };
    }

    destroy() {
        this.root.remove();
        const globals = window as unknown as Record<string, unknown>;
        if (globals.__vedaLabels) delete globals.__vedaLabels;
    }
}

/** The median of a sample, for the benchmark hooks. */
function median(samples: number[]): number {
    const sorted = [...samples].sort((a, b) => a - b);
    return Number(sorted[Math.floor(sorted.length / 2)].toFixed(4));
}

/** A name is set larger and darker when it is the chosen subject or the one under the pointer. */
function nameClass(tier: number): string {
    return tier >= LABEL_TIER.HOVERED_NAME ? "va-world-label is-strong" : "va-world-label";
}
