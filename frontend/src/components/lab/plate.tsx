import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import type { Plate } from "@/lib/lab";

/**
 * The chrome every plate wears.
 *
 * A plate is laid out as a museum object rather than as a dashboard card: the object's name
 * and the question it answers at the top, the figure in the middle given the full measure,
 * and the wall label beneath it. The label is not an afterthought and not a collapsed
 * disclosure — it states what is measured, what a mark is, what is in scope, what is out, and
 * what the reader must not conclude, and it is set at reading size because a caveat nobody
 * reads is decoration.
 *
 * All of this renders on the server. The Lab ships no client JavaScript of its own: every
 * control is a link, every hover is CSS, and every expandable is a `<details>`.
 */

export function PlateHeader({ plate, lede }: { plate: Plate; lede: string }) {
    return (
        <header className="va-plate-head">
            <Link className="va-plate-back" href="/visualizations">
                <ArrowLeft size={15} aria-hidden="true" />
                All plates
            </Link>
            <p className="va-plate-lens">{plate.lens}</p>
            <h1>{plate.title}</h1>
            <p className="va-plate-question">{plate.question}</p>
            <p className="va-plate-lede">{lede}</p>
        </header>
    );
}

/**
 * One figure and its caption.
 *
 * `title` is rendered as a real heading and referenced by `aria-labelledby`, so the figure is
 * announced by name rather than as "figure". `description` is the text alternative the brief
 * requires for a chart: it says in words what the marks say in space, and it is visible rather
 * than hidden, because a sighted reader benefits from it just as much.
 */
export function PlateFigure({
    id,
    title,
    description,
    footnote,
    children,
}: {
    id: string;
    title: string;
    description: string;
    footnote?: React.ReactNode;
    children: React.ReactNode;
}) {
    return (
        <figure aria-labelledby={`${id}-title`} className="va-figure" id={id}>
            <figcaption>
                <h2 id={`${id}-title`}>{title}</h2>
                <p>{description}</p>
            </figcaption>
            <div className="va-figure-body">{children}</div>
            {footnote ? <p className="va-figure-note">{footnote}</p> : null}
        </figure>
    );
}

/** The wall label: the five questions of the visualization standard, answered. */
export function PlateLabel({ plate }: { plate: Plate }) {
    const rows: [string, string][] = [
        ["What is measured", plate.label.measures],
        ["What one mark is", plate.label.mark],
        ["What is in scope", plate.label.scope],
        ["What is excluded", plate.label.excluded],
        ["What this does not show", plate.label.notInfer],
    ];
    return (
        <section aria-labelledby="va-plate-label-title" className="va-plate-label">
            <h2 id="va-plate-label-title">How to read this plate</h2>
            <dl>
                {rows.map(([term, description]) => (
                    <div key={term}>
                        <dt>{term}</dt>
                        <dd>{description}</dd>
                    </div>
                ))}
            </dl>
            <p className="va-plate-reads">
                <span>Reads</span> {plate.reads}
            </p>
        </section>
    );
}

/**
 * The one sentence a reader should leave with.
 *
 * Marked as an observation and never as a conclusion. Where a plate supports a reading beyond
 * the count, that reading goes in `interpretation` and is framed as one interpretation rather
 * than as a finding, because corpus frequency is not historical causation and the difference
 * has to survive being skim-read.
 */
export function PlateTakeaway({
    observation,
    interpretation,
}: {
    observation: React.ReactNode;
    interpretation?: React.ReactNode;
}) {
    return (
        <section className="va-plate-takeaway">
            <div className="va-takeaway-block" data-knowledge-kind="derived-metric">
                <p className="va-takeaway-tag">What the figures show</p>
                <p className="va-takeaway-body">{observation}</p>
            </div>
            {interpretation ? (
                <div className="va-takeaway-block" data-knowledge-kind="interpretation">
                    <p className="va-takeaway-tag">One way to read it</p>
                    <p className="va-takeaway-body">{interpretation}</p>
                </div>
            ) : null}
        </section>
    );
}

/** Where the plate lets go of the reader. Never fewer than two routes onward. */
export function PlateHandoff({
    title = "Follow this further",
    links,
}: {
    title?: string;
    links: { href: string; label: string; note: string }[];
}) {
    return (
        <nav aria-label={title} className="va-plate-handoff">
            <h2>{title}</h2>
            <ul>
                {links.map((link) => (
                    <li key={link.href}>
                        <Link href={link.href}>
                            <strong>{link.label}</strong>
                            <span>{link.note}</span>
                            <ArrowUpRight aria-hidden="true" size={15} />
                        </Link>
                    </li>
                ))}
            </ul>
        </nav>
    );
}
