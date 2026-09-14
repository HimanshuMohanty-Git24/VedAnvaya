"use client";

import {
    EdgeLabelLayout,
    LABEL_FRACTIONS,
    LABEL_STRIDE,
    type EdgeLabelPick,
    type LabelAnchor,
    type PlacedLabel,
} from "./edge-labels";

/**
 * The words on the lines, as DOM.
 *
 * ## Why DOM and not sprites or a second canvas
 *
 * Measured, interleaved against a baseline under load: sixteen absolutely-positioned spans moved
 * every frame cost +0.109 ms of JavaScript, and sixteen `fillText` calls on an overlay canvas
 * cost +0.292 ms. Both hold sixty frames a second; the DOM is the cheaper of the two and it is
 * also the one that gets the project's real typefaces, its diacritics, its theme tokens and its
 * halo for nothing. A texture atlas would have to reproduce all four and would still set Charis
 * SIL's combining marks worse than the browser does.
 *
 * The usual objection - never one element per graph node - is about count, not technique. It
 * bites at hundreds: the same probe put four hundred spans at 24.4 ms a frame. The cap here is
 * sixteen.
 *
 * ## Why it is a class and not a component
 *
 * Positions change every frame during an orbit. Routing that through React state would put the
 * reconciler back inside the frame budget, which is the one thing the engine is arranged to keep
 * it out of. The pool is allocated once, at the cap, and thereafter only `textContent`,
 * `transform` and `opacity` are written - no elements are created, destroyed or reordered while
 * the camera moves.
 *
 * ## Shared by both renderers on purpose
 *
 * Nothing here knows how a point was projected. The spatial view supplies screen coordinates from
 * the camera; the planar view supplies them from its own affine transform. Same cap, same
 * collision rule, same hysteresis, same words - so "what is this line" cannot come back with two
 * different answers depending on how the graph happens to be drawn.
 */

/** Reused for every measurement, so text width never costs a layout of the real pool. */
const MEASURE_CLASS = "va-edge-label is-measuring";

export class EdgeLabelView {
    private readonly root: HTMLDivElement;
    private readonly pool: HTMLSpanElement[] = [];
    private readonly ruler: HTMLSpanElement;
    private readonly layout = new EdgeLabelLayout();
    private picks: EdgeLabelPick[] = [];
    private lineHeight = 16;
    /** Subject-name boxes to avoid, and when they were last read. */
    private reserved: PlacedLabel[] = [];
    private reservedAt = 0;
    private obstacles?: () => PlacedLabel[];

    constructor(
        container: HTMLElement,
        max: number,
        onPick?: (edge: number) => void,
        obstacles?: () => PlacedLabel[],
    ) {
        this.obstacles = obstacles;
        this.root = document.createElement("div");
        this.root.className = "va-edge-labels";
        /* The canvas is already `aria-hidden` and the connections are listed as text in the
           panel beside it. Announcing sixteen fragments that appear and vanish under a moving
           pointer would be noise, and the same information is available in a form that can
           actually be navigated. */
        this.root.setAttribute("aria-hidden", "true");

        for (let i = 0; i < max; i += 1) {
            const span = document.createElement("span");
            span.className = "va-edge-label";
            span.style.opacity = "0";
            if (onPick) {
                /*
                 * The label is the way in.
                 *
                 * A relationship in a 3D scene is a one-pixel line, and asking someone to hit one
                 * is asking them to fail. The word sitting on it is a large, obvious target that
                 * is already the thing they are reading, so clicking it is what opening its
                 * explanation should mean.
                 *
                 * Kept out of the keyboard path deliberately: this layer is `aria-hidden` and
                 * these are not buttons, because sixteen controls appearing and vanishing under
                 * a moving pointer would be a hostile tab order. The same explanations are
                 * reachable from the connections list in the panel, which is ordinary, stable
                 * markup.
                 */
                span.dataset.pickable = "true";
                span.addEventListener("click", () => {
                    // A faded span keeps its last edge in the dataset; clicking through to it
                    // would open an explanation of a relationship that is no longer on screen.
                    if (span.style.opacity !== "1") return;
                    const edge = span.dataset.edge;
                    if (edge !== undefined) onPick(Number(edge));
                });
            }
            this.root.appendChild(span);
            this.pool.push(span);
        }

        this.ruler = document.createElement("span");
        this.ruler.className = MEASURE_CLASS;
        this.root.appendChild(this.ruler);

        container.appendChild(this.root);
    }

