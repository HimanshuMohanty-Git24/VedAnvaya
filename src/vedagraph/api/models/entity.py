"""Deity, seer, ritual and generic-entity contracts.

The deity models carry the two safety contracts that the ontology freeze deliberately left
to the product layer, and they are the reason this file is longer than a set of DTOs
should be. Both are documented on the models that enforce them:
:class:`DeityPopulation` for "what counts as a Devata", and
:class:`MentionCertainty` for "which mentions a user-facing number is allowed to include".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from pydantic import Field

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    CountedByVeda,
    CoverageView,
    EvidenceBasis,
    EvidenceView,
    KnowledgeStatus,
    Paginated,
    ReferentCertaintyCounts,
)

# ---------------------------------------------------------------------------
# The deity population contract (spec section 16)
# ---------------------------------------------------------------------------

#: Structures that are gods, or at least are the kind of thing the tradition addresses as
#: one. Everything outside this set is a subject of a hymn, not its deity.
#:
#: The Anukramani names a "devata" for every hymn, and that slot is not a theological
#: claim: it holds Indra, and it holds the patron who paid for the hymn, the gift he gave,
#: and in one case a dog. The graph types all of them ``:Devata`` because the Anukramani
#: does, which is faithful to the source and wrong for a product. So the API resolves the
#: population rather than trusting the label, and it does so HERE -- once -- so that every
#: deity endpoint inherits the same answer.
DEITY_STRUCTURES: Final[frozenset[str]] = frozenset({"INDIVIDUAL", "PAIR", "GROUP", "ABSTRACT"})

#: Explicitly not deities: 22 human patrons, 7 danastuti topic labels ("praise of the gift
#: of Sudas son of Pijavana"), and one ``UNSPECIFIED`` entry that is a dog. These are real
#: Anukramani ascriptions and they are excluded from every deity surface.
NON_DEITY_STRUCTURES: Final[frozenset[str]] = frozenset({"HUMAN", "PATRON_PRAISE", "UNSPECIFIED"})

#: ``ABSTRACT`` is admitted but is heterogeneous, and a client needs to know that.
#:
#: It holds genuine abstract personifications the tradition worships -- Sraddha (Faith),
#: Manyu (battle-fury), Nirrti (dissolution), Death -- and it also holds Anukramani topic
#: labels that are what a hymn is ABOUT rather than who it addresses: "food", "knowledge",
#: "ploughing", "concord", "censure of the dice and the gambler". Both carry
#: ``structure='ABSTRACT'`` and no property in the frozen graph separates them.
#:
#: The ontology is frozen, so this is disclosed rather than fixed: every deity response
#: carries ``structure`` and ``axes`` so a client can make its own cut, and the list
#: endpoint attaches this caveat. Splitting the two is a backlog item, not an API change.
ABSTRACT_HETEROGENEITY_CAVEAT: Final = (
    "structure='ABSTRACT' is not uniform. It carries abstract personifications the "
    "tradition addresses as deities (Sraddha, Manyu, Nirrti, Death) alongside Anukramani "
    "topic labels naming what a hymn is about rather than whom it addresses ('food', "
    "'ploughing', 'censure of the dice and the gambler'). No property in the frozen graph "
    "separates the two, so both are returned; use `structure` and `axes` to filter."
)

#: How the graph records, per Veda, why a deity's mention count is what it is. This
#: vocabulary is already measured on every Devata node, so the API maps it rather than
#: recomputing a judgement the build already made.
_VERDICT_TO_STATUS: Final[dict[str, KnowledgeStatus]] = {
    "ATTESTED": KnowledgeStatus.SUPPORTED,
    "NOT_IN_LAYER": KnowledgeStatus.NOT_BUILT,
    "INSUFFICIENT_EVIDENCE": KnowledgeStatus.INSUFFICIENT_EVIDENCE,
}


class MentionCertainty(StrEnum):
    """Which mention tiers a request wants counted.

    ``agni`` is the god and it is fire; ``soma`` is the god, the plant and the drink. The
    graph grades every mention edge accordingly, and the split is not marginal: Soma has
    240 CERTAIN, 181 PROBABLE and 1,091 AMBIGUOUS mentions, so the tier choice moves that
    number by a factor of four.

    ``DEFAULT`` (CERTAIN + PROBABLE) is the product default. ``STRICT`` is offered but
    warned about: filtering to CERTAIN alone returns zero non-Rigvedic mentions for Agni,
    Soma, Surya, Mitra, Savitr, Usas, Vayu, Apah and Prthivi, so the cautious caller gets a
    worse answer than the careless one and reads those zeros as absence from the text.
    """

    DEFAULT = "default"
    STRICT = "strict"
    EXPLORATORY = "exploratory"


class DeityPopulation(StrEnum):
    """Which slice of the Anukramani's devata slot a request wants."""

    DEITIES = "deities"
    """The resolved population. Human patrons, gift-praise and non-divine subjects excluded."""

    ALL_ASCRIPTIONS = "all_ascriptions"
    """Everything the Anukramani names, including patrons. Each row states its structure."""


