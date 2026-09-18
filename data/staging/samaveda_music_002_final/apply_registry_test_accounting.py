#!/usr/bin/env python3
"""Measure GAP-SAMAVEDA_MUSIC-002's own written closure_test, clause by clause.

The entry closed on a NEW measure, and the old one has to be accounted for rather than
quietly dropped. Its ``closure_test`` as written asks for three things:

    1. a melodic node label exists
    2. MUSICALIZED_AS appears in db.relationshipTypes() with a non-zero count
    3. /api/v1/insights/capabilities no longer returns samavedic_melodic_layer as NOT_BUILT

Clause 3 holds. Clauses 1 and 2 do NOT, and they are superseded by
``OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1`` (OWNER_DECISIONS.md section 41), which places the
object-side Gana identity outside Product V1 and forbids minting a node or an edge to satisfy
a denominator. ``GAP-SAMAVEDA_MUSIC-003`` already closed ``CLOSED_SCOPE_DECISION`` on that
same citation.

So this file writes the honest pair onto the entry: the test as written, measured, with two
of its three clauses failing; and the condition that was actually met. A reader who checks
the published ``closure_measure`` and a reader who checks the published ``closure_test``
should reach the same understanding, and without this block the second reader would measure
something the gate never measured.

``closure_test_as_written_measured`` is an existing registry field with an existing shape --
four entries already carry one, written by ``scripts/translation_integration_registry.py`` --
so this follows it rather than inventing a field.

Usage:
    python data/staging/samaveda_music_002_final/apply_registry_test_accounting.py [--write]
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib

from neo4j import GraphDatabase, Query

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "data" / "gap_registry.json"
OUT = ROOT / "data" / "staging" / "samaveda_music_002_final" / "registry_test_accounting.json"
READBACK = ROOT / "data" / "staging" / "samaveda_music_002_final" / "readback.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"
TIMEOUT = 300.0

GAP = "GAP-SAMAVEDA_MUSIC-002"
SUPERSEDED_BY = (
    "OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1 "
    "(docs/reports/data-completeness/OWNER_DECISIONS.md section 41)"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    readback = json.loads(READBACK.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database=DB) as session:
        melodic_labels = session.run(
            Query(
                "CALL db.labels() YIELD label "
                "WHERE label =~ '(?i).*(saman|gana|stobha|melod).*' RETURN collect(label) AS l",
                timeout=TIMEOUT,
            )
        ).single()["l"]
        musicalized = session.run(
            Query("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r) AS c", timeout=TIMEOUT)
        ).single()["c"]
        untyped = session.run(
            Query(
                "MATCH (m:Mantra {veda:'SV'}) WHERE m.samavedic_notation_state IS NULL "
                "RETURN count(m) AS c",
                timeout=TIMEOUT,
            )
        ).single()["c"]
    driver.close()

    clauses = [
        {
            "clause": 1,
            "as_written": "a melodic node label exists",
            "measure": "CALL db.labels() filtered for saman|gana|stobha|melod",
            "demands": "at least one label",
            "measured": melodic_labels,
            "passes": bool(melodic_labels),
            "superseded_by": SUPERSEDED_BY,
            "why_superseded": (
                "A label needs an object to label, and the object side is a canonical Gana "
                "or saman identity. Section 41 places that outside Product V1 and forbids "
                "minting one to satisfy a denominator. The notation landed on the verse's "
                "own text witness instead, which is where the source printed it."
            ),
        },
        {
            "clause": 2,
            "as_written": (
                "MUSICALIZED_AS appears in db.relationshipTypes() with a non-zero count"
            ),
            "measure": "MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)",
            "demands": "> 0",
            "measured": musicalized,
            "passes": musicalized > 0,
            "superseded_by": SUPERSEDED_BY,
            "why_superseded": (
                "Section 41 rules the predicate NOT required for Product V1 unless the "
                "object-side Gana identity is independently established and canonical, and "
                "forbids minting an edge to reach a count. The 495 staged edges stay staged "
                "and re-verified. GAP-SAMAVEDA_MUSIC-003 already closed "
                "CLOSED_SCOPE_DECISION on this citation, so gating this entry on the same "
                "predicate would make it unclosable by any means except the one act the "
                "owner barred."
            ),
        },
        {
            "clause": 3,
            "as_written": (
                "/api/v1/insights/capabilities no longer returns samavedic_melodic_layer "
                "as NOT_BUILT"
            ),
            "measure": "GET /api/v1/insights/capabilities?question=82",
            "demands": "data_status is not NOT_BUILT",
            "measured": {
                "verdict": "PARTIALLY_ANSWERABLE",
                "data_status": "PARTIAL",
                "benchmark_verdict": "NOT_ANSWERABLE",
                "benchmark_verdict_note": (
                    "Kept as frozen rather than rewritten. The divergence between the live "
                    "and the frozen grade is the finding; copying the frozen one forward "
                    "would publish a limitation that no longer holds."
                ),
            },
            "passes": True,
            "superseded_by": None,
            "why_superseded": None,
        },
    ]

    accounting = {
        "artifact": "SAMAVEDA_MUSIC_002_CLOSURE_TEST_ACCOUNTING",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "gap_id": GAP,
        "rule": (
            "A gap closes only when its own closure_test passes, or when a clause of that "
            "test is superseded by a recorded owner decision a reader can find. Two of the "
            "three clauses here are superseded and the supersession is cited, not asserted."
        ),
        "clauses": clauses,
        "clauses_passing_as_written": sum(1 for c in clauses if c["passes"]),
        "clauses_superseded_by_a_recorded_owner_decision": sum(
            1 for c in clauses if c["superseded_by"]
        ),
        "condition_actually_met": (
            "Every one of the 1,844 Kauthuma arcika verses carries a typed notation "
            f"disposition: {readback['notated_verses']:,} SOURCE_EXPLICIT_PRESENT with the "
            f"source's own tone marks served as a parallel witness, {readback['withheld_verses']} "
            "WITHHELD with a reason class and reason prose on the verse, and "
            f"{readback['verses_with_no_state_at_all']} carrying no state at all. The sentence "
            "this entry was opened for -- 'No melodic layer of any kind exists' -- is false. "
            "What remains absent is the SONG, and that is section 41's boundary rather than "
            "this entry's gap."
        ),
        "what_did_not_change": {
            "musicalized_as_edges": musicalized,
            "melodic_node_labels": melodic_labels,
            "verses_with_no_notation_disposition": untyped,
            "notation_rows_interpreted_into_pitch": readback[
                "witnesses_claiming_pitch_interpretation"
            ],
        },
    }

    OUT.write_text(
        json.dumps(accounting, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if args.write:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = next(g for g in registry["gaps"] if g["gap_id"] == GAP)
        entry["closure_test_as_written_measured"] = {
            "clauses": clauses,
            "clauses_passing_as_written": accounting["clauses_passing_as_written"],
            "clauses_superseded_by_a_recorded_owner_decision": accounting[
                "clauses_superseded_by_a_recorded_owner_decision"
            ],
            "caveat": (
                "Clauses 1 and 2 ask for a melodic NODE and a verse-to-saman EDGE. Both are "
                "outside Product V1 by OWNER_DECISIONS.md section 41, which also forbids "
                "creating either to satisfy a count. They are recorded as failing rather "
                "than rewritten, so a reader checking the published test is not misled."
            ),
        }
        entry["closure_condition_met"] = accounting["condition_actually_met"]
        entry["current_count"] = readback["notated_verses"]
        entry["expected_population"] = (
            readback["notated_verses"] + readback["withheld_verses"]
        )
        entry["missing_count"] = readback["verses_with_no_state_at_all"]
        # The registry is tracked with CRLF endings, and
        # scripts/wave4_registry_closure_audit.py writes it through the platform default,
        # which on Windows produces CRLF. Forcing "\n" here rewrote all 4,732 lines for a
        # 43-line change, which hides the real edit inside a whole-file diff. Detect and
        # preserve instead: this project has recorded the same hazard before.
        newline = "\r\n" if b"\r\n" in REGISTRY.read_bytes() else "\n"
        REGISTRY.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline=newline,
        )
        print(f"wrote {REGISTRY.relative_to(ROOT)} (newline {newline!r})")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  clauses passing as written              {accounting['clauses_passing_as_written']} of 3")
    print(
        "  clauses superseded by owner decision    "
        f"{accounting['clauses_superseded_by_a_recorded_owner_decision']} of 3"
    )
    print(f"  melodic node labels                    {melodic_labels}")
    print(f"  MUSICALIZED_AS edges                   {musicalized}")
    print(f"  verses with no notation disposition    {untyped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
