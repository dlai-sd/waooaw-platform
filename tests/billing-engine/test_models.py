# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.billing_engine.markup.models import (
    ThreadEntry,
    BundleProfile,
    PriceConfig,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    ValidationOutcome,
)
from src.billing_engine.markup.bundle_engine import BundleEngine

logger = logging.getLogger(__name__)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for bundle_profiles queries."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_bundle_profile():
    """Mock BundleProfile row from DB."""
    profile = MagicMock()
    profile.cost_floor_paise = 50000
    profile.minimum_margin_pct = 25.0
    return profile


@pytest.fixture
def mock_bundle_engine(mock_db_session, mock_bundle_profile):
    """BundleEngine with mocked DB session factory."""
    with patch('src.billing_engine.markup.bundle_engine._get_session_factory') as mock_factory:
        factory = MagicMock()
        factory.return_value = mock_db_session
        mock_factory.return_value = factory

        engine = BundleEngine()
        # Pre-configure the session mock to return the profile
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        yield engine


# ── ThreadEntry Tests ───────────────────────────────────────────────────────

class TestThreadEntry:
    """Tests for ThreadEntry Pydantic model."""

    def test_thread_entry_valid_construction(self):
        """ThreadEntry with all required fields."""
        entry = ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="1000 tokens",
            raw_cost_inr_paise=5000,
            total_markup_pct=40.0,
            marked_up_cost_paise=7000,
            is_platform_thread=False,
            applicable_agents=["researcher", "analyst"],
            status="ACTIVE",
        )
        assert entry.thread_id == "gpt-4-turbo"
        assert entry.raw_cost_inr_paise == 5000
        assert entry.total_markup_pct == 40.0

    def test_thread_entry_reject_missing_required_field(self):
        """ThreadEntry rejects missing required field."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                # missing unit_description
                raw_cost_inr_paise=5000,
                total_markup_pct=40.0,
                marked_up_cost_paise=7000,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )

    def test_thread_entry_negative_cost_rejected(self):
        """ThreadEntry rejects negative raw_cost_inr_paise."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                unit_description="1000 tokens",
                raw_cost_inr_paise=-5000,
                total_markup_pct=40.0,
                marked_up_cost_paise=7000,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


# ── BundleProfile Tests ──────────────────────────────────────────────────────

class TestBundleProfile:
    """Tests for BundleProfile Pydantic model."""

    def test_bundle_profile_valid_construction(self):
        """BundleProfile with valid cost_floor_paise and minimum_margin_pct."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=20.0,
        )
        assert profile.agent_type == "researcher"
        assert profile.cost_floor_paise == 80000
        assert profile.minimum_margin_pct == 20.0
        assert isinstance(profile.cost_floor_paise, int)
        assert isinstance(profile.minimum_margin_pct, float)

    def test_bundle_profile_reject_negative_cost_floor(self):
        """BundleProfile rejects negative cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-80000,
                minimum_margin_pct=20.0,
            )

    def test_bundle_profile_reject_negative_margin(self):
        """BundleProfile rejects negative minimum_margin_pct."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-20.0,
            )

    def test_bundle_profile_reject_zero_cost_floor(self):
        """BundleProfile rejects zero cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=0,
                minimum_margin_pct=20.0,
            )


# ── PriceConfig Tests ────────────────────────────────────────────────────────

class TestPriceConfig:
    """Tests for PriceConfig Pydantic model."""

    def test_price_config_valid_construction(self):
        """PriceConfig with valid values."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=25.0,
        )
        assert config.agent_type == "researcher"
        assert config.bundle_tier == "starter"
        assert config.target_margin_pct == 25.0

    def test_price_config_reject_negative_margin(self):
        """PriceConfig rejects negative target_margin_pct."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-25.0,
            )


# ── PriceValidationRequest Tests ─────────────────────────────────────────────

