"""Lexical graph: Lemma nodes, MENTIONS_LEMMA and EXACT_PARALLEL_OF relationships."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import orjson


def _iter_jsonl(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    for raw in path.read_bytes().split(b"\n"):
        raw = raw.strip()
        if raw:
            yield orjson.loads(raw)


_LEXICAL_DIR = pathlib.Path("data") / "knowledge" / "rigveda_lexical_v1"


def iter_lemma_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Lemma node dicts from the RV lexical layer."""
    path = project_root / _LEXICAL_DIR / "lemmas.jsonl"
    for rec in _iter_jsonl(path):
        yield {
            "lemma": rec["lemma"],
            "normalized_lemma": rec.get("normalized_lemma", ""),
            "mantra_count": rec.get("mantra_count", 0),
            "token_count": rec.get("token_count", 0),
            "parts_of_speech": orjson.dumps(rec.get("parts_of_speech", [])).decode(),
            "lemma_ids": orjson.dumps(rec.get("lemma_ids", [])).decode(),
        }


def iter_mentions_entity_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield MENTIONS_ENTITY relationship dicts (Passage -> Devata/Rishi).

    These are lexically derived from VedaWeb morphology and are provenance-distinct
    from the Anukramani-sourced HAS_DEVATA edges; both are kept rather than merged.
    """
    path = project_root / _LEXICAL_DIR / "mentions.jsonl"
    for rec in _iter_jsonl(path):
        yield {
            "subject_key": rec["subject_key"],
            "subject_id": rec["subject_id"],
            "object_key": rec["object_key"],
            "entity_type": rec.get("entity_type", ""),
            "occurrence_count": rec.get("occurrence_count", 1),
            "provenance_class": rec.get("provenance_class", ""),
            "annotation_layer_id": rec.get("annotation_layer_id", ""),
        }


def iter_mentions_lemma_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield MENTIONS_LEMMA relationship dicts (Passage -> Lemma).

    Derived from the per-token ``evidence`` recorded on each mention. Evidence entries
    are grouped by (passage, lemma) and the token hits per pair become occurrence_count,
    so no count is invented beyond what the lexical layer already records.
    """
    path = project_root / _LEXICAL_DIR / "mentions.jsonl"
    counts: dict[tuple[str, str], int] = {}
    provenance: dict[tuple[str, str], str] = {}

    for rec in _iter_jsonl(path):
        subject_key: str = rec["subject_key"]
        for evidence in rec.get("evidence", []):
            lemma = evidence.get("lemma")
            if not lemma:
                continue
            pair = (subject_key, lemma)
            counts[pair] = counts.get(pair, 0) + 1
            provenance.setdefault(pair, rec.get("provenance_class", ""))

    for (subject_key, lemma), count in counts.items():
        yield {
            "subject_key": subject_key,
            "lemma": lemma,
            "occurrence_count": count,
            "provenance_class": provenance[(subject_key, lemma)],
        }


def iter_exact_parallel_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield EXACT_PARALLEL_OF relationship dicts from RV lexical layer."""
    path = project_root / _LEXICAL_DIR / "mantra_parallels.jsonl"
    for rec in _iter_jsonl(path):
        predicate: str = rec.get("predicate", "EXACT_PARALLEL_OF")
        metrics: dict[str, Any] = rec.get("metrics", {})
        yield {
            "predicate": predicate,
            "subject_key": rec["subject_key"],
            "subject_id": rec["subject_id"],
            "object_key": rec["object_key"],
            "object_id": rec.get("object_id", ""),
            "methods": orjson.dumps(rec.get("methods", [])).decode(),
            "strongest_method": rec.get("strongest_method", ""),
            "similarity": float(metrics.get("character_ngram_similarity", "1.0")),
            "status": rec.get("status", ""),
            "provenance_class": rec.get("provenance_class", ""),
        }
