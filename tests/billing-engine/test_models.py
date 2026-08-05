# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.bundle_engine import BundleEngine
from skeleton.wbe_interfaces import IMarkupEngine
from procurement.models import (
    Base,
    CostRecordRequest,
    PlatformCostLedgerEntry,
    ProviderAccount,
    ProviderRunwayStatus,
)


def _db_one(row: tuple | None) -> AsyncMock:
    """Return a mock AsyncSession whose execute().fetchone() returns row."""
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.fetchone.return_value = row
    db.execute = AsyncMock(return_value=result)
    return db


def _db_sequence(*rows: tuple | None) -> AsyncMock:
    """Return a mock AsyncSession with sequential fetchone returns."""
    db = AsyncMock(spec=AsyncSession)
    results = [MagicMock() for _ in rows]
    for r, row in zip(results, rows, strict=True):
        r.fetchone.return_value = row
    db.execute = AsyncMock(side_effect=results)
    return db


# ---------------------------------------------------------------------------
# ORM Model Tests: ProviderAccount
# ---------------------------------------------------------------------------


def test_provider_account_table_schema() -> None:
    """ProviderAccount maps institutional.provider_accounts correctly."""
    assert ProviderAccount.__tablename__ == "provider_accounts"
    assert ProviderAccount.__table_args__ == {"schema": "institutional"}


def test_provider_account_columns_exist() -> None:
    """ProviderAccount has required columns per WC-029 spec."""
    mapper = ProviderAccount.__mapper__
    col_names = {c.name for c in mapper.columns}
    required = {
        "id",
        "provider_name",
        "display_name",
        "currency",
        "balance_paise",
        "low_balance_threshold_days",
        "founder_action_template",
    }
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


def test_provider_account_defaults() -> None:
    """ProviderAccount currency defaults to INR; balance to 0; threshold to 30 days."""
    from sqlalchemy import inspect

    mapper = inspect(ProviderAccount)
    currency_col = mapper.get_property("currency").columns[0]
    balance_col = mapper.get_property("balance_paise").columns[0]
    threshold_col = mapper.get_property("low_balance_threshold_days").columns[0]

    assert currency_col.default.arg == "INR"
    assert balance_col.default.arg == 0
    assert threshold_col.default.arg == 30


# ---------------------------------------------------------------------------
# ORM Model Tests: PlatformCostLedgerEntry
# ---------------------------------------------------------------------------


def test_platform_cost_ledger_entry_table_schema() -> None:
    """PlatformCostLedgerEntry maps institutional.platform_cost_ledger correctly."""
    assert PlatformCostLedgerEntry.__tablename__ == "platform_cost_ledger"
    assert PlatformCostLedgerEntry.__table_args__ == {"schema": "institutional"}


def test_platform_cost_ledger_entry_columns_exist() -> None:
    """PlatformCostLedgerEntry has required columns per WC-029 spec."""
    mapper = PlatformCostLedgerEntry.__mapper__
    col_names = {c.name for c in mapper.columns}
    required = {
        "id",
        "provider_account_id",
        "thread_type",
        "customer_id",
        "agent_type",
        "raw_cost_inr_paise",
        "fx_rate_inr_per_usd",
        "recorded_at",
    }
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


def test_platform_cost_ledger_entry_fk_constraint() -> None:
    """PlatformCostLedgerEntry.provider_account_id FK references provider_accounts(id) with RESTRICT."""
    mapper = PlatformCostLedgerEntry.__mapper__
    fk_col = mapper.get_property("provider_account_id").columns[0]
    assert len(fk_col.foreign_keys) == 1
    fk = list(fk_col.foreign_keys)[0]
    assert "provider_accounts" in str(fk.column)
    assert fk.ondelete == "RESTRICT"


def test_platform_cost_ledger_entry_recorded_at_default() -> None:
    """PlatformCostLedgerEntry.recorded_at defaults to UTC now."""
    from sqlalchemy import inspect

    mapper = inspect(PlatformCostLedgerEntry)
    recorded_at_col = mapper.get_property("recorded_at").columns[0]
    # Default is a callable that returns datetime.now(timezone.utc)
    assert recorded_at_col.default is not None


# ---------------------------------------------------------------------------
# Pydantic Model Tests: ProviderRunwayStatus
# ---------------------------------------------------------------------------


def test_provider_runway_status_basic_construction() -> None:
    """ProviderRunwayStatus accepts required fields."""
    status = ProviderRunwayStatus(
        provider_name="anthropic",
        balance_paise=100_000,
        daily_burn_rate_paise=1000.0,
        days_remaining=100.0,
        last_fa_level_triggered=None,
    )
    assert status.provider_name == "anthropic"
    assert status.balance_paise == 100_000
    assert status.daily_burn_rate_paise == 1000.0
    assert status.days_remaining == 100.0
    assert status.last_fa_level_triggered is None


