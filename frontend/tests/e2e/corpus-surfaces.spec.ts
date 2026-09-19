import { expect, test, type Page } from "@playwright/test";
import { absentHere, atUrl } from "./guards";

/**
 * The Phase 4 surfaces: the collection index, one collection, the reader, and the deity and
 * entity records.
 *
 * The assertions here are about claims rather than about pixels. What matters on these pages
 * is that a limit is stated before a reader starts counting, that an absence is typed rather
 * than blank, that the four corpora keep their own vocabulary instead of being flattened into
 * a Rigveda-shaped tree, and that Vedic text lands in a face that can actually place its
 * accents. A layout regression will show up in a screenshot; these would not.
 */

const RV_1_1_1 = "VG:RV:SAK:M01:S001:V001";
const SV_NO_AUDIO = "VG:SV:KAU:ARANYA:D03:V04";

const reader = (key: string) => `/passage/${encodeURIComponent(key)}`;

/* ------------------------------------------------------------------ vedas - */

test.describe("the collection index", () => {
    test("names each recension, and reaches the page that names the exclusions", async ({
        page,
    }) => {
        await page.goto("/vedas");

        /*
         * The recension stays here. The exclusions moved.
         *
         * /vedas is a reading gateway in this phase's direction, and each card used to carry
         * a paragraph of what that edition does not hold - three of the four opened on an
         * absence. The exclusions are not gone and are not softened: they are on /limits, in
         * full, per edition, and this test follows the link to check rather than trusting it.
         */
        for (const recension of [/Śākala/, /Kauthuma/, /Mādhyandina/, /Śaunaka/]) {
            await expect(page.getByText(recension).first()).toBeVisible();
        }
        await expect(page.getByText(/scope page|what is not held|limits/i).first()).toBeVisible();

        const limits = await page.request.get("/limits");
        expect(limits.status()).toBe(200);
        const scope = await limits.text();
        /* The Krishna (Black) Yajurveda is the omission most likely to mislead, because the
           name ordinarily covers both. The gana collections and the Paippalada recension are
           the other two a reader would otherwise assume were here. */
        expect(scope).toMatch(/Krishna|Kṛṣṇa|Black/i);
        expect(scope).toMatch(/Taittirīya/);
        expect(scope).toMatch(/gāna|Gāna|Grāmageya/);
        expect(scope).toMatch(/Paippalāda/);

        /* Samaveda has no translation layer at all. It must read as a typed "none", never as
           a zero that invites the reader to infer the verses are untranslatable. */
        const samaveda = page.locator(".va-collection", { hasText: "Samaveda" });
        await expect(samaveda.locator(".va-fact.is-none")).not.toHaveCount(0);
    });

    test("each collection keeps its own hierarchy", async ({ page }) => {
        await page.goto("/vedas");
        const structures = await page.locator(".va-collection-structure").allInnerTexts();
        expect(structures.join(" | ")).toContain("Mandala");
        expect(structures.join(" | ")).toContain("Adhyaya");
        expect(structures.join(" | ")).toContain("Kanda");
        // Four collections, four distinct shapes. None borrows another's.
        expect(new Set(structures).size).toBe(structures.length);
    });
});

