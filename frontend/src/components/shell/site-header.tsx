import { MagnifyingGlass } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { Wordmark } from "../brand/wordmark";
import { MobileNav } from "./mobile-nav";
import { OverflowMenu } from "./overflow-menu";
import { PrimaryNav } from "./primary-nav";
import { ThemeToggle } from "../theme-toggle";

/**
 * The site header.
 *
 * Three zones on one 64px line: the mark, the routes, the instruments. It stays a single
 * line at every width down to the point where the routes move into the drawer, because a
 * header that wraps to two lines at 1024px is a header that was designed at 1440 and never
 * looked at again.
 *
 * Search keeps its own affordance rather than becoming a nav item. It is the only control
 * here that takes input, it carries a keyboard shortcut, and folding it into the route list
 * would make the one thing a reader reaches for repeatedly look like the five things they
 * reach for occasionally.
 */
export function SiteHeader() {
    return (
        <header className="va-header">
            <div className="va-header-inner">
                <Link className="va-header-brand" href="/" aria-label="VedAnvaya, home">
                    <Wordmark />
                </Link>

                <div className="va-header-routes">
                    <PrimaryNav />
                    <OverflowMenu />
                </div>

                <div className="va-header-tools">
                    <Link className="va-header-search" href="/search">
                        <MagnifyingGlass aria-hidden="true" size={16} />
                        <span>Search</span>
                        <kbd aria-hidden="true">/</kbd>
                    </Link>
                    <ThemeToggle />
                    <MobileNav />
                </div>
            </div>
        </header>
    );
}
