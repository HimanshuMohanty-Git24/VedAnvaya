"""Ask VedaGraph request/response contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from vedagraph.api.models.common import ApiModel, CaveatView, KnowledgeStatus


class AskMode(StrEnum):
    AUTO = "AUTO"
    TEXTUAL = "TEXTUAL"
    GRAPH = "GRAPH"
    COMPARATIVE = "COMPARATIVE"
    RESEARCH = "RESEARCH"


class SupportLevel(StrEnum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class QueryIntent(StrEnum):
    PASSAGE_LOOKUP = "PASSAGE_LOOKUP"
    ENTITY_PROFILE = "ENTITY_PROFILE"
    DEITY_COMPARISON = "DEITY_COMPARISON"
    RISHI = "RISHI"
    RITUAL = "RITUAL"
    HUMAN_CONCERN = "HUMAN_CONCERN"
    FORMULA = "FORMULA"
    CROSS_VEDA = "CROSS_VEDA"
    TEXTUAL_REUSE = "TEXTUAL_REUSE"
    CONCEPT = "CONCEPT"
    MATERIAL_CULTURE = "MATERIAL_CULTURE"
    GRAPH_CONNECTION = "GRAPH_CONNECTION"
    EVIDENCE_EXPLANATION = "EVIDENCE_EXPLANATION"
    INTERPRETIVE_CLAIM = "INTERPRETIVE_CLAIM"
    STATISTICS = "STATISTICS"
    GENERAL_VEDIC_QUERY = "GENERAL_VEDIC_QUERY"


class ConversationTurn(ApiModel):
    role: str  # "user" or "assistant"
    content: str = Field(max_length=4000)


class AskRequest(ApiModel):
    question: str = Field(min_length=1, max_length=2000)
    veda: str | None = Field(default=None, pattern="^(RV|SV|YV|AV|ALL)$")
    passage_context: str | None = Field(default=None, max_length=200)
    entity_context: str | None = Field(default=None, max_length=200)
    conversation_context: list[ConversationTurn] | None = Field(default=None, max_length=10)
    mode: AskMode = AskMode.AUTO
    debug: bool = False


class EvidenceItemType(StrEnum):
    PASSAGE = "PASSAGE"
    ENTITY_FACT = "ENTITY_FACT"
    GRAPH_PATH = "GRAPH_PATH"
    METRIC = "METRIC"
    INTERPRETIVE_CLAIM = "INTERPRETIVE_CLAIM"
    FORMULA_FAMILY = "FORMULA_FAMILY"
    TEXTUAL_REUSE = "TEXTUAL_REUSE"

    ATTRIBUTION = "ATTRIBUTION"
    """A hymn *dedicated to* a deity. Never interchangeable with a mention of it."""

    CORPUS_DISTRIBUTION = "CORPUS_DISTRIBUTION"
    """Per-Veda counts with all three referent-certainty tiers reported."""

    LEXICAL_PRESENCE = "LEXICAL_PRESENCE"
    """A measured search for a term across all four corpora, with the searchable surface
    of each reported alongside the hit count.

    The item type that makes absence sayable. Without it, a term found nowhere yields an
    empty packet -- and an empty packet is what a model answers from memory.
    """


class EvidenceItem(ApiModel):
    """One citable unit of retrieved evidence."""

    id: str = Field(description="Stable within one response: E1, E2, E3 ...")
    type: EvidenceItemType
    passage_key: str | None = None
    citation: str | None = None
    veda: str | None = None
    sanskrit: str | None = None
    translation: str | None = None
    entity_label: str | None = None
    entity_type: str | None = None
    entity_key: str | None = None
    fact: str | None = None
    relationship_type: str | None = None
    source_label: str | None = None
    target_label: str | None = None
    claim_text: str | None = None
    claim_source: str | None = None
    evidence_basis: str | None = None
    knowledge_status: str | None = None
    qualifier: str | None = Field(
        default=None,
        description="What this item does NOT establish, travelling with the item rather "
        "than in a preamble. A translation is not the Sanskrit, an AMBIGUOUS mention is "
        "not a deity occurrence, an inherited attribution is not a per-verse statement, "
        "and a shared formula is not a claim of reuse. Rendered inline in the synthesis "
        "prompt so it is the nearest line to whatever the model writes next.",
    )


class CitationRef(ApiModel):
    id: str  # E1, E2, ...
    citation: str
    passage_key: str | None = None
    veda: str | None = None


class EntityMention(ApiModel):
    """A name the question used, and what the graph made of it."""

    label: str
    entity_key: str | None = None
    entity_type: str | None = None
    resolved: bool = Field(
        default=False,
        description="False means the graph has no entity under this name. Reported "
        "rather than dropped: 'VedaGraph has no Devata called Shiva' answers a question "
        "about Shiva, and a silently shortened list hides it.",
    )
    asked_as: str | None = Field(
        default=None, description="The spelling the question used, before folding."
    )
    match_rank: str | None = Field(
        default=None,
        description="How the name reached the node: EXACT_LABEL, EXACT_ALIAS or "
        "TOKEN_IN_LABEL. A token match is weaker and the response says so.",
    )


class RetrievalSummary(ApiModel):
    channels_used: list[str] = Field(default_factory=list)
    channels_empty: list[str] = Field(
        default_factory=list,
        description="Channels that ran and returned nothing. Distinct from a channel "
        "that was never selected: searched-and-empty is evidence, unexamined is not.",
    )
    intents: list[str] = Field(default_factory=list)
    entities_resolved: list[str] = Field(default_factory=list)
    entities_unresolved: list[str] = Field(default_factory=list)
    veda_scope: str = "ALL"
    evidence_count: int = 0
    planner_ms: float = 0.0
    retrieval_ms: float = 0.0
    synthesis_ms: float = 0.0
    total_ms: float = 0.0


class LLMInfo(ApiModel):
    provider: str
    model: str


class AskResponse(ApiModel):
    answer: str
    status: KnowledgeStatus
    support_level: SupportLevel
    citations: list[CitationRef] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    entities: list[EntityMention] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)
    caveats: list[CaveatView] = Field(default_factory=list)
    retrieval_summary: RetrievalSummary
    interpretive_content_present: bool = False
    llm: LLMInfo


class AskDebugInfo(ApiModel):
    query_plan: dict[str, Any]
    evidence_packet_preview: list[str]
    synthesis_prompt_length: int


class AskDebugResponse(AskResponse):
    debug: AskDebugInfo | None = None
