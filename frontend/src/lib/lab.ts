import { vedaNames, vedaOrder } from "./api";

/**
 * The Lab's catalogue.
 *
 * A *lens* on `/explore` is a way to browse a list. A *plate* here is one comparative figure
 * that answers one question and then hands the reader back to the lens that holds its rows.
 * Keeping the two apart is the only thing stopping this surface from becoming a second
 * Explore with charts on it.
 *
 * The catalogue is a module rather than a route's local constant because four things need the
 * same entry: the index card, the plate's own header, `generateStaticParams`, and the
 * metadata. A plate whose index card and page header had drifted apart would be a
 * navigational lie of exactly the kind this project spends its caveats avoiding.
 */

export type PlateSlug =
    | "four-corpora"
    | "deities"
    | "transmission"
    | "formulas"
    | "human-concerns"
    | "ritual"
    | "material-culture";

/**
 * The five questions every plate answers before it is allowed to ship, kept as fields rather
 * than as prose so that a plate cannot be written without answering them. A missing field is
 * a type error, which is the point.
 */
export type PlateLabel = {
    /** What is being measured. */
    measures: string;
    /** What one mark represents. */
    mark: string;
    /** What corpus scope is included. */
    scope: string;
    /** What is excluded. */
    excluded: string;
    /** What the reader must not infer. */
    notInfer: string;
};

export type Plate = {
    slug: PlateSlug;
    /** The section of the atlas this plate belongs to. */
    lens: string;
    /** The plate's own name. A title, not a headline. */
    title: string;
    /** The single research question, phrased as a question. */
    question: string;
    /** One sentence for the index card. */
    summary: string;
    /** The methodological warning the index card carries, so it is read before the figure. */
    caution: string;
    /** Which API views this plate reads, named for the reader rather than for the pipeline. */
    reads: string;
    label: PlateLabel;
};

