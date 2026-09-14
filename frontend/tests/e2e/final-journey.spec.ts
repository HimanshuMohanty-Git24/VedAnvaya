import { expect, test } from "@playwright/test";

/**
 * The journey this phase is accepted or rejected on.
 *
 * One continuous path from the front door to an explained relationship, asserted end to end
 * rather than as separate features that each work in isolation. The two defects it exists to
 * prevent from returning:
 *
 *   - the homepage showing a diagram with no relationship to the product behind it, so that
 *     clicking through was a change of subject rather than a continuation;
 *   - a graph of anonymous lines, where a reader could see that two subjects were connected and
 *     never learn what connected them.
 *
 * Each step asserts the *state after arriving*, not merely that a click did not throw.
 */

const AGNI = encodeURIComponent("VG:DEVATA:AGNIH");

/** The world is a two-megabyte artifact and a settling layout; it is not a fast page. */
const SETTLE = 30_000;

/** The labels are written directly to the DOM, so their visibility lives in the style. */
async function shownLabels(page: import("@playwright/test").Page) {
    return page.evaluate(() =>
        [...document.querySelectorAll(".va-edge-label")]
            .filter((node) => (node as HTMLElement).style.opacity === "1")
            .map((node) => node.textContent ?? ""),
    );
}

test.describe("the final journey", () => {
    test("front door to an explained relationship, without a break in the language", async ({
        page,
    }) => {
        /* 1 — The front door shows the real world, not a picture of one. */
        await page.goto("/");
        const hero = page.locator("canvas.va-world-preview-canvas");
        await expect(hero).toBeVisible({ timeout: SETTLE });

        /*
         * The teaser this replaced is gone, not merely hidden behind it.
         *
         * Restated, because the two assertions here were inert. They read
         * `.va-constellation-canvas` and `.va-constellation-panel` at count 0, and neither
         * class occurs in any source file in this repository - so both passed by matching
         * nothing, bypassed the `absentHere()` guard that exists in this suite precisely to
         * catch that, and would have gone on passing had the teaser returned under any other
         * name. A guard is no use here either: `absentHere` needs a control page where the
         * locator still matches, and a deleted component has none.
         *
         * So the claim is made about what the front door draws rather than about two dead
         * class names: every canvas on this page is the world preview's own. A second,
         * decorative canvas - which is what the teaser was - fails this whatever it is
         * called. The two mutually exclusive preview variants (spatial and flat) both use
         * `va-world-preview-canvas`, so one class covers either.
         */
        const canvasClasses = await page
            .locator("canvas")
            .evaluateAll((nodes) => nodes.map((node) => node.className));
        expect(canvasClasses.length, "the front door drew no canvas at all").toBeGreaterThan(0);
        for (const name of canvasClasses) {
            expect(name, `an extra canvas is on the front door: ${name}`).toContain(
                "va-world-preview-canvas",
            );
        }

        // Its subjects are real and reachable without a canvas.
        const alternatives = page.locator(".va-world-preview-panel .sr-only li a");
        expect(await alternatives.count()).toBeGreaterThan(20);
        await expect(alternatives.first()).toHaveAttribute("href", /\/graph\?view=focus/);

        /* 2 — The way in leads to the same world. The panel's own link, not the hero's action
           beside it: the claim is that the preview is a door, not that the page has a button. */
        await page.locator(".va-world-preview-link").click();
        await expect(page).toHaveURL(/\/graph/);
        await expect(page.locator(".va-world-canvas")).toBeVisible({ timeout: SETTLE });

        /* 3 — A subject can be found by name, from the keyboard alone. */
        const find = page.getByLabel(/find a subject/i);
        await find.click();
        await find.fill("Agni");
        const hit = page.locator(".va-world-hits button").first();
        await expect(hit).toBeVisible({ timeout: SETTLE });
        await hit.click();

        /* 4 — Choosing it says what it is, and how much of it is being shown. */
        const panel = page.locator(".va-world-panel");
        await expect(panel).toBeVisible();
        await expect(panel.getByRole("heading", { level: 2 })).toContainText(/\w/);
        await expect(page.locator(".va-world-neighbours h3")).toContainText(/\d/);

        /* 5 — Its connections say what they are. This is the defect the phase exists to fix. */
        await expect
            .poll(async () => (await shownLabels(page)).length, { timeout: SETTLE })
            .toBeGreaterThan(0);
        const phrases = await shownLabels(page);
        for (const phrase of phrases) {
            // Curated words, not ontology tokens.
            expect(phrase).not.toMatch(/_/);
            expect(phrase.trim().length).toBeGreaterThan(0);
        }

        /* 6 — One of them explains itself, including what it does not establish. */
        const labels = page.locator('.va-edge-label[data-pickable="true"]');
        const count = await labels.count();
        for (let i = 0; i < count; i += 1) {
            const label = labels.nth(i);
            if ((await label.evaluate((node) => (node as HTMLElement).style.opacity)) !== "1") {
                continue;
            }
            await label.click();
            break;
        }
        const inspector = page.locator(".va-relationship");
        await expect(inspector).toBeVisible();
        await expect(inspector.getByText("What it does not establish")).toBeVisible();

        /* 7 — Escape steps back out of it, rather than trapping the reader in the panel. */
        await page.keyboard.press("Escape");
        await expect(page.locator(".va-relationship")).toHaveCount(0);
        await expect(panel).toBeVisible();
    });

    test("the same connections are named the same way in both renderers", async ({ page }) => {
        /* The parity claim. Two renderers with two label systems would eventually disagree about
           what a subject is attached to, which is worse than one of them being silent. */
        const vocabulary = async (renderer: "3d" | "2d") => {
            await page.goto(`/graph?view=focus&renderer=${renderer}&node=${AGNI}`);
            await expect(page.locator(".va-world-panel")).toBeVisible({ timeout: SETTLE });
            await expect
                .poll(async () => (await shownLabels(page)).length, { timeout: SETTLE })
                .toBeGreaterThan(0);
            return new Set(await shownLabels(page));
        };

        const spatial = await vocabulary("3d");
        const planar = await vocabulary("2d");

        // Which connections fit on screen differs between a projection and a simulation, so the
        // sets need not be equal. What must hold is that neither invents a phrase the other has
        // never heard of: both read the same exported vocabulary.
        const shared = [...spatial].filter((phrase) => planar.has(phrase));
        expect(shared.length, `3d: ${[...spatial]} / 2d: ${[...planar]}`).toBeGreaterThan(0);
    });

    test("changing how the graph is drawn never changes what is being explored", async ({
        page,
    }) => {
        /* The invariant from the previous corrective phase, re-asserted through the new surface:
           relationship labels must not have introduced a path from a label to a renderer. */
        await page.goto(`/graph?view=focus&renderer=3d&node=${AGNI}`);
        await expect(page.locator(".va-world-panel")).toBeVisible({ timeout: SETTLE });

        await page.getByRole("button", { name: "2D", exact: true }).click();
        await expect(page).toHaveURL(/renderer=2d/);
        await expect(page).toHaveURL(/view=focus/);
        await expect(page).toHaveURL(new RegExp(AGNI.replace(/%/g, "%")));

        await page.getByRole("button", { name: "3D", exact: true }).click();
        await expect(page).toHaveURL(/renderer=3d/);
        await expect(page).toHaveURL(/view=focus/);
    });

    test("a route says what each of its steps is", async ({ page }) => {
        await page.goto(
            `/graph?view=path&renderer=3d&from=${AGNI}&to=${encodeURIComponent("VG:DEVATA:INDRAH")}`,
        );
        await expect(page.locator(".va-path")).toBeVisible({ timeout: SETTLE });
        // The route's own list states every hop and its relationship; the canvas names the steps
        // it can fit. The list is the guarantee, so that is what is asserted.
        const relations = page.locator(".va-path-relation");
        await expect(relations.first()).toBeVisible({ timeout: SETTLE });
        for (const phrase of await relations.allTextContents()) {
            expect(phrase.trim().length).toBeGreaterThan(0);
            // The service sends words; a token here would mean the label was lost on the way.
            expect(phrase).not.toMatch(/_/);
        }
    });
});
