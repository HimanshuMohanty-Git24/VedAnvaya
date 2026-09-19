import Link from "next/link";
import { DerivedMatrix, byFamily } from "@/components/lab/derived-matrix";
import { LoadFailure } from "@/components/empty-state";
import { RegisterOpening } from "@/components/register";
import { Caveat, CaveatList, InterpretationFrame, KnowledgeStatus } from "@/components/status";
import { load, type Civilization } from "@/lib/api";
import { className, humanizePredicate, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "Evidence and interpretation",
    description:
        "Measured textual data, derived metrics and candidate interpretations, presented as three different kinds of knowledge.",
};

/**
 * Three kinds of knowledge, kept apart.
 *
 * The page's argument is that a count, a calculation and a reading are not the same object,
 * and the old layout undercut it: all three sat in the same bordered card, and the counts
 * sat in a second grid of smaller bordered cards inside that. Containment was doing no work,
 * and the one place it genuinely should - around an interpretation, which must never be
 * mistaken for a measurement - was drowned out by the two containers that did not.
 *
 * So the sections are now editorial blocks separated by a drawn rule, the counts are a ruled
 * table with a share bar that resolves to its measured value, and the interpretation frame
 * is the only box left on the page. Its dashed border now means something.
 *
 * The three kickers stay. They are the page's vocabulary rather than decoration: MEASURED
 * FROM THE TEXT, DERIVED MEASURE and INTERPRETATION are the distinction, and this is the one
 * route where the eyebrow is load-bearing.
 */
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
    const result = await load<Civilization>("/insights/civilization?limit=40");
    if (!result.ok) {
        return (
            <div className="va-page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    const sections = data.sections ?? [];

    return (
        <div className="va-page">
            <RegisterOpening
                title="Evidence and interpretation"
                lede="Three kinds of knowledge sit on this page, and they never look alike: what the texts say, what we computed from it, and what someone reads into it."
                /*
                 * How much of each kind is on the page, not a second copy of the three
                 * section kickers. The labels are the *things* - rows, measures, readings -
                 * so the strip is an inventory rather than a table of contents duplicating
                 * the headings twenty pixels below it.
                 */
                standing={[
                    {
                        label: "Measured rows",
                        value: String(
                            sections.reduce(
                                (total, section) => total + (section.data_rows?.length ?? 0),
                                0,
                            ),
                        ),
                    },
                    {
                        label: "Derived measures",
                        value: String(
                            sections.reduce(
                                (total, section) => total + (section.metric_rows?.length ?? 0),
                                0,
                            ),
                        ),
                    },
                    {
                        label: "Recorded readings",
                        value: String(
                            sections.reduce(
                                (total, section) => total + (section.claim_rows?.length ?? 0),
                                0,
                            ),
                        ),
                    },
                ]}
            />

            <Caveat title="Reading this page">
                A measured row is a count over passages. A derived measure is a calculation over
                those counts. An interpretation is a claim about what they mean, and it carries the
                observation that would falsify it.{" "}
                <Link className="text-link" href="/limits">
                    See what this product cannot answer
                </Link>
            </Caveat>

            {sections.map((section) => {
                const copy = SECTION_COPY[section.section_kind] ?? {
                    kicker: titleCase(humanizePredicate(section.section_kind)),
                    note: "",
                };
                const ceiling = Math.max(
                    1,
                    ...(section.data_rows ?? []).map((row) => row.passages ?? 0),
                );
                return (
                    <section
                        className="va-block va-insight"
                        key={section.section_kind}
                        data-knowledge-kind={section.section_kind.toLowerCase()}
                    >
                        {/* DRAW: the rule at the head of a section extends as the reader
                            arrives at it. See the motion law in `thread.css`. */}
                        <hr className="va-rule-drawn" />
                        <header className="va-insight-head">
                            <div>
                                <p className="va-insight-kicker">{copy.kicker}</p>
                                <h2>{section.title}</h2>
                                <p className="va-insight-lede">{section.what_this_is}</p>
                            </div>
                            <KnowledgeStatus status={section.data_status} compact />
                        </header>

                        {section.data_rows && (
                            <table className="va-block-table">
                                <caption className="sr-only">
                                    {section.title}: passages naming each kind of thing, and the
                                    collections each was counted over.
                                </caption>
                                <thead>
                                    <tr>
                                        <th scope="col">Kind of thing</th>
                                        <th className="is-num" scope="col">
                                            Passages
                                        </th>
                                        <th className="is-bar" scope="col">
                                            <span className="sr-only">Share of the largest</span>
                                        </th>
                                        <th scope="col">Counted over</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {section.data_rows.map((row) => (
                                        <tr key={row.kind}>
                                            <th scope="row">{className(row.kind)}</th>
                                            <td className="is-num">
                                                {row.passages.toLocaleString("en-GB")}
                                            </td>
                                            <td className="is-bar">
                                                <span
                                                    aria-hidden="true"
                                                    className="va-block-track"
                                                >
                                                    <span
                                                        className="va-resolve"
                                                        style={
                                                            {
                                                                "--va-resolve-to": `${Math.round(
                                                                    (row.passages / ceiling) * 100,
                                                                )}%`,
                                                            } as React.CSSProperties
                                                        }
                                                    />
                                                </span>
                                            </td>
                                            <td className="is-scope">{row.vedas?.join(", ")}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}

                        {section.metric_rows &&
                            /*
                             * A family of derived cells, drawn as the matrix it is.
                             *
                             * These arrived as sixteen identically-headed cards carrying
                             * identical boilerplate and one different number each. They are
                             * the cells of one measure - each row has a `subject` and a
                             * `dimension` - and a grid of cards was throwing that structure
                             * away and repeating the caption sixteen times. See
                             * `DerivedMatrix`, including why an empty cell says "not
                             * returned" rather than nothing.
                             */
                            byFamily(section.metric_rows).map((group) => (
                                <DerivedMatrix
                                    family={group.family}
                                    key={group.family}
                                    rows={group.rows}
                                />
                            ))}

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
