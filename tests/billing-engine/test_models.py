# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from billing_engine.markup.models import (
    ThreadEntry,
    BundleProfile,
    PriceConfig,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
)
from billing_engine.markup.bundle_engine import BundleEngine


class TestThreadEntry:
    """Test ThreadEntry Pydantic model construction and validation."""

    def test_valid_construction(self):
        """ThreadEntry accepts all required fields."""
        entry = ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="per 1K tokens",
            raw_cost_inr_paise=50000,
            total_markup_pct=15.0,
            marked_up_cost_paise=57500,
            is_platform_thread=False,
            applicable_agents=["researcher", "analyst"],
            status="ACTIVE",
        )
        assert entry.thread_id == "gpt-4-turbo"
        assert entry.raw_cost_inr_paise == 50000
        assert entry.is_platform_thread is False

    def test_reject_missing_required_fields(self):
        """ThreadEntry rejects missing required fields."""
        with pytest.raises(ValueError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                unit_description="per 1K tokens",
                raw_cost_inr_paise=50000,
                total_markup_pct=15.0,
                marked_up_cost_paise=57500,
                is_platform_thread=False,
            )

    def test_reject_invalid_cost_negative(self):
        """ThreadEntry rejects negative raw_cost_inr_paise."""
        with pytest.raises(ValueError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                unit_description="per 1K tokens",
                raw_cost_inr_paise=-50000,
                total_markup_pct=15.0,
                marked_up_cost_paise=57500,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


class TestBundleProfile:
    """Test BundleProfile Pydantic model construction and validation."""

    def test_valid_construction(self):
        """BundleProfile accepts all required fields."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
            description="Starter tier for researcher",
        )
        assert profile.agent_type == "researcher"
        assert profile.cost_floor_paise == 80000
        assert profile.minimum_margin_pct == 25.0

    def test_cost_floor_paise_must_be_positive(self):
        """BundleProfile rejects non-positive cost_floor_paise."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=0,
                minimum_margin_pct=25.0,
                description="Starter tier",
            )

    def test_minimum_margin_pct_must_be_positive(self):
        """BundleProfile rejects non-positive minimum_margin_pct."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-5.0,
                description="Starter tier",
            )

    def test_minimum_margin_pct_must_be_less_than_100(self):
        """BundleProfile rejects minimum_margin_pct >= 100."""
        with pytest.raises(ValueError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=100.0,
                description="Starter tier",
            )


class TestPriceConfig:
    """Test PriceConfig Pydantic model round-trip and validation."""

    def test_valid_construction(self):
        """PriceConfig accepts all required fields."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            base_price_paise=100000,
            markup_pct=20.0,
        )
        assert config.agent_type == "researcher"
        assert config.base_price_paise == 100000

    def test_reject_negative_base_price(self):
        """PriceConfig rejects negative base_price_paise."""
        with pytest.raises(ValueError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                base_price_paise=-100000,
                markup_pct=20.0,
            )

    def test_reject_negative_markup_pct(self):
        """PriceConfig rejects negative markup_pct."""
        with pytest.raises(ValueError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                base_price_paise=100000,
                markup_pct=-20.0,
            )


