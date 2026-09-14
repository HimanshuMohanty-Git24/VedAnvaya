import {
    type Constellation,
    type World,
    edgesOf,
    otherEnd,
} from "./artifact";
import {
    FOCUS_ORB_RADIUS,
    FOCUS_TOUCH_PITCH,
    FAMILY_INDEX,
    type FocusNeighbour,
    type FocusNeighbourhood,
} from "./focus";
import { type PointerKind } from "./gesture";
import {
    type Field,
    PLANAR_TUNING,
    createField,
    fieldBounds,
    relaxOverlaps,
    stepField,
    tuningFor,
} from "./local-physics";

/**
 * The planar view: a manuscript diagram you can pull apart.
 *
 * This is not the 3D view flattened, and it is emphatically not a fallback. It answers a
 * different question. The world map answers "where does this sit in the corpus"; this answers
 * "what is attached to this, and how tightly" - and for that, being able to take hold of a
 * subject and feel its neighbours resist is worth more than depth.
 *
 * ## The physics lives next door
 *
 * Everything about how the marks move is in `local-physics.ts`, written over an axis count so
 * the spatial renderer runs the same model rather than a second one that drifts from it
 * (ARB-7). This module is the 2D binding: it decides *where the marks go* and *how big they
 * are*, which is the part that genuinely differs between a plane and a slab.
 *
 * ## Why the layout is authored in CSS pixels
 *
 * Because the previous one was authored in arbitrary graph units and then squashed. Measured on
 * the real artifact at 1440x760, `fit` resolved to a scale of 0.317-0.339 for every subject
 * tried, so a leaf orb drawn at `4 + cbrt(degree) * 1.5` units came out at **3.85 px across
 * every viewport** and the pick radius came out at 1.87-3.90 px. The mark, the hit target and
 * the reader's finger were all functions of a number nobody had chosen.
 *
 * So the slots below are px at scale 1, the neighbour count is taken from what the band can
 * seat (`focusBudgetForBand`), and `fit` for an authored scene translates without scaling up.
 * The separation floor is then a property of the layout rather than of the viewport, and
 * `tests/unit/local-physics.test.ts` asserts it instead of a comment claiming it.
 *
 * ## Why it comes to rest
 *
 * A graph that jitters forever is unreadable and looks like a screensaver. Energy enters only
 * when the reader puts it in - a drag, a selection, a new neighbourhood - and decays. Below a
 * threshold the simulation stops stepping entirely rather than continuing to compute
 * imperceptible motion, so an untouched diagram is perfectly still.
 */

export type PlanarNode = {
    /** Index into the world artifact, so every view names subjects the same way. */
    id: number;
    x: number;
    y: number;
    vx: number;
    vy: number;
    /** Heavier nodes move less when pulled, which reads as "this one is more established". */
    mass: number;
    /** Drawn radius in CSS px at scale 1 for an authored scene; see `markRadius`. */
    radius: number;
    /** Index into `manifest.groups`, or -1 where the mark stands for no single group. */
    group: number;
    degree: number;
    /** Depth from the root: 0 is the subject itself, 1 its neighbours. */
    ring: number;
    /** Held by the pointer. A held node ignores forces and is moved directly. */
    held: boolean;
    /** Pinned nodes resist but are not immovable; a slot anchor is soft. */
    anchorX: number | null;
    anchorY: number | null;
    /** Subjects this mark stands for. 1 where it is one subject. */
    members: number;
    /** The mark's own name, where it has one. Null means "look the label up by `id`". */
    caption: string | null;
    /**
     * Whether this mark's name is worth drawing beside it, as opposed to on hover.
     *
     * Separate from `caption` having a value, because an unnamed constellation still has
     * something to say when a reader points at it - its number - and nothing to say on a
     * crowded map. See `constellationCaption`.
     */
    labelled: boolean;
};

export type PlanarEdge = {
    a: number;
    b: number;
    /**
     * Index into the world edge arrays, so the inspector can look the relationship up.
     *
     * **-1 where the line is an aggregate** and stands for no single relationship - the
     * constellation links in the world scene are the only case. Naming one of the 3,303 bridge
     * edges between two constellations as though it were the link would be a caption about a
     * line the reader is not looking at.
     */
    edge: number;
    rest: number;
    bridge: boolean;
    /** Relationships this line stands for. 1 where it is one. */
    weight: number;
};

export type PlanarGraph = {
    nodes: PlanarNode[];
    edges: PlanarEdge[];
    index: Map<number, number>;
    rootId: number | null;
    /** The bodies and springs behind `nodes`. One store, so nothing can disagree with it. */
    field: Field;
    /**
     * True where positions are CSS px at scale 1, so `fit` may translate but must not enlarge.
     *
     * A scene that is not authored - none ship today - would be in the artifact's own units and
     * fitted as before.
     */
    authored: boolean;
    /**
     * The centre-to-centre separation the layout guarantees, in px, or null where it makes no
     * such promise. Asserted rather than asserted-in-a-comment; see `worstSeparation`.
     */
    guarantee: number | null;
    /** What `respaceFocusScene` has multiplied the slot radii by. 1 is the authored layout. */
    spacing: number;
};

/* ------------------------------------------------------------------ the bodies - */

/**
 * A node record backed by the field's arrays.
 *
 * Accessors rather than a copy. The alternative - plain objects synced into the field before
 * each step and back out after - is two stores for one fact, and this codebase has now recorded
 * four separate defects of that exact shape (two semantic colour tables, two neighbourhood
 * selectors, two label collision passes, two zoom clamps). One store, read through a view.
 */
