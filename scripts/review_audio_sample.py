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

WHAT COUNTS AS HAVING HEARD IT, AND THE LIMIT OF THIS TOOL
==========================================================

``AUDIBLY_VERIFIED`` and ``AUDIBLY_REJECTED`` are refused unless the recording was opened
in this session -- pressing Y without ever pressing play is not a verdict. That is a
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

Usage::

    python scripts/review_audio_sample.py                  # start or resume
    python scripts/review_audio_sample.py --progress       # counts, decide nothing
    python scripts/review_audio_sample.py --rejected       # inspect rejected rows
    python scripts/review_audio_sample.py --typed          # line input, no raw keys
    python scripts/review_audio_sample.py --reviewer NAME  # skip the name prompt
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import pathlib
import sys
import webbrowser
from typing import Any, Final

ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
SAMPLE: Final = ROOT / "data" / "staging" / "wave4" / "audio_owner_sample_manifest.json"
QUEUE: Final = ROOT / "data" / "staging" / "audio_review_queue.jsonl"
OUT_DIR: Final = ROOT / "data" / "manual" / "audio_review"
DECISIONS: Final = OUT_DIR / "sample_decisions.jsonl"
SUMMARY: Final = OUT_DIR / "sample_summary.json"

#: The same three the harness allows. A fourth would be a way to avoid deciding.
VERDICTS: Final[tuple[str, ...]] = (
    "AUDIBLY_VERIFIED",
    "AUDIBLY_REJECTED",
    "AUDIBLE_REVIEW_UNCERTAIN",
)

#: Verdicts asserting the reviewer heard the recording. Refused if it was never opened.
REQUIRES_AUDIO: Final[frozenset[str]] = frozenset({"AUDIBLY_VERIFIED", "AUDIBLY_REJECTED"})

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
    }


def write_summary(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    summary = summarise(rows, manifest)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return summary


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
    print("\n  Y accept   N reject   U uncertain   S skip   R replay   Q quit")
    print("  (or type the word: yes / no / uncertain / skip / replay / quit)")
    print("  Accept and reject both require the recording to have been opened first.\n")

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

        opened = False
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
                webbrowser.open(str(row["media_url"]))
                opened = True
                print("  opened in the system handler")
                continue
            verdict = resolve(token)
            if verdict is None:
                print("  ? Y accept, N reject, U uncertain, S skip, R replay, Q quit")
                continue
            if verdict in REQUIRES_AUDIO and not opened:
                print(
                    f"  {verdict} needs the recording to have been opened. Press R to play "
                    "it, or U if it will not play."
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
                    "audio_opened_in_this_session": opened,
                    # Stated rather than guessed at. A terminal cannot see inside the
                    # system player, so this tool records that the recording was opened
                    # and refuses to invent a duration. The browser harness measures it.
                    "listened_seconds": None,
                    "evidence_of_audio_consumption": (
                        "the reviewer opened the recording in the system handler; seconds "
                        "heard are not measurable from a terminal"
                        if opened
                        else "the recording was not opened; only UNCERTAIN is reachable here"
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

    print_progress(rows, manifest)
    review(rows, manifest, reviewer, args.typed or not sys.stdin.isatty(), args.redo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
