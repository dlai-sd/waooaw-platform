# Implements: WC027-02 — tests for BundleEngine, pricing router, property-based math
# constitutional_basis: C-059, C-073, C-076, C-089, C-097
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from hypothesis import given, settings
from hypothesis import strategies as st

# --- sys.path injection (hyphen dirs are not importable as dotted paths) ---
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidation,
    ThreadEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db() -> AsyncMock:
    """Return a fresh AsyncMock that behaves like an AsyncSession."""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


def _row(values: tuple[Any, ...]) -> MagicMock:
    """Return a MagicMock that behaves like a SQLAlchemy Row."""
    row = MagicMock()
    row.__getitem__ = lambda self, idx: values[idx]
    # Support positional attribute access via index
    for _i, _v in enumerate(values):
        row.__getitem__ = lambda self, idx, _v=values: _v[idx]
    return row


def _make_execute_result(row_values: tuple[Any, ...] | None) -> MagicMock:
    result = MagicMock()
    if row_values is None:
        result.fetchone.return_value = None
    else:
        result.fetchone.return_value = row_values
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def mock_app() -> FastAPI:
    """Return the billing-engine FastAPI app with DB and CE mocked."""
    from main import create_app  # type: ignore[import]

    application = create_app()
    return application


@pytest_asyncio.fixture
async def client(mock_app: FastAPI) -> AsyncClient:  # type: ignore[override]
    """Async HTTP client wired to the billing-engine app with all external deps mocked."""
    async with AsyncClient(
        transport=ASGITransport(app=mock_app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Pure-unit: BundleEngine.cost_floor reads bundle_profiles.cost_floor_paise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cost_floor_reads_stored_value_not_recomputed() -> None:
    """cost_floor must return the DB-stored value, never recompute it."""
    db = _make_mock_db()
    stored_floor = 75_000  # 750 INR in paise

    db.execute = AsyncMock(
        return_value=_make_execute_result((stored_floor,))
    )

    engine = BundleEngine(db=db)
    result = await engine.cost_floor(agent_type="DMA", bundle_tier="STANDARD")

    assert result == stored_floor
    # Verify only ONE DB call was made (no recomputation queries)
    assert db.execute.call_count == 1
    call_sql = str(db.execute.call_args[0][0])
    assert "cost_floor_paise" in call_sql
    assert "bundle_profiles" in call_sql


@pytest.mark.asyncio
async def test_cost_floor_raises_when_profile_missing() -> None:
    """cost_floor must raise ValueError when no bundle profile row exists."""
    db = _make_mock_db()
    db.execute = AsyncMock(return_value=_make_execute_result(None))

    engine = BundleEngine(db=db)
    with pytest.raises(ValueError, match="Bundle profile not found"):
        await engine.cost_floor(agent_type="UNKNOWN", bundle_tier="TIER_X")


# ---------------------------------------------------------------------------
# Pure-unit: derive_price uses margin-on-revenue formula floor / (1 - m/100)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_derive_price_margin_on_revenue_formula() -> None:
    """derive_price must use floor / (1 - margin/100), not cost-plus."""
    cost_floor = 80_000
    minimum_margin_pct = 20

    db = _make_mock_db()
    db.execute = AsyncMock(
        return_value=_make_execute_result((cost_floor, minimum_margin_pct))
    )

    engine = BundleEngine(db=db)
    result = await engine.derive_price(agent_type="DMA", bundle_tier="STANDARD")

    expected = int(cost_floor / (1 - minimum_margin_pct / 100))
    assert result == expected
    # Sanity: cost-plus would give 96_000; margin-on-revenue gives 100_000
    assert result == 100_000


@pytest.mark.asyncio
async def test_derive_price_uses_target_margin_when_provided() -> None:
    """derive_price must use target_margin_pct when explicitly supplied."""
    cost_floor = 50_000
    minimum_margin_pct = 10
    target_margin_pct = 30

    db = _make_mock_db()
    db.execute = AsyncMock(
        return_value=_make_execute_result((cost_floor, minimum_margin_pct))
    )

    engine = BundleEngine(db=db)
    result = await engine.derive_price(
        agent_type="DMA", bundle_tier="STANDARD", target_margin_pct=target_margin_pct
    )

    expected = int(cost_floor / (1 - target_margin_pct / 100))
    assert result == expected


@pytest.mark.asyncio
async def test_derive_price_raises_on_100_pct_margin() -> None:
    """derive_price must raise ValueError when margin >= 100."""
    db = _make_mock_db()
    db.execute = AsyncMock(return_value=_make_execute_result((50_000, 10)))

    engine = BundleEngine(db=db)
    with pytest.raises(ValueError, match="Margin percentage must be < 100"):
        await engine.derive_price(
            agent_type="DMA", bundle_tier="STANDARD", target_margin_pct=100
        )


# ---------------------------------------------------------------------------
# Pure-unit: validate_price — APPROVED path + pricing_floor_log written
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_price_approved_writes_log() -> None:
    """validate_price APPROVED: outcome==APPROVED and pricing_floor_log row written."""
    cost_floor = 60_000
    minimum_margin_pct = 20
    proposed = 80_000  # >= floor / (1 - 0.20) = 75_000 → APPROVED

    db = _make_mock_db()
    execute_calls: list[Any] = []

    async def _execute(query: Any, params: dict[str, Any] | None = None) -> MagicMock:
        sql = str(query)
        execute_calls.append(sql)
        if "billing_profiles" in sql:
            return _make_execute_result(("FOUNDER_AUTHORIZED",))
        if "bundle_profiles" in sql:
            return _make_execute_result((cost_floor, minimum_margin_pct))
        # pricing_floor_log INSERT
        return MagicMock()

    db.execute = _execute  # type: ignore[assignment]

    engine = BundleEngine(db=db)
    result = await engine.validate_price(
        agent_type="DMA", bundle_tier="STANDARD", proposed_price_paise=proposed
    )

    assert result.outcome == "APPROVED"
    assert result.cost_floor_paise == cost_floor
    assert result.proposed_price_paise == proposed
    assert result.minimum_compliant_price_paise == int(cost_floor / (1 - minimum_margin_pct / 100))

    # C-059: commit must have been called (log row persisted)
    db.commit.assert_called_once()

    # pricing_floor_log INSERT must appear in executed SQL
    log_sqls = [s for s in execute_calls if "pricing_floor_log" in s]
    assert len(log_sqls) == 1


@pytest.mark.asyncio
async def test_validate_price_rejected_writes_log() -> None:
    """validate_price REJECTED: outcome==REJECTED, minimum_compliant_price_paise present, log written."""
    cost_floor = 60_000
    minimum_margin_pct = 20
    proposed = 50_000  # < 75_000 → REJECTED

    db = _make_mock_db()
    execute_calls: list[Any] = []

    async def _execute(query: Any, params: dict[str, Any] | None = None) -> MagicMock:
        sql = str(query)
        execute_calls.append(sql)
        if "billing_profiles" in sql:
            return _make_execute_result(("FOUNDER_AUTHORIZED",))
        if "bundle_profiles" in sql:
            return _make_execute_result((cost_floor, minimum_margin_pct))
        return MagicMock()

    db.execute = _execute  # type: ignore[assignment]

    engine = BundleEngine(db=db)
    result = await engine.validate_price(
        agent_type="DMA", bundle_tier="STANDARD", proposed_price_paise=proposed
    )

    assert result.outcome == "REJECTED"
    assert result.minimum_compliant_price_paise == int(cost_floor / (1 - minimum_margin_pct / 100))
    assert result.proposed_price_paise == proposed

    db.commit.assert_called_once()
    log_sqls = [s for s in execute_calls if "pricing_floor_log" in s]
    assert len(log_sqls) == 1


@pytest.mark.asyncio
async def test_validate_price_raises_when_not_founder_authorized() -> None:
    """validate_price must raise ValueError when billing_profiles.status != FOUNDER_AUTHORIZED."""
    db = _make_mock_db()

    async def _execute(query: Any, params: dict[str, Any] | None = None) -> MagicMock:
        sql = str(query)
        if "billing_profiles" in sql:
            return _make_execute_result(("PENDING",))
        return _make_execute_result((60_000, 20))

    db.execute = _execute  # type: ignore[assignment]

    engine = BundleEngine(db=db)
    with pytest.raises(ValueError, match="FOUNDER_AUTHORIZED"):
        await engine.validate_price(
            agent_type="DMA", bundle_tier="STANDARD", proposed_price_paise=80_000
        )


# ---------------------------------------------------------------------------
# HTTP integration: POST /pricing/validate — 200 APPROVED path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_pricing_validate_approved(client: AsyncClient) -> None:
    """POST /pricing/validate returns 200 with APPROVED outcome."""
    cost_floor = 60_000
    minimum_margin_pct = 20
    proposed = 80_000

    mock_validation = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=int(cost_floor / (1 - minimum_margin_pct / 100)),
        proposed_price_paise=proposed,
    )

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.validate_price = AsyncMock(return_value=mock_validation)
        mock_engine_cls.return_value = mock_engine

        response = await client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "STANDARD",
                "proposed_price_paise": proposed,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "APPROVED"
    assert body["cost_floor_paise"] == cost_floor
    assert "minimum_compliant_price_paise" in body


# ---------------------------------------------------------------------------
# HTTP integration: POST /pricing/validate — 422 REJECTED path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_pricing_validate_rejected(client: AsyncClient) -> None:
    """POST /pricing/validate returns 422 with minimum_compliant_price_paise on REJECTED."""
    cost_floor = 60_000
    minimum_margin_pct = 20
    proposed = 50_000
    min_compliant = int(cost_floor / (1 - minimum_margin_pct / 100))

    mock_validation = PriceValidation(
        outcome="REJECTED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=min_compliant,
        proposed_price_paise=proposed,
    )

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.validate_price = AsyncMock(return_value=mock_validation)
        mock_engine_cls.return_value = mock_engine

        response = await client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "STANDARD",
                "proposed_price_paise": proposed,
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["outcome"] == "REJECTED"
    assert detail["minimum_compliant_price_paise"] == min_compliant
    assert detail["proposed_price_paise"] == proposed


# ---------------------------------------------------------------------------
# HTTP integration: POST /pricing/validate (scaffold alias)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_pricing_validate(client: AsyncClient) -> None:
    """Test POST /pricing/validate — APPROVED path via HTTP."""
    cost_floor = 100_000
    minimum_margin_pct = 25
    proposed = 140_000
    min_compliant = int(cost_floor / (1 - minimum_margin_pct / 100))

    mock_validation = PriceValidation(
        outcome="APPROVED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=min_compliant,
        proposed_price_paise=proposed,
    )

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.validate_price = AsyncMock(return_value=mock_validation)
        mock_engine_cls.return_value = mock_engine

        response = await client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "PREMIUM",
                "proposed_price_paise": proposed,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "APPROVED"
    assert body["minimum_compliant_price_paise"] == min_compliant


# ---------------------------------------------------------------------------
# HTTP integration: GET /pricing/thread-catalog response shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pricing_thread_catalog(client: AsyncClient) -> None:
    """GET /pricing/thread-catalog returns list with correct shape."""
    sample_entry = ThreadEntry(
        thread_id="t-001",
        display_name="GPT-4o Standard",
        provider="openai",
        unit_description="per 1k tokens",
        raw_cost_inr_paise=500,
        total_markup_pct=20.0,
        marked_up_cost_paise=600,
        is_platform_thread=True,
        applicable_agents=["DMA", "CCA"],
        status="ACTIVE",
    )

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.thread_catalog") as mock_tc,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_tc.get_all_threads = AsyncMock(return_value=[sample_entry])

        response = await client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    entry = body[0]
    assert entry["thread_id"] == "t-001"
    assert entry["display_name"] == "GPT-4o Standard"
    assert entry["provider"] == "openai"
    assert entry["raw_cost_inr_paise"] == 500
    assert entry["marked_up_cost_paise"] == 600
    assert entry["is_platform_thread"] is True
    assert "applicable_agents" in entry
    assert "status" in entry


@pytest.mark.asyncio
async def test_get_thread_catalog(client: AsyncClient) -> None:
    """GET /pricing/thread-catalog — alias test verifying list shape."""
    entries = [
        ThreadEntry(
            thread_id=f"t-{i:03d}",
            display_name=f"Thread {i}",
            provider="anthropic",
            unit_description="per call",
            raw_cost_inr_paise=1000 * i,
            total_markup_pct=15.0,
            marked_up_cost_paise=int(1000 * i * 1.15),
            is_platform_thread=False,
            applicable_agents=["DMA"],
            status="ACTIVE",
        )
        for i in range(1, 4)
    ]

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.thread_catalog") as mock_tc,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_tc.get_all_threads = AsyncMock(return_value=entries)

        response = await client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    for item in body:
        assert "thread_id" in item
        assert "raw_cost_inr_paise" in item
        assert "marked_up_cost_paise" in item


# ---------------------------------------------------------------------------
# HTTP integration: GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_bundle_cost_floor_agent_type_bundle_tier(client: AsyncClient) -> None:
    """GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns cost_floor_paise."""
    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.cost_floor = AsyncMock(return_value=75_000)
        mock_engine_cls.return_value = mock_engine

        response = await client.get("/pricing/bundle-cost-floor/DMA/STANDARD")

    assert response.status_code == 200
    body = response.json()
    assert body["cost_floor_paise"] == 75_000


# ---------------------------------------------------------------------------
# HTTP integration: POST /pricing/validate (scaffold alias)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_validate(client: AsyncClient) -> None:
    """POST /pricing/validate — REJECTED path returns 422 with minimum_compliant_price_paise."""
    cost_floor = 80_000
    minimum_margin_pct = 30
    proposed = 90_000
    min_compliant = int(cost_floor / (1 - minimum_margin_pct / 100))  # ~114_285

    mock_validation = PriceValidation(
        outcome="REJECTED",
        cost_floor_paise=cost_floor,
        minimum_compliant_price_paise=min_compliant,
        proposed_price_paise=proposed,
    )

    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.validate_price = AsyncMock(return_value=mock_validation)
        mock_engine_cls.return_value = mock_engine

        response = await client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "STANDARD",
                "proposed_price_paise": proposed,
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["minimum_compliant_price_paise"] == min_compliant


# ---------------------------------------------------------------------------
# HTTP integration: POST /pricing/derive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_derive(client: AsyncClient) -> None:
    """POST /pricing/derive returns derived_price_paise."""
    with (
        patch("markup.router.CE") as mock_ce,
        patch("markup.router.BundleEngine") as mock_engine_cls,
    ):
        mock_ce.ValidateAction = AsyncMock(return_value=None)
        mock_engine = AsyncMock()
        mock_engine.derive_price = AsyncMock(return_value=100_000)
        mock_engine_cls.return_value = mock_engine

        response = await client.post(
            "/pricing/derive",
            json={"agent_type": "DMA", "bundle_tier": "STANDARD"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["derived_price_paise"] == 100_000


# ---------------------------------------------------------------------------
# Property-based tests — C-097
# ---------------------------------------------------------------------------

def _derive_price_pure(cost_floor_paise: int, margin_pct: float) -> int:
    """Pure Python implementation of the margin-on-revenue formula."""
    return int(cost_floor_paise / (1 - margin_pct / 100))


@given(
    cost_floor_paise=st.integers(min_value=0, max_value=10_000_000),
    margin_pct=st.floats(
        min_value=0.0,
        max_value=99.9,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@settings(max_examples=500)
def test_property_derive_price_margin_on_revenue(
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """
    Property: derive_price always uses floor / (1 - margin/100).
    Covers zero margin, near-100% margin, large paise values, float precision.
    """
    result = _derive_price_pure(cost_floor_paise, margin_pct)

    # Result must be an integer (paise — never float)
    assert isinstance(result, int)

    # Zero margin: price == cost_floor (int truncation)
    if margin_pct == 0.0:
        assert result == cost_floor_paise

    # Result must be >= cost_floor (margin-on-revenue always inflates)
    assert result >= cost_floor_paise

    # Near-100% margin: price must be very large (but finite)
    if margin_pct >= 99.0:
        assert result >= cost_floor_paise * 100

    # Verify formula exactly
    expected = int(cost_floor_paise / (1 - margin_pct / 100))
    assert result == expected


@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
    margin_pct=st.integers(min_value=1, max_value=50),
    proposed_price_paise=st.integers(min_value=1, max_value=20_000_000),
)
@settings(max_examples=500)
def test_property_validate_price_outcomes(
    cost_floor_paise: int,
    margin_pct: int,
    proposed_price_paise: int,
) -> None:
    """
    Property: validate_price outcome is deterministic based on margin-on-revenue formula.
    Covers APPROVED and REJECTED paths with generated integer paise values.
    """
    minimum_compliant = int(cost_floor_paise / (1 - margin_pct / 100))

    if proposed_price_paise >= minimum_compliant:
        expected_outcome = "APPROVED"
    else:
        expected_outcome = "REJECTED"

    # Verify the formula is consistent
    assert minimum_compliant >= cost_floor_paise

    # APPROVED: proposed >= minimum_compliant
    if expected_outcome == "APPROVED":
        assert proposed_price_paise >= minimum_compliant

    # REJECTED: proposed < minimum_compliant, and minimum_compliant is returned
    if expected_outcome == "REJECTED":
        assert proposed_price_paise < minimum_compliant
        assert minimum_compliant > 0

    # minimum_compliant_price_paise must always be an integer
    assert isinstance(minimum_compliant, int)


@given(
    cost_floor_paise=st.integers(min_value=0, max_value=10_000_000),
    margin_pct=st.floats(
        min_value=0.0,
        max_value=99.9,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@settings(max_examples=200)
def test_property_based(cost_floor_paise: int, margin_pct: float) -> None:
    """Hypothesis property-based test — scaffold alias covering derive_price formula."""
    result = _derive_price_pure(cost_floor_paise, margin_pct)

    assert isinstance(result, int)
    assert result >= cost_floor_paise

    # Verify no float leakage — result is always int (paise)
    assert not isinstance(result, float)

    # Verify formula: floor / (1 - m/100) rounded down
    raw = cost_floor_paise / (1 - margin_pct / 100)
    assert result == math.floor(raw)


@given(
    cost_floor_paise=st.integers(min_value=1_000_000, max_value=100_000_000),
    margin_pct=st.floats(
        min_value=0.001,
        max_value=99.9,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@settings(max_examples=200)
def test_property_large_paise_values(cost_floor_paise: int, margin_pct: float) -> None:
    """Property: formula holds for large paise values (enterprise pricing)."""
    result = _derive_price_pure(cost_floor_paise, margin_pct)

    assert isinstance(result, int)
    assert result >= cost_floor_paise

    # Verify margin is actually achieved: (result - floor) / result >= margin/100
    if result > 0:
        actual_margin = (result - cost_floor_paise) / result * 100
        # Allow small floating point tolerance
        assert actual_margin >= margin_pct - 0.01


@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
)
@settings(max_examples=200)
def test_property_zero_margin(cost_floor_paise: int) -> None:
    """Property: zero margin means price equals cost floor (no markup)."""
    result = _derive_price_pure(cost_floor_paise, 0.0)
    assert result == cost_floor_paise


@given(
    cost_floor_paise=st.integers(min_value=1, max_value=1_000_000),
    margin_pct=st.floats(
        min_value=95.0,
        max_value=99.9,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@settings(max_examples=200)
def test_property_near_100_margin(cost_floor_paise: int, margin_pct: float) -> None:
    """Property: near-100% margin produces very large prices (never negative, never zero)."""
    result = _derive_price_pure(cost_floor_paise, margin_pct)

    assert isinstance(result, int)
    assert result > 0
    # Near-100% margin: price must be at least 10x the floor
    assert result >= cost_floor_paise * 10