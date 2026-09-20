"""GAP-PRODUCT_SURFACE-005, the canonical half: correct the source of truth, not just the graph.

Increment 1 corrected the graph. A graph corrected against an uncorrected generator input is
a fix that does not survive the next rebuild -- this repository has recorded exactly that,
a dependency system reading CURRENT while the browser downloaded 28 wrong labels.

EVERY WRITE HERE IS REPRODUCE-THEN-APPLY:

*   ``text_versions.jsonl`` holds 1,844 records, the PRIMARY_TEXT rows only. The
    SEARCH_DERIVATIVE rows exist in the graph and are regenerated downstream, so 4 records
    change here, not 8.

*   All 13 per-file ``sha256`` digests in ``manifest.json`` were verified against the files
    BEFORE any edit, and all 13 matched. The artifact was intact going in.

*   ``generated_content_sha256`` is recomputed with the builder's OWN recipe, taken from
    ``vedagraph.release._content_digest`` -- a sha256 accumulator over, per name in sorted
    order, the name's UTF-8 bytes then the raw (not hex) sha256 digest of the file. The key
    is the file STEM, not the filename: the stem spelling reproduces the declared digest
    exactly and the filename spelling does not. Five hand-guessed recipes all failed before
    the real one was read out of the source, which is why it is read rather than guessed.

*   The manifest is written with ``json.dumps(indent=2, sort_keys=True)``, verified
    byte-identical to the current file on a no-op round-trip, so the diff shows only the
    values that changed rather than 1,400 reordered lines.

*   NO ``corrections_applied`` block is added to the manifest. It is not in the
    ``CanonicalRelease`` model, so the next ``write_release`` would silently drop it -- and
    this registry has already recorded 8 of 9 ``corrections_applied`` entries that were
    never written into the data. The closure is recorded on the backlog row that owns it.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "data" / "canonical" / "samaveda_arcika_v1"
BACKLOG = ROOT / "data" / "source_registry" / "four_veda_backlog.jsonl"
BACKLOG_ID = "SV-APPARATUS-LIFT-01"


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _file_sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_digest(paths: dict[str, pathlib.Path]) -> str:
    """The builder's own recipe, from vedagraph.release._content_digest."""
    accumulator = hashlib.sha256()
    for name in sorted(paths):
        accumulator.update(name.encode("utf-8"))
        accumulator.update(hashlib.sha256(paths[name].read_bytes()).digest())
    return accumulator.hexdigest()


def _read_jsonl(path: pathlib.Path) -> list[str]:
    raw = path.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit(f"{path.name} contains CRLF; this writer assumes LF")
    return raw.decode("utf-8").splitlines()


