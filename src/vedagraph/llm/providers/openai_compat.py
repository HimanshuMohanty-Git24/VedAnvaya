"""OpenAI-compatible adapter covering OpenAI, Groq, OpenRouter, xAI/Grok.

These providers share the same HTTP interface so one adapter handles all of them.
Provider-specific defaults (base URL, headers) are injected by the factory.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any, Final, cast

from vedagraph.llm.base import LLMCapabilities, LLMProvider, LLMRequest, LLMResponse, LLMUsage
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMContentBlockedError,
    LLMContextWindowError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

# Default base URLs for known compatible providers
_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "xai": "https://api.x.ai/v1",
}

#: Ceiling on a single backoff sleep. A provider asking for minutes is not something to
#: hold an HTTP request open for.
_MAX_BACKOFF_SECONDS: Final = 30.0


def _retry_after_seconds(error: Exception) -> float | None:
    """The provider's ``Retry-After``, in seconds, if it sent one.

    OpenAI-compatible services return it on 429 and it is the only reliable signal for a
    *per-minute* quota, where exponential backoff from one second is far too short. Read
    defensively: only this header is touched, the SDK's exception shape varies by version,
    and a missing or unparseable value simply means "fall back to exponential".
    """
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    for name in ("retry-after", "Retry-After", "x-ratelimit-reset-tokens"):
        raw = headers.get(name) if hasattr(headers, "get") else None
        if not raw:
            continue
        text = str(raw).strip().lower().removesuffix("s")
        try:
            seconds = float(text)
        except ValueError:
            continue
        if seconds > 0:
            return seconds
    return None


#: Substrings that mark a 429 as a quota measured per *day* rather than per minute.
#:
#: Matched against the provider's own message because, unlike Google, OpenAI-compatible
#: services carry no machine-readable quota identifier -- the period appears only in the
#: prose. Groq writes ``on tokens per day (TPD): Limit 200000``, OpenAI writes
#: ``requests per day (RPD)``. Both spellings and their bare acronyms are listed.
_DAILY_QUOTA_MARKERS: Final[tuple[str, ...]] = (
    "per day",
    "per-day",
    "(tpd)",
    "(rpd)",
    "tokens per day",
    "requests per day",
    "daily limit",
    "daily quota",
)


def _is_exhausted_for_the_day(error: Exception) -> bool:
    """Whether a 429 names a per-*day* ceiling, which waiting will not clear today.

    The same hazard :func:`vedagraph.llm.providers.gemini._is_exhausted_for_the_day`
    guards, on the path that had no guard. It was found by this benchmark: Groq reported
    ``tokens per day (TPD): Limit 200000, Used 199681`` and the retry ladder answered by
    sleeping through the provider's own ten-minute ``Retry-After`` and asking twice more.
    A single question took 91 seconds to fail at something knowable from the first
    response, and each attempt was itself metered against the exhausted allowance.

    Read only from the message text, and conservatively: a body that does not say "day"
    is treated as a momentary spike and still retried, because misreading a transient
    limit as a daily one ends a run that would have recovered.
    """
    return any(marker in str(error).lower() for marker in _DAILY_QUOTA_MARKERS)


class OpenAICompatProvider(LLMProvider):
    """OpenAI-compatible provider adapter (OpenAI, Groq, OpenRouter, xAI, etc.)."""

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        model: str,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 4096,
        temperature: float = 0.1,
        max_retries: int = 3,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._model_name = model
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._max_retries = max_retries
        self._extra_headers = extra_headers or {}

        resolved_base = base_url or _BASE_URLS.get(provider_name)

        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMConfigurationError(
                "openai package is not installed. Run: pip install 'vedagraph[ask]'"
            ) from e

        client_kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}  # we retry
        if resolved_base:
            client_kwargs["base_url"] = resolved_base
        if extra_headers:
            client_kwargs["default_headers"] = extra_headers

        self._client = OpenAI(**client_kwargs)

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def capabilities(self) -> LLMCapabilities:
        return LLMCapabilities(
            supports_streaming=True,
            supports_json_schema=self._provider_name == "openai",
            supports_tool_calling=True,
            supports_system_message=True,
            supports_usage=True,
        )

    def _build_messages(self, request: LLMRequest) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if request.system:
            msgs.append({"role": "system", "content": request.system})
        for msg in request.messages:
            if msg.role == "system" and not request.system:
                msgs.append({"role": "system", "content": msg.content})
            elif msg.role != "system":
                msgs.append({"role": msg.role, "content": msg.content})
        return msgs

    @staticmethod
    def _backoff_seconds(error: LLMError, attempt: int) -> float:
        """How long to wait before the next attempt.

        Prefers the provider's own ``Retry-After`` over exponential backoff, because the
        two describe different things and guessing loses. Doubling from one second gives
        1 + 2 + 4 = 7 seconds across three retries, which is right for a transient 5xx and
        useless against a *per-minute* token quota: the window has not moved by then, so
        all three retries fail and the caller is told the backend is unreachable when it
        was merely busy. That is the observed failure -- one demo question failed on every
        run at the same position, ~8 seconds in, because cumulative token spend crossed
        Groq's TPM ceiling at exactly that point.

        Capped, because a provider asking for several minutes is not something to hold an
        HTTP request open for; past the cap the error surfaces and the caller decides.
        """
        hinted = getattr(error, "retry_after_seconds", None)
        if hinted:
            return min(float(hinted) + 0.5, _MAX_BACKOFF_SECONDS)
        return min(2.0**attempt, _MAX_BACKOFF_SECONDS)

    def _map_error(self, e: Exception) -> LLMError:
        try:
            from openai import (
                APITimeoutError,
                AuthenticationError,
                BadRequestError,
                InternalServerError,
                PermissionDeniedError,
                RateLimitError,
            )

            if isinstance(e, AuthenticationError | PermissionDeniedError):
                return LLMAuthenticationError(provider=self._provider_name)
            if isinstance(e, RateLimitError):
                return LLMRateLimitError(
                    provider=self._provider_name,
                    retry_after_seconds=_retry_after_seconds(e),
                )
            if isinstance(e, APITimeoutError):
                return LLMTimeoutError(provider=self._provider_name, timeout_seconds=self._timeout)
            if isinstance(e, InternalServerError):
                return LLMProviderUnavailableError(provider=self._provider_name)
            if isinstance(e, BadRequestError):
                msg = str(e).lower()
                if "context" in msg or "token" in msg or "length" in msg:
                    return LLMContextWindowError(provider=self._provider_name)
                return LLMResponseError(
                    provider=self._provider_name, detail=f"Bad request: {type(e).__name__}"
                )
        except ImportError:
            pass
        return LLMResponseError(
            provider=self._provider_name,
            detail=f"Unexpected error ({type(e).__name__}). Check logs.",
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        messages = self._build_messages(request)
        temperature = request.temperature if request.temperature is not None else self._temperature
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": request.max_output_tokens or self._max_output_tokens,
            "timeout": request.timeout_seconds or self._timeout,
        }

        start = time.monotonic()

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(**kwargs)
                latency_ms = (time.monotonic() - start) * 1000

                choice = response.choices[0] if response.choices else None
                if not choice:
                    # A 200 carrying no choice means the gateway accepted the request and
                    # the upstream model produced nothing -- capacity, an upstream
                    # timeout, or a routed provider failing behind the gateway. That is
                    # transient, and classifying it as a permanent response error ended a
                    # whole 60-question benchmark batch on the fifth question while the
                    # very next call to the same model succeeded. Raised as unavailable
                    # so the existing retry ladder gets its attempts; exhausting them
                    # still fails, just not on the first blip.
                    raise LLMProviderUnavailableError(provider=self._provider_name)

                text = choice.message.content or ""
                finish_reason = (choice.finish_reason or "stop").lower()

                if finish_reason == "content_filter":
                    raise LLMContentBlockedError(provider=self._provider_name)

                usage = LLMUsage()
                if response.usage:
                    usage = LLMUsage(
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                    )

                return LLMResponse(
                    text=text,
                    finish_reason=finish_reason,
                    provider=self._provider_name,
                    model=response.model or self._model_name,
                    usage=usage,
                    latency_ms=latency_ms,
                    provider_request_id=response.id,
                )

            except LLMError as normalised:
                # Already normalised, so it must not pass through _map_error a second
                # time -- but it must still honour `retryable`, and for a long time it
                # did not. The empty-choice branch above raises LLMProviderUnavailableError
                # *precisely* so this ladder answers it, and an unconditional re-raise
                # here silently denied it every attempt: the branch's own comment
                # described behaviour the code did not implement. A free-tier gateway
                # returning one empty 200 ended a 60-question batch on the spot, which is
                # the exact failure that branch was written to prevent. Non-retryable
                # normalised errors -- a content filter, a blown context window -- still
                # surface on the first occurrence.
                if normalised.retryable and attempt < self._max_retries:
                    time.sleep(self._backoff_seconds(normalised, attempt))
                    continue
                raise
            except Exception as e:
                mapped = self._map_error(e)
                if isinstance(mapped, LLMRateLimitError) and _is_exhausted_for_the_day(e):
                    # A daily allowance does not recover within the life of this request,
                    # and every retry is itself metered against it. Surface it now, marked
                    # so callers further out make the same distinction instead of sleeping
                    # through an allowance that will not return until tomorrow.
                    raise LLMRateLimitError(
                        provider=self._provider_name,
                        retry_after_seconds=mapped.retry_after_seconds,
                        daily_exhausted=True,
                    ) from e
                if mapped.retryable and attempt < self._max_retries:
                    time.sleep(self._backoff_seconds(mapped, attempt))
                    continue
                raise mapped from e

        raise LLMResponseError(provider=self._provider_name, detail="All retry attempts failed.")

    def stream(self, request: LLMRequest) -> Iterator[str]:
        messages = self._build_messages(request)
        temperature = request.temperature if request.temperature is not None else self._temperature
        try:
            with self._client.chat.completions.create(
                model=self._model_name,
                messages=cast("Any", messages),
                temperature=temperature,
                max_tokens=request.max_output_tokens or self._max_output_tokens,
                timeout=request.timeout_seconds or self._timeout,
                stream=True,
            ) as stream:
                for chunk in stream:
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield delta.content
        except LLMError:
            raise
        except Exception as e:
            raise self._map_error(e) from e
