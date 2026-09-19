"use client";

import { MagnifyingGlass, WarningCircle } from "@phosphor-icons/react";
import clsx from "clsx";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { SearchResponse } from "@/lib/api";
import { entityHref, entityTypeLabel, humanizePredicate, statusCopy } from "@/lib/knowledge";
import { NoSearchResults } from "./empty-state";

/**
 * Search, as an archive catalogue.
 *
 * Every distinction the previous carded version drew is still drawn - the record type, the
 * gloss, how the row matched, and which collection it sits in. What changed is the dialect:
 * ruled entries with ranged metadata instead of bordered cards in a grid. See the note at
 * the head of the finding-aid block in `src/styles/register.css`.
 */

/** Full names, because "RV" in a right margin is a code and "Rigveda" is a collection. */
const VEDA_NAMES: Record<string, string> = {
    RV: "Rigveda",
    SV: "Samaveda",
    YV: "Yajurveda",
    AV: "Atharvaveda",
};

/**
 * Which face this record's name is set in.
 *
 * Three kinds arrive in one list and setting them all in the display face is wrong for two
 * of them. A passage row's label is a canonical citation, which wants tabular figures so a
 * column of them aligns. A seer or a formula row's label is romanised Sanskrit carrying
 * combining accents, and the display face has no mark-attachment table at all: set in it,
 * `indraḥ` loses its dot-below to the glyph origin. Only an English name takes Fraunces.
 */
function nameClass(item: { type: string; display_label: string }) {
    if (item.type === "PASSAGE" || item.type === "STRUCTURAL_CONTAINER") return "is-citation";
    /* A label carrying a Latin diacritic or a Devanagari letter. Plain ASCII falls
       through to the display face, which is where an English name belongs. */
    if (/[\u0100-\u017f\u1e00-\u1eff\u0900-\u097f]/.test(item.display_label)) {
        return "is-sanskrit";
    }
    return undefined;
}

/**
 * A passage's subtitle is `AV / MANTRA`: the corpus code and the structural level.
 *
 * Printed as it stands it said three things the row already said - the collection is named
 * in the right margin, the type is named above the citation - and it said them in machine
 * case. What is genuinely new in it is the *level*, so that is what is kept, and it replaces
 * the generic "passage" rather than sitting beside it. A verse and the hymn containing it
 * are both passages and a reader scanning a column wants to know which.
 */
const STRUCTURED_SUBTITLE = /^([A-Z]{2})\s*\/\s*([A-Z_]+)$/;

function recordKind(item: { type: string; subtitle?: string | null }) {
    const structured = item.subtitle ? STRUCTURED_SUBTITLE.exec(item.subtitle) : null;
    if (structured) return humanizePredicate(structured[2]);
    return entityTypeLabel(item.type);
}

/**
 * The line under the name: what this record is, in words a reader can use.
 *
 * The snippet is preferred over the subtitle for a passage, which is the opposite of what
 * this did before. `subtitle ?? snippet` meant every verse in the catalogue described itself
 * as "AV / MANTRA" while the Sanskrit the query actually matched - which is the single most
 * useful thing a search over a corpus can show - was fetched, carried across the wire and
 * thrown away. An entity keeps its prose gloss, because that is a real description and its
 * snippet is null.
 */
function describeRecord(item: {
    type: string;
    subtitle?: string | null;
    snippet?: string | null;
}): { text: string; sanskrit: boolean } | null {
    const gloss = item.subtitle && !STRUCTURED_SUBTITLE.test(item.subtitle) ? item.subtitle : null;
    if (gloss) return { text: gloss, sanskrit: false };
    if (item.snippet) {
        return {
            text: item.snippet,
            /* A passage's snippet is the verse. Anything else's is English around a match. */
            sanskrit: item.type === "PASSAGE" || item.type === "STRUCTURAL_CONTAINER",
        };
    }
    return null;
}

const TYPE_FILTERS = [
    { value: "", label: "Everything" },
    { value: "PASSAGE", label: "Passages" },
    { value: "DEVATA", label: "Deities" },
    { value: "RISHI", label: "Seers" },
    { value: "CONCEPT", label: "Concepts" },
    { value: "RITUAL", label: "Rituals" },
    { value: "CONDITION", label: "Conditions" },
    { value: "FORMULA_FAMILY", label: "Formulas" },
];

const VEDA_FILTERS = [
    { value: "", label: "All four" },
    { value: "RV", label: "Rigveda" },
    { value: "SV", label: "Samaveda" },
    { value: "YV", label: "Yajurveda" },
    { value: "AV", label: "Atharvaveda" },
];

