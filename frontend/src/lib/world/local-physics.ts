/**
 * The local simulation, with the axis count as a parameter.
 *
 * ## Why this is a module and not two copies
 *
 * Both renderers need a live layout for a few dozen marks and neither needs a general graph
 * drawing library. `d3-force-3d` and `graphology` are in this project's devDependencies, which
 * is where they belong: `scripts/build-world.mjs` and `scripts/build-constellations.mjs` run
 * them once, offline, over 35,370 nodes. Promoting `d3-force` to a runtime dependency would
 * add an alpha-decay tick schedule that fights the engine's own frame loop, an octree that is
 * pure overhead at forty bodies, and bundle weight on the graph route, in exchange for a
 * sixty-line loop. Phase 7F's arbitration (ARB-7) settled that: extract the tuned loop this
 * project already has, rather than importing a bigger one.
 *
 * So the tuning below is not new. It was measured against a real neighbourhood in the 2D view
 * and is reproduced here unchanged, including the record of what the first attempt cost, so
 * that the 3D binding inherits a model that has already been argued with rather than starting
 * its own argument.
 *
 * ## What is shared and what is not
 *
 * Shared: repulsion, springs, damping, the centre or shell constraint, soft anchors, the
 * degenerate-coincidence nudge, the sleep threshold, and the overlap relaxation. All of it is
 * written over a coordinate count, so nothing in here says "x" or "z".
 *
 * Not shared: where the bodies go in the first place. A plane seats neighbours on rings; a
 * slab seats them in sectors at a clamped elevation. Those are layouts, they live with their
 * renderer, and they disagree for good reasons.
 *
 * ## Storage is flat, and deliberately
 *
 * `pos` is one `Float32Array` of `count * dims`, which is what a `BufferAttribute` wants, so a
 * 3D binding can upload it without a copy. That matters beyond convenience: ARB-7 records that
 * the engine's `buildNodes` passed the artifact's own `positions` array by reference into its
 * attribute, so animating a node would have rewritten the canonical world coordinates and
 * silently moved the pick index, the label projection and the planar view with it. A field
 * owns its own buffer; the artifact is read once, into it.
 */

export type Dims = 2 | 3;

/**
 * The constants, in one record, so a binding declares its model rather than patching it.
 *
 * Every field is a rate per step at `dt = 1`, not per second. The loop is driven by
 * `requestAnimationFrame` and a dropped frame makes the next step no larger, which is the
 * behaviour a reader wants: a simulation that catches up after a stall lurches.
 */
export type Tuning = {
    /**
     * Spring constant on an edge.
     *
     * ## Tuned against a real neighbourhood, not chosen for tidiness
     *
     * Agni has 5,385 connections; a first ring capped at sixty all spring toward the same
     * centre. With the first numbers tried - repulsion 5,200 against a spring constant of
     * 0.035 - a spring stretched a hundred units pulled at 3.5 while repulsion at fifty units
     * apart pushed at 2.1, so the ring collapsed into a knot at the rest radius and the
     * diagram was unreadable. Repulsion has to dominate at the distances bodies actually sit
     * at, and the spring has to be weak enough that it positions rather than compresses.
     */
    spring: number;
    /**
     * Largest extension a spring is allowed to feel, in world units.
     *
     * An edge to a body that has drifted a long way should pull it back steadily, not fling it
     * through everything in between. Unclamped springs were what produced the long straight
     * lines shooting off the first version of the planar view.
     */
    springClamp: number;
    /**
     * Repulsion coefficient, in a law that falls as 1/d rather than 1/d squared.
     *
     * An inverse-square law is what gravity does and it is the wrong shape for laying out a
     * graph: overwhelming at close range and negligible a little further out, so bodies either
     * sit on top of each other or ignore each other entirely and the layout settles into a
     * knot with a few strays flung to the edge - which is what the first version produced.
     * Fruchterman and Reingold's k-squared-over-d falls off slowly enough to keep pushing at
     * the distances bodies actually occupy, which is what spreads a ring evenly.
     */
    repulsion: number;
    /** Multiplier inside the near field, where two marks are about to touch. */
    nearGain: number;
    /** How much clear space between two surfaces counts as the near field, in world units. */
    nearPad: number;
    /** Velocity retained per step. Below 1 by construction, or nothing ever comes to rest. */
    damping: number;
    /** Pull toward the origin, scaled by 60 inside the loop. Zero where `shell` is set. */
    centrePull: number;
    /**
     * Hold bodies at a distance from the origin instead of pulling them into it.
     *
     * ## Why 3D needs this and 2D does not
     *
     * A centre pull in three dimensions collapses the arrangement toward a ball and then
     * toward its middle, and ARB-1 measured what a ball costs once it is projected: a uniform
     * shell puts 59.8% of its points in the outer 36% of the projected disc, and a free orbit
     * over 180x25 viewpoints found a worst-case minimum projected separation of 0.0003 disc
     * radii, with a mean of 10.9 overlapping pairs per random view out of 780. A radial
     * constraint holds the arrangement on a surface, which is where a slab or a cap can keep a
     * separation guarantee; a centre pull flattens it into the thing that has no guarantee.
     *
     * `radius` is in world units and `pull` is a rate per step on the radial error.
     */
    shell: { radius: number; pull: number } | null;
    /**
     * Rate at which an anchored body returns to its anchor.
     *
     * A soft anchor, not a pin: a subject can be dragged off its slot and drifts back. A pin
     * would make the layout authored and dead, and the whole claim of this view is that taking
     * hold of a subject and feeling its neighbours resist is worth more than a tidy picture.
     */
    anchorPull: number;
    /** Below this kinetic energy per body the field is at rest and stops stepping. */
    sleepEnergy: number;
};

