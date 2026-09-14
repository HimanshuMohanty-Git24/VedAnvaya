"use client";

import { useMemo } from "react";
import {
    describeSubject,
    edgesOf,
    otherEnd,
    type Subject,
    type World,
    type WorldLabels,
} from "./artifact";

/**
 * Which neighbours of a subject are worth drawing, and what is behind the ones that are not.
 *
 * ## The scene this file exists to prevent
 *
 * Indra has 7,347 recorded connections to 5,544 distinct subjects. Drawn as they are stored,
 * that is a disc of five and a half thousand dots in which 3,566 are passages that merely
 * name him and 606 are evidence records whose own labels embed a raw graph id. Nothing about
 * it is false and nothing about it is legible: the eleven other deities Indra co-occurs with,
 * the one rite, the one object and the one idea are in there, individually indistinguishable
 * from the wall of passages. A reader who came to find out what Indra is attached to learns
 * that he is attached to a great deal.
 *
 * Taking the most connected forty instead is worse, not better. Measured on Indra, the top
 * forty by degree are 294 edges between themselves - a hairball - and they cover 4 of the 13
 * relationship kinds and 3 of the 7 node groups on the subject. Ranking by prominence hides
 * exactly the rare relationships that carry the information.
 *
 * So the forty are chosen for *coverage* first: every relationship kind before any is shown
 * twice, every node group, then reach into other constellations, and only then rank. On Indra
 * at a budget of 40 that yields all 13 predicates, all 7 families, all 7 node groups and 17
 * of the 33 constellations he touches.
 *
 * ## The typical scene is six orbs, not forty
 *
 * Two figures were measured against this artifact and both are correct; consumers designing
 * layouts have to know which one they are designing against.
 *
 *   - 399 nodes have a *degree* above 40; 335 above 48.
 *   - 377 nodes have more than 40 *distinct neighbours*; 308 have more than 50.
 *
 * They differ because 16,631 nodes are joined to at least one neighbour by more than one
 * relationship, so degree overstates the number of dots to draw. Distinct neighbours is the
 * figure the budget is compared against, because the budget counts orbs.
 *
 * Either way the curation engages on roughly one node in a hundred: at budget 40 it truncates
 * 377 of 34,373 connected nodes, 1.10%. The median node over the whole artifact has 6
 * distinct neighbours (7 by degree), and the 90th percentile has 12. So the overwhelmingly
 * common FOCUS scene is a subject with six things around it, drawn complete, with nothing
 * hidden and no "show more" - and a layout tuned only for the forty-orb case will look wrong
 * on 99% of the corpus.
 *
 * ## Cost
 *
 * Nothing here may be called from a frame callback. `selectFocus` on Indra walks 7,347 edges
 * and allocates 5,544 candidate records; measured at 9.3 ms in its first form, and 0.9 ms
 * after the two optimisations described at `buildCandidates` and `sortCandidates`. That is
 * fifty-five frames of a sixty-hertz budget, or one, and neither belongs in a render loop.
 * It is computed once per selection, memoised by `useFocusNeighbourhood`, and read by the
 * renderers as data.
 */

/* -------------------------------------------------------------------- families - */

/**
 * The twelve kinds of relationship a reader is asked to distinguish, plus a total fallback.
 *
 * The artifact carries 48 predicate names and the exported vocabulary declares 60, which is
 * more distinctions than a sidebar can offer and more than the scholarship needs a reader to
 * hold. Twelve is the grouping the predicate phrasing itself falls into: `HAS_DEVATA` and
 * `HAS_RISHI` are both the tradition ascribing a hymn to somebody, `EXACT_PARALLEL_OF` and
 * `REUSES_TEXT_FROM` are both shared wording.
 *
 * Ordered by how directly the family answers "what is this subject", because that order is
 * the tiebreak in every round below and in the sidebar rows, and an order derived from the
 * data would move when the data did.
 */
export const RELATIONSHIP_FAMILIES = [
    "ATTRIBUTION",
    "MENTION",
    "TOPIC",
    "APPEAL",
    "COOCCURRENCE",
    "PARALLEL",
    "FORMULA",
    "RITE",
    "REGISTRY",
    "EVIDENCE",
    "PROSODY",
    "CONTAINMENT",
    "OTHER",
] as const;

export type RelationshipFamily = (typeof RELATIONSHIP_FAMILIES)[number];

/**
 * The twelve a subject's sidebar accounts for whether or not it has any.
 *
 * OTHER is excluded: it is the bucket an unmapped predicate falls into, so an "Other: none"
 * row states only that the mapping is complete, which is a fact about this file rather than
 * about the subject. It appears as a row when it carries edges, and not otherwise.
 */
export const ACCOUNTED_FAMILIES: readonly RelationshipFamily[] = RELATIONSHIP_FAMILIES.filter(
    (family) => family !== "OTHER",
);

export const FAMILY_INDEX: ReadonlyMap<RelationshipFamily, number> = new Map(
    RELATIONSHIP_FAMILIES.map((family, index) => [family, index]),
);

/**
 * A heading, and what to say when a subject has none of this family.
 *
 * `absent` is phrased as a statement about the record and never about possibility. "No metre
 * recorded" is true of Indra; "a deity cannot have a metre" would be this file inventing an
 * ontology rule, and the artifact does not carry one to check it against.
 */
export const FAMILY_COPY: Record<RelationshipFamily, { heading: string; absent: string }> = {
    ATTRIBUTION: { heading: "Ascribed by the tradition", absent: "No ascription recorded" },
    MENTION: { heading: "Named in", absent: "Not named in any passage" },
    TOPIC: { heading: "About", absent: "No subject matter recorded" },
    APPEAL: { heading: "Invoked and asked", absent: "No invocation recorded" },
    COOCCURRENCE: { heading: "Named alongside", absent: "Nothing recorded alongside" },
    PARALLEL: { heading: "Shared wording", absent: "No parallel wording recorded" },
    FORMULA: { heading: "Formulae", absent: "No formula recorded" },
    RITE: { heading: "Ritual use", absent: "No ritual use recorded" },
    REGISTRY: { heading: "Registry relations", absent: "No registry relation recorded" },
    EVIDENCE: { heading: "Evidence records", absent: "No evidence records" },
    PROSODY: { heading: "Metre", absent: "No metre recorded" },
    CONTAINMENT: { heading: "Where it sits", absent: "No container recorded" },
    OTHER: { heading: "Other", absent: "None" },
};

/**
 * Every predicate in both vocabularies, assigned to exactly one family.
 *
 * Total over the 48 edge types the artifact can draw *and* over the 12 further predicates
 * `world.predicates.json` declares but no edge carries today. Covering the declared-only
 * twelve costs nothing and means the day one of them starts carrying rows, the sidebar
 * already knows where to put it instead of dropping it into OTHER unnoticed.
 *
 * A predicate in two families throws at module load rather than resolving to whichever entry
 * was written last: a silently mis-filed predicate makes the coverage round believe it has
 * represented a family it has not, and the reader loses a whole kind of relationship with no
 * symptom. `tests/unit/focus-curation.test.ts` asserts totality against both files, so adding
 * a predicate to the ontology fails a test rather than landing quietly in OTHER.
 */
