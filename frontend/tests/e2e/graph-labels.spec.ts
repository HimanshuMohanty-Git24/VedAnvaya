import { expect, test, type Page } from "@playwright/test";

/**
 * Nothing overlaps anything. The only gate that keeps a unified label pass honest.
 *
 * ## Why this file exists
 *
 * Subject names and relationship phrases were placed by two systems on two cadences, and the
 * second was handed the first's boxes as obstacles. That arrangement cannot express a priority
 * order, so this phase replaced it with one pass over one integer tier order - and in doing so
 * deleted two escapes that used to let a label through *in collision*: a dwell that pushed a
 * label while it overlapped, and a `tolerated` fallback that printed a phrase on top of a name.
 * Both were asserted as desired behaviour by the unit tests at the time.
 *
 * The failure mode of getting the replacement wrong is not a crash and not a thrown error. It is
 * a diagram that looks very slightly wrong to somebody who is not measuring, which is precisely
 * the class of defect a unit test on synthetic rectangles cannot catch: the unit test proves the
 * algorithm is sound given the boxes it is handed, and says nothing about whether the boxes the
 * browser paints are the boxes the algorithm was given. The name offsets used to live in the
 * stylesheet, nine pixels and half a line-height away from the rectangle that had been reserved,
 * which is exactly that gap.
 *
 * So this reads the real DOM, in both classes, and counts pairs.
 *
 * ## It measures the pad, not only the ink
 *
 * Two chips can be comfortably clear of one another in ink and still have overlapping 44 px touch
 * pads, in which case the one later in the document silently wins the tap. That has shipped twice
 * in this product - once on these labels, and once on the view and renderer control rows, where
 * pads overlapped by 15.8 px at 390 px wide and a tap inside the word "World" changed the
 * renderer. So the ink boxes are checked, and then the pads are checked, and both must be clean.
 *
 * ## It measures on the settled DOM
 *
 * This project has a recorded lesson that transitions and wrapper-held focus rings each invented
 * a defect that was not there. The label pipeline is deliberately split - per frame the view only
 * moves what is already placed, and the assignment runs on a debounced settle - so a sample taken
 * mid-flight is a sample of an intermediate state that was never meant to be collision-free.
 * `settle` below waits for two identical readings rather than for a fixed delay.
 */

const SUBJECTS = {
    Agni: "VG:DEVATA:AGNIH",
    Indra: "VG:DEVATA:INDRAH",
} as const;

/** The world is a two-megabyte artifact and a settling layout; it is not a fast page. */
const READY = 30_000;

/** One label as the browser actually painted it. */
type Painted = {
    kind: "phrase" | "name";
    /**
     * Whether this label can receive a tap at all.
     *
     * Read from the computed style rather than assumed from the class: the whole overlay is
     * `pointer-events: none` and only a shown phrase is given `auto` back, so a subject name is
     * never a tap target. That distinction is what the pad comparison below turns on.
     */
    interactive: boolean;
    text: string;
    ink: { x: number; y: number; width: number; height: number };
    pad: { x: number; y: number; width: number; height: number };
};

/**
 * Every label currently visible, in both classes, with its ink box and its pad box.
 *
 * Visibility is read from the computed opacity rather than from Playwright's `isVisible`, because
 * a label on its way out keeps its box and its transform for the 300 ms of its crossfade. Those
 * are not on screen in any sense the reader would recognise and they are not what the collision
 * pass placed, so counting them would report a defect that does not exist - which is the same
 * mistake as sampling mid-transition, one layer down.
 */
