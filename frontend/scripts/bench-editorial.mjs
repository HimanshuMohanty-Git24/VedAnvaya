#!/usr/bin/env node
/**
 * What the editorial surfaces cost, relative to the Knowledge World.
 *
 * The Lab and the two document pages are meant to be light, and "light" needs a comparator or
 * it is an adjective. So the Knowledge World is measured in the same run: it is the heaviest
 * route in the product, it ships Three.js and a 2.4 MB artifact, and the only figure that
 * matters here is how far below it these pages sit.
 *
 * Three numbers per route:
 *
 *   ttfb      server render plus network for the document. On these routes the server render
 *             is several API calls, so this is the figure the revalidate window protects.
 *   scripts   JavaScript transferred, uncompressed. The Lab is server-rendered end to end and
 *             its controls are links, so its number should be the shell's and nothing more.
 *   lcp       largest contentful paint, which on a text page is the headline.
 *
 * Each route is loaded with a cold cache, `--reps` times, and the median reported. One sample
 * is not a measurement: the first hit on a revalidating route pays for the API calls and the
 * second does not.
 *
 * Usage:
 *   node scripts/bench-editorial.mjs [--base http://127.0.0.1:3100] [--reps 3] [--json out.json]
 */

import { chromium } from "@playwright/test";
import { writeFileSync } from "node:fs";

const args = new Map();
for (let i = 2; i < process.argv.length; i += 1) {
    const key = process.argv[i];
    if (!key.startsWith("--")) continue;
    const next = process.argv[i + 1];
    args.set(key.slice(2), next && !next.startsWith("--") ? next : true);
}

const BASE = args.get("base") ?? "http://127.0.0.1:3100";
const REPS = Number(args.get("reps") ?? 3);

const ROUTES = [
    { name: "lab", url: "/visualizations" },
    { name: "plate-four-corpora", url: "/visualizations/four-corpora" },
    { name: "plate-deities", url: "/visualizations/deities" },
    { name: "plate-transmission", url: "/visualizations/transmission" },
    { name: "about", url: "/about" },
    { name: "sources", url: "/sources" },
    /*
     * The comparator, and it must be `/graph/world` rather than `/graph`.
     *
     * `/graph` is the entry shell; the three-dimensional renderer and the 2.4 MB world
     * artifact live one route deeper. Measuring the shell would have shown the Knowledge
     * World costing exactly what an editorial page costs, which is true of the shell and
     * false of the thing being compared against.
     */
    { name: "knowledge-world", url: "/graph/world", settle: 6000 },
];

const median = (values) => {
    const sorted = [...values].sort((a, b) => a - b);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};

const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge" });
const results = [];

