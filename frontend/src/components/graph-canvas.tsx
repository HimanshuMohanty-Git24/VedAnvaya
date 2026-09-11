"use client";

import { useEffect, useRef, useState } from "react";
import type { Core, ElementDefinition, StylesheetJson } from "cytoscape";
import type { GraphEdge, GraphNode } from "@/lib/api";
import {
    humanizePredicate,
    isPublicGraphNode,
    isRenderedAsDeity,
    normalizeType,
    titleCase,
} from "@/lib/knowledge";

/** Predicate and metric nodes arrive as SCREAMING_SNAKE ids; readers get words. */
function displayLabel(node: { label?: string | null; type?: string | null }) {
    const label = node.label ?? "";
    if (!label) return "";
    if (/^[A-Z0-9]+(_[A-Z0-9]+)+$/.test(label) || /^[A-Z]{3,}$/.test(label)) {
        return titleCase(humanizePredicate(label));
    }
    return label;
}

export type SemanticGroup =
    | "deity"
    | "unresolved-deity"
    | "passage"
    | "person"
    | "idea"
    | "rite"
    | "thing"
    | "wording"
    | "derived"
    | "record"
    | "other";

/** One semantic group per node type. Colour is never the only difference. */
export function semanticGroup(node: {
    type?: string | null;
    is_deity?: boolean | null;
}): SemanticGroup {
    const type = normalizeType(node.type);
    if (type === "DEVATA") return node.is_deity === true ? "deity" : "unresolved-deity";
    if (type === "MANTRA" || type === "PASSAGE" || type === "STRUCTURAL_CONTAINER")
        return "passage";
    if (type === "RISHI" || type === "RISHI_FAMILY" || type === "TRIBE") return "person";
    if (
        type === "RITUAL" ||
        type === "RITUAL_ROLE" ||
        type === "SOCIAL_RITE" ||
        type === "OFFERING"
    )
        return "rite";
    if (type === "FORMULA" || type === "FORMULA_FAMILY" || type === "CHANDAS") return "wording";
    if (type === "DERIVED_METRIC" || type === "INTERPRETIVE_CLAIM") return "derived";
    // Reified records of a claim. Real provenance, never Vedic subject matter, and
    // an ascription descriptor in particular must never be drawn as a deity.
    if (
        type === "DEVATA_ASCRIPTION" ||
        type === "SEMANTIC_ASSERTION" ||
        type === "AGENTIVE_ASSERTION"
    )
        return "record";
    if (
        type === "OBJECT" ||
        type === "WEAPON" ||
        type === "SUBSTANCE" ||
        type === "PLANT" ||
        type === "ANIMAL" ||
        type === "METAL" ||
        type === "CROP" ||
        type === "RIVER" ||
        type === "PLACE"
    )
        return "thing";
    if (
        type === "CONCEPT" ||
        type === "PHILOSOPHICAL_CONCEPT" ||
        type === "ACTION_PREDICATE" ||
        type === "ACTION" ||
        type === "CONDITION" ||
        type === "HUMAN_CONCERN" ||
        type === "QUALITY" ||
        type === "STATE" ||
        type === "DEITY_AXIS" ||
        type === "EPITHET" ||
        type === "NATURAL_PHENOMENON" ||
        type === "COSMIC_ENTITY"
    )
        return "idea";
    return "other";
}

export const GROUP_STYLE: Record<
    SemanticGroup,
    { label: string; shape: string; light: string; dark: string; size: number }
> = {
    deity: { label: "Deity", shape: "ellipse", light: "#bd4f32", dark: "#e07858", size: 40 },
    "unresolved-deity": {
        label: "Unresolved devata slot",
        shape: "ellipse",
        light: "#b59a8f",
        dark: "#9b807a",
        size: 28,
    },
    passage: {
        label: "Passage",
        shape: "round-rectangle",
        light: "#9b8462",
        dark: "#c7ab7e",
        size: 20,
    },
    person: { label: "Seer", shape: "diamond", light: "#607d92", dark: "#86a6bb", size: 26 },
    idea: { label: "Idea", shape: "hexagon", light: "#6c8f83", dark: "#8fb3a6", size: 24 },
    rite: { label: "Rite", shape: "round-diamond", light: "#8a6f9b", dark: "#ab8ec0", size: 26 },
    thing: { label: "Thing", shape: "round-tag", light: "#7d7969", dark: "#a5a08c", size: 22 },
    wording: { label: "Wording", shape: "barrel", light: "#4f7f8f", dark: "#77a9b8", size: 22 },
    derived: {
        label: "Derived metric",
        shape: "rectangle",
        light: "#8d8d8d",
        dark: "#a8a8a8",
        size: 20,
    },
    record: {
        label: "Evidence record",
        shape: "vee",
        light: "#8c9490",
        dark: "#9faaa5",
        size: 18,
    },
    other: { label: "Other", shape: "ellipse", light: "#8c9490", dark: "#9faaa5", size: 20 },
};