const LANGUAGE_FILTERS = [
    { value: "any", label: "Any language" },
    { value: "sa", label: "Sanskrit" },
    { value: "en", label: "English" },
];

const SUGGESTIONS = [
    { query: "Indra", note: "the most invoked deity" },
    { query: "Soma", note: "deity and substance, kept apart" },
    { query: "RV 1.1.1", note: "a citation" },
    { query: "takman", note: "fever in the Atharvaveda" },
    { query: "ṛta", note: "IAST with diacritics" },
];

type Params = { q: string; type: string; veda: string; language: string };

function toQueryString({ q, type, veda, language }: Params, limit = 30) {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (type) params.set("type", type);
    if (veda) params.set("veda", veda);
    if (language && language !== "any") params.set("language", language);
    return params.toString();
}

export function SearchExperience({
    initialQuery = "",
    initialType = "",
    initialVeda = "",
}: {
    initialQuery?: string;
    initialType?: string;
    initialVeda?: string;
}) {
    const router = useRouter();
    const pathname = usePathname();
    const [query, setQuery] = useState(initialQuery);
    const [type, setType] = useState(initialType);
    const [veda, setVeda] = useState(initialVeda);
    const [language, setLanguage] = useState("any");
    const [data, setData] = useState<SearchResponse | null>(null);
    const [pending, setPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const cache = useRef(new Map<string, SearchResponse>());

    const trimmed = query.trim();
    const requestKey = trimmed ? toQueryString({ q: trimmed, type, veda, language }) : "";

    useEffect(() => {
        const onKey = (event: KeyboardEvent) => {
            const tag = document.activeElement?.tagName;
            if (event.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") {
                event.preventDefault();
                inputRef.current?.focus();
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, []);

    useEffect(() => {
        if (!requestKey) return;
        const cached = cache.current.get(requestKey);
        const controller = new AbortController();
        const delay = cached ? 0 : 260;
        const timer = window.setTimeout(async () => {
            if (cached) {
                setData(cached);
                setError(null);
                return;
            }
            // Previous results stay on screen while a refined query resolves.
            setPending(true);
            setError(null);
            try {
                const response = await fetch(`/backend/search?${requestKey}`, {
                    signal: controller.signal,
                });
                if (!response.ok) throw new Error("The search service refused this query.");
                const payload = (await response.json()) as SearchResponse;
                cache.current.set(requestKey, payload);
                setData(payload);
            } catch (reason) {
                if (controller.signal.aborted) return;
                setError(
                    reason instanceof Error
                        ? reason.message
                        : "The search service could not be reached.",
                );
            } finally {
                if (!controller.signal.aborted) setPending(false);
            }
        }, delay);
        return () => {
            window.clearTimeout(timer);
            controller.abort();
        };
    }, [requestKey]);

    useEffect(() => {
        if (pathname !== "/search") return;
        const params = new URLSearchParams();
        if (trimmed) params.set("q", trimmed);
        if (type) params.set("type", type);
        if (veda) params.set("veda", veda);
        const next = params.toString();
        const timer = window.setTimeout(() => {
            router.replace(next ? `/search?${next}` : "/search", { scroll: false });
        }, 400);
        return () => window.clearTimeout(timer);
    }, [trimmed, type, veda, pathname, router]);

    const items = useMemo(() => data?.items ?? [], [data]);
    const showing = Boolean(trimmed) && data !== null;

    return (
        <div className="search-experience">
            <label htmlFor="global-search">
                Search Sanskrit, IAST, English, canonical citations and every registered entity
            </label>
            <div className="search-field">
                <MagnifyingGlass size={22} aria-hidden="true" />
                <input
                    ref={inputRef}
                    id="global-search"
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Try Indra, Soma, takman, ṛta, or RV 1.1.1"
                    autoComplete="off"
                    spellCheck={false}
                    aria-describedby="search-status"
                />
                <kbd aria-hidden="true">/</kbd>
            </div>

            <div className="filter-bank">
                <fieldset>
                    <legend>Result type</legend>
                    <div className="filter-row">
                        {TYPE_FILTERS.map((item) => (
                            <button
                                type="button"
                                key={item.value || "all"}
                                aria-pressed={type === item.value}
                                onClick={() => setType(item.value)}
                            >
                                {item.label}
                            </button>
                        ))}
                    </div>
                </fieldset>
                <div className="filter-selects">
                    <label>
                        <span>Collection</span>
                        <select value={veda} onChange={(event) => setVeda(event.target.value)}>
                            {VEDA_FILTERS.map((item) => (
                                <option key={item.value || "all"} value={item.value}>
                                    {item.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        <span>Language</span>
                        <select
                            value={language}
                            onChange={(event) => setLanguage(event.target.value)}
                        >
                            {LANGUAGE_FILTERS.map((item) => (
                                <option key={item.value} value={item.value}>
                                    {item.label}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
            </div>

            <p className="sr-only" id="search-status" role="status">
                {pending
                    ? "Searching"
                    : showing
                      ? `${items.length} results for ${trimmed}`
                      : "Enter a query"}
            </p>

            {error && (
                <div className="search-error" role="alert">
                    <WarningCircle size={18} aria-hidden="true" />
                    <div>
                        <strong>{error}</strong>
                        <span>
                            This is a connection problem, not a statement about the corpus. Try
                            again.
                        </span>
                    </div>
                </div>
            )}

            {!trimmed && (
                <div className="search-prompts">
                    {SUGGESTIONS.map((item) => (
                        <button type="button" key={item.query} onClick={() => setQuery(item.query)}>
                            <strong>{item.query}</strong>
                            <span>{item.note}</span>
                        </button>
                    ))}
                </div>
            )}

            {trimmed && !data && !error && <ResultSkeleton />}

            {showing && (
                <div className={pending ? "search-results-wrap is-stale" : "search-results-wrap"}>
                    <div className="results-meta">
                        <span>
                            <strong>{items.length}</strong>
                            {data?.pagination?.has_more ? "+" : ""} ranked records
                        </span>
                        <span>
                            Read {(data?.surfaces_searched ?? []).map(humanizePredicate).join(", ")}
                        </span>
                        {pending && <span className="refreshing">Refining…</span>}
                    </div>

                    {items.length === 0 ? (
                        <NoSearchResults query={trimmed} />
                    ) : (
                        <ul className="search-results">
                            {items.map((item) => {
                                const described = describeRecord(item);
                                return (
                                    <li key={`${item.type}-${item.stable_id}`}>
                                        <Link
                                            href={entityHref(item.type, item.stable_id)}
                                            className="result-row"
                                        >
                                            <span className="result-record">
                                                <span className="result-type">
                                                    {recordKind(item)}
                                                </span>
                                                <strong className={clsx(nameClass(item))}>
                                                    {item.display_label}
                                                </strong>
                                            </span>
                                            <span className="result-body">
                                                {described && (
                                                    <p
                                                        className={clsx(
                                                            described.sanskrit && "is-sanskrit",
                                                        )}
                                                        lang={described.sanskrit ? "sa" : undefined}
                                                    >
                                                        {described.text}
                                                    </p>
                                                )}
                                                {/*
                                                 * Why this row is here. Printed on every result,
                                                 * without exception: a ranked list that will not
                                                 * say what it matched on is a list a reader has to
                                                 * take on trust, and this product does not ask for
                                                 * that anywhere else.
                                                 */}
                                                <small>
                                                    Matched on{" "}
                                                    <em>{humanizePredicate(item.match_type)}</em>
                                                </small>
                                            </span>
                                            {item.veda && (
                                                <span className="result-veda">
                                                    {VEDA_NAMES[item.veda] ?? item.veda}
                                                </span>
                                            )}
                                        </Link>
                                    </li>
                                );
                            })}
                        </ul>
                    )}

                    {data && data.data_status !== "SUPPORTED" && (
                        <details className="search-caveats">
                            <summary>
                                {statusCopy(data.data_status).label}. What this search does and does
                                not reach
                            </summary>
                            {data.caveats?.map((caveat) => (
                                <p key={caveat.text}>{caveat.text}</p>
                            ))}
                        </details>
                    )}
                </div>
            )}
        </div>
    );
}

/**
 * Five ruled entries with nothing in them yet.
 *
 * Shaped like the catalogue rather than like a generic loading card, so the page does not
 * change layout when the records arrive. The first column is the record slot and carries two
 * bars for the type and the name; the second is the description.
 */
function ResultSkeleton() {
    return (
        <div className="search-results" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((row) => (
                <div className="result-skeleton" key={row}>
                    <div>
                        <div className="skeleton" style={{ width: 72, height: 11 }} />
                        <div className="skeleton" style={{ width: "62%", height: 22 }} />
                    </div>
                    <div>
                        <div className="skeleton" style={{ width: "88%", height: 15 }} />
                        <div className="skeleton" style={{ width: "44%", height: 12 }} />
                    </div>
                </div>
            ))}
        </div>
    );
}
