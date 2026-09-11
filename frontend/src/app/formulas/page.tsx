import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList } from "@/components/status";
import { encoded, load, type EntityListResponse, type FormulaDiffusion } from "@/lib/api";

export const metadata = {
    title: "Formula families",
    description:
        "Shared wording grouped into cores, expansions and variants across the four collections.",
};

export default async function FormulasPage() {
    const [listResult, diffusionResult] = await Promise.all([
        load<EntityListResponse>("/entities/formula_family?limit=60"),
        load<FormulaDiffusion>("/insights/formula-diffusion?limit=6"),
    ]);
    if (!listResult.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={listResult.status} message={listResult.message} />
            </div>
        );
    }
    const data = listResult.data;
    const census = diffusionResult.ok ? (diffusionResult.data.span_census ?? []) : [];
    return (
        <div className="shell page">
            <PageHeading
                title="Formula families"
                description="A family is one representative wording plus everything that contains or closely resembles it. Following a family across collections shows shared diction, and diction is not by itself a demonstrated line of transmission."
            />
            {census.length > 0 && (
                <div className="census-grid">
                    {census.map((row) => (
                        <article key={row.vedas_reached}>
                            <strong>{row.families?.toLocaleString()}</strong>
                            <span>
                                reach {row.vedas_reached}{" "}
                                {row.vedas_reached === 1 ? "collection" : "collections"}
                            </span>
                        </article>
                    ))}
                </div>
            )}
            <Caveat title="Reading a family">
                Core forms are the shared wording itself. Expansions contain it inside a longer
                phrase. Variants differ from it slightly. The three are counted separately.
            </Caveat>
            <div className="formula-list">
                {data.items?.map((item) => (
                    <Link href={`/formula-families/${encoded(item.id)}`} key={item.id}>
                        <span>{item.subtitle ?? "formula family"}</span>
                        <strong className="sanskrit" lang="sa">
                            {item.display_label}
                        </strong>
                        <small>
                            {item.passage_count == null
                                ? "passage count not established"
                                : `${item.passage_count.toLocaleString()} passages`}
                        </small>
                        <ArrowRight size={17} aria-hidden="true" />
                    </Link>
                ))}
            </div>
            <CaveatList caveats={data.caveats} title="How families were built" />
        </div>
    );
}
