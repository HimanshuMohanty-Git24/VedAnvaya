"""Read the Zurich morphological annotation out of the pinned VedaWeb book TEI.

The morphology is not a separate corpus. It is the ``zurich`` annotation layer already
present in the VedaWeb book TEI artifacts this project pinned at commit ``d3eb8af``, and
it is the layer whose provenance the corpus TEI header records as a Filemaker database
morphosyntactically annotated over more than ten years at the University of Zurich, on
Lubotsky's text, later corrected against Grassmann's Rigveda dictionary.

Alignment is structural and nothing else. Each stanza's ``xml:id`` (``b02_h001_01``)
states its Mandala, Sūkta and mantra directly, so a token reaches its canonical mantra by
citation, never by comparing text. A stanza whose id does not parse is skipped and
counted, not guessed at.

The annotation's own surface reading is preserved as ``surface_form``. It is *not* the
canonical Sanskrit: ``GRETIL.RV.AUFRECHT`` remains the primary text, untouched.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from lxml import etree

from vedagraph.identity import rv_mantra_key, uuid_for_urn
from vedagraph.models.lexical import MorphologyToken
from vedagraph.normalize import normalize_nfc, strip_vedic_accents

TEI = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

MORPHOLOGY_PARSER_VERSION = "vedaweb-zurich-morphology-v1"

#: The annotation layer token ids are tied to. Tokenization is a property of an edition,
#: so a different morphology source would produce different token ids for the same
#: mantra. It would *not* change the mantra's own canonical id.
ANNOTATION_LAYER_ID = "VEDAWEB.ZURICH"
ANNOTATION_PROVENANCE = (
    "University of Zurich morphosyntactic annotation of Lubotsky's Rigveda text "
    "(Widmer/Scarlata), corrected against Grassmann's dictionary by Halfmann and "
    "Korobzow, published in VedaWeb TEI by the Cologne Center for eHumanities"
)
ANNOTATION_METHOD = "MANUAL_SCHOLARLY_ANNOTATION"
ANNOTATION_LICENSE = "CC BY 4.0"
MORPHOLOGY_SOURCE_ID = "VEDAWEB"
MORPHOLOGY_REPOSITORY_URL = "https://github.com/VedaWebProject/vedaweb-data"
MORPHOLOGY_COMMIT_SHA = "d3eb8af7324338161520d2d35eae8f7e985a19a5"

#: ``b02_h001_01_zur_d_05`` -> mandala 2, sūkta 1, mantra 1, pāda ``d``, token 5.
_TOKEN_ID = re.compile(
    r"^b(?P<book>\d+)_h(?P<hymn>\d+)_(?P<stanza>\d+)_zur_(?P<pada>[a-z])_(?P<token>\d+)$"
)
_STANZA_ID = re.compile(r"^b(?P<book>\d+)_h(?P<hymn>\d+)_(?P<stanza>\d+)$")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class MorphologyArtifact:
    """One pinned book TEI snapshot carrying the annotation layer."""

    mandala: int
    artifact_id: str
    snapshot_path: Path
    snapshot_id: str
    sha256: str
    url: str


@dataclass
class MorphologyParseReport:
    """What the parser saw, so gaps are reported rather than inferred."""

    stanzas_seen: int = 0
    stanzas_with_annotation: int = 0
    unparsable_stanza_ids: list[str] = None  # type: ignore[assignment]
    unparsable_token_ids: list[str] = None  # type: ignore[assignment]
    tokens_without_lemma: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.unparsable_stanza_ids = self.unparsable_stanza_ids or []
        self.unparsable_token_ids = self.unparsable_token_ids or []
        self.tokens_without_lemma = self.tokens_without_lemma or []


def token_identity(
    mandala: int, sukta: int, mantra: int, pada: str, sequence: int
) -> tuple[str, str, UUID]:
    """Deterministic identity for one annotated token.

    The key names the annotation layer because tokenization differs between editions;
    the mantra's own canonical id is unaffected by which morphology source is selected.
    Identity derives from the citation alone, never from insertion order.
    """
    layer_slug = ANNOTATION_LAYER_ID.replace(".", "-")
    key = (
        f"VG:TOKEN:{layer_slug}:RV:SAK:M{mandala:02d}:S{sukta:03d}:V{mantra:03d}"
        f":P{pada.upper()}:T{sequence:03d}"
    )
    urn = (
        f"urn:vedagraph:token:{ANNOTATION_LAYER_ID.lower()}:rigveda:shakala"
        f":mandala:{mandala}:sukta:{sukta}:mantra:{mantra}:pada:{pada.lower()}:token:{sequence}"
    )
    return key, urn, uuid_for_urn(urn)


def normalize_lemma(lemma: str) -> str:
    """Fold a lemma to its comparison form: NFC, accentless, lowercase, no stem marks.

    The annotation writes nominal stems with a trailing hyphen (``agní-``) and verbal
    roots with a leading root sign (``√jan¹-``). Those are notation, not spelling, so
    they are removed. Nothing else about the word is altered, and two different
    spellings are never merged here.
    """
    value = strip_vedic_accents(normalize_nfc(lemma)).strip().lower()
    value = value.replace("√", "")
    value = _WHITESPACE.sub(" ", value).strip()
    return value.strip("-").strip()


def normalize_surface(surface: str) -> str:
    """Comparison form of a surface token: NFC, accentless, lowercase."""
    return _WHITESPACE.sub(" ", strip_vedic_accents(normalize_nfc(surface)).strip().lower())


def _stanzas(path: Path) -> Iterator[etree._Element]:
    context = etree.iterparse(str(path), events=("end",), tag=f"{{{TEI}}}div")
    for _, element in context:
        if element.get("type") == "stanza":
            yield element
        element.clear()
        parent = element.getparent()
        while parent is not None and element.getprevious() is not None:
            del parent[0]


def _feature_values(feature_set: etree._Element) -> dict[str, object]:
    """Flatten one ``<fs type="zurich_info">`` into plain fields."""
    values: dict[str, object] = {}
    for feature in feature_set.findall(f"{{{TEI}}}f"):
        name = feature.get("name")
        if name is None:
            continue
        string = feature.find(f"{{{TEI}}}string")
        symbol = feature.find(f"{{{TEI}}}symbol")
        nested = feature.find(f"{{{TEI}}}fs")
        if string is not None:
            values[name] = ((string.text or "").strip(), string.get("correction"))
        elif symbol is not None:
            values[name] = symbol.get("value") or ""
        elif nested is not None:
            morphology: dict[str, str] = {}
            for inner in nested.findall(f"{{{TEI}}}f"):
                inner_name = inner.get("name")
                inner_symbol = inner.find(f"{{{TEI}}}symbol")
                if inner_name and inner_symbol is not None and inner_symbol.get("value"):
                    morphology[inner_name] = str(inner_symbol.get("value"))
            values[name] = morphology
    return values


def parse_morphology(
    artifact: MorphologyArtifact,
    *,
    report: MorphologyParseReport | None = None,
) -> list[MorphologyToken]:
    """Parse one pinned book TEI into annotated tokens aligned by structural citation."""
    report = report if report is not None else MorphologyParseReport()
    tokens: list[MorphologyToken] = []
    for stanza in _stanzas(artifact.snapshot_path):
        report.stanzas_seen += 1
        stanza_id = stanza.get(XML_ID) or ""
        stanza_match = _STANZA_ID.match(stanza_id)
        if stanza_match is None:
            report.unparsable_stanza_ids.append(stanza_id)
            continue
        mandala = int(stanza_match.group("book"))
        sukta = int(stanza_match.group("hymn"))
        mantra = int(stanza_match.group("stanza"))
        stanza_tokens = _stanza_tokens(stanza, artifact, mandala, sukta, mantra, report)
        if stanza_tokens:
            report.stanzas_with_annotation += 1
            tokens.extend(stanza_tokens)
    return tokens


def _stanza_tokens(
    stanza: etree._Element,
    artifact: MorphologyArtifact,
    mandala: int,
    sukta: int,
    mantra: int,
    report: MorphologyParseReport,
) -> list[MorphologyToken]:
    passage_key = rv_mantra_key(mandala, sukta, mantra)
    passage_urn = (
        f"urn:vedagraph:mantra:rigveda:shakala:mandala:{mandala}:sukta:{sukta}:mantra:{mantra}"
    )
    passage_id = uuid_for_urn(passage_urn)
    out: list[MorphologyToken] = []
    sequence = 0
    for group in stanza.findall(f"{{{TEI}}}lg"):
        if group.get("source") != "zurich":
            continue
        for line in group.findall(f"{{{TEI}}}l"):
            line_id = line.get(XML_ID) or ""
            if not line_id.endswith("_tokens"):
                continue
            for feature_set in line.findall(f"{{{TEI}}}fs"):
                if feature_set.get("type") != "zurich_info":
                    continue
                raw_id = feature_set.get(XML_ID) or ""
                parsed = _TOKEN_ID.match(raw_id)
                if parsed is None:
                    report.unparsable_token_ids.append(raw_id)
                    continue
                values = _feature_values(feature_set)
                surface_value = values.get("surface")
                lemma_value = values.get("gra_lemma")
                surface = surface_value[0] if isinstance(surface_value, tuple) else ""
                lemma = lemma_value[0] if isinstance(lemma_value, tuple) else ""
                correction = lemma_value[1] if isinstance(lemma_value, tuple) else None
                if not surface:
                    report.unparsable_token_ids.append(raw_id)
                    continue
                if not lemma:
                    # No lemma is reported, never invented.
                    report.tokens_without_lemma.append(raw_id)
                    continue
                sequence += 1
                pada = parsed.group("pada")
                key, urn, token_uuid = token_identity(mandala, sukta, mantra, pada, sequence)
                part_of_speech = values.get("gra_gramm")
                features = values.get("morphosyntax")
                out.append(
                    MorphologyToken(
                        token_id=token_uuid,
                        token_key=key,
                        canonical_urn=urn,
                        passage_key=passage_key,
                        passage_id=passage_id,
                        annotation_layer_id=ANNOTATION_LAYER_ID,
                        source_id=MORPHOLOGY_SOURCE_ID,
                        source_artifact_id=artifact.artifact_id,
                        snapshot_id=artifact.snapshot_id,
                        source_locator=raw_id,
                        sequence=sequence,
                        pada=pada,
                        pada_sequence=int(parsed.group("token")),
                        surface_form=normalize_nfc(surface),
                        normalized_surface=normalize_surface(surface),
                        lemma=normalize_nfc(lemma),
                        normalized_lemma=normalize_lemma(lemma),
                        lemma_ids=sorted(_lemma_ids(correction)),
                        part_of_speech=part_of_speech if isinstance(part_of_speech, str) else None,
                        morphological_features=features if isinstance(features, dict) else {},
                        annotation_provenance=ANNOTATION_PROVENANCE,
                        annotation_method=ANNOTATION_METHOD,
                        parser_version=MORPHOLOGY_PARSER_VERSION,
                    )
                )
    return out


def _lemma_ids(correction: str | None) -> set[str]:
    """The annotation's stable lemma identifiers, e.g. ``#lemma_agni_79``.

    A token may carry several when the annotators could not choose between two lexical
    entries (``dyú- ~ div-``). That ambiguity is kept, not collapsed.
    """
    if not correction:
        return set()
    return {part.lstrip("#") for part in correction.split() if part.strip()}


def load_morphology_artifacts(index_path: Path) -> list[MorphologyArtifact]:
    """Load the pinned artifact index. The build never scans a mutable directory."""
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    artifacts = [
        MorphologyArtifact(
            mandala=int(entry["mandala"]),
            artifact_id=str(entry["artifact_id"]),
            snapshot_path=Path(str(entry["snapshot_path"])),
            snapshot_id=str(entry["snapshot_id"]),
            sha256=str(entry["sha256"]),
            url=str(entry["url"]),
        )
        for entry in entries
    ]
    commits = {artifact.url.split("/vedaweb-data/")[1].split("/")[0] for artifact in artifacts}
    if commits != {MORPHOLOGY_COMMIT_SHA}:
        raise ValueError(f"morphology artifacts must all come from {MORPHOLOGY_COMMIT_SHA}")
    return sorted(artifacts, key=lambda artifact: artifact.mandala)
