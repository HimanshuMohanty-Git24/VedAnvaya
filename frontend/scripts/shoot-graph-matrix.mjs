#!/usr/bin/env node
/**
 * shoot-graph-matrix.mjs - every graph surface, in every theme, at every width.
 *
 *   node scripts/shoot-graph-matrix.mjs --out <dir> [--base <url>] [--only <pattern>]
 *
 * Separate from `tests/visual-qa.mjs` on purpose. That harness sweeps the whole product at
 * three widths and reports overflow; this one takes a fixed, named matrix of graph states so a
 * review has the same twenty-one frames every time and a before/after pair is comparable frame
 * for frame. Mixing the two would mean either the product sweep grew a theme axis it does not
 * need, or the graph matrix inherited a width axis that says nothing about it.
 *
 * ## Why it refuses rather than warns
 *
 * A WebGL canvas that failed to draw screenshots as a clean rectangle of the page colour, and
 * the difference between that and a deliberately sparse composition is invisible in a
 * thumbnail. So every shot is measured: a canvas whose pixels have almost no spread in
 * luminance, or almost no distinct colours, is a failure and the process exits non-zero naming
 * it. The whole point of this phase is that the graph should have breathing room, which is
 * exactly the claim a blank canvas would counterfeit.
 *
 * The same discipline applies to the state each shot is supposed to be in: a frame captioned
 * FOCUS is asserted to be in Focus before the shutter, because this phase exists to fix a view
 * that silently reverted, and a screenshot of the wrong state is worse than a missing one.
 */
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
/* Reused rather than reimplemented. Node has no image decoder, and the motion harness already
   solved that by decoding in a blank browser tab; a second copy of the same thresholds is how
   two harnesses come to disagree about whether a frame is blank. */
import { imageStats, BLANK_STDDEV_MIN, BLANK_COLOURS_MIN } from "./capture-motion.mjs";

const args = process.argv.slice(2);
const arg = (name, fallback) => {
    const index = args.indexOf(`--${name}`);
    return index >= 0 ? args[index + 1] : fallback;
};

const BASE = arg("base", "http://127.0.0.1:3100");
const OUT = arg("out", ".tmp/graph-matrix");
const ONLY = arg("only", null);

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };

const INDRA = encodeURIComponent("VG:DEVATA:INDRAH");
/* 298 connections against Indra's 7,347, five node groups, and a river among them. The
   comparison case for whether the curation reads well at both ends rather than only at the
   extreme it was tuned on. */
const SARASVATI = encodeURIComponent("VG:DEVATA:SARASVATI");
const AGNI = encodeURIComponent("VG:DEVATA:AGNIH");

/** The canvas each state is judged on, and the selector that says it has drawn. */
const SPATIAL = {
    canvas: "canvas.va-world-canvas",
    ready: ".va-world[data-phase='ready']",
};
const PLANAR = {
    canvas: "canvas.va-planar-canvas",
    ready: "canvas.va-planar-canvas",
};

/**
 * The matrix.
 *
 * `expect` is asserted on the settled DOM before the shutter. `settle` is generous because the
 * world→focus transition is choreographed and a frame taken mid-move tells a reviewer nothing
 * about the composition they are being asked to judge.
 */
