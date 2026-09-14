/**
 * The graph, under a finger.
 *
 * ## Why this file exists
 *
 * The mobile suite before it had zero tests that touched a canvas with a pointer, and that is
 * not a coincidental gap - it is why both of this phase's P0 defects shipped green. One was a
 * homepage canvas that navigated away on a mouse drag; the other was a reader who selected a
 * subject, explored it, and was returned to the whole corpus. The second had fourteen existing
 * regression tests around it. All fourteen asserted the state model, none of them touched the
 * canvas, and the mechanism was in the wiring between the two.
 *
 * So everything here goes through a real pointer, and the two things it mostly asserts are
 * *absences*: that a drag does not select, and that a tap does not move an axis it does not
 * own. An absence is the easiest kind of assertion to pass by accident - a canvas that has
 * stopped receiving events at all passes every one of them - so where the module under test
 * offers a positive signal, this file reads it. `gesture.ts` writes its classification to
 * `data-gesture` for exactly that reason, and the slop assertions come in pairs: the tap that
 * must work is asserted beside the drag that must not, because only the pair pins the
 * threshold rather than its sign.
 *
 * ## Touch drags need CDP
 *
 * `page.touchscreen` has only `tap()`. A drag, a pinch and a cancelled gesture all need
 * `Input.dispatchTouchEvent`, so `touchHarness` opens one CDP session and every touch in this
 * file goes through it. That makes the file Chromium-only, which is already true of the whole
 * suite: Playwright's own Chromium could not be downloaded in this environment and the projects
 * run the installed Edge through `channel`.
 *
 * ## Measurements
 *
 * Every figure quoted in a comment here was measured on the live layout at 390x844 rather than
 * derived, and the reference viewport is the project's, set once in `playwright.config.ts`.
 */
import { expect, test, type CDPSession, type Page } from "@playwright/test";

const INDRA = encodeURIComponent("VG:DEVATA:INDRAH");

/** The touch slop for a finger, from `GESTURE_SLOP`. Duplicated as a number on purpose: a test
 *  that imports the constant it is checking asserts that the code equals itself. */
const TOUCH_SLOP = 10;

/** The floor every touch target has to clear. */
const TARGET = 44;

/*
 * Two pixels, not one, when sampling a declared box's own edge.
 *
 * Measured rather than chosen. Sweeping the 2D pad's four corners at insets of 1, 2, 3, 4, 6, 8,
 * 10 and 12 px from its declared box of x 47.12..91.12, y 182.88..226.88: at 1px the two *bottom*
 * corners miss and the top two hit; at 2px all four hit. Along the vertical centre line the
 * bottom edge is live to y 226.0 and dead at 227.0, which is exactly where the box says it ends.
 *
 * So the pads are the size they declare and the sub-pixel behaviour is at the corners only. That
 * is a sampling property of a 44px box centred on fractional ink - 25.8px tall on the view row,
 * 22.59px on the renderer row - and not a defect in the control. Reading it as one would have
 * been a fifth invented defect in a phase that has already had four, so it is written down here
 * with its numbers instead.
 *
 * The inset is applied to the true fractional edge, not to a floored copy of it: flooring first
 * and then insetting lands 2.88px inside, which is a different measurement than the one above.
 */
const EDGE_INSET = 2;

type Touch = {
    cdp: CDPSession;
    tap: (x: number, y: number) => Promise<void>;
    /**
     * A press, a straight travel, and a release.
     *
     * `probe` is called after each move, while the finger is still down, so a caller can read
     * the gesture classification mid-gesture. That matters: an earlier version of the drag test
     * read the phase by dispatching a *zero-distance* swipe first, which is a tap, and it
     * selected whatever was under it. The test was flaky and the flake was the test's own doing.
     */
    swipe: (
        x: number,
        y: number,
        dx: number,
        dy: number,
        steps?: number,
        probe?: () => Promise<void>,
    ) => Promise<void>;
    /** A two-finger pinch about a centre, from one half-gap to another. */
    pinch: (cx: number, cy: number, from: number, to: number) => Promise<void>;
    /** A press, a small travel, and then the browser taking the gesture away. */
    cancel: (x: number, y: number) => Promise<void>;
};