const FAMILY_PREDICATES: Record<RelationshipFamily, readonly string[]> = {
    ATTRIBUTION: ["HAS_DEVATA", "HAS_RISHI", "HAS_DEVATA_ASCRIPTION"],
    MENTION: ["MENTIONS_DEVATA", "MENTIONS_ENTITY"],
    TOPIC: [
        "ABOUT_CONCEPT", "ADDRESSES_CONCERN", "HAS_THEME", "TREATS", "DESCRIBES",
        "DESCRIBES_ACTION", "CONTRASTS_WITH", "REFERS_TO_NATURAL_PHENOMENON",
        "REFERS_TO_PLACE", "CONCERNS",
    ],
    APPEAL: ["INVOKES", "INVOKES_DEVATA", "PRAISES", "REQUESTS", "PROTECTS_FROM", "IS_ASKED_TO"],
    COOCCURRENCE: ["CO_OCCURS_WITH"],
    PARALLEL: [
        "EXACT_PARALLEL_OF", "NEAR_PARALLEL_OF", "PARALLEL_TO", "VARIANT_OF",
        "REUSES_TEXT_FROM", "SHARES_ENTITY_VOCABULARY_WITH",
    ],
    FORMULA: ["USES_FORMULA", "HAS_FORMULA", "MEMBER_OF_FAMILY"],
    RITE: [
        "USED_FOR_RITE", "DESCRIBED_IN", "INVOLVES_RITUAL", "INVOLVES_OFFERING",
        "INVOLVES_SUBSTANCE", "USES_OBJECT", "USES_OFFERING", "USES_SUBSTANCE",
        "PERFORMED_BY", "PERFORMED_FOR", "HAS_STEP", "PERFORMS_ACTION",
    ],
    REGISTRY: [
        "COMPOSED_OF", "EPITHET_VARIANT_OF", "BROADER_THAN", "DEVATA_ASSOCIATED_WITH",
        "BELONGS_TO_FAMILY", "HAS_AXIS", "HAS_EPITHET", "MEMBER_OF",
    ],
    EVIDENCE: [
        "HAS_SEMANTIC_ASSERTION", "ASSERTION_AGENT", "ASSERTION_TARGET", "MEASURES",
        "CONTRADICTS", "SUPPORTED_BY", "SUPPORTED_BY_STATISTIC",
    ],
    PROSODY: ["HAS_CHANDAS"],
    CONTAINMENT: ["CONTAINS"],
    OTHER: [],
};

function buildPredicateFamily(): Map<string, RelationshipFamily> {
    const table = new Map<string, RelationshipFamily>();
    for (const family of RELATIONSHIP_FAMILIES) {
        for (const predicate of FAMILY_PREDICATES[family]) {
            const existing = table.get(predicate);
            if (existing) {
                throw new Error(
                    `relationship families: ${predicate} is in both ${existing} and ${family}`,
                );
            }
            table.set(predicate, family);
        }
    }
    return table;
}

export const PREDICATE_FAMILY: ReadonlyMap<string, RelationshipFamily> = buildPredicateFamily();

/**
 * The family a predicate belongs to. Total: an unmapped name is OTHER, and OTHER is a row.
 *
 * Returning OTHER rather than null is the whole point. A predicate this table has not heard
 * of still exists in the graph, its edges still count towards the subject's degree, and a
 * lookup that returned null would invite every caller to skip it - at which point the
 * sidebar's family totals no longer sum to the degree and nothing says why.
 */
export function familyOfPredicate(predicate: string): RelationshipFamily {
    return PREDICATE_FAMILY.get(predicate) ?? "OTHER";
}

/* --------------------------------------------------------------------- budgets - */

/**
 * How many neighbours a Focus scene draws before it starts curating.
 *
 * 40 is the desktop default. Measured over the 335 nodes the curation engages on, a 40-orb
 * scene draws a median of 52 lines and at worst 123 (the "demon" node, degree 484); at 48 the
 * worst case is 147, which is where a scene stops reading as a subject with relationships and
 * starts reading as a mesh.
 */
export const FOCUS_BUDGET = 40;

/**
 * The narrow-viewport budget.
 *
 * 16, and it is not an arbitrary halving. It is the measured *coverage floor*: over all 335
 * curated nodes, the smallest budget that still shows every predicate, every family and every
 * node group the subject has is 4 at the median, 12 at the 99th percentile and 16 at the
 * worst case, which is Indra. So 16 is the smallest budget at which no subject in this corpus
 * loses a kind of relationship - below it, curation stops being a choice about crowding and
 * starts withholding information.
 */
export const FOCUS_BUDGET_COMPACT = 16;

/**
 * The floor when even the compact budget will not physically seat.
 *
 * 12 is the 99th-percentile coverage floor: 331 of the 335 curated nodes still show every
 * relationship kind they have at 12. Four do not - Indra, Agni, Vayu and AVS 6.125.2 - and
 * that is the stated cost of a band this short.
 */
export const FOCUS_BUDGET_CRAMPED = 12;

/** One press of "show more". */
export const FOCUS_EXPAND_STEP = 20;

/**
 * The ceiling on expansion.
 *
 * 200, not the subject's degree. Expansion is additive by construction (see ROUND 0), so a
 * reader can keep pressing; the cap is where the scene has stopped being able to answer any
 * question that a list could not answer better. Indra would need 139 presses to exhaust his
 * neighbours and the last hundred would each add twenty passages that name him.
 */
export const FOCUS_BUDGET_MAX = 200;

/**
 * The viewport width below which the compact budget applies.
 *
 * 768px, matching the single `@media (max-width: 47.99rem)` breakpoint the graph stylesheet
 * already uses. A second, differently-placed breakpoint here would put the budget and the
 * chrome on different sides of the same viewport.
 */
export const FOCUS_COMPACT_WIDTH = 768;

/** The touch-target floor every drawn orb has to clear, in CSS pixels. */
export const FOCUS_TOUCH_PITCH = 44;

/** Drawn radius of a neighbour orb, measured in the 2D renderer. */
export const FOCUS_ORB_RADIUS = 11;

/**
 * How many orbs one ring inside a band of this height can seat at the touch pitch.
 *
 * A ring of N at radius R has arc pitch 2*pi*R/N, and R is bounded by half the *short* axis
 * of the band less the orb radius. Area is not the constraint and measuring it was the wrong
 * model: at a 44px hexagonal pitch the collapsed mobile band holds 101 orbs by area and 29 by
 * ring pitch, and the ring is what the layout draws.
 */
export function focusRingSeats(shortAxis: number): number {
    const radius = shortAxis / 2 - FOCUS_ORB_RADIUS;
    if (!(radius > 0)) return 0;
    return Math.floor((2 * Math.PI * radius) / FOCUS_TOUCH_PITCH);
}

/**
 * The budget a given drawing band can actually seat.
 *
 * ## Why the band and not the viewport
 *
 * Because they are different numbers by more than a factor of two, and the viewport is the
 * one that does not matter. Measured live on a 390x844 phone, the graph chrome takes 225.6px
 * before anything is drawn; the canvas band left under a collapsed sheet is 434.4px and under
 * a half-raised sheet 183.1px. At 183px one ring seats 11 orbs at a 44px pitch, so a budget
 * chosen from the 844px viewport height draws sixteen orbs into space for eleven and a finger
 * cannot pick any of them out.
 *
 * There is no phone constant here. The arithmetic is `focusRingSeats` over whichever axis is
 * shorter, so a short desktop band is treated as the short band it is rather than being given
 * the desktop budget because the window is wide.
 *
 * The measured phone case falls out: collapsed band 434px seats 29, so the compact 16 stands;
 * half-sheet band 183px seats 11, so it drops to 12. Twelve rather than eleven is a deliberate
 * 2px concession - twelve orbs at that radius sit at a 42px pitch, and going to 11 would cost
 * a relationship kind on Indra, Agni and Vayu for two pixels of finger room.
 *
 * `bandHeight` may be 0 or non-finite where a caller genuinely has not measured yet; the width
 * rule then stands alone, which is the previous behaviour rather than a collapsed scene.
 */
export function focusBudgetForBand(viewportWidth: number, bandHeight: number): number {
    const base = viewportWidth < FOCUS_COMPACT_WIDTH ? FOCUS_BUDGET_COMPACT : FOCUS_BUDGET;
    if (!Number.isFinite(bandHeight) || bandHeight <= 0) return base;
    const seats = focusRingSeats(Math.min(viewportWidth, bandHeight));
    if (seats >= base) return base;
    return Math.min(base, Math.max(FOCUS_BUDGET_CRAMPED, seats));
}

/**
 * The budget for a viewport whose drawing band is not known.
 *
 * A convenience over `focusBudgetForBand`, kept because two call sites only have a width. It
 * cannot see the sheet, so it cannot see the case above: a caller that *can* measure the band
 * should, and this one will over-draw a raised sheet by four orbs.
 */
export function focusBudget(viewportWidth: number): number {
    return focusBudgetForBand(viewportWidth, Number.NaN);
}