const SHOTS = [
    /* ---------------------------------------------------------------- home - */
    { name: "home-1440-light", url: "/", theme: "light", viewport: DESKTOP, canvas: "section.va-hero canvas", settle: 4000 },
    { name: "home-1440-dark", url: "/", theme: "dark", viewport: DESKTOP, canvas: "section.va-hero canvas", settle: 4000 },
    { name: "home-390", url: "/", theme: "light", viewport: PHONE, mobile: true, canvas: "section.va-hero canvas", settle: 4000 },

    /* --------------------------------------------------------------- world - */
    { name: "world-3d-light", url: "/graph?view=world&renderer=3d", theme: "light", viewport: DESKTOP, ...SPATIAL, expect: { view: "WORLD", renderer: "3d" }, settle: 5000 },
    { name: "world-3d-dark", url: "/graph?view=world&renderer=3d", theme: "dark", viewport: DESKTOP, ...SPATIAL, expect: { view: "WORLD", renderer: "3d" }, settle: 5000 },
    { name: "world-2d-light", url: "/graph?view=world&renderer=2d", theme: "light", viewport: DESKTOP, ...PLANAR, expect: { view: "WORLD", renderer: "2d" }, settle: 5000 },
    { name: "world-2d-dark", url: "/graph?view=world&renderer=2d", theme: "dark", viewport: DESKTOP, ...PLANAR, expect: { view: "WORLD", renderer: "2d" }, settle: 5000 },

    /* ------------------------------------------------- focus, the hard case - */
    { name: "focus-indra-3d-dark", url: `/graph?view=focus&renderer=3d&node=${INDRA}`, theme: "dark", viewport: DESKTOP, ...SPATIAL, expect: { view: "FOCUS", renderer: "3d" }, settle: 6000 },
    { name: "focus-indra-3d-light", url: `/graph?view=focus&renderer=3d&node=${INDRA}`, theme: "light", viewport: DESKTOP, ...SPATIAL, expect: { view: "FOCUS", renderer: "3d" }, settle: 6000 },
    { name: "focus-indra-2d-dark", url: `/graph?view=focus&renderer=2d&node=${INDRA}`, theme: "dark", viewport: DESKTOP, ...PLANAR, expect: { view: "FOCUS", renderer: "2d" }, settle: 6000 },
    { name: "focus-indra-2d-light", url: `/graph?view=focus&renderer=2d&node=${INDRA}`, theme: "light", viewport: DESKTOP, ...PLANAR, expect: { view: "FOCUS", renderer: "2d" }, settle: 6000 },

    /* --------------------------------------------- focus, an ordinary subject - */
    { name: "focus-lower-3d", url: `/graph?view=focus&renderer=3d&node=${SARASVATI}`, theme: "dark", viewport: DESKTOP, ...SPATIAL, expect: { view: "FOCUS", renderer: "3d" }, settle: 6000 },
    { name: "focus-lower-2d", url: `/graph?view=focus&renderer=2d&node=${SARASVATI}`, theme: "dark", viewport: DESKTOP, ...PLANAR, expect: { view: "FOCUS", renderer: "2d" }, settle: 6000 },

    /* -------------------------------------------------------- relationships - */
    {
        name: "relationship-3d",
        url: `/graph?view=focus&renderer=3d&node=${AGNI}`,
        theme: "dark",
        viewport: DESKTOP,
        ...SPATIAL,
        expect: { view: "FOCUS", renderer: "3d" },
        await: ".va-edge-label",
        settle: 6000,
    },
    {
        name: "relationship-2d",
        url: `/graph?view=focus&renderer=2d&node=${AGNI}`,
        theme: "dark",
        viewport: DESKTOP,
        ...PLANAR,
        expect: { view: "FOCUS", renderer: "2d" },
        await: ".va-edge-label",
        settle: 6000,
    },

    /* ----------------------------------------------------------------- path - */
    { name: "path-3d", url: `/graph?view=path&renderer=3d&from=${AGNI}&to=${INDRA}`, theme: "dark", viewport: DESKTOP, ...SPATIAL, expect: { view: "PATH", renderer: "3d" }, settle: 7000 },
    { name: "path-2d", url: `/graph?view=path&renderer=2d&from=${AGNI}&to=${INDRA}`, theme: "dark", viewport: DESKTOP, ...PLANAR, expect: { view: "PATH", renderer: "2d" }, settle: 7000 },

    /* --------------------------------------------------------------- mobile - */
    { name: "mobile-focus-3d", url: `/graph?view=focus&renderer=3d&node=${INDRA}`, theme: "dark", viewport: PHONE, mobile: true, ...SPATIAL, expect: { view: "FOCUS", renderer: "3d" }, settle: 6000 },
    { name: "mobile-focus-2d", url: `/graph?view=focus&renderer=2d&node=${INDRA}`, theme: "dark", viewport: PHONE, mobile: true, ...PLANAR, expect: { view: "FOCUS", renderer: "2d" }, settle: 6000 },
    {
        name: "mobile-relationship-sheet",
        url: `/graph?view=focus&renderer=3d&node=${AGNI}`,
        theme: "dark",
        viewport: PHONE,
        mobile: true,
        ...SPATIAL,
        expect: { view: "FOCUS", renderer: "3d" },
        await: ".va-edge-label",
        settle: 4000,
        /* Tap a relationship so the frame shows the inspector, which is the thing being
           reviewed. Tapping is the only way to reach it on a device with no hover. */
        tap: ".va-edge-label[data-pickable='true']",
        then: ".va-relationship",
        after: 2500,
    },
];

