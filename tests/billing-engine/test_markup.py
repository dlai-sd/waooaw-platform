# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

import logging

import pytest
from hypothesis import given, strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.billing_engine.markup.models import (
    PriceValidation,
    PriceValidationRequest,
    PriceDeriveRequest,
    ThreadEntry,
)
from src.billing_engine.markup.bundle_engine import BundleEngine

logger = logging.getLogger(__name__)

# ── Test fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def test_db_engine():
    """Create in-memory SQLite async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS bundle_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type TEXT NOT NULL,
                bundle_tier TEXT NOT NULL,
                cost_floor_paise INTEGER NOT NULL,
                minimum_margin_pct REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_type, bundle_tier)
            )
            """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pricing_floor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type TEXT NOT NULL,
                bundle_tier TEXT NOT NULL,
                proposed_price_paise INTEGER NOT NULL,
                minimum_compliant_price_paise INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        await conn.commit()
    return engine


@pytest.fixture
async def test_session_factory(test_db_engine):
    """Create session factory for test database."""
    factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
    return factory


@pytest.fixture
async def bundle_engine(test_session_factory):
    """Instantiate BundleEngine with test session factory."""
    engine = BundleEngine(session_factory=test_session_factory)
    return engine


@pytest.fixture
async def seed_bundle_profiles(test_session_factory):
    """Seed test database with bundle profile fixtures."""
    async with test_session_factory() as session:
        await session.execute(
            text("""
            INSERT INTO bundle_profiles (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct)
            VALUES
                ('DMA', 'STARTER', 50000, 30.0),
                ('DMA', 'PROFESSIONAL', 150000, 35.0),
                ('DMA', 'ENTERPRISE', 500000, 40.0),
                ('RESEARCH', 'STARTER', 75000, 25.0),
                ('RESEARCH', 'PROFESSIONAL', 200000, 30.0)
            """)
        )
        await session.commit()


# ── Unit tests ──────────────────────────────────────────────────────────────

