import { expect, test, type Page } from "@playwright/test";
import { absentHere, atUrl } from "./guards";
import { PLATES } from "../../src/lib/lab";

/**
 * The Phase 8 surfaces: the Visualization Lab, About, and Sources and method.
 *
 * The journeys asserted here are the ones the phase brief names as mandatory, and the
 * assertions are about claims rather than pixels. What matters on these pages is that a plate
 * states what it does not show, that no plate is a dead end, that the two editorial pages that
 * six existing links already promised now exist, and that the sources page names sources the
 * build actually loaded.
 */

/* ------------------------------------------------------------------- lab - */

test.describe("the Lab index", () => {
    test("lists every plate in the catalogue, with its question and its caution", async ({
        page,
    }) => {
        await page.goto("/visualizations");

        for (const plate of PLATES) {
            const card = page.locator(".va-lab-card", { hasText: plate.title });
            await expect(card, plate.slug).toHaveCount(1);
            await expect(card.getByText(plate.question)).toBeVisible();
            /* The caution is the first thing a card layout drops and the thing that must not
               be dropped: it is what stops the figure being read as more than it is. */
            await expect(card.locator(".va-lab-card-caution")).toBeVisible();
        }
    });

    test("says what it considered and refused to draw", async ({ page }) => {
        await page.goto("/visualizations");
        const omissions = page.locator(".va-lab-omissions");
        await expect(omissions).toBeVisible();
        await expect(omissions.getByText(/Metre across the four collections/i)).toBeVisible();
        await expect(omissions.getByText(/Communities of deities/i)).toBeVisible();
    });

    test("carries a measured figure on its cards rather than a sketch", async ({ page }) => {
        await page.goto("/visualizations");
        const corpus = page.locator(".va-lab-card", { hasText: "Four corpora" });
        // 20,210 verses, read from the API at request time.
        await expect(corpus.locator(".va-lab-card-figure b")).toHaveText(/^\d[\d,]+$/);
        await expect(corpus.getByRole("rowheader", { name: /RV/ })).toBeVisible();
    });
});

/* ---------------------------------------------------------------- plates - */

for (const plate of PLATES) {
    test.describe(`the ${plate.slug} plate`, () => {
        test("answers all five questions of the visualization standard", async ({ page }) => {
            await page.goto(`/visualizations/${plate.slug}`);
            await expect(page.getByRole("heading", { level: 1, name: plate.title })).toBeVisible();

            const label = page.locator(".va-plate-label");
            await expect(label).toBeVisible();
            for (const term of [
                "What is measured",
                "What one mark is",
                "What is in scope",
                "What is excluded",
                "What this does not show",
            ]) {
                await expect(label.getByText(term, { exact: true })).toBeVisible();
            }
            await expect(label.getByText(plate.label.notInfer)).toBeVisible();
        });

        test("keeps an interpretation visibly apart from a count", async ({ page }) => {
            await page.goto(`/visualizations/${plate.slug}`);
            await expect(page.locator('[data-knowledge-kind="derived-metric"]')).not.toHaveCount(0);
        });

        test("is never a dead end", async ({ page }) => {
            await page.goto(`/visualizations/${plate.slug}`);
            const onward = page.locator(".va-plate-handoff a");
            await expect(onward.first()).toBeVisible();
            expect(await onward.count()).toBeGreaterThanOrEqual(2);
        });
    });
}

/* --------------------------------------------------- mandatory journeys - */

