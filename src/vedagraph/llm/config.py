"""LLM configuration — read from env, never hardcoded provider names in app layers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    vedagraph_llm_provider: str = "gemini"
    vedagraph_llm_model: str = "gemini-2.0-flash"
    vedagraph_llm_api_key: SecretStr | None = None
    vedagraph_llm_base_url: str | None = None
    vedagraph_llm_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    vedagraph_llm_max_output_tokens: int = Field(default=4096, gt=0, le=32768)
    vedagraph_llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    vedagraph_llm_max_retries: int = Field(default=3, ge=0, le=10)
    vedagraph_llm_stream: bool = False

    # Backward-compatible fallback keys (used only if vedagraph_llm_api_key is absent)
    google_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    def resolved_api_key(self) -> str | None:
        """Return the API key for the configured provider, checking fallbacks."""
        if self.vedagraph_llm_api_key is not None:
            return self.vedagraph_llm_api_key.get_secret_value()
        provider = self.vedagraph_llm_provider.lower()
        if provider == "gemini":
            fallback = self.gemini_api_key or self.google_api_key
            return fallback.get_secret_value() if fallback else None
        if provider == "openai":
            return self.openai_api_key.get_secret_value() if self.openai_api_key else None
        if provider == "anthropic":
            return self.anthropic_api_key.get_secret_value() if self.anthropic_api_key else None
        # Groq/OpenRouter/xAI use openai_api_key as fallback
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None

    def safe_summary(self) -> dict[str, Any]:
        """Provider config without secret values — safe for logs and /ready."""
        return {
            "provider": self.vedagraph_llm_provider,
            "model": self.vedagraph_llm_model,
            "timeout_seconds": self.vedagraph_llm_timeout_seconds,
            "max_output_tokens": self.vedagraph_llm_max_output_tokens,
            "temperature": self.vedagraph_llm_temperature,
            "stream": self.vedagraph_llm_stream,
            "api_key_present": self.resolved_api_key() is not None,
        }


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()
