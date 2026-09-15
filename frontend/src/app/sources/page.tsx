import Link from "next/link";
import type { Metadata } from "next";
import { ArrowSquareOut } from "@phosphor-icons/react/dist/ssr";
import {
    encoded,
    load,
    vedaNames,
    vedaOrder,
    workSlugs,
    type AudioStats,
    type Capabilities,
    type DevataInsight,
    type WorksResponse,
} from "@/lib/api";
import { count } from "@/lib/lab";
import { readProvenance, type ProvenanceEntry } from "@/lib/provenance";
import { pageMetadata } from "@/lib/site";

/**
 * Sources and method.
 *
 * One page rather than two. A reader who wants to know where a verse came from and a reader
 * who wants to know what "PROBABLE" means are usually the same reader two minutes apart, and
 * splitting them means each arrives at the half that does not answer the question they have.
 * `/methodology` redirects here.
 *
 * The source inventory is generated. Every title, editor, edition, date, licence and URL is
 * read from `public/data/provenance.json`, which `scripts/build_frontend_provenance.py`
 * derives from the committed registries and refuses to write if a shipped artifact is
 * unaccounted for. Nothing on this page names a source that the build does not use, and
 * nothing the build uses is missing from it.
 *
 * The worked example in the attribution section is live. It reads one deity from the API and
 * prints the actual figures, because an example with invented numbers in it teaches the
 * reader that the numbers here are illustrative.
 */

export const revalidate = 3600;

export const metadata: Metadata = pageMetadata({
    title: "Sources & Methodology",
    description:
        "The editions behind this corpus, their terms, and the evidence model that turns text into accountable connections.",
    pathname: "/sources",
});

const CONTENTS = [
    { id: "scope", label: "What is in this corpus" },
    { id: "method-layers", label: "Four kinds of knowledge" },
    { id: "method-attribution", label: "Named, and dedicated to" },
    { id: "method-certainty", label: "Certain, probable, ambiguous" },
    { id: "method-relationships", label: "Kinds of connection" },
    { id: "method-ask", label: "How Ask works" },
    { id: "method-audio", label: "Recitation" },
    { id: "limitations", label: "Known limitations" },
    { id: "sources", label: "The sources" },
];

/**
 * The four evidence layers, in the reader's words.
 *
 * The technical names are kept beside the editorial ones rather than replaced by them,
 * because the technical names are what appear on the API and in the graph. A reader who
 * learns "source-explicit" here and meets `SOURCE_EXPLICIT` in a response should recognise it.
 */
const LAYERS: { label: string; technical: string; body: string }[] = [
    {
        label: "What a source says",
        technical: "Source-explicit",
        body: "The text itself, and the statements an edition or a traditional index makes about it. The verse, its number, the seer and deity its Anukramani names, the translator's English. These are quotations, and the strongest thing this product holds.",
    },
    {
        label: "What follows from it by rule",
        technical: "Deterministically derived",
        body: "Anything a stated rule computes from the layer above, the same way every time. A hymn's deity projected down onto its verses, a citation resolved into a canonical key, two verses matched as carrying the same normalised wording. Reproducible, checkable, and no stronger than the rule that produced it.",
    },
    {
        label: "What a model extracted",
        technical: "Semantic or model-assisted",
        body: "Statements pulled out of a translation by a language model and kept as candidates. Every one is marked, none is treated as a source statement, and this layer reaches the Rigveda only. It is the smallest layer here and the one held at the greatest distance.",
    },
    {
        label: "What someone concluded",
        technical: "Interpretive claim",
        body: "A reading of the data, recorded with the observation that would falsify it. There are six of these in the whole build, they are permanently marked as candidates, and they are never displayed in the same style as a count.",
    },
];