export const PLATES: Plate[] = [
    {
        slug: "four-corpora",
        lens: "Corpus",
        title: "Four corpora, side by side",
        question: "How are the four Vedas structurally different?",
        summary:
            "Size, translation, recitation and connectedness, held apart on one aligned scale each so that no two of them are added together.",
        caution:
            "There is no combined score. The four collections differ in size by a factor of nearly six, and three of the four are partial in different ways.",
        reads: "Work registry, translation layer, recitation catalogue, cross-corpus relationship census",
        label: {
            measures:
                "Six independent properties of each collection as this build holds it: verses addressed, verses with an English translation, verses with a recitation, relationships joining it to the other three, the divisions it is organised by, and what its ordinary name covers but this build does not.",
            mark: "One bar is one collection's figure for one property. Bars are only ever compared along a row, never down a column.",
            scope: "All four Samhitas, one recension each, as listed on the sources page.",
            excluded:
                "The Samavedic gana corpus, the whole Krishna Yajurveda, the Paippalada Atharvaveda, the second Rigvedic recension, and every Brahmana, Aranyaka and Upanisad.",
            notInfer:
                "That a longer bar means a more important collection. Every row measures what this build holds, and three of these four collections are held in part.",
        },
    },
    {
        slug: "deities",
        lens: "Deities",
        title: "Named, and dedicated to",
        question: "Which deities shape each Veda, and are they the deities the hymns are given to?",
        summary:
            "The deity a verse names and the deity a hymn is dedicated to are two different records with two different scopes. This plate refuses to add them.",
        caution:
            "Naming spans all four collections. The traditional dedication exists for the Rigveda alone, so a blank elsewhere is a missing index, not an absent god.",
        reads: "Deity registry, mention layer at CERTAIN and PROBABLE, Anukramani ascription apparatus",
        label: {
            measures:
                "Two counts per deity. Naming: verses in which the deity is named, at the CERTAIN and PROBABLE certainty tiers. Dedication: verses carrying the traditional hymn ascription to that deity.",
            mark: "In the two-column figure, one bar is one deity's count of verses; both columns count verses and share one scale, so a shorter bar is a smaller count. In the rate figure, one bar is that deity's naming rate in one collection, per 1,000 verses of that collection.",
            scope: "Naming covers all four collections. Dedication covers the Rigveda.",
            excluded:
                "AMBIGUOUS mentions, which are held back from the default figures because Vedic Sanskrit uses one word for the god Agni and for fire. They can be added, loudly, from the control above the table.",
            notInfer:
                "That naming and dedication measure the same thing, or that the gap between them is a correction. They have different scopes and a deity can be named often and dedicated to rarely, or the reverse.",
        },
    },
    {
        slug: "transmission",
        lens: "Textual transmission",
        title: "What the collections share",
        question: "Where does Rigvedic material reappear in the Samaveda?",
        summary:
            "Every corpus pair against every kind of textual relationship, with the empty cells typed rather than drawn as zeroes, and then the Rigveda-to-Samaveda reuse itself, verse by verse.",
        caution:
            "Directed reuse — one verse carrying another's wording, in that direction — was established for one corpus pair. A pair without it is an unmeasured pair.",
        reads: "Parallel layer, directed reuse edges, variant layer, formula mediation, shared-vocabulary layer",
        label: {
            measures:
                "Relationship edges between passages in different collections, counted by the kind of relationship and by the pair of collections joined.",
            mark: "In the matrix, one cell is one corpus pair against one relationship class, and its weight is the number of edges. In the flow view, one line is one Samavedic verse and the Rigvedic verse it reuses.",
            scope: "All six corpus pairs against all eight relationship classes: 48 cells, all 48 returned.",
            excluded:
                "Generic similarity. There is no single similarity score here, because the eight classes are not degrees of one measure.",
            notInfer:
                "That an empty cell means the two collections share nothing. Twelve of the 48 cells are NOT_BUILT and five were never established for that pair, and those are facts about the graph.",
        },
    },
    {
        slug: "formulas",
        lens: "Poetic form",
        title: "How a wording travels",
        question: "How do fixed phrases move between the four collections?",
        summary:
            "A formula family is one wording plus everything that contains or nearly repeats it. Following a family outward shows how far a single phrase reaches.",
        caution:
            "Families are built by normalised string match. Shared diction is evidence of a shared poetic idiom; it is not by itself a demonstrated line of transmission.",
        reads: "Formula layer, formula-family membership, family span census",
        label: {
            measures:
                "Formula families, and how many of the four collections each one occurs in. Within a family, members are counted as cores, expansions or variants.",
            mark: "In the span ladder, one block is the number of families reaching that many collections. In the family strips, one segment is one collection's share of that family's occurrences.",
            scope: "All 720 families in this build, complete — the census is a count over the whole layer, not a sample.",
            excluded:
                "Wording shared by meaning rather than by letters. No semantic resemblance measure exists in this graph.",
            notInfer:
                "That a family crossing four collections proves one borrowed from another. The census records co-occurrence of a wording, and direction is only established separately, for one pair.",
        },
    },
    {
        slug: "human-concerns",
        lens: "Human concerns",
        title: "What people asked for",
        question:
            "What human concerns does the Atharvaveda address, and how do the other three compare?",
        summary:
            "Fever, rivals, childbirth, cattle, a house, a safe journey. The Atharvaveda names what its reciters wanted, and this plate keeps what is suffered apart from what is guarded against.",
        caution:
            "A demon is not a disease. The registry types each condition, and the two are drawn on separate axes so they can never be read as one list of ailments.",
        reads: "Condition registry, human-concern registry, lexical mention layer, protection and treatment edges",
        label: {
            measures:
                "Verses in which a registered Sanskrit alias for a condition, concern or rite occurs, counted per collection and normalised per 1,000 verses of that collection.",
            mark: "One bar is one condition's rate in one collection. The colour and the heading say which of the three kinds of condition it is: an affliction, a threat, or a named cause.",
            scope: "All four collections. The mention layer reaches all four, so a collection with no figure for a row genuinely had no match.",
            excluded:
                "Anything the registry has no alias for. These are lexical minima and the true figures are higher.",
            notInfer:
                "A diagnosis. `yaksma` is a Sanskrit word for a wasting illness, not a identification of a disease, and nothing here maps a Vedic condition onto a modern one.",
        },
    },
    {
        slug: "ritual",
        lens: "Ritual",
        title: "The rite, as far as it is modelled",
        question: "What does the corpus say about ritual, and how much of it has been modelled?",
        summary:
            "Eight rites carry a modelled structure and three step edges exist across all of them. The coverage statement comes before the content here, because it is the more important fact.",
        caution:
            "This is modelled coverage, not a taxonomy of Vedic ritual. The corpus names far more rites than the layer holds, and no rite here has a recoverable order of steps.",
        reads: "Ritual layer, curated implement and offering edges, lexical mention layer",
        label: {
            measures:
                "Rites and ritual implements in the curated layer, with the number of verses in which each is named.",
            mark: "One row is one modelled rite or one implement. Its figure is the number of verses a registered alias matched.",
            scope: "The rites and implements that have been modelled, with the denominator measured in the payload rather than written here. Two step layers are reported apart: what a Samhita text numbers, and what a sutra prints.",
            excluded:
                "Every rite the corpus names that has not been modelled, and the sequence of any rite: there are three step edges in the whole layer.",
            notInfer:
                "That a rite absent from this list is absent from the Vedas, or that the rites listed are the important ones. This is a list of what has been built.",
        },
    },
    {
        slug: "material-culture",
        lens: "Material culture",
        title: "What the corpus handles",
        question: "What things do the Vedas name, and where?",
        summary:
            "Cattle, horses, rivers, barley, copper. The nouns of daily life, counted by collection, with one cell that is known to be wrong left visible.",
        caution:
            "A blank cell means no registered alias matched. At least one of those blanks is known to be false, and it is labelled rather than quietly fixed.",
        reads: "Entity registry across six material categories, lexical mention layer, metal grid",
        label: {
            measures:
                "Verses in which a registered Sanskrit alias for a material thing occurs, by collection, raw and per 1,000 verses.",
            mark: "One row is one thing. One cell is its count in one collection; a cell with no match is drawn as a stated absence, never as a zero.",
            scope: "All four collections, across the five categories the registry carries: animals, crops, metals, rivers and peoples.",
            excluded:
                "Anything without a registry entry, and any alias the matcher does not carry.",
            notInfer:
                "That a blank cell means the thing is absent from that collection. `ayas` is named at VSM 18.13 and the matcher misses it, which is why the gap is declared on the plate rather than corrected in the data.",
        },
    },
];

