"""Search results, and the rank ladder that explains them.

**Why a ladder and not a score.** There is no fulltext index on ``Passage``,
``TextVersion`` or ``Translation``, and this API does not create one. Measured against the
live graph a substring scan of all 18,391 translations takes 19ms and of all 18,235 primary
Sanskrit texts 89ms, so the corpus is small enough that deterministic matching is fast
enough -- and deterministic matching has the property that matters more than speed: every
result can say *why* it is a result.

So relevance is a fixed ten-rung ladder, from an exact canonical key down to a concept
match, and :class:`MatchType` names the rung on every row. :attr:`SearchResult.score` is
derived from the rung and nothing else. It is **a rank ordering, not a confidence**: 0.90
does not mean 90% likely, it means "matched an entity label exactly", and two results with
the same score are ordered by a documented tie-break rather than by a fabricated decimal.
A pseudo-confidence would be the search-shaped version of the failure this whole API
exists to refuse -- a number a reader trusts because it looks measured.

**Why the surfaces are declared.** The searchable surfaces do not cover the corpus evenly,
and the gaps are invisible in a result list. Measured per passage against the live graph:
English translation reaches the Rigveda (10,509), Atharvaveda (5,770), Yajurveda (1,939) and
173 Samavedic passages -- every one of those carrying Griffith's Rigvedic rendering of
verified-identical text rather than a Samavedic translation, so **the Samaveda still has no
English of its own** and 1,671 of its verses cannot be reached in English at all; the
normalised Sanskrit surface exists for the
Atharvaveda alone (5,839); the lemma layer is Rigvedic alone (6,560). A caller who searches
an English phrase and finds nothing Samavedic has learnt nothing about the Samaveda, so
:class:`SearchResponse` carries the surfaces it actually read and the coverage they have.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import Field

from vedagraph.api.models.common import ApiModel, CaveatView, Paginated
from vedagraph.api.models.entity import ENTITY_TYPE_NAMES


class MatchType(StrEnum):
    """Why this row matched, in descending rank order.

    The order of the members *is* the ranking. A consumer that wants "at least an exact
    alias" slices :data:`MATCH_TYPE_ORDER` rather than hard-coding four strings and
    silently missing a rung added later.
    """

    EXACT_CANONICAL_KEY = "EXACT_CANONICAL_KEY"
    """The query is a stable product id or canonical passage key, verbatim."""

    EXACT_CITATION = "EXACT_CITATION"
    """The query is a canonical citation, e.g. ``RV 1.1.1``, ``AVS 3.21.8``, ``VSM 1.1``."""

    EXACT_ENTITY_LABEL = "EXACT_ENTITY_LABEL"
    """The query equals a knowledge object's display, preferred or IAST label."""

    EXACT_ALIAS = "EXACT_ALIAS"
    """The query equals one of an object's recorded aliases."""

    FOLDED_ENTITY_LABEL = "FOLDED_ENTITY_LABEL"
    """The query equals a label or alias once diacritics are folded away on both sides.

    ``yajna`` finds ``sacrifice (yajña)``; ``yaksma`` finds ``consumption (yakṣma)``;
    ``hiranya`` finds ``gold (hiraṇya)``. Without this rung they found nothing at all:
    every entity label in this graph carries IAST diacritics and nothing folded them, so an
    ASCII transliteration could not match an entity even when it named one of the most
    central words in the corpus. It ranks below an exact alias because it IS weaker -- two
    distinct Sanskrit words can fold together -- and above a prefix because matching a
    whole name is stronger than matching its start.
    """

    PREFIX_ENTITY_LABEL = "PREFIX_ENTITY_LABEL"
    """A label begins with the query, before or after folding. Makes type-ahead work."""

    EXACT_SANSKRIT_PHRASE = "EXACT_SANSKRIT_PHRASE"
    """The query occurs in the Sanskrit text as transmitted, accents included."""

    NORMALIZED_SANSKRIT_PHRASE = "NORMALIZED_SANSKRIT_PHRASE"
    """The query occurs in the accent-stripped search surface. Atharvaveda only."""

    LEMMA_FORM = "LEMMA_FORM"
    """The query is a dictionary headword; the row is a passage the lemma occurs in. RV only."""

    TRANSLATION_PHRASE = "TRANSLATION_PHRASE"
    """The query occurs in a public-domain English translation. No Samavedic translation exists."""

    CONCEPT_MATCH = "CONCEPT_MATCH"
    """The query occurs in a concept's definition or description rather than its name."""


