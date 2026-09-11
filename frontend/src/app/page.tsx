import {
    ArrowRight,
    BookOpenText,
    CirclesThreePlus,
    FirstAidKit,
    Flask,
    MagnifyingGlass,
    Repeat,
    Sparkle,
} from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { ServiceUnavailable } from "@/components/empty-state";
import { HomeNetwork } from "@/components/home-network";
import { Caveat } from "@/components/status";
import {
    encoded,
    load,
    vedaOrder,
    workSlugs,
    type GraphData,
    type Stats,
    type WorksResponse,
} from "@/lib/api";

const VEDA_BLURB: Record<string, string> = {
    RV: "Hymns arranged in ten mandalas, held with accented text and near-complete translation coverage.",
    SV: "The Kauthuma arcika verse collection, drawn largely from the Rigveda and rearranged for chanting.",
    YV: "The Vajasaneyi Madhyandina recension of the Shukla Yajurveda, the liturgist's book of formulae.",
    AV: "The Saunaka recension, turned towards healing, protection, the household and the concerns of a life.",
};

const VEDA_BOUNDARY: Record<string, string | undefined> = {
    SV: "Gana collections and musical information are not included.",
    YV: "The Krishna Yajurveda is not included.",
    AV: "The Paippalada recension is not included.",
};

const DISCOVERIES = [
    {
        href: `/devatas/${encoded("VG:DEVATA:INDRAH")}`,
        icon: Sparkle,
        title: "Explore Indra across the Vedas",
        note: "What one deity does, and where it is named",
    },
    {
        href: `/passage/${encoded("VG:RV:SAK:M01:S001:V001")}`,
        icon: BookOpenText,
        title: "Read the first verse of the Rigveda",
        note: "Sanskrit, translation, context and provenance",
    },
    {
        href: "/connections",
        icon: Repeat,
        title: "See Rigvedic verses reappear in the Samaveda",
        note: "Reuse and formula relationships, kept distinct",
    },
    {
        href: `/devatas/${encoded("VG:DEVATA:SOMAH")}`,
        icon: Flask,
        title: "Explore Soma as deity and as substance",
        note: "One word, two records, both linked",
    },
    {
        href: "/explore/atharvaveda",
        icon: FirstAidKit,
        title: "Explore Atharvavedic healing",
        note: "Afflictions, threats and what the texts address",
    },
    {
        href: "/formulas",
        icon: CirclesThreePlus,
        title: "Follow a formula through four collections",
        note: "Shared wording, traced where it travels",
    },
];

