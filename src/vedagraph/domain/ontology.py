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
#: One step of a rite as a Srautasutra or Grhyasutra prints it. A product label since M7,
#: which gave the 3,121 nodes a display_type to go with the deterministic step_key,
#: canonical URN and uuid5 they already carried. Distinct from LABEL_ACTION, which is what
#: the Samhita-numbered HAS_STEP points at.
LABEL_RITUAL_STEP: Final = "RitualStep"

#: A named scholar of the secondary literature. Product-visible: a recorded disagreement is
#: only interpretable if the reader can see who holds the position.
LABEL_SCHOLAR: Final = "Scholar"
#: A work of secondary literature. Distinct from LABEL_WORK, which is a corpus.
LABEL_SCHOLARLY_WORK: Final = "ScholarlyWork"
#: A recorded disagreement between named scholars about a passage. Product-visible, and
#: deliberately NOT :InterpretiveClaim -- that label's contract promises an ``about`` enum
#: and a ``falsifier``, and a disagreement between two asserters has neither.
LABEL_SCHOLARLY_DISAGREEMENT: Final = "ScholarlyDisagreement"

#: This repository's own quality assessment of one of its passages. INTERNAL, on the same
#: footing as QAIssue: it is a fact about the record and never product content. 2,568 of
#: these were reaching the public world export, where they were the fourth-largest node
#: type, because "public" is measured as ``NOT n:Internal`` and nothing had marked them.
LABEL_QUALITY_VERDICT: Final = "QualityVerdict"
#: The reified filler of one semantic role slot. INTERNAL: it carries no entity_key and is
#: not a thing a reader asked to see -- it is the wiring by which a passage's role
#: assignment reaches its referent.
LABEL_ROLE_FILLER: Final = "RoleFiller"
#: One cluster of a deity co-occurrence partition, imported with its refusal attached and
#: no membership claim. INTERNAL: an analytic artifact about this graph, not a Vedic
#: subject, and six of the twelve draw every internal edge from a single hymn.
LABEL_DEITY_COMMUNITY: Final = "DeityCommunity"
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
LABEL_HUMAN_CONCERN: Final = "HumanConcern"  # Q13-16, 32, 47, 48
LABEL_CONDITION: Final = "Condition"  # Q12, 15, 47 -- disease, fever, poison
LABEL_EPITHET: Final = "Epithet"  # Q42
LABEL_DEITY_GROUP: Final = "DeityGroup"  # Q23, 41
LABEL_DEITY_AXIS: Final = "DeityAxis"  # Q20, 38, 45, 46
LABEL_SOCIAL_RITE: Final = "SocialRite"  # Q13, 14
LABEL_RITUAL_ROLE: Final = "RitualRole"  # Q32, 39 -- hotar, adhvaryu, udgatar
LABEL_RISHI_FAMILY: Final = "RishiFamily"  # Q2, 19, 24, 35
LABEL_TRIBE: Final = "Tribe"  # Q26
LABEL_INTERPRETIVE_CLAIM: Final = "InterpretiveClaim"  # Q28, 29, 30
LABEL_DERIVED_METRIC: Final = "DerivedMetric"  # Q30, 36, 43, 44

# Sublabels: narrower views of a broader family, applied in addition to it. A crop is a
# plant and answers "which plants" as well as "which crops"; splitting them into
# unrelated labels would make the general question unanswerable.
LABEL_CROP: Final = "Crop"  # Q9,  sublabel of Plant
LABEL_METAL: Final = "Metal"  # Q10, sublabel of Substance
LABEL_WEAPON: Final = "Weapon"  # Q40, sublabel of Object

# ---------------------------------------------------------------------------
# V3: the reified assertion layer
# ---------------------------------------------------------------------------

#: One assertion, with its own evidence. The V3 answer to a question the brief poses as a
#: design choice: carry passage-level evidence on multiple relationships, or reify.
#:
#: **Reified, with derived one-hop edges on top.** Measured against both requirements:
#:
#: *Evidence.* An agentive fact has up to six parts -- agent, predicate, patient,
#: instrument, beneficiary, location -- plus the verb form and morphology that licensed
#: it. A plain ``(Devata)-[:SLAYS]->(Entity)`` edge can hold two of them and has nowhere
#: to put the other four, so the roles would have to be flattened into edge properties on
#: an edge whose endpoints already chose two of the roles as privileged. Reifying keeps
#: all six as first-class and lets a query ask for the instrument.
#:
#: *Explosion.* The rule fires 2,362 times over the Rigveda and the sealed model artifact
#: adds 2,474, so the node count is four thousand-ish rather than a million. Reification
#: is affordable here precisely because the layer is evidence-bound and therefore small.
#:
#: *Traversal.* Reification alone costs a hop, and "which actions does Indra perform" is
#: the commonest question this layer exists to answer. So the aggregate is *also* written,
#: as ``PERFORMS_ACTION`` and ``IS_ASKED_TO`` from the deity straight to the predicate,
#: carrying the assertion and passage counts and derived from the assertion nodes rather
#: than authored beside them. One hop for the leaderboard, two for the evidence, and the
#: aggregate cannot drift from its assertions because it is rebuilt from them.
LABEL_SEMANTIC_ASSERTION: Final = "SemanticAssertion"

