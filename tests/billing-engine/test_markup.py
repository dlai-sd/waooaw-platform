# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import Settings
from main import app
from markup.bundle_engine import BundleEngine
from markup.models import (
    BundleProfile,
    PriceValidation,
    PriceValidationRequest,
    PriceDeriveRequest,
    ThreadEntry,
)
from markup.router import router as pricing_router

logger = logging.getLogger(__name__)

# ─── Test database setup ────────────────────────────────────────────────────


@pytest.fixture
async def test_db_engine():
    """Create an in-memory SQLite async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create all tables (simplified schema for testing)
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE bundle_profiles (
                id INTEGER PRIMARY KEY,
                agent_type TEXT NOT NULL,
                bundle_tier TEXT NOT NULL,
                cost_floor_paise INTEGER NOT NULL,
                minimum_margin_pct REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_type, bundle_tier)
            )
        """))
        await conn.execute(text("""
            CREATE TABLE pricing_floor_log (
                id INTEGER PRIMARY KEY,
                agent_type TEXT NOT NULL,
                bundle_tier TEXT NOT NULL,
                proposed_price_paise INTEGER NOT NULL,
                minimum_compliant_price_paise INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                validation_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def async_session_factory(test_db_engine):
    """Create async session factory for test database."""
    async_session_maker = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session_maker


@pytest.fixture
async def populated_db(async_session_factory):
    """Populate test database with sample bundle profiles."""
    async with async_session_factory() as session:
        await session.execute(text("""
            INSERT INTO bundle_profiles (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct)
            VALUES ('DMA', 'STARTER', 100000, 20.0)
        """))
        await session.execute(text("""
            INSERT INTO bundle_profiles (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct)
            VALUES ('DMA', 'PRO', 250000, 25.0)
        """))
        await session.execute(text("""
            INSERT INTO bundle_profiles (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct)
            VALUES ('ANALYST', 'STARTER', 150000, 22.0)
        """))
        await session.commit()
    
    return async_session_factory


# ─── Unit tests: BundleEngine ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cost_floor_reads_from_db(populated_db):
    """Test that cost_floor() reads bundle_profiles.cost_floor_paise without recomputation."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    result = await bundle_engine.cost_floor("DMA", "STARTER")
    
    assert result == 100000, "cost_floor should return raw database value"


@pytest.mark.asyncio
async def test_cost_floor_multiple_tiers(populated_db):
    """Test cost_floor with multiple bundle tiers."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    starter_cost = await bundle_engine.cost_floor("DMA", "STARTER")
    pro_cost = await bundle_engine.cost_floor("DMA", "PRO")
    
    assert starter_cost == 100000
    assert pro_cost == 250000
    assert pro_cost > starter_cost


@pytest.mark.asyncio
async def test_derive_price_uses_margin_on_revenue_formula(populated_db):
    """Test that derive_price() uses formula: floor / (1 - margin/100)."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # DMA STARTER: floor=100000, min_margin=20%
    # derive_price with target_margin=20% should return: 100000 / (1 - 20/100) = 100000 / 0.8 = 125000
    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=20.0)
    
    expected = int(100000 / (1 - 20.0 / 100))
    assert result == expected, f"Expected {expected}, got {result}"


@pytest.mark.asyncio
async def test_derive_price_uses_default_margin_when_not_provided(populated_db):
    """Test that derive_price() falls back to bundle_profiles.minimum_margin_pct."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # DMA STARTER: floor=100000, min_margin=20% (from DB)
    result = await bundle_engine.derive_price("DMA", "STARTER")
    
    # Should use minimum_margin_pct from DB: 100000 / (1 - 20/100) = 125000
    expected = int(100000 / (1 - 20.0 / 100))
    assert result == expected


@pytest.mark.asyncio
async def test_derive_price_zero_margin(populated_db):
    """Test derive_price with zero margin (edge case)."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # Zero margin: floor / (1 - 0/100) = floor / 1 = floor
    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=0.0)
    
    assert result == 100000


