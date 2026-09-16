"""M11: correct the deity attribution-scope note on 214 live nodes. Wave 4 Phase 6.

``GAP-ATTRIBUTION-009``. Every ``:Devata`` carried::

    "The Anukramani attribution layer covers the Rigveda only. A zero for SV, YV or AV
     means that corpus has no attribution layer, NOT that the deity is absent from it."

The second sentence is false. The Atharvaveda has an attribution layer: 5,385
``HAS_DEVATA_ASCRIPTION`` edges over 4,665 of its 5,839 mantras, from Whitney's
Bṛhatsarvānukramaṇī. What it lacks is a layer that *resolves* those ascriptions to a
``:Devata``, which is why the count on this node is zero.

It matters more here than in the insight caveat, because ``api/ask/evidence.py`` reads this
property as the qualifier attached to an absence -- so a false "no attribution layer" became
a model-visible justification for a false answer.

**The corrected text is imported from the generator, not restated.**
``vedagraph.domain.taxonomy`` was fixed first, so a future ``build_domain_v2.py`` writes the
same string this migration writes. Duplicating the sentence here is how the graph and its
builder drift, and this campaign has paid for that twice.

Why not simply re-run the builder: ``build_domain_v2.py`` rebuilds the entire V2 domain pass.
Running it to change one property mid-audit would re-project mentions, taxonomy, profiles and
entity projections, and any of those moving would invalidate the verification chain this
round is in the middle of. A targeted, receipted write of one property is auditable; a
whole-layer rebuild to fix a sentence is not.

Usage:
    python scripts/m11_devata_scope_note_correction.py [--execute] [--backup DIR]
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

from vedagraph.domain.taxonomy import load_taxonomy

OUT = pathlib.Path("data/staging/integration/m11_receipt.json")
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: The claim that must not survive anywhere on a Devata node.
FALSE_FRAGMENT = "no attribution layer"


def corrected_note() -> str:
    """The note as the fixed generator produces it. Read, never restated.

    Taken from the first overlay entry: the property is identical on all 214 nodes by
    construction -- ``as_properties`` sets one constant -- and reading it from the generator
    is what keeps this migration from becoming a second source of the sentence.
    """
    overlay, _ = load_taxonomy(PROJECT_ROOT)
    entries = list(overlay.values()) if isinstance(overlay, dict) else list(overlay)
    # The method is as_row(), not as_properties(). Checked rather than assumed: a getattr
    # with a silent fallback would have produced an empty note set and this migration would
    # have written nothing while reporting success.
    notes = {
        str(row["attribution_scope_note"])
        for row in (entry.as_row() for entry in entries)
        if row.get("attribution_scope_note")
    }
    if len(notes) != 1:
        raise SystemExit(
            f"expected one attribution_scope_note in the overlay, found {len(notes)}. "
            "A migration that picks one of several would be guessing."
        )
    return notes.pop()


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    note = corrected_note()
    if FALSE_FRAGMENT in note:
        print(f"  REFUSING: the generator's note still contains {FALSE_FRAGMENT!r}. "
              "Fix vedagraph.domain.taxonomy first; this migration only propagates it.")
        return 1

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            row = session.run(
                "MATCH (d:Devata) RETURN count(d) AS total, "
                "count(d.attribution_scope_note) AS with_note, "
                "sum(CASE WHEN d.attribution_scope_note CONTAINS $bad THEN 1 ELSE 0 END) "
                "  AS carrying_the_false_claim, "
                "sum(CASE WHEN d.attribution_scope_note = $note THEN 1 ELSE 0 END) "
                "  AS already_corrected",
                bad=FALSE_FRAGMENT,
                note=note,
            ).single()
            total = int(row["total"])
            false_claim = int(row["carrying_the_false_claim"])
            already = int(row["already_corrected"])

            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  M11 DEVATA SCOPE NOTE CORRECTION  {mode}")
            print()
            print(f"  :Devata nodes                    {total}")
            print(f"  carrying a note                   {int(row['with_note'])}")
            print(f"  carrying the false claim          {false_claim}")
            print(f"  already corrected                 {already}")
            print(f"  corrected note length             {len(note)} chars")
            print()

            written = 0
            if args.execute and false_claim:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                with session.begin_transaction() as tx:
                    written = int(
                        tx.run(
                            "MATCH (d:Devata) WHERE d.attribution_scope_note CONTAINS $bad "
                            "SET d.attribution_scope_note = $note, d.m11_applied = $at "
                            "RETURN count(d) AS n",
                            bad=FALSE_FRAGMENT,
                            note=note,
                            at=stamp,
                        ).single()["n"]
                    )
                    tx.commit()

            after = census(session)
            residual = int(
                session.run(
                    "MATCH (d:Devata) WHERE d.attribution_scope_note CONTAINS $bad "
                    "RETURN count(d) AS c",
                    bad=FALSE_FRAGMENT,
                ).single()["c"]
            )
            receipt = {
                "migration": "M11_DEVATA_SCOPE_NOTE_CORRECTION",
                "gap": "GAP-ATTRIBUTION-009",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "false_claim_removed": FALSE_FRAGMENT,
                "note_source": "vedagraph.domain.taxonomy, imported not restated",
                "devata_nodes": total,
                "carrying_the_false_claim_before": false_claim,
                "nodes_written": written,
                "still_carrying_it": residual,
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "core_corpus_unchanged": after["core"] == CORE,
                "additive": after["nodes"] == before["nodes"]
                and after["relationships"] == before["relationships"],
                "complete": residual == 0,
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print(f"  nodes written                     {written}")
            print(f"  still carrying the false claim    {residual}")
            print(f"  census unchanged                  {receipt['additive']}")
            print(f"  core corpus unchanged             {receipt['core_corpus_unchanged']}")
            print()
            print(f"  receipt: {OUT}")
            if not args.execute:
                print("\n  REHEARSAL ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["additive"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
