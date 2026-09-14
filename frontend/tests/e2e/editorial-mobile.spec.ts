import { expect, test } from "@playwright/test";

/**
 * The Lab and the editorial pages at 390px.
 *
 * Two things are being checked and they pull in opposite directions. Nothing may run past the
 * viewport, and the figures must still be figures: a chart that survives a phone by dropping
 * its numbers has not survived. So the bar track is allowed to disappear on the ranked tables
 * — at 390px it has about 90px to work with, which cannot encode a difference — but the row
 * label and the figure must both remain, and the corpus strips keep their bars because four
 * rows of one property is the one comparison that still reads narrow.
 *
 * The matrix is the deliberate exception. Six pairs by eight classes cannot be read at 390px,
 * so it lives in a horizontal scroller, and the test asserts that the scroller is what is wide
 * rather than the page.
 */

const PAGES = [
    "/visualizations",
    "/visualizations/four-corpora",
    "/visualizations/deities",
    "/visualizations/transmission",
    "/visualizations/human-concerns",
    "/visualizations/material-culture",
    "/about",
    "/sources",
];

test.describe("at 390px", () => {
    for (const url of PAGES) {
        test(`${url} does not scroll sideways`, async ({ page }) => {
            await page.goto(url);
            const overflow = await page.evaluate(
                () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
            );
            expect(overflow, `${url} overflows by ${overflow}px`).toBeLessThanOrEqual(1);
        });
    }

    test("a ranked table keeps its numbers when it loses its bars", async ({ page }) => {
        await page.goto("/visualizations/human-concerns");
        const row = page.locator(".va-rank tbody tr").first();
        await expect(row.locator("th")).toBeVisible();
        await expect(row.locator(".va-rank-value")).toBeVisible();
        // The track is what gives way, and only the track.
        await expect(row.locator(".va-rank-track")).toBeHidden();
    });

    test("a corpus strip keeps its bars, because four rows still compare", async ({ page }) => {
        await page.goto("/visualizations/four-corpora");
        const strip = page.locator(".va-strip").first();
        await expect(strip.locator("tbody tr")).toHaveCount(4);
        await expect(strip.locator(".va-strip-bar").first()).toBeVisible();
    });

    test("the wide matrix scrolls inside itself rather than widening the page", async ({
        page,
    }) => {
        await page.goto("/visualizations/transmission");
        const region = page.locator(".va-matrix-scroll");
        const measured = await region.evaluate((node) => ({
            client: node.clientWidth,
            scroll: node.scrollWidth,
            overflowX: getComputedStyle(node).overflowX,
        }));
        expect(measured.overflowX).toBe("auto");
        expect(measured.scroll).toBeGreaterThan(measured.client);
        expect(measured.client).toBeLessThanOrEqual(390);
    });

    test("the plate label is still readable prose, not a collapsed disclosure", async ({
        page,
    }) => {
        await page.goto("/visualizations/deities");
        const label = page.locator(".va-plate-label");
        await expect(label.getByText("What this does not show")).toBeVisible();
        await expect(label.locator("dd").last()).toBeVisible();
    });

    test("a long document keeps its contents list above the prose", async ({ page }) => {
        await page.goto("/sources");
        const contents = page.locator(".va-doc-contents");
        const body = page.locator(".va-doc-body");
        await expect(contents).toBeVisible();
        const contentsBox = await contents.boundingBox();
        const bodyBox = await body.boundingBox();
        expect(contentsBox!.y).toBeLessThan(bodyBox!.y);
        // Not sticky on a phone: a pinned rail would eat the viewport the document needs.
        await expect(contents).toHaveCSS("position", "static");
    });
});
