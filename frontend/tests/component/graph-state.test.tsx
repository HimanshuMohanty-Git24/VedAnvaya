import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The state owner, exercised through the hook rather than through its pure parts.
 *
 * `tests/unit/mode-stability.test.ts` covers the reducer exhaustively and every one of its
 * assertions passed while the release blocker was live, because the reducer was never where the
 * defect was. It was in the wiring: which call site fired, what it read, and what the boot did
 * before anything was on screen. So this file mounts the hook, drives a real router mock and
 * asserts what actually lands.
 *
 * The first test here is a regression for a defect that shipped inside the fix for the defect.
 * `commit` refuses a view change from any cause that is not the reader, which is the whole
 * invariant - and `boot:resolve-precedence` is not a reader, so a deep link into a subject was
 * resolved to FOCUS and then forced back to WORLD before the first paint. It was found by a
 * colour test noticing that the engine never left WORLD, which is a long way from where it was
 * introduced, and nothing in the reducer suite could have seen it.
 */

/** The query the hook last wrote, so a test can read what it did rather than what it holds. */
let written: string[] = [];
let search = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        replace: (url: string) => {
            written.push(url);
            /* The real router updates `useSearchParams` only when the transition commits; the
               hook is built for that and reads the URL back solely to notice a history move. A
               test that echoed it synchronously would be testing a router nobody ships. */
        },
        push: vi.fn(),
    }),
    usePathname: () => "/graph",
    useSearchParams: () => search,
}));

/* The capability probe builds a WebGL context, which jsdom does not have. FULL_3D keeps the
   opening renderer out of the way of what these tests are about. */
vi.mock("@/lib/world/capability", () => ({
    probeCapability: () => ({
        capability: "FULL_3D",
        webgl: true,
        renderer: "test",
        software: false,
        deviceMemory: null,
        reason: "mocked",
    }),
    recallRenderer: () => null,
    rememberRenderer: vi.fn(),
}));

const load = async () => (await import("@/lib/world/graph-state")).useGraphState;

const at = (query: string) => {
    search = new URLSearchParams(query);
    window.history.replaceState(null, "", `/graph?${query}`);
};

beforeEach(() => {
    written = [];
    vi.resetModules();
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
});

/** The opening resolution is deferred a tick so the canvas starts before a re-render. */
const settle = async () => {
    await act(async () => {
        vi.advanceTimersByTime(1);
    });
};

describe("the opening state", () => {
    it("establishes a deep-linked Focus rather than refusing it", async () => {
        /*
         * The regression. A deep link naming a subject is the shape every link into this graph
         * takes from the rest of the product, and landing it on the whole corpus is the exact
         * complaint the phase exists to answer.
         */
        at("view=focus&renderer=3d&node=VG%3ADEVATA%3AINDRAH");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        expect(result.current.state.view).toBe("FOCUS");
        expect(result.current.state.node).toBe("VG:DEVATA:INDRAH");
        expect(result.current.transitions[0]?.refused).toBeUndefined();
    });

    it("establishes a deep-linked Path", async () => {
        at("view=path&renderer=3d&from=VG%3ADEVATA%3AAGNIH&to=VG%3ADEVATA%3AINDRAH");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        expect(result.current.state.view).toBe("PATH");
        expect(result.current.transitions[0]?.refused).toBeUndefined();
    });

    it("still opens a bare link on the world", async () => {
        at("");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        expect(result.current.state.view).toBe("WORLD");
        expect(result.current.state.node).toBeNull();
    });

    it("writes both axes back, so the link it produces means what produced it", async () => {
        at("node=VG%3ADEVATA%3AINDRAH");
        const useGraphState = await load();
        renderHook(() => useGraphState());
        await settle();

        expect(written.at(-1)).toContain("view=focus");
        expect(written.at(-1)).toContain("renderer=3d");
    });
});

describe("what may move the view once the reader is looking", () => {
    it("refuses a renderer failure that reaches for the view", async () => {
        /*
         * The invariant, from the side that matters. A lost context must change the renderer and
         * nothing else: a reader studying one subject keeps studying it, drawn the other way.
         */
        at("view=focus&renderer=3d&node=VG%3ADEVATA%3AINDRAH");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        await act(async () => {
            result.current.reportRendererFailure("context-lost", "the driver gave up");
        });

        expect(result.current.state.view).toBe("FOCUS");
        expect(result.current.state.node).toBe("VG:DEVATA:INDRAH");
        expect(result.current.state.renderer).toBe("2d");
    });

    it("composes two changes made inside one commit window", async () => {
        /*
         * The race the authority ref exists for. `router.replace` is a transition, so
         * `useSearchParams` does not report the new query until it lands; two mutators reading
         * the rendered state would both compute from before either of them and the second would
         * discard the first. Here the selection must survive the renderer change that follows it
         * without waiting for anything.
         */
        at("view=world&renderer=3d");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        await act(async () => {
            result.current.select("VG:DEVATA:INDRAH", "reader:select-subject");
            result.current.setRenderer("2d", "reader:renderer-control");
        });

        expect(result.current.state.view).toBe("FOCUS");
        expect(result.current.state.node).toBe("VG:DEVATA:INDRAH");
        expect(result.current.state.renderer).toBe("2d");
        expect(written.at(-1)).toContain("view=focus");
        expect(written.at(-1)).toContain("renderer=2d");
    });

    it("leaves Focus only when the reader asks", async () => {
        at("view=focus&renderer=3d&node=VG%3ADEVATA%3AINDRAH");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        /* Clearing the subject is not leaving the view. This is the transition whose conflation
           let a stray tap on empty canvas discard a Focus session. */
        await act(async () => {
            result.current.select(null, "reader:select-subject");
        });
        expect(result.current.state.view).toBe("FOCUS");

        await act(async () => {
            result.current.returnToWorld("reader:view-control");
        });
        expect(result.current.state.view).toBe("WORLD");
        expect(result.current.state.node).toBeNull();
    });

    it("records every transition with the cause that asked for it", async () => {
        at("view=world&renderer=3d");
        const useGraphState = await load();
        const { result } = renderHook(() => useGraphState());
        await settle();

        await act(async () => {
            result.current.select("VG:DEVATA:INDRAH", "reader:select-subject");
        });

        const reasons = result.current.transitions.map((entry) => entry.reason);
        expect(reasons).toContain("reader:select-subject");
        expect(reasons).toContain("boot:resolve-precedence");
        /* An empty trace would let the soak test's assertions pass by reading nothing, which is
           the failure mode that suite keeps a guard for. */
        expect(result.current.transitions.length).toBeGreaterThan(1);
        expect(result.current.transitions.every((entry) => !entry.refused)).toBe(true);
    });
});
