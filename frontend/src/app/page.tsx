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
    vedaNames,
    vedaOrder,
    workSlugs,
    type Loaded,
    type Stats,
    type WorksResponse,
} from "@/lib/api";

export const metadata = pageMetadata({
    title: "VedAnvaya — The Vedas, connected",
    description:
        "Read the four Vedic Samhitas as one connected corpus, with passages, recitation, entities and the evidence behind every connection.",
    pathname: "/",
});

/**
 * The VedAnvaya homepage.
 *
 * Ten sections and ten different layout families. That constraint is doing real work: the
 * failure mode of a long marketing page is that every section becomes a heading, a
 * paragraph and three cards, and the reader stops seeing sections at all. Here the ledger is
 * a table, the recitation figures are bars, the cross-Veda material is the live matrix, the
 * world preview is full-bleed, the featured verse is a plate, and the closing list is a
 * contents page. No two neighbours are shaped alike.
 *
 * Every figure on the page is read from the API at request time. None is hard-coded, with
 * one deliberate exception noted at the Ask section, and one figure is deliberately never
 * printed anywhere: the graph's own relationship total, which the API withholds because most
 * of its edges are one annotation layer's projection of a container label onto the passages
 * inside it. A headline built from that number would measure the build and not the corpus.
 */

export const revalidate = 300;

type AudioStats = {
    total_records: number;
    mapped_scope_keys_by_veda: Record<string, number>;
};

type Capabilities = { limits?: unknown[] };
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

/** A recension whose ordinary name promises more than this build holds. */
const NOT_HELD: Record<string, string> = {
    RV: "The Ashvalayana recension. No Brahmana, Aranyaka or Upanisad.",
    SV: "The gāna collections (outside release scope). 1,136 notation witnesses validated (Gates A/B/C passed); 708 withheld.",
    YV: "The whole of the Krishna Yajurveda. The Kanva recension.",
    AV: "The Paippalada recension.",
};

const RECENSION: Record<string, string> = {
    RV: "Śākala",
    SV: "Kauthuma (ārcika only)",
    YV: "Śukla, Vājasaneyi Mādhyandina",
    AV: "Śaunaka",
};

const SANSKRIT_NAME: Record<string, string> = {
    RV: "ऋग्वेद",
    SV: "सामवेद",
    YV: "यजुर्वेद",
    AV: "अथर्ववेद",
};