#: An Anukramaṇī ascription that is **not** a deity name.
#:
#: Whitney's Bṛhatsarvānukramaṇī excerpts ascribe an Atharvavedic hymn with an adjectival
#: *descriptor*: ``āgneyam`` "belonging to Agni", ``mantroktadevatyam`` "having the deity
#: named in the mantra", ``bhāiṣajyāyuṣyam uta mantroktāuṣadhidevatākam``. There are 324 of
#: them and they are the Atharvaveda's entire deity-attribution layer. (356 before the
#: harvest was filtered: the printed bracket interleaves verse counts and pāda addresses
#: with the ascriptions, so the graph once asserted that AVS 18.4's deity-ascription was
#: ``ekonanavati``, eighty-nine. The rejections are recorded in the generated registry.)
#:
#: They get their own label because the alternative is worse in both directions. Projected
#: as ``:Devata`` they would add 324 spurious gods, and "how many deities does this graph
#: know?" would stop being answerable. Dropped, the Atharvaveda would keep a deity
#: attribution rate of zero while its own index ascribes 507 hymns. So the descriptor is
#: modelled as what it is, and ``derived_devata_key`` carries the deity for the subset
#: where the derivation is a plain morphological fact rather than a reading.
LABEL_DEVATA_ASCRIPTION: Final = "DevataAscription"

#: One member of the closed action-predicate vocabulary in
#: ``data/registry/action_predicates.yaml``. Deliberately **not** the existing
#: :data:`LABEL_ACTION`, which holds registry *nouns* -- five of them, reached by a
#: mention edge. "The act of pressing soma" as a concept and ``PRESSES`` as a predicate
#: are different ontological things, and merging them is the flattening V2 spent a pass
#: undoing.
LABEL_ACTION_PREDICATE: Final = "ActionPredicate"

#: One family of formulas related by containment: a core phrase, the longer phrases that
#: contain it, and its spelling variants.
#:
#: This label exists because 1,103 of 4,825 ``Formula`` nodes are strict substrings of
#: another one on the surface that defines formula identity, so the flat formula layer
#: answers "which formulas does this passage use?" with a core phrase and its expansions
#: listed as unrelated peers. A reader counting formulas counts the same phrase several
#: times, and a reader looking for the *shared* phrase behind a group of near-identical
#: ones has no node to look at.
#:
#: Grouping is by containment on the collapsed identity form, which is the same surface
#: ``formula_id`` is derived from -- not by similarity. That matters: containment is a
#: decidable relation over the stored strings, so the layer is deterministic and
#: reproducible, and no threshold was chosen. Formulas in no family stay unfamilied
#: rather than being forced into singletons, because a singleton family asserts a grouping
#: that was never found.
LABEL_FORMULA_FAMILY: Final = "FormulaFamily"


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
        LABEL_SEMANTIC_ASSERTION,
        LABEL_ACTION_PREDICATE,
        LABEL_DEVATA_ASCRIPTION,
        LABEL_FORMULA_FAMILY,
        LABEL_RITUAL_STEP,
        LABEL_SCHOLAR,
        LABEL_SCHOLARLY_WORK,
        LABEL_SCHOLARLY_DISAGREEMENT,
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
        LABEL_QUALITY_VERDICT,
        LABEL_ROLE_FILLER,
        LABEL_DEITY_COMMUNITY,
    }
)

assert PRODUCT_LABELS.isdisjoint(INTERNAL_LABELS), "a label cannot be both"

