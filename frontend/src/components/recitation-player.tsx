"use client";

import {
    ArrowSquareOut,
    Pause,
    Play,
    SpeakerHigh,
    WarningCircle,
} from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import type { AudioTrack } from "@/lib/api";

/**
 * The reader's recitation control.
 *
 * **The label comes from the server, not from here.** `track.scope.scope_note` is composed
 * once in the API and rendered verbatim. The current source records one file per verse, so
 * it usually reads "Recitation of this verse" -- but a coarser source makes it "Recitation
 * of this hymn, which contains this passage", and composing that sentence in the client
 * would put a second place where it could come out as "Play this mantra".
 *
 * **A recording that will not load is not hidden.** The `failed` state replaces the
 * transport with a link to the source page, because the alternative -- a dead play
 * button -- reads as a defect in the corpus rather than a third party being unreachable.
 * Audio is the least load-bearing thing on this page and must never look like the most.
 *
 * Note the element is chosen from `playback.media_kind`: a source may serve video, and an
 * `<audio>` element pointed at an MP4 plays nothing on some browsers.
 *
 * **`preload="none"` is deliberate, and the seek bar is disabled until it pays off.** The
 * API's streaming route pulls the whole upstream file to answer any request, because the
 * source serves a verse as one base64 document rather than a seekable stream. Preloading
 * metadata would therefore fetch every verse's audio on every reader page view, for readers
 * who never press play. The cost is that duration is unknown until playback starts, so the
 * slider is inert until then -- disabled rather than present-but-lying about a position.
 *
 * **Callers must key this on `track.audio_id`.** Position, duration and failure are local
 * state belonging to one recording, and a new track must start clean. Remounting is how
 * that is done -- resetting the four values inside an effect would fire a second render
 * pass on every track change and is what `react-hooks/set-state-in-effect` exists to
 * prevent.
 */

const SPEEDS = [0.75, 1, 1.25, 1.5] as const;

/** What each scope covers, in a word a reader recognises. */
const SCOPE_WORDS: Record<string, string> = {
    MANTRA: "one verse",
    SUKTA: "a whole hymn",
    SECTION: "a whole section",
    ADHYAYA: "a whole adhyaya",
    KANDA: "a whole kanda",
    COLLECTION: "a whole collection",
    WORK: "the whole Samhita",
    UNKNOWN: "an unstated span",
};

function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
    const total = Math.floor(seconds);
    const minutes = Math.floor(total / 60);
    const rest = total % 60;
    return `${minutes}:${String(rest).padStart(2, "0")}`;
}

