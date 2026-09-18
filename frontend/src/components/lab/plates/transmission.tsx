import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { Figure } from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import {
    encoded,
    load,
    type CrossVeda,
    type FormulaDiffusion,
    type SearchResponse,
} from "@/lib/api";
import { count, PLATES_BY_SLUG } from "@/lib/lab";

/**
 * What the collections share.
 *
 * Two figures, and the order matters. First the whole matrix, so the reader sees that eight
 * different things get called "similarity" and that most of the grid is not a measurement at
 * all. Then one pair, drawn as the pairing it is: a Samavedic verse and the Rigvedic verse it
 * reuses, both clickable, in the order the endpoint returned them.
 *
 * The matrix is the part worth defending. Twelve of its 48 cells were never built and five
 * were never established for that pair, and a grid that rendered those as `0` would state
 * that the Atharvaveda reuses no Rigvedic text while the same graph holds 551 exact parallels
 * between them. So every cell carries its own status and prints a mark that says which kind
 * of non-number it is.
 */

const plate = PLATES_BY_SLUG.transmission;

/** Column headings. Short enough for a 6-by-8 grid, and never the graph's own edge names. */
const CLASS_LABEL: Record<string, { short: string; long: string }> = {
    EXACT_PARALLEL_OF: {
        short: "Exact parallel",
        long: "The same verse, word for word, in two collections.",
    },
    NEAR_PARALLEL_OF: {
        short: "Near parallel",
        long: "Closely similar wording, short of identity.",
    },
    REUSES_TEXT_FROM: {
        short: "Directed reuse",
        long: "One verse carries the other's wording, and the direction is recorded.",
    },
    VARIANT_OF: {
        short: "Variant",
        long: "The same verse with edition-level differences.",
    },
    SHARES_ENTITY_VOCABULARY_WITH: {
        short: "Shared vocabulary",
        long: "Both verses name the same registered entities. Not shared wording.",
    },
    PARALLEL_TO: {
        short: "Parallel, internal",
        long: "A parallel between two verses inside one collection, which by definition joins no pair.",
    },
    SEMANTIC_RESEMBLANCE: {
        short: "Semantic resemblance",
        long: "Resemblance by meaning rather than by letters. No such measure exists in this graph.",
    },
    SEMANTIC_ASSERTION: {
        short: "Semantic assertion",
        // Said twice wrongly before: "model-extracted" of a layer that is mostly rule-derived
        // (2,459 of 35,131 are model extractions), and "every one of them is Rigvedic" of a
        // layer that reaches all four collections. The reason it joins no pair is structural
        // and has nothing to do with how much of it was built.
        long: "A statement about a single verse, so it relates no two collections. The layer reaches all four.",
    },
};

/**
 * What a cell prints when it is not a count.
 *
 * Four different marks for four different reasons, because collapsing them is the exact
 * misreading this figure exists to prevent. The mark is text, not colour, so it survives
 * greyscale and a screen reader.
 */
const CELL_MARK: Record<string, { mark: string; means: string }> = {
    MEASURED_ZERO: { mark: "0", means: "Measured, and zero." },
    NOT_ESTABLISHED_FOR_PAIR: {
        mark: "·",
        means: "The class exists and was never established for this pair of collections.",
    },
    CLASS_NOT_CROSS_VEDA: {
        mark: "—",
        means: "This class joins verses inside one collection, so it cannot reach a pair.",
    },
    NOT_BUILT: { mark: "∅", means: "The layer does not exist anywhere in this graph." },
};

/** How many Rigveda-to-Samaveda witnesses the flow shows. */
const WITNESSES = 14;

/** Resolves a citation to a canonical key so both ends of a reuse pair are clickable. */
async function resolveCitation(citation: string) {
    if (!citation) return null;
    const result = await load<SearchResponse>(
        `/search?q=${encodeURIComponent(citation)}&type=PASSAGE&limit=1`,
    );
    if (!result.ok) return null;
    const hit = result.data.items?.[0];
    return hit?.match_type === "EXACT_CITATION" ? (hit.stable_id ?? null) : null;
}

