"""Validated data contracts for VedaGraph records."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from vedagraph.models.enums import (
    AlignmentLevel,
    AlignmentMethod,
    AssertionStatus,
    AudioType,
    AuthorityTier,
    CandidateScopeType,
    DiscoveryAvailability,
    EntityType,
    MetadataPredicate,
    PassageStatus,
    QASeverity,
    QAStatus,
    QualityStatus,
    RangeParseStatus,
    ReviewStatus,
    RightsStatus,
    ScopeType,
    StoragePolicy,
    TextComparisonCategory,
    TextForm,
    TextRole,
    TextSelectionPolicy,
    TranslationAlignment,
)

SCHEMA_VERSION = "1.0.0"


class VGModel(BaseModel):
    """Strict base class shared by persisted records."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=False)


class RightsInfo(VGModel):
    status: RightsStatus
    license_url: AnyHttpUrl | None = None
    holder: str | None = None
    jurisdiction: str | None = None
    notes: str | None = None
    verified_at: datetime | None = None


class Source(VGModel):
    source_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    name: str
    organization: str | None = None
    url: AnyHttpUrl
    authority_tier: AuthorityTier
    formats: list[str]
    known_languages: list[str]
    rights: RightsInfo
    verification_roles: list[str]
    bulk_ingestion_status: str
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class SourceArtifact(VGModel):
    """One exact electronic file/transformation and its edition-level provenance."""

    artifact_id: str = Field(pattern=r"^[A-Z][A-Z0-9_.-]+$")
    source_id: str
    work_id: str | None = None
    url: AnyHttpUrl
    format: str
    filename: str
    retrieval_date: date | None = None
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    title: str | None = None
    edition_title: str | None = None
    editors: list[str] = Field(default_factory=list)
    electronic_editors: list[str] = Field(default_factory=list)
    contributors: list[str] = Field(default_factory=list)
    provenance_notes: str | None = None
    source_edition: str | None = None
    publication_date: str | None = None
    license_statement_verbatim: str | None = None
    rights_status: RightsStatus
    license_url: AnyHttpUrl | None = None
    transformation_version: str | None = None
    encoding: str | None = None
    language: str | None = None
    recension: str | None = None
    citation_system: str | None = None
    repository_url: AnyHttpUrl | None = None
    repository_commit_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    repository_path: str | None = None
    git_blob_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    file_size_bytes: int | None = Field(default=None, ge=0)
    parent_artifact_id: str | None = None
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def require_commit_pin(self) -> SourceArtifact:
        """Git-hosted datasets must name an exact commit, never a moving branch."""
        if self.repository_url is not None and self.repository_commit_sha is None:
            raise ValueError("repository-hosted artifacts require repository_commit_sha")
        if self.repository_commit_sha is not None and self.repository_path is None:
            raise ValueError("pinned repository artifacts require repository_path")
        return self


class Work(VGModel):
    """One recension of one Veda, and the structural vocabulary it is addressed by.

    ``hierarchy`` is a declared assertion about a text, so ``structure_evidence_sha256``
    lets it point at the exact artifact that evidences it rather than resting on
    secondary literature. ``identity_status`` is ``FINAL`` only when the key may never
    change again; ``PROVISIONAL`` means the structure is confirmed from a source record
    but something the key depends on is still open, and ``RESEARCH_REQUIRED`` means the
    hierarchy itself is not yet known. See docs/FOUR_VEDA_STRUCTURAL_MODEL.md.
    """

    work_id: str = Field(pattern=r"^VG:WORK:[A-Z]+:[A-Z]+$")
    abbreviation: str
    veda: str
    work_name: str
    recension: str
    hierarchy: list[str] = Field(min_length=1)
    citation_pattern: str
    key_pattern: str | None = None
    identity_status: str = "FINAL"
    structure_evidence_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class Citation(VGModel):
    citation_id: UUID
    passage_id: UUID
    label: str
    system: str
    source_id: str | None = None
    is_canonical: bool = False
    schema_version: str = SCHEMA_VERSION