function buildStyle(dark: boolean, compact: boolean): StylesheetJson {
    const ink = dark ? "#d5dedb" : "#465155";
    const halo = dark ? "#182023" : "#f4f5f2";
    const line = dark ? "#4a5659" : "#b9c2bd";
    const accent = dark ? "#e07858" : "#bd4f32";
    const groupRules = (Object.keys(GROUP_STYLE) as SemanticGroup[]).map((group) => ({
        selector: `node[group = "${group}"]`,
        style: {
            "background-color": dark ? GROUP_STYLE[group].dark : GROUP_STYLE[group].light,
            shape: GROUP_STYLE[group].shape,
            width: compact ? GROUP_STYLE[group].size * 0.66 : GROUP_STYLE[group].size,
            height: compact ? GROUP_STYLE[group].size * 0.66 : GROUP_STYLE[group].size,
        },
    }));
    return [
        {
            selector: "node",
            style: {
                label: "data(label)",
                color: ink,
                "font-family": "Geist, system-ui, sans-serif",
                "font-size": compact ? "9px" : "11px",
                "text-max-width": compact ? "80px" : "112px",
                "min-zoomed-font-size": 7,
                "text-wrap": "ellipsis",
                "text-valign": "bottom",
                "text-margin-y": 7,
                "text-background-color": halo,
                "text-background-opacity": 0.72,
                "text-background-padding": "2px",
                "border-width": 2,
                "border-color": halo,
            },
        },
        ...groupRules,
        {
            selector: 'node[group = "unresolved-deity"]',
            style: { "border-style": "dashed", "border-color": dark ? "#6c5a55" : "#c9b1a8" },
        },
        {
            selector: 'node[group = "derived"], node[group = "record"]',
            style: { "border-style": "dotted", "border-width": 2, "border-color": ink },
        },
        { selector: "node[root = 'true']", style: { "border-width": 4, "border-color": accent } },
        {
            selector: "edge",
            style: {
                width: 1.1,
                "line-color": line,
                "target-arrow-color": line,
                "target-arrow-shape": "triangle",
                "arrow-scale": 0.7,
                "curve-style": "bezier",
                label: "",
                "font-size": "9px",
                color: ink,
                "text-rotation": "autorotate",
                "text-background-color": halo,
                "text-background-opacity": 0.86,
                "text-background-padding": "2px",
            },
        },
        { selector: "edge.show-label", style: { label: "data(label)" } },
        ...(compact
            ? [
                  {
                      // The home neighbourhood is a calm sketch: only deities carry a name.
                      selector: 'node[group != "deity"]',
                      style: { label: "" },
                  },
              ]
            : []),
        {
            // Small nodes drop their label when zoomed out so the map stays readable.
            selector: 'node.hide-label[group != "deity"][group != "rite"][root != "true"]',
            style: { label: "" },
        },
        {
            selector: "node:selected",
            style: { "border-width": 5, "border-color": accent },
        },
        {
            selector: "edge:selected",
            style: { width: 2.6, "line-color": accent, "target-arrow-color": accent },
        },
        { selector: ".faded", style: { opacity: 0.18 } },
    ] as StylesheetJson;
}

