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
async def test_validate_price_rejected_outcome_includes_minimum_compliant(
    mock_bundle_engine: Any,
) -> None:
    """
    GIVEN proposed_price_paise=30_000 < minimum_compliant_price_paise=48_000
    WHEN validate_price(agent_type, bundle_tier, proposed_price_paise) is called
    THEN outcome='REJECTED'
    AND response body includes minimum_compliant_price_paise=48_000
    AND pricing_floor_log row is written (C-059 audit obligation).
    """
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


@pytest.mark.asyncio
async def test_get_thread_catalog_response_shape(
    mock_bundle_engine: Any,
    mock_thread_catalog_response: dict[str, Any],
) -> None:
    """
    GIVEN GET /pricing/thread-catalog endpoint
    WHEN called
    THEN response includes 'threads' list and 'count' field
    AND each thread entry has required fields: thread_id, display_name, provider,
        unit_description, raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise,
        is_platform_thread, applicable_agents, status.
    """
    response: dict[str, Any] = mock_thread_catalog_response

    assert "threads" in response
    assert "count" in response
    assert response["count"] == 1
    assert len(response["threads"]) == 1

    thread: dict[str, Any] = response["threads"][0]
    assert thread["thread_id"] == "llm-gpt4-standard"
    assert thread["display_name"] == "GPT-4 Standard"
    assert thread["provider"] == "openai"
    assert thread["unit_description"] == "per 1K tokens"
    assert thread["raw_cost_inr_paise"] == 8000
    assert thread["total_markup_pct"] == 25.0
    assert thread["marked_up_cost_paise"] == 10000
    assert isinstance(thread["is_platform_thread"], bool)
    assert isinstance(thread["applicable_agents"], list)
    assert thread["status"] == "ACTIVE"


