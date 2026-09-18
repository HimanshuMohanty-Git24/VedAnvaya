"""The deity endpoints, and the two carried-forward defects they contain.

Two tests here are regressions in the strict sense -- they reproduce a live, verified,
wrong answer and then assert the endpoint does not give it:

*Defect A* (:func:`test_defect_a_indras_co_deities_drop_the_human_and_say_so`). The frozen
``profile_co_devatas`` property on Indra is literally ``['Vasukra']``, and Vasukra is a
human patron. The test asserts the raw property still says that, and that the endpoint
returns no deity for it while explaining the emptiness.

*Defect B* (:func:`test_defect_b_the_seer_bridge_admits_no_non_deity`). Walking
``HAS_DEVATA`` twice through shared seers returns, for Indra, 22 things that are not gods,
including Brbu the carpenter, a dog and "praise of the gift of Sudas son of Pijavana". The
test runs the unfiltered walk to prove the defect is live, then asserts the endpoint's
answer contains none of it.

Both are written before/after on purpose. A test that only asserts the clean result passes
just as well when the filter has been deleted and the underlying data has changed.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, UntracedBlock
from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.models.entity import (
    DEITY_STRUCTURES,
    KNOWN_DEITY_AXES,
    NON_DEITY_STRUCTURES,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.deity_population import (
    KNOWN_DEITY_STRUCTURES,
    DevataSubject,
    is_deity,
)
from vedagraph.api.services.entity_service import subject_disclosure

INDRA = "VG:DEVATA:INDRAH"
AGNI = "VG:DEVATA:AGNIH"
SOMA = "VG:DEVATA:SOMAH"
VASISTHA = "VG:DEVATA:VASISTHAH"
#: The dog is a DEITY. It is kept here because it is the canonical example of a subject
#: the *structure* predicate refused and the recorded ruling admits: 13 other animals are in
#: the population, and excluding this one for carrying structure UNSPECIFIED rather than
#: INDIVIDUAL was, in the ruling's own words, "excluding on a morphological accident".
THE_DOG = "VG:DEVATA:SUNAH"
#: A ruled non-deity, and of the class that matters: 28 ABSTRACT labels are ruled
#: ABSTRACTION_NOT_AN_ADDRESSEE and the old structure predicate admitted every one of them.
#: "the course of becoming" is the best-attested of them at 15 dedications.
AN_ABSTRACTION = "VG:DEVATA:BHAVAVRTTAM"

#: Names the unfiltered seer-bridge returns for Indra, verified live. Used as a
#: denylist: if any of these reaches a deity surface the containment has regressed.
KNOWN_NON_DEITY_LABELS = frozenset(
    {
        "Vasukra",
        "Vamadeva",
        "Atri",
        "Visvamitra",
        "Brbu the carpenter",
        "the sons of Vasistha",
        "Svanaya Bhavayavya",
        "Somaka son of Sahadeva",
        "the dog",
        "praise of a patron's gift",
        "praise of the gift of Svanaya",
        "praise of the gift of Sudas son of Pijavana",
        "praise of the gift of Prastoka Sarnjaya",
    }
)

#: Strings that would mean an internal graph object, a Neo4j id or a credential escaped
#: into a response body.
FORBIDDEN_IN_BODY = (
    "QAIssue",
    "element_id",
    "elementId",
    '"Internal"',
    ":Internal",
    "MATCH (",
    "bolt://",
    "neo4j",
    "password",
)


def assert_no_internals(body: str) -> None:
    leaked = [needle for needle in FORBIDDEN_IN_BODY if needle in body]
    assert not leaked, f"response leaked {leaked}"


# ---------------------------------------------------------------------------
# Contract, offline
# ---------------------------------------------------------------------------


def test_unknown_deity_is_404_with_a_hint(client: TestClient) -> None:
    response = client.get(f"/api/v1/devatas/{INDRA}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "ENTITY_NOT_FOUND"
    assert body["hint"]


def test_deity_list_with_no_rows_cannot_claim_supported(client: TestClient) -> None:
    """An empty first page must carry a non-SUPPORTED status or a caveat. Never a bare []."""
    response = client.get("/api/v1/devatas")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["data_status"] != "SUPPORTED" or body["caveats"]
    assert body["caveats"], "the population contract must be stated even on an empty page"


def test_limit_above_the_maximum_is_422(client: TestClient) -> None:
    response = client.get("/api/v1/devatas", params={"limit": MAX_PAGE_SIZE + 1})
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_unknown_population_is_422(client: TestClient) -> None:
    response = client.get("/api/v1/devatas", params={"population": "everything"})
    assert response.status_code == 422


def test_graph_outage_is_503_naming_no_host(down_client: TestClient) -> None:
    for path in (
        "/api/v1/devatas",
        f"/api/v1/devatas/{INDRA}",
        f"/api/v1/devatas/{INDRA}/passages",
        f"/api/v1/devatas/{INDRA}/network",
    ):
        response = down_client.get(path)
        assert response.status_code == 503, path
        assert_no_internals(response.text)


@pytest.mark.parametrize(
    "malicious",
    [
        "MATCH (n) DETACH DELETE n",
        "' OR 1=1 --",
        "\" ' \\ { } ( ) ~ * ? : ^ ] [",
        "VG:DEVATA:X'}) DETACH DELETE (n",
    ],
)
def test_deity_ids_and_filters_are_parameterised(
    client: TestClient, fake_repository: FakeRepository, malicious: str
) -> None:
    """No client string reaches the query TEXT. Asserted against what the driver was asked."""
    # The id has no closed value space, so it must reach the driver BOUND. The path
    # segment is percent-encoded, or a payload containing '?' would be truncated into a
    # query string by the client and the assertion below would prove nothing.
    client.get(f"/api/v1/devatas/{quote(malicious, safe='')}")
    assert fake_repository.calls, "no query was issued, so the assertion proves nothing"
    assert malicious not in fake_repository.query_text
    bound = [v for v in fake_repository.all_parameters.values() if isinstance(v, str)]
    assert any(malicious in value for value in bound), (
        "the id must have travelled as a bound parameter, not vanished"
    )

    # structure and axis DO have closed value spaces, so they are refused before any
    # query runs -- which is stronger than binding them.
    fake_repository.calls.clear()
    refused = client.get("/api/v1/devatas", params={"structure": malicious, "axis": malicious})
    assert refused.status_code == 400, (
        "a filter value outside its measured space must be a 400, not an empty page"
    )
    assert not fake_repository.calls, (
        "the refusal must happen before the query, or the value reached Cypher"
    )
    assert malicious not in fake_repository.query_text


# ---------------------------------------------------------------------------
# Defect A: the co-deity list holds display labels, and one of Indra's is a human
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_defect_a_indras_co_deities_drop_the_human_and_say_so(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    before = live_repository.run_one(
        "MATCH (dv:Devata {entity_key: $key}) RETURN dv.profile_co_devatas AS raw", key=INDRA
    )
    assert before is not None
    assert before["raw"] == ["Vasukra"], (
        "the defect this test contains has changed shape; re-read the property before "
        f"trusting the assertion below (raw = {before['raw']!r})"
    )
    vasukra = live_repository.run_one(
        "MATCH (dv:Devata {display_label: 'Vasukra'}) RETURN dv.structure AS structure"
    )
    assert vasukra is not None and vasukra["structure"] == "HUMAN"

    after = live_client.get(f"/api/v1/devatas/{INDRA}").json()
    assert after["co_deities"] == [], (
        "Vasukra is a human patron and must not be returned as one of Indra's co-deities"
    )
    statuses = {row["dimension"]: row for row in after["dimension_status"]}
    assert "co_deities" in statuses, "an emptied list must say why it is empty"
    note = statuses["co_deities"]["note"]
    assert statuses["co_deities"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert "Vasukra" in note and "HUMAN" in note
    assert "network" in note, "the note should point at the measured co-occurrence layer"


@pytest.mark.neo4j
def test_every_co_deity_returned_anywhere_is_a_deity(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """Sweep the whole pantheon rather than sampling: a per-alias defect hides in a sample."""
    keys = [
        str(row["key"])
        for row in live_repository.run(
            "MATCH (dv:Devata) WHERE size(coalesce(dv.profile_co_devatas, [])) > 0 "
            "RETURN dv.entity_key AS key"
        )
    ]
    assert keys, "no deity carries profile_co_devatas; the sweep would prove nothing"
    structures = {
        str(row["key"]): row["structure"]
        for row in live_repository.run(
            "MATCH (dv:Devata) RETURN dv.entity_key AS key, dv.structure AS structure"
        )
    }
    for key in keys:
        payload = live_client.get(f"/api/v1/devatas/{key}").json()
        for ref in payload["co_deities"]:
            assert is_deity(structures.get(ref["id"])), (
                f"{key} returned {ref['id']} ({structures.get(ref['id'])}) as a co-deity"
            )


# ---------------------------------------------------------------------------
# Defect B: the seer bridge lands on whatever the Anukramani ascribed
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_defect_b_the_seer_bridge_admits_no_non_deity(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    unfiltered = live_repository.run(
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:HAS_RISHI]->(rs:Rishi)
        MATCH (p2:Passage)-[:HAS_RISHI]->(rs)
        MATCH (p2)-[:HAS_DEVATA]->(other:Devata)
        WHERE other.entity_key <> $key
          AND coalesce(other.structure, 'UNSPECIFIED') IN $non_deities
        RETURN DISTINCT other.display_label AS label, other.structure AS structure
        """,
        key=INDRA,
        non_deities=sorted(NON_DEITY_STRUCTURES),
    )
    leaked_before = {str(row["label"]) for row in unfiltered}
    assert len(leaked_before) >= 15, (
        "the unfiltered walk no longer returns a crowd of non-deities, so this regression "
        f"is measuring nothing (got {sorted(leaked_before)})"
    )
    assert "Brbu the carpenter" in leaked_before
    assert "the dog" in leaked_before
    assert "praise of the gift of Sudas son of Pijavana" in leaked_before

    payload = live_client.get(f"/api/v1/devatas/{INDRA}/network").json()
    returned = {ref["display_label"] for ref in payload["shared_rishi_deities"]}
    assert returned, "the bridge returned nothing at all, so nothing is being contained"
    assert not returned & leaked_before, f"non-deities leaked: {sorted(returned & leaked_before)}"
    assert not returned & KNOWN_NON_DEITY_LABELS
    assert "Agni" in returned, "the bridge should still reach real deities"