/** The budget after one press of "show more". */
export function expandFocusBudget(budget: number): number {
    return Math.min(FOCUS_BUDGET_MAX, budget + FOCUS_EXPAND_STEP);
}

/**
 * The most root-to-neighbour lines drawn before parallel edges stop being drawn separately.
 *
 * 128. Measured over every curated node, a budget-40 scene draws at worst 116 spokes, so the
 * cap has 10% of headroom and never binds at the default - it binds on expansion, which is
 * exactly where it should: at 48 the worst case is already 140. Past the cap a pair gets one
 * line and `collapsedSpokes` says how many it stands for, because four indistinguishable
 * lines between the same two dots is not four pieces of information.
 *
 * ## It is a cap on parallel spokes, not on spokes
 *
 * One line per shown neighbour is not discretionary. A neighbour with no line to the subject is
 * an unattached dot in a view whose entire claim is "this is what the subject is attached to",
 * which is a worse defect than a crowded scene. So where the budget alone exceeds the cap -
 * and FOCUS_BUDGET_MAX is 200, which does - every neighbour still gets its one line and this
 * cap governs only the parallels above them. The guarantee is
 * `spokes <= max(shown.length, SPOKE_CAP)`, and the two constants were derived independently:
 * 128 from the worst measured scene at the default budgets, 200 from where expansion stops
 * being useful.
 */
export const SPOKE_CAP = 128;

/**
 * The most lines of any kind in one Focus scene.
 *
 * 160, above the 147 worst case measured at budget 48 (140 spokes plus 24 between-edges,
 * capped). Between-edges are trimmed first when it binds, and to zero if need be: a line from
 * the subject to a neighbour is the relationship the reader asked about, and a line between two
 * neighbours is context. Bounded by the same floor as SPOKE_CAP for the same reason -
 * `spokes + between <= max(shown.length, FOCUS_LINE_CAP)`.
 */
export const FOCUS_LINE_CAP = 160;

/* --------------------------------------------------------------------- weights - */

/**
 * How much of the *fill* a node group may attract, as a multiplier on sqrt(count).
 *
 * Three tiers, and the tiers are the build's own judgement rather than a new one:
 *
 * 1.00 - the six groups `build-world.mjs` puts in the hub index, plus passage. A passage is
 *        the corpus's primary object and the thing a reader clicks through to.
 * 0.35 - the reified layers deliberately held *out* of the hub index. Real subjects, quiet
 *        ones: an evidence record is a genuine part of the apparatus and not what a reader
 *        came for. Indra has 796 of them against 38 deities, so an unweighted fill gives him
 *        a ring of provenance.
 * 0.00 - DerivedMetric. Degree-1 measurements whose labels embed a raw graph id
 *        ("DEVATA_ATTRIBUTION_BY_VEDA (VG:DEVATA:INDRAH)"). Never *filled*, but still
 *        reachable: MEASURES is a real relationship kind, so the coverage round shows one.
 *
 * A group absent from this table gets DEFAULT_GROUP_PRIOR rather than throwing, because a new
 * node group in a future artifact should appear in the scene at a defensible weight rather
 * than white-screening the graph.
 */
export const GROUP_PRIOR: Record<string, number> = {
    deity: 1,
    person: 1,
    idea: 1,
    rite: 1,
    thing: 1,
    wording: 1,
    passage: 1,
    record: 0.35,
    "unresolved-deity": 0.35,
    other: 0.35,
    derived: 0,
};

export const DEFAULT_GROUP_PRIOR = 0.35;

export function groupPrior(group: string): number {
    return GROUP_PRIOR[group] ?? DEFAULT_GROUP_PRIOR;
}

/**
 * Salience, in log2-degree units.
 *
 * Degree is the base term and the other three are corrections to it, sized in the same units
 * so they are comparable: one extra relationship family on the same pair is worth as much as
 * tripling the neighbour's degree, which is the ratio that made Indra's one rite and one idea
 * survive a fill round against four thousand passages.
 */
export const W_FAMILY = 1.5;
export const W_EDGE = 0.5;
export const W_BRIDGE = 1.0;

/** No node group may hold more than this share of the budget after the fill rounds. */
export const GROUP_CEILING = 0.3;

/** Share of the budget held back for constellation reach, and its absolute bounds. */
export const BRIDGE_RESERVE = 0.1;
export const BRIDGE_RESERVE_MIN = 2;
export const BRIDGE_RESERVE_MAX = 6;

/**
 * Off, and it stays off until something measures a reason.
 *
 * Dealing a group's fill slots round-robin across its relationship kinds is the obvious next
 * refinement and it was measured on Indra, Agni, Sarasvati and sacrifice at budgets 24, 40 and
 * 48 - twelve pairs. Coverage was *identical* in all twelve: same predicate count, same family
 * count, same group count, same group mix. What it changed was the connective tissue, and for
 * the worse: between-neighbour edges fell from 17 to 12 on Indra at 40, 20 to 15 on Agni at
 * 40, and 24 to 17 on Agni at 48, because spreading the picks across rare predicates picks
 * neighbours that are not attached to each other. It also halved the median neighbour degree,
 * 26 to 17, which reads as a scene of minor subjects.
 *
 * So it buys nothing measurable and costs a quarter of the edges that make the scene look like
 * a neighbourhood. Kept, because a future sidebar that groups by predicate may want it, and
 * removing it would mean re-deriving the twelve comparisons to find out.
 */
export const LANE_ROUND_ROBIN_DEFAULT = false;

/** `nodeRegion` for a node in no drawn constellation. The artifact's own sentinel. */
const NO_REGION = 65535;

/* ------------------------------------------------------------------ public types - */

export type FocusReason =
    /** The whole neighbourhood fitted; nothing was curated. */
    | "ALL"
    /** Already on screen at the previous budget. */
    | "PINNED"
    /** Chosen to represent a relationship kind nothing else on screen carried. */
    | "PREDICATE"
    /** Chosen to represent a node group nothing else on screen carried. */
    | "CATEGORY"
    /** Chosen to reach a constellation nothing else on screen reached. */
    | "CONSTELLATION"
    /** Dealt to its node group by the weighted fill. */
    | "FILL"
    /** Highest salience left, after every quota was spent or dry. */
    | "RANK";

export type FocusNeighbour = {
    /** Node index. Indices change between builds; `id` does not. */
    node: number;
    id: string;
    label: string;
    group: string;
    /** The neighbour's own degree in the whole graph, not within this scene. */
    degree: number;
    /** Edge indices joining it to the root, ascending. More than one is normal. */
    edges: number[];
    /** Predicate names on those edges, in the artifact's own order. */
    predicates: string[];
    families: RelationshipFamily[];
    /** True where at least one of those edges leaves the root's constellation. */
    bridge: boolean;
    /** The constellation it sits in, or null. */
    region: number | null;
    salience: number;
    reason: FocusReason;
    /** The predicate it was chosen to represent, where that is why it is here. */
    representing: string | null;
};

export type FocusSelection = {
    root: number;
    budget: number;
    shown: FocusNeighbour[];
    /** Distinct connected subjects. Not the degree, and usually smaller. */
    total: number;
    truncated: boolean;
    /**
     * What each round contributed.
     *
     * Kept on the result rather than logged because a scene that looks wrong is diagnosed by
     * which round produced it, and by then the console is gone.
     */
    trace: string[];
};

/** A root-to-neighbour line. */
export type FocusSpoke = {
    edge: number;
    node: number;
    predicate: string;
    family: RelationshipFamily;
};

/** A line between two shown neighbours. */
export type FocusEdge = {
    edge: number;
    a: number;
    b: number;
    predicate: string;
    family: RelationshipFamily;
};

export type FocusPredicateRow = {
    predicate: string;
    edges: number;
    subjects: number;
};

export type FocusGroupRow = {
    family: RelationshipFamily;
    heading: string;
    /** False where the subject has no edge in this family. The row is still rendered. */
    present: boolean;
    /** The sentence for an absent row. Empty where the family is present. */
    absent: string;
    /** Recorded connections in this family. Zero when absent. */
    edges: number;
    /** Distinct subjects reached. Different from `edges`: Indra's 826 evidence edges reach 799. */
    subjects: number;
    /** Busiest predicate first. */
    predicates: FocusPredicateRow[];
    /** Largest node group first. */
    groups: Array<{ group: string; subjects: number }>;
    /** How many of this family's subjects are in the current selection. */
    shown: number;
};

