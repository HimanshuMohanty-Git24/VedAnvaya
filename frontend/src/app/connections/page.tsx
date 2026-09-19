import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import {
    cellState,
    connectionCopy,
    corpusName,
    listSentence,
    pairDash,
    pairName,
    plainNote,
} from "@/components/connections/connection-copy";
import { EvidenceMatrix } from "@/components/connections/evidence-matrix";
import { LoadFailure } from "@/components/empty-state";
import { CaveatList } from "@/components/status";
import {
    encoded,
    load,
    vedaNames,
    type CrossVeda,
    type FormulaDiffusion,
    type SearchResponse,
} from "@/lib/api";
import { matchLevelCopy, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "What the four Vedas share",
    description:
        "Exact parallels, near parallels, directed reuse, variant readings and shared vocabulary between the four Samhitas, measured pair by pair and never added into one score.",
};

type PairRow = NonNullable<CrossVeda["pairs"]>[number];
type ClassRow = NonNullable<CrossVeda["relationship_classes"]>[number];

const REUSE_CLASS = "REUSES_TEXT_FROM";

/** How many of the four collections a formula family reaches, in words. */
const REACH_WORDS: Record<number, string> = {
    1: "one collection only",
    2: "two of the four",
    3: "three of the four",
    4: "all four collections",
};

function cellFor(pair: PairRow, relationshipClass: string) {
    return (pair.cells ?? []).find((cell) => cell.relationship_class === relationshipClass);
}

/** The count a cell carries, or null where the cell carries a state instead. */
function countFor(pair: PairRow, relationshipClass: string) {
    const cell = cellFor(pair, relationshipClass);
    if (!cell) return null;
    if (cell.status !== "MEASURED" && cell.status !== "MEASURED_ZERO") return null;
    return cell.edges ?? null;
}

/**
 * One resolved side of a reuse witness.
 *
 * The witness rows arrive with their two sides keyed `samaveda` and `rigveda`, and
 * the measurement behind them filters neither side by corpus. The rows it currently
 * returns are Atharvavedic, so trusting the field name would print "Samaveda" above
 * an Atharvavedic citation on every row. Each citation is resolved instead and the
 * corpus is read off the resolved passage, which is also what makes the row
 * clickable.
 */
async function resolveCitation(citation: string) {
    if (!citation) return null;
    const result = await load<SearchResponse>(
        `/search?q=${encodeURIComponent(citation)}&type=PASSAGE&limit=1`,
    );
    if (!result.ok) return null;
    const hit = result.data.items?.[0];
    if (hit?.match_type !== "EXACT_CITATION") return null;
    return { key: hit.stable_id, veda: hit.veda ?? null };
}

