import Link from "next/link";
import type { Metadata } from "next";
import { CorpusStrip } from "@/components/lab/marks";
import { ServiceUnavailable } from "@/components/empty-state";
import {
    load,
    type AvConcerns,
    type CrossVeda,
    type FormulaDiffusion,
    type MaterialCulture,
    type RitualsInsight,
    type Stats,
    type WorksResponse,
} from "@/lib/api";
import { count, NOT_DRAWN, PLATES, plateHref, type CorpusCode, type PlateSlug } from "@/lib/lab";

/**
 * The Lab index.
 *
 * An atlas has a list of plates at the front, and this is that list: the question each plate
 * answers, the one sentence that says what it is, the methodological caution that has to be
 * read before the figure, and one real measurement from the plate itself.
 *
 * The figures are measured rather than illustrated. A preview that showed a sketch of a chart
 * would be the one thing on this surface that was not data, and an index whose previews are
 * decoration teaches the reader to skip the previews.
 *
 * The page closes with what was considered and not drawn. Without it the index reads as the
 * set of questions the corpus can answer, and it is the set this build can answer honestly.
 */

export const revalidate = 300;

export const metadata: Metadata = {
    title: "Visualizations",
    description: `${PLATES.length} plates over the four Vedic Samhitas: how the corpora differ, which deities are named and which are dedicated to, where Rigvedic wording reappears in the Samaveda, how formulas travel, what the Atharvaveda addresses, how much ritual is modelled, and what the corpus handles.`,
    openGraph: {
        title: "Visualizations | VedAnvaya",
        description: `${PLATES.length} plates over the four Vedic Samhitas, each answering one question and stating what it does not show.`,
    },
};

/** Small counts read better spelled out in a headline, and only small counts appear there. */
const NUMBER_WORDS = [
    "No",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
];

function spellOut(value: number) {
    return NUMBER_WORDS[value] ?? String(value);
}

type Headline = {
    figure: string;
    unit: string;
    strip?: Record<CorpusCode, { value: number | null; absence?: string }>;
};

