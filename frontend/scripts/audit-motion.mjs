/**
 * Enforces the motion law: nothing animates on a timer, and nothing loops.
 *
 *   node scripts/audit-motion.mjs
 *
 * The law is in `src/styles/thread.css`: NO MOTION MAY ASSERT WHAT THE DATA DOES NOT, and
 * only three verbs move anything - RESOLVE, DRAW, ADVANCE. All three are either one-shot on
 * entry or driven by a real progress value. None of them repeats.
 *
 * This phase added a horizontal moving-text moment to the homepage, which is the single
 * pattern most likely to decay into a marquee the next time someone touches it. A marquee is
 * motion with no referent: it says "this is alive" about data that is not doing anything, it
 * cannot be read at its own speed, and it never stops. So the gate is written now, while the
 * thing it guards is one commit old.
 *
 * ## What is refused
 *
 *   `animation-iteration-count: infinite`, and the `infinite` keyword inside an `animation`
 *   shorthand, outside the allowlist below. Two spinners and one shimmer are genuinely
 *   indefinite - they run while a request the product cannot bound is in flight, and they
 *   stop when it lands - so they are named, with the state each one reports.
 *
 *   `<marquee>`, which is obsolete and would not be an accident.
 *
 *   `setInterval` driving a style, transform or scroll position. A scroll animated on a
 *   timer is a marquee with extra steps.
 *
 * ## What is not refused
 *
 *   `animation-timeline: view()` and `scroll()`. Both are driven by the reader's own scroll
 *   position, which means they are still when the reader is, and they are the mechanism the
 *   archive register uses instead of a timer.
 */
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, "..", "src");

/**
 * Indefinite animations that are allowed, each with the pending state it reports.
 *
 * The rule for adding one: it must be bound to a request or a process whose duration the
 * product genuinely cannot know, and it must stop when that ends. "It looks nice" is not on
 * the list and will not be.
 */
const ALLOWED = new Map([
    ["va-spin", "the Ask spinner, while a generation the product cannot bound is in flight"],
    ["va-shimmer", "a skeleton row, while its request is open"],
    ["va-pulse", "the recitation player's buffering state"],
    ["spin", "the legacy spinner in globals.css, same contract as va-spin"],
    ["shimmer", "the legacy skeleton shimmer in globals.css"],
    ["pulse", "the legacy pending pulse in globals.css"],
    ["va-graph-pulse", "the graph's own loading state, while the 2 MB artifact is fetched"],
    ["va-inquiry-pass", "the Ask shuttle, while a multi-minute generation is in flight"],
    ["ask-pulse", "the active phase dot on the Ask progress list, while that phase runs"],
]);

async function walk(dir) {
    const found = [];
    for (const entry of await readdir(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) found.push(...(await walk(full)));
        else if (/\.(css|tsx|ts)$/.test(entry.name)) found.push(full);
    }
    return found;
}

const findings = [];

for (const file of await walk(SRC)) {
    const label = path.relative(path.join(ROOT, ".."), file).replace(/\\/g, "/");
    const source = await readFile(file, "utf8");
    /*
     * Comments are blanked before the line scan, across lines as well as within one.
     *
     * A per-line strip only catches a comment that opens and closes on the same line, so the
     * sentence in `thread.css` that explains this gate refuses an infinite animation was
     * itself reported as one - a validator failing on its own documentation. Replacing every
     * character of a comment with a space keeps every line number below intact.
     */
    const stripped = source.replace(/\/\*[\s\S]*?\*\//g, (block) => block.replace(/[^\n]/g, " "));
    const lines = stripped.split("\n");
    const rawLines = source.split("\n");

    lines.forEach((code, i) => {
        const line = rawLines[i] ?? code;
        const at = { file: label, line: i + 1, text: line.trim().slice(0, 120) };

        if (/<marquee/i.test(code)) {
            findings.push({ ...at, why: "the <marquee> element is obsolete and never correct" });
        }

        if (/\binfinite\b/.test(code)) {
            /*
             * Which keyframes this line animates. Taken from the same line, because both the
             * shorthand and the longhand put the name and the count together in practice -
             * and a name split across two declarations would be worth a finding anyway.
             */
            const named = [...code.matchAll(/([a-z][a-z0-9-]*)/gi)].map((m) => m[1]);
            const allowed = named.find((name) => ALLOWED.has(name));
            if (!allowed) {
                findings.push({
                    ...at,
                    why: "an animation that never ends. Bind it to a real state or drop it",
                });
            }
        }

        /*
         * A timer that writes a style. `setInterval` for polling a request is fine and
         * common; `setInterval` that moves something is a marquee.
         */
        if (/setInterval/.test(code) && /(style|transform|scrollLeft|scrollTo|translate)/.test(code)) {
            findings.push({ ...at, why: "motion driven by a timer rather than by real progress" });
        }
    });

    /*
     * `setInterval` whose body touches a style, across lines.
     *
     * The single-line test above catches the compact form. This catches the block form,
     * which is the one a scrolling ticker is actually written in.
     */
    for (const match of source.matchAll(/setInterval\(\s*\(\s*\)\s*=>\s*\{([\s\S]{0,400}?)\}/g)) {
        if (/(\.style\.|scrollLeft|scrollTo|translateX)/.test(match[1])) {
            const line = source.slice(0, match.index).split("\n").length;
            findings.push({
                file: label,
                line,
                text: "setInterval body writes a style or a scroll position",
                why: "motion driven by a timer rather than by real progress",
            });
        }
    }
}

if (findings.length === 0) {
    console.log(
        `No timer-driven or looping motion (${ALLOWED.size} indefinite animations allowed by name).`,
    );
    process.exit(0);
}

console.error(`${findings.length} motion finding(s):\n`);
for (const { file, line, why, text } of findings) {
    console.error(`  ${file}:${line}  ${why}`);
    console.error(`    ${text}`);
}
console.error(
    "\nSee the motion law at the head of src/styles/thread.css. Motion here is RESOLVE, DRAW\n" +
        "or ADVANCE: one-shot on entry, or driven by a progress value that is real.",
);
process.exit(1);