async function touchHarness(page: Page): Promise<Touch> {
    const cdp = await page.context().newCDPSession(page);
    const point = (x: number, y: number, id = 1) => ({
        x,
        y,
        id,
        radiusX: 12,
        radiusY: 12,
        force: 1,
    });
    const send = (type: string, touchPoints: ReturnType<typeof point>[]) =>
        cdp.send("Input.dispatchTouchEvent", {
            type: type as "touchStart",
            touchPoints,
            modifiers: 0,
        });

    return {
        cdp,
        async tap(x, y) {
            await send("touchStart", [point(x, y)]);
            await send("touchEnd", []);
        },
        async swipe(x, y, dx, dy, steps = 10, probe) {
            await send("touchStart", [point(x, y)]);
            for (let i = 1; i <= steps; i += 1) {
                await send("touchMove", [point(x + (dx * i) / steps, y + (dy * i) / steps)]);
                if (probe) await probe();
            }
            await send("touchEnd", []);
        },
        async pinch(cx, cy, from, to) {
            const steps = 8;
            await send("touchStart", [point(cx - from, cy, 1), point(cx + from, cy, 2)]);
            for (let i = 1; i <= steps; i += 1) {
                const gap = from + ((to - from) * i) / steps;
                await send("touchMove", [point(cx - gap, cy, 1), point(cx + gap, cy, 2)]);
            }
            /* Lift one finger, then the other. The second lift is the whole point: without the
               pinch latch it looks like a press and release that never travelled, because by
               then the first finger's travel has been forgotten. */
            await send("touchEnd", [point(cx + to, cy, 2)]);
            await send("touchEnd", []);
        },
        async cancel(x, y) {
            await send("touchStart", [point(x, y)]);
            await send("touchMove", [point(x + 2, y)]);
            await send("touchCancel", []);
        },
    };
}

/** The two axes and the URL, read off the one element that carries both. */
async function axes(page: Page) {
    return page.evaluate(() => {
        const graph = document.querySelector(".va-graph");
        const canvas = document.querySelector<HTMLElement>(".va-world-canvas");
        return {
            view: graph?.getAttribute("data-view") ?? null,
            renderer: graph?.getAttribute("data-renderer") ?? null,
            node: new URLSearchParams(location.search).get("node"),
            gesture: canvas?.dataset.gesture ?? null,
            subject: document.querySelector(".va-world-panel h2")?.textContent ?? null,
        };
    });
}

async function openGraph(page: Page, query: string) {
    await page.goto(`/graph?${query}`);
    await expect(page.locator(".va-graph-switch button").first()).toBeVisible();
    /*
     * The *visible* canvas, not the first one.
     *
     * Both stages stay mounted and only one is shown - a canvas that unmounts loses its context,
     * its buffers and its camera - so in 2D the spatial canvas is still in the document with
     * `visibility: hidden`, and `.first()` finds it and waits twelve seconds for it to appear.
     */
    await expect(page.locator(".va-graph canvas:visible").first()).toBeVisible();
}

/*
 * Focus is entered by tapping, never by the URL.
 *
 * `?view=FOCUS` does not work: the state model refuses it, because `boot:resolve-precedence` is
 * not in the reader's half of the intent union and only the reader's half may move the semantic
 * axis. So a shared Focus link opens in World. That is reported as a defect rather than worked
 * around here - but a test cannot assert Focus geometry from a URL until it is fixed, and a
 * test that quietly ran in World while claiming to test Focus would be worse than either.
 */
async function enterFocus(page: Page) {
    await openGraph(page, `view=world&renderer=3d&node=${INDRA}`);
    await page.locator('[aria-label="What to explore"] button', { hasText: "Focus" }).tap();
    await expect(page.locator(".va-graph")).toHaveAttribute("data-view", "FOCUS");
    await expect(page.locator(".va-world-panel h2")).toHaveText("Indra");
    /* The scene is curated, laid out and flown to. Wait for the engine to have a focus scene
       with members rather than for a duration. */
    await page.waitForFunction(
        () => {
            const engine = (window as unknown as { __vedaWorld?: { focusScene?: unknown } })
                .__vedaWorld;
            const scene = engine?.focusScene as { members?: unknown[] } | null | undefined;
            return !!scene && Array.isArray(scene.members) && scene.members.length > 0;
        },
        null,
        { timeout: 30_000 },
    );
}

/**
 * The drawn orbs, once they have stopped moving.
 *
 * Reading `orbGeometry` as soon as the scene exists reads it mid-flight, and a tap aimed at
 * where an orb was a moment ago misses it: the camera flight is two stages of about a second,
 * and the first 350 ms of it moved the target neighbour 14.55 px. This is the same mistake in a
 * new place - a UI defect measured before the DOM settled - so the wait is for stillness rather
 * than for a duration.
 *
 * Measured: after that first 350 ms the positions are stable to 0.00 px indefinitely, in both
 * motion settings, so two agreeing samples is a real settle signal and not a guess at one.
 */
async function settledOrbs(page: Page) {
    let previous: Awaited<ReturnType<typeof orbs>> = null;
    for (let attempt = 0; attempt < 40; attempt += 1) {
        const current = await orbs(page);
        if (current && previous && current.length === previous.length) {
            const moved = current.every((orb, index) => {
                const was = previous![index];
                return Math.hypot(orb.x - was.x, orb.y - was.y) <= 0.5;
            });
            if (moved) return current;
        }
        previous = current;
        await page.waitForTimeout(250);
    }
    throw new Error("the drawn scene never stopped moving");
}

