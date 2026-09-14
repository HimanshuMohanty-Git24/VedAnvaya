"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { encoded } from "@/lib/api";
import { humanizePredicate } from "@/lib/knowledge";
import type { World, WorldLabels } from "@/lib/world/artifact";

/**
 * Path tracing: how one subject reaches another.
 *
 * The backend has answered this since before the graph was rebuilt - `/graph/path` runs
 * `allShortestPaths` over a whitelist of predicates and ranks routes by their lowest
 * worst-waypoint degree - and nothing in the product has ever called it. A capability nobody
 * can reach is not a capability, so this is the interface for it.
 *
 * ## Why the route is explained rather than drawn
 *
 * A path drawn as three highlighted lines says that a connection exists. What a reader wants
 * to know is what kind of connection, and whether it means anything: two deities joined
 * through a metre they happen to share are connected in a way that establishes very little,
 * and two joined through a hymn that names both are connected in a way that establishes
 * rather a lot. So each hop states its relationship, and the service's own `hub_mediated`
 * flag - set when the route runs through a very busy waypoint - is surfaced rather than
 * hidden, because it is the difference between those two cases.
 */

type PathNode = {
    id: string;
    type: string;
    label: string;
    is_deity?: boolean | null;
};

type PathRelationship = {
    id: string;
    type: string;
    /** Already in words: the service sends "co-occurs with", not CO_OCCURS_WITH. */
    label: string;
    evidence?: { tier?: string | null; method?: string | null } | null;
    score?: number | null;
};

type PathHop = {
    index: number;
    source: PathNode;
    target: PathNode;
    relationship: PathRelationship;
    /**
     * The service's own prose for this step, and the reason this surface is scholarship
     * rather than decoration.
     *
     * It is written by the API, carries the same "what it does not establish" clause the rest
     * of the product uses, and is reproduced verbatim. Re-phrasing it here, or generating a
     * narrative around it, would fork an epistemic policy that is deliberately central.
     */
    explanation?: string | null;
};

export type PathView = {
    source: PathNode;
    target: PathNode;
    length: number;
    hops: PathHop[];
    /** Set by the service where the route passes through a very highly connected waypoint. */
    hub_mediated?: boolean | null;
    caveats?: Array<{ text: string; source: string }> | null;
};

/**
 * Only the outcome of a request is stored.
 *
 * Whether the form is idle is not a fact about the request, it is a fact about whether both
 * endpoints are set - which the props already say. Storing it as well meant writing state
 * synchronously inside the effect that watches those props, which cascades a second render on
 * every keystroke that clears a field.
 */
type Outcome =
    | { kind: "TRACING" }
    | { kind: "FOUND"; path: PathView }
    | { kind: "NONE" }
    | { kind: "FAILED"; message: string };

