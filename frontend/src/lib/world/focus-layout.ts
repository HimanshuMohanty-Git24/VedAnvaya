/**
 * Where a curated neighbourhood is drawn: a tilted slab, not a shell.
 *
 * ## Why this is a plane and not a ball
 *
 * The first design for this was a family-sectored sunflower over three spherical shells, on the
 * claim that a 3D relaxation is orbit-invariant, so an arrangement good from the arrival pose is
 * good from any pose. That claim is false, and the counter-example is one line:
 *
 *     sep(v) = |(I - v.vT)(pi - pj)| = |d| * sin(angle between d and v)
 *
 * Choose the view direction along the line joining any two nodes and their projected separation
 * is zero. It holds in orthographic and a fortiori in perspective, so **there is no layout in a
 * free orbit with a guaranteed minimum projected separation**. The shell was measured before it
 * was abandoned: 40 nodes at 3D Poisson-disk separation, swept over 180x25 viewpoints, gave a
 * worst-case minimum projected separation of 0.0003 disc radii - a total eclipse - and a mean of
 * 10.9 overlapping pairs per random view out of 780, worst 22.
 *
 * A shell is also the worst available shape for the complaint it was meant to answer. Uniform on
 * a sphere puts z uniform on [-1, 1], so the projected radial density is r / sqrt(1 - r^2), which
 * diverges at the silhouette: measured over 200k samples, **59.8% of points land in the outer 36%
 * of the projected disc**. The flat ring the shell was chosen to avoid is what a shell produces,
 * and the simulation would have taken the blame.
 *
 * A slab with a clamped elevation band does have a guarantee. With the camera free in azimuth and
 * its elevation above the slab plane at least `theta`, nodes in a slab of half-thickness H about a
 * plane whose minimum in-plane separation is s satisfy
 *
 *     sep >= s * sin( theta - arctan(2H / s) )
 *
 * That is `slabSeparationBound`, and `tests/unit/focus-layout.test.ts` sweeps 360 azimuths across
 * the whole elevation band and asserts it. A separation asserted at one pose is the defect this
 * module exists to prevent, so the test is the deliverable and not a formality.
 *
 * ## What the bound is not
 *
 * It is an *orthographic* statement, and the renderer is perspective. Swept the same way through
 * the real lens the worst case comes in **12.5% under** the proven bound at the worst count -
 * 38.70 px falls to 33.87 - because the further of two nodes projects smaller and drifts towards
 * the vanishing point. So the bound is not a pixel promise about the screen, and calling it one
 * would be the same overclaim the shell was retired for. What holds on screen is the weaker
 * claim: two orbs never touch, 33.87 px against a 22 px drawn orb. The error scales with the
 * slab radius over the camera distance, which is fixed by the field of view alone once the slab
 * has to fill the frame - 0.44 at 52 degrees against 0.28 at 34 - and that is why Focus draws
 * through a narrower lens than the world does.
 *
 * Depth comes from the slab thickness and from the cues the renderer applies - occlusion, size
 * attenuation, aerial perspective - not from volume. Looking down on a plane preserves
 * separation; looking along it destroys it, which is why the band is clamped rather than free.
 *
 * ## Tuned for six, built to survive fifty
 *
 * The real fan-out was measured over the whole artifact: distinct neighbours per node p50 = 6,
 * p75 = 8, p90 = 12, p99 = 43, and only 308 of 35,370 nodes exceed 50. So the typical scene is
 * six orbs in three families, and the layout's first duty is not to spoil that.
 *
 * It is also why the ring count is minimised rather than the packing maximised. Edge-node overlap
 * is measured as mattering more to readers than node-node overlap, and on a single ring the
 * clearance between a node and the nearest spoke is as large as the pitch itself - measured at
 * 0.87 of the pitch at six orbs rising to 0.99 at twenty-four, because the only spokes that pass a
 * node at all are its immediate neighbours' and those leave at a whole angular division. A single
 * ring covers every count up to 24, which is past p90. Above that the rule takes the fewest rings
 * whose provable bound still clears `SEPARATION_FLOOR`.
 *
 * Two earlier attempts are worth recording, because each was defeated by something the next one
 * had to answer. The first maximised the in-plane pitch by relaxation in a disc with the hub
 * pinned: it reached only 0.787 of the achievable pitch at forty orbs once family sectors were
 * enforced, and its worst node-to-spoke clearance fell to 5.7 px at fifty. The second used
 * concentric rings each filled to its own circumference, with the ring offsets searched for
 * clearance; it packed well - 102.1 px of pitch at forty - and the clearance still collapsed to
 * **1.1 px**, because the free fill puts 17 and 23 seats on two rings, coprime counts admit
 * angles dense to a third of a degree, and no offset exists. The shared grid in `planRings` gives
 * up 11% of that pitch and returns 45.3 px of clearance for it.
 *
 * ## What this module does not do
 *
 * It places nothing on screen and knows nothing about labels. Label placement is one unified
 * screen-space pass over node labels and relationship labels together, owned elsewhere; this
 * supplies geometry and stops. Two passes on separate cadences cannot honour one priority order,
 * because a relation can never outrank a name that was already placed.
 */

