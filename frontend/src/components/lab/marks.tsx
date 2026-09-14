import clsx from "clsx";
import { CORPORA, count, rate, type CorpusCode } from "@/lib/lab";

/**
 * The Lab's marks.
 *
 * Three rules hold across all of them, and they are what keep this surface from turning into
 * a dashboard.
 *
 * **Every chart is a table.** Not a table as a fallback: the table *is* the chart, and the bar
 * is drawn inside the cell that already holds the number. That gives the figure a real row
 * header, a real caption and a real reading order for nothing, and it means a reader on a
 * phone who cannot see a 40px bar can still read the column.
 *
 * **No categorical palette.** There is one ink and one accent. A corpus is identified by its
 * position in the row and by its name in the row header, never by a colour, so the figures
 * survive greyscale, colour blindness and the dark theme without a legend. The accent marks
 * the one row a reader asked about and nothing else.
 *
 * **A null is never a zero.** `null` from these endpoints means "not reached" or "layer not
 * built", and drawing it as a bar of length zero asserts a measured absence that was never
 * measured. Every mark here renders it as a stated absence instead.
 */

export type Datum = {
    key: string;
    label: string;
    /** `null` is an absence, and is rendered as one. */
    value: number | null;
    /** Printed instead of the bar when `value` is null. */
    absence?: string;
    /** Printed beneath the row when present. */
    note?: string;
    href?: string;
    /** Draws the row in the accent. At most one row per figure. */
    emphasis?: boolean;
    /** Replaces the formatted value, for rows whose figure is not a plain count. */
    display?: string;
};

const DEFAULT_ABSENCE = "no figure";

function barWidth(value: number, max: number) {
    /*
     * A 0.4% floor, so a genuine but tiny count is still a mark rather than nothing.
     *
     * A measured zero is the exception and draws no mark at all. Giving it the floor put a
     * hairline tick beside the Samaveda's "0 translations", which reads as "almost none"
     * rather than as none - the one thing a zero row must not do.
     */
    if (value === 0) return "0%";
    return `${Math.max(0.4, (value / Math.max(max, 1)) * 100)}%`;
}

/**
 * A ranked bar table.
 *
 * `max` is passed in rather than derived when several of these are meant to be read against
 * each other; derived per-figure otherwise.
 */
