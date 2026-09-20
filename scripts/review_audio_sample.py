#!/usr/bin/env python3
"""A 100-row audible spot-check the owner can actually finish, and nothing more.

The full queue is 1,021 rows and 0 of them have been heard. Asking for all 1,021 has not
produced a single verdict in three passes, so this tool asks for the **seeded stratified
sample of 100** that Wave 4 already drew, and is explicit that a sample is what it is.

WHAT THIS TOOL MAY AND MAY NOT CONCLUDE
=======================================

If the owner reviews all 100 and accepts *n*::

    AUDIBLY_VERIFIED_SAMPLE = n

and the other 921 rows remain ``NOT_INDIVIDUALLY_HEARD``. There is no arithmetic anywhere
in this file that turns *n* into 1,021, because there is no arithmetic that could. A
completed sample may support an owner sample-acceptance decision later; it is never a
claim that 1,021 recordings were heard. The summary this writes states the residual
population in those words so a later reader cannot mistake one for the other.

WHY IT REUSES THE WAVE 4 SAMPLE INSTEAD OF DRAWING ITS OWN
==========================================================

``data/staging/wave4/audio_owner_sample_manifest.json`` is seeded
(``vedanvaya-wave4-audio-sample``), stratified proportionally to the queue with a floor of
one, and drawn from a citation-sorted list, so it reproduces exactly. Drawing a fresh
sample because a sampler is easy to write would discard that and invite the sample to be
redrawn until it looked good. It is validated on every start instead: every row must still
exist in the live queue with the same canonical key and the same recording, and the
manifest's sha256 is written into every decision.

THE RECORDING IS PART OF THE IDENTITY
=====================================

``review_id`` is **not** unique in this queue. ``REV-SV_CONTAINER_SCOPE-VG:SV:KAU:UTTARA:P01:R01``
covers four distinct Commons recordings, because a container-scope mapping asserts only
that a file belongs to the arcika container. Decisions are therefore keyed on
``review_id`` *and* ``media_url``, and each one records both.

THE SOURCE URL IS NOT A MEDIA FILE
==================================

Most of this queue points at ``vedsearch.org/api/v1/attachment/audio/...``, which answers
with a JSON document carrying the MP3 as base64 in ``data.attachment_content_base64`` --
not with audio. Handing that URL to a browser shows the reviewer a page of JSON and plays
nothing, which is how the first reviewed row was presented. ``R`` therefore resolves a
*recording* rather than opening a URL: it fetches, dispatches on what came back, decodes
the attachment where there is one, writes the bytes to ``.tmp/audio_review/`` under the
extension the content type implies, and opens that file in the system audio player. A
second ``R`` replays the saved file instead of fetching it again.

Dispatch is on the response rather than the hostname, because this queue spans four
sources and only one of them wraps its audio. An ``audio/*`` response is saved as it
arrived, a JSON one is decoded, a row naming a local file is played where it lies, and
anything else -- an ordinary web page -- is the single case that still falls back to the
browser. That fallback does **not** open the verdict gate.

WHAT COUNTS AS HAVING HEARD IT, AND THE LIMIT OF THIS TOOL
==========================================================

``AUDIBLY_VERIFIED`` and ``AUDIBLY_REJECTED`` are refused unless audio was decoded and
handed to a player in this session -- pressing Y without ever pressing play is not a
verdict, and neither is a browser window that opened on something unplayable. That is a
weaker gate than the browser harness's, which reads seconds actually consumed from the
audio element's own ``timeupdate`` events; a terminal cannot see inside the system player.
The difference is recorded in every row rather than glossed: ``listened_seconds`` is
``null`` here and the evidence field says so. For the stronger gate, use
``scripts/audio_review_harness.py``.

``AUDIBLE_REVIEW_UNCERTAIN`` is allowed with no audio, because that is the honest answer
when a recording will not play, and a queue that makes uncertainty inconvenient collects
false certainty.

Nothing in this file writes a verdict the reviewer did not type. There is no default, no
prefill and no bulk mode.

CORRECTING A MISTYPED VERDICT
=============================

``--correct`` appends a superseding decision rather than editing the log: the corrected
verdict becomes effective because :func:`decisions_by_row` keeps the last line per row
key, and the original line stays exactly where it was. The new line records both verdicts,
the reason, who corrected it and when, and the line number it supersedes.

It is for an *input* error only -- ``--reason`` is a closed vocabulary, and the sole member
is ``OWNER_CORRECTION_ACCIDENTAL_KEYPRESS``. A reviewer who listened again and changed
their mind uses ``--redo``, because that verdict rests on a second hearing and has to
record it. A correction records no hearing at all: ``new_playback_performed`` is False, the
superseded row's playback evidence is carried forward unchanged, and correcting *to*
``AUDIBLY_VERIFIED`` or ``AUDIBLY_REJECTED`` is refused outright unless that row already
recorded a recording that played.

Usage::

    python scripts/review_audio_sample.py                  # start or resume
    python scripts/review_audio_sample.py --progress       # counts, decide nothing
    python scripts/review_audio_sample.py --rejected       # inspect rejected rows
    python scripts/review_audio_sample.py --typed          # line input, no raw keys
    python scripts/review_audio_sample.py --reviewer NAME  # skip the name prompt
    python scripts/review_audio_sample.py --correct REVIEW_ID --to VERDICT \\
        --reason OWNER_CORRECTION_ACCIDENTAL_KEYPRESS --reviewer NAME
"""

from __future__ import annotations

import argparse
import base64
import collections
import dataclasses
import datetime
import hashlib
import json
import mimetypes
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Final

