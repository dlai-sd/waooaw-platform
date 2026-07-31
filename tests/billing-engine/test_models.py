# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# constitutional_basis: C-059 (audit obligation), C-089 (margin floor)
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
import math

from src.billing_engine.markup.models import (
    ThreadEntry,
    BundleProfile,
    PriceConfig,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
)
from src.billing_engine.markup.bundle_engine import BundleEngine


# ────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODEL TESTS
# ────────────────────────────────────────────────────────────────────────────


class TestThreadEntry:
    """Test ThreadEntry Pydantic model construction and validation."""

    def test_valid_construction(self):
        """ThreadEntry accepts all required fields."""
        entry = ThreadEntry(
            thread_id="gpt4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="1000 tokens",
            raw_cost_inr_paise=150,
            total_markup_pct=25.0,
            marked_up_cost_paise=188,
            is_platform_thread=False,
            applicable_agents=["researcher", "analyst"],
            status="ACTIVE",
        )
        assert entry.thread_id == "gpt4-turbo"
        assert entry.display_name == "GPT-4 Turbo"
        assert entry.provider == "openai"
        assert entry.total_markup_pct == 25.0

    def test_reject_missing_required_field(self):
        """ThreadEntry rejects missing required fields."""
        with pytest.raises(ValueError):
            ThreadEntry(
                thread_id="gpt4-turbo",
                display_name="GPT-4 Turbo",
                # missing provider
                unit_description="1000 tokens",
                raw_cost_inr_paise=150,
                total_markup_pct=25.0,
                marked_up_cost_paise=188,
                is_platform_thread=False,
                applicable_agents=[],
                status="ACTIVE",
            )


class TestBundleProfile:
    """Test BundleProfile Pydantic model."""

    def test_valid_construction(self):
        """BundleProfile accepts valid cost_floor_paise and minimum_margin_pct."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=20.0,
        )
        assert profile.cost_floor_paise == 50000
        assert profile.minimum_margin_pct == 20.0
        assert isinstance(profile.cost_floor_paise, int)
        assert isinstance(profile.minimum_margin_pct, float)

    def test_reject_negative_cost_floor(self):
        """BundleProfile rejects negative cost_floor_paise."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-50000,
                minimum_margin_pct=20.0,
            )

    def test_reject_negative_margin(self):
        """BundleProfile rejects negative minimum_margin_pct."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=50000,
                minimum_margin_pct=-20.0,
            )

    def test_reject_margin_gte_100(self):
        """BundleProfile rejects margin >= 100 (invalid for pricing formula)."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=50000,
                minimum_margin_pct=100.0,
            )


