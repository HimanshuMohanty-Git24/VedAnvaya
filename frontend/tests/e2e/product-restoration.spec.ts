import { expect, test, type Page } from "@playwright/test";

/**
 * The defects the owner reported after the data-completeness campaign, held.
 *
 * Every assertion here was reachable from a browser and from nowhere else: the graph
 * neighbourhood is drawn from a packed artifact the unit tests read off disk but that a
 * reader reaches over HTTP with a year-long cache header; the reader page is a server
 * component assembled from four endpoints; and the copy assertions are about what is on a
 * page rather than what is in a file, which a grep cannot settle once a figure is read from
 * an API.
 *
 * They are written as minimums and as absences, never as exact counts. The corpus is frozen
 * but the layers over it are not, and a test that fails when Indra gains a relationship is a
 * test that gets deleted the first time it does.
 */

/** The world artifact is megabytes and a settling layout; the graph is not a fast page. */
const SETTLE = 30_000;

/** Samavedic verses chosen for what they carry, and verified to carry it. */
const SV_WITH_EVERYTHING = "VG:SV:KAU:CHANDA:P01:D01:V01";
const SV_THIN = "VG:SV:KAU:MAHANAMNYA:V01";

/** This project's own issue tracker. A reader cannot look any of these up. */
const INTERNAL_VOCABULARY = [
    /GAP-AUDIO-\d/,
    /GAP-QUALITY-\d/,
    /REGISTRY_IMPLEMENTATION_FIXABLE/,
    /owner-decision-required/,
    /\bGate [ABC]:/,
];

async function bodyText(page: Page) {
    return (await page.locator("body").innerText()).replace(/\s+/g, " ");
}

/** Open the graph, find a subject by name, and select the first hit. */
async function findAndSelect(page: Page, needle: string) {
    await page.goto("/graph");
    const find = page.locator("#graph-find");
    await find.waitFor({ state: "visible", timeout: SETTLE });
    await find.fill(needle);
    const hits = page.locator(".va-world-hits li");
    await expect(hits.first()).toBeVisible({ timeout: SETTLE });
    return hits;
}

test.describe("entity search names the right kind of thing", () => {
    test("the graph's own search types a deity as a deity, and not everything as one kind", async ({
        page,
    }) => {
        /*
         * Reported: a search for "Indra" showed nearly every result labelled RITE, including
         * rows that were plainly not rites. Two assertions, because either alone passes for
         * the wrong reason: the canonical deity must be typed as a deity, and the page must
         * not be one type end to end.
         */
        const hits = await findAndSelect(page, "indra");
        const rows = await hits.allInnerTexts();
        expect(rows.length).toBeGreaterThan(1);

        const indra = rows.find((row) => row.split("\n")[0].trim() === "Indra");
        expect(indra, `no row named exactly "Indra" among ${JSON.stringify(rows)}`).toBeTruthy();
        expect(indra).toMatch(/DEITY/i);

        const kinds = new Set(rows.map((row) => row.split("\n")[1]?.trim()).filter(Boolean));
        expect(kinds.size, `every hit was ${[...kinds]}`).toBeGreaterThan(1);
    });

    test("the search page types a deity, a seer and a formula apart", async ({ page }) => {
        await page.goto("/search?q=indra");
        const results = page.locator("main");
        await expect(results).toContainText("results for indra", { timeout: SETTLE });
        const text = await bodyText(page);
        expect(text).toMatch(/DEVATA/);
        expect(text).toMatch(/RISHI|FORMULA/);
    });
});

test.describe("a major deity is a neighbourhood, not a star of verses", () => {
    for (const [name, id] of [
        ["Indra", "VG:DEVATA:INDRAH"],
        ["Varuna", "VG:DEVATA:VARUNAH"],
    ] as const) {
        test(`${name} focuses into several kinds of connected subject`, async ({ page }) => {
            await page.goto(`/graph?view=focus&node=${encodeURIComponent(id)}`);
            const rows = page.locator(".va-world-neighbours li");
            await expect(rows.first()).toBeVisible({ timeout: SETTLE });

            const listed = await rows.allInnerTexts();
            expect(listed.length).toBeGreaterThan(1);

            const kinds = new Set(
                listed.map((row) => row.split("\n").pop()?.trim()).filter(Boolean),
            );
            /*
             * More than one *kind*, which is the assertion a count survives. The reported
             * failure was "approximately one useful connection", and forty verses joined by
             * one predicate satisfies any count while being exactly that complaint.
             */
            expect(kinds.size, `${name} drew only ${[...kinds]}`).toBeGreaterThan(2);
            expect(
                [...kinds].some((kind) => /deity/i.test(kind ?? "")),
                `${name} drew no other deity: ${[...kinds]}`,
            ).toBe(true);
        });
    }

    test("Indra's scene is not mostly passages and evidence records", async ({ page }) => {
        await page.goto("/graph?view=focus&node=VG%3ADEVATA%3AINDRAH");
        const rows = page.locator(".va-world-neighbours li");
        await expect(rows.first()).toBeVisible({ timeout: SETTLE });
        const listed = await rows.allInnerTexts();
        const apparatus = listed.filter((row) =>
            /(PASSAGE|EVIDENCE RECORD|DERIVED METRIC)\s*$/i.test(row.trim()),
        );
        expect(
            apparatus.length,
            `${apparatus.length} of ${listed.length} rows are apparatus`,
        ).toBeLessThan(listed.length / 2);
    });

    test("no drawn subject shouts a pipeline constant or a raw graph id", async ({ page }) => {
        /*
         * `IS_OR_BECOMES` and `DEVATA_ATTRIBUTION_BY_VEDA (VG:DEVATA:INDRAH)` are the two
         * label families the artifact stores as vocabulary rather than as words, and eight of
         * the twelve idea seats in Indra's scene were the first kind.
         */
        await page.goto("/graph?view=focus&node=VG%3ADEVATA%3AINDRAH");
        const rows = page.locator(".va-world-neighbours li");
        await expect(rows.first()).toBeVisible({ timeout: SETTLE });
        for (const row of await rows.allInnerTexts()) {
            const label = row.split("\n")[0].trim();
            expect(label, `${label} is a shouted constant`).not.toMatch(/^[A-Z][A-Z0-9_]*$/);
            expect(label, `${label} carries a raw graph id`).not.toContain("VG:");
        }
    });
});

