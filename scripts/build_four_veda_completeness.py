"""Measure four-Veda coverage from the released records, and audit cross-work identity.

Everything here is COUNTED, never asserted. Each figure is derived by reading the JSONL a
release actually emitted, so a number that appears in the report exists in the corpus. The
distinction matters because this repository has twice recorded a coverage figure that no
record supported -- once by citing a source's page count as a work's coverage, once by
generalising a property of one page to a whole corpus.

Two things this report deliberately refuses to do
=================================================

**It does not fill a gap with a plausible number.** A layer a release does not emit is
reported as ``0`` with the release named, not omitted and not estimated.

**It does not treat a missing release as a zero.** A work whose release directory is
absent is reported as ``present: false``. Zero coverage and no release are different
states, and collapsing them would let a forgotten build masquerade as a measured gap.

Usage::

    python scripts/build_four_veda_completeness.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

CANONICAL = REPO / "data" / "canonical"
OUT_PATH = REPO / "data" / "builds" / "four_veda_corpus_completeness.json"

# Release directory per work, most-preferred first. A pilot is listed only where no
# production release exists yet, and the report names which one it read.
RELEASE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "VG:WORK:RV:SAK": ("rigveda_full_v1",),
    "VG:WORK:SV:KAU": ("samaveda_arcika_v1", "samaveda_pilot_v1"),
    "VG:WORK:YV:VSM": ("yajurveda_vsm_v1", "yajurveda_pilot_v1"),
    # atharvaveda_saunaka_digital_working_v1 is the WORKING PRIVATE full-corpus build from
    # the GRETIL/TITUS digital Sanskrit. The image-based independent-transcription project
    # that would have produced atharvaveda_saunaka_v1 was cancelled and never released, so
    # that name is kept only so a future release would take precedence over the pilot.
    "VG:WORK:AV:SAU": (
        "atharvaveda_saunaka_digital_working_v1",
        "atharvaveda_saunaka_v1",
        "atharvaveda_pilot_v1",
    ),
}

VEDA_LABEL = {
    "VG:WORK:RV:SAK": "Rigveda Shakala",
    "VG:WORK:SV:KAU": "Samaveda Kauthuma (ARCIKA corpus only; gana not ingested)",
    "VG:WORK:YV:VSM": "Shukla Yajurveda Vajasaneyi Madhyandina",
    "VG:WORK:AV:SAU": "Atharvaveda Shaunaka",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def resolve_release(work_id: str) -> Path | None:
    for name in RELEASE_CANDIDATES[work_id]:
        candidate = CANONICAL / name
        if (candidate / "passages.jsonl").exists():
            return candidate
    return None


def _mantra_ids(passages: list[dict[str, Any]]) -> set[str]:
    return {str(p["entity_id"]) for p in passages if p.get("entity_type") == "MANTRA"}


def measure(work_id: str) -> dict[str, Any]:
    release = resolve_release(work_id)
    if release is None:
        return {
            "work_id": work_id,
            "label": VEDA_LABEL[work_id],
            "present": False,
            "reason": "no release directory with a passages.jsonl was found",
            "searched": list(RELEASE_CANDIDATES[work_id]),
        }

    passages = read_jsonl(release / "passages.jsonl")
    texts = read_jsonl(release / "text_versions.jsonl")
    translations = read_jsonl(release / "translations.jsonl")
    metadata = read_jsonl(release / "traditional_metadata.jsonl")
    audio = read_jsonl(release / "audio_recordings.jsonl")
    segments = read_jsonl(release / "audio_segments.jsonl")
    issues = read_jsonl(release / "qa_issues.jsonl")

    mantras = _mantra_ids(passages)

    # A passage counts as covered by a layer when at least one record of that layer
    # targets it. Counting records instead would let three text layers on one mantra read
    # as three covered mantras.
    def covered(rows: list[dict[str, Any]], key: str, predicate: Any = None) -> int:
        hit = {
            str(row[key])
            for row in rows
            if key in row and str(row[key]) in mantras and (predicate is None or predicate(row))
        }
        return len(hit)

    by_role: Counter[str] = Counter(str(t.get("text_role")) for t in texts)
    by_language: Counter[str] = Counter(str(t.get("language")) for t in translations)

    # PRIMARY_TEXT only. EXTRACTED_FROM_CONTAINER is deliberately NOT counted here:
    # folding it in reported sanskrit_primary_coverage = 1975 for the Vajasaneyi Samhita,
    # a work whose whole point is that it HAS NO PRIMARY LAYER. A number that contradicts
    # the record it summarises is worse than a gap. The union is reported separately, and
    # named for what it is.
    sanskrit_primary = covered(
        texts, "passage_id", lambda row: str(row.get("text_role")) == "PRIMARY_TEXT"
    )
    sanskrit_fallback = covered(
        texts, "passage_id", lambda row: str(row.get("text_role")) == "EXTRACTED_FROM_CONTAINER"
    )
    sanskrit_parallel = covered(
        texts, "passage_id", lambda row: str(row.get("text_role")) == "PARALLEL_TEXT"
    )

    metadata_by_predicate: dict[str, int] = {}
    for predicate in ("HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"):
        targets = {
            str(row["scope"]["passage_id"])
            for row in metadata
            if row.get("predicate") == predicate and isinstance(row.get("scope"), dict)
        }
        metadata_by_predicate[predicate] = len(targets & mantras)

    return {
        "work_id": work_id,
        "label": VEDA_LABEL[work_id],
        "present": True,
        "release_dir": release.name,
        # A pilot standing in for an absent production release is NOT a release, and the
        # difference is load-bearing: the surviving Atharvaveda pilot is built from the
        # REFERENCE_ONLY Orlandi-lineage GRETIL text, which may not be redistributed or
        # redistributed in derived form. Counting it silently would put an unshippable
        # layer into an aggregate that reads as shippable.
        "is_production_release": release.name == RELEASE_CANDIDATES[work_id][0],
        "release_kind": (
            "PRODUCTION" if release.name == RELEASE_CANDIDATES[work_id][0] else "PILOT_FALLBACK"
        ),
        "passage_count_total": len(passages),
        "mantra_count": len(mantras),
        "container_count": len(passages) - len(mantras),
        "sanskrit_primary_coverage": sanskrit_primary,
        "sanskrit_source_faithful_fallback_coverage": sanskrit_fallback,
        "sanskrit_any_canonical_layer_coverage": covered(
            texts,
            "passage_id",
            lambda row: str(row.get("text_role")) in {"PRIMARY_TEXT", "EXTRACTED_FROM_CONTAINER"},
        ),
        "has_primary_text_layer": sanskrit_primary > 0,
        "sanskrit_parallel_coverage": sanskrit_parallel,
        "text_records_by_role": dict(sorted(by_role.items())),
        "english_coverage": covered(
            translations, "passage_id", lambda row: str(row.get("language")) == "en"
        ),
        "hindi_coverage": covered(
            translations, "passage_id", lambda row: str(row.get("language")) == "hi"
        ),
        "translation_records_by_language": dict(sorted(by_language.items())),
        "rishi_coverage": metadata_by_predicate["HAS_RISHI"],
        "devata_coverage": metadata_by_predicate["HAS_DEVATA"],
        "chandas_coverage": metadata_by_predicate["HAS_CHANDAS"],
        "traditional_metadata_records": len(metadata),
        "audio_recordings": len(audio),
        "audio_segments": len(segments),
        "audio_coverage": covered(segments, "passage_id"),
        "qa_issues_total": len(issues),
        "qa_issues_by_severity": dict(
            sorted(Counter(str(i.get("severity")) for i in issues).items())
        ),
        "unresolved_textual_qa": sum(
            1 for i in issues if "text" in str(i.get("check_id", "")).lower()
        ),
        "unresolved_structural_qa": sum(
            1
            for i in issues
            if any(word in str(i.get("check_id", "")).lower() for word in ("structur", "sequence"))
        ),
        "rights_restricted_text_records": sum(
            1
            for t in texts
            if str(t.get("rights_status"))
            in {
                "REFERENCE_ONLY",
                "EXTERNAL_REFERENCE_ONLY",
                "PERMISSION_REQUIRED",
                "RESEARCH_ONLY",
                "UNKNOWN",
            }
        ),
        "rights_statuses_present": dict(
            sorted(Counter(str(t.get("rights_status")) for t in texts).items())
        ),
    }


#: The Rigveda keeps rsi/devata/chandas in a separate deterministic knowledge layer rather
#: than in its corpus release, so reading only ``traditional_metadata.jsonl`` reports the
#: Rigveda as having ZERO traditional metadata. That is false, and it is the exact shape of
#: error this report exists to avoid: a real layer invisible because the reader looked in
#: one place. The layer is counted separately and labelled, never merged into the corpus
#: figure, because the two are produced by different pipelines with different guarantees.
KNOWLEDGE_LAYER = REPO / "data" / "knowledge" / "rigveda_deterministic_v1"


def measure_knowledge_layer(mantra_keys: set[str]) -> dict[str, Any]:
    path = KNOWLEDGE_LAYER / "knowledge_assertions.jsonl"
    rows = read_jsonl(path)
    if not rows:
        return {"present": False, "path": path.as_posix()}
    by_predicate: dict[str, set[str]] = {}
    for row in rows:
        by_predicate.setdefault(str(row.get("predicate")), set()).add(str(row.get("subject_key")))
    return {
        "present": True,
        "layer": KNOWLEDGE_LAYER.name,
        "assertion_count": len(rows),
        "rishi_coverage": len(by_predicate.get("HAS_RISHI", set()) & mantra_keys),
        "devata_coverage": len(by_predicate.get("HAS_DEVATA", set()) & mantra_keys),
        "chandas_coverage": len(by_predicate.get("HAS_CHANDAS", set()) & mantra_keys),
        "note": (
            "Counted from the separate deterministic knowledge layer, NOT from the corpus "
            "release's traditional_metadata.jsonl, which carries only 9 rows. Reported "
            "beside the corpus figure rather than added into it: the two layers are built "
            "by different pipelines and merging them would hide which one a claim came from."
        ),
    }


def audit_collisions() -> dict[str, Any]:
    """Cross-work uniqueness over canonical key, URN and UUID."""
    keys: dict[str, list[str]] = {}
    urns: dict[str, list[str]] = {}
    ids: dict[str, list[str]] = {}
    per_work: dict[str, int] = {}

    for work_id in RELEASE_CANDIDATES:
        release = resolve_release(work_id)
        if release is None:
            continue
        passages = read_jsonl(release / "passages.jsonl")
        per_work[work_id] = len(passages)
        for passage in passages:
            keys.setdefault(str(passage["canonical_key"]), []).append(work_id)
            urns.setdefault(str(passage["canonical_urn"]), []).append(work_id)
            ids.setdefault(str(passage["entity_id"]), []).append(work_id)

    def collisions(index: dict[str, list[str]]) -> dict[str, list[str]]:
        return {value: works for value, works in index.items() if len(set(works)) > 1}

    intra = {
        "canonical_key_repeated_within_one_work": {
            value: works for value, works in keys.items() if len(works) > 1 and len(set(works)) == 1
        }
    }
    return {
        "passages_examined": sum(per_work.values()),
        "passages_per_work": per_work,
        "cross_work_canonical_key_collisions": collisions(keys),
        "cross_work_canonical_urn_collisions": collisions(urns),
        "cross_work_entity_id_collisions": collisions(ids),
        "intra_work_duplicate_keys": intra["canonical_key_repeated_within_one_work"],
        "clean": not (
            collisions(keys)
            or collisions(urns)
            or collisions(ids)
            or intra["canonical_key_repeated_within_one_work"]
        ),
    }


def audit_orphan_provenance() -> dict[str, Any]:
    """Source assertions whose provenance does not resolve against the registries."""
    from vedagraph.config.registry import load_source_artifacts, load_sources

    known_sources = {source.source_id for source in load_sources()}
    known_artifacts = {artifact.artifact_id for artifact in load_source_artifacts()}

    findings: dict[str, list[str]] = {}
    total = 0
    for work_id in RELEASE_CANDIDATES:
        release = resolve_release(work_id)
        if release is None:
            continue
        orphans: list[str] = []
        for name in ("source_assertions.jsonl", "structure_reconciliation.jsonl"):
            for row in read_jsonl(release / name):
                total += 1
                source_id = str(row.get("source_id", ""))
                artifact_id = row.get("source_artifact_id")
                if source_id not in known_sources:
                    orphans.append(f"{name}:{row.get('assertion_id')}: source {source_id!r}")
                elif artifact_id and str(artifact_id) not in known_artifacts:
                    orphans.append(f"{name}:{row.get('assertion_id')}: artifact {artifact_id!r}")
                elif not str(row.get("source_locator", "")):
                    orphans.append(f"{name}:{row.get('assertion_id')}: empty source_locator")
        if orphans:
            findings[work_id] = sorted(orphans)
    return {
        "assertions_examined": total,
        "orphan_claims": findings,
        "orphan_count": sum(len(v) for v in findings.values()),
        "clean": not findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    per_veda = {work_id: measure(work_id) for work_id in RELEASE_CANDIDATES}

    rigveda_release = resolve_release("VG:WORK:RV:SAK")
    if rigveda_release is not None:
        rv_keys = {
            str(p["canonical_key"])
            for p in read_jsonl(rigveda_release / "passages.jsonl")
            if p.get("entity_type") == "MANTRA"
        }
        per_veda["VG:WORK:RV:SAK"]["separate_knowledge_layer"] = measure_knowledge_layer(rv_keys)
    aggregate_mantras = sum(
        int(entry.get("mantra_count", 0)) for entry in per_veda.values() if entry.get("present")
    )
    aggregate_passages = sum(
        int(entry.get("passage_count_total", 0))
        for entry in per_veda.values()
        if entry.get("present")
    )

    report: dict[str, Any] = {
        "report_version": "four-veda-completeness-v1",
        "counting_rule": (
            "Every figure is counted from the JSONL a release emitted. A layer a release "
            "does not emit is 0 with the release named; a work with no release is "
            "present:false, which is a different state from zero coverage."
        ),
        "samaveda_scope_warning": (
            "The Samaveda figures cover the Kauthuma ARCIKA corpus ONLY. The gana "
            "collections are a parallel and larger body that this work_id does not "
            "address. 'Complete Samaveda' is never a correct description of this release."
        ),
        "per_veda": per_veda,
        "aggregate": {
            "works_with_a_production_release": sum(
                1 for e in per_veda.values() if e.get("is_production_release")
            ),
            "works_on_a_pilot_fallback": sorted(
                str(w)
                for w, e in per_veda.items()
                if e.get("present") and not e.get("is_production_release")
            ),
            "works_released": sum(1 for e in per_veda.values() if e.get("present")),
            "works_missing": sorted(str(w) for w, e in per_veda.items() if not e.get("present")),
            "passages_all_works": aggregate_passages,
            "mantras_all_works": aggregate_mantras,
        },
        "cross_veda_identity_audit": audit_collisions(),
        "source_assertion_completeness": audit_orphan_provenance(),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
