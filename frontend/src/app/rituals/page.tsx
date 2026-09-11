import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type RitualsResponse } from "@/lib/api";

export const metadata = {
    title: "Rituals",
    description:
        "The rites this graph models, explored through passages, roles, objects and stated steps.",
};

export default async function RitualsPage() {
    const result = await load<RitualsResponse>("/rituals?limit=25");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    const coverage = data.items?.[0]?.inventory_coverage;
    return (
        <div className="shell page">
            <PageHeading
                title="Rites the corpus names"
                description="Explored through the passages that describe them, the people who perform them, and what is offered."
            />
            {coverage && (
                <Caveat title="Not a taxonomy of Vedic ritual" tone="boundary">
                    {coverage}
                </Caveat>
            )}
            <div className="ritual-grid">
                {data.items?.map((item) => (
                    <Link href={`/rituals/${encoded(item.id)}`} key={item.id}>
                        <span lang="sa">{item.label_iast}</span>
                        <h2>{item.display_label}</h2>
                        <p>{item.short_description}</p>
                        <div>
                            <small>{item.described_in_count ?? 0} describing passages</small>
                            <small>
                                {item.step_count
                                    ? `${item.step_count} stated steps`
                                    : "no stated order"}
                            </small>
                        </div>
                        <ArrowRight size={18} aria-hidden="true" />
                    </Link>
                ))}
            </div>
            <CaveatList caveats={data.caveats} title="How this list was scoped" />
        </div>
    );
}