class VedaMentionCount(ApiModel):
    """One Veda's mention figure, with the reason it is what it is.

    ``count`` is nullable and a null is never a zero. ``NOT_IN_LAYER`` means this deity's
    mention layer does not reach that corpus; ``INSUFFICIENT_EVIDENCE`` means it does and
    cannot establish the claim. Rendering either as 0 is the specific misreading this
    project spent three sessions removing from its benchmark.
    """

    veda: str
    count: int | None = None
    status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    certainty: ReferentCertaintyCounts | None = None


class DimensionStatus(ApiModel):
    """One dimension of a profile that is NOT answered, and why it is not.

    The Devata nodes carry ``profile_absent_dimensions``, a list naming the dimensions the
    build could not establish for that deity -- for Agni it is ``['co_devatas']``, and 25
    of the 214 deities carry at least one entry. Every one of those dimensions is a list
    field on the profile, and the frozen graph stores an empty list for it. Returning that
    empty list as-is would assert "Agni co-occurs with no deity", which is false and is the
    exact shape the benchmark grades MISLEADING.

    So the empty list travels with a row here instead. ``NOT_BUILT`` where the layer the
    dimension needs does not reach this deity at all -- the action dimensions come from the
    Rigveda-only lemma annotation, and six deities absent from them are absent from the
    Rigvedic morphology rather than from Vedic action -- and ``INSUFFICIENT_EVIDENCE``
    where the layer does reach it and could not settle the question.
    """

    dimension: str = Field(description="The profile field this concerns, e.g. co_deities.")
    status: KnowledgeStatus
    note: str = Field(description="Why the field is empty. Never 'no data'.")


class CentralityView(ApiModel):
    """A domain entity's measured prominence, with its unbuilt half kept unbuilt.

    ``centrality_bridging`` is not a number in the frozen graph. It is the string
    ``"NOT_BUILT: no community structure exists in this graph, so bridge centrality is not
    computable and is not reported as a zero"`` -- a status the build wrote into a field a
    reader would render as a metric. This model keeps the two apart: ``bridging`` stays
    null and ``bridging_status`` says NOT_BUILT, so no client can plot the prose as 0.
    """

    degree: float | None = None
    share: float | None = None
    measure: str | None = Field(
        default=None, description="What was measured, e.g. DEGREE_OVER_PASSAGE_CO_MENTION."
    )
    layer: str | None = Field(default=None, description="The edge layer it was measured over.")
    bridging: float | None = None
    bridging_status: KnowledgeStatus = KnowledgeStatus.NOT_BUILT
    bridging_note: str | None = None


class RecallView(ApiModel):
    """How much of what this entity should reach, it measurably reaches.

    Recall is a returned field and not a caveat, deliberately. ``USED_FOR_RITE`` tags 14 of
    the 141 passages of Atharvaveda Kanda 14 for marriage -- 9.93% -- and the reader who
    runs the obvious query never sees a caveat. ``is_measured`` false means unmeasured, not
    complete, and ``alias_purity`` null means unmeasured, not clean.
    """

    is_measured: bool = False
    basis: str | None = None
    strict_recall_against_locus: float | None = None
    locus_veda: str | None = None
    locus_book: str | None = None
    locus_tagged_passages: int | None = None
    locus_book_passages: int | None = None
    mention_edges_total: int | None = None
    mention_edges_own_alias: int | None = None
    mention_edges_foreign_alias: int | None = None
    alias_purity: float | None = Field(
        default=None, description="Null means unmeasured. It never means 1.0."
    )
    alias_purity_basis: str | None = None


class EntityRef(ApiModel):
    """A pointer to another knowledge object, safe to render and to follow."""

    type: str = Field(description="Product type, e.g. DEVATA. Never a raw graph label.")
    id: str = Field(description="Stable product id, e.g. VG:DEVATA:INDRAH. Never a Neo4j id.")
    display_label: str
    subtitle: str | None = None


