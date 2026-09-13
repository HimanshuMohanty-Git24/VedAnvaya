/**
 * Build the VedAnvaya browser identity from the emblem geometry.
 *
 * ## Why the icon is not one drawing
 *
 * The emblem is 240 units wide and 160 tall: two mirrored calligraphic strokes around a rule,
 * with the rule itself 7 units thick. Put in a square at 16 pixels, that rule is a fifth of a
 * pixel and the strokes taper to points that fall below a pixel long before their tips. It
 * renders as a smear. Rendered at 16, 32 and 48 and magnified, the crossover is visible: the
 * full mark is unreadable at 16, marginal at 32 and correct from 48.
 *
 * So the `.ico` carries two drawings. The small entries keep the part of the mark that
 * survives, which is the rubric diamond sitting on its rule, and that is not a compromise:
 * the diamond is the element the wordmark, the thread divider and the section rules all share,
 * so a reader who has seen the site once recognises it. From 48 up the full emblem is drawn.
 *
 * Ground is rubric red with an ivory mark, which is the brand board's primary app icon and
 * has the practical advantage of holding its own against both a light and a dark browser
 * chrome. An ivory icon disappears into a light tab strip.
 *
 * Run: node scripts/build-brand-icons.mjs
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const APP = path.join(here, "..", "src", "app");
const PUBLIC = path.join(here, "..", "public");

const IVORY = "#F4F0E7";
const RUBRIC = "#B64A2E";

/** The upper-left stroke, traced and fitted in Phase 1. The rest is reflection. */
const STROKE =
    "M-11.1 -79.7C-31 -80.1 -48.1 -65.3 -54 -48.9C-61.2 -34.2 -64.5 -14.4 -83.3 -7.5" +
    "L-78.3 -7.5C-33.6 -6.8 -38.7 -54.3 -12.3 -74C-9.9 -76.8 -2.2 -77.3 -2.1 -79.7Z";

const frame = (inner, radius) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="-128 -128 256 256">` +
    `<rect x="-128" y="-128" width="256" height="256" rx="${radius}" fill="${RUBRIC}"/>` +
    `${inner}</svg>`;

/**
 * The whole mark. Correct from 48 pixels up.
 *
 * The diamond is ivory here rather than rubric. On the site it is rubric on ink and reads as
 * a mark; on a rubric ground the same fill makes it a hole, and what the eye sees is a notch
 * bitten out of the rule with two arrow points, which reads as a rendering fault. Solid, it
 * is a diamond swelling on a line, which is the mark.
 */
const fullEmblem = (radius, scale = 0.98) =>
    frame(
        `<g transform="scale(${scale})" fill="${IVORY}">` +
            `<path d="${STROKE}"/><path d="${STROKE}" transform="scale(-1 1)"/>` +
            `<path d="${STROKE}" transform="scale(1 -1)"/><path d="${STROKE}" transform="scale(-1 -1)"/>` +
            `<rect x="-120" y="-3.5" width="99" height="7"/><rect x="21" y="-3.5" width="99" height="7"/>` +
            `<path d="M0 -21L21 0L0 21L-21 0Z"/></g>`,
        radius,
    );

/**
 * The diamond on its rule. What is left of the mark when a pixel is the unit.
 *
 * The stubs are deliberately short and thick. A rule that ran the full width would be one
 * pixel at this size and would either vanish or alias into a grey band; two heavy stubs read
 * as a line passing behind the diamond, which is the idea the mark is about.
 */
const smallMark = (radius) =>
    frame(
        `<g fill="${IVORY}">` +
            `<rect x="-96" y="-9" width="46" height="18"/><rect x="50" y="-9" width="46" height="18"/>` +
            `<path d="M0 -58L58 0L0 58L-58 0Z"/></g>`,
        radius,
    );

/** The emblem in ink on no ground, for the social card, which has its own paper. */
const fullEmblemInk = () =>
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-120 -80 240 160" fill="none">` +
    `<g fill="#171815"><path d="${STROKE}"/><path d="${STROKE}" transform="scale(-1 1)"/>` +
    `<path d="${STROKE}" transform="scale(1 -1)"/><path d="${STROKE}" transform="scale(-1 -1)"/>` +
    `<rect x="-120" y="-3.5" width="99" height="7"/><rect x="21" y="-3.5" width="99" height="7"/></g>` +
    `<path d="M0 -21L21 0L0 21L-21 0Z" fill="${RUBRIC}"/></svg>`;

