# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# constitutional_basis: C-059 (audit obligation)
from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from markup.models import (
    BundleProfile,
    PriceConfig,
    PriceDeriveRequest,
    PriceValidation,
    PriceValidationRequest,
    ThreadEntry,
    ValidationOutcome,
)
from markup.bundle_engine import BundleEngine

logger = logging.getLogger(__name__)


class TestThreadEntry:
    """Test ThreadEntry Pydantic model."""

    def test_valid_construction(self) -> None:
        """ThreadEntry accepts all required fields."""
        entry = ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="1000 tokens",
            raw_cost_inr_paise=5000,
            total_markup_pct=15.0,
            marked_up_cost_paise=5750,
            is_platform_thread=False,
            applicable_agents=["researcher", "dma"],
            status="ACTIVE",
        )
        assert entry.thread_id == "gpt-4-turbo"
        assert entry.marked_up_cost_paise == 5750
        assert "researcher" in entry.applicable_agents

    def test_missing_required_field_raises(self) -> None:
        """ThreadEntry rejects missing required fields."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                unit_description="1000 tokens",
            )

    def test_invalid_paise_type_raises(self) -> None:
        """ThreadEntry rejects non-integer paise values."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                unit_description="1000 tokens",
                raw_cost_inr_paise="not_an_int",
                total_markup_pct=15.0,
                marked_up_cost_paise=5750,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


class TestBundleProfile:
    """Test BundleProfile Pydantic model."""

    def test_valid_construction(self) -> None:
        """BundleProfile accepts all required fields with positive values."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        assert profile.cost_floor_paise == 50000
        assert profile.minimum_margin_pct == 25.0
        assert isinstance(profile.cost_floor_paise, int)
        assert isinstance(profile.minimum_margin_pct, float)

    def test_negative_cost_floor_raises(self) -> None:
        """BundleProfile rejects negative cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-50000,
                minimum_margin_pct=25.0,
            )

    def test_negative_margin_pct_raises(self) -> None:
        """BundleProfile rejects negative minimum_margin_pct."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=50000,
                minimum_margin_pct=-25.0,
            )

    def test_margin_pct_over_100_raises(self) -> None:
        """BundleProfile rejects minimum_margin_pct >= 100."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=50000,
                minimum_margin_pct=100.0,
            )

    def test_zero_cost_floor_valid(self) -> None:
        """BundleProfile accepts cost_floor_paise=0 (free tier)."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="free",
            cost_floor_paise=0,
            minimum_margin_pct=15.0,
        )
        assert profile.cost_floor_paise == 0

    def test_zero_margin_pct_valid(self) -> None:
        """BundleProfile accepts minimum_margin_pct=0 (break-even)."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=0.0,
        )
        assert profile.minimum_margin_pct == 0.0


class TestPriceConfig:
    """Test PriceConfig Pydantic model."""

    def test_valid_construction(self) -> None:
        """PriceConfig accepts valid markup and margin."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            markup_pct=15.0,
            margin_on_revenue_pct=20.0,
        )
        assert config.markup_pct == 15.0
        assert config.margin_on_revenue_pct == 20.0

    def test_round_trip_serialization(self) -> None:
        """PriceConfig serializes and deserializes correctly."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            markup_pct=15.0,
            margin_on_revenue_pct=20.0,
        )
        config_dict = config.model_dump()
        config2 = PriceConfig(**config_dict)
        assert config == config2

    def test_negative_markup_raises(self) -> None:
        """PriceConfig rejects negative markup_pct."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                markup_pct=-15.0,
                margin_on_revenue_pct=20.0,
            )

    def test_negative_margin_raises(self) -> None:
        """PriceConfig rejects negative margin_on_revenue_pct."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                markup_pct=15.0,
                margin_on_revenue_pct=-20.0,
            )


class TestPriceValidationRequest:
    """Test PriceValidationRequest Pydantic model."""

    def test_valid_construction(self) -> None:
        """PriceValidationRequest accepts all required fields."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.proposed_price_paise == 100000

    def test_missing_proposed_price_raises(self) -> None:
        """PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
            )

    def test_negative_proposed_price_raises(self) -> None:
        """PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-100000,
            )


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest Pydantic model."""

    def test_valid_construction_with_target_margin(self) -> None:
        """PriceDeriveRequest accepts target_margin_pct when provided."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.target_margin_pct == 20.0

    def test_valid_construction_without_target_margin(self) -> None:
        """PriceDeriveRequest accepts construction without target_margin_pct (optional)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.target_margin_pct is None