/**
 * The 2D constants, as measured. `planar.ts` is a thin binding over these.
 *
 * `tests/unit/planar-physics.test.ts` passes against this record unmodified, which is how this
 * extraction is known not to have changed the model.
 */
export const PLANAR_TUNING: Readonly<Tuning> = {
    spring: 0.012,
    springClamp: 60,
    repulsion: 210,
    nearGain: 2.6,
    nearPad: 8,
    damping: 0.86,
    centrePull: 0.0009,
    shell: null,
    anchorPull: 0.02,
    sleepEnergy: 0.055,
};

/**
 * Repulsion in three dimensions, as a multiple of the planar value.
 *
 * 1.9. The planar number was tuned so that a ring of N neighbours spreads evenly around a
 * circumference, where each body competes with two others. On a surface each body has about
 * six, so the same coefficient leaves a shell visibly clumpier than the ring it was tuned for.
 * The factor is a density ratio rather than a measurement - hexagonal packing seats
 * pi/sqrt(12) = 0.9069 of a surface against a line's 1.0, and the neighbour count doubles - so
 * it is a starting point that puts the 3D binding in the right decade, and it is stated as
 * such. If the slab reads clumpy this is the number to move, and moving it should leave a
 * measurement in this comment.
 */
export const SPATIAL_REPULSION_FACTOR = 1.9;

/**
 * The 3D constants.
 *
 * `centrePull` is zero and the shell carries the constraint instead; see `Tuning.shell`. The
 * radius is ARB-1's worked R = 380 px, at which a 40-body slab has an in-plane minimum
 * separation of 2.03 * R / sqrt(N) = 122 px and a projected separation of at least ~54 px from
 * every viewpoint in a [40, 80] degree elevation band. A binding drawing at another radius
 * must set this, because the guarantee is a function of it.
 */
export const SPATIAL_TUNING: Readonly<Tuning> = {
    ...PLANAR_TUNING,
    repulsion: PLANAR_TUNING.repulsion * SPATIAL_REPULSION_FACTOR,
    centrePull: 0,
    shell: { radius: 380, pull: 0.02 },
};

/** The tuning for a given axis count, with whatever a caller needs to override. */
export function tuningFor(dims: Dims, overrides: Partial<Tuning> = {}): Tuning {
    return { ...(dims === 3 ? SPATIAL_TUNING : PLANAR_TUNING), ...overrides };
}

