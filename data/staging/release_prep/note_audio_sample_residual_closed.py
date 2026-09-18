#!/usr/bin/env python3
"""Close the receipt's ``AUDIO_SAMPLE_REVIEW: PENDING_OWNER`` residual, editing no figure.

``release_prep_receipt.json`` is a dated receipt pinned to HEAD a40fb58, and section 40's
supersession note already set the precedent this follows: a receipt is not rewritten when
the world moves under it, because a receipt whose numbers were edited to agree with a later
state is indistinguishable from a doctored one. One additive key is written instead.

The residual it closes is the owner *execution* task -- the 100-row sample had no verdicts
on it when the receipt was taken. It now has 20, and the owner has accepted them
(OWNER_DECISIONS.md section 43). What that does **not** close is
``OWNER_DECISION_E_AUDIO_GATE``: the three ``NEEDS_AUDIBLE_REVIEW`` registry entries need
954 staged rows promoted into the product catalogue, section 14 gates that on the queue
being heard, and 1,001 of 1,021 rows have not been. So the note states the closure and the
non-closure side by side, and reads both from the live artifacts rather than restating them.

Usage::

    python data/staging/release_prep/note_audio_sample_residual_closed.py [--write]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "data" / "staging" / "release_prep" / "release_prep_receipt.json"
ACCEPTANCE = ROOT / "data" / "manual" / "audio_review" / "owner_sample_acceptance.json"
SUMMARY = ROOT / "data" / "manual" / "audio_review" / "sample_summary.json"
AUDIT = ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"

KEY = "audio_sample_residual_closed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    before = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()

    note = {
        "what_this_closes": (
            "manual_and_external_residuals.AUDIO_SAMPLE_REVIEW, which this receipt recorded "
            "as PENDING_OWNER with audio.reviewed 0 and AUDIBLY_VERIFIED_SAMPLE 0. The owner "
            "has since listened to 20 rows of the seeded 100-row sample and accepted them."
        ),
        "settled_by": (
            "OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE, OWNER_DECISIONS.md section 43, "
            "OWNER-SUPPLIED 2026-09-18."
        ),
        "current_reading": {
            "AUDIO_SAMPLE_REVIEW": "CLOSED_OWNER_SAMPLE_ACCEPTED",
            "AUDIO_OWNER_SAMPLE": acceptance["AUDIO_OWNER_SAMPLE"],
            "AUDIO_SAMPLE_REVIEWED": acceptance["SAMPLE_REVIEWED"],
            "AUDIO_SAMPLE_VERIFIED": acceptance["SAMPLE_VERIFIED"],
            "AUDIO_SAMPLE_UNCERTAIN": acceptance["SAMPLE_UNCERTAIN"],
            "AUDIO_SAMPLE_REJECTED": acceptance["SAMPLE_REJECTED"],
            "measured_by": "data/manual/audio_review/owner_sample_acceptance.json",
            "measured_at": acceptance["recorded_at"],
        },
        "what_it_does_not_close": {
            "NEEDS_AUDIBLE_REVIEW": audit["counts"].get("NEEDS_AUDIBLE_REVIEW", 0),
            "entries": ["GAP-AUDIO-002", "GAP-AUDIO-003", "GAP-AUDIO-004"],
            "why": (
                "Their release requirement is the promotion of 954 staged rows into the "
                "product catalogue, which OWNER_DECISION_E_AUDIO_GATE (section 14) gates on "
                "the 1,021-row queue being heard. It has not been: "
                f"{summary['NOT_INDIVIDUALLY_HEARD']} of "
                f"{summary['audible_review_queue_total']} rows remain "
                "NOT_INDIVIDUALLY_HEARD. A sample acceptance is not a licence to relabel the "
                "population it was drawn from, and 0 queue rows were promoted."
            ),
            "queue_rows_promoted": acceptance["scope"]["rows_promoted_by_this_decision"],
        },
        "also_unchanged": {
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA": audit["counts"].get(
                "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA", 0
            ),
            "ASK_FORMAL_60": "PENDING_OWNER_EXECUTION",
        },
        "receipt_figures_edited": 0,
        "noted_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    if args.write:
        receipt[KEY] = note
        RECEIPT.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        after = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
        print(f"wrote {RECEIPT.relative_to(ROOT)}")
        print(f"  sha256 before  {before}")
        print(f"  sha256 after   {after}")
    print(f"  keys added     1 ({KEY})")
    print(f"  figures edited {note['receipt_figures_edited']}")
    print(f"  AUDIO_SAMPLE_REVIEW  {note['current_reading']['AUDIO_SAMPLE_REVIEW']}")
    print(f"  still open           NEEDS_AUDIBLE_REVIEW="
          f"{note['what_it_does_not_close']['NEEDS_AUDIBLE_REVIEW']}, "
          f"promoted={note['what_it_does_not_close']['queue_rows_promoted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
