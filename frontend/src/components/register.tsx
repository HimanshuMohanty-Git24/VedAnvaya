import clsx from "clsx";
import Link from "next/link";

/**
 * The register: one component for every list of things this product holds.
 *
 * Five routes each built their own card grid, and each got a slightly different answer to
 * the same four questions - what is this called, what is it, how much of it is there, and
 * what is the count over. This is the one answer, and it is the dialect the deity index and
 * the Vedas page already used: ruled rows, ranged metadata, no containers.
 *
 * Two rules it enforces that a card grid could not:
 *
 *   A figure never appears without its unit. `figure` and `unit` travel together, and a row
 *   with no figure prints the *kind* of absence rather than a blank cell or a dash.
 *
 *   A measure bar is drawn only against a stated ceiling. `ceiling` is the largest figure in
 *   the register, computed once by the caller from the rows it is actually showing, so a bar
 *   is a share of something the reader can see rather than of an unstated maximum.
 */

export type RegisterRow = {
    key: string;
    href: string;
    /** The name, in the reading face. */
    name: string;
    /** Set the name in the Sanskrit face: a romanised or Devanagari label. */
    script?: "IAST" | "DEVANAGARI";
    /** A second form beside the name, not under it. */
    alt?: string | null;
    /** What kind of thing this is, if the register mixes kinds. */
    kind?: string | null;
    /** The sentence. Clamped to three lines by the stylesheet. */
    gloss?: string | null;
    /** A second, quieter line: how a row was established, what its figure excludes. */
    note?: React.ReactNode;
    /** The ranged figure. Null draws `absent` instead, never a dash. */
    figure?: number | null;
    /** What the figure counts. Always printed with it. */
    unit?: string | null;
    /**
     * What kind of absence this is, when `figure` is null.
     *
     * Required rather than defaulted, because the four absences this corpus distinguishes -
     * measured zero, no lexical match, never measured, not a relation that can hold - are
     * different claims, and a component that picked one for the caller would be asserting
     * something it cannot know.
     */
    absent?: string | null;
};

export function Register({
    rows,
    ceiling,
    columns,
    "aria-label": ariaLabel,
}: {
    rows: RegisterRow[];
    /**
     * The largest figure in this register, if a measure rule should be drawn.
     *
     * Omitted where no trustworthy count exists. The formula index is the binding case: its
     * `passage_count` is null on every family, so it gets no bars at all rather than bars
     * drawn against a ceiling of one.
     */
    ceiling?: number | null;
    /**
     * Column heads, printed once above the register.
     *
     * Where every row's unit is the same word - "matching mantras" on twenty afflictions,
     * "verses name it" on twenty-five rites - printing it per row is the heading repeated
     * twenty times in the right margin. Passing `columns` moves it to a rule at the top,
     * which is what a catalogue does, and the rows then omit their own unit.
     *
     * The row's own unit is still rendered either way, and only *visually* hidden where the
     * head is on screen to carry it. Below 62rem the head is `display: none`, so the row's
     * unit is what a reader sees; above it, the head is.
     */
    columns?: { name: string; figure: string };
    "aria-label"?: string;
}) {
    return (
        <ul
            aria-label={ariaLabel}
            className={clsx("va-register", columns && "has-columns")}
        >
            {columns && (
                <li aria-hidden="true" className="va-register-head">
                    <span>{columns.name}</span>
                    <span />
                    <span>{columns.figure}</span>
                </li>
            )}
            {rows.map((row) => (
                <li key={row.key}>
                    <Link className="va-register-row" href={row.href}>
                        <span className="va-register-lead">
                            <span
                                className={clsx(
                                    "va-register-name",
                                    row.script && "va-sanskrit-inline",
                                )}
                                data-script={row.script}
                                lang={row.script ? "sa" : undefined}
                            >
                                {row.name}
                            </span>
                            {row.alt && (
                                <span className="va-register-alt" lang="sa">
                                    {row.alt}
                                </span>
                            )}
                            {row.kind && <span className="va-register-kind">{row.kind}</span>}
                        </span>

                        <span className="va-register-gloss-wrap">
                            {row.gloss && <span className="va-register-gloss">{row.gloss}</span>}
                            {row.note && <span className="va-register-note">{row.note}</span>}
                        </span>

                        <span className="va-register-meta">
                            {row.figure == null ? (
                                <span className="va-register-absent">
                                    {row.absent ?? "not established"}
                                </span>
                            ) : (
                                <>
                                    <span className="va-register-figure">
                                        {row.figure.toLocaleString("en-GB")}
                                    </span>
                                    {/*
                                     * The unit is never dropped, and it is only ever
                                     * *visually* deduplicated.
                                     *
                                     * It is always in the DOM, so it is always in the row's
                                     * accessible name: a figure read out as "89" with no
                                     * unit is the kind of bare number this product prints
                                     * nowhere else. The stylesheet hides it per row only
                                     * where the column head is actually on screen, which is
                                     * 62rem and up - below that the head is `display: none`
                                     * and the unit has to be here or it is nowhere. An
                                     * earlier version keyed the hiding on `columns` in
                                     * JavaScript and produced exactly that: a mobile
                                     * register of rites whose smallest rows read "0".
                                     */}
                                    {row.unit && (
                                        <span className="va-register-unit">{row.unit}</span>
                                    )}
                                    {ceiling != null && ceiling > 0 && (
                                        /*
                                         * Hidden from assistive technology on purpose. The
                                         * figure above it is the same fact in words, and a
                                         * screen reader announcing "0.42 of the maximum"
                                         * after "839 verses name it" is noise.
                                         */
                                        <span aria-hidden="true" className="va-register-measure">
                                            <span
                                                className="va-resolve"
                                                style={
                                                    {
                                                        "--va-resolve-to": `${Math.max(
                                                            2,
                                                            Math.round(
                                                                (row.figure / ceiling) * 100,
                                                            ),
                                                        )}%`,
                                                    } as React.CSSProperties
                                                }
                                            />
                                        </span>
                                    )}
                                </>
                            )}
                        </span>
                    </Link>
                </li>
            ))}
        </ul>
    );
}

/**
 * The register's opening: a title, one sentence, and what is standing in the list.
 *
 * Replaces the shared `PageHeading` on the index routes. The difference is the standing
 * strip: a reader arriving at an index wants its size and its scope before its first row,
 * and that is measured rather than decorative - which is exactly what the uppercase eyebrow
 * it displaces was not.
 */
export function RegisterOpening({
    title,
    lede,
    standing,
    children,
}: {
    title: string;
    lede?: string | null;
    standing?: Array<{ label: string; value: React.ReactNode; absent?: boolean }>;
    children?: React.ReactNode;
}) {
    return (
        <header className="va-open">
            <h1>{title}</h1>
            {lede && <p className="va-open-lede">{lede}</p>}
            {standing && standing.length > 0 && (
                <dl className="va-open-standing">
                    {standing.map((item) => (
                        <div key={item.label}>
                            <dt>{item.label}</dt>
                            <dd className={clsx(item.absent && "is-absent")}>{item.value}</dd>
                        </div>
                    ))}
                </dl>
            )}
            {children}
        </header>
    );
}
