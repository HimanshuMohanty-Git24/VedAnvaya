import Link from "next/link";
import { AskAboutButton } from "@/components/ask/ask-about-button";
import { LoadFailure } from "@/components/empty-state";
import {
    BarTable,
    CorpusStrip,
    SmallMultiple,
    type CorpusFigure,
    type Datum,
} from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import { encoded, load, type DevataInsight, type DevatasResponse } from "@/lib/api";
import { CORPORA, count, PLATES_BY_SLUG, type CorpusCode } from "@/lib/lab";

/**
 * Named, and dedicated to.
 *
 * The brief for this plate was that a mention and an attribution must never be mixed in one
 * unlabelled count, and the whole layout is built around refusing to. Naming and dedication
 * are two columns with two scopes stated above them, they never share a bar, and the
 * difference between them is shown as a signed number rather than as a correction, because
 * neither is the corrected version of the other.
 *
 * The asymmetry is real and it is the plate's finding: the mention layer reaches all four
 * collections and the traditional ascription apparatus exists for the Rigveda alone. A blank
 * in the dedication column is a missing index, never an absent god.
 */

const plate = PLATES_BY_SLUG.deities;

const CERTAINTIES = {
    default: {
        label: "Certain and probable",
        note: "The product default. Excludes AMBIGUOUS mentions.",
        api: "default",
    },
    exploratory: {
        label: "Include ambiguous",
        note: "Adds the AMBIGUOUS tier. Vedic Sanskrit uses one word for the god Agni and for fire, and this view cannot tell them apart. For candidate generation, not for fact.",
        api: "exploratory",
    },
} as const;

export type Certainty = keyof typeof CERTAINTIES;

export function isCertainty(value: string | undefined): value is Certainty {
    return value === "default" || value === "exploratory";
}

/** How many deities the plate draws. Twelve fills the figure without becoming a directory. */
const SHOWN = 12;

