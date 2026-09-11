"""The FastAPI application: assembly, lifespan, health and readiness.

Route modules are imported and mounted here and nowhere else, so the set of things this
API exposes is readable in one place.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from vedagraph.api.config import (
    EXPECTED_DOMAIN_MODEL_VERSION,
    EXPECTED_WORK_IDS,
    get_api_settings,
)
from vedagraph.api.errors import install_error_handlers
from vedagraph.api.models.common import ApiModel
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

API_V1: Final = "/api/v1"

DESCRIPTION: Final = """
The VedaGraph product API: Vedic knowledge with its evidence and its limits attached.

**What this API refuses to do.** It never returns an empty list whose meaning is
ambiguous. Where a layer of the graph was not built, or where evidence exists but cannot
support a claim, the response says so in `data_status` -- `NOT_BUILT` or
`INSUFFICIENT_EVIDENCE` -- rather than returning `0` or `[]` and letting a reader infer
that the Vedas are silent. Caveats travel *with* the payload, not in this documentation,
because the client who calls the obvious endpoint never reads the documentation.

**Deity counts default to CERTAIN plus PROBABLE.** Vedic Sanskrit has one word for the god
Agni and for fire. Every mention is graded, and `AMBIGUOUS` mentions are excluded from
user-facing totals unless `include_ambiguous=true`. All three counts are always reported.

**Scope is not the Vedas.** Four Samhitas, one recension each: Sakala Rigveda, Kauthuma
Samaveda *arcika only* (the gana corpus is not included), Shukla Yajurveda in the
Madhyandina recension, and a working Saunaka Atharvaveda. No Brahmana, Aranyaka or
Upanisad. `GET /api/v1/works` states each work's exclusions explicitly.
"""

TAGS_METADATA: Final[list[dict[str, Any]]] = [
    {"name": "Health", "description": "Liveness and readiness."},
    {"name": "Works", "description": "The four Samhitas, their recensions and their exclusions."},
    {"name": "Passages", "description": "Canonical passage lookup, navigation and reading."},
    {"name": "Search", "description": "Unified search across text, entities and translations."},
    {"name": "Devatas", "description": "Deities, with the ambiguity contract applied."},
    {"name": "Entities", "description": "Rishis, concepts, rituals, conditions and the rest."},
    {"name": "Rituals", "description": "The eight modelled rites. Not a taxonomy of Vedic ritual."},
    {
        "name": "Formulas",
        "description": "Fixed verbal formulae and the families they group into. A family's "
        "membership is one set of 2,037 edges stored in both directions; traversing both "
        "double-counts, so these endpoints traverse one and say which.",
    },
    {"name": "Graph", "description": "Neighbourhoods, relationship explanations and paths."},
    {"name": "Insights", "description": "Deterministic, evidence-aware aggregate views."},
    {"name": "Stats", "description": "Product-level corpus statistics."},
    {
        "name": "Ask",
        "description": "Evidence-grounded question answering. Retrieval runs first and "
        "the model sees only what it found, so every factual claim carries a citation "
        "into the graph and an unanswerable question returns INSUFFICIENT_EVIDENCE "
        "rather than a confident denial. The synthesis backend is a configuration "
        "choice; no credential is ever returned.",
    },
]


class HealthResponse(ApiModel):
    status: str
    service: str
    api_version: str


class ReadinessCheck(ApiModel):
    name: str
    ok: bool
    detail: str


class ReadinessResponse(ApiModel):
    ready: bool
    checks: list[ReadinessCheck]
    graph: dict[str, str] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_api_settings()
    repository = Neo4jRepository(settings)
    app.state.repository = repository
    app.state.settings = settings
    # Deliberately not connecting here. A database that is down at boot must produce a
    # process that starts and answers /health, so an orchestrator can distinguish "the app
    # is broken" from "the app is fine and its dependency is not".
    try:
        yield
    finally:
        repository.close()


def _readiness_checks(app: FastAPI) -> list[ReadinessCheck]:
    """Four questions, none of which a bare connectivity ping would answer.

    A graph can be reachable, empty, built under a different ontology, or missing the
    uniqueness constraint that passage lookup depends on. Each is a distinct way for this
    API to serve confident nonsense, so each is checked separately and named in the result.
    """
    repository: Neo4jRepository = app.state.repository
    checks: list[ReadinessCheck] = []

    try:
        repository.verify_connectivity()
        checks.append(ReadinessCheck(name="neo4j_reachable", ok=True, detail="Connected."))
    except Exception:
        checks.append(
            ReadinessCheck(name="neo4j_reachable", ok=False, detail="Cannot reach the graph.")
        )
        return checks

    try:
        rows = repository.run(
            "MATCH (w:Work) RETURN collect(w.work_id) AS ids",
        )
        found = set(rows[0]["ids"]) if rows else set()
        missing = [w for w in EXPECTED_WORK_IDS if w not in found]
        checks.append(
            ReadinessCheck(
                name="works_present",
                ok=not missing,
                detail=(
                    f"All {len(EXPECTED_WORK_IDS)} works present."
                    if not missing
                    else f"Missing {len(missing)} of {len(EXPECTED_WORK_IDS)} works."
                ),
            )
        )
    except Exception:
        checks.append(
            ReadinessCheck(name="works_present", ok=False, detail="Could not read works.")
        )

    try:
        row = repository.run_one(
            "MATCH (n:DomainEntity) WHERE n.domain_model_version IS NOT NULL "
            "RETURN n.domain_model_version AS version LIMIT 1"
        )
        version = row["version"] if row else None
        ok = version == EXPECTED_DOMAIN_MODEL_VERSION
        checks.append(
            ReadinessCheck(
                name="ontology_version",
                ok=ok,
                detail=(
                    f"Graph carries {EXPECTED_DOMAIN_MODEL_VERSION}."
                    if ok
                    else f"Expected {EXPECTED_DOMAIN_MODEL_VERSION}, found {version!r}."
                ),
            )
        )
    except Exception:
        checks.append(
            ReadinessCheck(name="ontology_version", ok=False, detail="Could not read the version.")
        )

    try:
        rows = repository.run("SHOW CONSTRAINTS YIELD name RETURN collect(name) AS names")
        names = set(rows[0]["names"]) if rows else set()
        required = {"passage_canonical_key_unique", "devata_entity_key_unique"}
        missing_constraints = required - names
        checks.append(
            ReadinessCheck(
                name="constraints_present",
                ok=not missing_constraints,
                detail=(
                    "Required uniqueness constraints present."
                    if not missing_constraints
                    else f"Missing: {', '.join(sorted(missing_constraints))}."
                ),
            )
        )
    except Exception:
        checks.append(
            ReadinessCheck(
                name="constraints_present", ok=False, detail="Could not read constraints."
            )
        )

    return checks


class _HeadMethodMiddleware(BaseHTTPMiddleware):
    """Answer ``HEAD`` wherever ``GET`` is answered, with the body dropped.

    Starlette routes only the methods a decorator declares, so ``HEAD`` on 36 ``GET``
    endpoints was 405 -- which RFC 9110 forbids: a server supporting GET on a resource must
    support HEAD on it. Clients rely on it for cheap liveness and cache checks, and a
    monitor probing ``HEAD /health`` would have read this API as down.

    Done as one middleware rather than by adding ``methods=["GET", "HEAD"]`` to every route
    because that is 36 edits that a 37th route can forget, and this is the kind of contract
    that must hold for endpoints nobody remembered to think about.

    ``Content-Length`` is left as the handler computed it: RFC 9110 says HEAD's headers
    SHOULD match what GET would have returned, so the length of the body that *would* have
    been sent is the correct value even though no bytes follow.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "HEAD":
            return await call_next(request)
        request.scope["method"] = "GET"
        response = await call_next(request)
        return Response(
            status_code=response.status_code,
            headers=response.headers,
            media_type=response.media_type,
        )


