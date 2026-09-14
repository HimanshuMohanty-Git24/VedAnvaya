import { redirect } from "next/navigation";

/**
 * The world moved to `/graph`.
 *
 * It lived here while it was being proven, and links to it exist. A redirect rather than a
 * deletion keeps them working, and carries any deep link across: `/graph/world?node=X` becomes
 * `/graph?node=X`, which selects the same subject in the same place.
 */
export default async function WorldRedirect({
    searchParams,
}: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
    const params = await searchParams;
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (typeof value === "string") query.set(key, value);
    }
    const suffix = query.toString();
    redirect(suffix ? `/graph?${suffix}` : "/graph");
}
