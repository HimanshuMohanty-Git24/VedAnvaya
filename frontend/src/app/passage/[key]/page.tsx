import {
    ArrowLeft,
    ArrowRight,
    ArrowsLeftRight,
    CirclesThreePlus,
} from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { AskAboutButton } from "@/components/ask/ask-about-button";
import { CopyButton } from "@/components/copy-button";
import { LoadFailure } from "@/components/empty-state";
import { PassageKnowledge } from "@/components/passage-knowledge";
import { Caveat, KnowledgeStatus } from "@/components/status";
import {
    routeId,
    encoded,
    load,
    type ParallelsResponse,
    type Reader,
    workSlugs,
    vedaNames,
} from "@/lib/api";

type Params = { params: Promise<{ key: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { key: rawKey } = await params;
    const key = routeId(rawKey);
    const result = await load<Reader>(`/passages/${encoded(key)}/reader`);
    if (!result.ok) return { title: "Passage" };
    return {
        title: result.data.canonical_citation ?? result.data.display_label ?? "Passage",
        description: result.data.translations.items?.[0]?.text ?? undefined,
    };
}

export default async function PassagePage({ params }: Params) {
    const { key: rawKey } = await params;
    const key = routeId(rawKey);
    const result = await load<Reader>(`/passages/${encoded(key)}/reader`);
    if (!result.ok) {
        if (result.status === 404) notFound();
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const reader = result.data;
    const parallels = await load<ParallelsResponse>(`/passages/${encoded(key)}/parallels?limit=25`);

    const primary = reader.primary_text;
    const alternates = (reader.text.surfaces ?? []).filter(
        (surface) => surface.text && surface.text !== primary?.text,
    );
    const crossVeda = parallels.ok
        ? (parallels.data.items ?? []).filter((row) => !row.same_veda && row.is_textual_parallelism)
        : [];

    return (
        <div className="reader-page">
            <nav className="shell reader-breadcrumbs" aria-label="Passage location">
                <Link href={`/vedas/${workSlugs[reader.veda] ?? "rigveda"}`}>
                    {reader.work_display_label}
                </Link>
                {reader.breadcrumbs?.map((crumb) => (
                    <Link
                        key={crumb.canonical_key}
                        href={`/passage/${encoded(crumb.canonical_key ?? "")}`}
                    >
                        <span className="crumb-level">{crumb.native_label}</span>
                        {crumb.value}
                    </Link>
                ))}
            </nav>

            <div className="shell reader-layout">
                <article className="reading-column">
                    <header className="citation-line">
                        <div>
                            <span className="veda-chip">
                                {vedaNames[reader.veda] ?? reader.veda}
                            </span>
                            <h1>{reader.canonical_citation ?? reader.display_label}</h1>
                        </div>
                        <KnowledgeStatus status={reader.data_status} compact />
                    </header>

                    {primary?.text ? (
                        <section className="mantra-block" aria-label="Sanskrit text">
                            <div className="text-meta">
                                <span>
                                    {primary.script === "DEVANAGARI" ? "Devanagari" : "IAST"}{" "}
                                    Sanskrit
                                    {primary.accented ? ", accented" : ""}
                                </span>
                                <CopyButton text={primary.text} />
                            </div>
                            <p
                                className={
                                    primary.script === "DEVANAGARI"
                                        ? "sanskrit devanagari"
                                        : "sanskrit"
                                }
                                lang="sa"
                            >
                                {primary.text}
                            </p>
                        </section>
                    ) : (
                        <KnowledgeStatus status={reader.text.data_status} />
                    )}

                    {alternates.length > 0 && (
                        <details className="witness-block">
                            <summary>
                                Other witnesses of this text
                                <span>{alternates.length}</span>
                            </summary>
                            {alternates.map((surface) => (
                                <div key={`${surface.witness_id}-${surface.surface}`}>
                                    <div className="text-meta">
                                        <span>
                                            {surface.witness_id ?? "Witness not identified"}{" "}
                                            &middot;{" "}
                                            {surface.script === "DEVANAGARI"
                                                ? "Devanagari"
                                                : "IAST"}
                                        </span>
                                        {surface.text && <CopyButton text={surface.text} />}
                                    </div>
                                    <p
                                        className={
                                            surface.script === "DEVANAGARI"
                                                ? "sanskrit devanagari"
                                                : "sanskrit"
                                        }
                                        lang="sa"
                                    >
                                        {surface.text}
                                    </p>
                                </div>
                            ))}
                        </details>
                    )}

                    <section className="translation-section" aria-label="Translation">
                        <h2>Translation</h2>
                        {reader.translations.items?.length ? (
                            reader.translations.items.map((translation) => (
                                <figure key={`${translation.translator}-${translation.text}`}>
                                    <blockquote>{translation.text}</blockquote>
                                    <figcaption>
                                        <span>
                                            {translation.translator}
                                            {translation.year ? `, ${translation.year}` : ""}
                                        </span>
                                        {translation.work_edition && (
                                            <small>{translation.work_edition}</small>
                                        )}
                                    </figcaption>
                                </figure>
                            ))
                        ) : (
                            <KnowledgeStatus
                                status={reader.translations.data_status}
                                note="No released translation covers this passage in the current build. The verse is held; its translation layer is not."
                            />
                        )}
                    </section>

                    {crossVeda.length > 0 && (
                        <Link
                            className="reuse-callout"
                            href={`/reuse/${encoded(reader.canonical_key)}`}
                        >
                            <ArrowsLeftRight size={20} aria-hidden="true" />
                            <span>
                                <strong>
                                    This wording also stands in{" "}
                                    {[
                                        ...new Set(
                                            crossVeda.map((row) => vedaNames[row.passage.veda]),
                                        ),
                                    ]
                                        .filter(Boolean)
                                        .join(" and ")}
                                </strong>
                                <small>
                                    Compare the two texts side by side with their evidence
                                </small>
                            </span>
                            <ArrowRight size={17} aria-hidden="true" />
                        </Link>
                    )}

                    <nav className="reader-nav" aria-label="Adjacent passages">
                        {reader.previous ? (
                            <Link href={`/passage/${encoded(reader.previous.canonical_key)}`}>
                                <ArrowLeft size={17} aria-hidden="true" />
                                <span>
                                    <small>Previous</small>
                                    {reader.previous.display_label}
                                </span>
                            </Link>
                        ) : (
                            <p className="reader-edge">{reader.neighbour_note}</p>
                        )}
                        {reader.next && (
                            <Link href={`/passage/${encoded(reader.next.canonical_key)}`}>
                                <span>
                                    <small>Next</small>
                                    {reader.next.display_label}
                                </span>
                                <ArrowRight size={17} aria-hidden="true" />
                            </Link>
                        )}
                    </nav>
                </article>

                <aside className="reader-aside" aria-label="Passage knowledge">
                    <PassageKnowledge
                        reader={reader}
                        parallels={parallels.ok ? (parallels.data.items ?? []) : []}
                        parallelsFailed={!parallels.ok}
                    />
                    <Link
                        className="graph-entry"
                        href={`/graph?node=${encoded(reader.canonical_key)}`}
                    >
                        <CirclesThreePlus size={20} aria-hidden="true" />
                        <span>
                            <strong>Open in the graph</strong>
                            <small>
                                {reader.graph_neighbour_count ?? 0} curated connections from this
                                verse
                            </small>
                        </span>
                        <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                    <AskAboutButton
                        passageKey={reader.canonical_key}
                        label="Ask about this mantra"
                    />
                </aside>
            </div>

            {reader.caveats?.length ? (
                <div className="shell reader-footnotes">
                    {reader.caveats.map((caveat) => (
                        <Caveat key={caveat.text}>{caveat.text}</Caveat>
                    ))}
                </div>
            ) : null}
        </div>
    );
}
