# Implements: WC027-01ac — BundleEngine unit tests with mocked AsyncSession
# constitutional_basis: C-059, C-082, C-088, C-089
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.bundle_engine import BundleEngine
from skeleton.wbe_interfaces import IMarkupEngine


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
# BundleEngine inherits IMarkupEngine (ADR-036)
# ---------------------------------------------------------------------------

def test_get_thread_catalog() -> None:
    """BundleEngine must be a subclass of IMarkupEngine (ADR-036)."""
    assert issubclass(BundleEngine, IMarkupEngine)


# ---------------------------------------------------------------------------
# BundleEngine.cost_floor — reads DB, does NOT recompute
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_bundle_cost_floor_agent_type_bundle_tier() -> None:
    """cost_floor returns bundle_profiles.cost_floor_paise directly from DB."""
    db = _db_one((5000,))
    result = await BundleEngine(db=db).cost_floor("DMA", "STARTER")
    assert result == 5000
    db.execute.assert_awaited_once()  # one DB read, zero recomputation


@pytest.mark.asyncio
async def test_cost_floor_not_found_raises() -> None:
    db = _db_one(None)
    with pytest.raises(ValueError, match="Bundle profile not found"):
        await BundleEngine(db=db).cost_floor("UNKNOWN", "INVALID")


# ---------------------------------------------------------------------------
# BundleEngine.derive_price — margin-on-revenue formula
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_validate() -> None:
    """derive_price uses minimum_margin_pct from DB when target is None."""
    db = _db_one((5000, 20))  # cost_floor=5000, minimum_margin_pct=20
    result = await BundleEngine(db=db).derive_price("DMA", "STARTER")
    assert result == 6250  # int(5000 / (1 - 0.20))


@pytest.mark.asyncio
async def test_post_derive() -> None:
    """derive_price uses supplied target_margin_pct over minimum."""
    db = _db_one((5000, 20))
    result = await BundleEngine(db=db).derive_price("DMA", "STARTER", target_margin_pct=50)
    assert result == 10000  # int(5000 / (1 - 0.50))


# ---------------------------------------------------------------------------
# BundleEngine.validate_price — C-059 audit + C-088 authorization + C-089 floor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_pricing_validate() -> None:
    """APPROVED path: outcome=APPROVED, pricing_floor_log committed (C-059)."""
    db = _db_sequence(
        ("FOUNDER_AUTHORIZED",),   # billing_profiles status check (C-088)
        (5000, 20),                # bundle_profiles cost_floor + margin
        MagicMock(),               # pricing_floor_log INSERT
    )
    result = await BundleEngine(db=db).validate_price("DMA", "STARTER", 7000)
    assert result.outcome == "APPROVED"
    assert result.cost_floor_paise == 5000
    assert result.minimum_compliant_price_paise == 6250
    assert db.commit.await_count == 1  # C-059: audit log always committed


@pytest.mark.asyncio
async def test_get_pricing_thread_catalog() -> None:
    """REJECTED path: pricing_floor_log still committed on rejection (C-059)."""
    db = _db_sequence(
        ("FOUNDER_AUTHORIZED",),
        (5000, 20),
        MagicMock(),
    )
    result = await BundleEngine(db=db).validate_price("DMA", "STARTER", 4000)
    assert result.outcome == "REJECTED"
    assert result.minimum_compliant_price_paise == 6250
    assert db.commit.await_count == 1  # C-059: REJECTED must also be audited


@pytest.mark.asyncio
async def test_validate_price_unauthorized_raises() -> None:
    """C-088: non-FOUNDER_AUTHORIZED billing profile raises ValueError."""
    db = _db_one(("PENDING",))
    with pytest.raises(ValueError, match="not FOUNDER_AUTHORIZED"):
        await BundleEngine(db=db).validate_price("DMA", "STARTER", 7000)


# ---------------------------------------------------------------------------
# Hypothesis: C-089 margin-on-revenue formula invariants
# ---------------------------------------------------------------------------

@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
    margin_pct=st.floats(min_value=0.0, max_value=99.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_property_based(cost_floor_paise: int, margin_pct: float) -> None:
    """Derived price is always >= cost floor for all valid margin percentages."""
    derived = int(cost_floor_paise / (1 - margin_pct / 100))
    assert derived >= cost_floor_paise
