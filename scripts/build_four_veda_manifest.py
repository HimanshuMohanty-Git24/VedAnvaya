"""Emit the four-Veda corpus CANDIDATE manifest.

This manifest is a COLLECTION, not a work
=========================================

It enumerates four separately-licensed datasets and their identities. It is deliberately
not, and must never become, a single adapted work, because the licences do not permit one:
the Samaveda and Yajurveda primary layers are CC BY-SA 4.0, the Rigveda primary is
CC BY-NC-SA 4.0, and CC BY-NC-SA is not on the BY-SA compatibility list. Under CC BY-SA 4.0
s3(b)(1) a merged adaptation would have to satisfy both simultaneously, which is impossible.
The Atharvaveda transcription is CC0, which composes upward into either -- but only upward.

So this file may carry: four directories, four licence declarations, four attribution
blocks, and rights-neutral cross-work identity facts. It may not carry: one licence
declaration for the whole, a merged text table, or any jointly built index spanning the
BY-SA and BY-NC-SA layers.

CANDIDATE, not frozen
=====================

``status`` is ``CANDIDATE`` and the next phase is the freeze. Nothing here should be read
as a commitment that these bytes are final.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

CANONICAL = REPO / "data" / "canonical"
COMPLETENESS = REPO / "data" / "builds" / "four_veda_corpus_completeness.json"
OUT = REPO / "data" / "builds" / "four_veda_corpus_candidate_manifest.json"

RUN = "FULL_SV_YV_AV_CANONICAL_INGESTION"

MEMBERS: dict[str, dict[str, str]] = {
    "VG:WORK:RV:SAK": {
        "release_dir": "rigveda_full_v1",
        "primary_licence": "CC_BY_NC_SA",
        "attribution": "GRETIL / VedaWeb, Aufrecht lineage; see text_versions.yaml",
    },
    "VG:WORK:SV:KAU": {
        "release_dir": "samaveda_arcika_v1",
        "primary_licence": "CC_BY_SA",
        "attribution": "Sanskrit Wikisource contributors, CC BY-SA 4.0; per-page revids retained",
    },
    "VG:WORK:YV:VSM": {
        "release_dir": "yajurveda_vsm_v1",
        "primary_licence": "CC_BY_SA",
        "attribution": "Sanskrit Wikisource contributors, CC BY-SA 4.0; per-page revids retained",
    },
    "VG:WORK:AV:SAU": {
        "release_dir": "atharvaveda_saunaka_v1",
        "primary_licence": "CC0",
        "attribution": "VedaGraph transcription of Roth & Whitney 1856 (BSB/MDZ bsb10219750)",
    },
}


def _digest_dir(path: Path) -> tuple[str, int]:
    """Aggregate digest over a release directory, and its file count."""
    accumulator = hashlib.sha256()
    count = 0
    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        accumulator.update(file.relative_to(path).as_posix().encode("utf-8"))
        accumulator.update(hashlib.sha256(file.read_bytes()).digest())
        count += 1
    return accumulator.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    completeness: Any = (
        json.loads(COMPLETENESS.read_text(encoding="utf-8")) if COMPLETENESS.exists() else {}
    )
    per_veda = completeness.get("per_veda", {})

    members: dict[str, Any] = {}
    for work_id, spec in MEMBERS.items():
        release = CANONICAL / spec["release_dir"]
        measured = per_veda.get(work_id, {})
        present = release.exists() and (release / "passages.jsonl").exists()
        entry: dict[str, Any] = {
            "work_id": work_id,
            "declared_release_dir": spec["release_dir"],
            "present": present,
            "primary_licence": spec["primary_licence"],
            "attribution": spec["attribution"],
        }
        if present:
            digest, files = _digest_dir(release)
            entry["aggregate_content_sha256"] = digest
            entry["file_count"] = files
            entry["mantra_count"] = measured.get("mantra_count")
            entry["release_kind"] = measured.get("release_kind")
        else:
            # The Atharvaveda production release does not exist. The completeness report
            # falls back to the pilot for MEASUREMENT; this manifest does not, because the
            # pilot is built from the REFERENCE_ONLY Orlandi-lineage text and may not be
            # redistributed or redistributed in derived form. Including it would put an
            # unshippable member into a manifest that reads as shippable.
            entry["reason_absent"] = (
                "no production release exists for this work. The surviving pilot is NOT "
                "substituted here: it is built from the REFERENCE_ONLY Orlandi lineage, "
                "whose terms forbid derived redistribution."
            )
        members[work_id] = entry

    manifest: dict[str, Any] = {
        "manifest_version": "four-veda-candidate-v1",
        "status": "CANDIDATE",
        "not_frozen": (
            "This is a candidate. The freeze is a separate phase and has not happened. "
            "Nothing here asserts that these bytes are final."
        ),
        "produced_by_run": RUN,
        "collection_not_adapted_work": (
            "This manifest enumerates four SEPARATELY LICENSED datasets. It is not a single "
            "adapted work and must not be published as one. SV and YV primary layers are "
            "CC BY-SA 4.0; the Rigveda primary is CC BY-NC-SA 4.0, which is NOT on the BY-SA "
            "compatibility list, so under CC BY-SA 4.0 s3(b)(1) a merged adaptation would "
            "have to satisfy both at once. The AV transcription is CC0, which composes "
            "upward into either but only upward. PERMITTED: four directories, four licences, "
            "four attribution blocks, plus rights-neutral cross-work identity data. "
            "FORBIDDEN: one licence declaration for the whole, a merged text table, or any "
            "jointly built index spanning the BY-SA and BY-NC-SA layers."
        ),
        "members": members,
        "members_present": sorted(w for w, m in members.items() if m["present"]),
        "members_absent": sorted(w for w, m in members.items() if not m["present"]),
        "cross_work_identity": completeness.get("cross_veda_identity_audit", {}),
        "source_assertion_completeness": completeness.get("source_assertion_completeness", {}),
        "samaveda_scope": (
            "The Samaveda member is the Kauthuma ARCIKA corpus only. The gana collections "
            "are a parallel and larger body that VG:WORK:SV:KAU does not address and that "
            "needs its own work_id. This manifest must never be described as containing a "
            "complete Samaveda."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
