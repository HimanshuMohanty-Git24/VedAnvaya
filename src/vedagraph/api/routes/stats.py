"""Product-level corpus statistics.

One endpoint, and its shape is a product decision rather than a convenience. The obvious
``/stats`` returns node and relationship totals; this one does not, because this graph's
relationship count is dominated by one annotation layer projecting container labels onto the
passages inside them, and published as a headline that figure measures the build rather than
the corpus. What is returned instead is the population of each thing a reader can ask about,
each with the caveat that makes it readable -- and, for the two populations that have been
misread before, both numbers rather than a chosen one.
"""

from __future__ import annotations

from fastapi import APIRouter

from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.completeness import CompletenessResponse
from vedagraph.api.models.insight import StatsResponse
from vedagraph.api.services.completeness_service import CompletenessService
from vedagraph.api.services.insight_service import InsightService

router = APIRouter(tags=["Stats"], responses=COMMON_ERROR_RESPONSES)


@router.get(
    "/completeness",
    summary="Certified data-completeness state (all corpora)",
    description=(
        "Returns the certified post-campaign data completeness and release state of VedAnvaya, "
        "including exact canonical mantra counts, typed translation coverage, released recitation audio, "
        "audible review gate state, Samaveda musical notation witnesses, and Ask benchmark results."
    ),
    response_model=CompletenessResponse,
    responses=COMMON_ERROR_RESPONSES,
)
@router.get(
    "/stats/completeness",
    include_in_schema=False,
    response_model=CompletenessResponse,
)
def completeness_stats() -> CompletenessResponse:
    return CompletenessService().get_completeness()


@router.get(
    "/stats",
    summary="Corpus and entity populations (aggregate)",
    description=(
        "**Cost class: AGGREGATE.** Groups over the mantra, translation, deity, seer and "
        "cross-Veda layers in one round trip, so it is exempt from the median latency "
        "target.\n\n"
        "**Two deity numbers, both labelled.** `resolved_deities` is the population every "
        "deity surface in this API uses. `anukramani_ascriptions` is the traditional devata "
        "slot as it stands, which also holds human patrons, labels naming a gift rather than a "
        "recipient, and abstractions ruled not to name an addressee. Neither is the corrected version of the other.\n\n"
        "**Seers are separated from non-seer addressees.** The seer slot also names deities, "
        "abstractions, mythic beings, a plant and an object; those are counted apart and their "
        "kinds enumerated, because a combined figure is a category error.\n\n"
        "**A corpus with no translation is null, not zero.** The Samaveda has no released "
        "translation of its own, so every translation-derived layer is absent for it rather "
        "than empty in it, and the per-corpus breakdown says so. 173 of its verses do carry "
        "an English rendering reused from the Rigvedic parallel; that is reported as "
        "`reused_renderings` and never inside `translations`, because adding the two would "
        "report a translated Samaveda.\n\n"
        "**The graph's relationship total is deliberately absent.** Cross-corpus connections "
        "are reported per class instead, with intra-corpus edges excluded and counted "
        "separately: an exact parallel, a directed reuse and a shared entity vocabulary assert "
        "different things and one total over them would rank a vocabulary overlap beside a "
        "verbatim repetition."
    ),
    response_model=StatsResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def product_stats(repository: RepositoryDep) -> StatsResponse:
    return InsightService(repository).product_stats()
