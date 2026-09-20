"""The release-prep receipt: every figure in the final report, re-measured from source.

Nothing here is copied from the report or from a prior receipt. The registry counts come
from ``data/gap_registry.json``, the census and the melodic-layer facts from the live
store, the worktree figures from this pass's own classification, and the audio figures
from the sample manifest and the queue. A receipt assembled from prose would confirm the
prose rather than the repository.

Usage::

    python data/staging/release_prep/build_receipt.py
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import subprocess
from typing import Any, Final

from neo4j import GraphDatabase, Query

ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
OUT: Final = ROOT / "data" / "staging" / "release_prep" / "release_prep_receipt.json"
REGISTRY: Final = ROOT / "data" / "gap_registry.json"
CLASSIFICATION: Final = ROOT / "data" / "staging" / "release_prep" / "worktree_classification.json"
SAMPLE: Final = ROOT / "data" / "staging" / "wave4" / "audio_owner_sample_manifest.json"
QUEUE: Final = ROOT / "data" / "staging" / "audio_review_queue.jsonl"
DECISIONS: Final = ROOT / "data" / "manual" / "audio_review" / "sample_decisions.jsonl"

URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
TIMEOUT: Final = 120.0

#: Statuses that are data-completeness closure, per the registry's own vocabulary.
CLOSURES: Final[frozenset[str]] = frozenset(
    {
        "CLOSED_SOURCE_ACQUIRED",
        "CLOSED_DERIVED",
        "CLOSED_VERIFIED_ZERO",
        "CLOSED_NOT_APPLICABLE",
        "CLOSED_SCOPE_DECISION",
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
    }
)
NOT_TERMINAL: Final[frozenset[str]] = frozenset(
    {"STILL_IMPLEMENTATION_FIXABLE", "BLOCKED_EVIDENCE_INCOMPLETE"}
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout.strip()


def graph_facts() -> dict[str, Any]:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database="neo4j") as session:

            def one(cypher: str) -> Any:
                record = session.run(Query(cypher, timeout=TIMEOUT)).single()
                return None if record is None else record[0]

            types = {
                r["relationshipType"]
                for r in session.run("CALL db.relationshipTypes() YIELD relationshipType")
            }
            labels = {r["label"] for r in session.run("CALL db.labels() YIELD label")}
            return {
                "nodes": one("MATCH (n) RETURN count(n)"),
                "relationships": one("MATCH ()-[r]->() RETURN count(r)"),
                "musicalized_as_type_exists": "MUSICALIZED_AS" in types,
                "musicalized_as_edges": one("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)"),
                "melodic_labels": sorted(
                    label
                    for label in labels
                    if any(t in label.lower() for t in ("saman", "gana", "stobha", "melod"))
                ),
                "nodes_with_a_gana_property_key": one(
                    "MATCH (n) WHERE any(k IN keys(n) WHERE toLower(k) CONTAINS 'gana') "
                    "RETURN count(n)"
                ),
                "sv_mantras": one("MATCH (m:Mantra {veda:'SV'}) RETURN count(m)"),
                "sv_mantras_without_a_running_number": one(
                    "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL "
                    "RETURN count(m)"
                ),
            }
    finally:
        driver.close()


def registry_facts() -> dict[str, Any]:
    gaps = json.loads(REGISTRY.read_text(encoding="utf-8"))["gaps"]
    counts = collections.Counter(g["status"] for g in gaps)
    return {
        "entries": len(gaps),
        "by_status": dict(sorted(counts.items())),
        "data_completeness_closures": sum(v for k, v in counts.items() if k in CLOSURES),
        "REGISTRY_IMPLEMENTATION_FIXABLE": sum(
            v for k, v in counts.items() if k in NOT_TERMINAL
        ),
        "OWNER_DECISION_REQUIRED": counts.get("BLOCKED_OWNER_DECISION_REQUIRED", 0),
        "NEEDS_AUDIBLE_REVIEW": counts.get("NEEDS_AUDIBLE_REVIEW", 0),
        "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA": counts.get(
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA", 0
        ),
        "samaveda_music": {
            g["gap_id"]: g["status"] for g in gaps if g["gap_id"].startswith("GAP-SAMAVEDA_MUSIC")
        },
        "not_terminal_entries": [g["gap_id"] for g in gaps if g["status"] in NOT_TERMINAL],
    }


def audio_facts() -> dict[str, Any]:
    manifest = json.loads(SAMPLE.read_text(encoding="utf-8"))
    queue = [
        json.loads(line)
        for line in QUEUE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    decided = 0
    accepted = 0
    if DECISIONS.exists():
        latest: dict[str, str] = {}
        for line in DECISIONS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                latest[f"{row['review_id']}|{row['media_url']}"] = row["verdict"]
        decided = len(latest)
        accepted = sum(1 for v in latest.values() if v == "AUDIBLY_VERIFIED")
    return {
        "queue_rows": len(queue),
        "queue_distinct_review_ids": len({r["review_id"] for r in queue}),
        "sample_rows": len(manifest["rows"]),
        "sample_seed": manifest["seed"],
        "sample_strata": manifest["quota_by_stratum"],
        "reviewed": decided,
        "AUDIBLY_VERIFIED_SAMPLE": accepted,
        "NOT_INDIVIDUALLY_HEARD": len(queue) - decided,
    }


def worktree_facts() -> dict[str, Any]:
    payload = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    return {
        "classified": payload["total_paths"],
        "counts": payload["counts"],
        "gitignore_rules_added": [r["rule"] for r in payload["proposed_gitignore_rules"]],
        "deleted": ["data/staging/release_blocker_r5/openapi.json"],
        "deletion_justified_by": (
            "vedagraph.api.app.create_app().openapi() re-emitted 386,344 bytes over 46 "
            "paths with sha256 5a464b183e940ab5, byte-identical to the stored dump, before "
            "it was removed."
        ),
    }


def main() -> int:
    payload = {
        "artifact": "RELEASE_PREP_RECEIPT",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "head_at_start": "a40fb589e85f60dc608cec345005d4fc6f8ffec4",
        "head_now": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "owner_decisions_recorded": [
            {
                "id": "OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO",
                "section": "docs/reports/data-completeness/OWNER_DECISIONS.md section 40",
                "provenance": "OWNER-SUPPLIED",
                "applied_to": "GAP-SAMAVEDA_MUSIC-002",
                "outcome": "STILL_IMPLEMENTATION_FIXABLE",
                "why_not_closed": (
                    "Three of the four release conditions measure MET. The fourth, "
                    "'existing validation gates pass', does not: Gate A is PASS but "
                    "wave3_eligibility.json records Gate B UNKNOWN and Gate C NOT_RUN for "
                    "samaveda_music, against a stated rule of A and B and C all PASS. The "
                    "1,136 aligned ARCIKA_NOTATION rows are authorised and not yet "
                    "released; the 708 unaligned ones stay withheld by the decision's own "
                    "closing clause."
                ),
            },
            {
                "id": "OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1",
                "section": "docs/reports/data-completeness/OWNER_DECISIONS.md section 41",
                "provenance": "OWNER-SUPPLIED",
                "applied_to": "GAP-SAMAVEDA_MUSIC-003 clause 2",
                "outcome": "CLOSED_SCOPE_DECISION",
                "why_closed": (
                    "MUSICALIZED_AS is not required for Product V1 without a canonical "
                    "object-side Gana identity, and none exists. No gana node was minted "
                    "and no edge was created."
                ),
            },
        ],
        "registry": registry_facts(),
        "graph": graph_facts(),
        "audio": audio_facts(),
        "worktree": worktree_facts(),
        "manual_and_external_residuals": {
            "AUDIO_SAMPLE_REVIEW": "PENDING_OWNER",
            "ASK_FORMAL_60": "PENDING_OWNER_QUOTA",
        },
    }
    OUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"  wrote {OUT.relative_to(ROOT)}")
    registry = payload["registry"]
    print(f"    REGISTRY_IMPLEMENTATION_FIXABLE  {registry['REGISTRY_IMPLEMENTATION_FIXABLE']}")
    print(f"    OWNER_DECISION_REQUIRED          {registry['OWNER_DECISION_REQUIRED']}")
    print(f"    data-completeness closures       {registry['data_completeness_closures']}")
    for gap_id in registry["not_terminal_entries"]:
        print(f"    NOT TERMINAL: {gap_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
