"""The four Samhitas, their recensions, scope and exclusions.

Every response from this router carries the scope-honest ``display_label`` beside the
traditional ``work_name``, and the ``scope`` prose verbatim. That is the whole point of the
endpoint: the corpus is four Samhitas in one recension each, and three of the four are
partial in a way a reader cannot guess from the name. The Samavedic label reads *Kauthuma
arcika only (gana corpus NOT included)*; its ``scope`` says THIS IS NOT THE COMPLETE
SAMAVEDA; its ``completeness`` says zero translations are released. All three reach the
client on the list endpoint, not only on the detail one, because a client that renders a
work picker never calls the detail endpoint first.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.common import CaveatView, KnowledgeStatus, Paginated, paginate
from vedagraph.api.models.work import WorkDetail, WorkRoot, WorkSummary
from vedagraph.api.services.passage_service import PassageService, paged_meaning

router = APIRouter(tags=["Works"], responses=COMMON_ERROR_RESPONSES)

WorkIdPath = Annotated[
    str,
    Path(
        description="A work id, e.g. VG:WORK:RV:SAK.",
        examples=["VG:WORK:RV:SAK", "VG:WORK:SV:KAU"],
    ),
]

#: Attached to the list response. It is a caveat and not documentation prose because the
#: client who calls ``GET /works`` to populate a dropdown is exactly the client who will
#: never read the documentation, and "four works" looks like a complete answer.
_SCOPE_CAVEAT = CaveatView(
    text=(
        "These four works are the whole of this corpus: four Samhitas, one recension each. "
        "No Brahmana, Aranyaka or Upanisad is held, and three of the four Samhitas are "
        "themselves partial -- the Samaveda is the Kauthuma arcika without the gana corpus, "
        "the Yajurveda is the Shukla recension with the Krishna Yajurveda absent entirely, "
        "and the Atharvaveda is Saunaka without Paippalada. Read each row's `scope` and "
        "`excluded_corpora` before treating a per-work count as a Vedic total."
    ),
    source="measured",
)


@router.get(
    "/works",
    summary="List the four Samhitas",
    description=(
        "Every work in the corpus, with its scope-honest `display_label`, its traditional "
        "`traditional_name`, its recension code, the bodies it explicitly does not address, "
        "and measured passage, mantra and translation counts.\n\n"
        "`display_label` is the field to render. `traditional_name` is true and is not a "
        "description of what the corpus holds: for the Samaveda it is 'Samaveda Samhita' "
        "over a corpus that is the arcika only.\n\n"
        "`translated_mantra_count` is a measured figure. Zero for the Samaveda is measured "
        "and real, and the row's caveat says what that zero means."
    ),
    response_model=Paginated[WorkSummary],
    responses=COMMON_ERROR_RESPONSES,
)
def list_works(
    repository: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginated[WorkSummary]:
    works = PassageService(repository).works()
    page = works[offset : offset + limit]
    # The status describes the four works, not this page of them. `?offset=99999999` is a
    # client asking for page four million of a four-row collection, and answering it
    # INSUFFICIENT_EVIDENCE would spend a status meaning "evidence exists and cannot
    # support the claim" on arithmetic -- devaluing it everywhere it is load-bearing.
    status, paging_caveats = paged_meaning(
        page,
        limit=limit,
        offset=offset,
        total=len(works),
        empty_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
        empty_caveats=[
            CaveatView(
                text="No work was returned at all. This corpus holds four Samhitas, so an "
                "empty collection here means the graph could not be read rather than that "
                "the corpus is empty.",
                source="measured",
            )
        ],
    )
    return paginate(
        page,
        limit=limit,
        offset=offset,
        total=len(works),
        data_status=status,
        caveats=[_SCOPE_CAVEAT, *paging_caveats],
    )


@router.get(
    "/works/{work_id}",
    summary="One work, with its scope and measured layer availability",
    description=(
        "A work's full record: the quoted `scope` statement, the `completeness` figure with "
        "its shortfall enumerated, `excluded_corpora`, rights, the native structural "
        "hierarchy with the tradition's name for each level, passage counts by type, "
        "translation coverage, and which knowledge layers measurably reach this corpus.\n\n"
        "`knowledge_layers` is measured per request, never asserted. `NOT_BUILT` there means "
        "the layer has no edge into this work: the Yajurveda has no deity ascription because "
        "the Anukramani apparatus that supplies it covers the Rigveda only, which is a fact "
        "about the apparatus and not about Yajurvedic verses.\n\n"
        "`attribution_splits` reports source-stated and container-inherited attributions "
        "apart. They must not be summed: every one of the Atharvaveda's 5,084 seer "
        "attributions is a hymn label projected onto its verses, and every one of the "
        "Yajurveda's 2,240 is stated by the source."
    ),
    response_model=WorkDetail,
    responses=COMMON_ERROR_RESPONSES,
)
def get_work(repository: RepositoryDep, work_id: WorkIdPath) -> WorkDetail:
    return PassageService(repository).work_detail(work_id)


@router.get(
    "/works/{work_id}/root",
    summary="A work's top-level containers",
    description=(
        "The entry point for browsing a work: its top-level containers in stored reading "
        "order, with the level descriptor beside them.\n\n"
        "The four works enter at four different levels -- 10 Mandalas, 20 Kandas, 40 "
        "Adhyayas and 4 Samavedic collections -- so `root_level` names the level rather than "
        "leaving a client to infer it from the rows. The Samavedic collections come back in "
        "the stored traditional order (Chanda, Aranyaka, Mahanamnya, Uttara), which is not "
        "their alphabetical order.\n\n"
        "Follow each row with `GET /api/v1/passages/{key}/children` to descend."
    ),
    response_model=WorkRoot,
    responses=COMMON_ERROR_RESPONSES,
)
def get_work_root(
    repository: RepositoryDep,
    work_id: WorkIdPath,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkRoot:
    return PassageService(repository).work_root(work_id, limit=limit, offset=offset)
