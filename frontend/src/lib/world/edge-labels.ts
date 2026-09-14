import { edgesOf, otherEnd, type World } from "./artifact";
import { describePredicate, edgePredicate, type PredicateTable } from "./predicates";

/**
 * Which connections get named, and where the words go.
 *
 * ## The problem this solves
 *
 * A reader hovers a subject and sees lines. Lines are not knowledge. They have to say what they
 * are - "is ascribed to the seer", "co-occurs with", "is in the metre" - and the moment you try
 * to do that at this scale two things go wrong at once.
 *
 * The first is volume. Indra carries 7,347 edges. Sixteen is roughly what a person can read
 * before a diagram becomes a wall of text, so at least 99.8% of them must go unnamed, and
 * *which* ones survive is the entire design.
 *
 * The second is that the obvious answer to the first is wrong. Ranking by the neighbour's degree
 * - show the most important connections - gives you sixteen labels that all read "is ascribed to
 * the seer", because that is what most of a passage-heavy hub's edges are. The reader learns one
 * fact sixteen times and still does not know that this subject also has metres, epithets and
 * parallels hanging off it.
 *
 * So the rule is coverage before rank: every *distinct kind* of relationship gets named once
 * before any kind is named twice. A hub with eleven predicates spends its first eleven slots
 * showing eleven different words, and only then starts doubling up. That turns the label set
 * from a sample into a summary, and it is the difference between decorating a hover and
 * answering it.
 *
 * ## Renderer-agnostic on purpose
 *
 * Nothing here knows about WebGL, canvas or the DOM. Selection takes an artifact and a node;
 * layout takes points already projected into screen pixels by whoever did the projecting. That
 * is what lets the spatial view, the planar view and the path trace show the same connections
 * with the same words under the same cap - the alternative being three label systems that
 * quietly disagree about what a subject is attached to.
 */

/** One connection chosen to be named. */
export type EdgeLabelPick = {
    /** Index into the world edge arrays - the identity the inspector looks relationships up by. */
    edge: number;
    /** The node at the far end, so the caller can position and the inspector can name it. */
    other: number;
    /** True when the hovered subject is the stored source, which fixes the reading order. */
    outgoing: boolean;
    predicate: string;
    text: string;
    /** Higher is kept. Set by selection; layout only ever compares these, never rebuilds them. */
    priority: number;
};

/**
 * How many labels may be on screen at once.
 *
 * Sixteen is the ceiling on a desktop canvas and eight on a phone, where the same count over a
 * quarter of the area is not a denser diagram but an unreadable one.
 */
export const MAX_EDGE_LABELS = 16;
export const MAX_EDGE_LABELS_COMPACT = 8;

export function edgeLabelBudget(viewportWidth: number): number {
    return viewportWidth < 720 ? MAX_EDGE_LABELS_COMPACT : MAX_EDGE_LABELS;
}

/**
 * Choose which of a subject's connections to name.
 *
 * Two passes over the incident edges. The first groups them by predicate and orders each group
 * by the far node's degree, so that within a kind the most substantial example leads. The second
 * deals the groups out round-robin: one from each kind, then a second from each kind, until the
 * budget is spent.
 *
 * Ordering the groups themselves by rarity - fewest edges first - is deliberate. A subject with
 * 5,000 passage attributions and one exact parallel should show the parallel; it is the
 * surprising fact, and the attributions will still be represented by their own single slot.
 */
