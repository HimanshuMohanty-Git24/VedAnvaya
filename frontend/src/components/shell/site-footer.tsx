import Link from "next/link";
import { Wordmark } from "../brand/wordmark";
import { Thread } from "../brand/thread";

/**
 * The site footer.
 *
 * Quiet by instruction and by function: it is the last thing on a reading page and should
 * read as the bottom margin of a folio, not as a second navigation.
 *
 * The one editorial decision here is that Limits holds the first link in the first column.
 * It is the page the product is least entitled to bury, since every figure on every surface
 * is only true inside it.
 *
 * There is no copyright line. The texts are ancient and the translations held here are in
 * the public domain, so asserting copyright over the page would be asserting something about
 * the material that is not true. What belongs there instead is the acknowledgement, which
 * lives on its own page.
 */

const COLUMNS: { heading: string; links: { href: string; label: string }[] }[] = [
    {
        heading: "Read",
        links: [
            { href: "/vedas", label: "The four Samhitas" },
            { href: "/search", label: "Search the corpus" },
            { href: "/explore", label: "Explore" },
            { href: "/connections", label: "Connections" },
        ],
    },
    {
        heading: "Follow",
        links: [
            { href: "/graph", label: "Knowledge graph" },
            { href: "/visualizations", label: "Visualizations" },
            { href: "/devatas", label: "Deities" },
            { href: "/entities", label: "Entities" },
            { href: "/ask", label: "Ask VedAnvaya" },
        ],
    },
    {
        heading: "Check",
        links: [
            { href: "/limits", label: "What is not held" },
            { href: "/sources", label: "Sources and method" },
            { href: "/insights", label: "Evidence and interpretation" },
            { href: "/about", label: "About the project" },
        ],
    },
];

export function SiteFooter() {
    return (
        <footer className="va-footer">
            <Thread className="va-footer-thread" size={18} />
            <div className="va-footer-inner">
                <div className="va-footer-brand">
                    <Wordmark tagline />
                    <p>
                        Every figure on this site describes what this build holds. None of them
                        describes what the Vedas contain.
                    </p>
                </div>

                {COLUMNS.map((column) => (
                    <nav aria-label={column.heading} className="va-footer-column" key={column.heading}>
                        <h2 className="va-footer-heading">{column.heading}</h2>
                        {column.links.map((link) => (
                            <Link href={link.href} key={link.href}>
                                {link.label}
                            </Link>
                        ))}
                    </nav>
                ))}
            </div>
            <p className="va-footer-close">Ancient knowledge. New connections.</p>
        </footer>
    );
}