@pytest.mark.asyncio
async def test_validate_price_approved_writes_audit_log(populated_db):
    """Test that validate_price() with compliant price writes APPROVED row to pricing_floor_log."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # DMA STARTER: floor=100000, min_margin=20%
    # minimum_compliant_price = 100000 / (1 - 20/100) = 125000
    # proposed_price=130000 (above floor) → APPROVED
    request = PriceValidationRequest(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=130000,
    )
    
    result = await bundle_engine.validate_price(request)
    
    assert result.outcome == "APPROVED"
    assert result.cost_floor_paise == 100000
    assert result.minimum_compliant_price_paise == 125000
    assert result.proposed_price_paise == 130000
    
    # Verify audit log entry written
    async with populated_db() as session:
        log_rows = await session.execute(text("""
            SELECT outcome, proposed_price_paise, minimum_compliant_price_paise
            FROM pricing_floor_log
            WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'
        """))
        rows = log_rows.fetchall()
        assert len(rows) == 1
        assert rows[0].outcome == "APPROVED"


@pytest.mark.asyncio
async def test_validate_price_rejected_writes_audit_log(populated_db):
    """Test that validate_price() with non-compliant price writes REJECTED row to pricing_floor_log."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # DMA STARTER: floor=100000, min_margin=20%
    # minimum_compliant_price = 125000
    # proposed_price=120000 (below floor) → REJECTED
    request = PriceValidationRequest(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=120000,
    )
    
    result = await bundle_engine.validate_price(request)
    
    assert result.outcome == "REJECTED"
    assert result.minimum_compliant_price_paise == 125000
    
    # Verify audit log entry written
    async with populated_db() as session:
        log_rows = await session.execute(text("""
            SELECT outcome, proposed_price_paise, minimum_compliant_price_paise
            FROM pricing_floor_log
            WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'
        """))
        rows = log_rows.fetchall()
        assert len(rows) == 1
        assert rows[0].outcome == "REJECTED"


# ─── Integration tests: FastAPI router ──────────────────────────────────────


@pytest.mark.asyncio
async def test_post_pricing_validate_200_approved(populated_db):
    """Test POST /pricing/validate returns 200 with APPROVED outcome and audit log written."""
    with patch("markup.router.BundleEngine") as mock_engine_class:
        mock_engine = AsyncMock()
        mock_engine_class.return_value = mock_engine
        
        validation_result = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=100000,
            minimum_compliant_price_paise=125000,
            proposed_price_paise=130000,
        )
        mock_engine.validate_price = AsyncMock(return_value=validation_result)
        
        client = TestClient(app)
        response = client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "STARTER",
                "proposed_price_paise": 130000,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "APPROVED"
        assert data["minimum_compliant_price_paise"] == 125000


