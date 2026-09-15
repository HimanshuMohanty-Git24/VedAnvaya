import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ReactNode } from "react";
import { Thread } from "../brand/thread";

/**
 * The homepage's shared furniture.
 *
 * Small on purpose. The page's job is to look composed rather than assembled, and the way
 * that goes wrong is a kit of section wrappers rich enough that every section reaches for
 * the same three. What is shared here is the things that genuinely must not drift between
 * sections: the measure, the heading scale, the kicker, and the one call-to-action form.
 */

export function Section({
    children,
    className,
    id,
    tone = "paper",
}: {
    children: ReactNode;
    className?: string;
    id?: string;
    /** `paper` is the page. `sunk` is one step down, for sections that want separating. */
    tone?: "paper" | "sunk" | "carbon";
}) {
    return (
        /*
         * The page width lives on an inner element, not on the section's children.
         *
         * Putting `width: page; margin-inline: auto` on every direct child looked like the
         * same thing and was not: any child that then set its own max-width, which is every
         * heading and every prose block, got centred on the page instead of aligned to it.
         * The result was headings floating in the middle of sections whose tables and bars
         * ran the full measure. One container, children aligned to its start.
         */
        <section
            className={["va-section", `is-${tone}`, className].filter(Boolean).join(" ")}
            id={id}
        >
            <div className="va-section-inner">{children}</div>
        </section>
    );
}

/**
 * The uppercase micro-label above a heading.
 *
 * Rationed hard: three on the whole page, against ten sections. The reason is that an
 * eyebrow over every section produces an identical rhythm down the page, which is the single
 * most recognisable signature of a generated layout. Where one is used here it names the
 * thing on screen in the tradition's own word, which is a reason to exist rather than a
 * decoration.
 */
export function Kicker({ sanskrit, children }: { sanskrit?: string; children: ReactNode }) {
    return (
        <p className="va-kicker">
            {sanskrit ? (
                <span className="va-deva-label" lang="sa">
                    {sanskrit}
                </span>
            ) : null}
            <span>{children}</span>
        </p>
    );
}

export function Heading({
    children,
    lede,
    level = 2,
}: {
    children: ReactNode;
    lede?: ReactNode;
    level?: 2 | 3;
}) {
    const Tag = level === 2 ? "h2" : "h3";
    return (
        <div className="va-heading">
            <Tag className="va-heading-title">{children}</Tag>
            {lede ? <p className="va-heading-lede">{lede}</p> : null}
        </div>
    );
}

/**
 * The one call-to-action form on the page.
 *
 * A ruled line with an arrow, not a filled pill. Two reasons. A page with ten sections and a
 * filled button in each reads as ten competing offers, and the filled pill is the single
 * most generic object in contemporary interface design. The hero keeps one solid button, so
 * that the primary action is the only thing on the page shaped like a button, and everything
 * else is a link that behaves like a link.
 */
export function Action({
    href,
    children,
    note,
    prefetch,
}: {
    href: string;
    children: ReactNode;
    note?: string;
    prefetch?: boolean;
}) {
    return (
        <Link className="va-action" href={href} prefetch={prefetch}>
            <span className="va-action-label">{children}</span>
            <ArrowRight aria-hidden="true" size={15} weight="bold" />
            {note ? <span className="va-action-note">{note}</span> : null}
        </Link>
    );
}

/** The Anvaya Thread, as a rule between two sections that would otherwise butt together. */
export function SectionRule() {
    return (
        <div className="va-section-rule" role="presentation">
            <Thread size={18} />
        </div>
    );
}
