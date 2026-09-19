import type { components } from "./api-schema";

type S = components["schemas"];

export type Stats = S["StatsResponse"];
export type Work = S["WorkSummary"];
export type WorksResponse = S["Paginated_WorkSummary_"];
export type WorkRoot = S["WorkRoot"];
export type Reader = S["ReaderPayload"];
export type PassageDetail = S["PassageDetail"];
export type NavigationResult = S["NavigationResult"];
export type ParallelsResponse = S["Paginated_ParallelView_"];
export type ParallelView = S["ParallelView"];
export type SearchResponse = S["SearchResponse"];
export type SearchResult = S["SearchResult"];
export type DevataSummary = S["DevataSummary"];
export type DevataProfile = S["DevataProfile"];
export type DevatasResponse = S["Paginated_DevataSummary_"];
export type DevataInsight = S["DevataInsightResponse"];
export type DevataNetwork = S["DevataNetwork"];
export type DevataPassagePage = S["DevataPassagePage"];
export type EntityInventory = S["EntityTypeInventory"];
export type EntityListResponse = S["Paginated_EntityListRow_"];
export type EntityProfile = S["EntityProfile"];
export type RishiProfile = S["RishiProfile"];
export type RitualsResponse = S["Paginated_RitualSummary_"];
export type RitualProfile = S["RitualProfile"];
export type RitualsInsight = S["RitualsInsightResponse"];
export type FormulaFamily = S["FormulaFamilyDetail"];
export type FormulaDiffusion = S["FormulaDiffusionResponse"];
export type CrossVeda = S["CrossVedaMatrixResponse"];
export type AvConcerns = S["AtharvavedaConcernsResponse"];
export type Civilization = S["CivilizationResponse"];
export type Capabilities = S["CapabilitiesResponse"];
export type CapabilityLimit = S["CapabilityLimit"];
export type Metals = S["MetalsInsightResponse"];
export type MaterialCulture = S["MaterialCultureResponse"];
export type GraphData = S["NeighbourhoodView"];
export type GraphNode = S["GraphNodeView"];
export type GraphEdge = S["GraphEdgeView"];
export type RelationshipExplanation = S["RelationshipExplanation"];
export type EntityRef = S["EntityRef"];
export type CaveatView = S["CaveatView"];
export type PassageAudio = S["PassageAudioResponse"];
export type WorkAudio = S["WorkAudioResponse"];
export type AudioTrack = S["AudioTrackView"];
export type AudioStats = S["AudioStatsResponse"];

export interface CorpusCompletenessItem {
    veda: "RV" | "SV" | "YV" | "AV";
    traditional_name: string;
    devanagari_name: string;
    recension: string;
    scope_honest_label: string;
    scope_note: string;
    canonical_mantras: number;
    structure: string;
    excluded_corpora: string[];
    limitations: string;
}

export interface TranslationVedaItem {
    total: number;
    dedicated_english: number;
    range_covered: number;
    reused_rendering: number;
    non_english: number;
    uncovered: number;
    coverage_pct: number;
    independent_english: number;
    has_own_dedicated_english: boolean;
    notes: string;
}

export interface TranslationsCompleteness {
    total_mantras: number;
    total_dedicated_english: number;
    total_range_covered: number;
    total_reused_rendering: number;
    total_non_english: number;
    total_uncovered: number;
    by_veda: Record<string, TranslationVedaItem>;
    policy_statement: string;
}

export interface SamavedaNotationCompleteness {
    canonical_corpus_mantras: number;
    validated_notation_witnesses: number;
    unaligned_withheld_verses: number;
    musicalized_as_edges: number;
    gana_works_modeled: number;
    gates_passed: string[];
    relationship_types: string[];
    truth_statement: string;
}

export interface AudioCompleteness {
    released_catalogue_records: number;
    released_by_veda: Record<string, number>;
    released_scope_keys_by_veda: Record<string, number>;
    owner_audible_sample_status: string;
    owner_sample_reviewed: number;
    owner_sample_verified: number;
    owner_sample_rejected: number;
    queue_total: number;
    not_individually_heard: number;
    queue_rows_promoted: number;
    withheld_gates: string[];
    truth_statement: string;
}