/** Degrees to radians. Used often enough here to be worth a name. */
const DEG = Math.PI / 180;
const TAU = Math.PI * 2;

/**
 * The slab's in-plane radius, as a share of the shorter visible axis.
 *
 * 0.45 rather than 0.5 because the outermost ring has to leave the orb's own radius plus room for
 * a name outside it. On the measured 1440x836 desktop canvas this yields 376 px, which is the
 * 380 px the arbitration worked its parameters at; on a phone band of 434 px it yields 195.
 */
const RADIUS_FRACTION = 0.45;

/** The arbitration's worked radius. A larger canvas gains distance, not sprawl. */
export const SLAB_RADIUS_MAX = 380;

/** Below this the scene is not a place, and the caller should be drawing a list. */
export const SLAB_RADIUS_MIN = 90;

/**
 * Slab half-thickness as a share of the achieved in-plane pitch.
 *
 * The arbitration allows up to 0.17 and verified the bound numerically at 0.07 / 0.17 / 0.33.
 * 0.15 is taken because the bound falls faster than the depth cue improves: at theta = 42 degrees
 * and N = 40, going from 0.15 to 0.17 costs 3.1 px of guaranteed separation and buys 1.9 px of
 * slab. Keeping it a *ratio* is the part that matters - it makes the guarantee a fixed fraction of
 * the pitch, so a six-orb scene gets a genuinely thick slab and a fifty-orb scene gets a thin one,
 * which is the right trade in both directions.
 */
const THICKNESS_RATIO = 0.15;

/**
 * The camera's elevation above the slab plane, in degrees. Clamped, and the clamp is the guarantee.
 *
 * The default is deliberately off both axes. An axis-aligned arrival pose reads as a diagram
 * rather than a place and users reject it; it is also the one pose from which the slab's thickness
 * conveys nothing.
 */
export const SLAB_ELEVATION = { min: 42, max: 80, default: 56 } as const;

/** Default azimuth, in degrees. Off-axis for the same reason the elevation is. */
export const SLAB_AZIMUTH_DEFAULT = 34;

/**
 * The guaranteed separation two orbs need before the layout is allowed to add a ring.
 *
 * 1.6 times a 22 px orb. At exactly one orb diameter two discs touch, which is legible but reads
 * as a pair; 1.6 leaves a gap the eye resolves as two things without having to look for it.
 */
export const SEPARATION_FLOOR = 35;

/** Most rings the search will consider. Eight covers 200, which is the expansion ceiling. */
const MAX_RINGS = 8;

/** One member of the neighbourhood, as this module needs it. */
export type SlabMember = {
    /** Node index in the world artifact. The identity a transition keys on - never the slot. */
    node: number;
    /**
     * Which relationship family sectors this member.
     *
     * An index rather than a name so this module carries no vocabulary. A member in more than one
     * family is sectored by one of them; which one is the caller's decision, not this module's.
     */
    family: number;
};