#: Product labels this project has DELIBERATELY DEMOTED by marking every node
#: ``:Internal``, as distinct from labels that are internal by nature.
#:
#: ``Lemma`` is the only member and the distinction is load-bearing. A lemma is a real
#: lexical object and belongs in :data:`PRODUCT_LABELS` on its merits -- which is why the
#: disjointness assertion above is correct and must not be "fixed" by moving it. But V3's
#: fix to adversarial finding M-1 marked the WHOLE layer ``:Internal``, because 39 deity
#: lemmas carrying ``MENTIONS_LEMMA`` edges were surfacing in product traversal looking
#: like deities while carrying none of a Devatā's profile.
#:
#: That decision was never written down anywhere a checker could read, and V3.1 measured
#: the consequence: ``internal_leakage_check`` compared the live graph against a
#: hard-coded copy of :data:`INTERNAL_LABELS` and reported **10,031 Lemma nodes as
#: leaked** -- a false positive large enough to be believed, in the query whose entire
#: job is to be trusted about the product boundary. The V3 close-out's claim that the
#: check "returns 0 rows (its pass condition)" was measured before that marking landed.
#:
#: Anything marked ``:Internal`` that is in neither set is a genuine leak.
INTERNAL_MARKED_LABELS: Final[frozenset[str]] = INTERNAL_LABELS | frozenset({"Lemma"})

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
    #: The passage *names* the entity in its own text. Not an attribution at all in the
    #: Anukramaṇī's sense, and kept as a distinct value rather than folded into
    #: ``PER_PASSAGE`` because the two answer different questions and a reader must be
    #: able to choose. "How many mantras invoke Indra?" has at least four honest answers
    #: — strict source-stated, container-inherited, textual mention, and semantic
    #: invocation — and collapsing any pair of them makes one of the four unaskable.
    TEXTUAL_MENTION = "TEXTUAL_MENTION"

    #: This edge is not an attribution at all. Either no endpoint is a ``:Passage``, or
    #: both are, or the edge is the corpus's own structure rather than a claim attached to
    #: a passage — so "did a source say this of THIS verse, or of the sūkta it sits in?" is
    #: not a well-formed question about it.
    #:
    #: **Declared rather than left absent, and the repository is the argument.** V3.1 tried
    #: absence twice and could not hold it. ``MEMBER_OF_FAMILY`` needed an explicit
    #: ``REMOVE`` because MERGE plus SET leaves an unmentioned property in place, and 2,037
    #: edges kept a stale ``TEXTUAL_MENTION`` through a rebuild that reported success.
    #: Then ``BELONGS_TO_FAMILY`` — ``Rishi -> RishiFamily``, the identical category error
    #: 500 lines further down the same module — reached the opposite verdict, conceding
    #: that "the property should be absent" and then overruling it because "the invariant
    #: that every edge in this graph carries full grading metadata wins, and once the
    #: property has to hold something the only safe value is the inherited one". It
    #: therefore asserts ``CONTAINER_INHERITED`` on an edge with no container and no
    #: passage. This member is the option that comment was reaching for: the invariant is
    #: kept, and no false inherited claim has to be minted to keep it.
    #:
    #: The contract this establishes: **every edge carries ``attribution_precision``, and a
    #: live NULL is a defect.** That makes the validator one query with one right answer,
    #: and it makes a new relationship type whose producer forgot the property fail loudly
    #: instead of defaulting to looking correct.
    #:
    #: Retires ``REGISTRY_STATED``, which was found live on 6 ``EPITHET_VARIANT_OF`` edges
    #: and was never a member of this enum. Nothing caught it, because until V3.2 there was
    #: no closed-world check on this property anywhere in the codebase.
    NOT_AN_ATTRIBUTION = "NOT_AN_ATTRIBUTION"


#: ``provenance_class`` in the knowledge layer, graded. ``SOURCE_DERIVED_SCOPE`` is a
#: derivation *from* a source-explicit statement about a larger unit, so it is TIER_B: the
#: Anukramaṇī's authority over the sūkta does not transfer to a claim it never made about
#: the mantra.
KNOWLEDGE_TIER_BY_PROVENANCE: Final[dict[str, QualityTier]] = {
    "SOURCE_EXPLICIT": QualityTier.TIER_A,
    "SOURCE_DERIVED_SCOPE": QualityTier.TIER_B,
}


