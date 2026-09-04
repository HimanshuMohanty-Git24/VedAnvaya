"""Data contracts for the semantic candidate layer.

Everything here is downstream of three read-only inputs — the canonical corpus, the
traditional metadata layer and the deterministic lexical layer — and none of it may be
written back into them.

The layer's central asymmetry is in the names: an :class:`EvidencePacket` is assembled
deterministically and is exactly what a model was shown; a
:class:`SemanticAssertionCandidate` is what the model said about it, and is not knowledge
until something other than the model says so.

Rights: no packet or candidate stored here is required to carry translation text.
Evidence points at record identifiers and carries a hash of the text it rests on, so an
assertion can be verified against a source the reader holds without this repository
redistributing that source.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.models.enums import (
    EvidenceSpanType,
    SemanticAssertionStatus,
    SemanticEntityResolution,
    SemanticValidationCode,
)
from vedagraph.semantic.ontology import (
    Explicitness,
    SemanticNodeType,
    SemanticPredicate,
    SemanticSubjectKind,
)

# --------------------------------------------------------------------------------------
# The evidence packet: what the model is shown, assembled without a model
# --------------------------------------------------------------------------------------


class PacketToken(VGModel):
    """One annotated Sanskrit token, offered as citable evidence.

    Token ids are what an assertion points at. A model claiming a word is in the mantra
    has to name the token that is, and the validator checks the name against this list.
    """

    token_key: str = Field(min_length=1)
    pada: str = Field(pattern=r"^[a-z]$")
    sequence: int = Field(ge=1)
    surface: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    part_of_speech: str | None = None
    morphology: dict[str, str] = Field(default_factory=dict)


class PacketMention(VGModel):
    """A deterministic lexical mention already established for this mantra.

    Supplied so the model does not re-derive it and, more importantly, so it can cite it
    rather than paraphrase it. This is a fact, not a hint.
    """

    entity_key: str = Field(min_length=1)
    entity_label: str = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    token_keys: list[str] = Field(min_length=1)


class PacketTranslation(VGModel):
    """A translation record referenced by id, with a hash of the text supplied.

    ``text`` is populated at request time from the local build and never reaches disk:
    only the hash does. See :meth:`EvidencePacket.index_row`.
    """

    translation_id: str = Field(min_length=1)
    translator: str = Field(min_length=1)
    language: str = Field(min_length=1)
    text: str | None = None
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PacketNeighbour(VGModel):
    """The mantra before or after the target, for context and nothing else.

    A neighbour may be cited as evidence only by an assertion whose subject is the
    target mantra; it never becomes a subject of its own in the same packet.
    """

    passage_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    citation: str = Field(min_length=1)
    sanskrit: str = Field(min_length=1)
    translation: PacketTranslation | None = None


class EvidencePacket(VGModel):
    """Everything one extraction request is allowed to see, and nothing else.

    Deliberately small. A whole Maṇḍala in the context window costs money, buys no
    precision, and makes an assertion's evidence impossible to check, because anything
    can be justified from enough text.
    """

    packet_version: str = Field(min_length=1)
    passage_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    passage_id: UUID
    citation: str = Field(min_length=1)
    mandala: int = Field(ge=1, le=10)
    sukta: int = Field(ge=1)
    mantra: int = Field(ge=1)

    sanskrit: str = Field(min_length=1)
    sanskrit_text_version_id: str = Field(min_length=1)
    translation: PacketTranslation | None = None
    #: Set when no translation exists for this mantra. The model is told, and is never
    #: asked to supply one: a generated translation would become evidence for the next
    #: claim, and the provenance would be a model citing itself.
    translation_missing: bool = False

    rishi_keys: list[str] = Field(default_factory=list)
    devata_keys: list[str] = Field(default_factory=list)
    chandas_keys: list[str] = Field(default_factory=list)
    rishi_labels: list[str] = Field(default_factory=list)
    devata_labels: list[str] = Field(default_factory=list)
    chandas_labels: list[str] = Field(default_factory=list)

    tokens: list[PacketToken] = Field(default_factory=list)
    mentions: list[PacketMention] = Field(default_factory=list)

    previous: PacketNeighbour | None = None
    next: PacketNeighbour | None = None
    sukta_mantra_count: int = Field(ge=1)

    exact_parallel_passage_keys: list[str] = Field(default_factory=list)
    near_parallel_passage_keys: list[str] = Field(default_factory=list)

    #: Hash of the packet as it was sent, with translation text present. Two runs with
    #: the same hash saw the same thing; that is the only reproducibility claim this
    #: layer makes, and it is a claim about the input, never about the output.
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str = SCHEMA_VERSION

    @property
    def citable_token_keys(self) -> frozenset[str]:
        return frozenset(token.token_key for token in self.tokens)

    @property
    def citable_passage_keys(self) -> frozenset[str]:
        keys = {self.passage_key}
        for neighbour in (self.previous, self.next):
            if neighbour is not None:
                keys.add(neighbour.passage_key)
        return frozenset(keys)

    def index_row(self) -> dict[str, object]:
        """What was sent, as identifiers and hashes, with no source text at all.

        This is the only form of a packet that is written to disk. A reviewer holding
        the same pinned build can rebuild the packet from ``passage_key`` and check it
        against ``input_sha256``; a reader without the sources learns nothing they were
        not already entitled to. Storing the text instead would duplicate the corpus
        into every run directory for no gain.
        """
        return {
            "packet_version": self.packet_version,
            "passage_key": self.passage_key,
            "citation": self.citation,
            "input_sha256": self.input_sha256,
            "sanskrit_sha256": hashlib.sha256(self.sanskrit.encode("utf-8")).hexdigest(),
            "sanskrit_text_version_id": self.sanskrit_text_version_id,
            "translation_id": self.translation.translation_id if self.translation else None,
            "translation_sha256": self.translation.text_sha256 if self.translation else None,
            "translation_missing": self.translation_missing,
            "rishi_keys": list(self.rishi_keys),
            "devata_keys": list(self.devata_keys),
            "chandas_keys": list(self.chandas_keys),
            "token_count": len(self.tokens),
            "mention_entity_keys": [item.entity_key for item in self.mentions],
            "previous_passage_key": self.previous.passage_key if self.previous else None,
            "next_passage_key": self.next.passage_key if self.next else None,
            "sukta_mantra_count": self.sukta_mantra_count,
            "exact_parallel_passage_keys": list(self.exact_parallel_passage_keys),
            "near_parallel_passage_keys": list(self.near_parallel_passage_keys),
        }


# --------------------------------------------------------------------------------------
# Semantic entities: proposed, resolved, never minted on the spot
# --------------------------------------------------------------------------------------


class SemanticEntityCandidate(VGModel):
    """A concept a model proposed. Not yet an entity, and not given a canonical id.

    ``candidate_id`` is derived from the normalized label and type, so the same proposal
    from two mantras is one candidate with two source mantras — which is what makes
    ``evidence_count`` mean anything.
    """

    candidate_id: str = Field(min_length=1)
    entity_type: SemanticNodeType
    preferred_label: str = Field(min_length=1)
    normalized_label: str = Field(min_length=1)
    description: str = Field(default="")
    aliases: list[str] = Field(default_factory=list)
    source_passage_keys: list[str] = Field(default_factory=list)
    evidence_count: int = Field(ge=0, default=0)
    created_by_model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    resolution: SemanticEntityResolution = SemanticEntityResolution.NEEDS_REVIEW
    #: Set only by an exact registry hit. Similarity never fills this in.
    matched_entity_key: str | None = None
    #: Registry rows a reviewer should compare this against. Advisory, never applied.
    review_candidate_keys: list[str] = Field(default_factory=list)
    resolution_reason: str = Field(default="")
    schema_version: str = SCHEMA_VERSION


class SemanticEntityRegistryRow(VGModel):
    """A reviewed semantic entity. Only a person's decision puts a row in this file."""

    entity_key: str = Field(pattern=r"^VG:SEM:[A-Z_]+:[A-Z0-9_]+$")
    entity_type: SemanticNodeType
    preferred_label: str = Field(min_length=1)
    normalized_label: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    description: str = Field(default="")
    evidence: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION


