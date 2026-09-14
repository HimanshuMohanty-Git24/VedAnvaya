export type NavItem = {
    href: string;
    label: string;
    description: string;
};

/**
 * The things a reader comes here to do, in the order they escalate: ask a question, read a
 * collection, take a curated route through it, follow what the collections share, and open
 * the graph.
 *
 * Six is the ceiling. The desktop bar has to stay on one line at 1024px beside the wordmark,
 * the search affordance and the theme control, and a seventh item is what pushes it to two.
 * The sixth slot was held empty for Visualize until that surface existed, because a
 * navigation item is a promise that something is there. It is now filled, and the bar is
 * full: a seventh item costs a second line, so the next surface goes in the overflow.
 */
export const PRIMARY_NAV: NavItem[] = [
    {
        href: "/ask",
        label: "Ask",
        description: "Put a question to the corpus and check its evidence",
    },
    { href: "/vedas", label: "Vedas", description: "Read each collection by its own hierarchy" },
    {
        href: "/explore",
        label: "Explore",
        description: "Routes through the corpus, chosen for a reason",
    },
    {
        href: "/connections",
        label: "Connections",
        description: "Wording and figures the collections share",
    },
    {
        href: "/graph",
        label: "Graph",
        description: "Follow a relationship and ask it to explain itself",
    },
    {
        href: "/visualizations",
        label: "Visualize",
        description: "Seven plates, each answering one question about the corpus",
    },
];

/**
 * Everything else, in the overflow.
 *
 * Limits comes first and that is deliberate. It is the page most easily buried and least
 * safely buried, so it also holds the first slot in the footer, a section of its own on the
 * homepage, and an inline route out of every caveat. What it does not get is a primary slot,
 * because nobody sets out to visit it: a reader arrives at it from a figure they have just
 * read and want to know the edge of.
 */
export const SECONDARY_NAV: NavItem[] = [
    { href: "/limits", label: "Limits", description: "What this corpus cannot answer, and why" },
    {
        href: "/insights",
        label: "Evidence",
        description: "Data, derived measures and interpretation, kept apart",
    },
    { href: "/devatas", label: "Deities", description: "Who is invoked, where, and on whose word" },
    {
        href: "/entities",
        label: "Entities",
        description: "People, places, substances, rites and ideas",
    },
    {
        href: "/sources",
        label: "Sources and method",
        description: "Where the material comes from, and how it is turned into evidence",
    },
    { href: "/about", label: "About", description: "Why VedAnvaya exists" },
];