export type FocusNeighbourhood = {
    subject: Subject;
    budget: number;
    shown: FocusNeighbour[];
    total: number;
    truncated: boolean;
    spokes: FocusSpoke[];
    /** Parallel spokes not drawn because SPOKE_CAP collapsed their pair to one line. */
    collapsedSpokes: number;
    between: FocusEdge[];
    /** Between-edges dropped by FOCUS_LINE_CAP rather than by the between cap. */
    droppedBetween: number;
    rows: FocusGroupRow[];
    trace: string[];
};

export type FocusOptions = {
    /**
     * Node indices already on screen, kept whatever else happens.
     *
     * This is what makes "show twenty more" additive. Without it the set shown at 40 was not a
     * subset of the set shown at 48 - one subject was dropped on the way - and a reader who
     * asked for more lost something they were looking at.
     */
    pinned?: Iterable<number> | null;
    /** See LANE_ROUND_ROBIN_DEFAULT. Off. */
    laneRoundRobin?: boolean;
    /** Share of the budget one node group may hold. Defaults to GROUP_CEILING. */
    groupCeiling?: number;
    /** Override the three-tier prior. For tests, and for a surface wanting a flat mix. */
    priorOf?: (group: string) => number;
    /** Suppress two orbs with the same visible text. On. */
    dedupeLabels?: boolean;
};

export type FocusBetweenOptions = {
    /** Most between-edges in the scene. Defaults to `betweenCap(budget)`. */
    betweenCap?: number;
    /** Most between-edges at any one neighbour. Defaults to BETWEEN_PER_NODE. */
    betweenPerNode?: number;
};

/* ------------------------------------------------------------------- candidates - */

/**
 * Per-world lookup tables, built once and cached against the world object.
 *
 * The family of an edge is a string lookup through two indirections - `edgeType[e]` into
 * `manifest.edgeTypes` into `PREDICATE_FAMILY` - and the candidate loop does it 7,347 times
 * for Indra. Flattened to one `Uint8Array` read it disappears. A WeakMap because a composed
 * world (the homepage preview) is a different world with a different type table, and keying on
 * anything else would hand one world's families to the other.
 */
type FamilyTables = {
    /** Family index per edge-type index. */
    typeFamily: Uint8Array;
};

const FAMILY_TABLES = new WeakMap<World, FamilyTables>();

function familyTables(world: World): FamilyTables {
    const cached = FAMILY_TABLES.get(world);
    if (cached) return cached;
    const types = world.manifest.edgeTypes;
    const typeFamily = new Uint8Array(types.length);
    const other = FAMILY_INDEX.get("OTHER") ?? 0;
    for (let i = 0; i < types.length; i += 1) {
        typeFamily[i] = FAMILY_INDEX.get(familyOfPredicate(types[i])) ?? other;
    }
    const built: FamilyTables = { typeFamily };
    FAMILY_TABLES.set(world, built);
    return built;
}

/**
 * One neighbour, as numbers.
 *
 * Deliberately not a `{ predicates: Set<string>, families: Set<string> }` record, which is
 * what this was. Building 5,544 of those for Indra cost 2.97 ms of the 9.3 ms total, almost
 * all of it allocating two Sets per neighbour to hold a median of one string each. The 48 edge
 * types fit in two 32-bit words and the 13 families in one, so membership is a bit test and
 * the whole record is one monomorphic object with no allocation inside it.
 *
 * Measured: 2.97 ms -> 0.76 ms for the same 5,544 candidates, bit-for-bit the same set.
 */
type Candidate = {
    node: number;
    /** Edge-type membership, types 0-31. */
    typeLo: number;
    /** Edge-type membership, types 32-63. */
    typeHi: number;
    /**
     * Edge types at 64 and above, which two words cannot hold.
     *
     * Null in every artifact that exists: the current one declares 48 and the vocabulary 60.
     * Present because "48 fits in two words" is a fact about today's data and silently
     * dropping a predicate's membership would make the coverage round claim it had shown a
     * relationship kind it had not.
     */
    typeOver: number[] | null;
    familyMask: number;
    familyCount: number;
    edgeCount: number;
    bridge: boolean;
    degree: number;
    groupIndex: number;
    region: number;
    label: string;
    salience: number;
    chosen: boolean;
    reason: FocusReason;
    representing: string | null;
};

type CandidateSet = {
    list: Candidate[];
    /** Edges on the root per edge-type index. */
    typeEdges: Uint32Array;
    /** Edges on the root per family index. */
    familyEdges: Uint32Array;
};

function buildCandidates(world: World, labels: WorldLabels | null, root: number): CandidateSet {
    const { typeFamily } = familyTables(world);
    const edges = edgesOf(world, root);
    const pairs = world.edgePairs;
    const edgeType = world.edgeType;
    const edgeBridge = world.edgeBridge;
    const typeEdges = new Uint32Array(world.manifest.edgeTypes.length);
    const familyEdges = new Uint32Array(RELATIONSHIP_FAMILIES.length);
    const seen = new Map<number, Candidate>();
    const list: Candidate[] = [];

    for (let i = 0; i < edges.length; i += 1) {
        const edge = edges[i];
        const a = pairs[edge * 2];
        const other = a === root ? pairs[edge * 2 + 1] : a;
        const type = edgeType[edge];
        const family = typeFamily[type];
        typeEdges[type] += 1;
        familyEdges[family] += 1;
        // The artifact has no self-loops; one would be a dot orbiting itself, so it is skipped
        // from the scene but still counted above, where it is part of the subject's degree.
        if (other === root) continue;
        let candidate = seen.get(other);
        if (candidate === undefined) {
            candidate = {
                node: other,
                typeLo: 0,
                typeHi: 0,
                typeOver: null,
                familyMask: 0,
                familyCount: 0,
                edgeCount: 0,
                bridge: false,
                degree: world.nodeDegree[other],
                groupIndex: world.nodeGroup[other],
                region: world.nodeRegion[other],
                label: labels?.labels[other] ?? "",
                salience: 0,
                chosen: false,
                reason: "RANK",
                representing: null,
            };
            seen.set(other, candidate);
            list.push(candidate);
        }
        if (type < 32) candidate.typeLo |= 1 << type;
        else if (type < 64) candidate.typeHi |= 1 << (type - 32);
        else {
            const over = candidate.typeOver ?? (candidate.typeOver = []);
            if (!over.includes(type)) over.push(type);
        }
        const bit = 1 << family;
        if ((candidate.familyMask & bit) === 0) {
            candidate.familyMask |= bit;
            candidate.familyCount += 1;
        }
        candidate.edgeCount += 1;
        if (edgeBridge[edge] === 1) candidate.bridge = true;
    }

    for (let i = 0; i < list.length; i += 1) {
        const c = list[i];
        c.salience =
            Math.log2(1 + c.degree) +
            W_FAMILY * (c.familyCount - 1) +
            W_EDGE * (c.edgeCount - 1) +
            W_BRIDGE * (c.bridge ? 1 : 0);
    }
    return { list, typeEdges, familyEdges };
}

/**
 * Descending salience, ties by node index ascending. A total order, so the result is one set.
 *
 * Every list below is derived from this one sort by iterating it, rather than being sorted
 * itself. The previous form sorted each per-predicate, per-group and per-region list
 * separately, which on Indra is about fifty sorts over slices of 5,544 candidates; one sort of
 * the whole array costs 0.88 ms and the slices inherit its order for free.
 *
 * In place. The array it is handed is either freshly built or the chosen forty, so there is no
 * caller whose order it could disturb, and a `slice()` here is a 5,544-element copy.
 */
function sortCandidates(list: Candidate[]): Candidate[] {
    return list.sort((a, b) => b.salience - a.salience || a.node - b.node);
}

