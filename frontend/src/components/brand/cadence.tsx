"use client";

/**
 * Vedic Cadence: the recitation mark.
 *
 * A contour line that rises and falls, with rubric marks above its peaks and below its
 * troughs. It is the brand's drawing of Vedic pitch accent, which is the reason the Samhitas
 * are transmitted as sound and not only as text: udatta raised, anudatta lowered, svarita
 * the fall between them.
 *
 * ## Why this is generated rather than traced
 *
 * The other brand marks are fixed artwork and are traced to match it. This one is not fixed
 * artwork, it is a notation, and a notation with its content hard-coded can only ever be
 * decoration. Built from a list of turns instead, the same component draws the brand's
 * default contour now and a particular verse's contour later, from accents the corpus
 * already carries. See the note above CONTOUR for what that would take.
 *
 * An accent belongs to a turn rather than to a position on the baseline, which is both how
 * the notation works and what the artwork does: measured, each mark sits between 8.9 and
 * 12.5 units clear of its own turn's apex, never a fixed distance from the line.
 *
 * The default contour is measured from `Vedic Cadence.png`: baseline at y=63.3 in a 1000 by
 * 90 box, three deliberate breaks, seven turns, six accents.
 */

import { useId } from "react";

/** One rise or fall in the contour, with whatever is written beside it. */
type Turn = {
    /** Centre of the turn, in viewBox units along the line. */
    at: number;
    /** Distance from the baseline at the apex. Negative is up, because SVG y grows down. */
    amplitude: number;
    /** Half the turn's footprint. Wider reads as a slower change of pitch. */
    width: number;
    /** The mark written beside this turn, clear of its apex. */
    accent?: { mark: "dot" | "stroke"; height?: number };
};

const BASELINE = 63.3;
const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 90;

/** How far clear of its apex an accent is written. Measured range in the artwork: 8.9 to 12.5. */
const ACCENT_CLEARANCE = 10.4;

/**
 * The line breaks. A recited verse is not one continuous sound, and the artwork says so by
 * lifting the pen between phrases. Each entry is the x range of one gap.
 */
const BREAKS: ReadonlyArray<readonly [number, number]> = [
    [198, 220],
    [531, 554],
    [742, 764],
];

/**
 * To drive this from real text later: the RV and AV surfaces carry combining U+0331 for
 * anudatta and a line above for svarita, per syllable. One Turn per accented syllable, with
 * amplitude chosen by accent class, would make a player's contour the verse's own rather
 * than a house pattern. Recorded as an open question in the revamp plan; not done here.
 */
const CONTOUR: readonly Turn[] = [
    { at: 99, amplitude: -17.8, width: 45, accent: { mark: "dot" } },
    { at: 286, amplitude: -39.6, width: 52, accent: { mark: "stroke", height: 14 } },
    { at: 459, amplitude: 11.3, width: 23, accent: { mark: "dot" } },
    { at: 610, amplitude: -25.8, width: 43, accent: { mark: "dot" } },
    { at: 668, amplitude: -10.6, width: 22, accent: { mark: "stroke", height: 7.7 } },
    { at: 798, amplitude: 11.1, width: 23, accent: { mark: "dot" } },
    { at: 914, amplitude: -16.6, width: 52 },
];

const round = (value: number) => Math.round(value * 10) / 10;

/**
 * Build one run of the line, from `from` to `to`, bending through the turns inside it.
 *
 * Each turn is two mirrored cubics through its apex. The 0.45 and 0.55 handle fractions are
 * what keep the shoulders from squaring off: pulling the outer handle past the halfway point
 * flattens the approach, so the line leaves the baseline gradually and arrives at the apex
 * steeply. That is how a pitch contour moves and is not how a sine wave moves.
 */
function run(from: number, to: number): string {
    const parts = [`M${round(from)} ${BASELINE}`];
    let cursor = from;

    for (const turn of CONTOUR) {
        const start = turn.at - turn.width;
        const end = turn.at + turn.width;
        if (start < from || end > to) continue;

        const apex = round(BASELINE + turn.amplitude);
        if (start > cursor) parts.push(`L${round(start)} ${BASELINE}`);
        parts.push(
            `C${round(turn.at - turn.width * 0.45)} ${BASELINE}` +
                ` ${round(turn.at - turn.width * 0.55)} ${apex} ${round(turn.at)} ${apex}`,
        );
        parts.push(
            `C${round(turn.at + turn.width * 0.55)} ${apex}` +
                ` ${round(turn.at + turn.width * 0.45)} ${BASELINE} ${round(end)} ${BASELINE}`,
        );
        cursor = end;
    }

    if (cursor < to) parts.push(`L${round(to)} ${BASELINE}`);
    return parts.join("");
}

const RUNS: string[] = (() => {
    const edges = [0, ...BREAKS.flat(), VIEW_WIDTH];
    const out: string[] = [];
    for (let i = 0; i < edges.length; i += 2) out.push(run(edges[i], edges[i + 1]));
    return out;
})();

export type CadenceProps = {
    className?: string;
    /**
     * How far through the line to draw, from 0 to 1. Past the cut the line is drawn faint
     * rather than omitted, so the mark keeps its full shape while a recording plays and the
     * player does not appear to be growing a new element as it goes.
     */
    progress?: number;
    /** An accessible name. Omit it inside a player that already labels itself. */
    title?: string;
};

export function Cadence({ className, progress = 1, title }: CadenceProps) {
    /* Two instances on one page would otherwise share a clipPath id and clip each other. */
    const uid = useId().replace(/:/g, "");
    const clamped = Math.min(1, Math.max(0, progress));
    const cut = round(clamped * VIEW_WIDTH);

    return (
        <svg
            className={className}
            viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
            fill="none"
            /*
             * The one place stretching is right: the mark's meaning is its sequence of turns,
             * and filling a player's width with it is what a waveform does. The stroke is
             * held to a true weight by vector-effect below.
             */
            preserveAspectRatio="none"
            role={title ? "img" : "presentation"}
            aria-hidden={title ? undefined : true}
        >
            {title ? <title>{title}</title> : null}
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
                    opacity={part === "rest" && clamped < 1 ? 0.3 : 1}
                >
                    {RUNS.map((d) => (
                        <path
                            key={d}
                            d={d}
                            stroke="currentColor"
                            strokeWidth="1.6"
                            strokeLinecap="round"
                            vectorEffect="non-scaling-stroke"
                        />
                    ))}
                    {CONTOUR.map((turn) => {
                        if (!turn.accent) return null;
                        const raised = turn.amplitude < 0;
                        const apex = BASELINE + turn.amplitude;
                        const y = raised ? apex - ACCENT_CLEARANCE : apex + ACCENT_CLEARANCE;
                        const fill = "var(--va-rubric, #B64A2E)";
                        return turn.accent.mark === "dot" ? (
                            <circle key={turn.at} cx={turn.at} cy={round(y)} r="2.7" fill={fill} />
                        ) : (
                            <rect
                                key={turn.at}
                                x={turn.at - 0.7}
                                y={round(y - (turn.accent.height ?? 10) / 2)}
                                width="1.4"
                                height={turn.accent.height ?? 10}
                                fill={fill}
                            />
                        );
                    })}
                </g>
            ))}
        </svg>
    );
}
