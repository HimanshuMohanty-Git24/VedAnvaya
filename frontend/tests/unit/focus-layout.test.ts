import { describe, expect, it } from "vitest";
import {
    SEPARATION_FLOOR,
    SLAB_ELEVATION,
    SLAB_RADIUS_MAX,
    layoutFocusSlab,
    measureSlabPlan,
    slabRadiusFor,
    slabSeparationBound,
    slabSeparation,
    slabSpreadGain,
    type FocusSlab,
    type SlabMember,
} from "@/lib/world/focus-layout";

/**
 * The slab's separation guarantee, asserted rather than believed.
 *
 * ## Why this file is the deliverable and not a formality
 *
 * The design this replaced was a family-sectored sunflower over spherical shells, justified by
 * the claim that a 3D relaxation is orbit-invariant - good from the arrival pose, therefore good
 * from any pose. The claim is false for any two distinct points, because
 *
 *     sep(v) = |d| * sin(angle between d and v)
 *
 * and a view direction along `d` sets it to zero. Measured on that design: 40 nodes swept over
 * 180x25 viewpoints gave a worst-case minimum projected separation of 0.0003 disc radii and a
 * mean of 10.9 overlapping pairs per random view out of 780.
 *
 * The slab is only better if a sweep says so, and its whole claim is a bound that holds over a
 * *clamped* band rather than a free orbit:
 *
 *     sep >= s * sin(theta_min - arctan(2H / s))
 *
 * So every test here sweeps 360 azimuths across the whole elevation band and asserts every pair
 * at every pose. A separation measured at one pose is the defect this exists to prevent, and a
 * test that checked one pose would have passed on the shell too.
 */

const AZIMUTHS = 360;
const ELEVATIONS = 25;

/**
 * The worst projected separation over the reachable camera poses, and where it happened.
 *
 * Orthographic, which is the same projection the bound is stated in. The camera's real lens is
 * perspective and is checked separately; mixing the two here would test two things and prove
 * neither.
 *
 * ## Why this projects all the points and then compares, rather than calling `slabSeparation`
 *
 * Because the obvious loop is twenty times too slow to be a unit test, and the first version of
 * this file was: `slabSeparation` takes a pose, so it recomputes four trigonometric functions per
 * *pair*, and at the expansion ceiling that is 1,275 pairs x 9,000 poses x two projections - 23
 * million projections and about 92 million trig calls. Measured at 5.1 to 6.5 s, which overran
 * vitest's 5,000 ms default and reported as a timeout rather than as a slow test.
 *
 * The pose's basis is the same for every point in it, so it is computed once per pose and the 51
 * points are projected against it; the pairs are then plain subtraction. Same 9,000 poses, same
 * every-pair coverage, about 12 million cheap operations instead. `slabSeparation` is still
 * exercised below, against this, so the fast path cannot drift from the documented one.
 */