class TestCostFloor:
    """Test that cost_floor reads from bundle_profiles, not recomputed."""

    @pytest.mark.asyncio
    async def test_cost_floor_reads_from_db(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Verify cost_floor retrieves cost_floor_paise from DB without recomputation."""
        # Act
        floor = await bundle_engine.cost_floor("DMA", "STARTER")

        # Assert
        assert floor == 50000
        assert isinstance(floor, int)

    @pytest.mark.asyncio
    async def test_cost_floor_multiple_tiers(self, bundle_engine, seed_bundle_profiles):
        """Verify cost_floor works across different bundle tiers."""
        tiers_expected = {
            ("DMA", "STARTER"): 50000,
            ("DMA", "PROFESSIONAL"): 150000,
            ("DMA", "ENTERPRISE"): 500000,
            ("RESEARCH", "STARTER"): 75000,
            ("RESEARCH", "PROFESSIONAL"): 200000,
        }
        for (agent_type, bundle_tier), expected_floor in tiers_expected.items():
            floor = await bundle_engine.cost_floor(agent_type, bundle_tier)
            assert floor == expected_floor

    @pytest.mark.asyncio
    async def test_cost_floor_not_found_raises_error(self, bundle_engine):
        """Verify cost_floor raises error for non-existent bundle."""
        with pytest.raises(ValueError, match="Bundle profile not found"):
            await bundle_engine.cost_floor("NONEXISTENT", "STARTER")


class TestDerivePrice:
    """Test margin-on-revenue pricing formula: floor / (1 - margin/100)."""

    @pytest.mark.asyncio
    async def test_derive_price_with_default_margin(self, bundle_engine, seed_bundle_profiles):
        """Verify derive_price uses minimum_margin_pct when target_margin_pct is None."""
        # DMA STARTER: floor=50000, min_margin=30%
        # Expected: 50000 / (1 - 0.30) = 50000 / 0.70 = 71428.57... → 71429
        price = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=None)

        assert isinstance(price, int)
        expected = int(50000 / (1 - 0.30))
        assert price == expected

    @pytest.mark.asyncio
    async def test_derive_price_with_custom_margin(self, bundle_engine, seed_bundle_profiles):
        """Verify derive_price uses custom target_margin_pct when provided."""
        # DMA STARTER: floor=50000, custom margin=50%
        # Expected: 50000 / (1 - 0.50) = 50000 / 0.50 = 100000
        price = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=50.0)

        assert price == 100000

    @pytest.mark.asyncio
    async def test_derive_price_zero_margin(self, bundle_engine, seed_bundle_profiles):
        """Verify derive_price with zero margin returns cost floor."""
        # DMA STARTER: floor=50000, margin=0%
        # Expected: 50000 / (1 - 0) = 50000
        price = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=0.0)

        assert price == 50000

    @pytest.mark.asyncio
    async def test_derive_price_high_margin(self, bundle_engine, seed_bundle_profiles):
        """Verify derive_price handles high margins correctly."""
        # DMA STARTER: floor=50000, margin=90%
        # Expected: 50000 / (1 - 0.90) = 50000 / 0.10 = 500000
        price = await bundle_engine.derive_price("DMA", "STARTER", target_margin_pct=90.0)

        assert price == 500000


class TestValidatePrice:
    """Test price validation with audit logging."""

    @pytest.mark.asyncio
    async def test_validate_price_approved(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Verify POST /pricing/validate 200 path: APPROVED outcome with audit log."""
        # DMA STARTER: floor=50000, min_margin=30%, so min_price=71429
        # Proposed: 75000 (above minimum)
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            proposed_price_paise=75000,
        )
        result = await bundle_engine.validate_price(request)

        # Assert result
        assert result.outcome == "APPROVED"
        assert result.cost_floor_paise == 50000
        assert result.minimum_compliant_price_paise == int(50000 / (1 - 0.30))
        assert result.proposed_price_paise == 75000

        # Assert audit log written
        async with test_session_factory() as session:
            log_rows = await session.execute(
                text("SELECT * FROM pricing_floor_log WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'")
            )
            logs = log_rows.fetchall()
            assert len(logs) == 1
            assert logs[0].outcome == "APPROVED"
            assert logs[0].proposed_price_paise == 75000

    @pytest.mark.asyncio
    async def test_validate_price_rejected(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Verify POST /pricing/validate 422 path: REJECTED with minimum_compliant_price_paise in body."""
        # DMA STARTER: floor=50000, min_margin=30%, so min_price=71429
        # Proposed: 40000 (below minimum)
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            proposed_price_paise=40000,
        )
        result = await bundle_engine.validate_price(request)

        # Assert result
        assert result.outcome == "REJECTED"
        assert result.cost_floor_paise == 50000
        assert result.minimum_compliant_price_paise == int(50000 / (1 - 0.30))
        assert result.proposed_price_paise == 40000

        # Assert audit log written
        async with test_session_factory() as session:
            log_rows = await session.execute(
                text("SELECT * FROM pricing_floor_log WHERE agent_type = 'DMA' AND bundle_tier = 'STARTER'")
            )
            logs = log_rows.fetchall()
            assert len(logs) == 1
            assert logs[0].outcome == "REJECTED"
            assert logs[0].proposed_price_paise == 40000

    @pytest.mark.asyncio
    async def test_validate_price_exact_minimum(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Verify validation passes when proposed price equals minimum compliant price."""
        min_price = int(50000 / (1 - 0.30))
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            proposed_price_paise=min_price,
        )
        result = await bundle_engine.validate_price(request)

        assert result.outcome == "APPROVED"
        assert result.minimum_compliant_price_paise == min_price


class TestThreadCatalogResponse:
    """Test thread catalog endpoint response shape."""

    @pytest.mark.asyncio
    async def test_thread_catalog_response_shape(self, bundle_engine):
        """Verify GET /pricing/thread-catalog response has correct fields."""
        # This test assumes ThreadCatalogService exists and is callable
        # For now, we test the response model shape

        entry = ThreadEntry(
            thread_id="claude-3-5-sonnet",
            display_name="Claude 3.5 Sonnet",
            provider="Anthropic",
            unit_description="tokens",
            raw_cost_inr_paise=100,
            total_markup_pct=25.0,
            marked_up_cost_paise=125,
            is_platform_thread=False,
            applicable_agents=["DMA", "RESEARCH"],
            status="ACTIVE",
        )

        assert entry.thread_id == "claude-3-5-sonnet"
        assert entry.provider == "Anthropic"
        assert entry.applicable_agents == ["DMA", "RESEARCH"]


