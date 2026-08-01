# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, given, settings as hypothesis_settings, strategies as st
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
    mock_redis = AsyncMock()
    engine = BundleEngine(
        db_session=test_db,
        redis_client=mock_redis,
        logger=logger,
    )
    return engine


@pytest.fixture
async def http_client(test_db: AsyncSession) -> AsyncClient:
    """Provide FastAPI test client with test DB injected."""

    async def override_get_db() -> AsyncSession:
        return test_db

    app.dependency_overrides["get_db"] = override_get_db
    client = AsyncClient(app=app, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


# ── Unit Tests: cost_floor ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cost_floor_reads_from_bundle_profiles(
    bundle_engine: BundleEngine,
) -> None:
    """C-097: cost_floor() reads cost_floor_paise from DB, does not recompute."""
    result = await bundle_engine.cost_floor("DMA", "STARTER")
    assert result == 50000, "cost_floor must read cost_floor_paise from bundle_profiles"


@pytest.mark.asyncio
async def test_cost_floor_different_tiers(
    bundle_engine: BundleEngine,
) -> None:
    """C-097: cost_floor returns correct value for different bundle tiers."""
    starter = await bundle_engine.cost_floor("DMA", "STARTER")
    pro = await bundle_engine.cost_floor("DMA", "PRO")
    crm = await bundle_engine.cost_floor("CRM", "STARTER")

    assert starter == 50000
    assert pro == 150000
    assert crm == 75000


# ── Unit Tests: derive_price ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_derive_price_formula_with_explicit_margin(
    bundle_engine: BundleEngine,
) -> None:
    """C-089: derive_price uses margin-on-revenue formula: floor / (1 - margin/100)."""
    margin_pct = 25.0

    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=margin_pct)

    # Formula: floor / (1 - margin/100) = 50000 / (1 - 0.25) = 50000 / 0.75 = 66666.67
    expected = int(50000 / (1 - margin_pct / 100))
    assert result == expected, f"derive_price formula error: {result} != {expected}"


@pytest.mark.asyncio
async def test_derive_price_uses_minimum_margin_when_none(
    bundle_engine: BundleEngine,
) -> None:
    """C-089: derive_price uses bundle_profiles.minimum_margin_pct when target_margin_pct is None."""
    # DMA STARTER has minimum_margin_pct = 25.0
    result = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=None)

    cost_floor = 50000
    minimum_margin = 25.0
    expected = int(cost_floor / (1 - minimum_margin / 100))

    assert result == expected


@pytest.mark.asyncio
async def test_derive_price_pro_tier(
    bundle_engine: BundleEngine,
) -> None:
    """C-089: derive_price works correctly for PRO tier with higher margin."""
    # DMA PRO has cost_floor_paise=150000, minimum_margin_pct=30.0
    result = await bundle_engine.derive_price("DMA", "PRO", target_margin_pct=None)

    expected = int(150000 / (1 - 30.0 / 100))
    assert result == expected


# ── Unit Tests: validate_price (Happy Path - APPROVED) ──────────────────────


