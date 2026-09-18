"""What the cross-Veda surface says about granularity and about direction.

Two closure-test clauses live here.

GAP-CROSS_VEDA-004 asks that the pada layer's "RV-only reach is stated on the surface that
reports them". The matrix now publishes a measured granularity census, so a reader sees
VERSE and PADA as separate populations and sees which corpora each reaches. Before the pada
layer is imported the same statement says so, rather than describing edges that are not
there -- a sentence asserting a layer nobody built is the failure this repository has found
more than once.

GAP-CROSS_VEDA-001 asks that pairs carrying no directed reuse are typed. They used to read
NOT_ESTABLISHED_FOR_PAIR, which cannot distinguish "nobody built it" from "it was measured
and refused". A pair whose own edges carry a refusal status now reports a measured zero
with the measurement attached.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from vedagraph.api.models.insight import CrossVedaCellStatus

from .conftest import FakeRepository, build_client

CROSS_VEDA = "/api/v1/insights/cross-veda"

_GRANULARITY_NEEDLE = "coalesce(r.parallel_granularity, 'UNTYPED')"
_DIRECTION_NEEDLE = "r.cross_veda_direction_status IS NOT NULL"
_WORKS_NEEDLE = "MATCH (w:Work)"

#: The envelope refuses to construct without a corpus boundary per Veda, which is the point
#: of it: "1,844" published without "THIS IS NOT THE COMPLETE SAMAVEDA" is the product's
#: most misleading string. Scripted here so these tests exercise the matrix and not that.
_WORKS = [
    {
        "veda": veda,
        "work_id": f"VG:WORK:{veda}",
        "traditional_name": veda,
        "scope_honest_label": veda,
        "scope": "COMPLETE",
        "completeness": "COMPLETE",
        "excluded_corpora": [],
        "scope_source": "test",
    }
    for veda in ("RV", "SV", "YV", "AV")
]


def _client(script: dict[str, list[dict[str, Any]]]) -> TestClient:
    repository = FakeRepository({_WORKS_NEEDLE: _WORKS, **script})
    app, test_client = build_client(repository)
    test_client.__enter__()
    app.state.repository = repository
    return test_client


def _caveats(body: dict[str, Any]) -> str:
    return "\n".join(caveat["text"] for caveat in body["caveats"])


def test_with_no_pada_edges_the_surface_says_the_layer_is_absent() -> None:
    """GOOD -> PASS for the honest pre-import state."""
    client = _client(
        {
            _GRANULARITY_NEEDLE: [
                {"granularity": "VERSE", "edges": 6596, "vedas": ["RV", "AV", "SV", "YV"]}
            ]
        }
    )
    try:
        body = client.get(CROSS_VEDA).json()
    finally:
        client.__exit__(None, None, None)
    text = _caveats(body)
    assert "PARALLEL GRANULARITY" in text
    assert "VERSE 6,596 edges" in text
    assert "No quarter-verse (PADA) edge is present in this graph" in text
    assert "Rigveda only" in text


def test_with_pada_edges_the_surface_states_the_count_and_the_single_corpus_reach() -> None:
    """GAP-CROSS_VEDA-004's third clause, on the post-import state."""
    client = _client(
        {
            _GRANULARITY_NEEDLE: [
                {"granularity": "VERSE", "edges": 6596, "vedas": ["RV", "AV", "SV", "YV"]},
                {"granularity": "PADA", "edges": 4079, "vedas": ["RV"]},
            ]
        }
    )
    try:
        body = client.get(CROSS_VEDA).json()
    finally:
        client.__exit__(None, None, None)
    text = _caveats(body)
    assert "PADA 4,079 edges over RV" in text
    assert "VERSE 6,596 edges over RV/AV/YV/SV" in text, "corpus order, not sorted"
    assert "reaches the Rigveda only" in text
    assert "no other corpus in this graph carries a quarter-verse" in text.lower()
    assert "No quarter-verse (PADA) edge is present" not in text


def test_an_untyped_parallel_layer_is_reported_as_untyped_not_as_verse() -> None:
    """BAD -> FAIL. The granularity must be read, never assumed from the predicate."""
    client = _client(
        {_GRANULARITY_NEEDLE: [{"granularity": "UNTYPED", "edges": 6596, "vedas": ["RV"]}]}
    )
    try:
        body = client.get(CROSS_VEDA).json()
    finally:
        client.__exit__(None, None, None)
    text = _caveats(body)
    assert "UNTYPED 6,596 edges" in text
    assert "VERSE 6,596" not in text


def test_a_pair_with_no_directed_reuse_and_no_refusal_reads_not_established() -> None:
    """The pre-fix behaviour, kept as the control for the test below."""
    client = _client({})
    try:
        body = client.get(CROSS_VEDA).json()
    finally:
        client.__exit__(None, None, None)
    cells = [
        cell
        for row in body["pairs"]
        for cell in row["cells"]
        if cell["relationship_class"] == "REUSES_TEXT_FROM"
    ]
    assert cells
    assert all(cell["status"] != CrossVedaCellStatus.MEASURED_ZERO for cell in cells)