class AttributedRef(EntityRef):
    """A pointer that also says how the attribution was arrived at.

    Vedic attribution is mostly inherited: 15,177 of 17,889 seer edges are a sukta's label
    projected onto each mantra inside it, and every one of the Atharvaveda's 5,084 is. A
    reference that does not carry its precision lets a hymn-level ascription be read as a
    statement the verse itself makes.
    """

    attribution_precision: str | None = Field(
        default=None, description="PER_PASSAGE (source-stated) or CONTAINER_INHERITED."
    )
    evidence_basis: EvidenceBasis = EvidenceBasis.UNKNOWN
    passage_count: int | None = None


class EntitySummary(ApiModel):
    """The list-row shape for every knowledge type."""

    type: str
    id: str
    display_label: str
    label_iast: str | None = None
    subtitle: str | None = None
    short_description: str | None = None
    passage_count: int | None = None


class DevataSummary(EntitySummary):
    """A deity list row. ``structure`` is always present so a client can re-filter."""

    is_deity: bool = Field(
        description="False when this row is an Anukramani ascription that is not a god -- "
        "a human patron, a praise-of-a-gift label, or the dog. Only reachable with "
        "population=all_ascriptions, and always present so a client never has to infer it "
        "from `structure`."
    )
    structure: str | None = None
    axes: list[str] = Field(default_factory=list)
    is_composite: bool = False
    mentions_default_total: int | None = None
    certainty: ReferentCertaintyCounts | None = None


class DevataProfile(ApiModel):
    """The flagship deity payload.

    Every count here obeys the ambiguity contract: totals are CERTAIN + PROBABLE unless the
    caller asked otherwise, and all three tiers are reported so the caller can see what the
    default excluded.
    """

    type: str = "DEVATA"
    id: str
    display_label: str
    label_iast: str | None = None
    label_en: str | None = None
    preferred_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    short_description: str | None = None

    structure: str | None = None
    is_composite: bool = False
    component_count: int = 0
    axes: list[str] = Field(default_factory=list)
    epithets: list[str] = Field(default_factory=list)

    population: DeityPopulation = DeityPopulation.DEITIES
    is_deity: bool = Field(
        description="False when this subject is an Anukramani ascription that is not a "
        "god. Only reachable with population=all_ascriptions, and accompanied by the "
        "THIS SUBJECT IS NOT A DEITY caveat that every deity route attaches."
    )

    certainty: ReferentCertaintyCounts
    mentions_by_veda: list[VedaMentionCount] = Field(default_factory=list)
    mentions_included_total: int | None = Field(
        default=None,
        description="Mentions summed over the tiers this request included. Null, never 0, "
        "where no included tier has evidence for this deity.",
    )
    mention_scope: list[str] = Field(default_factory=list)
    included_certainty: MentionCertainty = MentionCertainty.DEFAULT

    attributed_total: int | None = None
    attributed_per_passage: int | None = Field(
        default=None, description="Attributions the source states verse by verse."
    )
    attributed_inherited: int | None = Field(
        default=None, description="Attributions projected down from a containing sukta."
    )
    attribution_scope: list[str] = Field(
        default_factory=list,
        description="Vedas the Anukramani attribution layer reaches. It is Rigveda-only, "
        "so a zero elsewhere is a missing layer and not an absent deity.",
    )

    top_rishis: list[str] = Field(default_factory=list)
    top_chandas: list[str] = Field(default_factory=list)
    top_concepts: list[str] = Field(default_factory=list)
    top_actions: list[str] = Field(default_factory=list)
    top_requested_actions: list[str] = Field(default_factory=list)
    top_objects: list[str] = Field(default_factory=list)
    co_deities: list[EntityRef] = Field(
        default_factory=list,
        description="Resolved through the deity population contract. The frozen "
        "`profile_co_devatas` property holds display labels rather than keys and Indra's "
        "is ['Vasukra'], a human patron; labels that resolve to a non-deity or to nothing "
        "are dropped and reported in `dimension_status`.",
    )
    co_mentioned: list[str] = Field(default_factory=list)
    formula_count: int | None = None
    top_formulas: list[EntityRef] = Field(
        default_factory=list,
        description="Formulas recurring in mantras that name this deity. There is no "
        "deity-to-formula edge in the graph, so this is co-occurrence within the mention "
        "layer and not a claim that the formula is about the deity.",
    )
    interpretive_claims: list[EntityRef] = Field(default_factory=list)

    dimension_status: list[DimensionStatus] = Field(
        default_factory=list,
        description="Every dimension above whose empty value is NOT an assertion of "
        "absence. Read this before reading any empty list in this payload.",
    )

    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)


