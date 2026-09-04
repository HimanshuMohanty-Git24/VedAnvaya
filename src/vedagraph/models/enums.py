"""Controlled vocabularies used by canonical and staging records."""

from enum import StrEnum


class RightsStatus(StrEnum):
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    CC_BY = "CC_BY"
    CC_BY_SA = "CC_BY_SA"
    CC_BY_NC = "CC_BY_NC"
    CC_BY_NC_SA = "CC_BY_NC_SA"
    APACHE_2_0 = "APACHE_2_0"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    EXTERNAL_REFERENCE_ONLY = "EXTERNAL_REFERENCE_ONLY"
    UNKNOWN = "UNKNOWN"


class AuthorityTier(StrEnum):
    PRIMARY_TRADITIONAL = "PRIMARY_TRADITIONAL"
    SCHOLARLY_EDITION = "SCHOLARLY_EDITION"
    HISTORICAL_TRANSLATION = "HISTORICAL_TRANSLATION"
    AGGREGATOR = "AGGREGATOR"
    COMMUNITY_TRANSCRIPTION = "COMMUNITY_TRANSCRIPTION"


class PassageStatus(StrEnum):
    DRAFT = "DRAFT"
    CANONICAL = "CANONICAL"
    DEPRECATED = "DEPRECATED"


class EntityType(StrEnum):
    WORK = "WORK"
    SECTION = "SECTION"
    HYMN = "HYMN"
    MANTRA = "MANTRA"


class TextForm(StrEnum):
    SAMHITA = "SAMHITA"
    PADAPATHA = "PADAPATHA"
    OTHER = "OTHER"


class AlignmentLevel(StrEnum):
    WORK = "WORK"
    SECTION = "SECTION"
    HYMN = "HYMN"
    MANTRA = "MANTRA"


class TranslationAlignment(StrEnum):
    EXACT_MANTRA_ALIGNMENT = "EXACT_MANTRA_ALIGNMENT"
    HYMN_LEVEL_ALIGNMENT = "HYMN_LEVEL_ALIGNMENT"
    RANGE_ALIGNMENT = "RANGE_ALIGNMENT"
    UNCERTAIN_ALIGNMENT = "UNCERTAIN_ALIGNMENT"


class TextSelectionPolicy(StrEnum):
    ORIGINAL = "ORIGINAL"
    REGULARIZED = "REGULARIZED"


class DiscoveryAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    UNKNOWN = "UNKNOWN"


class QualityStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    MACHINE_ALIGNED = "MACHINE_ALIGNED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    VERIFIED = "VERIFIED"


class MetadataPredicate(StrEnum):
    HAS_RISHI = "HAS_RISHI"
    HAS_DEVATA = "HAS_DEVATA"
    HAS_CHANDAS = "HAS_CHANDAS"


class ScopeType(StrEnum):
    WHOLE_PASSAGE = "WHOLE_PASSAGE"
    SINGLE_MANTRA = "SINGLE_MANTRA"
    MANTRA_RANGE = "MANTRA_RANGE"


class TextRole(StrEnum):
    """How VedaGraph is allowed to use one Sanskrit textual representation."""

    PRIMARY_TEXT = "PRIMARY_TEXT"
    PARALLEL_TEXT = "PARALLEL_TEXT"
    PADAPATHA = "PADAPATHA"
    METRICALLY_RESTORED = "METRICALLY_RESTORED"
    NORMALIZED = "NORMALIZED"
    SEARCH_DERIVATIVE = "SEARCH_DERIVATIVE"
    DISPLAY_DERIVATIVE = "DISPLAY_DERIVATIVE"
    LINGUISTIC_ANNOTATION = "LINGUISTIC_ANNOTATION"
    COMPARISON_ONLY = "COMPARISON_ONLY"
    REFERENCE_ONLY = "REFERENCE_ONLY"


class TextComparisonCategory(StrEnum):
    """Deterministic classification of a difference between two text versions."""

    IDENTICAL = "IDENTICAL"
    UNICODE_ONLY = "UNICODE_ONLY"
    ACCENT_ONLY = "ACCENT_ONLY"
    ORTHOGRAPHIC = "ORTHOGRAPHIC"
    SANDHI_OR_SEGMENTATION = "SANDHI_OR_SEGMENTATION"
    METRICAL_RESTORATION = "METRICAL_RESTORATION"
    LEXICAL_VARIANT = "LEXICAL_VARIANT"
    STRUCTURAL_VARIANT = "STRUCTURAL_VARIANT"
    UNCLASSIFIED = "UNCLASSIFIED"
    MISSING = "MISSING"


