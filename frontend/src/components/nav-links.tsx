"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PRIMARY_NAV } from "./navigation";

export function NavLinks() {
    const pathname = usePathname();
    return (
        <nav className="desktop-nav" aria-label="Primary">
            {PRIMARY_NAV.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                    <Link
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