class ConditionKind(StrEnum):
    """What sort of thing a ``:Condition`` is: borne, carried, or aimed at the patient.

    The V1 and V3 concern fragments typed afflictions and hostile agents with one label,
    on the stated precedent "that a cause is a Condition". That is defensible as an entity
    type — a charm against a demon and a charm against a cough are the same *kind of text*
    — but it makes one question unanswerable. "Which diseases does the corpus name?" was
    answering with demons, sorcery, curses, worms and poison: of the 718 ``MENTIONS_ENTITY``
    edges reaching a ``:Condition``, 314 reach a threat and 88 a pathogen. Benchmark Q15
    names the defect in terms, requiring "causes (sorcery, ill-named beings) typed
    separately from afflictions".

    **Three values, not five.** ``STATE`` and ``UNSPECIFIED`` were both considered and both
    refused, each with zero members. ``STATE`` had three candidates — greying, madness and
    debility — and all three lose on their own definitions: the corpus prints a remedy
    compound for the first two and the third is borne by a body. It would also collide with
    the live ``:State`` label and the live ``STATE`` node type, putting two unrelated
    meanings on one token in one graph. ``UNSPECIFIED`` is refused on the precedent recorded
    at :mod:`vedagraph.domain.tiers` — a live ``UNSPECIFIED`` there reached 61,861 edges,
    25.5% of the graph, because a declared shrug is always used. Instead this field is
    **required** on every ``CONDITION`` entity and the registry load fails without it, so a
    new condition with no kind breaks the build rather than landing in a bucket.

    ``condition_kind`` is orthogonal to the ``TREATS`` / ``PROTECTS_FROM`` split and must
    not be reconciled with it. Those two predicates are whitelists graded on *evidence
    strength* — whether the corpus prints an explicit remedy compound, or whether the match
    set was small enough to read to the end — not on what kind of thing the target is. That
    is why ``PROTECTS_FROM`` reaches 181 affliction edges over six entities, consumption
    among them, and why a narrowed disease query must filter on this field rather than on
    the predicate: filtering by predicate would drop the corpus's most-attested disease.
    """

    #: A sickness, pain, injury or disorder borne by the patient's own body or mind. The
    #: thing that is *in* the person. 26 of the 36.
    AFFLICTION = "AFFLICTION"
    #: A material or living thing inside or on the patient that produces the trouble but is
    #: not itself a state of the body — worms and poison. Removing it removes a thing
    #: rather than curing a state, and both are what the V1 fragment's own header separates
    #: out as causes. Two members, kept rather than folded: collapsing either into
    #: ``AFFLICTION`` reinstates the exact defect this enum exists to fix.
    PATHOGEN_OR_CAUSE = "PATHOGEN_OR_CAUSE"
    #: An external hostile agent — a being or a person — or a hostile act such as a spell
    #: or a curse, directed at the patient from outside. Warded off, turned back or driven
    #: away, never cured. 8 of the 36.
    THREAT = "THREAT"


#: The closed value space of ``Condition.condition_kind``. Required on every ``CONDITION``
#: entity; see :class:`ConditionKind` for why there is no ``UNSPECIFIED`` to fall back on.
CONDITION_KINDS: Final[frozenset[str]] = frozenset(str(kind) for kind in ConditionKind)


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
#: An epithet-qualified deity label resolved to the base deity it qualifies. Not
#: ``COMPOSED_OF``: `jātavedā agniḥ` is not made *of* Agni the way `mitrāvaruṇau` is made
#: of Mitra and Varuṇa, and a consumer enumerating a compound's members through
#: ``COMPOSED_OF`` would start returning Agni as a member of himself. Not ``HAS_EPITHET``
#: either: that points at an ``:Epithet`` node, and these are ``:Devata`` nodes with
#: attributions and mentions of their own. QUESTION_UNLOCKED = Q86.
REL_EPITHET_VARIANT_OF: Final = "EPITHET_VARIANT_OF"
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

#: ``Formula`` -> ``FormulaFamily``. Carries ``role`` (``CORE``, ``EXPANSION``,
#: ``VARIANT``), so the direction of the containment is recoverable from the edge and a
#: query can ask for the core phrase alone. Not symmetric and not a similarity edge: the
#: role is what distinguishes "this is the shared phrase" from "this contains it".
REL_MEMBER_OF_FAMILY: Final = "MEMBER_OF_FAMILY"

#: ``FormulaFamily`` -> ``Formula``, the outward twin of :data:`REL_MEMBER_OF_FAMILY`.
#:
#: Declared because the family layer landed with membership pointing *inward only*, and
#: two things follow from that which are easy to miss. Cypher can walk a relationship in
#: either direction, so ``(fam)<-[:MEMBER_OF_FAMILY]-(f)`` always worked -- but every
#: consumer that reads the graph through a **directed** surface could not: the ontology
#: reference generated from :data:`RELATIONSHIP_SIGNATURES` reported ``FormulaFamily`` as
#: a sink with no outward predicate, and a reader asking "what can I do from a family?"
#: was told, correctly, nothing. The family was reachable and not navigable.
#:
#: Named ``HAS_FORMULA`` and not ``FORMULA_MEMBER_OF``. The V3 close-out report names the
#: missing predicate ``FORMULA_MEMBER_OF``, which reads subject-first as *"the formula is
#: a member of"* -- the direction that already exists. A name whose plain reading is the
#: opposite of its declared signature is the kind of thing that gets a query written
#: backwards, so the close-out's name is not adopted. ``HAS_FORMULA`` reads in the
#: direction it points, and matches the ``HAS_``-prefix convention every other
#: container-to-contained predicate here already uses.
#:
#: **Mirrored, never re-derived.** Every property is copied from the inbound edge by
#: :func:`vedagraph.domain.v3_loader.load_formula_family_outward`, so ``role``,
#: ``quality_tier`` and ``grade_basis`` cannot disagree between the two directions. The
#: four similarity-derived ``VARIANT`` rows stay ``TIER_D`` outward exactly as they are
#: inward; a mirror that regraded would be a second opinion, and this layer is not
#: entitled to one.
REL_HAS_FORMULA: Final = "HAS_FORMULA"

