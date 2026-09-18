"""App assembly, liveness, readiness, error translation and OpenAPI integrity.

These are the tests that hold the *boundary* rather than any one route's knowledge. They
answer four questions no domain test asks:

*Does the process survive its dependency?* A graph that is down at boot must still produce
an app that answers ``/health``, because an orchestrator restarting a healthy API over a
sick database makes an outage worse.

*Does readiness distinguish its failure modes?* A reachable but empty graph, a graph built
under a different ontology, and a graph missing the uniqueness constraint passage lookup
depends on are three different faults with the same symptom -- confidently wrong answers --
so each is named separately.

*Does anything leak?* The password, the bolt URI's credentials, Cypher text, a driver
exception repr and a stack trace are all things that reach a client only through a mistake,
and the mistake is easy: FastAPI's debug 500 page renders a traceback naming query text and
sometimes the connection string.

*Does the OpenAPI document actually build?* ``/docs`` is a deliverable here. A response
model with an unresolvable annotation does not fail at import or at request time -- it fails
when the schema is generated, which without this test is the first time a frontend
developer opens the page.
"""

from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, build_client
from vedagraph.api.app import API_V1, create_app
from vedagraph.api.config import (
    EXPECTED_DOMAIN_MODEL_VERSION,
    EXPECTED_WORK_IDS,
    ApiSettings,
)


def test_health_does_not_touch_the_graph(down_client: TestClient) -> None:
    """Liveness must not depend on Neo4j, or a database outage looks like a crashed app."""
    response = down_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_503_and_names_the_failing_check(down_client: TestClient) -> None:
    response = down_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    failed = [check["name"] for check in body["checks"] if not check["ok"]]
    assert "neo4j_reachable" in failed


def test_ready_never_returns_credentials(down_client: TestClient) -> None:
    """The URI and database name are useful to an operator; the password is not, ever."""
    body = down_client.get("/ready").json()
    assert set(body["graph"]) == {"uri", "database"}
    serialized = json.dumps(body)
    assert "password" not in serialized.lower()


def test_ready_checks_are_independent() -> None:
    """A reachable graph with no works must fail ``works_present`` and nothing else.

    Written as a distinct case because the tempting implementation -- one query that joins
    every precondition -- reports a single boolean, and a single boolean cannot tell an
    operator whether to load the corpus or to rebuild it under the right ontology.
    """
    repository = FakeRepository(
        script={
            "collect(w.work_id)": [{"ids": []}],
            "domain_model_version": [{"version": EXPECTED_DOMAIN_MODEL_VERSION}],
            "SHOW CONSTRAINTS": [
                {"names": ["passage_canonical_key_unique", "devata_entity_key_unique"]}
            ],
        }
    )
    app, test_client = build_client(repository)
    with test_client:
        app.state.repository = repository
        body = test_client.get("/ready").json()
    results = {check["name"]: check["ok"] for check in body["checks"]}
    assert results["neo4j_reachable"] is True
    assert results["works_present"] is False
    assert results["ontology_version"] is True
    assert results["constraints_present"] is True


def test_ready_rejects_a_graph_built_under_another_ontology() -> None:
    repository = FakeRepository(
        script={
            "collect(w.work_id)": [{"ids": list(EXPECTED_WORK_IDS)}],
            "domain_model_version": [{"version": "vedagraph-knowledge-model-v1"}],
            "SHOW CONSTRAINTS": [
                {"names": ["passage_canonical_key_unique", "devata_entity_key_unique"]}
            ],
        }
    )
    app, test_client = build_client(repository)
    with test_client:
        app.state.repository = repository
        response = test_client.get("/ready")
    assert response.status_code == 503
    detail = next(
        check["detail"]
        for check in response.json()["checks"]
        if check["name"] == "ontology_version"
    )
    assert EXPECTED_DOMAIN_MODEL_VERSION in detail


def test_unknown_path_is_a_404_not_a_stack_trace(client: TestClient) -> None:
    response = client.get(f"{API_V1}/no-such-collection")
    assert response.status_code == 404


def test_openapi_document_builds_and_is_tagged() -> None:
    """Every public route must carry a tag, a summary and a response model.

    An untagged route lands in a default bucket in ``/docs`` and is effectively
    undiscoverable, which for a product whose whole thesis is "the caveat travels with the
    payload" means the caveat is documented where nobody looks.
    """
    app = create_app()
    schema = app.openapi()
    assert schema["info"]["title"] == "VedaGraph API"

    untagged: list[str] = []
    unsummarized: list[str] = []
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not operation.get("tags"):
                untagged.append(f"{method.upper()} {path}")
            if not operation.get("summary"):
                unsummarized.append(f"{method.upper()} {path}")
    assert not untagged, f"untagged operations: {untagged}"
    assert not unsummarized, f"operations with no summary: {unsummarized}"


