import type { CrossVeda } from "@/lib/api";
import { cellState, connectionCopy, pairName, plainNote } from "./connection-copy";

type PairRow = NonNullable<CrossVeda["pairs"]>[number];
type ClassRow = NonNullable<CrossVeda["relationship_classes"]>[number];

/**
 * The full cell-by-cell evidence, behind a disclosure.
 *
 * It is the last thing on the page rather than the first because a 6 x 8 grid of
 * typed cells is a record, not an interface: a reader arrives wanting to know what
 * joins the Rigveda to the Samaveda, and a matrix answers that only after they have
 * worked out what eight column headings mean.
 *
 * Below 72rem the table stacks into one block per corpus pair. The column headings
 * are then carried on each value by `data-label`, which is why every `td` sets one:
 * a table that can only be read by scrolling sideways is a table a phone reader
 * never reads. Nothing is dropped in the narrow layout -- every cell is present in
 * both, because the cells that carry no count are the ones most worth keeping.
 *
 * The roles are explicit rather than redundant. Changing `display` on a table drops
 * its implicit table semantics in every engine, so a stacked table without them is
 * read to assistive technology as a run of unrelated blocks.
 */
export function EvidenceMatrix({
    pairs,
    classes,
    shape,
}: {
    pairs: PairRow[];
    classes: ClassRow[];
    shape?: CrossVeda["shape"] | null;
}) {
    if (!pairs.length || !classes.length) return null;
    const counted = shape?.cells_by_status?.MEASURED ?? null;
    const returned = shape?.cells_returned ?? pairs.length * classes.length;

    return (
        <details className="va-conn-evidence">
            <summary className="va-conn-evidence-summary">
                <span>View the full evidence matrix</span>
                <small>
                    {pairs.length} corpus pairs across {classes.length} kinds of connection
                    {counted == null
                        ? `, ${returned} cells`
                        : `, ${returned} cells of which ${counted} carry a count`}
                </small>
            </summary>
            <div className="va-conn-evidence-body">
                <p className="va-conn-evidence-key">
                    A number is a measured count of connections. Every other cell states which kind
                    of empty it is, and no cell is drawn as zero unless zero was the measurement.
                </p>
                <div className="va-conn-table-wrap">
                    <table className="va-conn-table" role="table">
                        <caption className="sr-only">
                            Every relationship class for every corpus pair, with the status of each
                            cell.
                        </caption>
                        <thead role="rowgroup">
                            <tr role="row">
                                <th scope="col" role="columnheader">
                                    Corpus pair
                                </th>
                                {classes.map((relation) => (
                                    <th scope="col" role="columnheader" key={relation.relationship_class}>
                                        {connectionCopy(relation.relationship_class).name}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody role="rowgroup">
                            {pairs.map((pair) => (
                                <tr role="row" key={pair.pair}>
                                    <th scope="row" role="rowheader" data-label="Corpus pair">
                                        {pairName(pair.vedas)}
                                    </th>
                                    {classes.map((relation) => {
                                        const copy = connectionCopy(relation.relationship_class);
                                        const cell = (pair.cells ?? []).find(
                                            (row) =>
                                                row.relationship_class ===
                                                relation.relationship_class,
                                        );
                                        const state = cellState(cell?.status);
                                        const reason = plainNote(cell?.note) || state.meaning;
                                        return (
                                            <td
                                                key={relation.relationship_class}
                                                className="va-conn-cell"
                                                role="cell"
                                                data-tone={state.tone}
                                                data-label={copy.name}
                                                title={reason}
                                            >
                                                {cell?.status === "MEASURED" && cell.edges != null ? (
                                                    <b className="va-conn-figure">
                                                        {cell.edges.toLocaleString()}
                                                    </b>
                                                ) : (
                                                    <span className="va-conn-state">
                                                        {state.label}
                                                    </span>
                                                )}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>
    );
}
