/**
 * Refuses a `va-` class whose box model is defined twice, differently, in two stylesheets.
 *
 *   node scripts/audit-class-collisions.mjs
 *
 * The design system is ten unlayered stylesheets sharing one flat namespace, and the last one
 * imported wins. That is fine until two surfaces independently reach for the same obvious
 * word, at which point one of them silently gets the other's layout. Silently is the problem:
 * both collisions this check was written for rendered without a console warning, a build error
 * or a horizontal scrollbar.
 *
 *   `.va-plate`   the homepage's featured-verse plate is `display: grid; place-items: center;
 *                 overflow: clip`. The Lab reused the name for its page wrapper, so every plate
 *                 was laid out inside a centring grid that sized its children to max-content
 *                 and then clipped them. At 390px the page head was 666px wide with its right
 *                 third cut off, and nothing reported it.
 *
 *   `.va-bars`    the homepage's recitation bars are `display: grid`. The Lab reused the name
 *                 for a table, so `display: grid` replaced `display: table` and every row shrank
 *                 to its content: a 632px table drawing 290px rows, with the bar scale wrong.
 *
 * Only the four properties that decide what kind of box an element is are checked, and only
 * when two sheets give the same class *different* values for one of them. A second sheet that
 * adjusts colour, spacing or type on a class the first defined is ordinary cascade and is not a
 * finding -- `.va-sanskrit` is set up in base.css and tuned in home.css on purpose.
 *
 * A name is only owned by an unscoped selector. `.va-lab .va-rank { ... }` is one surface
 * adjusting an element inside itself, which is what a descendant selector is for.
 */
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SHEETS = path.join(ROOT, "..", "src", "styles");
const GLOBALS = path.join(ROOT, "..", "src", "app", "globals.css");

/** What kind of box this is. Disagreeing on any of these is a different element, not a tweak. */
const STRUCTURAL = ["display", "position", "overflow", "overflow-x"];

/** `.va-x` → the structural declarations this stylesheet makes about it. */
function structuralClaims(css) {
    const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
    const claims = new Map();
    /*
     * The selector group must not consume the previous rule's closing brace.
     *
     * An earlier version anchored on `(^|[{}])` and, because `matchAll` cannot overlap,
     * silently skipped every second rule -- including both of the collisions above. A
     * validator that passes by not looking is worse than no validator, so this one is
     * verified against a deliberately reintroduced collision.
     */
    for (const match of stripped.matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
        const [, selectorList, body] = match;
        const declared = new Map();
        for (const property of STRUCTURAL) {
            const found = body.match(new RegExp(`(?:^|;)\\s*${property}\\s*:\\s*([^;]+)`, "i"));
            if (found) declared.set(property, found[1].trim());
        }
        if (declared.size === 0) continue;

        for (const selector of selectorList.split(",")) {
            const trimmed = selector.trim();
            if (!trimmed || trimmed.startsWith("@")) continue;
            /*
             * Only an unscoped selector claims ownership.
             *
             * `.va-reader-skeleton .va-reader-where { display: grid }` is one surface saying
             * what that element looks like *inside its own skeleton*, which is exactly what a
             * descendant selector is for. Counting it as a second owner reported the reader's
             * loading state as a collision with the reader itself.
             */
            if (/[\s>+~]/.test(trimmed)) continue;
            for (const [, name] of trimmed.matchAll(/\.(va-[a-z0-9-]+)/g)) {
                const existing = claims.get(name) ?? new Map();
                for (const [property, value] of declared) existing.set(property, value);
                claims.set(name, existing);
            }
        }
    }
    return claims;
}

const files = [
    ...(await readdir(SHEETS))
        .filter((name) => name.endsWith(".css"))
        .map((name) => path.join(SHEETS, name)),
    GLOBALS,
];

/** class → property → value → the sheets that said it. */
const seen = new Map();
for (const file of files) {
    const label = path.basename(file);
    for (const [name, declared] of structuralClaims(await readFile(file, "utf8"))) {
        const byProperty = seen.get(name) ?? new Map();
        for (const [property, value] of declared) {
            const byValue = byProperty.get(property) ?? new Map();
            byValue.set(value, [...(byValue.get(value) ?? []), label]);
            byProperty.set(property, byValue);
        }
        seen.set(name, byProperty);
    }
}

const collisions = [];
for (const [name, byProperty] of seen) {
    for (const [property, byValue] of byProperty) {
        const sheets = new Set([...byValue.values()].flat());
        if (byValue.size > 1 && sheets.size > 1) {
            collisions.push({ name, property, byValue });
        }
    }
}
collisions.sort((a, b) => a.name.localeCompare(b.name));

if (collisions.length === 0) {
    console.log(`No box-model collisions across ${files.length} stylesheets (${seen.size} names).`);
    process.exit(0);
}

console.error(`${collisions.length} class name(s) are given a different box in two stylesheets:\n`);
for (const { name, property, byValue } of collisions) {
    const described = [...byValue.entries()]
        .map(([value, sheets]) => `${value} (${[...new Set(sheets)].join(", ")})`)
        .join("  vs  ");
    console.error(`  .${name}  ${property}:  ${described}`);
}
console.error(
    "\nThe later import wins and the earlier surface changes shape without any error. Rename one.",
);
process.exit(1);