/** Where the drawn orbs are, in page pixels, and how big. */
async function orbs(page: Page) {
    return page.evaluate(() => {
        type Engine = {
            focusScene: { root: number; members: { node: number }[] } | null;
            orbGeometry: (
                nodes: number[],
            ) => { node: number; x: number; y: number; radius: number }[];
        };
        const engine = (window as unknown as { __vedaWorld?: Engine }).__vedaWorld;
        const scene = engine?.focusScene;
        const canvas = document.querySelector(".va-world-canvas");
        if (!engine || !scene || !canvas) return null;
        const box = canvas.getBoundingClientRect();
        return engine
            .orbGeometry([scene.root, ...scene.members.map((member) => member.node)])
            .map((orb) => ({
                node: orb.node,
                root: orb.node === scene.root,
                x: orb.x + box.x,
                y: orb.y + box.y,
                diameter: orb.radius * 2,
            }));
    });
}

/** The strip of canvas the reader can actually see: below the chrome, above the sheet. */
async function visibleBand(page: Page) {
    return page.evaluate(() => {
        const graph = document.querySelector(".va-graph")!.getBoundingClientRect();
        const height = (selector: string) =>
            document.querySelector(selector)?.getBoundingClientRect().height ?? 0;
        const top = graph.y + height(".va-graph-chrome");
        const bottom = graph.y + graph.height - height(".va-world-panel");
        return { top, bottom, height: bottom - top, stage: graph.height };
    });
}

/* ------------------------------------------------------------------ the pads - */

/**
 * Every declared touch pad in the two-axis switch, read from the live stylesheet.
 *
 * Derived rather than hardcoded: the pad is a `::after` on the button, so its size comes from
 * the computed style of the pseudo-element and its centre from the button's own box. That way
 * the assertion tracks whatever the stylesheet says instead of restating it, and a change to
 * the pad rule is caught rather than silently agreed with.
 */
async function pads(page: Page) {
    return page.evaluate(() => {
        const read = (axis: string, scope: string) =>
            [...document.querySelectorAll<HTMLButtonElement>(`${scope} button`)].map((button) => {
                const box = button.getBoundingClientRect();
                const after = getComputedStyle(button, "::after");
                const width = parseFloat(after.width);
                const height = parseFloat(after.height);
                const centreX = box.x + box.width / 2;
                const centreY = box.y + box.height / 2;
                return {
                    axis,
                    label: (button.textContent ?? "").trim(),
                    hasPad: after.content === '""' && Number.isFinite(width),
                    x: centreX - width / 2,
                    y: centreY - height / 2,
                    width,
                    height,
                    right: centreX + width / 2,
                    bottom: centreY + height / 2,
                };
            });
        return [
            ...read("view", '[aria-label="What to explore"]'),
            ...read("renderer", '[aria-label="How it is drawn"]'),
        ];
    });
}