test.describe("Lab to a visualization to the evidence", () => {
    test("reaches a deity record from the deities plate", async ({ page }) => {
        await page.goto("/visualizations");
        await page.getByRole("link", { name: "Named, and dedicated to" }).click();
        await expect(page).toHaveURL(/\/visualizations\/deities/);

        await page.getByRole("rowheader", { name: "Indra" }).getByRole("link").first().click();
        /* The deity record titles itself in IAST -- `indraḥ`, not `Indra` -- so the assertion
           is on the record being reached rather than on the display form of its name. */
        await expect(page).toHaveURL(/\/devatas\/VG%3ADEVATA%3AINDRAH/);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    });

    test("reaches a verse from the transmission plate's reuse pairs", async ({ page }) => {
        await page.goto("/visualizations/transmission");
        const flow = page.locator(".va-flow li").nth(1);
        await expect(flow).toBeVisible();
        const citation = await flow.locator("a").first().innerText();
        await flow.locator("a").first().click();
        await expect(page).toHaveURL(/\/passage\//);
        await expect(page.getByText(citation, { exact: false }).first()).toBeVisible();
    });

    test("reaches a condition record from the human concerns plate", async ({ page }) => {
        await page.goto("/visualizations/human-concerns");
        const affliction = page.locator(".va-panel", { hasText: "Afflictions" });
        await affliction.getByRole("rowheader").first().getByRole("link").click();
        await expect(page).toHaveURL(/\/entities\/condition\//);
    });
});

test.describe("About to method to a source", () => {
    test("About reaches the method page, which reaches the editions", async ({ page }) => {
        await page.goto("/about");
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

        await page
            .getByRole("link", { name: /Sources and method/ })
            .first()
            .click();
        await expect(page).toHaveURL(/\/sources$/);

        await page.locator("#sources").scrollIntoViewIfNeeded();
        await expect(page.locator(".va-source").first()).toBeVisible();
        // The editions are named, not described in the abstract.
        await expect(
            page.locator(".va-source-id code", { hasText: "GRETIL" }).first(),
        ).toBeVisible();
        await expect(page.getByText(/Aufrecht|G.ttingen/).first()).toBeVisible();
    });

    test("the method page reaches a verse from its worked example", async ({ page }) => {
        await page.goto("/sources#method-attribution");
        await expect(page.locator(".va-doc-example")).toBeVisible();
        await page.getByRole("link", { name: /deities plate draws the two side by side/ }).click();
        await expect(page).toHaveURL(/\/visualizations\/deities/);
    });
});

/* ------------------------------------------------------------- the claims - */

test.describe("what these pages refuse to say", () => {
    test("the deities plate never merges naming with dedication", async ({ page }) => {
        await page.goto("/visualizations/deities");
        await expect(page.getByText(/missing index, not an absent god/i)).toBeVisible();
        await expect(
            page.getByRole("heading", { level: 3, name: "Named", exact: true }),
        ).toBeVisible();
        await expect(
            page.getByRole("heading", { level: 3, name: "Dedicated to", exact: true }),
        ).toBeVisible();
    });

    test("the human concerns plate keeps a threat off the list of afflictions", async ({
        page,
    }) => {
        await page.goto("/visualizations/human-concerns");
        await expect(page.getByText(/A demon is not a disease/i)).toBeVisible();

        /* The specific regression: demons ranked as illnesses. `rakṣas` is a THREAT and must
           appear in the threats panel and nowhere in the afflictions panel. */
        const threats = page.locator(".va-panel", { hasText: "Threats" });
        await expect(threats.getByText(/rak.as/i).first()).toBeVisible();
        const afflictions = page.locator(".va-panel", { hasText: "Afflictions" });
        await expect(afflictions.getByText(/rak.as/i)).toHaveCount(0);
    });

    test("the transmission matrix types its empty cells rather than zeroing them", async ({
        page,
    }) => {
        await page.goto("/visualizations/transmission");
        const key = page.locator(".va-matrix-key");
        await expect(key).toBeVisible();

        /*
         * Every mark on the grid is explained in the key, and the key explains nothing that
         * is not on the grid.
         *
         * Two specific legend sentences were pinned here, and one of them -- "never
         * established for this pair" -- stopped rendering when the measurement behind those
         * cells moved from NOT_ESTABLISHED_FOR_PAIR to MEASURED_ZERO. The legend is built
         * from the statuses actually present, which is correct behaviour and the reason a
         * sentence pinned in a test is the wrong thing to assert: the claim is that no mark
         * is unexplained, and it survives the data moving underneath it.
         */
        const cells = page.locator(".va-matrix tbody td");
        expect(await cells.count()).toBeGreaterThan(0);

        const statuses = new Set<string>();
        for (const cell of await cells.all()) {
            const status = await cell.getAttribute("data-cell");
            /* An untyped cell would render as an empty box and read as a zero. */
            expect(status, "a matrix cell carries no status").toMatch(/\w+/);
            statuses.add(status!);
        }

        const keyText = await key.innerText();
        const nonCount = [...statuses].filter((status) => status !== "MEASURED");
        expect(nonCount.length, "no cell on this grid is anything but a count").toBeGreaterThan(0);
        for (const status of nonCount) {
            const mark = await page
                .locator(`.va-matrix tbody td[data-cell="${status}"]`)
                .first()
                .innerText();
            expect(keyText, `${status} prints "${mark}" and the key does not explain it`).toContain(
                mark.trim(),
            );
        }
        /* The most misreadable of them all, whenever it is on the grid. */
        if (statuses.has("NOT_BUILT")) {
            await expect(key.getByText(/does not exist anywhere in this graph/i)).toBeVisible();
        }
    });

    test("the material culture plate shows the cell it knows is wrong", async ({ page }) => {
        await page.goto("/visualizations/material-culture");
        await expect(page.getByText(/this cell is empty and it should not be/i)).toBeVisible();
        await expect(page.locator('.va-matrix td[data-cell="DECLARED_GAP"]')).not.toHaveCount(0);
    });

    test("the ritual plate states its coverage before its content", async ({ page }) => {
        await page.goto("/visualizations/ritual");
        const note = page.locator(".va-plate-note").first();
        const figure = page.locator("#rites");
        await expect(note).toBeVisible();
        await expect(note).toContainText(/modelled coverage, not a taxonomy/i);
        const noteBox = await note.boundingBox();
        const figureBox = await figure.boundingBox();
        expect(noteBox!.y).toBeLessThan(figureBox!.y);
    });

    test("About says what VedAnvaya is not, in its own section", async ({ page }) => {
        await page.goto("/about");
        const section = page.locator("#not");
        await expect(section.getByRole("heading", { name: /What VedAnvaya is not/ })).toBeVisible();
        await expect(section.getByText(/Not a replacement for reading the Vedas/)).toBeVisible();
        await expect(section.getByText(/Not philology/)).toBeVisible();
    });

    test("the method page explains the evidence layers and the certainty grades", async ({
        page,
    }) => {
        await page.goto("/sources");
        await expect(page.locator("#method-layers").getByText("Interpretive claim")).toBeVisible();
        await expect(
            page.locator("#method-certainty").getByText("AMBIGUOUS", { exact: true }),
        ).toBeVisible();
        await expect(page.getByText(/INSUFFICIENT_EVIDENCE/).first()).toBeVisible();
        await expect(
            page.locator("#method-ask").getByText(/model is not the database/i),
        ).toBeVisible();
        await expect(
            page.locator("#method-audio").getByText(/streamed from its source/i),
        ).toBeVisible();
    });
});

/* --------------------------------------------------------------- the shell - */

test.describe("navigation", () => {
    test("no longer promises a page that does not exist", async ({ page }) => {
        /* Before this phase the footer, the overflow menu, the homepage and the 404 page all
           linked to /about and /sources, and all six links 404'd. */
        for (const url of ["/about", "/sources", "/visualizations"]) {
            const response = await page.goto(url);
            expect(response?.status(), url).toBe(200);
        }
    });

    test("answers the short names for the two surfaces that have them", async ({ page }) => {
        await page.goto("/lab");
        await expect(page).toHaveURL(/\/visualizations$/);
        await page.goto("/methodology");
        await expect(page).toHaveURL(/\/sources$/);
    });

    test("puts Visualize in the primary bar and marks it as current", async ({ page }) => {
        await page.goto("/visualizations");
        const link = page.getByRole("navigation").getByRole("link", { name: "Visualize" }).first();
        await expect(link).toBeVisible();
        await expect(link).toHaveAttribute("aria-current", "page");
    });
});

/* ----------------------------------------------------------- accessibility - */

const headingOrderOf = async (page: Page) =>
    page.evaluate(() =>
        [...document.querySelectorAll("main h1, main h2, main h3, main h4")].map((node) =>
            Number(node.tagName[1]),
        ),
    );

test.describe("accessibility", () => {
    for (const url of ["/visualizations", "/visualizations/four-corpora", "/about", "/sources"]) {
        test(`${url} has exactly one h1 and no skipped heading level`, async ({ page }) => {
            await page.goto(url);
            const levels = await headingOrderOf(page);
            expect(levels.filter((level) => level === 1)).toHaveLength(1);
            for (let index = 1; index < levels.length; index += 1) {
                expect(
                    levels[index] - levels[index - 1],
                    `${url}: h${levels[index - 1]} is followed by h${levels[index]}`,
                ).toBeLessThanOrEqual(1);
            }
        });
    }

    test("every figure is announced by its own name", async ({ page }) => {
        await page.goto("/visualizations/four-corpora");
        for (const figure of await page.locator("figure.va-figure").all()) {
            await expect(figure).toHaveAttribute("aria-labelledby", /.+/);
        }
    });

    test("every chart is a table with a caption", async ({ page }) => {
        await page.goto("/visualizations/human-concerns");
        const tables = page.locator(".va-rank, .va-strip");
        expect(await tables.count()).toBeGreaterThan(0);
        for (const table of await tables.all()) {
            await expect(table.locator("caption")).toHaveCount(1);
        }
    });

    test("a plate's controls are links, so each view has an address", async ({ page }) => {
        await page.goto("/visualizations/four-corpora");
        const controls = page.locator(".va-controls a");
        expect(await controls.count()).toBeGreaterThan(1);
        await controls.filter({ hasText: "Per 1,000" }).click();
        await expect(page).toHaveURL(/scale=share/);
        await expect(page.getByText(/per 1,000/i).first()).toBeVisible();
    });

    test("the Lab ships no client-side chart runtime", async ({ page }) => {
        /* The Lab is server-rendered end to end: the controls are links and the reveals are
           `<details>`. Three.js belongs to the Knowledge World and must not follow a reader
           onto an editorial page. */
        const requests: string[] = [];
        page.on("request", (request) => requests.push(request.url()));
        await page.goto("/visualizations/four-corpora", { waitUntil: "networkidle" });
        expect(requests.filter((url) => /three|chart|d3-/i.test(url))).toHaveLength(0);
    });
});

test.describe("the deities plate opts into ambiguity loudly", () => {
    test("the exploratory view warns before it shows a figure", async ({ page }) => {
        /* The warning belongs to the opted-in view and nowhere else. `absentHere` proves the
           locator still matches on the exploratory page before asserting it is missing from
           the default one, so this cannot pass because the copy was renamed. */
        await page.goto("/visualizations/deities");
        await absentHere(
            page,
            (target) => target.getByText(/You are looking at the exploratory view/i),
            atUrl("/visualizations/deities?certainty=exploratory", "the exploratory view"),
        );
        await expect(page.getByText(/Excludes AMBIGUOUS mentions/i)).toBeVisible();
    });
});
