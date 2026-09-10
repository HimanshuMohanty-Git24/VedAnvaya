"""The eight modelled rites, and the emptiness that must not read as completeness.

Two properties are asserted here that no amount of documentation could enforce. First, the
step list is empty for seven of the eight rites and that emptiness must be a
``dimension_status`` row saying NOT_BUILT -- elaborate procedure is Brahmana and Sutra
material, and 3 ``HAS_STEP`` edges exist in the whole graph. Second, a list with eight rows
in it reads as a taxonomy of eight unless the rows say otherwise, so
``inventory_coverage`` is on every row and ``coverage_statement`` on every profile.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository
from tests.api.test_devatas import KNOWN_NON_DEITY_LABELS, assert_no_internals
from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

RITUAL_TOTAL = 8
HAS_STEP_TOTAL = 3
SOMA_PRESSING = "VG:CONCEPT:SOMA-PRESSING"
SAUTRAMANI = "VG:CONCEPT:SAUTRAMANI"


# ---------------------------------------------------------------------------
# Contract, offline
# ---------------------------------------------------------------------------


def test_unknown_ritual_is_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/rituals/{SOMA_PRESSING}")
    assert response.status_code == 404
    assert "GET /api/v1/rituals" in response.json()["hint"]


def test_empty_ritual_page_cannot_claim_supported(client: TestClient) -> None:
    body = client.get("/api/v1/rituals").json()
    assert body["items"] == []
    assert body["data_status"] == "PARTIAL"
    assert any("NOT A TAXONOMY" in caveat["text"] for caveat in body["caveats"])


def test_limit_above_the_maximum_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/rituals", params={"limit": MAX_PAGE_SIZE + 1}).status_code == 422


def test_graph_outage_is_503(down_client: TestClient) -> None:
    for path in ("/api/v1/rituals", f"/api/v1/rituals/{SOMA_PRESSING}"):
        response = down_client.get(path)
        assert response.status_code == 503
        assert_no_internals(response.text)


def test_ritual_ids_are_parameterised(client: TestClient, fake_repository: FakeRepository) -> None:
    malicious = "x'}) DETACH DELETE (n) RETURN 1"
    client.get(f"/api/v1/rituals/{malicious}")
    assert fake_repository.calls
    assert malicious not in fake_repository.query_text
    assert fake_repository.all_parameters.get("id") == malicious


# ---------------------------------------------------------------------------
# Live
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_all_eight_rites_are_listed_and_each_row_states_the_bound(
    live_client: TestClient,
) -> None:
    body = live_client.get("/api/v1/rituals").json()
    assert body["pagination"]["total"] == RITUAL_TOTAL
    assert len(body["items"]) == RITUAL_TOTAL
    assert body["data_status"] == "PARTIAL"
    for row in body["items"]:
        assert "NOT A TAXONOMY" in row["inventory_coverage"], (
            "the bound must be on the row, because a list of eight implies a taxonomy"
        )
        assert row["id"] and row["display_label"]
        assert row["step_count"] is not None


@pytest.mark.neo4j
def test_only_the_soma_pressing_has_steps_and_the_rest_say_why_not(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    measured = live_repository.run_one("MATCH ()-[h:HAS_STEP]->() RETURN count(h) AS n")
    assert measured is not None and int(measured["n"]) == HAS_STEP_TOTAL, (
        "the graph's step layer has changed size; re-read it before trusting this test"
    )

    pressing = live_client.get(f"/api/v1/rituals/{SOMA_PRESSING}").json()
    assert len(pressing["steps"]) == HAS_STEP_TOTAL
    assert [step["order"] for step in pressing["steps"]] == [1, 2, 3]
    assert all(step["description"] for step in pressing["steps"]), (
        "a step's order needs its stated evidence, not just an ordinal"
    )
    assert not any(row["dimension"] == "steps" for row in pressing["dimension_status"])

    for row in live_client.get("/api/v1/rituals").json()["items"]:
        if row["id"] == SOMA_PRESSING:
            continue
        profile = live_client.get(f"/api/v1/rituals/{row['id']}").json()
        assert profile["steps"] == []
        statuses = {entry["dimension"]: entry for entry in profile["dimension_status"]}
        assert "steps" in statuses, f"{row['id']} returned a bare empty step list"
        assert statuses["steps"]["status"] == "NOT_BUILT"
        assert "Brahmana" in statuses["steps"]["note"]


@pytest.mark.neo4j
def test_every_profile_carries_the_coverage_statement(live_client: TestClient) -> None:
    for row in live_client.get("/api/v1/rituals").json()["items"]:
        profile = live_client.get(f"/api/v1/rituals/{row['id']}").json()
        assert "NOT A TAXONOMY" in profile["coverage_statement"]
        assert "TIER_D" in profile["coverage_statement"]
        assert profile["caveats"], f"{row['id']} carried no caveat"
        assert profile["data_status"] == "PARTIAL"


@pytest.mark.neo4j
def test_invoked_deities_pass_the_population_contract(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """A rite must not list a human patron among the gods it invokes."""
    invoked = live_repository.run(
        "MATCH (:Ritual)-[:INVOKES_DEVATA]->(dv:Devata) RETURN count(*) AS n"
    )
    assert int(invoked[0]["n"]) == 16, "the invocation layer has changed size"
    for row in live_client.get("/api/v1/rituals").json()["items"]:
        profile = live_client.get(f"/api/v1/rituals/{row['id']}").json()
        for ref in profile["devatas"]:
            assert ref["type"] == "DEVATA"
            assert ref["display_label"] not in KNOWN_NON_DEITY_LABELS
    assert any(
        live_client.get(f"/api/v1/rituals/{row['id']}").json()["devatas"]
        for row in live_client.get("/api/v1/rituals").json()["items"]
    ), "no rite returned an invoked deity, so the filter is being tested against nothing"


@pytest.mark.neo4j
def test_thin_apparatus_is_reported_as_uncurated_rather_than_absent(
    live_client: TestClient,
) -> None:
    profile = live_client.get(f"/api/v1/rituals/{SAUTRAMANI}").json()
    dimensions = {entry["dimension"]: entry for entry in profile["dimension_status"]}
    assert dimensions, "a rite with no apparatus returned no explanation for it"
    for entry in dimensions.values():
        assert entry["status"] in {"NOT_BUILT", "INSUFFICIENT_EVIDENCE"}
        assert "curated" in entry["note"] or "Brahmana" in entry["note"]


@pytest.mark.neo4j
def test_described_in_passages_are_capped_with_the_true_total_beside_them(
    live_client: TestClient,
) -> None:
    profile = live_client.get(f"/api/v1/rituals/{SOMA_PRESSING}").json()
    assert profile["passage_count"] is not None
    assert len(profile["passages"]) <= profile["passage_count"]
    assert profile["mention_count"], "the soma pressing is lexically mentioned; count is 0"
    for ref in profile["passages"]:
        assert ref["type"] == "PASSAGE"


@pytest.mark.neo4j
def test_no_ritual_response_leaks_an_internal(live_client: TestClient) -> None:
    for path in ("/api/v1/rituals", f"/api/v1/rituals/{SOMA_PRESSING}"):
        response = live_client.get(path)
        assert response.status_code == 200
        assert_no_internals(response.text)


@pytest.mark.neo4j
def test_ritual_endpoints_answer_inside_the_latency_budget(live_client: TestClient) -> None:
    cases: list[tuple[str, dict[str, Any]]] = [
        ("/api/v1/rituals", {}),
        (f"/api/v1/rituals/{SOMA_PRESSING}", {}),
    ]
    timings = {}
    for path, params in cases:
        live_client.get(path, params=params)
        timings[path] = min(_elapsed_ms(live_client, path, params) for _ in range(3))
    slow = {key: round(ms, 1) for key, ms in timings.items() if ms > 300}
    assert not slow, f"over the 300ms budget: {slow}"


def _elapsed_ms(client: TestClient, path: str, params: dict[str, Any]) -> float:
    started = time.perf_counter()
    response = client.get(path, params=params)
    assert response.status_code == 200
    return (time.perf_counter() - started) * 1000
