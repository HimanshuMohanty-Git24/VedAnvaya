"""Entity nodes: Rishi, Devata, Chandas from registry YAML + knowledge assertions."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import yaml


def _load_yaml(path: pathlib.Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Registry entity nodes
# ---------------------------------------------------------------------------


def iter_rishi_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Rishi node dicts from the registry."""
    path = project_root / "data" / "registry" / "rishis.yaml"
    if not path.exists():
        return
    data = _load_yaml(path)
    for rec in data.get("entities", []):
        entity_key: str = rec["entity_key"]
        yield {
            "entity_key": entity_key,
            "preferred_label": rec.get("preferred_label", ""),
            "occurrence_count": rec.get("occurrence_count", 0),
        }


def iter_devata_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Devata node dicts from the registry."""
    path = project_root / "data" / "registry" / "devatas.yaml"
    if not path.exists():
        return
    data = _load_yaml(path)
    for rec in data.get("entities", []):
        entity_key: str = rec["entity_key"]
        yield {
            "entity_key": entity_key,
            "preferred_label": rec.get("preferred_label", ""),
            "devata_subtype": rec.get("devata_subtype", ""),
            "is_composite": rec.get("is_composite", False),
        }


def iter_chandas_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Chandas node dicts from the registry."""
    path = project_root / "data" / "registry" / "chandas.yaml"
    if not path.exists():
        return
    data = _load_yaml(path)
    for rec in data.get("entities", []):
        entity_key: str = rec["entity_key"]
        yield {
            "entity_key": entity_key,
            "preferred_label": rec.get("preferred_label", ""),
        }


# ---------------------------------------------------------------------------
# Knowledge assertion relationships
# ---------------------------------------------------------------------------


def _iter_jsonl(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    import orjson

    if not path.exists():
        return
    for raw in path.read_bytes().split(b"\n"):
        raw = raw.strip()
        if raw:
            yield orjson.loads(raw)


def iter_rishi_devata_chandas_rels(
    project_root: pathlib.Path,
) -> Iterator[dict[str, Any]]:
    """Yield HAS_RISHI / HAS_DEVATA / HAS_CHANDAS relationship dicts from RV knowledge layer."""
    path = (
        project_root
        / "data"
        / "knowledge"
        / "rigveda_deterministic_v1"
        / "knowledge_assertions.jsonl"
    )
    for rec in _iter_jsonl(path):
        predicate: str = rec.get("predicate", "")
        if predicate not in {"HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"}:
            continue
        yield {
            "predicate": predicate,
            "subject_key": rec["subject_key"],
            "subject_id": rec["subject_id"],
            "object_key": rec["object_key"],
            "object_id": rec.get("object_id", ""),
            "confidence": rec.get("confidence", 1.0),
            "provenance_class": rec.get("provenance_class", ""),
            "scope_origin": rec.get("scope_origin", ""),
            "source_id": rec.get("source_id", ""),
        }