async function shoot(browser, analyzer, spec) {
    const context = await browser.newContext({
        viewport: spec.viewport,
        isMobile: spec.mobile ?? false,
        hasTouch: spec.mobile ?? false,
        deviceScaleFactor: 1,
        colorScheme: spec.theme,
    });
    const page = await context.newPage();
    const notes = [];
    try {
        await page.goto(`${BASE}${spec.url}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
        if (spec.ready) {
            await page.waitForSelector(spec.ready, { timeout: 60_000, state: "attached" });
        }
        if (spec.await) {
            await page.waitForSelector(spec.await, { timeout: 30_000 });
        }
        await page.waitForTimeout(spec.settle ?? 3000);

        if (spec.tap) {
            await page.locator(spec.tap).first().click({ timeout: 15_000 });
            if (spec.then) await page.waitForSelector(spec.then, { timeout: 15_000 });
            await page.waitForTimeout(spec.after ?? 2000);
        }

        /* Asserted on the settled DOM, before the shutter. A frame captioned FOCUS that is not
           in Focus is the defect this phase exists to close, photographed. */
        if (spec.expect) {
            const root = page.locator(".va-graph").first();
            for (const [attribute, want] of Object.entries(spec.expect)) {
                const got = await root.getAttribute(`data-${attribute}`);
                if (got !== want) {
                    throw new Error(
                        `state drifted before the shutter: data-${attribute} is "${got}", ` +
                            `expected "${want}"`,
                    );
                }
            }
            notes.push(Object.entries(spec.expect).map(([k, v]) => `${k}=${v}`).join(" "));
        }

        const file = path.join(OUT, `${spec.name}.png`);
        await page.screenshot({ path: file, fullPage: false });

        if (spec.canvas) {
            const canvas = page.locator(spec.canvas).first();
            if ((await canvas.count()) === 0) {
                throw new Error(`the canvas "${spec.canvas}" is not on the page`);
            }
            const shot = await canvas.screenshot();
            const stats = await imageStats(analyzer, shot);
            notes.push(`stddev ${stats.stdDev.toFixed(2)}, ${stats.colours} colours`);
            if (stats.stdDev < BLANK_STDDEV_MIN || stats.colours < BLANK_COLOURS_MIN) {
                throw new Error(
                    `the canvas looks blank - stddev ${stats.stdDev.toFixed(2)} ` +
                        `(min ${BLANK_STDDEV_MIN}), ${stats.colours} colours ` +
                        `(min ${BLANK_COLOURS_MIN}). A sparse composition and a canvas that ` +
                        `failed to draw are indistinguishable in a thumbnail, so this refuses ` +
                        `rather than warns.`,
                );
            }
        }
        return { name: spec.name, ok: true, notes };
    } catch (reason) {
        return {
            name: spec.name,
            ok: false,
            notes,
            error: reason instanceof Error ? reason.message : String(reason),
        };
    } finally {
        await context.close();
    }
}

const main = async () => {
    const wanted = SHOTS.filter((s) => !ONLY || s.name.includes(ONLY));
    if (wanted.length === 0) {
        console.error(`no shot matches "${ONLY}". Names: ${SHOTS.map((s) => s.name).join(", ")}`);
        process.exit(2);
    }
    await mkdir(OUT, { recursive: true });

    /*
     * The browser the rest of this suite has been proven against.
     *
     * Playwright's own Chromium download does not succeed in this environment, which
     * `playwright.config.ts` already works around by running the installed Edge. An explicit
     * path wins if one is given, because that is the motion harness's convention and a machine
     * with a real Chromium should use it; otherwise the channel is the thing that actually
     * launches here. Getting this wrong means a matrix that cannot be shot at all, which is a
     * worse failure than an unfamiliar browser.
     *
     * The GL flags are not optional. Without them the canvas comes back as a blank rectangle
     * under a software rasteriser - the exact failure the blankness check exists to catch, and
     * one that would then be attributed to the composition rather than to the launcher.
     */
    const explicit = process.env.CAPTURE_CHROMIUM;
    const browser = await chromium.launch({
        ...(explicit
            ? { executablePath: explicit }
            : { channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge" }),
        args: ["--use-gl=angle", "--use-angle=default", "--ignore-gpu-blocklist"],
    });

    /* A blank tab, only ever used to decode a PNG. It never loads the application. */
    const analyzerContext = await browser.newContext();
    const analyzer = await analyzerContext.newPage();
    await analyzer.setContent("<!doctype html><title>decode</title>");

    const results = [];
    try {
        for (const spec of wanted) {
            const result = await shoot(browser, analyzer, spec);
            results.push(result);
            const line = result.notes.length > 0 ? `  ${result.notes.join(" | ")}` : "";
            console.log(`${result.ok ? "ok  " : "FAIL"} ${result.name}${line}`);
            if (!result.ok) console.log(`     ${result.error}`);
        }
    } finally {
        await analyzerContext.close();
        await browser.close();
    }

    await writeFile(
        path.join(OUT, "manifest.json"),
        `${JSON.stringify({ base: BASE, at: new Date().toISOString(), results }, null, 2)}\n`,
        "utf8",
    );

    const failed = results.filter((r) => !r.ok);
    console.log(`\n${results.length - failed.length}/${results.length} frames captured into ${OUT}`);
    if (failed.length > 0) {
        console.error(`failed: ${failed.map((r) => r.name).join(", ")}`);
        process.exit(1);
    }
};

main().catch((reason) => {
    console.error(reason);
    process.exit(1);
});
