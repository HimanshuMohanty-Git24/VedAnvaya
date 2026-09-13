/**
 * The VedAnvaya emblem.
 *
 * Four mirrored calligraphic strokes around a horizontal rule, with a rubric diamond at the
 * crossing. The brand board glosses it as source, relationship, source: two forms that meet
 * at a mark, on a line that runs through both. The rule is a sirorekha, the headline stroke
 * that binds a line of Devanagari into one word.
 *
 * ## Why this is a component and not the supplied PNG
 *
 * The artwork ships as a 168 KB PNG with the ink baked in as black. In dark mode that is a
 * black mark on a carbon page, and there is no way to recolour it short of a CSS filter that
 * would take the rubric diamond with it. As a path it inherits `currentColor`, costs under
 * 2 KB, stays crisp at any size, and can be drawn on.
 *
 * ## Where the geometry came from
 *
 * Traced from `VedAnvaya Logo.png` rather than guessed. The upper-left stroke's two edges
 * were sampled at every one of the 257 rows the ink occupies, then fitted with two cubic
 * segments each by least squares with pinned endpoints. Maximum deviation from the traced
 * contour is 0.35 units on the outer edge and 0.78 on the inner, against a 240-unit width:
 * 0.14% and 0.33%. The remaining three strokes are that path reflected, which is how the
 * mark gets a symmetry the raster does not quite have.
 *
 * Source measurements, for anyone who needs to re-derive this: the artwork is 1254 square,
 * the mark is centred on (626.5, 626.5), its ink spans x 201..1052 and y 344..909, the rule
 * is 25px thick and broken between x 551 and x 702, and the diamond is 150 square. The scale
 * factor into this viewBox is 240/851.
 */

export type EmblemProps = {
    /** Ink for the strokes and the rule. Defaults to `currentColor`. */
    className?: string;
    /**
     * Draw the diamond in the ink colour instead of rubric red. For contexts that are
     * already single-colour: a favicon mask, a print stylesheet, a dark-on-dark watermark.
     */
    mono?: boolean;
    /**
     * An accessible name. Omit it for the common case where the emblem sits beside the
     * wordmark and would otherwise be announced twice.
     */
    title?: string;
};

/**
 * One stroke, drawn in the upper-left quadrant. The other three are this path reflected
 * through the axes, which costs three transforms instead of three more path strings.
 */
const STROKE =
    "M-11.1 -79.7C-31 -80.1 -48.1 -65.3 -54 -48.9C-61.2 -34.2 -64.5 -14.4 -83.3 -7.5" +
    "L-78.3 -7.5C-33.6 -6.8 -38.7 -54.3 -12.3 -74C-9.9 -76.8 -2.2 -77.3 -2.1 -79.7Z";

export function Emblem({ className, mono = false, title }: EmblemProps) {
    return (
        <svg
            className={className}
            viewBox="-120 -80 240 160"
            fill="none"
            role={title ? "img" : "presentation"}
            aria-hidden={title ? undefined : true}
        >
            {title ? <title>{title}</title> : null}
            <g fill="currentColor">
                <path d={STROKE} />
                <path d={STROKE} transform="scale(-1 1)" />
                <path d={STROKE} transform="scale(1 -1)" />
                <path d={STROKE} transform="scale(-1 -1)" />
                {/*
                 * The rule is two runs with a gap, not one run behind the diamond. It is
                 * drawn that way in the artwork, and it matters in `mono`: a continuous rule
                 * under a same-coloured diamond would read as a lozenge swelling on a line
                 * rather than as a mark sitting in a break.
                 */}
                <rect x="-120" y="-3.5" width="99" height="7" />
                <rect x="21" y="-3.5" width="99" height="7" />
            </g>
            <path
                d="M0 -21L21 0L0 21L-21 0Z"
                fill={mono ? "currentColor" : "var(--va-rubric, #B64A2E)"}
            />
        </svg>
    );
}