export function BarTable({
    caption,
    rows,
    unit,
    max,
    headers = ["", "", ""],
    dense = false,
}: {
    caption: string;
    rows: Datum[];
    unit?: string;
    max?: number;
    headers?: [string, string, string];
    dense?: boolean;
}) {
    const ceiling = max ?? Math.max(1, ...rows.map((row) => row.value ?? 0));
    return (
        <table className={clsx("va-rank", dense && "is-dense")}>
            <caption className="sr-only">{caption}</caption>
            <thead>
                <tr>
                    <th scope="col">{headers[0] || <span className="sr-only">Row</span>}</th>
                    <th scope="col">{headers[1] || <span className="sr-only">Bar</span>}</th>
                    <th scope="col">{headers[2] || <span className="sr-only">Figure</span>}</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row) => (
                    <tr className={clsx(row.emphasis && "is-emphasis")} key={row.key}>
                        <th scope="row">
                            {row.href ? <a href={row.href}>{row.label}</a> : row.label}
                            {row.note ? <small>{row.note}</small> : null}
                        </th>
                        <td className="va-rank-track">
                            {row.value == null ? (
                                <span className="va-rank-absent">
                                    {row.absence ?? DEFAULT_ABSENCE}
                                </span>
                            ) : (
                                <span
                                    aria-hidden="true"
                                    className="va-rank-bar"
                                    style={{ width: barWidth(row.value, ceiling) }}
                                />
                            )}
                        </td>
                        <td className="va-rank-value">
                            {row.display ??
                                (row.value == null ? (
                                    <span className="va-rank-null">not established</span>
                                ) : (
                                    <>
                                        {count(row.value)}
                                        {unit ? <small> {unit}</small> : null}
                                    </>
                                ))}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

export type CorpusFigure = {
    value: number | null;
    /** Why there is no figure. Required whenever `value` is null. */
    absence?: string;
    href?: string;
};

/**
 * One property of the corpus, drawn across the four collections on one shared scale.
 *
 * The four always appear in traditional order and always all four, including the ones with
 * nothing to show. A small multiple that dropped its empty collections would make the reader
 * count to four themselves and get a different answer each time.
 */
export function CorpusStrip({
    caption,
    figures,
    unit,
    perThousand = false,
    max,
}: {
    caption: string;
    figures: Record<CorpusCode, CorpusFigure>;
    unit?: string;
    /** Formats values as rates rather than counts. */
    perThousand?: boolean;
    max?: number;
}) {
    const values = CORPORA.map(({ code }) => figures[code]?.value).filter(
        (value): value is number => typeof value === "number",
    );
    const ceiling = max ?? Math.max(1, ...values);
    return (
        <table className="va-strip">
            <caption className="sr-only">{caption}</caption>
            <tbody>
                {CORPORA.map(({ code, name }) => {
                    const figure = figures[code] ?? { value: null };
                    return (
                        <tr key={code}>
                            <th scope="row">
                                <abbr title={name}>{code}</abbr>
                                <span className="sr-only">{name}</span>
                            </th>
                            <td className="va-strip-track">
                                {figure.value == null ? (
                                    <span className="va-strip-absent">
                                        {figure.absence ?? DEFAULT_ABSENCE}
                                    </span>
                                ) : (
                                    <span
                                        aria-hidden="true"
                                        className="va-strip-bar"
                                        style={{ width: barWidth(figure.value, ceiling) }}
                                    />
                                )}
                            </td>
                            <td className="va-strip-value">
                                {figure.value == null ? (
                                    <span className="va-strip-null">—</span>
                                ) : (
                                    <>
                                        {perThousand ? rate(figure.value) : count(figure.value)}
                                        {unit ? <small> {unit}</small> : null}
                                    </>
                                )}
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

/**
 * One row of a small-multiple grid: a title, a definition, and the strip itself.
 *
 * The definition sits with the strip rather than in a legend somewhere else on the page,
 * because a row of this grid is the unit a reader actually looks at.
 */
export function SmallMultiple({
    title,
    definition,
    footnote,
    children,
}: {
    title: string;
    definition: string;
    footnote?: React.ReactNode;
    children: React.ReactNode;
}) {
    return (
        <section className="va-multiple">
            <header>
                <h3>{title}</h3>
                <p>{definition}</p>
            </header>
            <div className="va-multiple-figure">{children}</div>
            {footnote ? <p className="va-multiple-note">{footnote}</p> : null}
        </section>
    );
}

/**
 * A single bar split into the four collections' shares of one total.
 *
 * Shares, not counts, and the counts travel beside it in the row header — a segmented bar
 * whose segments are unlabelled counts is the chart form that most reliably gets misread.
 * Segments carry a hatch pattern that steps with the corpus order, so the four are separable
 * without colour.
 */
export function ShareStrip({
    label,
    total,
    shares,
}: {
    label: string;
    total: number;
    shares: Record<CorpusCode, number | null>;
}) {
    const present = CORPORA.filter(({ code }) => (shares[code] ?? 0) > 0);
    const sum = present.reduce((running, { code }) => running + (shares[code] ?? 0), 0) || 1;
    return (
        <div className="va-share">
            <div aria-hidden="true" className="va-share-track">
                {present.map(({ code }, index) => (
                    <span
                        className="va-share-segment"
                        data-corpus={code}
                        data-tone={index % 4}
                        key={code}
                        style={{ width: `${((shares[code] ?? 0) / sum) * 100}%` }}
                    />
                ))}
            </div>
            <p className="va-share-legend">
                <span className="sr-only">{label}: </span>
                {present.map(({ code, name }, index) => (
                    <span key={code}>
                        {index > 0 ? <span aria-hidden="true"> · </span> : null}
                        <abbr title={name}>{code}</abbr> {count(shares[code])}
                    </span>
                ))}
                {present.length < CORPORA.length ? (
                    <span className="va-share-absent">
                        {" "}
                        · not in{" "}
                        {CORPORA.filter(({ code }) => !(shares[code] ?? 0))
                            .map(({ code }) => code)
                            .join(", ")}
                    </span>
                ) : null}
                <span className="va-share-total"> · {count(total)} occurrences</span>
            </p>
        </div>
    );
}

/**
 * A figure printed at display size with its unit and its scope beneath it.
 *
 * Used sparingly and never in a row of four: a grid of these is a KPI tile set, which is the
 * thing this Lab is most at risk of becoming.
 */
export function Figure({
    value,
    unit,
    note,
}: {
    value: string;
    unit: string;
    note?: React.ReactNode;
}) {
    return (
        <p className="va-figure-number">
            <strong>{value}</strong>
            <span>{unit}</span>
            {note ? <small>{note}</small> : null}
        </p>
    );
}
