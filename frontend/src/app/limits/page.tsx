import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { load, type Capabilities } from "@/lib/api";

export const metadata = {
    title: "What this atlas cannot answer",
    description:
        "Every recorded limit of the current build, with the measurement behind it and a safer question to ask instead.",
};

const VERDICT_COPY: Record<string, { label: string; note: string }> = {
    NOT_ANSWERABLE: {
        label: "Cannot be answered",
        note: "The dimension this question asks about was never built.",
    },
    PARTIALLY_ANSWERABLE: {
        label: "Partly answerable",
        note: "Some of this can be answered, and the rest would overstate what was built.",
    },
};

export default async function LimitsPage() {
    const result = await load<Capabilities>("/insights/capabilities");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    // Read, never typed. See the caveat below for why.
    const total = data.benchmark_not_answerable_total ?? 0;
    const published = data.benchmark_not_answerable_published ?? 0;
    const unpublished = data.unpublished_not_answerable ?? [];

    return (
        <div className="shell page limits-page">
            <PageHeading
                title="What this atlas cannot answer"
                description="Every limit recorded here is a fact about this graph, never about the Vedas. An honest refusal is an outcome, not a failure."
            />
            <KnowledgeStatus
                status={data.data_status}
                note={`${published} of the ${total} questions the benchmark grades unanswerable are catalogued here, each with a probe that runs on request. Each limit below is a separate finding.`}
            />

            {/*
             * The completeness figures are read from the response, not typed. This box used
             * to say the catalogue was "complete for the questions the benchmark probed"
             * while the endpoint published seven cards against twenty-one graded questions.
             * Both numbers now come from the same payload the cards come from, so the claim
             * cannot drift from the list beneath it.
             */}
            <Caveat title="This catalogue is not a complete account of what this atlas cannot do" tone="boundary">
                It covers every question the hundred-question benchmark graded unanswerable
                {unpublished.length > 0
                    ? ` except ${unpublished.length} still unpublished`
                    : ""}
                . The benchmark is a hundred questions rather than every question, so a
                question absent from this list is not thereby answerable.
            </Caveat>

            <div className="limit-list">
                {data.limits?.map((limit) => {
                    const verdict = VERDICT_COPY[limit.verdict] ?? {
                        label: limit.verdict,
                        note: "",
                    };
                    return (
                        <article className="limit-card" key={limit.limit_id}>
                            <header>
                                <div>
                                    <span
                                        className={`verdict verdict-${limit.verdict.toLowerCase()}`}
                                    >
                                        {verdict.label}
                                    </span>
                                    <h2>{limit.question}</h2>
                                </div>
                                <KnowledgeStatus status={limit.data_status} compact />
                            </header>

                            <div className="limit-body">
                                <section>
                                    <h3>Why</h3>
                                    <p>{limit.why}</p>
                                </section>
                                <section>
                                    <h3>What this is not</h3>
                                    <p>{limit.what_this_is_not}</p>
                                </section>
                            </div>

                            {limit.measurements?.length ? (
                                <table className="limit-measurements">
                                    <caption className="sr-only">
                                        Measurements behind this limit
                                    </caption>
                                    <tbody>
                                        {limit.measurements.map((measurement) => (
                                            <tr key={measurement.name}>
                                                <th scope="row">
                                                    {measurement.name.replaceAll("_", " ")}
                                                </th>
                                                <td>{measurement.value?.toLocaleString()}</td>
                                                <td>{measurement.means}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : null}

                            {limit.safe_alternative && (
                                <p className="limit-alternative">
                                    <strong>Ask this instead</strong>
                                    {limit.safe_alternative}
                                </p>
                            )}
                        </article>
                    );
                })}
            </div>

            <p className="limits-footer">
                Coverage that exists but is partial is marked in place, wherever it appears.{" "}
                <Link className="text-link" href="/insights">
                    See how evidence and interpretation are separated
                </Link>
            </p>

            <CaveatList caveats={data.caveats} title="How this catalogue was built" />
        </div>
    );
}
