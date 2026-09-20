/**
 * The single translation layer between backend knowledge vocabulary and the words
 * a reader sees. Nothing in the UI should invent its own phrasing for a grade,
 * a certainty, or an absence.
 */

/** Node types that describe our own bookkeeping, never Vedic subject matter. */
export const INTERNAL_GRAPH_TYPES = new Set([
    "QAISSUE",
    "QA_ISSUE",
    "INTERNAL",
    "SOURCE",
    "SOURCEARTIFACT",
    "SOURCE_ARTIFACT",
    "TEXTVERSION",
    "TEXT_VERSION",
    "TRANSLATION",
    "PIPELINE_RUN",
    "PIPELINERUN",
    "AUDIT",
    "AUDITRECORD",
]);

export function normalizeType(value?: string | null) {
    return (value ?? "").toUpperCase().replaceAll(" ", "_");
}

export function isPublicGraphNode(node: { type?: string | null }) {
    return !INTERNAL_GRAPH_TYPES.has(normalizeType(node.type));
}

/**
 * A DEVATA-typed node is only drawn as a deity when the backend resolved it as one.
 * The Anukramani devata slot also holds human patrons and praise-of-a-gift labels.
 */
export function isRenderedAsDeity(node: { type?: string | null; is_deity?: boolean | null }) {
    return normalizeType(node.type) === "DEVATA" && node.is_deity === true;
}

export function isNonDeityDevataSlot(node: { type?: string | null; is_deity?: boolean | null }) {
    return normalizeType(node.type) === "DEVATA" && node.is_deity === false;
}

export function humanizePredicate(value?: string | null) {
    if (!value) return "not supplied";
    return value.toLowerCase().replaceAll("_", " ");
}

