"""Adversarial regression tests: one per CRITICAL or HIGH finding from the §44 sweep.

Two kinds of test live here and the distinction matters when reading a failure.

The **xfail(strict=True)** tests each encode a defect that was demonstrated against the
live graph and is *not yet fixed*. Each asserts the behaviour the product contract
promises, so it fails today, keeps the suite green, and flips to a pass the moment the
coordinator lands the fix. A strict xfail that starts XPASSing is the signal that the
finding is closed -- remove the marker, do not remove the test.

The **passing** tests are the other half of the sweep: the containments that held under
attack. They are here because each one is a property an attacker probed and could not
break, and a regression in any of them would itself be a CRITICAL. The graph census is the
bluntest of them: this whole audit was read-only, and a test that proves the node and
relationship counts are unchanged is the cheapest way to keep it that way.

Every test that reads Vedic content is marked ``neo4j``. The offline ones use
``FakeRepository`` because the assertion is about the HTTP contract -- a status code, an
error shape, whether a client string reached query text -- and a live graph would make them
slower without making them stronger.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository

# ---------------------------------------------------------------------------
# Measured constants. Every figure here was read off the live frozen graph during the
# adversarial sweep, so a rebuild that moves one fails a test rather than quietly
# invalidating the finding it anchors.
# ---------------------------------------------------------------------------
#: The frozen graph, as declared and as measured before and after the whole sweep. Imported
#: rather than restated: two copies of one census drift, and this file's copy said 108,779
#: for a whole import after the other was re-derived.
from tests.api.test_app_health import (
    FROZEN_NODES as EXPECTED_NODES,
)
from tests.api.test_app_health import (
    FROZEN_RELATIONSHIPS as EXPECTED_RELATIONSHIPS,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

#: Anukramani devata-slot entries the recorded ruling excludes, one per exclusion class.
#:
#: ``VG:DEVATA:SUNAH``, the dog, used to stand here for the UNSPECIFIED structure. It is a
#: DEITY under the ruling -- thirteen other animals are in the population and excluding this
#: one for its structure was "excluding on a morphological accident" -- so the third row is
#: an ABSTRACT label ruled ABSTRACTION_NOT_AN_ADDRESSEE, which is the class the superseded
#: structure predicate admitted and this sweep therefore never tested.
NON_DEITY_IDS: tuple[tuple[str, str], ...] = (
    ("VG:DEVATA:VASISTHAH", "HUMAN"),
    ("VG:DEVATA:DANASTUTIH", "PATRON_PRAISE"),
    ("VG:DEVATA:BHAVAVRTTAM", "ABSTRACT"),
)

#: RV 1.4.2 carries exactly one MENTIONS_DEVATA edge and it is graded DEITY_AMBIGUOUS.
AMBIGUOUS_ONLY_PASSAGE = "VG:RV:SAK:M01:S004:V002"

#: Deities whose profile statistics were never materialised on the node, while the insight
#: endpoint computes them live. ``/devatas/{id}`` reports null for all four corpora.
UNMATERIALISED_DEITIES: tuple[str, ...] = (
    "VG:DEVATA:SARASVATI",
    "VG:DEVATA:PRTHIVI",
    "VG:DEVATA:YAMAH",
    "VG:DEVATA:PARJANYAH",
)

#: The Atharvavedic seer whose list row and profile disagree by an order of magnitude.
ATHARVAN = "VG:RISHI:AV:ATHARVAN-A868"

#: Payloads that must never reach query text, and must never produce a 500.
INJECTION_PAYLOADS: tuple[str, ...] = (
    "' OR 1=1 --",
    '") RETURN 1 //',
    "\x00",
    "`",
    "VG:DEVATA:INDRAH'}) DETACH DELETE n //",
    "MATCH (n) DETACH DELETE n",
    "1) UNION MATCH (q:QAIssue) RETURN q //",
    "${jndi:ldap://x}",
    "{{7*7}}",
    "a\nRETURN 1\n",
    "\" ' \\ { } ( ) ~ * ? : ^ ] [ / AND OR NOT",
    "HAS_RISHI]->() DETACH DELETE n //",
    "HAS_RISHI`",
    "QA_ISSUE_ON",
    "../../etc/passwd",
    "QAIssue",
)

#: Every string-valued parameter the product exposes, as a URL template with one slot.
INJECTION_TARGETS: tuple[str, ...] = (
    "/api/v1/search?q={}",
    "/api/v1/search?q=agni&type={}",
    "/api/v1/search?q=agni&veda={}",
    "/api/v1/search?q=agni&work={}",
    "/api/v1/search?q=agni&language={}",
    "/api/v1/passages/{}",
    "/api/v1/passages/{}/reader",
    "/api/v1/works/{}",
    "/api/v1/devatas?structure={}",
    "/api/v1/devatas?axis={}",
    "/api/v1/devatas?population={}",
    "/api/v1/devatas?certainty={}",
    "/api/v1/devatas/{}",
    "/api/v1/devatas/VG:DEVATA:INDRAH/passages?basis={}",
    "/api/v1/devatas/VG:DEVATA:INDRAH/passages?veda={}",
    "/api/v1/entities/{}",
    "/api/v1/entities/rishi?name={}",
    "/api/v1/entities/condition?kind={}",
    "/api/v1/entities/rishi/{}",
    "/api/v1/rituals/{}",
    "/api/v1/formulas/{}",
    "/api/v1/formula-families/{}",
    "/api/v1/graph/neighborhood/{}",
    "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?types={}",
    "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?trust_tier={}",
    "/api/v1/graph/relationships/{}",
    "/api/v1/graph/path?from={}&to=VG:DEVATA:AGNIH",
    "/api/v1/graph/path?from=VG:DEVATA:INDRAH&to={}",
    "/api/v1/insights/devatas/{}",
    "/api/v1/insights/material-culture?category={}",
)

#: Every knowledge route. A dead graph must make each one a 503 that names nothing.
KNOWLEDGE_ROUTES: tuple[str, ...] = (
    "/api/v1/works",
    "/api/v1/works/VG:WORK:RV:SAK",
    "/api/v1/works/VG:WORK:RV:SAK/root",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/parent",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/children",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/siblings",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/reader",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/parallels",
    "/api/v1/search?q=agni",
    "/api/v1/devatas",
    "/api/v1/devatas/VG:DEVATA:INDRAH",
    "/api/v1/devatas/VG:DEVATA:INDRAH/passages",
    "/api/v1/devatas/VG:DEVATA:INDRAH/network",
    "/api/v1/entities",
    "/api/v1/entities/rishi",
    "/api/v1/entities/rishi/VG:RISHI:X",
    "/api/v1/rituals",
    "/api/v1/rituals/VG:CONCEPT:AGNIHOTRA",
    "/api/v1/formulas/VG:ENRICH:FORMULA:bbc0cacb972d846fcc13a1ecd2087735",
    "/api/v1/formula-families/VG:ENRICH:FORMULA-FAMILY:15978509b31e68df11a77d83ecdde6fd",
    "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH",
    "/api/v1/graph/path?from=VG:DEVATA:INDRAH&to=VG:DEVATA:AGNIH",
    "/api/v1/insights/cross-veda",
    "/api/v1/insights/devatas/VG:DEVATA:INDRAH",
    "/api/v1/insights/material-culture",
    "/api/v1/insights/rituals",
    "/api/v1/insights/atharvaveda/concerns",
    "/api/v1/insights/formula-diffusion",
    "/api/v1/insights/civilization",
    "/api/v1/insights/metals",
    "/api/v1/insights/capabilities",
    "/api/v1/stats",
)

#: Substrings a 503 body may not contain. Deliberately includes the lowercase driver
#: module name and the bolt scheme: a leak here is a leak of deployment topology.
OUTAGE_FORBIDDEN: tuple[str, ...] = (
    "bolt://",
    "localhost",
    "127.0.0.1",
    "7687",
    "neo4j",
    "Neo4j",
    "Cypher",
    "MATCH (",
    "RETURN ",
    "Traceback",
    "ServiceUnavailable",
    "GraphDatabase",
    "password",
)

#: Needles that must not appear in any product payload under any parameter.
LEAK_NEEDLES: tuple[str, ...] = (
    "QAIssue",
    "qa_issue",
    "issue_id",
    "QA_ISSUE_ON",
    "elementId",
    "element_id",
    "bolt://",
    "MATCH (",
    "OPTIONAL MATCH",
    "Traceback",
    "password",
)


def _encode(payload: str) -> str:
    return urllib.parse.quote(payload, safe="")


# ---------------------------------------------------------------------------
# 1. Deity type safety -- the containment that broke
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(("devata_id", "structure"), NON_DEITY_IDS)
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-01: /devatas/{id}/network applies the population contract to its edges but not to its
#: subject. _require_devata checks existence only, so a HUMAN, PATRON_PRAISE or UNSPECIFIED
#: ascription is served under the default population=deities as type=DEVATA -- and carries the
#: caveat 'This response excludes all 30' while being one of the 30. The dog reaches Indra and
#: Agni through shared_rishi_deities.
def test_f01_devata_network_refuses_a_non_deity_under_the_default_population(
    live_client: TestClient, devata_id: str, structure: str
) -> None:
    response = live_client.get(f"/api/v1/devatas/{devata_id}/network")
    assert response.status_code == 404, (
        f"{devata_id} is structure={structure} and population=deities is the default, so "
        f"the network endpoint must refuse it the way /devatas/{{id}} does; it returned "
        f"{response.status_code}"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(("devata_id", "structure"), NON_DEITY_IDS)
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-07: /devatas/{id}/passages takes no population parameter and applies no non-deity refusal,
#: so basis=ascription returns the dog's Anukramani slot as a 200 SUPPORTED page from a route
#: titled 'Passages naming or ascribed to a deity'. /devatas/{id} 404s for the same id: a
#: cross-endpoint contradiction.
def test_f07_devata_passages_refuses_or_types_a_non_deity(
    live_client: TestClient, devata_id: str, structure: str
) -> None:
    response = live_client.get(f"/api/v1/devatas/{devata_id}/passages?basis=ascription")
    if response.status_code == 404:
        return
    body = response.json()
    caveat_text = " ".join(caveat["text"] for caveat in body.get("caveats", []))
    assert structure in caveat_text, (
        f"{devata_id} is structure={structure}; a 200 from a deity route must state that "
        "this id is not a deity, and no caveat in the payload does"
    )


@pytest.mark.neo4j
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-03: the /entities/rishi payload caveat asserts verbatim 'Every row carries `is_seer` and
#: `non_seer_kind`' and the EntityListRow model declares neither. Row one is VG:RISHI:ADITIH,
#: whose non_seer_kind is DEITY, presented in a seer list with nothing marking it -- the same
#: defect EntityListRow's own docstring documents having fixed for Condition.kind.
def test_f03_rishi_list_rows_carry_the_is_seer_flag_its_caveat_promises(
    live_client: TestClient,
) -> None:
    response = live_client.get("/api/v1/entities/rishi?limit=200")
    assert response.status_code == 200
    body = response.json()
    promised = any(
        "is_seer" in caveat["text"] and "non_seer_kind" in caveat["text"]
        for caveat in body["caveats"]
    )
    assert promised, "the caveat asserting per-row seer typing has moved; re-read this test"
    missing = [row["id"] for row in body["items"] if "is_seer" not in row]
    assert not missing, (
        f"{len(missing)} of {len(body['items'])} rishi rows carry no is_seer field while "
        f"the response caveat says every row does; first: {missing[:3]}"
    )


@pytest.mark.neo4j
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-04: /entities/rishi reads passage_count from coalesce(mention_edges_total,
#: occurrence_count, ...), which for a Rishi lands on an unrelated registry statistic. 367 of
#: 729 seers report a bare 0 while carrying HAS_RISHI edges -- Vasistha, the most-attributed
#: seer in the Rigveda, reads 0 against 836 in the graph.
def test_f04_rishi_list_never_reports_a_bare_zero_where_the_graph_has_edges(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    truth = {
        str(row["k"]): int(row["c"])
        for row in live_repository.run(
            "MATCH (p:Passage)-[:HAS_RISHI]->(x:Rishi) RETURN x.entity_key AS k, count(p) AS c"
        )
    }
    rows: list[dict[str, Any]] = []
    for offset in range(0, 800, 200):
        page = live_client.get(f"/api/v1/entities/rishi?limit=200&offset={offset}")
        assert page.status_code == 200
        rows.extend(page.json()["items"])

    false_zeros = [
        (row["id"], truth[row["id"]])
        for row in rows
        if row.get("passage_count") == 0 and truth.get(row["id"], 0) > 0
    ]
    assert not false_zeros, (
        f"{len(false_zeros)} rishi rows report passage_count=0 while the graph carries "
        f"HAS_RISHI edges for them; worst: {sorted(false_zeros, key=lambda p: -p[1])[:3]}"
    )


@pytest.mark.neo4j
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-09: the same coalesce makes the list row disagree with the profile of the same node.
#: Atharvan reads passage_count 121 in /entities/rishi and 1282 in /entities/rishi/{id}; 501 of
#: 729 rows disagree with the graph's own edge count.
def test_f09_rishi_list_row_agrees_with_the_rishi_profile(live_client: TestClient) -> None:
    profile = live_client.get(f"/api/v1/entities/rishi/{ATHARVAN}")
    assert profile.status_code == 200
    expected = profile.json()["passage_count"]

    listed: int | None = None
    for offset in range(0, 800, 200):
        page = live_client.get(f"/api/v1/entities/rishi?limit=200&offset={offset}")
        for row in page.json()["items"]:
            if row["id"] == ATHARVAN:
                listed = row.get("passage_count")
    assert listed is not None, f"{ATHARVAN} did not appear in the paginated rishi list"
    assert listed == expected, (
        f"/entities/rishi reports passage_count={listed} for {ATHARVAN} and its own "
        f"profile reports {expected}"
    )


# ---------------------------------------------------------------------------
# 2. Ambiguous mention handling -- the surface that does not obey the default
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-02: /passages/{key}.mentioned_devatas collects every MENTIONS_DEVATA edge regardless of
#: referent_certainty, does not project the grade onto the row, offers no include_ambiguous
#: control, and _attribution_set gives a non-empty set data_status=SUPPORTED with caveats=[].
#: RV 1.4.2's single mention edge is DEITY_AMBIGUOUS and Soma the god is reported as named
#: there, as fact. 5,365 passages carry at least one AMBIGUOUS edge and 2,997 carry nothing
#: else.
def test_f02_passage_mentioned_devatas_obeys_the_ambiguity_contract(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    grades = {
        str(row["cert"])
        for row in live_repository.run(
            "MATCH (p:Passage {canonical_key: $key})-[m:MENTIONS_DEVATA]->() "
            "RETURN DISTINCT m.referent_certainty AS cert",
            key=AMBIGUOUS_ONLY_PASSAGE,
        )
    }
    assert grades == {"DEITY_AMBIGUOUS"}, (
        f"{AMBIGUOUS_ONLY_PASSAGE} no longer carries only ambiguous mentions ({grades}); "
        "pick another witness before reading this failure"
    )

    response = live_client.get(f"/api/v1/passages/{AMBIGUOUS_ONLY_PASSAGE}")
    assert response.status_code == 200
    block = response.json()["mentioned_devatas"]

    # Either the default excludes AMBIGUOUS -- so the block is empty and typed -- or it
    # includes them and says so. What it may not do is report them as SUPPORTED fact.
    if not block["items"]:
        assert block["data_status"] != "SUPPORTED"
        return
    stated = block["data_status"] != "SUPPORTED" or bool(block["caveats"])
    graded = all("referent_certainty" in item for item in block["items"])
    assert stated or graded, (
        "mentioned_devatas reported an AMBIGUOUS-only mention set with "
        f"data_status={block['data_status']!r}, {len(block['caveats'])} caveats and no "
        "per-row referent_certainty: the ambiguity contract is not applied here"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "devata_id",
    [
        "VG:DEVATA:AGNIH",
        "VG:DEVATA:SOMAH",
        "VG:DEVATA:SURYAH",
        "VG:DEVATA:MITRAH",
        "VG:DEVATA:SAVITA",
        "VG:DEVATA:USAH",
        "VG:DEVATA:VAYUH",
        "VG:DEVATA:APAH",
    ],
)
def test_certainty_strict_never_yields_a_bare_zero_for_a_non_rigvedic_corpus(
    live_client: TestClient, devata_id: str
) -> None:
    """The strict filter is a Rigvedic grade, so it must empty a corpus to null, not 0."""
    response = live_client.get(f"/api/v1/devatas/{devata_id}?certainty=strict")
    assert response.status_code == 200
    for row in response.json()["mentions_by_veda"]:
        assert row["count"] != 0, (
            f"{devata_id} {row['veda']} returned a bare 0 under certainty=strict; "
            "an emptied corpus must be null with INSUFFICIENT_EVIDENCE"
        )
        if row["veda"] != "RV" and row["count"] is None:
            assert row["status"] in {"INSUFFICIENT_EVIDENCE", "NOT_BUILT"}


@pytest.mark.neo4j
def test_devata_passages_excludes_ambiguous_by_default_and_admits_it_on_request(
    live_client: TestClient,
) -> None:
    """Soma is the witness the contract is written around: 421 by default, 1,512 with all."""
    base = "/api/v1/devatas/VG:DEVATA:SOMAH/passages?basis=mention&limit=5"
    default = live_client.get(base).json()
    widened = live_client.get(f"{base}&include_ambiguous=true").json()
    assert default["pagination"]["total"] < widened["pagination"]["total"]
    assert all(item["referent_certainty"] != "DEITY_AMBIGUOUS" for item in default["items"]), (
        "the default page must not contain an AMBIGUOUS mention"
    )


# ---------------------------------------------------------------------------
# 3. Zero versus unknown, and the cross-endpoint contradiction it produced
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize("devata_id", UNMATERIALISED_DEITIES)
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-05: /devatas/{id} reads its mention and attribution totals off materialised profile_*
#: properties that exist on only 30 of the 214 Devata nodes. For 15 deities with real
#: MENTIONS_DEVATA edges the flagship profile reports null for all four corpora with
#: INSUFFICIENT_EVIDENCE and no dimension_status naming the gap, while /insights/devatas/{id}
#: computes the counts live. Sarasvati: null against 65.
def test_f05_devata_profile_agrees_with_the_devata_insight(
    live_client: TestClient, devata_id: str
) -> None:
    profile = live_client.get(f"/api/v1/devatas/{devata_id}")
    insight = live_client.get(f"/api/v1/insights/devatas/{devata_id}")
    assert profile.status_code == 200
    assert insight.status_code == 200
    profile_total = profile.json()["mentions_included_total"]
    insight_total = insight.json()["named_total"]
    assert profile_total == insight_total, (
        f"/devatas/{devata_id} reports mentions_included_total={profile_total!r} while "
        f"/insights/devatas/{devata_id} reports named_total={insight_total!r}"
    )


@pytest.mark.neo4j
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-10: the /devatas/{id} OpenAPI description tells a client that '25 of the 214 deities carry
#: at least one' dimension_status, which invites the other 189 to be read without it. Measured,
#: all 214 carry one, because the service appends interpretive_claims unconditionally for 213
#: of them. The figure describes a graph property, not the response.
def test_f10_dimension_status_population_matches_the_documented_figure(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    row = live_repository.run_one(
        "MATCH (d:Devata) WHERE d.profile_absent_dimensions IS NOT NULL "
        "AND size(d.profile_absent_dimensions) > 0 RETURN count(d) AS c"
    )
    assert row is not None
    # 25 -> 152 at R4. GAP-ENTITY_COVERAGE-002 widened the profile materialisation from a
    # top-25 union to the 157 deities the eligibility contract admits, and 152 of them are
    # thin in at least one dimension -- which is the finding, not a defect. Re-derived from
    # the graph and still an equality, not loosened.
    assert int(row["c"]) == 152, "the graph's profile_absent_dimensions population has moved"

    keys = [
        str(item["k"])
        for item in live_repository.run(
            "MATCH (d:Devata) WHERE d.profile_absent_dimensions IS NULL "
            "OR size(d.profile_absent_dimensions) = 0 "
            "RETURN d.entity_key AS k ORDER BY k LIMIT 6"
        )
    ]
    assert keys, "every Devata carries profile_absent_dimensions; re-read this test"
    unexpected = []
    for key in keys:
        response = live_client.get(f"/api/v1/devatas/{key}?population=all_ascriptions")
        assert response.status_code == 200
        statuses = [entry["dimension"] for entry in response.json()["dimension_status"]]
        if statuses:
            unexpected.append((key, statuses))
    assert not unexpected, (
        "the description says 25 of 214 deities carry a dimension_status, but these are "
        f"outside the graph's set of 25 and carry one anyway: {unexpected[:3]}"
    )


@pytest.mark.neo4j
def test_q10_metals_grid_types_the_known_false_yajurvedic_cell(
    live_client: TestClient,
) -> None:
    """The ayas cell must be null with its locator, never 0 and never 'absent from YV'."""
    response = live_client.get("/api/v1/insights/metals")
    assert response.status_code == 200
    body = response.json()
    ayas = next(row for row in body["metals"] if row["entity_key"] == "VG:CONCEPT:AYAS-METAL")
    yv = next(cell for cell in ayas["by_veda"] if cell["veda"] == "YV")
    assert yv["matched_mantras"] is None, "the ayas/YV cell must be null, never 0"
    assert yv["evidence_status"] == "NO_LEXICAL_MATCH"
    assert yv["source_witness"] == "VSM 18.13"
    assert "VSM 18.13" in yv["note"]
    gap = next(row for row in body["declared_gaps"] if row["entity_key"] == "VG:CONCEPT:AYAS-METAL")
    assert gap["veda"] == "YV"
    assert gap["source_witness"] == "VSM 18.13"


@pytest.mark.neo4j
def test_q10_material_culture_metals_never_render_ayas_as_a_zero(
    live_client: TestClient,
) -> None:
    """The second rendering path over the same data must not lose the typing."""
    response = live_client.get("/api/v1/insights/material-culture?category=metals&limit=200")
    assert response.status_code == 200
    body = response.json()
    ayas = next(row for row in body["rows"] if row["label"].startswith("metal (ayas)"))
    assert ayas["by_veda"]["yv"] is None, "a YV zero here would be the Q10 defect returning"
    assert "NO_LEXICAL_MATCH" in ayas["evidence_status"]
    assert any("VSM 18.13" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.neo4j
def test_q23_deity_communities_is_a_typed_refusal_not_an_empty_list(
    live_client: TestClient,
) -> None:
    response = live_client.get("/api/v1/insights/capabilities?question=23")
    assert response.status_code == 200
    limits = response.json()["limits"]
    assert len(limits) == 1
    limit = limits[0]
    assert limit["verdict"] == "NOT_ANSWERABLE"
    assert limit["data_status"] == "NOT_BUILT"
    assert limit["why"]
    assert limit["what_this_is_not"]
    assert limit["safe_alternative"]


@pytest.mark.neo4j
def test_q25_ritual_layer_is_partial_and_names_both_step_layers(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """Both layers by their own count, and neither one standing in for the other.

    The original form asserted the literal "3 step edges", which was the whole ritual
    procedure figure at the time. Wave 3 added a second layer of 3,121 sutra-attested steps,
    and a caveat quoting only the Samhita's 3 would state that this graph holds almost no
    procedure while the larger layer sat beside it. So the caveat must name both, and the
    counts are read out of the graph rather than written here.
    """
    samhita = live_repository.run_one("MATCH ()-[s:HAS_STEP]->() RETURN count(s) AS c")
    sutra = live_repository.run_one("MATCH ()-[s:HAS_RITUAL_STEP]->() RETURN count(s) AS c")
    assert samhita is not None and sutra is not None
    assert int(samhita["c"]) == 3, "the Samhita step layer must not be widened in place"

    response = live_client.get("/api/v1/insights/rituals?limit=200")
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == "PARTIAL"
    text = " ".join(caveat["text"] for caveat in body["caveats"])
    assert f"{int(samhita['c'])} such edges" in text
    assert f"{int(sutra['c']):,} steps" in text
    assert body["not_covered"]


@pytest.mark.neo4j
def test_samavedic_translations_are_a_typed_unbuilt_layer_not_an_empty_list(
    live_client: TestClient,
) -> None:
    response = live_client.get("/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01")
    assert response.status_code == 200
    block = response.json()["translations"]
    assert block["items"] == []
    assert block["data_status"] == "NOT_BUILT"
    assert block["coverage"]["vedas_not_covered"] == ["SV"]
    assert any("1,844" in caveat["text"] for caveat in block["caveats"])


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("key", "veda"),
    [
        ("VG:SV:KAU:ARANYA:D01:V01", "SV"),
        ("VG:YV:VSM:A01:V001", "YV"),
        ("VG:AV:SAU:K01:S001:V001", "AV"),
    ],
)
def test_has_devata_is_rigvedic_and_a_non_rigvedic_zero_says_so(
    live_client: TestClient, key: str, veda: str
) -> None:
    block = live_client.get(f"/api/v1/passages/{key}").json()["devatas"]
    assert block["items"] == []
    assert block["data_status"] == "NOT_BUILT"
    assert block["coverage"]["vedas_not_covered"] == [veda]
    assert any("Rigveda-only" in caveat["text"] for caveat in block["caveats"])


@pytest.mark.neo4j
def test_no_empty_first_page_ever_claims_supported(live_client: TestClient) -> None:
    """The Paginated guard, attacked with the filter combinations that empty a page."""
    candidates = [
        "/api/v1/devatas?structure=HUMAN",
        "/api/v1/devatas?structure=NOPE",
        "/api/v1/devatas?axis=NOPE",
        "/api/v1/devatas?structure=INDIVIDUAL&axis=NOPE",
        "/api/v1/devatas/VG:DEVATA:BHAVAVRTTAM/passages?basis=mention",
        "/api/v1/devatas/VG:DEVATA:INDRAH/passages?basis=ascription&veda=SV",
        "/api/v1/devatas/VG:DEVATA:INDRAH/passages?basis=ascription&veda=AV",
        "/api/v1/devatas/VG:DEVATA:INDRAH/passages?basis=ascription&veda=YV",
        "/api/v1/entities/rishi?name=zzzznope",
        "/api/v1/entities/concept?name=zzzznope",
        "/api/v1/passages/VG:RV:SAK:M01:S001:V001/children",
        "/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01/children",
        "/api/v1/search?q=zzzznope",
        "/api/v1/search?q=zzzznope&type=devata",
        "/api/v1/search?q=agni%20soma%20indra%20varuna%20mitra",
        "/api/v1/insights/material-culture?limit=200&offset=39",
    ]
    offenders = []
    for url in candidates:
        response = live_client.get(url)
        if response.status_code != 200:
            continue
        body = response.json()
        collection = body.get("items")
        if collection is None:
            collection = body.get("rows")
        pagination = body.get("pagination")
        if collection or not isinstance(pagination, dict) or pagination.get("offset") != 0:
            continue
        if body.get("data_status") == "SUPPORTED" and not body.get("caveats"):
            offenders.append(url)
    assert not offenders, f"empty first pages claiming SUPPORTED with no caveat: {offenders}"


# ---------------------------------------------------------------------------
# 4. Caveat correctness, cross-checked against the live graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_the_seer_layer_caveat_figures_still_match_the_graph(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """V3.1 and V3.2 both shipped drifted caveat prose. These four numbers are the check."""
    measured = {
        (str(row["veda"]), str(row["precision"])): int(row["c"])
        for row in live_repository.run(
            "MATCH (p:Passage)-[x:HAS_RISHI]->() "
            "RETURN p.veda AS veda, x.attribution_precision AS precision, count(*) AS c"
        )
    }
    total = sum(measured.values())
    inherited = sum(
        c for (_, precision), c in measured.items() if precision == "CONTAINER_INHERITED"
    )
    text = " ".join(
        caveat["text"]
        for caveat in live_client.get("/api/v1/passages/VG:RV:SAK:M01:S001:V001").json()["rishis"][
            "caveats"
        ]
    )
    assert f"{total:,}" in text, f"the caveat no longer states the measured total {total:,}"
    assert f"{inherited:,}" in text
    assert f"{measured[('AV', 'CONTAINER_INHERITED')]:,}" in text
    assert f"{measured[('YV', 'PER_PASSAGE')]:,}" in text


@pytest.mark.neo4j
def test_the_mention_layer_caveat_figures_still_match_the_graph(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    per_veda = {
        str(row["veda"]): int(row["c"])
        for row in live_repository.run(
            "MATCH (p:Passage)-[m:MENTIONS_DEVATA]->() RETURN p.veda AS veda, count(m) AS c"
        )
    }
    text = " ".join(
        caveat["text"]
        for caveat in live_client.get("/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01").json()[
            "devatas"
        ]["caveats"]
    )
    assert f"{sum(per_veda.values()):,}" in text
    for veda, count in per_veda.items():
        assert f"{veda} {count:,}" in text, f"{veda} {count:,} is not in the caveat"


@pytest.mark.neo4j
def test_the_deity_population_caveat_matches_the_measured_structures(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """The caveat's figures are measured, and measured from the ruling that decides them.

    This derived its expectation from ``structure``, which is what made the caveat say 30
    and name a dog among the excluded. Eligibility is the recorded ruling, so the figure a
    reader is given has to come from the same place the filter does -- otherwise the caveat
    can be true about structures while the response is filtered on something else.
    """
    kinds = {
        str(row["k"]): int(row["c"])
        for row in live_repository.run(
            "MATCH (d:Devata) WHERE d.is_deity = false "
            "RETURN coalesce(d.non_deity_kind,'UNTYPED') AS k, count(*) AS c"
        )
    }
    total = int(live_repository.run_one("MATCH (d:Devata) RETURN count(d) AS c")["c"])
    excluded = sum(kinds.values())
    assert "UNTYPED" not in kinds, f"a deity is excluded with no recorded kind: {kinds}"
    text = " ".join(
        caveat["text"] for caveat in live_client.get("/api/v1/devatas").json()["caveats"]
    )
    assert f"{excluded} of the {total}" in text
    assert f"{kinds['HUMAN_PATRON']} " in text
    assert f"{kinds['DANASTUTI_GIFT_PRAISE']} danastuti" in text
    assert f"{kinds['ABSTRACTION_NOT_AN_ADDRESSEE']} abstractions" in text


@pytest.mark.neo4j
def test_caveats_sourced_from_the_frozen_library_match_it_verbatim(
    live_client: TestClient,
) -> None:
    from vedagraph.api.repositories.neo4j_repository import named_query_caveat

    checks = (
        ("/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01", "devatas", "deity_profile"),
        ("/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01", "rishis", "rishi_layer_reach_by_veda"),
    )
    for path, block, query_name in checks:
        frozen = named_query_caveat(query_name)
        assert frozen, f"{query_name} carries no caveat in the frozen library"
        served = [
            caveat["text"]
            for caveat in live_client.get(path).json()[block]["caveats"]
            if caveat["source"] == query_name
        ]
        assert served, f"{path} {block} carries no caveat sourced {query_name}"
        assert frozen in served, (
            f"{path} {block} paraphrased the frozen {query_name} caveat instead of "
            "reusing it, which is how V3.1 and V3.2 shipped drifted prose"
        )


# ---------------------------------------------------------------------------
# 5. Pagination and filter validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "-1", "201", "999999", "1e9", "abc", "1.5", "%20"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/works",
        "/api/v1/devatas",
        "/api/v1/entities/rishi",
        "/api/v1/rituals",
        "/api/v1/insights/material-culture",
        "/api/v1/insights/civilization",
    ],
)
def test_out_of_range_limit_is_refused_and_never_silently_truncated(
    client: TestClient, path: str, value: str
) -> None:
    response = client.get(f"{path}?limit={value}")
    assert response.status_code == 422, (
        f"{path}?limit={value} returned {response.status_code}; a bound this API cannot "
        "serve must be refused, because a truncated page is indistinguishable from the end"
    )
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("parameter", ["structure", "axis"])
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-08: list_devatas binds structure and axis straight through with no check against their
#: value spaces, so a misspelling yields 200 with total=0 and no caveat distinguishing an
#: invalid filter from an empty result. /entities/{type} handles the same case correctly,
#: adding 'an unknown type would have been a 400'.
def test_f08_unknown_devata_filter_value_is_a_400_naming_the_problem(
    client: TestClient, parameter: str
) -> None:
    response = client.get(f"/api/v1/devatas?{parameter}=NOT_A_REAL_VALUE")
    assert response.status_code == 400, (
        f"?{parameter}=NOT_A_REAL_VALUE returned {response.status_code} rather than a 400 "
        "naming the unknown value"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("base", "identity"),
    [
        ("/api/v1/devatas", "id"),
        ("/api/v1/devatas?population=all_ascriptions", "id"),
        ("/api/v1/entities/rishi", "id"),
        ("/api/v1/entities/concept", "id"),
        ("/api/v1/devatas/VG:DEVATA:AGNIH/passages", "passage_id"),
    ],
)
def test_walking_a_collection_page_by_page_neither_skips_nor_duplicates(
    live_client: TestClient, base: str, identity: str
) -> None:
    separator = "&" if "?" in base else "?"
    seen: list[str] = []
    offset = 0
    total: int | None = None
    for _ in range(40):
        page = live_client.get(f"{base}{separator}limit=200&offset={offset}").json()
        seen.extend(str(row[identity]) for row in page["items"])
        total = page["pagination"]["total"]
        if not page["items"] or not page["pagination"]["has_more"]:
            break
        offset += 200
    assert total is not None
    assert len(seen) == total, f"{base}: walked {len(seen)} rows against total {total}"
    assert len(set(seen)) == len(seen), f"{base}: the walk returned duplicate rows"


@pytest.mark.neo4j
def test_deep_paging_on_search_is_refused_rather_than_served_incompletely(
    live_client: TestClient,
) -> None:
    response = live_client.get("/api/v1/search?q=agni&limit=5&offset=99999999")
    assert response.status_code == 400
    assert response.json()["error"] == "BAD_REQUEST"


# ---------------------------------------------------------------------------
# 6. Path explosion and fan-out bounds
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "node_id",
    [
        "VG:DEVATA:INDRAH",
        "VG:DEVATA:AGNIH",
        "VG:CHANDAS:TRISTUP",
        "VG:CONCEPT:SOMA-DRINK",
        "VG:CONCEPT:DYAUS-HEAVEN",
    ],
)
def test_hub_neighbourhood_stays_bounded_in_size(live_client: TestClient, node_id: str) -> None:
    url = f"/api/v1/graph/neighborhood/{node_id}?depth=2&limit_per_type=50&include_internal=true"
    response = live_client.get(url)
    assert response.status_code == 200
    assert len(response.content) < 1_000_000, (
        f"{node_id} returned {len(response.content)} bytes; an unbounded response is a "
        "denial-of-service vector whatever it contains"
    )
    bounds = response.json()["bounds"]
    assert bounds["returned_nodes"] <= bounds["node_budget"]


@pytest.mark.neo4j
def test_an_unconnected_pair_is_a_typed_answer_not_a_404_or_an_outage(
    live_client: TestClient,
) -> None:
    response = live_client.get(
        "/api/v1/graph/path?from=VG:CONCEPT:LOHA-COPPER&to=VG:CONCEPT:UNMADA-MADNESS&max_depth=4"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hops"] == []
    assert body["data_status"] == "INSUFFICIENT_EVIDENCE"
    assert body["caveats"], "a route this search could not find must say what it searched"


@pytest.mark.neo4j
def test_a_self_path_is_explained_rather_than_fabricated(live_client: TestClient) -> None:
    response = live_client.get("/api/v1/graph/path?from=VG:DEVATA:INDRAH&to=VG:DEVATA:INDRAH")
    assert response.status_code == 200
    body = response.json()
    assert body["length"] == 0
    assert body["hops"] == []
    assert any("same node" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.parametrize("depth", ["0", "5", "99", "-1", "abc"])
def test_path_depth_outside_its_bounds_is_a_422(client: TestClient, depth: str) -> None:
    response = client.get(
        f"/api/v1/graph/path?from=VG:DEVATA:INDRAH&to=VG:DEVATA:AGNIH&max_depth={depth}"
    )
    assert response.status_code == 422


#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-06: Neo4jRepository.run calls session.run(cypher, parameters, timeout=...), but on the
#: installed driver Session.run's **kwargs are additional *query parameters*, which 'take
#: precedence over parameters passed as parameters'. So the configured budget is injected into
#: every query as $timeout and no query timeout is enforced: a read-only query completed in
#: 1.07s under a 0.001s budget, and RETURN $timeout echoes the configured value. The documented
#: 15s bound and the 503-on-budget path do not exist. Use neo4j.Query(cypher, timeout=...)
#: instead.
def test_f06_query_timeout_is_a_driver_option_and_not_a_cypher_parameter() -> None:
    from vedagraph.api.config import ApiSettings

    captured: dict[str, Any] = {}

    class FakeResult:
        def __iter__(self) -> Any:
            return iter(())

    class FakeSession:
        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def run(self, query: Any, parameters: Any = None, **kwargs: Any) -> FakeResult:
            captured["parameters"] = parameters
            captured["kwargs"] = kwargs
            return FakeResult()

    class FakeDriver:
        def session(self, **_: Any) -> FakeSession:
            return FakeSession()

        def close(self) -> None:
            return None

    repository = Neo4jRepository(ApiSettings(neo4j_query_timeout_seconds=7.5))
    repository._driver = FakeDriver()  # type: ignore[assignment]
    repository.run("RETURN 1 AS one", key="value")

    parameters: dict[str, Any] = dict(captured["parameters"] or {})
    parameters.update(captured["kwargs"])
    assert "timeout" not in parameters, (
        "the query budget reached the driver as a Cypher parameter named 'timeout', so no "
        f"timeout is enforced; parameters were {sorted(parameters)}"
    )


# ---------------------------------------------------------------------------
# 7 and 8. Injection, in every string parameter and every relationship type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_no_client_string_ever_reaches_query_text(payload: str) -> None:
    """Every string parameter, every payload: bound, never spliced, and never a 500."""
    from vedagraph.api.app import create_app
    from vedagraph.api.dependencies import get_repository

    app = create_app()
    for template in INJECTION_TARGETS:
        repository = FakeRepository()
        app.dependency_overrides[get_repository] = lambda bound=repository: bound
        test_client = TestClient(app, raise_server_exceptions=False)
        app.state.repository = repository
        url = template.format(_encode(payload))
        response = test_client.get(url)
        assert response.status_code < 500, (
            f"{url} returned {response.status_code}; a hostile string must be refused, "
            "not crash the handler"
        )
        if len(payload) >= 3:
            assert payload not in repository.query_text, (
                f"{payload!r} was spliced into the Cypher issued for {url}"
            )


@pytest.mark.parametrize(
    "payload",
    [
        "HAS_RISHI]->() DETACH DELETE n //",
        "HAS_RISHI`",
        "FOO",
        "*",
        "",
        "QA_ISSUE_ON",
        "CONTAINS",
        "HAS_TEXT_VERSION",
        "MENTIONS_LEMMA",
        "ASSERTION_TARGET",
        "has_rishi",
    ],
)
def test_a_non_traversable_relationship_type_is_a_400_naming_it(
    client: TestClient, payload: str
) -> None:
    response = client.get(f"/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?types={_encode(payload)}")
    assert response.status_code == 400, (
        f"types={payload!r} returned {response.status_code}; a type outside the traversal "
        "whitelist must be refused by name, never served as an empty graph"
    )
    body = response.json()
    assert payload in body["detail"]
    assert body["hint"], "the refusal must say which types are traversable"


def test_five_hundred_repeated_type_parameters_stay_bounded(client: TestClient) -> None:
    query = "&".join(["types=HAS_RISHI"] * 500)
    response = client.get(f"/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?{query}")
    assert response.status_code < 500


def test_a_query_string_of_twenty_kilobytes_is_not_a_server_error(client: TestClient) -> None:
    junk = "&".join(f"junk{index}=x" for index in range(2500))
    response = client.get(f"/api/v1/search?q=agni&{junk}")
    assert response.status_code < 500


@pytest.mark.neo4j
def test_the_graph_census_is_unchanged(live_repository: Neo4jRepository) -> None:
    """Nothing in this audit, or in any request it makes, may write to the graph."""
    nodes = live_repository.run_one("MATCH (n) RETURN count(n) AS c")
    relationships = live_repository.run_one("MATCH ()-[r]->() RETURN count(r) AS c")
    assert nodes is not None
    assert relationships is not None
    assert int(nodes["c"]) == EXPECTED_NODES
    assert int(relationships["c"]) == EXPECTED_RELATIONSHIPS


# ---------------------------------------------------------------------------
# 9. Neo4j downtime
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", KNOWLEDGE_ROUTES)
def test_every_knowledge_route_is_a_clean_503_when_the_graph_is_down(
    down_client: TestClient, path: str
) -> None:
    response = down_client.get(path)
    assert response.status_code == 503, f"{path} returned {response.status_code}"
    assert response.json()["error"] == "KNOWLEDGE_GRAPH_UNAVAILABLE"
    for needle in OUTAGE_FORBIDDEN:
        assert needle not in response.text, f"{path} leaked {needle!r} in a 503 body"


def test_health_stays_up_and_ready_names_the_failing_check_when_the_graph_is_down(
    down_client: TestClient,
) -> None:
    health = down_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = down_client.get("/ready")
    assert ready.status_code == 503
    body = ready.json()
    assert body["ready"] is False
    failing = {check["name"] for check in body["checks"] if not check["ok"]}
    assert "neo4j_reachable" in failing, "a 503 readiness body must name the failing check"
    assert "password" not in ready.text


# ---------------------------------------------------------------------------
# 10. Internal and interpretive leakage
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/stats",
        "/api/v1/works/VG:WORK:RV:SAK",
        "/api/v1/passages/VG:RV:SAK:M01:S001:V001",
        "/api/v1/passages/VG:RV:SAK:M01:S001:V001/reader",
        "/api/v1/passages/VG:RV:SAK:M01:S001:V001/parallels?limit=200",
        "/api/v1/search?q=agni&limit=200",
        "/api/v1/devatas?limit=200&population=all_ascriptions",
        "/api/v1/devatas/VG:DEVATA:INDRAH",
        "/api/v1/devatas/VG:DEVATA:INDRAH/network?population=all_ascriptions",
        "/api/v1/entities/rishi?limit=200",
        "/api/v1/entities/rishi/VG:RISHI:VAISVAMITRO-MADHUCCHANDAH",
        "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?depth=2&include_internal=true",
        "/api/v1/graph/neighborhood/VG:RV:SAK:M01:S001:V001?depth=2&include_internal=true",
        "/api/v1/insights/civilization?limit=200",
        "/api/v1/insights/metals",
        "/api/v1/insights/capabilities",
    ],
)
def test_no_qa_finding_or_neo4j_identity_reaches_any_payload(
    live_client: TestClient, path: str
) -> None:
    response = live_client.get(path)
    assert response.status_code == 200
    for needle in LEAK_NEEDLES:
        assert needle not in response.text, f"{path} leaked {needle!r}"


@pytest.mark.neo4j
def test_interpretive_claims_stay_typed_apart_from_data_and_derived_metrics(
    live_client: TestClient,
) -> None:
    response = live_client.get("/api/v1/insights/civilization?limit=200")
    assert response.status_code == 200
    sections = {section["section_kind"]: section for section in response.json()["sections"]}
    assert set(sections) == {"DATA", "DERIVED_METRIC", "INTERPRETIVE_CLAIM"}
    claims = sections["INTERPRETIVE_CLAIM"]
    assert claims["data_status"] == "INSUFFICIENT_EVIDENCE"
    assert claims["claim_rows"]
    assert sections["DATA"]["claim_rows"] == []
    assert sections["DERIVED_METRIC"]["claim_rows"] == []


# ---------------------------------------------------------------------------
# 11. Scope and completeness
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/stats",
        "/api/v1/insights/cross-veda",
        "/api/v1/insights/material-culture?limit=200",
        "/api/v1/insights/formula-diffusion?limit=200",
        "/api/v1/insights/civilization?limit=200",
        "/api/v1/insights/metals",
    ],
)
def test_every_per_corpus_figure_carries_its_exclusions(live_client: TestClient, path: str) -> None:
    body = live_client.get(path).json()
    scopes = {statement["veda"]: statement for statement in body["scope_statements"]}
    assert {"RV", "AV", "YV", "SV"} <= set(scopes), path
    assert "THIS IS NOT THE COMPLETE SAMAVEDA" in scopes["SV"]["scope"]
    assert "SAMAVEDA_GRAMAGEYA_GANA" in scopes["SV"]["excluded_corpora"]
    assert "KRISHNA" in scopes["YV"]["scope"]
    assert any("KRISHNA" in code for code in scopes["YV"]["excluded_corpora"])
    assert "PAIPPALADA" in scopes["AV"]["scope"]
    assert "ATHARVAVEDA_PAIPPALADA_RECENSION" in scopes["AV"]["excluded_corpora"]


# ---------------------------------------------------------------------------
# 12. Invalid canonical keys and ids
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "key",
    [
        "VG:RV:SAK:M99:S999:V999",
        "VG:RV",
        "VG:RV:SAK:K01",
        "%20",
        "RV%201.1.10",
        "VG:RV:SAK:M01:S001%0AV001",
        "VG:RV:S%D0%90K:M01:S001:V001",
        "x" * 2000,
    ],
)
def test_a_bad_passage_reference_is_a_clean_refusal(live_client: TestClient, key: str) -> None:
    response = live_client.get(f"/api/v1/passages/{key}")
    assert response.status_code in {400, 404, 422}, (
        f"/passages/{key[:40]} returned {response.status_code}"
    )
    if response.status_code == 404:
        assert response.json()["error"] == "PASSAGE_NOT_FOUND"


@pytest.mark.neo4j
def test_rv_1_1_10_does_not_exist_and_is_not_resolved_to_a_neighbour(
    live_client: TestClient,
) -> None:
    """RV 1.1 has nine verses. A tenth must 404, never resolve to something adjacent."""
    assert live_client.get("/api/v1/passages/RV%201.1.9").status_code == 200
    response = live_client.get("/api/v1/passages/RV%201.1.10")
    assert response.status_code == 404
    assert "1.1.10" in response.json()["detail"]


@pytest.mark.neo4j
@pytest.mark.parametrize("token", ["4:abc-def:12345", "12345", "AAAA", "r1-QUJD"])
def test_a_neo4j_identity_is_never_accepted_as_a_relationship_id(
    live_client: TestClient, token: str
) -> None:
    response = live_client.get(f"/api/v1/graph/relationships/{token}")
    assert response.status_code == 400
    assert response.json()["error"] == "BAD_REQUEST"


# ---------------------------------------------------------------------------
# HTTP hygiene
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", ["/health", "/api/v1/works", "/api/v1/entities", "/api/v1/devatas"]
)
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-11: no route declares HEAD, so Starlette answers 405. RFC 9110 requires a general-purpose
#: server to support HEAD wherever it supports GET, and health checkers, caches and link
#: validators use it.
def test_f11_head_is_supported_wherever_get_is(client: TestClient, path: str) -> None:
    response = client.request("HEAD", path)
    assert response.status_code != 405, f"HEAD {path} returned 405"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/no-such-route"),
        ("GET", "/api/v1/"),
        ("POST", "/api/v1/works"),
        ("DELETE", "/api/v1/devatas/VG:DEVATA:INDRAH"),
    ],
)
#: CLOSED in the fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: F-12: errors.py promises 'the single error shape every failing route returns', but
#: Starlette's HTTPException handler is not replaced, so an unmatched route and a wrong method
#: answer with {'detail': ...} and no `error` code. A client written against ErrorBody cannot
#: parse either.
def test_f12_router_level_failures_use_the_documented_error_shape(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path)
    assert response.status_code >= 400
    body = response.json()
    assert set(body) >= {"error", "detail"}, (
        f"{method} {path} returned {sorted(body)}; every failure must carry an `error` code"
    )


@pytest.mark.parametrize(
    "accept",
    ["application/xml", "text/html", "*/*", "garbage/garbage", "application/json;q=0.1"],
)
def test_an_absurd_accept_header_does_not_change_the_representation(
    client: TestClient, accept: str
) -> None:
    response = client.get("/api/v1/works", headers={"Accept": accept})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.neo4j
def test_openapi_builds_and_every_operation_is_tagged_and_summarised(
    live_client: TestClient,
) -> None:
    response = live_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    untagged = [
        f"{method.upper()} {path}"
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
        if not operation.get("tags") or not operation.get("summary")
    ]
    assert not untagged, f"operations missing a tag or a summary: {untagged}"


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/devatas?limit=50",
        "/api/v1/entities/rishi?limit=50",
        "/api/v1/search?q=agni&limit=50",
        "/api/v1/stats",
        "/api/v1/insights/civilization",
        "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH",
        "/api/v1/graph/path?from=VG:DEVATA:INDRAH&to=VG:DEVATA:AGNIH",
    ],
)
def test_the_same_request_five_times_returns_the_same_bytes(
    live_client: TestClient, path: str
) -> None:
    """Unstable ordering in a paginated collection is how a page walk skips a row."""
    bodies = {live_client.get(path).content for _ in range(5)}
    assert len(bodies) == 1, f"{path} is not byte-stable across five identical calls"


# ---------------------------------------------------------------------------
# 14. Second pass: findings against the code the first round's fixes introduced
#
# Everything below this line was written in the second adversarial pass, against the
# deity gate, the subject-disclosure producer, the diacritic-folding search rung, the
# HEAD middleware, the Starlette error handler, the neo4j.Query timeout and the live
# deity aggregation -- none of which existed when the first pass ran.
# ---------------------------------------------------------------------------

#: Combining marks that occur in this graph's entity labels, with their frequencies.
#: Measured over the 9,150 distinct label strings on the eleven searchable label sets, so
#: a rebuild that introduces a new mark fails a test rather than silently losing recall.
LABEL_COMBINING_MARKS: dict[str, int] = {
    "̄": 13_307,  # macron
    "̣": 11_194,  # dot below
    "́": 2_062,  # acute
    "̇": 1_199,  # dot above
    "̥": 372,  # ring below -- NOT in DIACRITIC_MARKS
    "्": 290,  # devanagari virama -- NOT in DIACRITIC_MARKS
    "̃": 282,  # tilde
    "̧": 97,  # cedilla -- NOT in DIACRITIC_MARKS
    "̐": 51,  # candrabindu -- NOT in DIACRITIC_MARKS
    "̱": 30,  # macron below
    "̈": 1,  # diaeresis
}

#: A label the fold cannot reach: its C-cedilla decomposes to a mark the table omits.
UNREACHABLE_FOLDED_LABEL = "Çam̄tāti"

#: The Cypher clause keywords that mark a string constant as a query rather than prose.
CYPHER_CLAUSE_WORDS = ("MATCH", "RETURN", "WITH", "UNWIND", "CALL", "WHERE")

#: Structures whose subjects the default deity population admits.
DEITY_STRUCTURE_NAMES = frozenset({"INDIVIDUAL", "GROUP", "PAIR", "ABSTRACT"})


def _all_devata_keys(repository: Neo4jRepository) -> list[tuple[str, bool]]:
    """Every ``:Devata`` key with its recorded eligibility ruling. All 214, never a sample.

    This project has twice certified an absence from a sample that a full sweep
    contradicted, and the deity population is 214 rows: there is no reason to sample it.

    Returns the ruling, not the structure. Deriving eligibility from structure here made
    these sweeps agree with a gate that was itself wrong about 29 nodes -- they asked about
    the dog, whom the ruling admits, and never asked about the 28 ruled abstractions.
    """
    rows = repository.run(
        "MATCH (d:Devata) RETURN d.entity_key AS key, d.is_deity AS is_deity "
        "ORDER BY d.entity_key"
    )
    return [(str(row["key"]), row["is_deity"] is True) for row in rows]


def _devata_url(key: str, is_deity: bool, base: str = "/api/v1/devatas") -> str:
    """The URL that serves ``key``, opting into the Anukramani slot only where it must.

    ``base`` exists because this helper was originally applied to the profile URL only,
    while the insight URL beside it was called bare. That asymmetry was correct while
    ``/insights/devatas/{id}`` had no population gate -- and became wrong the moment G-01
    was fixed, at which point the bare call started returning 404 for all 30 non-deities and
    this test failed for the right reason on the wrong line. Every deity surface must be
    addressed the same way, which is the whole content of G-01.
    """
    if is_deity:
        return f"{base}/{key}"
    return f"{base}/{key}?population=all_ascriptions"


def _caveat_texts(payload: Any) -> str:
    """Every ``caveats[].text`` anywhere in a response, joined.

    Walks rather than indexes because the disclosure contract does not say *where* the
    caveat sits, only that the response carries it -- and the sites the first pass found
    put it at three different depths.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "caveats" and isinstance(value, list):
                    found.extend(
                        str(item.get("text", item)) if isinstance(item, dict) else str(item)
                        for item in value
                    )
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return " || ".join(found)


