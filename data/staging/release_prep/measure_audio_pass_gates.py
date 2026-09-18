#!/usr/bin/env python3
"""The five release gates plus the audio figures, remeasured after the audio sample pass.

Every value is read from a live artifact at the moment this runs -- the registry audit, the
gap registry, the dependency report, the generated scorecard and the audio decision log --
and nothing is copied from ``release_blocker_r5/final_receipt.json``. The point of
remeasuring is that it is allowed to disagree with the last receipt.

The gate definitions are the R5 ones, unchanged, so the two receipts are comparable:
``data/staging/release_blocker_r5/build_final_receipt.py``.

Usage::

    python data/staging/release_prep/measure_audio_pass_gates.py [--write]
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
AUDIT = ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"
REGISTRY = ROOT / "data" / "gap_registry.json"
DEPS = ROOT / "data" / "staging" / "integration" / "dependency_status.json"
SCORECARD = ROOT / "docs" / "reports" / "GRAPH_QUALITY_V2_SCORECARD.md"
ACCEPTANCE = ROOT / "data" / "manual" / "audio_review" / "owner_sample_acceptance.json"
SUMMARY = ROOT / "data" / "manual" / "audio_review" / "sample_summary.json"
OUT = ROOT / "data" / "staging" / "release_prep" / "audio_pass_final_gates.json"


def scorecard_gates() -> tuple[int, int]:
    """Passing and total integrity gates, read off the generated table.

    Matching the pass *cell* rather than the substring, for the reason R5 records: a
    ``"NO" in line`` test matched "NOT" elsewhere in the document and reported 13 gates
    where the table has 11.
    """
    lines: list[str] = []
    in_table = False
    for line in SCORECARD.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("## ") and "Integrity gates" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("## "):
            break
        if in_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[2] in {"YES", "NO"}:
                lines.append(line)
    return sum(1 for line in lines if line.strip().endswith("YES |")), len(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    deps = json.loads(DEPS.read_text(encoding="utf-8"))
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    rows = deps.get("rows", deps.get("consumers", []))
    passing, total = scorecard_gates()
    owner_blocked = sorted(
        g["gap_id"]
        for g in registry["gaps"]
        if g["status"] == "BLOCKED_OWNER_DECISION_REQUIRED"
    )

    receipt = {
        "artifact": "AUDIO_OWNER_SAMPLE_PASS_FINAL_GATES",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "gate": {
            "REGISTRY_IMPLEMENTATION_FIXABLE": len(audit["not_terminated"]),
            "OWNER_DECISION_REQUIRED": len(owner_blocked),
            "DEPENDENCY_STALE_INPUT": sum(
                1 for r in rows if r.get("status") == "STALE_INPUT"
            ),
            "DEPENDENCY_UNKNOWN": sum(1 for r in rows if r.get("status") == "UNKNOWN"),
            "GRAPH_SCORECARD": f"{passing}/{total}",
        },
        "audio": {
            "AUDIO_OWNER_SAMPLE": acceptance["AUDIO_OWNER_SAMPLE"],
            "AUDIO_SAMPLE_REVIEWED": acceptance["SAMPLE_REVIEWED"],
            "AUDIO_SAMPLE_VERIFIED": acceptance["SAMPLE_VERIFIED"],
            "AUDIO_SAMPLE_UNCERTAIN": acceptance["SAMPLE_UNCERTAIN"],
            "AUDIO_SAMPLE_REJECTED": acceptance["SAMPLE_REJECTED"],
            "queue_total": summary["audible_review_queue_total"],
            "NOT_INDIVIDUALLY_HEARD": summary["NOT_INDIVIDUALLY_HEARD"],
            "queue_rows_promoted": acceptance["scope"]["rows_promoted_by_this_decision"],
            "decision_lines_in_log": summary["decision_lines_in_log"],
            "corrections": summary["corrections_count"],
        },
        "still_open_and_counted_apart": {
            "NEEDS_AUDIBLE_REVIEW": audit["counts"].get("NEEDS_AUDIBLE_REVIEW", 0),
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA": audit["counts"].get(
                "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA", 0
            ),
            "ASK_FORMAL_60": "PENDING_OWNER_EXECUTION",
            "note": (
                "Execution blockers, terminal for 'nothing is OPEN' and not data-completeness "
                "closure. The three NEEDS_AUDIBLE_REVIEW entries are unchanged by the sample "
                "acceptance: their requirement is promotion of 954 staged rows, gated by "
                "OWNER_DECISION_E_AUDIO_GATE on the queue being heard, and 1,001 of 1,021 "
                "rows have not been."
            ),
        },
        "measured_from": {
            "registry_audit": "data/staging/wave4/registry_closure_audit.json",
            "registry_audit_at": audit["at"],
            "registry": "data/gap_registry.json",
            "dependency": "data/staging/integration/dependency_status.json",
            "dependency_at": deps.get("at"),
            "scorecard": "docs/reports/GRAPH_QUALITY_V2_SCORECARD.md",
            "audio_acceptance": "data/manual/audio_review/owner_sample_acceptance.json",
            "gate_definitions": "data/staging/release_blocker_r5/build_final_receipt.py",
        },
    }

    for key, value in receipt["gate"].items():
        print(f"  {key:34} {value}")
    print()
    for key, value in receipt["audio"].items():
        print(f"  {key:34} {value}")

    if args.write:
        OUT.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
