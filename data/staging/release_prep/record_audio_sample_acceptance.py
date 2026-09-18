#!/usr/bin/env python3
"""Record the owner's sample-acceptance decision, with every figure read rather than typed.

The decision is the owner's; the numbers in it are not. Every count here is recomputed
from ``data/manual/audio_review/sample_decisions.jsonl`` by replaying the log -- last line
per row key -- and the script refuses to write if what it measures disagrees with what the
decision asserts. A figure typed into a decision record is the one figure nothing checks,
and this repository has already shipped that mistake once.

WHAT THE DECISION IS, AND THE LINE IT MUST NOT CROSS
====================================================

The owner listened to 20 recordings from the seeded 100-row sample and accepts them as
sufficient release-level audible QA of the acquisition and mapping pipeline. That is a
statement about a *sample*. The queue holds 1,021 rows and 1,001 of them have not been
played by anyone.

So the artifact states both, and this script enforces the second:

* ``rows_promoted_by_this_decision`` is 0, checked against the live queue -- every one of
  the 1,021 rows must still read ``NEEDS_AUDIBLE_REVIEW`` after this runs, and the script
  refuses if one does not.
* ``remaining_recordings_status`` is ``NOT_INDIVIDUALLY_HEARD``, and the residual is
  computed as queue minus reviewed rather than asserted.

Acceptance of a sample is not a licence to relabel the population it was drawn from.
``OWNER_DECISION_E_AUDIO_GATE`` (OWNER_DECISIONS.md section 14) is untouched by this: the
1,021-row queue stays mandatory and no automated check may relabel a row.

Usage::

    python data/staging/release_prep/record_audio_sample_acceptance.py          # dry run
    python data/staging/release_prep/record_audio_sample_acceptance.py --write
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SUMMARY = ROOT / "data" / "manual" / "audio_review" / "sample_summary.json"
DECISIONS = ROOT / "data" / "manual" / "audio_review" / "sample_decisions.jsonl"
QUEUE = ROOT / "data" / "staging" / "audio_review_queue.jsonl"
MANIFEST = ROOT / "data" / "staging" / "wave4" / "audio_owner_sample_manifest.json"
OUT = ROOT / "data" / "manual" / "audio_review" / "owner_sample_acceptance.json"

#: What the owner's decision asserts. Measured against the log below; a disagreement is a
#: refusal to write, not a warning.
ASSERTED = {"REVIEWED": 20, "VERIFIED": 20, "UNCERTAIN": 0, "REJECTED": 0}

DECISION_TEXT = (
    "The owner manually listened to 20 recordings from the deterministic VedAnvaya owner "
    "audio sample. All 20 reviewed recordings matched their expected Vedic passage/audio "
    "mapping. No reviewed recording was rejected and no effective uncertain verdict "
    "remains. The owner accepts this sample as sufficient release-level audible QA of the "
    "automated audio acquisition and mapping pipeline. This is SAMPLE-LEVEL validation. It "
    "does NOT mean every queued recording was individually heard."
)


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def row_key(row: dict) -> str:
    return f"{row.get('review_id') or ''}|{row.get('media_url') or ''}"


def measure() -> tuple[dict, list[str]]:
    """Replay the log and the queue. Returns the measurement and every disagreement."""
    log = read_jsonl(DECISIONS)
    queue = read_jsonl(QUEUE)

    effective: dict[str, dict] = {}
    for entry in log:
        effective[row_key(entry)] = entry

    counts = {
        "REVIEWED": len(effective),
        "VERIFIED": sum(1 for e in effective.values() if e["verdict"] == "AUDIBLY_VERIFIED"),
        "UNCERTAIN": sum(
            1 for e in effective.values() if e["verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
        ),
        "REJECTED": sum(1 for e in effective.values() if e["verdict"] == "AUDIBLY_REJECTED"),
    }

    problems = [
        f"{name}: the decision asserts {want} and the log replays to {counts[name]}"
        for name, want in ASSERTED.items()
        if counts[name] != want
    ]

    # The promotion check. A sample acceptance that moved a queue row would be the exact
    # failure this artifact is written to make impossible.
    promoted = [r for r in queue if r.get("review_status") != "NEEDS_AUDIBLE_REVIEW"]
    if promoted:
        problems.append(
            f"{len(promoted)} queue rows no longer read NEEDS_AUDIBLE_REVIEW; a sample "
            "acceptance may not promote one"
        )

    heard = set(effective)
    residual = [r for r in queue if row_key(r) not in heard]
    if len(residual) != len(queue) - counts["REVIEWED"]:
        problems.append(
            f"the {counts['REVIEWED']} reviewed rows do not all resolve to queue rows: "
            f"{len(queue)} - {counts['REVIEWED']} != {len(residual)}"
        )

    corrections = [e for e in log if e.get("entry_type") == "CORRECTION"]
    fabricated = [e for e in corrections if e.get("new_playback_performed") is not False]
    if fabricated:
        problems.append(f"{len(fabricated)} corrections claim a playback of their own")

    measurement = {
        "counts": counts,
        "queue_total": len(queue),
        "residual": len(residual),
        "decision_lines": len(log),
        "corrections": corrections,
    }
    return measurement, problems


def build(measurement: dict) -> dict:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    counts = measurement["counts"]
    return {
        "artifact": "OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE",
        "decision_id": "OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE",
        "provenance": "OWNER-SUPPLIED",
        "recorded_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "recorded_in": "docs/reports/data-completeness/OWNER_DECISIONS.md section 43",
        "decision": DECISION_TEXT,
        "AUDIO_OWNER_SAMPLE": "ACCEPTED",
        "SAMPLE_REVIEWED": counts["REVIEWED"],
        "SAMPLE_VERIFIED": counts["VERIFIED"],
        "SAMPLE_UNCERTAIN": counts["UNCERTAIN"],
        "SAMPLE_REJECTED": counts["REJECTED"],
        "sample": {
            "manifest": "data/staging/wave4/audio_owner_sample_manifest.json",
            "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "seed": summary.get("sample_seed"),
            "size": summary.get("sample_size"),
            "reviewed_of_size": f"{counts['REVIEWED']} of {summary.get('sample_size')}",
            "strata_reviewed": {
                stratum: bucket["AUDIBLY_VERIFIED"]
                for stratum, bucket in summary.get("by_stratum", {}).items()
            },
        },
        "scope": {
            "level": "SAMPLE_LEVEL",
            "what_this_establishes": (
                f"{counts['VERIFIED']} recordings drawn by a published seed from the "
                "audible-review queue were played by a named listener and matched the "
                "passage they are mapped to. That is evidence about the acquisition and "
                "mapping pipeline, and the owner accepts it as sufficient for release."
            ),
            "what_this_does_not_establish": (
                f"That the queue was heard. {measurement['residual']} of "
                f"{measurement['queue_total']} rows have not been played by anyone and "
                "remain NEEDS_AUDIBLE_REVIEW. This decision may not be reported as "
                f"AUDIBLY_VERIFIED = {measurement['queue_total']}, and no report, UI or API "
                "surface may describe it as exhaustive manual review."
            ),
            "queue_total": measurement["queue_total"],
            "remaining_recordings": measurement["residual"],
            "remaining_recordings_status": "NOT_INDIVIDUALLY_HEARD",
            "rows_promoted_by_this_decision": 0,
            "owner_decision_e_audio_gate": (
                "Untouched. OWNER_DECISIONS.md section 14 stands: the 1,021-row queue stays "
                "mandatory, no automated check may relabel a row, and GAP-AUDIO-002, -003 "
                "and -004 stay NEEDS_AUDIBLE_REVIEW because their release requirement is "
                "promotion of 954 staged rows, not acceptance of a sample."
            ),
        },
        "corrections_replayed": [
            {
                "row_key": c.get("corrects_row_key"),
                "citation": c.get("citation"),
                "from": c.get("superseded_verdict"),
                "to": c.get("verdict"),
                "reason": c.get("correction_reason"),
                "reviewer": c.get("reviewer"),
                "superseded_decision_line": c.get("superseded_decision_line"),
                "new_playback_performed": c.get("new_playback_performed"),
            }
            for c in measurement["corrections"]
        ],
        "measured_from": {
            "decisions_log": "data/manual/audio_review/sample_decisions.jsonl",
            "decisions_log_sha256": hashlib.sha256(DECISIONS.read_bytes()).hexdigest(),
            "decision_lines": measurement["decision_lines"],
            "summary": "data/manual/audio_review/sample_summary.json",
            "effective_verdicts_are": (
                "the last line per row key. Corrections append; nothing is edited or "
                "deleted, so every superseded verdict stays readable in the log."
            ),
            "recomputed_by": "data/staging/release_prep/record_audio_sample_acceptance.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    measurement, problems = measure()
    counts = measurement["counts"]
    print(f"  reviewed  {counts['REVIEWED']}")
    print(f"  verified  {counts['VERIFIED']}")
    print(f"  uncertain {counts['UNCERTAIN']}")
    print(f"  rejected  {counts['REJECTED']}")
    print(f"  queue     {measurement['queue_total']}, unheard {measurement['residual']}")
    print(f"  log lines {measurement['decision_lines']}, "
          f"corrections {len(measurement['corrections'])}")

    if problems:
        print("\n  REFUSED. The decision does not match what the log measures:")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    record = build(measurement)
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\n  wrote {OUT.relative_to(ROOT)}")
    else:
        print("\n  measurement agrees with the decision; re-run with --write to record it")
    print(f"  AUDIO_OWNER_SAMPLE = {record['AUDIO_OWNER_SAMPLE']}")
    print(f"  rows promoted      = {record['scope']['rows_promoted_by_this_decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
