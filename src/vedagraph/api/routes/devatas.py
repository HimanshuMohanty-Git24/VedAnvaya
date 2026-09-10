"""The deity surface, under the resolved-population and ambiguity contracts.

The two contracts are declared in the OpenAPI text of every route here, because the client
that calls the obvious endpoint never reads the schema description of a nested model. Both
are enforced in :mod:`vedagraph.api.services.entity_service` and
:mod:`vedagraph.api.services.deity_population`; nothing in this module decides anything.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.common import Paginated
from vedagraph.api.models.entity import (
    DeityPopulation,
    DevataNetwork,
    DevataPassagePage,
    DevataProfile,
    DevataSummary,
    MentionBasis,
    MentionCertainty,
)
from vedagraph.api.services.entity_service import EntityService

router = APIRouter(tags=["Devatas"], responses=COMMON_ERROR_RESPONSES)

_POPULATION_NOTE = """
**The population contract.** The Anukramani names a *devata* for every Rigvedic hymn and
that slot is not a theological claim: 30 of the 214 `:Devata` nodes are not gods -- 22
human patrons and seers (Vasistha, Visvamitra, Brbu the carpenter), 7 danastuti labels
naming the gift rather than a recipient ("praise of the gift of Sudas son of Pijavana"),
and one dog. `population=deities` (the default) excludes all 30.
`population=all_ascriptions` returns the slot as it stands, with every row's `structure`
and `is_deity` stated, and `is_deity` false where it is false.

