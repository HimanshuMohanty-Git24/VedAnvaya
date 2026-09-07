"""Contracts for typed, evidence-anchored semantic object occurrences."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.semantic.object_ontology import (
    COMPARISON_POLICY_VERSION,
    EXPLICITNESS_POLICY_VERSION,
    SEMANTIC_OBJECT_SCHEMA_VERSION,
    DisagreementDecomposition,
    ExplicitnessPolicyAssessment,
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
    SemanticOntologyGapCode,
    StructuredComparisonCategory,
    object_kind_is_allowed,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate


class TranslationSpan(VGModel):
    """Half-open character offsets into a pinned translation record."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> TranslationSpan:
        if self.end <= self.start:
            raise ValueError("translation span end must be greater than start")
        return self


class SemanticEvidenceAnchor(VGModel):
    """Deterministic references justifying an occurrence-level semantic object."""

    source_passage_id: str = Field(min_length=1)
    translation_record_id: str | None = None
    translation_span: TranslationSpan | None = None
    token_ids: list[str] = Field(default_factory=list)
    passage_ids: list[str] = Field(default_factory=list)
    other_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def span_requires_translation(self) -> SemanticEvidenceAnchor:
        if self.translation_span is not None and self.translation_record_id is None:
            raise ValueError("translation offsets require a translation record id")
        if not (
            self.translation_record_id
            or self.token_ids
            or self.passage_ids
            or self.other_evidence_ids
        ):
            raise ValueError("an evidence anchor must name a deterministic evidence record")
        return self


class EventParticipant(VGModel):
    """One evidenced event role; the role vocabulary is intentionally not canonicalized."""

    role: str = Field(min_length=1)
    entity_id: str | None = None
    normalized_head: str | None = None

    @model_validator(mode="after")
    def participant_has_referent(self) -> EventParticipant:
        if bool(self.entity_id) == bool(self.normalized_head):
            raise ValueError("event participant requires exactly one entity id or head")
        return self


class ActionEvent(VGModel):
    """An occurrence-level action; absent arguments stay absent."""

    action_head: str = Field(min_length=1)
    actor_entity_id: str | None = None
    patient_entity_id: str | None = None
    other_participants: list[EventParticipant] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)


class SemanticObjectCandidate(VGModel):
    """An evidenced occurrence candidate, never a global canonical semantic concept."""

    candidate_id: str = Field(pattern=r"^VG:SEMOBJ:[A-F0-9]{20}$")
    object_kind: SemanticObjectKind
    normalized_head: str | None = None
    display_label: str = Field(min_length=1)
    qualifiers: list[str] = Field(default_factory=list)
    canonical_entity_id: str | None = None
    beneficiary_entity_id: str | None = None
    target_entity_id: str | None = None
    event: ActionEvent | None = None
    source_passage_id: str = Field(min_length=1)
    evidence: list[SemanticEvidenceAnchor] = Field(min_length=1)
    extraction_model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    normalization_status: SemanticObjectNormalizationStatus
    ontology_gap_code: SemanticOntologyGapCode | None = None
    legacy_object_id: str | None = None
    schema_version: str = SEMANTIC_OBJECT_SCHEMA_VERSION

    @model_validator(mode="after")
    def kind_specific_fields(self) -> SemanticObjectCandidate:
        if any(item.source_passage_id != self.source_passage_id for item in self.evidence):
            raise ValueError("object evidence must be scoped to its source passage")
        if self.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF:
            if self.canonical_entity_id is None:
                raise ValueError("canonical entity reference requires canonical_entity_id")
            if self.normalization_status is not SemanticObjectNormalizationStatus.CANONICAL_REF:
                raise ValueError("canonical entity reference requires CANONICAL_REF status")
        elif self.canonical_entity_id is not None:
            raise ValueError("only CANONICAL_ENTITY_REF may carry canonical_entity_id")
        if self.object_kind is SemanticObjectKind.EVENT:
            if self.event is None:
                raise ValueError("EVENT requires structured action fields")
        elif self.event is not None:
            raise ValueError("structured action fields are only valid for EVENT")
        if self.object_kind is SemanticObjectKind.ONTOLOGY_GAP_REF:
            if self.ontology_gap_code is None:
                raise ValueError("ontology gap object requires a gap code")
            if self.normalization_status is not SemanticObjectNormalizationStatus.ONTOLOGY_GAP:
                raise ValueError("ontology gap object requires ONTOLOGY_GAP status")
        elif self.ontology_gap_code is not None:
            raise ValueError("ontology gap code is only valid for ONTOLOGY_GAP_REF")
        if self.object_kind is not SemanticObjectKind.CANONICAL_ENTITY_REF and not (
            self.normalized_head or self.object_kind is SemanticObjectKind.ONTOLOGY_GAP_REF
        ):
            raise ValueError("non-canonical semantic object requires a normalized head")
        return self


class EventSignature(VGModel):
    action_head: str
    actor_entity_id: str | None = None
    patient_entity_id: str | None = None
    participants: tuple[tuple[str, str], ...] = ()
    qualifiers: tuple[str, ...] = ()


class SemanticObjectSignature(VGModel):
    """Identity-bearing structure; deliberately excludes the display label."""

    object_kind: SemanticObjectKind
    canonical_entity_id: str | None = None
    normalized_head: str | None = None
    qualifiers: tuple[str, ...] = ()
    beneficiary_entity_id: str | None = None
    target_entity_id: str | None = None
    event: EventSignature | None = None


