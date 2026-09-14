"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { probeCapability, recallRenderer, rememberRenderer } from "./capability";
import {
    DEFAULT_STATE,
    graphStateToQuery,
    parseGraphState,
    resolveInitialState,
    selectRegion as applyRegion,
    selectSubject as applySelection,
    setRenderer as applyRenderer,
    setView as applyView,
    type GraphRenderer,
    type GraphState,
    type GraphView,
} from "./modes";

/**
 * The one owner of graph state.
 *
 * Before this there were four writers - the URL, a capability probe, a stored preference and
 * a selection effect - each holding part of the answer and each free to overwrite the others
 * on any render. That is how a reader ended up in a view they had not chosen: two of them
 * disagreed and the last one to run won. Everything that can change the graph's state now
 * goes through this hook, and precedence between the sources is resolved exactly once, on
 * mount, rather than continuously by whichever effect fired last.
 *
 * The URL remains the record of state, because a view of the graph should be something you can
 * send to someone. But it is written from here, and read back only as the reader navigates -
 * never re-derived into a decision.
 */

export type FallbackReason = {
    reason: string;
    detail: string;
    at: number;
};

export type GraphStateHandle = {
    state: GraphState;
    /** Where the opening renderer came from. Reported, and useful when this misbehaves. */
    rendererSource: "url" | "remembered" | "capability";
    /** Set only where a real runtime failure forced the renderer to change. */
    fallback: FallbackReason | null;
    ready: boolean;

    setView: (view: GraphView) => void;
    setRenderer: (renderer: GraphRenderer) => void;
    select: (node: string | null) => void;
    selectRegion: (region: number | null) => void;
    setEndpoints: (from: string | null, to: string | null) => void;
    setQuery: (query: string | null) => void;
    /** Called by the renderer when it genuinely cannot continue. Never speculatively. */
    reportRendererFailure: (reason: string, detail: string) => void;
    dismissFallback: () => void;
};

export function useGraphState(): GraphStateHandle {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const [resolved, setResolved] = useState<{
        state: GraphState;
        rendererSource: "url" | "remembered" | "capability";
    } | null>(null);
    const [fallback, setFallback] = useState<FallbackReason | null>(null);
    /** Set once the opening state has actually been applied, not once it has been scheduled. */
    const applied = useRef(false);

    /*
     * Precedence is applied once.
     *
     * Deferred a tick so the canvas starts before the page is asked to re-render, and guarded
     * by a ref so a later navigation cannot send it round again. A classifier that re-runs is
     * a classifier that can change its mind about a reader who has since made a choice, and
     * that is the failure this file is arranged to prevent.
     */
    useEffect(() => {
        /*
         * Guarded on the work being *done*, not on it having been started.
         *
         * The first version set this ref before scheduling the deferred read. Under React's
         * development double-invoke the sequence is mount, cleanup, mount: the first mount set
         * the flag and scheduled, the cleanup cancelled the timer, and the second mount saw
         * the flag and returned without scheduling anything. So the resolution never ran and
         * the graph stayed on its defaults for good - which looked exactly like the renderer
         * in the URL being ignored, because it was.
         */
        if (applied.current) return;
        const timer = window.setTimeout(() => {
            applied.current = true;
            const url = new URLSearchParams(window.location.search);
            const report = probeCapability();
            const opening = resolveInitialState({
                url,
                remembered: recallRenderer(),
                capability: report.capability,
            });
            setResolved(opening);
            /* Where the device could not have drawn what was asked for, that is a fallback and
               it is announced. Where the device merely had no preference to override, it is
               not, and saying so would be noise. */
            if (
                opening.rendererSource === "capability" &&
                report.capability === "FLAT" &&
                opening.state.renderer === "2d"
            ) {
                setFallback({ reason: "capability", detail: report.reason, at: Date.now() });
            }
            router.replace(`${pathname}${graphStateToQuery(opening.state)}`, { scroll: false });
        }, 0);
        return () => window.clearTimeout(timer);
        // Mount only. This resolves precedence; it is not a subscription to anything.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /*
     * After the opening resolution, the URL is the state.
     *
     * Reading it back rather than keeping a second copy is what makes the browser's own back
     * button work, and leaves no second source that can drift out of agreement with it.
     */
    const state = useMemo(() => {
        if (!resolved) return DEFAULT_STATE;
        const params = new URLSearchParams(searchParams.toString());
        if (!params.has("view") && !params.has("renderer")) return resolved.state;
        return parseGraphState(params);
    }, [resolved, searchParams]);

    const write = useCallback(
        (next: GraphState) => {
            router.replace(`${pathname}${graphStateToQuery(next)}`, { scroll: false });
        },
        [router, pathname],
    );

    const setView = useCallback((view: GraphView) => write(applyView(state, view)), [state, write]);

    const setRenderer = useCallback(
        (renderer: GraphRenderer) => {
            // An explicit choice: remembered, and it clears any standing notice about a choice
            // that was made on the reader's behalf.
            rememberRenderer(renderer);
            setFallback(null);
            write(applyRenderer(state, renderer));
        },
        [state, write],
    );

    const select = useCallback(
        (node: string | null) => write(applySelection(state, node)),
        [state, write],
    );

    const selectRegion = useCallback(
        (region: number | null) => write(applyRegion(state, region)),
        [state, write],
    );

    const setEndpoints = useCallback(
        (from: string | null, to: string | null) => write({ ...state, view: "PATH", from, to }),
        [state, write],
    );

    const setQuery = useCallback(
        (query: string | null) => write({ ...state, query }),
        [state, write],
    );

    /**
     * The only path by which the product may change the renderer on its own.
     *
     * Called from a lost WebGL context or a failed renderer construction, and from nothing
     * else - not a frame-rate sample, not a selection, not a camera move, not a theme change.
     * The view is untouched: a reader looking at the world keeps looking at the world, drawn
     * the other way.
     */
    const reportRendererFailure = useCallback(
        (reason: string, detail: string) => {
            setFallback({ reason, detail, at: Date.now() });
            write(applyRenderer(state, "2d"));
        },
        [state, write],
    );

    const dismissFallback = useCallback(() => setFallback(null), []);

    return {
        state,
        rendererSource: resolved?.rendererSource ?? "capability",
        fallback,
        ready: resolved !== null,
        setView,
        setRenderer,
        select,
        selectRegion,
        setEndpoints,
        setQuery,
        reportRendererFailure,
        dismissFallback,
    };
}
