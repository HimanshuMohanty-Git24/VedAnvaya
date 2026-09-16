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
 * This is the plate most easily made dishonest, because a small curated ritual layer renders
 * perfectly well as a confident diagram of Vedic ritual. So the coverage statement is the
 * first thing on the page and the content comes second.
 *
 * Every figure here is read from `coverage` in the payload. The previous version typed them
 * into prose -- "eight rites, fourteen implements, three step edges" -- and went on saying so
 * after the graph held 103 rites and 3,121 sutra-attested steps, because nothing compares a
 * sentence to the data beside it.
 *
 * Two step layers are reported apart, and never summed. `step_edges` is what a Samhita text
 * numbers in its own words; `procedure_step_edges` is what a Srautasutra prints. Neither one
 * gives a rite a recoverable sequence, and they fail to for different reasons: the first
 * barely exists, and the second is independently numbered per source work so its groups do
 * not compose.
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
                lede="The Vedas are, among other things, the libretto of a sacrifice. What this build holds of that sacrifice is a curated layer whose exact size is measured beneath, and the honest thing to show first is the shape of what is missing."
                plate={plate}
            />

            <div className="va-plate-note">
                <strong>This is modelled coverage, not a taxonomy of Vedic ritual.</strong>
                <p>{coverage?.statement}</p>
            </div>

            <PlateFigure
                description={`The ${count(coverage?.rituals_modelled) ?? "—"} rites this build models, by the number of verses in which a registered alias for the rite occurs. The figure beside each row is what has been attached to it: objects, offerings, deities, and whether any sequence was recorded.`}
                footnote={
                    <>
                        The Brahmana and Srautasutra prose that describes the srauta apparatus is
                        not held as text by this product. What it does hold is{" "}
                        {count(coverage?.procedure_step_edges) ?? "—"} located sutra steps drawn
                        from {count(coverage?.procedure_source_works) ?? "—"} works, each numbering
                        its own sequence from 1 — so they are points a source fixes, not a
                        procedure that runs. The apparatus itself is still visible only where a
                        Samhita verse names it.
                    </>
                }
                id="rites"
                title="The modelled rites, and what is attached to them"
            >
                <div className="va-figure-split">
                    <Figure
                        note={
                            <>
                                in the whole graph, all on one rite.{" "}
                                {withSteps.length
                                    ? `Only ${withSteps.map((row) => row.ritual).join(", ")} carries any.`
                                    : null}{" "}
                                A second and much larger layer is sutra-attested —{" "}
                                {count(coverage?.procedure_step_edges) ?? "—"} steps over{" "}
                                {count(coverage?.rituals_with_procedure) ?? "—"} rites — and it does
                                not close the gap: each work numbers its own sequence, and{" "}
                                {count(coverage?.procedure_partial_steps) ?? "—"} of those steps
                                state a position without printing the run it falls in.
                            </>
                        }
                        unit="steps the Samhita numbers in its own words"
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
                        {count(coverage?.implements_curated) ?? "—"} curated objects are linked to a
                        rite and so eligible for this ranking. The amulet and the drum are among
                        those that are not, and their absence here is a missing link rather than a
                        missing attestation.
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
                        label: "The modelled rites",
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
