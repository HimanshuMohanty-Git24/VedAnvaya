"""Griffith 1899 White Yajurveda English translation, aligned to the VSM spine.

Source
======
``sacred-texts.com/hin/wyv/wyvbk01.htm`` .. ``wyvbk40.htm``. Ralph T. H. Griffith,
*The Texts of the White Yajurveda*, E. J. Lazarus & Co., Benares, 1899. Public domain by
age: Griffith died in 1906.

The site's own JSON-LD declares the digitisation base verbatim: "We worked from a somewhat
problematic 1976 photographic reprint of the first edition ... footnotes and indexes are
omitted for technical reasons." That sentence is the origin of nearly every defect this
module reports, and it is why the defects are surfaced rather than smoothed away.

Extraction
==========
The pages are served by a JavaScript application shell; roughly 97% of each response is
chrome. The translation lives in the single element carrying
``data-slot="reader-prose"``, and nothing outside that element is ever read. Inside it the
work is plain ``<h3>`` / ``<p>`` with ``<br>`` at every printed line break, and printed
page turns appear as their own paragraph ``p. N``.

Addressing is PROVEN, never positional
======================================
The nth translation unit is emphatically NOT the nth mantra: sixteen of the forty books
break that assumption. Two independent printed coordinates carry the address, and both are
read rather than assumed.

* **Book.** Each page prints its own ``BOOK THE <ORDINAL>.`` heading. The ordinal is
  parsed and must agree with the book number in the URL; a mismatch is a hard failure.
  The URL alone is never trusted.
* **Mantra.** Griffith numbers each verse in the body text. A unit's address is the number
  printed on its first line. Position in the document is used for exactly one thing --
  deciding which lines belong to which unit, because a verse body is a contiguous run of
  lines and the source offers no other grouping -- and for nothing else. Permuting the
  units cannot change a single canonical key.

The label grammar was derived by enumerating every line-initial token in all forty books,
not guessed. Of 1,916 label-shaped lines, exactly three are followed by a lower-case word;
two of those are cross-references (``18 = IX. 40.``) and the third is a stray numeral
sitting mid-verse in book 16. Requiring an upper-case letter, digit, quote, bracket or
``=`` after the number therefore rejects precisely the one line that is not a label.

Defects are classified, never repaired
======================================
``EXACT`` a canonical mantra resolved by exactly one unit's printed number.
``STRUCTURAL_DIVERGENCE`` a canonical mantra covered by a unit that prints a grouped
label (``40, 41 Return again``) or that spans an unlabelled neighbour.
``SOURCE_GAP`` a canonical mantra no unit claims.
``AMBIGUOUS`` a unit whose printed number is claimed by another unit too, or cannot be
read at all.
``UNRESOLVED`` a unit whose printed number lies outside the canonical book.

Two repairs are permitted and both are recorded on the record they touch.

**Glyph repair.** ``I7`` in book 2 and ``S5`` in book 20 are the only two mixed-glyph
labels in the corpus. A fixed confusion table maps ``I``/``l`` to ``1`` and ``O``/``o`` to
``0``; the result is accepted only if it is in range and unclaimed. ``I7`` repairs to 17.
``S5`` does not -- ``S`` is not in the table, and 55 and 85 are both readings a human could
defend -- so it stays AMBIGUOUS, which is the honest answer.

**Span inference.** When a unit prints *v* and the very next unit prints *v+k*, the
source's own arithmetic proves the intervening numbers are not separately labelled, so the
unit is recorded as covering *v..v+k-1* under STRUCTURAL_DIVERGENCE. This fires only when
both document neighbours resolved cleanly and the unit contains no printed omission row.
Book 23 shows why the omission guard is needed: Griffith replaces VSM 23.20-31 with two
rows of dots, and inferring a span there would invent twelve translations that the page
itself says are absent.

**Numbering-spine divergence.** Book 12 prints 118 labels against 117 canonical mantras
and prints one verse twice, at 97 and again at 102. Counting alone cannot say which copy
is spurious -- dropping either satisfies the arithmetic -- so no shift is applied and every
unit from the first duplicate onward is reported UNRESOLVED with its full text, rather than
asserted onto a spine it may be one off from. This is detected from the artifact (duplicate
normalised text plus a label maximum above the canonical count), not hard-coded.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from lxml import etree
from lxml import html as lxml_html

from vedagraph.ingest.adapters.base import DiscoveredResource
from vedagraph.models import StagingTranslationRecord
from vedagraph.models.enums import TranslationAlignment
from vedagraph.normalize import normalize_nfc

SOURCE_ID = "SACRED_TEXTS"
SOURCE_ARTIFACT_ID = "GRIFFITH.YV.1899.SACREDTEXTS"
WORK_ID = "VG:WORK:YV:VSM"
STAGE_VERSION = "1.0.0"
TRANSLATOR = "Ralph T. H. Griffith"
WORK_EDITION = "The Texts of the White Yajurveda, E. J. Lazarus & Co., Benares, 1899"
PUBLICATION_YEAR = 1899
BOOK_COUNT = 40
BASE_URL = "https://sacred-texts.com/hin/wyv"

_READER_PROSE = ".//*[@data-slot='reader-prose']"
_PAGE_MARKER = re.compile(r"^p\.\s*(\d+)$")
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# A label is one or more comma-separated integers, an optional full stop, then the verse.
_LABEL = re.compile(r"^(?P<label>\d+(?:,\s*\d+)*)\.?[ \t]+(?P<rest>\S.*)$")
# A label-shaped token corrupted by OCR: at least one real digit mixed with glyphs the
# 1976 reprint's scan confuses digits with. Detection is wider than repair on purpose.
_GLYPH_LABEL = re.compile(r"^(?P<label>[IlOoS0-9]{2,})[ \t]+(?P<rest>\S.*)$")
_GLYPH_REPAIRS = {"I": "1", "l": "1", "O": "0", "o": "0"}
# Two bare integers with no comma between them ("6 56 This is thine ordered place"): the
# print carries a stray numeral beside the real one, and only the book's own set of
# printed labels can say which is which.
_DOUBLE_NUMBER = re.compile(r"^(?P<nums>\d+(?:[ \t]+\d+)+)[ \t]+(?P<rest>\S.*)$")
# Griffith's printed mark for an omitted passage: a row of nothing but spaced dots.
_OMISSION_ROW = re.compile(r"^[.\s·]{9,}$")
# Griffith opens a verse with a capital, a numeral, a quote, a bracket, or "=" for a
# cross-reference. The curly quotes are written as escapes so the literal cannot be
# confused with an ASCII apostrophe by a later reader.
_VERSE_OPENERS = frozenset('"(=' + "\u2018\u2019\u201c\u201d")

_ORDINAL_UNITS = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
    "FOURTH": 4,
    "FIFTH": 5,
    "SIXTH": 6,
    "SEVENTH": 7,
    "EIGHTH": 8,
    "NINTH": 9,
    "TENTH": 10,
    "ELEVENTH": 11,
    "TWELFTH": 12,
    "THIRTEENTH": 13,
    "FOURTEENTH": 14,
    "FIFTEENTH": 15,
    "SIXTEENTH": 16,
    "SEVENTEENTH": 17,
    "EIGHTEENTH": 18,
    "NINETEENTH": 19,
    "TWENTIETH": 20,
    "THIRTIETH": 30,
    "FORTIETH": 40,
}
_ORDINAL_TENS = {"TWENTY": 20, "THIRTY": 30, "FORTY": 40}
_BOOK_HEADING = re.compile(r"^BOOK\s+THE\s+([A-Z-]+)\s*\.?$")


class Alignment(StrEnum):
    """The five alignment outcomes this module is required to distinguish."""

    EXACT = "EXACT"
    SOURCE_GAP = "SOURCE_GAP"
    AMBIGUOUS = "AMBIGUOUS"
    STRUCTURAL_DIVERGENCE = "STRUCTURAL_DIVERGENCE"
    UNRESOLVED = "UNRESOLVED"


class Defect(StrEnum):
    """Why a unit or a canonical key failed to align cleanly."""

    DUPLICATE_LABEL = "DUPLICATE_LABEL"
    UNREADABLE_LABEL = "UNREADABLE_LABEL"
    ADJACENT_UNREADABLE_LABEL = "ADJACENT_UNREADABLE_LABEL"
    LABEL_OUT_OF_RANGE = "LABEL_OUT_OF_RANGE"
    NUMBERING_SPINE_DIVERGENCE = "NUMBERING_SPINE_DIVERGENCE"
    PRINTED_OMISSION = "PRINTED_OMISSION"
    LABEL_NOT_PRINTED = "LABEL_NOT_PRINTED"


class AdapterError(RuntimeError):
    """The snapshot does not have the shape this adapter is allowed to read."""


def book_url(book: int) -> str:
    return f"{BASE_URL}/wyvbk{book:02d}.htm"


def parse_book_ordinal(heading: str) -> int:
    """Read ``BOOK THE TWENTY-FIRST.`` as 21, so the URL is never the only witness."""
    match = _BOOK_HEADING.match(heading.strip().upper())
    if match is None:
        raise AdapterError(f"not a book heading: {heading!r}")
    words = match.group(1).split("-")
    if len(words) == 1:
        value = _ORDINAL_UNITS.get(words[0])
        if value is None:
            raise AdapterError(f"unreadable book ordinal: {heading!r}")
        return value
    if len(words) == 2 and words[0] in _ORDINAL_TENS:
        tens = _ORDINAL_TENS[words[0]]
        ones = _ORDINAL_UNITS.get(words[1])
        if ones is None or ones > 9:
            raise AdapterError(f"unreadable book ordinal: {heading!r}")
        return tens + ones
    raise AdapterError(f"unreadable book ordinal: {heading!r}")


@dataclass(frozen=True)
class PrintedLine:
    """One printed line of the translation and the printed page it sits on."""

    text: str
    printed_page: int | None


@dataclass(frozen=True)
class TranslationUnit:
    """One numbered unit of Griffith's text, exactly as the page prints it."""

    book: int
    document_index: int
    label_printed: str
    label_repaired: str | None
    values: tuple[int, ...]
    lines: tuple[str, ...]
    printed_page: int | None
    unreadable: Defect | None = None
    candidates: tuple[int, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def has_omission_row(self) -> bool:
        return any(_OMISSION_ROW.match(line) for line in self.lines)

    def normalized_text(self) -> str:
        folded = unicodedata.normalize("NFKD", self.text)
        stripped = "".join(ch for ch in folded if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9 ]", "", stripped.lower().replace("\n", " ")).strip()


@dataclass(frozen=True)
class AlignedVerse:
    """One canonical mantra bound to the Griffith unit that claims it."""

    canonical_key: str
    adhyaya: int
    mantra: int
    text: str
    source_book: int
    source_verse_label: str
    alignment: Alignment
    source_page_url: str
    snapshot_sha256: str
    printed_page: int | None
    label_repair: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "adhyaya": self.adhyaya,
            "alignment": self.alignment.value,
            "canonical_key": self.canonical_key,
            "label_repair": self.label_repair,
            "mantra": self.mantra,
            "printed_page": self.printed_page,
            "snapshot_sha256": self.snapshot_sha256,
            "source_book": self.source_book,
            "source_page_url": self.source_page_url,
            "source_verse_label": self.source_verse_label,
            "text": self.text,
        }


