import { ArrowRight, ArrowsLeftRight, CirclesThreePlus } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { AskAboutButton } from "@/components/ask/ask-about-button";
import { DerivedMetricCard } from "@/components/derived-metric";
import { LoadFailure, NothingHere } from "@/components/empty-state";
import { MeasureChart, RankedFacts, type MeasureRow } from "@/components/measure";
import { Caveat, CaveatList, InterpretationFrame, KnowledgeStatus } from "@/components/status";
import {
    encoded,
    load,
    routeId,
    vedaNames,
    vedaOrder,
    type DevataInsight,
    type DevataPassagePage,
    type DevataProfile,
} from "@/lib/api";
import { humanizePredicate, titleCase } from "@/lib/knowledge";

/**
 * Identities the corpus does not lexically separate. The graph separates them as an
 * editorial aid, so the page says so and links both records.
 */
const IDENTITY_PAIRS: Record<string, { href: string; label: string; note: string }> = {
    "VG:DEVATA:AGNIH": {
        href: `/entities/natural_phenomenon/${encodeURIComponent("VG:CONCEPT:AGNI-FIRE")}`,
        label: "fire (agni), the phenomenon",
        note: "This page is Agni the deity. Fire as the ritual and natural phenomenon is a separate record. The corpus uses one word for both, so the separation is a navigational aid rather than a distinction the text draws.",
    },
    "VG:DEVATA:SOMAH": {
        href: `/entities/offering/${encodeURIComponent("VG:CONCEPT:SOMA-DRINK")}`,
        label: "soma juice, the substance",
        note: "This page is Soma the deity. The pressed plant and its juice are a separate record. The corpus uses one word for both, so the separation is a navigational aid rather than a distinction the text draws.",
    },
};

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { id } = await params;
    const result = await load<DevataProfile>(`/devatas/${encoded(routeId(id))}`);
    if (!result.ok) return { title: "Deity" };
    return {
        title: result.data.display_label ?? "Deity",
        description: result.data.short_description ?? undefined,
    };
}

