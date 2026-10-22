"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_PRODUCTION_SECRETS = {
    "replace_me",
    "local-compose-change-me",
    "change-me",
    "changeme",
    "secret",
    "development-secret",
}


class Settings(BaseSettings):
    """Runtime configuration with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Industry Pain Radar"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_secret_key: str = "replace_me"
    app_timezone: str = "Asia/Shanghai"
    app_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "127.0.0.1,localhost,testserver,api"
    task_execution_mode: str = "inline"

    database_url: str = "sqlite+pysqlite:///./.local/industry_pain_radar.db"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    search_provider_default: str = "mock"
    llm_provider: str = "mock"

    default_job_max_queries: int = Field(default=10, ge=1, le=20)
    default_job_max_results_per_query: int = Field(default=3, ge=1, le=30)
    default_job_max_sources: int = Field(default=60, ge=1, le=200)
    default_job_max_cost: float = Field(default=5.0, ge=0, le=100)
    default_retention_days: int = Field(default=90, ge=1, le=3_650)

    max_page_bytes: int = Field(default=204_800, ge=1_024)
    max_redirects: int = Field(default=5, ge=0, le=10)
    fetch_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    connect_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    allowed_fetch_ports: str = "80,443"
    store_full_page_text: bool = False

    github_token: str = ""
    tavily_api_key: str = ""
    brave_search_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_enabled: bool = False
    product_hunt_enabled: bool = False

    @model_validator(mode="after")
    def reject_unsafe_production_secret(self) -> Settings:
        if self.app_env.lower() != "production":
            return self
        secret = self.app_secret_key.strip()
        if len(secret) < 32 or secret.lower() in WEAK_PRODUCTION_SECRETS:
            raise ValueError(
                "APP_SECRET_KEY must be a non-placeholder value of at least 32 characters "
                "in production"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized CORS origins without permitting wildcard credentials."""

        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def allowed_ports(self) -> frozenset[int]:
        """Return the explicit outbound port allowlist."""

        ports = {int(port.strip()) for port in self.allowed_fetch_ports.split(",") if port.strip()}
        return frozenset(ports)

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url.strip())

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def ensure_local_paths(self) -> None:
        """Create parent directories for file-backed SQLite development databases."""

        prefix = "sqlite+pysqlite:///"
        if self.database_url.startswith(prefix):
            raw_path = self.database_url.removeprefix(prefix)
            if raw_path and raw_path != ":memory:":
                Path(raw_path).resolve().parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings for production entrypoints."""

    return Settings()
