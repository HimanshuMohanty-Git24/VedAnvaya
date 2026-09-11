"""Anthropic Claude adapter.

Translates normalized LLMRequest → Anthropic Messages API → LLMResponse.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from vedagraph.llm.base import LLMCapabilities, LLMProvider, LLMRequest, LLMResponse, LLMUsage
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMContextWindowError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

_PROVIDER_NAME = "anthropic"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude via anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 4096,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> None:
        self._model_name = model
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._max_retries = max_retries

        try:
            import anthropic as _anthropic
        except ImportError as e:
            raise LLMConfigurationError(
                "anthropic package is not installed. Run: pip install 'vedagraph[ask]'"
            ) from e

        self._client = _anthropic.Anthropic(api_key=api_key, max_retries=0)

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
            supports_json_schema=False,
            supports_tool_calling=True,
            supports_system_message=True,
            supports_usage=True,
        )

    def _build_messages(self, request: LLMRequest) -> tuple[str | None, list[dict[str, Any]]]:
        """Returns (system_prompt, messages_list) in Anthropic format."""
        system = request.system
        msgs: list[dict[str, Any]] = []
        for msg in request.messages:
            if msg.role == "system":
                if not system:
                    system = msg.content
            else:
                role = "assistant" if msg.role == "assistant" else "user"
                msgs.append({"role": role, "content": msg.content})
        return system, msgs

    def _map_error(self, e: Exception) -> LLMError:
        try:
            import anthropic as _anthropic

            if isinstance(e, _anthropic.AuthenticationError):
                return LLMAuthenticationError(provider=_PROVIDER_NAME)
            if isinstance(e, _anthropic.RateLimitError):
                return LLMRateLimitError(provider=_PROVIDER_NAME)
            if isinstance(e, _anthropic.APITimeoutError):
                return LLMTimeoutError(provider=_PROVIDER_NAME, timeout_seconds=self._timeout)
            if isinstance(e, _anthropic.InternalServerError):
                return LLMProviderUnavailableError(provider=_PROVIDER_NAME)
            if isinstance(e, _anthropic.BadRequestError):
                msg = str(e).lower()
                if "context" in msg or "token" in msg:
                    return LLMContextWindowError(provider=_PROVIDER_NAME)
        except ImportError:
            pass
        return LLMResponseError(
            provider=_PROVIDER_NAME,
            detail=f"Unexpected error ({type(e).__name__}).",
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        system, messages = self._build_messages(request)

        temperature = request.temperature if request.temperature is not None else self._temperature
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": request.max_output_tokens or self._max_output_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        start = time.monotonic()

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.messages.create(**kwargs)
                latency_ms = (time.monotonic() - start) * 1000

                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                text = "".join(text_blocks)

                stop_reason = (response.stop_reason or "stop").lower()
                if stop_reason == "end_turn":
                    stop_reason = "stop"

                usage = LLMUsage(
                    input_tokens=getattr(response.usage, "input_tokens", None),
                    output_tokens=getattr(response.usage, "output_tokens", None),
                )

                return LLMResponse(
                    text=text,
                    finish_reason=stop_reason,
                    provider=_PROVIDER_NAME,
                    model=response.model or self._model_name,
                    usage=usage,
                    latency_ms=latency_ms,
                    provider_request_id=response.id,
                )

            except LLMError:
                raise
            except Exception as e:
                mapped = self._map_error(e)
                if mapped.retryable and attempt < self._max_retries:
                    import time as _t

                    _t.sleep(min(2**attempt, 30))
                    continue
                raise mapped from e

        raise LLMResponseError(provider=_PROVIDER_NAME, detail="All retry attempts failed.")

    def stream(self, request: LLMRequest) -> Iterator[str]:
        system, messages = self._build_messages(request)
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": request.max_output_tokens or self._max_output_tokens,
        }
        if system:
            kwargs["system"] = system
        try:
            with self._client.messages.stream(**kwargs) as stream:
                yield from stream.text_stream
        except LLMError:
            raise
        except Exception as e:
            raise self._map_error(e) from e
