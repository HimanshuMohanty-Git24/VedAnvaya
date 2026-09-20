import { expect, test, type Page } from "@playwright/test";

/**
 * The restored surfaces at 390px, the narrowest width this project designs for.
 *
 * The owner's report singled out the graph's search panel, which "can become extremely
 * narrow", and the connections matrix, which was a horizontal-scroll-only experience. Both
 * are width failures and neither is visible from a desktop run, so they get their own file
 * rather than a viewport override inside the desktop suite.
 *
 * Every assertion here is measured on the settled DOM. Reading a box mid-transition reports
 * a layout nobody ever sees, and this project has invented three defects that way.
 */

const SETTLE = 30_000;

/** How far the document may exceed its own viewport before a reader has to scroll sideways. */
const SLACK = 1;

async function overflow(page: Page) {
    return page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
}

/** Every element whose box crosses the right edge of the viewport, named so a failure is fixable. */
async function offscreen(page: Page) {
    return page.evaluate(() => {
        const limit = document.documentElement.clientWidth;
        const out: string[] = [];
        for (const node of document.querySelectorAll<HTMLElement>("main *")) {
            const box = node.getBoundingClientRect();
            if (box.width === 0 || box.height === 0) continue;
            if (box.right <= limit + 1) continue;
            /* A scroll container is allowed to be wider than the page *inside itself*. */
            const style = getComputedStyle(node);
            if (style.overflowX === "auto" || style.overflowX === "scroll") continue;
            out.push(
                `${node.tagName.toLowerCase()}.${node.className || "(none)"} right=${Math.round(box.right)} > ${limit}`,
            );
        }
        return out.slice(0, 8);
    });
}

test.describe("the restored surfaces at 390px", () => {
    for (const route of [
        "/",
        "/vedas",
        "/vedas/samaveda",
        "/connections",
        "/limits",
        "/passage/VG%3ASV%3AKAU%3ACHANDA%3AP01%3AD01%3AV01",
    ]) {
        test(`${route} does not scroll sideways`, async ({ page }) => {
            await page.goto(route);
            await page.waitForLoadState("networkidle");
            const excess = await overflow(page);
            expect(excess, `offenders: ${JSON.stringify(await offscreen(page))}`).toBeLessThanOrEqual(
                SLACK,
            );
        });
    }

    test("the connections matrix stacks rather than scrolling", async ({ page }) => {
        /*
         * The reported experience: "a horizontally overflowing raw table". The repair stacks
         * each pair into its own block below 72rem, so what is asserted is that the matrix is
         * still all there -- every pair, every class -- and still fits.
         */
        await page.goto("/connections");
        await page.getByText(/full evidence matrix/i).first().click();
        const cells = page.locator(".va-conn-cell");
        await expect(cells.first()).toBeVisible({ timeout: SETTLE });
        expect(await cells.count()).toBeGreaterThan(20);
        expect(await overflow(page)).toBeLessThanOrEqual(SLACK);
    });

    test("the graph's search results stay readable in a narrow panel", async ({ page }) => {
        /*
         * The panel is the narrowest thing on the narrowest page, and it is where the owner
         * saw a name and its type collide. Three claims, all measured on the settled DOM:
         * every hit is inside the viewport, the name and the type do not overlap, and the
         * type is still legible rather than clipped to nothing.
         */
        await page.goto("/graph");
        const find = page.locator("#graph-find");
        await find.waitFor({ state: "visible", timeout: SETTLE });
        await find.fill("indra");
        const hits = page.locator(".va-world-hits li");
        await expect(hits.first()).toBeVisible({ timeout: SETTLE });

        const rows = await hits.count();
        expect(rows).toBeGreaterThan(1);

        const report = await page.evaluate(() => {
            const limit = document.documentElement.clientWidth;
            const bad: string[] = [];
            for (const item of document.querySelectorAll(".va-world-hits li")) {
                const name = item.querySelector(".va-world-hit-name");
                const kind = item.querySelector(".va-world-hit-kind");
                if (!name || !kind) {
                    bad.push("a hit is missing its name or its kind");
                    continue;
                }
                const n = name.getBoundingClientRect();
                const k = kind.getBoundingClientRect();
                if (Math.round(n.right) > limit) bad.push(`name past the edge: ${name.textContent}`);
                if (Math.round(k.right) > limit) bad.push(`kind past the edge: ${kind.textContent}`);
                if (k.width < 8 || k.height < 8) bad.push(`kind collapsed: ${kind.textContent}`);
                /* Side by side on one line, or stacked. Overlapping is neither. */
                const sameLine = n.bottom > k.top + 1 && k.bottom > n.top + 1;
                if (sameLine && n.right > k.left + 1) {
                    bad.push(`name and kind overlap: ${name.textContent}`);
                }
            }
            return bad;
        });
        expect(report, report.join("; ")).toEqual([]);
    });

    test("a Samavedic verse keeps its text, its notation and its phrases on a phone", async ({
        page,
    }) => {
        await page.goto("/passage/VG%3ASV%3AKAU%3ACHANDA%3AP01%3AD01%3AV01");
        await expect(page.locator(".va-verse")).toBeVisible();
        await expect(page.getByRole("heading", { name: /svara notation/i })).toBeVisible();
        await expect(page.getByRole("heading", { name: /fixed phrases/i })).toBeVisible();
        expect(await overflow(page)).toBeLessThanOrEqual(SLACK);
    });
});
