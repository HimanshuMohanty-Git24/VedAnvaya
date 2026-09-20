import { expect, test, type Page } from "@playwright/test";

/**
 * The manual-QA pass, held.
 *
 * Three defects were found by a person looking at the running product and none of them was
 * caught by a gate: a homepage row that had grown into a panel, a scroll-driven register
 * that was attached, running and completely motionless, and a centred verse whose last line
 * ranged left. What they have in common is that each one is correct in the DOM and wrong on
 * the screen, so each assertion below is a *measurement* - a travelled distance, a rendered
 * line's centre, a rendered block's height - rather than a check that an element exists.
 *
 * Every one of these was confirmed to fail against the code as it shipped at 0105b96.
 */

const home = async (page: Page) => {
    await page.goto("/", { waitUntil: "load" });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
};

/** Where the strip sits in the document, and how tall it is. */
const stripBox = (page: Page) =>
    page.evaluate(() => {
        const r = document.querySelector(".va-archive-strip")!.getBoundingClientRect();
        return { top: Math.round(r.top + window.scrollY), height: Math.round(r.height) };
    });

/** The first citation's left edge, in viewport coordinates. */
const firstCitationLeft = (page: Page) =>
    page.evaluate(() =>
        Math.round(
            document
                .querySelector(".va-register-track li:first-child a")!
                .getBoundingClientRect().left,
        ),
    );

const scrollTo = async (page: Page, y: number) => {
    await page.evaluate((to) => window.scrollTo(0, to), Math.max(0, y));
    await page.waitForTimeout(260);
};

/* ============================================ 1. the Samavedic recitation row === */

test.describe("homepage: the Samavedic recitation row is a row", () => {
    test("one concise typed status, and none of the paragraph it replaced", async ({ page }) => {
        await home(page);
        const absent = page.locator(".va-bar-row.is-absent");
        await expect(absent).toHaveCount(1);

        const status = absent.locator(".va-bar-none");
        await expect(status).toHaveText(/^No catalogued recitation$/i);

        /*
         * The bound that matters, and the one a wording assertion cannot make. The defect
         * was never that the sentence was wrong - it was that the row carried 260 characters
         * of argument where its neighbours carry a bar and a figure.
         */
        const length = await status.evaluate((el) => (el.textContent ?? "").trim().length);
        expect(length).toBeLessThan(40);
    });

    test("the four-line explanation cannot come back to this row", async ({ page }) => {
        await home(page);
        const section = page.locator("section").filter({ has: page.locator(".va-bars") });
        /*
         * Each clause of the panel that was removed, named separately, because the failure
         * this guards against is someone restoring "just the important sentence". The
         * argument is not deleted - it is on /limits, and the second half of this test is
         * what says so.
         */
        for (const clause of [
            /most conspicuous gap/i,
            /sung realisation/i,
            /not a statement about the tradition/i,
            /gap in what has been published/i,
        ]) {
            await expect(section).not.toContainText(clause);
        }
        const limits = await page.request.get("/limits");
        expect(limits.status()).toBe(200);
        expect(await limits.text()).toMatch(/No Samavedic recording is catalogued/i);
    });

    test("the row keeps the rhythm of the three rows around it", async ({ page }) => {
        await home(page);
        const heights = await page
            .locator(".va-bar-row")
            .evaluateAll((rows) => rows.map((r) => Math.round(r.getBoundingClientRect().height)));
        expect(heights.length).toBe(4);
        /*
         * The visible defect, measured. The panel made the Samavedic row 71px against 30px
         * for its neighbours; a row that is within a few pixels of the tallest ordinary row
         * is a row rather than a warning block.
         */
        expect(Math.max(...heights) - Math.min(...heights)).toBeLessThanOrEqual(8);
    });
});

/* ================================================= 2. the archive register === */

