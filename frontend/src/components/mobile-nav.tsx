"use client";

import { List, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { PRIMARY_NAV, SECONDARY_NAV } from "./navigation";

export function MobileNav() {
    return (
        <Dialog.Root>
            <Dialog.Trigger asChild>
                <button
                    className="icon-button mobile-nav-trigger"
                    type="button"
                    aria-label="Open navigation"
                >
                    <List size={21} aria-hidden="true" />
                </button>
            </Dialog.Trigger>
            <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content className="mobile-nav-panel">
                    <div className="mobile-nav-top">
                        <Dialog.Title>Explore VedaGraph</Dialog.Title>
                        <Dialog.Close className="icon-button" aria-label="Close navigation">
                            <X size={20} aria-hidden="true" />
                        </Dialog.Close>
                    </div>
                    <nav aria-label="Mobile" className="mobile-nav-links">
                        <Dialog.Close asChild>
                            <Link href="/search">
                                <strong>Search</strong>
                                <small>Text, citations and every registered entity</small>
                            </Link>
                        </Dialog.Close>
                        {[...PRIMARY_NAV, ...SECONDARY_NAV].map((item) => (
                            <Dialog.Close asChild key={item.href}>
                                <Link href={item.href}>
                                    <strong>{item.label}</strong>
                                    <small>{item.description}</small>
                                </Link>
                            </Dialog.Close>
                        ))}
                    </nav>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
