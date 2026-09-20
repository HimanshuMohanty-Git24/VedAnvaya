#!/usr/bin/env python3
"""Phase A and B: reconcile C_PASS = 922 against evidence-safe = 1,144, row for row.

The packet reported both figures and neither was wrong, so the reconciliation cannot
consist of picking one. It has to name the population each was computed over and then
account for every row in the difference. This script does that arithmetically and refuses
to emit anything if a row is missing from either adjudication.

Run:  python scripts/translation_integration_reconcile.py
"""

from __future__ import annotations

import collections
import json
import sys
from typing import Any

import translation_integration_common as T


def reconcile(packet: dict[str, Any], classified: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prior = packet["prior"]
    gate_b = packet["gate_b"]
    gate_c = packet["gate_c"]

    prior_safe = {i for i, r in prior.items() if r["final_class"].startswith("SAFE_IMPORT_")}
    b_pass = {i for i in packet["ids"] if gate_b[i]["gate_b_category"] == "B_PASS"}
    c_pass = {i for i in packet["ids"] if gate_c[i]["gate_c_category"] == "C_PASS"}

    c_pass_within_b_pass = c_pass & b_pass
    safe_not_c_pass = prior_safe - c_pass
    c_pass_not_safe = c_pass - prior_safe

    # The reported 922 counts C_PASS inside the Gate B passes. The reported 1,144 counts
    # every safe row. The 222 is therefore not one population minus a subset of itself,
    # and has two independent parts.
    reused_category = "C_WITHHOLD_REUSED_RENDERING_POLICY"
    delta_reused = sorted(
        i for i in safe_not_c_pass if gate_c[i]["gate_c_category"] == reused_category
    )
    delta_not_b_pass = sorted(prior_safe & c_pass - b_pass)
    delta_other = sorted(
        (safe_not_c_pass - set(delta_reused))
        | ((prior_safe & c_pass) - b_pass - set(delta_not_b_pass))
    )

    explained = len(delta_reused) + len(delta_not_b_pass)
    difference = len(prior_safe) - len(c_pass_within_b_pass)

    groups = [
        {
            "group": "SAFE_AND_C_PASS_BUT_GATE_B_PARKED_IT",
            "rows": len(delta_not_b_pass),
            "why_it_is_outside_the_922": (
                "922 was computed over the 1,187 rows whose Gate B category is B_PASS. "
                "These rows carry B_NEEDS_INDEPENDENT_CONTENT_CONTROL: Gate B declined to "
                "pass a forced address until a content control existed, Gate C then found "
                "the independent control in the printed source and returned C_PASS. They "
                "are C_PASS rows that the 922 tally could not see."
            ),
            "owner_policy_dependency": "OWNER_DECISION_C_FORCED_ADDRESSES",
            "by_veda": dict(collections.Counter(prior[i]["veda"] for i in delta_not_b_pass)),
            "gate_b_verdicts": dict(
                collections.Counter(gate_b[i]["gate_b_category"] for i in delta_not_b_pass)
            ),
            "gate_c_verdicts": dict(
                collections.Counter(gate_c[i]["gate_c_category"] for i in delta_not_b_pass)
            ),
            "row_ids": delta_not_b_pass,
        },
        {
            "group": "SAFE_BUT_GATE_C_WITHHELD_PENDING_AN_OWNER_POLICY",
            "rows": len(delta_reused),
            "why_it_is_outside_the_922": (
                "Gate C withheld these deliberately and only because the reused-rendering "
                "policy had not been decided. The evidence is complete -- the target's "
                "Sanskrit is verified character-identical to a Rigvedic verse Griffith "
                "translated -- so the matrix counted them safe, while C_PASS could not."
            ),
            "owner_policy_dependency": "OWNER_DECISION_D_REUSED_RENDERING_POLICY",
            "by_veda": dict(collections.Counter(prior[i]["veda"] for i in delta_reused)),
            "gate_b_verdicts": dict(
                collections.Counter(gate_b[i]["gate_b_category"] for i in delta_reused)
            ),
            "gate_c_verdicts": dict(
                collections.Counter(gate_c[i]["gate_c_category"] for i in delta_reused)
            ),
            "row_ids": delta_reused,
        },
    ]

    # Rows Gate C passed that the matrix did NOT call safe. Not part of the 222, but the
    # reconciliation is not honest without them: they are why 966 != 922 + 222.
    counter_direction = {
        "rows": len(c_pass_not_safe),
        "what_it_is": (
            "rows Gate C passed adversarially whose Gate B verdict is a hard failure. Gate "
            "C assesses every staged row so the packet can report on withheld populations "
            "too, so a C_PASS here means 'the adversarial checks found nothing against it', "
            "not 'it may be imported'."
        ),
        "gate_b_verdicts": dict(
            collections.Counter(gate_b[i]["gate_b_category"] for i in sorted(c_pass_not_safe))
        ),
        "terminal_classes_now": dict(
            collections.Counter(classified[i]["final_class"] for i in sorted(c_pass_not_safe))
        ),
        "row_ids": sorted(c_pass_not_safe),
    }

    return {
        "phase": "A",
        "total_staged_rows": len(packet["ids"]),
        "the_two_reported_figures": {
            "C_PASS": {
                "value": len(c_pass_within_b_pass),
                "population": "the 1,187 rows whose Gate B category is B_PASS",
                "artifact": "gate_c_summary.json :: by_category_assessed.C_PASS",
                "reproduced": len(c_pass_within_b_pass) == 922,
            },
            "C_PASS_over_all_staged_rows": {
                "value": len(c_pass),
                "population": "all 2,254 staged rows",
                "note": (
                    "Gate C ran its deterministic checks over every staged row, so the "
                    "row-level C_PASS population is larger than the figure the summary "
                    "reported. This number appears in no headline and is stated here so "
                    "the two are never confused again."
                ),
            },
            "evidence_safe": {
                "value": len(prior_safe),
                "population": "every row the decision matrix placed in a SAFE_IMPORT_* class",
                "artifact": "translation_decision_matrix.json :: safe_total",
                "reproduced": len(prior_safe) == 1144,
            },
        },
        "difference": {
            "arithmetic": f"{len(prior_safe)} - {len(c_pass_within_b_pass)} = {difference}",
            "value": difference,
            "rows_explained": explained,
            "fully_explained": explained == difference,
            "groups": groups,
        },
        "the_opposite_direction": counter_direction,
        "identity_check": {
            "c_pass_all_rows": len(c_pass),
            "equals_c_pass_in_b_pass_plus_the_forced_group_plus_the_counter_direction": (
                len(c_pass)
                == len(c_pass_within_b_pass) + len(delta_not_b_pass) + len(c_pass_not_safe)
            ),
        },
        "rows_missing_from_gate_c_adjudication": 0,
        "unexplained_rows": len(delta_other),
        "unexplained_row_ids": delta_other,
        "verdict": (
            "RECONCILED"
            if explained == difference and not delta_other
            else "TRANSLATION_IMPORT_BLOCKED_ACCOUNTING_INCONSISTENCY"
        ),
    }


def matrix_report(classified: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = T.class_counts(classified)
    rows = list(classified.values())

    def tally(field: str, predicate=lambda r: True) -> dict[str, int]:
        return dict(sorted(collections.Counter(r[field] for r in rows if predicate(r)).items()))

    by_class_veda: dict[str, dict[str, int]] = {}
    for row in rows:
        by_class_veda.setdefault(row["final_class"], {})
        by_class_veda[row["final_class"]][row["veda"]] = (
            by_class_veda[row["final_class"]].get(row["veda"], 0) + 1
        )

    importable = [r for r in rows if r["importable"]]
    return {
        "phase": "B",
        "classes_declared": list(T.ALL_CLASSES),
        "mutually_exclusive": True,
        "final_class_counts": counts,
        "sum_of_final_class_counts": sum(counts.values()),
        "distinct_row_ids": len({r["row_id"] for r in rows}),
        "assertions": {
            "sum_equals_2254": sum(counts.values()) == T.EXPECTED_ROWS,
            "distinct_row_ids_equals_2254": len({r["row_id"] for r in rows}) == T.EXPECTED_ROWS,
        },
        "by_class_and_veda": by_class_veda,
        "importable_rows": len(importable),
        "withheld_or_rejected_rows": len(rows) - len(importable),
        "importable_by_veda": tally("veda", lambda r: r["importable"]),
        "importable_by_source": tally("source_id", lambda r: r["importable"]),
        "importable_by_language": tally("import_language", lambda r: r["importable"]),
        "independent_english_rows": len(
            [r for r in importable if r["counts_as_independent_english"]]
        ),
        "owner_policy_dependencies": tally("owner_policy_dependency"),
        "product_semantics_dependencies": tally("product_semantics_dependency"),
        "movement_from_the_prior_matrix": _movement(rows),
    }


def _movement(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Where this round's class differs from round 2's, and why.

    Printed as a transition table rather than a total, because "22 rows moved" invites the
    reader to assume they moved the same way.
    """
    moved = collections.Counter((r["prior_final_class"], r["final_class"]) for r in rows)
    changed_importability = collections.Counter(
        (r["prior_final_class"], r["final_class"])
        for r in rows
        if r["prior_final_class"].startswith("SAFE_IMPORT_") is not r["importable"]
    )
    return {
        "transitions": {f"{a} -> {b}": n for (a, b), n in sorted(moved.items())},
        "rows_whose_importability_changed": sum(changed_importability.values()),
        "importability_transitions": {
            f"{a} -> {b}": n for (a, b), n in sorted(changed_importability.items())
        },
    }


def main() -> int:
    packet = T.load_packet()
    classified = T.classify(packet)
    T.assert_one_disposition(classified)

    recon = reconcile(packet, classified)
    matrix = matrix_report(classified)
    recon["phase_b"] = matrix

    T.write_json(T.INTEGRATION / "gate_reconciliation.json", recon)
    T.write_jsonl(
        T.INTEGRATION / "gate_reconciliation_rows.jsonl",
        [classified[i] for i in packet["ids"]],
    )

    print(json.dumps(recon["the_two_reported_figures"], indent=1))
    print()
    print("DIFFERENCE:", recon["difference"]["arithmetic"])
    for group in recon["difference"]["groups"]:
        print(f"  {group['rows']:5d}  {group['group']}  {group['by_veda']}")
    print("  explained:", recon["difference"]["rows_explained"], "of", recon["difference"]["value"])
    print()
    print(
        "OPPOSITE DIRECTION (C_PASS but not safe):",
        recon["the_opposite_direction"]["rows"],
        recon["the_opposite_direction"]["gate_b_verdicts"],
    )
    print()
    print("FINAL CLASS COUNTS")
    for name, n in matrix["final_class_counts"].items():
        print(f"  {n:6d}  {name}")
    print(f"  {matrix['sum_of_final_class_counts']:6d}  TOTAL")
    print()
    print("assertions:", json.dumps(matrix["assertions"]))
    print("importable rows:", matrix["importable_rows"], matrix["importable_by_veda"])
    print("VERDICT:", recon["verdict"])

    if recon["verdict"] != "RECONCILED":
        return 1
    if not all(matrix["assertions"].values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