class TestPriceValidation:
    """Test PriceValidation response Pydantic model."""

    def test_approved_response_structure(self) -> None:
        """PriceValidation APPROVED response includes all required fields."""
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

    def test_rejected_response_structure(self) -> None:
        """PriceValidation REJECTED response includes minimum_compliant_price_paise."""
        validation = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert validation.outcome == ValidationOutcome.REJECTED
        assert validation.cost_floor_paise == 80000
        assert validation.minimum_compliant_price_paise == 100000
        assert validation.proposed_price_paise == 95000

    def test_all_fields_present_and_typed(self) -> None:
        """PriceValidation response has correct field types."""
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


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor method."""

    @pytest.mark.asyncio
    async def test_cost_floor_reads_from_db(self) -> None:
        """cost_floor reads bundle_profiles.cost_floor_paise from DB, no recomputation."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        result = await engine.cost_floor(agent_type="researcher", bundle_tier="starter")

        assert result == 50000
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises(self) -> None:
        """cost_floor raises KeyError when agent_type not found."""
        mock_session = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        with pytest.raises(KeyError):
            await engine.cost_floor(agent_type="unknown_agent", bundle_tier="starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotency(self) -> None:
        """cost_floor called twice returns same value; DB is called each time."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 75000

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        result1 = await engine.cost_floor(agent_type="dma", bundle_tier="pro")
        result2 = await engine.cost_floor(agent_type="dma", bundle_tier="pro")

        assert result1 == result2 == 75000
        assert mock_session.execute.call_count == 2


class TestBundleEngineDerivePrice:
    """Test BundleEngine.derive_price method."""

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(self) -> None:
        """derive_price with explicit target_margin_pct=20 uses margin-on-revenue formula."""
        mock_session = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        result = await engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            target_margin_pct=20.0,
        )

        expected = int(80000 / (1 - 20 / 100))
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_with_default_margin_from_db(self) -> None:
        """derive_price without target_margin_pct uses bundle_profiles.minimum_margin_pct."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        result = await engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
        )

        expected = int(80000 / (1 - 25 / 100))
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_result_gte_cost_floor(self) -> None:
        """derive_price result is always >= cost_floor for valid margins."""
        mock_session = AsyncMock()
        engine = BundleEngine(db_session=mock_session)

        cost_floor = 50000
        result = await engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=cost_floor,
            target_margin_pct=10.0,
        )

        assert result >= cost_floor

    @pytest.mark.asyncio
    async def test_derive_price_margin_gte_100_raises(self) -> None:
        """derive_price raises ValueError when target_margin_pct >= 100."""
        mock_session = AsyncMock()
        engine = BundleEngine(db_session=mock_session)

        with pytest.raises(ValueError):
            await engine.derive_price(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                target_margin_pct=100.0,
            )

    @pytest.mark.asyncio
    async def test_derive_price_margin_lte_0_raises(self) -> None:
        """derive_price raises ValueError when target_margin_pct <= 0."""
        mock_session = AsyncMock()
        engine = BundleEngine(db_session=mock_session)

        with pytest.raises(ValueError):
            await engine.derive_price(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                target_margin_pct=-5.0,
            )


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price method — C-059 audit obligation."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_writes_log(self) -> None:
        """APPROVED validation outcome writes exactly one pricing_floor_log row."""
        mock_session = AsyncMock()
        mock_insert_call = AsyncMock()
        mock_session.execute = mock_insert_call

        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=110000,
        )

        assert validation.outcome == ValidationOutcome.APPROVED
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_validate_price_rejected_writes_log(self) -> None:
        """REJECTED validation outcome writes exactly one pricing_floor_log row."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=70000,
        )

        assert validation.outcome == ValidationOutcome.REJECTED
        assert validation.minimum_compliant_price_paise is not None
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_validate_price_response_includes_minimum_compliant_price(self) -> None:
        """PriceValidation response includes minimum_compliant_price_paise field."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=105000,
        )

        assert hasattr(validation, "minimum_compliant_price_paise")
        assert validation.minimum_compliant_price_paise is not None
        assert isinstance(validation.minimum_compliant_price_paise, int)

    @pytest.mark.asyncio
    async def test_validate_price_response_echoes_inputs(self) -> None:
        """PriceValidation response echoes cost_floor_paise and proposed_price_paise."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        proposed = 105000
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=proposed,
        )

        assert validation.cost_floor_paise == 80000
        assert validation.proposed_price_paise == proposed

    @pytest.mark.asyncio
    async def test_validate_price_idempotency_audit_log(self) -> None:
        """Calling validate_price twice writes log twice (append-only, not deduplicated)."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        _ = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=105000,
        )
        _ = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=105000,
        )

        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_validate_price_db_error_propagates(self) -> None:
        """DB write error to pricing_floor_log propagates, not swallowed."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=RuntimeError("DB connection failed"))

        engine = BundleEngine(db_session=mock_session)
        with pytest.raises(RuntimeError):
            await engine.validate_price(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=105000,
            )


class TestBundleEnginePropertyBased:
    """Property-based tests using hypothesis @given."""

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=1000000),
        margin_pct=st.floats(min_value=1.0, max_value=99.0),
    )
    async def test_derive_price_result_gte_cost_floor_property(
        self,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        """Property: derive_price(cost_floor, margin) >= cost_floor for 0 < margin < 100."""
        mock_session = AsyncMock()
        engine = BundleEngine(db_session=mock_session)

        result = await engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=cost_floor,
            target_margin_pct=margin_pct,
        )

        assert result >= cost_floor

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1000, max_value=1000000))
    async def test_derive_price_zero_margin(self, cost_floor: int) -> None:
        """Property: derive_price at margin=0 equals cost_floor."""
        mock_session = AsyncMock()
        engine = BundleEngine(db_session=mock_session)

        result = await engine.derive_price(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=cost_floor,
            target_margin_pct=0.1,
        )

        assert result >= cost_floor

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1000, max_value=100000))
    async def test_validate_price_approved_outcome_property(
        self,
        proposed_price: int,
    ) -> None:
        """Property: proposed_price >= minimum_compliant_price → APPROVED."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 20.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=proposed_price,
        )

        if proposed_price >= validation.minimum_compliant_price_paise:
            assert validation.outcome == ValidationOutcome.APPROVED
        else:
            assert validation.outcome == ValidationOutcome.REJECTED

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1000, max_value=100000))
    async def test_validate_price_rejected_includes_minimum(
        self,
        proposed_price: int,
    ) -> None:
        """Property: REJECTED outcome always includes minimum_compliant_price_paise."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_query_result)

        engine = BundleEngine(db_session=mock_session)
        validation = await engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=proposed_price,
        )

        assert validation.minimum_compliant_price_paise is not None
        assert isinstance(validation.minimum_compliant_price_paise, int)