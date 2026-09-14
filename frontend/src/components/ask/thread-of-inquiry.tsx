import type { CSSProperties } from "react";

/**
 * The Thread of Inquiry.
 *
 * Traced from `Thread of Inquiry.png`, the same way the Anvaya Thread was traced rather than
 * shipped as a raster: the source is a drawing on cream paper, so as an image it would have to
 * be replaced wholesale in dark mode and could not carry a state. Drawn, it inherits
 * `currentColor`, costs a few hundred bytes, and the diamond at its end can be the one part
 * that changes.
 *
 * The figure is a line that leaves a point on the left, passes through a series of instruments
 * - a lens, a stack of leaves, a plotted circle, a rule, a proportioned square, two circles
 * meeting - and arrives at a rubric diamond. That is the shape of the product's claim about
 * Ask: a question is not answered, it is carried through a set of instruments until it arrives
 * somewhere, and the arrival is worth marking in red.
 *
 * ## On the travelling mark
 *
 * When `working` is set a short highlight runs along the thread and repeats. It deliberately
 * does not fill from left to right. A bar that fills is a claim about how much is left, and
 * this request reports nothing at all while it runs: the backend does not stream, so a
 * proportion would have to be invented. A shuttle passing along a warp says work is happening
 * and says nothing about when it stops, which is exactly what is known.
 */

/** The thread itself, left terminal to the diamond. Sampled from the source at 1656x944. */
const THREAD =
    "M4 78C28 78 44 60 62 60C80 60 88 74 108 74C128 74 138 56 160 56" +
    "C196 56 210 96 244 96C286 96 300 40 336 40C372 40 384 82 420 82" +
    "C448 82 462 66 486 66C516 66 528 84 556 84C588 84 600 52 632 52" +
    "C664 52 676 74 706 74C740 74 752 58 782 58";

/** The instruments, in the order the thread meets them. */
const LENS = { cx: 62, cy: 60, r: 22 };
const CIRCLE_PLOT = { cx: 244, cy: 68, r: 48 };
const SMALL_LENS = { cx: 420, cy: 82, r: 26 };
const MEETING = [
    { cx: 690, cy: 60, r: 30 },
    { cx: 722, cy: 78, r: 30 },
];

/** Leaves of a codex, seen at an angle. Four strokes plus the fore-edge. */
const LEAVES = [0, 5, 10, 15].map((offset) => ({
    d: `M${108 + offset} 30L${108 + offset} 96L${132 + offset} 104L${132 + offset} 38Z`,
}));

export function ThreadOfInquiry({
    className,
    working = false,
    arrived = false,
    height = 96,
}: {
    className?: string;
    /** Run the travelling highlight. Indeterminate on purpose; see the note above. */
    working?: boolean;
    /** Ink the terminal diamond. Set when an answer has actually landed. */
    arrived?: boolean;
    height?: number;
}) {
    return (
        <svg
            aria-hidden="true"
            className={["va-inquiry", working && "is-working", arrived && "has-arrived", className]
                .filter(Boolean)
                .join(" ")}
            fill="none"
            focusable="false"
            height={height}
            preserveAspectRatio="xMidYMid meet"
            style={{ "--va-inquiry-height": `${height}px` } as CSSProperties}
            viewBox="0 0 800 140"
        >
            {/* Verticals: the registration ticks the source drops through its instruments. */}
            <g className="va-inquiry-ticks" strokeWidth="1">
                <path d="M62 20v18M62 82v24" strokeDasharray="2 5" />
                <path d="M420 44v20M420 100v22" strokeDasharray="2 5" />
                <path d="M706 22v34M706 92v26" strokeDasharray="2 5" />
            </g>

            <g className="va-inquiry-instruments" strokeWidth="1.25">
                <circle cx={LENS.cx} cy={LENS.cy} r={LENS.r} />
                {LEAVES.map((leaf, index) => (
                    <path d={leaf.d} key={index} />
                ))}
                <circle cx={CIRCLE_PLOT.cx} cy={CIRCLE_PLOT.cy} r={CIRCLE_PLOT.r} />
                <path d="M244 20v96M196 68h96" strokeWidth="1" />
                <circle cx={SMALL_LENS.cx} cy={SMALL_LENS.cy} r={SMALL_LENS.r} />
                {/* The proportioned square, with the quarter-arc the source draws inside it. */}
                <path d="M556 44h72v64h-72z" />
                <path d="M628 108a72 72 0 0 0-72-64" strokeWidth="1" />
                <path d="M592 108v-28h36" strokeWidth="1" />
                {MEETING.map((circle, index) => (
                    <circle cx={circle.cx} cy={circle.cy} key={index} r={circle.r} />
                ))}
            </g>

            {/* The thread, drawn last so it passes over the instruments rather than under. */}
            <path className="va-inquiry-line" d={THREAD} strokeWidth="1.5" />
            {working && <path className="va-inquiry-shuttle" d={THREAD} strokeWidth="1.75" />}

            {/* Where the question enters, and the nodes it is carried through. */}
            <g className="va-inquiry-nodes">
                <circle cx="4" cy="78" r="4" />
                {[
                    [62, 60],
                    [244, 96],
                    [420, 82],
                    [556, 84],
                    [706, 74],
                ].map(([cx, cy]) => (
                    <circle cx={cx} cy={cy} key={`${cx}-${cy}`} r="2.5" />
                ))}
            </g>

            {/* The arrival. Rubric red, and the only filled mark in the figure. */}
            <path className="va-inquiry-diamond" d="M782 46l12 12l-12 12l-12-12z" />
        </svg>
    );
}
