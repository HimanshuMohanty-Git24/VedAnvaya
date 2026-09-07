"""GRETIL Kauthuma Samaveda adapter.

The GRETIL Samavedasamhita file is *not* structurally marked up: its TEI body contains
only ``p`` elements, with no ``div``, ``lg``, ``l`` or ``xml:id``.  Structure lives
entirely in the leading reference label of each physical line, in the notation the file
declares for itself in its first body paragraph::

    REFERENCE SYSTEM:
    arcika | prapathaka | ardha | dasati | verse | line
    1 1 1 01 01 a

Two consequences drive this parser.

First, the label is written in two different notations, and both occur inside the
Uttararcika: ``4 1 1 01 01a`` (dasati and verse space separated) and ``1 1 1 0101a``
(the two concatenated into four digits).  Both are accepted; which one matched is
recorded, because it is a property of the source, not of us.

Second, the depth is genuinely not uniform.  The Aranya and Mahanamnya arcikas have no
prapathaka and no ardha, and the file encodes that absence as a literal ``0``.  Zero is
therefore a meaningful value here and is never treated as an error.

Nothing in this module repairs the source.  Lines that do not parse, and verses whose
line labels collide, are emitted as :class:`SamavedaParseDefect` records so that a
reconciliation against the source's own verse count remains possible.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from vedagraph.identity import sv_mantra_identity
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents

PARSER_VERSION = "gretil-samaveda-arcika-v1"
TEI_NS = "http://www.tei-c.org/ns/1.0"
TEI = f"{{{TEI_NS}}}"

SNAPSHOT_URL = "https://gretil.sub.uni-goettingen.de/gretil/corpustei/sa_sAmavedasaMhitA.xml"

# Level names as the source itself names them, aligned to Passage.structural_path.
# ``line`` is absent on purpose: it is a sub-mantra pada label, not an identity level.
NATIVE_LABELS: tuple[str, ...] = ("Arcika", "Prapathaka", "Ardha", "Dasati", "Verse")

# The four arcikas, in the order the file presents them.  Index 3 (Mahanamnya) carries
# verses despite having no prapathaka, ardha or dasati.
ARCIKA_NAMES: dict[int, str] = {
    1: "purvarcika",
    2: "aranya-arcika",
    3: "mahanamnya-arcika",
    4: "uttararcika",
}

# ``4 1 1 01 01a text`` - dasati and verse separated by a space.
_LABEL_SPACED = re.compile(r"^(\d+) (\d+) (\d+) (\d{2}) (\d{2})([a-z]) (.*)$")
# ``1 1 1 0101a text`` - dasati and verse concatenated into four digits.
_LABEL_CONCAT = re.compile(r"^(\d+) (\d+) (\d+) (\d{2})(\d{2})([a-z]) (.*)$")
# The source prints a running verse number after the closing danda of a verse's last
# line.  It is edition apparatus, not text, and is lifted out into a citation.
_RUNNING_NUMBER = re.compile(r"\s*\.\.\s*(\d+)\s*$")
# A line that clearly meant to carry a reference label but is malformed.  The second
# pattern keeps the reference-system *example* line (``1 1 1 01 01 a``, no text payload)
# from being reported as corruption; a real corrupt line carries a mantra.
_DIGIT_LABEL_HINT = re.compile(r"\d+ \d+ \d+ \d")
_HAS_WORD = re.compile(r"[^\W\d_]{3}")
# GRETIL's IAST conversion failed for vocalic long r, leaving raw ITRANS behind
# (``jaritR^INAm``).  The residue is real bytes in the source and is reported, not fixed.
_ITRANS_RESIDUE = re.compile(r"[A-Za-z]\^")
# The text is otherwise lowercase IAST; a stray capital marks an unconverted or
# inconsistently normalized token (the source writes ``Om`` three times).
_UNEXPECTED_UPPERCASE = re.compile(r"[A-Z]")


def _defect_locator(arcika: int, prapathaka: int, ardha: int, dasati: int, verse: int) -> str:
    """A human locator for a record the canonical identity function refuses.

    ``sv_mantra_identity`` fails closed on a defective verse index, so a defect record
    still needs something to point at.  This is deliberately not key-shaped: nothing
    downstream may mistake it for canonical identity.
    """
    return f"SV-DEFECT {arcika}.{prapathaka}.{ardha}.{dasati}.{verse}"


@dataclass(frozen=True)
class SamavedaSourceLine:
    """One physical line of the source, kept exactly as the snapshot spells it."""

    paragraph_index: int
    line_index: int
    label_notation: str
    line_label: str
    raw_line: str


@dataclass(frozen=True)
class SamavedaParseDefect:
    """Something the source says that this parser refuses to silently normalize."""

    defect_code: str
    paragraph_index: int
    detail: str
    raw_line: str | None = None
    verse_key: str | None = None


@dataclass
class SamavedaVerse:
    arcika: int
    prapathaka: int
    ardha: int
    dasati: int
    verse: int
    lines: list[SamavedaSourceLine] = field(default_factory=list)
    running_numbers: list[int] = field(default_factory=list)

    @property
    def hierarchy(self) -> dict[str, int | str]:
        return {
            "arcika": self.arcika,
            "prapathaka": self.prapathaka,
            "ardha": self.ardha,
            "dasati": self.dasati,
            "verse": self.verse,
        }

    @property
    def unit(self) -> tuple[int, int, int, int]:
        return (self.arcika, self.prapathaka, self.ardha, self.dasati)

    @property
    def coordinates(self) -> tuple[int, int, int, int, int]:
        return (self.arcika, self.prapathaka, self.ardha, self.dasati, self.verse)

    @property
    def has_canonical_identity(self) -> bool:
        """False when the source's own indices are defective beyond minting identity."""
        return self.arcika >= 1 and self.verse >= 1

    @property
    def verse_key(self) -> str:
        """The canonical key, or a clearly-marked defect locator when identity is refused."""
        if not self.has_canonical_identity:
            return _defect_locator(*self.coordinates)
        return sv_mantra_identity(*self.coordinates)[0]

    @property
    def structural_path(self) -> list[str]:
        """Level values as strings, zero-padding preserved, aligned to native_labels."""
        return [
            f"{self.arcika}",
            f"{self.prapathaka:02d}",
            f"{self.ardha}",
            f"{self.dasati:02d}",
            f"{self.verse:02d}",
        ]

    @property
    def citation(self) -> str:
        return f"SV {self.arcika}.{self.prapathaka}.{self.ardha}.{self.dasati}.{self.verse}"


