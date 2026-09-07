"""Build the FULL production canonical Shukla Yajurveda (Vajasaneyi Madhyandina) release.

    .venv/Scripts/python.exe scripts/build_yajurveda_canonical.py
    .venv/Scripts/python.exe scripts/build_yajurveda_canonical.py --no-verify-determinism

Why this exists next to ``scripts/build_yajurveda_pilot.py``
============================================================
The pilot is a sealed four-adhyaya v1 artifact at ``data/canonical/yajurveda_pilot_v1``.
It is not edited and not deleted here. This script writes a *different* dataset id at
full scale on parser ``wikisource-sa-vsm-v2``, and it sits on the shared release core in
:mod:`vedagraph.release` rather than re-implementing selection, gating and emission.

The one thing this build refuses to do
======================================
It does not manufacture a ``PRIMARY_TEXT`` layer. ``data/registry/text_versions.yaml``
registers the accented layer as ``EXTRACTED_FROM_CONTAINER`` and the unaccented layer as
``PARALLEL_TEXT``, and those roles are read from the registry and stamped verbatim onto
every emitted row. The accented layer is the complete one, but a subset of its unit
boundaries is inferred rather than declared by the source, so calling it primary would
make an interpretive segmentation canonical. ``allowed_roles`` is therefore passed
EXPLICITLY at the :func:`select_primary_text_version` call site: the concession is
visible at the point it is made instead of hidden in a default.

Four numbers, never one
=======================
Because the layer is honestly mixed, coverage is reported as four distinct figures --
source-declared units, inference-derived units, variant-bearing units and review items --
and per-record boundary provenance is emitted as a ``SourceAssertion`` on every accented
address. A single blended "coverage %" would hide exactly the property that decides the
layer's role.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from vedagraph.config.registry import (
    load_source_artifacts,
    load_sources,
    load_text_versions,
    load_works,
)
from vedagraph.identity import (
    uuid_for_urn,
    vsm_adhyaya_identity,
    vsm_adhyaya_key,
    vsm_mantra_identity,
)
from vedagraph.ingest.adapters.yajurveda_apparatus import (
    RISHI_INDEX_TITLE,
    SARVANUKRAMANI_TITLE,
    RishiIndexAdapter,
    RishiIndexParse,
)
from vedagraph.ingest.adapters.yajurveda_wikisource import (
    PARSER_VERSION,
    AdhyayaParse,
    ParseFailure,
    YajurvedaWikisourceAdapter,
    adhyaya_title,
    canonical_page_url,
    content_api_url,
)
from vedagraph.models import (
    Citation,
    Passage,
    PassageReferentBinding,
    QAIssue,
    RawSnapshotMetadata,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
    Work,
)
from vedagraph.models.core import MetadataScope
from vedagraph.models.enums import (
    AssertionStatus,
    EntityType,
    MetadataPredicate,
    PassageStatus,
    QASeverity,
    QAStatus,
    ScopeType,
    TextForm,
    TextRole,
)
from vedagraph.normalize import has_vedic_accents, normalize_nfc
from vedagraph.referent import duplicate_referents, fingerprint_of, text_fingerprints
from vedagraph.release import (
    CanonicalRelease,
    gate_referents,
    orphan_provenance_claims,
    referent_verdict_counts,
    select_primary_text_version,
    write_json,
    write_release,
)
from vedagraph.storage import read_jsonl

WORK_ID = "VG:WORK:YV:VSM"
RUN_ID = "FULL_SV_YV_AV_CANONICAL_INGESTION"
# Git-tracked because data/derived/** is gitignored, so a baseline written there
# would not survive a clean checkout and so would not be a baseline at all.
REFERENT_BASELINE = Path("tests/fixtures/identity/vsm_referent_baseline.jsonl")
SOURCE_ID = "WIKISOURCE_SA"
SAMHITA_ARTIFACT_ID = "WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI"
RISHI_ARTIFACT_ID = "WIKISOURCE_SA.YV.VSM.RISHISUCI"
APPARATUS_PARSER_VERSION = "wikisource-sa-vsm-apparatus-v1"
BUILDER_VERSION = "yajurveda-vsm-canonical-v1"

DEFAULT_CONFIG = Path("data/builds/yajurveda_vsm_v1.yaml")

#: The adapter logs this prefix when an accented run began WITHOUT a source-declared
#: ordinal header, so the unit's start boundary came from the v1 accent-presence
#: fallback instead. It is the discriminator between the two provenance classes below.
ORDINAL_HEADER_ABSENT = "ORDINAL_HEADER_ABSENT"

#: Boundary provenance, carried per accented record. This is the per-record resolution
#: the text-version registry asked for and left unimplemented: the LAYER role stays
#: EXTRACTED_FROM_CONTAINER for everything, while a consumer can still select the units
#: whose boundary the 1929 edition itself declared.
SOURCE_DECLARED = "SOURCE_DECLARED_ORDINAL_HEADER"
INFERENCE_DERIVED = "INFERRED_ACCENT_PRESENCE_FALLBACK"

#: Traditional metadata is stored as the source's own string. No rsi name is resolved to
#: a person entity, merged with a homonym, or normalised across spellings.
ENTITY_RESOLUTION_METHOD = "VERBATIM_SOURCE_STRING_NOT_RESOLVED"

#: Prior research projected this many rsi assertions. It is carried as a CLAIM TO BE
#: CHECKED against the recomputed figure, never as the expected value of a test.
PROJECTED_RISHI_ASSERTIONS = 2106


class BuildError(RuntimeError):
    """The release cannot be assembled from what is on disk."""


# ---------------------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TranslationSourceSpec:
    """One aligned translation artifact this release is willing to ingest.

    The list is empty today. The slot is live rather than decorative: a declared source
    is read, and a declared source that cannot be read stops the build. That is what
    makes "zero translations" a reported gap instead of an unnoticed omission.
    """

    source_id: str
    source_artifact_id: str
    jsonl_path: Path


@dataclass(frozen=True)
class VsmReleaseConfig:
    config_version: str
    dataset_id: str
    release_version: str
    work_id: str
    section_level: str
    mantra_level: str
    selected_sections: tuple[int, ...]
    primary_text_version: str
    parallel_text_versions: tuple[str, ...]
    forbidden_text_version_ids: tuple[str, ...]
    expected_artifact_id: str
    metadata_sources: tuple[str, ...]
    translation_sources: tuple[TranslationSourceSpec, ...]
    audio_sources: tuple[str, ...]
    reconciliation_policy_version: str
    segmentation_policy_version: str
    raw_root: Path
    output_location: Path
    build_timestamp: datetime

    @classmethod
    def load(cls, path: Path) -> VsmReleaseConfig:
        payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        if payload["work_id"] != WORK_ID:
            raise BuildError(f"this builder only builds {WORK_ID}")
        sections = tuple(sorted({int(value) for value in payload["selected_sections"]}))
        if not sections:
            raise BuildError("selected_sections must not be empty")
        out_of_range = [value for value in sections if not 1 <= value <= 40]
        if out_of_range:
            raise BuildError(f"adhyaya out of range for the Vajasaneyi Samhita: {out_of_range}")
        translations = tuple(
            TranslationSourceSpec(
                source_id=str(entry["source_id"]),
                source_artifact_id=str(entry["source_artifact_id"]),
                jsonl_path=Path(str(entry["jsonl_path"])),
            )
            for entry in payload.get("translation_sources") or []
        )
        return cls(
            config_version=str(payload["config_version"]),
            dataset_id=str(payload["dataset_id"]),
            release_version=str(payload["release_version"]),
            work_id=str(payload["work_id"]),
            section_level=str(payload["section_level"]),
            mantra_level=str(payload["mantra_level"]),
            selected_sections=sections,
            primary_text_version=str(payload["primary_text_version"]),
            parallel_text_versions=tuple(
                str(value) for value in payload.get("parallel_text_versions") or []
            ),
            forbidden_text_version_ids=tuple(
                str(value) for value in payload.get("forbidden_text_version_ids") or []
            ),
            expected_artifact_id=str(payload["expected_artifact_id"]),
            metadata_sources=tuple(str(value) for value in payload.get("metadata_sources") or []),
            translation_sources=translations,
            audio_sources=tuple(str(value) for value in payload.get("audio_sources") or []),
            reconciliation_policy_version=str(payload["reconciliation_policy_version"]),
            segmentation_policy_version=str(payload["segmentation_policy_version"]),
            raw_root=Path(str(payload["raw_root"])),
            output_location=Path(str(payload["output_location"])),
            build_timestamp=_as_datetime(payload["build_timestamp"]),
        )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value))


# ---------------------------------------------------------------------------------------
# snapshots and registry
# ---------------------------------------------------------------------------------------


def _snapshot_index(raw_root: Path) -> dict[str, tuple[Path, RawSnapshotMetadata]]:
    """Map retrieval URL -> (content path, metadata), re-verifying every digest."""
    if not raw_root.exists():
        raise BuildError(
            f"no raw snapshot root at {raw_root}; run scripts/fetch_yajurveda_wikisource.py"
        )
    index: dict[str, tuple[Path, RawSnapshotMetadata]] = {}
    for metadata_path in sorted(raw_root.glob("**/*.metadata.json")):
        metadata = RawSnapshotMetadata.model_validate_json(metadata_path.read_bytes())
        content_path = metadata_path.with_name(metadata.filename)
        if not content_path.exists():
            continue
        if sha256(content_path.read_bytes()).hexdigest() != metadata.sha256:
            raise BuildError(f"snapshot {content_path} does not match its recorded sha256")
        index[str(metadata.retrieval_url)] = (content_path, metadata)
    return index


def _registry_work() -> Work:
    for work in load_works():
        if work.work_id == WORK_ID:
            return work
    raise BuildError(f"{WORK_ID} is not declared in data/registry/works.yaml")


def _registry_source() -> Source:
    """The REGISTERED source record. Rights are read, never constructed here."""
    for source in load_sources():
        if source.source_id == SOURCE_ID:
            return source
    raise BuildError(
        f"{SOURCE_ID} is not declared in data/registry/sources.yaml. Request the entry "
        "from the rights authority; do not construct one here."
    )


def _registry_artifacts() -> list[SourceArtifact]:
    declared = {artifact.artifact_id: artifact for artifact in load_source_artifacts()}
    missing = [key for key in (SAMHITA_ARTIFACT_ID, RISHI_ARTIFACT_ID) if key not in declared]
    if missing:
        raise BuildError(
            "these artifact ids are not declared in data/registry/source_artifacts.yaml: "
            f"{missing}. Request them from the rights authority; do not construct them here."
        )
    return [declared[SAMHITA_ARTIFACT_ID], declared[RISHI_ARTIFACT_ID]]


def registry_text_roles(version_ids: tuple[str, ...]) -> dict[str, TextRole]:
    """Take each layer's role FROM the registry. The build must not decide this.

    ``TextRole`` is a permission statement about how VedaGraph may use a representation,
    so choosing it in build code asserts at a level the rights and provenance authority
    owns. An id the registry does not declare falls back to ``COMPARISON_ONLY``, the most
    restrictive sensible role, never to something permissive.
    """
    declared = {item.text_version_id: item.text_role for item in load_text_versions()}
    return {
        version_id: declared.get(version_id, TextRole.COMPARISON_ONLY) for version_id in version_ids
    }


def _registry_rights(version_ids: tuple[str, ...]) -> dict[str, str]:
    declared = {item.text_version_id: item.normalized_rights for item in load_text_versions()}
    return {
        version_id: declared[version_id].value
        for version_id in version_ids
        if version_id in declared
    }


def _derived_uuid(kind: str, *parts: object) -> UUID:
    return uuid_for_urn(f"urn:vedagraph:{kind}:{':'.join(str(part) for part in parts)}")


# ---------------------------------------------------------------------------------------
# boundary provenance
# ---------------------------------------------------------------------------------------


def boundary_provenance(parse: AdhyayaParse) -> tuple[dict[int, str], list[ParseFailure]]:
    """Attribute each accented unit's start boundary to the source or to inference.

    The adapter reports an ``ORDINAL_HEADER_ABSENT`` :class:`ParseFailure` whenever an
    accented run began with no declared ordinal header, but it reports the offending
    LINE, not the mantra number, so the failure cannot be joined to a record by key.

    The join is BY SOURCE LINE. The adapter now records, for every accented record, the
    line its run opened on, and the failure is emitted at exactly that moment with the same
    ``line_number`` -- so the two identify the same run by construction.

    CORRECTED after an adversarial review. The previous implementation matched on
    ``record.text.startswith(failure.line)`` with a monotonically advancing cursor,
    justified on the grounds that both sequences are in content order. They are, and the
    join was still wrong: in adhyaya 11 the sole fallback belongs to VSM 11.28, whose
    printed header lacks its terminal danda, but VSM 11.9 opens with the SAME 63-character
    formula and sits earlier, so the greedy earliest match claimed it. The shipped result
    marked 11.9 inference-derived and 11.28 source-declared -- both backwards, on the exact
    pair the docstring claimed to resolve. Aggregate counts were unaffected, so a
    count-only test stayed green over two wrong records. A line number is an identity; a
    text prefix is a guess that happens to be usually right.

    A fallback matching NO record is returned unattributed rather than forced onto the
    nearest one. Those are runs of accented commentary prose that never became a record;
    silently assigning them would overstate the inference-derived count.
    """
    numbers = [int(record.hierarchy["mantra"]) for record in parse.accented]
    provenance: dict[int, str] = dict.fromkeys(numbers, SOURCE_DECLARED)
    by_start_line = {
        line: mantra for mantra, line in parse.accented_start_lines.items() if line >= 0
    }
    unattributed: list[ParseFailure] = []
    for failure in parse.failures:
        if not failure.reason.startswith(ORDINAL_HEADER_ABSENT):
            continue
        mantra = by_start_line.get(failure.line_number)
        if mantra is None or mantra not in provenance:
            unattributed.append(failure)
            continue
        provenance[mantra] = INFERENCE_DERIVED
    return provenance, unattributed


# ---------------------------------------------------------------------------------------
# assembled result
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LayerStatistics:
    """The four figures this release refuses to merge into one coverage number."""

    #: Units whose start boundary the 1929 edition itself declared with an ordinal header.
    source_declared_units: int
    #: Units whose boundary is the adapter's accent-presence inference (v1 fallback).
    #: These are still EXTRACTED_FROM_CONTAINER and still source-faithful in TEXT; what
    #: they lack is a source-declared BOUNDARY.
    inference_derived_units: int
    #: Addresses for which the page prints more than one reading.
    variant_bearing_units: int
    #: Rows this release marks NEEDS_REVIEW, i.e. not settled without recorded human work.
    review_items: int

    def as_dict(self) -> dict[str, int]:
        return {
            "source_declared_units": self.source_declared_units,
            "inference_derived_units": self.inference_derived_units,
            "variant_bearing_units": self.variant_bearing_units,
            "review_items": self.review_items,
        }


@dataclass
class BuildOutcome:
    release: CanonicalRelease
    statistics: LayerStatistics
    snapshot_ids: list[str]
    raw_snapshot_hashes: dict[str, str]
    report: dict[str, Any] = field(default_factory=dict)
    digests: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------------------
# the build
# ---------------------------------------------------------------------------------------


def _load_translations(config: VsmReleaseConfig, known_passage_ids: set[UUID]) -> list[Translation]:
    """Read every declared aligned translation, or return none because none is declared.

    Griffith 1899 is public domain by age and is being acquired separately. Until an
    aligned artifact exists this returns ``[]`` and the release writes a zero-length
    ``translations.jsonl`` that the manifest counts, so absence is stated rather than
    implied. Fabricating coverage from an unaligned OCR would be worse than the gap.
    """
    translations: list[Translation] = []
    for spec in config.translation_sources:
        if not spec.jsonl_path.exists():
            raise BuildError(
                f"translation source {spec.source_artifact_id} declares "
                f"{spec.jsonl_path}, which does not exist. The build STOPS rather than "
                "releasing with a silently missing translation layer."
            )
        for record in read_jsonl(spec.jsonl_path, Translation):
            if record.passage_id not in known_passage_ids:
                raise BuildError(
                    f"translation {record.translation_id} targets passage "
                    f"{record.passage_id}, which this release does not contain. "
                    "Translations align by the translation's own printed numbering, "
                    "never by sequence position."
                )
            translations.append(record)
    translations.sort(key=lambda item: (str(item.passage_id), item.translator))
    return translations


def assemble(config: VsmReleaseConfig, *, output_root: Path) -> BuildOutcome:
    """Parse every selected adhyaya and assemble the release in memory."""
    snapshots = _snapshot_index(config.raw_root)
    adapter = YajurvedaWikisourceAdapter(source_artifact_id=SAMHITA_ARTIFACT_ID)

    registry_work = _registry_work()
    registry_source = _registry_source()
    registry_artifacts = _registry_artifacts()

    # SELECTION. allowed_roles is passed explicitly and it deliberately does NOT include
    # PRIMARY_TEXT: this work has no primary layer, and relabelling the accented layer to
    # make the statistics uniform is a forbidden shortcut, not a fix.
    descriptor = select_primary_text_version(
        config.primary_text_version,
        work_id=WORK_ID,
        expected_artifact_id=config.expected_artifact_id,
        forbidden_text_version_ids=config.forbidden_text_version_ids,
        allowed_roles=(TextRole.EXTRACTED_FROM_CONTAINER,),
    )

    layer_ids = (config.primary_text_version, *config.parallel_text_versions)
    roles = registry_text_roles(layer_ids)
    rights = _registry_rights(layer_ids)
    unregistered = sorted(set(layer_ids) - set(rights))

    parses: dict[int, AdhyayaParse] = {}
    snapshot_ids: list[str] = []
    raw_hashes: dict[str, str] = {}
    for adhyaya in config.selected_sections:
        url = content_api_url(adhyaya_title(adhyaya))
        if url not in snapshots:
            raise BuildError(
                f"no snapshot for adhyaya {adhyaya}; run scripts/fetch_yajurveda_wikisource.py"
            )
        path, metadata = snapshots[url]
        parses[adhyaya] = adapter.parse_adhyaya(path, snapshot_id=metadata.snapshot_id)
        snapshot_ids.append(metadata.snapshot_id)
        raw_hashes[metadata.snapshot_id] = metadata.sha256

    rishi_parse: RishiIndexParse | None = None
    if "RISHI_INDEX" in config.metadata_sources:
        url = content_api_url(RISHI_INDEX_TITLE)
        if url not in snapshots:
            raise BuildError(f"no snapshot for the rsi index page {RISHI_INDEX_TITLE}")
        path, metadata = snapshots[url]
        rishi_parse = RishiIndexAdapter().parse_rishi_index(path)
        snapshot_ids.append(metadata.snapshot_id)
        raw_hashes[metadata.snapshot_id] = metadata.sha256

    passages: list[Passage] = []
    texts: list[TextVersion] = []
    citations: list[Citation] = []
    assertions: list[SourceAssertion] = []
    metadata_rows: list[TraditionalMetadataAssertion] = []
    bindings: list[PassageReferentBinding] = []
    issues: list[QAIssue] = []

    provenance_counts: Counter[str] = Counter()
    intervention_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    unattributed_fallbacks: list[dict[str, Any]] = []
    per_adhyaya: list[dict[str, int]] = []
    variant_bearing: list[str] = []

    for adhyaya in config.selected_sections:
        parse = parses[adhyaya]
        section_key, section_urn, section_id = vsm_adhyaya_identity(adhyaya)
        passages.append(
            Passage(
                entity_id=section_id,
                canonical_key=section_key,
                canonical_urn=section_urn,
                entity_type=EntityType.SECTION,
                work_id=WORK_ID,
                hierarchy={"adhyaya": adhyaya},
                canonical_citation=f"VSM {adhyaya}",
                sequence_in_parent=adhyaya,
                native_labels=[config.section_level],
                structural_path=[str(adhyaya)],
                status=PassageStatus.CANONICAL,
            )
        )

        accented = {
            int(record.hierarchy["mantra"]): record.text_original for record in parse.accented
        }
        unaccented = {
            int(record.hierarchy["mantra"]): record.text_original for record in parse.samhita
        }
        by_version = {
            config.primary_text_version: accented,
            **{version: unaccented for version in config.parallel_text_versions},
        }
        inventory = sorted(set(accented) | set(unaccented))

        provenance, unattributed = boundary_provenance(parse)
        for failure in unattributed:
            unattributed_fallbacks.append(
                {
                    "adhyaya": adhyaya,
                    "line_number": failure.line_number,
                    "line": failure.line,
                }
            )
        for failure in parse.failures:
            failure_counts[failure.reason.split(":")[0]] += 1

        for mantra in inventory:
            key, urn, entity_id = vsm_mantra_identity(adhyaya, mantra)
            passages.append(
                Passage(
                    entity_id=entity_id,
                    canonical_key=key,
                    canonical_urn=urn,
                    entity_type=EntityType.MANTRA,
                    work_id=WORK_ID,
                    hierarchy={"adhyaya": adhyaya, "mantra": mantra},
                    canonical_citation=f"VSM {adhyaya}.{mantra}",
                    parent_key=section_key,
                    sequence_in_parent=mantra,
                    native_labels=[config.section_level, config.mantra_level],
                    structural_path=[str(adhyaya), str(mantra)],
                    status=PassageStatus.CANONICAL,
                )
            )
            citations.append(
                Citation(
                    citation_id=_derived_uuid("citation", key, "VSM"),
                    passage_id=entity_id,
                    label=f"VSM {adhyaya}.{mantra}",
                    system="VSM_ADHYAYA_MANTRA",
                    source_id=SOURCE_ID,
                    is_canonical=True,
                )
            )
            annotation = parse.alternate_citations.get(mantra)
            if annotation:
                # VSM 40 labels every mantra with the Kanva-recension Isavasya Upanisad
                # number. An alternate system stated by the source: recorded as data,
                # never as this work's canonical address.
                citations.append(
                    Citation(
                        citation_id=_derived_uuid("citation", key, "SOURCE_CROSS_REFERENCE"),
                        passage_id=entity_id,
                        label=annotation,
                        system="SOURCE_CROSS_REFERENCE",
                        source_id=SOURCE_ID,
                        is_canonical=False,
                    )
                )

            locator = f"{parse.revision.resolved_title}#{adhyaya}.{mantra}"
            for version_id, layer in by_version.items():
                text = layer.get(mantra)
                if text is None:
                    continue
                normalized = normalize_nfc(text)
                texts.append(
                    TextVersion(
                        text_id=_derived_uuid("text", key, version_id),
                        passage_id=entity_id,
                        language="sa",
                        script="Devanagari",
                        text_form=TextForm.SAMHITA,
                        text_role=roles[version_id],
                        text_version_id=version_id,
                        text_original=text,
                        text_nfc=normalized,
                        content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
                        accented=has_vedic_accents(text),
                        source_id=SOURCE_ID,
                        source_artifact_id=SAMHITA_ARTIFACT_ID,
                        source_locator=locator,
                        rights_status=descriptor.normalized_rights,
                    )
                )

            primary_text = accented.get(mantra)
            if primary_text is None:
                # Cannot happen while the accented layer is the complete one, but a
                # release must not assume its own coverage claim.
                issues.append(
                    _issue(
                        "YV-PRIMARY-LAYER-MISSING-ADDRESS",
                        QASeverity.ERROR,
                        f"VSM {adhyaya}.{mantra} has no reading in the leading layer "
                        f"{config.primary_text_version}",
                        entity=key,
                    )
                )
                continue

            unit_provenance = provenance[mantra]
            provenance_counts[unit_provenance] += 1
            assertions.append(
                SourceAssertion(
                    assertion_id=_derived_uuid("assertion", key, "BOUNDARY_PROVENANCE"),
                    subject_id=key,
                    predicate="ACCENTED_BOUNDARY_PROVENANCE",
                    value={
                        "text_version_id": config.primary_text_version,
                        "text_role": roles[config.primary_text_version].value,
                        "boundary_provenance": unit_provenance,
                        "segmentation_policy_version": config.segmentation_policy_version,
                    },
                    source_id=SOURCE_ID,
                    source_artifact_id=SAMHITA_ARTIFACT_ID,
                    source_locator=locator,
                    status=(
                        AssertionStatus.ACCEPTED
                        if unit_provenance == SOURCE_DECLARED
                        else AssertionStatus.NEEDS_REVIEW
                    ),
                    evidence=(
                        "The 1929 Nirnaya Sagara edition prints a Sanskrit ordinal header "
                        "before each accented mula quotation. Where the header is present "
                        "the unit boundary is the source's own declaration; where it is "
                        "absent the boundary is the adapter's accent-presence inference "
                        "and is reported as such rather than passing silently."
                    ),
                )
            )

            raw_digest, comparison_digest = text_fingerprints(primary_text)
            bindings.append(
                PassageReferentBinding(
                    canonical_key=key,
                    canonical_urn=urn,
                    entity_id=entity_id,
                    work_id=WORK_ID,
                    structural_coordinates={"adhyaya": adhyaya, "mantra": mantra},
                    source_id=SOURCE_ID,
                    source_artifact_id=SAMHITA_ARTIFACT_ID,
                    source_locator=locator,
                    source_revision_id=parse.revision.revision_id,
                    source_snapshot_sha256=None,
                    text_sha256=raw_digest,
                    comparison_sha256=comparison_digest,
                    source_verse_marker=mantra,
                    segmentation_policy_version=config.segmentation_policy_version,
                    parser_version=PARSER_VERSION,
                )
            )

        # Layer divergence is data. Recorded, never reconciled, never blended.
        only_primary = sorted(set(accented) - set(unaccented))
        if only_primary:
            issues.append(
                _issue(
                    "YV-LAYER-DIVERGENCE",
                    QASeverity.WARNING,
                    f"adhyaya {adhyaya}: {len(only_primary)} address(es) are carried only "
                    f"by {config.primary_text_version} and are absent from the direct "
                    "unaccented transcription",
                    entity=section_key,
                    details={"only_in_leading_layer": only_primary},
                )
            )

        for mantra, count in parse.accented_collisions.items():
            variant_bearing.append(f"VSM {adhyaya}.{mantra}")
            issues.append(
                _issue(
                    "YV-VARIANT-READING-UNRESOLVED",
                    QASeverity.WARNING,
                    f"the page prints VSM {adhyaya}.{mantra} {count} times with differing "
                    "readings. The FIRST is the record; every later reading is preserved "
                    "in full as an EDITORIAL_INTERVENTION_SECOND_READING assertion. No "
                    "winner is chosen by this build.",
                    entity=vsm_mantra_identity(adhyaya, mantra)[0],
                    details={"printed_readings": count},
                )
            )

        for index, intervention in enumerate(parse.editorial_interventions):
            intervention_counts[intervention.kind] += 1
            target = vsm_mantra_identity(intervention.adhyaya, intervention.mantra)[0]
            assertions.append(
                SourceAssertion(
                    assertion_id=_derived_uuid(
                        "assertion", target, "EDITORIAL", intervention.kind, index
                    ),
                    subject_id=target,
                    predicate=f"EDITORIAL_INTERVENTION_{intervention.kind}",
                    value={
                        # FULL text, never truncated. For SECOND_READING this field IS the
                        # second attested reading; truncating it would destroy the variant
                        # while appearing to preserve it.
                        "text": intervention.removed,
                        "reason": intervention.reason,
                        "declared_status": intervention.status or "RECORDED",
                    },
                    source_id=SOURCE_ID,
                    source_artifact_id=SAMHITA_ARTIFACT_ID,
                    source_locator=(
                        f"{parse.revision.resolved_title}"
                        f"#{intervention.adhyaya}.{intervention.mantra}"
                    ),
                    status=AssertionStatus.NEEDS_REVIEW,
                    evidence=(
                        "Every departure from the source bytes is recorded so it is "
                        "reviewable and reversible rather than implicit in parser code."
                    ),
                )
            )

        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", section_key, "REVISION"),
                subject_id=section_key,
                predicate="SOURCE_REVISION",
                value={
                    "requested_title": parse.revision.requested_title,
                    "resolved_title": parse.revision.resolved_title,
                    "redirected": parse.revision.redirected,
                    "page_id": parse.revision.page_id,
                    "revision_id": parse.revision.revision_id,
                    "revision_timestamp": parse.revision.revision_timestamp,
                    "canonical_url": canonical_page_url(parse.revision.resolved_title),
                },
                source_id=SOURCE_ID,
                source_artifact_id=SAMHITA_ARTIFACT_ID,
                source_locator=parse.revision.resolved_title,
                status=AssertionStatus.ACCEPTED,
                evidence="MediaWiki action=query&prop=revisions response",
            )
        )

        per_adhyaya.append(
            {
                "adhyaya": adhyaya,
                "addresses": len(inventory),
                "leading_layer": len(accented),
                "parallel_layer": len(unaccented),
                "source_declared": sum(
                    1 for value in provenance.values() if value == SOURCE_DECLARED
                ),
                "inference_derived": sum(
                    1 for value in provenance.values() if value == INFERENCE_DERIVED
                ),
                "parse_failures": len(parse.failures),
            }
        )

    # -- traditional metadata --------------------------------------------------------
    # MANTRA keys only. Counting the 40 SECTION keys here would inflate the "addresses
    # without an rsi" figure by 40 and make a real gap look worse than it is.
    known_keys = {
        passage.canonical_key for passage in passages if passage.entity_type == EntityType.MANTRA
    }
    metadata_rows, metadata_provenance, rishi_report = _rishi_assertions(
        rishi_parse, known_keys=known_keys
    )
    assertions.extend(metadata_provenance)
    issues.extend(_rishi_issues(rishi_parse, rishi_report, known_keys=known_keys))

    # -- work-level statements --------------------------------------------------------
    mantra_passages = [item for item in passages if item.entity_type == EntityType.MANTRA]
    statistics = LayerStatistics(
        source_declared_units=provenance_counts[SOURCE_DECLARED],
        inference_derived_units=provenance_counts[INFERENCE_DERIVED],
        variant_bearing_units=len(variant_bearing),
        review_items=sum(1 for item in assertions if item.status == AssertionStatus.NEEDS_REVIEW),
    )

    assertions.extend(
        _work_level_assertions(
            config,
            statistics=statistics,
            roles=roles,
            per_adhyaya=per_adhyaya,
            address_count=len(mantra_passages),
            leading_layer_count=sum(
                1 for item in texts if item.text_version_id == config.primary_text_version
            ),
            parallel_layer_count=sum(
                1 for item in texts if item.text_version_id in set(config.parallel_text_versions)
            ),
        )
    )
    issues.extend(_gap_issues(config, statistics, unattributed_fallbacks, failure_counts))

    translations = _load_translations(config, {item.entity_id for item in mantra_passages})

    # -- ordering, then integrity ------------------------------------------------------
    passages.sort(
        key=lambda item: (
            int(item.hierarchy["adhyaya"]),
            0 if item.entity_type == EntityType.SECTION else 1,
            int(item.hierarchy.get("mantra", 0)),
        )
    )
    texts.sort(key=lambda item: (item.source_locator, item.text_version_id or ""))
    citations.sort(key=lambda item: (str(item.passage_id), item.system, item.label))
    metadata_rows.sort(key=lambda item: (str(item.scope.passage_id), item.value))
    assertions.sort(key=lambda item: (item.subject_id, item.predicate, str(item.assertion_id)))
    bindings.sort(key=lambda item: item.canonical_key)
    issues.sort(key=lambda item: (item.check_id, item.entity_id or "", str(item.issue_id)))

    _assert_unique("passage canonical_key", [item.canonical_key for item in passages])
    _assert_unique("text_id", [str(item.text_id) for item in texts])
    _assert_unique("citation_id", [str(item.citation_id) for item in citations])
    _assert_unique("assertion_id", [str(item.assertion_id) for item in assertions])
    _assert_unique(
        "traditional metadata assertion_id", [str(item.assertion_id) for item in metadata_rows]
    )
    _assert_unique("qa issue_id", [str(item.issue_id) for item in issues])

    shared = duplicate_referents([fingerprint_of(binding) for binding in bindings])
    if shared:
        raise BuildError(
            f"{len(shared)} source occurrence(s) are claimed by more than one canonical "
            "key, so at least one key does not denote a single verse"
        )

    # Referent stability against the committed baseline. Uniqueness above proves no two
    # keys share an occurrence WITHIN this build; it says nothing about whether a key
    # still denotes what it denoted last time. That second property is the one UUID
    # determinism cannot see, because the UUID is a function of the URN alone -- a key can
    # silently start pointing at a different mantra with every existing gate still green.
    referent_deltas = gate_referents(
        bindings,
        baseline_path=REFERENT_BASELINE,
        licensing_run=RUN_ID,
    )
    drift_verdicts = referent_verdict_counts(referent_deltas)

    orphans = orphan_provenance_claims(
        assertions,
        known_source_ids={SOURCE_ID},
        known_artifact_ids={SAMHITA_ARTIFACT_ID, RISHI_ARTIFACT_ID},
    )
    if orphans:
        raise BuildError(
            f"{len(orphans)} assertion(s) carry unresolvable provenance: {orphans[:5]}"
        )

    release = CanonicalRelease(
        dataset_id=config.dataset_id,
        work_id=WORK_ID,
        release_version=config.release_version,
        output_root=output_root,
        works=[registry_work],
        passages=passages,
        text_versions=texts,
        translations=translations,
        traditional_metadata=metadata_rows,
        sources=[registry_source],
        source_artifacts=registry_artifacts,
        source_assertions=assertions,
        citations=citations,
        audio_recordings=[],
        audio_segments=[],
        qa_issues=issues,
        referent_bindings=bindings,
    )

    report: dict[str, Any] = {
        "dataset_id": config.dataset_id,
        "release_version": config.release_version,
        "work_id": WORK_ID,
        "parser_version": PARSER_VERSION,
        "builder_version": BUILDER_VERSION,
        "adhyaya_count": sum(1 for item in passages if item.entity_type == EntityType.SECTION),
        "address_count": len(mantra_passages),
        "layer_statistics": statistics.as_dict(),
        "layer_statistics_note": (
            "These four numbers are deliberately NOT merged. source_declared_units + "
            "inference_derived_units == address_count; the split is what decides the "
            "layer's role and a single coverage figure would erase it."
        ),
        "text_roles_from_registry": {key: value.value for key, value in roles.items()},
        "has_primary_text_layer": ("YES" if TextRole.PRIMARY_TEXT in set(roles.values()) else "NO"),
        "unregistered_text_versions": unregistered,
        "per_adhyaya": per_adhyaya,
        "editorial_interventions": dict(sorted(intervention_counts.items())),
        "parse_failures": dict(sorted(failure_counts.items())),
        "unattributed_ordinal_header_fallbacks": unattributed_fallbacks,
        "variant_bearing_addresses": sorted(variant_bearing),
        "referent_drift": drift_verdicts,
        "rishi": rishi_report,
        "record_counts": {
            "passages": len(passages),
            "text_versions": len(texts),
            "citations": len(citations),
            "source_assertions": len(assertions),
            "traditional_metadata": len(metadata_rows),
            "translations": len(translations),
            "referent_bindings": len(bindings),
            "qa_issues": len(issues),
            "audio_recordings": 0,
            "audio_segments": 0,
        },
        "qa_issue_counts": dict(sorted(Counter(item.check_id for item in issues).items())),
        "gaps": {
            "english_translation": (
                f"PARTIAL: {len(translations)} of {len(mantra_passages)} mantras carry "
                "Griffith 1899 (public domain by age). The shortfall is reported as a "
                "count rather than described, so it cannot drift out of step with the "
                "records. Alignment is proven from Griffith's OWN PRINTED verse numbers, "
                "never from position; the largest single gap is the book-12 spine "
                "divergence, where the print carries one verse twice and a naive "
                "printed-number map would have put the wrong translation on 21 keys."
            ),
            "english_translation_missing": len(mantra_passages) - len(translations),
            "devata": (
                "NOT ASSERTED. No approved deterministic per-mantra devata source exists "
                "for this work. The Sukla YV Sarvanukramasutra's devata co-domain "
                "includes ritual implements, so Rigvedic practice does not transfer."
            ),
            "chandas": (
                "NOT ASSERTED. The same sutra states that many yajus have no metre at "
                "all, so absence here is a source property and not a gap to be filled."
            ),
            "sarvanukramani": (
                f"{SARVANUKRAMANI_TITLE} is snapshotted as evidence and deliberately NOT "
                "machine-resolved: it is continuous sutra prose grouped by anuvaka."
            ),
            "audio": "REFERENCE ONLY. No recording is held and no segment is aligned.",
        },
    }

    return BuildOutcome(
        release=release,
        statistics=statistics,
        snapshot_ids=sorted(set(snapshot_ids)),
        raw_snapshot_hashes=dict(sorted(raw_hashes.items())),
        report=report,
    )


def _issue(
    check_id: str,
    severity: QASeverity,
    message: str,
    *,
    entity: str | None = None,
    details: dict[str, Any] | None = None,
) -> QAIssue:
    return QAIssue(
        issue_id=_derived_uuid("qa", check_id, entity or WORK_ID, message),
        check_id=check_id,
        severity=severity,
        message=message,
        entity_id=entity,
        details=details or {},
    )


def _assert_unique(label: str, values: list[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise BuildError(f"{len(duplicates)} duplicate {label}: {duplicates[:5]}")


def _rishi_assertions(
    rishi_parse: RishiIndexParse | None, *, known_keys: set[str]
) -> tuple[list[TraditionalMetadataAssertion], list[SourceAssertion], dict[str, Any]]:
    """One assertion per rsi assignment the index actually states, recomputed every build.

    Nothing is inferred and nothing is defaulted. The Sarvanukramasutra names ``vivasvan``
    as a samhita-wide fallback rsi; that default is NOT applied here, because applying it
    would turn 70 addresses the index is silent about into 70 claims the source never made
    at this address.
    """
    rows: list[TraditionalMetadataAssertion] = []
    provenance: list[SourceAssertion] = []
    if rishi_parse is None:
        return rows, provenance, {"parsed": False}

    covered: set[tuple[int, int]] = set()
    off_corpus: list[str] = []
    for item in rishi_parse.assertions:
        key, _urn, entity_id = vsm_mantra_identity(item.adhyaya, item.mantra)
        if key not in known_keys:
            off_corpus.append(f"VSM {item.adhyaya}.{item.mantra}")
            continue
        covered.add((item.adhyaya, item.mantra))
        assertion_id = _derived_uuid("traditional-metadata", key, "HAS_RISHI", item.rishi)
        locator = f"{RISHI_INDEX_TITLE}#L{item.line_number}: {item.source_line}"
        rows.append(
            TraditionalMetadataAssertion(
                assertion_id=assertion_id,
                predicate=MetadataPredicate.HAS_RISHI,
                value=item.rishi,
                scope=MetadataScope(scope_type=ScopeType.SINGLE_MANTRA, passage_id=entity_id),
                source_id=SOURCE_ID,
                source_locator=locator,
                status=AssertionStatus.UNREVIEWED,
                notes=(
                    f"Stated by the edition's own rsi index as {item.scope_note}. "
                    f"entity_resolution_method={ENTITY_RESOLUTION_METHOD}: the name is the "
                    "source string verbatim and is not resolved to a person, merged with a "
                    "homonym or normalised across spellings. devata and chandas are NOT "
                    "asserted for this work; no approved deterministic source exists and "
                    "Rigvedic practice does not transfer to the Yajurveda."
                ),
            )
        )
        provenance.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", key, "RISHI_PROVENANCE", item.rishi),
                subject_id=key,
                predicate="TRADITIONAL_METADATA_PROVENANCE",
                value={
                    "metadata_assertion_id": str(assertion_id),
                    "predicate": MetadataPredicate.HAS_RISHI.value,
                    "value": item.rishi,
                    "scope_type": ScopeType.SINGLE_MANTRA.value,
                    "stated_scope": item.scope_note,
                    "source_line": item.source_line,
                    "line_number": item.line_number,
                    "entity_resolution_method": ENTITY_RESOLUTION_METHOD,
                },
                source_id=SOURCE_ID,
                source_artifact_id=RISHI_ARTIFACT_ID,
                source_locator=locator,
                status=AssertionStatus.UNREVIEWED,
                evidence=(
                    "TraditionalMetadataAssertion carries no artifact field, so the "
                    "artifact, the printed index line and the resolution method are "
                    "carried here. Every metadata row has exactly one of these."
                ),
            )
        )

    ranged = sum(1 for item in rishi_parse.assertions if item.scope_note.startswith("MANTRA_RANGE"))
    report: dict[str, Any] = {
        "parsed": True,
        "computed_assertions": len(rows),
        "projected_assertions_prior_research": PROJECTED_RISHI_ASSERTIONS,
        "difference_vs_projection": len(rows) - PROJECTED_RISHI_ASSERTIONS,
        "projection_status": (
            "The 2,106 figure is a prior CLAIM, not validation truth. The build recomputes "
            "from the source records and reports the recomputed number."
        ),
        "index_rows_read": len(rishi_parse.assertions),
        "rows_off_corpus": sorted(set(off_corpus)),
        "distinct_addresses_covered": len(covered),
        "addresses_with_multiple_rishis": len(
            [
                address
                for address, count in Counter(
                    (item.adhyaya, item.mantra) for item in rishi_parse.assertions
                ).items()
                if count > 1
            ]
        ),
        "assertions_from_a_printed_range": ranged,
        "assertions_from_a_single_mantra_label": len(rishi_parse.assertions) - ranged,
        "adhyayas_covered": rishi_parse.adhyayas_covered,
        "adhyayas_not_covered": sorted(set(range(1, 41)) - set(rishi_parse.adhyayas_covered)),
        "unparsed_index_lines": [
            {"line_number": number, "line": line} for number, line in rishi_parse.unparsed_lines
        ],
        "devata_assertions": 0,
        "chandas_assertions": 0,
    }
    return rows, provenance, report


def _rishi_issues(
    rishi_parse: RishiIndexParse | None,
    report: dict[str, Any],
    *,
    known_keys: set[str],
) -> list[QAIssue]:
    issues: list[QAIssue] = []
    if rishi_parse is None:
        return issues
    for entry in report["unparsed_index_lines"]:
        issues.append(
            _issue(
                "YV-RISHI-INDEX-LINE-UNPARSED",
                QASeverity.WARNING,
                f"rsi index line {entry['line_number']} could not be read as "
                f"'<name> <adhyaya>.<ranges>': {entry['line']}",
                entity=RISHI_ARTIFACT_ID,
                details={"line_number": entry["line_number"]},
            )
        )
    missing = report["adhyayas_not_covered"]
    if missing:
        issues.append(
            _issue(
                "YV-RISHI-ADHYAYA-UNCOVERED",
                QASeverity.ERROR,
                f"the rsi index yields no assignment for adhyaya(s) {missing}. This is a "
                "parse gap traceable to the unreadable index lines above, not a statement "
                "by the source that no rsi exists. It is reported, never defaulted.",
                entity=RISHI_ARTIFACT_ID,
                details={"adhyayas": missing},
            )
        )
    uncovered = len(known_keys) - report["distinct_addresses_covered"]
    issues.append(
        _issue(
            "YV-RISHI-COVERAGE",
            QASeverity.WARNING,
            f"{report['distinct_addresses_covered']} of {len(known_keys)} released mantra "
            f"addresses carry at least one rsi assertion; {uncovered} have none. The "
            "Sarvanukramasutra's samhita-wide vivasvan default is deliberately NOT "
            "applied, because applying it would manufacture claims at addresses the "
            "index is silent about.",
            entity=WORK_ID,
            details={"released_addresses_without_any_rishi": uncovered},
        )
    )
    return issues


def _work_level_assertions(
    config: VsmReleaseConfig,
    *,
    statistics: LayerStatistics,
    roles: dict[str, TextRole],
    per_adhyaya: list[dict[str, int]],
    address_count: int,
    leading_layer_count: int,
    parallel_layer_count: int,
) -> list[SourceAssertion]:
    rows: list[SourceAssertion] = [
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", WORK_ID, "COMPUTED_STRUCTURE"),
            subject_id=WORK_ID,
            predicate="COMPUTED_WORK_STRUCTURE",
            value={
                "adhyaya_count": len(per_adhyaya),
                "address_count": address_count,
                "leading_layer_records": leading_layer_count,
                "parallel_layer_records": parallel_layer_count,
            },
            source_id=SOURCE_ID,
            source_artifact_id=SAMHITA_ARTIFACT_ID,
            source_locator=f"{len(per_adhyaya)} adhyaya snapshots under {config.raw_root}",
            status=AssertionStatus.ACCEPTED,
            evidence=(
                "Computed from every adhyaya snapshot at build time, never quoted. The "
                "address inventory is the UNION of the distinct mantra numbers the two "
                "layers label; only the inventory is unioned and no text is blended. "
                "External cross-checks disagree and are recorded as data: TITUS yields "
                "1974 (VS 2.32 absent there) and the Vedic Heritage Portal yields 1974 "
                "(adhyaya 23 = 64 against 65 elsewhere)."
            ),
        ),
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", WORK_ID, "LAYER_STATISTICS"),
            subject_id=WORK_ID,
            predicate="LAYER_BOUNDARY_STATISTICS",
            value=statistics.as_dict(),
            source_id=SOURCE_ID,
            source_artifact_id=SAMHITA_ARTIFACT_ID,
            source_locator=config.primary_text_version,
            status=AssertionStatus.ACCEPTED,
            evidence=(
                "Four distinct figures, deliberately not merged into one coverage "
                "percentage. The split between source-declared and inference-derived "
                "boundaries is the property that decides this layer's role."
            ),
        ),
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", WORK_ID, "TEXT_ROLE_POLICY"),
            subject_id=WORK_ID,
            predicate="NO_PRIMARY_TEXT_LAYER",
            value={
                "roles_from_registry": {key: value.value for key, value in roles.items()},
                "leading_text_version": config.primary_text_version,
                "consequence": (
                    "No layer of this work is registered PRIMARY_TEXT. The leading layer "
                    "drives coverage, comparison and the referent bindings and must not "
                    "be treated as canonical primary text. Relabelling it to make the "
                    "statistics uniform is forbidden: the accented layer legitimately "
                    "lacks a source-declared boundary at some units, which is an honest "
                    "source property and not a parser defect."
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=SAMHITA_ARTIFACT_ID,
            source_locator="data/registry/text_versions.yaml",
            status=AssertionStatus.ACCEPTED,
            evidence="Roles read from the registry at build time and stamped verbatim.",
        ),
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", WORK_ID, "METADATA_SCOPE"),
            subject_id=WORK_ID,
            predicate="TRADITIONAL_METADATA_SCOPE",
            value={
                "asserted_predicates": [MetadataPredicate.HAS_RISHI.value],
                "not_asserted": [
                    MetadataPredicate.HAS_DEVATA.value,
                    MetadataPredicate.HAS_CHANDAS.value,
                ],
                "reason": (
                    "No approved deterministic per-mantra devata or chandas source exists "
                    "for this work. The Sukla YV Sarvanukramasutra states that many yajus "
                    "have no metre at all and lists ritual implements among the devatas, "
                    "so neither field may be carried over from Rigvedic practice. The "
                    f"{SARVANUKRAMANI_TITLE} page is continuous sutra prose and is "
                    "deliberately not machine-resolved."
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=RISHI_ARTIFACT_ID,
            source_locator=RISHI_INDEX_TITLE,
            status=AssertionStatus.ACCEPTED,
            evidence="Stated as a scope limit so the absence is a finding, not an oversight.",
        ),
    ]
    rows.extend(
        SourceAssertion(
            assertion_id=_derived_uuid(
                "assertion", vsm_adhyaya_key(int(row["adhyaya"])), "COMPUTED_COUNT"
            ),
            subject_id=vsm_adhyaya_key(int(row["adhyaya"])),
            predicate="COMPUTED_MANTRA_COUNT",
            value=row,
            source_id=SOURCE_ID,
            source_artifact_id=SAMHITA_ARTIFACT_ID,
            source_locator=adhyaya_title(int(row["adhyaya"])),
            status=AssertionStatus.ACCEPTED,
            evidence="Distinct mantra numbers labelled by the source in this adhyaya.",
        )
        for row in per_adhyaya
    )
    return rows


def _gap_issues(
    config: VsmReleaseConfig,
    statistics: LayerStatistics,
    unattributed: list[dict[str, Any]],
    failure_counts: Counter[str],
) -> list[QAIssue]:
    issues = [
        _issue(
            "YV-NO-PRIMARY-TEXT-LAYER",
            QASeverity.ERROR,
            "this work has no layer registered PRIMARY_TEXT. The leading layer is "
            f"{config.primary_text_version}, registered EXTRACTED_FROM_CONTAINER. It is "
            "released as such and must not be consumed as canonical primary text.",
            entity=WORK_ID,
        ),
        _issue(
            "YV-BOUNDARY-INFERRED",
            QASeverity.WARNING,
            f"{statistics.inference_derived_units} of "
            f"{statistics.source_declared_units + statistics.inference_derived_units} "
            "accented units have a boundary inferred from accent presence rather than a "
            "source-declared ordinal header. Each carries its own "
            "ACCENTED_BOUNDARY_PROVENANCE assertion at NEEDS_REVIEW.",
            entity=WORK_ID,
        ),
        _issue(
            "YV-TRANSLATION-ABSENT",
            QASeverity.WARNING,
            "no English translation is released. Griffith 1899 is public domain by age "
            "and is being acquired separately; translations.jsonl is written empty rather "
            "than filled with unverifiable alignments.",
            entity=WORK_ID,
        ),
        _issue(
            "YV-DEVATA-NOT-ASSERTED",
            QASeverity.INFO,
            "zero devata assertions. No approved deterministic per-mantra source exists "
            "for this work and none is invented.",
            entity=WORK_ID,
        ),
        _issue(
            "YV-CHANDAS-NOT-ASSERTED",
            QASeverity.INFO,
            "zero chandas assertions. The Sukla YV Sarvanukramasutra states that many "
            "yajus have no metre at all, so absence is a source property here.",
            entity=WORK_ID,
        ),
        _issue(
            "YV-AUDIO-REFERENCE-ONLY",
            QASeverity.INFO,
            "audio is reference-only: no recording is held and no segment is aligned, so "
            "both audio files are written empty.",
            entity=WORK_ID,
        ),
    ]
    for entry in unattributed:
        issues.append(
            _issue(
                "YV-BOUNDARY-FALLBACK-UNATTRIBUTED",
                QASeverity.INFO,
                f"adhyaya {entry['adhyaya']} line {entry['line_number']}: an accented run "
                "began without an ordinal header and produced no record. It is reported "
                "rather than attributed to the nearest mantra, which would overstate the "
                "inference-derived count.",
                entity=vsm_adhyaya_key(int(entry["adhyaya"])),
                details={"line": entry["line"]},
            )
        )
    for reason, count in sorted(failure_counts.items()):
        if reason.startswith(ORDINAL_HEADER_ABSENT):
            continue
        issues.append(
            _issue(
                "YV-PARSE-FAILURE",
                QASeverity.WARNING,
                f"{count} parse failure(s) of class: {reason}",
                entity=WORK_ID,
                details={"count": count},
            )
        )
    return issues


# ---------------------------------------------------------------------------------------
# emission
# ---------------------------------------------------------------------------------------


def build(config: VsmReleaseConfig, config_path: Path, *, output_root: Path) -> BuildOutcome:
    outcome = assemble(config, output_root=output_root)
    manifest, digests = write_release(
        outcome.release,
        built_at=config.build_timestamp,
        source_snapshot_ids=outcome.snapshot_ids,
        source_artifact_ids=[SAMHITA_ARTIFACT_ID, RISHI_ARTIFACT_ID],
        parser_versions={
            "wikisource-sa-vsm": PARSER_VERSION,
            "wikisource-sa-vsm-apparatus": APPARATUS_PARSER_VERSION,
            "builder": BUILDER_VERSION,
        },
        rights_summary={
            SOURCE_ID: _registry_source().rights.status.value,
            **_registry_rights((config.primary_text_version, *config.parallel_text_versions)),
        },
        qa_status=QAStatus.PASSED_WITH_WARNINGS,
        reconciliation_policy_version=config.reconciliation_policy_version,
        build_config_sha256=sha256(config_path.read_bytes()).hexdigest(),
        raw_snapshot_hashes=outcome.raw_snapshot_hashes,
    )
    outcome.digests = digests
    outcome.report["manifest_generated_content_sha256"] = manifest.generated_content_sha256
    write_json(output_root / "reports" / "build_report.json", outcome.report)
    write_json(
        output_root / "reports" / "layer_statistics.json",
        {
            "layer_statistics": outcome.statistics.as_dict(),
            "definitions": {
                "source_declared_units": (
                    "Accented units whose START boundary the 1929 edition declared with "
                    "its own Sanskrit ordinal header."
                ),
                "inference_derived_units": (
                    "Accented units whose boundary came from the accent-presence v1 "
                    "fallback. Source-faithful in TEXT, EXTRACTED_FROM_CONTAINER in "
                    "boundary provenance. Never relabelled PRIMARY_TEXT."
                ),
                "variant_bearing_units": (
                    "Addresses for which the page prints more than one reading. The first "
                    "is the record; every other is preserved in full as evidence."
                ),
                "review_items": (
                    "SourceAssertion rows emitted at NEEDS_REVIEW, i.e. rows that are not "
                    "settled without recorded human philological work."
                ),
            },
            "per_adhyaya": outcome.report["per_adhyaya"],
        },
    )
    write_json(output_root / "reports" / "rishi_index.json", outcome.report["rishi"])
    return outcome


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def verify_determinism(config: VsmReleaseConfig, config_path: Path, first: Path) -> bool:
    """Rebuild into a throwaway root and compare every emitted byte, then clean up."""
    scratch = Path(tempfile.mkdtemp(prefix="yajurveda-vsm-determinism-"))
    try:
        build(config, config_path, output_root=scratch)
        return _tree_digest(first) == _tree_digest(scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--no-verify-determinism", action="store_true", help="skip the second rebuild"
    )
    args = parser.parse_args(argv)

    config = VsmReleaseConfig.load(args.config)
    outcome = build(config, args.config, output_root=config.output_location)
    statistics = outcome.statistics
    report = outcome.report

    print(f"dataset            {config.dataset_id} {config.release_version}")
    print(f"output             {config.output_location}")
    print(f"adhyayas           {report['adhyaya_count']}")
    print(f"mantra addresses   {report['address_count']}")
    print(f"passages           {report['record_counts']['passages']}")
    print(f"text_versions      {report['record_counts']['text_versions']}")
    print("layer statistics (four distinct figures, not merged):")
    print(f"  source-declared units    {statistics.source_declared_units}")
    print(f"  inference-derived units  {statistics.inference_derived_units}")
    print(f"  variant-bearing units    {statistics.variant_bearing_units}")
    print(f"  review items             {statistics.review_items}")
    print(f"has PRIMARY_TEXT layer     {report['has_primary_text_layer']}")
    print(f"text roles                 {report['text_roles_from_registry']}")
    rishi = report["rishi"]
    print(
        f"rsi assertions (computed)  {rishi['computed_assertions']} "
        f"vs projection {rishi['projected_assertions_prior_research']} "
        f"(difference {rishi['difference_vs_projection']:+d})"
    )
    print(
        f"devata / chandas           {rishi['devata_assertions']} / {rishi['chandas_assertions']}"
    )
    print(f"translations               {report['record_counts']['translations']}")
    print(f"qa issues                  {report['record_counts']['qa_issues']}")

    if args.no_verify_determinism:
        print("determinism        SKIPPED")
        return 0
    identical = verify_determinism(config, args.config, config.output_location)
    print(f"determinism        {'BYTE-IDENTICAL' if identical else 'DIVERGED'}")
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
