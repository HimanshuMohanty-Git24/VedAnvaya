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

/*
 * These interfaces name what `/api/v1/completeness` actually returns.
 *
 * They did not, and the divergence was invisible for a structural reason worth keeping in
 * view: the endpoint 404'd on the running server, so `loadCompleteness` fell through to
 * the literal below on every request and the declared field names were never tested
 * against a real payload. Measured once the route was live, five of them were fiction --
 * `total`, `coverage_pct`, `policy_statement` and `relationship_types` are names this file
 * invented, and `has_own_dedicated_english` was a field nobody served. Each would have
 * rendered `undefined` the first time the backend answered.
 *
 * Three were renamed here to the backend's spelling; `has_own_dedicated_english` was worth
 * keeping and is now computed by the service, because "the Samaveda has no English of its
 * own" is a distinction the product makes and `dedicated_english > 0` at the call site is
 * that rule written out four times.
 */
export interface TranslationVedaItem {
    veda: string;
    total_mantras: number;
    dedicated_english: number;
    range_covered: number;
    reused_rendering: number;
    non_english: number;
    uncovered: number;
    coverage_percentage: number;
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
    truth_statement: string;
}

export interface SamavedaNotationCompleteness {
    canonical_corpus_mantras: number;
    validated_notation_witnesses: number;
    unaligned_withheld_verses: number;
    musicalized_as_edges: number;
    gana_works_modeled: number;
    gates_passed: string[];
    evidence_class: string;
    notation_system: string;
    source_supplied: boolean;
    interpreted_into_pitch: boolean;
    withheld_reason: string;
    gana_object_layer: string;
    truth_statement: string;
}

export interface AudioCompleteness {
    released_catalogue_records: number;
    released_by_veda: Record<string, number>;
    released_scope_keys_by_veda: Record<string, number>;
    /**
     * The catalogue split by publication tier, and it must never be summed away.
     *
     * `OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION` publishes source-mapped recordings that
     * nobody has listened to. 20 of 17,780 have been heard, and a surface that shows only
     * the total is one sentence away from calling the other 17,760 verified.
     */
    released_by_tier: Record<string, number>;
    released_by_veda_and_tier: Record<string, Record<string, number>>;
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
    /**
     * Where this object came from. Set by `loadCompleteness`, never by the backend.
     *
     * A surface that prints a certified figure can ask whether the figure is live. It exists
     * because the alternative is what this file used to do silently: serve a frozen copy of
     * last week's release numbers as though the service had answered.
     */
    data_source?: "api" | "fallback";
}

/**
 * The last-resort copy of the certified state, and it is a hazard, not a convenience.
 *
 * `/api/v1/completeness` did not exist on the running backend when this pass began - the route
 * had been added in the previous commit and the server predated it - so every figure on the
 * homepage, /vedas, /limits and /sources came from this literal, and nothing on any of those
 * pages said so. That is precisely the failure the constant is supposed to protect against:
 * a fallback nobody can see is indistinguishable from live data that happens to be wrong.
 *
 * Two things keep it honest now. `loadCompleteness` stamps `data_source` so a surface can tell
 * and a reader can be told. And `scripts/audit-completeness-fallback.mjs`, wired into
 * `pnpm audit`, fetches the live endpoint and fails the audit when this constant and the
 * backend disagree - or when the endpoint cannot be reached at all, because a check that
 * passes when it could not run is not a check.
 *
 * Keep the two versioned together: this is the state certified at
 * `certified_release_commit`, and changing the backend's figures means changing this and
 * running the audit, not either one alone.
 */
