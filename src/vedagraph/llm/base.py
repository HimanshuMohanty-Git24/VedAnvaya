"""Provider protocol and normalized request/response models.

Application code works with LLMRequest and LLMResponse only.
No provider-specific type ever crosses this boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True)
class LLMCapabilities:
    supports_streaming: bool = False
    supports_json_schema: bool = False
    supports_tool_calling: bool = False
    supports_system_message: bool = True
    supports_usage: bool = True


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    system: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    stream: bool = False
    json_schema: dict[str, Any] | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


#: Canonical finish reasons. Every adapter normalises to these four before returning, so
#: no caller has to know which vendor answered.
FINISH_STOP: Final = "stop"
FINISH_LENGTH: Final = "length"
FINISH_ERROR: Final = "error"
FINISH_CONTENT_FILTER: Final = "content_filter"

#: Vendor spellings of "I ran out of output budget". Anthropic says ``max_tokens``,
#: Gemini says ``MAX_TOKENS``, the OpenAI-compatible family says ``length``, and gateways
#: in front of them invent their own. They mean one thing and the product needs one flag:
#: an answer that stopped mid-sentence must not be presented as a finished one. Before
#: this table, four answers in a 60-question benchmark hit the cap and every one of them
#: was returned looking complete, because only two of the three adapters happened to emit
#: the spelling the rest of the code tested for.
_FINISH_ALIASES: Final[dict[str, str]] = {
    "end_turn": FINISH_STOP,
    "stop": FINISH_STOP,
    "stop_sequence": FINISH_STOP,
    "complete": FINISH_STOP,
    "completed": FINISH_STOP,
    "eos": FINISH_STOP,
    "length": FINISH_LENGTH,
    "max_tokens": FINISH_LENGTH,
    "maxtokens": FINISH_LENGTH,
    "max_output_tokens": FINISH_LENGTH,
    "model_length": FINISH_LENGTH,
    "token_limit": FINISH_LENGTH,
    "safety": FINISH_CONTENT_FILTER,
    "recitation": FINISH_CONTENT_FILTER,
    "content_filter": FINISH_CONTENT_FILTER,
}


def normalise_finish_reason(raw: str | None) -> str:
    """A vendor's stop reason as one of the four canonical values.

    An unrecognised value is passed through lower-cased rather than forced to ``error``.
    A new vendor string is not a failed generation, and silently recording it as one
    would turn an unknown into a fault report.
    """
    if not raw:
        return FINISH_STOP
    key = raw.strip().lower()
    return _FINISH_ALIASES.get(key, key)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    finish_reason: str  # "stop", "length", "error", "content_filter"
    provider: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    provider_request_id: str | None = None

    @property
    def provider_info(self) -> dict[str, str]:
        return {"provider": self.provider, "model": self.model}

    @property
    def generation_truncated(self) -> bool:
        """The model stopped because it ran out of output budget, not because it finished.

        Derived rather than stored so it cannot drift from ``finish_reason``: two fields
        saying different things about the same generation is how a truncated answer gets
        presented as a complete one.
        """
        return self.finish_reason == FINISH_LENGTH


class LLMProvider(ABC):
    """Protocol every provider adapter must satisfy.

    Implement generate() at minimum. stream() falls back to generate() unless overridden.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    def capabilities(self) -> LLMCapabilities:
        return LLMCapabilities()

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse: ...

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream text chunks. Default falls back to generate() as one chunk."""
        response = self.generate(request)
        yield response.text
