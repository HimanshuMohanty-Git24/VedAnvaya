"use client";

import { useTheme } from "next-themes";
import type { GraphData } from "@/lib/api";
import { GraphCanvas } from "./graph-canvas";

export function HomeNetwork({ data }: { data: GraphData }) {
    const { resolvedTheme } = useTheme();
    return (
        <div className="graph-frame compact">
            <GraphCanvas
                nodes={data.nodes ?? []}
                edges={data.edges ?? []}
                rootId={data.root?.id}
                dark={resolvedTheme === "dark"}
                compact
            />
            <div className="graph-caption">
                <div>
                    <strong>{data.root?.label ?? "A live neighbourhood"}</strong>
                    <span>
                        {data.bounds?.returned_nodes ?? data.nodes?.length ?? 0} connected entities,
                        read from the graph just now
                    </span>
                </div>
            </div>
        </div>
    );
}