@pytest.mark.asyncio
async def test_validate_price_approved_compliance(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """C-089: validate_price returns APPROVED when price >= minimum_compliant_price."""
    cost_floor = 50000
    minimum_margin = 25.0
    minimum_compliant = int(cost_floor / (1 - minimum_margin / 100))  # 66666
    proposed = minimum_compliant + 1000  # price above floor

    result = await bundle_engine.validate_price(
        "DMA",
        "STARTER",
        proposed,
    )

    assert result.outcome == "APPROVED"
    assert result.minimum_compliant_price_paise == minimum_compliant
    assert result.proposed_price_paise == proposed

    # C-059: Verify audit log row written
    audit_rows = await test_db.execute(
        text(
            "SELECT outcome, proposed_price_paise, minimum_compliant_price_paise "
            "FROM billing.pricing_floor_log WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'"
        )
    )
    rows = audit_rows.fetchall()
    assert len(rows) == 1
    assert rows[0].outcome == "APPROVED"


@pytest.mark.asyncio
async def test_validate_price_rejected_below_floor(
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """C-089: validate_price returns REJECTED when price < minimum_compliant_price."""
    cost_floor = 50000
    minimum_margin = 25.0
    minimum_compliant = int(cost_floor / (1 - minimum_margin / 100))
    proposed = minimum_compliant - 1000  # price below floor

    result = await bundle_engine.validate_price(
        "DMA",
        "STARTER",
        proposed,
    )

    assert result.outcome == "REJECTED"
    assert result.minimum_compliant_price_paise == minimum_compliant
    assert result.proposed_price_paise == proposed

    # C-059: Verify audit log row written on rejection
    audit_rows = await test_db.execute(
        text(
            "SELECT outcome, proposed_price_paise FROM billing.pricing_floor_log "
            "WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'"
        )
    )
    rows = audit_rows.fetchall()
    assert len(rows) == 1
    assert rows[0].outcome == "REJECTED"


# ── Integration Tests: FastAPI Router ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_thread_catalog_response_shape(
    http_client: AsyncClient,
) -> None:
    """Response shape for GET /pricing/thread-catalog."""
    response = await http_client.get("/pricing/thread-catalog")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    if len(data) > 0:
        catalog_item = data[0]
        assert "thread_id" in catalog_item
        assert "display_name" in catalog_item
        assert "provider" in catalog_item
        assert "unit_description" in catalog_item
        assert "raw_cost_inr_paise" in catalog_item
        assert "total_markup_pct" in catalog_item
        assert "marked_up_cost_paise" in catalog_item


@pytest.mark.asyncio
async def test_post_pricing_validate_approved_200(
    http_client: AsyncClient,
    test_db: AsyncSession,
) -> None:
    """POST /pricing/validate returns 200 + APPROVED outcome + audit log."""
    cost_floor = 50000
    minimum_margin = 25.0
    minimum_compliant = int(cost_floor / (1 - minimum_margin / 100))
    proposed = minimum_compliant + 5000

    payload = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed,
    }

    response = await http_client.post("/pricing/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "APPROVED"
    assert data["minimum_compliant_price_paise"] == minimum_compliant

    # Verify audit log
    audit = await test_db.execute(
        text(
            "SELECT outcome FROM billing.pricing_floor_log "
            "WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER' AND outcome = 'APPROVED'"
        )
    )
    assert audit.fetchone() is not None


@pytest.mark.asyncio
async def test_post_pricing_validate_rejected_422(
    http_client: AsyncClient,
    test_db: AsyncSession,
) -> None:
    """POST /pricing/validate returns 422 + body includes minimum_compliant_price_paise + audit log."""
    cost_floor = 50000
    minimum_margin = 25.0
    minimum_compliant = int(cost_floor / (1 - minimum_margin / 100))
    proposed = minimum_compliant - 10000  # below floor

    payload = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "proposed_price_paise": proposed,
    }

    response = await http_client.post("/pricing/validate", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["outcome"] == "REJECTED"
    assert "minimum_compliant_price_paise" in data
    assert data["minimum_compliant_price_paise"] == minimum_compliant

    # Verify audit log
    audit = await test_db.execute(
        text(
            "SELECT outcome FROM billing.pricing_floor_log "
            "WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER' AND outcome = 'REJECTED'"
        )
    )
    assert audit.fetchone() is not None


@pytest.mark.asyncio
async def test_get_bundle_cost_floor_endpoint(
    http_client: AsyncClient,
) -> None:
    """GET /pricing/bundle-cost-floor/{agent_type}/{bundle_tier} returns cost floor in paise."""
    response = await http_client.get("/pricing/bundle-cost-floor/DMA/STARTER")

    assert response.status_code == 200
    data = response.json()
    assert "cost_floor_paise" in data
    assert data["cost_floor_paise"] == 50000


@pytest.mark.asyncio
async def test_post_pricing_derive_endpoint(
    http_client: AsyncClient,
) -> None:
    """POST /pricing/derive returns derived price using formula."""
    payload = {
        "agent_type": "DMA",
        "bundle_tier": "STARTER",
        "target_margin_pct": 25.0,
    }

    response = await http_client.post("/pricing/derive", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "derived_price_paise" in data
    assert isinstance(data["derived_price_paise"], int)

    # Verify formula: 50000 / (1 - 0.25) = 66666
    expected = int(50000 / (1 - 25.0 / 100))
    assert data["derived_price_paise"] == expected


# ── Property-Based Tests: Hypothesis ─────────────────────────────────────────


@hypothesis_settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=100,
)
@given(
    cost_floor=st.integers(min_value=1000, max_value=10_000_000),
    margin_pct=st.floats(min_value=0.0, max_value=99.9),
)
@pytest.mark.asyncio
async def test_derive_price_property_zero_to_99_margin(
    cost_floor: int,
    margin_pct: float,
    bundle_engine: BundleEngine,
) -> None:
    """C-097: derive_price formula holds for all valid margin percentages."""
    # Derived price must always be >= cost_floor (margin pushes price up)
    result = await bundle_engine.derive_price(
        "DMA", "STARTER", target_margin_pct=margin_pct
    )

    # When margin is 0%, price = cost_floor
    if margin_pct == 0.0:
        assert result == cost_floor
    else:
        # When margin > 0%, price > cost_floor
        assert result > cost_floor

    # Verify formula: derived = floor / (1 - margin/100)
    expected = int(cost_floor / (1 - margin_pct / 100))
    assert result == expected


@hypothesis_settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=100,
)
@given(
    proposed_paise=st.integers(min_value=1000, max_value=10_000_000),
)
@pytest.mark.asyncio
async def test_validate_price_property_all_outcomes(
    proposed_paise: int,
    bundle_engine: BundleEngine,
    test_db: AsyncSession,
) -> None:
    """C-097: validate_price returns either APPROVED or REJECTED for any proposed price."""
    cost_floor = 50000
    minimum_margin = 25.0
    minimum_compliant = int(cost_floor / (1 - minimum_margin / 100))

    result = await bundle_engine.validate_price(
        "DMA",
        "STARTER",
        proposed_paise,
    )

    # Result must be one of the valid outcomes
    assert result.outcome in ["APPROVED", "REJECTED"]

    # minimum_compliant_price_paise is always present
    assert result.minimum_compliant_price_paise == minimum_compliant

    # Outcome logic must match price comparison
    if proposed_paise >= minimum_compliant:
        assert result.outcome == "APPROVED"
    else:
        assert result.outcome == "REJECTED"

    # C-059: Every outcome must produce an audit log
    audit = await test_db.execute(
        text(
            "SELECT outcome FROM billing.pricing_floor_log "
            "WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER' "
            "ORDER BY id DESC LIMIT 1"
        )
    )
    audit_row = audit.fetchone()
    assert audit_row is not None
    assert audit_row.outcome == result.outcome


@hypothesis_settings(max_examples=50)
@given(
    cost_floor=st.integers(min_value=10000, max_value=1_000_000),
    margin_pct=st.floats(min_value=10.0, max_value=99.0),
)
@pytest.mark.asyncio
async def test_derive_price_formula_precision(
    cost_floor: int,
    margin_pct: float,
    bundle_engine: BundleEngine,
) -> None:
    """C-097: Formula precision — no rounding errors that violate C-089 margin floor."""
    # Mock a temporary bundle profile with the generated values
    # For property testing, we use the STARTER tier but verify math
    result = await bundle_engine.derive_price(
        "DMA", "STARTER", target_margin_pct=margin_pct
    )

    # Verify inverse: if we know the derived price and margin,
    # cost_floor should be approximately recoverable
    # actual_margin = (derived - cost) / derived * 100
    # This is to ensure formula consistency
    expected = int(cost_floor / (1 - margin_pct / 100))
    assert result == expected

    # Derived price must be greater than or equal to cost_floor
    assert result >= cost_floor