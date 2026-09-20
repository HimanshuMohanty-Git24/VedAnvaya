import type { components } from "@/lib/api-schema";
import { className as humanClassName, humanizePredicate } from "@/lib/knowledge";
import { vedaNames } from "@/lib/api";

type MetricRow = components["schemas"]["DerivedMetricRow"];

/**
 * A derived-measure family, drawn as the matrix it is.
 *
 * ## What was there
 *
 * Sixteen bordered cards in a four-up grid, every one of them headed "Animal mention
 * distribution", every one carrying the same two sentences of boilerplate, and the only
 * thing that differed between them a number. Measured on the live response, those sixteen
 * rows are not sixteen measures at all: they are the cells of one measure, each carrying a
 * `subject` and a `dimension`, and the grid was drawing a 5-by-4 table as sixteen
 * unconnected facts with its structure thrown away and its caption repeated sixteen times.
 *
 * ## What a missing cell means here
 *
 * Not zero, and not "the corpus is silent". The section is capped, so a cell with no row in
 * the response is a cell **this view did not receive** - and at every cap tried, between a
 * fifth and a quarter of the matrix is in that state. That is a fact about the request and
 * it is printed as one. Reading an empty cell as an absence is exactly the misreading this
 * product exists to prevent, and it would be the easiest one to make on a page whose own
 * heading is "Evidence and interpretation".
 *
 * ## No bars
 *
 * The service's own note on every row says it: "Any reading of a trend in these numbers
 * belongs in an InterpretiveClaim, not here." A length channel across the cells would be
 * exactly that reading, drawn.
 */

/**
 * The label for one axis value.
 *
 * A work key resolves to its collection's name; anything else is spelled out from its last
 * key segment. Deliberately *not* parsed further: `AHI-SERPENT` could be rendered as
 * "serpent (ahi)" to match the house style elsewhere, and that is a guess about how a key
 * is composed which is wrong the moment a key like `SOMA-PRESSING` arrives. The full key
 * travels in the `title`, so nothing is lost by declining to interpret it.
 */
function axisLabel(key: string): string {
    const work = /^VG:WORK:([A-Z]{2}):/.exec(key);
    if (work) return vedaNames[work[1]] ?? key;
    const tail = key.split(":").pop() ?? key;
    return humanizePredicate(tail.replaceAll("-", "_"));
}

export function DerivedMatrix({ family, rows }: { family: string; rows: MetricRow[] }) {
    /* Axis order is first-appearance order, which is the service's own ordering. */
    const subjects: string[] = [];
    const dimensions: string[] = [];
    const cells = new Map<string, MetricRow>();
    for (const row of rows) {
        const subject = row.subject ?? "";
        const dimension = row.dimension ?? "";
        if (subject && !subjects.includes(subject)) subjects.push(subject);
        if (dimension && !dimensions.includes(dimension)) dimensions.push(dimension);
        cells.set(`${subject}\u0000${dimension}`, row);
    }

    const missing = subjects.length * dimensions.length - cells.size;
    /* The family's note, printed once. It is identical on every row, which is what made
       sixteen cards sixteen copies of one paragraph. */
    const note = rows.find((row) => row.interpretation)?.interpretation ?? null;
    const heading = humanClassName(family);

    return (
        <div className="va-block">
            <h3 className="va-block-heading">{heading}</h3>
            {note && <p className="va-block-note">{note}</p>}
            <div className="va-block-scroll">
                <table className="va-block-table">
                    <caption className="sr-only">
                        {heading}: one cell per subject and collection.
                    </caption>
                    <thead>
                        <tr>
                            <th scope="col">Subject</th>
                            {dimensions.map((dimension) => (
                                <th className="is-num" key={dimension} scope="col">
                                    {axisLabel(dimension)}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {subjects.map((subject) => (
                            <tr key={subject}>
                                <th scope="row" title={subject}>
                                    {axisLabel(subject)}
                                </th>
                                {dimensions.map((dimension) => {
                                    const cell = cells.get(`${subject}\u0000${dimension}`);
                                    return (
                                        <td className="is-num" key={dimension}>
                                            {cell?.value == null ? (
                                                <span className="is-none">not returned</span>
                                            ) : (
                                                cell.value.toLocaleString("en-GB")
                                            )}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {missing > 0 && (
                <p className="va-block-note">
                    {missing} of the {subjects.length * dimensions.length} cells in this matrix
                    were not returned in this view, which is capped. An empty cell here is a
                    statement about the request and never a measured zero.
                </p>
            )}
        </div>
    );
}

/** Group a section's metric rows by the family each belongs to, in first-appearance order. */
export function byFamily(rows: MetricRow[]): Array<{ family: string; rows: MetricRow[] }> {
    const out: Array<{ family: string; rows: MetricRow[] }> = [];
    for (const row of rows) {
        const family = row.metric_family ?? row.metric_name ?? "measure";
        const existing = out.find((group) => group.family === family);
        if (existing) existing.rows.push(row);
        else out.push({ family, rows: [row] });
    }
    return out;
}
