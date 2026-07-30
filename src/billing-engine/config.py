# Implements: architecture/reference/billing/wbe-component-spec.md §1 Configuration
# constitutional_basis: C-059, ADR-014 (Secret Management), ADR-034

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    port: int = 8140

    database_url: str = (
        "postgresql+asyncpg://wbe_app:changeme@postgres:5432/waooaw"
    )
    redis_url: str = "redis://redis:6379/0"
    thread_catalog_cache_ttl_seconds: int = 30

    otlp_endpoint: str = "http://jaeger:4317"

    # ADR-014: secrets from Key Vault in production; env vars in dev
    wbe_db_password: str = "changeme"


settings = Settings()
