"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { encoded } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";
import type { World, WorldLabels } from "@/lib/world/artifact";
import { probeCapability, recallMode, rememberMode } from "@/lib/world/capability";
import type { WorldEngine } from "@/lib/world/engine";
import {
    GRAPH_MODES,
    MODE_COPY,
    graphStateToQuery,
    parseGraphState,
    switchMode,
    type GraphMode,
} from "@/lib/world/modes";
import { PathTrace } from "./path-trace";
import { PlanarView } from "./planar-view";
import { WorldView, type WorldSelection } from "./world-view";

/**
 * One graph, four ways of looking at it.
 *
 * This replaces two disconnected things: a 2D explorer at `/graph` that the product linked to,
 * and a spatial world at `/graph/world` that nothing linked to. Whichever of those was better
 * did not matter, because a reader only ever saw one of them.
 *
 * The modes here are views over one piece of state. Switching from the world to the planar
 * diagram keeps the subject you were looking at; entering path tracing offers it as a starting
 * point; every one of them writes to the same URL, so any view of the graph can be sent to
 * someone. The chrome is a thin index line rather than a tab bar, and the panel only exists
 * once something is selected: when a page is mostly a map, everything that is not the map has
 * to earn its space.
 */

const GROUP_LABEL: Record<string, string> = {
    deity: "Deity",
    "unresolved-deity": "Unresolved devata slot",
    passage: "Passage",
    person: "Seer",
    idea: "Idea",
    rite: "Rite",
    thing: "Thing",
    wording: "Wording",
    derived: "Derived metric",
    record: "Evidence record",
    other: "Other",
};

function fold(value: string) {
    return value
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();
}

type Hit = { index: number; label: string; group: string };