function hasType(candidate: Candidate, type: number): boolean {
    if (type < 32) return (candidate.typeLo & (1 << type)) !== 0;
    if (type < 64) return (candidate.typeHi & (1 << (type - 32))) !== 0;
    return candidate.typeOver !== null && candidate.typeOver.includes(type);
}

/* -------------------------------------------------------------------- selection - */

/**
 * Choose the neighbours to draw.
 *
 * Six rounds, each spending from the same budget, in an order that puts *what kinds of thing
 * this subject is attached to* ahead of *which of them is biggest*:
 *
 *   0. PINNED             - whatever the previous, smaller budget showed
 *   1. PREDICATE COVERAGE - every relationship kind once, rarest family first
 *   2. CATEGORY COVERAGE  - every node group once, rarest first
 *   3. CONSTELLATION REACH- the held-back reserve, spent on unreached constellations
 *   4. WEIGHTED FILL      - the rest, apportioned across groups by sqrt(count) x prior
 *   5. RANK FILL          - anything a dry group could not use, by salience
 *
 * Deterministic throughout: every comparison ends in a node index, an edge-type index or a
 * name, so there is no tie a run can break differently from the last.
 */
export function selectFocus(
    world: World,
    labels: WorldLabels | null,
    root: number,
    budget: number,
    options: FocusOptions = {},
): FocusSelection {
    const built = buildCandidates(world, labels, root);
    const { typeEdges, familyEdges } = built;
    const sorted = sortCandidates(built.list);
    const total = sorted.length;
    const priorOf = options.priorOf ?? groupPrior;
    const groups = world.manifest.groups;

    /*
     * The common case, and it is genuinely common: the median node in this artifact has six
     * distinct neighbours, and only 377 of 34,373 connected nodes have more than forty. Nine
     * subjects in ten are drawn whole, with no curation, no hidden neighbours and no "show
     * more" - so this early return is the path most readers are on, not a fast case.
     */
    if (total <= budget) {
        for (const candidate of sorted) candidate.reason = "ALL";
        return {
            root,
            budget,
            shown: toNeighbours(world, labels, root, sorted),
            total,
            truncated: false,
            trace: [`ALL=${total}`],
        };
    }

    const dedupeLabels = options.dedupeLabels !== false;
    const pinned = new Set<number>(options.pinned ?? []);
    const chosen: Candidate[] = [];
    const shownLabels = new Set<string>();
    /* Predicates already represented on screen, as bits, so ROUND 1's "has this kind been
       shown?" is a bit test rather than a scan of everything chosen so far. */
    let coveredLo = 0;
    let coveredHi = 0;
    const coveredOver = new Set<number>();
    const coveredGroups = new Set<number>();
    const coveredRegions = new Set<number>();
    /* Free candidates per node group, decremented on every take. The fill round asks for this
       repeatedly and recomputing it by filtering cost 16 passes over 5,544 candidates. */
    const freeInGroup = new Int32Array(groups.length);

    const take = (candidate: Candidate | undefined, reason: FocusReason): boolean => {
        if (!candidate || candidate.chosen) return false;
        if (dedupeLabels && candidate.label && shownLabels.has(candidate.label)) return false;
        candidate.chosen = true;
        candidate.reason = reason;
        chosen.push(candidate);
        if (candidate.label) shownLabels.add(candidate.label);
        coveredLo |= candidate.typeLo;
        coveredHi |= candidate.typeHi;
        if (candidate.typeOver) for (const type of candidate.typeOver) coveredOver.add(type);
        coveredGroups.add(candidate.groupIndex);
        coveredRegions.add(candidate.region);
        freeInGroup[candidate.groupIndex] -= 1;
        return true;
    };
    const available = (candidate: Candidate): boolean =>
        !candidate.chosen && !(dedupeLabels && candidate.label !== "" && shownLabels.has(candidate.label));
    const firstFree = (from: readonly Candidate[]): Candidate | undefined => from.find(available);
    const room = () => budget - chosen.length;

    /*
     * Every index the rounds need, built in one pass over the sorted candidates.
     *
     * One pass and not four. Free-per-group, per-predicate, per-group and per-region were each
     * their own loop over the same 5,544 records, and four traversals of an array that does not
     * fit in cache cost more than everything the rounds then do with them. Arrays indexed by
     * the artifact's own type and group indices rather than Maps for the same reason: there are
     * 48 edge types and 11 groups, so the dense array is smaller than the Map's hash table.
     *
     * Regions stay a Map because `nodeRegion` is a Uint16 whose sentinel is 65535, and a dense
     * array over that range would be sixty-five thousand slots to hold thirty-three lists.
     */
    const { typeFamily } = familyTables(world);
    const edgeTypeNames = world.manifest.edgeTypes;
    const rootRegion = world.nodeRegion[root];
    const byType: Array<Candidate[] | undefined> = new Array(edgeTypeNames.length);
    const byTypeOver = new Map<number, Candidate[]>();
    const byGroup: Array<Candidate[] | undefined> = new Array(groups.length);
    const byRegion = new Map<number, Candidate[]>();
    for (const candidate of sorted) {
        freeInGroup[candidate.groupIndex] += 1;

        const group = byGroup[candidate.groupIndex];
        if (group) group.push(candidate);
        else byGroup[candidate.groupIndex] = [candidate];

        if (candidate.region !== NO_REGION && candidate.region !== rootRegion) {
            const region = byRegion.get(candidate.region);
            if (region) region.push(candidate);
            else byRegion.set(candidate.region, [candidate]);
        }

        /*
         * Only the set bits are visited - `mask & -mask` isolates the lowest, `clz32` names it.
         * The obvious form tests all 64 positions per candidate, which over Indra's 5,544 is
         * 355,000 bit tests to find a median of one type each.
         */
        let lo = candidate.typeLo;
        while (lo !== 0) {
            const bit = lo & -lo;
            const type = 31 - Math.clz32(bit);
            const bucket = byType[type];
            if (bucket) bucket.push(candidate);
            else byType[type] = [candidate];
            lo ^= bit;
        }
        let hi = candidate.typeHi;
        while (hi !== 0) {
            const bit = hi & -hi;
            const type = 63 - Math.clz32(bit);
            const bucket = byType[type];
            if (bucket) bucket.push(candidate);
            else byType[type] = [candidate];
            hi ^= bit;
        }
        if (candidate.typeOver) {
            for (const type of candidate.typeOver) {
                const bucket = byTypeOver.get(type);
                if (bucket) bucket.push(candidate);
                else byTypeOver.set(type, [candidate]);
            }
        }
    }
    const candidatesForType = (type: number): readonly Candidate[] =>
        byType[type] ?? byTypeOver.get(type) ?? [];

    /*
     * ROUND 0 - WHAT IS ALREADY ON SCREEN.
     *
     * Expansion has to be additive or "show twenty more" is a lie: measured before this round
     * existed, the 40-set was not a subset of the 48-set - the weighted fill re-apportioned and
     * one subject the reader was looking at fell out. Taking the previous set first makes each
     * tier a superset of the last by construction rather than by luck.
     */
    for (const candidate of sorted) {
        if (room() <= 0) break;
        if (pinned.has(candidate.node)) take(candidate, "PINNED");
    }
    const tracePinned = chosen.length;

    /*
     * ROUND 1 - PREDICATE COVERAGE.
     *
     * Every distinct relationship kind on the root is represented once before any is
     * represented twice, visited rarest-family-first and then rarest-predicate-first. The
     * order matters because a budget too small to hold them all should spend what it has on
     * the surprising kinds: Indra's one EPITHET_VARIANT_OF says more about him than his
     * 3,566th passage mention, and a frequency-ordered round would never reach it.
     */
    const reserve = Math.max(
        BRIDGE_RESERVE_MIN,
        Math.min(BRIDGE_RESERVE_MAX, Math.ceil(budget * BRIDGE_RESERVE)),
    );
    const presentTypes: number[] = [];
    for (let type = 0; type < byType.length; type += 1) if (byType[type]) presentTypes.push(type);
    for (const type of byTypeOver.keys()) presentTypes.push(type);
    const typeOrder = presentTypes.sort(
        (a, b) =>
            familyEdges[typeFamily[a]] - familyEdges[typeFamily[b]] ||
            typeFamily[a] - typeFamily[b] ||
            typeEdges[a] - typeEdges[b] ||
            (edgeTypeNames[a] ?? "").localeCompare(edgeTypeNames[b] ?? ""),
    );
    for (const type of typeOrder) {
        // Coverage may spend everything except the constellation reserve.
        if (room() <= reserve) break;
        // A neighbour already on screen that carries this predicate has represented it. Two
        // rounds agreeing about the same pair must not also cost two coverage slots.
        if (
            type < 32
                ? (coveredLo & (1 << type)) !== 0
                : type < 64
                  ? (coveredHi & (1 << (type - 32))) !== 0
                  : coveredOver.has(type)
        ) {
            continue;
        }
        const pick = firstFree(candidatesForType(type));
        if (pick) {
            pick.representing = edgeTypeNames[type] ?? String(type);
            take(pick, "PREDICATE");
        }
    }
    const tracePredicate = chosen.length - tracePinned;

    /* ROUND 2 - CATEGORY COVERAGE. Every node group present gets a member, rarest first. */
    const presentGroups: number[] = [];
    for (let group = 0; group < byGroup.length; group += 1) {
        if (byGroup[group]) presentGroups.push(group);
    }
    const groupOrder = presentGroups.sort(
        (a, b) =>
            (byGroup[a]?.length ?? 0) - (byGroup[b]?.length ?? 0) ||
            groups[a].localeCompare(groups[b]),
    );
    for (const group of groupOrder) {
        if (room() <= reserve) break;
        if (coveredGroups.has(group)) continue;
        take(firstFree(byGroup[group] ?? []), "CATEGORY");
    }
    const traceCategory = chosen.length - tracePinned - tracePredicate;

    /*
     * ROUND 3 - CONSTELLATION REACH.
     *
     * The reserve buys the thing a star of neighbours cannot show: that this subject is part
     * of how the corpus hangs together. Indra reaches 33 of the 33 drawn constellations and a
     * pure-salience 40 reaches 12 of them; spending two to six slots on unreached regions takes
     * that to 17. A neighbour with no region is not a reach, so it is skipped rather than
     * treated as a thirty-fourth constellation.
     */
    let traceConstellation = 0;
    if (rootRegion !== NO_REGION) {
        const regionOrder = [...byRegion.keys()].sort(
            (a, b) => (byRegion.get(a)?.length ?? 0) - (byRegion.get(b)?.length ?? 0) || a - b,
        );
        let spent = 0;
        for (const region of regionOrder) {
            if (spent >= reserve || room() <= 0) break;
            if (coveredRegions.has(region)) continue;
            if (take(firstFree(byRegion.get(region) ?? []), "CONSTELLATION")) {
                spent += 1;
                traceConstellation += 1;
            }
        }
    }

    /*
     * ROUND 4 - WEIGHTED FILL.
     *
     * What is left is dealt to node groups in proportion to sqrt(neighbours) x prior, capped so
     * no group exceeds `groupCeiling` of the whole budget. sqrt rather than count because the
     * proportional version is the failure it replaces: Indra's 4,702 passages against 38
     * deities is 124:1 by count and 11:1 by root, and the 11:1 scene is the one that shows a
     * deity at all. The ceiling is what stops the largest group taking the tail of the budget
     * once the smaller ones run dry.
     *
     * Largest-remainder apportionment, iterated: a group clamped by the ceiling or by having no
     * candidates left returns its surplus to the pool rather than leaving the budget unspent.
     * Remainders tie by group name, so an equal split cannot drift between runs.
     */
    let traceFill = 0;
    if (room() > 0) {
        const weight = new Map<number, number>();
        for (const group of presentGroups) {
            if (freeInGroup[group] === 0) continue;
            const prior = priorOf(groups[group]);
            if (prior <= 0) continue;
            weight.set(group, Math.sqrt(byGroup[group]?.length ?? 0) * prior);
        }
        const ceiling = Math.max(1, Math.floor(budget * (options.groupCeiling ?? GROUP_CEILING)));
        const held = new Map<number, number>();
        for (const candidate of chosen) {
            held.set(candidate.groupIndex, (held.get(candidate.groupIndex) ?? 0) + 1);
        }
        const quota = new Map<number, number>();
        let pool = new Set(weight.keys());
        let slots = room();
        // Sixteen passes is far more than the eleven node groups can need; it is a guard
        // against a weight table that somehow never clamps, not a tuning parameter.
        for (let pass = 0; pass < 16 && slots > 0 && pool.size > 0; pass += 1) {
            let totalWeight = 0;
            for (const group of pool) totalWeight += weight.get(group) ?? 0;
            if (totalWeight <= 0) break;
            const exact = new Map<number, number>();
            const base = new Map<number, number>();
            let dealt = 0;
            for (const group of pool) {
                const share = (slots * (weight.get(group) ?? 0)) / totalWeight;
                exact.set(group, share);
                base.set(group, Math.floor(share));
                dealt += Math.floor(share);
            }
            let left = slots - dealt;
            const remainderOrder = [...pool].sort(
                (a, b) =>
                    (exact.get(b)! - base.get(b)!) - (exact.get(a)! - base.get(a)!) ||
                    groups[a].localeCompare(groups[b]),
            );
            for (const group of remainderOrder) {
                if (left <= 0) break;
                base.set(group, (base.get(group) ?? 0) + 1);
                left -= 1;
            }
            let placed = 0;
            const nextPool = new Set<number>();
            for (const group of pool) {
                const assigned = quota.get(group) ?? 0;
                const free = freeInGroup[group] - assigned;
                const headroom = Math.max(0, ceiling - (held.get(group) ?? 0) - assigned);
                const want = base.get(group) ?? 0;
                const allow = Math.min(want, free, headroom);
                quota.set(group, assigned + allow);
                placed += allow;
                if (allow === want && Math.min(free, headroom) > allow) nextPool.add(group);
            }
            slots -= placed;
            if (placed === 0) break;
            pool = nextPool;
        }

        for (const [group, count] of quota) {
            const members = byGroup[group] ?? [];
            if (!(options.laneRoundRobin ?? LANE_ROUND_ROBIN_DEFAULT)) {
                let taken = 0;
                for (const candidate of members) {
                    if (taken >= count) break;
                    if (take(candidate, "FILL")) {
                        taken += 1;
                        traceFill += 1;
                    }
                }
                continue;
            }
            /*
             * The lane variant: spread a group's slots over its relationship kinds by the same
             * coverage-before-rank rule, one level down. Off by default - see
             * LANE_ROUND_ROBIN_DEFAULT for the twelve comparisons that measured it costing
             * between 15% and 29% of the between-neighbour edges for no coverage at all.
             */
            const lanes = new Map<number, Candidate[]>();
            for (const candidate of members) {
                if (!available(candidate)) continue;
                // A candidate's lane is the rarest predicate it carries on this root.
                let lane = -1;
                let laneEdges = Number.POSITIVE_INFINITY;
                for (let type = 0; type < edgeTypeNames.length; type += 1) {
                    if (!hasType(candidate, type)) continue;
                    if (typeEdges[type] < laneEdges) {
                        lane = type;
                        laneEdges = typeEdges[type];
                    }
                }
                const bucket = lanes.get(lane);
                if (bucket) bucket.push(candidate);
                else lanes.set(lane, [candidate]);
            }
            const laneOrder = [...lanes.keys()].sort(
                (a, b) => (typeEdges[a] ?? 0) - (typeEdges[b] ?? 0) || a - b,
            );
            let taken = 0;
            for (let depth = 0; taken < count; depth += 1) {
                let round = 0;
                for (const lane of laneOrder) {
                    if (taken >= count) break;
                    const candidate = (lanes.get(lane) ?? [])[depth];
                    if (!candidate) continue;
                    if (take(candidate, "FILL")) {
                        taken += 1;
                        traceFill += 1;
                        round += 1;
                    }
                }
                if (round === 0) break;
            }
        }
    }

    /*
     * ROUND 5 - RANK FILL.
     *
     * Slots the fill could not place - because every group with a prior ran dry, or the
     * ceiling bound - go to the highest-salience neighbour left. A zero-prior group stays out:
     * a scene padded to forty with derived metrics is worse than a scene of thirty-six.
     */
    let traceRank = 0;
    if (room() > 0) {
        for (const candidate of sorted) {
            if (room() <= 0) break;
            if (priorOf(groups[candidate.groupIndex]) <= 0) continue;
            if (take(candidate, "RANK")) traceRank += 1;
        }
    }

    return {
        root,
        budget,
        shown: toNeighbours(world, labels, root, sortCandidates(chosen)),
        total,
        truncated: true,
        trace: [
            `PINNED=${tracePinned}`,
            `PREDICATE=+${tracePredicate}`,
            `CATEGORY=+${traceCategory}`,
            `CONSTELLATION=+${traceConstellation}`,
            `FILL=+${traceFill}`,
            `RANK=+${traceRank}`,
        ],
    };
}

