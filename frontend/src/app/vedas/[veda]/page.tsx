import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArchiveIndex } from "@/components/corpus/archive-index";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { CaveatList, KnowledgeStatus } from "@/components/status";
import { VedaAudioPanel } from "@/components/veda-audio-panel";
import {
    encoded,
    firstFailure,
    load,
    vedaNames,
    workIds,
    type WorkAudio,
    type WorkRoot,
    type WorksResponse,
} from "@/lib/api";
import { pageMetadata } from "@/lib/site";

/**
 * One Samhita, as a collection rather than as a folder.
 *
 * The page answers four questions in the order a reader asks them: which recension is this,
 * how much of it is here, what is deliberately not here, and how do I get into it. The limit
 * statement comes before the index on purpose. A reader who descends into the Yajurveda
 * without having been told that the Krishna recension is absent will read every absence they
 * find as a fact about the Yajurveda, and it is not: it is a fact about this build.
 */

const DEVANAGARI: Record<string, string> = {
    RV: "ऋग्वेद",
    SV: "सामवेद",
    YV: "यजुर्वेद",
    AV: "अथर्ववेद",
};

const RECENSION: Record<string, string> = {
    RV: "Śākala recension",
    SV: "Kauthuma recension, ārcika only",
    YV: "Śukla, Vājasaneyi Mādhyandina",
    AV: "Śaunaka recension",
};

/** The levels each collection actually uses. None of them is forced into another's shape. */
const STRUCTURE: Record<string, string> = {
    RV: "Mandala → Sukta → Mantra",
    SV: "Collection → Prapathaka → Ardha → Dasati → Verse",
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
    SV: "Four named ārcikas rather than numbered books, subdivided down to single verses. The divisions are the verse collection's own; they are not the gāna song-books, which are not held here.",
    YV: "Forty adhyayas holding mantras directly. There is no hymn level between them, because the Yajurveda is arranged by rite rather than by hymn, and many of its units are prose.",
    AV: "Twenty kandas of hymns. The arrangement of the earlier books is largely by hymn length rather than by subject, so a kanda is not a theme.",
};

const NOT_HELD: Record<string, string> = {
    RV: "Samhita only, in one recension. No Brahmana, Aranyaka or Upanisad layer is held, and the Ashvalayana recension is not present.",
    SV: "The ārcika verses only. Gana collections are not included: they are a parallel and larger body, and they are the reason the Samaveda is a distinct Veda rather than a Rigvedic excerpt. Nothing here shows, notates or infers melody.",
    YV: "The White Yajurveda only. The Krishna Yajurveda is not held at all, which is the omission most likely to mislead, because the name ordinarily covers both. No Taittiriya, Kathaka, Maitrayani or Kapisthala samhita is present.",
    AV: "The Śaunaka recension only. The Paippalāda is not a minor variant: it is a substantially different collection with its own hymn order. An Atharvavedic absence measured here is an absence from Śaunaka.",
};

type Params = { params: Promise<{ veda: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { veda } = await params;
    const code = veda.slice(0, 2).toUpperCase();
    const name = vedaNames[code] ?? veda;
    const title = name.charAt(0).toUpperCase() + name.slice(1);
    const description = NOT_HELD[code]
        ? `${RECENSION[code]}. ${NOT_HELD[code]}`
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

    const [worksResult, rootResult] = await Promise.all([
        load<WorksResponse>("/works"),
        load<WorkRoot>(`/works/${encoded(workId)}/root?limit=120`),
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

    const work = worksResult.data.items?.find((item) => item.work_id === workId);
    if (!work) notFound();
    const root = rootResult.data;
    const code = work.veda ?? "RV";
    const rootLevel = root.root_level;
    const rootLabel = rootLevel?.native_label ?? "division";

    const audioResult = await load<WorkAudio>(`/works/${encoded(workId)}/audio?limit=1`);
    const total = work.mantra_count ?? 0;
    const translated = work.translated_mantra_count ?? 0;

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
                    <div className={`va-fact${translated === 0 ? " is-none" : ""}`}>
                        <dt>Translated</dt>
                        <dd>
                            <strong>{translated === 0 ? "none" : number(translated)}</strong>
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
             * The limit statement is a section of the page, not a footnote on it. It is the
             * thing a reader most needs before they start counting what they find.
             */}
            <section className="va-work-limit">
                <h2>What this collection does not hold</h2>
                <p>{NOT_HELD[code]}</p>
                <div className="va-work-status">
                    <KnowledgeStatus status={work.data_status} />
                </div>
            </section>

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
                        Search inside this collection
                    </Action>
                    <Action href={`/graph?node=${encoded(workId)}`}>
                        Open this work in the graph
                    </Action>
                    <Action href="/devatas">Deities named across the four collections</Action>
                </div>
            </div>

            <CaveatList caveats={work.caveats} title="Scope notes for this work" />
        </div>
    );
}
