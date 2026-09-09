"""Entity nodes: Rishi, Devata, Chandas from registry YAML + knowledge assertions."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any, Final

import yaml


def _load_yaml(path: pathlib.Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Registry entity nodes
# ---------------------------------------------------------------------------


#: Rsi registries, with the namespace each carries onto its nodes.
#:
#: They are separate files and separate namespaces on purpose. The Rigvedic registry
#: stores Sarvanukramani patronymic compounds (``rāhūgaṇo gotamaḥ``) where the Yajurvedic
#: index gives bare names (``गोतमः``), so only 8 of 228 Yajurvedic names equal a Rigvedic
#: label outright. A further 64 appear as one word inside a Rigvedic compound, which is a
#: candidate identity signal and not identity -- ``bhāradvāja`` matches inside a Rigvedic
#: entry that is itself a *dual*, Bharadvaja-Rjisva. Merging on either signal is an
#: alias-level error that per-row sampling would not catch, since ``prajāpati`` alone
#: carries 222 assertions. ``normalized_name`` is projected onto both so that a query can
#: join them deliberately, with a caveat, instead of the graph deciding.
RISHI_REGISTRIES: Final[tuple[tuple[str, str], ...]] = (
    ("rishis.yaml", "RV_WSC2023_ANUKRAMANI"),
    ("rishis_yv.yaml", "YV_VSM_RSISUCI"),
    ("rishis_av.yaml", "AV_WHITNEY_ANUKRAMANI"),
)

#: Metre registries, same reasoning as the rsi ones. Whitney's Atharvavedic metre
#: vocabulary is 579 distinct printed strings against the Rigvedic registry's 34, because
#: he prints compound descriptions of individual verses (``anustubgarbha 4-p. tristubh``)
#: where the Rigvedic index names a metre. They are not the same vocabulary and are not
#: merged.
CHANDAS_REGISTRIES: Final[tuple[tuple[str, str], ...]] = (
    ("chandas.yaml", "RV_WSC2023_ANUKRAMANI"),
    ("chandas_av.yaml", "AV_WHITNEY_ANUKRAMANI"),
)


def _visarga_folded(label: str) -> str:
    """The label with a trailing visarga removed, in Devanagari or IAST.

    Projected as ``normalized_name`` so a cross-namespace join is expressible without
    either registry having asserted that two indices mean the same person.
    """
    # The first character is DEVANAGARI SIGN VISARGA, not a colon; both
    # spellings are folded because this runs over Devanagari values and IAST labels.
    return label.rstrip("ः").rstrip("ḥ").strip()  # noqa: RUF001


def iter_rishi_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Rishi node dicts from every rsi registry."""
    for filename, namespace in RISHI_REGISTRIES:
        path = project_root / "data" / "registry" / filename
        if not path.exists():
            continue
        data = _load_yaml(path)
        for rec in data.get("entities", []):
            label: str = rec.get("preferred_label", "")
            yield {
                "entity_key": rec["entity_key"],
                "preferred_label": label,
                "occurrence_count": rec.get("occurrence_count", 0),
                "registry_namespace": rec.get("registry_namespace", namespace),
                "label_iast": rec.get("label_iast", label),
                "normalized_name": rec.get(
                    "normalized_name", _visarga_folded(rec.get("label_iast", label))
                ),
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
    """Yield Chandas node dicts from every metre registry."""
    for filename, namespace in CHANDAS_REGISTRIES:
        path = project_root / "data" / "registry" / filename
        if not path.exists():
            continue
        for rec in _load_yaml(path).get("entities", []):
            label: str = rec.get("preferred_label", "")
            yield {
                "entity_key": rec["entity_key"],
                "preferred_label": label,
                "registry_namespace": rec.get("registry_namespace", namespace),
                "label_iast": rec.get("label_iast", label),
                "normalized_name": rec.get("normalized_name", _visarga_folded(label)),
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
    """Yield HAS_RISHI / HAS_DEVATA / HAS_CHANDAS rows from every knowledge artifact.

    Previously hard-wired to the single Rigvedic path, which is why the graph carried
    zero attribution edges on the Samaveda, Yajurveda and Atharvaveda while a
    source-stated Yajurvedic rsi layer sat unread on disk. The set of artifacts, and the
    reason the Samaveda has none, is recorded in
    :data:`vedagraph.enrich.corpus.KNOWLEDGE_ARTIFACTS` -- one table, read by both the
    corpus view and the projection, so the two cannot drift.
    """
    from vedagraph.enrich.corpus import ATTRIBUTION_PREDICATES, KNOWLEDGE_ARTIFACTS

    root = project_root / "data" / "knowledge"
    for dirname in KNOWLEDGE_ARTIFACTS.values():
        if dirname is None:
            continue
        for rec in _iter_jsonl(root / dirname / "knowledge_assertions.jsonl"):
            predicate: str = rec.get("predicate", "")
            if predicate not in ATTRIBUTION_PREDICATES:
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
