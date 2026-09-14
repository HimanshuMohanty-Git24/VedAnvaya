import { afterEach, describe, expect, it, vi } from "vitest";
import { defaultRendererFor } from "@/lib/world/modes";

/**
 * What the device classifier is allowed to claim.
 *
 * These assertions are deliberately written through `defaultRendererFor` rather than against
 * the `capability` field, because the defect they exist to prevent was invisible at that field.
 * The classifier returned a third class for a low-memory device and every reader of it treated
 * that class as the first, so the only test that could have caught it is one that asks what the
 * reader actually gets drawn. A claim about a capability is worth nothing until it changes a
 * renderer.
 *
 * The probe memoises, so each case re-imports the module. That is the point of the memo and it
 * is asserted below; resetting it through a production-only export would have meant shipping
 * an API that exists for this file.
 */

/** The enum value `WEBGL_debug_renderer_info` hands back for the unmasked renderer. */
const UNMASKED = 0x9246;
const GENERIC_RENDERER = 0x1f01;

type Probe = typeof import("@/lib/world/capability");

/**
 * Stand in for a GPU that names itself.
 *
 * `renderer: null` models the case that is easy to forget and common in the wild - a browser
 * that withholds `WEBGL_debug_renderer_info`, leaving only the generic `gl.RENDERER` constant.
 */
function installGpu(renderer: string | null) {
    const contexts: string[] = [];
    const released = { count: 0 };
    const gl = {
        getExtension(name: string) {
            if (name === "WEBGL_debug_renderer_info") {
                return renderer === null ? null : { UNMASKED_RENDERER_WEBGL: UNMASKED };
            }
            if (name === "WEBGL_lose_context") {
                return {
                    loseContext() {
                        released.count += 1;
                    },
                };
            }
            return null;
        },
        getParameter(parameter: number) {
            return parameter === UNMASKED ? renderer : "WebKit WebGL";
        },
        RENDERER: GENERIC_RENDERER,
    };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(((kind: string) => {
        contexts.push(kind);
        return kind === "webgl2" ? gl : null;
    }) as never);
    return { contexts, released };
}

function installNoWebGL() {
    const contexts: string[] = [];
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(((kind: string) => {
        contexts.push(kind);
        return null;
    }) as never);
    return { contexts };
}

function setDeviceMemory(gigabytes: number | null) {
    if (gigabytes === null) {
        Reflect.deleteProperty(navigator, "deviceMemory");
        return;
    }
    Object.defineProperty(navigator, "deviceMemory", {
        configurable: true,
        value: gigabytes,
    });
}

async function freshProbe(): Promise<Probe> {
    vi.resetModules();
    return import("@/lib/world/capability");
}

afterEach(() => {
    vi.restoreAllMocks();
    setDeviceMemory(null);
});

describe("what the classifier sends to 2D", () => {
    it("keeps a hardware GPU in 3D however little memory the device reports", async () => {
        /* The withdrawn `REDUCED_3D` class. A device answering 1 GB used to be classified apart
           and then drawn identically, so the honest position is that it is not classified apart
           at all - and this is the assertion that fails if a third class returns without a
           consumer to give it meaning. 0.25 is the floor the Device Memory API clamps to. */
        for (const gigabytes of [0.25, 0.5, 1, 2]) {
            setDeviceMemory(gigabytes);
            installGpu("Apple M2");
            const { probeCapability } = await freshProbe();
            const report = probeCapability();
            expect(report.deviceMemory, "the figure is still reported").toBe(gigabytes);
            expect(
                defaultRendererFor(report.capability),
                `${gigabytes} GB was sent to a different renderer`,
            ).toBe("3d");
            vi.restoreAllMocks();
        }
    });

    it("sends every driver that admits to being a rasteriser", async () => {
        for (const driver of [
            "Google SwiftShader",
            "llvmpipe (LLVM 15.0.7, 256 bits)",
            "Mesa OffScreen",
            "Microsoft Basic Render Driver",
            "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))",
        ]) {
            installGpu(driver);
            const { probeCapability } = await freshProbe();
            const report = probeCapability();
            expect(report.software, `${driver} was not recognised`).toBe(true);
            expect(defaultRendererFor(report.capability)).toBe("2d");
            vi.restoreAllMocks();
        }
    });

    it("sends a browser that will not open a context", async () => {
        installNoWebGL();
        const { probeCapability } = await freshProbe();
        const report = probeCapability();
        expect(report.webgl).toBe(false);
        expect(defaultRendererFor(report.capability)).toBe("2d");
    });

    it("gives 3D to a browser that withholds its renderer string", async () => {
        /* Fingerprinting protection masks the driver name, and the generic constant left behind
           cannot match a software pattern. Erring towards 3D there is the intended direction,
           so it is pinned rather than left to be discovered as a regression. */
        installGpu(null);
        const { probeCapability } = await freshProbe();
        const report = probeCapability();
        expect(report.software).toBe(false);
        expect(defaultRendererFor(report.capability)).toBe("3d");
    });
});

describe("the contexts the probe opens", () => {
    it("releases the one it opened", async () => {
        const gpu = installGpu("Apple M2");
        const { probeCapability } = await freshProbe();
        probeCapability();
        expect(gpu.released.count).toBe(1);
    });

    it("opens one context however many callers ask", async () => {
        /* Two call sites, each able to run twice under React's development double-invoke,
           against a browser cap that is typically eight to sixteen live contexts. */
        const gpu = installGpu("Apple M2");
        const { probeCapability } = await freshProbe();
        const first = probeCapability();
        for (let i = 0; i < 5; i += 1) probeCapability();
        expect(gpu.contexts.filter((kind) => kind === "webgl2")).toHaveLength(1);
        expect(probeCapability(), "the same report, not an equal one").toBe(first);
    });
});

describe("the reason a reader is shown", () => {
    /*
     * `graph-shell.tsx` renders these as `Drawing this flat: {detail}.` and supplies the frame
     * itself. That coupling is across a file this module cannot see, so it is pinned here: a
     * reason that capitalised itself or carried its own stop would read as a sentence spliced
     * into the middle of another one.
     */
    it("completes the clause the notice puts around it", async () => {
        for (const install of [() => installNoWebGL(), () => installGpu("Google SwiftShader")]) {
            install();
            const { probeCapability } = await freshProbe();
            const { reason } = probeCapability();
            expect(reason, "starts a new sentence inside one").toBe(
                reason.charAt(0).toLowerCase() + reason.slice(1),
            );
            expect(reason.endsWith("."), "brings its own full stop").toBe(false);
            expect(reason.length, "too terse to act on").toBeGreaterThan(20);
            vi.restoreAllMocks();
        }
    });
});