@dataclass(frozen=True)
class SamavedaParseResult:
    verses: list[SamavedaVerse]
    defects: list[SamavedaParseDefect]
    structural_headings: list[tuple[int, str]]
    declared_reference_system: str | None
    verse_line_count: int
    notation_counts: dict[str, int]


def _paragraph_texts(snapshot_path: Path) -> list[str]:
    body = etree.parse(str(snapshot_path)).getroot().find(f".//{TEI}body")
    if body is None:
        raise ValueError(f"no TEI body in {snapshot_path}")
    return ["".join(paragraph.itertext()) for paragraph in body.findall(f"{TEI}p")]


def _strip_running_number(text: str) -> tuple[str, int | None]:
    match = _RUNNING_NUMBER.search(text)
    if match is None:
        return text.strip(), None
    return text[: match.start()].strip(), int(match.group(1))


def _match_label(line: str) -> tuple[re.Match[str], str] | None:
    spaced = _LABEL_SPACED.match(line)
    if spaced is not None:
        return spaced, "SPACED"
    concat = _LABEL_CONCAT.match(line)
    if concat is not None:
        return concat, "CONCAT"
    return None


class SamavedaGRETILAdapter(SourceAdapter):
    """Parse the GRETIL Kauthuma Samavedasamhita arcika text.

    This adapter covers the *arcika* (verse) text only.  The file contains no gana
    (song) collection, and this adapter therefore makes no claim about gana identity.
    """

    source_id = "GRETIL"

    def __init__(
        self,
        *,
        source_artifact_id: str = "GRETIL.SV.KAUTHUMA.TEI.2020",
        text_version_id: str = "GRETIL.SV.KAUTHUMA",
    ) -> None:
        self.source_artifact_id = source_artifact_id
        self.text_version_id = text_version_id

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        if scope not in {"SV", "SV.KAU"}:
            return []
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=SNAPSHOT_URL,
                locator="GRETIL sa_sAmavedasaMhitA.xml",
                media_type="application/tei+xml",
            )
        ]

    def parse_structure(self, snapshot_path: Path) -> SamavedaParseResult:
        """Read the snapshot into verses, headings and defects, repairing nothing."""
        paragraphs = _paragraph_texts(snapshot_path)
        verses: OrderedDict[tuple[int, int, int, int, int], SamavedaVerse] = OrderedDict()
        defects: list[SamavedaParseDefect] = []
        headings: list[tuple[int, str]] = []
        declared_reference_system: str | None = None
        notation_counts = {"SPACED": 0, "CONCAT": 0}
        verse_line_count = 0

        for paragraph_index, paragraph in enumerate(paragraphs):
            for line_index, physical_line in enumerate(paragraph.split("\n")):
                line = physical_line.strip()
                if not line:
                    continue
                matched = _match_label(line)
                if matched is None:
                    if "prapathaka | ardha" in line or "prapāṭhaka | ardha" in line:
                        declared_reference_system = line
                    headings.append((paragraph_index, line))
                    continue
                match, notation = matched
                notation_counts[notation] += 1
                verse_line_count += 1
                arcika, prapathaka, ardha, dasati, verse_number = (
                    int(value) for value in match.groups()[:5]
                )
                line_label, payload = match.group(6), match.group(7)
                key = (arcika, prapathaka, ardha, dasati, verse_number)
                verse = verses.get(key)
                if verse is None:
                    verse = SamavedaVerse(*key)
                    verses[key] = verse
                if any(existing.line_label == line_label for existing in verse.lines):
                    defects.append(
                        SamavedaParseDefect(
                            defect_code="DUPLICATE_LINE_LABEL",
                            paragraph_index=paragraph_index,
                            detail=(
                                f"line label {line_label!r} already present for this verse; "
                                "the source's verse numbering is inconsistent here"
                            ),
                            raw_line=line,
                            verse_key=verse.verse_key,
                        )
                    )
                if verse_number == 0:
                    defects.append(
                        SamavedaParseDefect(
                            defect_code="ZERO_VERSE_INDEX",
                            paragraph_index=paragraph_index,
                            detail="verse index is 0, which the reference system does not define",
                            raw_line=line,
                            verse_key=verse.verse_key,
                        )
                    )
                body_text, running = _strip_running_number(payload)
                if not body_text:
                    defects.append(
                        SamavedaParseDefect(
                            defect_code="EMPTY_VERSE_LINE",
                            paragraph_index=paragraph_index,
                            detail="reference label carries no text",
                            raw_line=line,
                            verse_key=verse.verse_key,
                        )
                    )
                if _ITRANS_RESIDUE.search(body_text):
                    defects.append(
                        SamavedaParseDefect(
                            defect_code="TRANSLITERATION_RESIDUE",
                            paragraph_index=paragraph_index,
                            detail=(
                                "unconverted ITRANS sequence survives in the source text; "
                                "the text is ingested verbatim and NOT repaired"
                            ),
                            raw_line=line,
                            verse_key=verse.verse_key,
                        )
                    )
                elif _UNEXPECTED_UPPERCASE.search(body_text):
                    defects.append(
                        SamavedaParseDefect(
                            defect_code="UNEXPECTED_UPPERCASE",
                            paragraph_index=paragraph_index,
                            detail=(
                                "capital letter in otherwise lowercase IAST text; "
                                "ingested verbatim and NOT repaired"
                            ),
                            raw_line=line,
                            verse_key=verse.verse_key,
                        )
                    )
                verse.lines.append(
                    SamavedaSourceLine(
                        paragraph_index=paragraph_index,
                        line_index=line_index,
                        label_notation=notation,
                        line_label=line_label,
                        raw_line=line,
                    )
                )
                if running is not None:
                    verse.running_numbers.append(running)

        for paragraph_index, heading in headings:
            if _DIGIT_LABEL_HINT.search(heading) and _HAS_WORD.search(heading):
                defects.append(
                    SamavedaParseDefect(
                        defect_code="UNPARSEABLE_REFERENCE_LABEL",
                        paragraph_index=paragraph_index,
                        detail=(
                            "line carries digits in reference-label position but matches "
                            "neither declared notation; its text is NOT ingested"
                        ),
                        raw_line=heading,
                    )
                )

        return SamavedaParseResult(
            verses=list(verses.values()),
            defects=defects,
            structural_headings=headings,
            declared_reference_system=declared_reference_system,
            verse_line_count=verse_line_count,
            notation_counts=notation_counts,
        )

    def verse_text(self, verse: SamavedaVerse) -> str:
        """Join a verse's source lines, dropping only the running-number apparatus.

        Whitespace between lines is collapsed to one space; every other character the
        source wrote, including GRETIL's in-word numeric svarita (``nya3trinam``) and
        the danda punctuation, survives untouched.
        """
        parts: list[str] = []
        for line in verse.lines:
            matched = _match_label(line.raw_line)
            if matched is None:  # pragma: no cover - re-matched, never re-classified
                raise ValueError(f"source line no longer parses: {line.raw_line!r}")
            body_text, _ = _strip_running_number(matched[0].group(7))
            if body_text:
                parts.append(body_text)
        return " ".join(" ".join(parts).split())

    def parse(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        units: frozenset[tuple[int, int, int, int]] | None = None,
    ) -> list[StagingTextRecord]:
        """Parse verses into staging records, optionally limited to selected units.

        A *unit* is an ``(arcika, prapathaka, ardha, dasati)`` tuple.  Restricting to a
        declared set of units is how the pilot samples structural regions without
        changing record semantics.
        """
        result = self.parse_structure(snapshot_path)
        records: list[StagingTextRecord] = []
        for verse in result.verses:
            if units is not None and verse.unit not in units:
                continue
            text = self.verse_text(verse)
            if not text:
                continue
            records.append(
                StagingTextRecord(
                    source_id=self.source_id,
                    source_artifact_id=self.source_artifact_id,
                    source_locator=verse.citation,
                    work_id="VG:WORK:SV:KAU",
                    hierarchy=verse.hierarchy,
                    text_original=text,
                    language="sa",
                    script="Latin",
                    accented=has_vedic_accents(text),
                    text_version_id=self.text_version_id,
                    text_role=TextRole.PRIMARY_TEXT,
                    snapshot_id=snapshot_id,
                )
            )
        return sorted(
            records,
            key=lambda record: tuple(
                int(record.hierarchy[level])
                for level in ("arcika", "prapathaka", "ardha", "dasati", "verse")
            ),
        )
