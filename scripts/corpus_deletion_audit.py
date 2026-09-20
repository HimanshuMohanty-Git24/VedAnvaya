"""The exact identity and reason for every node this campaign deleted. Owner decision 1.

The owner ratified three deletion batches and asked that the exact IDs and the reason for
each be in the audit trail. They were described in prose and counted, never enumerated.

This reconstructs them deterministically rather than from memory. The withholding rule is in
the plan, so the set of keys the plan refuses is recomputable at any time; a key the plan
refuses and the graph does not hold is a key this campaign removed. Each is then attributed
to the rule that first excluded it, because the rule changed twice and the batches are the
three versions of it:

BATCH_1  evidence the import does not carry
    12 registry entities attested only in a Brahmana or Srautasutra. That evidence lives in
    ritual/supplementary_passages.jsonl, which is declared not-imported, so importing the
    entity while excluding its evidence asserts what the graph cannot support.

BATCH_2  a claim of attestation with no locator
    2 officiant roles carrying samhita_attested with no example recorded. roles.jsonl has no
    attestation-example field at all. An entity claiming attestation it cannot point at is
    weaker than an absent one.

BATCH_3  reachable only through an edge the import refuses
    27 registry entities whose only path into the graph was a rite edge staged PROBABLE.
    Reachability had been computed over the artifact's full row set rather than over the
    rows that would actually become edges.

All three share the properties the owner ratified: created by this campaign, unsupported
after the importability filter, edgeless after it, and recoverable from the verified dump.

Nothing here writes to the graph.

Usage:
    python scripts/corpus_deletion_audit.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase
from wave3_import_plan import (
    GROUPS,
    NOT_IMPORTABLE,
    STAGING,
    get_path,
    passes,
    read_jsonl,
)

OUT = pathlib.Path("data/staging/integration/corpus_deletion_audit.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The rite-edge artifacts and the fields in each that name a registry entity. The same
#: files the plan's reachability reads, listed here so both versions of the rule can be
#: replayed: over every row, and over only the rows that survive the importability filter.
RITE_EDGE_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "rite_edges.jsonl",
        ("ritual_key", "action_key", "object_key", "offering_key", "material_key"),
    ),
    ("role_assignments.jsonl", ("ritual_key", "role_key")),
    ("rite_relations.jsonl", ("child_ritual_key", "parent_ritual_key")),
    ("steps.jsonl", ("ritual_key",)),
)


def rite_edge_referents(*, only_importable: bool) -> set[str]:
    """Keys a rite edge names, over either the full row set or the importable one.

    The difference between these two sets is precisely batch 3: entities that looked
    reachable while reachability was computed over rows the import would go on to refuse.
    """
    keys: set[str] = set()
    root = STAGING / "ritual"
    for filename, fields in RITE_EDGE_SOURCES:
        for row in read_jsonl(root / filename):
            if only_importable and str(row.get("mapping_confidence") or "") in NOT_IMPORTABLE:
                continue
            for field in fields:
                if row.get(field):
                    keys.add(str(row[field]))
    return keys


#: The two roles that were batch 2, named because the rule that removed them -- "an
#: attestation claim needs a locator" -- cannot be replayed from the current plan: the plan
#: no longer has the intermediate version that accepted the flag alone.
BATCH_2_KEYS: tuple[str, ...] = (
    "VG:CONCEPT:SADASYA-PRIEST",
    "VG:CONCEPT:SAMITR-BUTCHER",
)

#: What the owner ratified, per batch. The replay must reproduce these exactly; a split
#: that merely sums to 41 is not evidence that each key is attributed to the right rule.
RATIFIED: dict[str, int] = {
    "BATCH_1_EVIDENCE_NOT_IMPORTED": 12,
    "BATCH_2_ATTESTATION_WITHOUT_LOCATOR": 2,
    "BATCH_3_REACHABLE_ONLY_VIA_A_REFUSED_EDGE": 27,
}

BATCH_REASONS: dict[str, str] = {
    "BATCH_1_EVIDENCE_NOT_IMPORTED": (
        "Attested only in a Brahmana or Srautasutra. That evidence lives in "
        "ritual/supplementary_passages.jsonl, which this wave declares not-imported, so the "
        "entity would assert what the graph cannot support."
    ),
    "BATCH_2_ATTESTATION_WITHOUT_LOCATOR": (
        "Carried samhita_attested with no example recorded; roles.jsonl has no "
        "attestation-example field at all, so the claim cannot be located."
    ),
    "BATCH_3_REACHABLE_ONLY_VIA_A_REFUSED_EDGE": (
        "Named only by a rite edge staged PROBABLE. Once the importability filter refused "
        "those edges, the entity's only path into the graph was an edge nobody would write."
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    # Every key the current plan refuses, and why, recomputed from the artifacts.
    withheld: dict[str, dict[str, Any]] = {}
    for group in GROUPS:
        if not group.require_reachable_evidence:
            continue
        filename = group.source.split(":", 1)[0]
        for row in read_jsonl(STAGING / group.domain / filename):
            key = str(get_path(row, group.identity_fields[0]) or "")
            if not key or passes(row, group):
                continue
            withheld[key] = {
                "entity_key": key,
                "group": group.group_id,
                "label_en": row.get("label_en") or row.get("name") or None,
                "samhita_attested": bool(row.get("samhita_attested")),
                "has_attestation_example": bool(row.get("samhita_attestation_examples")),
            }

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            present = {
                str(r["k"])
                for r in session.run(
                    "UNWIND $keys AS k MATCH (n {entity_key: k}) RETURN DISTINCT k",
                    keys=sorted(withheld),
                )
            }
            census = dict(
                session.run(
                    "MATCH (n) RETURN count(n) AS nodes"
                ).single()
                or {}
            )
    finally:
        driver.close()

    deleted = {k: v for k, v in withheld.items() if k not in present}

    # Attribute each to the rule that first excluded it, by replaying both rules rather
    # than inferring from a flag. An earlier version used samhita_attested as a proxy and
    # split the 41 as 32/2/7 against the ratified 12/2/27.
    reachable_over_all_rows = rite_edge_referents(only_importable=False)
    reachable_over_importable_rows = rite_edge_referents(only_importable=True)
    for key, record in deleted.items():
        record["named_by_any_rite_edge"] = key in reachable_over_all_rows
        record["named_by_an_importable_rite_edge"] = key in reachable_over_importable_rows
        if key in BATCH_2_KEYS:
            record["batch"] = "BATCH_2_ATTESTATION_WITHOUT_LOCATOR"
        elif record["named_by_any_rite_edge"]:
            # It passed the original rule and failed only once reachability was computed
            # over the edges that would actually be written.
            record["batch"] = "BATCH_3_REACHABLE_ONLY_VIA_A_REFUSED_EDGE"
        else:
            record["batch"] = "BATCH_1_EVIDENCE_NOT_IMPORTED"
        record["reason"] = BATCH_REASONS[record["batch"]]

    batches: dict[str, list[str]] = {}
    for key, record in sorted(deleted.items()):
        batches.setdefault(str(record["batch"]), []).append(key)

    report = {
        "artifact": "CORPUS_DELETION_AUDIT",
        "owner_decision": "section 1 -- deletions ratified, enumeration required",
        "recoverable_from": "D:/vedanvaya-backups/wave3-pre-import-20260915T155144/neo4j.dump",
        "graph_nodes_now": census.get("nodes"),
        "keys_the_plan_withholds": len(withheld),
        "of_those_still_present_in_the_graph": len(present),
        "of_those_deleted": len(deleted),
        "batch_reasons": BATCH_REASONS,
        "batches": {name: {"count": len(keys), "keys": keys} for name, keys in batches.items()},
        "every_deleted_key_is_withheld_by_the_current_plan": True,
        "ratified_counts": RATIFIED,
        "replay_reproduces_the_ratified_counts": {
            name: len(batches.get(name, [])) == expected for name, expected in RATIFIED.items()
        },
        "note": (
            "A key is listed here because the current plan refuses it AND the graph does not "
            "hold it. Both halves are recomputed, so this file cannot drift from the plan: "
            "if a future change made one of these importable again, it would leave this list."
        ),
    }
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  CORPUS DELETION AUDIT -- nothing written to the graph")
    print()
    print(f"  keys the plan withholds      {len(withheld)}")
    print(f"  still present in the graph   {len(present)}")
    print(f"  deleted by this campaign     {len(deleted)}")
    print()
    ok = True
    for name, expected in sorted(RATIFIED.items()):
        found = len(batches.get(name, []))
        mark = "ok  " if found == expected else "MISMATCH"
        ok = ok and found == expected
        print(f"  {mark} {name:44} {found:>3}  (ratified {expected})")
    if not ok:
        print()
        print("  The replay does not reproduce the ratified split. The attribution is wrong.")
    print()
    print(f"  report: {args.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
