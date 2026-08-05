# Implements: work-contracts/WC-029-*.md §WC029-01ab:models.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# SQLAlchemy ORM base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# ORM model: institutional.provider_accounts
# ---------------------------------------------------------------------------

class ProviderAccount(Base):
    """
    Maps institutional.provider_accounts.
    Tracks per-provider wallet balance and FA template reference.
    Constitutional: C-077 (dev budget ceiling enforcement via runway alerts).
    """

    __tablename__ = "provider_accounts"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "institutional"}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    low_balance_threshold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    founder_action_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationship -- not eagerly loaded; used by service when needed
    cost_ledger_entries: Mapped[list[PlatformCostLedgerEntry]] = relationship(
        "PlatformCostLedgerEntry",
        back_populates="provider_account",
        lazy="select",
    )


# ---------------------------------------------------------------------------
# ORM model: institutional.platform_cost_ledger
# ---------------------------------------------------------------------------

class PlatformCostLedgerEntry(Base):
    """
    Maps institutional.platform_cost_ledger.
    Append-only per C-007 -- no UPDATE/DELETE ever issued against this table.
    FK: provider_account_id UUID references institutional.provider_accounts(id).
    """

    __tablename__ = "platform_cost_ledger"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "institutional"}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    provider_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("institutional.provider_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    thread_type: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_cost_inr_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fx_rate_inr_per_usd: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    provider_account: Mapped[ProviderAccount] = relationship(
        "ProviderAccount",
        back_populates="cost_ledger_entries",
        lazy="select",
    )


# ---------------------------------------------------------------------------
# Pydantic response model: ProviderRunwayStatus
# Computed fields -- NOT DB-mapped.  Sourced from wbe_interfaces.py dataclass
# but expressed here as a Pydantic model for FastAPI serialisation.
# ---------------------------------------------------------------------------

class ProviderRunwayStatus(BaseModel):
    """
    One entry in GET /platform/procurement/status response.
    ADR-029 providers.  Mirrors skeleton.wbe_interfaces.ProviderRunwayStatus
    as a Pydantic model for FastAPI JSON serialisation.
    """

    provider_name: str
    balance_paise: int
    daily_burn_rate_paise: float
    days_remaining: float
    last_fa_level_triggered: str | None = Field(default=None)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Pydantic request model: CostRecordRequest
# ---------------------------------------------------------------------------

class CostRecordRequest(BaseModel):
    """
    Request body for POST /platform/procurement/record-cost.
    provider: short name matching provider_accounts.provider_name.
    cost_paise: raw cost already converted to INR paise by caller.
    fx_rate_inr_per_usd: snapshot FX rate used for the conversion.
    """

    provider: str = Field(..., min_length=1, max_length=128)
    thread_type: str = Field(..., min_length=1, max_length=128)
    customer_id: UUID
    agent_type: str = Field(..., min_length=1, max_length=128)
    cost_paise: int = Field(..., ge=0)
    fx_rate_inr_per_usd: float = Field(..., gt=0.0)

    model_config = {"frozen": True}