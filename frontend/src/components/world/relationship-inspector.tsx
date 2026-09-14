"use client";

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
        <aside aria-label="The selected relationship" className="va-relationship">
            <div className="va-relationship-head">
                <p className="va-relationship-kind">Relationship</p>
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
             * reading order and nothing more: only ten of fifty-seven predicates declare a
             * direction at all, so an arrowhead here would assert something the ontology does
             * not. Where symmetry *is* declared, the note below says so outright.
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
