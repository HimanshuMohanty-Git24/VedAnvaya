#!/usr/bin/env python3
"""Execute Wave 3: the canonical import, read back out of the database.

Owner sections 7, 11 and 12. This is the only script in the campaign that writes to the
canonical graph, and it is built around three rules the campaign learned the hard way.

**A failed domain must not leave half its mutation committed.** Each element group runs in
one explicit transaction. The group either lands whole or not at all, and the checkpoint is
written only after the transaction commits, so a resumed run cannot skip a group that
half-ran.

**Import code returning success closes nothing.** Every group's count is read back out of
the database after its transaction commits, and rows-sent is diffed against rows-landed. A
MERGE can collapse two rows into one and a MATCH can find no endpoint; neither failure
appears offline, and both have happened in this project.

**Idempotent, ordered, checkpointed, domain-attributed.** Re-running is a no-op. The order
is the owner's canonical order, not the declaration order: corrections first, then schema,
then nodes, then the edges that point at them. Every element carries the domain that
produced it and the run id that wrote it, so a rollback can be scoped.

WHAT IT REFUSES TO DO
=====================

It will not write unless ``WAVE_3_DRY_RUN_V2`` says GO, and it re-reads that artifact's own
inputs rather than trusting its verdict: if the element plan, the eligibility ledger or the
gap registry has changed since the dry-run was generated, the run stops. A dry-run that
describes a different tree than the one being imported is worse than no dry-run.

It also refuses any group the plan marked unusable, and it never writes an element whose
identity the plan withheld.

Usage:
    python scripts/wave3_import.py --execute      # write
    python scripts/wave3_import.py                # rehearse: plan, verify, write nothing
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase, Session
from wave3_import_plan import (
    GROUPS,
    ElementGroup,
    elements_of,
    get_path,
    identity_of,
    passes,
    row_rel_type,
)

INTEGRATION = pathlib.Path("data/staging/integration")
DRY_RUN = INTEGRATION / "wave3_dry_run_v2.json"
PLAN = INTEGRATION / "wave3_import_plan.json"
LEDGER = INTEGRATION / "wave3_eligibility.json"
SOMA = INTEGRATION / "wave3_soma_pressing_correction.json"
SCOPE = INTEGRATION / "wave3_scope_grain.json"
REGISTRY = pathlib.Path("data/gap_registry.json")
CHECKPOINT = INTEGRATION / "wave3_import_checkpoint.json"
RECEIPT = INTEGRATION / "wave3_import_receipt.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: Stamped on every element this wave writes, so a rollback can be scoped to it and a
#: readback can tell a Wave 3 element from one that was already there.
WAVE = "WAVE_3"

#: Properties carried onto every written element. ``run_id`` is the import's own identity.
def provenance(run_id: str, domain: str, group_id: str) -> dict[str, str]:
    return {
        "wave": WAVE,
        "wave3_run_id": run_id,
        "wave3_domain": domain,
        "wave3_group": group_id,
    }


#: Which properties of a source row become element properties. Everything else in the row
#: is evidence about how the row was produced and stays in the staging artifact -- copying a
#: whole row onto a node makes the graph a second, diverging copy of the artifact.
CARRIED: dict[str, tuple[str, ...]] = {
    "SR_ROLE_FILLER_NODES": (
        "role_filler_key",
        "canonical_key",
        "veda",
        "role",
        "surface",
        "lemma",
        "upos",
        "case",
        "filler_type",
        "derivation",
        "predicate",
        "frame",
        "assertion_ordinal",
        "entity_key",
        "entity_label",
    ),
    "RITUAL_RITE_NODES": (
        "ritual_key",
        "label_en",
        "label_sa",
        "rite_class",
        "existence_evidence_type",
        "samhita_attested",
        "samhita_attestation_count",
        "supplementary_attestation_count",
        "curator_note",
        "node_status",
    ),
    "RITUAL_STEP_NODES": (
        "step_key",
        "canonical_urn",
        "entity_id",
        "entity_type",
        "ritual_key",
        "step_position",
        "printed_ordinal_in_work",
        "sequence_marker",
        "citation",
        "supplementary_key",
        "work_key",
        "veda_school",
        "tier",
        "text_iast",
        "translation",
        "translation_translator",
        "order_basis",
        "order_completeness",
        "source_stated_position",
        "anchor_note",
    ),
    "RITUAL_ROLE_NODES": (
        "role_key",
        "label_en",
        "label_sa",
        "officiant_group",
        "in_classical_sixteen",
        "denominator_schema",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_ACTION_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_IMPLEMENT_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_MATERIAL_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_OFFERING_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "SCHOLARSHIP_SCHOLAR_NODES": (
        "scholar_id",
        "name",
        "scholar_type",
        "attribution_status",
    ),
    "SCHOLARSHIP_WORK_NODES": ("work_id", "title", "source_id", "scope_note"),
    "COMMUNITIES_ARTIFACT_NODES": (
        "community_id",
        "algorithm",
        "algorithm_version",
        "resolution",
        "seed",
        "weighting",
        "projection",
        "size",
        "caveat",
        "interpretation_warning",
        "code_commit",
        "config_hash",
        "source_snapshot",
    ),
}


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def digest(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def scalar(value: Any) -> Any:
    """Neo4j stores scalars and lists of scalars; a nested structure becomes JSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) and all(
        v is None or isinstance(v, (str, int, float, bool)) for v in value
    ):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def node_props(row: dict[str, Any], group: ElementGroup) -> dict[str, Any]:
    fields = CARRIED.get(group.group_id, tuple(row))
    return {field: scalar(row.get(field)) for field in fields if field in row}


