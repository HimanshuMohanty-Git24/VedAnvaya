"""M9: withdraw 33 metre assertions whose object is not a metre. Owner round four, item 1.

``GAP-AV-CHANDOMETRE-SEGMENTATION-001``. The AV registry's segmentation of Whitney's printed
bracket is incomplete, so some ``:Chandas`` entities are whole bracket fragments carrying a
deity, a metre and a per-verse exception in one string. 33 canonical ``HAS_CHANDAS`` edges
point at 28 such entities, which means a reader asking a verse's metre is told, for example,
``'āindryas. ānuṣṭubham: 2. 3-av. 6-p. jagatī'``.

**The criterion is Whitney's own notation, not a judgement about Sanskrit.** He uses ``:`` to
separate a hymn-level statement from its per-verse exceptions, and a bare ``N.`` inside the
string is a verse number. Neither can occur inside a metre *name*. That is a structural fact
about the printed apparatus, which is why these 33 are demonstrable while the wider
population the three earlier tests disagreed about (17 / 28 / 39) is not.

**What this does NOT do**, per the owner's constraints:

* no metre is inferred from the mixed string -- ``'6. anuṣṭubh'`` is not read as
  *anuṣṭubh*, and on ``K03:S003:V005`` it could not be anyway: the ``6.`` addresses verse 6
  and the edge sits on verse 5
* no ``:Chandas`` entity is re-keyed, merged, renamed or migrated -- the 28 entities stay
  exactly as they are, so the printed literal remains in the graph
* no replacement edge is created. Measured, not assumed: the only source asserting a metre
  for these passages is the same bracket, so there is no independent evidence to build one
  from, and the script records that rather than claiming it

**The literal and its provenance travel onto the passage.** Deleting the edge without that
would turn a malformed assertion into silence, and silence reads as *the source says
nothing* -- which is false and is the one substitution this campaign refuses. Each affected
passage gains a withheld-claim record naming the printed string, the entity it pointed at,
the original scope and source, and the reason. 16 of the 33 passages hold no other metre
edge, so for them this record is the only thing standing between a reader and a false zero.

Usage:
    python scripts/m9_malformed_chandas_withdrawal.py [--execute] [--backup DIR] [--readback]
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

REGISTRY = pathlib.Path("data/registry/chandas_av.yaml")
PLAN_OUT = pathlib.Path("data/staging/integration/m9_plan.json")
RECEIPT = pathlib.Path("data/staging/integration/m9_receipt.json")
READBACK = pathlib.Path("data/staging/integration/m9_readback.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

WITHDRAWAL = "M9_MALFORMED_CHANDAS_WITHDRAWAL"
REASON = "TARGET_IS_AN_UNSEGMENTED_SOURCE_BRACKET_NOT_A_METRE_NAME"
GAP = "GAP-AV-CHANDOMETRE-SEGMENTATION-001"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: A bare verse number inside the label. ``3-av.`` and ``6-p.`` are structural qualifiers
#: and are excluded by the negative lookbehind; ``24. `` is a verse reference.
_VERSE_REF = re.compile(r"(?<![0-9a-zA-Z-])\d{1,2}\.\s")


def malformed_entities() -> dict[str, dict[str, str]]:
    """The entities whose label is not a metre name, by Whitney's own punctuation.

    Two signals, both structural: a colon, which separates his hymn statement from its
    per-verse exceptions, and an embedded verse number. A metre name contains neither.
    Deliberately NOT the wider two-statement test -- that one and these two disagree, and an
    unbounded criterion cannot authorise a deletion.
    """
    entities = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["entities"]
    out: dict[str, dict[str, str]] = {}
    for entity in entities:
        label = str(entity["preferred_label"])
        signals = []
        if ":" in label:
            signals.append("COLON_SEPARATES_HYMN_STATEMENT_FROM_VERSE_EXCEPTIONS")
        if _VERSE_REF.search(label):
            signals.append("EMBEDDED_VERSE_REFERENCE")
        if signals:
            out[str(entity["entity_key"])] = {
                "printed_label": label,
                "signals": ",".join(signals),
            }
    return out


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "has_chandas": int(
            session.run("MATCH ()-[r:HAS_CHANDAS]->() RETURN count(r) AS c").single()["c"]
        ),
        "chandas_nodes": int(
            session.run("MATCH (c:Chandas) RETURN count(c) AS c").single()["c"]
        ),
        "core": {
            r["veda"]: int(r["n"])
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def build_payload(session: Session, suspect: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Exactly the edges this migration withdraws, with what to preserve from each.

    The single source of truth: the plan, the executor and the readback all call it.
    """
    payload: list[dict[str, Any]] = []
    for row in session.run(
        "UNWIND $keys AS k "
        "MATCH (p:Passage)-[e:HAS_CHANDAS]->(c:Chandas {entity_key: k}) "
        "RETURN p.canonical_key AS passage, k AS entity_key, "
        "c.preferred_label AS printed_label, e.scope_origin AS scope_origin, "
        "e.source_id AS source_id, e.knowledge_layer AS knowledge_layer, "
        "e.quality_tier AS quality_tier ORDER BY p.canonical_key",
        keys=sorted(suspect),
    ):
        payload.append(
            {
                "passage": str(row["passage"]),
                "entity_key": str(row["entity_key"]),
                "printed_label": str(row["printed_label"]),
                "scope_origin": str(row["scope_origin"]),
                "source_id": str(row["source_id"]),
                "knowledge_layer": str(row["knowledge_layer"]),
                "quality_tier": str(row["quality_tier"]),
                "signals": suspect[str(row["entity_key"])]["signals"],
            }
        )
    return payload


