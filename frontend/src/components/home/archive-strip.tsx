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
 * is `animation-timeline: view()` - the page's own scroll position drives the animation's
 * progress, so the register moves exactly as far as the reader moves it and stops dead when
 * they stop. `scripts/audit-motion.mjs` refuses an infinite animation or a `setInterval`
 * that writes a transform anywhere in this codebase, which is the gate that keeps it from
 * becoming one.
 *
 * **Not Sanskrit wallpaper.** Citations, not verses: an address a reader can act on rather
 * than a script used as texture.
 *
 * ## The one line of JavaScript in it
 *
 * How far the track may travel is `scrollWidth - clientWidth`, and CSS cannot compute that.
 * So a ResizeObserver writes one custom property and the keyframes read it. That is the
 * whole of the script: no scroll listener, no rAF, no animation driven from the main
 * thread. Without it the keyframe would animate to a guessed distance and either leave the
 * last citation off the edge or stop short with empty space.
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

export function ArchiveStrip({ entries }: { entries: ArchiveEntry[] }) {
    const frameRef = useRef<HTMLDivElement>(null);
    const trackRef = useRef<HTMLOListElement>(null);

    useEffect(() => {
        const frame = frameRef.current;
        const track = trackRef.current;
        if (!frame || !track) return;

        const measure = () => {
            const travel = Math.max(0, track.scrollWidth - frame.clientWidth);
            track.style.setProperty("--va-register-travel", `${Math.round(travel)}px`);
        };
        measure();
        /* Both boxes: the frame changes with the viewport and the track changes when its
           fonts land, and a distance measured before the display face has loaded is the
           fallback face's distance. */
        const observer = new ResizeObserver(measure);
        observer.observe(frame);
        observer.observe(track);
        return () => observer.disconnect();
    }, [entries.length]);

    if (entries.length === 0) return null;

    return (
        <section aria-labelledby="va-archive-strip-heading" className="va-archive-strip">
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