export function pickEdgeLabels(
    world: World,
    table: PredicateTable | null,
    node: number,
    limit: number = MAX_EDGE_LABELS,
    /**
     * The connections eligible to be named. Defaults to all of them.
     *
     * The spatial view passes the subset it is actually drawing: its overlay buffer is a fixed
     * size and truncates past it, so a subject with more edges than capacity has some on screen
     * and some not. Naming one that is not drawn puts a phrase beside whichever unrelated line
     * happens to pass under it.
     */
    edges: ArrayLike<number> = edgesOf(world, node),
): EdgeLabelPick[] {
    if (node < 0 || node >= world.manifest.counts.nodes || limit <= 0) return [];

    const byPredicate = new Map<string, EdgeLabelPick[]>();

    for (let i = 0; i < edges.length; i += 1) {
        const edge = edges[i];
        const predicate = edgePredicate(world, edge);
        if (!predicate) continue;
        const other = otherEnd(world, edge, node);
        if (other === node) continue;
        const semantics = describePredicate(table, predicate);
        const group = byPredicate.get(predicate);
        const pick: EdgeLabelPick = {
            edge,
            other,
            outgoing: world.edgePairs[edge * 2] === node,
            predicate,
            text: semantics?.phrase ?? predicate.toLowerCase().replaceAll("_", " "),
            // Filled in below, once the group's position in the deal order is known.
            priority: 0,
        };
        if (group) group.push(pick);
        else byPredicate.set(predicate, [pick]);
    }

    if (byPredicate.size === 0) return [];

    const degree = (pick: EdgeLabelPick) => world.nodeDegree[pick.other] ?? 0;
    const groups = [...byPredicate.entries()]
        .map(([predicate, picks]) => ({
            predicate,
            picks: picks.sort((a, b) => degree(b) - degree(a)),
        }))
        // Rarest kind first, ties broken by name so a rebuild cannot reorder the world.
        .sort((a, b) => a.picks.length - b.picks.length || a.predicate.localeCompare(b.predicate));

    const chosen: EdgeLabelPick[] = [];
    for (let round = 0; chosen.length < limit; round += 1) {
        let dealt = 0;
        for (const group of groups) {
            if (chosen.length >= limit) break;
            const pick = group.picks[round];
            if (!pick) continue;
            /* Priority descends with the order they were dealt in, so the first example of each
               kind outranks the second example of any kind. Layout drops from the bottom, which
               means a crowded canvas loses repetition before it loses coverage. */
            pick.priority = 1 - chosen.length / limit;
            chosen.push(pick);
            dealt += 1;
        }
        if (dealt === 0) break;
    }

    return chosen;
}

/** How many distinct kinds of relationship a subject has, named or not. */
export function countEdgeKinds(world: World, node: number): number {
    const kinds = new Set<string>();
    for (const edge of edgesOf(world, node)) {
        const predicate = edgePredicate(world, edge);
        if (predicate) kinds.add(predicate);
    }
    return kinds.size;
}

/**
 * Where along a connection a label may sit, as fractions from the subject to the far end.
 *
 * Three, tried in this order, and the reason is what a hub looks like. Every edge of a subject
 * radiates from one point, so every *midpoint* sits at a similar small radius from it and the
 * boxes pile into each other: measured on Indra, placing at the midpoint alone put thirteen of
 * sixteen labels in collision and showed three. Further out along the line the edges have fanned
 * apart, so the same sixteen labels have somewhere to go.
 *
 * All three are points on the label's own edge. That is the distinction from nudging: a label
 * moved perpendicular to its line lands on a neighbouring line and starts describing the wrong
 * relationship, while a label slid along its line is still unambiguously about that line.
 */
export const LABEL_FRACTIONS = [0.62, 0.44, 0.8] as const;

/** `usable`, then an x and a y for each fraction. */
export const LABEL_STRIDE = 1 + LABEL_FRACTIONS.length * 2;

/** A chosen label, projected into screen pixels by a renderer. */
export type LabelAnchor = {
    /** Stable across frames. The edge index; identity is what makes hysteresis possible. */
    key: number;
    /** Candidate positions along the edge, best first. */
    candidates: Array<{ x: number; y: number }>;
    text: string;
    priority: number;
    /** False where the renderer knows the point is behind the camera or otherwise unusable. */
    usable: boolean;
};

export type PlacedLabel = {
    key: number;
    text: string;
    /** Top-left of the box, in CSS pixels. */
    x: number;
    y: number;
    width: number;
    height: number;
};

const PADDING_X = 6;
const PADDING_Y = 3;
/** Kept clear of the viewport edge so a label is never half a word. */
const MARGIN = 4;

/**
 * A label that has appeared stays for at least this long.
 *
 * Without it, a label whose box grazes another's flickers on and off at frame rate as the camera
 * drifts, which is worse than never showing it: the eye is drawn to the blinking rather than to
 * the word. Three hundred milliseconds is long enough to read a two-word phrase and short enough
 * that a deliberate camera move still clears the screen promptly.
 */
const HOLD_MS = 300;

/**
 * Screen-space placement, with a memory.
 *
 * Held as an object rather than a pure function because the useful behaviour here is entirely
 * about what happened last frame. Two rules come out of that:
 *
 * - **Incumbency.** A label already on screen is compared with a bonus, so a rival has to be
 *   meaningfully better to take its place rather than a rounding error better. Otherwise two
 *   near-equal labels trade the same slot back and forth forever.
 * - **Dwell.** A label that has just appeared is not removed for `HOLD_MS`, even if it now
 *   collides. It is better to briefly overlap than to blink.
 *
 * Collisions are resolved by dropping, not nudging. A nudged label no longer points at its own
 * edge, and at this cap the reader can simply move the pointer to see the rest - whereas a label
 * silently relocated onto a neighbouring line is a wrong answer rather than a missing one.
 */
export class EdgeLabelLayout {
    private shownAt = new Map<number, number>();
    private widths = new Map<string, number>();