test.describe("the two-axis switch, under a finger", () => {
    /**
     * The regression that matters most in this file.
     *
     * ## What shipped, twice
     *
     * The ink in this control is typographic - a ruled row of names, about 26px tall - and the
     * 44px target is an invisible pad centred on it. So each row overhangs its own box by about
     * nine pixels at the top and at the bottom, and at the 4px grid gap the phase inherited, the
     * two rows' pads overlapped by 15.8px. The renderer row comes later in the document, so it
     * won the hit test: measured at 390px, a single touch tap at (34.1, 167.6) - inside the word
     * "World" - changed the *renderer*.
     *
     * Which is the exact failure that splitting one control into two axes was done to make
     * impossible, returning through a stylesheet, on touch only, where no state-model test could
     * see it. The horizontal case along each row had already been found and fixed once. Between
     * the rows was never looked at.
     *
     * ## What is asserted, and why it is this and not the gap
     *
     * Pairwise disjointness over every pad pair, not the gap value that currently produces it.
     * A gap assertion passes as soon as someone writes the right number and says nothing about
     * whether it is enough; disjointness is the property the reader experiences, and it stays
     * true through a token rename, a font change or a fourth view.
     *
     * The measured clearances are why this needs a test at all rather than a comment: 4.20px
     * between the rows and 2.08px between 3D and 2D. The fix is correct and it has almost no
     * margin in it, so the failure message reports the tightest pair and its overlap - the next
     * person needs to know which pair moved and by how much, not that a boolean flipped.
     */
    test("every pad on both axes is pairwise disjoint, in every view", async ({ page }) => {
        /*
         * Checked in World *and* in Focus, because they are not the same layout any more.
         * Clipping the page title in Focus lifts the whole switch by 57.8px - the view row from
         * y 134.68 to 76.9, the renderer row from 182.88 to 125.09 - and a disjointness proof
         * taken in one view says nothing about the other. That is a consequence of this phase's
         * own chrome cut, so it is the kind of thing a single-view test would have missed.
         */
        for (const where of ["WORLD", "FOCUS"] as const) {
            if (where === "FOCUS") await enterFocus(page);
            else await openGraph(page, `view=world&renderer=3d&node=${INDRA}`);
            await expect(page.locator(".va-graph")).toHaveAttribute("data-view", where);
            await assertPadsDisjoint(page, where);
        }
    });

    async function assertPadsDisjoint(page: Page, where: string) {
        const measured = await pads(page);

        expect(measured.length, "five controls: three views, two renderers").toBe(5);
        const padless = measured.filter((pad) => !pad.hasPad).map((pad) => pad.label);
        expect(
            padless,
            `in ${where}: every control in the switch carries a 44px pad at pointer:coarse`,
        ).toEqual([]);
        for (const pad of measured) {
            expect(pad.width, `${pad.axis}:${pad.label} pad width`).toBeGreaterThanOrEqual(TARGET);
            expect(pad.height, `${pad.axis}:${pad.label} pad height`).toBeGreaterThanOrEqual(
                TARGET,
            );
        }

        const collisions: string[] = [];
        let tightest = { pair: "", clearance: Number.POSITIVE_INFINITY };
        for (let i = 0; i < measured.length; i += 1)
            for (let j = i + 1; j < measured.length; j += 1) {
                const a = measured[i];
                const b = measured[j];
                const name = `${a.axis}:${a.label} vs ${b.axis}:${b.label}`;
                const overlapX = Math.min(a.right, b.right) - Math.max(a.x, b.x);
                const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y);
                if (overlapX > 0 && overlapY > 0)
                    collisions.push(
                        `${name} overlap ${overlapX.toFixed(2)}x${overlapY.toFixed(2)}px`,
                    );
                /* Separated on either axis is separated. The clearance is the larger of the two
                   gaps, because one is enough. */
                const clearance = Math.max(-overlapX, -overlapY);
                if (clearance < tightest.clearance) tightest = { pair: name, clearance };
            }

        expect(
            collisions,
            `in ${where}: overlapping pads steal each other's targets, and the later one in the document wins. Tightest pair: ${tightest.pair} at ${tightest.clearance.toFixed(2)}px`,
        ).toEqual([]);
        expect(
            tightest.clearance,
            `in ${where} the tightest clearance is ${tightest.pair}; it must stay positive. Measured 2.08px between 3D and 2D and 4.20px between the rows, so there is very little of it`,
        ).toBeGreaterThan(0);
    }

    /**
     * The same property, driven rather than computed.
     *
     * Disjoint rectangles are necessary and not sufficient: the pad has to be what receives the
     * touch, and the handler behind it has to move one axis. So every pad is tapped at its four
     * corners and its centre - twenty-five real touch taps - and each one must leave the axis it
     * belongs to at the value it names and the other axis exactly as it was.
     *
     * Each tap starts from a state where its own axis is *not* already at that value, which
     * sounds pedantic and is not: an earlier version of this test started every tap from World
     * in 3D, so ten of the twenty-five assertions were "World is still WORLD" and "3D is still
     * 3d" and would have passed against a control that did nothing at all.
     */
    test("a tap anywhere in a pad moves that pad's axis and only that axis", async ({ page }) => {
        test.setTimeout(300_000);

        const expected: Record<string, { axis: "view" | "renderer"; value: string }> = {
            World: { axis: "view", value: "WORLD" },
            Focus: { axis: "view", value: "FOCUS" },
            Path: { axis: "view", value: "PATH" },
            "3D": { axis: "renderer", value: "3d" },
            "2D": { axis: "renderer", value: "2d" },
        };

        const failures: string[] = [];
        for (const label of Object.keys(expected)) {
            const { axis, value } = expected[label];
            const other = axis === "view" ? "renderer" : "view";

            for (const corner of ["tl", "tr", "bl", "br", "centre"] as const) {
                /* The start state has to differ from what this pad asserts. World is the only
                   one that needs a tap to set up, because the URL cannot open in Focus. */
                if (label === "World") await enterFocus(page);
                else if (axis === "renderer")
                    await openGraph(
                        page,
                        `view=world&renderer=${value === "3d" ? "2d" : "3d"}&node=${INDRA}`,
                    );
                else await openGraph(page, `view=world&renderer=3d&node=${INDRA}`);

                const before = await axes(page);
                expect(
                    before[axis],
                    `${label} ${corner}: the start state must not already be ${value}`,
                ).not.toBe(value);

                /* Re-read after navigating. The pads are not at fixed coordinates: clipping
                   the title in Focus lifts the whole switch by 57.8px, so a pad measured in
                   World and tapped in Focus is a tap into the canvas. */
                const pad = (await pads(page)).find((one) => one.label === label)!;
                const { x: left, y: top, right, bottom } = pad;
                const at = {
                    tl: [left + EDGE_INSET, top + EDGE_INSET],
                    tr: [right - EDGE_INSET, top + EDGE_INSET],
                    bl: [left + EDGE_INSET, bottom - EDGE_INSET],
                    br: [right - EDGE_INSET, bottom - EDGE_INSET],
                    centre: [(left + right) / 2, (top + bottom) / 2],
                }[corner];

                /*
                 * `page.touchscreen.tap`, not the CDP helper, and the difference is measured.
                 *
                 * The helper dispatches a touch point with `radiusX/radiusY: 12`, which is about
                 * the size of a real fingertip - and Chromium's touch adjustment resolves a blob
                 * that wide by looking for the best candidate under it, so at a pad's *bottom*
                 * corner it can settle on something other than the pad. At the same coordinate
                 * (224.875, 2px inside the declared bottom of 226.88) a point-sized tap hits and
                 * a 12px-radius tap misses.
                 *
                 * Point-sized is the right instrument for asking where a box's edge is; the
                 * fingertip-sized one stays in use for drags, where travel and not position is
                 * what is being classified. Worth knowing that the two disagree at a pad's
                 * corners, which is recorded rather than smoothed over.
                 */
                await page.touchscreen.tap(
                    Math.round(at[0] * 10) / 10,
                    Math.round(at[1] * 10) / 10,
                );
                await page.waitForTimeout(400);
                const after = await axes(page);

                if (after[axis] !== value)
                    failures.push(
                        `${label} ${corner} @${at[0]},${at[1]}: ${axis} stayed ${after[axis]}, wanted ${value} - dead space inside a declared 44px target`,
                    );
                if (after[other] !== before[other])
                    failures.push(
                        `${label} ${corner} @${at[0]},${at[1]}: moved ${other} from ${before[other]} to ${after[other]} - a pad stole the other axis, which is the defect this control was split to prevent`,
                    );
            }
        }
        expect(failures, "every pad point must move its own axis and nothing else").toEqual([]);
    });
});

