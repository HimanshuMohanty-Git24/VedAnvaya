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
 * Indra is at node index 22975. The engine is asked where it projected that node and how wide it
 * drew it, the canvas is sampled across that disc, and each sampled pixel is compared against a
 * prediction built from `--va-group-deity-fill`, `--va-graph-canvas`, the curated alpha token and
 * the renderer's own declared depth cues. Within dE00 2, per band of the key light.
 *
 * ## There is no flat patch, and assuming one was a defect in this file
 *
 * The first version of this test grew a square block outward from the projected centre for as
 * long as every pixel stayed within dE00 6 of the block's median, required 5px of it, and
 * compared that median against `over(deity, canvas, alphaCurated)`. It never had a green run,
 * and the reason was not the renderer:
 *
 *   - **A curated orb is a shaded ball, not a disc.** The node shader builds a hemisphere normal
 *     from the point coordinate and mixes towards a key tint by `0.18 * lit`. So the interior is
 *     a gradient by design, and the largest genuinely flat region at the centre measured 3px.
 *   - **It is fogged.** `uFogMax` is solved against the 3:1 contrast gate rather than chosen, and
 *     at the Focus framing it resolves to 0.096 on an ivory page and 0.494 on a carbon one, with
 *     the node half way through the fog band. Measured, that moves the published pixel by about
 *     dE00 3.8 in light and 2.8 in dark - on its own more than the tolerance.
 *   - **Its own spokes are drawn over it.** Forty-one curated nodes means forty spokes converging
 *     on the root, the line object carries `renderOrder` 2 against the orb's 1, and coincident
 *     depth passes `LessEqualDepth`. So the fan covers most of the middle of its own subject's
 *     disc, in very nearly the subject's own hue. This is what made the flat region 3px, and it
 *     is not a defect: an edge that stopped at the rim would be a diagram of a hub rather than a
 *     hub.
 *
 * So the prediction models the fragment - linear fill, key mix, fog mix, sRGB encode, then the
 * encoded-space blend - and the *statistic* is chosen to survive the overdraw rather than to
 * pretend it is absent. See `assertOrbMatchesTokens`.
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
 * **The screenshot is a page clip.** `locator.screenshot()` on a canvas returns the page
 * composited and cropped to the element, so the DOM label overlay above it lands in the buffer -
 * and a name backplate is opaque and sits within 9px of this particular orb. The overlay is
 * hidden for the shutter. That changes no canvas pixel: it is a sibling element, and the claim
 * here is about what the canvas published.
 *
 * **Antialiasing.** The node fragment shader feathers the rim with a smoothstep from r = 0.19 to
 * 0.25 in disc coordinates, which is the outer 13% of the radius. Sampling stops at 0.85R, inside
 * the plateau, so no sampled pixel is part of the feather.
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

/**
 * The band of the orb that is sampled, as a fraction of the drawn radius.
 *
 * The outer bound is inside the rim feather, which begins at 0.872R. The inner bound excludes
 * the densest part of the spoke fan: measured across the whole disc the median disagreement is
 * dE00 1.20, and over this annulus it is 0.30, because forty spokes converging on a point cover
 * a region whose area falls as the square of the radius while their own coverage falls linearly.
 * Nothing about the claim depends on the inner bound - the statistic below already tolerates the
 * fan - but a sample that is three quarters overdrawn is a worse instrument than one that is a
 * third overdrawn, and this costs nothing to choose well.
 */
const SAMPLE_INNER = 0.7;
const SAMPLE_OUTER = 0.85;

