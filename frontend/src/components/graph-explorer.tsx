"use client";

import {
    ArrowsClockwise,
    ArrowsOut,
    ArrowSquareOut,
    MagnifyingGlass,
    Plus,
    Minus,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useCallback, useMemo, useState } from "react";
import type {
    GraphData,
    GraphEdge,
    GraphNode,
    RelationshipExplanation,
    SearchResponse,
} from "@/lib/api";
import {
    entityHref,
    entityTypeLabel,
    humanizePredicate,
    isPublicGraphNode,
    isRenderedAsDeity,
} from "@/lib/knowledge";
import { EvidenceDrawer } from "./evidence-drawer";
import { GraphCanvas, GROUP_STYLE, semanticGroup, type SemanticGroup } from "./graph-canvas";
import { KnowledgeStatus } from "./status";

const TIERS = [
    { value: "", label: "Every grade" },
    { value: "TIER_A", label: "Textual only" },
    { value: "TIER_B", label: "Textual and derived" },
    { value: "TIER_C", label: "Include reviewed semantics" },
    { value: "TIER_D", label: "Include interpretive" },
];

const GROUP_ORDER: SemanticGroup[] = [
    "deity",
    "passage",
    "person",
    "idea",
    "rite",
    "thing",
    "wording",
    "unresolved-deity",
    "derived",
    "record",
    "other",
];

type Store = { nodes: Map<string, GraphNode>; edges: Map<string, GraphEdge> };

function ingest(store: Store, data: GraphData): Store {
    const nodes = new Map(store.nodes);
    const edges = new Map(store.edges);
    for (const node of data.nodes ?? []) {
        if (isPublicGraphNode(node)) nodes.set(node.id, node);
    }
    for (const edge of data.edges ?? []) {
        if (nodes.has(edge.source) && nodes.has(edge.target)) edges.set(edge.id, edge);
    }
    return { nodes, edges };
}

