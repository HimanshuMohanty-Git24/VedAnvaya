"""The generic entity surface: thirty-one types, one contract each.

The most valuable test here is
:func:`test_every_registered_type_resolves_against_the_live_graph`. The registry claims an
identity property per type and they are not uniform -- ``family_key`` for a seer family,
``formula_id`` for a formula, ``predicate`` for an action predicate, ``entity_key`` for
most of the rest. A wrong entry there does not throw: it returns null ids in the list and
404s the detail view while reporting that the entity does not exist, which is a wrong
answer said confidently. So every type is listed and one row of each is opened.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository
from tests.api.test_devatas import assert_no_internals
from vedagraph.api.models.entity import ENTITY_TYPES
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

AFFLICTION_TOTAL = 26
THREAT_TOTAL = 8
PATHOGEN_TOTAL = 2
CONDITION_TOTAL = AFFLICTION_TOTAL + THREAT_TOTAL + PATHOGEN_TOTAL

FEVER = "VG:CONCEPT:TAKMAN-FEVER"
DEMON = "VG:CONCEPT:RAKSAS-DEMON"
VASISTHA_RISHI = "VG:RISHI:MAITRAVARUNIRVASISTHAH"
ADITI_RISHI = "VG:RISHI:ADITIH"
YV_SEER = "VG:RISHI:YV:PRAJAPATI-2F3C"
ANGIRASA = "VG:RISHI_FAMILY:ANGIRASA"


# ---------------------------------------------------------------------------
# Type resolution
# ---------------------------------------------------------------------------


def test_unknown_type_is_400_listing_the_alternatives_not_an_empty_200(
    client: TestClient,
) -> None:
    """ "No such type" and "that type is empty" are different answers."""
    response = client.get("/api/v1/entities/nonsense_type")
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "UNKNOWN_ENTITY_TYPE"
    assert "rishi" in body["hint"] and "condition" in body["hint"]


@pytest.mark.parametrize("slug", ["devata", "devatas", "deity", "deities", "god"])
def test_deities_are_refused_by_the_generic_surface(client: TestClient, slug: str) -> None:
    """Serving a deity here would serve it without the population contract."""
    response = client.get(f"/api/v1/entities/{slug}")
    assert response.status_code == 400
    body = response.json()
    assert "/api/v1/devatas" in body["detail"] or "/api/v1/devatas" in (body["hint"] or "")
    assert "dog" in body["detail"], "the reason must be stated, not just the redirect"


def test_kind_is_refused_on_a_type_that_has_no_kind(client: TestClient) -> None:
    response = client.get("/api/v1/entities/plant", params={"kind": "AFFLICTION"})
    assert response.status_code == 400
    assert "condition" in response.json()["hint"]


def test_unknown_kind_is_422(client: TestClient) -> None:
    response = client.get("/api/v1/entities/condition", params={"kind": "DISEASE"})
    assert response.status_code == 422


def test_graph_outage_is_503(down_client: TestClient) -> None:
    for path in (
        "/api/v1/entities",
        "/api/v1/entities/rishi",
        f"/api/v1/entities/condition/{FEVER}",
    ):
        response = down_client.get(path)
        assert response.status_code == 503, path
        assert_no_internals(response.text)


def test_empty_type_page_cannot_claim_supported(client: TestClient) -> None:
    body = client.get("/api/v1/entities/plant").json()
    assert body["items"] == []
    assert body["data_status"] != "SUPPORTED" or body["caveats"]
    assert any("filter result" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.parametrize(
    "malicious",
    ["MATCH (n) DETACH DELETE n", "') RETURN 1 //", "{ } ( ) ~ * : ^ ] ["],
)
def test_entity_filters_are_parameterised(
    client: TestClient, fake_repository: FakeRepository, malicious: str
) -> None:
    client.get("/api/v1/entities/concept", params={"name": malicious})
    client.get(f"/api/v1/entities/concept/{malicious}")
    assert fake_repository.calls
    assert malicious not in fake_repository.query_text
    assert malicious.lower() not in fake_repository.query_text.lower()


def test_an_unknown_type_never_reaches_a_query(
    client: TestClient, fake_repository: FakeRepository
) -> None:
    """The 400 must be raised before any Cypher runs, or the label was interpolated."""
    client.get("/api/v1/entities/Devata%20WHERE%20true")
    assert not fake_repository.calls


# ---------------------------------------------------------------------------
# The registry against the graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_every_registered_type_resolves_against_the_live_graph(
    live_client: TestClient,
) -> None:
    """Each of the 31 types lists rows with real ids, and one of each opens.

    A wrong identity property in the registry produces null ids and a 404 on a node that
    exists. Six of the thirty-one types key on something other than ``entity_key``, so a
    convention would have been wrong six times.
    """
    inventory = live_client.get("/api/v1/entities").json()
    counts = {row["slug"]: row["count"] for row in inventory["types"]}
    assert set(counts) == set(ENTITY_TYPES), "the inventory and the registry disagree"

    for slug in sorted(ENTITY_TYPES):
        params: dict[str, Any] = {"limit": 3}
        if slug == "condition":
            params["kind"] = "ANY"
        listing = live_client.get(f"/api/v1/entities/{slug}", params=params)
        assert listing.status_code == 200, slug
        body = listing.json()
        assert body["pagination"]["total"] == counts[slug], slug
        assert body["items"], f"{slug} has {counts[slug]} nodes but listed none"
        for row in body["items"]:
            assert row["id"], f"{slug} returned a row with no id -- wrong id_property"
            assert row["display_label"]
        first = body["items"][0]["id"]
        detail = live_client.get(f"/api/v1/entities/{slug}/{first}")
        assert detail.status_code == 200, f"{slug}/{first} did not open"
        assert detail.json()["id"] == first


@pytest.mark.neo4j
def test_no_entity_response_leaks_an_internal(live_client: TestClient) -> None:
    for path, params in (
        ("/api/v1/entities", {}),
        ("/api/v1/entities/rishi", {"limit": 50}),
        (f"/api/v1/entities/rishi/{VASISTHA_RISHI}", {}),
        ("/api/v1/entities/condition", {"kind": "ANY"}),
        (f"/api/v1/entities/concept/{FEVER}", {}),
        ("/api/v1/entities/formula", {"limit": 20}),
    ):
        response = live_client.get(path, params=params)
        assert response.status_code == 200, path
        assert_no_internals(response.text)


@pytest.mark.neo4j
@pytest.mark.parametrize("slug", ["rishi", "concept", "condition", "chandas", "plant"])
def test_every_list_row_agrees_with_its_own_profile(live_client: TestClient, slug: str) -> None:
    """One number, one source. A row and its own detail view cannot disagree.

    They did, for every type: the list read a coalesce over registry statistics and the
    profile counted the edges, so 501 of 729 seer rows disagreed with the graph and
    Atharvan read 121 in the list against 1,282 in its profile. Sweeping five types keeps
    the fix from being a per-type patch.
    """
    params: dict[str, Any] = {"limit": 25}
    if slug == "condition":
        params["kind"] = "ANY"
    rows = live_client.get(f"/api/v1/entities/{slug}", params=params).json()["items"]
    assert rows, f"{slug} listed nothing"
    disagreements = []
    for row in rows:
        profile = live_client.get(f"/api/v1/entities/{slug}/{row['id']}").json()
        if row["passage_count"] != profile["passage_count"]:
            disagreements.append((row["id"], row["passage_count"], profile["passage_count"]))
    assert not disagreements, (
        f"{len(disagreements)} {slug} rows disagree with their own profile: {disagreements[:3]}"
    )


@pytest.mark.neo4j
def test_no_list_row_reports_a_bare_zero_where_the_graph_has_edges(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """A bare 0 in a field named passage_count is the shape this product refuses."""
    truth = {
        str(row["k"]): int(row["c"])
        for row in live_repository.run(
            "MATCH (p:Passage)-[:HAS_RISHI]->(x:Rishi) "
            "RETURN x.entity_key AS k, count(DISTINCT p) AS c"
        )
    }
    rows: list[dict[str, Any]] = []
    for offset in (0, 200, 400, 600):
        rows.extend(
            live_client.get(
                "/api/v1/entities/rishi", params={"limit": 200, "offset": offset}
            ).json()["items"]
        )
    assert len(rows) == 729
    assert not [r for r in rows if r["passage_count"] == 0], "passage_count must be null, never 0"
    false_zeros = [
        (r["id"], truth[r["id"]])
        for r in rows
        if r["passage_count"] is None and truth.get(r["id"], 0) > 0
    ]
    assert not false_zeros, f"nulls where the graph has edges: {false_zeros[:3]}"
    vasistha = next(r for r in rows if r["id"] == VASISTHA_RISHI)
    assert vasistha["passage_count"] == truth[VASISTHA_RISHI] == 836


@pytest.mark.neo4j
def test_every_rishi_row_carries_the_seer_typing_its_caveat_promises(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """113 of 729 are not seers, and the list is where a client picks one."""
    truth = {
        str(row["k"]): row["s"]
        for row in live_repository.run("MATCH (x:Rishi) RETURN x.entity_key AS k, x.is_seer AS s")
    }
    rows: list[dict[str, Any]] = []
    for offset in (0, 200, 400, 600):
        rows.extend(
            live_client.get(
                "/api/v1/entities/rishi", params={"limit": 200, "offset": offset}
            ).json()["items"]
        )
    assert len(rows) == 729
    for row in rows:
        assert row["is_seer"] is truth[row["id"]], row["id"]
        if row["is_seer"] is False:
            assert row["non_seer_kind"], f"{row['id']} is not a seer and does not say why"
            assert "not a seer" in (row["subtitle"] or ""), row["id"]
    assert sum(1 for r in rows if r["is_seer"] is False) == 113


@pytest.mark.neo4j
def test_is_seer_is_null_and_not_false_on_a_type_that_has_no_seers(
    live_client: TestClient,
) -> None:
    """A river is not "not a seer"; the question does not apply to it."""
    for row in live_client.get("/api/v1/entities/river", params={"limit": 10}).json()["items"]:
        assert row["is_seer"] is None
        assert row["non_seer_kind"] is None


# ---------------------------------------------------------------------------
# Conditions: an affliction question must not be answered with demons
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_condition_defaults_to_affliction_and_excludes_threats(
    live_client: TestClient,
) -> None:
    default = live_client.get("/api/v1/entities/condition", params={"limit": 50}).json()
    assert default["pagination"]["total"] == AFFLICTION_TOTAL
    assert {row["kind"] for row in default["items"]} == {"AFFLICTION"}
    labels = {row["display_label"] for row in default["items"]}
    assert not any("rakṣas" in label or "demon" in label for label in labels)
    assert any("AFFLICTION" in caveat["text"] for caveat in default["caveats"])
    assert any("category error" in caveat["text"] for caveat in default["caveats"])


@pytest.mark.neo4j
def test_the_kind_is_on_every_row_and_not_only_in_the_filter(live_client: TestClient) -> None:
    """The response_model must not drop ``kind``; that dropped field is the whole guard."""
    everything = live_client.get(
        "/api/v1/entities/condition", params={"kind": "ANY", "limit": 50}
    ).json()
    assert everything["pagination"]["total"] == CONDITION_TOTAL
    kinds = [row["kind"] for row in everything["items"]]
    assert all(kinds), "a row without a kind lets a demon be read as a disease"
    assert set(kinds) == {"AFFLICTION", "THREAT", "PATHOGEN_OR_CAUSE"}
    assert kinds.count("THREAT") == THREAT_TOTAL
    assert kinds.count("PATHOGEN_OR_CAUSE") == PATHOGEN_TOTAL


@pytest.mark.neo4j
def test_threat_and_pathogen_remain_reachable_by_name(live_client: TestClient) -> None:
    for kind, expected in (("THREAT", THREAT_TOTAL), ("PATHOGEN_OR_CAUSE", PATHOGEN_TOTAL)):
        body = live_client.get(
            "/api/v1/entities/condition", params={"kind": kind, "limit": 50}
        ).json()
        assert body["pagination"]["total"] == expected
        assert {row["kind"] for row in body["items"]} == {kind}


@pytest.mark.neo4j
def test_the_fever_network_is_reachable_and_carries_its_kind(live_client: TestClient) -> None:
    fever = live_client.get(f"/api/v1/entities/condition/{FEVER}").json()
    assert fever["condition_kind"] == "AFFLICTION"
    assert fever["type"] == "CONDITION"
    assert fever["passages_by_veda"]["av"], "takman is Atharvavedic; the AV count is missing"
    assert fever["co_mentioned"], "the fever neighbourhood returned nothing"
    labels = {ref["display_label"] for ref in fever["co_mentioned"]}
    assert any("balāsa" in label or "kāsa" in label for label in labels), (
        "the measured Atharvavedic fever neighbourhood should reach balasa and cough"
    )
    assert any("co_mentioned" in caveat["text"] for caveat in fever["caveats"])
    assert any("no causal" in caveat["text"] for caveat in fever["caveats"])
    demon = live_client.get(f"/api/v1/entities/condition/{DEMON}").json()
    assert demon["condition_kind"] == "THREAT"


@pytest.mark.neo4j
def test_a_null_per_veda_count_says_it_is_not_a_zero(live_client: TestClient) -> None:
    fever = live_client.get(f"/api/v1/entities/condition/{FEVER}").json()
    by_veda = fever["passages_by_veda"]
    assert any(by_veda[key] is None for key in ("rv", "sv", "yv", "av"))
    assert "not a zero" in by_veda["note"]


# ---------------------------------------------------------------------------
# Seers
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_a_non_seer_is_not_presented_as_a_seer(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/entities/rishi/{ADITI_RISHI}").json()
    seer = body["seer"]
    assert seer is not None
    assert seer["is_seer"] is False
    assert seer["non_seer_kind"] == "DEITY"
    assert any("THIS IS NOT A SEER" in caveat["text"] for caveat in seer["caveats"])
    assert any("not a reason to render it as a deity" in c["text"] for c in seer["caveats"])
    assert body["type"] == "RISHI", "a rishi node must never be typed DEVATA"


@pytest.mark.neo4j
def test_the_rishi_list_exposes_is_seer_for_the_whole_non_seer_stratum(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    measured = live_repository.run(
        "MATCH (rs:Rishi) WHERE rs.is_seer = false RETURN rs.non_seer_kind AS kind, count(*) AS n"
    )
    kinds = {str(row["kind"]): int(row["n"]) for row in measured}
    assert kinds == {
        "DEITY": 58,
        "ABSTRACTION": 21,
        "MYTHIC_BEING": 13,
        "DEITY_GROUP": 11,
        "PLANT_OR_ANIMAL": 5,
        "COLLECTIVE": 3,
        "OBJECT": 2,
    }
    assert sum(kinds.values()) == 113
    assert any(
        "113 of the 729" in caveat["text"]
        for caveat in live_client.get("/api/v1/entities/rishi", params={"limit": 5}).json()[
            "caveats"
        ]
    )


@pytest.mark.neo4j
def test_strict_and_inherited_seer_attribution_are_never_summed(
    live_client: TestClient,
) -> None:
    """Two seers whose mixes are opposite, so a blended figure would be visibly wrong."""
    vasistha = live_client.get(f"/api/v1/entities/rishi/{VASISTHA_RISHI}").json()["seer"]
    assert vasistha["passages_source_stated"] == 9
    assert vasistha["passages_container_inherited"] == 827
    rv = next(row for row in vasistha["passages_by_veda"] if row["veda"] == "RV")
    assert rv["count"] == 836 == 9 + 827
    assert any("NOT SUMMED" in caveat["text"] for caveat in vasistha["caveats"])

    yajurvedic = live_client.get(f"/api/v1/entities/rishi/{YV_SEER}").json()["seer"]
    assert yajurvedic["passages_container_inherited"] is None, (
        "every Yajurvedic seer edge is source-stated; an inherited count would be a defect"
    )
    assert yajurvedic["passages_source_stated"]


@pytest.mark.neo4j
def test_the_samaveda_seer_layer_is_reported_as_absent_and_not_as_zero(
    live_client: TestClient,
) -> None:
    seer = live_client.get(f"/api/v1/entities/rishi/{VASISTHA_RISHI}").json()["seer"]
    samaveda = next(row for row in seer["passages_by_veda"] if row["veda"] == "SV")
    assert samaveda["count"] is None
    assert samaveda["status"] == "NOT_BUILT"
    assert any("NO seer apparatus" in caveat["text"] for caveat in seer["caveats"])


@pytest.mark.neo4j
def test_a_seers_deities_are_population_filtered_and_carry_their_precision(
    live_client: TestClient,
) -> None:
    seer = live_client.get(f"/api/v1/entities/rishi/{VASISTHA_RISHI}").json()["seer"]
    assert seer["deities"], "Vasistha is ascribed 836 mantras; no deity was returned"
    for ref in seer["deities"]:
        assert ref["type"] == "DEVATA"
        assert not ref["id"].startswith("VG:RISHI:")
        assert ref["attribution_precision"] in {"PER_PASSAGE", "CONTAINER_INHERITED"}
        assert ref["evidence_basis"] in {"SOURCE_STATED", "CONTAINER_INHERITED"}


@pytest.mark.neo4j
def test_a_seer_family_lists_its_members(live_client: TestClient) -> None:
    listing = live_client.get(f"/api/v1/entities/rishi_family/{ANGIRASA}")
    assert listing.status_code == 200
    body = listing.json()
    assert body["type"] == "RISHI_FAMILY"
    assert body["id"] == ANGIRASA
    member_ids = {ref["id"] for ref in body["neighbours"]}
    assert member_ids, "the family returned no members"
    assert all(identifier.startswith("VG:RISHI:") for identifier in member_ids)


# ---------------------------------------------------------------------------
# Measured figures that are not numbers
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_bridge_centrality_is_not_built_and_is_not_reported_as_zero(
    live_client: TestClient,
) -> None:
    """The frozen graph stores prose in ``centrality_bridging``. It must not become 0.0."""
    body = live_client.get(f"/api/v1/entities/condition/{FEVER}").json()
    centrality = body["centrality"]
    assert centrality is not None
    assert centrality["degree"] is not None
    assert centrality["bridging"] is None
    assert centrality["bridging_status"] == "NOT_BUILT"
    assert "no community structure" in (centrality["bridging_note"] or "")
    statuses = {row["dimension"] for row in body["dimension_status"]}
    assert "centrality.bridging" in statuses


@pytest.mark.neo4j
def test_a_measured_recall_is_a_field_and_not_a_caveat(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    row = live_repository.run_one(
        "MATCH (n:SocialRite) WHERE n.strict_recall_against_locus IS NOT NULL "
        "RETURN n.entity_key AS key"
    )
    assert row is not None, "no social rite carries a measured recall figure"
    body = live_client.get(f"/api/v1/entities/social_rite/{row['key']}").json()
    recall = body["recall"]
    assert recall is not None
    assert recall["strict_recall_against_locus"] is not None
    assert recall["locus_book"] and recall["locus_book_passages"]


@pytest.mark.neo4j
def test_entity_endpoints_answer_inside_the_latency_budget(live_client: TestClient) -> None:
    cases: list[tuple[str, dict[str, Any]]] = [
        ("/api/v1/entities", {}),
        ("/api/v1/entities/rishi", {"limit": 25}),
        ("/api/v1/entities/condition", {}),
        ("/api/v1/entities/formula", {"limit": 25}),
        (f"/api/v1/entities/rishi/{VASISTHA_RISHI}", {}),
        (f"/api/v1/entities/condition/{FEVER}", {}),
    ]
    timings: dict[str, float] = {}
    for path, params in cases:
        live_client.get(path, params=params)
        best = min(_elapsed_ms(live_client, path, params) for _ in range(3))
        timings[f"{path} {params}"] = best
    slow = {key: round(ms, 1) for key, ms in timings.items() if ms > 300}
    assert not slow, f"over the 300ms budget: {slow}"
    ordered = sorted(timings.values())
    assert ordered[len(ordered) // 2] < 150, f"median over budget: {timings}"


def _elapsed_ms(client: TestClient, path: str, params: dict[str, Any]) -> float:
    started = time.perf_counter()
    response = client.get(path, params=params)
    assert response.status_code == 200
    return (time.perf_counter() - started) * 1000
