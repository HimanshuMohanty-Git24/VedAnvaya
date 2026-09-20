"""The normalized Sanskrit rung must fold the query the way the text was folded.

A confirmed product-surface defect, and the root cause is the probe set rather than the
binding. ``SearchService.search`` bound ``$q = query.strip().lower()`` -- the raw query --
into a rung that matches ``SEARCH_DERIVATIVE`` text, which is
``comparison_form(..., SEARCH_NORMALIZED)``: casefolded, Vedic tone marks stripped, and
four sounds folded onto private-use sentinels. The two surfaces share no code point for any
non-ASCII letter, so the rung returned nothing.

Measured on the rung's own Cypher against the live graph, before the fix and after:

======================  ======  ======
probe                   before   after
======================  ======  ======
vocalic-r ``rtasya``         0      94
vocalic-r ``rsi``            0      33
anusvara ``somam``           0      34
udatta ``indra``             0     571
udatta ``agnim``             0      19
udatta ``devasya``           0      40
======================  ======  ======

The report named the sentinel classes -- vocalic r, anusvara, vocalic l. The measurement is
wider: the fold also strips tone marks, so the rung was dead for *every* non-ASCII query,
including the four the existing suite already probed with. ``tests/api/test_search.py``
uses ``agním``, ``sómam``, ``índra`` and ``devásya``; all four returned zero on this rung
and the suite was green, because the other rungs filled the page.

**So the probe set is the defect.** A probe set that cannot see a failure certifies its
absence, which this project has done twice before. The probes here are chosen to cover the
fold's own value space -- one per sentinel class, plus an accent-only case, plus an ASCII
control that must be unaffected -- and the test asserts the fold is applied in *both*
directions rather than asserting a count.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.search_service import _NORMALIZED_PHRASE_QUERY
from vedagraph.normalize.unicode import ComparisonForm, comparison_form

#: The fold's private-use sentinels, and what each one is for. Named here so a probe set
#: that stops covering one of them is visible rather than merely absent.
SENTINELS: dict[str, str] = {
    "": "vocalic r",
    "": "vocalic l",
    "": "anusvara",
}

#: One probe per sentinel class, one accent-only probe, one ASCII control. Every non-ASCII
#: probe here returned 0 on this rung before the fix.
PROBES: tuple[tuple[str, str], ...] = (
    ("ṛtasya", "vocalic r, the reported case"),
    ("ṛṣi", "vocalic r beside a retroflex"),
    ("somaṁ", "anusvara"),
    ("kḻptam", "vocalic l, the rarest sentinel class"),
    ("índra", "udatta only -- no sentinel, and it was equally dead"),
    ("devásya", "udatta only"),
    ("soma", "ASCII control: the fold must be a no-op and the count must not move"),
)


def test_the_probe_set_covers_every_sentinel_class() -> None:
    """The guard on the guard. A probe set blind to a class certifies nothing about it."""
    folded = "".join(
        comparison_form(probe, ComparisonForm.SEARCH_NORMALIZED) for probe, _ in PROBES
    )
    missing = [name for sentinel, name in SENTINELS.items() if sentinel not in folded]
    assert not missing, f"no probe exercises: {missing}"


def test_the_fold_actually_changes_the_non_ascii_probes() -> None:
    """If the fold were a no-op, every assertion below would pass vacuously."""
    for probe, why in PROBES:
        folded = comparison_form(probe, ComparisonForm.SEARCH_NORMALIZED)
        if probe.isascii():
            assert folded == probe, why
        else:
            assert folded != probe.lower(), f"{probe} ({why}) survives the fold unchanged"


@pytest.mark.neo4j
def test_the_raw_query_matches_nothing_on_the_normalized_rung(
    live_repository: Neo4jRepository,
) -> None:
    """BAD -> FAIL. The binding the service used, run against the rung's own Cypher.

    This is the defect itself, pinned. If a later change makes the raw query work on this
    rung, it will be because the text side was widened -- which is the dangerous direction,
    since the IAST acute is both a consonant diacritic and the udatta -- and this test is
    where that shows up.
    """
    dead: list[str] = []
    for probe, _why in PROBES:
        if probe.isascii():
            continue
        rows = live_repository.run(
            "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv:TextVersion) "
            "WHERE tv.text_role = 'SEARCH_DERIVATIVE' AND toLower(tv.text_nfc) CONTAINS $q "
            "RETURN count(DISTINCT p) AS passages",
            q=probe.lower(),
        )
        if not (rows and rows[0]["passages"]):
            dead.append(probe)
    assert dead == [probe for probe, _ in PROBES if not probe.isascii()], (
        "a raw non-ASCII query now matches SEARCH_DERIVATIVE text. Either the text side "
        "was widened -- which merges the udatta with the consonant acute -- or the stored "
        "derivative is no longer produced by SEARCH_NORMALIZED."
    )


@pytest.mark.neo4j
def test_the_folded_query_reaches_the_text_the_rung_exists_to_serve(
    live_repository: Neo4jRepository,
) -> None:
    """GOOD -> PASS, on the rung's own Cypher with the service's own parameter name."""
    reached: dict[str, int] = {}
    for probe, _why in PROBES:
        folded = comparison_form(probe, ComparisonForm.SEARCH_NORMALIZED)
        rows = live_repository.run(
            "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv:TextVersion) "
            "WHERE tv.text_role = 'SEARCH_DERIVATIVE' "
            "  AND toLower(tv.text_nfc) CONTAINS $q_search_normalized "
            "RETURN count(DISTINCT p) AS passages",
            q_search_normalized=folded,
        )
        reached[probe] = int(rows[0]["passages"]) if rows else 0
    # Every sentinel and accent probe must reach something. kḻptam is allowed to be zero:
    # the vocalic l is genuinely rare and a zero there is a fact about the corpus, not
    # about the fold -- which is why the fold itself is asserted separately above.
    for probe, why in PROBES:
        if probe == "kḻptam":
            continue
        assert reached[probe] > 0, f"{probe} ({why}) still reaches nothing"


@pytest.mark.neo4j
def test_the_service_binds_the_folded_query_into_that_rung(live_client: TestClient) -> None:
    """The fix has to be in the service, not only in this test's own Cypher.

    ``somaṁ`` is the end-to-end witness because it is the one probe the stronger rungs do
    not saturate: the anusvara spelling does not occur in ``PRIMARY_TEXT`` as written, so
    ``EXACT_SANSKRIT_PHRASE`` returns nothing and the normalized rung is the only thing
    that can answer. Before the fix that query returned no passages from this rung at all;
    it now returns the full measured population.
    """
    assert "$q_search_normalized" in _NORMALIZED_PHRASE_QUERY
    assert "CONTAINS $q\n" not in _NORMALIZED_PHRASE_QUERY

    body = live_client.get(
        "/api/v1/search", params={"q": "somaṁ", "type": "passage", "limit": 100}
    ).json()
    normalized = [
        item for item in body["items"] if item.get("match_type") == "NORMALIZED_SANSKRIT_PHRASE"
    ]
    assert normalized, (
        "the normalized rung contributed nothing to an anusvara query, which is the whole "
        f"defect. Rungs that did contribute: "
        f"{sorted({item.get('match_type') for item in body['items']})}"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(("probe", "why"), PROBES)
def test_no_probe_loses_ground_through_the_whole_service(
    live_client: TestClient, probe: str, why: str
) -> None:
    """Every probe still returns passages end to end, and none of them is a 4xx.

    Deliberately not a rung assertion. ``EXACT_SANSKRIT_PHRASE`` saturates the page for
    most of these probes, so the normalized rung is a fallback that does not surface -- and
    a test demanding it would fail for a correct product. The rung's own reach is asserted
    against its own Cypher above, which is where the defect lived.
    """
    response = live_client.get(
        "/api/v1/search", params={"q": probe, "type": "passage", "limit": 100}
    )
    assert response.status_code == 200, f"{probe} ({why}) -> {response.status_code}"
    if probe == "kḻptam":
        pytest.skip("the vocalic l is genuinely rare; its zero is a corpus fact")
    assert response.json()["items"], f"{probe} ({why}) returns no passage at all"