export default async function DevataPage({ params }: Params) {
    const { id } = await params;
    const decodedId = routeId(id);
    const result = await load<DevataProfile>(`/devatas/${encoded(decodedId)}`);
    if (!result.ok) {
        if (result.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const deity = result.data;

    const [insightResult, mentionPassages, ascriptionPassages] = await Promise.all([
        load<DevataInsight>(`/insights/devatas/${encoded(decodedId)}`),
        load<DevataPassagePage>(`/devatas/${encoded(decodedId)}/passages?basis=mention&limit=8`),
        load<DevataPassagePage>(`/devatas/${encoded(decodedId)}/passages?basis=ascription&limit=8`),
    ]);
    const insight = insightResult.ok ? insightResult.data : null;
    const identity = IDENTITY_PAIRS[decodedId];

    const byVeda = [...(deity.mentions_by_veda ?? [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );
    const mentionRows: MeasureRow[] = byVeda.map((row) => ({
        key: row.veda ?? "",
        label: vedaNames[row.veda ?? ""] ?? row.veda ?? "",
        value: row.count ?? null,
        status: row.status,
        note:
            (row.certainty?.ambiguous_count ?? 0) > 0
                ? `holds back ${row.certainty?.ambiguous_count?.toLocaleString()} ambiguous mentions`
                : null,
    }));

    const attributionRows: MeasureRow[] = [
        {
            key: "per-passage",
            label: "Stated for the verse",
            value: deity.attributed_per_passage ?? null,
            tone: "primary",
        },
        {
            key: "inherited",
            label: "Inherited from the hymn",
            value: deity.attributed_inherited ?? null,
            tone: "muted",
            note: "the hymn heading projected onto every verse inside it",
        },
    ];

    const ambiguous = deity.certainty.ambiguous_count ?? 0;
    const scopeOfAttribution = (deity.attribution_scope ?? []).map(
        (code) => vedaNames[code] ?? code,
    );

    return (
        <div className="shell page profile-page">
            <div className="profile-hero">
                <div>
                    <Link className="back-link" href="/devatas">
                        Deity atlas
                    </Link>
                    <span className="profile-iast" lang="sa">
                        {deity.preferred_label ?? deity.label_iast}
                    </span>
                    <h1>{deity.display_label}</h1>
                    <p>{deity.short_description}</p>
                    {deity.epithets?.length ? (
                        <div className="alias-line">
                            <span className="alias-label">Epithets</span>
                            {deity.epithets.slice(0, 6).map((epithet) => (
                                <span key={epithet} lang="sa">
                                    {epithet}
                                </span>
                            ))}
                        </div>
                    ) : null}
                    {deity.axes?.length ? (
                        <div className="axis-list">
                            {deity.axes.map((axis) => (
                                <span key={axis}>{humanizePredicate(axis)}</span>
                            ))}
                        </div>
                    ) : null}
                </div>
                <div className="profile-actions">
                    <KnowledgeStatus status={deity.data_status} compact />
                    <Link className="button primary" href={`/graph?node=${encoded(deity.id)}`}>
                        <CirclesThreePlus size={18} aria-hidden="true" />
                        Explore connections
                    </Link>
                    <AskAboutButton
                        entityLabel={deity.display_label ?? deity.preferred_label ?? decodedId}
                        label={`Ask about ${deity.display_label ?? "this deity"}`}
                    />
                </div>
            </div>

            {identity && (
                <Caveat title="Two records, one word" tone="boundary">
                    {identity.note}{" "}
                    <Link className="text-link" href={identity.href}>
                        Open {identity.label}
                        <ArrowsLeftRight size={15} aria-hidden="true" />
                    </Link>
                </Caveat>
            )}

            <div className="profile-grid">
                <div className="profile-main">
                    <section>
                        <div className="section-heading small">
                            <h2>Across the four Vedas</h2>
                            <p>
                                Where this deity is named in the text, counted per collection.
                                Certain and probable mentions are included; ambiguous ones are held
                                back and shown separately below.
                            </p>
                        </div>
                        <MeasureChart
                            id="mentions-by-veda"
                            title="Named in the text"
                            definition="Passages in which a registered form of this name occurs, counted once per passage."
                            scope={`Measured over ${(deity.mention_scope ?? []).map((code) => vedaNames[code] ?? code).join(", ")}.`}
                            caveat="These are Sanskrit surface matches and therefore lower bounds. Being named is not the same as the passage being about the deity."
                            rows={mentionRows}
                            unit="passages"
                        />

                        <div className="certainty-split">
                            <div>
                                <strong>{deity.certainty.certain_count.toLocaleString()}</strong>
                                <span>Certain</span>
                            </div>
                            <div>
                                <strong>{deity.certainty.probable_count.toLocaleString()}</strong>
                                <span>Probable</span>
                            </div>
                            <div className="is-ambiguous">
                                <strong>{ambiguous.toLocaleString()}</strong>
                                <span>Ambiguous</span>
                                <small>
                                    Held back from every figure above. The referent could not be
                                    resolved, so counting these would overstate the deity.
                                </small>
                            </div>
                        </div>
                    </section>

                    <section>
                        <div className="section-heading small">
                            <h2>Ascribed by the apparatus</h2>
                            <p>
                                The traditional hymn dedication, which is a different kind of record
                                from being named in a verse. The two are never summed.
                            </p>
                        </div>
                        <MeasureChart
                            id="attribution-split"
                            title="How the ascription was recorded"
                            definition="Passages carrying this deity as their dedication, split by whether the source states it verse by verse or the hymn heading was projected downward."
                            scope={
                                scopeOfAttribution.length
                                    ? `The ascription apparatus exists for ${scopeOfAttribution.join(", ")} only. A zero elsewhere is a missing apparatus, not an absent deity.`
                                    : undefined
                            }
                            rows={attributionRows}
                            unit="passages"
                        />
                        {insight?.ascription_note && (
                            <p className="panel-note">{insight.ascription_note}</p>
                        )}
                    </section>

                    <section className="profile-sections">
                        <RankedFacts
                            title="What this deity does"
                            definition="Actions where the deity stands as the grammatical agent. Read from the Rigvedic morphological annotation only."
                            items={(deity.top_actions ?? []).slice(0, 10).map((item) => ({
                                key: item,
                                label: titleCase(humanizePredicate(item)),
                            }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                        <RankedFacts
                            title="What it is asked to do"
                            definition="Actions in the imperative or optative: what the poets request, as distinct from what is asserted."
                            items={(deity.top_requested_actions ?? []).slice(0, 10).map((item) => ({
                                key: item,
                                label: titleCase(humanizePredicate(item)),
                            }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                        <RankedFacts
                            title="Associated ideas"
                            definition="Registered concepts named in the same passages."
                            items={(deity.top_concepts ?? [])
                                .slice(0, 10)
                                .map((item) => ({ key: item, label: item }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                        <RankedFacts
                            title="Objects and substances"
                            items={(deity.top_objects ?? [])
                                .slice(0, 10)
                                .map((item) => ({ key: item, label: item }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                        <RankedFacts
                            title="Seers of its hymns"
                            definition="Ranked over the ascription apparatus, most of which is inherited from the hymn heading."
                            items={(deity.top_rishis ?? [])
                                .slice(0, 10)
                                .map((item) => ({ key: item, label: item }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                        <RankedFacts
                            title="Metres"
                            items={(deity.top_chandas ?? [])
                                .slice(0, 10)
                                .map((item) => ({ key: item, label: item }))}
                            empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                        />
                    </section>

                    <section>
                        <div className="section-heading small">
                            <h2>Named alongside</h2>
                            <p>
                                Deities that share passages with this one. Co-mention is proximity
                                in a verse, not a relationship the text asserts.
                            </p>
                        </div>
                        {deity.co_mentioned?.length ? (
                            <div className="chip-row">
                                {deity.co_mentioned.slice(0, 12).map((name) => (
                                    <Link href={`/search?q=${encodeURIComponent(name)}`} key={name}>
                                        {name}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <KnowledgeStatus
                                status={
                                    deity.dimension_status?.find(
                                        (item) => item.dimension === "co_devatas",
                                    )?.status ?? "INSUFFICIENT_EVIDENCE"
                                }
                                note={
                                    deity.dimension_status?.find(
                                        (item) => item.dimension === "co_devatas",
                                    )?.note
                                }
                            />
                        )}
                    </section>

                    <section>
                        <div className="section-heading small">
                            <h2>Formula families</h2>
                            <p>Shared wording that recurs in passages naming this deity.</p>
                        </div>
                        {deity.top_formulas?.length ? (
                            <div className="formula-chip-list">
                                {deity.top_formulas.slice(0, 8).map((formula) => (
                                    <div className="formula-chip" key={formula.id}>
                                        <strong className="sanskrit" lang="sa">
                                            {formula.display_label}
                                        </strong>
                                        <small>{formula.subtitle}</small>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />
                        )}
                    </section>

                    <section>
                        <div className="section-heading small">
                            <h2>Passages to read</h2>
                            <p>
                                Verses that name this deity, and verses the apparatus dedicates to
                                it. These are different claims and are listed separately.
                            </p>
                        </div>
                        <div className="passage-columns">
                            <div>
                                <h3>Named in the verse</h3>
                                {mentionPassages.ok && mentionPassages.data.items?.length ? (
                                    <ul className="citation-list">
                                        {mentionPassages.data.items.map((row) => (
                                            <li key={`m-${row.passage_id}`}>
                                                <Link href={`/passage/${encoded(row.passage_id)}`}>
                                                    <strong>{row.citation}</strong>
                                                    <small>
                                                        {row.matched_forms?.length
                                                            ? row.matched_forms.join(", ")
                                                            : "form not recorded"}
                                                    </small>
                                                </Link>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />
                                )}
                            </div>
                            <div>
                                <h3>Dedicated by the apparatus</h3>
                                {ascriptionPassages.ok && ascriptionPassages.data.items?.length ? (
                                    <ul className="citation-list">
                                        {ascriptionPassages.data.items.map((row) => (
                                            <li key={`a-${row.passage_id}`}>
                                                <Link href={`/passage/${encoded(row.passage_id)}`}>
                                                    <strong>{row.citation}</strong>
                                                    <small>
                                                        {row.attribution_precision === "PER_PASSAGE"
                                                            ? "stated for this verse"
                                                            : "inherited from the hymn"}
                                                    </small>
                                                </Link>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <KnowledgeStatus
                                        status="INSUFFICIENT_EVIDENCE"
                                        note="No dedication apparatus reaches this deity in the collections that carry one."
                                    />
                                )}
                            </div>
                        </div>
                    </section>

                    {insight?.derived_metrics?.length ? (
                        <section>
                            <div className="section-heading small">
                                <h2>Derived measures</h2>
                                <p>
                                    Computed over this graph. Each states its method, and none is a
                                    statement the texts make.
                                </p>
                            </div>
                            <div className="derived-grid">
                                {insight.derived_metrics.map((metric) => (
                                    <DerivedMetricCard key={metric.metric_id} metric={metric} />
                                ))}
                            </div>
                        </section>
                    ) : null}

                    {deity.interpretive_claims?.length ? (
                        <section>
                            <div className="section-heading small">
                                <h2>Interpretation on record</h2>
                            </div>
                            {deity.interpretive_claims.map((claim) => (
                                <InterpretationFrame key={claim.id}>
                                    <blockquote>{claim.display_label}</blockquote>
                                    {claim.subtitle && <cite>{claim.subtitle}</cite>}
                                </InterpretationFrame>
                            ))}
                        </section>
                    ) : null}
                </div>

                <aside className="sticky-aside">
                    <div className="panel">
                        <h3>Atlas coordinates</h3>
                        <dl className="provenance-list">
                            <div>
                                <dt>Structure</dt>
                                <dd>{humanizePredicate(deity.structure)}</dd>
                            </div>
                            <div>
                                <dt>Resolved as a deity</dt>
                                <dd>{deity.is_deity ? "Yes" : "Not resolved"}</dd>
                            </div>
                            <div>
                                <dt>Named in</dt>
                                <dd>
                                    {(deity.mention_scope ?? [])
                                        .map((code) => vedaNames[code] ?? code)
                                        .join(", ") || "Not recorded"}
                                </dd>
                            </div>
                            <div>
                                <dt>Ascription apparatus</dt>
                                <dd>
                                    {scopeOfAttribution.join(", ") || "None reaches this deity"}
                                </dd>
                            </div>
                        </dl>
                    </div>

                    {deity.aliases?.length ? (
                        <div className="panel">
                            <h3>Registered forms</h3>
                            <p className="panel-note">
                                The Sanskrit surfaces the matcher accepts for this name.
                            </p>
                            <div className="chip-row is-static">
                                {deity.aliases.map((alias) => (
                                    <span key={alias} lang="sa">
                                        {alias}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ) : null}

                    <Link
                        className="graph-entry"
                        href={`/search?q=${encodeURIComponent(deity.display_label ?? "")}`}
                    >
                        <ArrowRight size={20} aria-hidden="true" />
                        <span>
                            <strong>Search this name</strong>
                            <small>See every entity and text match, including look-alikes</small>
                        </span>
                    </Link>

                    <CaveatList
                        caveats={deity.caveats}
                        title="How this profile was built"
                        limit={6}
                    />
                </aside>
            </div>

            {!deity.top_actions?.length && !deity.top_concepts?.length && (
                <NothingHere
                    title="Little is modelled for this deity yet"
                    message="This record exists in the registry, and the action and concept layers did not reach it. That is a limit of what was built."
                    action={{ href: "/devatas", label: "Back to the deity atlas" }}
                />
            )}
        </div>
    );
}