function sweep(slab: FocusSlab) {
    /* The hub counts. A neighbour drawn on top of the subject is the worst case of all, and an
       earlier version of the measurement omitted the one point that is always there. */
    const points = [
        { x: 0, y: 0, z: 0 },
        ...slab.placements.map((placement) => ({
            x: placement.x,
            y: placement.y,
            z: placement.z,
        })),
    ];
    const count = points.length;
    const screenX = new Float64Array(count);
    const screenY = new Float64Array(count);
    let worst = Number.POSITIVE_INFINITY;
    let pose = { azimuth: 0, elevation: 0 };
    let poses = 0;
    for (let a = 0; a < AZIMUTHS; a += 1) {
        const azimuth = ((a / AZIMUTHS) * 360 * Math.PI) / 180;
        const sinAzimuth = Math.sin(azimuth);
        const cosAzimuth = Math.cos(azimuth);
        for (let e = 0; e < ELEVATIONS; e += 1) {
            const elevation =
                SLAB_ELEVATION.min +
                ((SLAB_ELEVATION.max - SLAB_ELEVATION.min) * e) / (ELEVATIONS - 1);
            const radians = (elevation * Math.PI) / 180;
            const sinElevation = Math.sin(radians);
            const cosElevation = Math.cos(radians);
            poses += 1;
            /* The same basis `projectSlab` builds: in-plane (x, y) maps to world (x, z) and the
               slab offset to world y, screen right is perpendicular to the azimuth, screen up is
               the view direction turned a quarter turn in the vertical plane. */
            for (let i = 0; i < count; i += 1) {
                const wx = points[i].x;
                const wy = points[i].z;
                const wz = points[i].y;
                screenX[i] = wx * -sinAzimuth + wz * cosAzimuth;
                screenY[i] =
                    wx * -sinElevation * cosAzimuth +
                    wy * cosElevation +
                    wz * -sinElevation * sinAzimuth;
            }
            for (let i = 0; i < count; i += 1) {
                for (let j = i + 1; j < count; j += 1) {
                    const dx = screenX[i] - screenX[j];
                    const dy = screenY[i] - screenY[j];
                    const separation = Math.sqrt(dx * dx + dy * dy);
                    if (separation < worst) {
                        worst = separation;
                        pose = { azimuth: (azimuth * 180) / Math.PI, elevation };
                    }
                }
            }
        }
    }
    return { worst, pose, poses, pairs: (count * (count - 1)) / 2 };
}

/** Family sizes that add up to `count`, spread over `families` of them. */
function members(count: number, families: number): SlabMember[] {
    const out: SlabMember[] = [];
    for (let i = 0; i < count; i += 1) {
        /* Round-robin rather than blocked, so the salience order interleaves the families and the
           sectoring has to do real work. A blocked order would let a wedge be filled by a
           contiguous run, which is the easy case. */
        out.push({ node: 1000 + i, family: i % families });
    }
    return out;
}

const CASES: Array<{ label: string; count: number; families: number }> = [
    { label: "1 neighbour", count: 1, families: 1 },
    { label: "3", count: 3, families: 2 },
    /* The median node in the artifact has six distinct neighbours, so this is the typical scene
       and not a corner case: p50 = 6, p75 = 8, p90 = 12, and at budget 40 the curation truncates
       only 377 of 34,373 connected nodes. */
    { label: "6 - the median subject", count: 6, families: 3 },
    { label: "8 - p75", count: 8, families: 3 },
    { label: "12 - p90", count: 12, families: 4 },
    { label: "16 - the compact budget", count: 16, families: 5 },
    { label: "24", count: 24, families: 6 },
    { label: "40 - the desktop budget", count: 40, families: 7 },
    { label: "43 - p99", count: 43, families: 7 },
    { label: "50", count: 50, families: 7 },
    { label: "40 in one family", count: 40, families: 1 },
    { label: "40 across all thirteen families", count: 40, families: 13 },
    { label: "200 - the expansion ceiling", count: 200, families: 7 },
];

describe("the slab's separation bound holds from every reachable pose", () => {
    for (const { label, count, families } of CASES) {
        it(`${label}: swept over ${AZIMUTHS} azimuths x the elevation band`, () => {
            const slab = layoutFocusSlab(1, members(count, families), {
                radius: SLAB_RADIUS_MAX,
            });
            expect(slab.placements).toHaveLength(count);
            const measured = sweep(slab);
            expect(measured.poses).toBe(AZIMUTHS * ELEVATIONS);
            /*
             * The bound, at every pose, for every pair. Not the mean and not the arrival pose.
             *
             * A small tolerance because the bound is computed from the same floating-point pitch
             * the construction used, so an exactly-tight pair can land a few parts in a billion
             * under it. One pixel would hide a real regression; 1e-6 px cannot.
             */
            expect(measured.worst).toBeGreaterThanOrEqual(slab.separationBound - 1e-6);
        });
    }
});

