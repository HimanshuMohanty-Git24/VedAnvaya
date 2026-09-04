"""Bounded VHP HTML adapter used for verification and the RV 1.1 pilot."""

import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from vedagraph.identity import rv_mandala_key, rv_sukta_key
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord, SuktaDiscoveryRecord, VHPMetadataStagingRecord
from vedagraph.models.enums import DiscoveryAvailability
from vedagraph.normalize import has_vedic_accents

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
VERSE_PATTERN = re.compile(r"(.+?॥\s*[०-९0-9]+\s*॥)", re.DOTALL)  # noqa: RUF001
TRAILING_NUMBER = re.compile(r"॥\s*([०-९0-9]+)\s*॥\s*$")  # noqa: RUF001


class VHPAdapter(SourceAdapter):
    source_id = "VHP"

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        if scope != "RV.1.1":
            raise ValueError("D1 VHP discovery is intentionally bounded to RV.1.1")
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url="https://vedicheritage.gov.in/samhitas/rigveda/shakala-samhita/mandal-01/",
                locator="RV 1.1",
                media_type="text/html",
            )
        ]

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        soup = BeautifulSoup(snapshot_path.read_bytes(), "lxml")
        heading = soup.find(
            lambda tag: (
                tag.name in {"h1", "h2", "h3", "h4"}
                and "Sukta 001" in tag.get_text(" ", strip=True)
            )
        )
        if heading is None:
            raise ValueError("RV 1.1 heading was not found in VHP snapshot")
        chunks: list[str] = []
        for node in heading.find_all_next(string=True):
            value = " ".join(str(node).split())
            if "Links" == value:
                break
            if "॥" in value:
                chunks.append(value)
        text = " ".join(chunks)
        records: list[StagingTextRecord] = []
        for match in VERSE_PATTERN.finditer(text):
            verse = " ".join(match.group(1).split())
            number_match = TRAILING_NUMBER.search(verse)
            if not number_match:
                continue
            number = int(number_match.group(1).translate(DEVANAGARI_DIGITS))
            records.append(
                StagingTextRecord(
                    source_id=self.source_id,
                    source_locator=f"RV 1.1.{number}",
                    work_id="VG:WORK:RV:SAK",
                    hierarchy={"mandala": 1, "sukta": 1, "mantra": number},
                    text_original=verse,
                    accented=has_vedic_accents(verse),
                    snapshot_id=snapshot_id,
                )
            )
        if not records:
            raise ValueError("no mantra records found in VHP snapshot")
        return records

    def discover_suktas(
        self, snapshot_path: Path, *, snapshot_id: str, mandala: int
    ) -> list[SuktaDiscoveryRecord]:
        soup = BeautifulSoup(snapshot_path.read_bytes(), "lxml")
        discovered: dict[int, str] = {}
        for link in soup.find_all("a", href=True):
            label = " ".join(link.get_text(" ", strip=True).split())
            if label.isdigit():
                number = int(label)
                if number >= 1:
                    discovered[number] = str(link["href"])
        return [
            SuktaDiscoveryRecord(
                canonical_sukta_key=rv_sukta_key(mandala, number),
                sukta_number=number,
                mandala_number=mandala,
                parent_mandala_key=rv_mandala_key(mandala),
                source_id=self.source_id,
                source_locator=locator,
                availability=DiscoveryAvailability.REFERENCE_ONLY,
                discovery_source="VHP Mandala Sukta navigation",
                snapshot_id=snapshot_id,
            )
            for number, locator in sorted(discovered.items())
        ]

    def parse_metadata(self, snapshot_path: Path, *, snapshot_id: str) -> VHPMetadataStagingRecord:
        soup = BeautifulSoup(snapshot_path.read_bytes(), "lxml")
        heading = soup.find(
            lambda tag: (
                tag.name in {"h1", "h2", "h3", "h4"} and "Sukta" in tag.get_text(" ", strip=True)
            )
        )
        if heading is None:
            raise ValueError("Rigveda Sukta heading was not found in VHP snapshot")
        match = re.search(r"Mandala\s*0*(\d+)\s+Sukta\s*0*(\d+)", heading.get_text(" ", strip=True))
        if match is None:
            match = re.search(r"Sukta\s*0*(\d+)", heading.get_text(" ", strip=True))
            if match is None:
                raise ValueError("could not parse VHP Mandala/Sukta heading")
            mandala, sukta = 1, int(match.group(1))
        else:
            mandala, sukta = (int(value) for value in match.groups())

        content_block = heading.find_next(class_="fnt-shobhika-reg")
        if content_block is None:
            content_block = heading.find_next("p")
        block_text = (
            " ".join(content_block.get_text(" ", strip=True).split()) if content_block else ""
        )
        metadata_prefix = re.split(r"[\u0951-\u0954\u0331\u030d]", block_text, maxsplit=1)[0]
        markers = list(
            re.finditer(
                r"([०-९0-9]+)\s+(.+?)\s*।\s*(.+?)।\s*(.+?)।(?=\s|$)",  # noqa: RUF001
                metadata_prefix,
            )
        )
        marker = markers[-1] if markers else None
        media_urls = []
        for node in soup.find_all(["a", "source", "video"]):
            value = node.get("href") or node.get("src")
            if value and "RIGSS_" in value:
                joined = urlsplit(urljoin("https://vedicheritage.gov.in/", str(value)))
                media_urls.append(urlunsplit((joined.scheme, joined.netloc, joined.path, "", "")))
        return VHPMetadataStagingRecord(
            source_locator=f"RV {mandala}.{sukta} VHP page",
            hierarchy={"mandala": mandala, "sukta": sukta},
            rishis=[marker.group(2).strip()] if marker else [],
            devatas=[marker.group(3).strip()] if marker else [],
            chandas=[marker.group(4).strip()] if marker else [],
            reported_mantra_count=(
                int(marker.group(1).translate(DEVANAGARI_DIGITS)) if marker else None
            ),
            media_urls=sorted(set(media_urls)),
            snapshot_id=snapshot_id,
        )
