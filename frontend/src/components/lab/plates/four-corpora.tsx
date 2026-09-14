import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { CorpusStrip, SmallMultiple, type CorpusFigure } from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import { load, type AudioStats, type CrossVeda, type WorksResponse } from "@/lib/api";
import { CORPORA, PLATES_BY_SLUG, type CorpusCode } from "@/lib/lab";
import { readProvenance } from "@/lib/provenance";

/**
 * Four corpora, side by side.
 *
 * The instruction for this plate was "do not flatten incomparable metrics into one score", and
 * the form follows from taking that literally. Six properties, each on its own scale, each
 * drawn across the same four collections in the same order. Nothing is summed down a column,
 * because nothing down a column is in the same unit, and the layout makes reading along a row
 * the only comfortable way to read it.
 *
 * The two zeroes here are the reason the plate exists. The Samaveda has no released
 * translation and no catalogued recitation. Both are measured facts about what this build
 * holds rather than facts about the Samaveda, and each carries the sentence that says so
 * directly beneath the bars rather than in a caveat at the foot of the page.
 */

const plate = PLATES_BY_SLUG["four-corpora"];

const SCALES = {
    count: { label: "Counts", note: "Raw figures, as this build holds them." },
    share: {
        label: "Per 1,000 verses",
        note: "Each figure against a stated denominator, which is how collections differing in size by nearly six to one become comparable.",
    },
} as const;

export type Scale = keyof typeof SCALES;

export function isScale(value: string | undefined): value is Scale {
    return value === "count" || value === "share";
}

/** Sums the three corpus pairs each collection belongs to. */
function pairTotals(matrix: CrossVeda | null) {
    const totals: Record<string, number> = {};
    for (const pair of matrix?.pairs ?? []) {
        for (const veda of pair.vedas ?? []) {
            totals[veda] = (totals[veda] ?? 0) + (pair.measured_edges_total ?? 0);
        }
    }
    return totals;
}