describe("the bound is worth having, not merely true", () => {
    it("clears the two-orb floor at every budget the product actually uses", () => {
        /*
         * 1 to 43 covers the compact budget of 16, the desktop budget of 40 and p99 of 43, which
         * is every count the product reaches unless a reader asks for more. A bound that held at
         * 0.3 px would satisfy the sweep above and be useless, so this is what makes the sweep
         * worth running.
         */
        for (let count = 1; count <= 43; count += 1) {
            const slab = layoutFocusSlab(1, members(count, 3), { radius: SLAB_RADIUS_MAX });
            expect(slab.separationBound).toBeGreaterThanOrEqual(SEPARATION_FLOOR);
        }
    });

    it("keeps two orbs from touching well past the floor, and says where it gives out", () => {
        /*
         * Above p99 the floor of 1.6 orb diameters stops being reachable, and the layout says so
         * by returning the strongest guarantee it has rather than by failing. What must still
         * hold is the weaker and harder claim: two orbs never touch. 22 px is the drawn diameter
         * of a neighbour orb at the Focus clamp.
         *
         * Where it gives out is a fact about the design, pinned here so a change to it is
         * visible: 44 to 64 orbs stay clear of the orb diameter and the 200 of the expansion
         * ceiling does not. That is the honest reading of that ceiling.
         */
        const ORB_DIAMETER = 22;
        for (const count of [44, 48, 50, 56, 64]) {
            const slab = layoutFocusSlab(1, members(count, 5), { radius: SLAB_RADIUS_MAX });
            expect(slab.separationBound).toBeGreaterThan(ORB_DIAMETER);
        }
        expect(
            layoutFocusSlab(1, members(200, 7), { radius: SLAB_RADIUS_MAX }).separationBound,
        ).toBeLessThan(ORB_DIAMETER);
    });

    it("is generous at the median and still legible at the ceiling", () => {
        const six = layoutFocusSlab(1, members(6, 3), { radius: SLAB_RADIUS_MAX });
        const forty = layoutFocusSlab(1, members(40, 7), { radius: SLAB_RADIUS_MAX });
        /* Six orbs get most of the disc, which is the "feels like a place" quality arriving free
           for nine subjects in ten rather than being designed for forty and inherited badly. */
        expect(six.separationBound).toBeGreaterThan(120);
        expect(forty.separationBound).toBeGreaterThan(36);
        expect(six.separationBound).toBeGreaterThan(forty.separationBound);
    });

    it("still places every member at the expansion ceiling, floor or no floor", () => {
        const ceiling = layoutFocusSlab(1, members(200, 7), { radius: SLAB_RADIUS_MAX });
        expect(ceiling.separationBound).toBeLessThan(SEPARATION_FLOOR);
        expect(ceiling.separationBound).toBeGreaterThan(15);
        expect(ceiling.placements).toHaveLength(200);
    });
});

