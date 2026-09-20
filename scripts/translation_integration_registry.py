#!/usr/bin/env python3
"""Phase L: re-measure the translation gaps, and close only what is actually closed.

The rule this script exists to enforce is the one the task states: do not close a gap
because coverage improved. Each entry carries a ``closure_test`` written when the gap was
opened, and the only question is whether that test now passes. Three of the four
translation gaps moved a long way and none of them passes.

There is a second, subtler thing to report. Two of the closure tests are written as
``NOT (p)-[:HAS_TRANSLATION]->()``, and that predicate no longer means "has no
translation": a verse inside a multi-verse print unit carries no edge of its own and is
covered. So each gap is measured twice -- once by its test as literally written, and once
on the definition the test was reaching for -- and both numbers are recorded. Reporting
only the first would call 30 covered Rigvedic verses untranslated; reporting only the
second would quietly rewrite the gap's own acceptance criterion.

Run:  python scripts/translation_integration_registry.py [--write]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import Any, Final

import translation_integration_common as T

REGISTRY: Final = T.REPO / "data" / "gap_registry.json"

#: Per gap: the Veda it measures, and what its closure test demands.
TRANSLATION_GAPS: Final[dict[str, str]] = {
    "GAP-TRANSLATION-001": "SV",
    "GAP-TRANSLATION-002": "AV",
    "GAP-TRANSLATION-003": "YV",
    "GAP-TRANSLATION-004": "RV",
}

_MEASURE: Final = """
MATCH (m:Mantra {veda: $veda})
OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
WITH m, collect(t) AS ts
RETURN
  count(m) AS corpus,
  // The closure test exactly as written in the registry.
  count(CASE WHEN size(ts) = 0 THEN 1 END) AS no_edge_of_its_own,
  // The four populations, on their own definitions.
  count(CASE WHEN any(x IN ts WHERE x.language = 'en' AND x.reuse_kind IS NULL
                        AND x.alignment_level <> 'MANTRA_RANGE') THEN 1 END) AS dedicated,
  count(CASE WHEN any(x IN ts WHERE x.reuse_kind = 'REUSED_RENDERING')
             THEN 1 END) AS reused,
  count(CASE WHEN any(x IN ts WHERE x.language <> 'en')
              AND none(x IN ts WHERE x.language = 'en') THEN 1 END) AS other_language
"""

_RANGE_COVERED: Final = """
MATCH (:Mantra {veda: $veda})-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.alignment_level = 'MANTRA_RANGE'
UNWIND t.covers_canonical_keys AS key
MATCH (m:Mantra {canonical_key: key})
RETURN count(DISTINCT m) AS range_covered
"""


def measure(session: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for gap_id, veda in TRANSLATION_GAPS.items():
        row = session.run(_MEASURE, veda=veda).single()
        span = session.run(_RANGE_COVERED, veda=veda).single()["range_covered"]
        corpus = row["corpus"]
        covered_by_something = row["dedicated"] + span + row["reused"] + row["other_language"]
        out[gap_id] = {
            "veda": veda,
            "corpus_mantras": corpus,
            "closure_test_as_written": {
                "cypher": (
                    f"MATCH (p:Mantra) WHERE p.veda='{veda}' AND NOT "
                    "(p)-[:HAS_TRANSLATION]->() RETURN count(p)"
                ),
                "demands": 0,
                "measured": row["no_edge_of_its_own"],
                "passes": row["no_edge_of_its_own"] == 0,
                "caveat": (
                    "this predicate counts a verse inside a multi-verse print unit as "
                    "untranslated, which it is not"
                ),
            },
            "populations": {
                "dedicated_translation": row["dedicated"],
                "range_covered": span,
                "reused_rendering": row["reused"],
                "other_language": row["other_language"],
                "uncovered": corpus - covered_by_something,
            },
            "verses_no_rendering_of_any_kind_reaches": corpus - covered_by_something,
            "closure_condition_met": (corpus - covered_by_something) == 0,
        }
    return out


def verdicts(measured: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """What each gap's status should be, with the reason stated rather than implied."""
    out = {}
    for gap_id, row in measured.items():
        veda = row["veda"]
        uncovered = row["verses_no_rendering_of_any_kind_reaches"]
        pops = row["populations"]
        if uncovered == 0:
            status = "CLOSED_DERIVED"
            reason = f"every {veda} mantra is now reached by a rendering"
        else:
            status = "STILL_IMPLEMENTATION_FIXABLE"
            reason = (
                f"{uncovered} {veda} verses are reached by no rendering of any kind, so the "
                "gap's own closure test is not met. Coverage improved substantially and "
                "that is not closure."
            )
        if gap_id == "GAP-TRANSLATION-001":
            # The Samaveda is the case where improved coverage is most misleading: all 173
            # are Rigvedic renderings and the gap is about the Samaveda's own translation.
            reason = (
                f"{pops['reused_rendering']} of 1,844 Samavedic verses now show a rendering, "
                "and every one of them is Griffith's Rigvedic English on verified-identical "
                "text, disclosed as reuse. The gap asks for a Kauthuma-aligned Samaveda "
                "translation and the count of those is still 0, so this is not partial "
                f"closure: {uncovered} verses have nothing, and the other 173 have another "
                "corpus's."
            )
        out[gap_id] = {
            "status_now": status,
            "reason": reason,
            "closed_this_round": status.startswith("CLOSED"),
        }
    return out


