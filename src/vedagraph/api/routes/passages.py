"""Canonical passage lookup, structural navigation and the reader payload.

**Every route resolves its key the same way.** ``VG:RV:SAK:M01:S001:V001`` is accepted as
written -- a colon is legal inside a path segment -- and so are the citation forms
``RV 1.1.1``, ``RV.1.1.1``, ``rv_1.1.1`` and the ``urn:vedagraph:...`` form. Resolution
happens once, in :meth:`PassageService.resolve`, so a client that holds a citation can use
every endpoint here without first converting it, and an unknown reference produces a 404
carrying an example that works rather than only the news that theirs did not.

**A container key is a valid key.** A Sukta, a Mandala and a Samavedic Dasati are
``Passage`` nodes, and asking for one returns its record and navigates from it. What a
container does not have is text of its own: the corpus attaches text to the 20,210 mantras
and not to the 2,327 containers above them, so a container's ``text`` block reports
``NOT_BUILT`` with a caveat pointing at its children rather than an empty list a frontend
would render as a blank verse.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.common import Paginated
from vedagraph.api.models.entity import MentionCertainty
from vedagraph.api.models.passage import (
    NavigationResult,
    ParallelFilter,
    ParallelView,
    PassageDetail,
    ReaderPayload,
)
from vedagraph.api.services.passage_service import PassageService

router = APIRouter(tags=["Passages"], responses=COMMON_ERROR_RESPONSES)

KeyPath = Annotated[
    str,
    Path(
        description=(
            "A canonical key (VG:RV:SAK:M01:S001:V001), a citation (RV 1.1.1, RV.1.1.1, "
            "rv_1.1.1, AV 20.143.9, YV 1.1, SV ARANYA 1.1) or a canonical URN."
        ),
        examples=["VG:RV:SAK:M01:S001:V001", "RV 1.1.1", "VG:SV:KAU:UTTARA:P01:R01:D01:V01"],
    ),
]

LimitQuery = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page.")]
OffsetQuery = Annotated[int, Query(ge=0, description="Items to skip.")]

#: Opt-in to ambiguous deity mentions. A boolean rather than the three-valued
#: ``MentionCertainty`` because a reading page has one real question -- show the uncertain
#: matches or not -- and ``strict`` on a single passage would drop DEITY_PROBABLE rows that
#: score 0.9818 against the gold set, which is a worse answer for a careful caller than the
#: default. The analytic surfaces that need all three modes are the deity endpoints.
IncludeAmbiguousQuery = Annotated[
    bool,
    Query(
        description=(
            "Include deity mentions the graph grades DEITY_AMBIGUOUS, where the matched "
            "form is also an ordinary noun. Default false: 6,806 of 17,165 mention edges "
            "are ambiguous and CERTAIN+PROBABLE score 0.9742 against 0.6142 for what is "
            "left in AMBIGUOUS. All three counts are reported either way in "
            "`mentioned_devatas.certainty`."
        )
    ),
]


def _certainty(include_ambiguous: bool) -> MentionCertainty:
    return MentionCertainty.EXPLORATORY if include_ambiguous else MentionCertainty.DEFAULT


@router.get(
    "/passages/{key}",
    summary="One passage, in full",
    description=(
        "A passage's complete record: its three identifiers, its work with both names, its "
        "position in its Veda's own structure, every Sanskrit witness held for it, aligned "
        "translations, the seer, deity and metre attributed to it, concepts, formulas, "
        "interpretive relations, the agentive assertions extracted from it, parallel counts "
        "and provenance.\n\n"
        "Every collection in the payload carries a `data_status` and, where its emptiness "
        "could be misread, a caveat. An empty `devatas` on a Yajurvedic verse is `NOT_BUILT` "
        "with the Anukramani scope caveat attached -- it does not mean the verse addresses "
        "no deity. An empty `translations` on a Samavedic verse is `NOT_BUILT` because zero "
        "of that corpus's 1,844 verses carry one.\n\n"
        "**Deity mentions are graded and ambiguous ones are withheld by default.** "
        "`devatas` is the Anukramani's ascription, which reaches the Rigveda only. "
        "`mentioned_devatas` is which deities are *named* in the verse, reaches all four "
        "corpora, and is matched on the surface form -- which matters because `soma` is the "
        "god, the plant and the pressed drink. Every row carries `referent_certainty` and "
        "`is_ambiguous`, and the 6,806 edges graded `DEITY_AMBIGUOUS` are excluded unless "
        "you pass `include_ambiguous=true`. All three tier counts are always in "
        "`mentioned_devatas.certainty`, so you can see what the default withheld. Where "
        "every mention in a passage is ambiguous -- 2,997 passages are in that position -- "
        "the list is empty with `INSUFFICIENT_EVIDENCE` and a caveat, which is not the same "
        "as the verse naming no deity.\n\n"
        "`attribution_precision` is on every attribution row and is never blended: "
        "`CONTAINER_INHERITED` is a containing hymn's label projected onto this verse, and "
        "15,177 of the corpus's 17,889 seer attributions are that rather than a statement "
        "the verse makes.\n\n"
        "No Neo4j identifier appears anywhere in the response."
    ),
    response_model=PassageDetail,
    responses=COMMON_ERROR_RESPONSES,
)
def get_passage(
    repository: RepositoryDep,
    key: KeyPath,
    include_ambiguous: IncludeAmbiguousQuery = False,
) -> PassageDetail:
    service = PassageService(repository)
    return service.detail(service.resolve(key), certainty=_certainty(include_ambiguous))


@router.get(
    "/passages/{key}/parent",
    summary="The containing passage",
    description=(
        "The passage that contains this one, with the native name of the level it sits at: "
        "a Rigvedic mantra's parent is its Sukta, an Atharvavedic verse's is its Sukta, a "
        "Yajurvedic verse's is its Adhyaya, and a Samavedic verse's is its Dasati.\n\n"
        "A top-level container has no parent passage and returns an empty result with a "
        "caveat naming the work as its parent, rather than a 404: having no parent is a "
        "correct answer for the 74 passages at the top of the four works."
    ),
    response_model=NavigationResult,
    responses=COMMON_ERROR_RESPONSES,
)
def get_parent(repository: RepositoryDep, key: KeyPath) -> NavigationResult:
    service = PassageService(repository)
    return service.parent(service.resolve(key))


@router.get(
    "/passages/{key}/children",
    summary="The passages inside this one",
    description=(
        "The passages this one directly contains, in stored sequence, with the native name "
        "of their level. One traversal serves all four Vedas: it returns the Suktas of a "
        "Mandala, the Suktas of a Kanda, the verses of an Adhyaya, or the verses of a "
        "Samavedic Dasati.\n\n"
        "A mantra contains nothing and returns an empty result with a caveat saying it is "
        "the deepest level of its work, so the empty list cannot be read as a container "
        "that lost its contents."
    ),
    response_model=NavigationResult,
    responses=COMMON_ERROR_RESPONSES,
)
def get_children(
    repository: RepositoryDep,
    key: KeyPath,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> NavigationResult:
    service = PassageService(repository)
    return service.children(service.resolve(key), limit=limit, offset=offset)


@router.get(
    "/passages/{key}/siblings",
    summary="The other passages in the same container",
    description=(
        "The passages sharing this one's container, in stored sequence. The anchor passage "
        "is always excluded, so an only child returns an empty result with a caveat saying "
        "so.\n\n"
        "A top-level container's siblings are the work's other top-level containers, and "
        "the response points at `GET /api/v1/works/{work_id}/root` rather than guessing."
    ),
    response_model=NavigationResult,
    responses=COMMON_ERROR_RESPONSES,
)
def get_siblings(
    repository: RepositoryDep,
    key: KeyPath,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> NavigationResult:
    service = PassageService(repository)
    return service.siblings(service.resolve(key), limit=limit, offset=offset)


@router.get(
    "/passages/{key}/reader",
    summary="Everything needed to render one mantra",
    description=(
        "One compact payload for a reader view: the Sanskrit witness to render, every other "
        "witness held, aligned translations, breadcrumbs in the tradition's own level names, "
        "the previous and next passage in reading order, seer, deity, metre, the major "
        "concepts, audio availability, parallel counts by kind, and a graph-neighbour "
        "count. A frontend renders a mantra from this one call.\n\n"
        "`previous` and `next` cross container boundaries: RV 1.1.9 is followed by RV 1.2.1 "
        "and RV 1.191.16 by RV 2.1.1. The Samavedic collections are traversed in their "
        "stored traditional order, so the last Chanda verse is followed by the first "
        "Aranyaka verse and not by a Mahanamnya one. At the first and last passage of a "
        "work the neighbour is null and `neighbour_note` says which end you are at.\n\n"
        "`mentioned_devatas` carries the graded deity-mention set with ambiguous rows "
        "withheld by default; pass `include_ambiguous=true` to see them. It is on the "
        "reader beside `devatas` because the ascription layer is Rigveda-only, so for a "
        "Samavedic, Yajurvedic or Atharvavedic verse this is the only deity signal a "
        "reading page can show.\n\n"
        "`audio.status` is always `NOT_BUILT`. There is no audio node, relationship or "
        "property anywhere in this graph, so this is an unbuilt layer and not a claim that "
        "the passage is unrecited. Do not render a disabled play control from a null."
    ),
    response_model=ReaderPayload,
    responses=COMMON_ERROR_RESPONSES,
)
def get_reader(
    repository: RepositoryDep,
    key: KeyPath,
    include_ambiguous: IncludeAmbiguousQuery = False,
) -> ReaderPayload:
    service = PassageService(repository)
    return service.reader(service.resolve(key), certainty=_certainty(include_ambiguous))


@router.get(
    "/passages/{key}/parallels",
    summary="Related passages, traversed in both directions",
    description=(
        "Passages related to this one by shared text, with the kind of relation stated on "
        "every row before any similarity figure.\n\n"
        "**Traversed undirected.** Parallelism is symmetric and this graph stores it as a "
        "directed edge: all 1,684 `REUSES_TEXT_FROM` edges point Samaveda-to-Rigveda, and "
        "1,421 Rigvedic passages have reuse edges only inbound. Each row's "
        "`stored_direction` says which way the stored edge ran.\n\n"
        "**`filter=vocabulary` is not reuse.** `SHARES_ENTITY_VOCABULARY_WITH` means two "
        "passages name some of the same registry concepts and says nothing about shared "
        "wording. Those rows carry `is_textual_parallelism: false` and are excluded from "
        "`textual_total`.\n\n"
        "**`filter=formula` asks a different question.** It is not a stored edge between "
        "passages: it finds passages using the same `Formula` through `USES_FORMULA`, and "
        "must be requested on its own. Use it when the whole-verse matchers return nothing, "
        "because shared wording is common where whole-verse similarity is not.\n\n"
        "`same_veda` and `cross_veda` are derived from the two passages' corpora and not "
        "from the stored `veda_pair`, which is null on all 325 same-Veda edges."
    ),
    response_model=Paginated[ParallelView],
    responses=COMMON_ERROR_RESPONSES,
)
def get_parallels(
    repository: RepositoryDep,
    key: KeyPath,
    filter: Annotated[
        list[ParallelFilter] | None,
        Query(
            description=(
                "Repeatable. Omit for all four textual predicates plus entity-vocabulary "
                "overlap. `formula` must be requested alone: it is formula-mediated rather "
                "than a stored passage-to-passage edge."
            )
        ),
    ] = None,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = 0,
) -> Paginated[ParallelView]:
    service = PassageService(repository)
    return service.parallels(
        service.resolve(key),
        filters=tuple(filter or ()),
        limit=limit,
        offset=offset,
    )
