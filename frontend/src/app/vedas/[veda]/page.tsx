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
    SV: "Kauthuma recension (ārcika only)",
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
    RV: "Canonical Śākala Samhita core (10,552 mantras). 100% English translation coverage (10,502 dedicated, 50 range-covered). Public recitation has 10,402 verified catalogue records. Brahmana, Aranyaka, Upanisad layers and Ashvalayana recension are excluded from release scope.",
    SV: "Canonical 1,844 ārcika verses only (Pūrvārcika, Āraṇyaka Saṃhitā, Mahānāmnī, Uttarārcika). The gāna song collections and MUSICALIZED_AS graph edges remain outside release scope. 1,136 verses carry validated source-explicit notation witnesses (PARALLEL_WITNESS / PARALLEL_TEXT svara marks, Gates A/B/C passed); 708 verses remain withheld unaligned. Translation layer holds 0 own dedicated English translations, 173 verified reused Rigvedic English renderings (with source identity verified), and 1,671 uncovered. Public recitation has 0 released records; 1,001 queued recordings remain withheld behind the manual audible-review gate (GAP-AUDIO-002, 003, 004).",
    YV: "The White Yajurveda only (Vājasaneyi Mādhyandina, 1,975 mantras). 1,972 translated (1,894 dedicated, 57 range, 21 reused; 3 uncovered ritual markers). Recited: 1,752 records. The Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala) is absent entirely.",
    AV: "The Śaunaka recension only (5,839 mantras). 5,770 English coverage (5,749 dedicated, 21 range; 24 Whitney Sanskrit notes for prose formulas, 45 uncovered). Recited: 4,680 records. The Paippalāda recension is absent.",
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

    const [worksResult, rootResult, completeness] = await Promise.all([
        load<WorksResponse>("/works"),
        load<WorkRoot>(`/works/${encoded(workId)}/root?limit=120`),
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
    const code = work.veda ?? "RV";
    const rootLevel = root.root_level;
    const rootLabel = rootLevel?.native_label ?? "division";

    const audioResult = await load<WorkAudio>(`/works/${encoded(workId)}/audio?limit=1`);
    const transItem = completeness.translations.by_veda[code];
    const total = work.mantra_count ?? transItem?.total ?? 0;
    const audioCount = completeness.audio.released_by_veda[code] ?? 0;
    const notation = completeness.samaveda_notation;

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
                    <div className="va-fact">
                        <dt>Translated</dt>
                        <dd>
                            {code === "SV" ? (
                                <strong title="0 own dedicated English; 173 verified reused Rigvedic English renderings">
                                    173 <span style={{ fontSize: "var(--va-text-xs)", color: "var(--va-text-secondary)", fontWeight: "normal" }}>reused</span>
                                </strong>
                            ) : code === "RV" ? (
                                <strong title="10,502 dedicated English + 50 range-covered">
                                    {number(10552)}
                                </strong>
                            ) : code === "YV" ? (
                                <strong title="1,894 dedicated + 57 range + 21 reused">
                                    {number(1972)}
                                </strong>
                            ) : (
                                <strong title="5,749 dedicated + 21 range (24 non-English Sanskrit notes)">
                                    {number(5770)}
                                </strong>
                            )}
                        </dd>
                    </div>
                    {code === "SV" ? (
                        <div className="va-fact">
                            <dt>Notation</dt>
                            <dd>
                                <strong title="1,136 validated source-explicit notation witnesses (Gates A/B/C passed); 708 withheld">
                                    {number(notation.validated_notation_witnesses)}
                                </strong>
                            </dd>
                        </div>
                    ) : null}
                    <div className={`va-fact${audioCount === 0 ? " is-none" : ""}`}>
                        <dt>Recited</dt>
                        <dd>
                            <strong>
                                {audioCount === 0
                                    ? "0 (1,001 withheld)"
                                    : number(audioCount)}
                            </strong>
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
