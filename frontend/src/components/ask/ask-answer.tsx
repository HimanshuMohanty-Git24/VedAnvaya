"use client";

import { ArrowRight, Books, Lightbulb, MagnifyingGlass, Sparkle } from "@phosphor-icons/react";
import clsx from "clsx";
import Link from "next/link";
import {
    channelLabel,
    formatMs,
    matchRankCopy,
    supportLevelCopy,
    type AskResponse,
} from "@/lib/ask";
import { parseAnswer } from "@/lib/ask-citations";
import { entityHref } from "@/lib/knowledge";
import { KnowledgeStatus } from "../status";

/** Support level, as a badge that says its grade in words as well as in colour. */
function SupportBadge({ level }: { level: string }) {
    const copy = supportLevelCopy(level);
    return (
        <span className={clsx("ask-support", `tone-${copy.tone}`)} title={copy.description}>
            <b>{copy.label}</b>
        </span>
    );
}

export function AskAnswer({
    result,
    citedIds,
    onOpenEvidence,
    onAsk,
}: {
    result: AskResponse;
    citedIds: string[];
    onOpenEvidence: (focusId: string | null) => void;
    onAsk: (question: string) => void;
}) {
    const paragraphs = parseAnswer(result.answer);
    const summary = result.retrieval_summary;
    const evidenceIds = new Set(result.evidence.map((item) => item.id));
    const unresolved = result.entities.filter((entity) => !entity.resolved);
    const resolved = result.entities.filter((entity) => entity.resolved);

    return (
        <article className="ask-answer" aria-labelledby="ask-answer-heading">
            <header className="ask-answer-head">
                <h2 id="ask-answer-heading">Answer</h2>
                <div className="ask-badges">
                    <KnowledgeStatus status={result.status} compact />
                    <SupportBadge level={result.support_level} />
                </div>
            </header>

            <p className="ask-status-note">{supportLevelCopy(result.support_level).description}</p>

            {result.interpretive_content_present && (
                <div className="ask-interpretive" data-knowledge-kind="interpretation">
                    <Lightbulb size={17} weight="duotone" aria-hidden="true" />
                    <span>
                        <b>This answer draws on an interpretive claim.</b> Part of what follows is a
                        reading attributed to a source, not something the texts state. The
                        interpretation is listed in the evidence under its own heading.
                    </span>
                </div>
            )}

            <div className="ask-prose">
                {paragraphs.length === 0 && (
                    <p className="muted">The synthesis returned no prose for this question.</p>
                )}
                {paragraphs.map((paragraph, index) => (
                    // Paragraph order is the answer's own order; index is the stable key.
                    <p key={index}>
                        {paragraph.segments.map((segment, position) =>
                            segment.kind === "text" ? (
                                <span key={position}>{segment.text}</span>
                            ) : (
                                <span className="ask-cite-group" key={position}>
                                    {segment.ids.map((id) => (
                                        <button
                                            type="button"
                                            className="ask-cite"
                                            key={id}
                                            aria-label={`Evidence ${id}`}
                                            disabled={!evidenceIds.has(id)}
                                            onClick={() => onOpenEvidence(id)}
                                        >
                                            {id}
                                        </button>
                                    ))}
                                </span>
                            ),
                        )}
                    </p>
                ))}
            </div>

            <div className="ask-answer-actions">
                <button
                    type="button"
                    className="button secondary"
                    onClick={() => onOpenEvidence(null)}
                >
                    <Books size={18} aria-hidden="true" />
                    Inspect all {summary.evidence_count} evidence items
                </button>
                <p className="ask-provenance">
                    Retrieved from the VedaGraph graph, synthesised by {result.llm.provider} /{" "}
                    {result.llm.model}. The model saw only the retrieved evidence.
                </p>
            </div>

            {result.caveats.length > 0 && (
                <section className="ask-caveats" aria-label="Scope notes for this answer">
                    <h3>What this answer does not settle</h3>
                    <ul>
                        {result.caveats.map((caveat) => (
                            <li key={`${caveat.source}-${caveat.text}`}>
                                <p>{caveat.text}</p>
                                <cite>{caveat.source}</cite>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {(resolved.length > 0 || unresolved.length > 0) && (
                <section className="ask-entities" aria-label="Names in this question">
                    <h3>Names in this question</h3>
                    {resolved.length > 0 && (
                        <ul className="ask-entity-list">
                            {resolved.map((entity) => (
                                <li key={`${entity.label}-${entity.entity_key}`}>
                                    {entity.entity_key ? (
                                        <Link
                                            className="ask-entity is-resolved"
                                            href={entityHref(entity.entity_type, entity.entity_key)}
                                        >
                                            <strong>{entity.label}</strong>
                                            <small>{matchRankCopy(entity.match_rank)}</small>
                                            <ArrowRight size={14} aria-hidden="true" />
                                        </Link>
                                    ) : (
                                        <span className="ask-entity is-resolved">
                                            <strong>{entity.label}</strong>
                                            <small>{matchRankCopy(entity.match_rank)}</small>
                                        </span>
                                    )}
                                </li>
                            ))}
                        </ul>
                    )}
                    {unresolved.length > 0 && (
                        <div className="ask-unresolved">
                            <p>
                                <b>Not found in VedaGraph.</b> These names were read out of the
                                question and no entity in this build answers to them. That is a
                                fact about this graph, not about the Vedas.
                            </p>
                            <ul>
                                {unresolved.map((entity) => (
                                    <li key={entity.label}>
                                        {entity.label}
                                        {entity.asked_as && entity.asked_as !== entity.label && (
                                            <small>asked as “{entity.asked_as}”</small>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </section>
            )}

            {result.related_questions.length > 0 && (
                <section className="ask-related" aria-label="Related questions">
                    <h3>
                        <Sparkle size={15} weight="duotone" aria-hidden="true" />
                        Ask next
                    </h3>
                    <div className="ask-chip-row">
                        {result.related_questions.map((question) => (
                            <button type="button" key={question} onClick={() => onAsk(question)}>
                                {question}
                            </button>
                        ))}
                    </div>
                </section>
            )}

            <details className="ask-retrieval">
                <summary>
                    <MagnifyingGlass size={16} aria-hidden="true" />
                    How this answer was retrieved
                    <span>{formatMs(summary.total_ms)}</span>
                </summary>
                <div className="ask-retrieval-body">
                    <div className="ask-retrieval-block">
                        <h4>Question read as</h4>
                        {summary.intents.length ? (
                            <div className="ask-tag-row">
                                {summary.intents.map((intent) => (
                                    <span key={intent}>{channelLabel(intent)}</span>
                                ))}
                            </div>
                        ) : (
                            <p className="muted">No intent was recorded for this question.</p>
                        )}
                    </div>

                    <div className="ask-retrieval-block">
                        <h4>Channels that returned evidence</h4>
                        {summary.channels_used.length ? (
                            <div className="ask-tag-row">
                                {summary.channels_used.map((channel) => (
                                    <span key={channel}>{channelLabel(channel)}</span>
                                ))}
                            </div>
                        ) : (
                            <p className="muted">No channel returned evidence.</p>
                        )}
                    </div>

                    <div className="ask-retrieval-block">
                        <h4>Searched, found nothing</h4>
                        {summary.channels_empty.length ? (
                            <>
                                <div className="ask-tag-row is-empty">
                                    {summary.channels_empty.map((channel) => (
                                        <span key={channel}>{channelLabel(channel)}</span>
                                    ))}
                                </div>
                                <p className="ask-empty-note">
                                    These channels ran and came back empty. That is different from a
                                    channel that was never selected: searched-and-empty is evidence
                                    of a kind, unexamined is not.
                                </p>
                            </>
                        ) : (
                            <p className="muted">
                                Every channel that ran returned something. Channels not listed above
                                were not selected for this question, so nothing is known about them
                                either way.
                            </p>
                        )}
                    </div>

                    <div className="ask-retrieval-block">
                        <h4>Scope and yield</h4>
                        <dl className="ask-figures">
                            <div>
                                <dt>Collection scope</dt>
                                <dd>{summary.veda_scope}</dd>
                            </div>
                            <div>
                                <dt>Evidence retrieved</dt>
                                <dd>{summary.evidence_count}</dd>
                            </div>
                            <div>
                                <dt>Evidence cited</dt>
                                <dd>{citedIds.length}</dd>
                            </div>
                            <div>
                                <dt>Names resolved</dt>
                                <dd>
                                    {summary.entities_resolved.length} of{" "}
                                    {summary.entities_resolved.length +
                                        summary.entities_unresolved.length}
                                </dd>
                            </div>
                        </dl>
                    </div>

                    <div className="ask-retrieval-block">
                        <h4>Time spent</h4>
                        <dl className="ask-figures">
                            <div>
                                <dt>Planning</dt>
                                <dd>{formatMs(summary.planner_ms)}</dd>
                            </div>
                            <div>
                                <dt>Retrieval</dt>
                                <dd>{formatMs(summary.retrieval_ms)}</dd>
                            </div>
                            <div>
                                <dt>Synthesis</dt>
                                <dd>{formatMs(summary.synthesis_ms)}</dd>
                            </div>
                            <div>
                                <dt>Total</dt>
                                <dd>{formatMs(summary.total_ms)}</dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </details>
        </article>
    );
}