    /** Text measurement is expensive and the phrase set is tiny, so it is cached by string. */
    private measureText(text: string, measure: (text: string) => number): number {
        const known = this.widths.get(text);
        if (known !== undefined) return known;
        const width = measure(text);
        this.widths.set(text, width);
        return width;
    }

    /** Called when the subject changes, so a new selection does not inherit old incumbents. */
    reset(): void {
        this.shownAt.clear();
    }

    /** Called when the font or its size changes, which invalidates every cached width. */
    invalidateMeasurements(): void {
        this.widths.clear();
    }

    /**
     * Decide what is drawn this frame.
     *
     * O(n squared) in the number of labels, which at a cap of sixteen is 120 box comparisons -
     * far below the cost of drawing them, and not worth a spatial index that would have to be
     * rebuilt every frame anyway.
     */
    place(
        anchors: LabelAnchor[],
        viewport: { width: number; height: number },
        measure: (text: string) => number,
        lineHeight: number,
        /**
         * Boxes already occupied by something else on the canvas - the subject names.
         *
         * Those are drawn by a different system entirely (DOM spans in the spatial view, canvas
         * text in the planar one) and neither knew this existed, so a relationship phrase would
         * land squarely on the name of the subject it was describing. Passing them in as
         * pre-placed rectangles makes one collision pass responsible for the whole canvas.
         */
        reserved: PlacedLabel[] = [],
        now: number = performance.now(),
    ): PlacedLabel[] {
        const held = new Set<number>();
        const ranked = anchors
            .filter((anchor) => anchor.usable)
            .map((anchor) => {
                const since = this.shownAt.get(anchor.key);
                const incumbent = since !== undefined;
                if (incumbent && now - since < HOLD_MS) held.add(anchor.key);
                return { anchor, rank: anchor.priority + (incumbent ? 0.15 : 0) };
            })
            .sort((a, b) => b.rank - a.rank);

        const placed: PlacedLabel[] = [];
        const height = lineHeight + PADDING_Y * 2;

        const overlaps = (box: PlacedLabel, against: PlacedLabel[]) =>
            against.some(
                (other) =>
                    box.x < other.x + other.width &&
                    box.x + box.width > other.x &&
                    box.y < other.y + other.height &&
                    box.y + box.height > other.y,
            );

        /*
         * Two standards, in order of how bad the collision is.
         *
         * Another relationship label is a hard conflict: two phrases on top of each other are
         * both unreadable, so one has to go. A subject name is a soft one - the name is still
         * legible under a phrase set in a different face and colour, and losing the phrase
         * entirely is the worse outcome. Treating both as vetoes was measured: on Agni it cut the
         * visible phrases from five to two, because the thirteen names cluster exactly where the
         * edges do.
         *
         * So every candidate is tried against both first, and only if none is clear does it fall
         * back to avoiding the phrases alone.
         */
        const hits = (box: PlacedLabel) => overlaps(box, placed);
        const hitsAnything = (box: PlacedLabel) => hits(box) || overlaps(box, reserved);

        for (const { anchor } of ranked) {
            const width = this.measureText(anchor.text, measure) + PADDING_X * 2;
            let chosen: PlacedLabel | null = null;
            let tolerated: PlacedLabel | null = null;

            for (const candidate of anchor.candidates) {
                // Clamped rather than dropped: a label near the edge of the canvas is still the
                // right answer about the right line, it just has to sit inside the frame.
                const x = Math.min(
                    Math.max(candidate.x - width / 2, MARGIN),
                    Math.max(MARGIN, viewport.width - width - MARGIN),
                );
                const y = Math.min(
                    Math.max(candidate.y - height / 2, MARGIN),
                    Math.max(MARGIN, viewport.height - height - MARGIN),
                );
                const box = { key: anchor.key, text: anchor.text, x, y, width, height };
                if (!hitsAnything(box)) {
                    chosen = box;
                    break;
                }
                // Clear of other phrases but sitting on a name: acceptable if nothing better
                // turns up further along the line.
                if (!tolerated && !hits(box)) tolerated = box;
                // Remembered so a label already on screen keeps a place even when every
                // position it could take is contested; dropping it would make it blink.
                if (!chosen) chosen = box;
            }

            const best = chosen && !hitsAnything(chosen) ? chosen : (tolerated ?? chosen);
            if (!best) continue;
            if (hits(best) && !held.has(anchor.key)) continue;
            placed.push(best);
        }

        const next = new Map<number, number>();
        for (const label of placed) {
            next.set(label.key, this.shownAt.get(label.key) ?? now);
        }
        this.shownAt = next;

        return placed;
    }
}