export type SlabPlacement = {
    node: number;
    /** In-plane, in CSS pixels at the framing distance. The hub is at the origin. */
    x: number;
    y: number;
    /** Along the slab normal, same units. |z| <= halfThickness. */
    z: number;
    family: number;
    /** Which ring, innermost 0. */
    ring: number;
    /** Position in the input order, which is the caller's salience order. */
    rank: number;
};

export type FocusSlab = {
    root: number;
    /** Neighbours only. The root is pinned at the origin and is not in this list. */
    placements: SlabPlacement[];
    /** In-plane radius the layout was solved for, CSS px. */
    radius: number;
    /** Achieved minimum in-plane separation, CSS px. Guaranteed by construction, then measured. */
    spacing: number;
    halfThickness: number;
    /** Members per ring, innermost first. */
    rings: number[];
    ringRadii: number[];
    /**
     * The provable floor on projected separation from every reachable camera pose, CSS px, at the
     * framing distance. Zooming in raises it; zooming out is what `maxDistance` exists to bound.
     */
    separationBound: number;
    /**
     * Smallest distance from a node to another node's spoke, CSS px. Infinity where no spoke can
     * pass a node at all, which is every single-ring layout.
     *
     * Measured, not guaranteed. The ring construction cannot promise it above one ring, and
     * saying so is the point: see the module note on the fewest-rings rule.
     */
    spokeClearance: number;
    /**
     * Members seated outside their own family's sector because it was short by rounding.
     *
     * Reported rather than hidden. A sectoring that silently misplaces a member is worse than one
     * that says how often it had to.
     */
    borrowed: number;
    /** Which of the two arrangements this is. See `SlabSpread`. */
    spread: SlabSpread;
};

/**
 * Which of two arrangements of the same members to use.
 *
 * They are not better and worse, they are a trade, and it is the trade a reader who finds a scene
 * cramped is actually asking about.
 *
 * `compact` takes the fewest rings whose guarantee clears `SEPARATION_FLOOR`, because every extra
 * ring costs node-to-spoke clearance. `wide` takes whichever ring count has the largest guaranteed
 * separation, wherever that is a different answer.
 *
 * Measured on a desktop canvas, R = 380 px, the window in which the two differ is **narrow**: at
 * 16 members `wide` gains 11% and at 24 it gains 31%, and at 12 and below and at 32 and above the
 * two arrangements are the same one. That is the honest account of this control - it does nothing
 * at the median, nothing at the desktop budget of forty, and something real for a subject with
 * between thirteen and about thirty neighbours. `slabSpreadGain` exists so that a control can read
 * that and disable itself, rather than animating a scene into the arrangement it is already in.
 */
export type SlabSpread = "compact" | "wide";

/* ------------------------------------------------------------------ rings - */

/**
 * ARB-1's in-plane target: the max-min separation for N points in a disc with the hub pinned.
 *
 * Used as a *ceiling* on the pitch rather than as a goal. Where the ring geometry could spread
 * further than this it is held back instead, because the extra pitch is bought by pushing the
 * outermost ring against the edge of the disc, and the disc's radius already has the orb and its
 * name budgeted into it. Six neighbours therefore sit on a ring at 0.83 R with a 65 px gutter
 * rather than at 1.0 R with none.
 */
const PITCH_TARGET = 2.03;

/**
 * One ring arrangement: a pitch, a shared angular grid, and where each ring sits.
 *
 * ## The grid is the whole idea, and it replaced a search
 *
 * Every ring's seats lie on the *same* `grid`-fold division of the circle, with ring k rotated by
 * `k / ringCount` of one division. That single constraint is what makes node-to-spoke clearance
 * provable: a spoke runs from the hub to a node, so an inner node lies on an outer node's spoke
 * exactly when the two share an angle, and on a shared grid rotated by even fractions the
 * smallest angle between any two rings' seats is exactly one fraction of one division. No search,
 * no measurement, no hope.
 *
 * The first version did search. It let each ring hold as many seats as its circumference allowed
 * and then hunted for the offsets that kept nodes furthest off each other's spokes - greedy, then
 * coordinate descent, 192 probes a ring. It was very nearly optimal and almost worthless, because
 * the thing it was optimising has no good answer: at forty orbs the free fill is 17 and 23 seats,
 * those counts are coprime, so the achievable angles are dense at a spacing of 360/391 of a
 * degree and the best possible clearance is about 2 px. Measured, the search found **1.1 px** out
 * of a theoretical 2.2. A node sat on a spoke and no amount of searching could move it off.
 *
 * The shared grid gives up pitch to fix that, and the trade is heavily worth taking because
 * edge-node overlap is measured as mattering more to readers than node-node overlap. At forty
 * orbs: two rings of twenty, pitch **90.6 px against the free fill's 102.1** - 11% less - and
 * node-to-spoke clearance **45.3 px against 1.1** - forty times more.
 */