export const FALLBACK_COMPLETENESS: CompletenessResponse = {
        "data_status": "SUPPORTED",
        "as_of_date": "2026-09-19",
        "certified_release_commit": "50a40429103fa32a5667ee58c72c029cfbeb0f74",
        "total_canonical_mantras": 20210,
        "corpora": [
            {
                "veda": "RV",
                "traditional_name": "Rigveda Samhita",
                "devanagari_name": "ऋग्वेद",
                "recension": "Śākala recension",
                "scope_honest_label": "Rigveda Samhita - Śākala recension",
                "scope_note": "Samhita only, in one recension. No Brahmana, Aranyaka or Upanisad layer is held.",
                "canonical_mantras": 10552,
                "structure": "Mandala → Sukta → Mantra",
                "excluded_corpora": [
                    "SECOND_RIGVEDIC_RECENSION",
                    "RIGVEDIC_BRAHMANA",
                    "RIGVEDIC_ARANYAKA",
                    "UPANISAD"
                ],
                "limitations": "Samhita only, in the Śākala recension. The Āśvalāyana recension is absent."
            },
            {
                "veda": "SV",
                "traditional_name": "Samaveda Samhita",
                "devanagari_name": "सामवेद",
                "recension": "Kauthuma recension, ārcika only",
                "scope_honest_label": "Samaveda Samhita - Kauthuma ārcika only (gāna corpus NOT included)",
                "scope_note": "Kauthuma ārcika verse corpus only. The gāna song-books are not included. 1,136 validated notation witnesses are held; no melody or pitch is inferred.",
                "canonical_mantras": 1844,
                "structure": "Collection → Prapathaka → Ardha → Dasati → Verse",
                "excluded_corpora": [
                    "SAMAVEDA_GRAMAGEYA_GANA",
                    "SAMAVEDA_ARANYAKAGEYA_GANA",
                    "SAMAVEDA_UHAGANA",
                    "SAMAVEDA_UHYAGANA",
                    "SECOND_SAMAVEDIC_RECENSION",
                    "SAMAVEDIC_BRAHMANA",
                    "UPANISAD"
                ],
                "limitations": "Ārcika verses only. Gāna song-books not included; no canonical Gāna works or MUSICALIZED_AS edges."
            },
            {
                "veda": "YV",
                "traditional_name": "Vājasaneyi Samhitā",
                "devanagari_name": "यजुर्वेद",
                "recension": "Śukla, Vājasaneyi Mādhyandina",
                "scope_honest_label": "Vājasaneyi Samhitā - Śukla Yajurveda, Mādhyandina recension",
                "scope_note": "Śukla (White) Yajurveda only. The Krishna Yajurveda is not held at all.",
                "canonical_mantras": 1975,
                "structure": "Adhyaya → Mantra",
                "excluded_corpora": [
                    "KRISHNA_YAJURVEDA_TAITTIRIYA",
                    "KRISHNA_YAJURVEDA_KATHAKA",
                    "KRISHNA_YAJURVEDA_MAITRAYANI",
                    "KRISHNA_YAJURVEDA_KAPISTHALA",
                    "SHUKLA_YAJURVEDA_KANVA_RECENSION",
                    "SATAPATHA_BRAHMANA",
                    "UPANISAD"
                ],
                "limitations": "White Yajurveda only. Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala) absent entirely."
            },
            {
                "veda": "AV",
                "traditional_name": "Atharvaveda Samhita",
                "devanagari_name": "अथर्ववेद",
                "recension": "Śaunaka recension",
                "scope_honest_label": "Atharvaveda Samhita - Śaunaka recension",
                "scope_note": "Śaunaka recension only, held as a working private corpus. Paippalāda recension is absent.",
                "canonical_mantras": 5839,
                "structure": "Kanda → Sukta → Mantra",
                "excluded_corpora": [
                    "ATHARVAVEDA_PAIPPALADA_RECENSION",
                    "GOPATHA_BRAHMANA",
                    "UPANISAD"
                ],
                "limitations": "Śaunaka recension only. The Paippalāda recension is substantially different and absent."
            }
        ],
        "translations": {
            "by_veda": {
                "RV": {
                    "veda": "RV",
                    "total_mantras": 10552,
                    "dedicated_english": 10480,
                    "range_covered": 60,
                    "reused_rendering": 0,
                    "non_english": 6,
                    "uncovered": 6,
                    "independent_english": 10540,
                    "coverage_percentage": 99.94,
                    "has_own_dedicated_english": true,
                    "notes": "High dedicated English coverage (10,480 verses). 60 verses covered in multi-verse ranges; 6 Latin substitutions; 6 mantras uncovered."
                },
                "SV": {
                    "veda": "SV",
                    "total_mantras": 1844,
                    "dedicated_english": 0,
                    "range_covered": 0,
                    "reused_rendering": 173,
                    "non_english": 0,
                    "uncovered": 1671,
                    "independent_english": 0,
                    "coverage_percentage": 9.38,
                    "has_own_dedicated_english": false,
                    "notes": "No own translation layer. 173 verses carry published English renderings reused from verified character-identical Rigvedic parallels; 1,671 mantras uncovered."
                },
                "YV": {
                    "veda": "YV",
                    "total_mantras": 1975,
                    "dedicated_english": 1950,
                    "range_covered": 0,
                    "reused_rendering": 0,
                    "non_english": 0,
                    "uncovered": 25,
                    "independent_english": 1950,
                    "coverage_percentage": 98.73,
                    "has_own_dedicated_english": true,
                    "notes": "1,950 verses carry dedicated English translations; 25 mantras uncovered."
                },
                "AV": {
                    "veda": "AV",
                    "total_mantras": 5839,
                    "dedicated_english": 5715,
                    "range_covered": 68,
                    "reused_rendering": 21,
                    "non_english": 18,
                    "uncovered": 17,
                    "independent_english": 5783,
                    "coverage_percentage": 99.71,
                    "has_own_dedicated_english": true,
                    "notes": "5,715 dedicated English renderings, 68 range-covered, 21 reused from Rigveda parallels, 18 Latin substitutions, 17 uncovered."
                }
            },
            "total_mantras": 20210,
            "total_dedicated_english": 18145,
            "total_range_covered": 128,
            "total_reused_rendering": 194,
            "total_non_english": 24,
            "total_uncovered": 1719,
            "truth_statement": "Translation coverage is explicitly typed into five states: dedicated English, multi-verse range coverage, reused parallel rendering, non-English (Latin) substitution, and uncovered remainder. For the Samaveda, 'no own translation' is not 'no translation available at all': 173 verses carry verified reused English from Rigvedic parallels."
        },
        "samaveda_notation": {
            "canonical_corpus_mantras": 1844,
            "validated_notation_witnesses": 1136,
            "gates_passed": [
                "Gate A: PASS",
                "Gate B: PASS",
                "Gate C: SURVIVED"
            ],
            "evidence_class": "PARALLEL_WITNESS / PARALLEL_TEXT",
            "notation_system": "Kauthuma numeric svara (source-printed codepoints)",
            "source_supplied": true,
            "interpreted_into_pitch": false,
            "unaligned_withheld_verses": 708,
            "withheld_reason": "Unaligned or unsupported notation rows withheld",
            "gana_object_layer": "OUT_OF_SCOPE",
            "gana_works_modeled": 0,
            "musicalized_as_edges": 0,
            "truth_statement": "VedAnvaya holds the Kauthuma Ārcika as its canonical Samaveda text (1,844 mantras). Source-explicit notation witnesses are available for 1,136 aligned verses (validated through Gates A, B, and C). Unaligned/unsupported notation remains withheld (708 verses). VedAnvaya does not model the canonical Gāna corpus as separate Gāna works and does not assert MUSICALIZED_AS relations."
        },
        "audio": {
            "released_catalogue_records": 17780,
            "released_by_veda": {
                "RV": 10552,
                "AV": 5451,
                "YV": 1777,
                "SV": 0
            },
            "released_scope_keys_by_veda": {
                "RV": 10552,
                "AV": 5451,
                "YV": 1777,
                "SV": 0
            },
            "released_by_tier": {
                "RELEASED_VERIFIED": 20,
                "SOURCE_MAPPED_UNREVIEWED": 17760
            },
            "released_by_veda_and_tier": {
                "AV": {
                    "RELEASED_VERIFIED": 20,
                    "SOURCE_MAPPED_UNREVIEWED": 5431
                },
                "RV": {
                    "RELEASED_VERIFIED": 0,
                    "SOURCE_MAPPED_UNREVIEWED": 10552
                },
                "SV": {
                    "RELEASED_VERIFIED": 0,
                    "SOURCE_MAPPED_UNREVIEWED": 0
                },
                "YV": {
                    "RELEASED_VERIFIED": 0,
                    "SOURCE_MAPPED_UNREVIEWED": 1777
                }
            },
            "owner_audible_sample_status": "ACCEPTED",
            "owner_sample_reviewed": 20,
            "owner_sample_verified": 20,
            "owner_sample_rejected": 0,
            "queue_total": 1021,
            "not_individually_heard": 1001,
            "queue_rows_promoted": 0,
            "withheld_gates": [
                "No Samavedic recitation is catalogued from any source.",
                "Recordings are streamed from their publishers; none is redistributed here.",
                "Human audible review is a per-recording badge, not a condition of publication."
            ],
            "truth_statement": "17,780 recitations are catalogued (RV 10,552; AV 5,451; YV 1,777; SV 0). 20 of them have been listened to and confirmed by a person; the remaining 17,760 are mapped to their verse and checked against its text automatically, and no one has heard them. They are not described as human-verified."
        },
        "ask_benchmark": {
            "benchmark_version": "ask_benchmark_v1",
            "status": "COMPLETE",
            "total_questions": 60,
            "effective_acceptable": "60/60",
            "supported_correct": 39,
            "partial_correct": 4,
            "insufficient_evidence_refused": 17,
            "misleading": 0,
            "hallucinated": 0,
            "truth_statement": "Ask formal 60 benchmark achieved 60/60 acceptable results (39 SUPPORTED_CORRECT, 4 PARTIAL_CORRECT, 17 INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED) with 0 MISLEADING and 0 HALLUCINATED claims. Ask returns PARTIAL or INSUFFICIENT_EVIDENCE when the knowledge graph lacks evidence; it is not factually omniscient."
        },
        "truth_summary": "VedAnvaya holds 20,210 canonical mantras across four Vedic Samhitas in one recension each (RV 10,552; SV 1,844; YV 1,975; AV 5,839), 18,145 dedicated English translations and 194 renderings reached through a verified parallel, 1,136 validated Samaveda notation witnesses, and 17,780 catalogued recordings."
    };

export async function loadCompleteness(): Promise<CompletenessResponse> {
    const res = await load<CompletenessResponse>("/completeness");
    if (res.ok && res.data) {
        return { ...res.data, data_source: "api" };
    }
    return { ...FALLBACK_COMPLETENESS, data_source: "fallback" };
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