/**
 * A set of bodies and the springs between them.
 *
 * Structure of arrays rather than an array of structures. Two reasons, and the first is the
 * weaker one: the inner loop is all-pairs, so the coordinates want to be contiguous. The
 * stronger one is that `pos` is then already in the shape a renderer uploads, so no binding
 * has to choose between keeping its own copy and aliasing somebody else's.
 */
export type Field = {
    readonly dims: Dims;
    readonly count: number;
    /** `count * dims` coordinates. Uploadable as a `BufferAttribute` with `itemSize = dims`. */
    pos: Float32Array;
    /** `count * dims` velocities. */
    vel: Float32Array;
    /** Heavier bodies move less when pulled, which reads as "this one is more established". */
    mass: Float32Array;
    /** Drawn radius, in the same units as `pos`. Read by the near field and by the picker. */
    radius: Float32Array;
    /** 1 where a pointer holds the body. A held body ignores forces and is moved directly. */
    held: Uint8Array;
    /**
     * `count * dims` anchor coordinates; `NaN` on any coordinate means the body is free.
     *
     * Every coordinate must be finite for the anchor to apply, which is the condition the
     * planar view has always used. A half-written anchor is a mistake, and honouring it on one
     * axis only would produce a body that slides along a line for no stated reason.
     */
    anchor: Float32Array;
    /** Per-body anchor rate. Seeded from `tuning.anchorPull`. */
    anchorPull: Float32Array;
    /**
     * How far a body may stray from its anchor, in world units. `Infinity` where free.
     *
     * This is what turns a relaxation into a layout with a *provable* separation. A slot
     * layout that only asks the simulation nicely has no floor; with a clamp the floor is
     * `pitch - 2 * slack`, and it holds because the clamp is applied to the position rather
     * than added to the forces. It is skipped while a body is held, because a mark that will
     * not follow the pointer reads as broken - so the guarantee is on the settled arrangement,
     * which is what a reader reads.
     */
    slack: Float32Array;
    /**
     * A stable number per body, used only to break exact coincidence.
     *
     * Two bodies at the same point have no direction to separate along, so one is nudged
     * deterministically rather than left welded forever. The seed is the caller's own
     * identifier - the world node index in both bindings - so the nudge is the same on every
     * run and the same after a rebuild, which a body index would not be.
     */
    seed: Uint32Array;
    readonly edgeCount: number;
    edgeA: Uint32Array;
    edgeB: Uint32Array;
    /** Rest length per edge, in world units. */
    edgeRest: Float32Array;
    tuning: Tuning;
};

export function createField(input: {
    dims: Dims;
    count: number;
    edges: number;
    tuning?: Tuning;
}): Field {
    const { dims, count, edges } = input;
    const tuning = input.tuning ?? tuningFor(dims);
    return {
        dims,
        count,
        pos: new Float32Array(count * dims),
        vel: new Float32Array(count * dims),
        mass: new Float32Array(count).fill(1),
        radius: new Float32Array(count),
        held: new Uint8Array(count),
        anchor: new Float32Array(count * dims).fill(Number.NaN),
        anchorPull: new Float32Array(count).fill(tuning.anchorPull),
        slack: new Float32Array(count).fill(Number.POSITIVE_INFINITY),
        seed: new Uint32Array(count),
        edgeCount: edges,
        edgeA: new Uint32Array(edges),
        edgeB: new Uint32Array(edges),
        edgeRest: new Float32Array(edges),
        tuning,
    };
}

/**
 * The direction two exactly coincident bodies are pushed apart along.
 *
 * Taken from the seed on a different modulus per axis, so two bodies rarely draw the same
 * vector and none draws the zero vector. The first two moduli are the 2D view's own - 7 and 5 -
 * kept so that this extraction leaves the planar binding's behaviour untouched.
 */
function nudge(seed: number, axis: number): number {
    if (axis === 0) return (seed % 7) - 3 || 1;
    if (axis === 1) return (seed % 5) - 2 || 1;
    return (seed % 3) - 1 || 1;
}

