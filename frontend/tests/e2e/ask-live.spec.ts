/**
 * One real Ask journey, against the live API and a live provider.
 *
 * Deliberately excluded from the default e2e run: every execution spends provider quota,
 * so this is opt-in via `ASK_LIVE=1`. The rest of the suite must stay runnable without a
 * key, which is why no other spec touches /ask.
 *
 * The question is short and cheap on purpose. What is under test is the *journey* --
 * composer, waiting state, answer, support grade, citation markers, evidence drawer,
 * follow-ups -- not the scholarship, which the 60-question benchmark measures.
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
        const composer = page.getByLabel("Your question");
        await expect(composer).toBeVisible();
        await composer.fill(QUESTION);

        const submit = page.getByRole("button", { name: "Ask", exact: true });
        await expect(submit).toBeEnabled();
        await submit.click();

        // -- the waiting state ---------------------------------------------
        // Raced against the answer rather than awaited: a fast reply is not a failure,
        // and asserting the waiting state strictly would make this flaky on a warm provider.
        const waiting = page.locator(".va-ask-waiting");
        const answer = page.locator(".va-answer");
        await expect(waiting.or(answer).first()).toBeVisible({ timeout: 30_000 });

        /* If the waiting state is the one that appeared, it must report elapsed time rather
           than a fabricated stage. This is the defect the phase existed to fix: the previous
           build advanced through three phases in 2.6s and then sat on the last one for the
           remaining hundred seconds of a median request. */
        if (await waiting.isVisible()) {
            await expect(page.locator(".va-ask-elapsed")).toContainText(/\d+s elapsed/);
            await expect(page.getByRole("button", { name: /Stop waiting/i })).toBeVisible();
        }

        // -- the answer ----------------------------------------------------
        await expect(answer).toBeVisible({ timeout: 150_000 });
        const prose = page.locator(".va-answer-prose");
        await expect(prose).toBeVisible();
        expect((await prose.innerText()).trim().length).toBeGreaterThan(40);

        // -- the grade on the evidence -------------------------------------
        const support = page.locator(".va-answer-support");
        await expect(support).toBeVisible();
        // Graded in words, not only in colour.
        expect((await support.innerText()).toUpperCase()).toMatch(
            /STRONG|MODERATE|LIMITED|INSUFFICIENT|NOT GRADED/,
        );

        // -- a citation marker opens its evidence --------------------------
        const markers = page.locator("button.va-cite");
        await expect(markers.first()).toBeVisible();
        expect(await markers.count()).toBeGreaterThan(0);

        await markers.first().click();
        const drawer = page.locator(".evidence-drawer");
        await expect(drawer).toBeVisible();
        expect((await drawer.innerText()).trim().length).toBeGreaterThan(20);
        await page.getByRole("button", { name: "Close the evidence panel" }).click();
        await expect(drawer).toBeHidden();

        // -- the drawer also opens from the answer's own action ------------
        await page.locator(".va-answer-inspect").click();
        await expect(drawer).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(drawer).toBeHidden();

        // -- follow-ups are offered ----------------------------------------
        const next = page.locator(".va-answer-next");
        await expect(next).toBeVisible();
        expect(await next.locator("button").count()).toBeGreaterThan(0);
    });
});