export function GraphCanvas({
    nodes,
    edges,
    rootId,
    compact = false,
    dark = false,
    onNode,
    onEdge,
    onBackground,
    fitSignal = 0,
    layoutSignal = 0,
}: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    rootId?: string | null;
    compact?: boolean;
    dark?: boolean;
    onNode?: (node: GraphNode) => void;
    onEdge?: (edge: GraphEdge) => void;
    onBackground?: () => void;
    fitSignal?: number;
    layoutSignal?: number;
}) {
    const elementRef = useRef<HTMLDivElement>(null);
    const cyRef = useRef<Core | null>(null);
    // Cytoscape is imported lazily, so the element effect below must wait for it.
    const [ready, setReady] = useState(0);
    const handlers = useRef({ onNode, onEdge, onBackground });

    useEffect(() => {
        handlers.current = { onNode, onEdge, onBackground };
    }, [onNode, onEdge, onBackground]);

    useEffect(() => {
        const container = elementRef.current;
        if (!container) return;
        let cancelled = false;
        let dispose: (() => void) | undefined;

        void import("cytoscape").then(({ default: cytoscape }) => {
            if (cancelled || !container) return;
            const cy = cytoscape({
                container,
                elements: [],
                minZoom: 0.22,
                maxZoom: 2.4,
                wheelSensitivity: 0.3,
                style: buildStyle(dark, compact),
            });
            cyRef.current = cy;
            cy.on("tap", "node", (event) =>
                handlers.current.onNode?.(event.target.data("raw") as GraphNode),
            );
            cy.on("tap", "edge", (event) =>
                handlers.current.onEdge?.(event.target.data("raw") as GraphEdge),
            );
            cy.on("tap", (event) => {
                if (event.target === cy) handlers.current.onBackground?.();
            });
            const applyLabelVisibility = () => {
                if (compact) return;
                const zoom = cy.zoom();
                cy.edges().toggleClass("show-label", zoom > 0.85);
                cy.nodes().toggleClass("hide-label", zoom < 0.62);
            };
            cy.on("zoom", applyLabelVisibility);
            applyLabelVisibility();
            dispose = () => {
                cyRef.current = null;
                cy.destroy();
            };
            setReady((value) => value + 1);
        });

        return () => {
            cancelled = true;
            dispose?.();
        };
        // The instance is created once per canvas; data flows through the effect below.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        cyRef.current?.style(buildStyle(dark, compact));
    }, [dark, compact]);

    useEffect(() => {
        const cy = cyRef.current;
        if (!cy) return;
        const visible = nodes.filter(isPublicGraphNode);
        const ids = new Set(visible.map((node) => node.id));
        const visibleEdges = edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
        const wanted: ElementDefinition[] = [
            ...visible.map((node) => ({
                group: "nodes" as const,
                data: {
                    id: node.id,
                    label: displayLabel(node),
                    group: semanticGroup(node),
                    deity: isRenderedAsDeity(node) ? "true" : "false",
                    root: node.id === rootId ? "true" : "false",
                    raw: node,
                },
            })),
            ...visibleEdges.map((edge) => ({
                group: "edges" as const,
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    label: (edge.label ?? edge.type ?? "").toLowerCase().replaceAll("_", " "),
                    raw: edge,
                },
            })),
        ];

        const existing = new Set(cy.elements().map((element) => element.id()));
        const wantedIds = new Set(wanted.map((element) => element.data.id as string));
        cy.batch(() => {
            cy.elements()
                .filter((element) => !wantedIds.has(element.id()))
                .remove();
            const additions = wanted.filter((element) => !existing.has(element.data.id as string));
            if (additions.length) cy.add(additions);
            cy.nodes().forEach((node) => {
                node.data("root", node.id() === rootId ? "true" : "false");
            });
        });

        const layout = cy.layout({
            name: "cose",
            animate:
                typeof window !== "undefined" &&
                !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
            animationDuration: 460,
            randomize: false,
            fit: true,
            padding: compact ? 34 : 56,
            nodeRepulsion: () => (compact ? 5200 : 9200),
            idealEdgeLength: () => (compact ? 70 : 118),
            nodeDimensionsIncludeLabels: true,
        });
        layout.run();
    }, [nodes, edges, rootId, compact, layoutSignal, ready]);

    useEffect(() => {
        if (!fitSignal) return;
        cyRef.current?.animate({ fit: { eles: "", padding: compact ? 34 : 56 }, duration: 320 });
    }, [fitSignal, compact]);

    const deityCount = nodes.filter(isRenderedAsDeity).length;
    return (
        <div
            ref={elementRef}
            className="graph-canvas"
            role="img"
            aria-label={`Knowledge graph showing ${nodes.length} entities, ${deityCount} of them deities, and ${edges.length} relationships. A textual list of the same nodes is in the panel beside this graph.`}
        />
    );
}
