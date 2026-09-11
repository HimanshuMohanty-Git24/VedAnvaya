import { ArrowRight, ArrowsLeftRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import {
    encoded,
    load,
    type CrossVeda,
    type FormulaDiffusion,
    type SearchResponse,
} from "@/lib/api";
import { humanizePredicate, statusCopy, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "Across the four Vedas",
    description:
        "Exact reuse, near parallels, variants, formula families and shared vocabulary, kept as separate kinds of connection.",
};

/** Reuse rows carry citations. Resolve each to a canonical key so it is clickable. */
async function resolveCitation(citation: string) {
    const result = await load<SearchResponse>(
        `/search?q=${encodeURIComponent(citation)}&type=PASSAGE&limit=1`,
    );
    if (!result.ok) return null;
    const hit = result.data.items?.[0];
    return hit?.match_type === "EXACT_CITATION" ? hit.stable_id : null;
}

export default async function ConnectionsPage() {
    const [matrixResult, diffusionResult] = await Promise.all([
        load<CrossVeda>("/insights/cross-veda"),
        load<FormulaDiffusion>("/insights/formula-diffusion?limit=8"),
    ]);
    if (!matrixResult.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={matrixResult.status} message={matrixResult.message} />
            </div>
        );
    }
    const matrix = matrixResult.data;
    const classes = matrix.relationship_classes ?? [];
    const diffusion = diffusionResult.ok ? diffusionResult.data : null;
    const witnesses = (diffusion?.reuse_witnesses ?? []).slice(0, 8);
    const resolvedKeys = await Promise.all(
        witnesses.map((row) => resolveCitation(row.samaveda ?? "")),
    );

    return (
        <div className="shell page">
            <PageHeading
                title="Across the four Vedas"
                description="Exact reuse, near parallels, variants, formula families and shared vocabulary are different kinds of connection. They are never collapsed into one similarity score."
            />

            <section className="matrix-section">
                <div className="section-heading small">
                    <h2>What connects each pair</h2>
                    <p>
                        A number is a measured edge count. Every other cell states its reason, and
                        no cell is displayed as zero unless zero was measured.
                    </p>
                </div>
                <div className="matrix-wrap">
                    <table className="connection-matrix">
                        <caption className="sr-only">
                            Relationship classes by Veda pair, with the status of every cell.
                        </caption>
                        <thead>
                            <tr>
                                <th scope="col">Pair</th>
                                {classes.map((item) => (
                                    <th scope="col" key={item.relationship_class}>
                                        {titleCase(humanizePredicate(item.relationship_class))}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {matrix.pairs?.map((pair) => (
                                <tr key={pair.pair}>
                                    <th scope="row">{pair.pair}</th>
                                    {classes.map((relation) => {
                                        const cell = (pair.cells ?? []).find(
                                            (item) =>
                                                item.relationship_class ===
                                                relation.relationship_class,
                                        );
                                        const copy = statusCopy(cell?.status);
                                        return (
                                            <td
                                                key={relation.relationship_class}
                                                className={`cell tone-${copy.tone}`}
                                                title={cell?.note ?? copy.description}
                                            >
                                                {cell?.edges == null ? (
                                                    <span className="cell-reason">
                                                        {copy.label}
                                                    </span>
                                                ) : (
                                                    <strong>{cell.edges.toLocaleString()}</strong>
                                                )}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div className="connections-explainer">
                    <KnowledgeStatus status={matrix.data_status} />
                    <p>
                        Directed reuse edges exist for the Rigveda and Samaveda pair only. That is a
                        property of what was built, not a finding that the other pairs share
                        nothing.
                    </p>
                </div>
            </section>

            <section className="reuse-section">
                <div className="section-heading small">
                    <h2>Rigveda carried into Samaveda</h2>
                    <p>
                        Each row is one measured reuse witness. Open a pair to read both texts side
                        by side with the surface that matched.
                    </p>
                </div>
                {witnesses.length ? (
                    <div className="reuse-list">
                        {witnesses.map((row, index) => {
                            const key = resolvedKeys[index];
                            const body = (
                                <>
                                    <div>
                                        <span>Rigveda</span>
                                        <strong>{row.rigveda}</strong>
                                    </div>
                                    <ArrowsLeftRight size={19} aria-hidden="true" />
                                    <div>
                                        <span>Samaveda</span>
                                        <strong>{row.samaveda}</strong>
                                    </div>
                                    <small>
                                        {row.match_level
                                            ? titleCase(humanizePredicate(row.match_level))
                                            : "match level not recorded"}
                                    </small>
                                </>
                            );
                            return key ? (
                                <Link
                                    className="reuse-row"
                                    key={`${row.rigveda}-${row.samaveda}`}
                                    href={`/reuse/${encoded(key)}`}
                                >
                                    {body}
                                    <ArrowRight size={16} aria-hidden="true" />
                                </Link>
                            ) : (
                                <div
                                    className="reuse-row is-static"
                                    key={`${row.rigveda}-${row.samaveda}`}
                                >
                                    {body}
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <KnowledgeStatus status="NOT_BUILT" />
                )}
                <Link className="text-link" href="/formulas">
                    Follow shared wording through the formula families
                    <ArrowRight size={16} aria-hidden="true" />
                </Link>
            </section>

            {diffusion?.span_census?.length ? (
                <section className="span-census">
                    <div className="section-heading small">
                        <h2>How far shared wording travels</h2>
                        <p>
                            A formula family is a representative wording plus everything that
                            contains or closely resembles it. Its span measures diction, not a
                            demonstrated line of transmission.
                        </p>
                    </div>
                    <div className="census-grid">
                        {diffusion.span_census.map((row) => (
                            <article key={row.vedas_reached}>
                                <strong>{row.families?.toLocaleString()}</strong>
                                <span>
                                    families reach {row.vedas_reached}{" "}
                                    {row.vedas_reached === 1 ? "collection" : "collections"}
                                </span>
                                <small>{row.occurrences?.toLocaleString()} occurrences</small>
                            </article>
                        ))}
                    </div>
                </section>
            ) : null}

            <Caveat title="Samaveda scope" tone="boundary">
                Kauthuma arcika only. The gana collections and complete musical information are not
                held, so this view neither presents nor infers melody.
            </Caveat>
            <CaveatList caveats={matrix.caveats} title="How the matrix was measured" />
        </div>
    );
}
