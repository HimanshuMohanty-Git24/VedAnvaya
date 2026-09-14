#!/usr/bin/env node
/**
 * The world benchmark.
 *
 * Reproducible, and deliberately hostile to the number it is trying to produce. Three things
 * it does that a casual measurement does not:
 *
 *  - It times the interval between frames, not the duration of a `render` call. `render`
 *    returns when the commands are queued, so timing it measures neither the GPU nor vsync;
 *    an early version of the in-page HUD reported 1,667 fps while drawing 35,370 nodes in a
 *    software rasteriser, which is what that mistake looks like.
 *  - It records which renderer actually served the frames. Headless Chromium falls back to
 *    SwiftShader, a CPU rasteriser, unless a GPU is exposed; a number from SwiftShader is a
 *    floor and has to be labelled as one rather than quoted as a result.
 *  - It measures hover latency separately, because picking is the interaction most likely to
 *    scale badly with node count and the one a frame-rate figure hides completely.
 *
 * Usage:
 *   node scripts/bench-world.mjs                    # against the dev server
 *   node scripts/bench-world.mjs --gpu              # ask for real hardware
 *   node scripts/bench-world.mjs --json out.json
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
const BASE = args.get("base") ?? "http://localhost:3000";
const WANT_GPU = Boolean(args.get("gpu"));
const EXECUTABLE =
    args.get("chrome") ??
    "C:/Users/HKM49/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";

const SOFTWARE_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
const GPU_ARGS = ["--use-gl=angle", "--use-angle=default", "--ignore-gpu-blocklist"];

function stats(values) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const at = (p) => sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))];
    return {
        n: sorted.length,
        median: Number(at(0.5).toFixed(2)),
        p95: Number(at(0.95).toFixed(2)),
        max: Number(sorted[sorted.length - 1].toFixed(2)),
    };
}

const browser = await chromium.launch({
    executablePath: EXECUTABLE,
    args: WANT_GPU ? GPU_ARGS : SOFTWARE_ARGS,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on("pageerror", (e) => console.error("  PAGE ERROR:", e.message.slice(0, 200)));

const report = { base: BASE, requestedGpu: WANT_GPU, when: new Date().toISOString() };

console.log(`loading ${BASE}/graph/world ...`);
const navStart = Date.now();
await page.goto(`${BASE}/graph/world`, { waitUntil: "domcontentloaded" });
await page.waitForSelector('.va-world[data-phase="ready"]', { timeout: 120_000 });
report.readyMs = Date.now() - navStart;
console.log(`  ready in ${report.readyMs} ms`);

report.renderer = await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    const gl = canvas?.getContext("webgl2") ?? canvas?.getContext("webgl");
    if (!gl) return "no webgl";
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    return info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "unknown";
});
report.software = /swiftshader|software|llvmpipe/i.test(report.renderer);
console.log(`  renderer: ${report.renderer}`);
if (report.software) {
    console.log("  NOTE: software rasteriser. These figures are a floor, not a result.");
}

report.counts = await page.evaluate(async () => {
    const manifest = await (await fetch("/world/world.json")).json();
    return manifest.counts;
});

/* ------------------------------------------------------- frame interval - */

async function measureFrames(label, ms, drive) {
    if (drive) await drive();
    const samples = await page.evaluate(
        (duration) =>
            new Promise((resolve) => {
                const intervals = [];
                let last = 0;
                const until = performance.now() + duration;
                const tick = (now) => {
                    if (last) intervals.push(now - last);
                    last = now;
                    if (now < until) requestAnimationFrame(tick);
                    else resolve(intervals);
                };
                requestAnimationFrame(tick);
            }),
        ms,
    );
    const s = stats(samples);
    // The browser caps rAF at the display refresh, so an idle scene reads as exactly 60 fps
    // whatever the headroom. The useful figure here is the tail, not the median.
    console.log(
        `  ${label.padEnd(22)} median ${String(s.median).padStart(6)} ms   p95 ${String(s.p95).padStart(6)} ms   max ${String(s.max).padStart(7)} ms   (${Math.round(1000 / s.median)} fps)`,
    );
    return s;
}

console.log("\nframe interval");
report.frames = {};
report.frames.idle = await measureFrames("idle", 4000);

