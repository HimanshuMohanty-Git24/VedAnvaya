#!/usr/bin/env node
// Real scroll/orbit QA of the shipped world, including composited screenshots.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const base = process.env.WORLD_QA_BASE ?? "http://127.0.0.1:3000";
const out = process.env.WORLD_QA_OUT ?? ".tmp/world-qa";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge",
    headless: true,
});
const report = [];
try {
    for (const theme of ["dark", "light"]) {
        const page = await browser.newPage({
            viewport: { width: 1440, height: 900 },
            colorScheme: theme,
            reducedMotion: "reduce",
        });
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        await page.goto(`${base}/graph?view=world&renderer=3d`);
        await page.waitForSelector(".va-world[data-phase='ready']", { timeout: 60_000 });
        const canvas = page.locator("canvas.va-world-canvas");
        const box = await canvas.boundingBox();
        await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.5);
        for (const [name, wheel] of [
            ["overview", 0],
            ["middle", -1200],
            ["close", -1800],
            ["detail", -1600],
        ]) {
                await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.5);
            if (wheel) await page.mouse.wheel(0, wheel);
            await page.waitForTimeout(1400);
            const metrics = await page.evaluate(() => {
                const engine = window.__vedaWorld;
                const nodes = Array.from(
                    { length: Math.ceil(engine.world.manifest.counts.nodes / 13) },
                    (_, i) => i * 13,
                ).filter((node) => node < engine.world.manifest.counts.nodes);
                const orbs = engine
                    .orbGeometry(nodes)
                    .filter((orb) => orb.depth > -1 && orb.depth < 1);
                const radii = orbs.map((orb) => orb.radius).sort((a, b) => a - b);
                return {
                    mode: engine.currentMode,
                    drawn: engine.renderer.info.render.points,
                    total: engine.world.manifest.counts.nodes,
                    distance: engine.camera.position.distanceTo(engine.controls.target),
                    maxRadius: Math.max(...radii),
                    medianRadius: radii[Math.floor(radii.length * 0.5)],
                    maxRecordRadius: Math.max(...orbs.filter((orb) => engine.world.nodeGroup[orb.node] >= 8).map((orb) => orb.radius)),
                    hud: document.querySelector(".va-world-stats")?.textContent,
                };
            });
            assert.equal(metrics.mode, "WORLD");
            assert.equal(metrics.drawn, metrics.total, "the world must retain the complete corpus");
            assert.ok(metrics.maxRadius <= 3.01, "world dots must stay distinct when zooming in");
            assert.ok(metrics.maxRecordRadius <= 1.26, "records must not cover subject colors at deep zoom");
            await page.mouse.move(1420, 30);
            await page.screenshot({ path: `${out}/${theme}-${name}.png` });
            report.push({ theme, name, ...metrics });
        }
        await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.5);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width * 0.78, box.y + box.height * 0.62, { steps: 12 });
        await page.mouse.up();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: `${out}/${theme}-orbit.png` });
        assert.deepEqual(errors, [], "world navigation must not raise browser exceptions");
        await page.close();
    }
    for (const [name, url, viewport] of [
        ["mobile-world", "/graph?view=world&renderer=3d", { width: 390, height: 844 }],
        ["planar-world", "/graph?view=world&renderer=2d", { width: 1440, height: 900 }],
        [
            "focus",
            "/graph?view=focus&renderer=3d&node=VG%3ADEVATA%3AINDRAH",
            { width: 1440, height: 900 },
        ],
    ]) {
        const page = await browser.newPage({
            viewport,
            colorScheme: "dark",
            reducedMotion: "reduce",
        });
        await page.goto(`${base}${url}`);
        await page.waitForSelector(
            name === "planar-world" ? "canvas.va-planar-canvas" : ".va-world[data-phase='ready']",
            { timeout: 60_000 },
        );
        await page.waitForTimeout(2400);
        await page.screenshot({ path: `${out}/${name}.png` });
        if (name === "mobile-world") {
            await page.setViewportSize({ width: 844, height: 390 });
            await page.waitForTimeout(1400);
            await page.screenshot({ path: `${out}/mobile-landscape.png` });
        }
        await page.close();
    }
    await writeFile(`${out}/report.json`, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
} finally {
    await browser.close();
}
