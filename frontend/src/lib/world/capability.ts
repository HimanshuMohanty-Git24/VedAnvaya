import type { Capability } from "./modes";

/**
 * What this machine can actually draw.
 *
 * Not a user-agent test. A user-agent string says what a browser calls itself, which has never
 * been a reliable statement about a GPU and is a worse one every year; the same phone model
 * ships with three different chips and the same laptop throttles differently on battery. What
 * is tested here is the thing that can be tested - whether a WebGL context opens at all, and
 * what the driver says it is.
 *
 * ## Two outcomes, not three
 *
 * A device whose browser opens a hardware WebGL context is drawn in 3D. A device that gets no
 * context, or one backed by a CPU rasteriser, is drawn flat, told so, and offered the spatial
 * view anyway. There is no middle tier. The version of this docstring that preceded this one
 * implied there was, and the rest of this comment is why there is not.
 *
 * ## The claim this file withdrew
 *
 * It returned a third class, `REDUCED_3D`, for any device reporting two gigabytes of memory or
 * less. It read as the careful middle of a three-way judgement and it decided nothing: the
 * only consumer of a `Capability` anywhere in `src/` is `defaultRendererFor` in `modes.ts`,
 * which answers "2d" for `FLAT` and "3d" for everything else. So the low-memory Android that
 * branch was written to protect was handed exactly the renderer a workstation gets, and had
 * been since the class was introduced. A tier no consumer distinguishes is not a conservative
 * default; it is a comment that happens to type-check.
 *
 * It is withdrawn rather than implemented because the signal underneath it cannot carry a
 * device tier. `navigator.deviceMemory` is Chromium-only and secure-context-only: every
 * browser on iOS is WebKit underneath, so the field is absent across the whole iPhone and iPad
 * fleet, and it is absent in Firefox. Where it is present it is quantised to a power of two
 * between 0.25 and 8, and it describes installed RAM - not the GPU, and not what is free. A
 * mid-range Android answers 4. A tier that fires on some cheap Androids and on no iPhone at
 * all is not a reduced-capability path; it is a Chromium path with a misleading name. If this
 * phase wants a smaller budget on small machines, the axis to key it on is one every device
 * reports honestly - viewport area - and not this.
 *
 * ## Why there is no frame-health watcher here either
 *
 * There was one: `watchFrameHealth`, four seconds of rAF intervals, a `badFrameMs` of 34, one
 * report after a sustained bad run. Its own docstring called it the correction to the guess
 * this file makes before anything is drawn. It had no caller in `src/`, so the guess was never
 * corrected, and it is deleted rather than wired up for two reasons.
 *
 * It watched the wrong clock. It sampled the page's rAF cadence, which every canvas on the
 * page shares and which is not the cadence the engine draws at - the homepage preview is
 * deliberately held to `maxFps: 30` while rAF keeps firing at the display rate. Meanwhile the
 * engine already times the gap between its own frames, separates the JavaScript half from the
 * GPU and vsync, and emits a mean and a p95 every second on `onStats`, which `world-view.tsx`
 * has been reading all along. A second and blinder sampler of the same quantity is not a
 * correction to anything.
 *
 * And there was nothing it was permitted to do with an answer. `modes.ts` leaves a frame
 * sample out of `TransitionReason` deliberately - "there is no reason for them to be here,
 * which is the same thing as saying they may not change this state" - and the engine's
 * `onLost` records the same rule from the other side: a frame-rate sample is not a failure. So
 * frame health may offer and may never decide, and an offer needs a reader-facing channel that
 * does not exist yet. If one is ever built it should read `EngineStats`, which the view already
 * receives, rather than start a second loop beside the one already running.
 */

export type CapabilityReport = {
    capability: Capability;
    webgl: boolean;
    renderer: string | null;
    /** True where the driver is a CPU rasteriser, which no amount of tuning will rescue. */
    software: boolean;
    /**
     * Reported, and deliberately not classified on - see the docstring above, where this field
     * is the reason the third capability class went away. It is still measured because it is
     * the first thing anyone triaging "the graph is slow on my phone" will ask for, and
     * because a figure that is recorded but not acted on is honest in a way that a tier keyed
     * on it was not.
     */
    deviceMemory: number | null;
    reason: string;
};

/*
 * Names a driver uses when it is not a GPU.
 *
 * This pattern carries the whole of the 2D decision for any device that does open a context,
 * so its gaps matter more than they look - `mesa offscreen` is here because llvmpipe does not
 * always name itself. It is also only as good as the string it is handed:
 * `WEBGL_debug_renderer_info` is absent or masked under fingerprinting protection, and the
 * fallback `gl.RENDERER` is a generic constant - "WebKit WebGL" - that no pattern here can
 * match. So this fires when a driver is willing to name itself and is quietly false when it is
 * not, which errs towards giving a device 3D.
 */
const SOFTWARE = /swiftshader|software|llvmpipe|mesa offscreen|microsoft basic render/i;