class PlanarBody {
    constructor(
        private readonly field: Field,
        private readonly at: number,
        public id: number,
        public group: number,
        public degree: number,
        public ring: number,
        public members: number,
        public caption: string | null,
        public labelled: boolean,
    ) {}

    get x(): number {
        return this.field.pos[this.at * 2];
    }
    set x(value: number) {
        this.field.pos[this.at * 2] = value;
    }
    get y(): number {
        return this.field.pos[this.at * 2 + 1];
    }
    set y(value: number) {
        this.field.pos[this.at * 2 + 1] = value;
    }
    get vx(): number {
        return this.field.vel[this.at * 2];
    }
    set vx(value: number) {
        this.field.vel[this.at * 2] = value;
    }
    get vy(): number {
        return this.field.vel[this.at * 2 + 1];
    }
    set vy(value: number) {
        this.field.vel[this.at * 2 + 1] = value;
    }
    get mass(): number {
        return this.field.mass[this.at];
    }
    set mass(value: number) {
        this.field.mass[this.at] = value;
    }
    get radius(): number {
        return this.field.radius[this.at];
    }
    set radius(value: number) {
        this.field.radius[this.at] = value;
    }
    get held(): boolean {
        return this.field.held[this.at] === 1;
    }
    set held(value: boolean) {
        this.field.held[this.at] = value ? 1 : 0;
    }
    get anchorX(): number | null {
        const value = this.field.anchor[this.at * 2];
        return Number.isFinite(value) ? value : null;
    }
    set anchorX(value: number | null) {
        this.field.anchor[this.at * 2] = value ?? Number.NaN;
    }
    get anchorY(): number | null {
        const value = this.field.anchor[this.at * 2 + 1];
        return Number.isFinite(value) ? value : null;
    }
    set anchorY(value: number | null) {
        this.field.anchor[this.at * 2 + 1] = value ?? Number.NaN;
    }
}

/* ------------------------------------------------------------- the px geometry - */

/**
 * The subject's own orb, in px.
 *
 * Larger than its neighbours by half again, which is the first of the five channels that carry
 * hierarchy here. The others are the accent ring it alone wears, always being labelled, the
 * heavier spoke lines that reach it, and being painted last so nothing can occlude it. None of
 * them is transparency, and that is deliberate: ARB-5 records that a ring drawn at the previous
 * 0.55 alpha cannot reach 3:1 against this product's page colour *for any palette*, so
 * recession has to come from size and from label suppression.
 */
export const ROOT_ORB_RADIUS = 16;

/**
 * A neighbour orb's largest radius, in px. `FOCUS_ORB_RADIUS`, which is where
 * `focusRingSeats` already assumes it is, so the budget and the layout cannot disagree.
 */
export const LEAF_ORB_RADIUS = FOCUS_ORB_RADIUS;

/** A neighbour orb's smallest radius, in px. Below this a mark stops reading as a mark. */
export const LEAF_ORB_MIN = 7;

/**
 * The smallest centre-to-centre distance the layout will seat two neighbours at, in px.
 *
 * Half `FOCUS_TOUCH_PITCH`, because the pitch is a *ring* pitch and this is the pairwise floor
 * that also has to hold between rings and after the relaxation has had its way.
 */
export const SEPARATION_MIN = FOCUS_TOUCH_PITCH / 2;

/** Clear space demanded between two orb edges, in px, on top of their radii. */
export const SEPARATION_PAD = 8;

/** Ring pitch and radial gap, in px. One number, so the arithmetic is the same both ways. */
export const RING_PITCH = FOCUS_TOUCH_PITCH;

/**
 * The radius the first ring prefers, in px.
 *
 * 96 rather than "as far out as the band allows". The median node in this artifact has six
 * distinct neighbours and the 90th percentile has twelve, so the overwhelmingly common scene is
 * small; seating six orbs on the band's rim draws a large empty circle with a dot in the middle
 * and nothing in between. The preference is overridden downward when the band is genuinely
 * shorter than 214 px, which focus.ts measured happening under a half-raised sheet.
 */
export const RING_PREFERRED = 96;

/**
 * How far a neighbour may drift from its slot, in px. See `Field.slack`.
 *
 * 7, and it is derived rather than chosen: the ring pitch is 44, the largest separation any
 * pair of neighbours can require is `2 * LEAF_ORB_RADIUS + SEPARATION_PAD` = 30, and two bodies
 * each free to wander 7 px can close at most 14 of the 44. That leaves exactly 30, so the floor
 * is tight - raising the slack by a pixel breaks the guarantee, and the assertion in
 * `tests/unit/local-physics.test.ts` is what will say so.
 */
export const SLOT_SLACK = 7;

/**
 * The closest the first ring may sit to the subject, in px.
 *
 * The subject's slack is zero - it holds the centre - so this only has to clear one body's
 * wander on top of the root-to-leaf requirement of `ROOT_ORB_RADIUS + LEAF_ORB_RADIUS +
 * SEPARATION_PAD`. A band short enough to want a tighter ring than this does not get one; it
 * gets a smaller budget, which is `focusBudgetForBand`'s job and not this function's.
 */
export const RING_FLOOR = ROOT_ORB_RADIUS + LEAF_ORB_RADIUS + SEPARATION_PAD + SLOT_SLACK;

