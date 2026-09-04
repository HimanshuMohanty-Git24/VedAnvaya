"""Data contracts for the deterministic lexical and cross-mantra knowledge layer.

The layer rests on one distinction, which nothing in this module is allowed to blur:

``HAS_DEVATA``
    traditional metadata assigns a deity to a mantra. It lives in
    :mod:`vedagraph.models.knowledge` and is untouched here.

``MENTIONS_ENTITY``
    the Sanskrit text of the mantra itself contains a word whose annotated lemma
    resolves to a canonical entity.

A mantra assigned to Agni need not mention Agni, and a mantra mentioning Agni need not
be assigned to Agni. Both facts are recorded, separately, and never merged.

Staging is as strict as in the traditional layer:

``MorphologyToken``
    one token of the pinned annotation layer, verbatim, aligned to a canonical mantra by
    structural citation only.

``LexicalAlias``
    a reviewed statement that one lemma may establish a mention of one entity. Being an
    ``EntityAlias`` in the entity registry does *not* make a string a lexical alias.

``MentionAssertion``
    a mantra-to-entity edge that always carries the tokens that evidence it.

``MantraParallel`` / ``ParallelCandidate``
    within-corpus repetition, with the representation the match was found at recorded,
    never flattened into one opaque "similar" flag.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, Field, model_validator

from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.models.enums import (
    KnowledgeEntityType,
    LexicalAliasType,
    LexicalMatchStatus,
    LexicalPredicate,
    LexicalProvenanceClass,
    MentionMethod,
    ParallelMethod,
    ParallelStatus,
    ParallelUnit,
    QAStatus,
    ReviewStatus,
)

#: Lexical alias classes a mention may ever be built from. ``DO_NOT_MATCH`` is a
#: suppression rule and never appears here.
#:
#: ``COMPOSITE_NAME`` is included, but only because the annotation layer supplies
#: dvandvas such as ``indrāgní-`` as single lexical entries with their own lemma ids.
#: The mention therefore rests on an annotated lemma, exactly like any other. Splitting
#: a compound ourselves to manufacture component mentions remains forbidden.
MENTION_BEARING_ALIAS_TYPES = frozenset(
    {
        LexicalAliasType.CANONICAL_LEMMA,
        LexicalAliasType.ORTHOGRAPHIC_VARIANT,
        LexicalAliasType.KNOWN_LEMMA_VARIANT,
        LexicalAliasType.INFLECTIONAL_SOURCE_FORM,
        LexicalAliasType.EPITHET_REVIEWED,
        LexicalAliasType.COMPOSITE_NAME,
    }
)

#: Entity families v1 attempts literal mention extraction for. Chandas is excluded on
#: purpose: a metre name occurring in the text does not mean the mantra "mentions its
#: metre", and treating it that way would corrupt the metadata/lexical distinction.
MENTION_ENTITY_TYPES: tuple[KnowledgeEntityType, ...] = (
    KnowledgeEntityType.DEVATA,
    KnowledgeEntityType.RISHI,
)


class MorphologyToken(VGModel):
    """One annotated token of the pinned morphology layer.

    ``surface_form`` is the annotation layer's own reading and is *not* the canonical
    Sanskrit. The canonical text remains ``GRETIL.RV.AUFRECHT``; this record only ever
    references a mantra, it never replaces its text.
    """

    token_id: UUID
    token_key: str = Field(
        pattern=r"^VG:TOKEN:[A-Z0-9-]+:RV:SAK:M\d{2}:S\d{3}:V\d{3}:P[A-Z]:T\d{3}$"
    )
    canonical_urn: str = Field(pattern=r"^urn:vedagraph:token:")
    passage_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    passage_id: UUID
    annotation_layer_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    pada: str = Field(pattern=r"^[a-z]$")
    pada_sequence: int = Field(ge=1)
    surface_form: str = Field(min_length=1)
    normalized_surface: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    normalized_lemma: str = Field(min_length=1)
    lemma_ids: list[str] = Field(default_factory=list)
    part_of_speech: str | None = None
    morphological_features: dict[str, str] = Field(default_factory=dict)
    annotation_provenance: str = Field(min_length=1)
    annotation_method: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def sequence_matches_key(self) -> MorphologyToken:
        if self.token_key.endswith(f":T{self.sequence:03d}") is False:
            raise ValueError("token_key sequence must match the sequence field")
        if not self.token_key.endswith(f":P{self.pada.upper()}:T{self.sequence:03d}"):
            raise ValueError("token_key pāda must match the pada field")
        return self


class LemmaRecord(VGModel):
    """One distinct lemma of the annotation layer, with where it occurs.

    This is the inventory the lexical alias registry is reviewed against. It is derived
    data, not a claim about meaning.
    """

    lemma: str = Field(min_length=1)
    normalized_lemma: str = Field(min_length=1)
    lemma_ids: list[str] = Field(default_factory=list)
    parts_of_speech: list[str] = Field(default_factory=list)
    token_count: int = Field(ge=1)
    mantra_count: int = Field(ge=1)
    example_passage_keys: list[str] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


class LexicalAlias(VGModel):
    """A reviewed statement that one lemma may evidence a mention of one entity.

    Every alias carries ``review_status`` and ``evidence``. An alias that is not
    ``ACCEPTED`` never produces a ``MENTIONS_ENTITY`` edge, whatever its type.
    """

    alias_id: UUID
    alias_key: str = Field(min_length=1)
    entity_key: str = Field(pattern=r"^VG:(RISHI|DEVATA|CHANDAS):[A-Z0-9-]+$")
    entity_type: KnowledgeEntityType
    lemma: str = Field(min_length=1)
    normalized_lemma: str = Field(min_length=1)
    lemma_ids: list[str] = Field(default_factory=list)
    alias_type: LexicalAliasType
    review_status: ReviewStatus
    evidence: str = Field(min_length=1)
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    @property
    def may_produce_mention(self) -> bool:
        return (
            self.review_status is ReviewStatus.ACCEPTED
            and self.alias_type in MENTION_BEARING_ALIAS_TYPES
        )


class LexicalAliasCandidate(VGModel):
    """A machine-proposed lemma/entity pairing awaiting human review.

    Candidates exist so that similarity has somewhere to go that is *not* a graph edge.
    Nothing in this record may ever be promoted automatically.
    """

    candidate_key: str = Field(min_length=1)
    entity_key: str = Field(pattern=r"^VG:(RISHI|DEVATA|CHANDAS):[A-Z0-9-]+$")
    entity_type: KnowledgeEntityType
    entity_label: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    normalized_lemma: str = Field(min_length=1)
    lemma_ids: list[str] = Field(default_factory=list)
    proposal_rule: str = Field(min_length=1)
    token_count: int = Field(ge=0)
    mantra_count: int = Field(ge=0)
    competing_entity_keys: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    schema_version: str = SCHEMA_VERSION


class MentionEvidence(VGModel):
    """One token that evidences a mention, precise enough to highlight in a UI."""

    token_id: UUID
    token_key: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    pada: str = Field(pattern=r"^[a-z]$")
    surface: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    alias_id: UUID
    alias_key: str = Field(min_length=1)
    method: MentionMethod


class MentionAssertion(VGModel):
    """One mantra mentions one canonical entity, with every occurrence recorded.

    A mantra naming the same entity three times produces one edge whose evidence lists
    three tokens: the graph stays simple, the textual record stays complete.
    """

    assertion_id: UUID
    subject_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    subject_id: UUID
    predicate: LexicalPredicate = LexicalPredicate.MENTIONS_ENTITY
    object_key: str = Field(pattern=r"^VG:(RISHI|DEVATA):[A-Z0-9-]+$")
    object_id: UUID
    entity_type: KnowledgeEntityType
    occurrence_count: int = Field(ge=1)
    evidence: list[MentionEvidence] = Field(min_length=1)
    methods: list[MentionMethod] = Field(min_length=1)
    provenance_class: LexicalProvenanceClass = LexicalProvenanceClass.DETERMINISTIC_DERIVED
    annotation_layer_id: str = Field(min_length=1)
    source_artifact_ids: list[str] = Field(min_length=1)
    mention_policy_version: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def evidence_matches_count(self) -> MentionAssertion:
        if self.occurrence_count != len(self.evidence):
            raise ValueError("occurrence_count must equal the number of evidence tokens")
        if self.predicate is not LexicalPredicate.MENTIONS_ENTITY:
            raise ValueError("MentionAssertion carries only MENTIONS_ENTITY")
        return self


class AmbiguousMention(VGModel):
    """A token whose lemma could name more than one entity, deliberately not resolved.

    No ``MENTIONS_ENTITY`` edge exists for these. They are reported so a reviewer can
    decide, and so the absence is visible rather than silent.
    """

    passage_key: str = Field(min_length=1)
    token_key: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    normalized_lemma: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    status: LexicalMatchStatus
    candidate_entity_keys: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION


class ComponentAssertion(VGModel):
    """A reviewed composite Devatā and one of its components.

    Only rows a human marked ``ACCEPTED`` in ``data/registry/devata_components.yaml``
    reach this record. Composition is never inferred from a hyphen, a dual ending, or
    membership in a group label.
    """

    assertion_id: UUID
    subject_key: str = Field(pattern=r"^VG:DEVATA:[A-Z0-9-]+$")
    subject_id: UUID
    predicate: LexicalPredicate = LexicalPredicate.HAS_COMPONENT
    object_key: str = Field(pattern=r"^VG:DEVATA:[A-Z0-9-]+$")
    object_id: UUID
    component_sequence: int = Field(ge=1)
    provenance_class: LexicalProvenanceClass = LexicalProvenanceClass.HUMAN_REVIEWED
    evidence: str = Field(min_length=1)
    review_status: ReviewStatus
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def reviewed_only(self) -> ComponentAssertion:
        if self.review_status is not ReviewStatus.ACCEPTED:
            raise ValueError("only ACCEPTED component mappings become HAS_COMPONENT")
        if self.provenance_class is not LexicalProvenanceClass.HUMAN_REVIEWED:
            raise ValueError("HAS_COMPONENT is human-reviewed enrichment")
        if self.subject_key == self.object_key:
            raise ValueError("a composite entity is not its own component")
        return self


class ParallelMetrics(VGModel):
    """Individual deterministic similarity measurements for one mantra pair.

    They are stored separately and never fused into a single opaque score. A policy may
    combine them, but the policy is versioned and the inputs stay inspectable.
    """

    token_jaccard: float = Field(ge=0.0, le=1.0)
    lemma_jaccard: float = Field(ge=0.0, le=1.0)
    ordered_token_similarity: float = Field(ge=0.0, le=1.0)
    normalized_edit_similarity: float = Field(ge=0.0, le=1.0)
    character_ngram_similarity: float = Field(ge=0.0, le=1.0)
    length_ratio: float = Field(ge=0.0, le=1.0)
    shared_token_count: int = Field(ge=0)
    left_token_count: int = Field(ge=0)
    right_token_count: int = Field(ge=0)


class MantraParallel(VGModel):
    """One canonical, order-normalized parallel between two distinct mantras.

    The pair is always stored with ``subject_key < object_key`` so A-B and B-A cannot
    both exist. Rendering it in both directions is a graph-loading concern, not a
    storage one.
    """

    assertion_id: UUID
    subject_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    subject_id: UUID
    object_key: str = Field(pattern=r"^VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}$")
    object_id: UUID
    predicate: LexicalPredicate
    unit: ParallelUnit = ParallelUnit.MANTRA
    subject_locator: str | None = None
    object_locator: str | None = None
    status: ParallelStatus
    methods: list[ParallelMethod] = Field(default_factory=list)
    strongest_method: ParallelMethod | None = None
    metrics: ParallelMetrics | None = None
    group_id: str | None = None
    provenance_class: LexicalProvenanceClass = LexicalProvenanceClass.DETERMINISTIC_DERIVED
    parallel_policy_version: str = Field(min_length=1)
    text_version_id: str = Field(min_length=1)
    subject_citation: str = Field(min_length=1)
    object_citation: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def canonical_pair_order(self) -> MantraParallel:
        if self.subject_key >= self.object_key:
            raise ValueError("parallel pairs are stored with subject_key < object_key")
        if self.predicate not in {
            LexicalPredicate.EXACT_PARALLEL_OF,
            LexicalPredicate.PARALLEL_TO,
        }:
            raise ValueError("a parallel carries EXACT_PARALLEL_OF or PARALLEL_TO")
        if self.predicate is LexicalPredicate.EXACT_PARALLEL_OF and not self.methods:
            raise ValueError("an exact parallel must record the representation it matched at")
        return self


class ParallelCandidate(VGModel):
    """A scored pair that did not reach the accepted threshold, kept for review."""

    candidate_key: str = Field(min_length=1)
    subject_key: str = Field(min_length=1)
    object_key: str = Field(min_length=1)
    subject_citation: str = Field(min_length=1)
    object_citation: str = Field(min_length=1)
    status: ParallelStatus
    metrics: ParallelMetrics
    stratum: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION


class ExactParallelGroup(VGModel):
    """A set of mantras identical at one representation level."""

    group_id: str = Field(min_length=1)
    method: ParallelMethod
    member_keys: list[str] = Field(min_length=2)
    member_citations: list[str] = Field(min_length=2)
    mandalas: list[int] = Field(default_factory=list)
    size: int = Field(ge=2)
    schema_version: str = SCHEMA_VERSION


class EntityCoOccurrence(VGModel):
    """How often two entities are *lexically mentioned* in the same mantra.

    This is a statistical observation with a stated unit, not a semantic relationship.
    No ``RELATED_TO`` edge is derived from it.
    """

    left_entity_key: str = Field(min_length=1)
    right_entity_key: str = Field(min_length=1)
    left_label: str = Field(min_length=1)
    right_label: str = Field(min_length=1)
    count: int = Field(ge=1)
    unit: str = "MANTRA"
    method: str = "LEXICAL_MENTION_CO_OCCURRENCE"

    @model_validator(mode="after")
    def canonical_pair_order(self) -> EntityCoOccurrence:
        if self.left_entity_key >= self.right_entity_key:
            raise ValueError("co-occurrence pairs are stored with left < right")
        return self


class EntityLexicalFrequency(VGModel):
    """Three separate counts for one entity, which must never be merged.

    ``mantra_assignment_count``
        traditional metadata (``HAS_DEVATA`` / ``HAS_RISHI``).
    ``mantra_mention_count``
        mantras whose text lexically mentions the entity.
    ``token_occurrence_count``
        total tokens across the corpus resolving to the entity.

    "Most used god" is not one of these. It is three different questions.
    """

    entity_key: str = Field(min_length=1)
    preferred_label: str = Field(min_length=1)
    entity_type: KnowledgeEntityType
    mantra_assignment_count: int = Field(ge=0)
    mantra_mention_count: int = Field(ge=0)
    token_occurrence_count: int = Field(ge=0)
    assigned_and_mentioned_count: int = Field(ge=0)
    assigned_not_mentioned_count: int = Field(ge=0)
    mentioned_not_assigned_count: int = Field(ge=0)


class MandalaMentionStats(VGModel):
    """Mention density per Mandala, so coverage gaps are visible by book."""

    mandala: int = Field(ge=1, le=10)
    mantras: int = Field(ge=0)
    mantras_with_mentions: int = Field(ge=0)
    mention_assertions: int = Field(ge=0)
    token_occurrences: int = Field(ge=0)


class LexicalStats(VGModel):
    """Deterministic analytics for the lexical and cross-mantra layer."""

    metric_definitions: dict[str, str]
    total_mantras: int = Field(ge=0)
    mantras_with_morphology: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    tokens_with_lemma: int = Field(ge=0)
    distinct_lemmas: int = Field(ge=0)
    accepted_lexical_aliases: int = Field(ge=0)
    do_not_match_aliases: int = Field(ge=0)
    alias_candidates: int = Field(ge=0)
    mention_assertions: int = Field(ge=0)
    mention_token_occurrences: int = Field(ge=0)
    mantras_with_mentions: int = Field(ge=0)
    mantras_without_mentions: int = Field(ge=0)
    ambiguous_mentions: int = Field(ge=0)
    mentions_by_method: dict[str, int]
    top_assigned_devatas: list[EntityLexicalFrequency]
    top_mentioned_devatas: list[EntityLexicalFrequency]
    top_token_occurrence_entities: list[EntityLexicalFrequency]
    top_assigned_rishis: list[EntityLexicalFrequency]
    top_mentioned_rishis: list[EntityLexicalFrequency]
    top_co_occurrences: list[EntityCoOccurrence]
    mentions_by_mandala: list[MandalaMentionStats]
    exact_parallel_pairs: int = Field(ge=0)
    exact_parallel_groups: int = Field(ge=0)
    largest_exact_group: int = Field(ge=0)
    near_parallel_candidates: int = Field(ge=0)
    accepted_near_parallels: int = Field(ge=0)
    component_assertions: int = Field(ge=0)
    schema_version: str = SCHEMA_VERSION


class LexicalManifest(VGModel):
    """Pins every input, policy and output hash of one lexical-layer build."""

    dataset: str = "VedaGraph Deterministic Lexical Knowledge Layer"
    version: str
    built_at: datetime
    corpus_dataset_id: str
    corpus_version: str
    corpus_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    corpus_passage_count: int = Field(ge=0)
    knowledge_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    knowledge_layer_version: str = Field(min_length=1)
    morphology_source_id: str = Field(min_length=1)
    morphology_repository_url: AnyHttpUrl
    morphology_commit_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    morphology_annotation_layer_id: str = Field(min_length=1)
    morphology_license: str = Field(min_length=1)
    morphology_artifact_ids: list[str]
    morphology_artifact_hashes: dict[str, str]
    morphology_snapshot_ids: list[str]
    entity_registry_hashes: dict[str, str]
    lexical_registry_hashes: dict[str, str]
    canonical_text_version_id: str = Field(min_length=1)
    morphology_parser_version: str = Field(min_length=1)
    token_id_policy_version: str = Field(min_length=1)
    mention_policy_version: str = Field(min_length=1)
    parallel_policy_version: str = Field(min_length=1)
    component_mapping_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    predicate_whitelist: list[LexicalPredicate]
    record_counts: dict[str, int]
    qa_status: QAStatus
    generated_files: list[dict[str, str | int]]
    software_version: str | None = None
    schema_version: str = SCHEMA_VERSION
