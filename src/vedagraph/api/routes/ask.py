"""Ask VedaGraph: evidence-grounded conversational research over the frozen graph.

Thin by design, like every other route module here: one service call, no Cypher, no
provider names. The LLM provider is resolved from configuration by
:func:`~vedagraph.llm.factory.get_llm_provider` and injected, so this module contains no
knowledge of which vendor is active and switching providers never edits this file.

**The question never becomes a query.** No client input reaches Cypher as syntax. The
planner classifies intent deterministically, the resolver binds entity names as
parameters, and the retriever runs a fixed catalogue of named queries. The model receives
retrieved evidence and never a database handle, so there is no path by which a generated
string could execute.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from vedagraph.api.ask.models import AskRequest, AskResponse
from vedagraph.api.ask.service import AskService
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES, ApiError
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from vedagraph.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ask"], responses=COMMON_ERROR_RESPONSES)


class AskUnavailableError(ApiError):
    """The synthesis backend is not configured or not reachable.

    Separate from :class:`~vedagraph.api.errors.GraphUnavailableError` because the two
    fail for unrelated reasons and a client can act on the difference: the graph being
    down is an outage, an unconfigured provider is a deployment that never set
    ``VEDAGRAPH_LLM_API_KEY``. Neither body ever carries the key.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ASK_UNAVAILABLE"


ASK_DESCRIPTION = """
Ask a research question in natural language and receive an answer built from retrieved
VedaGraph evidence, with every factual claim carrying a citation into the graph.

**This is not a chat model answering from memory.** The pipeline is
question → intent plan → entity resolution → multi-channel graph retrieval → frozen
evidence packet → synthesis. The model sees only what retrieval found, and
`retrieval_summary` reports which channels ran. An answer whose claims are not in the
evidence packet is a defect, not a feature: every `[E1]`-style reference in `answer` is
checked against the packet before the response is returned, and an unverifiable one is
removed with a caveat saying so.

**Absence is never asserted.** A question the graph cannot answer returns
`INSUFFICIENT_EVIDENCE` and says which dimension was not reached. It does not return a
confident denial. The Yajurveda's lexical recovery limit is the worked example: the graph
records that its Sanskrit is present only as text extracted from printed containers, so a
term not found there has not been shown absent from the Yajurveda.

**Interpretation is labelled.** Where an answer draws on an `InterpretiveClaim`,
`interpretive_content_present` is true and the prose attributes the reading rather than
stating it as what the text says.

**The synthesis backend is a configuration choice.** `llm.provider` and `llm.model`
report which one served the request. No credential is ever returned.
"""


@router.post(
    "/ask",
    summary="Ask VedaGraph",
    description=ASK_DESCRIPTION,
    response_model=AskResponse,
    responses={
        **COMMON_ERROR_RESPONSES,
        503: {"description": "The graph or the synthesis backend is unavailable."},
    },
)
def ask_endpoint(repository: RepositoryDep, request: AskRequest) -> AskResponse:
    try:
        provider = get_llm_provider()
    except LLMConfigurationError as exc:
        # exc.detail is written by the config layer and never interpolates the key.
        logger.error("ask: provider not configured (%s)", type(exc).__name__)
        raise AskUnavailableError(
            "The synthesis backend is not configured.",
            hint="Set VEDAGRAPH_LLM_PROVIDER, VEDAGRAPH_LLM_MODEL and "
            "VEDAGRAPH_LLM_API_KEY in the deployment environment.",
        ) from exc

    service = AskService(repository, provider)

    try:
        return service.ask(request)
    except LLMAuthenticationError as exc:
        logger.error("ask: provider rejected credentials")
        raise AskUnavailableError(
            "The synthesis backend rejected this deployment's credentials.",
            hint="The configured API key is missing, invalid or revoked.",
        ) from exc
    except LLMRateLimitError as exc:
        raise AskUnavailableError(
            "The synthesis backend is rate limiting this deployment.",
            hint="Retry shortly.",
        ) from exc
    except LLMTimeoutError as exc:
        raise AskUnavailableError(
            "The synthesis backend did not respond in time.",
            hint="Retry, or ask a narrower question.",
        ) from exc
    except LLMError as exc:
        # Catch-all for the normalised hierarchy. Provider text never reaches the client:
        # the vendor's message can quote the request, and some vendors echo headers.
        logger.error("ask: provider error (%s)", type(exc).__name__)
        raise AskUnavailableError("The synthesis backend failed to answer this question.") from exc


@router.get(
    "/ask/health",
    summary="Ask readiness",
    description=(
        "Whether Ask VedaGraph can serve: which provider and model are configured and "
        "whether a credential is present. Never returns the credential itself."
    ),
)
def ask_health_endpoint() -> JSONResponse:
    from vedagraph.llm.config import get_llm_settings

    settings = get_llm_settings()
    # safe_summary() reports api_key_present as a boolean and holds no secret value.
    summary = settings.safe_summary()

    try:
        get_llm_provider()
        configured = True
        detail = "The synthesis backend is configured."
    except LLMConfigurationError as exc:
        configured = False
        detail = exc.detail

    payload = {"ask_available": configured, "detail": detail, "llm": summary}
    return JSONResponse(
        status_code=status.HTTP_200_OK if configured else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