class DevataNetworkEdge(ApiModel):
    """One co-occurrence edge, with the enrichment it carries and its own caveat.

    ``lift`` is above 1 when the pair is named together more often than the corpus baseline
    would produce, and the Rigvedic and non-Rigvedic passage counts are separate columns
    because the two halves of the mention layer were produced by different instruments --
    manual annotation for the Rigveda, adjudicated surface matching elsewhere.
    """

    other: EntityRef
    lift: float | None = None
    passage_count: int | None = None
    rv_passage_count: int | None = None
    non_rv_passage_count: int | None = None
    per_veda_counts: dict[str, int] = Field(default_factory=dict)
    example_citations: list[str] = Field(default_factory=list)
    quality_tier: str | None = None


class DevataNetwork(ApiModel):
    """A deity's immediate graph neighbourhood, every side of it population-filtered.

    Carries the SUBJECT's typing as well as its neighbours'. Under
    ``population=all_ascriptions`` this endpoint served the dog as ``type=DEVATA`` with
    ``display_label='the dog'`` and no ``structure`` anywhere in the payload, beneath a
    caveat telling the client to "read each row's `structure` before calling any of them a
    deity" -- advice the subject could not be checked against. The neighbour filter was
    applied and the subject disclosure was not, on the sibling route to the one that had
    it, which is the same defect class one step narrower.
    """

    type: str = "DEVATA"
    id: str
    display_label: str
    subject_structure: str | None = Field(
        default=None,
        description="The subject's Anukramani structure, so a payload served under "
        "population=all_ascriptions states what it is serving.",
    )
    subject_is_deity: bool = True
    co_occurring: list[DevataNetworkEdge] = Field(default_factory=list)
    components: list[EntityRef] = Field(
        default_factory=list, description="For a PAIR or GROUP: the deities it is made of."
    )
    member_of: list[EntityRef] = Field(default_factory=list)
    axes: list[EntityRef] = Field(default_factory=list)
    associated_entities: list[EntityRef] = Field(default_factory=list)
    shared_rishi_deities: list[EntityRef] = Field(
        default_factory=list,
        description="Deities reached through seers this deity shares. Filtered through the "
        "deity population contract: unfiltered, Indra's neighbours include Vasukra, "
        "Vamadeva, Atri, Brbu the carpenter and four praise-of-a-gift labels.",
    )
    dimension_status: list[DimensionStatus] = Field(default_factory=list)
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class MentionBasis(StrEnum):
    """Which of the two deity-passage relations a caller means.

    They are not interchangeable and the difference is the single most common misreading of
    this graph. ``MENTION`` is the four-Veda question "is this deity named in this verse?"
    (17,165 edges over all four corpora). ``ASCRIPTION`` is the Anukramani's statement
    "this hymn is for this deity" (10,558 edges, every one Rigvedic, 8,329 of them a
    sukta's label projected onto its mantras). A count from one presented as the other is
    wrong by construction, not by degree.
    """

    MENTION = "mention"
    ASCRIPTION = "ascription"


class DevataPassageRef(ApiModel):
    """A passage related to a deity, carrying which relation put it there."""

    passage_id: str
    citation: str | None = None
    veda: str | None = None
    basis: MentionBasis
    referent_certainty: str | None = Field(
        default=None, description="DEITY_CERTAIN / DEITY_PROBABLE / DEITY_AMBIGUOUS. Mentions only."
    )
    attribution_precision: str | None = Field(
        default=None, description="PER_PASSAGE or CONTAINER_INHERITED. Ascriptions only."
    )
    occurrences: int | None = None
    matched_forms: list[str] = Field(default_factory=list)
    evidence: EvidenceView | None = None


