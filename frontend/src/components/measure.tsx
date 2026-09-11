import clsx from "clsx";
import { KnowledgeStatus } from "./status";

export type MeasureRow = {
    key: string;
    label: string;
    value: number | null;
    /** Rendered instead of a bar when the value is not a count. */
    status?: string | null;
    note?: string | null;
    tone?: "primary" | "muted" | "excluded";
};

/**
 * A bar chart that is also a table. Every chart states what it counts, over what
 * scope, and what it leaves out; a null is never drawn as a zero-length bar.
 */
export function MeasureChart({
    title,
    definition,
    scope,
    caveat,
    rows,
    unit = "",
    id,
}: {
    title: string;
    definition: string;
    scope?: string;
    caveat?: string;
    rows: MeasureRow[];
    unit?: string;
    id: string;
}) {
    const max = Math.max(1, ...rows.map((row) => row.value ?? 0));
    const headingId = `${id}-title`;
    return (
        <figure className="measure" aria-labelledby={headingId}>
            <figcaption>
                <h3 id={headingId}>{title}</h3>
                <p>{definition}</p>
                {scope && <p className="measure-scope">{scope}</p>}
            </figcaption>
            <table className="measure-table">
                <caption className="sr-only">
                    {title}. {definition}
                </caption>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.key} className={clsx(row.tone && `row-${row.tone}`)}>
                            <th scope="row">{row.label}</th>
                            <td className="measure-track">
                                {row.value == null ? (
                                    <KnowledgeStatus status={row.status} compact />
                                ) : (
                                    <span
                                        className="measure-bar"
                                        style={{
                                            width: `${Math.max(2, (row.value / max) * 100)}%`,
                                        }}
                                        aria-hidden="true"
                                    />
                                )}
                            </td>
                            <td className="measure-value">
                                {row.value == null ? (
                                    <span className="measure-null">not established</span>
                                ) : (
                                    <>
                                        {row.value.toLocaleString()}
                                        {unit && <small> {unit}</small>}
                                    </>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {rows.some((row) => row.note) && (
                <ul className="measure-notes">
                    {rows
                        .filter((row) => row.note)
                        .map((row) => (
                            <li key={`${row.key}-note`}>
                                <strong>{row.label}</strong> {row.note}
                            </li>
                        ))}
                </ul>
            )}
            {caveat && <p className="measure-caveat">{caveat}</p>}
        </figure>
    );
}

/** A ranked list of labelled counts, used where a bar chart would be decoration. */
export function RankedFacts({
    title,
    definition,
    items,
    empty,
}: {
    title: string;
    definition?: string;
    items: Array<{ key: string; label: string; value?: string | number | null }>;
    empty?: React.ReactNode;
}) {
    return (
        <section className="ranked-facts">
            <h3>{title}</h3>
            {definition && <p className="ranked-definition">{definition}</p>}
            {items.length ? (
                <ul>
                    {items.map((item) => (
                        <li key={item.key}>
                            <span>{item.label}</span>
                            {item.value != null && <b>{item.value.toLocaleString()}</b>}
                        </li>
                    ))}
                </ul>
            ) : (
                empty
            )}
        </section>
    );
}
