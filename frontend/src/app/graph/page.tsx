import type { Metadata } from "next";
import { Suspense } from "react";
import { GraphShell } from "@/components/world/graph-shell";
import { pageMetadata } from "@/lib/site";

export const metadata: Metadata = pageMetadata({
    title: "Knowledge World",
    description:
        "Explore the public corpus as one connected map: a spatial world, a planar diagram, or a traced path between two subjects.",
    pathname: "/graph",
});

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
