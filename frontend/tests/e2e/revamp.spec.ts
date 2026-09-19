import { expect, test, type Page } from "@playwright/test";

/**
 * The final revamp, gated.
 *
 * Every assertion here is a regression for a defect this phase found by looking, and every
 * one of them would have rendered without an error. That is the class they share: a route
 * drawn as a map of everything, a phrase composited behind a panel, a catalogue showing a
 * machine label instead of the Sanskrit it matched, a margin that vanished at a width
 * nobody opened. None of them throws, so none of them is caught by anything but a
 * measurement.
 */

const RV_1_32_1 = encodeURIComponent("VG:RV:SAK:M01:S032:V001");
const TAKMAN = "VG:CONCEPT:TAKMAN-FEVER";

/** The world is a two-megabyte artifact and a settling layout; it is not a fast page. */
const READY = 40_000;

/* ============================================================== the graph === */

/** Drive the graph into PATH in the named renderer and trace a route that exists. */
async function traceRoute(page: Page, renderer: "3D" | "2D") {
    await page.goto("/graph", { waitUntil: "load" });
    await expect(page.locator(".va-graph")).toBeVisible({ timeout: READY });
    await page.getByRole("button", { name: renderer, exact: true }).click();
    await page.getByRole("button", { name: "Path", exact: true }).click();
    await page.getByRole("textbox", { name: "From" }).fill("Agni");
    await page.getByRole("textbox", { name: "To" }).fill(TAKMAN);
    /*
     * Wait for the control to mean something before pressing it.
     *
     * `resolve` reads a 4 MB label artifact fetched after render, so before it lands every
     * name resolves to null. This used to submit into that window and the page did nothing,
     * silently - which made this test flaky and, more to the point, made the feature
     * unusable for the first few seconds without saying so. The button now states its own
     * readiness, so the test waits for what a reader would wait for.
     */
    const trace = page.getByRole("button", { name: /Trace the connection/i });
    await expect(trace).toBeEnabled({ timeout: READY });
    await trace.click();
    /* The route's own list is the proof the service answered; the canvas is what is being
       tested, and asserting on the list first means a service failure reads as a service
       failure rather than as a rendering one. */
    await expect(page.locator(".va-path-step")).toHaveCount(3, { timeout: 20_000 });
}

test.describe("a traced route is drawn in both renderers", () => {
    /*
     * The defect: the shell computed the planar scope as
     * `view === "FOCUS" && selected ? "focus" : "world"`, so PATH fell through the ternary
     * and 2D drew the whole corpus with the route nowhere on it. Silent, and invisible to
     * every existing test, because the 3D renderer had always drawn routes.
     */
    for (const renderer of ["3D", "2D"] as const) {
        test(`${renderer}: the hops are drawn and each one is named`, async ({ page }) => {
            await traceRoute(page, renderer);

            /* The stage is in PATH and is drawing with the renderer that was asked for. */
            const stage = page.locator(".va-graph");
            await expect(stage).toHaveAttribute("data-view", "PATH");
            await expect(stage).toHaveAttribute(
                "data-renderer",
                renderer === "3D" ? "3d" : "2d",
            );

            /*
             * The hop phrases, on the canvas. This is the assertion that fails against the
             * old code: with the scope falling through to "world" the planar canvas drew
             * constellations and named no hop at all.
             *
             * The service returns two hops for this route, and each is numbered by the label
             * layer - "1. names the deity", "2. names" - so the numbering is asserted too:
             * an unnumbered phrase would mean the route's order had been lost.
             */
            const phrases = page
                .locator(".va-edge-labels > *")
                .filter({ hasText: /^\d+\.\s/ });
            await expect(phrases.first()).toBeVisible({ timeout: 20_000 });
            expect(await phrases.count()).toBeGreaterThanOrEqual(2);
        });
    }

    test("2D says what to do before a route has been traced, rather than drawing the corpus", async ({
        page,
    }) => {
        await page.goto("/graph", { waitUntil: "load" });
        await expect(page.locator(".va-graph")).toBeVisible({ timeout: READY });
        await page.getByRole("button", { name: "2D", exact: true }).click();
        await page.getByRole("button", { name: "Path", exact: true }).click();
        await expect(page.locator(".va-planar-empty")).toContainText(/trace a route/i);
    });
});