def test_a_measured_refusal_is_a_typed_zero_and_quotes_its_measurement() -> None:
    """GAP-CROSS_VEDA-001's third clause: a refusal is not the same shape as a gap."""
    client = _client(
        {
            _DIRECTION_NEEDLE: [
                {
                    "pair": "AV-SV",
                    "status": "REFUSED_MEDIATED_BY_THIRD_CORPUS",
                    "note": (
                        "96.1% of this pair's verses are counterparts of one and the same RV verse."
                    ),
                    "edges": 467,
                }
            ]
        }
    )
    try:
        body = client.get(CROSS_VEDA).json()
    finally:
        client.__exit__(None, None, None)
    by_pair = {
        row["pair"]: {cell["relationship_class"]: cell for cell in row["cells"]}
        for row in body["pairs"]
    }
    refused = by_pair["AV-SV"]["REUSES_TEXT_FROM"]
    assert refused["status"] == CrossVedaCellStatus.MEASURED_ZERO
    assert refused["edges"] == 0
    assert "REFUSED_MEDIATED_BY_THIRD_CORPUS" in refused["note"]
    assert "96.1%" in refused["note"]
    assert "measured refusal and not an unbuilt cell" in refused["note"]

    untouched = by_pair["RV-YV"]["REUSES_TEXT_FROM"]
    assert untouched["status"] != CrossVedaCellStatus.MEASURED_ZERO


@pytest.mark.parametrize("veda", ["AV", "SV", "YV"])
def test_the_pada_scope_statement_never_claims_a_second_corpus(veda: str) -> None:
    """The layer covers one corpus and must not be described as covering another."""
    from vedagraph.api.services.insight_service import PADA_GRANULARITY_SCOPE

    assert "Rigveda only" in PADA_GRANULARITY_SCOPE
    assert f"the {veda} " not in PADA_GRANULARITY_SCOPE


@pytest.mark.neo4j
def test_the_semantic_assertion_row_does_not_claim_the_layer_was_never_built(
    live_client: TestClient,
) -> None:
    """The row said NOT_BUILT -- "the layer does not exist anywhere in this graph" -- beside
    a measured total of 35,131 assertions in its own note. One cell, two contradictory
    claims, and the false one was the one a status chip renders.

    NOT_BUILT and CLASS_NOT_CROSS_VEDA are both empty cells and mean opposite things. The
    layer exists, reaches all four corpora, and still cannot enter a corpus pair, because an
    assertion is a predication about one passage rather than a relation between two. That is
    measured here rather than asserted: every assertion in the graph hangs off passages of a
    single Veda, so if one ever spanned two the status would be wrong and this fails.
    """
    body = live_client.get("/api/v1/insights/cross-veda").json()
    for pair_row in body["pairs"]:
        cell = next(
            c for c in pair_row["cells"] if c["relationship_class"] == "SEMANTIC_ASSERTION"
        )
        assert cell["status"] == "CLASS_NOT_CROSS_VEDA"
        assert cell["status"] != "NOT_BUILT"
        assert "every one of its assertions is Rigvedic" not in cell["note"]
        # The note must distinguish what the layer is, not just how big it is: a bare total
        # blends a model extraction and a rule over manual annotation into one figure.
        assert "model-assisted" in cell["note"]
        assert "reviewed by a human" in cell["note"]
        assert "Coverage is incomplete" in cell["note"]
        assert "by derivation" in cell["note"]

    view = next(
        c
        for c in body["relationship_classes"]
        if c["relationship_class"] == "SEMANTIC_ASSERTION"
    )
    assert view["population_status"] == "CLASS_NOT_CROSS_VEDA"
    assert view["population_status"] != "NOT_BUILT"
    # Stays 0: this field is the intra-corpus *relatedness* population the caveat
    # discloses, and the assertion layer's size belongs in the note, not in it.
    assert view["within_one_veda_edges"] == 0


@pytest.mark.neo4j
def test_no_semantic_assertion_spans_two_corpora(live_repository) -> None:
    """The measurement CLASS_NOT_CROSS_VEDA rests on, asserted separately from the copy.

    If an assertion is ever attached to passages of two Vedas, the class *can* enter a pair
    and the status above becomes the new false claim. This is the falsifier.
    """
    rows = live_repository.run(
        "MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->(s:SemanticAssertion) "
        "WITH s, count(DISTINCT p.veda) AS vedas WHERE vedas > 1 "
        "RETURN count(s) AS spanning"
    )
    assert rows[0]["spanning"] == 0


@pytest.mark.neo4j
def test_the_resemblance_row_is_still_genuinely_unbuilt(live_client: TestClient) -> None:
    """Guards the guard: the fix above must not have converted every empty cell.

    SEMANTIC_RESEMBLANCE really is NOT_BUILT -- no embedding, no vector, no asserted
    resemblance -- and a change that relabelled it too would have traded one false status
    for another.
    """
    body = live_client.get("/api/v1/insights/cross-veda").json()
    cell = next(
        c for c in body["pairs"][0]["cells"] if c["relationship_class"] == "SEMANTIC_RESEMBLANCE"
    )
    assert cell["status"] == "NOT_BUILT"
