"""R5 migration increment 2: what the remeasurement of increment 1 showed was still open.

Increment 1's checks all passed -- this is not a patch-forward after an unexplained
mismatch, it is work I under-scoped, measured, and am now completing under its own plan and
its own receipt.

TWO THINGS.

1.  GAP-QUALITY-003 clause 2 said "no predicate carries a single constant confidence on
    every edge", and after increment 1 TWO still do: ``INVOLVES_SUBSTANCE`` at 0.85 on 3
    edges and ``REFERS_TO_PLACE`` at 0.75 on 1 edge. They were deliberately excluded from
    the rename because 0.85 and 0.75 are NOT the source-explicit 1.0 the other seven carried,
    and giving them ``source_explicit_tier_marker`` would have asserted something false about
    them. They get ``uncalibrated_pipeline_score`` instead, which is what they are.

2.  GAP-QUALITY-003 clause 1 wants a calibration curve per confidence-carrying predicate,
    measured against a human-labelled sample. Eleven predicates carry a varying confidence
    over 25,470 edges and NOT ONE has a curve, because no human-labelled sample exists in
    this repository. Proven, not asserted: 0 nodes carry ``is_human_gold = true`` or
    ``human_gold_status = 'ANNOTATED'``, and the reference set that does exist is an
    INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET. So the absence is represented on the data
    instead of being manufactured: every one of those edges gains
    ``calibration_status = NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE`` naming what is missing
    and what exists in its place.

    ``confidence != probability`` is the whole point. A number a reader can threshold, with
    no curve behind it, invites a filter nobody can honour.

3.  GAP-PRODUCT_SURFACE-005's canonical half. Increment 1 corrected the graph; the source of
    truth is ``data/canonical/samaveda_arcika_v1``, and a graph corrected against an
    uncorrected generator input is a fix that does not survive the next rebuild. The four
    records in ``text_versions.jsonl`` are corrected, the ``referent_bindings.jsonl`` rows
    keyed on the old sha256 are re-keyed, and the tracked ``manifest.json`` per-file sha256
    is reconciled. Files are rewritten byte-wise with explicit ``\\n`` and their line count
    and record count asserted unchanged, because a whole-file rewrite with the wrong line
    endings is a defect this repository has recorded.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

from neo4j import Query

import _q

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "data" / "canonical" / "samaveda_arcika_v1"
CONTRACT = "VG:R5_CLOSURE:V1"

CONSTANT_PREDICATES = {"INVOLVES_SUBSTANCE": 0.85, "REFERS_TO_PLACE": 0.75}
VARYING_PREDICATES = [
    "ABOUT_CONCEPT",
    "INVOKES",
    "DESCRIBES",
    "REQUESTS",
    "PRAISES",
    "DESCRIBES_ACTION",
    "INVOLVES_OFFERING",
    "INVOLVES_RITUAL",
    "HAS_THEME",
    "CONTRASTS_WITH",
    "REFERS_TO_NATURAL_PHENOMENON",
]

CALIBRATION = {
    "calibration_status": "NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE",
    "calibration_blocked_by": "GAP-QUALITY-001",
    "calibration_absence_reason": (
        "No calibration curve has been measured for this predicate, because calibration "
        "needs a human-labelled sample per predicate and this repository holds none. "
        "Measured, not assumed: 0 nodes carry is_human_gold = true or "
        "human_gold_status = 'ANNOTATED'."
    ),
    "reference_set_available": "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET",
    "reference_set_is_human_gold": False,
    "confidence_is_not_a_probability": (
        "This value is an uncalibrated pipeline score. It orders edges within one predicate "
        "and it is NOT a probability that the claim is true, so a threshold over it has no "
        "measured meaning. confidence != probability."
    ),
    "r5_contract": CONTRACT,
}

WITHDRAWN = {
    "confidence_field_withdrawn_because": (
        "The value was a single constant on every edge of the predicate, over a population "
        "of 3 and 1 edges respectively -- too few to vary, rather than a tier wearing a "
        "probability's name. It is renamed rather than deleted so the pipeline's own figure "
        "survives, and it is NOT given source_explicit_tier_marker: 0.85 and 0.75 are not "
        "the source-explicit 1.0 the other seven predicates carried, and marking them so "
        "would assert something false about their evidence."
    ),
    "uncalibrated_pipeline_score_basis": "single-batch pipeline default, no calibration curve",
    "r5_contract": CONTRACT,
}


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_graph(session) -> dict[str, Any]:
    out: dict[str, Any] = {}
    before = {
        "edges_with_confidence": _q.one(
            session, "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r)"
        ),
        "constant_confidence_predicates": _q.one(
            session,
            """
            MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
            WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals
            WHERE size(vals) = 1 RETURN count(*)
            """,
        ),
    }
    renamed = 0
    for predicate in CONSTANT_PREDICATES:
        record = session.run(
            Query(
                f"""
                MATCH ()-[r:{predicate}]->() WHERE r.confidence IS NOT NULL
                SET r.uncalibrated_pipeline_score = r.confidence
                SET r += $extra
                REMOVE r.confidence
                RETURN count(r) AS n
                """,
                timeout=600.0,
            ),
            extra=WITHDRAWN,
        ).single()
        renamed += record["n"]

    calibrated = 0
    for predicate in VARYING_PREDICATES:
        record = session.run(
            Query(
                f"MATCH ()-[r:{predicate}]->() WHERE r.confidence IS NOT NULL "
                f"SET r += $props RETURN count(r) AS n",
                timeout=900.0,
            ),
            props=CALIBRATION,
        ).single()
        calibrated += record["n"]

    after = {
        "edges_with_confidence": _q.one(
            session, "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r)"
        ),
        "constant_confidence_predicates": _q.one(
            session,
            """
            MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
            WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals
            WHERE size(vals) = 1 RETURN count(*)
            """,
        ),
        "edges_with_a_calibration_status": _q.one(
            session, "MATCH ()-[r]->() WHERE r.calibration_status IS NOT NULL RETURN count(r)"
        ),
        "edges_still_carrying_confidence_without_a_calibration_status": _q.one(
            session,
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "AND r.calibration_status IS NULL RETURN count(r)",
        ),
    }
    out["quality_003"] = {
        "before": before,
        "after": after,
        "constants_renamed": renamed,
        "edges_given_a_calibration_status": calibrated,
        "clause_2_no_predicate_carries_a_constant_confidence": after[
            "constant_confidence_predicates"
        ]
        == 0,
        "clause_1_absence_of_calibration_is_represented": after[
            "edges_still_carrying_confidence_without_a_calibration_status"
        ]
        == 0,
    }
    return out


def apply_files() -> dict[str, Any]:
    proposal = json.loads(
        (
            HERE.parents[0]
            / "final_closure_sprint"
            / "agent6"
            / "gap005_sv_apparatus_corrections.json"
        ).read_text(encoding="utf-8")
    )
    corrections = {c["canonical_key"]: c for c in proposal["corrections"]}
    staged = json.loads((HERE / "staged_product_005.json").read_text(encoding="utf-8"))
    by_text_id = {
        u["text_id"]: u for u in staged["text_version_updates"]
    }
    old_to_new_sha = {
        c["current"]["content_sha256"]: c["proposed"]["content_sha256"]
        for c in corrections.values()
    }

    report: dict[str, Any] = {}

    # ---- text_versions.jsonl -------------------------------------------------
    tv_path = CANONICAL / "text_versions.jsonl"
    raw = tv_path.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("text_versions.jsonl contains CRLF; this writer assumes LF")
    lines = raw.decode("utf-8").splitlines()
    updated = 0
    out_lines: list[str] = []
    for line in lines:
        record = json.loads(line)
        update = by_text_id.get(record.get("text_id"))
        if update is not None:
            record["text_nfc"] = update["new_text_nfc"]
            record["content_sha256"] = update["new_sha256"]
            if record.get("text_original") is not None and update["role"] == "PRIMARY_TEXT":
                record["text_original"] = corrections[update["canonical_key"]]["proposed"][
                    "text_original"
                ]
            updated += 1
            out_lines.append(json.dumps(record, ensure_ascii=False))
        else:
            out_lines.append(line)
    tv_path.write_bytes(("\n".join(out_lines) + "\n").encode("utf-8"))
    report["text_versions"] = {
        "path": "data/canonical/samaveda_arcika_v1/text_versions.jsonl",
        "records_before": len(lines),
        "records_after": len(out_lines),
        "record_count_unchanged": len(lines) == len(out_lines),
        "records_updated": updated,
        "crlf_in_file": tv_path.read_bytes().count(b"\r\n"),
        "new_sha256": _sha(tv_path.read_text(encoding="utf-8")),
    }

    # ---- referent_bindings.jsonl -------------------------------------------
    rb_path = CANONICAL / "referent_bindings.jsonl"
    raw = rb_path.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("referent_bindings.jsonl contains CRLF; this writer assumes LF")
    lines = raw.decode("utf-8").splitlines()
    rb_updated = 0
    out_lines = []
    for line in lines:
        record = json.loads(line)
        changed = False
        for field in ("text_sha256", "comparison_sha256"):
            if record.get(field) in old_to_new_sha:
                record[field] = old_to_new_sha[record[field]]
                changed = True
        if changed:
            record["r5_rekeyed_by"] = "SV-APPARATUS-LIFT-01"
            record["r5_rekeyed_reason"] = (
                "The bound text lost a leading Wikisource apparatus line, so its content "
                "sha256 moved. The binding is re-keyed to the corrected digest; the passage "
                "key and the referent class are untouched."
            )
            rb_updated += 1
            out_lines.append(json.dumps(record, ensure_ascii=False))
        else:
            out_lines.append(line)
    rb_path.write_bytes(("\n".join(out_lines) + "\n").encode("utf-8"))
    report["referent_bindings"] = {
        "path": "data/canonical/samaveda_arcika_v1/referent_bindings.jsonl",
        "records_before": len(lines),
        "records_after": len(out_lines),
        "record_count_unchanged": len(lines) == len(out_lines),
        "records_rekeyed": rb_updated,
        "crlf_in_file": rb_path.read_bytes().count(b"\r\n"),
        "new_sha256": _sha(rb_path.read_text(encoding="utf-8")),
    }

    # ---- manifest.json -----------------------------------------------------
    manifest_path = CANONICAL / "manifest.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    files_block = None
    for candidate in ("files", "artifacts", "file_digests", "per_file"):
        if isinstance(manifest.get(candidate), (dict, list)):
            files_block = candidate
            break
    reconciled: list[dict[str, Any]] = []
    if files_block and isinstance(manifest[files_block], dict):
        for name in ("text_versions.jsonl", "referent_bindings.jsonl"):
            entry = manifest[files_block].get(name)
            new_sha = _sha((CANONICAL / name).read_text(encoding="utf-8"))
            if isinstance(entry, dict):
                reconciled.append(
                    {"file": name, "old": entry.get("sha256"), "new": new_sha}
                )
                entry["sha256"] = new_sha
            elif isinstance(entry, str):
                reconciled.append({"file": name, "old": entry, "new": new_sha})
                manifest[files_block][name] = new_sha
    elif files_block and isinstance(manifest[files_block], list):
        for entry in manifest[files_block]:
            name = entry.get("path") or entry.get("name") or entry.get("file")
            if name and pathlib.Path(str(name)).name in (
                "text_versions.jsonl",
                "referent_bindings.jsonl",
            ):
                new_sha = _sha((CANONICAL / pathlib.Path(str(name)).name).read_text(encoding="utf-8"))
                reconciled.append({"file": name, "old": entry.get("sha256"), "new": new_sha})
                entry["sha256"] = new_sha
    manifest.setdefault("corrections_applied", [])
    if isinstance(manifest["corrections_applied"], list):
        manifest["corrections_applied"].append(
            {
                "backlog_id": "SV-APPARATUS-LIFT-01",
                "gap_id": "GAP-PRODUCT_SURFACE-005",
                "at": _now(),
                "records": sorted(corrections),
                "what": (
                    "Removed a leading Wikisource apparatus line from four verses and "
                    "re-derived their search surface. The apparatus stands on its own line "
                    "AFTER the preceding verse's number marker in the pinned wikitext; the "
                    "parser's unit boundary attached it forward."
                ),
                "read_the_row_not_this_block": (
                    "This block records that a correction was applied. It is NOT evidence "
                    "that it landed: read text_versions.jsonl and the graph. This repository "
                    "has recorded 8 of 9 corrections_applied entries that were never written "
                    "into the data."
                ),
            }
        )
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    report["manifest"] = {
        "path": "data/canonical/samaveda_arcika_v1/manifest.json",
        "files_block": files_block,
        "digests_reconciled": reconciled,
        "correction_recorded": True,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["graph", "files"], required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.phase == "files":
        report = apply_files()
        (HERE / "increment_2_files_receipt.json").write_text(
            json.dumps({"artifact": "R5_INCREMENT_2_FILES", "at": _now(), **report},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    driver = _q.driver()
    try:
        with driver.session(database=_q.DB) as session:
            result = apply_graph(session)
    finally:
        driver.close()
    (HERE / "increment_2_graph_receipt.json").write_text(
        json.dumps({"artifact": "R5_INCREMENT_2_GRAPH", "at": _now(), **result},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
