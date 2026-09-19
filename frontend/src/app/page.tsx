import { readFile } from "node:fs/promises";
import path from "node:path";
import Image from "next/image";
import Link from "next/link";
import { WorldPreviewPanel } from "@/components/home/world-preview-panel";
import type { HeroSlice } from "@/components/home/world-preview";
import { Action, Heading, Kicker, Section, SectionRule } from "@/components/home/sections";
import { ServiceUnavailable } from "@/components/empty-state";
import { pageMetadata } from "@/lib/site";
import {
    encoded,
    load,
    loadCompleteness,
    vedaNames,
    vedaOrder,
    workSlugs,
    type CrossVeda,
    type Loaded,
    type Stats,
    type WorksResponse,
} from "@/lib/api";

export const metadata = pageMetadata({
    title: "VedAnvaya — The Vedas, connected",
    description:
        "Read the four Vedic Samhitas as one connected corpus: 20,210 canonical mantras with translation, recitation, notation, entities and cross-Veda textual reuse.",
    pathname: "/",
});

/**
 * The VedAnvaya homepage.
 *
 * Ten sections and ten different layout families. That constraint is doing real work: the
 * failure mode of a long marketing page is that every section becomes a heading, a
 * paragraph and three cards, and the reader stops seeing sections at all. Here the measured
 * figures are a ledger band, the collections are a table, the recitation figures are bars,
 * the world preview is full-bleed, the featured verse is a plate, and the closing list is a
 * contents page. No two neighbours are shaped alike.
 *
 * WHERE THE FIGURES COME FROM. Every number printed on this page is either read from the
 * knowledge service on this request or taken from the certified completeness record in
 * `lib/api.ts`. Nothing here is typed into prose. The `sourceNote` under the figures band
 * states that out loud, because a figure a reader cannot trace is a figure nothing can check.
 *
 * One figure is deliberately never printed anywhere: the graph's own relationship total. The
 * API withholds it because most of its edges are one annotation layer's projection of a
 * container label onto the passages inside it, so a headline built from it would measure the
 * build rather than the corpus. The cross-Veda link total below is a different thing: it is
 * the API's own measured sum over the five built cross-Veda classes.
 *
 * SCOPE COPY LIVES ON /limits. This page states scope in a clause, never in a paragraph.
 * The detailed boundaries -- excluded recensions, the gana corpus, translation typology,
 * audible review, notation scope -- are set out once, on /limits, and linked from here.
 */

export const revalidate = 300;

type AudioStats = {
    total_records: number;
    mapped_scope_keys_by_veda: Record<string, number>;
};

type FormulaDiffusion = { coverage?: { measured?: Record<string, number> } };

type PassageSurface = {
    script: string;
    accented: boolean;
    text: string;
    witness_id: string;
};
type Passage = {
    canonical_citation: string;
    canonical_key: string;
    text: { surfaces: PassageSurface[]; devanagari: string };
    translations: {
        items: Array<{ text: string; translator: string; year: number | null }>;
    };
};

/** One row of `/works`, once the optional list has been narrowed. */
type Collection = NonNullable<WorksResponse["items"]>[number];

/** The hero's slice of the world artifact. Built by `scripts/build-home-world.mjs`. */
type WorldSlice = HeroSlice;

const RECENSION: Record<string, string> = {
    RV: "Śākala",
    SV: "Kauthuma (ārcika)",
    YV: "Śukla, Vājasaneyi Mādhyandina",
    AV: "Śaunaka",
};

const SANSKRIT_NAME: Record<string, string> = {
    RV: "ऋग्वेद",
    SV: "सामवेद",
    YV: "यजुर्वेद",
    AV: "अथर्ववेद",
};

/**
 * The five things a reader can do here, in the order they are likely to want them.
 *
 * Each is a real destination, not a label. A rail of capability words that do not go anywhere
 * is an advertisement; a rail that does is navigation.
 */
const CAPABILITIES = [
    { label: "Read", href: "/vedas" },
    { label: "Explore", href: "/explore" },
    { label: "Ask", href: "/ask" },
    { label: "Hear", href: "/vedas/rigveda" },
    { label: "Connect", href: "/connections" },
];

