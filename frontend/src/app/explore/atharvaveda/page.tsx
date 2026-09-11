import { ArrowRight, FirstAidKit, HouseLine, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { encoded, load, type AvConcerns } from "@/lib/api";
import { conditionLabel, conditionNote, humanizePredicate, normalizeType } from "@/lib/knowledge";

export const metadata = {
    title: "Human concerns in the Atharvaveda",
    description:
        "Healing, protection, household life and prosperity, with afflictions kept distinct from the threats the texts guard against.",
};

type Row = {
    label?: string | null;
    kind?: string | null;
    entity_key?: string | null;
    total_mantras?: number | null;
    vedas_reached?: number | null;
    evidence_status?: string | null;
};

function ConcernRows({ rows, hrefType }: { rows: Row[]; hrefType: string }) {
    return (
        <div className="av-rows">
            {rows.map((row) => {
                const body = (
                    <>
                        <span
                            className={`condition-kind kind-${normalizeType(row.kind).toLowerCase()}`}
                        >
                            {conditionLabel(row.kind)}
                        </span>
                        <strong>{row.label}</strong>
                        <small>
                            {row.total_mantras?.toLocaleString()} matching mantras across{" "}
                            {row.vedas_reached ?? 1}{" "}
                            {row.vedas_reached === 1 ? "collection" : "collections"}
                        </small>
                    </>
                );
                if (!row.entity_key) {
                    return (
                        <div className="av-row is-static" key={row.label}>
                            {body}
                        </div>
                    );
                }
                return (
                    <Link
                        className="av-row"
                        href={`/entities/${hrefType}/${encoded(row.entity_key)}`}
                        key={row.entity_key}
                    >
                        {body}
                        <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                );
            })}
        </div>
    );
}

export default async function AtharvavedaPage() {
    const result = await load<AvConcerns>("/insights/atharvaveda/concerns?limit=20");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;

    // Defence in depth: an affliction view never shows a threat, whatever arrives.
    const afflictions = (data.afflictions ?? []).filter(
        (row) => normalizeType(row.kind) === "AFFLICTION",
    );
    const treatment = (data.protection_and_treatment ?? []).filter(
        (row) => normalizeType(row.condition_kind) !== "THREAT",
    );
    const threats = (data.protection_and_treatment ?? []).filter(
        (row) => normalizeType(row.condition_kind) === "THREAT",
    );

    return (
        <div className="shell page">
            <PageHeading
                title="Human concerns in the Atharvaveda"
                description="Healing, protection, household life and prosperity. What the texts suffer, what they guard against, and what they name as a cause are three different things and stay apart here."
            />
            <KnowledgeStatus status={data.data_status} />

            <section className="av-block">
                <div className="av-section-title">
                    <FirstAidKit size={24} aria-hidden="true" />
                    <div>
                        <h2>Afflictions</h2>
                        <p>
                            Conditions suffered in the body or the household. These counts are
                            Sanskrit lexical-match minima, not diagnoses and not exhaustive topic
                            counts.
                        </p>
                    </div>
                </div>
                <ConcernRows rows={afflictions} hrefType="condition" />
            </section>

            <section className="av-block">
                <div className="av-section-title">
                    <ShieldCheck size={24} aria-hidden="true" />
                    <div>
                        <h2>What the texts address</h2>
                        <p>
                            Each row is one relationship predicate over one target. The predicates
                            differ in how they were established and are never summed.
                        </p>
                    </div>
                </div>
                <div className="evidence-rows">
                    {treatment.map((row, index) => (
                        <article key={`${row.target}-${row.predicate}-${index}`}>
                            <span
                                className={`condition-kind kind-${normalizeType(row.condition_kind || row.kind).toLowerCase()}`}
                            >
                                {row.condition_kind ? conditionLabel(row.condition_kind) : row.kind}
                            </span>
                            <strong>{row.target}</strong>
                            <small>
                                {humanizePredicate(row.predicate)} &middot;{" "}
                                {row.passages?.toLocaleString()} passages
                            </small>
                        </article>
                    ))}
                </div>
            </section>

            {threats.length > 0 && (
                <section className="av-block">
                    <div className="av-section-title">
                        <ShieldCheck size={24} aria-hidden="true" />
                        <div>
                            <h2>Threats guarded against</h2>
                            <p>{conditionNote("THREAT")}</p>
                        </div>
                    </div>
                    <div className="evidence-rows is-threat">
                        {threats.map((row, index) => (
                            <article key={`${row.target}-${row.predicate}-${index}`}>
                                <span className="condition-kind kind-threat">
                                    {conditionLabel(row.condition_kind)}
                                </span>
                                <strong>{row.target}</strong>
                                <small>
                                    {humanizePredicate(row.predicate)} &middot;{" "}
                                    {row.passages?.toLocaleString()} passages
                                </small>
                            </article>
                        ))}
                    </div>
                </section>
            )}

            <section className="av-block">
                <div className="av-section-title">
                    <HouseLine size={24} aria-hidden="true" />
                    <div>
                        <h2>Household and social life</h2>
                        <p>Marriage, house building, childbirth and the rites around them.</p>
                    </div>
                </div>
                <ConcernRows rows={data.social_rites ?? []} hrefType="social_rite" />
            </section>

            <section className="concern-strip">
                <h2>Wider human concerns</h2>
                <div>
                    {data.concerns?.map((row) =>
                        row.entity_key ? (
                            <Link
                                href={`/entities/human_concern/${encoded(row.entity_key)}`}
                                key={row.entity_key}
                            >
                                <strong>{row.label}</strong>
                                <span>{row.total_mantras?.toLocaleString()} lexical matches</span>
                            </Link>
                        ) : null,
                    )}
                </div>
            </section>

            <Caveat title="Atharvaveda scope" tone="boundary">
                The Saunaka recension is held as a working private corpus. The Paippalada recension
                is a substantially different collection and is not present, so an Atharvavedic
                absence measured here is an absence from Saunaka only.
            </Caveat>
            <CaveatList caveats={data.caveats} title="How these counts were measured" limit={6} />
        </div>
    );
}