for (const route of ROUTES) {
    const samples = [];
    for (let rep = 0; rep < REPS; rep += 1) {
        // A fresh context per repetition, so nothing is served from the HTTP cache.
        const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        const page = await context.newPage();

        /*
         * Two script budgets, not one, and the difference is the whole point.
         *
         * `scriptBytes` is what the page needs in order to become interactive: the chunks the
         * document itself asks for. `prefetchBytes` is what Next fetches afterwards, at low
         * priority, for the links it can see -- which on every page of this site includes the
         * Graph nav item and therefore a 623 KB chunk containing Three.js.
         *
         * An earlier version of this script totalled both and reported 1,220 KB for every
         * route including About, which says nothing about any of them: it is the same prefetch
         * on all seven, it lands after `load`, and none of it is on the critical path.
         * Splitting at the load event is what makes the figure mean something.
         */
        let loaded = false;
        page.on("load", () => {
            loaded = true;
        });
        let scriptBytes = 0;
        let prefetchBytes = 0;
        let documentBytes = 0;
        const scripts = new Set();
        page.on("response", async (response) => {
            const type = response.request().resourceType();
            if (type !== "script" && type !== "document") return;
            const afterLoad = loaded;
            try {
                const length = Number(response.headers()["content-length"] ?? 0);
                const size = length || (await response.body()).byteLength;
                if (type !== "script") {
                    documentBytes += size;
                } else if (afterLoad) {
                    prefetchBytes += size;
                } else {
                    scriptBytes += size;
                    scripts.add(response.url().split("/").pop() ?? "");
                }
            } catch {
                /* A response whose body is gone by the time we ask is not worth failing over. */
            }
        });

        await page.goto(`${BASE}${route.url}`, { waitUntil: "load", timeout: 60_000 });
        await page.waitForTimeout(route.settle ?? 900);

        /*
         * LCP has to be observed, not queried.
         *
         * `getEntriesByType("largest-contentful-paint")` returns nothing on these pages: the
         * entries are only delivered to a PerformanceObserver, and `buffered: true` is what
         * replays the ones that fired before this ran. An earlier version of this script used
         * the query form and reported 0 ms for every route, which is a benchmark that cannot
         * fail.
         */
        const timing = await page.evaluate(
            () =>
                new Promise((resolve) => {
                    const nav = performance.getEntriesByType("navigation")[0];
                    let lcp = null;
                    const observer = new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        if (entries.length) lcp = entries[entries.length - 1].startTime;
                    });
                    try {
                        observer.observe({ type: "largest-contentful-paint", buffered: true });
                    } catch {
                        /* Not supported here; the row reports null rather than zero. */
                    }
                    setTimeout(() => {
                        observer.disconnect();
                        resolve({
                            ttfb: nav ? nav.responseStart - nav.requestStart : null,
                            lcp,
                            domContentLoaded: nav ? nav.domContentLoadedEventEnd : null,
                        });
                    }, 200);
                }),
        );

        samples.push({
            ...timing,
            scriptBytes,
            prefetchBytes,
            documentBytes,
            scriptUrls: scripts,
        });
        await context.close();
    }

    results.push({
        route: route.name,
        url: route.url,
        ttfbMs: Math.round(median(samples.map((s) => s.ttfb ?? 0))),
        lcpMs: Math.round(median(samples.map((s) => s.lcp ?? 0))),
        domContentLoadedMs: Math.round(median(samples.map((s) => s.domContentLoaded ?? 0))),
        scriptKb: Math.round(median(samples.map((s) => s.scriptBytes)) / 1024),
        prefetchKb: Math.round(median(samples.map((s) => s.prefetchBytes)) / 1024),
        documentKb: Math.round(median(samples.map((s) => s.documentBytes)) / 1024),
        scriptCount: samples[0].scriptUrls.size,
        scriptUrls: [...samples[0].scriptUrls].sort(),
    });
}

await browser.close();

const pad = (value, width) => String(value).padStart(width);
console.log(`Median of ${REPS} cold loads at 1440x900.\n`);
console.log("route                   ttfb    lcp    dcl   script  prefetch    html");
for (const row of results) {
    console.log(
        `${row.route.padEnd(20)}${pad(row.ttfbMs, 7)}${pad(row.lcpMs, 7)}${pad(
            row.domContentLoadedMs,
            7,
        )}${pad(`${row.scriptKb}K`, 9)}${pad(`${row.prefetchKb}K`, 10)}${pad(`${row.documentKb}K`, 8)}`,
    );
}

const world = results.find((row) => row.route === "knowledge-world");
const editorial = results.filter((row) => row.route !== "knowledge-world");
if (world) {
    const heaviest = Math.max(...editorial.map((row) => row.scriptKb));
    console.log(
        `
Heaviest editorial route needs ${heaviest}K of JavaScript to become interactive, ` +
            `against the Knowledge World's ${world.scriptKb}K.`,
    );

    /*
     * The figure that actually answers the brief.
     *
     * Every route pays for the same shared shell bundle, so a total in kilobytes mostly
     * measures the shell. What is being asserted is narrower and checkable: the editorial
     * routes add no chunk of their own beyond it, and the Knowledge World does.
     */
    const baseline = new Set(editorial[0]?.scriptUrls ?? []);
    for (const row of editorial.slice(1)) {
        const extra = row.scriptUrls.filter((name) => !baseline.has(name));
        console.log(
            extra.length
                ? `  ${row.route}: ${extra.length} chunk(s) beyond ${editorial[0].route} -- ${extra.join(", ")}`
                : `  ${row.route}: the same chunks as ${editorial[0].route}, and nothing more.`,
        );
    }
    const worldExtra = world.scriptUrls.filter((name) => !baseline.has(name));
    console.log(`  knowledge-world: ${worldExtra.length} chunk(s) no editorial route loads.`);
}

if (args.get("json")) {
    writeFileSync(String(args.get("json")), `${JSON.stringify(results, null, 2)}\n`);
}
