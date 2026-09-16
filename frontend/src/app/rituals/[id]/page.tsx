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
    const procedureStatus = ritual.dimension_status?.find(
        (item) => item.dimension === "procedure",
    );
    const procedure = ritual.procedure ?? [];
    const procedureShown = procedure.reduce((total, source) => total + (source.steps?.length ?? 0), 0);

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
                <p className="ritual-layer-note">
                    What the Samhita text numbers in its own words. Three such steps exist in
                    the whole corpus, all on the soma pressing.
                </p>
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

            {/*
              The sutra layer, kept visibly apart from the Samhita numbering above. Grouping
              by source work is the claim, not a layout choice: each work numbers its own
              sequence from 1, and 2,666 of the 3,121 steps share a position with another
              step of the same rite, so one merged list would invent a procedure nobody
              recorded. Until this section existed, 102 of 103 rites showed "not built" for
              order while the graph held their full procedural evidence.
            */}
            <section className="ritual-procedure-section">
                <h2>Procedure the sutras print</h2>
                <p className="ritual-layer-note">
                    A different claim from the order above, and a different source. Each work
                    below numbers its own sequence independently, so these are located steps
                    rather than one procedure — they do not run together.
                </p>
                {procedure.length ? (
                    <>
                        {procedureStatus?.note ? (
                            <Caveat>{procedureStatus.note}</Caveat>
                        ) : null}
                        {procedure.map((source) => (
                            <div className="ritual-procedure-source" key={source.work_key}>
                                <h3>
                                    {source.work_label}
                                    <span className="ritual-procedure-meta">
                                        {source.source_type?.toLowerCase()}
                                        {source.veda_school ? ` · ${source.veda_school}` : ""}
                                        {` · ${source.step_count} step${source.step_count === 1 ? "" : "s"}`}
                                        {source.steps && source.step_count
                                        && source.steps.length < source.step_count
                                            ? ` · ${source.steps.length} shown`
                                            : ""}
                                    </span>
                                </h3>
                                <ol className="ritual-procedure-steps">
                                    {source.steps?.map((step) => (
                                        <li key={`${source.work_key}:${step.citation}`}>
                                            <span className="ritual-procedure-citation">
                                                {step.citation}
                                            </span>
                                            <div>
                                                {step.text ? <p lang="sa">{step.text}</p> : null}
                                                {step.order_completeness
                                                    === "PARTIAL_STATED_POSITIONS" ? (
                                                    <p className="ritual-procedure-partial">
                                                        The source states where this step
                                                        falls without printing the run it
                                                        falls in.
                                                    </p>
                                                ) : null}
                                            </div>
                                        </li>
                                    ))}
                                </ol>
                            </div>
                        ))}
                        {ritual.procedure_step_count
                        && procedureShown < ritual.procedure_step_count ? (
                            <p className="ritual-layer-note">
                                {procedureShown} of {ritual.procedure_step_count} steps shown.
                            </p>
                        ) : null}
                    </>
                ) : (
                    <KnowledgeStatus
                        status={procedureStatus?.status ?? "NOT_BUILT"}
                        note={procedureStatus?.note}
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