/**
 * The fraction of each band that must match, and why it is a quantile at all.
 *
 * Because the spoke fan is drawn over an unknown share of the disc and that share is a property
 * of the layout, not of the colour pipeline. A mean or a maximum over the disc would be a
 * measurement of how many neighbours Indra was given this week. A low quantile is a claim that
 * cannot be satisfied by luck - a quarter of a 130-pixel band is 32 pixels - and cannot be
 * defeated by overdraw short of three quarters of the band.
 *
 * Measured at the commit this was written against: the 25th percentile is dE00 0.13-0.42 across
 * the three bands and both themes, and the best pixels in every band agree to 0.02, which is
 * below one 8-bit step. A missing `colorspace_fragment` would read 21-26 against this same
 * prediction, so there is about fifty times more headroom than the defect needs.
 */
const MATCHING_QUANTILE = 0.25;

/** Below this a band is too small to make a claim about, and something has moved. */
const MIN_BAND = 20;

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

const linearToSrgb = (c: number) => (c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055);

/** What the renderer says it is doing to a fragment's colour. See `Engine.depthCues`. */
type Cues = {
    depth: number;
    fogColour: [number, number, number];
    fog: number;
    keyAmount: number;
    keyShape: number;
    keyTint: [number, number, number];
    light: [number, number, number];
    alpha: number;
};

/**
 * The whole node colour pipeline, for one fragment of one orb, in the order the hardware runs it.
 *
 * `u` and `v` are the fragment's offset from the orb centre divided by its drawn radius, which is
 * exactly `normal.xy` in the shader: the disc spans the point sprite's inscribed circle, so an
 * offset of one radius is a unit of normal. `v` is positive downward, matching both CSS and
 * `gl_PointCoord.t` - the GLES definition is `1/2 - (yw - yf)/size` against a window y that
 * points up, which reverses twice into screen order. Getting that sign wrong would not be a
 * subtle failure: it would put the whole prediction on the wrong hemisphere, and the measured
 * agreement of dE00 0.02 on the lit side is what says it is right.
 *
 * The blend at the end is in encoded space, not linear. The drawing buffer is RGBA8 with no
 * hardware sRGB encode, both custom shaders run `colorspace_fragment` before they write, and the
 * blend func Three sets for a non-premultiplied material is SRC_ALPHA / ONE_MINUS_SRC_ALPHA - so
 * the values the blender sees are already encoded. Compositing in linear here would predict a
 * lighter pixel than the one published and would fail against a correct renderer.
 */
function predictFragment(fill: Rgb, ground: Rgb, alpha: number, cues: Cues, u: number, v: number) {
    const nz = Math.sqrt(Math.max(0, 1 - u * u - v * v));
    const lit = Math.min(
        1,
        Math.max(0, u * cues.light[0] + v * cues.light[1] + nz * cues.light[2]),
    );
    /* `keyShape` selects which side of the ball the light is spent on, and it is a uniform
       rather than a constant because the answer depends on which way the page has contrast to
       give: the unlit half darkens on ivory, the lit half lightens on carbon. */
    const key = cues.keyAmount * (cues.keyShape === 1 ? lit : 1 - lit);
    const colour = fill.map((channel, i) => {
        let linear = srgbToLinear(channel / 255);
        linear = linear * (1 - key) + cues.keyTint[i] * key;
        linear = linear * (1 - cues.fog) + cues.fogColour[i] * cues.fog;
        const encoded = linearToSrgb(linear) * 255;
        return alpha * encoded + (1 - alpha) * ground[i];
    }) as Rgb;
    return { lit, colour };
}

type Sample = { u: number; v: number; lit: number; sampled: Rgb; predicted: Rgb; error: number };

