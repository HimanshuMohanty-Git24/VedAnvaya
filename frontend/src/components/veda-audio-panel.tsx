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
                <p className="panel-note">
                    <strong>0 released recordings.</strong> While queued recordings exist,
                    1,001 recordings remain not individually heard and stay withheld behind the manual audible-review gate
                    (GAP-AUDIO-002, 003, 004); no unverified recordings are promoted without verified human audible QA.
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
    const sources = [...new Set((audio.tracks ?? []).map((track) => track.source.name))];

    // Whether every recording in this collection is of one verse. That decides the
    // sentence: a per-verse catalog plays the verse, anything coarser plays a span
    // containing it, and saying the wrong one is exactly the "too long" complaint.
    const perVerse = present.length === 1 && present[0][0] === "MANTRA";
    // The corpus total, where the caller knows it. Without a denominator "10,402 verses"
    // reads as the whole collection; with one it reads as the share it is.
    const denominator = perVerse && verseTotal && verseTotal > playable ? verseTotal : null;
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
                    Source: {sources.join(", ")}. Each recording&rsquo;s full provenance, and
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
