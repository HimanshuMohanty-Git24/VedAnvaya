"""Corpus-to-graph projection: read canonical JSONL → in-memory node/rel dicts."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from hashlib import sha256
from typing import Any

import orjson

from vedagraph.graph.corrections import CorrectionApplier, load_corrections

# ---------------------------------------------------------------------------
# Canonical dataset directories (relative to data root)
# ---------------------------------------------------------------------------

CANONICAL_DIRS: dict[str, str] = {
    "RV": "rigveda_full_v1",
    "SV": "samaveda_arcika_v1",
    "YV": "yajurveda_vsm_v1",
    "AV": "atharvaveda_saunaka_digital_working_v1",
}

_WORK_IDS: dict[str, str] = {
    "RV": "VG:WORK:RV:SAK",
    "SV": "VG:WORK:SV:KAU",
    "YV": "VG:WORK:YV:VSM",
    "AV": "VG:WORK:AV:SAU",
}


def _data_root(project_root: pathlib.Path) -> pathlib.Path:
    return project_root / "data" / "canonical"


def _iter_jsonl(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield parsed records from a JSONL file, skipping blank lines."""
    if not path.exists():
        return
    for raw in path.read_bytes().split(b"\n"):
        raw = raw.strip()
        if raw:
            yield orjson.loads(raw)


def _derive_parent_key(canonical_key: str, raw: dict[str, Any]) -> str | None:
    """Return the parent canonical_key, or None if this is a top-level node."""
    # RV carries parent_key in the record
    if "parent_key" in raw:
        parent: str | None = raw["parent_key"]
        return parent or None
    # SV / YV / AV: derive from key structure
    parts = canonical_key.split(":")
    if len(parts) > 4:
        return ":".join(parts[:-1])
    return None


# ---------------------------------------------------------------------------
# Work nodes
# ---------------------------------------------------------------------------


def iter_work_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield one Work node per Veda corpus."""
    data_root = _data_root(project_root)
    for veda, dirname in CANONICAL_DIRS.items():
        works_path = data_root / dirname / "works.jsonl"
        for rec in _iter_jsonl(works_path):
            yield {
                "work_id": rec.get("work_id", _WORK_IDS[veda]),
                "veda": veda,
                "abbreviation": rec.get("abbreviation", ""),
                "work_name": rec.get("work_name", ""),
                "corpus_dir": dirname,
            }


# ---------------------------------------------------------------------------
# Passage nodes
# ---------------------------------------------------------------------------


def iter_passage_nodes(
    project_root: pathlib.Path,
) -> Iterator[dict[str, Any]]:
    """Yield Passage node dicts for all four Vedas."""
    data_root = _data_root(project_root)
    for veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "passages.jsonl"
        for rec in _iter_jsonl(path):
            canonical_key: str = rec["canonical_key"]
            parent_key = _derive_parent_key(canonical_key, rec)
            node: dict[str, Any] = {
                "canonical_key": canonical_key,
                "canonical_urn": rec["canonical_urn"],
                "entity_id": rec["entity_id"],
                "entity_type": rec["entity_type"],
                "work_id": rec["work_id"],
                "veda": veda,
                "hierarchy": orjson.dumps(rec.get("hierarchy", {})).decode(),
                "sequence_in_parent": rec.get("sequence_in_parent", 0),
                "canonical_citation": rec.get("canonical_citation", ""),
                "status": rec.get("status", "CANONICAL"),
                "parent_key": parent_key,
                # SV/YV/AV extras
                "structural_path": orjson.dumps(rec.get("structural_path", [])).decode(),
                "native_labels": orjson.dumps(rec.get("native_labels", [])).decode(),
            }
            yield node


# ---------------------------------------------------------------------------
# TextVersion nodes
# ---------------------------------------------------------------------------


def iter_text_version_nodes(
    project_root: pathlib.Path,
) -> Iterator[dict[str, Any]]:
    """Yield TextVersion node dicts for all four Vedas."""
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "text_versions.jsonl"
        for rec in _iter_jsonl(path):
            yield {
                "text_id": rec["text_id"],
                "passage_id": rec["passage_id"],
                "language": rec.get("language", ""),
                "script": rec.get("script", ""),
                "text_form": rec.get("text_form", ""),
                "text_role": rec.get("text_role", ""),
                "text_version_id": rec.get("text_version_id", ""),
                "text_nfc": rec.get("text_nfc", ""),
                "accented": rec.get("accented", False),
                "source_id": rec.get("source_id", ""),
                "source_artifact_id": rec.get("source_artifact_id", ""),
                "rights_status": rec.get("rights_status", ""),
                "content_sha256": rec.get("content_sha256", ""),
            }


# ---------------------------------------------------------------------------
# Translation nodes
# ---------------------------------------------------------------------------


def _passage_key_maps(project_root: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    """Return (canonical_key by passage UUID, passage UUID by canonical_key)."""
    key_by_id: dict[str, str] = {}
    id_by_key: dict[str, str] = {}
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        for rec in _iter_jsonl(data_root / dirname / "passages.jsonl"):
            key_by_id[rec["entity_id"]] = rec["canonical_key"]
            id_by_key[rec["canonical_key"]] = rec["entity_id"]
    return key_by_id, id_by_key


def build_correction_applier(project_root: pathlib.Path) -> CorrectionApplier:
    """Construct the applier for declared upstream corrections."""
    key_by_id, id_by_key = _passage_key_maps(project_root)
    return CorrectionApplier(load_corrections(project_root), key_by_id, id_by_key)


def iter_translation_nodes(
    project_root: pathlib.Path,
    applier: CorrectionApplier | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield Translation node dicts for all four Vedas.

    Upstream verse-number corrections are applied on the way past, which is what makes all
    17,283 corpus rows representable: two of them carry a colliding ``translation_id``
    because a Wikisource page printed one verse number twice, and without the correction
    the loader's MERGE silently discards one of each pair. See
    :mod:`vedagraph.graph.corrections`.
    """
    applier = applier or build_correction_applier(project_root)
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "translations.jsonl"
        for raw in _iter_jsonl(path):
            rec = applier.apply(raw)
            yield {
                "translation_id": rec["translation_id"],
                "passage_id": rec["passage_id"],
                "language": rec.get("language", "en"),
                "text": rec.get("text", ""),
                "translator": rec.get("translator", ""),
                "year": rec.get("year", 0),
                "alignment_level": rec.get("alignment_level", ""),
                "quality_status": rec.get("quality_status", ""),
                "rights_status": rec.get("rights_status", ""),
                "source_id": rec.get("source_id", ""),
                "source_artifact_id": rec.get("source_artifact_id", ""),
                "work_edition": rec.get("work_edition", ""),
                "upstream_correction_id": rec.get("upstream_correction_id", ""),
                "upstream_correction_reason": rec.get("upstream_correction_reason", ""),
            }


