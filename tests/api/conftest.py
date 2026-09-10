"""Fixtures for the product API tests.

Two kinds of test live here and they answer different questions.

*Route tests* run against :class:`FakeRepository` and never open a socket. They are the
right tool for the contract: that a bad ``limit`` is a 422, that an unknown entity type is
a 400 and not an empty list, that a Neo4j outage is a 503 whose body names no hostname,
that an empty page cannot claim ``SUPPORTED``. None of those need real Vedic data, and
running them against a live graph would make them slow and dependent on its contents.

*Live tests* are marked ``neo4j`` and take :func:`live_repository`. They are the only way
to answer the questions that actually matter here -- whether Vasukra can reach a deity
list, whether Indra's mention counts sum the way the profile claims -- because those are
statements about 108,779 real nodes and a mock cannot falsify them. This project has twice
certified an absence against the wrong surface; a fixture that quietly returned ``[]``
would be a third opportunity.

Live fixtures skip rather than fail when the graph is down, so the suite stays green on a
machine with no Neo4j, and the skip reason says which check failed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vedagraph.api.app import create_app
from vedagraph.api.config import ApiSettings, get_api_settings
from vedagraph.api.dependencies import get_repository
from vedagraph.api.errors import GraphUnavailableError
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository


class FakeRepository:
    """A repository that answers from a script and remembers what it was asked.

    ``script`` maps a substring of the Cypher to the rows that query should return, so a
    test declares intent ("the deity lookup finds nothing") without reproducing a query it
    does not own. An unmatched query returns ``[]``.

    ``calls`` is kept so the security tests can assert what actually reached the driver:
    that every parameter travelled bound, and that no client string was ever spliced into
    the query text.
    """

    def __init__(
        self,
        script: dict[str, list[dict[str, Any]]] | None = None,
        *,
        unavailable: bool = False,
    ) -> None:
        self.script = script or {}
        self.unavailable = unavailable
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _answer(self, cypher: str) -> list[dict[str, Any]]:
        if self.unavailable:
            raise GraphUnavailableError("The knowledge graph is unavailable.")
        for needle, rows in self.script.items():
            if needle in cypher:
                return rows
        return []

    def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]:
        self.calls.append((cypher, parameters))
        return self._answer(cypher)

    def run_one(self, cypher: str, /, **parameters: Any) -> dict[str, Any] | None:
        rows = self.run(cypher, **parameters)
        return rows[0] if rows else None

    def run_named(self, query_name: str, /, **overrides: Any) -> list[dict[str, Any]]:
        from vedagraph.domain.queries import QUERIES_BY_NAME

        query = QUERIES_BY_NAME[query_name]
        return self.run(query.cypher, **{**query.parameters, **overrides})

    def verify_connectivity(self) -> None:
        if self.unavailable:
            raise GraphUnavailableError("The knowledge graph is unavailable.")

    def close(self) -> None:  # pragma: no cover - lifespan symmetry only
        return None

    @property
    def query_text(self) -> str:
        """Every query this repository was asked, joined. For injection assertions."""
        return "\n".join(cypher for cypher, _ in self.calls)

    @property
    def all_parameters(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for _, parameters in self.calls:
            merged.update(parameters)
        return merged


def build_client(repository: FakeRepository) -> tuple[FastAPI, TestClient]:
    """An app whose graph access is ``repository``, for both routes and ``/ready``.

    The dependency override covers the routes; ``app.state`` covers ``/health`` and
    ``/ready``, which read the repository off the app directly because they must work
    before any dependency has resolved. Both are pointed at the same fake so a test cannot
    accidentally exercise one path against the real driver.
    """
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app, raise_server_exceptions=False)
    app.state.repository = repository
    return app, client


@pytest.fixture
def fake_repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def client(fake_repository: FakeRepository) -> Iterator[TestClient]:
    app, test_client = build_client(fake_repository)
    with test_client:
        # Re-asserted inside the context: lifespan runs on __enter__ and installs the real
        # repository on app.state, which would otherwise dial a live database from a test
        # that believes it is offline.
        app.state.repository = fake_repository
        yield test_client


@pytest.fixture
def down_client() -> Iterator[TestClient]:
    """A client whose graph is unreachable. Every knowledge route must answer 503."""
    app, test_client = build_client(FakeRepository(unavailable=True))
    with test_client:
        app.state.repository = FakeRepository(unavailable=True)
        yield test_client


# ---------------------------------------------------------------------------
# Live graph
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def live_settings() -> ApiSettings:
    return get_api_settings()


@pytest.fixture(scope="session")
def live_repository(live_settings: ApiSettings) -> Iterator[Neo4jRepository]:
    """The real graph, or a skip naming what was missing.

    Checks connectivity *and* that the four works are present. A reachable but empty
    database would otherwise produce a long tail of tests failing on missing data, which
    reads as "the API is broken" rather than "load the graph first".
    """
    repository = Neo4jRepository(live_settings)
    try:
        repository.verify_connectivity()
    except Exception:
        repository.close()
        pytest.skip(f"no Neo4j at {live_settings.neo4j_uri}")
    try:
        row = repository.run_one("MATCH (w:Work) RETURN count(w) AS c")
        if row is None or int(row["c"]) < 4:
            pytest.skip("Neo4j is reachable but the frozen graph is not loaded")
    except Exception:
        repository.close()
        pytest.skip("Neo4j is reachable but unreadable")
    try:
        yield repository
    finally:
        repository.close()


@pytest.fixture(scope="session")
def live_client(live_repository: Neo4jRepository) -> Iterator[TestClient]:
    """A TestClient over the real graph, for end-to-end route assertions."""
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: live_repository
    with TestClient(app) as test_client:
        app.state.repository = live_repository
        yield test_client
