"""What the product graph is allowed to contain, and what a reader may conclude from it.

Knowledge Model V1 produced a technically sound graph that still read like a database: a
QA finding sat beside Indra as a peer node, 54 of 89 domain entities were labelled
``Concept`` regardless of whether they were a river or a ritual, and the deity/meter
attributions carried no indication of whether a source said them or a scope rule inferred
them. None of that was a bug in the loader. It was an absent contract, which is what this
module is.

Four decisions are fixed here.

**Type lives on the node, not on the edge.** The enrichment layer already records that
``VG:CONCEPT:GO-CATTLE`` is an ``ANIMAL`` and ``VG:CONCEPT:SINDHU-RIVER`` is a ``RIVER``;
the Neo4j projection dropped it and wrote both as ``:Concept``. So the label set here is
derived from the frozen :class:`~vedagraph.semantic.ontology.SemanticNodeType` whitelist
rather than invented next to it, and a passage that mentions a crop is found by the
*target's* label (``-[:MENTIONS_ENTITY]->(:Crop)``) instead of by a fifteenth near-
duplicate relationship type. One mention predicate, many node types, is the difference
between a graph that grows in expressiveness and one that grows in edge count.

**Product and internal are separate graphs sharing a database.** A ``QAIssue`` is a fact
about this repository, not about the Vedas. Rather than deleting it -- it is genuinely
useful to ask the graph what it doubts about itself -- every non-domain node carries the
marker label :data:`LABEL_INTERNAL`, and :data:`PRODUCT_NODE_FILTER` is the single place
that exclusion is written down. Sprinkling ``WHERE NOT n:QAIssue`` across thirty queries
would be the same policy, enforced thirty times, and wrong the first time a new
diagnostic label appears.

**A deity is not one thing, so it does not get one enum.** ``devata_subtype`` forced Agni
to choose between being a god, a fire, and the mouth that carries an offering. It is kept
for structural facts a source states (this label names a dual, a group, a patron's
praise) and superseded for role by :class:`DeityAxis`, which a deity may hold several of
at once, each with its own evidence.

**Tier is how a claim was reached, never how confident it sounds.** ``SUKTA_WIDE``
attribution is the case that matters: 24,698 of 31,650 Anukramaṇī assertions reach a
mantra by inheriting its sūkta's label. Those are reproducible derivations, not statements
about that mantra, and :data:`KNOWLEDGE_TIER_BY_PROVENANCE` files them as ``TIER_B``
however authoritative the Anukramaṇī is about the sūkta.

Nothing here asserts a Vedic fact. This module says what shape an assertion must take;
the artifacts under ``data/domain/`` say what is asserted, and every one of them carries
the evidence envelope from :mod:`vedagraph.enrich.provenance`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from vedagraph.semantic.ontology import SemanticNodeType

#: Bumped when a change would alter which nodes or edges a rebuild produces. Stored on
#: every domain record, so a row produced under one version is never silently compared
#: with one produced under another.
DOMAIN_MODEL_VERSION: Final = "vedagraph-knowledge-model-v2"


# ---------------------------------------------------------------------------
# Marker labels
# ---------------------------------------------------------------------------

#: Carried by every node this layer treats as Vedic knowledge. Gives "how big is the
#: product graph" a single label scan and gives the display contract one place to live.
LABEL_DOMAIN_ENTITY: Final = "DomainEntity"

#: Carried by every node that describes the repository rather than the corpus. The only
#: thing that keeps engineering plumbing out of a knowledge traversal.
LABEL_INTERNAL: Final = "Internal"


# ---------------------------------------------------------------------------
# Domain node labels
# ---------------------------------------------------------------------------

# Entity families already present in the corpus and knowledge layers.
LABEL_WORK: Final = "Work"
LABEL_PASSAGE: Final = "Passage"
LABEL_MANTRA: Final = "Mantra"
LABEL_DEVATA: Final = "Devata"
LABEL_RISHI: Final = "Rishi"
LABEL_CHANDAS: Final = "Chandas"
LABEL_LEMMA: Final = "Lemma"
LABEL_FORMULA: Final = "Formula"

# The seventeen frozen semantic node types, as Neo4j labels.
LABEL_CONCEPT: Final = "Concept"
LABEL_PHILOSOPHICAL_CONCEPT: Final = "PhilosophicalConcept"
LABEL_THEME: Final = "Theme"
LABEL_RITUAL: Final = "Ritual"
LABEL_OFFERING: Final = "Offering"
LABEL_SUBSTANCE: Final = "Substance"
LABEL_PLANT: Final = "Plant"
LABEL_ANIMAL: Final = "Animal"
LABEL_OBJECT: Final = "Object"
LABEL_PLACE: Final = "Place"
LABEL_RIVER: Final = "River"
LABEL_REGION: Final = "Region"
LABEL_NATURAL_PHENOMENON: Final = "NaturalPhenomenon"
LABEL_COSMIC_ENTITY: Final = "CosmicEntity"
LABEL_ACTION: Final = "Action"
LABEL_QUALITY: Final = "Quality"
LABEL_STATE: Final = "State"

# Added by V2. Each one is here because it unblocks a named killer question; a label that
# only sounded interesting was left out.
LABEL_HUMAN_CONCERN: Final = "HumanConcern"      # Q13-16, 32, 47, 48
LABEL_CONDITION: Final = "Condition"             # Q12, 15, 47 -- disease, fever, poison
LABEL_EPITHET: Final = "Epithet"                 # Q42
LABEL_DEITY_GROUP: Final = "DeityGroup"          # Q23, 41
LABEL_DEITY_AXIS: Final = "DeityAxis"            # Q20, 38, 45, 46
LABEL_SOCIAL_RITE: Final = "SocialRite"          # Q13, 14
LABEL_RITUAL_ROLE: Final = "RitualRole"          # Q32, 39 -- hotar, adhvaryu, udgatar
LABEL_RISHI_FAMILY: Final = "RishiFamily"        # Q2, 19, 24, 35
LABEL_TRIBE: Final = "Tribe"                     # Q26
LABEL_INTERPRETIVE_CLAIM: Final = "InterpretiveClaim"  # Q28, 29, 30
LABEL_DERIVED_METRIC: Final = "DerivedMetric"    # Q30, 36, 43, 44

# Sublabels: narrower views of a broader family, applied in addition to it. A crop is a
# plant and answers "which plants" as well as "which crops"; splitting them into
# unrelated labels would make the general question unanswerable.
LABEL_CROP: Final = "Crop"                       # Q9,  sublabel of Plant
LABEL_METAL: Final = "Metal"                     # Q10, sublabel of Substance
LABEL_WEAPON: Final = "Weapon"                   # Q40, sublabel of Object

class DomainNodeType(StrEnum):
    """Entity types V2 adds, on top of the frozen semantic seventeen.

    Kept as a separate enum rather than appended to
    :class:`~vedagraph.semantic.ontology.SemanticNodeType`, which is deliberately frozen:
    every sealed semantic candidate records the ontology version it was produced under, and
    growing that enum would silently redefine what ``rigveda-semantic-ontology-v1`` means
    for 448 already-sealed extractions. A registry entry may name a type from either enum;
    only this one may grow.

    ``CROP``, ``METAL`` and ``WEAPON`` are narrower views of ``PLANT``, ``SUBSTANCE`` and
    ``OBJECT`` and carry those labels too, so adding them cannot make the broader question
    harder to ask. See :data:`SUPERLABELS`.
    """

    HUMAN_CONCERN = "HUMAN_CONCERN"
    CONDITION = "CONDITION"
    SOCIAL_RITE = "SOCIAL_RITE"
    RITUAL_ROLE = "RITUAL_ROLE"
    TRIBE = "TRIBE"
    CROP = "CROP"
    METAL = "METAL"
    WEAPON = "WEAPON"


LABEL_BY_DOMAIN_NODE_TYPE: Final[dict[DomainNodeType, str]] = {
    DomainNodeType.HUMAN_CONCERN: LABEL_HUMAN_CONCERN,
    DomainNodeType.CONDITION: LABEL_CONDITION,
    DomainNodeType.SOCIAL_RITE: LABEL_SOCIAL_RITE,
    DomainNodeType.RITUAL_ROLE: LABEL_RITUAL_ROLE,
    DomainNodeType.TRIBE: LABEL_TRIBE,
    DomainNodeType.CROP: LABEL_CROP,
    DomainNodeType.METAL: LABEL_METAL,
    DomainNodeType.WEAPON: LABEL_WEAPON,
}

assert set(LABEL_BY_DOMAIN_NODE_TYPE) == set(DomainNodeType), (
    "every V2 domain node type needs a Neo4j label"
)

#: Every type name a registry entry may declare, from either enum.
ALL_NODE_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    {str(member) for member in SemanticNodeType} | {str(member) for member in DomainNodeType}
)

#: Superlabels applied alongside a narrower label, so that a query for the family finds
#: the specialisation. Kept explicit rather than mechanical: ``River`` implies ``Place``
#: because a river is somewhere, whereas ``Crop`` implies ``Plant`` for a different
#: reason, and a rule that produced both would be a coincidence rather than a model.
SUPERLABELS: Final[dict[str, tuple[str, ...]]] = {
    LABEL_RIVER: (LABEL_PLACE,),
    LABEL_REGION: (LABEL_PLACE,),
    LABEL_PHILOSOPHICAL_CONCEPT: (LABEL_CONCEPT,),
    LABEL_CROP: (LABEL_PLANT,),
    LABEL_METAL: (LABEL_SUBSTANCE,),
    LABEL_WEAPON: (LABEL_OBJECT,),
}

#: The frozen semantic whitelist, mapped to the labels above. This mapping is the fix for
#: the V1 flattening: the projection had this information and discarded it.
LABEL_BY_SEMANTIC_NODE_TYPE: Final[dict[SemanticNodeType, str]] = {
    SemanticNodeType.CONCEPT: LABEL_CONCEPT,
    SemanticNodeType.PHILOSOPHICAL_CONCEPT: LABEL_PHILOSOPHICAL_CONCEPT,
    SemanticNodeType.THEME: LABEL_THEME,
    SemanticNodeType.RITUAL: LABEL_RITUAL,
    SemanticNodeType.OFFERING: LABEL_OFFERING,
    SemanticNodeType.SUBSTANCE: LABEL_SUBSTANCE,
    SemanticNodeType.PLANT: LABEL_PLANT,
    SemanticNodeType.ANIMAL: LABEL_ANIMAL,
    SemanticNodeType.OBJECT: LABEL_OBJECT,
    SemanticNodeType.PLACE: LABEL_PLACE,
    SemanticNodeType.RIVER: LABEL_RIVER,
    SemanticNodeType.REGION: LABEL_REGION,
    SemanticNodeType.NATURAL_PHENOMENON: LABEL_NATURAL_PHENOMENON,
    SemanticNodeType.COSMIC_ENTITY: LABEL_COSMIC_ENTITY,
    SemanticNodeType.ACTION: LABEL_ACTION,
    SemanticNodeType.QUALITY: LABEL_QUALITY,
    SemanticNodeType.STATE: LABEL_STATE,
}

assert set(LABEL_BY_SEMANTIC_NODE_TYPE) == set(SemanticNodeType), (
    "every frozen semantic node type needs a Neo4j label, or the projection will "
    "silently flatten it again"
)

#: Labels a normal knowledge traversal may return.
PRODUCT_LABELS: Final[frozenset[str]] = frozenset(
    {
        LABEL_DOMAIN_ENTITY,
        LABEL_WORK,
        LABEL_PASSAGE,
        LABEL_MANTRA,
        LABEL_DEVATA,
        LABEL_RISHI,
        LABEL_CHANDAS,
        LABEL_LEMMA,
        LABEL_FORMULA,
        *LABEL_BY_SEMANTIC_NODE_TYPE.values(),
        LABEL_HUMAN_CONCERN,
        LABEL_CONDITION,
        LABEL_EPITHET,
        LABEL_DEITY_GROUP,
        LABEL_DEITY_AXIS,
        LABEL_SOCIAL_RITE,
        LABEL_RITUAL_ROLE,
        LABEL_RISHI_FAMILY,
        LABEL_TRIBE,
        LABEL_INTERPRETIVE_CLAIM,
        LABEL_DERIVED_METRIC,
        LABEL_CROP,
        LABEL_METAL,
        LABEL_WEAPON,
    }
)

#: Labels that describe the repository, its provenance chain or its own doubts. Present in
#: the database on purpose, absent from knowledge traversal on purpose.
INTERNAL_LABELS: Final[frozenset[str]] = frozenset(
    {
        LABEL_INTERNAL,
        "QAIssue",
        "TextVersion",
        "Translation",
        "Source",
        "SourceArtifact",
    }
)

assert PRODUCT_LABELS.isdisjoint(INTERNAL_LABELS), "a label cannot be both"

#: The one place the product/internal boundary is written as Cypher. Every product query
#: interpolates this instead of naming excluded labels itself.
PRODUCT_NODE_FILTER: Final = f"NOT n:{LABEL_INTERNAL}"

_SEMANTIC_NAMES: Final[frozenset[str]] = frozenset(str(m) for m in SemanticNodeType)
_DOMAIN_NAMES: Final[frozenset[str]] = frozenset(str(m) for m in DomainNodeType)


def product_filter(variable: str) -> str:
    """The product/internal exclusion for a given Cypher variable."""
    return f"NOT {variable}:{LABEL_INTERNAL}"


def labels_for_node_type(node_type: str) -> tuple[str, ...]:
    """Every label a domain entity of ``node_type`` carries, broadest last.

    Returns the specific label, any superlabels it implies, and the shared
    :data:`LABEL_DOMAIN_ENTITY` marker. Unknown types raise rather than defaulting to
    ``Concept``: defaulting is exactly how V1 came to label a river as a concept.
    """
    if node_type in _SEMANTIC_NAMES:
        specific = LABEL_BY_SEMANTIC_NODE_TYPE[SemanticNodeType(node_type)]
    elif node_type in _DOMAIN_NAMES:
        specific = LABEL_BY_DOMAIN_NODE_TYPE[DomainNodeType(node_type)]
    else:
        raise ValueError(
            f"{node_type!r} is not a known domain node type. Allowed: "
            f"{', '.join(sorted(ALL_NODE_TYPE_NAMES))}"
        )
    return (specific, *SUPERLABELS.get(specific, ()), LABEL_DOMAIN_ENTITY)


# ---------------------------------------------------------------------------
# Deity axes: the multi-axial replacement for devata_subtype
# ---------------------------------------------------------------------------


class DeityAxis(StrEnum):
    """A role a deity occupies. A deity may hold several, each needing its own evidence.

    These are *functional* axes read off what the corpus does with a deity, deliberately
    not a pantheon-wide domain assignment: ``IS_GOD_OF`` is a refused predicate in the
    semantic ontology for good reasons, and this enum is not a way to smuggle it back.
    ``SOLAR`` on Sūrya says the corpus treats Sūrya as a solar body, not that Sūrya is
    "the sun god" in a systematised theology largely later than these texts.
    """

    COSMIC_SOVEREIGN = "COSMIC_SOVEREIGN"
    WARRIOR = "WARRIOR"
    FIRE_MEDIUM = "FIRE_MEDIUM"
    RITUAL_SUBSTANCE = "RITUAL_SUBSTANCE"
    RITUAL_OBJECT = "RITUAL_OBJECT"
    PRIESTLY = "PRIESTLY"
    SOLAR = "SOLAR"
    ATMOSPHERIC = "ATMOSPHERIC"
    TERRESTRIAL = "TERRESTRIAL"
    CHTHONIC = "CHTHONIC"
    AQUATIC = "AQUATIC"
    SPEECH = "SPEECH"
    DAWN_TIME = "DAWN_TIME"
    #: Added after curation: the first vocabulary had no lunar axis, which left Candramās,
    #: Rākā and Sinīvālī unclassifiable, and no nocturnal axis, which was forcing Rātri to
    #: borrow DAWN_TIME. Both were found by trying to use the enum rather than by
    #: designing it, which is the only way this kind of gap gets found.
    LUNAR = "LUNAR"
    NOCTURNAL = "NOCTURNAL"
    HEALER = "HEALER"
    ARTISAN = "ARTISAN"
    ANCESTRAL = "ANCESTRAL"
    GUARDIAN_OF_ORDER = "GUARDIAN_OF_ORDER"
    PSYCHOPOMP = "PSYCHOPOMP"
    ABSTRACT_PERSONIFICATION = "ABSTRACT_PERSONIFICATION"
    #: The honest default. A justified UNSPECIFIED is worth more than an invented axis,
    #: and the scorecard counts it as unclassified rather than hiding it.
    UNSPECIFIED = "UNSPECIFIED"


class DevataStructure(StrEnum):
    """A structural fact about what a Devatā *label* is, not about the deity's role.

    Retained from ``devata_subtype`` because these are things the Anukramaṇī states or
    that the label's own morphology settles: a dual is a dual. Role went to
    :class:`DeityAxis`; this axis stayed because it never had the collapsing problem.
    """

    INDIVIDUAL = "INDIVIDUAL"
    PAIR = "PAIR"
    GROUP = "GROUP"
    #: A hymn labelled for the praise of a human patron rather than a deity.
    PATRON_PRAISE = "PATRON_PRAISE"
    #: The label names a thing, quality or event treated as the hymn's addressee.
    ABSTRACT = "ABSTRACT"
    #: A named human being (a Ṛṣi, a king) standing as the hymn's addressee.
    HUMAN = "HUMAN"
    UNSPECIFIED = "UNSPECIFIED"


# ---------------------------------------------------------------------------
# Knowledge layers and quality tiers
# ---------------------------------------------------------------------------


class KnowledgeLayer(StrEnum):
    """How a claim came to be. Never collapsed, never inferred from a score."""

    #: A source states it.
    L1_SOURCE_EXPLICIT = "L1_SOURCE_EXPLICIT"
    #: A reproducible rule over stored text or over L1 produced it.
    L2_DETERMINISTIC_DERIVED = "L2_DETERMINISTIC_DERIVED"
    #: A language model read evidence and proposed it.
    L3_LLM_EXTRACTED = "L3_LLM_EXTRACTED"
    #: A reading of the corpus, held by this project or by a named commentator.
    L4_INTERPRETIVE_CLAIM = "L4_INTERPRETIVE_CLAIM"


class QualityTier(StrEnum):
    """The reader-facing grade of an edge. A function of layer, not of confidence."""

    TIER_A = "TIER_A"  # source-explicit
    TIER_B = "TIER_B"  # deterministic derivation, including scope inheritance
    TIER_C = "TIER_C"  # model-extracted with surviving evidence
    TIER_D = "TIER_D"  # interpretive


TIER_BY_LAYER: Final[dict[KnowledgeLayer, QualityTier]] = {
    KnowledgeLayer.L1_SOURCE_EXPLICIT: QualityTier.TIER_A,
    KnowledgeLayer.L2_DETERMINISTIC_DERIVED: QualityTier.TIER_B,
    KnowledgeLayer.L3_LLM_EXTRACTED: QualityTier.TIER_C,
    KnowledgeLayer.L4_INTERPRETIVE_CLAIM: QualityTier.TIER_D,
}


class AttributionPrecision(StrEnum):
    """Whether an attribution is about this passage or about a container it sits in.

    The Anukramaṇī names a deity for a *sūkta*. Projecting that onto each of its mantras
    is useful and is what makes "passages of Indra" work at all, but a reader who cannot
    see the difference will read 24,698 inherited labels as 24,698 per-verse statements.
    """

    #: The source names this exact passage, or a range that names it.
    PER_PASSAGE = "PER_PASSAGE"
    #: Inherited from the enclosing sūkta's label by a scope rule.
    CONTAINER_INHERITED = "CONTAINER_INHERITED"


#: ``provenance_class`` in the knowledge layer, graded. ``SOURCE_DERIVED_SCOPE`` is a
#: derivation *from* a source-explicit statement about a larger unit, so it is TIER_B: the
#: Anukramaṇī's authority over the sūkta does not transfer to a claim it never made about
#: the mantra.
KNOWLEDGE_TIER_BY_PROVENANCE: Final[dict[str, QualityTier]] = {
    "SOURCE_EXPLICIT": QualityTier.TIER_A,
    "SOURCE_DERIVED_SCOPE": QualityTier.TIER_B,
}

PRECISION_BY_SCOPE_ORIGIN: Final[dict[str, AttributionPrecision]] = {
    "SINGLE_MANTRA": AttributionPrecision.PER_PASSAGE,
    "MANTRA_RANGE": AttributionPrecision.PER_PASSAGE,
    "SUKTA_WIDE": AttributionPrecision.CONTAINER_INHERITED,
}


class ClaimStatus(StrEnum):
    """What kind of interpretive claim this is. None of these is a textual fact."""

    #: A named external commentator or secondary source holds it.
    SOURCE_INTERPRETATION = "SOURCE_INTERPRETATION"
    #: This project synthesised it from its own derived statistics.
    MODEL_SYNTHESIS = "MODEL_SYNTHESIS"
    #: Stated so it can be tested; not asserted as holding.
    RESEARCH_HYPOTHESIS = "RESEARCH_HYPOTHESIS"


# ---------------------------------------------------------------------------
# Controlled relationship vocabulary
# ---------------------------------------------------------------------------

# Corpus and knowledge layers (pre-existing; listed so the closed vocabulary is complete).
REL_CONTAINS: Final = "CONTAINS"
REL_HAS_DEVATA: Final = "HAS_DEVATA"
REL_HAS_RISHI: Final = "HAS_RISHI"
REL_HAS_CHANDAS: Final = "HAS_CHANDAS"
REL_MENTIONS_LEMMA: Final = "MENTIONS_LEMMA"
REL_ABOUT_CONCEPT: Final = "ABOUT_CONCEPT"
REL_USES_FORMULA: Final = "USES_FORMULA"
REL_BROADER_THAN: Final = "BROADER_THAN"

#: The single deterministic "this passage names this entity" edge. Extended in V2 from
#: Devatā-only to every :data:`LABEL_DOMAIN_ENTITY`, because the entity's own label
#: already carries the type. Fifteen typed mention predicates would have carried the same
#: information in a form no query could generalise over.
REL_MENTIONS_ENTITY: Final = "MENTIONS_ENTITY"

# Devatā identity and role.
REL_HAS_AXIS: Final = "HAS_AXIS"
REL_HAS_EPITHET: Final = "HAS_EPITHET"
REL_MEMBER_OF: Final = "MEMBER_OF"
REL_COMPOSED_OF: Final = "COMPOSED_OF"
REL_PERSONIFIES: Final = "PERSONIFIES"
REL_ASSOCIATED_WITH_CONCEPT: Final = "ASSOCIATED_WITH_CONCEPT"
REL_ASSOCIATED_WITH_PHENOMENON: Final = "ASSOCIATED_WITH_PHENOMENON"
REL_ASSOCIATED_WITH_SUBSTANCE: Final = "ASSOCIATED_WITH_SUBSTANCE"
REL_WIELDS: Final = "WIELDS"
REL_RECEIVES_OFFERING: Final = "RECEIVES_OFFERING"
REL_PERFORMS_ACTION: Final = "PERFORMS_ACTION"
REL_CO_OCCURS_WITH: Final = "CO_OCCURS_WITH"

# Ritual structure.
REL_USES_OFFERING: Final = "USES_OFFERING"
REL_USES_SUBSTANCE: Final = "USES_SUBSTANCE"
REL_USES_OBJECT: Final = "USES_OBJECT"
REL_INVOKES_DEVATA: Final = "INVOKES_DEVATA"
REL_PERFORMED_FOR: Final = "PERFORMED_FOR"
REL_PERFORMED_BY: Final = "PERFORMED_BY"
REL_HAS_STEP: Final = "HAS_STEP"
REL_DESCRIBED_IN: Final = "DESCRIBED_IN"

# Human concerns, chiefly but not only Atharvavedic.
REL_ADDRESSES_CONCERN: Final = "ADDRESSES_CONCERN"
REL_TREATS: Final = "TREATS"
REL_PROTECTS_FROM: Final = "PROTECTS_FROM"
REL_USED_FOR_RITE: Final = "USED_FOR_RITE"

# Ṛṣi social structure.
REL_BELONGS_TO_FAMILY: Final = "BELONGS_TO_FAMILY"
REL_ASSOCIATED_WITH_TRIBE: Final = "ASSOCIATED_WITH_TRIBE"

# Cross-Veda transmission. Kept distinct because "the same verse appears in Sāmaveda" and
# "the verse was set to a melody" are different claims with different evidence, and
# collapsing both into PARALLEL_TO is what made the Sāmaveda look like a duplicate corpus.
REL_TEXTUALLY_REUSED_AS: Final = "TEXTUALLY_REUSED_AS"
REL_MUSICALIZED_AS: Final = "MUSICALIZED_AS"

# Interpretive layer.
REL_SUPPORTED_BY: Final = "SUPPORTED_BY"
REL_SUPPORTED_BY_STATISTIC: Final = "SUPPORTED_BY_STATISTIC"
REL_ASSERTED_BY: Final = "ASSERTED_BY"
REL_CONCERNS: Final = "CONCERNS"
REL_CONTRADICTS: Final = "CONTRADICTS"
REL_MEASURES: Final = "MEASURES"


#: Relationship types V2 introduces or re-scopes. Anything not here and not already
#: emitted by an earlier layer is a controlled-predicate violation, which
#: :mod:`vedagraph.domain.guards` fails the build on rather than warning about.
DOMAIN_RELATIONSHIP_TYPES: Final[frozenset[str]] = frozenset(
    {
        REL_MENTIONS_ENTITY,
        REL_HAS_AXIS,
        REL_HAS_EPITHET,
        REL_MEMBER_OF,
        REL_COMPOSED_OF,
        REL_PERSONIFIES,
        REL_ASSOCIATED_WITH_CONCEPT,
        REL_ASSOCIATED_WITH_PHENOMENON,
        REL_ASSOCIATED_WITH_SUBSTANCE,
        REL_WIELDS,
        REL_RECEIVES_OFFERING,
        REL_PERFORMS_ACTION,
        REL_CO_OCCURS_WITH,
        REL_USES_OFFERING,
        REL_USES_SUBSTANCE,
        REL_USES_OBJECT,
        REL_INVOKES_DEVATA,
        REL_PERFORMED_FOR,
        REL_PERFORMED_BY,
        REL_HAS_STEP,
        REL_DESCRIBED_IN,
        REL_ADDRESSES_CONCERN,
        REL_TREATS,
        REL_PROTECTS_FROM,
        REL_USED_FOR_RITE,
        REL_BELONGS_TO_FAMILY,
        REL_ASSOCIATED_WITH_TRIBE,
        REL_TEXTUALLY_REUSED_AS,
        REL_MUSICALIZED_AS,
        REL_SUPPORTED_BY,
        REL_SUPPORTED_BY_STATISTIC,
        REL_ASSERTED_BY,
        REL_CONCERNS,
        REL_CONTRADICTS,
        REL_MEASURES,
    }
)

#: Declared so the architecture is inspectable, deliberately not populated in this
#: release. The Sāmaveda's melodies (gāna) are not in the corpus, and an empty typed edge
#: is an honest statement of that where a ``PARALLEL_TO`` standing in for it would not be.
UNPOPULATED_BY_DESIGN: Final[dict[str, str]] = {
    REL_MUSICALIZED_AS: (
        "No gāna/Saman melodic corpus is ingested. The edge type exists so that adding "
        "one later does not require reinterpreting existing textual-reuse edges."
    ),
}


#: What each V2 predicate may connect. Enforced at build time, because the fastest way
#: back to a synonym pile is an edge whose endpoints nobody checked.
RELATIONSHIP_SIGNATURES: Final[dict[str, tuple[frozenset[str], frozenset[str]]]] = {
    # Two producers, both legitimate, and the first version of this signature named only
    # the second -- which made the lexical layer's 9,000 Rigvedic deity mentions read as
    # 9,000 contract violations. ``Devata`` is here because a passage naming Indra is a
    # mention in exactly the sense this predicate means; measured against the live graph,
    # the range is these two families and nothing else (never Rishi, Chandas or Lemma).
    REL_MENTIONS_ENTITY: (
        frozenset({LABEL_PASSAGE}),
        frozenset({LABEL_DOMAIN_ENTITY, LABEL_DEVATA}),
    ),
    REL_HAS_AXIS: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEITY_AXIS})),
    REL_HAS_EPITHET: (frozenset({LABEL_DEVATA}), frozenset({LABEL_EPITHET})),
    REL_MEMBER_OF: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEITY_GROUP})),
    REL_COMPOSED_OF: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEVATA})),
    REL_PERSONIFIES: (
        frozenset({LABEL_DEVATA}),
        frozenset(
            {
                LABEL_NATURAL_PHENOMENON,
                LABEL_CONCEPT,
                LABEL_SUBSTANCE,
                LABEL_COSMIC_ENTITY,
                LABEL_ACTION,
            }
        ),
    ),
    REL_ASSOCIATED_WITH_CONCEPT: (frozenset({LABEL_DEVATA}), frozenset({LABEL_CONCEPT})),
    REL_ASSOCIATED_WITH_PHENOMENON: (
        frozenset({LABEL_DEVATA}),
        frozenset({LABEL_NATURAL_PHENOMENON, LABEL_COSMIC_ENTITY}),
    ),
    REL_ASSOCIATED_WITH_SUBSTANCE: (
        frozenset({LABEL_DEVATA}),
        frozenset({LABEL_SUBSTANCE, LABEL_PLANT, LABEL_OFFERING}),
    ),
    REL_WIELDS: (frozenset({LABEL_DEVATA}), frozenset({LABEL_OBJECT})),
    REL_RECEIVES_OFFERING: (
        frozenset({LABEL_DEVATA}),
        frozenset({LABEL_OFFERING, LABEL_SUBSTANCE, LABEL_ANIMAL, LABEL_PLANT}),
    ),
    REL_PERFORMS_ACTION: (frozenset({LABEL_DEVATA}), frozenset({LABEL_ACTION})),
    REL_CO_OCCURS_WITH: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEVATA})),
    REL_USES_OFFERING: (frozenset({LABEL_RITUAL}), frozenset({LABEL_OFFERING})),
    REL_USES_SUBSTANCE: (
        frozenset({LABEL_RITUAL}),
        frozenset({LABEL_SUBSTANCE, LABEL_PLANT}),
    ),
    REL_USES_OBJECT: (frozenset({LABEL_RITUAL}), frozenset({LABEL_OBJECT})),
    REL_INVOKES_DEVATA: (frozenset({LABEL_RITUAL}), frozenset({LABEL_DEVATA})),
    REL_PERFORMED_FOR: (
        frozenset({LABEL_RITUAL, LABEL_SOCIAL_RITE}),
        frozenset({LABEL_HUMAN_CONCERN, LABEL_CONCEPT, LABEL_STATE}),
    ),
    REL_PERFORMED_BY: (frozenset({LABEL_RITUAL}), frozenset({LABEL_RITUAL_ROLE})),
    REL_HAS_STEP: (frozenset({LABEL_RITUAL}), frozenset({LABEL_ACTION})),
    REL_DESCRIBED_IN: (
        frozenset({LABEL_RITUAL, LABEL_SOCIAL_RITE}),
        frozenset({LABEL_PASSAGE}),
    ),
    REL_ADDRESSES_CONCERN: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_HUMAN_CONCERN})),
    REL_TREATS: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_CONDITION})),
    REL_PROTECTS_FROM: (
        frozenset({LABEL_PASSAGE}),
        frozenset({LABEL_CONDITION, LABEL_HUMAN_CONCERN}),
    ),
    REL_USED_FOR_RITE: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_SOCIAL_RITE})),
    REL_BELONGS_TO_FAMILY: (frozenset({LABEL_RISHI}), frozenset({LABEL_RISHI_FAMILY})),
    REL_ASSOCIATED_WITH_TRIBE: (
        frozenset({LABEL_RISHI, LABEL_RISHI_FAMILY, LABEL_PASSAGE}),
        frozenset({LABEL_TRIBE}),
    ),
    REL_TEXTUALLY_REUSED_AS: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_PASSAGE})),
    REL_MUSICALIZED_AS: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_PASSAGE})),
    REL_SUPPORTED_BY: (
        frozenset({LABEL_INTERPRETIVE_CLAIM}),
        frozenset({LABEL_PASSAGE}),
    ),
    REL_SUPPORTED_BY_STATISTIC: (
        frozenset({LABEL_INTERPRETIVE_CLAIM}),
        frozenset({LABEL_DERIVED_METRIC}),
    ),
    REL_ASSERTED_BY: (frozenset({LABEL_INTERPRETIVE_CLAIM}), frozenset({"Source"})),
    REL_CONCERNS: (
        frozenset({LABEL_INTERPRETIVE_CLAIM}),
        frozenset({LABEL_DEVATA, LABEL_CONCEPT, LABEL_WORK, LABEL_DOMAIN_ENTITY}),
    ),
    REL_CONTRADICTS: (
        frozenset({LABEL_INTERPRETIVE_CLAIM}),
        frozenset({LABEL_INTERPRETIVE_CLAIM}),
    ),
    REL_MEASURES: (
        frozenset({LABEL_DERIVED_METRIC}),
        frozenset({LABEL_DEVATA, LABEL_CONCEPT, LABEL_WORK, LABEL_DOMAIN_ENTITY}),
    ),
}

assert set(RELATIONSHIP_SIGNATURES) == DOMAIN_RELATIONSHIP_TYPES, (
    "every V2 relationship type needs an endpoint signature"
)


# ---------------------------------------------------------------------------
# Display contract
# ---------------------------------------------------------------------------

#: Properties every product-domain node must carry so an explorer can render it without
#: knowing what it is. Semantic metadata only: no colours, no icons, no styling. The
#: frontend does not exist yet and hard-coding its choices here would outlive them.
REQUIRED_DISPLAY_PROPERTIES: Final[tuple[str, ...]] = (
    "display_label",
    "display_type",
)

#: Additionally expected on entities important enough to have a page of their own.
RICH_DISPLAY_PROPERTIES: Final[tuple[str, ...]] = (
    "short_description",
    "label_en",
    "label_iast",
)

#: Label values that mean "we do not know" and must never reach a display slot. Measured
#: as UNKNOWN_LABEL_RATE in the scorecard.
NULL_LABEL_SENTINELS: Final[frozenset[str]] = frozenset(
    {"", "UNKNOWN", "Unknown", "unknown", "NULL", "null", "None", "?", "-"}
)


def is_meaningful_label(value: str | None) -> bool:
    """Whether ``value`` can be shown to a reader as an entity's name."""
    if value is None:
        return False
    return value.strip() not in NULL_LABEL_SENTINELS