export function PathTrace({
    world,
    labels,
    from,
    to,
    onEndpoints,
    onPathNodes,
}: {
    world: World;
    labels: WorldLabels | null;
    from: string | null;
    to: string | null;
    onEndpoints: (from: string | null, to: string | null) => void;
    /** Node indices along the route, so the spatial view can frame and emphasise them. */
    /**
     * The route, as node indices, and the phrase for each step between them.
     *
     * The phrases are sent with the route rather than looked up again by the canvas, because the
     * service already resolved them from the same curated table the artifact was exported from.
     * Re-deriving them from the artifact would mean matching an API hop back to an edge index and
     * could disagree with the list the reader is looking at.
     */
    onPathNodes: (nodes: number[], hops: string[]) => void;
}) {
    const [outcome, setOutcome] = useState<Outcome | null>(null);
    /*
     * The fields are uncontrolled, and keyed on the endpoints.
     *
     * Mirroring a prop into state and syncing it in an effect is the standard way to write a
     * cascading render, and it is unnecessary here: what the field should say when the
     * endpoints change is exactly its initial value, so remounting it by key says that
     * without a second render or a second source of truth.
     */
    const fromRef = useRef<HTMLInputElement>(null);
    const toRef = useRef<HTMLInputElement>(null);

    const nameOf = useCallback(
        (id: string | null) => {
            if (!id || !labels) return id ?? "";
            const index = labels.ids.indexOf(id);
            return index >= 0 ? labels.labels[index] || id : id;
        },
        [labels],
    );

    useEffect(() => {
        if (!from || !to) {
            onPathNodes([], []);
            return;
        }
        const controller = new AbortController();
        void (async () => {
            try {
                setOutcome({ kind: "TRACING" });
                const response = await fetch(
                    `/backend/graph/path?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&max_depth=4`,
                    { signal: controller.signal },
                );
                if (!response.ok) {
                    // A 404 here is a real answer: no route inside the depth the service
                    // searches. It is not an error and must not be reported as one.
                    if (response.status === 404) {
                        setOutcome({ kind: "NONE" });
                        onPathNodes([], []);
                        return;
                    }
                    throw new Error("The route could not be traced.");
                }
                const path = (await response.json()) as PathView;
                setOutcome({ kind: "FOUND", path });

                if (labels) {
                    const ids = [
                        path.source.id,
                        ...path.hops.map((hop) => hop.target.id),
                    ];
                    const indices = ids
                        .map((id) => labels.ids.indexOf(id))
                        .filter((index) => index >= 0);
                    onPathNodes(
                        indices,
                        path.hops.map((hop) => hop.relationship.label),
                    );
                }
            } catch (reason) {
                if (controller.signal.aborted) return;
                setOutcome({
                    kind: "FAILED",
                    message:
                        reason instanceof Error ? reason.message : "The route could not be traced.",
                });
                onPathNodes([], []);
            }
        })();
        return () => controller.abort();
    }, [from, to, labels, onPathNodes]);

    /** Resolve typed text to a canonical id, preferring an exact name over a substring. */
    const resolve = useCallback(
        (text: string): string | null => {
            if (!labels) return null;
            const needle = text.trim().toLowerCase();
            if (!needle) return null;
            if (needle.startsWith("vg:")) return text.trim();
            let best: number | null = null;
            let bestScore = Infinity;
            for (const hub of world.manifest.hubs) {
                const label = (labels.labels[hub] ?? "").toLowerCase();
                if (!label) continue;
                if (label === needle) return labels.ids[hub];
                if (label.includes(needle) && label.length < bestScore) {
                    bestScore = label.length;
                    best = hub;
                }
            }
            if (best !== null) return labels.ids[best];
            for (let i = 0; i < labels.labels.length; i += 1) {
                if ((labels.labels[i] ?? "").toLowerCase() === needle) return labels.ids[i];
            }
            return null;
        },
        [labels, world],
    );

    return (
        <section aria-label="Trace a connection" className="va-path">
            <form
                className="va-path-form"
                onSubmit={(event) => {
                    event.preventDefault();
                    onEndpoints(
                    resolve(fromRef.current?.value ?? ""),
                    resolve(toRef.current?.value ?? ""),
                );
                }}
            >
                <div className="va-path-fields">
                    <label>
                        <span>From</span>
                        <input
                            autoComplete="off"
                            defaultValue={nameOf(from)}
                            key={`from-${from ?? ""}`}
                            placeholder="Agni"
                            ref={fromRef}
                        />
                    </label>
                    <label>
                        <span>To</span>
                        <input
                            autoComplete="off"
                            defaultValue={nameOf(to)}
                            key={`to-${to ?? ""}`}
                            placeholder="Indra"
                            ref={toRef}
                        />
                    </label>
                </div>
                <button className="va-path-go" type="submit">
                    Trace the connection
                </button>
            </form>

            {outcome?.kind === "TRACING" && (
                <p className="va-path-status" role="status">
                    Looking for the shortest route…
                </p>
            )}

            {outcome?.kind === "NONE" && (
                <p className="va-path-status">
                    No route of four steps or fewer joins these two. That is a limit of what this
                    build records, not a statement that the Vedas hold no connection between them.
                </p>
            )}

            {outcome?.kind === "FAILED" && (
                <p className="va-path-status is-failed" role="alert">
                    {outcome.message}
                </p>
            )}

            {outcome?.kind === "FOUND" && (
                <div className="va-path-route">
                    <p className="va-path-summary">
                        {outcome.path.length} {outcome.path.length === 1 ? "step" : "steps"} from{" "}
                        <strong>{outcome.path.source.label}</strong> to{" "}
                        <strong>{outcome.path.target.label}</strong>
                    </p>

                    {outcome.path.hub_mediated && (
                        /*
                         * The most important sentence on this surface.
                         *
                         * A route through a waypoint that is attached to thousands of things
                         * is nearly always available between any two subjects, and reading it
                         * as a meaningful relationship is the single easiest mistake to make
                         * with a shortest path. The service flags it; hiding the flag would
                         * make every pair look connected.
                         */
                        <p className="va-path-caution">
                            This route passes through a very highly connected waypoint. Such a
                            route exists between almost any two subjects and is weak evidence of
                            a relationship between these two in particular.
                        </p>
                    )}

                    <ol className="va-path-steps">
                        <li className="va-path-step is-end">
                            <span className="va-path-node">{outcome.path.source.label}</span>
                            <span className="va-path-kind">
                                {humanizePredicate(outcome.path.source.type)}
                            </span>
                        </li>
                        {outcome.path.hops.map((hop) => (
                            <li className="va-path-step" key={`${hop.index}-${hop.target.id}`}>
                                <span className="va-path-relation">
                                    {hop.relationship?.label ??
                                        humanizePredicate(hop.relationship?.type ?? "related to")}
                                </span>
                                <span className="va-path-node">{hop.target.label}</span>
                                <span className="va-path-kind">
                                    {humanizePredicate(hop.target.type)}
                                </span>
                                {hop.explanation && (
                                    <p className="va-path-why">{hop.explanation}</p>
                                )}
                                {hop.target.id.startsWith("VG:") &&
                                    /:(RV|SV|YV|AV):/.test(hop.target.id) && (
                                        <Link
                                            className="va-path-read"
                                            href={`/passage/${encoded(hop.target.id)}`}
                                        >
                                            Read this passage
                                        </Link>
                                    )}
                            </li>
                        ))}
                    </ol>

                    {outcome.path.caveats?.length ? (
                        <ul className="va-path-caveats">
                            {outcome.path.caveats.map((caveat) => (
                                <li key={`${caveat.source}-${caveat.text}`}>{caveat.text}</li>
                            ))}
                        </ul>
                    ) : null}
                </div>
            )}
        </section>
    );
}
