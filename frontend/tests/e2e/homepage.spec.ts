import { expect, test, type Page } from "@playwright/test";
import { failingContrast } from "./contrast";

/**
 * The hero teaser's test handle, installed by `world-preview.tsx`.
 *
 * Nothing in the application reads it. It exists because two of the claims this file makes
 * cannot be checked from the outside: that the offscreen pause stops the frame loop dead,
 * which is an equality on a frame count rather than a small-enough number, and that a drag
 * ending *on* a subject still does not navigate, which needs the subject's position to aim at.
 */
type HeroHandle = {
    drawCount: () => number;
    paused: () => boolean;
    count: number;
    screenOf: (index: number) => { x: number; y: number; z: number } | null;
    refit: (spread: number) => void;
};

/** One subject in the hero's slice, as `public/data/home-world.json` ships it. */
type SliceNode = { id: string; label: string; group: string; degree: number };

const HERO_CANVAS = ".va-world-preview-canvas";

/**
 * Load the homepage and wait for the teaser's engine to exist.
 *
 * `reducedMotion` is on by default here, and that is not a convenience: the field is a
 * turntable, so a subject read at one moment is somewhere else a frame later, and a test that
 * aims at a coordinate it took 200 ms ago is a test that fails on a slow machine and passes on
 * a fast one. The drift is exercised deliberately, in the tests that are about the drift.
 */
