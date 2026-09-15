#!/usr/bin/env python3
"""Owner section 13: which dependent artifacts did Wave 3 invalidate, and which it did not.

The owner's instruction is to rebuild every dependent artifact whose inputs changed, and at
minimum to *inspect* dependency invalidation for nine named consumers. This does the
inspection, and it does it by measurement rather than by reasoning about what probably
moved: every element Wave 3 wrote carries a ``wave`` stamp, so "did this artifact's inputs
change" is a query about labels and predicates rather than a judgement.

WHY A STALENESS REPORT AND NOT A REBUILD SCRIPT
===============================================

Rebuilding is not uniform work. Three of the nine consumers read the graph directly and can
be regenerated in minutes; three are derived layers with their own gates and evaluation
sets; two are product projections whose figures are published, so regenerating them changes
what a reader sees; and one -- semantic resemblance -- the owner has explicitly ruled is a
re-derivation from the post-import snapshot rather than a refresh.

A single "rebuild everything" would therefore either skip the hard ones silently or publish
the projections without the gate. So this reports, per consumer, whether its inputs moved,
by how much, what rebuilds it, and what that rebuild costs. The decision to run each stays
where it belongs.

WHAT COUNTS AS AN INPUT CHANGING
================================

A label or predicate this wave created or wrote onto. That includes a property backfill: an
artifact that read ``USES_FORMULA`` before the match levels landed was computed over edges
that now say more than they did, and a reader cannot tell from the artifact which version
it saw. Counting only new elements would call those artifacts current when they are not.

Usage:
    python scripts/wave3_dependency_invalidation.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

INTEGRATION = pathlib.Path("data/staging/integration")
RECEIPT = INTEGRATION / "wave3_import_receipt.json"
OUT = INTEGRATION / "wave3_dependency_invalidation.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

WAVE = "WAVE_3"


#: The nine consumers the owner names, each with the graph elements it reads, what rebuilds
#: it, and what rebuilding costs. ``reads`` is deliberately the element types rather than a
#: file list: the question is whether the GRAPH moved under the artifact.
CONSUMERS: tuple[dict[str, Any], ...] = (
    {
        "consumer": "semantic resemblance",
        "reads_labels": ("Passage", "Mantra", "Translation", "SemanticAssertion", "RoleFiller"),
        "reads_types": ("HAS_TRANSLATION", "ASSERTION_ROLE", "REFERS_TO", "USES_FORMULA"),
        "rebuilt_by": "the domain's own pipeline, from the post-import snapshot",
        "owner_ruling": (
            "Section 8: re-derive from the post-import snapshot. Not a refresh -- the "
            "predicate stays defined on the translation-free channels and its declared "
            "limits carry over. Tier B stays refused until the Devata bridge exists."
        ),
        "cost": "the full candidate pool; the layer's own gates and adjudication set apply",
    },
    {
        "consumer": "cross-Veda matrices",
        "reads_labels": ("Passage", "Mantra"),
        "reads_types": (
            "EXACT_PARALLEL_OF",
            "VARIANT_OF",
            "NEAR_PARALLEL_OF",
            "REUSES_TEXT_FROM",
        ),
        "rebuilt_by": "vedagraph.enrich.crossveda over the canonical corpora",
        "owner_ruling": None,
        "cost": "about four minutes over all 20,210 mantras",
    },
    {
        "consumer": "formula / parallel / variant relations",
        "reads_labels": ("Formula", "FormulaFamily", "Passage"),
        "reads_types": ("USES_FORMULA", "HAS_FORMULA", "SHARES_FORMULA_WITH", "MEMBER_OF_FAMILY"),
        "rebuilt_by": "scripts/build_formula_families.py",
        "owner_ruling": None,
        "cost": "minutes; its byte-identical rebuild test pins the output",
    },
    {
        "consumer": "entity coverage",
        "reads_labels": ("Devata", "Concept", "DomainEntity", "Rishi", "Chandas"),
        "reads_types": ("MENTIONS_ENTITY", "ABOUT_CONCEPT", "HAS_DEVATA", "MENTIONS_DEVATA"),
        "rebuilt_by": "scripts/build_veda_coverage_and_metrics.py",
        "owner_ruling": (
            "Coverage figures must come from canonical readback, not staging manifests "
            "(section 12)."
        ),
        "cost": "minutes, reads the graph directly",
    },
    {
        "consumer": "ritual aggregates",
        "reads_labels": ("Ritual", "RitualStep", "RitualRole", "Offering", "Action"),
        "reads_types": (
            "HAS_RITUAL_STEP",
            "PERFORMED_BY",
            "USES_OBJECT",
            "USES_OFFERING",
            "USES_SUBSTANCE",
            "RITE_INVOLVES_ACTION",
            "ATTESTED_IN",
        ),
        "rebuilt_by": "no aggregate exists yet -- this layer is new in Wave 3",
        "owner_ruling": None,
        "cost": "n/a: nothing to invalidate, and nothing consumes it yet",
    },
    {
        "consumer": "quality evaluation",
        "reads_labels": ("QualityVerdict", "QAIssue", "Passage"),
        "reads_types": ("QUALITY_VERDICT_ABOUT", "QA_ISSUE_ON"),
        "rebuilt_by": "scripts/graph_quality_scorecard.py",
        "owner_ruling": None,
        "cost": "cheap, and the scorecard's own docstring says re-running is the only way "
        "it stays honest",
    },
    {
        "consumer": "Ask retrieval",
        "reads_labels": ("Passage", "Mantra", "Translation", "Devata", "Concept"),
        "reads_types": ("MENTIONS_ENTITY", "ABOUT_CONCEPT", "HAS_TRANSLATION", "HAS_DEVATA"),
        "rebuilt_by": "the search index build, then scripts/run_ask_benchmark.py to re-grade",
        "owner_ruling": None,
        "cost": "the index is cheap; re-grading the benchmark spends LLM quota, and a "
        "daily quota is burned by retrying it",
    },
    {
        "consumer": "Visualization Lab aggregates",
        "reads_labels": ("Devata", "Concept", "Passage", "DerivedMetric"),
        "reads_types": ("MENTIONS_ENTITY", "ABOUT_CONCEPT", "CO_OCCURS_WITH", "HAS_DEVATA"),
        "rebuilt_by": "scripts/export_graph_world.py and the metrics build",
        "owner_ruling": "Do not regenerate the frontend design (section 13).",
        "cost": "minutes; publishes to a reader-facing surface, so it follows the gate",
    },
    {
        "consumer": "Knowledge World public projection",
        "reads_labels": ("Devata", "Concept", "DomainEntity", "Passage"),
        "reads_types": ("MENTIONS_ENTITY", "ABOUT_CONCEPT", "SPECIALIZED_FORM_OF"),
        "rebuilt_by": "scripts/export_graph_world.py",
        "owner_ruling": (
            "A staged figure may not reach a public surface before canonical readback "
            "(section F, carried into Wave 3)."
        ),
        "cost": "minutes; public, so it follows the gate",
    },
)


def touched(session: Session) -> tuple[dict[str, int], dict[str, int]]:
    """Labels and predicates Wave 3 wrote to, with how many elements each."""
    labels = {
        record["label"]: int(record["c"])
        for record in session.run(
            "MATCH (n) WHERE n.wave = $wave UNWIND labels(n) AS label "
            "RETURN label, count(*) AS c ORDER BY label",
            wave=WAVE,
        )
    }
    types = {
        record["t"]: int(record["c"])
        for record in session.run(
            "MATCH ()-[r]->() WHERE r.wave = $wave "
            "RETURN type(r) AS t, count(*) AS c ORDER BY t",
            wave=WAVE,
        )
    }
    return labels, types


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
    if not receipt.get("executed"):
        print("  no executed import receipt. Nothing has been invalidated.")
        return 1

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            labels, types = touched(session)
    finally:
        driver.close()

    rows: list[dict[str, Any]] = []
    for consumer in CONSUMERS:
        moved_labels = {
            label: labels[label] for label in consumer["reads_labels"] if label in labels
        }
        moved_types = {t: types[t] for t in consumer["reads_types"] if t in types}
        stale = bool(moved_labels or moved_types)
        rows.append(
            {
                "consumer": consumer["consumer"],
                "status": "STALE_INPUT" if stale else "CURRENT",
                "inputs_that_moved": {
                    "labels": moved_labels,
                    "relationship_types": moved_types,
                },
                "elements_touched": sum(moved_labels.values()) + sum(moved_types.values()),
                "reads_labels": list(consumer["reads_labels"]),
                "reads_types": list(consumer["reads_types"]),
                "rebuilt_by": consumer["rebuilt_by"],
                "owner_ruling": consumer["owner_ruling"],
                "cost": consumer["cost"],
            }
        )

    stale_rows = [row for row in rows if row["status"] == "STALE_INPUT"]
    report = {
        "schema_version": "1.0",
        "artifact": "WAVE_3_DEPENDENCY_INVALIDATION",
        "owner_section": "13",
        "import_run_id": receipt.get("run_id"),
        "method": (
            "Every element Wave 3 wrote carries a wave stamp, so staleness is a query about "
            "labels and predicates rather than a judgement about what probably moved. A "
            "property backfill counts as an input changing: an artifact computed over "
            "USES_FORMULA before the match levels landed read edges that now say more than "
            "they did, and nothing in the artifact records which version it saw."
        ),
        "labels_written_by_this_wave": labels,
        "relationship_types_written_by_this_wave": types,
        "consumers": rows,
        "stale": [row["consumer"] for row in stale_rows],
        "current": [row["consumer"] for row in rows if row["status"] == "CURRENT"],
        "nothing_has_been_rebuilt": True,
        "rebuild_order": [
            "1. cross-Veda matrices and formula relations -- no consumer of theirs yet",
            "2. entity coverage and quality evaluation -- read the graph directly",
            "3. semantic resemblance -- the owner's re-derivation, with its own gates",
            "4. Ask retrieval index, then re-grade only if the index moved",
            "5. Visualization Lab and Knowledge World -- public, so last and gated",
        ],
        "do_not": [
            "regenerate the frontend design",
            "publish a projection figure that has not been read back",
            "re-grade the Ask benchmark speculatively -- a daily quota is burned by a retry",
        ],
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  WAVE 3 DEPENDENCY INVALIDATION -- inspected, nothing rebuilt")
    print()
    print(
        f"  this wave wrote {len(labels)} labels and {len(types)} relationship types; "
        "an artifact reading any of them is stale"
    )
    print()
    print(f"  {'consumer':38}{'status':14}{'elements':>10}  rebuilt by")
    print(f"  {'-' * 38}{'-' * 14}{'-' * 10}  {'-' * 40}")
    for row in rows:
        print(
            f"  {row['consumer'][:37]:38}{row['status']:14}{row['elements_touched']:>10}  "
            f"{row['rebuilt_by'][:44]}"
        )
    print()
    print(f"  STALE: {len(stale_rows)} of {len(rows)}")
    for row in stale_rows:
        moved = row["inputs_that_moved"]
        names = [*moved["labels"], *moved["relationship_types"]]
        print(f"    {row['consumer']}: {', '.join(names[:6])}{' …' if len(names) > 6 else ''}")
        if row["owner_ruling"]:
            print(f"      ruling: {row['owner_ruling'][:96]}")
    print()
    print("  rebuild order:")
    for step in report["rebuild_order"]:
        print(f"    {step}")
    print()
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
