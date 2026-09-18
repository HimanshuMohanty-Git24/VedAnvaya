"""Insight contract tests, with the three graded regressions at the top.

The aggregate surface is where this product's 0-MISLEADING property is kept or lost, so
these tests are written against the specific answers that were once wrong rather than
against the code that produces them.

*Q10 metals.* Graded MISLEADING for a grid that dropped what it could not match. The
regression here is stronger than "the cell exists": it asserts that **no** metal cell
anywhere in the response carries ``0``, that the one knowingly wrong cell carries its
source verse in the cell rather than only in a caveat, and that the caveat text is fetched
from the frozen query rather than retyped.

*Q23 deity communities.* Graded MISLEADING for returning a plausible four-row pair table
where the honest answer was that no community structure was ever built. The regression
asserts a typed refusal with live measurements, and that the payload says what the zero is
not.

*Q25 ritual objects.* Graded MISLEADING for ranking the chariot and the thunderbolt as the
corpus's foremost ritual objects. The regression asserts the answer is labelled partial,
that those two are absent, and that the response cannot be constructed with an empty
statement of what it does not cover.

Offline tests hold the contract and need no data. Live tests hold the numbers, because
every claim above is a statement about 108,779 real nodes.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.api.conftest import FakeRepository, build_client

# Imported rather than restated. The rite inventory moved from 8 to 103 in one import and
# four files asserted it independently; the one that is about rites owns the figure.
from tests.api.test_rituals import (
    HAS_STEP_TOTAL,
    PROCEDURE_STEP_TOTAL,
    RITUAL_TOTAL,
)
from tests.api.test_stats import FORBIDDEN_IN_BODY, _population_row, _works_rows
from vedagraph.api.models.common import CaveatView, KnowledgeStatus, PaginationMeta
from vedagraph.api.models.entity import NON_DEITY_STRUCTURES
from vedagraph.api.models.insight import (
    CapabilityVerdict,
    CivilizationSection,
    CostClass,
    CrossVedaCellStatus,
    InsightEnvelope,
    InterpretiveClaimRow,
    MetalEvidenceStatus,
    RitualCoverageView,
    RitualsInsightResponse,
    RitualSummaryRow,
    SectionKind,
    WorkScopeView,
    offset_overrun_caveat,
    reject_meaningless_empty,
)
from vedagraph.api.repositories.neo4j_repository import (
    Neo4jRepository,
    named_query_caveat,
)

CROSS_VEDA = "/api/v1/insights/cross-veda"
METALS = "/api/v1/insights/metals"
CAPABILITIES = "/api/v1/insights/capabilities"
RITUALS = "/api/v1/insights/rituals"
CONCERNS = "/api/v1/insights/atharvaveda/concerns"
FORMULAS = "/api/v1/insights/formula-diffusion"
CIVILIZATION = "/api/v1/insights/civilization"
MATERIAL = "/api/v1/insights/material-culture"
DEVATA = "/api/v1/insights/devatas/VG:DEVATA:INDRAH"

ALL_INSIGHTS: tuple[str, ...] = (
    CROSS_VEDA,
    METALS,
    CAPABILITIES,
    RITUALS,
    CONCERNS,
    FORMULAS,
    CIVILIZATION,
    MATERIAL,
    DEVATA,
)

#: Endpoints whose figures are per-corpus, so every one of them must carry the Samavedic
#: exclusion. ``/insights/capabilities`` is absent because it reports no corpus figure at
#: all -- and its Samavedic entry quotes the work node's scope sentence instead.
PER_CORPUS_INSIGHTS: tuple[str, ...] = (
    CROSS_VEDA,
    METALS,
    RITUALS,
    CONCERNS,
    FORMULAS,
    CIVILIZATION,
    MATERIAL,
    DEVATA,
)


@pytest.fixture
def scoped_repository() -> FakeRepository:
    """Answers the corpus-scope and population reads and nothing else.

    Every other aggregate then runs over empty result sets, which is the case worth
    testing offline: a view that found nothing must say why.
    """
    return FakeRepository(
        {
            "w.scope_source AS scope_source": _works_rows(),
            "AS philosophical_concepts": [_population_row()],
        }
    )


@pytest.fixture
def scoped_client(scoped_repository: FakeRepository) -> TestClient:
    app, client = build_client(scoped_repository)
    with client:
        app.state.repository = scoped_repository
        return client


def _scope_statements() -> list[WorkScopeView]:
    return [WorkScopeView(**row) for row in _works_rows()]


def _all_metal_cells(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [cell for row in body["metals"] for cell in row["by_veda"]]


# ---------------------------------------------------------------------------
# The response vocabulary's own guards, tested without a graph
# ---------------------------------------------------------------------------


def test_envelope_refuses_a_corpus_figure_with_no_scope_statement() -> None:
    """The Samaveda rule, generalised and enforced by construction.

    Reporting an SV figure without the work node's exclusions is the failure this refuses.
    It is a validator rather than a review checklist because a checklist is exactly what
    was in place when three caveats drifted from their data.
    """
    with pytest.raises(ValidationError, match="no scope statement"):
        InsightEnvelope(
            insight="x",
            question="q",
            data_status=KnowledgeStatus.SUPPORTED,
            cost_class=CostClass.AGGREGATE,
            cost_note="n",
            vedas_reported=["SV"],
            scope_statements=[],
        )


def test_envelope_accepts_a_corpus_figure_that_carries_its_scope() -> None:
    envelope = InsightEnvelope(
        insight="x",
        question="q",
        data_status=KnowledgeStatus.SUPPORTED,
        cost_class=CostClass.AGGREGATE,
        cost_note="n",
        vedas_reported=["SV"],
        scope_statements=_scope_statements(),
    )
    assert envelope.vedas_reported == ["SV"]


def test_envelope_refuses_a_qualified_answer_with_no_caveat() -> None:
    """Telling a client the answer is limited without telling it how is worse than silence."""
    with pytest.raises(ValidationError, match="no caveat"):
        InsightEnvelope(
            insight="x",
            question="q",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="n",
        )


def test_empty_result_claiming_supported_is_refused() -> None:
    """An empty collection may not assert SUPPORTED with nothing to explain it."""
    with pytest.raises(ValueError, match="non-SUPPORTED data_status or a caveat"):
        reject_meaningless_empty([], status=KnowledgeStatus.SUPPORTED, caveats=[])


def test_empty_result_is_accepted_when_typed_insufficient() -> None:
    reject_meaningless_empty([], status=KnowledgeStatus.INSUFFICIENT_EVIDENCE, caveats=[])
    reject_meaningless_empty(
        [], status=KnowledgeStatus.SUPPORTED, caveats=[CaveatView(text="measured absence")]
    )


def test_civilization_section_refuses_a_row_of_another_kind() -> None:
    """Interpretation cannot arrive in the data section, even by accident."""
    claim = InterpretiveClaimRow(
        claim_id="VG:CLAIM:X", claim_text="a reading", falsifier="a demonstration"
    )
    with pytest.raises(ValidationError, match="must not be flattened into fact"):
        CivilizationSection(
            section_kind=SectionKind.DATA,
            title="t",
            what_this_is="w",
            data_status=KnowledgeStatus.PARTIAL,
            returned=1,
            claim_rows=[claim],
        )


def _bounds(returned: int, *, total: int, offset: int = 0) -> PaginationMeta:
    return PaginationMeta(limit=25, offset=offset, returned=returned, total=total, has_more=False)


def _ritual_response(**overrides: Any) -> RitualsInsightResponse:
    payload: dict[str, Any] = {
        "insight": "ritual_layer",
        "question": "q",
        "data_status": KnowledgeStatus.PARTIAL,
        "cost_class": CostClass.AGGREGATE,
        "cost_note": "n",
        "caveats": [CaveatView(text="c")],
        "coverage_view": RitualCoverageView(
            rituals_modelled=8, rituals_with_steps=1, step_edges=3, statement="s"
        ),
        "objects": [],
        "rituals": [],
        "collections": {"objects": _bounds(0, total=0), "rituals": _bounds(0, total=0)},
        "not_covered": ["something"],
    }
    payload.update(overrides)
    return RitualsInsightResponse(**payload)


def test_ritual_response_refuses_an_empty_statement_of_what_it_omits() -> None:
    """A partial layer with an empty ``not_covered`` would assert completeness."""
    with pytest.raises(ValidationError, match="not_covered may not be empty"):
        _ritual_response(not_covered=[])


def test_response_refuses_bounds_that_describe_a_different_collection() -> None:
    """F-15's exact defect, made unconstructible.

    A ritual response once returned ``returned: 0`` while eight rites sat in the body,
    because its single pagination block described the implement list and the rites list
    beside it was unpaginated. A client reading that block concluded the response was empty
    when it was not. The bounds are now checked against the length of the field they are
    keyed by, so the mismatch cannot be built.
    """
    summary = RitualSummaryRow(
        ritual="soma pressing",
        matched_mantras=1,
        steps=3,
        objects=5,
        offerings=0,
        substances=1,
        devatas=3,
    )
    with pytest.raises(ValidationError, match="describes a different collection"):
        _ritual_response(
            rituals=[summary],
            collections={"objects": _bounds(0, total=0), "rituals": _bounds(0, total=1)},
        )


def test_response_refuses_a_missing_or_unknown_bounds_block() -> None:
    """Every bounded collection needs its own block, and only real collections may have one."""
    with pytest.raises(ValidationError, match="missing"):
        _ritual_response(collections={"objects": _bounds(0, total=0)})
    with pytest.raises(ValidationError, match="unexpected"):
        _ritual_response(
            collections={
                "objects": _bounds(0, total=0),
                "rituals": _bounds(0, total=0),
                "invented": _bounds(0, total=0),
            }
        )


def test_offset_overrun_is_a_paging_caveat_and_never_a_knowledge_status() -> None:
    """F-19: page four million of a fourteen-row table is arithmetic, not evidence.

    ``INSUFFICIENT_EVIDENCE`` means "evidence exists and cannot support the claim". Spending
    it on an offset overrun devalues it everywhere it means what it says, so the status keeps
    describing the collection and this caveat describes the page.
    """
    assert offset_overrun_caveat(_bounds(0, total=14, offset=99_999_999)) is not None
    caveat = offset_overrun_caveat(_bounds(0, total=14, offset=99_999_999))
    assert caveat is not None
    assert "past the end" in caveat.text
    assert "not a finding" in caveat.text
    assert caveat.source == "pagination"
    # Nothing to explain on a full page, or on an empty first page (which has its own rule).
    assert offset_overrun_caveat(_bounds(5, total=14, offset=0)) is None
    assert offset_overrun_caveat(_bounds(0, total=0, offset=0)) is None


def test_offset_overrun_caveat_never_fires_on_a_genuinely_empty_collection() -> None:
    """The guard that stops the caveat contradicting the status it points at.

    Its text asserts the collection is not empty. That is true of an overrun and false of a
    genuinely empty collection, so attaching it unguarded to an empty one would emit a
    caveat denying the very emptiness ``data_status`` had just reported -- worse than the
    silence it replaces. An unknown total is treated the same way: it cannot support a claim
    of non-emptiness either.
    """
    assert offset_overrun_caveat(_bounds(0, total=0, offset=99_999_999)) is None
    unknown = PaginationMeta(limit=25, offset=99_999_999, returned=0, total=None, has_more=False)
    assert offset_overrun_caveat(unknown) is None


# ---------------------------------------------------------------------------
# Offline: outage, validation and the empty-versus-unknown distinction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ALL_INSIGHTS)
def test_every_insight_is_503_when_the_graph_is_down(path: str, down_client: TestClient) -> None:
    response = down_client.get(path)
    assert response.status_code == 503
    assert response.json()["error"] == "KNOWLEDGE_GRAPH_UNAVAILABLE"


@pytest.mark.parametrize("path", ALL_INSIGHTS)
def test_outage_body_names_no_host_or_query(path: str, down_client: TestClient) -> None:
    body = down_client.get(path).text
    for token in FORBIDDEN_IN_BODY:
        assert token not in body, f"{path} outage body leaked {token!r}"


def test_material_culture_empty_result_is_insufficient_evidence_not_supported(
    scoped_client: TestClient,
) -> None:
    """The central distinction, exercised end to end.

    The repository answers no mention rows. The response must not be a 200 whose empty list
    claims SUPPORTED, because that asserts the corpus names no crops, no metals and no
    rivers -- and a client rendering rows alone would read exactly that.
    """
    response = scoped_client.get(MATERIAL)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["data_status"] == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert body["caveats"], "an empty aggregate must carry a caveat"


def test_unknown_material_category_is_a_400_and_not_an_empty_page(
    scoped_client: TestClient,
) -> None:
    """ "No such category" and "that category is empty" are different answers."""
    response = scoped_client.get(MATERIAL, params={"category": "chariots"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "BAD_REQUEST"
    assert "crops" in (body["hint"] or "")


def test_unknown_capability_question_is_a_404_and_not_an_empty_list(
    scoped_client: TestClient,
) -> None:
    """An empty capability list would assert that the product has no limits."""
    response = scoped_client.get(CAPABILITIES, params={"question": 99})
    assert response.status_code == 404


@pytest.mark.parametrize("path", (MATERIAL, RITUALS, CONCERNS, FORMULAS, CIVILIZATION))
def test_page_size_above_the_bound_is_refused_not_truncated(
    path: str, scoped_client: TestClient
) -> None:
    """Silent truncation is indistinguishable from the end of the data."""
    assert scoped_client.get(path, params={"limit": 5_000}).status_code == 422


def test_insight_without_a_scope_read_refuses_to_serve(client: TestClient) -> None:
    """No corpus boundaries, no corpus figures.

    The deity view is excluded from the sweep on purpose: its entity lookup runs first, so
    an unscripted repository yields a 404 for the deity rather than a 503 for the scope,
    and "no such deity" is the more useful of the two answers.
    """
    for path in PER_CORPUS_INSIGHTS:
        if path == DEVATA:
            assert client.get(path).status_code == 404
            continue
        assert client.get(path).status_code == 503, path


def test_every_insight_parameter_travels_bound(scoped_repository: FakeRepository) -> None:
    """No client value is ever spliced into query text."""
    app, client = build_client(scoped_repository)
    with client:
        app.state.repository = scoped_repository
        client.get(MATERIAL, params={"category": "metals", "limit": 3})
        client.get(CIVILIZATION, params={"limit": 4, "offset": 2})
    assert "metals" not in scoped_repository.query_text
    assert scoped_repository.all_parameters.get("limit") in {3, 4}


# ---------------------------------------------------------------------------
# Live: Q10 -- the metals regression
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_q10_no_metal_cell_anywhere_renders_as_zero(live_client: TestClient) -> None:
    """There must be no path by which an unmatched metal cell reads as 0.

    The strongest form of the Q10 contract, and the reason it is asserted over every cell
    rather than over the one known-wrong one: a lexical miss is a fact about an alias
    registry that admits attested whole-word inflections only, so ``0`` would claim an
    absence the matcher cannot establish for *any* metal in *any* corpus.
    """
    body = live_client.get(METALS).json()
    cells = _all_metal_cells(body)
    assert cells, "the grid must not be empty"
    for cell in cells:
        assert cell["matched_mantras"] != 0, cell
        assert cell["per_1000_mantras"] != 0, cell
        if cell["evidence_status"] == MetalEvidenceStatus.NO_LEXICAL_MATCH:
            assert cell["matched_mantras"] is None, cell
            assert cell["knowledge_status"] != KnowledgeStatus.SUPPORTED, cell
            assert cell["note"], cell


@pytest.mark.neo4j
def test_q10_the_grid_is_complete_and_says_so(live_client: TestClient) -> None:
    """Every registered metal against every corpus, and the shape is checkable."""
    body = live_client.get(METALS).json()
    shape = body["shape"]
    assert shape["cells_returned"] == shape["cells_expected"]
    assert shape["columns"] == 4
    assert shape["rows"] == len(body["metals"])
    for row in body["metals"]:
        assert [cell["veda"] for cell in row["by_veda"]] == ["RV", "AV", "YV", "SV"]


@pytest.mark.neo4j
def test_q10_yajurvedic_ayas_is_typed_in_its_own_row_with_its_source_locator(
    live_client: TestClient,
) -> None:
    """The one knowingly wrong cell, typed in the cell and not only in a caveat.

    The Yajurveda names ``ayas`` at VSM 18.13, and no alias can be registered for it: the
    elided Devanagari folds to a token that is the relative pronoun in almost all of its
    corpus occurrences, so registering it would land wrong-sense mentions instead of one
    right one. A caveat-only disclosure is not acceptable here, because a client that
    renders rows would still conclude that the Yajurveda has no metal -- so this asserts the
    locator is on the cell, and that the cell says what it is not.
    """
    body = live_client.get(METALS).json()
    ayas = next(row for row in body["metals"] if row["entity_key"] == "VG:CONCEPT:AYAS-METAL")
    cell = next(cell for cell in ayas["by_veda"] if cell["veda"] == "YV")

    assert cell["evidence_status"] == MetalEvidenceStatus.NO_LEXICAL_MATCH
    assert cell["matched_mantras"] is None
    assert cell["source_witness"] == "VSM 18.13"
    assert "VSM 18.13" in cell["note"]
    assert "NOT '0 occurrences'" in cell["note"]
    assert "NOT 'absent from this Veda'" in cell["note"]
    # And the same cell is declared at the top level, with what the verse is measured to name.
    gap = next(
        gap
        for gap in body["declared_gaps"]
        if gap["entity_key"] == "VG:CONCEPT:AYAS-METAL" and gap["veda"] == "YV"
    )
    assert gap["source_witness"] == "VSM 18.13"
    assert len(gap["co_attested_at_witness"]) >= 4


@pytest.mark.neo4j
def test_q10_caveat_is_the_frozen_one_and_not_a_retyped_copy(live_client: TestClient) -> None:
    """The caveat is fetched from the graded query, so it cannot drift from it.

    V3.1 and V3.2 both found hand-copied caveat prose that had drifted from the data it
    described, and that is what made three benchmark questions MISLEADING. This asserts
    identity with the frozen text rather than similarity to it.
    """
    body = live_client.get(METALS).json()
    frozen = next(caveat for caveat in body["caveats"] if caveat["source"] == "metals_by_veda")
    assert frozen["text"] == named_query_caveat("metals_by_veda")


@pytest.mark.neo4j
def test_q10_reports_the_ordering_that_normalising_produces(live_client: TestClient) -> None:
    """Gold is Rigveda-first raw and Atharvaveda-first per thousand mantras.

    Normalising can invert an ordering, and the raw figure is the one a reader sees. So the
    row states both and flags the inversion rather than leaving a client to notice that the
    ranking it rendered depends on which column it sorted.
    """
    body = live_client.get(METALS).json()
    gold = next(row for row in body["metals"] if row["entity_key"] == "VG:CONCEPT:HIRANYA-GOLD")
    assert gold["ordering_inverts"] is True
    assert gold["raw_ordering"][0] == "RV"
    assert gold["normalised_ordering"][0] == "AV"
    assert gold["ordering_note"]


# ---------------------------------------------------------------------------
# Live: Q23 -- the capability refusal
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_q23_is_a_typed_refusal_and_not_an_empty_list(live_client: TestClient) -> None:
    """The refusal has to explain why, in terms of the graph rather than the corpus.

    The version graded MISLEADING returned a confident four-row deity-pair table whose top
    and fourth rows were human patrons, while no community structure existed anywhere. This
    asserts the replacement: NOT_ANSWERABLE, NOT_BUILT, live measurements including the zero
    that is the finding, and an explicit statement of the conclusion the refusal prevents.
    """
    response = live_client.get(CAPABILITIES, params={"question": 23})
    assert response.status_code == 200
    body = response.json()
    limit = body["limits"][0]

    assert limit["question_number"] == 23
    assert limit["verdict"] == CapabilityVerdict.NOT_ANSWERABLE
    assert limit["data_status"] == KnowledgeStatus.NOT_BUILT
    assert limit["why"]
    assert "NOT a finding" in limit["what_this_is_not"]
    assert limit["safe_alternative"]
    assert limit["what_would_change_it"]

    measured = {row["name"]: row for row in limit["measurements"]}
    assert measured["deities_with_a_community_assignment"]["value"] == 0
    assert "about the graph" in measured["deities_with_a_community_assignment"]["means"]
    assert measured["pairwise_co_occurrence_edges"]["value"] == 306
    # Was pinned at 192, which is what the query published while it excluded
    # structure='HUMAN' alone -- 7 danastuti gift-praise labels and one non-divine subject
    # above even the crude figure, on the endpoint whose whole job is to refuse a deity
    # table contaminated by patrons. GAP-ENTITY_COVERAGE-008 replaced the predicate. The
    # assertion is expressed against the row's OWN pending count rather than against a
    # literal, so it stays true across the mutation that lands the ruling instead of having
    # to be edited again the day the data changes.
    unruled = measured["devatas_without_an_eligibility_ruling"]["value"]
    expected_eligible = 185 if unruled else 157
    assert measured["eligible_deities"]["value"] == expected_eligible, (
        f"{unruled} Devata carry no is_deity ruling, so eligible_deities must read "
        f"{expected_eligible}"
    )
    assert measured["eligible_deities"]["value"] != 192
    assert "denominator" in measured["eligible_deities"]["means"]
    assert "danastuti" in measured["eligible_deities"]["means"]
    # Every measurement must say what it means; a bare figure is what this endpoint refuses.
    assert all(row["means"] for row in limit["measurements"])


@pytest.mark.neo4j
def test_q23_carries_the_frozen_capability_caveat(live_client: TestClient) -> None:
    body = live_client.get(CAPABILITIES, params={"question": 23}).json()
    caveat = next(
        caveat
        for caveat in body["limits"][0]["caveats"]
        if caveat["source"] == "deity_community_capability"
    )
    assert caveat["text"] == named_query_caveat("deity_community_capability")


@pytest.mark.neo4j
def test_capability_catalogue_is_enumerable_and_states_its_own_incompleteness(
    live_client: TestClient,
) -> None:
    """A frontend must be able to discover the boundary rather than trip over it."""
    body = live_client.get(CAPABILITIES).json()
    assert body["total_available"] == len(body["limits"]) >= 5
    numbers = {limit["question_number"] for limit in body["limits"]}
    assert {23, 25} <= numbers
    # The load-bearing clause, not the old wording. The catalogue used to say "this
    # catalogue is not exhaustive" while publishing 7 cards against 21 graded questions;
    # it now covers all 21 and says instead that the benchmark is a hundred questions
    # rather than every question. Both sentences make the same promise and only this
    # clause is common to them, so the test asserts the promise.
    assert any("not thereby answerable" in caveat["text"] for caveat in body["caveats"])
    assert body["unpublished_not_answerable"] == []
    for limit in body["limits"]:
        assert limit["verdict"] in set(CapabilityVerdict)
        assert limit["data_status"] != KnowledgeStatus.SUPPORTED
        assert limit["what_this_is_not"]


# ---------------------------------------------------------------------------
# Live: Q25 -- the partial ritual answer
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_q25_is_labelled_partial_with_what_is_and_is_not_covered(
    live_client: TestClient,
) -> None:
    """A real ranking, labelled partial, bounded by measured figures.

    The version graded MISLEADING ranked the chariot and the thunderbolt as the corpus's
    foremost ritual objects. The replacement defines an implement as an object a modelled
    rite uses, so those two are excluded by construction; this asserts both the label and
    the exclusion, and that the response states its own ceiling.
    """
    response = live_client.get(RITUALS)
    assert response.status_code == 200
    body = response.json()

    assert body["data_status"] == KnowledgeStatus.PARTIAL
    assert body["objects"], "the partial answer still has to be a real answer"
    labels = " ".join(row["implement"] for row in body["objects"]).lower()
    assert "chariot" not in labels
    assert "thunderbolt" not in labels
    assert "ratha" not in labels
    assert "vajra" not in labels

    coverage = body["coverage_view"]
    assert coverage["rituals_modelled"] == RITUAL_TOTAL
    assert coverage["step_edges"] == HAS_STEP_TOTAL
    assert coverage["procedure_step_edges"] == PROCEDURE_STEP_TOTAL
    # The layers are reported apart and never summed. Reporting only the Samhita figure made
    # this view state that one rite of 103 carried "any procedure at all", and that no rite
    # had a recoverable sequence, while 3,121 located sutra steps sat in the graph.
    assert coverage["step_edges"] != coverage["procedure_step_edges"]
    assert coverage["procedure_partial_steps"] < coverage["procedure_step_edges"], (
        "if every step were partial the share would stop discriminating; if none were, the "
        "caveat about non-contiguous runs would be describing nothing"
    )
    assert coverage["procedure_source_works"] > 1, (
        "the per-work grouping only means something if more than one work is cited"
    )
    assert coverage["statement"]
    assert str(HAS_STEP_TOTAL + PROCEDURE_STEP_TOTAL) not in coverage["statement"].replace(
        ",", ""
    ), "the two step layers must not be added together anywhere in the prose"

    assert body["not_covered"], "a partial layer must say what it omits"
    omitted = " ".join(body["not_covered"]).lower()
    assert "chariot" in omitted and "thunderbolt" in omitted
    assert "brahmana" in omitted
    assert "do not compose" in omitted or "independently numbered" in omitted, (
        "the sutra layer is large enough now that omitting to say it does not compose into "
        "a procedure would read as procedural coverage"
    )


@pytest.mark.neo4j
def test_q25_partial_semantics_are_reachable_through_the_capability_catalogue(
    live_client: TestClient,
) -> None:
    """The same limit, discoverable by question number."""
    body = live_client.get(CAPABILITIES, params={"question": 25}).json()
    limit = body["limits"][0]
    assert limit["verdict"] == CapabilityVerdict.PARTIALLY_ANSWERABLE
    assert limit["data_status"] == KnowledgeStatus.PARTIAL
    assert limit["endpoint"] == RITUALS
    measured = {row["name"]: row["value"] for row in limit["measurements"]}
    assert measured["rituals_modelled"] == RITUAL_TOTAL
    assert measured["step_edges"] == HAS_STEP_TOTAL
    assert measured["procedure_step_edges"] == PROCEDURE_STEP_TOTAL
    # 15 since the ritual-object adjudication landed; was 14. The figure is a snapshot and
    # the assertion below is the actual guard.
    assert measured["curated_implements"] == 15
    # Grew from 23 with the Wave 3 object registry. The curation ceiling is the point of the
    # pair, so what matters is that the registry stays the larger of the two.
    assert measured["objects_in_the_registry"] == 41
    assert measured["curated_implements"] < measured["objects_in_the_registry"], (
        "if these ever match, the curation ceiling this measurement exists to expose is gone"
    )
    assert "NOT a census" in limit["what_this_is_not"]


@pytest.mark.neo4j
def test_q25_rows_carry_their_registry_type(live_client: TestClient) -> None:
    """The axe is registered a weapon and is a ritual tool anyway, so the row says both."""
    body = live_client.get(RITUALS).json()
    types = {row["registry_type"] for row in body["objects"]}
    assert types - {None}


# ---------------------------------------------------------------------------
# Live: the cross-Veda matrix
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_cross_veda_matrix_returns_all_six_pairs_with_every_cell_typed(
    live_client: TestClient,
) -> None:
    """No pair omitted, no class omitted, no cell untyped.

    A query returning only its positive rows lets a reader infer a false zero, so the grid
    is enumerated from the constant six pairs and the constant class list. This asserts the
    full product is present and that the declared shape matches what was shipped.
    """
    body = live_client.get(CROSS_VEDA).json()
    pairs = {row["pair"] for row in body["pairs"]}
    assert pairs == {"AV-RV", "RV-SV", "RV-YV", "AV-SV", "AV-YV", "SV-YV"}

    shape = body["shape"]
    assert shape["rows"] == 6
    assert shape["cells_returned"] == shape["cells_expected"] == 6 * shape["columns"]

    valid = set(CrossVedaCellStatus)
    for row in body["pairs"]:
        assert len(row["cells"]) == shape["columns"]
        for cell in row["cells"]:
            assert cell["status"] in valid, cell
            assert cell["note"], cell
            if cell["status"] not in {
                CrossVedaCellStatus.MEASURED,
                CrossVedaCellStatus.MEASURED_ZERO,
            }:
                assert cell["edges"] is None, cell


@pytest.mark.neo4j
def test_cross_veda_no_cell_is_silently_omitted_or_silently_zero(
    live_client: TestClient,
) -> None:
    """Each class appears once per pair, and an unbuilt cell is null rather than nought."""
    body = live_client.get(CROSS_VEDA).json()
    classes = {view["relationship_class"] for view in body["relationship_classes"]}
    for row in body["pairs"]:
        present = [cell["relationship_class"] for cell in row["cells"]]
        assert sorted(present) == sorted(classes), row["pair"]
        assert len(present) == len(set(present))


@pytest.mark.neo4j
def test_directed_reuse_absence_is_typed_and_carries_the_parallels_that_disprove_it(
    live_client: TestClient,
) -> None:
    """The single most dangerous zero in this graph, and how the matrix defuses it.

    Directed textual reuse reaches two pairs, RV-SV and AV-RV. Rendered as ``0`` for the
    other four it would say the Yajurveda reuses no Rigvedic text -- and RV-YV carries 662
    undirected parallels in this very graph. So those cells are NOT_ESTABLISHED_FOR_PAIR,
    and each carries the measured parallel count for its own pair.

    The absent example used to be AV-RV. It gained 311 directed edges when the reuse
    direction layer was extended, so it is asserted here as the *second measured* pair and
    the guard moves to a pair that still has none. Bumping the expected status instead
    would have deleted the guard rather than updated it.
    """
    body = live_client.get(CROSS_VEDA).json()
    cells = {
        (row["pair"], cell["relationship_class"]): cell
        for row in body["pairs"]
        for cell in row["cells"]
    }
    measured = cells[("RV-SV", "REUSES_TEXT_FROM")]
    assert measured["status"] == CrossVedaCellStatus.MEASURED
    assert measured["edges"] == 1684

    also_measured = cells[("AV-RV", "REUSES_TEXT_FROM")]
    assert also_measured["status"] == CrossVedaCellStatus.MEASURED
    assert also_measured["edges"] and also_measured["edges"] > 0

    # The four pairs with no directed reuse are MEASURED_ZERO now rather than
    # NOT_ESTABLISHED_FOR_PAIR, because a typed refusal was computed for each: the zero is a
    # decision that the instrument does not apply, not an unrun measurement. What this test
    # guards is unchanged and asserted on the note -- the zero may not travel naked, it must
    # name its refusal and carry the undirected parallels that disprove a reading of "these
    # two corpora share no text".
    refused = cells[("RV-YV", "REUSES_TEXT_FROM")]
    assert refused["status"] == CrossVedaCellStatus.MEASURED_ZERO
    assert refused["related_edges_on_pair"] and refused["related_edges_on_pair"] > 500
    assert "REFUSED_UNIT_GRANULARITY_INCOMPARABLE" in refused["note"]
    assert "measured refusal and not an unbuilt cell" in refused["note"]
    assert "undirected parallel edges are unaffected" in refused["note"]


@pytest.mark.neo4j
def test_semantic_assertion_layer_contributes_no_cross_veda_count(
    live_client: TestClient,
) -> None:
    """The layer contributes no *pair* count, and that is not the same as not existing.

    This test asserted NOT_BUILT and required the word "Rigvedic" in the note, on the
    premise that every assertion is Rigvedic. That premise was false when it was written
    or became false soon after: the layer reaches AV, YV and SV as well, and the same cell
    carried a measured total saying so. The row still appears in all six pairs and still
    carries no count -- an assertion is a predication about one passage, so it has no
    second endpoint -- but the reason is CLASS_NOT_CROSS_VEDA, not absence.

    Omitting the row would leave a reader with a table of built classes and no way to know
    the semantic layer cannot speak to a cross-corpus question; reporting it as 0 would say
    the corpora share no semantic structure.
    """
    body = live_client.get(CROSS_VEDA).json()
    rows = [
        cell
        for row in body["pairs"]
        for cell in row["cells"]
        if cell["relationship_class"] == "SEMANTIC_ASSERTION"
    ]
    assert len(rows) == 6
    for cell in rows:
        assert cell["status"] == CrossVedaCellStatus.CLASS_NOT_CROSS_VEDA
        assert cell["edges"] is None
        assert "every one of its assertions is Rigvedic" not in cell["note"]


@pytest.mark.neo4j
def test_semantic_resemblance_row_is_not_built_rather_than_zero(
    live_client: TestClient,
) -> None:
    """No embedding, no vector index, no asserted resemblance anywhere in this graph."""
    body = live_client.get(CROSS_VEDA).json()
    census = {row["method"]: row for row in body["method_census"]}
    unbuilt = [row for row in census.values() if row["population_status"] == "NOT_BUILT"]
    assert unbuilt
    for row in unbuilt:
        assert row["edges"] is None
        assert row["note"]


@pytest.mark.neo4j
def test_class_reaching_only_one_pair_is_visible_in_the_class_summary(
    live_client: TestClient,
) -> None:
    body = live_client.get(CROSS_VEDA).json()
    views = {view["relationship_class"]: view for view in body["relationship_classes"]}
    # Two pairs since the direction layer was extended; was ["RV-SV"].
    assert views["REUSES_TEXT_FROM"]["pairs_reached"] == ["AV-RV", "RV-SV"]
    assert len(views["NEAR_PARALLEL_OF"]["pairs_reached"]) == 6
    # A class entirely inside one corpus reports no pair and is typed as such per cell.
    assert views["PARALLEL_TO"]["pairs_reached"] == []
    assert views["PARALLEL_TO"]["within_one_veda_edges"] == 69


# ---------------------------------------------------------------------------
# Live: attribution versus textual mention
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_deity_naming_and_ascription_are_separate_fields_with_separate_scopes(
    live_client: TestClient,
) -> None:
    """The distinction the whole deity surface rests on.

    Naming is what the verse says and spans four corpora. Ascription is the traditional
    apparatus dedicating a hymn and exists for the Rigveda alone. Summed they would add a
    statement of the text to a projection over a container, for the one corpus that has the
    container labels -- so they are separate fields, separately scoped, and the response
    says the sum is not available.
    """
    body = live_client.get(DEVATA).json()
    assert body["named_by_veda"]["by_veda"]["av"] is not None
    assert body["ascribed_scope"] == ["RV"]
    assert body["ascribed_total"] is not None
    assert body["named_total"] != body["ascribed_total"]
    assert "missing apparatus" in body["ascription_note"]
    assert body["mention_surplus"] == body["named_total"] - body["ascribed_total"]
    # The corpora the ascription layer does not reach are named rather than left as zeros --
    # in the *ascription* dimension. They used to be named in the response's single coverage
    # block, beside naming figures for the same three corpora, which told a machine consumer
    # that AV 635, YV 221 and SV 405 were all uncovered. See
    # tests/api/test_coverage_dimensions.py.
    ascription = next(
        dim for dim in body["coverage"]["dimensions"] if dim["dimension"] == "ascription"
    )
    assert set(ascription["vedas_not_covered"]) == {"AV", "YV", "SV"}
    assert body["coverage"]["vedas_not_covered"] == []
    assert body["named_by_veda"]["per_1000_by_veda"]


@pytest.mark.neo4j
def test_g01_default_population_refuses_every_non_deity(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """The deity gate, on this route, for all 57 of them.

    This endpoint had the machine-readable half right -- ``is_resolved_deity: false`` and
    ``structure`` on the row -- and still served the dog at 200 with no disclosure under a
    question calling it a deity, while ``/devatas/VG:DEVATA:SUNAH`` 404'd for the same id in
    the same API. Enumerated over the whole non-deity population rather than sampled,
    because the pass-1 defect of this class was found on one route and missed on another.
    """
    non_deities = [
        str(row["k"])
        for row in live_repository.run(
            "MATCH (d:Devata) WHERE d.is_deity = false RETURN d.entity_key AS k ORDER BY k"
        )
    ]
    assert len(non_deities) == 57, "the non-deity population has moved; re-read this test"
    for entity_key in non_deities:
        response = live_client.get(f"/api/v1/insights/devatas/{entity_key}")
        assert response.status_code == 404, entity_key
        assert response.json()["error"] == "ENTITY_NOT_FOUND"
        # And the refusal points at the population that would serve it.
        assert "all_ascriptions" in (response.json()["hint"] or ""), entity_key


@pytest.mark.neo4j
def test_g01_non_deity_under_all_ascriptions_carries_both_disclosure_halves(
    live_client: TestClient,
) -> None:
    """Served deliberately, and never as a god.

    Both halves come from ``subject_disclosure``, so a route cannot take the flag without
    the caveat. The question string is asserted too: naming the subject a deity there is the
    same error as omitting the caveat, one field along.
    """
    body = live_client.get(
        "/api/v1/insights/devatas/VG:DEVATA:BHAVAVRTTAM",
        params={"population": "all_ascriptions"},
    ).json()
    assert body["is_resolved_deity"] is False
    assert body["structure"] == "ABSTRACT"
    disclosure = next(
        caveat for caveat in body["caveats"] if caveat["source"] == "deity_population_contract"
    )
    assert "THIS SUBJECT IS NOT A DEITY" in disclosure["text"]
    # The disclosure comes first, so a client rendering one caveat renders this one.
    assert body["caveats"][0]["source"] == "deity_population_contract"
    assert "NOT a deity" in body["question"]
    # Its ascription figures are real and still served.
    assert body["ascribed_total"] is not None


@pytest.mark.neo4j
def test_g01_the_gate_leaves_real_deities_untouched(live_client: TestClient) -> None:
    """No deity acquires a not-a-deity caveat, and none is refused."""
    for entity_key in ("VG:DEVATA:INDRAH", "VG:DEVATA:PRTHIVI", "VG:DEVATA:SOMAH"):
        body = live_client.get(f"/api/v1/insights/devatas/{entity_key}").json()
        assert body["is_resolved_deity"] is True
        assert not any(
            caveat["source"] == "deity_population_contract" for caveat in body["caveats"]
        )
        assert "NOT a deity" not in body["question"]


@pytest.mark.neo4j
def test_deity_insight_reports_all_three_certainty_tiers(live_client: TestClient) -> None:
    """A deity whose name is an ordinary noun is flattered or penalised by the tier choice."""
    body = live_client.get("/api/v1/insights/devatas/VG:DEVATA:SOMAH").json()
    certainty = body["certainty"]
    assert certainty["ambiguous_count"] > certainty["certain_count"]
    assert certainty["included_tiers"] == ["DEITY_CERTAIN", "DEITY_PROBABLE"]
    strict = live_client.get(
        "/api/v1/insights/devatas/VG:DEVATA:SOMAH", params={"certainty": "strict"}
    ).json()
    assert strict["named_total"] < body["named_total"]
    assert strict["certainty"]["included_tiers"] == ["DEITY_CERTAIN"]


@pytest.mark.neo4j
def test_unknown_deity_is_a_404_not_an_empty_profile(live_client: TestClient) -> None:
    response = live_client.get("/api/v1/insights/devatas/VG:DEVATA:NO-SUCH-THING")
    assert response.status_code == 404
    assert response.json()["error"] == "ENTITY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Live: the Samavedic disclaimer, everywhere
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize("path", PER_CORPUS_INSIGHTS)
def test_any_samavedic_figure_carries_the_arcika_scope_statement(
    path: str, live_client: TestClient
) -> None:
    """The mandatory disclaimer, asserted on every endpoint that reports an SV number.

    Read from the ``Work`` node rather than typed, so the sentence cannot drift from the
    corpus it describes. Its opening words are the point: this graph holds the Kauthuma
    arcika and not the gana corpus, and a Samavedic figure published without that is the
    single most misleading string this product can emit.
    """
    body = live_client.get(path).json()
    if "SV" not in body["vedas_reported"]:
        pytest.skip(f"{path} reports no Samavedic figure")
    samaveda = next(
        statement for statement in body["scope_statements"] if statement["veda"] == "SV"
    )
    assert "NOT THE COMPLETE SAMAVEDA" in (samaveda["scope"] or "").upper()
    assert samaveda["work_id"] == "VG:WORK:SV:KAU"
    assert any("GANA" in item.upper() for item in samaveda["excluded_corpora"])


@pytest.mark.neo4j
def test_yajurvedic_and_atharvavedic_exclusions_are_stated_too(live_client: TestClient) -> None:
    """Every corpus here has an exclusion a reader would not otherwise know about."""
    body = live_client.get(CROSS_VEDA).json()
    scopes = {statement["veda"]: statement for statement in body["scope_statements"]}
    assert "KRISHNA" in (scopes["YV"]["scope"] or "").upper()
    assert "PAIPPALADA" in (scopes["AV"]["scope"] or "").upper()


# ---------------------------------------------------------------------------
# Live: the civilization separation
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_civilization_keeps_data_metrics_and_interpretation_in_separate_sections(
    live_client: TestClient,
) -> None:
    """Three kinds of thing, three sections, three statuses. Not one ranked feed."""
    body = live_client.get(CIVILIZATION).json()
    sections = {section["section_kind"]: section for section in body["sections"]}
    assert set(sections) == {
        SectionKind.DATA,
        SectionKind.DERIVED_METRIC,
        SectionKind.INTERPRETIVE_CLAIM,
    }
    assert sections[SectionKind.DATA]["data_rows"]
    assert not sections[SectionKind.DATA]["claim_rows"]
    assert sections[SectionKind.DERIVED_METRIC]["metric_rows"]
    assert not sections[SectionKind.DERIVED_METRIC]["claim_rows"]
    assert sections[SectionKind.INTERPRETIVE_CLAIM]["claim_rows"]
    assert not sections[SectionKind.INTERPRETIVE_CLAIM]["data_rows"]
    # Interpretation is the weakest section and says so.
    assert (
        sections[SectionKind.INTERPRETIVE_CLAIM]["data_status"]
        == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    )
    for section in body["sections"]:
        assert section["what_this_is"]
        assert section["caveats"]


@pytest.mark.neo4j
def test_every_interpretive_claim_surfaces_its_falsifier(live_client: TestClient) -> None:
    """A claim that states what would refute it is a different object from a measurement."""
    body = live_client.get(CIVILIZATION).json()
    claims = next(
        section["claim_rows"]
        for section in body["sections"]
        if section["section_kind"] == SectionKind.INTERPRETIVE_CLAIM
    )
    assert len(claims) >= 5
    for claim in claims:
        assert claim["falsifier"]
        assert claim["about"] in {"VEDIC_TEXT", "DATASET", "TRADITIONAL_APPARATUS"}
        assert claim["quality_tier"] == "TIER_D"


@pytest.mark.neo4j
def test_interpretation_section_discloses_which_text_the_evidence_was_read_off(
    live_client: TestClient,
) -> None:
    """Half the semantic layer rests on a 19th-century English rendering, and it says so.

    A claim built on a translation is evidence about a translator, so the section reports the
    measured surface split rather than presenting all of its evidence as Sanskrit. The figure
    is measured on the request from the graph's own ``evidence_basis`` property -- which is a
    different axis from the API's ``EvidenceBasis`` vocabulary and has a disjoint value space.
    """
    body = live_client.get(CIVILIZATION).json()
    section = next(
        section
        for section in body["sections"]
        if section["section_kind"] == SectionKind.INTERPRETIVE_CLAIM
    )
    disclosure = next(
        caveat["text"] for caveat in section["caveats"] if "read off" in caveat["text"]
    )
    assert "TRANSLATION" in disclosure
    assert "SANSKRIT" in disclosure
    assert "19th-century English" in disclosure
    assert "must not be aggregated" in disclosure


@pytest.mark.neo4j
def test_deity_evidence_surface_is_read_not_cast(live_client: TestClient) -> None:
    """The graph's ``evidence_basis`` is a surface, and the API's is a derivation axis.

    Casting one to the other reported every attribution edge in the corpus as UNKNOWN once
    already, so the mention layer's surface is read into its own field and the derivation
    axis is derived from ``attribution_precision`` instead.
    """
    evidence = live_client.get(DEVATA).json()["evidence"]
    assert evidence["surface"] == "SANSKRIT"
    assert evidence["attribution_precision"] == "TEXTUAL_MENTION"
    assert evidence["evidence_basis"] == "TEXTUAL_MENTION"
    assert evidence["evidence_basis"] != "UNKNOWN"


@pytest.mark.neo4j
def test_cross_veda_matrix_states_the_intra_corpus_population_it_excludes(
    live_client: TestClient,
) -> None:
    """Same-corpus parallels carry no corpus pair, so they cannot be silently dropped.

    A matrix built by filtering on the edge's own ``veda_pair`` would lose every intra-corpus
    parallel and then compute a cross-corpus share of a population it never named. They are
    counted from the node vedas instead, excluded from the cells by design, and reported.
    """
    body = live_client.get(CROSS_VEDA).json()
    disclosure = next(
        caveat["text"] for caveat in body["caveats"] if "inside a single corpus" in caveat["text"]
    )
    assert "325" in disclosure
    assert "EXACT_PARALLEL_OF 256" in disclosure
    assert "PARALLEL_TO 69" in disclosure
    totals = {
        view["relationship_class"]: view["within_one_veda_edges"]
        for view in body["relationship_classes"]
    }
    assert sum(totals.values()) == 325


@pytest.mark.neo4j
def test_g04_civilization_honours_limit_and_offset_in_every_section(
    live_client: TestClient,
) -> None:
    """All three sections page, and each reports its own bounds.

    The interpretation section reported ``returned: 6`` under ``limit=5`` and handed back the
    same six rows at every offset, while the two beside it paged correctly -- so the view had
    two paging behaviours and no bounds block at all.
    """
    body = live_client.get(CIVILIZATION, params={"limit": 5}).json()
    assert set(body["collections"]) == {
        SectionKind.DATA,
        SectionKind.DERIVED_METRIC,
        SectionKind.INTERPRETIVE_CLAIM,
    }
    for section in body["sections"]:
        rows = len(section["data_rows"]) + len(section["metric_rows"]) + len(section["claim_rows"])
        assert rows <= 5, section["section_kind"]
        bounds = body["collections"][section["section_kind"]]
        assert bounds["returned"] == section["returned"] == rows
        assert bounds["limit"] == 5

    # Distinct rows per offset: the section that ignored `limit` also ignored `offset`.
    seen = []
    for offset in (0, 1, 2, 5):
        page = live_client.get(CIVILIZATION, params={"limit": 1, "offset": offset}).json()
        claims = next(
            section["claim_rows"]
            for section in page["sections"]
            if section["section_kind"] == SectionKind.INTERPRETIVE_CLAIM
        )
        seen.append(claims[0]["claim_id"] if claims else None)
    assert len(set(seen)) == len(seen), f"the same rows came back at different offsets: {seen}"


@pytest.mark.neo4j
def test_g04_civilization_overrun_keeps_the_real_total_and_carries_the_paging_caveat(
    live_client: TestClient,
) -> None:
    """An overrun must not zero out the total it is meant to be measured against.

    The metric section is paged in Cypher, and the obvious form of that query lost its total
    whenever the offset overran -- reporting ``total_available: 0`` against a live 1,072, on
    exactly the paging condition the caveat exists to explain. The caveat's own non-empty
    guard would then have suppressed it, one defect hiding another.
    """
    body = live_client.get(CIVILIZATION, params={"offset": 900}).json()
    assert body["data_status"] == KnowledgeStatus.PARTIAL
    assert any(caveat["source"] == "pagination" for caveat in body["caveats"])
    sections = {section["section_kind"]: section for section in body["sections"]}
    assert sections[SectionKind.DATA]["returned"] == 0
    assert sections[SectionKind.DATA]["total_available"] == 22
    # 900 is inside 1,072, so this section is genuinely non-empty and keeps its total.
    # 1,072 before the round-three coverage rebuild. The attribution census gave
    # that build 13 more metrics to compute. This assertion exists to prove the
    # paging caveat reports the REAL total rather than the page, so the figure is
    # expected to track the metric layer -- re-derived, not loosened.
    assert sections[SectionKind.DERIVED_METRIC]["total_available"] == 1085
    assert sections[SectionKind.DERIVED_METRIC]["returned"] > 0


@pytest.mark.neo4j
def test_derived_metrics_carry_their_scope_note(live_client: TestClient) -> None:
    """Several say in as many words that a non-Rigvedic zero means an absent layer."""
    body = live_client.get(CIVILIZATION).json()
    section = next(
        section
        for section in body["sections"]
        if section["section_kind"] == SectionKind.DERIVED_METRIC
    )
    assert section["total_available"] and section["total_available"] > section["returned"]
    assert any(row["scope_note"] or row["interpretation"] for row in section["metric_rows"])


# ---------------------------------------------------------------------------
# Live: the remaining views, and the leak sweep
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_atharvaveda_concerns_separates_afflictions_from_threats(
    live_client: TestClient,
) -> None:
    """A demon is not a disease, and the kind is on the row rather than in the filter."""
    body = live_client.get(CONCERNS).json()
    assert body["concerns"]
    assert body["afflictions"]
    assert body["protection_and_treatment"]
    tiers = {row["tier"] for row in body["protection_and_treatment"]}
    assert len(tiers) > 1, "the concern predicates differ in tier and must show it"
    predicates = {row["predicate"] for row in body["protection_and_treatment"]}
    assert len(predicates) > 1
    assert "must not be summed" in " ".join(caveat["text"] for caveat in body["caveats"]) or any(
        "Do not sum" in caveat["text"] for caveat in body["caveats"]
    )


@pytest.mark.neo4j
def test_material_culture_reports_a_corpus_with_no_match_as_null(
    live_client: TestClient,
) -> None:
    """A per-entity breakdown never invents a zero for a corpus the alias missed."""
    body = live_client.get(MATERIAL, params={"category": "metals", "limit": 50}).json()
    assert body["rows"]
    nulls = [
        row
        for row in body["rows"]
        if any(row["by_veda"][veda] is None for veda in ("rv", "av", "yv", "sv"))
    ]
    assert nulls, "some metal is unmatched in some corpus, and that must be a null"
    for row in nulls:
        assert row["by_veda"]["status"] != KnowledgeStatus.SUPPORTED
        assert row["by_veda"]["note"]
        assert 0 not in {row["by_veda"][veda] for veda in ("rv", "av", "yv", "sv")}


@pytest.mark.neo4j
def test_material_culture_rows_carry_a_followable_product_id(live_client: TestClient) -> None:
    """F-14: an aggregate row must be followable to the entity it names.

    Both renderings of the same seven metals now carry keys. The row previously handed a
    client a display label and nothing to resolve it with, so `/insights/metals` and
    `/insights/material-culture?category=metals` described the same entities and only one
    of them could be followed to a detail view.

    Resolution is by display label, which is measured to be collision-free across all
    registry entities, and a label resolving to several entities or to none yields null
    rather than a guess -- an id field is the worst place to publish one.
    """
    body = live_client.get(MATERIAL, params={"category": "metals", "limit": 50}).json()
    assert body["rows"]
    for row in body["rows"]:
        assert row["entity_key"], row["label"]
        assert row["entity_key"].startswith("VG:")

    # The two renderings must agree on the key for every metal they share.
    grid = live_client.get(METALS).json()
    by_label = {r["metal"]: r["entity_key"] for r in grid["metals"]}
    for row in body["rows"]:
        assert row["entity_key"] == by_label[row["label"]], row["label"]


@pytest.mark.neo4j
def test_concern_rows_carry_a_followable_product_id(live_client: TestClient) -> None:
    """The same fix on the other surface that folds display labels into rows."""
    body = live_client.get(CONCERNS, params={"limit": 50}).json()
    for collection in ("concerns", "afflictions", "social_rites"):
        assert body[collection], collection
        assert all(row["entity_key"] for row in body[collection]), collection


@pytest.mark.neo4j
def test_every_ritual_collection_has_bounds_that_describe_itself(
    live_client: TestClient,
) -> None:
    """F-15: two collections, two blocks, each reporting its own length."""
    body = live_client.get(RITUALS).json()
    assert "pagination" not in body
    bounds = body["collections"]
    assert set(bounds) == {"objects", "rituals"}
    assert bounds["objects"]["returned"] == len(body["objects"]) == 15
    assert bounds["objects"]["total"] == 15
    assert not bounds["objects"]["has_more"]

    # The rite collection now overruns its page, which is the case this block was built for:
    # `returned` describes the page and `total` describes the collection, and one shared
    # block once reported returned=0 beside eight rites in the body.
    assert bounds["rituals"]["returned"] == len(body["rituals"])
    assert bounds["rituals"]["total"] == RITUAL_TOTAL
    assert bounds["rituals"]["returned"] < bounds["rituals"]["total"]
    assert bounds["rituals"]["has_more"], (
        "a truncated collection that does not say so reads as the whole collection"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (RITUALS, {"objects", "rituals"}),
        (CONCERNS, {"concerns", "afflictions", "protection_and_treatment", "social_rites"}),
        (FORMULAS, {"span_census", "widest_families", "reuse_witnesses"}),
    ],
)
def test_multi_collection_responses_bound_each_collection_separately(
    path: str, expected: set[str], live_client: TestClient
) -> None:
    body = live_client.get(path).json()
    assert "pagination" not in body
    assert set(body["collections"]) == expected
    for name, meta in body["collections"].items():
        assert meta["returned"] == len(body[name]), f"{path}:{name}"


@pytest.mark.neo4j
@pytest.mark.parametrize("path", (MATERIAL, RITUALS, CONCERNS, FORMULAS))
def test_paging_past_the_end_is_a_caveat_and_not_insufficient_evidence(
    path: str, live_client: TestClient
) -> None:
    """F-19: an offset overrun must not spend the knowledge vocabulary.

    ``INSUFFICIENT_EVIDENCE`` has a precise meaning in this product, and a client asking
    for page four million of a forty-row collection has not produced an evidence problem.
    The status keeps describing the collection; a caveat sourced ``pagination`` describes
    the page.
    """
    body = live_client.get(path, params={"limit": 5, "offset": 99_999_999}).json()
    assert body["data_status"] != KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert body["data_status"] == KnowledgeStatus.PARTIAL
    assert any(caveat["source"] == "pagination" for caveat in body["caveats"]), path
    overrun = next(caveat for caveat in body["caveats"] if caveat["source"] == "pagination")
    assert "past the end" in overrun["text"]
    # And the collection it describes is genuinely non-empty.
    totals = [meta["total"] for meta in body.get("collections", {}).values()] or [
        body["pagination"]["total"]
    ]
    assert any(total for total in totals)


@pytest.mark.neo4j
def test_formula_diffusion_returns_the_single_corpus_baseline(live_client: TestClient) -> None:
    """The single-corpus families are the baseline, so the census is not filtered to four."""
    body = live_client.get(FORMULAS).json()
    spans = {row["vedas_reached"]: row for row in body["span_census"]}
    assert set(spans) == {1, 2, 3, 4}
    assert spans[1]["cross_veda"] is False
    assert body["widest_families"]
    assert body["reuse_witnesses"]
    assert any("baseline" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.neo4j
@pytest.mark.parametrize("path", ALL_INSIGHTS)
def test_no_insight_body_leaks_internal_content(path: str, live_client: TestClient) -> None:
    """No diagnostic label, no build state, no Cypher, no connection detail."""
    body = live_client.get(path).text
    for token in FORBIDDEN_IN_BODY:
        assert token not in body, f"{path} leaked {token!r}"
    assert '"Internal"' not in body
    assert ":Internal" not in body
    assert "run_id" not in body
    assert "build_pass" not in body


@pytest.mark.neo4j
@pytest.mark.parametrize("path", ALL_INSIGHTS)
def test_every_insight_declares_a_cost_class(path: str, live_client: TestClient) -> None:
    """An aggregate exempt from the latency target must say that it is one."""
    body = live_client.get(path).json()
    assert body["cost_class"] in set(CostClass)
    assert body["cost_note"]