#: Named for what it MEASURES and not for what a reader would like it to mean. Two
#: passages joined by this edge mention the same registry entities; whether they express
#: the same idea is an interpretation this graph does not make. The V3.1 benchmark
#: diagnosis graded Q22 and Q49 MISLEADING because an entity-overlap measure was presented
#: as an answer to a conceptual-similarity question, and both frozen criteria exclude
#: lexical overlap in terms -- so calling this ``CONCEPTUALLY_SIMILAR_TO`` would have
#: re-shipped the defect under a new predicate. QUESTION_UNLOCKED = Q22, Q49, Q81.
REL_SHARES_ENTITY_VOCABULARY_WITH: Final = "SHARES_ENTITY_VOCABULARY_WITH"

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

# ---------------------------------------------------------------------------
# The two concept layers, reconciled
# ---------------------------------------------------------------------------
#
# V2 shipped two predicates answering overlapping questions with different numbers, and
# named the reconciliation as unfinished business. V3 measured the overlap and it is not
# an overlap at all -- it is exact containment:
#
#   evidence_basis   ABOUT_CONCEPT edges   also carried by MENTIONS_ENTITY
#   SANSKRIT                     13,281                    13,281  (100.0%)
#   MIXED                        13,015                    13,015  (100.0%)
#   TRANSLATION                  21,246                         0  (  0.0%)
#
# So the layers were never rivals. Every Sanskrit-grounded aboutness assertion is a
# mention assertion, and ABOUT_CONCEPT's only independent content was 21,246 edges resting
# on an English word in Griffith 1896 with no Sanskrit evidence whatsoever.
#
# Those 21,246 are retired in V3. The instruction not to create an aboutness edge "merely
# because an English translation contains one keyword" describes them exactly, and the bias
# they carried is worse than their weakness: the Samaveda has **no translations at all**,
# so it contributed **zero** translation-only edges and was silently penalised on every
# cross-Veda conceptual comparison the layer was used for.
#
# What survives is defined, narrowly:
#
#   MENTIONS_ENTITY  -- this passage NAMES this entity. Lexical, uncapped, Sanskrit only.
#                       The claim is about the text.
#   ABOUT_CONCEPT    -- of the entities this passage names, these are the (at most four)
#                       it is substantively about. A **salience ranking over the mention
#                       layer**, not an independent claim, and now provably a subset of it:
#                       after the retirement the two cannot disagree, because one is
#                       contained in the other by construction.
#
# The evidence-basis axis stays filterable on both, as required, so a reader can still ask
# for Sanskrit-grounded, translation-grounded or corroborated evidence separately -- there
# is simply no longer a translation-only aboutness claim to ask for.

# ---------------------------------------------------------------------------
# V3 predicates
# ---------------------------------------------------------------------------

#: This passage names this god, in its own Sanskrit. **Not an attribution**, and that is
#: why it is a separate predicate rather than more ``HAS_DEVATA``: the Anukramaṇī saying a
#: sūkta belongs to Indra and the verse saying ``índra`` are different facts, and a reader
#: asking "how many mantras invoke Indra?" is entitled to choose which one they mean.
#: Carries ``attribution_precision = TEXTUAL_MENTION``.
#:
#: It also supersedes and replaces the V2 arrangement in which ``MENTIONS_ENTITY`` reached
#: ``:Devata`` for 9,000 Rigveda-only edges that duplicated ``MENTIONS_LEMMA`` fact for
#: fact -- identical per-passage counts on all 6,560 passages, empty symmetric difference
#: in both directions.
REL_MENTIONS_DEVATA: Final = "MENTIONS_DEVATA"

#: Passage to the assertions read off it. The reified layer's spine.
REL_HAS_SEMANTIC_ASSERTION: Final = "HAS_SEMANTIC_ASSERTION"

#: The being that acts, or is asked to act.
REL_ASSERTION_AGENT: Final = "ASSERTION_AGENT"

#: Which member of the closed vocabulary this assertion predicates.
REL_ASSERTION_PREDICATE: Final = "ASSERTION_PREDICATE"

#: What the assertion is about besides its agent: the patient of an action, or the entity
#: a model-extracted assertion resolved to. One predicate rather than one per role, with
#: the role on the edge, because the roles are an open set the corpus keeps extending and
#: a new role must not need an ontology change to be recorded.
REL_ASSERTION_TARGET: Final = "ASSERTION_TARGET"

#: Aggregate: this deity is stated to do this. Derived from the assertion nodes, never
#: authored separately. Declared and empty in V2; populated in V3.
#: (``REL_PERFORMS_ACTION`` is already defined above with the V2 predicates.)

