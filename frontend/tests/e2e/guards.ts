import { expect, type Page } from "@playwright/test";

/**
 * Guards for the most dangerous assertion in this suite: `toHaveCount(0)`.
 *
 * A bare count-zero passes for two completely different reasons. Either the thing really is
 * absent, which is what the test meant, or the selector no longer matches anything anywhere
 * because a class was renamed or the markup moved. In the second case the test has stopped
 * testing and reports success, so the coverage disappears with nothing turning red.
 *
 * The audit found six of these, and one of them was already inert before anyone touched it:
 * `svg.notation, .musical-notation` had been guarding against classes that do not exist in
 * the stylesheet at all, so "no fake musical notation on a Samaveda page" had never once been
 * checked. A seventh assertion, `toContainText(/Certain and probable mentions are
 * included|/)`, carried a trailing empty alternative, which makes the regex match the empty
 * string and the assertion incapable of failing.
 *
 * This matters more than usual right now. The rebrand renames classes and restructures the
 * DOM across every surface, which is exactly the change these assertions cannot survive
 * honestly.
 */

/**
 * Assert `selector` matches nothing on the current page, having first proved on `controlUrl`
 * that it still matches something.
 *
 * The control is the whole point. It is a page where the thing is known to be present, so if
 * the selector has gone stale the guard fails there and names the selector, instead of the
 * absence assertion passing for the wrong reason.
 */
export async function absentHere(
    page: Page,
    selector: string,
    { controlUrl, controlHint }: { controlUrl: string; controlHint: string },
) {
    const target = page.url();

    await page.goto(controlUrl);
    await expect(
        page.locator(selector),
        `Control failed: "${selector}" matched nothing on ${controlHint}, where it is expected. ` +
            `The selector is stale, so the absence check that follows would have passed ` +
            `without testing anything. Update the selector rather than the control.`,
    ).not.toHaveCount(0);

    await page.goto(target);
    await expect(page.locator(selector)).toHaveCount(0);
}

/**
 * The same idea for copy rather than markup: assert some text is absent here, having proved
 * the phrasing is still live somewhere it should appear.
 *
 * Without the control, rewording "Insufficient evidence" anywhere in the product silently
 * turns "an outage is not dressed up as a knowledge limit" into an assertion about a string
 * the product no longer uses.
 */
export async function textAbsentHere(
    page: Page,
    pattern: RegExp,
    { controlUrl, controlHint }: { controlUrl: string; controlHint: string },
) {
    const target = page.url();

    await page.goto(controlUrl);
    await expect(
        page.getByText(pattern).first(),
        `Control failed: ${pattern} appeared nowhere on ${controlHint}, where it is expected. ` +
            `The wording has changed, so the absence check that follows proves nothing.`,
    ).toBeVisible();

    await page.goto(target);
    await expect(page.getByText(pattern)).toHaveCount(0);
}