test.describe("no graph label is placed under the chrome", () => {
    /*
     * The placement bound was the canvas rectangle, and the canvas is not what the reader
     * can see of it: the control rail is a 368x233 block at the top left and the subject
     * panel is a 352-wide rail on the right. Measured before the fix, one phrase in 102
     * landed behind them - drawn, composited, counted as placed, invisible.
     *
     * Deleting the `chromeBoxes` entry from `reserved` in `edge-label-view.ts` fails this.
     */
    for (const [name, size] of [
        ["desktop", { width: 1440, height: 900 }],
        ["narrow", { width: 390, height: 844 }],
    ] as const) {
        test(`${name}: every drawn label clears every panel`, async ({ page }) => {
            await page.setViewportSize(size);
            await page.goto(`/graph?node=${encodeURIComponent("VG:DEVATA:INDRAH")}`, {
                waitUntil: "load",
            });
            await expect(page.locator(".va-graph")).toBeVisible({ timeout: READY });
            /* Labels are assigned on a debounced settle, so a sample taken too early is a
               sample of a state that was never meant to be placed. */
            await page.waitForTimeout(6_000);

            const report = await page.evaluate(() => {
                const stage = document.querySelector(".va-graph");
                if (!stage) return { drawn: 0, hidden: [] as string[] };
                const bounds = stage.getBoundingClientRect();
                const rel = (box: DOMRect) => ({
                    x: box.x - bounds.x,
                    y: box.y - bounds.y,
                    w: box.width,
                    h: box.height,
                });
                const panels = [".va-graph-chrome", ".va-world-panel", ".va-relationship"]
                    .map((selector) => stage.querySelector(selector))
                    .filter((node): node is Element => node !== null)
                    .map((node) => rel(node.getBoundingClientRect()));
                const labels = [...document.querySelectorAll(".va-edge-labels > *")]
                    .filter((node) => Number(getComputedStyle(node).opacity) > 0.05)
                    .map((node) => ({
                        text: (node.textContent ?? "").slice(0, 40),
                        ...rel(node.getBoundingClientRect()),
                    }));
                const over = (
                    label: { x: number; y: number; w: number; h: number },
                    panel: { x: number; y: number; w: number; h: number },
                ) =>
                    !(
                        label.x + label.w < panel.x ||
                        label.x > panel.x + panel.w ||
                        label.y + label.h < panel.y ||
                        label.y > panel.y + panel.h
                    );
                return {
                    drawn: labels.length,
                    hidden: labels
                        .filter((label) => panels.some((panel) => over(label, panel)))
                        .map((label) => label.text),
                };
            });

            /*
             * A count-zero that passes because nothing was drawn is the assertion this suite
             * has a whole guards file about. So the population is asserted first: if no label
             * is on screen, the test has stopped testing and says so.
             */
            expect(report.drawn).toBeGreaterThan(3);
            expect(report.hidden).toEqual([]);
        });
    }
});

/* ============================================================= the search === */

test.describe("search is a catalogue", () => {
    test("a passage row shows the Sanskrit it matched, not the machine subtitle", async ({
        page,
    }) => {
        /*
         * `subtitle ?? snippet` meant every verse described itself as "AV / MANTRA" while
         * the Sanskrit the query actually matched was fetched, carried across the wire and
         * thrown away. That is the most useful thing a search over a corpus can show.
         */
        await page.goto("/search?q=agni&type=PASSAGE", { waitUntil: "load" });
        const first = page.locator(".search-results li").first();
        await expect(first).toBeVisible({ timeout: 20_000 });
        await expect(first.locator("p.is-sanskrit")).toBeVisible();
        await expect(first.locator(".result-row")).not.toContainText("/ MANTRA");
    });

    test("every row still says how it matched", async ({ page }) => {
        /* The one thing the re-dress was not allowed to drop. A ranked list that will not
           say what it matched on is a list a reader has to take on trust. */
        await page.goto("/search?q=Indra", { waitUntil: "load" });
        const rows = page.locator(".search-results li");
        await expect(rows.first()).toBeVisible({ timeout: 20_000 });
        const count = await rows.count();
        expect(count).toBeGreaterThan(3);
        for (let i = 0; i < count; i += 1) {
            await expect(rows.nth(i).locator("small")).toContainText(/Matched on/);
        }
    });

    test("the field is still reachable by its label and by the slash key", async ({ page }) => {
        /* The visible label became `sr-only` in this phase. That is only acceptable while it
           is still the input's accessible name. */
        await page.goto("/search", { waitUntil: "load" });
        await expect(page.locator(".search-prompts button").first()).toBeVisible();
        await page.locator("h1").click();
        await page.keyboard.press("/");
        await expect(page.getByLabel(/Search Sanskrit, IAST/)).toBeFocused();
    });
});

