import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { RegisterOpening } from "@/components/register";
import { Caveat, CaveatList } from "@/components/status";
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

/**
 * The material world.
 *
 * The table was already the right object for this page - it is a matrix, and a matrix is
 * what a matrix should look like. What changed is everything around it: it sat inside a
 * bordered, rounded, filled container, under two stacked caveat panels and a status block,
 * so a reader met three boxes before a single figure.
 *
 * The status and the caveat have not been dropped, because the null cells on this page are
 * the most misreadable thing in the product. The status is now measured furniture in the
 * opening - which collections were read, how many rows, over what - and the "a null is not a
 * zero" note stays a panel, because it is a scope statement about the whole table and that
 * is one of the two places this design keeps a container.
 */
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
            <div className="va-page">
                <LoadFailure status={rowsResult.status} message={rowsResult.message} />
            </div>
        );
    }
    const data = rowsResult.data;
    const metals = metalsResult.ok ? metalsResult.data : null;
    const rows = data.rows ?? [];
    /* Which collections the mention scan read. From the response: a cell's absence only
       means "no alias matched" because every collection here was actually read. */
    const read = data.vedas_reported ?? data.coverage?.vedas_in_scope ?? [];

    return (
        <div className="va-page">
            <RegisterOpening
                title="The material world"
                lede="What the four collections name, and in which of them. Every figure is a Sanskrit lexical minimum: a lower bound produced by a registered set of word forms."
                standing={[
                    { label: "Things listed", value: rows.length.toLocaleString("en-GB") },
                    {
                        label: "Collections read",
                        value: read.length ? read.length.toString() : "not stated",
                        absent: read.length === 0,
                    },
                    { label: "Every figure is", value: statusCopy(data.data_status).label },
                ]}
            />

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

            <div className="va-block-scroll">
                <table className="va-block-table">
                    <caption className="sr-only">
                        Named things by collection, with the status of each cell.
                    </caption>
                    <thead>
                        <tr>
                            <th scope="col">Named thing</th>
                            <th scope="col">Kind</th>
                            {VEDA_CODES.map((code) => (
                                <th className="is-num" scope="col" key={code}>
                                    {vedaNames[code]}
                                </th>
                            ))}
                            <th className="is-num" scope="col">
                                Total
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => (
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
                                <td>{titleCase((row.kind ?? "").toLowerCase())}</td>
                                {VEDA_CODES.map((code) => {
                                    const value =
                                        row.by_veda?.[
                                            code.toLowerCase() as "rv" | "sv" | "yv" | "av"
                                        ];
                                    return (
                                        <td className="is-num" key={code}>
                                            {value == null ? (
                                                <span className="is-none">no match</span>
                                            ) : (
                                                value.toLocaleString("en-GB")
                                            )}
                                        </td>
                                    );
                                })}
                                <td className="is-num is-total">
                                    {row.total_mantras?.toLocaleString("en-GB")}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {metals?.declared_gaps?.length ? (
                <section aria-labelledby="va-declared-gaps" className="va-block">
                    <h2 className="va-block-heading" id="va-declared-gaps">
                        Gaps we know are wrong
                    </h2>
                    <p className="va-block-note">
                        Cells the matcher cannot reach even though the corpus names the thing. They
                        are declared here rather than left to read as an absence.
                    </p>
                    <ul className="va-gap">
                        {metals.declared_gaps.map((gap) => (
                            <li key={`${gap.entity_key}-${gap.veda}`}>
                                <span className="va-gap-name">
                                    <strong>
                                        {gap.display_label} in{" "}
                                        {vedaNames[gap.veda ?? ""] ?? gap.veda}
                                    </strong>
                                    <span>{statusCopy(gap.evidence_status).label}</span>
                                </span>
                                <span className="va-gap-body">
                                    <p>{gap.reason}</p>
                                    {gap.source_witness && (
                                        <p className="va-gap-witness">
                                            Named at {gap.source_witness}
                                            {gap.co_attested_at_witness?.length
                                                ? `, in the same verse as ${gap.co_attested_at_witness.join(", ")}`
                                                : ""}
                                            .
                                        </p>
                                    )}
                                </span>
                            </li>
                        ))}
                    </ul>
                </section>
            ) : null}

            {metals?.shape && (
                <p className="va-block-note">
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

            <p className="va-block-note">
                <Link className="text-link" href="/limits">
                    See every recorded limit of this build
                    <ArrowRight size={16} aria-hidden="true" />
                </Link>
            </p>

            <CaveatList caveats={data.caveats} title="How these counts were measured" limit={6} />
            {metals && (
                <CaveatList caveats={metals.caveats} title="Notes on the metals grid" limit={6} />
            )}
        </div>
    );
}