async function painted(page: Page): Promise<Painted[]> {
    return page.evaluate(() => {
        const out: Array<{
            kind: "phrase" | "name";
            interactive: boolean;
            text: string;
            ink: { x: number; y: number; width: number; height: number };
            pad: { x: number; y: number; width: number; height: number };
        }> = [];
        const nodes = document.querySelectorAll<HTMLElement>(".va-edge-label, .va-world-label");
        for (const node of nodes) {
            if (node.classList.contains("is-measuring")) continue;
            const style = getComputedStyle(node);
            if (Number(style.opacity) < 0.999) continue;
            const box = node.getBoundingClientRect();
            if (box.width === 0 || box.height === 0) continue;
            const px = (name: string) => Number.parseFloat(style.getPropertyValue(name)) || 0;
            const padX = px("--va-label-pad-x");
            const padY = px("--va-label-pad-y");
            /*
             * The painted pad, where there is one, rather than the arithmetic that asked for it.
             *
             * Deriving the box from the two custom properties reproduces the layout's own
             * rounding and therefore agrees with it by construction - so it cannot catch the
             * case where the stylesheet and the layout disagree about the size of the target.
             * It did not catch exactly that: the arithmetic said 44 and the chip painted 43.75.
             * `::after` is what a finger lands on, so `::after` is what is measured.
             */
            const painted = getComputedStyle(node, "::after");
            const paintedW = Number.parseFloat(painted.width);
            const paintedH = Number.parseFloat(painted.height);
            const hasPainted = Number.isFinite(paintedW) && Number.isFinite(paintedH) && paintedH > 0;
            out.push({
                kind: node.classList.contains("va-edge-label") ? "phrase" : "name",
                interactive: style.pointerEvents !== "none",
                text: node.textContent ?? "",
                ink: { x: box.x, y: box.y, width: box.width, height: box.height },
                pad: {
                    x: box.x - padX,
                    y: box.y - padY,
                    width: hasPainted ? paintedW : box.width + padX * 2,
                    height: hasPainted ? paintedH : box.height + padY * 2,
                },
            });
        }
        return out;
    });
}

/**
 * Wait until two consecutive readings agree.
 *
 * A fixed delay is a guess about how long a camera flight, an artifact load and a debounced
 * assignment take together on whatever machine is running the suite. Two matching readings 500 ms
 * apart is a statement about the thing being measured.
 */
async function settle(page: Page): Promise<Painted[]> {
    let previous = "";
    for (let attempt = 0; attempt < 40; attempt += 1) {
        const labels = await painted(page);
        const signature = labels
            .map((label) => `${label.kind}:${label.text}:${Math.round(label.ink.x)},${Math.round(label.ink.y)}`)
            .sort()
            .join("|");
        if (signature === previous && labels.length > 0) return labels;
        previous = signature;
        await page.waitForTimeout(500);
    }
    throw new Error("the labels never settled");
}

/**
 * Overlapping pairs, by box.
 *
 * The two boxes answer two different questions and are therefore scoped differently.
 *
 * `ink` is the visual claim and applies to every label of either class: two pieces of text over
 * one another are unreadable whether or not either is clickable.
 *
 * `pad` is a claim about taps - "the later one silently wins" - so it applies only between
 * labels that can receive one. Measured: a phrase's 44 px pad overhangs the name "Agni" by
 * 1.2 px at 390 px wide, and that cannot steal anything, because the overlay is
 * `pointer-events: none` and a name is never given it back. Asserting over that pair reports a
 * hazard the product does not have, which is the same error as asserting on the unsettled DOM -
 * a defect invented by measuring the wrong thing. The guarantee that matters, pad against pad
 * between two tap targets, is unchanged and is what shipped broken twice.
 */
function overlapping(labels: Painted[], box: "ink" | "pad"): string[] {
    const scoped = box === "pad" ? labels.filter((label) => label.interactive) : labels;
    const pairs: string[] = [];
    for (let i = 0; i < scoped.length; i += 1) {
        for (let j = i + 1; j < scoped.length; j += 1) {
            const a = scoped[i][box];
            const b = scoped[j][box];
            const dx = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
            const dy = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
            if (dx > 0.5 && dy > 0.5) {
                pairs.push(
                    `${scoped[i].kind} "${scoped[i].text}" x ${scoped[j].kind} ` +
                        `"${scoped[j].text}" overlap ${dx.toFixed(1)} x ${dy.toFixed(1)} px`,
                );
            }
        }
    }
    return pairs;
}

async function arrive(page: Page, id: string) {
    await page.goto(`/graph?view=focus&renderer=3d&node=${encodeURIComponent(id)}`);
    await expect(page.locator('.va-world[data-phase="ready"]')).toBeAttached({ timeout: READY });
    await expect(page.locator(".va-world-panel")).toBeVisible({ timeout: READY });
}