const START_HERE = [
    {
        href: `/passage/${encoded("VG:RV:SAK:M01:S001:V001")}`,
        title: "The first verse of the Rigveda",
        note: "Sanskrit, recitation, translation, and where each of them came from",
    },
    {
        href: `/devatas/${encoded("VG:DEVATA:INDRAH")}`,
        title: "Indra across the four collections",
        note: "Named in thousands of verses, with the apparatus and the text kept apart",
    },
    {
        href: `/devatas/${encoded("VG:DEVATA:SOMAH")}`,
        title: "Soma, as a deity and as a substance",
        note: "One word, two records, both linked, neither merged",
    },
    {
        href: "/connections",
        title: "Rigvedic wording in the Samaveda",
        note: "Matched verse by verse, and classified by the kind of resemblance",
    },
    {
        href: "/explore/atharvaveda",
        title: "What the Atharvaveda addresses",
        note: "Fever, rivals, household life, counted by the words the verses use",
    },
    {
        href: "/formulas",
        title: "A formula through four collections",
        note: "Shared wording, traced to every collection it reaches",
    },
    {
        href: "/visualizations",
        title: "The four collections, side by side",
        note: "A plate for each question, with the method printed beside it",
    },
];

const number = (value: number | null | undefined) =>
    typeof value === "number" ? value.toLocaleString("en-GB") : null;

async function readWorldSlice(): Promise<WorldSlice | null> {
    /*
     * Read from disk rather than fetched over HTTP. It is a build artifact that ships in
     * `public/`, so on the server the file is already there; fetching it from our own origin
     * would add a network round trip to render a file we are sitting on.
     */
    try {
        const file = path.join(process.cwd(), "public", "data", "home-world.json");
        return JSON.parse(await readFile(file, "utf8")) as WorldSlice;
    } catch {
        return null;
    }
}

/** A named figure from `/stats`'s `corpus` or `entity_populations` block. */
function figure(rows: Stats["corpus"] | undefined, name: string): number | null {
    return rows?.find((row) => row.name === name)?.total ?? null;
}