describe("the bound also survives the lens the camera actually uses", () => {
    /**
     * The bound is an orthographic statement and the renderer is perspective, so the two have to
     * be reconciled rather than assumed compatible.
     *
     * Perspective is not uniformly safer: the further of two nodes projects smaller and drifts
     * toward the vanishing point, which can shrink a pair's separation as well as stretch it. The
     * error scales with the ratio of the slab's radius to the camera distance, which is fixed by
     * the field of view alone once the slab has to fill the frame - 0.44 at 52 degrees and 0.28
     * at 34, which is why Focus narrows the lens. This asserts what that leaves.
     */
    const FOCUS_FOV = 34;
    const CANVAS_HEIGHT = 836;
    const DISTANCE = 900;

    function perspectiveSweep(slab: FocusSlab) {
        const perUnit =
            CANVAS_HEIGHT / (2 * Math.tan((FOCUS_FOV * Math.PI) / 360) * DISTANCE);
        const scale = 1 / perUnit;
        const points = [
            { x: 0, y: 0, z: 0 },
            ...slab.placements.map((p) => ({ x: p.x, y: p.y, z: p.z })),
        ];
        const half = Math.tan((FOCUS_FOV * Math.PI) / 360);
        let worst = Number.POSITIVE_INFINITY;
        for (let a = 0; a < AZIMUTHS; a += 1) {
            const azimuth = ((a / AZIMUTHS) * 360 * Math.PI) / 180;
            for (let e = 0; e < ELEVATIONS; e += 1) {
                const elevation =
                    ((SLAB_ELEVATION.min +
                        ((SLAB_ELEVATION.max - SLAB_ELEVATION.min) * e) / (ELEVATIONS - 1)) *
                        Math.PI) /
                    180;
                /* The camera sits on the band at the framing distance, looking at the hub - the
                   same pose `flyToSlab` produces, swept. */
                const eye = {
                    x: Math.cos(elevation) * Math.cos(azimuth) * DISTANCE,
                    y: Math.sin(elevation) * DISTANCE,
                    z: Math.cos(elevation) * Math.sin(azimuth) * DISTANCE,
                };
                const forward = {
                    x: -eye.x / DISTANCE,
                    y: -eye.y / DISTANCE,
                    z: -eye.z / DISTANCE,
                };
                const right = { x: -Math.sin(azimuth), y: 0, z: Math.cos(azimuth) };
                const up = {
                    x: forward.y * right.z - forward.z * right.y,
                    y: forward.z * right.x - forward.x * right.z,
                    z: forward.x * right.y - forward.y * right.x,
                };
                const screen = points.map((point) => {
                    /* In-plane (x, y) becomes world (x, z) and the slab offset becomes world y,
                       which is the mapping `composeFocus` applies. */
                    const w = {
                        x: point.x * scale - eye.x,
                        y: point.z * scale - eye.y,
                        z: point.y * scale - eye.z,
                    };
                    const depth = w.x * forward.x + w.y * forward.y + w.z * forward.z;
                    const sx = w.x * right.x + w.y * right.y + w.z * right.z;
                    const sy = w.x * up.x + w.y * up.y + w.z * up.z;
                    const k = CANVAS_HEIGHT / (2 * half * Math.max(depth, 1));
                    return { x: sx * k, y: sy * k };
                });
                for (let i = 0; i < screen.length; i += 1) {
                    for (let j = i + 1; j < screen.length; j += 1) {
                        worst = Math.min(
                            worst,
                            Math.hypot(screen[i].x - screen[j].x, screen[i].y - screen[j].y),
                        );
                    }
                }
            }
        }
        return worst;
    }

    for (const count of [6, 16, 40]) {
        it(`${count} orbs stay apart under the real lens, and by how much`, () => {
            const slab = layoutFocusSlab(1, members(count, 3), { radius: SLAB_RADIUS_MAX });
            const worst = perspectiveSweep(slab);
            /*
             * Two figures, and the weaker one is the one that must never fail.
             *
             * Perspective costs a measured **12.5%** of the proven orthographic bound at the
             * worst count - 38.70 px falls to 33.87 - so the bound is not a pixel guarantee on
             * screen and saying it is would be the same overclaim the shell was retired for.
             * What does hold on screen is that two orbs never touch: 33.87 px against a 22 px
             * drawn orb.
             *
             * 0.85 rather than 0.875 leaves the measurement a little room without letting a real
             * regression through; anything that cost a quarter of the bound would be a change to
             * the lens or to the disc's share of the frame, both of which should fail loudly.
             */
            const ORB_DIAMETER = 22;
            expect(worst).toBeGreaterThan(ORB_DIAMETER);
            expect(worst).toBeGreaterThan(slab.separationBound * 0.85);
        });
    }
});

