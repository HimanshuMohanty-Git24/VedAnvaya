"""Fail-closed parser for VHP traditional-metadata range strings.

VHP writes Rishi/Devata/Chandas metadata as one free-text string per Sukta. Some strings
are a single entity for the whole hymn; others assign different entities to numbered
mantras, to half-verses, or to alternatives introduced by ``va``. This module extracts a
*candidate* scope structure from such a string and refuses to guess.

Nothing produced here is canonical. Every record is a reviewable candidate: only records
whose status is ``PARSED`` may later be considered for promotion, and even those require a
human to accept the reading first.

Grammar forms observed in the current sample, and only those, are supported:

``<entity>``
    A single unscoped entity for the whole passage.
``<n>-<m> <entity>, <n> <entity>, ...``
    A comma-separated list of numbered segments.
``<entity>, <n>-<m> <entity>``
    A leading default entity followed by numbered exceptions.
``<entity> (<n>-<m> <entity>, ...)``
    A leading default entity with a parenthesised exception list.
``<n>, <n>, <n> <entity>``
    Bare numbers accumulate onto the next segment that carries an entity.

Anything else, including an entity that precedes a number inside the same segment, is
reported as ``AMBIGUOUS`` or ``UNSUPPORTED`` rather than being interpreted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vedagraph.identity import uuid_for_urn
from vedagraph.models import CandidateMetadataAssertion, CandidateMetadataScope
from vedagraph.models.enums import (
    CandidateScopeType,
    MetadataPredicate,
    RangeParseStatus,
    ReviewStatus,
)

PARSER_VERSION = "vhp-metadata-range-v1"

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_DIGIT = r"[०-९0-9]"  # noqa: RUF001
_DASH = "[-–—]"  # noqa: RUF001
_LEADING_SCOPE = re.compile(
    rf"^\s*({_DIGIT}+)\s*{_DASH}\s*({_DIGIT}+)\s*(.*)$|^\s*({_DIGIT}+)\s*(.*)$",
    re.DOTALL,
)
_ANY_DIGIT = re.compile(_DIGIT)
_BARE_NUMBER = re.compile(rf"^\s*{_DIGIT}+\s*$")
_BARE_RANGE = re.compile(rf"^\s*{_DIGIT}+\s*{_DASH}\s*{_DIGIT}+\s*$")

#: Literal Sanskrit qualifiers whose presence means the segment is not a plain whole-mantra
#: claim. Detection is a literal match, never an interpretation of meaning. ``standalone``
#: markers must be a whole word: "va" ("or") is also a syllable inside ordinary names such
#: as Dyavaprthivyau, and a substring test there would produce false qualifiers.
QUALIFIER_MARKERS: tuple[tuple[str, CandidateScopeType | None, bool], ...] = (
    ("आद्यर्धर्चस्य", CandidateScopeType.HALF_VERSE, False),
    ("अन्त्योऽर्धर्चः", CandidateScopeType.HALF_VERSE, False),
    ("अन्त्योर्धर्चः", CandidateScopeType.HALF_VERSE, False),
    ("अर्धर्च", CandidateScopeType.HALF_VERSE, False),
    ("द्वितीयस्य", CandidateScopeType.UNRESOLVED_SUBSPAN, False),
    ("पादस्य", CandidateScopeType.PADA, False),
    ("पादः", CandidateScopeType.PADA, False),
    ("वा", None, True),
)


@dataclass(frozen=True)
class _Segment:
    raw: str
    numbers: list[int]
    start: int | None
    end: int | None
    entity: str
    is_bare_number: bool


def _to_int(value: str) -> int:
    return int(value.translate(DEVANAGARI_DIGITS))


def _split_segments(value: str) -> list[str]:
    """Split on commas. Commas are the only separator VHP uses in the observed strings."""
    return [part.strip() for part in value.split(",") if part.strip()]


def _read_segment(raw: str) -> _Segment:
    match = _LEADING_SCOPE.match(raw)
    if match is None:
        return _Segment(
            raw=raw, numbers=[], start=None, end=None, entity=raw.strip(), is_bare_number=False
        )
    if match.group(1) is not None:
        start, end, rest = _to_int(match.group(1)), _to_int(match.group(2)), match.group(3)
        return _Segment(
            raw=raw,
            numbers=[],
            start=start,
            end=end,
            entity=rest.strip(),
            is_bare_number=bool(_BARE_RANGE.match(raw)),
        )
    number, rest = _to_int(match.group(4)), match.group(5)
    return _Segment(
        raw=raw,
        numbers=[number],
        start=number,
        end=number,
        entity=rest.strip(),
        is_bare_number=bool(_BARE_NUMBER.match(raw)),
    )


def _qualifiers(entity: str) -> tuple[list[str], CandidateScopeType | None]:
    found: list[str] = []
    words = entity.split()
    scope_override: CandidateScopeType | None = None
    for marker, scope, standalone in QUALIFIER_MARKERS:
        present = marker in words if standalone else marker in entity
        if present:
            found.append(marker)
            if scope is not None and scope_override is None:
                scope_override = scope
    return found, scope_override


def _scope_for(segment: _Segment, override: CandidateScopeType | None) -> CandidateScopeType:
    if override is not None:
        return override
    if len(segment.numbers) > 1:
        return CandidateScopeType.MANTRA_SET
    if segment.start is not None and segment.end is not None:
        if segment.start == segment.end:
            return CandidateScopeType.MANTRA
        return CandidateScopeType.MANTRA_RANGE
    return CandidateScopeType.WHOLE_PASSAGE


def parse_range_value(
    value: str,
) -> tuple[RangeParseStatus, list[CandidateMetadataScope], list[str], str | None]:
    """Return ``(status, segments, unparsed_remainder, note)`` for one metadata string."""
    text = " ".join(value.split())
    if not text:
        return RangeParseStatus.INVALID, [], [], "empty metadata value"
    if not _ANY_DIGIT.search(text):
        scope = CandidateMetadataScope(
            scope_type=CandidateScopeType.WHOLE_PASSAGE,
            raw_scope_text=text,
            raw_entity=text,
            qualifier_markers=_qualifiers(text)[0],
            needs_review=False,
        )
        return RangeParseStatus.PARSED, [scope], [], None

    head, parenthetical = _split_parenthetical(text)
    if parenthetical is None and "(" in text:
        return (
            RangeParseStatus.UNSUPPORTED,
            [],
            [text],
            "parenthesised content is not in a supported position; the observed grammar "
            "only allows a trailing exception list, and an inline gloss can itself contain "
            "the comma used as the segment separator",
        )

    scopes: list[CandidateMetadataScope] = []
    unparsed: list[str] = []
    notes: list[str] = []
    ambiguous = False

    if parenthetical is not None:
        if _ANY_DIGIT.search(head):
            return (
                RangeParseStatus.AMBIGUOUS,
                [],
                [text],
                "a default entity and a parenthesised exception list both carry numbers",
            )
        if head:
            scopes.append(
                CandidateMetadataScope(
                    scope_type=CandidateScopeType.WHOLE_PASSAGE,
                    raw_scope_text=head,
                    raw_entity=head,
                    qualifier_markers=_qualifiers(head)[0],
                    needs_review=True,
                    notes="default entity qualified by a parenthesised exception list",
                )
            )
        body = parenthetical
        notes.append("exceptions were read from a parenthesised list")
    else:
        body = text

    pending: list[int] = []
    for raw in _split_segments(body):
        segment = _read_segment(raw)
        if segment.is_bare_number:
            pending.extend(segment.numbers or _expand(segment))
            continue
        if segment.start is None and pending:
            # A bare number list must attach to the following entity, and this segment
            # carries no number of its own, so the attachment cannot be resolved.
            ambiguous = True
            unparsed.append(raw)
            pending = []
            continue
        if segment.start is None:
            if scopes or _ANY_DIGIT.search(raw):
                # Either a second unscoped entity, or an entity written before its numbers.
                # Both need a human to say which mantras are meant.
                ambiguous = True
                unparsed.append(raw)
                continue
            scopes.append(
                CandidateMetadataScope(
                    scope_type=CandidateScopeType.WHOLE_PASSAGE,
                    raw_scope_text=raw,
                    raw_entity=segment.entity,
                    qualifier_markers=_qualifiers(segment.entity)[0],
                    needs_review=True,
                    notes="leading default entity; later segments override it",
                )
            )
            continue
        if not segment.entity:
            ambiguous = True
            unparsed.append(raw)
            pending = []
            continue
        markers, override = _qualifiers(segment.entity)
        numbers = sorted({*pending, *(segment.numbers or [])})
        pending = []
        scope_type = _scope_for(
            _Segment(raw, numbers, segment.start, segment.end, segment.entity, False),
            override,
        )
        scopes.append(
            CandidateMetadataScope(
                scope_type=scope_type,
                start_mantra=segment.start if scope_type != CandidateScopeType.MANTRA_SET else None,
                end_mantra=segment.end if scope_type != CandidateScopeType.MANTRA_SET else None,
                mantras=numbers if scope_type == CandidateScopeType.MANTRA_SET else [],
                raw_scope_text=raw,
                raw_entity=segment.entity,
                qualifier_markers=markers,
                needs_review=override is not None or bool(markers),
            )
        )
    if pending:
        ambiguous = True
        unparsed.append(", ".join(str(number) for number in pending))

    if not scopes:
        return RangeParseStatus.INVALID, [], unparsed or [text], "no segment could be read"
    if ambiguous:
        return (
            RangeParseStatus.AMBIGUOUS,
            scopes,
            unparsed,
            "at least one segment could not be attached to a scope without guessing",
        )
    if unparsed:
        return RangeParseStatus.PARTIALLY_PARSED, scopes, unparsed, "; ".join(notes) or None
    if any(scope.needs_review for scope in scopes):
        return (
            RangeParseStatus.PARTIALLY_PARSED,
            scopes,
            [],
            "; ".join(
                [
                    *notes,
                    "at least one segment carries a sub-mantra or alternative "
                    "qualifier that was preserved rather than flattened",
                ]
            ),
        )
    return RangeParseStatus.PARSED, scopes, [], "; ".join(notes) or None


def _expand(segment: _Segment) -> list[int]:
    if segment.start is None or segment.end is None:
        return []
    return list(range(segment.start, segment.end + 1))


def _split_parenthetical(text: str) -> tuple[str, str | None]:
    if "(" not in text:
        return text, None
    open_index = text.index("(")
    close_index = text.rfind(")")
    if close_index < open_index:
        return text, None
    head = text[:open_index].strip().rstrip(",").strip()
    inner = text[open_index + 1 : close_index].strip().rstrip(",").strip()
    tail = text[close_index + 1 :].strip()
    if tail:
        # An exception list followed by more content is outside the observed grammar.
        return text, None
    return head, inner


def parse_metadata_value(
    *,
    subject_id: str,
    predicate: MetadataPredicate,
    value: str,
    source_id: str,
    source_locator: str,
) -> CandidateMetadataAssertion:
    """Parse one VHP metadata string into a reviewable candidate assertion."""
    status, scopes, unparsed, note = parse_range_value(value)
    return CandidateMetadataAssertion(
        candidate_id=uuid_for_urn(
            f"urn:vedagraph:metadata-candidate:{subject_id}:{predicate}:"
            f"{source_id}:{PARSER_VERSION}"
        ),
        subject_id=subject_id,
        predicate=predicate,
        source_id=source_id,
        source_locator=source_locator,
        raw_value=" ".join(value.split()),
        parse_status=status,
        parser_version=PARSER_VERSION,
        segments=scopes,
        unparsed_remainder=unparsed,
        safe_to_promote=(
            status == RangeParseStatus.PARSED and not any(scope.needs_review for scope in scopes)
        ),
        review_status=ReviewStatus.NEEDS_REVIEW,
        notes=note,
    )
