"""The attribution import: one module, one source of truth, three modes.

The owner's Phase C requires that the dry-run and the executor share one source of truth for
what will be written. The cheapest way to guarantee that is not discipline but structure:
this file holds the spec, and ``--plan``, ``--execute`` and ``--readback`` all read it. There
is no second list to drift.

What is imported, and what is not:

CENSUS -> three properties per passage, no nodes, no edges
    22,537 rows recording the state of rishi/devata/chandas attribution. Gate C checked all
    67,611 of those state assertions against the edges that actually exist and found zero
    contradictions, so the census is a true description of this graph.

    It lands as properties because it is not an assertion about the text. Its value is the
    distinction the graph currently cannot make: ASSESSED_SOURCE_ABSENT, where a source was
    consulted and says nothing, versus NEVER_ASSESSED, where nobody has looked. Without that,
    every absence reads as a verified zero -- which is the one thing this campaign has ruled
    out from the start.

WHITNEY -> nothing
    466 verse-level source assertions whose objects are verbatim printed strings that resolve
    to no node. An edge needs a node at the far end, and the only way to supply one is a
    normalized-string join, which is barred: normalization is a comparison instrument, not
    identity evidence. Retained, withheld, and registered as a blocker.

Usage:
    python scripts/attribution_import.py --plan
    python scripts/attribution_import.py --execute --backup DIR
    python scripts/attribution_import.py --readback
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

ROWS = pathlib.Path("data/staging/attribution/rows.jsonl")
GATE_B = pathlib.Path("data/staging/integration/attribution_gate_b.json")
GATE_C = pathlib.Path("data/staging/integration/attribution_gate_c.json")
PLAN_OUT = pathlib.Path("data/staging/integration/attribution_plan.json")
RECEIPT = pathlib.Path("data/staging/integration/attribution_import_receipt.json")
READBACK = pathlib.Path("data/staging/integration/attribution_readback.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

WAVE = "ATTRIBUTION"

#: The four corpus totals. They do not move, whatever an import does.
CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: The three dimensions, and the property each one's state lands under. Named per dimension
#: rather than packed into one blob so a reader -- and a Cypher query -- can ask about seers
#: without parsing anything.
DIMENSIONS: tuple[str, ...] = ("rishi", "devata", "chandas")


def state_property(dimension: str) -> str:
    return f"attribution_state_{dimension}"


def reason_property(dimension: str) -> str:
    return f"attribution_absence_reason_{dimension}"


#: Every state the census may report. An unknown one raises rather than being written: a
#: state nobody declared would reach the reader's surface wearing the authority of the four
#: that were checked.
DECLARED_STATES: frozenset[str] = frozenset(
    {
        "SOURCE_EXPLICIT_PRESENT",
        "DERIVED_PRESENT",
        "ASSESSED_SOURCE_ABSENT",
        "NEVER_ASSESSED",
        "NOT_APPLICABLE_AT_THIS_GRANULARITY",
    }
)

#: States that record an ABSENCE, and therefore must carry a reason code. The whole point of
#: importing the census is that these two are different from each other and from silence.
ABSENCE_STATES: frozenset[str] = frozenset(
    {"ASSESSED_SOURCE_ABSENT", "NOT_APPLICABLE_AT_THIS_GRANULARITY"}
)


class UndeclaredState(RuntimeError):
    """A census state with no declaration. Raised, never defaulted."""


def read_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in ROWS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_payload() -> list[dict[str, Any]]:
    """The exact rows this import will write. The single source of truth.

    Returns one dict per passage carrying the three state properties and any reason codes.
    Called by the plan, the executor and the readback, so all three describe the same write.
    """
    payload: list[dict[str, Any]] = []
    for row in read_rows():
        if row.get("evidence_layer") != "DETERMINISTIC_DERIVED":
            continue  # Whitney: withheld, see the module docstring.
        props: dict[str, Any] = {}
        for dimension in DIMENSIONS:
            block = row["payload"].get(dimension) or {}
            state = str(block.get("state") or "")
            if not state:
                continue
            if state not in DECLARED_STATES:
                raise UndeclaredState(
                    f"{row.get('canonical_key')}:{dimension} reports {state!r}, which is not "
                    "in DECLARED_STATES. Declare it deliberately or fix the artifact."
                )
            props[state_property(dimension)] = state
            reason = block.get("absence_reason_code")
            if state in ABSENCE_STATES:
                if not reason:
                    raise UndeclaredState(
                        f"{row.get('canonical_key')}:{dimension} records an absence with no "
                        "reason code. An untyped absence is what this import exists to stop."
                    )
                props[reason_property(dimension)] = str(reason)
        if props:
            props["attribution_census_source"] = str(row.get("source_id") or "")
            payload.append({"key": str(row["canonical_key"]), "props": props})
    return payload


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "core": {
            r["veda"]: int(r["n"])
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def gates_pass() -> tuple[bool, dict[str, Any]]:
    """Both gates, read from their own artifacts. Neither is restated here."""
    b = json.loads(GATE_B.read_text(encoding="utf-8")) if GATE_B.exists() else {}
    c = json.loads(GATE_C.read_text(encoding="utf-8")) if GATE_C.exists() else {}
    detail = {
        "gate_b_verdict": b.get("verdict"),
        "gate_b_failed_checks": b.get("checks_failed"),
        "gate_c_verdict": c.get("verdict"),
        "gate_c_census_contradicted": c.get("census_contradicted"),
        "gate_c_defect_class": c.get("defect_class"),
    }
    # Gate B's one finding is the Whitney object resolution, and this import writes no
    # Whitney row. That is why it is a precondition on the CENSUS half only: Gate C's census
    # contradiction count must be exactly 0, and its defect class must be NONE.
    # Read explicitly. `int(x or -1)` maps a correct 0 to -1, because 0 is falsy and 0 is
    # the passing value -- so a clean Gate C could not satisfy its own precondition. A key
    # that is ABSENT is still a failure, and that is what the None check preserves.
    contradicted = c.get("census_contradicted")
    b_failed = b.get("checks_failed")
    ok = (
        c.get("verdict") == "GATE_C_PASS"
        and contradicted is not None
        and int(contradicted) == 0
        and c.get("defect_class") == "NONE"
        and b_failed is not None
        and int(b_failed) <= 1
    )
    detail["preconditions_met"] = ok
    return ok, detail


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def promise(payload: list[dict[str, Any]], before: dict[str, Any]) -> dict[str, Any]:
    """The exact delta this import claims. Computed from the payload, never typed."""
    property_writes = sum(len(row["props"]) for row in payload)
    return {
        "nodes_create": 0,
        "nodes_update": len(payload),
        "nodes_retire": 0,
        "relationships_create": 0,
        "relationships_update": 0,
        "relationships_retire": 0,
        "property_writes": property_writes,
        "nodes_before": before["nodes"],
        "nodes_after": before["nodes"],
        "relationships_before": before["relationships"],
        "relationships_after": before["relationships"],
        "core_corpus_must_not_move": True,
        "note": (
            "Properties only. This import creates and deletes nothing, so both census "
            "figures are unchanged by construction and any movement in either is a defect."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--readback", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    payload = build_payload()
    ok, gate_detail = gates_pass()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            expected = promise(payload, before)

            if args.readback:
                return do_readback(session, payload, expected)

            print()
            mode = "EXECUTING" if args.execute else "PLAN"
            print(f"  ATTRIBUTION IMPORT  {mode}")
            print()
            print(f"  before: {before['nodes']:,} nodes / "
                  f"{before['relationships']:,} relationships")
            print(f"  passages to update      {len(payload):,}")
            print(f"  property writes         {expected['property_writes']:,}")
            print("  nodes/edges created     0 / 0")
            print()
            for name, value in gate_detail.items():
                print(f"  {name:34} {value}")
            print()

            clean_tree = git("status", "--porcelain") == ""
            print(f"  working tree clean      {clean_tree}")
            if args.execute:
                if not ok:
                    print("\n  GATES NOT GREEN. Nothing written.")
                    return 1
                if not clean_tree:
                    print("\n  Working tree is dirty. Commit before a canonical write.")
                    return 1
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("\n  --backup must name an existing verified dump directory.")
                    return 1

            written = 0
            if args.execute:
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                for i in range(0, len(payload), 2000):
                    chunk = payload[i : i + 2000]
                    with session.begin_transaction() as tx:
                        written += int(
                            tx.run(
                                "UNWIND $rows AS row "
                                "MATCH (p:Passage {canonical_key: row.key}) "
                                "SET p += row.props, p.attribution_wave = $wave, "
                                "    p.attribution_applied_at = $at "
                                "RETURN count(DISTINCT p) AS n",
                                rows=chunk,
                                wave=WAVE,
                                at=stamp,
                            ).single()["n"]
                        )
                        tx.commit()

            after = census(session)
            receipt = {
                "artifact": "ATTRIBUTION_IMPORT_RECEIPT",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "git_commit": git("rev-parse", "HEAD"),
                "working_tree_clean": clean_tree,
                "gates": gate_detail,
                "promised": expected,
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "core_corpus_unchanged": after["core"] == CORE,
                "passages_updated": written,
                "passages_promised": len(payload),
                "matched_the_promise": (
                    after["nodes"] == before["nodes"]
                    and after["relationships"] == before["relationships"]
                    and (not args.execute or written == len(payload))
                ),
                "withheld": {
                    "WHITNEY_INDEX": {
                        "rows": 466,
                        "reason": (
                            "entity_resolution_method = VERBATIM_SOURCE_STRING_NOT_RESOLVED "
                            "on every row. The object is a printed Sanskrit string that "
                            "resolves to no node, and the only way to supply one is a "
                            "normalized-string join, which is barred."
                        ),
                        "classification": "RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT",
                    }
                },
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            target = RECEIPT if args.execute else PLAN_OUT
            target.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print()
            print(f"  after: {after['nodes']:,} nodes / "
                  f"{after['relationships']:,} relationships"
                  f"  (nodes {receipt['node_delta']:+}, "
                  f"relationships {receipt['relationship_delta']:+})")
            print(f"  core corpus unchanged   {receipt['core_corpus_unchanged']}")
            if args.execute:
                print(f"  passages updated        {written:,} of {len(payload):,}")
            print(f"  matched the promise     {receipt['matched_the_promise']}")
            print()
            print(f"  receipt: {target}")
            if not args.execute:
                print()
                print("  PLAN ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["matched_the_promise"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


def do_readback(
    session: Session, payload: list[dict[str, Any]], expected: dict[str, Any]
) -> int:
    """Read the result out of the database. The closure event, not the import's own report."""
    findings: list[str] = []
    landed = int(
        session.run(
            f"MATCH (p:Passage) WHERE p.attribution_wave = '{WAVE}' RETURN count(p) AS c"
        ).single()["c"]
    )
    if landed != len(payload):
        findings.append(f"{len(payload)} passages promised, {landed} carry the stamp")

    for dimension in DIMENSIONS:
        prop = state_property(dimension)
        row = session.run(
            f"MATCH (p:Passage) WHERE p.{prop} IS NOT NULL "
            f"RETURN count(p) AS total, collect(DISTINCT p.{prop}) AS states"
        ).single()
        states = {str(s) for s in (row["states"] or [])}
        undeclared = states - DECLARED_STATES
        if undeclared:
            findings.append(f"{dimension}: undeclared states in the graph {sorted(undeclared)}")
        # Every absence must be able to say why.
        untyped = int(
            session.run(
                f"MATCH (p:Passage) WHERE p.{prop} IN $absent "
                f"AND p.{reason_property(dimension)} IS NULL RETURN count(p) AS c",
                absent=sorted(ABSENCE_STATES),
            ).single()["c"]
        )
        if untyped:
            findings.append(f"{dimension}: {untyped} absences carry no reason code")

    counts = {
        dimension: {
            str(r["state"]): int(r["n"])
            for r in session.run(
                f"MATCH (p:Passage) WHERE p.{state_property(dimension)} IS NOT NULL "
                f"RETURN p.{state_property(dimension)} AS state, count(*) AS n ORDER BY n DESC"
            )
        }
        for dimension in DIMENSIONS
    }

    live = census(session)
    if live["core"] != CORE:
        findings.append(f"core corpus moved: {live['core']}")
    if live["nodes"] != expected["nodes_after"]:
        findings.append(f"node census {live['nodes']} != promised {expected['nodes_after']}")
    if live["relationships"] != expected["relationships_after"]:
        findings.append(
            f"relationship census {live['relationships']} != "
            f"promised {expected['relationships_after']}"
        )

    report = {
        "artifact": "ATTRIBUTION_READBACK",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "passages_stamped": landed,
        "passages_promised": len(payload),
        "state_distribution_read_from_the_graph": counts,
        "census": live,
        "findings": findings,
        "verdict": "READBACK_CLEAN" if not findings else "READBACK_DEFECT",
    }
    READBACK.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  ATTRIBUTION READBACK -- read out of canonical Neo4j")
    print()
    print(f"  passages stamped   {landed:,} of {len(payload):,}")
    print(f"  census             {live['nodes']:,} nodes / {live['relationships']:,} rels")
    print(f"  core corpus        {live['core'] == CORE}")
    print()
    for dimension, states in counts.items():
        print(f"  {dimension}")
        for state, n in states.items():
            print(f"    {state:40} {n:>7,}")
    print()
    if findings:
        for f in findings:
            print(f"    - {f}")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {READBACK}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
