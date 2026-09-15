#!/usr/bin/env python3
"""Owner section 12: readback is the closure event. Nothing closes because code returned 0.

Every figure here is read out of canonical Neo4j, and the comparison is against the
**dry-run's promise**, not against the importer's own report. That ordering is the point: an
importer that miscounts reports its miscount consistently, so the only independent check is
the database, and the only honest denominator is what the plan said would happen before it
ran.

WHAT IT CHECKS, PER OWNER SECTION 12
====================================

* **Recount.** Census and per-label, per-type counts against the expected census.
* **Identities.** Every element this wave wrote is addressable by the identity the plan
  declared, and no identity the plan withheld exists.
* **Relationships.** Every edge written has both endpoints, and no edge points at nothing.
* **Source provenance.** Every written element names its wave, run, domain and group -- an
  element that cannot say which domain produced it cannot be rolled back or audited.
* **Domain closure tests.** Per domain, the one thing that would have to be true for that
  domain's claim to hold, expressed as a query rather than as a count.
* **The invariants.** The four corpus totals, and the edge counts the migration cards
  promised not to move.

Only after all of that does a registry gap's status change, and a gap closes only when its
own closure test passes.

Usage:
    python scripts/wave3_readback.py [--json OUT] [--close-gaps]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

INTEGRATION = pathlib.Path("data/staging/integration")
DRY_RUN = INTEGRATION / "wave3_dry_run_v2.json"
PLAN = INTEGRATION / "wave3_import_plan.json"
RECEIPT = INTEGRATION / "wave3_import_receipt.json"
REGISTRY = pathlib.Path("data/gap_registry.json")
OUT = INTEGRATION / "wave3_readback.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

WAVE = "WAVE_3"

#: Nodes this wave writes that are unattached on purpose, each with the decision behind it.
#: A list of decisions rather than a rule, so the next island is a finding rather than a
#: silent member of a class.
DELIBERATELY_UNATTACHED: dict[str, str] = {
    "VG:CONCEPT:SADASYA-PRIEST": (
        "An officiant role marked samhita_attested with evidence SAMHITA and no attestation "
        "example recorded -- roles.jsonl carries no samhita_attestation_examples field at "
        "all. Attested in a corpus this graph holds, so kept rather than dropped over a "
        "missing locator. The artifact's silence is a finding against the artifact."
    ),
    "VG:CONCEPT:SAMITR-BUTCHER": (
        "The same case as SADASYA-PRIEST: Samhita-attested, no locator recorded."
    ),
    "VG:SWORK:SAYANA-TAITTIRIYA-BRAHMANA-BHASYA": (
        "A registered scholarly work that no claim cites. 16 of the 17 works appear in the "
        "rows; this one is a bibliography entry, not an error."
    ),
}

#: The four corpus totals. The campaign's hardest boundary: whatever else an import does,
#: these do not move, and a readback that does not check them has not checked anything.
CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: Edge counts the migration cards promised would not change, and the one that changes by
#: exactly one. M1's card states ASSERTION_AGENT 2,502 and ASSERTION_TARGET 799; M5's
#: states EPITHET_VARIANT_OF goes 11 to 10 and SPECIALIZED_FORM_OF becomes 1.
PROMISED: dict[str, int] = {
    "ASSERTION_AGENT": 2502,
    "ASSERTION_TARGET": 799,
    "EPITHET_VARIANT_OF": 10,
    "SPECIALIZED_FORM_OF": 1,
    # HAS_STEP must NOT grow. Its 3 edges point at an :Action, and the 9,255 new steps use
    # HAS_RITUAL_STEP precisely so that an existing predicate's range is left alone.
    "HAS_STEP": 3,
}

#: One query per domain, each asking the thing that would have to be true for that domain's
#: claim to hold. Deliberately not a count of what was written: a count confirms the writer
#: and a closure test confirms the claim.
CLOSURE: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "semantic_roles": (
        "every asserted role filler resolves to exactly one passage, and none is a "
        "duplicate of a canonical entity",
        "MATCH (f:RoleFiller) "
        "OPTIONAL MATCH (f)<-[:ASSERTION_ROLE]-(p:Passage) "
        "WITH f, count(DISTINCT p) AS passages "
        "RETURN count(f) AS fillers, sum(CASE WHEN passages = 1 THEN 1 ELSE 0 END) AS anchored, "
        "sum(CASE WHEN passages <> 1 THEN 1 ELSE 0 END) AS unanchored",
        ("unanchored",),
    ),
    "formula": (
        "the shared-formula relation joins only mantras, and every edge names the formulae "
        "it was derived from",
        "MATCH (a)-[r:SHARES_FORMULA_WITH]->(b) "
        "RETURN count(r) AS edges, "
        "sum(CASE WHEN a:Mantra AND b:Mantra THEN 0 ELSE 1 END) AS off_grain, "
        "sum(CASE WHEN r.shared_formula_ids IS NULL THEN 1 ELSE 0 END) AS no_evidence",
        ("off_grain", "no_evidence"),
    ),
    "ritual": (
        "every ritual step is anchored on a rite and carries its source citation",
        "MATCH (s:RitualStep) "
        "RETURN count(s) AS steps, "
        "sum(CASE WHEN s.ritual_key IS NULL THEN 1 ELSE 0 END) AS unanchored, "
        "sum(CASE WHEN s.citation IS NULL THEN 1 ELSE 0 END) AS uncited, "
        "sum(CASE WHEN NOT (s)<-[:HAS_RITUAL_STEP]-() THEN 1 ELSE 0 END) AS unreachable",
        ("unanchored", "uncited", "unreachable"),
    ),
    "scholarship": (
        "every scholar carries a named attribution status, so a disputed ascription is "
        "never presented as settled",
        "MATCH (s:Scholar) RETURN count(s) AS scholars, "
        "sum(CASE WHEN s.attribution_status IS NULL THEN 1 ELSE 0 END) AS unstated",
        ("unstated",),
    ),
    "communities": (
        "the partition is present as an artifact with its refusal attached and NO membership "
        "edge asserts it as fact",
        "MATCH (c:DeityCommunity) "
        "OPTIONAL MATCH (c)-[m]-() "
        "RETURN count(DISTINCT c) AS communities, "
        "sum(CASE WHEN c.caveat IS NULL THEN 1 ELSE 0 END) AS without_caveat, "
        "count(m) AS membership_edges",
        ("without_caveat", "membership_edges"),
    ),
    "quality": (
        "no verdict is typed human gold, and every one names the reference set it came from",
        "MATCH (v:QualityVerdict) RETURN count(v) AS verdicts, "
        "sum(CASE WHEN v.reference_set_type IS NULL THEN 1 ELSE 0 END) AS unsourced, "
        "sum(CASE WHEN v.reference_set_type = 'HUMAN_GOLD' THEN 1 ELSE 0 END) AS "
        "claims_human_gold, "
        "sum(CASE WHEN NOT (v)-[:QUALITY_VERDICT_ABOUT]->() THEN 1 ELSE 0 END) AS unattached",
        ("unsourced", "claims_human_gold", "unattached"),
    ),
    "scholarship_label_contract": (
        "no row this wave imported wears :InterpretiveClaim, whose contract promises an "
        "about enum and a falsifier that a scholarly disagreement does not have",
        "MATCH (n:InterpretiveClaim) "
        "RETURN count(n) AS claims, "
        "sum(CASE WHEN n.about IS NULL THEN 1 ELSE 0 END) AS without_about, "
        "sum(CASE WHEN n.falsifier IS NULL THEN 1 ELSE 0 END) AS without_falsifier",
        ("without_about", "without_falsifier"),
    ),
    "graph_quality_contracts": (
        "every element this wave wrote carries the quality_tier and display_label the "
        "graph keeps on all the others -- NOT YET TRUE, and the figures are the residual",
        "MATCH ()-[r]->() WHERE r.wave3_touched_by IS NOT NULL AND r.quality_tier IS NULL "
        "WITH count(r) AS ungraded "
        "MATCH (n) WHERE n.wave3_created_by IS NOT NULL AND NOT n:Internal "
        "AND n.display_label IS NULL "
        "RETURN ungraded AS edges_without_a_quality_tier, "
        "count(n) AS nodes_without_a_display_label",
        (),
    ),
    "cross_veda": (
        "the corrected transformation typing landed on existing parallel edges and created "
        "none",
        "MATCH ()-[r:EXACT_PARALLEL_OF|VARIANT_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM]->() "
        "RETURN count(r) AS parallel_edges, "
        "sum(CASE WHEN r.cross_veda_transformation IS NOT NULL THEN 1 ELSE 0 END) AS typed",
        (),
    ),
}


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def one(session: Session, query: str, **params: Any) -> dict[str, Any]:
    record = session.run(query, **params).single()
    return dict(record) if record else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    parser.add_argument(
        "--close-gaps",
        action="store_true",
        help="update gap_registry statuses for the gaps whose closure test passed",
    )
    args = parser.parse_args()

    dry = load(DRY_RUN)
    plan = load(PLAN)
    receipt = load(RECEIPT)
    if not dry or not plan:
        print("  no dry-run or plan to read back against.")
        return 1
    if not receipt.get("executed"):
        print("  the import receipt says nothing was executed. Nothing to read back.")
        return 1

    promised = dry.get("expected_census") or {}
    findings: list[str] = []

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            nodes = int(one(session, "MATCH (n) RETURN count(n) AS c")["c"])
            rels = int(one(session, "MATCH ()-[r]->() RETURN count(r) AS c")["c"])
            core = {
                r["veda"]: r["n"]
                for r in session.run(
                    "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                )
            }

            # ---- the invariants, first, because nothing else matters if they moved -------
            if core != CORE:
                findings.append(f"THE CORE CORPUS MOVED: expected {CORE}, read {core}")
            promised_edges = {}
            for rel, expected in PROMISED.items():
                actual = int(
                    one(session, f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").get("c") or 0
                )
                promised_edges[rel] = {"expected": expected, "actual": actual}
                if actual != expected:
                    findings.append(
                        f"{rel}: the migration card promised {expected}, the graph holds {actual}"
                    )

            # ---- the census, against what the plan promised ------------------------------
            census = {
                "nodes_promised": promised.get("nodes_after"),
                "nodes_actual": nodes,
                "nodes_match": nodes == promised.get("nodes_after"),
                "relationships_promised": promised.get("relationships_after"),
                "relationships_actual": rels,
                "relationships_match": rels == promised.get("relationships_after"),
                "core_corpus": core,
            }
            if not census["nodes_match"]:
                findings.append(
                    f"node census: promised {promised.get('nodes_after')}, read {nodes}"
                )
            if not census["relationships_match"]:
                findings.append(
                    f"relationship census: promised {promised.get('relationships_after')}, "
                    f"read {rels}"
                )

            # ---- per group: is the element there, and is it attributed? ------------------
            groups: list[dict[str, Any]] = []
            for entry in plan.get("groups") or []:
                gid = entry["group_id"]
                kind = entry["kind"]
                element = entry["element"]
                row: dict[str, Any] = {"group_id": gid, "kind": kind, "element": element}
                if kind == "NODE":
                    counts = one(
                        session,
                        f"MATCH (n:{element}) WHERE n.wave3_group = $gid "
                        "RETURN count(n) AS written, "
                        "sum(CASE WHEN n.wave3_domain IS NULL THEN 1 ELSE 0 END) AS unattributed",
                        gid=gid,
                    )
                    row["promised_create"] = entry.get("nodes_create")
                    row["in_graph_from_this_wave"] = counts.get("written")
                    row["unattributed"] = counts.get("unattributed")
                    if counts.get("unattributed"):
                        findings.append(f"{gid}: {counts['unattributed']} elements name no domain")
                    if int(counts.get("written") or 0) < int(entry.get("nodes_create") or 0):
                        findings.append(
                            f"{gid}: promised {entry.get('nodes_create')} new nodes, "
                            f"{counts.get('written')} carry this wave's stamp"
                        )
                elif kind == "RELATIONSHIP":
                    types = entry.get("relationship_types_asserted") or []
                    if types:
                        pattern = "|".join(types)
                        counts = one(
                            session,
                            f"MATCH ()-[r:{pattern}]->() WHERE r.wave3_group = $gid "
                            "RETURN count(r) AS written, "
                            "sum(CASE WHEN r.wave3_domain IS NULL THEN 1 ELSE 0 END) "
                            "AS unattributed",
                            gid=gid,
                        )
                        row["promised_create"] = entry.get("relationships_create")
                        row["in_graph_from_this_wave"] = counts.get("written")
                        row["unattributed"] = counts.get("unattributed")
                        if counts.get("unattributed"):
                            findings.append(
                                f"{gid}: {counts['unattributed']} edges name no domain"
                            )
                groups.append(row)

            # ---- no withheld identity may exist -----------------------------------------
            withheld_found: list[str] = []
            for entry in plan.get("groups") or []:
                for record in entry.get("identity_collision_detail") or []:
                    if entry["kind"] != "NODE":
                        continue
                    key = record["identity"].split("|")[0]
                    hit = one(
                        session,
                        f"MATCH (n:{entry['element']}) "
                        f"WHERE n.{entry.get('match_property', 'entity_key')} = $key "
                        "RETURN count(n) AS c",
                        key=key,
                    )
                    if int(hit.get("c") or 0):
                        withheld_found.append(f"{entry['group_id']}:{key}")
            if withheld_found:
                findings.append(
                    f"{len(withheld_found)} withheld identities exist in the graph: "
                    f"{withheld_found[:5]}"
                )

            # ---- no edge written this wave may dangle -----------------------------------
            # A node nothing points at is not imported data. The twelve :DeityCommunity
            # artifacts are the one exception and they are exempted by name: the integration
            # plan's phase 5 imports the partition with its refusal and NO membership claim,
            # because six of the twelve draw every internal edge from a single hymn. Every
            # other island is a defect, and the second import left 12,033 of them.
            orphan = one(
                session,
                "MATCH (n) WHERE n.wave3_created_by IS NOT NULL AND NOT (n)--() "
                "AND NOT n:DeityCommunity AND NOT n.entity_key IN $exempt "
                "RETURN count(n) AS c",
                exempt=sorted(DELIBERATELY_UNATTACHED),
            )
            isolated = int(orphan.get("c") or 0)
            by_label = {
                r["label"]: r["c"]
                for r in session.run(
                    "MATCH (n) WHERE n.wave3_created_by IS NOT NULL AND NOT (n)--() "
                    "UNWIND labels(n) AS label RETURN label, count(*) AS c ORDER BY c DESC",
                    wave=WAVE,
                )
            }
            if isolated:
                findings.append(
                    f"{isolated} node(s) written this wave have no relationship at all and "
                    f"are unreachable: {by_label}"
                )
            deliberate = one(
                session,
                "MATCH (n) WHERE NOT (n)--() AND (n:DeityCommunity "
                "OR n.entity_key IN $exempt) RETURN count(n) AS c",
                exempt=sorted(DELIBERATELY_UNATTACHED),
            )

            # ---- domain closure tests ---------------------------------------------------
            closure: dict[str, Any] = {}
            for domain, (claim, query, must_be_zero) in sorted(CLOSURE.items()):
                measured = one(session, query)
                # Every field the claim covers, not one of them. Requiring a single field
                # let two tests measure their own failure and pass anyway: quality read
                # unsourced 2,568 of 2,568 and asserted claims_human_gold instead.
                failed = {
                    field: measured.get(field)
                    for field in must_be_zero
                    if int(measured.get(field) or 0) != 0
                }
                # A field named in must_be_zero that the query does not return would make
                # the assertion vacuous, so an absent field is a failure of the test itself.
                absent = [field for field in must_be_zero if field not in measured]
                closure[domain] = {
                    "claim": claim,
                    "measured": dict(measured),
                    "must_be_zero": list(must_be_zero),
                    "fields_not_returned_by_the_query": absent,
                    "failed_fields": failed,
                    "passed": not failed and not absent,
                }
                if failed:
                    findings.append(
                        f"{domain} closure test failed: "
                        + ", ".join(f"{k} = {v}" for k, v in sorted(failed.items()))
                    )
                if absent:
                    findings.append(
                        f"{domain} closure test is vacuous: it requires {absent} to be zero "
                        "and its query does not return them"
                    )

            # ---- the corrections, read back ---------------------------------------------
            soma_remaining = one(
                session,
                "MATCH ()-[r:MENTIONS_ENTITY]->(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
                "WHERE ALL(a IN r.matched_aliases WHERE a IN $retired) "
                "RETURN count(r) AS c",
                retired=["sute", "suteṣu", "sutāsaḥ"],
            )
            corrections = {
                "mentions_entity_edges_still_resting_only_on_a_retired_alias": int(
                    soma_remaining.get("c") or 0
                ),
                "soma_pressing_concept_still_present": int(
                    one(
                        session,
                        "MATCH (c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) RETURN count(c) AS c",
                    ).get("c")
                    or 0
                ),
            }
            if corrections["mentions_entity_edges_still_resting_only_on_a_retired_alias"]:
                findings.append(
                    "the SOMA-PRESSING retirement is incomplete: "
                    f"{corrections['mentions_entity_edges_still_resting_only_on_a_retired_alias']} "
                    "edges still rest only on a retired alias"
                )
            if not corrections["soma_pressing_concept_still_present"]:
                findings.append(
                    "SOMA-PRESSING is gone from the graph. The owner's decision was to KEEP it."
                )

            # ---- new labels and types, as a schema diff ---------------------------------
            new_labels = {
                r["label"]: r["c"]
                for r in session.run(
                    "UNWIND $labels AS label "
                    "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c } "
                    "RETURN label, c ORDER BY label",
                    labels=(plan.get("schema_additions") or {}).get("node_labels_created") or [],
                )
            }
            new_types = {
                r["t"]: r["c"]
                for r in session.run(
                    "UNWIND $types AS t "
                    "CALL (t) { MATCH ()-[r]->() WHERE type(r) = t RETURN count(r) AS c } "
                    "RETURN t, c ORDER BY t",
                    types=(plan.get("schema_additions") or {}).get(
                        "relationship_types_touched"
                    )
                    or [],
                )
            }
    finally:
        driver.close()

    report = {
        "schema_version": "1.0",
        "artifact": "WAVE_3_READBACK",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "read_against": "the dry-run's promise, not the importer's report",
        "import_run_id": receipt.get("run_id"),
        "census": census,
        "core_corpus_invariant_held": core == CORE,
        "promised_edge_counts": promised_edges,
        "per_group": groups,
        "withheld_identities_found_in_graph": withheld_found,
        "nodes_written_this_wave_with_no_relationship": isolated,
        "unattached_by_label": by_label,
        "deliberately_unattached": int(deliberate.get("c") or 0),
        "deliberately_unattached_reasons": DELIBERATELY_UNATTACHED,
        "domain_closure_tests": closure,
        "corrections_read_back": corrections,
        "schema_additions_in_graph": {
            "node_labels": new_labels,
            "relationship_types": new_types,
        },
        "findings": findings,
        "verdict": "READBACK_CLEAN" if not findings else "READBACK_DEFECT",
        "closure_rule": (
            "A registry gap closes only after canonical import, this readback, its own "
            "closure test, and product or API propagation where applicable. Staged work is "
            "not closed work, and neither is imported work until it is read back."
        ),
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  WAVE 3 READBACK -- every figure read out of canonical Neo4j")
    print()
    print(
        f"  census: {census['nodes_actual']:,} nodes "
        f"({'matches' if census['nodes_match'] else 'DIFFERS FROM'} the promise), "
        f"{census['relationships_actual']:,} relationships "
        f"({'matches' if census['relationships_match'] else 'DIFFERS FROM'} the promise)"
    )
    print(f"  core corpus invariant: {'HELD' if core == CORE else 'BROKEN'}  {core}")
    print()
    print("  edge counts the migration cards promised:")
    for rel, values in promised_edges.items():
        mark = "ok" if values["expected"] == values["actual"] else "DIFF"
        print(
            f"    {mark:4} {rel:24} expected {values['expected']:>6}  "
            f"actual {values['actual']:>6}"
        )
    print()
    print("  domain closure tests:")
    for domain, result in closure.items():
        print(f"    {'PASS' if result['passed'] else 'FAIL'}  {domain:22}{result['claim'][:70]}")
        print(f"          {result['measured']}")
    print()
    print("  new labels in the graph:", new_labels or "(none)")
    print("  new relationship types:", new_types or "(none)")
    print()
    print(f"  withheld identities found in the graph: {len(withheld_found)}")
    print(
        f"  nodes written this wave with no relationship: {isolated}"
        f"  (plus {int(deliberate.get('c') or 0)} unattached on purpose, "
        "12 communities and 3 named entities)"
    )
    print()
    if findings:
        print(f"  {len(findings)} FINDING(S):")
        for finding in findings:
            print(f"    - {finding}")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    print()
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