/**
 * Expand the chosen candidates back into words, in one pass over the root's adjacency.
 *
 * Done here, for the forty that are shown, rather than in the candidate loop for the 5,544
 * that are not - the rounds never need a neighbour's edge list, only its bit mask.
 *
 * One pass for all of them, and that is not a micro-optimisation: the first version walked the
 * root's adjacency once *per shown neighbour*, which on Indra at budget 40 is 40 x 7,347 =
 * 294,000 `otherEnd` calls and measured 6.99 ms - the entire cost the two optimisations above
 * were supposed to have removed, reintroduced by the function that formats the result.
 */
function toNeighbours(
    world: World,
    labels: WorldLabels | null,
    root: number,
    chosen: readonly Candidate[],
): FocusNeighbour[] {
    const out: FocusNeighbour[] = [];
    const byNode = new Map<number, FocusNeighbour>();
    for (const candidate of chosen) {
        const neighbour: FocusNeighbour = {
            node: candidate.node,
            id: labels?.ids[candidate.node] ?? String(candidate.node),
            label: candidate.label,
            group: world.manifest.groups[candidate.groupIndex],
            degree: candidate.degree,
            edges: [],
            predicates: [],
            families: [],
            bridge: candidate.bridge,
            region: candidate.region === NO_REGION ? null : candidate.region,
            salience: candidate.salience,
            reason: candidate.reason,
            representing: candidate.representing,
        };
        byNode.set(candidate.node, neighbour);
        out.push(neighbour);
    }

    const rootEdges = edgesOf(world, root);
    const pairs = world.edgePairs;
    for (let i = 0; i < rootEdges.length; i += 1) {
        const edge = rootEdges[i];
        const a = pairs[edge * 2];
        const neighbour = byNode.get(a === root ? pairs[edge * 2 + 1] : a);
        if (neighbour === undefined) continue;
        neighbour.edges.push(edge);
        const predicate = world.manifest.edgeTypes[world.edgeType[edge]] ?? "";
        if (!neighbour.predicates.includes(predicate)) neighbour.predicates.push(predicate);
        const family = familyOfPredicate(predicate);
        if (!neighbour.families.includes(family)) neighbour.families.push(family);
    }
    // The CSR run for a node is filled in edge-index order, so the lists are already
    // ascending; sorted anyway because nothing in the artifact's contract promises that.
    for (const neighbour of out) neighbour.edges.sort((a, b) => a - b);
    return out;
}