/**
 * One step, and the kinetic energy left in the system.
 *
 * Semi-implicit Euler with velocity damping, in three passes in this order: field forces from
 * the current positions, then spring impulses, then integration. The order is not an
 * implementation detail - folding the springs into the first pass makes a body's spring
 * response depend on whether its partner was visited first, which is a layout that changes
 * when the array is reordered.
 *
 * Repulsion is all-pairs, O(n squared), and entirely right here: a curated neighbourhood is
 * forty-odd bodies, so that is under two thousand distance calculations a frame. Measured on
 * the planar view, 0.019 ms per step at n = 24, 0.050 at n = 89 and 0.153 at n = 150. A
 * Barnes-Hut tree would be correct for the whole world and is pure overhead at this size.
 */
export function stepField(field: Field, dt = 1): number {
    const { dims, count, pos, vel, mass, radius, held, anchor, anchorPull, slack, seed, tuning } =
        field;
    const { repulsion, nearGain, nearPad, damping, centrePull, shell, spring, springClamp } =
        tuning;
    const force = new Float64Array(dims);
    const delta = new Float64Array(dims);

    for (let i = 0; i < count; i += 1) {
        if (held[i] === 1) continue;
        const bi = i * dims;
        force.fill(0);

        for (let j = 0; j < count; j += 1) {
            if (j === i) continue;
            const bj = j * dims;
            let d2 = 0;
            for (let d = 0; d < dims; d += 1) {
                delta[d] = pos[bi + d] - pos[bj + d];
                d2 += delta[d] * delta[d];
            }
            if (d2 < 0.01) {
                d2 = 0;
                for (let d = 0; d < dims; d += 1) {
                    delta[d] = nudge(seed[i], d);
                    d2 += delta[d] * delta[d];
                }
            }
            const distance = Math.sqrt(d2);
            const touching = radius[i] + radius[j] + nearPad;
            const magnitude =
                distance < touching ? (repulsion * nearGain) / distance : repulsion / distance;
            for (let d = 0; d < dims; d += 1) force[d] += (delta[d] / distance) * magnitude;
        }

        if (centrePull !== 0) {
            for (let d = 0; d < dims; d += 1) force[d] -= pos[bi + d] * centrePull * 60;
        }

        if (shell) {
            let length = 0;
            for (let d = 0; d < dims; d += 1) length += pos[bi + d] * pos[bi + d];
            length = Math.sqrt(length);
            if (length > 1e-4) {
                const pull = (shell.radius - length) * shell.pull;
                for (let d = 0; d < dims; d += 1) force[d] += (pos[bi + d] / length) * pull;
            }
        }

        let anchored = true;
        for (let d = 0; d < dims; d += 1) {
            if (!Number.isFinite(anchor[bi + d])) anchored = false;
        }
        if (anchored) {
            for (let d = 0; d < dims; d += 1) {
                force[d] += (anchor[bi + d] - pos[bi + d]) * anchorPull[i];
            }
        }

        for (let d = 0; d < dims; d += 1) {
            vel[bi + d] = (vel[bi + d] + (force[d] / mass[i]) * dt) * damping;
        }
    }

    for (let e = 0; e < field.edgeCount; e += 1) {
        const a = field.edgeA[e];
        const b = field.edgeB[e];
        const ba = a * dims;
        const bb = b * dims;
        let d2 = 0;
        for (let d = 0; d < dims; d += 1) {
            delta[d] = pos[bb + d] - pos[ba + d];
            d2 += delta[d] * delta[d];
        }
        const distance = Math.sqrt(d2) || 0.01;
        const extension = distance - field.edgeRest[e];
        const magnitude = Math.max(-springClamp, Math.min(springClamp, extension)) * spring;
        /* Divided by the mass at each end, so pulling a leaf barely moves the hub it hangs
           from and pulling the hub swings the whole neighbourhood. */
        for (let d = 0; d < dims; d += 1) {
            const impulse = (delta[d] / distance) * magnitude;
            if (held[a] !== 1) vel[ba + d] += impulse / mass[a];
            if (held[b] !== 1) vel[bb + d] -= impulse / mass[b];
        }
    }

    let energy = 0;
    for (let i = 0; i < count; i += 1) {
        const bi = i * dims;
        if (held[i] === 1) {
            for (let d = 0; d < dims; d += 1) vel[bi + d] = 0;
            continue;
        }
        for (let d = 0; d < dims; d += 1) pos[bi + d] += vel[bi + d] * dt;
        if (Number.isFinite(slack[i])) clampToSlot(field, i);

        /*
         * Measured after the clamp, and that is not a detail.
         *
         * Energy here means "what will move a body on the next step", so a component a
         * constraint has just removed is not energy in the system. Measured before the clamp
         * it was: every slotted body pressed against its limit re-earned an outward velocity
         * from the forces on every step, so a scene whose marks were provably motionless -
         * drift pinned at exactly the 7 px slack, velocity 0.000 - reported a constant energy
         * of 1.45 at 1440x760 and 17.98 at 390x434 against a sleep threshold of 0.055, and
         * therefore never slept. The canvas then repainted 60 times a second over a still
         * diagram, which is the exact defect this phase set out to remove.
         */
        let speed2 = 0;
        for (let d = 0; d < dims; d += 1) speed2 += vel[bi + d] * vel[bi + d];
        energy += speed2 * mass[i];
    }
    return energy / Math.max(1, count);
}

