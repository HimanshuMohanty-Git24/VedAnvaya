"""Sanskrit Wikisource Kauthuma Samaveda arcika adapter.

This is the SELECTED canonical witness for the Samaveda samhita. The GRETIL artifact is
rights-encumbered and is used only for structural comparison, never as a text source.

Segmentation is derived from source evidence, never from sequence position
=========================================================================

Three facts about this corpus drive the whole design.

**1. The page tree addresses each collection in its own shape.** The dotted number in a
page title is NOT a uniform five-slot coordinate. Slot 3 means *prapathaka* under
``1.1.x``, *dasati* under ``1.2.x`` and *ardha* under ``2.x.y`` -- three meanings in one
witness. A parser that reads the dotted address positionally therefore mis-keys. This
module reads it against the shape declared by the collection segment of the title, and
refuses a page whose address does not match that shape.

**2. The verse number printed in the body is the RUNNING number of the whole samhita
(1..1875), not a dasati-local index.** Page ``1.1.1.5`` prints 45..54, not 1..10. The
local verse index is therefore not printed on most pages and must be *derived*. It is
derived from the source's own printed arithmetic -- rank within the dasati's contiguous
ascending run of running numbers -- and the derivation FAILS CLOSED when that run is not
contiguous.

The verse index is therefore order-free: it is arithmetic over printed numbers, sorted by
value, so permuting verse blocks cannot change it. The DASATI of an Uttararcika verse is
NOT order-free, and this docstring previously overstated the case by saying HTML order is
never consulted. It is: a verse's dasati is the nearest preceding printed dasati numeral
in DOCUMENT ORDER, because that is how the source declares it. Moving a verse block across
a heading moves its dasati. That is a property of the source's layout, not a choice this
parser makes, and no alternative exists short of the source numbering each verse -- but it
is a real dependency and is recorded as one.

**3. The pages carry gana (song) material interleaved with the arcika text, and gana is a
different work.** The gana sections are written in the Samaveda svara notation using the
Devanagari Extended combining marks (U+A8E0..U+A8F1) and carry their own numbering. Those
sections are excluded by detecting the notation, not by position.

Five marker dialects occur, all accepted, and which one matched is recorded because it is
a property of the source rather than of this parser::

    DOUBLE_DANDA   ...barhisi ॥ 1 ॥        U+0965 on both sides
    TWO_DANDA      ...barhisi ।। 1 ।।      two U+0964 on both sides
    ASCII_PIPES    ...barhisi || 1 ||      two ASCII pipes, used by the table dialect
    UNTERMINATED   ...barhisi ॥ 1          opening separator only, at end of line
    SINGLE_DANDA   ...barhisi । 1133 ॥     single open, double close

A single-notation reader is not merely incomplete here: the superseded double-danda-only
regex lifts 1,195 of the 1,875 printed markers, leaves 22 pages yielding zero verses, and
reports nothing wrong.

Nothing here repairs the source. Every unit the source spells inconsistently is emitted as
a defect so that a referent audit against the source's own numbering stays possible.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from vedagraph.identity import SamavedaCollection, sv_mantra_identity
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents

PARSER_VERSION = "wikisource-sa-samaveda-arcika-v2"
SEGMENTATION_POLICY_VERSION = "sv-referent-segmentation-v1"

SOURCE_ID = "WIKISOURCE_SA"

API_TEMPLATE = (
    "https://sa.wikisource.org/w/api.php?action=parse&page={page}"
    "&prop=wikitext%7Crevid&formatversion=2&format=json"
)

# ---------------------------------------------------------------------------
# Source vocabulary, as the page tree spells it.
# ---------------------------------------------------------------------------

PURVARCIKA = "पूर्वार्चिकः"
UTTARARCIKA = "उत्तरार्चिकः"

# Title segment -> collection. The Purvarcika sub-collection segments are matched first
# because they are nested inside the Purvarcika segment.
COLLECTION_BY_SEGMENT: tuple[tuple[str, SamavedaCollection], ...] = (
    ("छन्द आर्चिकः", SamavedaCollection.CHANDA),
    ("अथारण्यार्चिकः", SamavedaCollection.ARANYA),
    ("आरण्यार्चिकः", SamavedaCollection.ARANYA),
    ("महानाम्न्यार्चिकः", SamavedaCollection.MAHANAMNYA),
)

# The declared shape of the dotted address in a leaf page title, per collection. A page
# whose address has a different arity is refused rather than read positionally.
#
#   CHANDA      1.1.{prapathaka}.{dasati}
#   ARANYA      1.2.{dasati}
#   MAHANAMNYA  (no dotted address; the collection page itself carries the verses)
#   UTTARA      2.{prapathaka}.{ardha}          dasati is printed inside the page
ADDRESS_ARITY: dict[SamavedaCollection, int] = {
    SamavedaCollection.CHANDA: 4,
    SamavedaCollection.ARANYA: 3,
    SamavedaCollection.UTTARA: 3,
}

# ---------------------------------------------------------------------------
# Source syntax classes.
# ---------------------------------------------------------------------------

# Verse-terminal separators. A DOUBLE form closes a verse; a SINGLE form is the ordinary
# pada separator, and the source sometimes types one where a double belongs.
_SEP2 = r"(?:॥|।।|\|\|)"
_SEP1 = r"(?:।|\|)"
_SEP_ANY = f"(?:{_SEP2}|{_SEP1})"
_DIGITS = r"[\d०-९]+"  # noqa: RUF001 - Devanagari digit range, not Latin letters

# A terminated marker. At least ONE side must be a double separator: requiring that is
# what keeps "। 5 ।" inside ordinary prose from being read as a verse boundary, while
# still lifting the source's mixed spellings such as "। 1133 ॥".
_MARKER_TERMINATED = re.compile(
    f"({_SEP2})\\s*({_DIGITS})\\s*({_SEP_ANY})|({_SEP1})\\s*({_DIGITS})\\s*({_SEP2})"
)
# An unterminated marker: double separator, number, then end of line. Only ever applied to
# the tail of a line, so it cannot swallow a mid-line cross reference.
_MARKER_UNTERMINATED = re.compile(f"({_SEP2})\\s*({_DIGITS})\\s*$")
# A marker whose OPENING separator is missing altogether: text, whitespace, number, closing
# double separator, end of line -- "...carsaninam 713 ॥".
#
# This dialect was missed on the first pass and cost the freeze. Its one occurrence in the
# corpus, running number 713, was read as an ordinary pada line and WELDED onto verse 714,
# so VG:SV:KAU:UTTARA:P01:R02:D01:V01 denoted two printed verse units while every gate
# reported it clean. It is matched only at end of line, only with a DOUBLE closing
# separator, and only when the digits are preceded by whitespace rather than by a letter or
# another digit -- which is what keeps GRETIL-style in-word numeric svarita ("gathanya3m")
# and Rigveda cross-references out.
_MARKER_NO_OPENER = re.compile(f"(?:^|\\s)({_DIGITS})\\s*{_SEP2}\\s*$")

# Samaveda gana svara notation. These combining marks are what makes a line gana rather
# than arcika; the Devanagari Extended block is the Samaveda-specific notation and is NOT
# covered by normalize.VEDIC_ACCENT_CODEPOINTS.
GANA_SVARA_MARKS = frozenset(chr(cp) for cp in range(0xA8E0, 0xA8F2))

# A line whose only content is a number is a dasati heading inside an Uttararcika ardha
# page. The source writes it three ways -- bare, parenthesised and bracketed -- and page
# 2.4.2 uses the parenthesised form throughout, so a bare-numeral-only rule reads that
# whole ardha as having no dasati structure at all.
_BARE_NUMBER_LINE = re.compile(f"^[(\\[]?\\s*({_DIGITS})\\s*[)\\]]?[.।]?$")
# The leading dotted address of a leaf page title, e.g. "1.1.1.5 pancami dasatih".
_TITLE_ADDRESS = re.compile(r"^([\d]+(?:\.[\d]+)*)\s")
# A source-declared local verse index plus pada label, as the table dialect prints it in
# its second cell: "1a", "1c".
_PADA_LABEL = re.compile(f"({_DIGITS})\\s*([^\\s\\d०-९]{{1,3}})")  # noqa: RUF001
# A line that is NOTHING BUT a pada label, e.g. "1a" or "1c". In the table dialect the
# label lives in a second cell, so once the cell tags are stripped it lands on its own
# line. It is apparatus and must not be collected as a pada: doing so prepends the previous
# row's label to the next verse's text.
_PADA_LABEL_ONLY = re.compile(f"^({_DIGITS})\\s*([^\\s\\d०-९]{{1,3}})$")  # noqa: RUF001

_REF = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.DOTALL | re.IGNORECASE)
_FILE_LINK = re.compile(r"\[\[(?:File|Image|चित्रम्|सञ्चिका):[^\]]*\]\]", re.IGNORECASE)
_EXTERNAL_LINK = re.compile(r"\[(?:https?:)?//\S+?(?:\s+[^\]]*)?\]")
_WIKI_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_HEADING = re.compile(r"^=+.*?=+$", re.MULTILINE)
_BREAK = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
# Table tags are in this list, and their omission was a real defect: on the two
# table-dialect pages the body path left raw <tr>/<td>/</tr> inside 20 released verses and
# leaked the PREVIOUS row's pada label into 18 of them. _TABLE_TAG and the row/cell
# splitters below exist only for _table_rows(), which reads the declared local index, and
# were never applied to the body.
_TAG = re.compile(
    r"</?(?:poem|span|div|small|big|center|references|table|tbody|thead|tr|td|th|p|b|i|u)"
    r"\b[^>]*/?>",
    re.IGNORECASE,
)
_TABLE_TAG = re.compile(r"</?(?:table|tbody|thead)\b[^>]*>", re.IGNORECASE)
_ROW_SPLIT = re.compile(r"<\s*tr\b[^>]*>", re.IGNORECASE)
_CELL_SPLIT = re.compile(r"<\s*td\b[^>]*>", re.IGNORECASE)
_ROW_END = re.compile(r"</\s*tr\s*>", re.IGNORECASE)

# Devanagari letters. Used to tell a text line from an apparatus line.
_DEVANAGARI_LETTER = re.compile(r"[ऀ-ॐक़-॥॰-ॿ]")


class MarkerDialect(StrEnum):
    DOUBLE_DANDA = "DOUBLE_DANDA"
    TWO_DANDA = "TWO_DANDA"
    ASCII_PIPES = "ASCII_PIPES"
    UNTERMINATED = "UNTERMINATED"
    # A single danda opening a marker that a double danda closes. The source types this
    # where a double belongs; the rejected GRETIL artifact has the same defect at the same
    # running number, so it is a property of the shared print antecedent, not of one wiki.
    SINGLE_DANDA = "SINGLE_DANDA"
    # No opening separator at all: "...carsaninam 713 ॥". One occurrence, and missing it
    # welded two printed verses onto one key.
    NO_OPENING_SEPARATOR = "NO_OPENING_SEPARATOR"


class PageKind(StrEnum):
    INDEX = "INDEX"
    CHANDA_DASATI = "CHANDA_DASATI"
    ARANYA_DASATI = "ARANYA_DASATI"
    MAHANAMNYA = "MAHANAMNYA"
    UTTARA_ARDHA = "UTTARA_ARDHA"


class ReferentClass(StrEnum):
    """How one candidate verse occurrence relates to its source verse unit."""

    ONE_TO_ONE = "ONE_TO_ONE"
    MERGED_MULTIPLE_VERSES = "MERGED_MULTIPLE_VERSES"
    SPLIT_SINGLE_VERSE = "SPLIT_SINGLE_VERSE"
    MARKERLESS_VERSE = "MARKERLESS_VERSE"
    DUPLICATED_MARKER = "DUPLICATED_MARKER"
    SOURCE_NUMBERING_ANOMALY = "SOURCE_NUMBERING_ANOMALY"
    STRUCTURAL_COLLISION = "STRUCTURAL_COLLISION"
    UNRESOLVED_REFERENT = "UNRESOLVED_REFERENT"


_SEP_DIALECT: dict[str, MarkerDialect] = {
    "॥": MarkerDialect.DOUBLE_DANDA,
    "।।": MarkerDialect.TWO_DANDA,
    "||": MarkerDialect.ASCII_PIPES,
}


def _devanagari_int(text: str) -> int:
    return int("".join(str(unicodedata.decimal(c)) if not c.isascii() else c for c in text))


def is_gana_line(text: str) -> bool:
    """True when a line carries the Samaveda gana svara notation.

    Gana is a separate work with its own numbering. Detecting it by notation rather than
    by position is what keeps a gana verse number out of the arcika running series.
    """
    return any(char in GANA_SVARA_MARKS for char in text)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SamavedaPageAddress:
    """The structural address a page title declares, read against its collection shape."""

    collection: SamavedaCollection
    kind: PageKind
    prapathaka: int | None = None
    ardha: int | None = None
    dasati: int | None = None
    declared_address: str | None = None


@dataclass(frozen=True)
class SamavedaDefect:
    """Something the source spells inconsistently, recorded rather than normalized."""

    defect_code: str
    page_title: str
    detail: str
    running_number: int | None = None
    raw_line: str | None = None


@dataclass
class VerseOccurrence:
    """One verse the source actually delimits, before any identity is minted."""

    page_title: str
    revision_id: int
    snapshot_sha256: str
    collection: SamavedaCollection
    prapathaka: int | None
    ardha: int | None
    dasati: int | None
    running_number: int | None
    marker_dialect: MarkerDialect | None
    text: str
    pada_count: int
    source_line_span: tuple[int, int]
    declared_local_index: int | None = None
    declared_pada_labels: list[str] = field(default_factory=list)
    # Filled in by the dasati-level resolution pass.
    local_index: int | None = None
    referent_class: ReferentClass = ReferentClass.ONE_TO_ONE
    notes: list[str] = field(default_factory=list)

    @property
    def source_locator(self) -> str:
        parts = [self.collection.value]
        for label, value in (
            ("P", self.prapathaka),
            ("R", self.ardha),
            ("D", self.dasati),
        ):
            if value is not None:
                parts.append(f"{label}{value}")
        rn = "?" if self.running_number is None else str(self.running_number)
        return f"WS {'.'.join(parts)} RN{rn}"


@dataclass(frozen=True)
class SamavedaPageParse:
    page_title: str
    revision_id: int
    snapshot_sha256: str
    address: SamavedaPageAddress
    occurrences: list[VerseOccurrence]
    defects: list[SamavedaDefect]
    gana_lines: int
    apparatus_lines: int
    dialects: dict[str, int]


# ---------------------------------------------------------------------------
# Title parsing
# ---------------------------------------------------------------------------


def _purvarcika_collection(segments: list[str]) -> SamavedaCollection | None:
    """Which Purvarcika sub-collection a title names, if any."""
    for segment in segments:
        for needle, candidate in COLLECTION_BY_SEGMENT:
            if segment.strip() == needle:
                return candidate
    return None


def classify_page(title: str) -> SamavedaPageAddress | None:
    """Read the structural address a page title declares, per-collection.

    Returns ``None`` for a title outside the arcika samhita (gana, brahmana, other work).
    The dotted address is validated against the arity the collection declares, so slot 3
    is never read positionally across collections.
    """
    if "/संहिता/" not in title:
        return None
    tail = title.split("/संहिता/", 1)[1]
    segments = tail.split("/")

    collection: SamavedaCollection
    if segments[0] == UTTARARCIKA:
        collection = SamavedaCollection.UTTARA
    elif segments[0] == PURVARCIKA:
        found = _purvarcika_collection(segments[1:])
        if found is None:
            # The Purvarcika index page itself, which names no sub-collection.
            return SamavedaPageAddress(collection=SamavedaCollection.CHANDA, kind=PageKind.INDEX)
        collection = found
    else:
        return None

    leaf = segments[-1].strip()
    match = _TITLE_ADDRESS.match(leaf)

    if collection is SamavedaCollection.MAHANAMNYA:
        # The Mahanamnyarcika has no dotted address and no sub-pages: the collection page
        # itself carries all ten verses.
        return SamavedaPageAddress(
            collection=collection, kind=PageKind.MAHANAMNYA, declared_address=None
        )

    if match is None:
        return SamavedaPageAddress(collection=collection, kind=PageKind.INDEX)

    declared = match.group(1)
    parts = [int(value) for value in declared.split(".")]
    if len(parts) != ADDRESS_ARITY[collection]:
        # An index page one level up (e.g. "1.1.1 prathamaprapathakah" or "2.6
        # sasthaprapathakah") legitimately carries a shorter address.
        return SamavedaPageAddress(
            collection=collection, kind=PageKind.INDEX, declared_address=declared
        )

    if collection is SamavedaCollection.CHANDA:
        # 1.1.{prapathaka}.{dasati}
        return SamavedaPageAddress(
            collection=collection,
            kind=PageKind.CHANDA_DASATI,
            prapathaka=parts[2],
            dasati=parts[3],
            declared_address=declared,
        )
    if collection is SamavedaCollection.ARANYA:
        # 1.2.{dasati} -- no prapathaka level exists in this collection.
        return SamavedaPageAddress(
            collection=collection,
            kind=PageKind.ARANYA_DASATI,
            dasati=parts[2],
            declared_address=declared,
        )
    # 2.{prapathaka}.{ardha} -- dasati is printed inside the page body.
    return SamavedaPageAddress(
        collection=collection,
        kind=PageKind.UTTARA_ARDHA,
        prapathaka=parts[1],
        ardha=parts[2],
        declared_address=declared,
    )


# ---------------------------------------------------------------------------
# Body cleaning
# ---------------------------------------------------------------------------


def _strip_templates(text: str) -> str:
    """Remove ``{{...}}`` including nested braces, without a recursive regex."""
    output: list[str] = []
    depth = 0
    index = 0
    while index < len(text):
        if text.startswith("{{", index):
            depth += 1
            index += 2
            continue
        if text.startswith("}}", index) and depth:
            depth -= 1
            index += 2
            continue
        if depth == 0:
            output.append(text[index])
        elif text[index] == "\n":
            # Keep line structure so a template cannot silently weld two verses together.
            output.append("\n")
        index += 1
    return "".join(output)


def clean_wikitext(wikitext: str) -> str:
    """Reduce wikitext to text lines, preserving line structure.

    Reference notes, templates, file links and external links are apparatus and are
    removed outright. ``<br>`` becomes a newline so a pada boundary the source draws with
    a break tag stays a line boundary.
    """
    text = _REF.sub(" ", wikitext)
    text = _strip_templates(text)
    text = _FILE_LINK.sub(" ", text)
    text = _BREAK.sub("\n", text)
    text = _TAG.sub(" ", text)
    text = _EXTERNAL_LINK.sub(" ", text)
    text = _WIKI_LINK.sub(r"\1", text)
    return _HEADING.sub(" ", text)


def _find_markers(line: str) -> list[tuple[int, int, int, MarkerDialect]]:
    """Every verse-terminal marker on one line as ``(start, end, value, dialect)``."""
    found: list[tuple[int, int, int, MarkerDialect]] = []
    for match in _MARKER_TERMINATED.finditer(line):
        opening, digits = (
            (match.group(1), match.group(2))
            if match.group(2) is not None
            else (match.group(4), match.group(5))
        )
        dialect = _SEP_DIALECT.get(opening or "", MarkerDialect.SINGLE_DANDA)
        found.append((match.start(), match.end(), _devanagari_int(digits), dialect))
    if found:
        return found
    tail = _MARKER_UNTERMINATED.search(line)
    if tail is not None:
        found.append(
            (tail.start(), tail.end(), _devanagari_int(tail.group(2)), MarkerDialect.UNTERMINATED)
        )
        return found
    bare = _MARKER_NO_OPENER.search(line)
    if bare is not None:
        found.append(
            (
                bare.start(1),
                bare.end(),
                _devanagari_int(bare.group(1)),
                MarkerDialect.NO_OPENING_SEPARATOR,
            )
        )
    return found


def _is_text_line(line: str) -> bool:
    return bool(_DEVANAGARI_LETTER.search(line))


# ---------------------------------------------------------------------------
# The adapter
# ---------------------------------------------------------------------------


class SamavedaWikisourceAdapter(SourceAdapter):
    """Parse one Sanskrit Wikisource Samaveda arcika page into verse occurrences."""

    source_id = SOURCE_ID

    def __init__(
        self,
        *,
        source_artifact_id: str = "WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI",
        text_version_id: str = "WIKISOURCE_SA.SV.KAU.ARCIKA_MULA",
    ) -> None:
        self.source_artifact_id = source_artifact_id
        self.text_version_id = text_version_id

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        """``scope`` is a full Wikisource page title."""
        from urllib.parse import quote

        if not scope:
            return []
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=API_TEMPLATE.format(page=quote(scope, safe="")),
                locator=scope,
                media_type="application/json",
            )
        ]

    # -- page reading -------------------------------------------------------

    def parse_page(self, snapshot_path: Path, *, snapshot_sha256: str = "") -> SamavedaPageParse:
        """Segment one arcika page using only source evidence.

        The address comes from the page title, the dasati from the title or from the
        numeral the page prints, and the verse boundary from the printed marker. Sequence
        position is never used to address anything.
        """
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        parse = payload.get("parse")
        if parse is None:
            raise ValueError(f"snapshot carries no parse payload: {snapshot_path}")
        title = parse["title"]
        revision_id = int(parse["revid"])
        sha = snapshot_sha256 or snapshot_path.stem

        address = classify_page(title)
        if address is None:
            raise ValueError(f"page is not part of the Samaveda arcika samhita: {title}")

        occurrences: list[VerseOccurrence] = []
        defects: list[SamavedaDefect] = []
        dialects: dict[str, int] = {}
        gana_lines = 0
        apparatus_lines = 0

        if address.kind is PageKind.INDEX:
            return SamavedaPageParse(
                page_title=title,
                revision_id=revision_id,
                snapshot_sha256=sha,
                address=address,
                occurrences=[],
                defects=[],
                gana_lines=0,
                apparatus_lines=0,
                dialects={},
            )

        raw = parse.get("wikitext", "")
        table_rows = self._table_rows(raw)
        body = clean_wikitext(raw)

        current_dasati = address.dasati
        pending: list[str] = []
        pending_start = 0

        for index, physical in enumerate(body.split("\n")):
            line = " ".join(physical.split())
            if not line:
                continue
            if is_gana_line(line):
                # A gana line closes any partially collected arcika verse: the arcika
                # text and the gana text of one unit are never continuous.
                gana_lines += 1
                pending = []
                continue
            heading = _BARE_NUMBER_LINE.match(line)
            if heading is not None:
                if address.kind is PageKind.UTTARA_ARDHA:
                    current_dasati = _devanagari_int(heading.group(1))
                    pending = []
                    continue
                # A bare numeral outside an Uttararcika ardha page is not a dasati
                # heading; the source does not define one there.
                defects.append(
                    SamavedaDefect(
                        defect_code="UNEXPECTED_BARE_NUMBER_LINE",
                        page_title=title,
                        detail=(
                            "a line containing only a numeral appeared outside an "
                            "Uttararcika ardha page, where the source declares no "
                            "dasati heading; it is not read as structure"
                        ),
                        raw_line=line,
                    )
                )
                continue

            markers = _find_markers(line)
            if not markers:
                if _PADA_LABEL_ONLY.match(line):
                    # A bare pada label from the table dialect's second cell.
                    apparatus_lines += 1
                elif _is_text_line(line):
                    pending.append(line)
                    if len(pending) == 1:
                        pending_start = index
                else:
                    apparatus_lines += 1
                continue

            cursor = 0
            for start, end, value, dialect in markers:
                head = " ".join(line[cursor:start].split())
                cursor = end
                parts = [*pending, head] if head else list(pending)
                text = " ".join(" ".join(parts).split())
                span_start = pending_start if pending else index
                declared_index, pada_labels = self._declared_label(table_rows, value)
                if not text:
                    # A verse-terminal marker with no text before it does not delimit a
                    # verse. This is how a gana-section or apparatus number that survived
                    # the notation filter is refused: minting a verse for it would put a
                    # spurious occurrence into the dasati and break the local-index
                    # arithmetic for every real verse after it.
                    defects.append(
                        SamavedaDefect(
                            defect_code="MARKER_WITHOUT_TEXT",
                            page_title=title,
                            detail=(
                                "a verse-terminal marker carries no preceding text, so it "
                                "delimits no verse and is not read as one"
                            ),
                            running_number=value,
                            raw_line=line,
                        )
                    )
                    continue
                dialects[dialect.value] = dialects.get(dialect.value, 0) + 1
                occurrences.append(
                    VerseOccurrence(
                        page_title=title,
                        revision_id=revision_id,
                        snapshot_sha256=sha,
                        collection=address.collection,
                        prapathaka=address.prapathaka,
                        ardha=address.ardha,
                        dasati=current_dasati,
                        running_number=value,
                        marker_dialect=dialect,
                        text=text,
                        pada_count=len(parts),
                        source_line_span=(span_start, index),
                        declared_local_index=declared_index,
                        declared_pada_labels=pada_labels,
                    )
                )
                pending = []
            trailing = " ".join(line[cursor:].split())
            if trailing:
                # Everything after a verse's terminal marker on the same line is
                # apparatus: a Rigveda concordance, a gana name, a pada label.
                apparatus_lines += 1

        if pending:
            defects.append(
                SamavedaDefect(
                    defect_code="TEXT_WITHOUT_MARKER",
                    page_title=title,
                    detail=(
                        f"{len(pending)} text line(s) at the end of the page carry no "
                        "verse-terminal marker, so no verse boundary is declared for them"
                    ),
                    raw_line=" / ".join(pending)[:300],
                )
            )

        return SamavedaPageParse(
            page_title=title,
            revision_id=revision_id,
            snapshot_sha256=sha,
            address=address,
            occurrences=occurrences,
            defects=defects,
            gana_lines=gana_lines,
            apparatus_lines=apparatus_lines,
            dialects=dialects,
        )

    def _table_rows(self, wikitext: str) -> dict[int, tuple[int | None, list[str]]]:
        """Source-declared local verse index and pada labels, from the table dialect.

        A minority of pages are typeset as an HTML table whose second cell prints the
        local verse index and the pada label for each row ("1a", "1c"). That is the one
        place in this corpus where the local index is printed rather than derived, so it
        is lifted and used to CHECK the derivation.
        """
        if "<tr" not in wikitext.lower():
            return {}
        declared: dict[int, tuple[int | None, list[str]]] = {}
        for row in _ROW_SPLIT.split(_TABLE_TAG.sub(" ", wikitext))[1:]:
            row = _ROW_END.split(row)[0]
            cells = _CELL_SPLIT.split(row)[1:]
            if len(cells) < 2:
                continue
            text_cell = clean_wikitext(cells[0])
            label_cell = clean_wikitext(" ".join(cells[1:]))
            markers = _find_markers(" ".join(text_cell.split()))
            if not markers:
                continue
            running = markers[-1][2]
            labels = _PADA_LABEL.findall(" ".join(label_cell.split()))
            if not labels:
                continue
            indices = {_devanagari_int(value) for value, _ in labels}
            local = indices.pop() if len(indices) == 1 else None
            declared[running] = (local, [label for _, label in labels])
        return declared

    def _declared_label(
        self, table_rows: dict[int, tuple[int | None, list[str]]], running: int
    ) -> tuple[int | None, list[str]]:
        return table_rows.get(running, (None, []))

    # -- staging records ----------------------------------------------------

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        """Staging records for one arcika page, addressed entirely from source evidence.

        Unlike the superseded ``parse_at_address``, this needs no caller-supplied
        coordinates: the page title declares the collection and the container address, and
        the body declares the dasati and the verse boundaries. The previous signature took
        an ``(arcika, prapathaka, ardha, dasati)`` tuple from the caller and wrote the
        source's RUNNING number straight into the identity-bearing verse slot, which
        minted keys for verses that do not exist. Deriving the address here is what makes
        that class of defect unrepresentable.
        """
        page = self.parse_page(snapshot_path)
        resolve_local_indices([page])
        records: list[StagingTextRecord] = []
        for occurrence in page.occurrences:
            if occurrence.local_index is None or not occurrence.text:
                continue
            # A level this collection does not declare is OMITTED, never written as 0.
            hierarchy: dict[str, int | str] = {"collection": occurrence.collection.value}
            for level, value in (
                ("prapathaka", occurrence.prapathaka),
                ("ardha", occurrence.ardha),
                ("dasati", occurrence.dasati),
            ):
                if value is not None:
                    hierarchy[level] = value
            hierarchy["verse"] = occurrence.local_index
            records.append(
                StagingTextRecord(
                    source_id=self.source_id,
                    source_artifact_id=self.source_artifact_id,
                    source_locator=occurrence.source_locator,
                    work_id="VG:WORK:SV:KAU",
                    hierarchy=hierarchy,
                    text_original=occurrence.text,
                    language="sa",
                    script="Devanagari",
                    accented=has_vedic_accents(occurrence.text),
                    text_version_id=self.text_version_id,
                    text_role=TextRole.PRIMARY_TEXT,
                    snapshot_id=snapshot_id,
                )
            )
        return records


# ---------------------------------------------------------------------------
# Dasati-level resolution: derive the local verse index from printed arithmetic
# ---------------------------------------------------------------------------


def dasati_key(
    occurrence: VerseOccurrence,
) -> tuple[str, int, int, int]:
    return (
        occurrence.collection.value,
        occurrence.prapathaka or 0,
        occurrence.ardha or 0,
        occurrence.dasati or 0,
    )


def resolve_local_indices(pages: list[SamavedaPageParse]) -> list[SamavedaDefect]:
    """Derive each verse's dasati-local index from the source's printed numbering.

    The rule, and the reason it is not positional identity: within one dasati the source
    prints a contiguous ascending run of running numbers. The local index of a verse is
    therefore ``running - first_running_of_the_dasati + 1`` -- an arithmetic fact about
    numbers the source prints, not the verse's position in the HTML. Reordering the page
    cannot change any local index.

    When the run is NOT contiguous the arithmetic does not close, so the derivation is
    refused for that dasati and every occurrence in it is classified
    ``UNRESOLVED_REFERENT``. Failing closed here is the whole point: a positional
    fallback would silently renumber every verse after the break.

    Where the source prints the local index itself (the table dialect), the printed value
    wins and a disagreement with the derived value is recorded as a defect.
    """
    defects: list[SamavedaDefect] = []
    groups: dict[tuple[str, int, int, int], list[VerseOccurrence]] = {}
    for page in pages:
        for occurrence in page.occurrences:
            groups.setdefault(dasati_key(occurrence), []).append(occurrence)

    for key, members in groups.items():
        numbered = [item for item in members if item.running_number is not None]
        unnumbered = [item for item in members if item.running_number is None]
        for item in unnumbered:
            item.referent_class = ReferentClass.MARKERLESS_VERSE
            item.notes.append("no printed running number, so no local index is derivable")

        if not numbered:
            continue

        running_values = [item.running_number for item in numbered]
        counts: dict[int, int] = {}
        for value in running_values:
            assert value is not None
            counts[value] = counts.get(value, 0) + 1
        duplicated = sorted(value for value, count in counts.items() if count > 1)

        ordered = sorted(numbered, key=lambda item: item.running_number or 0)
        first = ordered[0].running_number
        assert first is not None
        expected = list(range(first, first + len(ordered)))
        actual = [item.running_number for item in ordered]
        contiguous = actual == expected

        if duplicated:
            for item in numbered:
                if item.running_number in duplicated:
                    item.referent_class = ReferentClass.DUPLICATED_MARKER
                    item.notes.append(
                        f"running number {item.running_number} is printed more than once "
                        "in this dasati"
                    )
            defects.append(
                SamavedaDefect(
                    defect_code="DUPLICATED_RUNNING_NUMBER",
                    page_title=members[0].page_title,
                    detail=(
                        f"dasati {key} prints running number(s) {duplicated} more than "
                        "once; the local index arithmetic cannot close"
                    ),
                )
            )

        if not contiguous:
            gaps = sorted(set(expected) - set(v for v in actual if v is not None))
            defects.append(
                SamavedaDefect(
                    defect_code="NON_CONTIGUOUS_RUNNING_RUN",
                    page_title=members[0].page_title,
                    detail=(
                        f"dasati {key} prints running numbers {actual[0]}..{actual[-1]} "
                        f"with {len(ordered)} verses, which is not a contiguous run; "
                        f"unaccounted slots {gaps[:12]}"
                    ),
                )
            )

        for position, item in enumerate(ordered, start=1):
            derived = (item.running_number or 0) - first + 1
            if contiguous and not duplicated:
                item.local_index = derived
                if item.declared_local_index is not None:
                    if item.declared_local_index != derived:
                        item.referent_class = ReferentClass.SOURCE_NUMBERING_ANOMALY
                        item.notes.append(
                            "source-declared local index "
                            f"{item.declared_local_index} disagrees with the index "
                            f"{derived} derived from the printed running run"
                        )
                        defects.append(
                            SamavedaDefect(
                                defect_code="DECLARED_INDEX_DISAGREES_WITH_DERIVED",
                                page_title=item.page_title,
                                detail=(
                                    f"printed local index {item.declared_local_index} vs "
                                    f"derived {derived}"
                                ),
                                running_number=item.running_number,
                            )
                        )
                        item.local_index = item.declared_local_index
                continue
            # The run does not close. Prefer a printed index if the source gives one;
            # otherwise refuse rather than fall back on position.
            if item.declared_local_index is not None:
                item.local_index = item.declared_local_index
                item.referent_class = ReferentClass.SOURCE_NUMBERING_ANOMALY
                item.notes.append(
                    "local index taken from the printed label because the dasati's "
                    "running run is not contiguous"
                )
            else:
                item.local_index = None
                item.referent_class = ReferentClass.UNRESOLVED_REFERENT
                item.notes.append(
                    "the dasati's printed running run is not contiguous, so the local "
                    f"index is not derivable (position in run was {position})"
                )

    return defects


def mint_identity(occurrence: VerseOccurrence) -> tuple[str, str, str] | None:
    """Canonical key, URN and UUID for a resolved occurrence, or ``None`` if refused."""
    if occurrence.local_index is None:
        return None
    key, urn, uuid = sv_mantra_identity(
        occurrence.collection,
        prapathaka=occurrence.prapathaka,
        ardha=occurrence.ardha,
        dasati=occurrence.dasati,
        verse=occurrence.local_index,
    )
    return key, urn, str(uuid)
