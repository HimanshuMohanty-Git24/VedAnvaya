/**
 * The Ask VedAnvaya contract, and the words a reader sees for each of its codes.
 *
 * Hand-written rather than taken from `api-schema.ts`: the generated schema is
 * regenerated from the served OpenAPI document, and these routes were added after the
 * last generation. The shapes below track `vedagraph.api.ask.models`.
 */

export type AskMode = "AUTO" | "TEXTUAL" | "GRAPH" | "COMPARATIVE" | "RESEARCH";

export type AskVedaScope = "ALL" | "RV" | "SV" | "YV" | "AV";

export type SupportLevel = "STRONG" | "MODERATE" | "LIMITED" | "INSUFFICIENT";

export type EvidenceItemType =
    | "PASSAGE"
    | "ENTITY_FACT"
    | "GRAPH_PATH"
    | "METRIC"
    | "INTERPRETIVE_CLAIM"
    | "FORMULA_FAMILY"
    | "TEXTUAL_REUSE"
    | "ATTRIBUTION"
    | "CORPUS_DISTRIBUTION"
    | "LEXICAL_PRESENCE";

export type AskConversationTurn = { role: string; content: string };

export type AskRequest = {
    question: string;
    veda?: AskVedaScope | null;
    passage_context?: string | null;
    entity_context?: string | null;
    conversation_context?: AskConversationTurn[] | null;
    mode?: AskMode;
    debug?: boolean;
};

export type AskCitation = {
    id: string;
    citation: string;
    passage_key?: string | null;
    veda?: string | null;
};

export type AskEvidenceItem = {
    id: string;
    type: EvidenceItemType;
    passage_key?: string | null;
    citation?: string | null;
    veda?: string | null;
    sanskrit?: string | null;
    translation?: string | null;
    entity_label?: string | null;
    entity_type?: string | null;
    entity_key?: string | null;
    fact?: string | null;
    relationship_type?: string | null;
    source_label?: string | null;
    target_label?: string | null;
    claim_text?: string | null;
    claim_source?: string | null;
    evidence_basis?: string | null;
    knowledge_status?: string | null;
    /** What this item does NOT establish. Always rendered beside the item. */
    qualifier?: string | null;
};

export type AskEntityMention = {
    label: string;
    entity_key?: string | null;
    entity_type?: string | null;
    resolved: boolean;
    asked_as?: string | null;
    match_rank?: string | null;
};

export type AskRetrievalSummary = {
    channels_used: string[];
    channels_empty: string[];
    intents: string[];
    entities_resolved: string[];
    entities_unresolved: string[];
    veda_scope: string;
    evidence_count: number;
    planner_ms: number;
    retrieval_ms: number;
    synthesis_ms: number;
    total_ms: number;
};

export type AskResponse = {
    answer: string;
    status: string;
    support_level: SupportLevel;
    citations: AskCitation[];
    evidence: AskEvidenceItem[];
    entities: AskEntityMention[];
    related_questions: string[];
    caveats: Array<{ text: string; source: string }>;
    retrieval_summary: AskRetrievalSummary;
    interpretive_content_present: boolean;
    llm: { provider: string; model: string };
};

export type AskHealth = {
    ask_available: boolean;
    detail: string;
    llm?: Record<string, unknown> | null;
};

/** The server's deliberate error body. `hint` says what a deployer can do about it. */
export type ApiErrorBody = { error: string; detail: string; hint?: string | null };

export class AskError extends Error {
    constructor(
        message: string,
        readonly code: string,
        readonly status: number,
        readonly hint?: string | null,
    ) {
        super(message);
        this.name = "AskError";
    }

    /** A 503 from an unconfigured provider is a deployment fact, not a corpus fact. */
    get unavailable() {
        return this.code === "ASK_UNAVAILABLE";
    }
}

const UNREACHABLE = "The VedAnvaya knowledge service could not be reached.";

/**
 * Ask one question. Runs in the browser against the `/backend` rewrite, so the API base
 * never reaches the client bundle and no credential is involved on this side.
 */