def test_every_product_route_is_under_the_version_prefix() -> None:
    """Only health, readiness and the docs may sit outside ``/api/v1``.

    Spec §7: an unversioned product route is a promise the frontend will hold us to after
    the shape changes.
    """
    schema = create_app().openapi()
    allowed_unversioned = {"/health", "/ready", "/openapi.json", "/docs", "/redoc"}
    stray = [
        path
        for path in schema["paths"]
        if not path.startswith(API_V1) and path not in allowed_unversioned
    ]
    assert not stray, f"routes outside {API_V1}: {stray}"


@pytest.mark.neo4j
def test_live_readiness_passes_against_the_frozen_graph(live_client: TestClient) -> None:
    response = live_client.get("/ready")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ready"] is True
    assert all(check["ok"] for check in body["checks"])


#: The graph this API is written against. Raised from Product-V1's 108,779 / 265,295 by the
#: Wave 3 canonical import, and re-derived rather than bumped: the figures are the ones
#: ``data/staging/integration/wave3_readback.json`` read back out of Neo4j and matched
#: against the dry-run's promise, not numbers edited until a test went green.
#:
#: Raised again after the round-three coverage rebuild, which DETACH DELETEs :DerivedMetric
#: and recomputes it: the attribution census gave it 13 more metrics to compute, so the node
#: count moved 116,825 -> 116,838 while the relationship count and the four corpora did not.
#:
#: LOWERED once, by M9: 33 HAS_CHANDAS assertions were withdrawn because their object was
#: an unsegmented fragment of Whitney's printed bracket carrying a deity, a metre and a
#: per-verse exception in one string, not a metre name. 281,290 -> 281,257. The node count
#: did not move, because the :Chandas entities stay in the graph holding the literal.
#:
#: Raised again by the translation bulk integration, which created 1,132 :Translation nodes
#: and 1,132 HAS_TRANSLATION edges: 116,838 -> 117,970 and 281,257 -> 282,389. The pair moves
#: by the same 1,132 because every node this round created carries exactly one edge, and the
#: migration refused to commit unless that held -- a node count that grew by more than the
#: edge count would mean something other than a translation was created. The figures are the
#: ones data/staging/translation/integration/translation_bulk_readback.json read back out of
#: Neo4j and matched against the plan's promise.
#:
#: Raising this pair is a deliberate act, and the docstring below says what it costs.
#:
#: Raised in R2 from 117,970 / 282,389, which the graph passed several waves ago: the census
#: had reached 164,201 / 508,042 and this assertion had been failing continuously, which is
#: the failure mode a census guard is supposed to prevent and the one it causes when it is
#: left stale -- a test that always fails is a test nobody reads. R2's own graph writes moved
#: neither figure: the display_type normalisation and the ritual_context method landing are
#: property writes on existing nodes, promised and read back at 0 nodes and 0 relationships
#: created or deleted. The pair below is the closed-set guard and it has not moved.
#: R4 moved the census by one receipted migration:
#: data/staging/release_blocker_r4/migration_receipt.json. +396 nodes (399 DerivedMetric
#: created for the widened deity-profile population, 3 deleted with the danastuti label's
#: deity metrics) and +1,444 relationships (1,035 MENTIONS_EPITHET, 399 MEASURES, 8
#: ASCRIBES_TO_DEVATA, 4 COMPOSED_OF, 1 ATTESTED_IN, less the 3 MEASURES that went with
#: the deleted metrics). The delta reconciles exactly against the 164,201/508,042
#: baseline, and tests/api/test_adversarial.py imports both constants from here so the
#: pin has one home.
FROZEN_NODES = 164_597
FROZEN_RELATIONSHIPS = 509_486

#: The figures that must NEVER move, whatever an import does. The whole-graph census grows
#: with every wave; the four corpora are closed sets, and a drift here is corruption rather
#: than growth. Asserted alongside the census so that raising one cannot quietly excuse the
#: other.
CORPUS_MANTRAS = {"RV": 10_552, "SV": 1_844, "YV": 1_975, "AV": 5_839}