export function RecitationPlayer({ track }: { track: AudioTrack }) {
    const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);
    const [playing, setPlaying] = useState(false);
    const [current, setCurrent] = useState(0);
    const [duration, setDuration] = useState(track.duration_seconds ?? 0);
    const [speed, setSpeed] = useState<number>(1);
    const [failed, setFailed] = useState(false);
    const [loading, setLoading] = useState(false);
    const seekId = useId();

    const src = track.playback.stream_url ?? track.playback.media_url ?? null;
    const isVideo = track.playback.media_kind === "video";

    useEffect(() => {
        const media = mediaRef.current;
        if (media) media.playbackRate = speed;
    }, [speed]);

    async function toggle() {
        const media = mediaRef.current;
        if (!media) return;
        if (playing) {
            media.pause();
            return;
        }
        try {
            setLoading(true);
            await media.play();
        } catch {
            // Autoplay refusal and a network failure surface the same way here. Both mean
            // the reader cannot hear it from this page, so both offer the source instead.
            setFailed(true);
        } finally {
            setLoading(false);
        }
    }

    if (!src) {
        return (
            <section className="recitation is-external" aria-label="Recitation">
                <p className="recitation-scope">{track.scope.scope_note}</p>
                <SourceLink track={track} label="Open the recording at its source" />
                <Provenance track={track} />
            </section>
        );
    }

    return (
        <section className="recitation" aria-label="Recitation">
            <p className="recitation-scope" id={`${seekId}-scope`}>
                <SpeakerHigh size={16} weight="duotone" aria-hidden="true" />
                {track.scope.scope_note}
            </p>

            {failed ? (
                <div className="recitation-failed" role="status">
                    <WarningCircle size={17} weight="duotone" aria-hidden="true" />
                    <div>
                        <strong>This recitation did not load</strong>
                        <small>
                            The recording is streamed from {track.source.name}, which is
                            sometimes slow to answer. The text on this page is unaffected.
                        </small>
                    </div>
                    <SourceLink track={track} label="Play at the source" />
                </div>
            ) : (
                <div className="recitation-transport">
                    <button
                        type="button"
                        className="recitation-play"
                        onClick={toggle}
                        aria-label={
                            playing
                                ? `Pause ${track.title}`
                                : `Play ${track.title}`
                        }
                        aria-describedby={`${seekId}-scope`}
                    >
                        {playing ? (
                            <Pause size={18} weight="fill" aria-hidden="true" />
                        ) : (
                            <Play size={18} weight="fill" aria-hidden="true" />
                        )}
                    </button>

                    <input
                        id={seekId}
                        className="recitation-seek"
                        type="range"
                        min={0}
                        max={duration || 0}
                        step={0.5}
                        value={current}
                        disabled={!duration}
                        aria-label="Seek within this recitation"
                        aria-valuetext={`${formatTime(current)} of ${formatTime(duration)}`}
                        onChange={(event) => {
                            const media = mediaRef.current;
                            const next = Number(event.target.value);
                            setCurrent(next);
                            if (media) media.currentTime = next;
                        }}
                    />

                    <span className="recitation-time" aria-hidden="true">
                        {formatTime(current)}
                        {duration ? ` / ${formatTime(duration)}` : ""}
                    </span>

                    <label className="recitation-speed">
                        <span className="sr-only">Playback speed</span>
                        <select
                            value={speed}
                            onChange={(event) => setSpeed(Number(event.target.value))}
                        >
                            {SPEEDS.map((rate) => (
                                <option key={rate} value={rate}>
                                    {rate}&times;
                                </option>
                            ))}
                        </select>
                    </label>

                    {loading && <span className="recitation-loading">Loading…</span>}
                </div>
            )}

            {isVideo ? (
                <video
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    src={src}
                    // The portal serves these as MP4 with a static frame. Kept off-screen
                    // rather than rendered: the reader wants the recitation, and a video
                    // panel would displace the Sanskrit, which stays primary.
                    className="recitation-media"
                    preload="none"
                    playsInline
                    onPlay={() => setPlaying(true)}
                    onPause={() => setPlaying(false)}
                    onEnded={() => setPlaying(false)}
                    onError={() => setFailed(true)}
                    onLoadedMetadata={(event) => setDuration(event.currentTarget.duration || 0)}
                    onTimeUpdate={(event) => setCurrent(event.currentTarget.currentTime)}
                />
            ) : (
                <audio
                    ref={mediaRef as React.RefObject<HTMLAudioElement>}
                    src={src}
                    preload="none"
                    onPlay={() => setPlaying(true)}
                    onPause={() => setPlaying(false)}
                    onEnded={() => setPlaying(false)}
                    onError={() => setFailed(true)}
                    onLoadedMetadata={(event) => setDuration(event.currentTarget.duration || 0)}
                    onTimeUpdate={(event) => setCurrent(event.currentTarget.currentTime)}
                />
            )}

            <Provenance track={track} />
        </section>
    );
}

function SourceLink({ track, label }: { track: AudioTrack; label: string }) {
    return (
        <a
            className="recitation-source-link"
            href={track.source.page}
            // Several sources' terms forbid their pages being loaded into a frame, so this
            // always opens a new window. noreferrer travels with _blank for the usual
            // reason: the opened page gets no handle back on this one.
            target="_blank"
            rel="noreferrer"
        >
            {label}
            <ArrowSquareOut size={14} aria-hidden="true" />
        </a>
    );
}

/**
 * Secondary by construction. The Sanskrit is the primary object on this page, so the
 * recording's provenance collapses -- but it is present, because a reader who cannot see
 * where a recitation came from cannot judge it.
 */
function Provenance({ track }: { track: AudioTrack }) {
    return (
        <details className="recitation-provenance">
            <summary>About this recording</summary>
            <dl>
                <dt>Source</dt>
                <dd>{track.source.name}</dd>

                <dt>Recording covers</dt>
                <dd>
                    {SCOPE_WORDS[track.scope.scope_type] ??
                        track.scope.scope_type.toLowerCase()}
                    {track.scope.scope_citation ? ` — ${track.scope.scope_citation}` : ""}
                </dd>

                <dt>Matched to this passage</dt>
                <dd>
                    {track.text_verified
                        ? "Confirmed — the text the source says this recording recites matches this corpus's text for this passage."
                        : "By the source's own numbering. The recited text was not compared."}
                </dd>

                <dt>Recitation tradition</dt>
                <dd>{track.tradition ?? "Not stated by the source"}</dd>

                <dt>Reciter</dt>
                <dd>{track.performer ?? "Not stated by the source"}</dd>

                <dt>How it was matched</dt>
                <dd>{track.mapping_method}</dd>

                {track.source.attribution ? (
                    <>
                        <dt>Attribution</dt>
                        <dd>{track.source.attribution}</dd>
                    </>
                ) : null}

                {track.source.licence ? (
                    <>
                        <dt>Licence</dt>
                        <dd>{track.source.licence}</dd>
                    </>
                ) : null}
            </dl>
            {track.notes ? <p className="recitation-note">{track.notes}</p> : null}
            <SourceLink track={track} label="Open the original source" />
        </details>
    );
}