#: The ladder, strongest first. Iterated in this order by the search service, so the
#: service cannot rank differently from the documentation.
MATCH_TYPE_ORDER: Final[tuple[MatchType, ...]] = (
    MatchType.EXACT_CANONICAL_KEY,
    MatchType.EXACT_CITATION,
    MatchType.EXACT_ENTITY_LABEL,
    MatchType.EXACT_ALIAS,
    MatchType.FOLDED_ENTITY_LABEL,
    MatchType.PREFIX_ENTITY_LABEL,
    MatchType.EXACT_SANSKRIT_PHRASE,
    MatchType.NORMALIZED_SANSKRIT_PHRASE,
    MatchType.LEMMA_FORM,
    MatchType.TRANSLATION_PHRASE,
    MatchType.CONCEPT_MATCH,
)

assert len(MATCH_TYPE_ORDER) == len(MatchType), "every rung must be in the ranking order"

#: Rung scores. Fixed, hand-assigned, and deliberately coarse: they are labels for the
#: rungs and a client that renders them as a percentage is rendering a rank.
MATCH_TYPE_SCORES: Final[dict[MatchType, float]] = {
    MatchType.EXACT_CANONICAL_KEY: 1.00,
    MatchType.EXACT_CITATION: 0.95,
    MatchType.EXACT_ENTITY_LABEL: 0.90,
    MatchType.EXACT_ALIAS: 0.85,
    MatchType.FOLDED_ENTITY_LABEL: 0.82,
    MatchType.PREFIX_ENTITY_LABEL: 0.80,
    MatchType.EXACT_SANSKRIT_PHRASE: 0.70,
    MatchType.NORMALIZED_SANSKRIT_PHRASE: 0.65,
    MatchType.LEMMA_FORM: 0.60,
    MatchType.TRANSLATION_PHRASE: 0.50,
    MatchType.CONCEPT_MATCH: 0.40,
}

assert set(MATCH_TYPE_SCORES) == set(MatchType), "every rung needs a score"

#: What ``score`` is, said in the OpenAPI document as well as here, because the client that
#: renders a number as a confidence bar never reads the model docstring.
SCORE_SEMANTICS: Final = (
    "score is a RANK ORDERING, NOT A CONFIDENCE. It is derived from `match_type` alone and "
    "carries no probability: 0.90 means 'matched an entity label exactly', not '90% "
    "likely'. Rows sharing a score are ordered by occurrence count and then by stable_id, "
    "so the ordering is total and reproducible."
)

#: The tie-break, documented once and applied by the service.
TIE_BREAK_SEMANTICS: Final = (
    "Within one rung, rows are ordered by the number of occurrences behind them "
    "(mantra_count for a lemma or formula, mention count for an entity, 0 where the graph "
    "records none) and then by stable_id ascending."
)


class SearchResultType(StrEnum):
    """The product type of a search row. Never a raw Neo4j label.

    The first eleven are the types the product specification names. The rest are the
    remaining knowledge types the generic entity surface carries, and they are here because
    the alternative is worse: a search that silently cannot find ``hotar`` because
    ``RitualRole`` had no result type would be an unexplained empty answer, which is the
    one thing this API is built not to return. A module assertion below keeps this enum in
    step with the entity registry, so a type added there without a search type fails at
    import rather than going quietly unsearchable.
    """

    PASSAGE = "PASSAGE"
    DEVATA = "DEVATA"
    RISHI = "RISHI"
    CONCEPT = "CONCEPT"
    RITUAL = "RITUAL"
    FORMULA = "FORMULA"
    CONDITION = "CONDITION"
    RIVER = "RIVER"
    PLANT = "PLANT"
    ANIMAL = "ANIMAL"
    OBJECT = "OBJECT"
    # -- the remainder of the knowledge inventory, for recall rather than for the spec list
    RISHI_FAMILY = "RISHI_FAMILY"
    CHANDAS = "CHANDAS"
    PHILOSOPHICAL_CONCEPT = "PHILOSOPHICAL_CONCEPT"
    OFFERING = "OFFERING"
    SUBSTANCE = "SUBSTANCE"
    CROP = "CROP"
    WEAPON = "WEAPON"
    PLACE = "PLACE"
    HUMAN_CONCERN = "HUMAN_CONCERN"
    FORMULA_FAMILY = "FORMULA_FAMILY"
    METAL = "METAL"
    NATURAL_PHENOMENON = "NATURAL_PHENOMENON"
    COSMIC_ENTITY = "COSMIC_ENTITY"
    TRIBE = "TRIBE"
    SOCIAL_RITE = "SOCIAL_RITE"
    RITUAL_ROLE = "RITUAL_ROLE"
    EPITHET = "EPITHET"
    ACTION_PREDICATE = "ACTION_PREDICATE"
    DEITY_AXIS = "DEITY_AXIS"
    QUALITY = "QUALITY"
    STATE = "STATE"
    DEITY_GROUP = "DEITY_GROUP"