/**
 * Hold a body inside its slot. See `Field.slack` for why the clamp is positional.
 *
 * ## The velocity loses its normal component, not a fraction of itself
 *
 * The clamp is a constraint surface, and what a constraint removes is the motion *into* it. The
 * first version scaled the whole velocity by a half instead, which is not the same thing and had
 * a measured consequence: a body resting against its clamp re-earned an outward velocity from
 * the forces on every step and kept half of it, so the field's kinetic energy never fell below
 * `sleepEnergy`. Measured live on a throttled 390x844 phone, FOCUS 2D then repainted at **60.3
 * repaints per second at rest** - in the renderer that exists for the devices least able to
 * afford it - while at 1440x836 the same scene settled in a single step and repainted zero times.
 * A defect that appears only at the small band is exactly the one a desktop check misses.
 *
 * Projecting out the outward component leaves the tangential slide intact, which is what keeps a
 * dragged neighbour feeling as though it slides around its ring rather than sticking to it. The
 * normal is taken from the position *before* the clamp, because after it a zero-slack body sits
 * exactly on its anchor and has no direction left to project along - which is the subject, and
 * the subject is the body whose residual energy would keep the whole scene awake.
 */
function clampToSlot(field: Field, i: number): void {
    const { dims, pos, vel, anchor, slack } = field;
    const bi = i * dims;
    let drift2 = 0;
    for (let d = 0; d < dims; d += 1) {
        const to = anchor[bi + d];
        if (!Number.isFinite(to)) return;
        drift2 += (pos[bi + d] - to) * (pos[bi + d] - to);
    }
    const limit = slack[i];
    if (drift2 <= limit * limit) return;

    const drift = Math.sqrt(drift2);
    let outward = 0;
    for (let d = 0; d < dims; d += 1) {
        outward += (vel[bi + d] * (pos[bi + d] - anchor[bi + d])) / drift;
    }
    for (let d = 0; d < dims; d += 1) {
        const to = anchor[bi + d];
        const normal = (pos[bi + d] - to) / drift;
        if (outward > 0) vel[bi + d] -= outward * normal;
        pos[bi + d] = to + normal * limit;
    }
}

export function fieldAtRest(field: Field, energy: number): boolean {
    return energy < field.tuning.sleepEnergy;
}

/** The axis-aligned box containing every body and its radius. */
export function fieldBounds(field: Field): { min: number[]; max: number[] } {
    const { dims, count, pos, radius } = field;
    const min = new Array<number>(dims).fill(Number.POSITIVE_INFINITY);
    const max = new Array<number>(dims).fill(Number.NEGATIVE_INFINITY);
    for (let i = 0; i < count; i += 1) {
        for (let d = 0; d < dims; d += 1) {
            min[d] = Math.min(min[d], pos[i * dims + d] - radius[i]);
            max[d] = Math.max(max[d], pos[i * dims + d] + radius[i]);
        }
    }
    if (!Number.isFinite(min[0])) {
        return { min: new Array(dims).fill(-100), max: new Array(dims).fill(100) };
    }
    return { min, max };
}