export default async function LabIndexPage() {
    const [works, stats, matrix, diffusion, concerns, rituals, material] = await Promise.all([
        load<WorksResponse>("/works"),
        load<Stats>("/stats"),
        load<CrossVeda>("/insights/cross-veda"),
        load<FormulaDiffusion>("/insights/formula-diffusion?limit=1"),
        load<AvConcerns>("/insights/atharvaveda/concerns?limit=1"),
        load<RitualsInsight>("/insights/rituals?limit=1"),
        load<MaterialCulture>("/insights/material-culture?limit=1"),
    ]);

    if (!works.ok || !stats.ok) {
        return (
            <div className="va-lab">
                <ServiceUnavailable />
            </div>
        );
    }

    const verses = stats.data.corpus?.find((row) => row.name === "mantras");
    const byVeda = verses?.by_veda;
    const headlines: Partial<Record<PlateSlug, Headline>> = {
        "four-corpora": {
            figure: count(verses?.total) ?? "—",
            unit: `verses across ${works.data.items?.length ?? 4} collections, held in one recension each`,
            strip: {
                RV: { value: byVeda?.rv ?? null },
                SV: { value: byVeda?.sv ?? null },
                YV: { value: byVeda?.yv ?? null },
                AV: { value: byVeda?.av ?? null },
            },
        },
        deities: {
            figure: count(stats.data.deities?.resolved_deities) ?? "—",
            unit: "deities resolved from the registry. The traditional index also names 30 subjects that are not gods, and they are refused.",
        },
    };

    if (matrix.ok) {
        const cells = matrix.data.shape?.cells_by_status ?? {};
        headlines.transmission = {
            figure: `${count(cells.MEASURED ?? 0)} of ${count(matrix.data.shape?.cells_returned ?? 48)}`,
            unit: "cells of the corpus-pair matrix carry a measured count. The rest are typed, not zeroed.",
        };
    }
    if (diffusion.ok) {
        const measured = diffusion.data.coverage?.measured ?? {};
        headlines.formulas = {
            figure: count(measured.reaching_all_four) ?? "—",
            unit: `of ${count(measured.families) ?? "720"} formula families occur in all four collections.`,
        };
    }
    if (concerns.ok) {
        const measured = concerns.data.coverage?.measured ?? {};
        headlines["human-concerns"] = {
            figure: count(measured.afflictions) ?? "—",
            unit: `afflictions and ${count(measured.concerns) ?? "7"} human concerns, with threats kept on a separate axis.`,
        };
    }
    if (rituals.ok) {
        const coverage = rituals.data.coverage_view;
        headlines.ritual = {
            figure: count(coverage?.rituals_modelled) ?? "—",
            unit: `rites carry a modelled structure, and ${count(coverage?.step_edges) ?? "a handful of"} step edges exist across all of them.`,
        };
    }
    if (material.ok) {
        /* `categories_available` includes the `all` pseudo-category, which is a view rather
           than a category and must not be counted as one. */
        const categories = (material.data.categories_available ?? []).filter(
            (name) => name !== "all",
        ).length;
        headlines["material-culture"] = {
            figure: count(material.data.pagination?.total) ?? "—",
            unit: `named things across ${categories || 5} categories, counted by collection.`,
        };
    }

    return (
        <div className="va-lab">
            <header className="va-lab-head">
                <p className="va-lab-eyebrow">Visualizations</p>
                {/* The headline counts the catalogue rather than repeating a number someone
                    typed, so adding or removing a plate cannot leave the page miscounting
                    itself. */}
                <h1>{spellOut(PLATES.length)} plates, and one question each.</h1>
                <p>
                    Each of these answers something a reader could actually ask, and says in the
                    same breath what it does not show. They are not different datasets: they are{" "}
                    {PLATES.length} figures drawn over the one corpus, and every one of them hands
                    you back to the verses it was counted from.
                </p>
            </header>

            <ul className="va-lab-index">
                {PLATES.map((plate) => {
                    const headline = headlines[plate.slug];
                    return (
                        <li key={plate.slug}>
                            {/* The link wraps the title alone and is stretched over the card by
                                CSS. Putting the whole card inside the anchor would fold the
                                figure's table caption into the link's accessible name, so a
                                screen reader would announce the plate as its title followed by
                                every number on the card. */}
                            <article className="va-lab-card">
                                <div className="va-lab-card-lens">
                                    {plate.lens}
                                    <h2>
                                        <Link
                                            className="va-lab-card-link"
                                            href={plateHref(plate.slug)}
                                        >
                                            {plate.title}
                                        </Link>
                                    </h2>
                                </div>
                                <div className="va-lab-card-body">
                                    <p className="va-lab-card-question">{plate.question}</p>
                                    <p className="va-lab-card-summary">{plate.summary}</p>
                                    <p className="va-lab-card-caution">{plate.caution}</p>
                                </div>
                                {headline ? (
                                    <div className="va-lab-card-figure">
                                        <b>{headline.figure}</b>
                                        <span>{headline.unit}</span>
                                        {headline.strip ? (
                                            <CorpusStrip
                                                caption={`Verses held in each collection: ${plate.title}`}
                                                figures={headline.strip}
                                            />
                                        ) : null}
                                    </div>
                                ) : null}
                            </article>
                        </li>
                    );
                })}
            </ul>

            <section className="va-lab-omissions">
                <h2>Considered, and not drawn</h2>
                <p>
                    {NOT_DRAWN.length === 1
                        ? "One figure was"
                        : `${spellOut(NOT_DRAWN.length)} figures were`}{" "}
                    planned and refused. They are here because an index of what shipped reads as the
                    list of things the corpus supports, and it is the list of things this build
                    could draw without misleading you.
                </p>
                <ul>
                    {NOT_DRAWN.map((item) => (
                        <li key={item.title}>
                            <h3>{item.title}</h3>
                            <p>{item.why}</p>
                            {item.href ? (
                                <Link className="text-link" href={item.href}>
                                    {item.hrefLabel ?? "Read more"}
                                </Link>
                            ) : null}
                        </li>
                    ))}
                </ul>
            </section>
        </div>
    );
}
