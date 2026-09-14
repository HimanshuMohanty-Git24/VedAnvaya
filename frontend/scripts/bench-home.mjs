#!/usr/bin/env node
/**
 * The homepage teaser's cost, on screen and off it.
 *
 * Phase 7F asked for three numbers that `bench-world.mjs` does not produce, because they are
 * about a page rather than about a renderer: the largest contentful paint, the main-thread time
 * the hero spends in a five-second window while visible, and the same figure with the hero
 * scrolled out of the viewport. The last is the one with a target attached - the previous
 * measurement was ~245 ms visible and ~122 ms offscreen per 5 s, and an offscreen renderer
 * costing half of a visible one is a renderer that was never actually stopped.
 *
 * ## How the main-thread time is taken
 *
 * From CDP `Performance.getMetrics`, sampled at both ends of a fixed wall-clock window.
 * `TaskDuration` is the browser's own total for main-thread tasks and includes the rAF callback,
 * the render, style and layout; `ScriptDuration` is the subset that is this application's own
 * JavaScript. Both are reported, because they answer different questions and the committed
 * baseline recorded both.
 *
 * ## Why there is a floor row, and why it is not zero
 *
 * `TaskDuration` counts the whole page. "Offscreen approximately zero" therefore has to be read
 * against what a window costs on a route that has no WebGL in it at all, which is what the
 * floor row is for. The committed baseline makes the same point and its floor came out at
 * ~105 ms per 5 s - but that instrument ran its own `requestAnimationFrame` loop in the page to
 * sample frame intervals, and reported 301 rAF callbacks per 5 s in *every* state including the
 * floor. That loop is most of its floor. This harness does not run one, so its floor is far
 * lower and its numbers are not comparable to the baseline's absolute values. They are
 * comparable to each other, which is what a before/after needs.
 *
 * ## Why three repetitions
 *
 * Because one is not a measurement here. The baseline's own visible figure ranged from 135.7 to
 * 255.1 ms across three runs - an 88% spread - so a single sample cannot distinguish a change in
 * the product from the machine having had a thought. Median, min and max are all reported.
 *
 * Usage:
 *   node scripts/bench-home.mjs [--base http://127.0.0.1:3100] [--json out.json] [--reps 3]
 */

import { chromium } from "@playwright/test";
import { writeFileSync } from "node:fs";

const args = new Map();
for (let i = 2; i < process.argv.length; i += 1) {
    const key = process.argv[i];
    if (key.startsWith("--")) {
        const next = process.argv[i + 1];
        const hasValue = next && !next.startsWith("--");
        args.set(key.slice(2), hasValue ? next : true);
        if (hasValue) i += 1;
    }
}

const BASE = args.get("base") ?? "http://127.0.0.1:3100";
const WINDOW_MS = Number(args.get("window") ?? 5000);
/* A real content route with no WebGL on it, for the floor row. The first version of this asked
   for `/sources`, which this product deliberately does not have, and measured a 404 page - a
   floor, but not the floor of "a page like the rest of the site". */
const FLOOR_PATH = args.get("floor") ?? "/vedas/rigveda";
const EXECUTABLE =
    args.get("chrome") ?? "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

const GPU_ARGS = ["--use-gl=angle", "--use-angle=default", "--ignore-gpu-blocklist"];

const REPS = Number(args.get("reps") ?? 3);

const browser = await chromium.launch({
    executablePath: EXECUTABLE,
    args: GPU_ARGS,
});

/** The cumulative CDP duration counters, in seconds, as one record. */
const COUNTERS = ["TaskDuration", "ScriptDuration", "LayoutDuration", "RecalcStyleDuration"];

async function durations(session) {
    const { metrics } = await session.send("Performance.getMetrics");
    const out = {};
    for (const name of COUNTERS) {
        const found = metrics.find((metric) => metric.name === name);
        out[name] = found ? found.value : Number.NaN;
    }
    return out;
}

const summarise = (values) => {
    const sorted = [...values].sort((a, b) => a - b);
    const median = sorted[sorted.length >> 1];
    return {
        reps: values.map((value) => Number(value.toFixed(2))),
        median: Number(median.toFixed(2)),
        min: Number(sorted[0].toFixed(2)),
        max: Number(sorted.at(-1).toFixed(2)),
    };
};

