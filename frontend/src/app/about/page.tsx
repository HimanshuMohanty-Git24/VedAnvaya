import Link from "next/link";
import type { Metadata } from "next";
import { load, type Stats, type WorksResponse } from "@/lib/api";
import { count } from "@/lib/lab";

/**
 * About VedAnvaya.
 *
 * Written in the first person, because a project built by one person and described in the
 * corporate plural is lying about something small in a way that makes the reader doubt the
 * larger things. The figures are read from the API rather than typed in, for the same reason
 * every figure in the Lab is: a sentence with a number in it should not be able to go stale
 * quietly. If the service is unreachable the page still renders — this is the one surface a
 * reader might arrive at precisely because something else was broken.
 */

export const revalidate = 3600;

export const metadata: Metadata = {
    title: "About",
    description:
        "VedAnvaya is a reading and research interface for the four Vedic Samhitas, built by one person to make the connections between them followable. What it is, why it exists, how it was made, and what it is not.",
    openGraph: {
        title: "About VedAnvaya",
        description:
            "A reading and research interface for the four Vedic Samhitas, and an account of how it was built and what it does not do.",
    },
};

const CONTENTS = [
    { id: "what", label: "What this is" },
    { id: "why", label: "Why it exists" },
    { id: "what-you-can-do", label: "What you can do here" },
    { id: "evidence", label: "Why the evidence matters" },
    { id: "story", label: "How it was built" },
    { id: "builder", label: "Who built it" },
    { id: "not", label: "What VedAnvaya is not" },
];

const NOT: { title: string; body: string }[] = [
    {
        title: "Not a replacement for reading the Vedas",
        body: "Nothing here is a substitute for sitting with a text. A graph can show you that a phrase appears in four collections; it cannot tell you what it is like to read the hymn it belongs to.",
    },
    {
        title: "Not philology",
        body: "The textual work here is ingestion, alignment and provenance — reconciling editions, pinning citations, recording what a witness says. That is a different discipline from establishing a text, and this project does not do the second.",
    },
    {
        title: "Not a commentary",
        body: "The commentarial traditions — Sayana, and everything before and since — are not held here and are not summarised. Where this site offers an interpretation it says so and marks it as one reading among possible others.",
    },
    {
        title: "Not a teacher",
        body: "The Vedas were transmitted by people, to people, for three thousand years before anyone wrote them down. That relationship is not something software participates in.",
    },
    {
        title: "Not a claim about history",
        body: "Counting how often a word appears tells you about the corpus. It does not tell you about the society that produced it, and this site is careful never to let the first quietly stand in for the second.",
    },
    {
        title: "Not finished",
        body: "The Samavedic gana corpus is absent, the Krishna Yajurveda is absent, several layers reach one collection and not the others. The limits page is a real page with real entries in it, not a disclaimer.",
    },
];