/** The separation two orbs of these radii need, in px. */
export function requiredSeparation(a: PlanarNode, b: PlanarNode): number {
    return Math.max(SEPARATION_MIN, a.radius + b.radius + SEPARATION_PAD);
}

/**
 * The pair that comes closest to breaking the separation rule, and by how much.
 *
 * `slack` is positive where the rule holds. Reported per pair rather than as one number so a
 * failing assertion names the two marks instead of a statistic.
 */
export function worstSeparation(graph: PlanarGraph): {
    slack: number;
    distance: number;
    required: number;
    a: number;
    b: number;
} {
    let worst = { slack: Number.POSITIVE_INFINITY, distance: 0, required: 0, a: -1, b: -1 };
    const { nodes } = graph;
    for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
            const distance = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y);
            const required = requiredSeparation(nodes[i], nodes[j]);
            const slack = distance - required;
            if (slack < worst.slack) worst = { slack, distance, required, a: i, b: j };
        }
    }
    return worst;
}

/**
 * A neighbour's radius, from its own degree.
 *
 * Logarithmic because degree in this artifact spans 1 to 7,347 and a linear or cube-root map
 * spends the whole range on the top hundred nodes. Clamped at both ends: the floor keeps a
 * degree-1 record pickable and the ceiling keeps `requiredSeparation` bounded at
 * `2 * LEAF_ORB_RADIUS + SEPARATION_PAD`, which is what makes `SLOT_SLACK` provably safe at the
 * ring pitch.
 */
function leafRadius(degree: number): number {
    const scaled = LEAF_ORB_MIN + Math.log2(1 + Math.max(0, degree)) * 0.35;
    return Math.min(LEAF_ORB_RADIUS, Math.max(LEAF_ORB_MIN, scaled));
}

/**
 * Ring sizes and radii for N neighbours inside a band, in px.
 *
 * ## One ring, and it is the common case rather than the easy one
 *
 * Every scene this product ships draws a single ring, because `focusBudgetForBand` has already
 * reduced the neighbour count to what one ring can seat at the touch pitch. That is not a
 * forty-orb design with a small-N special case bolted on: the median node in this artifact has
 * **six** distinct neighbours and the 90th percentile has twelve, so six on one ring is the
 * shape this is tuned for, and forty is the 1.10% of connected nodes where curation engages at
 * all. At six the radius is `RING_PREFERRED` and the pitch is 100 px; at three it is 201 px.
 * Neither reads as sparse, because there is one ring and a hub rather than two thin shells with
 * three orbs each.
 *
 * ## Why the spill fills inward-out and not outward
 *
 * `FOCUS_BUDGET_MAX` is 200 and one spoke per shown neighbour is unconditional, so a reader who
 * keeps pressing "show more" on a wide band can ask for 200 orbs. The first version of this
 * function seated the first ring at the band's rim and spilled outward from there, which put
 * 200 orbs on rings at 367, 411, 455 and 499 px - a 1,020 px diagram in a 760 px band, and
 * therefore a diagram that had to be scaled down, and therefore a broken separation.
 *
 * Filling from `RING_FLOOR` outward instead packs concentrically: 200 orbs land on eight rings
 * from 42 to 350 px, a 722 px extent, at the full 44 px pitch. The single-ring case is
 * unaffected because it is taken first, and it is taken whenever one ring at the rim can seat
 * the whole set.
 */
function ringPlan(count: number, band: { width: number; height: number }) {
    const shortAxis = Math.max(120, Math.min(band.width, band.height));
    const outer = Math.max(RING_FLOOR, shortAxis / 2 - LEAF_ORB_RADIUS - 2);
    const preferred = Math.min(RING_PREFERRED, outer);
    const rings: Array<{ radius: number; count: number; offset: number }> = [];
    /* Staggered half a seat on alternate rings, so two rings never line up radially and the gap
       a reader looks through is never a straight corridor of orbs. */
    const seat = (radius: number, take: number) => ({
        radius,
        count: take,
        offset: rings.length % 2 === 0 ? 0 : Math.PI / take,
    });

    const wanted = (RING_PITCH * count) / (2 * Math.PI);
    if (count > 0 && wanted <= outer) {
        rings.push(seat(Math.max(wanted, preferred), count));
        return rings;
    }

    let remaining = count;
    let radius = RING_FLOOR;
    while (remaining > 0) {
        const seats = Math.max(1, Math.floor((2 * Math.PI * radius) / RING_PITCH));
        const take = Math.min(remaining, seats);
        rings.push(seat(radius, take));
        remaining -= take;
        radius += RING_PITCH;
    }
    return rings;
}

/**
 * Ring order: neighbours of the same relationship family adjacent, then by salience.
 *
 * ARB-6 forbids drawing community geometry over a node-link layout, and it is right to - Jianu
 * et al. measured about 25% worse accuracy on network tasks from encoding group membership over
 * one. An *ordering* is not geometry: nothing is drawn, no boundary is asserted, and a reader
 * who does not notice it loses nothing. What it buys is that the four evidence records sit
 * beside each other rather than alternating with the four deities, which is free.
 */
function ringOrder(shown: readonly FocusNeighbour[]): FocusNeighbour[] {
    const familyRank = (neighbour: FocusNeighbour) => {
        let best = Number.POSITIVE_INFINITY;
        for (const family of neighbour.families) {
            best = Math.min(best, FAMILY_INDEX.get(family) ?? Number.POSITIVE_INFINITY);
        }
        return best;
    };
    return [...shown].sort(
        (a, b) => familyRank(a) - familyRank(b) || b.salience - a.salience || a.node - b.node,
    );
}

