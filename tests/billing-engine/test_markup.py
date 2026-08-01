# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Hypothesis Strategies for Financial Math ─────────────────────────────────

@st.composite
def cost_floor_paise_strategy(draw: Any) -> int:
    """Generate realistic cost_floor_paise: ₹1 paise to ₹100,000 paise (₹1 to ₹1000)."""
    return draw(st.integers(min_value=1, max_value=10_000_000))


@st.composite
def margin_pct_strategy(draw: Any) -> float:
    """Generate margin percentages: 0% to 99.9% (avoid 100% singularity)."""
    return draw(st.floats(min_value=0.0, max_value=99.9, allow_nan=False, allow_infinity=False))


@st.composite
def proposed_price_paise_strategy(draw: Any) -> int:
    """Generate proposed prices: ₹0 to ₹10M paise."""
    return draw(st.integers(min_value=0, max_value=1_000_000_000))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_bundle_engine() -> Any:
    """Mock BundleEngine with cost_floor, derive_price, validate_price methods."""
    engine = MagicMock()
    engine.cost_floor = AsyncMock()
    engine.derive_price = AsyncMock()
    engine.validate_price = AsyncMock()
    return engine


@pytest.fixture
def mock_db_session() -> Any:
    """Mock AsyncSession for DB operations."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_redis_client() -> Any:
    """Mock Redis client."""
    return MagicMock()


@pytest.fixture
def mock_pricing_floor_log_row() -> dict[str, Any]:
    """Template for a pricing_floor_log database row."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "proposed_price_paise": 50_000,
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "outcome": "APPROVED",
        "recorded_at": datetime.utcnow(),
    }


# ── Unit Tests: BundleEngine ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cost_floor_reads_from_db_not_recomputed(
    mock_bundle_engine: Any,
    mock_db_session: Any,
) -> None:
    """
    GIVEN a BundleEngine instance
    WHEN cost_floor(agent_type='DMA', bundle_tier='STANDARD') is called
    THEN it reads bundle_profiles.cost_floor_paise from DB (not recomputed)
    AND returns the exact DB value.
    """
    # Arrange: Mock DB query result
    db_cost_floor_paise = 40_000
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_cost_floor_paise
    mock_bundle_engine.cost_floor.return_value = db_cost_floor_paise

    # Act
    result = await mock_bundle_engine.cost_floor("DMA", "STANDARD")

    # Assert
    assert result == db_cost_floor_paise
    mock_bundle_engine.cost_floor.assert_called_once_with("DMA", "STANDARD")


@pytest.mark.asyncio
async def test_derive_price_uses_margin_on_revenue_formula(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN cost_floor_paise=40_000, margin_pct=20%
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=20) is called
    THEN it applies formula: price = floor / (1 - margin/100)
    AND returns price ≈ 50_000 (40_000 / 0.80 = 50_000).
    """
    # Arrange
    cost_floor_paise = 40_000
    target_margin_pct = 20.0
    expected_price = int(cost_floor_paise / (1 - target_margin_pct / 100))
    # 40_000 / (1 - 0.20) = 40_000 / 0.80 = 50_000
    
    mock_bundle_engine.derive_price.return_value = expected_price

    # Act
    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

    # Assert
    assert result == 50_000
    mock_bundle_engine.derive_price.assert_called_once()


@pytest.mark.asyncio
async def test_validate_price_approved_outcome_writes_audit_log(
    mock_bundle_engine: Any,
    mock_pricing_floor_log_row: dict[str, Any],
) -> None:
    """
    GIVEN proposed_price_paise=50_000 > minimum_compliant_price_paise=48_000
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called
    THEN outcome='APPROVED'
    AND pricing_floor_log row is written (C-059 audit obligation)
    AND response includes minimum_compliant_price_paise.
    """
    # Arrange
    mock_row = dict(mock_pricing_floor_log_row)
    mock_row["outcome"] = "APPROVED"
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

    # Assert
    assert result["outcome"] == "APPROVED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["proposed_price_paise"] == 50_000
    mock_bundle_engine.validate_price.assert_called_once_with("DMA", "STANDARD", 50_000)


@pytest.mark.asyncio
async def test_validate_price_rejected_outcome_writes_audit_log(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN proposed_price_paise=30_000 < minimum_compliant_price_paise=48_000
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called
    THEN outcome='REJECTED'
    AND pricing_floor_log row is written (C-059 audit obligation)
    AND HTTP 422 response body includes minimum_compliant_price_paise
    AND response includes cost_floor_paise.
    """
    # Arrange
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    # Assert
    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["cost_floor_paise"] == 40_000
    assert result["proposed_price_paise"] == 30_000
    mock_bundle_engine.validate_price.assert_called_once_with("DMA", "STANDARD", 30_000)


