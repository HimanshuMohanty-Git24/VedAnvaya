"use client";

import { useEffect, useState } from "react";
import type { World } from "./artifact";

/**
 * What a line between two dots means, in words a reader can use.
 *
 * ## Why this is loaded rather than written here
 *
 * A graph whose edges cannot be named is a picture of a graph. Hovering a subject has to say
 * what each connection *is* - that this line is "is ascribed to the seer" and that one is
 * "co-occurs with" - and those words are not the frontend's to invent.
 *
 * They already exist, curated, in the API's `PREDICATE_SEMANTICS`: every neighbourhood and
 * path edge the server sends carries `label` built from it. The canvases, however, do not read
 * the API - the world, the neighbourhood and the planar view are all drawn from the build
 * artifact, which carries a predicate *name* per edge and no words at all. So the same table is
 * exported offline by `scripts/export_predicate_semantics.py` and fetched here.
 *
 * Retyping it in TypeScript was the obvious alternative and it would have been wrong on the day
 * it was written. This codebase already has a general enum humaniser, `humanizePredicate`, and
 * had it been pointed at edges it would have disagreed with the curated phrasing on 44 of 57
 * predicates - "has rishi" where the scholarship says "is ascribed to the seer". Two copies of
 * one lookup have drifted apart twice in this repository. There is one copy, and it is Python's.
 *
 * ## Direction
 *
 * `direction` is what the ontology declares, not what the rows happen to look like. Most
 * predicates are UNDECLARED and are drawn without an arrowhead, because the alternative is to
 * read a direction off storage order - and storage order is not evidence here: the symmetric
 * predicates are all written one way round with no mirrored row, so an arrow derived from it
 * would assert a direction the corpus does not claim.
 *
 * ## basis
 *
 * CURATED means a scholar wrote the explanation. DERIVED_FROM_NAME means nobody did, and the
 * words are the predicate name with its underscores removed - true, but not authored. The
 * inspector says so rather than presenting a generated sentence as though it were curated.
 */

export const PREDICATE_DIRECTIONS = ["DIRECTED", "SYMMETRIC", "UNDECLARED"] as const;
export type PredicateDirection = (typeof PREDICATE_DIRECTIONS)[number];

export type PredicateSemantics = {
    /** The phrase to draw on an edge. Short: the median is 16 characters, the longest 32. */
    phrase: string;
    /** What the edge claims, in one sentence. */
    asserts: string;
    /** What it does not establish. The half a reader is most often missing. */
    limit: string;
    direction: PredicateDirection;
    basis: "CURATED" | "DERIVED_FROM_NAME";
};

export type PredicateTable = {
    version: number;
    generated: string;
    /** The Python symbol these words came from, carried so the artifact can be traced back. */
    source: string;
    predicates: Record<string, PredicateSemantics>;
};

/**
 * An unknown predicate is named, never explained.
 *
 * A predicate the table has never heard of can still be drawn - the artifact says what it is
 * called - but nothing may be claimed about it. Returning readable words with an empty
 * `asserts` lets the interface show the edge and decline to explain it, which is the honest
 * pair. Inventing a sentence here would put fabricated scholarship on a line in a graph.
 */
export function unknownPredicate(predicate: string): PredicateSemantics {
    return {
        phrase: predicate.toLowerCase().replaceAll("_", " "),
        asserts: "",
        limit: "",
        direction: "UNDECLARED",
        basis: "DERIVED_FROM_NAME",
    };
}

export function describePredicate(
    table: PredicateTable | null,
    predicate: string | null | undefined,
): PredicateSemantics | null {
    if (!predicate) return null;
    return table?.predicates[predicate] ?? unknownPredicate(predicate);
}

/** The predicate name an artifact edge carries, or null if the index is out of range. */
export function edgePredicate(world: World, edge: number): string | null {
    if (edge < 0 || edge >= world.edgeType.length) return null;
    return world.manifest.edgeTypes[world.edgeType[edge]] ?? null;
}

/** What an artifact edge means, going through the artifact's own type table. */
export function describeWorldEdge(
    world: World,
    table: PredicateTable | null,
    edge: number,
): PredicateSemantics | null {
    return describePredicate(table, edgePredicate(world, edge));
}

let cached: Promise<PredicateTable> | null = null;

/**
 * Fetched once per page, and deliberately not bundled.
 *
 * Twenty-one kilobytes, most of it the long explanations that only the inspector reads. It is
 * held outside the JavaScript bundle so that changing a scholar's wording does not invalidate
 * a code chunk, and so a page that has no use for it does not pay for it.
 *
 * That last clause used to read "the homepage - which draws no edges - never pays for it", and
 * it stopped being true when the hero became fifty real subjects with a hundred and ten real
 * connections between them. The homepage does draw edges, and a connection the reader can see
 * and not name is the defect the previous phase existed to fix. So the teaser does fetch this -
 * but lazily, on the first hover over a subject, rather than at mount: a reader who scrolls
 * past the hero without touching it still pays nothing, which is what the clause was protecting.
 */
export function loadPredicateSemantics(signal?: AbortSignal): Promise<PredicateTable> {
    if (!cached) {
        /*
         * Revalidated, not cached hard. Twenty-one kilobytes against a year-long `immutable`
         * header on a stable filename: a rebuilt artifact would leave a reader naming this
         * build's edges out of last build's vocabulary, and a 304 costs less than that is
         * worth. The large files are versioned by export hash instead - see `artifactUrl`.
         */
        cached = fetch("/world/world.predicates.json", { signal, cache: "no-cache" })
            .then((response) => {
                if (!response.ok) throw new Error("The relationship vocabulary could not be read.");
                return response.json() as Promise<PredicateTable>;
            })
            .catch((error: unknown) => {
                // A failed fetch must not poison every later attempt with a settled rejection.
                cached = null;
                throw error;
            });
    }
    return cached;
}

/**
 * The vocabulary, or null while it is still arriving.
 *
 * Null is a usable state rather than a loading gate: the graph draws immediately and edges are
 * named a moment later. Blocking the canvas on a text file would trade the thing that has to be
 * instant for the thing that only matters once a reader has pointed at something.
 */
export function usePredicateSemantics(): PredicateTable | null {
    const [table, setTable] = useState<PredicateTable | null>(null);

    useEffect(() => {
        let alive = true;
        loadPredicateSemantics()
            .then((loaded) => {
                if (alive) setTable(loaded);
            })
            .catch(() => {
                // Edges keep their names from the artifact; only the words are missing.
            });
        return () => {
            alive = false;
        };
    }, []);

    return table;
}