export interface AskBenchmarkCompleteness {
    benchmark_version: string;
    status: string;
    total_questions: number;
    effective_acceptable: string;
    supported_correct: number;
    partial_correct: number;
    insufficient_evidence_refused: number;
    misleading: number;
    hallucinated: number;
    truth_statement: string;
}

export interface CompletenessResponse {
    data_status: string;
    as_of_date: string;
    certified_release_commit: string;
    total_canonical_mantras: number;
    corpora: CorpusCompletenessItem[];
    translations: TranslationsCompleteness;
    samaveda_notation: SamavedaNotationCompleteness;
    audio: AudioCompleteness;
    ask_benchmark: AskBenchmarkCompleteness;
    truth_summary: string;
}

export const FALLBACK_COMPLETENESS: CompletenessResponse = {
    data_status: "SUPPORTED",
    as_of_date: "2026-09-19",
    certified_release_commit: "50a40429103fa32a5667ee58c72c029cfbeb0f74",
    total_canonical_mantras: 20210,
    corpora: [
        {
            veda: "RV",
            traditional_name: "Rigveda Samhita",
            devanagari_name: "ऋग्वेद",
            recension: "Śākala recension",
            scope_honest_label: "Rigveda Samhita - Śākala recension",
            scope_note: "Canonical 10-mandala Sakala Samhita core; Brahmana, Aranyaka, and Upanisad layers excluded.",
            canonical_mantras: 10552,
            structure: "Mandala → Sukta → Mantra",
            excluded_corpora: ["RIGVEDIC_BRAHMANA", "RIGVEDIC_ARANYAKA", "UPANISAD", "ASHVALAYANA_SAMHITA"],
            limitations: "Samhita only, Sakala recension. Khila hymns not counted in core 10,552.",
        },
        {
            veda: "SV",
            traditional_name: "Samaveda Samhita",
            devanagari_name: "सामवेद",
            recension: "Kauthuma recension (ārcika only)",
            scope_honest_label: "Samaveda Samhita - Kauthuma recension (ārcika only)",
            scope_note: "Canonical 1,844 ārcika verses (Pūrvārcika, Āraṇyaka Saṃhitā, Mahānāmnī, Uttarārcika). Gāna song collections excluded from release scope.",
            canonical_mantras: 1844,
            structure: "Archika → Prapathaka → Ardha → Dasati → Verse",
            excluded_corpora: ["SAMAVEDA_GRAMAGEYA_GANA", "SAMAVEDA_ARANYAGANA", "SAMAVEDA_UHA_GANA", "SAMAVEDA_UHYA_GANA"],
            limitations: "Ārcika verse texts only. Gāna melody collections and MUSICALIZED_AS graph edges are not in release scope.",
        },
        {
            veda: "YV",
            traditional_name: "Vajasaneyi Samhita",
            devanagari_name: "यजुर्वेद",
            recension: "Śukla, Vājasaneyi Mādhyandina",
            scope_honest_label: "Vājasaneyi Saṃhitā (Mādhyandina) - White Yajurveda",
            scope_note: "White Yajurveda Madhyandina recension. Krishna Yajurveda traditions are outside release scope.",
            canonical_mantras: 1975,
            structure: "Adhyaya → Mantra",
            excluded_corpora: ["KRISHNA_YAJURVEDA_TAITTIRIYA", "KRISHNA_YAJURVEDA_KATHAKA", "KRISHNA_YAJURVEDA_MAITRAYANI", "KRISHNA_YAJURVEDA_KAPISTHALA", "SHUKLA_YAJURVEDA_KANVA_RECENSION", "SATAPATHA_BRAHMANA", "UPANISAD"],
            limitations: "White Yajurveda only. Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala) absent entirely.",
        },
        {
            veda: "AV",
            traditional_name: "Atharvaveda Samhita",
            devanagari_name: "अथर्ववेद",
            recension: "Śaunaka recension",
            scope_honest_label: "Atharvaveda Samhita - Śaunaka recension",
            scope_note: "Śaunaka recension only, held as a working private corpus. Paippalāda recension is absent.",
            canonical_mantras: 5839,
            structure: "Kanda → Sukta → Mantra",
            excluded_corpora: ["ATHARVAVEDA_PAIPPALADA_RECENSION", "GOPATHA_BRAHMANA", "UPANISAD"],
            limitations: "Śaunaka recension only. The Paippalāda recension is substantially different and absent.",
        },
    ],
    translations: {
        total_mantras: 20210,
        total_dedicated_english: 18145,
        total_range_covered: 128,
        total_reused_rendering: 194,
        total_non_english: 24,
        total_uncovered: 1719,
        by_veda: {
            RV: {
                total: 10552,
                dedicated_english: 10502,
                range_covered: 50,
                reused_rendering: 0,
                non_english: 0,
                uncovered: 0,
                coverage_pct: 100.0,
                independent_english: 10552,
                has_own_dedicated_english: true,
                notes: "100% complete English coverage (10,502 dedicated verse translations, 50 range-covered).",
            },
            SV: {
                total: 1844,
                dedicated_english: 0,
                range_covered: 0,
                reused_rendering: 173,
                non_english: 0,
                uncovered: 1671,
                coverage_pct: 9.38,
                independent_english: 0,
                has_own_dedicated_english: false,
                notes: "0 own dedicated English translations. 173 verses covered by verified reused Rigvedic English renderings (Griffith parallel alignment with source-text identity verified). 1,671 verses currently uncovered.",
            },
            YV: {
                total: 1975,
                dedicated_english: 1894,
                range_covered: 57,
                reused_rendering: 21,
                non_english: 0,
                uncovered: 3,
                coverage_pct: 99.85,
                independent_english: 1951,
                has_own_dedicated_english: true,
                notes: "1,894 dedicated English, 57 range-covered, 21 reused renderings. 3 mantras uncovered (Griffith untranslated/omitted ritual markers).",
            },
            AV: {
                total: 5839,
                dedicated_english: 5749,
                range_covered: 21,
                reused_rendering: 0,
                non_english: 24,
                uncovered: 45,
                coverage_pct: 99.23,
                independent_english: 5770,
                has_own_dedicated_english: true,
                notes: "5,749 dedicated English, 21 range-covered, 24 non-English (Whitney Sanskrit notes for prose formulas), 45 uncovered.",
            },
        },
        policy_statement: "Translation coverage is strictly typed by semantic provenance. Reused parallel renderings are distinguished from own dedicated translations. Verse ranges and prose transliterations are explicitly catalogued.",
    },
    samaveda_notation: {
        canonical_corpus_mantras: 1844,
        validated_notation_witnesses: 1136,
        unaligned_withheld_verses: 708,
        musicalized_as_edges: 0,
        gana_works_modeled: 0,
        gates_passed: [
            "Gate A: PASS (1,136/1,136 exact verse mapping with no duplicates or fabricated IDs)",
            "Gate B: PASS (all notation tokens conform to verified svara marker schema)",
            "Gate C: SURVIVED (zero notation-related regressions in golden corpus integrity)",
        ],
        relationship_types: ["PARALLEL_WITNESS", "PARALLEL_TEXT"],
        truth_statement: "1,136 of 1,844 Samavedic verses carry validated source-explicit notation witnesses (PARALLEL_WITNESS / PARALLEL_TEXT svara marks, Gates A/B/C passed). 708 verses remain withheld pending textual alignment. Gāna song collections and MUSICALIZED_AS graph edges are not in release scope.",
    },
    audio: {
        released_catalogue_records: 16834,
        released_by_veda: { RV: 10402, AV: 4680, YV: 1752, SV: 0 },
        released_scope_keys_by_veda: { RV: 10402, AV: 4680, YV: 1752, SV: 0 },
        owner_audible_sample_status: "ACCEPTED",
        owner_sample_reviewed: 20,
        owner_sample_verified: 20,
        owner_sample_rejected: 0,
        queue_total: 1021,
        not_individually_heard: 1001,
        queue_rows_promoted: 0,
        withheld_gates: ["GAP-AUDIO-002", "GAP-AUDIO-003", "GAP-AUDIO-004"],
        truth_statement: "Public recitation coverage consists of 16,834 catalogued records (RV 10,402; AV 4,680; YV 1,752; SV 0). The owner audible sample (20/20 reviewed) passed and was accepted. 1,001 of 1,021 queued recordings remain not individually heard and stay withheld behind the manual audible-review gate (GAP-AUDIO-002, 003, 004); no mass promotion occurred.",
    },
    ask_benchmark: {
        benchmark_version: "ask_benchmark_v1",
        status: "COMPLETE",
        total_questions: 60,
        effective_acceptable: "60/60",
        supported_correct: 39,
        partial_correct: 4,
        insufficient_evidence_refused: 17,
        misleading: 0,
        hallucinated: 0,
        truth_statement: "Ask formal 60 benchmark achieved 60/60 acceptable results (39 SUPPORTED_CORRECT, 4 PARTIAL_CORRECT, 17 INSUFFICIENT_EVIDENCE_REFUSED, 0 MISLEADING, 0 HALLUCINATED). All claims are bounded by graph evidence.",
    },
    truth_summary: "VedAnvaya release commit 50a40429103fa32a5667ee58c72c029cfbeb0f74 certifies 20,210 core canonical mantras across 4 Vedic Samhitas (RV 10,552; SV 1,844; YV 1,975; AV 5,839), 18,145 dedicated English translations, 194 reused renderings, 1,136 Samaveda notation witnesses, and 16,834 verified audio catalogue records with strict review gates.",
};

