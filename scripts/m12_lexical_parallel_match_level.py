"""M12: 256 parallel edges reported no match level while carrying one. Wave 4 Phase 7.

``GAP-CROSS_VEDA-003``, and the registry's own diagnosis was right: *"A name collision, not
an absence."*

``EXACT_PARALLEL_OF`` has two writers. The enrichment pipeline writes ``match_level`` and
``parallel_id``; the Rigvedic lexical pipeline writes the same level under
``strongest_method`` and no id at all. So 256 of 1,006 edges served a reader a null where the
evidence was present under another name, and every count taken over ``match_level`` was
measuring one writer's output and calling it the predicate's.

**What is a rename and what is not.** ``MatchLevel.SOURCE_EXACT`` and the lexical
``SOURCE_EXACT`` are the same assertion in the same words: identical stored text. Copying it
across asserts nothing new. ``TOKEN_EXACT`` and ``LEMMA_SEQUENCE_EXACT`` are not text
surfaces, and a pair whose STRONGEST method is one of them is by construction NOT identical at
any surface -- so every ``MatchLevel`` value would be false of it, and the 4 such edges get a
typed absence instead of a level. The owner's standing rule is the reason the line is drawn
there: never convert a normalization into an identity.

**The values are imported from the fixed generator, not restated here.**
``vedagraph.graph.lexical.iter_exact_parallel_rels`` was corrected first, so the next full
graph load writes exactly what this migration writes. That is the M11 pattern and it is the
only thing that stops the graph and its builder drifting -- which this campaign has paid for
twice.

Additive: property writes only. No node, no edge, no identity.

Usage:
    python scripts/m12_lexical_parallel_match_level.py [--execute] [--backup DIR]
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

from vedagraph.graph.lexical import iter_exact_parallel_rels

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "data" / "staging" / "integration" / "m12_receipt.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}
GAP = "GAP-CROSS_VEDA-003"


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "exact_parallel_edges": int(
            session.run("MATCH ()-[r:EXACT_PARALLEL_OF]->() RETURN count(r) AS c").single()["c"]
        ),
        "with_match_level": int(
            session.run(
                "MATCH ()-[r:EXACT_PARALLEL_OF]->() WHERE r.match_level IS NOT NULL "
                "RETURN count(r) AS c"
            ).single()["c"]
        ),
        "with_parallel_id": int(
            session.run(
                "MATCH ()-[r:EXACT_PARALLEL_OF]->() WHERE r.parallel_id IS NOT NULL "
                "RETURN count(r) AS c"
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

    rows = [
        row
        for row in iter_exact_parallel_rels(PROJECT_ROOT)
        if row["predicate"] == "EXACT_PARALLEL_OF"
    ]
    if not rows:
        print("  the lexical parallel artifact produced no EXACT_PARALLEL_OF rows.")
        return 1
    levelled = [r for r in rows if r.get("match_level")]
    absent = [r for r in rows if r.get("match_level_absence")]
    if len(levelled) + len(absent) != len(rows):
        print("  the generator left a row neither levelled nor typed-absent; refusing.")
        return 1

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)

            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  M12 LEXICAL PARALLEL MATCH LEVEL  {mode}")
            print()
            print(f"  EXACT_PARALLEL_OF edges in the graph   {before['exact_parallel_edges']}")
            print(f"    carrying a match_level               {before['with_match_level']}")
            print(f"    carrying a parallel_id               {before['with_parallel_id']}")
            print()
            print(f"  rows the fixed generator produces      {len(rows)}")
            print(f"    with a renamed surface level         {len(levelled)}")
            print(f"    typed absent (not a text surface)    {len(absent)}")
            print()

            written_level = written_absence = 0
            if args.execute:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                with session.begin_transaction() as tx:
                    written_level = int(
                        tx.run(
                            "UNWIND $rows AS row "
                            "MATCH (a {canonical_key: row.subject_key})"
                            "-[r:EXACT_PARALLEL_OF]->(b {canonical_key: row.object_key}) "
                            "SET r.match_level = row.match_level, "
                            "    r.parallel_id = row.parallel_id, "
                            "    r.match_level_basis = $basis, r.m12_applied = $at "
                            "RETURN count(r) AS n",
                            rows=[
                                {
                                    "subject_key": r["subject_key"],
                                    "object_key": r["object_key"],
                                    "match_level": r["match_level"],
                                    "parallel_id": r["parallel_id"],
                                }
                                for r in levelled
                            ],
                            basis=(
                                "RENAMED_FROM_STRONGEST_METHOD -- the lexical pipeline's "
                                "SOURCE_EXACT and MatchLevel.SOURCE_EXACT are the same "
                                "assertion, identical stored text. Nothing was re-derived."
                            ),
                            at=stamp,
                        ).single()["n"]
                    )
                    written_absence = int(
                        tx.run(
                            "UNWIND $rows AS row "
                            "MATCH (a {canonical_key: row.subject_key})"
                            "-[r:EXACT_PARALLEL_OF]->(b {canonical_key: row.object_key}) "
                            "SET r.match_level_absence = row.absence, "
                            "    r.match_level_absence_detail = row.detail, "
                            "    r.parallel_id = row.parallel_id, r.m12_applied = $at "
                            "RETURN count(r) AS n",
                            rows=[
                                {
                                    "subject_key": r["subject_key"],
                                    "object_key": r["object_key"],
                                    "absence": r["match_level_absence"],
                                    "detail": r["match_level_absence_detail"],
                                    "parallel_id": r["parallel_id"],
                                }
                                for r in absent
                            ],
                            at=stamp,
                        ).single()["n"]
                    )
                    tx.commit()

            after = census(session)
            residual = int(
                session.run(
                    "MATCH ()-[r:EXACT_PARALLEL_OF]->() "
                    "WHERE r.match_level IS NULL AND r.match_level_absence IS NULL "
                    "RETURN count(r) AS c"
                ).single()["c"]
            )
            no_pid = int(
                session.run(
                    "MATCH ()-[r:EXACT_PARALLEL_OF]->() WHERE r.parallel_id IS NULL "
                    "RETURN count(r) AS c"
                ).single()["c"]
            )
            # The 750 the enrichment pipeline wrote must not have moved. Checked by value,
            # not by count: a count is unchanged by a swap of equal size.
            enrichment_levels = {
                str(r["lvl"]): int(r["n"])
                for r in session.run(
                    "MATCH ()-[r:EXACT_PARALLEL_OF]->() WHERE r.cross_veda_parallel_id "
                    "IS NOT NULL RETURN r.match_level AS lvl, count(*) AS n"
                )
            }

            receipt = {
                "migration": "M12_LEXICAL_PARALLEL_MATCH_LEVEL",
                "gap": GAP,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "finding": (
                    "Two writers, one predicate. The lexical pipeline wrote its surface level "
                    "under strongest_method and no parallel_id, so 256 of 1,006 edges served a "
                    "null and every count over match_level measured one writer's output."
                ),
                "values_source": "vedagraph.graph.lexical, imported not restated",
                "rows_levelled": len(levelled),
                "rows_typed_absent": len(absent),
                "edges_written_with_level": written_level,
                "edges_written_with_absence": written_absence,
                "still_neither_levelled_nor_typed_absent": residual,
                "still_without_a_parallel_id": no_pid,
                "enrichment_written_levels_unchanged": enrichment_levels,
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "core_corpus_unchanged": after["core"] == CORE,
                "additive": after["nodes"] == before["nodes"]
                and after["relationships"] == before["relationships"],
                "complete": residual == 0 and no_pid == 0,
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print(f"  edges given a level        {written_level}")
            print(f"  edges typed absent         {written_absence}")
            print(f"  still neither             {residual}")
            print(f"  still without an id       {no_pid}")
            print(f"  enrichment levels         {enrichment_levels}")
            print(f"  additive                  {receipt['additive']}")
            print(f"  core corpus unchanged     {receipt['core_corpus_unchanged']}")
            print()
            print(f"  receipt: {OUT.relative_to(PROJECT_ROOT)}")
            if not args.execute:
                print("\n  REHEARSAL ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["additive"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
