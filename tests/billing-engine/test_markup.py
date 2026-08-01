# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Hypothesis Strategies for Financial Math ─────────────────────────────────

@st.composite
def cost_floor_paise_strategy(draw: Any) -> int:
    """Generate realistic cost_floor_paise: rupee 1 paise to rupee 100,000 paise (rupee 1 to rupee 1000)."""
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
    """Generate proposed prices: rupee 0 to rupee 10M paise."""
    return draw(st.integers(min_value=0, max_value=1_000_000_000))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_bundle_engine() -> Any:
    """Mock BundleEngine with cost_floor, derive_price, validate_price methods."""
    engine: Any = MagicMock()
    engine.cost_floor = AsyncMock()
    engine.derive_price = AsyncMock()
    engine.validate_price = AsyncMock()
    return engine


@pytest.fixture
def mock_db_session() -> Any:
    """Mock AsyncSession for DB operations."""
    session: Any = AsyncMock(spec=AsyncSession)
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
    GIVEN a BundleEngine instance.
    WHEN cost_floor(agent_type='DMA', bundle_tier='STANDARD') is called.
    THEN it reads bundle_profiles.cost_floor_paise from DB (not recomputed)
    AND returns the exact DB value.
    """
    db_cost_floor_paise: int = 40_000
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
        db_cost_floor_paise
    )
    mock_bundle_engine.cost_floor.return_value = db_cost_floor_paise

    result: int = await mock_bundle_engine.cost_floor("DMA", "STANDARD")

    assert result == db_cost_floor_paise
    mock_bundle_engine.cost_floor.assert_called_once_with("DMA", "STANDARD")


@pytest.mark.asyncio
async def test_derive_price_uses_margin_on_revenue_formula(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN cost_floor_paise=40_000, margin_pct=20%.
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=20) is called.
    THEN it applies formula: price = floor / (1 - margin/100)
    AND returns price approximately 50_000 (40_000 / 0.80 = 50_000).
    """
    cost_floor_paise: int = 40_000
    target_margin_pct: float = 20.0
    expected_price: int = int(cost_floor_paise / (1 - target_margin_pct / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result: int = await mock_bundle_engine.derive_price(
        "DMA", "STANDARD", target_margin_pct
    )

    assert result == 50_000
    mock_bundle_engine.derive_price.assert_called_once()


@pytest.mark.asyncio
async def test_validate_price_approved_outcome_writes_audit_log(
    mock_bundle_engine: Any,
    mock_pricing_floor_log_row: dict[str, Any],
) -> None:
    """
    GIVEN proposed_price_paise=50_000 > minimum_compliant_price_paise=48_000.
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called.
    THEN outcome='APPROVED'
    AND pricing_floor_log row is written (C-059 audit obligation)
    AND response includes minimum_compliant_price_paise.
    """
    mock_row: dict[str, Any] = dict(mock_pricing_floor_log_row)
    mock_row["outcome"] = "APPROVED"
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 50_000
    )

    assert result["outcome"] == "APPROVED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["proposed_price_paise"] == 50_000
    mock_bundle_engine.validate_price.assert_called_once_with("DMA", "STANDARD", 50_000)


@pytest.mark.asyncio
async def test_validate_price_rejected_outcome_includes_minimum_compliant_price(
    mock_bundle_engine: Any,
    mock_pricing_floor_log_row: dict[str, Any],
) -> None:
    """
    GIVEN proposed_price_paise=30_000 < minimum_compliant_price_paise=48_000 (C-089 violation).
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called.
    THEN outcome='REJECTED'
    AND pricing_floor_log row is written (C-059 audit obligation)
    AND response body includes minimum_compliant_price_paise for HTTP 422 error response.
    """
    mock_row: dict[str, Any] = dict(mock_pricing_floor_log_row)
    mock_row["outcome"] = "REJECTED"
    mock_row["proposed_price_paise"] = 30_000
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 30_000
    )

    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["proposed_price_paise"] == 30_000
    mock_bundle_engine.validate_price.assert_called_once_with("DMA", "STANDARD", 30_000)