export default async function ConnectionsPage() {
    const [matrixResult, diffusionResult] = await Promise.all([
        load<CrossVeda>("/insights/cross-veda"),
        load<FormulaDiffusion>("/insights/formula-diffusion?limit=8"),
    ]);
    if (!matrixResult.ok) {
        return (
            <div className="va-conn-page">
                <LoadFailure status={matrixResult.status} message={matrixResult.message} />
            </div>
        );
    }

    const matrix = matrixResult.data;
    const classes: ClassRow[] = matrix.relationship_classes ?? [];
    const pairs: PairRow[] = matrix.pairs ?? [];
    const diffusion = diffusionResult.ok ? diffusionResult.data : null;

    /* A class that reaches at least one pair has something to say on a pair card.
       The rest are real and are reported once, under their own kind, rather than as
       an empty column repeated six times. */
    const pairClasses = classes.filter((row) => (row.pairs_reached ?? []).length > 0);
    const everyPairClasses = pairClasses.filter(
        (row) => (row.pairs_reached ?? []).length === pairs.length,
    );

    /* The cards need an order and every honest one is a choice, so the choice is
       stated in the page rather than left to look like a ranking. It is a single
       class -- the largest one measured for every pair -- and never the sum of a
       pair's cells, which the measurement asks callers not to treat as a score. */
    const orderingClass =
        [...everyPairClasses].sort(
            (a, b) => (b.cross_veda_edges ?? 0) - (a.cross_veda_edges ?? 0),
        )[0] ?? null;
    const orderedPairs = orderingClass
        ? [...pairs].sort(
              (a, b) =>
                  (countFor(b, orderingClass.relationship_class) ?? 0) -
                  (countFor(a, orderingClass.relationship_class) ?? 0),
          )
        : pairs;

    /* One badge per pair at most. For every class, find the pair holding the largest
       share of it; a pair that leads several classes is badged with the one it
       dominates hardest, and a tie is left unbadged rather than broken arbitrarily. */
    const leads = new Map<string, { relation: ClassRow; edges: number; total: number }>();
    for (const relation of pairClasses) {
        const total = relation.cross_veda_edges ?? 0;
        if (total <= 0) continue;
        const counts = pairs.map((pair) => ({
            pair: pair.pair,
            edges: countFor(pair, relation.relationship_class) ?? 0,
        }));
        const top = Math.max(...counts.map((row) => row.edges));
        const holders = counts.filter((row) => row.edges === top);
        if (top <= 0 || holders.length !== 1) continue;
        const holder = holders[0];
        const held = leads.get(holder.pair);
        if (!held || holder.edges / total > held.edges / held.total) {
            leads.set(holder.pair, { relation, edges: holder.edges, total });
        }
    }

    /* What this page can state about direction, read off the measurement rather than
       assumed: the pairs where directed reuse was established, and the pairs where it
       was measured and refused. */
    const reuseClass = classes.find((row) => row.relationship_class === REUSE_CLASS) ?? null;
    const reuseEstablished = pairs.filter((pair) => (countFor(pair, REUSE_CLASS) ?? 0) > 0);
    const reuseRefused = pairs.filter(
        (pair) => cellFor(pair, REUSE_CLASS)?.status === "MEASURED_ZERO",
    );

    const witnesses = (diffusion?.reuse_witnesses ?? []).slice(0, 8);
    const resolved = await Promise.all(
        witnesses.map(async (row) => {
            const [later, earlier] = await Promise.all([
                resolveCitation(row.samaveda ?? ""),
                resolveCitation(row.rigveda ?? ""),
            ]);
            return { row, later, earlier };
        }),
    );
    const witnessPairCodes = [
        ...new Set(
            resolved
                .map((item) =>
                    [item.later?.veda, item.earlier?.veda]
                        .filter((code): code is string => Boolean(code))
                        .sort()
                        .join("|"),
                )
                .filter((key) => key.includes("|")),
        ),
    ].map((key) => key.split("|"));
    const witnessEarlier = [
        ...new Set(
            resolved.map((item) => item.earlier?.veda).filter((code): code is string => Boolean(code)),
        ),
    ].map((code) => vedaNames[code] ?? code);
    const levelsRecorded = witnesses.some((row) => Boolean(row.match_level));

    const span = diffusion?.span_census ?? [];
    const familiesTotal = span.reduce((total, row) => total + row.families, 0);
    const widestSpan = span.length ? Math.max(...span.map((row) => row.vedas_reached)) : 0;
    const widestRow = span.find((row) => row.vedas_reached === widestSpan) ?? null;

    return (
        <div className="va-conn-page">
            <header className="va-conn-head">
                <p className="va-conn-eyebrow">Connections</p>
                <h1>What the four Vedas share</h1>
                <p className="va-conn-lede">
                    {pairClasses.length} kinds of connection are measured between the four Samhitas,
                    pair by pair, and kept apart. A verse repeated word for word, a verse recorded
                    twice with edition-level differences and two verses that merely name the same
                    god are three different claims, so nothing on this page adds them into a single
                    similarity score.
                </p>
                {reuseEstablished.length > 0 && (
                    <p className="va-conn-standfirst">
                        Direction — which verse carries the other&rsquo;s wording — is established
                        for{" "}
                        {listSentence(reuseEstablished.map((pair) => pairDash(pair.vedas)))}.
                        {reuseRefused.length > 0 && (
                            <>
                                {" "}
                                The other {reuseRefused.length} pairs were measured for it and the
                                measurement declined to name a direction; each one says why, on the
                                pair.
                            </>
                        )}
                        {everyPairClasses.length > 0 && (
                            <>
                                {" "}
                                {titleCase(
                                    listSentence(
                                        everyPairClasses.map(
                                            (relation) =>
                                                connectionCopy(relation.relationship_class).plural,
                                        ),
                                    ),
                                )}{" "}
                                are measured for all {pairs.length} pairs.
                            </>
                        )}
                    </p>
                )}
            </header>

            <section className="va-conn-section" aria-labelledby="va-conn-kinds-heading">
                <hr className="va-rule-drawn" />
                    <div className="va-conn-section-head">
                    <h2 id="va-conn-kinds-heading">The kinds of connection</h2>
                    <p>
                        Each is a different claim about two verses, and a count is the number of
                        connections of that kind measured between two different Vedas.{" "}
                        {classes.length} kinds are tracked and {pairClasses.length} of them join two
                        Vedas. The rest are listed anyway, because a reader has to be able to tell a
                        measure that found nothing from one that was never taken.
                    </p>
                </div>
                <ul className="va-conn-kinds">
                    {classes.map((relation) => {
                        const copy = connectionCopy(relation.relationship_class);
                        const state = cellState(relation.population_status);
                        const reach = (relation.pairs_reached ?? []).length;
                        const inside = relation.within_one_veda_edges;
                        /* A kind that carries a count anywhere is a measured kind, whether
                           the count crosses a corpus boundary or stays inside one. Only a
                           kind with no count at all takes its tone from why it has none. */
                        const counted = relation.cross_veda_edges != null || inside > 0;
                        return (
                            <li
                                className="va-conn-kind"
                                key={relation.relationship_class}
                                data-tone={counted ? "measured" : state.tone}
                            >
                                <div className="va-conn-kind-text">
                                    <h3>{copy.name}</h3>
                                    <p>{copy.definition}</p>
                                </div>
                                <p className="va-conn-kind-figure">
                                    {relation.cross_veda_edges != null ? (
                                        <>
                                            <b>{relation.cross_veda_edges.toLocaleString()}</b>
                                            <span>
                                                between two Vedas,{" "}
                                                {reach === pairs.length
                                                    ? `across all ${pairs.length} pairs`
                                                    : `across ${reach} of the ${pairs.length} pairs`}
                                            </span>
                                            {inside > 0 && (
                                                <small>
                                                    {inside.toLocaleString()} more stay inside a
                                                    single Veda and are counted separately
                                                </small>
                                            )}
                                        </>
                                    ) : inside > 0 ? (
                                        <>
                                            <b>{inside.toLocaleString()}</b>
                                            <span>every one inside a single Veda</span>
                                        </>
                                    ) : (
                                        <>
                                            <span className="va-conn-state">{state.label}</span>
                                            <small>{state.meaning}</small>
                                        </>
                                    )}
                                </p>
                            </li>
                        );
                    })}
                </ul>
            </section>

            <section className="va-conn-section" aria-labelledby="va-conn-pairs-heading">
                <hr className="va-rule-drawn" />
                    <div className="va-conn-section-head">
                    <h2 id="va-conn-pairs-heading">Pair by pair</h2>
                    <p>
                        {orderingClass
                            ? `Ordered by ${connectionCopy(orderingClass.relationship_class).plural}, the largest class measured for every pair. The counts of different kinds are not comparable and are never summed.`
                            : "The counts of different kinds are not comparable and are never summed."}
                    </p>
                </div>
                <div className="va-conn-pairs">
                    {orderedPairs.map((pair) => {
                        const sides = (pair.vedas ?? []).map((code) => vedaNames[code] ?? code);
                        const lead = leads.get(pair.pair) ?? null;
                        const refusals = (pair.cells ?? []).filter(
                            (cell) =>
                                cell.status === "MEASURED_ZERO" ||
                                cell.status === "NOT_ESTABLISHED_FOR_PAIR",
                        );
                        const reuseEdges = countFor(pair, REUSE_CLASS) ?? 0;
                        return (
                            <article className="va-conn-pair" key={pair.pair}>
                                <h3 className="va-conn-pair-name">
                                    {sides[0]}
                                    <span aria-hidden="true">&#8596;</span>
                                    <span className="sr-only">and</span>
                                    {sides[1]}
                                </h3>
                                {lead && (
                                    <p className="va-conn-pair-lead">
                                        <b>
                                            {Math.round((lead.edges / lead.total) * 100)}% of all{" "}
                                            {connectionCopy(lead.relation.relationship_class).plural}
                                        </b>
                                        <span>
                                            {lead.edges.toLocaleString()} of{" "}
                                            {lead.total.toLocaleString()} measured anywhere in the
                                            corpus
                                        </span>
                                    </p>
                                )}
                                <dl className="va-conn-metrics">
                                    {pairClasses.map((relation) => {
                                        const cell = cellFor(pair, relation.relationship_class);
                                        const state = cellState(cell?.status);
                                        const copy = connectionCopy(relation.relationship_class);
                                        return (
                                            <div
                                                className="va-conn-metric"
                                                key={relation.relationship_class}
                                                data-tone={state.tone}
                                            >
                                                <dt>{copy.name}</dt>
                                                <dd>
                                                    {cell?.status === "MEASURED" &&
                                                    cell.edges != null ? (
                                                        cell.edges.toLocaleString()
                                                    ) : (
                                                        <span className="va-conn-state">
                                                            {state.label}
                                                        </span>
                                                    )}
                                                </dd>
                                            </div>
                                        );
                                    })}
                                </dl>
                                {reuseEdges > 0 && (
                                    <p className="va-conn-pair-note">
                                        Direction is recorded here: each of these{" "}
                                        {reuseEdges.toLocaleString()} connections names which of the
                                        two verses is the earlier side.
                                    </p>
                                )}
                                {refusals.map((cell) => (
                                    <p className="va-conn-refusal" key={cell.relationship_class}>
                                        <strong>
                                            {connectionCopy(cell.relationship_class).name}:{" "}
                                            {cellState(cell.status).label.toLowerCase()}.
                                        </strong>{" "}
                                        {plainNote(cell.note) || cellState(cell.status).meaning}
                                    </p>
                                ))}
                            </article>
                        );
                    })}
                </div>
            </section>

            {resolved.length > 0 && (
                <section className="va-conn-section" aria-labelledby="va-conn-witness-heading">
                    <hr className="va-rule-drawn" />
                    <div className="va-conn-section-head">
                        <h2 id="va-conn-witness-heading">Verses that carry earlier wording</h2>
                        <p>
                            {reuseClass?.cross_veda_edges != null && (
                                <>
                                    {reuseClass.cross_veda_edges.toLocaleString()} directed
                                    connections are measured in all; these are{" "}
                                    {resolved.length} of them.{" "}
                                </>
                            )}
                            {witnessPairCodes.length === 1
                                ? `Every row below joins ${pairName(witnessPairCodes[0])}.`
                                : witnessPairCodes.length > 1
                                  ? `The rows below join ${listSentence(witnessPairCodes.map(pairDash))}.`
                                  : ""}
                            {witnessEarlier.length === 1 &&
                                ` The earlier side is ${witnessEarlier[0]} in every one.`}
                        </p>
                    </div>
                    <ul className="va-conn-witnesses">
                        {resolved.map(({ row, later, earlier }) => {
                            const body = (
                                <>
                                    <span className="va-conn-witness-side">
                                        <small>
                                            {later?.veda
                                                ? (vedaNames[later.veda] ?? later.veda)
                                                : "Corpus not resolved"}
                                        </small>
                                        <strong>{row.samaveda}</strong>
                                    </span>
                                    <span className="va-conn-witness-rel">
                                        carries wording from
                                        <ArrowRight size={15} aria-hidden="true" />
                                    </span>
                                    <span className="va-conn-witness-side">
                                        <small>
                                            {earlier?.veda
                                                ? (vedaNames[earlier.veda] ?? earlier.veda)
                                                : "Corpus not resolved"}
                                        </small>
                                        <strong>{row.rigveda}</strong>
                                    </span>
                                    {row.match_level && (
                                        <span className="va-conn-witness-level">
                                            {matchLevelCopy(row.match_level)}
                                        </span>
                                    )}
                                </>
                            );
                            return (
                                <li key={`${row.samaveda}-${row.rigveda}`}>
                                    {later?.key ? (
                                        <Link
                                            className="va-conn-witness"
                                            href={`/reuse/${encoded(later.key)}`}
                                        >
                                            {body}
                                            <span className="va-conn-witness-go">
                                                <ArrowRight size={16} aria-hidden="true" />
                                            </span>
                                        </Link>
                                    ) : (
                                        <div className="va-conn-witness">{body}</div>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                    {!levelsRecorded && (
                        <p className="va-conn-footnote">
                            The comparison surface is not recorded for these connections. That is a
                            gap in what was stored about the match, not a sign of a weak one.
                        </p>
                    )}
                    <Link className="va-conn-onward" href="/formulas">
                        Follow shared wording through the formula families
                        <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                </section>
            )}

            {span.length > 0 && (
                <section className="va-conn-section" aria-labelledby="va-conn-span-heading">
                    <hr className="va-rule-drawn" />
                    <div className="va-conn-section-head">
                        <h2 id="va-conn-span-heading">How far a shared phrase travels</h2>
                        <p>
                            A formula family is one wording plus everything that contains it or
                            closely resembles it. Its span measures diction:{" "}
                            {widestRow
                                ? `${widestRow.families.toLocaleString()} of the ${familiesTotal.toLocaleString()} families are heard in ${REACH_WORDS[widestSpan] ?? `${widestSpan} collections`}`
                                : `${familiesTotal.toLocaleString()} families are measured`}
                            , which is a fact about shared phrasing and not a demonstrated line of
                            transmission.
                        </p>
                    </div>
                    <ul className="va-conn-span">
                        {span.map((row) => (
                            <li key={row.vedas_reached} data-cross={String(row.cross_veda)}>
                                <b>{row.families.toLocaleString()}</b>
                                <span>
                                    families reach {REACH_WORDS[row.vedas_reached] ?? `${row.vedas_reached} collections`}
                                </span>
                                <small>{row.occurrences.toLocaleString()} occurrences</small>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section className="va-conn-section" aria-labelledby="va-conn-evidence-heading">
                <hr className="va-rule-drawn" />
                    <div className="va-conn-section-head">
                    <h2 id="va-conn-evidence-heading">The evidence behind this page</h2>
                    <p>
                        What &ldquo;the four Vedas&rdquo; means here, and every cell of the
                        measurement in full.
                    </p>
                </div>
                {(matrix.scope_statements ?? []).length > 0 && (
                    <dl className="va-conn-scope">
                        {(matrix.scope_statements ?? []).map((statement) => (
                            <div key={statement.work_id}>
                                <dt>{vedaNames[statement.veda] ?? statement.veda}</dt>
                                <dd>
                                    {statement.scope_honest_label ??
                                        statement.traditional_name ??
                                        "Scope not stated"}
                                    {(statement.excluded_corpora ?? []).length > 0 && (
                                        <small>
                                            Not held:{" "}
                                            {listSentence(
                                                (statement.excluded_corpora ?? []).map(
                                                    corpusName,
                                                ),
                                            )}
                                            .
                                        </small>
                                    )}
                                </dd>
                            </div>
                        ))}
                    </dl>
                )}
                <EvidenceMatrix pairs={pairs} classes={classes} shape={matrix.shape} />
                <CaveatList
                    caveats={matrix.caveats}
                    limit={(matrix.caveats ?? []).length}
                    title="How this was measured, in the measurement's own words"
                />
            </section>
        </div>
    );
}
