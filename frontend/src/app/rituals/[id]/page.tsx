import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { routeId, encoded, load, type RitualProfile } from "@/lib/api";
import { entityHref } from "@/lib/knowledge";

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { id: rawId } = await params;
    const id = routeId(rawId);
    const result = await load<RitualProfile>(`/rituals/${encoded(id)}`);
    if (!result.ok) return { title: "Ritual" };
    return {
        title: result.data.display_label ?? "Ritual",
        description: result.data.short_description ?? undefined,
    };
}

export default async function RitualPage({ params }: Params) {
    const { id: rawId } = await params;
    const id = routeId(rawId);
    const result = await load<RitualProfile>(`/rituals/${encoded(id)}`);
    if (!result.ok) {
        if (result.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const ritual = result.data;

    const apparatus = [
        { dimension: "roles", title: "Performed by", items: ritual.roles },
        { dimension: "offerings", title: "Offerings made", items: ritual.offerings },
        { dimension: "substances", title: "Substances used", items: ritual.substances },
        { dimension: "objects", title: "Objects used", items: ritual.objects },
        { dimension: "devatas", title: "Deities invoked", items: ritual.devatas },
        { dimension: "purposes", title: "Undertaken for", items: ritual.purposes },
    ];

    const stepStatus = ritual.dimension_status?.find((item) => item.dimension === "steps");

    return (
        <div className="shell page">
            <PageHeading
                title={ritual.display_label ?? "Ritual"}
                description={ritual.short_description}
                backHref="/rituals"
                backLabel="All modelled rites"
            />
            <KnowledgeStatus status={ritual.data_status} />

            <section className="ritual-shape">
                <h2>The shape of the rite</h2>
                <p className="panel-note">
                    Each row is one relationship class the graph stores for this rite. An empty row
                    states which layer is missing.
                </p>
                <div className="ritual-map">
                    {apparatus.map((group) => (
                        <div className="ritual-row" key={group.title}>
                            <h3>{group.title}</h3>
                            {group.items?.length ? (
                                <div className="chip-row">
                                    {group.items.map((item) => (
                                        <Link href={entityHref(item.type, item.id)} key={item.id}>
                                            {item.display_label}
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <KnowledgeStatus
                                    status={
                                        ritual.dimension_status?.find(
                                            (item) => item.dimension === group.dimension,
                                        )?.status ?? "INSUFFICIENT_EVIDENCE"
                                    }
                                    compact
                                />
                            )}
                        </div>
                    ))}
                </div>
            </section>

            <section className="ritual-steps-section">
                <h2>Stated order</h2>
                {ritual.steps?.length ? (
                    <ol className="ritual-steps">
                        {ritual.steps.map((step) => (
                            <li key={step.order}>
                                <span>{step.order}</span>
                                <div>
                                    <h3>{step.display_label}</h3>
                                    {step.description && <p>{step.description}</p>}
                                </div>
                            </li>
                        ))}
                    </ol>
                ) : (
                    <KnowledgeStatus
                        status={stepStatus?.status ?? "NOT_BUILT"}
                        note={stepStatus?.note}
                    />
                )}
            </section>

            {ritual.broader_than?.length ? (
                <section className="ritual-children">
                    <h2>Rites this one contains</h2>
                    <div className="chip-row">
                        {ritual.broader_than.map((item) => (
                            <Link href={entityHref("RITUAL", item.id)} key={item.id}>
                                {item.display_label}
                            </Link>
                        ))}
                    </div>
                </section>
            ) : null}

            <section className="passage-rail">
                <h2>Described in</h2>
                <p className="panel-note">
                    {ritual.passage_count?.toLocaleString() ?? 0} passages carry a describes edge
                    for this rite, against {ritual.mention_count?.toLocaleString() ?? 0} that name
                    it. Naming is weaker than describing.
                </p>
                <div className="citation-rail">
                    {ritual.passages?.map((item) => (
                        <Link href={entityHref("PASSAGE", item.id)} key={item.id}>
                            <span>{item.subtitle}</span>
                            <strong>{item.display_label}</strong>
                            <ArrowRight size={15} aria-hidden="true" />
                        </Link>
                    ))}
                </div>
            </section>

            <Caveat title="What this ritual model covers" tone="boundary">
                {ritual.coverage_statement}
            </Caveat>
            <CaveatList caveats={ritual.caveats} title="How this rite was modelled" />
        </div>
    );
}