export async function postAsk(body: AskRequest, signal?: AbortSignal): Promise<AskResponse> {
    let response: Response;
    try {
        response = await fetch("/backend/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify(body),
            signal,
        });
    } catch (reason) {
        if (reason instanceof DOMException && reason.name === "AbortError") throw reason;
        throw new AskError(UNREACHABLE, "NETWORK", 503);
    }

    if (!response.ok) {
        // A proxy or a 500 can answer with HTML, so a failed parse must not mask the status.
        const payload = (await response.json().catch(() => null)) as ApiErrorBody | null;
        throw new AskError(
            payload?.detail ?? UNREACHABLE,
            payload?.error ?? "REQUEST_FAILED",
            response.status,
            payload?.hint ?? null,
        );
    }

    return (await response.json()) as AskResponse;
}

/** Readiness. A 503 body is still a readable answer here, so it is parsed, not thrown. */
export async function fetchAskHealth(signal?: AbortSignal): Promise<AskHealth | null> {
    try {
        const response = await fetch("/backend/ask/health", {
            headers: { Accept: "application/json" },
            signal,
        });
        return (await response.json()) as AskHealth;
    } catch {
        return null;
    }
}

export const ASK_QUESTION_LIMIT = 2000;

/**
 * The caveat source the synthesiser stamps when generation hit its output cap.
 *
 * Truncation does not travel as a field on the response. The service appends a caveat with
 * this source, downgrades `status` to PARTIAL and holds `support_level` at LIMITED or below.
 * Reading the caveat is therefore reading the contract, not sniffing a string: this is the
 * only channel the backend has for saying the prose stops early while the evidence does not.
 */
export const TRUNCATION_SOURCE = "generation_truncated";

/** A truncated answer must never be presented as a complete one. */
export function truncationCaveat(result: AskResponse) {
    return result.caveats.find((caveat) => caveat.source === TRUNCATION_SOURCE) ?? null;
}

/**
 * What to say to someone who has been waiting.
 *
 * The response is not streamed and the backend reports no phase while it works, so there is
 * nothing to show but the time that has actually passed. These thresholds are read against
 * measured latency rather than chosen for feel: synthesis has been observed from 29.7s to
 * 248.7s with a median near 106s, so a wait of half a minute is ordinary and one of two
 * minutes is still inside the envelope. Each line says only what is known at that point and
 * none of them promises a finish.
 */
export const WAIT_NOTES: Array<{ at: number; note: string }> = [
    {
        at: 0,
        note: "Resolving the names in the question, running the retrieval channels, then writing from what they returned.",
    },
    {
        at: 15_000,
        note: "Retrieval is usually done by now and the answer is being written. Synthesis is the slow half.",
    },
    {
        at: 45_000,
        note: "Still synthesising. Questions that span collections or resolve several names take longer than a single-passage lookup.",
    },
    {
        at: 90_000,
        note: "A complex question can take several minutes. Nothing is wrong; the request is still open and the answer will appear here.",
    },
];

export function waitNoteFor(elapsed: number) {
    return WAIT_NOTES.reduce(
        (current, entry) => (elapsed >= entry.at ? entry : current),
        WAIT_NOTES[0],
    ).note;
}

