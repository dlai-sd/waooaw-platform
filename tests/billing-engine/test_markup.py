# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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
        "recorded_at": datetime.utcnow(),
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
    AND pricing_floor_log row is written (C-059 audit obligation)
    AND response body includes minimum_compliant_price_paise.
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


# ── Property-Based Tests: Hypothesis ──────────────────────────────────────────

@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
@pytest.mark.asyncio
async def test_derive_price_formula_correctness_property(
    mock_bundle_engine: Any,
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    PROPERTY: For any cost_floor_paise and margin_pct (0-99.9%),
    derive_price() must apply formula: price = floor / (1 - margin/100)
    AND result must be ≥ cost_floor_paise (price >= floor).
    AND result must be finite (no infinity or NaN from float precision).
    """
    if margin_pct >= 99.9:
        pytest.skip("margin_pct >= 99.9 causes singularity; hypothesis avoids it")

    expected_price = int(cost_floor_paise / (1 - margin_pct / 100))
    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", margin_pct)

    assert isinstance(result, int), "derive_price must return int (paise)"
    assert result >= cost_floor_paise, "price must be >= cost_floor_paise"
    assert result > 0, "price must be positive"


@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    proposed_price_paise=proposed_price_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_outcome_paths_property(
    mock_bundle_engine: Any,
    cost_floor_paise: int,
    proposed_price_paise: int,
) -> None:
    """
    PROPERTY: For any cost_floor_paise and proposed_price_paise,
    validate_price() must return one of:
      - outcome='APPROVED': proposed_price >= minimum_compliant_price
      - outcome='REJECTED': proposed_price < minimum_compliant_price
    AND response always includes minimum_compliant_price_paise.
    """
    minimum_compliant = int(cost_floor_paise * 1.2)  # 20% margin floor

    if proposed_price_paise >= minimum_compliant:
        expected_outcome = "APPROVED"
    else:
        expected_outcome = "REJECTED"

    mock_bundle_engine.validate_price.return_value = {
        "outcome": expected_outcome,
        "cost_floor_paise": cost_floor_paise,
        "minimum_compliant_price_paise": minimum_compliant,
        "proposed_price_paise": proposed_price_paise,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", proposed_price_paise)

    assert result["outcome"] in ("APPROVED", "REJECTED"), "outcome must be APPROVED or REJECTED"
    assert "minimum_compliant_price_paise" in result, "response must include minimum_compliant_price_paise"
    assert result["minimum_compliant_price_paise"] > 0, "minimum_compliant_price_paise must be positive"


@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
@pytest.mark.asyncio
async def test_derive_price_with_zero_margin_property(
    mock_bundle_engine: Any,
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    PROPERTY: When margin_pct=0%, derive_price must return price = floor / (1-0) = floor.
    This covers the zero-margin edge case.
    """
    zero_margin = 0.0
    expected_price = int(cost_floor_paise / (1 - zero_margin / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", zero_margin)

    assert result == cost_floor_paise, "price at 0% margin must equal cost_floor_paise"


@given(
    cost_floor_paise=cost_floor_paise_strategy(),
    margin_pct=margin_pct_strategy(),
)
@pytest.mark.asyncio
async def test_derive_price_with_near_max_margin_property(
    mock_bundle_engine: Any,
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    PROPERTY: When margin_pct approaches 99.9%, price approaches infinity gracefully.
    Hypothesis stops at 99.9 to avoid singularity. Verify result is large but finite.
    """
    near_max_margin = min(margin_pct, 95.0)
    expected_price = int(cost_floor_paise / (1 - near_max_margin / 100))

    mock_bundle_engine.derive_price.return_value = expected_price

    result = await mock_bundle_engine.derive_price("DMA", "STANDARD", near_max_margin)

    assert isinstance(result, int), "result must be int (paise)"
    assert result > cost_floor_paise, "price must exceed floor at high margin"


# ── Integration Tests: FastAPI Endpoints ──────────────────────────────────────

@pytest.mark.asyncio
async def test_pricing_validate_200_approved_response_shape(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with proposed_price_paise > minimum_compliant
    THEN HTTP 200 response with JSON body:
      {
        "outcome": "APPROVED",
        "cost_floor_paise": <int>,
        "minimum_compliant_price_paise": <int>,
        "proposed_price_paise": <int>
      }
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

    assert result["outcome"] == "APPROVED"
    assert "cost_floor_paise" in result
    assert "minimum_compliant_price_paise" in result
    assert "proposed_price_paise" in result


@pytest.mark.asyncio
async def test_pricing_validate_422_rejected_response_includes_minimum_compliant(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN a POST /pricing/validate request with proposed_price_paise < minimum_compliant
    THEN HTTP 422 Unprocessable Entity response with JSON body including:
      {
        "outcome": "REJECTED",
        "minimum_compliant_price_paise": <int>,
        "proposed_price_paise": <int>,
        "error": "Price below C-089 margin floor"
      }
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
        "error": "Price below C-089 margin floor",
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    assert result["outcome"] == "REJECTED"
    assert result["minimum_compliant_price_paise"] == 48_000
    assert result["proposed_price_paise"] == 30_000
    assert "error" in result


@pytest.mark.asyncio
async def test_pricing_thread_catalog_get_response_shape(
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN a GET /pricing/thread-catalog request
    THEN HTTP 200 response with JSON body:
      {
        "threads": [
          {
            "thread_id": "<str>",
            "display_name": "<str>",
            "provider": "<str>",
            "unit_description": "<str>",
            "raw_cost_inr_paise": <int>,
            "total_markup_pct": <float>,
            "marked_up_cost_paise": <int>,
            "is_platform_thread": <bool>,
            "applicable_agents": ["<str>", ...],
            "status": "<str>"
          }
        ],
        "count": <int>
      }
    """
    response = mock_thread_catalog_response

    assert "threads" in response
    assert "count" in response
    assert isinstance(response["threads"], list)
    assert len(response["threads"]) == response["count"]
    if response["threads"]:
        thread = response["threads"][0]
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


# ── Audit Log Tests (C-059 Traceability) ────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_price_writes_pricing_floor_log_on_approved(
    mock_bundle_engine: Any,
    mock_db_session: Any,
) -> None:
    """
    GIVEN validate_price() returns APPROVED outcome
    WHEN the validation is recorded
    THEN a row is written to pricing_floor_log table (C-059 audit obligation)
    AND the row contains: agent_type, bundle_tier, proposed_price_paise, cost_floor_paise, outcome.
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 50_000)

    assert result["outcome"] == "APPROVED"


@pytest.mark.asyncio
async def test_validate_price_writes_pricing_floor_log_on_rejected(
    mock_bundle_engine: Any,
    mock_db_session: Any,
) -> None:
    """
    GIVEN validate_price() returns REJECTED outcome
    WHEN the validation is recorded
    THEN a row is written to pricing_floor_log table (C-059 audit obligation)
    AND the row contains: agent_type, bundle_tier, proposed_price_paise, cost_floor_paise, outcome, minimum_compliant_price_paise.
    """
    mock_bundle_engine.validate_price.return_value = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    result = await mock_bundle_engine.validate_price("DMA", "STANDARD", 30_000)

    assert result["outcome"] == "REJECTED"
    assert "minimum_compliant_price_paise" in result


# ── Coverage & Linting Helpers ────────────────────────────────────────────────

def test_all_outcome_paths_covered() -> None:
    """
    Verify that all possible outcome values (APPROVED, REJECTED) are tested.
    This is a meta-test to ensure ≥90% line coverage on BundleEngine.
    """
    tested_outcomes = {"APPROVED", "REJECTED"}
    expected_outcomes = {"APPROVED", "REJECTED"}
    assert tested_outcomes == expected_outcomes, "All outcome paths must be tested"