describe("the plan", () => {
    it("keeps every node at least the guaranteed pitch from every other, and from the hub", () => {
        for (const count of [6, 16, 24, 40, 50]) {
            const slab = layoutFocusSlab(1, members(count, 4), { radius: SLAB_RADIUS_MAX });
            const measured = measureSlabPlan(slab);
            expect(measured.minNode).toBeGreaterThanOrEqual(slab.spacing - 1e-6);
        }
    });

    it("leaves a spoke as much room as a node, while one ring is enough", () => {
        /*
         * The reason the layout minimises rings rather than maximising pitch: edge-node overlap
         * is measured as mattering more to readers than node-node overlap.
         *
         * On one ring the only spokes that pass a node at all are its immediate neighbours', and
         * those leave at a whole angular division, so the clearance is a fraction of the pitch
         * that rises towards 1 as the ring fills. The first version of this test asserted
         * infinity, on the reasoning that equal radii mean no spoke can pass. That is wrong, and
         * wrong in an instructive direction: a neighbour's spoke does have a perpendicular foot
         * on it whenever the two are less than a quarter turn apart, which is every ring of five
         * seats or more.
         */
        for (const count of [6, 8, 12, 16, 24]) {
            const slab = layoutFocusSlab(1, members(count, 3), { radius: SLAB_RADIUS_MAX });
            expect(slab.rings).toHaveLength(1);
            expect(slab.spokeClearance).toBeGreaterThan(slab.spacing * 0.86);
        }
        /* Three seats are 120 degrees apart, so there is genuinely no spoke to be near. */
        expect(
            layoutFocusSlab(1, members(3, 2), { radius: SLAB_RADIUS_MAX }).spokeClearance,
        ).toBe(Number.POSITIVE_INFINITY);
    });

    it("keeps a spoke clear of a node above one ring too, which a free fill could not", () => {
        /*
         * The whole point of the shared angular grid. The searched free-fill construction reached
         * 1.1 px here at forty orbs and 0.2 px at two hundred - a node sitting on a spoke - and no
         * offset could improve it, because coprime ring counts admit angles dense to a third of a
         * degree. These are the measured results of replacing the search with the grid.
         */
        const at = (count: number) =>
            layoutFocusSlab(1, members(count, 6), { radius: SLAB_RADIUS_MAX });
        expect(at(40).spokeClearance).toBeGreaterThan(40);
        expect(at(50).spokeClearance).toBeGreaterThan(24);
        expect(at(200).spokeClearance).toBeGreaterThan(6);
    });

    it("computes the clearance in closed form, and the measurement agrees exactly", () => {
        /*
         * The construction states the clearance rather than searching for it, so the measurement
         * checks the construction rather than substituting for it. They have to agree; a
         * discrepancy means the grid has been broken somewhere between the plan and the seats,
         * which is precisely the defect a partly filled outermost ring invites.
         */
        for (const count of [6, 16, 24, 32, 40, 43, 50, 64, 200]) {
            const slab = layoutFocusSlab(1, members(count, 5), { radius: SLAB_RADIUS_MAX });
            const measured = measureSlabPlan(slab);
            if (slab.spokeClearance === Number.POSITIVE_INFINITY) {
                expect(measured.minSpoke).toBe(Number.POSITIVE_INFINITY);
                continue;
            }
            expect(measured.minSpoke).toBeCloseTo(slab.spokeClearance, 6);
        }
    });

    it("stays inside the disc and clear of the hub", () => {
        const slab = layoutFocusSlab(1, members(40, 7), { radius: SLAB_RADIUS_MAX });
        for (const placement of slab.placements) {
            const r = Math.hypot(placement.x, placement.y);
            expect(r).toBeLessThanOrEqual(SLAB_RADIUS_MAX + 1e-6);
            expect(r).toBeGreaterThanOrEqual(slab.spacing - 1e-6);
            expect(Math.abs(placement.z)).toBeLessThanOrEqual(slab.halfThickness + 1e-6);
        }
    });

    it("is deterministic, so a re-render cannot reseat anything", () => {
        const once = layoutFocusSlab(1, members(40, 7), { radius: SLAB_RADIUS_MAX });
        const twice = layoutFocusSlab(1, members(40, 7), { radius: SLAB_RADIUS_MAX });
        expect(twice.placements).toEqual(once.placements);
    });

    it("returns placements in the caller's salience order, which is the transition's key", () => {
        const input = members(24, 5);
        const slab = layoutFocusSlab(1, input, { radius: SLAB_RADIUS_MAX });
        expect(slab.placements.map((placement) => placement.node)).toEqual(
            input.map((member) => member.node),
        );
        expect(slab.placements.map((placement) => placement.rank)).toEqual(
            input.map((_, index) => index),
        );
    });

    it("lifts the most salient toward the camera, monotonically", () => {
        const slab = layoutFocusSlab(1, members(12, 3), { radius: SLAB_RADIUS_MAX });
        const offsets = slab.placements.map((placement) => placement.z);
        expect(offsets[0]).toBeCloseTo(slab.halfThickness, 6);
        expect(offsets[offsets.length - 1]).toBeCloseTo(-slab.halfThickness, 6);
        for (let i = 1; i < offsets.length; i += 1) {
            expect(offsets[i]).toBeLessThan(offsets[i - 1]);
        }
    });

    it("sectors families as an angular partition, borrowing rarely and saying so", () => {
        const slab = layoutFocusSlab(1, members(40, 7), { radius: SLAB_RADIUS_MAX });
        /* Wedges are sized in proportion to membership, so a shortfall is a rounding event. More
           than a fifth of the scene misplaced would mean the partition is not one. */
        expect(slab.borrowed).toBeLessThan(slab.placements.length / 5);
    });
});

