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
            out.push({
                kind: node.classList.contains("va-edge-label") ? "phrase" : "name",
                text: node.textContent ?? "",
                ink: { x: box.x, y: box.y, width: box.width, height: box.height },
                pad: {
                    x: box.x - padX,
                    y: box.y - padY,
                    width: box.width + padX * 2,
                    height: box.height + padY * 2,
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

function overlapping(labels: Painted[], box: "ink" | "pad"): string[] {
    const pairs: string[] = [];
    for (let i = 0; i < labels.length; i += 1) {
        for (let j = i + 1; j < labels.length; j += 1) {
            const a = labels[i][box];
            const b = labels[j][box];
            const dx = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
            const dy = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
            if (dx > 0.5 && dy > 0.5) {
                pairs.push(
                    `${labels[i].kind} "${labels[i].text}" x ${labels[j].kind} ` +
                        `"${labels[j].text}" overlap ${dx.toFixed(1)} x ${dy.toFixed(1)} px`,
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