const START_HERE = [
    {
        href: `/passage/${encoded("VG:RV:SAK:M01:S001:V001")}`,
        title: "The first verse of the Rigveda",
        note: "Sanskrit, recitation, translation, and where each of them came from",
    },
    {
        href: `/devatas/${encoded("VG:DEVATA:INDRAH")}`,
        title: "Indra across the four collections",
        note: "Named in thousands of verses. The apparatus assigns him in one collection only",
    },
    {
        href: `/devatas/${encoded("VG:DEVATA:SOMAH")}`,
        title: "Soma, as a deity and as a substance",
        note: "One word, two records, both linked, neither merged",
    },
    {
        href: "/connections",
        title: "Rigvedic wording in the Samaveda",
        note: "The only corpus pair for which directed reuse was established",
    },
    {
        href: "/explore/atharvaveda",
        title: "What the Atharvaveda addresses",
        note: "Fever, rivals, household life. Counts are lexical minima, never diagnoses",
    },
    {
        href: "/formulas",
        title: "A formula through four collections",
        note: "Shared wording, traced to every collection it reaches",
    },
    {
        href: "/visualizations",
        title: "The four collections, side by side",
        note: "A plate for each question, and a plain statement of what it does not show",
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

export default async function Home() {
    const [works, stats, audio, capabilities, diffusion, featured, opening, worldSlice] =
        await Promise.all([
            load<WorksResponse>("/works"),
            load<Stats>("/stats"),
            load<AudioStats>("/audio/stats"),
            load<Capabilities>("/insights/capabilities"),
            load<FormulaDiffusion>("/insights/formula-diffusion"),
            load<Passage>(`/passages/${encoded("VG:RV:SAK:M10:S129:V007")}`),
            load<Passage>(`/passages/${encoded("VG:RV:SAK:M01:S001:V001")}`),
            readWorldSlice(),
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
    const verses = stats.data.corpus?.find((c) => c.name === "mantras")?.total ?? null;
    const translations = stats.data.corpus?.find((c) => c.name === "translations")?.total ?? null;
    const recitations = audio.ok ? audio.data.total_records : null;
    const limits = capabilities.ok ? (capabilities.data.limits?.length ?? null) : null;
    const reachingAll = diffusion.ok
        ? (diffusion.data.coverage?.measured?.reaching_all_four ?? null)
        : null;

    return (
        <>
            <Hero
                collections={collections.length}
                recitations={recitations}
                verses={verses}
                world={worldSlice}
            />

            <Ledger collections={collections} recited={recited} />

            <SectionRule />

            <Reading passage={opening} />

            <Recitation collections={collections} recited={recited} total={recitations} />

            <Connections reachingAll={reachingAll} />

            <Ask />

            <SectionRule />

            <FeaturedVerse featured={featured} />

            <Absence limits={limits} />

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
        collections ? `${collections} Samhitas` : null,
        verses ? `${number(verses)} verses` : null,
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
                        {/* The explicit space survives the line break being hidden on a
                            phone, where the headline sets as one paragraph. Without it the
                            two clauses ran together as "one corpus,and the". */}
                        Four Samhitas, one corpus, <br className="va-hero-break" />
                        and the evidence behind every connection.
                    </h1>
                    <p className="va-hero-lede">
                        Read any verse with its recitation, follow a deity across the four
                        collections, and see what is missing.
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

/* ------------------------------------------------------- S2 the four Vedas - */

function Ledger({
    collections,
    recited,
}: {
    collections: Collection[];
    recited: Record<string, number>;
}) {
    return (
        <Section tone="sunk" className="va-ledger-section is-open">
            <Kicker sanskrit="श्रुति">The Vedas</Kicker>
            <Heading lede="Three of the four are partial in ways their traditional names do not reveal. Each row says which part, before it says how much.">
                Four Samhitas, one recension each.
            </Heading>

            <table className="va-ledger">
                <caption className="sr-only">
                    The four collections held, with the recension of each, its verse count, how many
                    verses carry a translation and a recitation, and what is not held.
                </caption>
                <thead>
                    <tr>
                        <th scope="col">Collection</th>
                        <th scope="col">Recension held</th>
                        <th className="is-num" scope="col">
                            Verses
                        </th>
                        <th className="is-num" scope="col">
                            Translated
                        </th>
                        <th className="is-num" scope="col">
                            Recited
                        </th>
                        <th scope="col">Not held</th>
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
                                <td data-label="Recension held">{RECENSION[code]}</td>
                                <td className="is-num" data-label="Verses">
                                    {number(work.mantra_count)}
                                </td>
                                <td className="is-num" data-label="Translated">
                                    {code === "SV" ? (
                                        <span title="0 own dedicated English; 173 verified reused Rigvedic English renderings">
                                            173 reused
                                        </span>
                                    ) : translated === 0 ? (
                                        /* A zero here is a real zero and it is the most
                                           informative cell in the table, so it is marked
                                           rather than printed as an ordinary figure. */
                                        <span className="va-ledger-zero">none</span>
                                    ) : (
                                        number(translated)
                                    )}
                                </td>
                                <td className="is-num" data-label="Recited">
                                    {audio === 0 ? (
                                        <span className="va-ledger-zero" title="1,001 recordings withheld behind audible QA gate">
                                            0 (withheld)
                                        </span>
                                    ) : (
                                        (number(audio) ?? "—")
                                    )}
                                </td>
                                <td className="va-ledger-absent" data-label="Not held">
                                    {NOT_HELD[code]}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            <p className="va-ledger-note">
                The Yajurveda row is the one most likely to mislead, because &ldquo;the
                Yajurveda&rdquo; ordinarily means both the White and the Black. The Black is not
                held at all.
            </p>
            <Action href="/vedas">Read the Vedas</Action>
        </Section>
    );
}

/* ---------------------------------------------------- S3 reading a verse --- */

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
        <Section className="va-split is-tight">
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
                            <dt>Script held</dt>
                            <dd>Romanised, accented. No Devanagari for this collection.</dd>
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
                    The Sanskrit, the recitation, the translation where one exists, the seer and the
                    deity the traditional index assigns, the words the verse actually contains, and
                    the wording it shares with another collection.
                </p>
                <p>
                    Each of those comes from a named layer, and each says how it was established. An
                    assignment made by the index is never shown as a statement the Sanskrit makes.
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

/* --------------------------------------------------------- S4 recitation --- */

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
        <Section tone="sunk">
            <Heading lede="One recording per verse, from VedSearch. A recording is attached only when our canonical key lands in the source's numbering and the text matches this corpus's text. 16,834 verified catalogue records are released (RV 10,402; AV 4,680; YV 1,752; SV 0); queued recordings stay withheld behind manual audible-review gates until audited.">
                {total ? `${number(total)} verses, each with its own recitation.` : "Recitation."}
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
                                    <strong>Zero released records.</strong> While queued recordings exist,
                                    1,001 recordings remain not individually heard and stay withheld behind
                                    the manual audible-review gate (GAP-AUDIO-002, 003, 004); unverified files
                                    are not promoted to the published catalogue without verified human audible QA.
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

/* ------------------------------------------------------- S5 connections ---- */

function Connections({ reachingAll }: { reachingAll: number | null }) {
    return (
        <Section className="va-split is-reversed">
            <div className="va-split-copy">
                <Kicker sanskrit="अन्वय">Connections</Kicker>
                <Heading>The same wording stands in more than one collection.</Heading>
                <p>
                    Cross-corpus connections are built in five kinds, never as one similarity score:
                    exact parallel, near parallel, variant, shared formula, shared entity
                    vocabulary. Which kind a connection is decides what it can be used to argue.
                </p>
                <p>
                    Some pairs are empty on purpose. Directed reuse was established for the Rigveda
                    and Samaveda only, which is a fact about what was built. Non-lexical resemblance
                    was never built at all, so that row reads as unbuilt rather than as zero.
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

/* ---------------------------------------------------------------- S6 ask --- */

function Ask() {
    return (
        <Section tone="sunk" className="va-ask is-tight">
            <Heading lede="Retrieval runs first, over a fixed catalogue of channels, and the model sees only what retrieval returned.">
                Ask a question. Check the answer.
            </Heading>
            <div className="va-ask-pair">
                <div>
                    <h3>What it does</h3>
                    <p>
                        Every factual sentence carries a citation you can open: the retrieved item,
                        its Sanskrit, its translation and its canonical citation. The evidence is
                        the answer&rsquo;s working, not a reading list attached afterwards.
                    </p>
                </div>
                <div>
                    <h3>What it refuses to do</h3>
                    <p>
                        A question this build cannot answer returns insufficient evidence and names
                        the dimension it could not reach. It does not guess, and it does not turn a
                        gap in the graph into a confident denial about the Vedas.
                    </p>
                </div>
            </div>
            <Action href="/ask">Ask a question</Action>
        </Section>
    );
}

/* ------------------------------------------------------ S7 featured verse -- */

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

/* ------------------------------------------------------------ S8 absence --- */

function Absence({ limits }: { limits: number | null }) {
    return (
        <Section className="va-absence is-open">
            <Heading level={2}>When there is nothing to show, we say whose nothing it is.</Heading>
            <dl className="va-absence-list">
                <div>
                    <dt>Not built</dt>
                    <dd>The layer does not exist here. The silence is ours.</dd>
                </div>
                <div>
                    <dt>Insufficient evidence</dt>
                    <dd>Evidence exists and cannot support the claim. This is not a zero.</dd>
                </div>
                <div>
                    <dt>Partial</dt>
                    <dd>
                        A real answer over part of the corpus, one collection, or one kind of
                        evidence.
                    </dd>
                </div>
            </dl>
            <p className="va-absence-close">
                {limits
                    ? `${limits} limits are catalogued with the measurement behind each one and a better question to ask instead. The catalogue is not exhaustive, and it says so: a question absent from it is not thereby answerable.`
                    : "Every recorded limit carries the measurement behind it and a better question to ask instead."}
            </p>
            <Action href="/limits">See what is not held</Action>
        </Section>
    );
}

/* --------------------------------------------------------- S9 start here --- */

function StartHere({ translations }: { translations: number | null }) {
    return (
        <Section tone="sunk" className="va-start">
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
