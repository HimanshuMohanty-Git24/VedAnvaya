"use client";

import { useEffect, useState } from "react";

/**
 * The graph's colours, read from the token layer and re-read when the theme changes.
 *
 * ## Why this exists as its own module
 *
 * Both renderers read the same tokens, and both had their own copy of the reading code with
 * its own hardcoded fallbacks - which had drifted, and were a third semantic colour table
 * after the two this rebuild already spent a phase reconciling. One of them used the deity
 * fill as the accent colour. They are now read once, here, by one function.
 *
 * ## Why it is a subscription and not a one-off
 *
 * A canvas bakes colour into buffers, which is correct for a scene drawn thousands of times a
 * second and useless when the theme changes. Read once at mount, the 3D engine kept painting
 * an opaque ivory background inside a carbon page, with its own DOM labels correctly
 * re-themed above it: the canvas and the page visibly disagreeing. The theme class lands on
 * `<html>`, so that is what is watched.
 */

export const GROUP_NAMES = [
    "deity",
    "unresolved-deity",
    "passage",
    "person",
    "idea",
    "rite",
    "thing",
    "wording",
    "derived",
    "record",
    "other",
] as const;

export type GraphPalette = {
    /** rgb triples in the renderer's 0..1 space, indexed by group. */
    groups: Float32Array;
    /** The same colours as CSS strings, for the 2D canvas. */
    groupCss: string[];
    page: string;
    ink: string;
    inkSoft: string;
    line: string;
    accent: string;
    /** Bumped on every re-read, so a consumer can depend on it without deep comparison. */
    revision: number;
};

/**
 * Read a custom property by asking the browser to resolve it.
 *
 * A hidden span rather than `getComputedStyle(document.documentElement).getPropertyValue`,
 * because the latter returns the declaration verbatim - which for a token defined as
 * `var(--va-rubric-500)` is the string "var(--va-rubric-500)" rather than a colour. Setting
 * it as a `color` and reading the computed value makes the browser do the resolution.
 */
function makeReader() {
    const probe = document.createElement("span");
    probe.style.cssText = "position:absolute;visibility:hidden;pointer-events:none";
    document.body.appendChild(probe);
    const read = (token: string, fallback: string) => {
        probe.style.color = "";
        probe.style.color = `var(${token})`;
        const value = getComputedStyle(probe).color;
        /* An unresolvable custom property leaves `color` at its inherited value, which is
           usually black and is indistinguishable from a token that genuinely is black. The
           fallback is used rather than shipping an invisible graph. */
        return !value || value === "rgba(0, 0, 0, 0)" ? fallback : value;
    };
    return { read, done: () => probe.remove() };
}

function toLinearTriple(css: string): [number, number, number] {
    const match = css.match(/-?[\d.]+/g);
    if (!match || match.length < 3) return [0.55, 0.58, 0.56];
    const [r, g, b] = match.slice(0, 3).map((n) => Number(n) / 255);
    /*
     * sRGB to linear.
     *
     * Three renders in a linear working space, so a colour handed straight from CSS arrives
     * too light. This is the same transform `Color.setStyle` applies; it is done explicitly
     * because the values also go into a raw vertex attribute, which no one converts for us.
     */
    const toLinear = (c: number) =>
        c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    return [toLinear(r), toLinear(g), toLinear(b)];
}

export function readGraphPalette(revision = 0): GraphPalette {
    const { read, done } = makeReader();
    const groupCss = GROUP_NAMES.map((group) => read(`--va-group-${group}-fill`, "#8c9490"));
    const groups = new Float32Array(GROUP_NAMES.length * 3);
    groupCss.forEach((css, i) => {
        const [r, g, b] = toLinearTriple(css);
        groups[i * 3] = r;
        groups[i * 3 + 1] = g;
        groups[i * 3 + 2] = b;
    });
    const palette: GraphPalette = {
        groups,
        groupCss,
        page: read("--va-surface-page", "#f4f0e7"),
        ink: read("--va-text-primary", "#171815"),
        inkSoft: read("--va-text-tertiary", "#5d5f56"),
        line: read("--va-line-strong", "#cfc5af"),
        accent: read("--va-accent-base", "#b64a2e"),
        revision,
    };
    done();
    return palette;
}

/**
 * The palette, kept current.
 *
 * Watches the class attribute on `<html>`, which is where `next-themes` writes, and also the
 * system preference for the case where the site is following it. Returns null until the first
 * read, so a consumer never paints with guessed colours.
 */
export function useGraphPalette(): GraphPalette | null {
    const [palette, setPalette] = useState<GraphPalette | null>(null);

    useEffect(() => {
        let revision = 0;
        let frame = 0;

        const refresh = () => {
            // Deferred a frame: the class lands before the stylesheet has necessarily been
            // recomputed, and reading in the same tick can return the outgoing theme.
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                revision += 1;
                setPalette(readGraphPalette(revision));
            });
        };

        refresh();

        const observer = new MutationObserver(refresh);
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["class", "data-theme", "style"],
        });
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        media.addEventListener("change", refresh);

        return () => {
            cancelAnimationFrame(frame);
            observer.disconnect();
            media.removeEventListener("change", refresh);
        };
    }, []);

    return palette;
}
