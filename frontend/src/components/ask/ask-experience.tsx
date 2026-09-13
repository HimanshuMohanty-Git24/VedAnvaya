"use client";

import { ArrowUp, Prohibit, WarningCircle, X } from "@phosphor-icons/react";
import clsx from "clsx";
import { useCallback, useEffect, useRef, useState } from "react";
import {
    ASK_EXAMPLES,
    ASK_MODES,
    ASK_QUESTION_LIMIT,
    ASK_VEDA_SCOPES,
    AskError,
    fetchAskHealth,
    postAsk,
    type AskConversationTurn,
    type AskMode,
    type AskResponse,
    type AskVedaScope,
} from "@/lib/ask";
import { extractCitedIds } from "@/lib/ask-citations";
import { AskAnswer } from "./ask-answer";
import { AskEvidenceDrawer } from "./ask-evidence-drawer";

/**
 * The response is not streamed, so elapsed-time phases are estimates, not backend
 * telemetry. The pending copy states this explicitly.
 */
const PHASES = [
    { at: 0, label: "Reading the question", note: "Classifying intent and resolving names" },
    { at: 900, label: "Retrieving evidence", note: "Running the selected channels over the graph" },
    {
        at: 2600,
        label: "Synthesising the answer",
        note: "Writing prose from the retrieved evidence only",
    },
];

function phaseFor(elapsed: number) {
    return PHASES.reduce((current, phase) => (elapsed >= phase.at ? phase : current), PHASES[0]);
}

