import { expect, test, type Locator, type Page, type TestInfo } from "@playwright/test";
import { inflateSync } from "node:zlib";

/**
 * What the canvas actually publishes, compared against what the tokens predict.
 *
 * ## Why this file has to exist
 *
 * Everything else that guards the graph's colour reads declarations. `audit-tokens.mjs` proves
 * a token is declared, `audit-contrast.mjs` measures a token against a surface, and
 * `audit-graph-contrast.mjs` measures a token composited at the alphas the renderers declare.
 * All three parse CSS in Node. None of them can see the renderer.
 *
 * For the whole life of the two custom shaders in engine.ts they were wrong, and every one of
 * those checks was green. The shaders were handed linear-light triples and wrote them straight
 * into an 8-bit sRGB framebuffer without encoding, so every colour reached the screen darker
 * than the one it was given: light-mode deity #bd4f32 was published as #821408. The tell was
 * subtle and misread for a phase - the selection overlay looked right while everything around
 * it did not, because that object is a `LineBasicMaterial` and Three's own shader carries the
 * encode. One canvas was running two colour pipelines. 55e8715 added
 * `#include <colorspace_fragment>` to both custom shaders and closed it.
 *
 * Nothing in the repository would have caught that, and nothing would catch it coming back. A
 * second encode, a removed one, a `Color` built from a string Three keeps linear, an
 * `outputColorSpace` change, a premultiplied blend func - each moves the published pixel and
 * leaves every declaration untouched. The only instrument that sees it is a pixel.
 *
 * ## What it asserts
 *
 * Indra is at node index 22975. The engine is asked where it projected that node, the canvas is
 * sampled there, and the result is compared against `--va-group-deity-fill` composited over
 * `--va-graph-canvas` at the alpha the token layer declares for a curated orb. Within dE00 2.
 *
 * ## The obstacles, and what is done about each
 *
 * **Readback.** The renderer is built without `preserveDrawingBuffer`, so once a frame has been
 * composited `canvas.toDataURL()` and a `drawImage` into a 2D context both return undefined
 * content - usually transparent black, which would let this test pass on a blank canvas. The
 * pixels therefore come from `locator.screenshot()`, which reads the composited surface and does
 * not care how the context was configured. That leaves a PNG to decode, which is why there is a
 * decoder below rather than a dependency: all that is needed is a non-interlaced truecolour
 * PNG, and `zlib` is built in. The decoder is exercised over all five PNG filter types.
 *
 * **Antialiasing, and how big the orb actually is.** The node fragment shader feathers the rim
 * with a smoothstep, so only the interior carries the declared alpha. A fixed sample block was
 * the first thing tried and it was wrong: on the first run the engine was still in WORLD, where
 * the same node is a few pixels across, and a 9x9 block centred on it was mostly canvas. It
 * reported the dark orb as #b56850 against a predicted #ce7161 and blamed the colour. That is
 * the failure this project has a lesson about - a right figure inside a wrong sentence - so the
 * sample region is now *measured*: the block grows outward from the projected centre for as long
 * as every pixel in it stays within dE00 6 of the block's own median, and the test fails saying
 * "too small to sample" if the flat region is under 5px rather than reporting a colour.
 *
 * **Overdraw.** Indra is the graph's largest hub and every one of its edges terminates at its
 * centre, so the exact centre pixel is the most overdrawn on the canvas. The statistic is the
 * per-channel median of the block, which discards a handful of edge crossings as outliers while
 * a genuine shift in the fill moves every pixel together and is not discarded. A mean would be
 * dragged by the outliers; a wider tolerance would stop failing on the thing this file is for.
 *
 * **Device scale factor.** `screenPositionOf` answers in CSS pixels relative to the canvas's own
 * box; a screenshot buffer is in device pixels. The ratio is measured from the buffer against
 * the element's width and cross-checked against `devicePixelRatio`, rather than either being
 * assumed. The desktop project runs at DSF 1 today, and assuming that is how this would quietly
 * start sampling the wrong place on a machine that does not.
 *
 * **State.** The orb only carries the curated alpha in FOCUS, and the panel becoming visible is
 * not the same event as the focus scene being applied, so the view is waited for, in both
 * themes. The first run asserted it in one test and not the other, and the test without the
 * assertion is the one that reported a colour complaint about a state problem. What is waited on
 * is `data-view` rather than `engine.currentMode`, because the second of those is not
 * maintained - see `openFocusedOnIndra`.
 *
 * Run: npx playwright test graph-palette
 */