# --------------------------------------------------------------------------------------
# Assertions
# --------------------------------------------------------------------------------------


class SemanticEvidence(VGModel):
    """One thing an assertion rests on, precise enough to be checked or refused."""

    passage_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    span_type: EvidenceSpanType
    translation_id: str | None = None
    sanskrit_token_keys: list[str] = Field(default_factory=list)
    #: Hash of the exact supplied text the model says it used. Never the text itself.
    evidence_text_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    note: str = Field(default="")

    @model_validator(mode="after")
    def span_type_matches_payload(self) -> SemanticEvidence:
        if self.span_type is EvidenceSpanType.SANSKRIT_TOKEN and not self.sanskrit_token_keys:
            raise ValueError("SANSKRIT_TOKEN evidence must name at least one token")
        if self.span_type is EvidenceSpanType.TRANSLATION_LINE and not self.translation_id:
            raise ValueError("TRANSLATION_LINE evidence must name a translation record")
        return self


class SemanticAssertionObject(VGModel):
    """Exactly one of: an existing canonical entity, or a proposed semantic concept."""

    entity_key: str | None = None
    candidate_entity_id: str | None = None
    node_type: SemanticNodeType | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> SemanticAssertionObject:
        if bool(self.entity_key) == bool(self.candidate_entity_id):
            raise ValueError("an object names either a canonical entity or a candidate, not both")
        if self.candidate_entity_id and self.node_type is None:
            raise ValueError("a candidate object must declare its node type")
        return self