@pytest.mark.neo4j
def test_network_co_occurrence_is_population_filtered_and_carries_its_own_caveat(
    live_client: TestClient,
) -> None:
    payload = live_client.get(f"/api/v1/devatas/{INDRA}/network").json()
    for edge in payload["co_occurring"]:
        assert edge["other"]["display_label"] not in KNOWN_NON_DEITY_LABELS
        assert edge["other"]["type"] == "DEVATA"
    assert payload["co_occurring"], "Indra has 306-edge-layer neighbours; none were returned"
    sources = {caveat["source"] for caveat in payload["caveats"]}
    assert "graph:CO_OCCURS_WITH.evidence_caveat" in sources, (
        "the edge carries a measured caveat; it must be returned rather than retyped"
    )
    assert any("seer" in caveat["text"] for caveat in payload["caveats"])


# ---------------------------------------------------------------------------
# The population contract end to end
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_human_nodes_cannot_surface_as_deities(live_client: TestClient) -> None:
    payload = live_client.get("/api/v1/devatas", params={"limit": MAX_PAGE_SIZE}).json()
    assert payload["pagination"]["total"] == 157
    for row in payload["items"]:
        assert row["is_deity"] is True
        assert row["display_label"] not in KNOWN_NON_DEITY_LABELS - {"the dog"}

    for key in (VASISTHA, AN_ABSTRACTION):
        refused = live_client.get(f"/api/v1/devatas/{key}")
        assert refused.status_code == 404, f"{key} was served as a deity"
        assert "all_ascriptions" in refused.json()["hint"]

        allowed = live_client.get(
            f"/api/v1/devatas/{key}", params={"population": "all_ascriptions"}
        )
        assert allowed.status_code == 200
        body = allowed.json()
        assert body["is_deity"] is False
        assert body["structure"] in KNOWN_DEITY_STRUCTURES


