/**
 * How far something reaches across the four collections.
 *
 * Four marks in corpus order, and the point of the component is that they carry four
 * different claims rather than two. The obvious design - filled for present, hollow for
 * everything else - is the mistake this product exists to avoid: it merges "measured, and
 * the wording does not occur there" with "that collection was never read for this", and a
 * reader cannot tell a fact from a gap.
 *
 * So `measured` is required. It is the list of collections the producing query actually
 * read, and it comes from the service - `vedas_reported` on an insight, `vedas_in_scope` on
 * a coverage block - never from a guess here. A collection outside it is drawn as never
 * measured and says so.
 *
 * Shape as well as tone, because a mark distinguished only by colour is not distinguished
 * at all in greyscale or for a reader who cannot see the difference. Every mark also
 * carries its claim as text, in a `title` for the pointer and a visually hidden span for a
 * screen reader, so the register is never the only place the information exists.
 */

const ORDER = ["RV", "SV", "YV", "AV"] as const;

const VEDA_NAMES: Record<string, string> = {
    RV: "Rigveda",
    SV: "Samaveda",
    YV: "Yajurveda",
    AV: "Atharvaveda",
};

type ReachState = "HELD" | "NONE_FOUND" | "NOT_MEASURED" | "NOT_APPLICABLE";

/** The words for each state, written once so no caller can phrase an absence differently. */
function claimFor(veda: string, state: ReachState, count?: number | null): string {
    const name = VEDA_NAMES[veda] ?? veda;
    switch (state) {
        case "HELD":
            return count == null
                ? `Occurs in the ${name}`
                : `Occurs in the ${name}: ${count.toLocaleString("en-GB")} ${count === 1 ? "occurrence" : "occurrences"}`;
        case "NONE_FOUND":
            return `Read, and not found in the ${name}`;
        case "NOT_MEASURED":
            return `The ${name} was not read for this`;
        case "NOT_APPLICABLE":
            return `This relation cannot hold in the ${name}`;
    }
}

export function Reach({
    /** Collections the thing was found in. */
    present,
    /**
     * Collections the producing query read.
     *
     * Required. A caller that does not know which collections were read cannot draw this
     * register honestly, and passing all four to make the types pass is the failure mode
     * this parameter exists to make visible.
     */
    measured,
    /** Per-collection counts, where the payload carries them. */
    counts,
    /** Collections where the relation cannot hold at all: a within-corpus class, say. */
    notApplicable,
    label = "Reach across the four collections",
}: {
    present: readonly string[];
    measured: readonly string[];
    counts?: Record<string, number> | null;
    notApplicable?: readonly string[];
    label?: string;
}) {
    const found = new Set(present.filter(Boolean));
    const read = new Set(measured.filter(Boolean));
    const impossible = new Set(notApplicable ?? []);

    return (
        <span aria-label={label} className="va-reach" role="group">
            {ORDER.map((veda) => {
                const state: ReachState = impossible.has(veda)
                    ? "NOT_APPLICABLE"
                    : !read.has(veda)
                      ? "NOT_MEASURED"
                      : found.has(veda)
                        ? "HELD"
                        : "NONE_FOUND";
                const claim = claimFor(veda, state, counts?.[veda]);
                return (
                    <span className="va-reach-cell" data-state={state} key={veda} title={claim}>
                        <span aria-hidden="true" className="va-reach-mark" />
                        <span aria-hidden="true" className="va-reach-veda">
                            {veda}
                        </span>
                        <span className="sr-only">{claim}</span>
                    </span>
                );
            })}
        </span>
    );
}