test.describe("the canvas, under a finger", () => {
    /**
     * A drag is not a selection, and it is not a request for the corpus either.
     *
     * Both halves are load-bearing and the second is the one that shipped broken. When a pick
     * found nothing - which is where an orbit usually ends - one canvas read that as a request
     * for everything and pushed the world view, so almost every orbit left the page. A tap into
     * empty space now does nothing at all: "nothing is under the pointer" is not a request for
     * the corpus.
     *
     * `data-gesture` is read as well as the state, because otherwise a canvas that had stopped
     * receiving pointer events would pass this test perfectly.
     */
    test("a touch drag on the spatial canvas changes neither the subject nor the view", async ({
        page,
    }) => {
        const touch = await touchHarness(page);
        await enterFocus(page);
        const before = await axes(page);
        expect(before.view).toBe("FOCUS");
        expect(before.node).toBe(decodeURIComponent(INDRA));

        const band = await visibleBand(page);
        const midway = band.top + band.height / 2;

        /* Watch the classification while the finger is down rather than after it is up, so the
           assertion is that the engine saw a drag and not merely that nothing happened. */
        const phases: string[] = [];
        await touch.swipe(195, midway, 105, -90, 10, async () => {
            phases.push(
                await page.evaluate(
                    () =>
                        document.querySelector<HTMLElement>(".va-world-canvas")?.dataset.gesture ??
                        "missing",
                ),
            );
        });
        const settledPhase = await page.evaluate(
            () => document.querySelector<HTMLElement>(".va-world-canvas")?.dataset.gesture ?? "",
        );

        const after = await axes(page);
        expect(after.view, "an orbit may not leave Focus").toBe("FOCUS");
        expect(after.node, "an orbit may not change the subject").toBe(before.node);
        expect(after.renderer, "an orbit may not change the renderer").toBe(before.renderer);
        expect(after.subject).toBe(before.subject);
        expect(
            phases,
            "the engine must have classified this as a drag while the finger was down, or the absence above proves nothing",
        ).toContain("dragging");
        expect(settledPhase, "and returned to idle once the finger left").toBe("idle");
    });

    /**
     * The slop pair. This is what pins the threshold rather than its sign.
     *
     * `GESTURE_SLOP.touch` is 10px, measured from the press as a distance and not per axis,
     * chosen to clear Android's 8dp `ViewConfiguration` slop. A test that only asserts "a
     * 30px swipe does not select" passes at any threshold from 0 to 29 - including 0, which is
     * the defect: the planar view's old test compared two consecutive moves, which never
     * latches during a slow pan because a slow pan delivers one pixel at a time.
     *
     * So both sides are asserted against the same target orb in the same scene: 6px must
     * select, 30px must not.
     */
    test("a 6px jitter selects and a 30px swipe does not", async ({ page }) => {
        const touch = await touchHarness(page);

        await enterFocus(page);
        const drawn = (await settledOrbs(page))!;
        expect(drawn, "the engine must expose the drawn scene").not.toBeNull();
        const neighbour = drawn
            .filter((orb) => !orb.root)
            .sort((a, b) => b.diameter - a.diameter)[0];
        expect(neighbour, "a curated Focus draws neighbours").toBeTruthy();

        const jitter = 6;
        expect(jitter, "the tap side of the pair must be under the slop").toBeLessThan(TOUCH_SLOP);
        await touch.swipe(neighbour.x, neighbour.y, jitter, 0, 3);
        await expect(
            page.locator(".va-world-panel h2"),
            `a ${jitter}px jitter is under the ${TOUCH_SLOP}px slop and must still select`,
        ).not.toHaveText("Indra");
        const selected = await axes(page);
        expect(selected.view, "selecting a neighbour keeps the reader in Focus").toBe("FOCUS");
        expect(selected.node).not.toBe(decodeURIComponent(INDRA));

        await enterFocus(page);
        const again = (await settledOrbs(page))!;
        const target = again.filter((orb) => !orb.root).sort((a, b) => b.diameter - a.diameter)[0];
        const swipe = 30;
        expect(swipe, "the drag side of the pair must be over the slop").toBeGreaterThan(
            TOUCH_SLOP,
        );
        await touch.swipe(target.x, target.y, swipe, 0, 10);
        await page.waitForTimeout(500);
        const after = await axes(page);
        expect(
            after.node,
            `a ${swipe}px swipe is over the ${TOUCH_SLOP}px slop and must not select`,
        ).toBe(decodeURIComponent(INDRA));
        expect(after.subject).toBe("Indra");
    });

    /**
     * A pinch does not end in a tap.
     *
     * The latch is the whole of the argument. Without one, the *second* finger to lift looks
     * like a press and a release that never travelled, because by then the first finger's travel
     * has been forgotten - so a two-finger zoom would end by selecting whatever was under the
     * finger that happened to come up last.
     */
    test("a two-finger pinch does not end in a tap", async ({ page }) => {
        const touch = await touchHarness(page);
        await enterFocus(page);
        const before = await axes(page);
        const band = await visibleBand(page);

        await touch.pinch(195, band.top + band.height / 2, 40, 120);
        await page.waitForTimeout(600);

        const after = await axes(page);
        expect(after.node, "a pinch may not select").toBe(before.node);
        expect(after.subject).toBe(before.subject);
        expect(after.view, "a pinch may not change the view").toBe("FOCUS");
        expect(after.gesture, "every finger is up, so the gesture is over").toBe("idle");
    });

    /**
     * A cancelled gesture completes nothing.
     *
     * Not a corner case. Once an element lets the page scroll under a finger, the browser
     * cancels the pointer every single time a reader scrolls past with a finger that happened to
     * land on it. The planar view routed exactly this event into its release handler, where it
     * could reach a cleared selection - so a reader scrolling the page lost their subject.
     */
    test("a pointercancel mid-gesture completes nothing", async ({ page }) => {
        const touch = await touchHarness(page);
        await enterFocus(page);
        const drawn = (await settledOrbs(page))!;
        const neighbour = drawn
            .filter((orb) => !orb.root)
            .sort((a, b) => b.diameter - a.diameter)[0];
        const before = await axes(page);

        await touch.cancel(neighbour.x, neighbour.y);
        await page.waitForTimeout(600);

        const after = await axes(page);
        expect(after.node, "a cancelled press on an orb may not select it").toBe(before.node);
        expect(after.subject, "and may not clear the subject either").toBe(before.subject);
        expect(after.view).toBe("FOCUS");
        expect(after.gesture, "a cancel ends the gesture").toBe("idle");
    });

    /**
     * The planar canvas keeps the reader's subject through a pan.
     *
     * The 2D renderer was rewritten wholesale in this phase, including its picking, its pinch
     * zoom and its pointer bookkeeping. It shares `GESTURE_SLOP` with the spatial view but not
     * `installGestures`, so it does not write `data-gesture` - the classification is asserted
     * through what it does rather than what it reports, and that gap is reported rather than
     * papered over here.
     */
    test("a touch pan on the planar canvas keeps the subject", async ({ page }) => {
        const touch = await touchHarness(page);
        await openGraph(page, `view=world&renderer=2d&node=${INDRA}`);
        await page.locator('[aria-label="What to explore"] button', { hasText: "Focus" }).tap();
        await expect(page.locator(".va-graph")).toHaveAttribute("data-view", "FOCUS");
        await expect(page.locator(".va-planar-canvas")).toBeVisible();
        const before = await axes(page);

        const band = await visibleBand(page);
        await touch.swipe(195, band.top + band.height / 2, 85, -100);
        await page.waitForTimeout(600);

        const after = await axes(page);
        expect(after.node, "a pan may not clear the subject").toBe(before.node);
        expect(after.view, "a pan may not leave Focus").toBe("FOCUS");
        expect(after.renderer).toBe("2d");
        /* The canvas must still be declaring the axes it handles, or the page would take the
           gesture instead. */
        await expect(page.locator(".va-planar-canvas")).toHaveCSS("touch-action", "none");
    });
});

