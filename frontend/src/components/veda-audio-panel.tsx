import { SpeakerHigh } from "@phosphor-icons/react/dist/ssr";
import type { WorkAudio } from "@/lib/api";

/**
 * What recitation coverage exists for one Samhita.
 *
 * **Every number here is counted from the catalog on the request that rendered it.** The
 * release spec forbids a hard-coded coverage figure, and for good reason: a written-down
 * "10,402 recitations" survives the withdrawal of a recording and becomes a claim the
 * product cannot support.
 *
 * **The unit is stated next to the number, not left implied.** `mapped_scope_count` counts
 * whatever span the source recorded. For this catalog that is verses, because the source
 * publishes one file per verse -- but the component reads the unit out of
 * `scope_type_counts` rather than assuming it, so a future source that records whole
 * hymns changes the sentence instead of quietly making it false.
 *
 * **`playable` and `mapped` are both shown when they differ.** A verse whose recording the
 * source has withdrawn offers no player, so counting it as coverage would promise
 * something the reader cannot hear.
 *
 * A Veda with nothing mapped renders the API's explanation of the absence, or nothing at
 * all if there is none. What it never renders is a bare "0 recitations", which invites the
 * inference that no recitation of that Veda exists anywhere.
 */

const SPAN_WORDS: Record<string, { one: string; many: string }> = {
    MANTRA: { one: "verse", many: "verses" },
    SUKTA: { one: "hymn", many: "hymns" },
    SECTION: { one: "section", many: "sections" },
    ADHYAYA: { one: "adhyaya", many: "adhyayas" },
    KANDA: { one: "kanda", many: "kandas" },
    COLLECTION: { one: "collection", many: "collections" },
    WORK: { one: "collection-level reference", many: "collection-level references" },
};

function word(scope: string, count: number): string {
    const entry = SPAN_WORDS[scope] ?? {
        one: scope.toLowerCase(),
        many: scope.toLowerCase(),
    };
    return count === 1 ? entry.one : entry.many;
}

