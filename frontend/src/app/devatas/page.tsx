import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
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
        <div className="va-page">
            <header className="va-page-head">
                <h1>Deities across the Vedas</h1>
                <p>
                    Every figure here was resolved as a deity. The tradition&rsquo;s dedication
                    slot also holds human patrons and labels naming a gift rather than a
                    recipient, and those are not shown as gods.
                </p>
            </header>

            <Caveat title="What the totals count">
                The figure on each row is certain plus probable mentions. Ambiguous mentions, where
                the referent could not be resolved, are excluded from it and stated separately.
            </Caveat>

            <ul className="va-index">
                {data.items?.map((item) => (
                    <li key={item.id}>
                        <Link href={`/devatas/${encoded(item.id)}`}>
                            <span className="va-index-name">
                                <strong>{item.display_label}</strong>
                                <span className="va-index-kind">
                                    {humanizePredicate(item.structure)}
                                </span>
                            </span>
                            <span className="va-index-note">{item.short_description}</span>
                            <span className="va-index-figure">
                                {item.mentions_default_total?.toLocaleString("en-GB") ?? "not read"}
                                <small>
                                    named
                                    {(item.certainty?.ambiguous_count ?? 0) > 0
                                        ? `, ${item.certainty?.ambiguous_count?.toLocaleString("en-GB")} held back`
                                        : ""}
                                </small>
                            </span>
                        </Link>
                    </li>
                ))}
            </ul>

            <CaveatList caveats={data.caveats} title="How this list was assembled" limit={6} />
        </div>
    );
}
