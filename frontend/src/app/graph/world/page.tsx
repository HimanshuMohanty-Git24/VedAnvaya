import type { Metadata } from "next";
import { WorldStage } from "@/components/world/world-stage";

export const metadata: Metadata = {
    title: "The world",
    description:
        "The whole public knowledge graph as one spatial map: 35,370 subjects and 185,693 recorded relationships, with every connection openable.",
};

/**
 * The World View, behind its own route while it is being proven.
 *
 * The 2D explorer at `/graph` stays exactly as it is. It is the working graph today, it is
 * what the rest of the product links to, and replacing it before this one has a search, an
 * accessible parallel and a mobile answer would be trading something that works for something
 * that is nearly finished.
 */
export default function WorldPage({
    searchParams,
}: {
    searchParams: Promise<{ node?: string }>;
}) {
    return <WorldStage searchParams={searchParams} />;
}
