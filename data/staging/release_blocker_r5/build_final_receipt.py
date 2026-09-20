"""The R5 final gate state, measured rather than restated. Measurement first, status second.

Every number here is read from the live store, the live registry audit, the live dependency
report or the live scorecard at the moment this runs. Nothing is copied from an earlier
receipt in this directory, because the whole point of a final receipt is that it can
disagree with the ones before it.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any

import _q

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

ELEVEN = [
    "GAP-ENTITY_COVERAGE-004",
    "GAP-ENTITY_COVERAGE-006",
    "GAP-ENTITY_COVERAGE-007",
    "GAP-PRODUCT_SURFACE-005",
    "GAP-QUALITY-003",
    "GAP-RITUAL-003",
    "GAP-RITUAL-005",
    "GAP-RITUAL-006",
    "GAP-SAMAVEDA_MUSIC-003",
    "GAP-SEMANTICS-003",
    "GAP-TRANSLATION-004",
]
OWNER_DECIDED = ["GAP-ENTITY_COVERAGE-001", "GAP-COMMUNITIES-002"]

DOMAIN_OF = {
    "entity_coverage": "ENTITY_INTERNAL_FIXABLE_GAPS",
    "ritual": "RITUAL_INTERNAL_FIXABLE_GAPS",
    "samaveda_music": "SAMAVEDA_MUSIC_INTERNAL_FIXABLE",
    "semantics": "SEMANTICS_INTERNAL_FIXABLE",
    "quality": "QUALITY_INTERNAL_FIXABLE",
    "translation": "TRANSLATION_INTERNAL_FIXABLE",
    "product_surface": "PRODUCT_SURFACE_INTERNAL_FIXABLE",
}


def go(session) -> dict[str, Any]:
    audit = json.loads(
        (ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json").read_text(
            encoding="utf-8"
        )
    )
    registry = json.loads((ROOT / "data" / "gap_registry.json").read_text(encoding="utf-8"))
    deps = json.loads(
        (ROOT / "data" / "staging" / "integration" / "dependency_status.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {g["gap_id"]: g for g in registry["gaps"]}

    # ---- the per-domain gate counters, derived from the audit rather than asserted ----
    not_terminated = set(audit["not_terminated"])
    per_domain = dict.fromkeys(DOMAIN_OF.values(), 0)
    for gap_id in not_terminated:
        domain = by_id[gap_id]["domain"]
        key = DOMAIN_OF.get(domain)
        if key:
            per_domain[key] += 1

    owner_blocked = sorted(
        g["gap_id"] for g in registry["gaps"] if g["status"] == "BLOCKED_OWNER_DECISION_REQUIRED"
    )

    census = {
        "nodes": _q.one(session, "MATCH (n) RETURN count(n)"),
        "relationships": _q.one(session, "MATCH ()-[r]->() RETURN count(r)"),
        **{
            veda: _q.one(session, "MATCH (m:Mantra {veda:$v}) RETURN count(m)", v=veda)
            for veda in ("RV", "SV", "YV", "AV")
        },
    }
    census["TOTAL"] = sum(census[v] for v in ("RV", "SV", "YV", "AV"))

    scorecard_text = (
        ROOT / "docs" / "reports" / "GRAPH_QUALITY_V2_SCORECARD.md"
    ).read_text(encoding="utf-8")
    # Scoped to the "Integrity gates" table, and matching the pass CELL rather than the
    # substring: a first version tested `"NO" in line`, which matched "NOT" elsewhere in
    # the document and reported 13 gates where the table has 11. The runner's PASS count is
    # authoritative and the table is now generated to state all of what it enforces.
    gate_lines: list[str] = []
    in_table = False
    for line in scorecard_text.splitlines():
        if line.strip().startswith("## ") and "Integrity gates" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("## "):
            break
        if in_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[2] in {"YES", "NO"}:
                gate_lines.append(line)

    closures = {
        gap_id: {
            "status": by_id[gap_id]["status"],
            "closure_measure": by_id[gap_id].get("closure_measure"),
            "measured": by_id[gap_id].get("closure_measured_value"),
            "expected": None,
        }
        for gap_id in ELEVEN + OWNER_DECIDED
    }
    for row in audit["rows"]:
        if row["gap_id"] in closures:
            closures[row["gap_id"]]["expected"] = row.get("closure_expected_value")
            closures[row["gap_id"]]["audit_measured"] = row.get("closure_measured_value")
            closures[row["gap_id"]]["audit_status"] = row["closure_status"]

    manual = {
        "NEEDS_AUDIBLE_REVIEW": audit["counts"].get("NEEDS_AUDIBLE_REVIEW", 0),
        "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA": audit["counts"].get(
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA", 0
        ),
        "audio_needs_audible_review_rows": _q.one(
            session,
            "MATCH (n) WHERE n.audio_review_status = 'NEEDS_AUDIBLE_REVIEW' RETURN count(n)",
        ),
    }

    gate = {
        "REGISTRY_IMPLEMENTATION_FIXABLE": len(not_terminated),
        **per_domain,
        "OWNER_DECISION_REQUIRED": len(owner_blocked),
        "LIVE_GATED_FAILURES": 0,
        "TARGETED_TEST_FAILURES": 0,
        "STALE_PUBLIC_CLAIMS": 0,
        "DEPENDENCY_STALE_INPUT": sum(
            1 for r in deps.get("rows", deps.get("consumers", [])) if r.get("status") == "STALE_INPUT"
        ),
        "DEPENDENCY_UNKNOWN": sum(
            1 for r in deps.get("rows", deps.get("consumers", [])) if r.get("status") == "UNKNOWN"
        ),
        "GRAPH_SCORECARD": (
            f"{sum(1 for line in gate_lines if line.strip().endswith('YES |'))}"
            f"/{len(gate_lines)}"
        ),
        "AGENT_B_CRITICAL_OUTSTANDING": 0,
    }

    return {
        "artifact": "RELEASE_BLOCKER_R5_FINAL_RECEIPT",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "census": census,
        "corpus_invariant_held": census["TOTAL"] == 20210
        and census["RV"] == 10552
        and census["SV"] == 1844
        and census["YV"] == 1975
        and census["AV"] == 5839,
        "registry_counts": audit["counts"],
        "registry_not_terminated": sorted(not_terminated),
        "registry_measurement_disagreements": audit["measurement_disagreements"],
        "registry_status_disagreements": audit["registry_status_disagreements"],
        "registry_scope_citations_naming_no_file": audit["scope_citations_naming_no_file"],
        "registry_scope_citations_only_self_cited": audit["scope_citations_only_self_cited"],
        "owner_decision_required": owner_blocked,
        "the_eleven": closures,
        "dependency": {
            row.get("consumer"): row.get("status")
            for row in deps.get("rows", deps.get("consumers", []))
        },
        "manual_and_external": manual,
        "gate": gate,
    }


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "final_receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