@dataclass(frozen=True)
class CarriedUnit:
    """A unit that binds to no canonical key, carried whole so no text is lost."""

    alignment: Alignment
    defect: Defect
    source_book: int
    source_verse_label: str
    text: str
    source_page_url: str
    snapshot_sha256: str
    printed_page: int | None
    document_index: int

    def as_json(self) -> dict[str, object]:
        return {
            "alignment": self.alignment.value,
            "defect": self.defect.value,
            "document_index": self.document_index,
            "printed_page": self.printed_page,
            "snapshot_sha256": self.snapshot_sha256,
            "source_book": self.source_book,
            "source_page_url": self.source_page_url,
            "source_verse_label": self.source_verse_label,
            "text": self.text,
        }


@dataclass(frozen=True)
class GapKey:
    """A canonical mantra that no unit claims, with the evidence for why."""

    canonical_key: str
    adhyaya: int
    mantra: int
    defect: Defect

    def as_json(self) -> dict[str, object]:
        return {
            "adhyaya": self.adhyaya,
            "canonical_key": self.canonical_key,
            "defect": self.defect.value,
            "mantra": self.mantra,
        }


@dataclass(frozen=True)
class BookAlignment:
    """Everything one book resolved to."""

    book: int
    unit_count: int
    verses: tuple[AlignedVerse, ...]
    carried: tuple[CarriedUnit, ...]
    gaps: tuple[GapKey, ...]
    snapshot_sha256: str = ""
    content_sha256: str = ""
    spine_divergence_from: int | None = None