test.describe("homepage: the archive register advances with the scroll", () => {
    test("the animation reads a timeline that the page's own scroll drives", async ({ page }) => {
        await home(page);
        const state = await page.evaluate(() => {
            const track = document.querySelector(".va-register-track")!;
            const cs = getComputedStyle(track);
            const strip = document.querySelector(".va-archive-strip")!;
            return {
                supported: CSS.supports("animation-timeline: view()"),
                /* `animation-timeline` is not in this TypeScript lib's CSSStyleDeclaration
                   yet, so it is read the way any not-yet-typed property is. */
                timeline: cs.getPropertyValue("animation-timeline").trim(),
                name: cs.animationName,
                scope: getComputedStyle(strip).getPropertyValue("view-timeline-name").trim(),
                travel: cs.getPropertyValue("--va-register-travel").trim(),
                attached: track.getAnimations().length,
            };
        });
        test.skip(!state.supported, "no scroll-timeline support in this browser");

        expect(state.name).toBe("va-register-advance");
        expect(state.attached).toBe(1);
        /*
         * Named, and named against the strip. `view()` is an anonymous timeline measured
         * against the nearest ancestor scroll container, and the track's is the frame that
         * holds it - a box that scrolls sideways by hand and never vertically at all. That
         * is what left this register running and motionless, so the assertion is on the
         * timeline's identity rather than on the animation being present.
         */
        expect(state.timeline).toBe("--va-register");
        expect(state.scope).toBe("--va-register");
        /* And a measured distance, because a correct timeline moving zero pixels is the
           same blank screen as a broken one. */
        expect(Number.parseFloat(state.travel)).toBeGreaterThan(100);
    });

    test("it moves as the reader scrolls, stops when they stop, and reverses", async ({
        page,
    }) => {
        await home(page);
        const supported = await page.evaluate(() => CSS.supports("animation-timeline: view()"));
        test.skip(!supported, "no scroll-timeline support in this browser");

        const box = await stripBox(page);
        const vh = page.viewportSize()!.height;

        await scrollTo(page, box.top - vh - 250);
        const before = await firstCitationLeft(page);

        await scrollTo(page, box.top - vh * 0.4);
        const entered = await firstCitationLeft(page);
        expect(entered).toBeLessThan(before - 40); // it travelled, and leftward

        // Nothing loops and nothing runs on a timer: a second of no scrolling is a second
        // of no movement.
        await page.waitForTimeout(1000);
        expect(await firstCitationLeft(page)).toBe(entered);

        await scrollTo(page, box.top + box.height - vh * 0.15);
        const deeper = await firstCitationLeft(page);
        expect(deeper).toBeLessThan(entered);

        await scrollTo(page, box.top - vh * 0.4);
        expect(Math.abs((await firstCitationLeft(page)) - entered)).toBeLessThanOrEqual(2);
    });

    test("it is restrained: never more lateral travel than the scroll that drives it", async ({
        page,
    }) => {
        await home(page);
        const { travel, range } = await page.evaluate(() => {
            const track = document.querySelector(".va-register-track")!;
            const strip = document.querySelector(".va-archive-strip")!;
            return {
                travel: Number.parseFloat(
                    getComputedStyle(track).getPropertyValue("--va-register-travel"),
                ),
                range: window.innerHeight + strip.getBoundingClientRect().height,
            };
        });
        /*
         * The uncapped distance here is 4,197px across roughly 1,126px of scroll - four
         * pixels sideways per pixel down, which is unreadable at its own speed and is
         * precisely the marquee the motion law refuses. One lateral pixel per scrolled pixel
         * is the ceiling.
         */
        expect(travel).toBeLessThanOrEqual(range);
    });

    test("every entry is a real citation, and a pointer press opens the one it names", async ({
        page,
    }) => {
        await home(page);
        const entries = page.locator(".va-register-track a");
        expect(await entries.count()).toBeGreaterThan(8);
        for (const href of await entries.evaluateAll((els) =>
            els.slice(0, 8).map((e) => e.getAttribute("href")),
        )) {
            expect(href).toMatch(/^\/passage\/VG%3A/);
        }

        const box = await stripBox(page);
        await scrollTo(page, box.top - page.viewportSize()!.height * 0.4);
        /*
         * Clicked where it is, with no `scrollIntoView` - the point of the test is the
         * pointer path, and scrolling to the target would change the very progress value
         * that decides where the target is.
         *
         * This is the defect that made `:focus-within` wrong here. A press focuses the
         * link, `:focus-within` dropped the whole lateral offset between mousedown and
         * mouseup, the citation left the cursor, and the click never completed: the page
         * stayed on the homepage. Now the offset is dropped for `:focus-visible` only.
         */
        const target = await page.evaluate(() => {
            const vw = document.documentElement.clientWidth;
            for (const a of document.querySelectorAll<HTMLAnchorElement>(
                ".va-register-track a",
            )) {
                const r = a.getBoundingClientRect();
                if (r.left > 24 && r.right < vw - 24 && r.top > 0 && r.bottom < innerHeight) {
                    return {
                        x: Math.round(r.left + r.width / 2),
                        y: Math.round(r.top + r.height / 2),
                        href: a.getAttribute("href")!,
                    };
                }
            }
            return null;
        });
        expect(target).not.toBeNull();
        await page.mouse.click(target!.x, target!.y);
        await expect(page).toHaveURL(new RegExp(target!.href.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    });

    test("a keyboard reader gets a still row they can reach", async ({ page }) => {
        await home(page);
        const first = page.locator(".va-register-track a").first();
        await first.focus();
        await expect(first).toBeFocused();
        // Focus drops the lateral offset, so the browser's own scroll-into-view works
        // against untransformed positions and the tab stop is somewhere a reader can see.
        await expect(page.locator(".va-register-track")).toHaveCSS("transform", "none");
        await expect(first).toBeInViewport();
    });
});

test.describe("homepage: reduced motion leaves the register still", () => {
    test.use({ reducedMotion: "reduce" });

    test("no animation, no offset, at any scroll position", async ({ page }) => {
        await home(page);
        const track = page.locator(".va-register-track");
        await expect(track).toHaveCSS("transform", "none");
        expect(await track.evaluate((el) => el.getAnimations().length)).toBe(0);

        const box = await stripBox(page);
        const vh = page.viewportSize()!.height;
        await scrollTo(page, box.top - vh - 200);
        const before = await firstCitationLeft(page);
        await scrollTo(page, box.top - vh * 0.4);
        expect(await firstCitationLeft(page)).toBe(before);
        // Still a register: the citations are reachable by hand, and still links.
        await expect(page.locator(".va-register-track a").first()).toHaveAttribute(
            "href",
            /^\/passage\/VG%3A/,
        );
    });
});

/* =================================================== 3. the featured verse === */

test.describe("homepage: the featured verse is composed on one axis", () => {
    test("the plate keeps its structural wrappers", async ({ page }) => {
        await home(page);
        const plate = page.locator(".va-plate");
        await expect(plate).toHaveCount(1);
        for (const part of [
            ".va-plate-inner",
            ".va-plate-inner > .va-kicker",
            ".va-plate-verse.va-sanskrit",
            ".va-plate-translation",
            ".va-plate-caption",
        ]) {
            await expect(plate.locator(part)).toHaveCount(1);
        }
        // The hierarchy is a figure with a caption, in that order in the DOM.
        const order = await plate.evaluate((el) =>
            [...el.querySelector(".va-plate-inner")!.children].map((c) => c.className),
        );
        expect(order.join(" ")).toMatch(
            /va-kicker.*va-plate-verse.*va-plate-translation.*va-plate-caption/,
        );
    });

    test("every line of the verse is centred, including the last", async ({ page }) => {
        await home(page);
        const lines = await page.evaluate(() => {
            const verse = document.querySelector(".va-plate-verse")!;
            const box = verse.getBoundingClientRect();
            const range = document.createRange();
            range.selectNodeContents(verse);
            return [...range.getClientRects()]
                .filter((r) => r.width > 4)
                .map((r) => ({
                    lead: Math.round(r.left - box.left),
                    trail: Math.round(box.right - r.right),
                }));
        });
        expect(lines.length).toBeGreaterThan(1);
        /*
         * `.va-sanskrit` sets `text-align-last: start` - correctly, because a reading text
         * is not justified - and `text-align: center` does not override it. So the plate
         * centred every line but the last, which ranged hard left: on the shipped build the
         * final line led by 0px and trailed by 345px in a 928px box. A line is centred when
         * its two margins agree.
         */
        for (const line of lines) {
            expect(Math.abs(line.lead - line.trail)).toBeLessThanOrEqual(4);
        }
    });

    test("verse, translation and colophon share one centre", async ({ page }) => {
        await home(page);
        const centres = await page.evaluate(() =>
            [".va-kicker", ".va-plate-verse", ".va-plate-translation", ".va-plate-caption"].map(
                (sel) => {
                    const r = document
                        .querySelector(`.va-plate ${sel}`)!
                        .getBoundingClientRect();
                    return Math.round(r.left + r.width / 2);
                },
            ),
        );
        expect(Math.max(...centres) - Math.min(...centres)).toBeLessThanOrEqual(2);
    });

    test("the plate is framed in dark, where the photograph is dropped", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await home(page);
        // The ground is a picture of paper: it is removed rather than inverted, and what
        // replaces it is the hairline dialect rather than the same texture at low opacity.
        await expect(page.locator(".va-plate-ground")).toBeHidden();
        const framed = await page.locator(".va-plate").evaluate((el) => {
            const cs = getComputedStyle(el);
            return {
                width: cs.borderTopWidth,
                style: cs.borderTopStyle,
                same: cs.borderTopColor === cs.borderBottomColor,
            };
        });
        expect(framed.style).toBe("solid");
        expect(Number.parseFloat(framed.width)).toBeGreaterThan(0);
        expect(framed.same).toBe(true);
    });
});

/* ============================================= 4. what the sweep looked for === */

test("the homepage does not overflow sideways at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await home(page);
    /* The register is a horizontal scroller on purpose, so the assertion is on the
       document: whatever the strip does inside its own frame, the page does not widen. */
    const overflow = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth,
        view: document.documentElement.clientWidth,
    }));
    expect(overflow.doc).toBeLessThanOrEqual(overflow.view + 1);
});

