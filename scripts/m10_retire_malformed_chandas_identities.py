"""M10: the 28 malformed metre identities were still reader-visible. Wave 4 finding.

M9 withdrew the 33 assertions that claimed a bracket fragment was a verse's metre. It left
the 28 ``:Chandas`` entities in place on purpose, so the printed literal would survive.

**What M9 did not check is whether those entities were public.** They are.
``frontend/.world/world.raw.json`` carries all 28, typed ``Chandas``, so a reader browsing
the Knowledge World is shown

    '3-av. 6-p. virāḍ atijagatī: 24. 5-p. virāḍ atijagatī'
    '3-p. pipīlikamadhyā purauṣṇih: 1-11. ekāvasāna'
    '2. bhurij'

as Vedic metres. Removing the assertion and leaving the object on the shelf fixed the
sentence and left the noun.

**The fix is the M8 pattern, not deletion.** Marking them ``:Internal`` removes them from
every public surface through the one clause the product/internal boundary is written as
(``NOT n:Internal``), while destroying nothing: the entity, its ``preferred_label`` and its
``source_variants`` stay, and M9's 33 withheld-claim records keep resolving. Deleting them
would be an identity-changing migration and needs an owner decision; demoting them does not,
and it is the mechanism the owner already ratified for real graph content that is not
product knowledge.

They are *retired identities*: the corrected Wave 4 builder no longer emits them, so a
regenerated ``chandas_av.yaml`` holds 513 entities rather than 541, and these 28 exist in the
graph only as the referents of a historical record.

Criterion: Whitney's own notation, the same as M9's -- a colon separates a statement from its
per-verse exceptions, and a bare ``N.`` is a verse address. Neither can occur inside a metre
name.

Usage:
    python scripts/m10_retire_malformed_chandas_identities.py [--execute] [--backup DIR]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

from vedagraph.domain.ontology import LABEL_INTERNAL

#: The registry as it stood BEFORE the Wave 4 builder fix. The corrected builder no longer
#: emits these 28, so the current registry no longer names them -- and the set has to be read
#: from the pre-fix snapshot or it cannot be identified at all.
SNAPSHOT = pathlib.Path("data/staging/wave4/pre_phase3_backup/chandas_av.yaml")
LIVE_REGISTRY = pathlib.Path("data/registry/chandas_av.yaml")
OUT = pathlib.Path("data/staging/integration/m10_receipt.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}
REASON = "RETIRED_IDENTITY_NOT_A_METRE_NAME"
GAP = "GAP-AV-CHANDOMETRE-SEGMENTATION-001"

_VERSE_ADDRESS = re.compile(r"(?<![0-9a-zA-Z-])\d{1,2}\.\s")


def malformed_keys(path: pathlib.Path) -> dict[str, str]:
    """Entity key -> printed label, for labels that cannot be a metre name."""
    entities = yaml.safe_load(path.read_text(encoding="utf-8"))["entities"]
    return {
        str(e["entity_key"]): str(e["preferred_label"])
        for e in entities
        if ":" in str(e["preferred_label"]) or _VERSE_ADDRESS.search(str(e["preferred_label"]))
    }


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
        "public_chandas": int(
            session.run(
                f"MATCH (c:Chandas) WHERE NOT c:{LABEL_INTERNAL} RETURN count(c) AS c"
            ).single()["c"]
        ),
        "core": {
            r["veda"]: int(r["n"])
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    if not SNAPSHOT.exists():
        print(f"  {SNAPSHOT} is missing; the pre-fix registry is the only place these 28 "
              "identities are enumerated.")
        return 1
    targets = malformed_keys(SNAPSHOT)
    still_emitted = (
        set(targets) & set(malformed_keys(LIVE_REGISTRY)) if LIVE_REGISTRY.exists() else set()
    )

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            row = session.run(
                "UNWIND $keys AS k MATCH (c:Chandas {entity_key: k}) "
                f"RETURN count(c) AS present, "
                f"sum(CASE WHEN c:{LABEL_INTERNAL} THEN 1 ELSE 0 END) AS marked, "
                "sum(CASE WHEN (c)--() THEN 1 ELSE 0 END) AS with_edges",
                keys=sorted(targets),
            ).single()
            present = int(row["present"])
            marked = int(row["marked"])
            with_edges = int(row["with_edges"])
            referenced = int(
                session.run(
                    "UNWIND $keys AS k MATCH (p:Passage) "
                    "WHERE p.chandas_withheld_entity_key = k RETURN count(p) AS c",
                    keys=sorted(targets),
                ).single()["c"]
            )

            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  M10 RETIRE MALFORMED CHANDAS IDENTITIES  {mode}")
            print()
            print(f"  before: {before['nodes']:,} nodes, {before['public_nodes']:,} public, "
                  f"{before['public_chandas']} public :Chandas")
            print(f"  malformed identities in the pre-fix registry  {len(targets)}")
            print(f"  present in the graph                          {present}")
            print(f"  already :Internal                             {marked}")
            print(f"  still carrying an edge                        {with_edges}")
            print(f"  M9 withheld records pointing at them          {referenced}")
            print(f"  still emitted by the corrected builder        {len(still_emitted)}")
            print()

            if with_edges:
                print(f"  REFUSING: {with_edges} still carry an edge. M9 was supposed to "
                      "withdraw every assertion first; demoting a node that an edge still "
                      "reaches would hide a live claim rather than retire a dead identity.")
                return 1
            if still_emitted:
                print(f"  REFUSING: the corrected builder still emits {len(still_emitted)} of "
                      "these, so they are not retired and demoting them would diverge the "
                      "graph from its own source registry.")
                return 1

            written = 0
            if args.execute and present > marked:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                with session.begin_transaction() as tx:
                    written = int(
                        tx.run(
                            "UNWIND $keys AS k MATCH (c:Chandas {entity_key: k}) "
                            f"WHERE NOT c:{LABEL_INTERNAL} "
                            f"SET c:{LABEL_INTERNAL}, c.retired_reason = $reason, "
                            "    c.retired_gap = $gap, c.m10_applied = $at "
                            "RETURN count(c) AS n",
                            keys=sorted(targets),
                            reason=REASON,
                            gap=GAP,
                            at=stamp,
                        ).single()["n"]
                    )
                    tx.commit()

            after = census(session)
            leaked = int(
                session.run(
                    "UNWIND $keys AS k MATCH (c:Chandas {entity_key: k}) "
                    f"WHERE NOT c:{LABEL_INTERNAL} RETURN count(c) AS c",
                    keys=sorted(targets),
                ).single()["c"]
            )
            literals_intact = int(
                session.run(
                    "UNWIND $keys AS k MATCH (c:Chandas {entity_key: k}) "
                    "WHERE c.preferred_label IS NOT NULL RETURN count(c) AS c",
                    keys=sorted(targets),
                ).single()["c"]
            )

            receipt = {
                "migration": "M10_RETIRE_MALFORMED_CHANDAS_IDENTITIES",
                "gap": GAP,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "wave4_finding": (
                    "M9 withdrew the assertions and left the objects public. All 28 appeared "
                    "in frontend/.world/world.raw.json typed Chandas, so a reader browsing "
                    "the Knowledge World was shown a bracket fragment as a Vedic metre."
                ),
                "criterion": "Whitney's notation: a colon, or a bare N. verse address",
                "identities": [
                    {"entity_key": key, "printed_label": label}
                    for key, label in sorted(targets.items())
                ],
                "present_in_graph": present,
                "nodes_marked": written,
                "still_public": leaked,
                "printed_literals_intact": literals_intact,
                "m9_records_still_resolving": referenced,
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "public_node_delta": after["public_nodes"] - before["public_nodes"],
                "core_corpus_unchanged": after["core"] == CORE,
                "additive": after["nodes"] == before["nodes"]
                and after["relationships"] == before["relationships"],
                "complete": leaked == 0 and literals_intact == present,
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print(f"  after: {after['nodes']:,} nodes, {after['public_nodes']:,} public "
                  f"(delta {receipt['public_node_delta']:+}), "
                  f"{after['public_chandas']} public :Chandas")
            print(f"  still public               {leaked}")
            print(f"  printed literals intact    {literals_intact} of {present}")
            print(f"  core corpus unchanged      {receipt['core_corpus_unchanged']}")
            print(f"  additive                   {receipt['additive']}")
            print(f"  complete                   {receipt['complete']}")
            print()
            print(f"  receipt: {OUT}")
            if not args.execute:
                print("\n  REHEARSAL ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["additive"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