/* ---------------------------------------------------------------- focus scene - */

/**
 * The subject and its curated neighbours, seated on px rings.
 *
 * ## The neighbourhood is not chosen here
 *
 * It arrives from `focus.ts`, which both renderers read. That is the whole point: "the same
 * neighbourhood remains selected when switching renderers" cannot be true of two modules that
 * each pick their own. The one this replaced ranked by raw degree over two rings and drew, on
 * Indra, **84 nodes and 487 edges of which only 43 touched the root** - the other 440 being the
 * ring-one-to-ring-one mesh, which is the hairball the world view already shows better. The
 * curated set is 41 nodes and 68 lines on the same subject.
 *
 * ## What the slots guarantee
 *
 * A neighbour sits at its slot plus at most `SLOT_SLACK`, so two neighbours on the same ring are
 * at least `pitch - 2 * SLOT_SLACK` apart. With the pitch at `RING_PITCH` and slack at 7 that is
 * 30 px, which is exactly `2 * LEAF_ORB_RADIUS + SEPARATION_PAD`. The clamp is positional, not
 * a force, which is why this is a floor and not a hope.
 */
export function buildFocusScene(
    world: World,
    neighbourhood: FocusNeighbourhood,
    band: { width: number; height: number },
): PlanarGraph {
    const root = neighbourhood.subject.index;
    const ordered = ringOrder(neighbourhood.shown);
    const rings = ringPlan(ordered.length, band);

    const ids = [root, ...ordered.map((neighbour) => neighbour.node)];
    const index = new Map(ids.map((id, i) => [id, i]));

    /* Spokes first, then the lines between neighbours. `focus.ts` has already applied both
       caps, so nothing here may drop a line: a shown neighbour with no line to the subject is
       an unattached dot in a view whose whole claim is "this is what the subject is attached
       to". */
    const spokes = neighbourhood.spokes.filter((spoke) => index.has(spoke.node));
    const between = neighbourhood.between.filter(
        (line) => index.has(line.a) && index.has(line.b),
    );

    const field = createField({
        dims: 2,
        count: ids.length,
        edges: spokes.length + between.length,
        tuning: tuningFor(2),
    });

    const nodes: PlanarNode[] = [];
    nodes.push(
        new PlanarBody(
            field,
            0,
            root,
            world.nodeGroup[root],
            world.nodeDegree[root],
            0,
            1,
            null,
            false,
        ),
    );
    field.seed[0] = root;
    field.pos[0] = 0;
    field.pos[1] = 0;
    field.anchor[0] = 0;
    field.anchor[1] = 0;
    field.radius[0] = ROOT_ORB_RADIUS;
    /* Mass rises with connectedness but slowly: a hub should feel weightier to pull, not
       immovable. */
    field.mass[0] = 1 + Math.cbrt(world.nodeDegree[root]) * 0.5;
    /* The subject holds the centre. Zero slack rather than a soft anchor, because a Focus
       diagram whose middle wanders is a diagram with no middle - and because it is what makes
       `RING_FLOOR` only have to clear one body's wander instead of two. A drag still moves it:
       `held` bypasses the clamp, and letting go returns it. */
    field.slack[0] = 0;

    let seated = 0;
    const radiusOfRing: number[] = [];
    for (const ring of rings) {
        for (let k = 0; k < ring.count; k += 1) {
            const neighbour = ordered[seated];
            const at = seated + 1;
            /* Anticlockwise from straight up, so the most salient neighbour of the first
               family is at the top of the diagram on every subject and a reader coming back to
               one they have seen finds it where they left it. */
            const angle = -Math.PI / 2 + ring.offset + (k / ring.count) * Math.PI * 2;
            const x = Math.cos(angle) * ring.radius;
            const y = Math.sin(angle) * ring.radius;
            field.seed[at] = neighbour.node;
            field.pos[at * 2] = x;
            field.pos[at * 2 + 1] = y;
            field.anchor[at * 2] = x;
            field.anchor[at * 2 + 1] = y;
            field.radius[at] = leafRadius(neighbour.degree);
            field.mass[at] = 1 + Math.cbrt(neighbour.degree) * 0.5;
            field.slack[at] = SLOT_SLACK;
            nodes.push(
                new PlanarBody(
                    field,
                    at,
                    neighbour.node,
                    world.nodeGroup[neighbour.node],
                    neighbour.degree,
                    1,
                    1,
                    null,
                    false,
                ),
            );
            radiusOfRing[at] = ring.radius;
            seated += 1;
        }
    }

    const edges: PlanarEdge[] = [];
    for (const spoke of spokes) {
        const b = index.get(spoke.node) as number;
        edges.push({ a: 0, b, edge: spoke.edge, rest: radiusOfRing[b], bridge: false, weight: 1 });
    }
    for (const line of between) {
        const a = index.get(line.a) as number;
        const b = index.get(line.b) as number;
        /* Rest length is the distance between the two slots, so the spring agrees with the
           arrangement instead of hauling it back toward a knot - the failure the first version
           of this view shipped. */
        const rest = Math.hypot(
            field.pos[a * 2] - field.pos[b * 2],
            field.pos[a * 2 + 1] - field.pos[b * 2 + 1],
        );
        edges.push({ a, b, edge: line.edge, rest, bridge: false, weight: 1 });
    }
    edges.forEach((edge, i) => {
        field.edgeA[i] = edge.a;
        field.edgeB[i] = edge.b;
        field.edgeRest[i] = edge.rest;
    });

    const guarantee = Math.max(
        SEPARATION_MIN,
        2 * LEAF_ORB_RADIUS + SEPARATION_PAD,
    );
    return { nodes, edges, index, rootId: root, field, authored: true, guarantee, spacing: 1 };
}