const INDRA_INDEX = 22975;
const INDRA_ID = "VG:DEVATA:INDRAH";

/** The world is a two-megabyte artifact and a settling layout; it is not a fast page. */
const SETTLE = 30_000;

/** "The same colour." About two JND for a large patch, and roughly one 8-bit step here. */
const TOLERANCE = 2;

/** How far from the block's own median a pixel may sit and still count as the same flat fill.
    Loose enough to keep the rim's first faint pixel from truncating the block, tight enough
    that the block cannot grow across the rim into the canvas. */
const FLATNESS = 6;

/** The smallest flat region worth a colour claim, and the largest worth sampling. */
const MIN_BLOCK = 5;
const MAX_BLOCK = 15;

type Rgb = [number, number, number];

/* ------------------------------------------------------------------ colour - */

const srgbToLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

function toLab([r, g, b]: Rgb): [number, number, number] {
    const [lr, lg, lb] = [r, g, b].map((c) => srgbToLinear(c / 255));
    const X = (0.4124564 * lr + 0.3575761 * lg + 0.1804375 * lb) / 0.95047;
    const Y = 0.2126729 * lr + 0.7151522 * lg + 0.072175 * lb;
    const Z = (0.0193339 * lr + 0.119192 * lg + 0.9503041 * lb) / 1.08883;
    const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29);
    const [fx, fy, fz] = [f(X), f(Y), f(Z)];
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/**
 * CIEDE2000, the same implementation as scripts/audit-graph-contrast.mjs.
 *
 * Not a channel-wise difference: an 8-bit tolerance per channel is three different tolerances
 * depending on where in the gamut the colour sits, so it would be slack on a dark fill and
 * impossible on a light one. And not a plain Lab distance, which overstates hue differences at
 * the low chroma where half of this palette lives.
 */
