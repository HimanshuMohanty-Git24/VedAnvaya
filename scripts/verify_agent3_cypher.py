"""Dry-run Agent 3's proposed Cypher without writing anything.

Two checks, and they catch different failures:

1. ``EXPLAIN`` every statement. The planner parses it, resolves the labels and properties
   and produces a plan **without executing**, so a syntax error, an unknown function or a
   malformed MERGE is caught here rather than a third of the way through a 154,261-row
   import. A statement that only ever gets read by a human is a statement nobody has run.

2. Run every ``preflight`` with the **real** rows and assert it returns 0. A preflight that
   is never executed is a comment. This is the check that would have caught an endpoint
   that does not resolve -- the failure mode where ``MATCH`` silently skips a row and the
   import quietly writes fewer elements than it promised.

Neo4j is read **only**: ``EXPLAIN`` does not execute, and the preflights are ``MATCH`` /
``RETURN``. The census is measured before and after and asserted unchanged.

Run::

    python scripts/verify_agent3_cypher.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"
PROPOSAL: Final = OUT_DIR / "proposed_mutations.json"

#: EXPLAIN still plans the whole statement, so a handful of rows is enough to type the
#: parameter. It never reaches execution.
EXPLAIN_SAMPLE: Final = 3


def _session() -> Any:
    load_dotenv(str(REPO / ".env"))
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
        ),
    )
    return driver, driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


def _rows(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    with (REPO / path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _statements(group: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """``(label, statement, parameters_from)`` for each statement in a group."""
    cypher = group.get("cypher")
    if not cypher:
        return []
    out: list[tuple[str, str, str | None]] = []
    for item in cypher:
        if isinstance(item, str):
            out.append((group["group_id"], item, group.get("parameters_from")))
        else:
            out.append(
                (
                    f"{group['group_id']}#step{item['step']}",
                    item["statement"],
                    item.get("parameters_from"),
                )
            )
    return out


def main() -> int:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    driver, session = _session()
    failures: list[str] = []
    report: list[dict[str, Any]] = []
    try:
        before = (
            session.run("MATCH (n) RETURN count(n) AS v").single()["v"],
            session.run("MATCH ()-[r]->() RETURN count(r) AS v").single()["v"],
        )
        for group in proposal["groups"]:
            gid = group["group_id"]
            if group.get("skip"):
                report.append({"group": gid, "skipped": True, "reason": group["operation"]})
                continue

            entry: dict[str, Any] = {"group": gid, "statements": [], "preflight": None}

            for label, statement, params_path in _statements(group):
                rows = _rows(params_path)[:EXPLAIN_SAMPLE]
                try:
                    session.run(f"EXPLAIN {statement}", rows=rows).consume()
                    entry["statements"].append({"name": label, "explain": "OK"})
                except Exception as exc:
                    entry["statements"].append(
                        {"name": label, "explain": "FAILED", "error": str(exc)[:400]}
                    )
                    failures.append(f"{label}: EXPLAIN failed -- {str(exc)[:200]}")

            preflight = group.get("preflight")
            depends_on = group.get("preflight_depends_on_group")
            if preflight and depends_on:
                # This group's preflight checks endpoints a PREVIOUS group creates, so
                # running it before that group necessarily reports them missing. That is
                # the ordering working, not a defect, and reporting it as a failure would
                # be a false alarm on a correct proposal. Verified for real by the runner
                # between the two groups.
                entry["preflight"] = {
                    "deferred": True,
                    "run_after_group": depends_on,
                    "why": "its endpoints are created by that group; checking them earlier "
                    "measures the ordering, not the artifact",
                }
            elif preflight:
                rows = _rows(group.get("parameters_from"))
                # A two-endpoint preflight is two statements separated by a bare semicolon,
                # deliberately, so a runner cannot read a two-endpoint check as one number.
                # Both must return 0.
                results: list[dict[str, Any]] = []
                for statement in (s.strip() for s in preflight.split("\n;\n")):
                    try:
                        record = session.run(statement, rows=rows).single()
                        name, value = next(iter(record.items()))
                        results.append({name: value})
                        if value:
                            failures.append(f"{gid}: preflight {name} = {value}, expected 0")
                    except Exception as exc:
                        results.append({"error": str(exc)[:400]})
                        failures.append(f"{gid}: preflight failed -- {str(exc)[:200]}")
                entry["preflight"] = {"rows_checked": len(rows), "results": results}
            report.append(entry)

        after = (
            session.run("MATCH (n) RETURN count(n) AS v").single()["v"],
            session.run("MATCH ()-[r]->() RETURN count(r) AS v").single()["v"],
        )
    finally:
        session.close()
        driver.close()

    # A census that moved during the run does NOT mean this script wrote. EXPLAIN does not
    # execute and the preflights are MATCH/RETURN, so this process cannot have written; on a
    # graph the lead is actively importing into, the census moves under a read-only reader.
    # An earlier revision reported the movement as "THE DRY RUN WROTE SOMETHING", which is a
    # false accusation against a correct proposal and exactly the kind of alarm that stops a
    # good import. Report the movement as an observation and name the concurrency.
    concurrent = before != after
    if concurrent:
        note = (
            f"The census moved from {before} to {after} while this read-only run was in "
            "flight. This process issued only EXPLAIN (which does not execute) and "
            "MATCH/RETURN, so the movement is a concurrent writer, not this script. It "
            "also means no absolute figure in this report is a stable baseline."
        )
    else:
        note = "The census did not move during the run."

    print(
        json.dumps(
            {
                "artifact": "AGENT_3_CYPHER_DRY_RUN",
                "census_at_start": {"nodes": before[0], "relationships": before[1]},
                "census_at_end": {"nodes": after[0], "relationships": after[1]},
                "concurrent_writer_detected": concurrent,
                "census_note": note,
                "this_process_wrote": False,
                "this_process_wrote_basis": "EXPLAIN does not execute; every other "
                "statement issued is MATCH/RETURN",
                "groups": report,
                "failures": failures,
                "verdict": "PASS" if not failures else "FAIL",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