/** Every pixel of the orb's sampled annulus, with the fragment each one should have been. */
function sampleOrb(
    png: Png,
    centre: { x: number; y: number },
    radius: number,
    fill: Rgb,
    ground: Rgb,
    alpha: number,
    cues: Cues,
): Sample[] {
    const out: Sample[] = [];
    const reach = Math.ceil(radius) + 1;
    for (let y = Math.floor(centre.y - reach); y <= Math.ceil(centre.y + reach); y += 1) {
        for (let x = Math.floor(centre.x - reach); x <= Math.ceil(centre.x + reach); x += 1) {
            if (x < 0 || y < 0 || x >= png.width || y >= png.height) continue;
            /* The half is the pixel's own centre, which is where the fragment was evaluated. */
            const dx = x + 0.5 - centre.x;
            const dy = y + 0.5 - centre.y;
            const distance = Math.hypot(dx, dy);
            if (distance < radius * SAMPLE_INNER || distance > radius * SAMPLE_OUTER) continue;
            const u = dx / radius;
            const v = dy / radius;
            const { lit, colour } = predictFragment(fill, ground, alpha, cues, u, v);
            const sampled = pixelAt(png, x, y);
            out.push({ u, v, lit, sampled, predicted: colour, error: deltaE00(sampled, colour) });
        }
    }
    return out;
}

/**
 * The three bands of the key light, which are asserted separately.
 *
 * Because one statistic over the whole orb cannot tell a colour pipeline from a light. If
 * `keyShape` were inverted - the light spending contrast towards the page instead of away from
 * it, which is the regression the shader's own comment warns about - then on an ivory page the
 * shadowed side would be wrong by the full key amount while the lit side stayed exactly right,
 * and more than half the disc would still agree. Asserting each band separately means the claim
 * is about the shading and not only about the fill.
 */
const BANDS: Array<{ name: string; holds: (lit: number) => boolean }> = [
    { name: "shadowed", holds: (lit) => lit < 0.3 },
    { name: "turning", holds: (lit) => lit >= 0.3 && lit < 0.65 },
    { name: "lit", holds: (lit) => lit >= 0.65 },
];

const quantile = (values: number[], p: number) =>
    values.length === 0
        ? Number.NaN
        : [...values].sort((a, b) => a - b)[
              Math.min(values.length - 1, Math.floor(values.length * p))
          ];

/* ------------------------------------------------------------------- driving - */

