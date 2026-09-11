"use client";

import { ArrowRight, Prohibit, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useRef } from "react";
import {
    EVIDENCE_TYPE_ORDER,
    evidenceTypeCopy,
    type AskEvidenceItem,
    type EvidenceItemType,
} from "@/lib/ask";
import { encoded } from "@/lib/api";
import { entityHref, entityTypeLabel, humanizePredicate } from "@/lib/knowledge";
import { KnowledgeStatus } from "../status";

/** `E1` becomes a DOM id the citation chips can scroll to. */
export function evidenceDomId(id: string) {
    return `ask-evidence-${id}`;
}

function groupByType(items: AskEvidenceItem[]) {
    const groups = new Map<EvidenceItemType, AskEvidenceItem[]>();
    for (const item of items) {
        const bucket = groups.get(item.type);
        if (bucket) bucket.push(item);
        else groups.set(item.type, [item]);
    }
    // Only types that actually have items are rendered, and in the reading order.
    const ordered = EVIDENCE_TYPE_ORDER.filter((type) => groups.has(type)).map((type) => ({
        type,
        items: groups.get(type) as AskEvidenceItem[],
    }));
    // Any type the backend adds later still appears rather than vanishing silently.
    const unknown = [...groups.keys()].filter((type) => !EVIDENCE_TYPE_ORDER.includes(type));
    return [
        ...ordered,
        ...unknown.map((type) => ({ type, items: groups.get(type) as AskEvidenceItem[] })),
    ];
}

export function AskEvidenceDrawer({
    open,
    items,
    focusId,
    citedIds,
    onOpenChange,
}: {
    open: boolean;
    items: AskEvidenceItem[];
    /** The item a citation chip asked for. The drawer scrolls to it once mounted. */
    focusId: string | null;
    citedIds: string[];
    onOpenChange: (value: boolean) => void;
}) {
    const contentRef = useRef<HTMLDivElement>(null);
    const groups = groupByType(items);
    const cited = new Set(citedIds);

    useEffect(() => {
        if (!open || !focusId) return;
        // Radix moves focus into the panel on open; wait a frame so our scroll wins.
        const frame = requestAnimationFrame(() => {
            // Matched on the data attribute rather than an id selector so the lookup
            // needs no escaping and cannot be broken by an id the backend changes.
            const target = contentRef.current?.querySelector<HTMLElement>(
                `[data-evidence-id="${focusId}"]`,
            );
            if (!target) return;
            target.scrollIntoView({ block: "center", behavior: "smooth" });
            target.focus({ preventScroll: true });
        });
        return () => cancelAnimationFrame(frame);
    }, [open, focusId, items]);

    return (
        <Dialog.Root open={open} onOpenChange={onOpenChange}>
            <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content className="evidence-drawer" aria-describedby="ask-evidence-intro">
                    <header>
                        <div>
                            <span>What this answer was built from</span>
                            <Dialog.Title>
                                {items.length} retrieved {items.length === 1 ? "item" : "items"}
                            </Dialog.Title>
                        </div>
                        <Dialog.Close className="icon-button" aria-label="Close the evidence panel">
                            <X size={19} aria-hidden="true" />
                        </Dialog.Close>
                    </header>

                    <div className="evidence-content" ref={contentRef}>
                        <p className="panel-note" id="ask-evidence-intro">
                            Every item below was retrieved from the graph before the answer was
                            written. {cited.size} of {items.length} were cited in the prose; the
                            rest were available and not used. Each item states what it does
                            <em> not</em> establish.
                        </p>

                        {items.length === 0 && (
                            <KnowledgeStatus
                                status="INSUFFICIENT_EVIDENCE"
                                note="Retrieval returned no items for this question, so there is nothing here to inspect."
                            />
                        )}

                        {groups.map((group) => {
                            const copy = evidenceTypeCopy(group.type);
                            return (
                                <section className="ask-evidence-group" key={group.type}>
                                    <h3>
                                        {copy.label}
                                        <span>{group.items.length}</span>
                                    </h3>
                                    <p className="ask-evidence-group-note">{copy.note}</p>
                                    <ul>
                                        {group.items.map((item) => (
                                            <EvidenceRow
                                                item={item}
                                                cited={cited.has(item.id)}
                                                key={item.id}
                                            />
                                        ))}
                                    </ul>
                                </section>
                            );
                        })}
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}

function EvidenceRow({ item, cited }: { item: AskEvidenceItem; cited: boolean }) {
    const heading =
        item.citation ??
        item.entity_label ??
        (item.source_label && item.target_label
            ? `${item.source_label} — ${item.target_label}`
            : null) ??
        item.passage_key ??
        `Evidence ${item.id}`;

    return (
        <li
            className="ask-evidence-item"
            id={evidenceDomId(item.id)}
            data-evidence-id={item.id}
            tabIndex={-1}
            data-cited={cited}
        >
            <div className="ask-evidence-head">
                <span className="ask-evidence-id">{item.id}</span>
                <div>
                    <strong>{heading}</strong>
                    <small>
                        {item.veda ? `${item.veda} · ` : ""}
                        {cited ? "cited in the answer" : "retrieved, not cited"}
                    </small>
                </div>
            </div>

            {item.sanskrit && (
                <p className="sanskrit" lang="sa">
                    {item.sanskrit}
                </p>
            )}

            {item.translation && <blockquote>{item.translation}</blockquote>}

            {item.fact && <p className="ask-evidence-fact">{item.fact}</p>}

            {item.claim_text && (
                <div className="ask-evidence-claim">
                    <span>Interpretation</span>
                    <p>{item.claim_text}</p>
                    {item.claim_source && <cite>{item.claim_source}</cite>}
                </div>
            )}

            {item.relationship_type && (
                <p className="ask-evidence-relation">
                    {item.source_label ?? "subject"}{" "}
                    <i>{humanizePredicate(item.relationship_type)}</i>{" "}
                    {item.target_label ?? "object"}
                </p>
            )}

            {item.entity_label && item.entity_type && (
                <p className="ask-evidence-meta">
                    {entityTypeLabel(item.entity_type)}
                    {item.entity_key && (
                        <>
                            {" · "}
                            <Link
                                className="text-link"
                                href={entityHref(item.entity_type, item.entity_key)}
                            >
                                Open this record
                            </Link>
                        </>
                    )}
                </p>
            )}

            {/* The qualifier is the point of the item, so it is never collapsed away. */}
            <p className="ask-qualifier">
                <Prohibit size={15} weight="duotone" aria-hidden="true" />
                <span>
                    <b>Does not establish: </b>
                    {item.qualifier ??
                        "No qualifier travelled with this item. Read its knowledge status before relying on it."}
                </span>
            </p>

            <div className="ask-evidence-footer">
                <KnowledgeStatus status={item.knowledge_status} compact />
                {item.passage_key && (
                    <Link className="text-link" href={`/passage/${encoded(item.passage_key)}`}>
                        Open passage
                        <ArrowRight size={15} aria-hidden="true" />
                    </Link>
                )}
            </div>
        </li>
    );
}