export async function TransmissionPlate() {
    const [matrixResult, diffusionResult] = await Promise.all([
        load<CrossVeda>("/insights/cross-veda"),
        load<FormulaDiffusion>(`/insights/formula-diffusion?limit=${WITNESSES}`),
    ]);
    if (!matrixResult.ok) {
        return <LoadFailure message={matrixResult.message} status={matrixResult.status} />;
    }

    const matrix = matrixResult.data;
    const classes = matrix.relationship_classes ?? [];
    const pairs = matrix.pairs ?? [];
    const order = classes.map((row) => row.relationship_class);
    const shape = matrix.shape;

    const witnesses = (
        diffusionResult.ok ? (diffusionResult.data.reuse_witnesses ?? []) : []
    ).slice(0, WITNESSES);
    const resolved = await Promise.all(
        witnesses.map(async (row) => ({
            row,
            samaveda: await resolveCitation(row.samaveda ?? ""),
            rigveda: await resolveCitation(row.rigveda ?? ""),
        })),
    );

    const directed = classes.find((row) => row.relationship_class === "REUSES_TEXT_FROM");
    /* The takeaway's arithmetic, read off the same response the matrix is drawn from. */
    const widest = [...classes]
        .filter((row) => (row.cross_veda_edges ?? 0) > 0)
        .sort((a, b) => (b.cross_veda_edges ?? 0) - (a.cross_veda_edges ?? 0))[0];
    const unbuilt = classes.filter((row) => row.population_status === "NOT_BUILT");
    const measuredCells = shape?.cells_by_status?.MEASURED ?? 0;
    const usedMarks = new Set(
        pairs.flatMap((pair) => (pair.cells ?? []).map((cell) => cell.status)),
    );

    return (
        <>
            <PlateHeader
                lede="Eight different relationships between two verses get called 'similar' in ordinary speech, and they are not degrees of one measure. One of them records a direction — this verse carries that one's wording — and it was established for a single pair of collections. Everything else on this plate is context for that fact."
                plate={plate}
            />

            <PlateFigure
                description={`Six corpus pairs against eight relationship classes. All ${count(shape?.cells_returned ?? 48)} cells are shown, including the ones that are not numbers, and each of those prints a mark that says why.`}
                footnote={
                    <>
                        A cell is read as: this many edges of this class join these two collections.
                        Directed classes are counted once per edge regardless of which end is in
                        which collection.
                    </>
                }
                id="matrix"
                title="Every pair, against every kind of connection"
            >
                <div className="va-matrix-scroll" tabIndex={0}>
                    <table className="va-matrix">
                        <caption className="sr-only">
                            Cross-corpus relationship edges: six corpus pairs by eight relationship
                            classes.
                        </caption>
                        <thead>
                            <tr>
                                <th scope="col">Pair</th>
                                {order.map((name) => (
                                    <th key={name} scope="col">
                                        <abbr title={CLASS_LABEL[name]?.long ?? name}>
                                            {CLASS_LABEL[name]?.short ?? name}
                                        </abbr>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {pairs.map((pair) => {
                                const cells = new Map(
                                    (pair.cells ?? []).map((cell) => [
                                        cell.relationship_class,
                                        cell,
                                    ]),
                                );
                                return (
                                    <tr key={pair.pair}>
                                        <th scope="row">{pair.pair}</th>
                                        {order.map((name) => {
                                            const cell = cells.get(name);
                                            const status = cell?.status ?? "NOT_BUILT";
                                            const mark = CELL_MARK[status];
                                            return (
                                                <td data-cell={status} key={name}>
                                                    {status === "MEASURED" ? (
                                                        count(cell?.edges)
                                                    ) : (
                                                        <abbr
                                                            title={`${mark?.means ?? status} ${cell?.note ?? ""}`.trim()}
                                                        >
                                                            {mark?.mark ?? "∅"}
                                                        </abbr>
                                                    )}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                <ul className="va-matrix-key">
                    {Object.entries(CELL_MARK)
                        .filter(([status]) => usedMarks.has(status as never))
                        .map(([status, mark]) => (
                            <li key={status}>
                                <b>{mark.mark}</b> {mark.means}
                            </li>
                        ))}
                    <li>
                        <b>{count(shape?.cells_by_status?.MEASURED ?? 0)}</b> of{" "}
                        {count(shape?.cells_returned ?? 48)} cells carry a measured count.
                    </li>
                </ul>
            </PlateFigure>

            <PlateFigure
                description={`The Rigveda-to-Samaveda pair is the only one for which direction was established. ${count(directed?.cross_veda_edges)} directed reuse edges exist and they all join this pair; below are ${resolved.length} of them, as the two verses they connect.`}
                footnote={
                    <>
                        The order of these rows is the order the endpoint returned, which is the
                        Samavedic citation order. It carries no ranking: the first row is not the
                        strongest example of anything.
                    </>
                }
                id="flow"
                title="Rigveda to Samaveda, verse by verse"
            >
                <div className="va-flow-head">
                    <Figure
                        note={
                            <>
                                All of them on one corpus pair. The other five pairs have no
                                directed reuse, which means nobody established one.
                            </>
                        }
                        unit="directed reuse edges"
                        value={count(directed?.cross_veda_edges) ?? "—"}
                    />
                </div>

                {resolved.length ? (
                    <ul className="va-flow">
                        <li className="va-flow-header">
                            <span className="va-flow-source">Rigveda, the source</span>
                            <span className="va-flow-link">reused by</span>
                            <span>Samaveda, the reuse</span>
                        </li>
                        {resolved.map(({ row, samaveda, rigveda }) => (
                            <li key={`${row.samaveda}-${row.rigveda}`}>
                                <span className="va-flow-source">
                                    {rigveda ? (
                                        <Link href={`/passage/${encoded(rigveda)}`}>
                                            {row.rigveda}
                                        </Link>
                                    ) : (
                                        <span data-unresolved>{row.rigveda}</span>
                                    )}
                                </span>
                                <span className="va-flow-link">
                                    <span aria-hidden="true" className="va-flow-rule" />
                                    <span className="va-flow-kind">
                                        {row.match_level
                                            ? row.match_level.toLowerCase().replaceAll("_", " ")
                                            : "match level not recorded"}
                                    </span>
                                </span>
                                <span>
                                    {samaveda ? (
                                        <Link href={`/passage/${encoded(samaveda)}`}>
                                            {row.samaveda}
                                        </Link>
                                    ) : (
                                        <span data-unresolved>{row.samaveda}</span>
                                    )}
                                </span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="va-figure-note">
                        The reuse witnesses could not be read from the formula layer for this
                        request.
                    </p>
                )}
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        That the Samaveda reuses Rigvedic verses is not a discovery of this graph —
                        it is the oldest thing anyone says about the Samaveda. What the matrix adds
                        is the shape of the claim: the direction is recorded for this pair and not
                        for the other five, so a reader comparing pairs is comparing what was
                        measured rather than what happened.
                    </>
                }
                observation={
                    <>
                        {count(measuredCells)} of the {count(shape?.cells_returned ?? 48)} cells
                        carry a measured count. Directed reuse reaches{" "}
                        {directed?.pairs_reached?.length === 1
                            ? "one corpus pair"
                            : `${count(directed?.pairs_reached?.length)} corpus pairs`}
                        , while the class with the most edges —{" "}
                        {CLASS_LABEL[widest?.relationship_class ?? ""]?.short.toLowerCase() ??
                            widest?.relationship_class}{" "}
                        at {count(widest?.cross_veda_edges)} — reaches{" "}
                        {count(widest?.pairs_reached?.length)} of {count(pairs.length)}.{" "}
                        {count(unbuilt.length)} of the {count(classes.length)} classes are not built
                        at all and are shown anyway, because a row that vanished would be a row
                        nobody could ask about.
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/connections",
                        label: "The full connection index",
                        note: "Every class, with the witnesses and the formula families that mediate them",
                    },
                    {
                        href: "/visualizations/formulas",
                        label: "How a wording travels",
                        note: "The shared phrases underneath many of these parallels",
                    },
                    {
                        href: "/vedas/samaveda",
                        label: "Read the Samaveda",
                        note: "The collection on the right-hand side of every row above",
                    },
                    {
                        href: "/sources#method-relationships",
                        label: "What each relationship class means",
                        note: "Why none of these is a similarity score",
                    },
                ]}
            />
        </>
    );
}
