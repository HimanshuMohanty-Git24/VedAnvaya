"use client";

import clsx from "clsx";
import { useCallback, useEffect, useRef, useState } from "react";
import {
    ASK_EXAMPLES,
    ASK_MODES,
    ASK_QUESTION_LIMIT,
    ASK_VEDA_SCOPES,
    AskError,
    elapsedCopy,
    fetchAskHealth,
    postAsk,
    waitNoteFor,
    type AskConversationTurn,
    type AskMode,
    type AskResponse,
    type AskVedaScope,
} from "@/lib/ask";
import { extractCitedIds } from "@/lib/ask-citations";
import { AskAnswer } from "./ask-answer";
import { AskEvidenceDrawer } from "./ask-evidence-drawer";
import { ThreadOfInquiry } from "./thread-of-inquiry";

/**
 * Ask, as one state machine rather than as six booleans.
 *
 * The states below are the ones the transport can actually produce. There is deliberately no
 * COMPOSING state: typing is not a state of the request, and modelling it as one was how the
 * previous version ended up asking `!result && !pending && !error` in three places to decide
 * whether the examples should show.
 *
 * ## What changed about waiting, and why it mattered
 *
 * The previous version showed three phases that advanced on a timer at 0, 0.9 and 2.6
 * seconds. Measured synthesis latency on this backend runs from 29.7s to 248.7s with a
 * median near 106s. So every real request reached the last phase, "Synthesising the answer",
 * about two and a half seconds in, and then sat on it, unchanged, for another hundred
 * seconds. The phases were not a simplification of what the backend was doing; they were
 * three sentences the frontend made up, and they were wrong on every request that had ever
 * been made. What replaces them says the one thing that is actually known - how long it has
 * been - and lets the copy under it get more informative as that number grows.
 */
type AskState =
    | { kind: "IDLE" }
    | { kind: "WAITING" }
    | { kind: "ANSWER"; result: AskResponse }
    | { kind: "ERROR"; error: AskError }
    | { kind: "CANCELLED" };

