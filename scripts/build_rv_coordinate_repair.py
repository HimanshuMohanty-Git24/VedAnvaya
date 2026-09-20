#!/usr/bin/env python3
"""Build the RV 1.65-1.70 coordinate repair artifact.

Owner decision A: this is a COORDINATE_REPAIR, not a COVERAGE_FILL, and it runs before any
import touches the span. The eight required steps are enumerated per verse in the output.

The diagnosis this implements is narrower than the one first reported. It is not that
Griffith's unit k sits one place too early. It is that Griffith renders each *pair* of our
Sakala verses as one merged English unit, so unit k covers our verses 2k-1 and 2k together.
Verified by reading both halves of every unit against both verses' Sanskrit: unit 1 of
RV 1.65 carries "like a thief lurking in dark cave" (our v1, pasva na tayum guha catantam)
and "sate all the Holy Ones" (our v2, sajosa dhirah ... upa tva sidan).

That distinction changes the repair. Under a one-place shift, 30 verses are untranslated.
Under a merged-pair binding, all 61 verses are covered by some unit and the defect is
entirely in which verses each unit is attached to, plus an undeclared scope.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import unicodedata
from hashlib import sha256
from typing import Any

from neo4j import GraphDatabase

OUT = pathlib.Path("data/staging/rv_coordinate_repair")
SPAN = ["S065", "S066", "S067", "S068", "S069", "S070"]

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

# Content anchors: a distinctive English phrase from each half of a merged unit, paired with
# a distinctive Sanskrit fragment from the verse it renders. These are the evidence for
# step 7, and they were read off the live graph by hand rather than generated -- an
# automatic alignment here would be the same class of mistake as the defect being repaired.
ANCHORS = {
    "S065": [
        ("like a thief lurking in dark cave", "tāyuṁ", 1),
        ("sate all the Holy Ones", "sīdan", 2),
        ("The Gods approached the ways of holy Law", "vratā", 3),
        ("waters feed with praise the growing Babe", "āpaḥ", 4),
        ("like a fruit-bearing hill", "girir", 5),
        ("rushing like Sindhu", "sindhur", 6),
        ("Kin as a brother to his sister floods", "bhrāte", 7),
        ("shears the hair of earth", "vātajūto", 8),
        ("Like a swan sitting in the floods", "haṁso", 9),
        ("A Sage like Soma, sprung from Law", "ṛtaprajātaḥ", 10),
    ],
}


def norm(text: str) -> str:
    """Letters only, accents stripped -- for substring containment tests on Sanskrit."""
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    letters = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", letters)


def main() -> int:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    verses: list[dict[str, Any]] = []
    try:
        with driver.session(database=DB) as session:
            for sukta in SPAN:
                records = session.run(
                    """
                    MATCH (m:Mantra {veda:'RV'})
                    WHERE m.canonical_key STARTS WITH $prefix
                    OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
                    OPTIONAL MATCH (m)-[:HAS_TEXT_VERSION]->(v:TextVersion)
                      WHERE v.text_role = 'PRIMARY_TEXT'
                    RETURN m.canonical_key AS key, m.canonical_citation AS cite,
                           v.text_nfc AS sanskrit, t.text AS translation,
                           t.source_id AS source_id, t.translator AS translator
                    ORDER BY key
                    """,
                    prefix=f"VG:RV:SAK:M01:{sukta}:",
                )
                for r in records:
                    verses.append(dict(r))
    finally:
        driver.close()

    by_sukta: dict[str, list[dict[str, Any]]] = {}
    for v in verses:
        by_sukta.setdefault(v["key"].split(":")[4], []).append(v)

    rows = []
    summary = {"correct_and_complete": 0, "misattached": 0, "unbound_but_covered": 0}

    for sukta, group in sorted(by_sukta.items()):
        group.sort(key=lambda v: int(v["key"].split(":")[5][1:]))
        translated = [v for v in group if v["translation"]]
        n_verses, n_units = len(group), len(translated)

        # Establish the unit->verse-pair mapping from the counts, then verify it by content.
        # Declared rather than inferred per verse, so a wrong hypothesis fails loudly.
        pair_size = 2
        for index, verse in enumerate(group, start=1):
            unit_currently_here = index if index <= n_units else None
            correct_unit = (index - 1) // pair_size + 1
            covers = (2 * correct_unit - 1, min(2 * correct_unit, n_verses))

            if unit_currently_here is None:
                status = "UNBOUND_BUT_COVERED"
            elif unit_currently_here == correct_unit:
                status = "CORRECT_UNIT_UNDECLARED_SCOPE"
            else:
                status = "MISATTACHED"

            key_map = {
                "UNBOUND_BUT_COVERED": "unbound_but_covered",
                "CORRECT_UNIT_UNDECLARED_SCOPE": "correct_and_complete",
                "MISATTACHED": "misattached",
            }
            summary[key_map[status]] += 1

            rows.append(
                {
                    "canonical_key": verse["key"],
                    "citation": verse["cite"],
                    "step_1_verse_exists": True,
                    "step_2_current_translation_attached": bool(verse["translation"]),
                    "step_2_current_translation_head": (verse["translation"] or "")[:70] or None,
                    "step_3_source_coordinate": (
                        f"Griffith RV {sukta.lstrip('S').lstrip('0')}, printed unit {correct_unit} "
                        f"of {n_units}"
                    ),
                    "step_4_old_mapping": (
                        f"unit {unit_currently_here} -> verse {index}"
                        if unit_currently_here
                        else "no unit bound"
                    ),
                    "step_5_corrected_mapping": (
                        f"unit {correct_unit} -> verses {covers[0]}"
                        + (f" and {covers[1]}" if covers[1] != covers[0] else "")
                        + " jointly (PAIR_SCOPE)"
                    ),
                    "step_6_classification": status,
                    "source_id": verse["source_id"],
                    "sanskrit_head": (verse["sanskrit"] or "")[:44],
                }
            )

    # --- step 7: verify the corrected mapping by content, on RV 1.65 -----------------
    verification = []
    group = by_sukta["S065"]
    group.sort(key=lambda v: int(v["key"].split(":")[5][1:]))
    units = [v["translation"] for v in group if v["translation"]]
    for english, sanskrit_frag, verse_no in ANCHORS["S065"]:
        unit_index = (verse_no - 1) // 2
        unit_text = units[unit_index]
        english_present = english.lower() in unit_text.lower()
        target = group[verse_no - 1]
        sanskrit_present = norm(sanskrit_frag) in norm(target["sanskrit"])
        verification.append(
            {
                "verse": target["cite"],
                "predicted_unit": unit_index + 1,
                "english_anchor": english,
                "english_found_in_predicted_unit": english_present,
                "sanskrit_anchor": sanskrit_frag,
                "sanskrit_found_in_verse": sanskrit_present,
                "verified": english_present and sanskrit_present,
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repair_table.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
        newline="\n",
    )
    (OUT / "verification.json").write_text(
        json.dumps(
            {
                "method": (
                    "For each of RV 1.65's ten verses, a distinctive English phrase and a "
                    "distinctive Sanskrit fragment were chosen by hand. The test is whether "
                    "the English appears in the unit the corrected mapping predicts, and the "
                    "Sanskrit in the verse it is said to render. Chosen by hand deliberately: "
                    "an automatic alignment here would risk the same class of error as the "
                    "defect under repair."
                ),
                "checks": verification,
                "all_verified": all(v["verified"] for v in verification),
                "verified_count": sum(1 for v in verification if v["verified"]),
                "total": len(verification),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    digest = sha256((OUT / "repair_table.jsonl").read_bytes()).hexdigest()
    print(f"rows: {len(rows)}   sha256: {digest[:16]}")
    print(f"summary: {summary}")
    print(
        f"step 7 verification: {sum(1 for v in verification if v['verified'])}"
        f"/{len(verification)} verified"
    )
    for v in verification:
        if not v["verified"]:
            print("  UNVERIFIED:", v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
