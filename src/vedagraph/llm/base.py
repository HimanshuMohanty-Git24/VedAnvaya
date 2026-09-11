"""Provider protocol and normalized request/response models.

Application code works with LLMRequest and LLMResponse only.
No provider-specific type ever crosses this boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


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
