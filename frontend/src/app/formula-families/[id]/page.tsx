import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { LoadFailure } from "@/components/empty-state";
import { MeasureChart, type MeasureRow } from "@/components/measure";
import { PageHeading } from "@/components/page-heading";
import { CaveatList, KnowledgeStatus } from "@/components/status";
import { routeId, encoded, load, vedaNames, vedaOrder, type FormulaFamily } from "@/lib/api";
import { evidenceBasisCopy, trustTierCopy } from "@/lib/knowledge";

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { id: rawId } = await params;
    const id = routeId(rawId);
    const result = await load<FormulaFamily>(`/formula-families/${encoded(id)}`);
    if (!result.ok) return { title: "Formula family" };
    return { title: result.data.representative_display_form ?? "Formula family" };
}

export default async function FormulaFamilyPage({ params }: Params) {
    const { id: rawId } = await params;
    const id = routeId(rawId);
    const result = await load<FormulaFamily>(`/formula-families/${encoded(id)}`);
    if (!result.ok) {
        if (result.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const family = result.data;
    const groups = [
        {
            title: "Core forms",
            note: "The shared wording itself.",
            items: family.core,
        },
        {
            title: "Expansions",
            note: "Longer phrases that contain the core wording.",
            items: family.expansions,
        },
        {
            title: "Variants",
            note: "Wordings that differ slightly from the core.",
            items: family.variants,
        },
    ];

    const occurrenceRows: MeasureRow[] = Object.entries(family.occurrences_by_veda ?? {})
        .sort(([a], [b]) => (vedaOrder[a] ?? 9) - (vedaOrder[b] ?? 9))
        .map(([veda, count]) => ({
            key: veda,
            label: vedaNames[veda] ?? veda,
            value: typeof count === "number" ? count : null,
        }));

    const byVeda = new Map<string, typeof family.occurrences>();
    for (const occurrence of family.occurrences ?? []) {
        const list = byVeda.get(occurrence.veda ?? "") ?? [];
        list.push(occurrence);
        byVeda.set(occurrence.veda ?? "", list);
    }

    return (
        <div className="shell page">
            <PageHeading
                title={family.representative_display_form ?? "Formula family"}
                description="A family of shared wording. Its reach across collections measures diction, not a demonstrated line of transmission."
                backHref="/formulas"
                backLabel="Formula families"
            />

            <div className="formula-stats">
                <div>
                    <strong>{family.member_count}</strong>
                    <span>member wordings</span>
                </div>
                <div>
                    <strong>{family.mantra_count}</strong>
                    <span>distinct mantras</span>
                </div>
                <div>
                    <strong>{family.veda_span}</strong>
                    <span>collections reached</span>
                </div>
                <KnowledgeStatus status={family.data_status} compact />
            </div>

            <section className="family-tree">
                <h2>The shape of this family</h2>
                <div className="family-branches">
                    {groups.map((group) => (
                        <div key={group.title}>
                            <h3>
                                {group.title}
                                <span>{group.items?.length ?? 0}</span>
                            </h3>
                            <p className="panel-note">{group.note}</p>
                            {group.items?.length ? (
                                <ul>
                                    {group.items.map((item) => (
                                        <li key={item.formula_id}>
                                            <strong className="sanskrit" lang="sa">
                                                {item.display_form}
                                            </strong>
                                            <small>
                                                {item.passage_count} passages &middot;{" "}
                                                {(item.vedas ?? []).join(", ") ||
                                                    "collections not recorded"}
                                            </small>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <KnowledgeStatus
                                    status="INSUFFICIENT_EVIDENCE"
                                    note={`No ${group.title.toLowerCase()} were derived for this family.`}
                                    compact
                                />
                            )}
                        </div>
                    ))}
                </div>
            </section>

            <section>
                <MeasureChart
                    id="formula-occurrences"
                    title="Where this wording occurs"
                    definition="Occurrences of any member wording, counted per collection."
                    scope="A collection absent from this chart carries no occurrence of any member in the current build."
                    caveat="The Rigveda is the largest corpus and much of the Samaveda and Yajurveda draws on it, so a four-collection family is often one Rigvedic phrase carried forward rather than four independent attestations."
                    rows={occurrenceRows}
                    unit="occurrences"
                />
            </section>

            <section className="occurrence-section">
                <h2>Read the occurrences</h2>
                <div className="occurrence-columns">
                    {[...byVeda.entries()]
                        .sort(([a], [b]) => (vedaOrder[a] ?? 9) - (vedaOrder[b] ?? 9))
                        .map(([veda, occurrences]) => (
                            <div key={veda}>
                                <h3>{vedaNames[veda] ?? veda}</h3>
                                <ul className="citation-list">
                                    {(occurrences ?? []).slice(0, 10).map((occurrence, index) => (
                                        <li key={`${occurrence.passage_id}-${index}`}>
                                            <Link
                                                href={`/passage/${encoded(occurrence.passage_id)}`}
                                            >
                                                <strong>{occurrence.citation}</strong>
                                                <small className="sanskrit" lang="sa">
                                                    {occurrence.source_form}
                                                </small>
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                </div>
                {family.occurrences_truncated && (
                    <p className="panel-note">
                        More occurrences exist than are listed here. Open the graph to walk the
                        rest.
                    </p>
                )}
                <Link className="text-link" href={`/graph?node=${encoded(family.id)}`}>
                    Open this family in the graph
                    <ArrowRight size={16} aria-hidden="true" />
                </Link>
            </section>

            <section className="evidence-summary">
                <h2>How this family was derived</h2>
                <dl>
                    <div>
                        <dt>Knowledge grade</dt>
                        <dd>{trustTierCopy(family.evidence?.tier)}</dd>
                    </div>
                    <div>
                        <dt>How it was established</dt>
                        <dd>{evidenceBasisCopy(family.evidence?.evidence_basis).label}</dd>
                    </div>
                    <div>
                        <dt>Grade basis</dt>
                        <dd>{family.grade_basis ?? "Not recorded"}</dd>
                    </div>
                    <div>
                        <dt>Representative coverage</dt>
                        <dd>
                            {family.representative_coverage != null
                                ? `${Math.round(family.representative_coverage * 100)}% of the family's distinct mantras`
                                : "Not recorded"}
                        </dd>
                    </div>
                </dl>
                {family.notes && <p className="panel-note">{family.notes}</p>}
                {family.reconciliation && (
                    <details className="provenance">
                        <summary>Membership reconciliation</summary>
                        <p>
                            Recorded members: {family.reconciliation.recorded_member_count}.
                            Traversed members: {family.reconciliation.traversed_member_count}.{" "}
                            {family.reconciliation.agrees
                                ? "The two agree."
                                : "The two disagree, and this family is therefore unreconciled."}
                        </p>
                    </details>
                )}
            </section>

            <CaveatList caveats={family.caveats} title="Scope notes" />
        </div>
    );
}