export function GraphShell() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const state = useMemo(
        () => parseGraphState(new URLSearchParams(searchParams.toString())),
        [searchParams],
    );

    const [world, setWorld] = useState<World | null>(null);
    const [labels, setLabels] = useState<WorldLabels | null>(null);
    const [engine, setEngine] = useState<WorldEngine | null>(null);
    const [selection, setSelection] = useState<WorldSelection | null>(null);
    const [query, setQuery] = useState(state.query ?? "");
    const [pathNodes, setPathNodes] = useState<number[]>([]);
    const [notice, setNotice] = useState<string | null>(null);
    const [hintDismissed, setHintDismissed] = useState(false);
    const deferred = useDeferredValue(query);
    const appliedDeepLink = useRef(false);

    /* -------------------------------------------------------- capability - */

    useEffect(() => {
        /*
         * The probe runs in a microtask rather than in the effect body.
         *
         * It writes the degraded-mode notice, and a synchronous write inside an effect
         * cascades a second render before the first has painted. Deferring it by a tick also
         * means the canvas gets to start before the page is asked to re-render, which is the
         * order that matters on the device this branch is for.
         */
        const timer = window.setTimeout(() => {
        const report = probeCapability();
        if (report.capability === "FLAT" && state.mode !== "2D") {
            /*
             * Degraded, and said out loud.
             *
             * Silently serving a different experience is how a product ends up with users who
             * think it is worse than it is. The reader is told what happened, why, and is
             * given the way back.
             */
            setNotice(
                `Showing the planar view: ${report.reason}. You can still try the spatial view.`,
            );
            router.replace(
                `${pathname}${graphStateToQuery(switchMode(state, "2D"))}`,
                { scroll: false },
            );
            return;
        }
        // An explicit previous choice outranks anything measured, but only when the URL has
        // not asked for something specific.
        if (!searchParams.has("mode") && !searchParams.has("node")) {
            const remembered = recallMode();
            if (remembered && remembered !== state.mode) {
                const mode = (GRAPH_MODES as readonly string[]).includes(remembered)
                    ? (remembered as GraphMode)
                    : null;
                if (mode) {
                    router.replace(`${pathname}${graphStateToQuery({ ...state, mode })}`, {
                        scroll: false,
                    });
                }
            }
        }
        }, 0);
        return () => window.clearTimeout(timer);
        // Runs once on mount: this is a measurement of the device, not of the state.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /* ------------------------------------------------------------- state - */

    const push = useCallback(
        (next: Parameters<typeof graphStateToQuery>[0]) => {
            router.replace(`${pathname}${graphStateToQuery(next)}`, { scroll: false });
        },
        [router, pathname],
    );

    const setMode = useCallback(
        (mode: GraphMode) => {
            rememberMode(mode);
            setNotice(null);
            push(switchMode(state, mode));
        },
        [push, state],
    );

    const indexOfId = useCallback(
        (id: string | null) => {
            if (!id || !labels) return null;
            const index = labels.ids.indexOf(id);
            return index >= 0 ? index : null;
        },
        [labels],
    );

    const selectNode = useCallback(
        (node: number | null) => {
            const id = node !== null && labels ? labels.ids[node] : null;
            push({ ...state, node: id });
            if (node !== null && engine) {
                engine.select(node);
                engine.focusNode(node);
            } else if (engine) {
                engine.select(null);
            }
        },
        [engine, labels, push, state],
    );

    const onReady = useCallback(
        (loaded: World, loadedLabels: WorldLabels, loadedEngine: WorldEngine) => {
            setWorld(loaded);
            setLabels(loadedLabels);
            setEngine(loadedEngine);
        },
        [],
    );

    /* A deep link is applied once, after the world is available, and never again: re-applying
       it would fight the reader every time they selected something else. */
    useEffect(() => {
        if (appliedDeepLink.current || !engine || !labels || !state.node) return;
        const index = labels.ids.indexOf(state.node);
        if (index >= 0) {
            engine.select(index);
            engine.focusNode(index);
        }
        appliedDeepLink.current = true;
    }, [engine, labels, state.node]);

    /* ------------------------------------------------------------ search - */

    const hits = useMemo<Hit[]>(() => {
        const needle = fold(deferred.trim());
        if (!world || !labels || needle.length < 2) return [];
        const out: Hit[] = [];
        const seen = new Set<number>();
        // Hubs first, so two letters surface Indra before a verse containing the same letters.
        const order = [
            ...world.manifest.hubs,
            ...Array.from({ length: labels.labels.length }, (_, i) => i),
        ];
        for (const index of order) {
            if (out.length >= 20) break;
            if (seen.has(index)) continue;
            seen.add(index);
            const label = labels.labels[index];
            if (!label || !fold(label).includes(needle)) continue;
            out.push({ index, label, group: world.manifest.groups[world.nodeGroup[index]] });
        }
        return out;
    }, [deferred, world, labels]);

    const neighbourRows = useMemo(() => {
        if (!selection || !world || !labels) return [];
        return selection.neighbours
            .map((index) => ({
                index,
                label: labels.labels[index] || labels.ids[index],
                group: world.manifest.groups[world.nodeGroup[index]],
                degree: world.nodeDegree[index],
            }))
            .sort((a, b) => b.degree - a.degree)
            .slice(0, 40);
    }, [selection, world, labels]);

    const constellation = useMemo(() => {
        if (!selection || !world?.manifest.constellations) return null;
        const region = world.nodeRegion[selection.index];
        if (region === 65535) return null;
        return world.manifest.constellations[region] ?? null;
    }, [selection, world]);

    const spatial = state.mode === "WORLD" || state.mode === "3D" || state.mode === "PATH";
    const selectedIndex = indexOfId(state.node);

    return (
        <div className="va-graph" data-mode={state.mode}>
            {/* The spatial engine is mounted once and kept mounted across mode changes. A
                canvas that unmounts loses its WebGL context, its buffers and its camera, and
                switching modes would mean a blank flash and a second of reloading. */}
            <div className="va-graph-stage" data-active={spatial}>
                <WorldView
                    initialNodeId={state.node}
                    onReady={onReady}
                    onSelect={setSelection}
                    pathNodes={pathNodes}
                />
            </div>

            {state.mode === "2D" && world && (
                <div className="va-graph-stage is-planar" data-active>
                    <PlanarView
                        labels={labels}
                        onInspectEdge={() => {}}
                        onSelect={selectNode}
                        root={selectedIndex ?? world.manifest.hubs[0] ?? null}
                        world={world}
                    />
                </div>
            )}

            {/* ------------------------------------------------------ chrome - */}

            <div className="va-graph-chrome">
                <header className="va-graph-head">
                    <p className="va-graph-kicker">The knowledge world</p>
                    <h1>
                        {world
                            ? `${world.manifest.counts.nodes.toLocaleString("en-GB")} subjects, connected`
                            : "The corpus, connected"}
                    </h1>
                </header>

                {/*
                 * The mode switch as an index line, not a tab bar.
                 *
                 * Four capitalised pills across the top of a map is the shape of a dashboard.
                 * Set as a ruled row of names with the current one marked, it reads as the
                 * contents of one thing rather than four tools sharing a screen.
                 */}
                <nav aria-label="How to look at the graph" className="va-graph-modes">
                    {GRAPH_MODES.map((mode) => (
                        <button
                            aria-current={state.mode === mode ? "true" : undefined}
                            key={mode}
                            onClick={() => setMode(mode)}
                            title={MODE_COPY[mode].note}
                            type="button"
                        >
                            {MODE_COPY[mode].label}
                        </button>
                    ))}
                </nav>

                {state.mode !== "PATH" && (
                    <form
                        className="va-world-find"
                        onSubmit={(event) => {
                            event.preventDefault();
                            if (hits[0]) selectNode(hits[0].index);
                        }}
                        role="search"
                    >
                        <label htmlFor="graph-find">Find a subject</label>
                        <input
                            autoComplete="off"
                            id="graph-find"
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="A deity, a seer, an idea…"
                            type="search"
                            value={query}
                        />
                        {hits.length > 0 && (
                            <ul className="va-world-hits">
                                {hits.map((hit) => (
                                    <li key={hit.index}>
                                        <button onClick={() => selectNode(hit.index)} type="button">
                                            <span className="va-world-hit-name">{hit.label}</span>
                                            <span className="va-world-hit-kind">
                                                {GROUP_LABEL[hit.group] ?? hit.group}
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                        {deferred.trim().length >= 2 && hits.length === 0 && world && (
                            <p className="va-world-nohits">
                                No subject in this build answers to that. That is a limit of what
                                is held here, not a statement about the Vedas.
                            </p>
                        )}
                    </form>
                )}

                {state.mode === "PATH" && world && (
                    <PathTrace
                        from={state.from}
                        labels={labels}
                        onEndpoints={(from, to) => push({ ...state, from, to })}
                        onPathNodes={setPathNodes}
                        to={state.to}
                        world={world}
                    />
                )}

                {notice && (
                    <p className="va-graph-notice" role="status">
                        {notice}{" "}
                        <button onClick={() => setMode("3D")} type="button">
                            Try the spatial view
                        </button>
                    </p>
                )}

                {!hintDismissed && world && state.mode !== "2D" && !selection && (
                    <p className="va-graph-hint">
                        Drag to orbit, scroll to move through depth, select to follow a
                        connection.
                        <button onClick={() => setHintDismissed(true)} type="button">
                            Got it
                        </button>
                    </p>
                )}
            </div>

            {/* ------------------------------------------------------- panel - */}

            {selection && (
                <aside aria-label="The selected subject" className="va-world-panel">
                    <p className="va-world-panel-kind">
                        {GROUP_LABEL[selection.group] ?? selection.group}
                    </p>
                    <h2>{selection.label || selection.id}</h2>

                    {constellation && (
                        <p className="va-world-region">
                            in {constellation.name ?? `Constellation ${constellation.id}`}
                            <span>
                                {constellation.size.toLocaleString("en-GB")} subjects
                                {constellation.veda && constellation.veda.share >= 0.6
                                    ? `, mostly ${constellation.veda.name}`
                                    : ""}
                            </span>
                        </p>
                    )}

                    <dl className="va-world-facts">
                        <div>
                            <dt>Recorded connections</dt>
                            <dd>{selection.degree.toLocaleString("en-GB")}</dd>
                        </div>
                        <div>
                            <dt>Type</dt>
                            <dd>{selection.type}</dd>
                        </div>
                    </dl>

                    <div className="va-world-ways">
                        {selection.group === "passage" ? (
                            <Link href={`/passage/${encoded(selection.id)}`}>
                                Read the passage
                            </Link>
                        ) : (
                            selection.id.startsWith("VG:") && (
                                <Link href={entityHref(selection.type, selection.id)}>
                                    Open the record
                                </Link>
                            )
                        )}
                        <button
                            onClick={() => {
                                rememberMode("2D");
                                push({ ...switchMode(state, "2D"), node: selection.id });
                            }}
                            type="button"
                        >
                            Pull its connections apart
                        </button>
                        <button
                            onClick={() => push({ ...switchMode(state, "PATH"), from: selection.id })}
                            type="button"
                        >
                            Trace a path from here
                        </button>
                        <Link href={`/ask?entity=${encodeURIComponent(selection.id)}`}>
                            Ask about this
                        </Link>
                    </div>

                    {neighbourRows.length > 0 && (
                        <section className="va-world-neighbours">
                            <h3>
                                Connected subjects
                                <span>
                                    {neighbourRows.length < selection.degree
                                        ? `${neighbourRows.length} of ${selection.degree.toLocaleString("en-GB")}`
                                        : String(selection.degree)}
                                </span>
                            </h3>
                            <ul>
                                {neighbourRows.map((row) => (
                                    <li key={row.index}>
                                        <button onClick={() => selectNode(row.index)} type="button">
                                            <span className="va-world-hit-name">{row.label}</span>
                                            <span className="va-world-hit-kind">
                                                {GROUP_LABEL[row.group] ?? row.group}
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                            {neighbourRows.length < selection.degree && (
                                <p className="va-world-neighbours-note">
                                    The most connected are listed first. The rest are on the
                                    record page.
                                </p>
                            )}
                        </section>
                    )}
                </aside>
            )}
        </div>
    );
}
