import Link from "next/link";
import type { ParallelView, Reader } from "@/lib/api";
import { encoded } from "@/lib/api";
import {
    attributionCopy,
    certaintyBand,
    certaintyCopy,
    entityHref,
    entityTypeLabel,
    parallelKindCopy,
} from "@/lib/knowledge";
import { CaveatList, KnowledgeStatus } from "../status";

/**
 * The apparatus rail: what the tradition ascribes to this verse, what the verse names, and
 * what it connects to.
 *
 * This replaces a tab bar over six bordered panels. The tabs were the worse of the two
 * problems: an apparatus is read alongside its text, and putting three quarters of it behind
 * a control means a reader has to know it is there before they can find it. Four groups, all
 * visible, separated by rules.
 *
 * The content is unchanged. Every distinction the old panel drew is still drawn, because
 * those distinctions are the product: an ascription from the traditional index is not a
 * statement the Sanskrit makes, a named deity carries a referent certainty, and a parallel
 * has a kind.
 */

function Row({
    kind,
    value,
    note,
    href,
    certainty,
    band,
}: {
    kind: string;
    value: string;
    note?: string | null;
    href?: string;
    certainty?: string | null;
    band?: string;
}) {
    const body = (
        <>
            <span className="va-row-kind">{kind}</span>
            {certainty ? <span className="va-row-certainty">{certainty}</span> : null}
            <span className="va-row-value">{value}</span>
            {note ? <span className="va-row-note">{note}</span> : null}
        </>
    );
    return href ? (
        <Link className="va-row" data-certainty={band} href={href}>
            {body}
        </Link>
    ) : (
        <div className="va-row" data-certainty={band}>
            {body}
        </div>
    );
}

export function Apparatus({
    reader,
    parallels,
    parallelsFailed,
}: {
    reader: Reader;
    parallels: ParallelView[];
    parallelsFailed: boolean;
}) {
    const ascribed = [
        ...(reader.devatas.items ?? []),
        ...(reader.rishis.items ?? []),
        ...(reader.chandas.items ?? []),
    ];
    const named = reader.mentioned_devatas.items ?? [];
    const concepts = reader.major_concepts.items ?? [];
    const textual = parallels.filter((row) => row.is_textual_parallelism);
    const held = reader.mentioned_devatas.excluded_count ?? 0;

    /*
     * One row per connected passage, carrying every kind recorded for it.
     *
     * A pair can hold more than one relation at once - RV 1.1.1 and SV Aranya 3.4 are both a
     * textual parallel and a text reuse - and the two are not the same claim, so neither is
     * dropped. Printing them as separate rows repeated the citation and read as a duplicate,
     * which is also what React saw: two children under one key.
     *
     * The kind is what the connection is, and it decides what the connection can be used to
     * argue. It is never collapsed into a similarity score.
     */
    const connected = [
        ...textual
            .reduce((rows, row) => {
                const key = row.passage.canonical_key;
                const entry = rows.get(key) ?? {
                    key,
                    label: row.passage.canonical_citation ?? row.passage.display_label ?? key,
                    kinds: [] as ReturnType<typeof parallelKindCopy>[],
                };
                const kind = parallelKindCopy(row.relation_kind);
                if (!entry.kinds.some((seen) => seen.label === kind.label)) {
                    entry.kinds.push(kind);
                }
                rows.set(key, entry);
                return rows;
            }, new Map<string, { key: string; label: string; kinds: ReturnType<typeof parallelKindCopy>[] }>())
            .values(),
    ];

    return (
        <div className="va-apparatus">
            <section className="va-apparatus-group">
                <h2>Ascribed in the apparatus</h2>
                <p className="va-apparatus-note">
                    The traditional hymn heading, not a statement inside the verse.
                </p>
                {ascribed.length ? (
                    ascribed.map((ref) => (
                        <Row
                            href={entityHref(ref.type, ref.id)}
                            key={`${ref.type}-${ref.id}`}
                            kind={entityTypeLabel(ref.type)}
                            note={attributionCopy(ref.attribution_precision)}
                            value={ref.display_label}
                        />
                    ))
                ) : (
                    /*
                     * Compact, because in the rail this is a label and not an argument.
                     *
                     * The Samaveda has no ascription layer at all, so the full block -- an
                     * icon, a heading and two sentences of explanation -- fired on all 1,844
                     * of its verse pages and was the tallest object in the rail on every one
                     * of them. The state is still typed and still named; what is gone is the
                     * paragraph, which is on /limits.
                     */
                    <KnowledgeStatus compact status={reader.devatas.data_status} />
                )}
            </section>

            <section className="va-apparatus-group">
                <h2>Named inside this verse</h2>
                {named.length ? (
                    <>
                        {named.map((ref) => (
                            <Row
                                band={certaintyBand(ref.referent_certainty)}
                                certainty={certaintyCopy(ref.referent_certainty)}
                                href={entityHref("DEVATA", ref.id)}
                                key={ref.id}
                                kind="Deity"
                                note={
                                    ref.is_ambiguous
                                        ? "Excluded from default deity analytics until the referent is resolved."
                                        : null
                                }
                                value={ref.display_label}
                            />
                        ))}
                        {held > 0 ? (
                            <p className="va-apparatus-note">
                                {held} further mention{held === 1 ? " is" : "s are"} held back as
                                ambiguous.
                            </p>
                        ) : null}
                    </>
                ) : (
                    <KnowledgeStatus compact status={reader.mentioned_devatas.data_status} />
                )}
            </section>

            {concepts.length ? (
                <section className="va-apparatus-group">
                    <h2>Ideas, acts and things</h2>
                    {concepts.map((ref) => (
                        <Row
                            href={entityHref(ref.type, ref.id)}
                            key={`${ref.type}-${ref.id}`}
                            kind={entityTypeLabel(ref.type)}
                            note={ref.subtitle}
                            value={ref.display_label}
                        />
                    ))}
                </section>
            ) : null}

            <section className="va-apparatus-group">
                <h2>Connected passages</h2>
                {parallelsFailed ? (
                    <p className="va-apparatus-note">
                        The connection layer could not be read just now. The verse and its apparatus
                        are unaffected.
                    </p>
                ) : textual.length ? (
                    connected
                        .slice(0, 6)
                        .map((row) => (
                            <Row
                                href={`/passage/${encoded(row.key)}`}
                                key={row.key}
                                kind={row.kinds.map((kind) => kind.label).join(" · ")}
                                note={row.kinds.map((kind) => kind.detail).join(" ")}
                                value={row.label}
                            />
                        ))
                ) : (
                    <p className="va-apparatus-note">
                        No other passage in this corpus carries this wording. That is a statement
                        about the four collections held here, not about the Vedas.
                    </p>
                )}
            </section>

            <CaveatList caveats={reader.rishis.caveats} title="How attribution was recorded" />
        </div>
    );
}