@pytest.mark.neo4j
def test_all_ascriptions_returns_the_slot_as_it_stands(live_client: TestClient) -> None:
    payload = live_client.get(
        "/api/v1/devatas",
        params={"population": "all_ascriptions", "limit": MAX_PAGE_SIZE},
    ).json()
    assert payload["pagination"]["total"] == 214
    structures = {row["structure"] for row in payload["items"]}
    assert structures & NON_DEITY_STRUCTURES, "all_ascriptions must include the non-deities"
    assert any("not a pantheon" in caveat["text"] for caveat in payload["caveats"])


@pytest.mark.neo4j
def test_non_deity_rishi_ascriptions_never_surface_as_devatas(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """A lizard and a ladle are in the rishi slot. Neither may be rendered as a god.

    113 of the 729 ``:Rishi`` nodes are not seers, and the kinds include PLANT_OR_ANIMAL
    and OBJECT. The assertion is structural: no reference typed ``DEVATA`` anywhere in the
    deity surface may carry a ``VG:RISHI:`` id, and a rishi id is not a deity id.
    """
    non_seers = [
        str(row["key"])
        for row in live_repository.run(
            "MATCH (rs:Rishi) WHERE rs.is_seer = false "
            "AND rs.non_seer_kind IN ['PLANT_OR_ANIMAL', 'OBJECT', 'ABSTRACTION'] "
            "RETURN rs.entity_key AS key"
        )
    ]
    assert len(non_seers) >= 5, "the non-seer strata this test needs are missing"
    for key in non_seers[:6]:
        assert live_client.get(f"/api/v1/devatas/{key}").status_code == 404
        profile = live_client.get(f"/api/v1/entities/rishi/{key}")
        assert profile.status_code == 200
        body = profile.json()
        assert body["type"] == "RISHI"
        assert body["seer"]["is_seer"] is False
        assert body["seer"]["non_seer_kind"]

    network = live_client.get(f"/api/v1/devatas/{INDRA}/network").json()
    for ref in network["shared_rishi_deities"]:
        assert ref["type"] == "DEVATA"
        assert not ref["id"].startswith("VG:RISHI:")


# ---------------------------------------------------------------------------
# Cross-endpoint agreement: one contract, one gate, every surface
# ---------------------------------------------------------------------------
#
# Five of the six CRITICAL findings in the adversarial pass had one shape: a contract
# enforced at one call site and forgotten at a second. Per-endpoint tests cannot catch
# that, because each endpoint passed its own. These sweep every deity route against the
# same subject, and every list row against its own profile, so a contract applied in one
# place and not another fails here rather than in an audit.


@pytest.mark.neo4j
@pytest.mark.parametrize("suffix", ["", "/passages", "/passages?basis=ascription", "/network"])
def test_every_deity_route_refuses_the_same_non_deities(
    live_repository: Neo4jRepository, live_client: TestClient, suffix: str
) -> None:
    """The population gate is one chokepoint, so all four routes must agree exactly.

    They did not. ``/devatas/VG:DEVATA:SUNAH`` 404'd while
    ``/devatas/VG:DEVATA:SUNAH/network`` served the dog as ``type=DEVATA`` under a caveat
    reading "This response excludes all 30", and ``/passages`` served its Anukramani slot
    as a 200 SUPPORTED page.

    The population is read from the recorded ruling, not from ``structure``. Reading it
    from structure is what made this sweep agree with a gate that was itself wrong about
    29 nodes: it never asked about the 28 abstractions, and it asked about the dog, whom
    the ruling admits.
    """
    non_deities = [
        str(row["key"])
        for row in live_repository.run(
            "MATCH (dv:Devata) WHERE dv.is_deity = false RETURN dv.entity_key AS key"
        )
    ]
    assert len(non_deities) == 57, f"the non-deity population has moved: {len(non_deities)}"
    served = []
    for key in non_deities:
        separator = "&" if "?" in suffix else "?"
        response = live_client.get(f"/api/v1/devatas/{key}{suffix}")
        if response.status_code != 404:
            served.append((key, response.status_code))
        # and under all_ascriptions every route must serve it, typed as what it is
        allowed = live_client.get(
            f"/api/v1/devatas/{key}{suffix}{separator}population=all_ascriptions"
        )
        assert allowed.status_code == 200, (
            f"{key}{suffix} must be readable under population=all_ascriptions, got "
            f"{allowed.status_code}"
        )
    assert not served, (
        f"these non-deities were served by /devatas/{{id}}{suffix} under the default "
        f"population: {served[:5]}"
    )


#: Every deity route that serves a SUBJECT, with the params that reach it. Sweeping the
#: list is the guard: the disclosure contract was applied on ``/passages``, half-applied on
#: ``/devatas/{id}`` (the flag without the caveat) and not at all on ``/network``, so a
#: per-route test would have passed on the one route that was right.
SUBJECT_ROUTES: tuple[tuple[str, dict[str, str]], ...] = (
    ("/api/v1/devatas/{key}", {}),
    ("/api/v1/devatas/{key}/passages", {"basis": "ascription"}),
    ("/api/v1/devatas/{key}/network", {}),
)


def _subject_fields(body: dict[str, Any]) -> tuple[Any, Any]:
    """The subject's structure and deity flag, under either surface's field names."""
    structure = body.get("subject_structure", body.get("structure", "__MISSING__"))
    is_deity_flag = body.get("subject_is_deity", body.get("is_deity", "__MISSING__"))
    return structure, is_deity_flag


@pytest.mark.neo4j
@pytest.mark.parametrize(("path", "extra"), SUBJECT_ROUTES)
def test_every_opt_in_route_types_a_non_deity_subject(
    live_repository: Neo4jRepository, live_client: TestClient, path: str, extra: dict[str, str]
) -> None:
    """A 200 from a deity route must never leave the SUBJECT's typing to be inferred.

    Under ``population=all_ascriptions`` the network route served the dog as
    ``type=DEVATA``, ``display_label='the dog'``, with no ``structure`` anywhere in the
    payload, beneath a caveat instructing the client to "read each row's `structure`" --
    advice with nothing to read. Swept over all 30 non-deities on every subject route.
    """
    non_deities = [
        (str(row["key"]), str(row["structure"]))
        for row in live_repository.run(
            "MATCH (dv:Devata) WHERE dv.is_deity = false "
            "RETURN dv.entity_key AS key, coalesce(dv.structure, 'UNSPECIFIED') AS structure"
        )
    ]
    assert len(non_deities) == 57, f"the non-deity population has moved: {len(non_deities)}"
    for key, structure in non_deities:
        response = live_client.get(
            path.format(key=key), params={"population": "all_ascriptions", **extra}
        )
        assert response.status_code == 200, f"{path.format(key=key)} -> {response.status_code}"
        body = response.json()
        reported_structure, reported_flag = _subject_fields(body)
        assert reported_structure == structure, (
            f"{path.format(key=key)} reports subject structure {reported_structure!r}, "
            f"and the graph says {structure!r}"
        )
        assert reported_flag is False, (
            f"{path.format(key=key)} reports the subject as a deity, or omits the flag: "
            f"{reported_flag!r}"
        )
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "THIS SUBJECT IS NOT A DEITY" in text, (
            f"{path.format(key=key)} serves a {structure} subject with no caveat saying so"
        )
        assert structure in text


@pytest.mark.neo4j
@pytest.mark.parametrize(("path", "extra"), SUBJECT_ROUTES)
def test_no_real_deity_is_labelled_as_a_non_deity(
    live_client: TestClient, path: str, extra: dict[str, str]
) -> None:
    """The other direction: the disclosure must not be attached where it is false."""
    for key in (INDRA, AGNI, SOMA, "VG:DEVATA:SARASVATI"):
        body = live_client.get(path.format(key=key), params=extra).json()
        reported_structure, reported_flag = _subject_fields(body)
        assert reported_flag is True, f"{path.format(key=key)} flags a real deity as not one"
        assert reported_structure not in NON_DEITY_STRUCTURES
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "THIS SUBJECT IS NOT A DEITY" not in text, (
            f"{path.format(key=key)} tells a client that {key} is not a deity"
        )


def test_the_subject_disclosure_is_produced_in_exactly_one_place() -> None:
    """The flag and the caveat come from one call, so they cannot disagree.

    Three routes previously produced three different disclosures for the same subject --
    one complete, one flag-only, one absent. Returning both halves together removes the
    way to take one without the other.
    """
    for structure in sorted(NON_DEITY_STRUCTURES):
        flag, caveats = subject_disclosure(
            DevataSubject(structure=structure, is_deity=False, non_deity_kind="HUMAN_PATRON")
        )
        assert flag is False
        assert len(caveats) == 1
        assert "THIS SUBJECT IS NOT A DEITY" in caveats[0].text
        assert structure in caveats[0].text
        assert caveats[0].source == "deity_population_contract"
    for structure in sorted(DEITY_STRUCTURES):
        flag, caveats = subject_disclosure(DevataSubject(structure=structure, is_deity=True))
        assert flag is True
        assert caveats == []
    # An unruled subject fails closed on both halves at once, whatever its structure says.
    flag, caveats = subject_disclosure(DevataSubject(structure="SEMI_DIVINE", is_deity=False))
    assert flag is False and len(caveats) == 1
    flag, caveats = subject_disclosure(DevataSubject(structure=None, is_deity=False))
    assert flag is False and len(caveats) == 1
    # And an ABSTRACT subject, which the superseded structure predicate called a deity.
    flag, caveats = subject_disclosure(
        DevataSubject(
            structure="ABSTRACT", is_deity=False, non_deity_kind="ABSTRACTION_NOT_AN_ADDRESSEE"
        )
    )
    assert flag is False
    assert "ABSTRACTION_NOT_AN_ADDRESSEE" in caveats[0].text


@pytest.mark.neo4j
def test_every_deity_list_row_states_whether_it_is_a_deity(live_client: TestClient) -> None:
    """The list is the fourth surface reachable under all_ascriptions. Asserted, not assumed."""
    rows: list[dict[str, Any]] = []
    for offset in (0, 200):
        rows.extend(
            live_client.get(
                "/api/v1/devatas",
                params={"population": "all_ascriptions", "limit": 200, "offset": offset},
            ).json()["items"]
        )
    assert len(rows) == 214
    assert all("is_deity" in row and row["structure"] for row in rows)
    assert sum(1 for row in rows if row["is_deity"] is False) == 57
    # Every row's flag agrees with the deity page's own gate for the same subject: a row
    # flagged a deity must be servable under the default population, and one flagged not a
    # deity must be refused by it. That is the cross-surface agreement this file exists for.
    #
    # All 214, never a prefix. A 40-row slice of an ordered list is the first 40 labels
    # alphabetically, and this file's own sibling tests carry the reason: "Per subject, not
    # per sample. This project has twice certified an absence from a sample that happened to
    # miss the failing rows."
    disagreements: list[str] = []
    for row in rows:
        served = live_client.get(f"/api/v1/devatas/{row['id']}").status_code
        if (served == 200) is not (row["is_deity"] is True):
            disagreements.append(f"{row['id']} is_deity={row['is_deity']} route={served}")
    assert not disagreements, (
        f"the list flag and the deity route disagree on {len(disagreements)} of "
        f"{len(rows)} subjects: {disagreements[:5]}"
    )


@pytest.mark.neo4j
def test_a_non_deity_served_under_all_ascriptions_says_it_is_not_a_deity(
    live_client: TestClient,
) -> None:
    """A 200 from a deity route must never leave the reader to infer the structure."""
    for key, structure in (
        (VASISTHA, "HUMAN"),
        (AN_ABSTRACTION, "ABSTRACT"),
        ("VG:DEVATA:DANASTUTIH", "PATRON_PRAISE"),
    ):
        profile = live_client.get(
            f"/api/v1/devatas/{key}", params={"population": "all_ascriptions"}
        ).json()
        assert profile["is_deity"] is False
        assert profile["structure"] == structure

        page = live_client.get(
            f"/api/v1/devatas/{key}/passages",
            params={"population": "all_ascriptions", "basis": "ascription"},
        ).json()
        assert page["subject_is_deity"] is False
        assert page["subject_structure"] == structure
        text = " ".join(caveat["text"] for caveat in page["caveats"])
        assert structure in text, (
            f"the page for {key} does not state its structure {structure!r} anywhere"
        )
        assert "NOT A DEITY" in text


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "devata_id",
    [INDRA, AGNI, SOMA, "VG:DEVATA:SARASVATI", "VG:DEVATA:PRTHIVI", "VG:DEVATA:YAMAH"],
)
def test_the_deity_profile_and_the_deity_insight_report_the_same_total(
    live_client: TestClient, devata_id: str
) -> None:
    """One number, one source. The profile read a materialisation the insight did not.

    ``profile_mentions_by_veda_certainty`` sits on 30 of the 214 nodes, so the profile
    reported null with INSUFFICIENT_EVIDENCE for 184 deities while the insight endpoint
    counted the edges and answered correctly -- Sarasvati null against 65, Prthivi null
    against 61 with 712 mention edges behind it. Both now count the edges.
    """
    profile = live_client.get(f"/api/v1/devatas/{devata_id}").json()
    insight = live_client.get(f"/api/v1/insights/devatas/{devata_id}").json()
    assert profile["mentions_included_total"] == insight["named_total"], (
        f"{devata_id}: profile says {profile['mentions_included_total']!r}, insight says "
        f"{insight['named_total']!r}"
    )
    assert profile["certainty"]["certain_count"] == insight["certainty"]["certain_count"]
    assert profile["certainty"]["probable_count"] == insight["certainty"]["probable_count"]
    assert profile["certainty"]["ambiguous_count"] == insight["certainty"]["ambiguous_count"]


