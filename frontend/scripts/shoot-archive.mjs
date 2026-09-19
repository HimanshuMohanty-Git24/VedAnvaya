/**
 * The screenshot archive, and the overflow sweep that goes with it.
 *
 *   node scripts/shoot-archive.mjs --out ../screenshots/<name>
 *
 * Run against a *production* build. A capture from the dev server photographs Turbopack's
 * output rather than the artifact that ships, and the two differ - most visibly in how CSS
 * is ordered, which is exactly what an archive of a design system is for.
 *
 * Every required route at 1440 and 390, in both themes, plus the interaction states that
 * only exist after a click. The overflow check runs on every shot, so the archive and the
 * QA are one pass over one build rather than two passes that could disagree.
 */
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const args = process.argv.slice(2);
const arg = (n, d) => {
    const i = args.indexOf(`--${n}`);
    return i >= 0 ? args[i + 1] : d;
};
const BASE = arg("base", "http://localhost:3000");
const OUT = arg("out", ".tmp/archive");
const ONLY = arg("only", null);

const E = encodeURIComponent;
const RV = E("VG:RV:SAK:M01:S032:V001");
const SV = E("VG:SV:KAU:ARANYA:D03:V04");
const YV = E("VG:YV:VSM:A01:V017");
const AV = E("VG:AV:SAU:K01:S006:V002");
const INDRA = E("VG:DEVATA:INDRAH");
const TAKMAN = "VG:CONCEPT:TAKMAN-FEVER";

/** name, url, and optionally a state to drive before the shot. */
const SURFACES = [
    { name: "01-home", url: "/", full: true },
    { name: "02-home-archive-strip", url: "/", scrollTo: ".va-archive-strip" },
    { name: "03-vedas", url: "/vedas", full: true },
    { name: "04-vedas-scope-register", url: "/vedas", scrollTo: ".va-scope" },
    { name: "05-veda-rigveda", url: "/vedas/rigveda" },
    { name: "06-veda-samaveda", url: "/vedas/samaveda" },
    { name: "07-veda-yajurveda", url: "/vedas/yajurveda" },
    { name: "08-veda-atharvaveda", url: "/vedas/atharvaveda" },
    { name: "09-reader-rigveda", url: `/passage/${RV}` },
    { name: "10-reader-rigveda-marginalia", url: `/passage/${RV}`, scrollTo: ".va-folio-margin" },
    { name: "11-reader-rigveda-accent-trace", url: `/passage/${RV}`, scrollTo: ".recitation" },
    {
        name: "12-reader-witness-comparison",
        url: `/passage/${RV}`,
        click: ".va-collation-open",
    },
    { name: "13-reader-shelfmark", url: `/passage/${RV}`, scrollTo: ".va-shelfmark" },
    { name: "14-reader-samaveda", url: `/passage/${SV}` },
    { name: "15-reader-yajurveda", url: `/passage/${YV}` },
    { name: "16-reader-atharvaveda", url: `/passage/${AV}` },
    { name: "17-ask-idle", url: "/ask" },
    { name: "18-search", url: "/search?q=agni&type=PASSAGE" },
    { name: "19-search-entities", url: "/search?q=Indra" },
    { name: "20-explore", url: "/explore" },
    { name: "21-explore-atharvaveda", url: "/explore/atharvaveda", full: true },
    { name: "22-rituals", url: "/rituals", full: true },
    { name: "23-material-culture", url: "/material-culture", full: true },
    { name: "24-formulas", url: "/formulas", full: true },
    { name: "25-insights", url: "/insights", full: true },
    { name: "26-connections", url: "/connections", full: true },
    { name: "27-graph-world", url: "/graph", settle: 9000 },
    { name: "28-graph-focus", url: `/graph?node=${INDRA}`, settle: 9000 },
    { name: "31-entity-devata", url: `/devatas/${INDRA}`, full: true },
    { name: "32-entity-condition", url: `/entities/condition/${E(TAKMAN)}` },
    { name: "33-visualizations", url: "/visualizations", full: true },
    { name: "34-visualize-four-corpora", url: "/visualizations/four-corpora", full: true },
    { name: "35-sources", url: "/sources", full: true },
    { name: "36-limits", url: "/limits", full: true },
    { name: "37-about", url: "/about", full: true },
];

