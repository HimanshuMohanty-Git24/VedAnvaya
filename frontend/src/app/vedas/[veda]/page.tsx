import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArchiveIndex } from "@/components/corpus/archive-index";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { VedaAudioPanel } from "@/components/veda-audio-panel";
import {
    encoded,
    firstFailure,
    load,
    loadCompleteness,
    vedaNames,
    workIds,
    type Work,
    type WorkAudio,
    type WorkRoot,
    type WorksResponse,
} from "@/lib/api";
import { pageMetadata } from "@/lib/site";

/**
 * One Samhita, as a collection rather than as a folder.
 *
 * The page leads with what is readable. A reader who has arrived here wants the text, so the
 * order is: which edition this is, how it is divided, what it carries, and then the index into
 * it. The measured counts come from `/works` and `/audio/stats`; the list of what the
 * collection carries is read from the work's own `knowledge_layers`, so it can never claim a
 * layer the graph does not hold for this corpus.
 *
 * The edition's boundaries -- the recension held, the recensions absent, how translation,
 * recitation and notation coverage are typed -- are stated once, on /limits, and linked from
 * the foot of the page and from the scope line under the title. They used to be a paragraph
 * here, above the index, which made the first thing a reader met on the way to the text a
 * statement of what they would not find in it.
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
 * What the divisions are, in one sentence each.
 *
 * These are glosses on the shape, not on the contents. The Yajurveda entry earns its place:
 * an adhyaya holds mantras directly, with no hymn between, and a reader who has just come
 * from the Rigveda will otherwise look for the level that is not there.
 */
const SHAPE_NOTE: Record<string, string> = {
    RV: "Ten mandalas, each a book of hymns, each hymn a run of mantras. The family books, two to seven, are the older core; the first and tenth are later collections.",
    SV: "Four named ārcikas rather than numbered books, subdivided down to single verses. The divisions are the verse collection's own.",
    YV: "Forty adhyayas holding mantras directly. There is no hymn level between them, because the Yajurveda is arranged by rite rather than by hymn, and many of its units are prose.",
    AV: "Twenty kandas of hymns. The arrangement of the earlier books is largely by hymn length rather than by subject, so a kanda is not a theme.",
};

/** One sentence on what this edition is. A recension and a character, never a count. */
const EDITION: Record<string, string> = {
    RV: "The oldest of the four and the source most of the others draw on, with the traditional index naming a seer, a deity and a metre for every verse.",
    SV: "The Rigveda arranged for singing: the ārcika verse collection in the Kauthuma recension, carrying the svara marks that record how it was pitched.",
    YV: "The liturgy itself — formulas spoken at the rite, many of them prose, arranged by the order of the ceremony rather than by hymn.",
    AV: "The domestic and the urgent: healing, protection, rivalry, marriage and statecraft, and the collection that shows most of Vedic life outside the sacrificial ground.",
};

/** The measured layers, in the reader's words. A layer this map does not know is not shown. */
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

type Params = { params: Promise<{ veda: string }> };

type AudioStats = { mapped_scope_keys_by_veda?: Record<string, number> };

/** One work's measured detail. Only the fields this page reads are declared. */
type WorkDetail = Work & {
    knowledge_layers?: Array<{ layer: string; status: string }>;
    text_scripts?: string[];
};

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { veda } = await params;
    const code = veda.slice(0, 2).toUpperCase();
    const name = vedaNames[code] ?? veda;
    const title = name.charAt(0).toUpperCase() + name.slice(1);
    const description = EDITION[code]
        ? `${RECENSION[code]}. ${EDITION[code]}`
        : `The ${title} as held in this corpus.`;
    return pageMetadata({ title, description, pathname: `/vedas/${veda}` });
}

export async function generateStaticParams() {
    return Object.keys(workIds).map((veda) => ({ veda }));
}

const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