/** Elapsed time, spoken rather than counted, so a reader is not watching a stopwatch. */
export function elapsedCopy(ms: number) {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s elapsed`;
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    return `${minutes}m ${String(rest).padStart(2, "0")}s elapsed`;
}

export const ASK_VEDA_SCOPES: Array<{ value: AskVedaScope; label: string }> = [
    { value: "ALL", label: "All four" },
    { value: "RV", label: "Rigveda" },
    { value: "SV", label: "Samaveda" },
    { value: "YV", label: "Yajurveda" },
    { value: "AV", label: "Atharvaveda" },
];

export const ASK_MODES: Array<{ value: AskMode; label: string; note: string }> = [
    { value: "AUTO", label: "Automatic", note: "Let the planner choose the channels" },
    { value: "TEXTUAL", label: "Textual", note: "Favour passages and their wording" },
    { value: "GRAPH", label: "Graph", note: "Favour recorded connections between entities" },
    { value: "COMPARATIVE", label: "Comparative", note: "Favour cross-collection comparison" },
    { value: "RESEARCH", label: "Research", note: "Widen retrieval across every channel" },
];

export const ASK_EXAMPLES = [
    "What is RV 1.1.1 about?",
    "How does Indra appear across the four Vedas?",
    "How are Agni and Soma connected?",
    "What does the Atharvaveda say about fever?",
    "Does the Yajurveda mention ayas?",
];

/** Support level is graded on the evidence, so it is never phrased as certainty. */
export function supportLevelCopy(level?: SupportLevel | string | null): {
    label: string;
    description: string;
    tone: "supported" | "partial" | "insufficient" | "unknown";
} {
    switch ((level ?? "").toUpperCase()) {
        case "STRONG":
            return {
                label: "Strong support",
                description: "Several retrieved items carry the answer's claims.",
                tone: "supported",
            };
        case "MODERATE":
            return {
                label: "Moderate support",
                description: "The claims are cited, on a narrow evidence base.",
                tone: "partial",
            };
        case "LIMITED":
            return {
                label: "Limited support",
                description:
                    "Little evidence was retrieved. Read the cited items before relying on this.",
                tone: "partial",
            };
        case "INSUFFICIENT":
            return {
                label: "Insufficient support",
                description:
                    "The retrieved evidence does not establish an answer. This is a statement about this build, not about the Vedas.",
                tone: "insufficient",
            };
        default:
            return {
                label: "Support not graded",
                description: "No support grade travelled with this answer.",
                tone: "unknown",
            };
    }
}

/**
 * Evidence groups, in the order a reader should meet them: the text first, then what was
 * recorded of it, then what was measured, then what someone concluded.
 */
export const EVIDENCE_TYPE_ORDER: EvidenceItemType[] = [
    "PASSAGE",
    "TEXTUAL_REUSE",
    "FORMULA_FAMILY",
    "ATTRIBUTION",
    "ENTITY_FACT",
    "GRAPH_PATH",
    "LEXICAL_PRESENCE",
    "CORPUS_DISTRIBUTION",
    "METRIC",
    "INTERPRETIVE_CLAIM",
];

export function evidenceTypeCopy(type: EvidenceItemType | string): {
    label: string;
    note: string;
} {
    switch (type) {
        case "PASSAGE":
            return { label: "Passages", note: "Verses held in this build, with their wording." };
        case "TEXTUAL_REUSE":
            return {
                label: "Shared wording",
                note: "Passages whose wording stands in more than one place.",
            };
        case "FORMULA_FAMILY":
            return {
                label: "Formula families",
                note: "A shared formula is not by itself a claim that one passage reused another.",
            };
        case "ATTRIBUTION":
            return {
                label: "Dedications",
                note: "A hymn dedicated to a deity. Never interchangeable with a mention of it.",
            };
        case "ENTITY_FACT":
            return { label: "Entity facts", note: "What the graph records of a named subject." };
        case "GRAPH_PATH":
            return {
                label: "Recorded connections",
                note: "Stored relationships between two subjects.",
            };
        case "LEXICAL_PRESENCE":
            return {
                label: "Term searches",
                note: "A measured search for a term, with the searchable surface of each collection reported. A count of zero is a lower bound, not an absence.",
            };
        case "CORPUS_DISTRIBUTION":
            return {
                label: "Distribution across collections",
                note: "Per-collection counts with all three referent-certainty tiers reported.",
            };
        case "METRIC":
            return { label: "Measures", note: "Figures counted over this graph." };
        case "INTERPRETIVE_CLAIM":
            return {
                label: "Interpretation",
                note: "A reading attributed to a source, not something the texts state.",
            };
        default:
            return { label: type.toLowerCase().replaceAll("_", " "), note: "Evidence as stored." };
    }
}

export function matchRankCopy(rank?: string | null) {
    switch ((rank ?? "").toUpperCase()) {
        case "EXACT_LABEL":
            return "matched this entity's name";
        case "EXACT_ALIAS":
            return "matched a recorded alias";
        case "TOKEN_IN_LABEL":
            return "matched one word of a longer name, so the binding is weaker";
        default:
            return "match basis not recorded";
    }
}

/** Channel identifiers are internal names; give a reader the readable form. */
export function channelLabel(channel: string) {
    return channel.toLowerCase().replaceAll("_", " ");
}

export function formatMs(value: number) {
    if (!Number.isFinite(value)) return "not recorded";
    if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
    return `${Math.round(value)} ms`;
}

/**
 * A long scope statement, split into the clauses it is already made of.
 *
 * ## What this is for
 *
 * "What this answer does not settle" and an evidence item's "Does not establish" are the
 * most careful writing in the product and were the hardest to read: a single paragraph of
 * four or five sentences, set at 13px in a 560px drawer, each sentence qualifying a
 * different thing. Measured on a live answer, one qualifier ran 412 characters over six
 * lines with no visual break in it. A reader skims a wall like that, which is exactly the
 * text they must not skim.
 *
 * ## What it is not
 *
 * **Not a rewrite, and not a summary.** Every character of the input appears in the output.
 * `clauses(t).join(" ") === t.trim()` is asserted in `tests/unit/ask-clauses.test.ts`, and it
 * is the whole contract: this function is allowed to decide where a line ends and nothing
 * else. Shortening a statement about what the evidence does not establish would be the worst
 * available edit to this product.
 *
 * ## Why the splitter is conservative
 *
 * These statements are full of citations, and a citation contains full stops. `VS 18.21
 * inventories the pressing gear` and `AVS 5.22.2 names the deity` both carry a period
 * mid-token, and a naive split on `. ` cuts them in half. So a break needs three things at
 * once: a letter before the stop, a space after it, and a capital or an opening quote
 * starting the next word. `18.21` fails the first test, `e.g. the` fails the third.
 *
 * A labelled clause - `What it does not establish:` - is also a break, because it is the
 * author's own division and the sentence after it is a different statement from the one
 * before.
 */
export function clauses(text: string | null | undefined): string[] {
    const trimmed = (text ?? "").trim();
    if (!trimmed) return [];

    const parts: string[] = [];
    let start = 0;
    for (let i = 0; i < trimmed.length - 1; i += 1) {
        const here = trimmed[i];
        const next = trimmed[i + 1];

        /* A labelled clause. The colon stays with the label it introduces. */
        if (here === ":" && next === " " && /[a-z]/.test(trimmed[i - 1] ?? "")) {
            const label = trimmed.slice(start, i + 1);
            /* Only where the label is short enough to be a label rather than a sentence that
               happens to end in a colon. Measured: the real ones run 12 to 34 characters. */
            if (label.trim().length <= 48) {
                parts.push(label.trim());
                start = i + 2;
                continue;
            }
        }

        if (here !== "." && here !== "?" && here !== "!") continue;
        if (next !== " ") continue;
        /* A letter before the stop, never a digit: `18.21` is one token. */
        if (!/[a-zA-Z)\]"'’”]/.test(trimmed[i - 1] ?? "")) continue;
        /* A capital, a digit-led citation or an opening quote after it. `e.g. the` is not a
           break; `RV 1.32.1 is` is. */
        if (!/[A-Z0-9"'‘“]/.test(trimmed[i + 2] ?? "")) continue;

        parts.push(trimmed.slice(start, i + 1).trim());
        start = i + 2;
    }
    const tail = trimmed.slice(start).trim();
    if (tail) parts.push(tail);
    return parts.length > 0 ? parts : [trimmed];
}

/**
 * The subsystem that raised a caveat, in words.
 *
 * `certainty_scope`, `generation_truncated`, `formula_family_span_census`: registry keys,
 * printed raw under every scope note. They are genuine provenance - which part of the
 * service is speaking - and they were reading as leaked identifiers, which is a different
 * thing and teaches a reader to ignore the line. Only the spelling changes.
 */
export function caveatSourceLabel(source: string | null | undefined) {
    if (!source) return "not recorded";
    return source.toLowerCase().replaceAll("_", " ");
}
