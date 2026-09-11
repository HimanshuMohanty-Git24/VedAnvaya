"""The env-switch proof: provider selection is configuration and nothing else.

Seven provider names must each produce a working :class:`LLMProvider` from settings alone,
with no code path in the Ask pipeline naming a vendor. The second half of the proof is that
five of those seven share one adapter class -- if the OpenAI-compatible family had been
implemented once per vendor, "switching provider is an env change" would be true of the
factory and false of the maintenance burden behind it.

Settings are built with ``_env_file=None`` and every fallback key pinned to ``None`` on
purpose. This repository has a real ``.env``, and a test that let it load would assert
against the developer's credentials rather than against the case it names -- the missing-key
case would pass for the wrong reason, or fail on a machine that has no key.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import SecretStr

from vedagraph.llm.base import LLMProvider
from vedagraph.llm.config import LLMSettings
from vedagraph.llm.errors import LLMConfigurationError
from vedagraph.llm.factory import get_llm_provider
from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

ALL_PROVIDERS = (
    "gemini",
    "openai",
    "anthropic",
    "groq",
    "openrouter",
    "xai",
    "openai_compatible",
)

#: The five names the shared OpenAI-compatible adapter must cover.
OPENAI_COMPAT_FAMILY = ("openai", "groq", "openrouter", "xai", "openai_compatible")

#: Which SDK each provider needs installed, if any. Gemini speaks REST over httpx.
_REQUIRED_SDK = {
    "openai": "openai",
    "groq": "openai",
    "openrouter": "openai",
    "xai": "openai",
    "openai_compatible": "openai",
    "anthropic": "anthropic",
}


def settings(**overrides: Any) -> LLMSettings:
    base: dict[str, Any] = {
        "vedagraph_llm_provider": "gemini",
        "vedagraph_llm_model": "m",
        "vedagraph_llm_api_key": SecretStr("k"),
        "vedagraph_llm_base_url": "https://example.invalid/v1",
        "google_api_key": None,
        "gemini_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
    }
    base.update(overrides)
    return LLMSettings(_env_file=None, **base)


@pytest.mark.parametrize("provider_name", ALL_PROVIDERS)
def test_every_provider_is_reachable_from_settings_alone(provider_name: str) -> None:
    sdk = _REQUIRED_SDK.get(provider_name)
    if sdk:
        pytest.importorskip(sdk)

    provider = get_llm_provider(settings(vedagraph_llm_provider=provider_name))

    assert isinstance(provider, LLMProvider)
    assert provider.name == provider_name
    assert provider.model == "m"


def test_provider_name_is_case_and_whitespace_insensitive() -> None:
    provider = get_llm_provider(settings(vedagraph_llm_provider="  GEMINI  "))
    assert provider.name == "gemini"


def test_the_openai_compatible_family_shares_one_adapter() -> None:
    """Five vendors, one class. Duplicated adapters would each drift separately."""
    pytest.importorskip("openai")

    classes = {
        type(get_llm_provider(settings(vedagraph_llm_provider=name)))
        for name in OPENAI_COMPAT_FAMILY
    }

    assert classes == {OpenAICompatProvider}


def test_openrouter_gets_its_attribution_headers() -> None:
    """The one vendor-specific detail the factory owns, kept out of the adapter."""
    pytest.importorskip("openai")

    provider = get_llm_provider(settings(vedagraph_llm_provider="openrouter"))

    assert isinstance(provider, OpenAICompatProvider)
    assert provider._extra_headers["X-Title"] == "VedaGraph"


def test_unknown_provider_names_the_supported_set() -> None:
    with pytest.raises(LLMConfigurationError) as caught:
        get_llm_provider(settings(vedagraph_llm_provider="palm2"))

    message = str(caught.value)
    assert "palm2" in message
    for name in ALL_PROVIDERS:
        assert name in message
    assert "VEDAGRAPH_LLM_PROVIDER" in message


def test_missing_api_key_fails_at_construction() -> None:
    with pytest.raises(LLMConfigurationError) as caught:
        get_llm_provider(settings(vedagraph_llm_api_key=None))

    assert "VEDAGRAPH_LLM_API_KEY" in str(caught.value)


def test_empty_model_fails_at_construction() -> None:
    with pytest.raises(LLMConfigurationError) as caught:
        get_llm_provider(settings(vedagraph_llm_model="   "))

    assert "VEDAGRAPH_LLM_MODEL" in str(caught.value)


@pytest.mark.parametrize(
    ("provider_name", "fallback_field"),
    [
        ("gemini", "gemini_api_key"),
        ("gemini", "google_api_key"),
        ("openai", "openai_api_key"),
        ("anthropic", "anthropic_api_key"),
        ("groq", "openai_api_key"),
    ],
)
def test_provider_specific_fallback_keys_resolve(provider_name: str, fallback_field: str) -> None:
    resolved = settings(
        vedagraph_llm_provider=provider_name,
        vedagraph_llm_api_key=None,
        **{fallback_field: SecretStr("fallback-key")},
    ).resolved_api_key()

    assert resolved == "fallback-key"


def test_safe_summary_reports_configuration_without_the_key() -> None:
    summary = settings(vedagraph_llm_api_key=SecretStr("summary-probe-key")).safe_summary()

    assert summary["provider"] == "gemini"
    assert summary["model"] == "m"
    assert summary["api_key_present"] is True
    # Presence is a boolean and the value is absent entirely, not masked.
    assert "api_key" not in summary
    assert "summary-probe-key" not in str(summary)


def test_safe_summary_says_so_when_no_key_is_configured() -> None:
    assert settings(vedagraph_llm_api_key=None).safe_summary()["api_key_present"] is False
