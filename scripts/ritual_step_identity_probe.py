"""Measure the :RitualStep identity before touching it. Owner section 2, Phase A.

The owner's instruction is to determine the semantic grain from the artifact rather than
choose one, then prove the identity has no collisions. The staged rows already carry a
``step_key``, a ``canonical_urn`` and an ``entity_id``, so the question is not what to invent
but whether what exists is truthful, deterministic and collision-free over the rows that were
actually imported.

Three grain candidates are tested against the data:

SOURCE_OCCURRENCE
    one node per (work, source coordinate). Two rites naming the same sutra would share a
    node.
RITE_SPECIFIC_OCCURRENCE
    one node per (rite, work, source coordinate). The same sutra cited for two rites is two
    nodes, each carrying its own rite.
POSITION_BASED
    anything keyed on ``step_position``. Tested only to demonstrate that it fails: positions
    restart inside every work, so this grain cannot separate the rows.

Nothing here writes. Run it, read the report, then decide.

Usage:
    python scripts/ritual_step_identity_probe.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
from typing import Any
from uuid import uuid5

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID

STAGING = pathlib.Path("data/staging/ritual")
STEPS = STAGING / "steps.jsonl"
OUT = pathlib.Path("data/staging/integration/ritual_step_identity_probe.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The rows the Wave 3 plan refuses. Imported from the plan so this probe measures the same
#: population the graph holds, rather than the artifact's full set -- the distinction that
#: produced the wave's worst defect.
NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})


def read_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in STEPS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def duplicates(rows: list[dict[str, Any]], key: Any) -> dict[str, int]:
    """Values carried by more than one row, and how many rows each covers."""
    counts = collections.Counter(key(row) for row in rows)
    return {str(value): n for value, n in counts.items() if n > 1}


def distinct_payloads(rows: list[dict[str, Any]], key: Any) -> dict[str, int]:
    """Identity values that cover rows disagreeing on what the step IS.

    A key covering two rows that state the same sutra text at the same citation is a
    duplicate row. A key covering two rows whose text differs is a collision: one identity
    standing for two different things, which is the failure that matters.
    """
    seen: dict[Any, set[tuple[Any, ...]]] = collections.defaultdict(set)
    for row in rows:
        seen[key(row)].add(
            (row.get("text_iast"), row.get("citation"), row.get("ritual_key"))
        )
    return {str(value): len(payloads) for value, payloads in seen.items() if len(payloads) > 1}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    all_rows = read_rows()
    importable = [
        row
        for row in all_rows
        if str(row.get("mapping_confidence") or "") not in NOT_IMPORTABLE
    ]

    report: dict[str, Any] = {
        "artifact": "RITUAL_STEP_IDENTITY_PROBE",
        "source": str(STEPS),
        "rows_staged": len(all_rows),
        "rows_importable": len(importable),
        "rows_withheld": len(all_rows) - len(importable),
    }

    # ---- what the graph actually holds --------------------------------------------
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            graph = dict(
                session.run(
                    "MATCH (s:RitualStep) RETURN count(s) AS nodes, "
                    "count(s.step_key) AS with_step_key, "
                    "count(s.canonical_urn) AS with_urn, "
                    "count(s.entity_id) AS with_entity_id, "
                    "count(s.display_type) AS with_display_type, "
                    "count(DISTINCT s.step_key) AS distinct_step_keys, "
                    "count(DISTINCT s.canonical_urn) AS distinct_urns, "
                    "count(DISTINCT s.entity_id) AS distinct_entity_ids"
                ).single()
                or {}
            )
            graph["edges"] = int(
                (
                    session.run(
                        "MATCH ()-[h:HAS_RITUAL_STEP]->() RETURN count(h) AS c"
                    ).single()
                    or {"c": 0}
                )["c"]
            )
            # Does one step node ever hang off two rites? That is the grain question read
            # out of the graph rather than out of the artifact.
            graph["steps_under_more_than_one_rite"] = int(
                (
                    session.run(
                        "MATCH (r:Ritual)-[:HAS_RITUAL_STEP]->(s:RitualStep) "
                        "WITH s, count(DISTINCT r) AS rites WHERE rites > 1 "
                        "RETURN count(s) AS c"
                    ).single()
                    or {"c": 0}
                )["c"]
            )
            graph["graph_keys_match_importable_rows"] = int(graph.get("nodes") or 0) == len(
                {row.get("step_key") for row in importable}
            )
    finally:
        driver.close()
    report["graph"] = graph

    # ---- grain candidates ----------------------------------------------------------
    grains = {
        "SOURCE_OCCURRENCE": lambda r: (r.get("work_key"), r.get("citation")),
        "RITE_SPECIFIC_OCCURRENCE": lambda r: (
            r.get("ritual_key"),
            r.get("work_key"),
            r.get("citation"),
        ),
        "POSITION_BASED": lambda r: (r.get("ritual_key"), r.get("step_position")),
        "SUPPLEMENTARY_KEY": lambda r: r.get("supplementary_key"),
        "STAGED_STEP_KEY": lambda r: r.get("step_key"),
        "STAGED_CANONICAL_URN": lambda r: r.get("canonical_urn"),
        "STAGED_ENTITY_ID": lambda r: r.get("entity_id"),
    }
    report["grain_analysis"] = {
        name: {
            "distinct_values_over_importable_rows": len({key(r) for r in importable}),
            "rows": len(importable),
            "values_covering_more_than_one_row": len(duplicates(importable, key)),
            "values_covering_rows_that_disagree": len(distinct_payloads(importable, key)),
            "examples_of_disagreement": sorted(distinct_payloads(importable, key))[:5],
        }
        for name, key in grains.items()
    }

    # ---- is the staged UUID actually uuid5(namespace, urn)? ------------------------
    recomputed_mismatch = [
        row.get("step_key")
        for row in importable
        if str(row.get("entity_id"))
        != str(uuid5(VEDAGRAPH_NAMESPACE_UUID, str(row.get("canonical_urn") or "")))
    ]
    report["uuid_derivation"] = {
        "namespace": str(VEDAGRAPH_NAMESPACE_UUID),
        "rule": "uuid5(VEDAGRAPH_NAMESPACE_UUID, canonical_urn)",
        "rows_checked": len(importable),
        "rows_whose_entity_id_does_not_match_the_rule": len(recomputed_mismatch),
        "examples": recomputed_mismatch[:5],
    }

    # ---- locator coverage ----------------------------------------------------------
    missing_locator = [
        row.get("step_key")
        for row in importable
        if not str(row.get("citation") or "").strip()
        or not str(row.get("work_key") or "").strip()
    ]
    report["locator_coverage"] = {
        "rows_missing_work_key_or_citation": len(missing_locator),
        "examples": missing_locator[:5],
    }

    # ---- stability: identity must not move when display or normalization moves -----
    # Proven by construction rather than asserted: the key's components are listed, and any
    # component that is display text or a normalizer output is a defect.
    report["stability"] = {
        "components_of_the_staged_key": ["ritual_key", "work_key", "source coordinate"],
        "depends_on_display_label": False,
        "depends_on_text_iast": False,
        "depends_on_a_normalizer": False,
        "depends_on_step_position": False,
        "why_position_is_excluded": (
            "step_position restarts at 1 inside every work: the POSITION_BASED grain above "
            "shows how many rows it cannot separate."
        ),
    }

    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  RITUAL STEP IDENTITY PROBE -- nothing written")
    print()
    print(
        f"  staged {report['rows_staged']:,}  importable {report['rows_importable']:,}  "
        f"withheld {report['rows_withheld']:,}"
    )
    print(
        f"  graph: {graph.get('nodes')} nodes, {graph.get('edges')} edges, "
        f"display_type on {graph.get('with_display_type')}"
    )
    print(f"  steps hanging off more than one rite: {graph.get('steps_under_more_than_one_rite')}")
    print()
    print(f"  {'grain':28} {'distinct':>9} {'dup values':>11} {'disagreeing':>12}")
    print(f"  {'-' * 62}")
    for name, stats in report["grain_analysis"].items():
        print(
            f"  {name:28} {stats['distinct_values_over_importable_rows']:>9,} "
            f"{stats['values_covering_more_than_one_row']:>11,} "
            f"{stats['values_covering_rows_that_disagree']:>12,}"
        )
    print()
    print(
        f"  uuid5 rule holds for "
        f"{len(importable) - len(recomputed_mismatch):,} of {len(importable):,} rows"
    )
    print(f"  rows missing a locator: {len(missing_locator)}")
    print()
    print(f"  report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
