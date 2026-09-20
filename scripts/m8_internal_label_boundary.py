"""M8: stop three internal node classes leaking into the public surface. Owner Phase C.

The product/internal boundary in this graph is one Cypher clause: ``NOT n:Internal``. Every
product query interpolates it, and ``scripts/export_graph_world.py`` restates it so the
world file cannot become the one place the rule is forgotten.

Three node classes this campaign created were never marked, so they sat on the public side
of that clause:

    :QualityVerdict       2,568   this repository's assessment of its own passages
    :RoleFiller           2,052   the wiring by which a role assignment reaches a referent
    :DeityCommunity          12   an analytic partition, imported with its own refusal

The leak is measured, not hypothetical. ``frontend/.world/world.raw.json`` holds 2,568
``QualityVerdict`` nodes -- the fourth-largest type in the public world, ahead of
``:Rishi``. They carry an ``entity_key``, so the export's ``WHERE id IS NOT NULL`` admitted
them. ``RoleFiller`` and ``DeityCommunity`` have no id key and were dropped for that reason
alone, which is luck rather than a boundary.

This migration adds the ``:Internal`` label to those three classes and nothing else. It is
additive, it only ever REMOVES content from a public surface, and it is reversible by
removing one label.

What it does NOT do: touch ``:Scholar``, ``:ScholarlyWork`` or ``:ScholarlyDisagreement``.
Those are genuine product content -- a recorded disagreement is uninterpretable without the
scholar who holds it -- and they are declared in ``PRODUCT_LABELS`` instead.

Usage:
    python scripts/m8_internal_label_boundary.py [--execute] [--backup DIR]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

from vedagraph.domain.ontology import (
    LABEL_DEITY_COMMUNITY,
    LABEL_INTERNAL,
    LABEL_QUALITY_VERDICT,
    LABEL_ROLE_FILLER,
    PRODUCT_LABELS,
)

OUT = pathlib.Path("data/staging/integration/m8_internal_boundary_receipt.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The classes to demote, each with the reason it is a fact about the record rather than a
#: Vedic subject. Read from the ontology so this script cannot disagree with the declaration.
DEMOTE: tuple[str, ...] = (LABEL_QUALITY_VERDICT, LABEL_ROLE_FILLER, LABEL_DEITY_COMMUNITY)

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "public_nodes": int(
            session.run(
                f"MATCH (n) WHERE NOT n:{LABEL_INTERNAL} RETURN count(n) AS c"
            ).single()["c"]
        ),
        "core": {
            r["veda"]: int(r["n"])
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def per_label(session: Session) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for label in DEMOTE:
        row = session.run(
            f"MATCH (n:`{label}`) RETURN count(n) AS total, "
            f"sum(CASE WHEN n:{LABEL_INTERNAL} THEN 1 ELSE 0 END) AS marked, "
            "count(n.entity_key) AS with_id"
        ).single()
        out[label] = {
            "total": int(row["total"]),
            "already_internal": int(row["marked"]),
            "carries_an_id_key": int(row["with_id"]),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    # A class cannot be demoted and product at once. Checked against the declaration, so a
    # later edit that promotes one of these has to fail here rather than quietly re-leak.
    conflicts = sorted(set(DEMOTE) & PRODUCT_LABELS)
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            labels_before = per_label(session)
            outstanding = sum(
                stats["total"] - stats["already_internal"] for stats in labels_before.values()
            )

            print()
            print(f"  M8 INTERNAL LABEL BOUNDARY  {'EXECUTING' if args.execute else 'REHEARSAL'}")
            print()
            print(f"  before: {before['nodes']:,} nodes, {before['public_nodes']:,} public")
            print()
            for label, stats in labels_before.items():
                print(
                    f"  {label:22} {stats['total']:>6,} nodes  "
                    f"{stats['already_internal']:>6,} already internal  "
                    f"{stats['carries_an_id_key']:>6,} carry an id key"
                )
            print()
            print(f"  outstanding: {outstanding:,}")
            if conflicts:
                print(f"\n  REFUSING: {conflicts} are declared product labels.")
                return 1

            written = 0
            if args.execute and outstanding:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("\n  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                for label in DEMOTE:
                    with session.begin_transaction() as tx:
                        written += int(
                            tx.run(
                                f"MATCH (n:`{label}`) WHERE NOT n:{LABEL_INTERNAL} "
                                f"SET n:{LABEL_INTERNAL}, n.m8_applied = $at "
                                "RETURN count(n) AS n",
                                at=stamp,
                            ).single()["n"]
                        )
                        tx.commit()

            after = census(session)
            labels_after = per_label(session)
            complete = all(
                stats["already_internal"] == stats["total"] for stats in labels_after.values()
            )
            receipt = {
                "migration": "M8_INTERNAL_LABEL_BOUNDARY",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "demoted_classes": list(DEMOTE),
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "public_node_delta": after["public_nodes"] - before["public_nodes"],
                "core_corpus_unchanged": after["core"] == CORE,
                "labels_before": labels_before,
                "labels_after": labels_after,
                "nodes_marked": written,
                "additive": after["nodes"] == before["nodes"]
                and after["relationships"] == before["relationships"],
                "complete": complete,
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print()
            print(
                f"  after: {after['nodes']:,} nodes "
                f"(delta {receipt['node_delta']:+}), "
                f"{after['public_nodes']:,} public (delta {receipt['public_node_delta']:+})"
            )
            print(f"  core corpus unchanged  {receipt['core_corpus_unchanged']}")
            print(f"  every node marked      {complete}")
            print()
            print(f"  receipt: {OUT}")
            if not args.execute:
                print("\n  REHEARSAL ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["additive"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
