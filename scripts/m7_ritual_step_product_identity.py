"""M7: give :RitualStep a product identity the generic graph can resolve. Owner section 2.

The step layer arrived in Wave 3 with a complete deterministic identity already on every
node -- ``step_key``, ``canonical_urn`` and a ``uuid5`` ``entity_id`` -- and with no
``display_type``. ``display_type`` is what ``PRODUCT_TYPE_BY_DISPLAY_TYPE`` is keyed on and
what every non-internal node in this graph is contracted to carry, so its absence, not the
identity, is why ``HAS_RITUAL_STEP`` is refused by ``/api/v1/graph``.

This migration writes one property. It invents no identity: the grain question the owner
asked was answered by measurement in ``scripts/ritual_step_identity_probe.py`` and the answer
was that the staged key is already right.

    grain                       distinct   values covering rows that DISAGREE
    SOURCE_OCCURRENCE              2,767   308
    RITE_SPECIFIC_OCCURRENCE       3,122   1
    POSITION_BASED                 1,137   680

A source-occurrence key would merge 308 identities that stand for different claims, because
one sutra is cited for several rites. A position-based key fails outright: ``step_position``
restarts at 1 inside every work. The grain is RITE_SPECIFIC_OCCURRENCE, and the staged
``step_key`` -- rite + work + printed source coordinate -- is exactly that.

The one remaining collision is withheld from the graph and stays withheld: SankhSS 16.15.13
carries two printed sutras under one citation in the edition the staging read, so the locator
cannot separate them. That is a finding against the artifact's locator extraction, recorded
as a gap. It is not disambiguated here, because the only available discriminator is
``printed_ordinal_in_work``, and adding it to the key would change all 3,121 existing
identities to fix one row.

Usage:
    python scripts/m7_ritual_step_product_identity.py [--execute] [--backup DIR]
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

OUT = pathlib.Path("data/staging/integration/m7_ritual_step_identity_receipt.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The product type name. Matches ``entity_type`` already on the node, so this migration
#: introduces no new vocabulary -- it publishes a value the staging had already decided.
DISPLAY_TYPE = "RITUAL_STEP"

#: The four corpus totals. Whatever else a migration does, these do not move.
CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}


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


def preconditions(session: Session) -> dict[str, Any]:
    """Everything that must already be true. Measured, not assumed.

    The migration is additive and idempotent, but "additive" is a claim about the graph, so
    it is checked against the graph: every node must already carry the identity this
    migration is about to make resolvable, and no two may share one.
    """
    row = session.run(
        "MATCH (s:RitualStep) RETURN count(s) AS nodes, "
        "count(s.step_key) AS with_key, "
        "count(s.canonical_urn) AS with_urn, "
        "count(s.entity_id) AS with_uuid, "
        "count(DISTINCT s.step_key) AS distinct_keys, "
        "count(DISTINCT s.canonical_urn) AS distinct_urns, "
        "count(DISTINCT s.entity_id) AS distinct_uuids, "
        "count(s.display_type) AS already_typed, "
        "sum(CASE WHEN s.citation IS NULL OR s.work_key IS NULL THEN 1 ELSE 0 END) "
        "  AS missing_locator"
    ).single()
    measured = dict(row or {})
    nodes = int(measured.get("nodes") or 0)
    measured["every_node_carries_a_key"] = int(measured.get("with_key") or 0) == nodes
    measured["every_node_carries_a_urn"] = int(measured.get("with_urn") or 0) == nodes
    measured["every_node_carries_a_uuid"] = int(measured.get("with_uuid") or 0) == nodes
    measured["key_collisions"] = nodes - int(measured.get("distinct_keys") or 0)
    measured["urn_collisions"] = nodes - int(measured.get("distinct_urns") or 0)
    measured["uuid_collisions"] = nodes - int(measured.get("distinct_uuids") or 0)
    # An existing display_type that is NOT ours would mean this migration is about to
    # overwrite a decision somebody else made.
    measured["foreign_display_type"] = int(
        session.run(
            "MATCH (s:RitualStep) WHERE s.display_type IS NOT NULL "
            "AND s.display_type <> $t RETURN count(s) AS c",
            t=DISPLAY_TYPE,
        ).single()["c"]
    )
    measured["ok"] = (
        nodes > 0
        and measured["every_node_carries_a_key"]
        and measured["every_node_carries_a_urn"]
        and measured["every_node_carries_a_uuid"]
        and measured["key_collisions"] == 0
        and measured["urn_collisions"] == 0
        and measured["uuid_collisions"] == 0
        and int(measured.get("missing_locator") or 0) == 0
        and measured["foreign_display_type"] == 0
    )
    return measured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            checks = preconditions(session)
            outstanding = int(
                session.run(
                    "MATCH (s:RitualStep) WHERE s.display_type IS NULL RETURN count(s) AS c"
                ).single()["c"]
            )

            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  M7 RITUAL STEP PRODUCT IDENTITY  {mode}")
            print()
            print(
                f"  before: {before['nodes']:,} nodes / "
                f"{before['relationships']:,} relationships"
            )
            print(f"  :RitualStep nodes            {checks.get('nodes')}")
            print(
                f"  carrying step_key/urn/uuid   {checks.get('with_key')}/"
                f"{checks.get('with_urn')}/{checks.get('with_uuid')}"
            )
            print(
                f"  key / urn / uuid collisions  {checks['key_collisions']} / "
                f"{checks['urn_collisions']} / {checks['uuid_collisions']}"
            )
            print(f"  rows missing a locator       {checks.get('missing_locator')}")
            print(f"  already typed                {checks.get('already_typed')}")
            print(f"  outstanding                  {outstanding}")
            print()

            if not checks["ok"]:
                print("  PRECONDITIONS FAILED. Nothing written.")
                return 1

            written = 0
            if args.execute and outstanding:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                with session.begin_transaction() as tx:
                    written = int(
                        tx.run(
                            "MATCH (s:RitualStep) WHERE s.display_type IS NULL "
                            "SET s.display_type = $t, s.m7_applied = $at "
                            "RETURN count(s) AS n",
                            t=DISPLAY_TYPE,
                            at=datetime.datetime.now(datetime.UTC).isoformat(),
                        ).single()["n"]
                    )
                    tx.commit()

            after = census(session)
            final = preconditions(session)

            delta_nodes = after["nodes"] - before["nodes"]
            delta_rels = after["relationships"] - before["relationships"]
            core_held = after["core"] == CORE
            typed = int(final.get("already_typed") or 0)
            complete = typed == int(final.get("nodes") or -1)

            print(
                f"  after: {after['nodes']:,} nodes / "
                f"{after['relationships']:,} relationships"
                f"  (nodes {delta_nodes:+}, relationships {delta_rels:+})"
            )
            print(f"  core corpus unchanged: {core_held}")
            print(f"  display_type on {typed} of {final.get('nodes')}: {complete}")
            print()

            receipt = {
                "migration": "M7_RITUAL_STEP_PRODUCT_IDENTITY",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "display_type": DISPLAY_TYPE,
                "grain": "RITE_SPECIFIC_OCCURRENCE",
                "grain_evidence": "scripts/ritual_step_identity_probe.py",
                "census_before": before,
                "census_after": after,
                "node_delta": delta_nodes,
                "relationship_delta": delta_rels,
                "core_corpus_unchanged": core_held,
                "nodes_written": written,
                "preconditions": checks,
                "postconditions": final,
                "additive": delta_nodes == 0 and delta_rels == 0,
                "complete": complete,
            }
            receipt["receipt_sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(f"  receipt: {OUT}")
            if not args.execute:
                print()
                print("  REHEARSAL ONLY. Re-run with --execute --backup <dir>.")
            return 0 if (core_held and delta_nodes == 0 and delta_rels == 0) else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