class EvidenceSignature(VGModel):
    references: tuple[str, ...] = ()


class SemanticAssertionSignature(VGModel):
    """Subject, locked predicate, typed object structure, and deterministic evidence."""

    subject_id: str
    predicate: SemanticPredicate
    object_signature: SemanticObjectSignature
    evidence_signature: EvidenceSignature


class StructuredSemanticAssertion(VGModel):
    """A migrated or native-v3 assertion whose object is an occurrence candidate."""

    assertion_id: str = Field(min_length=1)
    source_run_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    predicate: SemanticPredicate
    object: SemanticObjectCandidate
    evidence: list[SemanticEvidenceAnchor] = Field(min_length=1)
    explicitness: Explicitness
    inference_step: str | None = None
    legacy_assertion_id: str | None = None
    schema_version: str = SEMANTIC_OBJECT_SCHEMA_VERSION

    @model_validator(mode="after")
    def predicate_accepts_object(self) -> StructuredSemanticAssertion:
        if self.subject_id != self.object.source_passage_id:
            raise ValueError("assertion subject and occurrence source passage must agree")
        if not object_kind_is_allowed(self.predicate, self.object.object_kind):
            raise ValueError(
                f"{self.predicate.value} cannot target {self.object.object_kind.value}"
            )
        return self


class StructuredSemanticComparison(VGModel):
    mantra_id: str
    category: StructuredComparisonCategory
    luna_assertion_id: str | None = None
    sol_assertion_id: str | None = None
    luna_predicate: SemanticPredicate | None = None
    sol_predicate: SemanticPredicate | None = None
    luna_object_signature: SemanticObjectSignature | None = None
    sol_object_signature: SemanticObjectSignature | None = None
    evidence_overlap: bool = False
    label_equality_signal: bool = False
    reasoning: str = Field(min_length=1)
    comparison_policy_version: str = COMPARISON_POLICY_VERSION
    provenance: Literal["MODEL_VS_MODEL_STRUCTURED_DIAGNOSTIC"] = (
        "MODEL_VS_MODEL_STRUCTURED_DIAGNOSTIC"
    )


class MantraDisagreementDiagnosis(VGModel):
    mantra_id: str
    primary_category: DisagreementDecomposition
    comparison_categories: list[StructuredComparisonCategory]
    rationale: str = Field(min_length=1)


class ExplicitnessReview(VGModel):
    assertion_id: str
    mantra_id: str
    predicate: SemanticPredicate
    legacy_explicitness: Explicitness
    policy_assessment: ExplicitnessPolicyAssessment
    reason: str = Field(min_length=1)
    policy_version: str = EXPLICITNESS_POLICY_VERSION
    legacy_output_unchanged: Literal[True] = True


class SemanticExtractionV3(VGModel):
    """Typed, evidence-anchored occurrence payload for the v3 pilot."""

    mantra_id: str
    assertions: list[StructuredSemanticAssertion] = Field(default_factory=list)
    ontology_gaps: list[SemanticObjectCandidate] = Field(default_factory=list)
    no_claim_reasons: list[str] = Field(default_factory=list)
    prompt_version: Literal["rigveda-semantic-extraction-v3"] = "rigveda-semantic-extraction-v3"
    object_schema_version: Literal["rigveda-semantic-object-v1"] = "rigveda-semantic-object-v1"

    @model_validator(mode="after")
    def consistent_claim_state(self) -> SemanticExtractionV3:
        if self.assertions and self.no_claim_reasons:
            raise ValueError("v3 assertions cannot coexist with no-claim reasons")
        if any(
            item.object_kind is not SemanticObjectKind.ONTOLOGY_GAP_REF
            for item in self.ontology_gaps
        ):
            raise ValueError("ontology_gaps must contain ONTOLOGY_GAP_REF objects")
        for assertion in self.assertions:
            if assertion.explicitness is Explicitness.INTERPRETIVE:
                raise ValueError("INTERPRETIVE relations are not emitted by semantic v3")
            if (
                assertion.explicitness is Explicitness.STRONG_INFERENCE
                and not assertion.inference_step
            ):
                raise ValueError("STRONG_INFERENCE requires one named inference step")
            if assertion.explicitness is Explicitness.EXPLICIT and assertion.inference_step:
                raise ValueError("EXPLICIT relation cannot carry an inference step")
        return self


class SemanticNormalizationManifest(VGModel):
    """Pinned provenance for the offline normalization diagnostic."""

    run_id: Literal["vedagraph-rigveda-semantic-normalization-v1"] = (
        "vedagraph-rigveda-semantic-normalization-v1"
    )
    corpus_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    traditional_knowledge_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    lexical_knowledge_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    luna_v1_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    luna_v2_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sol_silver_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    semantic_ontology_version: str = Field(min_length=1)
    semantic_object_schema_version: str = SEMANTIC_OBJECT_SCHEMA_VERSION
    comparison_policy_version: str = COMPARISON_POLICY_VERSION
    explicitness_policy_version: str = EXPLICITNESS_POLICY_VERSION
    input_hashes: dict[str, str]
    output_hashes: dict[str, str]
    record_counts: dict[str, int]
    human_gold_status: Literal["UNANNOTATED"] = "UNANNOTATED"
    unlocked_predicates: list[str] = Field(default_factory=list, max_length=0)
    model_execution: Literal[False] = False
    created_at: datetime
    schema_version: str = SCHEMA_VERSION
