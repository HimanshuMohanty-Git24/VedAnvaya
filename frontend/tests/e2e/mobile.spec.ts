import { expect, test } from "@playwright/test";
import { absentHere, atUrl } from "./guards";

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

        // The apparatus follows the verse down the page rather than beside it.
        await expect(
            page.getByRole("heading", { name: /Ascribed in the apparatus/i }),
        ).toBeVisible();
    });

    test("the whole apparatus is readable without opening anything", async ({ page }) => {
        /*
         * This replaces a test that clicked between six tabbed panels. The tabs are gone, and
         * their removal is the point rather than an incidental refactor: an apparatus is read
         * alongside its text, and putting three quarters of it behind a control means a reader
         * has to know it is there before they can find it. On a phone that cost was worst,
         * because the control sat below the fold as well.
         *
         * So the assertion is the inverse of the old one. Every group is present on arrival,
         * with nothing tapped.
         */
        await page.goto(`/passage/${RV_1_1_1}`);
        for (const heading of [
            /Ascribed in the apparatus/i,
            /Named inside this verse/i,
            /Connected passages/i,
        ]) {
            await expect(page.getByRole("heading", { name: heading })).toBeVisible();
        }
        await expect(page.getByRole("tab")).toHaveCount(0);
    });

    test("the rail stacks under the verse rather than beside it", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const verse = await page.locator(".va-verse").boundingBox();
        const rail = await page.locator(".va-rail").boundingBox();
        // Below, not alongside: a 390px column has no room for a margin apparatus.
        expect(rail!.y).toBeGreaterThan(verse!.y + verse!.height - 1);
        expect(rail!.x).toBeLessThan(40);
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
        await absentHere(
            page,
            (scope) => scope.locator("section.recitation"),
            atUrl(`/passage/${RV_1_1_1}`, "RV 1.1.1, which does have a recitation"),
        );
    });
});