type RingPlan = {
    /** Minimum in-plane separation, CSS px. Guaranteed by construction. */
    pitch: number;
    /** Seats per ring on the shared angular division. */
    grid: number;
    /** Members per ring, innermost first. Only the outermost may be short. */
    fill: number[];
    ringRadii: number[];
    /** Angular offset per ring, radians. */
    offsets: number[];
    /** Minimum distance from a node to another node's spoke, CSS px. Also guaranteed. */
    spokeClearance: number;
};

/**
 * The best arrangement of `count` members in exactly `ringCount` rings.
 *
 * Closed form, not bisected. Three constraints bind and all three are linear in the pitch, so the
 * largest feasible pitch can be written down:
 *
 *   - a chord on the grid must be at least the pitch, so a ring's radius is at least
 *     `pitch / (2 sin(pi / grid))`;
 *   - consecutive rings must be a pitch apart, radially;
 *   - the innermost ring must clear the pinned hub by a pitch;
 *   - the outermost must fit inside the disc.
 *
 * Taken together the stack spans `max(chord, 1) + ringCount - 1` pitches, which is the divisor
 * below. The previous version bisected for this because it allowed each ring its own seat count,
 * which made feasibility a step function; a shared grid makes it an equation.
 */
function planRings(radius: number, count: number, ringCount: number): RingPlan | null {
    if (count < 1 || ringCount < 1 || radius <= 0) return null;
    const grid = Math.ceil(count / ringCount);
    /* A ring this count does not actually use is a different ring count, and returning it would
       let the caller compare two names for one arrangement. */
    if (grid * (ringCount - 1) >= count) return null;

    /* How many pitches out the innermost ring has to sit for its own chord to be a pitch. Below a
       ring of six the chord constraint is weaker than the hub clearance, so the hub wins. */
    const chord = grid < 2 ? 1 : Math.max(1, 1 / (2 * Math.sin(Math.PI / grid)));
    const span = chord + ringCount - 1;
    const pitch = Math.min(radius / span, (PITCH_TARGET * radius) / Math.sqrt(count));
    if (!(pitch > 0)) return null;

    const first = pitch * chord;
    const ringRadii: number[] = [];
    for (let k = 0; k < ringCount; k += 1) ringRadii.push(first + k * pitch);
    if (ringRadii[ringCount - 1] > radius + 1e-6) return null;

    const fill: number[] = [];
    let left = count;
    for (let k = 0; k < ringCount; k += 1) {
        const take = Math.min(left, grid);
        fill.push(take);
        left -= take;
    }
    if (left > 0 || fill[ringCount - 1] < 1) return null;

    const division = TAU / grid;
    const step = division / ringCount;
    const offsets = ringRadii.map((_, k) => k * step);

    /*
     * The clearance, in closed form.
     *
     * Across rings the smallest angle between seats is one `step`, and the node nearest the hub is
     * the one whose spoke-distance that angle costs the most, so `first * sin(step)` is the floor.
     * Within one ring the neighbours are a whole `division` apart, and once that exceeds a quarter
     * turn the perpendicular foot falls off the spoke entirely - there is no spoke there to be
     * near, which is why a three-seat ring has no such pair at all.
     */
    const within =
        division >= Math.PI / 2
            ? Number.POSITIVE_INFINITY
            : ringRadii[0] * Math.sin(division);
    const across = ringCount > 1 ? first * Math.sin(step) : Number.POSITIVE_INFINITY;
    return { pitch, grid, fill, ringRadii, offsets, spokeClearance: Math.min(within, across) };
}


/* ------------------------------------------------------------- the bound - */

