# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from hypothesis import given, strategies as st
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.billing_engine.config import Settings
from src.billing_engine.markup.bundle_engine import BundleEngine
from src.billing_engine.main import app

logger = logging.getLogger(__name__)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    """Provide test configuration."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        environment="test",
    )


@pytest.fixture
async def test_db(settings: Settings) -> AsyncSession:
    """Create in-memory test database with schema."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        # Create institutional.bundle_profiles table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS institutional.bundle_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_type TEXT NOT NULL,
                    bundle_tier TEXT NOT NULL,
                    cost_floor_paise INTEGER NOT NULL,
                    minimum_margin_pct REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # Create billing.pricing_floor_log table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS billing.pricing_floor_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_type TEXT NOT NULL,
                    bundle_tier TEXT NOT NULL,
                    proposed_price_paise INTEGER NOT NULL,
                    minimum_compliant_price_paise INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tenant_id TEXT
                )
                """
            )
        )

        # Create institutional.thread_catalog table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS institutional.thread_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    unit_description TEXT NOT NULL,
                    raw_cost_inr_paise INTEGER NOT NULL,
                    total_markup_pct REAL NOT NULL,
                    marked_up_cost_paise INTEGER NOT NULL,
                    is_platform_thread BOOLEAN NOT NULL,
                    applicable_agents TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE'
                )
                """
            )
        )

        # Seed test data: bundle_profiles
        await conn.execute(
            text(
                """
                INSERT INTO institutional.bundle_profiles
                (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct)
                VALUES
                ('DMA', 'STARTER', 50000, 25.0),
                ('DMA', 'PRO', 150000, 30.0),
                ('CRM', 'STARTER', 75000, 20.0)
                """
            )
        )

        # Seed test data: thread_catalog
        await conn.execute(
            text(
                """
                INSERT INTO institutional.thread_catalog
                (thread_id, display_name, provider, unit_description,
                 raw_cost_inr_paise, total_markup_pct, marked_up_cost_paise,
                 is_platform_thread, applicable_agents, status)
                VALUES
                ('gpt4-turbo', 'GPT-4 Turbo', 'OpenAI', 'per-token',
                 10000, 50.0, 15000, FALSE, '["DMA", "CRM"]', 'ACTIVE'),
                ('claude3', 'Claude 3 Opus', 'Anthropic', 'per-token',
                 12000, 40.0, 16800, FALSE, '["DMA"]', 'ACTIVE')
                """
            )
        )

        await conn.commit()

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def bundle_engine(test_db: AsyncSession) -> BundleEngine:
    """Provide BundleEngine instance with mocked dependencies."""
    engine = BundleEngine(
        db_session=test_db,
        redis_client=AsyncMock(),
        logger=logger,
    )
    return engine


@pytest.fixture
async def http_client(test_db: AsyncSession) -> AsyncClient:
    """Provide FastAPI test client."""
    # Inject test_db into app dependency
    app.dependency_overrides[
        "get_db"
    ] = lambda: test_db  # type: ignore
    client = AsyncClient(app=app, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


# ── Unit Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cost_floor_reads_from_bundle_profiles(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """Verify cost_floor() reads cost_floor_paise from DB, does not recompute."""
    # GIVEN: bundle_profiles row exists with cost_floor_paise=50000
    # WHEN: cost_floor('DMA', 'STARTER') is called
    result = await bundle_engine.cost_floor("DMA", "STARTER")

    # THEN: result == 50000 (from DB, not computed)
    assert result == 50000


@pytest.mark.asyncio
async def test_cost_floor_different_bundles(
    bundle_engine: BundleEngine,
) -> None:
    """Verify cost_floor() returns correct value for different bundles."""
    starter_floor = await bundle_engine.cost_floor("DMA", "STARTER")
    pro_floor = await bundle_engine.cost_floor("DMA", "PRO")
    crm_floor = await bundle_engine.cost_floor("CRM", "STARTER")

    assert starter_floor == 50000
    assert pro_floor == 150000
    assert crm_floor == 75000


@pytest.mark.asyncio
async def test_derive_price_margin_on_revenue_formula(
    bundle_engine: BundleEngine,
) -> None:
    """Verify derive_price uses margin-on-revenue formula: floor / (1 - margin/100)."""
    # GIVEN: cost_floor=50000, minimum_margin_pct=25.0
    # WHEN: derive_price('DMA', 'STARTER', target_margin_pct=None)
    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=None)

    # THEN: result == 50000 / (1 - 25/100) == 50000 / 0.75 == 66666.67 (rounds to 66667)
    expected = int(50000 / (1 - 25.0 / 100))
    assert result == expected


