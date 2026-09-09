"""One read of the four canonical corpora, shared by every enrichment stage.

Each stage needs the same things -- mantras, their primary Sanskrit, their translations,
their traditional metadata -- and each stage transliterating and normalizing the corpus
again would dominate the runtime. This module reads once and hands out an immutable view.

The awkward part it hides is that "the primary Sanskrit text" is not spelled the same way
in all four datasets. The Rigveda, Samaveda and Atharvaveda mark their principal reading
``PRIMARY_TEXT``; the Vajasaneyi Yajurveda marks its accented layer
``EXTRACTED_FROM_CONTAINER``, because the source prints a whole adhyaya as one block and
the mantras were cut out of it. Selecting on ``PRIMARY_TEXT`` alone silently returns zero
Yajurveda texts, which reads as "the Yajurveda has no cross-Veda parallels" rather than as
a bug. :data:`PRIMARY_TEXT_ROLE` names the correct role per Veda, and
:func:`load_corpus` fails loudly if a Veda yields no text at all.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final

import orjson

from vedagraph.enrich.surfaces import TextSurfaces, build_surfaces
from vedagraph.graph.projection import CANONICAL_DIRS

VEDAS: Final[tuple[str, ...]] = ("RV", "SV", "YV", "AV")

#: The ``text_role`` carrying each corpus's principal Sanskrit reading. See module
#: docstring: this is a per-dataset fact, not a preference.
PRIMARY_TEXT_ROLE: Final[dict[str, str]] = {
    "RV": "PRIMARY_TEXT",
    "SV": "PRIMARY_TEXT",
    "YV": "EXTRACTED_FROM_CONTAINER",
    "AV": "PRIMARY_TEXT",
}


def iter_jsonl(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield parsed records from a JSONL file, skipping blank lines."""
    if not path.exists():
        return
    for raw in path.read_bytes().split(b"\n"):
        stripped = raw.strip()
        if stripped:
            yield orjson.loads(stripped)


@dataclass(frozen=True)
class MantraRecord:
    """One leaf mantra with everything the enrichment stages read from it."""

    passage_key: str
    passage_id: str
    veda: str
    citation: str
    surfaces: TextSurfaces
    translations: tuple[str, ...] = ()
    devatas: tuple[str, ...] = ()
    rishis: tuple[str, ...] = ()
    chandas: tuple[str, ...] = ()

    @property
    def has_translation(self) -> bool:
        return bool(self.translations)


@dataclass(frozen=True)
class Corpus:
    """Every mantra of the four Vedas, indexed the ways the stages need."""

    mantras: tuple[MantraRecord, ...]
    by_key: dict[str, MantraRecord] = field(default_factory=dict)

    def of_veda(self, veda: str) -> tuple[MantraRecord, ...]:
        return tuple(m for m in self.mantras if m.veda == veda)

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for mantra in self.mantras:
            counts[mantra.veda] = counts.get(mantra.veda, 0) + 1
        return counts


def _mantra_keys(corpus_dir: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Map passage UUID to (canonical_key, citation) for leaf mantras only."""
    keys: dict[str, tuple[str, str]] = {}
    for record in iter_jsonl(corpus_dir / "passages.jsonl"):
        if record.get("entity_type") != "MANTRA":
            continue
        keys[record["entity_id"]] = (
            record["canonical_key"],
            record.get("canonical_citation", record["canonical_key"]),
        )
    return keys


def _translations_by_passage(corpus_dir: pathlib.Path) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for record in iter_jsonl(corpus_dir / "translations.jsonl"):
        text = record.get("text", "").strip()
        if text:
            grouped.setdefault(record["passage_id"], []).append(text)
    return grouped


def _resolved_metadata(project_root: pathlib.Path) -> dict[str, dict[str, list[str]]]:
    """Resolved Rishi/Devata/Chandas entity keys per passage canonical key.

    Read from the deterministic knowledge layer, not from
    ``canonical/*/traditional_metadata.jsonl``. The canonical file holds 9 raw VHP
    strings; the knowledge layer holds the 31,646 resolved assertions the graph is
    actually built from, already mapped to registry entity keys. Only the Rigveda has any
    -- the other three sources carry no anukramani at all -- and that gap is reported by
    the analytics stage rather than papered over.
    """
    path = project_root / "data" / "knowledge" / "rigveda_deterministic_v1"
    grouped: dict[str, dict[str, list[str]]] = {}
    for record in iter_jsonl(path / "knowledge_assertions.jsonl"):
        predicate = str(record.get("predicate", ""))
        if predicate not in {"HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"}:
            continue
        key = record.get("subject_key")
        value = record.get("object_key")
        if key and value:
            grouped.setdefault(str(key), {}).setdefault(predicate, []).append(str(value))
    return grouped


def load_corpus(project_root: pathlib.Path) -> Corpus:
    """Read all four canonical corpora into one immutable view.

    Raises if any Veda contributes no mantra text, because every failure mode seen while
    building this layer -- a renamed dataset directory, a ``text_role`` that differs per
    corpus, a passage type filter that does not match -- shows up as one silently empty
    Veda rather than as an error.
    """
    data_root = project_root / "data" / "canonical"
    metadata_by_key = _resolved_metadata(project_root)
    mantras: list[MantraRecord] = []

    for veda, dirname in CANONICAL_DIRS.items():
        corpus_dir = data_root / dirname
        keys = _mantra_keys(corpus_dir)
        translations = _translations_by_passage(corpus_dir)
        role = PRIMARY_TEXT_ROLE[veda]
        seen = 0

        for record in iter_jsonl(corpus_dir / "text_versions.jsonl"):
            if record.get("text_role") != role:
                continue
            identity = keys.get(record["passage_id"])
            if identity is None:
                continue
            passage_key, citation = identity
            meta = metadata_by_key.get(passage_key, {})
            mantras.append(
                MantraRecord(
                    passage_key=passage_key,
                    passage_id=record["passage_id"],
                    veda=veda,
                    citation=citation,
                    surfaces=build_surfaces(
                        passage_key, veda, record.get("script", ""), record.get("text_nfc", "")
                    ),
                    translations=tuple(translations.get(record["passage_id"], ())),
                    devatas=tuple(sorted(meta.get("HAS_DEVATA", ()))),
                    rishis=tuple(sorted(meta.get("HAS_RISHI", ()))),
                    chandas=tuple(sorted(meta.get("HAS_CHANDAS", ()))),
                )
            )
            seen += 1

        if seen == 0:
            raise ValueError(
                f"{veda}: no mantra text found in {corpus_dir} under text_role={role!r}. "
                "Check PRIMARY_TEXT_ROLE against the dataset before trusting any count."
            )

    mantras.sort(key=lambda m: m.passage_key)
    return Corpus(mantras=tuple(mantras), by_key={m.passage_key: m for m in mantras})