function gate(width: number, height: number, where: string) {
    test.describe(`${where}`, () => {
        test.use({ viewport: { width, height } });

        for (const [name, id] of Object.entries(SUBJECTS)) {
            test(`no two labels overlap at Focus on ${name}`, async ({ page }) => {
                await arrive(page, id);
                const labels = await settle(page);

                /* A count-zero assertion that passes because the locator matches nothing is the
                   most dangerous shape in this suite, and this file is entirely count-zero
                   assertions. So the population is asserted first: if the classes are ever
                   renamed or the layer moves, this fails before the overlap checks report clean. */
                expect(
                    labels.length,
                    `${where}, ${name}: no labels were painted at all, so the overlap checks below would pass for the wrong reason`,
                ).toBeGreaterThan(0);

                expect(
                    overlapping(labels, "ink"),
                    `${where}, ${name}: labels overlap on screen`,
                ).toEqual([]);

                expect(
                    overlapping(labels, "pad"),
                    `${where}, ${name}: touch pads overlap, so the later label steals the earlier one's taps`,
                ).toEqual([]);
            });
        }

        test("both classes of label are in the one pass", async ({ page }) => {
            /*
             * The claim under test is that names and phrases are placed together. If only one
             * class is ever painted, every overlap assertion above is true of a set with one kind
             * of thing in it, and the cross-class guarantee is untested.
             *
             * Asserted on Indra, whose neighbourhood carries both in every measured configuration.
             */
            await arrive(page, SUBJECTS.Indra);
            const labels = await settle(page);
            const kinds = new Set(labels.map((label) => label.kind));
            expect([...kinds].sort()).toEqual(["name", "phrase"]);
        });

        test("every phrase carries a target at least 44 px tall", async ({ page }) => {
            await arrive(page, SUBJECTS.Indra);
            const labels = await settle(page);
            const phrases = labels.filter((label) => label.kind === "phrase");
            expect(phrases.length).toBeGreaterThan(0);
            const short = phrases
                .filter((label) => label.pad.height < 44 || label.pad.width < 44)
                .map((label) => `"${label.text}" ${label.pad.width}x${label.pad.height}`);
            expect(short, `${where}: a relationship's only affordance is under-size`).toEqual([]);
        });
    });
}

gate(1440, 900, "desktop 1440x900");
gate(390, 844, "phone 390x844");

/* ---------------------------------------------------------------- the inspector - */

test.describe("the relationship inspector", () => {
    test.use({ viewport: { width: 390, height: 844 } });

    test("replaces the subject sheet rather than stacking on it", async ({ page }) => {
        /*
         * Measured before the fix, at 390 px: the inspector occupied y 528.9 to 845 and the
         * collapsed sheet y 725 to 845, so the inspector covered the sheet completely. Both are
         * pinned to the foot of the stage and both claim it.
         */
        await arrive(page, SUBJECTS.Indra);
        await settle(page);

        const sheet = page.locator(".va-world-panel");
        await expect(sheet).toBeVisible();

        /* `[data-shown="true"]` matters: every span in the pool is pickable, and the pool is
           allocated at the total cap, so the first in document order is usually an empty one. */
        await page.locator('.va-edge-label[data-shown="true"]').first().click();

        const inspector = page.locator(".va-relationship");
        await expect(inspector).toBeVisible();
        await expect(sheet).toBeHidden();

        /* And it gives the stage back when it closes, rather than leaving the reader with a
           subject panel that has quietly gone missing. */
        await page.getByRole("button", { name: "Close the relationship" }).click();
        await expect(inspector).toHaveCount(0);
        await expect(sheet).toBeVisible();
    });

    test("is a dialog, takes focus to its heading, and gives focus back", async ({ page }) => {
        await arrive(page, SUBJECTS.Indra);
        await settle(page);

        await page.locator('.va-edge-label[data-pickable="true"][data-shown="true"]').first().click();
        const inspector = page.locator(".va-relationship");
        await expect(inspector).toHaveAttribute("role", "dialog");

        /* The heading rather than the close button: announcing "close" as the first thing a reader
           hears tells them how to leave before telling them what they are in. */
        await expect(page.locator(".va-relationship-kind")).toBeFocused();

        /* Escape closes it. The page has its own Escape listener with a larger meaning, and a
           reader inside a dialog means "close this", not "leave the subject I am reading". */
        await page.keyboard.press("Escape");
        await expect(inspector).toHaveCount(0);
        await expect(page.locator('.va-graph[data-view="FOCUS"]')).toBeAttached();
    });

    test("offers a close target of at least 44 px", async ({ page }) => {
        /* It was 41 x 21.6, on the one control whose job is to get a reader out of a panel
           covering the bottom third of their phone. */
        await arrive(page, SUBJECTS.Indra);
        await settle(page);
        await page.locator('.va-edge-label[data-pickable="true"][data-shown="true"]').first().click();

        const close = page.getByRole("button", { name: "Close the relationship" });
        const box = await close.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.width).toBeGreaterThanOrEqual(44);
        expect(box!.height).toBeGreaterThanOrEqual(44);
    });

    test("scrolls rather than running off the bottom of the stage", async ({ page }) => {
        await arrive(page, SUBJECTS.Indra);
        await settle(page);
        await page.locator('.va-edge-label[data-pickable="true"][data-shown="true"]').first().click();

        const overflow = await page
            .locator(".va-relationship")
            .evaluate((node) => getComputedStyle(node).overflowY);
        expect(overflow).toBe("auto");

        const box = await page.locator(".va-relationship").boundingBox();
        expect(box).not.toBeNull();
        expect(box!.y + box!.height).toBeLessThanOrEqual(844 + 1);
    });
});

