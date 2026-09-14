#!/usr/bin/env node
/**
 * capture-motion.mjs — a reusable capture harness.
 *
 * Records a short video plus a final screenshot for each named scene, so a UI
 * change can be reviewed as motion rather than as stills. Output naming is
 * deterministic (`<scene-id>.webm` / `<scene-id>.png`), so a before/after
 * comparison is a matter of capturing into two sibling directories.
 *
 *   node scripts/capture-motion.mjs --out <dir> [--only <pattern>] [--base <url>]
 *
 *   --out <dir>      where to write videos, screenshots and manifest.json.
 *                    Never point this inside the repo; videos are large.
 *   --only <pattern> record just the scenes whose id matches. Substring, or a
 *                    glob with `*` (e.g. --only "world-*").
 *   --base <url>     app under capture. Default http://localhost:3000
 *   --list           print the scene ids and exit.
 *   --headed         show the browser (recording still works either way).
 *
 * Environment:
 *   CAPTURE_CHROMIUM  path to a Chromium executable. Playwright's own browser
 *                     download fails in this environment, so an explicit path
 *                     is the norm rather than the exception.
 *   CAPTURE_FFMPEG    path to ffmpeg, used only to read back video duration.
 *
 * Failure policy: every scene is attempted, but a scene that cannot reach its
 * wait-for selector, or whose canvas renders blank, is recorded as a failure
 * and the process exits non-zero naming each failed scene. A harness that
 * silently records blank videos is worse than no harness.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

const DEFAULT_CHROMIUM =
    "C:/Users/HKM49/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";

// The app is WebGL. Without these the canvas comes back as a blank rectangle
// under a software rasteriser, which is exactly the failure this harness is
// meant to catch rather than record.
const GL_ARGS = [
    "--use-gl=angle",
    "--use-angle=default",
    "--ignore-gpu-blocklist",
    // Space-separated extras, e.g. CAPTURE_CHROMIUM_ARGS="--disable-gpu --disable-webgl"
    // to deliberately reproduce a blank-canvas failure and check the guard bites.
    ...(process.env.CAPTURE_CHROMIUM_ARGS ?? "").split(" ").filter(Boolean),
];

/** A canvas that drew something has spread in its luminance and some colours. */
const BLANK_STDDEV_MIN = 1.5;
const BLANK_COLOURS_MIN = 12;

// ---------------------------------------------------------------------------
// Scenes
// ---------------------------------------------------------------------------

const INDRA = "VG%3ADEVATA%3AINDRAH";
/* The packed index of the same subject. Checked against the label table by
   tests/e2e/graph-palette.spec.ts, which fails by name if a rebuild renumbers it. */
const INDRA_INDEX = 22975;
const AGNI = "VG%3ADEVATA%3AAGNIH";
/* 298 connections against Indra's 7,347, and a genuinely mixed neighbourhood - five node
   groups including a river. The comparison case for whether the curation is sane at both
   ends, rather than only at the extreme it was tuned on. */
const SARASVATI = "VG%3ADEVATA%3ASARASVATI";

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };

/**
 * Selected structurally, not by class. The hero canvas was called
 * `va-constellation-canvas`, then `va-hero-world-canvas`, then
 * `va-world-preview-canvas` — all within one afternoon. A before/after pair is
 * only comparable if the scene survives the rename, and "the canvas in the
 * hero" is the part that is actually stable.
 */
const HERO_CANVAS = "section.va-hero canvas";

/**
 * Stage is mounted and the world engine has drawn at least one frame. The stats
 * readout only renders once phase is ready AND a frame has been measured, which
 * makes it the honest "something was drawn" gate — but it is `display: none`
 * under the narrow-viewport media query, so wait for it attached, not visible.
 */
const WORLD_READY = [
    { type: "waitFor", selector: ".va-world[data-phase='ready']", timeout: 60_000 },
    { type: "waitFor", selector: "p.va-world-stats", state: "attached", timeout: 30_000 },
];

