"""GRETIL Rigveda TEI adapter with explicit editorial-text selection."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from vedagraph.identity import rv_mandala_key, rv_sukta_key
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import GretilHeaderMetadata, StagingTextRecord, SuktaDiscoveryRecord
from vedagraph.models.enums import DiscoveryAvailability, TextSelectionPolicy
from vedagraph.normalize import has_vedic_accents

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
RV_LG_ID = re.compile(r"^RV_(\d+)\.(\d+)\.(\d+)$")
PARSER_VERSION = "gretil-rigveda-tei-v2"


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _normalized_text(element: etree._Element | None) -> str | None:
    if element is None:
        return None
    text = " ".join(
        "".join(
            part.decode("utf-8") if isinstance(part, bytes) else part for part in element.itertext()
        ).split()
    )
    return text or None


def _selected_text(element: etree._Element, policy: TextSelectionPolicy) -> str:
    """Select one TEI editorial branch without concatenating alternatives."""
    parts: list[str] = []

    def visit(node: etree._Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            name = _local_name(child)
            if name == "choice":
                preferred = (
                    ("orig", "sic") if policy == TextSelectionPolicy.ORIGINAL else ("reg", "corr")
                )
                selected = next(
                    (
                        candidate
                        for wanted in preferred
                        for candidate in child
                        if _local_name(candidate) == wanted
                    ),
                    None,
                )
                if selected is None:
                    selected = child[0] if len(child) else None
                if selected is not None:
                    visit(selected)
            elif name in {"orig", "sic"} and policy == TextSelectionPolicy.REGULARIZED:
                pass
            else:
                visit(child)
            if child.tail:
                parts.append(child.tail)

    visit(element)
    return " ".join("".join(parts).split())


class GRETILAdapter(SourceAdapter):
    source_id = "GRETIL"

    def __init__(
        self,
        *,
        text_selection_policy: TextSelectionPolicy = TextSelectionPolicy.ORIGINAL,
        source_artifact_id: str = "GRETIL.RV.AUFRECHT.TEI.2019",
    ) -> None:
        self.text_selection_policy = text_selection_policy
        self.source_artifact_id = source_artifact_id

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        if scope not in {"RV", "RV.1"}:
            return []
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url="https://gretil.sub.uni-goettingen.de/gretil/corpustei/sa_Rgveda-edAufrecht.xml",
                locator="GRETIL sa_Rgveda-edAufrecht.xml",
                media_type="application/tei+xml",
            )
        ]

    def extract_header_metadata(self, snapshot_path: Path) -> GretilHeaderMetadata:
        root = etree.parse(str(snapshot_path)).getroot()

        def elements(name: str) -> list[etree._Element]:
            return [element for element in root.iter() if _local_name(element) == name]

        statements: dict[str, list[str]] = {}
        for statement in elements("respStmt"):
            responsibility = _normalized_text(
                next((child for child in statement if _local_name(child) == "resp"), None)
            )
            names = [
                value
                for child in statement
                if _local_name(child) == "name" and (value := _normalized_text(child)) is not None
            ]
            if responsibility:
                statements.setdefault(responsibility, []).extend(names)

        source_bibliography = [
            value
            for bibliography in elements("biblStruct")
            if (value := _normalized_text(bibliography)) is not None
        ]
        availability = next(iter(elements("availability")), None)
        licence = next(iter(elements("licence")), None)
        publication_stmt = next(iter(elements("publicationStmt")), None)
        publication_date = None
        if publication_stmt is not None:
            date_element = next(
                (child for child in publication_stmt if _local_name(child) == "date"), None
            )
            if date_element is not None:
                publication_date = date_element.get("when-iso") or _normalized_text(date_element)

        encoding_information = [
            value
            for node in elements("encodingDesc")
            if (value := _normalized_text(node)) is not None
        ]
        revision_information = [
            value
            for node in elements("revisionDesc")
            if (value := _normalized_text(node)) is not None
        ]
        languages = [
            value
            for language in elements("language")
            if (value := language.get("ident") or _normalized_text(language)) is not None
        ]
        return GretilHeaderMetadata(
            title=_normalized_text(next(iter(elements("title")), None)),
            publisher=_normalized_text(next(iter(elements("publisher")), None)),
            publication_date=publication_date,
            responsibility_statements=statements,
            source_bibliography=source_bibliography,
            license_statement_verbatim=_normalized_text(availability),
            license_url=licence.get("target") if licence is not None else None,
            revision_information=revision_information,
            encoding_information=encoding_information,
            languages=languages,
            xml_id=root.get(XML_ID),
        )

    def parse(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        mandala: int | None = None,
    ) -> list[StagingTextRecord]:
        """Parse Rigveda mantra records, optionally retaining one Mandala.

        The source is a single whole-Rigveda TEI file.  The optional filter keeps
        per-Mandala builds from retaining the other nine Mandalas in memory while
        preserving the exact same record semantics and order.
        """
        document = etree.parse(str(snapshot_path))
        records: list[StagingTextRecord] = []
        for element in document.getroot().iter():
            if _local_name(element) != "lg":
                continue
            identifier = element.get(XML_ID) or element.get("n") or ""
            match = RV_LG_ID.fullmatch(identifier)
            if match is None:
                continue
            parsed_mandala, sukta, mantra = (int(part) for part in match.groups())
            if mandala is not None and mandala != parsed_mandala:
                continue
            selected = _selected_text(element, self.text_selection_policy)
            alternate_policy = (
                TextSelectionPolicy.REGULARIZED
                if self.text_selection_policy == TextSelectionPolicy.ORIGINAL
                else TextSelectionPolicy.ORIGINAL
            )
            alternate = _selected_text(element, alternate_policy)
            records.append(
                StagingTextRecord(
                    source_id=self.source_id,
                    source_artifact_id=self.source_artifact_id,
                    source_locator=f"RV {parsed_mandala}.{sukta}.{mantra}",
                    work_id="VG:WORK:RV:SAK",
                    hierarchy={"mandala": parsed_mandala, "sukta": sukta, "mantra": mantra},
                    text_original=selected,
                    alternate_text=alternate if alternate != selected else None,
                    text_selection_policy=self.text_selection_policy,
                    script="Latin",
                    accented=has_vedic_accents(selected),
                    snapshot_id=snapshot_id,
                )
            )
        return sorted(
            records,
            key=lambda record: (
                int(record.hierarchy["mandala"]),
                int(record.hierarchy["sukta"]),
                int(record.hierarchy["mantra"]),
            ),
        )

    def discover_suktas(
        self, snapshot_path: Path, *, snapshot_id: str, mandala: int
    ) -> list[SuktaDiscoveryRecord]:
        return self.discover_suktas_from_records(
            self.parse(snapshot_path, snapshot_id=snapshot_id, mandala=mandala),
            snapshot_id=snapshot_id,
            mandala=mandala,
        )

    def discover_suktas_from_records(
        self,
        records: list[StagingTextRecord],
        *,
        snapshot_id: str,
        mandala: int,
    ) -> list[SuktaDiscoveryRecord]:
        """Create discovery records from an already parsed Mandala.

        This avoids a second full XML parse during every build.
        """
        counts: dict[int, int] = {}
        for record in records:
            if record.hierarchy["mandala"] == mandala:
                sukta = int(record.hierarchy["sukta"])
                counts[sukta] = counts.get(sukta, 0) + 1
        return [
            SuktaDiscoveryRecord(
                canonical_sukta_key=rv_sukta_key(mandala, sukta),
                sukta_number=sukta,
                mandala_number=mandala,
                parent_mandala_key=rv_mandala_key(mandala),
                source_id=self.source_id,
                source_artifact_id=self.source_artifact_id,
                source_locator=f"{self.source_artifact_id}#RV_{mandala}.{sukta:03d}",
                availability=DiscoveryAvailability.AVAILABLE,
                discovery_source="TEI div/lg hierarchy",
                known_mantra_count=count,
                snapshot_id=snapshot_id,
            )
            for sukta, count in sorted(counts.items())
        ]
