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

/**
 * Prose, or a bracket that turned out not to hold any evidence id.
 *
 * `emphasis` is set where the model wrapped the run in `**`. See `splitEmphasis`.
 */
export type AnswerTextSegment = { kind: "text"; text: string; emphasis?: boolean };

/** One rendered marker. Holds every id in the group, in the order written. */
export type AnswerCitationSegment = { kind: "citation"; ids: string[] };

export type AnswerSegment = AnswerTextSegment | AnswerCitationSegment;

/**
 * One paragraph of the answer, already split into prose and markers.
 *
 * `bullets` is set where the whole block was written as a markdown list. See `parseAnswer`.
 */
export type AnswerParagraph = { segments: AnswerSegment[]; bullets?: AnswerSegment[][] };

/**
 * `**bold**`, rendered rather than printed.
 *
 * The synthesis models write markdown, because that is what models write. Nothing asks them
 * to and nothing here can stop them, and the backend does not strip it: measured on a live
 * answer, the prose arrived reading `**Indra together with Vayu**, not Agni` and the page
 * printed the asterisks. That is the frontend failing to render what it was given rather
 * than the model failing to answer, and it is fixed here rather than by asking the
 * generator for something different - which would be a change to a system this phase must
 * not touch.
 *
 * Only a doubled asterisk. A single one is left alone: in a scope note it is far more
 * likely to be a footnote mark or a multiplication sign than an italic, and guessing wrong
 * turns a scholar's asterisk into invisible formatting.
 */
const BOLD_RUN = /\*\*(.+?)\*\*/g;

function splitEmphasis(text: string): AnswerTextSegment[] {
    const out: AnswerTextSegment[] = [];
    let cursor = 0;
    for (const match of text.matchAll(BOLD_RUN)) {
        const start = match.index ?? 0;
        if (start > cursor) out.push({ kind: "text", text: text.slice(cursor, start) });
        out.push({ kind: "text", text: match[1], emphasis: true });
        cursor = start + match[0].length;
    }
    if (cursor < text.length) out.push({ kind: "text", text: text.slice(cursor) });
    return out;
}

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
        if (text) segments.push(...splitEmphasis(text));
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
const BULLET_LINE = /^\s*[-*•]\s+/;

export function parseAnswer(answer: string): AnswerParagraph[] {
    return (answer ?? "")
        .split(/\n\s*\n/)
        .map((block) => block.trim())
        .filter(Boolean)
        .map((block) => {
            /*
             * A block written as a markdown list is rendered as one.
             *
             * Paragraphs are split on blank lines, so a four-item list arrives as a single
             * block with newlines inside it - and a newline inside a `<p>` collapses to a
             * space. Measured on a live answer, four separate findings about four separate
             * hymns ran together into one line reading "- RV 1.2.5-6 invoke ... - RV 1.3.4-5
             * address ... - RV 1.1.1-4 address ...", which is the author's own structure
             * being discarded at the last step.
             *
             * Every line must be a bullet. A block with one dashed line in it is prose that
             * happens to contain a dash, and turning that into a list would be inventing
             * structure rather than keeping it.
             */
            const lines = block
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean);
            if (lines.length > 1 && lines.every((line) => BULLET_LINE.test(line))) {
                return {
                    segments: [],
                    bullets: lines.map((line) =>
                        parseAnswerSegments(line.replace(BULLET_LINE, "")),
                    ),
                };
            }
            return { segments: parseAnswerSegments(block) };
        });
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