describe("the sweep agrees with the documented per-pair projection", () => {
    it("matches `slabSeparation` at every pose it samples", () => {
        /*
         * The sweep above projects every point once per pose for speed. This checks that the
         * shortcut is the same arithmetic as the exported per-pair function, which is what any
         * other caller would use - otherwise the fast path could drift and the sweep would be
         * asserting a bound about a projection nothing else uses.
         */
        const slab = layoutFocusSlab(1, members(12, 3), { radius: SLAB_RADIUS_MAX });
        const points = [
            { x: 0, y: 0, z: 0 },
            ...slab.placements.map((p) => ({ x: p.x, y: p.y, z: p.z })),
        ];
        const measured = sweep(slab);
        let worst = Number.POSITIVE_INFINITY;
        for (let a = 0; a < AZIMUTHS; a += 1) {
            const azimuth = (a / AZIMUTHS) * 360;
            for (let e = 0; e < ELEVATIONS; e += 1) {
                const elevation =
                    SLAB_ELEVATION.min +
                    ((SLAB_ELEVATION.max - SLAB_ELEVATION.min) * e) / (ELEVATIONS - 1);
                for (let i = 0; i < points.length; i += 1) {
                    for (let j = i + 1; j < points.length; j += 1) {
                        worst = Math.min(
                            worst,
                            slabSeparation(points[i], points[j], azimuth, elevation),
                        );
                    }
                }
            }
        }
        expect(measured.worst).toBeCloseTo(worst, 9);
    });
});

