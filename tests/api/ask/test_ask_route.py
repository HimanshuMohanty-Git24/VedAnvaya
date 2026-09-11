"""POST /api/v1/ask at the HTTP boundary, with both dependencies replaced.

Two things are mocked because two things must not be reachable from a test: the graph, via
the ``get_repository`` dependency override that :mod:`tests.api.conftest` installs, and the
provider, via the module-level ``get_llm_provider`` the route calls. The provider stub is
autouse -- without it a route test would resolve this repository's real ``.env``, build a
live Gemini client and spend money on a validation assertion.

What is asserted here is the contract a client integrates against: the response shape, the
four ways a request is rejected before any work happens, and that a deployment with no
credential answers 503 with a body that names the fault and carries nothing secret.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from vedagraph.api.ask.models import AskResponse, SupportLevel
from vedagraph.api.routes import ask as ask_route
from vedagraph.llm.base import LLMProvider, LLMRequest, LLMResponse, LLMUsage
from vedagraph.llm.errors import LLMConfigurationError

ANSWER = "VedaGraph's evidence does not establish an answer to this question."

#: A sentinel in the configuration error's text. The route must report the fault without
#: echoing the detail, because a config layer's message is not written for a client.
CONFIG_SENTINEL = "sk-ROUTE-SENTINEL-9f3a2b"


class StubProvider(LLMProvider):
    def __init__(self, text: str = ANSWER) -> None:
        self._text = text
        self.calls = 0

    @property
    def name(self) -> str:
        return "stub"

    @property
    def model(self) -> str:
        return "stub-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            text=self._text,
            finish_reason="stop",
            provider="stub",
            model="stub-1",
            usage=LLMUsage(input_tokens=10, output_tokens=5),
        )


@pytest.fixture(autouse=True)
def stub_provider(monkeypatch: pytest.MonkeyPatch) -> StubProvider:
    stub = StubProvider()
    monkeypatch.setattr(ask_route, "get_llm_provider", lambda: stub)
    return stub


def post(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/ask", json=body)


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_valid_question_returns_the_ask_response_shape(client: TestClient) -> None:
    response = post(client, question="Who is Indra?")

    assert response.status_code == 200
    parsed = AskResponse.model_validate(response.json())
    assert parsed.answer
    assert parsed.llm.provider == "stub"
    assert parsed.llm.model == "stub-1"
    assert parsed.retrieval_summary.total_ms >= 0


def test_an_unretrieved_question_is_insufficient_and_not_a_denial(
    client: TestClient,
) -> None:
    """The graph returned nothing, so the response says its evidence does not establish an
    answer. It must not claim the corpus is silent."""
    response = post(client, question="Who is Shiva?")

    body = response.json()
    assert body["status"] == "INSUFFICIENT_EVIDENCE"
    assert body["support_level"] == SupportLevel.INSUFFICIENT.value
    assert body["evidence"] == []
    assert body["citations"] == []
    assert any(c["source"] == "retrieval" for c in body["caveats"])


def test_the_provider_is_called_exactly_once_per_request(
    client: TestClient, stub_provider: StubProvider
) -> None:
    post(client, question="Who is Indra?")

    assert stub_provider.calls == 1


def test_the_retrieval_summary_separates_empty_from_unexamined(
    client: TestClient,
) -> None:
    response = post(client, question="Does Yajurveda mention ayas?")

    summary = response.json()["retrieval_summary"]
    # The lexical channel ran against the (empty) fake and is reported as searched, not
    # omitted: "we looked and found nothing" and "we never looked" are different answers.
    assert "lexical_presence" in summary["channels_empty"]
    assert "lexical_presence" not in summary["channels_used"]
    assert summary["veda_scope"] == "YV"


# ---------------------------------------------------------------------------
# Rejected before any work happens
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("over the maximum length", {"question": "a" * 2001}),
        ("empty", {"question": ""}),
        ("an invalid veda", {"question": "Who is Indra?", "veda": "Rigveda"}),
        ("an invalid mode", {"question": "Who is Indra?", "mode": "SHOUTING"}),
        ("an unknown field", {"question": "Who is Indra?", "cypher": "MATCH (n) RETURN n"}),
    ],
)
def test_malformed_requests_are_422(
    label: str, body: dict[str, Any], client: TestClient, stub_provider: StubProvider
) -> None:
    response = client.post("/api/v1/ask", json=body)

    assert response.status_code == 422, label
    assert response.json()["error"] == "VALIDATION_ERROR"
    # Validation runs before the handler, so no provider call was made and no bill.
    assert stub_provider.calls == 0


def test_the_maximum_length_boundary_is_accepted(client: TestClient) -> None:
    response = post(client, question="a" * 2000)

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# An unconfigured deployment
# ---------------------------------------------------------------------------


def test_an_unconfigured_provider_is_503_ask_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unconfigured() -> LLMProvider:
        raise LLMConfigurationError(
            f"No API key found. The configured value was {CONFIG_SENTINEL}."
        )

    monkeypatch.setattr(ask_route, "get_llm_provider", unconfigured)

    response = post(client, question="Who is Indra?")

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "ASK_UNAVAILABLE"
    assert "not configured" in body["detail"]
    # The config layer's own text is not echoed, so nothing it interpolated can escape.
    assert CONFIG_SENTINEL not in response.text
    assert "api_key" not in response.text


def test_ask_unavailable_is_distinct_from_a_graph_outage(
    down_client: TestClient,
) -> None:
    """A client can act on the difference: an outage is transient, an unset key is not."""
    response = down_client.post("/api/v1/ask", json={"question": "Who is Indra?"})

    assert response.status_code == 503
    assert response.json()["error"] == "KNOWLEDGE_GRAPH_UNAVAILABLE"


# ---------------------------------------------------------------------------
# No credential surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"question": "Who is Indra?"},
        {"question": "Does Yajurveda mention ayas?", "veda": "YV"},
        {"question": "How are Agni and Soma connected?", "mode": "GRAPH", "debug": True},
    ],
)
def test_no_response_body_mentions_a_key(body: dict[str, Any], client: TestClient) -> None:
    response = client.post("/api/v1/ask", json=body)

    assert response.status_code == 200
    assert "api_key" not in response.text
    assert "Authorization" not in response.text