/** The closest two surfaces, and the clear space between them. Negative where they overlap. */
export function minSeparation(field: Field): { gap: number; a: number; b: number } {
    const { dims, count, pos, radius } = field;
    let gap = Number.POSITIVE_INFINITY;
    let a = -1;
    let b = -1;
    for (let i = 0; i < count; i += 1) {
        for (let j = i + 1; j < count; j += 1) {
            let d2 = 0;
            for (let d = 0; d < dims; d += 1) {
                const step = pos[i * dims + d] - pos[j * dims + d];
                d2 += step * step;
            }
            const clear = Math.sqrt(d2) - radius[i] - radius[j];
            if (clear < gap) {
                gap = clear;
                a = i;
                b = j;
            }
        }
    }
    return { gap, a, b };
}

/**
 * Push overlapping bodies apart until none overlap, holding the arrangement they started in.
 *
 * ## Why this is not the force field
 *
 * Because a force field has no termination condition a caller can assert. Repulsion against an
 * anchor spring reaches equilibrium at whatever separation the two happen to balance at, and
 * that number is a consequence of the tuning rather than a promise. This is the separation
 * constraint from the graph drawing literature instead: each pass moves every overlapping pair
 * apart by exactly half its overlap, so a pass that finds no overlap *proves* there is none,
 * and the loop stops there.
 *
 * ## Why the anchor is annealed rather than held
 *
 * Measured on this artifact's 33 constellations projected to a plane: at a constant pull the
 * pass never converged - worst overlap stuck between 1.3 and 13.7 px depending on viewport,
 * because every pass re-introduced the overlap the previous one had just removed. Decaying the
 * pull to zero over 120 passes and then separating freely converges within 22 further passes
 * and keeps 93-99% of the original pairwise left-to-right ordering, for 3-5 ms over the whole
 * layout. The arrangement is recognisably the one the offline layout settled, and the
 * separation is a fact rather than a hope.
 */
export function relaxOverlaps(
    field: Field,
    options: { pad?: number; anneal?: number; passes?: number; tolerance?: number } = {},
): { worst: number; passes: number; converged: boolean } {
    const { dims, count, pos, radius, anchor, seed } = field;
    const pad = options.pad ?? field.tuning.nearPad;
    const anneal = options.anneal ?? 120;
    const limit = options.passes ?? 400;
    const tolerance = options.tolerance ?? 0.01;
    const pull = field.tuning.anchorPull * 4;
    const delta = new Float64Array(dims);

    let worst = 0;
    let used = 0;
    for (let k = 0; k < anneal + limit; k += 1) {
        worst = 0;
        for (let i = 0; i < count; i += 1) {
            for (let j = i + 1; j < count; j += 1) {
                let d2 = 0;
                for (let d = 0; d < dims; d += 1) {
                    delta[d] = pos[j * dims + d] - pos[i * dims + d];
                    d2 += delta[d] * delta[d];
                }
                if (d2 < 1e-9) {
                    d2 = 0;
                    for (let d = 0; d < dims; d += 1) {
                        delta[d] = nudge(seed[i] + j, d);
                        d2 += delta[d] * delta[d];
                    }
                }
                const distance = Math.sqrt(d2);
                const overlap = radius[i] + radius[j] + pad - distance;
                if (overlap <= 0) continue;
                if (overlap > worst) worst = overlap;
                const push = overlap / 2;
                for (let d = 0; d < dims; d += 1) {
                    const step = (delta[d] / distance) * push;
                    pos[i * dims + d] -= step;
                    pos[j * dims + d] += step;
                }
            }
        }
        used = k + 1;
        if (k < anneal) {
            const rate = pull * (1 - k / anneal);
            for (let i = 0; i < count; i += 1) {
                for (let d = 0; d < dims; d += 1) {
                    const to = anchor[i * dims + d];
                    if (!Number.isFinite(to)) continue;
                    pos[i * dims + d] += (to - pos[i * dims + d]) * rate;
                }
            }
            continue;
        }
        if (worst <= tolerance) break;
    }
    return { worst, passes: used, converged: worst <= tolerance };
}
