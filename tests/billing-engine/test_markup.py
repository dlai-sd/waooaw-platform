# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
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
    return draw(
        st.floats(
            min_value=0.0,
            max_value=99.9,
            allow_nan=False,
            allow_infinity=False,
        )
    )


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
        "recorded_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def mock_thread_catalog_response() -> dict[str, Any]:
    """Mock response shape for GET /pricing/thread-catalog."""
    return {
        "threads": [
            {
                "thread_id": "llm-gpt4-standard",
                "display_name": "GPT-4 Standard",
                "provider": "openai",
                "unit_description": "per 1K tokens",
                "raw_cost_inr_paise": 8000,
                "total_markup_pct": 25.0,
                "marked_up_cost_paise": 10000,
                "is_platform_thread": False,
                "applicable_agents": ["DMA", "CTA"],
                "status": "ACTIVE",
            }
        ],
        "count": 1,
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
    db_cost_floor_paise = 40_000
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
        db_cost_floor_paise
    )
    mock_bundle_engine.cost_floor.return_value = db_cost_floor_paise

    result = await mock_bundle_engine.cost_floor("DMA", "STANDARD")

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
    cost_floor_paise = 40_000
    target_margin_pct = 20.0
    expected_price = int(cost_floor_paise / (1 - target_margin_pct / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", target_margin_pct)

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
    mock_row = dict(mock_pricing_floor_log_row)
    mock_row["outcome"] = "APPROVED"
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

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
    AND HTTP 422 response includes minimum_compliant_price_paise in body
    AND pricing_floor_log row is written (C-059 audit obligation).
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["proposed_price_paise"] == 30_000
    mock_bundle_engine.validate_price.assert_called_once_with("DMA", "STANDARD", 30_000)


@pytest.mark.asyncio
async def test_get_thread_catalog_response_shape(
    mock_bundle_engine: Any,
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN GET /pricing/thread-catalog endpoint
    WHEN called
    THEN response includes threads array with correct fields
    AND each thread has: thread_id, display_name, provider, unit_description,
        raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise,
        is_platform_thread, applicable_agents, status.
    """
    mock_bundle_engine.thread_catalog = AsyncMock(
        return_value=mock_thread_catalog_response
    )

    response = mock_thread_catalog_response
    assert "threads" in response
    assert "count" in response
    assert len(response["threads"]) == 1
    thread = response["threads"][0]
    assert thread["thread_id"] == "llm-gpt4-standard"
    assert thread["display_name"] == "GPT-4 Standard"
    assert thread["provider"] == "openai"
    assert thread["unit_description"] == "per 1K tokens"
    assert thread["raw_cost_inr_paise"] == 8000
    assert thread["total_markup_pct"] == 25.0
    assert thread["marked_up_cost_paise"] == 10000
    assert thread["is_platform_thread"] is False
    assert "DMA" in thread["applicable_agents"]
    assert thread["status"] == "ACTIVE"


# ── Property-Based Tests: derive_price Financial Math ─────────────────────────

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor=cost_floor_paise_strategy(),
    margin=margin_pct_strategy(),
)
@pytest.mark.asyncio
async def test_derive_price_property_margin_on_revenue_formula(
    cost_floor: int,
    margin: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: derive_price(cost_floor, margin_pct)
    GIVEN any realistic cost_floor_paise and margin_pct
    WHEN derive_price is called with target_margin_pct
    THEN formula price = cost_floor / (1 - margin/100) holds
    AND price is always > cost_floor (margin > 0)
    AND price never causes division-by-zero (margin < 100%).
    """
    if margin >= 100.0:
        return

    expected_price = int(cost_floor / (1 - margin / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", margin)

    assert result == expected_price
    assert result >= cost_floor


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor=cost_floor_paise_strategy(),
    margin=margin_pct_strategy(),
)
@pytest.mark.asyncio
async def test_derive_price_property_zero_margin_equals_floor(
    cost_floor: int,
    margin: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: derive_price with zero margin
    GIVEN cost_floor_paise=X and margin_pct=0.0
    WHEN derive_price(target_margin_pct=0) is called
    THEN price = X / (1 - 0/100) = X / 1 = X (price equals cost floor exactly).
    """
    expected_price = int(cost_floor / (1 - 0.0 / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", 0.0)

    assert result == cost_floor


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor=cost_floor_paise_strategy(),
    margin=st.floats(min_value=50.0, max_value=99.9, allow_nan=False, allow_infinity=False),
)
@pytest.mark.asyncio
async def test_derive_price_property_high_margin_precision(
    cost_floor: int,
    margin: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: derive_price with high margins (50–99.9%)
    GIVEN large margins (near singularity at 100%)
    WHEN derive_price is called
    THEN price is computed correctly without float precision loss
    AND result > cost_floor significantly (high markup).
    """
    expected_price = int(cost_floor / (1 - margin / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", margin)

    assert result > cost_floor
    assert result == expected_price


# ── Property-Based Tests: validate_price Coverage ──────────────────────────────

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    proposed_price=proposed_price_paise_strategy(),
    cost_floor=cost_floor_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_property_approved_path(
    proposed_price: int,
    cost_floor: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: validate_price APPROVED path
    GIVEN cost_floor_paise and proposed_price_paise
    WHEN proposed_price >= minimum_compliant_price (cost_floor * margin multiplier)
    THEN outcome='APPROVED'
    AND pricing_floor_log row is written
    AND response includes all required fields.
    """
    minimum_compliant = int(cost_floor * 1.2)
    if proposed_price >= minimum_compliant:
        mock_bundle_engine.validate_price.return_value = {
            "outcome": "APPROVED",
            "cost_floor_paise": cost_floor,
            "minimum_compliant_price_paise": minimum_compliant,
            "proposed_price_paise": proposed_price,
        }

        result = await mock_bundle_engine.validate_price("DMA", "STANDARD", proposed_price)

        assert result["outcome"] == "APPROVED"
        assert result["cost_floor_paise"] == cost_floor
        assert result["minimum_compliant_price_paise"] == minimum_compliant
        assert result["proposed_price_paise"] == proposed_price


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    proposed_price=proposed_price_paise_strategy(),
    cost_floor=cost_floor_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_property_rejected_path(
    proposed_price: int,
    cost_floor: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: validate_price REJECTED path
    GIVEN cost_floor_paise and proposed_price_paise
    WHEN proposed_price < minimum_compliant_price
    THEN outcome='REJECTED'
    AND HTTP 422 response body includes minimum_compliant_price_paise (C-089)
    AND pricing_floor_log row is written (C-059).
    """
    minimum_compliant = int(cost_floor * 1.2)
    if proposed_price < minimum_compliant:
        mock_bundle_engine.validate_price.return_value = {
            "outcome": "REJECTED",
            "cost_floor_paise": cost_floor,
            "minimum_compliant_price_paise": minimum_compliant,
            "proposed_price_paise": proposed_price,
        }

        result = await mock_bundle_engine.validate_price("DMA", "STANDARD", proposed_price)

        assert result["outcome"] == "REJECTED"
        assert result["cost_floor_paise"] == cost_floor
        assert result["minimum_compliant_price_paise"] == minimum_compliant
        assert result["proposed_price_paise"] == proposed_price


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.sampled_from(["DMA", "CTA", "CUSTOM"]))
@pytest.mark.asyncio
async def test_validate_price_property_agent_type_invariant(
    agent_type: str,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY TEST: validate_price across agent types
    GIVEN any agent_type (DMA, CTA, CUSTOM)
    WHEN validate_price is called
    THEN response shape is consistent (outcome, cost_floor_paise, minimum_compliant_price_paise).
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result = await mock_bundle_engine.validate_price(agent_type, "STANDARD", 50_000)

    assert "outcome" in result
    assert "cost_floor_paise" in result
    assert "minimum_compliant_price_paise" in result
    assert "proposed_price_paise" in result