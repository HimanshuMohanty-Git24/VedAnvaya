import { expect, test, type Locator, type Page } from "@playwright/test";

/**
 * Focus, held - the graph page's own canvas coverage.
 *
 * ## Why this file exists
 *
 * The suite was green on both of the P0 defects this phase was opened to fix, and an audit
 * found the reason: no end-to-end test anywhere in this repository touched a canvas with a
 * pointer. There were no `mouse.down`/`move`/`up` sequences, no `dragTo`, and no clicks on a
 * canvas element. Every graph assertion arrived by URL and read the DOM afterwards. A defect
 * that only a gesture can produce was therefore unreachable, and the two that shipped were
 * exactly that shape:
 *
 *   - a reader who had selected Indra and was exploring its neighbourhood was returned to the
 *     whole corpus without asking. A planar pan whose movement threshold never latched was
 *     classified as a click, the click found empty canvas, and the resulting null selection
 *     demoted FOCUS to WORLD;
 *   - the renderer changed underneath a reader who had only changed what they were looking at.
 *
 * Both are invisible to a test that navigates and reads. So this file drives the canvas.
 *
 * ## Why it asserts against a trace as well as the DOM
 *
 * `data-view` sampled between interactions proves the state was right when it was looked at,
 * not that it was never wrong. The semantic-state trace added in 55e8715 (`__vedaGraphTrace`,
 * see `src/lib/world/graph-state.ts`) records every transition with the cause that asked for
 * it, and marks with `refused` any cause that reached for something it was not entitled to
 * change. That turns "the graph did not visibly reset" into two exact claims: nothing was
 * refused, and nothing left Focus except the reader.
 */

const INDRA_ID = "VG:DEVATA:INDRAH";
const INDRA = encodeURIComponent(INDRA_ID);

/** The world is a two-megabyte artifact and a settling layout; it is not a fast page. */
const SETTLE = 30_000;

/** How long the graph has to survive being used, per renderer. Required by the phase. */
const SOAK_MS = 60_000;

/*
 * A soak test needs its own timeout, set explicitly.
 *
 * The project default is 60s, which this would exceed on the interaction loop alone before
 * the world artifact had even finished loading. The budget is the 60s of interaction, plus up
 * to 30s to load and settle the world at entry, plus the interaction round that is in flight
 * when the deadline passes - a stepped orbit and a hover sweep are around 60 pointer round
 * trips each. 150s leaves that comfortable without letting a genuinely hung page sit for
 * minutes before it reports.
 */
const SOAK_TIMEOUT = 150_000;

type Renderer = "3d" | "2d";

/** One line of `__vedaGraphTrace`. Mirrors `GraphTransition` in graph-state.ts. */
type Transition = {
    at: number;
    from: string;
    to: string;
    reason: string;
    node: string | null;
    renderer: string;
    url: string;
    /** Set where a cause reached for something it was not entitled to change. A defect. */
    refused?: string;
};

/**
 * The engine handle the spatial view publishes on `window`, as far as this file uses it.
 *
 * `camera` is a private field on the engine, declared here because the node-drag test below
 * has to state that the camera did not move and there is nothing else on screen to state it
 * through. See the note on that test.
 */
type Stage = {
    orbGeometry(
        nodes: Iterable<number>,
    ): Array<{ node: number; x: number; y: number; depth: number; radius: number }>;
    screenPositionOf(node: number): { x: number; y: number; z: number } | null;
    currentMode: string;
    /** Private on the engine. See the note on the node-drag test for why it is read here. */
    camera?: {
        position: { x: number; y: number; z: number };
        quaternion: { x: number; y: number; z: number; w: number };
    };
};

const CANVAS: Record<Renderer, string> = {
    "3d": ".va-world-canvas",
    "2d": ".va-planar-canvas",
};

/* ------------------------------------------------------------------ reading - */

async function readTrace(page: Page): Promise<Transition[]> {
    return page.evaluate(() => {
        const held = window as unknown as { __vedaGraphTrace?: Transition[] };
        return held.__vedaGraphTrace ?? [];
    });
}

/**
 * Watch the semantic state on a 50ms interval from inside the page.
 *
 * Between-interaction assertions cannot see a state that flipped and flipped back inside one
 * gesture, and that is precisely how the reported defect behaved: the demotion happened on
 * pointer release. This records every sample that disagrees with the invariant, so a
 * transient violation is still evidence.
 */
