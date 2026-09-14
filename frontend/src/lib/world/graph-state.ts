"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { probeCapability, recallRenderer, rememberRenderer } from "./capability";
import {
    DEFAULT_STATE,
    graphStateToQuery,
    isReaderIntent,
    parseGraphState,
    resolveInitialState,
    returnToWorld as applyReturn,
    selectRegion as applyRegion,
    selectSubject as applySelection,
    setRenderer as applyRenderer,
    setView as applyView,
    type GraphRenderer,
    type GraphState,
    type GraphView,
    type TransitionReason,
} from "./modes";

/**
 * The one owner of graph state.
 *
 * ## What was wrong, precisely
 *
 * The previous version already had one owner and still lost the reader's place, so "one owner"
 * was not the whole of the problem. Two things were.
 *
 * The first is that the owner read its own state back out of the URL on every render and every
 * mutator computed the next state from that. `router.replace` is a transition: `useSearchParams`
 * does not report the new query until it commits. So two writes inside one commit window both
 * read the state from *before* either of them, and the second silently discarded the first.
 * Selecting a subject and then touching anything else lost the selection - not always, which
 * is what made it look like the graph resetting itself at random.
 *
 * The authority is now a ref, updated synchronously inside the write. Two writes in one window
 * compose instead of racing. The URL is still written from it, because a view of the graph
 * should be something you can send to someone, and it is still read back - but only to notice
 * that the reader moved through history, never to re-derive a decision.
 *
 * The second is that a write did not have to say why it was happening. `TransitionReason` is
 * now a required parameter and a closed union, and only the reader's half of it may move the
 * semantic axis. A boot, a history navigation and a lost WebGL context are the only causes
 * that are not the reader, they are each allowed exactly what they need, and anything else
 * reaching for `view` is refused and recorded. There is no reason in the union for a physics
 * tick, a camera move, a hover, a settling simulation or a theme change, which is the same
 * thing as saying none of them can do this.
 */

export type FallbackReason = {
    reason: string;
    detail: string;
    at: number;
};

/**
 * One line of the semantic-state trace.
 *
 * Kept in production rather than behind a development flag. It is a bounded ring of plain
 * objects and costs nothing, and the alternative is that the one bug this file exists to
 * prevent becomes unobservable in exactly the build a reader is running. The soak test asserts
 * against it, and so can a person with the console open.
 */
export type GraphTransition = {
    at: number;
    from: GraphView;
    to: GraphView;
    reason: TransitionReason;
    node: string | null;
    renderer: GraphRenderer;
    url: string;
    /** Set where a cause reached for something it was not entitled to change. A defect. */
    refused?: string;
};

const TRACE_LIMIT = 64;

export type GraphStateHandle = {
    state: GraphState;
    /** Where the opening renderer came from. Reported, and useful when this misbehaves. */
    rendererSource: "url" | "remembered" | "capability";
    /** Set only where a real runtime failure forced the renderer to change. */
    fallback: FallbackReason | null;
    ready: boolean;
    /** Most recent first. Read by the persistence soak test and by anyone debugging this. */
    transitions: GraphTransition[];

    setView: (view: GraphView, reason: TransitionReason) => void;
    /** Step back out to the whole corpus. The only thing that may leave Focus. */
    returnToWorld: (reason: TransitionReason) => void;
    setRenderer: (renderer: GraphRenderer, reason: TransitionReason) => void;
    select: (node: string | null, reason: TransitionReason) => void;
    selectRegion: (region: number | null, reason: TransitionReason) => void;
    setEndpoints: (from: string | null, to: string | null, reason: TransitionReason) => void;
    setQuery: (query: string | null, reason: TransitionReason) => void;
    /** Called by the renderer when it genuinely cannot continue. Never speculatively. */
    reportRendererFailure: (reason: string, detail: string) => void;
    dismissFallback: () => void;
};