/* ------------------------------------------------------- neighbour-to-neighbour - */

/** Most between-edges at any one neighbour. */
export const BETWEEN_PER_NODE = 3;

/** Between-edges as a share of the budget. */
export const BETWEEN_CAP_SHARE = 0.5;

/**
 * How many lines between neighbours a scene of this budget draws.
 *
 * Half the budget. The sensitivity was measured on Indra's 40: unbounded there are 67 lines
 * among them and a top-40-by-degree set with no coverage rules has 294, which is the hairball
 * this whole file avoids. At perNode 3 and cap 20 the scene draws 17, touching 14 of the 40
 * neighbours - enough that the reader sees the neighbourhood is interconnected, not so much
 * that the subject stops being the centre of it.
 */
export function betweenCap(budget: number): number {
    return Math.round(budget * BETWEEN_CAP_SHARE);
}

/**
 * Bounded lines between the neighbours that are on screen.
 *
 * One line per pair whatever the parallel edges say, at most `betweenPerNode` at any one
 * neighbour, at most `betweenCap` overall, ranked by the salience of the two ends and then by
 * edge index. The per-node cap is doing most of the work: without it the measured 67 lines
 * concentrate on the few most connected neighbours and read as a second hub inside the scene.
 */
export function betweenEdges(
    world: World,
    root: number,
    shown: readonly FocusNeighbour[],
    options: FocusBetweenOptions = {},
): FocusEdge[] {
    const cap = options.betweenCap ?? betweenCap(shown.length);
    const perNode = options.betweenPerNode ?? BETWEEN_PER_NODE;
    if (cap <= 0 || perNode <= 0) return [];

    const salience = new Map<number, number>();
    for (const neighbour of shown) salience.set(neighbour.node, neighbour.salience);
    const seenPair = new Set<number>();
    const candidates: Array<{ edge: number; a: number; b: number; score: number }> = [];
    for (const neighbour of shown) {
        const edges = edgesOf(world, neighbour.node);
        for (let i = 0; i < edges.length; i += 1) {
            const edge = edges[i];
            const a = world.edgePairs[edge * 2];
            const b = world.edgePairs[edge * 2 + 1];
            // A spoke is not a between-edge, and neither is a self-loop.
            if (a === root || b === root || a === b) continue;
            const from = salience.get(a);
            const to = salience.get(b);
            if (from === undefined || to === undefined) continue;
            const low = a < b ? a : b;
            const high = a < b ? b : a;
            /* A pair key, not an edge key: two neighbours joined four ways draw one line.
               `low * nodes + high` is exact while nodes stays under 2^26, which 35,370 is. */
            const key = low * world.manifest.counts.nodes + high;
            if (seenPair.has(key)) continue;
            seenPair.add(key);
            candidates.push({ edge, a, b, score: from + to });
        }
    }
    candidates.sort((x, y) => y.score - x.score || x.edge - y.edge);

    const used = new Map<number, number>();
    const out: FocusEdge[] = [];
    for (const candidate of candidates) {
        if (out.length >= cap) break;
        if ((used.get(candidate.a) ?? 0) >= perNode) continue;
        if ((used.get(candidate.b) ?? 0) >= perNode) continue;
        used.set(candidate.a, (used.get(candidate.a) ?? 0) + 1);
        used.set(candidate.b, (used.get(candidate.b) ?? 0) + 1);
        const predicate = world.manifest.edgeTypes[world.edgeType[candidate.edge]] ?? "";
        out.push({
            edge: candidate.edge,
            a: candidate.a,
            b: candidate.b,
            predicate,
            family: familyOfPredicate(predicate),
        });
    }
    return out;
}

/* ------------------------------------------------------------------ sidebar rows - */

/**
 * What the subject is attached to, by family, including the families it has none of.
 *
 * ## Why an absent family is a row and not an omission
 *
 * Because a list of only what is present lets a reader draw a false conclusion from it, and
 * this artifact makes that easy. Five of the twelve families are absent on Indra - PARALLEL,
 * FORMULA, RITE, PROSODY and CONTAINMENT - and a sidebar showing his seven present families
 * reads as a complete account. A reader then infers that Indra has no metre. What is actually
 * true is that a metre is a property of a passage and no deity node in this graph carries one,
 * which is a fact about the shape of the record rather than about Indra, and the difference
 * between those two readings is the difference between a description and a misleading one.
 *
 * The same trap has been documented twice in this project under "type absence in the row, not
 * the caveat": a query that returns only positive rows lets the reader infer a false zero, and
 * a caveat elsewhere on the page does not undo it. So the row is present, it says so in its
 * own words, and `sum(rows[].edges)` equals the subject's degree exactly.
 *
 * OTHER is the one exception, and only when empty: see ACCOUNTED_FAMILIES.
 */