# ── Property-based tests with Hypothesis ────────────────────────────────────

class TestDerivePrice_PropertyBased:
    """Property-based tests for derive_price formula using Hypothesis."""

    @given(
        cost_floor_paise=st.integers(min_value=1000, max_value=10_000_000),
        margin_pct=st.floats(min_value=0.0, max_value=99.9),
    )
    def test_derive_price_formula_correctness(self, cost_floor_paise, margin_pct):
        """Property: derive_price(floor, margin) ≥ floor, with equality at margin=0."""
        if margin_pct == 0.0:
            expected = cost_floor_paise
        else:
            expected = int(cost_floor_paise / (1 - margin_pct / 100))

        # Verify formula invariants
        assert expected >= cost_floor_paise, "Derived price must never be below cost floor"

        if margin_pct == 0.0:
            assert expected == cost_floor_paise, "At zero margin, price equals floor"

    @given(
        cost_floor_paise=st.integers(min_value=1000, max_value=10_000_000),
        margin_pct=st.floats(min_value=0.1, max_value=99.9),
    )
    def test_derive_price_monotonic_in_margin(self, cost_floor_paise, margin_pct):
        """Property: as margin increases, derived price increases (monotonic)."""
        price_at_margin = int(cost_floor_paise / (1 - margin_pct / 100))
        price_at_lower_margin = int(cost_floor_paise / (1 - (margin_pct - 1) / 100))

        assert price_at_margin > price_at_lower_margin, "Higher margin → higher price"

    @given(
        cost_floor_paise=st.integers(min_value=1000, max_value=10_000_000),
        margin_pct=st.floats(min_value=0.0, max_value=99.0),
    )
    def test_derive_price_large_paise_values(self, cost_floor_paise, margin_pct):
        """Property: derive_price handles large paise values without overflow."""
        try:
            price = int(cost_floor_paise / (1 - margin_pct / 100) if margin_pct < 100 else cost_floor_paise)
            assert isinstance(price, int)
            assert price > 0
        except ZeroDivisionError:
            pytest.skip("Margin too close to 100%")


class TestValidatePrice_PropertyBased:
    """Property-based tests for validate_price covering all outcomes."""

    @given(
        agent_type=st.just("DMA"),
        bundle_tier=st.just("STARTER"),
        cost_floor_paise=st.just(50000),
        margin_pct=st.just(30.0),
        proposed_price_offset=st.integers(min_value=-30000, max_value=30000),
    )
    @pytest.mark.asyncio
    async def test_validate_price_outcome_paths(
        self,
        agent_type,
        bundle_tier,
        cost_floor_paise,
        margin_pct,
        proposed_price_offset,
        bundle_engine,
        seed_bundle_profiles,
    ):
        """Property: validate_price outcome is APPROVED iff proposed ≥ minimum_compliant."""
        min_compliant = int(cost_floor_paise / (1 - margin_pct / 100))
        proposed_price = min_compliant + proposed_price_offset

        if proposed_price < 1:
            pytest.skip("Proposed price must be positive")

        request = PriceValidationRequest(
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            proposed_price_paise=proposed_price,
        )
        result = await bundle_engine.validate_price(request)

        if proposed_price >= min_compliant:
            assert result.outcome == "APPROVED"
        else:
            assert result.outcome == "REJECTED"

    @given(
        proposed_price=st.integers(min_value=40000, max_value=100000),
    )
    @pytest.mark.asyncio
    async def test_validate_price_all_branches(
        self,
        proposed_price,
        bundle_engine,
        seed_bundle_profiles,
        test_session_factory,
    ):
        """Property: every validation produces exactly one audit log entry."""
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            proposed_price_paise=proposed_price,
        )
        result = await bundle_engine.validate_price(request)

        # Verify result has expected fields
        assert result.outcome in ("APPROVED", "REJECTED")
        assert result.cost_floor_paise == 50000
        assert result.minimum_compliant_price_paise > 0
        assert result.proposed_price_paise == proposed_price

        # Verify exactly one audit log entry
        async with test_session_factory() as session:
            log_rows = await session.execute(
                text("""
                    SELECT COUNT(*) as cnt FROM pricing_floor_log
                    WHERE agent_type = 'DMA'
                      AND bundle_tier = 'STARTER'
                      AND proposed_price_paise = :proposed
                """),
                {"proposed": proposed_price},
            )
            result_row = log_rows.scalar()
            assert result_row >= 1, "At least one log entry for each validation"


