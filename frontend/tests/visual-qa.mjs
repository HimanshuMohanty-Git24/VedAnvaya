/**
 * Visual QA harness: renders key surfaces at three widths, saves screenshots for
 * inspection, and reports any element wider than its viewport.
 *
 *   node tests/visual-qa.mjs [--base http://127.0.0.1:3100] [--out .tmp/shots]
 *                            [--only substring] [--theme dark|light]
 *
 * `--theme` drives `prefers-color-scheme` rather than the theme toggle. The provider is
 * `defaultTheme: "system"` with `enableSystem`, so the emulated media query is what a first
 * visitor actually gets, and it needs no click and no localStorage seeding.
 */
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const args = process.argv.slice(2);
const arg = (name, fallback) => {
    const index = args.indexOf(`--${name}`);
    return index >= 0 ? args[index + 1] : fallback;
};

const BASE = arg("base", "http://127.0.0.1:3100");
const OUT = arg("out", ".tmp/shots");
const ONLY = arg("only", null);
const THEME = arg("theme", "light");

const VIEWPORTS = [
    { name: "desktop", width: 1440, height: 960 },
    { name: "tablet", width: 1024, height: 900 },
    { name: "mobile", width: 390, height: 844 },
];

const E = encodeURIComponent;
const SURFACES = [
    { name: "home", url: "/" },
    { name: "vedas", url: "/vedas" },
    { name: "veda-rigveda", url: "/vedas/rigveda" },
    { name: "veda-samaveda", url: "/vedas/samaveda" },
    { name: "veda-yajurveda", url: "/vedas/yajurveda" },
    { name: "veda-atharvaveda", url: "/vedas/atharvaveda" },
    { name: "reader", url: `/passage/${E("VG:RV:SAK:M01:S001:V001")}` },
    { name: "search", url: "/search?q=Indra" },
    { name: "devata-indra", url: `/devatas/${E("VG:DEVATA:INDRAH")}` },
    { name: "devata-agni", url: `/devatas/${E("VG:DEVATA:AGNIH")}` },
    { name: "devata-soma", url: `/devatas/${E("VG:DEVATA:SOMAH")}` },
    { name: "rishi", url: `/entities/rishi/${E("VG:RISHI:VAISVAMITRO-MADHUCCHANDAH")}` },
    { name: "rishi-family", url: `/entities/rishi_family/${E("VG:RISHI_FAMILY:VASISTHA")}` },
    { name: "ritual", url: `/rituals/${E("VG:CONCEPT:SOMA-PRESSING")}` },
    { name: "condition", url: `/entities/condition/${E("VG:CONCEPT:TAKMAN-FEVER")}` },
    { name: "atharvaveda", url: "/explore/atharvaveda" },
    { name: "connections", url: "/connections" },
    { name: "formulas", url: "/formulas" },
    { name: "graph", url: `/graph?node=${E("VG:DEVATA:INDRAH")}` },
    { name: "insights", url: "/insights" },
    { name: "limits", url: "/limits" },
    { name: "material-culture", url: "/material-culture" },
    { name: "explore", url: "/explore" },
    { name: "entities", url: "/entities" },
    { name: "lab", url: "/visualizations" },
    { name: "lab-four-corpora", url: "/visualizations/four-corpora" },
    { name: "lab-four-corpora-share", url: "/visualizations/four-corpora?scale=share" },
    { name: "lab-deities", url: "/visualizations/deities" },
    { name: "lab-transmission", url: "/visualizations/transmission" },
    { name: "lab-formulas", url: "/visualizations/formulas" },
    { name: "lab-human-concerns", url: "/visualizations/human-concerns" },
    { name: "lab-ritual", url: "/visualizations/ritual" },
    { name: "lab-material-culture", url: "/visualizations/material-culture" },
    { name: "about", url: "/about" },
    { name: "sources", url: "/sources" },
];

const findOverflow = () => {
    const docWidth = document.documentElement.clientWidth;
    const offenders = [];
    /*
     * A node inside a deliberate horizontal scroller is not an overflow.
     *
     * The cross-corpus matrix is 6 by 8 and cannot be read at 390px; it lives in an
     * `overflow-x: auto` region with a `min-width`, which is the correct answer for a wide
     * table on a phone. Without this check every cell of it is reported as a finding and the
     * one real page-level overflow is buried under forty-five false ones.
     */
    const inScroller = (node) => {
        for (let parent = node.parentElement; parent; parent = parent.parentElement) {
            const overflowX = getComputedStyle(parent).overflowX;
            if (overflowX === "auto" || overflowX === "scroll") return true;
        }
        return false;
    };
    for (const node of document.querySelectorAll("body *")) {
        const rect = node.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        if (inScroller(node)) continue;
        const right = rect.right + window.scrollX;
        if (right > docWidth + 1) {
            offenders.push({
                selector:
                    node.tagName.toLowerCase() +
                    (node.className && typeof node.className === "string"
                        ? "." + node.className.trim().split(/\s+/).slice(0, 2).join(".")
                        : ""),
                overflowPx: Math.round(right - docWidth),
                text: (node.textContent ?? "").trim().slice(0, 50),
            });
        }
    }
    // Report only the outermost offender of each kind.
    const seen = new Set();
    return offenders.filter((row) => {
        if (seen.has(row.selector)) return false;
        seen.add(row.selector);
        return true;
    });
};

const surfaces = ONLY ? SURFACES.filter((s) => s.name.includes(ONLY)) : SURFACES;
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge" });
const findings = [];

for (const viewport of VIEWPORTS) {
    const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1,
        colorScheme: THEME === "dark" ? "dark" : "light",
    });
    const page = await context.newPage();
    const dir = path.join(OUT, viewport.name);
    await mkdir(dir, { recursive: true });

    for (const surface of surfaces) {
        try {
            await page.goto(`${BASE}${surface.url}`, { waitUntil: "load", timeout: 45_000 });
            await page.waitForTimeout(surface.name === "graph" ? 3500 : 900);
            const overflow = await page.evaluate(findOverflow);
            const scrollWidth = await page.evaluate(
                () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
            );
            if (overflow.length || scrollWidth > 1) {
                findings.push({ viewport: viewport.name, surface: surface.name, scrollWidth, overflow });
            }
            await page.screenshot({
                path: path.join(dir, `${surface.name}.png`),
                fullPage: viewport.name !== "desktop",
            });
        } catch (error) {
            findings.push({
                viewport: viewport.name,
                surface: surface.name,
                error: String(error).slice(0, 200),
            });
        }
    }
    await context.close();
}

await browser.close();

if (findings.length === 0) {
    console.log(`No overflow or load failures at 1440, 1024 or 390 (${THEME}).`);
} else {
    console.log(JSON.stringify(findings, null, 1));
}