#: Aggregate: this deity is *asked* to do this. The counterpart of
#: ``PERFORMS_ACTION``, and a distinct predicate rather than a property because "Indra
#: slays Vṛtra" and "Indra, slay Vṛtra!" are different claims about the corpus and the
#: commonest thing said to a Vedic god is a request.
REL_IS_ASKED_TO: Final = "IS_ASKED_TO"

#: This passage is ascribed by a traditional index to a deity *descriptor*. A separate
#: predicate from ``HAS_DEVATA`` because the object is not a deity: see
#: :data:`LABEL_DEVATA_ASCRIPTION`. Keeping them apart is what lets the Atharvaveda have an
#: index-based deity layer without the deity census absorbing 324 adjectives.
REL_HAS_DEVATA_ASCRIPTION: Final = "HAS_DEVATA_ASCRIPTION"

#: The deity a descriptor is derived from, where the derivation is a morphological fact --
#: ``āgneyam`` is the vrddhi derivative of ``agni``. Absent where it would be a reading.
REL_ASCRIBES_TO_DEVATA: Final = "ASCRIBES_TO_DEVATA"

# Corpus structure and text surfaces (pre-existing, previously undeclared).
REL_HAS_TEXT_VERSION: Final = "HAS_TEXT_VERSION"
REL_HAS_TRANSLATION: Final = "HAS_TRANSLATION"
#: A textual parallel asserted before the typed cross-Veda predicates existed. 69 edges,
#: retained rather than retyped: retyping them would change what an existing predicate
#: means, which needs an owner decision and not a migration.
REL_PARALLEL_TO: Final = "PARALLEL_TO"

# The data-completeness campaign's predicates.
#: Passage to the reified filler of one semantic role slot.
REL_ASSERTION_ROLE: Final = "ASSERTION_ROLE"
#: A role filler to the entity it resolves to.
REL_REFERS_TO: Final = "REFERS_TO"
#: A rite to a step a Srautasutra or Grhyasutra prints. Distinct from REL_HAS_STEP, which
#: is the Samhita's own numbering, and never summed with it.
REL_HAS_RITUAL_STEP: Final = "HAS_RITUAL_STEP"
#: A registry entity to a passage the registry records as attesting it.
REL_ATTESTED_IN: Final = "ATTESTED_IN"
#: This repository's quality verdict to the passage it assesses. Internal.
REL_QUALITY_VERDICT_ABOUT: Final = "QUALITY_VERDICT_ABOUT"
#: A recorded scholarly disagreement to the passage it concerns.
REL_SCHOLARLY_CLAIM_ABOUT: Final = "SCHOLARLY_CLAIM_ABOUT"
#: A recorded position to the scholar who holds it. Distinct from REL_ASSERTED_BY, whose
#: signature is InterpretiveClaim -> Source; reusing that one was a measured defect.
REL_POSITION_ASSERTED_BY: Final = "POSITION_ASSERTED_BY"
#: A recorded position to the work stating it.
REL_POSITION_STATED_IN: Final = "POSITION_STATED_IN"
#: A recorded disagreement to the work reporting it.
REL_REPORTED_IN: Final = "REPORTED_IN"
#: A narrower deity name to the broader one. Narrower than, NOT an alias for: unlike
#: REL_EPITHET_VARIANT_OF it does not assert one referent under two names.
REL_SPECIALIZED_FORM_OF: Final = "SPECIALIZED_FORM_OF"


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
        REL_EPITHET_VARIANT_OF,
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
        REL_MEMBER_OF_FAMILY,
        REL_HAS_FORMULA,
        REL_SHARES_ENTITY_VOCABULARY_WITH,
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
        # V3
        REL_MENTIONS_DEVATA,
        REL_HAS_SEMANTIC_ASSERTION,
        REL_ASSERTION_AGENT,
        REL_ASSERTION_PREDICATE,
        REL_ASSERTION_TARGET,
        REL_IS_ASKED_TO,
        REL_HAS_DEVATA_ASCRIPTION,
        REL_ASCRIBES_TO_DEVATA,
    }
)

#: Pre-existing corpus-structure and traditional-metadata predicates. Their constants were
#: defined above with the note "listed so the closed vocabulary is complete", and then none
#: of them reached a declared SET -- because RELATIONSHIP_SIGNATURES is asserted equal to
#: DOMAIN_RELATIONSHIP_TYPES and these have no V2 signature. So the closed vocabulary was
#: never actually closed, and eight predicates carrying 138,143 edges were undeclared.
CORPUS_RELATIONSHIP_TYPES: Final[frozenset[str]] = frozenset(
    {
        REL_CONTAINS,
        REL_HAS_TEXT_VERSION,
        REL_HAS_TRANSLATION,
        REL_HAS_RISHI,
        REL_HAS_DEVATA,
        REL_HAS_CHANDAS,
        REL_MENTIONS_LEMMA,
        REL_PARALLEL_TO,
    }
)

