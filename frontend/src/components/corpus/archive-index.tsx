"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * The finding aid.
 *
 * This replaces a caret-and-indent folder tree, and the reason is not only that a tree looks
 * like a file manager. A tree asserts that every collection is the same shape and differs only
 * in how deep you have clicked, and that is the one thing about these four corpora that is
 * false. The Rigveda runs Mandala to Sukta to Mantra; the Yajurveda puts mantras directly
 * under an Adhyaya with no hymn level at all; the Samaveda's top division is not a number but
 * four named arcikas. A tree flattens that into identical rows of triangles.
 *
 * An index descends instead. You are at one level at a time, the level is named in its own
 * vocabulary, and the trail above you says how you arrived. Nothing about the shape is written
 * down here: each response carries the name of the level below it, so a corpus with a level
 * this build has never seen would still be navigable.
 */

type Row = {
    canonical_key: string;
    canonical_citation?: string | null;
    display_label?: string | null;
    passage_type: string;
    native_levels?: string[] | null;
    hierarchy?: Record<string, string> | null;
};

type Pagination = { returned?: number | null; total?: number | null; has_more?: boolean | null };

type ChildrenResponse = {
    native_label?: string | null;
    level_key?: string | null;
    results?: { items?: Row[]; pagination?: Pagination } | null;
};

/** One rung of the descent: where we are, what the level is called, and what is under it. */
type Level = {
    /** Null at the root, where the parent is the work itself. */
    parentKey: string | null;
    /** What this level is called in this corpus: Mandala, Kanda, Adhyaya, Prapathaka. */
    label: string;
    /** How the entry we descended through was written, for the trail. */
    crumb: string;
    rows: Row[];
    total: number | null;
    hasMore: boolean;
};

const PAGE = 120;

/**
 * The part of an entry that identifies it within its level.
 *
 * Labels arrive fully qualified - "RV 1.12", "SV CHANDA 1" - which is right for a citation and
 * wrong for an index, where the division number is the thing you are scanning for and the
 * qualification is already in the trail above. The hierarchy map gives the value for this
 * level directly, so the citation is only fallen back to when it does not.
 */
function entryValue(row: Row, levelKey: string | null) {
    const hierarchy = row.hierarchy ?? {};
    if (levelKey && hierarchy[levelKey]) return hierarchy[levelKey];
    const levels = row.native_levels ?? [];
    const last = levels.at(-1);
    if (last && hierarchy[last.toLowerCase()]) return hierarchy[last.toLowerCase()];
    const values = Object.values(hierarchy);
    if (values.length) return values[values.length - 1];
    return row.canonical_citation ?? row.display_label ?? row.canonical_key;
}

function plural(count: number, noun: string) {
    const word = noun.toLowerCase();
    return `${count.toLocaleString("en-GB")} ${word}${count === 1 ? "" : "s"}`;
}

