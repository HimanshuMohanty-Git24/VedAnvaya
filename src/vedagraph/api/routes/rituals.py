"""The modelled rites. Not a taxonomy of Vedic ritual.

Both routes carry `coverage_statement` in the payload and not only in this documentation,
because a list reads as a complete list unless the rows say otherwise — and because the
figures inside that statement are measured per request rather than typed here, where they
would go stale silently. They did: this module said "eight modelled rites" for a whole
import after the inventory became 103.

Two step layers are returned separately. `steps` is the Samhita's own numbering and is
empty for every rite but one; `procedure` is what a sutra prints. Each gets a
`dimension_status` row, so an empty array is a status and never a claim of absence.
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
**An inventory of rites, not a taxonomy.** The `Ritual` class holds fewer nodes than the
corpus names, so a rank in this list is a rank within the inventory and says nothing about
Vedic ritual as a whole. The exact figures are measured per request and returned in
`coverage_statement` — they are not written into this description, because a number typed
into prose is the one nothing checks.

**Two step layers, and they are not interchangeable.** `steps` is what the Samhita text
itself numbers: 3 such edges exist in the whole graph, all on the soma pressing, whose
morning, midday and third libations the hymn numbers in its own words. `procedure` is what
a Srautasutra or Grhyasutra prints, which is a different claim about a different source —
and most of those sequences state a step's position without printing the run it falls in,
so a `procedure` list is a set of located steps rather than a complete procedure. Every
row says which, and each layer gets its own `dimension_status` entry, so an empty array is
never left to be read as an absence of ritual structure.

Apparatus edges are all TIER_D curation, and a rite's "purpose" is a curator's statement
rather than a purpose clause quoted from a passage.
"""


@router.get(
    "/rituals",
    summary="List the modelled rites",
    description="Every modelled rite, ordered by lexical mention count." + _COVERAGE_NOTE,
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
