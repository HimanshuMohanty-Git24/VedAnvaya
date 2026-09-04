"""Environment-backed runtime settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VEDAGRAPH_", extra="ignore")

    contact_email: str | None = None
    user_agent: str = "VedaGraph/0.1 (+https://github.com/vedagraph/vedagraph)"
    data_dir: Path = Path("data")
    requests_per_second: float = Field(default=1.0, gt=0, le=10)
    max_concurrency: int = Field(default=2, ge=1, le=8)
    connect_timeout_seconds: float = Field(default=10.0, gt=0)
    read_timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def effective_user_agent(self) -> str:
        if self.contact_email:
            return f"{self.user_agent} contact={self.contact_email}"
        return self.user_agent


def get_settings() -> Settings:
    return Settings()
