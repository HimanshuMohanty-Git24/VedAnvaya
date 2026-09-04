"""WSC2023 digital Rigvedic Anukramaṇī adapter.

The dataset is one plain-text file per Maṇḍala. Each data row states one Sūkta:

    hymn.verses.seer.divinity.meter
    3.12.vaiśvāmitro madhucchandāḥ.(1-3)aśvinau,(4-6)indraḥ,...(10-12)sarasvatī.gāyatrī

Fields are separated by ``.``; entries within a field by ``,``; an optional leading
``(...)`` restricts an entry to numbered verses. A field with no parenthesis states one
claim for the whole hymn.

This adapter produces staging records only. It performs no entity resolution: a raw
field value stays a raw string, composite labels are never decomposed, and an
unexpected row is reported rather than repaired.
"""

from __future__ import annotations

import re
from pathlib import Path

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import AnukramaniSegment, AnukramaniStagingRecord, StagingTextRecord
from vedagraph.models.enums import AnukramaniField, AnukramaniParseStatus, ScopeOrigin
from vedagraph.normalize import normalize_nfc

PARSER_VERSION = "wsc2023-anukramani-v1"
EXPECTED_HEADER = "hymn.verses.seer.divinity.meter"
FIELD_ORDER = (AnukramaniField.SEER, AnukramaniField.DIVINITY, AnukramaniField.METER)

_SEGMENT = re.compile(r"^(?:\((?P<scope>[0-9]+(?:[-,][0-9]+)*)\))?(?P<value>[^()]+)$")
_SPAN = re.compile(r"^(?P<start>[0-9]+)(?:-(?P<end>[0-9]+))?$")


class WSC2023AnukramaniAdapter(SourceAdapter):
    """Parses one pinned ``Anukramani/Mandala_N.txt`` artifact."""

    source_id = "WSC2023"

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        raise NotImplementedError(
            "Anukramaṇī artifacts are pinned by commit; use scripts/fetch_wsc2023_anukramani.py"
        )

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        raise NotImplementedError("the Anukramaṇī dataset carries metadata, not Sanskrit text")

    def parse_anukramani(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        source_artifact_id: str,
        mandala: int,
    ) -> list[AnukramaniStagingRecord]:
        text = normalize_nfc(snapshot_path.read_bytes().decode("utf-8"))
        lines = text.split("\n")
        if not lines or lines[0].strip() != EXPECTED_HEADER:
            raise ValueError(f"{snapshot_path} does not start with the expected Anukramaṇī header")
        records: list[AnukramaniStagingRecord] = []
        for line_number, raw in enumerate(lines[1:], start=2):
            line = raw.strip()
            if not line:
                continue
            records.append(
                _parse_row(
                    line,
                    line_number=line_number,
                    mandala=mandala,
                    snapshot_id=snapshot_id,
                    source_artifact_id=source_artifact_id,
                )
            )
        if not records:
            raise ValueError(f"{snapshot_path} contains no Anukramaṇī rows")
        return records


def _parse_row(
    line: str,
    *,
    line_number: int,
    mandala: int,
    snapshot_id: str,
    source_artifact_id: str,
) -> AnukramaniStagingRecord:
    fields = line.split(".")
    notes: list[str] = []
    status = AnukramaniParseStatus.PARSED

    if len(fields) < 2 or not fields[0].isdigit() or not fields[1].isdigit():
        return _invalid(
            line,
            line_number=line_number,
            mandala=mandala,
            snapshot_id=snapshot_id,
            source_artifact_id=source_artifact_id,
            note="row does not begin with hymn and verse numbers",
        )

    sukta = int(fields[0])
    declared = int(fields[1])
    if sukta < 1 or declared < 1:
        return _invalid(
            line,
            line_number=line_number,
            mandala=mandala,
            snapshot_id=snapshot_id,
            source_artifact_id=source_artifact_id,
            note="hymn and verse numbers must be positive",
        )

    values = fields[2:]
    if len(values) != len(FIELD_ORDER):
        # RV 8.31 carries no seer field. The row is kept, the missing field is named,
        # and nothing is guessed about which field was dropped.
        status = AnukramaniParseStatus.PARTIALLY_PARSED
        notes.append(f"expected {len(FIELD_ORDER)} annotated fields, found {len(values)}")
        values = values[-len(FIELD_ORDER) :] if len(values) > len(FIELD_ORDER) else values
        values = [""] * (len(FIELD_ORDER) - len(values)) + values

    raw_fields: dict[AnukramaniField, str | None] = {}
    segments: list[AnukramaniSegment] = []
    for field, raw_field in zip(FIELD_ORDER, values, strict=True):
        raw_fields[field] = raw_field or None
        if not raw_field:
            notes.append(f"{field.value.lower()} field is absent")
            continue
        parsed, field_notes = _parse_field(field, raw_field, declared=declared)
        segments.extend(parsed)
        notes.extend(field_notes)
        if field_notes:
            status = AnukramaniParseStatus.PARTIALLY_PARSED

    return AnukramaniStagingRecord(
        source_artifact_id=source_artifact_id,
        snapshot_id=snapshot_id,
        source_locator=f"Anukramani/Mandala_{mandala}.txt:{line_number}",
        raw_line=line,
        line_number=line_number,
        mandala=mandala,
        sukta=sukta,
        declared_verse_count=declared,
        raw_seer_field=raw_fields.get(AnukramaniField.SEER),
        raw_divinity_field=raw_fields.get(AnukramaniField.DIVINITY),
        raw_meter_field=raw_fields.get(AnukramaniField.METER),
        segments=segments,
        parse_status=status,
        parse_notes=notes,
        parser_version=PARSER_VERSION,
    )