class Passage(VGModel):
    """One addressable node on the generic ``Work -> container(s) -> Passage`` spine.

    Depth is not fixed. Rigveda and Atharvaveda are three levels, Vajasaneyi is two,
    Samaveda Kauthuma is five and its depth varies between arcikas. ``hierarchy``
    therefore carries level-name -> value pairs rather than fixed columns, and
    ``native_labels`` carries the edition's own ordered level names so no work is read
    through another work's vocabulary. See docs/FOUR_VEDA_STRUCTURAL_MODEL.md.
    """

    entity_id: UUID
    canonical_key: str = Field(pattern=r"^VG:[A-Z]+:[A-Z]+:.+$")
    canonical_urn: str = Field(pattern=r"^urn:vedagraph:")
    entity_type: EntityType
    work_id: str
    hierarchy: dict[str, int | str]
    canonical_citation: str
    parent_key: str | None = None
    sequence_in_parent: int = Field(ge=1)
    native_labels: list[str] = Field(default_factory=list)
    structural_path: list[str] = Field(default_factory=list)
    status: PassageStatus = PassageStatus.CANONICAL
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_native_structure(self) -> Passage:
        """Keep the optional structural view consistent with ``hierarchy``.

        Both fields default to empty, so records written before they existed are
        unaffected. When supplied, ``native_labels`` names exactly the levels in
        ``hierarchy`` and supplies the ordering a dict cannot guarantee, and
        ``structural_path`` holds the matching values as strings so zero-padding and
        non-integer level labels survive.
        """
        if self.native_labels:
            lowered = [label.lower() for label in self.native_labels]
            if len(lowered) != len(set(lowered)):
                raise ValueError("native_labels must not repeat a level name")
            if set(lowered) != {key.lower() for key in self.hierarchy}:
                raise ValueError("native_labels must name exactly the levels in hierarchy")
        if self.structural_path:
            if not self.native_labels:
                raise ValueError("structural_path requires native_labels to define its order")
            if len(self.structural_path) != len(self.native_labels):
                raise ValueError("structural_path and native_labels must be positionally aligned")
        return self


class TextVersion(VGModel):
    text_id: UUID
    passage_id: UUID
    language: str
    script: str
    text_form: TextForm
    text_role: TextRole = TextRole.PRIMARY_TEXT
    text_version_id: str | None = None
    text_original: str = Field(min_length=1)
    text_nfc: str = Field(min_length=1)
    accented: bool
    transliteration_scheme: str | None = None
    source_id: str
    source_artifact_id: str | None = None
    source_locator: str
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rights_status: RightsStatus
    schema_version: str = SCHEMA_VERSION


class Translation(VGModel):
    translation_id: UUID
    passage_id: UUID
    language: str
    translator: str
    work_edition: str
    year: int | None = Field(default=None, ge=1000, le=3000)
    text: str = Field(min_length=1)
    source_id: str
    source_artifact_id: str | None = None
    rights_status: RightsStatus
    alignment_level: AlignmentLevel
    alignment: TranslationAlignment = TranslationAlignment.UNCERTAIN_ALIGNMENT
    quality_status: QualityStatus
    source_page_title: str | None = None
    source_page_id: int | None = None
    source_revision_id: int | None = None
    source_revision_timestamp: datetime | None = None
    canonical_page_url: AnyHttpUrl | None = None
    schema_version: str = SCHEMA_VERSION


class MetadataScope(VGModel):
    scope_type: ScopeType
    passage_id: UUID
    start_sequence: int | None = Field(default=None, ge=1)
    end_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> MetadataScope:
        if self.scope_type == ScopeType.MANTRA_RANGE:
            if self.start_sequence is None or self.end_sequence is None:
                raise ValueError("mantra ranges require start_sequence and end_sequence")
            if self.start_sequence > self.end_sequence:
                raise ValueError("start_sequence must not exceed end_sequence")
        elif self.start_sequence is not None or self.end_sequence is not None:
            raise ValueError("sequence bounds are only valid for MANTRA_RANGE")
        return self