/**
 * The provable floor on projected separation, given an in-plane pitch, a slab half-thickness and
 * the lowest elevation the camera may reach.
 *
 * Clamped at zero: an elevation band that dips below the slab's own aspect angle has no guarantee,
 * and returning a negative number would let a caller compare it against something and pass.
 */
export function slabSeparationBound(
    pitch: number,
    halfThickness: number,
    elevationMinDeg: number,
): number {
    if (!(pitch > 0)) return 0;
    const angle = elevationMinDeg * DEG - Math.atan((2 * halfThickness) / pitch);
    return angle <= 0 ? 0 : pitch * Math.sin(angle);
}

/**
 * Where a slab point lands on screen, orthographically, from a given pose.
 *
 * Orthographic on purpose. The bound is an orthographic statement, and perspective only ever
 * increases the separation of the nearer of two nodes, so testing orthographically tests the
 * harder case. The slab lies in the plane y = 0 of a right-handed frame whose +y is the slab
 * normal; elevation is measured up from that plane and azimuth around it.
 */
export function projectSlab(
    point: { x: number; y: number; z: number },
    azimuthDeg: number,
    elevationDeg: number,
): { x: number; y: number } {
    const az = azimuthDeg * DEG;
    const el = elevationDeg * DEG;
    // World position: in-plane (x, y) maps to (x, z); the slab offset maps to world y.
    const wx = point.x;
    const wy = point.z;
    const wz = point.y;
    // Screen right is horizontal and perpendicular to the view azimuth.
    const rx = -Math.sin(az);
    const rz = Math.cos(az);
    // Screen up is the view direction rotated a quarter turn in the vertical plane.
    const ux = -Math.sin(el) * Math.cos(az);
    const uy = Math.cos(el);
    const uz = -Math.sin(el) * Math.sin(az);
    return { x: wx * rx + wz * rz, y: wx * ux + wy * uy + wz * uz };
}

/** Projected distance between two slab points from a given pose. */
export function slabSeparation(
    a: { x: number; y: number; z: number },
    b: { x: number; y: number; z: number },
    azimuthDeg: number,
    elevationDeg: number,
): number {
    const pa = projectSlab(a, azimuthDeg, elevationDeg);
    const pb = projectSlab(b, azimuthDeg, elevationDeg);
    return Math.hypot(pa.x - pb.x, pa.y - pb.y);
}

/* ------------------------------------------------------------ measurement - */

/**
 * What the arrangement actually achieved, in plan.
 *
 * Separate from the construction so the test measures the shipped geometry rather than re-deriving
 * what the construction believes about itself. The hub counts as a node: a neighbour drawn on top
 * of the subject is the worst case of all, and an earlier version omitted it.
 */
export function measureSlabPlan(slab: FocusSlab): { minNode: number; minSpoke: number } {
    const points = slab.placements;
    let minNode = Infinity;
    for (let i = 0; i < points.length; i += 1) {
        minNode = Math.min(minNode, Math.hypot(points[i].x, points[i].y));
        for (let j = i + 1; j < points.length; j += 1) {
            minNode = Math.min(
                minNode,
                Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y),
            );
        }
    }
    let minSpoke = Infinity;
    for (let i = 0; i < points.length; i += 1) {
        const ri = Math.hypot(points[i].x, points[i].y);
        for (let j = 0; j < points.length; j += 1) {
            if (i === j) continue;
            const rj = Math.hypot(points[j].x, points[j].y);
            if (rj <= ri) continue;
            const ux = points[j].x / rj;
            const uy = points[j].y / rj;
            const along = points[i].x * ux + points[i].y * uy;
            /* Only the part of the spoke that exists: past either end there is no line to be near. */
            if (along <= 0 || along >= rj) continue;
            minSpoke = Math.min(minSpoke, Math.abs(-points[i].x * uy + points[i].y * ux));
        }
    }
    return { minNode, minSpoke };
}

/* ---------------------------------------------------------------- layout - */