const CERTAINTIES: { label: string; body: string }[] = [
    {
        label: "CERTAIN",
        body: "The word in the verse names this deity and nothing else plausibly. Included in every default figure.",
    },
    {
        label: "PROBABLE",
        body: "The reading is very likely but the form is shared with something else, or the context is doing the work. Included in default figures, and counted separately so you can remove it.",
    },
    {
        label: "AMBIGUOUS",
        body: "The word could equally be the god or the ordinary noun, and nothing decides it. Excluded from every default figure. The standing example is Agni: Vedic Sanskrit uses one word for the god and for fire, and the same problem recurs wherever a deity is named after the thing it is.",
    },
];

const RELATIONSHIPS: { label: string; body: string }[] = [
    {
        label: "Exact parallel",
        body: "The same verse, word for word, in two places. The strongest textual relationship here and the least common.",
    },
    {
        label: "Near parallel",
        body: "Closely similar wording that stops short of identity — a changed word, a different ending, an inserted particle.",
    },
    {
        label: "Text reuse",
        body: "One verse carries another's wording, with the direction recorded. Direction is expensive to establish and exists here for one corpus pair.",
    },
    {
        label: "Variant",
        body: "The same verse with edition-level differences. A fact about how the text was transmitted rather than about how it was composed.",
    },
    {
        label: "Formula family",
        body: "A fixed phrase, plus the longer lines that contain it and the slightly different lines that echo it. Built by normalised string match over the whole corpus.",
    },
    {
        label: "Shared vocabulary",
        body: "Two verses name the same registered entities. This is the weakest relationship in the set and the one most easily mistaken for the others: it says nothing at all about shared wording.",
    },
    {
        label: "Semantic assertion",
        body: "A statement about a verse extracted by a model from its translation. Rigvedic only, permanently marked as a candidate, and never counted as a textual relationship.",
    },
];

/** Licence strings, in words a reader does not have to decode. */
const RIGHTS_LABEL: Record<string, string> = {
    PUBLIC_DOMAIN: "Public domain",
    CC_BY: "Creative Commons BY",
    CC_BY_SA: "Creative Commons BY-SA",
    CC_BY_NC_SA: "Creative Commons BY-NC-SA",
    APACHE_2_0: "Apache 2.0",
    PERMISSION_REQUIRED: "Permission required — referenced, not reproduced",
    REFERENCE_ONLY: "No licence granted — referenced, not redistributed",
    UNKNOWN: "No licence statement established",
};

function rightsLabel(status: string | null | undefined) {
    if (!status) return RIGHTS_LABEL.UNKNOWN;
    return RIGHTS_LABEL[status] ?? status.replaceAll("_", " ").toLowerCase();
}

