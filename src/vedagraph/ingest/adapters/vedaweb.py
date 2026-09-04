"""VedaWeb TEI adapter.

The VedaWeb Rigveda corpus is not one text. Each stanza carries several parallel
``<lg source="...">`` blocks that are separate editions with separate lineage and
separate licences, declared in ``vedaweb_corpus.tei``. This adapter keeps them apart.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from vedagraph.identity import rv_mandala_key, rv_sukta_key
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord, SuktaDiscoveryRecord
from vedagraph.models.enums import DiscoveryAvailability, RightsStatus, TextForm, TextRole
from vedagraph.normalize import has_vedic_accents

TEI = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
PARSER_VERSION = "vedaweb-rigveda-tei-v1"

#: Sanskrit ``@source`` values in the Book TEI, mapped to VedaGraph text vocabulary.
#: Translation layers are deliberately excluded; this adapter reads Sanskrit only.
SANSKRIT_VERSIONS: dict[str, tuple[TextForm, TextRole]] = {
    "aufrecht": (TextForm.SAMHITA, TextRole.PARALLEL_TEXT),
    "eichler": (TextForm.SAMHITA, TextRole.PARALLEL_TEXT),
    "lubotsky": (TextForm.SAMHITA, TextRole.COMPARISON_ONLY),
    "vnh": (TextForm.SAMHITA, TextRole.METRICALLY_RESTORED),
    "zurich": (TextForm.SAMHITA, TextRole.LINGUISTIC_ANNOTATION),
    "padapatha": (TextForm.PADAPATHA, TextRole.PADAPATHA),
}

_RIGHTS_BY_LICENCE_URI: dict[str, RightsStatus] = {
    "https://creativecommons.org/licenses/by/4.0/": RightsStatus.CC_BY,
    "https://creativecommons.org/licenses/by-sa/4.0/": RightsStatus.CC_BY_SA,
    "https://creativecommons.org/licenses/by-nc/4.0/": RightsStatus.CC_BY_NC,
    "https://creativecommons.org/licenses/by-nc-sa/4.0/": RightsStatus.CC_BY_NC_SA,
}


def _flat(element: etree._Element | None) -> str:
    if element is None:
        return ""
    parts = [part if isinstance(part, str) else part.decode("utf-8") for part in element.itertext()]
    return " ".join("".join(parts).split())


def rights_status_for(license_uri: str | None) -> RightsStatus:
    """Map a declared licence URI to a registry rights status, never guessing."""
    if license_uri is None:
        return RightsStatus.UNKNOWN
    return _RIGHTS_BY_LICENCE_URI.get(license_uri.rstrip("/") + "/", RightsStatus.UNKNOWN)


class VedaWebCorpusHeader:
    """Reads the per-source licence declarations from ``vedaweb_corpus.tei``."""

    def parse(self, snapshot_path: Path) -> list[dict[str, object]]:
        root = etree.parse(str(snapshot_path)).getroot()
        entries: list[dict[str, object]] = []
        list_bibl = root.find(f".//{{{TEI}}}sourceDesc/{{{TEI}}}listBibl")
        if list_bibl is None:
            raise ValueError("vedaweb_corpus.tei has no sourceDesc/listBibl")
        for bibl_full in list_bibl.findall(f"{{{TEI}}}biblFull"):
            key = bibl_full.get(XML_ID)
            if key is None:
                continue
            file_desc = bibl_full.find(f"{{{TEI}}}fileDesc")
            if file_desc is None:
                continue
            availability = file_desc.find(
                f"{{{TEI}}}publicationStmt/{{{TEI}}}availability",
            )
            licence = availability.find(f"{{{TEI}}}licence") if availability is not None else None
            titles = [
                _flat(title) for title in file_desc.findall(f"{{{TEI}}}titleStmt/{{{TEI}}}title")
            ]
            responsibilities = [
                _flat(statement)
                for statement in file_desc.findall(f"{{{TEI}}}titleStmt/{{{TEI}}}respStmt")
            ]
            upstream: list[str] = []
            source_desc = file_desc.find(f"{{{TEI}}}sourceDesc")
            if source_desc is not None:
                for node in source_desc.iter(f"{{{TEI}}}availability"):
                    upstream.extend(_flat(child) for child in node if _flat(child))
            pointer = file_desc.find(f"{{{TEI}}}publicationStmt/{{{TEI}}}ptr")
            entries.append(
                {
                    "source_version_key": key,
                    "titles": titles,
                    "responsibilities": responsibilities,
                    "license_uri": licence.get("target") if licence is not None else None,
                    "verbatim_license": _flat(licence),
                    "upstream_rights_notes": upstream,
                    "upstream_source": _flat(source_desc),
                    "data_pointer": pointer.get("target") if pointer is not None else None,
                }
            )
        return entries


class VedaWebAdapter(SourceAdapter):
    """Streams one VedaWeb book TEI into per-version staging text records."""

    source_id = "VEDAWEB"

    def __init__(
        self,
        *,
        source_artifact_id: str,
        versions: tuple[str, ...] = tuple(SANSKRIT_VERSIONS),
    ) -> None:
        unknown = sorted(set(versions) - set(SANSKRIT_VERSIONS))
        if unknown:
            raise ValueError(f"unknown VedaWeb Sanskrit versions: {', '.join(unknown)}")
        self.source_artifact_id = source_artifact_id
        self.versions = versions

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        raise NotImplementedError("VedaWeb artifacts are pinned by commit, not discovered")

    def _stanzas(self, snapshot_path: Path) -> Iterator[etree._Element]:
        context = etree.iterparse(str(snapshot_path), events=("end",), tag=f"{{{TEI}}}div")
        for _, element in context:
            if element.get("type") == "stanza":
                yield element
            element.clear()
            parent = element.getparent()
            while parent is not None and element.getprevious() is not None:
                del parent[0]

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        return self.parse_versions(snapshot_path, snapshot_id=snapshot_id)

    def parse_versions(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        suktas: frozenset[int] | None = None,
    ) -> list[StagingTextRecord]:
        """Return one staging record per (stanza, declared Sanskrit version)."""
        records: list[StagingTextRecord] = []
        for stanza in self._stanzas(snapshot_path):
            identifier = stanza.get(XML_ID) or ""
            location = _parse_stanza_id(identifier)
            if location is None:
                continue
            mandala, sukta, mantra = location
            if suktas is not None and sukta not in suktas:
                continue
            for group in stanza.findall(f"{{{TEI}}}lg"):
                version = group.get("source")
                if version is None or version not in self.versions:
                    continue
                text = _version_text(group)
                if not text:
                    continue
                _, text_role = SANSKRIT_VERSIONS[version]
                script = "Devanagari" if group.get(XML_LANG) == "san-Deva" else "Latin"
                records.append(
                    StagingTextRecord(
                        source_id=self.source_id,
                        source_artifact_id=self.source_artifact_id,
                        source_locator=f"{identifier}_{version}",
                        work_id="VG:WORK:RV:SAK",
                        hierarchy={"mandala": mandala, "sukta": sukta, "mantra": mantra},
                        text_original=text,
                        language="sa",
                        script=script,
                        accented=has_vedic_accents(text),
                        snapshot_id=snapshot_id,
                        text_version_id=version_id(self.source_artifact_id, version),
                        text_role=text_role,
                    )
                )
        return sorted(
            records,
            key=lambda record: (
                int(record.hierarchy["mandala"]),
                int(record.hierarchy["sukta"]),
                int(record.hierarchy["mantra"]),
                record.text_version_id or "",
            ),
        )

    def discover_suktas_from_records(
        self,
        records: list[StagingTextRecord],
        *,
        snapshot_id: str,
        mandala: int,
    ) -> list[SuktaDiscoveryRecord]:
        """Derive source-order structure from one parsed VedaWeb book."""
        counts: dict[int, set[int]] = {}
        for record in records:
            if int(record.hierarchy["mandala"]) != mandala:
                continue
            sukta = int(record.hierarchy["sukta"])
            counts.setdefault(sukta, set()).add(int(record.hierarchy["mantra"]))
        return [
            SuktaDiscoveryRecord(
                canonical_sukta_key=rv_sukta_key(mandala, sukta),
                sukta_number=sukta,
                mandala_number=mandala,
                parent_mandala_key=rv_mandala_key(mandala),
                source_id=self.source_id,
                source_artifact_id=self.source_artifact_id,
                source_locator=f"{self.source_artifact_id}#b{mandala:02d}_h{sukta:03d}",
                availability=DiscoveryAvailability.AVAILABLE,
                discovery_source="TEI book/hymn/stanza hierarchy",
                known_mantra_count=len(mantras),
                snapshot_id=snapshot_id,
            )
            for sukta, mantras in sorted(counts.items())
        ]


def version_id(artifact_id: str, source_version_key: str) -> str:
    return f"{artifact_id}#{source_version_key}"


def _parse_stanza_id(identifier: str) -> tuple[int, int, int] | None:
    """``b01_h001_01`` -> ``(1, 1, 1)``; anything else is skipped."""
    parts = identifier.split("_")
    if len(parts) != 3:
        return None
    book, hymn, stanza = parts
    if not (book.startswith("b") and hymn.startswith("h")):
        return None
    try:
        return int(book[1:]), int(hymn[1:]), int(stanza)
    except ValueError:
        return None


def _version_text(group: etree._Element) -> str:
    """Join a version's lines, skipping the token-annotation sibling lines."""
    lines: list[str] = []
    for line in group.findall(f"{{{TEI}}}l"):
        line_id = line.get(XML_ID) or ""
        if line_id.endswith("_tokens"):
            continue
        value = _flat(line)
        if value:
            lines.append(value)
    return " ".join(lines)
