"""Google Gemini adapter, over the Google AI Studio REST API.

**Why HTTP and not a vendor SDK.** ``google-generativeai`` is end-of-life -- it emits a
deprecation warning on import and Google directs users to ``google-genai`` -- and the
replacement is a second heavyweight dependency (it pulls protobuf, google-auth and
websockets) for an interface this adapter uses three fields of. ``httpx`` is already a core
dependency of this project. The ``v1beta`` generateContent contract is stable and public,
so the trade is one small translation function here against a large transitive dependency
tree and a migration every time the vendor re-cuts its client.

**The thinking budget is load-bearing, not a tuning knob.** Gemini 2.5 and later spend
output tokens on internal reasoning before emitting any text, and that spend counts against
``maxOutputTokens``. A request with a small budget therefore returns
``finishReason: MAX_TOKENS`` and *zero* candidate parts -- not truncated prose, no prose at
all. That is what a naive port of this adapter produces against ``gemini-flash-latest``,
and it fails as an unreadable-response error rather than as anything that names the cause.
:data:`_THINKING_BUDGET_DISABLED` switches reasoning off so the whole budget reaches the
answer; models that do not accept the field ignore it.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any, Final

import httpx

from vedagraph.llm.base import (
    LLMCapabilities,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    normalise_finish_reason,
)
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMContentBlockedError,
    LLMContextWindowError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

_PROVIDER_NAME: Final = "gemini"

_DEFAULT_BASE_URL: Final = "https://generativelanguage.googleapis.com/v1beta"

#: Turns internal reasoning off. See the module docstring: with reasoning on, a modest
#: ``maxOutputTokens`` is consumed before the first visible token and the response carries
#: no text at all.
_THINKING_BUDGET_DISABLED: Final = 0

#: Gemini's ``finishReason`` vocabulary mapped onto the normalised one. ``MAX_TOKENS`` is
#: reported as ``length`` rather than raised, so a caller can see a truncated answer for
#: what it is; the no-parts case is what raises.
_FINISH_REASONS: Final[dict[str, str]] = {
    "STOP": "stop",
    "MAX_TOKENS": "length",
    "SAFETY": "content_filter",
    "RECITATION": "content_filter",
    "PROHIBITED_CONTENT": "content_filter",
    "BLOCKLIST": "content_filter",
    "SPII": "content_filter",
    "MALFORMED_FUNCTION_CALL": "error",
    "OTHER": "error",
}

#: Statuses worth another attempt. 429 is rate limiting; the 5xx family is the vendor
#: having a bad minute. Everything else -- 400, 401, 403, 404 -- is this deployment being
#: wrong and will be wrong again on retry.
#:
#: 429 is conditional -- see :func:`_is_exhausted_for_the_day`.
_RETRYABLE_STATUS: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})

#: Marks a quota measured per day rather than per minute, in Google's ``quotaId``.
_DAILY_QUOTA_MARKER: Final = "perday"


def _is_exhausted_for_the_day(body: object) -> bool:
    """Whether a 429 is a per-*day* quota, which no amount of waiting will clear today.

    Retrying the wrong kind of 429 is not merely futile, it is *harmful*: every retry is
    itself a metered request, so a burst of retries against an exhausted daily allowance
    spends the next day's headroom too. That is not hypothetical -- it is how the free
    tier's 20-requests-per-day allowance was consumed during this build, three units at a
    time, by a retry loop treating a daily ceiling as a momentary spike.

    Only ``quotaId`` is inspected. The rest of Google's error payload echoes request
    metadata, so nothing from it is read, logged or propagated.
    """
    if not isinstance(body, dict):
        return False
    details = (body.get("error") or {}).get("details") or []
    if not isinstance(details, list):
        return False
    for detail in details:
        if not isinstance(detail, dict):
            continue
        for violation in detail.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            quota_id = str(violation.get("quotaId", "")).lower()
            if _DAILY_QUOTA_MARKER in quota_id:
                return True
    return False


#: Ceiling on total time spent retrying, across all attempts. Retry *count* alone does
#: not bound latency: Google's newest aliases return 503 "high demand" after holding the
#: connection for 16 seconds, so three retries of a request that fails slowly spent 64
#: seconds before reporting a failure that was knowable at the first response. An HTTP
#: caller behind a timeout would already have given up. The budget is checked before each
#: further attempt, so a fast-failing provider still gets all its retries.
_RETRY_BUDGET_SECONDS: Final = 25.0


class GeminiProvider(LLMProvider):
    """Google Gemini via the Google AI Studio REST API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 4096,
        temperature: float = 0.1,
        max_retries: int = 3,
        base_url: str | None = None,
    ) -> None:
        self._model_name = model
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._max_retries = max_retries
        self._base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        # Held on the instance and never logged or included in a repr. The header is set
        # per client rather than per request so no call site can forget it.
        self._client = httpx.Client(
            headers={"x-goog-api-key": api_key, "content-type": "application/json"},
            timeout=timeout_seconds,
        )

    @property
    def name(self) -> str:
        return _PROVIDER_NAME

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def capabilities(self) -> LLMCapabilities:
        return LLMCapabilities(
            supports_streaming=True,
            supports_json_schema=True,
            supports_tool_calling=True,
            supports_system_message=True,
            supports_usage=True,
        )

    # -- request translation ------------------------------------------------

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        """Normalised request to Gemini's generateContent body."""
        contents: list[dict[str, Any]] = []
        system_parts: list[str] = []
        if request.system:
            system_parts.append(request.system)

        for message in request.messages:
            if message.role == "system":
                # Gemini carries system text in its own top-level field rather than as a
                # turn, so a system message in the list is hoisted instead of dropped.
                system_parts.append(message.content)
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        generation_config: dict[str, Any] = {
            "temperature": (
                request.temperature if request.temperature is not None else self._temperature
            ),
            "maxOutputTokens": request.max_output_tokens or self._max_output_tokens,
            "thinkingConfig": {"thinkingBudget": _THINKING_BUDGET_DISABLED},
        }
        if request.json_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = request.json_schema

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": text} for text in system_parts]}
        return payload

    # -- response translation -----------------------------------------------

    def _error_for_status(self, status_code: int) -> LLMError:
        """An HTTP status as a normalised error. The vendor's body is never quoted.

        Google's error payloads echo request metadata and, on some auth failures, the
        rejected key itself. Mapping on the status alone means no vendor text can reach a
        log line or an exception string.
        """
        if status_code in (401, 403):
            return LLMAuthenticationError(provider=_PROVIDER_NAME)
        if status_code == 429:
            return LLMRateLimitError(provider=_PROVIDER_NAME)
        if status_code == 400:
            return LLMResponseError(
                provider=_PROVIDER_NAME,
                detail="Gemini rejected the request as malformed. The configured model "
                "name may not exist, or the prompt may exceed the model's limits.",
            )
        if status_code == 404:
            return LLMResponseError(
                provider=_PROVIDER_NAME,
                detail=f"Gemini has no model named '{self._model_name}'. "
                "Check VEDAGRAPH_LLM_MODEL.",
            )
        if status_code == 413:
            return LLMContextWindowError(provider=_PROVIDER_NAME)
        if status_code >= 500:
            return LLMProviderUnavailableError(provider=_PROVIDER_NAME)
        return LLMResponseError(
            provider=_PROVIDER_NAME,
            detail=f"Gemini returned an unexpected HTTP {status_code}.",
        )

    def _read_response(self, body: dict[str, Any], latency_ms: float) -> LLMResponse:
        # A prompt refused before generation carries no candidates at all, only
        # promptFeedback. Reported as blocked rather than as an empty answer.
        feedback = body.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            raise LLMContentBlockedError(provider=_PROVIDER_NAME)

        candidates = body.get("candidates") or []
        if not candidates:
            raise LLMResponseError(
                provider=_PROVIDER_NAME,
                detail="Gemini returned no candidates for this request.",
            )

        candidate = candidates[0]
        raw_finish = str(candidate.get("finishReason") or "STOP").upper()
        finish_reason = normalise_finish_reason(_FINISH_REASONS.get(raw_finish, raw_finish))

        if finish_reason == "content_filter":
            raise LLMContentBlockedError(provider=_PROVIDER_NAME)

        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)

        if not text:
            # The failure mode the module docstring describes. Named precisely, because
            # "empty response" sends a reader looking at the prompt instead of the budget.
            if raw_finish == "MAX_TOKENS":
                raise LLMResponseError(
                    provider=_PROVIDER_NAME,
                    detail="Gemini consumed the entire output budget before emitting "
                    "text. Raise VEDAGRAPH_LLM_MAX_OUTPUT_TOKENS.",
                )
            raise LLMResponseError(
                provider=_PROVIDER_NAME,
                detail=f"Gemini returned no text (finishReason={raw_finish}).",
            )

        usage_meta = body.get("usageMetadata") or {}
        usage = LLMUsage(
            input_tokens=usage_meta.get("promptTokenCount"),
            output_tokens=usage_meta.get("candidatesTokenCount"),
        )

        return LLMResponse(
            text=text,
            finish_reason=finish_reason,
            provider=_PROVIDER_NAME,
            model=body.get("modelVersion") or self._model_name,
            usage=usage,
            latency_ms=latency_ms,
            provider_request_id=body.get("responseId"),
        )

    # -- the protocol -------------------------------------------------------

    def generate(self, request: LLMRequest) -> LLMResponse:
        url = f"{self._base_url}/models/{self._model_name}:generateContent"
        payload = self._payload(request)
        timeout = request.timeout_seconds or self._timeout
        start = time.monotonic()

        def may_retry(attempt: int) -> bool:
            """Whether another attempt is allowed by both count and elapsed budget."""
            if attempt >= self._max_retries:
                return False
            return (time.monotonic() - start) < _RETRY_BUDGET_SECONDS

        for attempt in range(self._max_retries + 1):
            try:
                http_response = self._client.post(url, json=payload, timeout=timeout)
            except httpx.TimeoutException as exc:
                if may_retry(attempt):
                    time.sleep(min(2**attempt, 8))
                    continue
                raise LLMTimeoutError(provider=_PROVIDER_NAME, timeout_seconds=timeout) from exc
            except httpx.HTTPError as exc:
                # Transport-level: DNS, connection reset, TLS. Retryable, and the
                # exception text can carry the full URL, so it is not propagated.
                if may_retry(attempt):
                    time.sleep(min(2**attempt, 8))
                    continue
                raise LLMProviderUnavailableError(provider=_PROVIDER_NAME) from exc

            if http_response.status_code != 200:
                error = self._error_for_status(http_response.status_code)
                retryable = http_response.status_code in _RETRYABLE_STATUS
                if http_response.status_code == 429:
                    # A daily allowance will not recover today, and each retry is itself
                    # a metered request. Fail immediately rather than spending three more
                    # units proving it.
                    try:
                        quota_body = http_response.json()
                    except ValueError:
                        quota_body = None
                    if _is_exhausted_for_the_day(quota_body):
                        raise LLMRateLimitError(
                            provider=_PROVIDER_NAME,
                            retry_after_seconds=None,
                            daily_exhausted=True,
                        ) from None
                if retryable and may_retry(attempt):
                    time.sleep(min(2**attempt, 8))
                    continue
                raise error

            try:
                body = http_response.json()
            except ValueError as exc:
                raise LLMResponseError(
                    provider=_PROVIDER_NAME, detail="Gemini returned a non-JSON body."
                ) from exc

            return self._read_response(body, (time.monotonic() - start) * 1000)

        raise LLMProviderUnavailableError(provider=_PROVIDER_NAME)

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream text chunks over server-sent events.

        Deliberately not retried. A retry after bytes have been yielded would replay the
        answer from its start, and the consumer has already rendered the first half.
        """
        import json

        url = f"{self._base_url}/models/{self._model_name}:streamGenerateContent"
        payload = self._payload(request)
        timeout = request.timeout_seconds or self._timeout

        try:
            with self._client.stream(
                "POST", url, json=payload, params={"alt": "sse"}, timeout=timeout
            ) as http_response:
                if http_response.status_code != 200:
                    http_response.read()
                    raise self._error_for_status(http_response.status_code)

                for line in http_response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[len("data:") :].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    try:
                        event = json.loads(chunk)
                    except ValueError:
                        continue
                    for candidate in event.get("candidates") or []:
                        parts = (candidate.get("content") or {}).get("parts") or []
                        for part in parts:
                            text = part.get("text")
                            if text:
                                yield text
        except LLMError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(provider=_PROVIDER_NAME, timeout_seconds=timeout) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderUnavailableError(provider=_PROVIDER_NAME) from exc

    def close(self) -> None:
        self._client.close()
