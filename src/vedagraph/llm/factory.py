"""Provider factory — the single place that maps provider names to implementations.

All provider-specific logic lives here and in providers/. No other module may
contain an `if provider == "..."` conditional.
"""

from __future__ import annotations

from vedagraph.llm.base import LLMProvider
from vedagraph.llm.config import LLMSettings, get_llm_settings
from vedagraph.llm.credentials import CredentialSlots, load_credential_slots
from vedagraph.llm.errors import LLMConfigurationError
from vedagraph.llm.failover import FailoverProvider
from vedagraph.llm.redaction import register_secrets

_KNOWN_PROVIDERS = frozenset(
    {"gemini", "openai", "anthropic", "groq", "openrouter", "xai", "openai_compatible"}
)

# OpenAI-compatible providers (share OpenAICompatProvider)
_OPENAI_COMPAT = frozenset({"openai", "groq", "openrouter", "xai", "openai_compatible"})


def credential_slots(settings: LLMSettings | None = None) -> CredentialSlots:
    """The configured credentials for the configured provider, in the order they are used.

    Slot 1 is whatever the single-key configuration already resolved to, so nothing about
    a one-key repository changes. Registering the values with the redaction layer here is
    deliberate: this is the one function every caller reaches before a request is made.
    """
    if settings is None:
        settings = get_llm_settings()
    provider = settings.vedagraph_llm_provider.lower().strip()
    slots = load_credential_slots(provider)
    resolved = settings.resolved_api_key()
    if resolved:
        slots = slots.with_first(resolved, "VEDAGRAPH_LLM_API_KEY")
    register_secrets(slots.raw_values())
    return slots


def get_llm_provider(settings: LLMSettings | None = None) -> LLMProvider:
    """Instantiate the configured provider. Fails fast on misconfiguration.

    With one configured credential this returns the bare adapter, byte for byte the
    object it always returned. With two or more it returns a :class:`FailoverProvider`
    over one adapter per credential, whose ``name`` and ``model`` are the same values the
    bare adapter reports -- so the benchmark's run identity cannot notice.
    """
    if settings is None:
        settings = get_llm_settings()

    provider = settings.vedagraph_llm_provider.lower().strip()

    if provider not in _KNOWN_PROVIDERS:
        raise LLMConfigurationError(
            f"Unknown LLM provider '{provider}'. "
            f"Supported: {', '.join(sorted(_KNOWN_PROVIDERS))}. "
            "Set VEDAGRAPH_LLM_PROVIDER in .env."
        )

    slots = credential_slots(settings)
    if not slots:
        raise LLMConfigurationError(
            f"No API key found for provider '{provider}'. "
            "Set VEDAGRAPH_LLM_API_KEY (or a provider-specific fallback) in .env. "
            "The key is never printed or logged."
        )

    model = settings.vedagraph_llm_model.strip()
    if not model:
        raise LLMConfigurationError("VEDAGRAPH_LLM_MODEL is required. Set it in .env.")

    built = [_build_one(settings, provider, model, slots.value(i)) for i in range(len(slots))]
    return built[0] if len(built) == 1 else FailoverProvider(built)


def _build_one(
    settings: LLMSettings, provider: str, model: str, api_key: str
) -> LLMProvider:
    """One adapter for one credential. Everything except the credential is shared."""
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
