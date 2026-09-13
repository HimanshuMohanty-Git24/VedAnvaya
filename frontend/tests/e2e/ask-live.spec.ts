/**
 * One real Ask journey, against the live API and a live provider.
 *
 * Deliberately excluded from the default e2e run: every execution spends provider quota,
 * so this is opt-in via `ASK_LIVE=1`. The rest of the suite must stay runnable without a
 * key, which is why no other spec touches /ask.
 *
 * The question is short and cheap on purpose. What is under test is the *journey* --
 * composer, pending state, answer, status badge, citation markers, evidence drawer,
 * follow-up chips -- not the scholarship, which the 60-question benchmark measures.
 */
import { expect, test } from "@playwright/test";

const LIVE = process.env.ASK_LIVE === "1";

// Short, cheap, and answerable from one passage lookup.
const QUESTION = "What does RV 1.1.1 contain?";

test.describe("Ask, live", () => {
    test.skip(!LIVE, "set ASK_LIVE=1 to spend provider quota on this journey");
    test.setTimeout(180_000);

    test("a real question returns a cited answer whose evidence can be opened", async ({
        page,
    }) => {
        await page.goto("/ask");

        // -- the page and its contract ------------------------------------
        await expect(page.getByRole("heading", { name: "Ask VedAnvaya", level: 1 })).toBeVisible();
        await expect(page.getByRole("heading", { name: "What it refuses to do" })).toBeVisible();

        // -- the composer --------------------------------------------------
        const composer = page.getByLabel("Your research question");
        await expect(composer).toBeVisible();
        await composer.fill(QUESTION);

        const submit = page.getByRole("button", { name: "Ask VedAnvaya" });
        await expect(submit).toBeEnabled();
        await submit.click();

        // -- the loading state ---------------------------------------------
        // Raced against the answer rather than awaited: a fast reply is not a failure,
        // and asserting the spinner strictly would make this flaky on a warm provider.
        const pending = page.locator(".ask-pending");
        const answer = page.locator(".ask-answer");
        await expect(pending.or(answer).first()).toBeVisible({ timeout: 30_000 });

        // -- the answer ----------------------------------------------------
        await expect(answer).toBeVisible({ timeout: 150_000 });
        const prose = page.locator(".ask-prose");
        await expect(prose).toBeVisible();
        expect((await prose.innerText()).trim().length).toBeGreaterThan(40);

        // -- KnowledgeStatus -----------------------------------------------
        const badges = page.locator(".ask-badges");
        await expect(badges).toBeVisible();
        const status = (await badges.innerText()).toUpperCase();
        expect(status).toMatch(/SUPPORTED|PARTIAL|INSUFFICIENT|NOT BUILT|NOT_BUILT/);

        // -- a citation marker opens its evidence --------------------------
        const markers = page.locator("button.ask-cite");
        await expect(markers.first()).toBeVisible();
        const markerCount = await markers.count();
        expect(markerCount).toBeGreaterThan(0);

        await markers.first().click();
        const drawer = page.locator(".evidence-drawer");
        await expect(drawer).toBeVisible();
        expect((await drawer.innerText()).trim().length).toBeGreaterThan(20);
        await page.getByRole("button", { name: "Close the evidence panel" }).click();
        await expect(drawer).toBeHidden();

        // -- the drawer also opens from the answer's own action ------------
        await page.locator(".ask-answer-actions button").first().click();
        await expect(drawer).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(drawer).toBeHidden();

        // -- follow-ups are offered ----------------------------------------
        const related = page.locator(".ask-related");
        await expect(related).toBeVisible();
        expect(await related.locator("button").count()).toBeGreaterThan(0);
    });
});