class TraditionalMetadataAssertion(VGModel):
    assertion_id: UUID
    predicate: MetadataPredicate
    value: str
    scope: MetadataScope
    source_id: str
    source_locator: str
    status: AssertionStatus = AssertionStatus.UNREVIEWED
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class SourceAssertion(VGModel):
    assertion_id: UUID
    subject_id: str
    predicate: str
    value: Any
    source_id: str
    source_artifact_id: str | None = None
    source_locator: str
    asserted_at: datetime | None = None
    status: AssertionStatus = AssertionStatus.UNREVIEWED
    evidence: str | None = None
    schema_version: str = SCHEMA_VERSION


class AudioRecording(VGModel):
    audio_id: UUID
    target_id: UUID
    language: str
    audio_type: AudioType
    recension: str | None = None
    patha_type: str | None = None
    recitation_tradition: str | None = None
    reciter: str | None = None
    source_id: str
    source_media_id: str | None = None
    source_url: AnyHttpUrl | None = None
    storage_policy: StoragePolicy
    rights_status: RightsStatus
    mime_type: str | None = None
    duration_ms: int | None = Field(default=None, gt=0)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def require_location(self) -> AudioRecording:
        if not self.source_media_id and not self.source_url and not self.sha256:
            raise ValueError("audio requires a source media id, URL, or stored content hash")
        return self


class AudioSegment(VGModel):
    segment_id: UUID
    audio_id: UUID
    passage_id: UUID
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    alignment_method: AlignmentMethod
    alignment_confidence: float | None = Field(default=None, ge=0, le=1)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def chronological(self) -> AudioSegment:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class QAIssue(VGModel):
    issue_id: UUID
    check_id: str
    severity: QASeverity
    message: str
    entity_id: str | None = None
    file: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


class ManifestFile(VGModel):
    path: str
    record_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class CorpusManifest(VGModel):
    dataset: str = "VedaGraph Canonical Corpus"
    version: str
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    works: list[str]
    passage_count: int = Field(ge=0)
    source_snapshot_ids: list[str]
    source_artifact_ids: list[str] = Field(default_factory=list)
    raw_snapshot_hashes: dict[str, str] = Field(default_factory=dict)
    build_config_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    parser_versions: dict[str, str] = Field(default_factory=dict)
    reconciliation_policy_version: str | None = None
    software_version: str | None = None
    qa_policy_version: str | None = None
    comparison_version: str | None = None
    component_manifest_hashes: dict[str, str] = Field(default_factory=dict)
    build_config_hashes: dict[str, str] = Field(default_factory=dict)
    revision_manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    generated_content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    rights_summary: dict[str, str] = Field(default_factory=dict)
    software_git_commit: str | None = None
    generated_files: list[ManifestFile]
    record_counts: dict[str, int]
    qa_status: QAStatus
    schema_version: str = SCHEMA_VERSION


class RawSnapshotMetadata(VGModel):
    snapshot_id: str
    source_id: str
    retrieval_url: AnyHttpUrl
    retrieved_at: datetime
    http_status: int
    content_type: str | None = None
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    etag: str | None = None
    last_modified: str | None = None
    filename: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    parser_independent_metadata: dict[str, str] = Field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


class StagingTextRecord(VGModel):
    source_id: str
    source_locator: str
    work_id: str
    hierarchy: dict[str, int | str]
    text_original: str
    language: str = "sa"
    script: str = "Devanagari"
    accented: bool = False
    snapshot_id: str
    source_artifact_id: str | None = None
    text_version_id: str | None = None
    text_role: TextRole = TextRole.PRIMARY_TEXT
    text_selection_policy: TextSelectionPolicy | None = None
    alternate_text: str | None = None


