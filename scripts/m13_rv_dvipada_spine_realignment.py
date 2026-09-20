"""M13: re-anchor 25 translations that read against the wrong Sanskrit. GAP-TRANSLATION-006.

Griffith's edition numbers each four-pada group of RV 1.65-1.70 as one verse where ours
numbers each hemistich, so his unit 2 -- which renders our verses 3 and 4 -- shipped as the
translation of our verse 2. 25 of the span's 31 rows were on the wrong verse on a public page.

**The correction is not computed here.** It is read from the projection, which reads the
declared spine corrections in ``data/registry/upstream_corrections.yaml``. So the dry run, the
executor and the readback share one source and a future rebuild produces the same result --
there is no second list to drift, which is the failure this campaign has paid for twice.

WHAT MOVES AND WHAT DOES NOT

*   The ``:Translation`` node keeps its text byte for byte, its translator, edition, year,
    rights and source. Nothing about the rendering was ever wrong.
*   Its ``passage_id`` and ``translation_id`` move to the anchor of the span it renders. The
    id is re-derived by the same function the corpus builder uses, so it is the id the row
    would have had if the two editions had shared a spine.
*   ``alignment_level`` becomes ``MANTRA_RANGE`` where the unit covers two verses, and the
    covered keys are written onto the node. A row that claims ``MANTRA`` over a two-verse span
    is making a false claim even when it sits on the right verse, and that was half the defect.
*   The history is kept: ``spine_corrected_from`` and ``spine_corrected_from_translation_id``
    record the mistaken attachment, because a silent move erases the evidence that it happened.

Additive in census: 31 nodes updated in place, 31 edges deleted and 31 created, so the node
and relationship totals are unchanged. No Mantra identity, no Sanskrit and no non-translation
predicate is touched, and the executor refuses if any of those move.

Usage:
    python scripts/m13_rv_dvipada_spine_realignment.py [--execute] [--backup DIR]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neo4j import GraphDatabase, Session  # noqa: E402

from vedagraph.graph.corrections import verify_corrections_applied  # noqa: E402
from vedagraph.graph.projection import (  # noqa: E402
    _passage_key_maps,
    build_correction_applier,
    iter_translation_nodes,
)

OUT = PROJECT_ROOT / "data" / "staging" / "integration" / "m13_receipt.json"
PLAN = PROJECT_ROOT / "data" / "staging" / "translation" / "m13_plan.json"
AUDIT = PROJECT_ROOT / "data" / "staging" / "translation" / "rv_1_65_1_70_pre_fix_audit.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}
GAP = "GAP-TRANSLATION-006"

#: Only these hymns may change. Asserted against the plan before anything is written, so a
#: declaration that reached beyond the span is refused rather than executed.
ALLOWED_PREFIXES = tuple(f"VG:RV:SAK:M01:S{n:03d}:" for n in range(65, 71))


def plan_from_projection() -> list[dict[str, Any]]:
    """The corrected rows, read from the projection rather than recomputed.

    Every field the migration writes comes from here. The plan is the promise and the same
    list is what gets executed.
    """
    applier = build_correction_applier(PROJECT_ROOT)
    rows = list(iter_translation_nodes(PROJECT_ROOT, applier))
    verify_corrections_applied(applier)
    key_by_id, _ = _passage_key_maps(PROJECT_ROOT)
    by_new_id = {str(r["translation_id"]): r for r in rows}

    plan: list[dict[str, Any]] = []
    for move in applier.spine_moves:
        row = by_new_id.get(str(move["new_translation_id"]))
        if row is None:
            raise SystemExit(
                f"{move['correction_id']}: the projection produced no row for "
                f"{move['new_translation_id']}; plan and projection disagree."
            )
        landed = key_by_id.get(str(row["passage_id"]))
        if landed != move["to_canonical_key"]:
            raise SystemExit(
                f"{move['correction_id']}: projection landed the row on {landed}, the move "
                f"says {move['to_canonical_key']}."
            )
        plan.append(
            {
                **move,
                "text": row["text"],
                "text_sha256": hashlib.sha256(
                    str(row["text"]).encode("utf-8")
                ).hexdigest(),
                "alignment_level": row["alignment_level"],
                "source_unit_recorded": row["source_unit"],
                "source_verse_spine": row["source_verse_spine"],
                "upstream_correction_reason": row["upstream_correction_reason"],
            }
        )
    # DESCENDING source unit, per hymn. ``translation_id`` is derived from the passage it
    # attaches to, so unit 2's corrected id is precisely the id unit 3 currently holds -- 12
    # of the 25 moved rows collide that way, and ``translation_id_unique`` would abort the
    # transaction. Highest unit first vacates each slot before the row below it needs one,
    # and the order is acyclic because the top units move to indices above the occupied
    # range: for RV 1.65, u5 005->009, u4 004->007, u3 003->005, u2 002->003.
    plan.sort(key=lambda p: (p["from_canonical_key"].rsplit(":V", 1)[0], -int(p["source_unit"])))
    return plan


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "translation_nodes": int(
            session.run("MATCH (t:Translation) RETURN count(t) AS c").single()["c"]
        ),
        "translation_edges": int(
            session.run("MATCH ()-[r:HAS_TRANSLATION]->() RETURN count(r) AS c").single()["c"]
        ),
        "rv_translated_mantras": int(
            session.run(
                "MATCH (m:Mantra {veda:'RV'}) WHERE (m)-[:HAS_TRANSLATION]->() "
                "RETURN count(m) AS c"
            ).single()["c"]
        ),
        "core": {
            str(r["veda"]): int(r["n"])
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def span_state(session: Session) -> list[dict[str, Any]]:
    """Which verse in the span carries which translation, right now."""
    return [
        dict(r)
        for r in session.run(
            """
            MATCH (m:Mantra {veda:'RV'})
            WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
            OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
            RETURN m.canonical_key AS key, t.translation_id AS translation_id,
                   t.text AS text, t.alignment_level AS alignment_level
            ORDER BY key
            """,
            prefixes=list(ALLOWED_PREFIXES),
        )
    ]


def outside_digest(session: Session) -> dict[str, str]:
    """A digest of every translation attachment OUTSIDE the span, plus the Sanskrit inside it.

    Compared before and after. A count would not do: a swap of equal size leaves a count
    unchanged, which is the mistake the dependency work had to correct twice.
    """
    outside = session.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE NOT any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
        RETURN m.canonical_key + '|' + t.translation_id AS pair ORDER BY pair
        """,
        prefixes=list(ALLOWED_PREFIXES),
    )
    sanskrit = session.run(
        """
        MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(v:TextVersion)
        WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
        RETURN m.canonical_key + '|' + v.text_version_id + '|' + v.content_sha256 AS row
        ORDER BY row
        """,
        prefixes=list(ALLOWED_PREFIXES),
    )
    others = session.run(
        """
        MATCH (m:Mantra)-[r]->(x)
        WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
          AND type(r) <> 'HAS_TRANSLATION'
        RETURN m.canonical_key + '|' + type(r) AS row ORDER BY row
        """,
        prefixes=list(ALLOWED_PREFIXES),
    )
    return {
        "translation_attachments_outside_the_span": hashlib.sha256(
            "\n".join(str(r["pair"]) for r in outside).encode("utf-8")
        ).hexdigest(),
        "sanskrit_inside_the_span": hashlib.sha256(
            "\n".join(str(r["row"]) for r in sanskrit).encode("utf-8")
        ).hexdigest(),
        "non_translation_edges_inside_the_span": hashlib.sha256(
            "\n".join(str(r["row"]) for r in others).encode("utf-8")
        ).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    if not AUDIT.exists():
        print(f"  {AUDIT} is missing. Run scripts/rv_dvipada_spine_audit.py first.")
        return 1
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if not audit.get("reproduces_wave4_claim"):
        print("  the pre-fix audit does not reproduce the measured defect; refusing.")
        return 1

    plan = plan_from_projection()
    moves = [p for p in plan if p["moved"]]
    stays = [p for p in plan if not p["moved"]]

    stray = [
        p
        for p in plan
        if not p["from_canonical_key"].startswith(ALLOWED_PREFIXES)
        or not p["to_canonical_key"].startswith(ALLOWED_PREFIXES)
    ]
    if stray:
        print(f"  REFUSING: {len(stray)} planned change(s) fall outside RV 1.65-1.70:")
        for p in stray[:5]:
            print(f"    {p['from_canonical_key']} -> {p['to_canonical_key']}")
        return 1
    if len(moves) != int(audit["measurement"]["wrongly_attached"]):
        print(
            f"  REFUSING: the plan moves {len(moves)} rows, the audit measured "
            f"{audit['measurement']['wrongly_attached']} wrong. These must agree."
        )
        return 1

    PLAN.write_text(
        json.dumps(
            {
                "artifact": "M13_PLAN",
                "gap": GAP,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "source": "vedagraph.graph.projection over the declared spine corrections",
                "rows": plan,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            before_digests = outside_digest(session)
            before_span = span_state(session)
            if before["core"] != CORE:
                print(f"  REFUSING: core corpus is {before['core']}.")
                return 1

            present = {
                str(r["translation_id"]): str(r["key"])
                for r in before_span
                if r["translation_id"]
            }
            missing = [p for p in plan if p["old_translation_id"] not in present]
            misplaced = [
                p
                for p in plan
                if p["old_translation_id"] in present
                and present[p["old_translation_id"]] != p["from_canonical_key"]
            ]
            if missing or misplaced:
                print(
                    f"  REFUSING: {len(missing)} planned row(s) are not in the graph and "
                    f"{len(misplaced)} sit somewhere other than the plan says."
                )
                for p in (missing + misplaced)[:5]:
                    print(f"    {p['old_translation_id']} expected at {p['from_canonical_key']}")
                return 1

            mode = "EXECUTING" if args.execute else "DRY RUN"
            print()
            print(f"  M13 RV DVIPADA SPINE REALIGNMENT  {mode}")
            print()
            print(f"  plan rows                        {len(plan)}")
            print(f"    moved to a new anchor          {len(moves)}")
            print(f"    already on their anchor        {len(stays)}")
            print()
            print("  PROMISED DELTA")
            print("    nodes created                  0")
            print("    nodes deleted                  0")
            print(f"    nodes updated                  {len(plan)}")
            print(f"    relationships created          {len(moves)}")
            print(f"    relationships deleted          {len(moves)}")
            print("    node total delta               0")
            print("    relationship total delta       0")
            print()
            for p in moves[:6]:
                print(
                    f"    unit {p['source_unit']}  "
                    f"{p['from_canonical_key'].split(':', 4)[4]} -> "
                    f"{p['to_canonical_key'].split(':', 4)[4]}  "
                    f"covers {[k.split(':')[5] for k in p['covers_canonical_keys']]}"
                )
            if len(moves) > 6:
                print(
                    f"    ... {len(moves) - 6} more, all in "
                    "data/staging/translation/m13_plan.json"
                )
            print()

            written = 0
            edges_made = 0
            if args.execute:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                with session.begin_transaction() as tx:
                    # One statement per row rather than one UNWIND, so a partial failure
                    # cannot leave a row detached from every verse.
                    for p in plan:
                        if p["moved"]:
                            # Belt and braces on the ordering above: if the slot is still
                            # occupied by someone else, stop rather than trust the sort.
                            occupied = tx.run(
                                "MATCH (t:Translation {translation_id: $new_id}) "
                                "WHERE t.translation_id <> $old_id RETURN count(t) AS n",
                                new_id=p["new_translation_id"],
                                old_id=p["old_translation_id"],
                            ).single()
                            if occupied is not None and int(occupied["n"]):
                                raise SystemExit(
                                    f"unit {p['source_unit']} of "
                                    f"{p['from_canonical_key']}: its corrected id is still "
                                    "held by another row. The plan order did not free the "
                                    "slot; transaction rolled back."
                                )
                        result = tx.run(
                            """
                            MATCH (old:Mantra {canonical_key: $from_key})
                                  -[e:HAS_TRANSLATION]->(t:Translation {translation_id: $old_id})
                            MATCH (anchor:Mantra {canonical_key: $to_key})
                            SET t.translation_id = $new_id,
                                t.passage_id = anchor.entity_id,
                                t.alignment_level = $alignment_level,
                                t.covers_canonical_keys = $covers,
                                t.source_unit = $unit,
                                t.source_verse_spine = $spine,
                                t.upstream_correction_id = $correction_id,
                                t.upstream_correction_reason = $reason,
                                t.spine_corrected_from = $from_key,
                                t.spine_corrected_from_translation_id = $old_id,
                                t.m13_applied = $at
                            WITH old, e, t, anchor
                            DELETE e
                            MERGE (anchor)-[n:HAS_TRANSLATION]->(t)
                            SET n.language = 'en', n.translator = t.translator,
                                n.quality_tier = 'TIER_A',
                                n.knowledge_layer = 'L1_SOURCE_EXPLICIT',
                                n.evidence_basis = 'STRUCTURAL',
                                n.attribution_precision = 'NOT_AN_ATTRIBUTION',
                                n.grade_basis = 'corpus structure as printed by the edition'
                            RETURN count(n) AS n
                            """,
                            from_key=p["from_canonical_key"],
                            to_key=p["to_canonical_key"],
                            old_id=p["old_translation_id"],
                            new_id=p["new_translation_id"],
                            alignment_level=p["alignment_level"],
                            covers=p["covers_canonical_keys"],
                            unit=p["source_unit"],
                            spine=p["source_verse_spine"],
                            correction_id=p["correction_id"],
                            reason=p["upstream_correction_reason"],
                            at=stamp,
                        ).single()
                        if result is None or int(result["n"]) != 1:
                            raise SystemExit(
                                f"row {p['old_translation_id']} did not update exactly once; "
                                "transaction rolled back"
                            )
                        written += 1
                        if p["moved"]:
                            edges_made += 1
                    tx.commit()

            after = census(session)
            after_digests = outside_digest(session)
            after_span = span_state(session)

            landed = {
                str(r["translation_id"]): str(r["key"])
                for r in after_span
                if r["translation_id"]
            }
            wrong_still = [
                p for p in plan if landed.get(p["new_translation_id"]) != p["to_canonical_key"]
            ]
            # ATTACHMENT, not id presence. The first version of this check asked whether the
            # old translation_id still existed anywhere and reported 12 survivors on a
            # migration that was completely correct -- because the id is derived from the
            # passage, so unit 3's old id (derived from V003) is legitimately reused by unit 2
            # once unit 2 moves onto V003. Asking about ids answered a question nobody had.
            text_at = {
                str(r["key"]): str(r["text"] or "") for r in after_span if r["translation_id"]
            }
            old_attachments_remaining = [
                p["from_canonical_key"]
                for p in plan
                if p["moved"] and text_at.get(p["from_canonical_key"]) == p["text"]
            ]
            old_ids_remaining = old_attachments_remaining
            translated_after = sorted(
                str(r["key"]).split(":", 4)[4] for r in after_span if r["translation_id"]
            )

            actual = {
                "nodes": after["nodes"] - before["nodes"],
                "relationships": after["relationships"] - before["relationships"],
                "translation_nodes": after["translation_nodes"] - before["translation_nodes"],
                "translation_edges": after["translation_edges"] - before["translation_edges"],
            }
            promised = {
                "nodes": 0,
                "relationships": 0,
                "translation_nodes": 0,
                "translation_edges": 0,
            }
            unchanged_outside = before_digests == after_digests

            receipt = {
                "migration": "M13_RV_DVIPADA_SPINE_REALIGNMENT",
                "gap": GAP,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "correction_source": (
                    "data/registry/upstream_corrections.yaml via "
                    "vedagraph.graph.projection -- the same source a rebuild reads"
                ),
                "plan_artifact": str(PLAN.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "audit_artifact": str(AUDIT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "rows_planned": len(plan),
                "rows_moved": len(moves),
                "rows_already_anchored": len(stays),
                "rows_updated": written,
                "edges_recreated": edges_made,
                "promised_delta": promised,
                "actual_delta": actual,
                "delta_matched_promise": promised == actual,
                "census_before": before,
                "census_after": after,
                "core_corpus_unchanged": after["core"] == CORE,
                "digests_before": before_digests,
                "digests_after": after_digests,
                "nothing_outside_the_span_changed": unchanged_outside,
                "corrected_rows_not_where_planned": [
                    p["new_translation_id"] for p in wrong_still
                ],
                "old_attachments_still_present": old_attachments_remaining,
                "old_attachment_check": (
                    "a verse the row moved AWAY from still serving that row's text; "
                    "NOT the survival of a derived translation_id, which is reused by design"
                ),
                "translated_verses_after": translated_after,
                "moves": [
                    {
                        k: p[k]
                        for k in (
                            "correction_id",
                            "source_unit",
                            "from_canonical_key",
                            "to_canonical_key",
                            "covers_canonical_keys",
                            "old_translation_id",
                            "new_translation_id",
                            "alignment_level",
                            "text_sha256",
                            "moved",
                        )
                    }
                    for p in plan
                ],
            }
            receipt["complete"] = bool(
                receipt["delta_matched_promise"]
                and receipt["core_corpus_unchanged"]
                and unchanged_outside
                and not wrong_still
                and not old_ids_remaining
            )
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print("  ACTUAL DELTA")
            for key in promised:
                print(f"    {key:<28} {actual[key]:+}  (promised {promised[key]:+})")
            print()
            print(f"  delta matched promise            {receipt['delta_matched_promise']}")
            print(f"  core corpus unchanged            {receipt['core_corpus_unchanged']}")
            print(f"  nothing outside the span moved   {unchanged_outside}")
            print(f"  rows not where planned           {len(wrong_still)}")
            print(f"  old attachments still present    {len(old_ids_remaining)}")
            print(f"  RV translated mantras            {after['rv_translated_mantras']}")
            print()
            print(f"  receipt: {OUT.relative_to(PROJECT_ROOT)}")
            if not args.execute:
                print("\n  DRY RUN ONLY. Re-run with --execute --backup <dir>.")
                return 0
            return 0 if receipt["complete"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
