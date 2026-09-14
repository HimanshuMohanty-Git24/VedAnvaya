import { LoadFailure } from "@/components/empty-state";
import { BarTable, Figure, type Datum } from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import { encoded, load, type RitualsInsight } from "@/lib/api";
import { count, PLATES_BY_SLUG, plural } from "@/lib/lab";

/**
 * The rite, as far as it is modelled.
 *
 * This is the plate most easily made dishonest, because a ritual layer with eight rites in it
 * renders perfectly well as a confident diagram of Vedic ritual. So the coverage statement is
 * the first thing on the page and the content comes second: eight modelled rites, three step
 * edges across all eight, and therefore no rite anywhere in this graph with a recoverable
 * sequence.
 *
 * The endpoint's own `not_covered` list is printed rather than paraphrased. It records, among
 * other things, that the chariot and the thunderbolt are absent because no modelled rite uses
 * them — which is the correction to an earlier version of this question that ranked them as
 * the corpus's foremost ritual objects.
 */

const plate = PLATES_BY_SLUG.ritual;

export async function RitualPlate() {
    const result = await load<RitualsInsight>("/insights/rituals?limit=25");
    if (!result.ok) {
        return <LoadFailure message={result.message} status={result.status} />;
    }

    const data = result.data;
    const coverage = data.coverage_view;
    const rituals = data.rituals ?? [];
    const objects = data.objects ?? [];

    const ritualRows: Datum[] = rituals.map((row) => ({
        key: row.entity_key ?? row.ritual ?? "",
        label: row.ritual ?? "",
        note: `${plural(row.objects, "object")} · ${plural(row.offerings, "offering")} · ${plural(row.devatas, "deity", "deities")} · ${row.steps ? plural(row.steps, "step edge") : "no steps recorded"}`,
        value: row.matched_mantras ?? null,
        absence: "no alias matched",
        href: row.entity_key ? `/rituals/${encoded(row.entity_key)}` : undefined,
    }));

    const objectRows: Datum[] = objects.map((row) => ({
        key: row.implement ?? "",
        label: row.implement ?? "",
        note: `named in ${count(row.vedas_with_matches)} of 4 collections · linked to ${plural(row.curated_rituals, "rite")}`,
        value: row.matched_mantras_minimum ?? null,
        absence: "no alias matched",
    }));

    const withSteps = rituals.filter((row) => (row.steps ?? 0) > 0);
    /* The takeaway's arithmetic, done here rather than written into the paragraph. */
    const ranked = [...rituals].sort((a, b) => (b.matched_mantras ?? 0) - (a.matched_mantras ?? 0));
    const tailTotal = ranked
        .slice(2)
        .reduce((running, row) => running + (row.matched_mantras ?? 0), 0);

    return (
        <>
            <PlateHeader
                lede="The Vedas are, among other things, the libretto of a sacrifice. What this build holds of that sacrifice is a small, curated layer — eight rites, fourteen implements, three step edges — and the honest thing to show first is the size of what is missing."
                plate={plate}
            />

            <div className="va-plate-note">
                <strong>This is modelled coverage, not a taxonomy of Vedic ritual.</strong>
                <p>{coverage?.statement}</p>
            </div>

            <PlateFigure
                description="The eight rites this build models, by the number of verses in which a registered alias for the rite occurs. The figure beside each row is what has been attached to it: objects, offerings, deities, and whether any sequence at all was recorded."
                footnote={
                    <>
                        The prose that actually describes the srauta apparatus — the Brahmanas and
                        the Srautasutras — is not held by this product at all. A rite is visible
                        here only where a Samhita verse happens to name it, which is the reason the
                        step count is what it is.
                    </>
                }
                id="rites"
                title="Eight rites, and what is attached to them"
            >
                <div className="va-figure-split">
                    <Figure
                        note={
                            <>
                                across all eight rites, so no rite in this graph has a recoverable
                                sequence.{" "}
                                {withSteps.length
                                    ? `Only ${withSteps.map((row) => row.ritual).join(", ")} carries any.`
                                    : null}
                            </>
                        }
                        unit="step edges in the whole layer"
                        value={count(coverage?.step_edges) ?? "—"}
                    />
                    <BarTable
                        caption="Modelled rites by the number of verses naming them"
                        headers={["Rite", "", "Verses"]}
                        rows={ritualRows}
                    />
                </div>
            </PlateFigure>

            <PlateFigure
                description={`The ${objects.length} implements linked to a modelled rite, by the number of verses in which each is named. These are the objects the sacrifice is performed with, as far as the curation reaches.`}
                footnote={
                    <>
                        Fourteen of twenty-three curated objects are linked to a rite and so
                        eligible for this ranking. The amulet and the drum are among the nine that
                        are not, and their absence here is a missing link rather than a missing
                        attestation.
                    </>
                }
                id="implements"
                title="What the rite is performed with"
            >
                <BarTable
                    caption="Ritual implements by the number of verses naming them"
                    headers={["Implement", "", "Verses"]}
                    rows={objectRows}
                />
            </PlateFigure>

            <PlateFigure
                description="What this layer does not cover, in the endpoint's own words. It is printed rather than summarised because each of these is a specific correction to a specific wrong answer."
                id="not-covered"
                title="What is not here"
            >
                <ul className="va-doc-negations">
                    {(data.not_covered ?? []).map((line) => (
                        <li key={line}>
                            <span>{line}</span>
                        </li>
                    ))}
                </ul>
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        The shape of this layer says something about the Samhitas rather than about
                        Vedic ritual: a collection of verses recited during a rite does not describe
                        the rite, because everyone present already knew it. The procedure lives in
                        the prose literature, and the prose literature is not held here.
                    </>
                }
                observation={
                    <>
                        The two rites named in the most verses — {ranked[0]?.ritual} at{" "}
                        {count(ranked[0]?.matched_mantras)} and {ranked[1]?.ritual} at{" "}
                        {count(ranked[1]?.matched_mantras)} — account for most of the layer&rsquo;s
                        reach; the remaining {ranked.length - 2} are named in {count(tailTotal)}{" "}
                        verses between them. Across all {ranked.length} there are{" "}
                        {count(coverage?.step_edges)} step edges, so nothing here supports a claim
                        about the order in which anything was done.
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/rituals",
                        label: "The eight rites",
                        note: "Each with its objects, offerings, performers and verses",
                    },
                    {
                        href: "/entities/object",
                        label: "Objects in the corpus",
                        note: "Including the nine curated objects no modelled rite links to",
                    },
                    {
                        href: "/visualizations/material-culture",
                        label: "What the corpus handles",
                        note: "The wider world of named things these implements belong to",
                    },
                    {
                        href: "/limits",
                        label: "What this layer cannot answer",
                        note: "The recorded limits behind the coverage statement above",
                    },
                ]}
            />
        </>
    );
}
