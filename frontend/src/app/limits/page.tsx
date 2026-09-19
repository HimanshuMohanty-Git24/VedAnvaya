import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { ScopeRegister } from "@/components/corpus/scope-register";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import {
    load,
    loadCompleteness,
    vedaNames,
    vedaOrder,
    type Capabilities,
    type Stats,
    type WorksResponse,
} from "@/lib/api";
import { pageMetadata } from "@/lib/site";

export const revalidate = 300;

export const metadata = pageMetadata({
    title: "Scope and limits",
    description:
        "What this edition covers and what it does not: the recensions held, translation and recitation coverage, notation scope, evidence layers, and the questions the current build refuses to answer.",
    pathname: "/limits",
});

/**
 * The one page where the boundaries are stated in full.
 *
 * Every other surface in the product states scope in a clause and links here. That is a
 * deliberate division of labour and it has a failure mode in each direction: a product that
 * repeats its limitations on every page reads as an apology, and a product that states them
 * nowhere is dishonest. So they are stated once, at length, in the register of a scholarly
 * statement of scope rather than an engineering incident report.
 *
 * TONE RULES FOR THIS PAGE. No sprint identifiers, no gate names, no internal work-item codes.
 * A reader here is a scholar deciding whether this corpus can support their question, not an
 * engineer triaging a backlog. Where an internal process is the reason for a boundary, the
 * boundary is described by what it means for the reader -- "held back until each recording has
 * been listened to" rather than the name of the queue it is held in.
 *
 * WHERE THE FIGURES COME FROM. The corpus rows, their exclusions, the corpus totals and the
 * live translation totals are read from `/works` and `/stats`; every recitation figure is read
 * from `/audio/stats`; the translation typology, the notation figures and the Ask benchmark
 * come from the completeness record; the question-level limits are probed by
 * `/insights/capabilities` on the request. The release identifier is at the foot, in the one
 * place on this page where a technical detail belongs.
 *
 * The completeness record also carries a recitation block, and it is deliberately not used:
 * on this build it reports a total and a per-Veda split that disagree with the audio layer's
 * own measurement, with one corpus's recording count equal to that corpus's mantra total. Its
 * review counts -- the owner sample, and the queue held outside the catalogue -- agree with
 * everything else and are used.
 */

const VERDICT_COPY: Record<string, { label: string; note: string }> = {
    NOT_ANSWERABLE: {
        label: "Cannot be answered",
        note: "The dimension this question asks about was never built.",
    },
    PARTIALLY_ANSWERABLE: {
        label: "Partly answerable",
        note: "Some of this can be answered, and the rest would overstate what was built.",
    },
};

/* The exclusion vocabulary moved to `ScopeRegister`, which is the one place that renders
   it now. Two copies of a table mapping a registry code to a reader's word for it is two
   places for the registry to outgrow. */



const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

type AudioStats = {
    total_records: number;
    mapped_scope_keys_by_veda?: Record<string, number>;
    by_publication_tier?: Record<string, number>;
};

function figure(rows: Stats["corpus"] | undefined, name: string): number | null {
    return rows?.find((row) => row.name === name)?.total ?? null;
}

