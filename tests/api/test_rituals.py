"""The modelled rites, and the emptiness that must not read as completeness.

Three properties are asserted here that no amount of documentation could enforce.

First, the two step layers stay separate. ``steps`` is what a Samhita text numbers in its own
words -- 3 such edges in the whole graph -- and ``procedure`` is what a sutra prints. Summing
them would claim procedural coverage the Samhita layer does not have.

Second, ``procedure`` stays grouped by source work. ``step_position`` is an ordinal within one
work, and 2,666 of the 3,121 steps share a position with another step of the same rite, so a
flat ordered list would compose eight independent sequences into one procedure nobody
recorded.

Third, a list reads as a taxonomy unless the rows say otherwise, so ``inventory_coverage`` is
on every row and ``coverage_statement`` on every profile -- with the figures measured per
request, because a number typed into prose is the one nothing checks. This suite is how that
was found: it asserted eight rites, the import made it 103, and the failure is what sent the
endpoint back to be re-derived.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, UntracedBlock
from tests.api.test_devatas import KNOWN_NON_DEITY_LABELS, assert_no_internals
from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

#: Measured, not assumed. Every rite in the inventory has at least one step on one layer or
#: the other, which is why the total and the procedure count move together.
RITUAL_TOTAL = 103
#: Steps a Samhita text numbers in its own words. This one has not moved and should not: the
#: import deliberately chose HAS_RITUAL_STEP over widening HAS_STEP, because widening it
#: would change what an existing predicate means.
HAS_STEP_TOTAL = 3
#: Sutra-attested procedural steps, and the works they come from. None of the 11 works has a
#: node in the graph -- work_key is a foreign key to a record nobody imported.
PROCEDURE_STEP_TOTAL = 3121
PROCEDURE_WORKS = 11
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
def test_every_rite_is_listed_and_each_row_states_the_bound(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """The bound is on the row, and both step counts are too.

    ``step_count`` alone read as "this rite has no recorded steps" for 92 rites that hold
    3,121 sutra-attested ones between them, so the row carries both figures or neither is
    interpretable.
    """
    measured = live_repository.run_one("MATCH (r:Ritual) RETURN count(r) AS n")
    assert measured is not None and int(measured["n"]) == RITUAL_TOTAL, (
        "the rite inventory has changed size; re-derive the caveats before trusting this "
        "suite, and do not simply raise the constant"
    )

    body = live_client.get(f"/api/v1/rituals?limit={MAX_PAGE_SIZE}").json()
    assert body["pagination"]["total"] == RITUAL_TOTAL
    assert body["data_status"] == "PARTIAL"
    for row in body["items"]:
        assert "NOT A TAXONOMY" in row["inventory_coverage"], (
            "the bound must be on the row, because the length of a list implies a taxonomy"
        )
        assert row["id"] and row["display_label"]
        assert row["step_count"] is not None
        assert row["procedure_step_count"] is not None, (
            "a row reporting only Samhita steps says 0 for a rite with 227 sutra steps"
        )
    assert sum(row["procedure_step_count"] for row in body["items"]) == PROCEDURE_STEP_TOTAL


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

    for row in live_client.get(f"/api/v1/rituals?limit={MAX_PAGE_SIZE}").json()["items"]:
        if row["id"] == SOMA_PRESSING:
            continue
        profile = live_client.get(f"/api/v1/rituals/{row['id']}").json()
        assert profile["steps"] == []
        statuses = {entry["dimension"]: entry for entry in profile["dimension_status"]}
        assert "steps" in statuses, f"{row['id']} returned a bare empty step list"
        assert statuses["steps"]["status"] == "NOT_BUILT"
        # The note must send the reader to the layer that DOES cover this rite. Saying only
        # that the Samhita numbers no steps, while 3,121 sutra steps sit one field away,
        # is a true sentence that leaves a false impression.
        assert "procedure" in statuses["steps"]["note"], (
            f"{row['id']}: an empty Samhita step list must point at `procedure`"
        )


@pytest.mark.neo4j
def test_every_profile_carries_the_coverage_statement(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/rituals?limit={MAX_PAGE_SIZE}").json()
    for row in body["items"][:12]:
        profile = live_client.get(f"/api/v1/rituals/{row['id']}").json()
        assert "NOT A TAXONOMY" in profile["coverage_statement"]
        assert "TIER_D" in profile["coverage_statement"]
        assert profile["caveats"], f"{row['id']} carried no caveat"
        assert profile["data_status"] == "PARTIAL"


@pytest.mark.neo4j
def test_the_coverage_statement_figures_are_measured_not_typed(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """Every number in the statement must be the graph's, checked against the graph.

    This is the guard for the defect that produced this whole change. The statement was a
    literal string asserting "EIGHT MODELLED RITES" and it went on asserting it after the
    inventory became 103, because nothing compared the prose to the graph. It is now built
    from measured arguments, and this test is what makes that hold.
    """
    statement = live_client.get("/api/v1/rituals").json()["items"][0]["inventory_coverage"]
    rites = live_repository.run_one("MATCH (r:Ritual) RETURN count(r) AS n")
    samhita = live_repository.run_one("MATCH ()-[h:HAS_STEP]->() RETURN count(h) AS n")
    sutra = live_repository.run_one("MATCH ()-[h:HAS_RITUAL_STEP]->() RETURN count(h) AS n")
    assert rites is not None and samhita is not None and sutra is not None

    assert f"{int(rites['n'])} RITES" in statement
    assert f"{int(samhita['n'])} numbered steps" in statement
    assert f"{int(sutra['n']):,} steps" in statement
    # The two layers must not be summed anywhere in the sentence.
    assert str(int(samhita["n"]) + int(sutra["n"])) not in statement.replace(",", "")


@pytest.mark.neo4j
def test_procedure_stays_grouped_by_source_and_never_flattens(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """One flat ordered list would assert a sequence that does not exist.

    ``step_position`` is an ordinal within one work. A rite drawing on eleven sutras has
    eleven sequences each numbered from 1, and 2,666 of the 3,121 steps share a position
    with another step of the same rite. Rendering them as one list would compose eleven
    independent accounts into a procedure nobody recorded, so the grouping is the claim.
    """
    collisions = live_repository.run_one(
        "MATCH (r:Ritual)-[h:HAS_RITUAL_STEP]->() "
        "WITH r, h.step_position AS p, count(*) AS c WHERE c > 1 "
        "RETURN count(*) AS pairs"
    )
    assert collisions is not None and int(collisions["pairs"]) > 0, (
        "if positions no longer collide within a rite, re-read the staging before "
        "concluding a flat list is now safe"
    )

    profile = live_client.get("/api/v1/rituals/VG:CONCEPT:YAJNA-SACRIFICE").json()
    assert len(profile["procedure"]) == PROCEDURE_WORKS
    assert profile["procedure_step_count"] == 227

    for source in profile["procedure"]:
        assert source["work_key"] and source["work_label"]
        assert source["source_type"] in {"SRAUTASUTRA", "GRHYASUTRA"}
        assert source["anchoring_basis"], "a source must say why its steps attach to the rite"
        positions = [step["position"] for step in source["steps"]]
        assert len(positions) == len(set(positions)), (
            f"{source['work_key']} repeats a position inside one work, so the grouping is "
            "not by the thing that makes positions unique"
        )
        for step in source["steps"]:
            assert step["text"], "a step that is only a citation is a locator, not a step"
            assert step["order_completeness"] in {
                "PARTIAL_STATED_POSITIONS",
                "CONTIGUOUS_PRINTED_RUN",
            }

    statuses = {entry["dimension"]: entry for entry in profile["dimension_status"]}
    assert statuses["procedure"]["status"] == "PARTIAL"
    assert "do not compose" in statuses["procedure"]["note"]
    assert "no node in this graph" in statuses["procedure"]["note"], (
        "the cited works are foreign keys to records nobody imported, and a client "
        "following work_key has to be told there is nothing to follow"
    )


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


#: An EMPTY dimension must name the KIND of gap it has, not merely report emptiness. One of
#: these words is what separates "nobody curated this" from "the rite did not have one".
#:
#: A vocabulary rather than a single keyword, because the first version required the literal
#: "Brahmana" and so failed when the steps note was re-worded -- the keyword was standing in
#: for the property.
GAP_VOCABULARY = ("uncurated", "unbuilt", "staged sources", "not held", "not imported")

#: A PARTIAL dimension is a different obligation. It HAS content, so naming a gap says
#: nothing useful; what it owes the reader is the limit of what it holds. Keeping these apart
#: matters: folding `procedure` into the gap rule would have been satisfied by adding the
#: word "uncurated" to a layer holding 3,121 real steps.
LIMIT_VOCABULARY = ("do not compose", "without printing the run", "not a complete")


@pytest.mark.neo4j
def test_thin_apparatus_is_reported_as_uncurated_rather_than_absent(
    live_client: TestClient,
) -> None:
    profile = live_client.get(f"/api/v1/rituals/{SAUTRAMANI}").json()
    dimensions = {entry["dimension"]: entry for entry in profile["dimension_status"]}
    assert dimensions, "a rite with no apparatus returned no explanation for it"
    for name, entry in dimensions.items():
        assert entry["status"] in {"NOT_BUILT", "INSUFFICIENT_EVIDENCE", "PARTIAL"}
        note = entry["note"]
        if entry["status"] == "PARTIAL":
            assert any(word in note for word in LIMIT_VOCABULARY), (
                f"the {name} note reports a partial layer without saying what bounds it: "
                f"{note!r}"
            )
            continue
        assert any(word in note for word in GAP_VOCABULARY), (
            f"the {name} note reports an absence without naming what kind: {note!r}"
        )
        assert ", not " in note or " rather than " in note, (
            f"the {name} note must contrast the gap with the conclusion a reader would "
            f"otherwise draw, which is the whole job of this field: {note!r}"
        )


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
def test_ritual_endpoints_answer_inside_the_latency_budget(
    live_client: TestClient, untraced_measurement: UntracedBlock
) -> None:
    """Every ritual endpoint under 300ms. Warmed, best of three.

    The budget is read with the coverage tracer paused; see the
    ``untraced_measurement`` fixture for why that is not cosmetic.
    """
    cases: list[tuple[str, dict[str, Any]]] = [
        ("/api/v1/rituals", {}),
        (f"/api/v1/rituals/{SOMA_PRESSING}", {}),
    ]
    timings = {}
    for path, params in cases:
        # Traced, and deliberately outside the block below: the warm call is what keeps
        # these routes in the coverage report.
        live_client.get(path, params=params)
        with untraced_measurement():
            timings[path] = min(_elapsed_ms(live_client, path, params) for _ in range(3))
    slow = {key: round(ms, 1) for key, ms in timings.items() if ms > 300}
    assert not slow, f"over the 300ms budget: {slow}"


def _elapsed_ms(client: TestClient, path: str, params: dict[str, Any]) -> float:
    started = time.perf_counter()
    response = client.get(path, params=params)
    assert response.status_code == 200
    return (time.perf_counter() - started) * 1000
