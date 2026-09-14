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

/**
 * The alphas both renderers composite at, read from the token layer rather than written
 * into a shader.
 *
 * They are here because they were nowhere. Held as literals inside engine.ts and
 * planar-view.tsx, no audit could know what a fill composites to, and four of the eleven
 * light group fills sat under 3:1 while every contrast check in the repository reported pass.
 * scripts/audit-graph-contrast.mjs now reads the same declarations this does, so the gate and
 * the renderer cannot disagree about what is on screen.
 */
export type GraphAlphas = {
    /** Every node, WORLD mode. */
    world: number;
    /** A node inside the focused neighbourhood; the rest are discarded, not faded. */
    focus: number;
    /** The 2D subject and its first ring. */
    planar: number;
    /** The 2D second ring. Cannot reach 3:1 in the light theme - see the audit. */
    planarQuiet: number;
    /** One resting edge, of up to 185,693. */
    edgeRest: number;
    /** The only alpha an orb sheen may be drawn at. */
    orbSheen: number;
    /** A plate laid over the canvas. */
    plate: number;
};

export type GraphPalette = {
    /** rgb triples in the renderer's 0..1 space, indexed by group. */
    groups: Float32Array;
    /** The same colours as CSS strings, for the 2D canvas. */
    groupCss: string[];
    /**
     * The ground both renderers clear to, and therefore what every alpha composites
     * against. Identical in value to `page`, which is the older name for it; `canvas` is the
     * name the token layer and the audit both use, so new code should read this one.
     */
    canvas: string;
    /** @deprecated the same value as `canvas`. */
    page: string;
    /** @deprecated prefer `labelInk`. */
    ink: string;
    /** @deprecated prefer `labelInkQuiet`. */
    inkSoft: string;
    /** @deprecated prefer `edgeQuiet` for the resting field, `edgeBridge` for one line. */
    line: string;
    /** @deprecated prefer `relationPrimary`; the accent measures dE00 4.1 from the deity fill. */
    accent: string;

    /* --- canvas text. The halo is the paper, never a literal ivory. ------------- */
    labelHalo: string;
    labelInk: string;
    labelInkQuiet: string;

    /* --- plates floating over the canvas. ------------------------------------- */
    plate: string;
    plateInk: string;
    plateInkQuiet: string;
    /** Clears 3:1 against both the plate and the canvas. Use for `.va-edge-label`. */
    plateEdge: string;

    /* --- edges and relations. -------------------------------------------------- */
    edgeQuiet: string;
    edgeBridge: string;
    relationPrimary: string;
    relationSecondary: string;
    relationHover: string;

    /* --- paths: the route, then a three-stop ramp along its hops. -------------- */
    pathStrong: string;
    pathStops: [string, string, string];

    /* --- state and orbs. ------------------------------------------------------- */
    /** Clears 3:1 against every group fill in both themes. The one token that has to. */
    focusRing: string;
    /** The canvas colour: a line of paper between two orbs, not a stroke. */
    orbKeyline: string;
    /** Only ever composited at `alphas.orbSheen`. Opaque it becomes a second keyline. */
    orbSheen: string;

    alphas: GraphAlphas;
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
function makeReader(scope: HTMLElement) {
    const probe = document.createElement("span");
    /*
     * `transition:none` is the whole fix for a release-blocking defect, so it is worth the note.
     *
     * `globals.css` carries the usual reduced-motion override - `*, *::before, *::after {
     * transition-duration: 0.01ms !important }` - and the probe is an element, so it inherits it.
     * With a non-zero duration on `transition-property: all`, `getComputedStyle().color` read
     * synchronously after an assignment returns the *interpolated* value, which at that instant is
     * still the previous colour. So every read after the first returned the first read's answer.
     *
     * Measured on `/graph` under `prefers-reduced-motion: reduce`: the deity fill is read first,
     * and `--va-surface-page`, `--va-text-primary`, `--va-line-strong`, `--va-accent-base` and
     * the other ten group fills then all came back as rgb(179, 80, 38) - the deity fill. The
     * canvas therefore cleared to the deity colour and drew deity-coloured nodes on it, and the
     * whole spatial view rendered as a flat orange rectangle covering 98.7% of the viewport, on
     * both the graph page and the homepage preview. A reader who asked for less motion got no
     * graph at all.
     *
     * The defect was invisible in the motion-on path because a 0s duration makes the read
     * immediate, and invisible in a unit test because jsdom runs no transitions.
     */
    probe.style.cssText =
        "position:absolute;visibility:hidden;pointer-events:none;transition:none";
    scope.appendChild(probe);
    const read = (token: string, fallback: string) => {
        probe.style.color = "";
        probe.style.color = `var(${token})`;
        const value = getComputedStyle(probe).color;
        /* An unresolvable custom property leaves `color` at its inherited value, which is
           usually black and is indistinguishable from a token that genuinely is black. The
           fallback is used rather than shipping an invisible graph. */
        return !value || value === "rgba(0, 0, 0, 0)" ? fallback : value;
    };
    /*
     * The alphas are bare numbers, so they cannot go through the `color` round trip above.
     * `getPropertyValue` is correct for them and only for them: a custom property holding a
     * number is returned verbatim, and there is no `var()` chain to resolve because
     * tokens.css declares them as literals for exactly this reason.
     *
     * A missing or unparseable value falls back rather than yielding NaN. A NaN alpha in a
     * vertex attribute does not throw; it silently discards the node.
     */
    const readNumber = (token: string, fallback: number) => {
        const raw = getComputedStyle(scope).getPropertyValue(token).trim();
        const value = Number.parseFloat(raw);
        return raw && Number.isFinite(value) ? value : fallback;
    };
    return { read, readNumber, done: () => probe.remove() };
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
     *
     * This must stay. It is only half of a pipeline, and the other half landed in 55e8715,
     * which added `#include <colorspace_fragment>` to both custom fragment shaders in
     * engine.ts. Linear in, encoded out, once. Before that commit the shaders wrote linear
     * values straight into an 8-bit sRGB buffer and published colours darker than the ones
     * they were given - light-mode deity #bd4f32 reached the screen as #821408 - so removing
     * this transform now would look like a fix and would instead publish everything too
     * light, and a second encode here would double-encode. The 3D pixel assertion in
     * tests/e2e/graph-palette.spec.ts is what holds this end of it honest.
     */
    const toLinear = (c: number) =>
        c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    return [toLinear(r), toLinear(g), toLinear(b)];
}

/**
 * Read the palette as it resolves *inside* a given element.
 *
 * `scope` exists because one surface in the product does not take the page's theme: the
 * homepage panel is carbon whether the site is light or dark, and it carries the `dark` class to
 * say so. A probe appended to `document.body` resolves the page's tokens, so a preview inside
 * that panel would clear to ivory inside a carbon frame - which is exactly the defect a previous
 * phase had to fix on the graph page. Reading through an element in the panel lets the cascade
 * answer the question instead of the caller guessing.
 */
export function readGraphPalette(
    revision = 0,
    scope: HTMLElement = document.body,
): GraphPalette {
    const { read, readNumber, done } = makeReader(scope);
    const groupCss = GROUP_NAMES.map((group) => read(`--va-group-${group}-fill`, "#747774"));
    const groups = new Float32Array(GROUP_NAMES.length * 3);
    groupCss.forEach((css, i) => {
        const [r, g, b] = toLinearTriple(css);
        groups[i * 3] = r;
        groups[i * 3 + 1] = g;
        groups[i * 3 + 2] = b;
    });
    const canvas = read("--va-graph-canvas", "#f4f0e7");
    const palette: GraphPalette = {
        groups,
        groupCss,
        canvas,
        page: canvas,
        ink: read("--va-graph-label-ink", "#171815"),
        inkSoft: read("--va-graph-label-ink-quiet", "#5d5f56"),
        line: read("--va-graph-edge-quiet", "#aa9c7f"),
        accent: read("--va-accent-base", "#b64a2e"),

        labelHalo: read("--va-graph-label-halo", "#f4f0e7"),
        labelInk: read("--va-graph-label-ink", "#171815"),
        labelInkQuiet: read("--va-graph-label-ink-quiet", "#5d5f56"),

        plate: read("--va-graph-plate", "#fbf9f4"),
        plateInk: read("--va-graph-plate-ink", "#171815"),
        plateInkQuiet: read("--va-graph-plate-ink-quiet", "#5c5e56"),
        plateEdge: read("--va-graph-plate-edge", "#847e70"),

        edgeQuiet: read("--va-graph-edge-quiet", "#aa9c7f"),
        edgeBridge: read("--va-graph-edge-bridge", "#7a705d"),
        relationPrimary: read("--va-graph-relation-primary", "#8e3720"),
        relationSecondary: read("--va-graph-relation-secondary", "#9b9080"),
        relationHover: read("--va-graph-relation-hover", "#3a3b36"),

        pathStrong: read("--va-graph-path-strong", "#26364a"),
        pathStops: [
            read("--va-graph-path-stop-1", "#35495f"),
            read("--va-graph-path-stop-2", "#4f6179"),
            read("--va-graph-path-stop-3", "#6f7d8f"),
        ],

        focusRing: read("--va-graph-focus-ring", "#171815"),
        orbKeyline: read("--va-graph-orb-keyline", "#f4f0e7"),
        orbSheen: read("--va-graph-orb-sheen", "#efe6d1"),

        alphas: {
            world: readNumber("--va-graph-alpha-world", 0.85),
            focus: readNumber("--va-graph-alpha-focus", 0.96),
            planar: readNumber("--va-graph-alpha-planar", 0.94),
            planarQuiet: readNumber("--va-graph-alpha-planar-quiet", 0.55),
            edgeRest: readNumber("--va-graph-alpha-edge-rest", 0.05),
            orbSheen: readNumber("--va-graph-alpha-orb-sheen", 0.18),
            plate: readNumber("--va-graph-alpha-plate", 0.92),
        },
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
    return usePaletteIn(undefined);
}

/**
 * The palette as it resolves inside one element, which may not exist yet.
 *
 * Distinct from `useGraphPalette` because the waiting is the point. A caller that names a scope
 * is saying its colours are not the page's, so answering with the page's while the element is
 * still null would be worse than answering nothing: the consumer would build with ivory, then
 * rebuild with carbon a frame later. Null here means "not yet", not "no theme".
 */
export function useScopedGraphPalette(scope: HTMLElement | null): GraphPalette | null {
    return usePaletteIn(scope);
}

function usePaletteIn(scope: HTMLElement | null | undefined): GraphPalette | null {
    const [palette, setPalette] = useState<GraphPalette | null>(null);

    useEffect(() => {
        // Explicitly null: a scope was named and has not arrived. Waiting is correct.
        if (scope === null) return;
        let revision = 0;
        let frame = 0;

        const refresh = () => {
            // Deferred a frame: the class lands before the stylesheet has necessarily been
            // recomputed, and reading in the same tick can return the outgoing theme.
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                revision += 1;
                setPalette(readGraphPalette(revision, scope ?? document.body));
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
        // Re-read when the scope element arrives, since the answer depends on where it is read.
    }, [scope]);

    return palette;
}