test.describe("one collection", () => {
    test("states the limit before the index", async ({ page }) => {
        await page.goto("/vedas/yajurveda");
        /* `.va-work-limit` was a block of exclusions; `.va-work-scope` is the line that
           names the edition and points at the page holding them. The claim under test is
           unchanged: a reader meets the scope of what they are about to read before they
           meet the index of it. */
        const limit = page.locator(".va-work-scope");
        const index = page.locator(".va-findaid");
        await expect(limit).toBeVisible();
        await expect(index).toBeVisible();

        const limitBox = await limit.boundingBox();
        const indexBox = await index.boundingBox();
        expect(limitBox!.y).toBeLessThan(indexBox!.y);
    });

    test("the finding aid descends in the corpus's own vocabulary", async ({ page }) => {
        await page.goto("/vedas/rigveda");
        await expect(page.locator(".va-findaid-level")).toContainText(/mandalas/i);

        await page.locator(".va-structure button").first().click();
        await expect(page.locator(".va-findaid-level")).toContainText(/suktas/i);
        await expect(page.locator(".va-findaid-trail")).toContainText("Mandala 1");

        await page.locator(".va-structure button").first().click();
        await expect(page.locator(".va-findaid-level")).toContainText(/mantras/i);
        // The leaves of the descent are verses, and a verse is a link out to the reader.
        await expect(page.locator('.va-structure a[href^="/passage/"]').first()).toBeVisible();
    });

    test("the Yajurveda has no hymn level and is not given one", async ({ page }) => {
        await page.goto("/vedas/yajurveda");
        await expect(page.locator(".va-findaid-level")).toContainText(/adhyayas/i);

        await page.locator(".va-structure button").first().click();
        /* One descent reaches mantras. Forcing a Rigveda-shaped Sukta level in between is the
           specific mistake this browser exists to avoid. */
        await expect(page.locator(".va-findaid-level")).toContainText(/mantras/i);
        await expect(page.locator(".va-findaid-trail")).not.toContainText(/sukta/i);
    });

    test("the Samaveda's top level is named, not numbered", async ({ page }) => {
        await page.goto("/vedas/samaveda");
        const values = await page.locator(".va-structure-value").allInnerTexts();
        expect(values).toContain("CHANDA");
        expect(values).toContain("UTTARA");
        // And nothing in the index collides with its neighbour at this width.
        expect(await overlappingCells(page)).toEqual([]);
    });
});

async function overlappingCells(page: Page) {
    return page.evaluate(() => {
        const cells = [...document.querySelectorAll(".va-structure > li")];
        const hits: string[] = [];
        for (let i = 0; i < cells.length; i++) {
            for (let j = i + 1; j < cells.length; j++) {
                const a = cells[i].getBoundingClientRect();
                const b = cells[j].getBoundingClientRect();
                if (a.right > b.left + 0.5 && b.right > a.left + 0.5 && a.bottom > b.top + 0.5 && b.bottom > a.top + 0.5) {
                    hits.push(`${cells[i].textContent?.trim()} / ${cells[j].textContent?.trim()}`);
                }
            }
        }
        return hits;
    });
}

/* ----------------------------------------------------------------- reader - */

