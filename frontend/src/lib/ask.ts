/**
 * The Ask VedaGraph contract, and the words a reader sees for each of its codes.
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

const UNREACHABLE = "The VedaGraph knowledge service could not be reached.";

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
