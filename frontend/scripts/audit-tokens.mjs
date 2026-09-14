#!/usr/bin/env node
/**
 * Every `--va-*` token read without a fallback must be declared somewhere.
 *
 * This exists because the failure it catches is silent. `var(--missing)` with no fallback is
 * *invalid at computed-value time*: the declaration is not ignored at parse time, so nothing
 * warns, and the property falls back to its inherited value or its initial value instead. A
 * heading set in a font token that does not exist renders in the body face and looks
 * deliberate. A `calc()` on a missing length collapses a margin to zero and the gap it was
 * drawing simply is not there.
 *
 * That has now happened three times in this rebuild - once when a font variable was deleted
 * rather than re-pointed, and twice in stylesheets written against token names that were
 * plausible but never existed (`--va-measure-body`, `--va-leading-relaxed`). None of the three
 * failed a build, a typecheck or a lint.
 *
 * Tokens set at runtime by a component's inline `style` are declared in TSX rather than CSS,
 * so the TSX is scanned for those too instead of maintaining a hand-written allowlist.
 */

import { readFile, readdir } from "node:fs/promises";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const CSS_DIRS = [join(ROOT, "src", "styles")];
const CSS_EXTRA = [join(ROOT, "src", "app", "globals.css")];
const TSX_DIR = join(ROOT, "src");

async function walk(dir, test) {
    const out = [];
    for (const entry of await readdir(dir, { withFileTypes: true })) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) out.push(...(await walk(path, test)));
        else if (test(entry.name)) out.push(path);
    }
    return out;
}

const cssFiles = [
    ...(await Promise.all(CSS_DIRS.map((d) => walk(d, (n) => n.endsWith(".css"))))).flat(),
    ...CSS_EXTRA,
];
const tsxFiles = await walk(TSX_DIR, (n) => n.endsWith(".tsx") || n.endsWith(".ts"));

const declared = new Set();
const used = new Map();
const withFallback = new Map();

for (const file of cssFiles) {
    const source = await readFile(file, "utf8");
    for (const [, name] of source.matchAll(/(--va-[a-z0-9-]+)\s*:/g)) declared.add(name);
    for (const match of source.matchAll(/var\(\s*(--va-[a-z0-9-]+)\s*([,)])/g)) {
        const at = source.slice(0, match.index).split("\n").length;
        const site = `${relative(ROOT, file)}:${at}`;
        /*
         * A read with a fallback cannot fail the way an undeclared read does, but in a token
         * layer that is meant to declare every `--va-*` name it fails a quieter way: the
         * fallback makes an invented name look deliberate, and the rule resolves to the wrong
         * value for good without ever warning. That is how `--va-accent-strong` got written
         * into a hover state here; it had never existed, and the page simply used the fallback.
         * So both forms are collected, and they are reported separately.
         */
        const bucket = match[2] === ")" ? used : withFallback;
        bucket.set(match[1], [...(bucket.get(match[1]) ?? []), site]);
    }
}

/* A token a component sets through inline style is declared, just not in a stylesheet. */
for (const file of tsxFiles) {
    const source = await readFile(file, "utf8");
    for (const [, name] of source.matchAll(/["'](--va-[a-z0-9-]+)["']\s*:/g)) declared.add(name);
}

const missing = [...used].filter(([name]) => !declared.has(name));
const invented = [...withFallback].filter(([name]) => !declared.has(name));

if (missing.length === 0 && invented.length === 0) {
    console.log(`tokens: ${used.size + withFallback.size} distinct --va-* reads, all declared.`);
    process.exit(0);
}

if (missing.length) {
    console.error(`tokens: ${missing.length} undeclared token(s) read without a fallback.\n`);
    for (const [name, sites] of missing) {
        console.error(`  ${name}`);
        for (const site of sites) console.error(`      ${site}`);
    }
    console.error("\nEach of these silently falls back to the inherited or initial value.");
}

if (invented.length) {
    console.error(`\ntokens: ${invented.length} undeclared token(s) read behind a fallback.\n`);
    for (const [name, sites] of invented) {
        console.error(`  ${name}`);
        for (const site of sites) console.error(`      ${site}`);
    }
    console.error(
        "\nThese never fail, which is the problem: the fallback is what renders, for good.\n" +
            "Either declare the token or write the value the fallback was standing in for.",
    );
}

process.exit(1);