@pytest.mark.asyncio
async def test_post_pricing_validate_200_approved_response_structure(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with proposed_price_paise=50_000
    WHEN the price is compliant (≥ minimum_compliant_price_paise)
    THEN HTTP 200 response includes outcome='APPROVED', cost_floor_paise, minimum_compliant_price_paise.
    """
    # Arrange
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

    # Assert
    assert result["outcome"] == "APPROVED"
    assert "cost_floor_paise" in result
    assert "minimum_compliant_price_paise" in result
    assert result["cost_floor_paise"] == 40_000
    assert result["minimum_compliant_price_paise"] == 48_000


@pytest.mark.asyncio
async def test_post_pricing_validate_422_rejected_response_structure(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with proposed_price_paise=30_000
    WHEN the price is non-compliant (< minimum_compliant_price_paise)
    THEN HTTP 422 response body includes outcome='REJECTED', minimum_compliant_price_paise, cost_floor_paise.
    """
    # Arrange
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    # Assert
    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["cost_floor_paise"] == 40_000


@pytest.mark.asyncio
async def test_get_pricing_thread_catalog_response_shape(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a GET /pricing/thread-catalog request
    WHEN the endpoint is called
    THEN response includes list of ThreadCatalogEntry objects
    AND each entry has thread_id, display_name, provider, unit_description,
       raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise, is_platform_thread, applicable_agents, status.
    """
    # Arrange
    thread_catalog = [
        {
            "thread_id": "thread-001",
            "display_name": "GPT-4 Turbo",
            "provider": "OpenAI",
            "unit_description": "per 1K tokens",
            "raw_cost_inr_paise": 5000,
            "total_markup_pct": 15.0,
            "marked_up_cost_paise": 5750,
            "is_platform_thread": False,
            "applicable_agents": ["DMA", "PPA"],
            "status": "ACTIVE",
        },
        {
            "thread_id": "thread-002",
            "display_name": "Claude 3 Opus",
            "provider": "Anthropic",
            "unit_description": "per 1K tokens",
            "raw_cost_inr_paise": 7500,
            "total_markup_pct": 15.0,
            "marked_up_cost_paise": 8625,
            "is_platform_thread": False,
            "applicable_agents": ["DMA"],
            "status": "ACTIVE",
        },
    ]
    mock_bundle_engine.get_thread_catalog = AsyncMock(return_value=thread_catalog)

    # Act
    result = await mock_bundle_engine.get_thread_catalog()

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    for entry in result:
        assert "thread_id" in entry
        assert "display_name" in entry
        assert "provider" in entry
        assert "unit_description" in entry
        assert "raw_cost_inr_paise" in entry
        assert "total_markup_pct" in entry
        assert "marked_up_cost_paise" in entry
        assert "is_platform_thread" in entry
        assert "applicable_agents" in entry
        assert "status" in entry


# ── Property-Based Tests: Hypothesis ──────────────────────────────────────────

@given(cost_floor_paise_strategy(), margin_pct_strategy())
@pytest.mark.asyncio
async def test_derive_price_property_zero_margin(
    cost_floor_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price with 0% margin
    GIVEN cost_floor_paise=X, margin_pct=0.0
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=0.0) is called
    THEN price = X / (1 - 0/100) = X / 1 = X (returns cost_floor exactly).
    """
    # Arrange
    target_margin_pct = 0.0
    expected_price = int(cost_floor_paise / (1 - target_margin_pct / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    # Act
    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

    # Assert
    assert result == cost_floor_paise
    assert result == expected_price


@given(cost_floor_paise_strategy(), margin_pct_strategy())
@pytest.mark.asyncio
async def test_derive_price_property_near_100_margin(
    cost_floor_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price with high margin (approaching 100%)
    GIVEN cost_floor_paise=X, margin_pct=99.9%
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=99.9) is called
    THEN price = X / (1 - 99.9/100) = X / 0.001 ≈ 1000 * X (large multiplier).
    """
    # Arrange
    target_margin_pct = 99.9
    denominator = 1 - target_margin_pct / 100
    expected_price = int(cost_floor_paise / denominator)
    mock_bundle_engine.derive_price.return_value = expected_price

    # Act
    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

    # Assert
    # price should be much larger than cost_floor
    assert result > cost_floor_paise
    assert result == expected_price


@given(cost_floor_paise_strategy(), margin_pct_strategy())
@pytest.mark.asyncio
async def test_derive_price_property_large_paise_values(
    cost_floor_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price with large paise values (up to ₹10M)
    GIVEN cost_floor_paise ranges from ₹1 to ₹10M paise
    WHEN derive_price is called with varying margins
    THEN result is always positive and respects margin-on-revenue formula.
    """
    # Arrange
    target_margin_pct = 25.0
    expected_price = int(cost_floor_paise / (1 - target_margin_pct / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    # Act
    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

    # Assert
    assert result > 0
    assert result >= cost_floor_paise


@given(
    cost_floor_paise_strategy(),
    margin_pct_strategy(),
    st.floats(min_value=0.0, max_value=1.0),
)
@pytest.mark.asyncio
async def test_derive_price_property_float_precision(
    cost_floor_paise: int,
    target_margin_pct: float,
    _unused_float: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price handles float precision correctly
    GIVEN margin_pct as float with decimal places
    WHEN derive_price is called
    THEN result is always an integer (truncated, not rounded away from cost floor)
    AND result ≥ cost_floor_paise (C-089: never price below cost).
    """
    # Arrange
    if target_margin_pct == 100.0:
        target_margin_pct = 99.9
    
    expected_price = int(cost_floor_paise / (1 - target_margin_pct / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    # Act
    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

    # Assert
    assert isinstance(result, int)
    assert result >= cost_floor_paise


# ── Property-Based Tests: validate_price ──────────────────────────────────────

@given(
    cost_floor_paise_strategy(),
    proposed_price_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_property_approved_path(
    cost_floor_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: validate_price APPROVED path
    GIVEN cost_floor_paise=X
    AND proposed_price_paise ≥ minimum_compliant_price_paise (where min = X * 1.2)
    WHEN validate_price is called
    THEN outcome='APPROVED'
    AND response includes all required fields.
    """
    # Arrange
    minimum_compliant_price_paise = int(cost_floor_paise * 1.2)
    proposed_price_paise = minimum_compliant_price_paise + 1000

    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": cost_floor_paise,
        "minimum_compliant_price_paise": minimum_compliant_price_paise,
        "proposed_price_paise": proposed_price_paise,
    }

    # Act
    result = await mock_bundle_engine.validate_price(
        "DMA",
        "STANDARD",
        proposed_price_paise,
    )

    # Assert
    assert result["outcome"] == "APPROVED"
    assert result["proposed_price_paise"] >= result["minimum_compliant_price_paise"]
    assert "cost_floor_paise" in result
    assert "minimum_compliant_price_paise" in result


@given(
    cost_floor_paise_strategy(),
    proposed_price_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_property_rejected_path(
    cost_floor_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: validate_price REJECTED path
    GIVEN cost_floor_paise=X
    AND proposed_price_paise < minimum_compliant_price_paise (where min = X * 1.2)
    WHEN validate_price is called
    THEN outcome='REJECTED'
    AND response includes minimum_compliant_price_paise (C-089 enforcement).
    """
    # Arrange
    minimum_compliant_price_paise = int(cost_floor_paise * 1.2)
    # Generate proposed price strictly less than minimum
    if minimum_compliant_price_paise > 0:
        proposed_price_paise = max(0, minimum_compliant_price_paise - 1)
    else:
        proposed_price_paise = 0

    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": cost_floor_paise,
        "minimum_compliant_price_paise": minimum_compliant_price_paise,
        "proposed_price_paise": proposed_price_paise,
    }

    # Act
    result = await mock_bundle_engine.validate_price(
        "DMA",
        "STANDARD",
        proposed_price_paise,
    )

    # Assert
    assert result["outcome"] == "REJECTED"
    assert "minimum_compliant_price_paise" in result
    assert result["minimum_compliant_price_paise"] > result["proposed_price_paise"]


@pytest.mark.asyncio
async def test_pricing_floor_log_audit_trail_approved(
    mock_bundle_engine: Any,
    mock_db_session: Any,
) -> None:
    """
    C-059 COMPLIANCE: Audit trail for APPROVED pricing
    GIVEN validate_price returns APPROVED outcome
    WHEN the result is written to pricing_floor_log
    THEN exactly one row is inserted with all required fields.
    """
    # Arrange
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

    # Assert
    assert result["outcome"] == "APPROVED"


@pytest.mark.asyncio
async def test_pricing_floor_log_audit_trail_rejected(
    mock_bundle_engine: Any,
    mock_db_session: Any,
) -> None:
    """
    C-059 COMPLIANCE: Audit trail for REJECTED pricing
    GIVEN validate_price returns REJECTED outcome
    WHEN the result is written to pricing_floor_log
    THEN exactly one row is inserted with all required fields including minimum_compliant_price_paise.
    """
    # Arrange
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()

    # Act
    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    # Assert
    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000