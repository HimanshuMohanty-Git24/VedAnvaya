#!/usr/bin/env python3
"""Owner sections 4, 5 and 6: give the registry a typed, testable account of causation.

Three problems this fixes, all of which let the campaign act on a guess.

**Free-text causes.** Every one of the 80 entries carries a prose `source_dependency`, and
several bury the word "NONE" inside a paragraph. Nothing can filter on that, so "which gaps
actually need an external source?" was unanswerable without reading all eighty.

**Hypothesis passing as cause.** `root_cause` was written when the gap was registered, from
inspection rather than measurement, and three of those hypotheses sent the campaign to
acquire material it already held. An entry now has to say whether its cause was *measured*.

**No addressing-first discipline.** Five findings share one shape: an apparent source
absence that was our own addressing defect. So a gap may not be classified as
source-missing until the addressing checks have actually been run, and the checklist is
stored per entry with each check's state rather than asserted in prose.

Every original `root_cause` is preserved as `initial_hypothesis`. A disproven one is marked
`DISPROVEN` and kept. A campaign that quietly rewrites its wrong guesses cannot learn which
kind it gets wrong.

Usage:
    python scripts/migrate_gap_registry_causation.py [--check]

    --check  verify the registry already conforms; write nothing. Exit 1 if it does not.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

REGISTRY = pathlib.Path("data/gap_registry.json")

#: Closed taxonomy of measured root causes (owner section 6). Free text may accompany a
#: type; it may not replace one.
ROOT_CAUSE_TYPES = (
    "SOURCE_TRULY_ABSENT",
    "SOURCE_NOT_YET_DISCOVERED",
    "WRONG_SOURCE_COORDINATE",
    "CANONICAL_COORDINATE_DEFECT",
    "TRANSLITERATION_MISMATCH",
    "UNICODE_NORMALIZATION_DEFECT",
    "OCR_LABEL_DEFECT",
    "COMPARATOR_DEFECT",
    "SORT_ORDER_DEFECT",
    "GRANULARITY_MISMATCH",
    "RECENSION_MISMATCH",
    "SCOPE_MISMATCH",
    "UNAPPLIED_EXISTING_TRANSFORM",
    "SCHEMA_CANNOT_REPRESENT_DOMAIN",
    "VALIDATOR_FALSE_COMPLETENESS",
    "PIPELINE_NOT_RUN",
    "DERIVED_LAYER_NOT_BUILT",
    "PRODUCT_PROJECTION_MISSING",
    "OTHER_MEASURED",
)

SOURCE_AVAILABILITY = (
    "UNDIAGNOSED",
    "NOT_REQUIRED",
    "HELD_LOCALLY",
    "PUBLICLY_REACHABLE",
    "REACHABLE_WITH_PERMISSION",
    "UNREACHABLE_FROM_HERE",
    "NOT_LOCATED",
    "CONFIRMED_ABSENT",
)

#: Owner section 4. A gap may not be called source-missing until these have been run. Stored
#: per entry with each check's state so the claim is inspectable rather than asserted.
ADDRESSING_CHECKS = {
    "A_canonical_key_correctness": "our own key is the key we think it is",
    "B_source_coordinate_system": "the source addresses its text the way we assume",
    "C_edition_numbering": "the edition does not divide or merge units differently",
    "D_recension_identity": "the material is the school we hold, not a sibling",
    "E_transliteration_script": "both sides are in the script we are comparing in",
    "F_unicode_normalization": "composed and decomposed forms are folded alike",
    "G_accent_normalization": "tone marks are not mistaken for letters, or vice versa",
    "H_ocr_digit_confusion": "printed labels were read correctly",
    "I_sort_order": "ordering is numeric where we assume numeric, and symmetric where declared",
    "J_comparator_behaviour": "the comparator measures what it claims to",
    "K_sandhi_word_boundary": "segmentation convention is not read as a textual difference",
    "L_granularity": "the source's unit is the unit we are attaching to",
    "M_scope": "the work or section boundary is the one we assume",
    "N_stale_transform": "an existing mapping table is applied, and applied correctly",
}

#: The eleven entries whose causation was measured in waves 1 and 2, typed against the
#: taxonomy. Each `diagnostics` entry names the checks that actually ran for that gap.
MEASURED: dict[str, dict[str, Any]] = {
    "GAP-AUDIO-001": {
        "type": ["GRANULARITY_MISMATCH", "RECENSION_MISMATCH"],
        "availability": "PUBLICLY_REACHABLE",
        "diagnostics": ["D_recension_identity", "L_granularity", "M_scope"],
        "note": (
            "475 licence-clean recordings exist and are now fetched, but every one is "
            "page-level and they are gana performances rather than arcika recitation. The "
            "LOAR deposit adds a Jaiminiya arcika, which is the wrong recension. So the "
            "material is reachable and the gap is not closable from it."
        ),
    },
    "GAP-AUDIO-002": {
        "type": ["WRONG_SOURCE_COORDINATE"],
        "availability": "PUBLICLY_REACHABLE",
        "diagnostics": [
            "A_canonical_key_correctness",
            "B_source_coordinate_system",
            "C_edition_numbering",
            "J_comparator_behaviour",
        ],
        "note": (
            "VedSearch divides the Atharvaveda into 754 suktas where our Berlin division "
            "has 731. Keys were mapped straight through, so past the first split in a kanda "
            "the coordinate addressed the wrong verse. The refusals were right and the "
            "address was wrong."
        ),
    },
    "GAP-AUDIO-003": {
        "type": ["COMPARATOR_DEFECT", "GRANULARITY_MISMATCH"],
        "availability": "REACHABLE_WITH_PERMISSION",
        "diagnostics": [
            "J_comparator_behaviour",
            "F_unicode_normalization",
            "G_accent_normalization",
            "L_granularity",
        ],
        "note": (
            "For 33 verses, difflib autojunk discarded nearly the whole alphabet and a "
            "colon-spelled visarga was dropped as a non-letter. For the remaining 190, "
            "Madhyandina recitation is published per adhyaya -- IGNCA under permission, and "
            "LOAR under CC0 at multi-chapter granularity -- so the blocker is granularity "
            "and rights, not availability."
        ),
    },
    "GAP-AUDIO-004": {
        "type": ["SCOPE_MISMATCH", "SOURCE_NOT_YET_DISCOVERED"],
        "availability": "PUBLICLY_REACHABLE",
        "diagnostics": ["B_source_coordinate_system", "M_scope", "N_stale_transform"],
        "note": (
            "The incumbent source publishes the 1,017-hymn presentation, so the "
            "transform's target 8.93 never existed there. The registry had recorded this as "
            "an unapplied transform; the transform is applied and correct. A different "
            "source covers all 10,552 per stanza."
        ),
    },
    "GAP-TRANSLATION-002": {
        "type": ["SOURCE_NOT_YET_DISCOVERED"],
        "availability": "PUBLICLY_REACHABLE",
        "diagnostics": ["M_scope", "D_recension_identity"],
        "note": (
            "Both incumbent sources omit kanda 20 for the same Whitney-related reason, so "
            "it was one source dependency rather than 961 absences. Closed via the Wayback "
            "Machine, sacred-texts.com being behind a Cloudflare challenge."
        ),
    },
    "GAP-TRANSLATION-003": {
        "type": ["OCR_LABEL_DEFECT"],
        "availability": "HELD_LOCALLY",
        "diagnostics": [
            "H_ocr_digit_confusion",
            "A_canonical_key_correctness",
            "C_edition_numbering",
        ],
        "note": (
            "39 of the 72 gap labels were digit-confusion OCR of printed verse numbers, with "
            "the translated text present throughout. Never a source gap."
        ),
    },
    "GAP-TRANSLATION-004": {
        "type": ["CANONICAL_COORDINATE_DEFECT", "GRANULARITY_MISMATCH"],
        "availability": "HELD_LOCALLY",
        "diagnostics": ["A_canonical_key_correctness", "C_edition_numbering", "L_granularity"],
        "note": (
            "Griffith renders each pair of our Sakala verses as one merged unit, so unit k "
            "covers verses 2k-1 and 2k. The import bound unit k to verse k. 30 of the 50 "
            "were never a source gap; they are the unbound halves of a pair-scope rendering."
        ),
    },
    "GAP-TRANSLATION-006": {
        "type": ["CANONICAL_COORDINATE_DEFECT", "GRANULARITY_MISMATCH"],
        "availability": "NOT_REQUIRED",
        "diagnostics": ["A_canonical_key_correctness", "C_edition_numbering", "L_granularity"],
        "note": (
            "25 of 31 shipped translations in RV 1.65-1.70 sit on the wrong verse, and the "
            "scope of the remaining 6 is undeclared. Nothing needs acquiring: all 61 verses "
            "are covered by some unit."
        ),
    },
    "GAP-OTHER-006": {
        "type": ["COMPARATOR_DEFECT", "UNICODE_NORMALIZATION_DEFECT"],
        "availability": "NOT_REQUIRED",
        "diagnostics": [
            "J_comparator_behaviour",
            "F_unicode_normalization",
            "G_accent_normalization",
        ],
        "note": (
            "autojunk discarded 17 of 18 distinct letters on a 285-character skeleton, and "
            "the published calibration had been measured with that comparator. Fixed at "
            "30ba692 and recalibrated over 12,000 mispaired pairs."
        ),
    },
    "GAP-FORMULA-002": {
        "type": ["DERIVED_LAYER_NOT_BUILT", "UNAPPLIED_EXISTING_TRANSFORM"],
        "availability": "NOT_REQUIRED",
        "diagnostics": ["N_stale_transform", "J_comparator_behaviour"],
        "note": (
            "Two things under one id. The USES_FORMULA half was recoverable from its own "
            "evidence surface all along; the parallel typology half was genuinely unbuilt "
            "and 4,368 backfills close it. The entry's closure test is false by design for "
            "edges identical at no level."
        ),
    },
    "GAP-CROSS_VEDA-003": {
        "type": ["UNAPPLIED_EXISTING_TRANSFORM"],
        "availability": "NOT_REQUIRED",
        "diagnostics": ["N_stale_transform", "A_canonical_key_correctness"],
        "note": (
            "A name collision, not an absence. The 256 edges lacking parallel_id are the "
            "same 256 with a null match_level and they already carry strongest_method. "
            "Backfill by mapping the existing property, not by re-deriving."
        ),
    },
    "GAP-COMMUNITIES-001": {
        "type": ["DERIVED_LAYER_NOT_BUILT"],
        "availability": "NOT_REQUIRED",
        "diagnostics": ["A_canonical_key_correctness", "L_granularity", "M_scope"],
        "note": (
            "Built, then refused for publication on evidence. The projection premise in the "
            "brief was wrong twice: within-mantra co-dedication is 6 edges, and the "
            "projection is Rigveda-only because HAS_DEVATA_ASCRIPTION targets 324 "
            ":DevataAscription nodes of which none is a :Devata."
        ),
    },
    "GAP-COMMUNITIES-002": {
        "type": ["OTHER_MEASURED"],
        "availability": "NOT_REQUIRED",
        "diagnostics": ["A_canonical_key_correctness"],
        "note": (
            "Real as a gap and false as a blocker: 59 of 71 composite labels were placed "
            "without decomposition, so it constrains interpretation rather than gating "
            "computation."
        ),
    },
}


def migrate(registry: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    registry["root_cause_taxonomy"] = list(ROOT_CAUSE_TYPES)
    registry["source_availability_vocabulary"] = list(SOURCE_AVAILABILITY)
    registry["addressing_checks"] = ADDRESSING_CHECKS
    registry["addressing_first_rule"] = (
        "A gap may not be classified SOURCE_TRULY_ABSENT, NOT_LOCATED or "
        "CONFIRMED_ABSENT until every applicable addressing check in "
        "`addressing_checks` has been run and recorded in the entry's "
        "`diagnostics_run`. Five campaign findings were an apparent source absence "
        "that turned out to be our own addressing defect; three registry "
        "prescriptions sent the campaign to acquire material it already held."
    )

    for gap in registry["gaps"]:
        gid = gap["gap_id"]

        gap.setdefault("observed_gap", gap.get("description", ""))
        if "initial_hypothesis" not in gap:
            gap["initial_hypothesis"] = gap.get("suspected_cause") or gap.get("root_cause", "")

        measured = MEASURED.get(gid)
        ran = set(measured["diagnostics"]) if measured else set()
        gap["diagnostics_run"] = {
            name: ("RUN" if name in ran else "NOT_RUN") for name in ADDRESSING_CHECKS
        }

        if measured:
            gap["measured_root_cause"] = {
                "types": measured["type"],
                "explanation": measured["note"],
            }
            gap["source_availability"] = measured["availability"]
            gap["causation_status"] = "MEASURED"
            if "disproven_prescription" in gap:
                gap["initial_hypothesis_status"] = "DISPROVEN"
            else:
                gap["initial_hypothesis_status"] = "SUPERSEDED_BY_MEASUREMENT"
            changes.append(f"{gid}: typed {'+'.join(measured['type'])}")
        else:
            gap["measured_root_cause"] = None
            gap["source_availability"] = "UNDIAGNOSED"
            gap["causation_status"] = "HYPOTHESIS_NOT_YET_MEASURED"
            gap["initial_hypothesis_status"] = "UNTESTED"

        gap.setdefault("closure_method", None)

    registry["gaps"].sort(key=lambda g: str(g["gap_id"]))
    return changes


def verify(registry: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if registry.get("root_cause_taxonomy") != list(ROOT_CAUSE_TYPES):
        failures.append("root_cause_taxonomy missing or altered")

    for gap in registry["gaps"]:
        gid = gap["gap_id"]
        for field in (
            "observed_gap",
            "initial_hypothesis",
            "diagnostics_run",
            "measured_root_cause",
            "source_availability",
            "closure_method",
            "causation_status",
            "initial_hypothesis_status",
        ):
            if field not in gap:
                failures.append(f"{gid}: missing {field}")

        if gap.get("source_availability") not in SOURCE_AVAILABILITY:
            failures.append(
                f"{gid}: source_availability {gap.get('source_availability')!r} not in vocabulary"
            )

        measured = gap.get("measured_root_cause")
        if measured is not None:
            for kind in measured.get("types", []):
                if kind not in ROOT_CAUSE_TYPES:
                    failures.append(f"{gid}: root cause {kind!r} not in taxonomy")
            if not measured.get("explanation"):
                failures.append(f"{gid}: typed root cause with no explanation")
        elif gap.get("causation_status") == "MEASURED":
            failures.append(f"{gid}: claims MEASURED with no measured_root_cause")

        # The addressing-first rule, enforced rather than described.
        absent_claims = {"SOURCE_TRULY_ABSENT", "NOT_LOCATED", "CONFIRMED_ABSENT"}
        claims_absent = gap.get("source_availability") in absent_claims or (
            measured and absent_claims & set(measured.get("types", []))
        )
        if claims_absent:
            never_run = [k for k, v in (gap.get("diagnostics_run") or {}).items() if v == "NOT_RUN"]
            if never_run:
                failures.append(
                    f"{gid}: claims source absence with {len(never_run)} addressing check(s) "
                    f"never run"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only, write nothing")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    if args.check:
        failures = verify(registry)
        print()
        if failures:
            for failure in failures[:30]:
                print(f"  [FAIL] {failure}")
            if len(failures) > 30:
                print(f"  ...and {len(failures) - 30} more")
            print(f"\n  {len(failures)} conformance failure(s).\n")
            return 1
        print(f"  PASS. {len(registry['gaps'])} entries conform to the causation schema.\n")
        return 0

    before = len(registry["gaps"])
    changes = migrate(registry)
    assert len(registry["gaps"]) == before, "migration changed the gap count"

    failures = verify(registry)
    if failures:
        print("REFUSING to write: the migration does not satisfy its own verifier")
        for failure in failures[:20]:
            print(f"  {failure}")
        return 1

    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    measured = sum(1 for g in registry["gaps"] if g["causation_status"] == "MEASURED")
    disproven = sum(1 for g in registry["gaps"] if g["initial_hypothesis_status"] == "DISPROVEN")
    print(f"\n  migrated {before} entries")
    print(f"  causation MEASURED              : {measured}")
    print(f"  hypothesis DISPROVEN            : {disproven}")
    print(f"  hypothesis UNTESTED             : {before - measured}")
    print(f"  taxonomy types                  : {len(ROOT_CAUSE_TYPES)}")
    print(f"  addressing checks per entry     : {len(ADDRESSING_CHECKS)}")
    print()
    for change in changes:
        print(f"    {change}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
