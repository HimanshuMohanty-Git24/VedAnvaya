"""Sanskrit Wikisource Kauthuma Samaveda adapter.

This is the parallel Sanskrit source for the Samaveda pilot. It differs from the GRETIL
artifact on every axis that matters, which is exactly why it is worth comparing against:
Devanagari rather than IAST, community transcription rather than a 1998 e-text, and
CC BY-SA 4.0 rather than a contested licence.

Its page tree encodes structure in the title, not in the body::

    samavedah/kauthumiya/samhita/purvarcikah/chanda arcikah/
        1.1.1 prathamaprapathakah/1.1.1.1 prathama dasatih

Two structural facts fall out of that tree and independently corroborate the GRETIL
reading of the hierarchy:

* there is no ``ardha`` level -- prapathaka contains dasati 1..10 directly, which is
  consistent with GRETIL numbering dasati continuously across the two ardhas
  (ardha 1 = dasati 1-5, ardha 2 = dasati 6-10), so ardha is derivable rather than
  independent;
* the Aranya arcika is nested *inside* Purvarcika as ``1.2.x`` with no prapathaka at
  all, where GRETIL numbers it as a sibling arcika 2 with prapathaka encoded ``0``.

The second point is a real edition-order divergence and is recorded, not reconciled.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents

PARSER_VERSION = "wikisource-sa-samaveda-dasati-v1"
# Matches the registered source in data/registry/sources.yaml, which Agent E owns.
SOURCE_ID = "WIKISOURCE_SA"

API_TEMPLATE = (
    "https://sa.wikisource.org/w/api.php?action=parse&page={page}"
    "&prop=wikitext%7Crevid&formatversion=2&format=json"
)

# Verse terminator: a Devanagari or ASCII numeral between double dandas.
_VERSE_END = re.compile(r"॥\s*([\d०-९]+)\s*॥")  # noqa: RUF001
# Wiki markup that carries no text.
_STRIP_TAGS = re.compile(r"</?(?:poem|span|div|br)\b[^>]*>", re.IGNORECASE)
_EXTERNAL_LINK = re.compile(r"\[(?:https?|//)\S+?(?:\s+([^\]]*))?\]")
_WIKI_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HEADING = re.compile(r"^=+\s*.*?\s*=+$", re.MULTILINE)


def _devanagari_int(text: str) -> int:
    return int("".join(str(unicodedata.decimal(c)) if not c.isascii() else c for c in text))


def _clean(text: str) -> str:
    text = _TEMPLATE.sub(" ", text)
    text = _STRIP_TAGS.sub(" ", text)
    text = _EXTERNAL_LINK.sub(" ", text)
    text = _WIKI_LINK.sub(r"\1", text)
    return _HEADING.sub(" ", text)


@dataclass(frozen=True)
class WikisourceVerse:
    verse: int
    text: str
    page_title: str
    revision_id: int


@dataclass(frozen=True)
class WikisourceDasati:
    page_title: str
    revision_id: int
    verses: list[WikisourceVerse]
    unparsed_remainder: list[str]


class SamavedaWikisourceAdapter(SourceAdapter):
    """Parse one Sanskrit Wikisource dasati page into verse records."""

    source_id = SOURCE_ID

    def __init__(
        self,
        *,
        source_artifact_id: str = "WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI",
        text_version_id: str = "WIKISOURCE_SA.SV.KAU.DEVANAGARI",
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

    def parse_dasati(self, snapshot_path: Path) -> WikisourceDasati:
        """Split one page's wikitext into numbered verses, keeping what did not parse."""
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        parse = payload["parse"]
        wikitext = _clean(parse["wikitext"])

        verses: list[WikisourceVerse] = []
        remainder: list[str] = []
        cursor = 0
        for match in _VERSE_END.finditer(wikitext):
            body = wikitext[cursor : match.start()]
            cursor = match.end()
            text = " ".join(body.split())
            if not text:
                remainder.append(f"empty body before verse {match.group(1)}")
                continue
            verses.append(
                WikisourceVerse(
                    verse=_devanagari_int(match.group(1)),
                    text=text,
                    page_title=parse["title"],
                    revision_id=int(parse["revid"]),
                )
            )
        tail = " ".join(wikitext[cursor:].split())
        if tail:
            remainder.append(tail)
        return WikisourceDasati(
            page_title=parse["title"],
            revision_id=int(parse["revid"]),
            verses=verses,
            unparsed_remainder=remainder,
        )

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        """Not available for this adapter. Use :meth:`parse_at_address` instead.

        This override exists to KEEP the base-class contract rather than to fulfil it.
        ``SourceAdapter.parse`` promises that a snapshot alone is enough to produce
        staging records, and for this source that promise cannot be kept honestly: a
        record needs a five-level address, the Wikisource page tree supplies only four
        levels, and inventing the missing ``ardha`` is precisely the kind of silent
        structural guess this project forbids. See :meth:`parse_at_address`.

        Previously this class overrode ``parse`` with four EXTRA REQUIRED keyword
        arguments. That was not merely a typing defect -- it broke
        ``SourceAdapter.to_staging_records``, which calls
        ``self.parse(snapshot_path, snapshot_id=...)`` generically and would therefore
        raise ``TypeError`` on this adapter at runtime. Failing loudly and specifically
        here is better than failing on an argument-count mismatch that says nothing
        about why.
        """
        raise NotImplementedError(
            "SamavedaWikisourceAdapter cannot parse from a snapshot alone. Its records "
            "require an explicit (arcika, prapathaka, ardha, dasati) address, because "
            "the Wikisource page tree has no ardha level and the mapping onto the "
            "selected edition's five-level address is a declared alignment decision, "
            "not something this parser may infer. Call parse_at_address() instead."
        )

    def parse_at_address(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        arcika: int,
        prapathaka: int,
        ardha: int,
        dasati: int,
    ) -> list[StagingTextRecord]:
        """Staging records for one dasati, keyed by the caller's declared coordinates.

        The coordinates are supplied rather than derived: the Wikisource page tree has
        no ardha level, so the mapping onto the selected edition's five-level address is
        a declared alignment decision and not something this parser may invent.

        NOTE ON VERSE NUMBERING, verified against the three pinned snapshots: the verse
        numbers this adapter reads are the edition's RUNNING numbers (1..1875), not
        dasati-local indices -- the fifth dasati of prapathaka 1 yields verses 45-54, and
        Aranya 1.2.1 yields 586-594. Any caller mapping these onto a local ``V{verse:02d}``
        key slot must convert running -> local explicitly, and must never use page-local
        ordinal or sequence position to do it.
        """
        page = self.parse_dasati(snapshot_path)
        return [
            StagingTextRecord(
                source_id=self.source_id,
                source_artifact_id=self.source_artifact_id,
                source_locator=f"SV {arcika}.{prapathaka}.{ardha}.{dasati}.{verse.verse}",
                work_id="VG:WORK:SV:KAU",
                hierarchy={
                    "arcika": arcika,
                    "prapathaka": prapathaka,
                    "ardha": ardha,
                    "dasati": dasati,
                    "verse": verse.verse,
                },
                text_original=verse.text,
                language="sa",
                script="Devanagari",
                accented=has_vedic_accents(verse.text),
                text_version_id=self.text_version_id,
                text_role=TextRole.PARALLEL_TEXT,
                snapshot_id=snapshot_id,
            )
            for verse in page.verses
        ]
