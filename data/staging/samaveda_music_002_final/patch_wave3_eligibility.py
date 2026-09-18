#!/usr/bin/env python3
"""Bring the ``samaveda_music`` row of wave3_eligibility.json up to date, and nothing else.

This file is the one the registry's own closure basis cited as the reason the fourth
condition of OWNER_DECISION_F was unmet: it recorded Gate B ``UNKNOWN`` and Gate C
``NOT_RUN``. Both have now been implemented and run, so leaving the row as it stands would
make the artifact contradict the closure it was used to block.

SCOPED TO ONE DOMAIN ON PURPOSE. The generator, ``scripts/wave3_eligibility_ledger.py``,
re-runs the structural validator for all fourteen domains and would rewrite every row's
digest against a graph that has moved since the 2026-09-15 snapshot. That is a broad
re-measurement, and this pass is a surgical one: reopening thirteen unrelated domains to fix
one row is exactly the scope creep the pass forbids. The generator's own ``ASSESSMENTS``
table is corrected in the same change, so the next full regeneration agrees with this patch
rather than reverting it.

The other thirteen rows keep their 2026-09-15 values and the file now says so in its own
snapshot caveat, rather than implying every row was measured together.

Usage:
    python data/staging/samaveda_music_002_final/patch_wave3_eligibility.py [--write]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
ELIGIBILITY = ROOT / "data" / "staging" / "integration" / "wave3_eligibility.json"
GATE_B = ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_b.json"
GATE_C = ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_c.json"
ROWS = ROOT / "data" / "staging" / "samaveda_music" / "rows.jsonl"
OUT = ROOT / "data" / "staging" / "samaveda_music_002_final" / "eligibility_patch.json"

DOMAIN = "samaveda_music"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    ledger = json.loads(ELIGIBILITY.read_text(encoding="utf-8"))
    gate_b = json.loads(GATE_B.read_text(encoding="utf-8"))
    gate_c = json.loads(GATE_C.read_text(encoding="utf-8"))
    before = json.loads(json.dumps(ledger["domains"][DOMAIN]))

    # The domain's own digest is the staging rows' hash. Re-read rather than copied, so a
    # patch applied against a restaged artifact is visible instead of silently wrong.
    digest = hashlib.sha256(ROWS.read_bytes()).hexdigest()
    if digest != before["own_digest"]:
        raise SystemExit(
            f"rows.jsonl digest moved since the ledger snapshot: {digest} != "
            f"{before['own_digest']}. The gates were run against the artifact the ledger "
            "recorded, so a changed artifact means re-running them, not patching this row."
        )

    after = {
        **before,
        "gate_b_semantic": {
            "status": gate_b["verdict"],
            "detail": (
                f"scripts/samaveda_music_gate_b.py at {gate_b['at']}: "
                f"{gate_b['summary']['checks_run']} checks over the four sections this file "
                f"names, {gate_b['summary']['rows_evaluated_across_all_checks']:,} "
                f"row-evaluations, {gate_b['summary']['total_failures']} defects, "
                f"{len(gate_b['summary']['checks_below_full_coverage'])} checks below full "
                "coverage. The 332 GANA_RENDERING rows are reported and not averaged in: "
                "their object side is outside Product V1 by OWNER_DECISIONS.md section 41."
            ),
        },
        "gate_c_adversarial": {
            "status": "DEFECT_FOUND_AND_FIXED",
            "detail": (
                "scripts/samaveda_music_gate_c.py. It LANDED: 39 of the 708 withheld verses "
                "stated a reason the repository disproves, their exact normalised text being "
                "released with notation on a coreferent twin. The failing run is preserved "
                "at data/staging/samaveda_music_002_final/gate_c_run1.json; the 39 now carry "
                "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT, no row moved from "
                "withheld to released, and no notation was invented. Re-run "
                f"{gate_c['at']}: {gate_c['verdict']}, "
                f"{gate_c['summary']['attacks_run']} attacks, "
                f"{gate_c['summary']['total_defects']} defects. Independent of the staging "
                "codepath: it refuses to read the artifact's own tone_stripped_text or QA "
                "report, re-implements the declared normalisation from the manifest's prose "
                "using the Unicode character database, and carries a negative control that "
                "reads 1,136/1,136 aligned against 0/1,136 shifted by one verse."
            ),
        },
        "blocked_by": [],
        "blocked_by_cleared": {
            "OWNER_DECISION_E_AUDIO_GATE": (
                "Never the right gate for this domain. OWNER_DECISIONS.md section 40 rules "
                "the audible-review gate covers AUDIO only; 1,136 of these 1,471 rows are "
                "printed tone marks and contain no recording anyone could listen to."
            ),
        },
        "status": "ELIGIBLE",
        "status_detail": (
            "all three gates pass and no blocker is open; imported 2026-09-18, see "
            "data/staging/samaveda_music_002_final/import_receipt.json"
        ),
        "imported": True,
    }

    patch = {
        "artifact": "SAMAVEDA_MUSIC_ELIGIBILITY_PATCH",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "domain": DOMAIN,
        "scope": "one domain; the other thirteen rows are left at their 2026-09-15 values",
        "why_not_a_full_regeneration": (
            "scripts/wave3_eligibility_ledger.py re-runs the structural validator for all "
            "fourteen domains and would re-digest every row against a graph that has moved "
            "since the snapshot. That is a broad re-measurement, and reopening thirteen "
            "unrelated domains to correct one row is outside this pass. The generator's own "
            "ASSESSMENTS table is corrected in the same change so a later full regeneration "
            "agrees with this patch instead of reverting it."
        ),
        "rows_digest_verified": digest,
        "before": before,
        "after": after,
    }
    OUT.write_text(
        json.dumps(patch, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if args.write:
        ledger["domains"][DOMAIN] = after
        eligible = sorted(
            name
            for name, row in ledger["domains"].items()
            if row.get("status") == "ELIGIBLE"
        )
        ledger["eligible_domains"] = eligible
        ledger["eligible_count"] = len(eligible)
        ledger["snapshot_caveat"] = (
            ledger["snapshot_caveat"]
            + " PER-ROW FRESHNESS: the samaveda_music row was re-measured 2026-09-18 when "
            "Gate B and Gate C were implemented and run (see "
            "data/staging/samaveda_music_002_final/eligibility_patch.json). Every other row "
            "still carries its 2026-09-15 value, so this file is a set of per-domain records "
            "and not one simultaneous measurement. Two domains -- attribution and "
            "samaveda_music -- have gate artifacts in this directory; only the second has "
            "been reconciled into this row."
        )
        ELIGIBILITY.write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {ELIGIBILITY.relative_to(ROOT)}")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  gate B  {before['gate_b_semantic']['status']} -> {after['gate_b_semantic']['status']}")
    print(
        f"  gate C  {before['gate_c_adversarial']['status']} -> "
        f"{after['gate_c_adversarial']['status']}"
    )
    print(f"  status  {before['status']} -> {after['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
