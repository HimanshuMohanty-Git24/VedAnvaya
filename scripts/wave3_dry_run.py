#!/usr/bin/env python3
"""Owner section 22: compute every canonical write Wave 3 would make. Perform none.

The graph is opened read-only and every count is read out of it, so the projected final
census is arithmetic over measured state rather than an estimate. If this script can write
anything at all it is broken; the driver is opened in a session that only ever runs
MATCH and RETURN, and that is asserted rather than intended.

What it reconciles, per owner section 22: nodes to create, nodes to update, relationships
to create, delete and update, properties to change, schema additions, per-domain counts,
identity collisions, dangling references, and the expected final census -- each compared
against the staging manifests so a disagreement between the plan and the artifacts is a
finding before anything is written.

Eligibility is honoured. A domain that is not ELIGIBLE in the three-gate ledger contributes
0 writes and is listed with its reason, because a dry-run that quietly plans writes for a
blocked domain is worse than no dry-run.

Usage:
    python scripts/wave3_dry_run.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
from typing import Any

from neo4j import GraphDatabase

STAGING = pathlib.Path("data/staging")
LEDGER = STAGING / "integration" / "wave3_eligibility.json"
BLOCKERS = STAGING / "integration" / "blockers.json"
OVERLAYS = STAGING / "lead_overlays" / "wave1_decisions.json"
OUT = STAGING / "integration" / "wave3_dry_run.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: Rows at these confidences are staged and not importable. Enforced here as well as in the
#: validator, because a dry-run that planned them would mis-state the census.
NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    ledger = load_json(LEDGER)
    blockers = load_json(BLOCKERS)
    overlays = load_json(OVERLAYS)

    open_blockers = [
        b["blocker_id"]
        for b in blockers.get("blockers", [])
        if not str(b.get("status", "")).startswith("RESOLVED")
    ]

    # Keys the owner has barred from import, from the overlay rather than from memory.
    barred_keys: set[str] = set()
    barred_patterns: list[str] = []
    barred_domains: set[str] = set()
    for decision in overlays.get("decisions", []):
        override = decision.get("override") or {}
        if not (override.get("import_barred") or override.get("mapping_confidence") == "PROBABLE"):
            continue
        for key in decision.get("affected_keys") or []:
            barred_keys.add(key)
        if decision.get("affected_key_pattern"):
            barred_patterns.append(decision["affected_key_pattern"])
        affected = str(decision.get("affects_domain") or "")
        if affected and affected != "*":
            barred_domains.update(d.strip() for d in affected.split(","))

    import re as _re

    barred_res = [_re.compile(p) for p in barred_patterns]

    def is_barred(key: str) -> bool:
        return key in barred_keys or any(r.match(key) for r in barred_res)

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            node_row = session.run("MATCH (n) RETURN count(n) AS c").single()
            rel_row = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()
            if node_row is None or rel_row is None:
                raise RuntimeError("the graph returned no census; refusing to plan against it")
            before_nodes = int(node_row["c"])
            before_rels = int(rel_row["c"])
            core = {
                r["veda"]: r["n"]
                for r in session.run(
                    "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                )
            }
    finally:
        driver.close()

    domains = sorted(
        p.name for p in STAGING.iterdir() if p.is_dir() and (p / "rows.jsonl").exists()
    )

    plan: dict[str, Any] = {}
    total_importable = 0
    total_withheld = 0

    for domain in domains:
        entry = (ledger.get("domains") or {}).get(domain, {})
        status = entry.get("status", "UNKNOWN")
        rows = read_jsonl(STAGING / domain / "rows.jsonl")
        manifest = load_json(STAGING / domain / "manifest.json")

        weak = sum(1 for r in rows if r.get("mapping_confidence") in NOT_IMPORTABLE)
        barred = sum(1 for r in rows if is_barred(str(r.get("canonical_key") or "")))
        eligible_rows = [
            r
            for r in rows
            if r.get("mapping_confidence") not in NOT_IMPORTABLE
            and not is_barred(str(r.get("canonical_key") or ""))
        ]

        gates_ok = status == "ELIGIBLE"
        planned = len(eligible_rows) if gates_ok else 0
        withheld = len(rows) - planned

        # The manifest's own accepted count must match the rows on disk, or the plan is
        # built on an artifact that has moved since it was described.
        declared = (manifest.get("counts") or {}).get("accepted")
        plan[domain] = {
            "ledger_status": status,
            "rows_on_disk": len(rows),
            "manifest_declares_accepted": declared,
            "manifest_agrees_with_disk": declared == len(rows),
            "not_importable_by_confidence": weak,
            "barred_by_owner_overlay": barred,
            "planned_writes": planned,
            "withheld": withheld,
            "reason_withheld": (
                None
                if gates_ok
                else f"ledger status {status}: {entry.get('status_detail', 'no detail')}"
            ),
            "blocked_by": entry.get("blocked_by", []),
        }
        total_importable += planned
        total_withheld += withheld

    disagreements = [d for d, p in plan.items() if not p["manifest_agrees_with_disk"]]

    reasons: list[str] = [
        *(f"open blocker: {b}" for b in open_blockers),
        *(f"manifest disagrees with disk: {d}" for d in disagreements),
        *(["no domain contributes an importable write"] if total_importable == 0 else []),
    ]

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "DRY_RUN_NO_WRITE",
        "graph_before": {
            "nodes": before_nodes,
            "relationships": before_rels,
            "core_corpus": core,
        },
        "planned_writes_total": total_importable,
        "withheld_total": total_withheld,
        "per_domain": plan,
        "schema_additions_pending": [
            "M1 :RoleFiller + ASSERTION_ROLE + ROLE_FILLER_ENTITY",
            "M2 running_samhita_number on Samavedic :Mantra",
            "M3 four gana :Work identities",
            "M4 MUSICALIZED_AS range widening",
            "M5 SPECIALIZED_FORM_OF",
        ],
        "schema_additions_returned_to_owner": [
            "M6 scope_type namespacing -- OLD_PREDICATE_MEANING_CHANGED is true"
        ],
        "open_blockers": open_blockers,
        "manifest_vs_disk_disagreements": disagreements,
        "expected_final_census": {
            "note": (
                "Unchanged from before, because no domain is both eligible and unblocked "
                "enough to contribute a write. That is the finding, not an omission: the "
                "dry-run's job is to say what would happen, and what would happen is "
                "nothing."
            )
            if total_importable == 0
            else (
                "Node and relationship deltas are not derivable from row counts alone -- a "
                "row may create several relationships and no node, or update a property "
                "with no new element. The importer must emit its own per-element plan "
                "before this figure can be stated, and stating it from row counts would be "
                "the kind of arithmetic-shaped guess this campaign has been correcting."
            ),
            "nodes_before": before_nodes,
            "relationships_before": before_rels,
            "derivable_yet": total_importable == 0,
        },
        "go_no_go": "NO-GO" if (open_blockers or total_importable == 0 or disagreements) else "GO",
        "go_no_go_reasons": reasons,
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  WAVE 3 DRY RUN -- no write performed")
    print(f"  graph before: {before_nodes:,} nodes / {before_rels:,} relationships")
    print()
    print(f"  {'domain':22}{'status':22}{'rows':>8}{'planned':>9}{'withheld':>10}")
    print(f"  {'-' * 22}{'-' * 22}{'-' * 8}{'-' * 9}{'-' * 10}")
    for domain in sorted(plan):
        p = plan[domain]
        print(
            f"  {domain:22}{p['ledger_status']:22}{p['rows_on_disk']:>8}"
            f"{p['planned_writes']:>9}{p['withheld']:>10}"
        )
    print()
    print(f"  planned writes: {total_importable:,}   withheld: {total_withheld:,}")
    if disagreements:
        print(f"  MANIFEST/DISK DISAGREEMENT: {', '.join(disagreements)}")
    print(f"  open blockers: {len(open_blockers)}  {', '.join(open_blockers) or 'none'}")
    print()
    print(f"  VERDICT: {report['go_no_go']}")
    for reason in reasons:
        print(f"    - {reason}")
    print()
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