/* ----------------------------------------------------------------- the panel - */

/**
 * The subject panel's own text, measured the same way the labels above are.
 *
 * ## Why this is in this file
 *
 * Because it is the same claim about a different surface, and the suite already had the whole
 * apparatus for it. Everything here measured the canvas overlay and nothing measured the panel,
 * and a defect lived in that gap: `.va-world-neighbours` carried a `min-height: 0` left behind
 * by a removed inner scroller, the panel is a grid with a definite height, and in that
 * combination the declaration tells the row-sizing algorithm the item may be shrunk below its
 * content. It was - to a 12 px row holding 491 px of content, reporting a box height of zero -
 * and the list painted straight through the section beneath it. Thirty-nine pairs of glyphs
 * overlapped on Indra at 1440x900.
 *
 * Every existing assertion passed. The counts were right, the text was present, the contrast was
 * fine, `toBeVisible` was true of all of it. What no test did was ask where the ink was.
 *
 * ## Why it reads Range rectangles and not element boxes
 *
 * The first version of this measurement compared `getBoundingClientRect` for every element with
 * text and reported 47 overlaps - eight of them real and the rest a parent's box containing its
 * own child's. A `Range` over a text node gives the rectangle the glyphs occupy, which is the
 * only thing a reader can see collide. Clipped text is excluded rather than measured: a name in
 * this list is `white-space: nowrap` with `overflow: hidden`, so its unclipped ink extends past
 * the box and a Range reports the ink rather than the ellipsis. Two of the three remaining
 * "overlaps" after the fix were exactly that, which is how the exclusion came to be here.
 */
