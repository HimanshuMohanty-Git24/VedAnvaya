"""Secret leakage regression: one recognisable key, and every surface it must not reach.

A credential does not leak through the path someone designed; it leaks through a repr, a
``model_dump`` in a debug endpoint, a vendor error string quoted into an exception, or a
log line written at DEBUG on a machine shipping logs somewhere. So the test is not "does
the code look careful" -- it is a sentinel pushed through the configured provider and then
searched for in every string the failure produces.

The sentinel is deliberately unmistakable. If any assertion here fails, the string in the
output *is* the key, and the fix is at the surface that printed it.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.llm.test_provider_contract import (
    FakeGeminiClient,
    fake_anthropic_client,
    fake_openai_client,
)
from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.synthesizer import synthesize
from vedagraph.llm.base import LLMMessage, LLMRequest
from vedagraph.llm.config import LLMSettings
from vedagraph.llm.errors import LLMConfigurationError, LLMError
from vedagraph.llm.factory import get_llm_provider
from vedagraph.llm.providers.anthropic import AnthropicProvider
from vedagraph.llm.providers.gemini import GeminiProvider
from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

SENTINEL = "sk-SENTINEL-must-never-appear-9f3a2b"


def settings(**overrides: Any) -> LLMSettings:
    base: dict[str, Any] = {
        "vedagraph_llm_provider": "gemini",
        "vedagraph_llm_model": "gemini-2.5-flash",
        "vedagraph_llm_api_key": SecretStr(SENTINEL),
        "vedagraph_llm_base_url": None,
        "google_api_key": None,
        "gemini_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
    }
    base.update(overrides)
    return LLMSettings(_env_file=None, **base)


def request() -> LLMRequest:
    return LLMRequest(messages=[LLMMessage(role="user", content="Who is Indra?")])


# ---------------------------------------------------------------------------
# Settings surfaces
# ---------------------------------------------------------------------------


def test_settings_repr_and_str_hide_the_key() -> None:
    configured = settings()

    assert SENTINEL not in repr(configured)
    assert SENTINEL not in str(configured)


def test_settings_serialisation_hides_the_key() -> None:
    configured = settings()

    assert SENTINEL not in str(configured.model_dump())
    assert SENTINEL not in configured.model_dump_json()


def test_safe_summary_reports_presence_and_not_the_value() -> None:
    summary = settings().safe_summary()

    assert summary["api_key_present"] is True
    assert SENTINEL not in str(summary)


def test_resolved_api_key_is_the_only_way_to_read_it() -> None:
    """The escape hatch exists and is explicit -- that is the point of SecretStr."""
    assert settings().resolved_api_key() == SENTINEL


# ---------------------------------------------------------------------------
# Provider surfaces
# ---------------------------------------------------------------------------


def gemini_with_sentinel(
    monkeypatch: pytest.MonkeyPatch, *, status_code: int = 200, body: Any = None
) -> GeminiProvider:
    provider = GeminiProvider(api_key=SENTINEL, model="gemini-2.5-flash", max_retries=0)
    monkeypatch.setattr(provider, "_client", FakeGeminiClient(status_code=status_code, body=body))
    return provider


def all_providers_with_sentinel(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    providers: list[Any] = [gemini_with_sentinel(monkeypatch)]

    if pytest.importorskip("openai", reason="openai SDK not installed"):
        compat = OpenAICompatProvider(
            provider_name="openai",
            api_key=SENTINEL,
            model="gpt-test",
            base_url="https://example.invalid/v1",
            max_retries=0,
        )
        monkeypatch.setattr(compat, "_client", fake_openai_client(None))
        providers.append(compat)

    if pytest.importorskip("anthropic", reason="anthropic SDK not installed"):
        claude = AnthropicProvider(api_key=SENTINEL, model="claude-test", max_retries=0)
        monkeypatch.setattr(claude, "_client", fake_anthropic_client(None))
        providers.append(claude)

    return providers


def test_provider_repr_and_str_hide_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for provider in all_providers_with_sentinel(monkeypatch):
        assert SENTINEL not in repr(provider)
        assert SENTINEL not in str(provider)


@pytest.mark.parametrize("status_code", [401, 403, 429, 500, 503, 400, 404])
def test_no_provider_error_quotes_the_key(
    status_code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every HTTP failure mode, including the ones whose vendor body echoes the key.

    The adapter maps on the status alone and never quotes the response body, which is why
    a 401 -- the case where Google's payload has been observed carrying the rejected key --
    cannot leak it.
    """
    provider = gemini_with_sentinel(monkeypatch, status_code=status_code)

    with pytest.raises(LLMError) as caught:
        provider.generate(request())

    assert SENTINEL not in str(caught.value)
    assert SENTINEL not in repr(caught.value)
    assert SENTINEL not in str(caught.value.detail)


