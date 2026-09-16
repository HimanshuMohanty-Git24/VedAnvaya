"""Wave 4 Phase 0: freeze the state before attacking it.

Everything here is measured, including the figures the Wave 4 brief supplied. The brief says
"verify these yourself before using them", and a baseline that copies its own inputs would
make every later comparison circular -- which is the defect class this whole round exists to
hunt.

The graph fingerprint is deliberately NOT a whole-graph digest of every property. It is a
structural census -- per-label node counts, per-predicate edge counts, and the four corpus
totals -- because that is what a rebuild or a stray mutation moves, and it can be recomputed
cheaply enough to compare at the end of the round.

Nothing here mutates.

Usage:
    python scripts/wave4_baseline.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

OUT = pathlib.Path("data/staging/wave4")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: What the Wave 4 brief asserts. Recorded so the baseline can DISAGREE with it in writing
#: rather than silently adopting it.
CLAIMED = {
    "nodes": 116_838,
    "relationships": 281_257,
    "core": {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839},
    "core_total": 20_210,
}

#: Backups that should exist and be restorable. Existence and checksum are verifiable here;
#: restorability is asserted from the round-three and round-four restore records, and is not
#: re-tested, because a restore would destroy the state this round is auditing.
BACKUPS = (
    "D:/vedanvaya-backups/round4-pre-m9-20260916T124347/neo4j.dump",
    "D:/vedanvaya-backups/round4-pre-m8-20260916T112837/neo4j.dump",
    "D:/vedanvaya-backups/wave3-final-baseline-20260916T101224/neo4j.dump",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def fingerprint(session: Session) -> dict[str, Any]:
    labels = {
        str(row["label"]): int(row["n"])
        for row in session.run(
            "CALL db.labels() YIELD label "
            "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS n } "
            "RETURN label, n ORDER BY label"
        )
    }
    types = {
        str(row["t"]): int(
            session.run(f"MATCH ()-[r:`{row['t']}`]->() RETURN count(r) AS c").single()["c"]
        )
        for row in session.run(
            "CALL db.relationshipTypes() YIELD relationshipType AS t RETURN t ORDER BY t"
        )
    }
    core = {
        str(row["veda"]): int(row["n"])
        for row in session.run(
            "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
        )
    }
    structure = {"labels": labels, "relationship_types": types, "core_corpus": core}
    return {
        "structure": structure,
        "sha256": digest(structure),
        "distinct_labels": len(labels),
        "distinct_relationship_types": len(types),
        "populated_relationship_types": sum(1 for n in types.values() if n > 0),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
            public = int(
                session.run(
                    "MATCH (n) WHERE NOT n:Internal RETURN count(n) AS c"
                ).single()["c"]
            )
            fp = fingerprint(session)
            constraints = sorted(
                str(row["name"])
                for row in session.run("SHOW CONSTRAINTS YIELD name RETURN name")
            )
    finally:
        driver.close()

    core = fp["structure"]["core_corpus"]
    disagreements: list[str] = []
    if nodes != CLAIMED["nodes"]:
        disagreements.append(f"nodes: claimed {CLAIMED['nodes']}, measured {nodes}")
    if rels != CLAIMED["relationships"]:
        disagreements.append(
            f"relationships: claimed {CLAIMED['relationships']}, measured {rels}"
        )
    if core != CLAIMED["core"]:
        disagreements.append(f"core corpus: claimed {CLAIMED['core']}, measured {core}")
    if sum(core.values()) != CLAIMED["core_total"]:
        disagreements.append(
            f"core total: claimed {CLAIMED['core_total']}, measured {sum(core.values())}"
        )

    baseline = {
        "artifact": "WAVE4_BASELINE",
        "at": now,
        "census": {"nodes": nodes, "relationships": rels, "public_nodes": public},
        "core_corpus": core,
        "core_total": sum(core.values()),
        "claimed_by_the_brief": CLAIMED,
        "disagreements_with_the_brief": disagreements,
        "brief_verified": not disagreements,
        "uniqueness_constraints": len(constraints),
        "constraint_names": constraints,
    }

    backups = []
    for path in BACKUPS:
        p = pathlib.Path(path)
        entry: dict[str, Any] = {"path": path, "exists": p.exists()}
        if p.exists():
            entry["bytes"] = p.stat().st_size
            entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        backups.append(entry)
    baseline["backups"] = backups
    baseline["at_least_one_backup_present"] = any(b["exists"] for b in backups)

    dependency = pathlib.Path("data/staging/integration/dependency_status.json")
    dep = json.loads(dependency.read_text(encoding="utf-8")) if dependency.exists() else {}
    dep_snapshot = {
        "artifact": "WAVE4_DEPENDENCY_SNAPSHOT",
        "at": now,
        "counts": dep.get("counts"),
        "unexplained_stale": dep.get("unexplained_stale"),
        "consumers": [
            {
                "consumer": row.get("consumer"),
                "status": row.get("status"),
                "current_input_digest": row.get("current_input_digest"),
                "recorded_input_digest": row.get("recorded_input_digest"),
                "output_hash": row.get("output_hash"),
                "reason": row.get("reason"),
            }
            for row in dep.get("consumers") or []
        ],
    }

    registry = json.loads(
        pathlib.Path("data/gap_registry.json").read_text(encoding="utf-8")
    )
    gaps = registry["gaps"]
    status_counts: dict[str, int] = {}
    for gap in gaps:
        status_counts[str(gap.get("status"))] = status_counts.get(str(gap.get("status")), 0) + 1
    registry_snapshot = {
        "artifact": "WAVE4_REGISTRY_SNAPSHOT",
        "at": now,
        "total_entries": len(gaps),
        "by_status": status_counts,
        "gap_ids": sorted(str(g["gap_id"]) for g in gaps),
        "sha256": digest(gaps),
    }

    git_snapshot = {
        "artifact": "WAVE4_GIT_SNAPSHOT",
        "at": now,
        "head": git("rev-parse", "HEAD"),
        "head_subject": git("log", "-1", "--format=%s"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "working_tree_clean": git("status", "--porcelain") == "",
        "porcelain": git("status", "--porcelain"),
    }

    for name, payload in (
        ("baseline.json", baseline),
        ("graph_fingerprint.json", fp),
        ("dependency_snapshot.json", dep_snapshot),
        ("registry_snapshot.json", registry_snapshot),
        ("git_snapshot.json", git_snapshot),
    ):
        (OUT / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    print()
    print("  WAVE 4 BASELINE -- measured, not inherited")
    print()
    print(f"  HEAD                 {git_snapshot['head'][:12]} "
          f"({'clean' if git_snapshot['working_tree_clean'] else 'DIRTY'})")
    print(f"  nodes                {nodes:,}")
    print(f"  relationships        {rels:,}")
    print(f"  public nodes         {public:,}")
    print(f"  core corpus          {core} = {sum(core.values()):,}")
    print(f"  fingerprint          {fp['sha256'][:16]}")
    print(f"  labels / types       {fp['distinct_labels']} / "
          f"{fp['populated_relationship_types']} populated of "
          f"{fp['distinct_relationship_types']}")
    print(f"  uniqueness constraints {len(constraints)}")
    print()
    print(f"  brief verified       {baseline['brief_verified']}")
    for line in disagreements:
        print(f"    DISAGREES: {line}")
    print(f"  backups present      "
          f"{sum(1 for b in backups if b['exists'])} of {len(backups)}")
    print(f"  dependency           {dep_snapshot['counts']}")
    print(f"  registry             {len(gaps)} entries {status_counts}")
    print()
    print(f"  written to {OUT}")
    return 0 if not disagreements else 1


if __name__ == "__main__":
    raise SystemExit(main())
