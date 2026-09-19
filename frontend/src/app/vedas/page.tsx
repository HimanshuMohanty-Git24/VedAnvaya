import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { CaveatList, KnowledgeStatus } from "@/components/status";
import {
    load,
    loadCompleteness,
    vedaOrder,
    workSlugs,
    type WorksResponse,
} from "@/lib/api";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site";

export const metadata: Metadata = pageMetadata({
    title: "The Four Vedas",
    description:
        "Four Samhita corpora, each with its own hierarchy, recension, translation and recitation coverage, and a statement of what is not held.",
    pathname: "/vedas",
});

/**
 * The collection index.
 *
 * Four entries rather than four cards, and the difference is not cosmetic. The collections
 * differ by a factor of six in size, one of them has no translation layer at all and another
 * has no recitation, and three are partial in ways their traditional names do not reveal.
 * Four equal tiles assert an equivalence the data contradicts, and a tile has no room for the
 * sentence that says what is missing, which is the most useful thing on the page.
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

const NOT_HELD: Record<string, string> = {
    RV: "Canonical Śākala Samhita core (10,552 mantras). 100% English translation coverage (10,502 dedicated, 50 range-covered). Public recitation has 10,402 verified catalogue records. Brahmana, Aranyaka, Upanisad layers and Ashvalayana recension are excluded from release scope.",
    SV: "Canonical 1,844 ārcika verses only (Pūrvārcika, Āraṇyaka Saṃhitā, Mahānāmnī, Uttarārcika). The gāna song collections and MUSICALIZED_AS graph edges remain outside release scope. 1,136 verses carry validated source-explicit notation witnesses (PARALLEL_WITNESS / PARALLEL_TEXT svara marks, Gates A/B/C passed); 708 verses remain withheld unaligned. Translation layer holds 0 own dedicated English translations, 173 verified reused Rigvedic English renderings (with source identity verified), and 1,671 uncovered. Public recitation has 0 released records; 1,001 queued recordings remain withheld behind the manual audible-review gate (GAP-AUDIO-002, 003, 004).",
    YV: "The White Yajurveda only (Vājasaneyi Mādhyandina, 1,975 mantras). 1,972 translated (1,894 dedicated, 57 range, 21 reused; 3 uncovered ritual markers). Recited: 1,752 records. The Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala) is absent entirely.",
    AV: "The Śaunaka recension only (5,839 mantras). 5,770 English coverage (5,749 dedicated, 21 range; 24 Whitney Sanskrit notes for prose formulas, 45 uncovered). Recited: 4,680 records. The Paippalāda recension is absent.",
};

const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

export default async function VedasPage() {
    const [result, completeness] = await Promise.all([
        load<WorksResponse>("/works"),
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

    const trans = completeness.translations;
    const audio = completeness.audio;
    const notation = completeness.samaveda_notation;

    return (
        <div className="va-page">
            <header className="va-page-head">
                <h1>Four Samhitas. Four textual worlds.</h1>
                <p>
                    Each collection keeps its own hierarchy and its own words for it. None is
                    flattened into a common template, and each says which recension is held here
                    before it says how much of it.
                </p>
                <div style={{ marginTop: "var(--va-space-md)" }}>
                    <KnowledgeStatus
                        status="SUPPORTED"
                        note={`Certified Core Invariant: ${completeness.total_canonical_mantras.toLocaleString("en-GB")} mantras (Release commit: ${completeness.certified_release_commit.slice(0, 7)}). Translations strictly typed; recitation bounded by audible review gates.`}
                    />
                </div>
            </header>

            <div className="va-collections">
                {works.map((work) => {
                    const code = work.veda ?? "RV";
                    const slug = workSlugs[code];
                    const transItem = trans.by_veda[code];
                    const total = work.mantra_count ?? transItem?.total ?? 0;
                    const audioCount = audio.released_by_veda[code] ?? 0;

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
                                <p className="va-collection-structure">{STRUCTURE[code]}</p>
                                <p className="va-collection-limit">{NOT_HELD[code]}</p>
                                <Action href={`/vedas/${slug}`}>
                                    Read the {work.traditional_name}
                                </Action>
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
                            </dl>
                        </article>
                    );
                })}
            </div>

            <CaveatList caveats={result.data.caveats} title="Scope of this list" />
        </div>
    );
}