#: Predicates the data-completeness campaign introduced. Each endpoint signature below was
#: measured against the live graph rather than intended.
CAMPAIGN_RELATIONSHIP_TYPES: Final[frozenset[str]] = frozenset(
    {
        REL_ASSERTION_ROLE,
        REL_REFERS_TO,
        REL_HAS_RITUAL_STEP,
        REL_ATTESTED_IN,
        REL_QUALITY_VERDICT_ABOUT,
        REL_SCHOLARLY_CLAIM_ABOUT,
        REL_POSITION_ASSERTED_BY,
        REL_POSITION_STATED_IN,
        REL_REPORTED_IN,
        REL_SPECIALIZED_FORM_OF,
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
# This map is **domain predicates only**, and a test enforces that every key is in
# `DOMAIN_RELATIONSHIP_TYPES`. The enrichment layer has its own deliberately-empty
# predicate (`SHARES_FORMULA_WITH`) and declares it in
# `vedagraph.enrich.predicates.UNPOPULATED_BY_DESIGN`, because a domain-layer constant
# claiming authority over an enrichment-layer predicate is the kind of cross-layer reach
# that makes both harder to reason about. The ontology reference reads both.


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
    REL_EPITHET_VARIANT_OF: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEVATA})),
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
    REL_MEMBER_OF_FAMILY: (
        frozenset({LABEL_FORMULA}),
        frozenset({LABEL_FORMULA_FAMILY}),
    ),
    REL_HAS_FORMULA: (
        frozenset({LABEL_FORMULA_FAMILY}),
        frozenset({LABEL_FORMULA}),
    ),
    REL_SHARES_ENTITY_VOCABULARY_WITH: (
        frozenset({LABEL_PASSAGE}),
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
    # ---- V3 -------------------------------------------------------------------------
    REL_MENTIONS_DEVATA: (frozenset({LABEL_PASSAGE}), frozenset({LABEL_DEVATA})),
    REL_HAS_SEMANTIC_ASSERTION: (
        frozenset({LABEL_PASSAGE}),
        frozenset({LABEL_SEMANTIC_ASSERTION}),
    ),
    REL_ASSERTION_AGENT: (
        frozenset({LABEL_SEMANTIC_ASSERTION}),
        frozenset({LABEL_DEVATA, LABEL_DOMAIN_ENTITY}),
    ),
    REL_ASSERTION_PREDICATE: (
        frozenset({LABEL_SEMANTIC_ASSERTION}),
        frozenset({LABEL_ACTION_PREDICATE}),
    ),
    REL_ASSERTION_TARGET: (
        frozenset({LABEL_SEMANTIC_ASSERTION}),
        frozenset({LABEL_DEVATA, LABEL_DOMAIN_ENTITY}),
    ),
    # Widened in V3, and declared once. It was V2's `Devata -> Action` and is now
    # `Devata -> {ActionPredicate, Action}`, because the aggregate points at a member of
    # the closed predicate vocabulary while the five V2 `Action` registry nouns remain
    # reachable. A second entry was briefly left in the V2 block above; two entries for
    # one key is not a widening, it is a silent precedence rule.
    REL_PERFORMS_ACTION: (
        frozenset({LABEL_DEVATA}),
        frozenset({LABEL_ACTION_PREDICATE, LABEL_ACTION}),
    ),
    REL_IS_ASKED_TO: (frozenset({LABEL_DEVATA}), frozenset({LABEL_ACTION_PREDICATE})),
    REL_HAS_DEVATA_ASCRIPTION: (
        frozenset({LABEL_PASSAGE}),
        frozenset({LABEL_DEVATA_ASCRIPTION}),
    ),
    REL_ASCRIBES_TO_DEVATA: (
        frozenset({LABEL_DEVATA_ASCRIPTION}),
        frozenset({LABEL_DEVATA}),
    ),
}

assert set(RELATIONSHIP_SIGNATURES) == DOMAIN_RELATIONSHIP_TYPES, (
    "every declared relationship type needs an endpoint signature"
)