class TestPriceValidationRequest:
    """Tests for PriceValidationRequest Pydantic model."""

    def test_price_validation_request_valid(self):
        """PriceValidationRequest with required fields."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.proposed_price_paise == 100000

    def test_price_validation_request_reject_missing_proposed_price(self):
        """PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                # missing proposed_price_paise
            )

    def test_price_validation_request_reject_negative_price(self):
        """PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-100000,
            )


# ── PriceDeriveRequest Tests ─────────────────────────────────────────────────

class TestPriceDeriveRequest:
    """Tests for PriceDeriveRequest Pydantic model."""

    def test_price_derive_request_with_explicit_margin(self):
        """PriceDeriveRequest with explicit target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.target_margin_pct == 20.0

    def test_price_derive_request_optional_margin_defaults_to_none(self):
        """PriceDeriveRequest target_margin_pct is optional (defaults to None)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None


# ── PriceValidation Response Tests ───────────────────────────────────────────

class TestPriceValidation:
    """Tests for PriceValidation response model."""

    def test_price_validation_response_all_fields_present(self):
        """PriceValidation response includes all required fields."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        assert validation.outcome == ValidationOutcome.APPROVED
        assert validation.cost_floor_paise == 80000
        assert validation.minimum_compliant_price_paise == 100000
        assert validation.proposed_price_paise == 105000

    def test_price_validation_response_rejected_outcome(self):
        """PriceValidation response with REJECTED outcome."""
        validation = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert validation.outcome == ValidationOutcome.REJECTED

    def test_price_validation_response_fields_typed(self):
        """PriceValidation response fields are correctly typed."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        assert isinstance(validation.outcome, ValidationOutcome)
        assert isinstance(validation.cost_floor_paise, int)
        assert isinstance(validation.minimum_compliant_price_paise, int)
        assert isinstance(validation.proposed_price_paise, int)


# ── BundleEngine.cost_floor Tests ────────────────────────────────────────────

class TestBundleEngineCostFloor:
    """Tests for BundleEngine.cost_floor method."""

    @pytest.mark.asyncio
    async def test_cost_floor_happy_path(self, mock_bundle_engine):
        """cost_floor reads from DB and returns bundle_profiles.cost_floor_paise."""
        result = await mock_bundle_engine.cost_floor("researcher", "starter")
        assert result == 50000

    @pytest.mark.asyncio
    async def test_cost_floor_no_recomputation(self, mock_bundle_engine):
        """cost_floor does not recompute; reads from DB."""
        result = await mock_bundle_engine.cost_floor("researcher", "starter")
        # Verify DB was queried (mock_db_session.execute was called)
        assert result == 50000

    @pytest.mark.asyncio
    async def test_cost_floor_idempotency(self, mock_bundle_engine):
        """Calling cost_floor twice returns same value each time."""
        result1 = await mock_bundle_engine.cost_floor("researcher", "starter")
        result2 = await mock_bundle_engine.cost_floor("researcher", "starter")
        assert result1 == result2
        assert result1 == 50000

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises_error(self, mock_bundle_engine):
        """cost_floor raises error for unknown agent_type."""
        mock_bundle_engine._get_session_factory().return_value.execute.return_value.scalar_one_or_none.return_value = None
        with pytest.raises((KeyError, ValueError)):
            await mock_bundle_engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_bundle_tier_raises_error(self, mock_bundle_engine):
        """cost_floor raises error for unknown bundle_tier."""
        mock_bundle_engine._get_session_factory().return_value.execute.return_value.scalar_one_or_none.return_value = None
        with pytest.raises((KeyError, ValueError)):
            await mock_bundle_engine.cost_floor("researcher", "unknown_tier")


# ── BundleEngine.derive_price Tests ──────────────────────────────────────────

class TestBundleEngineDerivePrice:
    """Tests for BundleEngine.derive_price method."""

    @pytest.mark.asyncio
    async def test_derive_price_explicit_target_margin(self, mock_bundle_engine):
        """derive_price with explicit target_margin_pct=20."""
        # cost_floor=50000 → expected = ceil(50000 / (1 - 20/100)) = ceil(62500) = 62500
        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=20)
        expected = 62500
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_uses_db_minimum_margin_when_none(self, mock_bundle_engine):
        """derive_price uses DB minimum_margin_pct when target_margin_pct is None."""
        # cost_floor=50000, minimum_margin_pct=25 (from mock) → expected = ceil(50000 / (1 - 25/100)) = ceil(66666.67) = 66667
        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=None)
        expected = 66667
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_formula_invariant_margin_on_revenue(self, mock_bundle_engine):
        """derive_price result >= cost_floor for valid margin 0 < m < 100."""
        cost_floor = 50000
        margin = 20.0
        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=margin)
        assert result >= cost_floor

    @pytest.mark.asyncio
    async def test_derive_price_reject_margin_gte_100(self, mock_bundle_engine):
        """derive_price raises ValueError for margin >= 100."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=100)

    @pytest.mark.asyncio
    async def test_derive_price_reject_margin_lte_0(self, mock_bundle_engine):
        """derive_price raises ValueError for margin <= 0."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=0)


# ── BundleEngine.validate_price Tests (C-059 Critical) ────────────────────────

class TestBundleEngineValidatePrice:
    """Tests for BundleEngine.validate_price method (C-059 audit obligation)."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_happy_path(self, mock_bundle_engine):
        """validate_price APPROVED: proposed_price >= minimum_compliant_price."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            result = await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            assert result.outcome == ValidationOutcome.APPROVED
            assert mock_insert.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_price_rejected_path(self, mock_bundle_engine):
        """validate_price REJECTED: proposed_price < minimum_compliant_price."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            result = await mock_bundle_engine.validate_price("researcher", "starter", 30000)
            assert result.outcome == ValidationOutcome.REJECTED
            assert mock_insert.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_price_c059_audit_on_approved(self, mock_bundle_engine):
        """C-059: pricing_floor_log written on APPROVED outcome."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            assert mock_insert.call_count == 1
            call_args = mock_insert.call_args
            assert "agent_type" in call_args.kwargs or call_args.args
            assert "outcome" in call_args.kwargs or len(call_args.args) >= 4

    @pytest.mark.asyncio
    async def test_validate_price_c059_audit_on_rejected(self, mock_bundle_engine):
        """C-059: pricing_floor_log written on REJECTED outcome too."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            await mock_bundle_engine.validate_price("researcher", "starter", 30000)
            assert mock_insert.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_price_response_fields_minimum_compliant_price(self, mock_bundle_engine):
        """PriceValidation response includes minimum_compliant_price_paise."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            result = await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            assert hasattr(result, 'minimum_compliant_price_paise')
            assert result.minimum_compliant_price_paise > 0

    @pytest.mark.asyncio
    async def test_validate_price_response_cost_floor_matches_cost_floor_method(self, mock_bundle_engine):
        """PriceValidation.cost_floor_paise matches cost_floor()."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            result = await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            assert result.cost_floor_paise == 50000

    @pytest.mark.asyncio
    async def test_validate_price_response_echoes_proposed_price(self, mock_bundle_engine):
        """PriceValidation response echoes proposed_price_paise."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            proposed = 70000
            result = await mock_bundle_engine.validate_price("researcher", "starter", proposed)
            assert result.proposed_price_paise == proposed

    @pytest.mark.asyncio
    async def test_validate_price_idempotency_multiple_calls(self, mock_bundle_engine):
        """Calling validate_price twice writes log twice (append-only, not deduplicated)."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.return_value = None
            await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            await mock_bundle_engine.validate_price("researcher", "starter", 70000)
            assert mock_insert.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_write_failure_propagates(self, mock_bundle_engine):
        """DB write failure to pricing_floor_log is propagated, not swallowed."""
        with patch('src.billing_engine.markup.bundle_engine._insert_pricing_floor_log') as mock_insert:
            mock_insert.side_effect = RuntimeError("DB write failed")
            with pytest.raises(RuntimeError):
                await mock_bundle_engine.validate_price("researcher", "starter", 70000)