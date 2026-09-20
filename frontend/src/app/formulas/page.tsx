import { LoadFailure } from "@/components/empty-state";
import { Reach } from "@/components/reach";
import { Register, RegisterOpening, type RegisterRow } from "@/components/register";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type EntityListResponse, type FormulaDiffusion } from "@/lib/api";

export const metadata = {
    title: "Formula families",
    description:
        "Shared wording grouped into cores, expansions and variants across the four collections.",
};

/**
 * The formula index.
 *
 * Three changes, and the reason for each is a fact about this layer rather than a
 * preference about layout.
 *
 * **No measure bars.** Every family in `/entities/formula_family` carries
 * `passage_count: null`, and the service says why: the mention layer's measured recall is
 * 0.8857, so a null is a lower bound and never a zero. Weighting a register by a figure that
 * does not exist would be inventing hierarchy, so the rows are level and each one prints
 * what kind of absence its figure is.
 *
 * **The widest families come first, with their reach.** `insights/formula-diffusion` does
 * carry per-collection occurrence counts for the 25 widest, and `vedas_reported` says which
 * collections were read - so those rows can draw a properly typed four-collection register
 * where a missing collection means "read, and not found" and not merely "blank".
 *
 * **The census is a ruled table, not four figures in boxes.** It is a distribution, and the
 * one-collection row is its baseline rather than a small number to be embarrassed about.
 */
export default async function FormulasPage() {
    const [listResult, diffusionResult] = await Promise.all([
        load<EntityListResponse>("/entities/formula_family?limit=60"),
        load<FormulaDiffusion>("/insights/formula-diffusion?limit=8"),
    ]);
    if (!listResult.ok) {
        return (
            <div className="va-page">
                <LoadFailure status={listResult.status} message={listResult.message} />
            </div>
        );
    }
    const data = listResult.data;
    const diffusion = diffusionResult.ok ? diffusionResult.data : null;
    const census = diffusion?.span_census ?? [];
    const widest = diffusion?.widest_families ?? [];
    /*
     * Which collections the diffusion query read. Taken from the response, never assumed:
     * the reach register's whole value is that a mark outside this list reads as "not
     * measured" rather than as "not there".
     */
    const measured = diffusion?.vedas_reported ?? diffusion?.coverage?.vedas_in_scope ?? [];
    const totalFamilies = diffusion?.coverage?.measured?.families ?? data.pagination?.total ?? null;
    const reachingAll = diffusion?.coverage?.measured?.reaching_all_four ?? null;
    const censusCeiling = Math.max(0, ...census.map((row) => row.families ?? 0));

    const rows: RegisterRow[] = (data.items ?? []).map((item) => ({
        key: item.id,
        href: `/formula-families/${encoded(item.id)}`,
        name: item.display_label,
        script: "IAST",
        figure: item.passage_count,
        unit: item.passage_count === 1 ? "passage" : "passages",
        /*
         * The typed absence, in the service's own terms. Not "0", not a dash: the mention
         * layer recalls 88.57% of what it should, so a null here is a lower bound.
         */
        absent: "passage count is a lower bound, not established",
    }));

    return (
        <div className="va-page">
            <RegisterOpening
                title="Formula families"
                lede="A family is one representative wording plus everything that contains or closely resembles it. Following a family across collections shows shared diction, and diction is not by itself a demonstrated line of transmission."
                standing={[
                    ...(totalFamilies != null
                        ? [
                              {
                                  label: "Families",
                                  value: totalFamilies.toLocaleString("en-GB"),
                              },
                          ]
                        : []),
                    ...(reachingAll != null
                        ? [
                              {
                                  label: "Reach all four",
                                  value: reachingAll.toLocaleString("en-GB"),
                              },
                          ]
                        : []),
                    { label: "Passage counts", value: "not established", absent: true },
                ]}
            />

            {census.length > 0 && (
                <section aria-labelledby="va-formula-census" className="va-block">
                    <h2 className="va-block-heading" id="va-formula-census">
                        How far a family travels
                    </h2>
                    <p className="va-block-note">
                        Every family, by the number of collections its wording reaches. The
                        single-collection row is the baseline the cross-collection ones should be
                        read against, not a separate finding.
                    </p>
                    <table className="va-block-table">
                        <caption className="sr-only">
                            Formula families by the number of collections reached, with the number
                            of family memberships and total occurrences of each.
                        </caption>
                        <thead>
                            <tr>
                                <th scope="col">Collections reached</th>
                                <th className="is-num" scope="col">
                                    Families
                                </th>
                                <th className="is-bar" scope="col">
                                    <span className="sr-only">Share</span>
                                </th>
                                <th className="is-num" scope="col">
                                    Occurrences
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {census.map((row) => (
                                <tr key={row.vedas_reached}>
                                    <th scope="row">
                                        {row.vedas_reached}
                                        {row.cross_veda ? "" : " (within one collection)"}
                                    </th>
                                    <td className="is-num">
                                        {row.families?.toLocaleString("en-GB")}
                                    </td>
                                    <td className="is-bar">
                                        <span aria-hidden="true" className="va-block-track">
                                            <span
                                                className="va-resolve"
                                                style={
                                                    {
                                                        "--va-resolve-to": `${Math.round(
                                                            ((row.families ?? 0) /
                                                                Math.max(1, censusCeiling)) *
                                                                100,
                                                        )}%`,
                                                    } as React.CSSProperties
                                                }
                                            />
                                        </span>
                                    </td>
                                    <td className="is-num">
                                        {row.occurrences?.toLocaleString("en-GB")}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </section>
            )}

            {widest.length > 0 && measured.length > 0 && (
                <section aria-labelledby="va-formula-widest" className="va-block">
                    <h2 className="va-block-heading" id="va-formula-widest">
                        The widest families, and where each one lands
                    </h2>
                    <p className="va-block-note">
                        A filled mark is an occurrence in that collection. A struck mark is a
                        collection that was read and does not carry the wording. The Rigvedic
                        figure is usually the largest, which is partly its size and partly that
                        the Samaveda and much of the Yajurveda are drawn from it.
                    </p>
                    <ul className="va-register">
                        {widest.map((family) => (
                            <li key={family.representative}>
                                <div className="va-register-row is-static">
                                    <span className="va-register-lead">
                                        <span
                                            className="va-register-name va-sanskrit-inline"
                                            lang="sa"
                                        >
                                            {family.representative}
                                        </span>
                                    </span>
                                    <span className="va-register-gloss-wrap">
                                        <span className="va-register-note">
                                            {family.members} members: {family.core} core,{" "}
                                            {family.expansions} expansions, {family.variants}{" "}
                                            variants
                                        </span>
                                    </span>
                                    <span className="va-register-meta">
                                        <Reach
                                            counts={family.occurrences_per_veda}
                                            measured={measured}
                                            present={Object.entries(
                                                family.occurrences_per_veda ?? {},
                                            )
                                                .filter(([, count]) => (count ?? 0) > 0)
                                                .map(([veda]) => veda)}
                                        />
                                        <span className="va-register-unit">
                                            {family.occurrences?.toLocaleString("en-GB")} in all
                                        </span>
                                    </span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section aria-labelledby="va-formula-index" className="va-block">
                <h2 className="va-block-heading" id="va-formula-index">
                    Every family
                </h2>
                <Caveat title="Reading a family">
                    Core forms are the shared wording itself. Expansions contain it inside a longer
                    phrase. Variants differ from it slightly. The three are counted separately.
                </Caveat>
                <Register aria-label="Formula families" rows={rows} />
            </section>

            <CaveatList caveats={data.caveats} title="How families were built" />
        </div>
    );
}