test.describe("the reader", () => {
    test("sets Vedic text in a face that places its accents", async ({ page }) => {
        await page.goto(reader(RV_1_1_1));
        const verse = page.locator(".sanskrit").first();
        await expect(verse).toBeVisible();

        /*
         * The invariant, measured rather than asserted by name.
         *
         * A face with a GPOS `mark` table places a combining mark over its base at zero
         * advance, so "a" and "a̱" are exactly the same width. A face without one gives
         * the mark its own advance and it lands beside the letter instead of under it.
         *
         * The display face is the positive control: Fraunces has no `mark` table at all, so
         * it must show a non-zero advance for at least one of these. If it ever measures zero
         * everywhere, the probe has stopped measuring anything and this test is inert.
         */
        const advances = await page.evaluate(() => {
            const probe = document.createElement("span");
            probe.style.cssText =
                "position:absolute;visibility:hidden;white-space:pre;font-size:64px";
            document.body.appendChild(probe);
            const width = (text: string, family: string) => {
                probe.style.fontFamily = family;
                probe.textContent = text;
                return probe.getBoundingClientRect().width;
            };
            const verseFace = getComputedStyle(document.querySelector(".sanskrit")!).fontFamily;
            const displayFace = getComputedStyle(
                document.querySelector(".va-reader-title")!,
            ).fontFamily;
            const marks = ["̱", "̍", "̥", "̐"];
            const result = {
                verse: marks.map((m) => width("a" + m, verseFace) - width("a", verseFace)),
                display: marks.map((m) => width("a" + m, displayFace) - width("a", displayFace)),
            };
            probe.remove();
            return result;
        });

        expect(
            advances.display.some((delta) => Math.abs(delta) > 0.25),
            "Positive control failed: the display face measured a zero advance for every " +
                "combining mark, which it cannot do - it has no GPOS mark table. The probe is " +
                "broken, so the verse-face assertion below would pass without testing anything.",
        ).toBe(true);

        for (const delta of advances.verse) {
            expect(Math.abs(delta)).toBeLessThan(0.25);
        }
    });

    test("routes each script to its own face", async ({ page }) => {
        await page.goto(reader(RV_1_1_1));
        await expect(page.locator(".sanskrit").first()).toHaveAttribute("data-script", "IAST");
        expect(await faceOf(page, ".sanskrit")).toMatch(/charis/i);

        await page.goto(reader(SV_NO_AUDIO));
        await expect(page.locator(".sanskrit").first()).toHaveAttribute(
            "data-script",
            "DEVANAGARI",
        );
        expect(await faceOf(page, ".sanskrit")).toMatch(/devanagari/i);
    });

    test("shows the verse, its translation and its apparatus", async ({ page }) => {
        await page.goto(reader(RV_1_1_1));
        await expect(page.locator(".sanskrit").first()).toBeVisible();
        await expect(page.locator(".va-translation blockquote").first()).toBeVisible();
        // An ascription from the hymn heading is never presented as something the verse says.
        await expect(
            page.getByRole("heading", { name: /Ascribed in the apparatus/i }),
        ).toBeVisible();
        await expect(page.getByRole("heading", { name: /Named inside this verse/i })).toBeVisible();
    });

    test("a passage with no recitation renders no player at all", async ({ page }) => {
        /* Not a disabled player showing 0:00, which would promise a recording that does not
           exist. The control is a passage that does have one, so a renamed player class fails
           here rather than turning this into a test of nothing. */
        await page.goto(reader(SV_NO_AUDIO));
        await absentHere(
            page,
            (p) => p.locator("section.recitation"),
            atUrl(reader(RV_1_1_1), "the Rigvedic reader, which is mapped to a recording"),
        );
    });

    test("the apparatus rail never prints over its own actions", async ({ page }) => {
        await page.goto(reader(RV_1_1_1));
        await expect(page.locator(".va-apparatus-actions")).toBeVisible();

        /*
         * This is a regression test for a real defect: the rail and the apparatus inside it
         * were both `position: sticky`, so the apparatus slid down over the actions as the
         * page scrolled and the graph link printed across the deity rows. It is only visible
         * part-way down the page, which is why it is swept rather than sampled.
         */
        const max = await page.evaluate(
            () => document.documentElement.scrollHeight - window.innerHeight,
        );
        for (let y = 0; y <= max; y += 150) {
            await page.evaluate((v) => window.scrollTo(0, v), y);
            const overlap = await page.evaluate(() => {
                const a = document.querySelector(".va-apparatus")!.getBoundingClientRect();
                const b = document.querySelector(".va-apparatus-actions")!.getBoundingClientRect();
                return a.bottom - b.top;
            });
            expect(overlap, `apparatus overlaps its actions at scrollY=${y}`).toBeLessThanOrEqual(0);
        }
    });

    test("a passage connected twice is listed once, carrying both kinds", async ({ page }) => {
        await page.goto(reader(RV_1_1_1));
        const rows = page.locator(".va-apparatus-group", {
            has: page.getByRole("heading", { name: /Connected passages/i }),
        });
        const citations = await rows.locator(".va-row-value").allInnerTexts();
        expect(new Set(citations).size, "the same passage is listed twice").toBe(citations.length);
    });

    test("long text does not push the page sideways", async ({ page }) => {
        for (const key of [RV_1_1_1, "VG:YV:VSM:A31:V001", "VG:AV:SAU:K10:S008:V001"]) {
            await page.goto(reader(key));
            await expect(page.locator(".sanskrit").first()).toBeVisible();
            const overflow = await page.evaluate(
                () => document.documentElement.scrollWidth - window.innerWidth,
            );
            expect(overflow, `${key} overflows horizontally`).toBeLessThanOrEqual(0);
        }
    });
});

function faceOf(page: Page, selector: string) {
    return page.evaluate(
        (sel) => getComputedStyle(document.querySelector(sel)!).fontFamily,
        selector,
    );
}

/* ---------------------------------------------------------------- explore - */

