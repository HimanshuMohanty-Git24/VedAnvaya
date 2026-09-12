import { expect, test } from "@playwright/test";

const RV_1_1_1 = encodeURIComponent("VG:RV:SAK:M01:S001:V001");
const INDRA = encodeURIComponent("VG:DEVATA:INDRAH");

test.describe("mobile reader", () => {
    test("the mantra reads cleanly and nothing overflows the viewport", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("RV 1.1.1");

        const sanskrit = page.locator(".sanskrit").first();
        await expect(sanskrit).toBeVisible();

        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);

        // The knowledge tabs stay reachable below the reading column.
        await expect(page.getByRole("tab", { name: /Context/ })).toBeVisible();
    });

    test("the knowledge tabs switch on a touch viewport", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        await page.getByRole("tab", { name: /Evidence/ }).click();
        await expect(
            page.getByRole("heading", { name: "Where this text comes from" }),
        ).toBeVisible();
    });
});

test.describe("mobile entity page", () => {
    test("a deity profile is readable and its charts do not clip", async ({ page }) => {
        await page.goto(`/devatas/${INDRA}`);
        await expect(page.getByRole("heading", { level: 1 })).toContainText("Indra");
        await expect(page.locator("figure.measure").first()).toBeVisible();

        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);

        const chart = page.locator("figure.measure").first();
        const box = await chart.boundingBox();
        const viewport = page.viewportSize();
        expect(box!.width).toBeLessThanOrEqual((viewport?.width ?? 390) + 1);
    });
});

test.describe("mobile navigation", () => {
    test("the drawer opens, lists every section and closes on choice", async ({ page }) => {
        await page.goto("/");
        await page.getByRole("button", { name: "Open navigation" }).click();
        const dialog = page.getByRole("dialog");
        await expect(dialog).toBeVisible();
        await expect(dialog.getByRole("link", { name: /Vedas/ })).toBeVisible();
        await expect(dialog.getByRole("link", { name: /Limits/ })).toBeVisible();

        await dialog.getByRole("link", { name: /Graph/ }).click();
        await expect(page).toHaveURL(/\/graph/);
        await expect(page.getByRole("dialog")).toHaveCount(0);
    });

    test("the graph remains usable with simplified controls", async ({ page }) => {
        await page.goto(`/graph?node=${INDRA}`);
        await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
        await expect(page.getByRole("button", { name: "Fit the graph to the view" })).toBeVisible();

        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);
    });
});

test.describe("mobile search", () => {
    test("results are legible and the filter bank wraps", async ({ page }) => {
        await page.goto("/search");
        await page.getByLabel(/Search Sanskrit, IAST/).fill("Indra");
        await expect(page.locator(".search-results li").first()).toBeVisible();

        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);
    });
});

test.describe("mobile recitation", () => {
    test("the player fits 390px and its controls stay usable", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const recitation = page.locator("section.recitation");
        await expect(recitation).toBeVisible();
        await expect(recitation).toContainText("Recitation of this verse");

        // The transport wraps rather than crushing the seek bar to a few pixels.
        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);

        // The play control keeps a real touch target.
        const play = page.getByRole("button", { name: /^Play / });
        const box = await play.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.width).toBeGreaterThanOrEqual(36);
        expect(box!.height).toBeGreaterThanOrEqual(36);

        // The seek bar takes the full width on its own row rather than sharing one.
        const seek = page.getByRole("slider", { name: /Seek within this recitation/ });
        const seekBox = await seek.boundingBox();
        expect(seekBox).not.toBeNull();
        expect(seekBox!.width).toBeGreaterThan(180);
    });

    test("a verse with no recitation reads normally on mobile", async ({ page }) => {
        await page.goto(`/passage/${encodeURIComponent("VG:SV:KAU:ARANYA:D01:V01")}`);
        await expect(page.locator(".sanskrit").first()).toBeVisible();
        await expect(page.locator("section.recitation")).toHaveCount(0);
    });
});