export async function FourCorporaPlate({ scale = "count" }: { scale?: Scale }) {
    const [worksResult, audioResult, matrixResult, provenance] = await Promise.all([
        load<WorksResponse>("/works"),
        load<AudioStats>("/audio/stats"),
        load<CrossVeda>("/insights/cross-veda"),
        readProvenance(),
    ]);
    if (!worksResult.ok) {
        return <LoadFailure message={worksResult.message} status={worksResult.status} />;
    }

    const works = worksResult.data.items ?? [];
    const byCode = new Map(works.map((work) => [work.veda ?? "", work]));
    const recited = audioResult.ok ? (audioResult.data.mapped_scope_keys_by_veda ?? {}) : null;
    const edges = pairTotals(matrixResult.ok ? matrixResult.data : null);
    const share = scale === "share";

    const verses = (code: CorpusCode) => byCode.get(code)?.mantra_count ?? null;
    const corpusVerses = CORPORA.reduce((total, { code }) => total + (verses(code) ?? 0), 0);

    /**
     * One row's four figures.
     *
     * `against` names the denominator the per-1,000 view divides by, and it differs by row on
     * purpose. Dividing "verses held" by the collection's own verses would return 1,000 four
     * times, which is a chart of the arithmetic rather than of the corpus.
     */
    const strip = (
        pick: (code: CorpusCode) => number | null,
        against: "self" | "corpus",
        absence?: (code: CorpusCode) => string | undefined,
    ) =>
        Object.fromEntries(
            CORPORA.map(({ code }) => {
                const raw = pick(code);
                const denominator = against === "self" ? verses(code) : corpusVerses;
                const figure: CorpusFigure = {
                    value:
                        raw == null
                            ? null
                            : share
                              ? denominator
                                  ? (raw / denominator) * 1000
                                  : null
                              : raw,
                    absence: absence?.(code),
                };
                return [code, figure];
            }),
        ) as Record<CorpusCode, CorpusFigure>;

    const per = (what: string) => (share ? `per 1,000 ${what}` : undefined);

    /*
     * The takeaway's figures are computed rather than written out.
     *
     * Every number in the prose below is derived here from the same response the bars are
     * drawn from, so a sentence cannot survive the data moving underneath it. A hand-typed
     * "99.5%" in a paragraph is the one kind of figure on this site that nothing checks.
     */
    const largest = [...CORPORA].sort((a, b) => (verses(b.code) ?? 0) - (verses(a.code) ?? 0))[0];
    const smallest = [...CORPORA].sort((a, b) => (verses(a.code) ?? 0) - (verses(b.code) ?? 0))[0];
    const sizeRatio =
        verses(largest.code) && verses(smallest.code)
            ? (verses(largest.code) as number) / (verses(smallest.code) as number)
            : null;
    const translatedShare = (code: CorpusCode) => {
        const held = verses(code);
        const translated = byCode.get(code)?.translated_mantra_count;
        return held && typeof translated === "number" ? (translated / held) * 100 : null;
    };
    const largestShare = translatedShare(largest.code);
    const untranslated = CORPORA.filter(
        ({ code }) => (byCode.get(code)?.translated_mantra_count ?? 0) === 0,
    );
    const unrecited = recited ? CORPORA.filter(({ code }) => (recited[code] ?? 0) === 0) : [];
    const largestSharePercent =
        verses(largest.code) && corpusVerses
            ? ((verses(largest.code) as number) / corpusVerses) * 100
            : null;
    const smallestSharePercent =
        verses(smallest.code) && corpusVerses
            ? ((verses(smallest.code) as number) / corpusVerses) * 100
            : null;

    return (
        <>
            <PlateHeader
                lede="Calling these four things 'the Vedas' suggests four volumes of one work. They are not. They differ in size by nearly six to one, they are organised by different divisions, three of the four are held here in one recension with a named parallel body missing, and two of the measurements below are simply absent for one of them. Each row is one property, on one scale, across all four."
                plate={plate}
            />

            <nav aria-label="Scale" className="va-controls">
                <span className="va-controls-label">Scale</span>
                {(Object.keys(SCALES) as Scale[]).map((option) => (
                    <Link
                        aria-current={option === scale}
                        className="va-control"
                        href={
                            option === "count" ? "/visualizations/four-corpora" : `?scale=${option}`
                        }
                        key={option}
                        scroll={false}
                    >
                        {SCALES[option].label}
                    </Link>
                ))}
                <span className="va-controls-label">{SCALES[scale].note}</span>
            </nav>

            <PlateFigure
                description="Six properties of the four collections, each on its own scale. Compare along a row. The rows are in different units and are never added together."
                footnote={
                    <>
                        Bars within a row share a scale; bars in different rows do not. The
                        collections appear in traditional order throughout, including where one has
                        nothing to show, because a figure that dropped its empty collections would
                        make the reader recount the four every time.
                    </>
                }
                id="portrait"
                title="Six properties, one row each"
            >
                <div className="va-multiples">
                    <SmallMultiple
                        definition={
                            share
                                ? "Verses this build addresses, per 1,000 verses of the whole corpus."
                                : "Verses this build addresses with a canonical key and citation."
                        }
                        footnote={
                            largestSharePercent && smallestSharePercent
                                ? `The ${largest.name} is ${largestSharePercent.toFixed(0)}% of the corpus by verse; the ${smallest.name} is ${smallestSharePercent.toFixed(0)}%.`
                                : "Verse counts as this build addresses them."
                        }
                        title="Verses held"
                    >
                        <CorpusStrip
                            caption="Verses held, by collection"
                            figures={strip((code) => verses(code), "corpus")}
                            perThousand={share}
                            unit={per("in the corpus")}
                        />
                    </SmallMultiple>

                    <SmallMultiple
                        definition={
                            share
                                ? "Verses with an English translation, per 1,000 verses of their own collection."
                                : "Verses carrying an English translation in this build."
                        }
                        footnote={
                            <>
                                The Samavedic zero is a fact about what has been released here, not
                                about the text. It also means every translation-derived figure
                                anywhere in this product excludes the Samaveda entirely.
                            </>
                        }
                        title="With a translation"
                    >
                        <CorpusStrip
                            caption="Verses with an English translation, by collection"
                            figures={strip(
                                (code) => byCode.get(code)?.translated_mantra_count ?? null,
                                "self",
                            )}
                            perThousand={share}
                            unit={per("of its own")}
                        />
                    </SmallMultiple>

                    <SmallMultiple
                        definition={
                            share
                                ? "Verses with a recitation, per 1,000 verses of their own collection."
                                : "Verses with a recitation catalogued and playable."
                        }
                        footnote={
                            recited
                                ? "No Samavedic recitation is catalogued. The Samaveda is the Veda defined by its sung realisation, which makes this the most conspicuous gap in the layer — and it is a gap in what has been published, not in the tradition."
                                : "The recitation catalogue could not be read for this row."
                        }
                        title="With a recitation"
                    >
                        <CorpusStrip
                            caption="Verses with a recitation, by collection"
                            figures={strip(
                                (code) => (recited ? (recited[code] ?? null) : null),
                                "self",
                                () => (recited ? undefined : "catalogue unavailable"),
                            )}
                            perThousand={share}
                            unit={per("of its own")}
                        />
                    </SmallMultiple>

                    <SmallMultiple
                        definition="Relationship edges joining this collection to one of the other three, summed over the three corpus pairs it belongs to."
                        footnote={
                            matrixResult.ok
                                ? "Measured classes only. Where a class was never established for a pair, that pair contributes nothing to this row rather than contributing a zero."
                                : "The cross-corpus matrix could not be read for this row."
                        }
                        title="Links to the other three"
                    >
                        <CorpusStrip
                            caption="Cross-corpus relationship edges, by collection"
                            figures={strip(
                                (code) => edges[code] ?? null,
                                "self",
                                () => (matrixResult.ok ? undefined : "matrix unavailable"),
                            )}
                            perThousand={share}
                            unit={per("of its own")}
                        />
                    </SmallMultiple>

                    <SmallMultiple
                        definition="The divisions each collection is organised by, in its own tradition's names."
                        footnote="Not one hierarchy with four sets of labels. A Yajurvedic adhyaya holds verses directly, with no hymn level between, because the collection is arranged by rite rather than by hymn."
                        title="How it is divided"
                    >
                        <dl className="va-plate-terms">
                            {CORPORA.map(({ code, name }) => (
                                <div key={code}>
                                    <dt>{name}</dt>
                                    <dd>
                                        {(
                                            provenance.works.find((work) => work.veda === code)
                                                ?.hierarchy ?? []
                                        ).join(" → ") || "not recorded"}
                                    </dd>
                                </div>
                            ))}
                        </dl>
                    </SmallMultiple>

                    <SmallMultiple
                        definition="Bodies that the ordinary name of this collection covers and that this build does not hold."
                        footnote="Only the Rigveda's exclusions are confined to layers later than the Samhita. The other three are each missing a parallel body that a reader would reasonably expect the name to include."
                        title="What the name covers and this does not"
                    >
                        <dl className="va-plate-terms">
                            {CORPORA.map(({ code, name }) => {
                                const excluded = byCode.get(code)?.excluded_corpora ?? [];
                                return (
                                    <div key={code}>
                                        <dt>
                                            {name} <span>{excluded.length}</span>
                                        </dt>
                                        <dd>
                                            {excluded.length
                                                ? excluded.map(humanizeCorpus).join(", ")
                                                : "none recorded"}
                                        </dd>
                                    </div>
                                );
                            })}
                        </dl>
                    </SmallMultiple>
                </div>
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        The Samaveda&rsquo;s two blanks sit oddly beside its reputation as the Veda
                        of song. One way to read them is that the layers this build holds are the
                        layers that are straightforward to publish as text, and a sung tradition is
                        the hardest of the four to reduce to a file. That is a claim about
                        publishing rather than about the Samaveda, and nothing on this plate can
                        settle it.
                    </>
                }
                observation={
                    <>
                        The {largest.name} is{" "}
                        {sizeRatio ? `${sizeRatio.toFixed(1)} times` : "far larger than"} the{" "}
                        {smallest.name} by verse count, and carries a translation for{" "}
                        {largestShare ? `${largestShare.toFixed(1)}%` : "almost all"} of its verses.{" "}
                        {gapSentence(untranslated, unrecited)} The four are also divided differently
                        enough that no single hierarchy fits them, which is why this site navigates
                        each collection by its own levels rather than forcing them into a common
                        shape.
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/vedas",
                        label: "Read the four collections",
                        note: "Each one by its own hierarchy, with its exclusions stated before its index",
                    },
                    {
                        href: "/visualizations/transmission",
                        label: "What the collections share",
                        note: "The cross-corpus links counted in the fourth row, pair by pair and class by class",
                    },
                    {
                        href: "/sources",
                        label: "Where each collection came from",
                        note: "The edition behind every verse, and the terms it is held under",
                    },
                    {
                        href: "/limits",
                        label: "What this corpus cannot answer",
                        note: "The recorded limits behind the absences on this plate",
                    },
                ]}
            />
        </>
    );
}

