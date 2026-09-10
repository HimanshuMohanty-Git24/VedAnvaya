"""FastAPI dependency wiring.

The repository is created once per process and held on ``app.state``, not built per
request: a Neo4j driver owns a connection pool, and constructing one per call would spend
more time on TCP than on Cypher. Services are cheap wrappers and are constructed per
request around that shared repository.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from vedagraph.api.config import ApiSettings, get_api_settings
from vedagraph.api.errors import GraphUnavailableError
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository


def get_repository(request: Request) -> Neo4jRepository:
    repository = getattr(request.app.state, "repository", None)
    if repository is None:  # pragma: no cover - only if lifespan did not run
        raise GraphUnavailableError("The knowledge graph is unavailable.")
    assert isinstance(repository, Neo4jRepository)
    return repository


def get_settings_dep() -> ApiSettings:
    return get_api_settings()


RepositoryDep = Annotated[Neo4jRepository, Depends(get_repository)]
SettingsDep = Annotated[ApiSettings, Depends(get_settings_dep)]