def _invalid(
    line: str,
    *,
    line_number: int,
    mandala: int,
    snapshot_id: str,
    source_artifact_id: str,
    note: str,
) -> AnukramaniStagingRecord:
    return AnukramaniStagingRecord(
        source_artifact_id=source_artifact_id,
        snapshot_id=snapshot_id,
        source_locator=f"Anukramani/Mandala_{mandala}.txt:{line_number}",
        raw_line=line,
        line_number=line_number,
        mandala=mandala,
        sukta=1,
        declared_verse_count=1,
        parse_status=AnukramaniParseStatus.INVALID,
        parse_notes=[note],
        parser_version=PARSER_VERSION,
    )


def _split_segments(field: str) -> list[str]:
    """Split on commas that are outside parentheses; ``(11-12,15-16)x`` is one segment."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for character in field:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return [part for part in (piece.strip() for piece in parts) if part]


def _parse_field(
    field: AnukramaniField, raw_field: str, *, declared: int
) -> tuple[list[AnukramaniSegment], list[str]]:
    segments: list[AnukramaniSegment] = []
    notes: list[str] = []
    for raw_segment in _split_segments(raw_field):
        match = _SEGMENT.match(raw_segment)
        if match is None:
            notes.append(f"{field.value.lower()} segment not understood: {raw_segment!r}")
            continue
        value = match.group("value").strip()
        scope = match.group("scope")
        if not value:
            notes.append(f"{field.value.lower()} segment has no value: {raw_segment!r}")
            continue
        if scope is None:
            segments.append(
                AnukramaniSegment(
                    field=field,
                    raw_segment=raw_segment,
                    raw_value=value,
                    scope_origin=ScopeOrigin.SUKTA_WIDE,
                )
            )
            continue
        spans, span_notes = _parse_spans(scope, declared=declared, field=field)
        notes.extend(span_notes)
        for start, end in spans:
            segments.append(
                AnukramaniSegment(
                    field=field,
                    raw_segment=raw_segment,
                    raw_value=value,
                    raw_scope=scope,
                    scope_origin=(
                        ScopeOrigin.SINGLE_MANTRA if start == end else ScopeOrigin.MANTRA_RANGE
                    ),
                    start_mantra=start,
                    end_mantra=end,
                )
            )
    return segments, notes


def _parse_spans(
    scope: str, *, declared: int, field: AnukramaniField
) -> tuple[list[tuple[int, int]], list[str]]:
    """A scope such as ``11-12,15-16`` becomes two spans. A set is never widened."""
    spans: list[tuple[int, int]] = []
    notes: list[str] = []
    for part in scope.split(","):
        match = _SPAN.match(part.strip())
        if match is None:
            notes.append(f"{field.value.lower()} scope not understood: {part!r}")
            continue
        start = int(match.group("start"))
        end = int(match.group("end") or match.group("start"))
        if start < 1 or end < start:
            notes.append(f"{field.value.lower()} scope is not an ascending span: {part!r}")
            continue
        if end > declared:
            notes.append(
                f"{field.value.lower()} scope {part!r} exceeds the declared {declared} verses"
            )
            continue
        spans.append((start, end))
    return spans, notes