@dataclass(frozen=True)
class CanonicalSpine:
    """The canonical address set, read from the release rather than reconstructed."""

    keys: Mapping[tuple[int, int], str]
    counts: Mapping[int, int]

    @classmethod
    def from_passages(cls, path: Path) -> CanonicalSpine:
        keys: dict[tuple[int, int], str] = {}
        counts: Counter[int] = Counter()
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("entity_type") != "MANTRA":
                    continue
                hierarchy = row["hierarchy"]
                adhyaya = int(hierarchy["adhyaya"])
                mantra = int(hierarchy["mantra"])
                keys[(adhyaya, mantra)] = str(row["canonical_key"])
                counts[adhyaya] += 1
        if not keys:
            raise AdapterError(f"no MANTRA rows in {path}")
        return cls(keys=keys, counts=dict(counts))


def extract_lines(html_bytes: bytes) -> tuple[int, tuple[PrintedLine, ...]]:
    """Return the printed book number and every printed line of the reader container."""
    document: etree._Element = lxml_html.fromstring(html_bytes)
    containers = document.findall(_READER_PROSE)
    if len(containers) != 1:
        raise AdapterError(f"expected one reader-prose container, found {len(containers)}")
    container = containers[0]

    printed_book: int | None = None
    raw: list[tuple[str, int | None]] = []
    page: int | None = None
    first_marker: int | None = None
    for child in container:
        tag = child.tag
        if not isinstance(tag, str):
            continue
        if tag in _HEADING_TAGS:
            heading = _element_text(child).strip()
            if _BOOK_HEADING.match(heading.upper()):
                printed_book = parse_book_ordinal(heading)
            continue
        if tag != "p":
            continue
        for line in _paragraph_lines(child):
            marker = _PAGE_MARKER.match(line)
            if marker is not None:
                page = int(marker.group(1))
                if first_marker is None:
                    first_marker = page
                continue
            raw.append((normalize_nfc(line), page))
    if printed_book is None:
        raise AdapterError("no 'BOOK THE ...' heading in the reader container")
    # Lines before the first page turn sit on the page before it; the source states the
    # turn, so the opening page number is read off the print rather than assumed to be 1.
    opening = first_marker - 1 if first_marker is not None else None
    lines = tuple(
        PrintedLine(text=text, printed_page=opening if page is None else page) for text, page in raw
    )
    return printed_book, lines