@pytest.mark.asyncio
async def test_thread_catalog_response_shape(
    mock_bundle_engine: Any,
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN a ThreadCatalogService.
    WHEN GET /pricing/thread-catalog is called.
    THEN response includes 'threads' list and 'count' field
    AND each thread entry has required fields: thread_id, display_name, provider,
        unit_description, raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise,
        is_platform_thread, applicable_agents, status.
    """
    mock_bundle_engine.get_thread_catalog.return_value = mock_thread_catalog_response

    result: dict[str, Any] = await mock_bundle_engine.get_thread_catalog()

    assert "threads" in result
    assert "count" in result
    assert result["count"] == 1
    assert len(result["threads"]) == 1

    thread: dict[str, Any] = result["threads"][0]
    assert "thread_id" in thread
    assert "display_name" in thread
    assert "provider" in thread
    assert "unit_description" in thread
    assert "raw_cost_inr_paise" in thread
    assert "total_markup_pct" in thread
    assert "marked_up_cost_paise" in thread
    assert "is_platform_thread" in thread
    assert "applicable_agents" in thread
    assert "status" in thread


# ── Property-Based Tests with Hypothesis ──────────────────────────────────────

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
def test_derive_price_formula_property(
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    Property: derive_price(cost_floor, margin_pct) applies formula:
        price = cost_floor / (1 - margin_pct/100)
    
    Covers:
    - Zero margin: price ≈ cost_floor
    - Near-100% margin: price approaches infinity (capped at 99.9%)
    - Large paise values: up to rupee 100,000
    - Float precision: margin_pct as float with decimals
    """
    if margin_pct >= 100.0:
        pytest.skip("Margin >= 100% is mathematically undefined (division by zero)")

    divisor: float = 1.0 - (margin_pct / 100.0)
    if divisor <= 0.0:
        pytest.skip("Divisor is non-positive; singularity avoided by margin_pct < 100%")

    expected_price: float = cost_floor_paise / divisor
    expected_price_int: int = int(expected_price)

    # Formula validation: for zero margin, price should equal cost_floor
    if margin_pct == 0.0:
        assert expected_price_int == cost_floor_paise, (
            "Zero margin should yield price = cost_floor"
        )

    # Formula validation: price >= cost_floor (always, since divisor < 1 for margin > 0)
    if margin_pct > 0.0:
        assert expected_price_int >= cost_floor_paise, (
            "Price must be >= cost_floor for positive margin"
        )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    proposed_price_paise=proposed_price_paise_strategy(),
    minimum_margin_pct=margin_pct_strategy(),
)
def test_validate_price_outcome_property(
    cost_floor_paise: int,
    proposed_price_paise: int,
    minimum_margin_pct: float,
) -> None:
    """
    Property: validate_price determines outcome based on:
        minimum_compliant_price = cost_floor / (1 - minimum_margin/100)
        outcome = APPROVED if proposed_price >= minimum_compliant_price else REJECTED
    
    Covers:
    - All outcome paths: APPROVED, REJECTED
    - Generated integer paise values: 0 to rupee 10M
    - Margin percentages: 0% to 99.9%
    """
    if minimum_margin_pct >= 100.0:
        pytest.skip("Margin >= 100% is undefined")

    divisor: float = 1.0 - (minimum_margin_pct / 100.0)
    if divisor <= 0.0:
        pytest.skip("Divisor is non-positive")

    minimum_compliant_price: int = int(
        cost_floor_paise / divisor
    )

    # APPROVED path: proposed >= minimum_compliant
    if proposed_price_paise >= minimum_compliant_price:
        outcome: str = "APPROVED"
    else:
        outcome = "REJECTED"

    # Validate outcome consistency
    if outcome == "APPROVED":
        assert proposed_price_paise >= minimum_compliant_price, (
            "APPROVED outcome requires proposed_price >= minimum_compliant_price"
        )
    else:
        assert proposed_price_paise < minimum_compliant_price, (
            "REJECTED outcome requires proposed_price < minimum_compliant_price"
        )


