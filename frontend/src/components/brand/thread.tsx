/**
 * The Anvaya Thread: the brand's section divider, and its broken twin.
 *
 * A hairline with a four-pointed flare at its centre holding a rubric diamond. `anvaya` is
 * the grammarian's word for the prose reordering that makes a verse's syntax explicit, so a
 * thread drawn between two things is the right mark for this product's one idea.
 *
 * ## Why it is a flex row and not one wide SVG
 *
 * A divider spans whatever it is put inside. Stretching one SVG to do that would stretch the
 * ornament with it and the flare would go oval at wide widths. So the rule is two CSS
 * hairlines that flex and only the ornament is drawn, at a fixed size, between them. The
 * rule then lands on a device pixel instead of being resampled.
 *
 * ## Geometry
 *
 * Traced from `Anvaya Thread.png`, whose flare spans 248 by 88. The quarter curve from the
 * flare's left point to its apex was fitted with two cubics at a maximum deviation of 0.66px
 * against that 88px height, which is 0.7%; the rest is that curve reflected.
 *
 * The flare is stroked, not filled, and that was checked rather than assumed: a column
 * through it at x=1000 in the source returns three separate ink runs of two to three pixels
 * each, the upper curve, the rule, and the lower curve. Filling the envelope between them
 * turns a hairline ornament into a black lozenge, which is what a first attempt here did.
 *
 * The rule also runs through the flare and stops at the diamond, so the two arcs read as
 * something the line passes through rather than as a shape sitting on top of it.
 */

import type { CSSProperties } from "react";

/** The upper arc, left point to right point through the apex. The lower one is its mirror. */
const ARC =
    "M-118 0C-83.1 -1.5 -49.4 -8.4 -23 -30.5C-14.1 -35.3 -13.9 -52.7 0 -44" +
    "C13.9 -52.7 14.1 -35.3 23 -30.5C49.4 -8.4 83.1 -1.5 118 0";

const DIAMOND = "M0 -19L19 0L0 19L-19 0Z";

export type ThreadProps = {
    className?: string;
    /**
     * Draw the thread with a gap at its centre and the diamond adrift in it.
     *
     * This is the 404 and empty-state mark, and it carries one idea: the connection this
     * product exists to draw is the thing that is missing. Using it wherever a lookup
     * returned nothing keeps an empty result inside the system rather than outside it.
     */
    broken?: boolean;
    /** Ornament height in pixels. The rule sits at its vertical centre. */
    size?: number;
};

export function Thread({ className, broken = false, size = 22 }: ThreadProps) {
    const width = Math.round((size * 248) / 88);

    return (
        <div
            className={["va-thread", broken && "is-broken", className].filter(Boolean).join(" ")}
            style={{ "--va-thread-size": `${size}px` } as CSSProperties}
        >
            <span className="va-thread-rule" aria-hidden="true" />
            <svg
                className="va-thread-mark"
                width={width}
                height={size}
                viewBox="-124 -44 248 88"
                fill="none"
                aria-hidden="true"
            >
                {/*
                 * Broken drops the arcs and the inner rule, keeping only the diamond. The
                 * flare is the join; with nothing to join, drawing it anyway would make the
                 * break read as decoration rather than as the absence it reports.
                 */}
                {broken ? null : (
                    <g stroke="currentColor" strokeWidth="1" vectorEffect="non-scaling-stroke">
                        <path d={ARC} />
                        <path d={ARC} transform="scale(1 -1)" />
                        <path d="M-118 0H-19" />
                        <path d="M19 0H118" />
                    </g>
                )}
                <path d={DIAMOND} fill="var(--va-rubric, #B64A2E)" />
            </svg>
            <span className="va-thread-rule" aria-hidden="true" />
        </div>
    );
}