report.frames.orbiting = await measureFrames("orbiting", 4000, async () => {
    // A real drag, so OrbitControls damping and the pick-index invalidation are both in play.
    await page.mouse.move(720, 450);
    await page.mouse.down();
    void (async () => {
        for (let i = 0; i < 60; i += 1) {
            await page.mouse.move(720 + Math.sin(i / 6) * 260, 450 + Math.cos(i / 8) * 160);
        }
        await page.mouse.up();
    })();
});

/* --------------------------------------------------------------- hover - */

console.log("\ninteraction");
const hoverSamples = await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    const rect = canvas.getBoundingClientRect();
    const times = [];
    for (let i = 0; i < 120; i += 1) {
        const x = rect.left + 120 + ((i * 37) % (rect.width - 240));
        const y = rect.top + 90 + ((i * 53) % (rect.height - 180));
        const began = performance.now();
        canvas.dispatchEvent(
            new PointerEvent("pointermove", {
                clientX: x,
                clientY: y,
                bubbles: true,
                pointerId: 1,
            }),
        );
        times.push(performance.now() - began);
    }
    return times;
});
report.hoverMs = stats(hoverSamples);
console.log(
    `  hover                  median ${report.hoverMs.median} ms   p95 ${report.hoverMs.p95} ms   max ${report.hoverMs.max} ms`,
);

const selectMs = await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    const rect = canvas.getBoundingClientRect();
    const began = performance.now();
    canvas.dispatchEvent(
        new MouseEvent("click", {
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2,
            bubbles: true,
        }),
    );
    return performance.now() - began;
});
report.selectMs = Number(selectMs.toFixed(2));
console.log(`  select                 ${report.selectMs} ms`);

report.frames.afterSelect = await measureFrames("during camera flight", 2500);

/* ------------------------------------------------------ edge-count sweep - */

/*
 * The curve the world edge budget is chosen from.
 *
 * This scene is fill-rate bound, so the single variable that moves the frame interval is how
 * many translucent hairlines are rasterised. Everything else - node count, buffer sizes,
 * adjacency - is fixed. Sweeping the draw range and measuring gives the budget an evidential
 * basis instead of a guess, and it has to be rerun per machine because the answer is a
 * property of the GPU rather than of the graph.
 */
if (args.get("sweep")) {
    console.log("\nedge budget sweep (nothing selected)");
    report.sweep = [];
    // Clear the selection left by the interaction section above, and let the camera flight it
    // started finish: measuring a sweep while the camera is still moving measures the flight.
    await page.evaluate(() => window.__vedaWorld.select(null));
    await page.waitForTimeout(1500);
    for (const budget of [2000, 6000, 12000, 24000, 48000, 96000, 146899]) {
        await page.evaluate((n) => window.__vedaWorld?.setEdgeBudgetOverride(n), budget);
        await page.waitForTimeout(500);
        const s = await measureFrames(`  ${budget.toLocaleString()} edges`, 2600);
        report.sweep.push({ budget, ...s, fps: Math.round(1000 / s.median) });
    }
    await page.evaluate(() => window.__vedaWorld?.setEdgeBudgetOverride(null));
}

/* -------------------------------------------------------------- memory - */

report.memory = await page.evaluate(() => {
    const m = performance.memory;
    return m
        ? {
              usedMB: Number((m.usedJSHeapSize / 1048576).toFixed(1)),
              totalMB: Number((m.totalJSHeapSize / 1048576).toFixed(1)),
          }
        : null;
});
if (report.memory) {
    console.log(`\nmemory   JS heap used ${report.memory.usedMB} MB of ${report.memory.totalMB} MB`);
}

report.transfer = await page.evaluate(() =>
    performance
        .getEntriesByType("resource")
        .filter((e) => e.name.includes("/world/"))
        .map((e) => ({
            file: e.name.split("/").pop(),
            transferKB: Number((e.transferSize / 1024).toFixed(1)),
            ms: Number(e.duration.toFixed(1)),
        })),
);
console.log("\ntransfer");
for (const row of report.transfer) {
    console.log(`  ${row.file.padEnd(20)} ${String(row.transferKB).padStart(8)} KB  ${row.ms} ms`);
}

await browser.close();

if (args.get("json")) {
    writeFileSync(String(args.get("json")), JSON.stringify(report, null, 2));
    console.log(`\nwrote ${args.get("json")}`);
}
console.log("\ndone");
