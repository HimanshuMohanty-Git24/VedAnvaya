"use client";

import { CaretDown, CaretRight, FileText } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

type PassageRow = {
    canonical_key: string;
    canonical_citation?: string | null;
    display_label?: string | null;
    passage_type: string;
    native_levels?: string[] | null;
};

type Pagination = { returned?: number | null; total?: number | null; has_more?: boolean | null };

type ChildrenResponse = {
    native_label?: string | null;
    level_key?: string | null;
    results?: { items?: PassageRow[]; pagination?: Pagination } | null;
};

const PAGE = 60;

function Branch({ item, depth = 0 }: { item: PassageRow; depth?: number }) {
    const [open, setOpen] = useState(false);
    const [children, setChildren] = useState<PassageRow[] | null>(null);
    const [childLabel, setChildLabel] = useState<string | null>(null);
    const [pagination, setPagination] = useState<Pagination | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const leaf = item.passage_type === "MANTRA";

    async function fetchChildren(offset: number) {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(
                `/backend/passages/${encodeURIComponent(item.canonical_key)}/children?limit=${PAGE}&offset=${offset}`,
            );
            if (!response.ok) throw new Error("This branch could not be opened.");
            const json = (await response.json()) as ChildrenResponse;
            const rows = json.results?.items ?? [];
            setChildLabel(json.native_label ?? null);
            setPagination(json.results?.pagination ?? null);
            setChildren((current) => (offset === 0 ? rows : [...(current ?? []), ...rows]));
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "This branch could not be opened.");
        } finally {
            setLoading(false);
        }
    }

    async function toggle() {
        if (leaf) return;
        const next = !open;
        setOpen(next);
        if (next && !children) await fetchChildren(0);
    }

    const label = item.display_label ?? item.canonical_citation ?? item.canonical_key;
    const level = item.native_levels?.at(-1);

    return (
        <li className="tree-row" style={{ "--depth": depth } as React.CSSProperties}>
            <div>
                {leaf ? (
                    <FileText size={15} aria-hidden="true" />
                ) : (
                    <button
                        type="button"
                        onClick={toggle}
                        aria-expanded={open}
                        aria-label={`${open ? "Collapse" : "Expand"} ${label}`}
                    >
                        {open ? <CaretDown size={15} /> : <CaretRight size={15} />}
                    </button>
                )}
                {leaf ? (
                    <Link href={`/passage/${encodeURIComponent(item.canonical_key)}`}>{label}</Link>
                ) : (
                    <button className="branch-label" type="button" onClick={toggle}>
                        {label}
                    </button>
                )}
                <span>{level ?? item.passage_type.toLowerCase().replaceAll("_", " ")}</span>
            </div>

            {loading && <div className="tree-loading">Loading this branch…</div>}
            {error && <div className="tree-loading">{error}</div>}

            {open && children && (
                <>
                    {childLabel && children.length > 0 && (
                        <div
                            className="tree-level-label"
                            style={{ "--depth": depth + 1 } as React.CSSProperties}
                        >
                            {children.length}
                            {pagination?.total && pagination.total > children.length
                                ? ` of ${pagination.total.toLocaleString()}`
                                : ""}{" "}
                            {childLabel.toLowerCase()}
                            {children.length === 1 ? "" : "s"}
                        </div>
                    )}
                    <ul>
                        {children.map((child) => (
                            <Branch item={child} depth={depth + 1} key={child.canonical_key} />
                        ))}
                    </ul>
                    {pagination?.has_more && (
                        <button
                            className="tree-more"
                            type="button"
                            style={{ "--depth": depth + 1 } as React.CSSProperties}
                            onClick={() => void fetchChildren(children.length)}
                            disabled={loading}
                        >
                            Show{" "}
                            {pagination.total
                                ? Math.min(PAGE, pagination.total - children.length)
                                : PAGE}{" "}
                            more
                        </button>
                    )}
                    {children.length === 0 && (
                        <div className="tree-loading">
                            No child passages are held under this entry.
                        </div>
                    )}
                </>
            )}
        </li>
    );
}

export function StructureBrowser({
    items,
    nativeLabel,
}: {
    items: PassageRow[];
    nativeLabel: string;
}) {
    return (
        <section className="structure-browser" aria-labelledby="structure-title">
            <div className="structure-top">
                <div>
                    <h2 id="structure-title">Browse by {nativeLabel}</h2>
                    <p>
                        Each collection keeps its own hierarchy. Open a branch to follow this one
                        down to a single verse.
                    </p>
                </div>
                <span>
                    {items.length} {nativeLabel.toLowerCase()}
                    {items.length === 1 ? "" : "s"}
                </span>
            </div>
            <ul>
                {items.map((item) => (
                    <Branch item={item} key={item.canonical_key} />
                ))}
            </ul>
        </section>
    );
}
