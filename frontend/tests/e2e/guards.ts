import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Guards for the most dangerous assertion in this suite: `toHaveCount(0)`.
 *
 * A bare count-zero passes for two completely different reasons. Either the thing really is
 * absent, which is what the test meant, or the locator no longer matches anything anywhere
 * because a class was renamed, an accessible name changed or the markup moved. In the second
 * case the test has stopped testing and reports success, so the coverage disappears with
 * nothing turning red.
 *
 * The audit that prompted this found six of them, and one had been inert from the day it was
 * written: `svg.notation, .musical-notation` guarded against classes that are not in the
 * stylesheet at all, so "no fake musical notation on a Samaveda page" had never once been
 * checked. A seventh assertion carried a trailing empty alternative in its regex, which makes
 * it match the empty string and makes the assertion incapable of failing.
 *
 * ## Why the control is a function and not a URL
 *
 * A first version took a CSS selector and a control URL. Both were too narrow, and the guards
 * proved it by refusing three real call sites on their first run:
 *
 * - The recitation play button carries its name in `aria-label` and has no text at all, so no
 *   CSS selector can express it. The locator is now a function, so a role query works.
 * - A search error only appears after the search has actually run, so navigating to a URL is
 *   not enough to reach the control state. The control is now a function too.
 *
 * Both refusals were correct: in each case the assertion they were guarding would otherwise
 * have been passing for the wrong reason.
 */

type Control = {
    /** Put the page into a state where the thing being guarded is definitely present. */
    arrange: (page: Page) => Promise<void>;
    /** Named in the failure message, so a stale guard says where it expected to find itself. */
    hint: string;
};

/**
 * Assert `locate` matches nothing on the current page, having first proved on a control state
 * that it still matches something.
 *
 * The control is the whole point. If the locator has gone stale the guard fails there and
 * names it, instead of the absence assertion passing for the wrong reason.
 */
export async function absentHere(
    page: Page,
    locate: (page: Page) => Locator,
    control: Control,
) {
    const target = page.url();

    await control.arrange(page);
    await expect(
        locate(page),
        `Control failed: the locator matched nothing on ${control.hint}, where it is expected. ` +
            `It is stale, so the absence check that follows would have passed without testing ` +
            `anything. Update the locator rather than the control.`,
    ).not.toHaveCount(0);

    await page.goto(target);
    await expect(locate(page)).toHaveCount(0);
}

/** The common case: the control is simply another page. */
export function atUrl(url: string, hint: string): Control {
    return { arrange: async (page) => void (await page.goto(url)), hint };
}
