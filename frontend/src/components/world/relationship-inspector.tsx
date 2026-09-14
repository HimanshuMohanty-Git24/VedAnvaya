"use client";

import { useEffect, useId, useRef } from "react";
import type { World } from "@/lib/world/artifact";
import { describePredicate, edgePredicate, type PredicateTable } from "@/lib/world/predicates";

/**
 * What one connection asserts, and what it does not.
 *
 * ## Why the second half is the point
 *
 * Naming a relationship on the map answers "what kind of line is this". It does not answer the
 * question a reader with any scholarly instinct asks next, which is "on what basis, and how far
 * does that go". Those answers exist, curated, in the same table the phrase comes from: every
 * predicate carries a sentence saying what it claims and a sentence saying what it does not
 * establish - that 15,177 of 17,889 seer ascriptions are a hymn's label projected onto each of
 * its verses, that an "exact" parallel is exact only on the weakest surface two scripts share.
 *
 * A graph that shows the first without the second invites exactly the misreading this corpus is
 * most vulnerable to: taking a drawn line as a claim of fact rather than as a record of what one
 * layer of evidence supports.
 *
 * ## When it says nothing
 *
 * Three predicates in the artifact have no curated explanation, because they are structural and
 * the API does not traverse them. For those the phrase is derived from the predicate's own name
 * and `basis` says so, and this declines to show an explanation rather than presenting a
 * generated sentence in the voice of the ones a scholar wrote.
 *
 * ## Why it is a dialog and where the focus goes
 *
 * It is opened by activating a control - a phrase on the canvas with a pointer, or a row in the
 * relations list with a keyboard - and it is the answer to that activation, so it takes focus and
 * gives it back. Not modal: the map behind it stays usable, and trapping a reader inside a
 * three-sentence explanation would be worse than not offering one. So `role="dialog"` with a
 * label and no `aria-modal`, focus moved to the heading on open, and focus returned to whatever
 * opened it on close - which is the only thing that makes the keyboard path a loop rather than a
 * one-way trip into a panel the reader then has to tab out of from the top of the document.
 */

export function RelationshipInspector({
    world,
    labels,
    predicates,
    edge,
    onClose,
    onSelect,
}: {
    world: World | null;
    labels: { ids: string[]; labels: string[] } | null;
    predicates: PredicateTable | null;
    /** Index into the world edge arrays, or null when nothing is being inspected. */
    edge: number | null;
    onClose: () => void;
    onSelect: (node: number) => void;
}) {
    const headingId = useId();
    const headingRef = useRef<HTMLParagraphElement>(null);
    /**
     * The control that opened it.
     *
     * Captured at the moment it opens rather than passed in, because the two things that open it
     * are a DOM span outside React's tree and a button inside it, and neither can name the other.
     * Restored only if it is still in the document: a reader who chooses one of the two subjects
     * in the statement has navigated away, and the row they clicked may not exist any more.
     */
    const invoker = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (edge === null) {
            const target = invoker.current;
            invoker.current = null;
            if (target && document.contains(target)) target.focus();
            return;
        }
        invoker.current = document.activeElement as HTMLElement | null;
        /* The heading rather than the close button. Announcing "close" as the first thing a
           reader hears on opening an explanation tells them how to leave before it has told them
           what they are in. */
        headingRef.current?.focus();
    }, [edge]);

    /* Negative keys are path hops, which are explained in the route list rather than here, and a
       non-integer is a click that read a stale attribute off a hidden label. Neither is an edge. */
    if (
        world === null ||
        edge === null ||
        !Number.isInteger(edge) ||
        edge < 0 ||
        edge >= world.manifest.counts.edges
    ) {
        return null;
    }

    const predicate = edgePredicate(world, edge);
    const semantics = describePredicate(predicates, predicate);
    if (!predicate || !semantics) return null;

    const source = world.edgePairs[edge * 2];
    const target = world.edgePairs[edge * 2 + 1];
    const name = (node: number) => labels?.labels[node] ?? `Subject ${node}`;
    const curated = semantics.basis === "CURATED";

    return (
        <aside
            aria-labelledby={headingId}
            className="va-relationship"
            /* Escape closes it, handled here rather than on the document. The page has its own
               Escape listener with a larger meaning, and a reader inside a dialog pressing Escape
               means "close this", not "leave the subject I am reading". Focus is inside this
               element, so this handler sees the key first and stops it going further. */
            onKeyDown={(event) => {
                if (event.key !== "Escape") return;
                event.stopPropagation();
                onClose();
            }}
            role="dialog"
        >
            <div className="va-relationship-head">
                <p
                    className="va-relationship-kind"
                    id={headingId}
                    ref={headingRef}
                    tabIndex={-1}
                >
                    Relationship
                </p>
                <button
                    aria-label="Close the relationship"
                    className="va-relationship-close"
                    onClick={onClose}
                    type="button"
                >
                    Close
                </button>
            </div>

            {/*
             * Set as a sentence with the two subjects in it, in stored order. That order is the
             * reading order and nothing more: of the sixty predicates the exported vocabulary
             * declares, eight declare a direction at all - five DIRECTED and three SYMMETRIC - so
             * an arrowhead here would assert something the ontology declines to state for the
             * other fifty-two. Where symmetry *is* declared, the note below says so outright.
             *
             * The figure to quote is 8 of 60, verified against `world.predicates.json` and the
             * artifact's 48 edge types, all eight of which are drawable. This comment previously
             * said "ten of fifty-seven", which was wrong in both numbers.
             */}
            <p className="va-relationship-statement">
                <button onClick={() => onSelect(source)} type="button">
                    {name(source)}
                </button>
                <span className="va-relationship-phrase">{semantics.phrase}</span>
                <button onClick={() => onSelect(target)} type="button">
                    {name(target)}
                </button>
            </p>

            {curated ? (
                <dl className="va-relationship-facts">
                    <dt>What it asserts</dt>
                    <dd>{semantics.asserts}</dd>
                    <dt>What it does not establish</dt>
                    <dd>{semantics.limit}</dd>
                </dl>
            ) : (
                <p className="va-relationship-uncurated">
                    No curated explanation is recorded for this relationship, so what it does and
                    does not establish is not stated here. Treat it as unexplained rather than as
                    unqualified.
                </p>
            )}

            <p className="va-relationship-meta">
                <span>{predicate}</span>
                {semantics.direction === "SYMMETRIC" ? (
                    <span>
                        Symmetric: the order of the two subjects carries no claim. It is stored one
                        way round because something had to be.
                    </span>
                ) : semantics.direction === "DIRECTED" ? (
                    <span>Directed: it reads from the first subject to the second.</span>
                ) : (
                    <span>The ontology declares no direction for this relationship.</span>
                )}
            </p>
        </aside>
    );
}
