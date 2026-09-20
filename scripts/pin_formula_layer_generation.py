#!/usr/bin/env python3
"""Pin the *published* formula-layer generation, and pin its distance from the rebuild.

Why this file exists
====================

Four live-gated tests in ``tests/domain/test_v3_layers.py`` asserted that the graph's
formula layer has exactly as many families, members and expansion roles as
``data/enrichment/vedagraph_enrichment_v1/formula_families.jsonl`` declares. That equality
held when the graph was loaded. It cannot hold now, and not because either side is broken:

*   ``formula_id`` is a **published stable product ID**. ``/api/v1/formulas/{formula_id}``
    serves it and ``graph.py`` documents it as stable. Re-mining the corpus re-keys it,
    because the id is a content hash, so ``data/staging/final_stabilization/
    formula_identity_impact.json`` records ``migration_permitted: false`` over all 217
    affected formulas. The graph's generation is frozen by that rule.

*   The enrichment layer was nevertheless rebuilt on disk. ``manifest.json`` digests match
    the live ``formulas.jsonl`` byte for byte and its ``corpus_counts`` are the graph's own
    20,210 mantras, so the on-disk trio is the current generator's honest output over the
    current corpus. It is simply a *later* generation than the one the graph holds.

So there are two generations, both correct, and an owner rule that forbids collapsing them.
A test asserting they are equal can never pass, and while it fails on the count it never
reaches the invariants it was actually written to protect -- uniqueness, endpoint labels,
the tier vocabulary and the containment claim. The suite already contained the evidence
that the *graph* is the served figure: ``tests/api/test_stats.py`` pins
``formula_families: 720``, which is the graph's number, and passes.

What this pins
==============

Two things, so that neither generation can drift unnoticed:

1.  **The published generation**, measured from the graph. This is the falsifier the four
    tests lost. If anything later adds, drops or re-keys a family, a member or a role, the
    census here stops matching and the tests fail in both directions.

2.  **The exact delta to the on-disk rebuild.** Recording only the graph's census would let
    the rebuild wander without anyone noticing. The delta is pinned by *identifier sets*,
    not just sizes, so a rebuild that swaps one formula for another of equal count still
    trips it. When it trips, the divergence has changed and it needs re-adjudicating
    against the owner rule -- which is the outcome this project wants, rather than a silent
    re-base.

The pin is small, tracked JSON, and it sits beside the manifest whose generation it is
measuring the distance from. ``data/enrichment/**/*.jsonl`` is gitignored and ``*.json``
there is not, which is the same rule that keeps ``manifest.json`` and ``analytics.json``
tracked.

Usage:
    python scripts/pin_formula_layer_generation.py [--write]

Without ``--write`` it measures and reports the drift against the existing pin, exiting
non-zero if anything moved. That is the mode CI and the release gate want.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any, Final

from neo4j import GraphDatabase, Query

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
ENRICHMENT_DIR: Final = PROJECT_ROOT / "data" / "enrichment" / "vedagraph_enrichment_v1"
PIN: Final = ENRICHMENT_DIR / "formula_layer_published_pin.json"

URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"

#: Every measure below is a single aggregate or one bounded id scan.
QUERY_TIMEOUT_SECONDS: Final[float] = 300.0

#: Where the rule that froze the published generation is written down. A pin that cannot
#: point at its own authority is indistinguishable from a number invented to pass a test.
OWNER_RULE: Final[dict[str, str]] = {
    "rule": (
        "formula_id is a published stable product ID; content-hash recomputation cannot "
        "silently re-key it"
    ),
    "recorded_in": "data/staging/final_stabilization/formula_identity_impact.json",
    "migration_permitted": "false",
    "published_contract": (
        "src/vedagraph/api/routes/formulas.py exposes /api/v1/formulas/{formula_id}; "
        "src/vedagraph/api/routes/graph.py describes Formula.formula_id as a stable "
        "product identifier"
    ),
    "verification_receipt": (
        "data/staging/release_blocker_r1/formula_identity_verification_receipt.json"
    ),
}


def _identity(normalized: str) -> str:
    """The collapsed identity surface -- ``normalized`` with its word breaks removed."""
    return "".join((normalized or "").split())


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def measure_published(session: Any) -> dict[str, Any]:
    """The graph's formula-layer census, plus every structural invariant it must hold.

    The invariants are measured here rather than only in the tests so that the pin itself
    records that the frozen generation was sound when it was pinned. Pinning a census over
    a layer nobody checked would freeze a defect.
    """

    def scalar(query: str) -> Any:
        record = session.run(Query(query, timeout=QUERY_TIMEOUT_SECONDS)).single()
        return None if record is None else record[0]

    roles = {
        record["role"]: record["n"]
        for record in session.run(
            Query(
                "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN r.role AS role, count(*) AS n",
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        )
    }
    tiers = sorted(
        record[0]
        for record in session.run(
            Query(
                "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN DISTINCT r.quality_tier",
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        )
    )

    # The containment claim, recomputed from the graph's own stored strings.
    containment_rows = list(
        session.run(
            Query(
                """
                MATCH (child:Formula)-[r:MEMBER_OF_FAMILY]->(fam:FormulaFamily)
                WHERE r.role = 'EXPANSION'
                MATCH (parent:Formula {formula_id: r.linked_formula_id})
                      -[:MEMBER_OF_FAMILY]->(fam)
                RETURN child.normalized AS child, parent.normalized AS parent
                """,
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        )
    )
    containment_violations = sum(
        1
        for row in containment_rows
        if not (
            _identity(row["parent"]) in _identity(row["child"])
            and _identity(row["parent"]) != _identity(row["child"])
        )
    )

    return {
        "formulas": scalar("MATCH (f:Formula) RETURN count(f)"),
        "families": scalar("MATCH (f:FormulaFamily) RETURN count(f)"),
        "members": scalar("MATCH (:Formula)-[r:MEMBER_OF_FAMILY]->(:FormulaFamily) RETURN count(r)"),
        "roles": roles,
        "quality_tiers": tiers,
        "invariants": {
            "distinct_family_id": scalar(
                "MATCH (f:FormulaFamily) RETURN count(DISTINCT f.family_id)"
            ),
            "null_family_id": scalar(
                "MATCH (f:FormulaFamily) WHERE f.family_id IS NULL RETURN count(f)"
            ),
            "distinct_collapsed_formula_identity": scalar(
                'MATCH (f:Formula) RETURN count(DISTINCT replace(f.normalized, " ", ""))'
            ),
            "member_edges_with_a_bad_endpoint": scalar(
                "MATCH (a)-[r:MEMBER_OF_FAMILY]->(b) "
                "WHERE NOT a:Formula OR NOT b:FormulaFamily RETURN count(r)"
            ),
            "formulas_in_more_than_one_family": scalar(
                "MATCH (f:Formula)-[:MEMBER_OF_FAMILY]->(x) "
                "WITH f, count(DISTINCT x) AS n WHERE n > 1 RETURN count(f)"
            ),
            "expansion_edges_whose_linked_parent_is_absent": scalar(
                "MATCH (child:Formula)-[r:MEMBER_OF_FAMILY]->(fam:FormulaFamily) "
                "WHERE r.role = 'EXPANSION' AND NOT EXISTS { "
                "MATCH (p:Formula {formula_id: r.linked_formula_id})"
                "-[:MEMBER_OF_FAMILY]->(fam) } RETURN count(r)"
            ),
            "families_whose_member_count_disagrees_with_landed_edges": scalar(
                "MATCH (fam:FormulaFamily) "
                "OPTIONAL MATCH (:Formula)-[r:MEMBER_OF_FAMILY]->(fam) "
                "WITH fam, count(r) AS landed "
                "WHERE coalesce(fam.member_count, -1) <> landed RETURN count(fam)"
            ),
            "expansion_rows_recomputed": len(containment_rows),
            "containment_violations": containment_violations,
        },
    }


def measure_rebuild_delta(session: Any) -> dict[str, Any]:
    """The distance from the published generation to the on-disk rebuild, by id set.

    Sizes alone would let a rebuild swap one formula for another and keep the delta
    looking unchanged, so each side is digested over its sorted identifier set.
    """

    def graph_ids(query: str) -> set[str]:
        return {
            record[0]
            for record in session.run(Query(query, timeout=QUERY_TIMEOUT_SECONDS))
            if record[0] is not None
        }

    graph_formulas = graph_ids("MATCH (f:Formula) RETURN f.formula_id")
    graph_families = graph_ids("MATCH (f:FormulaFamily) RETURN f.family_id")
    graph_members = {
        f"{record['a']}|{record['b']}|{record['role']}"
        for record in session.run(
            Query(
                "MATCH (a:Formula)-[r:MEMBER_OF_FAMILY]->(b:FormulaFamily) "
                "RETURN a.formula_id AS a, b.family_id AS b, r.role AS role",
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        )
    }

    disk_formulas = {str(row["formula_id"]) for row in _read_jsonl(ENRICHMENT_DIR / "formulas.jsonl")}
    disk_families = {
        str(row["family_id"]) for row in _read_jsonl(ENRICHMENT_DIR / "formula_families.jsonl")
    }
    disk_members = {
        f"{row['formula_id']}|{row['family_id']}|{row['role']}"
        for row in _read_jsonl(ENRICHMENT_DIR / "formula_family_members.jsonl")
    }

    def side(published: set[str], rebuilt: set[str]) -> dict[str, Any]:
        only_published = sorted(published - rebuilt)
        only_rebuilt = sorted(rebuilt - published)
        return {
            "published": len(published),
            "rebuilt": len(rebuilt),
            "published_only": len(only_published),
            "rebuilt_only": len(only_rebuilt),
            "published_only_sha256": hashlib.sha256(
                "\n".join(only_published).encode("utf-8")
            ).hexdigest(),
            "rebuilt_only_sha256": hashlib.sha256(
                "\n".join(only_rebuilt).encode("utf-8")
            ).hexdigest(),
        }

    return {
        "formulas": side(graph_formulas, disk_formulas),
        "families": side(graph_families, disk_families),
        "members": side(graph_members, disk_members),
    }


def build() -> dict[str, Any]:
    manifest_path = ENRICHMENT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            published = measure_published(session)
            delta = measure_rebuild_delta(session)
    finally:
        driver.close()

    return {
        "artifact": "FORMULA_LAYER_PUBLISHED_PIN",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "why": (
            "The graph's formula layer is frozen at a published generation and the "
            "enrichment layer on disk has since been rebuilt. Both are correct; the owner "
            "rule below forbids collapsing them. This pin is the falsifier for the frozen "
            "generation and for its exact distance from the rebuild."
        ),
        "owner_rule": OWNER_RULE,
        "published_generation": published,
        "rebuild_on_disk": {
            "pipeline_version": manifest.get("pipeline_version"),
            "corpus_counts": manifest.get("corpus_counts"),
            "manifest_formula_count": (manifest.get("counts") or {}).get("formulas"),
            "manifest_digest_of_formulas_jsonl": (manifest.get("digests") or {}).get(
                "formulas.jsonl"
            ),
        },
        "delta_published_to_rebuild": delta,
        "served_figure_is_the_graph": (
            "The API and the frontend read the graph :FormulaFamily nodes. "
            "tests/api/test_stats.py pins formula_families: 720, the graph's figure. "
            "The JSONL is read only by the producer, the graph importers and this pin."
        ),
    }


def report(pin: dict[str, Any], existing: dict[str, Any] | None) -> int:
    published = pin["published_generation"]
    inv = published["invariants"]
    print()
    print("  FORMULA LAYER -- PUBLISHED GENERATION PIN")
    print()
    print(f"  formulas {published['formulas']}   families {published['families']}   "
          f"members {published['members']}")
    print(f"  roles    {published['roles']}")
    print(f"  tiers    {published['quality_tiers']}")
    print()
    failures: list[str] = []
    if inv["distinct_family_id"] != published["families"]:
        failures.append("family_id is not unique over :FormulaFamily")
    if inv["distinct_collapsed_formula_identity"] != published["formulas"]:
        failures.append("two formulas collapse to one identity")
    for key in (
        "null_family_id",
        "member_edges_with_a_bad_endpoint",
        "formulas_in_more_than_one_family",
        "expansion_edges_whose_linked_parent_is_absent",
        "families_whose_member_count_disagrees_with_landed_edges",
        "containment_violations",
    ):
        if inv[key]:
            failures.append(f"{key} = {inv[key]}, must be 0")
    if inv["expansion_rows_recomputed"] != published["roles"].get("EXPANSION"):
        failures.append("EXPANSION rows recomputed does not match the role count")
    for name, row in pin["delta_published_to_rebuild"].items():
        print(f"  delta {name:<9} published {row['published']:>5}  rebuilt {row['rebuilt']:>5}  "
              f"published-only {row['published_only']:>4}  rebuilt-only {row['rebuilt_only']:>4}")
    print()
    for failure in failures:
        print(f"  INVARIANT FAILED: {failure}")
    if not failures:
        print("  every published-generation invariant holds")

    drift: list[str] = []
    if existing is not None:
        if existing.get("published_generation") != published:
            drift.append("published_generation moved against the pin")
        if existing.get("delta_published_to_rebuild") != pin["delta_published_to_rebuild"]:
            drift.append("delta_published_to_rebuild moved against the pin")
        for line in drift:
            print(f"  DRIFT: {line}")
        if not drift:
            print("  pin matches the live measurement")
    else:
        print("  no pin on disk yet")
    print()
    return 1 if failures or drift else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the pin to disk")
    args = parser.parse_args()

    pin = build()
    existing = json.loads(PIN.read_text(encoding="utf-8")) if PIN.exists() else None
    code = report(pin, None if args.write else existing)
    if args.write:
        PIN.write_text(
            json.dumps(pin, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"  written: {PIN.relative_to(PROJECT_ROOT)}")
        print()
    return code


if __name__ == "__main__":
    sys.exit(main())
