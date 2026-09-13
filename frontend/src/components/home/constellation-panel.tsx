"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

/**
 * The frame around the constellation: the carbon panel, the link out, and the text
 * alternative.
 *
 * The canvas is dynamically imported with `ssr: false`. It draws on a canvas and reads the
 * pointer, so there is nothing for it to do on the server, and keeping it out of the server
 * bundle means the homepage's first HTML contains the frame, the label and the link with no
 * script involved. Someone with JavaScript off gets a labelled panel and a working link to
 * the graph rather than an empty box.
 *
 * ## The one dark section on a light page
 *
 * Everything else here is manuscript ivory. This panel is carbon in both themes, which is a
 * deliberate exception to the rule that a page holds one theme. The justification is that it
 * is the one place showing the corpus as a spatial field rather than as text, and the shift
 * from paper to ground is the point being made: the same material, seen a second way. It
 * happens once. A second inverted section would make it a pattern rather than a moment.
 */

const Constellation = dynamic(
    () => import("./constellation").then((m) => m.Constellation),
    { ssr: false },
);

type Slice = {
    nodes: Array<{ id: string; type: string; label: string; deity: boolean; degree: number }>;
    edges: Array<{ s: string; t: string; p: string }>;
};

export function ConstellationPanel({ slice }: { slice: Slice | null }) {
    return (
        <div className="va-constellation-panel">
            {slice ? (
                <>
                    <Constellation slice={slice} />
                    {/*
                     * The real text alternative. The canvas is aria-hidden, so this list is
                     * what a screen reader receives, and it is the actual content rather than
                     * a description of a picture: the things shown, by name.
                     */}
                    <div className="sr-only">
                        <h2>The constellation, as a list</h2>
                        <p>
                            {slice.nodes.length} named things from the corpus, drawn as a field
                            with {slice.edges.length} of the relationships between them. Open the
                            graph to explore all of them.
                        </p>
                        <ul>
                            {slice.nodes.map((node) => (
                                <li key={node.id}>
                                    {node.label},{" "}
                                    {node.deity
                                        ? "deity"
                                        : node.type.toLowerCase().replace(/_/g, " ")}
                                </li>
                            ))}
                        </ul>
                    </div>
                </>
            ) : (
                <p className="va-constellation-absent">
                    The constellation could not be read for this build. The graph itself is
                    unaffected.
                </p>
            )}
            <Link className="va-constellation-link" href="/graph">
                Open the graph
            </Link>
        </div>
    );
}
