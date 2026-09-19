"use client";

import { useId } from "react";
import type { AccentTraceResult } from "@/lib/accent-trace";

/**
 * The Accent Trace, drawn.
 *
 * The line language is the Vedic Cadence's, the brand's own drawing of accentuation, and it
 * is kept exactly: a turn is two mirrored cubics through an apex, with the outer handle
 * pulled past the halfway point (0.55 against 0.45) so the line leaves the baseline
 * gradually and arrives at the apex steeply. That is how a pitch contour moves and is not
 * how a sine wave moves. The fractions are measured off `Vedic Cadence.png`.
 *
 * What is different is where the turns come from, and it is the whole change. The brand mark
 * drew a fixed house pattern of seven turns - the same drawing on all 17,780 recordings, a
 * picture of a verse and never of the verse. This draws the accent marks printed in the
 * verse on screen, one turn each, derived in `lib/accent-trace.ts`. A decorative waveform on
 * an audio player says "here is sound" and asserts a shape the data does not have; this says
 * "here is where this edition printed its accents", which is true, checkable and about the
 * text the reader is reading.
 *
 * The brand component it replaces is gone rather than kept beside it. A notation with its
 * content hard-coded can only ever be decoration - its own file said so - and a second
 * contour drawer that nothing renders is dead weight of exactly the kind this phase is
 * removing.
 *
 * ## The playhead
 *
 * `progress` is `currentTime / duration` from the audio element. Everything before it is
 * drawn at full weight and everything after at a third. This is ADVANCE in the motion law:
 * a marker moving along a track that already exists, driven by a real value, with no timer.
 *
 * It does NOT claim alignment. The horizontal axis is position in the text and the playhead
 * is position in the recording, and the trace never highlights a syllable, a word or a turn
 * as "the one being sung". The two axes run the same direction and that is all the drawing
 * says. The disclosure beside it says so in words.
 */

const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 56;
const BASELINE = 28;

/** Apex distance from the baseline. Negative is up, because SVG y grows down. */
const AMPLITUDE = 15;

/** Half a turn's footprint, in viewBox units. Wide enough to read, narrow enough to fit. */
const WIDTH = 13;

const round = (value: number) => Math.round(value * 10) / 10;

/**
 * The path.
 *
 * One pass along the baseline, bending through each turn in order. Turns closer together
 * than their own footprint are drawn where they fall and are allowed to overlap: a run of
 * marked syllables is a dense run in the text and the line should look dense there.
 */
function contour(turns: AccentTraceResult["turns"]): string {
    const parts = [`M0 ${BASELINE}`];
    let cursor = 0;

    for (const turn of turns) {
        const centre = turn.at * VIEW_WIDTH;
        const start = Math.max(0, centre - WIDTH);
        const end = Math.min(VIEW_WIDTH, centre + WIDTH);
        const apex = round(BASELINE + (turn.placement === "above" ? -AMPLITUDE : AMPLITUDE));

        if (start > cursor) parts.push(`L${round(start)} ${BASELINE}`);
        parts.push(
            `C${round(centre - WIDTH * 0.45)} ${BASELINE}` +
                ` ${round(centre - WIDTH * 0.55)} ${apex} ${round(centre)} ${apex}`,
        );
        parts.push(
            `C${round(centre + WIDTH * 0.55)} ${apex}` +
                ` ${round(centre + WIDTH * 0.45)} ${BASELINE} ${round(end)} ${BASELINE}`,
        );
        cursor = end;
    }

    if (cursor < VIEW_WIDTH) parts.push(`L${VIEW_WIDTH} ${BASELINE}`);
    return parts.join("");
}

export function AccentTrace({
    trace,
    progress = 0,
    className,
}: {
    trace: AccentTraceResult;
    /** `currentTime / duration`. 0 before playback. */
    progress?: number;
    className?: string;
}) {
    /* Two players on one page would otherwise share a clipPath id and clip each other. */
    const uid = useId().replace(/:/g, "");
    const clamped = Math.min(1, Math.max(0, progress));
    const cut = round(clamped * VIEW_WIDTH);
    const d = contour(trace.turns);

    return (
        <svg
            className={className}
            viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
            fill="none"
            /* Stretched to the player's width; the stroke is held to a true weight below. */
            preserveAspectRatio="none"
            aria-hidden="true"
        >
            <defs>
                <clipPath id={`${uid}-played`}>
                    <rect x="0" y="0" width={cut} height={VIEW_HEIGHT} />
                </clipPath>
                <clipPath id={`${uid}-rest`}>
                    <rect x={cut} y="0" width={VIEW_WIDTH - cut} height={VIEW_HEIGHT} />
                </clipPath>
            </defs>

            {(["played", "rest"] as const).map((part) => (
                <g
                    key={part}
                    clipPath={`url(#${uid}-${part})`}
                    opacity={part === "rest" && clamped > 0 ? 0.32 : 1}
                >
                    <path
                        d={d}
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                </g>
            ))}
        </svg>
    );
}