describe("the bound's own arithmetic", () => {
    it("is the arbitration's formula", () => {
        const s = 122;
        const h = 0.15 * s;
        const expected = s * Math.sin((42 * Math.PI) / 180 - Math.atan((2 * h) / s));
        expect(slabSeparationBound(s, h, 42)).toBeCloseTo(expected, 9);
    });

    it("degenerates to a flat disc when the slab has no thickness", () => {
        /* With H = 0 the slab is a plane and the bound is the pitch foreshortened by the
           elevation alone, which is the case the arbitration checked to four decimals. */
        expect(slabSeparationBound(100, 0, 42)).toBeCloseTo(100 * Math.sin((42 * Math.PI) / 180), 9);
    });

    it("returns zero rather than a negative number it could be compared against", () => {
        /* A band that dips below the slab's own aspect angle has no guarantee. Returning the
           signed value would let a caller compare it and pass. */
        expect(slabSeparationBound(10, 40, 42)).toBe(0);
        expect(slabSeparationBound(0, 0, 42)).toBe(0);
    });

    it("improves as the elevation floor rises, which is why the band is clamped", () => {
        const lower = slabSeparationBound(122, 18, 30);
        const higher = slabSeparationBound(122, 18, 60);
        expect(higher).toBeGreaterThan(lower);
    });
});

describe("the radius, and the re-space", () => {
    it("scales with the band a reader can see and never past the measured maximum", () => {
        expect(slabRadiusFor(836)).toBeCloseTo(376.2, 1);
        expect(slabRadiusFor(2000)).toBe(SLAB_RADIUS_MAX);
        expect(slabRadiusFor(120)).toBeGreaterThan(0);
        expect(slabRadiusFor(0)).toBeGreaterThan(0);
        expect(slabRadiusFor(Number.NaN)).toBeGreaterThan(0);
    });

    it("still holds the bound on a phone-sized band", () => {
        const slab = layoutFocusSlab(1, members(16, 5), { radius: slabRadiusFor(434) });
        const measured = sweep(slab);
        expect(measured.worst).toBeGreaterThanOrEqual(slab.separationBound - 1e-6);
        expect(slab.separationBound).toBeGreaterThan(0);
    });

    it("offers nothing to re-space at the median, and something real above it", () => {
        /* The control this feeds must be able to disable itself. A button that animates a scene
           into the arrangement it is already in is worse than an absent one. */
        for (const count of [1, 3, 6, 8, 12]) {
            expect(slabSpreadGain(count, SLAB_RADIUS_MAX)).toBeCloseTo(1, 6);
        }
        /* And nothing at the desktop budget either, because there the compact arrangement is
           already the widest one. The window is 13 to about 31, and the control must read it
           rather than assume it. */
        expect(slabSpreadGain(40, SLAB_RADIUS_MAX)).toBeCloseTo(1, 6);
        expect(slabSpreadGain(16, SLAB_RADIUS_MAX)).toBeGreaterThan(1.1);
        expect(slabSpreadGain(24, SLAB_RADIUS_MAX)).toBeGreaterThan(1.3);
    });

    it("keeps the bound after a re-space, from every pose", () => {
        for (const count of [24, 40, 50]) {
            const wide = layoutFocusSlab(1, members(count, 6), {
                radius: SLAB_RADIUS_MAX,
                spread: "wide",
            });
            const compact = layoutFocusSlab(1, members(count, 6), {
                radius: SLAB_RADIUS_MAX,
                spread: "compact",
            });
            expect(wide.separationBound).toBeGreaterThanOrEqual(compact.separationBound);
            expect(sweep(wide).worst).toBeGreaterThanOrEqual(wide.separationBound - 1e-6);
        }
    });
});

describe("degenerate input", () => {
    it("answers an empty neighbourhood without pretending to a guarantee", () => {
        const slab = layoutFocusSlab(7, [], { radius: SLAB_RADIUS_MAX });
        expect(slab.placements).toEqual([]);
        expect(slab.root).toBe(7);
        expect(slab.separationBound).toBe(Number.POSITIVE_INFINITY);
    });

    it("puts a single neighbour somewhere clear of the hub", () => {
        const slab = layoutFocusSlab(1, members(1, 1), { radius: SLAB_RADIUS_MAX });
        expect(slab.placements).toHaveLength(1);
        expect(Math.hypot(slab.placements[0].x, slab.placements[0].y)).toBeGreaterThan(0);
        expect(slab.placements[0].z).toBe(0);
    });
});
