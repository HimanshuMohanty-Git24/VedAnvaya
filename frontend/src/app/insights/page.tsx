import Link from "next/link";
import { DerivedMetricCard } from "@/components/derived-metric";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, InterpretationFrame, KnowledgeStatus } from "@/components/status";
import { load, type Civilization } from "@/lib/api";
import { humanizePredicate, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "Evidence and interpretation",
    description:
        "Measured textual data, derived metrics and candidate interpretations, presented as three different kinds of knowledge.",
};

const SECTION_COPY: Record<string, { kicker: string; note: string }> = {
    DATA: {
        kicker: "Measured from the text",
        note: "Counted directly over passages held in this graph.",
    },
    DERIVED_METRIC: {
        kicker: "Derived measure",
        note: "Computed from the data by a stated method. A number here is a property of this build, not a statement the texts make.",
    },
    INTERPRETIVE_CLAIM: {
        kicker: "Interpretation",
        note: "A reading someone put forward, recorded with what would falsify it. Never equivalent to a textual statement.",
    },
};

export default async function InsightsPage() {
    const result = await load<Civilization>("/insights/civilization?limit=16");
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
                title="Evidence and interpretation"
                description="Three kinds of knowledge sit on this page, and they never look alike: what the texts say, what we computed from it, and what someone reads into it."
            />

            <Caveat title="Reading this page">
                A measured row is a count over passages. A derived measure is a calculation over
                those counts. An interpretation is a claim about what they mean, and it carries the
                observation that would falsify it.{" "}
                <Link className="text-link" href="/limits">
                    See what this product cannot answer
                </Link>
            </Caveat>

            {data.sections?.map((section) => {
                const copy = SECTION_COPY[section.section_kind] ?? {
                    kicker: titleCase(humanizePredicate(section.section_kind)),
                    note: "",
                };
                return (
                    <section
                        className={`insight-section insight-${section.section_kind.toLowerCase()}`}
                        key={section.section_kind}
                        data-knowledge-kind={section.section_kind.toLowerCase()}
                    >
                        <header>
                            <div>
                                <span>{copy.kicker}</span>
                                <h2>{section.title}</h2>
                                <p>{section.what_this_is}</p>
                            </div>
                            <KnowledgeStatus status={section.data_status} compact />
                        </header>

                        {section.data_rows && (
                            <div className="data-row-grid">
                                {section.data_rows.map((row) => (
                                    <article key={row.kind}>
                                        <strong>{row.kind}</strong>
                                        <span>{row.passages.toLocaleString()} passages</span>
                                        <small>{row.vedas?.join(", ")}</small>
                                    </article>
                                ))}
                            </div>
                        )}

                        {section.metric_rows && (
                            <div className="derived-grid">
                                {section.metric_rows.map((row) => (
                                    <DerivedMetricCard key={row.metric_id} metric={row} />
                                ))}
                            </div>
                        )}

                        {section.claim_rows && (
                            <div className="claim-list">
                                {section.claim_rows.map((claim) => (
                                    <InterpretationFrame
                                        key={claim.claim_id}
                                        label="One reading"
                                        note="Recorded as a claim, with what would falsify it."
                                    >
                                        <blockquote>{claim.claim_text}</blockquote>
                                        <dl>
                                            <div>
                                                <dt>About</dt>
                                                <dd>{humanizePredicate(claim.about)}</dd>
                                            </div>
                                            <div>
                                                <dt>Asserted by</dt>
                                                <dd>{claim.asserted_by ?? "Not recorded"}</dd>
                                            </div>
                                            <div>
                                                <dt>What would falsify it</dt>
                                                <dd>{claim.falsifier}</dd>
                                            </div>
                                        </dl>
                                        {claim.contradicts?.length ? (
                                            <p className="counterclaim">
                                                A contradicting claim is on record:{" "}
                                                {claim.contradicts.join(", ")}
                                            </p>
                                        ) : null}
                                    </InterpretationFrame>
                                ))}
                            </div>
                        )}

                        <CaveatList caveats={section.caveats} title="Scope of this section" />
                    </section>
                );
            })}

            <CaveatList caveats={data.caveats} title="Scope of this page" limit={6} />
        </div>
    );
}
