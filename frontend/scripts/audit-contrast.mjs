/**
 * Check every VedAnvaya colour token against every surface it can legally be painted on.
 *
 * The end-to-end suite already walks the rendered DOM and resolves the nearest opaque painted
 * ancestor, which is the only way to catch what a page actually does. This is the other half:
 * it checks the token system itself, before a page is built out of it, so a token that cannot
 * pass is caught where it is defined rather than wherever it first happens to be used.
 *
 * It exists because it was needed. Phase 2 set `--va-text-tertiary` to a value whose stated
 * ratio was measured against the page background alone; on the sunk and strong surfaces the
 * same token landed at 4.44 and 3.94, and eight separate assertions went red at once in
 * places that had nothing to do with each other.
 *
 * Run: node scripts/audit-contrast.mjs
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const THEME = path.join(here, "..", "src", "styles", "theme.css");
const TOKENS = path.join(here, "..", "src", "styles", "tokens.css");

/** WCAG 2.1 relative luminance. */
function luminance(hex) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function ratio(a, b) {
    const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
}

/** Resolve `var(--x)` chains within one theme block down to a literal hex. */
function resolver(primitives, aliases) {
    const seen = new Set();
    return function resolve(value) {
        let current = value.trim();
        while (current.startsWith("var(")) {
            const name = current.slice(4, current.indexOf(")")).trim();
            if (seen.has(name)) return null;
            seen.add(name);
            current = (aliases[name] ?? primitives[name] ?? "").trim();
            if (!current) return null;
        }
        seen.clear();
        return /^#[0-9a-f]{6}$/i.test(current) ? current : null;
    };
}

function declarations(css, blockStart) {
    const start = css.indexOf(blockStart);
    if (start < 0) return {};
    const open = css.indexOf("{", start);
    let depth = 0;
    let end = open;
    for (let i = open; i < css.length; i++) {
        if (css[i] === "{") depth++;
        if (css[i] === "}" && --depth === 0) {
            end = i;
            break;
        }
    }
    const body = css.slice(open + 1, end);
    const out = {};
    for (const m of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
    return out;
}

/*
 * The compatibility shim in globals.css is audited too, not only the new tokens.
 *
 * 952 rule blocks still consume --ink, --muted, --faint and the rest, so an alias pointing at
 * an unthemed primitive is a dark-mode failure that a check of the new names alone cannot
 * see. --ink-soft did exactly that: it resolved to carbon-700 in both themes and painted
 * near-black text on the carbon page at 1.69:1.
 */
const GLOBALS = path.join(here, "..", "src", "app", "globals.css");
const shim = declarations(readFileSync(GLOBALS, "utf8"), ":root {");
const SHIM_TEXT = ["--ink", "--ink-soft", "--muted", "--faint"];
const SHIM_SURFACES = ["--bg", "--surface", "--surface-sunk", "--surface-strong"];

const themeCss = readFileSync(THEME, "utf8");
const primitives = declarations(readFileSync(TOKENS, "utf8"), "@theme static");
const light = declarations(themeCss, ":root {");
const dark = declarations(themeCss, ".dark {");

/**
 * Which foregrounds may be painted on which surfaces.
 *
 * Not every combination: a token painted somewhere it is never painted would produce noise
 * that teaches people to ignore the report. These are the pairings the stylesheets actually
 * produce, plus the ones a new surface would reasonably reach for.
 */
const SURFACES = ["--va-surface-page", "--va-surface-raised", "--va-surface-sunk", "--va-surface-strong"];
const TEXT = [
    "--va-text-primary",
    "--va-text-strong",
    "--va-text-secondary",
    "--va-text-tertiary",
    "--va-accent-text",
];
const TONE_PAIRS = [
    ["--va-tone-evidenced", "--va-tone-evidenced-surface"],
    ["--va-tone-partial", "--va-tone-partial-surface"],
    ["--va-tone-insufficient", "--va-tone-insufficient-surface"],
    ["--va-tone-unbuilt", "--va-tone-unbuilt-surface"],
    ["--va-tone-neutral", "--va-tone-neutral-surface"],
];
/* All eleven semantic groups the graph can render, not only the ones a given root happens to
   produce. The end-to-end suite injects the missing chips for the same reason. */
const GROUPS = [
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
].map((g) => `--va-group-${g}-text`);

/** Body text and anything under 18.66px needs 4.5. Large text needs 3. Nothing here is large. */
const AA = 4.5;

let failures = 0;
let checked = 0;

for (const [themeName, aliases] of [
    ["light", { ...light }],
    ["dark", { ...light, ...dark }],
]) {
    const resolve = resolver(primitives, aliases);
    const rows = [];

    const check = (fgName, bgName, minimum = AA) => {
        const fg = resolve(aliases[fgName] ?? "");
        const bg = resolve(aliases[bgName] ?? "");
        if (!fg || !bg) {
            rows.push(["?", fgName, bgName, "unresolved"]);
            failures++;
            return;
        }
        checked++;
        const value = ratio(fg, bg);
        if (value < minimum) {
            failures++;
            rows.push([value.toFixed(2), fgName, bgName, `${fg} on ${bg}`]);
        }
    };

    for (const fg of TEXT) for (const bg of SURFACES) check(fg, bg);
    /* Accent text is also painted on the soft accent surface, which is what a chip uses. */
    check("--va-accent-text", "--va-accent-soft");
    check("--va-text-primary", "--va-accent-soft");
    for (const [fg, bg] of TONE_PAIRS) {
        check(fg, bg);
        // A tone is also painted straight onto the page, not only onto its own surface.
        check(fg, "--va-surface-page");
        check(fg, "--va-surface-raised");
    }
    /* Every surface, including strong: the graph legend sits on an active chip and that is
       where the end-to-end contrast walk found rite at 4.46 and thing at 4.45. */
    for (const fg of GROUPS) for (const bg of SURFACES) check(fg, bg);
    for (const fg of SHIM_TEXT)
        for (const bg of SHIM_SURFACES) {
            const merged = { ...shim, ...aliases };
            const r = resolver(primitives, merged);
            const f = r(merged[fg] ?? "");
            const b = r(merged[bg] ?? "");
            if (!f || !b) {
                rows.push(["?", fg, bg, "unresolved"]);
                failures++;
                continue;
            }
            checked++;
            const value = ratio(f, b);
            if (value < AA) {
                failures++;
                rows.push([value.toFixed(2), fg, bg, `${f} on ${b}`]);
            }
        }
    check("--va-text-on-accent", "--va-accent-base");
    check("--va-text-inverse", "--va-surface-inverse");

    console.log(`\n${themeName}: ${rows.length ? `${rows.length} failing` : "all pass"}`);
    for (const [value, fg, bg, detail] of rows) {
        console.log(`  ${String(value).padStart(5)}  ${fg.padEnd(30)} on ${bg.padEnd(30)} ${detail}`);
    }
}

console.log(`\n${checked} pairs checked, ${failures} below ${AA}:1`);
process.exit(failures ? 1 : 0);
