export type NavItem = {
    href: string;
    label: string;
    description: string;
};

export const PRIMARY_NAV: NavItem[] = [
    { href: "/ask", label: "Ask", description: "Put a research question to the graph" },
    { href: "/vedas", label: "Vedas", description: "Browse each collection by its own hierarchy" },
    { href: "/explore", label: "Explore", description: "Curated lenses on the corpus" },
    { href: "/devatas", label: "Deities", description: "Who is invoked, and where" },
    { href: "/entities", label: "Entities", description: "People, ideas and things" },
    { href: "/connections", label: "Connections", description: "What the collections share" },
    { href: "/graph", label: "Graph", description: "The interactive knowledge graph" },
];

export const SECONDARY_NAV: NavItem[] = [
    { href: "/insights", label: "Evidence", description: "Data, derived measures, interpretation" },
    { href: "/limits", label: "Limits", description: "What this atlas cannot answer" },
];
