/**
 * The World <-> Focus transition, as a clock read rather than a choreography run.
 *
 * ## Two stages, not five
 *
 * The first design for this was a five-phase 1,240 ms sequence: dim, lift, fly, settle, name.
 * Heer and Robertson measured heavy multi-stage animation as *increasing* interpretation error,
 * and recommend "timing each stage around a full second, rather than around a half-second each".
 * Their own note on the five-stage condition is that "most subjects laughed upon first viewing the
 * multi-staged transition." So there are two stages of about a second, and no third.
 *
 *   A. the camera flies, survivors translate to their slab positions, and everything that is not
 *      in the curated set fades out over the first 400 ms.
 *   B. the lines draw in, then the names cross-fade.
 *
 * Translation and expansion beat rotation for comprehension, which is why the survivors move in a
 * straight line to their seats rather than being swung there.
 *
 * ## The two rules this file exists to keep
 *
 * **Object constancy.** Every weight this returns is a function of a *rank* within a stable order,
 * never of a buffer slot. A mark representing one subject must not be reused to depict a different
 * subject across a transition - that is the only thing that answers "where did that node go", and
 * it is why nothing here cross-fades one node into another.
 *
 * **Nothing is placed against moving geometry.** `settled` goes true the instant the geometry
 * stops, which is the end of stage A, and not when the last opacity has finished animating. Label
 * assignment waits on that flag; per-frame transform updates do not. Placement run mid-flight is
 * placement against a position that no longer exists by the time it lands.
 *
 * ## Reduced motion
 *
 * One branch, not a scaled-down copy of the same schedule: an instant camera cut, a short opacity
 * cross-fade, no travel and no stagger. The consequence has to be stated because it is large.
 * Motion parallax is the strongest depth cue a browser can offer - measured at +120% against +60%
 * for stereo - so a reader on reduced motion loses it entirely, and the static cues have to carry
 * depth on their own. That configuration is worth checking separately rather than assumed.
 */

export type TransitionDirection = "in" | "out";

export type TransitionWeights = {
    /** How far survivors have travelled to their slab seats. 0 at the world position, 1 seated. */
    travel: number;
    /** Presence of everything outside the curated set. 1 fully drawn, 0 gone. */
    context: number;
    /** Presence of the curated set's own lines. */
    edges: number;
    /** Presence of names. */
    labels: number;
    /** True while any weight is still moving. */
    running: boolean;
    /**
     * True once the geometry has stopped. The only safe moment to run label assignment.
     *
     * Deliberately earlier than `!running`: the labels are still cross-fading after this, and
     * waiting for them would delay placement by the length of its own fade.
     */
    settled: boolean;
    /** Which stage the clock is in, for a comment in a trace rather than for a branch. */
    stage: "A" | "B" | "rest";
};

/** Stage A: the camera flight and the travel. */
export const STAGE_A_MS = 1000;
/** Stage B: the lines, then the names. */
export const STAGE_B_MS = 1000;
/** How long the context takes to leave, inside stage A. */
export const CONTEXT_FADE_MS = 400;
/** Lines in, at the head of stage B. */
export const EDGE_DRAW_MS = 400;
/** Names, after the lines. Heer and Robertson's 300 ms, and MapLibre's default fade. */
export const LABEL_FADE_MS = 300;
/**
 * Per-item stagger, applied in salience order.
 *
 * A judgement rather than a measurement, and recorded as one. 20 ms across a forty-orb scene is
 * 800 ms of spread, which is inside the stage it belongs to; across two hundred it would not be,
 * so `itemWeight` compresses the stagger rather than letting the stage overrun.
 */
export const STAGGER_MS = 20;
/** The whole thing, so a caller can size a timeout without adding the constants up itself. */
export const TRANSITION_MS = STAGE_A_MS + STAGE_B_MS;
/** Reduced motion: a cross-fade, and no geometry in flight at all. */
export const REDUCED_MS = 130;

/**
 * The material ease, the same curve the stylesheet uses.
 *
 * Solved rather than approximated, because the two halves of this transition run in different
 * places - the camera in the engine, the opacities in the DOM - and an eased value that disagrees
 * with the CSS by a few percent reads as two things moving to slightly different rhythms.
 */
const EASE = { x1: 0.4, y1: 0, x2: 0.2, y2: 1 } as const;

function bezier(t: number, a: number, b: number): number {
    const c = 3 * a;
    const d = 3 * (b - a) - c;
    const e = 1 - c - d;
    return ((e * t + d) * t + c) * t;
}

function bezierSlope(t: number, a: number, b: number): number {
    const c = 3 * a;
    const d = 3 * (b - a) - c;
    const e = 1 - c - d;
    return (3 * e * t + 2 * d) * t + c;
}