export default async function LimitsPage() {
    const [result, works, stats, audioStats, completeness] = await Promise.all([
        load<Capabilities>("/insights/capabilities"),
        load<WorksResponse>("/works"),
        load<Stats>("/stats"),
        load<AudioStats>("/audio/stats"),
        loadCompleteness(),
    ]);

    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    // Read, never typed. See the caveat below for why.
    const total = data.benchmark_not_answerable_total ?? 0;
    const published = data.benchmark_not_answerable_published ?? 0;
    const unpublished = data.unpublished_not_answerable ?? [];

    const collections = [...(works.ok ? (works.data.items ?? []) : [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );
    const ownTranslations = stats.ok ? figure(stats.data.corpus, "translations") : null;
    const reused = stats.ok ? figure(stats.data.corpus, "reused_renderings") : null;
    const canonicalMantras = stats.ok ? figure(stats.data.corpus, "mantras") : null;

    const trans = completeness.translations;
    const notation = completeness.samaveda_notation;
    const ask = completeness.ask_benchmark;

    /*
     * Recitation figures come from the audio service, never from the completeness record.
     *
     * The record carries its own recitation block and on this build it disagrees with the
     * layer it describes: it reports 17,780 records, with the Rigvedic figure equal to that
     * corpus's entire mantra count, while `/audio/stats` measures 16,834 and 10,402. Its
     * review counts -- the owner sample and the unheard queue -- agree with everything else
     * and are used; its totals are not.
     */
    const recitationTotal = audioStats.ok ? audioStats.data.total_records : null;
    const recitedByVeda: Record<string, number> = audioStats.ok
        ? (audioStats.data.mapped_scope_keys_by_veda ?? {})
        : {};
    /*
     * How many recordings carry an audible review. Absent, this reads as "not stated" rather
     * than as zero: "no recording has been heard" and "we could not ask" are different claims
     * and only one of them belongs in the sentence below.
     */
    const tiers = audioStats.ok ? audioStats.data.by_publication_tier : undefined;
    const earVerified = tiers ? (tiers.RELEASED_VERIFIED ?? 0) : null;
    const review = completeness.audio;

    return (
        <div className="shell page limits-page">
            <PageHeading
                title="Scope and limits"
                description="What this edition covers, how each kind of coverage is established, and where it stops. Every boundary recorded here is a fact about this corpus, never about the Vedas."
            />

            <p className="va-limits-intro">
                This page exists so that the rest of the product does not have to argue. Every
                other surface states its scope in a clause and links here; everything the reader
                needs in order to judge whether a figure can support their question is set out
                below, in one place, at length.
            </p>

            {/* ---------------------------------------------------- the corpus - */}

            <section className="va-scope-section" id="corpus">
                <h2>The corpus</h2>
                <p className="va-scope-lede">
                    {canonicalMantras ? `${number(canonicalMantras)} canonical mantras across` : "Across"}{" "}
                    four Saṃhitās, one recension each. No Brāhmaṇa, Āraṇyaka or Upaniṣad is
                    held, and three of the four Saṃhitās are themselves partial in ways their
                    ordinary names do not reveal. Each row below states the recension held and
                    enumerates what that edition does not address.
                </p>

                {collections.length ? (
                    <>
                        {/*
                         * The same scope register the collections page carries, so a reader
                         * who has met it there recognises it here. It replaces a definition
                         * list that ran every exclusion of an edition into one sentence:
                         * "the Bāṣkala recension; the Rigvedic Brāhmaṇas; the Rigvedic
                         * Āraṇyakas; the Upaniṣads" is four different kinds of absence set
                         * as one, and the Yajurvedic row ran to seven. As a register each
                         * one is a line, and each line says which layer it belongs to.
                         *
                         * Deliberately not a tree. See the note in `ScopeRegister`.
                         */}
                        <ScopeRegister works={collections} />
                        <p className="va-scope-caption">
                            A solid mark is what this build holds. A hollow one is a corpus the
                            registry records as named and outside this edition, so an absence
                            measured here is an absence from the held recension only. The order
                            is the registry&rsquo;s; nothing on this page asserts that any
                            recension descends from any other.
                        </p>
                    </>
                ) : (
                    <p>
                        The per-edition figures could not be read from the knowledge service for
                        this request. The editions themselves are described on{" "}
                        <Link href="/vedas">the collections page</Link>.
                    </p>
                )}

                <div className="va-scope-note">
                    <h3>The two exclusions most likely to mislead</h3>
                    <p>
                        <b>The Yajurveda.</b> In ordinary use the name covers both the White and the
                        Black recensions. This edition holds the White one only, so no Taittirīya,
                        Kāṭhaka, Maitrāyaṇī or Kapiṣṭhala material is present at all, and the prose
                        Brāhmaṇa passages interleaved with the mantras in the Black recensions have
                        no counterpart here.
                    </p>
                    <p>
                        <b>The Sāmavedic gāna.</b> The song collections are a parallel and larger
                        body than the ārcika verse corpus held here, and they are the reason the
                        Samaveda is a distinct Veda rather than a Rigvedic excerpt. Any claim that
                        this product &ldquo;has the Samaveda&rdquo; while holding the ārcika alone
                        would be false, and the ārcika is what is held.
                    </p>
                    <p>
                        Khila additions are outside the canonical counts, and an absence measured in
                        any corpus here is an absence from the recension held, never from the
                        tradition.
                    </p>
                </div>
            </section>

            {/* ----------------------------------------------- translations ---- */}

            <section className="va-scope-section" id="translation">
                <h2>Translation coverage</h2>
                <p className="va-scope-lede">
                    Coverage is typed by provenance rather than counted as one number, because the
                    kinds are not interchangeable: a rendering borrowed from a parallel verse in
                    another corpus is translation assistance and not evidence about the corpus it
                    appears beside.
                </p>

                <dl className="va-scope-figures">
                    <div>
                        <dt>Dedicated English translations</dt>
                        <dd>{number(trans.total_dedicated_english)}</dd>
                    </div>
                    <div>
                        <dt>Multi-verse range translations</dt>
                        <dd>{number(trans.total_range_covered)}</dd>
                    </div>
                    <div>
                        <dt>Reused parallel renderings</dt>
                        <dd>{number(trans.total_reused_rendering)}</dd>
                    </div>
                    <div>
                        <dt>Non-English scholarly notes</dt>
                        <dd>{number(trans.total_non_english)}</dd>
                    </div>
                    <div>
                        <dt>Verses with no English</dt>
                        <dd>{number(trans.total_uncovered)}</dd>
                    </div>
                </dl>

                <div className="va-scope-note">
                    <h3>Every translation here is aligned, not reviewed</h3>
                    <p>
                        The English in this corpus is public-domain scholarly translation matched to
                        a canonical key. Coverage measures that alignment; it does not measure
                        translation quality, and no rendering here has been checked against the
                        Sanskrit by this project.
                    </p>
                    <h3>The Samaveda has no English of its own</h3>
                    <p>
                        Zero of its {number(notation.canonical_corpus_mantras)} verses carry a
                        dedicated translation. {number(trans.by_veda.SV?.reused_rendering)} verses
                        show a published Rigvedic rendering against text verified
                        character-identical, disclosed as reuse and never counted as Samavedic
                        English; {number(trans.by_veda.SV?.uncovered)} verses carry none. The
                        consequence runs further than the count: every layer derived from a
                        corpus&rsquo;s English translation is absent for the Samaveda rather than
                        empty in it, so a zero returned from such a layer is a statement about this
                        build and not about the text.
                    </p>
                    {ownTranslations && reused ? (
                        <p className="va-scope-measured">
                            Measured live on this request: {number(ownTranslations)} own-corpus
                            English renderings and {number(reused)} reused renderings, reported
                            apart and never summed.
                        </p>
                    ) : null}
                </div>
            </section>

            {/* ------------------------------------------------- recitation ---- */}

            <section className="va-scope-section" id="recitation">
                <h2>Recitation</h2>
                <p className="va-scope-lede">
                    Audio is a product layer over the text rather than part of the knowledge model.
                    No recording is republished here: each is streamed from its source at the moment
                    it is played, and a recording whose source numbers its verses by a different
                    recension is rejected rather than approximately aligned.
                </p>

                <dl className="va-scope-figures">
                    <div>
                        <dt>Catalogued recordings</dt>
                        <dd>{number(recitationTotal) ?? "not read"}</dd>
                    </div>
                    {Object.entries(recitedByVeda)
                        .sort(([a], [b]) => (vedaOrder[a] ?? 9) - (vedaOrder[b] ?? 9))
                        .map(([code, count]) => (
                            <div key={code}>
                                <dt>{vedaNames[code] ?? code}</dt>
                                <dd>{count === 0 ? "none" : number(count)}</dd>
                            </div>
                        ))}
                    {earVerified !== null ? (
                        <div>
                            <dt>Verified by ear</dt>
                            <dd>{earVerified === 0 ? "none" : number(earVerified)}</dd>
                        </div>
                    ) : null}
                </dl>

                <div className="va-scope-note">
                    <h3>A checked mapping is not an audible review</h3>
                    <p>
                        This is the distinction to carry away from this section.{" "}
                        {recitationTotal ? `All ${number(recitationTotal)} ` : "The "}catalogued
                        recordings are published because their mapping was checked — the
                        source&rsquo;s own verse coordinates resolve to our canonical key, the
                        Sanskrit matches this corpus&rsquo;s text, and the media resolves — and
                        not because anyone has listened to them.{" "}
                        {earVerified === 0
                            ? "None of them carries an audible review, and the total should never be described as human-verified."
                            : "The figure above states how many carry an audible review."}
                    </p>
                    <p>
                        What the check does rule out is the failure that matters most: a recording
                        whose source numbers its verses by a different recension is rejected rather
                        than approximately aligned, because playing the wrong verse is worse than
                        playing nothing.
                    </p>
                    <h3>What has been heard</h3>
                    <p>
                        An owner sample of {review.owner_sample_reviewed} recordings was listened to
                        in full, with {review.owner_sample_verified} verified and{" "}
                        {review.owner_sample_rejected} rejected. A separate queue of{" "}
                        {number(review.queue_total)} recordings is held outside the catalogue, of
                        which {number(review.not_individually_heard)} have not been listened to
                        individually; none has been promoted into the published catalogue.
                    </p>
                    <h3>No Samavedic recording is catalogued at all</h3>
                    <p>
                        The Samaveda is the one Veda defined by its sung realisation, which makes
                        this the most conspicuous gap in the layer — and it is a gap in what has
                        been published here, not a statement about the tradition.
                    </p>
                </div>
            </section>

            {/* --------------------------------------------------- notation ---- */}

            <section className="va-scope-section" id="notation">
                <h2>Sāmavedic notation</h2>
                <p className="va-scope-lede">
                    The ārcika carries svara marks that record how a verse was pitched. They are
                    held as what the printed witness prints, verse by verse, and never extrapolated
                    into sung pitches.
                </p>

                <dl className="va-scope-figures">
                    <div>
                        <dt>Verses with a validated notation witness</dt>
                        <dd>{number(notation.validated_notation_witnesses)}</dd>
                    </div>
                    <div>
                        <dt>Verses awaiting textual alignment</dt>
                        <dd>{number(notation.unaligned_withheld_verses)}</dd>
                    </div>
                    <div>
                        <dt>Gāna works modelled</dt>
                        <dd>{notation.gana_works_modeled === 0 ? "none" : notation.gana_works_modeled}</dd>
                    </div>
                </dl>

                <div className="va-scope-note">
                    <h3>A mark is not a melody</h3>
                    <p>
                        Each released witness is a source-explicit reading: the marks as one named
                        witness prints them, verified to map to exactly one verse. The Kauthuma
                        decipherment authority — the tradition that would turn those marks into
                        pitches — is not held in this build, so the tone marks are stored as
                        codepoints and no melody is ever reconstructed from them.
                    </p>
                    <p>
                        The remaining {number(notation.unaligned_withheld_verses)} verses are held
                        back because their printed run could not yet be aligned to a canonical key
                        with certainty. The gāna song collections are outside this edition
                        altogether.
                    </p>
                </div>
            </section>

            {/* -------------------------------------------- evidence layers ---- */}

            <section className="va-scope-section" id="evidence">
                <h2>Evidence layers, and where each one reaches</h2>
                <p className="va-scope-lede">
                    Every claim carries the layer it came from, and a weaker layer is never promoted
                    by being displayed beside a stronger one. The four grades, and what each can
                    carry, are described on <Link href="/sources">the sources page</Link>.
                </p>

                <div className="va-scope-note">
                    <h3>Several layers reach some collections and not others</h3>
                    <p>
                        The deity ascription that resolves to a named god comes from the
                        Anukramaṇī, and that apparatus covers the Rigveda. The Atharvaveda has its
                        own index, which records descriptive phrases rather than registry names, so
                        the two are not one layer. The metre layer reaches the Rigveda and the
                        Atharvaveda and neither of the other two. Where a layer has no edge into a
                        corpus, this product answers &ldquo;not built&rdquo; rather than zero.
                    </p>
                    <h3>Ascribed and named are different claims</h3>
                    <p>
                        What the traditional index assigns to a hymn is never shown as a statement
                        the Sanskrit makes. Where a hymn&rsquo;s label has been projected onto the
                        verses inside it, the projection is marked on the row, so a per-verse claim
                        is never built from a container&rsquo;s label — most Atharvavedic seer
                        attributions are of that kind, and the Yajurvedic ones are not.
                    </p>
                    <h3>Deity mentions are graded, and the ambiguous ones are withheld</h3>
                    <p>
                        Vedic Sanskrit has one word for the god Agni and for fire. Every mention is
                        graded certain, probable or ambiguous; the ambiguous ones are excluded from
                        default figures, all three counts are always reported, and a passage in
                        which every mention is ambiguous returns insufficient evidence rather than
                        an empty list.
                    </p>
                    <h3>Lexical counts are minima</h3>
                    <p>
                        A count of verses in which a registered alias occurs is a floor, not a
                        census: an unregistered spelling is simply not counted. Where a cell is
                        known to understate for this reason it is labelled rather than silently
                        corrected. The mention layer is also not one instrument — Rigvedic mentions
                        come from a manual scholarly lemma annotation and the other three corpora
                        from surface matching — so comparing a Rigvedic rate with an Atharvavedic
                        one compares two methods as well as two texts.
                    </p>
                    <h3>Non-lexical resemblance was never built</h3>
                    <p>
                        There is no embedding, no vector index and no asserted semantic similarity
                        anywhere in this graph. Cross-corpus relatedness here is textual, and that
                        is a fact about the method rather than a finding about the Vedas.
                    </p>
                    <h3>Nothing in the derived layers has been reviewed by a person</h3>
                    <p>
                        The assertion layer is derived by rule from scholarly annotation, with a
                        minority extracted by a language model; none of it has been read by a human
                        reviewer, and its coverage is uneven across the four corpora. It is usable
                        for a single passage and not as a corpus-level comparison. The interpretive
                        claims in the build are permanently marked as candidates and each records
                        the observation that would falsify it.
                    </p>
                </div>
            </section>

            {/* -------------------------------------------------------- ask ---- */}

            <section className="va-scope-section" id="ask">
                <h2>Ask</h2>
                <p className="va-scope-lede">
                    Retrieval runs first, over a fixed catalogue of channels, and the language model
                    sees only what retrieval returned. Every factual sentence carries a citation
                    that resolves to a passage in this corpus.
                </p>

                <dl className="va-scope-figures">
                    <div>
                        <dt>Benchmark questions</dt>
                        <dd>{ask.total_questions}</dd>
                    </div>
                    <div>
                        <dt>Acceptable outcomes</dt>
                        <dd>{ask.effective_acceptable}</dd>
                    </div>
                    <div>
                        <dt>Honestly refused</dt>
                        <dd>{ask.insufficient_evidence_refused}</dd>
                    </div>
                    <div>
                        <dt>Misleading</dt>
                        <dd>{ask.misleading}</dd>
                    </div>
                    <div>
                        <dt>Invented</dt>
                        <dd>{ask.hallucinated}</dd>
                    </div>
                </dl>

                <div className="va-scope-note">
                    <h3>What it will not do</h3>
                    <p>
                        A question this build cannot reach returns insufficient evidence and names
                        the dimension it could not reach. It does not guess, and it does not turn a
                        gap in the graph into a confident denial about the Vedas. Of the{" "}
                        {ask.total_questions} benchmark questions,{" "}
                        {ask.insufficient_evidence_refused} were answered that way, which is the
                        correct outcome rather than a shortfall.
                    </p>
                    <h3>The prose depends partly on the configured model</h3>
                    <p>
                        Retrieval and citation validation are deterministic and run the same way
                        every time. The sentences between them are generated, and a different model
                        will write different sentences over the same evidence.
                    </p>
                </div>
            </section>

            {/* ------------------------------------------ probed limits ------- */}

            <section className="va-scope-section" id="questions">
                <h2>Questions this build cannot answer</h2>
                <p className="va-scope-lede">
                    {published} of the {total} questions the benchmark grades unanswerable are
                    catalogued below, each with a probe that runs on this request and a question
                    that can be answered instead.
                </p>

                <Caveat
                    title="This catalogue is not a complete account of what this atlas cannot do"
                    tone="boundary"
                >
                    It covers every question the hundred-question benchmark graded unanswerable
                    {unpublished.length > 0
                        ? ` except ${unpublished.length} still unpublished`
                        : ""}
                    . The benchmark is a hundred questions rather than every question, so a question
                    absent from this list is not thereby answerable.
                </Caveat>

                <div className="limit-list">
                    {data.limits?.map((limit) => {
                        const verdict = VERDICT_COPY[limit.verdict] ?? {
                            label: limit.verdict,
                            note: "",
                        };
                        return (
                            <article className="limit-card" key={limit.limit_id}>
                                <header>
                                    <div>
                                        <span
                                            className={`verdict verdict-${limit.verdict.toLowerCase()}`}
                                        >
                                            {verdict.label}
                                        </span>
                                        <h3>{limit.question}</h3>
                                    </div>
                                    <KnowledgeStatus status={limit.data_status} compact />
                                </header>

                                <div className="limit-body">
                                    <section>
                                        <h4>Why</h4>
                                        <p>{limit.why}</p>
                                    </section>
                                    <section>
                                        <h4>What this is not</h4>
                                        <p>{limit.what_this_is_not}</p>
                                    </section>
                                </div>

                                {limit.measurements?.length ? (
                                    <table className="limit-measurements">
                                        <caption className="sr-only">
                                            Measurements behind this limit
                                        </caption>
                                        <tbody>
                                            {limit.measurements.map((measurement) => (
                                                <tr key={measurement.name}>
                                                    <th scope="row">
                                                        {measurement.name.replaceAll("_", " ")}
                                                    </th>
                                                    <td>{measurement.value?.toLocaleString()}</td>
                                                    <td>{measurement.means}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : null}

                                {limit.safe_alternative && (
                                    <p className="limit-alternative">
                                        <strong>Ask this instead</strong>
                                        {limit.safe_alternative}
                                    </p>
                                )}
                            </article>
                        );
                    })}
                </div>
            </section>

            {/*
             * The one place on this page where an internal identifier belongs, and it is one
             * line: the release the figures above were certified against, so a reader who wants
             * to reproduce them knows which build to reproduce.
             */}
            <section className="va-limits-appendix" id="release">
                <h2>Technical detail</h2>
                <p>
                    The translation typology, the notation figures and the Ask benchmark come from
                    the completeness record certified against release{" "}
                    <code>
                        {completeness.certified_release_commit?.slice(0, 12) ?? "unrecorded"}
                    </code>
                    , read{" "}
                    {completeness.data_source === "fallback"
                        ? "from the copy pinned in this build because the service did not answer"
                        : "from the knowledge service on this request"}
                    . The per-edition rows, their exclusions, the corpus and translation totals and
                    every recitation figure are read from the knowledge service when this page is
                    built, and the question-level probes above run on the request.
                </p>
                <p>
                    <Link className="text-link" href="/sources">
                        How each kind of evidence is established
                    </Link>
                </p>
            </section>

            <CaveatList caveats={data.caveats} title="How this catalogue was built" />
        </div>
    );
}
