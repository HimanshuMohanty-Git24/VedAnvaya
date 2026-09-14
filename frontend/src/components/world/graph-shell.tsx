"use client";

import Link from "next/link";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { encoded } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";
import type { World, WorldLabels } from "@/lib/world/artifact";
import type { WorldEngine } from "@/lib/world/engine";
import { useGraphState } from "@/lib/world/graph-state";
import { RENDERERS, RENDERER_COPY, VIEWS, VIEW_COPY } from "@/lib/world/modes";
import { PathTrace } from "./path-trace";
import { PlanarView } from "./planar-view";
import { WorldView, type WorldSelection } from "./world-view";

/**
 * One graph, on two axes.
 *
 * What the reader is exploring - the world, one subject, a route between two - and how it is
 * drawn. They were one control and one state field, and that conflation was a release
 * blocker: a URL written while looking at the world read back as a request for a different
 * renderer, so selecting anything moved the reader somewhere they had not asked to go.
 *
 * All state now comes from `useGraphState`, which owns the precedence between the URL, a
 * remembered preference and what the device can draw, and resolves it once. Nothing in this
 * component writes to the URL directly, and there is no path from a selection to a renderer.
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
    const graph = useGraphState();
    const { state } = graph;

    const [world, setWorld] = useState<World | null>(null);
    const [labels, setLabels] = useState<WorldLabels | null>(null);
    const [engine, setEngine] = useState<WorldEngine | null>(null);
    const [selection, setSelection] = useState<WorldSelection | null>(null);
    const [query, setQuery] = useState(state.query ?? "");
    const [pathNodes, setPathNodes] = useState<number[]>([]);
    const [hintDismissed, setHintDismissed] = useState(false);
    const deferred = useDeferredValue(query);
    const appliedDeepLink = useRef(false);

    const indexOfId = useCallback(
        (id: string | null) => {
            if (!id || !labels) return null;
            const index = labels.ids.indexOf(id);
            return index >= 0 ? index : null;
        },
        [labels],
    );

    /*
     * Selecting moves the camera and deepens the view.
     *
     * It cannot touch the renderer, and that is structural rather than careful: there is no
     * call to `setRenderer` reachable from here. The regression tests assert the same thing
     * from the state model's side.
     */
    const selectNode = useCallback(
        (node: number | null) => {
            const id = node !== null && labels ? labels.ids[node] : null;
            graph.select(id);
            if (node !== null && engine) {
                engine.select(node);
                engine.focusNode(node);
            } else if (engine) {
                engine.select(null);
            }
        },
        [engine, labels, graph],
    );

    const onReady = useCallback(
        (loaded: World, loadedLabels: WorldLabels, loadedEngine: WorldEngine) => {
            setWorld(loaded);
            setLabels(loadedLabels);
            setEngine(loadedEngine);
        },
        [],
    );

    /* A deep link is applied once. Re-applying it would fight the reader on every selection. */
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

    /* The renderer decides which stage is shown; the view decides what it is showing. */
    const spatial = state.renderer === "3d";
    const selectedIndex = indexOfId(state.node);

    return (
        <div className="va-graph" data-renderer={state.renderer} data-view={state.view}>
            {/* The spatial engine is mounted once and kept mounted across every change. A
                canvas that unmounts loses its context, its buffers and its camera, and a
                renderer switch would mean a blank flash and a reload of a 2 MB artifact. */}
            <div className="va-graph-stage" data-active={spatial}>
                <WorldView
                    initialNodeId={state.node}
                    onReady={onReady}
                    onRendererLost={(detail) =>
                        graph.reportRendererFailure("context-lost", detail)
                    }
                    onSelect={setSelection}
                    pathNodes={pathNodes}
                    paused={!spatial}
                />
            </div>

            {state.renderer === "2d" && world && (
                <div className="va-graph-stage is-planar" data-active>
                    {/* The view decides what the planar canvas draws; the renderer only
                        decided that it is the one drawing. World and Focus are the same two
                        semantic levels here as in the spatial view. */}
                    <PlanarView
                        labels={labels}
                        onInspectEdge={() => {}}
                        onSelect={selectNode}
                        root={selectedIndex}
                        scope={state.view === "FOCUS" && selectedIndex !== null ? "focus" : "world"}
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
                 * Two rows, because there are two questions.
                 *
                 * The previous version put World, 3D, 2D and Path on one line, which said the
                 * four were alternatives - and the state behind it believed that too, which is
                 * what let a selection change the renderer. Separating them on screen is the
                 * same correction as separating them in the model.
                 */}
                <div className="va-graph-switch">
                    <nav aria-label="What to explore" className="va-graph-modes">
                        {VIEWS.map((view) => (
                            <button
                                aria-current={state.view === view ? "true" : undefined}
                                key={view}
                                onClick={() => graph.setView(view)}
                                title={VIEW_COPY[view].note}
                                type="button"
                            >
                                {VIEW_COPY[view].label}
                            </button>
                        ))}
                    </nav>
                    <nav aria-label="How it is drawn" className="va-graph-modes is-renderer">
                        {RENDERERS.map((renderer) => (
                            <button
                                aria-current={state.renderer === renderer ? "true" : undefined}
                                key={renderer}
                                onClick={() => graph.setRenderer(renderer)}
                                title={RENDERER_COPY[renderer].note}
                                type="button"
                            >
                                {RENDERER_COPY[renderer].label}
                            </button>
                        ))}
                    </nav>
                </div>

                {state.view !== "PATH" && (
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

                {state.view === "PATH" && world && (
                    <PathTrace
                        from={state.from}
                        labels={labels}
                        onEndpoints={(from, to) => graph.setEndpoints(from, to)}
                        onPathNodes={setPathNodes}
                        to={state.to}
                        world={world}
                    />
                )}

                {/* A renderer chosen for the reader always says so and always offers the other
                    one. Nothing about how this graph is drawn changes quietly. */}
                {graph.fallback && (
                    <p className="va-graph-notice" role="status">
                        Drawing this flat: {graph.fallback.detail}.{" "}
                        <button onClick={() => graph.setRenderer("3d")} type="button">
                            Use the spatial view anyway
                        </button>
                    </p>
                )}

                {!hintDismissed && world && spatial && !selection && (
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
                        {/* Changing how the graph is drawn is the reader asking for it, so it
                            is remembered like any other explicit choice. */}
                        <button onClick={() => graph.setRenderer(spatial ? "2d" : "3d")} type="button">
                            {spatial ? "Pull its connections apart" : "See where it sits"}
                        </button>
                        <button
                            onClick={() => graph.setEndpoints(selection.id, state.to)}
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
