import { SearchExperience } from "@/components/search-experience";

export const metadata = {
    title: "Search",
    description:
        "One ranked search across Sanskrit text, canonical citations, translations and every registered entity.",
};

/**
 * The finding aid.
 *
 * No eyebrow and no rule under the title. Fifteen routes opened with the same four-part
 * figure and the repetition carried nothing; what a reader arriving here needs is the field,
 * immediately, and one sentence saying what it reaches.
 */
export default async function SearchPage({
    searchParams,
}: {
    searchParams: Promise<{ q?: string; type?: string; veda?: string }>;
}) {
    const { q = "", type = "", veda = "" } = await searchParams;
    return (
        <div className="va-page search-page">
            <header className="va-open">
                <h1>Search the corpus</h1>
                <p className="va-open-lede">
                    Canonical keys and citations, Sanskrit surfaces, English translations and
                    registered entity labels are all read at once, and every record says how it
                    matched.
                </p>
            </header>
            <SearchExperience initialQuery={q} initialType={type} initialVeda={veda} />
        </div>
    );
}
