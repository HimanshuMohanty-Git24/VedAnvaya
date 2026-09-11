import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList, KnowledgeStatus } from "@/components/status";
import { load, vedaOrder, workSlugs, type WorksResponse } from "@/lib/api";

export const metadata = {
    title: "The four Vedas",
    description: "Four Samhita corpora, presented with their native structures and stated limits.",
};

const NATIVE_STRUCTURE: Record<string, string> = {
    RV: "Mandala → Sukta → Mantra",
    SV: "Collection → Parvan → Dasati → Verse",
    YV: "Adhyaya → Mantra",
    AV: "Kanda → Sukta → Mantra",
};

const BOUNDARY: Record<string, string | undefined> = {
    SV: "Kauthuma arcika only. The gana collections and complete musical information are not included, so nothing here shows or infers melody.",
    YV: "Shukla Yajurveda in the Vajasaneyi Madhyandina recension only. The Krishna Yajurveda is not held at all.",
    AV: "Saunaka recension only, held as a working private corpus. The Paippalada recension is not held.",
    RV: "Sakala recension, Samhita only. No Brahmana, Aranyaka or Upanisad layer is held.",
};

export default async function VedasPage() {
    const result = await load<WorksResponse>("/works");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const works = [...(result.data.items ?? [])].sort(
        (a, b) => (vedaOrder[a.veda ?? ""] ?? 9) - (vedaOrder[b.veda ?? ""] ?? 9),
    );

    return (
        <div className="shell page">
            <PageHeading
                title="The four Vedas"
                description="Four Samhita corpora, each shown with its own hierarchy, its translation coverage and the boundary of what is held."
            />

            <div className="work-list">
                {works.map((work) => {
                    const code = work.veda ?? "RV";
                    const translated = work.translated_mantra_count ?? 0;
                    const total = work.mantra_count ?? 0;
                    return (
                        <article className="work-row" key={work.work_id}>
                            <div className="work-code">{code}</div>
                            <div>
                                <h2>{work.traditional_name}</h2>
                                <p>{work.display_label}</p>
                                <div className="work-facts">
                                    <span>
                                        <strong>{total.toLocaleString()}</strong> mantras
                                    </span>
                                    <span>
                                        <strong>{translated.toLocaleString()}</strong> translated
                                        {total > 0 && (
                                            <small>
                                                {" "}
                                                ({Math.round((translated / total) * 100)}%)
                                            </small>
                                        )}
                                    </span>
                                    <span>
                                        <strong>{NATIVE_STRUCTURE[code]}</strong>
                                    </span>
                                    <KnowledgeStatus status={work.data_status} compact />
                                </div>
                                {BOUNDARY[code] && (
                                    <Caveat title="Coverage boundary" tone="boundary">
                                        {BOUNDARY[code]}
                                    </Caveat>
                                )}
                            </div>
                            <Link className="button secondary" href={`/vedas/${workSlugs[code]}`}>
                                Open collection
                                <ArrowRight size={17} aria-hidden="true" />
                            </Link>
                        </article>
                    );
                })}
            </div>

            <CaveatList caveats={result.data.caveats} title="Scope of this list" />
        </div>
    );
}
