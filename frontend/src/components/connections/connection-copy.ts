/**
 * The reader's words for the eight cross-corpus relationship classes, and for the
 * several ways a cell of the evidence matrix can be empty.
 *
 * `@/lib/knowledge` remains the product's translation layer for grades, certainties
 * and absences, and nothing here duplicates it. What it does not hold is a
 * vocabulary for the relationship classes this surface is entirely about:
 * `statusCopy` renders NOT_BUILT as "Not yet modelled" and CLASS_NOT_CROSS_VEDA as
 * "Within one Veda", which are accurate and tell a reader nothing about what the
 * class is or why this cell is empty rather than that one.
 *
 * Every number on this surface is read from the payload. There is not a figure in
 * this file, on purpose: a count typed into a vocabulary table is a count nothing
 * can check.
 */

import { vedaNames } from "@/lib/api";
import { humanizePredicate, titleCase } from "@/lib/knowledge";

export type ConnectionCopy = {
    /** Singular, for a heading. */
    name: string;
    /** Plural, for a sentence that carries a count. */
    plural: string;
    /** What the class asserts about two verses, in one sentence. */
    definition: string;
};

/**
 * The predicate names are the graph's own and are deliberately stable. These are
 * their readings, and the distinctions between them are the whole product: an exact
 * repetition, an edition-level variant and a shared vocabulary are three different
 * claims and must never collapse into one similarity score.
 */
const CLASS_COPY: Record<string, ConnectionCopy> = {
    EXACT_PARALLEL_OF: {
        name: "Exact parallel",
        plural: "exact parallels",
        definition: "The same verse, word for word, standing in two different Vedas.",
    },
    NEAR_PARALLEL_OF: {
        name: "Near parallel",
        plural: "near parallels",
        definition:
            "Almost the same verse in both, with a word, an ending or a word order changed.",
    },
    REUSES_TEXT_FROM: {
        name: "Directed reuse",
        plural: "directed reuse connections",
        definition:
            "One verse is measured to carry the other's wording, and the measurement names which of the two is the earlier side.",
    },
    VARIANT_OF: {
        name: "Variant reading",
        plural: "variant readings",
        definition:
            "One verse as two traditions record it, differing the way two editions of a text differ.",
    },
    SHARES_ENTITY_VOCABULARY_WITH: {
        name: "Shared vocabulary",
        plural: "shared-vocabulary links",
        definition:
            "Both verses name the same gods, people or things. They need not share a single word of wording, so this is the weakest kind of connection here and is never counted as reuse.",
    },
    PARALLEL_TO: {
        name: "Parallel wording inside one Veda",
        plural: "internal parallels",
        definition:
            "Repeated wording that stays inside a single collection. It joins two verses of one Veda, so it never enters a pair of Vedas at all.",
    },
    SEMANTIC_RESEMBLANCE: {
        name: "Conceptual resemblance",
        plural: "conceptual resemblances",
        definition:
            "Two verses saying a similar thing in different words. Nothing in this corpus measures that — no reading of meaning, no comparison of sense — so every cell of this kind is unknown. It is not a finding that no such resemblance exists.",
    },
    SEMANTIC_ASSERTION: {
        name: "Semantic assertion",
        plural: "semantic assertions",
        definition:
            "A statement about what one verse says. It describes a single verse rather than linking two, so it cannot belong to a pair of Vedas however much of it is held.",
    },
};

export function connectionCopy(relationshipClass: string): ConnectionCopy {
    const known = CLASS_COPY[relationshipClass];
    if (known) return known;
    const fallback = titleCase(humanizePredicate(relationshipClass));
    return {
        name: fallback,
        plural: fallback.toLowerCase(),
        definition: "Relationship class as the measurement stores it.",
    };
}

export type CellTone = "measured" | "none" | "unknown" | "shape";

export type CellState = {
    /** What the cell says, in a phrase short enough for a table cell. */
    label: string;
    /** Why it says that, for the reader who wants the distinction. */
    meaning: string;
    tone: CellTone;
};

/**
 * Four ways to be empty, kept four ways apart.
 *
 * A measured zero, a class that cannot enter a pair, and a measure that was never
 * built are three different answers, and rendering all three as `0` is the single
 * misreading this whole matrix exists to prevent.
 */
export function cellState(status?: string | null): CellState {
    switch (status) {
        case "MEASURED":
            return { label: "Measured", meaning: "Counted in this corpus.", tone: "measured" };
        case "MEASURED_ZERO":
            return {
                label: "None found",
                meaning:
                    "This pair was measured for this kind of connection and none was established. The pair's other connections are unaffected.",
                tone: "none",
            };
        case "NOT_ESTABLISHED_FOR_PAIR":
            return {
                label: "Not established",
                meaning:
                    "No connection of this kind was established for this pair. That is a fact about what was measured, not about the texts.",
                tone: "unknown",
            };
        case "CLASS_NOT_CROSS_VEDA":
            return {
                label: "Not a pair relation",
                meaning:
                    "This kind of connection cannot join two Vedas by its own shape, so the cell is empty by construction rather than for want of evidence.",
                tone: "shape",
            };
        case "NOT_BUILT":
            return {
                label: "Never measured",
                meaning:
                    "No measure of this kind exists in this corpus. Unknown, and deliberately not shown as zero.",
                tone: "unknown",
            };
        case "UNRECONCILED":
            return {
                label: "Two counts disagree",
                meaning: "This cell was counted twice, the counts differ, and neither is published.",
                tone: "unknown",
            };
        default:
            return {
                label: "Status not supplied",
                meaning: "Read the scope notes before interpreting this cell.",
                tone: "unknown",
            };
    }
}

/**
 * The measurement writes its refusal reasons with a machine code in front of the
 * prose -- `REFUSED_MEDIATED_BY_THIRD_CORPUS. 96.1% of this pair's verses ...`.
 * The prose is the reason a reader wants; the code is a token for a log.
 */
export function plainNote(note?: string | null) {
    return (note ?? "").replace(/^[A-Z][A-Z0-9_]{3,}[.:]\s*/, "").trim();
}

/**
 * The two corpora of a pair, in full. The payload carries codes and an order; the
 * order is the payload's and is not re-sorted here, so `AV-RV` reads Atharvaveda
 * first exactly as the measurement returned it.
 */
export function pairSides(vedas?: string[] | null) {
    return (vedas ?? []).map((code) => vedaNames[code] ?? code);
}

/** "Atharvaveda and Rigveda", for a heading or a sentence with one pair in it. */
export function pairName(vedas?: string[] | null) {
    return listSentence(pairSides(vedas));
}

/**
 * "Atharvaveda-Rigveda", for a sentence that lists several pairs.
 *
 * `pairName` cannot be used there: joining two pairs that each contain "and" with a
 * third "and" produced "Atharvaveda and Rigveda and Rigveda and Samaveda", which
 * reads as four corpora rather than two pairs.
 */
export function pairDash(vedas?: string[] | null) {
    return pairSides(vedas).join("–");
}

/**
 * `SAMAVEDA_GRAMAGEYA_GANA` -> `Samaveda Gramageya Gana`.
 *
 * Every word takes a capital because these are the proper names of bodies of text,
 * not predicates: `humanizePredicate` alone renders "gopatha brahmana", which reads
 * as a description of something rather than the name of a book.
 */
export function corpusName(code: string) {
    return humanizePredicate(code)
        .split(" ")
        .map((word) => titleCase(word))
        .join(" ");
}

/** "a", "a and b", "a, b and c". */
export function listSentence(items: string[]) {
    if (items.length <= 1) return items[0] ?? "";
    return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