# ---------------------------------------------------------------------------
# Source nodes
# ---------------------------------------------------------------------------


def iter_source_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield deduplicated Source node dicts."""
    seen: set[str] = set()
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "sources.jsonl"
        for rec in _iter_jsonl(path):
            sid: str = rec["source_id"]
            if sid in seen:
                continue
            seen.add(sid)
            yield {
                "source_id": sid,
                "name": rec.get("name", ""),
                "organization": rec.get("organization", ""),
                "url": rec.get("url", ""),
                "authority_tier": str(rec.get("authority_tier", "")),
                "bulk_ingestion_status": rec.get("bulk_ingestion_status", ""),
            }


# ---------------------------------------------------------------------------
# CONTAINS relationships
# ---------------------------------------------------------------------------


def iter_contains_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield CONTAINS relationship dicts.

    Subject is either Work.work_id (for top-level passages) or Passage.canonical_key.
    Object is always Passage.canonical_key.
    """
    data_root = _data_root(project_root)
    for veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "passages.jsonl"
        for rec in _iter_jsonl(path):
            canonical_key: str = rec["canonical_key"]
            parent_key = _derive_parent_key(canonical_key, rec)
            if parent_key is None:
                # Top-level: Work → Passage
                yield {
                    "rel_type": "WORK_CONTAINS",
                    "from_work_id": _WORK_IDS[veda],
                    "to_passage_key": canonical_key,
                    "sequence": rec.get("sequence_in_parent", 0),
                }
            else:
                yield {
                    "rel_type": "PASSAGE_CONTAINS",
                    "from_passage_key": parent_key,
                    "to_passage_key": canonical_key,
                    "sequence": rec.get("sequence_in_parent", 0),
                }


# ---------------------------------------------------------------------------
# HAS_TEXT_VERSION relationships
# ---------------------------------------------------------------------------