async function startWatchdog(page: Page, renderer: Renderer) {
    await page.evaluate(
        ({ renderer, encodedNode }) => {
            const held = window as unknown as {
                __soakViolations?: string[];
                __soakTimer?: number;
                __soakSamples?: number;
            };
            const violations: string[] = [];
            held.__soakViolations = violations;
            held.__soakSamples = 0;
            const started = Date.now();
            held.__soakTimer = window.setInterval(() => {
                held.__soakSamples = (held.__soakSamples ?? 0) + 1;
                const at = `t+${Date.now() - started}ms`;
                const graph = document.querySelector(".va-graph");
                if (!graph) {
                    violations.push(`${at}: .va-graph left the document`);
                    return;
                }
                const view = graph.getAttribute("data-view");
                const drawn = graph.getAttribute("data-renderer");
                if (view !== "FOCUS") violations.push(`${at}: data-view became ${view}`);
                if (drawn !== renderer) violations.push(`${at}: data-renderer became ${drawn}`);
                if (!window.location.search.includes(encodedNode)) {
                    violations.push(`${at}: the URL lost the subject (${window.location.search})`);
                }
            }, 50);
        },
        { renderer, encodedNode: INDRA },
    );
}

async function stopWatchdog(page: Page) {
    return page.evaluate(() => {
        const held = window as unknown as {
            __soakViolations?: string[];
            __soakTimer?: number;
            __soakSamples?: number;
        };
        if (held.__soakTimer) window.clearInterval(held.__soakTimer);
        return {
            violations: [...new Set(held.__soakViolations ?? [])],
            samples: held.__soakSamples ?? 0,
        };
    });
}

/** The three things that must not move, asserted between every interaction. */
async function hold(page: Page, renderer: Renderer, when: string) {
    const graph = page.locator(".va-graph");
    await expect(graph, `${when}: the reader was moved out of Focus`).toHaveAttribute(
        "data-view",
        "FOCUS",
    );
    await expect(graph, `${when}: the renderer changed on its own`).toHaveAttribute(
        "data-renderer",
        renderer,
    );
    expect(page.url(), `${when}: the URL lost the subject`).toContain(INDRA);
}

/* ------------------------------------------------------------- interactions - */

async function boxOf(canvas: Locator, what: string) {
    const box = await canvas.boundingBox();
    expect(box, `${what} has no box, so no gesture could be delivered to it`).not.toBeNull();
    return box!;
}

/**
 * Orbit the canvas: press, many stepped moves, release.
 *
 * Stepped deliberately. `mouse.move(a, b)` in one jump is a single pointer event and tells a
 * gesture classifier nothing; the classifier reads the deltas between consecutive moves, so a
 * test that does not produce a sequence of them is not testing it.
 */
async function orbit(page: Page, canvas: Locator) {
    const box = await boxOf(canvas, "the canvas");
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    for (let step = 1; step <= 30; step += 1) {
        await page.mouse.move(cx + step * 5, cy + Math.sin(step / 4) * 24);
    }
    await page.mouse.up();
}

/** Hover right across the canvas, which is what drives hit-testing and hover state. */
async function sweep(page: Page, canvas: Locator) {
    const box = await boxOf(canvas, "the canvas");
    for (let step = 0; step <= 24; step += 1) {
        await page.mouse.move(box.x + (box.width * step) / 24, box.y + box.height * 0.45);
    }
}

/**
 * The gesture that used to demote FOCUS to WORLD.
 *
 * Delivered as many individual one-pixel moves, because that is the reported condition: a pan
 * slow enough that no single pointer event moved more than a pixel never latched the movement
 * threshold, so release was classified as a click. It is kept inside one corner of the canvas
 * and returns to where it started, so both the press and the release land on empty canvas -
 * which is the other half of the condition, since the click had to find nothing for a null
 * selection to be written.
 *
 * A `reader:select-subject` in the trace after this ran means the corner was not empty after
 * all and these coordinates need moving; it does not mean the product is wrong.
 */
async function slowPan(page: Page, canvas: Locator) {
    const box = await boxOf(canvas, "the planar canvas");
    const x = box.x + box.width * 0.07;
    const y = box.y + box.height * 0.9;
    await page.mouse.move(x, y);
    await page.mouse.down();
    for (let step = 1; step <= 60; step += 1) await page.mouse.move(x + step, y - step * 0.5);
    for (let step = 59; step >= 0; step -= 1) await page.mouse.move(x + step, y - step * 0.5);
    await page.mouse.up();
}