class DevataPassagePage(Paginated[DevataPassageRef]):
    """A page of deity passages that carries the ambiguity split it was filtered by.

    The contract is that all three tiers are ALWAYS reported, and a bare page of rows
    breaks it: filtered to the default tiers, Soma returns 421 rows and says nothing about
    the 1,091 DEITY_AMBIGUOUS mentions the filter removed, so a client cannot see that the
    number it is reading is a quarter of the layer. ``certainty`` is therefore on the page,
    measured over the whole edge set rather than over the page.
    """

    certainty: ReferentCertaintyCounts = Field(
        description="CERTAIN / PROBABLE / AMBIGUOUS over ALL of this deity's mention edges, "
        "not just the page, with `included_tiers` naming what this request counted."
    )
    basis: MentionBasis
    subject_structure: str | None = Field(
        default=None,
        description="The subject's Anukramani structure. Present so a page served under "
        "population=all_ascriptions states what it is serving.",
    )
    subject_is_deity: bool = True
    matched_total: int | None = Field(
        default=None,
        description="Passages reached at the included tiers. Null, never 0, where the "
        "relation does not reach this subject at all.",
    )


class RishiProfile(ApiModel):
    """A seer, with strict and inherited attribution kept apart.

    The two must never be summed into one "passages by this seer" number: the Yajurveda's
    2,240 seer edges are every one source-stated, and the Atharvaveda's 5,084 are every one
    inherited, so a blended total compares a statement of the text against a projection.
    """

    type: str = "RISHI"
    id: str
    display_label: str
    label_iast: str | None = None
    preferred_label: str | None = None
    normalized_name: str | None = None

    is_seer: bool = Field(
        description="False for 113 of the 729 :Rishi nodes. The Anukramani's rishi slot "
        "also holds the being a hymn ADDRESSES, so Aditi and the Waters are in it. A false "
        "here must never be rendered as a seer, and it is never a reason to render the "
        "node as a deity either -- the deity surface has its own population contract."
    )
    non_seer_kind: str | None = Field(
        default=None,
        description="Why this ascription is not a seer, when it is not one: DEITY (58), "
        "ABSTRACTION (21), MYTHIC_BEING (13), DEITY_GROUP (11), PLANT_OR_ANIMAL (5), "
        "COLLECTIVE (3), OBJECT (2).",
    )
    family_assignment_class: str | None = None
    registry_namespace: str | None = None
    occurrence_count: int | None = None
    patronymic_iast: str | None = None
    patronymics_iast: list[str] = Field(default_factory=list)
    personal_name_iast: str | None = None
    personal_names_iast: list[str] = Field(default_factory=list)
    decomposition_method: str | None = None
    layer_veda_scope: list[str] = Field(default_factory=list)

    family: EntityRef | None = None
    family_members: list[EntityRef] = Field(default_factory=list)
    passages_source_stated: int | None = None
    passages_container_inherited: int | None = None
    passages_by_veda: list[VedaMentionCount] = Field(default_factory=list)
    deities: list[AttributedRef] = Field(default_factory=list)
    concepts: list[EntityRef] = Field(default_factory=list)
    chandas: list[EntityRef] = Field(default_factory=list)
    formula_count: int | None = None
    dimension_status: list[DimensionStatus] = Field(default_factory=list)
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)


class RitualStep(ApiModel):
    order: int | None = None
    display_label: str
    description: str | None = None


class RitualProfile(ApiModel):
    """One of the eight modelled rites.

    Eight is not a taxonomy of Vedic ritual and the response says so in
    ``coverage_statement`` rather than leaving a client to infer completeness from a list
    that happens to have eight entries in it.
    """

    type: str = "RITUAL"
    id: str
    display_label: str
    label_iast: str | None = None
    short_description: str | None = None
    steps: list[RitualStep] = Field(
        default_factory=list,
        description="Only 3 HAS_STEP edges exist across all 8 rites, all of them on the "
        "soma pressing, so this list is empty for 7 of the 8. An empty list here is NOT "
        "an unstructured rite -- read `dimension_status` for which it is.",
    )
    roles: list[EntityRef] = Field(default_factory=list)
    offerings: list[EntityRef] = Field(default_factory=list)
    substances: list[EntityRef] = Field(default_factory=list)
    objects: list[EntityRef] = Field(default_factory=list)
    devatas: list[EntityRef] = Field(default_factory=list)
    purposes: list[EntityRef] = Field(default_factory=list)
    broader_than: list[EntityRef] = Field(default_factory=list)
    passages: list[EntityRef] = Field(default_factory=list)
    passage_count: int | None = None
    mention_count: int | None = None
    coverage_statement: str
    dimension_status: list[DimensionStatus] = Field(default_factory=list)
    data_status: KnowledgeStatus = KnowledgeStatus.PARTIAL
    caveats: list[CaveatView] = Field(default_factory=list)