/** One fixed wall-clock window on one page: the duration counters spent, and frames drawn. */
async function measureWindow(page, session, hasHero) {
    const before = await durations(session);
    const beforeDraw = hasHero
        ? await page.evaluate(() => ({
              count: window.__vedaHero.drawCount(),
              paused: window.__vedaHero.paused(),
          }))
        : null;
    const began = Date.now();
    await page.waitForTimeout(WINDOW_MS);
    const elapsed = Date.now() - began;
    const after = await durations(session);
    const afterDraw = hasHero
        ? await page.evaluate(() => ({
              count: window.__vedaHero.drawCount(),
              paused: window.__vedaHero.paused(),
          }))
        : null;
    return {
        elapsedMs: elapsed,
        taskMs: (after.TaskDuration - before.TaskDuration) * 1000,
        scriptMs: (after.ScriptDuration - before.ScriptDuration) * 1000,
        layoutMs: (after.LayoutDuration - before.LayoutDuration) * 1000,
        styleMs: (after.RecalcStyleDuration - before.RecalcStyleDuration) * 1000,
        frames: afterDraw && beforeDraw ? afterDraw.count - beforeDraw.count : null,
        paused: afterDraw ? afterDraw.paused : null,
    };
}

/** Everything one repetition measures. A fresh context each time, so nothing is carried over. */
async function repetition() {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const session = await context.newCDPSession(page);
    await session.send("Performance.enable");

    const started = Date.now();
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => Boolean(window.__vedaHero), null, { timeout: 60_000 });
    await page.waitForFunction(() => window.__vedaHero.drawCount() > 2, null, { timeout: 60_000 });
    const readyMs = Date.now() - started;

    const paint = await page.evaluate(
        () =>
            new Promise((resolve) => {
                let lcp = 0;
                let element = "";
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        lcp = entry.startTime;
                        element = entry.element ? entry.element.tagName : element;
                    }
                }).observe({ type: "largest-contentful-paint", buffered: true });
                const fcp = performance
                    .getEntriesByType("paint")
                    .find((entry) => entry.name === "first-contentful-paint");
                let shift = 0;
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) shift += entry.value;
                    }
                }).observe({ type: "layout-shift", buffered: true });
                setTimeout(() => resolve({ lcp, element, fcp: fcp ? fcp.startTime : null, shift }), 900);
            }),
    );

    const glRenderer = await page.evaluate(() => {
        const canvas = document.querySelector("canvas");
        const gl = canvas?.getContext("webgl2") ?? canvas?.getContext("webgl");
        if (!gl) return "no webgl context";
        const info = gl.getExtension("WEBGL_debug_renderer_info");
        return info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : "unmasked info unavailable";
    });

    const visible = await measureWindow(page, session, true);

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    /* Waited for, not assumed: the pause is driven by an IntersectionObserver, and a window that
       began before it landed would be measuring the transition. */
    await page.waitForFunction(() => window.__vedaHero.paused() === true, null, { timeout: 10_000 });
    const offscreen = await measureWindow(page, session, true);

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForFunction(() => window.__vedaHero.paused() === false, null, {
        timeout: 10_000,
    });
    const resumed = await measureWindow(page, session, true);

    /* The floor: a route with no WebGL on it, through the same instrument. */
    const plain = await context.newPage();
    const plainSession = await context.newCDPSession(plain);
    await plainSession.send("Performance.enable");
    await plain.goto(`${BASE}${FLOOR_PATH}`, { waitUntil: "load" });
    const floor = await measureWindow(plain, plainSession, false);

    /* And with motion declined, where the field is required to be still - and, since Phase 7F,
       to stop being redrawn once it has settled. */
    const still = await context.newPage();
    await still.emulateMedia({ reducedMotion: "reduce" });
    await still.goto(BASE, { waitUntil: "domcontentloaded" });
    await still.waitForFunction(() => Boolean(window.__vedaHero), null, { timeout: 60_000 });
    await still.waitForFunction(() => window.__vedaHero.drawCount() > 2, null, { timeout: 60_000 });
    /* Past the idle grace period the loop keeps for the entry fit. */
    await still.waitForTimeout(1200);
    const reducedFirst = await still.evaluate(() => window.__vedaHero.drawCount());
    await still.waitForTimeout(3000);
    const reducedLast = await still.evaluate(() => window.__vedaHero.drawCount());
    const reducedPaused = await still.evaluate(() => window.__vedaHero.paused());

    await context.close();
    return {
        readyMs,
        lcpMs: paint.lcp,
        lcpElement: paint.element,
        fcpMs: paint.fcp,
        cls: paint.shift,
        glRenderer,
        visible,
        offscreen,
        resumed,
        floor,
        reducedIdleFrames: reducedLast - reducedFirst,
        reducedPaused,
    };
}

