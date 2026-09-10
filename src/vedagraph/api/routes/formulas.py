"""Formula and formula-family detail endpoints.

**This module is new and must be mounted.** ``_mount_v1_routers`` in
:mod:`vedagraph.api.app` lists its routers explicitly, and ``formulas`` is not in that list
yet; without it these two endpoints do not exist and nothing fails loudly, because a router
nobody includes is simply absent from the OpenAPI document.

The generic list surface for formulas belongs to the entity endpoints. What lives here is
the pair of *detail* payloads, because both have to enforce the membership direction
contract that :mod:`vedagraph.api.services.formula_service` owns -- the family layer is
stored in both directions, and a detail view that traversed both would report every family
at twice its real size.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.formula import FormulaDetail, FormulaFamilyDetail
from vedagraph.api.services.formula_service import FormulaService

router = APIRouter(tags=["Formulas"], responses=COMMON_ERROR_RESPONSES)

_FORMULA_DESCRIPTION = """
One recurring wording: its normalised identity, its surface forms, how many passages use
it, which corpora it reaches, the families it belongs to, and a bounded list of the passages
themselves with the wording **as each passage has it** rather than as the normalised form.

`cross_veda` is the field most likely to be over-read, so the response always carries the
reason it must not be: formula identity is a normalised-string match, so a wording found in
all four Samhitas is shared *diction* and not a demonstrated line of transmission. The
Samaveda and much of the Yajurveda are drawn from the Rigveda, which means a four-Veda
formula is often one Rigvedic phrase carried forward rather than four independent
attestations. Per-Veda counts are returned so they can be read as shares of their corpus --
RV 10,552 mantras, AV 5,839, YV 1,975, SV 1,844 -- rather than as comparable totals.

`occurrences` is bounded and `occurrence_count` is not, so a passage missing from the list
is missing from the *page*: `occurrences_truncated` says when that happened.
"""

_FAMILY_DESCRIPTION = """
One family of shared wording: the representative phrase, and the members grouped by the
role each membership records -- `core` for the phrase that names the family, `expansions`
for wordings that contain it, `variants` for the handful that reach it by resemblance
instead.

**Membership is traversed in one direction only, and the response proves it.** The graph
stores every membership twice: 2,037 `(Formula)-[:MEMBER_OF_FAMILY]->(FormulaFamily)` edges
and 2,037 `(FormulaFamily)-[:HAS_FORMULA]->(Formula)` edges mirroring them property for
property, down to a shared `membership_id`. Following both returns every member twice --
measured, that is exactly `2 x member_count` on all 720 families. `MEMBER_OF_FAMILY` is
authoritative, and the `reconciliation` block states the counts actually traversed beside
the counts recorded on the family node, on every response, so the two can be checked
against each other rather than trusted.

**`secondary_core_count` must never be added to the other three.** The membership edges
carry only CORE, EXPANSION and VARIANT, and `core_count + expansion_count + variant_count`
equals `member_count` on all 720 families. 157 families additionally record a
`secondary_core_count`, which is a *subset* of `core_count`; adding it over-counts those
families, and because no edge carries a SECONDARY_CORE role the split is not traversable and
this response cannot say which cores are secondary.

A member's `vedas` and `passage_count` describe where *that member's wording* occurs, not
where the family does. The family's own reach is `vedas`, `veda_span` and
`occurrences_by_veda` on the family itself.
"""


@router.get(
    "/formulas/{formula_id}",
    summary="One recurring wording, its reach, and what its reach does not prove",
    description=_FORMULA_DESCRIPTION,
    response_model=FormulaDetail,
    responses=COMMON_ERROR_RESPONSES,
)
def formula_endpoint(
    repository: RepositoryDep,
    formula_id: Annotated[
        str,
        Path(
            description="A Formula id, e.g. VG:ENRICH:FORMULA:<32 hex characters>.",
            min_length=1,
            max_length=200,
        ),
    ],
) -> FormulaDetail:
    return FormulaService(repository).formula_detail(formula_id)


@router.get(
    "/formula-families/{family_id}",
    summary="One family of shared wording: representative, core, expansions and variants",
    description=_FAMILY_DESCRIPTION,
    response_model=FormulaFamilyDetail,
    responses=COMMON_ERROR_RESPONSES,
)
def formula_family_endpoint(
    repository: RepositoryDep,
    family_id: Annotated[
        str,
        Path(
            description="A FormulaFamily id, e.g. VG:ENRICH:FORMULA-FAMILY:<32 hex characters>.",
            min_length=1,
            max_length=200,
        ),
    ],
) -> FormulaFamilyDetail:
    return FormulaService(repository).family_detail(family_id)
