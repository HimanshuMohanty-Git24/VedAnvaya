"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { encoded } from "@/lib/api";

/**
 * The archive register: the one horizontal moving-text moment in the product.
 *
 * ## What it is
 *
 * A line of real canonical citations, one from each collection in turn, that travels
 * sideways as the reader scrolls past it and is perfectly still when they stop. Every entry
 * is a link to that verse. Nothing here is a sample, a placeholder or a word chosen for its
 * shape: the citations are read from `/passages/{key}/siblings` on one anchor per
 * collection, so what moves past is the archive's own numbering.
 *
 * ## What it is not
 *
 * **Not a marquee.** There is no timer, no loop and no autoplay anywhere in it. The motion
 * runs on a named view timeline declared on this section - the page's own scroll position
 * drives the animation's progress, so the register moves exactly as far as the reader moves
 * it and stops dead when they stop. `scripts/audit-motion.mjs` refuses an infinite animation
 * or a `setInterval` that writes a transform anywhere in this codebase, which is the gate
 * that keeps it from becoming one. The timeline is named rather than anonymous for a reason
 * that cost this register its motion for a release: see `thread.css`.
 *
 * **Not Sanskrit wallpaper.** Citations, not verses: an address a reader can act on rather
 * than a script used as texture.
 *
 * ## The one line of JavaScript in it
 *
 * How far the track may travel is a distance CSS cannot compute, so a ResizeObserver writes
 * one custom property and the keyframes read it. That is the whole of the script: no scroll
 * listener, no rAF, no animation driven from the main thread. Without it the keyframe would
 * animate to a guessed distance and either leave the last citation off the edge or stop
 * short with empty space.
 *
 * The distance is the smaller of two. The track's own overflow bounds it, so the register
 * never advances past its last citation. A share of the scroll the animation range covers
 * bounds it again, so a long register crosses at a readable rate instead of being dragged
 * through a screen's worth of scroll - see `thread.css` for the measurement that made that
 * second bound necessary.
 *
 * ## Without scroll-timeline support
 *
 * The track does not move, and the frame is a horizontally scrollable row the reader can
 * push by hand. Same content, same links, no polyfill.
 */

export type ArchiveEntry = {
    /** The collection this citation belongs to, named. */
    collection: string;
    /** The citation as the corpus writes it: "RV 1.1.2", "AVS 1.1.3". */
    citation: string;
    /** The canonical key, so the citation is a link and not a label. */
    passageKey: string;
};

/**
 * The share of the scroll the animation range covers that the register may travel across.
 *
 * `animation-range: entry 0% exit 100%` is the strip's whole passage through the viewport,
 * which is one viewport height plus the strip's own height of scrolling. At seven tenths of
 * that the register moves clearly - three or four citations cross the frame - while staying
 * under one lateral pixel per pixel the reader scrolls, so the row reads at the rate it is
 * moving. Above one it becomes a blur, which is a ticker with the timer taken out.
 */
const REGISTER_TRAVEL_SHARE = 0.7;

export function ArchiveStrip({ entries }: { entries: ArchiveEntry[] }) {
    const scopeRef = useRef<HTMLElement>(null);
    const frameRef = useRef<HTMLDivElement>(null);
    const trackRef = useRef<HTMLOListElement>(null);

    useEffect(() => {
        const scope = scopeRef.current;
        const frame = frameRef.current;
        const track = trackRef.current;
        if (!scope || !frame || !track) return;

        const measure = () => {
            /* The frame's own overflow, which is the true distance it can be hand-scrolled -
               the track's width alone ignores the frame's start padding and overstates it. */
            const overflow = Math.max(0, frame.scrollWidth - frame.clientWidth);
            const range = window.innerHeight + scope.getBoundingClientRect().height;
            const travel = Math.min(overflow, range * REGISTER_TRAVEL_SHARE);
            track.style.setProperty("--va-register-travel", `${Math.round(travel)}px`);
        };
        measure();
        /* Both boxes: the frame changes with the viewport and the track changes when its
           fonts land, and a distance measured before the display face has loaded is the
           fallback face's distance. The window listener is for the other half of the bound:
           a viewport that changes height alone resizes neither box. */
        const observer = new ResizeObserver(measure);
        observer.observe(frame);
        observer.observe(track);
        window.addEventListener("resize", measure);
        return () => {
            observer.disconnect();
            window.removeEventListener("resize", measure);
        };
    }, [entries.length]);

    if (entries.length === 0) return null;

    return (
        <section
            aria-labelledby="va-archive-strip-heading"
            className="va-archive-strip va-register-scope"
            ref={scopeRef}
        >
            <div className="va-archive-strip-head">
                <h2 id="va-archive-strip-heading">Every verse has an address.</h2>
                <p>
                    Canonical citations, read from the corpus. Each one opens the verse it names.
                </p>
            </div>
            <div className="va-archive-frame" ref={frameRef}>
                <ol className="va-register-track" ref={trackRef}>
                    {entries.map((entry) => (
                        <li key={entry.passageKey}>
                            <Link href={`/passage/${encoded(entry.passageKey)}`}>
                                <span className="va-archive-collection">{entry.collection}</span>
                                <span className="va-archive-citation">{entry.citation}</span>
                            </Link>
                        </li>
                    ))}
                </ol>
            </div>
        </section>
    );
}