/** How much further out one press of "space it out" pushes the slots. */
export const RESPACE_STEP = 1.4;

/**
 * Give the same neighbours more room, or hand the room back.
 *
 * ## Why this action exists, and why it is not "show more"
 *
 * Because there is genuinely unused room, and it is the common case that has it. The first ring
 * sits at `RING_PREFERRED` whenever the neighbour count does not need more, so the median
 * subject - six neighbours - occupies a 214 px circle inside a band that at 1440x760 could seat
 * a 734 px one. That is the right default: six orbs on the rim of the band is a large empty
 * circle with a dot in the middle. But a reader looking closely at those six has a real reason
 * to want them further apart, and it is a different want from "show me more of them".
 *
 * It **cannot** widen the curated set. Same neighbours, same angles, same family ordering, same
 * rank: the only thing that changes is the radius. Adding neighbours is the tier expansion,
 * which passes the previous set as `pinned` so the tiers nest.
 *
 * ## It cycles rather than saturating
 *
 * Because the alternative is a control that silently stops working. One press goes out by
 * `RESPACE_STEP`, and the press that would exceed what the band can hold goes back to the
 * authored layout instead. So every press changes the diagram, the action is reversible without
 * a second control, and the diagram never leaves the reader's band - which is the constraint
 * the arrangement is held to rather than shrinking the separation, the same trade `fit` makes.
 *
 * ## The separation invariant holds throughout, not only afterwards
 *
 * Not by luck. This is a radial scaling that leaves every angle untouched, so on any ring the
 * chord between two neighbours is `2 * R * sin(pi / N)` with only `R` changing; the minimum over
 * a transition is therefore the minimum at whichever end has the smaller radius, and both ends
 * are configurations this function has already bounded. The slack is widened for the flight so
 * the anchor springs can actually carry the marks out - the clamp would otherwise snap them
 * there in one step - and `settleSlots` puts it back when the field comes to rest.
 *
 * Returns the multiplier now in force.
 */
export function respaceFocusScene(
    graph: PlanarGraph,
    band: { width: number; height: number },
    options: { instant?: boolean } = {},
): number {
    const { field } = graph;
    if (graph.rootId === null || field.count < 2) return graph.spacing;

    const shortAxis = Math.max(120, Math.min(band.width, band.height));
    const outer = Math.max(RING_FLOOR, shortAxis / 2 - LEAF_ORB_RADIUS - 2);
    let furthest = 0;
    for (let i = 0; i < field.count; i += 1) {
        const ax = field.anchor[i * 2];
        const ay = field.anchor[i * 2 + 1];
        if (!Number.isFinite(ax) || !Number.isFinite(ay)) continue;
        furthest = Math.max(furthest, Math.hypot(ax, ay));
    }
    if (furthest <= 0) return graph.spacing;

    const ceiling = (outer / furthest) * graph.spacing;
    const wanted = graph.spacing * RESPACE_STEP;
    /* Within two per cent of the ceiling there is nothing left to give, so the press returns
       the diagram instead of pretending to move it. */
    const target = wanted > ceiling * 0.98 ? 1 : wanted;
    const factor = target / graph.spacing;
    if (Math.abs(factor - 1) < 1e-6) return graph.spacing;

    for (let i = 0; i < field.count; i += 1) {
        const ax = field.anchor[i * 2];
        const ay = field.anchor[i * 2 + 1];
        if (!Number.isFinite(ax) || !Number.isFinite(ay)) continue;
        field.anchor[i * 2] = ax * factor;
        field.anchor[i * 2 + 1] = ay * factor;
        if (options.instant) {
            field.pos[i * 2] *= factor;
            field.pos[i * 2 + 1] *= factor;
        } else if (field.slack[i] > 0) {
            field.slack[i] = Math.hypot(ax * factor, ay * factor) + SLOT_SLACK;
        }
    }
    for (let e = 0; e < field.edgeCount; e += 1) field.edgeRest[e] *= factor;
    for (const edge of graph.edges) edge.rest *= factor;
    graph.spacing = target;
    return target;
}

/**
 * Put the slot clamps back after a re-space has flown. See `respaceFocusScene`.
 *
 * Focus scenes only. The world scene's anchors are the artifact's projected centres, which
 * `relaxOverlaps` deliberately moved away from by up to 44 px to stop the discs overlapping;
 * clamping those bodies to their anchors would hand that overlap straight back.
 */
export function settleSlots(graph: PlanarGraph): void {
    if (graph.rootId === null) return;
    const { field } = graph;
    for (let i = 0; i < field.count; i += 1) field.slack[i] = i === 0 ? 0 : SLOT_SLACK;
}

/* ---------------------------------------------------------------- world scene - */

/** Smallest disc radius in px, which is a pickability floor rather than an encoding. */
export const DISC_RADIUS_BASE = 6;

/** Disc radius per square root of a member count, in px. */
export const DISC_RADIUS_GAIN = 0.34;

/** Clear space demanded between two disc edges, in px. */
export const DISC_PAD = 8;