def content_digest(printed_book: int, lines: Sequence[PrintedLine]) -> str:
    """A digest of the translation itself, stable across retrievals.

    The whole-response sha256 is NOT a content identifier here: every response carries a
    fresh CSP nonce and a fresh SvelteKit hydration id, so refetching an unchanged page
    yields different bytes. Verified 2026-09-07 by fetching the index page twice -- the
    two responses are byte-identical once ``nonce="..."`` and ``__sveltekit_<id>`` are
    removed, and differ otherwise. Downstream therefore needs a second digest that moves
    only when the text moves, and this is it.
    """
    payload = f"BOOK {printed_book}\n" + "\n".join(
        f"{line.printed_page}\t{line.text}" for line in lines
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _element_text(element: etree._Element) -> str:
    """All descendant text of one element, in document order."""
    return "".join(chunk for chunk in element.itertext() if isinstance(chunk, str))


def _paragraph_lines(paragraph: etree._Element) -> list[str]:
    """Split one paragraph on ``<br>``, which is how the source marks printed lines."""
    parts: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        parts.append("".join(buffer).strip())
        buffer.clear()

    def walk(node: etree._Element) -> None:
        if node.tag == "br":
            flush()
        else:
            if node.text:
                buffer.append(node.text)
            for child in node:
                walk(child)
        if node.tail:
            buffer.append(node.tail)

    if paragraph.text:
        buffer.append(paragraph.text)
    for child in paragraph:
        walk(child)
    flush()
    return [part for part in parts if part]


def _reads_as_label(rest: str) -> bool:
    """Griffith opens every verse with a capital, a quote, a numeral or ``=``."""
    head = rest[0]
    return head.isupper() or head.isdigit() or head in _VERSE_OPENERS


@dataclass(frozen=True)
class LabelRead:
    """What a line's leading token turned out to be."""

    label: str
    printed: str
    rest: str
    repaired: bool = False
    candidates: tuple[int, ...] = ()


def _read_label(line: str) -> LabelRead | None:
    """Read a line's leading verse label, or ``None`` if the line is body text.

    ``label`` is empty when the line is label-shaped but the number cannot be settled
    from the token alone; ``candidates`` then lists the readings the print allows.
    """
    doubled = _DOUBLE_NUMBER.match(line)
    if doubled is not None and _reads_as_label(doubled.group("rest")):
        # "6 56 This is thine ordered place": two bare numerals with no comma. One is a
        # stray; the token alone cannot say which, so both readings are carried forward.
        numbers = tuple(int(part) for part in doubled.group("nums").split())
        return LabelRead(
            label="",
            printed=doubled.group("nums"),
            rest=doubled.group("rest"),
            candidates=numbers,
        )
    match = _LABEL.match(line)
    if match is not None and _reads_as_label(match.group("rest")):
        return LabelRead(
            label=match.group("label"), printed=match.group("label"), rest=match.group("rest")
        )
    glyph = _GLYPH_LABEL.match(line)
    if glyph is None:
        return None
    token, rest = glyph.group("label"), glyph.group("rest")
    if token.isdigit() or not any(ch.isdigit() for ch in token):
        return None
    if not _reads_as_label(rest):
        return None
    repaired = "".join(_GLYPH_REPAIRS.get(ch, ch) for ch in token)
    if repaired.isdigit():
        return LabelRead(label=repaired, printed=token, rest=rest, repaired=True)
    return LabelRead(label="", printed=token, rest=rest)


def segment_units(book: int, lines: Sequence[PrintedLine]) -> tuple[TranslationUnit, ...]:
    """Group printed lines into the units the source itself numbers.

    Document order decides only which lines belong together -- a verse body is a
    contiguous run and the source offers no other grouping. It never decides an address.
    """
    units: list[TranslationUnit] = []
    head = LabelRead(label="", printed="", rest="")
    unreadable: Defect | None = Defect.LABEL_NOT_PRINTED
    body: list[str] = []
    page: int | None = lines[0].printed_page if lines else None

    def emit() -> None:
        units.append(
            TranslationUnit(
                book=book,
                document_index=len(units),
                label_printed=head.printed,
                label_repaired=head.label if head.repaired else None,
                values=_label_values(head.label),
                lines=tuple(body),
                printed_page=page,
                unreadable=unreadable,
                candidates=head.candidates,
            )
        )

    for line in lines:
        read = _read_label(line.text)
        if read is None:
            body.append(line.text)
            continue
        if body or units:
            emit()
        head = read
        unreadable = None if read.label else Defect.UNREADABLE_LABEL
        body = [read.rest]
        page = line.printed_page
    if body or not units:
        emit()
    return tuple(units)


def _label_values(label: str) -> tuple[int, ...]:
    if not label:
        return ()
    return tuple(int(part) for part in re.split(r",\s*", label))


def resolve_candidates(
    units: Sequence[TranslationUnit], canon_count: int
) -> tuple[TranslationUnit, ...]:
    """Settle a two-numeral label against the book's own set of printed labels.

    ``6 56 This is thine ordered place`` prints a stray beside the real number. 6 is
    already printed on another unit and 56 is not, so 56 is the only reading the book's
    own numbering leaves open. Order-free: it depends on the multiset of printed labels,
    not on where anything sits.
    """
    printed: Counter[int] = Counter()
    for unit in units:
        for value in unit.values:
            printed[value] += 1
    resolved: list[TranslationUnit] = []
    for unit in units:
        if unit.values or not unit.candidates:
            resolved.append(unit)
            continue
        viable = [
            value for value in unit.candidates if 1 <= value <= canon_count and printed[value] == 0
        ]
        if len(viable) != 1:
            resolved.append(unit)
            continue
        resolved.append(
            replace(
                unit,
                values=(viable[0],),
                label_repaired=str(viable[0]),
                unreadable=None,
            )
        )
    return tuple(resolved)


def _poisoned_by_unreadable(units: Sequence[TranslationUnit]) -> set[int]:
    """Indices whose printed label is contradicted by an unreadable unit beside it.

    If an unreadable unit sits between two units printing consecutive numbers, the span
    holds one more unit than it holds numbers. One of the two printed labels must
    therefore be misattributed, and the print cannot say which, so neither is asserted.
    Book 20 is the case: ``84``, ``S5``, ``85`` -- three units, two numbers.
    """
    poisoned: set[int] = set()
    for index, unit in enumerate(units):
        if unit.values or index == 0 or index == len(units) - 1:
            continue
        before, after = units[index - 1], units[index + 1]
        if len(before.values) != 1 or len(after.values) != 1:
            continue
        if after.values[0] == before.values[0] + 1:
            poisoned.update({index - 1, index + 1})
    return poisoned


def _detect_spine_divergence(units: Sequence[TranslationUnit], canon_count: int) -> int | None:
    """Return the first label from which the printed spine cannot be trusted.

    Fires only on hard evidence: the book prints more labels than the canonical book has
    mantras AND prints the same verse twice. Which copy is spurious is not decidable from
    the print, so the whole tail is refused rather than shifted by a guess.
    """
    labelled = [unit for unit in units if unit.values]
    if not labelled:
        return None
    highest = max(value for unit in labelled for value in unit.values)
    if highest <= canon_count:
        return None
    by_text: dict[str, list[TranslationUnit]] = defaultdict(list)
    for unit in labelled:
        normalized = unit.normalized_text()
        if len(normalized) > 40:
            by_text[normalized].append(unit)
    duplicated = [group for group in by_text.values() if len(group) > 1]
    if not duplicated:
        return None
    return min(min(unit.values) for group in duplicated for unit in group)


def align_book(
    raw_units: Sequence[TranslationUnit],
    *,
    book: int,
    spine: CanonicalSpine,
    snapshot_sha256: str,
) -> BookAlignment:
    """Bind units to canonical keys using only the numbers the source prints."""
    canon_count = spine.counts[book]
    page_url = book_url(book)
    # Sorted on the recorded printed position, so the order the caller happens to hand
    # units over cannot influence a single binding.
    units = tuple(
        sorted(resolve_candidates(raw_units, canon_count), key=lambda unit: unit.document_index)
    )
    divergence = _detect_spine_divergence(units, canon_count)
    poisoned = _poisoned_by_unreadable(units)

    claims: Counter[int] = Counter()
    for unit in units:
        for value in unit.values:
            claims[value] += 1

    bound: dict[int, list[int]] = {}
    carried: list[CarriedUnit] = []

    def carry(unit: TranslationUnit, alignment: Alignment, defect: Defect) -> None:
        carried.append(
            CarriedUnit(
                alignment=alignment,
                defect=defect,
                source_book=book,
                source_verse_label=unit.label_printed,
                text=unit.text,
                source_page_url=page_url,
                snapshot_sha256=snapshot_sha256,
                printed_page=unit.printed_page,
                document_index=unit.document_index,
            )
        )

    for index, unit in enumerate(units):
        if divergence is not None and unit.values and min(unit.values) >= divergence:
            carry(unit, Alignment.UNRESOLVED, Defect.NUMBERING_SPINE_DIVERGENCE)
            continue
        if unit.unreadable is Defect.UNREADABLE_LABEL:
            carry(unit, Alignment.AMBIGUOUS, Defect.UNREADABLE_LABEL)
            continue
        if index in poisoned:
            carry(unit, Alignment.AMBIGUOUS, Defect.ADJACENT_UNREADABLE_LABEL)
            continue
        if not unit.values:
            # The unnumbered head of a book. Griffith omits the "1" under the book
            # heading; the next printed label supplies the address arithmetically.
            if index != 0:
                carry(unit, Alignment.AMBIGUOUS, Defect.UNREADABLE_LABEL)
                continue
            bound[index] = [1] if claims[1] == 0 else []
            if not bound[index]:
                del bound[index]
                carry(unit, Alignment.AMBIGUOUS, Defect.DUPLICATE_LABEL)
            continue
        if any(claims[value] > 1 for value in unit.values):
            carry(unit, Alignment.AMBIGUOUS, Defect.DUPLICATE_LABEL)
            continue
        in_range = [value for value in unit.values if 1 <= value <= canon_count]
        if not in_range:
            carry(unit, Alignment.UNRESOLVED, Defect.LABEL_OUT_OF_RANGE)
            continue
        if len(in_range) != len(unit.values):
            carry(unit, Alignment.AMBIGUOUS, Defect.LABEL_OUT_OF_RANGE)
            continue
        bound[index] = sorted(in_range)

    _infer_spans(units, bound, canon_count=canon_count, divergence=divergence)

    verses: list[AlignedVerse] = []
    covered: set[int] = set()
    for index in sorted(bound):
        values = bound[index]
        unit = units[index]
        alignment = Alignment.EXACT if len(values) == 1 else Alignment.STRUCTURAL_DIVERGENCE
        for mantra in values:
            covered.add(mantra)
            verses.append(
                AlignedVerse(
                    canonical_key=spine.keys[(book, mantra)],
                    adhyaya=book,
                    mantra=mantra,
                    text=unit.text,
                    source_book=book,
                    source_verse_label=unit.label_printed or _implicit_label(values),
                    alignment=alignment,
                    source_page_url=page_url,
                    snapshot_sha256=snapshot_sha256,
                    printed_page=unit.printed_page,
                    label_repair=unit.label_repaired,
                )
            )

    gaps = tuple(
        GapKey(
            canonical_key=spine.keys[(book, mantra)],
            adhyaya=book,
            mantra=mantra,
            defect=_gap_defect(mantra, units, divergence),
        )
        for mantra in range(1, canon_count + 1)
        if mantra not in covered
    )
    return BookAlignment(
        book=book,
        snapshot_sha256=snapshot_sha256,
        unit_count=len(units),
        verses=tuple(verses),
        carried=tuple(carried),
        gaps=gaps,
        spine_divergence_from=divergence,
    )


def _implicit_label(values: Sequence[int]) -> str:
    """Label recorded for the head unit, which the print leaves unnumbered."""
    return "[unnumbered:{}]".format(",".join(str(value) for value in values))


def _infer_spans(
    units: Sequence[TranslationUnit],
    bound: dict[int, list[int]],
    *,
    canon_count: int,
    divergence: int | None,
) -> None:
    """Extend a unit over numbers the print skipped, where the arithmetic proves it.

    Guarded three ways: both document neighbours must have resolved, so a corrupted label
    absorbed nearby cannot be mistaken for a grouping; the unit must not print an omission
    row; and a book with a divergent spine is left alone entirely.
    """
    if divergence is not None:
        return
    resolved = sorted(bound)
    for position, index in enumerate(resolved):
        values = bound[index]
        if len(values) != 1:
            continue
        if index > 0 and (index - 1) not in bound:
            continue
        if units[index].has_omission_row:
            continue
        if position + 1 >= len(resolved):
            # Nothing follows, so nothing bounds the span. A book whose last printed
            # number falls short of the canonical count leaves a gap; it does not license
            # stretching the closing unit over whatever is missing.
            continue
        following = resolved[position + 1]
        if following != index + 1:
            continue
        limit = min(bound[following])
        start = values[0]
        if limit > start + 1:
            bound[index] = list(range(start, min(limit, canon_count + 1)))


def _gap_defect(mantra: int, units: Sequence[TranslationUnit], divergence: int | None) -> Defect:
    """Say why a canonical mantra has no unit, from the print rather than by guess."""
    if divergence is not None and mantra >= divergence:
        return Defect.NUMBERING_SPINE_DIVERGENCE
    preceding = [unit for unit in units if unit.values and max(unit.values) < mantra]
    if preceding:
        nearest = max(preceding, key=lambda unit: max(unit.values))
        if nearest.has_omission_row:
            return Defect.PRINTED_OMISSION
    return Defect.LABEL_NOT_PRINTED


def to_staging_records(
    alignment: BookAlignment, *, snapshot_id: str
) -> list[StagingTranslationRecord]:
    """The aligned verses as repo staging records, for downstream build code."""
    mapping = {
        Alignment.EXACT: TranslationAlignment.EXACT_MANTRA_ALIGNMENT,
        Alignment.STRUCTURAL_DIVERGENCE: TranslationAlignment.RANGE_ALIGNMENT,
    }
    return [
        StagingTranslationRecord(
            source_id=SOURCE_ID,
            source_locator=f"wyvbk{verse.source_book:02d}.htm#{verse.source_verse_label}",
            work_id=WORK_ID,
            hierarchy={"adhyaya": verse.adhyaya, "mantra": verse.mantra},
            text_original=verse.text,
            language="en",
            translator=TRANSLATOR,
            work_edition=WORK_EDITION,
            year=PUBLICATION_YEAR,
            snapshot_id=snapshot_id,
            source_artifact_id=SOURCE_ARTIFACT_ID,
            alignment=mapping.get(verse.alignment, TranslationAlignment.UNCERTAIN_ALIGNMENT),
        )
        for verse in alignment.verses
    ]


@dataclass(frozen=True)
class Snapshot:
    """One pinned page: which book it is, its digest, and where its bytes are."""

    book: int
    sha256: str
    path: Path
    retrieval_url: str


@dataclass
class GriffithYajurvedaAdapter:
    """Read pinned sacred-texts snapshots into a proven VSM alignment.

    Deliberately not a :class:`~vedagraph.ingest.adapters.base.SourceAdapter`: that base
    class's ``parse`` returns ``StagingTextRecord``, which models a Sanskrit text layer and
    carries a ``TextRole`` vocabulary with no term for an English translation. Claiming the
    interface and then returning the wrong record type would be worse than not claiming it.
    """

    source_id: str = SOURCE_ID
    books: tuple[int, ...] = field(default_factory=lambda: tuple(range(1, BOOK_COUNT + 1)))

    def discover(self, scope: str = "all") -> list[DiscoveredResource]:
        if scope not in {"all", "books"}:
            raise ValueError(f"unsupported scope: {scope}")
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=book_url(book),
                locator=f"wyvbk{book:02d}.htm",
                media_type="text/html",
            )
            for book in self.books
        ]

    def load_snapshots(self, snapshot_dir: Path) -> list[Snapshot]:
        """Resolve ``manifest.json`` into the book snapshots, refusing a partial set."""
        manifest_path = snapshot_dir / "manifest.json"
        if not manifest_path.exists():
            raise AdapterError(f"no manifest at {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        by_book: dict[int, Snapshot] = {}
        for row in manifest["pages"]:
            book = row.get("wyv_book")
            if book is None:
                continue
            digest = str(row["sha256"])
            by_book[int(book)] = Snapshot(
                book=int(book),
                sha256=digest,
                path=snapshot_dir / f"{digest}.html",
                retrieval_url=str(row["retrieval_url"]),
            )
        missing = [book for book in self.books if book not in by_book]
        if missing:
            raise AdapterError(f"manifest is missing books {missing}")
        absent = [str(by_book[b].path) for b in self.books if not by_book[b].path.exists()]
        if absent:
            raise AdapterError(f"snapshot bytes absent: {absent}")
        return [by_book[book] for book in self.books]

    def align(self, snapshot_dir: Path, spine: CanonicalSpine) -> list[BookAlignment]:
        results: list[BookAlignment] = []
        for snapshot in self.load_snapshots(snapshot_dir):
            printed_book, lines = extract_lines(snapshot.path.read_bytes())
            if printed_book != snapshot.book:
                raise AdapterError(
                    f"{snapshot.retrieval_url} prints book {printed_book}, "
                    f"manifest says {snapshot.book}"
                )
            units = segment_units(snapshot.book, lines)
            aligned = align_book(
                units, book=snapshot.book, spine=spine, snapshot_sha256=snapshot.sha256
            )
            results.append(replace(aligned, content_sha256=content_digest(printed_book, lines)))
        return results


def build_stage(
    alignments: Sequence[BookAlignment],
    *,
    spine: CanonicalSpine,
    snapshot_id: str,
    canonical_release: str,
) -> dict[str, object]:
    """The staged translation payload.

    Deterministic by construction: every list is sorted by a stable key and no retrieval
    timestamp appears anywhere. Fetch times live in the snapshot sidecars, where a change
    means a genuinely new retrieval rather than a diff in the aligned data.
    """
    verses = sorted(
        (verse.as_json() for alignment in alignments for verse in alignment.verses),
        key=lambda row: str(row["canonical_key"]),
    )
    unresolved = [
        unit.as_json()
        for unit in sorted(
            (unit for alignment in alignments for unit in alignment.carried),
            key=lambda unit: (unit.source_book, unit.document_index),
        )
    ]
    gaps = sorted(
        (gap.as_json() for alignment in alignments for gap in alignment.gaps),
        key=lambda row: str(row["canonical_key"]),
    )
    digests = sorted({alignment.snapshot_sha256 for alignment in alignments})
    books = [
        {
            "adhyaya": alignment.book,
            "content_sha256": alignment.content_sha256,
            "retrieval_url": book_url(alignment.book),
            "snapshot_sha256": alignment.snapshot_sha256,
            "translation_units": alignment.unit_count,
        }
        for alignment in sorted(alignments, key=lambda item: item.book)
    ]
    return {
        "alignment_summary": summarize(alignments, spine),
        "retrieval_context": {
            "base_url": BASE_URL,
            "canonical_release": canonical_release,
            "publication_year": PUBLICATION_YEAR,
            "snapshot_date": snapshot_id,
            "source_edition": WORK_EDITION,
            "translator": TRANSLATOR,
            "user_agent": (
                "VedaGraph/1.0 (research; +https://github.com/HimanshuMohanty-Git24/VedAnvaya)"
            ),
        },
        "books": books,
        "snapshot_ids": digests,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_gaps": gaps,
        "source_id": SOURCE_ID,
        "spine_divergences": [
            {
                "adhyaya": alignment.book,
                "divergent_from_printed_label": alignment.spine_divergence_from,
            }
            for alignment in sorted(alignments, key=lambda item: item.book)
            if alignment.spine_divergence_from is not None
        ],
        "stage_version": STAGE_VERSION,
        "unresolved": unresolved,
        "verses": verses,
        "work_id": WORK_ID,
    }


def summarize(alignments: Iterable[BookAlignment], spine: CanonicalSpine) -> dict[str, int]:
    """The five counts, plus the identity that makes them auditable.

    The universe is every canonical mantra plus every unit that binds to none, so
    ``EXACT + STRUCTURAL_DIVERGENCE + SOURCE_GAP`` is the canonical mantra count and
    adding ``AMBIGUOUS + UNRESOLVED`` gives the total.
    """
    counts: Counter[str] = Counter()
    books = 0
    for alignment in alignments:
        books += 1
        for verse in alignment.verses:
            counts[verse.alignment.value] += 1
        for unit in alignment.carried:
            counts[unit.alignment.value] += 1
        counts[Alignment.SOURCE_GAP.value] += len(alignment.gaps)
        counts["translation_units"] += alignment.unit_count
    canonical = sum(spine.counts[book] for book in sorted(spine.counts))
    summary = {
        "AMBIGUOUS": counts[Alignment.AMBIGUOUS.value],
        "EXACT": counts[Alignment.EXACT.value],
        "SOURCE_GAP": counts[Alignment.SOURCE_GAP.value],
        "STRUCTURAL_DIVERGENCE": counts[Alignment.STRUCTURAL_DIVERGENCE.value],
        "UNRESOLVED": counts[Alignment.UNRESOLVED.value],
        "books": books,
        "canonical_mantra_count": canonical,
        "translation_units": counts["translation_units"],
    }
    summary["english_coverage"] = summary["EXACT"] + summary["STRUCTURAL_DIVERGENCE"]
    summary["total_accounted"] = (
        summary["EXACT"]
        + summary["STRUCTURAL_DIVERGENCE"]
        + summary["SOURCE_GAP"]
        + summary["AMBIGUOUS"]
        + summary["UNRESOLVED"]
    )
    return summary