@pytest.mark.neo4j
def test_no_deity_profile_reports_insufficient_evidence_for_an_unbuilt_layer(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """INSUFFICIENT_EVIDENCE means evidence exists and cannot settle it. Nothing else.

    An unmaterialised property is not that, and neither is a deity outside the theonym
    registry: those are NOT_BUILT. Sweeping every deity keeps the two words apart.
    """
    with_edges = {
        str(row["key"])
        for row in live_repository.run(
            "MATCH (dv:Devata) WHERE EXISTS { (:Passage)-[:MENTIONS_DEVATA]->(dv) } "
            "RETURN dv.entity_key AS key"
        )
    }
    assert len(with_edges) == 42, f"the mention population has moved: {len(with_edges)}"
    keys = [
        str(row["key"])
        for row in live_repository.run("MATCH (dv:Devata) RETURN dv.entity_key AS key ORDER BY key")
    ]
    wrong = []
    for key in keys:
        body = live_client.get(
            f"/api/v1/devatas/{key}", params={"population": "all_ascriptions"}
        ).json()
        for entry in body["mentions_by_veda"]:
            if entry["status"] == "INSUFFICIENT_EVIDENCE" and key not in with_edges:
                wrong.append((key, entry["veda"]))
    assert not wrong, (
        "these deities carry no mention edge at all, so their corpora are NOT_BUILT and "
        f"not INSUFFICIENT_EVIDENCE: {wrong[:5]}"
    )


@pytest.mark.neo4j
def test_a_deity_with_no_mention_layer_says_so_and_never_prints_a_zero(
    live_client: TestClient,
) -> None:
    body = live_client.get(
        "/api/v1/devatas/VG:DEVATA:ABHISAPAH", params={"population": "all_ascriptions"}
    ).json()
    assert body["mentions_included_total"] is None
    assert {row["status"] for row in body["mentions_by_veda"]} == {"NOT_BUILT"}
    assert all(row["count"] is None for row in body["mentions_by_veda"])
    text = " ".join(caveat["text"] for caveat in body["caveats"])
    assert "NO MENTION LAYER AT ALL" in text
    assert body["attributed_total"], "its Anukramani ascription is real and must be reported"


@pytest.mark.neo4j
def test_the_declared_axis_space_matches_the_graph(live_repository: Neo4jRepository) -> None:
    """The axis filter refuses offline, so its value space is declared and must be checked."""
    measured = {
        str(row["axis"])
        for row in live_repository.run("MATCH (a:DeityAxis) RETURN a.axis AS axis")
        if row["axis"] is not None
    }
    assert measured == KNOWN_DEITY_AXES, (
        f"declared but absent: {sorted(KNOWN_DEITY_AXES - measured)}; measured but "
        f"undeclared: {sorted(measured - KNOWN_DEITY_AXES)}"
    )


@pytest.mark.neo4j
def test_the_passage_page_reports_all_three_tiers_over_the_whole_edge_set(
    live_client: TestClient,
) -> None:
    """Soma's 421 default rows must not hide the 1,091 ambiguous mentions behind them."""
    page = live_client.get(f"/api/v1/devatas/{SOMA}/passages", params={"limit": 5}).json()
    counts = page["certainty"]
    assert counts["certain_count"] == 240
    assert counts["probable_count"] == 181
    assert counts["ambiguous_count"] == 1091
    assert counts["included_tiers"] == ["DEITY_CERTAIN", "DEITY_PROBABLE"]
    assert page["matched_total"] == 421
    assert page["basis"] == "mention"

    opted_in = live_client.get(
        f"/api/v1/devatas/{SOMA}/passages", params={"limit": 5, "include_ambiguous": "true"}
    ).json()
    assert opted_in["matched_total"] == 1512
    assert opted_in["certainty"]["ambiguous_count"] == 1091


@pytest.mark.neo4j
def test_an_unknown_deity_filter_value_is_refused_by_name(live_client: TestClient) -> None:
    for parameter, value in (
        ("structure", "NOPE"),
        ("axis", "NOPE"),
        # an axis value in the structure slot: previously indistinguishable from an
        # empty result
        ("structure", "WARRIOR"),
        ("axis", "INDIVIDUAL"),
    ):
        response = live_client.get("/api/v1/devatas", params={parameter: value})
        assert response.status_code == 400, f"?{parameter}={value} returned 200"
        body = response.json()
        assert value in body["detail"]
        assert parameter in body["hint"]


# ---------------------------------------------------------------------------
# The ambiguity contract end to end
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_default_counts_are_certain_plus_probable(live_client: TestClient) -> None:
    payload = live_client.get(f"/api/v1/devatas/{AGNI}").json()
    counts = payload["certainty"]
    assert payload["included_certainty"] == "default"
    assert counts["included_tiers"] == ["DEITY_CERTAIN", "DEITY_PROBABLE"]
    assert counts["ambiguous_count"] > 0, "Agni has ambiguous mentions; they must be reported"
    assert payload["mentions_included_total"] == counts["certain_count"] + counts["probable_count"]
    assert all(
        row["certainty"]["ambiguous_count"] is not None for row in payload["mentions_by_veda"]
    )


@pytest.mark.neo4j
def test_ambiguous_is_opt_in_and_moves_soma_by_a_factor_of_four(
    live_client: TestClient,
) -> None:
    default = live_client.get(f"/api/v1/devatas/{SOMA}").json()
    opted_in = live_client.get(
        f"/api/v1/devatas/{SOMA}", params={"include_ambiguous": "true"}
    ).json()
    assert default["mentions_included_total"] == 421
    assert opted_in["mentions_included_total"] == 1512
    assert "DEITY_AMBIGUOUS" in opted_in["certainty"]["included_tiers"]
    assert "DEITY_AMBIGUOUS" not in default["certainty"]["included_tiers"]
    assert any("0.6142" in caveat["text"] for caveat in opted_in["caveats"]), (
        "including the ambiguous bucket must state its measured precision"
    )


@pytest.mark.neo4j
def test_strict_mode_returns_null_and_not_zero_where_it_empties_a_corpus(
    live_client: TestClient,
) -> None:
    """The single most dangerous request in this API: the cautious one.

    Agni has 831 CERTAIN Rigvedic mentions and zero CERTAIN anywhere else, against 170
    PROBABLE in the Atharvaveda, 97 in the Yajurveda and 82 in the Samaveda. A strict
    request must not print 0 for those three.
    """
    payload = live_client.get(f"/api/v1/devatas/{AGNI}", params={"certainty": "strict"}).json()
    rows = {row["veda"]: row for row in payload["mentions_by_veda"]}
    assert rows["RV"]["count"] == 831 and rows["RV"]["status"] == "SUPPORTED"
    for veda in ("AV", "YV", "SV"):
        assert rows[veda]["count"] is None, f"{veda} printed a count under strict mode"
        assert rows[veda]["status"] == "INSUFFICIENT_EVIDENCE"
        assert rows[veda]["certainty"]["probable_count"] > 0, (
            "the excluded evidence must still be visible on the row"
        )
    assert any("certainty=strict" in caveat["text"] for caveat in payload["caveats"])
    assert any(
        "never `0`" in c["text"] or "not an absence" in c["text"] for c in payload["caveats"]
    )


@pytest.mark.neo4j
def test_default_mode_reaches_all_four_corpora_for_agni(live_client: TestClient) -> None:
    """The other half of the strict test: the default answer is the better answer."""
    payload = live_client.get(f"/api/v1/devatas/{AGNI}").json()
    rows = {row["veda"]: row for row in payload["mentions_by_veda"]}
    for veda in ("RV", "AV", "YV", "SV"):
        assert rows[veda]["count"] and rows[veda]["status"] == "SUPPORTED", veda
    assert rows["AV"]["count"] == 170
    assert rows["SV"]["count"] == 82


# ---------------------------------------------------------------------------
# Attribution versus mention
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_mention_and_ascription_are_different_questions(live_client: TestClient) -> None:
    mentions = live_client.get(
        f"/api/v1/devatas/{AGNI}/passages", params={"basis": "mention", "limit": 50}
    ).json()
    ascriptions = live_client.get(
        f"/api/v1/devatas/{AGNI}/passages", params={"basis": "ascription", "limit": 50}
    ).json()

    assert {row["basis"] for row in mentions["items"]} == {"mention"}
    assert {row["basis"] for row in ascriptions["items"]} == {"ascription"}
    assert all(row["referent_certainty"] for row in mentions["items"])
    assert all(row["attribution_precision"] for row in ascriptions["items"])
    assert all(row["referent_certainty"] is None for row in ascriptions["items"])

    # 2,164 and not 1,988: this route read HAS_DEVATA alone while its sibling
    # /api/v1/insights/devatas/{id} read both resolved dedication predicates, so the same
    # product answered the same question two ways. Both now read HAS_DEVATA plus
    # HAS_DEVATA_DERIVED. Agni gains 176 Atharvavedic passages, resolved from the
    # Anukramani's own adjective under Panini 4.2.24 sasya devata.
    assert ascriptions["pagination"]["total"] == 1988 + 176 == 2164
    ascribed_vedas = {
        str(row["veda"])
        for row in live_client.get(
            f"/api/v1/devatas/{AGNI}/passages",
            params={"basis": "ascription", "limit": 200},
        ).json()["items"]
    }
    # RV and AV, and NOT SV or YV: those two carry no dedication layer under any of the three
    # predicates, which is GAP-ATTRIBUTION-001 and a source block rather than an unbuilt
    # projection. A Samavedic or Yajurvedic row here would be the defect.
    assert ascribed_vedas == {"RV", "AV"}
    assert any("ATTRIBUTION IS NOT MENTION" in c["text"] for c in ascriptions["caveats"])


@pytest.mark.neo4j
def test_ascription_outside_the_dedication_layer_is_empty_and_says_why(
    live_client: TestClient,
) -> None:
    """Renamed, because "outside the Rigveda" stopped being the boundary.

    The Atharvaveda now HAS a resolved dedication layer -- HAS_DEVATA_DERIVED, 851 passages
    and 35 deities -- so asking for Agni's Atharvavedic ascription returns 176 real rows and
    the old assertion of emptiness had become a false absence. The Samaveda and Yajurveda
    carry no dedication layer under any of the three predicates, so THEY are what "empty by
    construction" now means, and both halves are asserted here: the corpora that are empty
    say why, and the corpus that is not is not claimed to be.
    """
    for veda in ("SV", "YV"):
        payload = live_client.get(
            f"/api/v1/devatas/{AGNI}/passages", params={"basis": "ascription", "veda": veda}
        ).json()
        assert payload["items"] == [], veda
        assert payload["data_status"] != "SUPPORTED", veda
        assert any("empty by construction" in c["text"] for c in payload["caveats"]), veda
        assert any("basis=mention" in c["text"] for c in payload["caveats"]), veda

    atharvan = live_client.get(
        f"/api/v1/devatas/{AGNI}/passages", params={"basis": "ascription", "veda": "AV"}
    ).json()
    assert atharvan["pagination"]["total"] == 176
    assert {row["veda"] for row in atharvan["items"]} == {"AV"}
    # And it must NOT claim emptiness for a corpus it just served rows from.
    assert not any("empty by construction" in c["text"] for c in atharvan["caveats"])
    assert any("HAS_DEVATA_DERIVED" in c["text"] for c in atharvan["caveats"])
    assert any("basis=mention" in c["text"] for c in atharvan["caveats"])


@pytest.mark.neo4j
def test_the_profile_keeps_strict_and_inherited_attribution_apart(
    live_client: TestClient,
) -> None:
    payload = live_client.get(f"/api/v1/devatas/{INDRA}").json()
    # 2,945 = 2,869 Rigvedic + 76 Atharvavedic, both resolved dedication routes. The strict /
    # inherited split this test exists for is unchanged in kind: the Atharvavedic rows are
    # CONTAINER_INHERITED, a sukta label projected onto its verses, so they land in
    # `attributed_inherited` and the two still sum to the total.
    assert payload["attributed_total"] == 2945
    assert payload["attributed_per_passage"] == 655
    assert payload["attributed_inherited"] == 2290
    assert payload["attributed_per_passage"] + payload["attributed_inherited"] == 2945
    assert payload["attribution_scope"] == ["RV", "AV"]
    assert any("ATTRIBUTION IS NOT MENTION" in c["text"] for c in payload["caveats"])


@pytest.mark.neo4j
def test_samaveda_scope_is_stated_wherever_a_samavedic_figure_appears(
    live_client: TestClient,
) -> None:
    payload = live_client.get(f"/api/v1/devatas/{INDRA}").json()
    sv = next(row for row in payload["mentions_by_veda"] if row["veda"] == "SV")
    assert sv["count"], "Indra is named in the Samaveda; the fixture assumption has moved"
    assert any("SAMAVEDA SCOPE" in caveat["text"] for caveat in payload["caveats"])
    assert any("arcika" in caveat["text"] for caveat in payload["caveats"])


# ---------------------------------------------------------------------------
# Absence typing, leakage and latency
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_absent_profile_dimensions_are_typed_not_emptied(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """``profile_absent_dimensions`` must become a status, never an empty list."""
    rows = live_repository.run(
        "MATCH (dv:Devata) WHERE size(coalesce(dv.profile_absent_dimensions, [])) > 0 "
        "RETURN dv.entity_key AS key, dv.profile_absent_dimensions AS absent, "
        "dv.structure AS structure"
    )
    assert len(rows) == 25, f"25 deities carried absent dimensions; found {len(rows)}"
    checked = 0
    for row in rows:
        if not is_deity(row["structure"]):
            continue
        payload = live_client.get(f"/api/v1/devatas/{row['key']}").json()
        reported = {entry["dimension"] for entry in payload["dimension_status"]}
        for dimension in row["absent"]:
            expected = "co_deities" if dimension == "co_devatas" else dimension
            assert dimension in reported or expected in reported, (
                f"{row['key']} left {dimension} unexplained"
            )
        for entry in payload["dimension_status"]:
            assert entry["status"] in {"INSUFFICIENT_EVIDENCE", "NOT_BUILT", "PARTIAL"}
            assert len(entry["note"]) > 40, "a status needs a reason, not a label"
        checked += 1
    assert checked >= 15


@pytest.mark.neo4j
def test_no_deity_response_leaks_an_internal(live_client: TestClient) -> None:
    for path, params in (
        ("/api/v1/devatas", {"limit": 50}),
        ("/api/v1/devatas", {"population": "all_ascriptions", "limit": 50}),
        (f"/api/v1/devatas/{INDRA}", {}),
        (f"/api/v1/devatas/{INDRA}/passages", {"limit": 50}),
        (f"/api/v1/devatas/{INDRA}/passages", {"basis": "ascription"}),
        (f"/api/v1/devatas/{INDRA}/network", {}),
    ):
        response = live_client.get(path, params=params)
        assert response.status_code == 200, path
        assert_no_internals(response.text)


@pytest.mark.neo4j
def test_deity_endpoints_answer_inside_the_latency_budget(
    live_client: TestClient, untraced_measurement: UntracedBlock
) -> None:
    """Median under 150ms, every endpoint under 300ms. Warmed, best of three.

    The budget is read with the coverage tracer paused; see the
    ``untraced_measurement`` fixture for why that is not cosmetic.
    """
    cases: list[tuple[str, dict[str, Any]]] = [
        ("/api/v1/devatas", {}),
        (f"/api/v1/devatas/{INDRA}", {}),
        (f"/api/v1/devatas/{AGNI}", {"certainty": "strict"}),
        (f"/api/v1/devatas/{INDRA}/passages", {"limit": 25}),
        (f"/api/v1/devatas/{INDRA}/network", {}),
    ]
    timings: dict[str, float] = {}
    for path, params in cases:
        # Traced, and deliberately outside the block below: the warm call is what keeps
        # these routes in the coverage report.
        live_client.get(path, params=params)
        with untraced_measurement():
            best = min(_elapsed_ms(live_client, path, params) for _ in range(3))
        timings[f"{path} {params}"] = best
    slow = {key: round(ms, 1) for key, ms in timings.items() if ms > 300}
    assert not slow, f"over the 300ms budget: {slow}"
    ordered = sorted(timings.values())
    median = ordered[len(ordered) // 2]
    assert median < 150, f"median {median:.1f}ms over budget: {timings}"


def _elapsed_ms(client: TestClient, path: str, params: dict[str, Any]) -> float:
    started = time.perf_counter()
    response = client.get(path, params=params)
    assert response.status_code == 200
    return (time.perf_counter() - started) * 1000
