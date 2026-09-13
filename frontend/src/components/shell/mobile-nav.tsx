"use client";

import { List, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Thread } from "../brand/thread";
import { PRIMARY_NAV, SECONDARY_NAV } from "../navigation";

/**
 * The small-screen navigation.
 *
 * A full-height sheet rather than a shrunken copy of the bar. Every route gets its label and
 * its one-line description, because on a phone the reader has the room for it and no hover
 * to discover it with, and because the descriptions are the only place the product explains
 * what "Connections" means before you have opened it.
 *
 * Search leads. It is the first row rather than a control in the header, since at this width
 * the header has surrendered everything except the mark and this trigger.
 */
export function MobileNav() {
    const pathname = usePathname();
    const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

    return (
        <Dialog.Root>
            <Dialog.Trigger asChild>
                <button className="va-icon-button va-mobile-trigger" type="button" aria-label="Open navigation">
                    <List aria-hidden="true" size={21} />
                </button>
            </Dialog.Trigger>
            <Dialog.Portal>
                <Dialog.Overlay className="va-sheet-scrim" />
                <Dialog.Content className="va-sheet" aria-describedby={undefined}>
                    <div className="va-sheet-head">
                        <Dialog.Title className="va-sheet-title">Go to</Dialog.Title>
                        <Dialog.Close className="va-icon-button" aria-label="Close navigation">
                            <X aria-hidden="true" size={20} />
                        </Dialog.Close>
                    </div>

                    <nav aria-label="Site" className="va-sheet-nav">
                        <Dialog.Close asChild>
                            <Link className="va-sheet-link" href="/search">
                                <span className="va-sheet-link-label">Search</span>
                                <span className="va-sheet-link-note">
                                    Sanskrit, transliteration, citations and every named thing
                                </span>
                            </Link>
                        </Dialog.Close>

                        {PRIMARY_NAV.map((item) => (
                            <Dialog.Close asChild key={item.href}>
                                <Link
                                    aria-current={isActive(item.href) ? "page" : undefined}
                                    className="va-sheet-link"
                                    href={item.href}
                                >
                                    <span className="va-sheet-link-label">{item.label}</span>
                                    <span className="va-sheet-link-note">{item.description}</span>
                                </Link>
                            </Dialog.Close>
                        ))}

                        <Thread className="va-sheet-thread" size={16} />

                        {SECONDARY_NAV.map((item) => (
                            <Dialog.Close asChild key={item.href}>
                                <Link
                                    aria-current={isActive(item.href) ? "page" : undefined}
                                    className="va-sheet-link is-secondary"
                                    href={item.href}
                                >
                                    <span className="va-sheet-link-label">{item.label}</span>
                                    <span className="va-sheet-link-note">{item.description}</span>
                                </Link>
                            </Dialog.Close>
                        ))}
                    </nav>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
