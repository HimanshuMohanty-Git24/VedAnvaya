"""Deterministic, evidence-aware aggregate views.

Routes only: parameter validation, the service call, the response. Every Cypher these
endpoints run lives in :mod:`vedagraph.api.services.insight_service` or in the frozen query
catalogue, so a query cannot be tuned in a route where nobody would look for it.

The OpenAPI descriptions here carry each endpoint's cost class as well as its meaning. The
product's latency target exempts aggregate and census endpoints, and an exemption a caller
cannot see before calling is not an exemption -- so the label is in the docs *and* in
``cost_class`` on every response body.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.entity import DeityPopulation, MentionCertainty
from vedagraph.api.models.insight import (
    AtharvavedaConcernsResponse,
    CapabilitiesResponse,
    CivilizationResponse,
    CrossVedaMatrixResponse,
    DevataByBookResponse,
    DevataByMetreResponse,
    DevataDispersionResponse,
    DevataInsightResponse,
    FormulaDiffusionResponse,
    MaterialCultureResponse,
    MetalsInsightResponse,
    RitualsInsightResponse,
)
from vedagraph.api.services.insight_service import MATERIAL_CATEGORIES, InsightService
from vedagraph.domain.theonyms import (
    DEFAULT_REFERENT_TIERS,
    EXPLORATORY_REFERENT_TIERS,
    STRICT_REFERENT_TIERS,
)

router = APIRouter(tags=["Insights"], responses=COMMON_ERROR_RESPONSES)

LimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Rows per page. A larger value is refused rather than truncated, "
        "because a silently truncated page is indistinguishable from the end of the data.",
    ),
]
OffsetQuery = Annotated[int, Query(ge=0, description="Rows to skip.")]

_TIERS_BY_CERTAINTY = {
    MentionCertainty.DEFAULT: DEFAULT_REFERENT_TIERS,
    MentionCertainty.STRICT: STRICT_REFERENT_TIERS,
    MentionCertainty.EXPLORATORY: EXPLORATORY_REFERENT_TIERS,
}


@router.get(
    "/insights/cross-veda",
    summary="Cross-Veda relatedness matrix (aggregate)",
    description=(
        "**Cost class: AGGREGATE.** Scans six relationship types in full and is exempt from "
        "the median latency target.\n\n"
        "Returns all six corpus pairs against every relationship class, with **every cell "
        "typed** -- including the empty ones. A cell is `MEASURED`, `MEASURED_ZERO`, "
        "`NOT_ESTABLISHED_FOR_PAIR`, `CLASS_NOT_CROSS_VEDA` or `NOT_BUILT`, and the count is "
        "null for every status but the first two. That distinction is the endpoint's whole "
        "purpose: directed textual reuse exists for one corpus pair only, and a table that "
        "rendered the other five as `0` would say the Atharvaveda reuses no Rigvedic text "
        "while the same graph carries hundreds of parallels between them.\n\n"
        "The semantic-resemblance and semantic-assertion rows are `NOT_BUILT` for every pair "
        "and are returned anyway -- the first because no non-lexical measure exists in this "
        "graph, the second because every semantic assertion is Rigvedic and so has no "
        "non-Rigvedic endpoint to pair with."
    ),
    response_model=CrossVedaMatrixResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def cross_veda_matrix(repository: RepositoryDep) -> CrossVedaMatrixResponse:
    return InsightService(repository).cross_veda_matrix()


# ---------------------------------------------------------------------------
# The three visualization blockers (GAP-PRODUCT_SURFACE-003)
#
# Three aggregates a live design spec named as blocking three charts, all three of them API
# omissions over data the graph already holds. Each is served here rather than left to
# client-side aggregation of /devatas/{id}/passages, which the spec itself warned against:
# that route is capped at 200 rows a page, so a chart assembled by paging it truncates
# silently and a truncated heatmap is indistinguishable from a sparse one.
# ---------------------------------------------------------------------------


_DEVATA_PATH = Annotated[
    str,
    Path(
        min_length=3,
        max_length=200,
        description="Product id of the deity, e.g. VG:DEVATA:INDRAH.",
    ),
]
_CERTAINTY_QUERY = Annotated[
    MentionCertainty, Query(description="Which mention certainty tiers to count.")
]
_POPULATION_QUERY = Annotated[
    DeityPopulation,
    Query(
        description="`deities` (default) refuses the 30 non-divine devata-slot ascriptions; "
        "`all_ascriptions` serves them with their structure and a not-a-deity caveat.",
    ),
]


@router.get(
    "/insights/devatas/{devata_id}/by-book",
    summary="One deity's distribution across the books of every corpus (aggregate)",
    description=(
        "**Cost class: AGGREGATE.** Walks the containment tree and is exempt from the "
        "median latency target.\n\n"
        "Closes `VIZ_BLOCKER_02`. A deity x mandala heatmap could not be served: "
        "`named_by_veda` is per-*Veda* only, and building the breakdown client-side from "
        "`/devatas/{id}/passages` would hit the 200-row page cap and truncate without "
        "saying so.\n\n"
        "**Every book is returned, including the ones with no mention.** A book the deity "
        "is absent from carries `MEASURED_ZERO` and a note, because a query that returns "
        "only its positive rows lets a reader infer a zero nobody measured.\n\n"
        "Each row carries the book's own mantra total and a per-1,000 figure. Books differ "
        "in size by more than an order of magnitude, and a heatmap read on raw counts puts "
        "every deity in the largest book."
    ),
    response_model=DevataByBookResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_by_book(
    repository: RepositoryDep,
    devata_id: _DEVATA_PATH,
    certainty: _CERTAINTY_QUERY = MentionCertainty.DEFAULT,
    population: _POPULATION_QUERY = DeityPopulation.DEITIES,
) -> DevataByBookResponse:
    return InsightService(repository).devata_by_book(
        devata_id=devata_id,
        tiers=sorted(_TIERS_BY_CERTAINTY[certainty]),
        population=population,
    )


@router.get(
    "/insights/devatas/{devata_id}/by-metre",
    summary="One deity against the metre layer, with the corpora it misses typed (aggregate)",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "Closes `VIZ_BLOCKER_03`, which was deferred on the grounds that the metre layer "
        "reaches only two corpora so the matrix would be two thirds hatched -- honest, but "
        "thin. Thin and honest is what is served: the corpora the metre layer does not "
        "reach are **returned** as rows typed `NOT_BUILT`, never omitted. A matrix with two "
        "corpora silently missing is read as a matrix of two corpora, and the Samaveda's "
        "verses are metrical whatever this graph knows about them.\n\n"
        "The layer's reach is measured on each request rather than listed, so a metre layer "
        "that grows shrinks the hatched rows without anyone editing a constant."
    ),
    response_model=DevataByMetreResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_by_metre(
    repository: RepositoryDep,
    devata_id: _DEVATA_PATH,
    certainty: _CERTAINTY_QUERY = MentionCertainty.DEFAULT,
    population: _POPULATION_QUERY = DeityPopulation.DEITIES,
) -> DevataByMetreResponse:
    return InsightService(repository).devata_by_metre(
        devata_id=devata_id,
        tiers=sorted(_TIERS_BY_CERTAINTY[certainty]),
        population=population,
    )


@router.get(
    "/insights/devatas/{devata_id}/dispersion",
    summary="Every position at which a deity is attested, unbounded by the page cap",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "Closes `VIZ_BLOCKER_01`. An Invocation Landscape for a major deity needs every "
        "attesting position, and `/devatas/{id}/passages` is capped at 200 rows a page -- "
        "Indra's 2,305 Rigvedic verses were eighteen round trips, and a caller who stopped "
        "early got a landscape that looked sparse rather than truncated.\n\n"
        "Returns **integer positions only**, never passage payloads, so the response stays "
        "small whatever the deity's size. A position is the verse's rank in its corpus's "
        "canonical order: reading order, which is not order of composition.\n\n"
        "Every corpus is present. An empty `positions` array is `MEASURED_ZERO` with a "
        "note, so it is distinguishable from an absent layer."
    ),
    response_model=DevataDispersionResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_dispersion(
    repository: RepositoryDep,
    devata_id: _DEVATA_PATH,
    certainty: _CERTAINTY_QUERY = MentionCertainty.DEFAULT,
    population: _POPULATION_QUERY = DeityPopulation.DEITIES,
) -> DevataDispersionResponse:
    return InsightService(repository).devata_dispersion(
        devata_id=devata_id,
        tiers=sorted(_TIERS_BY_CERTAINTY[certainty]),
        population=population,
    )


@router.get(
    "/insights/devatas/{devata_id}",
    summary="One deity's reach, by naming and by ascription",
    description=(
        "**Cost class: POINT_READ.**\n\n"
        "Naming and ascription are returned as separate figures with separate scopes and are "
        "never summed. Naming spans all four corpora; the traditional deity ascription exists "
        "for the Rigveda only, so a zero for another corpus is a missing apparatus and not an "
        "absent deity. Per-1,000-mantra figures accompany the raw counts because the corpora "
        "differ in size by a factor of nearly six.\n\n"
        "Mention totals default to CERTAIN plus PROBABLE. `certainty=strict` is offered and "
        "warned about: filtering to CERTAIN alone returns no non-Rigvedic mentions for several "
        "major deities, so the cautious caller gets the worse answer.\n\n"
        "**The default population refuses a non-deity.** The traditional devata slot holds 22 "
        "human patrons, 7 praise-of-a-gift labels and one dog alongside the gods, and under "
        "`population=deities` those 30 are a 404 here exactly as they are on `/devatas/{id}`. "
        "Ask with `population=all_ascriptions` to read one deliberately: the ascription figures "
        "are real, and the response then carries `is_resolved_deity: false`, the subject's "
        "`structure`, and a THIS SUBJECT IS NOT A DEITY caveat."
    ),
    response_model=DevataInsightResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_insight(
    repository: RepositoryDep,
    devata_id: Annotated[
        str,
        Path(
            min_length=3,
            max_length=200,
            description="Product id of the deity, e.g. VG:DEVATA:INDRAH.",
        ),
    ],
    certainty: Annotated[
        MentionCertainty,
        Query(description="Which mention certainty tiers to count."),
    ] = MentionCertainty.DEFAULT,
    population: Annotated[
        DeityPopulation,
        Query(
            description="`deities` (default) refuses the 30 non-divine devata-slot "
            "ascriptions; `all_ascriptions` serves them with their structure and a "
            "not-a-deity caveat.",
        ),
    ] = DeityPopulation.DEITIES,
) -> DevataInsightResponse:
    tiers = sorted(_TIERS_BY_CERTAINTY[certainty])
    return InsightService(repository).devata_insight(
        devata_id=devata_id, tiers=tiers, population=population
    )


@router.get(
    "/insights/material-culture",
    summary="Material culture by corpus (aggregate)",
    description=(
        "**Cost class: AGGREGATE.** One grouped mention scan per requested category.\n\n"
        "Crops, animals, metals, rivers and tribes, folded to one row per entity with raw and "
        "per-1,000-mantra counts side by side. A corpus with no figure carries `null` and not "
        "`0`: the mention layer reaches all four corpora, so a missing corpus means no "
        "registered alias matched there, and alias recall is measured to be partial. Every "
        "row states its own evidence status for the same reason."
    ),
    response_model=MaterialCultureResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def material_culture(
    repository: RepositoryDep,
    category: Annotated[
        str,
        Query(description=f"One of: {', '.join(MATERIAL_CATEGORIES)}."),
    ] = "all",
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> MaterialCultureResponse:
    return InsightService(repository).material_culture(
        category=category, limit=limit, offset=offset
    )


@router.get(
    "/insights/rituals",
    summary="The ritual layer and its recurring implements (aggregate, PARTIAL)",
    description=(
        "**Cost class: AGGREGATE.** **`data_status` is always `PARTIAL`.**\n\n"
        'This is the honest answer to "which ritual objects recur most". A ritual implement '
        "is an object a modelled rite is curated to use, so chariots and thunderbolts are "
        "excluded by construction rather than by a blocklist -- an earlier version of this "
        "ranking returned exactly those two as the corpus's foremost ritual objects.\n\n"
        "The response carries the figures that bound it: how many rites are modelled, how many "
        "procedure edges exist across all of them, and how many curated implements the mention "
        "layer reaches at all. `not_covered` is never empty, because an empty list would "
        "assert that the modelled rites are a taxonomy of Vedic ritual."
    ),
    response_model=RitualsInsightResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def rituals(
    repository: RepositoryDep,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> RitualsInsightResponse:
    return InsightService(repository).rituals(limit=limit, offset=offset)


@router.get(
    "/insights/atharvaveda/concerns",
    summary="Human concerns, afflictions and apotropaic material (aggregate)",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "What the corpus is about in human terms: concerns, afflictions, the things it asks to "
        "be protected from, and the social rites. Afflictions are separated from threats and "
        "causes by `condition_kind` on every row -- an earlier version of this answer ranked "
        "demons, sorcery and worms as diseases.\n\n"
        "All four corpora are reported deliberately, even though the Atharvaveda leads every "
        "row. A reader shown the Atharvavedic column alone cannot tell whether that is "
        "specialisation or the only column anyone measured. The three concern predicates carry "
        "different evidence tiers and are returned side by side; their rows must not be "
        "summed, since a target can appear under two of them from the same mention."
    ),
    response_model=AtharvavedaConcernsResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def atharvaveda_concerns(
    repository: RepositoryDep,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> AtharvavedaConcernsResponse:
    return InsightService(repository).atharvaveda_concerns(limit=limit, offset=offset)


@router.get(
    "/insights/formula-diffusion",
    summary="How shared wording spreads across the four Samhitas (aggregate)",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "The formula-family span census in full, the widest-spread families, and the measured "
        "Samavedic reuse witnesses. The census is returned whole rather than filtered to the "
        "four-corpus families, because the single-corpus families are the baseline the rest "
        "should be read against.\n\n"
        "A family is a shared wording identified by normalised string match, so its span "
        "measures diction rather than a demonstrated line of transmission. Directed reuse "
        "edges exist for one corpus pair only; see `/insights/cross-veda` for the matrix that "
        "types what that does and does not mean."
    ),
    response_model=FormulaDiffusionResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def formula_diffusion(
    repository: RepositoryDep,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> FormulaDiffusionResponse:
    return InsightService(repository).formula_diffusion(limit=limit, offset=offset)


@router.get(
    "/insights/civilization",
    summary="Data, derived statistics and interpretation, kept apart (census)",
    description=(
        "**Cost class: CENSUS.** The data section groups the entire mention layer by label, so "
        "its cost is proportional to that layer and no latency target applies.\n\n"
        "Three sections, three kinds of thing, and they are not three confidence levels of one "
        "assertion. `DATA` is what the corpus is measured to name. `DERIVED_METRIC` is what "
        "this project computed over that, each metric carrying its own method and scope note. "
        "`INTERPRETIVE_CLAIM` is what a model read into it: permanently CANDIDATE, each claim "
        "carrying the falsifier that would refute it, and two of them contradicting each other "
        "on purpose.\n\n"
        "The sections are separately typed and separately statused, and a section will not "
        "construct holding a row of another kind. Do not merge them into one ranked feed."
    ),
    response_model=CivilizationResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def civilization(
    repository: RepositoryDep,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> CivilizationResponse:
    return InsightService(repository).civilization(limit=limit, offset=offset)


@router.get(
    "/insights/metals",
    summary="The complete metal-by-corpus grid (aggregate)",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "Every registered metal against every corpus, with no cell omitted. A cell that "
        "matched nothing carries `matched_mantras: null` and "
        "`evidence_status: NO_LEXICAL_MATCH`, never `0`: the alias registry admits attested "
        "whole-word inflections only, so a miss is a fact about the matcher and a lower bound "
        "of zero.\n\n"
        "One cell is knowingly wrong and says so **in the cell**. The Yajurveda names *ayas* "
        "at a verse this endpoint locates from the graph, but the elided Devanagari folds to "
        "the token of the relative pronoun, so no alias can be registered without landing "
        "wrong-sense mentions. That cell carries the verse's citation in `source_witness`, so "
        "a client rendering only rows still cannot conclude that the Yajurveda has no metal.\n\n"
        "Each row also reports its raw and its normalised ordering, because normalising by "
        "corpus size reorders them: gold is Rigveda-first on raw counts and "
        "Atharvaveda-first per 1,000 mantras."
    ),
    response_model=MetalsInsightResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def metals(repository: RepositoryDep) -> MetalsInsightResponse:
    return InsightService(repository).metals()


@router.get(
    "/insights/capabilities",
    summary="What this product cannot answer, and why (aggregate)",
    description=(
        "**Cost class: AGGREGATE.**\n\n"
        "The boundary as data, so a frontend can enumerate it instead of discovering it by "
        "getting an empty list back from a reasonable question. Each entry carries the "
        "benchmark verdict, the reason stated in terms of the graph rather than the corpus, "
        "the false conclusion the refusal exists to prevent, and the measurements -- read live "
        "-- that establish the limit.\n\n"
        "`NOT_ANSWERABLE` is not a sub-grade of partial. It says the dimension the question "
        "asks about is absent from the graph, which is a statement about this build and never "
        "about the Vedas. A lookup for a question with no recorded limit is a 404 rather than "
        "an empty list, because an empty capability list would assert that the product has no "
        "limits."
    ),
    response_model=CapabilitiesResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def capabilities(
    repository: RepositoryDep,
    question: Annotated[
        int | None,
        Query(
            ge=1,
            le=100,
            description="Filter to one benchmark question number, e.g. 23. Absent returns "
            "every recorded limit.",
        ),
    ] = None,
) -> CapabilitiesResponse:
    return InsightService(repository).capabilities(question=question)
