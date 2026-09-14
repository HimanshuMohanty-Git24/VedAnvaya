import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { BarTable, Figure, ShareStrip, type Datum } from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import { load, type FormulaDiffusion } from "@/lib/api";
import { CORPORA, count, PLATES_BY_SLUG, type CorpusCode } from "@/lib/lab";

/**
 * How a wording travels.
 *
 * The difficulty with this subject is that "formula family" is graph jargon and the thing it
 * names is not: it is a phrase that turns up in more than one place, plus the longer lines
 * that contain it and the slightly different lines that echo it. So the plate opens with the
 * census — how many families reach one collection, two, three, four — and only then shows the
 * families themselves, each as a single bar split into the collections it occurs in.
 *
 * The share strip is the one mark on the Lab whose segments touch, which is why its segments
 * are separated by hatch density rather than by hue and why every segment's count is printed
 * beneath it. A segmented bar with unlabelled segments is the chart form that gets misread
 * most reliably.
 */

const plate = PLATES_BY_SLUG.formulas;

/** How many families the second figure draws. */
const SHOWN = 12;

const REACH_LABEL: Record<number, string> = {
    4: "All four collections",
    3: "Three collections",
    2: "Two collections",
    1: "One collection only",
};

export async function FormulasPlate() {
    const result = await load<FormulaDiffusion>(`/insights/formula-diffusion?limit=${SHOWN}`);
    if (!result.ok) {
        return <LoadFailure message={result.message} status={result.status} />;
    }

    const data = result.data;
    const census = [...(data.span_census ?? [])].sort(
        (a, b) => (b.vedas_reached ?? 0) - (a.vedas_reached ?? 0),
    );
    const families = data.widest_families ?? [];
    const measured = data.coverage?.measured ?? {};
    const total = census.reduce((running, row) => running + (row.families ?? 0), 0);

    /*
     * The takeaway's example, chosen by the data rather than by hand: the family with the most
     * members, and the collection that holds the largest share of its occurrences. A sentence
     * naming one family by name is the sentence most likely to be quietly wrong next month.
     */
    const widest = families[0];
    const widestShares = Object.entries(widest?.occurrences_per_veda ?? {}).sort(
        (a, b) => b[1] - a[1],
    );
    const widestTop = widestShares[0];
    const widestConcentration =
        widestTop && widest?.occurrences ? (widestTop[1] / widest.occurrences) * 100 : null;

    const censusRows: Datum[] = census.map((row) => ({
        key: String(row.vedas_reached),
        label: REACH_LABEL[row.vedas_reached ?? 0] ?? `${row.vedas_reached} collections`,
        note: `${count(row.occurrences)} occurrences across ${count(row.memberships)} memberships`,
        value: row.families ?? null,
        emphasis: row.vedas_reached === 4,
    }));

    return (
        <>
            <PlateHeader
                lede="Some phrases in this corpus are not written once. They are set down, extended, adapted and set down again, in collections that were compiled for different purposes. A formula family is one such phrase plus everything that contains or nearly repeats it, and counting how many collections a family reaches is the cheapest honest measure of how far a wording travelled."
                plate={plate}
            />

            <PlateFigure
                description={`All ${count(measured.families ?? total)} families in this build, grouped by how many of the four collections each one occurs in. The census is complete over the layer rather than a sample of it.`}
                footnote={
                    <>
                        A membership is one formula belonging to one family; an occurrence is one
                        verse carrying one of those formulas. A family with many memberships and few
                        occurrences is a phrase with many recorded variants and few actual
                        appearances.
                    </>
                }
                id="span"
                title="How far a family reaches"
            >
                <div className="va-figure-split">
                    <Figure
                        note={
                            <>
                                of {count(measured.families ?? total)} families occur in every one
                                of the four collections.
                            </>
                        }
                        unit="families reach all four"
                        value={count(measured.reaching_all_four) ?? "—"}
                    />
                    <BarTable
                        caption="Formula families by the number of collections they reach"
                        headers={["Reach", "", "Families"]}
                        rows={censusRows}
                    />
                </div>
            </PlateFigure>

            <PlateFigure
                description={`The ${families.length} families with the most members, each drawn as one bar split into the collections its occurrences fall in. The bar shows composition, not size; the counts beneath it are the sizes.`}
                footnote={
                    <>
                        Cores are the shared wording itself, expansions contain it inside a longer
                        line, and variants differ from it slightly. The three are counted separately
                        because a family of thirteen expansions and one core is a different object
                        from a family of fourteen cores.
                    </>
                }
                id="widest"
                title="Twelve families, and where they land"
            >
                <ol className="va-families">
                    {families.map((family) => {
                        const per = family.occurrences_per_veda ?? {};
                        const shares = Object.fromEntries(
                            CORPORA.map(({ code }) => [code, per[code] ?? null]),
                        ) as Record<CorpusCode, number | null>;
                        const reached = CORPORA.filter(({ code }) => (per[code] ?? 0) > 0).length;
                        return (
                            <li key={family.representative ?? ""}>
                                <div className="va-family-head">
                                    <h3>
                                        <Link
                                            href={`/search?q=${encodeURIComponent(family.representative ?? "")}`}
                                            lang="sa"
                                        >
                                            <span className="va-sanskrit-inline">
                                                {family.representative}
                                            </span>
                                        </Link>
                                    </h3>
                                    <p>
                                        {count(family.members)} members · {count(family.core)} core,{" "}
                                        {count(family.expansions)} expansion
                                        {family.expansions === 1 ? "" : "s"},{" "}
                                        {count(family.variants)} variant
                                        {family.variants === 1 ? "" : "s"} · {reached} of 4
                                        collections
                                    </p>
                                </div>
                                <ShareStrip
                                    label={`Occurrences of ${family.representative} by collection`}
                                    shares={shares}
                                    total={family.occurrences ?? 0}
                                />
                            </li>
                        );
                    })}
                </ol>
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        A phrase that turns up in all four collections may be a quotation, or it may
                        be a piece of common poetic stock that no collection had to borrow from
                        another. These counts cannot distinguish the two, and the families most
                        likely to be common stock are exactly the ones that reach furthest — which
                        is why reach is presented here as reach and not as influence.
                    </>
                }
                observation={
                    <>
                        {count(measured.reaching_all_four)} of {count(measured.families ?? total)}{" "}
                        families occur in all four collections. Most are narrower than that, and a
                        wide family is not the same thing as an evenly spread one:{" "}
                        {widest ? (
                            <>
                                <span className="va-sanskrit-inline" lang="sa">
                                    {widest.representative}
                                </span>{" "}
                                has {count(widest.members)} members across {widestShares.length}{" "}
                                collections, and{" "}
                                {widestConcentration
                                    ? `${widestConcentration.toFixed(0)}%`
                                    : "most"}{" "}
                                of its occurrences fall in one of them.
                            </>
                        ) : (
                            "membership and reach are counted separately for exactly this reason."
                        )}
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/formulas",
                        label: "Every formula family",
                        note: "All 720, with their members and the verses that carry them",
                    },
                    {
                        href: "/visualizations/transmission",
                        label: "What the collections share",
                        note: "The relationship classes these formulas sit underneath",
                    },
                    {
                        href: "/search?q=indra",
                        label: "Search the corpus",
                        note: "Wording, entities and translations, in one index",
                    },
                    {
                        href: "/sources#method-relationships",
                        label: "How families were built",
                        note: "Normalised string match, and what that does and does not establish",
                    },
                ]}
            />
        </>
    );
}