class TestPriceValidationRequest:
    """Test PriceValidationRequest model validation."""

    def test_valid_construction(self):
        """PriceValidationRequest accepts all required fields."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.proposed_price_paise == 100000

    def test_reject_missing_proposed_price_paise(self):
        """PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValueError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
            )

    def test_reject_negative_proposed_price_paise(self):
        """PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValueError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-100000,
            )


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest model validation."""

    def test_valid_construction_with_target_margin(self):
        """PriceDeriveRequest accepts target_margin_pct when provided."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.target_margin_pct == 20.0

    def test_valid_construction_without_target_margin(self):
        """PriceDeriveRequest allows target_margin_pct to be None (defaults to DB minimum)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None

    def test_reject_negative_target_margin_pct(self):
        """PriceDeriveRequest rejects negative target_margin_pct."""
        with pytest.raises(ValueError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-20.0,
            )

    def test_reject_target_margin_pct_gte_100(self):
        """PriceDeriveRequest rejects target_margin_pct >= 100."""
        with pytest.raises(ValueError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=100.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model fields and types."""

    def test_valid_construction_approved(self):
        """PriceValidation accepts all required fields for APPROVED outcome."""
        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        assert response.outcome == "APPROVED"
        assert response.cost_floor_paise == 80000
        assert response.minimum_compliant_price_paise == 100000
        assert response.proposed_price_paise == 105000

    def test_valid_construction_rejected(self):
        """PriceValidation accepts all required fields for REJECTED outcome."""
        response = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert response.outcome == "REJECTED"
        assert response.proposed_price_paise == 95000

    def test_reject_invalid_outcome(self):
        """PriceValidation rejects invalid outcome values."""
        with pytest.raises(ValueError):
            PriceValidation(
                outcome="PENDING",
                cost_floor_paise=80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=95000,
            )


@pytest.fixture
def mock_db_session():
    """Provide a mock async DB session for BundleEngine tests."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_bundle_profile():
    """Provide a mock BundleProfile DB row."""
    profile = MagicMock()
    profile.cost_floor_paise = 80000
    profile.minimum_margin_pct = 25.0
    return profile


@pytest.fixture
def bundle_engine(mock_db_session):
    """Provide a BundleEngine instance with mocked DB session."""
    engine = BundleEngine(db_session=mock_db_session)
    return engine


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor(agent_type, bundle_tier) method."""

    @pytest.mark.asyncio
    async def test_cost_floor_happy_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """cost_floor reads bundle_profiles.cost_floor_paise from DB without recomputation."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        cost_floor_result = await bundle_engine.cost_floor("researcher", "starter")

        assert cost_floor_result == 80000
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises_key_error(self, bundle_engine, mock_db_session):
        """cost_floor raises KeyError for unknown agent_type."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        with pytest.raises(KeyError):
            await bundle_engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotency(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """Calling cost_floor twice returns same value; DB is queried each time."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        result1 = await bundle_engine.cost_floor("researcher", "starter")
        result2 = await bundle_engine.cost_floor("researcher", "starter")

        assert result1 == result2 == 80000
        assert mock_db_session.execute.call_count == 2


class TestBundleEngineDerivePrice:
    """Test BundleEngine.derive_price(agent_type, bundle_tier, target_margin_pct) method."""

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price with explicit target_margin_pct uses formula floor / (1 - margin/100)."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        derived_price = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=20)

        # Formula: ceil(80000 / (1 - 20/100)) = ceil(80000 / 0.8) = ceil(100000) = 100000
        assert derived_price == 100000

    @pytest.mark.asyncio
    async def test_derive_price_uses_db_minimum_margin_when_none(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price with target_margin_pct=None uses bundle_profiles.minimum_margin_pct from DB."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        derived_price = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=None)

        # Formula: ceil(80000 / (1 - 25/100)) = ceil(80000 / 0.75) = ceil(106666.67) = 106667
        assert derived_price == 106667

    @pytest.mark.asyncio
    async def test_derive_price_result_gte_cost_floor(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derived price MUST always be >= cost_floor for valid margins 0 < m < 100."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        cost_floor_val = await bundle_engine.cost_floor("researcher", "starter")
        derived_price = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=50)

        assert derived_price >= cost_floor_val

    @pytest.mark.asyncio
    async def test_derive_price_rejects_margin_gte_100(self, bundle_engine, mock_db_session):
        """derive_price raises ValueError for target_margin_pct >= 100 (division by zero)."""
        with pytest.raises(ValueError):
            await bundle_engine.derive_price("researcher", "starter", target_margin_pct=100)

    @pytest.mark.asyncio
    async def test_derive_price_rejects_negative_margin(self, bundle_engine, mock_db_session):
        """derive_price raises ValueError for negative target_margin_pct."""
        with pytest.raises(ValueError):
            await bundle_engine.derive_price("researcher", "starter", target_margin_pct=-10)


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price(agent_type, bundle_tier, proposed_price_paise) method.
    
    C-059 CRITICAL: pricing_floor_log MUST be written for BOTH APPROVED and REJECTED outcomes.
    """

    @pytest.mark.asyncio
    async def test_validate_price_approved_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price APPROVED: proposed >= minimum_compliant; pricing_floor_log written once."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation_result = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=106667)

        assert validation_result.outcome == "APPROVED"
        assert validation_result.proposed_price_paise == 106667
        assert validation_result.minimum_compliant_price_paise == 106667
        assert validation_result.cost_floor_paise == 80000
        # C-059: pricing_floor_log MUST be written
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_rejected_path(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """validate_price REJECTED: proposed < minimum_compliant; pricing_floor_log written once (C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation_result = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=95000)

        assert validation_result.outcome == "REJECTED"
        assert validation_result.proposed_price_paise == 95000
        assert validation_result.minimum_compliant_price_paise == 106667
        # C-059: pricing_floor_log MUST be written even on REJECTION
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_audit_log_called_for_both_outcomes(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """C-059: pricing_floor_log write is called exactly once for BOTH APPROVED and REJECTED."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        # Test APPROVED
        _ = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=120000)
        assert mock_db_session.add.call_count == 1

        mock_db_session.reset_mock()

        # Test REJECTED
        _ = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=50000)
        assert mock_db_session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_price_response_fields_present(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """PriceValidation response includes all required fields with correct types."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation_result = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=106667)

        assert hasattr(validation_result, "outcome")
        assert hasattr(validation_result, "cost_floor_paise")
        assert hasattr(validation_result, "minimum_compliant_price_paise")
        assert hasattr(validation_result, "proposed_price_paise")
        assert isinstance(validation_result.outcome, str)
        assert isinstance(validation_result.cost_floor_paise, int)
        assert isinstance(validation_result.minimum_compliant_price_paise, int)
        assert isinstance(validation_result.proposed_price_paise, int)

    @pytest.mark.asyncio
    async def test_validate_price_idempotency_of_audit_log(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """Calling validate_price twice writes pricing_floor_log twice (append-only, no dedup)."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        _ = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=106667)
        _ = await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=106667)

        assert mock_db_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_write_failure_propagates(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """C-059: If pricing_floor_log DB write fails, exception is propagated (audit MUST NOT be bypassed)."""
        mock_db_session.execute = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_query_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("DB write failed"))

        with pytest.raises(Exception, match="DB write failed"):
            await bundle_engine.validate_price("researcher", "starter", proposed_price_paise=106667)