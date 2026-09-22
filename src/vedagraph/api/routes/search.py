"""Unified search across canonical keys, Sanskrit, translations and entities.

Thin by design: parameter declarations, one service call, no Cypher. The ranking, the
surface coverage and the deity population filter all live in
:mod:`vedagraph.api.services.search_service`, so a second search endpoint added later
cannot rank differently or forget the filter.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep, SettingsDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.search import (
    MATCH_TYPE_ORDER,
    SCORE_SEMANTICS,
    TIE_BREAK_SEMANTICS,
    SearchLanguage,
    SearchResponse,
)
from vedagraph.api.services.search_service import SearchService

router = APIRouter(tags=["Search"], responses=COMMON_ERROR_RESPONSES)

_LADDER = " > ".join(rung.value for rung in MATCH_TYPE_ORDER)

SEARCH_DESCRIPTION = f"""
Search canonical keys, canonical citations, Sanskrit text, the accent-stripped Sanskrit
search surface, English translations, dictionary headwords, entity labels and aliases, and
concept definitions -- in one call, with one ranking.

**Relevance is a fixed ladder, not a model.** Every row carries the `match_type` that
produced it, in this order:

`{_LADDER}`

{SCORE_SEMANTICS}

{TIE_BREAK_SEMANTICS}

**A miss is not absence.** The searchable surfaces do not cover the four corpora evenly:
there is no Samavedic English translation at all, the accent-stripped Sanskrit surface
exists only for the Atharvaveda, and the lemma layer is Rigvedic. Every response returns
`surfaces_searched` and `surface_coverage` so a caller can tell an empty result from an
unreachable corpus. Where the strongest rungs already fill the requested page the text
surfaces are not read, `total` is null, and a caveat says so.

**Deities are population-resolved.** The Anukramani's devata slot holds 22 human patrons,
7 praise-of-a-gift labels and 28 abstractions ruled not to name an addressee, and none of
them is returned typed `DEVATA`.
Searching *Vasistha* will not offer him as a god; a caveat states how many such
ascriptions the query matched and where to read them.
"""


@router.get(
    "/search",
    summary="Unified search",
    description=SEARCH_DESCRIPTION,
    response_model=SearchResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def search_endpoint(
    repository: RepositoryDep,
    settings: SettingsDep,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=200,
            description="A canonical key, a citation, a Sanskrit or English phrase, a "
            "dictionary headword, or an entity name. Passed as a bound parameter and "
            "never as query syntax, so Cypher and Lucene metacharacters are inert.",
        ),
    ],
    type: Annotated[
        str | None,
        Query(
            description="Restrict to one result type, e.g. `devata`, `condition`, "
            "`passage`. An unknown type is a 400 listing the available ones.",
        ),
    ] = None,
    veda: Annotated[
        str | None,
        Query(
            description="RV, AV, YV or SV. Filters PASSAGE rows only: an entity is a "
            "corpus-wide object and is returned unfiltered, with a caveat saying so.",
        ),
    ] = None,
    work: Annotated[
        str | None,
        Query(description="Work id, e.g. VG:WORK:RV:SAK. Filters PASSAGE rows only."),
    ] = None,
    language: Annotated[
        SearchLanguage,
        Query(description="Restrict the ladder to Sanskrit rungs or English rungs."),
    ] = SearchLanguage.ANY,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SearchResponse:
    return SearchService(
        repository,
        lemma_search_enabled=settings.api_deployment_profile != "aura_free",
    ).search(
        q,
        limit=limit,
        offset=offset,
        result_type=type,
        veda=veda,
        work=work,
        language=language,
    )
