import { expect, test, type Page } from "@playwright/test";
import { failingContrast } from "./contrast";

/**
 * The homepage.
 *
 * Two things are protected here beyond "the page renders". The first is that every figure on
 * the page comes from the API rather than from a constant, so these assert the shape of a
 * figure and its relation to the corpus rather than its value; a data rebuild should not turn
 * this file red. The second is that the page's honesty devices survive a restyle: the typed
 * absences, the Samavedic statement, and the fact that the two verses shown are two verses.
 */

const VIEWPORTS = [
    { name: "desktop", width: 1440, height: 900 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "phone", width: 390, height: 844 },
] as const;

async function home(page: Page) {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

test.describe("homepage: the opening claim", () => {
    test("the hero states what is held and offers both ways in", async ({ page }) => {
        await home(page);

        const heading = page.getByRole("heading", { level: 1 });
        await expect(heading).toContainText(/four samhitas/i);
        await expect(heading).toContainText(/evidence/i);

        // The brand line is Devanagari and must be marked as Sanskrit, or a screen reader
        // reads it with English phonetics and a translation tool offers to translate it.
        const brand = page.locator(".va-hero-brand");
        await expect(brand).toHaveText("वेदान्वय");
        await expect(brand).toHaveAttribute("lang", "sa");

        await expect(page.getByRole("link", { name: "Read the Vedas" }).first()).toBeVisible();
        await expect(page.getByRole("link", { name: "Open the graph" }).first()).toBeVisible();
    });

    test("the primary action reaches the Vedas and the graph action reaches the graph", async ({
        page,
    }) => {
        await home(page);
        await page.getByRole("link", { name: "Read the Vedas" }).first().click();
        await expect(page).toHaveURL(/\/vedas$/);

        await home(page);
        await page.getByRole("link", { name: "Open the graph" }).first().click();
        await expect(page).toHaveURL(/\/graph/);
    });

    test("the signal line counts the corpus, not the build", async ({ page }) => {
        await home(page);
        const signal = page.locator(".va-hero-signal");
        await expect(signal).toContainText(/\d[\d,]* verses/);
        await expect(signal).toContainText(/\d[\d,]* recitations/);
        // The graph's relationship total is withheld by the API, which says why: most of its
        // edges are one annotation layer's projection of a container label onto the passages
        // inside it, so a headline built from them measures the build rather than the corpus.
        // No surface may print it, and the homepage is where the temptation is strongest.
        await expect(signal).not.toContainText(/relationship/i);
    });
});

test.describe("homepage: the sections are present and distinct", () => {
    test("every section renders and the heading order is sound", async ({ page }) => {
        await home(page);

        for (const phrase of [
            /one recension each/i,
            /everything standing behind it/i,
            /own recitation/i,
            /more than one collection/i,
            /check the answer/i,
            /whose nothing it is/i,
            /where to start/i,
        ]) {
            await expect(page.getByRole("heading", { name: phrase })).toBeVisible();
        }

        await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);

        // No heading level may be skipped. An h3 with no h2 above it leaves anyone browsing
        // by heading unable to tell what the h3 belongs to.
        const levels = await page.evaluate(() =>
            [...document.querySelectorAll("main h1, main h2, main h3, main h4")].map((h) =>
                Number(h.tagName[1]),
            ),
        );
        for (let i = 1; i < levels.length; i++) {
            expect(levels[i] - levels[i - 1]).toBeLessThanOrEqual(1);
        }
    });

    test("the ledger names a recension for each collection and what is not held", async ({
        page,
    }) => {
        await home(page);
        const ledger = page.locator(".va-ledger");
        await expect(ledger).toBeVisible();
        await expect(ledger.locator("tbody tr")).toHaveCount(4);

        const rows = [
            ["Rigveda", /Śākala/],
            ["Samaveda", /ārcika only/],
            ["Yajurveda", /Mādhyandina/],
            ["Atharvaveda", /Śaunaka/],
        ] as const;
        for (const [name, recension] of rows) {
            await expect(ledger.locator("tbody tr").filter({ hasText: name })).toContainText(
                recension,
            );
        }

        // The Krishna Yajurveda is the omission most likely to mislead, because "the
        // Yajurveda" ordinarily means both it and the White. It has to be named on the page.
        await expect(page.locator(".va-ledger-section")).toContainText(/Krishna Yajurveda/);
    });
});

test.describe("homepage: absence is typed, not blank", () => {
    test("the Samaveda has no translation and no recitation and both say so in words", async ({
        page,
    }) => {
        await home(page);

        const row = page.locator(".va-ledger tbody tr").filter({ hasText: "Samaveda" });
        // "none", not "0". A zero beside four-figure counts reads as a rounding artefact, and
        // this is the most informative cell in the table.
        await expect(row.locator(".va-ledger-zero")).toHaveCount(2);

        const absence = page.locator(".va-bar-row.is-absent");
        await expect(absence).toHaveCount(1);
        await expect(absence).toContainText(/No recording exists/i);
        // The claim is about what has been published, not about the tradition.
        await expect(absence).toContainText(/published/i);
    });

    test("the three states of nothing are each named", async ({ page }) => {
        await home(page);
        const list = page.locator(".va-absence-list");
        await expect(list.locator("dt")).toHaveCount(3);
        await expect(list).toContainText("Not built");
        await expect(list).toContainText("Insufficient evidence");
        await expect(list).toContainText("Partial");
        await expect(list).toContainText(/not a zero/i);
    });

    test("the Samavedic recitation row draws no bar at all", async ({ page }) => {
        await home(page);
        // A zero-length bar would sit in the same visual sentence as the other three and read
        // as "almost none", which is a different claim from "none exists anywhere".
        //
        // The control and the subject are on the same page, so this does not use absentHere:
        // that helper proves a selector still matches on some other page, and this selector
        // can never match anywhere, because the whole claim is that the absent row has no
        // track. A first draft did reach for it and the guard refused, correctly. The control
        // here is the other three rows, which must still draw tracks.
        await expect(page.locator(".va-bar-row:not(.is-absent) .va-bar-track")).toHaveCount(3);
        await expect(page.locator(".va-bar-row.is-absent")).toHaveCount(1);
        await expect(page.locator(".va-bar-row.is-absent .va-bar-track")).toHaveCount(0);
        await expect(page.locator(".va-bar-row.is-absent .va-bar-fill")).toHaveCount(0);
    });
});