type Handle = {
    screenPositionOf(node: number): { x: number; y: number; z: number } | null;
    /** Rebuilds the projection before answering, which is why the settle poll uses it. */
    orbGeometry(
        nodes: Iterable<number>,
    ): Array<{ node: number; x: number; y: number; depth: number; radius: number }>;
    /** The depth cues in force, because both of them are solved at runtime and not declared. */
    depthCues(node: number): Cues;
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
     * `data-view` first, then the engine's own mode, then a projection that has stopped moving.
     *
     * An earlier version of this comment recorded that `engine.currentMode` never reaches
     * "FOCUS" and blamed the shell for calling `setMode` against a null engine ref. That was a
     * real observation of a real defect and the diagnosis was wrong: the shell's effect is keyed
     * on the engine and re-runs correctly. The cause was in the state owner - `commit` refused
     * the boot because a boot is not a reader intent, so a `?view=focus` deep link resolved to
     * FOCUS and was forced back to WORLD before the first paint, and the engine was being told
     * WORLD because WORLD was genuinely the state. Fixed, so `currentMode` is a legitimate
     * signal again and is waited on here.
     */
    await expect(page.locator('.va-graph[data-view="FOCUS"]')).toBeVisible({ timeout: SETTLE });
    /*
     * The flight is allowed to finish. It used to be cancelled here.
     *
     * `setReducedMotion(true)` clears the engine's in-progress flight, and the comment that
     * asked for it reasoned that this makes the projection and the pixels come from the same
     * camera. It does - but it does so by stopping the camera *wherever it happens to be*, so
     * the orb was frozen part-way at 801, 529 on its route to 720, 418 and every pixel
     * assertion below was aimed between the ring nodes. Measured against a build with no such
     * call, the same read gives 720, 418 and the two APIs agree to the pixel.
     *
     * The concern it was addressing is real and is now handled properly by waiting for two
     * identical projections below, which is a statement about the camera having arrived rather
     * than about it having been switched off.
     */

    /*
     * Waited on, not slept through.
     *
     * A fixed 1.5s was not enough: the sample landed at 805, 533 while the orb was at 720, 418,
     * found three pixels of flat colour between the ring nodes, and reported a colour defect
     * that was really a camera still in flight. The error message said as much and nobody could
     * tell which of its two branches applied.
     *
     * `orbGeometry` rebuilds the projection before answering, so polling it until the position
     * repeats is a direct statement about the thing the sample depends on. The radius comes
     * back too, so "is this a curated orb" is read from the engine rather than inferred from how
     * wide a flat patch of colour turned out to be.
     */
    /*
     * Polled until the projection *repeats*, not until it merely looks plausible.
     *
     * The first version of this matched a pattern - mode FOCUS and a radius in the curated
     * range - and both of those are true within a few frames of arrival, while the camera is
     * still flying. So it returned at 17 frames drawn with the orb at 799.8, 528.4 on its way
     * to 720, 418, the sample landed between the ring nodes, and the failure read as a colour
     * defect. Matching a shape is not waiting for stillness, and the distinction is the whole
     * point of this wait.
     *
     * `orbGeometry` rebuilds the projection before answering, so two identical consecutive
     * readings are a statement about the camera rather than about the poll interval.
     */
    let previous: string | null = null;
    await expect
        .poll(
            async () => {
                const reading = await page.evaluate((node) => {
                    const engine = (window as unknown as { __vedaWorld?: Handle }).__vedaWorld;
                    const orb = engine?.orbGeometry?.([node])?.[0];
                    if (!orb || engine?.currentMode !== "FOCUS") return null;
                    return `${Math.round(orb.x)}:${Math.round(orb.y)}:${Math.round(orb.radius)}`;
                }, INDRA_INDEX);
                const settled = reading !== null && reading === previous;
                previous = reading;
                return settled ? reading : null;
            },
            {
                message:
                    "the engine never reported the same projection for Indra twice running, so " +
                    "the camera never settled and no pixel here could be attributed to a token",
                timeout: SETTLE,
                intervals: [300, 300, 300, 300, 500, 500, 500, 1_000, 1_000],
            },
        )
        /* A curated root orb is 16-40 CSS px; a WORLD-sized node at this zoom is not, and
           saying so here means the colour assertions below cannot run against a speck. */
        .toMatch(/^\d+:\d+:(1[6-9]|[23]\d|40)$/);
    return canvas;
}

/**
 * Sample Indra's orb across its annulus and compare every pixel against the modelled fragment.
 *
 * The prediction's *palette* comes from CSS - the group fill, the page colour and the curated
 * alpha - and its *cues* come from the renderer, because the fog ceiling is solved against the
 * contrast gate and the key tint is derived from the page's luminance, so neither can be written
 * down here without writing down a number that is allowed to move. What is asserted is the
 * arithmetic that combines them, which is where the defect this file exists for lived: an
 * unencoded write moves every fragment by about dE00 21 whatever the cues are set to.
 *
 * The cues are not taken on trust either. Their *direction* is checked against the contract the
 * shader states - shading only towards the high-contrast side of the page - so reading them from
 * the renderer cannot turn into accepting whatever the renderer felt like doing.
 */
