"use client";

import { ArrowRight, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import type { GraphEdge, RelationshipExplanation } from "@/lib/api";
import {
    attributionCopy,
    entityHref,
    entityTypeLabel,
    evidenceBasisCopy,
    humanizePredicate,
    isRenderedAsDeity,
    trustTierCopy,
} from "@/lib/knowledge";
import { KnowledgeStatus } from "./status";

/** The reusable "why are these connected?" surface. */
export function EvidenceDrawer({
    open,
    loading,
    data,
    edge,
    onOpenChange,
}: {
    open: boolean;
    loading: boolean;
    data: RelationshipExplanation | null;
    edge?: GraphEdge | null;
    onOpenChange: (value: boolean) => void;
}) {
    const basis = evidenceBasisCopy(data?.relationship.evidence?.evidence_basis);
    const spans = (data?.relationship.evidence?.spans ?? []).filter((span) => span.quote);
    const title = data
        ? `${data.source.label} — ${data.relationship.label} — ${data.target.label}`
        : edge
          ? `${humanizePredicate(edge.type)}`
          : "Evidence";

    return (
        <Dialog.Root open={open} onOpenChange={onOpenChange}>
            <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content className="evidence-drawer" aria-describedby="evidence-why">
                    <header>
                        <div>
                            <span>Why are these connected?</span>
                            <Dialog.Title>{title}</Dialog.Title>
                        </div>
                        <Dialog.Close className="icon-button" aria-label="Close the evidence panel">
                            <X size={19} aria-hidden="true" />
                        </Dialog.Close>
                    </header>

                    {loading && (
                        <div className="evidence-loading" aria-hidden="true">
                            <div className="skeleton" style={{ height: 54 }} />
                            <div className="skeleton" style={{ height: 96 }} />
                            <div className="skeleton" style={{ height: 140 }} />
                        </div>
                    )}

                    {!loading && !data && (
                        <div className="evidence-content">
                            <KnowledgeStatus
                                status="INSUFFICIENT_EVIDENCE"
                                note="No stored explanation was returned for this relationship. The edge exists in the graph; its derivation record does not."
                            />
                        </div>
                    )}

                    {!loading && data && (
                        <div className="evidence-content">
                            <div className="evidence-triple">
                                <Link href={entityHref(data.source.type, data.source.id)}>
                                    <span>
                                        {isRenderedAsDeity(data.source)
                                            ? "deity"
                                            : entityTypeLabel(data.source.type)}
                                    </span>
                                    <strong>{data.source.label}</strong>
                                </Link>
                                <i aria-hidden="true">{data.relationship.label}</i>
                                <Link href={entityHref(data.target.type, data.target.id)}>
                                    <span>
                                        {isRenderedAsDeity(data.target)
                                            ? "deity"
                                            : entityTypeLabel(data.target.type)}
                                    </span>
                                    <strong>{data.target.label}</strong>
                                </Link>
                            </div>

                            <KnowledgeStatus status={data.data_status} />

                            <section className="why-answer">
                                <h3>Why</h3>
                                <p id="evidence-why">{data.why}</p>
                            </section>

                            <dl className="evidence-metadata">
                                <div>
                                    <dt>How it was established</dt>
                                    <dd>
                                        {basis.label}
                                        <small>{basis.detail}</small>
                                    </dd>
                                </div>
                                <div>
                                    <dt>Knowledge grade</dt>
                                    <dd>{trustTierCopy(data.trust_tier)}</dd>
                                </div>
                                <div>
                                    <dt>What it attributes</dt>
                                    <dd>
                                        {attributionCopy(
                                            data.relationship.evidence?.attribution_precision,
                                        )}
                                    </dd>
                                </div>
                                <div>
                                    <dt>Review</dt>
                                    <dd>
                                        {data.review_status ??
                                            "No review record is stored for this layer."}
                                    </dd>
                                </div>
                            </dl>

                            <section>
                                <h3>Evidence</h3>
                                {spans.length > 0 && (
                                    <div className="evidence-spans">
                                        {spans.map((span) => (
                                            <figure key={`${span.passage_key}-${span.quote}`}>
                                                <blockquote className="sanskrit" lang="sa">
                                                    {span.quote}
                                                </blockquote>
                                                <figcaption>
                                                    {span.citation ?? span.passage_key}
                                                    {span.surface && (
                                                        <small>
                                                            surface:{" "}
                                                            {humanizePredicate(span.surface)}
                                                        </small>
                                                    )}
                                                </figcaption>
                                            </figure>
                                        ))}
                                    </div>
                                )}
                                {data.evidence_passages?.length ? (
                                    <div className="evidence-passages">
                                        {data.evidence_passages.map((passage) => (
                                            <Link
                                                href={entityHref("PASSAGE", passage.id)}
                                                key={passage.id}
                                            >
                                                <span>{passage.label}</span>
                                                {passage.description && (
                                                    <p>{passage.description}</p>
                                                )}
                                                <ArrowRight size={16} aria-hidden="true" />
                                            </Link>
                                        ))}
                                    </div>
                                ) : (
                                    !spans.length && (
                                        <p className="muted">
                                            No quoted passage is attached to this relationship. It
                                            was derived over the layer as a whole rather than read
                                            off one verse, so read its derivation and its caveat
                                            before relying on it.
                                        </p>
                                    )
                                )}
                            </section>

                            {data.relationship.caveat?.text && (
                                <aside className="caveat-text">
                                    {data.relationship.caveat.text}
                                </aside>
                            )}

                            <details className="evidence-technical">
                                <summary>Technical details</summary>
                                <dl>
                                    <div>
                                        <dt>Predicate</dt>
                                        <dd>{data.relationship.type}</dd>
                                    </div>
                                    <div>
                                        <dt>Method</dt>
                                        <dd>{data.method ?? "Not recorded"}</dd>
                                    </div>
                                    <div>
                                        <dt>Trust tier</dt>
                                        <dd>{data.trust_tier ?? "Not recorded"}</dd>
                                    </div>
                                    <div>
                                        <dt>Derivation</dt>
                                        <dd>{data.derivation ?? "Not recorded"}</dd>
                                    </div>
                                    <div>
                                        <dt>Confidence basis</dt>
                                        <dd>
                                            {humanizePredicate(data.relationship.confidence_basis)}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt>Relationship id</dt>
                                        <dd className="mono">{data.relationship.id}</dd>
                                    </div>
                                </dl>
                            </details>

                            {data.caveats?.map((caveat) => (
                                <aside className="caveat-text" key={caveat.text}>
                                    {caveat.text}
                                </aside>
                            ))}
                        </div>
                    )}
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