class StagingTranslationRecord(VGModel):
    source_id: str
    source_locator: str
    work_id: str
    hierarchy: dict[str, int | str]
    text_original: str
    language: str
    translator: str
    work_edition: str
    year: int | None = None
    snapshot_id: str
    source_artifact_id: str | None = None
    alignment: TranslationAlignment = TranslationAlignment.UNCERTAIN_ALIGNMENT
    page_title: str | None = None
    page_id: int | None = None
    revision_id: int | None = None
    revision_timestamp: datetime | None = None
    canonical_page_url: AnyHttpUrl | None = None
    retrieval_timestamp: datetime | None = None


class VHPMetadataStagingRecord(VGModel):
    source_id: str = "VHP"
    source_locator: str
    work_id: str = "VG:WORK:RV:SAK"
    hierarchy: dict[str, int | str]
    rishis: list[str] = Field(default_factory=list)
    devatas: list[str] = Field(default_factory=list)
    chandas: list[str] = Field(default_factory=list)
    reported_mantra_count: int | None = Field(default=None, ge=1)
    media_urls: list[AnyHttpUrl] = Field(default_factory=list)
    snapshot_id: str
    schema_version: str = SCHEMA_VERSION


class GretilHeaderMetadata(VGModel):
    title: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    responsibility_statements: dict[str, list[str]] = Field(default_factory=dict)
    source_bibliography: list[str] = Field(default_factory=list)
    license_statement_verbatim: str | None = None
    license_url: AnyHttpUrl | None = None
    revision_information: list[str] = Field(default_factory=list)
    encoding_information: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    xml_id: str | None = None


class SuktaDiscoveryRecord(VGModel):
    canonical_sukta_key: str
    sukta_number: int = Field(ge=1)
    mandala_number: int = Field(ge=1)
    parent_mandala_key: str
    source_id: str
    source_artifact_id: str | None = None
    source_locator: str
    availability: DiscoveryAvailability
    discovery_source: str
    discovered_at: datetime | None = None
    known_mantra_count: int | None = Field(default=None, ge=1)
    snapshot_id: str
    schema_version: str = SCHEMA_VERSION


class SectionDiscoveryRecord(VGModel):
    """Work-agnostic structural discovery for a container at any depth.

    :class:`SuktaDiscoveryRecord` is Rigveda-shaped -- it requires ``sukta_number``,
    ``mandala_number`` and ``parent_mandala_key`` -- so works with no sukta level
    (Vajasaneyi) or with four container levels (Samaveda) cannot use it. It is left
    exactly as it is because the sealed Rigveda corpus contains 2,247 such records;
    this is the additive generic form for every other work. ``section_number`` allows
    ``0`` because Samaveda encodes an absent level as a literal zero.
    """

    work_id: str
    canonical_section_key: str
    section_level: str
    section_number: int = Field(ge=0)
    parent_key: str | None = None
    known_child_count: int | None = Field(default=None, ge=0)
    availability: DiscoveryAvailability
    discovery_source: str
    source_id: str
    source_artifact_id: str | None = None
    source_locator: str
    snapshot_id: str
    discovered_at: datetime | None = None
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class BuildSourceInput(VGModel):
    source_id: str
    role: str
    scope: str | None = None
    snapshot_path: Path
    snapshot_id: str
    snapshot_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_artifact_id: str | None = None
    parser_version: str


class TextVersionSelection(VGModel):
    """Build-configuration reference to one declared text version."""

    artifact: str
    text_version: str
    role: TextRole
    selection_policy: str | None = None


