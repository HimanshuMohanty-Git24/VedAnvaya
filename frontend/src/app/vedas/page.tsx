import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import {
    encoded,
    load,
    loadCompleteness,
    vedaNames,
    vedaOrder,
    workSlugs,
    type Stats,
    type Work,
    type WorksResponse,
} from "@/lib/api";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site";

export const revalidate = 300;

export const metadata: Metadata = pageMetadata({
    title: "The Four Vedas",
    description:
        "Read the four Samhita corpora: the Rigveda, Samaveda, Yajurveda and Atharvaveda, each with its own hierarchy, recension, translation, recitation and evidence layers.",
    pathname: "/vedas",
});

/**
 * The collection index, as a way in rather than as a ledger of what is absent.
 *
 * Four entries rather than four cards, and the difference is not cosmetic. The collections
 * differ by a factor of six in size, one of them has no translation layer of its own and
 * another has no recitation, and each keeps a different structure. Four equal tiles assert an
 * equivalence the data contradicts.
 *
 * WHAT EACH ROW SAYS, AND WHERE IT COMES FROM. The counts are read from `/works` and
 * `/audio/stats` on this request. The feature list is read from each work's measured
 * `knowledge_layers`, so a layer appears on a card only where the graph actually holds edges
 * into that corpus -- it is never a list typed here and left to drift. The notation figure is
 * the certified completeness record. The one-line scope note is the only typed string on the
 * page and it names a recension, never a count; the full scope statement for every edition,
 * with its exclusions enumerated, is on /limits.
 */

const DEVANAGARI: Record<string, string> = {
    RV: "ऋग्वेद",
    SV: "सामवेद",
    YV: "यजुर्वेद",
    AV: "अथर्ववेद",
};

const RECENSION: Record<string, string> = {
    RV: "Śākala recension",
    SV: "Kauthuma recension, ārcika",
    YV: "Śukla, Vājasaneyi Mādhyandina",
    AV: "Śaunaka recension",
};

/** The levels each collection actually uses. None of them is forced into another's shape. */
const STRUCTURE: Record<string, string> = {
    RV: "Mandala → Sukta → Mantra",
    SV: "Ārcika → Prapāṭhaka → Ardha → Daśati → Verse",
    YV: "Adhyaya → Mantra",
    AV: "Kanda → Sukta → Mantra",
};

/**
 * One sentence on what this edition is, in the reader's terms.
 *
 * A recension and a shape, not a list of exclusions. A reader standing at the index needs to
 * know which text they are about to open; the enumerated boundaries of each edition are set
 * out once, on /limits, and linked from the foot of this page.
 */
const EDITION: Record<string, string> = {
    RV: "The oldest of the four and the source most of the others draw on: ten mandalas of hymns to Agni, Indra, Soma and the rest, with the traditional index naming a seer, a deity and a metre for every verse.",
    /*
     * One clause of absence survives the move to /limits, and only this one.
     *
     * Every other exclusion is enumerated on the scope page. The gāna are different in kind:
     * they are the sung books the ārcika is sung *from*, they are larger than it, and a card
     * that says "arranged for singing" and "the marks that record how it was pitched" without
     * them invites a reader to conclude the singing is here. The absence has to travel with
     * the sentence that raises it, so it does - in a clause, not in a block.
     */
    SV: "The Rigveda arranged for singing: the ārcika verse collection in the Kauthuma recension, most of it Rigvedic wording set in a new order, carrying the svara marks that record how it was pitched. The gāna song-books it was sung from are not included.",
    YV: "The liturgy itself: forty adhyayas of formulas spoken at the rite, many of them prose, arranged by the order of the ceremony rather than by hymn.",
    AV: "The domestic and the urgent — healing, protection, rivalry, marriage, statecraft — in twenty kandas, and the collection that shows most of Vedic life outside the sacrificial ground.",
};

/**
 * The measured layers, in the reader's words.
 *
 * Keyed on the layer name the API reports, so a layer this map does not know is simply not
 * shown rather than printed as a raw identifier. The order of this object is the order the
 * features appear, which puts the text and the ways of hearing and reading it first and the
 * annotation layers after.
 */
const LAYER_LABEL: Record<string, string> = {
    TRANSLATION: "English translation",
    DEVATA_ASCRIPTION: "Deity named by the index",
    DEVATA_ASCRIPTION_DESCRIPTOR: "Deity descriptors from the index",
    RISHI_ATTRIBUTION: "Seer attribution",
    CHANDAS_ATTRIBUTION: "Metre",
    DEVATA_MENTION: "Deities named in the verse",
    ENTITY_MENTION: "Named entities",
    FORMULA_OCCURRENCE: "Shared formulas",
    CONCEPT_ASSERTION: "Concept links",
};

const SCRIPT_LABEL: Record<string, string> = {
    IAST: "Accented romanised Sanskrit",
    DEVANAGARI: "Devanagari",
};

const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

type AudioStats = { mapped_scope_keys_by_veda?: Record<string, number> };

/** One work's measured detail. Only the fields this page reads are declared. */
type WorkDetail = Work & {
    knowledge_layers?: Array<{ layer: string; status: string }>;
    text_scripts?: string[];
};

/**
 * What this collection carries, built from what was measured rather than from a list.
 *
 * Recitation and notation are not knowledge layers -- they are product layers over the text --
 * so they are added from their own measured figures. The translation entry is relabelled where
 * a corpus has none of its own: the Samaveda's TRANSLATION edges are Rigvedic renderings shown
 * against verses verified character-identical, and calling that "English translation" on a card
 * would be the single most misleading word on this page.
 */