export function GraphExplorer({
    initialData,
    initialNode,
}: {
    initialData: GraphData;
    initialNode: string;
}) {
    const router = useRouter();
    const { resolvedTheme } = useTheme();
    const [store, setStore] = useState<Store>(() =>
        ingest({ nodes: new Map(), edges: new Map() }, initialData),
    );
    const [rootId, setRootId] = useState(initialData.root?.id ?? initialNode);
    const [bounds, setBounds] = useState(initialData.bounds ?? null);
    const [selected, setSelected] = useState<GraphNode | null>(initialData.root ?? null);
    const [expanded, setExpanded] = useState<Set<string>>(() => new Set([initialNode]));
    const [query, setQuery] = useState(initialData.root?.label ?? "");
    const [depth, setDepth] = useState(1);
    const [tier, setTier] = useState("");
    const [perType, setPerType] = useState(8);
    const [hidden, setHidden] = useState<Set<SemanticGroup>>(() => new Set());
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [fitSignal, setFitSignal] = useState(0);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [evidence, setEvidence] = useState<RelationshipExplanation | null>(null);
    const [evidenceEdge, setEvidenceEdge] = useState<GraphEdge | null>(null);
    const [evidenceLoading, setEvidenceLoading] = useState(false);

    const fetchNeighbourhood = useCallback(
        async (nodeId: string, limit = perType) => {
            const params = new URLSearchParams({
                depth: String(depth),
                limit_per_type: String(limit),
            });
            if (tier) params.set("trust_tier", tier);
            const response = await fetch(
                `/backend/graph/neighborhood/${encodeURIComponent(nodeId)}?${params}`,
            );
            if (!response.ok) throw new Error("This neighbourhood could not be loaded.");
            return (await response.json()) as GraphData;
        },
        [depth, perType, tier],
    );

    const openRoot = useCallback(
        async (nodeId: string) => {
            setBusy(true);
            setMessage(null);
            try {
                const data = await fetchNeighbourhood(nodeId);
                setStore(ingest({ nodes: new Map(), edges: new Map() }, data));
                setRootId(data.root?.id ?? nodeId);
                setBounds(data.bounds ?? null);
                setSelected(data.root ?? null);
                setExpanded(new Set([nodeId]));
                setQuery(data.root?.label ?? nodeId);
                router.replace(`/graph?node=${encodeURIComponent(nodeId)}`, { scroll: false });
            } catch (reason) {
                setMessage(
                    reason instanceof Error ? reason.message : "This neighbourhood did not load.",
                );
            } finally {
                setBusy(false);
            }
        },
        [fetchNeighbourhood, router],
    );

    const expandNode = useCallback(
        async (nodeId: string) => {
            setBusy(true);
            setMessage(null);
            try {
                const data = await fetchNeighbourhood(nodeId);
                setStore((current) => ingest(current, data));
                setExpanded((current) => new Set(current).add(nodeId));
            } catch (reason) {
                setMessage(
                    reason instanceof Error ? reason.message : "That expansion did not load.",
                );
            } finally {
                setBusy(false);
            }
        },
        [fetchNeighbourhood],
    );

    /** Drop everything reachable only through this node, keeping the root intact. */
    const collapseNode = useCallback(
        (nodeId: string) => {
            setStore((current) => {
                const keep = new Set<string>([rootId]);
                const touching = [...current.edges.values()].filter(
                    (edge) => edge.source === nodeId || edge.target === nodeId,
                );
                const candidates = new Set(
                    touching.map((edge) => (edge.source === nodeId ? edge.target : edge.source)),
                );
                candidates.delete(rootId);
                for (const candidate of candidates) {
                    const degree = [...current.edges.values()].filter(
                        (edge) =>
                            (edge.source === candidate || edge.target === candidate) &&
                            edge.source !== nodeId &&
                            edge.target !== nodeId,
                    ).length;
                    if (degree > 0) keep.add(candidate);
                }
                const nodes = new Map(current.nodes);
                for (const candidate of candidates) {
                    if (!keep.has(candidate)) nodes.delete(candidate);
                }
                const edges = new Map(
                    [...current.edges.entries()].filter(
                        ([, edge]) => nodes.has(edge.source) && nodes.has(edge.target),
                    ),
                );
                return { nodes, edges };
            });
            setExpanded((current) => {
                const next = new Set(current);
                next.delete(nodeId);
                return next;
            });
        },
        [rootId],
    );

    const explain = useCallback(async (edge: GraphEdge) => {
        setEvidenceEdge(edge);
        setDrawerOpen(true);
        setEvidenceLoading(true);
        setEvidence(null);
        try {
            const response = await fetch(
                `/backend/graph/relationships/${encodeURIComponent(edge.id)}`,
            );
            if (!response.ok) throw new Error();
            setEvidence((await response.json()) as RelationshipExplanation);
        } catch {
            setEvidence(null);
        } finally {
            setEvidenceLoading(false);
        }
    }, []);

    const findStart = useCallback(
        async (event: React.FormEvent) => {
            event.preventDefault();
            const text = query.trim();
            if (!text) return;
            if (text.startsWith("VG:")) {
                await openRoot(text);
                return;
            }
            setBusy(true);
            setMessage(null);
            try {
                const response = await fetch(
                    `/backend/search?q=${encodeURIComponent(text)}&limit=1`,
                );
                const search = (await response.json()) as SearchResponse;
                const hit = search.items?.[0];
                if (!hit) throw new Error("Nothing in the corpus matched that start point.");
                await openRoot(hit.stable_id);
            } catch (reason) {
                setMessage(
                    reason instanceof Error
                        ? reason.message
                        : "Nothing in the corpus matched that start point.",
                );
                setBusy(false);
            }
        },
        [openRoot, query],
    );

    const allNodes = useMemo(() => [...store.nodes.values()], [store]);
    const allEdges = useMemo(() => [...store.edges.values()], [store]);

    const groupCounts = useMemo(() => {
        const counts = new Map<SemanticGroup, number>();
        for (const node of allNodes) {
            const group = semanticGroup(node);
            counts.set(group, (counts.get(group) ?? 0) + 1);
        }
        return counts;
    }, [allNodes]);

    const visibleNodes = useMemo(
        () => allNodes.filter((node) => !hidden.has(semanticGroup(node))),
        [allNodes, hidden],
    );
    const visibleIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
    const visibleEdges = useMemo(
        () => allEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
        [allEdges, visibleIds],
    );

    const toggleGroup = (group: SemanticGroup) =>
        setHidden((current) => {
            const next = new Set(current);
            if (next.has(group)) next.delete(group);
            else next.add(group);
            return next;
        });

    const selectedIsExpanded = selected ? expanded.has(selected.id) : false;
    const truncated = bounds?.truncated_types ?? [];

    const selectedEdges = useMemo(() => {
        if (!selected) return [];
        return visibleEdges.filter(
            (edge) => edge.source === selected.id || edge.target === selected.id,
        );
    }, [selected, visibleEdges]);

    const nodeLabel = useCallback((id: string) => store.nodes.get(id)?.label ?? id, [store]);

    return (
        <div className="graph-explorer">
            <div className="graph-toolbar">
                <form onSubmit={findStart} role="search">
                    <MagnifyingGlass size={18} aria-hidden="true" />
                    <label className="sr-only" htmlFor="graph-start">
                        Start the graph from an entity or citation
                    </label>
                    <input
                        id="graph-start"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Start from Indra, Agnihotra, or RV 1.1.1"
                    />
                    <button type="submit">Open</button>
                </form>
                <div className="graph-options">
                    <label>
                        <span>Depth</span>
                        <select
                            value={depth}
                            onChange={(event) => setDepth(Number(event.target.value))}
                        >
                            <option value={1}>Immediate</option>
                            <option value={2}>Two steps</option>
                        </select>
                    </label>
                    <label>
                        <span>Evidence grade</span>
                        <select value={tier} onChange={(event) => setTier(event.target.value)}>
                            {TIERS.map((item) => (
                                <option key={item.value || "all"} value={item.value}>
                                    {item.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        <span>Per relationship</span>
                        <select
                            value={perType}
                            onChange={(event) => setPerType(Number(event.target.value))}
                        >
                            <option value={5}>5</option>
                            <option value={8}>8</option>
                            <option value={14}>14</option>
                        </select>
                    </label>
                    <button
                        className="icon-button"
                        type="button"
                        onClick={() => setFitSignal((value) => value + 1)}
                        aria-label="Fit the graph to the view"
                        title="Fit to view"
                    >
                        <ArrowsOut size={17} aria-hidden="true" />
                    </button>
                    <button
                        className="icon-button"
                        type="button"
                        onClick={() => void openRoot(rootId)}
                        aria-label="Reset to the starting neighbourhood"
                        title="Reset"
                    >
                        <ArrowsClockwise size={17} aria-hidden="true" />
                    </button>
                </div>
            </div>

            <div className="graph-legend" role="group" aria-label="Show or hide entity kinds">
                {GROUP_ORDER.filter((group) => groupCounts.get(group)).map((group) => (
                    <button
                        key={group}
                        type="button"
                        className={`legend-chip group-${group}`}
                        aria-pressed={!hidden.has(group)}
                        onClick={() => toggleGroup(group)}
                    >
                        <i aria-hidden="true" data-shape={GROUP_STYLE[group].shape} />
                        {GROUP_STYLE[group].label}
                        <span>{groupCounts.get(group)}</span>
                    </button>
                ))}
            </div>

            {message && (
                <div className="graph-message" role="alert">
                    {message}
                </div>
            )}

            <div className="graph-workspace">
                <div className="graph-stage">
                    <GraphCanvas
                        nodes={visibleNodes}
                        edges={visibleEdges}
                        rootId={rootId}
                        dark={resolvedTheme === "dark"}
                        onNode={setSelected}
                        onEdge={explain}
                        onBackground={() => setSelected(null)}
                        fitSignal={fitSignal}
                    />
                    {busy && (
                        <div className="graph-busy" role="status">
                            <span className="graph-spinner" aria-hidden="true" />
                            Loading a bounded neighbourhood
                        </div>
                    )}
                    <div className="graph-bounds">
                        <span>
                            {visibleNodes.length} shown of {allNodes.length} loaded &middot;{" "}
                            {visibleEdges.length} relationships
                        </span>
                        {bounds?.total_degree != null && (
                            <span>
                                This start point has {bounds.total_degree.toLocaleString()}{" "}
                                relationships in total. Only a bounded sample is drawn.
                            </span>
                        )}
                    </div>
                </div>

                <aside className="graph-detail" aria-label="Selected item">
                    {selected ? (
                        <>
                            <span className={`node-type group-${semanticGroup(selected)}`}>
                                {isRenderedAsDeity(selected)
                                    ? "deity"
                                    : entityTypeLabel(selected.type)}
                            </span>
                            <h2>{selected.label}</h2>
                            {selected.description ? (
                                <p>{selected.description}</p>
                            ) : (
                                <p className="muted">
                                    No description is held for this node. Select a relationship line
                                    to see why it exists.
                                </p>
                            )}

                            {selected.type === "DEVATA" && selected.is_deity !== true && (
                                <KnowledgeStatus
                                    status="INSUFFICIENT_EVIDENCE"
                                    note="This sits in the traditional devata slot but was not resolved as a deity. It is drawn differently and is excluded from deity analytics."
                                />
                            )}

                            <div className="graph-detail-actions">
                                {selectedIsExpanded ? (
                                    <button
                                        className="button secondary"
                                        type="button"
                                        onClick={() => collapseNode(selected.id)}
                                        disabled={selected.id === rootId}
                                    >
                                        <Minus size={15} aria-hidden="true" />
                                        Collapse
                                    </button>
                                ) : (
                                    <button
                                        className="button primary"
                                        type="button"
                                        onClick={() => void expandNode(selected.id)}
                                    >
                                        <Plus size={15} aria-hidden="true" />
                                        Expand neighbours
                                    </button>
                                )}
                                <button
                                    className="button secondary"
                                    type="button"
                                    onClick={() => void openRoot(selected.id)}
                                >
                                    Recentre here
                                </button>
                                <Link
                                    className="button secondary"
                                    href={entityHref(selected.type, selected.id)}
                                >
                                    <ArrowSquareOut size={15} aria-hidden="true" />
                                    Open full profile
                                </Link>
                            </div>

                            {selectedEdges.length > 0 && (
                                <div className="selected-relationships">
                                    <h3>Its relationships</h3>
                                    <p>
                                        Open any one to see why the two are connected. These are the
                                        same lines drawn on the map.
                                    </p>
                                    <ul>
                                        {selectedEdges.slice(0, 40).map((edge) => (
                                            <li key={edge.id}>
                                                <button
                                                    type="button"
                                                    onClick={() => void explain(edge)}
                                                >
                                                    <span>
                                                        {(
                                                            edge.label ??
                                                            humanizePredicate(edge.type)
                                                        )
                                                            .toString()
                                                            .toLowerCase()}
                                                    </span>
                                                    <strong>
                                                        {edge.source === selected.id
                                                            ? nodeLabel(edge.target)
                                                            : nodeLabel(edge.source)}
                                                    </strong>
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                    {selectedEdges.length > 40 && (
                                        <p>
                                            {selectedEdges.length - 40} further relationships are
                                            drawn on the map.
                                        </p>
                                    )}
                                </div>
                            )}

                            {selected.id === rootId && truncated.length > 0 && (
                                <div className="truncated-types">
                                    <h3>Held back to keep this readable</h3>
                                    <p>
                                        These relationship kinds have more neighbours than are
                                        drawn. Raise the per-relationship limit to see more.
                                    </p>
                                    <ul>
                                        {truncated.map((type) => (
                                            <li key={type}>{humanizePredicate(type)}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="graph-detail-empty">
                            <h2>Nothing selected</h2>
                            <p>
                                Choose a node for its summary and its expansion controls, or select
                                a relationship line to ask why the two are connected.
                            </p>
                        </div>
                    )}

                    <details className="graph-node-list">
                        <summary>All {visibleNodes.length} nodes as a list</summary>
                        <ul>
                            {visibleNodes.map((node) => (
                                <li key={node.id}>
                                    <button type="button" onClick={() => setSelected(node)}>
                                        <span>{entityTypeLabel(node.type)}</span>
                                        {node.label}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </details>
                </aside>
            </div>

            <EvidenceDrawer
                open={drawerOpen}
                onOpenChange={setDrawerOpen}
                loading={evidenceLoading}
                data={evidence}
                edge={evidenceEdge}
            />
        </div>
    );
}