/**
 * Open a relationship, read it, close it. Returns whether one was actually reachable.
 *
 * Every step is bounded, and that is not incidental. A first version selected candidates on
 * inline opacity alone - which is how the rest of this suite decides a label is current - and
 * then clicked with the default timeout. In the planar renderer that hung: the 27th label
 * reported `opacity: 1` while never becoming hit-testable, so the click waited for "visible,
 * enabled and stable" until the whole soak timed out at 150s. The soak then reported a
 * timeout, which says nothing about whether Focus held.
 *
 * Opacity is a statement about paint, not about hit-testing, so it is now only the first of
 * three filters: the label must also be visible to Playwright and have a real box, and the
 * click itself is bounded so an unclickable candidate costs a second and moves on. The
 * coverage claim is kept where it belongs - the caller counts successes and the soak asserts
 * at the end that at least one relationship was opened - so this cannot quietly degrade into
 * a soak that skips the interaction entirely.
 */
async function tapRelationship(page: Page) {
    /*
     * The candidate is chosen in one page evaluation, not by walking `nth()`.
     *
     * The three filters above were right about *what* makes a label clickable and wrong about
     * *how* to ask. Reading a count and then walking `locator.nth(index)` is three round trips
     * per candidate against a DOM that is moving: the pool retires and reuses spans as the
     * camera turns, so an index that existed when the count was taken may not exist when it is
     * resolved - and `nth()` waits for it. That is not a slow click, it is an unbounded one,
     * and it timed out the whole sixty-second soak on a scene where Focus never wavered. The
     * soak then reported a timeout, which says nothing about the thing it exists to prove.
     *
     * So the enumeration is atomic. One evaluation reads every span, applies the real
     * hit test - `elementFromPoint` at the centre, which is what "clickable" actually means and
     * is stricter than a visible box - and returns a coordinate. Nothing after that can wait on
     * an element that has since gone, because nothing after that names one.
     */
    const target = await page.evaluate(() => {
        const spans = [...document.querySelectorAll('.va-edge-label[data-pickable="true"]')];
        for (const span of spans) {
            const node = span as HTMLElement;
            if (node.style.opacity !== "1") continue;
            const box = node.getBoundingClientRect();
            if (box.width === 0 || box.height === 0) continue;
            const x = box.left + box.width / 2;
            const y = box.top + box.height / 2;
            /* Topmost at its own centre, or a click there would land on whatever is over it. */
            const hit = document.elementFromPoint(x, y);
            if (!hit || !(hit === node || node.contains(hit))) continue;
            return { x, y, text: node.textContent ?? "" };
        }
        return null;
    });
    if (!target) return false;

    try {
        await page.mouse.click(target.x, target.y);
    } catch {
        return false;
    }
    const inspector = page.locator(".va-relationship");
    /* Bounded, so a click that landed on nothing costs a second rather than the test. */
    try {
        await expect(inspector).toBeVisible({ timeout: 2_000 });
    } catch {
        return false;
    }
    await page.keyboard.press("Escape");
    await expect(inspector).toHaveCount(0);
    return true;
}

/** Collapse the subject panel and open it again. */
async function cycleSheet(page: Page) {
    const handle = page.locator(".va-world-sheet-handle");
    if ((await handle.count()) === 0) return false;
    await handle.click();
    await handle.click();
    return true;
}

async function flipTheme(page: Page) {
    const toggle = page.getByRole("button", { name: "Switch between light and dark theme" });
    await toggle.click();
    await toggle.click();
}

/* ------------------------------------------------------------------- checks - */

function refusals(entries: Transition[]) {
    return entries.filter((entry) => entry.refused !== undefined);
}

/**
 * Transitions out of Focus that the reader did not ask for.
 *
 * `reader:` is the whole of the permitted set. A boot, a history navigation and a lost WebGL
 * context are the only other causes in the union, and none of them is a reason to stop
 * looking at the subject the reader chose.
 */
function unaskedDemotions(entries: Transition[]) {
    return entries.filter(
        (entry) =>
            entry.from === "FOCUS" && entry.to === "WORLD" && !entry.reason.startsWith("reader:"),
    );
}

