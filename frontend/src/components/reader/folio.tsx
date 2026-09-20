import clsx from "clsx";

/**
 * The folio: a block of the reading column and the margin beside it.
 *
 * The desktop reader had 368px of nothing between the verse and the apparatus rail, because
 * the reading column was a `1fr` track and the text inside it was capped at its own measure.
 * A critical edition does not waste that space; it rules it and writes in it.
 *
 * ## What the margin is allowed to say
 *
 * Only what is true at the level the margin is anchored to. This is the rule that decides
 * the whole design, and it is why the margin is a sibling of one block rather than a
 * free-floating column of notes positioned by offset: a note placed beside a verse is read
 * as a note *about that verse*, and a note placed beside a line is read as a note about that
 * line. This corpus records witnesses, provenance, translations and formula reach at the
 * verse level and nowhere finer. There is no line-level alignment in the data, so nothing in
 * this component can produce one: a `Folio` wraps exactly one block, its margin annotates
 * exactly that block, and the two share a grid row so the alignment is the browser's rather
 * than a guess.
 *
 * ## Three widths
 *
 * At 84rem and above the margin is a real column between the text and the apparatus rail,
 * and each note sits level with the top of the block it annotates.
 *
 * Between 62rem and 84rem there is no room for a third column - the text measure, the rail
 * and a margin do not fit - so the note folds beneath its block as a ruled strip. It is not
 * moved into the apparatus rail: the rail is a list of what the tradition ascribes to this
 * verse, and a note about which edition printed the text is not that. Separating a note from
 * the block it annotates to save a column would cost the one thing the margin is for.
 *
 * Below 62rem the same strip, stacked, with the rail beneath the article as it already was.
 */
export function Folio({
    children,
    notes,
    /** Names the margin for a screen reader: "Apparatus for the Sanskrit text". */
    label,
    /**
     * Draw the registration mark at the head of this folio's margin.
     *
     * One per page, on the block the page is about. A pothi leaf is held together by a cord
     * through the leaf, and the ring and the rule in the margin are that geometry borrowed
     * as registration - not a hole drawn through the text, which would be cosplay and would
     * make the text bend around a fiction.
     */
    registration = false,
}: {
    children: React.ReactNode;
    notes?: React.ReactNode;
    label?: string;
    registration?: boolean;
}) {
    if (!notes) return <div className="va-folio">{children}</div>;
    return (
        <div className="va-folio">
            <div className="va-folio-text">{children}</div>
            <aside
                aria-label={label}
                className={clsx("va-folio-margin", registration && "has-registration")}
            >
                {notes}
            </aside>
        </div>
    );
}

/**
 * One marginal note: a term and what it says.
 *
 * Set as a definition rather than a sentence, because that is what a manuscript margin
 * holds - a hand naming the source, the variant, the authority - and because a reader
 * scanning three notes needs the terms to line up.
 */
export function FolioNote({
    term,
    children,
    tone,
}: {
    term: string;
    children: React.ReactNode;
    /** `absent` sets the note in the unbuilt tone: this is a gap, not a fact. */
    tone?: "absent";
}) {
    return (
        <div className={clsx("va-folio-note", tone === "absent" && "is-absent")}>
            <p className="va-folio-term">{term}</p>
            <div className="va-folio-body">{children}</div>
        </div>
    );
}

/**
 * The shelfmark: this passage's canonical key, treated as an archival identifier.
 *
 * `VG:RV:SAK:M01:S032:V001` is a catalogue number. It is how the store addresses the verse,
 * how the API is called, and how a citation of this build stays resolvable when the human
 * citation form changes - which is exactly the job a shelfmark does in an archive. So it is
 * exposed, set in the mono face at the foot of the folio, and labelled as what it is.
 *
 * It is deliberately quiet and it never replaces the human citation. "RV 1.32.1" is the
 * heading of the page; this is the line at the bottom of the card in the drawer.
 */
export function Shelfmark({ canonicalKey, citation }: { canonicalKey: string; citation?: string }) {
    return (
        <div className="va-shelfmark">
            <span className="va-shelfmark-term">Shelfmark</span>
            <code className="va-shelfmark-key">{canonicalKey}</code>
            {citation ? <span className="va-shelfmark-cite">cited as {citation}</span> : null}
        </div>
    );
}