function deltaE00(c1: Rgb, c2: Rgb): number {
    const [L1, a1, b1] = toLab(c1);
    const [L2, a2, b2] = toLab(c2);
    const Cb = (Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2;
    const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
    const ap1 = a1 * (1 + G);
    const ap2 = a2 * (1 + G);
    const Cp1 = Math.hypot(ap1, b1);
    const Cp2 = Math.hypot(ap2, b2);
    const deg = (x: number) => ((x * 180) / Math.PI + 360) % 360;
    const hp1 = Cp1 === 0 ? 0 : deg(Math.atan2(b1, ap1));
    const hp2 = Cp2 === 0 ? 0 : deg(Math.atan2(b2, ap2));
    const dL = L2 - L1;
    const dC = Cp2 - Cp1;
    let dh = 0;
    if (Cp1 * Cp2 !== 0) {
        dh = hp2 - hp1;
        if (dh > 180) dh -= 360;
        else if (dh < -180) dh += 360;
    }
    const dH = 2 * Math.sqrt(Cp1 * Cp2) * Math.sin((dh * Math.PI) / 360);
    const Lb = (L1 + L2) / 2;
    const Cpb = (Cp1 + Cp2) / 2;
    let hb: number;
    if (Cp1 * Cp2 === 0) hb = hp1 + hp2;
    else if (Math.abs(hp1 - hp2) <= 180) hb = (hp1 + hp2) / 2;
    else hb = hp1 + hp2 < 360 ? (hp1 + hp2 + 360) / 2 : (hp1 + hp2 - 360) / 2;
    const T =
        1 -
        0.17 * Math.cos(((hb - 30) * Math.PI) / 180) +
        0.24 * Math.cos((2 * hb * Math.PI) / 180) +
        0.32 * Math.cos(((3 * hb + 6) * Math.PI) / 180) -
        0.2 * Math.cos(((4 * hb - 63) * Math.PI) / 180);
    const Sl = 1 + (0.015 * (Lb - 50) ** 2) / Math.sqrt(20 + (Lb - 50) ** 2);
    const Sc = 1 + 0.045 * Cpb;
    const Sh = 1 + 0.015 * Cpb * T;
    const Rt =
        -Math.sin((2 * 30 * Math.exp(-(((hb - 275) / 25) ** 2)) * Math.PI) / 180) *
        (2 * Math.sqrt(Cpb ** 7 / (Cpb ** 7 + 25 ** 7)));
    return Math.sqrt(
        (dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh),
    );
}

/**
 * Encoded-sRGB alpha compositing, which is what the pipeline does.
 *
 * Not a linear-light blend. The drawing buffer is RGBA8 with no hardware sRGB encode, both
 * custom shaders run `colorspace_fragment` before the blend, and the blend func Three sets for
 * a non-premultiplied material is SRC_ALPHA / ONE_MINUS_SRC_ALPHA - so the values the blender
 * sees are already encoded. Compositing in linear here would predict a lighter pixel than the
 * one published and would fail against a correct renderer.
 */
const over = (fg: Rgb, bg: Rgb, alpha: number): Rgb =>
    fg.map((c, i) => alpha * c + (1 - alpha) * bg[i]) as Rgb;

const show = (c: Rgb) =>
    "#" + c.map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");

/* --------------------------------------------------------------- png, decoded - */

/**
 * Enough of a PNG decoder for a Playwright screenshot, and no more.
 *
 * Chromium writes non-interlaced, 8-bit-per-channel, colour type 2 (RGB) or 6 (RGBA), no
 * palette. Anything else throws rather than guessing, because a decoder that silently misread a
 * scanline would hand this test plausible wrong colours - the same class of failure it exists to
 * catch. The filter arithmetic below was checked against PNGs encoded with each of the five
 * filter types, 3- and 4-channel, before this test was trusted.
 */
function decodePng(buffer: Buffer): {
    width: number;
    height: number;
    channels: number;
    data: Buffer;
} {
    expect(buffer.subarray(0, 8).toString("hex"), "not a PNG").toBe("89504e470d0a1a0a");
    let offset = 8;
    let width = 0;
    let height = 0;
    let channels = 0;
    const idat: Buffer[] = [];
    while (offset < buffer.length) {
        const length = buffer.readUInt32BE(offset);
        const type = buffer.subarray(offset + 4, offset + 8).toString("latin1");
        const body = buffer.subarray(offset + 8, offset + 8 + length);
        if (type === "IHDR") {
            width = body.readUInt32BE(0);
            height = body.readUInt32BE(4);
            expect(body.readUInt8(8), "unexpected PNG bit depth").toBe(8);
            expect(body.readUInt8(12), "interlaced PNG").toBe(0);
            const colour = body.readUInt8(9);
            expect([2, 6], `unexpected PNG colour type ${colour}`).toContain(colour);
            channels = colour === 6 ? 4 : 3;
        } else if (type === "IDAT") {
            idat.push(Buffer.from(body));
        } else if (type === "IEND") {
            break;
        }
        offset += 12 + length;
    }
    const raw = inflateSync(Buffer.concat(idat));
    const stride = width * channels;
    const out = Buffer.alloc(stride * height);
    /* Per-scanline filters, undone in place against the row above. Types 0-4 are the whole PNG
       filter set; an unknown byte throws rather than producing a plausible wrong row. */
    for (let y = 0; y < height; y += 1) {
        const filter = raw[y * (stride + 1)];
        const line = raw.subarray(y * (stride + 1) + 1, y * (stride + 1) + 1 + stride);
        for (let x = 0; x < stride; x += 1) {
            const a = x >= channels ? out[y * stride + x - channels] : 0;
            const b = y > 0 ? out[(y - 1) * stride + x] : 0;
            const c = x >= channels && y > 0 ? out[(y - 1) * stride + x - channels] : 0;
            let value: number;
            switch (filter) {
                case 0:
                    value = line[x];
                    break;
                case 1:
                    value = line[x] + a;
                    break;
                case 2:
                    value = line[x] + b;
                    break;
                case 3:
                    value = line[x] + ((a + b) >> 1);
                    break;
                case 4: {
                    const p = a + b - c;
                    const pa = Math.abs(p - a);
                    const pb = Math.abs(p - b);
                    const pc = Math.abs(p - c);
                    value = line[x] + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c);
                    break;
                }
                default:
                    throw new Error(`unknown PNG filter ${filter} on row ${y}`);
            }
            out[y * stride + x] = value & 0xff;
        }
    }
    return { width, height, channels, data: out };
}

