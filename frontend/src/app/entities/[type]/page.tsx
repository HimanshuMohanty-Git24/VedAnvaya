import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LoadFailure, NothingHere } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { Caveat, CaveatList } from "@/components/status";
import { routeId, encoded, load, type EntityListResponse } from "@/lib/api";
import { conditionLabel, conditionNote, humanizePredicate, titleCase } from "@/lib/knowledge";

const KIND_TABS = [
    { value: "AFFLICTION", label: "Afflictions" },
    { value: "THREAT", label: "Threats" },
    { value: "PATHOGEN_OR_CAUSE", label: "Named causes" },
    { value: "ANY", label: "All three" },
];

const TYPE_INTRO: Record<string, string> = {
    condition:
        "Afflictions are shown by default. Threats and named causes are different kinds of thing and are never presented as diseases.",
    rishi: "Names recorded in the seer slot of the traditional apparatus. Some of them are not seers, and each row says so.",
    rishi_family:
        "Seer families as the apparatus groups them. A name with no family is not thereby familyless.",
    formula_family:
        "Shared wording grouped into families. A family measures diction, not a demonstrated line of transmission.",
};

type Params = {
    params: Promise<{ type: string }>;
    searchParams: Promise<{ kind?: string }>;
};

export async function generateMetadata({ params }: Params) {
    const { type: rawType } = await params;
    const type = routeId(rawType);
    return { title: titleCase(humanizePredicate(type)) };
}

export default async function EntityTypePage({ params, searchParams }: Params) {
    const { type: rawType } = await params;
    const type = routeId(rawType);
    const { kind } = await searchParams;
    const isCondition = type === "condition";
    const activeKind = isCondition ? (kind ?? "AFFLICTION") : null;

    const query = new URLSearchParams({ limit: "80" });
    if (activeKind) query.set("kind", activeKind);
    const result = await load<EntityListResponse>(`/entities/${encodeURIComponent(type)}?${query}`);
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const data = result.data;
    const title = titleCase(humanizePredicate(type));

    return (
        <div className="shell page">
            <PageHeading
                title={title}
                description={
                    TYPE_INTRO[type] ??
                    "A curated, evidence-aware list from the frozen product graph."
                }
                backHref="/entities"
                backLabel="All entity types"
            />

            {isCondition && (
                <>
                    <nav className="kind-tabs" aria-label="Condition kind">
                        {KIND_TABS.map((tab) => (
                            <Link
                                key={tab.value}
                                href={`/entities/condition?kind=${tab.value}`}
                                aria-current={activeKind === tab.value ? "page" : undefined}
                            >
                                {tab.label}
                            </Link>
                        ))}
                    </nav>
                    <Caveat title={conditionLabel(activeKind)}>
                        {activeKind === "ANY"
                            ? "All three kinds are shown together and each row is labelled. A threat is a hostile agent the texts guard against, not a disease."
                            : conditionNote(activeKind)}
                    </Caveat>
                </>
            )}

            {data.items?.length ? (
                <div className="entity-index">
                    {data.items.map((item) => (
                        <Link
                            href={`/entities/${type}/${encoded(item.id)}`}
                            className="entity-index-row"
                            key={item.id}
                        >
                            <div>
                                <span
                                    className={
                                        isCondition
                                            ? `condition-kind kind-${(item.kind ?? "").toLowerCase()}`
                                            : undefined
                                    }
                                >
                                    {isCondition
                                        ? conditionLabel(item.kind)
                                        : item.is_seer === false
                                          ? `not a seer: ${humanizePredicate(item.non_seer_kind)}`
                                          : (item.subtitle ?? humanizePredicate(item.type))}
                                </span>
                                <h2>{item.display_label}</h2>
                                {item.short_description && <p>{item.short_description}</p>}
                            </div>
                            <div className="certainty-mini">
                                {item.passage_count == null ? (
                                    <span>passage count not established</span>
                                ) : (
                                    <>
                                        <strong>{item.passage_count.toLocaleString()}</strong>
                                        <span>linked passages</span>
                                    </>
                                )}
                            </div>
                            <ArrowRight size={18} aria-hidden="true" />
                        </Link>
                    ))}
                </div>
            ) : (
                <NothingHere
                    title="Nothing is registered under this type yet"
                    message="The type exists in the inventory and no entity was returned for it. That is a limit of what was built, not a statement about the texts."
                    action={{ href: "/entities", label: "Back to the type index" }}
                />
            )}

            <CaveatList caveats={data.caveats} title="How this list was scoped" limit={5} />
        </div>
    );
}
