#!/usr/bin/env python3
"""Phases H and I: the dry run and the one bulk migration, from one immutable plan.

``--dry-run`` and ``--execute`` are the same code path up to the transaction. That is the
point: a dry run that re-derives what it thinks the executor will do is a second
implementation, and the two agreeing proves only that the same author made the same
assumption twice. Here both read ``translation_import_plan.json``, verify its sha256
against the digest file, and iterate the identical ``nodes_detail`` list.

The executor promises an exact delta and refuses to commit if it does not get it. Every
write is inside one transaction, the census is taken before and after inside the same
session, and a mismatch rolls back rather than being patched forward -- because a canonical
mutation nobody predicted is not something to reason about afterwards.

Run:
    python scripts/translation_integration_migrate.py --dry-run
    python scripts/translation_integration_migrate.py --execute
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
from typing import Any, Final

import translation_integration_common as T

PLAN_PATH: Final = T.INTEGRATION / "translation_import_plan.json"
DIGEST_PATH: Final = T.INTEGRATION / "translation_import_plan.sha256.json"

#: The one write. ``MERGE`` on ``translation_id`` rather than ``CREATE`` so an interrupted
#: run can be repeated without a duplicate beside the node that landed, and ``ON CREATE``
#: only for the payload, so a second run cannot silently rewrite a literal this one wrote.
#:
#: The label and the edge grade are set unconditionally, because they are the plan's
#: promise about shape rather than content and a node that already exists may be missing
#: them -- which is exactly what happened: plan version 1 omitted both, the quality
#: scorecard reported 1,132 internal_leaked and 1,132 ungraded edges, and :func:`_COMPLETE`
#: exists to finish those 1,132 without touching a single literal.
_WRITE: Final = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.attach_to})
MERGE (t:Translation {translation_id: row.translation_id})
ON CREATE SET t += row.props
SET t:Internal
MERGE (m)-[r:HAS_TRANSLATION]->(t)
SET r += row.edge_props
RETURN count(*) AS touched
"""

#: The completion pass. Sets only the label and the edge grade, never a property that
#: carries text, so it cannot alter a translation's content. Its promised delta is zero
#: nodes and zero relationships, and the executor refuses to commit if it sees any.
_COMPLETE: Final = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.attach_to})
      -[r:HAS_TRANSLATION]->(t:Translation {translation_id: row.translation_id})
SET t:Internal
SET r += row.edge_props
RETURN count(*) AS touched
"""


def load_plan() -> dict[str, Any]:
    """The plan, refused unless its bytes hash to the digest recorded beside it."""
    declared = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))
    measured = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
    if measured != declared["sha256"]:
        raise SystemExit(
            "PLAN DIGEST MISMATCH\n"
            f"  declared {declared['sha256']}\n"
            f"  measured {measured}\n"
            "The plan has changed since it was hashed. Rebuild it with "
            "translation_integration_plan.py and re-read the diff before running anything."
        )
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """The plan's nodes in the exact shape the write consumes. One conversion, both paths."""
    return [
        {
            "attach_to": node["attach_to_canonical_key"],
            "translation_id": node["translation_id"],
            "props": {k: v for k, v in node["properties"].items() if v is not None},
            "edge_props": {
                k: v for k, v in node.get("edge_properties", {}).items() if v is not None
            },
        }
        for node in plan["nodes_detail"]
    ]


# --------------------------------------------------------------------------------------
# Pre-flight
# --------------------------------------------------------------------------------------