/* ------------------------------------------------------------------ sampling - */

type Png = ReturnType<typeof decodePng>;

const pixelAt = (png: Png, x: number, y: number): Rgb => {
    const at = (y * png.width + x) * png.channels;
    return [png.data[at], png.data[at + 1], png.data[at + 2]];
};

const medianRgb = (pixels: Rgb[]): Rgb =>
    [0, 1, 2].map((c) => {
        const values = pixels.map((p) => p[c]).sort((a, b) => a - b);
        return values[(values.length - 1) >> 1];
    }) as Rgb;

/**
 * The largest odd block centred on a point in which every pixel is the same flat colour.
 *
 * Grown rather than assumed, so that "the orb is smaller than the sample" reports itself as a
 * geometry problem instead of as a colour one. Returns the block's median and its size.
 */
function flatBlock(png: Png, cx: number, cy: number) {
    let best: { size: number; colour: Rgb } | null = null;
    for (let size = 3; size <= MAX_BLOCK; size += 2) {
        const half = (size - 1) / 2;
        if (cx - half < 0 || cy - half < 0 || cx + half >= png.width || cy + half >= png.height)
            break;
        const pixels: Rgb[] = [];
        for (let dy = -half; dy <= half; dy += 1)
            for (let dx = -half; dx <= half; dx += 1) pixels.push(pixelAt(png, cx + dx, cy + dy));
        const colour = medianRgb(pixels);
        /* The 90th-percentile deviation rather than the maximum: a hub's edges terminate inside
           this block and each leaves a pixel or two, which the median rejects anyway. Judging
           the block by its single worst pixel would refuse to grow past the first edge. */
        const spread = pixels
            .map((p) => deltaE00(p, colour))
            .sort((a, b) => a - b)[Math.floor(pixels.length * 0.9)];
        if (spread > FLATNESS) break;
        best = { size, colour };
    }
    return best;
}

/* ------------------------------------------------------------------- driving - */

type Handle = {
    screenPositionOf(node: number): { x: number; y: number; z: number } | null;
    currentMode: string;
    drawCount: number;
    setReducedMotion(value: boolean): void;
};

/** The token colours and alphas, resolved by the browser rather than parsed here, so this
    measures the same values the renderer was handed. */
async function readTokens(page: Page) {
    return page.evaluate(() => {
        const probe = document.createElement("span");
        probe.style.cssText = "position:absolute;visibility:hidden;pointer-events:none";
        document.body.append(probe);
        const colour = (token: string) => {
            probe.style.color = "";
            probe.style.color = `var(${token})`;
            return getComputedStyle(probe).color;
        };
        const out = {
            deity: colour("--va-group-deity-fill"),
            canvas: colour("--va-graph-canvas"),
            alphaCurated: Number.parseFloat(
                getComputedStyle(document.documentElement).getPropertyValue(
                    "--va-graph-alpha-curated",
                ),
            ),
            dpr: window.devicePixelRatio,
        };
        probe.remove();
        return out;
    });
}

const parseRgb = (css: string): Rgb => {
    const parts = css.match(/[\d.]+/g);
    expect(parts, `unparseable colour ${css}`).not.toBeNull();
    return parts!.slice(0, 3).map(Number) as Rgb;
};

/**
 * Open the graph on Indra in FOCUS and wait for the engine to agree that it is there.
 *
 * The panel appearing is a DOM event and the mode change is an engine one, and on the first run
 * of this file they were not the same moment: the panel was visible, the engine was still in
 * WORLD, and the orb was therefore a two-pixel WORLD node rather than a curated one.
 */
