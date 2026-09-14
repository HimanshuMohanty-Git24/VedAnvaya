import { edgesOf, otherEnd, type World, type WorldLabels } from "./artifact";
import { describePredicate, edgePredicate, type PredicateTable } from "./predicates";

/**
 * Which connections get named, which subjects get named, and where all of those words go.
 *
 * ## The problem this solves
 *
 * A reader hovers a subject and sees lines. Lines are not knowledge. They have to say what they
 * are - "is ascribed to the seer", "co-occurs with", "is in the metre" - and the moment you try
 * to do that at this scale two things go wrong at once.
 *
 * The first is volume. Indra carries 7,347 edges. Ten is roughly what a person can read on a
 * diagram they are also trying to understand the shape of, so at least 99.8% of them must go
 * unnamed, and *which* ones survive is the entire design.
 *
 * The second is that the obvious answer to the first is wrong. Ranking by the neighbour's degree
 * - show the most important connections - gives you ten labels that all read "is ascribed to
 * the seer", because that is what most of a passage-heavy hub's edges are. The reader learns one
 * fact ten times and still does not know that this subject also has metres, epithets and
 * parallels hanging off it.
 *
 * So the rule is coverage before rank: every *distinct kind* of relationship gets named once
 * before any kind is named twice. A hub with eleven predicates spends its first eleven slots
 * showing eleven different words, and only then starts doubling up. That turns the label set
 * from a sample into a summary, and it is the difference between decorating a hover and
 * answering it.
 *
 * ## One collision pass over both classes of label, not two
 *
 * Subject names and relationship phrases used to be placed by two systems that had never heard
 * of each other: a React component on a 160 ms timer for the names, and this file per frame for
 * the phrases. The phrases were then handed the names' boxes as obstacles, which sounds like a
 * fix and is not one, because a one-way contract cannot express a priority order. A relationship
 * under the pointer can never outrank a name that has already been placed, however much more the
 * reader wants to read it, and a name can never yield to one.
 *
 * They are now one pass with one integer order (see `LABEL_TIER`). That is the arbitrated design
 * for this phase - lead arbitration ARB-3 - which also supplies the two additions from the
 * literature that the pass ends with: a simulated-annealing finish and three-part hysteresis.
 * Both are implemented, with their sources, at `LabelLayout`.
 *
 * ## Renderer-agnostic on purpose
 *
 * Nothing here knows about WebGL, canvas or the DOM. Selection takes an artifact and a node;
 * layout takes points already projected into screen pixels by whoever did the projecting. That
 * is what lets the spatial view, the planar view and the path trace show the same connections
 * with the same words under the same cap - the alternative being three label systems that
 * quietly disagree about what a subject is attached to.
 */

/* ------------------------------------------------------------- what is named - */

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
 * The one priority order, across both classes of label.
 *
 * Integers rather than an enum because the comparison is arithmetic, and the gaps are the design:
 * a tier is a hard partition, and nothing inside a tier can climb out of it. The rules that fall
 * out of these eight numbers, in the order they matter:
 *
 *  - **You never lose the name of the thing you are looking at.** Selected (100) and hovered
 *    (80) names outrank every relationship. A diagram that drops the name of the subject under
 *    the pointer in favour of a phrase about it has answered a question nobody asked.
 *  - **The relationship being explained outranks everything but the subject's own name** (90).
 *    The inspector is open on it; that label is the thing the reader just clicked.
 *  - **A phrase under the pointer beats a bystander's name.** Hovered relations (70) sit above
 *    neighbour names (50), so the phrase places first and the neighbour's name yields. That
 *    inversion is the whole reason a single order was worth building: under two passes the name
 *    was always already on the canvas, so the phrase could only ever give way.
 *  - **A name still beats an off-pointer relationship.** Neighbour names (50) outrank other
 *    relations (40). In a settled scene the reader is orienting, not reading predicates.
 *  - **World hub names are the first thing to go** (10). They are wayfinding for a map nobody
 *    has asked a question of yet.
 */
export const LABEL_TIER = {
    SELECTED_NAME: 100,
    INSPECTED_RELATION: 90,
    PATH_STEP: 85,
    HOVERED_NAME: 80,
    HOVERED_RELATION: 70,
    NEIGHBOUR_NAME: 50,
    RELATION: 40,
    WORLD_HUB_NAME: 10,
} as const;

/**
 * At or above this tier a label is *reserved*: it is given a box before anything else is
 * considered, it is clamped into the viewport rather than dropped, and the annealer may not
 * touch it.
 *
 * Three things qualify - the selected subject's name, the relationship the inspector is open on,
 * and the steps of a traced route - and they have one property in common. Each is the answer to
 * a question the reader has just asked out loud, by selecting, by clicking a phrase, or by
 * tracing a route. Dropping one of those for a collision is not graceful degradation; it is the
 * interface declining to answer.
 */
export const RESERVED_TIER: number = LABEL_TIER.PATH_STEP;

/* ------------------------------------------------------------------------ caps - */

/**
 * The caps are legibility numbers, and it is worth being exact about that, because the natural
 * assumption is that they are performance numbers and they are not.
 *
 * Measured cost of a placed label, interleaved against a baseline (see
 * `scripts/bench-world.mjs --labels`), is 0.0068 ms per frame. Against a 16.7 ms frame:
 *
 *      10 labels    0.068 ms    0.41% of a frame
 *      24 labels    0.163 ms    0.98%
 *     100 labels    0.680 ms    4.1%
 *
 * So cost does not begin to bind until around a hundred, and every cap below is four to ten
 * times tighter than that. They are set by what a person can read on a diagram whose shape they
 * are also trying to take in, which is a far smaller number than what a browser can draw. The
 * probe these came from is recorded in the phase notes: at FOCUS on a real hub, a cap of 16 on
 * a 1440x900 canvas lands sixteen phrases whose boxes tile roughly a fifth of the canvas and the
 * diagram underneath stops being visible. Ten does not.
 *
 * The mobile numbers are half or less, not two thirds. A phone is a quarter of the desktop area,
 * and the same count over a quarter of the area is not a denser diagram but an unreadable one.
 */
export const FOCUS_LABEL_CAP = 10;
export const FOCUS_LABEL_CAP_COMPACT = 5;
export const WORLD_LABEL_CAP = 4;
export const WORLD_LABEL_CAP_COMPACT = 2;
export const PATH_LABEL_CAP = 6;
export const PATH_LABEL_CAP_COMPACT = 4;

/**
 * The ceiling across *both* classes at once, which is the number a reader actually experiences.
 *
 * The per-mode caps above govern relationship phrases only. This is what stops a scene with ten
 * phrases and twenty-two names from being thirty-two pieces of text over a diagram.
 */
export const TOTAL_LABEL_CAP = 24;
export const TOTAL_LABEL_CAP_COMPACT = 10;

/**
 * The one width at which this product becomes compact.
 *
 * It was 720 here and 768 everywhere else - `FOCUS_COMPACT_WIDTH` in `focus.ts`, the `47.99rem`
 * media queries in `world.css`, and the shell's own breakpoint. A phone held in landscape at
 * 740 px therefore got the desktop label cap inside the mobile layout, with the mobile sheet
 * over the bottom third of it. `tests/unit/edge-labels.test.ts` asserts this against `focus.ts`'s
 * constant, so the two cannot drift apart again without a failure.
 */
export const LABEL_COMPACT_WIDTH = 768;

export type LabelMode = "WORLD" | "FOCUS" | "PATH";

/** How many relationship phrases this mode may show at this width. */
export function edgeLabelBudget(viewportWidth: number, mode: LabelMode = "FOCUS"): number {
    const compact = viewportWidth < LABEL_COMPACT_WIDTH;
    if (mode === "WORLD") return compact ? WORLD_LABEL_CAP_COMPACT : WORLD_LABEL_CAP;
    if (mode === "PATH") return compact ? PATH_LABEL_CAP_COMPACT : PATH_LABEL_CAP;
    return compact ? FOCUS_LABEL_CAP_COMPACT : FOCUS_LABEL_CAP;
}