def preflight(session: Any, plan: dict[str, Any]) -> dict[str, Any]:
    """Everything that must be true of the graph before a single row is written."""
    import gate_bc_common as G

    rows = _rows(plan)
    keys = [r["attach_to"] for r in rows]
    covered = sorted({k for node in plan["nodes_detail"] for k in node["covers_canonical_keys"]})

    resolved = {
        record["k"]
        for record in session.run(
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k}) RETURN m.canonical_key AS k",
            keys=covered,
        )
    }
    unresolvable = sorted(set(covered) - resolved)

    already = [
        {"canonical_key": record["k"], "translation_id": record["t"], "source": record["s"]}
        for record in session.run(
            """
            UNWIND $keys AS k
            MATCH (m:Mantra {canonical_key: k})-[:HAS_TRANSLATION]->(t:Translation)
            RETURN m.canonical_key AS k, t.translation_id AS t, t.source_id AS s
            """,
            keys=covered,
        )
    ]

    colliding = [
        record["t"]
        for record in session.run(
            """
            UNWIND $ids AS id
            MATCH (t:Translation {translation_id: id})
            RETURN t.translation_id AS t
            """,
            ids=[r["translation_id"] for r in rows],
        )
    ]

    # Every reuse row names a Rigvedic translation it reuses. If that node has gone, the
    # provenance the owner policy requires would be a dangling id.
    reuse_sources = sorted(
        {
            node["properties"]["reused_from_translation_id"]
            for node in plan["nodes_detail"]
            if node["properties"].get("reuse_kind")
        }
    )
    reuse_found = {
        record["t"]
        for record in session.run(
            "UNWIND $ids AS id MATCH (t:Translation {translation_id: id}) "
            "RETURN t.translation_id AS t",
            ids=reuse_sources,
        )
    }

    core = G.core_corpus(session)
    return {
        "census_before": G.graph_census(session),
        "core_corpus_before": core,
        "core_corpus_matches_invariant": core
        == plan["invariants_the_migration_must_hold"]["core_corpus_unchanged"],
        "coverage_before": G.translation_coverage(session)["per_veda"],
        "attachment_digest_before": G.attachment_digest(session),
        "targets": {
            "canonical_keys_covered": len(covered),
            "resolved_in_graph": len(resolved),
            "unresolvable": unresolvable,
            "anchors": len(keys),
        },
        "targets_already_carrying_a_translation": already,
        "translation_ids_already_present": colliding,
        "reuse_sources": {
            "declared": len(reuse_sources),
            "found_in_graph": len(reuse_found),
            "missing": sorted(set(reuse_sources) - reuse_found),
        },
        "blockers": _blockers(
            unresolvable, already, colliding, reuse_sources, reuse_found, core, plan
        ),
    }


def _blockers(
    unresolvable: list[str],
    already: list[dict[str, Any]],
    colliding: list[str],
    reuse_sources: list[str],
    reuse_found: set[str],
    core: dict[str, int],
    plan: dict[str, Any],
) -> list[str]:
    out = []
    if unresolvable:
        out.append(f"{len(unresolvable)} planned canonical keys do not resolve: {unresolvable[:5]}")
    if already:
        out.append(
            f"{len(already)} planned targets already carry a translation; the plan promises "
            f"to overwrite nothing: {already[:3]}"
        )
    if colliding:
        out.append(f"{len(colliding)} planned translation_ids already exist: {colliding[:3]}")
    if set(reuse_sources) - reuse_found:
        out.append(
            f"{len(set(reuse_sources) - reuse_found)} reuse rows name a source translation "
            "that is not in the graph"
        )
    if core != plan["invariants_the_migration_must_hold"]["core_corpus_unchanged"]:
        out.append(f"core corpus is {core}, not the invariant the plan was built against")
    return out


# --------------------------------------------------------------------------------------
# Delta
# --------------------------------------------------------------------------------------


def promised_delta(plan: dict[str, Any]) -> dict[str, int]:
    return {
        "nodes": plan["nodes"]["total"],
        "relationships": plan["relationships"]["HAS_TRANSLATION"],
        "translation_nodes": plan["nodes"]["total"],
        "has_translation_edges": plan["relationships"]["HAS_TRANSLATION"],
    }


