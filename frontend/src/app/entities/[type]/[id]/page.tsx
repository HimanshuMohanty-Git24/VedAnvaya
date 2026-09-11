import { ArrowRight, CirclesThreePlus } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { LoadFailure } from "@/components/empty-state";
import { MeasureChart, type MeasureRow } from "@/components/measure";
import { SeerPanel } from "@/components/seer-panel";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { routeId, encoded, load, vedaNames, vedaOrder, type EntityProfile } from "@/lib/api";
import {
    conditionLabel,
    conditionNote,
    entityHref,
    entityTypeLabel,
    humanizePredicate,
} from "@/lib/knowledge";

type Params = { params: Promise<{ type: string; id: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { type: rawType, id: rawId } = await params;
    const type = routeId(rawType);
    const id = routeId(rawId);
    const result = await load<EntityProfile>(
        `/entities/${encodeURIComponent(type)}/${encoded(id)}`,
    );
    if (!result.ok) return { title: "Entity" };
    return {
        title: result.data.display_label ?? "Entity",
        description: result.data.definition ?? result.data.short_description ?? undefined,
    };
}

export default async function EntityPage({ params }: Params) {
    const { type: rawType, id: rawId } = await params;
    const type = routeId(rawType);
    const id = routeId(rawId);
    const result = await load<EntityProfile>(
        `/entities/${encodeURIComponent(type)}/${encoded(id)}`,
    );
    if (!result.ok) {
        if (result.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const entity = result.data;
    const byVeda = entity.passages_by_veda;
    const reachRows: MeasureRow[] = (["rv", "sv", "yv", "av"] as Array<"rv" | "sv" | "yv" | "av">)
        .sort((a, b) => vedaOrder[a.toUpperCase()] - vedaOrder[b.toUpperCase()])
        .map((code) => ({
            key: code,
            label: vedaNames[code.toUpperCase()] ?? code.toUpperCase(),
            value: typeof byVeda?.[code] === "number" ? byVeda[code] : null,
            // A null cell was not reached by the predicates counted here. The block's
            // own status describes the layer, not this row, and must not be reused.
            status: "INSUFFICIENT_EVIDENCE",
        }));
    const anyReach = reachRows.some((row) => row.value != null);

    return (
        <div className="shell page profile-page">
            <PageHeader entity={entity} type={type} />

            <div className="content-grid">
                <div>
                    <div className="entity-detail-meta">
                        <KnowledgeStatus status={entity.data_status} compact />
                        {entity.condition_kind && (
                            <span
                                className={`condition-kind kind-${entity.condition_kind.toLowerCase()}`}
                            >
                                {conditionLabel(entity.condition_kind)}
                            </span>
                        )}
                    </div>

                    {entity.condition_kind && (
                        <Caveat title={conditionLabel(entity.condition_kind)}>
                            {conditionNote(entity.condition_kind)}
                            {entity.condition_kind === "THREAT" &&
                                " It is excluded from affliction views for that reason."}
                        </Caveat>
                    )}

                    {entity.seer && <SeerPanel seer={entity.seer} />}

                    <section className="related-section">
                        <h2>Direct relationships</h2>
                        <p className="panel-note">
                            Edges the graph stores between this record and another.
                        </p>
                        {entity.neighbours?.length ? (
                            <div className="related-grid">
                                {entity.neighbours.map((item) => (
                                    <Link
                                        href={entityHref(item.type, item.id)}
                                        key={`${item.type}-${item.id}`}
                                    >
                                        <span>{entityTypeLabel(item.type)}</span>
                                        <strong>{item.display_label}</strong>
                                        {item.subtitle && (
                                            <small>{humanizePredicate(item.subtitle)}</small>
                                        )}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <KnowledgeStatus
                                status={
                                    entity.dimension_status?.find(
                                        (item) => item.dimension === "neighbours",
                                    )?.status ?? "INSUFFICIENT_EVIDENCE"
                                }
                                note={
                                    entity.dimension_status?.find(
                                        (item) => item.dimension === "neighbours",
                                    )?.note
                                }
                            />
                        )}
                    </section>

                    <section className="related-section">
                        <h2>Named in the same verses</h2>
                        <p className="panel-note">
                            Co-mention is proximity inside a passage. It is not a causal, medical or
                            doctrinal claim.
                        </p>
                        {entity.co_mentioned?.length ? (
                            <div className="related-grid">
                                {entity.co_mentioned.slice(0, 16).map((item) => (
                                    <Link
                                        href={entityHref(item.type, item.id)}
                                        key={`${item.type}-${item.id}`}
                                    >
                                        <span>{entityTypeLabel(item.type)}</span>
                                        <strong>{item.display_label}</strong>
                                        {item.subtitle && <small>{item.subtitle}</small>}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />
                        )}
                    </section>
                </div>

                <aside className="sticky-aside">
                    <div className="panel">
                        <h3>Corpus reach</h3>
                        {anyReach ? (
                            <MeasureChart
                                id="entity-reach"
                                title="Passages reached"
                                definition="Passages that reach this record through the lexical, conceptual or ritual predicates this surface counts."
                                caveat={byVeda?.note ?? undefined}
                                rows={reachRows}
                            />
                        ) : (
                            <KnowledgeStatus
                                status={byVeda?.status ?? "INSUFFICIENT_EVIDENCE"}
                                note={
                                    byVeda?.note ??
                                    "No passage reaches this record through the predicates counted here. It is curated and unattested, rather than absent from the corpus."
                                }
                            />
                        )}
                    </div>

                    {Boolean(entity.aliases_sa?.length || entity.aliases_en?.length) && (
                        <div className="panel">
                            <h3>Other names</h3>
                            <div className="chip-row is-static">
                                {entity.aliases_sa?.map((alias) => (
                                    <span key={alias} lang="sa">
                                        {alias}
                                    </span>
                                ))}
                                {entity.aliases_en?.map((alias) => (
                                    <span key={alias}>{alias}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    <Link className="graph-entry" href={`/graph?node=${encoded(entity.id)}`}>
                        <CirclesThreePlus size={20} aria-hidden="true" />
                        <span>
                            <strong>Open in the graph</strong>
                            <small>See this record and what it connects to</small>
                        </span>
                        <ArrowRight size={16} aria-hidden="true" />
                    </Link>

                    <CaveatList caveats={entity.caveats} title="How this record was built" />
                </aside>
            </div>
        </div>
    );
}

function PageHeader({ entity, type }: { entity: EntityProfile; type: string }) {
    return (
        <header className="page-heading">
            <Link className="back-link" href={`/entities/${type}`}>
                All {humanizePredicate(type)}
            </Link>
            {entity.preferred_label_sa && (
                <span className="profile-iast" lang="sa">
                    {entity.preferred_label_sa}
                </span>
            )}
            <h1>{entity.display_label}</h1>
            {(entity.definition || entity.short_description) && (
                <p>{entity.definition ?? entity.short_description}</p>
            )}
        </header>
    );
}
