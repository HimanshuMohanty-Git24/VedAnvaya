import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { load, loadCompleteness, type Capabilities } from "@/lib/api";

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
    const [result, completeness] = await Promise.all([
        load<Capabilities>("/insights/capabilities"),
        loadCompleteness(),
    ]);

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
                status="SUPPORTED"
                note={`Certified Release Commit: ${completeness.certified_release_commit.slice(0, 7)} · Core Corpus: ${completeness.total_canonical_mantras.toLocaleString("en-GB")} canonical mantras across 4 Samhitas.`}
            />

            <section className="limits-system-section" style={{ marginBlock: "var(--va-space-2xl)", display: "flex", flexDirection: "column", gap: "var(--va-space-xl)" }}>
                <div>
                    <h2 style={{ fontFamily: "var(--va-font-display)", fontSize: "var(--va-text-2xl)", marginBottom: "var(--va-space-xs)" }}>
                        System Limitations & Corpus Invariants
                    </h2>
                    <p style={{ color: "var(--va-text-secondary)", fontSize: "var(--va-text-sm)", maxWidth: "var(--va-measure)" }}>
                        The core boundaries established by certified data releases. These limits govern what data is held, how evidence is typed, and what assertions the system refuses to make.
                    </p>
                </div>

                <div className="limit-list">
                    {/* 1. Core Corpus Scope */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-partially_answerable">Corpus Scope</span>
                                <h2>Invariant Core: 20,210 Canonical Mantras Only</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Why</h3>
                                <p>
                                    VedAnvaya models exactly four canonical Samhita corpora:
                                    Rigveda Śākala (10,552 mantras), Samaveda Kauthuma ārcika (1,844 verses),
                                    White Yajurveda Vājasaneyi Mādhyandina (1,975 mantras), and Atharvaveda Śaunaka (5,839 mantras).
                                </p>
                            </section>
                            <section>
                                <h3>What is excluded</h3>
                                <p>
                                    All Brāhmaṇa, Āraṇyaka, and Upaniṣad layers are outside release scope. Excluded recensions include
                                    Atharvaveda Paippalāda, the entire Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala),
                                    and Rigveda Āśvalāyana. Khila additions are excluded from core canonical counts.
                                </p>
                            </section>
                        </div>
                    </article>

                    {/* 2. Translation Coverage & Provenance */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-partially_answerable">Translations</span>
                                <h2>Strictly Typed Coverage (18,145 Dedicated English, 1,719 Uncovered)</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Translation Typology</h3>
                                <p>
                                    Coverage is divided into: 18,145 dedicated verse English translations, 128 multi-verse range translations,
                                    194 reused parallel renderings, 24 non-English scholarly formula transcriptions (Whitney), and 1,719 uncovered verses.
                                </p>
                            </section>
                            <section>
                                <h3>Samaveda Translation Reality</h3>
                                <p>
                                    The Samaveda holds <strong>0 own dedicated English translations</strong>. 173 verses are covered via
                                    verified reused Rigvedic English renderings (Griffith parallel alignment with source-text identity verified).
                                    1,671 verses remain uncovered. The system distinguishes &ldquo;no own dedicated translation&rdquo; from &ldquo;no translation available&rdquo;.
                                </p>
                            </section>
                        </div>
                    </article>

                    {/* 3. Audio Catalogue & Review Gates */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-not_answerable">Recitation Audio</span>
                                <h2>16,834 Released Records · 1,001 Queued Withheld Behind QA Gate</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Released Records</h3>
                                <p>
                                    Public recitation coverage holds 16,834 catalogue records: Rigveda 10,402; Atharvaveda 4,680; White Yajurveda 1,752; Samaveda 0.
                                    The owner audible sample (20/20 reviewed) passed and was accepted.
                                </p>
                            </section>
                            <section>
                                <h3>Audible QA Gate (GAP-AUDIO-002..004)</h3>
                                <p>
                                    1,001 of 1,021 queued recordings remain not individually heard and stay withheld behind the manual audible-review gate;
                                    zero mass promotion occurred. Unaudited audio is never served.
                                </p>
                            </section>
                        </div>
                    </article>

                    {/* 4. Samaveda Musical Notation & Gāna Corpus */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-partially_answerable">Samaveda Music</span>
                                <h2>1,136 Validated Notation Witnesses · Gāna Corpus Outside Scope</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Validated Notation Witnesses</h3>
                                <p>
                                    1,136 of 1,844 Samavedic verses carry validated source-explicit notation witnesses (PARALLEL_WITNESS / PARALLEL_TEXT svara marks,
                                    with Gates A, B, and C all passed). 708 verses remain withheld pending textual alignment.
                                </p>
                            </section>
                            <section>
                                <h3>A Mark is Not a Melody</h3>
                                <p>
                                    The Gāna song collections (Grāmageyagāna, Āraṇyagāna, Ūhagāna, Ūhyagāna) and MUSICALIZED_AS graph edges remain outside release scope.
                                    The Kauthuma decipherment authority is not held in this build; tone marks are stored as codepoints and never extrapolated into sung musical pitches.
                                </p>
                            </section>
                        </div>
                    </article>

                    {/* 5. Attribution & Normalisation Boundaries */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-partially_answerable">Attribution</span>
                                <h2>Structural Deity Entities & Normalisation Rules</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Devata & Rishi Entities</h3>
                                <p>
                                    Deity mentions are classified into 6 structural types (INDIVIDUAL, ABSTRACT, PAIR, GROUP, HUMAN, PATRON_PRAISE, UNSPECIFIED).
                                    Ascription in the Anukramaṇī index is kept strictly distinct from naming in the verse text.
                                </p>
                            </section>
                            <section>
                                <h3>Normalisation Rule</h3>
                                <p>
                                    Surface text is preserved and normalized to Unicode NFC. Accents (svara) are stripped only for phonetic search indexing
                                    and never mutated or discarded in primary text representations.
                                </p>
                            </section>
                        </div>
                    </article>

                    {/* 6. Ask 60/60 Benchmark & Bounded Synthesis */}
                    <article className="limit-card">
                        <header>
                            <div>
                                <span className="verdict verdict-partially_answerable">Ask System</span>
                                <h2>Ask Formal 60 Benchmark: 60/60 Acceptable Outcomes</h2>
                            </div>
                            <KnowledgeStatus status="SUPPORTED" compact />
                        </header>
                        <div className="limit-body">
                            <section>
                                <h3>Verification Benchmark</h3>
                                <p>
                                    The Ask natural-language engine achieved 60/60 acceptable results on its formal benchmark:
                                    39 supported correct, 4 partial correct, 17 insufficient evidence refused, 0 misleading, and 0 hallucinated.
                                </p>
                            </section>
                            <section>
                                <h3>Honest Refusal Principle</h3>
                                <p>
                                    The language model is strictly grounded on the graph evidence packet. If the graph holds no evidence or the question asks
                                    about an unbuilt dimension, the system refuses honestly instead of fabricating answers.
                                </p>
                            </section>
                        </div>
                    </article>
                </div>
            </section>

            <div>
                <h2 style={{ fontFamily: "var(--va-font-display)", fontSize: "var(--va-text-2xl)", marginBottom: "var(--va-space-xs)" }}>
                    Probed Question-Level Limits
                </h2>
                <p style={{ color: "var(--va-text-secondary)", fontSize: "var(--va-text-sm)", maxWidth: "var(--va-measure)", marginBottom: "var(--va-space-md)" }}>
                    {published} of the {total} questions the benchmark grades unanswerable are catalogued below, each with a live probe and a safer alternative question.
                </p>
            </div>

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