export async function DeitiesPlate({ certainty = "default" }: { certainty?: Certainty }) {
    const exploratory = certainty === "exploratory";
    const listQuery = exploratory ? "&certainty=exploratory&include_ambiguous=true" : "";
    const listResult = await load<DevatasResponse>(`/devatas?limit=${SHOWN}${listQuery}`);
    if (!listResult.ok) {
        return <LoadFailure message={listResult.message} status={listResult.status} />;
    }

    const summaries = listResult.data.items ?? [];
    const insights = await Promise.all(
        summaries.map((summary) =>
            load<DevataInsight>(
                `/insights/devatas/${encoded(summary.id)}?certainty=${CERTAINTIES[certainty].api}`,
            ),
        ),
    );

    const rows = summaries
        .map((summary, index) => {
            const result = insights[index];
            return result.ok ? { summary, insight: result.data } : null;
        })
        .filter((row): row is { summary: (typeof summaries)[number]; insight: DevataInsight } =>
            Boolean(row),
        );

    if (!rows.length) {
        return <LoadFailure message="No deity figures could be read." status={503} />;
    }

    /* Scope, read from the data rather than asserted: whichever corpora the ascription layer
       reaches for these deities is what the column header says it reaches. */
    const ascribedScope = Array.from(
        new Set(rows.flatMap((row) => row.insight.ascribed_scope ?? [])),
    );
    /*
     * One scale across both columns.
     *
     * Scaling each panel to its own maximum drew Indra's 3,566 namings and his 2,869
     * dedications as bars of identical length, which is the false equivalence this plate
     * exists to prevent. Both columns count the same unit - verses - so they share a ceiling,
     * and what they do not share is scope, which is stated in each column's own heading.
     * Sharing the scale is also what makes the informative case visible: Agni is dedicated to
     * by more verses than name him.
     */
    const ceiling = Math.max(
        1,
        ...rows.map((row) =>
            Math.max(row.insight.named_total ?? 0, row.insight.ascribed_total ?? 0),
        ),
    );

    const namedRows: Datum[] = rows.map(({ summary, insight }) => ({
        key: summary.id,
        label: summary.display_label,
        /* No per-row note here. The two panels list the same deities in the same order, so a
           note under one column's rows and not the other's breaks the alignment that makes
           the comparison readable. Structure is on the deity's own page. */
        value: insight.named_total ?? null,
        absence: "no mention edge",
        href: `/devatas/${encoded(summary.id)}`,
    }));

    const ascribedRows: Datum[] = rows.map(({ summary, insight }) => ({
        key: summary.id,
        label: summary.display_label,
        value: insight.ascribed_total ?? null,
        absence: "no ascription",
        href: `/devatas/${encoded(summary.id)}`,
    }));

    const leader = rows[0];

    /*
     * Does normalising reorder the deities?
     *
     * Asserted in the takeaway, so it is measured here: rank the shown deities by their rate
     * in the Rigveda and again by their rate in the Atharvaveda, and compare the sequences.
     * If the two agree, the paragraph says so instead.
     */
    const orderBy = (code: "RV" | "AV") =>
        [...rows]
            .sort(
                (a, b) =>
                    (b.insight.named_by_veda?.per_1000_by_veda?.[code] ?? 0) -
                    (a.insight.named_by_veda?.per_1000_by_veda?.[code] ?? 0),
            )
            .map((row) => row.summary.id);
    const rigvedic = orderBy("RV");
    const atharvavedic = orderBy("AV");
    const reordered = rigvedic.some((id, index) => id !== atharvavedic[index]);

    const ambiguous = rows.reduce(
        (total, row) => total + (row.insight.certainty?.ambiguous_count ?? 0),
        0,
    );

    return (
        <>
            <PlateHeader
                lede="A verse that says the name of a god and a hymn that the tradition assigns to a god are two different records. This product keeps them apart everywhere, and this is the plate where the reason becomes visible: one of them spans all four collections and the other exists for one."
                plate={plate}
            />

            <nav aria-label="Certainty" className="va-controls">
                <span className="va-controls-label">Mentions counted</span>
                {(Object.keys(CERTAINTIES) as Certainty[]).map((option) => (
                    <Link
                        aria-current={option === certainty}
                        className="va-control"
                        href={
                            option === "default"
                                ? "/visualizations/deities"
                                : `?certainty=${option}`
                        }
                        key={option}
                        scroll={false}
                    >
                        {CERTAINTIES[option].label}
                    </Link>
                ))}
                <span className="va-controls-label">{CERTAINTIES[certainty].note}</span>
            </nav>

            {exploratory ? (
                <div className="va-plate-note">
                    <strong>You are looking at the exploratory view.</strong>
                    <p>
                        {count(ambiguous)} ambiguous mentions are included in the figures below. An
                        ambiguous mention is one where the resolver could not decide between the god
                        and the ordinary noun, so these totals are upper bounds and are not the
                        product&rsquo;s reported figures.
                    </p>
                </div>
            ) : null}

            <PlateFigure
                description={`The ${rows.length} most-named deities in the corpus, in two columns. The left column counts verses that name the deity, across all four collections. The right counts verses carrying the traditional ascription of their hymn to that deity, which exists for ${ascribedScope.join(", ") || "one collection"}. Both columns count verses and share one scale, so a shorter bar is a smaller count; what they do not share is scope, and they are never added.`}
                footnote={<>{rows[0]?.insight.ascription_note}</>}
                id="named-versus-ascribed"
                title="Named in a verse, and dedicated to by its hymn"
            >
                <div className="va-panels">
                    <section className="va-panel">
                        <header>
                            <h3>Named</h3>
                            <p>
                                Verses in which the deity is named. Reaches all four collections, at
                                the{" "}
                                {exploratory
                                    ? "CERTAIN, PROBABLE and AMBIGUOUS"
                                    : "CERTAIN and PROBABLE"}{" "}
                                tiers.
                            </p>
                        </header>
                        <BarTable
                            caption="Verses naming each deity, across all four collections"
                            headers={["Deity", "", "Verses"]}
                            max={ceiling}
                            rows={namedRows}
                        />
                    </section>

                    <section className="va-panel">
                        <header>
                            <h3>Dedicated to</h3>
                            <p>
                                Verses whose hymn the traditional index assigns to the deity.
                                Reaches {ascribedScope.join(", ") || "one collection"} only. A blank
                                here is a missing index, not an absent god.
                            </p>
                        </header>
                        <BarTable
                            caption="Verses ascribed to each deity by the traditional index"
                            headers={["Deity", "", "Verses"]}
                            max={ceiling}
                            rows={ascribedRows}
                        />
                    </section>
                </div>
            </PlateFigure>

            <PlateFigure
                description="The same deities as rates rather than totals: verses naming each one per 1,000 verses of the collection they are counted in. This is the only form in which the four collections are comparable, because they differ in size by nearly six to one."
                footnote={
                    <>
                        The mention layer is not one instrument. The Rigvedic figures come from a
                        manual scholarly lemma annotation; the other three collections are matched
                        on surface tokens and sandhi, with no morphology behind them. A Rigvedic
                        rate and an Atharvavedic rate are therefore measured differently, and a
                        small difference between them should not be read as a difference in the
                        texts.
                    </>
                }
                id="named-rates"
                title="Naming rates, collection by collection"
            >
                <div className="va-multiples">
                    {rows.slice(0, 9).map(({ summary, insight }) => {
                        const per = insight.named_by_veda?.per_1000_by_veda ?? {};
                        const raw = insight.named_by_veda?.by_veda;
                        const figures = Object.fromEntries(
                            CORPORA.map(({ code }) => {
                                const key = code.toLowerCase() as "rv" | "sv" | "yv" | "av";
                                const counted = raw?.[key];
                                const figure: CorpusFigure = {
                                    value: typeof counted === "number" ? (per[code] ?? null) : null,
                                    absence: "not named",
                                };
                                return [code, figure];
                            }),
                        ) as Record<CorpusCode, CorpusFigure>;
                        return (
                            <SmallMultiple
                                definition={`${count(insight.named_total)} verses name this deity in the corpus.`}
                                key={summary.id}
                                title={summary.display_label}
                            >
                                <CorpusStrip
                                    caption={`Verses naming ${summary.display_label} per 1,000 verses, by collection`}
                                    figures={figures}
                                    perThousand
                                    unit="per 1,000"
                                />
                            </SmallMultiple>
                        );
                    })}
                </div>
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        Where a deity is named far more often than it is dedicated to, one reading
                        is that the name had become part of the poetic vocabulary rather than the
                        subject of the hymn. The opposite case is the more interesting one: a deity
                        whose hymns are dedicated to it and whose name the verses rarely say.
                        Neither reading can be settled from these counts, because the two columns do
                        not cover the same collections.
                    </>
                }
                observation={
                    <>
                        {leader ? (
                            <>
                                {leader.summary.display_label} is named in{" "}
                                {count(leader.insight.named_total)} verses across the four
                                collections and carries {count(leader.insight.ascribed_total)} in
                                the traditional ascription, which exists for{" "}
                                {ascribedScope.join(", ") || "one collection"} alone.{" "}
                            </>
                        ) : null}
                        {reordered
                            ? "The collections do not agree on the order: ranking these deities by their rate in the Atharvaveda gives a different sequence from ranking them by their rate in the Rigveda, so a deity common in one is not automatically common in the other."
                            : "Ranked by rate, the Rigvedic and Atharvavedic orders of these deities agree, which is itself worth noting given how differently the two collections are put together."}
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/devatas",
                        label: "All 184 deities",
                        note: "The resolved pantheon, with the 30 non-divine ascription subjects refused",
                    },
                    leader
                        ? {
                              href: `/devatas/${encoded(leader.summary.id)}`,
                              label: `${leader.summary.display_label} in full`,
                              note: "Naming, ascription, structural spread and the verses behind each",
                          }
                        : {
                              href: "/devatas",
                              label: "Deity profiles",
                              note: "Naming and ascription for one deity at a time",
                          },
                    {
                        href: "/sources#method-attribution",
                        label: "Why naming and dedication are kept apart",
                        note: "The methodological distinction this plate is built on",
                    },
                    {
                        href: "/limits",
                        label: "What the deity layer cannot answer",
                        note: "Including why there is no map of deity communities",
                    },
                ]}
            />

            {leader ? (
                <p className="va-plate-ask">
                    <AskAboutButton
                        entityLabel={leader.summary.display_label}
                        label={`Ask about ${leader.summary.display_label}`}
                        variant="secondary"
                    />
                </p>
            ) : null}
        </>
    );
}