/**
 * Choose the ring count, which is the whole of the compact/wide trade.
 *
 * `compact` stops at the first ring count good enough, because every extra ring costs
 * node-to-spoke clearance and the first adequate answer keeps the most of it. `wide` keeps
 * looking for the largest guarantee. Where nothing clears the floor - which begins between 64
 * and 100 members on a desktop canvas, well past the budget of 40 and short of the expansion
 * ceiling of 200 - both take the strongest guarantee available, because at that point the caller
 * is drawing more than the space holds and a floor is not a thing the layout can offer.
 */
function solveRings(
    radius: number,
    count: number,
    spread: SlabSpread,
): RingPlan | null {
    let best: RingPlan | null = null;
    let bestBound = -Infinity;
    for (let ringCount = 1; ringCount <= MAX_RINGS; ringCount += 1) {
        const candidate = planRings(radius, count, ringCount);
        if (!candidate) continue;
        const bound = slabSeparationBound(
            candidate.pitch,
            THICKNESS_RATIO * candidate.pitch,
            SLAB_ELEVATION.min,
        );
        if (bound > bestBound) {
            bestBound = bound;
            best = candidate;
        }
        if (spread === "compact" && bound >= SEPARATION_FLOOR) return candidate;
    }
    return best;
}

/**
 * What a re-space would buy, as a ratio of guaranteed separation. 1 means nothing.
 *
 * Exported so a control can disable itself rather than offering an action that does nothing. At
 * twelve members and below this returns exactly 1, which is the common case: the compact
 * arrangement is already the widest one, and a reader at the median has nothing to gain because
 * the layout was not fighting them in the first place.
 */
export function slabSpreadGain(count: number, radius: number): number {
    if (count <= 1) return 1;
    const compact = solveRings(radius, count, "compact");
    const wide = solveRings(radius, count, "wide");
    if (!compact || !wide) return 1;
    const of = (pitch: number) =>
        slabSeparationBound(pitch, THICKNESS_RATIO * pitch, SLAB_ELEVATION.min);
    const from = of(compact.pitch);
    return from > 0 ? Math.max(1, of(wide.pitch) / from) : 1;
}

/** The slab radius a canvas of this shorter visible axis affords, CSS px. */
export function slabRadiusFor(shortAxisPx: number): number {
    if (!Number.isFinite(shortAxisPx) || shortAxisPx <= 0) return SLAB_RADIUS_MIN;
    return Math.max(
        SLAB_RADIUS_MIN,
        Math.min(SLAB_RADIUS_MAX, shortAxisPx * RADIUS_FRACTION),
    );
}

/**
 * Lay a curated neighbourhood out on the slab.
 *
 * `members` arrives in the caller's salience order and that order is kept: it decides the slab
 * offset, which seat inside a family sector a member takes, and the stagger order of the
 * transition. Families sector the plane as an angular partition, in the order they appear.
 */
