"""Normalized LLM error hierarchy. Provider errors never leak into application layers."""

from __future__ import annotations


class LLMError(Exception):
    """Base for all provider errors after normalization."""

    def __init__(self, detail: str, *, provider: str = "unknown", retryable: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.provider = provider
        self.retryable = retryable


class LLMAuthenticationError(LLMError):
    """API key is missing, invalid, or expired. Do NOT retry."""

    def __init__(self, *, provider: str) -> None:
        super().__init__(
            f"LLM authentication failed for provider '{provider}'. "
            "Check VEDAGRAPH_LLM_API_KEY in .env.",
            provider=provider,
            retryable=False,
        )


class LLMRateLimitError(LLMError):
    """Provider rate limit hit. Retryable with backoff."""

    def __init__(self, *, provider: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(
            f"Rate limit reached for provider '{provider}'.",
            provider=provider,
            retryable=True,
        )
        self.retry_after_seconds = retry_after_seconds


class LLMTimeoutError(LLMError):
    """Request timed out. Retryable."""

    def __init__(self, *, provider: str, timeout_seconds: float) -> None:
        super().__init__(
            f"LLM request to '{provider}' timed out after {timeout_seconds}s.",
            provider=provider,
            retryable=True,
        )


class LLMProviderUnavailableError(LLMError):
    """Provider returned a 5xx or is unreachable. Retryable."""

    def __init__(self, *, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' is unavailable.",
            provider=provider,
            retryable=True,
        )


class LLMConfigurationError(LLMError):
    """Startup-time misconfiguration. Do NOT retry."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, provider="config", retryable=False)


class LLMResponseError(LLMError):
    """Provider returned a malformed or unacceptable response."""

    def __init__(self, *, provider: str, detail: str) -> None:
        super().__init__(detail, provider=provider, retryable=False)


class LLMContentBlockedError(LLMError):
    """Content safety filter blocked the request or response."""

    def __init__(self, *, provider: str) -> None:
        super().__init__(
            f"Content blocked by provider '{provider}' safety filters.",
            provider=provider,
            retryable=False,
        )


class LLMContextWindowError(LLMError):
    """Request exceeded the provider's context window."""

    def __init__(self, *, provider: str) -> None:
        super().__init__(
            f"Request exceeded the context window of provider '{provider}'.",
            provider=provider,
            retryable=False,
        )
