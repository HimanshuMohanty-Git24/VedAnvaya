#!/usr/bin/env python3
"""Phase J: prove this analysis changed nothing, and hash the packet.

The census alone cannot prove that. A node and relationship count is unchanged by rewriting
the text of every translation in place, so the load-bearing check here is the attachment
digest: a sha256 over every (passage, source, alignment_level, translation_id, text-hash)
tuple in the graph, sorted. If a single translation body had moved, the count would agree
and the digest would not.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from gate_bc_common import (
    CORE_CORPUS_INVARIANT,
    PACKET,
    REPO,
    attachment_digest,
    core_corpus,
    driver,
    graph_census,
    session,
    sha256_file,
    translation_coverage,
    write_json,
)


def main() -> int:
    baseline = json.loads((PACKET / "baseline.json").read_text(encoding="utf-8"))

    drv = driver()
    with session(drv) as s:
        census = graph_census(s)
        core = core_corpus(s)
        coverage = translation_coverage(s)
        digest = attachment_digest(s)
    drv.close()

    b_census = baseline["graph_fingerprint"]
    b_core = baseline["core_corpus"]["measured"]
    b_digest = baseline["translation_attachment_digest"]
    b_cov = {
        v: d["covered_mantras"] for v, d in baseline["live_translation_coverage"]["per_veda"].items()
    }
    now_cov = {v: d["covered_mantras"] for v, d in coverage["per_veda"].items()}

    checks = {
        "graph_census_unchanged": census == b_census,
        "core_corpus_unchanged": core == b_core,
        "core_corpus_matches_invariant": all(
            core.get(v) == n for v, n in CORE_CORPUS_INVARIANT.items()
        ),
        "translation_coverage_unchanged": now_cov == b_cov,
        "translation_attachment_digest_unchanged": digest["digest_sha256"]
        == b_digest["digest_sha256"],
        "translation_attachment_count_unchanged": digest["attachments"]
        == b_digest["attachments"],
    }

    # Hash every file in the packet, and hash the list of hashes so the packet has one id.
    files = []
    for p in sorted(PACKET.rglob("*")):
        if p.is_file() and p.name != "packet_manifest.json":
            files.append(
                {
                    "path": p.relative_to(PACKET).as_posix(),
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                }
            )
    roll = hashlib.sha256()
    for f in files:
        roll.update(f"{f['path']}:{f['sha256']}\n".encode())

    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    packet_owned = ("data/staging/translation/gate_bc/", "scripts/gate_bc_", "tests/unit/test_translation_gate_bc.py")
    dirty = [line for line in porcelain.splitlines() if line.strip()]
    foreign = [line for line in dirty if not any(tok in line for tok in packet_owned)]

    result = {
        "phase": "J",
        "no_canonical_import_performed": True,
        "statement": (
            "no :Translation node and no HAS_TRANSLATION edge was created, updated or deleted "
            "by this task. Every graph interaction was a read."
        ),
        "baseline": {
            "census": b_census,
            "core_corpus": b_core,
            "coverage": b_cov,
            "attachment_digest": b_digest,
        },
        "final": {
            "census": census,
            "core_corpus": core,
            "coverage": now_cov,
            "attachment_digest": digest,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "pre_existing_baseline_failure": {
            "test": "tests/enrich/test_formula_families.py",
            "case": "test_real_artifact_reproduces_the_v1_substring_figure_on_the_identity_surface",
            "gap": "GAP-FORMULA-003",
            "expected": 1103,
            "measured_at_phase_0": 1064,
            "measured_at_phase_14": 1064,
            "unchanged": True,
            "assertion_text": "assert 1064 == 1103",
            "rest_of_file": "37 passed",
            "scope_leak": False,
            "why_no_leak_is_possible": (
                "this task read the graph and wrote only files under "
                "data/staging/translation/gate_bc, scripts/gate_bc_* and one new test file. "
                "It touched no formula artifact, no enrichment code and no graph data."
            ),
        },
        "git": {
            "clean_of_everything_but_this_packet": foreign == [],
            "foreign_dirty_paths": foreign,
            "packet_owned_dirty_paths": dirty,
        },
        "packet": {
            "files": files,
            "file_count": len(files),
            "packet_sha256": roll.hexdigest(),
        },
    }
    write_json("packet_manifest.json", result)

    for k, v in checks.items():
        print(f"  {'OK  ' if v else 'FAIL'}  {k}")
    print(f"  census: {census}")
    print(f"  core:   {core}")
    print(f"  digest: {digest['digest_sha256'][:24]}... ({digest['attachments']} attachments)")
    print(f"  packet: {len(files)} files, sha256 {roll.hexdigest()}")
    print(f"  git clean of foreign changes: {foreign == []}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