export default async function Home() {
    const [works, stats, audio, crossVeda, diffusion, featured, opening, worldSlice, completeness] =
        await Promise.all([
            load<WorksResponse>("/works"),
            load<Stats>("/stats"),
            load<AudioStats>("/audio/stats"),
            load<CrossVeda>("/insights/cross-veda"),
            load<FormulaDiffusion>("/insights/formula-diffusion"),
            load<Passage>(`/passages/${encoded("VG:RV:SAK:M10:S129:V007")}`),
            load<Passage>(`/passages/${encoded("VG:RV:SAK:M01:S001:V001")}`),
            readWorldSlice(),
            loadCompleteness(),
        ]);

    if (!works.ok || !stats.ok) {
        return (
            <div className="shell page">
                <ServiceUnavailable />
            </div>
        );
    }

    const collections = [...(works.data.items ?? [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );
    const recited = audio.ok ? audio.data.mapped_scope_keys_by_veda : {};

    /* --- every figure below is read, never typed --------------------------------- */

    const verses = figure(stats.data.corpus, "mantras");
    const translations = figure(stats.data.corpus, "translations");
    const reused = figure(stats.data.corpus, "reused_renderings");
    const recitations = audio.ok ? audio.data.total_records : null;
    const notation = completeness.samaveda_notation.validated_notation_witnesses;

    const deities = stats.data.deities?.resolved_deities ?? null;
    const seers = stats.data.seers?.seers ?? null;
    const formulas = figure(stats.data.entity_populations, "formulas");
    const rituals = figure(stats.data.entity_populations, "rituals");
    const metres = figure(stats.data.entity_populations, "chandas");

    /*
     * Two cross-Veda totals, and they answer different questions.
     *
     * `crossLinks` is every measured cross-Veda edge across the five built classes, which is
     * the same number the API reports as the sum of its six pair totals. `literalReuse` is
     * the subset the API itself types LITERAL_TEXTUAL_REUSE -- exact parallel, near parallel,
     * directed reuse and variant -- with shared entity vocabulary left out, because shared
     * vocabulary says nothing at all about shared wording and adding it to a reuse figure
     * would say it did. Both are sums of typed class totals, so both are edge counts and
     * neither is a count of verse pairs.
     */
    const classes = crossVeda.ok ? (crossVeda.data.relationship_classes ?? []) : [];
    const built = classes.filter((row) => typeof row.cross_veda_edges === "number");
    const crossLinks = built.length
        ? built.reduce((sum, row) => sum + (row.cross_veda_edges ?? 0), 0)
        : null;
    const literalReuse = built.length
        ? built
              .filter((row) => row.resemblance_kind === "LITERAL_TEXTUAL_REUSE")
              .reduce((sum, row) => sum + (row.cross_veda_edges ?? 0), 0)
        : null;

    const reachingAll = diffusion.ok
        ? (diffusion.data.coverage?.measured?.reaching_all_four ?? null)
        : null;
    const families = diffusion.ok ? (diffusion.data.coverage?.measured?.families ?? null) : null;

    const ask = completeness.ask_benchmark;
    /*
     * `loadCompleteness` stamps where its answer came from. A page that prints a certified
     * figure beside live ones has to say which it is showing, and "the certified release
     * record" is only true when the service answered; when it did not, the figure is a copy
     * pinned in the client, and that is a different claim.
     */
    const certifiedLive = completeness.data_source !== "fallback";

    return (
        <>
            <Hero
                collections={collections.length}
                recitations={recitations}
                verses={verses}
                world={worldSlice}
            />

            <Counts
                certifiedLive={certifiedLive}
                collections={collections.length}
                crossLinks={crossLinks}
                deities={deities}
                formulas={formulas}
                literalReuse={literalReuse}
                metres={metres}
                notation={notation}
                recitations={recitations}
                reused={reused}
                rituals={rituals}
                seers={seers}
                translations={translations}
                verses={verses}
            />

            <Ledger collections={collections} recited={recited} />

            <SectionRule />

            <Reading passage={opening} />

            <Recitation collections={collections} recited={recited} total={recitations} />

            <Connections
                families={families}
                literalReuse={literalReuse}
                reachingAll={reachingAll}
            />

            <Ask
                acceptable={ask.effective_acceptable}
                refused={ask.insufficient_evidence_refused}
                total={ask.total_questions}
            />

            <SectionRule />

            <FeaturedVerse featured={featured} />

            <EvidenceKey />

            <StartHere translations={translations} />
        </>
    );
}

/* ------------------------------------------------------------------ S1 hero - */

function Hero({
    collections,
    recitations,
    verses,
    world,
}: {
    collections: number;
    recitations: number | null;
    verses: number | null;
    world: WorldSlice | null;
}) {
    /*
     * The signal line is institutional proof, not a growth metric, so it is set at the size
     * of a caption and placed below the actions rather than above the headline. Four figures
     * would start to read as a dashboard; three do not.
     */
    const signals = [
        verses ? `${number(verses)} canonical mantras` : null,
        collections ? `${collections} Samhita corpora` : null,
        recitations ? `${number(recitations)} recitations` : null,
    ].filter(Boolean) as string[];

    return (
        <section className="va-hero">
            <div className="va-hero-inner">
                <div className="va-hero-type">
                    <p className="va-hero-brand" lang="sa">
                        वेदान्वय
                    </p>
                    <h1 className="va-hero-headline">
                        VedAnvaya <span className="va-hero-em">— The Vedas, connected.</span>
                    </h1>

                    {/* The five verbs, each one a destination. Set as a rail directly under
                        the headline so the page's first claim is what a reader can do. */}
                    <ul className="va-hero-rail">
                        {CAPABILITIES.map((item) => (
                            <li key={item.href}>
                                <Link className="va-hero-rail-item" href={item.href}>
                                    {item.label}
                                </Link>
                            </li>
                        ))}
                    </ul>

                    <p className="va-hero-lede">
                        Four Samhitas held as one corpus. Read any verse in Sanskrit with its
                        recitation and its translation, follow a deity or a formula across the
                        collections, and see the evidence behind every connection.
                    </p>
                    <div className="va-hero-actions">
                        <Link className="va-button" href="/vedas">
                            Read the Vedas
                        </Link>
                        <Action href="/graph" prefetch={false}>
                            Open the graph
                        </Action>
                    </div>
                    {signals.length ? (
                        <p className="va-hero-signal">{signals.join(" · ")}</p>
                    ) : null}
                </div>

                <div className="va-hero-figure">
                    <WorldPreviewPanel slice={world} />
                </div>
            </div>
        </section>
    );
}

/* --------------------------------------------------------- S2 the figures - */

/**
 * What the product holds, as a band of measured figures.
 *
 * Every cell carries a value, the thing it counts, and one clause that stops the value being
 * read as something it is not. The subjects cell is wide and holds a list rather than a
 * headline number, because the entity populations overlap by construction -- a metal is also
 * a substance and also a concept -- so a single summed total would be wrong. Each named
 * population beneath it is measured on its own and can be compared to itself.
 */
function Counts({
    certifiedLive,
    collections,
    crossLinks,
    deities,
    formulas,
    literalReuse,
    metres,
    notation,
    recitations,
    reused,
    rituals,
    seers,
    translations,
    verses,
}: {
    certifiedLive: boolean;
    collections: number;
    crossLinks: number | null;
    deities: number | null;
    formulas: number | null;
    literalReuse: number | null;
    metres: number | null;
    notation: number;
    recitations: number | null;
    reused: number | null;
    rituals: number | null;
    seers: number | null;
    translations: number | null;
    verses: number | null;
}) {
    const subjects = [
        deities ? { value: number(deities), label: "deities" } : null,
        seers ? { value: number(seers), label: "seers" } : null,
        formulas ? { value: number(formulas), label: "formulas" } : null,
        metres ? { value: number(metres), label: "metres" } : null,
        rituals ? { value: number(rituals), label: "rites" } : null,
    ].filter(Boolean) as Array<{ value: string | null; label: string }>;

    return (
        <Section className="va-counts-section is-tight" tone="sunk">
            <Heading lede="Read from the knowledge service when this page was built, and shown with the clause each one needs to be read correctly.">
                What this atlas holds.
            </Heading>

            <dl className="va-counts">
                {verses ? (
                    <div className="va-count-cell">
                        <dt className="va-count-label">Canonical mantras</dt>
                        <dd>
                            <span className="va-count-value">{number(verses)}</span>
                            <span className="va-count-gloss">
                                Every verse addressed by a canonical key and a canonical citation.
                            </span>
                        </dd>
                    </div>
                ) : null}

                {collections ? (
                    <div className="va-count-cell">
                        <dt className="va-count-label">Samhita corpora</dt>
                        <dd>
                            <span className="va-count-value">{collections}</span>
                            <span className="va-count-gloss">
                                Rigveda, Samaveda, Yajurveda, Atharvaveda — one recension each.
                            </span>
                        </dd>
                    </div>
                ) : null}

                {translations ? (
                    <div className="va-count-cell">
                        <dt className="va-count-label">English translations</dt>
                        <dd>
                            <span className="va-count-value">{number(translations)}</span>
                            <span className="va-count-gloss">
                                A corpus&rsquo;s own published English
                                {reused
                                    ? `, plus ${number(reused)} renderings reused from a parallel verse and labelled as reuse`
                                    : ""}
                                .
                            </span>
                        </dd>
                    </div>
                ) : null}

                {recitations ? (
                    <div className="va-count-cell">
                        <dt className="va-count-label">Verse recitations</dt>
                        <dd>
                            <span className="va-count-value">{number(recitations)}</span>
                            <span className="va-count-gloss">
                                One recording per verse, mapped to an exact verse and streamed from
                                its source.
                            </span>
                        </dd>
                    </div>
                ) : null}

                <div className="va-count-cell">
                    <dt className="va-count-label">Samavedic notation witnesses</dt>
                    <dd>
                        <span className="va-count-value">{number(notation)}</span>
                        <span className="va-count-gloss">
                            Verses carrying source-explicit svara marks, validated against the
                            printed witness.
                        </span>
                    </dd>
                </div>

                {crossLinks ? (
                    <div className="va-count-cell">
                        <dt className="va-count-label">Cross-Veda links</dt>
                        <dd>
                            <span className="va-count-value">{number(crossLinks)}</span>
                            <span className="va-count-gloss">
                                Measured across six corpus pairs
                                {literalReuse
                                    ? `, of which ${number(literalReuse)} are literal textual reuse`
                                    : ""}
                                .
                            </span>
                        </dd>
                    </div>
                ) : null}

                {subjects.length ? (
                    <div className="va-count-cell is-wide">
                        <dt className="va-count-label">Named subjects in the graph</dt>
                        <dd>
                            <ul className="va-count-subjects">
                                {subjects.map((item) => (
                                    <li key={item.label}>
                                        <b>{item.value}</b>
                                        <span>{item.label}</span>
                                    </li>
                                ))}
                            </ul>
                            <span className="va-count-gloss">
                                Counted apart rather than summed: one subject can be a metal, a
                                substance and a concept at once, so a single total would count it
                                three times.
                            </span>
                        </dd>
                    </div>
                ) : null}
            </dl>

            <p className="va-count-source">
                Corpus, translation, subject and cross-Veda figures are read live from the
                knowledge service. The notation figure comes from the certified completeness
                record,{" "}
                {certifiedLive
                    ? "read from the service on this request"
                    : "from the copy pinned in this build because the service did not answer"}
                . <Link href="/sources">How each figure is established</Link>.
            </p>
        </Section>
    );
}

/* ------------------------------------------------------- S3 the four Vedas - */

function Ledger({
    collections,
    recited,
}: {
    collections: Collection[];
    recited: Record<string, number>;
}) {
    return (
        <Section className="va-ledger-section is-open">
            <Kicker sanskrit="श्रुति">The Vedas</Kicker>
            <Heading lede="Each collection keeps its own structure, its own recension and its own words for both. Open one to read it.">
                Four Samhitas, one recension each.
            </Heading>

            <table className="va-ledger">
                <caption className="sr-only">
                    The four collections held, with the recension of each, its verse count, and how
                    many verses carry a translation and a recitation.
                </caption>
                <thead>
                    <tr>
                        <th scope="col">Collection</th>
                        <th scope="col">Recension</th>
                        <th className="is-num" scope="col">
                            Verses
                        </th>
                        <th className="is-num" scope="col">
                            Translated
                        </th>
                        <th className="is-num" scope="col">
                            Recited
                        </th>
                        <th scope="col">
                            <span className="sr-only">Read</span>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {collections.map((work) => {
                        const code = work.veda ?? "RV";
                        const audio = recited[code];
                        const translated = work.translated_mantra_count ?? null;
                        return (
                            <tr key={work.work_id}>
                                <th scope="row">
                                    <Link href={`/vedas/${workSlugs[code]}`}>
                                        <span className="va-ledger-name">{vedaNames[code]}</span>
                                        <span className="va-deva-label" lang="sa">
                                            {SANSKRIT_NAME[code]}
                                        </span>
                                    </Link>
                                </th>
                                <td data-label="Recension">{RECENSION[code]}</td>
                                <td className="is-num" data-label="Verses">
                                    {number(work.mantra_count)}
                                </td>
                                <td className="is-num" data-label="Translated">
                                    {translated === 0 ? (
                                        /*
                                         * The Samavedic zero is real and measured, and it is the
                                         * most informative cell in the table, so it is marked
                                         * rather than printed as an ordinary figure. What sits
                                         * against those verses instead is a Rigvedic rendering,
                                         * disclosed as reuse on the collection's own page.
                                         */
                                        <span className="va-ledger-zero">
                                            reused renderings only
                                        </span>
                                    ) : (
                                        number(translated)
                                    )}
                                </td>
                                <td className="is-num" data-label="Recited">
                                    {audio === 0 ? (
                                        <span className="va-ledger-zero">none released</span>
                                    ) : (
                                        (number(audio) ?? "—")
                                    )}
                                </td>
                                <td className="va-ledger-open" data-label="Read">
                                    <Link href={`/vedas/${workSlugs[code]}`}>
                                        Open {vedaNames[code]}
                                    </Link>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            <p className="va-ledger-note">
                Each edition&rsquo;s recension, and what it excludes, is set out in full on{" "}
                <Link href="/limits">the scope page</Link>.
            </p>
        </Section>
    );
}

/* ---------------------------------------------------- S4 reading a verse --- */

/*
 * The reader preview shows the corpus's opening verse, not the verse the plate shows further
 * down. A first pass fed both sections the same passage, so the page printed RV 10.129.7
 * twice and this section's "Open this passage" led somewhere the reader had not been shown.
 */
function Reading({ passage }: { passage: Loaded<Passage> }) {
    const iast = passage.ok
        ? passage.data.text.surfaces.find((s) => s.script === "IAST")
        : undefined;

    return (
        <Section className="va-split" tone="sunk">
            <div className="va-split-figure">
                <div className="va-verse-frame">
                    <p className="va-verse-citation">
                        {passage.ok ? passage.data.canonical_citation : "RV 1.1.1"}
                    </p>
                    {iast ? (
                        <p className="va-sanskrit" data-script="IAST" lang="sa">
                            {iast.text}
                        </p>
                    ) : null}
                    <dl className="va-verse-apparatus">
                        <div>
                            <dt>Script</dt>
                            <dd>Romanised, accented</dd>
                        </div>
                        <div>
                            <dt>Witness</dt>
                            <dd>{iast?.witness_id ?? "not read"}</dd>
                        </div>
                        <div>
                            <dt>Translation</dt>
                            <dd>
                                {passage.ok && passage.data.translations.items[0]
                                    ? `${passage.data.translations.items[0].translator}, ${passage.data.translations.items[0].year}`
                                    : "not read"}
                            </dd>
                        </div>
                    </dl>
                </div>
            </div>
            <div className="va-split-copy">
                <Heading>A verse, and everything standing behind it.</Heading>
                <p>
                    The Sanskrit, the recitation, the translation, the seer and the deity the
                    traditional index assigns, the words the verse actually contains, and the
                    wording it shares with another collection.
                </p>
                <p>
                    Each of those comes from a named layer, and each says how it was established.
                    An assignment made by the index is never shown as a statement the Sanskrit
                    makes.
                </p>
                <Action
                    href={`/passage/${encoded(passage.ok ? passage.data.canonical_key : "VG:RV:SAK:M01:S001:V001")}`}
                >
                    Open this passage
                </Action>
            </div>
        </Section>
    );
}

/* --------------------------------------------------------- S5 recitation --- */

function Recitation({
    collections,
    recited,
    total,
}: {
    collections: Collection[];
    recited: Record<string, number>;
    total: number | null;
}) {
    const widest = Math.max(...collections.map((w) => w.mantra_count ?? 0), 1);

    return (
        <Section className="is-tight">
            {/* "catalogued from VedSearch" was true of every recording in the catalogue and
                stopped being true when 946 were admitted from two further publishers. The
                sentence names no publisher now; /sources names all three, which is where a
                reader looking for a provenance goes. The count itself is not written here
                either, in a comment or anywhere else - it is read from the service, and
                `completeness-truth.test.ts` holds this file to that. */}
            <Heading lede="One recording per verse, catalogued from its publisher and streamed from there rather than copied. A recording is attached only where our canonical key lands in the source's numbering and the Sanskrit matches this corpus's text, because playing the wrong verse is worse than playing nothing. That is a checked mapping and not an audible review; how far each has been taken is on the scope page.">
                {total
                    ? `${number(total)} verses, each with its own recitation.`
                    : "Recitation, verse by verse."}
            </Heading>

            <ul className="va-bars">
                {collections.map((work) => {
                    const code = work.veda ?? "RV";
                    const have = recited[code] ?? 0;
                    const of = work.mantra_count ?? 0;
                    /*
                     * The Samavedic row is not a zero-length bar. A bar of length zero sits in
                     * the same visual sentence as the other three and reads as "almost none",
                     * which is a different claim from "none exists anywhere". It gets a typed
                     * statement at the same weight as the bars instead.
                     */
                    if (have === 0) {
                        return (
                            <li className="va-bar-row is-absent" key={work.work_id}>
                                <span className="va-bar-label">{vedaNames[code]}</span>
                                <p className="va-bar-absence">
                                    <strong>No Samavedic recording is catalogued.</strong> The
                                    Samaveda is the one Veda defined by its sung realisation, so
                                    this is the most conspicuous gap in the layer &mdash; and it is
                                    a gap in what has been published, not a statement about the
                                    tradition.
                                </p>
                            </li>
                        );
                    }
                    return (
                        <li className="va-bar-row" key={work.work_id}>
                            <span className="va-bar-label">{vedaNames[code]}</span>
                            <span className="va-bar-track">
                                <span
                                    className="va-bar-fill"
                                    style={{ width: `${(have / widest) * 100}%` }}
                                />
                                <span
                                    className="va-bar-ghost"
                                    style={{ width: `${(of / widest) * 100}%` }}
                                />
                            </span>
                            <span className="va-bar-figure">
                                {number(have)} <span>of {number(of)}</span>
                            </span>
                        </li>
                    );
                })}
            </ul>
        </Section>
    );
}

/* ------------------------------------------------------- S6 connections ---- */

function Connections({
    families,
    literalReuse,
    reachingAll,
}: {
    families: number | null;
    literalReuse: number | null;
    reachingAll: number | null;
}) {
    return (
        <Section className="va-split is-reversed" tone="sunk">
            <div className="va-split-copy">
                <Kicker sanskrit="अन्वय">Connections</Kicker>
                <Heading>The same wording stands in more than one collection.</Heading>
                <p>
                    {literalReuse ? `${number(literalReuse)} cross-Veda links are ` : "Links are "}
                    built in typed kinds rather than as one similarity score: exact parallel, near
                    parallel, variant, directed reuse, shared formula, shared entity vocabulary.
                    Which kind a link is decides what it can be used to argue.
                </p>
                <p>
                    {families
                        ? `${number(families)} formula families are traced through the corpus, and each one carries the collections it reaches.`
                        : "Formula families are traced through the corpus, and each carries the collections it reaches."}{" "}
                    Every link opens onto both verses, so the resemblance can be read rather than
                    taken on trust.
                </p>
                <Action href="/connections">
                    {reachingAll
                        ? `Follow the wording, including ${number(reachingAll)} families that reach all four`
                        : "Follow the wording"}
                </Action>
            </div>
            <div className="va-split-figure">
                <ol className="va-chain">
                    <li>
                        <span className="va-chain-mark" aria-hidden="true" />
                        <span className="va-chain-label">A Rigvedic verse</span>
                        <span className="va-chain-note">
                            RV 1.1.1, the text as GRETIL prints it
                        </span>
                    </li>
                    <li>
                        <span className="va-chain-mark" aria-hidden="true" />
                        <span className="va-chain-label">stands again in the Samaveda</span>
                        <span className="va-chain-note">
                            Matched on wording, classified, and kept distinct from mere reuse
                        </span>
                    </li>
                    <li>
                        <span className="va-chain-mark" aria-hidden="true" />
                        <span className="va-chain-label">and the difference is shown</span>
                        <span className="va-chain-note">
                            Both texts side by side, with what each witness actually reads
                        </span>
                    </li>
                </ol>
            </div>
        </Section>
    );
}

/* ---------------------------------------------------------------- S7 ask --- */

function Ask({
    acceptable,
    refused,
    total,
}: {
    acceptable: string;
    refused: number;
    total: number;
}) {
    return (
        <Section className="va-ask is-tight">
            <Heading lede="Retrieval runs first, over a fixed catalogue of channels, and the model sees only what retrieval returned.">
                Ask a question. Check the answer.
            </Heading>
            <div className="va-ask-pair">
                <div>
                    <h3>Every sentence carries its evidence</h3>
                    <p>
                        Each factual claim comes with a citation you can open: the retrieved item,
                        its Sanskrit, its translation and its canonical citation. The evidence is
                        the answer&rsquo;s working, not a reading list attached afterwards.
                    </p>
                </div>
                <div>
                    <h3>And a question it cannot reach is refused</h3>
                    <p>
                        On its {total}-question benchmark the current build returned{" "}
                        {acceptable} acceptable outcomes, nothing misleading and nothing invented,
                        with {refused} questions honestly refused rather than answered from a gap.
                    </p>
                </div>
            </div>
            <Action href="/ask">Ask a question</Action>
        </Section>
    );
}

/* ------------------------------------------------------ S8 featured verse -- */

function FeaturedVerse({ featured }: { featured: Loaded<Passage> }) {
    if (!featured.ok) return null;
    const iast = featured.data.text.surfaces.find((s) => s.script === "IAST");
    const translation = featured.data.translations.items[0];
    if (!iast || !translation) return null;

    return (
        <section className="va-plate">
            <Image
                alt=""
                aria-hidden="true"
                className="va-plate-ground"
                height={1086}
                sizes="100vw"
                src="/brand/textures/quote-light-1280.webp"
                width={1448}
            />
            <figure className="va-plate-inner">
                <p className="va-kicker">
                    <span className="va-deva-label" lang="sa">
                        मन्त्र
                    </span>
                    <span>{featured.data.canonical_citation}</span>
                </p>
                <blockquote className="va-sanskrit va-plate-verse" data-script="IAST" lang="sa">
                    {iast.text}
                </blockquote>
                <p className="va-plate-translation">{translation.text}</p>
                <figcaption className="va-plate-caption">
                    <span>
                        Translated by {translation.translator}
                        {translation.year ? `, ${translation.year}` : ""}
                    </span>
                    <Link href={`/passage/${encoded(featured.data.canonical_key)}`}>
                        Open this passage
                    </Link>
                </figcaption>
            </figure>
        </section>
    );
}

/* ------------------------------------------------------- S9 evidence key --- */

/**
 * How to read a provenance badge.
 *
 * This section used to be a wall of absence copy. It is a capability, not a caveat: the four
 * grades are the thing that makes a connection here checkable, and the reader meets them on
 * every surface. The detailed boundaries it used to carry now live on /limits.
 */
function EvidenceKey() {
    return (
        <Section className="va-absence is-open" tone="sunk">
            <Heading
                level={2}
                lede="Four grades, attached to the claim rather than assumed from context. A weaker grade is never promoted by sitting next to a stronger one."
            >
                Every claim says how it was established.
            </Heading>
            <dl className="va-absence-list">
                <div>
                    <dt>Source</dt>
                    <dd>The text, an edition, or a statement the traditional index makes.</dd>
                </div>
                <div>
                    <dt>Derived</dt>
                    <dd>Computed from a source by a stated rule, the same way every time.</dd>
                </div>
                <div>
                    <dt>Model-assisted</dt>
                    <dd>Extracted by a language model, kept as a candidate, always marked.</dd>
                </div>
                <div>
                    <dt>Interpretation</dt>
                    <dd>A reading of the data, recorded with what would falsify it.</dd>
                </div>
            </dl>
            <p className="va-absence-close">
                Where a layer was never built, the answer says so instead of returning a zero that
                a reader could mistake for silence in the Vedas.
            </p>
            <div className="va-absence-actions">
                <Action href="/sources">Read the evidence model</Action>
                <Action href="/limits">See the scope of this edition</Action>
            </div>
        </Section>
    );
}

/* -------------------------------------------------------- S10 start here --- */

function StartHere({ translations }: { translations: number | null }) {
    return (
        <Section className="va-start">
            <Heading>Where to start.</Heading>
            <ol className="va-start-list">
                {START_HERE.map((item, i) => (
                    <li key={item.href}>
                        <Link href={item.href}>
                            <span className="va-start-index" aria-hidden="true">
                                {String(i + 1).padStart(2, "0")}
                            </span>
                            <span className="va-start-title">{item.title}</span>
                            <span className="va-start-note">{item.note}</span>
                        </Link>
                    </li>
                ))}
            </ol>
            <p className="va-start-close">
                Built by one person over{" "}
                <Link href="/sources">the sources named on the sources page</Link>
                {translations ? `, across ${number(translations)} translated verses` : ""}.{" "}
                <Link href="/about">About this project</Link>
            </p>
        </Section>
    );
}