#: The eleven the specification enumerates, kept as data so a test can assert they are all
#: still reachable rather than trusting that nobody renamed one.
SPECIFIED_RESULT_TYPES: Final[tuple[SearchResultType, ...]] = (
    SearchResultType.PASSAGE,
    SearchResultType.DEVATA,
    SearchResultType.RISHI,
    SearchResultType.CONCEPT,
    SearchResultType.RITUAL,
    SearchResultType.FORMULA,
    SearchResultType.CONDITION,
    SearchResultType.RIVER,
    SearchResultType.PLANT,
    SearchResultType.ANIMAL,
    SearchResultType.OBJECT,
)

_RESULT_TYPE_NAMES: Final[frozenset[str]] = frozenset(t.value for t in SearchResultType)

assert ENTITY_TYPE_NAMES <= _RESULT_TYPE_NAMES, (
    "every entity type must have a search result type, or that type is silently "
    f"unsearchable: {sorted(ENTITY_TYPE_NAMES - _RESULT_TYPE_NAMES)}"
)


class SearchSurface(StrEnum):
    """A searchable body of text or labels, named so a response can say what it read."""

    CANONICAL_KEY = "CANONICAL_KEY"
    CANONICAL_CITATION = "CANONICAL_CITATION"
    SANSKRIT_TEXT = "SANSKRIT_TEXT"
    NORMALIZED_SANSKRIT = "NORMALIZED_SANSKRIT"
    ENGLISH_TRANSLATION = "ENGLISH_TRANSLATION"
    ENTITY_LABELS = "ENTITY_LABELS"
    LEMMA = "LEMMA"
    CONCEPT_TEXT = "CONCEPT_TEXT"


class SearchLanguage(StrEnum):
    """Which textual surfaces a caller wants read."""

    ANY = "any"
    SANSKRIT = "sa"
    ENGLISH = "en"


class SurfaceCoverageView(ApiModel):
    """One surface and the corpus it measurably reaches.

    ``passages_by_veda`` is the count of passages that *have* this surface at all, not the
    count that matched. Without it, a query that returns no Samavedic translation row looks
    like a statement about the Samaveda instead of a statement about the fact that no
    Samavedic translation exists in this graph.
    """

    surface: SearchSurface
    passages_by_veda: dict[str, int] = Field(default_factory=dict)
    vedas_not_covered: list[str] = Field(default_factory=list)
    note: str | None = None


class SearchResult(ApiModel):
    """One row, with the reason it is a row attached."""

    type: SearchResultType
    stable_id: str = Field(
        description="The product id to follow, e.g. VG:RV:SAK:M01:S001:V001 or "
        "VG:DEVATA:INDRAH. Never a Neo4j internal id."
    )
    display_label: str
    subtitle: str | None = Field(
        default=None, description="Type, citation or Veda context for disambiguation."
    )
    snippet: str | None = Field(
        default=None,
        description="The matched text in context, truncated. Absent for a label match, "
        "where the label is the whole of the evidence.",
    )
    score: float = Field(description=SCORE_SEMANTICS)
    match_type: MatchType
    veda: str | None = Field(
        default=None,
        description="Corpus code for a passage row. Null on an entity row, which is a "
        "corpus-wide object and not located in one Veda.",
    )


class SearchResponse(Paginated[SearchResult]):
    """A page of results, plus what was searched and what that could not reach."""

    surfaces_searched: list[SearchSurface] = Field(default_factory=list)
    surface_coverage: list[SurfaceCoverageView] = Field(default_factory=list)
    ranking: list[MatchType] = Field(
        default_factory=lambda: list(MATCH_TYPE_ORDER),
        description="The rank ladder this response used, strongest first.",
    )
    score_semantics: str = SCORE_SEMANTICS
    tie_break: str = TIE_BREAK_SEMANTICS


class EntityTypeInfo(ApiModel):
    """One queryable knowledge type, for the type inventory endpoint."""

    slug: str = Field(description="Path segment for /api/v1/entities/{type}.")
    type: str = Field(description="Product type name as it appears on a result row.")
    count: int | None = Field(
        default=None, description="Nodes of this type, or null where it was not counted."
    )
    detail_available: bool = True
    note: str | None = None


class EntityTypeInventory(ApiModel):
    """Every type the generic entity surface serves.

    Exists because :func:`vedagraph.api.repositories.neo4j_repository.validated_label`
    promises it by name in the hint on every unknown-type 400. A 400 whose hint points at a
    route that does not exist is a worse answer than no hint.
    """

    types: list[EntityTypeInfo] = Field(default_factory=list)
    caveats: list[CaveatView] = Field(default_factory=list)
