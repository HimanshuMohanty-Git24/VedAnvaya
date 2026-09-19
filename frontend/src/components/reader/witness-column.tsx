"use client";

import { X } from "@phosphor-icons/react";
import { useId, useState } from "react";
import { CopyButton } from "../copy-button";

/**
 * The verse, and a second witness beside it.
 *
 * ## What this replaces
 *
 * A collapsed `<details>` holding every other witness stacked under the primary text. It
 * worked and it answered the wrong question: the reason to look at a second witness is to
 * see where it differs, and two texts eight hundred pixels apart vertically cannot be
 * compared by eye at all. A reader had to remember the first while scrolling to the second.
 *
 * ## What it does not do
 *
 * **It does not diff them.** No character is highlighted, no word is marked as changed, and
 * no normalisation is applied to either side. The reason is the corpus rather than effort:
 * the accents are combining marks, a naive diff over code points reports every accented
 * syllable as a difference, and a diff over *normalised* text would have to decide that an
 * accent is noise - which is the opposite of true here, where the accentuation is the
 * edition's most careful work. Both texts are printed exactly as their witness prints them
 * and the reader does the comparing, which is what a collation is.
 *
 * **It does not correct the witness.** A surface that reads differently reads differently.
 *
 * ## One control, one region, two layouts
 *
 * The button and the witness region exist once in the DOM. At 84rem and above the region is
 * a column beside the primary text and the two are collated; below that the same region
 * stacks under it, which is the disclosure the small screen wants. Rendering two trees and
 * hiding one with CSS would put the witness text in the accessibility tree twice, and
 * switching trees on a media query would be a hydration mismatch.
 *
 * The primary stays primary in both: it keeps the verse size and the full ink, and the
 * witness is set one step down in the secondary tone. Size and colour, not position - at
 * a narrow width position is all there is, and the reader still has to know which is which.
 */

export type WitnessSurface = {
    key: string;
    text: string;
    script: "IAST" | "DEVANAGARI";
    /** The edition, named. "Witness not identified" where the store does not say. */
    name: string;
    /** Source and licence, where they differ from the primary's. */
    provenance?: string | null;
    accented?: boolean | null;
};

export function WitnessColumn({
    primary,
    alternates,
}: {
    primary: WitnessSurface;
    alternates: WitnessSurface[];
}) {
    const regionId = useId();
    /*
     * Which witness is open, by key. Null is closed.
     *
     * A key rather than a boolean, because a verse can carry more than one alternate and the
     * control has to say which one is being collated. Opening a second closes the first: two
     * witnesses beside one primary is three columns in a 912px field and neither reads.
     */
    const [open, setOpen] = useState<string | null>(null);
    const shown = alternates.find((surface) => surface.key === open) ?? null;

    return (
        <div className="va-collation" data-compare={shown ? "true" : "false"}>
            <div className="va-collation-primary">
                <div className="va-verse-meta">
                    <CopyButton text={primary.text} />
                </div>
                <p
                    className={
                        primary.script === "DEVANAGARI" ? "sanskrit devanagari" : "sanskrit"
                    }
                    data-script={primary.script}
                    lang="sa"
                >
                    {primary.text}
                </p>
            </div>

            {shown ? (
                <aside
                    aria-label={`Witness: ${shown.name}`}
                    className="va-collation-witness"
                    id={regionId}
                >
                    <div className="va-collation-witness-head">
                        <div>
                            <p className="va-collation-witness-name">{shown.name}</p>
                            <p className="va-collation-witness-kind">
                                {shown.script === "DEVANAGARI" ? "Devanagari" : "Romanised"}
                                {shown.accented ? ", accented" : ", without accents"}
                            </p>
                        </div>
                        <button
                            aria-controls={regionId}
                            aria-expanded="true"
                            className="va-collation-close"
                            onClick={() => setOpen(null)}
                            type="button"
                        >
                            <X aria-hidden="true" size={14} />
                            <span className="sr-only">Close the {shown.name} column</span>
                        </button>
                    </div>
                    <p
                        className={
                            shown.script === "DEVANAGARI" ? "sanskrit devanagari" : "sanskrit"
                        }
                        data-script={shown.script}
                        lang="sa"
                    >
                        {shown.text}
                    </p>
                    {shown.provenance ? (
                        <p className="va-collation-witness-provenance">{shown.provenance}</p>
                    ) : null}
                    <p className="va-collation-note">
                        Printed as this witness prints it. Nothing is normalised and no
                        difference is marked.
                    </p>
                </aside>
            ) : null}

            <div className="va-collation-controls">
                {alternates.map((surface) => (
                    <button
                        aria-controls={regionId}
                        aria-expanded={open === surface.key}
                        className="va-collation-open"
                        key={surface.key}
                        onClick={() => setOpen(open === surface.key ? null : surface.key)}
                        type="button"
                    >
                        {open === surface.key
                            ? `Close ${surface.name}`
                            : `Read ${surface.name} beside this`}
                    </button>
                ))}
            </div>
        </div>
    );
}
