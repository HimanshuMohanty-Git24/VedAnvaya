"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import type { HeroSlice } from "./world-preview";

/**
 * The frame around the world preview: the panel, the way in, and the text alternative.
 *
 * The canvas is dynamically imported with `ssr: false`, which does two jobs. It keeps a renderer
 * that reads the pointer and holds a GL context out of the server bundle, and - measured - it
 * keeps three.js out of the homepage's first-load JavaScript entirely, so the front door does not
 * pay for the graph engine before anyone has asked for a graph. The first HTML contains this
 * frame, the list of subjects and a working link, so JavaScript off still yields a labelled panel
 * and a route into the corpus.
 *
 * ## The one dark section on a light page
 *
 * Everything else here is manuscript ivory. This panel is carbon in both themes, a deliberate
 * exception to the rule that a page holds one theme. It is the one place showing the corpus as a
 * spatial field rather than as text, and the shift from paper to ground is the point being made:
 * the same material, seen a second way. It happens once. A second inverted section would make it
 * a pattern rather than a moment.
 */

const WorldPreview = dynamic(() => import("./world-preview").then((m) => m.WorldPreview), {
    ssr: false,
});

export function WorldPreviewPanel({ slice }: { slice: HeroSlice | null }) {
    /*
     * `dark` is load-bearing, not decorative. It makes every token inside this panel resolve to
     * its carbon value, which is how the preview reads colours belonging to the surface it is
     * drawn on rather than to the page around it.
     */
    return (
        <div className="va-world-preview-panel dark">
            {slice ? (
                <>
                    <WorldPreview slice={slice} />
                    {/*
                     * The real text alternative. The canvas is aria-hidden, so this is what a
                     * screen reader receives, and it is the actual content rather than a
                     * description of a picture: the subjects shown, by name, each one a link to
                     * the same place clicking it in the canvas would go.
                     */}
                    <div className="sr-only">
                        <h2>The world preview, as a list</h2>
                        <p>
                            {slice.nodes.length} subjects from the corpus, drawn as a spatial field
                            with {slice.edges.length} of the relationships between them. This is a
                            small part of a graph of 35,370 subjects.
                        </p>
                        <ul>
                            {slice.nodes.map((node) => (
                                <li key={node.id}>
                                    <Link
                                        href={`/graph?view=focus&renderer=3d&node=${encodeURIComponent(node.id)}`}
                                        prefetch={false}
                                    >
                                        {node.label}
                                    </Link>
                                    , {node.group.replace(/-/g, " ")},{" "}
                                    {node.degree.toLocaleString()} connections
                                </li>
                            ))}
                        </ul>
                    </div>
                </>
            ) : (
                <p className="va-world-preview-absent">
                    The world preview could not be read for this build. The graph itself is
                    unaffected.
                </p>
            )}
            <Link className="va-world-preview-link" href="/graph" prefetch={false}>
                Open the graph
            </Link>
        </div>
    );
}