export default async function VedaPage({ params }: Params) {
    const { veda } = await params;
    const workId = workIds[veda];
    if (!workId) notFound();

    const [worksResult, rootResult, detailResult, audioStats, completeness] = await Promise.all([
        load<WorksResponse>("/works"),
        load<WorkRoot>(`/works/${encoded(workId)}/root?limit=120`),
        load<WorkDetail>(`/works/${encoded(workId)}`),
        load<AudioStats>("/audio/stats"),
        loadCompleteness(),
    ]);
    const failure = firstFailure(worksResult, rootResult);
    if (failure || !worksResult.ok || !rootResult.ok) {
        return (
            <div className="va-page">
                <LoadFailure
                    message={failure?.message ?? "This collection could not be loaded."}
                    status={failure?.status ?? 503}
                />
            </div>
        );
    }

    const work = worksResult.data.items?.find((item: Work) => item.work_id === workId);
    if (!work) notFound();
    const root = rootResult.data;
    const detail = detailResult.ok ? detailResult.data : null;
    const code = work.veda ?? "RV";
    const name = vedaNames[code] ?? veda;
    const rootLevel = root.root_level;
    const rootLabel = rootLevel?.native_label ?? "division";

    const audioResult = await load<WorkAudio>(`/works/${encoded(workId)}/audio?limit=1`);
    const total = work.mantra_count ?? 0;
    const translated = work.translated_mantra_count ?? 0;
    const reused = completeness.translations.by_veda[code]?.reused_rendering ?? 0;
    /*
     * The recitation count comes from the audio service and from nowhere else. The
     * completeness record carries a second per-Veda recitation block which disagrees with it
     * on this build, reporting one corpus's recording count as that corpus's mantra total.
     */
    const recited = audioStats.ok
        ? (audioStats.data.mapped_scope_keys_by_veda?.[code] ?? 0)
        : 0;
    const notation =
        code === "SV" ? completeness.samaveda_notation.validated_notation_witnesses : null;

    const built = new Set(
        (detail?.knowledge_layers ?? [])
            .filter((row) => row.status === "SUPPORTED")
            .map((row) => row.layer),
    );

    /*
     * What this collection carries, built from what was measured.
     *
     * The translation entry is relabelled where a corpus has none of its own: the Samaveda's
     * TRANSLATION edges are Rigvedic renderings shown against verses verified
     * character-identical, and calling that "English translation" here would be the single
     * most misleading phrase on the page.
     */
    const carries: string[] = [];
    for (const script of detail?.text_scripts ?? []) {
        const label = SCRIPT_LABEL[script];
        if (label) carries.push(label);
    }
    if (built.has("TRANSLATION")) {
        carries.push(
            translated ? LAYER_LABEL.TRANSLATION : "Reused English renderings, labelled as reuse",
        );
    }
    if (recited > 0) carries.push("Verse-by-verse recitation");
    if (notation) carries.push("Source-explicit svara notation");
    carries.push("Cross-Veda parallels");
    for (const [layer, label] of Object.entries(LAYER_LABEL)) {
        if (layer === "TRANSLATION") continue;
        if (built.has(layer)) carries.push(label);
    }

    return (
        <div className="va-page">
            <header className="va-work-head">
                <Link className="va-work-back" href="/vedas">
                    All four Samhitas
                </Link>
                <p className="va-work-deva" lang="sa">
                    {DEVANAGARI[code]}
                </p>
                <h1>{work.traditional_name ?? root.traditional_name ?? veda}</h1>
                <p className="va-work-recension">{RECENSION[code]}</p>
                <p className="va-work-edition">{EDITION[code]}</p>
            </header>

            <div className="va-work-band">
                <div className="va-work-shape">
                    <h2>How this collection is divided</h2>
                    <p className="va-collection-structure">{STRUCTURE[code]}</p>
                    <p className="va-work-gloss">{SHAPE_NOTE[code]}</p>
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
                            <strong>{recited === 0 ? "none yet" : number(recited)}</strong>
                        </dd>
                    </div>
                    <div className="va-fact">
                        <dt>{rootLabel}s</dt>
                        <dd>
                            <strong>{number(rootLevel?.passage_count)}</strong>
                        </dd>
                    </div>
                </dl>
            </div>

            {/*
             * What the collection carries, before the index into it. This is the section the
             * reader uses to decide where to go, and every entry in it was measured on this
             * request rather than asserted here.
             */}
            {carries.length ? (
                <section className="va-work-carries">
                    <h2>What this collection carries</h2>
                    <ul className="va-collection-features">
                        {carries.map((item) => (
                            <li className="va-collection-feature" key={item}>
                                {item}
                            </li>
                        ))}
                    </ul>
                    <p className="va-work-scope">
                        This is one recension of one Samhita.{" "}
                        <Link href="/limits">What this edition covers and excludes</Link>, and how
                        each kind of coverage is typed, is set out on the scope page.
                    </p>
                    {/*
                      * Two sentences that stay on the Samaveda's own page rather than moving
                      * to /limits with the rest of the scope.
                      *
                      * Both guard against an inference this particular page invites and no
                      * other one does. It lists source-explicit svara notation among what the
                      * collection carries, and svara marks are the closest thing in this
                      * product to music: a reader who meets them here, with the gāna
                      * unmentioned, can reasonably conclude that the sung Samaveda is what
                      * they are looking at. It is not. The marks are reproduced from a
                      * printed witness and nothing in this build turns them into pitch.
                      *
                      * A link to a scope page does not close that, because the reader has no
                      * reason to suspect there is anything to go and check.
                      */}
                    {code === "SV" && (
                        <p className="va-work-scope">
                            The gāna song-books, in which these verses are actually sung, are
                            not included: what is held is the ārcika verse collection. Where a
                            verse carries svara marks they are reproduced from the printed
                            witness, and nothing here shows, notates or infers melody.
                        </p>
                    )}
                </section>
            ) : null}

            <ArchiveIndex
                rootLabel={rootLabel}
                rootLevelKey={rootLevel?.key}
                rootRows={root.results?.items ?? []}
                rootTotal={rootLevel?.passage_count}
                workLabel={work.traditional_name ?? veda}
            />

            <div className="va-work-foot">
                {audioResult.ok ? (
                    <VedaAudioPanel audio={audioResult.data} verseTotal={work.mantra_count} />
                ) : null}

                <div className="va-work-ways">
                    <h2>Other ways in</h2>
                    <Action href={`/search?q=${encodeURIComponent(code)}`}>
                        Search inside the {name}
                    </Action>
                    <Action href={`/graph?node=${encoded(workId)}`}>
                        Open this work in the graph
                    </Action>
                    <Action href="/devatas">Deities named across the four collections</Action>
                </div>
            </div>
        </div>
    );
}