export function ArchiveIndex({
    rootRows,
    rootLabel,
    rootLevelKey,
    workLabel,
    rootTotal,
}: {
    rootRows: Row[];
    rootLabel: string;
    rootLevelKey?: string | null;
    /** The collection's own name, which is the first crumb. */
    workLabel: string;
    rootTotal?: number | null;
}) {
    const root: Level = {
        parentKey: null,
        label: rootLabel,
        crumb: workLabel,
        rows: rootRows,
        total: rootTotal ?? rootRows.length,
        hasMore: false,
    };
    const [trail, setTrail] = useState<Level[]>([root]);
    const [levelKeys, setLevelKeys] = useState<(string | null)[]>([rootLevelKey ?? null]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const headingRef = useRef<HTMLParagraphElement>(null);
    const descended = useRef(false);

    const current = trail[trail.length - 1];
    const currentLevelKey = levelKeys[levelKeys.length - 1] ?? null;

    /* Moving between levels replaces the list under the heading rather than the page, so the
       heading is where a screen reader has to be sent, and only after a move the reader made. */
    useEffect(() => {
        if (!descended.current) return;
        headingRef.current?.focus();
    }, [trail.length]);

    const fetchChildren = useCallback(
        async (key: string, offset: number): Promise<ChildrenResponse> => {
            const response = await fetch(
                `/backend/passages/${encodeURIComponent(key)}/children?limit=${PAGE}&offset=${offset}`,
            );
            if (!response.ok) throw new Error("This division could not be opened.");
            return (await response.json()) as ChildrenResponse;
        },
        [],
    );

    async function descend(row: Row) {
        descended.current = true;
        setLoading(true);
        setError(null);
        try {
            const json = await fetchChildren(row.canonical_key, 0);
            const rows = json.results?.items ?? [];
            const pagination = json.results?.pagination;
            setTrail((levels) => [
                ...levels,
                {
                    parentKey: row.canonical_key,
                    label: json.native_label ?? "entry",
                    crumb: `${current.label} ${entryValue(row, currentLevelKey)}`,
                    rows,
                    total: pagination?.total ?? rows.length,
                    hasMore: Boolean(pagination?.has_more),
                },
            ]);
            setLevelKeys((keys) => [...keys, json.level_key ?? null]);
        } catch (reason) {
            setError(
                reason instanceof Error ? reason.message : "This division could not be opened.",
            );
        } finally {
            setLoading(false);
        }
    }

    async function more() {
        if (!current.parentKey) return;
        setLoading(true);
        setError(null);
        try {
            const json = await fetchChildren(current.parentKey, current.rows.length);
            const rows = json.results?.items ?? [];
            const pagination = json.results?.pagination;
            setTrail((levels) =>
                levels.map((level, index) =>
                    index === levels.length - 1
                        ? {
                              ...level,
                              rows: [...level.rows, ...rows],
                              hasMore: Boolean(pagination?.has_more),
                          }
                        : level,
                ),
            );
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "More could not be loaded.");
        } finally {
            setLoading(false);
        }
    }

    function ascend(depth: number) {
        descended.current = true;
        setTrail((levels) => levels.slice(0, depth + 1));
        setLevelKeys((keys) => keys.slice(0, depth + 1));
        setError(null);
    }

    return (
        <section aria-labelledby="findaid-title" className="va-findaid">
            <div className="va-findaid-top">
                <h2 id="findaid-title">Index of the collection</h2>
                <nav aria-label="Position in the collection" className="va-findaid-trail">
                    {trail.map((level, depth) =>
                        depth === trail.length - 1 ? (
                            <span aria-current="location" key={level.crumb}>
                                {level.crumb}
                            </span>
                        ) : (
                            <button key={level.crumb} onClick={() => ascend(depth)} type="button">
                                {level.crumb}
                            </button>
                        ),
                    )}
                </nav>
            </div>

            <p className="va-findaid-level" ref={headingRef} tabIndex={-1}>
                {/* The level is named in the corpus's own vocabulary, never as "folder" or
                    "section", because the word is part of what the reader is learning. */}
                {plural(current.total ?? current.rows.length, current.label)}
                {current.total && current.rows.length < current.total
                    ? `, ${current.rows.length.toLocaleString("en-GB")} listed`
                    : ""}
            </p>

            {current.rows.length === 0 ? (
                <p className="va-findaid-empty">
                    No divisions are held under this entry. The level exists in the corpus
                    description but carries nothing in this build.
                </p>
            ) : (
                <ul className="va-structure">
                    {current.rows.map((row) => {
                        const value = entryValue(row, currentLevelKey);
                        const leaf = row.passage_type === "MANTRA";
                        const citation =
                            row.canonical_citation ?? row.display_label ?? row.canonical_key;
                        return (
                            <li key={row.canonical_key}>
                                {leaf ? (
                                    <Link
                                        href={`/passage/${encodeURIComponent(row.canonical_key)}`}
                                    >
                                        <span className="va-structure-value">{value}</span>
                                        <span className="va-structure-count">{citation}</span>
                                    </Link>
                                ) : (
                                    <button
                                        disabled={loading}
                                        onClick={() => void descend(row)}
                                        type="button"
                                    >
                                        <span className="va-structure-value">{value}</span>
                                        <span className="va-structure-count">{citation}</span>
                                    </button>
                                )}
                            </li>
                        );
                    })}
                </ul>
            )}

            {error ? (
                <p className="va-findaid-error" role="alert">
                    {error}
                </p>
            ) : null}

            {loading ? <p className="va-findaid-loading">Reading the index…</p> : null}

            {current.hasMore ? (
                <button
                    className="va-findaid-more"
                    disabled={loading}
                    onClick={() => void more()}
                    type="button"
                >
                    Show more {current.label.toLowerCase()}s
                </button>
            ) : null}
        </section>
    );
}