export function focusGroupRows(
    world: World,
    root: number,
    shown?: readonly FocusNeighbour[] | null,
): FocusGroupRow[] {
    type Bucket = {
        edges: number;
        subjects: Set<number>;
        predicates: Map<string, { edges: number; subjects: Set<number> }>;
        groups: Map<string, Set<number>>;
        shown: Set<number>;
    };
    const buckets = new Map<RelationshipFamily, Bucket>();
    const bucketFor = (family: RelationshipFamily): Bucket => {
        const existing = buckets.get(family);
        if (existing) return existing;
        const fresh: Bucket = {
            edges: 0,
            subjects: new Set(),
            predicates: new Map(),
            groups: new Map(),
            shown: new Set(),
        };
        buckets.set(family, fresh);
        return fresh;
    };

    const onScreen = new Set<number>();
    if (shown) for (const neighbour of shown) onScreen.add(neighbour.node);

    const edges = edgesOf(world, root);
    for (let i = 0; i < edges.length; i += 1) {
        const edge = edges[i];
        const predicate = world.manifest.edgeTypes[world.edgeType[edge]] ?? "";
        const bucket = bucketFor(familyOfPredicate(predicate));
        bucket.edges += 1;
        const other = otherEnd(world, edge, root);
        bucket.subjects.add(other);
        if (onScreen.has(other)) bucket.shown.add(other);
        const row = bucket.predicates.get(predicate);
        if (row) {
            row.edges += 1;
            row.subjects.add(other);
        } else {
            bucket.predicates.set(predicate, { edges: 1, subjects: new Set([other]) });
        }
        const group = world.manifest.groups[world.nodeGroup[other]];
        const members = bucket.groups.get(group);
        if (members) members.add(other);
        else bucket.groups.set(group, new Set([other]));
    }

    const families: RelationshipFamily[] = [...ACCOUNTED_FAMILIES];
    if ((buckets.get("OTHER")?.edges ?? 0) > 0) families.push("OTHER");

    const rows = families.map((family): FocusGroupRow => {
        const bucket = buckets.get(family);
        const present = (bucket?.edges ?? 0) > 0;
        return {
            family,
            heading: FAMILY_COPY[family].heading,
            present,
            absent: present ? "" : FAMILY_COPY[family].absent,
            edges: bucket?.edges ?? 0,
            subjects: bucket?.subjects.size ?? 0,
            predicates: bucket
                ? [...bucket.predicates.entries()]
                      .map(([predicate, row]) => ({
                          predicate,
                          edges: row.edges,
                          subjects: row.subjects.size,
                      }))
                      .sort((a, b) => b.edges - a.edges || a.predicate.localeCompare(b.predicate))
                : [],
            groups: bucket
                ? [...bucket.groups.entries()]
                      .map(([group, members]) => ({ group, subjects: members.size }))
                      .sort((a, b) => b.subjects - a.subjects || a.group.localeCompare(b.group))
                : [],
            shown: bucket?.shown.size ?? 0,
        };
    });

    /* Busiest family first, absent families last in the declared order. An absent row sorted
       by its zero would interleave with nothing and read as the quietest present family. */
    return rows.sort(
        (a, b) =>
            Number(!a.present) - Number(!b.present) ||
            b.edges - a.edges ||
            (FAMILY_INDEX.get(a.family) ?? 0) - (FAMILY_INDEX.get(b.family) ?? 0),
    );
}

/* ---------------------------------------------------------------- the whole scene - */

/**
 * Everything a Focus surface needs about one subject, in one object.
 *
 * Pure, and separate from the hook so that a test, a script or a future server render can
 * build it without React. The two line caps are applied here rather than by the renderers,
 * because two renderers applying them separately is how this codebase previously ended up with
 * two disagreeing copies of one rule.
 */
export function focusNeighbourhood(
    world: World,
    labels: WorldLabels | null,
    root: number,
    budget: number = FOCUS_BUDGET,
    options: FocusOptions & FocusBetweenOptions = {},
): FocusNeighbourhood {
    const selection = selectFocus(world, labels, root, budget, options);

    /*
     * Spokes, in two passes: every neighbour's first line, then the parallels until the cap.
     *
     * Graduated rather than all-or-nothing. Collapsing every pair the moment the total crossed
     * 128 took a 140-spoke scene straight down to 48, throwing away ninety lines to save
     * twelve; filling the parallels in salience order keeps the cap's worth and drops only what
     * does not fit. The first pass is unconditional - see SPOKE_CAP on why a neighbour may not
     * end up with no line at all.
     */
    const spokes: FocusSpoke[] = [];
    let spokeTotal = 0;
    const pushSpoke = (node: number, edge: number) => {
        const predicate = world.manifest.edgeTypes[world.edgeType[edge]] ?? "";
        spokes.push({ edge, node, predicate, family: familyOfPredicate(predicate) });
    };
    for (const neighbour of selection.shown) {
        spokeTotal += neighbour.edges.length;
        if (neighbour.edges.length > 0) pushSpoke(neighbour.node, neighbour.edges[0]);
    }
    if (spokeTotal > spokes.length) {
        for (const neighbour of selection.shown) {
            if (spokes.length >= SPOKE_CAP) break;
            for (let i = 1; i < neighbour.edges.length; i += 1) {
                if (spokes.length >= SPOKE_CAP) break;
                pushSpoke(neighbour.node, neighbour.edges[i]);
            }
        }
    }

    const wanted = betweenEdges(world, root, selection.shown, {
        betweenCap: options.betweenCap ?? betweenCap(budget),
        betweenPerNode: options.betweenPerNode,
    });
    const lineRoom = Math.max(0, FOCUS_LINE_CAP - spokes.length);
    const between = wanted.length > lineRoom ? wanted.slice(0, lineRoom) : wanted;

    return {
        subject: describeSubject(world, labels, root),
        budget,
        shown: selection.shown,
        total: selection.total,
        truncated: selection.truncated,
        spokes,
        collapsedSpokes: spokeTotal - spokes.length,
        between,
        droppedBetween: wanted.length - between.length,
        rows: focusGroupRows(world, root, selection.shown),
        trace: selection.trace,
    };
}

/**
 * The memoised neighbourhood, for a React surface.
 *
 * ## This may not be called from a frame callback
 *
 * `selectFocus` on Indra was 9.3 ms before the optimisations in `buildCandidates` and
 * `sortCandidates` and is 0.9 ms after; either figure is a frame or fifty-five of them, and
 * neither belongs inside `requestAnimationFrame`. The renderers read the returned arrays; they
 * do not call this. The only inputs are the subject, the budget and what is pinned, none of
 * which can change within a frame, so there is nothing a frame could usefully re-ask.
 *
 * ## Why the argument is one object
 *
 * So that `useMemo` can key on primitives. A `FocusOptions` bag passed positionally is rebuilt
 * on every render by every caller that writes it inline, and a memo keyed on its identity
 * recomputes every render - which is the whole cost this function exists to pay once. `pinned`
 * is keyed on its contents for the same reason: it is a fresh array on every render of a
 * surface that holds it in state.
 */
export function useFocusNeighbourhood(input: {
    world: World | null;
    labels: WorldLabels | null;
    /** Node index, or null where nothing is selected. */
    root: number | null;
    budget?: number;
    pinned?: Iterable<number> | null;
    laneRoundRobin?: boolean;
    betweenPerNode?: number;
}): FocusNeighbourhood | null {
    const {
        world,
        labels,
        root,
        budget = FOCUS_BUDGET,
        pinned = null,
        laneRoundRobin = LANE_ROUND_ROBIN_DEFAULT,
        betweenPerNode = BETWEEN_PER_NODE,
    } = input;

    const pinnedKey = useMemo(() => {
        if (!pinned) return "";
        return Array.from(pinned)
            .sort((a, b) => a - b)
            .join(",");
    }, [pinned]);

    return useMemo(() => {
        if (!world || root === null) return null;
        return focusNeighbourhood(world, labels, root, budget, {
            pinned: pinnedKey === "" ? null : pinnedKey.split(",").map(Number),
            laneRoundRobin,
            betweenPerNode,
        });
    }, [world, labels, root, budget, pinnedKey, laneRoundRobin, betweenPerNode]);
}