def iter_has_text_version_rels(
    project_root: pathlib.Path,
) -> Iterator[dict[str, Any]]:
    """Yield HAS_TEXT_VERSION relationship dicts keyed by passage UUID."""
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "text_versions.jsonl"
        for rec in _iter_jsonl(path):
            yield {
                "passage_entity_id": rec["passage_id"],
                "text_id": rec["text_id"],
                "language": rec.get("language", ""),
                "text_form": rec.get("text_form", ""),
            }


# ---------------------------------------------------------------------------
# HAS_TRANSLATION relationships
# ---------------------------------------------------------------------------


def iter_has_translation_rels(
    project_root: pathlib.Path,
    applier: CorrectionApplier | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield HAS_TRANSLATION relationship dicts keyed by passage UUID.

    Reads through the same corrections as :func:`iter_translation_nodes`; if it did not,
    a corrected Translation node would be attached to the mantra its mis-printed verse
    number named rather than the one it belongs to.
    """
    applier = applier or build_correction_applier(project_root)
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "translations.jsonl"
        for raw in _iter_jsonl(path):
            rec = applier.apply(raw)
            yield {
                "passage_entity_id": rec["passage_id"],
                "translation_id": rec["translation_id"],
                "language": rec.get("language", "en"),
                "translator": rec.get("translator", ""),
            }


# ---------------------------------------------------------------------------
# QA issue nodes
# ---------------------------------------------------------------------------


def iter_qa_issue_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield QAIssue node dicts for all four corpora.

    These are the caveats each corpus records about itself: a numbering gap the edition
    prints, a locator the source uses twice, a metrical classification the source declines
    to make. They were previously visible only in a JSONL file next to the corpus, which
    meant a graph query could return AV 9.6.49 as an ordinary mantra with no hint that its
    own corpus flags the surrounding sequence as gapped.

    Projected for all four Vedas rather than the Atharvaveda alone. The brief asks only for
    the ten Atharvaveda items, but a Veda-specific branch here would be *more* code than
    the uniform pass and would leave the Rigveda's 842 findings invisible for no reason.
    Most carry no ``entity_id``, so they attach to the Work; the few that name an entity
    also attach to that Passage.
    """
    data_root = _data_root(project_root)
    for veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "qa_issues.jsonl"
        for index, rec in enumerate(_iter_jsonl(path)):
            details = rec.get("details", {})
            # Identity is content-derived: the corpus writes these without stable ids for
            # the unscoped ones, and an index alone would renumber on any corpus change.
            fingerprint = orjson.dumps(
                [rec.get("check_id", ""), rec.get("message", ""), details],
                option=orjson.OPT_SORT_KEYS,
            )
            issue_id = rec.get("issue_id") or (
                f"VG:QA:{veda}:{sha256(fingerprint).hexdigest()[:16]}"
            )
            yield {
                "issue_id": str(issue_id),
                "veda": veda,
                "work_id": _WORK_IDS[veda],
                "check_id": rec.get("check_id", ""),
                "severity": rec.get("severity", ""),
                "message": rec.get("message", ""),
                "details": orjson.dumps(details, option=orjson.OPT_SORT_KEYS).decode(),
                "entity_id": rec.get("entity_id") or "",
                "scope_key": str(details.get("parent", "")),
                "sequence": index,
            }


# ---------------------------------------------------------------------------
# Corpus statistics (from manifests)
# ---------------------------------------------------------------------------

_MANIFEST_PASSAGE_COUNTS: dict[str, int] = {
    # Total passages in passages.jsonl including structural (Section/Hymn) + Mantra levels
    # RV: 10 mandalas + 1028 suktas + 10552 mantras = 11590
    # SV: 498 structural containers + 1844 mantras = 2342
    # YV: 40 sections + 1975 mantras = 2015
    # AV: 20 kandas + 731 suktas + 5839 mantras = 6590
    "RV": 11590,
    "SV": 2342,
    "YV": 2015,
    "AV": 6590,
}

_MANIFEST_MANTRA_COUNTS: dict[str, int] = {
    "RV": 10552,  # all RV passages are mantras or sections; leaf count from manifest
    "SV": 1844,
    "YV": 1975,
    "AV": 5839,
}


def manifest_passage_count(veda: str) -> int:
    """Return expected passage count from manifest for a given Veda code."""
    return _MANIFEST_PASSAGE_COUNTS.get(veda, 0)


def manifest_mantra_count(veda: str) -> int:
    """Return expected leaf-level mantra count from manifest for a given Veda code."""
    return _MANIFEST_MANTRA_COUNTS.get(veda, 0)
