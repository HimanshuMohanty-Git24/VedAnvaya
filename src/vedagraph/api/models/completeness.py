"""Certified data-completeness models for user-facing surfaces.

Exposes the certified post-campaign data completeness and release state,
guaranteeing a single authoritative source of truth across all frontend pages.
"""

from __future__ import annotations

from pydantic import Field

from vedagraph.api.models.common import ApiModel, CaveatView, KnowledgeStatus


class CorpusCompletenessItem(ApiModel):
    """One canonical Samhita's certified invariant scope and metrics."""

    veda: str
    traditional_name: str
    devanagari_name: str
    recension: str
    scope_honest_label: str
    scope_note: str
    canonical_mantras: int
    structure: str
    excluded_corpora: list[str] = Field(default_factory=list)
    limitations: str


class TranslationVedaItem(ApiModel):
    """Typed translation coverage for one corpus."""

    veda: str
    total_mantras: int
    dedicated_english: int
    range_covered: int
    reused_rendering: int
    non_english: int
    uncovered: int
    independent_english: int
    coverage_percentage: float
    notes: str


class TranslationCompletenessSummary(ApiModel):
    """Overall translation coverage with typed categories."""

    by_veda: dict[str, TranslationVedaItem]
    total_mantras: int
    total_dedicated_english: int
    total_range_covered: int
    total_reused_rendering: int
    total_non_english: int
    total_uncovered: int
    truth_statement: str


class SamavedaNotationCompleteness(ApiModel):
    """Certified status of the Samaveda notation and Gāna scope."""

    canonical_corpus_mantras: int = 1844
    validated_notation_witnesses: int = 1136
    gates_passed: list[str] = Field(
        default_factory=lambda: ["Gate A: PASS", "Gate B: PASS", "Gate C: SURVIVED"]
    )
    evidence_class: str = "PARALLEL_WITNESS / PARALLEL_TEXT"
    notation_system: str = "Kauthuma numeric svara (source-printed codepoints)"
    source_supplied: bool = True
    interpreted_into_pitch: bool = False
    unaligned_withheld_verses: int = 708
    withheld_reason: str = "Unaligned or unsupported notation rows withheld"
    gana_object_layer: str = "OUT_OF_SCOPE"
    gana_works_modeled: int = 0
    musicalized_as_edges: int = 0
    truth_statement: str


class AudioCompleteness(ApiModel):
    """Certified public recitation audio and audible review gate status."""

    released_catalogue_records: int
    released_by_veda: dict[str, int]
    released_scope_keys_by_veda: dict[str, int]
    owner_audible_sample_status: str
    owner_sample_reviewed: int
    owner_sample_verified: int
    owner_sample_rejected: int
    queue_total: int
    not_individually_heard: int
    queue_rows_promoted: int
    withheld_gates: list[str]
    truth_statement: str


class AskBenchmarkCompleteness(ApiModel):
    """Certified Ask formal 60 benchmark verification result."""

    benchmark_version: str
    status: str
    total_questions: int
    effective_acceptable: str
    supported_correct: int
    partial_correct: int
    insufficient_evidence_refused: int
    misleading: int
    hallucinated: int
    truth_statement: str


class EvidenceLayersCompleteness(ApiModel):
    """The four knowledge evidence layers and grounding rules."""

    source_explicit: str
    deterministic_derived: str
    semantic_model_assisted: str
    interpretive_claim: str
    normalization_rule: str
    predicate_reach_rule: str


class CompletenessResponse(ApiModel):
    """The complete certified data-completeness state of VedAnvaya."""

    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    certified_release_commit: str = "50a40429103fa32a5667ee58c72c029cfbeb0f74"
    corpora: list[CorpusCompletenessItem]
    translations: TranslationCompletenessSummary
    samaveda_notation: SamavedaNotationCompleteness
    audio: AudioCompleteness
    ask_benchmark: AskBenchmarkCompleteness
    evidence_layers: EvidenceLayersCompleteness
    caveats: list[CaveatView] = Field(default_factory=list)
