#!/usr/bin/env python3
"""Mark the release-prep receipt as superseded on ONE reading, changing no measured figure.

``data/staging/release_prep/release_prep_receipt.json`` is a dated receipt: it records what
was true at HEAD a40fb58, and its own ``head_at_start``/``head_now`` pin it there. It is not
a live claim and it is not a public product surface, so it is not rewritten here --
regenerating it would mean re-running release prep, which this pass is explicitly not.

But it states ``REGISTRY_IMPLEMENTATION_FIXABLE: 1`` and a ``why_not_closed`` for
OWNER_DECISION_F that section 42 has since answered, and a reader who opens it next has no
way to know that. So one additive key is written naming the supersession. Every measured
figure in the file is left exactly as it was: editing a receipt's numbers to agree with a
later state is indistinguishable from doctoring it, and the whole value of a dated receipt is
that it says what was true when it was taken.

Usage:
    python data/staging/samaveda_music_002_final/note_release_prep_supersession.py [--write]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "data" / "staging" / "release_prep" / "release_prep_receipt.json"
AUDIT = ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"

KEY = "superseded_on_2026_09_18"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    before = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()

    note = {
        "what_this_receipt_still_records_correctly": (
            "Everything it measured, at the HEAD it names. No figure in it has been edited."
        ),
        "what_has_since_changed": (
            "Exactly one reading: GAP-SAMAVEDA_MUSIC-002. This receipt records it as "
            "STILL_IMPLEMENTATION_FIXABLE with REGISTRY_IMPLEMENTATION_FIXABLE 1, because "
            "the fourth condition of OWNER_DECISION_F -- 'existing validation gates pass' -- "
            "was unmet with Gate B UNKNOWN and Gate C NOT_RUN."
        ),
        "what_settled_it": (
            "OWNER_DECISION_H_GATES_MEANS_A_AND_B_AND_C, OWNER_DECISIONS.md section 42, "
            "OWNER-SUPPLIED 2026-09-18: 'existing validation gates' means Gate A and Gate B "
            "and Gate C, not Gate A alone. The condition was then satisfied by building and "
            "running the two missing gates rather than by narrowing the word. Gate C found a "
            "real defect (39 withheld verses stating a reason the repository disproves), the "
            "defect was fixed by overlay, and the notation was imported."
        ),
        "current_reading": {
            "GAP-SAMAVEDA_MUSIC-002": "CLOSED_SOURCE_ACQUIRED",
            "REGISTRY_IMPLEMENTATION_FIXABLE": audit["counts"].get(
                "STILL_IMPLEMENTATION_FIXABLE", 0
            ),
            "OWNER_DECISION_REQUIRED": audit["counts"].get(
                "BLOCKED_OWNER_DECISION_REQUIRED", 0
            ),
            "measured_by": "data/staging/wave4/registry_closure_audit.json",
            "measured_at": audit["at"],
        },
        "unchanged_by_that_closure": {
            "NEEDS_AUDIBLE_REVIEW": audit["counts"].get("NEEDS_AUDIBLE_REVIEW", 0),
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA": audit["counts"].get(
                "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA", 0
            ),
            "note": (
                "The audio review and the Ask regrade are untouched by this pass. 0 of 1,021 "
                "files are heard and the notation is not audio: section 40 is the decision "
                "that separates them."
            ),
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
    print(f"  current        {note['current_reading']['GAP-SAMAVEDA_MUSIC-002']}, "
          f"fixable={note['current_reading']['REGISTRY_IMPLEMENTATION_FIXABLE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