export function titleCase(value: string) {
    return value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * A graph class name, as a reader would say it.
 *
 * The ontology writes its classes in Pascal case - `NaturalPhenomenon`, `CosmicEntity`,
 * `RitualRole` - and `humanizePredicate` cannot help, because it lower-cases and splits on
 * underscores and there are none: it turns `NaturalPhenomenon` into `naturalphenomenon`.
 * So fifteen class names were printed raw on the evidence page, in the middle of English
 * sentences, and read as identifiers rather than as the things they name.
 *
 * Splits on a lower-to-upper boundary and on the underscore, so both spellings in the
 * ontology land in the same place. `RitualRole` becomes "Ritual role" rather than "Ritual
 * Role": this is a noun phrase in running text, not a heading.
 */
export function className(value?: string | null) {
    if (!value) return "not supplied";
    const spaced = value
        .replaceAll("_", " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
        .trim();
    if (!spaced) return "not supplied";
    return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

export type StatusTone = "supported" | "partial" | "insufficient" | "not-built" | "unknown";

export type StatusCopy = {
    label: string;
    description: string;
    tone: StatusTone;
};

/**
 * Knowledge status vocabulary. "No evidence found" is deliberately never rendered
 * as "does not occur".
 */
export function statusCopy(status?: string | null): StatusCopy {
    switch (normalizeType(status)) {
        case "SUPPORTED":
            return {
                label: "Supported",
                description: "Established within the stated corpus scope.",
                tone: "supported",
            };
        case "PARTIAL":
            return {
                label: "Partial coverage",
                description: "Real evidence exists, and this layer is incomplete.",
                tone: "partial",
            };
        case "INSUFFICIENT_EVIDENCE":
            return {
                label: "Insufficient evidence",
                description:
                    "The current evidence cannot establish this. That is not the same as an absence from the texts.",
                tone: "insufficient",
            };
        case "NOT_BUILT":
            return {
                label: "Not yet modelled",
                description:
                    "This knowledge layer has not been built. Nothing here should be read as a finding about the corpus.",
                tone: "not-built",
            };
        case "NO_LEXICAL_MATCH":
            return {
                label: "No lexical match",
                description:
                    "No registered Sanskrit form matched. This is a fact about the matcher and a lower bound of zero, not an occurrence count.",
                tone: "insufficient",
            };
        case "LEXICAL_MATCH_MINIMUM":
            return {
                label: "Lexical minimum",
                description:
                    "A lower bound from Sanskrit surface matching. A mention is not a claim that the passage is about the thing.",
                tone: "partial",
            };
        case "MEASURED":
            return { label: "Measured", description: "Counted in this graph.", tone: "supported" };
        case "MEASURED_ZERO":
            return {
                label: "Measured zero",
                description: "This relationship was looked for in this pair and none was found.",
                tone: "partial",
            };
        case "NOT_ESTABLISHED_FOR_PAIR":
            return {
                label: "Not established",
                description: "No relationship of this class was established for this pair.",
                tone: "insufficient",
            };
        case "CLASS_NOT_CROSS_VEDA":
            return {
                label: "Within one Veda",
                description: "This relationship class does not cross corpus boundaries.",
                tone: "unknown",
            };
        case "UNRECONCILED":
            return {
                label: "Unreconciled",
                description: "Two counts of this cell disagree and have not been reconciled.",
                tone: "insufficient",
            };
        case "":
            return {
                label: "Status not supplied",
                description: "Read the accompanying scope note before interpreting this result.",
                tone: "unknown",
            };
        default:
            return {
                label: titleCase(humanizePredicate(status)),
                description: "Read the accompanying scope note before interpreting this result.",
                tone: "unknown",
            };
    }
}

/** Internal grade vocabulary, in the words a reader can act on. */
export function evidenceBasisCopy(basis?: string | null): { label: string; detail: string } {
    switch (normalizeType(basis)) {
        case "SOURCE_STATED":
            return {
                label: "Stated in the source",
                detail: "The edition or traditional apparatus states this directly for this passage.",
            };
        case "CONTAINER_INHERITED":
            return {
                label: "Inherited from the hymn",
                detail: "Recorded for the containing hymn and carried down to every verse inside it, not stated verse by verse.",
            };
        case "DETERMINISTIC_DERIVED":
            return {
                label: "Derived by rule",
                detail: "Computed from the text by a deterministic procedure that can be re-run.",
            };
        case "TEXTUAL_MENTION":
            return {
                label: "Named in the text",
                detail: "A registered Sanskrit form occurs in the passage. Naming is not the same as being about.",
            };
        case "MODEL_EXTRACTION":
            return {
                label: "Read by a model",
                detail: "A language model proposed this from the text, so it carries model error.",
            };
        case "MODEL_ADJUDICATED":
            return {
                label: "Model-adjudicated",
                detail: "A language model chose between candidates. Interpretive, and open to revision.",
            };
        default:
            return {
                label: "Basis not recorded",
                detail: "No derivation basis was stored for this relationship.",
            };
    }
}

/** Trust tiers are never the primary user-facing phrase. */
export function trustTierCopy(tier?: string | null) {
    switch (normalizeType(tier)) {
        case "TIER_A":
            return "Textual";
        case "TIER_B":
            return "Derived";
        case "TIER_C":
            return "Reviewed semantic relationship";
        case "TIER_D":
            return "Interpretive";
        default:
            return "Tier not recorded";
    }
}

export function attributionCopy(precision?: string | null) {
    switch (normalizeType(precision)) {
        case "PER_PASSAGE":
            return "Stated for this verse";
        case "CONTAINER_INHERITED":
            return "Inherited from the hymn";
        case "TEXTUAL_MENTION":
            return "Named in the verse";
        case "NOT_AN_ATTRIBUTION":
            return "Not an attribution";
        default:
            return "Attribution basis not recorded";
    }
}

export type CertaintyBand = "certain" | "probable" | "ambiguous" | "unknown";

export function certaintyBand(value?: string | null): CertaintyBand {
    const normalized = normalizeType(value);
    if (normalized.includes("AMBIG")) return "ambiguous";
    if (normalized.includes("CERTAIN")) return "certain";
    if (normalized.includes("PROBABLE")) return "probable";
    return "unknown";
}

export function certaintyCopy(value?: string | null) {
    switch (certaintyBand(value)) {
        case "certain":
            return "Certain";
        case "probable":
            return "Probable";
        case "ambiguous":
            return "Ambiguous";
        default:
            return "Certainty not recorded";
    }
}

/** Default analytics for a deity include CERTAIN + PROBABLE, never AMBIGUOUS. */
export function defaultDeityTotal(certainty: {
    certain_count?: number | null;
    probable_count?: number | null;
}) {
    return (certainty.certain_count ?? 0) + (certainty.probable_count ?? 0);
}

export function conditionLabel(kind?: string | null) {
    switch (normalizeType(kind)) {
        case "AFFLICTION":
            return "Affliction";
        case "THREAT":
            return "Threat";
        case "PATHOGEN_OR_CAUSE":
            return "Named cause or agent";
        default:
            return "Condition";
    }
}

export function conditionNote(kind?: string | null) {
    switch (normalizeType(kind)) {
        case "AFFLICTION":
            return "A condition suffered in the body or the household.";
        case "THREAT":
            return "A hostile agent the texts guard against. Not a disease.";
        case "PATHOGEN_OR_CAUSE":
            return "Named by the texts as a cause. Not a modern pathogen.";
        default:
            return "Kind not recorded.";
    }
}

export function parallelKindCopy(kind?: string | null) {
    switch (normalizeType(kind)) {
        case "TEXTUAL_PARALLEL":
            return {
                label: "Parallel wording",
                detail: "Closely similar wording in both passages.",
            };
        case "TEXT_REUSE":
            return { label: "Text reuse", detail: "One passage carries the wording of the other." };
        case "TEXTUAL_VARIANT":
            return { label: "Variant", detail: "The same verse with edition-level differences." };
        case "ENTITY_VOCABULARY_OVERLAP":
            return {
                label: "Shared vocabulary",
                detail: "Both passages name the same registered entities. This is not shared wording.",
            };
        case "FORMULA_MEDIATED":
            return {
                label: "Shared formula",
                detail: "Both passages belong to the same formula family.",
            };
        default:
            return {
                label: titleCase(humanizePredicate(kind)),
                detail: "Relationship class as stored.",
            };
    }
}

export function matchLevelCopy(level?: string | null) {
    switch (normalizeType(level)) {
        case "IDENTICAL":
            return "Identical surface";
        case "SANDHI_INSENSITIVE":
            return "Matched after sandhi folding";
        case "NORMALIZED":
            return "Matched on a normalised surface";
        case "":
            return "Match level not recorded";
        default:
            return titleCase(humanizePredicate(level));
    }
}

const ENTITY_ROUTE_OVERRIDES: Record<string, (id: string) => string> = {
    DEVATA: (id) => `/devatas/${encodeURIComponent(id)}`,
    MANTRA: (id) => `/passage/${encodeURIComponent(id)}`,
    PASSAGE: (id) => `/passage/${encodeURIComponent(id)}`,
    STRUCTURAL_CONTAINER: (id) => `/passage/${encodeURIComponent(id)}`,
    RITUAL: (id) => `/rituals/${encodeURIComponent(id)}`,
    FORMULA_FAMILY: (id) => `/formula-families/${encodeURIComponent(id)}`,
};

export function entityHref(type: string | null | undefined, id: string) {
    const normalized = normalizeType(type);
    const override = ENTITY_ROUTE_OVERRIDES[normalized];
    if (override) return override(id);
    return `/entities/${normalized.toLowerCase()}/${encodeURIComponent(id)}`;
}

export function entityTypeLabel(type?: string | null) {
    return humanizePredicate(type);
}
