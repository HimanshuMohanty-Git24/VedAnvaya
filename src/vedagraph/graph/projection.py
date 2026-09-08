"""Corpus-to-graph projection: read canonical JSONL → in-memory node/rel dicts."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import orjson

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
                "structural_path": orjson.dumps(
                    rec.get("structural_path", [])
                ).decode(),
                "native_labels": orjson.dumps(
                    rec.get("native_labels", [])
                ).decode(),
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


def iter_translation_nodes(
    project_root: pathlib.Path,
) -> Iterator[dict[str, Any]]:
    """Yield Translation node dicts for all four Vedas."""
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "translations.jsonl"
        for rec in _iter_jsonl(path):
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
) -> Iterator[dict[str, Any]]:
    """Yield HAS_TRANSLATION relationship dicts keyed by passage UUID."""
    data_root = _data_root(project_root)
    for _veda, dirname in CANONICAL_DIRS.items():
        path = data_root / dirname / "translations.jsonl"
        for rec in _iter_jsonl(path):
            yield {
                "passage_entity_id": rec["passage_id"],
                "translation_id": rec["translation_id"],
                "language": rec.get("language", "en"),
                "translator": rec.get("translator", ""),
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