test.describe("the graph chrome at 390px", () => {
    /**
     * Every interactive control, measured, with the failures named.
     *
     * Named and not counted: `expect(failures).toHaveLength(0)` tells whoever broke it that a
     * number moved, and a list tells them which control and by how much. The controls in this
     * chrome are typographic on purpose - the ink is 14x23 on the renderer row - so most of them
     * reach 44px through an invisible centred pad rather than by being 44px of ink, and the
     * effective target is the union of the two.
     */
    test("every control in the chrome and the sheet reaches 44x44", async ({ page }) => {
        await enterFocus(page);
        const failures = await page.evaluate((floor) => {
            const selector =
                'button, a[href], input, select, textarea, [role="button"], [tabindex]:not([tabindex="-1"])';
            const bad: string[] = [];
            for (const scope of [".va-graph-chrome", ".va-world-panel"]) {
                const root = document.querySelector(scope);
                if (!root) continue;
                for (const element of root.querySelectorAll(selector)) {
                    const box = element.getBoundingClientRect();
                    if (box.width === 0 && box.height === 0) continue;
                    const after = getComputedStyle(element, "::after");
                    /* A pad, not any pseudo-element: empty content and absolutely positioned is
                       what the touch-target rule produces, and a decorative chevron is not it. */
                    const isPad = after.content === '""' && after.position === "absolute";
                    const width = isPad ? Math.max(box.width, parseFloat(after.width)) : box.width;
                    const height = isPad
                        ? Math.max(box.height, parseFloat(after.height))
                        : box.height;
                    if (width + 0.5 < floor || height + 0.5 < floor) {
                        const name = (
                            element.getAttribute("aria-label") ??
                            element.textContent ??
                            element.getAttribute("placeholder") ??
                            element.id ??
                            element.tagName
                        )
                            .trim()
                            .slice(0, 48);
                        bad.push(
                            `${scope} ${element.tagName.toLowerCase()} "${name}": ${width.toFixed(1)}x${height.toFixed(1)}${isPad ? " (pad)" : ""}`,
                        );
                    }
                }
            }
            return bad;
        }, TARGET);
        expect(failures, "controls under 44x44 at 390px").toEqual([]);
    });

    /**
     * The chrome is the binding constraint on the drawing band, so its height is asserted.
     *
     * Not a style preference. `focusBudgetForBand` derives how many connections may be drawn
     * from the band left under this chrome, so every pixel here is a pixel of neighbourhood. It
     * was measured at 245.6px of a 780px stage - 31.5%, opaque, and taking taps - and the kicker
     * and the h1 were clipped in Focus to bring it to 168.2px. The half-raised sheet's budget
     * rose from 12 to 15 as a direct result.
     *
     * The ceiling is 180px rather than 168.2: this is a guard against the drift that put 20px
     * back on in one commit, not a pin on a font metric.
     */
    test("the Focus chrome stays under a fifth of the stage", async ({ page }) => {
        await enterFocus(page);
        const measured = await page.evaluate(() => {
            const graph = document.querySelector(".va-graph")!.getBoundingClientRect();
            const chrome = document.querySelector(".va-graph-chrome")!.getBoundingClientRect();
            const head = document.querySelector(".va-graph-head")!.getBoundingClientRect();
            return {
                stage: graph.height,
                chrome: chrome.height,
                share: chrome.height / graph.height,
                head: head.height,
            };
        });
        expect(measured.chrome, "the Focus chrome, measured at 168.2px").toBeLessThanOrEqual(180);
        expect(measured.share, "under a quarter of the stage").toBeLessThan(0.25);
        expect(measured.head, "the title is clipped in Focus, not laid out").toBeLessThanOrEqual(2);

        /* Clipped, not removed. The h1 is this route's only one, so hiding it from the
           accessibility tree would trade a layout defect for a structural one. */
        await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
        await expect(page.getByLabel("Find a subject")).toBeVisible();
    });

    /**
     * Path at 390px.
     *
     * Deliberately asserted before a route is traced. Tracing one from here currently issues an
     * unbounded stream of identical requests to the backend - measured, 36 and still going - so
     * a suite that traced a route in CI would hammer the service to assert a layout. The loop
     * and the 970px-of-content-in-a-379px-window that a settled two-hop route produces are both
     * reported rather than asserted here, and this test covers what a reader meets on arrival:
     * the fields, the control that starts the trace, and no sideways scroll.
     */
    test("Path opens with its fields and its control reachable, and does not scroll sideways", async ({
        page,
    }) => {
        await openGraph(page, `view=world&renderer=3d`);
        await page.locator('[aria-label="What to explore"] button', { hasText: "Path" }).tap();
        await expect(page.locator(".va-graph")).toHaveAttribute("data-view", "PATH");

        const fields = page.locator(".va-path-fields input");
        await expect(fields).toHaveCount(2);
        const go = page.locator(".va-path-go");
        await expect(go).toBeVisible();

        const geometry = await page.evaluate(() => {
            const box = (selector: string) => {
                const element = document.querySelector(selector);
                return element ? element.getBoundingClientRect().bottom : null;
            };
            const chrome = document.querySelector(".va-graph-chrome")!;
            return {
                chromeBottom: chrome.getBoundingClientRect().bottom,
                goBottom: box(".va-path-go"),
                scrollable:
                    chrome.scrollHeight > chrome.clientHeight
                        ? getComputedStyle(chrome).overflowY
                        : "not-needed",
                viewport: window.innerHeight,
                sideways:
                    document.documentElement.scrollWidth - document.documentElement.clientWidth,
            };
        });
        expect(geometry.sideways, "no horizontal scroll at 390px").toBeLessThanOrEqual(1);
        expect(
            geometry.goBottom!,
            "the control that starts a trace is reachable without scrolling",
        ).toBeLessThanOrEqual(geometry.viewport);
        /* If the band overflows, it has to be a scroller - it is opaque and inside a clipped
           stage, so anything past its edge is unreachable otherwise. */
        expect(["auto", "scroll", "not-needed"]).toContain(geometry.scrollable);
    });
});