test("a standard product route carries no wall of absence copy", async ({ page }) => {
    /*
     * /limits and /sources own the detail and are deliberately not in this list. What this
     * guards is the direction of travel: the homepage's Samavedic panel is the shape of
     * defect being refused, and the same block pasted onto /rituals or /connections would
     * be the same defect somewhere else.
     */
    const ABSENCE =
        /\b(not built|never (measured|built)|does not exist|no .{0,30}(is|are) (catalogued|recorded|released)|not a statement about the tradition|most conspicuous gap)\b/i;
    for (const route of [
        "/",
        "/vedas",
        "/explore",
        "/rituals",
        "/formulas",
        "/insights",
        "/material-culture",
        "/connections",
    ]) {
        await page.goto(route, { waitUntil: "load" });
        const offenders = await page.evaluate(() => {
            const out: Array<{ cls: string; len: number; height: number; text: string }> = [];
            for (const el of document.querySelectorAll("p, dd, li, blockquote, aside")) {
                if (el.querySelector("p, li, dd")) continue;
                const text = (el.textContent ?? "").trim();
                if (text.length < 240) continue;
                const r = el.getBoundingClientRect();
                if (r.height < 60) continue;
                out.push({
                    cls: el.className?.toString?.() ?? "",
                    len: text.length,
                    height: Math.round(r.height),
                    text,
                });
            }
            return out;
        });
        const walls = offenders.filter((o) => ABSENCE.test(o.text));
        expect(
            walls,
            `${route} carries ${walls.length} absence block(s): ${walls
                .map((w) => `[${w.cls} ${w.len}c ${w.height}px] ${w.text.slice(0, 70)}`)
                .join(" ;; ")}`,
        ).toHaveLength(0);
    }
});