class CorpusBuildConfig(VGModel):
    """Rigveda-specific build configuration, sliced one Mandala at a time.

    ``mandala`` and ``selected_suktas`` are required and are read as plain ints
    throughout ``vedagraph.build``, so this model cannot express a work without a
    Mandala or a Sukta level. That is intentional and is not a defect to be relaxed:
    other works use :class:`WorkBuildConfig`. See ADR-018.
    """

    config_version: str
    dataset_id: str
    release_version: str
    work_id: str
    mandala: int = Field(ge=1)
    selected_suktas: list[int] = Field(min_length=1)
    text_selection_policy: TextSelectionPolicy
    primary_sanskrit: TextVersionSelection | None = None
    parallel_sanskrit: list[TextVersionSelection] = Field(default_factory=list)
    candidate_text_versions: list[TextVersionSelection] = Field(default_factory=list)
    sources: list[BuildSourceInput]
    translation_sources: list[str] = Field(default_factory=list)
    metadata_sources: list[str] = Field(default_factory=list)
    media_discovery_sources: list[str] = Field(default_factory=list)
    reconciliation_policy_version: str
    qa_policy_version: str = "corpus-qa-v1"
    rights_policy_version: str = "artifact-and-version-rights-v1"
    media_policy_version: str = "external-reference-only-v1"
    translation_alignment_policy_version: str = "conservative-source-numbered-v1"
    output_location: Path
    staging_location: Path | None = None
    build_timestamp: datetime

    @model_validator(mode="after")
    def unique_suktas(self) -> CorpusBuildConfig:
        if len(self.selected_suktas) != len(set(self.selected_suktas)):
            raise ValueError("selected_suktas must be unique")
        object.__setattr__(self, "selected_suktas", sorted(self.selected_suktas))
        return self


class WorkBuildConfig(VGModel):
    """Work-agnostic build configuration for non-Rigveda works.

    :class:`CorpusBuildConfig` requires ``mandala`` and ``selected_suktas`` and reads
    them as plain ints throughout the sealed Rigveda builder, so it is Rigveda-specific
    and is deliberately NOT loosened. This is the shared shape every other work builds
    against, so Samaveda, Vajasaneyi and Atharvaveda do not each invent one.
    ``section_level`` names the container the build is sliced on using the work's own
    vocabulary; an empty ``selected_sections`` means the whole work.
    See docs/decisions/ADR-018-per-work-build-configuration.md.
    """

    config_version: str
    dataset_id: str
    release_version: str
    work_id: str = Field(pattern=r"^VG:WORK:[A-Z]+:[A-Z]+$")
    section_level: str | None = None
    selected_sections: list[int] = Field(default_factory=list)
    mantra_level: str = "Mantra"
    text_selection_policy: TextSelectionPolicy
    primary_sanskrit: TextVersionSelection | None = None
    parallel_sanskrit: list[TextVersionSelection] = Field(default_factory=list)
    candidate_text_versions: list[TextVersionSelection] = Field(default_factory=list)
    sources: list[BuildSourceInput]
    translation_sources: list[str] = Field(default_factory=list)
    metadata_sources: list[str] = Field(default_factory=list)
    media_discovery_sources: list[str] = Field(default_factory=list)
    reconciliation_policy_version: str
    qa_policy_version: str = "corpus-qa-v1"
    rights_policy_version: str = "artifact-and-version-rights-v1"
    media_policy_version: str = "external-reference-only-v1"
    translation_alignment_policy_version: str = "conservative-source-numbered-v1"
    output_location: Path
    staging_location: Path | None = None
    build_timestamp: datetime
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_sections(self) -> WorkBuildConfig:
        if len(self.selected_sections) != len(set(self.selected_sections)):
            raise ValueError("selected_sections must be unique")
        if self.selected_sections and self.section_level is None:
            raise ValueError("selected_sections requires section_level to name the container")
        object.__setattr__(self, "selected_sections", sorted(self.selected_sections))
        return self