/** Every step of a route is named, up to the cap. */
export function pathLabelBudget(viewportWidth: number, steps: number): number {
    return Math.max(0, Math.min(steps, edgeLabelBudget(viewportWidth, "PATH")));
}

/** How many labels of both classes together may be on screen at this width. */
export function totalLabelCap(viewportWidth: number): number {
    return viewportWidth < LABEL_COMPACT_WIDTH ? TOTAL_LABEL_CAP_COMPACT : TOTAL_LABEL_CAP;
}

/* --------------------------------------------------------------- the selection - */

/**
 * Pull the edge indices out of `focus.ts`'s spokes.
 *
 * Structurally typed rather than importing `FocusSpoke`, because `focus.ts` is a client module
 * that imports React and this one is neither and has to stay usable from a plain script.
 */
export function spokeEdges(spokes: ArrayLike<{ edge: number }>): Uint32Array {
    const out = new Uint32Array(spokes.length);
    for (let i = 0; i < spokes.length; i += 1) out[i] = spokes[i].edge;
    return out;
}

/**
 * Choose which of a subject's connections to name.
 *
 * Two passes over the eligible edges. The first groups them by predicate and orders each group
 * by the far node's degree, so that within a kind the most substantial example leads. The second
 * deals the groups out round-robin: one from each kind, then a second from each kind, until the
 * budget is spent.
 *
 * Ordering the groups themselves by rarity - fewest edges first - is deliberate. A subject with
 * 5,000 passage attributions and one exact parallel should show the parallel; it is the
 * surprising fact, and the attributions will still be represented by their own single slot.
 *
 * ## Rarity is counted over the whole incident set, not over what was passed in
 *
 * This sort used to read `picks.length`, counted over `edges`. That is right only while `edges`
 * is the subject's whole neighbourhood, and it stopped being that when `focus.ts` began curating
 * what the scene draws. Curation's entire purpose is to *flatten* the predicate histogram:
 * measured on a 7,347-edge hub with eleven kinds, a per-predicate cap of 8 hands this function
 * group sizes of (8, 8, 8, 8, 8) - a five-way tie in which the tie-break, a `localeCompare` on
 * the predicate name, silently decided which rare relationship led. The ordering was
 * alphabetical and looked deliberate.
 *
 * So rarity is read from `edgesOf(world, node)` - the corpus figure, which is what makes a
 * parallel surprising - while eligibility is still read from `edges`. One extra pass over the
 * incident set, off the frame path, and the two questions stop being conflated.
 */