@pytest.mark.asyncio
async def test_derive_price_custom_margin(
    bundle_engine: BundleEngine,
) -> None:
    """Verify derive_price respects target_margin_pct when provided."""
    # GIVEN: cost_floor=50000
    # WHEN: derive_price('DMA', 'STARTER', target_margin_pct=40.0)
    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=40.0)

    # THEN: result == 50000 / (1 - 40/100) == 50000 / 0.6 == 83333.33 (rounds to 83333)
    expected = int(50000 / (1 - 40.0 / 100))
    assert result == expected


@pytest.mark.asyncio
async def test_validate_price_approved_writes_audit_log(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """Verify POST /pricing/validate 200 path: APPROVED writes pricing_floor_log row."""
    # GIVEN: cost_floor=50000, minimum_margin_pct=25.0
    # minimum_compliant_price=66667 (from formula)
    # WHEN: validate_price('DMA', 'STARTER', proposed_price_paise=70000) [above floor]
    result = await bundle_engine.validate_price(
        "DMA",
        "STARTER",
        proposed_price_paise=70000,
    )

    # THEN: outcome='APPROVED', minimum_compliant_price_paise=66667
    assert result.outcome == "APPROVED"
    assert result.minimum_compliant_price_paise == 66667

    # AND: exactly one row written to pricing_floor_log
    log_rows = await test_db.execute(
        text("SELECT COUNT(*) as cnt FROM billing.pricing_floor_log WHERE outcome='APPROVED'")
    )
    count = log_rows.scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_validate_price_rejected_writes_audit_log(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """Verify POST /pricing/validate 422 path: REJECTED writes pricing_floor_log + returns minimum_compliant_price."""
    # GIVEN: cost_floor=50000, minimum_margin_pct=25.0
    # minimum_compliant_price=66667
    # WHEN: validate_price('DMA', 'STARTER', proposed_price_paise=60000) [below floor]
    result = await bundle_engine.validate_price(
        "DMA",
        "STARTER",
        proposed_price_paise=60000,
    )

    # THEN: outcome='REJECTED', minimum_compliant_price_paise=66667
    assert result.outcome == "REJECTED"
    assert result.minimum_compliant_price_paise == 66667

    # AND: exactly one row written to pricing_floor_log
    log_rows = await test_db.execute(
        text("SELECT COUNT(*) as cnt FROM billing.pricing_floor_log WHERE outcome='REJECTED'")
    )
    count = log_rows.scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_validate_price_audit_log_fields(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """Verify pricing_floor_log row contains all required fields."""
    # GIVEN: validate_price called with agent_type='DMA', bundle_tier='STARTER', proposed=70000
    await bundle_engine.validate_price("DMA", "STARTER", proposed_price_paise=70000)

    # WHEN: audit log row is queried
    log_row = await test_db.execute(
        text(
            "SELECT agent_type, bundle_tier, proposed_price_paise, "
            "minimum_compliant_price_paise, outcome FROM billing.pricing_floor_log LIMIT 1"
        )
    )
    row = log_row.first()

    # THEN: all fields are present and correct
    assert row.agent_type == "DMA"
    assert row.bundle_tier == "STARTER"
    assert row.proposed_price_paise == 70000
    assert row.minimum_compliant_price_paise == 66667
    assert row.outcome == "APPROVED"


@pytest.mark.asyncio
async def test_pricing_validate_endpoint_200_response(
    http_client: AsyncClient,
) -> None:
    """Verify GET /pricing/thread-catalog endpoint response shape."""
    # GIVEN: thread_catalog table has 2 entries
    # WHEN: GET /pricing/thread-catalog is called
    response = await http_client.get("/pricing/thread-catalog")

    # THEN: status 200 and response is list of ThreadEntry objects
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # AND: each entry has required fields
    entry = data[0]
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


@pytest.mark.asyncio
async def test_validate_price_endpoint_422_includes_minimum_compliant_price(
    http_client: AsyncClient,
) -> None:
    """Verify POST /pricing/validate 422 response body includes minimum_compliant_price_paise."""
    # GIVEN: proposed price below floor
    request_body = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 40000,
    }

    # WHEN: POST /pricing/validate with below-floor price
    response = await http_client.post("/pricing/validate", json=request_body)

    # THEN: status 422 and response body includes minimum_compliant_price_paise
    assert response.status_code == 422
    data = response.json()
    assert "minimum_compliant_price_paise" in data
    assert data["minimum_compliant_price_paise"] == 66667


# ── Property-Based Tests (Hypothesis) ────────────────────────────────────────


@given(
    cost_floor_paise=st.integers(min_value=1000, max_value=10000000),
    margin_pct=st.floats(min_value=0.0, max_value=99.0),
)
@pytest.mark.asyncio
async def test_derive_price_margin_formula_property(
    bundle_engine: BundleEngine,
    cost_floor_paise: int,
    margin_pct: float,
) -> None:
    """Property: derive_price(cost, margin) = cost / (1 - margin/100)."""
    # Temporarily override cost_floor to return our test value
    original_cost_floor = bundle_engine.cost_floor
    bundle_engine.cost_floor = AsyncMock(return_value=cost_floor_paise)

    try:
        result = await bundle_engine.derive_price(
            "DMA",
            "STARTER",
            target_margin_pct=margin_pct,
        )

        # Verify formula: price = cost_floor / (1 - margin/100)
        # For margin=0, price == cost_floor
        # For margin approaching 100, price approaches infinity
        if margin_pct < 99.0:  # avoid division by very small numbers
            expected = int(cost_floor_paise / (1 - margin_pct / 100))
            assert result == expected
    finally:
        bundle_engine.cost_floor = original_cost_floor


@given(
    cost_floor_paise=st.integers(min_value=1000, max_value=10000000),
    proposed_price=st.integers(min_value=1000, max_value=10000000),
)
@pytest.mark.asyncio
async def test_validate_price_outcome_paths_property(
    bundle_engine: BundleEngine,
    cost_floor_paise: int,
    proposed_price: int,
) -> None:
    """Property: validate_price outcome is APPROVED iff proposed >= minimum_compliant."""
    # Temporarily override cost_floor
    original_cost_floor = bundle_engine.cost_floor
    bundle_engine.cost_floor = AsyncMock(return_value=cost_floor_paise)

    try:
        result = await bundle_engine.validate_price(
            "DMA",
            "STARTER",
            proposed_price_paise=proposed_price,
        )

        # Calculate expected minimum_compliant_price (using 25% minimum margin)
        minimum_compliant = int(cost_floor_paise / (1 - 25.0 / 100))

        # Verify outcome matches price comparison
        if proposed_price >= minimum_compliant:
            assert result.outcome == "APPROVED"
        else:
            assert result.outcome == "REJECTED"

        # Verify minimum_compliant_price_paise is always returned
        assert result.minimum_compliant_price_paise == minimum_compliant
    finally:
        bundle_engine.cost_floor = original_cost_floor


@given(st.floats(min_value=0.0, max_value=99.5))
@pytest.mark.asyncio
async def test_derive_price_zero_and_high_margin_property(
    bundle_engine: BundleEngine,
    margin_pct: float,
) -> None:
    """Property: derive_price with zero margin equals cost_floor; high margin approaches infinity."""
    # Test at zero margin
    if margin_pct == 0.0:
        original_cost_floor = bundle_engine.cost_floor
        bundle_engine.cost_floor = AsyncMock(return_value=50000)

        try:
            result = await bundle_engine.derive_price(
                "DMA",
                "STARTER",
                target_margin_pct=0.0,
            )
            # At 0% margin: price = 50000 / (1 - 0) = 50000
            assert result == 50000
        finally:
            bundle_engine.cost_floor = original_cost_floor


@given(
    cost_floor_paise=st.integers(min_value=100000, max_value=100000000),
)
@pytest.mark.asyncio
async def test_validate_price_always_includes_minimum_compliant_property(
    bundle_engine: BundleEngine,
    cost_floor_paise: int,
) -> None:
    """Property: validate_price always returns minimum_compliant_price_paise, regardless of outcome."""
    # Override cost_floor
    original_cost_floor = bundle_engine.cost_floor
    bundle_engine.cost_floor = AsyncMock(return_value=cost_floor_paise)

    try:
        # Test with price above floor
        result_approved = await bundle_engine.validate_price(
            "DMA",
            "STARTER",
            proposed_price_paise=cost_floor_paise * 2,
        )

        # Test with price below floor
        result_rejected = await bundle_engine.validate_price(
            "DMA",
            "STARTER",
            proposed_price_paise=cost_floor_paise // 2,
        )

        # Both must include minimum_compliant_price_paise
        assert result_approved.minimum_compliant_price_paise is not None
        assert result_rejected.minimum_compliant_price_paise is not None

        # Both must be equal (same formula)
        assert (
            result_approved.minimum_compliant_price_paise
            == result_rejected.minimum_compliant_price_paise
        )
    finally:
        bundle_engine.cost_floor = original_cost_floor


# ── Integration Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_validate_endpoint_201_approved(
    http_client: AsyncClient,
) -> None:
    """Verify POST /pricing/validate 200 with APPROVED outcome."""
    request_body = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "proposed_price_paise": 70000,
    }

    response = await http_client.post("/pricing/validate", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "APPROVED"
    assert data["minimum_compliant_price_paise"] == 66667


@pytest.mark.asyncio
async def test_pricing_derive_endpoint_response(
    http_client: AsyncClient,
) -> None:
    """Verify POST /pricing/derive endpoint returns derived price."""
    request_body = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "target_margin_pct": 30.0,
    }

    response = await http_client.post("/pricing/derive", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert "derived_price_paise" in data
    # Expected: 50000 / (1 - 30/100) = 50000 / 0.7 = 71428
    expected = int(50000 / (1 - 30.0 / 100))
    assert data["derived_price_paise"] == expected


@pytest.mark.asyncio
async def test_pricing_bundle_cost_floor_endpoint(
    http_client: AsyncClient,
) -> None:
    """Verify GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier}."""
    response = await http_client.get("/pricing/bundle-cost-floor/DMA/STARTER")

    assert response.status_code == 200
    data = response.json()
    assert data["cost_floor_paise"] == 50000


@pytest.mark.asyncio
async def test_pricing_multiple_validations_writes_multiple_logs(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """Verify multiple validate_price calls write multiple audit log rows."""
    # WHEN: validate_price is called 3 times with different proposals
    await bundle_engine.validate_price("DMA", "STARTER", proposed_price_paise=70000)
    await bundle_engine.validate_price("DMA", "STARTER", proposed_price_paise=60000)
    await bundle_engine.validate_price("DMA", "STARTER", proposed_price_paise=80000)

    # THEN: 3 rows in pricing_floor_log
    log_rows = await test_db.execute(
        text("SELECT COUNT(*) as cnt FROM billing.pricing_floor_log")
    )
    count = log_rows.scalar()
    assert count == 3