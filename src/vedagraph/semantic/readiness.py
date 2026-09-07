"""Engineering audit records; deliberately separate from semantic truth and gold."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GapClassification(StrEnum):
    TRUE_SCHEMA_GAP = "TRUE_SCHEMA_GAP"
    INTENTIONAL_OPAQUE_CASE = "INTENTIONAL_OPAQUE_CASE"
    CANONICAL_ENTITY_RESOLUTION_MISSED = "CANONICAL_ENTITY_RESOLUTION_MISSED"
    WRONG_GAP_CODE = "WRONG_GAP_CODE"
    EXTRACTION_OVERREACH = "EXTRACTION_OVERREACH"
    EXPERT_PHILOLOGY_REQUIRED = "EXPERT_PHILOLOGY_REQUIRED"


class ParallelClassification(StrEnum):
    CONTEXT_JUSTIFIED_DIFFERENCE = "CONTEXT_JUSTIFIED_DIFFERENCE"
    TEXT_VARIANT_JUSTIFIED_DIFFERENCE = "TEXT_VARIANT_JUSTIFIED_DIFFERENCE"
    TRANSLATION_VARIANT_EFFECT = "TRANSLATION_VARIANT_EFFECT"
    PREDICATE_BOUNDARY_AMBIGUITY = "PREDICATE_BOUNDARY_AMBIGUITY"
    OBJECT_GRANULARITY_DIFFERENCE = "OBJECT_GRANULARITY_DIFFERENCE"
    EXTRACTION_INCONSISTENCY = "EXTRACTION_INCONSISTENCY"
    PARALLEL_MATCH_FALSE_POSITIVE = "PARALLEL_MATCH_FALSE_POSITIVE"
    EXPERT_PHILOLOGY_REQUIRED = "EXPERT_PHILOLOGY_REQUIRED"


class ReviewClassification(StrEnum):
    ARCHITECTURE_BUG = "ARCHITECTURE_BUG"
    EVIDENCE_PACKET_BUG = "EVIDENCE_PACKET_BUG"
    ONTOLOGY_GAP = "ONTOLOGY_GAP"
    PREDICATE_BOUNDARY = "PREDICATE_BOUNDARY"
    OBJECT_GRANULARITY = "OBJECT_GRANULARITY"
    TRANSLATION_AMBIGUITY = "TRANSLATION_AMBIGUITY"
    PHILOLOGY_REQUIRED = "PHILOLOGY_REQUIRED"
    EXPECTED_MODEL_UNCERTAINTY = "EXPECTED_MODEL_UNCERTAINTY"
    SAFE_REVIEW_ONLY = "SAFE_REVIEW_ONLY"
    CANONICAL_ENTITY_RISK = "CANONICAL_ENTITY_RISK"
    TYPE_BOUNDARY_RISK = "TYPE_BOUNDARY_RISK"


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1)
    passage_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    blocker_ids: list[str] = Field(default_factory=list)
    decision: Literal["BLOCKS_FULL_RUN", "DOES_NOT_BLOCK_FULL_RUN"]
    provenance: Literal["ENGINEERING_DIAGNOSTIC"] = "ENGINEERING_DIAGNOSTIC"

    @model_validator(mode="after")
    def blocker_evidence(self) -> "Diagnostic":
        if bool(self.blocker_ids) != (self.decision == "BLOCKS_FULL_RUN"):
            raise ValueError("blocking requires a concrete engineering blocker ID")
        return self


class GapAudit(Diagnostic):
    classification: GapClassification
    person_ref: Literal["USEFUL", "UNSAFE", "EXPERT_REQUIRED"]


class ParallelAudit(Diagnostic):
    classification: ParallelClassification


class ReviewAudit(Diagnostic):
    classification: ReviewClassification
    secondary_tags: list[ReviewClassification] = Field(default_factory=list)


def readiness_state(blockers: list[str], *, frozen: bool, operations_ready: bool) -> str:
    if blockers or not frozen or not operations_ready:
        return "FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED"
    return "FULL_RIGVEDA_V3_CANDIDATE_RUN_READY"
