import { PageHeading } from "@/components/page-heading";
import { SearchExperience } from "@/components/search-experience";

export const metadata = {
    title: "Search",
    description:
        "One ranked search across Sanskrit text, canonical citations, translations and every registered entity.",
};

export default async function SearchPage({
    searchParams,
}: {
    searchParams: Promise<{ q?: string; type?: string; veda?: string }>;
}) {
    const { q = "", type = "", veda = "" } = await searchParams;
    return (
        <div className="shell page search-page">
            <PageHeading
                title="Search the corpus"
                description="Canonical keys and citations, Sanskrit surfaces, English translations and registered entity labels are all searched at once, and every result says how it matched."
            />
            <SearchExperience initialQuery={q} initialType={type} initialVeda={veda} />
        </div>
    );
}