export function pickEdgeLabels(
    world: World,
    table: PredicateTable | null,
    node: number,
    limit: number = FOCUS_LABEL_CAP,
    /**
     * The connections eligible to be named. Defaults to all of them.
     *
     * Callers pass what they are actually drawing. In FOCUS that is `focus.ts`'s `spokes` - see
     * `spokeEdges` - rather than the raw incident set: a subject's 7,347 edges are not 7,347
     * lines on the canvas, and naming one that is not drawn puts a phrase beside whichever
     * unrelated line happens to pass under it.
     *
     * Curation and the coverage deal below are complementary rather than redundant, and it is
     * worth recording why, because they look like the same idea applied twice. Curation
     * diversifies the *drawn* forty; it does not diversify the *labelled* ten. Measured on the
     * same hub, from a curated forty with a per-predicate cap of 4: ranking by salience alone
     * names ten relationships covering four distinct kinds (HAS_RISHI x4, CONTAINS x4), while
     * the coverage deal names ten covering ten. At a cap of 8 it is four kinds against five.
     * The coverage pass stays.
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

    /* Rarity in the corpus rather than in the subset - see the note on `edges`. Counted only for
       the kinds that survived curation, so this is one pass and a handful of map writes. */
    const incident = new Map<string, number>();
    for (const edge of edgesOf(world, node)) {
        const predicate = edgePredicate(world, edge);
        if (!predicate || !byPredicate.has(predicate)) continue;
        incident.set(predicate, (incident.get(predicate) ?? 0) + 1);
    }

    const degree = (pick: EdgeLabelPick) => world.nodeDegree[pick.other] ?? 0;
    const groups = [...byPredicate.entries()]
        .map(([predicate, picks]) => ({
            predicate,
            picks: picks.sort((a, b) => degree(b) - degree(a)),
            /* The subset size is the floor rather than zero, because a caller may pass edges
               that are not in `edgesOf` at all - the planar view passes its own projection's
               edge list - and a kind with a zero count would sort ahead of a genuinely unique
               one. */
            rarity: Math.max(incident.get(predicate) ?? 0, picks.length),
        }))
        // Rarest kind first, ties broken by name so a rebuild cannot reorder the world.
        .sort((a, b) => a.rarity - b.rarity || a.predicate.localeCompare(b.predicate));

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

/* --------------------------------------------------- the same pass, as prose - */

/** One relationship, as a panel row. */
export type RelationRow = {
    /** Index into the world edge arrays. The identity the inspector opens on. */
    edge: number;
    /** The node at the far end. */
    other: number;
    otherLabel: string;
    predicate: string;
    /** The curated phrase, or a humanised predicate name where the table has none. */
    phrase: string;
    /** True where the subject is the stored source, which fixes the reading order. */
    outgoing: boolean;
    /**
     * True where the label pass chose to write this phrase on the canvas.
     *
     * This is what makes the panel's count and the canvas's count one number rather than two
     * guesses: both come from the single `pickEdgeLabels` call below.
     */
    named: boolean;
    /** True where the predicate carries a curated "what this establishes" sentence. */
    explained: boolean;
};

/**
 * Recorded against shown, for one subject, from the same selection pass that drew the labels.
 *
 * Three numbers, and they are three different numbers on purpose. A reader told "7,347
 * connections" beside a diagram showing forty lines and ten phrases has been told something true
 * and useless; the useful statement names all three and how they relate. This project has a
 * recorded lesson that a result carrying only positive rows lets the reader infer a false zero,
 * and a second that a metric row's keys are labels rather than counts. Both apply here:
 * `recorded` is the denominator and has to be stated even when it dwarfs the rest.
 */
export type RelationSummary = {
    /** Every edge incident on the subject in the artifact. The denominator. */
    recorded: number;
    /** Distinct kinds of relationship recorded, named or not. */
    kinds: number;
    /** Edges the visualisation is drawing as lines, after curation and the line caps. */
    drawn: number;
    /**
     * Of those, how many carry a phrase on the canvas.
     *
     * This is the cap, not the collision result. It is a deterministic function of the subject
     * and the viewport and does not move when the camera does, which is what lets React read it
     * without a per-frame `setState`. The post-collision figure is inherently per-frame:
     * `EdgeLabelView.shownLabels()` reports it for the benchmark and the end-to-end gate, and
     * `EdgeLabelView.onPlacedCount` pushes it to React once per settle rather than once a frame.
     */
    named: number;
    /** Every drawn relationship, named ones first, in the order the canvas ranked them. */
    rows: RelationRow[];
};

/**
 * Everything a relations-first panel list needs, computed by the same call the canvas makes.
 *
 * The panel used to build its own list out of `WorldSelection.neighbours`, which is a
 * deduplicated array of node indices - so edge identity was thrown away before the panel saw it,
 * and the accessible list named *subjects* where the reader had asked about *relationships*.
 * There was no keyboard path to a relationship at all: the only way to open one was to click a
 * phrase on the canvas, and that layer is `aria-hidden` by design and has to stay that way.
 *
 * Calling this once and reading both `named` and `rows` off it is what keeps "shown in the
 * current visualisation" honest. Two independent counts of one thing is how this codebase
 * previously ended up with an audit block that disagreed with its own rows.
 */
export function describeRelations(input: {
    world: World;
    labels: WorldLabels | null;
    table: PredicateTable | null;
    /** The subject. */
    node: number;
    /**
     * The edges the visualisation is drawing. `spokeEdges(neighbourhood.spokes)` in FOCUS,
     * `engine.drawnEdgesOf(node)` in the spatial world view, the projection's own edge list in
     * the planar one. Defaults to the whole incident set.
     */
    drawn?: ArrayLike<number>;
    /** The label cap for the current mode and width. See `edgeLabelBudget`. */
    limit?: number;
}): RelationSummary {
    const { world, labels, table, node } = input;
    if (node < 0 || node >= world.manifest.counts.nodes) {
        return { recorded: 0, kinds: 0, drawn: 0, named: 0, rows: [] };
    }

    const incident = edgesOf(world, node);
    const drawn = input.drawn ?? incident;
    const limit = input.limit ?? FOCUS_LABEL_CAP;

    const picks = pickEdgeLabels(world, table, node, limit, drawn);
    const namedEdges = new Set(picks.map((pick) => pick.edge));

    /* Every drawn edge becomes a row, whether or not it won a phrase. A list of only the named
       ones would tell the reader that ten relationships exist. */
    const all = pickEdgeLabels(world, table, node, Math.max(drawn.length, 1), drawn);
    const rows: RelationRow[] = all.map((pick) => {
        const semantics = describePredicate(table, pick.predicate);
        return {
            edge: pick.edge,
            other: pick.other,
            otherLabel: labels?.labels[pick.other] ?? `Subject ${pick.other}`,
            predicate: pick.predicate,
            phrase: pick.text,
            outgoing: pick.outgoing,
            named: namedEdges.has(pick.edge),
            explained: semantics?.basis === "CURATED",
        };
    });

    return {
        recorded: incident.length,
        kinds: countEdgeKinds(world, node),
        drawn: rows.length,
        named: picks.length,
        rows,
    };
}

/* ---------------------------------------------------------- where the words go - */

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

/**
 * The four places a subject's name may sit relative to its orb: an offset, and which corner of
 * the box the offset is measured from. Best first.
 *
 * Right-of-the-orb is first because that is where a reader of a left-to-right script looks for a
 * caption, and because it is where the name has always sat here; moving every name in the scene
 * to gain a little room would be a worse trade than dropping one. The order is also the a-priori
 * position preference the annealing objective charges for, so a name in the fourth quadrant
 * costs the layout something and has to be earning it.
 */
export const NAME_QUADRANTS = [
    { dx: 9, dy: 0, anchorX: 1, anchorY: 0 },
    { dx: -9, dy: 0, anchorX: -1, anchorY: 0 },
    { dx: 9, dy: 13, anchorX: 1, anchorY: 0 },
    { dx: -9, dy: -13, anchorX: -1, anchorY: 0 },
] as const;

export type LabelKind = "relation" | "name";

/** A rectangle in CSS pixels, top-left origin. Anything already inked on the canvas. */
export type LabelRect = { x: number; y: number; width: number; height: number };

/** A candidate position for a label: the point it hangs from, and how it hangs off it. */
export type LabelCandidate = {
    x: number;
    y: number;
    /**
     * Which edge of the box sits on (x, y). `0` centres it, `1` puts its left edge there, `-1`
     * its right edge. Relationship phrases centre on their point; a name hangs off one side of
     * an orb, so it needs to say which.
     */
    anchorX?: -1 | 0 | 1;
    anchorY?: -1 | 0 | 1;
    /**
     * False where this particular position is off the canvas.
     *
     * Unusable candidates stay in the array rather than being filtered out, and the reason is the
     * per-frame half of the pipeline. A label's chosen candidate is remembered as an *index*, so
     * the frame that moves it can look the position back up without re-running the assignment -
     * and an array that changes length as positions slide off screen makes that index mean a
     * different place from one frame to the next. Which is how a phrase comes to sit on the wrong
     * line while still reading as though it were placed deliberately.
     */
    usable?: boolean;
};

/** A label offered to the layout, of either class. */
export type LabelAnchor = {
    /**
     * Stable across frames, and unique across both classes.
     *
     * Identity is what makes hysteresis possible, so the two classes must not collide in this
     * space. A relationship uses its edge index, a path hop uses `-1 - step`, and a name uses
     * `nameKey(node)`, which is offset clear of both.
     */
    key: number;
    kind: LabelKind;
    /** See `LABEL_TIER`. A hard partition: nothing inside a tier can climb out of it. */
    tier: number;
    /**
     * Ordering within the tier, 0..1, higher first. Salience, degree, deal order - whatever the
     * caller ranks by. Incumbency adds to this and never to the tier.
     */
    weight: number;
    text: string;
    /** Candidate positions, best first. */
    candidates: LabelCandidate[];
    /** False where the renderer knows the point is behind the camera or otherwise unusable. */
    usable: boolean;
};

/** Where a label was put. */
export type PlacedLabel = {
    key: number;
    kind: LabelKind;
    tier: number;
    text: string;
    /** The ink box: top-left, in CSS pixels. What gets drawn. */
    x: number;
    y: number;
    width: number;
    height: number;
    /**
     * The guard box: the ink box grown to the touch minimum, and what collision is tested
     * against.
     *
     * Not a detail. A 44 px pad around a 17 px chip is nearly three times its ink height, so two
     * chips that look comfortably apart have overlapping pads - and the one later in the document
     * wins the tap, invisibly. That defect class has now shipped twice in this codebase: once
     * here, and once on the view and renderer control rows, where 44 px pads overlapped by
     * 15.8 px at 390 px wide and a tap inside the word "World" changed the renderer. Colliding on
     * the ink box and padding afterwards reproduces it exactly, which is why the collision test
     * and `countOverlaps` both read these four numbers and never the ink.
     */
    hitX: number;
    hitY: number;
    hitWidth: number;
    hitHeight: number;
    /** Which candidate was used. Latched per key, so a name never changes side mid-view. */
    candidate: number;
    /** True where the box had to be pushed inside the viewport. Reserved tiers only. */
    clamped: boolean;
};

/** What one assignment produced. */
export type LabelFrame = {
    placed: PlacedLabel[];
    /** Labels with a usable anchor that were not placed. The literature's "point selection". */
    dropped: number;
    /**
     * Overlapping pairs among the placed guard boxes.
     *
     * Zero, except where two reserved-tier labels were both clamped into the same corner of a
     * viewport too small to hold them - which is a choice, stated at `RESERVED_TIER`, rather than
     * a collision the layout failed to notice. Those pairs are excluded and nothing else is.
     */
    overlaps: number;
    /** Annealing bookkeeping, for the benchmark and for the test that it converges. */
    anneal: { stages: number; moves: number; accepted: number; energy: number };
};

/**
 * Kept clear of the viewport edge so a label is never half a word.
 *
 * There is no chip padding constant here any more, and its absence is the fix for a defect the
 * end-to-end gate caught. The layout used to add `PADDING_X = 6` and `PADDING_Y = 3` on each side
 * of the measured text - but the ruler is a span carrying the label's own class, so `offsetWidth`
 * and `offsetHeight` already include the chip's CSS padding and its border. Every box was
 * therefore twelve pixels wider and six taller than the thing that got painted.
 *
 * Conservative, so it never let two labels touch. But the guard box is centred on the reserved
 * box, so a 44 px guard around an over-reserved 24 px box put only 10 px of pad on each side of an
 * 18 px chip - a 38 px touch target that the layout believed was 44. Measured on the real DOM at
 * 390 px and 1440 px, both failing. The reserved box is now the painted box.
 */
const MARGIN = 4;

/**
 * Inflation applied to every box in the overlap test, and nowhere else.
 *
 * Two boxes that merely touch are legible; two that share a pixel of padding read as one word
 * with a seam in it. Four pixels is the smallest gap at which the phrase set's own descenders
 * stopped visually joining at `--va-text-2xs`. The chips' CSS padding is unchanged - this is a
 * layout-time gutter, not a style.
 */
export const GUTTER = 4;

/**
 * The touch minimum, and the reason the guard box exists at all.
 *
 * A relationship label is the only way into a relationship on the canvas, because the line it
 * names is one pixel wide and asking someone to hit one is asking them to fail. Measured, the
 * chip is about 17 px tall on a phone at `--va-text-2xs`, which is well under every published
 * touch minimum and fell outside the audit that cleared this product's chrome, because that audit
 * covered the chrome and the panel. Padded to 44, and collided at 44.
 *
 * ## It applies to targets only, and that distinction is load-bearing
 *
 * A subject name is not a control. It is `pointer-events: none` and always has been, so there is
 * nothing to hit and nothing to keep 44 px clear of. Applying this floor to both classes was
 * measured against the real scene and was badly wrong: a 40 x 17 name grew a 48 x 44 guard box,
 * nearly tripling its area, and the consequences were visible on both viewports.
 *
 *   - Desktop 1440x900, Focus on Indra: **one relationship phrase placed against a cap of ten**,
 *     with nine names taking the whole total. Names outrank plain relations by tier, so
 *     over-reserved names simply consumed the canvas.
 *   - Phone 390x844, Focus on Indra: **two labels of any kind** against a total cap of ten.
 *
 * Which is the opposite of what this subsystem exists to do. A name is collided at the legibility
 * gutter and nothing more; a phrase, which is a target, is collided at 44.
 */
export const TOUCH_MIN = 44;

/**
 * How much larger a clear zone a *newcomer* needs than an incumbent's.
 *
 * Vaaraniemi, Treib & Westermann (COM.Geo 2012) report that asymmetric padding of about this
 * ratio "greatly stabilizes the labeling layout": a label already on screen is tested with the
 * plain guard, and a label trying to get on is tested with a larger one, so the threshold to
 * enter sits strictly above the threshold to stay. Without it, two labels whose boxes graze trade
 * one slot at frame rate.
 */
const NEWCOMER_PADDING = 1.5;

/**
 * Incumbency, as weight and never as tier.
 *
 * A label already on screen is compared with a bonus, so a rival has to be meaningfully better
 * to take its place rather than a rounding error better. Half a unit is chosen to be larger than
 * any weight difference that can occur inside a tier - weights are normalised to 0..1 - and
 * smaller than the smallest tier gap, which is 10. That arithmetic is the guarantee that
 * incumbency cannot promote a label past a whole class of label that outranks it.
 */
const INCUMBENCY = 0.5;

/**
 * How long a dropped label must wait before it may come back.
 *
 * Vaaraniemi et al.'s third ingredient: MapLibre's 300 ms `fadeDuration` as the crossfade, with
 * a re-entry cooldown of 600-900 ms over the top of it. 750 is the midpoint.
 */
export const REENTRY_COOLDOWN_MS = 750;

/** The crossfade, on entry and on exit. MapLibre's `fadeDuration` default. */
export const FADE_MS = 300;

/* --------------------------------------------------------------- the annealer - */

/**
 * Christensen, Marks & Shieber's schedule, copied rather than re-derived.
 *
 * ACM TOG 14(3), 1995, measured on their own 750-feature map: random placement left 564
 * overlaps, greedy depth-first 341, gradient descent 222, Zoraster's integer program 219, and
 * simulated annealing 75. It was also the second-shortest program in their table - 239 lines
 * against 1,807 for 2-opt - which is the other half of why it is the right finish here rather
 * than something cleverer.
 *
 * `T0 = 1 / ln 3` is their initialisation, and it is worth writing it down in both forms because
 * a reader checking the constant against one and finding the other will assume a bug. Acceptance
 * of an uphill move is `e^(-dE/T)`, so at `dE = 1` and `T = 1/ln 3` a move is accepted with
 * probability 1/3. The arbitration quotes the rejection form, `P = 1 - e^(-dE/T) = 2/3`. Same
 * number.
 */
const T0 = 1 / Math.log(3);
const MOVES_PER_STAGE = 20;
const COOLING = 0.9;
const EARLY_DROP_ACCEPTS = 5;
const MAX_STAGES = 50;

/**
 * How many labels beyond the total cap the annealer may consider moving.
 *
 * ARB-3 costed the schedule "at n = 8-24" and concluded single-digit thousands of rect tests,
 * which is microseconds. That holds at n = 24 and not above it, because the cost is quadratic and
 * not linear: the schedule spends `20n` moves per stage and each move is evaluated against the
 * other n - 1 labels, so the work goes as n squared.
 *
 * Measured, before this bound existed. The offered set was up to 24 phrases plus 48 names, so
 * n ran to about 70, and `LabelLayout.place` took **9.4 ms** on a real Focus scene at the desktop
 * cap - more than half a frame, for a scene that can only show 24 of them. A label ranked
 * thirty-third by tier and weight cannot win a slot in a 24-slot assignment, so every move spent
 * on it is spent for nothing.
 *
 * Eight is slack rather than zero so that the annealer can still substitute: a label just outside
 * the cap must be able to take the place of one just inside it when that turns out to be the
 * better arrangement, which is a real move and is the whole reason point selection is in the
 * objective.
 */
const ANNEAL_SLACK = 8;

/** What one overlapping pair costs the objective. Overlaps are the thing being minimised. */
const W_OVERLAP = 1;
/** What each step down the candidate list costs. The a-priori position preference. */
const W_POSITION = 0.06;
/** What leaving a label unplaced costs, scaled by its tier. Point selection, as a term. */
const W_DROP = 0.9;

/**
 * A seeded generator, because a layout that is not reproducible is not testable.
 *
 * Annealing needs randomness; the scene does not. Two identical settles must anneal to the same
 * answer, or an unrelated re-render moves every label for no reason the reader can see and the
 * end-to-end collision gate becomes a coin toss. xorshift32, seeded from the scene's own shape.
 */
function seeded(seed: number) {
    let s = seed | 0 || 0x2f6e2b1;
    return () => {
        s ^= s << 13;
        s ^= s >>> 17;
        s ^= s << 5;
        return ((s >>> 0) % 0xff_ffff) / 0xff_ffff;
    };
}

/* ------------------------------------------------------------------- the keys - */

/** Big enough to clear the artifact's edge count - 146,899 today - with room to spare. */
const NAME_KEY_BASE = 1_000_000_000;

/** A name's layout key, offset clear of every edge index and every path hop. */
export function nameKey(node: number): number {
    return NAME_KEY_BASE + node;
}

/** The node a name key refers to. */
export function nodeOfNameKey(key: number): number {
    return key - NAME_KEY_BASE;
}

/** True where a key came from `nameKey`. */
export function isNameKey(key: number): boolean {
    return key >= NAME_KEY_BASE;
}

/**
 * True where a key came from a path hop rather than an artifact edge.
 *
 * The spatial view keys hops as `-1 - step`, which is also how the inspector knows not to look
 * one up: a hop is not one edge in the world file.
 */
export function isPathKey(key: number): boolean {
    return key < 0;
}

/** Which step of a route a path key refers to, one-based, for the numeral on the label. */
export function pathStepOf(key: number): number {
    return -key;
}

/* ------------------------------------------------------------------ the layout - */

type Slot = {
    anchor: LabelAnchor;
    /** Every candidate resolved to a box, plus whether the viewport had to clamp it. */
    boxes: Array<{ box: LabelRect; guard: LabelRect; clamped: boolean; usable: boolean }>;
    /** Index into `boxes`, or `boxes.length` for "unplaced". */
    at: number;
    incumbent: boolean;
    /** Held off screen by the re-entry cooldown. Not the annealer's to overrule. */
    barred: boolean;
    /** Tier, weight and incumbency, resolved into one number for the greedy sort. */
    rank: number;
};

/**
 * Screen-space placement for both classes of label, with a memory.
 *
 * ## The shape of the pass
 *
 * 1. **Reserved tiers first.** Tier >= `RESERVED_TIER` gets a box before anything else is
 *    considered, and is clamped into the viewport rather than dropped.
 * 2. **Greedy by priority.** Everything else in tier-then-weight order, each taking the first of
 *    *its own* candidates that is clear. This is the base the arbitration kept.
 * 3. **Annealing finish.** The greedy answer is the annealer's initial state, and the annealer
 *    may move any non-reserved label to any of its candidates or to nothing at all. Schedule and
 *    source above.
 * 4. **Hysteresis**, three parts, applied throughout: asymmetric padding, a one-active-interval
 *    rule, and a cooldown before re-entry. The 300 ms crossfade is the view's half of it.
 *
 * ## What was removed, and what it cost
 *
 * Two escapes used to let a label through *in collision*, and both were asserted as desired
 * behaviour by the tests that are being replaced:
 *
 *  - A label inside its 300 ms dwell was pushed while overlapping. Probed: two labels shown, one
 *    overlapping pair, for up to 300 ms. The intent was right - a phrase that blinks draws the
 *    eye to the blink rather than to the word - but overlapping is not the way to pay for it.
 *    Fading is, and the fade now lives in the view where it belongs.
 *  - A `tolerated` fallback accepted a phrase *on top of* a subject name when no candidate was
 *    clear, on the theory that a name is a soft obstacle. Probed true. That is the two-pass
 *    design showing through: with one order the phrase simply outranks the name it needs to sit
 *    on and the name yields, which is a better answer than two overlapping pieces of text.
 *
 * Both are gone, and `tests/e2e/graph-labels.spec.ts` now reads every visible box of both classes
 * and asserts zero overlapping pairs. That assertion is the only thing that keeps a unified pass
 * honest, because the failure mode of getting this wrong is not a crash but a diagram that looks
 * slightly wrong to somebody who is not measuring.
 *
 * ## Cost
 *
 * No spatial index. At the total cap of 24 an all-pairs test is 276 comparisons, and each
 * annealing move is evaluated incrementally against the other 23; a grid or a quadtree would have
 * to be rebuilt for every move and costs more than it saves at this n. Measured figures are in
 * the report for this phase.
 */
export class LabelLayout {
    /** Keys placed by the previous assignment. */
    private incumbents = new Set<number>();
    /** Which candidate each key is latched to, until it is dropped. */
    private latched = new Map<number, number>();
    /** When each key was last dropped, for the cooldown. */
    private droppedAt = new Map<number, number>();
    /**
     * Been et al.'s presence intervals: how many times a key has been switched on during the
     * current continuous run of being offerable at all.
     */
    private activations = new Map<number, number>();
    private offered = new Set<number>();
    private measured = new Map<string, { width: number; height: number }>();

    /** Text measurement is expensive and the phrase set is tiny, so it is cached by string. */
    private sizeOf(
        text: string,
        kind: LabelKind,
        measure: (text: string, kind: LabelKind) => { width: number; height: number },
    ) {
        const cacheKey = `${kind}|${text}`;
        const known = this.measured.get(cacheKey);
        if (known !== undefined) return known;
        const size = measure(text, kind);
        this.measured.set(cacheKey, size);
        return size;
    }

    /** Called when the subject changes, so a new selection does not inherit old incumbents. */
    reset(): void {
        this.incumbents.clear();
        this.latched.clear();
        this.droppedAt.clear();
        this.activations.clear();
        this.offered.clear();
    }

    /** Called when the font or its size changes, which invalidates every cached measurement. */
    invalidateMeasurements(): void {
        this.measured.clear();
    }

    /** Which keys the last assignment placed. The view drives its crossfade off this. */
    get placedKeys(): ReadonlySet<number> {
        return this.incumbents;
    }

    /**
     * Run one assignment.
     *
     * Not per frame. ARB-3 splits the pipeline: per frame the view updates `transform` on
     * already-placed labels and nothing else, and this runs on a debounced settle. That split is
     * what makes the annealer affordable and the hysteresis meaningful. It is also the rule that
     * "labels are never placed against moving geometry" - placing mid-transition is how a phrase
     * ends up describing the line it was next to two frames ago.
     */
    place(input: {
        anchors: LabelAnchor[];
        viewport: { width: number; height: number };
        measure: (text: string, kind: LabelKind) => { width: number; height: number };
        /**
         * Boxes already inked on the canvas by something that cannot be asked to move.
         *
         * The planar view draws its subject names into the 2D context during its own draw pass,
         * before this runs, so those names are facts rather than candidates and are treated as
         * immovable obstacles above every tier. That is a real asymmetry with the spatial view,
         * where names now arrive as anchors and can yield: in the planar view a phrase can still
         * be the thing that loses. Closing it means that renderer deciding its names *after* this
         * pass rather than before it, which is its own call to make.
         */
        reserved?: LabelRect[];
        /** The ceiling across both classes. See `totalLabelCap`. */
        total?: number;
        /**
         * How much of `total` is reserved for relationship phrases. See `edgeLabelBudget`.
         *
         * A reservation and not a ceiling, and the difference was measured. With one total cap and
         * names ranked above plain relations, the names take every slot before a single phrase is
         * considered: on Indra at 1440x900 that produced **nine names and one phrase** against a
         * phrase cap of ten. The cap was never reached, because the budget it was drawn from had
         * already been spent by the other class.
         *
         * This is the same correction ARB-8 makes to neighbour selection - two budgets rather than
         * one blended score - and for the same reason. A blend lets whichever class ranks higher
         * consume the other's share entirely, and the higher-ranking class here is always the
         * names.
         *
         * Slack transfers. A subject with two relationships must not hold eight empty phrase slots
         * while names go unplaced, so a second pass spends whatever the first left over.
         */
        relationBudget?: number;
        now?: number;
    }): LabelFrame {
        const { anchors, viewport, measure } = input;
        const reserved = input.reserved ?? [];
        const total = input.total ?? TOTAL_LABEL_CAP;
        /*
         * No budget given means no per-class reservation, and that distinction has to be explicit.
         * Defaulting the phrase share to `total` looks harmless and silently leaves the names a
         * share of zero, so a scene with one name and one phrase places the phrase and drops the
         * name however the tiers are set. Caught by the tier-order tests.
         */
        const shared = input.relationBudget !== undefined;
        const relationBudget = shared ? Math.min(input.relationBudget ?? total, total) : total;
        const now = input.now ?? performance.now();

        /* Presence intervals. A key that has stopped being offerable has ended its interval, so
           its activation count and its latch are forgotten and it may be shown freely the next
           time it appears. Without this, leaving a subject and coming back to it would find the
           old cooldowns still running. */
        const nowOffered = new Set<number>();
        for (const anchor of anchors) if (anchor.usable) nowOffered.add(anchor.key);
        for (const key of this.offered) {
            if (nowOffered.has(key)) continue;
            this.activations.delete(key);
            this.latched.delete(key);
            this.droppedAt.delete(key);
        }
        this.offered = nowOffered;

        const slots: Slot[] = [];
        for (const anchor of anchors) {
            if (!anchor.usable || anchor.candidates.length === 0) continue;
            /* The measurement is of a span carrying the label's own class, so it is already the
               painted box, padding and border included. Nothing is added to it. */
            const { width, height } = this.sizeOf(anchor.text, anchor.kind, measure);
            const incumbent = this.incumbents.has(anchor.key);
            const boxes = anchor.candidates.map((candidate) =>
                resolve(
                    candidate,
                    width,
                    height,
                    viewport,
                    anchor.tier >= RESERVED_TIER,
                    anchor.kind === "relation",
                ),
            );
            slots.push({
                anchor,
                boxes,
                at: boxes.length,
                incumbent,
                barred: false,
                rank: anchor.tier + Math.min(anchor.weight, 0.99) + (incumbent ? INCUMBENCY : 0),
            });
        }

        /* Tier and weight descending; key ascending, so a rebuild cannot reorder the world. */
        slots.sort((a, b) => b.rank - a.rank || a.anchor.key - b.anchor.key);

        /*
         * Been's criterion, in a cooldown-gated form rather than the strict one.
         *
         * Been et al.'s rule is that "each presence interval contains at most one active
         * interval": a label may not flicker within one period of being on screen. Applied
         * strictly, a label dropped once by a transient occlusion stays dropped for as long as
         * the camera sits still, which is the worse of the two failures - the reader is left with
         * a permanent hole instead of a brief one. So a key that has already been active in this
         * presence interval may return, but only after `REENTRY_COOLDOWN_MS`.
         *
         * The cost of that deviation is bounded and worth stating plainly: a label can toggle at
         * most once every 750 ms, or 1.3 Hz, against roughly 6 Hz for the 160 ms full
         * re-derivation this replaces.
         */
        for (const slot of slots) {
            if (slot.incumbent) continue;
            if ((this.activations.get(slot.anchor.key) ?? 0) === 0) continue;
            const dropped = this.droppedAt.get(slot.anchor.key);
            slot.barred = dropped !== undefined && now - dropped < REENTRY_COOLDOWN_MS;
        }

        const taken: LabelRect[] = [];
        /* Per-class shares, so neither class can spend the other's. Reserved tiers sit outside
           both: they are placed whatever happens, and then counted against their class. */
        const share = {
            relation: relationBudget,
            name: shared ? total - relationBudget : total,
        };
        const clear = (slot: Slot, guard: LabelRect) => {
            const grow = slot.incumbent ? 0 : NEWCOMER_PADDING - 1;
            const probe = grow === 0 ? guard : inflate(guard, grow);
            for (const other of reserved) if (hits(probe, other)) return false;
            for (const other of taken) if (hits(probe, other)) return false;
            return true;
        };

        /* 1 and 2. Reserved tiers, then greedy by priority - one loop, because the sort has
           already put every reserved tier at the front (the highest possible non-reserved rank is
           80 + 0.99 + 0.5 = 81.49, below 85). They differ only in not being refusable. */
        const consider = (slot: Slot, pass: "own" | "slack"): boolean => {
            const mustPlace = slot.anchor.tier >= RESERVED_TIER;
            if (!mustPlace) {
                if (taken.length >= total) return false;
                if (slot.barred) return true;
                if (pass === "own" && share[slot.anchor.kind] <= 0) return true;
            }

            /* First refusal on whatever it held last time. A label that keeps its position across
               a settle does not move at all, which is the cheapest kind of stability there is,
               and it is what latches a name's quadrant so quadrants never swap mid-view. */
            const latch = this.latched.get(slot.anchor.key);
            const order = slot.boxes.map((_, i) => i);
            if (latch !== undefined && latch < order.length) {
                order.splice(latch, 1);
                order.unshift(latch);
            }

            let chosen = -1;
            for (const i of order) {
                if (!slot.boxes[i].usable) continue;
                if (clear(slot, slot.boxes[i].guard)) {
                    chosen = i;
                    break;
                }
            }
            if (chosen < 0 && mustPlace) chosen = fallback(slot, latch);
            if (chosen < 0) return true;
            slot.at = chosen;
            taken.push(slot.boxes[chosen].guard);
            share[slot.anchor.kind] -= 1;
            return true;
        };

        /* First pass: each class inside its own share. Second: whatever the first left over, in
           the same priority order, so the slack goes to the best unplaced label of either class
           rather than to whichever class happens to be iterated first. */
        for (const slot of slots) if (!consider(slot, "own")) break;
        for (const slot of slots) {
            if (slot.at < slot.boxes.length) continue;
            if (!consider(slot, "slack")) break;
        }

        /*
         * 3. The annealing finish, told what the greedy pass achieved per class.
         *
         * The annealer minimises an objective in which leaving a label unplaced is a cost scaled
         * by its tier, so left to itself it will trade a relation out for a name: a name's drop
         * penalty is higher, and swapping one for the other lowers the energy by the difference.
         * Measured on the exact fixture the budget test uses - 10 phrases and 20 names, total 14,
         * phrase share 6 - the greedy pass placed 6 and 8 correctly and the annealer handed back
         * **1 phrase and 13 names**. Same failure as the cooldown: a constraint the greedy pass
         * applies is invisible to the annealer unless it is given to it.
         *
         * The cap per class is what was placed plus whatever of that class's share is left, so the
         * annealer may fill a share the greedy pass could not - a position it refused for a
         * collision the annealer can resolve - and may never exceed it.
         */
        const anneal = this.anneal(slots, reserved, total, viewport, {
            relation: countOf(slots, "relation") + Math.max(0, share.relation),
            name: countOf(slots, "name") + Math.max(0, share.name),
        });

        // 4. Bookkeeping, and the frame.
        const placed: PlacedLabel[] = [];
        const next = new Set<number>();
        for (const slot of slots) {
            if (slot.at >= slot.boxes.length) continue;
            placed.push(describePlacement(slot));
            next.add(slot.anchor.key);
            this.latched.set(slot.anchor.key, slot.at);
            if (!this.incumbents.has(slot.anchor.key)) {
                const key = slot.anchor.key;
                this.activations.set(key, (this.activations.get(key) ?? 0) + 1);
            }
        }
        for (const key of this.incumbents) if (!next.has(key)) this.droppedAt.set(key, now);
        this.incumbents = next;

        placed.sort((a, b) => b.tier - a.tier || a.key - b.key);

        return { placed, dropped: slots.length - placed.length, overlaps: countOverlaps(placed), anneal };
    }

    /**
     * The Christensen/Marks/Shieber finish, over the greedy answer.
     *
     * The objective is theirs, including point selection as a term rather than as a separate
     * phase: overlaps, plus an a-priori position preference, plus what is left unplaced, with the
     * drop penalty proportional to the tier so the annealer cannot buy a clear canvas by
     * silencing the subject's own name. Reserved tiers are frozen; they are not its business.
     *
     * The total cap is a constraint on the state rather than a term in the objective. A move that
     * would put a twenty-fifth label on screen is simply not available, which is cheaper than
     * pricing it and means the cap cannot be traded away for a few fewer overlaps.
     */
    private anneal(
        slots: Slot[],
        reserved: LabelRect[],
        total: number,
        viewport: { width: number; height: number },
        /** The most of each class the annealer may end up with. See the call site. */
        ceiling: Record<LabelKind, number>,
    ): LabelFrame["anneal"] {
        /* Reserved tiers are frozen, and so is anything the cooldown is holding off screen. The
           annealer minimises an objective in which leaving a label unplaced is a cost, so without
           the second exclusion it would immediately place a barred label - a free improvement by
           its own measure - and undo the hysteresis the greedy pass had just applied. This was
           measured as a real failure: the unit test for the cooldown failed with exactly one
           label on screen that the greedy pass had correctly refused. */
        /* Already sorted by tier, then weight, then key, so the truncation takes the best
           candidates and not an arbitrary prefix. See ANNEAL_SLACK for what it is worth. */
        const movable = slots
            .filter(
                (slot) => slot.anchor.tier < RESERVED_TIER && slot.boxes.length > 0 && !slot.barred,
            )
            .slice(0, total + ANNEAL_SLACK);
        const n = movable.length;
        if (n === 0) return { stages: 0, moves: 0, accepted: 0, energy: 0 };

        /* Seeded from the scene's shape rather than from a clock - see `seeded`. */
        let seed = (n * 2_654_435_761) ^ (viewport.width << 11) ^ viewport.height;
        for (const slot of movable) seed = (seed * 31 + slot.anchor.key) | 0;
        const random = seeded(seed);

        const maxTier = Math.max(...slots.map((slot) => slot.anchor.tier), 1);
        /** What a slot costs on its own: a drop penalty, or a preference for a worse position. */
        const own = (slot: Slot) =>
            slot.at >= slot.boxes.length
                ? W_DROP * (slot.anchor.tier / maxTier)
                : W_POSITION * slot.at;
        /** What a slot costs in overlaps. Counted once per pair from each end, hence the halving
            when it is summed over every slot below. */
        const pairs = (slot: Slot) => {
            if (slot.at >= slot.boxes.length) return 0;
            const grow = slot.incumbent ? 0 : NEWCOMER_PADDING - 1;
            const guard = slot.boxes[slot.at].guard;
            const probe = grow === 0 ? guard : inflate(guard, grow);
            let count = 0;
            for (const other of reserved) if (hits(probe, other)) count += 1;
            for (const other of slots) {
                if (other === slot || other.at >= other.boxes.length) continue;
                if (hits(probe, other.boxes[other.at].guard)) count += 1;
            }
            return W_OVERLAP * count;
        };
        const local = (slot: Slot) => own(slot) + pairs(slot);

        /* E = the sum of every slot's own cost, plus one unit per overlapping pair. Counted once
           per pair, which is why the initial value cannot be the sum of `local` - that counts
           each pair from both of its ends. The deltas are right either way, because a move only
           changes the pairs one slot is part of, but a reported energy that is off by the
           overlap count is a number somebody will later try to reconcile. */
        let energy = 0;
        for (const slot of slots) energy += own(slot);
        let overlapPairs = 0;
        for (const slot of slots) overlapPairs += pairs(slot);
        energy += overlapPairs / 2;

        /*
         * Best-so-far retention, which is a deliberate departure from the bare paper.
         *
         * Christensen et al. minimise overlaps as a soft objective over 750 map features, where
         * 75 residual overlaps is the winning result. Here the greedy pass has already produced a
         * *feasible* state - it never places a label in collision at all - so the annealer's job
         * is to improve the position preferences and the number placed, not to find feasibility.
         * Plain Metropolis can and does end a run worse than it started, because a late uphill
         * move is accepted and never undone; keeping the best state seen and restoring it at the
         * end makes the finish monotone, so this can never be worse than the greedy answer it was
         * given. That is what lets the end-to-end gate assert zero overlaps rather than "not many".
         */
        let bestEnergy = energy;
        const best = slots.map((slot) => slot.at);
        const remember = () => {
            bestEnergy = energy;
            for (let i = 0; i < slots.length; i += 1) best[i] = slots[i].at;
        };

        let temperature = T0;
        let stages = 0;
        let moves = 0;
        let accepted = 0;
        let count = 0;
        for (const slot of slots) if (slot.at < slot.boxes.length) count += 1;
        const perKind: Record<LabelKind, number> = {
            relation: countOf(slots, "relation"),
            name: countOf(slots, "name"),
        };

        for (; stages < MAX_STAGES; stages += 1) {
            let stageAccepts = 0;
            const budget = MOVES_PER_STAGE * n;
            for (let m = 0; m < budget; m += 1) {
                const pick = movable[Math.min(n - 1, Math.floor(random() * n))];
                const options = pick.boxes.length + 1;
                const to = Math.min(options - 1, Math.floor(random() * options));
                if (to === pick.at) continue;
                if (to < pick.boxes.length && !pick.boxes[to].usable) continue;
                const wasPlaced = pick.at < pick.boxes.length;
                const willPlace = to < pick.boxes.length;
                const kind = pick.anchor.kind;
                if (willPlace && !wasPlaced) {
                    if (count >= total) continue;
                    if (perKind[kind] >= ceiling[kind]) continue;
                }

                moves += 1;
                const before = local(pick);
                const was = pick.at;
                pick.at = to;
                const delta = local(pick) - before;

                if (delta <= 0 || random() < Math.exp(-delta / temperature)) {
                    energy += delta;
                    accepted += 1;
                    stageAccepts += 1;
                    const moved = (willPlace ? 1 : 0) - (wasPlaced ? 1 : 0);
                    count += moved;
                    perKind[kind] += moved;
                    if (energy < bestEnergy) remember();
                    if (stageAccepts >= EARLY_DROP_ACCEPTS * n) break;
                } else {
                    pick.at = was;
                }
            }
            temperature *= COOLING;
            /* Frozen. A whole stage without one accepted move means the schedule has nothing
               left to spend and the remaining stages are pure cost. */
            if (stageAccepts === 0) {
                stages += 1;
                break;
            }
        }

        for (let i = 0; i < slots.length; i += 1) slots[i].at = best[i];

        return { stages, moves, accepted, energy: Number(bestEnergy.toFixed(4)) };
    }
}

/* ------------------------------------------------------------------- geometry - */

/** How many labels of one class are currently placed. */
function countOf(slots: Slot[], kind: LabelKind): number {
    let n = 0;
    for (const slot of slots) {
        if (slot.anchor.kind === kind && slot.at < slot.boxes.length) n += 1;
    }
    return n;
}

function describePlacement(slot: Slot): PlacedLabel {
    const { box, guard, clamped } = slot.boxes[slot.at];
    return {
        key: slot.anchor.key,
        kind: slot.anchor.kind,
        tier: slot.anchor.tier,
        text: slot.anchor.text,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        hitX: guard.x,
        hitY: guard.y,
        hitWidth: guard.width,
        hitHeight: guard.height,
        candidate: slot.at,
        clamped,
    };
}

function resolve(
    candidate: LabelCandidate,
    width: number,
    height: number,
    viewport: { width: number; height: number },
    clampable: boolean,
    targetable: boolean,
): { box: LabelRect; guard: LabelRect; clamped: boolean; usable: boolean } {
    const ax = candidate.anchorX ?? 0;
    const ay = candidate.anchorY ?? 0;
    // -1 puts the box's trailing edge on the point, 0 centres it, 1 puts its leading edge there.
    const rawX = candidate.x - (ax === 0 ? width / 2 : ax === -1 ? width : 0);
    const rawY = candidate.y - (ay === 0 ? height / 2 : ay === -1 ? height : 0);
    const x = Math.min(Math.max(rawX, MARGIN), Math.max(MARGIN, viewport.width - width - MARGIN));
    const y = Math.min(Math.max(rawY, MARGIN), Math.max(MARGIN, viewport.height - height - MARGIN));
    /* Clamped rather than dropped: a label near the edge of the canvas is still the right answer
       about the right line, it just has to sit inside the frame. Reported, because two clamped
       reserved boxes in one corner are the single case where the zero-overlap guarantee is
       deliberately spent. */
    const clamped = clampable && (x !== rawX || y !== rawY);
    const box = { x, y, width, height };
    return {
        box,
        guard: guardBox(box, targetable),
        clamped,
        usable: candidate.usable !== false,
    };
}

/**
 * Where a reserved label goes when every one of its candidates is contested.
 *
 * Its latched position if it has one, otherwise its first usable candidate, otherwise the first.
 * It is being placed in collision, which is the choice `RESERVED_TIER` documents: the alternative
 * is the interface declining to name the thing the reader just selected.
 */
function fallback(slot: Slot, latch: number | undefined): number {
    if (latch !== undefined && latch < slot.boxes.length && slot.boxes[latch].usable) return latch;
    const usable = slot.boxes.findIndex((entry) => entry.usable);
    return usable >= 0 ? usable : 0;
}

/**
 * The ink box grown to whichever is larger of the touch minimum and the legibility gutter, in each
 * axis independently, centred on the ink. `targetable` is false for anything the reader cannot
 * click; see `TOUCH_MIN` for what applying the touch floor to a name cost when it was measured.
 *
 * Doing it per axis matters. A phrase chip is about 110 x 18, so the height needs 13 px of pad on
 * each side to reach 44 and the width needs only the 4 px gutter. Inflating both to 44 would
 * reserve half a screen of horizontal space for nothing.
 */
function guardBox(box: LabelRect, targetable: boolean): LabelRect {
    const floor = targetable ? TOUCH_MIN : 0;
    const width = Math.max(box.width + GUTTER * 2, floor);
    const height = Math.max(box.height + GUTTER * 2, floor);
    return {
        x: box.x - (width - box.width) / 2,
        y: box.y - (height - box.height) / 2,
        width,
        height,
    };
}

function inflate(box: LabelRect, factor: number): LabelRect {
    const dx = (box.width * factor) / 2;
    const dy = (box.height * factor) / 2;
    return { x: box.x - dx, y: box.y - dy, width: box.width + dx * 2, height: box.height + dy * 2 };
}

function hits(a: LabelRect, b: LabelRect): boolean {
    return (
        a.x < b.x + b.width &&
        a.x + a.width > b.x &&
        a.y < b.y + b.height &&
        a.y + a.height > b.y
    );
}

/**
 * Overlapping pairs, measured on the *guard* boxes.
 *
 * This is the number the end-to-end gate asserts is zero, and it is measured on the pad rather
 * than the ink for the reason recorded at `PlacedLabel.hitX`: adjacent pads that overlap let the
 * later label in the document steal the earlier one's taps, with nothing visible to show it.
 */
export function countOverlaps(placed: PlacedLabel[]): number {
    let pairs = 0;
    for (let i = 0; i < placed.length; i += 1) {
        for (let j = i + 1; j < placed.length; j += 1) {
            const a = placed[i];
            const b = placed[j];
            // Both clamped means both are reserved tiers in a viewport too small for them.
            if (a.clamped && b.clamped) continue;
            if (
                a.hitX < b.hitX + b.hitWidth &&
                a.hitX + a.hitWidth > b.hitX &&
                a.hitY < b.hitY + b.hitHeight &&
                a.hitY + a.hitHeight > b.hitY
            ) {
                pairs += 1;
            }
        }
    }
    return pairs;
}

/* -------------------------------------------------------------- naming subjects - */

/**
 * Which subjects get their name written, and where the name may sit.
 *
 * This is the half of the label problem that used to live in `world-labels.tsx`, a React
 * component on its own 160 ms timer with its own collision rule - a fixed 132 x 20 centre-distance
 * test against a `max-width` of 13rem, so a long constellation name was under-reserved and the
 * word "Agni" was over-reserved by a factor of four. That component is deleted; ARB-3 puts both
 * classes through one pass, and this function is what feeds the names into it.
 *
 * ## Why the offered set is bounded well below the artifact's six hundred hubs
 *
 * The annealer's cost is *quadratic* in the number of labels offered - `20n` moves per stage, each
 * evaluated against the other n - 1 - and the greedy pass orders them by degree, so offering six
 * hundred candidates for at most twenty-four slots buys nothing: the tail cannot win a slot and
 * every one of them still costs a measurement, a box and a place in the move distribution.
 *
 * Bounded at twice the total cap, which leaves the collision pass a real choice of alternatives.
 * `ANNEAL_SLACK` then bounds what the annealer will actually move, and records the 9.4 ms that
 * measured the difference.
 */
export type NameLayer = {
    mode: LabelMode;
    anchors: LabelAnchor[];
    /**
     * Which tier the scene's relationship phrases belong in.
     *
     * It lives here rather than on the renderer because this is the function that already knows
     * the whole subject situation. A phrase about the subject *under the pointer* is the reader
     * asking a question and outranks a bystander's name (70 > 50); a phrase about the subject
     * they have already chosen is ambient annotation and yields to one (40 < 50). A renderer
     * would have to be told the tier table to work that out, and would then be a third place
     * that could disagree about it.
     */
    relationTier: number;
};

export function nodeNameAnchors(input: {
    world: World;
    labels: WorldLabels | null;
    /** Screen position of a node's orb, or null where it is behind the camera. */
    positionOf: (node: number) => { x: number; y: number } | null;
    /** The chosen subject, whose name is a reserved tier. */
    selected: number | null;
    /** The subject under the pointer. */
    hovered: number | null;
    /** Neighbours worth naming, most important first - `focus.ts`'s `shown` order. */
    neighbours?: ArrayLike<number>;
    viewport: { width: number; height: number };
}): NameLayer {
    const { world, labels, positionOf, selected, hovered, viewport } = input;
    const neighbours = input.neighbours ?? [];
    const mode: LabelMode = selected === null ? "WORLD" : "FOCUS";
    const relationTier =
        selected === null && hovered !== null
            ? LABEL_TIER.HOVERED_RELATION
            : LABEL_TIER.RELATION;
    if (!labels) return { mode, anchors: [], relationTier };

    const ceiling = totalLabelCap(viewport.width) * 2;
    const anchors: LabelAnchor[] = [];
    const seen = new Set<number>();

    const offer = (node: number, tier: number, weight: number) => {
        if (node < 0 || seen.has(node) || anchors.length >= ceiling) return;
        const text = labels.labels[node];
        if (!text) return;
        const at = positionOf(node);
        seen.add(node);
        anchors.push({
            key: nameKey(node),
            kind: "name",
            tier,
            weight,
            text,
            /* Four quadrants rather than one fixed offset. A name that can move to the other side
               of its own orb is still unambiguously that orb's name, which is the same test the
               relationship fractions pass and the reason neither class is ever nudged somewhere
               it stops meaning what it says. */
            candidates: at
                ? NAME_QUADRANTS.map((quadrant) => ({
                      x: at.x + quadrant.dx,
                      y: at.y + quadrant.dy,
                      anchorX: quadrant.anchorX,
                      anchorY: quadrant.anchorY,
                  }))
                : [],
            usable: at !== null,
        });
    };

    if (selected !== null) offer(selected, LABEL_TIER.SELECTED_NAME, 1);
    if (hovered !== null) offer(hovered, LABEL_TIER.HOVERED_NAME, 1);
    for (let i = 0; i < neighbours.length; i += 1) {
        /* Weight descends with the caller's own order, which in FOCUS is salience. Normalised
           into 0..1 so it cannot reach across a tier gap; see `INCUMBENCY`. */
        offer(neighbours[i], LABEL_TIER.NEIGHBOUR_NAME, 1 - i / Math.max(neighbours.length, 1));
    }
    /* The artifact ships a hub index: the six hundred most connected subjects that are not
       passages or reified records, most connected first. Degree order means the ceiling cuts the
       least important names rather than arbitrary ones. */
    const hubs = world.manifest.hubs;
    for (let i = 0; i < hubs.length && anchors.length < ceiling; i += 1) {
        offer(hubs[i], LABEL_TIER.WORLD_HUB_NAME, 1 - i / Math.max(hubs.length, 1));
    }

    return { mode, anchors, relationTier };
}

/**
 * Resolve one candidate to its ink box, for the per-frame transform update.
 *
 * ARB-3 splits the pipeline: the assignment runs on a settle, and every frame in between only
 * moves the labels it already chose. So the frame path needs to turn a candidate into a box
 * without re-running the assignment, which is this - the same arithmetic, no collision test, no
 * clamp reporting.
 */
export function resolveCandidate(
    candidate: LabelCandidate,
    width: number,
    height: number,
    viewport: { width: number; height: number },
): LabelRect {
    return resolve(candidate, width, height, viewport, false, false).box;
}

/** The guard box for an ink box, so the view can size the invisible touch pad to match. */
export function guardOf(box: LabelRect, targetable = true): LabelRect {
    return guardBox(box, targetable);
}