/** `cubic-bezier(0.4, 0, 0.2, 1)` evaluated at a progress in [0, 1]. */
export function ease(progress: number): number {
    const t = progress <= 0 ? 0 : progress >= 1 ? 1 : progress;
    if (t === 0 || t === 1) return t;
    /* Newton from the identity guess, which converges in three or four steps on this curve;
       bisection afterwards only for the case where the slope is too flat to divide by. */
    let guess = t;
    for (let i = 0; i < 6; i += 1) {
        const x = bezier(guess, EASE.x1, EASE.x2) - t;
        if (Math.abs(x) < 1e-6) return bezier(guess, EASE.y1, EASE.y2);
        const slope = bezierSlope(guess, EASE.x1, EASE.x2);
        if (Math.abs(slope) < 1e-6) break;
        guess -= x / slope;
    }
    let lo = 0;
    let hi = 1;
    for (let i = 0; i < 24; i += 1) {
        guess = (lo + hi) / 2;
        if (bezier(guess, EASE.x1, EASE.x2) < t) lo = guess;
        else hi = guess;
    }
    return bezier(guess, EASE.y1, EASE.y2);
}

const span = (elapsed: number, from: number, duration: number) =>
    duration <= 0 ? 1 : ease((elapsed - from) / duration);

/**
 * The whole transition as a pure function of the clock.
 *
 * Pure so that it is testable without a renderer and without a frame, and so that reduced motion
 * is one branch at the top rather than a condition threaded through five callbacks. Out is in,
 * played backwards: the arbitration's instruction, and it also means there is only one schedule to
 * keep correct.
 */
export function transitionWeights(
    elapsed: number,
    {
        direction = "in",
        reducedMotion = false,
    }: { direction?: TransitionDirection; reducedMotion?: boolean } = {},
): TransitionWeights {
    if (reducedMotion) {
        const t = REDUCED_MS <= 0 ? 1 : Math.min(1, Math.max(0, elapsed / REDUCED_MS));
        const forward = direction === "in" ? t : 1 - t;
        return {
            /* Seated immediately. A reader who has declined motion has not asked for a slower
               journey, they have asked for no journey. */
            travel: direction === "in" ? 1 : 0,
            context: 1 - forward,
            edges: forward,
            labels: forward,
            running: t < 1,
            settled: true,
            stage: t < 1 ? "A" : "rest",
        };
    }

    const t = Math.max(0, elapsed);
    const reverse = direction === "out";
    /* Backwards means reading the same schedule from the far end, so the stages and the stagger
       need no mirror image of themselves. */
    const clock = reverse ? TRANSITION_MS - t : t;
    const at = Math.min(TRANSITION_MS, Math.max(0, clock));

    const travel = span(at, 0, STAGE_A_MS);
    const context = 1 - span(at, 0, CONTEXT_FADE_MS);
    const edges = span(at, STAGE_A_MS, EDGE_DRAW_MS);
    const labels = span(at, STAGE_A_MS + EDGE_DRAW_MS, LABEL_FADE_MS);

    const running = t < TRANSITION_MS;
    /* Geometry is at rest at the end of stage A in either direction: forward it has arrived, and
       backward it has not started to leave yet. */
    const settled = reverse ? at <= 0 || at >= STAGE_A_MS : at >= STAGE_A_MS;

    return {
        travel: clamp01(travel),
        context: clamp01(context),
        edges: clamp01(edges),
        labels: clamp01(labels),
        running,
        settled,
        stage: at < STAGE_A_MS ? "A" : at < TRANSITION_MS ? "B" : "rest",
    };
}

function clamp01(value: number): number {
    return value <= 0 ? 0 : value >= 1 ? 1 : Number.isFinite(value) ? value : 1;
}

/**
 * One item's share of a weight, staggered by its rank.
 *
 * `rank` is a position in the caller's salience order and `count` is how many there are. Keyed on
 * the order rather than on an array slot, so re-sorting a buffer cannot make two subjects swap
 * their moment.
 *
 * The stagger is compressed rather than allowed to overrun: 20 ms over the forty-orb budget is
 * 780 ms, which fits inside a stage, and over the two-hundred expansion ceiling it would be four
 * seconds, which does not. `window` caps the total spread at half the stage.
 */
export function itemWeight(
    weight: number,
    rank: number,
    count: number,
    { stage = STAGE_A_MS, stagger = STAGGER_MS }: { stage?: number; stagger?: number } = {},
): number {
    if (count <= 1 || weight <= 0) return clamp01(weight);
    if (weight >= 1) return 1;
    const window = Math.min(stagger * (count - 1), stage / 2);
    const spread = window / stage;
    if (spread <= 0) return clamp01(weight);
    const offset = (rank / (count - 1)) * spread;
    /* Each item runs the same curve over the remaining fraction of the stage, so the last one
       still finishes exactly with the stage rather than after it. */
    return clamp01((weight - offset) / (1 - spread));
}
