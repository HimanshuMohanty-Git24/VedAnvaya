/**
 * Reader-facing names for the identifiers the API prints beside a text surface.
 *
 * The reader payload carries `source_id` ("WIKISOURCE_SA"), `witness_id`
 * ("WIKISOURCE_SA.SV.KAU.ARCIKA_MULA") and `rights_status` ("CC_BY_SA"), and the page was
 * printing the middle one raw next to the verse. An internal identifier beside the text is
 * not provenance: it tells a reader that the build knows something without telling them
 * what.
 *
 * Every name below is transcribed from the graph's own `:Source` nodes, or is a direct
 * expansion of the identifier's own segments -- nothing here adds a bibliographic claim the
 * store does not already hold. It is a table in the client only because the reader endpoint
 * does not yet return `source_name` / `source_url`, which those `:Source` nodes do hold;
 * once it does, this table should be deleted rather than maintained.
 *
 * Every lookup falls back to the raw identifier. An unmapped witness loses its prose, never
 * its provenance.
 */

/** `:Source.name`, as the graph records it. */
const SOURCE_NAMES: Record<string, string> = {
    GRETIL: "GRETIL, Göttingen",
    VEDAWEB: "VedaWeb, Cologne",
    WIKISOURCE_SA: "Sanskrit Wikisource",
    WIKISOURCE_GRIFFITH_RV: "Wikisource, Griffith second edition",
    WIKISOURCE_GRIFFITH_SV: "Wikisource, Griffith Samaveda",
    WIKISOURCE_WHITNEY_AV: "Wikisource, Whitney and Lanman",
};

/** What each edition this build ingested actually is, in the words its own id uses. */
const WITNESS_NAMES: Record<string, string> = {
    "GRETIL.RV.AUFRECHT": "Aufrecht edition",
    "VEDAWEB.AUFRECHT": "Aufrecht edition, VedaWeb TEI",
    "GRETIL.AVS.SAUNAKA.ACCENTED": "Śaunaka recension, accented",
    "GRETIL.AVS.SAUNAKA.UNACCENTED": "Śaunaka recension, unaccented",
    "WIKISOURCE_SA.YV.VSM.ACCENTED": "Vājasaneyi Saṃhitā, accented",
    "WIKISOURCE_SA.YV.VSM.UNACCENTED": "Vājasaneyi Saṃhitā, unaccented",
    "WIKISOURCE_SA.SV.KAU.ARCIKA_MULA": "Kauthuma ārcika, mūla text",
    "WIKISOURCE_SA.SV.KAU.ARCIKA_SASVARA": "Kauthuma ārcika, sasvara text",
};

/**
 * The licence, spelled the way the licence spells itself.
 *
 * REFERENCE_ONLY is the one that must not be softened: it is the Atharvavedic corpus's
 * working-private status, and a reader who copies that text needs to have been told.
 */
const RIGHTS_NAMES: Record<string, string> = {
    CC_BY_SA: "CC BY-SA",
    CC_BY_NC_SA: "CC BY-NC-SA",
    CC0: "CC0",
    PUBLIC_DOMAIN: "Public domain",
    REFERENCE_ONLY: "Held for reference, not redistribution",
};

export function witnessName(witnessId?: string | null): string | null {
    if (!witnessId) return null;
    return WITNESS_NAMES[witnessId] ?? witnessId;
}

export function sourceName(sourceId?: string | null): string | null {
    if (!sourceId) return null;
    return SOURCE_NAMES[sourceId] ?? sourceId;
}

export function rightsName(rights?: string | null): string | null {
    if (!rights) return null;
    return RIGHTS_NAMES[rights] ?? rights.replaceAll("_", " ").toLowerCase();
}

/** "Sanskrit Wikisource · CC BY-SA", with whichever halves the surface actually carries. */
export function provenanceLine(surface?: {
    source_id?: string | null;
    rights_status?: string | null;
} | null): string | null {
    if (!surface) return null;
    const parts = [sourceName(surface.source_id), rightsName(surface.rights_status)].filter(
        Boolean,
    );
    return parts.length ? parts.join(" · ") : null;
}

/**
 * The four Samavedic collections are names, not ordinals, and the graph stores the name in
 * upper case because it is a key. `SV CHANDA 1.1.1` is a citation and stays as it is; the
 * breadcrumb is prose and should read as prose.
 *
 * Only the diacritics are added. Identifying which of the four blocks is "the Pūrvārcika"
 * is a bracketing question this build's own structural model deliberately leaves open, so
 * the labels say no more than the keys do.
 */
const SV_COLLECTIONS: Record<string, string> = {
    CHANDA: "Chanda",
    ARANYA: "Āraṇya",
    MAHANAMNYA: "Mahānāmnī",
    UTTARA: "Uttarārcika",
};

/** Samavedic level names, in the spelling the frozen structural model uses. */
const SV_LEVELS: Record<string, string> = {
    collection: "Collection",
    prapathaka: "Prapāṭhaka",
    ardha: "Ardha",
    dasati: "Daśati",
    verse: "Verse",
};

export function crumbLevelName(
    veda: string,
    levelKey?: string | null,
    fallback?: string | null,
): string {
    if (veda !== "SV") return fallback ?? levelKey ?? "";
    return SV_LEVELS[levelKey ?? ""] ?? fallback ?? levelKey ?? "";
}

export function crumbValue(veda: string, levelKey?: string | null, value?: string | null): string {
    if (veda !== "SV" || levelKey !== "collection") return value ?? "";
    return SV_COLLECTIONS[value ?? ""] ?? value ?? "";
}

/** "Rigvedic", for a sentence that needs the adjective rather than the corpus's name. */
const VEDA_ADJECTIVES: Record<string, string> = {
    RV: "Rigvedic",
    SV: "Samavedic",
    YV: "Yajurvedic",
    AV: "Atharvavedic",
};

export function vedaAdjective(veda?: string | null): string {
    return VEDA_ADJECTIVES[veda ?? ""] ?? "cross-corpus";
}
