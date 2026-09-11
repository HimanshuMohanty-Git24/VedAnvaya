import { MagnifyingGlass } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { MobileNav } from "./mobile-nav";
import { NavLinks } from "./nav-links";
import { ThemeToggle } from "./theme-toggle";

export function SiteHeader() {
    return (
        <header className="site-header">
            <div className="shell header-inner">
                <Link className="brand" href="/" aria-label="VedaGraph, home">
                    <span className="brand-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24" width="20" height="20" role="presentation">
                            <circle cx="12" cy="5" r="2.6" fill="currentColor" />
                            <circle cx="5" cy="17" r="2.2" fill="currentColor" opacity="0.72" />
                            <circle cx="19" cy="17" r="2.2" fill="currentColor" opacity="0.72" />
                            <path
                                d="M12 7.6 5.6 15M12 7.6 18.4 15M6.8 17.6h10.4"
                                stroke="currentColor"
                                strokeWidth="1.3"
                                fill="none"
                                opacity="0.62"
                            />
                        </svg>
                    </span>
                    <span>VedaGraph</span>
                </Link>
                <NavLinks />
                <div className="header-actions">
                    <Link className="search-action" href="/search">
                        <MagnifyingGlass size={17} aria-hidden="true" />
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