/* ============================================================= the reader === */

test.describe("the reader's margin", () => {
    test("wide: the witness and the printing source stand in the folio margin", async ({
        page,
    }) => {
        await page.setViewportSize({ width: 1600, height: 1000 });
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
        const margin = page.locator(".va-folio-margin").first();
        await expect(margin).toBeVisible();
        await expect(margin).toContainText(/Witness/i);
        await expect(margin).toContainText(/Printed from/i);
        /* Beside the verse, not under it: the margin's left edge is past the text's right. */
        const verse = await page.locator(".va-verse .sanskrit").first().boundingBox();
        const notes = await margin.boundingBox();
        expect(notes!.x).toBeGreaterThan(verse!.x + verse!.width - 1);
    });

    for (const [name, width] of [
        ["medium", 1280],
        ["narrow", 390],
    ] as const) {
        test(`${name}: the margin folds beneath its block and loses nothing`, async ({
            page,
        }) => {
            /*
             * The fallback has to be a fold, never a drop. Both lines are apparatus the
             * reader needs, and a responsive rule that hid them below 84rem would be the
             * margin costing the product two facts on most of its traffic.
             */
            await page.setViewportSize({ width, height: 900 });
            await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
            const margin = page.locator(".va-folio-margin").first();
            await expect(margin).toBeVisible();
            await expect(margin).toContainText(/Witness/i);
            await expect(margin).toContainText(/Printed from/i);
            const verse = await page.locator(".va-verse .sanskrit").first().boundingBox();
            const notes = await margin.boundingBox();
            expect(notes!.y).toBeGreaterThan(verse!.y);
        });
    }

    test("the shelfmark is exposed, quietly, and does not replace the citation", async ({
        page,
    }) => {
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
        await expect(page.locator(".va-shelfmark")).toContainText("VG:RV:SAK:M01:S032:V001");
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("RV 1.32.1");
    });
});

test.describe("the witness column", () => {
    test("opens beside the verse, names its witness, and closes", async ({ page }) => {
        await page.setViewportSize({ width: 1600, height: 1000 });
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });

        const open = page.locator(".va-collation-open").first();
        await expect(open).toBeVisible();
        await open.click();

        const witness = page.locator(".va-collation-witness");
        await expect(witness).toBeVisible();
        await expect(witness.locator(".va-collation-witness-name")).not.toBeEmpty();
        /* Beside, not below. */
        const primary = await page.locator(".va-collation-primary").boundingBox();
        const second = await witness.boundingBox();
        expect(second!.x).toBeGreaterThan(primary!.x + primary!.width - 1);

        /* And the product says, in words, that it has not diffed them. */
        await expect(witness).toContainText(/Nothing is normalised/i);

        await page.locator(".va-collation-close").click();
        await expect(witness).toBeHidden();
    });

    test("narrow: the same control, stacked", async ({ page }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
        const open = page.locator(".va-collation-open").first();
        await expect(open).toBeVisible();
        await open.click();
        const witness = page.locator(".va-collation-witness");
        await expect(witness).toBeVisible();
        const primary = await page.locator(".va-collation-primary").boundingBox();
        const second = await witness.boundingBox();
        expect(second!.y).toBeGreaterThan(primary!.y);
    });
});