def create_app() -> FastAPI:
    settings = get_api_settings()
    app = FastAPI(
        title="VedaGraph API",
        version="1.0.0",
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        debug=settings.api_debug,
    )
    install_error_handlers(app)
    app.add_middleware(_HeadMethodMiddleware)

    health = APIRouter(tags=["Health"])

    @health.get(
        "/health",
        summary="Liveness",
        description="Whether this process is running. Does not touch the graph.",
        response_model=HealthResponse,
    )
    def health_endpoint() -> HealthResponse:
        return HealthResponse(status="ok", service="vedagraph-api", api_version="1.0.0")

    @health.get(
        "/ready",
        summary="Readiness",
        description=(
            "Whether this process can serve knowledge: the graph is reachable, the four "
            "works are present, the ontology version matches the one this API was written "
            "against, and the uniqueness constraints lookup depends on exist. Returns 503 "
            "when any check fails. Never returns credentials."
        ),
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse, "description": "Not ready to serve."}},
    )
    def ready_endpoint() -> Any:
        checks = _readiness_checks(app)
        ready = all(check.ok for check in checks)
        payload = ReadinessResponse(
            ready=ready,
            checks=checks,
            # safe_summary() carries the URI and database name and never the credentials.
            graph={k: str(v) for k, v in settings.safe_summary().items()},
        )
        if not ready:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=payload.model_dump(),
            )
        return payload

    app.include_router(health)
    _mount_v1_routers(app)
    return app


def _mount_v1_routers(app: FastAPI) -> None:
    """Mount the product routers under /api/v1.

    Imported inside the function so that a route module with an import-time error breaks
    app construction with a clear traceback rather than poisoning ``import
    vedagraph.api.app`` for every consumer, including the test collector.
    """
    from vedagraph.api.routes import (
        ask,
        devatas,
        entities,
        formulas,
        graph,
        insights,
        passages,
        rituals,
        search,
        stats,
        works,
    )

    for module in (
        works,
        passages,
        search,
        devatas,
        entities,
        rituals,
        formulas,
        graph,
        insights,
        stats,
        ask,
    ):
        app.include_router(module.router, prefix=API_V1)


app = create_app()