/** ICO entries, smallest first. `art` decides which of the two drawings the size gets. */
const ICO_SIZES = [
    { size: 16, art: smallMark },
    { size: 32, art: smallMark },
    { size: 48, art: fullEmblem },
];

/**
 * Standalone PNGs.
 *
 * Deliberately no `src/app/icon.png`. Next emits a link for every icon convention it finds,
 * so an `icon.png` beside `favicon.ico` produces two candidates, one declaring 48x48 and one
 * declaring 512x512, and which a browser picks for a 16px tab is a heuristic rather than a
 * decision. Since the whole point of the `.ico` here is that it carries different artwork at
 * different sizes, leaving a second candidate that does not would put the illegible drawing
 * back in the tab. The 192 and 512 an installed app needs come from the manifest instead.
 */
const PNGS = [
    { file: path.join(APP, "apple-icon.png"), size: 180, art: fullEmblem, radius: 40 },
    { file: path.join(PUBLIC, "brand/icon-192.png"), size: 192, art: fullEmblem, radius: 42 },
    { file: path.join(PUBLIC, "brand/icon-512.png"), size: 512, art: fullEmblem, radius: 112 },
    /* Maskable: the platform crops to its own shape, so the art is pulled in to sit entirely
       inside the safe area and the corners are left square for the platform to cut. */
    { file: path.join(PUBLIC, "brand/icon-maskable-512.png"), size: 512, art: (r) => fullEmblem(r, 0.66), radius: 0 },
];

/**
 * Render one SVG to a PNG of exactly `size` square.
 *
 * `omitBackground` is on, which does two jobs. It leaves the area outside the rounded
 * rectangle genuinely transparent, which is what an icon wants, and it makes Playwright emit
 * RGBA rather than RGB. Next's ICO decoder refuses a PNG that is not RGBA outright, with
 * "The PNG is not in RGBA format", and the build fails rather than the icon degrading.
 */
async function render(page, svg, size) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(
        `<body style="margin:0;background:transparent;width:${size}px;height:${size}px">` +
            `<div style="width:${size}px;height:${size}px">${svg}</div>` +
            `<style>svg{width:100%;height:100%;display:block}</style></body>`,
    );
    return page.screenshot({ omitBackground: true });
}

/**
 * Assemble an ICO from PNG payloads.
 *
 * The container is six bytes of header, sixteen per entry, then the payloads. Every modern
 * browser reads PNG-in-ICO, which is what makes per-size artwork possible at all: a BMP-based
 * ICO would force one bitmap format across every entry and rule out changing the drawing.
 */
function buildIco(entries) {
    const header = Buffer.alloc(6);
    header.writeUInt16LE(0, 0); // reserved
    header.writeUInt16LE(1, 2); // type 1 is icon
    header.writeUInt16LE(entries.length, 4);

    let offset = 6 + entries.length * 16;
    const directory = [];
    for (const { size, png } of entries) {
        const entry = Buffer.alloc(16);
        entry.writeUInt8(size >= 256 ? 0 : size, 0); // 0 means 256
        entry.writeUInt8(size >= 256 ? 0 : size, 1);
        entry.writeUInt8(0, 2); // palette size, 0 for truecolour
        entry.writeUInt8(0, 3); // reserved
        entry.writeUInt16LE(1, 4); // colour planes
        entry.writeUInt16LE(32, 6); // bits per pixel
        entry.writeUInt32LE(png.length, 8);
        entry.writeUInt32LE(offset, 12);
        directory.push(entry);
        offset += png.length;
    }
    return Buffer.concat([header, ...directory, ...entries.map((e) => e.png)]);
}

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ deviceScaleFactor: 1 });