/** The graph's PATH states need driving, and are captured in both renderers. */
async function tracePath(page, renderer) {
    await page.getByRole("button", { name: renderer, exact: true }).click();
    await page.getByRole("button", { name: "Path", exact: true }).click();
    await page.getByRole("textbox", { name: "From" }).fill("Agni");
    await page.getByRole("textbox", { name: "To" }).fill(TAKMAN);
    const trace = page.getByRole("button", { name: /Trace the connection/i });
    await trace.waitFor({ state: "visible" });
    for (let i = 0; i < 60 && (await trace.isDisabled()); i += 1) await page.waitForTimeout(500);
    await trace.click();
    await page.waitForTimeout(6000);
}

const VIEWS = [
    { name: "desktop", width: 1440, height: 1000 },
    { name: "mobile", width: 390, height: 844 },
];
const THEMES = ["light", "dark"];

const findings = [];
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge" });

for (const view of VIEWS) {
    for (const theme of THEMES) {
        const dir = path.join(OUT, `${view.name}-${theme}`);
        await mkdir(dir, { recursive: true });
        const context = await browser.newContext({
            viewport: { width: view.width, height: view.height },
            deviceScaleFactor: 1,
            colorScheme: theme,
            hasTouch: view.name === "mobile",
            isMobile: view.name === "mobile",
        });
        const page = await context.newPage();

        const surfaces = ONLY ? SURFACES.filter((s) => s.name.includes(ONLY)) : SURFACES;
        for (const surface of surfaces) {
            try {
                await page.goto(`${BASE}${surface.url}`, { waitUntil: "load", timeout: 60000 });
                await page.waitForTimeout(surface.settle ?? 1200);
                if (surface.click) {
                    await page.locator(surface.click).first().click({ timeout: 8000 });
                    await page.waitForTimeout(900);
                }
                if (surface.scrollTo) {
                    await page.evaluate((sel) => {
                        document.querySelector(sel)?.scrollIntoView({
                            block: "center",
                            behavior: "instant",
                        });
                    }, surface.scrollTo);
                    await page.waitForTimeout(900);
                }
                const overflow = await page.evaluate(
                    () =>
                        document.documentElement.scrollWidth -
                        document.documentElement.clientWidth,
                );
                if (overflow > 1) {
                    findings.push(`${view.name}/${theme} ${surface.name}: +${overflow}px`);
                }
                await page.screenshot({
                    path: path.join(dir, `${surface.name}.png`),
                    fullPage: Boolean(surface.full),
                });
            } catch (error) {
                findings.push(
                    `${view.name}/${theme} ${surface.name}: ${String(error).slice(0, 140)}`,
                );
            }
        }

        /* The two PATH renderers, driven. Desktop only: the trace form is the same control
           on a phone and the canvas is what differs, which the graph shots already carry. */
        if (!ONLY && view.name === "desktop") {
            for (const [name, renderer] of [
                ["29-graph-path-3d", "3D"],
                ["30-graph-path-2d", "2D"],
            ]) {
                try {
                    await page.goto(`${BASE}/graph`, { waitUntil: "load", timeout: 60000 });
                    await page.waitForTimeout(6000);
                    await tracePath(page, renderer);
                    await page.screenshot({ path: path.join(dir, `${name}.png`) });
                } catch (error) {
                    findings.push(`${view.name}/${theme} ${name}: ${String(error).slice(0, 140)}`);
                }
            }
        }

        await context.close();
    }
}

await browser.close();
await writeFile(path.join(OUT, "overflow-report.txt"), findings.join("\n") || "none\n", "utf8");
console.log(findings.length ? findings.join("\n") : "No overflow or capture failures.");