function features(
    detail: WorkDetail | null,
    { recited, notation, ownTranslations }: {
        recited: number;
        notation: number | null;
        ownTranslations: number | null;
    },
): string[] {
    const out: string[] = [];

    for (const script of detail?.text_scripts ?? []) {
        const label = SCRIPT_LABEL[script];
        if (label) out.push(label);
    }

    const built = new Set(
        (detail?.knowledge_layers ?? [])
            .filter((row) => row.status === "SUPPORTED")
            .map((row) => row.layer),
    );

    if (built.has("TRANSLATION")) {
        out.push(
            ownTranslations ? LAYER_LABEL.TRANSLATION : "Reused English renderings, labelled as reuse",
        );
    }
    if (recited > 0) out.push("Verse-by-verse recitation");
    if (notation) out.push("Source-explicit svara notation");
    out.push("Cross-Veda parallels");

    for (const [layer, label] of Object.entries(LAYER_LABEL)) {
        if (layer === "TRANSLATION") continue;
        if (built.has(layer)) out.push(label);
    }

    return out;
}

export default async function VedasPage() {
    const [result, audio, stats, completeness] = await Promise.all([
        load<WorksResponse>("/works"),
        load<AudioStats>("/audio/stats"),
        load<Stats>("/stats"),
        loadCompleteness(),
    ]);
    if (!result.ok) {
        return (
            <div className="va-page">
                <LoadFailure message={result.message} status={result.status} />
            </div>
        );
    }
    const works = [...(result.data.items ?? [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );

    /* The feature list is measured per work, so it is fetched per work. */
    const details = await Promise.all(
        works.map((work) => load<WorkDetail>(`/works/${encoded(work.work_id)}`)),
    );

    /*
     * Recitation counts come from the audio service and from nowhere else.
     *
     * The completeness record also carries a per-Veda recitation block, and on this build it
     * disagrees: it reports one Veda's recording count as that Veda's entire mantra total.
     * `/audio/stats` is the layer's own measurement, so it is the only figure printed here,
     * and an unreachable audio service prints nothing rather than a second-hand number.
     */
    const recitedByVeda: Record<string, number> = audio.ok
        ? (audio.data.mapped_scope_keys_by_veda ?? {})
        : {};
    const notationTotal = completeness.samaveda_notation.validated_notation_witnesses;
    const canonicalMantras = stats.ok
        ? (stats.data.corpus?.find((row) => row.name === "mantras")?.total ?? null)
        : null;

    return (
        <div className="va-page">
            <header className="va-page-head">
                <h1>Four Samhitas. Four textual worlds.</h1>
                <p>
                    {canonicalMantras ? `${number(canonicalMantras)} canonical mantras, held` : "Held"}{" "}
                    as four editions rather than as one flattened corpus. Each keeps its own
                    hierarchy and its own words for it, and each says which recension is open in
                    front of you.
                </p>
            </header>

            <div className="va-collections">
                {works.map((work, index) => {
                    const code = work.veda ?? "RV";
                    const slug = workSlugs[code];
                    const name = vedaNames[code] ?? work.traditional_name;
                    const loaded = details[index];
                    const detail = loaded && loaded.ok ? loaded.data : null;
                    const total = work.mantra_count ?? 0;
                    const translated = work.translated_mantra_count ?? 0;
                    const reused = completeness.translations.by_veda[code]?.reused_rendering ?? 0;
                    const recited = recitedByVeda[code] ?? 0;
                    const notation = code === "SV" ? notationTotal : null;

                    return (
                        <article className="va-collection" key={work.work_id}>
                            <Link className="va-collection-name" href={`/vedas/${slug}`}>
                                <span className="va-collection-deva" lang="sa">
                                    {DEVANAGARI[code]}
                                </span>
                                <span className="va-collection-latin">{work.traditional_name}</span>
                                <span className="va-collection-recension">{RECENSION[code]}</span>
                            </Link>

                            <div className="va-collection-body">
                                <p className="va-collection-scope">{EDITION[code]}</p>
                                <p className="va-collection-structure">{STRUCTURE[code]}</p>

                                <ul className="va-collection-features">
                                    {features(detail, {
                                        recited,
                                        notation,
                                        ownTranslations: translated,
                                    }).map((item) => (
                                        <li className="va-collection-feature" key={item}>
                                            {item}
                                        </li>
                                    ))}
                                </ul>

                                <p className="va-collection-cta">
                                    <Action href={`/vedas/${slug}`}>Read the {name}</Action>
                                </p>
                            </div>

                            <dl className="va-facts">
                                <div className="va-fact">
                                    <dt>Verses</dt>
                                    <dd>
                                        <strong>{number(total)}</strong>
                                    </dd>
                                </div>

                                <div className="va-fact">
                                    <dt>{translated ? "Translated" : "Reused renderings"}</dt>
                                    <dd>
                                        <strong>{number(translated ? translated : reused)}</strong>
                                    </dd>
                                </div>

                                {notation ? (
                                    <div className="va-fact">
                                        <dt>Notation witnesses</dt>
                                        <dd>
                                            <strong>{number(notation)}</strong>
                                        </dd>
                                    </div>
                                ) : null}

                                <div className={`va-fact${recited === 0 ? " is-none" : ""}`}>
                                    <dt>Recited</dt>
                                    <dd>
                                        <strong>
                                            {recited === 0 ? "none yet" : number(recited)}
                                        </strong>
                                    </dd>
                                </div>
                            </dl>
                        </article>
                    );
                })}
            </div>

            <p className="va-collections-foot">
                Each edition is one recension of one Samhita. Which recension, what it excludes,
                and how translation, recitation and notation coverage are typed is set out in full
                on <Link href="/limits">the scope page</Link>.
            </p>
        </div>
    );
}