/** The world scene's margin inside the band, in px. */
const DISC_MARGIN = 44;

function discRadius(members: number): number {
    return DISC_RADIUS_BASE + Math.sqrt(members) * DISC_RADIUS_GAIN;
}

/**
 * A constellation's caption, or null where it has none worth drawing.
 *
 * 17 of this artifact's 33 constellations are named "passage cluster", "Rigvedic · passage
 * cluster" or "Atharvavedic · passage cluster" - the build's own honest description of a group
 * that is genuinely mixed. Drawing that beside a disc asserts a distinction a reader cannot
 * use, three times over on the same screen. Those keep their number, which is available on
 * hover, and carry no label. The 16 that remain are the ones worth a name.
 *
 * 17 is **counted**, by matching every `constellations[].name` in `public/world/world.json`
 * against this predicate, rather than taken from the phase's research summary, which put it at
 * 12. The figures differ by five and the count is the one that decides how many labels reach
 * the declutterer, so it is worth saying which it is.
 */
export function constellationCaption(constellation: Constellation): string | null {
    const name = constellation.name;
    if (!name) return null;
    return /passage cluster$/i.test(name) ? null : name;
}

/**
 * The corpus as its constellations, one disc each.
 *
 * ## Why not the nodes
 *
 * Because the projection this replaced was not legible and could not be made legible. Measured
 * on the real artifact at 1440x760: 2,600 marks whose nearest-neighbour projected separation
 * was **0.45 px at the 5th percentile and 2.05 px at the median** against drawn radii of
 * 2.59-12.69 px - total overplotting - of which **1,988 (76%) were passages**, because the cut
 * was the top 2,600 by raw degree and a passage's degree counts the metre and the mandala that
 * contain it. Of 22,095 eligible edges it drew 5,200, and the 16,895 it dropped were dropped
 * **by artifact index order**, so the lines on screen were not the important ones, they were
 * the early ones. Its own importance tier was dead: the degree floor of the top 2,600 is 15 and
 * the faint bucket was `degree < 14`, so every node was drawn at the same weight.
 *
 * ## What a disc does and does not claim
 *
 * It is a mark whose area encodes a member count, not a hull over a node-link layout. ARB-6
 * allows the first and forbids the second, on Jianu, Rusu, Hu & Taggart (TVCG 20(11) 2014, ~800
 * subjects): visually encoding group membership over a node-link diagram costs **about 25%
 * accuracy on network tasks**, and the only component with positive evidence is a prominent
 * group label. So there is no hull, no contour, and - the condition ARB-6 attached to letting
 * these discs ship at all - **no fill by dominant group**. `group` is -1 and the painter uses
 * one neutral ink. The 25% figure is recorded here so the next reader knows the cost was weighed
 * rather than missed.
 *
 * The radius is `6 + 0.34 * sqrt(members)`. Area would encode membership exactly at a zero
 * offset; the 6 px floor is what keeps the smallest of the 33 pickable, and it compresses a
 * 29.8-fold membership range into a 7.5-fold area range. A reader who needs the exact number
 * gets it from the mark, not from its size.
 *
 * ## Why the discs are relaxed rather than projected
 *
 * The constellation centres are 3D and this is a plane. Dropping z puts constellation 1 at
 * (126.0, 91.7) and constellation 13 at (103.8, 95.2) - 248 units apart in the world and 22.5
 * apart on screen - so the straight projection overlaps the two largest discs by 85 px at
 * 1440x760 and 37 px at 390x620. `relaxOverlaps` anneals away from the projection until nothing
 * overlaps, and keeps 93-99% of the original left-to-right ordering doing it, so this is still
 * recognisably the world the spatial view draws from above.
 */