def test_provider_runway_status_with_fa_level() -> None:
    """ProviderRunwayStatus can include last_fa_level_triggered."""
    status = ProviderRunwayStatus(
        provider_name="google",
        balance_paise=50_000,
        daily_burn_rate_paise=500.0,
        days_remaining=100.0,
        last_fa_level_triggered="P2",
    )
    assert status.last_fa_level_triggered == "P2"


def test_provider_runway_status_infinite_days() -> None:
    """ProviderRunwayStatus can represent infinite days_remaining."""
    status = ProviderRunwayStatus(
        provider_name="sarvam",
        balance_paise=200_000,
        daily_burn_rate_paise=0.0,
        days_remaining=float("inf"),
        last_fa_level_triggered=None,
    )
    assert status.days_remaining == float("inf")


def test_provider_runway_status_json_serialization() -> None:
    """ProviderRunwayStatus serializes to JSON (for FastAPI response)."""
    status = ProviderRunwayStatus(
        provider_name="ollama",
        balance_paise=75_000,
        daily_burn_rate_paise=750.0,
        days_remaining=100.0,
        last_fa_level_triggered="P1",
    )
    json_data = status.model_dump()
    assert json_data["provider_name"] == "ollama"
    assert json_data["balance_paise"] == 75_000


# ---------------------------------------------------------------------------
# Pydantic Model Tests: CostRecordRequest
# ---------------------------------------------------------------------------


def test_cost_record_request_basic_construction() -> None:
    """CostRecordRequest accepts all required fields."""
    customer_id = uuid4()
    req = CostRecordRequest(
        provider="anthropic",
        thread_type="message",
        customer_id=customer_id,
        agent_type="DMA",
        cost_paise=500,
        fx_rate_inr_per_usd=83.5,
    )
    assert req.provider == "anthropic"
    assert req.thread_type == "message"
    assert req.customer_id == customer_id
    assert req.agent_type == "DMA"
    assert req.cost_paise == 500
    assert req.fx_rate_inr_per_usd == 83.5


def test_cost_record_request_json_parsing() -> None:
    """CostRecordRequest parses from JSON (FastAPI request body)."""
    customer_id = uuid4()
    data = {
        "provider": "google",
        "thread_type": "completion",
        "customer_id": str(customer_id),
        "agent_type": "TVM",
        "cost_paise": 1000,
        "fx_rate_inr_per_usd": 83.0,
    }
    req = CostRecordRequest(**data)
    assert req.provider == "google"
    assert req.customer_id == customer_id


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    provider=st.sampled_from(["anthropic", "google", "sarvam", "azure", "ollama"]),
    thread_type=st.sampled_from(["message", "completion"]),
    agent_type=st.sampled_from(["DMA", "TVM"]),
    cost_paise=st.integers(min_value=1, max_value=1_000_000),
    fx_rate=st.floats(min_value=80.0, max_value=90.0, allow_nan=False, allow_infinity=False),
)
def test_cost_record_request_property_roundtrip(
    provider: str,
    thread_type: str,
    agent_type: str,
    cost_paise: int,
    fx_rate: float,
) -> None:
    """CostRecordRequest survives roundtrip: object -> dict -> object."""
    customer_id = uuid4()
    req1 = CostRecordRequest(
        provider=provider,
        thread_type=thread_type,
        customer_id=customer_id,
        agent_type=agent_type,
        cost_paise=cost_paise,
        fx_rate_inr_per_usd=fx_rate,
    )
    req2 = CostRecordRequest(**req1.model_dump())
    assert req2.provider == req1.provider
    assert req2.thread_type == req1.thread_type
    assert req2.customer_id == req1.customer_id
    assert req2.agent_type == req1.agent_type
    assert req2.cost_paise == req1.cost_paise
    assert req2.fx_rate_inr_per_usd == req1.fx_rate_inr_per_usd


# ---------------------------------------------------------------------------
# Base Class Tests
# ---------------------------------------------------------------------------


def test_base_is_declarative_base() -> None:
    """Base is a valid SQLAlchemy DeclarativeBase."""
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")


def test_provider_account_inherits_from_base() -> None:
    """ProviderAccount is registered with Base registry."""
    assert ProviderAccount in Base.registry.mappers[0].class_


def test_platform_cost_ledger_entry_inherits_from_base() -> None:
    """PlatformCostLedgerEntry is registered with Base registry."""
    assert issubclass(PlatformCostLedgerEntry, Base)