export function useGraphState(): GraphStateHandle {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    /**
     * The state, twice: once for rendering and once for writing.
     *
     * The duplication is deliberate and it is the whole fix. A mutator has to see the result of
     * the mutator that ran a microsecond ago - two changes inside one commit window must
     * compose rather than the second discarding the first - and React state cannot offer that,
     * because it does not update until the next render. A ref can.
     *
     * But a ref must not be *read during render*, and not merely because a lint rule says so:
     * a render that reads a value React does not know changed can paint a state that was never
     * committed. So the two have distinct jobs and the boundary is strict. `rendered` is what
     * the component tree sees. `authority` is what a mutator computes from, and it is touched
     * only inside callbacks and effects, which is where refs are legitimate.
     */
    const [rendered, setRendered] = useState<GraphState>(DEFAULT_STATE);
    const authority = useRef<GraphState>(DEFAULT_STATE);
    /** The query we last wrote, so the reader moving through history can be told apart. */
    const written = useRef<string | null>(null);
    const [transitions, setTransitions] = useState<GraphTransition[]>([]);
    const trace = useRef<GraphTransition[]>([]);

    const [rendererSource, setRendererSource] = useState<"url" | "remembered" | "capability">(
        "capability",
    );
    const [fallback, setFallback] = useState<FallbackReason | null>(null);
    const [ready, setReady] = useState(false);
    /** Set once the opening state has actually been applied, not once it has been scheduled. */
    const applied = useRef(false);
    /**
     * Set once the opening state has been *committed*, which is later than `applied`.
     *
     * A separate ref rather than reusing `applied`, and not for tidiness: `applied` is set
     * before the commit so that React's development double-invoke cannot schedule the
     * resolution twice, so by the time `commit` runs it is already true. Asking it whether the
     * boot has happened would always be answered yes, and the boot would be refused - which is
     * the defect this pair of flags exists to keep apart. Two questions, two answers.
     */
    const booted = useRef(false);

    const record = useCallback((entry: GraphTransition) => {
        trace.current = [entry, ...trace.current].slice(0, TRACE_LIMIT);
        setTransitions(trace.current);
        if (typeof window !== "undefined") {
            (window as unknown as Record<string, unknown>).__vedaGraphTrace = trace.current;
        }
    }, []);

    /**
     * Apply a state change, or refuse it.
     *
     * Everything that can move this state goes through here, so the invariant is stated once:
     * a cause that is not the reader may not change what is being explored. Refusing rather
     * than throwing in production is deliberate - a reader mid-session is better served by a
     * graph that ignores an illegitimate transition than by one that stops - but the refusal is
     * recorded, and in development it is loud, because a refusal means a caller exists that
     * should not.
     */
    const commit = useCallback(
        (next: GraphState, reason: TransitionReason) => {
            const current = authority.current;
            let applying = next;
            let refused: string | undefined;

            /*
             * Only the reader may *change* the view. The boot may *establish* it.
             *
             * The distinction is not a loophole, and leaving it out was a defect that a colour
             * test found by accident. `boot:resolve-precedence` is the one cause with no prior
             * state to preserve: it runs once, against `DEFAULT_STATE`, and its whole job is to
             * say what the URL, a remembered preference and the device add up to. Refusing it
             * meant that `?view=focus&node=INDRA` resolved to FOCUS and was then forced back to
             * WORLD before the first paint - a deep link into a subject landing on the whole
             * corpus, which is the exact failure this file exists to prevent, reintroduced by
             * the guard against it.
             *
             * Every other system cause is still refused. A lost context may change the renderer
             * and nothing else; a history navigation is adopted in its own effect, because
             * arriving somewhere the browser already went is not this function's business.
             */
            const establishing = reason === "boot:resolve-precedence" && !booted.current;
            if (!isReaderIntent(reason) && !establishing && next.view !== current.view) {
                refused = `${reason} tried to change the view from ${current.view} to ${next.view}`;
                applying = { ...next, view: current.view };
            }

            const query = graphStateToQuery(applying);
            /*
             * A write that changes nothing is dropped - except the boot, which is always
             * recorded even when it agrees with the URL it read.
             *
             * "The opening state was resolved and matched" and "the resolution never ran" are
             * different facts, and a trace that cannot tell them apart is the wrong tool for the
             * bug it was added to catch. It also makes an invariant the soak test relies on
             * actually true: the trace holds at least the opening transition, so an assertion
             * over it cannot pass by reading an empty array.
             */
            if (
                !establishing &&
                applying.view === current.view &&
                query === graphStateToQuery(current) &&
                !refused
            ) {
                return;
            }

            authority.current = applying;
            setRendered(applying);
            written.current = query.slice(1);
            if (reason === "boot:resolve-precedence") booted.current = true;
            record({
                at: Date.now(),
                from: current.view,
                to: applying.view,
                reason,
                node: applying.node,
                renderer: applying.renderer,
                url: `${pathname}${query}`,
                ...(refused ? { refused } : {}),
            });
            if (refused && process.env.NODE_ENV !== "production") {
                // Not thrown: throwing here would take the graph down in a development session
                // for a transition that has already been correctly refused. It is an error in
                // the console because it means a call site needs deleting.
                console.error(`[graph-state] refused a transition. ${refused}`);
            }
            router.replace(`${pathname}${query}`, { scroll: false });
        },
        [pathname, record, router],
    );

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
            setRendererSource(opening.rendererSource);
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
            setReady(true);
            commit(opening.state, "boot:resolve-precedence");
        }, 0);
        return () => window.clearTimeout(timer);
        // Mount only. This resolves precedence; it is not a subscription to anything.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /*
     * The reader moved through history, or arrived from a link.
     *
     * This is the only thing the URL is still read for. Anything the query says that we did not
     * just write is somebody else navigating - the back button, a link from the sidebar, a
     * pasted address - and it is adopted whole, because the alternative is fighting the browser
     * over its own history. Anything the query says that we *did* write is our own echo and is
     * ignored, which is what stops the loop the previous version had.
     */
    useEffect(() => {
        if (!applied.current) return;
        const incoming = searchParams.toString();
        if (incoming === written.current) return;
        const parsed = parseGraphState(new URLSearchParams(incoming));
        const current = authority.current;
        authority.current = parsed;
        setRendered(parsed);
        written.current = incoming;
        record({
            at: Date.now(),
            from: current.view,
            to: parsed.view,
            reason: "history:navigated",
            node: parsed.node,
            renderer: parsed.renderer,
            url: `${pathname}?${incoming}`,
        });
    }, [searchParams, pathname, record]);

    const setView = useCallback(
        (view: GraphView, reason: TransitionReason) =>
            commit(applyView(authority.current, view), reason),
        [commit],
    );

    const returnToWorld = useCallback(
        (reason: TransitionReason) => commit(applyReturn(authority.current), reason),
        [commit],
    );

    const setRenderer = useCallback(
        (renderer: GraphRenderer, reason: TransitionReason) => {
            // An explicit choice: remembered, and it clears any standing notice about a choice
            // that was made on the reader's behalf.
            rememberRenderer(renderer);
            setFallback(null);
            commit(applyRenderer(authority.current, renderer), reason);
        },
        [commit],
    );

    const select = useCallback(
        (node: string | null, reason: TransitionReason) =>
            commit(applySelection(authority.current, node), reason),
        [commit],
    );

    const selectRegion = useCallback(
        (region: number | null, reason: TransitionReason) =>
            commit(applyRegion(authority.current, region), reason),
        [commit],
    );

    const setEndpoints = useCallback(
        (from: string | null, to: string | null, reason: TransitionReason) =>
            commit({ ...authority.current, view: "PATH", from, to }, reason),
        [commit],
    );

    const setQuery = useCallback(
        (query: string | null, reason: TransitionReason) =>
            commit({ ...authority.current, query }, reason),
        [commit],
    );

    /**
     * The only path by which the product may change the renderer on its own.
     *
     * Called from a lost WebGL context or a failed renderer construction, and from nothing
     * else - not a frame-rate sample, not a selection, not a camera move, not a theme change.
     * The view is untouched, and now cannot be touched: `fallback:renderer-lost` is not a
     * reader intent, so `commit` would refuse a view change even if one were computed here. A
     * reader looking at one subject keeps looking at it, drawn the other way.
     */
    const reportRendererFailure = useCallback(
        (reason: string, detail: string) => {
            setFallback({ reason, detail, at: Date.now() });
            commit(applyRenderer(authority.current, "2d"), "fallback:renderer-lost");
        },
        [commit],
    );

    const dismissFallback = useCallback(() => setFallback(null), []);

    return {
        state: rendered,
        rendererSource,
        fallback,
        ready,
        transitions,
        setView,
        returnToWorld,
        setRenderer,
        select,
        selectRegion,
        setEndpoints,
        setQuery,
        reportRendererFailure,
        dismissFallback,
    };
}
