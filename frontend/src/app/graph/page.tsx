import { LoadFailure } from "@/components/empty-state";
import { GraphExplorer } from "@/components/graph-explorer";
import { PageHeading } from "@/components/page-heading";
import { encoded, load, type GraphData } from "@/lib/api";

export const metadata = {
    title: "Knowledge graph",
    description:
        "A curated, bounded map of passages, deities, seers, ideas, rites and wording, where every relationship can be asked to explain itself.",
};

export default async function GraphPage({
    searchParams,
}: {
    searchParams: Promise<{ node?: string }>;
}) {
    const { node = "VG:DEVATA:INDRAH" } = await searchParams;
    const result = await load<GraphData>(
        `/graph/neighborhood/${encoded(node)}?depth=1&limit_per_type=8`,
        { revalidate: 0 },
    );
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    return (
        <div className="shell page graph-page">
            <PageHeading
                title="Knowledge graph"
                description="Curated for reading, not a database browser. Expand one node at a time and select any relationship line to see the exact evidence behind it."
            />
            <GraphExplorer initialData={result.data} initialNode={node} />
        </div>
    );
}