def measured_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {k: after[k] - before[k] for k in before}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument(
        "--complete-shape",
        action="store_true",
        help="set the :Internal label and the HAS_TRANSLATION grade on rows this plan "
        "already imported. Creates nothing and writes no text.",
    )
    args = parser.parse_args()

    import gate_bc_common as G

    plan = load_plan()
    rows = _rows(plan)
    driver = G.driver()
    try:
        with G.session(driver) as session:
            pre = preflight(session, plan)
            promised = promised_delta(plan)

            report: dict[str, Any] = {
                "mode": "DRY_RUN" if args.dry_run else "EXECUTE",
                "started_at": dt.datetime.now(dt.UTC).isoformat(),
                "plan_sha256": json.loads(DIGEST_PATH.read_text(encoding="utf-8"))["sha256"],
                "import_batch": plan["import_batch"],
                "rows_to_write": len(rows),
                "promised_delta": promised,
                "preflight": pre,
            }

            for line in (
                f"mode                : {report['mode']}",
                f"plan sha256         : {report['plan_sha256']}",
                f"nodes to write      : {len(rows)}",
                f"census before       : {pre['census_before']}",
                f"core corpus         : {pre['core_corpus_before']} "
                f"(matches invariant: {pre['core_corpus_matches_invariant']})",
                f"targets covered     : {pre['targets']['canonical_keys_covered']} "
                f"resolved {pre['targets']['resolved_in_graph']}",
                f"already translated  : {len(pre['targets_already_carrying_a_translation'])}",
                f"id collisions       : {len(pre['translation_ids_already_present'])}",
                f"reuse sources found : {pre['reuse_sources']['found_in_graph']} of "
                f"{pre['reuse_sources']['declared']}",
            ):
                print(line)

            if args.complete_shape:
                # The population must already be present and complete. Anything else means
                # this is being run instead of the import rather than after it.
                present = session.run(
                    "UNWIND $ids AS id MATCH (:Mantra)-[:HAS_TRANSLATION]->"
                    "(t:Translation {translation_id: id}) RETURN count(t) AS c",
                    ids=[r["translation_id"] for r in rows],
                ).single()["c"]
                report["rows_already_present"] = present
                if present != len(rows):
                    report["verdict"] = "BLOCKED"
                    print(
                        f"BLOCKER: {present} of {len(rows)} planned rows are present; "
                        "--complete-shape finishes an executed import and does not replace it"
                    )
                    _write(report, args)
                    return 1

                before_shape = _shape_census(session)
                with session.begin_transaction() as tx:
                    tx.run(_COMPLETE, rows=rows).consume()
                    after = G.graph_census(tx)
                    delta = measured_delta(pre["census_before"], after)
                    if any(delta.values()):
                        tx.rollback()
                        report["measured_delta"] = delta
                        report["verdict"] = "ROLLED_BACK_CREATED_SOMETHING"
                        print("CREATED SOMETHING -- rolled back:", delta)
                        _write(report, args)
                        return 1
                    tx.commit()
                report["promised_delta"] = dict.fromkeys(pre["census_before"], 0)
                report["measured_delta"] = measured_delta(
                    pre["census_before"], G.graph_census(session)
                )
                report["shape_before"] = before_shape
                report["shape_after"] = _shape_census(session)
                report["attachment_digest_after"] = G.attachment_digest(session)
                report["translation_text_unchanged"] = (
                    report["attachment_digest_after"]["digest_sha256"]
                    == pre["attachment_digest_before"]["digest_sha256"]
                )
                report["verdict"] = (
                    "SHAPE_COMPLETED"
                    if not any(report["measured_delta"].values())
                    and report["shape_after"]["translations_without_internal"] == 0
                    and report["shape_after"]["ungraded_has_translation_edges"] == 0
                    and report["translation_text_unchanged"]
                    else "SHAPE_COMPLETION_FAILED"
                )
                print()
                print("shape before:", json.dumps(before_shape))
                print("shape after :", json.dumps(report["shape_after"]))
                print("text unchanged:", report["translation_text_unchanged"])
                print("VERDICT     :", report["verdict"])
                _write(report, args)
                return 0 if report["verdict"] == "SHAPE_COMPLETED" else 1

            if pre["blockers"]:
                print()
                for blocker in pre["blockers"]:
                    print("BLOCKER:", blocker)
                report["verdict"] = "BLOCKED"
                _write(report, args)
                return 1

            if args.dry_run:
                # The rehearsal: run the real write inside a transaction and roll it back,
                # so the delta reported is the one the write actually produces rather than
                # one counted from the plan a second time.
                with session.begin_transaction() as tx:
                    tx.run(_WRITE, rows=rows).consume()
                    after = G.graph_census(tx)
                    core_after = G.core_corpus(tx)
                    coverage_after = G.translation_coverage(tx)["per_veda"]
                    tx.rollback()
                report["measured_delta"] = measured_delta(pre["census_before"], after)
                report["census_inside_the_rolled_back_transaction"] = after
                report["core_corpus_inside_the_transaction"] = core_after
                report["coverage_inside_the_transaction"] = coverage_after
                report["delta_matches_promise"] = report["measured_delta"] == promised
                report["core_corpus_unchanged_by_the_write"] = (
                    core_after == pre["core_corpus_before"]
                )
                report["mutation_outside_translations"] = _mutation_outside_translations(
                    pre["census_before"], after, promised
                )

                census_now = G.graph_census(session)
                report["census_after_rollback"] = census_now
                report["rollback_restored_the_graph"] = census_now == pre["census_before"]
                digest_now = G.attachment_digest(session)
                report["attachment_digest_after_rollback"] = digest_now
                report["existing_attachments_untouched"] = (
                    digest_now == pre["attachment_digest_before"]
                )
                report["verdict"] = (
                    "DRY_RUN_OK"
                    if report["delta_matches_promise"]
                    and report["core_corpus_unchanged_by_the_write"]
                    and not report["mutation_outside_translations"]
                    and report["rollback_restored_the_graph"]
                    and report["existing_attachments_untouched"]
                    else "DRY_RUN_FAILED"
                )
            else:
                with session.begin_transaction() as tx:
                    tx.run(_WRITE, rows=rows).consume()
                    after = G.graph_census(tx)
                    core_after = G.core_corpus(tx)
                    delta = measured_delta(pre["census_before"], after)
                    outside = _mutation_outside_translations(pre["census_before"], after, promised)
                    if delta != promised or core_after != pre["core_corpus_before"] or outside:
                        tx.rollback()
                        report["measured_delta"] = delta
                        report["core_corpus_after"] = core_after
                        report["mutation_outside_translations"] = outside
                        report["verdict"] = "ROLLED_BACK_DELTA_MISMATCH"
                        print()
                        print("DELTA MISMATCH -- rolled back, nothing committed")
                        print("  promised:", promised)
                        print("  measured:", delta)
                        _write(report, args)
                        return 1
                    tx.commit()
                report["measured_delta"] = delta
                report["census_after"] = G.graph_census(session)
                report["core_corpus_after"] = G.core_corpus(session)
                report["coverage_after"] = G.translation_coverage(session)["per_veda"]
                report["attachment_digest_after"] = G.attachment_digest(session)
                report["delta_matches_promise"] = True
                report["verdict"] = "EXECUTED"
                report["nodes_written"] = [
                    {
                        "translation_id": node["translation_id"],
                        "attach_to_canonical_key": node["attach_to_canonical_key"],
                        "final_class": node["final_class"],
                        "veda": node["veda"],
                        "language": node["properties"]["language"],
                        "alignment_level": node["properties"]["alignment_level"],
                        "covers_canonical_keys": node["covers_canonical_keys"],
                        "staged_row_ids": node["staged_row_ids"],
                    }
                    for node in plan["nodes_detail"]
                ]

            print()
            print("promised delta :", promised)
            print("measured delta :", report.get("measured_delta"))
            print("VERDICT        :", report["verdict"])
            _write(report, args)
            return 0 if report["verdict"] in ("DRY_RUN_OK", "EXECUTED") else 1
    finally:
        driver.close()