class RangeParseStatus(StrEnum):
    """Fail-closed statuses for traditional-metadata range strings."""

    PARSED = "PARSED"
    PARTIALLY_PARSED = "PARTIALLY_PARSED"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class CandidateScopeType(StrEnum):
    """Richer scope vocabulary used by unreviewed candidate metadata only.

    Canonical records still use :class:`ScopeType`. Nothing here is promoted to
    canonical metadata until a human review accepts the mapping.
    """

    WHOLE_PASSAGE = "WHOLE_PASSAGE"
    MANTRA = "MANTRA"
    MANTRA_RANGE = "MANTRA_RANGE"
    MANTRA_SET = "MANTRA_SET"
    HALF_VERSE = "HALF_VERSE"
    PADA = "PADA"
    PADA_RANGE = "PADA_RANGE"
    UNRESOLVED_SUBSPAN = "UNRESOLVED_SUBSPAN"


class AssertionStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"
    SUPERSEDED = "SUPERSEDED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AudioType(StrEnum):
    VEDIC_RECITATION = "VEDIC_RECITATION"
    HINDI_NARRATION = "HINDI_NARRATION"
    ENGLISH_NARRATION = "ENGLISH_NARRATION"
    COMMENTARY_AUDIO = "COMMENTARY_AUDIO"
    LECTURE = "LECTURE"
    MUSICAL_RENDERING = "MUSICAL_RENDERING"
    OTHER = "OTHER"


class StoragePolicy(StrEnum):
    LOCAL = "LOCAL"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"


class AlignmentMethod(StrEnum):
    SOURCE_PROVIDED = "SOURCE_PROVIDED"
    MANUAL = "MANUAL"
    ALGORITHMIC = "ALGORITHMIC"
    ALGORITHMIC_REVIEWED = "ALGORITHMIC_REVIEWED"


class ReviewStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class QASeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class QAStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PASSED_WITH_WARNINGS = "PASSED_WITH_WARNINGS"


class KnowledgeEntityType(StrEnum):
    """Canonical entity families in the deterministic knowledge layer."""

    RISHI = "RISHI"
    DEVATA = "DEVATA"
    CHANDAS = "CHANDAS"


class AnukramaniField(StrEnum):
    """The three annotated fields of one Anukramaṇī row."""

    SEER = "SEER"
    DIVINITY = "DIVINITY"
    METER = "METER"


class AliasType(StrEnum):
    """Why one surface string is treated as naming the same entity.

    A string is only classified beyond ``SOURCE_SPELLING`` when evidence supports it.
    """

    SOURCE_SPELLING = "SOURCE_SPELLING"
    ORTHOGRAPHIC_VARIANT = "ORTHOGRAPHIC_VARIANT"
    TRANSLITERATION_VARIANT = "TRANSLITERATION_VARIANT"
    INFLECTIONAL_FORM = "INFLECTIONAL_FORM"
    ALTERNATE_NAME = "ALTERNATE_NAME"
    EPITHET = "EPITHET"
    COMPOSITE_LABEL = "COMPOSITE_LABEL"
    UNCERTAIN_EQUIVALENCE = "UNCERTAIN_EQUIVALENCE"


class ResolutionStatus(StrEnum):
    """How a raw source label reached (or failed to reach) a canonical entity.

    Only ``EXACT``, ``NORMALIZED_EXACT``, ``KNOWN_ALIAS`` and ``COMPOSITE_PRESERVED``
    may attach a canonical entity id.
    """

    EXACT = "EXACT"
    NORMALIZED_EXACT = "NORMALIZED_EXACT"
    KNOWN_ALIAS = "KNOWN_ALIAS"
    COMPOSITE_PRESERVED = "COMPOSITE_PRESERVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"


class ProvenanceClass(StrEnum):
    """What kind of statement a knowledge assertion rests on."""

    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"
    SOURCE_DERIVED_SCOPE = "SOURCE_DERIVED_SCOPE"


class ScopeOrigin(StrEnum):
    """The scope the source itself stated, before expansion to mantras."""

    SUKTA_WIDE = "SUKTA_WIDE"
    MANTRA_RANGE = "MANTRA_RANGE"
    SINGLE_MANTRA = "SINGLE_MANTRA"


class DevataSubtype(StrEnum):
    """Optional Devatā classification. ``UNKNOWN`` unless evidence exists."""

    INDIVIDUAL = "INDIVIDUAL"
    PAIR = "PAIR"
    GROUP = "GROUP"
    ABSTRACT = "ABSTRACT"
    RITUAL_OBJECT = "RITUAL_OBJECT"
    NATURAL_PHENOMENON = "NATURAL_PHENOMENON"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class AnukramaniParseStatus(StrEnum):
    """Fail-closed status of one parsed Anukramaṇī row."""

    PARSED = "PARSED"
    PARTIALLY_PARSED = "PARTIALLY_PARSED"
    INVALID = "INVALID"