class RitualSummary(EntitySummary):
    """A rite list row. Carries the eight-rite bound on the row, not only in the header."""

    inventory_coverage: str = Field(
        description="Stated per row because a list of eight implies a taxonomy of eight."
    )
    step_count: int | None = None
    devata_count: int | None = None
    described_in_count: int | None = None


class EntityListRow(EntitySummary):
    """The row the generic entity list returns, for every type.

    The condition fields are on this base and not only on :class:`ConditionSummary`, and
    that is a fix for a measured defect rather than laziness. FastAPI validates a response
    against its declared ``response_model``, so a route declaring
    ``Paginated[EntitySummary]`` and returning ``ConditionSummary`` rows serialises them
    through the base model and **silently drops ``kind``** -- which is exactly the field
    that stops a demon being read as a disease. Declaring the union of fields on the row
    the route actually promises makes that loss impossible: a null ``kind`` on a plant is
    noise, a missing ``kind`` on an affliction is the category error the contract exists to
    prevent.
    """

    kind: str | None = Field(default=None, description="AFFLICTION, THREAT or PATHOGEN_OR_CAUSE.")
    treated_by_count: int | None = None
    protected_from_count: int | None = None

    is_seer: bool | None = Field(
        default=None,
        description="For type RISHI: whether this is a seer at all. 113 of the 729 :Rishi "
        "nodes are not -- the Anukramani's rishi slot also holds the being a hymn "
        "ADDRESSES, so Aditi and the Waters are in it. Null on every other type. On the "
        "ROW and not only on the profile, because the list is where a client picks one.",
    )
    non_seer_kind: str | None = Field(
        default=None,
        description="Why this ascription is not a seer, when it is not one: DEITY (58), "
        "ABSTRACTION (21), MYTHIC_BEING (13), DEITY_GROUP (11), PLANT_OR_ANIMAL (5), "
        "COLLECTIVE (3), OBJECT (2).",
    )


class ConditionSummary(EntityListRow):
    """An Atharvavedic condition, always carrying its kind.

    ``AFFLICTION``, ``THREAT`` and ``PATHOGEN_OR_CAUSE`` are three different things and a
    disease list that returns a demon is a category error, not a rounding error. The kind
    is therefore on the row and not only in the filter.
    """