# -- G-01 ------------------------------------------------------------------------------


@pytest.mark.neo4j
#: CLOSED in the second fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: G-01: /insights/devatas/{id} never passes through the deity gate. It declares no population
#: parameter, so all 30 non-deity Anukramani ascriptions are served on it under the DEFAULT
#: population -- the dog included -- while /devatas/{id}, /devatas/{id}/network and
#: /devatas/{id}/passages 404 for the same id in the same API. It reports is_resolved_deity
#: false and a structure, so it has the machine-readable half of the disclosure, but
#: subject_disclosure() is never called here and the THIS SUBJECT IS NOT A DEITY caveat is
#: absent, while its question field reads 'How far does this deity reach, by naming and by
#: ascription?'. One deity gate that a fourth deity route can still bypass is not a chokepoint.
def test_g01_the_deity_insight_route_gates_and_discloses_a_non_deity(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """The disclosure contract must hold on every route that serves a devata-slot subject.

    Asserted over all 30 non-deities rather than one, because the first pass's own F-01
    test asserted a single route under a single population and passed while two other
    halves of the same contract were open.
    """
    non_deities = [
        (key, ruled) for key, ruled in _all_devata_keys(live_repository) if not ruled
    ]
    assert len(non_deities) == 57, f"the non-deity population moved: {len(non_deities)}"

    served_by_default: list[str] = []
    missing_caveat: list[str] = []
    for key, _ruled in non_deities:
        response = live_client.get(f"/api/v1/insights/devatas/{key}")
        if response.status_code == 200:
            served_by_default.append(key)
            if "NOT A DEITY" not in _caveat_texts(response.json()).upper():
                missing_caveat.append(key)

    assert not served_by_default, (
        f"{len(served_by_default)} non-deities are served on /insights/devatas/{{id}} under "
        f"the default population, e.g. {served_by_default[:3]}, while /devatas/{{id}} 404s "
        "for the same ids"
    )
    assert not missing_caveat, (
        f"{len(missing_caveat)} non-deity subjects reach /insights/devatas/{{id}} without "
        f"the THIS SUBJECT IS NOT A DEITY caveat, e.g. {missing_caveat[:3]}"
    )


# -- G-02 ------------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize("mark", ["̄", "̣", "́", "̃", "̇"])
#: CLOSED in the second fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: G-02: the FOLDED_ENTITY_LABEL rung folds the query in Python before binding it as $q_folded,
#: and a query made only of combining marks folds to the EMPTY STRING. The prefix rung then
#: evaluates any(x IN folded_names WHERE x STARTS WITH ''), which is true of every string, so
#: GET /api/v1/search?q=%CC%84 returns every entity in the graph at match_type
#: PREFIX_ENTITY_LABEL with score 0.8 -- an assertion that a bare macron is a prefix of
#: 'Indra'. str.strip() does not remove combining marks, so the empty-q guard never sees it.
#: Every one of the 12 declared DIACRITIC_MARKS does this on its own.
def test_g02_a_bare_combining_mark_is_not_a_prefix_of_every_label(
    live_client: TestClient, mark: str
) -> None:
    """A rung is a claim about the query. An empty fold must not make every claim true."""
    response = live_client.get(f"/api/v1/search?q={urllib.parse.quote(mark)}&limit=5")
    assert response.status_code in {200, 400, 422}
    if response.status_code != 200:
        return
    matched = [item["match_type"] for item in response.json()["items"]]
    assert "PREFIX_ENTITY_LABEL" not in matched, (
        f"q=U+{ord(mark):04X} folds to '' and prefix-matches every entity: {matched}"
    )


# -- G-03 ------------------------------------------------------------------------------


@pytest.mark.neo4j
#: CLOSED in the second fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: G-03: DIACRITIC_MARKS declares twelve marks and its docstring claims NFD decomposition means
#: 'this short list covers the whole IAST repertoire'. Measured over the 9,150 distinct entity
#: labels in the graph, four marks that DO occur are absent from it -- U+0325 ring below (372
#: uses), U+094D virama (290), U+0327 cedilla (97), U+0310 candrabindu (51) -- so 635 label
#: strings fold incompletely and the FOLDED_ENTITY_LABEL rung cannot reach them. The fix
#: round's own test asserts only that the Python and Cypher folds AGREE, which they do, because
#: both read the same incomplete table: an agreement test cannot see a coverage gap. Nothing in
#: any search response discloses that the fold is partial.
def test_g03_the_fold_table_covers_every_label_mark(live_client: TestClient) -> None:
    """The fold must reach every mark the corpus uses, or say which ones it does not."""
    from vedagraph.api.services.search_service import DIACRITIC_MARKS, fold_diacritics

    uncovered = sorted(set(LABEL_COMBINING_MARKS) - set(DIACRITIC_MARKS))
    assert not uncovered, (
        "combining marks in graph labels that DIACRITIC_MARKS omits: "
        + ", ".join(f"U+{ord(mark):04X} ({LABEL_COMBINING_MARKS[mark]} uses)" for mark in uncovered)
    )
    folded = fold_diacritics(UNREACHABLE_FOLDED_LABEL)
    response = live_client.get(f"/api/v1/search?q={urllib.parse.quote(folded)}&limit=10")
    assert response.status_code == 200
    assert response.json()["items"], f"the folded form {folded!r} reaches nothing"


# -- G-04 ------------------------------------------------------------------------------


@pytest.mark.neo4j
#: CLOSED in the second fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: G-04: /insights/civilization declares limit and offset and its three sections obey them
#: differently. The INTERPRETIVE_CLAIM section ignores both: it reports returned=6 against a
#: requested limit of 5, and re-serves the same six claim rows at every offset including
#: offset=900. The DATA section does honour them, so at offset=900 it reports returned=0 with
#: data_status PARTIAL and no caveat naming the overrun -- the empty list whose meaning is
#: ambiguous that this API's own description promises never to return. F-15 gave per-collection
#: collections blocks to /insights/rituals, /insights/formula-diffusion and
#: /insights/atharvaveda/concerns; this fourth paginated insight was not among them and carries
#: no pagination metadata at all.
def test_g04_civilization_sections_honour_the_paging_they_declare(
    live_client: TestClient,
) -> None:
    """A declared bound a section ignores is worse than no bound: it is a false one."""
    response = live_client.get("/api/v1/insights/civilization?limit=5&offset=0")
    assert response.status_code == 200
    over_limit = [
        (section["section_kind"], section["returned"])
        for section in response.json()["sections"]
        if int(section["returned"]) > 5
    ]
    assert not over_limit, f"sections returned more rows than limit=5 allowed: {over_limit}"

    deep = live_client.get("/api/v1/insights/civilization?limit=5&offset=900")
    assert deep.status_code == 200
    deep_payload = deep.json()
    unpaged = [
        section["section_kind"]
        for section in deep_payload["sections"]
        if 0 < int(section["total_available"]) <= int(section["returned"])
    ]
    assert not unpaged, f"sections ignored offset=900 and re-served their whole body: {unpaged}"

    emptied = [
        section["section_kind"]
        for section in deep_payload["sections"]
        if int(section["returned"]) == 0
    ]
    if emptied:
        text = _caveat_texts(deep_payload).lower()
        assert "offset" in text or "past the end" in text, (
            f"sections {emptied} were emptied by offset=900 with no paging caveat"
        )


# -- G-05 ------------------------------------------------------------------------------


#: CLOSED in the second fix round; kept as an active regression.
#: The defect it pins, as adversarial QA described it:
#: G-05: test_no_api_cypher_writes_to_the_graph is the assertion that this API cannot mutate
#: the frozen graph, and it scans only Cypher held in TRIPLE-quoted strings. 68 Cypher
#: statements in the API are built from ordinary quoted strings and concatenation, and none is
#: scanned by the write-clause guard or by the property-existence guard: every stage query in
#: search_service, all three readiness queries in app.py, the interpolated relationship
#: fragments in graph_service, and -- most pointedly -- the new _resolve_devata deity gate
#: itself. A SET added to any of them would ship green. The project has three prior instances
#: of certifying an absence against the wrong surface; this is a fourth surface.
def test_g05_the_write_guard_scans_every_cypher_string_in_the_api() -> None:
    """The read-only guarantee must be asserted over all of the API's Cypher, not half.

    Rewritten when the finding was fixed. The original form hardcoded the *old*
    triple-quoted extraction and asserted nothing fell outside it, which could never pass
    while ordinary string literals exist -- it measured the defect rather than the
    invariant. The invariant is: whatever `test_cypher_property_hygiene` uses to find
    Cypher must find *all* of it. So this asks that module's own extractor, which is the
    thing whose coverage actually decides whether the read-only claim is worth anything.
    """
    import ast
    import re
    from pathlib import Path

    from tests.api.test_cypher_property_hygiene import _cypher_blocks

    api_root = Path(__file__).resolve().parents[2] / "src" / "vedagraph" / "api"
    clause = re.compile(r"\b(" + "|".join(CYPHER_CLAUSE_WORDS) + r")\b")

    scanned = {text for _, text in _cypher_blocks()}
    assert len(scanned) > 100, f"the guard's extractor found only {len(scanned)} strings"

    unscanned: list[str] = []
    for path in sorted(api_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Docstrings quote Cypher as prose and are deliberately out of scope for both the
        # guard and this test; excluding them here the same way keeps the two in step.
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
                body = getattr(node, "body", [])
                if body and isinstance(body[0], ast.Expr):
                    value = body[0].value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        docstrings.add(id(value))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings or not clause.search(node.value):
                continue
            if node.value not in scanned:
                unscanned.append(f"{path.name}:{node.lineno}")

    assert not unscanned, (
        f"{len(unscanned)} Cypher strings are invisible to the write-clause guard, "
        f"including {unscanned[:6]}"
    )


# -- Containments that held under the second pass ---------------------------------------


@pytest.mark.neo4j
def test_g06_both_deity_endpoints_agree_for_every_one_of_the_214(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """F-05 closed, verified over the whole population and against the edges.

    The fix round checked four deities. This checks all 214 and adds the third witness:
    the CERTAIN+PROBABLE distinct-passage count read straight off MENTIONS_DEVATA. Two
    endpoints agreeing with each other and both being wrong is exactly the failure this
    project found in the deity profile, so agreement alone is not the assertion.
    """
    truth = {
        str(row["key"]): int(row["count"])
        for row in live_repository.run(
            "MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata) "
            "RETURN dv.entity_key AS key, count(DISTINCT CASE WHEN m.referent_certainty "
            "IN ['DEITY_CERTAIN', 'DEITY_PROBABLE'] THEN p END) AS count"
        )
    }
    disagreements: list[str] = []
    for key, ruled in _all_devata_keys(live_repository):
        profile = live_client.get(_devata_url(key, ruled))
        insight = live_client.get(_devata_url(key, ruled, "/api/v1/insights/devatas"))
        assert profile.status_code == 200, f"{key} -> {profile.status_code}"
        assert insight.status_code == 200, f"{key} -> {insight.status_code}"
        detail_total = profile.json()["mentions_included_total"]
        insight_total = insight.json()["named_total"]
        expected = truth.get(key, 0)
        if detail_total != insight_total or (detail_total or 0) != expected:
            disagreements.append(
                f"{key}: detail={detail_total!r} insight={insight_total!r} edges={expected}"
            )
    assert not disagreements, "deity totals disagree: " + "; ".join(disagreements[:10])


@pytest.mark.neo4j
def test_g07_the_certainty_triple_reconciles_with_the_edges_for_every_deity(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """All three tiers are reported, and all three are the graph's own numbers.

    F-02's contract is that AMBIGUOUS is excluded from totals *and* always reported. A
    reported triple that did not reconcile with the edges would satisfy the letter of that
    and none of its point.
    """
    tiers: dict[str, dict[str, int]] = {}
    for row in live_repository.run(
        "MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata) "
        "RETURN dv.entity_key AS key, m.referent_certainty AS tier, count(DISTINCT p) AS count"
    ):
        tiers.setdefault(str(row["key"]), {})[str(row["tier"])] = int(row["count"])

    mismatches: list[str] = []
    for key, ruled in _all_devata_keys(live_repository):
        block = live_client.get(_devata_url(key, ruled)).json()["certainty"]
        graph = tiers.get(key, {})
        expected = (
            graph.get("DEITY_CERTAIN", 0),
            graph.get("DEITY_PROBABLE", 0),
            graph.get("DEITY_AMBIGUOUS", 0),
        )
        reported = (block["certain_count"], block["probable_count"], block["ambiguous_count"])
        if expected != reported:
            mismatches.append(f"{key}: graph={expected} api={reported}")
    assert not mismatches, "certainty triples disagree: " + "; ".join(mismatches[:10])


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "entity_type",
    [
        "action_predicate",
        "animal",
        "chandas",
        "concept",
        "condition",
        "cosmic_entity",
        "crop",
        "deity_axis",
        "deity_group",
        "epithet",
        "human_concern",
        "metal",
        "natural_phenomenon",
        "object",
        "offering",
        "philosophical_concept",
        "place",
        "plant",
        "quality",
        "rishi",
        "rishi_family",
        "ritual",
        "ritual_role",
        "river",
        "social_rite",
        "state",
        "substance",
        "tribe",
        "weapon",
    ],
)
def test_g08_no_list_row_disagrees_with_its_own_profile(
    live_client: TestClient, entity_type: str
) -> None:
    """F-04/F-09 closed, checked per TYPE rather than per random row.

    Parametrised by type because the sixth instance of this defect lived in the
    ``condition`` list alone -- a sample drawn across all types would have had one chance
    in thirty of catching it, and this project has twice been misled by a sample that
    agreed while one slice was badly wrong. Within a type the rows are walked on an even
    stride over the whole ordering rather than from the head, so a defect in the tail
    cannot hide behind a clean first page.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = live_client.get(f"/api/v1/entities/{entity_type}?limit=200&offset={offset}")
        assert response.status_code == 200, f"{entity_type} -> {response.status_code}"
        page = response.json()["items"]
        rows.extend(page)
        if len(page) < 200:
            break
        offset += 200
    assert rows, f"{entity_type} returned no rows at all"

    bare_zeros = [row["id"] for row in rows if row["passage_count"] == 0]
    assert not bare_zeros, (
        f"{entity_type} has {len(bare_zeros)} bare-zero passage_counts, e.g. "
        f"{bare_zeros[:3]} -- a measured zero must be null with a caveat"
    )

    stride = max(1, len(rows) // 30)
    disagreements: list[str] = []
    for row in rows[::stride]:
        profile = live_client.get(f"/api/v1/entities/{entity_type}/{row['id']}")
        assert profile.status_code == 200, f"{row['id']} -> {profile.status_code}"
        listed, profiled = row["passage_count"], profile.json()["passage_count"]
        if listed != profiled:
            disagreements.append(f"{row['id']}: list={listed!r} profile={profiled!r}")
    assert not disagreements, f"{entity_type} list and profile disagree: " + "; ".join(
        disagreements[:5]
    )


def test_g09_the_query_timeout_actually_stops_a_long_read() -> None:
    """F-06 closed, proved by the clock rather than by reading the call site.

    The first attempt at this probe reported the timeout unenforced and was wrong: the
    planner folds ``MATCH (a:Passage), (b:Passage) RETURN count(*)`` into a product of two
    counts, so it finishes in 63ms and never needs bounding. A predicate the planner cannot
    fold is what makes the test a test. The bound is asserted with slack because Neo4j
    notices an expired transaction on a monitor interval rather than instantly; measured
    overshoot on this graph is about one second at every budget from 1ms to 15s.
    """
    import time

    from vedagraph.api.config import ApiSettings
    from vedagraph.api.errors import GraphUnavailableError
    from vedagraph.api.repositories.neo4j_repository import Neo4jRepository as Repository

    budget = 2.0
    repository = Repository(ApiSettings(neo4j_query_timeout_seconds=budget))
    unfoldable = (
        "MATCH (a:Passage), (b:Passage), (c:Passage) "
        "WHERE a.veda = b.veda AND b.veda = c.veda RETURN count(*) AS c"
    )
    started = time.perf_counter()
    try:
        result = repository.run_one(unfoldable)
    except GraphUnavailableError as error:
        elapsed = time.perf_counter() - started
        assert "too long" in error.detail, f"unexpected 503 detail: {error.detail!r}"
        assert elapsed < budget + 6.0, f"stopped only after {elapsed:.1f}s on a {budget}s budget"
        for secret in ("bolt://", "7687", "MATCH", "Neo4j", "localhost"):
            assert secret not in error.detail, f"the 503 detail leaks {secret!r}"
            assert secret not in (error.hint or ""), f"the 503 hint leaks {secret!r}"
    except Exception as error:  # pragma: no cover - a driver exception escaping IS the bug
        pytest.fail(f"a raw driver exception escaped the repository: {type(error).__name__}")
    else:
        pytest.fail(f"a three-way join over 22,537 passages completed unbounded: {result!r}")
    finally:
        repository.close()


@pytest.mark.neo4j
def test_g10_head_matches_get_on_every_route_including_the_failures(
    live_client: TestClient,
) -> None:
    """F-11 closed. The middleware rewrites the method, so every response shape is in scope.

    The interesting half is the error paths: a middleware that drops the body by building a
    fresh Response could lose the ``Content-Length`` GET would have sent, and RFC 9110 says
    HEAD's headers SHOULD match. Checked on 200, 400, 404 and 422, not the happy path alone.
    """
    paths = [
        "/health",
        "/ready",
        "/openapi.json",
        "/api/v1/works",
        "/api/v1/devatas",
        "/api/v1/devatas/VG:DEVATA:INDRAH",
        "/api/v1/devatas/VG:DEVATA:INDRAH/network",
        "/api/v1/devatas/VG:DEVATA:BHAVAVRTTAM",
        "/api/v1/entities/nosuchtype",
        "/api/v1/devatas?limit=99999",
        "/api/v1/search",
        "/api/v1/search?q=agni",
        "/api/v1/stats",
        "/api/v1/graph/neighborhood/VG:DEVATA:INDRAH",
        "/api/v1/passages/VG:RV:SAK:M01:S001:V001",
        "/api/v1/nope/nope",
    ]
    problems: list[str] = []
    for path in paths:
        got = live_client.get(path)
        headed = live_client.head(path)
        if headed.status_code != got.status_code:
            problems.append(f"{path}: GET {got.status_code} but HEAD {headed.status_code}")
        if headed.headers.get("content-length") != got.headers.get("content-length"):
            problems.append(
                f"{path}: content-length {got.headers.get('content-length')!r} on GET, "
                f"{headed.headers.get('content-length')!r} on HEAD"
            )
        if headed.content:
            problems.append(f"{path}: HEAD returned {len(headed.content)} body bytes")
    assert not problems, "; ".join(problems)


def test_g11_head_on_an_unhandled_error_drops_the_body_and_leaks_nothing() -> None:
    """The 500 path runs in a different middleware layer from every other response.

    An ``Exception`` handler can land OUTSIDE a ``BaseHTTPMiddleware``, which would let a
    500 bypass the HEAD middleware and answer a HEAD request with a body. It does not, and
    the handler's promise -- logged in full, described to the client in none -- holds for a
    repository whose exception text carries the connection string.
    """
    from tests.api.conftest import build_client

    secret = "bolt://localhost:7687 password=vedagraph_dev"

    class ExplodingRepository(FakeRepository):
        def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]:
            raise ValueError(f"internal detail: {secret}")

    app, client = build_client(ExplodingRepository())
    with client:
        app.state.repository = ExplodingRepository()
        got = client.get("/api/v1/devatas")
        headed = client.head("/api/v1/devatas")

    assert got.status_code == 500
    assert headed.status_code == 500
    assert headed.content == b"", f"HEAD on a 500 returned a body: {headed.content[:80]!r}"
    assert headed.headers.get("content-length") == got.headers.get("content-length")
    assert got.json()["error"] == "INTERNAL_ERROR"
    for leak in ("bolt://", "7687", "vedagraph_dev", "ValueError", "Traceback"):
        assert leak not in got.text, f"the 500 body leaks {leak!r}"


@pytest.mark.neo4j
@pytest.mark.parametrize("query", ["a", "agni", "yajna", "sarasvati", "somam", "bharadvaja"])
def test_g12_search_scores_never_rise_as_you_read_down_a_page(
    live_client: TestClient, query: str
) -> None:
    """The new FOLDED_ENTITY_LABEL rung sits inside the ladder rather than beside it.

    A rung inserted with a score out of order, or a merge that sorted by something other
    than rung index, would break monotonicity without breaking any single-query assertion.
    Checked on the deep pages too, because that is where the per-stage fetch shrink changes
    which candidates the merge ever sees.
    """
    for limit, offset in ((200, 0), (100, 100), (25, 175)):
        response = live_client.get(
            f"/api/v1/search?q={urllib.parse.quote(query)}&limit={limit}&offset={offset}"
        )
        assert response.status_code == 200, f"{query} {limit}/{offset} -> {response.status_code}"
        scores = [item["score"] for item in response.json()["items"]]
        rising = [
            (index, scores[index], scores[index + 1])
            for index in range(len(scores) - 1)
            if scores[index] < scores[index + 1]
        ]
        assert not rising, f"q={query!r} limit={limit} offset={offset}: score rises at {rising}"


@pytest.mark.neo4j
def test_g13_the_repertoire_prefilter_does_not_gate_the_entity_stage(
    live_client: TestClient,
) -> None:
    """Asserted through the API, not by reading ``_STAGE_ENTITIES.reads_sanskrit``.

    ``yajna`` contains the pair ``jn``, which no Sanskrit text in this corpus carries, so
    the repertoire prefilter proves the Sanskrit *text* scans cannot match it. Gating the
    entity stage with the same proof would be unsound, because the entity stage folds
    diacritics and ``yajna`` folds onto the label. A flag can be set back; the observable
    behaviour is what the contract is.
    """
    from vedagraph.api.services.search_service import sanskrit_cannot_contain

    assert sanskrit_cannot_contain("yajna") == "jn", (
        "the premise moved: 'yajna' is no longer rejected by the repertoire prefilter, so "
        "this test no longer proves the entity stage is ungated"
    )
    response = live_client.get("/api/v1/search?q=yajna&limit=10")
    assert response.status_code == 200
    folded = [
        item["display_label"]
        for item in response.json()["items"]
        if item["match_type"] == "FOLDED_ENTITY_LABEL"
    ]
    assert folded, (
        "q=yajna returned no FOLDED_ENTITY_LABEL row: the repertoire prefilter has been "
        "applied to the entity stage and the fold can no longer match"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize("query", ["bharadvaja", "kanva", "brhaspati", "angirasa"])
def test_g14_a_fold_collision_returns_every_colliding_label(
    live_client: TestClient, live_repository: Neo4jRepository, query: str
) -> None:
    """Folding merges distinct Sanskrit names; the response must not pick one silently.

    ``bharadvaja`` and the same name with a long first vowel are a seer and his patronymic,
    and ``kanva`` likewise names a seer and a school. Folding makes them one key. That is
    acceptable only if every colliding node is returned and the ordering is total -- if the
    rung emitted one row, the client would read the others as absent.
    """
    from vedagraph.api.services.search_service import DIACRITIC_MARKS

    rows = live_repository.run(
        "CALL () { MATCH (n:Devata) RETURN n UNION MATCH (n:DomainEntity) RETURN n "
        "UNION MATCH (n:Rishi) RETURN n UNION MATCH (n:RishiFamily) RETURN n "
        "UNION MATCH (n:Epithet) RETURN n UNION MATCH (n:Chandas) RETURN n } "
        "WITH n, coalesce(n.display_label, n.preferred_label, n.label_iast) AS label "
        "WHERE label IS NOT NULL AND reduce(s = normalize(toLower(label), NFD), "
        "m IN $fold_marks | replace(s, m, '')) = $folded "
        "RETURN count(DISTINCT label) AS labels",
        fold_marks=list(DIACRITIC_MARKS),
        folded=query,
    )
    colliding = int(rows[0]["labels"])
    assert colliding > 1, f"{query!r} no longer collides; pick another probe"

    response = live_client.get(f"/api/v1/search?q={query}&limit=50")
    assert response.status_code == 200
    items = response.json()["items"]
    folded_rows = [item for item in items if item["match_type"] == "FOLDED_ENTITY_LABEL"]
    assert len(folded_rows) >= 2, (
        f"{colliding} labels fold onto {query!r} but the folded rung returned "
        f"{len(folded_rows)} row(s): the others read as absent"
    )
    ids = [item["stable_id"] for item in items]
    assert len(ids) == len(set(ids)), f"the merge returned a duplicate stable_id for {query!r}"
