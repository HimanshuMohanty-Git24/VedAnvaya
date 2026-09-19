import { LoadFailure } from "@/components/empty-state";
import { Register, RegisterOpening, type RegisterRow } from "@/components/register";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type RitualsResponse } from "@/lib/api";

export const metadata = {
    title: "Rituals",
    description:
        "The rites this graph models, explored through passages, roles, objects and stated steps.",
};

/**
 * The rite register.
 *
 * This was a four-up card grid, and the cards were the problem rather than the data: one
 * rite's description runs 640 characters and inventories two Yajurvedic adhyayas, so its
 * card was three times the height of its neighbour and the row it sat in grew to match,
 * leaving four hundred pixels of empty container on either side of it.
 *
 * As a register the rows are level, the glosses start on one line, and the two figures the
 * cards buried in a footer - how many verses name the rite, and whether any order was
 * recorded for it - are ranged at the right margin where a reader can scan the column.
 */
export default async function RitualsPage() {
    const result = await load<RitualsResponse>("/rituals?limit=25");
    if (!result.ok) {
        return (
            <div className="va-page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    const items = data.items ?? [];
    const coverage = items[0]?.inventory_coverage;

    /*
     * The ceiling is the largest figure in *this* register, not in the class.
     *
     * The list is capped at 25 of the 103 modelled rites, so a bar drawn against the class
     * maximum would be a share of something the page never shows.
     */
    const ceiling = Math.max(0, ...items.map((item) => item.passage_count ?? 0));

    const rows: RegisterRow[] = items.map((item) => ({
        key: item.id,
        href: `/rituals/${encoded(item.id)}`,
        name: item.display_label ?? item.label_iast ?? item.id,
        gloss: item.short_description,
        /*
         * The step layers, in the service's own words.
         *
         * `subtitle` already distinguishes the three numbered steps the Samhita itself
         * states from the sutra-attested procedure, and that distinction is the whole
         * reason the ritual layer is honest. The card printed "no stated order" instead,
         * which flattened both layers into one.
         */
        note: item.subtitle,
        figure: item.passage_count,
        unit: item.passage_count === 1 ? "verse names it" : "verses name it",
        absent: "no registered alias was matched",
    }));

    return (
        <div className="va-page">
            <RegisterOpening
                title="Rites the corpus names"
                lede="Read through the passages that describe them, the people who perform them, and what is offered."
                standing={[
                    { label: "Rites modelled", value: "103" },
                    { label: "Shown here", value: items.length.toLocaleString("en-GB") },
                    { label: "Ranked by", value: "verses naming the rite" },
                ]}
            />
            {coverage && (
                <Caveat title="Not a taxonomy of Vedic ritual" tone="boundary">
                    {coverage}
                </Caveat>
            )}
            <Register
                aria-label="Rites"
                ceiling={ceiling}
                columns={{ name: "Rite", figure: "Verses naming it" }}
                rows={rows}
            />
            <CaveatList caveats={data.caveats} title="How this list was scoped" />
        </div>
    );
}