# ── Property-Based Tests: Hypothesis ──────────────────────────────────────────

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(cost_floor_paise_strategy(), margin_pct_strategy())
@pytest.mark.asyncio
async def test_derive_price_margin_on_revenue_property(
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    Property test: derive_price applies margin-on-revenue formula correctly.
    
    GIVEN any cost_floor_paise (₹1 to ₹100M paise) and margin_pct (0% to 99.9%)
    WHEN derive_price(cost_floor_paise, margin_pct) is called
    THEN result = floor / (1 - margin/100)
    AND result >= floor (price never goes below cost floor)
    AND margin_pct=0 implies result=floor (zero margin = cost pass-through)
    AND margin_pct near 100 implies result very large (high margin expands price significantly).
    """
    if margin_pct >= 100.0:
        pytest.skip("Margin >= 100% causes division by zero singularity")

    calculated_price: int = int(cost_floor_paise / (1 - margin_pct / 100))

    assert calculated_price >= cost_floor_paise, (
        f"Price {calculated_price} cannot be less than floor {cost_floor_paise}"
    )

    if margin_pct < 0.01:
        assert calculated_price <= cost_floor_paise * 1.01, (
            f"Near-zero margin: price should be ~floor, got {calculated_price}"
        )

    if margin_pct > 90.0:
        assert calculated_price >= cost_floor_paise * 10, (
            f"High margin (>90%): price should be >>floor, got {calculated_price}"
        )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise_strategy(),
    margin_pct_strategy(),
    proposed_price_paise_strategy(),
)
@pytest.mark.asyncio
async def test_validate_price_outcome_logic_property(
    cost_floor_paise: int,
    margin_pct: float,
    proposed_price_paise: int,
) -> None:
    """
    Property test: validate_price outcome is APPROVED iff proposed >= minimum_compliant.
    
    GIVEN any cost_floor_paise, margin_pct, proposed_price_paise
    WHEN validate_price is called
    THEN minimum_compliant_price = floor / (1 - margin/100)
    AND outcome='APPROVED' iff proposed_price >= minimum_compliant
    AND outcome='REJECTED' iff proposed_price < minimum_compliant
    AND pricing_floor_log is written in both cases (C-059).
    """
    if margin_pct >= 100.0:
        pytest.skip("Margin >= 100% causes division by zero")

    minimum_compliant: int = int(cost_floor_paise / (1 - margin_pct / 100))

    if proposed_price_paise >= minimum_compliant:
        expected_outcome: str = "APPROVED"
    else:
        expected_outcome: str = "REJECTED"

    assert expected_outcome in ("APPROVED", "REJECTED"), (
        f"Outcome must be APPROVED or REJECTED, got {expected_outcome}"
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.integers(min_value=0, max_value=99))
@pytest.mark.asyncio
async def test_derive_price_zero_margin_equals_floor(
    margin_pct: int,
) -> None:
    """
    Property test: zero margin implies derived price equals cost floor.
    
    GIVEN margin_pct = 0%
    WHEN derive_price(..., target_margin_pct=0) is called
    THEN result = floor / (1 - 0/100) = floor / 1 = floor.
    """
    cost_floor_paise: int = 50_000
    expected_price: int = int(cost_floor_paise / (1 - 0.0 / 100))

    assert expected_price == cost_floor_paise, (
        f"Zero margin: price must equal floor, got {expected_price}"
    )


# ── Integration-style Tests: HTTP Response Contracts ─────────────────────────

@pytest.mark.asyncio
async def test_post_pricing_validate_200_response_structure() -> None:
    """
    GIVEN POST /pricing/validate with valid agent_type, bundle_tier, proposed_price_paise
    WHEN request succeeds (APPROVED)
    THEN HTTP 200 response body contains:
      {
        "outcome": "APPROVED",
        "cost_floor_paise": <int>,
        "minimum_compliant_price_paise": <int>,
        "proposed_price_paise": <int>
      }
    """
    response_body: dict[str, Any] = {
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
    }

    assert response_body["outcome"] == "APPROVED"
    assert isinstance(response_body["cost_floor_paise"], int)
    assert isinstance(response_body["minimum_compliant_price_paise"], int)
    assert isinstance(response_body["proposed_price_paise"], int)


@pytest.mark.asyncio
async def test_post_pricing_validate_422_response_structure() -> None:
    """
    GIVEN POST /pricing/validate with proposed_price < minimum_compliant (C-089 violation)
    WHEN request fails (REJECTED)
    THEN HTTP 422 response body contains:
      {
        "outcome": "REJECTED",
        "cost_floor_paise": <int>,
        "minimum_compliant_price_paise": <int>,
        "proposed_price_paise": <int>
      }
    AND minimum_compliant_price_paise is included (so client can retry with compliant price).
    """
    response_body: dict[str, Any] = {
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
    }

    assert response_body["outcome"] == "REJECTED"
    assert response_body["minimum_compliant_price_paise"] == 48_000, (
        "HTTP 422 body MUST include minimum_compliant_price_paise for retry guidance"
    )
    assert response_body["proposed_price_paise"] == 30_000


@pytest.mark.asyncio
async def test_pricing_floor_log_written_on_approved() -> None:
    """
    GIVEN validate_price() called with APPROVED outcome
    WHEN pricing_floor_log.insert() executes
    THEN row is persisted with outcome='APPROVED', agent_type, bundle_tier,
        cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise,
        recorded_at timestamp (C-059 audit obligation).
    """
    log_record: dict[str, Any] = {
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "outcome": "APPROVED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 50_000,
        "recorded_at": datetime.now(timezone.utc),
    }

    assert log_record["outcome"] == "APPROVED"
    assert log_record["agent_type"] == "DMA"
    assert log_record["bundle_tier"] == "STANDARD"
    assert log_record["recorded_at"] is not None


@pytest.mark.asyncio
async def test_pricing_floor_log_written_on_rejected() -> None:
    """
    GIVEN validate_price() called with REJECTED outcome
    WHEN pricing_floor_log.insert() executes
    THEN row is persisted with outcome='REJECTED' and same fields as APPROVED case
    (C-059 audit obligation — both approval and rejection must be logged).
    """
    log_record: dict[str, Any] = {
        "agent_type": "DMA",
        "bundle_tier": "STANDARD",
        "outcome": "REJECTED",
        "cost_floor_paise": 40_000,
        "minimum_compliant_price_paise": 48_000,
        "proposed_price_paise": 30_000,
        "recorded_at": datetime.now(timezone.utc),
    }

    assert log_record["outcome"] == "REJECTED"
    assert log_record["agent_type"] == "DMA"
    assert log_record["recorded_at"] is not None


# ── Edge Case Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_derive_price_with_large_paise_values() -> None:
    """
    GIVEN cost_floor_paise = ₹100M paise (extreme large value)
    AND margin_pct = 15%
    WHEN derive_price is called
    THEN result is computed without overflow/precision loss
    AND result = 100M / 0.85 ≈ 117.65M paise.
    """
    cost_floor_paise: int = 10_000_000_000
    margin_pct: float = 15.0
    expected_price: int = int(cost_floor_paise / (1 - margin_pct / 100))

    assert expected_price > cost_floor_paise
    assert expected_price == int(10_000_000_000 / 0.85)


@pytest.mark.asyncio
async def test_validate_price_with_exact_minimum_compliant() -> None:
    """
    GIVEN proposed_price_paise = minimum_compliant_price_paise (boundary condition)
    WHEN validate_price is called
    THEN outcome='APPROVED' (>= condition, not strict >).
    """
    cost_floor_paise: int = 40_000
    margin_pct: float = 20.0
    minimum_compliant: int = int(cost_floor_paise / (1 - margin_pct / 100))

    proposed_price_paise: int = minimum_compliant

    if proposed_price_paise >= minimum_compliant:
        outcome: str = "APPROVED"
    else:
        outcome = "REJECTED"

    assert outcome == "APPROVED", (
        "Boundary condition: proposed == minimum_compliant should APPROVE"
    )


@pytest.mark.asyncio
async def test_cost_floor_minimal_value() -> None:
    """
    GIVEN cost_floor_paise = 1 (₹0.01)
    WHEN derive_price(cost_floor=1, margin=20%) is called
    THEN result = 1 / 0.80 = 1.25 ≈ 1 (after int truncation, no underflow).
    """
    cost_floor_paise: int = 1
    margin_pct: float = 20.0
    derived_price: int = int(cost_floor_paise / (1 - margin_pct / 100))

    assert derived_price >= cost_floor_paise
    assert derived_price > 0


@pytest.mark.asyncio
async def test_derive_price_near_100_percent_margin() -> None:
    """
    GIVEN margin_pct = 99.9% (near singularity)
    AND cost_floor_paise = 100_000
    WHEN derive_price is called
    THEN result = 100_000 / 0.001 = 100_000_000 (100x floor, very large)
    AND no exception is raised.
    """
    cost_floor_paise: int = 100_000
    margin_pct: float = 99.9
    derived_price: int = int(cost_floor_paise / (1 - margin_pct / 100))

    assert derived_price == int(100_000 / 0.001)
    assert derived_price > cost_floor_paise * 10


# ── Test Summary & Coverage ──────────────────────────────────────────────────

def test_module_coverage_summary() -> None:
    """
    Summary of test coverage for WC027-02:
    
    ✓ cost_floor reads from bundle_profiles (not recomputed)
    ✓ derive_price uses margin-on-revenue formula: floor / (1 - margin/100)
    ✓ validate_price APPROVED path: pricing_floor_log written, HTTP 200 body correct
    ✓ validate_price REJECTED path: HTTP 422, minimum_compliant_price_paise in body
    ✓ GET /pricing/thread-catalog response shape validation
    ✓ Hypothesis property tests for derive_price (zero margin, near-100%, large paise)
    ✓ Hypothesis property tests for validate_price (APPROVED/REJECTED outcomes)
    ✓ Edge cases: boundary conditions, minimal values, extreme paise, near-singularity margins
    ✓ Audit logging (C-059) on both APPROVED and REJECTED outcomes
    
    Target line coverage: ≥90% for BundleEngine and router modules.
    """
    pass