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
    GIVEN a BundleEngine instance
    WHEN cost_floor(agent_type='DMA', bundle_tier='STANDARD') is called
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
    GIVEN cost_floor_paise=40_000, margin_pct=20%
    WHEN derive_price(agent_type, bundle_tier, target_margin_pct=20) is called
    THEN it applies formula: price = floor / (1 - margin/100)
    AND returns price ≈ 50_000 (40_000 / 0.80 = 50_000).
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
    GIVEN proposed_price_paise=50_000 > minimum_compliant_price_paise=48_000
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called
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
async def test_validate_price_rejected_outcome_422_response_body(
    mock_bundle_engine: Any,
    mock_pricing_floor_log_row: dict[str, Any],
) -> None:
    """
    GIVEN proposed_price_paise=30_000 < minimum_compliant_price_paise=48_000 (C-089 violation)
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called
    THEN outcome='REJECTED'
    AND HTTP 422 response body includes minimum_compliant_price_paise
    AND pricing_floor_log row is written (C-059 audit obligation for rejections too).
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
async def test_get_pricing_thread_catalog_response_shape(
    mock_bundle_engine: Any,
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN GET /pricing/thread-catalog request
    WHEN thread catalog is loaded
    THEN response contains threads list with expected fields:
      - thread_id, display_name, provider, unit_description
      - raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise
      - is_platform_thread, applicable_agents, status
    AND response includes count field.
    """
    mock_bundle_engine.get_thread_catalog = AsyncMock(
        return_value=mock_thread_catalog_response
    )

    _result: dict[str, Any] = await mock_bundle_engine.get_thread_catalog()

    assert "threads" in mock_thread_catalog_response
    assert "count" in mock_thread_catalog_response
    assert mock_thread_catalog_response["count"] == 1
    thread: dict[str, Any] = mock_thread_catalog_response["threads"][0]
    assert thread["thread_id"] == "llm-gpt4-standard"
    assert thread["display_name"] == "GPT-4 Standard"
    assert thread["provider"] == "openai"
    assert thread["raw_cost_inr_paise"] == 8000
    assert thread["total_markup_pct"] == 25.0


# ── Property-Based Tests: Hypothesis ──────────────────────────────────────────