const runs = [];
for (let rep = 0; rep < REPS; rep += 1) runs.push(await repetition());

const pick = (path) => summarise(runs.map((run) => path(run)));
const report = {
    at: new Date().toISOString(),
    base: BASE,
    windowMs: WINDOW_MS,
    reps: REPS,
    executable: EXECUTABLE,
    floorPath: FLOOR_PATH,
    glRenderer: runs[0].glRenderer,
    lcpElement: runs[0].lcpElement,
    note:
        "TaskDuration counts the whole page. This harness runs no in-page rAF loop, unlike the " +
        "75e5efb baseline, so its floor is much lower and its absolute values are not " +
        "comparable to that document's. The rows here are comparable to each other.",
    readyMs: pick((run) => run.readyMs),
    lcpMs: pick((run) => run.lcpMs),
    fcpMs: pick((run) => run.fcpMs ?? Number.NaN),
    cls: pick((run) => run.cls),
    taskMsPer5s: {
        visible: pick((run) => run.visible.taskMs),
        offscreen: pick((run) => run.offscreen.taskMs),
        resumed: pick((run) => run.resumed.taskMs),
        staticRouteFloor: pick((run) => run.floor.taskMs),
    },
    scriptMsPer5s: {
        visible: pick((run) => run.visible.scriptMs),
        offscreen: pick((run) => run.offscreen.scriptMs),
        resumed: pick((run) => run.resumed.scriptMs),
        staticRouteFloor: pick((run) => run.floor.scriptMs),
    },
    framesPer5s: {
        visible: pick((run) => run.visible.frames),
        offscreen: pick((run) => run.offscreen.frames),
        resumed: pick((run) => run.resumed.frames),
    },
    offscreenPaused: runs.every((run) => run.offscreen.paused === true),
    reducedIdleFrames: pick((run) => run.reducedIdleFrames),
    reducedPaused: runs.every((run) => run.reducedPaused === true),
};

const row = (label, stat, unit = "ms") =>
    `  ${label.padEnd(26)} ${String(stat.median).padStart(8)} ${unit}   (${stat.min}-${stat.max} over ${REPS})`;

console.log(`\nhomepage teaser, ${BASE}, ${REPS} repetitions of a ${WINDOW_MS} ms window`);
console.log(`  gl renderer                ${report.glRenderer}`);
console.log(`  LCP element                ${report.lcpElement || "unknown"}`);
console.log(row("ready (handle + 2 frames)", report.readyMs));
console.log(row("LCP", report.lcpMs));
console.log(row("FCP", report.fcpMs));
console.log(row("CLS", report.cls, "  "));
console.log("  TaskDuration per 5 s");
console.log(row("    visible", report.taskMsPer5s.visible));
console.log(row("    offscreen", report.taskMsPer5s.offscreen));
console.log(row("    resumed", report.taskMsPer5s.resumed));
console.log(row(`    floor (${FLOOR_PATH})`, report.taskMsPer5s.staticRouteFloor));
console.log("  ScriptDuration per 5 s");
console.log(row("    visible", report.scriptMsPer5s.visible));
console.log(row("    offscreen", report.scriptMsPer5s.offscreen));
console.log(row(`    floor (${FLOOR_PATH})`, report.scriptMsPer5s.staticRouteFloor));
console.log("  frames drawn per 5 s");
console.log(row("    visible", report.framesPer5s.visible, "  "));
console.log(row("    offscreen", report.framesPer5s.offscreen, "  "));
console.log(`  offscreen reports paused   ${report.offscreenPaused}`);
console.log(row("reduced motion, 3 s idle", report.reducedIdleFrames, "fr"));
console.log(`  reduced motion parks       ${report.reducedPaused}`);

if (args.get("json")) {
    writeFileSync(args.get("json"), `${JSON.stringify({ ...report, runs }, null, 2)}\n`);
    console.log(`  written                    ${args.get("json")}`);
}

await browser.close();