# Every row prints its canonical Sanskrit, which is IAST: accented sibilants, retroflexes
# with dots below. On a Windows stdout that is not already UTF-8 -- a pipe, a redirect, an
# older console -- the first such character raises UnicodeEncodeError and takes the session
# down mid-row, after the recording has been played but before a verdict can be typed. The
# five tools under scripts/audio/ all open with this; this one did not, and row 1 of the
# sample is an Atharvavedic verse whose text carries U+015B.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
SAMPLE: Final = ROOT / "data" / "staging" / "wave4" / "audio_owner_sample_manifest.json"
QUEUE: Final = ROOT / "data" / "staging" / "audio_review_queue.jsonl"
OUT_DIR: Final = ROOT / "data" / "manual" / "audio_review"
DECISIONS: Final = OUT_DIR / "sample_decisions.jsonl"
SUMMARY: Final = OUT_DIR / "sample_summary.json"

#: Where a fetched recording is kept so that R can replay it without asking the source
#: again. Under the gitignored ``.tmp/``: these are third-party media files, reproducible
#: from the queue's own URLs, and none of them belongs in the history.
CACHE_DIR: Final = ROOT / ".tmp" / "audio_review"

#: Bounds on one review fetch. The measured median verse is about 40 KB.
MAX_AUDIO_BYTES: Final = 20 * 1024 * 1024
FETCH_TIMEOUT: Final = 30.0

#: Content type to extension. Explicit, and consulted before ``mimetypes``; see
#: :func:`extension_for` for why.
AUDIO_EXTENSIONS: Final[dict[str, str]] = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/vorbis": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "audio/vnd.wave": ".wav",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/webm": ".webm",
}

#: A Wikimedia file *page*: HTML wrapped around a player. See :func:`fetchable_url`.
_WIKIMEDIA_FILE_PAGE: Final = re.compile(
    r"^(https?://[^/]*wikimedia\.org)/wiki/File:(.+)$", re.IGNORECASE
)

# The audio tools share one HTTP identity so that an operator reading vedsearch.org's
# access log sees a single recognisable agent rather than a fourth anonymous one. The
# package lives under src/ and this script is run directly, hence the path insert.
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.product.audio.net import USER_AGENT  # noqa: E402

#: The same three the harness allows. A fourth would be a way to avoid deciding.
VERDICTS: Final[tuple[str, ...]] = (
    "AUDIBLY_VERIFIED",
    "AUDIBLY_REJECTED",
    "AUDIBLE_REVIEW_UNCERTAIN",
)

#: Verdicts asserting the reviewer heard the recording. Refused if it was never opened.
REQUIRES_AUDIO: Final[frozenset[str]] = frozenset({"AUDIBLY_VERIFIED", "AUDIBLY_REJECTED"})

#: Why a recorded verdict may be superseded without listening again. Not free text: a
#: correction that accepts any reason at all is not a gate, and the one thing that must
#: never be correctable this way is a judgement. These name an *input* error -- the wrong
#: key reached the terminal -- and nothing else. A reviewer who listened again and changed
#: their mind goes through ``--redo``, which plays the recording and records the new
#: playback, because that correction really does rest on a second hearing and must show it.
CORRECTION_REASONS: Final[frozenset[str]] = frozenset({
    "OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
})

#: Keystroke and typed word to verdict. Typed commands exist because raw-key capture on
#: Windows terminals is unreliable often enough to be worth not depending on.
KEYS: Final[dict[str, str]] = {
    "y": "AUDIBLY_VERIFIED",
    "n": "AUDIBLY_REJECTED",
    "u": "AUDIBLE_REVIEW_UNCERTAIN",
}
WORDS: Final[dict[str, str]] = {
    "y": "AUDIBLY_VERIFIED",
    "yes": "AUDIBLY_VERIFIED",
    "accept": "AUDIBLY_VERIFIED",
    "n": "AUDIBLY_REJECTED",
    "no": "AUDIBLY_REJECTED",
    "reject": "AUDIBLY_REJECTED",
    "u": "AUDIBLE_REVIEW_UNCERTAIN",
    "uncertain": "AUDIBLE_REVIEW_UNCERTAIN",
    "unsure": "AUDIBLE_REVIEW_UNCERTAIN",
}

_VEDA_OF: Final[dict[str, str]] = {
    "RV": "Rigveda",
    "SV": "Samaveda",
    "YV": "Yajurveda",
    "AV": "Atharvaveda",
}


def row_key(row: dict[str, Any]) -> str:
    """``review_id`` plus the recording. See the module docstring: the id is not unique."""
    return f"{row.get('review_id') or ''}|{row.get('media_url') or ''}"


def veda_of(row: dict[str, Any]) -> str:
    """The Veda, read off the canonical key rather than stored twice and allowed to drift."""
    parts = str(row.get("canonical_key") or "").split(":")
    code = parts[1] if len(parts) > 1 else ""
    return f"{_VEDA_OF.get(code, code or 'unknown')} ({code})" if code else "unknown"


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sample_digest() -> str:
    return hashlib.sha256(SAMPLE.read_bytes()).hexdigest()


