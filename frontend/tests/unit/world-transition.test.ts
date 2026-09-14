import { describe, expect, it } from "vitest";
import {
    CONTEXT_FADE_MS,
    EDGE_DRAW_MS,
    LABEL_FADE_MS,
    REDUCED_MS,
    STAGE_A_MS,
    STAGE_B_MS,
    STAGGER_MS,
    TRANSITION_MS,
    ease,
    itemWeight,
    transitionWeights,
} from "@/lib/world/transition";

/**
 * The World <-> Focus schedule.
 *
 * Testable at all because it is a pure function of the clock rather than a set of callbacks, and
 * worth testing because two of its properties are contracts that other files depend on and that
 * would regress silently:
 *
 *  - `settled` is the flag label placement waits on. Placement against moving geometry lands text
 *    at a position that no longer exists, and nothing in the rendered result says so.
 *  - every weight is a function of a *rank* in a stable order and never of an array slot, which
 *    is the only thing that answers "where did that node go" across a transition.
 */

describe("two stages, of about a second each", () => {
    it("is two stages and not five", () => {
        expect(STAGE_A_MS).toBe(1000);
        expect(STAGE_B_MS).toBe(1000);
        expect(TRANSITION_MS).toBe(STAGE_A_MS + STAGE_B_MS);
        /* Each sub-step is inside the stage that owns it, so there is no third stage hiding in
           the arithmetic. */
        expect(CONTEXT_FADE_MS).toBeLessThanOrEqual(STAGE_A_MS);
        expect(EDGE_DRAW_MS + LABEL_FADE_MS).toBeLessThanOrEqual(STAGE_B_MS);
    });

    it("moves geometry in stage A and nothing else", () => {
        const early = transitionWeights(1);
        expect(early.stage).toBe("A");
        expect(early.travel).toBeLessThan(0.1);
        expect(early.context).toBeGreaterThan(0.9);
        /* Lines and names have not begun. Drawing them against geometry in flight is the defect
           the two-stage split exists to prevent. */
        expect(early.edges).toBe(0);
        expect(early.labels).toBe(0);
    });

    it("takes the context out early, inside stage A", () => {
        expect(transitionWeights(CONTEXT_FADE_MS).context).toBe(0);
        expect(transitionWeights(CONTEXT_FADE_MS / 2).context).toBeGreaterThan(0);
        /* Still travelling when the context has gone: the survivors are visibly the survivors. */
        expect(transitionWeights(CONTEXT_FADE_MS).travel).toBeLessThan(1);
    });

    it("draws the lines, then the names", () => {
        const lines = transitionWeights(STAGE_A_MS + EDGE_DRAW_MS);
        expect(lines.edges).toBe(1);
        expect(lines.labels).toBe(0);
        const names = transitionWeights(STAGE_A_MS + EDGE_DRAW_MS + LABEL_FADE_MS);
        expect(names.labels).toBe(1);
    });

    it("comes to rest, and stays there", () => {
        const done = transitionWeights(TRANSITION_MS + 1);
        expect(done.running).toBe(false);
        expect(done.travel).toBe(1);
        expect(done.context).toBe(0);
        expect(done.edges).toBe(1);
        expect(done.labels).toBe(1);
        expect(done.stage).toBe("rest");
        /* Far past the end is the same answer. A clock read long after a backgrounded tab wakes
           up must not restart anything. */
        expect(transitionWeights(TRANSITION_MS * 40)).toEqual(done);
    });
});

describe("settled is earlier than finished, deliberately", () => {
    it("goes true when the geometry stops, not when the last fade does", () => {
        expect(transitionWeights(STAGE_A_MS - 1).settled).toBe(false);
        expect(transitionWeights(STAGE_A_MS).settled).toBe(true);
        /* Still running - the names are crossfading - but placement may proceed. Waiting for
           `!running` would delay every label by the length of its own fade. */
        expect(transitionWeights(STAGE_A_MS).running).toBe(true);
    });

    it("is true throughout the reduced-motion branch, because nothing moves in it", () => {
        for (const elapsed of [0, REDUCED_MS / 2, REDUCED_MS, REDUCED_MS * 10]) {
            expect(transitionWeights(elapsed, { reducedMotion: true }).settled).toBe(true);
        }
    });
});

describe("played backwards for focus -> world", () => {
    it("starts where forward ends and ends where forward starts", () => {
        const out = transitionWeights(0, { direction: "out" });
        expect(out.travel).toBe(1);
        expect(out.context).toBe(0);
        const done = transitionWeights(TRANSITION_MS, { direction: "out" });
        expect(done.travel).toBe(0);
        expect(done.context).toBe(1);
        expect(done.running).toBe(false);
    });

    it("reads the same schedule from the far end rather than a mirror of it", () => {
        /* One schedule, so there is only one thing to keep correct. */
        for (const at of [0, 250, 600, 1000, 1400, 2000]) {
            const forward = transitionWeights(TRANSITION_MS - at);
            const backward = transitionWeights(at, { direction: "out" });
            expect(backward.travel).toBeCloseTo(forward.travel, 9);
            expect(backward.context).toBeCloseTo(forward.context, 9);
        }
    });

    it("holds the geometry still at both ends of the reverse", () => {
        expect(transitionWeights(0, { direction: "out" }).settled).toBe(true);
        expect(transitionWeights(TRANSITION_MS, { direction: "out" }).settled).toBe(true);
        /* And not in the middle of it, which is where placement would be wrong. */
        expect(transitionWeights(STAGE_A_MS + 500, { direction: "out" }).settled).toBe(false);
    });
});

