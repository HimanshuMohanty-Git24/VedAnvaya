"""The eight modelled rites. Not a taxonomy of Vedic ritual.

Both routes carry `coverage_statement` in the payload and not only in this documentation,
because a list with eight rows in it reads as a complete list unless the rows say
otherwise. The step list is empty for seven of the eight rites and that emptiness is a
status, never an array.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.common import Paginated
from vedagraph.api.models.entity import DeityPopulation, RitualProfile, RitualSummary
from vedagraph.api.services.entity_service import EntityService

router = APIRouter(tags=["Rituals"], responses=COMMON_ERROR_RESPONSES)

_COVERAGE_NOTE = """
**Eight modelled rites, not a taxonomy.** The `Ritual` class holds 8 nodes against a
corpus that names considerably more, so a rank in this list is a rank within 8 and says
nothing about Vedic ritual as a whole. Elaborate procedure is Brahmana and Sutra material
and was deliberately not imported into Samhita passages: **3** `HAS_STEP` edges exist in
the entire graph, all three on the soma pressing, whose morning, midday and third
libations the text itself numbers. A rite with no steps therefore returns a
`dimension_status` row saying NOT_BUILT rather than an empty array, and all 25 apparatus
edges are TIER_D curation whose "purpose" is a curator's statement rather than a purpose
clause quoted from a passage.
"""


@router.get(
    "/rituals",
    summary="List the modelled rites",
    description="All eight, ordered by lexical mention count." + _COVERAGE_NOTE,
    response_model=Paginated[RitualSummary],
    responses=COMMON_ERROR_RESPONSES,
)
def list_rituals_endpoint(
    repository: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginated[RitualSummary]:
    return EntityService(repository).list_rituals(limit=limit, offset=offset)


@router.get(
    "/rituals/{ritual_id}",
    summary="Ritual profile",
    description="One rite: recorded steps where the text states an order, officiants, "
    "offerings, substances, objects, invoked deities, stated purposes, narrower rites and "
    "the passages said to describe it.\n\n"
    "The invoked deities pass the deity population contract, so a rite cannot list a human "
    "patron among the gods it invokes." + _COVERAGE_NOTE,
    response_model=RitualProfile,
    responses=COMMON_ERROR_RESPONSES,
)
def get_ritual_endpoint(
    repository: RepositoryDep,
    ritual_id: Annotated[
        str,
        Path(
            description="Stable rite id, e.g. VG:CONCEPT:SOMA-PRESSING.",
            min_length=1,
            max_length=200,
        ),
    ],
    population: Annotated[
        DeityPopulation,
        Query(description="Which slice of the Anukramani's devata slot the invoked deities use."),
    ] = DeityPopulation.DEITIES,
) -> RitualProfile:
    return EntityService(repository).get_ritual(ritual_id, population=population)
