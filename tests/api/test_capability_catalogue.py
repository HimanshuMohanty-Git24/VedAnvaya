"""The limits catalogue covers every dimension the benchmark grades NOT_ANSWERABLE.

GAP-PRODUCT_SURFACE-002. ``GET /api/v1/insights/capabilities`` published seven cards with
``total_available: 7`` against a frozen benchmark that grades twenty-one questions
NOT_ANSWERABLE. It said so -- "this catalogue is not exhaustive" -- which is the right
disclosure and still left a reader consulting it to find out whether a question is
answerable with an incomplete answer that correctly warned them it was incomplete.

Four things are asserted here, and the second is the one that matters most:

*The population is read from the artifact.* ``BENCHMARK_NOT_ANSWERABLE`` is a constant, so
it is checked against ``docs/reports/V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl`` rather than
remembered. A constant that drifts from the artifact it summarises is how a completeness
claim becomes false without anything failing.

*Every card is probed, and the probe is what grades it.* A card whose verdict is copied
from the frozen benchmark is a limitation with no measurement behind it, and three of these
dimensions have moved since the benchmark was frozen -- so a copied grade would publish a
limitation that no longer holds.

*Nothing is unpublished.* ``unpublished_not_answerable`` is empty, and it is derived from
the cards rather than asserted beside them.

*A missing card is caught.* The response model recomputes the published count, so dropping
a card fails rather than quietly shrinking the catalogue.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vedagraph.api.models.insight import (
    CapabilitiesResponse,
    CapabilityLimit,
    CapabilityVerdict,
    CostClass,
    KnowledgeStatus,
)
from vedagraph.api.services.capability_probes import (
    BENCHMARK_NOT_ANSWERABLE,
    PROBED_LIMIT_SPECS,
)

FROZEN_BENCHMARK = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reports"
    / "V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl"
)


def _benchmark_not_answerable() -> set[int]:
    """The NOT_ANSWERABLE question numbers, read off the frozen artifact."""
    numbers: set[int] = set()
    with open(FROZEN_BENCHMARK, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("verdict") == "NOT_ANSWERABLE":
                numbers.add(int(str(row["question_id"]).removeprefix("Q")))
    return numbers


def test_the_declared_population_matches_the_frozen_benchmark() -> None:
    """The constant is checked against the artifact, not against memory."""
    assert set(BENCHMARK_NOT_ANSWERABLE) == _benchmark_not_answerable()
    assert len(BENCHMARK_NOT_ANSWERABLE) == 21


def test_every_probe_spec_declares_measurements_that_say_what_they_mean() -> None:
    for spec in PROBED_LIMIT_SPECS:
        assert spec.measurements, spec.limit_id
        for name, means in spec.measurements:
            assert name and means, spec.limit_id
            # A measurement column the probe does not return would publish a silent None.
            assert name in spec.cypher, f"{spec.limit_id}: {name} is not in its own probe"
        assert spec.why({name: 0 for name, _ in spec.measurements}), spec.limit_id
        assert spec.what_this_is_not and spec.safe_alternative and spec.what_would_change_it


def test_dropping_a_card_fails_rather_than_shrinking_the_catalogue() -> None:
    """The BAD case. The published count is derived, so it cannot agree with a short list."""
    card = CapabilityLimit(
        limit_id="x",
        question_number=7,
        question="q",
        verdict=CapabilityVerdict.NOT_ANSWERABLE,
        benchmark_verdict=CapabilityVerdict.NOT_ANSWERABLE,
        data_status=KnowledgeStatus.NOT_BUILT,
        why="w",
        what_this_is_not="n",
    )
    with pytest.raises(ValidationError) as excinfo:
        CapabilitiesResponse(
            insight="capabilities",
            question="q",
            data_status=KnowledgeStatus.SUPPORTED,
            cost_class=CostClass.AGGREGATE,
            cost_note="n",
            vedas_reported=[],
            scope_statements=[],
            caveats=[],
            limits=[card],
            total_available=1,
            benchmark_not_answerable_total=21,
            benchmark_not_answerable_published=21,  # the lie: one card, twenty-one claimed
        )
    assert "NOT_ANSWERABLE benchmark verdict" in str(excinfo.value)


@pytest.mark.neo4j
def test_the_catalogue_covers_every_not_answerable_dimension(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/insights/capabilities").json()
    published = {
        limit["question_number"]
        for limit in body["limits"]
        if limit["benchmark_verdict"] == "NOT_ANSWERABLE"
    }
    assert published == set(BENCHMARK_NOT_ANSWERABLE)
    assert body["unpublished_not_answerable"] == []
    assert body["benchmark_not_answerable_total"] == len(BENCHMARK_NOT_ANSWERABLE)
    assert body["benchmark_not_answerable_published"] == len(BENCHMARK_NOT_ANSWERABLE)
    # total_available is the catalogue's own size, and it exceeds the NOT_ANSWERABLE
    # population by exactly the cards that are genuinely PARTIALLY_ANSWERABLE. Q25 is one:
    # a real, partial answer with its recall shortfall measured. Deleting it to make two
    # numbers equal would remove a truthful limitation.
    partial = [
        limit["question_number"]
        for limit in body["limits"]
        if limit["benchmark_verdict"] != "NOT_ANSWERABLE"
    ]
    assert body["total_available"] == len(published) + len(partial)
    assert body["total_available"] == len(body["limits"])


@pytest.mark.neo4j
def test_every_card_carries_a_reproducible_probe(live_client: TestClient) -> None:
    """A limit with no measurement is an assertion. Every card must carry one figure."""
    body = live_client.get("/api/v1/insights/capabilities").json()
    for limit in body["limits"]:
        measured = limit["measurements"]
        assert measured, limit["limit_id"]
        assert all(row["means"] for row in measured), limit["limit_id"]
        assert any(row["value"] is not None for row in measured), (
            f"{limit['limit_id']}: every measurement came back None, so the probe reached "
            "nothing and the card is an assertion rather than a measurement"
        )
        assert limit["why"] and limit["what_this_is_not"], limit["limit_id"]


@pytest.mark.neo4j
def test_a_card_whose_dimension_has_been_built_is_not_published_as_unbuilt(
    live_client: TestClient,
) -> None:
    """The stale-limitation guard, on the one dimension known to have moved.

    The benchmark graded Q7 NOT_ANSWERABLE on a measurement of zero typed reuse edges. The
    typology has since been built. Publishing the frozen grade would tell a reader the
    product cannot answer something it partly can, which is the same class of defect as a
    false finding and is what this whole audit exists to remove.
    """
    body = live_client.get("/api/v1/insights/capabilities", params={"question": 7}).json()
    card = body["limits"][0]
    typed = next(
        row for row in card["measurements"] if row["name"] == "edges_with_a_transformation_type"
    )
    assert typed["value"] and typed["value"] > 0
    assert card["benchmark_verdict"] == "NOT_ANSWERABLE"
    assert card["verdict"] == "PARTIALLY_ANSWERABLE"
    assert card["data_status"] == "PARTIAL"
    assert any("the graph has moved" in caveat["text"] for caveat in card["caveats"])


@pytest.mark.neo4j
def test_q23_no_longer_claims_no_partition_exists(live_client: TestClient) -> None:
    """A partition has been computed since this card was written; its wording was false.

    The card is still NOT_ANSWERABLE -- the partition carries no membership -- but for a
    different reason, and the old reason had become a false statement about the graph.
    """
    body = live_client.get("/api/v1/insights/capabilities", params={"question": 23}).json()
    card = body["limits"][0]
    assert card["verdict"] == "NOT_ANSWERABLE"
    assert "No community structure exists anywhere in this graph" not in card["why"]
    stored = next(
        row for row in card["measurements"] if row["name"] == "stored_community_partitions"
    )
    assert stored["value"] and stored["value"] > 0
    assigned = next(
        row for row in card["measurements"] if row["name"] == "deities_with_a_community_assignment"
    )
    assert assigned["value"] == 0


@pytest.mark.neo4j
@pytest.mark.parametrize("question", sorted(BENCHMARK_NOT_ANSWERABLE))
def test_each_not_answerable_question_is_individually_retrievable(
    live_client: TestClient, question: int
) -> None:
    response = live_client.get("/api/v1/insights/capabilities", params={"question": question})
    assert response.status_code == 200
    limits = response.json()["limits"]
    assert len(limits) == 1
    assert limits[0]["question_number"] == question
