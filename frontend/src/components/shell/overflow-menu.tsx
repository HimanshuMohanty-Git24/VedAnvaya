"use client";

import { CaretDown } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { SECONDARY_NAV } from "../navigation";

/**
 * The overflow menu, holding the six surfaces that are destinations rather than daily routes.
 *
 * Written by hand rather than pulled from a menu library. It needs four behaviours: open on
 * click, close on Escape, close on a pointer outside, and return focus to the trigger. That
 * is about thirty lines, against a dependency whose remaining value would be typeahead and
 * roving focus that a six-item list does not need.
 *
 * It is a disclosure, not a `role="menu"`. A menu makes screen readers announce "menu item"
 * and swallows arrow keys, which is right for commands and wrong for links: these are six
 * ordinary links and Tab should walk them.
 */
export function OverflowMenu() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);
    const wrapper = useRef<HTMLDivElement>(null);
    const trigger = useRef<HTMLButtonElement>(null);
    const panelId = useId();

    const activeHere = SECONDARY_NAV.some(
        (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
    );

    /*
     * Close whenever the route changes, so following a link inside the panel does not leave
     * it hanging open over the page it just navigated to. It also covers the browser's back
     * and forward buttons, which a close-on-click handler would not.
     *
     * Adjusted during render rather than in an effect. React supports this for exactly this
     * case and re-renders before touching the DOM, so the panel never paints in the wrong
     * state; setting it in an effect would paint it open for one frame and then close it.
     */
    const [lastPath, setLastPath] = useState(pathname);
    if (pathname !== lastPath) {
        setLastPath(pathname);
        setOpen(false);
    }

    useEffect(() => {
        if (!open) return;

        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== "Escape") return;
            setOpen(false);
            /* Escape has to hand focus back, or it lands on <body> and the next Tab starts
               the page again from the top. */
            trigger.current?.focus();
        };
        /* pointerdown rather than click: a click listener fires after the browser has already
           moved focus, which reopens the panel when the trigger itself is what was pressed. */
        const onPointerDown = (event: PointerEvent) => {
            if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
        };

        document.addEventListener("keydown", onKeyDown);
        document.addEventListener("pointerdown", onPointerDown);
        return () => {
            document.removeEventListener("keydown", onKeyDown);
            document.removeEventListener("pointerdown", onPointerDown);
        };
    }, [open]);

    return (
        <div className="va-overflow" ref={wrapper}>
            <button
                aria-controls={panelId}
                aria-current={activeHere && !open ? "page" : undefined}
                aria-expanded={open}
                className="va-nav-link va-overflow-trigger"
                onClick={() => setOpen((value) => !value)}
                ref={trigger}
                type="button"
            >
                More
                <CaretDown aria-hidden="true" size={12} weight="bold" />
            </button>
            {open ? (
                <div className="va-overflow-panel" id={panelId}>
                    {SECONDARY_NAV.map((item) => {
                        const active =
                            pathname === item.href || pathname.startsWith(`${item.href}/`);
                        return (
                            <Link
                                aria-current={active ? "page" : undefined}
                                className="va-overflow-link"
                                href={item.href}
                                key={item.href}
                            >
                                <span className="va-overflow-label">{item.label}</span>
                                <span className="va-overflow-note">{item.description}</span>
                            </Link>
                        );
                    })}
                </div>
            ) : null}
        </div>
    );
}
