import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { load, vedaNames, vedaOrder, type MaterialCulture, type Metals } from "@/lib/api";
import { entityHref, statusCopy, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "The material world",
    description:
        "What the corpus names and where: animals, crops, metals, rivers and peoples, counted as Sanskrit lexical minima.",
};

const CATEGORY_LABELS: Record<string, string> = {
    all: "Everything",
    animals: "Animals",
    crops: "Crops",
    metals: "Metals",
    rivers: "Rivers",
    tribes: "Peoples",
};

const VEDA_CODES = ["RV", "SV", "YV", "AV"].sort((a, b) => vedaOrder[a] - vedaOrder[b]);

export default async function MaterialCulturePage({
    searchParams,
}: {
    searchParams: Promise<{ category?: string }>;
}) {
    const { category = "all" } = await searchParams;
    const [rowsResult, metalsResult] = await Promise.all([
        load<MaterialCulture>(
            `/insights/material-culture?category=${encodeURIComponent(category)}&limit=40`,
        ),
        load<Metals>("/insights/metals"),
    ]);
    if (!rowsResult.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={rowsResult.status} message={rowsResult.message} />
            </div>
        );
    }
    const data = rowsResult.data;
    const metals = metalsResult.ok ? metalsResult.data : null;

    return (
        <div className="shell page">
            <PageHeading
                title="The material world"
                description="What the four collections name, and in which of them. Every figure is a Sanskrit lexical minimum: a lower bound produced by a registered set of word forms."
            />
            <KnowledgeStatus status={data.data_status} />

            <nav className="kind-tabs" aria-label="Material category">
                {(data.categories_available ?? ["all"]).map((item) => (
                    <Link
                        key={item}
                        href={`/material-culture?category=${item}`}
                        aria-current={category === item ? "page" : undefined}
                    >
                        {CATEGORY_LABELS[item] ?? titleCase(item)}
                    </Link>
                ))}
            </nav>

            <Caveat title="A null is not a zero">
                An empty cell means no registered word form matched in that collection. The registry
                admits attested inflections only, so an empty cell is a fact about the matcher and a
                lower bound of zero. It is never evidence that the corpus is silent.
            </Caveat>

            <div className="matrix-wrap">
                <table className="material-table">
                    <caption className="sr-only">
                        Named things by collection, with the status of each cell.
                    </caption>
                    <thead>
                        <tr>
                            <th scope="col">Named thing</th>
                            <th scope="col">Kind</th>
                            {VEDA_CODES.map((code) => (
                                <th scope="col" key={code}>
                                    {vedaNames[code]}
                                </th>
                            ))}
                            <th scope="col">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.rows?.map((row) => (
                            <tr key={row.entity_key ?? row.label}>
                                <th scope="row">
                                    {row.entity_key ? (
                                        <Link href={entityHref(row.kind, row.entity_key)}>
                                            {row.label}
                                        </Link>
                                    ) : (
                                        row.label
                                    )}
                                </th>
                                <td className="cell-kind">
                                    {titleCase((row.kind ?? "").toLowerCase())}
                                </td>
                                {VEDA_CODES.map((code) => {
                                    const value =
                                        row.by_veda?.[
                                            code.toLowerCase() as "rv" | "sv" | "yv" | "av"
                                        ];
                                    return (
                                        <td
                                            key={code}
                                            className={
                                                value == null ? "cell tone-insufficient" : "cell"
                                            }
                                        >
                                            {value == null ? (
                                                <span className="cell-reason">no match</span>
                                            ) : (
                                                value.toLocaleString()
                                            )}
                                        </td>
                                    );
                                })}
                                <td className="cell-total">
                                    <strong>{row.total_mantras?.toLocaleString()}</strong>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {metals?.declared_gaps?.length ? (
                <section className="declared-gaps">
                    <div className="section-heading small">
                        <h2>Gaps we know are wrong</h2>
                        <p>
                            Cells the matcher cannot reach even though the corpus names the thing.
                            They are declared here rather than left to read as an absence.
                        </p>
                    </div>
                    {metals.declared_gaps.map((gap) => (
                        <article className="gap-card" key={`${gap.entity_key}-${gap.veda}`}>
                            <header>
                                <div>
                                    <span>{statusCopy(gap.evidence_status).label}</span>
                                    <h3>
                                        {gap.display_label} in{" "}
                                        {vedaNames[gap.veda ?? ""] ?? gap.veda}
                                    </h3>
                                </div>
                                {gap.source_witness && (
                                    <span className="gap-witness">
                                        named at {gap.source_witness}
                                    </span>
                                )}
                            </header>
                            <p>{gap.reason}</p>
                            {gap.co_attested_at_witness?.length ? (
                                <p className="panel-note">
                                    Named in the same verse as{" "}
                                    {gap.co_attested_at_witness.join(", ")}.
                                </p>
                            ) : null}
                        </article>
                    ))}
                </section>
            ) : null}

            {metals?.shape && (
                <p className="panel-note">
                    The metals grid returned {metals.shape.cells_returned} of{" "}
                    {metals.shape.cells_expected} cells:{" "}
                    {Object.entries(metals.shape.cells_by_status ?? {})
                        .map(
                            ([status, count]) =>
                                `${count} ${statusCopy(status).label.toLowerCase()}`,
                        )
                        .join(", ")}
                    .
                </p>
            )}

            <Link className="text-link" href="/limits">
                See every recorded limit of this build
                <ArrowRight size={16} aria-hidden="true" />
            </Link>

            <CaveatList caveats={data.caveats} title="How these counts were measured" limit={6} />
            {metals && (
                <CaveatList caveats={metals.caveats} title="Notes on the metals grid" limit={6} />
            )}
        </div>
    );
}