class TestPriceConfig:
    """Test PriceConfig Pydantic model."""

    def test_valid_round_trip(self):
        """PriceConfig valid construction and round-trip serialization."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=25.0,
        )
        assert config.agent_type == "researcher"
        assert config.bundle_tier == "starter"
        assert config.target_margin_pct == 25.0
        config_dict = config.model_dump()
        config_restored = PriceConfig(**config_dict)
        assert config_restored.agent_type == config.agent_type

    def test_reject_negative_margin_in_config(self):
        """PriceConfig rejects negative target_margin_pct."""
        with pytest.raises(ValueError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-25.0,
            )


class TestPriceValidationRequest:
    """Test PriceValidationRequest Pydantic model."""

    def test_valid_construction(self):
        """PriceValidationRequest accepts required fields."""
        req = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert req.agent_type == "researcher"
        assert req.proposed_price_paise == 100000

    def test_reject_missing_proposed_price(self):
        """PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValueError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                # missing proposed_price_paise
            )


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest Pydantic model."""

    def test_valid_with_explicit_margin(self):
        """PriceDeriveRequest accepts explicit target_margin_pct."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert req.target_margin_pct == 20.0

    def test_valid_with_optional_margin(self):
        """PriceDeriveRequest allows target_margin_pct to be None (optional)."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert req.target_margin_pct is None


class TestPriceValidationResponse:
    """Test PriceValidation response model."""

    def test_all_fields_present(self):
        """PriceValidation contains outcome, cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise."""
        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=75000,
        )
        assert response.outcome == "APPROVED"
        assert response.cost_floor_paise == 50000
        assert response.minimum_compliant_price_paise == 62500
        assert response.proposed_price_paise == 75000

    def test_outcome_enum_values(self):
        """PriceValidation outcome accepts 'APPROVED' or 'REJECTED'."""
        approved = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=75000,
        )
        assert approved.outcome == "APPROVED"

        rejected = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=40000,
        )
        assert rejected.outcome == "REJECTED"


# ────────────────────────────────────────────────────────────────────────────
# BUNDLE ENGINE TESTS
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Provide a mock async DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_bundle_profile():
    """Provide a mock BundleProfile DB row."""
    profile = MagicMock()
    profile.cost_floor_paise = 50000
    profile.minimum_margin_pct = 25.0
    return profile


@pytest.fixture
def bundle_engine(mock_db_session):
    """Provide a BundleEngine with mocked DB session."""
    engine = BundleEngine(db_session_factory=lambda: mock_db_session)
    return engine


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor() — reads from DB, no recomputation."""

    @pytest.mark.asyncio
    async def test_cost_floor_happy_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """cost_floor returns cost_floor_paise from DB row."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        result = await bundle_engine.cost_floor(
            agent_type="researcher",
            bundle_tier="starter",
        )

        assert result == 50000
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_cost_floor_not_recomputed(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """cost_floor reads from DB, does not recompute."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        result1 = await bundle_engine.cost_floor(
            agent_type="researcher",
            bundle_tier="starter",
        )
        result2 = await bundle_engine.cost_floor(
            agent_type="researcher",
            bundle_tier="starter",
        )

        assert result1 == result2 == 50000
        assert mock_db_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type(self, bundle_engine, mock_db_session):
        """cost_floor raises KeyError or domain exception if agent_type not found."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = None

        with pytest.raises((KeyError, ValueError)):
            await bundle_engine.cost_floor(
                agent_type="unknown_agent",
                bundle_tier="starter",
            )


class TestBundleEngineDerivePrice:
    """Test BundleEngine.derive_price() — margin-on-revenue formula."""

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price with explicit margin: floor / (1 - margin/100)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        result = await bundle_engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )

        # floor=50000, margin=20% → 50000 / (1 - 0.20) = 50000 / 0.80 = 62500
        expected = math.ceil(50000 / (1.0 - 0.20))
        assert result == expected
        assert result == 62500

    @pytest.mark.asyncio
    async def test_derive_price_with_default_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price without explicit margin uses bundle_profiles.minimum_margin_pct."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        result = await bundle_engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=None,
        )

        # floor=50000, minimum_margin=25% → 50000 / (1 - 0.25) = 50000 / 0.75 = 66666.67 → ceil = 66667
        expected = math.ceil(50000 / (1.0 - 0.25))
        assert result == expected
        assert result == 66667

    @pytest.mark.asyncio
    async def test_derive_price_invariant_gte_floor(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price result >= cost_floor for any valid 0 < margin < 100."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        for margin in [5.0, 15.0, 25.0, 50.0, 75.0, 99.0]:
            result = await bundle_engine.derive_price(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=margin,
            )
            assert result >= 50000, f"derive_price({margin}%) = {result} should be >= floor 50000"

    @pytest.mark.asyncio
    async def test_derive_price_reject_margin_gte_100(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price rejects margin >= 100 (division by zero)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        with pytest.raises(ValueError):
            await bundle_engine.derive_price(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=100.0,
            )

    @pytest.mark.asyncio
    async def test_derive_price_reject_negative_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price rejects negative margin."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )

        with pytest.raises(ValueError):
            await bundle_engine.derive_price(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-5.0,
            )


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price() — C-059 CRITICAL: audit on BOTH outcomes."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price: proposed >= minimum_compliant → APPROVED, pricing_floor_log written."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=75000,
        )

        assert result.outcome == "APPROVED"
        assert result.cost_floor_paise == 50000
        assert result.minimum_compliant_price_paise == math.ceil(50000 / 0.75)
        assert result.proposed_price_paise == 75000
        assert mock_db_session.add.call_count == 1
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_validate_price_rejected_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price: proposed < minimum_compliant → REJECTED, pricing_floor_log written (C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=40000,
        )

        assert result.outcome == "REJECTED"
        assert result.cost_floor_paise == 50000
        assert result.minimum_compliant_price_paise == math.ceil(50000 / 0.75)
        assert result.proposed_price_paise == 40000
        assert mock_db_session.add.call_count == 1, "pricing_floor_log must be written on REJECTION (C-059)"
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_validate_price_audit_on_both_outcomes(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price writes pricing_floor_log for BOTH APPROVED and REJECTED (C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        approved = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=75000,
        )
        assert approved.outcome == "APPROVED"
        assert mock_db_session.add.call_count == 1

        mock_db_session.reset_mock()
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        rejected = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=40000,
        )
        assert rejected.outcome == "REJECTED"
        assert mock_db_session.add.call_count == 1, "pricing_floor_log written on rejection (C-059)"

    @pytest.mark.asyncio
    async def test_validate_price_response_fields(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price response includes all required fields."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=75000,
        )

        assert hasattr(result, "outcome")
        assert hasattr(result, "cost_floor_paise")
        assert hasattr(result, "minimum_compliant_price_paise")
        assert hasattr(result, "proposed_price_paise")
        assert result.minimum_compliant_price_paise >= result.cost_floor_paise

    @pytest.mark.asyncio
    async def test_validate_price_idempotent_audit_log(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price called twice → pricing_floor_log written twice (append-only, no deduplication)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result1 = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=75000,
        )
        assert result1.outcome == "APPROVED"

        mock_db_session.add.reset_mock()
        mock_db_session.commit.reset_mock()

        result2 = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=75000,
        )
        assert result2.outcome == "APPROVED"
        assert mock_db_session.add.call_count == 1, "second call writes second log entry"

    @pytest.mark.asyncio
    async def test_validate_price_db_error_propagates(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price: DB write failure → exception propagated (C-059 audit cannot be bypassed)."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_bundle_profile
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("DB commit failed"))

        with pytest.raises(Exception, match="DB commit failed"):
            await bundle_engine.validate_price(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=75000,
            )