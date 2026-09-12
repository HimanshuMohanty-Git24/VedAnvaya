"""Loading the audio catalog and answering "is there a recording for this passage?".

**The one hard problem this module solves.** A recording does not always cover exactly
the passage a reader is looking at. The present source publishes one file per verse, so a
verse usually has its own -- but the first source tried recorded whole suktas and
adhyayas, and a lookup keyed by the mantra's own key then found nothing for all 10,552
Rigvedic mantras even though all 1,028 of their suktas were recorded. The obvious fix,
copying a sukta's record onto each of its mantras, produces the lie Section 8 of the
release spec forbids: a hymn-length recording presented as though each mantra had an
individual track.

:meth:`AudioCatalog.resolve` therefore walks *up* from the requested key and reports
**which level answered**. :class:`AudioMatch` carries ``levels_above``, and that integer is
what lets the frontend say "Recitation of this verse" when it is one, and "Recitation of
this hymn, which contains this passage" when it is not, without the frontend having to know
anything about Vedic structure. One record is returned however many mantras share it, so a
container's track is never multiplied into hundreds of media objects.

**Ancestry is derived from the key, not from the graph.** ``canonical_key`` is
colon-delimited and strictly hierarchical -- ``VG:RV:SAK:M01:S001:V003`` sits under
``VG:RV:SAK:M01:S001`` under ``VG:RV:SAK:M01`` -- so the walk is string truncation and
needs no database round trip per mantra. Truncation stops at four segments because
``VG:RV:SAK`` is a corpus prefix and not a passage; the Work is addressed by its own
``VG:WORK:RV:SAK`` id, which is a different shape and reached through
:meth:`for_work` instead.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from vedagraph.product.audio.models import (
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    MappingConfidence,
)

#: Path of the committed catalog, relative to the data directory.
CATALOG_RELATIVE_PATH: Final = Path("product") / "audio_catalog.jsonl"

#: Directory holding optional local copies, relative to the data directory. Binary media
#: under here is gitignored; the catalog that describes it is not.
CACHE_RELATIVE_PATH: Final = Path("audio") / "cache"

#: A ``canonical_key`` shorter than this is a corpus prefix rather than a passage.
_MIN_KEY_SEGMENTS: Final = 4


def ancestor_keys(canonical_key: str) -> list[str]:
    """The passage keys containing ``canonical_key``, nearest container first.

    ``VG:RV:SAK:M01:S001:V003`` yields ``['VG:RV:SAK:M01:S001', 'VG:RV:SAK:M01']``. The
    key itself is not included: callers distinguish a recording of this passage from a
    recording of something above it, and returning both in one list would erase that.
    """
    parts = canonical_key.split(":")
    return [":".join(parts[:i]) for i in range(len(parts) - 1, _MIN_KEY_SEGMENTS - 1, -1)]


def work_id_for_veda(veda: str) -> str | None:
    """The ``work_id`` addressing a Veda's one recension in this corpus."""
    recension = VEDA_RECENSIONS.get(veda)
    return None if recension is None else f"VG:WORK:{veda}:{recension}"


@dataclass(frozen=True)
class AudioMatch:
    """One recording found for a requested passage, and how far above it sits.

    ``levels_above`` is the field that keeps the product honest. Zero means the recording
    is of the requested passage itself. One or more means it is of a container, and the
    caller must say so rather than implying the narrower thing.
    """

    record: AudioRecord
    matched_key: str
    levels_above: int

    @property
    def is_own_level(self) -> bool:
        """True only when the recording covers exactly the passage that was asked for."""
        return self.levels_above == 0