#: The two owner decisions this round resolves, and what resolving them means.
OWNER_DECISION_UPDATES: Final[dict[str, dict[str, Any]]] = {
    "OWNER_DECISION_A_RV_SPAN": {
        "resolution": "CLOSED",
        "basis": (
            "Mechanically resolved. M13 re-anchored RV 1.65-1.70 onto the paired-dvipada "
            "spine and typed the 30 renderings MANTRA_RANGE with their complete covered-key "
            "lists; this round made the product read that typing, so the 30 paired verses "
            "are served their covering unit, marked as anchored elsewhere, instead of being "
            "told no translation covers them. No row was imported for the span: the decision "
            "was that those verses are not independently missing a translation, and they are "
            "not."
        ),
        "measured_at_closure": {
            "range_translations_in_the_span": 30,
            "canonical_verses_the_span_covers": 60,
            "verses_served_their_covering_unit": 30,
            "rows_imported_for_the_span": 0,
        },
    },
    "OWNER_DECISION_C_FORCED_ADDRESSES": {
        "resolution": "NARROWED_TO_THREE_WITHHELD",
        "basis": (
            "36 of the 39 Yajurvedic forced-address rows are imported, each independently "
            "verified against the printed source's own labels. Three are withheld by name "
            "and remain withheld unless new independent evidence appears. The decision is "
            "not closed because those three are a standing exception rather than a finished "
            "question."
        ),
        "approved": 36,
        "withheld": T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS,
    },
    "OWNER_DECISION_D_REUSED_RENDERING_POLICY": {
        "resolution": "CLOSED",
        "basis": (
            "194 reused renderings are imported with reuse_kind=REUSED_RENDERING, the source "
            "Veda, the source passage, the source translation's identity, the translator and "
            "the basis on which the text equivalence was established. None counts toward any "
            "corpus's independent English coverage, and the API, the reader, the "
            "cross-corpus comparison and Ask's evidence packet each disclose the reuse."
        ),
        "measured_at_closure": {"reused_renderings": 194, "SV": 173, "AV": 21},
    },
    "OWNER_DECISION_LATIN_SUBSTITUTION": {
        "resolution": "CLOSED_WITH_A_CORRECTED_POPULATION",
        "basis": (
            "The decision names 22 rows; the measured population is 24. AV 20.136.1 and "
            "RV 10.61.6 carry Latin literals and were classified source-explicit English. "
            "Both were verified against the pinned source pages -- sacred-texts heads its "
            "AV 20.136 page 'Erotica' and prints verses 1-16 in Latin -- and both are "
            "imported as language='la'. The decision's operative clause is that a Latin row "
            "must never increase English coverage, so it is applied to the measured "
            "population rather than to the quoted count."
        ),
        "measured_at_closure": {
            "owner_quoted": 22,
            "measured": 24,
            "language": "la",
            "counted_as_english": 0,
        },
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="update data/gap_registry.json")
    args = parser.parse_args()

    import gate_bc_common as G

    driver = G.driver()
    try:
        with G.session(driver) as session:
            measured = measure(session)
    finally:
        driver.close()

    decided = verdicts(measured)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.UTC).isoformat()

    changes = []
    for gap in registry["gaps"]:
        gap_id = gap["gap_id"]
        if gap_id not in measured:
            continue
        row = measured[gap_id]
        verdict = decided[gap_id]
        changes.append(
            {
                "gap_id": gap_id,
                "status_before": gap.get("status"),
                "status_after": verdict["status_now"],
                "current_count_before": gap.get("current_count"),
                "current_count_after": row["populations"]["dedicated_translation"],
                "missing_count_before": gap.get("missing_count"),
                "missing_count_after": row["verses_no_rendering_of_any_kind_reaches"],
                "reason": verdict["reason"],
            }
        )
        if args.write:
            gap["status"] = verdict["status_now"]
            gap["current_count"] = row["populations"]["dedicated_translation"]
            gap["missing_count"] = row["verses_no_rendering_of_any_kind_reaches"]
            gap["closure_measured_value"] = row["populations"]["dedicated_translation"]
            gap["closure_measured_at"] = now
            gap["translation_populations_measured"] = row["populations"]
            gap["closure_test_as_written_measured"] = row["closure_test_as_written"]
            gap["closure_condition_met"] = row["closure_condition_met"]
            gap["post_bulk_import_note"] = verdict["reason"]
            gap["owner_decisions_resolved"] = {
                name: body["resolution"]
                for name, body in OWNER_DECISION_UPDATES.items()
                if name
                in str(gap.get("closure_owner_decision") or "")
                + " OWNER_DECISION_D_REUSED_RENDERING_POLICY OWNER_DECISION_LATIN_SUBSTITUTION"
            }

    report = {
        "phase": "L",
        "measured_at": now,
        "rule_applied": (
            "a gap closes only when its own closure_test passes. Improved coverage is not "
            "closure, and the Samavedic case is why: 173 of its verses now show a rendering "
            "and none of them is the Samaveda's own translation."
        ),
        "measured": measured,
        "verdicts": decided,
        "changes": changes,
        "owner_decisions": OWNER_DECISION_UPDATES,
        "gaps_closed_this_round": [
            gap_id for gap_id, v in decided.items() if v["closed_this_round"]
        ],
        "gaps_remaining": [gap_id for gap_id, v in decided.items() if not v["closed_this_round"]],
        "registry_written": bool(args.write),
    }
    if args.write:
        registry["generated_at"] = now
        # indent=2 and CRLF, matching the file as it stands rather than this repository's
        # usual indent=1 and LF. Re-serialising it the other way rewrote all 4,453 lines,
        # which buries a four-entry change inside a whole-file diff nobody can review.
        REGISTRY.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\r\n",
        )
    T.write_json(T.INTEGRATION / "registry_remeasurement.json", report)

    for gap_id, row in measured.items():
        pops = row["populations"]
        print(f"{gap_id} ({row['veda']})")
        print(
            f"   corpus={row['corpus_mantras']:>6} dedicated={pops['dedicated_translation']:>6}"
            f" range={pops['range_covered']:>4} reused={pops['reused_rendering']:>4}"
            f" other_lang={pops['other_language']:>3} uncovered={pops['uncovered']:>5}"
        )
        print(
            f"   closure test as written: measured "
            f"{row['closure_test_as_written']['measured']}, demands 0, passes "
            f"{row['closure_test_as_written']['passes']}"
        )
        print(f"   closure condition met  : {row['closure_condition_met']}")
        print(f"   status -> {decided[gap_id]['status_now']}")
    print()
    print("closed this round :", report["gaps_closed_this_round"] or "none")
    print("remaining         :", report["gaps_remaining"])
    print()
    for name, body in OWNER_DECISION_UPDATES.items():
        print(f"{name}: {body['resolution']}")
    print()
    print("registry written:", args.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