async function assertOrbMatchesTokens(
    page: Page,
    canvas: Locator,
    testInfo: TestInfo,
    label: "light" | "dark",
) {
    const tokens = await readTokens(page);
    expect(
        Number.isFinite(tokens.alphaCurated),
        "--va-graph-alpha-curated is not declared as a bare number",
    ).toBe(true);

    const placed = await page.evaluate((index) => {
        const engine = (window as unknown as { __vedaWorld?: Handle }).__vedaWorld;
        if (!engine) return null;
        const orb = engine.orbGeometry([index])[0];
        if (!orb) return null;
        return {
            ...orb,
            cues: engine.depthCues(index),
            mode: engine.currentMode,
            drawn: engine.drawCount,
        };
    }, INDRA_INDEX);
    expect(
        placed,
        "the engine handle did not place Indra: __vedaWorld is absent or the node is off screen",
    ).not.toBeNull();

    const cues = placed!.cues;

    /*
     * The light is hidden from the page it has to be read against.
     *
     * Not a colour assertion - a statement about which way the cue points, without which reading
     * the cue from the renderer would make the prediction unfalsifiable. On an ivory page the
     * tint is black and the shape shades the unlit side; on a carbon one the tint is white and
     * the shape lights the lit side. The inverse of either would lift half of every orb towards
     * the paper it is measured against, spending contrast the palette has none of to spare.
     */
    expect(
        cues.keyAmount,
        "the curated orb has no key light at all, so it is a flat disc again",
    ).toBeGreaterThan(0);
    expect(
        { tint: cues.keyTint[0], shape: cues.keyShape },
        `in the ${label} theme the key light must shade away from the page, not towards it`,
    ).toEqual(label === "light" ? { tint: 0, shape: 0 } : { tint: 1, shape: 1 });

    /*
     * The label overlay is hidden for the shutter, because the screenshot is a page clip.
     *
     * `.va-world-label.is-strong` for Indra measures 50x23 at an offset of 9px from this orb's
     * centre, with an opaque near-white backplate. It is a sibling of the canvas and hiding it
     * changes nothing the canvas draws; leaving it visible would put a token of the *label*
     * palette inside a sample of the *graph* palette.
     */
    await page.addStyleTag({
        content: ".va-edge-labels, .va-world-label { display: none !important }",
    });

    /* The canvas element's own screenshot, so the coordinates `orbGeometry` returns - relative
       to the canvas's client box - need no page offset that could be stale. */
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

    const fill = parseRgb(tokens.deity);
    const ground = parseRgb(tokens.canvas);
    const samples = sampleOrb(
        png,
        { x: placed!.x * scale, y: placed!.y * scale },
        placed!.radius * scale,
        fill,
        ground,
        tokens.alphaCurated,
        cues,
    );

    const bands = BANDS.map((band) => {
        const rows = samples.filter((sample) => band.holds(sample.lit));
        const errors = rows.map((sample) => sample.error);
        return {
            name: band.name,
            count: rows.length,
            matching: quantile(errors, MATCHING_QUANTILE),
            median: quantile(errors, 0.5),
            worst: quantile(errors, 1),
            best: rows.length === 0 ? null : rows.reduce((a, b) => (a.error <= b.error ? a : b)),
        };
    });

    /* How wrong an unencoded write would look against this same prediction, so the attachment
       records the margin rather than only the reading. */
    const unencoded = quantile(
        samples.map((sample) => {
            const raw = fill.map((channel, i) => {
                let linear = srgbToLinear(channel / 255);
                const key = cues.keyAmount * (cues.keyShape === 1 ? sample.lit : 1 - sample.lit);
                linear = linear * (1 - key) + cues.keyTint[i] * key;
                linear = linear * (1 - cues.fog) + cues.fogColour[i] * cues.fog;
                return tokens.alphaCurated * linear * 255 + (1 - tokens.alphaCurated) * ground[i];
            }) as Rgb;
            return deltaE00(raw, sample.predicted);
        }),
        MATCHING_QUANTILE,
    );

    await testInfo.attach(`graph-palette-${label}.txt`, {
        body:
            `node            ${INDRA_INDEX} (${INDRA_ID})\n` +
            `engine mode     ${placed!.mode}\n` +
            `frames drawn    ${placed!.drawn}\n` +
            `projected       ${placed!.x.toFixed(1)}, ${placed!.y.toFixed(1)} css px, radius ${placed!.radius.toFixed(1)}\n` +
            `buffer scale    ${scale.toFixed(3)} (devicePixelRatio ${tokens.dpr})\n` +
            `canvas buffer   ${png.width}x${png.height}, ${png.channels} channels\n` +
            `sampled         ${samples.length} px over ${SAMPLE_INNER}-${SAMPLE_OUTER}R\n` +
            `deity token     ${show(fill)}\n` +
            `canvas token    ${show(ground)}\n` +
            `alpha curated   ${tokens.alphaCurated}\n` +
            `view depth      ${cues.depth.toFixed(0)}\n` +
            `fog             ${cues.fog.toFixed(4)} towards linear ${cues.fogColour.map((c) => c.toFixed(4)).join(", ")}\n` +
            `key light       ${cues.keyAmount} towards ${cues.keyTint.join(",")}, shape ${cues.keyShape}, from ${cues.light.map((c) => c.toFixed(3)).join(", ")}\n` +
            bands
                .map(
                    (band) =>
                        `band ${band.name.padEnd(9)} n=${String(band.count).padStart(4)} ` +
                        `p${MATCHING_QUANTILE * 100} ${band.matching.toFixed(2)} ` +
                        `median ${band.median.toFixed(2)} worst ${band.worst.toFixed(2)}` +
                        (band.best
                            ? `  best px published ${show(band.best.sampled)} against ${show(band.best.predicted)} at lit ${band.best.lit.toFixed(2)}`
                            : ""),
                )
                .join("\n") +
            `\ntolerance       ${TOLERANCE}\n` +
            `margin          an unencoded write would read ${unencoded.toFixed(1)} here\n`,
        contentType: "text/plain",
    });

    /*
     * Geometry before colour.
     *
     * Each of these is a way for the sample to be measuring something other than the orb, and
     * each would otherwise surface as a wrong colour. The first run of this file did exactly
     * that: it reported #b56850 against a predicted #ce7161 and blamed the renderer, when the
     * engine had simply still been in WORLD and the sample had been mostly canvas.
     */
    for (const band of bands) {
        expect(
            band.count,
            `the ${band.name} band of the orb holds only ${band.count} pixels, so either the orb ` +
                "is not being drawn at the curated size or the key light has moved. Nothing " +
                "below can be attributed to a token from a sample this small.",
        ).toBeGreaterThanOrEqual(MIN_BAND);
    }
    expect(
        quantile(
            samples.map((sample) => deltaE00(sample.sampled, ground)),
            0.9,
        ),
        `nine tenths of the sample is the cleared canvas (${show(ground)}), so either the sample ` +
            "missed the orb or the readback returned nothing",
    ).toBeGreaterThan(TOLERANCE);

    /*
     * And the colour, per band.
     *
     * The statistic is the 25th percentile of each band rather than its mean, because the spoke
     * fan is drawn over an unknown share of the disc - see the note at the top of this file - and
     * that share is a fact about Indra's degree rather than about the colour pipeline. What is
     * claimed is that within each band of the key light there is a substantial population of
     * pixels publishing exactly what the tokens and the cues predict. Measured, that population
     * agrees to dE00 0.02, which is finer than one 8-bit step.
     */
    for (const band of bands) {
        expect(
            band.matching,
            `In the ${band.name} band of Indra's orb, three quarters of the ${band.count} sampled ` +
                `pixels are further than dE00 ${band.matching.toFixed(2)} from what the ${label} ` +
                "tokens and the renderer's own declared depth cues predict. The best pixel in " +
                `that band published ${band.best ? show(band.best.sampled) : "-"} where the model ` +
                `says ${band.best ? show(band.best.predicted) : "-"}. A gap of this size is a ` +
                "renderer-side colour defect rather than a palette one: check that " +
                "colorspace_fragment appears exactly once in each custom fragment shader in " +
                "engine.ts, that toLinearTriple in palette.ts has neither been removed nor " +
                "doubled, that outputColorSpace is still SRGBColorSpace, and that no uniform is " +
                "scaling the colour on its way through. For reference, an unencoded write would " +
                `read ${unencoded.toFixed(1)} against this same prediction.`,
        ).toBeLessThanOrEqual(TOLERANCE);
    }
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
