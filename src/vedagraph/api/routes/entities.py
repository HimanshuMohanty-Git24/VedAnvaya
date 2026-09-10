"""One generic surface over every non-deity knowledge type.

Thirty-one types through one pair of routes, because thirty-one pairs of routes is how a
contract comes to be applied to thirty of them. The type registry, the identity-property
table and every caveat live in :mod:`vedagraph.api.services.entity_service`.

Deities are deliberately NOT served here. The generic surface has no deity population
filter, and a deity list without one returns 22 human patrons, 7 praise-of-a-gift labels
and a dog; `/api/v1/entities/devata` is a 400 pointing at `/api/v1/devatas`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.common import Paginated
from vedagraph.api.models.entity import ConditionKindFilter, EntityListRow, EntityProfile
from vedagraph.api.models.search import EntityTypeInventory
from vedagraph.api.services.entity_service import EntityService

router = APIRouter(tags=["Entities"], responses=COMMON_ERROR_RESPONSES)

TypeParam = Annotated[
    str,
    Path(
        description="Type slug, e.g. `rishi`, `condition`, `plant`, `ritual_role`. "
        "GET /api/v1/entities lists them all with counts. An unknown slug is a 400 naming "
        "the available ones, never an empty 200.",
        min_length=1,
        max_length=64,
    ),
]
IdParam = Annotated[
    str,
    Path(
        description="Stable product id, e.g. VG:RISHI:VASISTHAH or VG:CONCEPT:TAKMAN-FEVER.",
        min_length=1,
        max_length=200,
    ),
]


@router.get(
    "/entities",
    summary="Queryable knowledge types",
    description="Every type the generic entity surface serves, with its live node count. "
    "A count here is a node count and not a measure of corpus coverage: a type with 8 "
    "nodes is a curated selection, not an inventory of what the Samhitas name.",
    response_model=EntityTypeInventory,
    responses=COMMON_ERROR_RESPONSES,
)
def list_entity_types_endpoint(repository: RepositoryDep) -> EntityTypeInventory:
    return EntityService(repository).type_inventory()


@router.get(
    "/entities/{entity_type}",
    summary="List entities of one type",
    description="One page of one knowledge type, ordered by measured centrality.\n\n"
    "**`kind` on the condition type defaults to AFFLICTION, and that default is the "
    "point.** Of the 718 lexical mention edges reaching a `Condition`, 314 reach a THREAT "
    "and 88 a PATHOGEN_OR_CAUSE, so an unfiltered disease list ranks demons, sorcery, "
    "curses, worms and poison as diseases. The kind is on every row as well as in the "
    "filter, so a caller who forgets the filter can still see what it got.\n\n"
    "**`rishi` rows carry `is_seer` and `non_seer_kind`.** 113 of the 729 `:Rishi` nodes "
    "are not seers at all but the being a hymn addresses -- 58 deities, 21 abstractions, "
    "13 mythic beings, 11 deity groups, 5 plants or animals, 3 collectives, 2 objects. The "
    "flags are on the row and reflected in `subtitle`, because the list is where a client "
    "picks one and the first row by centrality is Aditi.\n\n"
    "**`passage_count` counts the edges** and is the same figure the detail view reports, "
    "so a row and its own profile cannot disagree. It is null, never 0, where no passage "
    "reaches the object.",
    response_model=Paginated[EntityListRow],
    responses=COMMON_ERROR_RESPONSES,
)
def list_entities_endpoint(
    repository: RepositoryDep,
    entity_type: TypeParam,
    kind: Annotated[
        ConditionKindFilter | None,
        Query(
            description="Condition kind. Defaults to AFFLICTION on the condition type and "
            "is rejected on any other. Use ANY to see all three kinds.",
        ),
    ] = None,
    name: Annotated[
        str | None,
        Query(max_length=200, description="Case-insensitive substring of the display label."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginated[EntityListRow]:
    return EntityService(repository).list_entities(
        entity_type, condition_kind=kind, name=name, limit=limit, offset=offset
    )


@router.get(
    "/entities/{entity_type}/{entity_id}",
    summary="Entity profile",
    description="One knowledge object: labels, aliases, definition, measured centrality, "
    "recall and alias purity where they were measured, per-Veda passage counts, and "
    "immediate neighbours.\n\n"
    "**`centrality.bridging` is null and says NOT_BUILT rather than 0.** The frozen graph "
    "stores prose in that field -- no community structure exists, so bridge centrality is "
    "not computable -- and this response keeps the status out of the number.\n\n"
    "**`seer` is present when the type is `rishi`**, carrying the full seer profile: "
    "`is_seer`, `non_seer_kind`, family, and source-stated versus container-inherited "
    "attribution as separate figures that must never be summed. The Yajurveda's 2,240 seer "
    "edges are every one source-stated and the Atharvaveda's 5,084 are every one "
    "inherited, so a blended total compares a statement of the text against a projection. "
    "The Samaveda carries no seer apparatus at all.",
    response_model=EntityProfile,
    responses=COMMON_ERROR_RESPONSES,
)
def get_entity_endpoint(
    repository: RepositoryDep, entity_type: TypeParam, entity_id: IdParam
) -> EntityProfile:
    return EntityService(repository).get_entity(entity_type, entity_id)
