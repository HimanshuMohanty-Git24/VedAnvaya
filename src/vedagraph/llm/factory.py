"""Provider factory — the single place that maps provider names to implementations.

All provider-specific logic lives here and in providers/. No other module may
contain an `if provider == "..."` conditional.
"""

from __future__ import annotations

from vedagraph.llm.base import LLMProvider
from vedagraph.llm.config import LLMSettings, get_llm_settings
from vedagraph.llm.errors import LLMConfigurationError

_KNOWN_PROVIDERS = frozenset(
    {"gemini", "openai", "anthropic", "groq", "openrouter", "xai", "openai_compatible"}
)

# OpenAI-compatible providers (share OpenAICompatProvider)
_OPENAI_COMPAT = frozenset({"openai", "groq", "openrouter", "xai", "openai_compatible"})


def get_llm_provider(settings: LLMSettings | None = None) -> LLMProvider:
    """Instantiate the configured provider. Fails fast on misconfiguration."""
    if settings is None:
        settings = get_llm_settings()

    provider = settings.vedagraph_llm_provider.lower().strip()

    if provider not in _KNOWN_PROVIDERS:
        raise LLMConfigurationError(
            f"Unknown LLM provider '{provider}'. "
            f"Supported: {', '.join(sorted(_KNOWN_PROVIDERS))}. "
            "Set VEDAGRAPH_LLM_PROVIDER in .env."
        )

    api_key = settings.resolved_api_key()
    if not api_key:
        raise LLMConfigurationError(
            f"No API key found for provider '{provider}'. "
            "Set VEDAGRAPH_LLM_API_KEY (or a provider-specific fallback) in .env. "
            "The key is never printed or logged."
        )

    model = settings.vedagraph_llm_model.strip()
    if not model:
        raise LLMConfigurationError("VEDAGRAPH_LLM_MODEL is required. Set it in .env.")

    if provider == "gemini":
        from vedagraph.llm.providers.gemini import GeminiProvider

        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=settings.vedagraph_llm_timeout_seconds,
            max_output_tokens=settings.vedagraph_llm_max_output_tokens,
            temperature=settings.vedagraph_llm_temperature,
            max_retries=settings.vedagraph_llm_max_retries,
            base_url=settings.vedagraph_llm_base_url,
        )

    if provider == "anthropic":
        from vedagraph.llm.providers.anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=settings.vedagraph_llm_timeout_seconds,
            max_output_tokens=settings.vedagraph_llm_max_output_tokens,
            temperature=settings.vedagraph_llm_temperature,
            max_retries=settings.vedagraph_llm_max_retries,
        )

    # All OpenAI-compatible providers
    from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

    extra_headers: dict[str, str] = {}
    if provider == "openrouter":
        extra_headers["HTTP-Referer"] = "https://vedagraph.app"
        extra_headers["X-Title"] = "VedaGraph"

    base_url = settings.vedagraph_llm_base_url  # may be None for openai/groq/xai (uses preset)

    return OpenAICompatProvider(
        provider_name=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=settings.vedagraph_llm_timeout_seconds,
        max_output_tokens=settings.vedagraph_llm_max_output_tokens,
        temperature=settings.vedagraph_llm_temperature,
        max_retries=settings.vedagraph_llm_max_retries,
        extra_headers=extra_headers or None,
    )