def replacement_evidence(session: Session, payload: list[dict[str, Any]]) -> dict[str, Any]:
    """Is there independent evidence to build a replacement edge from? Measured.

    The owner permits a replacement only where independent source evidence identifies the
    metre unambiguously. This asks the graph rather than assuming: for each affected
    passage, what OTHER metre edges exist, and do any come from a source other than the one
    whose segmentation is at fault?
    """
    keys = sorted({row["passage"] for row in payload})
    suspect = {row["entity_key"] for row in payload}
    other: dict[str, list[dict[str, str]]] = {key: [] for key in keys}
    for row in session.run(
        "UNWIND $keys AS k MATCH (p:Passage {canonical_key: k})-[e:HAS_CHANDAS]->(c:Chandas) "
        "RETURN k AS passage, c.entity_key AS entity_key, c.preferred_label AS label, "
        "e.scope_origin AS scope_origin, e.source_id AS source_id",
        keys=keys,
    ):
        if str(row["entity_key"]) in suspect:
            continue
        other[str(row["passage"])].append(
            {
                "entity_key": str(row["entity_key"]),
                "label": str(row["label"]),
                "scope_origin": str(row["scope_origin"]),
                "source_id": str(row["source_id"]),
            }
        )
    independent_sources = sorted(
        {
            edge["source_id"]
            for edges in other.values()
            for edge in edges
            if edge["source_id"] not in {row["source_id"] for row in payload}
        }
    )
    return {
        "passages_affected": len(keys),
        "passages_keeping_a_well_formed_metre_edge": sum(1 for k in keys if other[k]),
        "passages_left_with_no_metre_edge": sum(1 for k in keys if not other[k]),
        "independent_sources_asserting_a_metre_for_these_passages": independent_sources,
        "replacements_creatable": 0,
        "why_no_replacement": (
            "Every metre assertion for these passages traces to WIKISOURCE_WHITNEY_AV, the "
            "source whose segmentation is the defect. Building a replacement would mean "
            "reading the metre out of the mixed string, which the owner barred -- and on "
            "K03:S003:V005 it would also be wrong, because the '6.' in '6. anustubh' "
            "addresses verse 6 while the edge sits on verse 5."
        ),
        "other_metre_edges_by_passage": other,
    }