export default async function AboutPage() {
    const [stats, works] = await Promise.all([
        load<Stats>("/stats"),
        load<WorksResponse>("/works"),
    ]);
    const verses = stats.ok
        ? (stats.data.corpus?.find((row) => row.name === "mantras")?.total ?? null)
        : null;
    const collections = works.ok ? (works.data.items?.length ?? null) : null;

    return (
        <div className="va-doc">
            <header className="va-doc-head">
                <p className="va-doc-eyebrow">About</p>
                <h1>I wanted this to exist, so I built it.</h1>
                <p className="va-doc-lede">
                    VedAnvaya is a reading and research interface for the four Vedic Samhitas. It
                    holds {verses ? count(verses) : "roughly twenty thousand"} verses across{" "}
                    {collections ?? "four"} collections, with the deities, seers, rites, conditions
                    and shared wording that connect them — and with a statement, attached to every
                    figure, of what that figure does not establish.
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
                    <section id="what">
                        <h2>What this is</h2>
                        <p className="va-doc-open">
                            The Vedas are usually met one verse at a time, in a book, in order. That
                            is the right way to read them and a poor way to see them. A hymn to Agni
                            in the first mandala of the Rigveda is connected to a verse in the
                            Samaveda that reuses it, to a formula that turns up in the Atharvaveda,
                            to a metre it shares with hundreds of other hymns, and to a seer whose
                            family composed a whole book. None of that is visible on the page.
                        </p>
                        <p>
                            VedAnvaya is an attempt to make it visible without making it up. Every
                            connection here is one of a small number of stated kinds — an exact
                            parallel, a directed reuse, a shared formula, a named deity, a
                            traditional ascription — and each kind carries its own scope and its own
                            evidence. There is no single similarity score anywhere in this product,
                            because the eight things it would average are not degrees of one
                            quantity.
                        </p>
                        <p>
                            The name is{" "}
                            <span className="va-deva-label" lang="sa">
                                वेदान्वय
                            </span>
                            , <i>vedānvaya</i>: the following of a connection through the Veda.{" "}
                            <i>Anvaya</i> is the grammarian&rsquo;s word for the thread you follow
                            to resolve a sentence — the order in which the words actually connect,
                            as opposed to the order in which they are written. That is close enough
                            to what this is doing.
                        </p>
                    </section>

                    <section id="why">
                        <h2>Why it exists</h2>
                        <p>
                            I started this because I kept wanting to ask questions that the
                            available tools could not answer, and because the questions were not
                            exotic. Which deity does the Atharvaveda actually invoke most, once you
                            account for it being a little over half the size of the Rigveda? Which
                            Rigvedic verses does the Samaveda take, and does it change them? What
                            does the corpus name when it talks about illness, and is a demon in that
                            list?
                        </p>
                        <p>
                            Each of these is answerable, and each of them is answerable wrongly in a
                            way that looks fine. The last one is the example I keep coming back to:
                            an early version of this project asked what conditions the corpus
                            addresses and returned a confident ranked list whose top entries were
                            demons and sorcery. The numbers were correct. The answer was not,
                            because the question was about illness and the data was about everything
                            a verse asks protection from. Fixing it took typing every condition in
                            the registry as an affliction, a threat or a named cause, and it is why{" "}
                            <Link href="/visualizations/human-concerns">
                                that plate has two panels rather than one list
                            </Link>
                            .
                        </p>
                        <p>
                            So the project is as much about the failure modes as about the corpus. A
                            knowledge system over an ancient text is very good at producing answers
                            that are precise, reproducible and subtly about the wrong thing. Most of
                            the engineering here is spent making that harder.
                        </p>
                    </section>

                    <section id="what-you-can-do">
                        <h2>What you can do here</h2>
                        <ul>
                            <li>
                                <Link href="/vedas">Read any of the four collections</Link> by its
                                own divisions, with the Sanskrit, a translation where one exists, a
                                recitation where one is catalogued, and the source of each.
                            </li>
                            <li>
                                <Link href="/devatas">Follow a deity</Link>, a seer, a rite or a
                                condition across all four collections, and see where the layer that
                                tracks it stops.
                            </li>
                            <li>
                                <Link href="/visualizations">Read the plates</Link> — seven figures,
                                each answering one question about the corpus and stating what it
                                does not show.
                            </li>
                            <li>
                                <Link href="/graph">Open the knowledge graph</Link> and move through
                                the relationships themselves, asking any one of them to explain what
                                it is and where it came from.
                            </li>
                            <li>
                                <Link href="/ask">Ask a question in ordinary language</Link> and get
                                an answer whose every factual claim is tied to a verse you can open.
                            </li>
                            <li>
                                <Link href="/limits">Find out what cannot be answered</Link>, which
                                is a catalogue with entries rather than a paragraph of hedging.
                            </li>
                        </ul>
                    </section>

                    <section id="evidence">
                        <h2>Why the evidence matters</h2>
                        <p>
                            There is one rule underneath all of this, and it is the rule that costs
                            the most to keep:{" "}
                            <b>an absence must say which kind of absence it is.</b>
                        </p>
                        <p>
                            If you ask this product how many Samavedic verses carry an English
                            translation, the answer is zero — and that zero means no translation has
                            been released here, not that the Samaveda resists translation. If you
                            ask which Atharvavedic hymns are dedicated to Indra, the answer is that
                            the traditional index which records dedications exists for the Rigveda
                            and not for the Atharvaveda, so the question has no Atharvavedic answer
                            in this build. Neither of those is a zero you could have inferred, and
                            both are the kind of thing an interface returns as an empty list if
                            nobody makes it do otherwise.
                        </p>
                        <p>
                            That is why coverage statements travel with the data rather than sitting
                            in documentation, why a null is never drawn as a bar of length zero, and
                            why the <Link href="/sources">sources and method page</Link> is as long
                            as it is. The alternative — a clean interface that quietly turns gaps in
                            the build into facts about the Vedas — would be worse than not building
                            this at all.
                        </p>
                    </section>

                    <section id="story">
                        <h2>How it was built</h2>
                        <p>
                            It began in September 2026 as <b>VedaGraph</b>, which was a database
                            problem before it was anything else. The first question was not what to
                            show but what could honestly be loaded: which editions exist, what they
                            are licensed under, whether two witnesses to the same verse agree, and
                            what a canonical citation should even be for a corpus whose four
                            collections number their contents four different ways.
                        </p>
                        <p>
                            That work produced the layers everything else sits on, roughly in this
                            order. A provenance registry, so that every verse could name the file it
                            came from and the terms that file is held under. A canonical key and
                            citation for each verse, reconciled across witnesses. The traditional
                            apparatus — seer, deity, metre — where a collection has one. A lexical
                            mention layer, matching registered Sanskrit aliases against the text. A
                            relationship layer: exact parallels, near parallels, directed reuse,
                            variants, formula families. Then the product layers: a reader, a
                            recitation catalogue, a search index, an API, an Ask pipeline that
                            retrieves evidence before it generates anything, and finally the
                            three-dimensional knowledge world.
                        </p>
                        <p>
                            Along the way the ontology was rebuilt three times and frozen once. Each
                            rebuild came from an adversarial pass that found a new stratum of
                            something the model had been quietly wrong about — most often about what
                            counts as a deity, since the traditional index that names one for every
                            hymn also names twenty-two human patrons, seven praise-of-a-gift labels,
                            and a dog.
                        </p>
                        <p>
                            The name changed last. <b>VedaGraph</b> described the technique, and by
                            the time there was a reader, a recitation player and a graph you could
                            walk through, the technique was no longer the thing. <b>VedAnvaya</b>{" "}
                            describes what a person does with it. The internal identifiers still say{" "}
                            <code>VG:</code>, and they will keep saying it: renaming a stable
                            identity to match a brand is how you lose the ability to compare two
                            builds.
                        </p>
                    </section>

                    <section className="va-maker" id="builder">
                        <h2>Who built it</h2>
                        <p className="va-maker-open">
                            I am Himanshu Mohanty. I am a software engineer, and this is a personal
                            project — not a product, not a startup, and not affiliated with any
                            institution.
                        </p>
                        <p>
                            My working life is in software engineering, machine learning and the
                            design of systems that have to hold knowledge without distorting it. My
                            reading life is in history and language. This project sits exactly where
                            those overlap, which is why it exists: I wanted to ask structural
                            questions of the Vedas, I could not find a tool that would answer them
                            without inventing things, and building one turned out to be within
                            reach.
                        </p>
                        <p>
                            I am not a Sanskritist and I have not represented myself as one anywhere
                            on this site. What I have done is read carefully, record provenance
                            obsessively, and refuse to ship a figure I could not account for. Where
                            the corpus needed a judgement I was not qualified to make, the project
                            records the question rather than answering it — which is why{" "}
                            <Link href="/limits">the limits page</Link> is one of the larger things
                            here.
                        </p>
                        <p>
                            If you are a scholar and something on this site is wrong, I would
                            genuinely like to know. Most of the errors that have been caught so far
                            were caught by taking a confident-looking answer and asking what
                            question it was actually answering.
                        </p>
                        <p className="va-maker-sign">
                            <strong>Himanshu Mohanty</strong>
                            Begun September 2026. Still being worked on.
                        </p>
                    </section>

                    <section id="not">
                        <h2>What VedAnvaya is not</h2>
                        <p>
                            This matters enough to be its own section rather than a line in a
                            footer. VedAnvaya is a computational research and exploration interface.
                            It is not any of the following, and it does not want to be.
                        </p>
                        <ul className="va-doc-negations">
                            {NOT.map((item) => (
                                <li key={item.title}>
                                    <strong>{item.title}</strong>
                                    <span>{item.body}</span>
                                </li>
                            ))}
                        </ul>
                        <p>
                            What it can do is hold four collections of verses, and the layers built
                            over them, in a form where you can follow a connection, check it, and
                            find out what checking it did not establish. That is a narrow thing, and
                            it is worth doing well.
                        </p>
                    </section>

                    <nav aria-label="Where to go next" className="va-doc-onward">
                        <h2>Where to go next</h2>
                        <ul>
                            <li>
                                <Link href="/sources">
                                    <strong>Sources and method</strong>
                                    <span>
                                        Every edition behind every verse, and how the evidence model
                                        works
                                    </span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/visualizations">
                                    <strong>The visualizations</strong>
                                    <span>Seven plates, each answering one question</span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/limits">
                                    <strong>What this corpus cannot answer</strong>
                                    <span>
                                        The recorded limits, with the measurement behind each
                                    </span>
                                </Link>
                            </li>
                            <li>
                                <Link href="/vedas">
                                    <strong>Read the Vedas</strong>
                                    <span>Four collections, each by its own divisions</span>
                                </Link>
                            </li>
                        </ul>
                    </nav>
                </div>
            </div>
        </div>
    );
}
