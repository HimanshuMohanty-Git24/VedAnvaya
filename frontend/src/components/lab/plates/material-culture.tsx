import Link from "next/link";
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
import { encoded, load, type MaterialCulture, type Metals } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";
import { CORPORA, count, PLATES_BY_SLUG, type CorpusCode } from "@/lib/lab";

/**
 * What the corpus handles.
 *
 * The plate exists for the metals grid, and the metals grid exists for one cell in it. `ayas`
 * is named at VSM 18.13 — the verse this graph measures as naming more metals than any other —
 * and no registered alias reaches it, because the elided form folds to a token that is the
 * relative pronoun almost everywhere else in the corpus. Registering it would land hundreds of
 * wrong-sense mentions to catch one right one.
 *
 * So that cell is wrong, it is known to be wrong, and it is labelled rather than quietly
 * corrected. A reader who learns that one cell of a lexical grid can be wrong for a reason
 * that has nothing to do with the text has learned the most useful thing this plate can teach.
 */

const plate = PLATES_BY_SLUG["material-culture"];

const CATEGORIES = ["all", "animals", "crops", "metals", "rivers", "tribes"] as const;

export type Category = (typeof CATEGORIES)[number];

export function isCategory(value: string | undefined): value is Category {
    return (CATEGORIES as readonly string[]).includes(value ?? "");
}

const CATEGORY_LABEL: Record<Category, string> = {
    all: "Everything",
    animals: "Animals",
    crops: "Plants and crops",
    metals: "Metals",
    rivers: "Rivers",
    tribes: "Peoples",
};

const SHOWN = 16;

