"""Independent model-reviewed silver contracts.

These types deliberately do not inherit from or alias the human-gold models.  Silver
annotations are useful review evidence, but can never satisfy a human-gold gate.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.semantic.ontology import (
    Explicitness,
    OntologyGapKind,
    SemanticNodeType,
    SemanticPredicate,
    SilverComparisonCategory,
    SilverEvidenceAssessment,
)


class SilverEvidenceReference(VGModel):
    """An identifier inside the EvidencePacket used for the independent judgment."""

    kind: Literal["PASSAGE", "TRANSLATION", "TOKEN", "ENTITY", "PARALLEL"]
    reference_id: str = Field(min_length=1)
    note: str = ""


class SilverSemanticEntity(VGModel):
    """An entity used by the silver reviewer, canonical or packet-bounded candidate."""

    label: str = Field(min_length=1)
    node_type: SemanticNodeType
    entity_key: str | None = None
    candidate_key: str | None = None
    evidence: list[SilverEvidenceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def exactly_one_identity(self) -> SilverSemanticEntity:
        if bool(self.entity_key) == bool(self.candidate_key):
            raise ValueError("silver entity requires exactly one canonical or candidate key")
        return self


class SilverSemanticAssertion(VGModel):
    """One conservative relation independently supported by the packet."""

    assertion_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: SemanticPredicate
    object_label: str = Field(min_length=1)
    object_node_type: SemanticNodeType | None = None
    object_entity_key: str | None = None
    explicitness: Explicitness
    evidence: list[SilverEvidenceReference] = Field(min_length=1)
    rationale_code: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def target_is_typed(self) -> SilverSemanticAssertion:
        if self.object_node_type is None and self.object_entity_key is None:
            raise ValueError("silver assertion object requires a type or canonical entity key")
        return self


class SilverOntologyGap(VGModel):
    kind: OntologyGapKind
    requested_value: str = Field(min_length=1)
    note: str = Field(min_length=1)


class SilverSemanticAnnotation(VGModel):
    """A sealed independent review. It is never a human annotation."""

    mantra_id: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    citation: str = Field(min_length=1)
    provenance: Literal["MODEL_REVIEWED_SILVER"] = "MODEL_REVIEWED_SILVER"
    reviewer_model: str = Field(min_length=1)
    reviewer_runtime: Literal["CODEX_DIRECT"] = "CODEX_DIRECT"
    reasoning_effort: Literal["high"] = "high"
    ontology_version: str = Field(min_length=1)
    evidence_packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    entities: list[SilverSemanticEntity] = Field(default_factory=list)
    semantic_assertions: list[SilverSemanticAssertion] = Field(default_factory=list)
    no_claim: bool
    no_claim_code: Literal["NO_SUPPORTED_SEMANTIC_ASSERTION"] | None = None
    uncertainties: list[str] = Field(default_factory=list)
    ontology_gaps: list[SilverOntologyGap] = Field(default_factory=list)
    reviewed_at: datetime
    review_run_id: str = Field(min_length=1)
    batch_id: str = Field(pattern=r"^batch_\d{3}$")
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def claim_state_is_consistent(self) -> SilverSemanticAnnotation:
        if self.no_claim:
            if self.semantic_assertions:
                raise ValueError("no_claim cannot coexist with silver assertions")
            if self.no_claim_code != "NO_SUPPORTED_SEMANTIC_ASSERTION":
                raise ValueError("no_claim requires NO_SUPPORTED_SEMANTIC_ASSERTION")
        elif not self.semantic_assertions:
            raise ValueError("an annotation without assertions must set no_claim")
        elif self.no_claim_code is not None:
            raise ValueError("no_claim_code is only valid for no-claim annotations")
        return self


class SilverComparison(VGModel):
    """One comparison row between sealed Sol silver and Luna pilot output."""

    mantra_id: str = Field(min_length=1)
    category: SilverComparisonCategory
    luna_assertion_id: str | None = None
    sol_assertion_id: str | None = None
    luna_predicate: SemanticPredicate | None = None
    sol_predicate: SemanticPredicate | None = None
    luna_object: str | None = None
    sol_object: str | None = None
    evidence_assessment: SilverEvidenceAssessment | None = None
    reasoning: str = Field(min_length=1)
    provenance: Literal["MODEL_VS_MODEL_SILVER"] = "MODEL_VS_MODEL_SILVER"
    schema_version: str = SCHEMA_VERSION


class SilverBenchmarkManifest(VGModel):
    """Reproducibility and safety record for one silver benchmark run."""

    run_id: str = Field(min_length=1)
    provenance: Literal["MODEL_REVIEWED_SILVER"] = "MODEL_REVIEWED_SILVER"
    corpus_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deterministic_knowledge_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lexical_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_ontology_version: str = Field(min_length=1)
    luna_pilot_run_id: str = Field(min_length=1)
    luna_model_id: str = Field(min_length=1)
    sol_reviewer_model_id: str = Field(min_length=1)
    runtime: Literal["CODEX_DIRECT"] = "CODEX_DIRECT"
    human_gold_status: Literal["UNANNOTATED"] = "UNANNOTATED"
    silver_status: Literal["COMPLETE", "READY_WITH_LIMITATIONS", "NOT_READY"]
    selected_mantra_count: int = Field(ge=0)
    reviewed_mantra_count: int = Field(ge=0)
    evidence_packet_hashes: dict[str, str]
    output_hashes: dict[str, str]
    unlocked_predicates: list[str] = Field(default_factory=list, max_length=0)
    created_at: datetime
    schema_version: str = SCHEMA_VERSION
