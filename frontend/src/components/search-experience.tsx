"use client";

import { ArrowRight, MagnifyingGlass, WarningCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { SearchResponse } from "@/lib/api";
import { entityHref, entityTypeLabel, humanizePredicate, statusCopy } from "@/lib/knowledge";
import { NoSearchResults } from "./empty-state";

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
                            {items.length}
                            {data?.pagination?.has_more ? "+" : ""} ranked results
                        </span>
                        <span>
                            Searched{" "}
                            {(data?.surfaces_searched ?? []).map(humanizePredicate).join(", ")}
                        </span>
                        {pending && <span className="refreshing">Refining…</span>}
                    </div>

                    {items.length === 0 ? (
                        <NoSearchResults query={trimmed} />
                    ) : (
                        <ul className="search-results">
                            {items.map((item) => (
                                <li key={`${item.type}-${item.stable_id}`}>
                                    <Link
                                        href={entityHref(item.type, item.stable_id)}
                                        className="result-row"
                                    >
                                        <span className="result-type">
                                            {entityTypeLabel(item.type)}
                                        </span>
                                        <div>
                                            <strong>{item.display_label}</strong>
                                            {(item.subtitle || item.snippet) && (
                                                <p>{item.subtitle ?? item.snippet}</p>
                                            )}
                                            <small>
                                                Matched on {humanizePredicate(item.match_type)}
                                            </small>
                                        </div>
                                        {item.veda && (
                                            <span className="result-veda">{item.veda}</span>
                                        )}
                                        <ArrowRight size={17} aria-hidden="true" />
                                    </Link>
                                </li>
                            ))}
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

function ResultSkeleton() {
    return (
        <div className="search-results" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((row) => (
                <div className="result-skeleton" key={row}>
                    <div className="skeleton" style={{ width: 74, height: 18 }} />
                    <div>
                        <div className="skeleton" style={{ width: "36%", height: 18 }} />
                        <div className="skeleton" style={{ width: "72%", height: 13 }} />
                    </div>
                </div>
            ))}
        </div>
    );
}