/**
 * The sentence about the collections that have nothing in a layer.
 *
 * Built in code rather than interpolated into the paragraph, because the interesting case is
 * the one where the two lists are the same collection and the prose has to say so once. A
 * template with two optional clauses in it produces "The Samaveda carries one for none of
 * them, and no recitation either" when they agree and a fragment when they do not.
 */
function gapSentence(untranslated: { name: string }[], unrecited: { name: string }[]): string {
    const names = (rows: { name: string }[]) => rows.map((row) => row.name).join(" and ");
    if (!untranslated.length && !unrecited.length) return "";
    if (
        untranslated.length === unrecited.length &&
        untranslated.every((row, index) => row.name === unrecited[index]?.name)
    ) {
        return `The ${names(untranslated)} carries neither a translation nor a recitation.`;
    }
    const clauses: string[] = [];
    if (untranslated.length) clauses.push(`the ${names(untranslated)} carries no translation`);
    if (unrecited.length) clauses.push(`the ${names(unrecited)} carries no recitation`);
    const joined = clauses.join(", and ");
    return `${joined.charAt(0).toUpperCase()}${joined.slice(1)}.`;
}

/** `SAMAVEDA_GRAMAGEYA_GANA` → `Samaveda gramageya gana`. */
function humanizeCorpus(value: string) {
    const words = value.toLowerCase().replaceAll("_", " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
}
