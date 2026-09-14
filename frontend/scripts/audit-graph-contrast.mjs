#!/usr/bin/env node
/**
 * The graph's colours, measured against what a reader actually sees.
 *
 * ## Why this is a second script and not more rows in audit-contrast.mjs
 *
 * That script checks a token against a surface. Nothing in the graph is painted that way. A
 * node fill is composited at 0.85, 0.96, 0.94 or 0.55 over the canvas before a reader sees it,
 * a plate bleeds the fill beneath it through at 0.92, and a focus ring has to be seen on a
 * *fill* rather than on the page. Measuring the token is measuring the wrong colour, and the
 * gap is not academic: the light deity fill measured 4.51:1 as a token and 3.54:1 on screen.
 *
 * ## What it caught when it was written
 *
 * The eleven group fills were checked by audit-contrast.mjs against four surfaces in two
 * themes - 88 pairs, every one of them on a `--va-group-*-text` token that no stylesheet and
 * no renderer read. The eleven `-fill` tokens that were painted got none. The report said
 * "all pass" while four light fills sat under 3:1 against the page even at full alpha
 * (unresolved-deity 2.31, derived 2.92, record 2.73, other 2.73) and six of eleven failed
 * once composited. The 2D focus keyline measured 1.18:1 light and 1.07:1 dark over the node
 * it was marking. `record` and `other` were byte-identical at dE00 0.00 and nobody had
 * decided that.
 *
 * A validator that skips is worse than no validator, so this one measures its own coverage:
 * it enumerates every declared `--va-graph-*` and `--va-group-*` token and fails if any of
 * them is never checked. Precision without coverage is how the last one passed.
 *
 * ## Every number is printed, pass or fail
 *
 * A gate that prints only failures teaches its readers that silence means "fine", and the
 * next person to widen a threshold does it invisibly. Every check below prints its measured
 * value and its floor, so the output is the evidence and the exit code is only the summary.
 *
 * Run: node scripts/audit-graph-contrast.mjs
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const THEME = path.join(here, "..", "src", "styles", "theme.css");
const TOKENS = path.join(here, "..", "src", "styles", "tokens.css");

/* ----------------------------------------------------------------- colour - */

const hex = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
const srgbToLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const linearToSrgb = (c) => (c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055);
const toLinear = (rgb) => rgb.map((c) => srgbToLinear(c / 255));

function luminance(rgb) {
    const [r, g, b] = toLinear(rgb);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a, b) {
    const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
}
/*
 * Alpha compositing in *encoded* sRGB, which is what both renderers do.
 *
 * Not a linear-light blend. The WebGL drawing buffer is RGBA8 with no sRGB hardware encode,
 * and since 55e8715 both custom fragment shaders run `colorspace_fragment` before the blend,
 * so the values the blender sees are already encoded. The 2D canvas blends its stored 8-bit
 * values directly. Compositing in linear here would report every mid-tone as lighter than it
 * is and quietly hand back contrast the reader never got.
 */
const over = (fg, bg, alpha) => fg.map((c, i) => alpha * c + (1 - alpha) * bg[i]);

function toLab(rgb) {
    const [r, g, b] = toLinear(rgb);
    const X = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047;
    const Y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b;
    const Z = (0.0193339 * r + 0.119192 * g + 0.9503041 * b) / 1.08883;
    const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29);
    const [fx, fy, fz] = [f(X), f(Y), f(Z)];
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/** CIEDE2000. Euclidean distance in Lab overstates hue differences at low chroma, which is
    where half this palette lives, so the quiet categories would score as separated when they
    are not. */
