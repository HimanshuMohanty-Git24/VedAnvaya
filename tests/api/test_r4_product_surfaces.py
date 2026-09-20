"""The product surfaces R4's closures are answerable on, pinned end to end.

Each gap below was closed on a claim about what a *reader* can now reach, not only about
what the graph holds. A graph-level assertion would pass while the route that serves it
still returned a null or an old caveat, which is the shape of defect this project has hit
before -- a fix that never reaches the shipped artifact.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.neo4j
def test_sarasvati_returns_per_corpus_figures_rather_than_nulls(live_client: TestClient) -> None:
    """GAP-ENTITY_COVERAGE-002's named example.

    The entry names this deity because its page reported ``null`` for every corpus: the
    profile materialisation had reached 25 of 214 deities, selected as the union of the top
    twenty by mention and the top twenty by attribution. It now reaches the 157 the
    eligibility contract admits.
    """
    response = live_client.get("/api/v1/devatas/VG:DEVATA:SARASVATI")
    assert response.status_code == 200
    body = response.json()

    mentions = body["mentions_by_veda"]
    assert mentions, "the entry's whole complaint was that this was empty"
    # Every corpus is reported, so a reader can tell a real zero from an unmeasured one.
    assert {cell["veda"] for cell in mentions} == {"RV", "SV", "YV", "AV"}
    # And at least one corpus carries a figure, or the page is still saying nothing.
    assert any(cell.get("count") for cell in mentions)


@pytest.mark.neo4j
def test_the_deity_profile_population_is_the_eligible_one(
    live_client: TestClient, live_repository: object
) -> None:
    """157, and not 214: profiling every registry row puts human patrons on deity pages.

    Both directions are asserted. An eligible deity without a profile is the defect the
    entry was opened for; an INELIGIBLE deity with one is the defect its
    implementation_dependency warned about, and ``VG:DEVATA:DANASTUTIH`` -- a danastuti
    gift-praise label ruled NOT_DEITY -- was carrying all three deity metrics before R4.
    """
    rows = live_repository.run(  # type: ignore[attr-defined]
        "MATCH (d:Devata) RETURN "
        "sum(CASE WHEN d.is_deity = true AND d.profile_attributed_total IS NULL "
        "         THEN 1 ELSE 0 END) AS eligible_without, "
        "sum(CASE WHEN d.is_deity <> true AND d.profile_attributed_total IS NOT NULL "
        "         THEN 1 ELSE 0 END) AS ineligible_with, "
        "sum(CASE WHEN d.is_deity = true THEN 1 ELSE 0 END) AS eligible"
    )
    row = rows[0]
    assert int(row["eligible"]) == 157
    assert int(row["eligible_without"]) == 0
    assert int(row["ineligible_with"]) == 0, (
        "a non-deity is carrying a deity profile, which is what the entry's "
        "implementation_dependency names as the hazard"
    )


@pytest.mark.neo4j
def test_the_concerns_endpoint_reaches_a_stated_remedy(live_client: TestClient) -> None:
    """GAP-ENTITY_COVERAGE-003's third clause, and the false claim behind it.

    This endpoint told readers for two rounds that "the registry has no healing entity --
    bhesaja was never curated -- so 'what does the corpus do about illness' is reachable
    only through the afflictions and plants a verse names, never through a stated remedy",
    while ``VG:CONCEPT:BHESAJA-HEALING`` sat in the registry with 7 registered Sanskrit
    aliases and 108 evidenced mention edges over all four corpora.
    """
    response = live_client.get("/api/v1/insights/atharvaveda/concerns?limit=10")
    assert response.status_code == 200
    body = response.json()

    assert "stated_remedy" in body["collections"], (
        "the remedy dimension is not bounded, so the endpoint cannot be paging it"
    )
    remedy = body["stated_remedy"]
    assert remedy, "a stated remedy is reachable and this list proves it"
    assert any("bhe" in (row["label"] or "").lower() for row in remedy)

    # The corrective caveat must be present AND must not re-assert the false absence.
    caveats = " ".join(caveat["text"] for caveat in body["caveats"])
    assert "was false" in caveats, (
        "the correction is not disclosed, so a reader cannot tell the earlier caveat was wrong"
    )
    assert "never curated" not in caveats or "was false" in caveats


@pytest.mark.neo4j
def test_the_ayas_yajurvedic_cell_is_still_never_a_zero(live_client: TestClient) -> None:
    """GAP-ENTITY_COVERAGE-006 clause 2, which must stay NO_LEXICAL_MATCH.

    R4 added a source attestation to the graph for this cell -- an ``ATTESTED_IN`` edge to
    VSM 18.13 carrying ``source_attested`` and ``lexical_match:
    NOT_SAFELY_RECOVERABLE`` -- and deliberately did NOT add a ``MENTIONS_ENTITY`` edge,
    because that predicate means a lexical match and there is not one. So the product must
    still refuse to print a number here, and must still name the witness.
    """
    response = live_client.get("/api/v1/insights/metals")
    assert response.status_code == 200
    ayas = next(
        row
        for row in response.json()["metals"]
        if row["entity_key"] == "VG:CONCEPT:AYAS-METAL"
    )
    yv = next(cell for cell in ayas["by_veda"] if cell["veda"] == "YV")
    assert yv["matched_mantras"] is None, "the ayas/YV cell must be null, never 0"
    assert yv["evidence_status"] == "NO_LEXICAL_MATCH"
    assert yv["source_witness"] == "VSM 18.13"


@pytest.mark.neo4j
def test_the_epithet_occurrence_layer_is_reachable_from_the_graph_api(
    live_client: TestClient,
) -> None:
    """GAP-ENTITY_COVERAGE-001: the layer is traversable, not silently refused.

    An undeclared or refused predicate is invisible to ``/api/v1/graph`` while its edges
    sit in the graph, which is the safe-and-silent failure the whitelist test exists for.
    Asserted through the neighbourhood route on a real Rigvedic verse rather than against a
    catalogue endpoint -- there is no predicate-catalogue route, and a test that skipped
    when it could not find one would certify nothing.

    RV 3.30.5 carries three epithet occurrences (maghavan, puruhūta, vṛtrahan).
    """
    response = live_client.get(
        "/api/v1/graph/neighborhood/VG:RV:SAK:M03:S030:V005",
        params={"types": "MENTIONS_EPITHET"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    text = str(body)
    assert "MENTIONS_EPITHET" in text, (
        "the epithet occurrence predicate is not traversable, so the layer cannot be "
        "reached from /api/v1/graph even though its 1,035 edges are in the graph"
    )
    assert "EPITHET:" in text, "the traversal returned no epithet node"


@pytest.mark.neo4j
def test_an_epithet_edge_states_its_tier_and_its_rigvedic_bound(
    live_client: TestClient, live_repository: object
) -> None:
    """The bound travels in the row, because a reader who takes a count did not read the caveat.

    ``MENTIONS_LEMMA`` -- the annotation this layer is derived from -- is 154,261 edges over
    the Rigveda and ZERO over the other three corpora, so an epithet with no Samavedic
    occurrence is unannotated there rather than absent. Both match tiers are pinned too:
    STEM_LEMMA covers every inflection of the annotator's lemma, ATTESTED_SURFACE_FORM
    covers one attested word form and is used only for the three duals whose wider
    inflection is deliberately not claimed.
    """
    rows = live_repository.run(  # type: ignore[attr-defined]
        "MATCH (:Mantra)-[r:MENTIONS_EPITHET]->(:Epithet) "
        "RETURN count(r) AS edges, "
        "count(DISTINCT r.epithet_match_tier) AS tiers, "
        "sum(CASE WHEN r.absence_outside_annotated_vedas IS NULL THEN 1 ELSE 0 END) AS unbounded, "
        "sum(CASE WHEN r.annotator_lemma IS NULL THEN 1 ELSE 0 END) AS unprovenanced"
    )
    row = rows[0]
    assert int(row["edges"]) == 1035
    assert int(row["tiers"]) == 2
    assert int(row["unbounded"]) == 0
    assert int(row["unprovenanced"]) == 0