def parse_json_property(value: Any) -> Any:
    """Read one of the graph's JSON-string properties.

    Several profile fields are stored as JSON text rather than as native maps
    (``profile_mentions_by_veda``, ``hierarchy``, ``native_labels``). A malformed one
    returns None rather than raising: a single bad property should degrade one field, not
    fail the request.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return None


def status_for_verdict(verdict: str | None) -> KnowledgeStatus:
    """Map the graph's own per-Veda verdict onto the API's status vocabulary."""
    if verdict is None:
        return KnowledgeStatus.INSUFFICIENT_EVIDENCE
    return _VERDICT_TO_STATUS.get(verdict, KnowledgeStatus.INSUFFICIENT_EVIDENCE)


# ---------------------------------------------------------------------------
# The generic entity surface (spec section 18): one system, not twenty
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityTypeSpec:
    """One queryable knowledge type: its URL slug, its graph label, its identity property.

    The identity property is per-type and not uniform, which is why this table exists
    rather than a convention. ``Rishi`` and ``Chandas`` key on ``entity_key``, the domain
    entities carry both ``entity_key`` and ``concept_id``, ``RishiFamily`` keys on
    ``family_key``, ``Formula`` on ``formula_id``, ``FormulaFamily`` on ``family_id``,
    ``Epithet`` on ``epithet_key``, ``DeityAxis`` on ``axis_key``, ``DeityGroup`` on
    ``group_key``, and ``ActionPredicate`` has no ``*_key`` property at all -- its identity
    is ``predicate``, verified unique at 41 distinct values over 41 nodes. A service that
    assumed ``entity_key`` everywhere would 404 on six of the thirty-one types while
    reporting that the entity does not exist, which is the wrong answer said confidently.
    """

    slug: str
    label: str
    type_name: str
    id_property: str
    #: Set where a richer surface owns the detail view, so the generic one stays a summary.
    detail_note: str | None = None


def _spec(slug: str, label: str, type_name: str, id_property: str = "entity_key") -> EntityTypeSpec:
    return EntityTypeSpec(slug=slug, label=label, type_name=type_name, id_property=id_property)


#: Every type reachable at ``/api/v1/entities/{type}``, with its live node count in the
#: frozen graph noted beside it. Deities are deliberately ABSENT: they are served only by
#: ``/api/v1/devatas``, because the generic surface has no deity population filter and a
#: deity list without one returns 22 human patrons and a dog.
ENTITY_TYPES: Final[dict[str, EntityTypeSpec]] = {
    spec.slug: spec
    for spec in (
        _spec("rishi", "Rishi", "RISHI"),  # 729
        _spec("rishi_family", "RishiFamily", "RISHI_FAMILY", "family_key"),  # 87
        _spec("chandas", "Chandas", "CHANDAS"),  # 575
        _spec("concept", "Concept", "CONCEPT"),  # 229
        _spec("philosophical_concept", "PhilosophicalConcept", "PHILOSOPHICAL_CONCEPT"),  # 13
        _spec("ritual", "Ritual", "RITUAL"),  # 8
        _spec("offering", "Offering", "OFFERING"),  # 8
        _spec("substance", "Substance", "SUBSTANCE"),  # 15
        _spec("plant", "Plant", "PLANT"),  # 22
        _spec("crop", "Crop", "CROP"),  # 5
        _spec("animal", "Animal", "ANIMAL"),  # 15
        _spec("object", "Object", "OBJECT"),  # 23
        _spec("weapon", "Weapon", "WEAPON"),  # 5
        _spec("river", "River", "RIVER"),  # 8
        _spec("place", "Place", "PLACE"),  # 11
        _spec("condition", "Condition", "CONDITION"),  # 36
        _spec("human_concern", "HumanConcern", "HUMAN_CONCERN"),  # 7
        EntityTypeSpec(
            slug="formula",
            label="Formula",
            type_name="FORMULA",
            id_property="formula_id",
            detail_note="Formula family membership and cross-Veda reuse are served by the "
            "formula surface; this view is the summary the generic surface carries.",
        ),  # 4,825
        EntityTypeSpec(
            slug="formula_family",
            label="FormulaFamily",
            type_name="FORMULA_FAMILY",
            id_property="family_id",
            detail_note="Family membership roles and diffusion are served by the formula "
            "surface; this view is the summary the generic surface carries.",
        ),  # 720
        _spec("metal", "Metal", "METAL"),  # 7
        _spec("natural_phenomenon", "NaturalPhenomenon", "NATURAL_PHENOMENON"),  # 13
        _spec("cosmic_entity", "CosmicEntity", "COSMIC_ENTITY"),  # 4
        _spec("tribe", "Tribe", "TRIBE"),  # 5
        _spec("social_rite", "SocialRite", "SOCIAL_RITE"),  # 5
        _spec("ritual_role", "RitualRole", "RITUAL_ROLE"),  # 11
        _spec("epithet", "Epithet", "EPITHET", "epithet_key"),  # 13
        _spec("action_predicate", "ActionPredicate", "ACTION_PREDICATE", "predicate"),  # 41
        _spec("deity_axis", "DeityAxis", "DEITY_AXIS", "axis_key"),  # 22
        _spec("quality", "Quality", "QUALITY"),  # 3
        _spec("state", "State", "STATE"),  # 3
        _spec("deity_group", "DeityGroup", "DEITY_GROUP", "group_key"),  # 2
    )
}

#: Product type names the generic surface can return. Imported by the search models, which
#: assert that every one of them has a search result type.
ENTITY_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    spec.type_name for spec in ENTITY_TYPES.values()
)

#: Graph label -> product type name, for mapping a traversal result without ever letting a
#: raw Neo4j label reach a response body.
TYPE_NAME_BY_LABEL: Final[dict[str, str]] = {
    spec.label: spec.type_name for spec in ENTITY_TYPES.values()
} | {"Devata": "DEVATA", "Passage": "PASSAGE", "Mantra": "PASSAGE"}

#: Identity properties this API is willing to name in a query, checked before one is
#: interpolated. A second gate behind :data:`ENTITY_TYPES`: the registry decides which
#: property a type uses, and this refuses anything not on the list even if the registry
#: were later mis-edited.
ALLOWED_ID_PROPERTIES: Final[frozenset[str]] = frozenset(
    spec.id_property for spec in ENTITY_TYPES.values()
)

#: Slugs a caller might reasonably try for deities, refused with a pointer rather than
#: served. Serving a deity here would be serving it without the population contract.
DEITY_SLUGS: Final[frozenset[str]] = frozenset({"devata", "devatas", "deity", "deities", "god"})

#: Why a deity is refused by the generic surface. Not an apology -- a safety property.
DEITY_SURFACE_REDIRECT: Final = (
    "Deities are not served by the generic entity surface. The Anukramani's devata slot "
    "holds 22 human patrons, 7 praise-of-a-gift labels and one dog alongside the gods, and "
    "resolving that population is a contract only the deity endpoints apply. Use "
    "GET /api/v1/devatas (add population=all_ascriptions to see the slot as it stands)."
)


#: Every ``axis`` value the frozen graph's 22 ``:DeityAxis`` nodes carry. Declared so an
#: unknown axis can be refused OFFLINE, by name, rather than becoming a 200 with an empty
#: page that looks exactly like an axis with no members. Asserted against the live graph by
#: ``tests/api/test_devatas.py::test_the_declared_axis_space_matches_the_graph``.
KNOWN_DEITY_AXES: Final[frozenset[str]] = frozenset(
    {
        "ABSTRACT_PERSONIFICATION",
        "ANCESTRAL",
        "AQUATIC",
        "ARTISAN",
        "ATMOSPHERIC",
        "CHTHONIC",
        "COSMIC_SOVEREIGN",
        "DAWN_TIME",
        "FIRE_MEDIUM",
        "GUARDIAN_OF_ORDER",
        "HEALER",
        "LUNAR",
        "NOCTURNAL",
        "PRIESTLY",
        "PSYCHOPOMP",
        "RITUAL_OBJECT",
        "RITUAL_SUBSTANCE",
        "SOLAR",
        "SPEECH",
        "TERRESTRIAL",
        "UNSPECIFIED",
        "WARRIOR",
    }
)


class ConditionKindFilter(StrEnum):
    """Which kind of Condition a caller means.

    ``AFFLICTION`` is the default and the reason this enum exists. Of the 718
    ``MENTIONS_ENTITY`` edges reaching a ``Condition``, 314 reach a THREAT and 88 a
    PATHOGEN_OR_CAUSE, so an unfiltered disease query ranks rakshas, sorcery, curses, worms
    and poison as diseases. ``ANY`` is available and returns the kind on every row.
    """

    AFFLICTION = "AFFLICTION"
    THREAT = "THREAT"
    PATHOGEN_OR_CAUSE = "PATHOGEN_OR_CAUSE"
    ANY = "ANY"


class EntityProfile(ApiModel):
    """The generic detail payload for any non-deity knowledge type.

    One model for thirty-one types, because thirty-one nearly-identical models is how a
    caveat comes to be applied to twenty-nine of them. Where a type has a genuinely
    different shape the block is nested and typed rather than flattened: ``seer`` carries
    the full :class:`RishiProfile` for ``type=RISHI``, whose strict and inherited
    attribution must not be summed and cannot be expressed in a shared field.
    """

    type: str
    id: str
    display_label: str
    label_iast: str | None = None
    preferred_label_en: str | None = None
    preferred_label_sa: str | None = None
    aliases_en: list[str] = Field(default_factory=list)
    aliases_sa: list[str] = Field(default_factory=list)
    definition: str | None = None
    short_description: str | None = None
    condition_kind: str | None = Field(
        default=None,
        description="AFFLICTION, THREAT or PATHOGEN_OR_CAUSE. On the row and not only in "
        "the filter, so a demon cannot be read as a disease by whoever forgot the filter.",
    )
    centrality: CentralityView | None = None
    recall: RecallView | None = None
    passages_by_veda: CountedByVeda | None = None
    passage_count: int | None = None
    neighbours: list[EntityRef] = Field(
        default_factory=list,
        description="Objects joined to this one by a CURATED edge -- a broader concept, an "
        "associated deity, a family member. Most domain entities have none: the graph "
        "links them to passages, not to each other.",
    )
    co_mentioned: list[EntityRef] = Field(
        default_factory=list,
        description="Objects named in the same mantras, strongest first. This is the "
        "neighbourhood a reader means by 'what surrounds fever' -- and it is "
        "CO-OCCURRENCE WITHIN A MANTRA, carrying no causal, prescriptive or pharmacological "
        "claim. A plant named beside an affliction is named beside it and nothing more.",
    )
    seer: RishiProfile | None = Field(default=None, description="Present only when type is RISHI.")
    dimension_status: list[DimensionStatus] = Field(default_factory=list)
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)
