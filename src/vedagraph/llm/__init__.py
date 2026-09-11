"""Provider-agnostic LLM layer for Ask VedaGraph.

Switch providers by changing VEDAGRAPH_LLM_PROVIDER in .env — no code changes.
"""

from vedagraph.llm.base import LLMCapabilities, LLMProvider, LLMRequest, LLMResponse
from vedagraph.llm.config import LLMSettings, get_llm_settings
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
from vedagraph.llm.factory import get_llm_provider

__all__ = [
    "LLMAuthenticationError",
    "LLMCapabilities",
    "LLMConfigurationError",
    "LLMContentBlockedError",
    "LLMContextWindowError",
    "LLMError",
    "LLMProvider",
    "LLMProviderUnavailableError",
    "LLMRateLimitError",
    "LLMRequest",
    "LLMResponse",
    "LLMResponseError",
    "LLMSettings",
    "LLMTimeoutError",
    "get_llm_provider",
    "get_llm_settings",
]
