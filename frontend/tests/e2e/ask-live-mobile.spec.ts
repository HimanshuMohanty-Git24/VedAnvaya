/**
 * The same live Ask journey at 390px, the narrowest phone this project designs for.
 *
 * Opt-in via `ASK_LIVE=1` for the same reason as the desktop journey: it spends provider
 * quota. What is checked here is not that the page renders, but that nothing a reader
 * needs is unreachable at that width -- the composer, the answer, a citation marker, and
 * the evidence drawer the marker opens -- and that the layout does not scroll sideways,
 * which is how a narrow break actually presents.
 */
import { expect, test } from "@playwright/test";

const LIVE = process.env.ASK_LIVE === "1";
const QUESTION = "What does RV 1.1.1 contain?";

test.describe("Ask, live, 390px", () => {
    test.skip(!LIVE, "set ASK_LIVE=1 to spend provider quota on this journey");
    test.setTimeout(180_000);
    test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

    test("the journey is usable at 390px without horizontal scroll", async ({ page }) => {
        await page.goto("/ask");
        await expect(page.getByRole("heading", { name: "Ask VedAnvaya", level: 1 })).toBeVisible();

        const noSideScroll = async (where: string) => {
            const overflow = await page.evaluate(
                () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
            );
            expect(overflow, `horizontal overflow at ${where}`).toBeLessThanOrEqual(1);
        };
        await noSideScroll("the empty composer");

        const composer = page.getByLabel("Your research question");
        await expect(composer).toBeVisible();
        await composer.fill(QUESTION);

        const submit = page.getByRole("button", { name: "Ask VedAnvaya" });
        await expect(submit).toBeEnabled();
        await submit.click();

        const answer = page.locator(".ask-answer");
        await expect(answer).toBeVisible({ timeout: 150_000 });
        await expect(page.locator(".ask-prose")).toBeVisible();
        await expect(page.locator(".ask-badges")).toBeVisible();
        await noSideScroll("the rendered answer");

        // A citation marker must be tappable, not merely present.
        const marker = page.locator("button.ask-cite").first();
        await expect(marker).toBeVisible();
        const box = await marker.boundingBox();
        expect(box, "the citation marker has no layout box").not.toBeNull();
        expect(box!.width).toBeGreaterThan(0);
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(391);

        await marker.tap();
        const drawer = page.locator(".evidence-drawer");
        await expect(drawer).toBeVisible();
        await noSideScroll("the open evidence drawer");
        const drawerBox = await drawer.boundingBox();
        expect(drawerBox!.width).toBeLessThanOrEqual(391);

        await page.getByRole("button", { name: "Close the evidence panel" }).tap();
        await expect(drawer).toBeHidden();

        await expect(page.locator(".ask-related")).toBeVisible();
    });
});
