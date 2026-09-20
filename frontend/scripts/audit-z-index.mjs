/**
 * Refuses a numeric `z-index` written anywhere but the token scale.
 *
 *   node scripts/audit-z-index.mjs
 *
 * A bare integer in a stylesheet is a claim about what that element sits above, and nothing
 * in the build can check it. Before this gate the product held nine of them across five
 * sheets: the header at 40, the dialog overlay at 60, the drawer and the mobile nav panel
 * both at 61, and the skip link at 100 -- which put the one control a keyboard user needs
 * *above* the modal it was supposed to escape only because 100 happens to exceed 61. That
 * ordering was luck. Six more were local layer numbers (-1, 0, 1, 2, 3) inside components
 * that isolate, and they were indistinguishable, in a grep, from the page rungs.
 *
 * So there are two scales in `tokens.css` and this check enforces that every author reaches
 * for one of them:
 *
 *   --va-z-beneath | ground | content | annotation | panel   inside one isolated component
 *   --va-z-base | raised | sticky | overlay | modal | toast | skip   across the page
 *
 * The declarations *in* the token block are the definition and are skipped. Everything else
 * must read `z-index: var(--va-z-...)`. `inherit`, `initial`, `unset` and `revert` are
 * allowed: they assert nothing.
 *
 * TSX is checked too, for `zIndex` in an inline style object. There are none today, and a
 * sheet-only gate would not have noticed the first.
 */
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, "..", "src");
const TOKENS = path.join(SRC, "styles", "tokens.css");

/** Every .css and .tsx under src, as absolute paths. */
async function walk(dir) {
    const found = [];
    for (const entry of await readdir(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) found.push(...(await walk(full)));
        else if (/\.(css|tsx|ts)$/.test(entry.name)) found.push(full);
    }
    return found;
}

const KEYWORD = /^(auto|inherit|initial|unset|revert|revert-layer)$/;

const findings = [];
for (const file of await walk(SRC)) {
    const label = path.relative(path.join(ROOT, ".."), file).replace(/\\/g, "/");
    const source = await readFile(file, "utf8");
    const lines = source.split("\n");

    lines.forEach((line, i) => {
        // The token definitions themselves are the scale. Nothing else in that file declares one.
        if (file === TOKENS) return;
        // A comment discussing z-index is not a declaration.
        const code = line.replace(/\/\*.*?\*\//g, "").replace(/^\s*\/\/.*/, "");

        const css = code.match(/(?:^|[;{\s])z-index\s*:\s*([^;}]+)/i);
        if (css) {
            const value = css[1].trim();
            if (!value.startsWith("var(--va-z-") && !KEYWORD.test(value)) {
                findings.push({ file: label, line: i + 1, value, text: line.trim() });
            }
        }

        const jsx = code.match(/\bzIndex\s*:\s*([^,}]+)/);
        if (jsx) {
            const value = jsx[1].trim();
            if (!/var\(--va-z-/.test(value)) {
                findings.push({ file: label, line: i + 1, value, text: line.trim() });
            }
        }
    });
}

if (findings.length === 0) {
    console.log("No raw z-index outside the token scale.");
    process.exit(0);
}

console.error(`${findings.length} raw z-index value(s) outside the token scale:\n`);
for (const { file, line, value } of findings) {
    console.error(`  ${file}:${line}  z-index: ${value}`);
}
console.error(
    "\nUse a rung from tokens.css: --va-z-beneath/ground/content/annotation/panel inside an\n" +
        "isolated component, or --va-z-base/raised/sticky/overlay/modal/toast/skip across the page.",
);
process.exit(1);
