#!/usr/bin/env python3
"""Phase J: verify the import against what was promised, not against what happened.

The distinction is the whole design. A readback that asks the graph "what translations do
you hold?" and then checks they look reasonable will confirm any import, including one that
attached 1,132 renderings to the wrong verses -- every row would resolve, every property
would be populated, and the report would be clean. This campaign has already produced that
artifact once: three Wave 3 attempts printed a clean per-group table while over-writing the
data, and only a census diff caught it.

So the expectation here comes from two files and never from a query: the immutable plan,
whose sha256 is verified before it is read, and the executor's receipt. Every check is of
the form "the plan said X; the graph says Y; X == Y". The graph is the subject, not the
source of the answer.

Run:  python scripts/translation_integration_readback.py
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import sys
from typing import Any, Final

import translation_integration_common as T

PLAN_PATH: Final = T.INTEGRATION / "translation_import_plan.json"
DIGEST_PATH: Final = T.INTEGRATION / "translation_import_plan.sha256.json"
RECEIPT_PATH: Final = T.INTEGRATION / "translation_bulk_import_receipt.json"
COMPLETION_PATH: Final = T.INTEGRATION / "translation_import_shape_completion.json"

#: Properties a reused rendering must carry. The owner policy names five things the
#: provenance must include, and this is them: source Veda, source passage, source
#: translation identity, translator/source and the reuse disclosure itself.
REQUIRED_REUSE_PROPERTIES: Final[tuple[str, ...]] = (
    "reuse_kind",
    "reused_from_veda",
    "reused_from_passage_key",
    "reused_from_citation",
    "reused_from_translation_id",
    "reuse_basis",
    "translator",
)


def main() -> int:
    import gate_bc_common as G

    declared = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))
    measured = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
    if measured != declared["sha256"]:
        raise SystemExit(f"PLAN DIGEST MISMATCH: {measured} != {declared['sha256']}")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    if receipt.get("verdict") != "EXECUTED":
        raise SystemExit(f"the receipt's verdict is {receipt.get('verdict')!r}, not EXECUTED")

    # The import ran in two passes against two plan versions, and the lineage is checked
    # rather than waved through. Plan v1 created the 1,132 nodes and edges; the quality
    # scorecard then reported 1,132 internal_leaked and 1,132 ungraded edges, because v1
    # omitted the :Internal label and the seven HAS_TRANSLATION grade properties every
    # pre-existing edge carries. Plan v2 adds both, and the shape-completion pass applied
    # them without creating anything. So the current plan must match the completion
    # receipt, and the creation receipt must name a plan that differs from it only in those
    # two respects -- which is why the node-level expectations below are read from v2 and
    # still describe exactly what v1 wrote: neither addition changes a translation_id or
    # any value in `properties`.
    lineage = {
        "current_plan_sha256": declared["sha256"],
        "creation_receipt_plan_sha256": receipt.get("plan_sha256"),
        "creation_receipt_verdict": receipt.get("verdict"),
        "plan_was_amended_after_creation": receipt.get("plan_sha256") != declared["sha256"],
    }
    if lineage["plan_was_amended_after_creation"]:
        if not COMPLETION_PATH.exists():
            raise SystemExit(
                "the plan was amended after the import and no shape-completion receipt "
                "exists, so the graph cannot hold what the current plan promises"
            )
        completion = json.loads(COMPLETION_PATH.read_text(encoding="utf-8"))
        lineage["completion_receipt_plan_sha256"] = completion.get("plan_sha256")
        lineage["completion_receipt_verdict"] = completion.get("verdict")
        if completion.get("plan_sha256") != declared["sha256"]:
            raise SystemExit(
                "the shape-completion receipt was produced against a different plan: "
                f"{completion.get('plan_sha256')} != {declared['sha256']}"
            )
        if completion.get("verdict") != "SHAPE_COMPLETED":
            raise SystemExit(
                f"the completion verdict is {completion.get('verdict')!r}, not SHAPE_COMPLETED"
            )
        if any(completion.get("measured_delta", {"x": 1}).values()):
            raise SystemExit(
                "the shape-completion pass changed the census, which it promised not to: "
                f"{completion.get('measured_delta')}"
            )

    expected = {node["translation_id"]: node for node in plan["nodes_detail"]}
    findings: list[dict[str, Any]] = []

    driver = G.driver()
    try:
        with G.session(driver) as session:
            observed = {
                record["id"]: {
                    "attached_to": record["k"],
                    "props": record["p"],
                }
                for record in session.run(
                    """
                    UNWIND $ids AS id
                    MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation {translation_id: id})
                    RETURN t.translation_id AS id, m.canonical_key AS k, properties(t) AS p
                    """,
                    ids=sorted(expected),
                )
            }

            # 1. Every promised node present, once, on the verse the plan named.
            missing = sorted(set(expected) - set(observed))
            for tid in missing:
                findings.append(
                    {
                        "check": "promised_row_missing",
                        "translation_id": tid,
                        "expected_on": expected[tid]["attach_to_canonical_key"],
                    }
                )
            for tid, seen in observed.items():
                want = expected[tid]
                if seen["attached_to"] != want["attach_to_canonical_key"]:
                    findings.append(
                        {
                            "check": "wrong_target",
                            "translation_id": tid,
                            "expected_on": want["attach_to_canonical_key"],
                            "found_on": seen["attached_to"],
                        }
                    )

            # 2. Nothing unintended. Selected by the batch stamp rather than by counting,
            #    so an extra node written by something else is visible.
            batch = [
                record["id"]
                for record in session.run(
                    "MATCH (t:Translation {import_batch: $b}) RETURN t.translation_id AS id",
                    b=plan["import_batch"],
                )
            ]
            unexpected = sorted(set(batch) - set(expected))
            for tid in unexpected:
                findings.append({"check": "unexpected_row_imported", "translation_id": tid})

            # 3. Property fidelity, field by field against the plan.
            for tid, seen in observed.items():
                want = expected[tid]["properties"]
                got = seen["props"]
                for key, value in want.items():
                    if value is None:
                        continue
                    if key not in got:
                        findings.append(
                            {"check": "property_missing", "translation_id": tid, "property": key}
                        )
                    elif _normalise(got[key]) != _normalise(value):
                        findings.append(
                            {
                                "check": "property_differs",
                                "translation_id": tid,
                                "property": key,
                                "expected": _clip(value),
                                "found": _clip(got[key]),
                            }
                        )

            # 3b. The shape the completion pass promised: the label on every node and the
            #     grade on every edge. Checked here and not only by the scorecard, because
            #     the scorecard reports a graph-wide zero and this attributes it to rows.
            shape = list(
                session.run(
                    """
                    UNWIND $ids AS id
                    MATCH (m:Mantra)-[r:HAS_TRANSLATION]->(t:Translation {translation_id: id})
                    RETURN id AS id, t:Internal AS internal, properties(r) AS rp
                    """,
                    ids=sorted(expected),
                )
            )
            for record in shape:
                want_edge = expected[record["id"]].get("edge_properties", {})
                if not record["internal"]:
                    findings.append(
                        {"check": "node_missing_internal_label", "translation_id": record["id"]}
                    )
                for key, value in want_edge.items():
                    if record["rp"].get(key) != value:
                        findings.append(
                            {
                                "check": "edge_grade_differs",
                                "translation_id": record["id"],
                                "property": key,
                                "expected": _clip(value),
                                "found": _clip(record["rp"].get(key)),
                            }
                        )

            # 4. Reuse disclosure. Every reuse node carries all five provenance fields and
            #    none of them is presented as independent.
            reuse_planned = {
                tid
                for tid, node in expected.items()
                if node["properties"].get("reuse_kind") == "REUSED_RENDERING"
            }
            for tid in sorted(reuse_planned & set(observed)):
                got = observed[tid]["props"]
                for key in REQUIRED_REUSE_PROPERTIES:
                    if not got.get(key):
                        findings.append(
                            {
                                "check": "reuse_disclosure_incomplete",
                                "translation_id": tid,
                                "missing_property": key,
                            }
                        )
            # The mirror: any node claiming reuse that was not planned to.
            claiming = {
                record["id"]
                for record in session.run(
                    "MATCH (t:Translation) WHERE t.reuse_kind IS NOT NULL "
                    "RETURN t.translation_id AS id"
                )
            }
            for tid in sorted(claiming - reuse_planned):
                findings.append({"check": "unplanned_reuse_claim", "translation_id": tid})
            for tid in sorted(reuse_planned - claiming):
                findings.append({"check": "reuse_claim_absent", "translation_id": tid})

            # 5. Language. A Latin row presented as English is the single outcome the owner
            #    decision rules out, so it is checked from both sides.
            latin_planned = {
                tid for tid, node in expected.items() if node["properties"]["language"] != "en"
            }
            live_non_english = {
                record["id"]
                for record in session.run(
                    "MATCH (t:Translation) WHERE t.language <> 'en' RETURN t.translation_id AS id"
                )
            }
            for tid in sorted(latin_planned - live_non_english):
                findings.append({"check": "latin_row_stored_as_english", "translation_id": tid})
            for tid in sorted(live_non_english - latin_planned):
                findings.append({"check": "unplanned_non_english_row", "translation_id": tid})

            # 6. Range completeness. The covered-key list must be exactly what was planned,
            #    and every key in it must resolve to a mantra of the same Veda.
            for tid, node in sorted(expected.items()):
                if node["properties"]["alignment_level"] != "MANTRA_RANGE":
                    continue
                if tid not in observed:
                    continue
                got = observed[tid]["props"].get("covers_canonical_keys") or []
                if sorted(got) != sorted(node["covers_canonical_keys"]):
                    findings.append(
                        {
                            "check": "range_covered_keys_differ",
                            "translation_id": tid,
                            "expected": node["covers_canonical_keys"],
                            "found": list(got),
                        }
                    )
                if len(got) < 2:
                    findings.append({"check": "range_covers_one_verse", "translation_id": tid})
            unresolved_span = [
                record["k"]
                for record in session.run(
                    """
                    MATCH (t:Translation) WHERE t.alignment_level = 'MANTRA_RANGE'
                    UNWIND t.covers_canonical_keys AS k
                    OPTIONAL MATCH (m:Mantra {canonical_key: k})
                    WITH k, m WHERE m IS NULL
                    RETURN k AS k
                    """
                )
            ]
            for key in unresolved_span:
                findings.append({"check": "range_names_a_key_that_is_not_a_mantra", "key": key})

            # 7. Policy leakage. The three withheld addresses, the PROBABLE population and
            #    the provenance failures must be absent -- checked by canonical key against
            #    the batch, so a row that arrived by another route is still caught.
            classified_rows = [
                json.loads(line)
                for line in (T.INTEGRATION / "gate_reconciliation_rows.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            withheld_keys = {
                row["canonical_key"] for row in classified_rows if not row["importable"]
            }
            imported_keys = {k for node in expected.values() for k in node["covers_canonical_keys"]}
            # A key can be both withheld on one row and imported on another only if two
            # rows address it; that would itself be a defect, so report the overlap.
            leaked = sorted(withheld_keys & imported_keys)
            for key in leaked:
                findings.append({"check": "withheld_key_also_imported", "key": key})

            for key in sorted(T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS):
                present = session.run(
                    """
                    MATCH (m:Mantra {canonical_key: $k})-[:HAS_TRANSLATION]->(t:Translation)
                    RETURN count(t) AS c
                    """,
                    k=key,
                ).single()["c"]
                if present:
                    findings.append(
                        {
                            "check": "owner_withheld_address_is_present",
                            "key": key,
                            "reason_withheld": T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS[key],
                            "translations_found": present,
                        }
                    )

            # 8. Existing translations unchanged. The receipt recorded a content digest of
            #    every English attachment before the write; the pre-existing subset of it
            #    must still hash the same.
            before = receipt["preflight"]["attachment_digest_before"]
            after_now = G.attachment_digest(session)
            digest_check = {
                "attachments_before": before["attachments"],
                "attachments_now": after_now["attachments"],
                "expected_growth": plan["nodes"]["independent_english"]
                + plan["nodes"]["reused_renderings"],
                "measured_growth": after_now["attachments"] - before["attachments"],
            }
            digest_check["growth_matches"] = (
                digest_check["measured_growth"] == digest_check["expected_growth"]
            )
            if not digest_check["growth_matches"]:
                findings.append({"check": "english_attachment_growth_unexpected", **digest_check})

            pre_existing = _pre_existing_digest(session, set(expected))
            digest_check["pre_existing_digest_before"] = before["digest_sha256"]
            digest_check["pre_existing_digest_now"] = pre_existing["digest_sha256"]
            digest_check["pre_existing_attachments_now"] = pre_existing["attachments"]
            digest_check["existing_attachments_unchanged"] = (
                pre_existing["digest_sha256"] == before["digest_sha256"]
            )
            if not digest_check["existing_attachments_unchanged"]:
                findings.append(
                    {
                        "check": "a_pre_existing_translation_changed",
                        "digest_before": before["digest_sha256"],
                        "digest_now": pre_existing["digest_sha256"],
                    }
                )

            census = G.graph_census(session)
            core = G.core_corpus(session)
            coverage = G.translation_coverage(session)

            report = {
                "phase": "J",
                "ran_at": dt.datetime.now(dt.UTC).isoformat(),
                "expectation_source": (
                    "translation_import_plan.json (sha256 verified) and "
                    "translation_bulk_import_receipt.json. No expectation is derived from "
                    "the graph."
                ),
                "plan_sha256": declared["sha256"],
                "receipt_lineage": lineage,
                "promised": {
                    "nodes": plan["nodes"]["total"],
                    "edges": plan["relationships"]["HAS_TRANSLATION"],
                    "verses_reached": plan["canonical_verses_reached"]["total"],
                },
                "observed": {
                    "promised_nodes_found": len(observed),
                    "batch_stamped_nodes": len(batch),
                    "verses_reached": len(imported_keys),
                },
                "checks": {
                    "missing_expected": len(missing),
                    "unexpected_imported": len(unexpected),
                    "wrong_target": len([f for f in findings if f["check"] == "wrong_target"]),
                    "property_failures": len(
                        [
                            f
                            for f in findings
                            if f["check"] in ("property_missing", "property_differs")
                        ]
                    ),
                    "reuse_disclosure_failures": len(
                        [
                            f
                            for f in findings
                            if f["check"]
                            in (
                                "reuse_disclosure_incomplete",
                                "unplanned_reuse_claim",
                                "reuse_claim_absent",
                            )
                        ]
                    ),
                    "language_failures": len(
                        [
                            f
                            for f in findings
                            if f["check"]
                            in ("latin_row_stored_as_english", "unplanned_non_english_row")
                        ]
                    ),
                    "range_failures": len([f for f in findings if f["check"].startswith("range_")]),
                    "shape_failures": len(
                        [
                            f
                            for f in findings
                            if f["check"] in ("node_missing_internal_label", "edge_grade_differs")
                        ]
                    ),
                    "policy_leakage": len(
                        [
                            f
                            for f in findings
                            if f["check"]
                            in (
                                "withheld_key_also_imported",
                                "owner_withheld_address_is_present",
                            )
                        ]
                    ),
                },
                "cross_veda_contamination": _cross_veda(expected, observed),
                "forced_addresses": {
                    "approved_planned": len(
                        [
                            n
                            for n in plan["nodes_detail"]
                            if n["final_class"] == "IMPORT_VERIFIED_FORCED_ADDRESS"
                        ]
                    ),
                    "approved_present": len(
                        [
                            tid
                            for tid, node in expected.items()
                            if node["final_class"] == "IMPORT_VERIFIED_FORCED_ADDRESS"
                            and tid in observed
                        ]
                    ),
                    "withheld_by_name": sorted(T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS),
                    "withheld_absent": len(T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS)
                    - len(
                        [f for f in findings if f["check"] == "owner_withheld_address_is_present"]
                    ),
                },
                "existing_translations": digest_check,
                "census_now": census,
                "core_corpus_now": core,
                "core_corpus_invariant_holds": core
                == plan["invariants_the_migration_must_hold"]["core_corpus_unchanged"],
                "coverage_now": coverage["per_veda"],
                "coverage_by_alignment_level": coverage["by_alignment_level"],
                "findings": findings[:200],
                "findings_total": len(findings),
                "verdict": "READBACK_CLEAN" if not findings else "READBACK_FAILED",
            }
    finally:
        driver.close()

    T.write_json(T.INTEGRATION / "translation_bulk_readback.json", report)
    print("promised :", json.dumps(report["promised"]))
    print("observed :", json.dumps(report["observed"]))
    print("checks   :", json.dumps(report["checks"], indent=1))
    print("forced   :", json.dumps(report["forced_addresses"]))
    print("existing :", json.dumps(report["existing_translations"]))
    print(
        "core     :", json.dumps(report["core_corpus_now"]), report["core_corpus_invariant_holds"]
    )
    print("coverage :", json.dumps(report["coverage_by_alignment_level"]))
    if report["findings"]:
        print()
        for finding in report["findings"][:20]:
            print("FINDING:", json.dumps(finding, ensure_ascii=False)[:220])
    print("VERDICT  :", report["verdict"])
    return 0 if report["verdict"] == "READBACK_CLEAN" else 1


def _pre_existing_digest(session: Any, imported_ids: set[str]) -> dict[str, Any]:
    """The attachment digest over everything this import did *not* create.

    Same tuple and same ordering as ``gate_bc_common.attachment_digest``, minus the new
    rows, so the value is directly comparable to the one the receipt recorded before the
    write. Comparing totals could not detect a rewritten literal; this can.
    """
    digest = hashlib.sha256()
    lines = []
    for record in session.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE t.language = 'en'
        RETURN m.canonical_key AS k,
               coalesce(t.source_id,'') AS src,
               coalesce(t.alignment_level,'') AS lvl,
               coalesce(t.translation_id,'') AS tid,
               coalesce(t.text,'') AS text
        """
    ):
        if record["tid"] in imported_ids:
            continue
        lines.append(
            f"{record['k']}|{record['src']}|{record['lvl']}|{record['tid']}|"
            f"{hashlib.sha256(record['text'].encode('utf-8')).hexdigest()}"
        )
    for line in sorted(lines):
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return {"attachments": len(lines), "digest_sha256": digest.hexdigest()}


def _cross_veda(
    expected: dict[str, dict[str, Any]], observed: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Whether any node landed on a verse of a different Veda than its row claimed.

    The reuse population makes this worth checking explicitly rather than trusting: those
    rows legitimately carry Rigvedic text and a Samavedic or Atharvavedic target, so "the
    text is Rigvedic" is not evidence of a mistake, and the target's Veda is the only thing
    that would be.
    """
    mismatches = []
    for tid, seen in observed.items():
        claimed = expected[tid]["veda"]
        landed = seen["attached_to"].split(":")[1]
        if claimed != landed:
            mismatches.append({"translation_id": tid, "claimed": claimed, "landed_on": landed})
    return {
        "mismatches": mismatches,
        "count": len(mismatches),
        "by_veda_landed": dict(
            sorted(
                collections.Counter(
                    seen["attached_to"].split(":")[1] for seen in observed.values()
                ).items()
            )
        ),
    }


def _normalise(value: Any) -> Any:
    if isinstance(value, list):
        return [str(v) for v in value]
    return value


def _clip(value: Any) -> Any:
    text = str(value)
    return text if len(text) <= 120 else text[:120] + "..."


if __name__ == "__main__":
    sys.exit(main())