export default async function SourcesPage() {
    const [provenance, works, capabilities, audio, indra] = await Promise.all([
        readProvenance(),
        load<WorksResponse>("/works"),
        load<Capabilities>("/insights/capabilities"),
        load<AudioStats>("/audio/stats"),
        load<DevataInsight>(`/insights/devatas/${encoded("VG:DEVATA:INDRAH")}`),
    ]);

    const collections = [...(works.ok ? (works.data.items ?? []) : [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );
    const limits = capabilities.ok ? (capabilities.data.limits?.length ?? null) : null;
    const audioStats = audio.ok ? audio.data : null;
    const example = indra.ok ? indra.data : null;
    const precision = example?.derived_metrics?.find(
        (row) => row.metric_name === "DEVATA_ATTRIBUTION_PRECISION",
    );
    const inherited = precision?.values?.container_inherited;
    const perPassage = precision?.values?.per_passage;

    /* Named rather than counted in prose: a sentence that says "two sources" and then lists
       one is how a page stops being checkable. */
    const consulted = provenance.entries.filter((entry) => entry.layer === "comparison");

    const byLayer = new Map<string, ProvenanceEntry[]>();
    for (const entry of provenance.entries) {
        byLayer.set(entry.layer, [...(byLayer.get(entry.layer) ?? []), entry]);
    }

    return (
        <div className="va-doc">
            <header className="va-doc-head">
                <p className="va-doc-eyebrow">Sources and method</p>
                <h1>Where this comes from, and what it is allowed to claim.</h1>
                <p className="va-doc-lede">
                    Every verse on this site came from a named electronic edition, held under stated
                    terms, and every figure derived from it belongs to one of four kinds of
                    knowledge that are never mixed. This page is both halves of that: the editions,
                    and the rules.
                </p>
            </header>

            <div className="va-doc-layout">
                <nav aria-label="Contents" className="va-doc-contents">
                    <h2>On this page</h2>
                    <ol>
                        {CONTENTS.map((item) => (
                            <li key={item.id}>
                                <a href={`#${item.id}`}>
                                    <span>{item.label}</span>
                                </a>
                            </li>
                        ))}
                    </ol>
                </nav>

                <div className="va-doc-body">
                    <section id="scope">
                        <h2>What is in this corpus</h2>
                        <p className="va-doc-open">
                            Four Samhitas, one recension each. No Brahmana, no Aranyaka, no
                            Upanisad, for any of them. Three of the four are missing a body of
                            material that their ordinary name covers, and in one case that missing
                            body is larger than what is held.
                        </p>
                        {collections.length ? (
                            <dl className="va-doc-terms">
                                {collections.map((work) => {
                                    const code = work.veda ?? "";
                                    const registryWork = provenance.works.find(
                                        (row) => row.veda === code,
                                    );
                                    return (
                                        <div key={work.work_id}>
                                            <dt>
                                                <Link href={`/vedas/${workSlugs[code] ?? ""}`}>
                                                    {vedaNames[code] ?? work.traditional_name}
                                                </Link>
                                                <small>
                                                    {registryWork?.recension ?? work.recension}
                                                </small>
                                            </dt>
                                            <dd>
                                                {count(work.mantra_count)} verses,{" "}
                                                {count(work.translated_mantra_count)} with an
                                                English translation. Not held:{" "}
                                                {(work.excluded_corpora ?? [])
                                                    .map((item) =>
                                                        item.toLowerCase().replaceAll("_", " "),
                                                    )
                                                    .join("; ")}
                                                .
                                            </dd>
                                        </div>
                                    );
                                })}
                            </dl>
                        ) : (
                            <p>
                                The corpus figures could not be read from the knowledge service for
                                this request. The editions themselves are listed{" "}
                                <a href="#sources">below</a>.
                            </p>
                        )}
                        <p>
                            The exclusion most likely to mislead is the Yajurveda. In ordinary use
                            &ldquo;the Yajurveda&rdquo; covers both the White and the Black
                            recensions; this build holds the White one only, so no Taittiriya,
                            Kathaka, Maitrayani or Kapisthala material is present at all. The
                            Samavedic one is the largest in absolute terms: the gana song-books are
                            a parallel and bigger body than the verse collection held here, and they
                            are the reason the Samaveda is a distinct Veda rather than a Rigvedic
                            excerpt.
                        </p>
                    </section>

                    <section id="method-layers">
                        <h2>Four kinds of knowledge</h2>
                        <p>
                            Everything this product knows sits in one of four layers, and the layer
                            is attached to the claim rather than assumed from context. They are
                            ordered by how much weight they can carry, strongest first.
                        </p>
                        <dl className="va-doc-terms">
                            {LAYERS.map((layer) => (
                                <div key={layer.technical}>
                                    <dt>
                                        {layer.label}
                                        <small>{layer.technical}</small>
                                    </dt>
                                    <dd>{layer.body}</dd>
                                </div>
                            ))}
                        </dl>
                        <p>
                            The rule that matters is that a lower layer never gets promoted by being
                            displayed next to a higher one.{" "}
                            <Link href="/insights">The evidence page</Link> renders the three
                            quantitative layers in visibly different styles for exactly this reason,
                            and the visualizations mark an interpretation as an interpretation even
                            when it is the obvious reading of the bars above it.
                        </p>
                    </section>

                    <section id="method-attribution">
                        <h2>Named, and dedicated to</h2>
                        <p className="va-doc-open">
                            This is the single most important distinction on the site, and it is the
                            one most often collapsed elsewhere.
                        </p>
                        <p>
                            A deity being <b>named</b> in a verse and a hymn being <b>dedicated</b>{" "}
                            to that deity are two different records. The first is a fact about the
                            words: the verse says the name. The second is a fact about the
                            tradition&rsquo;s own index: the Anukramani states which god the hymn
                            belongs to. A hymn dedicated to Indra can run for ten verses without
                            saying his name, and a verse can name six gods while being dedicated to
                            none of them.
                        </p>
                        <p>
                            They also have different scopes, and this is where a merged count goes
                            wrong. The naming layer reaches all four collections. The traditional
                            ascription exists for the Rigveda. So a merged &ldquo;Indra count&rdquo;
                            would be four collections of one measure plus one collection of another,
                            and a zero for the Atharvaveda would look like a statement about the
                            Atharvaveda when it is a statement about which collections have a
                            surviving index in this build.
                        </p>
                        {example ? (
                            <div className="va-doc-example">
                                <h3>Worked example, read live from the knowledge service</h3>
                                <dl>
                                    <div>
                                        <dt>{example.display_label}, named in</dt>
                                        <dd>
                                            {count(example.named_total)} verses, across{" "}
                                            {example.coverage?.vedas_in_scope?.length ?? 4}{" "}
                                            collections
                                        </dd>
                                    </div>
                                    <div>
                                        <dt>{example.display_label}, dedicated to by</dt>
                                        <dd>
                                            {count(example.ascribed_total)} verses, in{" "}
                                            {(example.ascribed_scope ?? []).join(", ") ||
                                                "one collection"}{" "}
                                            only
                                        </dd>
                                    </div>
                                    {typeof inherited === "number" &&
                                    typeof perPassage === "number" ? (
                                        <>
                                            <div>
                                                <dt>Of those, stated verse by verse</dt>
                                                <dd>{count(perPassage)} verses</dd>
                                            </div>
                                            <div>
                                                <dt>Inherited from the hymn&rsquo;s label</dt>
                                                <dd>{count(inherited)} verses</dd>
                                            </div>
                                        </>
                                    ) : null}
                                </dl>
                                <p>
                                    The last two rows are a second distinction inside the first.
                                    Most ascriptions are not statements about a verse at all: they
                                    are the hymn&rsquo;s label, projected down onto the verses
                                    inside it by a stated rule. That projection is reproducible and
                                    it is derived, not source-explicit, so every ascription on this
                                    site carries which of the two it is.
                                </p>
                            </div>
                        ) : null}
                        <p>
                            <Link href="/visualizations/deities">
                                The deities plate draws the two side by side
                            </Link>{" "}
                            and never on one axis.
                        </p>
                    </section>

                    <section id="method-certainty">
                        <h2>Certain, probable, ambiguous</h2>
                        <p>
                            Deciding that a word in a verse refers to a god is not always
                            straightforward, because in Vedic Sanskrit the god and the thing often
                            share a name. Every mention carries one of three grades.
                        </p>
                        <dl className="va-doc-terms">
                            {CERTAINTIES.map((grade) => (
                                <div key={grade.label}>
                                    <dt>{grade.label}</dt>
                                    <dd>{grade.body}</dd>
                                </div>
                            ))}
                        </dl>
                        <p>
                            Default figures are CERTAIN plus PROBABLE. All three counts are always
                            available, and the ambiguous tier can be switched on where it is offered
                            — labelled, because a figure that includes it is an upper bound rather
                            than a count.
                        </p>
                        <h3>Why this site sometimes says it cannot establish something</h3>
                        <p>
                            An empty result has at least three meanings and they are not
                            interchangeable. The thing genuinely does not occur. The layer that
                            would have found it was never built for that collection. Or the layer
                            exists, reached the collection, and cannot support the claim. Returning{" "}
                            <code>0</code> for all three is how a reader ends up believing something
                            about the Vedas that is only true about a database.
                        </p>
                        <p>
                            So this product distinguishes them. <code>NOT_BUILT</code> means the
                            dimension does not exist here. <code>INSUFFICIENT_EVIDENCE</code> means
                            it exists and cannot answer. A measured zero is printed as a zero and
                            says what it counted. Nothing is ever drawn as a bar of length zero
                            unless a real zero was measured.
                        </p>
                    </section>

                    <section id="method-relationships">
                        <h2>Kinds of connection</h2>
                        <p>
                            Two verses can be related in several unrelated ways, and this product
                            never averages them into a similarity score. Seven kinds are carried,
                            and the difference between the strongest and the weakest is
                            considerable.
                        </p>
                        <dl className="va-doc-terms">
                            {RELATIONSHIPS.map((kind) => (
                                <div key={kind.label}>
                                    <dt>{kind.label}</dt>
                                    <dd>{kind.body}</dd>
                                </div>
                            ))}
                        </dl>
                        <p>
                            <Link href="/visualizations/transmission">
                                The transmission plate shows all of them against all six corpus
                                pairs
                            </Link>
                            , with the cells that are not measurements typed rather than zeroed.
                        </p>
                    </section>

                    <section id="method-ask">
                        <h2>How Ask works</h2>
                        <p>
                            <Link href="/ask">Ask VedAnvaya</Link> answers questions in ordinary
                            language, and the important thing about it is the order in which it does
                            things.
                        </p>
                        <p>
                            A question is first resolved against the registry — the names in it are
                            matched to entities that actually exist in this graph, and a name that
                            does not resolve is reported rather than guessed at. The resolved
                            question drives a retrieval over the graph and the corpus, which
                            produces an evidence packet: specific verses, specific entities,
                            specific counts, each with its canonical key. Only then is a language
                            model involved, and its job is to write prose over that packet. Its
                            output is then validated: every citation it makes is checked against the
                            packet, and a citation that does not resolve is not shown as a citation.
                        </p>
                        <p>
                            <b>The model is not the database.</b> It does not look anything up, it
                            cannot reach the graph, and it is not asked what it knows about the
                            Vedas. If the retrieval finds nothing, the answer says so instead of
                            filling the gap — which is the failure mode this design exists to
                            prevent. Answer quality does depend in part on which model is
                            configured, and that is a real limitation rather than a footnote.
                        </p>
                    </section>

                    <section id="method-audio">
                        <h2>Recitation</h2>
                        <p>
                            Audio is a product layer over the text, not part of the knowledge model.
                            No recording is part of the graph, no recording is republished here, and
                            every file is streamed from its source at the moment it is played.
                        </p>
                        <p>
                            {audioStats ? (
                                <>
                                    {count(audioStats.total_records)} recitations are catalogued,
                                    one file per verse, all of them mapped to an exact verse rather
                                    than to a hymn.{" "}
                                </>
                            ) : null}
                            A mapping can be exact — this recording recites this verse — or
                            structural, where a recording covers a hymn and the verse is inside it,
                            or external only, where the recording exists and this product can point
                            at it without placing it. Those are kept apart, and a recording whose
                            source numbers its verses by a different recension is rejected rather
                            than approximately aligned: playing the wrong verse is worse than
                            playing nothing.
                        </p>
                        <p>
                            One collection has no recitation at all. No Samavedic recording is
                            catalogued here, which is conspicuous given that the Samaveda is the
                            Veda defined by its sung realisation — and it is a gap in what has been
                            published in a form this product can use, not a gap in the tradition.
                        </p>
                    </section>

                    <section id="limitations">
                        <h2>Known limitations</h2>
                        <p>
                            The full catalogue is <Link href="/limits">on its own page</Link>
                            {limits ? `, with ${limits} recorded entries` : ""}, each carrying the
                            measurement behind it and a question that can be answered instead. The
                            ones worth knowing before you read anything else:
                        </p>
                        <ul>
                            <li>
                                <b>The Samavedic gana corpus is absent.</b> A parallel and larger
                                body than the verse collection held here, and the reason the
                                Samaveda is a distinct Veda. Nothing here shows, notates or infers
                                melody.
                            </li>
                            <li>
                                <b>The Krishna Yajurveda is absent entirely</b>, and the
                                Atharvavedic Paippalada recension with it. Both are substantially
                                different collections rather than minor variants.
                            </li>
                            <li>
                                <b>The Samaveda has no released translation</b>, so every
                                translation-derived layer excludes it rather than being empty in it.
                            </li>
                            <li>
                                <b>Several layers reach one collection and not the others.</b> The
                                traditional deity ascription is Rigvedic; the semantic layer is
                                Rigvedic; the metre layer does not reach outside the Rigveda in a
                                form these surfaces can read.
                            </li>
                            <li>
                                <b>The mention layer is not one instrument.</b> Rigvedic mentions
                                come from a manual scholarly lemma annotation; the other three
                                collections are matched on surface tokens and sandhi, with no
                                morphology behind them. Comparing a Rigvedic rate with an
                                Atharvavedic one compares two methods as well as two texts.
                            </li>
                            <li>
                                <b>Lexical counts are minima.</b> They count verses in which a
                                registered alias occurs. At least one cell in the metals grid is
                                known to be wrong for this reason, and it is labelled rather than
                                corrected.
                            </li>
                            <li>
                                <b>Recitation coverage is uneven</b> and the Atharvavedic verse
                                total itself diverges slightly from the attested one, for reasons
                                that remain open research rather than settled.
                            </li>
                            <li>
                                <b>Ask depends partly on the configured model.</b> Retrieval and
                                citation validation are deterministic; the prose between them is
                                not.
                            </li>
                        </ul>
                    </section>

                    <section id="sources">
                        <h2>The sources</h2>
                        <p className="va-doc-open">
                            {provenance.totals.sources} sources and {provenance.totals.artifacts}{" "}
                            individual files, grouped by what each one contributes. This list is
                            generated from the build&rsquo;s own provenance records rather than
                            written by hand, and the generator refuses to run if a file the build
                            loaded is not accounted for here.
                        </p>

                        {provenance.layers.map((layer) => {
                            const entries = byLayer.get(layer.id) ?? [];
                            if (!entries.length) return null;
                            return (
                                <div className="va-source-layer" key={layer.id}>
                                    <header>
                                        <h3>{layer.label}</h3>
                                        <p>{layer.note}</p>
                                    </header>
                                    <ul className="va-source-list">
                                        {entries.map((entry) => (
                                            <li
                                                className="va-source"
                                                key={`${entry.layer}-${entry.source_id}-${entry.vedas.join("")}`}
                                            >
                                                <div className="va-source-name">
                                                    <h4>{entry.name}</h4>
                                                    {/* The short id, because it is what these
                                                        sources are called and what every
                                                        artifact id below is prefixed with. */}
                                                    <p className="va-source-id">
                                                        <code>{entry.source_id}</code>
                                                    </p>
                                                    {entry.organization ? (
                                                        <p className="va-source-org">
                                                            {entry.organization}
                                                        </p>
                                                    ) : null}
                                                    {entry.url ? (
                                                        <a
                                                            href={entry.url}
                                                            rel="noreferrer noopener"
                                                            target="_blank"
                                                        >
                                                            {new URL(entry.url).hostname}
                                                            <ArrowSquareOut
                                                                aria-hidden="true"
                                                                size={13}
                                                            />
                                                            <span className="sr-only">
                                                                (opens in a new tab)
                                                            </span>
                                                        </a>
                                                    ) : null}
                                                    <p className="va-source-vedas">
                                                        {entry.vedas.map((code) => (
                                                            <span key={code}>
                                                                <abbr
                                                                    title={vedaNames[code] ?? code}
                                                                >
                                                                    {code}
                                                                </abbr>
                                                            </span>
                                                        ))}
                                                    </p>
                                                </div>
                                                <div className="va-source-body">
                                                    <p>{entry.contributes}</p>
                                                    <p className="va-source-terms">
                                                        <b>Held under</b>
                                                        {entry.rights_status
                                                            .map(rightsLabel)
                                                            .join("; ")}
                                                        {entry.site_rights_status &&
                                                        !entry.rights_status.includes(
                                                            entry.site_rights_status,
                                                        )
                                                            ? ` — the site's own statement is ${rightsLabel(entry.site_rights_status).toLowerCase()}, and the files carry their own`
                                                            : ""}
                                                        .
                                                    </p>
                                                    {entry.artifacts.length ? (
                                                        <details className="va-source-artifacts">
                                                            <summary>
                                                                {entry.artifacts.length}{" "}
                                                                {entry.artifacts.length === 1
                                                                    ? "file"
                                                                    : "files"}
                                                                , with editions and retrieval dates
                                                            </summary>
                                                            <ul>
                                                                {entry.artifacts.map((artifact) => (
                                                                    <li key={artifact.artifact_id}>
                                                                        <strong>
                                                                            {artifact.title ??
                                                                                artifact.artifact_id}
                                                                        </strong>
                                                                        {artifact.source_edition ??
                                                                            artifact.edition_title ??
                                                                            null}
                                                                        {artifact.editors?.length
                                                                            ? ` · edited by ${artifact.editors.join(", ")}`
                                                                            : ""}
                                                                        {artifact.retrieval_date
                                                                            ? ` · retrieved ${artifact.retrieval_date}`
                                                                            : ""}
                                                                        {artifact.format
                                                                            ? ` · ${artifact.format}`
                                                                            : ""}
                                                                        <br />
                                                                        <code>
                                                                            {artifact.artifact_id}
                                                                        </code>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </details>
                                                    ) : null}
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            );
                        })}

                        <h3>On the terms</h3>
                        <p>
                            The texts are ancient and the translations held here are out of
                            copyright, but the electronic editions that carry them are not
                            automatically free to reuse: a transcription is a work, and several of
                            these carry share-alike or non-commercial terms that a reader
                            redistributing them would inherit. Where a site states one thing and the
                            file it serves states another, both are recorded above, and the file is
                            the one that governs.{" "}
                            {consulted.length
                                ? `${consulted.length === 1 ? "One source is" : `${consulted.length} sources are`} consulted and not reproduced — ${consulted
                                      .map((entry) => entry.name)
                                      .join(
                                          ", ",
                                      )} — read against the text to check it rather than to supply it.`
                                : null}
                        </p>
                    </section>

                    <nav aria-label="Where to go next" className="va-doc-onward">
                        <h2>Where to go next</h2>
                        <ul>
                            <li>
                                <Link href="/limits">
                                    <strong>What this corpus cannot answer</strong>
                                    <span>
                                        The full catalogue of recorded limits, with measurements
                                    </span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/insights">
                                    <strong>Evidence and interpretation</strong>
                                    <span>The three quantitative layers, kept visibly apart</span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/visualizations">
                                    <strong>The visualizations</strong>
                                    <span>The method above, applied to seven questions</span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/about">
                                    <strong>About the project</strong>
                                    <span>Why it exists, and who built it</span>
                                </Link>
                            </li>
                        </ul>
                    </nav>
                </div>
            </div>
        </div>
    );
}
