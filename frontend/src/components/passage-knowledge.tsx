import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ParallelView, Reader } from "@/lib/api";
import { encoded } from "@/lib/api";
import {
    attributionCopy,
    certaintyBand,
    certaintyCopy,
    entityHref,
    entityTypeLabel,
    evidenceBasisCopy,
    matchLevelCopy,
    parallelKindCopy,
    trustTierCopy,
} from "@/lib/knowledge";
import { NothingHere } from "./empty-state";
import { CaveatList, KnowledgeStatus } from "./status";
import { TabPanel, Tabs } from "./tabs";

/** Context, Entities, Connections and Evidence for one passage. */
export function PassageKnowledge({
    reader,
    parallels,
    parallelsFailed,
}: {
    reader: Reader;
    parallels: ParallelView[];
    parallelsFailed: boolean;
}) {
    const context = [
        ...(reader.devatas.items ?? []),
        ...(reader.rishis.items ?? []),
        ...(reader.chandas.items ?? []),
    ];
    const textual = parallels.filter((row) => row.is_textual_parallelism);
    const vocabulary = parallels.filter((row) => !row.is_textual_parallelism);

    return (
        <Tabs
            label="Passage knowledge"
            tabs={[
                { value: "context", label: "Context", badge: context.length || null },
                {
                    value: "entities",
                    label: "Entities",
                    badge: reader.major_concepts.items?.length || null,
                },
                { value: "connections", label: "Connections", badge: parallels.length || null },
                { value: "evidence", label: "Evidence" },
            ]}
        >
            <TabPanel value="context">
                <section>
                    <h2>Ascribed in the apparatus</h2>
                    <p className="panel-note">
                        The traditional hymn heading, not a statement inside the verse.
                    </p>
                    {context.length ? (
                        <div className="reference-list">
                            {context.map((ref) => (
                                <Link
                                    href={entityHref(ref.type, ref.id)}
                                    key={`${ref.type}-${ref.id}`}
                                >
                                    <span>{entityTypeLabel(ref.type)}</span>
                                    <strong>{ref.display_label}</strong>
                                    <small>{attributionCopy(ref.attribution_precision)}</small>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <KnowledgeStatus status={reader.devatas.data_status} />
                    )}
                </section>
                <section>
                    <h2>Named inside this verse</h2>
                    {reader.mentioned_devatas.items?.length ? (
                        <>
                            <div className="reference-list">
                                {reader.mentioned_devatas.items.map((ref) => (
                                    <Link
                                        href={entityHref("DEVATA", ref.id)}
                                        key={ref.id}
                                        data-certainty={certaintyBand(ref.referent_certainty)}
                                    >
                                        <span
                                            className={`certainty-chip band-${certaintyBand(ref.referent_certainty)}`}
                                        >
                                            {certaintyCopy(ref.referent_certainty)}
                                        </span>
                                        <strong>{ref.display_label}</strong>
                                        {ref.is_ambiguous && (
                                            <small>
                                                Excluded from default deity analytics until the
                                                referent is resolved.
                                            </small>
                                        )}
                                    </Link>
                                ))}
                            </div>
                            {(reader.mentioned_devatas.excluded_count ?? 0) > 0 && (
                                <p className="panel-note">
                                    {reader.mentioned_devatas.excluded_count} further mention
                                    {reader.mentioned_devatas.excluded_count === 1
                                        ? " is"
                                        : "s are"}{" "}
                                    held back as ambiguous.
                                </p>
                            )}
                        </>
                    ) : (
                        <KnowledgeStatus status={reader.mentioned_devatas.data_status} />
                    )}
                </section>
                <CaveatList caveats={reader.rishis.caveats} title="How attribution was recorded" />
            </TabPanel>

            <TabPanel value="entities">
                <section>
                    <h2>Ideas, acts and things</h2>
                    <p className="panel-note">
                        Registered entities this verse names. A phenomenon and the deity that shares
                        its name stay separate records.
                    </p>
                    {reader.major_concepts.items?.length ? (
                        <div className="entity-chip-list">
                            {reader.major_concepts.items.map((item) => (
                                <Link
                                    className="entity-chip"
                                    href={entityHref(item.type, item.id)}
                                    key={item.id}
                                >
                                    <span>{entityTypeLabel(item.type)}</span>
                                    <strong>{item.display_label}</strong>
                                    {item.subtitle && <small>{item.subtitle}</small>}
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <KnowledgeStatus
                            status={reader.major_concepts.data_status}
                            note="No registered entity was matched in this verse. The verse may still speak of things this graph has not registered."
                        />
                    )}
                </section>
            </TabPanel>

            <TabPanel value="connections">
                {parallelsFailed ? (
                    <KnowledgeStatus
                        status="UNKNOWN"
                        note="The parallel layer did not answer for this passage."
                    />
                ) : (
                    <>
                        <section>
                            <h2>Shared wording</h2>
                            {textual.length ? (
                                <div className="parallel-list">
                                    {textual.slice(0, 12).map((row) => (
                                        <Link
                                            key={
                                                row.parallel_id ??
                                                `${row.passage.canonical_key}-${row.relation}`
                                            }
                                            href={`/reuse/${encoded(reader.canonical_key)}`}
                                            className="parallel-row"
                                        >
                                            <span className="parallel-kind">
                                                {parallelKindCopy(row.relation_kind).label}
                                            </span>
                                            <strong>{row.passage.canonical_citation}</strong>
                                            <small>
                                                {row.veda_pair ?? "same corpus"} &middot;{" "}
                                                {matchLevelCopy(row.match_level)}
                                            </small>
                                            <ArrowRight size={15} aria-hidden="true" />
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <KnowledgeStatus
                                    status={reader.parallel_counts.data_status}
                                    note="No shared wording was established for this passage. The parallel layer is derived, so this is a limit of what was computed."
                                />
                            )}
                        </section>
                        {vocabulary.length > 0 && (
                            <section>
                                <h2>Shared vocabulary</h2>
                                <p className="panel-note">
                                    These passages name some of the same registered entities. That
                                    is not shared wording, and it is counted separately.
                                </p>
                                <div className="parallel-list is-muted">
                                    {vocabulary.slice(0, 8).map((row) => (
                                        <Link
                                            key={row.parallel_id ?? row.passage.canonical_key}
                                            href={`/passage/${encoded(row.passage.canonical_key)}`}
                                            className="parallel-row"
                                        >
                                            <span className="parallel-kind">
                                                {parallelKindCopy(row.relation_kind).label}
                                            </span>
                                            <strong>{row.passage.canonical_citation}</strong>
                                            <ArrowRight size={15} aria-hidden="true" />
                                        </Link>
                                    ))}
                                </div>
                            </section>
                        )}
                        <CaveatList
                            caveats={reader.parallel_counts.caveats}
                            title="How parallels were counted"
                        />
                    </>
                )}
            </TabPanel>

            <TabPanel value="evidence">
                <section>
                    <h2>Where this text comes from</h2>
                    <dl className="provenance-list">
                        <div>
                            <dt>Witness</dt>
                            <dd>{reader.primary_text?.witness_id ?? "Not recorded"}</dd>
                        </div>
                        <div>
                            <dt>Source</dt>
                            <dd>{reader.primary_text?.source_id ?? "Not recorded"}</dd>
                        </div>
                        <div>
                            <dt>Rights</dt>
                            <dd>{reader.primary_text?.rights_status ?? "Not recorded"}</dd>
                        </div>
                        <div>
                            <dt>Translation</dt>
                            <dd>
                                {reader.translations.items?.[0]
                                    ? `${reader.translations.items[0].translator}, ${reader.translations.items[0].quality_status?.toLowerCase().replaceAll("_", " ")}`
                                    : "None released for this passage"}
                            </dd>
                        </div>
                    </dl>
                </section>
                <section>
                    <h2>How the attributions were established</h2>
                    <ul className="basis-list">
                        {[...(reader.devatas.items ?? []), ...(reader.rishis.items ?? [])].map(
                            (ref) => {
                                const copy = evidenceBasisCopy(ref.evidence_basis);
                                return (
                                    <li key={`basis-${ref.type}-${ref.id}`}>
                                        <strong>{ref.display_label}</strong>
                                        <span>{copy.label}</span>
                                        <small>{copy.detail}</small>
                                    </li>
                                );
                            },
                        )}
                    </ul>
                    {!reader.devatas.items?.length && !reader.rishis.items?.length && (
                        <NothingHere
                            title="No attribution to explain"
                            message="This passage carries no deity or seer attribution in the current build."
                        />
                    )}
                </section>
                {textual.length > 0 && (
                    <section>
                        <h2>Derivation of the parallels</h2>
                        <ul className="basis-list">
                            {textual.slice(0, 4).map((row) => (
                                <li key={`ev-${row.parallel_id ?? row.passage.canonical_key}`}>
                                    <strong>{row.passage.canonical_citation}</strong>
                                    <span>{trustTierCopy(row.quality_tier)}</span>
                                    <small>{parallelKindCopy(row.relation_kind).detail}</small>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}
                <details className="provenance">
                    <summary>Layer availability</summary>
                    <dl className="provenance-list">
                        <div>
                            <dt>Devanagari</dt>
                            <dd>{reader.text.devanagari ?? "Not recorded"}</dd>
                        </div>
                        <div>
                            <dt>Transliteration</dt>
                            <dd>{reader.text.transliteration ?? "Not recorded"}</dd>
                        </div>
                        <div>
                            <dt>Recitation audio</dt>
                            <dd>{reader.audio?.note ?? "Not recorded"}</dd>
                        </div>
                    </dl>
                </details>
                <CaveatList caveats={reader.text.caveats} title="Text layer notes" />
            </TabPanel>
        </Tabs>
    );
}