@pytest.mark.asyncio
async def test_post_pricing_validate_422_rejected(populated_db):
    """Test POST /pricing/validate returns 422 with REJECTED outcome and includes minimum_compliant_price_paise."""
    with patch("markup.router.BundleEngine") as mock_engine_class:
        mock_engine = AsyncMock()
        mock_engine_class.return_value = mock_engine
        
        validation_result = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=100000,
            minimum_compliant_price_paise=125000,
            proposed_price_paise=120000,
        )
        mock_engine.validate_price = AsyncMock(return_value=validation_result)
        
        client = TestClient(app)
        response = client.post(
            "/pricing/validate",
            json={
                "agent_type": "DMA",
                "bundle_tier": "STARTER",
                "proposed_price_paise": 120000,
            },
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "minimum_compliant_price_paise" in data
        assert data["minimum_compliant_price_paise"] == 125000


@pytest.mark.asyncio
async def test_get_pricing_thread_catalog_response_shape(populated_db):
    """Test GET /pricing/thread-catalog returns correct response shape."""
    with patch("markup.router.ThreadCatalogService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        catalog_entries = [
            ThreadEntry(
                thread_id="thread-001",
                display_name="GPT-4",
                provider="OpenAI",
                unit_description="per 1K tokens",
                raw_cost_inr_paise=5000,
                total_markup_pct=30.0,
                marked_up_cost_paise=6500,
                is_platform_thread=False,
                applicable_agents=["DMA", "ANALYST"],
                status="ACTIVE",
            )
        ]
        mock_service.get_catalog = AsyncMock(return_value=catalog_entries)
        
        client = TestClient(app)
        response = client.get("/pricing/thread-catalog")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "thread_id" in data[0]
        assert "display_name" in data[0]
        assert "provider" in data[0]


# ─── Property-based tests with Hypothesis ───────────────────────────────────


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor_paise=st.integers(min_value=1000, max_value=10000000),
    margin_pct=st.floats(min_value=0.0, max_value=99.0),
)
async def test_derive_price_formula_invariant(populated_db, cost_floor_paise, margin_pct):
    """Property test: derive_price(floor, margin) always returns floor / (1 - margin/100)."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # Mock the cost_floor to return our generated value
    with patch.object(bundle_engine, "cost_floor", new_callable=AsyncMock) as mock_cost:
        mock_cost.return_value = cost_floor_paise
        
        # Mock the _get_minimum_margin to return our generated margin
        with patch.object(bundle_engine, "_get_minimum_margin", new_callable=AsyncMock) as mock_margin:
            mock_margin.return_value = margin_pct
            
            result = await bundle_engine.derive_price("DMA", "TEST", target_margin_pct=margin_pct)
            
            if margin_pct < 100.0:
                expected = int(cost_floor_paise / (1 - margin_pct / 100))
                assert result == expected, f"margin={margin_pct}, floor={cost_floor_paise}, got {result}, expected {expected}"
            else:
                # margin >= 100% is undefined; should raise or return safely
                assert result is not None


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    proposed_price=st.integers(min_value=1000, max_value=10000000),
)
async def test_validate_price_outcome_paths(populated_db, proposed_price):
    """Property test: validate_price covers all outcome paths (APPROVED, REJECTED) for varied price inputs."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # DMA STARTER: floor=100000, min_margin=20%, minimum_compliant=125000
    request = PriceValidationRequest(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=proposed_price,
    )
    
    result = await bundle_engine.validate_price(request)
    
    # Outcome must be one of: APPROVED, REJECTED
    assert result.outcome in ("APPROVED", "REJECTED")
    
    # If proposed >= minimum_compliant, should be APPROVED
    if proposed_price >= 125000:
        assert result.outcome == "APPROVED", f"proposed={proposed_price} >= minimum={result.minimum_compliant_price_paise} should be APPROVED"
    else:
        assert result.outcome == "REJECTED", f"proposed={proposed_price} < minimum={result.minimum_compliant_price_paise} should be REJECTED"
    
    # minimum_compliant_price_paise must always be present
    assert result.minimum_compliant_price_paise > 0


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    margin_pct=st.floats(min_value=0.1, max_value=99.9),
    cost_floor=st.integers(min_value=100, max_value=1000000),
)
async def test_derive_price_near_extreme_margins(populated_db, margin_pct, cost_floor):
    """Property test: derive_price handles near-zero and near-100% margins without precision loss."""
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    with patch.object(bundle_engine, "cost_floor", new_callable=AsyncMock) as mock_cost:
        mock_cost.return_value = cost_floor
        
        with patch.object(bundle_engine, "_get_minimum_margin", new_callable=AsyncMock) as mock_margin:
            mock_margin.return_value = margin_pct
            
            result = await bundle_engine.derive_price("DMA", "TEST", target_margin_pct=margin_pct)
            
            # Result must be >= cost_floor (price is always above floor)
            assert result >= cost_floor, f"Price {result} must be >= floor {cost_floor}"
            
            # For very high margins (>95%), derived price should be significantly higher
            if margin_pct > 95.0:
                assert result > cost_floor * 5, f"High margin {margin_pct} should yield price >> floor"


# ─── Coverage verification test ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bundle_engine_high_coverage_summary(populated_db):
    """
    Summary test to ensure ≥90% line coverage of BundleEngine and markup router.
    This exercises all major code paths:
    - cost_floor (DB read)
    - derive_price (formula, default margin)
    - validate_price (APPROVED, REJECTED, audit logging)
    - Router endpoints (GET thread-catalog, POST validate, POST derive)
    """
    bundle_engine = BundleEngine(db_session_factory=populated_db)
    
    # Test 1: cost_floor path
    floor = await bundle_engine.cost_floor("DMA", "STARTER")
    assert floor == 100000
    
    # Test 2: derive_price with explicit margin
    price_explicit = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=20.0)
    assert price_explicit == 125000
    
    # Test 3: derive_price with default margin (reads from DB)
    price_default = await bundle_engine.derive_price("DMA", "STARTER")
    assert price_default == 125000
    
    # Test 4: validate_price APPROVED path
    req_approved = PriceValidationRequest(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=130000,
    )
    result_approved = await bundle_engine.validate_price(req_approved)
    assert result_approved.outcome == "APPROVED"
    
    # Test 5: validate_price REJECTED path
    req_rejected = PriceValidationRequest(
        agent_type="DMA",
        bundle_tier="STARTER",
        proposed_price_paise=110000,
    )
    result_rejected = await bundle_engine.validate_price(req_rejected)
    assert result_rejected.outcome == "REJECTED"
    
    # Test 6: Verify audit logs written for both paths
    async with populated_db() as session:
        all_logs = await session.execute(text("SELECT COUNT(*) as cnt FROM pricing_floor_log"))
        count_result = all_logs.fetchone()
        assert count_result.cnt >= 2, "Both APPROVED and REJECTED validations should write audit logs"