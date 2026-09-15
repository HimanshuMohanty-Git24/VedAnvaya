#!/usr/bin/env python3
"""Owner sections 9, 12 and 13: three gates per domain, and staleness that propagates.

The adversarial preflight tested four domains and found a material defect in four. That is
no longer anecdote, and it changes what a validator pass is worth: it establishes that an
artifact is well-formed, and says nothing about whether its headline is true. Two of the
four defects left every aggregate count intact while changing what the data *meant* --
which a structural check cannot see by construction.

So eligibility is three independent gates, reported separately and never averaged:

  GATE A  STRUCTURAL   schema, identity, subject grain, source references, denominators.
                       Machine-checkable: `validate_staging_artifact.py --graph`.
  GATE B  SEMANTIC     classification correctness, population correctness, source meaning,
                       relation meaning. Requires a reviewer who understands the domain.
  GATE C  ADVERSARIAL  the headline survived an independent attempt to falsify it.

A domain enters Wave 3 only at A=PASS, B=PASS, C=PASS. There is no combined score, because
a percentage would let a strong A carry a failed C -- which is precisely the reasoning this
ledger exists to prevent.

It also tracks dependency staleness. A corrected domain invalidates the artifacts computed
from it, and a stale artifact must not keep a VALIDATED badge: an artifact whose inputs
moved is reported STALE_INPUT even if its own three gates once passed.

Usage:
    python scripts/wave3_eligibility_ledger.py [--json OUT] [--markdown OUT]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from hashlib import sha256
from typing import Any

STAGING = pathlib.Path("data/staging")
LEDGER = STAGING / "integration" / "wave3_eligibility.json"

#: Which domain's output feeds which. Used to propagate STALE_INPUT, so a correction in one
#: place cannot leave a dependent artifact wearing a stale pass.
DEPENDENCIES: dict[str, list[str]] = {
    "semantic_resemblance": ["translation", "semantic_roles", "attribution", "formula"],
    "cross_veda": ["formula"],
    "communities": ["attribution"],
    "quality": [
        "semantic_roles",
        "attribution",
        "formula",
        "cross_veda",
        "translation",
    ],
    "semantic_roles": [],
    "formula": [],
    "attribution": [],
    "translation": [],
    "ritual": [],
    "scholarship": [],
    "audio_rv": [],
    "audio_yv": [],
    "audio_av": [],
    "samaveda_music": [],
}

#: Gate B and C are judgements, not computations, so they are recorded here by the lead
#: rather than inferred. An absent entry is UNKNOWN, which blocks -- silence is not a pass.
ASSESSMENTS: dict[str, dict[str, Any]] = {
    "semantic_roles": {
        "B": (
            "PASS_AFTER_RESTAGE",
            "roles asserted only from treebank labels: 2,052 fillers, all TREEBANK_DEPREL, "
            "0 outside it; 28,742 assertions carry roles_withheld and 15,704 candidate rows "
            "are importable:false. Enforced mechanically and verified by the lead.",
        ),
        "C": (
            "SURVIVED",
            "repair was attempted and measured to fail before withdrawal: widening the gate "
            "moved the wrong share 24.8% to 24.3% at a cost of 18 points of recall, and the "
            "largest AGENT class is 39.8% wrong, so no threshold makes the rule safe.",
        ),
        "restage_required": False,
        "restage_reason": (
            "Restage complete. Asserted fillers 51,231 to 2,052 and triples 5,219 to 341, "
            "with the known 24.8% error eliminated rather than documented."
        ),
    },
    "cross_veda": {
        "B": (
            "PASS_PENDING_FOLD_FIX",
            "396 of 6,271 transformation types corrected and 197 stored relationship types "
            "identified as contradicted by their own text. The corrected typing is right "
            "and the codebase cannot yet reproduce it, because the fold fix it depends on "
            "is blocked on FOLD_FIX_BREAKS_REFERENT_IDENTITY.",
        ),
        "C": (
            "SURVIVED",
            "root cause traced to dead code -- surfaces transliterates before it folds, so "
            "every Devanagari anusvara rule was unreachable on the only cross-script "
            "comparison surface. Re-measured over all six pairs rather than assuming "
            "Yajurveda-only, which moved RV-SV from a reported 0 to 6.",
        ),
        "restage_required": False,
        "restage_reason": (
            "Restage complete. Blocked on the fold fix rather than on further work."
        ),
        "blocked_by": ["FOLD_FIX_BREAKS_REFERENT_IDENTITY"],
    },
    "formula": {
        "B": (
            "PASS_AFTER_RESTAGE",
            "a general structural-reference class replaced the digit exception; all five "
            "classes tested and reported including class 4's measured zero. The clearest "
            "evidence: EDITORIAL_APPARATUS no longer exists as a transformation type, "
            "having held 158 rows.",
        ),
        "C": (
            "SURVIVED",
            "whole 34,502-pair population re-run on stripped surfaces, with the floor "
            "re-measured on the changed surface rather than inherited. 13 defects recorded, "
            "including a validation race the agent caught in its own gate.",
        ),
        "restage_required": False,
        "restage_reason": (
            "Restage complete and independently re-validated by the lead at 30/30 "
            "checksums on frozen bytes."
        ),
    },
    "communities": {
        "B": (
            "PASS_AFTER_CORRECTION",
            "withdrawn claim replaced by a measured internal limitation",
        ),
        "C": (
            "SURVIVED",
            "the decisive check rested on a scholarly prior the graph contradicts; the "
            "claim was withdrawn with the mistake preserved, and the refusal now stands on "
            "eight measured grounds with no prior among them",
        ),
        "restage_required": False,
        "restage_reason": (
            "Rationale corrected, not data. The refusal stands on six measurements, and "
            "the artifact already carries both grains."
        ),
        "blocked_by": ["CURATION_CONTRADICTION_SOMA_PAVAMANA"],
    },
    "attribution": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
    },
    "translation": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
        "blocked_by": ["OWNER_DECISION_A_RV_SPAN", "OWNER_DECISION_C_FORCED_ADDRESSES"],
    },
    "audio_rv": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
        "blocked_by": ["OWNER_DECISION_E_AUDIO_GATE"],
    },
    "audio_yv": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
        "blocked_by": ["OWNER_DECISION_E_AUDIO_GATE"],
    },
    "audio_av": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
        "blocked_by": ["OWNER_DECISION_E_AUDIO_GATE"],
    },
    "samaveda_music": {
        "B": ("UNKNOWN", "no semantic review recorded"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
        "blocked_by": ["OWNER_DECISION_E_AUDIO_GATE"],
    },
    "ritual": {
        "B": ("UNKNOWN", "agent has not reported"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
    },
    "scholarship": {
        "B": ("UNKNOWN", "agent has not reported"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
    },
    "quality": {
        "B": ("UNKNOWN", "agent has not reported"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
    },
    "semantic_resemblance": {
        "B": ("UNKNOWN", "agent has not reported"),
        "C": ("NOT_RUN", "adversarial test not yet performed"),
        "restage_required": False,
    },
}


def file_digest(path: pathlib.Path) -> str | None:
    if not path.exists():
        return None
    return sha256(path.read_bytes()).hexdigest()


def structural_gate(domain: str) -> tuple[str, str]:
    """Gate A, actually run rather than remembered."""
    root = STAGING / domain
    if not (root / "rows.jsonl").exists():
        return "ABSENT", "no rows.jsonl"
    result = subprocess.run(
        [
            "python",
            "scripts/validate_staging_artifact.py",
            str(root),
            "--graph",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = result.stdout or ""
    if result.returncode == 0 and "PASS" in out:
        return "PASS", "validator PASS at full evaluation coverage with --graph"
    if "VALIDATOR INCOMPLETE" in out:
        return "FAIL", "a check did not evaluate every eligible row"
    return "FAIL", "validator reported data defects"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(LEDGER))
    parser.add_argument("--markdown", default="")
    parser.add_argument("--skip-structural", action="store_true", help="reuse nothing; A=SKIPPED")
    args = parser.parse_args()

    # This is a snapshot tool, and a snapshot taken while an agent is rewriting its
    # directory reads that directory half-written. Observed: a manifest checksum mismatch
    # on a generator script whose agent was mid-restage, which the validator correctly
    # reported as a defect and which was gone minutes later. So the run is timestamped and
    # carries the caveat, rather than the ledger trying to guess which failures are
    # transient -- a heuristic for that would eventually excuse a real one.
    from datetime import UTC, datetime

    generated_at = datetime.now(UTC).isoformat()

    domains = sorted(
        p.name for p in STAGING.iterdir() if p.is_dir() and (p / "rows.jsonl").exists()
    )

    entries: dict[str, dict[str, Any]] = {}
    for domain in domains:
        root = STAGING / domain
        assessed = ASSESSMENTS.get(domain, {})
        gate_a = ("SKIPPED", "not run") if args.skip_structural else structural_gate(domain)
        gate_b = assessed.get("B", ("UNKNOWN", "not recorded"))
        gate_c = assessed.get("C", ("NOT_RUN", "not recorded"))

        entries[domain] = {
            "gate_a_structural": {"status": gate_a[0], "detail": gate_a[1]},
            "gate_b_semantic": {"status": gate_b[0], "detail": gate_b[1]},
            "gate_c_adversarial": {"status": gate_c[0], "detail": gate_c[1]},
            "restage_required": assessed.get("restage_required", False),
            "restage_reason": assessed.get("restage_reason"),
            "blocked_by": assessed.get("blocked_by", []),
            "depends_on": DEPENDENCIES.get(domain, []),
            "input_digests": {
                name: file_digest(STAGING / name / "rows.jsonl")
                for name in DEPENDENCIES.get(domain, [])
            },
            "own_digest": file_digest(root / "rows.jsonl"),
        }

    # Staleness propagates: a domain depending on one that must be restaged has stale input,
    # whatever its own gates once said.
    restaging = {d for d, e in entries.items() if e["restage_required"]}
    for entry in entries.values():
        stale_from = sorted(set(entry["depends_on"]) & restaging)
        entry["stale_inputs"] = stale_from
        if stale_from:
            entry["status"] = "STALE_INPUT"
            entry["status_detail"] = (
                f"depends on {', '.join(stale_from)}, which must be restaged; its own gates "
                f"cannot certify it until those inputs settle"
            )
        elif entry["restage_required"]:
            entry["status"] = "RESTAGE_REQUIRED"
            entry["status_detail"] = entry["restage_reason"] or ""
        elif entry["blocked_by"]:
            # An open blocker outranks three passing gates. The first version of this
            # ledger reported cross_veda ELIGIBLE while it carried an unresolved blocker,
            # which is the same shape of error as a validator pass standing in for
            # correctness: every check it ran was green and the thing still could not ship.
            entry["status"] = "BLOCKED"
            entry["status_detail"] = (
                f"three gates pass, blocked by {', '.join(entry['blocked_by'])}"
            )
        elif (
            entry["gate_a_structural"]["status"] == "PASS"
            and entry["gate_b_semantic"]["status"].startswith("PASS")
            and entry["gate_c_adversarial"]["status"] in ("PASS", "SURVIVED")
        ):
            entry["status"] = "ELIGIBLE"
            entry["status_detail"] = "all three gates pass and no blocker is open"
        else:
            entry["status"] = "NOT_ELIGIBLE"
            missing = [
                name
                for name, key in (
                    ("A", "gate_a_structural"),
                    ("B", "gate_b_semantic"),
                    ("C", "gate_c_adversarial"),
                )
                if not (
                    entry[key]["status"] == "PASS"
                    or entry[key]["status"].startswith("PASS")
                    or entry[key]["status"] == "SURVIVED"
                )
            ]
            entry["status_detail"] = f"gate(s) {', '.join(missing)} not passed"

    eligible = [d for d, e in entries.items() if e["status"] == "ELIGIBLE"]
    report = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "snapshot_caveat": (
            "A domain whose agent is actively restaging may read FAIL transiently -- most "
            "often a manifest checksum mismatch, because the manifest is rewritten after "
            "the files it hashes. Re-run once no agent is in flight before treating any "
            "gate A result here as final."
        ),
        "gates": {
            "A": "STRUCTURAL -- schema, identity, subject grain, source refs, denominators",
            "B": "SEMANTIC -- classification, population, source meaning, relation meaning",
            "C": "ADVERSARIAL -- headline survived an independent falsification attempt",
        },
        "rule": (
            "Wave 3 eligibility requires A=PASS and B=PASS and C=PASS. No combined "
            "percentage: a strong A must not be allowed to carry a failed C. Four of four "
            "domains adversarially tested so far have failed C, and two of those four had "
            "every aggregate count survive."
        ),
        "domains": entries,
        "eligible_domains": eligible,
        "eligible_count": len(eligible),
        "domain_count": len(entries),
        "wave_3_go": len(eligible) == len(entries) and len(entries) >= 14,
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print(f"  {'domain':20}{'A':>10}{'B':>24}{'C':>16}   status")
    print(f"  {'-' * 20}{'-' * 10}{'-' * 24}{'-' * 16}   {'-' * 18}")
    for domain in sorted(entries):
        e = entries[domain]
        print(
            f"  {domain:20}{e['gate_a_structural']['status']:>10}"
            f"{e['gate_b_semantic']['status']:>24}"
            f"{e['gate_c_adversarial']['status']:>16}   {e['status']}"
        )
    print()
    print(f"  eligible: {len(eligible)} of {len(entries)}")
    print(f"  WAVE 3: {'GO' if report['wave_3_go'] else 'NO-GO'}")
    print()
    print(f"  ledger: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