test.describe("the Samaveda is readable", () => {
    test("a Samavedic verse shows its text, its rendering, its notation and its phrases", async ({
        page,
    }) => {
        await page.goto(`/passage/${encodeURIComponent(SV_WITH_EVERYTHING)}`);
        const text = await bodyText(page);

        // Canonical Sanskrit, in Devanagari, actually rendered.
        const verse = page.locator(".va-verse");
        await expect(verse).toBeVisible();
        expect((await verse.innerText()).trim().length).toBeGreaterThan(20);

        // The English, named as what it is, with the verse it came from.
        expect(text).toMatch(/Rigvedic parallel|rendering via/i);
        expect(text).toMatch(/RV \d+\.\d+\.\d+/);

        // The notation witness, as its own section rather than buried in a disclosure.
        await expect(page.getByRole("heading", { name: /svara notation/i })).toBeVisible();

        // The formula layer, which the reader payload did not carry before this pass.
        await expect(page.getByRole("heading", { name: /fixed phrases/i })).toBeVisible();
    });

    test("a Samavedic verse with nothing attached is still a page, not a wall of warnings", async ({
        page,
    }) => {
        await page.goto(`/passage/${encodeURIComponent(SV_THIN)}`);
        const verse = page.locator(".va-verse");
        await expect(verse).toBeVisible();
        expect((await verse.innerText()).trim().length).toBeGreaterThan(20);

        const text = await bodyText(page);
        for (const pattern of INTERNAL_VOCABULARY) {
            expect(text, `the reader page says ${pattern}`).not.toMatch(pattern);
        }
        /* An absence states itself once, in a line, and points at the page that explains it. */
        expect(text).toMatch(/No English rendering is linked to this verse/i);
    });

    test("the other three corpora still read", async ({ page }) => {
        for (const key of [
            "VG:RV:SAK:M01:S001:V001",
            "VG:YV:VSM:A01:V001",
            "VG:AV:SAU:K01:S001:V001",
        ]) {
            await page.goto(`/passage/${encodeURIComponent(key)}`);
            await expect(page.locator(".va-verse")).toBeVisible();
        }
    });
});

test.describe("normal product pages do not speak to themselves", () => {
    for (const route of ["/", "/vedas", "/vedas/samaveda", "/connections", "/graph"]) {
        test(`${route} carries no internal identifier`, async ({ page }) => {
            await page.goto(route);
            await page.waitForLoadState("domcontentloaded");
            const text = await bodyText(page);
            for (const pattern of INTERNAL_VOCABULARY) {
                expect(text, `${route} says ${pattern}`).not.toMatch(pattern);
            }
        });
    }

    test("the homepage leads with what the product does", async ({ page }) => {
        await page.goto("/");
        const text = await bodyText(page);
        expect(text).toContain("20,210");
        /* The wall of absences is gone. Counted rather than forbidden outright: scope is
           allowed to be stated once, and this is the count at which it became the page. */
        const absences = (text.match(/\bnot held\b|\bunavailable\b|\bwithheld\b/gi) ?? []).length;
        expect(absences, `the homepage states an absence ${absences} times`).toBeLessThan(4);
    });
});

test.describe("connections reads as a product", () => {
    test("it leads with connection kinds and keeps the matrix behind a disclosure", async ({
        page,
    }) => {
        await page.goto("/connections");
        const text = await bodyText(page);
        expect(text).toMatch(/exact parallel/i);
        expect(text).toMatch(/near parallel/i);
        expect(text).toMatch(/reuse/i);

        /* The full matrix is still reachable, and is not the first thing on the page. */
        const disclosure = page.getByText(/full evidence matrix/i).first();
        await expect(disclosure).toBeVisible();
    });

    test("no table forces the page into a horizontal scroll", async ({ page }) => {
        await page.goto("/connections");
        await page.waitForLoadState("networkidle");
        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow, `the page scrolls ${overflow}px horizontally`).toBeLessThanOrEqual(1);
    });
});