export async function MaterialCulturePlate({ category = "all" }: { category?: Category }) {
    const [materialResult, metalsResult] = await Promise.all([
        load<MaterialCulture>(`/insights/material-culture?category=${category}&limit=40`),
        load<Metals>("/insights/metals"),
    ]);
    if (!materialResult.ok) {
        return <LoadFailure message={materialResult.message} status={materialResult.status} />;
    }

    const data = materialResult.data;
    const rows = (data.rows ?? []).slice(0, SHOWN);
    const metals = metalsResult.ok ? metalsResult.data : null;
    const gaps = metals?.declared_gaps ?? [];
    const inverting = (metals?.metals ?? []).filter((metal) => metal.ordering_inverts);

    const ranked: Datum[] = rows.map((row) => ({
        key: row.entity_key ?? row.label ?? "",
        label: row.label ?? "",
        note: `${row.kind?.toLowerCase().replaceAll("_", " ")} · named in ${count(row.vedas_reached)} of 4 collections`,
        value: row.total_mantras ?? null,
        absence: "no alias matched",
        href: row.entity_key ? entityHref(row.kind, row.entity_key) : undefined,
    }));

    return (
        <>
            <PlateHeader
                lede="Cattle, horses, barley, rivers, gold. The nouns of daily life, counted by the collection they occur in. What this plate is really about is the one kind of error a lexical count makes: a cell can be empty because the thing is absent, or because the word that names it is a word the matcher cannot safely look for."
                plate={plate}
            />

            <nav aria-label="Category" className="va-controls">
                <span className="va-controls-label">Category</span>
                {CATEGORIES.map((option) => (
                    <Link
                        aria-current={option === category}
                        className="va-control"
                        href={
                            option === "all"
                                ? "/visualizations/material-culture"
                                : `?category=${option}`
                        }
                        key={option}
                        scroll={false}
                    >
                        {CATEGORY_LABEL[option]}
                    </Link>
                ))}
            </nav>

            <PlateFigure
                description={`${category === "all" ? "Everything the registry names" : CATEGORY_LABEL[category]}, ranked by the number of verses in which a registered Sanskrit alias occurs, across all four collections.`}
                footnote={
                    <>
                        Every figure here is a lexical minimum. It counts verses in which a
                        registered alias occurs, so the true figure is at least this and possibly
                        higher — and a row with no figure for a collection means no alias matched
                        there, not that the thing is absent from it.
                    </>
                }
                id="ranked"
                title={`${CATEGORY_LABEL[category]}, by how often they are named`}
            >
                <BarTable
                    caption="Named things by the number of verses naming them"
                    headers={["Thing", "", "Verses"]}
                    rows={ranked}
                />
            </PlateFigure>

            <PlateFigure
                description="The six things named in the most verses, each across all four collections at the rate per 1,000 verses of the collection. Rates rather than counts, because the Rigveda is nearly six times the Samaveda and would otherwise win every row."
                footnote="A collection with no bar in a row had no alias match for that thing. The mention layer reaches all four collections, so this is a matcher result rather than a missing layer."
                id="by-corpus"
                title="Where each thing is named"
            >
                <div className="va-multiples">
                    {rows.slice(0, 6).map((row) => {
                        const per = row.per_1000_by_veda ?? {};
                        const raw = row.by_veda;
                        const figures = Object.fromEntries(
                            CORPORA.map(({ code }) => {
                                const key = code.toLowerCase() as "rv" | "sv" | "yv" | "av";
                                const counted = raw?.[key];
                                const figure: CorpusFigure = {
                                    value: typeof counted === "number" ? (per[code] ?? null) : null,
                                    absence: "no match",
                                };
                                return [code, figure];
                            }),
                        ) as Record<CorpusCode, CorpusFigure>;
                        return (
                            <SmallMultiple
                                definition={`${count(row.total_mantras)} verses across the corpus.`}
                                key={row.entity_key ?? row.label ?? ""}
                                title={row.label ?? ""}
                            >
                                <CorpusStrip
                                    caption={`Verses naming ${row.label} per 1,000 verses, by collection`}
                                    figures={figures}
                                    perThousand
                                    unit="per 1,000"
                                />
                            </SmallMultiple>
                        );
                    })}
                </div>
            </PlateFigure>

            {metals ? (
                <PlateFigure
                    description={`Seven metals against four collections: ${count(metals.shape?.cells_returned ?? 28)} cells, every one of them typed. A cell with no number says which kind of nothing it is, and one of them says that it is wrong.`}
                    footnote={
                        <>
                            The Vedic metal vocabulary is genuinely hard: several of these words are
                            contested as to which metal they name, and one of them is a general word
                            for metal that the corpus also uses for iron and for bronze. The grid
                            counts words, not metallurgy.
                        </>
                    }
                    id="metals"
                    title="The metals grid, and the cell that is wrong"
                >
                    {gaps.map((gap) => (
                        <div className="va-plate-note" key={gap.entity_key ?? gap.display_label}>
                            <strong>
                                {gap.display_label} in the {gap.veda}: this cell is empty and it
                                should not be.
                            </strong>
                            <p>{gap.reason}</p>
                        </div>
                    ))}

                    <div className="va-matrix-scroll" tabIndex={0}>
                        <table className="va-matrix">
                            <caption className="sr-only">
                                Metals by collection: verses in which each metal is named.
                            </caption>
                            <thead>
                                <tr>
                                    <th scope="col">Metal</th>
                                    {CORPORA.map(({ code, name }) => (
                                        <th key={code} scope="col">
                                            <abbr title={name}>{code}</abbr>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {(metals.metals ?? []).map((metal) => {
                                    const cells = new Map(
                                        (metal.by_veda ?? []).map((cell) => [cell.veda, cell]),
                                    );
                                    return (
                                        <tr key={metal.entity_key ?? metal.metal ?? ""}>
                                            <th scope="row">
                                                {metal.entity_key ? (
                                                    <Link
                                                        href={`/entities/metal/${encoded(metal.entity_key)}`}
                                                    >
                                                        {metal.metal}
                                                    </Link>
                                                ) : (
                                                    metal.metal
                                                )}
                                            </th>
                                            {CORPORA.map(({ code }) => {
                                                const cell = cells.get(code);
                                                const matched = cell?.matched_mantras;
                                                const declared = gaps.some(
                                                    (gap) =>
                                                        gap.entity_key === metal.entity_key &&
                                                        gap.veda === code,
                                                );
                                                return (
                                                    <td
                                                        data-cell={
                                                            typeof matched === "number"
                                                                ? "MEASURED"
                                                                : declared
                                                                  ? "DECLARED_GAP"
                                                                  : "NOT_ESTABLISHED_FOR_PAIR"
                                                        }
                                                        key={code}
                                                    >
                                                        {typeof matched === "number" ? (
                                                            count(matched)
                                                        ) : (
                                                            <abbr
                                                                title={
                                                                    declared
                                                                        ? "Declared gap: the metal is named in this collection and no alias reaches it."
                                                                        : (cell?.note ??
                                                                          "No registered alias matched a verse in this collection.")
                                                                }
                                                            >
                                                                {declared ? "!" : "·"}
                                                            </abbr>
                                                        )}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    <ul className="va-matrix-key">
                        <li>
                            <b>·</b> No registered alias matched a verse in this collection. Not a
                            measured zero.
                        </li>
                        <li>
                            <b>!</b> A declared gap: the metal is named in that collection and the
                            matcher cannot reach it.
                        </li>
                        {inverting.length ? (
                            <li>
                                <b>{inverting.length}</b>{" "}
                                {inverting.length === 1 ? "metal" : "metals"} rank differently by
                                raw count than by rate:{" "}
                                {inverting.map((metal) => metal.metal).join(", ")}.
                            </li>
                        ) : null}
                    </ul>

                    {inverting.map((metal) =>
                        metal.ordering_note ? (
                            <p className="va-figure-note" key={metal.entity_key ?? metal.metal}>
                                <strong>{metal.metal}.</strong> {metal.ordering_note} Raw order{" "}
                                {(metal.raw_ordering ?? []).join(" > ")}; by rate{" "}
                                {(metal.normalised_ordering ?? []).join(" > ")}.
                            </p>
                        ) : null,
                    )}
                </PlateFigure>
            ) : null}

            <PlateTakeaway
                interpretation={
                    <>
                        A frequency table of things is a tempting object: it looks like an inventory
                        of a world. It is not. It is an inventory of the words a curated registry
                        knows how to look for, over the verses this build holds, and the declared
                        gap above is the cheapest available proof of the difference.
                    </>
                }
                observation={
                    <>
                        {rows[0] ? (
                            <>
                                {rows[0].label} is named in {count(rows[0].total_mantras)} verses
                                {rows[1] && rows[0].total_mantras && rows[1].total_mantras
                                    ? `, ${(rows[0].total_mantras / rows[1].total_mantras).toFixed(1)} times the next entry (${rows[1].label}, ${count(rows[1].total_mantras)})`
                                    : ""}
                                .{" "}
                            </>
                        ) : null}
                        {inverting.length ? (
                            <>
                                Normalising by collection size changes the order for{" "}
                                {inverting.length === 1
                                    ? inverting[0].metal
                                    : `${count(inverting.length)} of the metals`}
                                : {inverting[0].metal} ranks{" "}
                                {(inverting[0].raw_ordering ?? []).join(" → ")} by raw count and{" "}
                                {(inverting[0].normalised_ordering ?? []).join(" → ")} per 1,000
                                verses. Both orderings are recorded because the raw one partly ranks
                                corpus size.
                            </>
                        ) : (
                            "Every figure here is a lexical minimum, and the registry is the limit rather than the corpus."
                        )}
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/material-culture",
                        label: "The full material index",
                        note: "All forty entries, with their per-collection figures and caveats",
                    },
                    {
                        href: "/entities",
                        label: "Every kind of entity",
                        note: "Animals, plants, metals, places, peoples, objects and ideas",
                    },
                    {
                        href: "/visualizations/ritual",
                        label: "The rite, as far as it is modelled",
                        note: "The subset of these objects that a modelled rite uses",
                    },
                    {
                        href: "/limits",
                        label: "What this layer cannot answer",
                        note: "The recorded limits of the lexical mention layer",
                    },
                ]}
            />
        </>
    );
}