describe("reduced motion is one branch, not a slower copy", () => {
    it("cuts the camera and seats everything at once", () => {
        const at = transitionWeights(0, { reducedMotion: true });
        /* No travel at all. A reader who declined motion has not asked for a slower journey. */
        expect(at.travel).toBe(1);
        expect(transitionWeights(0, { reducedMotion: true, direction: "out" }).travel).toBe(0);
    });

    it("crossfades in 120-150 ms and then stops", () => {
        expect(REDUCED_MS).toBeGreaterThanOrEqual(120);
        expect(REDUCED_MS).toBeLessThanOrEqual(150);
        expect(transitionWeights(REDUCED_MS / 2, { reducedMotion: true }).running).toBe(true);
        expect(transitionWeights(REDUCED_MS, { reducedMotion: true }).running).toBe(false);
        const done = transitionWeights(REDUCED_MS, { reducedMotion: true });
        expect(done.context).toBe(0);
        expect(done.edges).toBe(1);
        expect(done.labels).toBe(1);
    });
});

describe("the stagger is keyed on rank, never on a slot", () => {
    it("runs earlier ranks first and finishes them all inside the stage", () => {
        const count = 40;
        const mid = itemWeight(0.5, 0, count);
        const late = itemWeight(0.5, count - 1, count);
        expect(mid).toBeGreaterThan(late);
        /* Every item is complete when the stage is, rather than the last one overrunning it. */
        for (let rank = 0; rank < count; rank += 1) {
            expect(itemWeight(1, rank, count)).toBe(1);
            expect(itemWeight(0, rank, count)).toBe(0);
        }
    });

    it("compresses rather than overruns at the expansion ceiling", () => {
        /* 20 ms across 200 items would be four seconds, which is twice the whole transition. The
           window is capped at half the stage instead. */
        expect(STAGGER_MS).toBe(20);
        for (const count of [6, 40, 200]) {
            expect(itemWeight(1, count - 1, count)).toBe(1);
            expect(itemWeight(0.999, 0, count)).toBeGreaterThan(0.9);
        }
    });

    it("gives a single item the ungarnished weight", () => {
        expect(itemWeight(0.37, 0, 1)).toBeCloseTo(0.37, 9);
        expect(itemWeight(0.37, 0, 0)).toBeCloseTo(0.37, 9);
    });

    it("never leaves a weight outside 0..1, whatever it is handed", () => {
        for (const weight of [-1, 0, 0.5, 1, 2, Number.NaN]) {
            for (const [rank, count] of [
                [0, 1],
                [0, 40],
                [39, 40],
            ]) {
                const value = itemWeight(weight, rank, count);
                expect(value).toBeGreaterThanOrEqual(0);
                expect(value).toBeLessThanOrEqual(1);
            }
        }
    });
});

describe("the ease is the stylesheet's curve", () => {
    it("is pinned at both ends and monotonic between them", () => {
        expect(ease(0)).toBe(0);
        expect(ease(1)).toBe(1);
        expect(ease(-5)).toBe(0);
        expect(ease(5)).toBe(1);
        let previous = -1;
        for (let t = 0; t <= 1.0001; t += 0.02) {
            const value = ease(t);
            expect(value).toBeGreaterThanOrEqual(previous - 1e-9);
            previous = value;
        }
    });

    it("solves cubic-bezier(0.4, 0, 0.2, 1) rather than approximating it", () => {
        /*
         * Solved rather than eyeballed because the two halves of this transition run in different
         * places - the camera in the engine, the opacities in the DOM - and a curve that
         * disagrees with the CSS by a few per cent reads as two things moving to slightly
         * different rhythms.
         *
         * The reference values were cross-checked against a 200-step bisection of the same curve
         * written independently, rather than taken from memory. The first set written here *was*
         * from memory and was wrong by 0.20 at a quarter of the way through, which is the reason
         * this note exists.
         */
        expect(ease(0.25)).toBeCloseTo(0.236587, 5);
        expect(ease(0.5)).toBeCloseTo(0.775561, 5);
        expect(ease(0.75)).toBeCloseTo(0.959368, 5);
        /* Slow to leave and quick through the middle: behind the clock at a quarter of the way
           and well ahead of it by two fifths. That shape is why a camera flight on this curve
           does not appear to start with a jerk. */
        expect(ease(0.25)).toBeLessThan(0.25);
        expect(ease(0.4)).toBeGreaterThan(0.6);
    });
});