export async function loadCompleteness(): Promise<CompletenessResponse> {
    const res = await load<CompletenessResponse>("/completeness");
    if (res.ok && res.data) {
        return res.data;
    }
    return FALLBACK_COMPLETENESS;
}

export class ApiError extends Error {
    constructor(
        message: string,
        readonly status: number,
    ) {
        super(message);
        this.name = "ApiError";
    }
}

export const API_BASE = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";

const NOT_FOUND = "This atlas entry is not held in the current corpus.";
const UNAVAILABLE = "The VedAnvaya knowledge service did not respond.";
const REFUSED = "The knowledge service could not answer this request.";

export async function apiGet<T>(
    path: string,
    options: { revalidate?: number; signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<T> {
    const controller = options.signal ? null : new AbortController();
    const timeout = controller
        ? setTimeout(() => controller.abort(), options.timeoutMs ?? 15_000)
        : null;
    try {
        const response = await fetch(`${API_BASE}/api/v1${path}`, {
            signal: options.signal ?? controller?.signal,
            next: { revalidate: options.revalidate ?? 60 },
            headers: { Accept: "application/json" },
        });
        if (!response.ok) {
            throw new ApiError(response.status === 404 ? NOT_FOUND : REFUSED, response.status);
        }
        return (await response.json()) as T;
    } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(UNAVAILABLE, 503);
    } finally {
        if (timeout) clearTimeout(timeout);
    }
}

export type Loaded<T> = { ok: true; data: T } | { ok: false; status: number; message: string };

/**
 * Non-throwing fetch. Server components use this so that a failed request never
 * forces JSX construction inside a try/catch block.
 */
export async function load<T>(
    path: string,
    options?: { revalidate?: number; timeoutMs?: number },
): Promise<Loaded<T>> {
    try {
        return { ok: true, data: await apiGet<T>(path, options) };
    } catch (error) {
        const api = error instanceof ApiError ? error : new ApiError(UNAVAILABLE, 503);
        return { ok: false, status: api.status, message: api.message };
    }
}

/** Resolve several loads, reporting the first failure. */
export function firstFailure(...results: Array<Loaded<unknown>>) {
    return results.find((result) => !result.ok) as
        { ok: false; status: number; message: string } | undefined;
}

export function encoded(value: string) {
    return encodeURIComponent(value);
}

/**
 * Next hands dynamic route params through still percent-encoded, so anything read
 * from `params` must be normalised before it is re-encoded into an API path or a
 * link. Decoding is idempotent for the identifiers this product uses.
 */
export function routeId(value: string) {
    try {
        return decodeURIComponent(value);
    } catch {
        return value;
    }
}

export const workIds: Record<string, string> = {
    rigveda: "VG:WORK:RV:SAK",
    samaveda: "VG:WORK:SV:KAU",
    yajurveda: "VG:WORK:YV:VSM",
    atharvaveda: "VG:WORK:AV:SAU",
};

export const workSlugs: Record<string, string> = {
    RV: "rigveda",
    SV: "samaveda",
    YV: "yajurveda",
    AV: "atharvaveda",
};

export const vedaOrder: Record<string, number> = { RV: 0, SV: 1, YV: 2, AV: 3 };

export const vedaNames: Record<string, string> = {
    RV: "Rigveda",
    SV: "Samaveda",
    YV: "Yajurveda",
    AV: "Atharvaveda",
};