export function VedaAudioPanel({
    audio,
    verseTotal,
}: {
    audio: WorkAudio;
    verseTotal?: number | null;
}) {
    const scopeCounts = audio.scope_type_counts ?? {};
    const present = Object.entries(scopeCounts).filter(([, n]) => n > 0);
    const caveats = audio.caveats ?? [];

    // A Veda with no audio still gets a panel when the API explains the absence. Silence
    // would be the worse choice here: a reader who has seen the other three collections
    // offer recitations reads a missing panel as an oversight, and the Samavedic absence in
    // particular is a fact about what has been published rather than about this product.
    if (present.length === 0) {
        return (
            <div className="panel">
                <h3>
                    <SpeakerHigh size={17} weight="duotone" aria-hidden="true" /> Recitation audio
                </h3>
                {/*
                  * The reason, and it is no longer the one this panel used to give.
                  *
                  * It read "none is published until it has been [listened to]", which was the
                  * rule until OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION replaced audible
                  * review with a per-recording badge and admitted 946 source-mapped
                  * recordings. The sentence survived the decision that falsified it, which is
                  * how a policy statement in prose usually fails.
                  *
                  * For the Samaveda the absence has a different cause and always did: no
                  * recitation of it is catalogued from any source. Saying so is the honest
                  * answer, and it is a statement about what has been published rather than
                  * about the tradition, which sings this collection above all others.
                  */}
                <p className="panel-note">
                    <strong>No recitation is catalogued for this collection.</strong> None has
                    been found in a form that could be mapped to these verses and played here.
                </p>
                {caveats.slice(0, 1).map((caveat) => (
                    <p className="panel-note panel-note-faint" key={caveat.text}>
                        {caveat.text}
                    </p>
                ))}
            </div>
        );
    }

    const mapped = audio.mapped_scope_count ?? 0;
    const playable = audio.playable_scope_count ?? mapped;
    const withdrawn = mapped - playable;
    /*
     * The publishers of the whole collection, from the response's own census.
     *
     * This read `audio.tracks` and deduplicated the names on it, which is a sample: `tracks`
     * is one page of recordings, and the page the Rigveda happened to return was Cologne's
     * 150 out of 10,552. The panel therefore told a reader that the Rigveda's recitation
     * comes from the National Library of Denmark. `source_counts` is counted over the Veda,
     * so the leading publisher is the leading publisher.
     */
    const sourceCounts = Object.entries(audio.source_counts ?? {}).sort((a, b) => b[1] - a[1]);
    const sources = sourceCounts.map(([name]) => name);

    // Whether every recording in this collection is of one verse. That decides the
    // sentence: a per-verse catalog plays the verse, anything coarser plays a span
    // containing it, and saying the wrong one is exactly the "too long" complaint.
    const perVerse = present.length === 1 && present[0][0] === "MANTRA";
    // The corpus total, where the caller knows it. Without a denominator "10,402 verses"
    // reads as the whole collection; with one it reads as the share it is.
    const denominator = perVerse && verseTotal && verseTotal > playable ? verseTotal : null;
    /*
     * And when it *is* the whole collection, say so.
     *
     * The denominator is suppressed at full coverage because "10,552 of 10,552" is a clumsy
     * way to say "all of them" - but dropping it silently leaves "10,552 verses carry their
     * own recitation" looking like the same kind of partial figure it was last week, when
     * the Rigveda stood at 10,402. Completeness is the more informative claim of the two and
     * it is now true of one collection, so it is stated rather than implied.
     */
    const complete = Boolean(perVerse && verseTotal && verseTotal === playable);
    const unitPhrase = present
        .map(([scope, n]) => `${n.toLocaleString()} ${word(scope, n)}`)
        .join(", ");

    return (
        <div className="panel">
            <h3>
                <SpeakerHigh size={17} weight="duotone" aria-hidden="true" /> Recitation audio
            </h3>
            {mapped > 0 ? (
                <p className="panel-note">
                    <strong>
                        {denominator
                            ? `${playable.toLocaleString()} of ${denominator.toLocaleString()}`
                            : withdrawn > 0
                              ? `${playable.toLocaleString()} of ${unitPhrase}`
                              : complete
                                ? `All ${unitPhrase}`
                                : unitPhrase}
                    </strong>
                    {perVerse ? (
                        <>
                            {denominator
                                ? " verses carry their own recitation, one recording per verse."
                                : " of this collection carry their own recitation, one recording per verse."}
                        </>
                    ) : (
                        <>
                            of this collection carry a recitation, offered at the level each was
                            recorded &mdash; so a verse plays the span containing it, from the
                            start.
                        </>
                    )}
                </p>
            ) : (
                <p className="panel-note">
                    <strong>{unitPhrase}</strong> for this collection. No recording is tied to
                    an individual verse.
                </p>
            )}

            {withdrawn > 0 && (
                <p className="panel-note panel-note-faint">
                    {withdrawn.toLocaleString()} mapped{" "}
                    {withdrawn === 1 ? "recording is" : "recordings are"} no longer served by
                    the source, so {withdrawn === 1 ? "it offers" : "they offer"} no player.
                </p>
            )}

            {sources.length > 0 && (
                <p className="panel-note panel-note-faint">
                    {sources.length === 1 ? "Source" : "Sources"}:{" "}
                    {sourceCounts
                        .map(([name, count]) =>
                            sources.length === 1
                                ? name
                                : `${name} (${count.toLocaleString()})`,
                        )
                        .join(", ")}
                    . Each recording&rsquo;s full provenance, and
                    how it was matched to its verse, is on the reader page.
                </p>
            )}

            {(audio.caveats ?? []).slice(0, 1).map((caveat) => (
                <p className="panel-note panel-note-faint" key={caveat.text}>
                    {caveat.text}
                </p>
            ))}
        </div>
    );
}