const icoEntries = [];
for (const { size, art } of ICO_SIZES) {
    /* Radius scales with the icon: a fixed 56-unit radius on a 16px icon is a circle. */
    const radius = size <= 32 ? 40 : 52;
    const png = await render(page, art(radius), size);
    icoEntries.push({ size, png });
    console.log(`  ico ${String(size).padStart(3)}px  ${(png.length / 1024).toFixed(1)} KB  ${art === smallMark ? "diamond and rule" : "full emblem"}`);
}

const ico = buildIco(icoEntries);
writeFileSync(path.join(APP, "favicon.ico"), ico);
console.log(`  favicon.ico  ${(ico.length / 1024).toFixed(1)} KB, ${icoEntries.length} entries`);

mkdirSync(path.join(PUBLIC, "brand"), { recursive: true });
for (const { file, size, art, radius } of PNGS) {
    const png = await render(page, art(radius), size);
    writeFileSync(file, png);
    console.log(`  ${path.relative(path.join(here, ".."), file).padEnd(38)} ${size}px  ${(png.length / 1024).toFixed(1)} KB`);
}



/* ---------------------------------------------------------------- social card - */

/**
 * The OpenGraph card, 1200 by 630.
 *
 * Rendered rather than hand-composed in an image editor so it stays in step with the brand:
 * it uses the same rebalanced plate as the homepage hero, the same emblem geometry, and
 * Fraunces at the same optical size the site sets it at.
 *
 * Static rather than generated per route. A per-passage card would be better and is a real
 * piece of work, because the verse would have to be shaped correctly at card size with its
 * combining marks intact, and the font that can do that is the self-hosted one. Recorded as
 * backlog rather than half-built here.
 */
/* Read from disk rather than fetched over HTTP. A first version pointed an <img> at
   localhost:3000, which silently produced a blank card whenever the dev server happened to
   be down, and the only symptom was the file getting ten times smaller. */
const plate = readFileSync(path.join(PUBLIC, "brand/textures/og-light-1200.webp")).toString("base64");

const ogPage = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await ogPage.setContent(
    `<!doctype html><meta charset="utf-8">
     <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400&family=Inter:opsz,wght@14..32,400&display=block">
     <body style="margin:0;width:1200px;height:630px;position:relative;background:${IVORY};overflow:hidden">
       <img src="data:image/webp;base64,${plate}"
            style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.92">
       <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;gap:26px;padding:0 92px">
         <div style="display:flex;align-items:center;gap:22px">
           <div style="width:96px">${fullEmblemInk()}</div>
           <span style="font-family:Fraunces;font-size:62px;letter-spacing:-.02em;color:#171815;line-height:1">VedAnvaya</span>
         </div>
         <p style="margin:0;font-family:Fraunces;font-size:40px;line-height:1.22;letter-spacing:-.015em;color:#171815;max-width:22ch">Four Samhitas, one corpus, and the evidence behind every connection.</p>
         <p style="margin:0;font-family:Inter;font-size:17px;letter-spacing:.16em;text-transform:uppercase;color:#5d5f56">The Vedas, connected.</p>
       </div>
     </body>`,
    { waitUntil: "networkidle" },
);
await ogPage.evaluate(() => document.fonts.ready);
const og = await ogPage.screenshot();
writeFileSync(path.join(PUBLIC, "brand/og.png"), og);
console.log(`  ${path.relative(path.join(here, ".."), path.join(PUBLIC, "brand/og.png")).padEnd(38)} 1200x630  ${(og.length / 1024).toFixed(1)} KB`);
await ogPage.close();

await browser.close();