class SemanticAssertionCandidate(VGModel):
    """What a model proposed about one passage. A proposal, in the file, with its receipts.

    ``confidence`` is the model's self-assessment and has no authority. It is stored
    because it is cheap and occasionally diagnostic, and it is used only as a floor
    inside a predicate's own acceptance rule — never as a reason on its own. See
    :func:`vedagraph.semantic.validate.decide_status`.
    """

    candidate_assertion_id: str = Field(min_length=1)
    subject_key: str = Field(min_length=1)
    subject_kind: SemanticSubjectKind
    predicate: SemanticPredicate
    object: SemanticAssertionObject
    evidence: list[SemanticEvidence] = Field(default_factory=list)
    explicitness: Explicitness
    confidence: float = Field(ge=0.0, le=1.0)
    model: str = Field(min_length=1)
    model_snapshot: str | None = None
    reasoning_effort: str | None = None
    prompt_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: SemanticAssertionStatus = SemanticAssertionStatus.CANDIDATE
    schema_version: str = SCHEMA_VERSION

    #: pydantic reserves the ``model_`` prefix for its own namespace; ``model`` and
    #: ``model_snapshot`` are the field names this project's schemas use, so the
    #: protection is turned off here rather than the fields renamed.
    model_config = VGModel.model_config | {"protected_namespaces": ()}


class SemanticValidationResult(VGModel):
    """The deterministic verdict on one candidate, and why."""

    candidate_assertion_id: str = Field(min_length=1)
    codes: list[SemanticValidationCode] = Field(default_factory=list)
    status: SemanticAssertionStatus
    reason: str = Field(default="")
    #: Set when the proposal is compatible with the text but sits oddly beside the
    #: Anukramaṇī. Not a rejection: traditional assignment and textual content differ
    #: legitimately and often, which is why they are separate predicates.
    conflicts_with_metadata: bool = False
    schema_version: str = SCHEMA_VERSION

    @property
    def accepted(self) -> bool:
        return self.status in {
            SemanticAssertionStatus.AUTO_ACCEPTED,
            SemanticAssertionStatus.HUMAN_ACCEPTED,
        }


# --------------------------------------------------------------------------------------
# Gold data, runs and cost
# --------------------------------------------------------------------------------------


class GoldRelation(VGModel):
    """One relation a human annotator says is present, or says is tempting but absent."""

    predicate: SemanticPredicate
    object_label: str = Field(min_length=1)
    object_node_type: SemanticNodeType | None = None
    object_entity_key: str | None = None
    explicitness: Explicitness
    #: A relation a careful reader would be drawn to and which the text does not support.
    #: Scoring these separately is how the evaluation measures restraint rather than only
    #: recall.
    rejected: bool = False
    note: str = Field(default="")


class GoldAnnotation(VGModel):
    """The reviewed expectation for one mantra. Written by a person, never by a model."""

    passage_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    citation: str = Field(min_length=1)
    annotator: str = Field(min_length=1)
    annotated_at: datetime
    entities: list[str] = Field(default_factory=list)
    relations: list[GoldRelation] = Field(default_factory=list)
    notes: str = Field(default="")
    schema_version: str = SCHEMA_VERSION


class TokenUsage(VGModel):
    """Actual usage reported by the API. Never an estimate when a real number exists."""

    requests: int = Field(ge=0, default=0)
    input_tokens: int = Field(ge=0, default=0)
    cached_input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    reasoning_tokens: int = Field(ge=0, default=0)

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            requests=self.requests + other.requests,
            input_tokens=self.input_tokens + other.input_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


class SemanticRunManifest(VGModel):
    """What was run, against what, with which configuration, and what it produced."""

    run_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    corpus_version: str = Field(min_length=1)
    corpus_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    traditional_knowledge_manifest_sha256: str = ""
    lexical_knowledge_manifest_sha256: str = ""
    pilot_config_sha256: str = ""
    prompt_sha256: str = ""
    lexical_policy_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    acceptance_policy_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    packet_version: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    extraction_runtime: str = "API"
    api_invocation: bool = False
    model: str = Field(min_length=1)
    model_snapshot: str | None = None
    reasoning_effort: str = Field(min_length=1)
    max_output_tokens: int = Field(ge=1)
    temperature: float | None = None
    passage_count: int = Field(ge=0)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    input_cost_usd_per_million: float = Field(ge=0.0)
    cached_input_cost_usd_per_million: float = Field(ge=0.0)
    output_cost_usd_per_million: float = Field(ge=0.0)
    total_cost_usd: float = Field(ge=0.0, default=0.0)
    batch_count: int = Field(ge=0, default=0)
    batch_size: int = Field(ge=0, default=0)
    unlocked_predicates: list[str] = Field(default_factory=list)
    gold_status: str = "UNANNOTATED"
    validator_version: str = ""
    qa_result: str = ""
    packet_hashes: dict[str, str] = Field(default_factory=dict)
    output_hashes: dict[str, str] = Field(default_factory=dict)
    notes: str = Field(default="")
    schema_version: str = SCHEMA_VERSION

    model_config = VGModel.model_config | {"protected_namespaces": ()}
