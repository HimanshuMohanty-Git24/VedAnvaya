import { Emblem } from "./emblem";

/**
 * The VedAnvaya lockup: the emblem, then the name.
 *
 * The name is live text in Fraunces rather than the supplied `Logo with text.png`. A raster
 * wordmark is 264 KB, has the ink baked in so it cannot invert for dark mode, blurs on any
 * display that is not exactly 1x, and is invisible to search and to a screen reader. Set as
 * text it costs nothing extra, because the display face is already loaded for the headings.
 *
 * The rubric diamond between "Ved" and "Anvaya" is the brand board's signature and the only
 * ornament in the mark. It is a span rather than a character because there is no Unicode
 * point for it that any text font would draw at the right weight and size.
 */

export type WordmarkProps = {
    className?: string;
    /**
     * Drop the diamond and set the name plainly. Below roughly 18px the diamond stops being
     * a mark and becomes a speck, and a speck between two syllables reads as a rendering
     * fault rather than as a separator.
     */
    plain?: boolean;
    /** Show the tagline under the name. For the footer and the About page, not the header. */
    tagline?: boolean;
};

export function Wordmark({ className, plain = false, tagline = false }: WordmarkProps) {
    return (
        <span className={["va-wordmark", className].filter(Boolean).join(" ")}>
            <Emblem className="va-wordmark-emblem" />
            <span className="va-wordmark-text">
                {/*
                 * One accessible string, assembled from three nodes. The diamond is
                 * aria-hidden so the name is announced as "VedAnvaya" and not as
                 * "Ved, image, Anvaya".
                 */}
                <span className="va-wordmark-name">
                    Ved
                    {plain ? null : (
                        <span className="va-wordmark-diamond" aria-hidden="true">
                            <svg viewBox="-10 -10 20 20" fill="currentColor">
                                <path d="M0 -9L9 0L0 9L-9 0Z" />
                            </svg>
                        </span>
                    )}
                    Anvaya
                </span>
                {tagline ? <span className="va-wordmark-tagline">The Vedas, connected.</span> : null}
            </span>
        </span>
    );
}