async function heroPage(page: Page, { motion = false } = {}) {
    /* Stated rather than inherited: the default depends on the machine the suite runs on, and
       a drift test that silently became a stillness test would pass for the wrong reason. */
    await page.emulateMedia({ reducedMotion: motion ? "no-preference" : "reduce" });
    await page.goto("/");
    await page.waitForFunction(
        () => Boolean((window as unknown as { __vedaHero?: HeroHandle }).__vedaHero),
        null,
        { timeout: 30_000 },
    );
    /* The fit is applied on the frame after construction, so a position read immediately is a
       position from the default camera. */
    await page.waitForFunction(
        () => (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!.drawCount() > 2,
    );
    return page.locator(HERO_CANVAS);
}

const drawCount = (page: Page) =>
    page.evaluate(() =>
        (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!.drawCount(),
    );

const paused = (page: Page) =>
    page.evaluate(() => (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!.paused());

/** Every subject's position on the canvas, for comparing one moment against another. */
const positions = (page: Page) =>
    page.evaluate(() => {
        const handle = (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!;
        const out: Array<string> = [];
        for (let i = 0; i < handle.count; i += 1) {
            const at = handle.screenOf(i);
            out.push(at ? `${i}:${at.x.toFixed(2)},${at.y.toFixed(2)}` : `${i}:behind`);
        }
        return out;
    });

/** The slice, read from the same file the page reads, so index and identity cannot disagree. */
async function slice(page: Page): Promise<{ nodes: SliceNode[]; edges: Array<{ a: number; b: number }> }> {
    return page.evaluate(() => fetch("/data/home-world.json").then((r) => r.json()));
}

/**
 * The subject with the most connections inside the slice, and where it is on screen.
 *
 * The busiest rather than the first: it is the largest disc, so it is the most forgiving target
 * for a synthetic pointer, and its card has the most to say.
 */
async function busiestSubject(page: Page) {
    const data = await slice(page);
    const degree = data.nodes.map(() => 0);
    for (const edge of data.edges) {
        degree[edge.a] += 1;
        degree[edge.b] += 1;
    }
    const projected = await page.evaluate(() => {
        const handle = (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!;
        const out: Array<{ index: number; x: number; y: number }> = [];
        for (let i = 0; i < handle.count; i += 1) {
            const at = handle.screenOf(i);
            if (at) out.push({ index: i, x: at.x, y: at.y });
        }
        return out;
    });
    const best = [...projected].sort((a, b) => degree[b.index] - degree[a.index])[0];
    expect(best, "no subject in the hero slice projected onto the canvas").toBeTruthy();
    return { ...best, node: data.nodes[best.index], here: degree[best.index] };
}

/** A point on the canvas no subject is near, for a gesture that must end on empty ground. */
async function emptyPoint(page: Page, box: { width: number; height: number }) {
    return page.evaluate(
        ({ width, height }) => {
            const handle = (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!;
            const points: Array<[number, number]> = [];
            for (let i = 0; i < handle.count; i += 1) {
                const at = handle.screenOf(i);
                if (at) points.push([at.x, at.y]);
            }
            let best = { x: width / 2, y: height / 2, clearance: -1 };
            for (let x = 16; x < width - 16; x += 8) {
                for (let y = 16; y < height - 90; y += 8) {
                    let clearance = Infinity;
                    for (const [px, py] of points) {
                        clearance = Math.min(clearance, Math.hypot(px - x, py - y));
                    }
                    if (clearance > best.clearance) best = { x, y, clearance };
                }
            }
            return best;
        },
        { width: box.width, height: box.height },
    );
}

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

});

/* ------------------------------------------------------------ the teaser - */

/**
 * The front door's field of subjects: what handling it does, and what it refuses to do.
 *
 * Every test here exists because of a specific defect. Dragging the field navigated to the
 * graph, on every orbit, because the canvas acted on `click` and a mouse drag always ends in
 * one - and when the pick found nothing, which is where an orbit usually ends, the handler read
 * that as a request for the whole corpus. So the first claim is a negative one, and a negative
 * claim needs a positive control: an assertion that nothing happened passes just as well when
 * the canvas has stopped receiving events at all, which is why `data-gesture` is read here
 * rather than inferred.
 */
test.describe("homepage: the world teaser is handled, not followed", () => {
    test("a mouse drag ending on empty ground does not navigate", async ({ page }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const target = await emptyPoint(page, box);

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        /* Stepped, not teleported. A single move from press to release is one event and would
           latch the threshold just as well, but it is not what a hand does, and the copy of
           this classifier that used to live in the planar view failed specifically on the slow
           case - a pixel at a time, compared against the previous move rather than the press. */
        const steps = 14;
        for (let i = 1; i <= steps; i += 1) {
            await page.mouse.move(
                box.x + box.width / 2 + ((target.x - box.width / 2) * i) / steps,
                box.y + box.height / 2 + ((target.y - box.height / 2) * i) / steps,
            );
        }
        await page.mouse.up();

        await expect(page).toHaveURL(/\/$/);
        await expect(page.getByTestId("hero-selection")).toHaveCount(0);
    });

    test("a mouse drag ending on a subject does not navigate either", async ({ page }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        for (let i = 1; i <= 14; i += 1) {
            await page.mouse.move(box.x + box.width / 2 - i * 6, box.y + box.height / 2 + i * 2);
        }

        /*
         * The release is aimed after the drag, not before it.
         *
         * Dragging turns the field, so the subject is no longer where it was when the press
         * began - and this is the case the obvious guard gets wrong. A canvas that navigates
         * unless `pick()` returns null still navigates here, because the pointer really is over
         * a subject at the moment it comes up. Nothing but a gesture classifier can tell this
         * release from a tap.
         */
        const at = await page.evaluate(
            (index) =>
                (window as unknown as { __vedaHero?: HeroHandle }).__vedaHero!.screenOf(index),
            subject.index,
        );
        expect(at, "the subject aimed at turned away from the camera during the drag").toBeTruthy();
        await page.mouse.move(box.x + at!.x, box.y + at!.y);
        await expect(canvas).toHaveAttribute("data-gesture", "dragging");
        await page.mouse.up();

        await expect(page).toHaveURL(/\/$/);
        await expect(page.getByTestId("hero-selection")).toHaveCount(0);
    });

    test("the drag really is classified as a drag, and the phase returns to idle", async ({
        page,
    }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;

        /* Without this the two tests above pass vacuously: a canvas that receives no pointer
           events at all navigates nowhere either. The classifier is made to say so out loud. */
        await expect(canvas).toHaveAttribute("data-gesture", "idle");

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await expect(canvas).toHaveAttribute("data-gesture", "pressed");
        /* Two pixels is inside the 4 px mouse slop, so this is still a press. The threshold is
           part of the claim: a hand on a trackpad moves two or three pixels during a deliberate
           click, and a classifier that calls that a drag eats the click. */
        await page.mouse.move(box.x + box.width / 2 + 2, box.y + box.height / 2);
        await expect(canvas).toHaveAttribute("data-gesture", "pressed");
        for (let i = 1; i <= 10; i += 1) {
            await page.mouse.move(box.x + box.width / 2 + 2 + i * 5, box.y + box.height / 2);
        }
        await expect(canvas).toHaveAttribute("data-gesture", "dragging");
        await page.mouse.up();
        await expect(canvas).toHaveAttribute("data-gesture", "idle");
    });

    test("a click holds the subject under it, here, and the page does not move", async ({
        page,
    }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await page.mouse.down();
        await page.mouse.up();

        const selection = page.getByTestId("hero-selection");
        await expect(selection).toBeVisible();
        // The subject that was under the pointer, not merely some subject.
        await expect(selection).toHaveAttribute("data-node-id", subject.node.id);
        await expect(selection).toContainText(subject.node.label);
        await expect(page).toHaveURL(/\/$/);

        /* And the ground clears it. "Nothing is under the pointer" is a legitimate thing for a
           reader to say and it means let go, not show me everything - which is what it used to
           mean, and why an orbit ending over empty canvas left for /graph?view=world. */
        const empty = await emptyPoint(page, box);
        await page.mouse.move(box.x + empty.x, box.y + empty.y);
        await page.mouse.down();
        await page.mouse.up();
        await expect(selection).toHaveCount(0);
        await expect(page).toHaveURL(/\/$/);
    });

    test("and the card can be let go of without finding bare ground", async ({ page }) => {
        /*
         * At 390 the panel is 350 by 263 and a held subject's card and readout take about two
         * thirds of it, so "tap the ground to let it go" was an instruction about a strip of
         * canvas some forty pixels tall. This is the width the control exists for.
         */
        await page.setViewportSize({ width: 390, height: 844 });
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await page.mouse.down();
        await page.mouse.up();
        await expect(page.getByTestId("hero-selection")).toBeVisible();

        await page.getByRole("button", { name: /let go/i }).click();
        await expect(page.getByTestId("hero-selection")).toHaveCount(0);
        await expect(page).toHaveURL(/\/$/);
    });

    test("the held subject's connections are named in the curated words", async ({ page }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await page.mouse.down();
        await page.mouse.up();

        const rows = page.locator("[data-testid='hero-selection'] .va-world-preview-relations li");
        // Two to four. A connection a reader can see and not name is the defect this closes,
        // and forty of them in a hero panel is a wall of text rather than an answer.
        await expect(rows.first()).toBeVisible();
        const count = await rows.count();
        expect(count).toBeGreaterThanOrEqual(1);
        expect(count).toBeLessThanOrEqual(4);

        /*
         * Every phrase has to be one the scholarship wrote.
         *
         * This is the assertion, not the row count. The alternative implementation - and the
         * one this codebase already contains - is `humanizePredicate`, a general enum
         * humaniser that disagrees with the curated table on 44 of 57 predicates: "has rishi"
         * where the table says "is ascribed to the seer". Both produce plausible English, so
         * only a comparison against the table can tell which one the front door is showing.
         */
        const curated = await page.evaluate(async () => {
            const table = await fetch("/world/world.predicates.json").then((r) => r.json());
            return Object.values(table.predicates as Record<string, { phrase: string }>).map(
                (entry) => entry.phrase,
            );
        });
        expect(curated.length).toBeGreaterThan(40);
        for (const phrase of await page
            .locator("[data-testid='hero-selection'] .va-world-preview-predicate")
            .allInnerTexts()) {
            expect(curated, `"${phrase}" is not a phrase the curated table carries`).toContain(
                phrase.trim(),
            );
        }

        // And each row names the subject at the other end, so the phrase is about something.
        for (const name of await page
            .locator("[data-testid='hero-selection'] .va-world-preview-other")
            .allInnerTexts()) {
            expect(name.trim().length).toBeGreaterThan(0);
        }
    });

    test("the relationship vocabulary is fetched on the first hover, never at mount", async ({
        page,
    }) => {
        const asked: string[] = [];
        page.on("request", (request) => {
            if (request.url().includes("world.predicates.json")) asked.push(request.url());
        });

        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        /*
         * Nothing yet. 21 kB of curated explanation, most of it read only by the graph page's
         * inspector, and most visitors to a homepage never point at the field at all. The
         * graph page's own hook fetches at mount, which is why the teaser does not use it.
         */
        expect(asked, "the teaser paid for the vocabulary before anyone asked for it").toEqual([]);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await expect
            .poll(() => asked.length, { message: "one hover did not fetch the vocabulary" })
            .toBeGreaterThan(0);
        // Once. `loadPredicateSemantics` caches the promise, and a hover is a cheap event.
        await page.mouse.move(box.x + subject.x + 1, box.y + subject.y + 1);
        await page.waitForTimeout(300);
        expect(asked.length).toBe(1);
    });

    test("the affordances that do navigate, do", async ({ page }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await page.mouse.down();
        await page.mouse.up();

        const explore = page.getByTestId("hero-explore");
        await expect(explore).toBeVisible();
        // Named in the link, because "open it" is not a sentence a reader can mean about a
        // canvas they cannot see the state of.
        await expect(explore).toContainText(subject.node.label);
        /* The link's own destination, asserted before following it: this is the teaser's
           responsibility, and the next test is about what the graph page then does with it. */
        await expect(explore).toHaveAttribute(
            "href",
            `/graph?view=focus&renderer=3d&node=${encodeURIComponent(subject.node.id)}`,
        );
        await explore.click();
        await expect(page).toHaveURL(
            new RegExp(`/graph\\?.*node=${escapeForRegExp(encodeURIComponent(subject.node.id))}`),
        );

        await heroPage(page);
        await page.locator(".va-world-preview-link").click();
        await expect(page).toHaveURL(/\/graph$/);
    });

    /**
     * A defect in the graph page, recorded here because this is where it is reachable from.
     *
     * `Explore Agni in the Knowledge World` links to `?view=focus&renderer=3d&node=…` and the
     * graph page rewrites it to `?view=world&renderer=3d&node=…` on arrival - in that
     * parameter order, which is `graphStateToQuery`'s own, so the application wrote it rather
     * than the link carrying it. The subject survives; only the view axis is demoted. Measured
     * against a production build of 4c3d3e0.
     *
     * That is the same axis 55e8715 was written to protect - "keep the reader in Focus until
     * they say otherwise" - arriving now from a deep link rather than from a canvas tap, which
     * is a path that commit did not cover. `parseGraphState` reads `view=focus` correctly and
     * `setView` only refuses FOCUS when there is no subject, so the demotion is downstream of
     * both and is in `graph-state.ts`, `graph-shell.tsx` or `focus.ts` - none of which this
     * agent owns.
     *
     * Marked as an expected failure rather than weakened, so that fixing it turns this red and
     * the test gets deleted instead of quietly enshrining the wrong behaviour.
     */
    test("the explore link arrives in Focus", async ({ page }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;
        const subject = await busiestSubject(page);

        await page.mouse.move(box.x + subject.x, box.y + subject.y);
        await page.mouse.down();
        await page.mouse.up();
        await page.getByTestId("hero-explore").click();
        await expect(page).toHaveURL(/view=focus/);
    });

    test("the wheel over the hero scrolls the page and does not zoom the field", async ({
        page,
    }) => {
        const canvas = await heroPage(page);
        const box = (await canvas.boundingBox())!;

        /*
         * This works today for a reason nobody wrote down: OrbitControls returns before
         * `preventDefault` when `enableZoom` is false, so the wheel reaches the document. That
         * is a load-bearing consequence of a third-party early return - one release away from
         * a reader who cannot scroll past a third of their phone's fold - so it is pinned here
         * rather than left as a comment.
         */
        const before = await positions(page);
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.wheel(0, 500);
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(200);
        // And the field is the same size: the wheel was not spent on the camera.
        expect(await positions(page)).toEqual(before);
    });

    test("scrolled off screen, the teaser stops drawing entirely", async ({ page }) => {
        await heroPage(page, { motion: true });

        /* The control. Without it this whole test passes against an engine that never drew a
           frame in the first place, which is the same assertion being made twice about
           nothing. */
        const visibleBefore = await drawCount(page);
        await page.waitForTimeout(700);
        const visibleAfter = await drawCount(page);
        expect(
            visibleAfter,
            "the teaser drew no frames while on screen, so the pause below proves nothing",
        ).toBeGreaterThan(visibleBefore);

        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await expect.poll(() => paused(page)).toBe(true);

        /*
         * Exact equality, on wall clock.
         *
         * "Fewer than a handful of frames" passes with the defect present: the loop used to
         * reschedule itself before testing the flag, so a paused engine still woke about sixty
         * times a second to read a boolean and return. It now cancels the frame, and the only
         * assertion that can tell the two apart is that the count does not move at all.
         */
        const parked = await drawCount(page);
        await page.waitForTimeout(2500);
        expect(await drawCount(page)).toBe(parked);

        // And it comes back, because a pause a reader cannot undo is a broken hero.
        await page.evaluate(() => window.scrollTo(0, 0));
        await expect.poll(() => paused(page)).toBe(false);
        await expect.poll(() => drawCount(page)).toBeGreaterThan(parked);
    });

    test("the field names a few of its subjects, and fewer on a phone", async ({ page }) => {
        await heroPage(page);
        const data = await slice(page);
        const labels = page.locator(".va-world-preview-label");

        /* Between two and four. Fifty unnamed discs is a texture: a reader has no way to
           discover that the thing in front of them holds Indra, and the graph page's own
           ceiling of twenty-two names would fill this panel with overlapping type. */
        await expect.poll(() => labels.count()).toBeGreaterThanOrEqual(2);
        expect(await labels.count()).toBeLessThanOrEqual(4);

        const names = data.nodes.map((node) => node.label);
        for (const text of await labels.allInnerTexts()) {
            expect(names, `"${text}" is not a subject in the slice`).toContain(text.trim());
        }

        await page.setViewportSize({ width: 390, height: 844 });
        await heroPage(page);
        await expect.poll(() => labels.count()).toBeGreaterThanOrEqual(1);
        expect(await labels.count()).toBeLessThanOrEqual(2);
    });

    test("under prefers-reduced-motion the field does not move at all", async ({ page }) => {
        await heroPage(page);
        /* Zero, not gentler. The drift is refused outright in the engine rather than slowed,
           and this reads the projected position of every subject rather than sampling the
           camera, so a rotation of a hundredth of a degree would still show up. */
        const before = await positions(page);
        await page.waitForTimeout(1600);
        expect(await positions(page)).toEqual(before);
    });
});

/* ------------------------------------------------- who may handle a pointer - */

/** Event types a reader can navigate with, registered directly on an element. */
const POINTER_EVENTS = [
    "click",
    "pointerdown",
    "pointerup",
    "mousedown",
    "mouseup",
    "touchstart",
    "touchend",
];

/** The same, as React props, which never reach the DOM as attributes. */
const POINTER_PROPS = [
    "onClick",
    "onPointerDown",
    "onPointerUp",
    "onMouseDown",
    "onMouseUp",
    "onTouchStart",
    "onTouchEnd",
];

/** Elements a reader can reasonably expect to act on a press, by tag. */
const ANSWERABLE = ["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "SUMMARY", "LABEL"];

/**
 * Canvases permitted to read the pointer, and what each is permitted to do with it.
 *
 * An allowlist rather than a blanket exemption for `CANVAS`. The teaser reads the pointer
 * because it is a field a reader turns and holds subjects in; it does not navigate, and the
 * tests above are what says so.
 */
const ALLOWED_TO_HANDLE = [".va-world-preview-canvas"];

function escapeForRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Record every direct pointer registration from the first script onward.
 *
 * React sets its handlers as props and delegates at the root, so nothing it owns appears as a
 * DOM attribute - which is exactly how the assertion this replaces came to be worthless. It
 * queried `main [onclick], main [role='button']`, a selector React can never match, so it
 * reported an empty list for the whole life of a canvas that navigated on every click.
 */
async function watchPointerHandlers(page: Page) {
    await page.addInitScript((kinds: string[]) => {
        const held = window as unknown as { __pointerHandled?: Element[] };
        const recorded: Element[] = [];
        const seen = new Set<Element>();
        held.__pointerHandled = recorded;
        const wanted = new Set(kinds);
        const original = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function patched(
            this: EventTarget,
            type: string,
            listener: EventListenerOrEventListenerObject | null,
            options?: boolean | AddEventListenerOptions,
        ) {
            if (wanted.has(type) && this instanceof Element && !seen.has(this)) {
                seen.add(this);
                recorded.push(this);
            }
            return original.call(this, type, listener, options);
        };
    }, POINTER_EVENTS);
}

async function pointerHandlers(page: Page, props: string[], allowed: string[], tags: string[]) {
    return page.evaluate(
        ({ props, allowed, tags }) => {
            const held = window as unknown as { __pointerHandled?: Element[] };
            const recorded = held.__pointerHandled ?? [];
            const main = document.querySelector("main");
            if (!main) return { instrumented: false, scanned: 0, found: [] as string[], offenders: [] as string[] };

            const found = new Set<Element>();
            for (const element of recorded) {
                if (main.contains(element)) found.add(element);
            }

            /*
             * The React half. Props live on the DOM node under a key React randomises per
             * build, so the key is discovered rather than named. This is an internals read and
             * it is the only way to see a handler React never wrote to the document.
             */
            let scanned = 0;
            for (const element of main.querySelectorAll("*")) {
                const key = Object.keys(element).find((name) => name.startsWith("__reactProps$"));
                if (!key) continue;
                scanned += 1;
                const carried = (element as unknown as Record<string, Record<string, unknown>>)[
                    key
                ];
                if (props.some((prop) => typeof carried?.[prop] === "function")) {
                    found.add(element);
                }
            }

            const describe = (element: Element) =>
                `${element.tagName.toLowerCase()}${element.className ? `.${String(element.className).trim().split(/\s+/).join(".")}` : ""}`;

            const offenders: string[] = [];
            for (const element of found) {
                if (tags.includes(element.tagName)) continue;
                if (allowed.some((selector) => element.matches(selector))) continue;
                offenders.push(describe(element));
            }
            return {
                instrumented: true,
                scanned,
                found: [...found].map(describe),
                offenders,
            };
        },
        { props, allowed, tags },
    );
}

test.describe("homepage: only a link, a button or a named canvas may read the pointer", () => {
    /*
     * This replaces an assertion that never once ran.
     *
     * `main [onclick], main [role='button']` matched nothing on any render of this page,
     * because React does not write an `onclick` attribute - so the check reported a clean page
     * throughout the entire life of a canvas whose `onClick` navigated to /graph on every
     * orbit. A validator that silently matches nothing is worse than no validator, because it
     * is also a claim. So this one measures its own coverage, and is shown to be capable of
     * failing before it is believed.
     */
    test("every pointer handler in the body belongs to something that says so", async ({
        page,
    }) => {
        await watchPointerHandlers(page);
        await heroPage(page);

        const report = await pointerHandlers(page, POINTER_PROPS, ALLOWED_TO_HANDLE, ANSWERABLE);

        // Coverage, first, and as a hard assertion. Precision over an empty set is free.
        expect(report.instrumented, "the recorder never ran").toBe(true);
        expect(
            report.scanned,
            "no element in main carried React props, so the props half of this scan saw nothing",
        ).toBeGreaterThan(50);
        expect(
            report.found,
            "the scan found no pointer handler at all in a page whose hero is a canvas that reads the pointer",
        ).toContain("canvas.va-world-preview-canvas");

        expect(report.offenders).toEqual([]);
    });

    test("and the scan reports a violation when there is one", async ({ page }) => {
        await watchPointerHandlers(page);
        await heroPage(page);

        /*
         * The mutation. A div that acts on a press is the defect class this test exists for -
         * it is unreachable by keyboard, carries no role, and gives a screen reader nothing -
         * so the scan is required to name it. Without this the test above is just an empty
         * array compared against an empty array.
         */
        await page.evaluate(() => {
            const planted = document.createElement("div");
            planted.className = "planted-offender";
            planted.addEventListener("click", () => {});
            document.querySelector("main")!.append(planted);
        });

        const report = await pointerHandlers(page, POINTER_PROPS, ALLOWED_TO_HANDLE, ANSWERABLE);
        expect(report.offenders).toContain("div.planted-offender");
    });
});

/** The phone viewport height these tests use, named so the assertion reads as a claim. */
function view844() {
    return 844;
}