test("explore says what each lens does not establish", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.getByText(/does not establish/i).first()).toBeVisible();
});

/* -------------------------------------------------------- deity and entity - */

test.describe("records", () => {
    test("a deity separates being named from being ascribed", async ({ page }) => {
        await page.goto("/devatas/VG%3ADEVATA%3AAGNIH");
        await expect(page.getByRole("heading", { name: /Across the four Vedas/i })).toBeVisible();
        await expect(page.getByRole("heading", { name: /Ascribed by the apparatus/i })).toBeVisible();

        /* Ambiguous mentions are excluded from every figure above them, and the page has to
           say so rather than quietly dropping them. */
        await expect(page.locator(".certainty-split .is-ambiguous")).toBeVisible();
        await expect(page.locator(".certainty-split .is-ambiguous")).toContainText(/Held back/i);
    });

    test("a deity name is set in the reading face, not the display face", async ({ page }) => {
        await page.goto("/devatas/VG%3ADEVATA%3AAGNIH");
        // `agniḥ` carries a dot-below. Set in Fraunces it would drift off the letter.
        expect(await faceOf(page, ".va-archive-name")).toMatch(/charis/i);
    });

    test("an entity with no established relationships types the absence", async ({ page }) => {
        await page.goto("/entities/condition/VG%3ACONCEPT%3AAMIVA-AFFLICTION");
        const absence = page.locator(".related-section .knowledge-status").first();
        await expect(absence).toBeVisible();
        await expect(absence).toContainText(/not the same as an absence from the texts/i);
    });

    test("co-mention is labelled as proximity, not as a claim", async ({ page }) => {
        await page.goto("/entities/condition/VG%3ACONCEPT%3AAMIVA-AFFLICTION");
        await expect(
            page.getByText(/not a causal, medical or doctrinal claim/i),
        ).toBeVisible();
    });
});

/* -------------------------------------------------------------- not found - */

/**
 * Every route that can answer "not held", asserted on all of them rather than one.
 *
 * This started as a single assertion on `/passage`, and that is exactly what let the defect
 * hide. The seven routes below all call `notFound()` after awaiting the record, and all seven
 * were answering HTTP 200 with the broken-thread page drawn inside it - a soft 404, which
 * tells a crawler, a link checker and an API client that a record exists when it does not.
 * One route's worth of coverage reported one route's worth of the problem.
 *
 * The list is the complete set: `grep -rn "notFound()" src/app` returns these and nothing
 * else. Keep them in step. The status is the load-bearing assertion here - the broken-thread
 * UI was already correct on every one of them before the fix, so asserting only the markup
 * would still pass today with the status wrong.
 *
 * The cause was a Suspense boundary above the existence check (a root `loading.tsx`, plus a
 * segment-level one under `passage/[key]`), which commits the response before `notFound()`
 * can be reached. The reasoning is written up in `src/app/not-found.tsx`.
 */
const MISSING_RECORDS = [
    { what: "a passage", url: "/passage/VG%3ANOT%3AHELD" },
    { what: "a deity", url: "/devatas/VG%3ADEVATA%3ANOT-HELD" },
    { what: "an entity", url: "/entities/condition/VG%3ACONCEPT%3ANOT-HELD" },
    { what: "a formula family", url: "/formula-families/VG%3AFF%3ANOT-HELD" },
    { what: "a reuse record", url: "/reuse/VG%3ANOT%3AHELD" },
    { what: "a rite", url: "/rituals/VG%3ARITUAL%3ANOT-HELD" },
    { what: "a collection", url: "/vedas/not-a-veda" },
];

for (const { what, url } of MISSING_RECORDS) {
    test(`${what} that is not held gets the broken thread and a 404`, async ({ page }) => {
        const response = await page.goto(url);
        expect(
            response?.status(),
            `${url} answered a soft 404: the broken thread over a success status. ` +
                `A Suspense boundary above the existence check will do this - see ` +
                `src/app/not-found.tsx.`,
        ).toBe(404);
        await expect(page.locator(".va-missing .va-thread.is-broken")).toBeVisible();
        await expect(page.getByText(/not a statement about the Vedas/i)).toBeVisible();
    });
}
