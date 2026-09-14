import type { Capability } from "./modes";

/**
 * What this machine can actually draw.
 *
 * Not a user-agent test. A user-agent string says what a browser calls itself, which has never
 * been a reliable statement about a GPU and is a worse one every year; the same phone model
 * ships with three different chips and the same laptop throttles differently on battery. What
 * is tested here is the thing that matters - whether a WebGL context exists, what the driver
 * says it is, and how long a frame takes - and the last of those is measured on the real scene
 * rather than guessed from the first two.
 *
 * The classification is deliberately conservative in one direction only: it will send a
 * borderline machine to a mode that works, and it always says so and offers the other one.
 */

export type CapabilityReport = {
    capability: Capability;
    webgl: boolean;
    renderer: string | null;
    /** True where the driver is a CPU rasteriser, which no amount of tuning will rescue. */
    software: boolean;
    deviceMemory: number | null;
    reason: string;
};

const SOFTWARE = /swiftshader|software|llvmpipe|microsoft basic render/i;

export function probeCapability(): CapabilityReport {
    if (typeof window === "undefined") {
        return {
            capability: "FULL_3D",
            webgl: false,
            renderer: null,
            software: false,
            deviceMemory: null,
            reason: "not measured on the server",
        };
    }

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
            reason: "this browser did not provide a WebGL context",
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
    // Release the probe context immediately: browsers cap how many a page may hold, and the
    // engine is about to ask for the one that matters.
    gl.getExtension("WEBGL_lose_context")?.loseContext();

    const software = renderer ? SOFTWARE.test(renderer) : false;
    if (software) {
        return {
            capability: "FLAT",
            webgl: true,
            renderer,
            software: true,
            deviceMemory,
            reason: "this device is rendering in software rather than on a GPU",
        };
    }

    /* Under 2 GB is the one hardware figure worth acting on: the artifact and its buffers are
       tens of megabytes, and a device that reports this little has usually reported it
       honestly. Absent, the field simply is not consulted. */
    if (deviceMemory !== null && deviceMemory <= 2) {
        return {
            capability: "REDUCED_3D",
            webgl: true,
            renderer,
            software: false,
            deviceMemory,
            reason: "this device reports limited memory",
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

/**
 * Watch the real frame interval and report when it is persistently bad.
 *
 * The probe above is a guess made before anything is drawn; this is the correction. It reports
 * once, after a sustained run of slow frames, not on the first stutter - a single long frame
 * happens whenever a texture uploads or another tab wakes up, and offering to change rendering
 * mode because of one is worse than saying nothing.
 */
export function watchFrameHealth(
    onStruggling: (medianMs: number) => void,
    {
        sampleMs = 4000,
        badFrameMs = 34,
        badShare = 0.6,
    }: { sampleMs?: number; badFrameMs?: number; badShare?: number } = {},
) {
    const intervals: number[] = [];
    let last = 0;
    let raf = 0;
    let done = false;
    const started = performance.now();

    const tick = (now: number) => {
        if (done) return;
        if (last) intervals.push(now - last);
        last = now;
        if (now - started < sampleMs) {
            raf = requestAnimationFrame(tick);
            return;
        }
        done = true;
        if (intervals.length < 20) return;
        const bad = intervals.filter((ms) => ms > badFrameMs).length;
        if (bad / intervals.length < badShare) return;
        const sorted = [...intervals].sort((a, b) => a - b);
        onStruggling(sorted[Math.floor(sorted.length / 2)]);
    };
    raf = requestAnimationFrame(tick);

    return () => {
        done = true;
        cancelAnimationFrame(raf);
    };
}

const STORAGE_KEY = "vedanvaya.graph.mode";

/** The reader's last explicit choice, which always outranks anything measured. */
export function rememberMode(mode: string) {
    try {
        window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
        // Private browsing, or storage disabled. Not remembering is not an error.
    }
}

export function recallMode(): string | null {
    try {
        return window.localStorage.getItem(STORAGE_KEY);
    } catch {
        return null;
    }
}
