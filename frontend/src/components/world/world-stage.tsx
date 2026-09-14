"use client";

import Link from "next/link";
import { use, useCallback, useDeferredValue, useMemo, useState } from "react";
import { encoded } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";
import type { World, WorldLabels } from "@/lib/world/artifact";
import type { WorldEngine } from "@/lib/world/engine";
import { WorldView, type WorldSelection } from "./world-view";

/**
 * The page around the world.
 *
 * The map dominates; the chrome recedes. What is deliberately absent is a dashboard - no
 * floating panel stack, no HUD, no permanently open filter drawer. There is a map, a way in
 * by name, and a panel that exists only once something has been chosen.
 *
 * ## The list is not a fallback
 *
 * The index beside the map is the same graph, and it is reachable by keyboard and by screen
 * reader whether or not WebGL ever starts. This is not a degraded mode offered apologetically
 * to people who cannot use the canvas: a spatial view answers "where does this sit", and a
 * list answers "what is this attached to", and the second question is the one a reader
 * checking a citation actually has. Making 35,370 points individually tabbable would satisfy
 * a checklist and help nobody; a searchable list of names and a navigable list of connections
 * is what the canvas is a picture of.
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

/** Diacritics folded, so "agnih" finds "agniḥ". */
function fold(value: string) {
    return value
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();
}

type Hit = { index: number; label: string; group: string };

export function WorldStage({ searchParams }: { searchParams: Promise<{ node?: string }> }) {
    const { node: initialNode } = use(searchParams);
    const [selection, setSelection] = useState<WorldSelection | null>(null);
    const [query, setQuery] = useState("");
    /* State, not refs. All three are read during render - the heading, the search results
       and the connection list - and a ref read during render does not schedule one, so the
       page would show the loading title after the world had arrived. */
    const [world, setWorld] = useState<World | null>(null);
    const [labels, setLabels] = useState<WorldLabels | null>(null);
    const [engine, setEngine] = useState<WorldEngine | null>(null);

    // Typing must not block on scanning 35,370 labels; the input stays responsive and the
    // result list catches up.
    const deferred = useDeferredValue(query);

    const onReady = useCallback(
        (loaded: World, loadedLabels: WorldLabels, loadedEngine: WorldEngine) => {
            setWorld(loaded);
            setLabels(loadedLabels);
            setEngine(loadedEngine);
        },
        [],
    );

    const hits = useMemo<Hit[]>(() => {
        const needle = fold(deferred.trim());
        if (!world || !labels || needle.length < 2) return [];
        const out: Hit[] = [];
        /* Hubs first, so a two-letter query surfaces Indra before a verse that happens to
           contain the same letters. Degree order is already the artifact's hub order. */
        const order = [
            ...world.manifest.hubs,
            ...Array.from({ length: labels.labels.length }, (_, i) => i),
        ];
        const seen = new Set<number>();
        for (const index of order) {
            if (out.length >= 24) break;
            if (seen.has(index)) continue;
            seen.add(index);
            const label = labels.labels[index];
            if (!label || !fold(label).includes(needle)) continue;
            out.push({
                index,
                label,
                group: world.manifest.groups[world.nodeGroup[index]],
            });
        }
        return out;
    }, [deferred, world, labels]);

    const goTo = useCallback(
        (index: number) => {
            if (!engine) return;
            engine.select(index);
            engine.focusNode(index);
        },
        [engine],
    );

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

    return (
        <div className="va-world-stage">
            <WorldView
                initialNodeId={initialNode ?? null}
                onReady={onReady}
                onSelect={setSelection}
            />

            <div className="va-world-chrome">
                <header className="va-world-head">
                    <p className="va-world-kicker">The world</p>
                    <h1>
                        {world
                            ? `${world.manifest.counts.nodes.toLocaleString("en-GB")} subjects, connected`
                            : "The corpus, connected"}
                    </h1>
                </header>

                <form
                    className="va-world-find"
                    onSubmit={(event) => {
                        event.preventDefault();
                        if (hits[0]) goTo(hits[0].index);
                    }}
                    role="search"
                >
                    <label htmlFor="world-find">Find a subject</label>
                    <input
                        autoComplete="off"
                        id="world-find"
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="A deity, a seer, an idea…"
                        type="search"
                        value={query}
                    />
                    {hits.length > 0 && (
                        <ul className="va-world-hits">
                            {hits.map((hit) => (
                                <li key={hit.index}>
                                    <button onClick={() => goTo(hit.index)} type="button">
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
                            No subject in this build answers to that. That is a limit of what is
                            held here, not a statement about the Vedas.
                        </p>
                    )}
                </form>
            </div>

            {selection && (
                <aside aria-label="The selected subject" className="va-world-panel">
                    <p className="va-world-panel-kind">
                        {GROUP_LABEL[selection.group] ?? selection.group}
                    </p>
                    <h2>{selection.label || selection.id}</h2>

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
                        {selection.id.startsWith("VG:") && selection.group !== "passage" && (
                            <Link href={entityHref(selection.type, selection.id)}>
                                Open the record
                            </Link>
                        )}
                        {selection.group === "passage" && (
                            <Link href={`/passage/${encoded(selection.id)}`}>
                                Read the passage
                            </Link>
                        )}
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
                            {/* The navigable half of the view. Every one of these moves the
                                map as well, so keyboard and pointer reach the same places. */}
                            <ul>
                                {neighbourRows.map((row) => (
                                    <li key={row.index}>
                                        <button onClick={() => goTo(row.index)} type="button">
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