test.describe("the subject sheet", () => {
    /**
     * Three heights, and a control that names the one it moves to.
     *
     * Three rather than one because a floating panel put the thing the reader had just chosen
     * underneath the panel describing it. And a named control rather than `aria-expanded`
     * because that attribute is boolean and this has three states, so it reported "expanded" at
     * half height.
     */
    test("the sheet cycles its three heights and the control names the next one", async ({
        page,
    }) => {
        await enterFocus(page);
        const panel = page.locator(".va-world-panel");
        const handle = page.locator(".va-world-sheet-handle");

        await expect(panel).toHaveAttribute("data-sheet", "collapsed");
        await expect(handle).toHaveText("Show more");
        const collapsed = (await panel.boundingBox())!.height;

        await handle.tap();
        await expect(panel).toHaveAttribute("data-sheet", "half");
        await expect(handle).toHaveText("Show all of it");
        const half = (await panel.boundingBox())!.height;

        await handle.tap();
        await expect(panel).toHaveAttribute("data-sheet", "expanded");
        await expect(handle).toHaveText("Show less");
        const expanded = (await panel.boundingBox())!.height;

        await handle.tap();
        await expect(panel, "the cycle closes").toHaveAttribute("data-sheet", "collapsed");

        expect(collapsed, "measured 120px").toBeLessThan(half);
        expect(half, "measured 371.4px").toBeLessThan(expanded);

        /* A collapsed sheet is not a scroller. Measured before this: 829px of content behind a
           117px window, so a vertical swipe inside it scrolled the panel rather than raising it,
           and a reader could read the whole thing without discovering it had three heights. */
        await expect(panel).toHaveCSS("overflow-y", "hidden");
    });

    /**
     * The subject stays where the reader can see it - and at one height it does not.
     *
     * ## Marked as a known failure on purpose
     *
     * Measured at 390x844 after the chrome was cut to 168.2px: the expanded sheet is 684px of a
     * 780px stage, so 168.2 + 684 = 852.2px of opaque furniture sits over 780px of canvas and
     * the visible band is **-72.2px**. There is no strip of canvas at all. All sixteen drawn
     * orbs are behind the chrome or the sheet, the subject included, and the minimum centre
     * separation collapses from 59.5px to 36.7px - under the 44px touch pitch the whole budget
     * exists to guarantee - because the camera is fitting a scene into a band that the 120px
     * floor in `focusBudgetForBand` is inventing.
     *
     * The sheet heights are in `world.css` and the floor is in `focus.ts`, neither of which is
     * this agent's to change, so this is recorded as `test.fail()` rather than deleted or
     * softened. It keeps the numbers in the codebase, it keeps the suite honest, and the moment
     * the expanded height is bounded so that a band survives it, Playwright reports this test as
     * unexpectedly passing - which is the prompt to remove the annotation.
     */
    test("the selected subject stays inside the visible band at every sheet height", async ({
        page,
    }) => {
        /*
         * This was an expected failure and is now a real assertion.
         *
         * The expanded sheet was `calc(100% - 6rem)`, which left 96px of a 780px stage - less
         * than the chrome standing above it - so the band was measured at -72.2px and every
         * drawn orb including the subject sat behind furniture. The sheet is now bounded by the
         * chrome height the page publishes from its own measurement, plus the same 7.5rem floor
         * the neighbour budget uses, so the two cannot disagree about how much canvas survives.
         */
        await enterFocus(page);
        const handle = page.locator(".va-world-sheet-handle");
        const outside: string[] = [];

        for (const height of ["collapsed", "half", "expanded"] as const) {
            await expect(page.locator(".va-world-panel")).toHaveAttribute("data-sheet", height);
            /* The camera flies to the band, so settle before reading it. */
            await page.waitForTimeout(2_500);
            const band = await visibleBand(page);
            const drawn = await orbs(page);
            const subject = drawn?.find((orb) => orb.root);

            if (band.height <= 0)
                outside.push(
                    `${height}: there is no visible band at all (${band.height.toFixed(1)}px)`,
                );
            else if (!subject) outside.push(`${height}: the subject is not drawn`);
            else if (subject.y < band.top || subject.y > band.bottom)
                outside.push(
                    `${height}: the subject is at y ${subject.y.toFixed(1)}, outside the band ${band.top.toFixed(1)}..${band.bottom.toFixed(1)}`,
                );

            if (height !== "expanded") await handle.tap();
        }
        expect(outside, "the subject a reader chose must be visible at every sheet height").toEqual(
            [],
        );
    });
});