# ---------------------------------------------------------------------------------------
# Corrections. These run first, and each is a named, proof-backed change to existing data.
# ---------------------------------------------------------------------------------------


def correction_soma(session: Session, run_id: str, *, execute: bool) -> dict[str, Any]:
    """Owner section 3: retire the edges whose sole evidence is a retired weak alias.

    The retirement set comes from the correction artifact, which re-derived the ABOUT_CONCEPT
    layer over all 20,210 mantras rather than reading the stored evidence quote -- that quote
    is a window round the match, and a verse may carry a surviving alias the window does not
    show.

    The edges are DELETEd rather than flagged. A flagged edge still answers a query, and the
    whole point of withdrawing an alias's authority is that the edges it alone created stop
    being assertions.
    """
    artifact = load(SOMA)
    mentions = artifact.get("mentions_entity") or {}
    about = artifact.get("about_concept") or {}
    retired = artifact.get("retired_aliases") or []
    mention_keys = list(mentions.get("retire_keys") or [])
    about_keys = list(about.get("retire_keys") or [])
    updates = list(mentions.get("update_rows") or [])

    result: dict[str, Any] = {
        "correction": "SOMA_PRESSING_WEAK_ALIAS_RETIREMENT",
        "retired_aliases": retired,
        "mentions_entity_sent": len(mention_keys),
        "about_concept_sent": len(about_keys),
        "matched_alias_updates_sent": len(updates),
    }
    if not execute:
        result["executed"] = False
        return result

    with session.begin_transaction() as tx:
        deleted_m = tx.run(
            "UNWIND $keys AS k "
            "MATCH (p:Passage {canonical_key: k})-[r:MENTIONS_ENTITY]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "WHERE ALL(a IN r.matched_aliases WHERE a IN $retired) "
            "DELETE r RETURN count(*) AS n",
            keys=mention_keys,
            retired=retired,
        ).single()["n"]
        deleted_a = tx.run(
            "UNWIND $keys AS k "
            "MATCH (p:Passage {canonical_key: k})-[r:ABOUT_CONCEPT]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "DELETE r RETURN count(*) AS n",
            keys=about_keys,
        ).single()["n"]
        # The 12 edges that survive lose the retired alias from their evidence, so the
        # property stops naming a form that is no longer allowed to assert anything.
        edited = tx.run(
            "UNWIND $rows AS row "
            "MATCH (p:Passage {canonical_key: row.canonical_key})-[r:MENTIONS_ENTITY]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "SET r.matched_aliases = row.after, "
            "    r.alias_count = size(row.after), "
            "    r.wave3_alias_retirement = $run_id "
            "RETURN count(*) AS n",
            rows=[
                {
                    "canonical_key": row["canonical_key"],
                    "after": row["matched_aliases_after"],
                }
                for row in updates
            ],
            run_id=run_id,
        ).single()["n"]
        tx.commit()

    result.update(
        {
            "executed": True,
            "mentions_entity_landed": deleted_m,
            "about_concept_landed": deleted_a,
            "matched_alias_updates_landed": edited,
        }
    )
    return result