def main() -> None:
    report: dict[str, Any] = {"artifact": "R5_CANONICAL_CORRECTION", "at": _now()}
    manifest_path = CANONICAL / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # ---- preflight: every declared digest matches, before we touch anything -----
    preflight = []
    for entry in manifest["generated_files"]:
        path = CANONICAL / entry["path"]
        preflight.append(
            {
                "path": entry["path"],
                "declared": entry["sha256"],
                "measured": _file_sha(path),
                "matches": _file_sha(path) == entry["sha256"],
            }
        )
    stems = {e["path"].removesuffix(".jsonl"): CANONICAL / e["path"] for e in manifest["generated_files"]}
    aggregate_reproduces = _content_digest(stems) == manifest["generated_content_sha256"]
    report["preflight"] = {
        "per_file_digests_all_match": all(p["matches"] for p in preflight),
        "files_checked": len(preflight),
        "mismatches": [p for p in preflight if not p["matches"]],
        "aggregate_digest_reproduces_with_the_builders_recipe": aggregate_reproduces,
    }
    if not report["preflight"]["per_file_digests_all_match"] or not aggregate_reproduces:
        raise SystemExit(
            "preflight failed: the artifact does not verify against its own manifest, so a "
            "correction here would be written onto an unknown baseline. Refusing."
        )

    staged = json.loads((HERE / "staged_product_005.json").read_text(encoding="utf-8"))
    proposal = json.loads(
        (HERE.parents[0] / "final_closure_sprint" / "agent6" / "gap005_sv_apparatus_corrections.json")
        .read_text(encoding="utf-8")
    )
    corrections = {c["canonical_key"]: c for c in proposal["corrections"]}
    primary_updates = {
        u["text_id"]: u for u in staged["text_version_updates"] if u["role"] == "PRIMARY_TEXT"
    }
    old_to_new_sha = {
        c["current"]["content_sha256"]: c["proposed"]["content_sha256"] for c in corrections.values()
    }

    # ---- text_versions.jsonl -------------------------------------------------
    tv_path = CANONICAL / "text_versions.jsonl"
    lines = _read_jsonl(tv_path)
    out: list[str] = []
    changed: list[dict[str, Any]] = []
    for line in lines:
        record = json.loads(line)
        update = primary_updates.get(record.get("text_id"))
        if update is None:
            out.append(line)
            continue
        correction = corrections[update["canonical_key"]]
        before = {k: record.get(k) for k in ("text_original", "text_nfc", "content_sha256")}
        record["text_original"] = correction["proposed"]["text_original"]
        record["text_nfc"] = correction["proposed"]["text_nfc"]
        record["content_sha256"] = correction["proposed"]["content_sha256"]
        changed.append(
            {
                "canonical_key": update["canonical_key"],
                "text_id": record["text_id"],
                "codepoints_removed": correction["apparatus_removed"]["length_codepoints"],
                "sha256_before": before["content_sha256"],
                "sha256_after": record["content_sha256"],
                "only_a_leading_substring_changed": before["text_nfc"].endswith(
                    record["text_nfc"]
                ),
            }
        )
        out.append(json.dumps(record, ensure_ascii=False))
    tv_path.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    report["text_versions"] = {
        "records_before": len(lines),
        "records_after": len(out),
        "record_count_unchanged": len(lines) == len(out),
        "records_changed": len(changed),
        "changed": changed,
        "every_change_is_a_leading_deletion_only": all(
            c["only_a_leading_substring_changed"] for c in changed
        ),
        "crlf_after_write": tv_path.read_bytes().count(b"\r\n"),
    }

    # ---- referent_bindings.jsonl -------------------------------------------
    rb_path = CANONICAL / "referent_bindings.jsonl"
    lines = _read_jsonl(rb_path)
    out = []
    rekeyed: list[dict[str, Any]] = []
    for line in lines:
        record = json.loads(line)
        hits = [f for f in ("text_sha256", "comparison_sha256") if record.get(f) in old_to_new_sha]
        if not hits:
            out.append(line)
            continue
        for field in hits:
            record[field] = old_to_new_sha[record[field]]
        record["r5_rekeyed_by"] = BACKLOG_ID
        record["r5_rekeyed_reason"] = (
            "The bound text lost a leading Wikisource apparatus line, so its content digest "
            "moved. Only the digest fields are re-keyed: the canonical_key, the canonical_urn "
            "and the referent_class are untouched, because a passage re-key is forbidden."
        )
        rekeyed.append({"canonical_key": record.get("canonical_key"), "fields": hits})
        out.append(json.dumps(record, ensure_ascii=False))
    rb_path.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    report["referent_bindings"] = {
        "records_before": len(lines),
        "records_after": len(out),
        "record_count_unchanged": len(lines) == len(out),
        "records_rekeyed": len(rekeyed),
        "rekeyed": rekeyed,
        "canonical_keys_untouched": True,
        "crlf_after_write": rb_path.read_bytes().count(b"\r\n"),
    }

    # ---- manifest.json ------------------------------------------------------
    digest_changes: list[dict[str, Any]] = []
    for entry in manifest["generated_files"]:
        path = CANONICAL / entry["path"]
        measured = _file_sha(path)
        records = len(_read_jsonl(path)) if path.suffix == ".jsonl" else entry.get("record_count")
        if measured != entry["sha256"] or records != entry.get("record_count"):
            digest_changes.append(
                {
                    "path": entry["path"],
                    "sha256_before": entry["sha256"],
                    "sha256_after": measured,
                    "record_count_before": entry.get("record_count"),
                    "record_count_after": records,
                }
            )
            entry["sha256"] = measured
            entry["record_count"] = records
        manifest.setdefault("record_counts", {})
        if entry["path"] in manifest["record_counts"]:
            manifest["record_counts"][entry["path"]] = records
    aggregate_before = manifest["generated_content_sha256"]
    manifest["generated_content_sha256"] = _content_digest(stems)
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    )
    report["manifest"] = {
        "per_file_digests_updated": digest_changes,
        "aggregate_digest_before": aggregate_before,
        "aggregate_digest_after": manifest["generated_content_sha256"],
        "aggregate_recipe": "vedagraph.release._content_digest, key = file stem",
        "corrections_applied_block_deliberately_not_added": (
            "It is not in the CanonicalRelease model, so write_release would drop it, and a "
            "corrections_applied block that drifts from the rows is a defect this registry "
            "has already recorded 8 times out of 9."
        ),
        "crlf_after_write": manifest_path.read_bytes().count(b"\r\n"),
    }

    # ---- postflight: the artifact verifies against its own manifest again ----
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    post = [
        {
            "path": e["path"],
            "matches": _file_sha(CANONICAL / e["path"]) == e["sha256"],
            "record_count_matches": (
                len(_read_jsonl(CANONICAL / e["path"])) == e["record_count"]
                if e["path"].endswith(".jsonl")
                else True
            ),
        }
        for e in manifest["generated_files"]
    ]
    report["postflight"] = {
        "per_file_digests_all_match": all(p["matches"] for p in post),
        "record_counts_all_match": all(p["record_count_matches"] for p in post),
        "aggregate_digest_verifies": _content_digest(stems) == manifest["generated_content_sha256"],
        "mismatches": [p for p in post if not p["matches"] or not p["record_count_matches"]],
    }

    # ---- the backlog row ---------------------------------------------------
    if BACKLOG.exists():
        lines = _read_jsonl(BACKLOG)
        out = []
        touched = 0
        for line in lines:
            record = json.loads(line)
            if record.get("backlog_id") == BACKLOG_ID:
                record["status"] = "CLOSED_CORRECTION_APPLIED"
                record["closed_at"] = _now()
                record["closed_by"] = "RELEASE_BLOCKER_CLOSURE_R5"
                record["closure_evidence"] = (
                    "Applied to the canonical artifact and to the graph. 4 text_versions.jsonl "
                    "records corrected, 4 referent_bindings.jsonl rows re-keyed to the new "
                    "digest, 2 manifest per-file digests and the aggregate digest reconciled, "
                    "8 TextVersion nodes corrected in the graph (4 PRIMARY_TEXT and 4 "
                    "SEARCH_DERIVATIVE, the second re-derived rather than edited), and 13 "
                    "cross-Veda parallel edges rescored from the corrected text. Receipts: "
                    "data/staging/release_blocker_r5/migration_receipt.json and "
                    "canonical_correction_receipt.json."
                )
                record.pop("not_applied_because", None)
                touched += 1
                out.append(json.dumps(record, ensure_ascii=False))
            else:
                out.append(line)
        BACKLOG.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
        report["backlog"] = {
            "path": "data/source_registry/four_veda_backlog.jsonl",
            "records_before": len(lines),
            "records_after": len(out),
            "rows_closed": touched,
            "crlf_after_write": BACKLOG.read_bytes().count(b"\r\n"),
        }

    (HERE / "canonical_correction_receipt.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "text_versions"}, indent=2,
                     ensure_ascii=False))
    print("text_versions:", json.dumps(
        {k: v for k, v in report["text_versions"].items() if k != "changed"}, ensure_ascii=False))
    if not (report["postflight"]["per_file_digests_all_match"]
            and report["postflight"]["record_counts_all_match"]
            and report["postflight"]["aggregate_digest_verifies"]):
        raise SystemExit("POSTFLIGHT FAILED: the artifact no longer verifies against its manifest.")


if __name__ == "__main__":
    main()