/** @type {Array<import("./capture-motion.mjs").Scene>} */
const SCENES = [
    {
        id: "home-hero",
        url: "/",
        viewport: DESKTOP,
        canvas: HERO_CANVAS,
        actions: [
            { type: "waitFor", selector: HERO_CANVAS },
            { type: "wait", ms: 4000 },
        ],
    },
    {
        id: "home-hero-mobile",
        url: "/",
        viewport: MOBILE,
        mobile: true,
        canvas: HERO_CANVAS,
        actions: [
            { type: "waitFor", selector: HERO_CANVAS },
            { type: "wait", ms: 4000 },
        ],
    },
    /*
     * The front door, as three separate claims.
     *
     * Dragging the hero used to navigate, and so did the click that ended an orbit, because the
     * canvas acted on `click` and a mouse drag always ends in one. These three scenes are the
     * proof, and they are deliberately split: one clip showing a drag that stays put, one
     * showing a tap that selects without leaving, and one showing the only thing on the surface
     * that is allowed to navigate. A single clip covering all three would let the interesting
     * failure hide behind the successful part.
     */
    {
        id: "home-drag-stays",
        url: "/",
        viewport: DESKTOP,
        canvas: HERO_CANVAS,
        actions: [
            { type: "waitFor", selector: HERO_CANVAS },
            { type: "wait", ms: 1200 },
            { type: "drag", from: [0.3, 0.5], to: [0.72, 0.34], steps: 44, holdMs: 16 },
            { type: "wait", ms: 600 },
            // Released over empty space, which is where an orbit usually ends and which used
            // to be read as a request for the whole graph.
            { type: "drag", from: [0.5, 0.5], to: [0.12, 0.86], steps: 44, holdMs: 16 },
            { type: "assertUrl", matches: "^[^?]*/$" },
            { type: "assertAbsent", selector: "[data-testid='hero-selection']" },
            { type: "wait", ms: 1500 },
        ],
    },
    {
        id: "home-tap-selects",
        url: "/",
        viewport: DESKTOP,
        canvas: HERO_CANVAS,
        actions: [
            { type: "waitFor", selector: HERO_CANVAS },
            { type: "wait", ms: 1500 },
            {
                type: "clickUntil",
                selector: "[data-testid='hero-selection']",
                timeout: 2000,
                candidates: [
                    [0.5, 0.5],
                    [0.46, 0.48],
                    [0.54, 0.52],
                    [0.5, 0.44],
                    [0.42, 0.55],
                    [0.58, 0.45],
                    [0.48, 0.58],
                    [0.55, 0.4],
                ],
            },
            { type: "assertUrl", matches: "^[^?]*/$" },
            { type: "wait", ms: 2500 },
        ],
    },
    {
        id: "home-explicit-open",
        url: "/",
        viewport: DESKTOP,
        /*
         * The graph's canvas, not the hero's.
         *
         * This is the one scene that deliberately leaves the page it started on, and `canvas`
         * names what the *final* frame is checked against - so declaring the hero's canvas made
         * the scene fail for succeeding: by the time the shutter fell the hero had been unmounted
         * by the navigation the clip exists to record. Naming the graph canvas keeps the blank
         * check meaningful, and makes it a stronger claim than before: the explicit affordance
         * both navigates and arrives somewhere that draws.
         */
        canvas: "canvas.va-world-canvas",
        actions: [
            { type: "waitFor", selector: HERO_CANVAS },
            { type: "wait", ms: 1200 },
            { type: "clickSelector", selector: ".va-world-preview-link" },
            { type: "waitFor", selector: ".va-graph", timeout: 30_000 },
            { type: "assertUrl", matches: "/graph" },
            ...WORLD_READY,
            { type: "wait", ms: 3000 },
        ],
    },
    {
        id: "world-load",
        url: "/graph?view=world&renderer=3d",
        viewport: DESKTOP,
        actions: [...WORLD_READY, { type: "wait", ms: 6000 }],
    },
    {
        id: "world-rotate",
        url: "/graph?view=world&renderer=3d",
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "wait", ms: 1500 },
            { type: "drag", from: [0.35, 0.5], to: [0.68, 0.38], steps: 40, holdMs: 16 },
            { type: "wait", ms: 800 },
            { type: "drag", from: [0.65, 0.42], to: [0.4, 0.6], steps: 40, holdMs: 16 },
            { type: "wait", ms: 1500 },
        ],
    },
    {
        id: "world-zoom",
        url: "/graph?view=world&renderer=3d",
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "wait", ms: 1500 },
            { type: "wheel", at: [0.5, 0.5], dy: -220, times: 8, gapMs: 90 },
            { type: "wait", ms: 1200 },
            { type: "wheel", at: [0.5, 0.5], dy: 220, times: 8, gapMs: 90 },
            { type: "wait", ms: 1500 },
        ],
    },
    {
        id: "world-select",
        url: "/graph?view=world&renderer=3d",
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "wait", ms: 1500 },
            // The dense core sits near the middle; probe a short spiral of
            // offsets rather than trusting one pixel to land on a node.
            {
                type: "clickUntil",
                selector: "aside.va-world-panel",
                timeout: 2500,
                candidates: [
                    [0.5, 0.5],
                    [0.52, 0.52],
                    [0.48, 0.48],
                    [0.54, 0.47],
                    [0.46, 0.54],
                    [0.5, 0.45],
                    [0.55, 0.55],
                    [0.45, 0.5],
                ],
            },
            { type: "wait", ms: 3000 },
        ],
    },
    {
        id: "focus-3d",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 5000 },
        ],
    },
    {
        id: "focus-2d",
        url: `/graph?view=focus&renderer=2d&node=${INDRA}`,
        viewport: DESKTOP,
        canvas: "canvas.va-planar-canvas",
        actions: [
            { type: "waitFor", selector: ".va-graph[data-renderer='2d']", timeout: 60_000 },
            { type: "waitFor", selector: "canvas.va-planar-canvas", timeout: 60_000 },
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 5000 },
        ],
    },
    {
        id: "renderer-switch",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "wait", ms: 2000 },
            { type: "clickRenderer", renderer: "2D" },
            { type: "waitFor", selector: ".va-graph[data-renderer='2d']", timeout: 30_000 },
            { type: "waitFor", selector: "canvas.va-planar-canvas", timeout: 30_000 },
            { type: "wait", ms: 3000 },
            { type: "clickRenderer", renderer: "3D" },
            { type: "waitFor", selector: ".va-graph[data-renderer='3d']", timeout: 30_000 },
            { type: "wait", ms: 3000 },
        ],
    },
    {
        id: "path-trace",
        url: `/graph?view=path&renderer=3d&from=${AGNI}&to=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: ".va-graph[data-view='PATH']", timeout: 30_000 },
            { type: "wait", ms: 6000 },
        ],
    },
    /*
     * Thirty seconds in Focus, doing everything that used to break it.
     *
     * This is the release-blocking claim, and it is held rather than checked at the end: an
     * assertion taken once at the finish cannot tell "it never moved" from "it moved and moved
     * back". Orbiting, hovering, dwelling while the physics settles and raising the panel are
     * each one of the things the product owner named, and the trace assertion at the end says
     * not merely that the view is still Focus but that nothing ever asked it not to be.
     */
    {
        id: "focus-soak-3d",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 2000 },
            { type: "drag", from: [0.35, 0.5], to: [0.66, 0.4], steps: 40, holdMs: 16 },
            { type: "hover", at: [0.5, 0.46], ms: 1200 },
            { type: "drag", from: [0.66, 0.42], to: [0.38, 0.58], steps: 40, holdMs: 16 },
            { type: "hover", at: [0.44, 0.54], ms: 1200 },
            { type: "wheel", at: [0.5, 0.5], dy: -180, times: 5, gapMs: 110 },
            { type: "wheel", at: [0.5, 0.5], dy: 180, times: 5, gapMs: 110 },
            {
                type: "hold",
                ms: 30_000,
                everyMs: 750,
                url: `node=${INDRA}`,
                claims: [
                    { selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
                    { selector: ".va-graph", attribute: "data-renderer", equals: "3d" },
                ],
            },
            { type: "assertTrace" },
        ],
    },
    {
        id: "focus-soak-2d",
        url: `/graph?view=focus&renderer=2d&node=${INDRA}`,
        viewport: DESKTOP,
        canvas: "canvas.va-planar-canvas",
        actions: [
            { type: "waitFor", selector: ".va-graph[data-renderer='2d']", timeout: 60_000 },
            { type: "waitFor", selector: "canvas.va-planar-canvas", timeout: 60_000 },
            { type: "wait", ms: 2500 },
            /*
             * The historical reproduction, deliberately slow.
             *
             * The planar threshold measured travel between two pointer moves rather than from
             * the press, so a pan delivering a pixel at a time never latched: the release was
             * read as a click, the click hit empty canvas, and the subject was discarded. Many
             * small steps over a long hold is exactly that gesture.
             */
            { type: "drag", from: [0.2, 0.8], to: [0.28, 0.72], steps: 60, holdMs: 34 },
            { type: "wait", ms: 800 },
            {
                type: "hold",
                ms: 30_000,
                everyMs: 750,
                url: `node=${INDRA}`,
                claims: [
                    { selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
                    { selector: ".va-graph", attribute: "data-renderer", equals: "2d" },
                ],
            },
            { type: "assertTrace" },
        ],
    },
    /* Dragging a subject moves what it is attached to, and nothing else in the world. */
    {
        id: "focus-drag-3d",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 3000 },
            /* The drag starts at the centre of the canvas, which is where the Focus framing
               puts the subject's own orb - so this is the node drag, not an orbit, and the
               assertion after it is what says so. */
            { type: "markSubject", node: INDRA_INDEX },
            { type: "drag", from: [0.5, 0.5], to: [0.62, 0.42], steps: 36, holdMs: 22 },
            { type: "assertMoved", node: INDRA_INDEX, atLeastPx: 60 },
            { type: "wait", ms: 2500 },
            { type: "drag", from: [0.62, 0.42], to: [0.44, 0.56], steps: 36, holdMs: 22 },
            { type: "wait", ms: 3000 },
            { type: "assertAttribute", selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
        ],
    },
    {
        id: "focus-drag-2d",
        url: `/graph?view=focus&renderer=2d&node=${INDRA}`,
        viewport: DESKTOP,
        canvas: "canvas.va-planar-canvas",
        actions: [
            { type: "waitFor", selector: "canvas.va-planar-canvas", timeout: 60_000 },
            { type: "wait", ms: 3000 },
            { type: "drag", from: [0.5, 0.5], to: [0.64, 0.4], steps: 36, holdMs: 22 },
            { type: "wait", ms: 2500 },
            { type: "drag", from: [0.64, 0.4], to: [0.42, 0.58], steps: 36, holdMs: 22 },
            { type: "wait", ms: 3000 },
            { type: "assertAttribute", selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
        ],
    },
    /* What the lines say, and what clicking one of them explains. */
    {
        id: "focus-relationships",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: ".va-edge-label", timeout: 30_000 },
            { type: "wait", ms: 3000 },
            { type: "hover", at: [0.58, 0.44], ms: 1600 },
            { type: "hover", at: [0.42, 0.56], ms: 1600 },
            { type: "wait", ms: 2000 },
        ],
    },
    {
        id: "focus-edge-inspector",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: ".va-edge-label", timeout: 30_000 },
            { type: "wait", ms: 3000 },
            { type: "clickSelector", selector: ".va-edge-label[data-pickable='true']" },
            { type: "waitFor", selector: ".va-relationship", timeout: 15_000 },
            { type: "wait", ms: 4000 },
            { type: "key", key: "Escape", ms: 1200 },
            { type: "assertAttribute", selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
            { type: "wait", ms: 1200 },
        ],
    },
    /*
     * Leaving Focus, which only the reader may do.
     *
     * The clip is the counterpart of the soak: World returns, and it returns because the World
     * control was pressed. Both claims matter - a product that never returned would be as
     * broken as one that returned on its own.
     */
    {
        id: "focus-to-world",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 2500 },
            { type: "assertAttribute", selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
            { type: "clickSelector", selector: "nav.va-graph-modes button:has-text('World')" },
            { type: "waitFor", selector: ".va-graph[data-view='WORLD']", timeout: 15_000 },
            { type: "assertAbsent", selector: "aside.va-world-panel" },
            { type: "wait", ms: 3500 },
        ],
    },
    /* The same subject in both themes, so the palette is judged on the same composition. */
    {
        id: "focus-light",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        theme: "light",
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 4000 },
            { type: "drag", from: [0.4, 0.5], to: [0.6, 0.42], steps: 30, holdMs: 18 },
            { type: "wait", ms: 2500 },
        ],
    },
    {
        id: "focus-dark",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: DESKTOP,
        theme: "dark",
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 4000 },
            { type: "drag", from: [0.4, 0.5], to: [0.6, 0.42], steps: 30, holdMs: 18 },
            { type: "wait", ms: 2500 },
        ],
    },
    /* A subject with an ordinary number of connections. The median node has six. */
    {
        id: "focus-low-degree",
        url: `/graph?view=focus&renderer=3d&node=${SARASVATI}`,
        viewport: DESKTOP,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 4000 },
            { type: "drag", from: [0.4, 0.5], to: [0.6, 0.42], steps: 30, holdMs: 18 },
            { type: "wait", ms: 2500 },
        ],
    },
    {
        id: "focus-mobile",
        url: `/graph?view=focus&renderer=3d&node=${INDRA}`,
        viewport: MOBILE,
        mobile: true,
        actions: [
            ...WORLD_READY,
            { type: "waitFor", selector: "aside.va-world-panel", timeout: 30_000 },
            { type: "wait", ms: 2500 },
            { type: "drag", from: [0.3, 0.5], to: [0.7, 0.4], steps: 34, holdMs: 18, touch: true },
            { type: "wait", ms: 1500 },
            { type: "clickSelector", selector: ".va-world-sheet-handle" },
            { type: "wait", ms: 2500 },
            { type: "assertAttribute", selector: ".va-graph", attribute: "data-view", equals: "FOCUS" },
            { type: "wait", ms: 1500 },
        ],
    },
    {
        id: "world-dark",
        url: "/graph?view=world&renderer=3d",
        viewport: DESKTOP,
        theme: "dark",
        actions: [...WORLD_READY, { type: "wait", ms: 5000 }],
    },
    {
        id: "world-mobile",
        url: "/graph?view=world&renderer=3d",
        viewport: MOBILE,
        mobile: true,
        actions: [
            ...WORLD_READY,
            { type: "wait", ms: 1500 },
            { type: "drag", from: [0.3, 0.5], to: [0.7, 0.38], steps: 34, holdMs: 18, touch: true },
            { type: "wait", ms: 1000 },
            { type: "pinch", at: [0.5, 0.5], scale: 2.2, ms: 900 },
            { type: "wait", ms: 2500 },
        ],
    },
];

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
    const out = {
        out: path.join(os.tmpdir(), "vedagraph-captures"),
        base: "http://localhost:3000",
        only: null,
        list: false,
        headed: false,
    };
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        const next = () => {
            const v = argv[i + 1];
            if (v === undefined || v.startsWith("--")) die(`${arg} needs a value`);
            i += 1;
            return v;
        };
        if (arg === "--out") out.out = path.resolve(next());
        else if (arg === "--only") out.only = next();
        else if (arg === "--base") out.base = next().replace(/\/$/, "");
        else if (arg === "--list") out.list = true;
        else if (arg === "--headed") out.headed = true;
        else if (arg === "--help" || arg === "-h") {
            console.log(readHelp());
            process.exit(0);
        } else die(`unknown argument: ${arg}`);
    }
    return out;
}

function readHelp() {
    return [
        "capture-motion — record videos + screenshots of the app's interactions",
        "",
        "  node scripts/capture-motion.mjs --out <dir> [--only <pattern>] [--base <url>]",
        "",
        "  --out <dir>       output directory (keep it outside the repo)",
        "  --only <pattern>  scene id substring, or a glob with '*'",
        "  --base <url>      default http://localhost:3000",
        "  --list            print scene ids and exit",
        "  --headed          show the browser",
        "",
        `Scenes: ${SCENES.map((s) => s.id).join(", ")}`,
    ].join("\n");
}

function die(message) {
    console.error(`capture-motion: ${message}`);
    process.exit(2);
}

function matcher(pattern) {
    if (!pattern) return () => true;
    if (pattern.includes("*")) {
        const rx = new RegExp(
            `^${pattern
                .split("*")
                .map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
                .join(".*")}$`,
        );
        return (id) => rx.test(id);
    }
    return (id) => id.includes(pattern);
}

// ---------------------------------------------------------------------------
// Image analysis — is that canvas actually drawing anything?
// ---------------------------------------------------------------------------

/**
 * Decode a PNG inside the browser and reduce it to luminance statistics plus a
 * coarse signature grid. Node has no built-in image decoder, and the point of
 * this harness is to need no extra dependencies, so the browser does the work.
 */
async function imageStats(analyzer, png) {
    return analyzer.evaluate(async (b64) => {
        const img = new Image();
        img.src = `data:image/png;base64,${b64}`;
        await img.decode();
        const W = Math.max(2, Math.min(320, img.naturalWidth));
        const H = Math.max(2, Math.round((img.naturalHeight * W) / img.naturalWidth));
        const c = document.createElement("canvas");
        c.width = W;
        c.height = H;
        const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(img, 0, 0, W, H);
        const d = g.getImageData(0, 0, W, H).data;

        let sum = 0;
        let sum2 = 0;
        let n = 0;
        const seen = new Set();
        for (let i = 0; i < d.length; i += 4) {
            const l = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
            sum += l;
            sum2 += l * l;
            n += 1;
            // 5 bits per channel: tolerant of dithering, strict about flatness.
            seen.add(((d[i] >> 3) << 10) | ((d[i + 1] >> 3) << 5) | (d[i + 2] >> 3));
        }
        const mean = sum / n;
        const stdDev = Math.sqrt(Math.max(0, sum2 / n - mean * mean));

        // 24x24 mean-luminance grid, used to tell motion from a frozen frame.
        const GW = 24;
        const GH = 24;
        const sig = new Array(GW * GH).fill(0);
        const cnt = new Array(GW * GH).fill(0);
        for (let y = 0; y < H; y += 1) {
            for (let x = 0; x < W; x += 1) {
                const i = (y * W + x) * 4;
                const cell =
                    Math.min(GH - 1, Math.floor((y / H) * GH)) * GW +
                    Math.min(GW - 1, Math.floor((x / W) * GW));
                sig[cell] += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
                cnt[cell] += 1;
            }
        }
        for (let i = 0; i < sig.length; i += 1) sig[i] = cnt[i] ? sig[i] / cnt[i] : 0;

        return {
            width: img.naturalWidth,
            height: img.naturalHeight,
            mean: Number(mean.toFixed(2)),
            stdDev: Number(stdDev.toFixed(3)),
            colours: seen.size,
            sig,
        };
    }, png.toString("base64"));
}

/** Mean absolute difference between two signature grids, as 0-100. */
function signatureDelta(a, b) {
    if (!a || !b || a.length !== b.length) return null;
    let total = 0;
    for (let i = 0; i < a.length; i += 1) total += Math.abs(a[i] - b[i]);
    return Number(((total / a.length / 255) * 100).toFixed(3));
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function canvasBox(page, selector, sceneId) {
    const box = await page.locator(selector).first().boundingBox();
    if (!box) throw new Error(`[${sceneId}] canvas "${selector}" has no layout box`);
    return box;
}

const at = (box, [fx, fy]) => ({ x: box.x + box.width * fx, y: box.y + box.height * fy });

async function smoothDrag(page, box, action) {
    const from = at(box, action.from);
    const to = at(box, action.to);
    const steps = action.steps ?? 30;
    const hold = action.holdMs ?? 16;

    if (action.touch) {
        const cdp = page.__cdp;
        const touch = (type, x, y) =>
            cdp.send("Input.dispatchTouchEvent", {
                type,
                touchPoints: type === "touchEnd" ? [] : [{ x: Math.round(x), y: Math.round(y) }],
            });
        await touch("touchStart", from.x, from.y);
        for (let i = 1; i <= steps; i += 1) {
            const t = i / steps;
            await touch("touchMove", from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
            await page.waitForTimeout(hold);
        }
        await touch("touchEnd", to.x, to.y);
        return;
    }

    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    for (let i = 1; i <= steps; i += 1) {
        const t = i / steps;
        await page.mouse.move(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
        await page.waitForTimeout(hold);
    }
    await page.mouse.up();
}

async function pinch(page, box, action) {
    const p = at(box, action.at);
    try {
        await page.__cdp.send("Input.synthesizePinchGesture", {
            x: Math.round(p.x),
            y: Math.round(p.y),
            scaleFactor: action.scale ?? 2,
            relativeSpeed: 500,
            gestureSourceType: "touch",
        });
        return "synthesizePinchGesture";
    } catch {
        // Some Chromium builds refuse the synthesized gesture; a two-finger
        // spread over the raw touch protocol gets the same pixels moving.
        const cdp = page.__cdp;
        const span = Math.min(box.width, box.height) * 0.15;
        const steps = 20;
        const pts = (d) => [
            { x: Math.round(p.x - d), y: Math.round(p.y) },
            { x: Math.round(p.x + d), y: Math.round(p.y) },
        ];
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: pts(span) });
        for (let i = 1; i <= steps; i += 1) {
            await cdp.send("Input.dispatchTouchEvent", {
                type: "touchMove",
                touchPoints: pts(span * (1 + (i / steps) * ((action.scale ?? 2) - 1))),
            });
            await page.waitForTimeout((action.ms ?? 800) / steps);
        }
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
        return "dispatchTouchEvent-fallback";
    }
}

async function runAction(page, scene, action, notes, state) {
    const box = async () => canvasBox(page, scene.canvas ?? "canvas.va-world-canvas", scene.id);

    switch (action.type) {
        case "wait":
            await page.waitForTimeout(action.ms);
            return;

        case "waitFor":
            try {
                await page.waitForSelector(action.selector, {
                    state: action.state ?? "visible",
                    timeout: action.timeout ?? 30_000,
                });
            } catch {
                throw new Error(
                    `[${scene.id}] selector never appeared: "${action.selector}" ` +
                        `(waited ${action.timeout ?? 30_000}ms on ${scene.url})`,
                );
            }
            return;

        case "click": {
            const p = at(await box(), action.at);
            await page.mouse.click(p.x, p.y);
            return;
        }

        case "clickUntil": {
            const b = await box();
            for (const candidate of action.candidates) {
                const p = at(b, candidate);
                await page.mouse.click(p.x, p.y);
                try {
                    await page.waitForSelector(action.selector, {
                        timeout: action.timeout ?? 2500,
                    });
                    notes.push(`selected at [${candidate.join(", ")}]`);
                    return;
                } catch {
                    /* try the next offset */
                }
            }
            throw new Error(
                `[${scene.id}] clicked ${action.candidates.length} points on the canvas and ` +
                    `"${action.selector}" never appeared`,
            );
        }

        case "clickRenderer": {
            const nav = page.locator("nav.va-graph-modes.is-renderer");
            const button = nav.getByRole("button", { name: action.renderer, exact: true });
            try {
                await button.click({ timeout: 15_000 });
            } catch {
                throw new Error(
                    `[${scene.id}] could not click the "${action.renderer}" renderer control`,
                );
            }
            return;
        }

        case "clickSelector":
            try {
                await page
                    .locator(action.selector)
                    .first()
                    .click({ timeout: action.timeout ?? 15_000 });
            } catch {
                throw new Error(`[${scene.id}] could not click "${action.selector}"`);
            }
            return;

        case "hover": {
            const p = at(await box(), action.at);
            await page.mouse.move(p.x, p.y, { steps: 20 });
            await page.waitForTimeout(action.ms ?? 600);
            return;
        }

        case "drag":
            await smoothDrag(page, await box(), action);
            return;

        case "wheel": {
            const p = at(await box(), action.at);
            await page.mouse.move(p.x, p.y);
            for (let i = 0; i < (action.times ?? 5); i += 1) {
                await page.mouse.wheel(action.dx ?? 0, action.dy ?? -120);
                await page.waitForTimeout(action.gapMs ?? 90);
            }
            return;
        }

        case "pinch":
            notes.push(`pinch via ${await pinch(page, await box(), action)}`);
            return;

        case "key":
            await page.keyboard.press(action.key);
            await page.waitForTimeout(action.ms ?? 400);
            return;

        /*
         * The assertions below are what make a clip evidence rather than footage.
         *
         * A recording of the Focus view not resetting looks exactly like a recording of the
         * Focus view resetting if nobody watches the right second of it. So the claim is made
         * inside the capture, the scene fails loudly when it is false, and the reviewer watches
         * the clip to judge whether it is *beautiful* rather than to check whether it is broken.
         */
        case "assertAttribute": {
            const actual = await page
                .locator(action.selector)
                .first()
                .getAttribute(action.attribute);
            if (actual !== action.equals) {
                throw new Error(
                    `[${scene.id}] expected ${action.selector}[${action.attribute}] to be ` +
                        `"${action.equals}" but found "${actual}"`,
                );
            }
            notes.push(`${action.attribute}="${actual}"`);
            return;
        }

        case "assertUrl": {
            const url = page.url();
            if (!new RegExp(action.matches).test(url)) {
                throw new Error(
                    `[${scene.id}] expected the address to match /${action.matches}/ ` +
                        `but it is ${url}`,
                );
            }
            notes.push(`url ok: ${url.replace(/^https?:\/\/[^/]+/, "")}`);
            return;
        }

        case "assertAbsent": {
            const count = await page.locator(action.selector).count();
            if (count !== 0) {
                throw new Error(
                    `[${scene.id}] expected no "${action.selector}" but found ${count}`,
                );
            }
            return;
        }

        /*
         * Remember where the subject is, so a later `assertMoved` has something to compare to.
         *
         * A drag clip is the one kind of scene whose whole content is a change, and the two
         * changes it could be recording - the object moving, or the camera swinging around it -
         * look similar in a thumbnail and completely different to a reader. The harness's blank
         * canvas guard cannot tell them apart, so the scene says which one it means.
         */
        case "markSubject": {
            state.subject = await page.evaluate((node) => {
                const engine = window.__vedaWorld;
                const orb = engine?.orbGeometry?.([node])?.[0];
                return orb ? { x: orb.x, y: orb.y } : null;
            }, action.node);
            if (!state.subject) {
                throw new Error(
                    `[${scene.id}] the engine could not place node ${action.node}, so this ` +
                        "scene cannot state what its drag moved",
                );
            }
            return;
        }

        case "assertMoved": {
            const now = await page.evaluate((node) => {
                const engine = window.__vedaWorld;
                const orb = engine?.orbGeometry?.([node])?.[0];
                return orb ? { x: orb.x, y: orb.y } : null;
            }, action.node);
            if (!now || !state.subject) {
                throw new Error(`[${scene.id}] nothing to compare: the subject was not placed`);
            }
            const moved = Math.hypot(now.x - state.subject.x, now.y - state.subject.y);
            if (moved < (action.atLeastPx ?? 40)) {
                throw new Error(
                    `[${scene.id}] node ${action.node} moved ${moved.toFixed(1)} px, under the ` +
                        `${action.atLeastPx ?? 40} px this scene claims to show. The drag orbited ` +
                        "the camera instead of taking hold of the orb, so the clip is of the " +
                        "wrong gesture.",
                );
            }
            return;
        }

        /*
         * Hold a claim for a while, checking it throughout rather than at the end.
         *
         * The reported defect was a view that reverted at some unpredictable moment during an
         * exploration. An assertion taken once at the finish cannot distinguish "it never moved"
         * from "it moved and moved back", so this samples on an interval and names the elapsed
         * time when it breaks. That is the difference between a soak test and a long wait.
         */
        case "hold": {
            const every = action.everyMs ?? 500;
            const began = Date.now();
            while (Date.now() - began < action.ms) {
                for (const claim of action.claims) {
                    const actual = await page
                        .locator(claim.selector)
                        .first()
                        .getAttribute(claim.attribute);
                    if (actual !== claim.equals) {
                        throw new Error(
                            `[${scene.id}] after ${Date.now() - began}ms of holding, ` +
                                `${claim.selector}[${claim.attribute}] became "${actual}" ` +
                                `when it should have stayed "${claim.equals}"`,
                        );
                    }
                }
                if (action.url && !new RegExp(action.url).test(page.url())) {
                    throw new Error(
                        `[${scene.id}] after ${Date.now() - began}ms the address left ` +
                            `/${action.url}/ and became ${page.url()}`,
                    );
                }
                await page.waitForTimeout(every);
            }
            notes.push(`held every claim for ${action.ms}ms`);
            return;
        }

        /*
         * The semantic-state trace, read back out of the page.
         *
         * `useGraphState` keeps a bounded ring of every transition with the cause that asked for
         * it, precisely so this claim can be exact. A transition into WORLD whose reason is not
         * the reader is the defect, by definition, and so is any refusal - a refusal means a
         * caller exists that should not.
         */
        case "assertTrace": {
            const trace = await page.evaluate(() => window.__vedaGraphTrace ?? []);
            const refused = trace.filter((entry) => entry.refused);
            const unasked = trace.filter(
                (entry) =>
                    entry.to === "WORLD" &&
                    entry.from !== "WORLD" &&
                    !String(entry.reason).startsWith("reader:"),
            );
            if (refused.length > 0 || unasked.length > 0) {
                throw new Error(
                    `[${scene.id}] the state trace is not clean. ` +
                        `${refused.length} refused transition(s): ` +
                        `${JSON.stringify(refused)}. ` +
                        `${unasked.length} unasked return(s) to World: ` +
                        `${JSON.stringify(unasked)}`,
                );
            }
            notes.push(`${trace.length} transitions, all accounted for`);
            return;
        }

        default:
            throw new Error(`[${scene.id}] unknown action type "${action.type}"`);
    }
}

// ---------------------------------------------------------------------------
// Video duration, read back with the ffmpeg Playwright already ships
// ---------------------------------------------------------------------------

function findFfmpeg() {
    if (process.env.CAPTURE_FFMPEG) return process.env.CAPTURE_FFMPEG;
    const root = path.join(
        process.env.LOCALAPPDATA ?? path.join(os.homedir(), "AppData", "Local"),
        "ms-playwright",
    );
    if (!fs.existsSync(root)) return null;
    for (const dir of fs.readdirSync(root)) {
        if (!dir.startsWith("ffmpeg-")) continue;
        for (const name of ["ffmpeg-win64.exe", "ffmpeg-mac", "ffmpeg-linux", "ffmpeg.exe"]) {
            const p = path.join(root, dir, name);
            if (fs.existsSync(p)) return p;
        }
    }
    return null;
}

function videoDuration(ffmpeg, file) {
    if (!ffmpeg) return null;
    const r = spawnSync(ffmpeg, ["-hide_banner", "-i", file], { encoding: "utf8" });
    const text = `${r.stderr ?? ""}${r.stdout ?? ""}`;
    const m = /Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)/.exec(text);
    if (!m) return null;
    const secs = Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
    return Number.isFinite(secs) && secs > 0 ? Number(secs.toFixed(2)) : null;
}

// ---------------------------------------------------------------------------
// One scene
// ---------------------------------------------------------------------------

async function captureScene(browser, analyzer, scene, opts, ffmpeg) {
    const videoPath = path.join(opts.out, `${scene.id}.webm`);
    const shotPath = path.join(opts.out, `${scene.id}.png`);
    const canvasSel = scene.canvas ?? "canvas.va-world-canvas";
    const notes = [];
    /* Carried across the actions of one scene, so a claim can be made about a change
       rather than only about an end state. See `markSubject`. */
    const state = {};
    const consoleErrors = [];

    const record = {
        id: scene.id,
        status: "fail",
        url: `${opts.base}${scene.url}`,
        viewport: `${scene.viewport.width}x${scene.viewport.height}`,
        theme: scene.theme ?? "default (light)",
        touch: Boolean(scene.mobile),
        video: `${scene.id}.webm`,
        videoBytes: 0,
        videoDurationSec: null,
        screenshot: `${scene.id}.png`,
        durationMs: 0,
        canvas: canvasSel,
        blankCheck: null,
        motionDelta: null,
        notes,
        consoleErrors,
        error: null,
    };

    fs.rmSync(videoPath, { force: true });
    fs.rmSync(shotPath, { force: true });

    const context = await browser.newContext({
        viewport: scene.viewport,
        deviceScaleFactor: scene.mobile ? 2 : 1,
        isMobile: Boolean(scene.mobile),
        hasTouch: Boolean(scene.mobile),
        colorScheme: scene.theme === "dark" ? "dark" : "light",
        recordVideo: { dir: opts.out, size: scene.viewport },
    });

    if (scene.theme) {
        // next-themes reads localStorage before first paint; writing the class
        // as well keeps the very first recorded frames from flashing the wrong
        // theme. The app is never modified — this is all in the page context.
        await context.addInitScript((theme) => {
            try {
                window.localStorage.setItem("theme", theme);
            } catch {
                /* storage may be blocked; the class below still applies */
            }
            const apply = () => {
                const el = document.documentElement;
                el.classList.remove("light", "dark");
                el.classList.add(theme);
                el.style.colorScheme = theme;
            };
            apply();
            document.addEventListener("DOMContentLoaded", apply);
        }, scene.theme);
    }

    const page = await context.newPage();
    page.__cdp = await context.newCDPSession(page);
    page.on("console", (m) => {
        if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200));
    });
    page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 200)}`));

    const started = Date.now();
    /** Signatures of the settled frame and a mid-scene frame, for motionDelta. */
    const sigs = [];

    try {
        await page.goto(`${opts.base}${scene.url}`, {
            waitUntil: "domcontentloaded",
            timeout: 60_000,
        });

        const sample = async () => {
            try {
                const shot = await page.locator(canvasSel).first().screenshot({ timeout: 15_000 });
                sigs.push((await imageStats(analyzer, shot)).sig);
            } catch {
                /* non-fatal: motionDelta simply degrades */
            }
        };
        // Two reference frames: the moment the scene has settled but has not yet
        // moved, and the midpoint. A scene that ends where it started (zoom in,
        // zoom out) would otherwise report zero motion despite a lively video.
        const firstMove = scene.actions.findIndex((a) => a.type !== "waitFor");
        const midpoint = Math.floor((firstMove + scene.actions.length) / 2);
        for (const [i, action] of scene.actions.entries()) {
            if (i === firstMove || i === midpoint) await sample();
            await runAction(page, scene, action, notes, state);
        }

        if (scene.theme) {
            const applied = await page.evaluate(() =>
                document.documentElement.classList.contains("dark") ? "dark" : "light",
            );
            if (applied !== scene.theme) {
                throw new Error(
                    `[${scene.id}] theme "${scene.theme}" was requested but <html> resolved to "${applied}"`,
                );
            }
        }

        // The blank check measures the canvas alone. A page full of chrome text
        // around an empty rectangle must not be allowed to pass.
        let canvasShot;
        try {
            canvasShot = await page.locator(canvasSel).first().screenshot({ timeout: 20_000 });
        } catch {
            throw new Error(`[${scene.id}] could not screenshot the canvas "${canvasSel}"`);
        }
        const stats = await imageStats(analyzer, canvasShot);
        const blank = stats.stdDev < BLANK_STDDEV_MIN || stats.colours < BLANK_COLOURS_MIN;
        record.blankCheck = {
            selector: canvasSel,
            size: `${stats.width}x${stats.height}`,
            meanLuminance: stats.mean,
            stdDev: stats.stdDev,
            distinctColours: stats.colours,
            thresholds: { stdDev: BLANK_STDDEV_MIN, distinctColours: BLANK_COLOURS_MIN },
            passed: !blank,
        };
        // The largest change between any two sampled frames: the frame that
        // moved most, not merely the difference between first and last.
        const frames = [...sigs, stats.sig];
        let peak = null;
        for (let a = 0; a < frames.length; a += 1) {
            for (let b = a + 1; b < frames.length; b += 1) {
                const d = signatureDelta(frames[a], frames[b]);
                if (d !== null && (peak === null || d > peak)) peak = d;
            }
        }
        record.motionDelta = peak;

        await page.screenshot({ path: shotPath });

        if (blank) {
            throw new Error(
                `[${scene.id}] canvas "${canvasSel}" rendered blank ` +
                    `(stdDev ${stats.stdDev} < ${BLANK_STDDEV_MIN}, ` +
                    `${stats.colours} distinct colours < ${BLANK_COLOURS_MIN}). ` +
                    `Check the GL flags and the executable path.`,
            );
        }

        record.status = "pass";
    } catch (err) {
        record.error = err instanceof Error ? err.message : String(err);
        // Still save whatever is on screen — a failed scene's last frame is
        // usually the fastest way to see why it failed.
        try {
            if (!fs.existsSync(shotPath)) await page.screenshot({ path: shotPath });
        } catch {
            /* the page may be gone */
        }
    } finally {
        record.durationMs = Date.now() - started;
        const video = page.video();
        await context.close();
        if (video) {
            try {
                await video.saveAs(videoPath);
                await video.delete();
            } catch (err) {
                record.notes.push(`video save failed: ${String(err).slice(0, 120)}`);
            }
        }
    }

    if (fs.existsSync(videoPath)) {
        record.videoBytes = fs.statSync(videoPath).size;
        record.videoDurationSec = videoDuration(ffmpeg, videoPath);
        if (record.videoBytes === 0) {
            record.status = "fail";
            record.error = record.error ?? `[${scene.id}] video file is empty`;
        }
    } else {
        record.video = null;
        record.status = "fail";
        record.error = record.error ?? `[${scene.id}] no video was produced`;
    }

    return record;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
    const opts = parseArgs(process.argv.slice(2));

    if (opts.list) {
        for (const s of SCENES) console.log(s.id);
        process.exit(0);
    }

    const wanted = SCENES.filter((s) => matcher(opts.only)(s.id));
    if (wanted.length === 0) die(`--only "${opts.only}" matched no scenes. Try --list.`);

    const executablePath = process.env.CAPTURE_CHROMIUM ?? DEFAULT_CHROMIUM;
    if (!fs.existsSync(executablePath)) {
        die(
            `Chromium not found at ${executablePath}. ` +
                `Set CAPTURE_CHROMIUM to a Chromium/Edge executable.`,
        );
    }

    // A reachable app is a precondition, not a per-scene failure.
    try {
        const res = await fetch(opts.base, { signal: AbortSignal.timeout(10_000) });
        if (!res.ok) die(`${opts.base} answered ${res.status}. Is the dev server healthy?`);
    } catch (err) {
        die(`${opts.base} is not reachable (${String(err).slice(0, 120)}). Start the dev server.`);
    }

    fs.mkdirSync(opts.out, { recursive: true });
    const ffmpeg = findFfmpeg();

    console.log(`capture-motion -> ${opts.out}`);
    console.log(`  app      ${opts.base}`);
    console.log(`  chromium ${executablePath}`);
    console.log(
        `  scenes   ${wanted.length}/${SCENES.length}${opts.only ? ` (--only ${opts.only})` : ""}`,
    );
    console.log("");

    const browser = await chromium.launch({
        executablePath,
        args: GL_ARGS,
        headless: !opts.headed,
    });

    // A throwaway page used purely as an image decoder for the blank check. It is
    // in its own context so it never lands in a recorded video.
    const analyzerContext = await browser.newContext();
    const analyzer = await analyzerContext.newPage();
    await analyzer.goto("about:blank");

    const results = [];
    for (const scene of wanted) {
        process.stdout.write(`  ${scene.id} ... `);
        let record;
        try {
            record = await captureScene(browser, analyzer, scene, opts, ffmpeg);
        } catch (err) {
            record = {
                id: scene.id,
                status: "fail",
                error: `[${scene.id}] ${err instanceof Error ? err.message : String(err)}`,
                video: null,
                videoBytes: 0,
            };
        }
        results.push(record);
        const kb = (record.videoBytes / 1024).toFixed(0);
        console.log(
            record.status === "pass"
                ? `pass  ${kb} KB  ${(record.durationMs / 1000).toFixed(1)}s  ` +
                      `sd=${record.blankCheck?.stdDev}  motion=${record.motionDelta ?? "n/a"}`
                : `FAIL  ${record.error}`,
        );
    }

    await analyzerContext.close();
    await browser.close();

    const failed = results.filter((r) => r.status !== "pass");

    // An --only run must not silently shrink the manifest to one scene: carry
    // forward the entries for scenes this run did not touch, so manifest.json
    // always describes everything sitting in the directory.
    const carried = [];
    if (opts.only) {
        const manifestPath = path.join(opts.out, "manifest.json");
        if (fs.existsSync(manifestPath)) {
            try {
                const previous = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
                const fresh = new Set(results.map((r) => r.id));
                for (const old of previous.scenes ?? []) {
                    if (!fresh.has(old.id) && fs.existsSync(path.join(opts.out, old.video ?? ""))) {
                        carried.push({ ...old, carriedFromPreviousRun: true });
                    }
                }
            } catch {
                /* an unreadable manifest is simply replaced */
            }
        }
    }
    const order = new Map(SCENES.map((s, i) => [s.id, i]));
    const allScenes = [...results, ...carried].sort(
        (a, b) => (order.get(a.id) ?? 99) - (order.get(b.id) ?? 99),
    );

    const manifest = {
        tool: "capture-motion",
        generatedAt: new Date().toISOString(),
        base: opts.base,
        out: opts.out,
        chromium: executablePath,
        glArgs: GL_ARGS,
        only: opts.only,
        blankCheck: {
            method:
                "final screenshot of the canvas element alone, decoded in-browser, " +
                "reduced to luminance stdDev and distinct 15-bit colours",
            thresholds: { stdDev: BLANK_STDDEV_MIN, distinctColours: BLANK_COLOURS_MIN },
        },
        motionDelta:
            "largest mean-absolute luminance difference (0-100) between any two of the " +
            "sampled frames (settled, midpoint, final), on a 24x24 grid; 0 means nothing moved",
        totals: {
            scenes: allScenes.length,
            recordedThisRun: results.length,
            carriedFromPreviousRun: carried.length,
            passed: allScenes.filter((s) => s.status === "pass").length,
            failed: allScenes.filter((s) => s.status !== "pass").length,
        },
        scenes: allScenes,
    };
    fs.writeFileSync(
        path.join(opts.out, "manifest.json"),
        `${JSON.stringify(manifest, null, 2)}\n`,
    );

    console.log("");
    console.log(`  manifest ${path.join(opts.out, "manifest.json")}`);
    console.log(
        `  ${results.length - failed.length}/${results.length} scenes passed this run` +
            (carried.length ? ` (${carried.length} carried forward in the manifest)` : ""),
    );

    if (failed.length > 0) {
        console.error("");
        console.error(`capture-motion: ${failed.length} scene(s) failed:`);
        for (const f of failed) console.error(`  - ${f.id}: ${f.error}`);
        process.exit(1);
    }
}

// Importable, so the scene list and the blank-check metric can be reused or
// tested without recording anything.
export { SCENES, imageStats, signatureDelta, BLANK_STDDEV_MIN, BLANK_COLOURS_MIN };

if (path.resolve(process.argv[1] ?? "") === path.resolve(fileURLToPath(import.meta.url))) {
    await main();
}