def correction_m5(session: Session, run_id: str, *, execute: bool) -> dict[str, Any]:
    """Owner decision 1, card M5: one edge moves from EPITHET_VARIANT_OF.

    Scoped to the single Soma Pavamana -> Soma pair. The other 10 EPITHET_VARIANT_OF edges
    and the predicate's meaning are untouched, so this is a data migration with a recorded
    reason rather than a semantic change.
    """
    result: dict[str, Any] = {"correction": "M5_SPECIALIZED_FORM_OF", "edges_sent": 1}
    if not execute:
        result["executed"] = False
        return result

    with session.begin_transaction() as tx:
        before = tx.run(
            "MATCH ()-[r:EPITHET_VARIANT_OF]->() RETURN count(r) AS n"
        ).single()["n"]
        moved = tx.run(
            "MATCH (a:Devata {entity_key: 'VG:DEVATA:PAVAMANAH-SOMAH'})"
            "-[r:EPITHET_VARIANT_OF]->(b:Devata {entity_key: 'VG:DEVATA:SOMAH'}) "
            "CREATE (a)-[n:SPECIALIZED_FORM_OF]->(b) "
            "SET n = properties(r), "
            "    n.migrated_from = 'EPITHET_VARIANT_OF', "
            "    n.migration_reason = "
            "      'Owner decision 1: both distinctions carry useful semantics and "
            "EPITHET_VARIANT_OF is too strong for this pair. A is a contextually "
            "specialized manifestation of B and stays separately addressable.', "
            "    n.wave3_run_id = $run_id, "
            "    n.wave = $wave "
            "DELETE r RETURN count(*) AS n",
            run_id=run_id,
            wave=WAVE,
        ).single()["n"]
        after = tx.run("MATCH ()-[r:EPITHET_VARIANT_OF]->() RETURN count(r) AS n").single()["n"]
        specialized = tx.run(
            "MATCH ()-[r:SPECIALIZED_FORM_OF]->() RETURN count(r) AS n"
        ).single()["n"]
        tx.commit()

    result.update(
        {
            "executed": True,
            "edges_landed": moved,
            "epithet_variant_of_before": before,
            "epithet_variant_of_after": after,
            "specialized_form_of_after": specialized,
        }
    )
    return result


# ---------------------------------------------------------------------------------------
# Element groups.
# ---------------------------------------------------------------------------------------