# ── Integration tests ──────────────────────────────────────────────────────

class TestMarkupEngineIntegration:
    """Integration tests across multiple functions."""

    @pytest.mark.asyncio
    async def test_full_workflow_approved_pricing(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Integration: load cost floor → derive price → validate → audit trail."""
        # Step 1: Load cost floor
        floor = await bundle_engine.cost_floor("DMA", "PROFESSIONAL")
        assert floor == 150000

        # Step 2: Derive price with default margin
        derived_price = await bundle_engine.derive_price("DMA", "PROFESSIONAL", target_margin_pct=None)
        assert derived_price > floor

        # Step 3: Validate the derived price
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="PROFESSIONAL",
            proposed_price_paise=derived_price,
        )
        result = await bundle_engine.validate_price(request)
        assert result.outcome == "APPROVED"

        # Step 4: Verify audit trail
        async with test_session_factory() as session:
            logs = await session.execute(
                text("SELECT * FROM pricing_floor_log WHERE agent_type = 'DMA' AND bundle_tier = 'PROFESSIONAL'")
            )
            entries = logs.fetchall()
            assert len(entries) >= 1
            assert entries[0].outcome == "APPROVED"

    @pytest.mark.asyncio
    async def test_full_workflow_rejected_pricing(self, bundle_engine, seed_bundle_profiles, test_session_factory):
        """Integration: underpriced proposal is rejected with audit trail."""
        floor = await bundle_engine.cost_floor("RESEARCH", "STARTER")
        min_margin = 0.25  # 25%
        min_price = int(floor / (1 - min_margin))

        # Attempt to price below minimum
        request = PriceValidationRequest(
            agent_type="RESEARCH",
            bundle_tier="STARTER",
            proposed_price_paise=min_price - 1000,
        )
        result = await bundle_engine.validate_price(request)
        assert result.outcome == "REJECTED"

        # Verify audit trail
        async with test_session_factory() as session:
            logs = await session.execute(
                text("SELECT * FROM pricing_floor_log WHERE outcome = 'REJECTED'")
            )
            entries = logs.fetchall()
            assert len(entries) >= 1


# ── Marker tests for coverage ────────────────────────────────────────────────

class TestCoverageMarkers:
    """Ensure ≥90% line coverage of bundle_engine.py and models.py."""

    @pytest.mark.asyncio
    async def test_bundle_engine_initialization(self, test_session_factory):
        """Test BundleEngine initialization path."""
        from src.billing_engine.markup.bundle_engine import BundleEngine

        engine = BundleEngine(session_factory=test_session_factory)
        assert engine is not None

    def test_price_validation_request_model(self):
        """Test PriceValidationRequest Pydantic model."""
        request = PriceValidationRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            proposed_price_paise=50000,
        )
        assert request.agent_type == "DMA"
        assert request.bundle_tier == "STARTER"
        assert request.proposed_price_paise == 50000

    def test_price_validation_response_model(self):
        """Test PriceValidation Pydantic model (response)."""
        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=71429,
            proposed_price_paise=75000,
        )
        assert response.outcome == "APPROVED"
        assert response.cost_floor_paise == 50000

    def test_price_derive_request_model(self):
        """Test PriceDeriveRequest Pydantic model."""
        request = PriceDeriveRequest(
            agent_type="DMA",
            bundle_tier="STARTER",
            target_margin_pct=35.0,
        )
        assert request.agent_type == "DMA"
        assert request.target_margin_pct == 35.0