export default async function Home() {
    const [statsResult, worksResult, graphResult] = await Promise.all([
        load<Stats>("/stats"),
        load<WorksResponse>("/works"),
        load<GraphData>(
            `/graph/neighborhood/${encoded("VG:DEVATA:INDRAH")}?depth=1&limit_per_type=3`,
        ),
    ]);

    if (!statsResult.ok || !worksResult.ok) {
        return (
            <div className="shell page">
                <ServiceUnavailable />
            </div>
        );
    }
    const stats = statsResult.data;
    const works = [...(worksResult.data.items ?? [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );

    const mantras = stats.corpus?.find((item) => item.name === "mantras")?.total ?? 0;
    const formulas =
        stats.entity_populations?.find((item) => item.name === "formula_families")?.total ?? 0;

    return (
        <>
            <section className="shell hero">
                <div className="hero-copy">
                    <p className="hero-kicker">A digital atlas of the Vedas</p>
                    <h1>Four collections, read as one connected corpus.</h1>
                    <p className="hero-lede">
                        Read a mantra, follow its deity across the four Samhitas, trace its wording
                        into another collection, and ask any connection to show you its evidence.
                    </p>
                    <div className="hero-actions">
                        <Link className="button primary" href="/vedas">
                            <BookOpenText size={18} aria-hidden="true" />
                            Explore the Vedas
                        </Link>
                        <Link className="button secondary" href="/search">
                            <MagnifyingGlass size={18} aria-hidden="true" />
                            Search the corpus
                        </Link>
                        <Link className="button secondary" href="/graph">
                            <CirclesThreePlus size={18} aria-hidden="true" />
                            Open the knowledge graph
                        </Link>
                    </div>
                </div>
                <div className="hero-visual">
                    {graphResult.ok ? (
                        <HomeNetwork data={graphResult.data} />
                    ) : (
                        <div className="graph-frame compact is-empty">
                            <p>The live neighbourhood could not be read just now.</p>
                        </div>
                    )}
                </div>
            </section>

            <section className="shell metric-strip" aria-label="What this atlas holds">
                <div className="metric">
                    <strong>{mantras.toLocaleString()}</strong>
                    <span>mantras addressed</span>
                </div>
                <div className="metric">
                    <strong>{works.length}</strong>
                    <span>Samhita collections</span>
                </div>
                <div className="metric">
                    <strong>{formulas.toLocaleString()}</strong>
                    <span>formula families</span>
                </div>
                <div className="metric">
                    <strong>{stats.deities?.resolved_deities?.toLocaleString() ?? "—"}</strong>
                    <span>resolved deities</span>
                </div>
            </section>

            <section className="shell section">
                <div className="section-heading">
                    <h2>Four collections, each with its own shape.</h2>
                    <p>
                        Every collection keeps its native hierarchy, its stated scope and its
                        declared boundaries. None of them is flattened into a common template.
                    </p>
                </div>
                <div className="veda-grid">
                    {works.map((work) => {
                        const code = work.veda ?? "RV";
                        return (
                            <Link
                                className="veda-card"
                                href={`/vedas/${workSlugs[code]}`}
                                key={work.work_id}
                            >
                                <div>
                                    <div className="veda-card-top">
                                        <span className="veda-code">{code}</span>
                                        <ArrowRight size={20} aria-hidden="true" />
                                    </div>
                                    <h3>{work.traditional_name}</h3>
                                    <p>{VEDA_BLURB[code]}</p>
                                </div>
                                <div className="veda-card-bottom">
                                    <div className="veda-count">
                                        {work.mantra_count?.toLocaleString()}
                                        <span>mantras</span>
                                    </div>
                                    {VEDA_BOUNDARY[code] && (
                                        <div className="scope-warning">{VEDA_BOUNDARY[code]}</div>
                                    )}
                                </div>
                            </Link>
                        );
                    })}
                </div>
                <Caveat title="What this atlas holds">
                    Four Samhitas and nothing beyond them. No Brahmana, Aranyaka, Upanisad, Sutra or
                    second recension is present, so an absence measured here is an absence from
                    these four collections only.{" "}
                    <Link className="text-link" href="/limits">
                        See every recorded limit
                    </Link>
                </Caveat>
            </section>

            <section className="shell section discovery-layout">
                <div className="section-heading">
                    <h2>Enter through a question.</h2>
                    <p>
                        Move from text to entity, relationship and exact evidence without learning
                        the database underneath.
                    </p>
                </div>
                <div className="discovery-list">
                    {DISCOVERIES.map((item) => (
                        <Link className="discovery-link" href={item.href} key={item.href}>
                            <span className="icon">
                                <item.icon size={20} weight="duotone" aria-hidden="true" />
                            </span>
                            <span>
                                <strong>{item.title}</strong>
                                <small>{item.note}</small>
                            </span>
                            <ArrowRight size={18} aria-hidden="true" />
                        </Link>
                    ))}
                </div>
            </section>

            <section className="shell section evidence-pitch">
                <div>
                    <h2>Every connection can explain itself.</h2>
                    <p>
                        Select any relationship in the graph and the atlas answers in plain
                        language: what the relationship is, how it was established, which passage
                        carries it, and what it does not establish. Where the evidence cannot settle
                        a question, the interface says so rather than filling the gap with a zero.
                    </p>
                    <div className="hero-actions">
                        <Link className="button secondary" href="/insights">
                            Evidence and interpretation
                        </Link>
                        <Link className="button secondary" href="/limits">
                            What this atlas cannot answer
                        </Link>
                    </div>
                </div>
            </section>
        </>
    );
}
