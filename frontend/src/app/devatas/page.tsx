import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type DevatasResponse } from "@/lib/api";
import { humanizePredicate } from "@/lib/knowledge";

export const metadata = {
    title: "Deities",
    description:
        "Resolved deity profiles, with certain, probable and ambiguous mentions kept visibly separate.",
};

export default async function DevatasPage() {
    const result = await load<DevatasResponse>("/devatas?limit=60");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    return (
        <div className="shell page">
            <PageHeading
                title="Deities across the Vedas"
                description="Every figure here was resolved as a deity. The traditional dedication slot also holds human patrons and praise-of-a-gift labels, and those are not shown as gods."
            />

            <Caveat title="What the totals count">
                The figure on each row is certain plus probable mentions. Ambiguous mentions, where
                the referent could not be resolved, are excluded from it and stated separately.
            </Caveat>

            <div className="entity-index">
                {data.items?.map((item) => (
                    <Link
                        href={`/devatas/${encoded(item.id)}`}
                        className="entity-index-row"
                        key={item.id}
                    >
                        <div>
                            <span>{humanizePredicate(item.structure)}</span>
                            <h2>{item.display_label}</h2>
                            <p>{item.short_description}</p>
                        </div>
                        <div className="certainty-mini">
                            <strong>{item.mentions_default_total?.toLocaleString() ?? "—"}</strong>
                            <span>certain and probable</span>
                            {(item.certainty?.ambiguous_count ?? 0) > 0 && (
                                <small>
                                    {item.certainty?.ambiguous_count?.toLocaleString()} ambiguous,
                                    excluded
                                </small>
                            )}
                        </div>
                        <ArrowRight size={18} aria-hidden="true" />
                    </Link>
                ))}
            </div>

            <CaveatList caveats={data.caveats} title="How this list was assembled" limit={6} />
        </div>
    );
}
