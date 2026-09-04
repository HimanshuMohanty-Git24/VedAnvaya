"""Data contracts for the deterministic knowledge layer.

The layer is strictly staged:

``AnukramaniStagingRecord``
    one parsed source row, verbatim.

``MetadataSourceAssertion``
    one attributable raw claim: this locator says this raw string, for this scope.

``KnowledgeEntity`` / ``EntityAlias``
    the canonical registries, which are reviewed data, not parser output.

``KnowledgeAssertion``
    a resolved deterministic edge from one mantra to one canonical entity, which always
    names the source assertion it came from.

Nothing skips a stage. A raw string never becomes an entity without passing through a
recorded resolution.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, Field, model_validator

from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.models.enums import (
    AliasType,
    AnukramaniField,
    AnukramaniParseStatus,
    DevataSubtype,
    KnowledgeEntityType,
    MetadataAgreement,
    MetadataPredicate,
    ProvenanceClass,
    QAStatus,
    ResolutionStatus,
    ReviewStatus,
    ScopeOrigin,
    ScopeType,
)

FIELD_PREDICATE: dict[AnukramaniField, MetadataPredicate] = {
    AnukramaniField.SEER: MetadataPredicate.HAS_RISHI,
    AnukramaniField.DIVINITY: MetadataPredicate.HAS_DEVATA,
    AnukramaniField.METER: MetadataPredicate.HAS_CHANDAS,
}

PREDICATE_ENTITY_TYPE: dict[MetadataPredicate, KnowledgeEntityType] = {
    MetadataPredicate.HAS_RISHI: KnowledgeEntityType.RISHI,
    MetadataPredicate.HAS_DEVATA: KnowledgeEntityType.DEVATA,
    MetadataPredicate.HAS_CHANDAS: KnowledgeEntityType.CHANDAS,
}

RESOLVING_STATUSES = frozenset(
    {
        ResolutionStatus.EXACT,
        ResolutionStatus.NORMALIZED_EXACT,
        ResolutionStatus.KNOWN_ALIAS,
        ResolutionStatus.COMPOSITE_PRESERVED,
    }
)


class AnukramaniSegment(VGModel):
    """One comma-separated segment of one Anukramaṇī field, kept verbatim."""

    field: AnukramaniField
    raw_segment: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    raw_scope: str | None = None
    scope_origin: ScopeOrigin
    start_mantra: int | None = Field(default=None, ge=1)
    end_mantra: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> AnukramaniSegment:
        if self.scope_origin is ScopeOrigin.SUKTA_WIDE:
            if self.start_mantra is not None or self.end_mantra is not None:
                raise ValueError("sukta-wide segments carry no mantra bounds")
            return self
        if self.start_mantra is None or self.end_mantra is None:
            raise ValueError("scoped segments require mantra bounds")
        if self.start_mantra > self.end_mantra:
            raise ValueError("start_mantra must not exceed end_mantra")
        if self.scope_origin is ScopeOrigin.SINGLE_MANTRA and self.start_mantra != self.end_mantra:
            raise ValueError("single-mantra segments span exactly one mantra")
        return self

    def mantras(self) -> list[int]:
        if self.start_mantra is None or self.end_mantra is None:
            return []
        return list(range(self.start_mantra, self.end_mantra + 1))


class AnukramaniStagingRecord(VGModel):
    """One parsed Anukramaṇī row. Adapters produce these and nothing canonical."""

    source_id: str = "WSC2023"
    source_artifact_id: str
    snapshot_id: str
    source_locator: str
    raw_line: str = Field(min_length=1)
    line_number: int = Field(ge=1)
    work_id: str = "VG:WORK:RV:SAK"
    mandala: int = Field(ge=1)
    sukta: int = Field(ge=1)
    declared_verse_count: int = Field(ge=1)
    raw_seer_field: str | None = None
    raw_divinity_field: str | None = None
    raw_meter_field: str | None = None
    segments: list[AnukramaniSegment] = Field(default_factory=list)
    parse_status: AnukramaniParseStatus
    parse_notes: list[str] = Field(default_factory=list)
    parser_version: str
    schema_version: str = SCHEMA_VERSION


class MetadataSourceAssertion(VGModel):
    """One attributable raw metadata claim, before any entity resolution.

    ``raw_value`` is never rewritten to a canonical spelling, so the digitized
    Anukramaṇī can be reconstructed exactly from these records.
    """

    assertion_id: UUID
    subject_key: str = Field(pattern=r"^VG:RV:SAK:")
    scope_type: ScopeType
    scope_origin: ScopeOrigin
    start_mantra: int | None = Field(default=None, ge=1)
    end_mantra: int | None = Field(default=None, ge=1)
    predicate: MetadataPredicate
    raw_value: str = Field(min_length=1)
    normalized_value: str = Field(min_length=1)
    raw_segment: str = Field(min_length=1)
    raw_line: str = Field(min_length=1)
    source_id: str
    source_artifact_id: str
    snapshot_id: str
    source_locator: str
    citation: str
    parser_version: str
    schema_version: str = SCHEMA_VERSION


class EntityAlias(VGModel):
    """One surface string treated as naming an entity, with the reason recorded."""

    alias: str = Field(min_length=1)
    alias_type: AliasType
    evidence: str | None = None


class KnowledgeEntity(VGModel):
    """A canonical Ṛṣi, Devatā or Chandas.

    ``entity_key`` is pinned registry data, not a value recomputed from the label at
    build time, so an entity's identity survives a change to the normalization rules.
    """

    entity_id: UUID
    entity_key: str = Field(pattern=r"^VG:(RISHI|DEVATA|CHANDAS):[A-Z0-9-]+$")
    canonical_urn: str = Field(pattern=r"^urn:vedagraph:entity:")
    entity_type: KnowledgeEntityType
    preferred_label: str = Field(min_length=1)
    preferred_label_iast: str = Field(min_length=1)
    devanagari: str | None = None
    aliases: list[EntityAlias] = Field(default_factory=list)
    source_labels: list[str] = Field(default_factory=list)
    is_composite: bool = False
    composite_parts: list[str] = Field(default_factory=list)
    devata_subtype: DevataSubtype | None = None
    resolution_status: ResolutionStatus
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    provenance: list[str] = Field(default_factory=list)
    occurrence_count: int = Field(default=0, ge=0)
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def subtype_only_for_devata(self) -> KnowledgeEntity:
        if self.devata_subtype is not None and self.entity_type is not KnowledgeEntityType.DEVATA:
            raise ValueError("devata_subtype applies only to DEVATA entities")
        return self


class KnowledgeAssertion(VGModel):
    """A deterministic edge: one mantra, one predicate, one canonical entity.

    Deterministic resolution carries no probability. ``confidence`` is fixed at 1.0 for
    every record in this file; an unresolved label produces no record at all.
    """

    assertion_id: UUID
    subject_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    subject_id: UUID
    predicate: MetadataPredicate
    object_key: str = Field(pattern=r"^VG:(RISHI|DEVATA|CHANDAS):[A-Z0-9-]+$")
    object_id: UUID
    source_label: str = Field(min_length=1)
    source_assertion_id: UUID
    provenance_class: ProvenanceClass
    scope_origin: ScopeOrigin
    resolution_method: ResolutionStatus
    source_id: str
    source_artifact_id: str
    citation: str
    confidence: float = Field(default=1.0, ge=1.0, le=1.0)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def deterministic_only(self) -> KnowledgeAssertion:
        if self.resolution_method not in RESOLVING_STATUSES:
            raise ValueError(f"{self.resolution_method} may not attach a canonical entity")
        return self


class UnresolvedLabel(VGModel):
    """A raw label that reached no canonical entity, with why and where."""

    normalized_label: str = Field(min_length=1)
    raw_labels: list[str] = Field(min_length=1)
    entity_type: KnowledgeEntityType
    predicate: MetadataPredicate
    resolution_status: ResolutionStatus
    reason: str
    ascii_key: str
    occurrence_count: int = Field(ge=1)
    mantra_count: int = Field(ge=0)
    example_subject_keys: list[str] = Field(default_factory=list)
    candidate_entity_keys: list[str] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


class MetadataComparison(VGModel):
    """One overlapping metadata claim compared across two sources."""

    comparison_id: UUID
    subject_key: str
    citation: str
    predicate: MetadataPredicate
    left_source_id: str
    right_source_id: str
    left_values: list[str] = Field(default_factory=list)
    right_values: list[str] = Field(default_factory=list)
    left_comparable: list[str] = Field(default_factory=list)
    right_comparable: list[str] = Field(default_factory=list)
    agreement: MetadataAgreement
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class KnowledgeCoverage(VGModel):
    """Deterministic metadata coverage for one predicate over the whole corpus."""

    predicate: MetadataPredicate
    total_mantras: int = Field(ge=0)
    mantras_with_source_claim: int = Field(ge=0)
    mantras_resolved: int = Field(ge=0)
    mantras_unresolved_only: int = Field(ge=0)
    mantras_without_claim: int = Field(ge=0)
    mantras_with_multiple_entities: int = Field(ge=0)
    assertion_count: int = Field(ge=0)
    distinct_entities: int = Field(ge=0)


class EntityFrequency(VGModel):
    """How many mantras carry an assignment of one entity.

    This counts *metadata assignment*, not occurrences of the name in the Sanskrit.
    """

    entity_key: str
    preferred_label: str
    entity_type: KnowledgeEntityType
    mantra_assignment_count: int = Field(ge=0)
    sukta_count: int = Field(ge=0)


class KnowledgeStats(VGModel):
    metric_definition: str
    total_mantras: int = Field(ge=0)
    total_suktas: int = Field(ge=0)
    dataset_rows: int = Field(ge=0)
    aligned_rows: int = Field(ge=0)
    unaligned_rows: int = Field(ge=0)
    duplicate_row_mappings: int = Field(ge=0)
    missing_corpus_suktas: int = Field(ge=0)
    source_assertions: int = Field(ge=0)
    knowledge_assertions: int = Field(ge=0)
    coverage: list[KnowledgeCoverage]
    entity_counts: dict[str, int]
    unresolved_label_counts: dict[str, int]
    top_rishis: list[EntityFrequency]
    top_devatas: list[EntityFrequency]
    top_chandas: list[EntityFrequency]
    composite_devata_count: int = Field(ge=0)
    schema_version: str = SCHEMA_VERSION


class KnowledgeManifest(VGModel):
    """Pins the exact corpus, artifacts, registries and policies a build used."""

    dataset: str = "VedaGraph Deterministic Knowledge Layer"
    version: str
    built_at: datetime
    corpus_dataset_id: str
    corpus_version: str
    corpus_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    corpus_passage_count: int = Field(ge=0)
    source_id: str
    source_repository_url: AnyHttpUrl
    source_commit_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    source_artifact_ids: list[str]
    source_artifact_hashes: dict[str, str]
    snapshot_ids: list[str]
    registry_hashes: dict[str, str]
    normalization_policy_version: str
    resolution_policy_version: str
    parser_version: str
    qa_policy_version: str
    predicate_whitelist: list[MetadataPredicate]
    assertion_counts: dict[str, int]
    unresolved_counts: dict[str, int]
    qa_status: QAStatus
    generated_files: list[dict[str, str | int]]
    software_version: str | None = None
    schema_version: str = SCHEMA_VERSION
