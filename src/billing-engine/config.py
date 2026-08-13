# Implements: adr/ADR-034-waooaw-billing-engine.md §WBE Configuration Contract
# constitutional_basis: C-043, C-059, C-088, C-089
"""Environment-only Billing Engine configuration."""

from __future__ import annotations

from pydantic import Field, HttpUrl, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Fail-closed runtime settings loaded exclusively from the environment."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    DATABASE_URL: str = Field(min_length=1)
    REDIS_URL: str = Field(min_length=1)
    OPS_AUTH_TOKEN: str = Field(min_length=1)
    RAZORPAY_KEY_ID: str = Field(min_length=1)
    RAZORPAY_KEY_SECRET: str = Field(min_length=1)
    RAZORPAY_WEBHOOK_SECRET: str = Field(min_length=1)
    CONSTITUTIONAL_ENGINE_ADDRESS: str = Field(min_length=1)
    BILLING_CONTRACT_ID: str = Field(min_length=1)
    BILLING_DECISION_SPACE_VERSION: PositiveInt = 1
    CONSTITUTIONAL_ENGINE_TIMEOUT_SECONDS: float = Field(default=2.0, gt=0)
    WBE_INTERNAL_BASE_URL: HttpUrl = HttpUrl("http://localhost:8140")
    THREAD_CATALOG_CACHE_TTL_SECONDS: PositiveInt = 30
    TRIAL_FREE_UNITS: dict[str, dict[str, int]] = Field(default_factory=dict)
    TRIAL_DURATION_DAYS: PositiveInt = 14
    MAX_DISCOUNT_PCT: int = Field(default=0, ge=0, le=100)

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def redis_url(self) -> str:
        return self.REDIS_URL

    @property
    def thread_catalog_cache_ttl_seconds(self) -> int:
        return self.THREAD_CATALOG_CACHE_TTL_SECONDS


settings = Settings()