    /**
     * Change which connections are named.
     *
     * Called when the hover or the selection moves, not per frame. Resets the layout's memory so
     * a new subject's labels are not judged against the last subject's incumbents.
     */
    setLabels(picks: EdgeLabelPick[]) {
        this.picks = picks;
        this.layout.reset();
        if (picks.length === 0) this.hideFrom(0);
    }

    /** The font changed, so every cached text width is wrong. */
    invalidateMeasurements() {
        this.layout.invalidateMeasurements();
    }

    /**
     * Place this frame's labels.
     *
     * `points` carries one `LABEL_STRIDE` run per pick, in the order `setLabels` was given: a
     * usable flag, then an x and a y for each of `LABEL_FRACTIONS`, in CSS pixels relative to the
     * container. Whoever projected them decides what usable means - behind the camera in the
     * spatial view, nothing in the planar one.
     */
    update(points: Float32Array, viewport: { width: number; height: number }) {
        if (this.picks.length === 0) return;

        const anchors: LabelAnchor[] = [];
        for (let i = 0; i < this.picks.length; i += 1) {
            const base = i * LABEL_STRIDE;
            const candidates: Array<{ x: number; y: number }> = [];
            /* Off-screen is not a collision and must not consume a slot. The projection reports
               depth validity; the viewport test belongs here, where the viewport is known - and
               it is applied per candidate, so a position that has slid off the canvas simply
               takes the next one along the same line rather than losing the label. */
            for (let f = 0; f < LABEL_FRACTIONS.length; f += 1) {
                const x = points[base + 1 + f * 2];
                const y = points[base + 2 + f * 2];
                if (x >= 0 && y >= 0 && x <= viewport.width && y <= viewport.height) {
                    candidates.push({ x, y });
                }
            }
            anchors.push({
                key: this.picks[i].edge,
                candidates,
                text: this.picks[i].text,
                priority: this.picks[i].priority,
                usable: points[base] === 1 && candidates.length > 0,
            });
        }

        /*
         * The subject names move far more slowly than the camera does - they are re-placed on a
         * 160 ms timer, not per frame - so reading their boxes every frame would be paying for a
         * layout flush sixty times a second to learn the same answer. Sampled at roughly their
         * own cadence instead.
         */
        const now = performance.now();
        if (this.obstacles && now - this.reservedAt > 150) {
            this.reserved = this.obstacles();
            this.reservedAt = now;
        }

        const placed = this.layout.place(
            anchors,
            viewport,
            (text) => this.measure(text),
            this.lineHeight,
            this.reserved,
            now,
        );

        placed.forEach((label, i) => {
            const span = this.pool[i];
            if (!span) return;
            if (span.textContent !== label.text) span.textContent = label.text;
            span.dataset.edge = String(label.key);
            // Rounded to whole pixels: subpixel positions make text shimmer as the camera drifts,
            // and a label that shimmers is read as broken rather than as precise.
            span.style.transform = `translate3d(${Math.round(label.x)}px, ${Math.round(label.y)}px, 0)`;
            span.style.opacity = "1";
        });
        this.hideFrom(placed.length);
    }

    private hideFrom(index: number) {
        for (let i = index; i < this.pool.length; i += 1) {
            if (this.pool[i].style.opacity !== "0") this.pool[i].style.opacity = "0";
        }
    }

    /**
     * Text width, in the font the labels are actually set in.
     *
     * A hidden span rather than canvas `measureText`, because the canvas would need the font
     * shorthand rebuilt by hand and would get letter-spacing and font-feature settings wrong.
     * This costs one layout per distinct phrase; the phrase set is the predicate vocabulary,
     * about sixty strings for the whole corpus, and `EdgeLabelLayout` caches by string.
     */
    private measure(text: string): number {
        this.ruler.textContent = text;
        const width = this.ruler.offsetWidth;
        this.lineHeight = this.ruler.offsetHeight || this.lineHeight;
        return width;
    }

    destroy() {
        this.root.remove();
    }
}