class MetadataAgreement(StrEnum):
    """Classification of one overlapping metadata claim from two sources."""

    AGREE_EXACT = "AGREE_EXACT"
    AGREE_NORMALIZED = "AGREE_NORMALIZED"
    SCOPE_DIFFERENCE = "SCOPE_DIFFERENCE"
    LABEL_DIFFERENCE = "LABEL_DIFFERENCE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNCOMPARABLE = "UNCOMPARABLE"


class LexicalAliasType(StrEnum):
    """Why one lemma or form is permitted to establish a literal entity mention.

    This vocabulary is deliberately separate from :class:`AliasType`. An
    ``AliasType`` says "this Anukramaṇī spelling names this entity"; a
    ``LexicalAliasType`` says "this word occurring in the Sanskrit text is
    evidence that the mantra mentions this entity". The two answer different
    questions, and a registry alias is never silently promoted to a lexical one.

    ``DO_NOT_MATCH`` is an explicit negative: a form that looks like an entity
    name but must never produce a mention.
    """

    CANONICAL_LEMMA = "CANONICAL_LEMMA"
    ORTHOGRAPHIC_VARIANT = "ORTHOGRAPHIC_VARIANT"
    KNOWN_LEMMA_VARIANT = "KNOWN_LEMMA_VARIANT"
    INFLECTIONAL_SOURCE_FORM = "INFLECTIONAL_SOURCE_FORM"
    EPITHET_REVIEWED = "EPITHET_REVIEWED"
    COMPOSITE_NAME = "COMPOSITE_NAME"
    DO_NOT_MATCH = "DO_NOT_MATCH"


class MentionMethod(StrEnum):
    """How one token was matched to a canonical entity.

    Ordered strongest first. ``LEMMA_ID_EXACT`` rests on the annotation source's
    own stable lemma identifier and involves no string comparison at all.
    """

    LEMMA_ID_EXACT = "LEMMA_ID_EXACT"
    LEMMA_EXACT = "LEMMA_EXACT"
    LEMMA_NORMALIZED_EXACT = "LEMMA_NORMALIZED_EXACT"
    SURFACE_EXACT = "SURFACE_EXACT"


class LexicalMatchStatus(StrEnum):
    """Fail-closed outcome of trying to link one lemma to a canonical entity."""

    MATCHED = "MATCHED"
    AMBIGUOUS_LEXICAL_ENTITY = "AMBIGUOUS_LEXICAL_ENTITY"
    AMBIGUOUS_SOURCE_LEMMA = "AMBIGUOUS_SOURCE_LEMMA"
    SUPPRESSED_DO_NOT_MATCH = "SUPPRESSED_DO_NOT_MATCH"
    NO_LEXICAL_ALIAS = "NO_LEXICAL_ALIAS"


class LexicalPredicate(StrEnum):
    """Deterministic predicates added by the lexical / cross-mantra layer.

    ``HAS_RISHI``, ``HAS_DEVATA`` and ``HAS_CHANDAS`` are *not* here: traditional
    assignment lives in :class:`MetadataPredicate` and is never conflated with
    lexical evidence.
    """

    MENTIONS_ENTITY = "MENTIONS_ENTITY"
    EXACT_PARALLEL_OF = "EXACT_PARALLEL_OF"
    PARALLEL_TO = "PARALLEL_TO"
    HAS_COMPONENT = "HAS_COMPONENT"


class LexicalProvenanceClass(StrEnum):
    """What kind of statement a lexical-layer assertion rests on.

    These never mix with :class:`ProvenanceClass`, whose members describe claims
    read directly out of the Anukramaṇī.
    """

    DETERMINISTIC_DERIVED = "DETERMINISTIC_DERIVED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"


class ParallelMethod(StrEnum):
    """The representation at which two mantras were found identical.

    The levels are not collapsed: two mantras may be ``ACCENTLESS_EXACT``
    without being ``SOURCE_EXACT``, and the difference is real information.
    """

    SOURCE_EXACT = "SOURCE_EXACT"
    NFC_EXACT = "NFC_EXACT"
    ACCENTLESS_EXACT = "ACCENTLESS_EXACT"
    TOKEN_EXACT = "TOKEN_EXACT"
    LEMMA_SEQUENCE_EXACT = "LEMMA_SEQUENCE_EXACT"


class ParallelStatus(StrEnum):
    """Review state of one mantra-pair parallel."""

    EXACT_PARALLEL = "EXACT_PARALLEL"
    HIGH_CONFIDENCE_NEAR_PARALLEL = "HIGH_CONFIDENCE_NEAR_PARALLEL"
    CANDIDATE_PARALLEL = "CANDIDATE_PARALLEL"
    REJECTED = "REJECTED"


class ParallelUnit(StrEnum):
    """The textual unit a parallel relates.

    ``PADA`` is declared now and unused in v1: the schema must not foreclose
    pāda-level matching, which the annotation layer's pāda-tagged token ids
    already make possible.
    """

    MANTRA = "MANTRA"
    PADA = "PADA"