async function assertTraceIsClean(page: Page, what: string) {
    const entries = await readTrace(page);
    /* Without this the two assertions below pass by reading an empty array, which is the
       failure mode this suite keeps a guards.ts for. The trace always holds at least the
       opening transition. */
    expect(
        entries.length,
        `${what}: __vedaGraphTrace is empty, so the assertions on it tested nothing. ` +
            `Either the instrumentation in graph-state.ts is gone or it never ran.`,
    ).toBeGreaterThan(0);

    expect(
        refusals(entries).map((entry) => `${entry.reason} -> ${entry.refused}`),
        `${what}: a cause reached for something it was not entitled to change`,
    ).toEqual([]);

    expect(
        unaskedDemotions(entries).map((entry) => `${entry.reason} (${entry.url})`),
        `${what}: something other than the reader moved the view from Focus back to World`,
    ).toEqual([]);
}

/* -------------------------------------------------------------------- soak - */

async function enter(page: Page, renderer: Renderer) {
    await page.goto(`/graph?view=focus&renderer=${renderer}&node=${INDRA}`);
    await expect(page.locator(CANVAS[renderer])).toBeVisible({ timeout: SETTLE });
    await expect(page.locator(".va-world-panel")).toBeVisible({ timeout: SETTLE });
    await hold(page, renderer, "on arriving from the deep link");
}

async function soak(page: Page, renderer: Renderer) {
    await enter(page, renderer);
    await startWatchdog(page, renderer);

    const deadline = Date.now() + SOAK_MS;
    let rounds = 0;
    let relationships = 0;
    let sheets = 0;

    while (Date.now() < deadline) {
        await orbit(page, page.locator(CANVAS[renderer]));
        await hold(page, renderer, `round ${rounds}, after a stepped orbit`);

        await sweep(page, page.locator(CANVAS[renderer]));
        await hold(page, renderer, `round ${rounds}, after a hover sweep`);

        if (await tapRelationship(page)) relationships += 1;
        await hold(page, renderer, `round ${rounds}, after opening a relationship`);

        if (await cycleSheet(page)) sheets += 1;
        await hold(page, renderer, `round ${rounds}, after collapsing and opening the panel`);

        await flipTheme(page);
        await hold(page, renderer, `round ${rounds}, after two theme changes`);

        if (renderer === "2d") {
            await slowPan(page, page.locator(CANVAS[renderer]));
            await hold(page, renderer, `round ${rounds}, after a slow one-pixel pan`);
        }

        /* Let the simulation settle with nobody touching it. A physics tick has no reason in
           the transition union, so this is the window in which an unauthorised write shows
           up rather than being masked by a gesture that was legitimately allowed one. */
        await page.waitForTimeout(1_500);
        await hold(page, renderer, `round ${rounds}, after the simulation settled`);
        rounds += 1;
    }

    const watched = await stopWatchdog(page);
    expect(
        watched.samples,
        "the in-page watchdog never sampled, so the continuous check tested nothing",
    ).toBeGreaterThan(100);
    expect(watched.violations, `the ${renderer} renderer did not hold Focus`).toEqual([]);

    await assertTraceIsClean(page, `the ${renderer} soak`);

    /* Coverage, stated. A soak that silently skipped an interaction is a soak that did not
       test it, and these two depend on something being on screen to act on. */
    expect(rounds, "the soak completed no interaction rounds").toBeGreaterThan(0);
    expect(
        relationships,
        "no relationship label was ever pickable, so that interaction was never exercised",
    ).toBeGreaterThan(0);
    expect(sheets, "the subject panel handle was never present").toBeGreaterThan(0);
}

