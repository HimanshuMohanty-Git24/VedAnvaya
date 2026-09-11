import Link from "next/link";
import { MeasureChart, RankedFacts, type MeasureRow } from "@/components/measure";
import { encoded, vedaNames, vedaOrder, type RishiProfile } from "@/lib/api";
import { entityHref, humanizePredicate } from "@/lib/knowledge";
import { KnowledgeStatus } from "./status";

/**
 * Everything specific to a name in the seer slot: whether it is a seer at all,
 * how its attributions were recorded, and which family it belongs to.
 */
export function SeerPanel({ seer }: { seer: RishiProfile }) {
    const reach: MeasureRow[] = [...(seer.passages_by_veda ?? [])]
        .sort((a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9))
        .map((row) => ({
            key: row.veda ?? "",
            label: vedaNames[row.veda ?? ""] ?? row.veda ?? "",
            value: row.count ?? null,
            status: row.status,
        }));

    const attribution: MeasureRow[] = [
        {
            key: "stated",
            label: "Stated by the source",
            value: seer.passages_source_stated ?? null,
            tone: "primary",
        },
        {
            key: "inherited",
            label: "Inherited from the hymn",
            value: seer.passages_container_inherited ?? null,
            tone: "muted",
            note: "the hymn heading projected onto every verse inside it",
        },
    ];

    return (
        <section className="seer-panel panel">
            <h2>As a name in the seer apparatus</h2>

            {seer.is_seer === false ? (
                <KnowledgeStatus
                    status="INSUFFICIENT_EVIDENCE"
                    note={`This name occupies a traditional seer slot but is classified as ${humanizePredicate(seer.non_seer_kind)}. It is not presented here as a composer of hymns.`}
                />
            ) : (
                <p className="panel-note">
                    Recorded as a seer in the traditional apparatus. Most such records are hymn
                    headings rather than verse-by-verse statements, and the split below shows which.
                </p>
            )}

            <MeasureChart
                id="seer-attribution"
                title="How the attribution was recorded"
                definition="Passages carrying this name, split by whether the source states it for the verse or a hymn heading was projected downward."
                caveat="The two are never summed: a statement of the text and a projection of this build are different claims."
                rows={attribution}
                unit="passages"
            />

            {reach.length > 0 && (
                <MeasureChart
                    id="seer-reach"
                    title="Reach by collection"
                    definition="Passages attributed to this name in each corpus."
                    scope={
                        seer.layer_veda_scope?.length
                            ? `This layer reaches ${seer.layer_veda_scope.map((code) => vedaNames[code] ?? code).join(", ")}. A collection absent from that list has no coverage here, which is not the same as the name being absent from it.`
                            : undefined
                    }
                    rows={reach}
                />
            )}

            <div className="seer-facts">
                <div>
                    <h3>Family</h3>
                    {seer.family ? (
                        <Link
                            className="text-link"
                            href={entityHref("RISHI_FAMILY", seer.family.id ?? "")}
                        >
                            {seer.family.display_label}
                        </Link>
                    ) : (
                        <KnowledgeStatus
                            status="INSUFFICIENT_EVIDENCE"
                            note={`Not established from current evidence. The apparatus records this name as ${humanizePredicate(seer.family_assignment_class)}, so no family is asserted rather than none existing.`}
                        />
                    )}
                </div>

                {seer.family_members?.length ? (
                    <div>
                        <h3>Named alongside in the family</h3>
                        <div className="chip-row">
                            {seer.family_members.slice(0, 10).map((member) => (
                                <Link
                                    key={member.id}
                                    href={`/entities/rishi/${encoded(member.id)}`}
                                >
                                    {member.display_label}
                                </Link>
                            ))}
                        </div>
                    </div>
                ) : null}
            </div>

            <div className="seer-associations">
                <RankedFacts
                    title="Deities in these hymns"
                    items={(seer.deities ?? []).slice(0, 8).map((item) => ({
                        key: item.id,
                        label: item.display_label ?? item.id,
                    }))}
                    empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                />
                <RankedFacts
                    title="Ideas in these hymns"
                    items={(seer.concepts ?? []).slice(0, 8).map((item) => ({
                        key: item.id,
                        label: item.display_label ?? item.id,
                    }))}
                    empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                />
                <RankedFacts
                    title="Metres"
                    items={(seer.chandas ?? []).slice(0, 8).map((item) => ({
                        key: item.id,
                        label: item.display_label ?? item.id,
                    }))}
                    empty={<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />}
                />
            </div>

            <details className="provenance">
                <summary>Registry details</summary>
                <dl className="provenance-list">
                    <div>
                        <dt>Registry</dt>
                        <dd>{seer.registry_namespace ?? "Not recorded"}</dd>
                    </div>
                    <div>
                        <dt>Normalised name</dt>
                        <dd>{seer.normalized_name ?? "Not recorded"}</dd>
                    </div>
                    <div>
                        <dt>Name decomposition</dt>
                        <dd>{humanizePredicate(seer.decomposition_method)}</dd>
                    </div>
                    <div>
                        <dt>Patronymic</dt>
                        <dd>{seer.patronymic_iast ?? "Not established"}</dd>
                    </div>
                    <div>
                        <dt>Personal name</dt>
                        <dd>{seer.personal_name_iast ?? "Not established"}</dd>
                    </div>
                    <div>
                        <dt>Family assignment</dt>
                        <dd>{humanizePredicate(seer.family_assignment_class)}</dd>
                    </div>
                </dl>
            </details>
        </section>
    );
}