export function buildWorldScene(
    world: World,
    band: { width: number; height: number },
): PlanarGraph {
    const constellations = world.manifest.constellations ?? [];
    const field = createField({ dims: 2, count: constellations.length, edges: 0 });
    if (constellations.length === 0) {
        /* No fallback layout. An artifact built before constellations existed draws nothing
           here and the view says so, which is a statement a reader can act on; a silent second
           arrangement of some other node set would be a different picture wearing this one's
           name. */
        return {
            nodes: [],
            edges: [],
            index: new Map(),
            rootId: null,
            field,
            authored: true,
            guarantee: null,
            spacing: 1,
        };
    }

    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const constellation of constellations) {
        minX = Math.min(minX, constellation.centre[0]);
        maxX = Math.max(maxX, constellation.centre[0]);
        minY = Math.min(minY, constellation.centre[1]);
        maxY = Math.max(maxY, constellation.centre[1]);
    }
    const scale = Math.min(
        (Math.max(240, band.width) - DISC_MARGIN * 2) / Math.max(1, maxX - minX),
        (Math.max(240, band.height) - DISC_MARGIN * 2) / Math.max(1, maxY - minY),
    );

    const nodes: PlanarNode[] = [];
    const index = new Map<number, number>();
    constellations.forEach((constellation, i) => {
        const x = (constellation.centre[0] - (minX + maxX) / 2) * scale;
        const y = (constellation.centre[1] - (minY + maxY) / 2) * scale;
        field.seed[i] = constellation.id;
        field.pos[i * 2] = x;
        field.pos[i * 2 + 1] = y;
        field.anchor[i * 2] = x;
        field.anchor[i * 2 + 1] = y;
        field.radius[i] = discRadius(constellation.size);
        field.mass[i] = 1;
        /*
         * The mark stands in for its most connected member, which is what a tap selects.
         *
         * `central[0]` rather than an arbitrary member: a reader who presses the Indra
         * constellation is taken to Indra, and from there Focus answers the question a disc
         * cannot. Picking a single node out of the plane at world scale is not an affordance
         * this view has ever really had - the target it offered was 2-5 px wide among 2,600
         * marks at 0.45 px separation - and search and Focus do that job properly.
         */
        const stands = constellation.central[0] ?? 0;
        const named = constellationCaption(constellation);
        index.set(stands, i);
        nodes.push(
            new PlanarBody(
                field,
                i,
                stands,
                -1,
                constellation.size,
                1,
                constellation.size,
                named ?? `Constellation ${constellation.id}`,
                named !== null,
            ),
        );
    });

    relaxOverlaps(field, { pad: DISC_PAD });

    /*
     * One line per pair of constellations, weighted by how many relationships bridge them.
     *
     * 82,240 of this artifact's edges are bridges and they fall into 515 constellation pairs,
     * the busiest carrying 3,303. Drawing them individually is the hairball; drawing one line
     * per pair is the statement a world map is for. The line carries `edge: -1` because it
     * stands for no single relationship, and nothing captions it.
     */
    const region = new Map<number, number>();
    constellations.forEach((constellation, i) => region.set(constellation.id, i));
    const weights = new Map<number, number>();
    for (let e = 0; e < world.manifest.counts.edges; e += 1) {
        if (world.edgeBridge[e] !== 1) continue;
        const a = region.get(world.nodeRegion[world.edgePairs[e * 2]]);
        const b = region.get(world.nodeRegion[world.edgePairs[e * 2 + 1]]);
        if (a === undefined || b === undefined || a === b) continue;
        const key = a < b ? a * constellations.length + b : b * constellations.length + a;
        weights.set(key, (weights.get(key) ?? 0) + 1);
    }
    const edges: PlanarEdge[] = [];
    for (const [key, weight] of weights) {
        const a = Math.floor(key / constellations.length);
        const b = key % constellations.length;
        edges.push({ a, b, edge: -1, rest: 0, bridge: true, weight });
    }
    edges.sort((x, y) => x.weight - y.weight);

    return { nodes, edges, index, rootId: null, field, authored: true, guarantee: null, spacing: 1 };
}

/* ------------------------------------------------------------------- the loop - */

/** One step of the simulation. See `stepField`; this binds it to two axes. */
export function stepPlanar(graph: PlanarGraph, dt = 1): number {
    return stepField(graph.field, dt);
}

export function isAtRest(energy: number) {
    return energy < PLANAR_TUNING.sleepEnergy;
}

/**
 * How many steps to run before the first paint of an authored scene.
 *
 * 60 was enough when the layout arrived as loose rings and only had to take the edge off. Slot
 * anchors converge faster than that, and a reduced-motion reader gets the settled arrangement
 * rather than a simulation they did not ask to watch, so the preroll runs until the field is at
 * rest or this many steps have passed - whichever comes first.
 */
export const PREROLL_LIMIT = 240;

/** Step until the field is at rest, or the limit runs out. Returns the steps used. */
export function preroll(graph: PlanarGraph, limit = PREROLL_LIMIT): number {
    for (let i = 0; i < limit; i += 1) {
        if (isAtRest(stepPlanar(graph))) return i + 1;
    }
    return limit;
}

/* ------------------------------------------------------------------- picking - */

/**
 * The smallest mark this view will draw, in px, however far out the reader has zoomed.
 *
 * The picker reads the same number, which is the point: the previous version drew at
 * `radius * clamp(scale, 0.7, 1.6)` and picked at `radius + 6` in *graph* units, so at the
 * measured fit scale of 0.16-0.34 a mark drawn 11-23 px across had a 2-5 px target. The mark
 * was lying about where the target was.
 */
export const MIN_MARK_PX = 3.5;

/** The radius a mark is drawn at, in CSS px, at a given view scale. */
export function markRadius(node: PlanarNode, scale: number): number {
    return Math.max(node.radius * scale, MIN_MARK_PX);
}

/**
 * The smallest hit target, in CSS px, per pointer.
 *
 * 22 for a finger is half `FOCUS_TOUCH_PITCH`, so the target and the seat pitch are the same
 * number and cannot drift apart. A mouse gets 12, which is above Fitts-comfortable for a
 * precise pointer and below the 22 that would make two adjacent orbs contend; a stylus sits
 * between them, as it does in `GESTURE_SLOP`.
 */
export const PICK_TARGET: Record<PointerKind, number> = {
    mouse: 12,
    pen: 16,
    touch: FOCUS_TOUCH_PITCH / 2,
};

export type PickOptions = {
    /** The view scale, so the target can be reasoned about in px. Defaults to 1. */
    scale?: number;
    /** Which pointer is asking. Defaults to a mouse. */
    pointer?: PointerKind;
};

/**
 * The node under a point, nearest first. The point is in graph coordinates; the tolerance is
 * in screen px, because that is where the reader's finger is.
 */
export function pickPlanar(
    graph: PlanarGraph,
    x: number,
    y: number,
    options: PickOptions = {},
): number | null {
    const scale = options.scale ?? 1;
    const target = PICK_TARGET[options.pointer ?? "mouse"];
    let best: number | null = null;
    let bestD = Number.POSITIVE_INFINITY;
    for (let i = 0; i < graph.nodes.length; i += 1) {
        const node = graph.nodes[i];
        const distance = Math.hypot(node.x - x, node.y - y) * scale;
        if (distance <= Math.max(markRadius(node, scale), target) && distance < bestD) {
            bestD = distance;
            best = i;
        }
    }
    return best;
}

