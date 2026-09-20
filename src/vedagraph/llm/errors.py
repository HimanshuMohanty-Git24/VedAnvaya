"""Normalized LLM error hierarchy. Provider errors never leak into application layers."""

from __future__ import annotations

from vedagraph.llm.redaction import scrub


class LLMError(Exception):
    """Base for all provider errors after normalization.

    Every normalised error passes through here, which makes it the one place worth
    scrubbing configured credentials out of. The adapters already refuse to quote a
    response body, so this guards what they cannot see: an SDK that formats the request
    into its exception, a vendor that echoes the rejected key in a 401, and the failover
    path, which re-raises the last provider error with several credentials in memory.
    """

    def __init__(self, detail: str, *, provider: str = "unknown", retryable: bool = False) -> None:
        detail = scrub(detail)
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
    """Provider rate limit hit. Retryable with backoff unless the *daily* cap is gone.

    ``daily_exhausted`` separates the two limits that share this one status code. A
    per-minute window refills while a caller waits; a per-day allowance does not, and
    every attempt against it is itself metered -- so a batch that sleeps and asks again
    spends the headroom it is waiting for. Only the adapter can tell them apart, because
    the period appears solely in the provider's prose, so the finding is recorded here
    rather than re-derived by each caller. ``retryable`` follows from it, which is what
    makes the distinction reach retry ladders that never heard of a daily quota.
    """

    def __init__(
        self,
        *,
        provider: str,
        retry_after_seconds: float | None = None,
        daily_exhausted: bool = False,
    ) -> None:
        suffix = " The daily allowance is exhausted; waiting will not clear it."
        super().__init__(
            f"Rate limit reached for provider '{provider}'." + (suffix if daily_exhausted else ""),
            provider=provider,
            retryable=not daily_exhausted,
        )
        self.retry_after_seconds = retry_after_seconds
        self.daily_exhausted = daily_exhausted


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