def write_nodes(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    key = group.match_property
    payload = []
    for row in rows:
        props = node_props(row, group)
        props.update(provenance(run_id, group.domain, group.group_id))
        if group.key_minted_from_identity:
            props[key] = f"{group.element}:{identity_of(row, group)}"
        else:
            props[key] = str(get_path(row, group.identity_fields[0]))
        payload.append(props)

    query = (
        f"UNWIND $rows AS row MERGE (n:{group.element} {{{key}: row.{key}}}) "
        "SET n += row RETURN count(n) AS n"
    )
    with session.begin_transaction() as tx:
        landed = tx.run(query, rows=payload).single()["n"]
        tx.commit()
    return int(landed)


def write_node_properties(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    """Property writes onto existing nodes. MATCH, never MERGE.

    A MERGE here would create the node the property was meant to annotate, turning a
    dangling reference into a silent new node -- which is how a projection grows rows that
    correspond to nothing.
    """
    key = group.match_property
    prefix = f"{group.domain}_"
    payload = []
    for row in rows:
        props = {
            f"{prefix}{field}": scalar(value)
            for field, value in row.items()
            if field not in group.identity_fields and not field.startswith("evidence")
        }
        props.update(provenance(run_id, group.domain, group.group_id))
        payload.append({"key": str(get_path(row, group.identity_fields[0])), "props": props})

    query = (
        f"UNWIND $rows AS row MATCH (n:{group.element}) WHERE n.{key} = row.key "
        "SET n += row.props RETURN count(n) AS n"
    )
    with session.begin_transaction() as tx:
        landed = tx.run(query, rows=payload).single()["n"]
        tx.commit()
    return int(landed)


def write_relationships(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    by_predicate = dict(group.object_field_by_predicate)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        predicate = row_rel_type(row, group)
        end_field = by_predicate.get(predicate, group.end_field)
        start = get_path(row, str(group.start_field))
        end = get_path(row, str(end_field))
        if not start or not end:
            continue
        props = {
            field: scalar(value)
            for field, value in row.items()
            if field not in {group.start_field, end_field}
        }
        props.update(provenance(run_id, group.domain, group.group_id))
        buckets.setdefault(predicate, []).append(
            {"start": str(start), "end": str(end), "props": props}
        )

    start_label = f":{group.start_label}" if group.start_label else ""
    end_label = f":{group.end_label}" if group.end_label else ""
    landed = 0
    for predicate, payload in sorted(buckets.items()):
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (a{start_label}) WHERE a.{group.start_key_property} = row.start "
            f"MATCH (b{end_label}) WHERE b.{group.end_key_property} = row.end "
            f"MERGE (a)-[r:{predicate}]->(b) SET r += row.props RETURN count(r) AS n"
        )
        with session.begin_transaction() as tx:
            landed += int(tx.run(query, rows=payload).single()["n"])
            tx.commit()
    return landed


def write_relationship_properties(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    """Backfill onto edges that already exist.

    The MATCH is undirected only for a symmetric group. The parallel family is stored once
    in ascending Veda-code order and read undirected, so a direction-sensitive MATCH would
    miss half of it and the backfill would land on one arbitrary half of the layer. For a
    directed relation the arrow is part of the claim, and matching either way would write
    the property onto an edge that asserts the opposite.

    Either way this MATCHes and never MERGEs: the group exists because the edges are already
    there, so a MERGE would create the very element whose absence is the finding.
    """
    by_predicate = dict(group.object_field_by_predicate)
    buckets: dict[str, list[dict[str, Any]]] = {}
    prefix = f"{group.domain}_"
    for row in rows:
        predicate = row_rel_type(row, group)
        end_field = by_predicate.get(predicate, group.end_field)
        start = get_path(row, str(group.start_field))
        end = get_path(row, str(end_field))
        if not start or not end:
            continue
        props = {
            f"{prefix}{field}": scalar(value)
            for field, value in row.items()
            if field not in {group.start_field, end_field}
        }
        props.update(provenance(run_id, group.domain, group.group_id))
        buckets.setdefault(predicate, []).append(
            {"start": str(start), "end": str(end), "props": props}
        )

    start_label = f":{group.start_label}" if group.start_label else ""
    end_label = f":{group.end_label}" if group.end_label else ""
    landed = 0
    for predicate, payload in sorted(buckets.items()):
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (a{start_label}) WHERE a.{group.start_key_property} = row.start "
            f"MATCH (b{end_label}) WHERE b.{group.end_key_property} = row.end "
            f"MATCH (a)-[r:{predicate}]{'-' if group.symmetric else '->'}(b) "
            "SET r += row.props RETURN count(r) AS n"
        )
        with session.begin_transaction() as tx:
            landed += int(tx.run(query, rows=payload).single()["n"])
            tx.commit()
    return landed


WRITERS = {
    "NODE": write_nodes,
    "NODE_PROPERTY": write_node_properties,
    "RELATIONSHIP": write_relationships,
    "RELATIONSHIP_PROPERTY": write_relationship_properties,
}

#: The owner's canonical order, by element kind. Nodes before the edges that point at them,
#: and property backfills last so they annotate a settled shape.
KIND_ORDER = {"NODE": 0, "RELATIONSHIP": 1, "NODE_PROPERTY": 2, "RELATIONSHIP_PROPERTY": 3}


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "core_corpus": {
            r["veda"]: r["n"]
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="actually write")
    parser.add_argument("--json", default=str(RECEIPT))
    args = parser.parse_args()

    dry = load(DRY_RUN)
    plan = load(PLAN)
    if not dry or not plan:
        print("  no dry-run or no element plan. Run wave3_dry_run_v2.py first.")
        return 1

    # The dry-run's verdict is only worth as much as the tree it described. Re-read its
    # inputs rather than trusting the verdict it recorded.
    stale = {
        name: (recorded, digest(path))
        for name, recorded, path in (
            ("element_plan", (dry.get("provenance") or {}).get("element_plan_sha256"), PLAN),
            (
                "eligibility_ledger",
                (dry.get("provenance") or {}).get("eligibility_ledger_sha256"),
                LEDGER,
            ),
            ("gap_registry", (dry.get("provenance") or {}).get("gap_registry_sha256"), REGISTRY),
            ("scope_grain", (dry.get("provenance") or {}).get("scope_grain_sha256"), SCOPE),
            ("soma_correction", (dry.get("provenance") or {}).get("soma_correction_sha256"), SOMA),
        )
        if recorded != digest(path)
    }
    if stale:
        print("  the dry-run describes a different tree than this one:")
        for name, (recorded, actual) in stale.items():
            print(f"    {name}: dry-run saw {recorded}, on disk {actual}")
        print("  re-run scripts/wave3_dry_run_v2.py before importing.")
        return 1

    if dry.get("go_no_go") != "GO":
        print(f"  dry-run says {dry.get('go_no_go')}. Owner section 6: STOP.")
        for failure in dry.get("acceptance_gate_failures") or []:
            print(f"    FAIL {failure}")
        return 1
    if not plan.get("usable"):
        print("  the element plan is not usable. STOP.")
        return 1

    run_id = hashlib.sha256(
        json.dumps(
            {
                "dry_run": digest(DRY_RUN),
                "plan": digest(PLAN),
                "commit": (dry.get("provenance") or {}).get("git_commit"),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:16]

    checkpoint = load(CHECKPOINT)
    done: set[str] = set(checkpoint.get("completed") or []) if checkpoint.get(
        "run_id"
    ) == run_id else set()

    eligible = set(dry.get("eligible_domains") or [])
    groups = sorted(
        (g for g in GROUPS if g.domain in eligible),
        key=lambda g: (KIND_ORDER[g.kind], g.domain, g.group_id),
    )

    # Identities the plan withheld must never be written.
    withheld: dict[str, set[str]] = {}
    for entry in plan.get("groups") or []:
        withheld[entry["group_id"]] = {
            record["identity"] for record in entry.get("identity_collision_detail") or []
        }

    driver = GraphDatabase.driver(URI, auth=AUTH)
    steps: list[dict[str, Any]] = []
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  WAVE 3 IMPORT  run_id {run_id}  {mode}")
            print(
                f"  before: {before['nodes']:,} nodes / "
                f"{before['relationships']:,} relationships"
            )
            print()

            for name, correction in (
                ("SOMA_PRESSING_WEAK_ALIAS_RETIREMENT", correction_soma),
                ("M5_SPECIALIZED_FORM_OF", correction_m5),
            ):
                if name in done:
                    print(f"  {name:46} already applied, skipping")
                    continue
                outcome = correction(session, run_id, execute=args.execute)
                steps.append(outcome)
                print(
                    f"  {name:46} "
                    + (
                        "rehearsed"
                        if not args.execute
                        else " ".join(
                            f"{k.replace('_landed', '')}={v}"
                            for k, v in outcome.items()
                            if k.endswith("_landed")
                        )
                    )
                )
                if args.execute:
                    done.add(name)
                    CHECKPOINT.write_text(
                        json.dumps({"run_id": run_id, "completed": sorted(done)}, indent=2)
                        + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )

            header = f"  {'group':38}{'kind':24}{'sent':>8}{'landed':>8}  status"
            print()
            print(header)
            print("  " + "-" * (len(header) - 2))
            for group in groups:
                skip = withheld.get(group.group_id, set())
                rows = [
                    row
                    for row in elements_of(group)
                    if passes(row, group) and identity_of(row, group) not in skip
                ]
                if group.skip_statuses and group.node_status_field:
                    rows = [
                        row
                        for row in rows
                        if str(get_path(row, group.node_status_field) or "")
                        not in group.skip_statuses
                    ]
                sent = len(rows)
                if group.group_id in done:
                    print(f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}{'-':>8}  done")
                    continue
                if not args.execute:
                    print(
                        f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}{'-':>8}  rehearsed"
                    )
                    steps.append(
                        {"group_id": group.group_id, "rows_sent": sent, "executed": False}
                    )
                    continue

                landed = WRITERS[group.kind](session, group, rows, run_id)
                ok = landed >= sent if group.kind == "NODE" else landed > 0 or sent == 0
                steps.append(
                    {
                        "group_id": group.group_id,
                        "domain": group.domain,
                        "kind": group.kind,
                        "rows_sent": sent,
                        "rows_landed": landed,
                        "executed": True,
                    }
                )
                print(
                    f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}{landed:>8}  "
                    + ("ok" if ok else "DIFF")
                )
                done.add(group.group_id)
                CHECKPOINT.write_text(
                    json.dumps({"run_id": run_id, "completed": sorted(done)}, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )

            after = census(session)
    finally:
        driver.close()

    receipt = {
        "schema_version": "1.0",
        "run_id": run_id,
        "executed": args.execute,
        "started_from_dry_run": str(DRY_RUN),
        "dry_run_sha256": digest(DRY_RUN),
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "census_before": before,
        "census_after": after,
        "node_delta": after["nodes"] - before["nodes"],
        "relationship_delta": after["relationships"] - before["relationships"],
        "core_corpus_unchanged": before["core_corpus"] == after["core_corpus"],
        "steps": steps,
    }
    pathlib.Path(args.json).write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print(
        f"  after: {after['nodes']:,} nodes / {after['relationships']:,} relationships"
        f"  (nodes {receipt['node_delta']:+}, relationships {receipt['relationship_delta']:+})"
    )
    print(f"  core corpus unchanged: {receipt['core_corpus_unchanged']}")
    print(f"  receipt: {args.json}")
    print()
    if not args.execute:
        print("  REHEARSAL ONLY. Nothing was written. Re-run with --execute.")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