class FullCorpusBuildConfig(VGModel):
    """Composition of independently validated Mandala build units."""

    config_version: str
    dataset_id: str
    release_version: str
    work_id: str
    mandala_configs: list[Path] = Field(min_length=1)
    expected_mandalas: int = Field(ge=1)
    expected_suktas: int = Field(ge=1)
    expected_mantras: int = Field(ge=1)
    reconciliation_policy_version: str
    qa_policy_version: str
    output_location: Path
    build_timestamp: datetime

    @model_validator(mode="after")
    def unique_components(self) -> FullCorpusBuildConfig:
        if len(self.mandala_configs) != len(set(self.mandala_configs)):
            raise ValueError("mandala_configs must be unique")
        return self


class TextVersionDescriptor(VGModel):
    """One declared Sanskrit textual representation inside a source artifact.

    A single artifact (the VedaWeb Book 1 TEI, for example) carries several distinct
    editions. Rights, lineage, and permitted VedaGraph role attach here, not to the host
    repository or the enclosing file.
    """

    text_version_id: str = Field(pattern=r"^[A-Z][A-Z0-9_.-]+$")
    artifact_id: str
    source_version_key: str
    human_title: str
    text_type: str
    text_form: TextForm
    text_role: TextRole
    recension: str | None = None
    underlying_edition: str | None = None
    electronic_lineage: list[str] = Field(default_factory=list)
    language: str
    script: str
    transliteration_scheme: str | None = None
    accent_support: str
    metrical_restoration: bool = False
    orthographic_normalization: str | None = None
    normalized_rights: RightsStatus
    license_uri: AnyHttpUrl | None = None
    verbatim_license: str | None = None
    upstream_rights_notes: list[str] = Field(default_factory=list)
    source_specific_restrictions: str | None = None
    transformation_provenance: str | None = None
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class CandidateMetadataScope(VGModel):
    """Unreviewed scope extracted from a traditional-metadata string.

    Canonical records use :class:`MetadataScope`. Nothing here is canonical: sub-mantra
    scopes are kept verbatim rather than widened into whole-mantra claims.
    """

    scope_type: CandidateScopeType
    start_mantra: int | None = Field(default=None, ge=1)
    end_mantra: int | None = Field(default=None, ge=1)
    mantras: list[int] = Field(default_factory=list)
    raw_scope_text: str
    raw_entity: str
    qualifier_markers: list[str] = Field(default_factory=list)
    needs_review: bool = True
    notes: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> CandidateMetadataScope:
        if self.scope_type == CandidateScopeType.MANTRA_RANGE:
            if self.start_mantra is None or self.end_mantra is None:
                raise ValueError("mantra ranges require start_mantra and end_mantra")
            if self.start_mantra > self.end_mantra:
                raise ValueError("start_mantra must not exceed end_mantra")
        return self


class CandidateMetadataAssertion(VGModel):
    """Reviewable output of the traditional-metadata range parser."""

    candidate_id: UUID
    subject_id: str
    predicate: MetadataPredicate
    source_id: str
    source_locator: str
    raw_value: str
    parse_status: RangeParseStatus
    parser_version: str
    segments: list[CandidateMetadataScope] = Field(default_factory=list)
    unparsed_remainder: list[str] = Field(default_factory=list)
    safe_to_promote: bool = False
    review_status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class TextComparison(VGModel):
    """Deterministic comparison of one mantra across two Sanskrit text versions."""

    comparison_id: UUID
    passage_key: str
    citation: str
    left_version_id: str
    right_version_id: str
    category: TextComparisonCategory
    classification_basis: str
    equal_at_form: str | None = None
    similarity: float = Field(ge=0, le=1)
    differing_codepoints: int = Field(ge=0)
    differing_tokens: int = Field(ge=0)
    left_token_count: int = Field(ge=0)
    right_token_count: int = Field(ge=0)
    accent_only: bool = False
    left_accented: bool = False
    right_accented: bool = False
    schema_version: str = SCHEMA_VERSION
