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
const UNAVAILABLE = "The VedaGraph knowledge service did not respond.";
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