def _shape_census(session: Any) -> dict[str, int]:
    """The two shape gates the quality scorecard reads, measured graph-wide.

    Graph-wide and not restricted to this batch, because the gates are graph-wide: if some
    other population also lacks the label, reporting only this batch's zero would claim a
    clean scorecard that the scorecard will not agree with.
    """
    return {
        "translations_without_internal": session.run(
            "MATCH (t:Translation) WHERE NOT t:Internal RETURN count(t) AS c"
        ).single()["c"],
        "ungraded_has_translation_edges": session.run(
            "MATCH ()-[r:HAS_TRANSLATION]->() WHERE r.quality_tier IS NULL RETURN count(r) AS c"
        ).single()["c"],
        "translation_nodes": session.run("MATCH (t:Translation) RETURN count(t) AS c").single()[
            "c"
        ],
    }


def _mutation_outside_translations(
    before: dict[str, int], after: dict[str, int], promised: dict[str, int]
) -> dict[str, Any]:
    """Whether anything moved that is not a translation node or its edge.

    The census counts all nodes and all relationships, so ``nodes`` growing by more than
    ``translation_nodes`` means something else was created. This is the check the task
    names as a STOP condition, and it is cheap because the two totals are in the same row.
    """
    out = {}
    node_delta = after["nodes"] - before["nodes"]
    translation_delta = after["translation_nodes"] - before["translation_nodes"]
    if node_delta != translation_delta:
        out["non_translation_nodes_created"] = node_delta - translation_delta
    rel_delta = after["relationships"] - before["relationships"]
    edge_delta = after["has_translation_edges"] - before["has_translation_edges"]
    if rel_delta != edge_delta:
        out["non_has_translation_relationships_created"] = rel_delta - edge_delta
    if translation_delta != promised["translation_nodes"]:
        out["translation_nodes_off_by"] = translation_delta - promised["translation_nodes"]
    return out


def _write(report: dict[str, Any], args: argparse.Namespace) -> pathlib.Path:
    if args.dry_run:
        name = "translation_import_dry_run.json"
    elif args.complete_shape:
        name = "translation_import_shape_completion.json"
    else:
        name = "translation_bulk_import_receipt.json"
    path = T.write_json(T.INTEGRATION / name, report)
    print("wrote", path)
    return path


if __name__ == "__main__":
    sys.exit(main())
