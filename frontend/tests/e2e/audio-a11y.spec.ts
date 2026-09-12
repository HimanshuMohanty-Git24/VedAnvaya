import { expect, test } from "@playwright/test";

const RV_1_1_1 = encodeURIComponent("VG:RV:SAK:M01:S001:V001");

test.describe("accessibility of the audio surface", () => {
    test("every interactive control has an accessible name", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const recitation = page.locator("section.recitation");
        const controls = recitation.locator("button, input, select, a");
        const count = await controls.count();
        expect(count).toBeGreaterThan(3);
        for (let i = 0; i < count; i++) {
            const control = controls.nth(i);
            const name =
                (await control.getAttribute("aria-label")) ??
                (await control.getAttribute("title")) ??
                (await control.textContent());
            expect(name?.trim(), `control ${i} has no accessible name`).toBeTruthy();
        }
    });

    test("the region is labelled so a screen reader can find it", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        await expect(page.getByRole("region", { name: "Recitation" })).toBeVisible();
    });

    test("state is conveyed by text and icon, not colour alone", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const play = page.getByRole("button", { name: /^Play / });
        // The accessible name carries the state, so it survives greyscale and a screen reader.
        await expect(play).toHaveAccessibleName(/^Play /);
        await expect(page.locator("section.recitation svg").first()).toBeVisible();
    });

    test("the media element is not exposed as a focus trap", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        // preload=none and off-screen: it must not be a tab stop competing with the
        // real transport controls.
        const media = page.locator(".recitation-media");
        await expect(media).toHaveCount(1);
        await expect(media).not.toHaveAttribute("controls", /.*/);
    });

    test("focus is visible on the play control", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const play = page.getByRole("button", { name: /^Play / });
        await play.focus();
        const outline = await play.evaluate(
            (el) => getComputedStyle(el).outlineStyle + " " + getComputedStyle(el).outlineWidth,
        );
        expect(outline).not.toBe("none 0px");
    });

    test("the provenance disclosure is keyboard operable", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const summary = page.getByText("About this recording");
        await summary.focus();
        await page.keyboard.press("Enter");
        await expect(page.locator("section.recitation")).toContainText("VedSearch");
    });

    test("the page keeps exactly one first-level heading", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    });
});
