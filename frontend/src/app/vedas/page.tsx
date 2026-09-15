import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { CaveatList } from "@/components/status";
import { load, vedaOrder, workSlugs, type WorksResponse } from "@/lib/api";
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
    SV: "Kauthuma recension, ārcika only",
    YV: "Śukla, Vājasaneyi Mādhyandina",
    AV: "Śaunaka recension",
};

/** The levels each collection actually uses. None of them is forced into another's shape. */
const STRUCTURE: Record<string, string> = {
    RV: "Mandala → Sukta → Mantra",
    SV: "Collection → Parvan → Dasati → Verse",
    YV: "Adhyaya → Mantra",
    AV: "Kanda → Sukta → Mantra",
};

const NOT_HELD: Record<string, string> = {
    RV: "Samhita only, in one recension. No Brahmana, Aranyaka or Upanisad layer is held, and the Ashvalayana recension is not present.",
    SV: "The ārcika verses only. The gana collections are not included: they are a parallel and larger body, and they are the reason the Samaveda is a distinct Veda rather than a Rigvedic excerpt. Nothing here shows or infers melody.",
    YV: "The White Yajurveda only. The Krishna Yajurveda is not held at all, which is the omission most likely to mislead, because the name ordinarily covers both.",
    AV: "The Śaunaka recension only. The Paippalāda is not a minor variant: it is a substantially different collection with its own hymn order.",
};

type AudioStats = { mapped_scope_keys_by_veda: Record<string, number> };

const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

export default async function VedasPage() {
    const [result, audio] = await Promise.all([
        load<WorksResponse>("/works"),
        load<AudioStats>("/audio/stats"),
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
    const recited = audio.ok ? audio.data.mapped_scope_keys_by_veda : {};

    return (
        <div className="va-page">
            <header className="va-page-head">
                <h1>Four Samhitas. Four textual worlds.</h1>
                <p>
                    Each collection keeps its own hierarchy and its own words for it. None is
                    flattened into a common template, and each says which recension is held here
                    before it says how much of it.
                </p>
            </header>

            <div className="va-collections">
                {works.map((work) => {
                    const code = work.veda ?? "RV";
                    const slug = workSlugs[code];
                    const total = work.mantra_count ?? 0;
                    const translated = work.translated_mantra_count ?? 0;
                    const audioCount = recited[code];

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
                                <div className={`va-fact${translated === 0 ? " is-none" : ""}`}>
                                    <dt>Translated</dt>
                                    <dd>
                                        <strong>
                                            {translated === 0 ? "none" : number(translated)}
                                        </strong>
                                    </dd>
                                </div>
                                <div className={`va-fact${audioCount === 0 ? " is-none" : ""}`}>
                                    <dt>Recited</dt>
                                    <dd>
                                        <strong>
                                            {audioCount === 0
                                                ? "none"
                                                : (number(audioCount) ?? "not read")}
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
