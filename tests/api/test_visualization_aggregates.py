"""The three aggregates that unblocked three charts.

GAP-PRODUCT_SURFACE-003. ``docs/design/research/04-visualization-research.md`` named three
blockers, all three of them API omissions over data the graph already held:

* ``VIZ_BLOCKER_01`` -- dispersion could not be fetched. ``MAX_PAGE_SIZE = 200`` caps
  ``/devatas/{id}/passages``, so an Invocation Landscape for Indra was eighteen round trips
  and a caller who stopped early got a landscape that looked sparse rather than truncated.
* ``VIZ_BLOCKER_02`` -- no per-book aggregate. ``named_by_veda`` is per-*Veda* only, and the
  spec's own warning is the one this file enforces: do **not** build the breakdown
  client-side from paged rows, because the cap truncates silently.
* ``VIZ_BLOCKER_03`` -- no deity-by-metre aggregate, deferred because the metre layer
  reaches two corpora of four and "the matrix would be two-thirds hatched -- honest, but
  thin".

The assertions that matter are not "the endpoint returns 200". They are that a book the
deity is absent from is *present* as a measured zero, that the corpora the metre layer does
not reach are *present* as ``NOT_BUILT`` rows, and that dispersion returns more positions
than the page cap would ever have allowed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vedagraph.api.config import MAX_PAGE_SIZE

INDRA = "VG:DEVATA:INDRAH"
BY_BOOK = f"/api/v1/insights/devatas/{INDRA}/by-book"
BY_METRE = f"/api/v1/insights/devatas/{INDRA}/by-metre"
DISPERSION = f"/api/v1/insights/devatas/{INDRA}/dispersion"


# ---------------------------------------------------------------------------
# VIZ_BLOCKER_02 -- the per-book aggregate
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_every_book_of_every_corpus_is_returned(live_client: TestClient) -> None:
    """74 books, not 74-minus-the-empty-ones.

    The BAD case this catches is the natural query: group the deity's mentions by book and
    return the groups. That returns only the books the deity appears in, and a heatmap built
    from it draws no cell where the deity is absent -- which reads as "no data" rather than
    as "measured, and zero".
    """
    body = live_client.get(BY_BOOK).json()
    books = body["books"]
    by_veda: dict[str, int] = {}
    for row in books:
        by_veda[row["veda"]] = by_veda.get(row["veda"], 0) + 1
    # The Work's direct children: ten mandalas, twenty kandas, forty adhyayas, four arcikas.
    assert by_veda == {"RV": 10, "AV": 20, "YV": 40, "SV": 4}
    assert len(books) == 74

    zeros = [row for row in books if row["count"] == 0]
    assert zeros, "no book has a zero, so the zero path is untested on this data"
    for row in zeros:
        assert row["status"] == "MEASURED_ZERO"
        assert row["note"] and "measured zero" in row["note"]


@pytest.mark.neo4j
def test_every_book_row_carries_its_own_denominator(live_client: TestClient) -> None:
    """Books differ in size by an order of magnitude; a raw-count heatmap is a size map."""
    body = live_client.get(BY_BOOK).json()
    for row in body["books"]:
        assert row["denominator"] > 0, row["book_key"]
        assert row["count"] <= row["denominator"], row["book_key"]
        assert row["per_1000"] is not None, row["book_key"]
    sizes = {row["book_key"]: row["denominator"] for row in body["books"]}
    assert max(sizes.values()) > 10 * min(sizes.values())


@pytest.mark.neo4j
def test_the_per_book_total_reconciles_with_the_per_veda_figure(live_client: TestClient) -> None:
    """The reconciliation that would catch a containment walk that missed a book."""
    books = live_client.get(BY_BOOK).json()
    insight = live_client.get(f"/api/v1/insights/devatas/{INDRA}").json()
    assert books["total"] == insight["named_by_veda"]["total_mantras"]
    per_veda: dict[str, int] = {}
    for row in books["books"]:
        per_veda[row["veda"]] = per_veda.get(row["veda"], 0) + row["count"]
    measured = {
        veda.upper(): value
        for veda, value in insight["named_by_veda"]["by_veda"].items()
        if isinstance(value, dict) and value.get("count") is not None
    }
    for veda, cell in measured.items():
        assert per_veda[veda] == cell["count"], veda


@pytest.mark.neo4j
def test_the_per_book_breakdown_exceeds_what_paging_could_have_assembled(
    live_client: TestClient,
) -> None:
    """The blocker itself: a client-side roll-up would have truncated at the page cap."""
    body = live_client.get(BY_BOOK).json()
    assert body["total"] > MAX_PAGE_SIZE


# ---------------------------------------------------------------------------
# VIZ_BLOCKER_03 -- deity x metre, with two thirds of it typed
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_the_corpora_the_metre_layer_misses_are_returned_not_omitted(
    live_client: TestClient,
) -> None:
    """The whole reason this endpoint is worth serving at all.

    A matrix with two corpora silently missing is read as a matrix of two corpora. The rows
    are present, ``NOT_BUILT``, and carry a note saying the Samaveda's verses are metrical
    whatever this graph knows about them.
    """
    body = live_client.get(BY_METRE).json()
    covered = set(body["vedas_with_a_metre_layer"])
    assert covered, "no corpus has a metre layer, which would make this test vacuous"
    uncovered = {"RV", "AV", "YV", "SV"} - covered
    unbuilt = {cell["veda"] for cell in body["cells"] if cell["status"] == "NOT_BUILT"}
    assert unbuilt == uncovered
    for cell in body["cells"]:
        if cell["status"] == "NOT_BUILT":
            assert cell["count"] is None, cell["veda"]
            assert cell["note"] and "unbuilt rather than zero" in cell["note"]
    assert set(body["coverage"]["vedas_not_covered"]) == uncovered
    # And the contradiction guard from GAP-PRODUCT_SURFACE-001 still holds here.
    assert not (set(body["coverage"]["vedas_in_scope"]) & uncovered)


@pytest.mark.neo4j
def test_every_measured_metre_cell_names_its_metre(live_client: TestClient) -> None:
    body = live_client.get(BY_METRE).json()
    measured = [cell for cell in body["cells"] if cell["status"] == "MEASURED"]
    assert measured
    for cell in measured:
        assert cell["metre_key"] and cell["metre_label"], cell
        assert cell["count"] and cell["count"] > 0
        assert cell["veda"] in set(body["vedas_with_a_metre_layer"])


# ---------------------------------------------------------------------------
# VIZ_BLOCKER_01 -- dispersion above the page cap
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_dispersion_is_fetchable_for_a_deity_with_more_than_two_hundred_passages(
    live_client: TestClient,
) -> None:
    """The closure test, as written. One request, no page, no cap.

    Indra's Rigvedic attestation alone is more than eleven times ``MAX_PAGE_SIZE``.
    """
    body = live_client.get(DISPERSION).json()
    assert body["total_positions"] > MAX_PAGE_SIZE
    rv = body["by_veda"]["RV"]
    assert len(rv["positions"]) > MAX_PAGE_SIZE
    # The route it replaces, for contrast: the same deity, capped and paged.
    paged = live_client.get(
        f"/api/v1/devatas/{INDRA}/passages", params={"limit": MAX_PAGE_SIZE}
    ).json()
    assert len(paged["items"]) <= MAX_PAGE_SIZE
    assert len(rv["positions"]) > len(paged["items"])


@pytest.mark.neo4j
def test_positions_are_ordinals_inside_their_corpus_and_are_sorted(
    live_client: TestClient,
) -> None:
    body = live_client.get(DISPERSION).json()
    for veda, series in body["by_veda"].items():
        positions = series["positions"]
        assert positions == sorted(positions), veda
        assert len(positions) == len(set(positions)), veda
        if positions:
            assert 1 <= positions[0]
            assert positions[-1] <= series["denominator"], veda


@pytest.mark.neo4j
def test_dispersion_counts_reconcile_with_the_deity_insight(live_client: TestClient) -> None:
    """A position list that lost entries would be a sparser landscape with no error."""
    dispersion = live_client.get(DISPERSION).json()
    insight = live_client.get(f"/api/v1/insights/devatas/{INDRA}").json()
    assert dispersion["total_positions"] == insight["named_by_veda"]["total_mantras"]
    for veda, cell in insight["named_by_veda"]["by_veda"].items():
        if not isinstance(cell, dict) or cell.get("count") is None:
            continue
        assert len(dispersion["by_veda"][veda.upper()]["positions"]) == cell["count"], veda


@pytest.mark.neo4j
def test_an_empty_corpus_is_a_measured_zero_and_not_an_absent_layer(
    live_client: TestClient,
) -> None:
    """A deity named in one corpus only still gets four typed series."""
    listing = live_client.get("/api/v1/devatas?limit=100").json()
    for row in listing["items"]:
        body = live_client.get(f"/api/v1/insights/devatas/{row['id']}/dispersion").json()
        empty = [series for series in body["by_veda"].values() if not series["positions"]]
        if not empty:
            continue
        for series in empty:
            assert series["status"] == "MEASURED_ZERO"
            assert series["note"] and "measured zero" in series["note"]
        assert set(body["by_veda"]) == {"RV", "AV", "YV", "SV"}
        return
    pytest.skip("no deity in the first page is absent from a corpus")


# ---------------------------------------------------------------------------
# All three carry the envelope the rest of the API carries
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize("route", [BY_BOOK, BY_METRE, DISPERSION])
def test_each_aggregate_labels_its_cost_and_carries_its_scope(
    live_client: TestClient, route: str
) -> None:
    body = live_client.get(route).json()
    assert body["cost_class"] == "AGGREGATE"
    assert body["cost_note"]
    assert {statement["veda"] for statement in body["scope_statements"]} >= set(
        body["vedas_reported"]
    )
    assert body["caveats"]


@pytest.mark.neo4j
@pytest.mark.parametrize("route", [BY_BOOK, BY_METRE, DISPERSION])
def test_the_deity_gate_refuses_a_non_deity_on_every_new_route(
    live_client: TestClient, route: str
) -> None:
    """The dog. One gate, and these routes call it rather than reimplementing it."""
    response = live_client.get(route.replace(INDRA, "VG:DEVATA:SUNAH"))
    assert response.status_code == 404