export const PLATES_BY_SLUG: Record<PlateSlug, Plate> = Object.fromEntries(
    PLATES.map((plate) => [plate.slug, plate]),
) as Record<PlateSlug, Plate>;

export function plateHref(slug: PlateSlug) {
    return `/visualizations/${slug}`;
}

/**
 * The Lab's declared omissions.
 *
 * A visualization that was considered and refused belongs on the index next to the ones that
 * shipped. Otherwise the index reads as the set of things the corpus supports, and it is the
 * set of things this build could draw honestly.
 */
export const NOT_DRAWN: { title: string; why: string; href?: string; hrefLabel?: string }[] = [
    {
        title: "Metre across the four collections",
        why: "The metre layer reaches the Rigveda. The 575 metre names in the registry carry a verse count, but the Rigvedic and Atharvavedic metre vocabularies are disjoint sets, so one ranked chart of metre names would be a chart of the Rigveda with the corpus's name on it.",
        href: "/entities/chandas",
        hrefLabel: "Browse the metres as a list",
    },
    {
        title: "Communities of deities",
        why: "No node in this graph carries a community, partition or cluster assignment, and none was computed. Deity pairs that share verses exist and are a different object: pairs are not a partition.",
        href: "/limits",
        hrefLabel: "Read the recorded limit",
    },
];

/** The four collections in their traditional order, for any figure with a corpus axis. */
export const CORPORA = (["RV", "SV", "YV", "AV"] as const).map((code) => ({
    code,
    name: vedaNames[code],
    order: vedaOrder[code],
}));

export type CorpusCode = (typeof CORPORA)[number]["code"];

/**
 * A per-corpus row as the insight endpoints return it: lower-case keys, and a `null` that
 * means "not reached" rather than "zero".
 */
export type ByVeda = {
    rv?: number | null;
    sv?: number | null;
    yv?: number | null;
    av?: number | null;
    status?: string | null;
    note?: string | null;
};

export function corpusValue(row: ByVeda | null | undefined, code: CorpusCode) {
    if (!row) return null;
    const value = row[code.toLowerCase() as "rv" | "sv" | "yv" | "av"];
    return typeof value === "number" ? value : null;
}

/** Tabular figures, so a column of counts can be read down. */
export function count(value: number | null | undefined) {
    return typeof value === "number" ? value.toLocaleString("en-GB") : null;
}

/**
 * `3 objects`, `1 deity`.
 *
 * Small enough to be tempting to inline and small enough to get wrong in six places: the
 * ritual rows read "1 deities" until this existed.
 */
export function plural(value: number | null | undefined, one: string, many = `${one}s`) {
    return `${count(value) ?? "no"} ${value === 1 ? one : many}`;
}

/**
 * A rate per 1,000 verses, rendered at the precision the figure can carry.
 *
 * Two decimals below ten and one above: 0.57 and 219.6 are both three significant figures,
 * and printing 219.63 would claim a precision the underlying integer counts do not have.
 */
export function rate(value: number | null | undefined) {
    if (typeof value !== "number") return null;
    return value >= 10 ? value.toFixed(1) : value.toFixed(2);
}