test.describe("the graph holds the reader's place while it is used", () => {
    test("Focus survives sixty seconds of use in the spatial renderer", async ({ page }) => {
        test.setTimeout(SOAK_TIMEOUT);
        await soak(page, "3d");
    });

    test("Focus survives sixty seconds of use in the planar renderer", async ({ page }) => {
        test.setTimeout(SOAK_TIMEOUT);
        await soak(page, "2d");
    });

    test("a slow one-pixel pan across empty planar canvas does not demote Focus", async ({
        page,
    }) => {
        /*
         * The historical repro, isolated from the soak so that a failure names it exactly.
         *
         * This is the gesture from the report: in the planar view, a pan delivered as many
         * moves of about a pixel each, released over empty canvas. It used to end a Focus
         * session on Indra and show the whole projected corpus instead.
         */
        await enter(page, "2d");
        await startWatchdog(page, "2d");

        const canvas = page.locator(CANVAS["2d"]);
        for (let attempt = 0; attempt < 3; attempt += 1) {
            await slowPan(page, canvas);
            await hold(page, "2d", `after slow pan ${attempt}`);
        }

        const watched = await stopWatchdog(page);
        expect(watched.violations, "a slow pan moved the reader out of Focus").toEqual([]);
        await assertTraceIsClean(page, "the slow-pan repro");

        // And the subject itself is untouched, not merely the view.
        const entries = await readTrace(page);
        expect(
            entries.filter((entry) => entry.node !== INDRA_ID).map((entry) => entry.reason),
            "the slow pan changed which subject was being explored",
        ).toEqual([]);
    });

    /**
     * Taking hold of the subject, in three dimensions.
     *
     * ## What this is distinguishing between
     *
     * A press and a drag on this canvas can mean two entirely different things - move the
     * object, or move the camera - and both of them look like "the picture changed". The
     * discriminator used here is that the orb lands *under the pointer*: `dragNodeTo`
     * intersects the pointer ray with the slab's own plane, so a held orb is placed exactly
     * where the cursor is, while an orbit whose target is that same orb would leave it almost
     * still and swing everything else around it. Those two are not near each other, so this is
     * not a threshold that needs tuning.
     *
     * The camera is then read directly, because there is nothing else in the frame to read it
     * through. The first attempt at this test looked for nodes *outside* the curated set and
     * asserted their screen positions were unchanged, on the reasoning that only the camera can
     * move those. It found none: at the Focus framing the camera sits 900 units from the subject
     * and `screenPositionOf` returns null for anything whose normalised depth leaves [-1, 1], so
     * of 255 sampled candidates **zero** projected. The neighbourhood is the whole of what is on
     * screen, and every orb in it is expected to move - that is the physics - so no orb can
     * witness the camera.
     *
     * ## Why it reads the camera off the engine
     *
     * `camera` is a private field, reached for here because it is precisely the subject of the
     * claim: "a node drag that leaves the orbit live is not a node drag, it is both at once."
     * Measuring it through anything else would be measuring a proxy for the thing this test
     * exists to state. The read is loud if it breaks - an absent field fails by name rather than
     * producing a plausible wrong number - and the assertion is exact rather than tolerant,
     * because `OrbitControls` either advanced or it did not.
     */
    test("a drag that starts on the subject moves the subject, not the camera", async ({
        page,
    }) => {
        await enter(page, "3d");
        const canvas = page.locator(CANVAS["3d"]);

        /* The index is resolved from the artifact the page itself loaded rather than written
           down, because a rebuild renumbers it and a test that dragged the wrong node would
           report a physics problem as a gesture one. */
        const subject = await page.evaluate(async (id) => {
            const response = await fetch("/world/world.labels.json");
            const labels = (await response.json()) as { ids: string[] };
            return labels.ids.indexOf(id);
        }, INDRA_ID);
        expect(subject, `${INDRA_ID} is not in the artifact's label table`).toBeGreaterThanOrEqual(
            0,
        );

        /*
         * Waited until the projection repeats, not slept through.
         *
         * The entry flight is still moving the camera for a second or so after the panel
         * appears, and a displacement measured against a moving camera is a measurement of the
         * flight. Two identical readings is a statement about the camera having arrived.
         */
        let previous: string | null = null;
        await expect
            .poll(
                async () => {
                    const reading = await page.evaluate((node) => {
                        const engine = (window as unknown as { __vedaWorld?: Stage }).__vedaWorld;
                        const orb = engine?.orbGeometry([node])[0];
                        if (!orb || engine?.currentMode !== "FOCUS") return null;
                        return `${Math.round(orb.x)}:${Math.round(orb.y)}`;
                    }, subject);
                    const settled = reading !== null && reading === previous;
                    previous = reading;
                    return settled;
                },
                {
                    message: "the curated scene never stopped moving, so nothing could be grabbed",
                    timeout: SETTLE,
                    intervals: [300, 300, 300, 300, 500, 500, 500, 1_000, 1_000],
                },
            )
            .toBe(true);

        /** Where the camera is, to the digit. Rounded only so a float tail cannot read as motion. */
        const cameraSignature = () =>
            page.evaluate(() => {
                const engine = (window as unknown as { __vedaWorld?: Stage }).__vedaWorld;
                const camera = engine?.camera;
                if (!camera) return null;
                const { position: p, quaternion: q } = camera;
                return [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
                    .map((value) => value.toFixed(6))
                    .join(" ");
            });

        const cameraBefore = await cameraSignature();
        expect(
            cameraBefore,
            "the engine no longer exposes its camera, so this test cannot say whether it moved",
        ).not.toBeNull();

        const box = await boxOf(canvas, "the spatial canvas");
        const start = await page.evaluate((node) => {
            const engine = (window as unknown as { __vedaWorld?: Stage }).__vedaWorld;
            return engine!.orbGeometry([node])[0];
        }, subject);
        expect(
            start.radius,
            `the subject is drawn at ${start.radius.toFixed(1)} px, which is not a curated root, ` +
                "so this is not the scene the drag is supposed to act on",
        ).toBeGreaterThanOrEqual(16);

        const from = { x: box.x + start.x, y: box.y + start.y };
        const to = { x: from.x + 150, y: from.y - 90 };
        await page.mouse.move(from.x, from.y);
        await page.mouse.down();
        /* Stepped, because the classifier reads travel from the press and a single jump is one
           event. Thirty steps also carries the gesture well past the 4px mouse slop early, so
           most of the drag is spent held rather than deciding. */
        for (let step = 1; step <= 30; step += 1) {
            const t = step / 30;
            await page.mouse.move(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
        }

        expect(
            await canvas.getAttribute("data-gesture"),
            "the canvas does not consider this a drag, so nothing below is about a drag",
        ).toBe("dragging");

        const held = await page.evaluate((node) => {
            const engine = (window as unknown as { __vedaWorld?: Stage }).__vedaWorld;
            return engine!.orbGeometry([node])[0];
        }, subject);
        const cameraHeld = await cameraSignature();
        await page.mouse.up();

        /* The orb is where the cursor is. Two pixels covers the physics writing back one frame
           behind the pointer and the projection being rebuilt on read. */
        expect(
            Math.hypot(box.x + held.x - to.x, box.y + held.y - to.y),
            `the held orb is at ${held.x.toFixed(1)}, ${held.y.toFixed(1)} while the pointer is ` +
                `at ${(to.x - box.x).toFixed(1)}, ${(to.y - box.y).toFixed(1)}. A drag that starts ` +
                "on an orb has to move the orb; if the orb barely moved, the gesture orbited the " +
                "camera instead and offerGrab did not take.",
        ).toBeLessThan(2);

        /* And the camera did not come along. Exact, not tolerant: `OrbitControls` records a
           rotation start on the press - its own listener runs before the gesture module's,
           because it is constructed first - and the only question is whether it was allowed to
           advance. Any advance at all is the defect. */
        expect(
            cameraHeld,
            "the camera moved during a node drag, so the orbit was left live and the gesture " +
                "was both things at once. `offerGrab` disables the controls on the press for " +
                "exactly this reason; check that it still answers for this orb.",
        ).toBe(cameraBefore);

        /*
         * Let go, and the arrangement takes its subject back.
         *
         * The seats are anchors and `slack` bounds how far a body may leave one, so a released
         * orb returns towards where the layout put it. This is the observable difference between
         * a simulation and a drag that simply leaves things where they were dropped, and it is
         * also the reason the separation guarantee survives being pulled about.
         */
        await expect
            .poll(
                async () => {
                    const at = await page.evaluate((node) => {
                        const engine = (window as unknown as { __vedaWorld?: Stage }).__vedaWorld;
                        return engine!.orbGeometry([node])[0];
                    }, subject);
                    return Math.hypot(at.x - start.x, at.y - start.y);
                    /* Against `start`, the seat it was pulled away from - not against the drop
                       point, which would also be satisfied by nothing happening at all. */
                },
                {
                    message:
                        "the released orb never came back towards its seat, so the arrangement " +
                        "is holding whatever position the pointer left it in",
                    timeout: 15_000,
                    intervals: [400, 400, 600, 600, 1_000, 1_000, 2_000],
                },
            )
            .toBeLessThan(20);

        /* None of which is allowed to have moved the reader. */
        await hold(page, "3d", "after dragging the subject about");
        await assertTraceIsClean(page, "the node drag");
    });
});