test.describe("the subject panel", () => {
    test.setTimeout(120_000);

    for (const width of [1440, 390] as const) {
        test(`no two pieces of its text overlap at ${width}px`, async ({ page }) => {
            await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
            await page.goto(`/graph?view=focus&renderer=3d&node=${encodeURIComponent(SUBJECTS.Indra)}`);
            await expect(page.locator("aside.va-world-panel")).toBeVisible({ timeout: READY });
            /* The rows arrive with the curated neighbourhood, which arrives after the artifact. */
            await expect
                .poll(() => page.locator("aside.va-world-panel li").count(), { timeout: READY })
                .toBeGreaterThan(0);

            const measured = await page.evaluate(() => {
                const panel = document.querySelector("aside.va-world-panel");
                if (!panel) return null;
                type Ink = { text: string; cls: string; box: DOMRect };
                const ink: Ink[] = [];
                const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    const text = (node.textContent ?? "").trim();
                    if (!text) continue;
                    const owner = node.parentElement;
                    if (!owner) continue;
                    const style = getComputedStyle(owner);
                    if (style.visibility === "hidden" || style.display === "none") continue;
                    if (Number(style.opacity) === 0) continue;
                    /* Off-screen on purpose. */
                    if (owner.closest(".sr-only")) continue;
                    /* Clipped text: the Range reports ink the reader cannot see, so measuring it
                       would report an overlap where there is an ellipsis. */
                    if (style.overflow === "hidden" && style.whiteSpace === "nowrap") continue;
                    const range = document.createRange();
                    range.selectNodeContents(node);
                    for (const box of range.getClientRects()) {
                        if (box.width < 1 || box.height < 1) continue;
                        ink.push({ text: text.slice(0, 32), cls: owner.className, box });
                    }
                    range.detach();
                }
                const clashes: string[] = [];
                for (let i = 0; i < ink.length; i += 1) {
                    for (let j = i + 1; j < ink.length; j += 1) {
                        const a = ink[i].box;
                        const b = ink[j].box;
                        /* Two pixels of slack, because a baseline-aligned row can share a
                           fraction of a pixel with its neighbour through rounding alone. */
                        const down = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                        const across = Math.min(a.right, b.right) - Math.max(a.left, b.left);
                        if (down > 2 && across > 2) {
                            clashes.push(
                                `"${ink[i].text}" over "${ink[j].text}" ` +
                                    `(${Math.round(down)}x${Math.round(across)} px)`,
                            );
                        }
                    }
                }
                /* And the sections themselves: a box of zero height holding content is the shape
                   the defect took, and it is worth naming directly rather than only through its
                   consequence. */
                const collapsed = [...panel.children]
                    .filter((child) => {
                        const box = child.getBoundingClientRect();
                        return box.height < 4 && (child.textContent ?? "").trim().length > 0;
                    })
                    .map((child) => `${child.tagName.toLowerCase()}.${child.className}`);
                /*
                 * And nothing may be laid out wider than the panel.
                 *
                 * The second defect this test was written after. One derived-metric node in the
                 * list is labelled `DEVATA_ATTRIBUTION_BY_VEDA (VG:DEVATA:INDRAH)`, its span is
                 * `white-space: nowrap`, and a flex item's default `min-width: auto` made that
                 * whole string the item's minimum - which floored the panel's implicit grid
                 * column at 403 px inside a 349 px panel. Every right-aligned value then sat 78
                 * px past the panel's edge and 46 px off a 1440 px viewport, so the counts this
                 * phase requires a reader to see were present, correct, accessible and invisible.
                 */
                const panelBox = panel.getBoundingClientRect();
                const outside: string[] = [];
                const measure = (node: Element) => {
                    for (const child of node.children) {
                        const box = child.getBoundingClientRect();
                        if (box.width > 0 && box.right > panelBox.right + 1) {
                            outside.push(
                                `${child.tagName.toLowerCase()}.${child.className} ` +
                                    `ends at ${Math.round(box.right)} against a panel edge at ` +
                                    `${Math.round(panelBox.right)}`,
                            );
                        }
                        measure(child);
                    }
                };
                measure(panel);

                /* The counts themselves, read as pairs, so "present" is not confused with
                   "legible": a term with no value beside it is the shape the defect took. */
                const facts = [...panel.querySelectorAll(".va-world-facts > div")].map((row) => ({
                    term: row.querySelector("dt")?.textContent?.trim() ?? "",
                    value: row.querySelector("dd")?.textContent?.trim() ?? "",
                    valueRight: Math.round(
                        row.querySelector("dd")?.getBoundingClientRect().right ?? 0,
                    ),
                }));

                return {
                    ink: ink.length,
                    clashes,
                    collapsed,
                    outside: outside.slice(0, 8),
                    outsideCount: outside.length,
                    horizontalOverflow: panel.scrollWidth - panel.clientWidth,
                    facts,
                    panelRight: Math.round(panelBox.right),
                    viewport: window.innerWidth,
                };
            });

            expect(measured, "the panel is not in the document").not.toBeNull();
            expect(
                measured!.ink,
                "no text was measured at all, so this test would pass against an empty panel",
            ).toBeGreaterThan(20);
            expect(
                measured!.collapsed,
                "a section of the panel has content and no height, so its content is painting " +
                    "outside its own box. Check for `min-height: 0` on a grid item: the panel " +
                    "has a definite height and that declaration lets the row shrink below its " +
                    "content.",
            ).toEqual([]);
            expect(
                measured!.clashes,
                `${measured!.clashes.length} pieces of the panel's text overlap each other`,
            ).toEqual([]);
            expect(
                measured!.outside,
                `${measured!.outsideCount} elements are laid out past the panel's right edge ` +
                    `(${measured!.panelRight} of a ${measured!.viewport} px viewport). A grid ` +
                    "column is floored at its items' min-content width and that floor is not " +
                    "clamped by the container, so one unbreakable string can displace the whole " +
                    "panel: check `grid-template-columns: minmax(0, 1fr)` on .va-world-panel and " +
                    "`min-width: 0` on .va-world-hit-name.",
            ).toEqual([]);
            expect(
                measured!.horizontalOverflow,
                "the panel scrolls sideways, so some of it cannot be read at all",
            ).toBeLessThanOrEqual(1);

            /* The counts the phase requires, each with a value, each inside the panel. */
            for (const fact of measured!.facts) {
                expect(
                    fact.value,
                    `the panel names "${fact.term}" and gives it no value`,
                ).not.toBe("");
                expect(
                    fact.valueRight,
                    `the value for "${fact.term}" ends at ${fact.valueRight}, outside the panel`,
                ).toBeLessThanOrEqual(measured!.panelRight + 1);
            }
            expect(
                measured!.facts.map((fact) => fact.term),
                "the panel no longer states the recorded count against the shown count, which " +
                    "is what stops a reader reading a curated view as the whole record",
            ).toEqual(
                expect.arrayContaining(["Recorded connections", "Shown in this view"]),
            );
        });
    }
});