The contract is applied by ONE gate that every deity route passes through, including
`/devatas/{id}/passages` and `/devatas/{id}/network`. Under the default population all
three refuse a non-deity identically, with the same 404 body.
"""

_CERTAINTY_NOTE = """
**The ambiguity contract.** Vedic Sanskrit has one word for the god Agni and for fire, and
one for Soma the god, the plant and the drink. Every mention edge is graded, and
user-facing totals include `DEITY_CERTAIN` + `DEITY_PROBABLE` and exclude
`DEITY_AMBIGUOUS` unless `include_ambiguous=true`. All three counts are reported whatever
you ask for. `certainty=strict` narrows to `DEITY_CERTAIN` alone and is measured to be a
*Rigvedic* grade rather than an accuracy grade -- it returns zero non-Rigvedic mentions for
Agni, Soma, Surya, Mitra, Savitr, Usas, Vayu, Apah and Prthivi -- so a corpus emptied by
that filter returns `count: null` with `INSUFFICIENT_EVIDENCE` and a caveat, never `0`.
"""

PopulationParam = Annotated[
    DeityPopulation,
    Query(description="Which slice of the Anukramani's devata slot to read."),
]
CertaintyParam = Annotated[
    MentionCertainty,
    Query(
        description="Which mention tiers to count. `default` is CERTAIN + PROBABLE; "
        "`strict` is CERTAIN alone and carries a mandatory caveat; `exploratory` is all "
        "three and is for candidate generation, not for fact.",
    ),
]
AmbiguousParam = Annotated[
    bool,
    Query(description="Add DEITY_AMBIGUOUS to the counted tiers. Off by default."),
]
DevataIdParam = Annotated[
    str,
    Path(description="Stable deity id, e.g. VG:DEVATA:INDRAH.", min_length=1, max_length=200),
]


@router.get(
    "/devatas",
    summary="List deities",
    description="The resolved pantheon, ordered by total mentions.\n"
    + _POPULATION_NOTE
    + _CERTAINTY_NOTE,
    response_model=Paginated[DevataSummary],
    responses=COMMON_ERROR_RESPONSES,
)
def list_devatas_endpoint(
    repository: RepositoryDep,
    population: PopulationParam = DeityPopulation.DEITIES,
    certainty: CertaintyParam = MentionCertainty.DEFAULT,
    include_ambiguous: AmbiguousParam = False,
    structure: Annotated[
        str | None,
        Query(
            description="Filter by structure: INDIVIDUAL (72), ABSTRACT (41), PAIR (38), "
            "GROUP (33), and with population=all_ascriptions also HUMAN (22), "
            "PATRON_PRAISE (7) and UNSPECIFIED (1). A value outside that space is a 400 "
            "naming it, never a 200 with an empty page.",
        ),
    ] = None,
    axis: Annotated[
        str | None,
        Query(
            description="Filter by one of the 22 functional axes, e.g. WARRIOR, "
            "COSMIC_SOVEREIGN, HEALER. An unknown axis is a 400 listing them.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginated[DevataSummary]:
    return EntityService(repository).list_devatas(
        population=population,
        certainty=certainty,
        include_ambiguous=include_ambiguous,
        structure=structure,
        axis=axis,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/devatas/{devata_id}",
    summary="Deity profile",
    description="Identity, labels, aliases, structure, functional axes, epithets, mention "
    "counts by Veda with all three certainty tiers, strict versus inherited attribution, "
    "top seers, metres, concepts, actions, requested actions, objects and formulas, "
    "co-deities, and interpretive claims.\n\n"
    "**Read `dimension_status` before reading any empty list here.** It names every "
    "dimension whose emptiness is a missing layer or unestablished evidence rather than an "
    "absence in the corpus. It is empty for most deities and non-empty exactly where the "
    "build recorded a dimension it could not establish, so its presence is the signal -- "
    "no count is quoted here, because a figure describing the graph invites a client to "
    "skip the field on the deities where it carries the warning.\n\n"
    "**Mention and attribution totals are counted from the edges**, not read off "
    "materialised profile properties, which exist on only 30 of the 214 nodes. This is "
    "why `/devatas/{id}` and `/insights/devatas/{id}` agree.\n"
    + _POPULATION_NOTE
    + _CERTAINTY_NOTE,
    response_model=DevataProfile,
    responses=COMMON_ERROR_RESPONSES,
)
def get_devata_endpoint(
    repository: RepositoryDep,
    devata_id: DevataIdParam,
    population: PopulationParam = DeityPopulation.DEITIES,
    certainty: CertaintyParam = MentionCertainty.DEFAULT,
    include_ambiguous: AmbiguousParam = False,
) -> DevataProfile:
    return EntityService(repository).get_devata(
        devata_id,
        population=population,
        certainty=certainty,
        include_ambiguous=include_ambiguous,
    )


@router.get(
    "/devatas/{devata_id}/passages",
    summary="Passages naming or ascribed to a deity",
    description="**`basis` is not a detail.** `basis=mention` walks `MENTIONS_DEVATA` "
    "(17,165 edges over all four corpora) and answers *is this deity named in this "
    "verse?*. `basis=ascription` walks `HAS_DEVATA` (10,558 edges, every one Rigvedic, "
    "8,329 of them a sukta label projected onto its mantras) and answers *does the "
    "Anukramani dedicate this hymn to it?*. Every row states which relation put it there, "
    "and a count from one presented as the other is wrong by construction rather than by "
    "degree. Asking for an ascription in the Samaveda, Yajurveda or Atharvaveda is empty "
    "by construction and the response says so.\n\n"
    "**All three certainty tiers travel with the page.** `certainty` reports CERTAIN, "
    "PROBABLE and AMBIGUOUS over *every* one of this deity's mention edges, not just the "
    "ones on the page, so a caller reading Soma's 421 default-tier passages can see the "
    "1,091 ambiguous mentions the filter removed.\n\n"
    "**`population` applies here too**, through the same gate as `/devatas/{id}`: under "
    "the default a non-deity ascription is a 404, and under `all_ascriptions` the page "
    "states its subject's `structure` and carries a caveat saying it is not a god.\n"
    + _CERTAINTY_NOTE,
    response_model=DevataPassagePage,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_passages_endpoint(
    repository: RepositoryDep,
    devata_id: DevataIdParam,
    basis: Annotated[
        MentionBasis,
        Query(description="Which deity-passage relation to read. They are not summable."),
    ] = MentionBasis.MENTION,
    certainty: CertaintyParam = MentionCertainty.DEFAULT,
    include_ambiguous: AmbiguousParam = False,
    veda: Annotated[str | None, Query(description="RV, AV, YV or SV.")] = None,
    population: PopulationParam = DeityPopulation.DEITIES,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DevataPassagePage:
    return EntityService(repository).devata_passages(
        devata_id,
        basis=basis,
        certainty=certainty,
        include_ambiguous=include_ambiguous,
        veda=veda,
        population=population,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/devatas/{devata_id}/network",
    summary="Deity neighbourhood",
    description="Measured co-occurrence with lift, composition and membership, functional "
    "axes, associated domain entities, and the deities reached through seers in common.\n\n"
    "**Every deity-valued edge passes the population contract.** Unfiltered, the "
    "seer-bridge for Indra returns 22 non-deities including Vasukra, Brbu the carpenter, "
    "the dog and four praise-of-a-gift labels; the bridge also runs only through actual "
    "seers, because 113 of the 729 `:Rishi` nodes are the being a hymn addresses rather "
    "than the one who saw it.\n\n"
    "**The subject is typed as well as its neighbours.** Under "
    "`population=all_ascriptions` the response states the subject's `subject_structure` "
    "and `subject_is_deity` and carries the THIS SUBJECT IS NOT A DEITY caveat when it is "
    "one of the 30 -- the same disclosure `/devatas/{id}` and `/devatas/{id}/passages` "
    "make, from the same helper.\n" + _POPULATION_NOTE,
    response_model=DevataNetwork,
    responses=COMMON_ERROR_RESPONSES,
)
def devata_network_endpoint(
    repository: RepositoryDep,
    devata_id: DevataIdParam,
    population: PopulationParam = DeityPopulation.DEITIES,
) -> DevataNetwork:
    return EntityService(repository).devata_network(devata_id, population=population)
