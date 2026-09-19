import { ArrowLeft, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { AskAboutButton } from "@/components/ask/ask-about-button";
import { CopyButton } from "@/components/copy-button";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { Apparatus } from "@/components/reader/apparatus";
import { RecitationPlayer } from "@/components/recitation-player";
import { Caveat, KnowledgeStatus } from "@/components/status";
import {
    routeId,
    encoded,
    load,
    type ParallelsResponse,
    type PassageAudio,
    type Reader,
    workSlugs,
    vedaNames,
} from "@/lib/api";

/**
 * One mantra, read.
 *
 * The composition rule for this page is that the verse is the protagonist and everything
 * else is margin. The build this replaces put the verse in a bordered card between a bordered
 * player and a bordered witness box, beside a tabbed rail of six more bordered panels, and
 * the effect was that the text had the same visual weight as the controls around it.
 *
 * Nothing has been removed. Every distinction the old page drew is still drawn, because those
 * distinctions are the product rather than decoration on it: an ascription from the
 * traditional index is never shown as something the Sanskrit says, a named deity keeps its
 * referent certainty, an absent translation is a statement about the layer rather than a
 * blank, and a caveat is printed rather than summarised.
 */

type Params = { params: Promise<{ key: string }> };

type TranslationItem = NonNullable<Reader["translations"]["items"]>[number];

/**
 * The words printed above a rendering that is not this verse's own English.
 *
 * Returns null for the ordinary case, so a dedicated English translation gets no label at
 * all and the three exceptional shapes are the only ones that carry one. The alternative --
 * labelling every row — trains a reader to skip the label.
 */
function translationLabel(translation: TranslationItem): string | null {
    if (translation.coverage_kind === "REUSED_RENDERING") {
        const veda = translation.reused_from_veda
            ? (vedaNames[translation.reused_from_veda] ?? translation.reused_from_veda)
            : "another corpus";
        return `Reused from the ${veda}`;
    }
    if (translation.language !== "en") {
        return `${translation.language_name ?? translation.language}, not English`;
    }
    if (translation.coverage_kind === "RANGE_TRANSLATION") {
        return translation.is_this_passages_own
            ? "One rendering across this verse and the next"
            : "Covered by a rendering anchored on a neighbouring verse";
    }
    if (translation.coverage_kind === "CONTAINER_TRANSLATION") {
        return "Aligned to the hymn, not to this verse";
    }
    return null;
}

function disclosureTitle(translation: TranslationItem): string {
    if (translation.coverage_kind === "REUSED_RENDERING") return "What this English is";
    if (translation.language !== "en") return "Why this is not English";
    return "What this rendering covers";
}

/** The attribution sentence for a search snippet, where no caveat can follow the text. */
function describeProvenance(translation: TranslationItem): string {
    const who = `${translation.translator}${translation.year ? `, ${translation.year}` : ""}`;
    if (translation.coverage_kind === "REUSED_RENDERING") {
        const where = translation.reused_from_citation ?? "a verified-identical parallel";
        return `English reused from ${where} (${who}), not an independent translation of this verse.`;
    }
    if (translation.language !== "en") {
        return `Rendered into ${translation.language_name ?? translation.language} by ${who}, not into English.`;
    }
    if (translation.coverage_kind === "RANGE_TRANSLATION") {
        const span = translation.covers_canonical_keys?.length ?? 0;
        return `One rendering covering ${span} verses, by ${who}.`;
    }
    return `Translated by ${who}.`;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { key: rawKey } = await params;
    const key = routeId(rawKey);
    const result = await load<Reader>(`/passages/${encoded(key)}/reader`);
    if (!result.ok) return { title: "Passage" };

    const citation = result.data.canonical_citation ?? result.data.display_label ?? "Passage";
    const translation = result.data.translations.items?.[0];
    return {
        title: citation,
        /*
         * The description is the translation, and never the Sanskrit as a substitute for one.
         * A verse whose translation layer is not built should say so rather than present its
         * romanised text to a search engine as though it were a gloss.
         *
         * The verb matters here as much as anywhere else on the page, and a search result is
         * the one place the caveat beneath the text cannot travel with it. "Translated by" is
         * reserved for a dedicated English rendering; a reused one is rendered from its
         * parallel, a range one covers a span, and a Latin one was not English at all.
         */
        description: translation
            ? `${translation.text} ${describeProvenance(translation)}`
            : `${citation} is held in this corpus. No translation of any kind reaches it in the current build.`,
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
    const [parallels, audio] = await Promise.all([
        load<ParallelsResponse>(`/passages/${encoded(key)}/parallels?limit=25`),
        load<PassageAudio>(`/passages/${encoded(key)}/audio`),
    ]);

    /*
     * No audio is a supported state, so an unmapped passage renders no player rather than a
     * disabled one with a zero duration. A failed request is treated the same way: the reader
     * loses a control they may never have had, and keeps the text.
     */
    const recitation = audio.ok ? (audio.data.tracks ?? [])[0] : undefined;

    const primary = reader.primary_text;
    const alternates = (reader.text.surfaces ?? []).filter(
        (surface) =>
            surface.is_displayable !== false &&
            surface.text &&
            surface.text !== primary?.text,
    );
    const hasNotationWitness =
        (reader.text.surfaces ?? []).some(
            (s) => s.surface === "PARALLEL_WITNESS" || (s.accented && s.is_displayable !== false),
        ) || Boolean(primary?.accented);
    const crossVeda = parallels.ok
        ? (parallels.data.items ?? []).filter((row) => !row.same_veda && row.is_textual_parallelism)
        : [];
    const script = primary?.script === "DEVANAGARI" ? "DEVANAGARI" : "IAST";

    return (
        <div className="va-reader">
            <nav aria-label="Passage location" className="va-reader-where">
                <Link href={`/vedas/${workSlugs[reader.veda] ?? "rigveda"}`}>
                    {reader.work_display_label}
                </Link>
                {reader.breadcrumbs?.map((crumb) => (
                    <span key={crumb.canonical_key} style={{ display: "contents" }}>
                        <span aria-hidden="true">/</span>
                        <Link href={`/passage/${encoded(crumb.canonical_key ?? "")}`}>
                            <em>{crumb.native_label}</em>
                            <strong>{crumb.value}</strong>
                        </Link>
                    </span>
                ))}
            </nav>

            <div className="va-reader-layout">
                <article className="va-reading">
                    <header className="va-reader-head">
                        <div>
                            <p className="va-reader-veda">
                                {vedaNames[reader.veda] ?? reader.veda}
                            </p>
                            <h1 className="va-reader-title">
                                {reader.canonical_citation ?? reader.display_label}
                            </h1>
                        </div>
                        <KnowledgeStatus status={reader.data_status} compact />
                    </header>

                    {primary?.text ? (
                        <section aria-label="Sanskrit text" className="va-verse">
                            <div className="va-verse-meta">
                                <span>
                                    {script === "DEVANAGARI" ? "Devanagari" : "Romanised"}
                                    {primary.accented ? ", accented" : ""}
                                    {primary.witness_id ? ` · ${primary.witness_id}` : ""}
                                </span>
                                <CopyButton text={primary.text} />
                            </div>
                            <p
                                className={
                                    script === "DEVANAGARI" ? "sanskrit devanagari" : "sanskrit"
                                }
                                data-script={script}
                                lang="sa"
                            >
                                {primary.text}
                            </p>
                        </section>
                    ) : (
                        <KnowledgeStatus status={reader.text.data_status} />
                    )}

                    {recitation ? (
                        <RecitationPlayer key={recitation.audio_id} track={recitation} />
                    ) : null}

                    {alternates.length > 0 && (
                        <details className="va-witnesses witness-block">
                            <summary>
                                {alternates.length === 1
                                    ? "One other witness prints this text"
                                    : `${alternates.length} other witnesses print this text`}
                            </summary>
                            {alternates.map((surface) => (
                                <div
                                    className="va-witness"
                                    key={`${surface.witness_id}-${surface.surface}`}
                                >
                                    <div className="va-verse-meta">
                                        <span>
                                            {surface.surface === "PARALLEL_WITNESS"
                                                ? "Validated Notation Witness (Source-explicit svara marks)"
                                                : (surface.witness_id ?? "Witness not identified")}
                                            {" · "}
                                            {surface.script === "DEVANAGARI"
                                                ? "Devanagari"
                                                : "Romanised"}
                                            {surface.accented ? ", accented" : ""}
                                        </span>
                                        {surface.text && <CopyButton text={surface.text} />}
                                    </div>
                                    <p
                                        className={
                                            surface.script === "DEVANAGARI"
                                                ? "sanskrit devanagari"
                                                : "sanskrit"
                                        }
                                        data-script={
                                            surface.script === "DEVANAGARI" ? "DEVANAGARI" : "IAST"
                                        }
                                        lang="sa"
                                    >
                                        {surface.text}
                                    </p>
                                </div>
                            ))}
                        </details>
                    )}

                    {reader.veda === "SV" && (
                        <p className="va-notation-notice" style={{ fontSize: "var(--va-text-xs)", color: "var(--va-text-tertiary)", marginBlock: "var(--va-space-xs)" }}>
                            {hasNotationWitness
                                ? "Validated Samavedic notation witness held (source-explicit svara marks, Gates A/B/C passed)."
                                : "Musical notation withheld for this verse (708 verses pending alignment; Gāna song collections outside release scope)."}
                        </p>
                    )}

                    <section
                        aria-label="Translation"
                        className="va-translation translation-section"
                    >
                        <h2>Translation</h2>
                        {reader.translations.items?.length ? (
                            <>
                                {reader.translations.items.map((translation) => (
                                    <figure
                                        data-coverage={translation.coverage_kind}
                                        data-language={translation.language}
                                        key={`${translation.translator}-${translation.text}`}
                                    >
                                        {/*
                                         * The heading above says "Translation", and for three of
                                         * the four coverage kinds that word alone is a claim the
                                         * row does not support. The label is printed before the
                                         * text rather than after it, because a reader who has
                                         * already read the English as this verse's own gloss does
                                         * not un-read it on reaching a footnote.
                                         */}
                                        {translationLabel(translation) && (
                                            <p className="va-translation-kind translation-kind">
                                                {translationLabel(translation)}
                                            </p>
                                        )}
                                        <blockquote
                                            lang={translation.language}
                                        >
                                            {translation.text}
                                        </blockquote>
                                        <figcaption>
                                            <span>
                                                {translation.translator}
                                                {translation.year ? `, ${translation.year}` : ""}
                                            </span>
                                            {translation.work_edition && (
                                                <span>{translation.work_edition}</span>
                                            )}
                                            {translation.language !== "en" && (
                                                <span>
                                                    {translation.language_name ??
                                                        translation.language}
                                                </span>
                                            )}
                                        </figcaption>
                                        {translation.disclosure && (
                                            <Caveat title={disclosureTitle(translation)}>
                                                {translation.disclosure}
                                            </Caveat>
                                        )}
                                        {translation.reused_from_citation && (
                                            <p className="va-translation-source translation-source">
                                                Shown from{" "}
                                                <Link
                                                    href={`/passage/${encoded(translation.reused_from_passage_key ?? "")}`}
                                                >
                                                    {translation.reused_from_citation}
                                                </Link>
                                            </p>
                                        )}
                                        {translation.coverage_kind === "RANGE_TRANSLATION" &&
                                            (translation.covers_canonical_keys?.length ?? 0) >
                                                1 && (
                                                <p className="va-translation-span translation-span">
                                                    Covers{" "}
                                                    {translation.covers_canonical_keys?.length}{" "}
                                                    verses of this hymn
                                                </p>
                                            )}
                                    </figure>
                                ))}
                                {reader.translations.caveats?.map((caveat) => (
                                    <Caveat key={caveat.text}>{caveat.text}</Caveat>
                                ))}
                            </>
                        ) : (
                            <KnowledgeStatus
                                note={
                                    reader.veda === "SV"
                                        ? "This Samavedic verse has 0 own dedicated English translations in this corpus (1,671 Samaveda verses are uncovered; 173 have verified reused Rigvedic English renderings)."
                                        : "No translation of any kind reaches this passage in the current build — it has none of its own and no multi-verse print unit covers it. The verse is held; its translation layer is not."
                                }
                                status={reader.translations.data_status}
                            />
                        )}
                    </section>

                    {crossVeda.length > 0 && (
                        <Link
                            className="va-parallel"
                            href={`/reuse/${encoded(reader.canonical_key)}`}
                        >
                            <strong>
                                This wording also stands in{" "}
                                {[...new Set(crossVeda.map((row) => vedaNames[row.passage.veda]))]
                                    .filter(Boolean)
                                    .join(" and ")}
                            </strong>
                            <small>
                                Compare the two texts side by side, with what each witness reads and
                                how the connection was established
                            </small>
                        </Link>
                    )}

                    <nav aria-label="Adjacent passages" className="va-reader-adjacent reader-nav">
                        {reader.previous ? (
                            <Link href={`/passage/${encoded(reader.previous.canonical_key)}`}>
                                <small>
                                    <ArrowLeft aria-hidden="true" size={11} /> Previous
                                </small>
                                <span>{reader.previous.display_label}</span>
                            </Link>
                        ) : (
                            <p className="va-reader-edge reader-edge">{reader.neighbour_note}</p>
                        )}
                        {reader.next && (
                            <Link href={`/passage/${encoded(reader.next.canonical_key)}`}>
                                <small>
                                    Next <ArrowRight aria-hidden="true" size={11} />
                                </small>
                                <span>{reader.next.display_label}</span>
                            </Link>
                        )}
                    </nav>
                </article>

                <aside aria-label="Passage apparatus" className="sticky-aside">
                    {/* The rail travels as one object. Apparatus and actions share a single
                        sticky wrapper so the actions can never be left behind by it. */}
                    <div className="va-rail">
                        <Apparatus
                            parallels={parallels.ok ? (parallels.data.items ?? []) : []}
                            parallelsFailed={!parallels.ok}
                            reader={reader}
                        />
                        <div className="va-apparatus-actions">
                            <Action href={`/graph?node=${encoded(reader.canonical_key)}`}>
                                {reader.graph_neighbour_count
                                    ? `Show ${reader.graph_neighbour_count} connections in the graph`
                                    : "Show this in the graph"}
                            </Action>
                            {/* Quiet, because the rail's language is links and rules. A filled
                            pill here reads as the most important thing on the page, and it
                            is not: the verse is. */}
                            <AskAboutButton
                                label="Ask about this mantra"
                                passageKey={reader.canonical_key}
                                variant="quiet"
                            />
                        </div>
                    </div>
                </aside>
            </div>

            {reader.caveats?.length ? (
                <div className="va-reader-footnotes">
                    {reader.caveats.map((caveat) => (
                        <Caveat key={caveat.text}>{caveat.text}</Caveat>
                    ))}
                </div>
            ) : null}
        </div>
    );
}
