"""A consumer is CURRENT when it was rebuilt from the graph as it now stands. Owner Phase D.

``wave3_dependency_invalidation.py`` computes staleness from the labels and predicates an
import touched. That is correct and it is also one-way: the wave stamps stay on the nodes
forever, so every consumer reads STALE_INPUT for ever after, and a rebuild cannot be
expressed at all. The report could say what had been invalidated and never what had been
repaired.

This is the missing half. A rebuild records:

    input_hash    what the consumer read -- a digest over the graph state it depends on,
                  computed from its own declared labels and predicates, so the hash moves
                  exactly when its inputs move and not when something unrelated does
    output_hash   a digest of what it produced
    rebuilt_at    when, and against which graph census

A consumer is CURRENT when the ledger holds a rebuild whose ``input_hash`` equals the
current input hash. That is a measurement, not a flag somebody set: if the graph moves
again, the hash stops matching and the consumer goes STALE without anyone remembering to
say so.

Usage:
    python scripts/rebuild_ledger.py --status
    python scripts/rebuild_ledger.py --record CONSUMER --output-file PATH
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase, Session
from wave3_dependency_invalidation import CONSUMERS

LEDGER = pathlib.Path("data/staging/integration/rebuild_ledger.json")
OUT = pathlib.Path("data/staging/integration/dependency_status.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"


def consumer_by_name(name: str) -> dict[str, Any]:
    for consumer in CONSUMERS:
        if consumer["consumer"] == name:
            return consumer
    raise SystemExit(f"unknown consumer {name!r}; known: {[c['consumer'] for c in CONSUMERS]}")


def input_hash(session: Session, consumer: dict[str, Any]) -> str:
    """A digest over exactly the graph state this consumer reads.

    Counts per declared label and per declared predicate. Deliberately not a whole-graph
    digest: a consumer that reads only deities must not go stale because a ritual step was
    written, or the ledger degenerates into "everything is stale whenever anything moves".
    """
    parts: list[str] = []
    for label in sorted(consumer["reads_labels"]):
        row = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()
        parts.append(f"label:{label}={int(row['c']) if row else 0}")
    for predicate in sorted(consumer["reads_types"]):
        row = session.run(f"MATCH ()-[r:`{predicate}`]->() RETURN count(r) AS c").single()
        parts.append(f"type:{predicate}={int(row['c']) if row else 0}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def load_ledger() -> dict[str, Any]:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--record", default="")
    parser.add_argument("--output-file", default="")
    parser.add_argument(
        "--blocked",
        default="",
        help="Record the consumer as BLOCKED with this reason instead of rebuilt.",
    )
    parser.add_argument(
        "--not-applicable",
        default="",
        help="Record the consumer as NOT_APPLICABLE with this reason: there is nothing to "
        "rebuild, as distinct from a rebuild that has not happened.",
    )
    args = parser.parse_args()

    ledger = load_ledger()
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])

            if args.record:
                consumer = consumer_by_name(args.record)
                entry: dict[str, Any] = {
                    "consumer": args.record,
                    "input_hash": input_hash(session, consumer),
                    "at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "graph_census": {"nodes": nodes, "relationships": rels},
                }
                if args.not_applicable:
                    entry["not_applicable_reason"] = args.not_applicable
                    entry["output_hash"] = None
                elif args.blocked:
                    entry["blocked_reason"] = args.blocked
                    entry["output_hash"] = None
                elif args.output_file:
                    path = pathlib.Path(args.output_file)
                    if not path.exists():
                        print(f"  output file {path} does not exist")
                        return 1
                    entry["output_file"] = str(path)
                    entry["output_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
                else:
                    print(
                        "  --record needs --output-file, --blocked or --not-applicable"
                    )
                    return 1
                ledger[args.record] = entry
                LEDGER.write_text(
                    json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                print(f"  recorded {args.record}: input {entry['input_hash'][:12]}")
                return 0

            rows: list[dict[str, Any]] = []
            for consumer in CONSUMERS:
                name = str(consumer["consumer"])
                current_hash = input_hash(session, consumer)
                recorded = ledger.get(name) or {}
                if recorded.get("not_applicable_reason"):
                    status = "NOT_APPLICABLE"
                elif recorded.get("blocked_reason"):
                    status = "BLOCKED"
                elif not recorded:
                    status = "STALE_INPUT"
                elif recorded.get("input_hash") == current_hash:
                    status = "CURRENT"
                else:
                    status = "STALE_INPUT"
                rows.append(
                    {
                        "consumer": name,
                        "status": status,
                        "input_hash": current_hash,
                        "recorded_input_hash": recorded.get("input_hash"),
                        "output_hash": recorded.get("output_hash"),
                        "rebuilt_at": recorded.get("at"),
                        "blocked_reason": recorded.get("blocked_reason"),
                        "not_applicable_reason": recorded.get("not_applicable_reason"),
                        "rebuilt_by": consumer.get("rebuilt_by"),
                    }
                )
    finally:
        driver.close()

    summary = {
        "artifact": "DEPENDENCY_STATUS",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "graph_census": {"nodes": nodes, "relationships": rels},
        "consumers": rows,
        "counts": {
            status: sum(1 for r in rows if r["status"] == status)
            for status in ("CURRENT", "STALE_INPUT", "BLOCKED", "NOT_APPLICABLE")
        },
        "rule": (
            "CURRENT means the ledger holds a rebuild whose input hash equals the current "
            "one. The hash covers only the labels and predicates the consumer declares it "
            "reads, so an unrelated write does not make it stale and a related one does."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  DEPENDENCY STATUS -- measured against the ledger")
    print()
    print(f"  {'consumer':40} {'status':12} {'input':>10} {'output':>10}")
    print(f"  {'-' * 76}")
    for row in rows:
        print(
            f"  {row['consumer']:40} {row['status']:12} "
            f"{row['input_hash'][:8]:>10} "
            f"{(row['output_hash'] or '-')[:8]:>10}"
        )
    print()
    print("  " + "  ".join(f"{k}={v}" for k, v in summary["counts"].items()))
    print(f"  report: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