#: Endpoint signatures for the corpus and campaign predicates. Every pair below was measured
#: against the live graph rather than intended, so a signature violation here means the graph
#: changed and not that somebody guessed wrong.
#:
#: Kept out of RELATIONSHIP_SIGNATURES because that dict is asserted to equal
#: DOMAIN_RELATIONSHIP_TYPES exactly, and widening it would silence a check that exists to
#: stop a V2 predicate shipping without a signature.
CORPUS_AND_CAMPAIGN_SIGNATURES: Final[dict[str, tuple[frozenset[str], frozenset[str]]]] = {
    # -- corpus structure -----------------------------------------------------------
    #: A container to what it contains: Work -> Passage, Passage -> Passage, Passage ->
    #: Mantra. One predicate for the whole containment tree.
    REL_CONTAINS: (
        frozenset({LABEL_WORK, LABEL_PASSAGE}),
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
    ),
    REL_HAS_TEXT_VERSION: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({"TextVersion"})),
    REL_HAS_TRANSLATION: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({"Translation"})),
    REL_MENTIONS_LEMMA: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({LABEL_LEMMA})),
    #: Anukramani attribution. Subject is a Mantra or the hymn-level Passage that inherits
    #: it; the 525 and 542 container-level edges are the source asserting at hymn scope.
    REL_HAS_RISHI: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({LABEL_RISHI})),
    REL_HAS_DEVATA: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({LABEL_DEVATA})),
    REL_HAS_CHANDAS: (frozenset({LABEL_PASSAGE, LABEL_MANTRA}), frozenset({LABEL_CHANDAS})),
    REL_PARALLEL_TO: (
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
    ),
    # -- the campaign ---------------------------------------------------------------
    REL_ASSERTION_ROLE: (
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
        frozenset({LABEL_ROLE_FILLER}),
    ),
    #: A filler resolves to any registered entity: measured as Devata, DomainEntity and its
    #: subtypes. The range is the domain-entity family, not one label.
    REL_REFERS_TO: (
        frozenset({LABEL_ROLE_FILLER}),
        frozenset({LABEL_DEVATA, LABEL_DOMAIN_ENTITY}),
    ),
    #: Subject is a Ritual, and 59 of the 3,121 come from a node carrying :SocialRite too --
    #: the three redirect targets M5 labelled, which are rites under both readings.
    REL_HAS_RITUAL_STEP: (
        frozenset({LABEL_RITUAL, LABEL_SOCIAL_RITE}),
        frozenset({LABEL_RITUAL_STEP}),
    ),
    REL_ATTESTED_IN: (
        frozenset({LABEL_DOMAIN_ENTITY}),
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
    ),
    REL_QUALITY_VERDICT_ABOUT: (
        frozenset({LABEL_QUALITY_VERDICT}),
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
    ),
    REL_SCHOLARLY_CLAIM_ABOUT: (
        frozenset({LABEL_SCHOLARLY_DISAGREEMENT}),
        frozenset({LABEL_PASSAGE, LABEL_MANTRA}),
    ),
    REL_POSITION_ASSERTED_BY: (
        frozenset({LABEL_SCHOLARLY_DISAGREEMENT}),
        frozenset({LABEL_SCHOLAR}),
    ),
    REL_POSITION_STATED_IN: (
        frozenset({LABEL_SCHOLARLY_DISAGREEMENT}),
        frozenset({LABEL_SCHOLARLY_WORK}),
    ),
    REL_REPORTED_IN: (
        frozenset({LABEL_SCHOLARLY_DISAGREEMENT}),
        frozenset({LABEL_SCHOLARLY_WORK}),
    ),
    REL_SPECIALIZED_FORM_OF: (frozenset({LABEL_DEVATA}), frozenset({LABEL_DEVATA})),
}

assert set(CORPUS_AND_CAMPAIGN_SIGNATURES) == (
    CORPUS_RELATIONSHIP_TYPES | CAMPAIGN_RELATIONSHIP_TYPES
), "every corpus and campaign predicate needs an endpoint signature"


#: Neo4j has no reserved relationship types of its own, so this set is empty and stays
#: empty. It exists so that "are there system exceptions?" has a declared answer rather than
#: an implicit one, and so that adding an exception is a visible act.
SYSTEM_RELATIONSHIP_TYPES: Final[frozenset[str]] = frozenset()


def all_declared_relationship_types() -> frozenset[str]:
    """Every relationship type any layer of this project declares.

    **Composed, never restated.** Each layer keeps its own authority and this function
    unions them, so a predicate added to a layer appears here automatically and one removed
    disappears -- which is what lets a test prove the gate fails when a declaration is taken
    away.

    Critically, the graph is not an input. The previous scorecard gate computed
    ``declared = ontology | everything in the graph`` and then asked which graph types were
    missing from ``declared``; nothing can be, so it reported 0 undeclared for a whole wave
    while eleven predicates went unclassified. **The data may not declare itself valid.**

    The enrichment layer is imported inside the function to keep the domain package free of
    an import-time dependency on it.
    """
    from vedagraph.enrich.predicates import CONTROLLED_PREDICATES

    return frozenset(
        DOMAIN_RELATIONSHIP_TYPES
        | CORPUS_RELATIONSHIP_TYPES
        | CAMPAIGN_RELATIONSHIP_TYPES
        | CONTROLLED_PREDICATES
        | SYSTEM_RELATIONSHIP_TYPES
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