async function openFocusedOnIndra(page: Page): Promise<Locator> {
    await page.goto(`/graph?view=focus&renderer=3d&node=${encodeURIComponent(INDRA_ID)}`);
    const canvas = page.locator(".va-world-canvas");
    await expect(canvas).toBeVisible({ timeout: SETTLE });
    await expect(page.locator(".va-world-panel")).toBeVisible({ timeout: SETTLE });
    /*
     * `data-view`, and deliberately not `engine.currentMode`.
     *
     * The engine's own mode was the first thing this waited on, and it never arrives:
     * graph-shell.tsx calls `engine?.setMode(state.view)` in an effect that runs while the
     * engine ref is still null on first mount, so `currentMode` stays "WORLD" for the life of
     * the page while `setFocus` has been applied and the curated orbs are on screen. That is
     * worth knowing and is not this file's to fix - it is carried in the attachment below so
     * the reading stays visible rather than assumed - but it makes `currentMode` the wrong
     * signal to wait on. `data-view` is written by the surface that owns the state.
     *
     * The orb's presence is then proved geometrically rather than trusted: the flat block has
     * to measure at least MIN_BLOCK across, which only a curated orb at 16-40px produces. A
     * WORLD-sized node at this zoom fails that and says so.
     */
    await expect(page.locator('.va-graph[data-view="FOCUS"]')).toBeVisible({ timeout: SETTLE });
    /* Reduced motion cancels the entry flight and the damping, so the projection the engine
       reports and the pixels the compositor holds come from the same camera. Without it the orb
       moves between the two reads and the sample lands beside it. */
    await page.evaluate(() => {
        (window as unknown as { __vedaWorld?: Handle }).__vedaWorld?.setReducedMotion(true);
    });
    await page.waitForTimeout(1_500);
    return canvas;
}

/** Sample Indra's orb and compare it against the prediction, attaching the numbers either way. */
async function assertOrbMatchesTokens(
    page: Page,
    canvas: Locator,
    testInfo: TestInfo,
    label: string,
) {
    const tokens = await readTokens(page);
    expect(
        Number.isFinite(tokens.alphaCurated),
        "--va-graph-alpha-curated is not declared as a bare number",
    ).toBe(true);

    const placed = await page.evaluate((index) => {
        const engine = (window as unknown as { __vedaWorld?: Handle }).__vedaWorld;
        if (!engine) return null;
        const at = engine.screenPositionOf(index);
        return at ? { ...at, mode: engine.currentMode, drawn: engine.drawCount } : null;
    }, INDRA_INDEX);
    expect(
        placed,
        "the engine handle did not place Indra: __vedaWorld is absent or the node is off screen",
    ).not.toBeNull();

    /* The canvas element's own screenshot, so the coordinates `screenPositionOf` returns -
       relative to the canvas's client box - need no page offset that could be stale. */
    const png = decodePng(await canvas.screenshot());
    const box = await canvas.boundingBox();
    expect(box, "the canvas has no layout box").not.toBeNull();

    /* Measured against the element's width, so it is right whether the difference comes from
       deviceScaleFactor, from browser zoom, or from the renderer capping its own pixel ratio. */
    const scale = png.width / box!.width;
    expect(
        Math.abs(scale - tokens.dpr),
        `the screenshot is ${scale.toFixed(3)}x the element and the page reports devicePixelRatio ${tokens.dpr}`,
    ).toBeLessThan(0.02);

    const cx = Math.round(placed!.x * scale);
    const cy = Math.round(placed!.y * scale);
    const block = flatBlock(png, cx, cy);

    const fill = parseRgb(tokens.deity);
    const ground = parseRgb(tokens.canvas);
    const predicted = over(fill, ground, tokens.alphaCurated);
    const sampled = block?.colour ?? pixelAt(png, cx, cy);
    const measured = deltaE00(sampled, predicted);

    await testInfo.attach(`graph-palette-${label}.txt`, {
        body:
            `node            ${INDRA_INDEX} (${INDRA_ID})\n` +
            `engine mode     ${placed!.mode} - not waited on; see openFocusedOnIndra\n` +
            `frames drawn    ${placed!.drawn}\n` +
            `projected       ${placed!.x.toFixed(1)}, ${placed!.y.toFixed(1)} css px\n` +
            `buffer scale    ${scale.toFixed(3)} (devicePixelRatio ${tokens.dpr})\n` +
            `canvas buffer   ${png.width}x${png.height}, ${png.channels} channels\n` +
            `flat block      ${block ? `${block.size}x${block.size} at ${cx},${cy}` : `none - centre pixel only at ${cx},${cy}`}\n` +
            `deity token     ${show(fill)}\n` +
            `canvas token    ${show(ground)}\n` +
            `alpha curated   ${tokens.alphaCurated}\n` +
            `predicted       ${show(predicted)}\n` +
            `published       ${show(sampled)}\n` +
            `dE00            ${measured.toFixed(2)} (tolerance ${TOLERANCE})\n`,
        contentType: "text/plain",
    });

    /*
     * Geometry before colour.
     *
     * Each of these three is a way for the sample to be measuring something other than the
     * orb's interior, and each of them would otherwise surface as a wrong colour. The first
     * run of this file did exactly that: it reported #b56850 against a predicted #ce7161 and
     * blamed the renderer, when the engine had simply still been in WORLD and the block had
     * been mostly canvas.
     */
    expect(
        block,
        `no flat region at all around ${cx},${cy}: the projection and the pixels disagree, ` +
            "so this is a placement failure rather than a colour one",
    ).not.toBeNull();
    expect(
        block!.size,
        `the flat region around Indra is only ${block!.size}px across, which is too small to ` +
            "make a colour claim about. Either the orb is not being drawn at the curated size " +
            "or the camera has not settled.",
    ).toBeGreaterThanOrEqual(MIN_BLOCK);
    expect(
        deltaE00(sampled, ground),
        `the sampled block is the cleared canvas (${show(ground)}), so either the sample missed ` +
            "the orb or the readback returned nothing",
    ).toBeGreaterThan(TOLERANCE);

    expect(
        measured,
        `Indra's orb published ${show(sampled)} where the ${label} tokens predict ${show(predicted)} ` +
            `(${show(fill)} at alpha ${tokens.alphaCurated} over ${show(ground)}), dE00 ${measured.toFixed(2)}. ` +
            `Sampled from a ${block!.size}x${block!.size} flat region, so this is the fill and not the rim. ` +
            "A gap of this size is a renderer-side colour defect rather than a palette one: check that " +
            "colorspace_fragment appears exactly once in each custom fragment shader in engine.ts, that " +
            "toLinearTriple in palette.ts has neither been removed nor doubled, that outputColorSpace is " +
            "still SRGBColorSpace, and that no uniform is scaling the colour on its way through.",
    ).toBeLessThanOrEqual(TOLERANCE);
}