/** The bounding box of the whole diagram, for fitting the viewport to it. */
export function planarBounds(graph: PlanarGraph) {
    const { min, max } = fieldBounds(graph.field);
    return { minX: min[0], minY: min[1], maxX: max[0], maxY: max[1] };
}

/* ----------------------------------------------------------- the test fixture - */

/**
 * A two-ring neighbourhood ranked by raw degree.
 *
 * ## This is not how a Focus scene is chosen any more
 *
 * `buildFocusScene` is, and it reads `focus.ts` - the one curated set both renderers share.
 * What survives here is the fixture the physics contract is asserted against:
 * `tests/unit/planar-physics.test.ts` builds a star by hand, with a `WorldManifest` cast from
 * two fields, and steps it. That test passing unmodified is how ARB-7's extraction is known not
 * to have changed the model, so it may not be rewritten to call the curated path - `focus.ts`
 * dereferences `manifest.edgeTypes`, which a hand-built fixture does not carry, and `focus.ts`
 * is not this module's to make defensive.
 *
 * So this function is deliberately kept, deliberately has no caller in `src/`, and deliberately
 * still selects by degree over two rings: it is a generator of graphs with hubs, leaves and a
 * few cross-links, which is what a force model wants to be tested against. Anything about the
 * product's neighbourhood curation belongs in `focus.ts` and nowhere near here.
 */
export function buildNeighbourhood(
    world: World,
    root: number,
    { ringOne = 48, ringTwo = 40 }: { ringOne?: number; ringTwo?: number } = {},
): PlanarGraph {
    const ring = new Map<number, number>([[root, 0]]);
    const byDegree = (a: number, b: number) => world.nodeDegree[b] - world.nodeDegree[a];

    const first: number[] = [];
    for (const edge of edgesOf(world, root)) {
        const other = otherEnd(world, edge, root);
        if (!ring.has(other)) first.push(other);
    }
    first.sort(byDegree);
    for (const node of first.slice(0, ringOne)) ring.set(node, 1);

    const second: number[] = [];
    for (const [node, depth] of [...ring]) {
        if (depth !== 1) continue;
        for (const edge of edgesOf(world, node)) {
            const other = otherEnd(world, edge, node);
            if (!ring.has(other)) second.push(other);
        }
    }
    second.sort(byDegree);
    for (const node of [...new Set(second)].slice(0, ringTwo)) {
        if (!ring.has(node)) ring.set(node, 2);
    }

    const ids = [...ring.keys()];
    const index = new Map(ids.map((id, i) => [id, i]));

    const counts = [0, 0, 0];
    for (const depth of ring.values()) counts[depth] += 1;
    /* The ring radius grows with how many have to fit on it: a subject with six neighbours and
       one with sixty should not put them on the same circle. */
    const ringRadius = [
        0,
        Math.max(150, counts[1] * 13),
        Math.max(300, counts[1] * 13 + counts[2] * 9),
    ];

    const seen = new Set<number>();
    const pairs: Array<{ a: number; b: number; edge: number; rest: number; bridge: boolean }> = [];
    for (const id of ids) {
        for (const edge of edgesOf(world, id)) {
            if (seen.has(edge)) continue;
            const a = world.edgePairs[edge * 2];
            const b = world.edgePairs[edge * 2 + 1];
            if (!index.has(a) || !index.has(b)) continue;
            seen.add(edge);
            const depth = Math.max(ring.get(a) ?? 0, ring.get(b) ?? 0);
            pairs.push({
                a: index.get(a) as number,
                b: index.get(b) as number,
                edge,
                rest: depth === 1 ? ringRadius[1] * 0.82 : ringRadius[2] * 0.5,
                bridge: world.edgeBridge[edge] === 1,
            });
        }
    }

    const field = createField({ dims: 2, count: ids.length, edges: pairs.length });
    const placed = [0, 0, 0];
    const nodes: PlanarNode[] = ids.map((id, i) => {
        const depth = ring.get(id) ?? 2;
        const radius = ringRadius[depth];
        const slot = placed[depth];
        placed[depth] += 1;
        const angle = (slot / Math.max(1, counts[depth])) * Math.PI * 2 + depth * 0.7;
        const degree = world.nodeDegree[id];
        field.seed[i] = id;
        field.pos[i * 2] = Math.cos(angle) * radius;
        field.pos[i * 2 + 1] = Math.sin(angle) * radius;
        field.mass[i] = 1 + Math.cbrt(degree) * 0.5;
        field.radius[i] = 4 + Math.cbrt(degree) * 1.5;
        if (depth === 0) {
            field.anchor[i * 2] = 0;
            field.anchor[i * 2 + 1] = 0;
        }
        return new PlanarBody(field, i, id, world.nodeGroup[id], degree, depth, 1, null, false);
    });

    const edges: PlanarEdge[] = pairs.map((pair, i) => {
        field.edgeA[i] = pair.a;
        field.edgeB[i] = pair.b;
        field.edgeRest[i] = pair.rest;
        return { ...pair, weight: 1 };
    });

    return {
        nodes,
        edges,
        index,
        rootId: root,
        field,
        authored: false,
        guarantee: null,
        spacing: 1,
    };
}
