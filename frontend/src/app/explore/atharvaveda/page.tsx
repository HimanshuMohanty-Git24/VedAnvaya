import { FirstAidKit, HouseLine, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { LoadFailure } from "@/components/empty-state";
import { Register, RegisterOpening, type RegisterRow } from "@/components/register";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type AvConcerns } from "@/lib/api";
import { conditionLabel, conditionNote, humanizePredicate, normalizeType } from "@/lib/knowledge";

export const metadata = {
    title: "Human concerns in the Atharvaveda",
    description:
        "Healing, protection, household life and prosperity, with afflictions kept distinct from the threats the texts guard against.",
};

/**
 * The Atharvavedic lens.
 *
 * Four card grids became four registers, and one repetition went with them. Every card in
 * the afflictions grid carried an AFFLICTION badge under a heading that said "Afflictions";
 * the badge stays only in the section where the kind genuinely varies, which is the one
 * listing what the texts address. That is the rule for the whole phase: a field label is
 * data vocabulary and stays, unless every row in the block carries the same value, in which
 * case it is the heading repeated forty times.
 *
 * The counts drive the hierarchy. Each register draws a share rule against the largest
 * figure in its own block, so the shape of the distribution is readable without any row
 * being made bigger than another.
 */
export default async function AtharvavedaPage() {
    const result = await load<AvConcerns>("/insights/atharvaveda/concerns?limit=20");
    if (!result.ok) {
        return (
            <div className="va-page">
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
    const social = data.social_rites ?? [];
    const concerns = (data.concerns ?? []).filter((row) => row.entity_key);

    const top = (rows: Array<{ total_mantras?: number | null }>) =>
        Math.max(0, ...rows.map((row) => row.total_mantras ?? 0));

    const conditionRows = (
        rows: Array<{
            label?: string | null;
            kind?: string | null;
            entity_key?: string | null;
            total_mantras?: number | null;
            vedas_reached?: number | null;
        }>,
        hrefType: string,
        showKind: boolean,
    ): RegisterRow[] =>
        rows
            .filter((row) => row.entity_key)
            .map((row) => ({
                key: row.entity_key as string,
                href: `/entities/${hrefType}/${encoded(row.entity_key as string)}`,
                name: row.label ?? (row.entity_key as string),
                kind: showKind ? conditionLabel(row.kind) : null,
                note: `Found in ${row.vedas_reached ?? 1} ${
                    row.vedas_reached === 1 ? "collection" : "collections"
                }`,
                figure: row.total_mantras,
                unit: row.total_mantras === 1 ? "matching mantra" : "matching mantras",
                absent: "no registered form matched",
            }));

    return (
        <div className="va-page">
            <RegisterOpening
                title="Human concerns in the Atharvaveda"
                lede="Healing, protection, household life and prosperity. What the texts suffer, what they guard against, and what they name as a cause are three different things and stay apart here."
                standing={[
                    { label: "Afflictions", value: afflictions.length.toLocaleString("en-GB") },
                    {
                        label: "Addressed targets",
                        value: treatment.length.toLocaleString("en-GB"),
                    },
                    { label: "Recension held", value: "Śaunaka" },
                    { label: "Every figure is", value: "a lexical minimum", absent: true },
                ]}
            />

            <section aria-labelledby="va-av-afflictions" className="va-block">
                <hr className="va-rule-drawn" />
                <div className="va-lens-head">
                    <FirstAidKit size={22} aria-hidden="true" />
                    <div>
                        <h2 className="va-block-heading" id="va-av-afflictions">
                            Afflictions
                        </h2>
                        <p className="va-block-note">
                            Conditions suffered in the body or the household. These counts are
                            Sanskrit lexical-match minima, not diagnoses and not exhaustive topic
                            counts.
                        </p>
                    </div>
                </div>
                <Register
                    aria-label="Afflictions"
                    ceiling={top(afflictions)}
                    columns={{ name: "Affliction", figure: "Matching mantras" }}
                    rows={conditionRows(afflictions, "condition", false)}
                />
            </section>

            <section aria-labelledby="va-av-addressed" className="va-block">
                <hr className="va-rule-drawn" />
                <div className="va-lens-head">
                    <ShieldCheck size={22} aria-hidden="true" />
                    <div>
                        <h2 className="va-block-heading" id="va-av-addressed">
                            What the texts address
                        </h2>
                        <p className="va-block-note">
                            Each row is one relationship predicate over one target. The predicates
                            differ in how they were established and are never summed, so the kind
                            travels with every row here.
                        </p>
                    </div>
                </div>
                <ul className="va-register">
                    {treatment.map((row, index) => (
                        <li key={`${row.target}-${row.predicate}-${index}`}>
                            <div className="va-register-row is-static">
                                <span className="va-register-lead">
                                    <span className="va-register-name">{row.target}</span>
                                    <span className="va-register-kind">
                                        {row.condition_kind
                                            ? conditionLabel(row.condition_kind)
                                            : row.kind}
                                    </span>
                                </span>
                                <span className="va-register-gloss-wrap">
                                    <span className="va-register-note">
                                        Established as <em>{humanizePredicate(row.predicate)}</em>
                                    </span>
                                </span>
                                <span className="va-register-meta">
                                    <span className="va-register-figure">
                                        {row.passages?.toLocaleString("en-GB")}
                                    </span>
                                    <span className="va-register-unit">passages</span>
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </section>

            {threats.length > 0 && (
                <section aria-labelledby="va-av-threats" className="va-block">
                    <hr className="va-rule-drawn" />
                    <div className="va-lens-head">
                        <ShieldCheck size={22} aria-hidden="true" />
                        <div>
                            <h2 className="va-block-heading" id="va-av-threats">
                                Threats guarded against
                            </h2>
                            <p className="va-block-note">{conditionNote("THREAT")}</p>
                        </div>
                    </div>
                    <ul className="va-register">
                        {threats.map((row, index) => (
                            <li key={`${row.target}-${row.predicate}-${index}`}>
                                <div className="va-register-row is-static">
                                    <span className="va-register-lead">
                                        <span className="va-register-name">{row.target}</span>
                                    </span>
                                    <span className="va-register-gloss-wrap">
                                        <span className="va-register-note">
                                            Established as{" "}
                                            <em>{humanizePredicate(row.predicate)}</em>
                                        </span>
                                    </span>
                                    <span className="va-register-meta">
                                        <span className="va-register-figure">
                                            {row.passages?.toLocaleString("en-GB")}
                                        </span>
                                        <span className="va-register-unit">passages</span>
                                    </span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section aria-labelledby="va-av-social" className="va-block">
                <hr className="va-rule-drawn" />
                <div className="va-lens-head">
                    <HouseLine size={22} aria-hidden="true" />
                    <div>
                        <h2 className="va-block-heading" id="va-av-social">
                            Household and social life
                        </h2>
                        <p className="va-block-note">
                            Marriage, house building, childbirth and the rites around them.
                        </p>
                    </div>
                </div>
                <Register
                    aria-label="Household and social rites"
                    ceiling={top(social)}
                    columns={{ name: "Rite", figure: "Matching mantras" }}
                    rows={conditionRows(social, "social_rite", false)}
                />
            </section>

            {concerns.length > 0 && (
                <section aria-labelledby="va-av-concerns" className="va-block">
                    <hr className="va-rule-drawn" />
                    <h2 className="va-block-heading" id="va-av-concerns">
                        Wider human concerns
                    </h2>
                    <Register
                        aria-label="Wider human concerns"
                        ceiling={top(concerns)}
                        columns={{ name: "Concern", figure: "Lexical matches" }}
                        rows={concerns.map((row) => ({
                            key: row.entity_key as string,
                            href: `/entities/human_concern/${encoded(row.entity_key as string)}`,
                            name: row.label ?? (row.entity_key as string),
                            figure: row.total_mantras,
                            unit: "lexical matches",
                            absent: "no registered form matched",
                        }))}
                    />
                </section>
            )}

            <Caveat title="Atharvaveda scope" tone="boundary">
                The Śaunaka recension is held as a working private corpus. The Paippalāda
                recension is a substantially different collection and is not present, so an
                Atharvavedic absence measured here is an absence from Śaunaka only.
            </Caveat>
            <CaveatList caveats={data.caveats} title="How these counts were measured" limit={6} />
        </div>
    );
}