test.describe("the accent trace", () => {
    test("states what it is, and says how many marks it drew", async ({ page }) => {
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
        const note = page.locator(".recitation-trace-note");
        await expect(note).toBeVisible();
        await expect(note).toContainText(/accent marks? printed in this verse/i);
        /* The sentence that keeps a drawing from being read as a measurement. */
        await expect(note).toContainText(/not measured pitch/i);
    });

    test("a contour is drawn only where the text carries marks to draw it from", async ({
        page,
    }) => {
        await page.goto(`/passage/${RV_1_32_1}`, { waitUntil: "load" });
        await expect(page.locator(".recitation-track")).toHaveAttribute(
            "data-trace",
            "derived",
        );
        await expect(page.locator("svg.recitation-cadence")).toBeVisible();
    });
});

/* ============================================================== the motion === */

test.describe("reduced motion", () => {
    test.use({ reducedMotion: "reduce" });

    test("a measure bar still shows its measured value rather than zero", async ({ page }) => {
        /*
         * The trap in every reduced-motion implementation of a growing bar. `animation: none`
         * on a rule whose base state is `inline-size: 0%` leaves every measured value drawn
         * as nothing - a product that reports all its figures as zero to the readers who
         * asked for less motion.
         */
        await page.goto("/rituals", { waitUntil: "load" });
        const bar = page.locator(".va-register-measure .va-resolve").first();
        await expect(bar).toBeVisible();
        const width = await bar.evaluate((node) => node.getBoundingClientRect().width);
        expect(width).toBeGreaterThan(0);
    });

    test("the archive register does not travel", async ({ page }) => {
        await page.goto("/", { waitUntil: "load" });
        const track = page.locator(".va-archive-strip .va-register-track");
        await expect(track).toBeVisible();
        await track.scrollIntoViewIfNeeded();
        await page.waitForTimeout(600);
        const transform = await track.evaluate((node) => getComputedStyle(node).transform);
        expect(["none", "matrix(1, 0, 0, 1, 0, 0)"]).toContain(transform);
    });
});

test("the archive register is real citations, and each one opens a verse", async ({ page }) => {
    /* Not Sanskrit wallpaper and not sample text: every entry is an address the reader can
       act on, and the register is worthless if they are not. */
    await page.goto("/", { waitUntil: "load" });
    const entries = page.locator(".va-archive-strip .va-register-track a");
    const count = await entries.count();
    expect(count).toBeGreaterThan(8);
    for (let i = 0; i < Math.min(count, 6); i += 1) {
        await expect(entries.nth(i)).toHaveAttribute("href", /^\/passage\/VG%3A/);
    }
    /*
     * Reached from the keyboard, which is the path that has to work and the one that was
     * broken. The track is translated by the reader's own scroll, so an entry can be sitting
     * outside the frame - and while the frame was `overflow-x: clip` the browser could not
     * reveal it, so tab-stops existed on citations nobody could see. Focus now drops the
     * lateral offset; this is the assertion that says so.
     */
    await entries.first().focus();
    await expect(entries.first()).toBeFocused();
    await expect(entries.first()).toBeInViewport();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/passage\//);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

/* ========================================================== page overflow === */

test.describe("no page overflows sideways", () => {
    const ROUTES = [
        "/",
        "/vedas",
        "/search?q=agni",
        "/rituals",
        "/formulas",
        "/insights",
        "/material-culture",
        "/explore/atharvaveda",
        "/connections",
        "/limits",
        `/passage/${RV_1_32_1}`,
    ];

    for (const width of [1440, 390]) {
        test(`at ${width}px`, async ({ page }) => {
            await page.setViewportSize({ width, height: 900 });
            const offenders: string[] = [];
            for (const route of ROUTES) {
                await page.goto(route, { waitUntil: "load" });
                await page.waitForTimeout(500);
                const overflow = await page.evaluate(
                    () =>
                        document.documentElement.scrollWidth -
                        document.documentElement.clientWidth,
                );
                if (overflow > 1) offenders.push(`${route} (+${overflow}px)`);
            }
            expect(offenders).toEqual([]);
        });
    }
});