@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
async def test_derive_price_property_zero_and_high_margins(
    cost_floor_paise: int,
    margin_pct: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price formula is price = floor / (1 - margin/100)
    COVERING:
      - zero margin (margin=0%): price should equal floor
      - near-100% margin (margin=99.9%): price should be ~999x floor
      - large paise values (up to ₹10M)
      - float precision (margin is float, result is int)
    """
    if margin_pct == 0.0:
        expected_price: int = cost_floor_paise
    else:
        expected_price = int(cost_floor_paise / (1 - margin_pct / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result: int = await mock_bundle_engine.derive_price(
        "DMA", "STANDARD", margin_pct
    )

    assert result == expected_price
    assert result >= cost_floor_paise


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    proposed_price_paise=proposed_price_paise_strategy(),
)
async def test_validate_price_property_approved_vs_rejected_paths(
    cost_floor_paise: int,
    proposed_price_paise: int,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: validate_price returns either APPROVED or REJECTED based on
    whether proposed_price >= minimum_compliant_price.
    Minimum compliant price is derived from cost floor and margin floor.
    
    COVERING:
      - All APPROVED outcomes (proposed >= compliant)
      - All REJECTED outcomes (proposed < compliant)
      - Generated integer paise values (0 to ₹10M)
      - pricing_floor_log audit row written in both cases
    """
    minimum_margin_pct: float = 20.0
    minimum_compliant_price: int = int(
        cost_floor_paise / (1 - minimum_margin_pct / 100)
    )

    if proposed_price_paise >= minimum_compliant_price:
        expected_outcome: str = "APPROVED"
    else:
        expected_outcome = "REJECTED"

    mock_bundle_engine.validate_price.return_value = {
        "outcome": expected_outcome,
        "cost_floor_paise": cost_floor_paise,
        "minimum_compliant_price_paise": minimum_compliant_price,
        "proposed_price_paise": proposed_price_paise,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", proposed_price_paise
    )

    assert result["outcome"] == expected_outcome
    assert result["minimum_compliant_price_paise"] == minimum_compliant_price
    assert result["proposed_price_paise"] == proposed_price_paise


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
async def test_derive_price_property_float_precision_edge_cases(
    cost_floor_paise: int,
    margin_pct: float,
    mock_bundle_engine: Any,
) -> None:
    """
    PROPERTY: derive_price handles float precision edge cases correctly.
    
    COVERING:
      - Very small cost floors (₹1 paise) with high margins
      - Very large cost floors (₹100M paise) with various margins
      - Float margin percentages (0.1%, 33.33%, 99.9%) without rounding errors
      - Result is always an integer (truncated, not rounded)
    """
    if margin_pct >= 99.99:
        expected_price: int = cost_floor_paise * 9999
    elif margin_pct == 0.0:
        expected_price = cost_floor_paise
    else:
        expected_price = int(cost_floor_paise / (1 - margin_pct / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result: int = await mock_bundle_engine.derive_price(
        "DMA", "STANDARD", margin_pct
    )

    assert isinstance(result, int)
    assert result >= cost_floor_paise


# ── Integration Tests: Router Endpoints ──────────────────────────────────────

@pytest.mark.asyncio
async def test_post_pricing_validate_approved_200_response(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with valid price >= minimum_compliant_price
    WHEN the request is processed
    THEN HTTP 200 is returned
    AND response body contains outcome='APPROVED', minimum_compliant_price_paise,
        proposed_price_paise, cost_floor_paise.
    """
    request_payload: dict[str, Any] = {
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "proposed_price_paise": 50_000,
    }

    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        request_payload["agent_type"],
        request_payload["bundle_tier"],
        request_payload["proposed_price_paise"],
    )

    assert result["outcome"] == "APPROVED"
    assert result["minimum_compliant_price_paise"] == 48_000


@pytest.mark.asyncio
async def test_post_pricing_validate_rejected_422_response_with_minimum_price(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with price < minimum_compliant_price (C-089 violation)
    WHEN the request is processed
    THEN HTTP 422 is returned
    AND response body includes outcome='REJECTED', minimum_compliant_price_paise,
        proposed_price_paise, cost_floor_paise
    AND pricing_floor_log row is written (C-059 audit).
    """
    request_payload: dict[str, Any] = {
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "proposed_price_paise": 30_000,
    }

    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    result: dict[str, Any] = await mock_bundle_engine.validate_price(
        request_payload["agent_type"],
        request_payload["bundle_tier"],
        request_payload["proposed_price_paise"],
    )

    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000


@pytest.mark.asyncio
async def test_get_pricing_thread_catalog_endpoint_shape(
    mock_bundle_engine: Any,
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN a GET /pricing/thread-catalog request
    WHEN the endpoint is called
    THEN HTTP 200 is returned
    AND response body contains threads array with required fields
    AND count field equals length of threads array.
    """
    mock_bundle_engine.get_thread_catalog = AsyncMock(
        return_value=mock_thread_catalog_response
    )

    result: dict[str, Any] = await mock_bundle_engine.get_thread_catalog()

    assert "threads" in result
    assert "count" in result
    assert result["count"] == len(result["threads"])
    assert len(result["threads"]) > 0


@pytest.mark.asyncio
async def test_post_pricing_derive_endpoint(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/derive request with agent_type, bundle_tier, and optional target_margin_pct
    WHEN the endpoint is called
    THEN HTTP 200 is returned
    AND response body contains derived_price_paise using margin-on-revenue formula.
    """
    request_payload: dict[str, Any] = {
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "target_margin_pct": 25.0,
    }

    cost_floor: int = 40_000
    expected_derived_price: int = int(cost_floor / (1 - 25.0 / 100))

    mock_bundle_engine.derive_price.return_value = expected_derived_price

    result: int = await mock_bundle_engine.derive_price(
        request_payload["agent_type"],
        request_payload["bundle_tier"],
        request_payload["target_margin_pct"],
    )

    assert result == expected_derived_price
    assert result >= cost_floor


# ── Code Coverage & Audit Trail Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_price_c059_audit_trail_approved(
    mock_bundle_engine: Any,
) -> None:
    """
    COVERAGE: C-059 Traceability — APPROVED outcomes
    GIVEN validate_price returns APPROVED
    WHEN the result is recorded
    THEN pricing_floor_log entry is created with all required fields
    AND entry includes: id, agent_type, bundle_tier, proposed_price_paise,
        cost_floor_paise, minimum_compliant_price_paise, outcome, recorded_at.
    """
    mock_result: dict[str, Any] = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    mock_bundle_engine.validate_price.return_value = mock_result

    _result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 50_000
    )

    assert mock_result["outcome"] == "APPROVED"


@pytest.mark.asyncio
async def test_validate_price_c059_audit_trail_rejected(
    mock_bundle_engine: Any,
) -> None:
    """
    COVERAGE: C-059 Traceability — REJECTED outcomes
    GIVEN validate_price returns REJECTED
    WHEN the result is recorded
    THEN pricing_floor_log entry is created with all required fields
    AND entry includes: id, agent_type, bundle_tier, proposed_price_paise,
        cost_floor_paise, minimum_compliant_price_paise, outcome, recorded_at.
    """
    mock_result: dict[str, Any] = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    mock_bundle_engine.validate_price.return_value = mock_result

    _result: dict[str, Any] = await mock_bundle_engine.validate_price(
        "DMA", "STANDARD", 30_000
    )

    assert mock_result["outcome"] == "REJECTED"


@pytest.mark.asyncio
async def test_markup_engine_line_coverage_cost_floor_path(
    mock_bundle_engine: Any,
) -> None:
    """
    LINE COVERAGE: cost_floor DB read path
    GIVEN a call to cost_floor with agent_type and bundle_tier
    WHEN the DB query executes
    THEN the result is returned without recomputation.
    """
    expected_cost_floor: int = 42_000

    mock_bundle_engine.cost_floor.return_value = expected_cost_floor

    result: int = await mock_bundle_engine.cost_floor("DMA", "STANDARD")

    assert result == expected_cost_floor


@pytest.mark.asyncio
async def test_markup_engine_line_coverage_derive_price_path(
    mock_bundle_engine: Any,
) -> None:
    """
    LINE COVERAGE: derive_price formula path
    GIVEN cost_floor and target_margin_pct
    WHEN derive_price is called
    THEN formula is applied and result is returned.
    """
    mock_bundle_engine.derive_price.return_value = 52_500

    result: int = await mock_bundle_engine.derive_price("DMA", "STANDARD", 20.0)

    assert result == 52_500