export function AskExperience({
    initialQuestion = "",
    passageContext: initialPassage = null,
    entityContext: initialEntity = null,
}: {
    initialQuestion?: string;
    passageContext?: string | null;
    entityContext?: string | null;
}) {
    const [question, setQuestion] = useState(initialQuestion);
    const [veda, setVeda] = useState<AskVedaScope>("ALL");
    const [mode, setMode] = useState<AskMode>("AUTO");
    const [state, setState] = useState<AskState>({ kind: "IDLE" });
    const [elapsed, setElapsed] = useState(0);
    /** Non-zero only while a request is open; the tick effect subscribes to it. */
    const [startedAt, setStartedAt] = useState(0);
    const [turns, setTurns] = useState<AskConversationTurn[]>([]);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [focusId, setFocusId] = useState<string | null>(null);
    const [unavailable, setUnavailable] = useState<{ detail: string; hint?: string | null } | null>(
        null,
    );

    /* Context arrives from the URL but is the reader's to drop: a question seeded from a
       passage is often the start of a broader one, and silently binding retrieval to a verse
       the reader has moved on from is worse than asking them to re-state it. */
    const [passageContext, setPassageContext] = useState(initialPassage);
    const [entityContext, setEntityContext] = useState(initialEntity);

    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const answerRef = useRef<HTMLDivElement>(null);
    const requestRef = useRef<AbortController | null>(null);

    const pending = state.kind === "WAITING";

    // Readiness is checked once so an unconfigured deployment says so before a reader writes
    // a question, rather than after waiting out a full request for a 503.
    useEffect(() => {
        const controller = new AbortController();
        void fetchAskHealth(controller.signal).then((health) => {
            if (health && !health.ask_available) setUnavailable({ detail: health.detail });
        });
        return () => controller.abort();
    }, []);

    /*
     * One second, not 200ms. The readout is whole seconds, so a faster tick renders four
     * frames that say the same thing, and this element is inside a live region.
     *
     * The clock is zeroed by the submit handler rather than here: resetting it in the effect
     * body is a synchronous setState inside an effect, which cascades a second render on
     * every request.
     */
    useEffect(() => {
        if (!startedAt) return;
        const timer = window.setInterval(() => setElapsed(Date.now() - startedAt), 1000);
        return () => window.clearInterval(timer);
    }, [startedAt]);

    useEffect(() => () => requestRef.current?.abort(), []);

    const submit = useCallback(
        async (raw: string, history: AskConversationTurn[]) => {
            const trimmed = raw.trim();
            if (!trimmed || trimmed.length > ASK_QUESTION_LIMIT) return;

            requestRef.current?.abort();
            const controller = new AbortController();
            requestRef.current = controller;
            setElapsed(0);
            setStartedAt(Date.now());
            setState({ kind: "WAITING" });

            try {
                const response = await postAsk(
                    {
                        question: trimmed,
                        veda,
                        mode,
                        passage_context: passageContext,
                        entity_context: entityContext,
                        // The graph is the source of truth; history only disambiguates a
                        // follow-up, so a short window is enough and stays in budget.
                        conversation_context: history.length ? history.slice(-6) : null,
                    },
                    controller.signal,
                );
                if (controller.signal.aborted) return;
                setStartedAt(0);
                setState({ kind: "ANSWER", result: response });
                setTurns([
                    ...history,
                    { role: "user", content: trimmed },
                    { role: "assistant", content: response.answer.slice(0, 4000) },
                ]);
                requestAnimationFrame(() =>
                    answerRef.current?.scrollIntoView({ block: "start", behavior: "smooth" }),
                );
            } catch (reason) {
                if (controller.signal.aborted) return;
                if (reason instanceof DOMException && reason.name === "AbortError") return;
                setStartedAt(0);
                const failure =
                    reason instanceof AskError
                        ? reason
                        : new AskError(
                              "The knowledge service could not answer this question.",
                              "REQUEST_FAILED",
                              503,
                          );
                setState({ kind: "ERROR", error: failure });
                if (failure.unavailable) {
                    setUnavailable({ detail: failure.message, hint: failure.hint });
                }
            }
        },
        [veda, mode, passageContext, entityContext],
    );

    /* Abort is the reader's, so it sets its own state rather than letting the rejected
       request fall through to ERROR. A cancelled request is not a failed one. */
    const cancel = useCallback(() => {
        requestRef.current?.abort();
        requestRef.current = null;
        setStartedAt(0);
        setState({ kind: "CANCELLED" });
    }, []);

    const askAgain = useCallback(
        (next: string) => {
            setQuestion(next);
            void submit(next, turns);
        },
        [submit, turns],
    );

    const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            void submit(question, turns);
        }
    };

    const trimmed = question.trim();
    const remaining = ASK_QUESTION_LIMIT - question.length;
    const overLimit = remaining < 0;
    const nearLimit = remaining <= 200;
    const result = state.kind === "ANSWER" ? state.result : null;
    const citedIds = result ? extractCitedIds(result.answer) : [];
    const context = passageContext ?? entityContext;

    const openEvidence = (id: string | null) => {
        setFocusId(id);
        setDrawerOpen(true);
    };

    /* Not `va-ask`: that class belongs to the homepage's Ask section, which paints the Thread
       of Inquiry as a background watermark. Reusing the name here pulled that watermark under
       this whole page, where it collided with the drawn thread below. */
    return (
        <div className="va-ask-console">
            {unavailable && (
                <div className="va-ask-notice is-unavailable" role="status">
                    <p className="va-ask-notice-head">The synthesis provider is not configured</p>
                    <p>{unavailable.detail}</p>
                    {unavailable.hint && <p className="va-ask-hint">{unavailable.hint}</p>}
                    <p className="va-ask-hint">
                        Ask is the only surface that needs a synthesis provider. Every other part
                        of this atlas, and all of the graph behind it, is unaffected.
                    </p>
                </div>
            )}

            <form
                className="va-ask-composer"
                onSubmit={(event) => {
                    event.preventDefault();
                    void submit(question, turns);
                }}
            >
                <label className="va-ask-label" htmlFor="ask-question">
                    Your question
                </label>

                {context && (
                    <div className="va-ask-context">
                        <span className="va-ask-context-kind">
                            {passageContext ? "Passage context" : "Entity context"}
                        </span>
                        <strong>{context}</strong>
                        <button
                            className="va-ask-context-drop"
                            onClick={() => {
                                setPassageContext(null);
                                setEntityContext(null);
                                textareaRef.current?.focus();
                            }}
                            type="button"
                        >
                            Ask without it
                        </button>
                        <small>
                            {passageContext
                                ? "Retrieval is bound to this verse rather than re-reading its citation out of the question."
                                : "Retrieval is bound to this record rather than resolving the name again."}
                        </small>
                    </div>
                )}

                <textarea
                    aria-describedby="ask-counter ask-submit-hint"
                    aria-invalid={overLimit || undefined}
                    className={clsx("va-ask-input", overLimit && "is-over")}
                    id="ask-question"
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={onKeyDown}
                    placeholder="How does Indra appear across the four Vedas, and is the Atharvavedic picture different?"
                    ref={textareaRef}
                    rows={3}
                    spellCheck
                    value={question}
                />

                <div className="va-ask-controls">
                    <div className="va-ask-scopes">
                        <label>
                            <span>Collection</span>
                            <select
                                onChange={(event) => setVeda(event.target.value as AskVedaScope)}
                                value={veda}
                            >
                                {ASK_VEDA_SCOPES.map((scope) => (
                                    <option key={scope.value} value={scope.value}>
                                        {scope.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label>
                            <span>Retrieval</span>
                            <select
                                aria-describedby="ask-mode-note"
                                onChange={(event) => setMode(event.target.value as AskMode)}
                                value={mode}
                            >
                                {ASK_MODES.map((item) => (
                                    <option key={item.value} value={item.value}>
                                        {item.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <small className="va-ask-mode-note" id="ask-mode-note">
                            {ASK_MODES.find((item) => item.value === mode)?.note}
                        </small>
                    </div>

                    <div className="va-ask-submit">
                        <span
                            className={clsx(
                                "va-ask-counter",
                                nearLimit && "is-near",
                                overLimit && "is-over",
                            )}
                            id="ask-counter"
                        >
                            {overLimit
                                ? `${-remaining} over the ${ASK_QUESTION_LIMIT}-character limit`
                                : nearLimit
                                  ? `${remaining} characters left`
                                  : ""}
                        </span>
                        <button
                            className="va-ask-go"
                            disabled={!trimmed || overLimit || pending}
                            type="submit"
                        >
                            {pending ? "Asking" : "Ask"}
                        </button>
                    </div>
                </div>

                <p className="va-ask-submit-hint" id="ask-submit-hint">
                    <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>Enter</kbd> to ask.
                    {turns.length > 0 && (
                        <>
                            {" "}
                            {turns.length / 2} earlier{" "}
                            {turns.length === 2 ? "exchange" : "exchanges"} will be sent as
                            context.{" "}
                            <button
                                className="va-ask-clear"
                                onClick={() => setTurns([])}
                                type="button"
                            >
                                Clear
                            </button>
                        </>
                    )}
                </p>
            </form>

            {state.kind === "IDLE" && (
                <section aria-labelledby="ask-openings" className="va-ask-openings">
                    <ThreadOfInquiry height={104} />
                    <h2 id="ask-openings">Questions this build can answer</h2>
                    <ul>
                        {ASK_EXAMPLES.map((example) => (
                            <li key={example}>
                                <button
                                    onClick={() => {
                                        setQuestion(example);
                                        textareaRef.current?.focus();
                                    }}
                                    type="button"
                                >
                                    {example}
                                </button>
                            </li>
                        ))}
                    </ul>
                    <p className="va-ask-openings-note">
                        The last is deliberate. A term the Yajurveda may not yield tests whether
                        the answer reports a limit or invents a denial.
                    </p>
                </section>
            )}

            {pending && (
                <section aria-label="Working" className="va-ask-waiting">
                    <ThreadOfInquiry height={104} working />
                    <p className="va-ask-waiting-note">
                        <span className="va-ask-waiting-lead">
                            Searching and synthesising from the corpus
                        </span>
                        {/*
                         * The clock is deliberately outside the live region below.
                         *
                         * It changes every second, and a polite region containing it announces
                         * every one of those: on a median request that is about a hundred
                         * announcements of a number nobody asked to be read the time. It stays
                         * in the accessibility tree, so it can still be read on demand; it just
                         * does not interrupt.
                         */}
                        <span className="va-ask-elapsed">{elapsedCopy(elapsed)}</span>
                    </p>
                    {/* What is announced instead: a sentence that changes four times in four
                        minutes, so a reader is told something only when something changed. */}
                    <p aria-live="polite" className="va-ask-waiting-detail" role="status">
                        {waitNoteFor(elapsed)}
                    </p>
                    <button className="va-ask-cancel" onClick={cancel} type="button">
                        Stop waiting
                    </button>
                </section>
            )}

            {state.kind === "CANCELLED" && (
                <div className="va-ask-notice" role="status">
                    <p className="va-ask-notice-head">Stopped</p>
                    <p>
                        The request was cancelled before an answer arrived. Nothing was retrieved
                        or discarded; ask again when you want it.
                    </p>
                </div>
            )}

            {state.kind === "ERROR" && !state.error.unavailable && (
                <div className="va-ask-notice is-error" role="alert">
                    <p className="va-ask-notice-head">{state.error.message}</p>
                    {state.error.hint && <p className="va-ask-hint">{state.error.hint}</p>}
                    <p className="va-ask-hint">
                        This is a service problem, not a finding about the corpus. Nothing should
                        be read into it about what the Vedas contain.
                    </p>
                    <button
                        className="va-ask-retry"
                        onClick={() => void submit(question, turns)}
                        type="button"
                    >
                        Ask again
                    </button>
                </div>
            )}

            <div ref={answerRef}>
                {result && (
                    <AskAnswer
                        citedIds={citedIds}
                        onAsk={askAgain}
                        onOpenEvidence={openEvidence}
                        result={result}
                    />
                )}
            </div>

            {result && (
                <AskEvidenceDrawer
                    citedIds={citedIds}
                    focusId={focusId}
                    items={result.evidence}
                    onOpenChange={setDrawerOpen}
                    open={drawerOpen}
                />
            )}
        </div>
    );
}