class AudioCatalog:
    """The catalog in memory, indexed for the two lookups the product performs."""

    def __init__(self, records: Iterable[AudioRecord]) -> None:
        self._records: tuple[AudioRecord, ...] = tuple(records)
        self._by_id: dict[str, AudioRecord] = {}
        for record in self._records:
            if record.audio_id in self._by_id:
                raise ValueError(f"duplicate audio_id {record.audio_id!r} in catalog")
            self._by_id[record.audio_id] = record

        by_scope: defaultdict[str, list[AudioRecord]] = defaultdict(list)
        by_veda: defaultdict[str, list[AudioRecord]] = defaultdict(list)
        for record in self._records:
            if record.scope_key is not None:
                by_scope[record.scope_key].append(record)
            by_veda[record.veda].append(record)
        self._by_scope: dict[str, tuple[AudioRecord, ...]] = {
            key: tuple(value) for key, value in by_scope.items()
        }
        self._by_veda: dict[str, tuple[AudioRecord, ...]] = {
            key: tuple(value) for key, value in by_veda.items()
        }

    @classmethod
    def load(cls, path: Path) -> AudioCatalog:
        """Read a JSONL catalog. A missing file is an empty catalog, not an error.

        No audio is a supported product state -- Section 21 of the release spec -- so a
        deployment that has never run discovery must start and browse normally rather than
        fail at import. A *malformed* file is still an error: that is a defect, not an
        absence.
        """
        if not path.exists():
            return cls(())
        records: list[AudioRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("//"):
                    continue
                try:
                    records.append(AudioRecord.model_validate_json(stripped))
                except ValidationError as error:
                    raise ValueError(f"{path}:{line_number}: {error}") from error
        return cls(records)

    @classmethod
    def load_default(cls, data_dir: Path | str = "data") -> AudioCatalog:
        return cls.load(Path(data_dir) / CATALOG_RELATIVE_PATH)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[AudioRecord]:
        return iter(self._records)

    @property
    def records(self) -> tuple[AudioRecord, ...]:
        return self._records

    def by_id(self, audio_id: str) -> AudioRecord | None:
        return self._by_id.get(audio_id)

    def for_veda(self, veda: str) -> tuple[AudioRecord, ...]:
        return self._by_veda.get(veda, ())

    def at_key(self, canonical_key: str) -> tuple[AudioRecord, ...]:
        """Records attached to exactly this key, with no ancestor walk."""
        return self._by_scope.get(canonical_key, ())

    def resolve(self, canonical_key: str) -> list[AudioMatch]:
        """Recordings covering this passage, nearest level first.

        Returns matches from the first level that has any, and stops. A sukta recording
        and a whole-collection recording both technically cover a given verse, but
        offering both invites the reader to treat the coarser one as an alternative
        reading of the same verse. The nearest containing level is the honest answer.
        """
        own = self.at_key(canonical_key)
        if own:
            return [AudioMatch(record=r, matched_key=canonical_key, levels_above=0) for r in own]
        for distance, ancestor in enumerate(ancestor_keys(canonical_key), start=1):
            found = self.at_key(ancestor)
            if found:
                return [
                    AudioMatch(record=r, matched_key=ancestor, levels_above=distance) for r in found
                ]
        return []

    def for_work(self, work_id: str) -> tuple[AudioRecord, ...]:
        """Every record for the Veda this ``work_id`` addresses, at any scope."""
        for veda, recension in VEDA_RECENSIONS.items():
            if work_id == f"VG:WORK:{veda}:{recension}":
                return self.for_veda(veda)
        return ()

    def scope_keys_for_veda(self, veda: str) -> frozenset[str]:
        """Distinct mapped keys for one Veda. Used to derive live coverage figures."""
        return frozenset(
            record.scope_key for record in self.for_veda(veda) if record.scope_key is not None
        )

    def counts_by(self, attribute: str) -> dict[str, int]:
        """Record counts grouped by one field, for the stats endpoint and reports.

        Derived rather than declared, so a coverage figure in the product cannot drift
        from the catalog the way a hard-coded number would.
        """
        counts: defaultdict[str, int] = defaultdict(int)
        for record in self._records:
            value = getattr(record, attribute)
            counts[str(value) if value is not None else "UNSPECIFIED"] += 1
        return dict(sorted(counts.items()))

    def mapped_confidences(self) -> dict[str, int]:
        return self.counts_by("mapping_confidence")

    def playable(self) -> tuple[AudioRecord, ...]:
        """Records the product can actually sound, as opposed to link out to."""
        return tuple(
            record
            for record in self._records
            if record.mapping_confidence is not MappingConfidence.EXTERNAL_ONLY
            and (record.media_url or record.local_cache_path)
        )


def scope_plural(scope: AudioScope) -> str:
    """Reader-facing name for a *class* of spans, for prose that aggregates them.

    Separate from :func:`scope_label` because that one is demonstrative -- "this hymn" --
    which is right beside one recording and ungrammatical in a sentence about a thousand.
    A work-level caveat built from ``scope_label`` read "these recordings cover structural
    spans -- this hymn -- and not individual verses".
    """
    return {
        AudioScope.MANTRA: "verses",
        AudioScope.SUKTA: "hymns",
        AudioScope.SECTION: "sections",
        AudioScope.ADHYAYA: "adhyayas",
        AudioScope.KANDA: "kandas",
        AudioScope.COLLECTION: "collections",
        AudioScope.WORK: "whole Samhitas",
        AudioScope.UNKNOWN: "unstated spans",
    }[scope]


def scope_label(scope: AudioScope) -> str:
    """Reader-facing name for a scope. Used where a UI must name the span in prose."""
    return {
        AudioScope.MANTRA: "this verse",
        AudioScope.SUKTA: "this hymn",
        AudioScope.SECTION: "this section",
        AudioScope.ADHYAYA: "this adhyaya",
        AudioScope.KANDA: "this kanda",
        AudioScope.COLLECTION: "this collection",
        AudioScope.WORK: "this Samhita",
        AudioScope.UNKNOWN: "an unstated span",
    }[scope]


def write_catalog(path: Path, records: Sequence[AudioRecord]) -> int:
    """Write a catalog deterministically: sorted by id, one compact JSON object per line.

    Sorted and compact so that re-running discovery against an unchanged source produces
    a byte-identical file and therefore an empty diff. A catalog that reorders on every
    run would make every discovery run look like a content change.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: record.audio_id)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in ordered:
            handle.write(
                json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            )
            handle.write("\n")
    return len(ordered)