export function AskExperience({
    initialQuestion = "",
    passageContext = null,
    entityContext = null,
}: {
    initialQuestion?: string;
    passageContext?: string | null;
    entityContext?: string | null;
}) {
    const [question, setQuestion] = useState(initialQuestion);
    const [veda, setVeda] = useState<AskVedaScope>("ALL");
    const [mode, setMode] = useState<AskMode>("AUTO");
    const [pending, setPending] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [startedAt, setStartedAt] = useState(0);
    const [result, setResult] = useState<AskResponse | null>(null);
    const [error, setError] = useState<AskError | null>(null);
    const [unavailable, setUnavailable] = useState<{ detail: string; hint?: string | null } | null>(
        null,
    );
    const [turns, setTurns] = useState<AskConversationTurn[]>([]);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [focusId, setFocusId] = useState<string | null>(null);

    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const answerRef = useRef<HTMLDivElement>(null);
    const requestRef = useRef<AbortController | null>(null);

    // Readiness is checked once so an unconfigured deployment says so before a reader
    // writes a question, rather than after waiting for a 503.
    useEffect(() => {
        const controller = new AbortController();
        void fetchAskHealth(controller.signal).then((health) => {
            if (health && !health.ask_available) {
                setUnavailable({ detail: health.detail });
            }
        });
        return () => controller.abort();
    }, []);

    // The clock is started by the submit handler, so this effect only subscribes to it.
    useEffect(() => {
        if (!pending || !startedAt) return;
        const timer = window.setInterval(() => setElapsed(Date.now() - startedAt), 200);
        return () => window.clearInterval(timer);
    }, [pending, startedAt]);

    useEffect(() => () => requestRef.current?.abort(), []);

    const submit = useCallback(
        async (raw: string, history: AskConversationTurn[]) => {
            const trimmed = raw.trim();
            if (!trimmed || trimmed.length > ASK_QUESTION_LIMIT) return;

            requestRef.current?.abort();
            const controller = new AbortController();
            requestRef.current = controller;

            setStartedAt(Date.now());
            setElapsed(0);
            setPending(true);
            setError(null);
            setResult(null);
            try {
                const response = await postAsk(
                    {
                        question: trimmed,
                        veda,
                        mode,
                        passage_context: passageContext,
                        entity_context: entityContext,
                        // The graph is the source of truth; history only disambiguates
                        // a follow-up, so a short window is enough and stays in budget.
                        conversation_context: history.length ? history.slice(-6) : null,
                    },
                    controller.signal,
                );
                if (controller.signal.aborted) return;
                setResult(response);
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
                const failure =
                    reason instanceof AskError
                        ? reason
                        : new AskError(
                              "The knowledge service could not answer this question.",
                              "REQUEST_FAILED",
                              503,
                          );
                setError(failure);
                if (failure.unavailable) {
                    setUnavailable({ detail: failure.message, hint: failure.hint });
                }
            } finally {
                if (!controller.signal.aborted) setPending(false);
            }
        },
        [veda, mode, passageContext, entityContext],
    );

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
    const phase = phaseFor(elapsed);
    const citedIds = result ? extractCitedIds(result.answer) : [];

    const openEvidence = (id: string | null) => {
        setFocusId(id);
        setDrawerOpen(true);
    };

    return (
        <div className="ask-experience">
            {unavailable && (
                <div className="ask-unavailable" role="status">
                    <Prohibit size={20} weight="duotone" aria-hidden="true" />
                    <div>
                        <strong>The synthesis backend is not configured.</strong>
                        <p>{unavailable.detail}</p>
                        {unavailable.hint && <p className="ask-hint">{unavailable.hint}</p>}
                        <p className="ask-hint">
                            Every other surface of this atlas still works. Ask is the only feature
                            that needs a synthesis provider, and none of the graph data depends on
                            it.
                        </p>
                    </div>
                </div>
            )}

            {(passageContext || entityContext) && (
                <div className="ask-context" role="status">
                    <span>Asking about</span>
                    <strong>{passageContext ?? entityContext}</strong>
                    <small>
                        {passageContext
                            ? "sent as passage context, so retrieval binds this verse rather than re-reading its citation out of the question"
                            : "sent as entity context, so retrieval binds this record rather than re-resolving the name"}
                    </small>
                </div>
            )}

            <form
                className="ask-composer"
                onSubmit={(event) => {
                    event.preventDefault();
                    void submit(question, turns);
                }}
            >
                <label htmlFor="ask-question">
                    Your research question
                    <small>
                        Questions can be long. Name the collection, the passage or the entity you
                        mean, and Ask will say which of them it could resolve.
                    </small>
                </label>
                <div className={clsx("ask-textarea-wrap", overLimit && "is-over")}>
                    <textarea
                        id="ask-question"
                        ref={textareaRef}
                        value={question}
                        rows={4}
                        onChange={(event) => setQuestion(event.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder="e.g. How does Indra appear across the four Vedas, and is the Atharvavedic picture different?"
                        aria-describedby="ask-counter ask-submit-hint"
                        aria-invalid={overLimit || undefined}
                        spellCheck
                    />
                </div>

                <div className="ask-controls">
                    <div className="ask-selects">
                        <label>
                            <span>Collection</span>
                            <select
                                value={veda}
                                onChange={(event) => setVeda(event.target.value as AskVedaScope)}
                            >
                                {ASK_VEDA_SCOPES.map((scope) => (
                                    <option key={scope.value} value={scope.value}>
                                        {scope.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label>
                            <span>Retrieval mode</span>
                            <select
                                value={mode}
                                aria-describedby="ask-mode-note"
                                onChange={(event) => setMode(event.target.value as AskMode)}
                            >
                                {ASK_MODES.map((item) => (
                                    <option key={item.value} value={item.value}>
                                        {item.label}
                                    </option>
                                ))}
                            </select>
                            <small className="ask-mode-note" id="ask-mode-note">
                                {ASK_MODES.find((item) => item.value === mode)?.note}
                            </small>
                        </label>
                    </div>

                    <div className="ask-submit-row">
                        <span
                            className={clsx(
                                "ask-counter",
                                nearLimit && "is-near",
                                overLimit && "is-over",
                            )}
                            id="ask-counter"
                            aria-live="polite"
                        >
                            {overLimit
                                ? `${-remaining} over the ${ASK_QUESTION_LIMIT}-character limit`
                                : nearLimit
                                  ? `${remaining} characters left`
                                  : `${question.length} / ${ASK_QUESTION_LIMIT}`}
                        </span>
                        <button
                            type="submit"
                            className="button primary"
                            disabled={!trimmed || overLimit || pending}
                        >
                            <ArrowUp size={17} aria-hidden="true" />
                            {pending ? "Asking…" : "Ask VedaGraph"}
                        </button>
                    </div>
                </div>
                <p className="ask-submit-hint" id="ask-submit-hint">
                    Press <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>Enter</kbd> to ask.
                    {turns.length > 0 && (
                        <>
                            {" "}
                            {turns.length / 2} earlier{" "}
                            {turns.length === 2 ? "exchange" : "exchanges"} will be sent as context.
                            <button
                                type="button"
                                className="ask-clear"
                                onClick={() => setTurns([])}
                            >
                                <X size={12} aria-hidden="true" />
                                Clear context
                            </button>
                        </>
                    )}
                </p>
            </form>

            {!result && !pending && (
                <section className="ask-examples" aria-label="Example questions">
                    <h2>Questions this build can answer</h2>
                    <div className="ask-chip-row">
                        {ASK_EXAMPLES.map((example) => (
                            <button
                                type="button"
                                key={example}
                                onClick={() => {
                                    setQuestion(example);
                                    textareaRef.current?.focus();
                                }}
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                    <p className="muted">
                        The last one is deliberate: a term the Yajurveda may not yield is a test of
                        whether the answer reports a limit or invents a denial.
                    </p>
                </section>
            )}

            {pending && (
                <div className="ask-pending" role="status" aria-live="polite">
                    <ol className="ask-phases">
                        {PHASES.map((item) => {
                            const done = elapsed > item.at && item.label !== phase.label;
                            const active = item.label === phase.label;
                            return (
                                <li
                                    key={item.label}
                                    data-state={done ? "done" : active ? "active" : "waiting"}
                                >
                                    <i aria-hidden="true" />
                                    <span>
                                        <strong>{item.label}</strong>
                                        <small>{item.note}</small>
                                    </span>
                                </li>
                            );
                        })}
                    </ol>
                    <p className="ask-pending-note">
                        Progress is estimated. The answer appears when retrieval and synthesis
                        finish. Response time varies with the question and synthesis provider.
                    </p>
                    <div className="skeleton" style={{ height: 14, width: "88%" }} />
                    <div className="skeleton" style={{ height: 14, width: "94%" }} />
                    <div className="skeleton" style={{ height: 14, width: "64%" }} />
                </div>
            )}

            {error && !error.unavailable && (
                <div className="ask-error" role="alert">
                    <WarningCircle size={20} aria-hidden="true" />
                    <div>
                        <strong>{error.message}</strong>
                        {error.hint && <p className="ask-hint">{error.hint}</p>}
                        <p className="ask-hint">
                            This is a service problem, not a finding about the corpus. Nothing
                            should be read into it about what the Vedas contain.
                        </p>
                    </div>
                </div>
            )}

            <div ref={answerRef}>
                {result && !pending && (
                    <AskAnswer
                        result={result}
                        citedIds={citedIds}
                        onOpenEvidence={openEvidence}
                        onAsk={askAgain}
                    />
                )}
            </div>

            {result && (
                <AskEvidenceDrawer
                    open={drawerOpen}
                    items={result.evidence}
                    focusId={focusId}
                    citedIds={citedIds}
                    onOpenChange={setDrawerOpen}
                />
            )}
        </div>
    );
}
