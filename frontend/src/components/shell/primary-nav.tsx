"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PRIMARY_NAV } from "../navigation";

/**
 * The desktop navigation.
 *
 * The active state is a rubricated segment of the header's own bottom rule rather than a
 * pill, a box or a floating underline. In a Sanskrit codex red is functional: it marks
 * headings, section divisions and the dandas that end a verse. Marking the reader's place in
 * the corpus by reddening that stretch of the rule is the same gesture, and it is the one
 * piece of ornament here that carries information.
 *
 * It also solves a real problem quietly. A pill needs a background, a radius and a padding
 * that all have to survive dark mode and a long label; a segment of an existing line needs
 * none of those and cannot collide with its neighbours.
 *
 * Hover draws the same segment in ink at low opacity, so the mechanism is legible before it
 * is used rather than appearing from nowhere on click.
 */
export function PrimaryNav() {
    const pathname = usePathname();

    return (
        <nav className="va-nav" aria-label="Primary">
            {PRIMARY_NAV.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                    <Link
                        className="va-nav-link"
                        href={item.href}
                        key={item.href}
                        aria-current={active ? "page" : undefined}
                    >
                        {item.label}
                    </Link>
                );
            })}
        </nav>
    );
}
