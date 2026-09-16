#!/usr/bin/env python3
"""Phase 0: baseline, input manifest and an independently measured population census.

The census does not read the staging manifest's own count. Wave 4 established that an
importer's success report is not evidence; the same applies to a stager's manifest. So the
row count, the per-Veda split and every partition here are counted from rows.jsonl and
resolved against the live graph, and the manifest's claims are recorded alongside as
*claims* carrying an agreement flag.
"""

from __future__ import annotations

import json
import subprocess
import sys

from gate_bc_common import (
    CORE_CORPUS_INVARIANT,
    PACKET,
    REPO,
    STAGING,
    attachment_digest,
    core_corpus,
    driver,
    graph_census,
    load_rejected,
    load_rows,
    not_importable_confidences,
    session,
    sha256_file,
    translation_coverage,
    write_json,
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def tally_forced_true(rows):
    out = {}
    for r in rows:
        if r["payload"].get("address_forced_without_content_control") is True:
            out[r["veda"]] = out.get(r["veda"], 0) + 1
    return out


def reject_tally(rejected):
    out = {}
    for r in rejected:
        code = r.get("reason_code") or r.get("reason") or "<none>"
        out[str(code)] = out.get(str(code), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def main() -> int:
    porcelain = git("status", "--porcelain")
    head = git("rev-parse", "HEAD")
    # This packet writes its own artifacts, so by the time phase 0 runs the tree is dirty
    # with exactly those. Cleanliness is therefore reported as "dirty with nothing but this
    # packet", which is checkable, rather than as a bare boolean that a later re-run of
    # phase 0 would always fail.
    packet_owned = ("data/staging/translation/gate_bc/", "scripts/gate_bc_")
    dirty = [line for line in porcelain.splitlines() if line]
    foreign = [line for line in dirty if not any(tok in line for tok in packet_owned)]

    drv = driver()
    with session(drv) as s:
        census = graph_census(s)
        core = core_corpus(s)
        coverage = translation_coverage(s)
        digest = attachment_digest(s)
    drv.close()

    core_ok = {v: core.get(v) == n for v, n in CORE_CORPUS_INVARIANT.items()}

    baseline = {
        "phase": 0,
        "git": {
            "head": head,
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "clean": porcelain == "",
            "clean_of_everything_but_this_packet": foreign == [],
            "dirty_paths": dirty,
            "foreign_dirty_paths": foreign,
        },
        "graph_fingerprint": census,
        "core_corpus": {
            "measured": core,
            "invariant": CORE_CORPUS_INVARIANT,
            "agrees": core_ok,
            "all_agree": all(core_ok.values()),
            "measured_total": sum(core.get(v, 0) for v in CORE_CORPUS_INVARIANT),
        },
        "live_translation_coverage": coverage,
        "translation_attachment_digest": digest,
        "central_policy": {
            "not_importable_confidences": sorted(not_importable_confidences()),
            "read_from": "scripts/validate_staging_artifact.py::NOT_IMPORTABLE",
            "note": "imported rather than re-declared, so this packet cannot soften it",
        },
        "pre_existing_baseline_failure": {
            "test": "tests/enrich/test_formula_families.py",
            "gap": "GAP-FORMULA-003",
            "expected_nested_formulas": 1103,
            "measured_nested_formulas": 1064,
            "in_scope_of_this_task": False,
            "note": (
                "baselined at phase 0 and re-measured at phase 14; the translation analysis "
                "touches no formula input, so any movement means this task's scope leaked"
            ),
        },
    }
    write_json("baseline.json", baseline)

    # ---- input manifest: hash every staged translation input, side files included ----
    staged_manifest = json.loads((STAGING / "manifest.json").read_text(encoding="utf-8"))
    files = []
    for p in sorted(STAGING.rglob("*")):
        if p.is_dir() or p == PACKET or PACKET in p.parents:
            continue
        rel = p.relative_to(STAGING).as_posix()
        entry = {
            "path": rel,
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
            "is_side_file": rel not in {"rows.jsonl", "manifest.json"},
        }
        if p.suffix == ".jsonl":
            entry["lines"] = sum(1 for line in p.open(encoding="utf-8") if line.strip())
        files.append(entry)

    declared = {f["path"]: f for f in staged_manifest.get("files", [])}
    hash_agreement = {}
    for f in files:
        if f["path"] in declared:
            d = declared[f["path"]]
            hash_agreement[f["path"]] = {
                "manifest_sha256": d.get("sha256"),
                "measured_sha256": f["sha256"],
                "agrees": d.get("sha256") == f["sha256"],
                "manifest_rows": d.get("rows"),
                "measured_lines": f.get("lines"),
                "rows_agree": d.get("rows") == f.get("lines"),
            }

    m13_plan = STAGING / "m13_plan.json"
    m13_readback = STAGING / "m13_readback.json"
    write_json(
        "input_manifest.json",
        {
            "phase": 0,
            "staging_root": "data/staging/translation",
            "files": files,
            "side_file_count": sum(1 for f in files if f["is_side_file"]),
            "staged_manifest_claims": {
                "algorithm_version": staged_manifest.get("algorithm_version"),
                "code_commit": staged_manifest.get("code_commit"),
                "config_hash": staged_manifest.get("config_hash"),
                "counts": staged_manifest.get("counts"),
                "source_snapshot_ids": staged_manifest.get("source_snapshot_ids"),
                "closes_gaps": staged_manifest.get("closes_gaps"),
            },
            "hash_agreement": hash_agreement,
            "all_declared_hashes_agree": all(v["agrees"] for v in hash_agreement.values()),
            "m13": {
                "plan_sha256": sha256_file(m13_plan) if m13_plan.exists() else None,
                "readback_sha256": sha256_file(m13_readback) if m13_readback.exists() else None,
                "readback": json.loads(m13_readback.read_text(encoding="utf-8"))
                if m13_readback.exists()
                else None,
            },
        },
    )

    # ---- population census: independently measured ----
    rows = load_rows()
    rejected = load_rejected()

    def tally(fn):
        out = {}
        for r in rows:
            k = str(fn(r))
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    ni = not_importable_confidences()
    census_obj = {
        "phase": 0,
        "measured_staged_rows": len(rows),
        "manifest_claimed_accepted": staged_manifest["counts"]["accepted"],
        "agrees_with_manifest": len(rows) == staged_manifest["counts"]["accepted"],
        "measured_rejected_rows": len(rejected),
        "manifest_claimed_rejected": staged_manifest["counts"]["rejected"],
        "by_veda": tally(lambda r: r["veda"]),
        "by_source_id": tally(lambda r: r["source_id"]),
        "by_veda_and_source": tally(lambda r: f"{r['veda']}|{r['source_id']}"),
        "by_evidence_layer": tally(lambda r: r["evidence_layer"]),
        "by_mapping_confidence": tally(lambda r: r["mapping_confidence"]),
        "by_quality_class": tally(lambda r: r["quality_class"]),
        "by_alignment": tally(lambda r: r["payload"].get("alignment")),
        "by_resolution_tier": tally(lambda r: r["payload"].get("resolution_tier")),
        "by_recension_verified": tally(lambda r: r["recension_verified"]),
        "by_translator": tally(lambda r: r["payload"].get("translator")),
        "by_work_edition": tally(lambda r: r["payload"].get("work_edition")),
        "by_relation_asserted": tally(lambda r: r["payload"].get("relation_asserted") or "<none>"),
        "central_policy_split": {
            "not_importable_by_confidence": sum(1 for r in rows if r["mapping_confidence"] in ni),
            "policy_eligible": sum(1 for r in rows if r["mapping_confidence"] not in ni),
        },
        "payload_field_presence": {
            f: sum(1 for r in rows if f in r["payload"])
            for f in sorted({k for r in rows for k in r["payload"]})
        },
        "forced_address_rows": {
            "flag_present": sum(
                1 for r in rows if "address_forced_without_content_control" in r["payload"]
            ),
            "flag_true": sum(
                1
                for r in rows
                if r["payload"].get("address_forced_without_content_control") is True
            ),
            "flag_false": sum(
                1
                for r in rows
                if r["payload"].get("address_forced_without_content_control") is False
            ),
            "flag_true_by_veda": tally_forced_true(rows),
        },
        "rejected_reason_codes": reject_tally(rejected),
    }
    write_json("population_census.json", census_obj)

    print(f"HEAD={head} clean_of_foreign_changes={foreign == []}")
    print(f"graph: {census}")
    print(f"core corpus all_agree={all(core_ok.values())} measured={core}")
    print(f"coverage: {{k: v['covered_mantras'] for ...}} ->")
    for v, d in sorted(coverage["per_veda"].items()):
        print(f"   {v}: covered={d['covered_mantras']} translations={d['translation_nodes']}")
    print(f"attachment digest: {digest}")
    print(f"staged rows measured={len(rows)} manifest={staged_manifest['counts']['accepted']}")
    print(
        "policy: not_importable="
        f"{census_obj['central_policy_split']['not_importable_by_confidence']}"
        f" eligible={census_obj['central_policy_split']['policy_eligible']}"
    )
    print(f"forced addresses: {census_obj['forced_address_rows']}")
    print(f"all declared input hashes agree: {all(v['agrees'] for v in hash_agreement.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