test.describe("homepage: the Sanskrit is real", () => {
    test("both verses shown are real, different, and free of placeholder text", async ({
        page,
    }) => {
        await home(page);

        const frame = page.locator(".va-verse-frame .va-sanskrit");
        const plate = page.locator(".va-plate-verse");
        await expect(frame).toBeVisible();
        await expect(plate).toBeVisible();

        const first = await frame.innerText();
        const second = await plate.innerText();
        // A first implementation fed both sections the same passage, so the page printed one
        // verse twice and the reader preview linked to somewhere it had not shown.
        expect(first).not.toEqual(second);

        for (const text of [first, second]) {
            expect(text.trim().length).toBeGreaterThan(20);
            // No replacement character and no dotted circle. The dotted circle is the
            // shaper's own failure glyph and is how a missing combining mark surfaces.
            expect(text).not.toMatch(/[�◌]/);
            expect(text).not.toMatch(/lorem|ipsum|TODO|placeholder|xxx/i);
            // Private Use Area characters exist in some surfaces of this corpus and render as
            // an empty box in every font.
            expect(text).not.toMatch(/[-]/);
        }

        // Both are Rigvedic, which is held in romanised IAST only, so the frame must be
        // marked as IAST and the text must still carry the marks that carry the accent.
        await expect(frame).toHaveAttribute("data-script", "IAST");
        expect(first).toMatch(/[̀-ͯ]/);
    });

    test("the verse face is the self-hosted one, not a CDN fallback", async ({ page }) => {
        await home(page);
        const family = await page
            .locator(".va-plate-verse")
            .evaluate((el) => getComputedStyle(el).fontFamily);
        // Charis SIL is vendored and subsetted because the Google Fonts CDN serves none of
        // U+0331, U+030D or U+0325 for any Latin font, and those are the marks this corpus
        // writes its Vedic accents with. If this stack ever resolves to a CDN face again the
        // accents go back to being drawn by an unpredictable system fallback.
        expect(family.toLowerCase()).toMatch(/charis/);
    });
});

test.describe("homepage: responsive and reachable", () => {
    for (const view of VIEWPORTS) {
        test(`nothing overflows the viewport at ${view.name}`, async ({ page }) => {
            await page.setViewportSize({ width: view.width, height: view.height });
            await home(page);
            const overflow = await page.evaluate(
                () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
            );
            expect(overflow).toBeLessThanOrEqual(1);
        });
    }

    test("the primary action is reachable without scrolling on a phone", async ({ page }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await home(page);
        const box = await page.getByRole("link", { name: "Read the Vedas" }).first().boundingBox();
        expect(box).not.toBeNull();
        // A homepage whose only call to action sits below the fold on the most common
        // viewport has asked the reader to take on trust that there is one.
        expect(box!.y + box!.height).toBeLessThanOrEqual(view844());
    });

    test("the world preview offers the same content as text", async ({ page }) => {
        await home(page);
        // The canvas is hidden from assistive technology, so the list beside it is the whole
        // of what a screen reader receives. It has to be the content, not a description of it,
        // and each subject has to be reachable rather than merely named.
        await expect(page.locator(".va-world-preview-canvas")).toHaveAttribute(
            "aria-hidden",
            "true",
        );
        await expect(
            page.getByRole("heading", { name: /world preview, as a list/i }),
        ).toBeAttached();
        const items = page.locator(".va-world-preview-panel .sr-only li");
        expect(await items.count()).toBeGreaterThan(8);
        await expect(items.first()).toContainText(/\w/);
        await expect(items.first().locator("a")).toHaveAttribute("href", /\/graph\?/);
    });

    for (const view of VIEWPORTS) {
        test(`every piece of text on the page meets AA at ${view.name}, in both themes`, async ({
            page,
        }) => {
            await page.setViewportSize({ width: view.width, height: view.height });
            for (const dark of [false, true]) {
                await page.emulateMedia({ colorScheme: dark ? "dark" : "light" });
                await page.addInitScript(
                    (value) => localStorage.setItem("theme", value),
                    dark ? "dark" : "light",
                );
                await home(page);
                // The Ask section paints the Thread of Inquiry behind its type, and the hero
                // paints the manuscript plate behind the headline. Both are the kind of thing
                // that quietly costs a point of contrast, so the page is walked rather than
                // spot-checked.
                expect(await failingContrast(page)).toEqual([]);
            }
        });
    }

    test("every interactive element in the page body is a link or a button", async ({ page }) => {
        await home(page);
        const bad = await page.evaluate(() =>
            [...document.querySelectorAll("main [onclick], main [role='button']")]
                .filter((el) => !["A", "BUTTON"].includes(el.tagName))
                .map((el) => el.tagName),
        );
        expect(bad).toEqual([]);
    });
});

/** The phone viewport height these tests use, named so the assertion reads as a claim. */
function view844() {
    return 844;
}
