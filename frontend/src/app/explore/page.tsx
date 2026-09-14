import Link from "next/link";
import { Caveat } from "@/components/status";

export const metadata = {
    title: "Lenses",
    description:
        "Curated ways into the corpus: deities, rites, human concerns, material culture and transmission.",
};

/**
 * Lenses are curated entry points, not separate datasets. Each one names the
 * knowledge layer it reads and what that layer does not establish.
 */
const LENSES = [
    {
        href: "/devatas",
        title: "Deities",
        blurb: "Who is invoked, what they do, and where each of them is named across the four collections.",
        reads: "Deity registry, mention layer, ascription apparatus",
        limit: "Ambiguous mentions are held back from every default figure.",
    },
    {
        href: "/rituals",
        title: "Ritual",
        blurb: "The rites the corpus names, who performs them, what is offered, and what the text actually describes.",
        reads: "Ritual layer, curated apparatus edges",
        limit: "Eight modelled rites against a corpus that names many more. Not a taxonomy.",
    },
    {
        href: "/explore/atharvaveda",
        title: "Human concerns",
        blurb: "Healing, protection, household life and prosperity, with afflictions kept apart from threats.",
        reads: "Condition and concern registries, lexical mention layer",
        limit: "Counts are Sanskrit lexical minima, never diagnoses.",
    },
    {
        href: "/material-culture",
        title: "Material culture",
        blurb: "Animals, crops, metals, rivers and peoples: what the texts name and where.",
        reads: "Entity registry, lexical mention layer",
        limit: "An empty cell is a matcher limit, and at least one is known to be wrong.",
    },
    {
        href: "/connections",
        title: "Cross-Veda transmission",
        blurb: "Shared wording between collections, kept as separate kinds of connection rather than one similarity score.",
        reads: "Parallel layer, formula families, directed reuse edges",
        limit: "Directed reuse exists for the Rigveda and Samaveda pair only.",
    },
];

export default function ExplorePage() {
    return (
        <div className="va-page">
            <header className="va-page-head">
                <h1>Five ways into the corpus.</h1>
                <p>
                    Each one reads a named knowledge layer and says what that layer does not
                    establish. They are routes through the same material, not separate datasets.
                </p>
            </header>

            <ul className="va-index">
                {LENSES.map((lens) => (
                    <li key={lens.href}>
                        <Link className="va-lens" href={lens.href}>
                            <span className="va-index-name">
                                <strong>{lens.title}</strong>
                            </span>
                            <span className="va-lens-body">
                                <span className="va-index-note">{lens.blurb}</span>
                                <span className="va-lens-layers">
                                    <span>
                                        <em>Reads</em> {lens.reads}
                                    </span>
                                    <span>
                                        <em>Does not establish</em> {lens.limit}
                                    </span>
                                </span>
                            </span>
                        </Link>
                    </li>
                ))}
            </ul>

            <Caveat title="No historical narrative is imposed">
                A lens groups what was measured. Where a view mixes measured data with a derived
                metric or a candidate interpretation, the three are kept visually distinct.{" "}
                <Link className="text-link" href="/insights">
                    See how that separation works
                </Link>
            </Caveat>
        </div>
    );
}