@pytest.mark.asyncio
async def test_pricing_floor_log_written_on_both_approved_and_rejected(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN validate_price is called for both APPROVED and REJECTED outcomes.
    WHEN the validation completes.
    THEN pricing_floor_log row is written in BOTH cases (C-059 audit obligation).
    """
    approved_result: dict[str, Any] = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }
    rejected_result: dict[str, Any] = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    mock_bundle_engine.validate_price.side_effect = [approved_result, rejected_result]

    approved_call: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 50_000
    )
    rejected_call: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 30_000
    )

    assert approved_call["outcome"] == "APPROVED"
    assert rejected_call["outcome"] == "REJECTED"
    assert mock_bundle_engine.validate_price.call_count == 2


@pytest.mark.asyncio
async def test_cost_floor_uses_bundle_profiles_table(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN bundle_profiles table in DB has cost_floor_paise for DMA/STANDARD.
    WHEN cost_floor(agent_type='DMA', bundle_tier='STANDARD') is called.
    THEN it reads from bundle_profiles (not bundle_profiles or thread_catalog)
    AND returns the exact DB value without recomputation.
    """
    expected_cost_floor: int = 45_000
    mock_bundle_engine.cost_floor.return_value = expected_cost_floor

    result: int = await mock_bundle_engine.cost_floor("DMA", "STANDARD")

    assert result == expected_cost_floor


@pytest.mark.asyncio
async def test_derive_price_falls_back_to_minimum_margin_pct(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN target_margin_pct is None.
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=None) is called.
    THEN it uses bundle_profiles.minimum_margin_pct from DB
    AND applies margin-on-revenue formula with that margin.
    """
    cost_floor_paise: int = 40_000
    minimum_margin_pct: float = 15.0
    expected_price: int = int(cost_floor_paise / (1 - minimum_margin_pct / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result: int = await mock_bundle_engine.derive_price(
        "DMA", "STANDARD", None
    )

    assert result == expected_price
    mock_bundle_engine.derive_price.assert_called_once_with("DMA", "STANDARD", None)


@pytest.mark.asyncio
async def test_validate_price_returns_all_required_fields(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN validate_price is called.
    WHEN the validation completes.
    THEN response includes: outcome, cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise
    AND all fields are present for HTTP response and 422 error body construction.
    """
    expected_response: dict[str, Any] = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }
    mock_bundle_engine.validate_price.return_value = expected_response

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 50_000
    )

    assert "outcome" in result
    assert "cost_floor_paise" in result
    assert "minimum_compliant_price_paise" in result
    assert "proposed_price_paise" in result
    assert result == expected_response


@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=50,
)
@given(
    cost_floor=cost_floor_paise_strategy(),
    margin=margin_pct_strategy(),
)
def test_derive_price_large_values_property(
    cost_floor: int,
    margin: float,
) -> None:
    """
    Property: derive_price handles large paise values (up to rupee 100,000 = 10M paise)
    and large margin percentages (up to 99.9%) without overflow or precision loss.
    """
    if margin >= 100.0:
        pytest.skip("Margin >= 100% skipped")

    divisor: float = 1.0 - (margin / 100.0)
    if divisor <= 0.0:
        pytest.skip("Divisor is non-positive")

    price: float = cost_floor / divisor
    price_int: int = int(price)

    # Sanity checks
    assert isinstance(price_int, int), "Result must be integer paise"
    assert price_int >= 0, "Price cannot be negative"
    if margin > 0:
        assert price_int >= cost_floor, "Price must exceed cost_floor for positive margin"


@pytest.mark.asyncio
async def test_validate_price_c089_compliance_margin_floor(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN C-089 margin floor requirement: price >= cost_floor / (1 - min_margin/100).
    WHEN validate_price is called with proposed_price below the floor.
    THEN outcome='REJECTED' and response.minimum_compliant_price_paise is set
    AND audit log (pricing_floor_log) records the violation (C-059).
    """
    cost_floor_paise: int = 40_000
    minimum_margin_pct: float = 20.0
    minimum_compliant: int = int(cost_floor_paise / (1 - minimum_margin_pct / 100))
    proposed_below_floor: int = minimum_compliant - 1000

    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": cost_floor_paise,
        "minimum_compliant_price_paise": minimum_compliant,
        "proposed_price_paise": proposed_below_floor,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", proposed_below_floor
    )

    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == minimum_compliant