def test_malformed_body_errors_do_not_quote_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for body in ({}, {"candidates": []}, {"promptFeedback": {"blockReason": "SAFETY"}}):
        provider = gemini_with_sentinel(monkeypatch, body=body)
        with pytest.raises(LLMError) as caught:
            provider.generate(request())
        assert SENTINEL not in str(caught.value)
        assert SENTINEL not in repr(caught.value)


def test_factory_configuration_errors_do_not_quote_the_key() -> None:
    with pytest.raises(LLMConfigurationError) as caught:
        get_llm_provider(settings(vedagraph_llm_provider="not-a-provider"))

    assert SENTINEL not in str(caught.value)
    assert SENTINEL not in repr(caught.value)


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


def test_failing_generate_logs_nothing_containing_the_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    provider = gemini_with_sentinel(monkeypatch, status_code=401)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(LLMError):
            provider.generate(request())

    _assert_logs_clean(caplog)


def test_degraded_synthesis_logs_nothing_containing_the_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The synthesizer logs a failure with ``exc_info=True``, so the traceback is
    formatted into the record. A key held on the provider must not appear in it."""
    provider = gemini_with_sentinel(monkeypatch, status_code=503)

    with caplog.at_level(logging.DEBUG):
        result = synthesize("Who is Indra?", EvidencePacket(), [], provider)

    assert result.degraded is True
    assert SENTINEL not in result.answer
    _assert_logs_clean(caplog)


def _assert_logs_clean(caplog: pytest.LogCaptureFixture) -> None:
    for record in caplog.records:
        assert SENTINEL not in record.getMessage()
        assert SENTINEL not in str(record.args)
        assert SENTINEL not in logging.Formatter().format(record)
    assert SENTINEL not in caplog.text


# ---------------------------------------------------------------------------
# The HTTP surface
# ---------------------------------------------------------------------------


def test_ask_health_body_never_carries_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vedagraph.api.app import create_app

    configured = settings()
    # Patched in both namespaces: the route reads the settings for its summary and the
    # factory reads them again to decide whether a provider can be built.
    monkeypatch.setattr("vedagraph.llm.config.get_llm_settings", lambda: configured)
    monkeypatch.setattr("vedagraph.llm.factory.get_llm_settings", lambda: configured)

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/api/v1/ask/health")

    assert response.status_code == 200
    assert SENTINEL not in response.text
    body = response.json()
    assert isinstance(body["llm"]["api_key_present"], bool)
    assert body["llm"]["api_key_present"] is True
    assert "api_key" not in body["llm"]


def test_ask_health_says_unavailable_without_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vedagraph.api.app import create_app

    configured = settings(vedagraph_llm_api_key=None)
    monkeypatch.setattr("vedagraph.llm.config.get_llm_settings", lambda: configured)
    monkeypatch.setattr("vedagraph.llm.factory.get_llm_settings", lambda: configured)

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/api/v1/ask/health")

    assert response.status_code == 503
    body = response.json()
    assert body["ask_available"] is False
    assert body["llm"]["api_key_present"] is False
    assert SENTINEL not in response.text
