# Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
# Constitutional basis: C-043, C-059, C-088, C-089
"""Environment-only Billing Engine configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Fail-closed runtime settings loaded exclusively from the environment."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    DATABASE_URL: str = Field(min_length=1)
    REDIS_URL: str = Field(min_length=1)
    OPS_AUTH_TOKEN: str = Field(min_length=1)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_READINESS_STATE: Literal[
        "NOT_CONFIGURED", "CONFIGURED_UNVERIFIED", "READY_TEST", "READY_LIVE", "DEGRADED", "REVOKED"
    ] = "NOT_CONFIGURED"
    RAZORPAY_MERCHANT_DISPLAY_NAME: str = ""
    RAZORPAY_ENABLED_METHOD_FAMILIES: str = ""
    RAZORPAY_CHECKOUT_TTL_SECONDS: PositiveInt = 900
    WAOOAW_ENVIRONMENT: Literal["demo", "uat", "production"] = "production"
    DEMO_PROMOTION_ENABLED: bool = False
    DEMO_PROMOTION_VERSION: str = ""
    DEMO_RENEWAL_CONSEQUENCE: str = "Standard paid renewal terms apply after the Demo period."
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

    @property
    def razorpay_enabled_method_families(self) -> tuple[str, ...]:
        return tuple(
            method.strip().upper()
            for method in self.RAZORPAY_ENABLED_METHOD_FAMILIES.split(",")
            if method.strip()
        )


settings = Settings()