export function layoutFocusSlab(
    root: number,
    members: readonly SlabMember[],
    {
        radius = SLAB_RADIUS_MAX,
        spread = "compact",
    }: { radius?: number; spread?: SlabSpread } = {},
): FocusSlab {
    const count = members.length;
    const empty: FocusSlab = {
        root,
        placements: [],
        radius,
        spacing: Infinity,
        halfThickness: 0,
        rings: [],
        ringRadii: [],
        separationBound: Infinity,
        spokeClearance: Infinity,
        borrowed: 0,
        spread,
    };
    if (count === 0) return empty;

    const chosen = solveRings(radius, count, spread);
    if (!chosen) return empty;

    const { pitch, fill, ringRadii: radii, offsets, grid } = chosen;

    /*
     * Every seat, innermost ring first and each ring in angular order.
     *
     * The angular step is one division of the *shared grid*, not of the ring's own count. On a
     * partly filled outermost ring those are different numbers, and using the ring's own count
     * would space its members evenly right round the circle - off the grid, and with the
     * clearance guarantee gone with it.
     */
    const seats: Array<{ ring: number; radius: number; angle: number }> = [];
    fill.forEach((seated, ring) => {
        for (let i = 0; i < seated; i += 1) {
            seats.push({
                ring,
                radius: radii[ring],
                angle: (offsets[ring] + (i * TAU) / grid) % TAU,
            });
        }
    });

    /*
     * Families as an angular partition, sized in proportion to membership.
     *
     * A family whose wedge is short by rounding takes the nearest free seat outside it and the
     * borrow is counted. The alternative - sizing every wedge to its worst case - costs the whole
     * scene pitch to fix an occasional single misplacement.
     */
    const order = members.map((member, rank) => ({ ...member, rank }));
    const familyOrder: number[] = [];
    for (const member of order) {
        if (!familyOrder.includes(member.family)) familyOrder.push(member.family);
    }
    let at = 0;
    const wedges = familyOrder.map((family) => {
        const size = order.filter((member) => member.family === family).length;
        const from = at;
        at += (size / count) * TAU;
        return { family, from, to: at, size };
    });

    const taken = new Array(seats.length).fill(false);
    const placements: SlabPlacement[] = [];
    let borrowed = 0;
    const angularDistance = (a: number, b: number) =>
        Math.abs(((a - b + Math.PI * 3) % TAU) - Math.PI);

    for (const wedge of wedges) {
        const inside = (angle: number) => angle >= wedge.from && angle < wedge.to;
        const mid = (wedge.from + wedge.to) / 2;
        const ranked = seats
            .map((seat, index) => ({ seat, index }))
            .sort((a, b) => {
                const aIn = inside(a.seat.angle) ? 0 : 1;
                const bIn = inside(b.seat.angle) ? 0 : 1;
                if (aIn !== bIn) return aIn - bIn;
                if (aIn === 0) {
                    // Inside the wedge: inner rings first, so salience reads as nearness.
                    return a.seat.ring - b.seat.ring || a.seat.angle - b.seat.angle;
                }
                return angularDistance(a.seat.angle, mid) - angularDistance(b.seat.angle, mid);
            });
        const mine = order.filter((member) => member.family === wedge.family);
        let dealt = 0;
        for (const { seat, index } of ranked) {
            if (dealt >= mine.length) break;
            if (taken[index]) continue;
            taken[index] = true;
            if (!inside(seat.angle)) borrowed += 1;
            const member = mine[dealt];
            placements.push({
                node: member.node,
                x: Math.cos(seat.angle) * seat.radius,
                y: Math.sin(seat.angle) * seat.radius,
                z: 0,
                family: member.family,
                ring: seat.ring,
                rank: member.rank,
            });
            dealt += 1;
        }
    }

    /*
     * Salience lifts a node off the plane, and it is a reading rather than decoration.
     *
     * The camera's elevation is clamped above the slab, so the slab normal always points towards
     * the viewer: +H is nearer, without exception and whatever the azimuth. A monotone ramp by
     * rank therefore says the same thing from every reachable pose, which a random scatter of
     * offsets would not.
     */
    const halfThickness = THICKNESS_RATIO * pitch;
    for (const placement of placements) {
        placement.z =
            count > 1 ? halfThickness * (1 - (2 * placement.rank) / (count - 1)) : 0;
    }
    // Back to the caller's order, so `placements[i]` and `members[i]` describe the same subject.
    placements.sort((a, b) => a.rank - b.rank);

    const slab: FocusSlab = {
        root,
        placements,
        radius,
        spacing: pitch,
        halfThickness,
        rings: fill,
        ringRadii: radii,
        separationBound: slabSeparationBound(pitch, halfThickness, SLAB_ELEVATION.min),
        spokeClearance: chosen.spokeClearance,
        borrowed,
        spread,
    };
    const measured = measureSlabPlan(slab);
    /*
     * The bound is restated from the *measured* pitch, not the solved one.
     *
     * They agree by construction, and the point of not assuming so is that a defect in the
     * construction would otherwise be published as a guarantee. Whichever is smaller is the one
     * that can be honestly promised.
     */
    slab.spacing = Math.min(pitch, measured.minNode);
    slab.separationBound = slabSeparationBound(
        slab.spacing,
        halfThickness,
        SLAB_ELEVATION.min,
    );
    /* Same reasoning as the pitch: the construction computes this in closed form, and the plan
       is then measured to check the construction rather than to replace it. */
    slab.spokeClearance = Math.min(chosen.spokeClearance, measured.minSpoke);
    return slab;
}