@pytest.mark.neo4j
def test_live_graph_matches_the_frozen_census(live_repository: object) -> None:
    """The graph this API was written against, asserted by size rather than assumed.

    If a later session reloads the corpus and this drifts, every measured caveat in the API
    is describing a graph that no longer exists, and that is worth failing a test over. It
    did drift, exactly as intended: Wave 3 added 8,046 nodes and 15,995 relationships, this
    test failed, and the failure is what sent the ritual endpoints back to be re-derived
    against the layer the import had actually added.

    So raising the pair is only legitimate together with that work. A bumped constant on its
    own would have left `/api/v1/rituals` reporting 92 rites as having no procedure while
    3,121 sutra-attested steps sat in the graph.
    """
    from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

    assert isinstance(live_repository, Neo4jRepository)
    nodes = live_repository.run_one("MATCH (n) RETURN count(n) AS c")
    rels = live_repository.run_one("MATCH ()-[r]->() RETURN count(r) AS c")
    assert nodes is not None and rels is not None
    assert int(nodes["c"]) == FROZEN_NODES
    assert int(rels["c"]) == FROZEN_RELATIONSHIPS

    corpus = {
        str(row["veda"]): int(row["n"])
        for row in live_repository.run(
            "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
        )
    }
    assert corpus == CORPUS_MANTRAS, (
        "the four corpora are closed sets. The census above may grow with an import; these "
        "may not, and a drift here is corruption rather than growth."
    )


# ---------------------------------------------------------------------------
# Regressions from the adversarial pass (F-06, F-11, F-12)
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_query_timeout_is_enforced(live_settings: ApiSettings) -> None:
    """A configured query budget must actually stop a query. It did not.

    ``Session.run(query, parameters, **kwargs)`` documents ``kwargs`` as *additional query
    parameters*, so ``session.run(cypher, params, timeout=1.0)`` bound a Cypher parameter
    named ``$timeout`` and set no time bound at all. Every read this API issued was
    unbounded, the documented 15s budget was fiction, and the ``TransientError`` to 503 path
    was dead code. The timeout now travels inside a :class:`neo4j.Query`.

    Measured while fixing it: an 8.6s aggregation ran to completion under the broken
    spelling and is stopped after 1.5s under the fixed one.
    """
    from vedagraph.api.config import ApiSettings as Settings
    from vedagraph.api.errors import GraphUnavailableError
    from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

    bounded = Settings(
        neo4j_uri=live_settings.neo4j_uri,
        neo4j_user=live_settings.neo4j_user,
        neo4j_password=live_settings.neo4j_password,
        neo4j_database=live_settings.neo4j_database,
        neo4j_query_timeout_seconds=1.0,
    )
    repository = Neo4jRepository(bounded)
    try:
        started = time.perf_counter()
        with pytest.raises(GraphUnavailableError):
            # Read-only and deliberately expensive: no node is touched, so this cannot
            # write and cannot depend on corpus contents.
            repository.run("UNWIND range(1, 300000000) AS x RETURN count(x) AS c")
        elapsed = time.perf_counter() - started
        assert elapsed < 6.0, f"the 1s budget did not stop the query for {elapsed:.1f}s"
    finally:
        repository.close()


@pytest.mark.neo4j
def test_no_stray_timeout_parameter_is_bound_into_queries(
    live_repository: object,
) -> None:
    """The broken spelling also injected ``$timeout`` into every statement.

    Harmless only by luck: ``kwargs`` take precedence over ``parameters``, so any query
    that ever needed a real parameter called ``timeout`` would have had it silently
    overwritten by the driver option.
    """
    from vedagraph.api.errors import GraphUnavailableError
    from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

    assert isinstance(live_repository, Neo4jRepository)
    with pytest.raises(GraphUnavailableError):
        live_repository.run("RETURN $timeout AS t")


@pytest.mark.parametrize("path", ["/health", "/ready"])
def test_head_is_answered_wherever_get_is(down_client: TestClient, path: str) -> None:
    """RFC 9110: a server answering GET on a resource must answer HEAD on it.

    All 36 GET operations returned 405 to HEAD, so a monitor probing ``HEAD /health``
    would have read a healthy process as broken.
    """
    response = down_client.head(path)
    assert response.status_code in {200, 503}
    assert response.content == b""


def test_head_reports_the_length_get_would_have_sent(client: TestClient) -> None:
    head = client.head("/health")
    get = client.get("/health")
    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-length"] == get.headers["content-length"]


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("GET", "/api/v1/no-such-route", 404),
        ("GET", "/api/v1/passages/..%2F..%2Fetc%2Fpasswd", 404),
        ("POST", "/api/v1/works", 405),
        ("DELETE", "/health", 405),
    ],
)
def test_router_level_failures_use_the_documented_error_shape(
    client: TestClient, method: str, path: str, expected: int
) -> None:
    """One error shape, including for the failures a client hits while integrating.

    Starlette raises its own HTTPException before any route runs and its default handler
    renders ``{"detail": "Not Found"}``, so this API served two different error bodies. A
    client parsing ``error`` got a KeyError on exactly the 404s and 405s it meets first.
    """
    response = client.request(method, path)
    assert response.status_code == expected
    body = response.json()
    assert set(body) == {"error", "detail", "hint"}, body
    assert body["error"] in {"NOT_FOUND", "METHOD_NOT_ALLOWED"}
    assert "Traceback" not in response.text
    assert "bolt://" not in response.text