/* -------------------------------------------------------------------- test - */

test.describe("the 3D canvas publishes the colours the tokens declare", () => {
    /* Two settles - the artifact, then the layout - before a pixel can be read. */
    test.setTimeout(150_000);

    test("Indra's orb is the deity fill, composited at the declared alpha", async ({
        page,
    }, testInfo) => {
        const canvas = await openFocusedOnIndra(page);

        /*
         * The magic number, checked rather than trusted.
         *
         * 22975 is an index into a packed artifact and a rebuild could renumber it. A test that
         * sampled the wrong node would compare a deity prediction against some other group's
         * fill and report a numbering problem as a colour complaint, so the identity is asserted
         * from the labels the page itself loaded.
         */
        const identity = await page.evaluate(async (index) => {
            const response = await fetch("/world/world.labels.json");
            const labels = (await response.json()) as { ids: string[]; labels: string[] };
            return { id: labels.ids[index], label: labels.labels[index] };
        }, INDRA_INDEX);
        expect(identity.id, `node ${INDRA_INDEX} is no longer Indra`).toBe(INDRA_ID);
        expect(identity.label).toBe("Indra");

        await assertOrbMatchesTokens(page, canvas, testInfo, "light");
    });

    /*
     * And the same claim in the dark theme.
     *
     * Not redundancy. The colour-space defect this file guards inverted by theme - darkening
     * everything happens to raise contrast against ivory and destroys it against carbon - so a
     * light-only check would report the lesser half of it, and a regression tuned until the light
     * theme looked right would pass.
     */
    test("the same orb is the dark deity fill in the dark theme", async ({ page }, testInfo) => {
        await page.goto(`/graph?view=focus&renderer=3d&node=${encodeURIComponent(INDRA_ID)}`);
        await expect(page.locator(".va-world-canvas")).toBeVisible({ timeout: SETTLE });
        await page.evaluate(() => document.documentElement.classList.add("dark"));
        /* Past the longest surface transition and past the engine's own re-read: the palette hook
           defers a frame after the class lands, because reading in the same tick returns the
           outgoing theme. */
        await page.waitForTimeout(1_200);
        const canvas = await openFocusedOnIndra(page);
        await page.evaluate(() => document.documentElement.classList.add("dark"));
        await page.waitForTimeout(1_200);

        await assertOrbMatchesTokens(page, canvas, testInfo, "dark");
    });
});