function deltaE00(rgb1, rgb2) {
    const [L1, a1, b1] = toLab(rgb1);
    const [L2, a2, b2] = toLab(rgb2);
    const Cb = (Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2;
    const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
    const ap1 = a1 * (1 + G);
    const ap2 = a2 * (1 + G);
    const Cp1 = Math.hypot(ap1, b1);
    const Cp2 = Math.hypot(ap2, b2);
    const deg = (x) => ((x * 180) / Math.PI + 360) % 360;
    const hp1 = Cp1 === 0 ? 0 : deg(Math.atan2(b1, ap1));
    const hp2 = Cp2 === 0 ? 0 : deg(Math.atan2(b2, ap2));
    const dL = L2 - L1;
    const dC = Cp2 - Cp1;
    let dh = 0;
    if (Cp1 * Cp2 !== 0) {
        dh = hp2 - hp1;
        if (dh > 180) dh -= 360;
        else if (dh < -180) dh += 360;
    }
    const dH = 2 * Math.sqrt(Cp1 * Cp2) * Math.sin((dh * Math.PI) / 360);
    const Lb = (L1 + L2) / 2;
    const Cpb = (Cp1 + Cp2) / 2;
    let hb;
    if (Cp1 * Cp2 === 0) hb = hp1 + hp2;
    else if (Math.abs(hp1 - hp2) <= 180) hb = (hp1 + hp2) / 2;
    else hb = hp1 + hp2 < 360 ? (hp1 + hp2 + 360) / 2 : (hp1 + hp2 - 360) / 2;
    const T =
        1 -
        0.17 * Math.cos(((hb - 30) * Math.PI) / 180) +
        0.24 * Math.cos((2 * hb * Math.PI) / 180) +
        0.32 * Math.cos(((3 * hb + 6) * Math.PI) / 180) -
        0.2 * Math.cos(((4 * hb - 63) * Math.PI) / 180);
    const Sl = 1 + (0.015 * (Lb - 50) ** 2) / Math.sqrt(20 + (Lb - 50) ** 2);
    const Sc = 1 + 0.045 * Cpb;
    const Sh = 1 + 0.015 * Cpb * T;
    const Rt =
        -Math.sin((2 * 30 * Math.exp(-(((hb - 275) / 25) ** 2)) * Math.PI) / 180) *
        (2 * Math.sqrt(Cpb ** 7 / (Cpb ** 7 + 25 ** 7)));
    return Math.sqrt(
        (dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh),
    );
}

/* Machado, Oliveira & Santos (2009), severity 1.0, applied in linear RGB. Chosen over a
   channel-swap approximation because the quiet categories differ by a few units of chroma and
   a crude simulation collapses them to identical, which would report a defect that is not
   there and get the whole check switched off. */
const CVD = {
    protanopia: [
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ],
    deuteranopia: [
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.01182, 0.04294, 0.968881],
    ],
    tritanopia: [
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.3039],
    ],
};
function simulate(rgb, kind) {
    const l = toLinear(rgb);
    return CVD[kind].map((row) =>
        Math.max(0, Math.min(255, linearToSrgb(Math.max(0, Math.min(1, row[0] * l[0] + row[1] * l[1] + row[2] * l[2]))) * 255)),
    );
}

/* ------------------------------------------------------------------- css - */

/** Comments are stripped before declarations are read, because this file's comments quote
    token names and ratios and a naive scan would parse prose as a declaration. The one
    machine-readable comment is pulled out first. */