def load_sample() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The 100 rows, validated against the live queue before any of them is shown.

    Validation is not ceremony. The manifest was drawn on 2026-09-16 and the queue is a
    separate artifact; a row that has since changed its recording would put the reviewer
    in front of one file while the record said another, which is the failure this
    project already shipped once in a listening sheet written from expectation.
    """
    manifest = json.loads(SAMPLE.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = manifest["rows"]
    live = {row_key(r): r for r in read_jsonl(QUEUE)}

    missing = [r["review_id"] for r in rows if row_key(r) not in live]
    drifted = [
        r["review_id"]
        for r in rows
        if row_key(r) in live and live[row_key(r)].get("canonical_key") != r.get("canonical_key")
    ]
    if missing or drifted:
        raise SystemExit(
            f"The sample no longer matches the queue: {len(missing)} rows absent, "
            f"{len(drifted)} with a changed canonical key. First few: "
            f"{(missing + drifted)[:5]}. Re-draw is an owner decision, not this tool's."
        )
    # Carry across the queue fields the manifest does not hold, so the reviewer sees the
    # mapping the product actually uses rather than a copy taken two days earlier.
    for row in rows:
        source = live[row_key(row)]
        carried = ("start_seconds", "end_seconds", "prior_automated_checks", "licence")
        for field in (*carried, "attribution"):
            row.setdefault(field, source.get(field))
    return rows, manifest


def decisions_by_row() -> dict[str, dict[str, Any]]:
    """Latest decision per row. The log is the record; this is a projection of it."""
    latest: dict[str, dict[str, Any]] = {}
    for entry in read_jsonl(DECISIONS):
        latest[row_key(entry)] = entry
    return latest


def append_decision(entry: dict[str, Any]) -> None:
    """Append and fsync before returning, so a decision survives an immediate kill.

    Append-only on purpose: a changed mind writes a second line and both stay on the
    record. Nothing in this tool rewrites or removes an earlier verdict.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with DECISIONS.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def summarise(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    decided = decisions_by_row()
    verdicts = collections.Counter(
        decided[row_key(r)]["verdict"] for r in rows if row_key(r) in decided
    )
    by_stratum: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_stratum.setdefault(
            str(row["stratum"]), {"rows": 0, **{v: 0 for v in VERDICTS}, "undecided": 0}
        )
        bucket["rows"] += 1
        entry = decided.get(row_key(row))
        bucket[entry["verdict"] if entry else "undecided"] += 1

    accepted = verdicts["AUDIBLY_VERIFIED"]
    reviewed = sum(verdicts[v] for v in VERDICTS)
    queue_total = len(read_jsonl(QUEUE))

    # Every figure above is the *effective* one: the log replayed, last line per row key
    # wins. Where a row has more than one line the earlier verdicts are not in the counts,
    # so the summary has to say which rows those are -- otherwise the only way to notice
    # that a figure moved is to diff the log by hand.
    log = read_jsonl(DECISIONS)
    sampled = {row_key(r) for r in rows}
    superseded = [
        {
            "row_key": entry.get("corrects_row_key") or row_key(entry),
            "citation": entry.get("citation"),
            "from": entry.get("superseded_verdict"),
            "to": entry["verdict"],
            "reason": entry.get("correction_reason"),
            "corrected_at": entry.get("corrected_at"),
            "reviewer": entry.get("reviewer"),
            "superseded_decision_line": entry.get("superseded_decision_line"),
            "new_playback_performed": entry.get("new_playback_performed", False),
        }
        for entry in log
        if entry.get("entry_type") == "CORRECTION" and row_key(entry) in sampled
    ]

    return {
        "artifact": "OWNER_AUDIO_SAMPLE_REVIEW_SUMMARY",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "sample_manifest": str(SAMPLE.relative_to(ROOT)).replace("\\", "/"),
        "sample_manifest_sha256": sample_digest(),
        "sample_seed": manifest.get("seed"),
        "sample_size": len(rows),
        "reviewed": reviewed,
        "undecided": len(rows) - reviewed,
        "by_verdict": {v: verdicts[v] for v in VERDICTS},
        "by_stratum": by_stratum,
        # The two figures that must never be confused, spelled out rather than left to
        # a reader's arithmetic.
        "AUDIBLY_VERIFIED_SAMPLE": accepted,
        "audible_review_queue_total": queue_total,
        "NOT_INDIVIDUALLY_HEARD": queue_total - reviewed,
        "what_this_does_not_establish": (
            f"{accepted} recordings in a {len(rows)}-row seeded sample were accepted by a "
            f"named listener. The other {queue_total - reviewed} rows of the "
            f"{queue_total}-row queue were NOT individually heard and remain "
            "NEEDS_AUDIBLE_REVIEW. This summary is not, and may not be reported as, "
            f"AUDIBLY_VERIFIED = {queue_total}."
        ),
        "decisions_log": str(DECISIONS.relative_to(ROOT)).replace("\\", "/"),
        "decision_lines_in_log": len(log),
        "effective_verdicts_are": (
            "the last line per row key in the decision log. Nothing is deleted or edited, "
            "so a superseded verdict stays readable at the line named below."
        ),
        "corrections": superseded,
        "corrections_count": len(superseded),
    }


def write_summary(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    summary = summarise(rows, manifest)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return summary


# ---------------------------------------------------------------------------
# Correcting a mistyped verdict, without pretending to have listened twice
# ---------------------------------------------------------------------------
#
# A keystroke interface will eventually take the wrong keystroke. The repair must not be
# an edit: ``sample_decisions.jsonl`` is the record of what a named person decided and
# when, and a log you may rewrite is not a record. So a correction is a *second line* with
# the same row key, and :func:`decisions_by_row` -- which already keeps the last entry per
# key -- makes it the effective verdict with no new arithmetic anywhere.
#
# The part that needs a rule rather than a convention: a correction must not manufacture
# evidence. ``AUDIBLY_VERIFIED`` is refused unless the *superseded* row already records a
# recording that played, and when it is allowed the new line carries that row's playback
# forward verbatim -- same file, same sha256, same byte count -- flagged as carried rather
# than fresh. No fetch is made, no player is opened, and ``new_playback_performed`` is
# False on every correction, so a later reader counting listening events counts one per
# recording heard and not one per line written.


class CorrectionRefused(Exception):
    """A correction was asked for that the log or the sample does not support."""


def find_decided(review_id: str, media_url: str | None = None) -> tuple[str, dict[str, Any], int]:
    """The live decision for ``review_id``, its row key, and its 1-based line in the log.

    ``media_url`` is optional and required only when it has to be: ``review_id`` is not
    unique in this queue (see the module docstring), so a bare id matching two decided
    recordings is refused rather than resolved to whichever happened to come first.
    """
    entries = read_jsonl(DECISIONS)
    lines = {row_key(e): i + 1 for i, e in enumerate(entries)}
    decided = decisions_by_row()
    if media_url:
        key = f"{review_id}|{media_url}"
        if key not in decided:
            raise CorrectionRefused(f"no decision is recorded for {key}")
        return key, decided[key], lines[key]

    matches = [k for k in decided if k.split("|", 1)[0] == review_id]
    if not matches:
        raise CorrectionRefused(f"no decision is recorded for review_id {review_id}")
    if len(matches) > 1:
        joined = "\n    ".join(sorted(m.split("|", 1)[1] for m in matches))
        raise CorrectionRefused(
            f"{review_id} has {len(matches)} decided recordings; name one with "
            f"--media-url:\n    {joined}"
        )
    return matches[0], decided[matches[0]], lines[matches[0]]


def correction_entry(
    superseded: dict[str, Any],
    *,
    key: str,
    line_no: int,
    to_verdict: str,
    reason: str,
    reviewer: str,
    note: str,
) -> dict[str, Any]:
    """The line a correction appends. Built here so a test can read it without writing it."""
    return {
        # Identity, copied so the correction lands on exactly the row it supersedes.
        "review_id": superseded["review_id"],
        "media_url": superseded["media_url"],
        "canonical_key": superseded.get("canonical_key"),
        "citation": superseded.get("citation"),
        "stratum": superseded.get("stratum"),
        "verdict": to_verdict,
        "reviewer": reviewer,
        # The moment the recording was reviewed is the original one. A correction does not
        # move it, because nothing was reviewed today.
        "reviewed_at": superseded.get("reviewed_at"),
        "notes": note,
        "sample_manifest_sha256": superseded.get("sample_manifest_sha256"),
        # The correction itself.
        "entry_type": "CORRECTION",
        "corrects_row_key": key,
        "superseded_verdict": superseded["verdict"],
        "superseded_reviewed_at": superseded.get("reviewed_at"),
        "superseded_decision_line": line_no,
        "correction_reason": reason,
        "corrected_at": datetime.datetime.now(datetime.UTC).isoformat(),
        # The playback, carried rather than re-performed. See the section header.
        "new_playback_performed": False,
        "playback_provenance": "CARRIED_FORWARD_FROM_SUPERSEDED_DECISION",
        "recording_opened": bool(superseded.get("recording_opened")),
        "audio_file": superseded.get("audio_file"),
        "audio_content_type": superseded.get("audio_content_type"),
        "audio_bytes": superseded.get("audio_bytes"),
        "audio_sha256": superseded.get("audio_sha256"),
        "audio_resolution": superseded.get("audio_resolution"),
        "listened_seconds": superseded.get("listened_seconds"),
        "evidence_of_audio_consumption": (
            f"No new playback. This corrects the verdict recorded at line {line_no} of the "
            f"decision log ({superseded['verdict']} at {superseded.get('reviewed_at')}); the "
            "recording was played once, by that decision, and its evidence is carried here "
            f"unchanged: {superseded.get('evidence_of_audio_consumption')}"
        ),
        "tool": "scripts/review_audio_sample.py --correct",
    }


def apply_correction(
    rows: list[dict[str, Any]],
    *,
    review_id: str,
    media_url: str | None,
    to_verdict: str,
    reason: str,
    reviewer: str,
    note: str = "",
) -> dict[str, Any]:
    """Append a superseding decision, or refuse and name the rule that refused it."""
    if to_verdict not in VERDICTS:
        raise CorrectionRefused(f"{to_verdict} is not one of {', '.join(VERDICTS)}")
    if reason not in CORRECTION_REASONS:
        raise CorrectionRefused(
            f"{reason} is not a correction reason. A correction records an input error; a "
            "changed judgement goes through --redo, which plays the recording again. "
            f"Allowed: {', '.join(sorted(CORRECTION_REASONS))}"
        )
    if not reviewer.strip():
        raise CorrectionRefused("a correction needs a named reviewer")

    key, superseded, line_no = find_decided(review_id, media_url)

    if superseded["verdict"] == to_verdict:
        raise CorrectionRefused(f"{key} already reads {to_verdict}; nothing to correct")
    if str(superseded.get("reviewer", "")).strip().casefold() != reviewer.strip().casefold():
        raise CorrectionRefused(
            f"{key} was decided by {superseded.get('reviewer')!r}, not {reviewer!r}. "
            "Someone else re-deciding a row is a new review, not a correction."
        )
    # The sample the decision was taken against has to be the sample in front of us, or the
    # correction is landing on a row that has since moved.
    digest = sample_digest()
    if superseded.get("sample_manifest_sha256") != digest:
        raise CorrectionRefused(
            f"{key} was decided against sample manifest "
            f"{superseded.get('sample_manifest_sha256')}, and the manifest now hashes to "
            f"{digest}. The sample changed; re-review rather than correct."
        )
    if key not in {row_key(r) for r in rows}:
        raise CorrectionRefused(f"{key} is not in the current sample")
    # The rule that keeps a correction from inventing a hearing.
    if to_verdict in REQUIRES_AUDIO and not superseded.get("recording_opened"):
        raise CorrectionRefused(
            f"{to_verdict} asserts the recording was heard, and the decision being "
            "corrected records that nothing played. A correction may not supply a playback "
            "that never happened -- re-review the row with --redo and play it."
        )

    entry = correction_entry(
        superseded,
        key=key,
        line_no=line_no,
        to_verdict=to_verdict,
        reason=reason,
        reviewer=reviewer.strip(),
        note=note,
    )
    append_decision(entry)
    return entry


# ---------------------------------------------------------------------------
# Getting a playable file in front of the reviewer
# ---------------------------------------------------------------------------


class AudioUnavailable(Exception):
    """No playable audio could be produced for a row, with the reason a reviewer needs.

    ``browser_url`` is set only when the source turned out to be a page a human could
    play by hand. It is offered as a last resort and deliberately does not open the
    verdict gate: opening a page is not hearing a recording.
    """

    def __init__(self, reason: str, *, browser_url: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.browser_url = browser_url


@dataclasses.dataclass(frozen=True)
class Playable:
    """A local audio file, and the provenance of the bytes in it."""

    path: pathlib.Path
    content_type: str
    origin: str
    size: int
    sha256: str


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def guessed_type(path: pathlib.Path) -> str:
    """A content type for a file already on disk, named by its extension."""
    for content_type, suffix in AUDIO_EXTENSIONS.items():
        if suffix == path.suffix.lower():
            return content_type
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def fetchable_url(media_url: str) -> str:
    """The URL to actually request for a row's recording.

    Almost always the row's own URL. The exception is a Wikimedia *file page*, which is
    HTML with a player embedded in it rather than audio; the media itself is one redirect
    away through ``Special:FilePath``, so it is worth resolving rather than handing to the
    browser. If that ever stops working the response is HTML, which falls back to the
    browser exactly as any other unhandled page does.
    """
    match = _WIKIMEDIA_FILE_PAGE.match(media_url.strip())
    if match is None:
        return media_url.strip()
    return f"{match.group(1)}/wiki/Special:FilePath/{match.group(2)}"


def fetch(url: str) -> tuple[bytes, str]:
    """The response body and its declared content type. The only network call in this file.

    Read with a ceiling rather than unbounded: the measured median verse is about 40 KB,
    so ``MAX_AUDIO_BYTES`` is three orders of magnitude of headroom, and it is here so
    that a change upstream cannot turn one keystroke into an unbounded download.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
        body = response.read(MAX_AUDIO_BYTES + 1)
        declared = str(response.headers.get("Content-Type") or "")
    if len(body) > MAX_AUDIO_BYTES:
        raise AudioUnavailable(
            f"the response is larger than the {MAX_AUDIO_BYTES // (1024 * 1024)} MB review cap"
        )
    return body, declared.split(";")[0].strip().lower()


def extension_for(content_type: str, attachment_name: str = "") -> str:
    """The extension to save under, from the content type first and the filename second.

    The content type wins because it describes the bytes that actually arrived: a source
    naming its file ``.mp3`` while serving Ogg would otherwise put an unplayable file on
    disk under a name Windows hands to an MP3 decoder. ``mimetypes`` is consulted only
    after the explicit table, because its answer for ``audio/mpeg`` is read from the
    Windows registry and comes back ``.mpga`` on some machines -- and the player is
    chosen by extension, so a wrong one here is silence.
    """
    direct = AUDIO_EXTENSIONS.get(content_type.split(";")[0].strip().lower())
    if direct:
        return direct
    suffix = pathlib.PurePosixPath(attachment_name.strip()).suffix.lower()
    if suffix in set(AUDIO_EXTENSIONS.values()):
        return suffix
    return mimetypes.guess_extension(content_type) or ".bin"


def decode_attachment(payload: object) -> tuple[bytes, str, str]:
    """Audio bytes, content type and filename out of a VedSearch attachment document.

    Mirrors ``VedSearchClient.audio_bytes``' contract -- refuse rather than hand back an
    empty body -- but works from a document already fetched by URL, because the review
    queue holds the URL and not the ``(veda, shlok_id)`` pair the product client is keyed
    on.

    ``validate=True`` is the point of this function. Without it ``b64decode`` silently
    discards every character outside the base64 alphabet, so a truncated or corrupted
    payload decodes to plausible-looking garbage and gets written out as audio.
    """
    if not isinstance(payload, dict):
        raise AudioUnavailable("the response is JSON but not an object")
    document = payload.get("data")
    if not isinstance(document, dict):
        raise AudioUnavailable("the JSON response carries no 'data' object")

    content_type = str(document.get("content_type") or "").split(";")[0].strip().lower()
    if not content_type.startswith("audio/"):
        raise AudioUnavailable(
            f"the attachment declares content_type {content_type or '(none)'}, not audio/*"
        )

    encoded = document.get("attachment_content_base64")
    if not isinstance(encoded, str) or not encoded.strip():
        raise AudioUnavailable("the attachment carries no attachment_content_base64")
    # Whitespace is stripped rather than rejected: line-wrapped base64 is a formatting
    # choice, unlike a character outside the alphabet, which means corruption.
    # ``binascii.Error`` subclasses ``ValueError``, and a payload corrupted into non-ASCII
    # raises plain ``ValueError``, so the one clause covers both.
    try:
        raw = base64.b64decode("".join(encoded.split()), validate=True)
    except ValueError as error:
        raise AudioUnavailable(
            f"attachment_content_base64 is not valid base64 ({error})"
        ) from error
    if not raw:
        raise AudioUnavailable("attachment_content_base64 decoded to zero bytes")
    return raw, content_type, str(document.get("attachment_name") or "")


def cache_stem(row: dict[str, Any]) -> str:
    """A deterministic filename per *recording*, not per review id.

    ``review_id`` is not unique in this queue (see the module docstring), so naming the
    file after it alone would collapse four distinct Commons recordings onto one path and
    replay the first of them four times. The digest of the media URL is what makes this
    name identify the recording.
    """
    label = "".join(
        ch if ch.isalnum() or ch in "-._" else "_" for ch in str(row.get("review_id") or "row")
    )
    url_digest = hashlib.sha256(str(row.get("media_url") or "").encode("utf-8")).hexdigest()
    return f"{label[:100]}__{url_digest[:12]}"


def cached_audio(row: dict[str, Any]) -> pathlib.Path | None:
    """An already-downloaded copy of this recording, if one is on disk and non-empty."""
    stem = cache_stem(row)
    for path in sorted(CACHE_DIR.glob(f"{stem}.*")):
        if path.is_file() and path.suffix != ".part" and path.stat().st_size > 0:
            return path
    return None


def local_source(media_url: str) -> pathlib.Path | None:
    """The row's recording as a path, for a queue entry naming a file rather than a URL.

    ``None`` for anything that has to be fetched over the network. A bare Windows drive
    letter parses as a one-character URL scheme, which is why the scheme's length is
    tested rather than the presence of a colon.
    """
    raw = media_url.strip()
    if not raw:
        return None
    parts = urllib.parse.urlsplit(raw)
    if parts.scheme == "file":
        return pathlib.Path(urllib.request.url2pathname(parts.path))
    if len(parts.scheme) > 1:
        return None
    path = pathlib.Path(raw)
    return path if path.is_absolute() else ROOT / path


def looks_like_json(content_type: str, body: bytes) -> bool:
    """Whether to try the attachment wrapper.

    Sniffed from the body as well as the header, because a wrapper mislabelled
    ``text/plain`` is still a wrapper, and the alternative is telling the reviewer the
    audio is unavailable while holding it in memory.
    """
    if content_type in ("application/json", "text/json", "application/problem+json"):
        return True
    return body.lstrip()[:1] in (b"{", b"[")


def resolve_audio(row: dict[str, Any]) -> Playable:
    """A local, playable audio file for this row, or ``AudioUnavailable`` saying why not.

    Tried in order: a copy already downloaded in this or an earlier session, a local file
    the queue names outright, then the network -- where the *response* decides how it is
    handled rather than the hostname, so a provider that changes shape degrades to a
    stated failure instead of a wrong one. Nothing here launches a player or records
    anything.
    """
    media_url = str(row.get("media_url") or "").strip()
    if not media_url:
        raise AudioUnavailable("the row names no recording")

    hit = cached_audio(row)
    if hit is not None:
        blob = hit.read_bytes()
        return Playable(
            hit,
            guessed_type(hit),
            "replayed the copy already downloaded",
            len(blob),
            digest(blob),
        )

    local = local_source(media_url)
    if local is not None:
        if not local.is_file():
            raise AudioUnavailable(f"the row names a local file that is not there: {local}")
        blob = local.read_bytes()
        if not blob:
            raise AudioUnavailable(f"the local file is empty: {local}")
        return Playable(
            local, guessed_type(local), "played the local file", len(blob), digest(blob)
        )

    try:
        body, content_type = fetch(fetchable_url(media_url))
    except AudioUnavailable:
        raise
    except urllib.error.HTTPError as error:
        raise AudioUnavailable(f"the source answered HTTP {error.code} {error.reason}") from error
    except urllib.error.URLError as error:
        raise AudioUnavailable(f"the source could not be reached ({error.reason})") from error
    except (TimeoutError, OSError) as error:
        raise AudioUnavailable(f"{type(error).__name__}: {error}") from error

    if content_type.startswith("audio/"):
        audio, declared, name = body, content_type, media_url.rsplit("/", 1)[-1]
        origin = f"downloaded as a direct {content_type} response"
    elif looks_like_json(content_type, body):
        try:
            document = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AudioUnavailable(f"the response is not readable JSON ({error})") from error
        audio, declared, name = decode_attachment(document)
        origin = f"decoded from the base64 attachment in a JSON response ({declared})"
    else:
        # The residual case the browser fallback exists for: a page, not a recording.
        raise AudioUnavailable(
            f"the source returned {content_type or 'an undeclared content type'}, which is "
            "neither audio nor an attachment document",
            browser_url=media_url,
        )

    if not audio:
        raise AudioUnavailable("the source returned an empty body")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destination = CACHE_DIR / f"{cache_stem(row)}{extension_for(declared, name)}"
    # Written aside and renamed, so an interrupted download never leaves a truncated file
    # that the next session picks up and replays as though it were complete.
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.write_bytes(audio)
    partial.replace(destination)
    return Playable(destination, declared, origin, len(audio), digest(audio))


def launch(path: pathlib.Path) -> None:
    """Hand the file to whatever the machine plays audio with. The seam that makes noise."""
    opener = getattr(os, "startfile", None)
    if opener is not None:  # Windows, which is where this review is being run
        opener(os.fspath(path))
        return
    webbrowser.open(path.as_uri())  # pragma: no cover - not the reviewer's platform


def shown_path(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def play(row: dict[str, Any]) -> tuple[Playable | None, str]:
    """Resolve the recording and start it playing.

    Returns the file that was played, or ``None`` and the reason. That return value *is*
    the verdict gate: only a real decode and a real launch open Y and N. Nothing raises --
    a review session has to survive a source being down, and a failure has to leave the
    reviewer on the same row rather than advancing past a recording nobody heard.
    """
    try:
        playable = resolve_audio(row)
    except AudioUnavailable as error:
        message = f"Could not retrieve playable audio:\n    {error.reason}"
        if error.browser_url:
            webbrowser.open(error.browser_url)
            message += (
                f"\n    Opened {error.browser_url} in the browser as a last resort. A page is "
                "not a verdict: this row is still not playable here, so it stays U unless you "
                "review it with scripts/audio_review_harness.py, which measures what played."
            )
        return None, message
    except Exception as error:  # pragma: no cover - defensive; the session must not die
        return None, f"Could not retrieve playable audio:\n    {type(error).__name__}: {error}"

    try:
        launch(playable.path)
    except OSError as error:
        return None, (
            "Could not retrieve playable audio:\n    the audio decoded to "
            f"{shown_path(playable.path)} but no player would open it ({error})"
        )
    return playable, (
        f"playing {shown_path(playable.path)}\n"
        f"    {playable.size} bytes of {playable.content_type} -- {playable.origin}"
    )


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------


def show(
    row: dict[str, Any],
    position: int,
    total: int,
    reviewed: int,
    prior: dict[str, Any] | None,
) -> None:
    bar_width = 34
    filled = round(bar_width * reviewed / total) if total else 0
    print()
    print("=" * 78)
    print(f"  progress: {reviewed} / {total}   [{'#' * filled}{'.' * (bar_width - filled)}]")
    print(f"  row {position} of {total}   stratum {row['stratum']}   {row['review_id']}")
    print("=" * 78)
    print(f"  Veda            {veda_of(row)}")
    print(f"  canonical key   {row['canonical_key']}")
    print(f"  citation        {row['citation']}")
    print(f"  source          {row.get('source_name') or 'unstated'}"
          f"{'  --  ' + str(row['performer']) if row.get('performer') else ''}")
    print(f"  licence         {row.get('licence') or 'unstated'}")
    segment = (
        f"{row.get('start_seconds') or 0}s - {row.get('end_seconds') or 'end'}s"
        if row.get("start_seconds") is not None or row.get("end_seconds") is not None
        else "whole file, no stated offsets"
    )
    duration = row.get("duration_seconds")
    shown_duration = duration if duration is not None else "unstated"
    print(f"  segment         {segment}   duration {shown_duration}")
    mapping = (row.get("prior_automated_checks") or {}).get("mapping_method")
    print(f"  mapping method  {mapping or 'not recorded on this row'}")
    print(f"  recording       {row['media_url']}")
    ready = cached_audio(row)
    if ready is not None:
        print(f"  local copy      {shown_path(ready)}   (R replays this, nothing refetched)")
    sanskrit = str(row.get("canonical_sanskrit") or "").strip()
    if sanskrit:
        print("\n  Sanskrit (this corpus's text for that key):")
        for line in sanskrit.splitlines():
            print(f"    {line}")
    print(f"\n  Listen for: {row.get('listen_for') or 'is this the mapped verse?'}")
    if prior is not None:
        print(
            f"\n  ALREADY DECIDED: {prior['verdict']} by {prior['reviewer']} at "
            f"{prior['reviewed_at']}. Deciding again appends a second line; "
            "nothing is overwritten."
        )
    print()


def read_key(typed: bool) -> str:
    """One keystroke, or a typed word when raw capture is unavailable or declined."""
    if not typed:
        try:
            # Windows only, and imported here rather than at module scope so the tool
            # still runs where msvcrt does not exist.
            import msvcrt

            raw = msvcrt.getch()
            try:
                return raw.decode("utf-8", "ignore").lower().strip() or "?"
            except UnicodeDecodeError:  # pragma: no cover - defensive
                return "?"
        except ImportError:
            pass
    try:
        return input("  > ").strip().lower()
    except EOFError:
        return "q"


def resolve(token: str) -> str | None:
    """A keystroke or a typed word to a verdict, or ``None`` if it is not one."""
    return WORDS.get(token) or (KEYS.get(token) if len(token) == 1 else None)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def print_progress(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    summary = summarise(rows, manifest)
    print()
    print(f"  sample        {summary['sample_size']} rows, seed {summary['sample_seed']}")
    print(f"  manifest      {summary['sample_manifest']}")
    print(f"  sha256        {summary['sample_manifest_sha256'][:32]}...")
    print(f"  decisions     {summary['decisions_log']}")
    print()
    print(f"  reviewed      {summary['reviewed']} / {summary['sample_size']}"
          f"   undecided {summary['undecided']}")
    for verdict, count in summary["by_verdict"].items():
        print(f"    {verdict:28}{count:>5}")
    print()
    for stratum, counts in sorted(summary["by_stratum"].items()):
        done = counts["rows"] - counts["undecided"]
        print(f"    {stratum:34}{counts['rows']:>4} rows, {done:>4} reviewed")
    print()
    print(f"  AUDIBLY_VERIFIED_SAMPLE   {summary['AUDIBLY_VERIFIED_SAMPLE']}")
    print(f"  NOT_INDIVIDUALLY_HEARD    {summary['NOT_INDIVIDUALLY_HEARD']}"
          f"  (of a {summary['audible_review_queue_total']}-row queue)")
    print()


def print_rejected(rows: list[dict[str, Any]]) -> None:
    decided = decisions_by_row()
    hits = [
        (r, decided[row_key(r)])
        for r in rows
        if decided.get(row_key(r), {}).get("verdict") == "AUDIBLY_REJECTED"
    ]
    if not hits:
        print("\n  No row has been rejected.\n")
        return
    print(f"\n  {len(hits)} rejected:\n")
    for row, entry in hits:
        print(f"  {row['citation']}   {row['canonical_key']}   [{row['stratum']}]")
        print(f"    {row['media_url']}")
        print(f"    {entry['reviewer']} at {entry['reviewed_at']}")
        if entry.get("notes"):
            print(f"    notes: {entry['notes']}")
        print()


def review(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    reviewer: str,
    typed: bool,
    redo: bool = False,
) -> None:
    digest = sample_digest()
    print("\n  Y accept   N reject   U uncertain   S skip   R play/replay   Q quit")
    print("  (or type the word: yes / no / uncertain / skip / replay / quit)")
    print("  R fetches the recording, decodes it when the source wraps it in JSON, saves it")
    print(f"  under {shown_path(CACHE_DIR)}/ and opens it in your audio player.")
    print("  Accept and reject require that to have succeeded. A page that opened in a")
    print("  browser is not a recording that played.\n")

    index = 0
    while index < len(rows):
        decided = decisions_by_row()
        row = rows[index]
        # Resume is exactly this: a row with a recorded decision is not asked again.
        # --redo is the only way past it, and it appends rather than overwrites, so a
        # changed mind leaves both judgements on the record.
        if row_key(row) in decided and not redo:
            index += 1
            continue
        reviewed = sum(1 for r in rows if row_key(r) in decided)
        show(row, index + 1, len(rows), reviewed, decided.get(row_key(row)))

        # The verdict gate. Not a flag set by opening a URL: the file that played, or
        # None. See play() and the module docstring.
        played: Playable | None = None
        while True:
            token = read_key(typed)
            if token in ("q", "quit", "exit"):
                write_summary(rows, manifest)
                print(f"\n  Stopped. {reviewed} of {len(rows)} reviewed. Re-run to continue.\n")
                return
            if token in ("s", "skip", ""):
                print("  skipped -- nothing recorded for this row")
                index += 1
                break
            if token in ("r", "replay", "p", "play"):
                candidate, message = play(row)
                print(f"  {message}")
                if candidate is not None:
                    played = candidate
                continue
            verdict = resolve(token)
            if verdict is None:
                print("  ? Y accept, N reject, U uncertain, S skip, R replay, Q quit")
                continue
            if verdict in REQUIRES_AUDIO and played is None:
                print(
                    f"  {verdict} needs the recording to have played. Press R to play it, "
                    "or U if it will not play."
                )
                continue
            try:
                notes = input("  notes (what you heard; blank for none): ").strip()
            except EOFError:
                notes = ""
            append_decision(
                {
                    "review_id": row["review_id"],
                    "media_url": row["media_url"],
                    "canonical_key": row["canonical_key"],
                    "citation": row["citation"],
                    "stratum": row["stratum"],
                    "verdict": verdict,
                    "reviewer": reviewer,
                    "reviewed_at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "notes": notes,
                    "sample_manifest_sha256": digest,
                    "recording_opened": played is not None,
                    "audio_file": shown_path(played.path) if played else None,
                    "audio_content_type": played.content_type if played else None,
                    "audio_bytes": played.size if played else None,
                    "audio_sha256": played.sha256 if played else None,
                    "audio_resolution": played.origin if played else None,
                    # Stated rather than guessed at. A terminal cannot see inside the
                    # system player, so this tool records the file it decoded and handed
                    # over -- which is checkable after the fact -- and refuses to invent a
                    # duration. The browser harness measures it.
                    "listened_seconds": None,
                    "evidence_of_audio_consumption": (
                        f"{played.origin}; {played.size} bytes of {played.content_type} "
                        f"were written to {shown_path(played.path)} and opened in the "
                        "system audio player. Seconds heard are not measurable from a "
                        "terminal."
                        if played is not None
                        else "no playable audio was retrieved for this row; only UNCERTAIN "
                        "is reachable here"
                    ),
                    "tool": "scripts/review_audio_sample.py",
                }
            )
            print(f"  recorded {verdict}")
            index += 1
            break

    summary = write_summary(rows, manifest)
    print(f"\n  All {len(rows)} rows decided.")
    print(f"  AUDIBLY_VERIFIED_SAMPLE = {summary['AUDIBLY_VERIFIED_SAMPLE']}")
    print(f"  NOT_INDIVIDUALLY_HEARD  = {summary['NOT_INDIVIDUALLY_HEARD']}")
    print(f"  {summary['what_this_does_not_establish']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress", action="store_true", help="Counts only; decide nothing.")
    parser.add_argument("--rejected", action="store_true", help="List the rejected rows.")
    parser.add_argument("--typed", action="store_true", help="Typed commands, no raw keys.")
    parser.add_argument("--reviewer", default=None, help="Your name; else you are asked.")
    parser.add_argument(
        "--redo",
        action="store_true",
        help="Revisit rows already decided. Appends a second verdict; overwrites nothing.",
    )
    parser.add_argument(
        "--correct",
        metavar="REVIEW_ID",
        default=None,
        help="Supersede a decided row's verdict because the wrong key was pressed. "
        "Appends; plays nothing; edits nothing.",
    )
    parser.add_argument(
        "--media-url",
        default=None,
        help="Needed with --correct only when the review_id covers several recordings.",
    )
    parser.add_argument("--to", default=None, help="The corrected verdict.")
    parser.add_argument(
        "--reason",
        default=None,
        help=f"Why. One of: {', '.join(sorted(CORRECTION_REASONS))}",
    )
    parser.add_argument("--note", default="", help="Free text kept on the correction.")
    args = parser.parse_args()

    if not SAMPLE.exists():
        print(f"  {SAMPLE} does not exist.")
        return 1
    rows, manifest = load_sample()

    if args.progress:
        print_progress(rows, manifest)
        write_summary(rows, manifest)
        return 0
    if args.rejected:
        print_rejected(rows)
        return 0

    reviewer = (args.reviewer or "").strip()
    if not reviewer:
        try:
            reviewer = input("  Your name (a verdict needs a named listener): ").strip()
        except EOFError:
            reviewer = ""
    if not reviewer:
        print("  A verdict needs a named reviewer. Re-run with --reviewer NAME.")
        return 1

    if args.correct:
        if not args.to or not args.reason:
            print("  --correct needs --to VERDICT and --reason REASON.")
            return 1
        try:
            entry = apply_correction(
                rows,
                review_id=args.correct,
                media_url=args.media_url,
                to_verdict=args.to,
                reason=args.reason,
                reviewer=reviewer,
                note=args.note,
            )
        except CorrectionRefused as refusal:
            print(f"  refused: {refusal}")
            return 1
        summary = write_summary(rows, manifest)
        print(f"\n  corrected {entry['corrects_row_key']}")
        print(f"    {entry['superseded_verdict']} -> {entry['verdict']}  "
              f"({entry['correction_reason']})")
        print(f"    supersedes decision-log line {entry['superseded_decision_line']}, "
              "which is still there")
        print(f"    new playback performed: {entry['new_playback_performed']}")
        print(f"\n  reviewed {summary['reviewed']} of {len(rows)} -- "
              + "  ".join(f"{v}={summary['by_verdict'][v]}" for v in VERDICTS))
        print(f"  NOT_INDIVIDUALLY_HEARD = {summary['NOT_INDIVIDUALLY_HEARD']}\n")
        return 0

    print_progress(rows, manifest)
    review(rows, manifest, reviewer, args.typed or not sys.stdin.isatty(), args.redo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