/*
 * Server-side rendering has measured nothing, says so, and still claims FULL_3D.
 *
 * FLAT would be the modest-looking answer and the wrong one: precedence is resolved on the
 * client, so pre-committing the markup to the flat renderer would show every reader a planar
 * graph for one paint before the real answer arrived. Note that `webgl` is false here while
 * `capability` is FULL_3D, which is the one internally inconsistent row this type can hold; a
 * consumer branching on `webgl` alone must guard on `window` first, as `world-preview.tsx`
 * does.
 */
const SERVER_REPORT: CapabilityReport = {
    capability: "FULL_3D",
    webgl: false,
    renderer: null,
    software: false,
    deviceMemory: null,
    reason: "not measured on the server",
};

/*
 * Why, in the reader's words. A fragment, not a sentence.
 *
 * The only reasons a reader ever sees are these two: `graph-shell.tsx` shows the notice as
 * `Drawing this flat: {detail}.` for a FLAT capability and for nothing else, so each must stay
 * lower-case, must not bring its own full stop, and must complete that clause. The notice
 * beside them already offers the spatial view, so the job of this text is not to defend the
 * decision - it is to tell someone whether the cause is at their end and worth fixing. Both of
 * these are, which is why both name the setting rather than the symptom.
 */
const NO_CONTEXT =
    "this browser would not open a 3D canvas - WebGL may be turned off, or blocked by an extension";
const RASTERISER =
    "this device is drawing with the processor rather than the graphics card, which usually means hardware acceleration is switched off in the browser's settings";

/*
 * Measured once per page, then remembered.
 *
 * The answer is a fact about the machine and cannot change while the page is open, and the
 * probe is not free: it builds a canvas and a real WebGL context. There are two callers -
 * `graph-state.ts` on mount and `world-preview.tsx` in a lazy `useState` initialiser - and
 * React's development double-invoke can run each of them twice, so an unmemoised probe opens
 * up to four contexts against a browser cap that is typically eight to sixteen. Every one of
 * them is explicitly released below, so that was churn rather than a leak; this makes it one
 * context.
 *
 * Only ever populated in the browser, so a server module instance cannot poison a client one.
 */
let cached: CapabilityReport | null = null;

export function probeCapability(): CapabilityReport {
    if (typeof window === "undefined") return SERVER_REPORT;
    cached ??= measure();
    return cached;
}

function measure(): CapabilityReport {
    const canvas = document.createElement("canvas");
    let gl: WebGLRenderingContext | WebGL2RenderingContext | null = null;
    try {
        gl = (canvas.getContext("webgl2") ??
            canvas.getContext("webgl")) as WebGL2RenderingContext | null;
    } catch {
        gl = null;
    }

    const deviceMemory =
        typeof (navigator as unknown as { deviceMemory?: number }).deviceMemory === "number"
            ? (navigator as unknown as { deviceMemory: number }).deviceMemory
            : null;

    if (!gl) {
        return {
            capability: "FLAT",
            webgl: false,
            renderer: null,
            software: false,
            deviceMemory,
            reason: NO_CONTEXT,
        };
    }

    let renderer: string | null = null;
    try {
        const info = gl.getExtension("WEBGL_debug_renderer_info");
        renderer = info
            ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL))
            : String(gl.getParameter(gl.RENDERER));
    } catch {
        renderer = null;
    }
    /* Released on the one path that created a context, before the branches rather than inside
       either of them: browsers cap how many a page may hold and evict the oldest, and the
       engine is about to ask for the one that matters. Releasing inside a branch is how the
       cap gets reached by whichever device took the other. */
    gl.getExtension("WEBGL_lose_context")?.loseContext();

    const software = renderer ? SOFTWARE.test(renderer) : false;
    if (software) {
        return {
            capability: "FLAT",
            webgl: true,
            renderer,
            software: true,
            deviceMemory,
            reason: RASTERISER,
        };
    }

    return {
        capability: "FULL_3D",
        webgl: true,
        renderer,
        software: false,
        deviceMemory,
        reason: "measured on this device",
    };
}

const STORAGE_KEY = "vedanvaya.graph.renderer";

/**
 * The reader's last explicit renderer choice.
 *
 * Only the renderer is remembered, never the view. Which subject someone was looking at last
 * time is not a preference, and restoring it would be the product deciding where a new visit
 * begins; how they prefer the graph drawn is exactly a preference.
 */
export function rememberRenderer(renderer: "3d" | "2d") {
    try {
        window.localStorage.setItem(STORAGE_KEY, renderer);
    } catch {
        // Private browsing, or storage disabled. Not remembering is not an error.
    }
}

export function recallRenderer(): "3d" | "2d" | null {
    try {
        const value = window.localStorage.getItem(STORAGE_KEY);
        return value === "3d" || value === "2d" ? value : null;
    } catch {
        return null;
    }
}