const stripComments = (css) => css.replace(/\/\*[\s\S]*?\*\//g, "");

function block(css, opener) {
    const start = css.indexOf(opener);
    if (start < 0) return "";
    const open = css.indexOf("{", start);
    let depth = 0;
    for (let i = open; i < css.length; i++) {
        if (css[i] === "{") depth++;
        if (css[i] === "}" && --depth === 0) return css.slice(open + 1, i);
    }
    return "";
}
function declarations(body) {
    const out = {};
    for (const m of stripComments(body).matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
    return out;
}

const themeCss = readFileSync(THEME, "utf8");
const tokensCss = readFileSync(TOKENS, "utf8");
const primitives = declarations(block(tokensCss, "@theme static"));
const lightDecl = declarations(block(themeCss, ":root {"));
const darkDecl = declarations(block(themeCss, ".dark {"));

/** `var(--x)` chains resolved inside one theme, down to a literal six-digit hex. */
function resolver(aliases) {
    return function resolve(value, seen = new Set()) {
        let current = String(value ?? "").trim();
        while (current.startsWith("var(")) {
            const name = current.slice(4, current.indexOf(")")).trim();
            if (seen.has(name)) return null;
            seen.add(name);
            current = String(aliases[name] ?? primitives[name] ?? "").trim();
            if (!current) return null;
        }
        return /^#[0-9a-f]{6}$/i.test(current) ? current : null;
    };
}

/* --------------------------------------------------------------- reporting - */

let failures = 0;
let checks = 0;
const touched = new Set();

/** Every check goes through here, so every check prints. */
function record(label, measured, test, expectation, unit = ":1") {
    checks += 1;
    const ok = test(measured);
    if (!ok) failures += 1;
    const value = typeof measured === "number" ? measured.toFixed(2) + unit : String(measured);
    console.log(`  ${ok ? "pass" : "FAIL"}  ${value.padStart(9)}  ${expectation.padEnd(34)} ${label}`);
    return ok;
}
const atLeast = (floor) => (v) => v >= floor - 1e-9;
const below = (ceiling) => (v) => v < ceiling;
const within = (lo, hi) => (v) => v >= lo - 1e-9 && v < hi;

/* --------------------------------------------------------------- the table - */

const GROUPS = [
    "deity", "unresolved-deity", "passage", "person", "idea",
    "rite", "thing", "wording", "derived", "record", "other",
];
/** The alphas a node carrying a focus ring is actually drawn at. A recessive second-ring node
    and a dimmed WORLD node are never the selected one, so gating the ring against them would
    assert a pairing the renderers cannot produce - the same mistake as checking a token pair
    that never occurs in the DOM. */
const RINGED_ALPHAS = [
    "--va-graph-alpha-planar",
    "--va-graph-alpha-curated",
    "--va-graph-alpha-focus",
];
/** The alphas at which a fill has to identify its group. Read from tokens.css, which follows
    the renderers; if an engine changes a literal and not the token, the gate measures a
    composite nobody draws, so the two are kept in step deliberately. */
const IDENTIFYING = [
    "--va-graph-alpha-planar",
    "--va-graph-alpha-curated",
    "--va-graph-alpha-focus",
    "--va-graph-alpha-world",
];
const DE_FLOOR = 9;
const DE_CVD_FLOOR = 4.5;
/** A drawn mark must be told apart from a node it can sit beside. */
const DE_MARK_FLOOR = 5;

for (const theme of ["light", "dark"]) {
    const aliases = theme === "light" ? { ...lightDecl } : { ...lightDecl, ...darkDecl };
    const resolve = resolver(aliases);
    const colour = (name) => {
        touched.add(name);
        const value = resolve(aliases[name]);
        if (!value) {
            failures += 1;
            checks += 1;
            console.log(`  FAIL  unresolved  declared and resolvable          ${name}`);
            return null;
        }
        return hex(value);
    };
    /* A missing alpha is a hard failure, not a default. A default would let the gate compute a
       composite the renderer never draws and report a ratio nobody sees. */
    const alpha = (name) => {
        if (!name) return 1;
        touched.add(name);
        const raw = primitives[name] ?? aliases[name];
        const value = Number.parseFloat(raw);
        if (!raw || !Number.isFinite(value)) {
            failures += 1;
            checks += 1;
            console.log(`  FAIL     missing  declared as a bare number        ${name}`);
            return null;
        }
        return value;
    };

    console.log(`\n${"=".repeat(96)}\n${theme.toUpperCase()}\n${"=".repeat(96)}`);

    const canvas = colour("--va-graph-canvas");
    const plate = colour("--va-graph-plate");
    const ring = colour("--va-graph-focus-ring");
    if (!canvas || !plate || !ring) {
        console.log("  the canvas, the plate or the ring is unresolvable; the rest cannot be measured");
        continue;
    }

    /* --- 1. the eleven names, the nine values ---------------------------------- */
    console.log("\n-- the nine values under eleven names");
    const fills = {};
    for (const g of GROUPS) {
        const c = colour(`--va-group-${g}-fill`);
        if (c) fills[g] = c;
    }
    const distinct = new Map();
    for (const [g, c] of Object.entries(fills)) {
        const key = c.join(",");
        distinct.set(key, [...(distinct.get(key) ?? []), g]);
    }
    record(
        `${GROUPS.length} group names resolve to ${distinct.size} distinct values`,
        distinct.size,
        (v) => v === 9,
        "exactly 9",
        "",
    );

    /* --- 2. the ALIASED declaration -------------------------------------------- */
    console.log("\n-- the declared alias");
    const aliasLine = /\/\*\s*ALIASED:\s*([\w\s-]+?)\s*->\s*(--[\w-]+)/.exec(themeCss);
    if (!aliasLine) {
        failures += 1;
        checks += 1;
        console.log("  FAIL     missing  an /* ALIASED: a b -> --target */ line  theme.css");
    } else {
        const [, namesRaw, target] = aliasLine;
        const names = namesRaw.trim().split(/\s+/);
        touched.add(target);
        const targetValue = resolve(aliases[target]);
        record(`ALIASED names -> ${target}`, names.join(" "), () => names.length >= 2, "at least 2 names", "");
        for (const g of names) {
            const token = `--va-group-${g}-fill`;
            /* The declaration text, not only the resolved value. A hand-edited literal that
               happens to match today is the drift this is here to catch: it resolves equal
               now and stops resolving equal the moment the target moves. */
            const declared = (lightDecl[token] ?? "").trim();
            record(
                `${token} is declared as var(${target})`,
                declared || "(absent)",
                (v) => v === `var(${target})`,
                `literally var(${target})`,
                "",
            );
            record(
                `${token} resolves to the target's bytes`,
                resolve(aliases[token]) ?? "(unresolved)",
                (v) => v === targetValue,
                `identical to ${targetValue}`,
                "",
            );
            /* And it must not be redeclared in .dark, where a second copy could drift. */
            record(
                `${token} is not redeclared in .dark`,
                token in darkDecl ? "redeclared" : "absent",
                (v) => v === "absent",
                "absent from .dark",
                "",
            );
        }
    }

    /* --- 3. composited fills --------------------------------------------------- */
    console.log("\n-- every fill, composited over the canvas at the alphas the renderers use");
    for (const name of IDENTIFYING) {
        const a = alpha(name);
        if (a === null) continue;
        for (const [g, c] of Object.entries(fills))
            record(
                `${g} at alpha ${a} (${name.replace("--va-graph-alpha-", "")})`,
                ratio(over(c, canvas, a), canvas),
                atLeast(3),
                "3:1, non-text",
            );
    }

    /*
     * The recessive tier, and why there is no check for it.
     *
     * The 2D view drew a second-ring node at 0.55 and the audit gated it against a measured
     * floor. Both are gone, and the arithmetic printed below is the reason: at that alpha a
     * *pure black* fill cannot reach 3:1 over the light page, so the tier was unreachable for
     * any palette and no colour decision could have rescued it. The planar renderer now draws
     * orbs opaque and recesses by size, naming, line weight and paint order.
     *
     * The proof is printed rather than deleted, because the next person to reach for opacity
     * as a recession channel needs the number in front of them.
     */
    /* Stated for the light theme only. In the dark theme "a pure black fill" is the page, so
       the same sentence would print 1.08:1 and read as a catastrophe rather than as a bound. */
    const proofAlpha = 0.55;
    if (theme === "light")
        console.log(
        `
-- why opacity is not a recession channel here
` +
            `  note              a pure black fill at alpha ${proofAlpha} over this canvas reaches ` +
            `${ratio(over([0, 0, 0], canvas, proofAlpha), canvas).toFixed(2)}:1, and the nine fills reach ` +
            `${Math.min(...Object.values(fills).map((c) => ratio(over(c, canvas, proofAlpha), canvas))).toFixed(2)}` +
            `-${Math.max(...Object.values(fills).map((c) => ratio(over(c, canvas, proofAlpha), canvas))).toFixed(2)}:1`,
    );

    /* --- 4. separability ------------------------------------------------------- */
    console.log("\n-- the nine values, told apart");
    const values = [...distinct.entries()].map(([key, names]) => [names.join("/"), key.split(",").map(Number)]);
    for (let i = 0; i < values.length; i++)
        for (let j = i + 1; j < values.length; j++)
            record(
                `${values[i][0]} / ${values[j][0]}`,
                deltaE00(values[i][1], values[j][1]),
                atLeast(DE_FLOOR),
                `dE00 ${DE_FLOOR}`,
                "",
            );
    console.log("\n-- and told apart under dichromacy, severity 1.0");
    for (const kind of Object.keys(CVD)) {
        let worst = Infinity;
        let pair = "";
        for (let i = 0; i < values.length; i++)
            for (let j = i + 1; j < values.length; j++) {
                const d = deltaE00(simulate(values[i][1], kind), simulate(values[j][1], kind));
                if (d < worst) {
                    worst = d;
                    pair = `${values[i][0]} / ${values[j][0]}`;
                }
            }
        record(`${kind}: worst pair is ${pair}`, worst, atLeast(DE_CVD_FLOOR), `dE00 ${DE_CVD_FLOOR}`, "");
    }

    /* --- 5. the focus ring ---------------------------------------------------- */
    console.log("\n-- the focus ring, on the thing it marks");
    for (const name of RINGED_ALPHAS) {
        const a = alpha(name);
        if (a === null) continue;
        for (const [g, c] of Object.entries(fills))
            record(
                `ring over ${g} at alpha ${a}`,
                ratio(ring, a === 1 ? c : over(c, canvas, a)),
                atLeast(3),
                "3:1, state indicator",
            );
    }
    record("ring against the canvas it crosses", ratio(ring, canvas), atLeast(3), "3:1, non-text");

    /* --- 6. plates ------------------------------------------------------------ */
    console.log("\n-- plates, measured through the bleed rather than against themselves");
    const plateAlpha = alpha("--va-graph-alpha-plate");
    const worstFill = Object.entries(fills).reduce((a, b) =>
        ratio(a[1], canvas) > ratio(b[1], canvas) ? a : b,
    );
    const bled = plateAlpha === null ? plate : over(plate, worstFill[1], plateAlpha);
    console.log(`  note              worst fill beneath a plate here is ${worstFill[0]}`);
    for (const token of ["--va-graph-plate-ink", "--va-graph-plate-ink-quiet"]) {
        const ink = colour(token);
        if (!ink) continue;
        record(`${token} on the plate alone`, ratio(ink, plate), atLeast(4.5), "4.5:1, AA", "");
        record(`${token} through the bleed`, ratio(ink, bled), atLeast(4.5), "4.5:1, AA");
    }
    const plateEdge = colour("--va-graph-plate-edge");
    if (plateEdge) {
        record("plate edge against the plate", ratio(plateEdge, plate), atLeast(3), "3:1, non-text");
        record("plate edge against the canvas", ratio(plateEdge, canvas), atLeast(3), "3:1, non-text");
    }

    /* --- 7. canvas labels ----------------------------------------------------- */
    console.log("\n-- canvas labels, on the halo they are stroked onto");
    const halo = colour("--va-graph-label-halo");
    if (halo) {
        record(
            "the halo is the canvas colour, not a literal",
            halo.join(",") === canvas.join(",") ? "canvas" : `#${halo.map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`,
            (v) => v === "canvas",
            "equal to --va-graph-canvas",
            "",
        );
        for (const token of ["--va-graph-label-ink", "--va-graph-label-ink-quiet"]) {
            const ink = colour(token);
            if (ink) record(token, ratio(ink, halo), atLeast(4.5), "4.5:1, AA");
        }
    }

    /* --- 8. edges and relations ----------------------------------------------- */
    console.log("\n-- edges and relations");
    const restAlpha = alpha("--va-graph-alpha-edge-rest");
    const edgeQuiet = colour("--va-graph-edge-quiet");
    if (edgeQuiet && restAlpha !== null) {
        /* Two-sided. One resting edge must stay sub-threshold or 185,693 of them become a
           wash; the accumulation must not vanish or the structure is not drawn at all. */
        record("one resting edge", ratio(over(edgeQuiet, canvas, restAlpha), canvas), below(1.15), "under 1.15:1, quiet");
        const sixDeep = 1 - (1 - restAlpha) ** 6;
        record(
            `six crossings (effective alpha ${sixDeep.toFixed(3)})`,
            ratio(over(edgeQuiet, canvas, sixDeep), canvas),
            atLeast(1.15),
            "at least 1.15:1, visible",
        );
    }
    const bridge = colour("--va-graph-edge-bridge");
    if (bridge) {
        record("a bridge as an opaque stroke", ratio(bridge, canvas), atLeast(3), "3:1, non-text");
        let minAlpha = null;
        for (let a = 1; a <= 100; a += 1)
            if (ratio(over(bridge, canvas, a / 100), canvas) >= 3) {
                minAlpha = a / 100;
                break;
            }
        console.log(
            `  note              a bridge holds 3:1 from alpha ${minAlpha === null ? "never" : minAlpha.toFixed(2)} upward; ` +
                "the bridge renderer owns that alpha",
        );
    }
    const primary = colour("--va-graph-relation-primary");
    if (primary) {
        record("relation-primary against the canvas", ratio(primary, canvas), atLeast(3), "3:1, non-text");
        if (fills.deity)
            record(
                "relation-primary told apart from the deity fill",
                deltaE00(primary, fills.deity),
                atLeast(DE_MARK_FLOOR),
                `dE00 ${DE_MARK_FLOOR}`,
                "",
            );
    }
    const secondary = colour("--va-graph-relation-secondary");
    if (secondary)
        /* The only two-sided colour gate here. "Present but not asserted" has a ceiling as
           well as a floor, and a one-sided floor would let someone raise it to 3:1 and delete
           the distinction while the gate applauded. */
        record(
            "relation-secondary: present, not asserted",
            ratio(secondary, canvas),
            within(2, 3),
            "2.0:1 <= r < 3.0:1",
        );
    const hover = colour("--va-graph-relation-hover");
    if (hover) {
        record("relation-hover against the canvas", ratio(hover, canvas), atLeast(3), "3:1, non-text");
        record(
            "relation-hover told apart from the focus ring",
            deltaE00(hover, ring),
            atLeast(DE_MARK_FLOOR),
            `dE00 ${DE_MARK_FLOOR}`,
            "",
        );
    }

    /* --- 9. paths ------------------------------------------------------------- */
    console.log("\n-- the path, and its three stops");
    const pathStrong = colour("--va-graph-path-strong");
    const stops = ["--va-graph-path-stop-1", "--va-graph-path-stop-2", "--va-graph-path-stop-3"].map(colour);
    if (pathStrong) {
        record("path-strong against the canvas", ratio(pathStrong, canvas), atLeast(3), "3:1, non-text");
        let worst = Infinity;
        let which = "";
        for (const [g, c] of Object.entries(fills)) {
            const d = deltaE00(pathStrong, c);
            if (d < worst) {
                worst = d;
                which = g;
            }
        }
        record(`path-strong told apart from every fill (nearest ${which})`, worst, atLeast(DE_MARK_FLOOR), `dE00 ${DE_MARK_FLOOR}`, "");
    }
    const ramp = [pathStrong, ...stops].filter(Boolean);
    stops.forEach((c, i) => {
        if (c) record(`path-stop-${i + 1} against the canvas`, ratio(c, canvas), atLeast(3), "3:1, non-text");
    });
    for (let i = 0; i + 1 < ramp.length; i++)
        record(`ramp step ${i} -> ${i + 1} is a step`, deltaE00(ramp[i], ramp[i + 1]), atLeast(DE_MARK_FLOOR), `dE00 ${DE_MARK_FLOOR}`, "");

    /* --- 10. orbs ------------------------------------------------------------- */
    console.log("\n-- orbs");
    const keyline = colour("--va-graph-orb-keyline");
    if (keyline)
        for (const [g, c] of Object.entries(fills))
            record(`orb keyline over ${g}`, ratio(keyline, c), atLeast(3), "3:1, non-text");
    const sheen = colour("--va-graph-orb-sheen");
    const sheenAlpha = alpha("--va-graph-alpha-orb-sheen");
    if (sheen && sheenAlpha !== null)
        /* Upper bound only. A sheen that reaches 3:1 is a second keyline, and a reader with two
           keylines cannot tell which one means "selected". */
        for (const [g, c] of Object.entries(fills))
            record(
                `sheen over ${g} at alpha ${sheenAlpha}`,
                ratio(over(sheen, c, sheenAlpha), c),
                below(2),
                "under 2:1, not a keyline",
            );
}

/* ------------------------------------------------------------- coverage - */

/*
 * The half a validator usually skips.
 *
 * audit-contrast.mjs reported "all pass" over 198 pairs while four painted fills sat under
 * 3:1, because coverage was never measured - only the pairs someone had thought to list.
 * Every declared token in these two namespaces is enumerated here and has to have been
 * measured above. A new token is therefore a gate failure until it is given a criterion,
 * which is the only way a measurement list stays honest as the palette grows.
 */
console.log(`\n${"=".repeat(96)}\ncoverage\n${"=".repeat(96)}`);
const declaredAll = new Set(
    [...Object.keys(lightDecl), ...Object.keys(darkDecl), ...Object.keys(primitives)].filter(
        (n) => n.startsWith("--va-graph-") || n.startsWith("--va-group-"),
    ),
);
const unchecked = [...declaredAll].filter((n) => !touched.has(n)).sort();
const RETIRED = [...declaredAll].filter((n) => n.endsWith("-text")).sort();
console.log(`  ${declaredAll.size} graph and group tokens declared, ${touched.size} measured`);
checks += 1;
if (unchecked.length) {
    failures += 1;
    console.log(`  FAIL  ${unchecked.length} declared token(s) that no check above measures:`);
    for (const n of unchecked) console.log(`          ${n}`);
    console.log("        Give each one a criterion here, or delete it. An unmeasured token is");
    console.log("        how this suite last reported a clean run over four failing fills.");
} else {
    console.log("  pass  every declared graph and group token is measured by a check above");
}
checks += 1;
if (RETIRED.length) {
    failures += 1;
    console.log(`  FAIL  ${RETIRED.length} retired --va-group-*-text token(s) have come back:`);
    for (const n of RETIRED) console.log(`          ${n}`);
    console.log("        22 of these were declared and read by nothing. They existed only to be");
    console.log("        audited, and the audit of them is what hid the fills that were painted.");
} else {
    console.log("  pass  the 22 retired --va-group-*-text tokens are still gone");
}

console.log(
    `\n${checks} checks, ${failures} failing. ` +
        (failures
            ? "Each FAIL above prints the value it measured; fix the value or state a new floor with its measurement."
            : "Every number above was measured from theme.css and tokens.css as they stand."),
);
process.exit(failures ? 1 : 0);
