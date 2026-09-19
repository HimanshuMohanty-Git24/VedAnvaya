import { ArrowLeft, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { AskAboutButton } from "@/components/ask/ask-about-button";
import { CopyButton } from "@/components/copy-button";
import { LoadFailure } from "@/components/empty-state";
import { Action } from "@/components/home/sections";
import { Apparatus } from "@/components/reader/apparatus";
import {
    crumbLevelName,
    crumbValue,
    provenanceLine,
    vedaAdjective,
    witnessName,
} from "@/components/reader/provenance";
import { SvaraNotation } from "@/components/reader/svara-notation";
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
        /*
         * "Reused from the Rigveda" named the mechanism. What a reader needs first is that
         * there IS an English rendering here and what licenses it: a published translation
         * of a verse whose Sanskrit this build verified to be the same text. The mechanism
         * still follows, in the source line and the disclosure beneath the quotation.
         */
        return `English rendering via the verified ${vedaAdjective(translation.reused_from_veda)} parallel`;
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

/**
 * "the Rigveda", "the Rigveda and the Yajurveda", "the Rigveda, the Yajurveda and the
 * Atharvaveda". Joining with " and the " alone produced the third case as a chant.
 */
function listCorpora(names: string[]): string {
    const prefixed = names.map((name) => `the ${name}`);
    if (prefixed.length <= 1) return prefixed[0] ?? "";
    return `${prefixed.slice(0, -1).join(", ")} and ${prefixed[prefixed.length - 1]}`;
}

/**
 * How far a fixed phrase travels, in a clause a reader can finish.
 *
 * The occurrence count is the corpus-wide total, so it includes this verse: "in 8 verses"
 * rather than "in 8 other verses", which would be off by one on every row. A null count is
 * omitted rather than rendered as zero - the formula exists, so zero is never the answer.
 */
function formulaReach(formula: {
    occurrence_count?: number | null;
    vedas?: string[] | null;
    match_level?: string | null;
}): string {
    const parts: string[] = [];
    const count = formula.occurrence_count ?? null;
    if (count !== null) parts.push(count === 1 ? "in this verse only" : `in ${count} verses`);
    const vedas = (formula.vedas ?? []).filter(Boolean);
    if (vedas.length > 1) parts.push(`across ${vedas.join(", ")}`);
    else if (vedas.length === 1) parts.push(`within ${vedas[0]}`);
    if (formula.match_level === "SANDHI_INSENSITIVE") parts.push("matched across sandhi");
    return parts.join(" · ");
}

/**
 * The work's name, said rather than shouted.
 *
 * Three of the four works carry their scope in the label itself - "Samaveda Samhita -
 * Kauthuma arcika only (gana corpus NOT included)" - and the upper-case NOT is deliberate
 * where it is written: it is a property on the :Work node, put there so that no surface can
 * print "Samaveda Samhita" over a corpus that is the arcika only. That guard is right and is
 * not touched here.
 *
 * What is wrong is printing it verbatim at the top of a reading page, where it is the first
 * thing a reader meets and reads as a machine label rather than as a statement about the
 * edition. The claim is kept exactly; only its voice changes.
 */
function readableWorkLabel(label: string | null | undefined): string {
    if (!label) return "";
    return label.replace(/NOT included/g, "not included").replace(/ - /, " — ");
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
    const surfaces = reader.text.surfaces ?? [];

    /*
     * The notated Samavedic witness.
     *
     * `PARALLEL_WITNESS` means four different things across the four corpora -- a second
     * Rigvedic edition, an unaccented Yajurvedic or Atharvavedic twin, and in the Samaveda
     * the sasvara text. Measured over the store: all 1,844 Samavedic primary surfaces are
     * unaccented and exactly 1,136 carry an accented PARALLEL_WITNESS, so the pair
     * (veda === "SV", accented) identifies the notation witness and nothing else. The test
     * is deliberately not "is accented", which would promote the Rigvedic and Atharvavedic
     * primary text on every other page.
     */
    const notation =
        reader.veda === "SV"
            ? surfaces.find(
                  (surface) =>
                      surface.surface === "PARALLEL_WITNESS" &&
                      surface.accented === true &&
                      surface.is_displayable !== false &&
                      Boolean(surface.text),
              )
            : undefined;

    /* A surface promoted to its own section is not also an "other witness". */
    const alternates = surfaces.filter(
        (surface) =>
            surface !== notation &&
            surface.is_displayable !== false &&
            surface.text &&
            surface.text !== primary?.text,
    );
    const crossVeda = parallels.ok
        ? (parallels.data.items ?? []).filter((row) => !row.same_veda && row.is_textual_parallelism)
        : [];

    /*
     * One row per counterpart passage, carrying the citation rather than only the corpus it
     * sits in. "This wording also stands in the Rigveda" was true and unusable: a Samavedic
     * verse whose English arrives through RV 6.16.10 should name RV 6.16.10.
     */
    const elsewhere = [
        ...crossVeda
            .reduce((rows, row) => {
                const rowKey = row.passage.canonical_key;
                rows.set(rowKey, {
                    key: rowKey,
                    citation:
                        row.passage.canonical_citation ?? row.passage.display_label ?? rowKey,
                    veda: row.passage.veda,
                });
                return rows;
            }, new Map<string, { key: string; citation: string; veda: string }>())
            .values(),
    ];
    const formulas = reader.formulas?.items ?? [];
    const script = primary?.script === "DEVANAGARI" ? "DEVANAGARI" : "IAST";

    return (
        <div className="va-reader">
            <nav aria-label="Passage location" className="va-reader-where">
                <Link href={`/vedas/${workSlugs[reader.veda] ?? "rigveda"}`}>
                    {readableWorkLabel(reader.work_display_label)}
                </Link>
                {/* The Samavedic collection slot holds a NAME where every other level holds an
                    ordinal, and the graph stores that name in upper case because it is a key.
                    Printed raw it read as shouting; printed with its diacritics it reads as the
                    section of the Samhita the reader is standing in. */}
                {reader.breadcrumbs?.map((crumb) => (
                    <span key={crumb.canonical_key} style={{ display: "contents" }}>
                        <span aria-hidden="true">/</span>
                        <Link href={`/passage/${encoded(crumb.canonical_key ?? "")}`}>
                            <em>
                                {crumbLevelName(reader.veda, crumb.level_key, crumb.native_label)}
                            </em>
                            <strong>
                                {crumbValue(reader.veda, crumb.level_key, crumb.value)}
                            </strong>
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
                                <span title={primary.witness_id ?? undefined}>
                                    {script === "DEVANAGARI" ? "Devanagari" : "Romanised"}
                                    {primary.accented ? ", accented" : ""}
                                    {witnessName(primary.witness_id)
                                        ? ` · ${witnessName(primary.witness_id)}`
                                        : ""}
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
                            {/* Who printed this text and under what licence, beneath the text
                                rather than in a panel elsewhere. It is one line because a
                                reader needs it once, not because it is unimportant. */}
                            {provenanceLine(primary) ? (
                                <p className="va-reader-provenance">{provenanceLine(primary)}</p>
                            ) : null}
                        </section>
                    ) : (
                        <KnowledgeStatus status={reader.text.data_status} />
                    )}

                    {recitation ? (
                        <RecitationPlayer key={recitation.audio_id} track={recitation} />
                    ) : null}

                    {notation?.text ? (
                        <SvaraNotation
                            /* The notated text and the mūla text come from the same edition
                               for every Samavedic verse held here, so repeating the source
                               and licence under both prints the same line twice on one
                               screen. It is stated again only when it differs. */
                            provenance={
                                provenanceLine(notation) === provenanceLine(primary)
                                    ? null
                                    : provenanceLine(notation)
                            }
                            text={notation.text}
                            witness={witnessName(notation.witness_id)}
                        />
                    ) : reader.veda === "SV" ? (
                        /*
                         * One line, and no number in it. The previous copy printed the
                         * withheld count and the names of three internal gates on the verse
                         * page, which is a release-management fact wearing a reader's
                         * clothes. What the reader needs is that this verse has no notated
                         * witness and that the shape of that absence is documented.
                         */
                        <p className="va-reader-absence">
                            No notated witness is linked to this verse.{" "}
                            <Link href="/limits">What is not held</Link>
                        </p>
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
                                        <span title={surface.witness_id ?? undefined}>
                                            {witnessName(surface.witness_id) ??
                                                "Witness not identified"}
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
                                        {/*
                                         * The parallel this English was taken from is a
                                         * citation, and a citation belongs next to the text
                                         * it licenses rather than inside a disclosure the
                                         * reader has to open. It is printed before the
                                         * explanation for the same reason the kind label is
                                         * printed before the quotation.
                                         */}
                                        {translation.reused_from_citation && (
                                            <p className="va-translation-source translation-source">
                                                Rendered from{" "}
                                                <Link
                                                    href={`/passage/${encoded(translation.reused_from_passage_key ?? "")}`}
                                                >
                                                    {translation.reused_from_citation}
                                                </Link>
                                            </p>
                                        )}
                                        {/*
                                         * A reused rendering's disclosure is two sentences and
                                         * is the ordinary case for a Samavedic verse, so it is
                                         * set as a note rather than raised into a bordered
                                         * caveat: on those pages the caveat box was the largest
                                         * object on the screen. The three genuinely exceptional
                                         * shapes keep the box.
                                         */}
                                        {translation.disclosure &&
                                            (translation.coverage_kind === "REUSED_RENDERING" ? (
                                                <p className="va-reader-origin">
                                                    {translation.disclosure}
                                                </p>
                                            ) : (
                                                <Caveat title={disclosureTitle(translation)}>
                                                    {translation.disclosure}
                                                </Caveat>
                                            ))}
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
                            /*
                             * One sentence, and it is about this verse.
                             *
                             * What stood here was a status block quoting the whole corpus's
                             * translation census, which on a Samavedic page is the ordinary
                             * case and therefore the loudest thing on nine pages in ten. The
                             * census is not wrong and it has not been deleted -- it is on
                             * /limits, where a reader goes to ask that question, rather than
                             * in front of the verse they came to read.
                             */
                            <p className="va-reader-absence">
                                No English rendering is linked to this verse.{" "}
                                <Link href="/limits">What is not held</Link>
                            </p>
                        )}
                    </section>

                    {elsewhere.length > 0 && (
                        <section aria-labelledby="va-reader-elsewhere-heading" className="va-reader-elsewhere">
                            <h2 className="va-reading-heading" id="va-reader-elsewhere-heading">
                                This wording also stands in{" "}
                                {listCorpora(
                                    [
                                        ...new Set(
                                            elsewhere.map((row) => vedaNames[row.veda]),
                                        ),
                                    ].filter(Boolean),
                                )}
                            </h2>
                            {/* The citation, not just the corpus. 1,662 of the 1,844 Samavedic
                                verses are linked to a Rigvedic counterpart, and on the 173 that
                                carry a reused rendering this is the verse the English came
                                from -- naming it is the difference between a fact and a lead. */}
                            <ul className="va-reader-elsewhere-list">
                                {elsewhere.slice(0, 6).map((row) => (
                                    <li key={row.key}>
                                        <Link href={`/passage/${encoded(row.key)}`}>
                                            {row.citation}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                            <Link
                                className="va-reader-elsewhere-more"
                                href={`/reuse/${encoded(reader.canonical_key)}`}
                            >
                                Compare the texts side by side, with what each witness reads and how
                                the connection was established
                            </Link>
                        </section>
                    )}

                    {formulas.length > 0 && (
                        /*
                         * The formula layer, which the reader payload did not carry until this
                         * pass and which 10,574 mantras have something in.
                         *
                         * It earns a place on the page for the Samaveda in particular. A
                         * Samavedic verse has no seer, no metre and no ascribed deity - those
                         * three layers are Rigveda-only - so besides the text and its Rigvedic
                         * counterpart, its shared wording is most of what there is to read
                         * about it. 1,311 of the 1,844 carry at least one.
                         *
                         * The match level travels with each phrase rather than being averaged
                         * away: the layer is a normalised-string match, SCRIPT_FOLDED is a
                         * closer reading than SANDHI_INSENSITIVE, and a row that showed both
                         * as "shares this phrase" would spend a distinction the edge recorded.
                         */
                        <section aria-labelledby="va-reader-formulae-heading" className="va-reader-formulae">
                            <h2 className="va-reading-heading" id="va-reader-formulae-heading">
                                Fixed phrases in this verse
                            </h2>
                            <ul className="va-reader-formulae-list">
                                {formulas.slice(0, 6).map((formula) => (
                                    <li key={formula.formula_id}>
                                        <Link href={`/formula-families/${encoded(formula.formula_id)}`}>
                                            <span className="va-reader-formula-form" lang="sa">
                                                {formula.source_form || formula.display_form}
                                            </span>
                                        </Link>
                                        <span className="va-reader-formula-reach">
                                            {formulaReach(formula)}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                            <p className="va-reader-formulae-note">
                                Phrases are matched on a normalised Sanskrit surface, so a
                                match is shared wording and not a claim about which verse
                                said it first.
                            </p>
                        </section>
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