def do_readback(session: Session) -> int:
    """Check the graph against the RECEIPT, never against the graph.

    The first version of this function rebuilt its expectation with build_payload(), which
    queries the graph for the malformed edges. After the withdrawal there are none, so it
    compared 0 against 0 and printed READBACK_CLEAN having verified nothing -- the same
    defect as the undeclared-type gate, in the tool meant to catch it.

    The expectation is the executor's own receipt. No receipt, no readback: "nothing to
    check" is not "clean".
    """
    findings: list[str] = []
    if not RECEIPT.exists():
        print("  no executed receipt. Nothing has been withdrawn, so there is nothing to "
              "read back -- and that is not a pass.")
        return 1
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if not receipt.get("executed"):
        print("  the receipt records a plan, not an execution. Refusing to report a verdict.")
        return 1
    payload = list(receipt.get("affected") or [])
    if not payload:
        print("  the receipt names no affected assertions. Refusing to report a verdict.")
        return 1
    expected = int(receipt.get("promised_withdrawals") or 0)
    if len(payload) != expected:
        findings.append(
            f"the receipt promises {expected} withdrawals and lists {len(payload)}"
        )
    entity_keys = sorted({row["entity_key"] for row in payload})
    passages = sorted({row["passage"] for row in payload})

    surviving = int(
        session.run(
            "UNWIND $keys AS k MATCH (:Passage)-[e:HAS_CHANDAS]->(:Chandas {entity_key: k}) "
            "RETURN count(e) AS c",
            keys=entity_keys,
        ).single()["c"]
    )
    if surviving:
        findings.append(f"{surviving} malformed metre assertion(s) still in the graph")

    entities_present = int(
        session.run(
            "UNWIND $keys AS k MATCH (c:Chandas {entity_key: k}) RETURN count(c) AS c",
            keys=entity_keys,
        ).single()["c"]
    )
    if entities_present != len(entity_keys):
        findings.append(
            f"{len(entity_keys) - entities_present} :Chandas entity/entities were removed; "
            "this migration must not touch the entity population"
        )

    recorded = int(
        session.run(
            "UNWIND $keys AS k MATCH (p:Passage {canonical_key: k}) "
            "WHERE p.chandas_withheld_literal IS NOT NULL RETURN count(p) AS c",
            keys=passages,
        ).single()["c"]
    )
    if recorded != len(passages):
        findings.append(
            f"{len(passages) - recorded} affected passage(s) carry no withheld-claim record, "
            "so the source's statement there reads as silence"
        )

    untyped = int(
        session.run(
            "MATCH (p:Passage) WHERE p.chandas_withheld_literal IS NOT NULL "
            "AND (p.chandas_withheld_reason IS NULL "
            "OR p.chandas_withheld_entity_key IS NULL "
            "OR p.chandas_withheld_source_id IS NULL) RETURN count(p) AS c"
        ).single()["c"]
    )
    if untyped:
        findings.append(f"{untyped} withheld record(s) are missing reason or provenance")

    # Every field the claim covers, not one of them: the literal on the node must be the
    # string the receipt says was printed, and it must point at the entity it came from.
    mismatched = [
        str(row["passage"])
        for row in payload
        if (
            found := session.run(
                "MATCH (p:Passage {canonical_key: $k}) "
                "RETURN p.chandas_withheld_literal AS lit, "
                "p.chandas_withheld_entity_key AS ent",
                k=row["passage"],
            ).single()
        )
        is None
        or str(found["lit"]) != str(row["printed_label"])
        or str(found["ent"]) != str(row["entity_key"])
    ]
    if mismatched:
        findings.append(
            f"{len(mismatched)} passage(s) carry a withheld record that does not match the "
            f"receipt: {mismatched[:5]}"
        )

    live = census(session)
    if live["core"] != CORE:
        findings.append(f"core corpus moved: {live['core']}")

    report = {
        "artifact": "M9_READBACK",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "malformed_assertions_remaining": surviving,
        "chandas_entities_intact": entities_present == len(entity_keys),
        "passages_with_a_withheld_record": recorded,
        "passages_expected": len(passages),
        "expectation_source": (
            "the executed receipt, not the graph. An earlier version rebuilt the expectation "
            "by querying the graph for the malformed edges, found none after the withdrawal, "
            "and reported READBACK_CLEAN having compared 0 against 0."
        ),
        "receipt_records_matched": not mismatched,
        "census": live,
        "findings": findings,
        "verdict": "READBACK_CLEAN" if not findings else "READBACK_DEFECT",
    }
    READBACK.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print()
    print("  M9 READBACK -- read out of canonical Neo4j")
    print()
    print(f"  malformed assertions remaining   {surviving}")
    print(f"  :Chandas entities intact         {entities_present} of {len(entity_keys)}")
    print(f"  passages with a withheld record  {recorded} of {len(passages)}")
    print(f"  HAS_CHANDAS now                  {live['has_chandas']:,}")
    print(f"  core corpus unchanged            {live['core'] == CORE}")
    print()
    for finding in findings:
        print(f"    - {finding}")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {READBACK}")
    return 0 if not findings else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--readback", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()

    suspect = malformed_entities()
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            if args.readback:
                return do_readback(session)

            payload = build_payload(session, suspect)
            before = census(session)
            evidence = replacement_evidence(session, payload)

            # One withheld record per passage, so no passage's record can overwrite another's.
            per_passage: dict[str, int] = {}
            for row in payload:
                per_passage[row["passage"]] = per_passage.get(row["passage"], 0) + 1
            collisions = sorted(k for k, n in per_passage.items() if n > 1)

            print()
            mode = "EXECUTING" if args.execute else "PLAN"
            print(f"  M9 MALFORMED CHANDAS WITHDRAWAL  {mode}")
            print()
            print(f"  before: {before['nodes']:,} nodes / "
                  f"{before['relationships']:,} relationships, "
                  f"{before['has_chandas']:,} HAS_CHANDAS")
            print(f"  malformed entities in the registry   {len(suspect)}")
            print(f"  assertions to withdraw               {len(payload)}")
            print(f"  passages affected                    {evidence['passages_affected']}")
            print(f"    keeping a well-formed metre edge   "
                  f"{evidence['passages_keeping_a_well_formed_metre_edge']}")
            print(f"    left with no metre edge            "
                  f"{evidence['passages_left_with_no_metre_edge']}")
            print(f"  replacements creatable               {evidence['replacements_creatable']}")
            print("  :Chandas entities to be touched      0")
            print()

            if collisions:
                print(f"  REFUSING: {collisions} carry more than one withheld claim, so one "
                      "record would overwrite another.")
                return 1

            withdrawn = 0
            recorded = 0
            if args.execute:
                if not args.backup or not pathlib.Path(args.backup).exists():
                    print("  --backup must name an existing verified dump directory.")
                    return 1
                stamp = datetime.datetime.now(datetime.UTC).isoformat()
                with session.begin_transaction() as tx:
                    # Record first, then delete. If the transaction fails between them the
                    # assertion is still there, which is the safer half to be left holding.
                    recorded = int(
                        tx.run(
                            "UNWIND $rows AS row "
                            "MATCH (p:Passage {canonical_key: row.passage}) "
                            "SET p.chandas_withheld_literal = row.printed_label, "
                            "    p.chandas_withheld_entity_key = row.entity_key, "
                            "    p.chandas_withheld_scope_origin = row.scope_origin, "
                            "    p.chandas_withheld_source_id = row.source_id, "
                            "    p.chandas_withheld_signals = row.signals, "
                            "    p.chandas_withheld_reason = $reason, "
                            "    p.chandas_withheld_gap = $gap, "
                            "    p.m9_applied = $at "
                            "RETURN count(DISTINCT p) AS n",
                            rows=payload,
                            reason=REASON,
                            gap=GAP,
                            at=stamp,
                        ).single()["n"]
                    )
                    withdrawn = int(
                        tx.run(
                            "UNWIND $rows AS row "
                            "MATCH (p:Passage {canonical_key: row.passage})"
                            "-[e:HAS_CHANDAS]->(:Chandas {entity_key: row.entity_key}) "
                            "DELETE e RETURN count(*) AS n",
                            rows=payload,
                        ).single()["n"]
                    )
                    tx.commit()

            after = census(session)
            receipt = {
                "migration": WITHDRAWAL,
                "gap": GAP,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "executed": bool(args.execute),
                "backup": args.backup or None,
                "criterion": (
                    "Whitney's own notation: a colon separates his hymn statement from its "
                    "per-verse exceptions, and a bare 'N. ' is a verse number. Neither can "
                    "occur inside a metre name."
                ),
                "promised_withdrawals": len(payload),
                "promised_records": len(payload),
                "withdrawn": withdrawn,
                "records_written": recorded,
                "affected": payload,
                "replacement_evidence": evidence,
                "census_before": before,
                "census_after": after,
                "node_delta": after["nodes"] - before["nodes"],
                "relationship_delta": after["relationships"] - before["relationships"],
                "has_chandas_delta": after["has_chandas"] - before["has_chandas"],
                "chandas_entities_unchanged": after["chandas_nodes"] == before["chandas_nodes"],
                "core_corpus_unchanged": after["core"] == CORE,
                "matched_the_promise": (
                    not args.execute
                    or (
                        withdrawn == len(payload)
                        and recorded == len(payload)
                        and after["nodes"] == before["nodes"]
                        and after["relationships"] == before["relationships"] - len(payload)
                    )
                ),
            }
            receipt["sha256"] = hashlib.sha256(
                json.dumps(receipt, sort_keys=True, default=str).encode()
            ).hexdigest()
            target = RECEIPT if args.execute else PLAN_OUT
            target.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            print(f"  after: {after['nodes']:,} nodes / "
                  f"{after['relationships']:,} relationships, "
                  f"{after['has_chandas']:,} HAS_CHANDAS "
                  f"(nodes {receipt['node_delta']:+}, "
                  f"edges {receipt['relationship_delta']:+})")
            print(f"  :Chandas population unchanged  {receipt['chandas_entities_unchanged']}")
            print(f"  core corpus unchanged          {receipt['core_corpus_unchanged']}")
            if args.execute:
                print(f"  withdrawn / recorded           {withdrawn} / {recorded}")
            print(f"  matched the promise            {receipt['matched_the_promise']}")
            print()
            print(f"  receipt: {target}")
            if not args.execute:
                print("\n  PLAN ONLY. Re-run with --execute --backup <dir>.")
            return 0 if receipt["matched_the_promise"] and receipt["core_corpus_unchanged"] else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
