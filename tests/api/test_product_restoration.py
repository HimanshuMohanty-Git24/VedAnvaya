"""The regressions the owner reported after the completeness campaign, pinned.

Each test here exists because a specific thing was observed to be wrong in the product, or
because the measurement that disproved it should not have to be repeated by hand next time.
They assert invariants and minimums rather than exact counts: the graph is allowed to grow,
and a test that fails when a deity gains a relationship is a test that gets deleted.

Live tests, because every one of these is a statement about the real graph. A fake
repository returning a hand-built row would pass all of them while telling us nothing --
which is the shape of this project's oldest recurring defect.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

#: Subjects whose search behaviour the owner named directly.
CANONICAL_SUBJECTS = [
    ("Indra", "VG:DEVATA:INDRAH", "DEVATA"),
    ("Varuna", "VG:DEVATA:VARUNAH", "DEVATA"),
    ("Agni", "VG:DEVATA:AGNIH", "DEVATA"),
    ("Soma", "VG:DEVATA:SOMAH", "DEVATA"),
]


@pytest.mark.neo4j
@pytest.mark.parametrize(("query", "stable_id", "expected_type"), CANONICAL_SUBJECTS)
def test_a_named_deity_is_returned_as_a_deity(
    live_client: TestClient, query: str, stable_id: str, expected_type: str
) -> None:
    """The canonical deity node must come back typed as one, and near the top.

    Reported symptom: a search for "Indra" showed nearly every result labelled RITE,
    including rows that were plainly not rites. Whatever produced that, the invariant it
    violated is this one, and it is cheap to hold.
    """
    body = live_client.get("/api/v1/search", params={"q": query, "limit": 25}).json()
    items = body["items"]
    match = next((item for item in items if item["stable_id"] == stable_id), None)
    assert match is not None, f"{stable_id} is not in the first 25 results for {query!r}"
    assert match["type"] == expected_type, (
        f"{stable_id} came back as {match['type']}, not {expected_type}"
    )
    rank = items.index(match)
    assert rank < 5, f"{stable_id} ranked {rank + 1} for its own name"


@pytest.mark.neo4j
def test_search_results_are_not_all_one_type(live_client: TestClient) -> None:
    """A page of results that is entirely one type is the reported failure's signature.

    Not an assertion that any *particular* mix appears -- that would pin the ranking. Only
    that a query matching deities, seers and formulae does not come back as a single kind.
    """
    body = live_client.get("/api/v1/search", params={"q": "indra", "limit": 25}).json()
    types = {item["type"] for item in body["items"]}
    assert len(types) > 1, f"every result for 'indra' came back as {types}"
    assert "DEVATA" in types, f"no deity among the results for 'indra': {sorted(types)}"


@pytest.mark.neo4j
def test_a_seer_is_returned_as_a_seer(live_client: TestClient) -> None:
    """RISHI must survive to the caller for at least one real, well-attested seer."""
    body = live_client.get(
        "/api/v1/search", params={"q": "vasistha", "limit": 25, "type": "RISHI"}
    ).json()
    items = body["items"]
    assert items, "no seer matched 'vasistha'"
    assert all(item["type"] == "RISHI" for item in items), (
        f"a RISHI-filtered page returned {sorted({i['type'] for i in items})}"
    )


@pytest.mark.neo4j
def test_every_public_entity_type_resolves_to_its_own_surface(live_client: TestClient) -> None:
    """Enumerate the type vocabulary and open each one, rather than sampling it.

    This project has twice certified an absence by grepping for the value it expected
    instead of enumerating the field's value space. The index names every public type and
    each must answer; a type that 404s or 500s is a type whose badges, search filter and
    profile route nobody has ever exercised.
    """
    index = live_client.get("/api/v1/entities").json()
    assert index["types"], "the entity index named no types at all"

    failures: list[str] = []
    for entry in index["types"]:
        response = live_client.get(
            f"/api/v1/entities/{entry['slug']}", params={"limit": 1}
        )
        if response.status_code != 200:
            failures.append(f"{entry['type']} -> HTTP {response.status_code}")
            continue
        body = response.json()
        rows = body.get("items", [])
        if entry["count"] > 0 and not rows:
            failures.append(f"{entry['type']} claims {entry['count']} members and returned none")
            continue
        for row in rows:
            declared = row.get("type") or row.get("entity_type")
            if declared is not None and declared != entry["type"]:
                failures.append(f"{entry['type']} returned a row typed {declared}")
                break
    assert not failures, "entity types that do not resolve to their own surface: " + "; ".join(
        failures
    )


@pytest.mark.neo4j
@pytest.mark.parametrize("stable_id", ["VG:DEVATA:INDRAH", "VG:DEVATA:VARUNAH"])
def test_a_major_deity_has_a_rich_typed_neighbourhood(
    live_client: TestClient, stable_id: str
) -> None:
    """Reported symptom: focusing Indra yielded about one useful connection.

    Three things are asserted, and the third is the one that would have caught a collapse
    that the first two survive: more than one connected subject, more than one relationship
    type, and connected subjects of more than one kind. A neighbourhood of four hundred
    verses all joined by MENTIONS_DEVATA passes a naive count and is still the failure the
    owner described.
    """
    response = live_client.get(
        f"/api/v1/graph/neighborhood/{stable_id}", params={"depth": 1, "limit": 200}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    nodes = body.get("nodes", [])
    edges = body.get("relationships", body.get("edges", []))
    assert len(nodes) > 1, f"{stable_id} reached {len(nodes)} nodes"
    assert len(edges) > 1, f"{stable_id} reached {len(edges)} relationships"

    predicates = {edge.get("type") or edge.get("relationship_type") for edge in edges}
    predicates.discard(None)
    assert len(predicates) > 1, (
        f"{stable_id}'s whole neighbourhood is one relationship type: {predicates}"
    )

    kinds = {node.get("type") or node.get("entity_type") for node in nodes}
    kinds.discard(None)
    assert len(kinds) > 1, f"{stable_id} is connected to only one kind of thing: {kinds}"


@pytest.mark.neo4j
def test_the_completeness_endpoint_serves_every_field_the_product_reads(
    live_client: TestClient,
) -> None:
    """The endpoint exists, and it carries the fields a page would otherwise render empty.

    It did not exist on the running server when this pass began -- the route had been added
    one commit earlier -- so the frontend served a frozen literal to every reader instead,
    with nothing on any page saying so. The first assertion is that it answers at all.
    """
    response = live_client.get("/api/v1/completeness")
    assert response.status_code == 200, response.text
    body = response.json()

    for field in ("as_of_date", "total_canonical_mantras", "truth_summary", "corpora"):
        assert field in body, f"/completeness does not serve {field}"

    summed = sum(corpus["canonical_mantras"] for corpus in body["corpora"])
    assert body["total_canonical_mantras"] == summed, (
        f"the stated total {body['total_canonical_mantras']} is not the sum of its corpora {summed}"
    )

    for corpus in body["corpora"]:
        item = body["translations"]["by_veda"].get(corpus["veda"])
        if item is None:
            continue
        assert item["has_own_dedicated_english"] == (item["dedicated_english"] > 0), (
            f"{corpus['veda']} reports has_own_dedicated_english="
            f"{item['has_own_dedicated_english']} against {item['dedicated_english']} of its own"
        )
