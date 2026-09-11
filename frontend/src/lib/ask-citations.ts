/**
 * Parsing the inline `[E1]` markers out of a synthesised answer.
 *
 * This mirrors `vedagraph.api.ask.citation.extract_cited_ids` on purpose. The backend
 * strips any id it could not verify against the evidence packet *before* responding, so
 * the prose that arrives here is already audited. If this reader used a narrower pattern
 * than the auditor, the mismatch would be silent and one-directional: a grouped
 * `[E6, E7, E8, E9]` that the backend checked and cleared would render as literal
 * bracket text, and four verified citations would lose their link to the evidence.
 *
 * So the two stages are the same two stages: find a bracket group, then pull every id
 * out of it. A bracket holding no `E<n>` is prose — `[see above]` is not a citation —
 * and is returned as text rather than dropped.
 */

/** A bracketed group, bounded like the backend's so a stray `[` cannot run away. */
const CITATION_GROUP = /\[([^[\]]{0,120}?)\]/g;

/** One evidence id inside a group. Word boundaries accept `,` `;` and `and` spellings. */
const ID_IN_GROUP = /\bE(\d+)\b/g;

/** Prose, or a bracket that turned out not to hold any evidence id. */
export type AnswerTextSegment = { kind: "text"; text: string };

/** One rendered marker. Holds every id in the group, in the order written. */
export type AnswerCitationSegment = { kind: "citation"; ids: string[] };

export type AnswerSegment = AnswerTextSegment | AnswerCitationSegment;

/** One paragraph of the answer, already split into prose and markers. */
export type AnswerParagraph = { segments: AnswerSegment[] };

function idsInGroup(body: string): string[] {
    const ids: string[] = [];
    for (const match of body.matchAll(ID_IN_GROUP)) {
        ids.push(`E${match[1]}`);
    }
    // A model that writes [E1, E1] cites one item, and two chips would overstate it.
    return [...new Set(ids)];
}

/**
 * Split one paragraph into prose and citation markers.
 *
 * Empty text runs are never emitted, so adjacent markers (`[E1][E2]`) yield two
 * citation segments with nothing between them.
 */
export function parseAnswerSegments(paragraph: string): AnswerSegment[] {
    const segments: AnswerSegment[] = [];
    let cursor = 0;

    const push = (text: string) => {
        if (text) segments.push({ kind: "text", text });
    };

    for (const match of paragraph.matchAll(CITATION_GROUP)) {
        const start = match.index ?? 0;
        const ids = idsInGroup(match[1]);
        if (!ids.length) continue; // Not a citation. Leave it inside the prose run.
        push(paragraph.slice(cursor, start));
        segments.push({ kind: "citation", ids });
        cursor = start + match[0].length;
    }

    push(paragraph.slice(cursor));
    return segments;
}

/**
 * Split an answer on blank lines, then parse each paragraph.
 *
 * A single trailing or leading blank line must not produce an empty paragraph, because
 * an empty `<p>` reads as a gap in the answer rather than as whitespace.
 */
export function parseAnswer(answer: string): AnswerParagraph[] {
    return (answer ?? "")
        .split(/\n\s*\n/)
        .map((block) => block.trim())
        .filter(Boolean)
        .map((block) => ({ segments: parseAnswerSegments(block) }));
}

/**
 * Every evidence id the answer cites, in first-appearance order, deduplicated.
 *
 * Used to report how much of the packet the prose actually leant on, which is a
 * different number from how much was retrieved.
 */
export function extractCitedIds(answer: string): string[] {
    const found: string[] = [];
    for (const match of (answer ?? "").matchAll(CITATION_GROUP)) {
        found.push(...idsInGroup(match[1]));
    }
    return [...new Set(found)];
}
