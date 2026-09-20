"use client";

import clsx from "clsx";
import Link from "next/link";
import { useState } from "react";
import { encoded } from "@/lib/api";
import {
    caveatSourceLabel,
    channelLabel,
    clauses,
    formatMs,
    matchRankCopy,
    supportLevelCopy,
    truncationCaveat,
    TRUNCATION_SOURCE,
    type AskEvidenceItem,
    type AskResponse,
} from "@/lib/ask";
import { parseAnswer, type AnswerSegment } from "@/lib/ask-citations";
import { entityHref } from "@/lib/knowledge";

/**
 * The answer, as a research response rather than as a message.
 *
 * There is no bubble, no avatar and no transcript, because none of those carry meaning here:
 * the reader knows who wrote it and there is only ever one of them on screen. What the layout
 * spends its hierarchy on instead is the part a bubble has nowhere to put - the grade on the
 * evidence, the passages the prose was built from, and the sentence saying what the answer
 * does not settle.
 *
 * Evidence is on the page, not only behind the drawer. Retrieved passages are what the answer
 * is made of, so at least the first of them are set under the prose where they can be read
 * without a click; the drawer holds the full set with every item's provenance.
 */

/** The first passages, which are the part of the evidence a reader can check by reading. */
function inlinePassages(evidence: AskEvidenceItem[]) {
    return evidence.filter((item) => item.type === "PASSAGE" && (item.sanskrit || item.translation));
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
    const support = supportLevelCopy(result.support_level);

    /*
     * Only citations that resolve to a retrieved item are counted.
     *
     * `citedIds` is parsed out of the prose, so it can name an item that is not in the
     * evidence at all: a model asked to cite its sources can emit a marker for something it
     * did not receive. Counting those made the summary line read "1 item retrieved, 2 cited",
     * which is not merely odd arithmetic - it credits the answer with support that was never
     * retrieved. The markers themselves already render disabled when they dangle.
     */
    const resolvedCitations = citedIds.filter((id) => evidenceIds.has(id));

    const truncated = truncationCaveat(result);
    /* The truncation caveat is lifted out of the list and given its own place above the prose.
       Left in the list it read as one scope note among five, which is the one thing it must
       not be: every other caveat qualifies a complete answer, and this one says the text is
       not complete. The remaining caveats keep their section unchanged. */
    const caveats = result.caveats.filter((caveat) => caveat.source !== TRUNCATION_SOURCE);
    const passages = inlinePassages(result.evidence);
    const cited = new Set(citedIds);

    /*
     * The binding: which evidence item the reader is pointing at, from either end.
     *
     * One piece of state, written by the citation markers in the prose and by the evidence
     * entries under it, and read by both. That is what makes the relation legible in both
     * directions without either side knowing about the other: a citation says "E2" and an
     * entry says "E2", and the id is the binding.
     *
     * Hover *and* focus, because the whole point is that it works from the keyboard as well.
     * A binding that only exists under a pointer is a binding a screen-reader user and a
     * keyboard user cannot see at all, and the citation markers are already buttons in the
     * tab order.
     *
     * The drawn rule is the Anvaya Thread from `thread.css`: DRAW, where a real evidentiary
     * relation exists. A citation pointing at the item it cites is exactly that, and it is
     * the only place in the answer where a line is drawn.
     */
    const [bound, setBound] = useState<string | null>(null);
    const bind = (id: string | null) => () => setBound(id);

    /**
     * One run of segments, as prose and citation markers.
     *
     * Shared by a paragraph and a list item rather than written twice, because the two
     * differ only in the element around them - and a second copy is a second place for the
     * binding, the disabled state or the accessible name of a citation to drift.
     */
    const render = (segments: AnswerSegment[]) =>
        segments.map((segment, position) =>
            segment.kind === "text" ? (
                segment.emphasis ? (
                    <strong key={position}>{segment.text}</strong>
                ) : (
                    <span key={position}>{segment.text}</span>
                )
            ) : (
                <span className="va-cite-group" key={position}>
                    {segment.ids.map((id) => (
                        <button
                            aria-label={`Open evidence ${id}`}
                            className="va-cite"
                            data-bound={bound === id}
                            disabled={!evidenceIds.has(id)}
                            key={id}
                            onBlur={bind(null)}
                            onClick={() => onOpenEvidence(id)}
                            onFocus={bind(id)}
                            onMouseEnter={bind(id)}
                            onMouseLeave={bind(null)}
                            type="button"
                        >
                            {id}
                        </button>
                    ))}
                </span>
            ),
        );

    return (
        <article aria-labelledby="ask-answer-heading" className="va-answer">
            {/*
             * The grade sits with the heading, not in the rail.
             *
             * It qualifies the prose, so it has to be met before the prose is read. In the
             * rail it was correct on a wide screen and wrong on a narrow one, where the rail
             * stacks under the reading column and "moderate support" arrived after the
             * answer, the evidence and the caveats had all been read.
             */}
            <header className="va-answer-head">
                <h2 id="ask-answer-heading">Answer</h2>
                <p className={clsx("va-answer-support", `tone-${support.tone}`)}>
                    <strong>{support.label}</strong>
                    <span>{support.description}</span>
                </p>
            </header>

            <div className="va-answer-main">
            {truncated && (
                <div className="va-answer-truncated" role="status">
                    <p className="va-answer-truncated-head">
                        This response ended before synthesis completed
                    </p>
                    {/* The backend's own wording. It is the canonical statement of this
                        condition and re-phrasing it here would fork the policy. */}
                    <p>{truncated.text}</p>
                    <div className="va-answer-truncated-ways">
                        <button onClick={() => onOpenEvidence(null)} type="button">
                            Read the evidence instead
                        </button>
                    </div>
                </div>
            )}

            {result.interpretive_content_present && (
                <p className="va-answer-interpretive" data-knowledge-kind="interpretation">
                    <strong>This answer draws on an interpretive claim.</strong> Part of what
                    follows is a reading attributed to a source, not something the texts state. It
                    is listed in the evidence under its own heading.
                </p>
            )}

            <div className="va-answer-prose">
                {paragraphs.length === 0 && (
                    <p className="va-answer-empty">
                        The synthesis returned no prose for this question. The retrieved evidence
                        is still listed below.
                    </p>
                )}
                {paragraphs.map((paragraph, index) =>
                    /*
                     * A block the model wrote as a list is rendered as one.
                     *
                     * Set in the reading column's own type rather than as a bulleted list
                     * with a marker: these are findings, each one carrying its citations,
                     * and a rubric mark in the margin is how the rest of the product marks
                     * a division. See `parseAnswer` for why the block arrives as one
                     * paragraph in the first place.
                     */
                    paragraph.bullets ? (
                        <ul className="va-answer-points" key={index}>
                            {paragraph.bullets.map((point, at) => (
                                <li key={at}>{render(point)}</li>
                            ))}
                        </ul>
                    ) : (
                        // Paragraph order is the answer's own order; index is the stable key.
                        <p key={index}>{render(paragraph.segments)}</p>
                    ),
                )}
            </div>

            {passages.length > 0 && (
                <section aria-labelledby="ask-evidence-heading" className="va-answer-evidence">
                    <div className="va-answer-evidence-top">
                        <h3 id="ask-evidence-heading">Evidence</h3>
                        <p>
                            {summary.evidence_count} item
                            {summary.evidence_count === 1 ? "" : "s"} retrieved,{" "}
                            {resolvedCitations.length} cited in the prose above.
                        </p>
                    </div>

                    <ul className="va-evidence-list">
                        {passages.slice(0, 3).map((item) => (
                            <li
                                className="va-evidence-entry"
                                data-bound={bound === item.id}
                                data-cited={cited.has(item.id)}
                                key={item.id}
                                /* The reverse binding. An entry is not a control, so the
                                   pointer half is on the item and the keyboard half is
                                   delegated: focus bubbles here from the links and buttons
                                   inside it, which are what a keyboard reader actually
                                   lands on. */
                                onBlur={bind(null)}
                                onFocus={bind(item.id)}
                                onMouseEnter={bind(item.id)}
                                onMouseLeave={bind(null)}
                            >
                                <div className="va-evidence-cite">
                                    <span className="va-evidence-id">{item.id}</span>
                                    <strong>{item.citation ?? item.passage_key}</strong>
                                    <small>
                                        {cited.has(item.id)
                                            ? "cited above"
                                            : "retrieved, not cited"}
                                    </small>
                                </div>
                                {item.sanskrit && (
                                    <p className="sanskrit" lang="sa">
                                        {item.sanskrit}
                                    </p>
                                )}
                                {item.translation && <blockquote>{item.translation}</blockquote>}
                                <div className="va-evidence-ways">
                                    {item.passage_key && (
                                        <Link href={`/passage/${encoded(item.passage_key)}`}>
                                            Open in the reader
                                        </Link>
                                    )}
                                    <button
                                        onClick={() => onOpenEvidence(item.id)}
                                        type="button"
                                    >
                                        What it does not establish
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>

                    <button
                        className="va-answer-inspect"
                        onClick={() => onOpenEvidence(null)}
                        type="button"
                    >
                        Inspect all {summary.evidence_count} retrieved items
                    </button>
                </section>
            )}

            {passages.length === 0 && (
                <section className="va-answer-evidence is-empty">
                    <h3>Evidence</h3>
                    <p>
                        {summary.evidence_count > 0 ? (
                            <>
                                {summary.evidence_count} item
                                {summary.evidence_count === 1 ? " was" : "s were"} retrieved, none
                                of them a passage with readable text.{" "}
                                <button onClick={() => onOpenEvidence(null)} type="button">
                                    Inspect what was retrieved
                                </button>
                            </>
                        ) : (
                            "Retrieval returned nothing for this question. That is a statement about what this build could reach, not about what the Vedas contain."
                        )}
                    </p>
                </section>
            )}

            {caveats.length > 0 && (
                <section aria-label="Scope notes for this answer" className="va-answer-caveats">
                    <h3>What this answer does not settle</h3>
                    {/*
                     * Each caveat, broken into the clauses it is already made of.
                     *
                     * Nothing is rewritten, shortened or dropped: `clauses` decides where a
                     * line ends and does nothing else, and its round trip is asserted in
                     * `tests/unit/ask-clauses.test.ts`. What changes is that four sentences
                     * qualifying four different things stop being one grey paragraph.
                     */}
                    <ul>
                        {caveats.map((caveat) => (
                            <li key={`${caveat.source}-${caveat.text}`}>
                                {clauses(caveat.text).map((clause, index) => (
                                    <p key={index}>{clause}</p>
                                ))}
                                <cite>{caveatSourceLabel(caveat.source)}</cite>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            </div>

            {/*
             * The apparatus rail.
             *
             * The same division the Reader draws: what is being read on the left, what is
             * recorded about it on the right. The grade, the names retrieval could and could
             * not resolve, and the channel report are all statements about the answer rather
             * than parts of it, and at this width they would otherwise sit under the prose as
             * four more full-width blocks with a measure of text in the left third of each.
             *
             * It comes after the reading column in the DOM, so it is also what a screen reader
             * and a narrow viewport get last, which is the right order for an apparatus.
             */}
            <aside aria-label="About this answer" className="va-answer-rail">
            {(resolved.length > 0 || unresolved.length > 0) && (
                <section aria-label="Names in this question" className="va-answer-names">
                    <h3>Names in this question</h3>
                    {resolved.length > 0 && (
                        <ul className="va-name-list">
                            {resolved.map((entity) => (
                                <li key={`${entity.label}-${entity.entity_key}`}>
                                    {entity.entity_key ? (
                                        <Link
                                            href={entityHref(entity.entity_type, entity.entity_key)}
                                        >
                                            <strong>{entity.label}</strong>
                                            <small>{matchRankCopy(entity.match_rank)}</small>
                                        </Link>
                                    ) : (
                                        <span>
                                            <strong>{entity.label}</strong>
                                            <small>{matchRankCopy(entity.match_rank)}</small>
                                        </span>
                                    )}
                                </li>
                            ))}
                        </ul>
                    )}
                    {unresolved.length > 0 && (
                        <div className="va-name-unresolved">
                            <p>
                                <strong>Not found in VedAnvaya.</strong> These names were read out
                                of the question and no entity in this build answers to them. That
                                is a fact about this graph, not about the Vedas.
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
                <section aria-label="Related questions" className="va-answer-next">
                    <h3>Continue the inquiry</h3>
                    <ul>
                        {result.related_questions.map((question) => (
                            <li key={question}>
                                <button onClick={() => onAsk(question)} type="button">
                                    {question}
                                </button>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <details className="va-answer-retrieval">
                <summary>
                    How this answer was retrieved
                    <span>{formatMs(summary.total_ms)}</span>
                </summary>
                <div className="va-retrieval-body">
                    <div className="va-retrieval-block">
                        <h4>Question read as</h4>
                        {summary.intents.length ? (
                            <p className="va-retrieval-terms">
                                {summary.intents.map(channelLabel).join(", ")}
                            </p>
                        ) : (
                            <p className="va-retrieval-none">
                                No intent was recorded for this question.
                            </p>
                        )}
                    </div>

                    <div className="va-retrieval-block">
                        <h4>Channels that returned evidence</h4>
                        {summary.channels_used.length ? (
                            <p className="va-retrieval-terms">
                                {summary.channels_used.map(channelLabel).join(", ")}
                            </p>
                        ) : (
                            <p className="va-retrieval-none">No channel returned evidence.</p>
                        )}
                    </div>

                    <div className="va-retrieval-block">
                        <h4>Searched, found nothing</h4>
                        {summary.channels_empty.length ? (
                            <>
                                <p className="va-retrieval-terms is-empty">
                                    {summary.channels_empty.map(channelLabel).join(", ")}
                                </p>
                                <p className="va-retrieval-note">
                                    These channels ran and came back empty. That is different from
                                    a channel that was never selected: searched-and-empty is
                                    evidence of a kind, unexamined is not.
                                </p>
                            </>
                        ) : (
                            <p className="va-retrieval-none">
                                Every channel that ran returned something. Channels not listed
                                above were not selected for this question, so nothing is known
                                about them either way.
                            </p>
                        )}
                    </div>

                    <div className="va-retrieval-block">
                        <h4>Scope and yield</h4>
                        <dl className="va-retrieval-figures">
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
                                <dd>{resolvedCitations.length}</dd>
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

                    <div className="va-retrieval-block">
                        <h4>Time spent</h4>
                        <dl className="va-retrieval-figures">
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

            <p className="va-answer-provenance">
                Retrieved from the VedAnvaya graph and synthesised by {result.llm.provider} /{" "}
                {result.llm.model}. The model saw only the retrieved evidence.
            </p>
            </aside>
        </article>
    );
}
