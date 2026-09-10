"""The only place in the API that talks to Neo4j.

Three jobs, and the third is the one that matters.

*Connection.* One driver for the process, opened lazily and closed on shutdown.

*Execution.* Every call is parameterised. :meth:`Neo4jRepository.run` takes Cypher and a
parameter mapping and there is no code path that concatenates a client value into a query
string. Where a query genuinely must vary its structure -- a relationship type in a
traversal, a label in a filter -- the caller passes it through
:func:`validated_relationship_types` or :func:`validated_label`, which check against the
frozen ontology and raise rather than interpolate anything unrecognised.

*Failure translation.* Driver exceptions never leave this module. A dead database, an
exhausted pool and a query that blew its timeout all become
:class:`~vedagraph.api.errors.GraphUnavailableError`, so no route has to know that
``neo4j.exceptions`` exists and no client ever sees a bolt URI in an error body.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

from neo4j import Driver, GraphDatabase, Query
from neo4j import exceptions as neo4j_exceptions

from vedagraph.api.config import ApiSettings
from vedagraph.api.errors import BadRequestError, GraphUnavailableError
from vedagraph.domain.ontology import (
    INTERNAL_MARKED_LABELS,
    LABEL_INTERNAL,
    PRODUCT_LABELS,
)

logger = logging.getLogger(__name__)

#: Labels a client may never name, whatever it asks for. ``Internal`` marks the 72,514
#: diagnostic nodes and ``QAIssue`` the 915 build findings; both are real graph content and
#: neither is Vedic knowledge. Keeping the set here rather than in each route means a label
#: added to the internal set later is excluded everywhere by editing one import.
FORBIDDEN_LABELS: Final[frozenset[str]] = INTERNAL_MARKED_LABELS | {LABEL_INTERNAL}

#: A Neo4j identifier we are willing to interpolate, having first checked it against the
#: ontology. The pattern is a second gate, not the first: nothing reaches interpolation
#: without appearing in an allow-list, and this rejects anything that could close a
#: backtick even if an allow-list were later mis-edited.
_SAFE_IDENTIFIER: Final = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def validated_label(label: str) -> str:
    """Return ``label`` if it is a product label, else raise.

    Used where a query must filter on a label the client chose. An unknown label is a 400
    rather than an empty result, because "no such type" and "that type is empty" are
    different answers and this API refuses to conflate them.
    """
    if label in FORBIDDEN_LABELS or label not in PRODUCT_LABELS:
        raise BadRequestError(
            f"'{label}' is not a queryable knowledge type.",
            hint="GET /api/v1/entities lists the available types.",
        )
    if not _SAFE_IDENTIFIER.match(label):
        raise BadRequestError(f"'{label}' is not a valid type name.")
    return label


def validated_relationship_types(
    requested: tuple[str, ...], allowed: frozenset[str]
) -> tuple[str, ...]:
    """Return the requested relationship types, all of which must be in ``allowed``.

    ``allowed`` is always a whitelist owned by the calling service -- the traversal
    whitelist for pathfinding, the neighbourhood set for exploration. A type outside it is
    refused by name so the client can see which one was wrong.
    """
    for name in requested:
        if name not in allowed or not _SAFE_IDENTIFIER.match(name):
            raise BadRequestError(
                f"'{name}' is not a traversable relationship for this operation.",
                hint=f"Traversable here: {', '.join(sorted(allowed))}.",
            )
    return requested


class Neo4jRepository:
    """A thin, safe execution surface over one Neo4j driver."""

    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
        self._driver: Driver | None = None

    # -- lifecycle ---------------------------------------------------------------

    def connect(self) -> None:
        if self._driver is not None:
            return
        try:
            self._driver = GraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=self._settings.auth,
                connection_timeout=self._settings.neo4j_query_timeout_seconds,
            )
        except Exception as exc:
            # The message can carry the URI, so it is logged and not re-raised.
            logger.error("could not construct Neo4j driver: %s", type(exc).__name__)
            raise GraphUnavailableError("The knowledge graph is unavailable.") from None

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self.connect()
        assert self._driver is not None
        return self._driver

    # -- execution ---------------------------------------------------------------

    def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]:
        """Execute read-only Cypher and materialise the rows.

        Rows are materialised inside the session rather than streamed out of it: a lazy
        result that escapes its session raises later, in a route, where the failure would
        be translated as an unhandled 500 instead of a 503.

        The timeout travels inside a :class:`neo4j.Query`, which is the only place the
        driver reads it from. ``Session.run(query, parameters, **kwargs)`` documents
        ``kwargs`` as *additional query parameters*, so the obvious spelling --
        ``session.run(cypher, parameters, timeout=...)`` -- does not set a timeout at all:
        it binds a Cypher parameter named ``$timeout`` and silently leaves every query
        unbounded. This API shipped that spelling and it was found by adversarial QA, which
        proved it by configuring a 1ms budget and watching a 20-million-row aggregation run
        to completion. Two things were wrong at once and both are fixed here: no query had
        any time bound, and a stray ``$timeout`` was injected into every statement -- where,
        because ``kwargs`` take precedence over ``parameters``, it would have silently
        clobbered a real parameter of that name. ``test_query_timeout_is_enforced`` pins it.
        """
        query = Query(cypher, timeout=self._settings.neo4j_query_timeout_seconds)
        try:
            with self.driver.session(database=self._settings.neo4j_database) as session:
                result = session.run(query, parameters)
                return [dict(record) for record in result]
        except (
            neo4j_exceptions.ServiceUnavailable,
            neo4j_exceptions.SessionExpired,
            neo4j_exceptions.TransientError,
            neo4j_exceptions.ConfigurationError,
        ) as exc:
            logger.error("neo4j unavailable: %s", type(exc).__name__)
            raise GraphUnavailableError("The knowledge graph is unavailable.") from None
        except neo4j_exceptions.Neo4jError as exc:
            # A timeout and a malformed query are both 503s and are not the same event, so
            # they are logged differently: the first says this read needs bounding or
            # indexing, the second says the Cypher is wrong. Collapsing them sends whoever
            # reads the log looking for a syntax error in a query that is merely too slow.
            if str(exc.code or "").endswith("TransactionTimedOutClientConfiguration"):
                logger.error(
                    "query exceeded the %.1fs budget: %s",
                    self._settings.neo4j_query_timeout_seconds,
                    cypher[:200],
                )
                raise GraphUnavailableError(
                    "This request took too long to answer and was stopped.",
                    hint="Narrow it with a smaller limit, a lower depth, or a filter.",
                ) from None
            # A malformed query is our defect, not the client's. It must not surface as a
            # 400 blaming the caller, and its message quotes Cypher, so it is logged only.
            logger.error("cypher failed (%s): %s", type(exc).__name__, cypher[:200])
            raise GraphUnavailableError(
                "The knowledge graph could not answer this request."
            ) from None

    def run_one(self, cypher: str, /, **parameters: Any) -> dict[str, Any] | None:
        rows = self.run(cypher, **parameters)
        return rows[0] if rows else None

    def run_named(self, query_name: str, /, **overrides: Any) -> list[dict[str, Any]]:
        """Execute a query from the frozen domain library by name.

        This is the preferred path. ``vedagraph.domain.queries`` carries 91 questions that
        were graded against the 100-question benchmark, each with its caveat and default
        parameters attached, and re-typing one of them here would fork it from the version
        the benchmark measured.
        """
        from vedagraph.domain.queries import QUERIES_BY_NAME

        query = QUERIES_BY_NAME.get(query_name)
        if query is None:  # pragma: no cover - a coding error, not a client error
            raise KeyError(f"no named domain query {query_name!r}")
        parameters: dict[str, Any] = {**query.parameters, **overrides}
        return self.run(query.cypher, **parameters)

    def verify_connectivity(self) -> None:
        try:
            self.driver.verify_connectivity()
        except Exception as exc:
            logger.error("connectivity check failed: %s", type(exc).__name__)
            raise GraphUnavailableError("The knowledge graph is unavailable.") from None


def named_query_caveat(query_name: str) -> str:
    """The frozen caveat attached to a named domain query.

    Exposed so services can put the measured caveat in the response rather than retyping
    it. V3.1 and V3.2 both found hand-copied caveat prose that had drifted from the data it
    described; the fix is to never copy it.
    """
    from vedagraph.domain.queries import QUERIES_BY_NAME

    query = QUERIES_BY_NAME.get(query_name)
    return query.caveat if query is not None else ""
