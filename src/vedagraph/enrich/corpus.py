"""One read of the four canonical corpora, shared by every enrichment stage.

Each stage needs the same things -- mantras, their primary Sanskrit, their translations,
their traditional metadata -- and each stage transliterating and normalizing the corpus
again would dominate the runtime. This module reads once and hands out an immutable view.

Traditional attribution is read here too, and which Vedas have any is a per-corpus fact
recorded in :data:`KNOWLEDGE_ARTIFACTS` rather than assumed.

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


#: Deterministic knowledge-layer artifacts holding traditional attribution, by Veda.
#:
#: There is one entry per Veda that has one, and the absences are as load-bearing as the
#: presences -- so they are written here rather than left implicit in a path.
#:
#: This map replaces a hard-coded single Rigvedic path whose docstring asserted that "the
#: other three sources carry no anukramani at all". That was false and expensive: the
#: Vajasaneyi corpus had carried 2,240 source-stated rsi assertions covering 1,960 of its
#: 1,975 mantras since ingestion, and nothing read them, so every report in this
#: repository that said attribution was Rigveda-only was measuring the reader rather than
#: the data. A missing directory here is skipped silently *by design* -- an artifact under
#: construction must not break the corpus loader -- which is exactly why the absence has
#: to be documented in this table instead of discovered from a stack trace.
KNOWLEDGE_ARTIFACTS: Final[dict[str, str | None]] = {
    "RV": "rigveda_deterministic_v1",
    "YV": "yajurveda_deterministic_v1",
    "AV": "atharvaveda_deterministic_v1",
    # The Kauthuma arcika has no attainable attribution layer. Its school's own indices
    # -- the Arseya and Devatadhyaya Brahmanas -- are keyed to samans in the gana
    # collections, which this corpus does not contain, so the join key exists for 7.7% of
    # verses. Transferring Rigvedic attribution along the 90.1% of Samavedic verses that
    # have a Rigvedic parallel was measured, considered and refused: no provenance class
    # in this graph is true of it. See docs/reports/NON_RV_ATTRIBUTION_ACQUISITION_V3.md.
    "SV": None,
}

#: Predicates read from the knowledge layer into the corpus view.
ATTRIBUTION_PREDICATES: Final[frozenset[str]] = frozenset(
    {"HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"}
)


def _resolved_metadata(project_root: pathlib.Path) -> dict[str, dict[str, list[str]]]:
    """Resolved Rishi/Devata/Chandas entity keys per passage canonical key.

    Read from the deterministic knowledge layer rather than from
    ``canonical/*/traditional_metadata.jsonl``, because the canonical files hold raw
    source strings and the knowledge layer holds them resolved to registry entity keys.

    Every artifact in :data:`KNOWLEDGE_ARTIFACTS` that exists is read. The Rigveda
    contributes rsi, devata and chandas; the Yajurveda contributes rsi only, and its
    absence of metre is a source-stated absence rather than a gap to be filled from
    Rigvedic practice.
    """
    grouped: dict[str, dict[str, list[str]]] = {}
    root = project_root / "data" / "knowledge"
    for dirname in KNOWLEDGE_ARTIFACTS.values():
        if dirname is None:
            continue
        for record in iter_jsonl(root / dirname / "knowledge_assertions.jsonl"):
            predicate = str(record.get("predicate", ""))
            if predicate not in ATTRIBUTION_PREDICATES:
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
