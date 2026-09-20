/**
 * Refuses a `va-` class that two stylesheets both define.
 *
 *   node scripts/audit-class-owner.mjs
 *
 * The companion to `audit-class-collisions.mjs`, and it exists because that check is
 * necessary and not sufficient. That one compares the four properties that decide what kind
 * of box an element is, and only reports a name when two sheets disagree about one of them.
 *
 * The way that is insufficient was found by walking into it during this phase. A new sheet
 * reused `.va-figure-note`, a name the Lab already owned. Both definitions are ordinary
 * static blocks, so `display`, `position` and `overflow` all agreed and the box-model check
 * passed - while the Lab's `border-top` and `padding-top` were applied to a paragraph on the
 * formula index that wanted neither. It rendered as a stray rule hanging off a heading, and
 * nothing in the build said a word.
 *
 * So: a `va-` name may be *owned* by one stylesheet and one only, where owned means defined
 * by an unscoped selector. This is stricter, and it is the rule the namespace actually
 * needs. The ten sheets are unlayered and share one flat namespace, so a class name is a
 * global; two sheets defining one global is a bug whatever they happen to disagree about.
 *
 * A descendant selector is not ownership. `.va-lab .va-rank { ... }` is one surface
 * adjusting an element inside itself, which is what a descendant selector is for.
 */
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SHEETS = path.join(ROOT, "..", "src", "styles");
const GLOBALS = path.join(ROOT, "..", "src", "app", "globals.css");

/**
 * Names more than one sheet may define, each with the reason it is not a collision.
 *
 * Deliberately short, and grandfathered rather than endorsed. Every entry is one component
 * whose rules were split across two files before this gate existed. A new name does not go
 * in this list; it gets renamed.
 */
const SHARED = new Map([
    ["va-graph", "the graph stage: set up in graph.css, adjusted in shell.css"],
    ["va-world-ways", "one block, defined in graph.css and tuned in world.css"],
    [
        "va-sanskrit-inline",
        "the inline Sanskrit face: base.css defines it, register.css binds it to a register name",
    ],
]);

const files = [
    ...(await readdir(SHEETS))
        .filter((name) => name.endsWith(".css"))
        .map((name) => path.join(SHEETS, name)),
    GLOBALS,
];

/** class name -> the sheets whose unscoped selectors define it. */
const owners = new Map();

for (const file of files) {
    const label = path.basename(file);
    const css = (await readFile(file, "utf8")).replace(/\/\*[\s\S]*?\*\//g, "");
    /*
     * The selector group must not consume the previous rule's closing brace. An earlier
     * version of the sibling check anchored on `(^|[{}])`, and because `matchAll` cannot
     * overlap it silently skipped every second rule. Same shape, same trap.
     */
    for (const match of css.matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
        for (const selector of match[1].split(",")) {
            const trimmed = selector.trim();
            if (!trimmed || trimmed.startsWith("@")) continue;
            if (/[\s>+~]/.test(trimmed)) continue;
            for (const [, name] of trimmed.matchAll(/\.(va-[a-z0-9-]+)/g)) {
                owners.set(name, (owners.get(name) ?? new Set()).add(label));
            }
        }
    }
}

const shared = [...owners.entries()]
    .filter(([name, sheets]) => sheets.size > 1 && !SHARED.has(name))
    .map(([name, sheets]) => ({ name, sheets: [...sheets].sort() }))
    .sort((a, b) => a.name.localeCompare(b.name));

if (shared.length === 0) {
    console.log(
        `One owner per name across ${files.length} stylesheets ` +
            `(${owners.size} names, ${SHARED.size} shared by exception).`,
    );
    process.exit(0);
}

console.error(`${shared.length} class name(s) are defined in more than one stylesheet:\n`);
for (const { name, sheets } of shared) {
    console.error(`  .${name}  ${sheets.join(", ")}`);
}
console.error(
    "\nThe sheets are unlayered, so a name is a global and the later import silently wins\n" +
        "every property the earlier one set. Rename the newer of the two.",
);
process.exit(1);
