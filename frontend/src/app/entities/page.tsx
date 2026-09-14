import Link from "next/link";
import { LoadFailure } from "@/components/empty-state";
import { Caveat, CaveatList } from "@/components/status";
import { load, type EntityInventory } from "@/lib/api";
import { humanizePredicate, titleCase } from "@/lib/knowledge";

export const metadata = {
    title: "People, ideas and things",
    description: "Browse the curated knowledge types that surround the four Samhitas.",
};

const GROUPS: Array<{ title: string; note: string; slugs: string[] }> = [
    {
        title: "People",
        note: "Seers, their families, and the peoples the texts name.",
        slugs: ["rishi", "rishi_family", "tribe", "ritual_role"],
    },
    {
        title: "Ideas and acts",
        note: "Concepts, actions, qualities and states the texts work with.",
        slugs: [
            "concept",
            "philosophical_concept",
            "action_predicate",
            "quality",
            "state",
            "human_concern",
            "deity_axis",
            "epithet",
        ],
    },
    {
        title: "Rites",
        note: "Rituals, offerings and the social rites around a household.",
        slugs: ["ritual", "offering", "social_rite", "chandas"],
    },
    {
        title: "The material world",
        note: "Things named in the texts: what is held, grown, worn, mined and crossed.",
        slugs: [
            "object",
            "weapon",
            "substance",
            "plant",
            "animal",
            "crop",
            "metal",
            "river",
            "place",
            "natural_phenomenon",
            "cosmic_entity",
        ],
    },
    {
        title: "Health and harm",
        note: "Afflictions, threats and named causes, which are three different things.",
        slugs: ["condition"],
    },
];

export default async function EntitiesPage() {
    const result = await load<EntityInventory>("/entities");
    if (!result.ok) {
        return (
            <div className="shell page">
                <LoadFailure status={result.status} message={result.message} />
            </div>
        );
    }
    const types = result.data.types ?? [];
    const byslug = new Map(types.map((type) => [type.slug, type]));
    const grouped = new Set(GROUPS.flatMap((group) => group.slugs));
    const remainder = types.filter(
        (type) => !grouped.has(type.slug) && !["formula", "formula_family"].includes(type.slug),
    );

    return (
        <div className="va-page">
            <header className="va-page-head">
                <h1>People, ideas and things.</h1>
                <p>
                    The curated knowledge types around the texts. Every count describes this
                    graph rather than an exhaustive Vedic taxonomy: a type with eight members is
                    a selection, and the type&rsquo;s own page says what it covers.
                </p>
            </header>

            <Caveat title="Deities are elsewhere">
                Deities are not served by this generic surface, because resolving the tradition&rsquo;s
                dedication slot into actual gods is a contract only the deity pages apply.{" "}
                <Link className="text-link" href="/devatas">
                    Open the deity index
                </Link>
            </Caveat>

            {[
                ...GROUPS.map((group) => ({
                    ...group,
                    items: group.slugs.map((slug) => byslug.get(slug)).filter(Boolean),
                })),
                ...(remainder.length
                    ? [
                          {
                              title: "Other types",
                              note: "Everything else registered in this graph.",
                              items: remainder,
                          },
                      ]
                    : []),
            ].map((group) => (
                <section className="va-group entity-group" key={group.title}>
                    <h2>
                        {group.title}
                        <span>{group.items.length} types</span>
                    </h2>
                    <p>{group.note}</p>
                    <ul className="va-index">
                        {group.items.map((type) =>
                            type ? (
                                <li key={type.slug}>
                                    <Link href={`/entities/${type.slug}`}>
                                        <span className="va-index-name">
                                            <strong>
                                                {titleCase(humanizePredicate(type.type))}
                                            </strong>
                                        </span>
                                        <span className="va-index-note">{type.note ?? ""}</span>
                                        <span className="va-index-figure">
                                            {type.count?.toLocaleString("en-GB") ?? "not read"}
                                            <small>registered</small>
                                        </span>
                                    </Link>
                                </li>
                            ) : null,
                        )}
                    </ul>
                </section>
            ))}

            <CaveatList caveats={result.data.caveats} title="What these counts mean" />
        </div>
    );
}
