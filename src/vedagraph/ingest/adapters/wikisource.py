"""Wikisource Griffith adapter with revision-aware MediaWiki parsing."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import orjson
from bs4 import BeautifulSoup

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord, StagingTranslationRecord
from vedagraph.models.enums import TranslationAlignment

PARSER_VERSION = "wikisource-griffith-v2"


class WikisourceTranslationAdapter(SourceAdapter):
    source_id = "WIKISOURCE_GRIFFITH_RV"

    def __init__(self, *, source_artifact_id: str = "GRIFFITH.RV.1896.WIKISOURCE") -> None:
        self.source_artifact_id = source_artifact_id

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        parts = scope.split(".")
        if len(parts) != 3 or parts[0] != "RV":
            raise ValueError("Wikisource discovery requires scope RV.<mandala>.<sukta>")
        mandala, sukta = (int(value) for value in parts[1:])
        title = f"The Hymns of the Rigveda/Book {mandala}/Hymn {sukta}"
        url = (
            "https://en.wikisource.org/w/api.php?action=parse&format=json&formatversion=2"
            f"&prop=text%7Crevid%7Cdisplaytitle&page={quote(title)}"
        )
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=url,
                locator=f"RV {mandala}.{sukta}",
                media_type="application/json",
            )
        ]

    @staticmethod
    def _document(snapshot_path: Path) -> tuple[BeautifulSoup, dict[str, object]]:
        content = snapshot_path.read_bytes()
        if content.lstrip().startswith(b"{"):
            payload = orjson.loads(content)
            parsed = payload.get("parse", payload)
            html = parsed.get("text", "")
            if isinstance(html, dict):
                html = html.get("*", "")
            if not isinstance(html, str):
                raise ValueError("MediaWiki parse response has no HTML text")
            return BeautifulSoup(html, "lxml"), parsed
        return BeautifulSoup(content, "lxml"), {}

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        soup, _ = self._document(snapshot_path)
        records: list[StagingTextRecord] = []
        for span in soup.select("[data-vedagraph-verse]"):
            number = int(str(span["data-vedagraph-verse"]))
            records.append(
                StagingTextRecord(
                    source_id=self.source_id,
                    source_locator=f"RV 1.1.{number}",
                    work_id="VG:WORK:RV:SAK",
                    hierarchy={"mandala": 1, "sukta": 1, "mantra": number},
                    text_original=span.get_text(" ", strip=True),
                    language="en",
                    script="Latin",
                    snapshot_id=snapshot_id,
                )
            )
        return records

    @staticmethod
    def _legacy_text(soup: BeautifulSoup) -> str:
        """Text of pages that carry no ``.ws-poem`` markup.

        Older transcriptions use ``<div class="verse"><pre>``; the oldest carry the
        stanzas as plain body text.  Both are numbered the same way, so fall back to the
        parser output with the navigation header removed rather than special-casing pages.
        """
        preformatted = soup.select_one(".verse pre")
        if preformatted is not None:
            return preformatted.get_text("\n")
        body = soup.select_one(".mw-parser-output") or soup
        for chrome in body.select(".ws-noexport, .ws-header, .licenseContainer, sup.reference"):
            chrome.decompose()
        return body.get_text("\n")

    def parse_translations(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        mandala: int = 1,
        sukta: int = 1,
        revision_timestamp: datetime | None = None,
        retrieval_timestamp: datetime | None = None,
    ) -> list[StagingTranslationRecord]:
        """Parse source-numbered Griffith stanzas from a page or MediaWiki response."""
        soup, page = self._document(snapshot_path)
        stanzas = soup.select(".prp-pages-output .ws-poem .ws-poem-stanza")
        if not stanzas:
            stanzas = soup.select(".ws-poem .ws-poem-stanza")
        numbered_texts: list[tuple[int, str]] = []
        if stanzas:
            explicit_numbers: list[int | None] = []
            for sequence, stanza in enumerate(stanzas, start=1):
                marker = stanza.select_one(".ws-poem-versenum")
                label = marker.get_text(" ", strip=True) if marker else ""
                explicit_numbers.append(int(label) if label.isdigit() else None)
                for reference in stanza.select("sup.reference, .ws-poem-versenum, .pagenum"):
                    reference.decompose()
                lines = [line.get_text(" ", strip=True) for line in stanza.select(".ws-poem-line")]
                text = " ".join(part for part in lines if part)
                if text:
                    numbered_texts.append((sequence, text))
            exact = all(
                number == sequence or (sequence == 1 and number is None)
                for sequence, number in enumerate(explicit_numbers, start=1)
            )
        else:
            raw_text = self._legacy_text(soup)
            # Legacy pages use several source-number markers: ``1. text``, ``1 text``,
            # ``1.TEXT`` and (for example in RV 2.28) ``2, text``. Match the observed
            # grammar rather than a Mandala-specific exception. A number must be followed
            # by punctuation or whitespace, avoiding digits embedded in verse text.
            number_pattern = r"\d+(?:[.,]\s*|\s+)"
            matches = list(
                re.finditer(
                    rf"(?ms)^\s*(\d+)(?:[.,]\s*|\s+)(.*?)(?=^\s*{number_pattern}|\Z)",
                    raw_text,
                )
            )
            numbered_texts = [
                (int(match.group(1)), " ".join(match.group(2).split())) for match in matches
            ]
            exact = [number for number, _ in numbered_texts] == list(
                range(1, len(numbered_texts) + 1)
            )
        alignment = (
            TranslationAlignment.EXACT_MANTRA_ALIGNMENT
            if exact
            else TranslationAlignment.UNCERTAIN_ALIGNMENT
        )

        page_title = page.get("title")
        page_id = page.get("pageid")
        revision_id = page.get("revid")
        canonical_url = None
        if isinstance(page_title, str):
            canonical_url = f"https://en.wikisource.org/wiki/{quote(page_title.replace(' ', '_'))}"

        records: list[StagingTranslationRecord] = []
        for sequence, text in numbered_texts:
            records.append(
                StagingTranslationRecord(
                    source_id=self.source_id,
                    source_artifact_id=self.source_artifact_id,
                    source_locator=f"RV {mandala}.{sukta}.{sequence}",
                    work_id="VG:WORK:RV:SAK",
                    hierarchy={"mandala": mandala, "sukta": sukta, "mantra": sequence},
                    text_original=text,
                    language="en",
                    translator="Ralph T. H. Griffith",
                    work_edition="The Hymns of the Rigveda, second edition",
                    year=1896,
                    snapshot_id=snapshot_id,
                    alignment=alignment,
                    page_title=page_title if isinstance(page_title, str) else None,
                    page_id=page_id if isinstance(page_id, int) else None,
                    revision_id=revision_id if isinstance(revision_id, int) else None,
                    revision_timestamp=revision_timestamp,
                    canonical_page_url=canonical_url,
                    retrieval_timestamp=retrieval_timestamp,
                )
            )
        if not records:
            raise ValueError("no Wikisource poem stanzas found")
        return records


def canonical_url_from_api_url(api_url: str, title: str) -> str:
    """Build a stable page URL using the API response host."""
    parsed = urlparse(api_url)
    return f"{parsed.scheme}://{parsed.netloc}/wiki/{quote(title.replace(' ', '_'))}"
