import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import { LoadFailure, NothingHere } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { ParallelComparison } from "@/components/parallel-comparison";
import { Caveat, CaveatList } from "@/components/status";
import {
    routeId,
    encoded,
    load,
    type ParallelsResponse,
    type ParallelView,
    type Reader,
    vedaNames,
} from "@/lib/api";

type Params = { params: Promise<{ key: string }> };

export async function generateMetadata({ params }: Params) {
    const { key: rawKey } = await params;
    const key = routeId(rawKey);
    const decoded = decodeURIComponent(key);
    return { title: `Shared wording around ${decoded.split(":").slice(1).join(" ")}` };
}

export default async function ReusePage({ params }: Params) {
    const { key: rawKey } = await params;
    const key = routeId(rawKey);
    const [readerResult, parallelResult] = await Promise.all([
        load<Reader>(`/passages/${encoded(key)}/reader`),
        load<ParallelsResponse>(`/passages/${encoded(key)}/parallels?filter=cross_veda&limit=20`),
    ]);
    if (!readerResult.ok) {
        if (readerResult.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={readerResult.status} message={readerResult.message} />
            </div>
        );
    }
    const reader = readerResult.data;
    const rows: ParallelView[] = parallelResult.ok
        ? (parallelResult.data.items ?? []).filter((row) => row.is_textual_parallelism)
        : [];

    // One counterpart passage can carry several relationship classes. Read it once.
    const counterpartKeys = [...new Set(rows.map((row) => row.passage.canonical_key))];
    const counterparts = await Promise.all(
        counterpartKeys
            .slice(0, 6)
            .map((counterpartKey) => load<Reader>(`/passages/${encoded(counterpartKey)}/reader`)),
    );
    const counterpartByKey = new Map<string, Reader>();
    counterparts.forEach((result, index) => {
        if (result.ok) counterpartByKey.set(counterpartKeys[index], result.data);
    });

    const involvesSamaveda = reader.veda === "SV" || rows.some((row) => row.passage.veda === "SV");

    return (
        <div className="shell page">
            <PageHeading
                title={`Shared wording with ${reader.canonical_citation}`}
                description="The same verse as it stands in two collections, with the surface that matched and the evidence behind the link."
                backHref={`/passage/${encoded(reader.canonical_key)}`}
                backLabel={`Back to ${reader.canonical_citation}`}
            />

            {involvesSamaveda && (
                <Caveat title="Samaveda scope" tone="boundary">
                    This is the Kauthuma arcika verse corpus. The gana collections and the melodic
                    apparatus are not held, so nothing here shows or implies how a verse was sung.
                </Caveat>
            )}

            {rows.length === 0 ? (
                <NothingHere
                    title="No cross-Veda wording was established here"
                    message="The parallel layer is derived by rule, so this is a statement about what was computed for this passage, not a finding that the wording stands nowhere else."
                    action={{ href: "/connections", label: "Open the cross-Veda explorer" }}
                />
            ) : (
                <div className="comparison-stack">
                    {counterpartKeys.slice(0, 6).map((counterpartKey) => {
                        const relations = rows.filter(
                            (row) => row.passage.canonical_key === counterpartKey,
                        );
                        const counterpart = counterpartByKey.get(counterpartKey);
                        return (
                            <ParallelComparison
                                key={counterpartKey}
                                source={reader}
                                target={counterpart ?? null}
                                targetSummary={relations[0].passage}
                                relations={relations}
                            />
                        );
                    })}
                    {counterpartKeys.length > 6 && (
                        <Link
                            className="text-link"
                            href={`/graph?node=${encoded(reader.canonical_key)}`}
                        >
                            {counterpartKeys.length - 6} further related passages in the graph
                            <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                    )}
                </div>
            )}

            <section className="transmission-note">
                <h2>What a match here does and does not show</h2>
                <p>
                    These links are derived by comparing normalised Sanskrit surfaces. They show
                    that two collections carry the same wording. They are not, by themselves, a
                    demonstrated line of transmission between them, and the direction stored on an
                    edge is a property of how it was built.
                </p>
                <p>
                    {vedaNames[reader.veda] ?? reader.veda} is one of four collections held here.
                    Cross-corpus comparison bottoms out at the weakest shared surface, because a
                    Devanagari text and a romanised text share no code points.
                </p>
            </section>

            {parallelResult.ok && (
                <CaveatList caveats={parallelResult.data.caveats} title="How these were derived" />
            )}
        </div>
    );
}
