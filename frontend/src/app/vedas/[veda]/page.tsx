import { ArrowRight, CirclesThreePlus, MagnifyingGlass } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { StructureBrowser } from "@/components/structure-browser";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import {
    encoded,
    firstFailure,
    load,
    vedaNames,
    workIds,
    type DevatasResponse,
    type WorkRoot,
    type WorksResponse,
} from "@/lib/api";

const SCOPE_NOTE: Record<string, string> = {
    RV: "Sakala recension, Samhita only. No Brahmana, Aranyaka or Upanisad layer is held.",
    SV: "Kauthuma arcika only. The gana collections and the melodic apparatus are not held.",
    YV: "Shukla Yajurveda in the Vajasaneyi Madhyandina recension. The Krishna Yajurveda is not held at all.",
    AV: "Saunaka recension, held as a working private corpus. The Paippalada recension is not held.",
};

const BOUNDARY: Record<string, { title: string; body: string } | undefined> = {
    SV: {
        title: "Gana collections are not included",
        body: "This is the Kauthuma arcika verse corpus. The gana collections and complete musical information are not present, so nothing in this product shows, notates or infers how a verse was sung.",
    },
    YV: {
        title: "Krishna Yajurveda is not included",
        body: "Only the Shukla (White) Yajurveda in the Vajasaneyi Madhyandina recension is held. No Taittiriya, Kathaka, Maitrayani or Kapisthala samhita is present, so an absence measured here is an absence from one recension.",
    },
    AV: {
        title: "Paippalada is not included",
        body: "The Saunaka recension is held. The Paippalada recension is a substantially different collection with its own hymn order and is not present, so an Atharvavedic absence measured here is an absence from Saunaka only.",
    },
};

type Params = { params: Promise<{ veda: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { veda } = await params;
    const name = vedaNames[veda.slice(0, 2).toUpperCase()] ?? veda;
    return { title: name.charAt(0).toUpperCase() + name.slice(1) };
}

export async function generateStaticParams() {
    return Object.keys(workIds).map((veda) => ({ veda }));
}

export default async function VedaPage({ params }: Params) {
    const { veda } = await params;
    const workId = workIds[veda];
    if (!workId) notFound();

    const [worksResult, rootResult] = await Promise.all([
        load<WorksResponse>("/works"),
        load<WorkRoot>(`/works/${encoded(workId)}/root?limit=60`),
    ]);
    const failure = firstFailure(worksResult, rootResult);
    if (failure || !worksResult.ok || !rootResult.ok) {
        return (
            <div className="shell page">
                <LoadFailure
                    status={failure?.status ?? 503}
                    message={failure?.message ?? "This collection could not be loaded."}
                />
            </div>
        );
    }

    const work = worksResult.data.items?.find((item) => item.work_id === workId);
    if (!work) notFound();
    const root = rootResult.data;
    const code = work.veda ?? "RV";
    const boundary = BOUNDARY[code];

    const deitiesResult = await load<DevatasResponse>("/devatas?limit=8");
    const deities = deitiesResult.ok ? (deitiesResult.data.items ?? []) : [];

    return (
        <div className="shell page">
            <PageHeading
                title={work.traditional_name ?? root.traditional_name ?? veda}
                description={work.display_label}
                backHref="/vedas"
                backLabel="All four Vedas"
            />

            <div className="content-grid">
                <div>
                    <div className="collection-metrics">
                        <div>
                            <strong>{work.mantra_count?.toLocaleString()}</strong>
                            <span>addressed mantras</span>
                        </div>
                        <div>
                            <strong>{work.translated_mantra_count?.toLocaleString()}</strong>
                            <span>carry a translation</span>
                        </div>
                        <div>
                            <strong>{root.root_level?.passage_count?.toLocaleString()}</strong>
                            <span>{root.root_level?.native_label ?? "root entries"}</span>
                        </div>
                    </div>

                    {boundary && (
                        <Caveat title={boundary.title} tone="boundary">
                            {boundary.body}
                        </Caveat>
                    )}

                    <StructureBrowser
                        items={root.results?.items ?? []}
                        nativeLabel={root.root_level?.native_label ?? "structure"}
                    />
                </div>

                <aside className="sticky-aside">
                    <div className="panel">
                        <h3>Corpus status</h3>
                        <div className="aside-status">
                            <KnowledgeStatus status={work.data_status} />
                        </div>
                        <p>{SCOPE_NOTE[code]}</p>
                    </div>

                    <div className="panel">
                        <h3>Start somewhere</h3>
                        <div className="panel-links">
                            <Link href={`/search?q=${encodeURIComponent(code)}`}>
                                <MagnifyingGlass size={17} aria-hidden="true" />
                                Search inside this collection
                            </Link>
                            <Link href={`/graph?node=${encoded(workId)}`}>
                                <CirclesThreePlus size={17} aria-hidden="true" />
                                Open this work in the graph
                            </Link>
                        </div>
                    </div>

                    {deities.length > 0 && (
                        <div className="panel">
                            <h3>Deities across the corpus</h3>
                            <p className="panel-note">
                                Ranked over all four collections, not within this one.
                            </p>
                            <div className="chip-row">
                                {deities.slice(0, 8).map((deity) => (
                                    <Link href={`/devatas/${encoded(deity.id)}`} key={deity.id}>
                                        {deity.display_label}
                                    </Link>
                                ))}
                            </div>
                            <Link className="text-link" href="/devatas">
                                All deity profiles
                                <ArrowRight size={15} aria-hidden="true" />
                            </Link>
                        </div>
                    )}

                    <CaveatList caveats={work.caveats} title="Scope notes for this work" />
                </aside>
            </div>
        </div>
    );
}
