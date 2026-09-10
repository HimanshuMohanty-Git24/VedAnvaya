"""Product-level errors and the handlers that turn them into HTTP.

One rule governs this module: a client learns what it asked for wrongly and nothing about
how the server is built. No Cypher, no driver exception text, no stack traces, no hostnames
and no credentials cross the boundary. A Neo4j outage is a 503 whose body says the
knowledge graph is unavailable, not a ``ServiceUnavailable`` repr naming the bolt URI.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    """The single error shape every failing route returns."""

    error: str = Field(description="Stable machine-readable code, e.g. PASSAGE_NOT_FOUND.")
    detail: str = Field(description="Human-readable explanation, safe to show a user.")
    hint: str | None = Field(
        default=None,
        description="What the client could do differently, where there is a useful answer.",
    )


class ApiError(Exception):
    """Base for every deliberately raised product error."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str, *, hint: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.hint = hint

    def body(self) -> ErrorBody:
        return ErrorBody(error=self.code, detail=self.detail, hint=self.hint)


class NotFoundError(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class PassageNotFoundError(NotFoundError):
    code = "PASSAGE_NOT_FOUND"


class EntityNotFoundError(NotFoundError):
    code = "ENTITY_NOT_FOUND"


class WorkNotFoundError(NotFoundError):
    code = "WORK_NOT_FOUND"


class BadRequestError(ApiError):
    """The request parsed, but asks for something the product does not offer.

    Distinct from a 422: a 422 means the shape was wrong, this means the shape was right
    and the *meaning* is unsupported -- an unknown entity type, a relationship not on the
    traversal whitelist, a filter combination with no defined semantics.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"


class UnknownEntityTypeError(BadRequestError):
    code = "UNKNOWN_ENTITY_TYPE"


class GraphUnavailableError(ApiError):
    """Neo4j could not be reached or a query exceeded its budget."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "KNOWLEDGE_GRAPH_UNAVAILABLE"


#: Documented on every route, so the generated OpenAPI shows the failure modes rather than
#: FastAPI's bare default of "422 Validation Error".
COMMON_ERROR_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    400: {"model": ErrorBody, "description": "The request is well-formed but unsupported."},
    404: {"model": ErrorBody, "description": "No such passage, entity or work."},
    422: {"model": ErrorBody, "description": "A parameter failed validation."},
    503: {"model": ErrorBody, "description": "The knowledge graph is unavailable."},
}


async def _api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    if exc.status_code >= 500:
        logger.error("api error %s: %s", exc.code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=exc.body().model_dump())


async def _validation_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Pydantic's own error list is safe -- it names parameters the client sent -- but its
    # `input` echo can carry an arbitrary payload back, and `url` leaks the mount path.
    fields = ", ".join(".".join(str(p) for p in err["loc"][1:]) or "body" for err in exc.errors())
    body = ErrorBody(
        error="VALIDATION_ERROR",
        detail=f"Invalid request parameters: {fields}.",
        hint="See /docs for each parameter's accepted range.",
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body.model_dump()
    )


async def _starlette_http_handler(_: Request, exc: Exception) -> JSONResponse:
    """Give router-level failures the same body shape as everything else.

    Starlette raises its own ``HTTPException`` before any route runs -- an unmatched path,
    a method the route does not declare -- and its default handler renders
    ``{"detail": "Not Found"}``. That is a second error shape in an API whose contract says
    :class:`ErrorBody` is the one every failing route returns, so a client parsing
    ``error`` gets a ``KeyError`` on exactly the responses it is most likely to hit while
    integrating. Adversarial QA found both spellings live.
    """
    assert isinstance(exc, StarletteHTTPException)
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 406: "NOT_ACCEPTABLE"}
    detail = str(exc.detail) if exc.detail else "The request could not be served."
    body = ErrorBody(
        error=codes.get(exc.status_code, "REQUEST_FAILED"),
        detail=detail,
        hint=(
            "See /docs for the routes this API serves." if exc.status_code in {404, 405} else None
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
        headers=getattr(exc, "headers", None),
    )


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    """Last resort. The exception is logged in full and described to the client in none.

    Without this, FastAPI's default 500 page in debug mode renders a traceback that names
    file paths, query text and sometimes the connection string.
    """
    logger.exception("unhandled error serving request", exc_info=exc)
    body = ErrorBody(
        error="INTERNAL_ERROR",
        detail="The server failed to complete this request.",
        hint="This is a defect. Retrying the same request is unlikely to help.",
    )
    return JSONResponse(status_code=500, content=body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _starlette_http_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
