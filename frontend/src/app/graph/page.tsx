import type { Metadata } from "next";
import { Suspense } from "react";
import { GraphShell } from "@/components/world/graph-shell";

export const metadata: Metadata = {
    title: "The knowledge world",
    description:
        "The whole public corpus as one connected map: 35,370 subjects and 185,693 recorded relationships, in a spatial world, a planar diagram, or traced as a path between two things.",
};

/**
 * The graph.
 *
 * This route used to open a bounded 2D explorer while the spatial world sat unlinked at
 * `/graph/world`, which meant the flagship view of the corpus was reachable only by typing its
 * address. There is now one graph with four ways of looking at it, and this is where it opens.
 */
export default function GraphPage() {
    return (
        <Suspense fallback={<div className="va-graph" data-mode="WORLD" />}>
            <GraphShell />
        </Suspense>
    );
}
