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
        req = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert req.agent_type == "researcher"
        assert req.proposed_price_paise == 100000

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

    def test_valid_with_explicit_margin(self) -> None:
        """PriceDeriveRequest accepts agent_type, bundle_tier, and target_margin_pct."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert req.target_margin_pct == 20.0

    def test_valid_with_none_margin(self) -> None:
        """PriceDeriveRequest accepts None for target_margin_pct (optional)."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=None,
        )
        assert req.target_margin_pct is None

    def test_default_margin_is_none(self) -> None:
        """PriceDeriveRequest defaults target_margin_pct to None if omitted."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert req.target_margin_pct is None

    def test_negative_margin_raises(self) -> None:
        """PriceDeriveRequest rejects negative target_margin_pct."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-20.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_all_fields_present(self) -> None:
        """PriceValidation contains outcome, cost_floor_paise, minimum_compliant_price_paise, proposed_price_paise."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=100000,
        )
        assert validation.outcome == ValidationOutcome.APPROVED
        assert validation.cost_floor_paise == 50000
        assert validation.minimum_compliant_price_paise == 62500
        assert validation.proposed_price_paise == 100000

    def test_rejected_outcome(self) -> None:
        """PriceValidation can represent REJECTED outcome."""
        validation = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=30000,
        )
        assert validation.outcome == ValidationOutcome.REJECTED
        assert validation.proposed_price_paise < validation.minimum_compliant_price_paise

    def test_field_types(self) -> None:
        """PriceValidation fields have correct types."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=100000,
        )
        assert isinstance(validation.outcome, ValidationOutcome)
        assert isinstance(validation.cost_floor_paise, int)
        assert isinstance(validation.minimum_compliant_price_paise, int)
        assert isinstance(validation.proposed_price_paise, int)


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor method — C-089 Margin Floor."""

    @pytest.mark.asyncio
    async def test_cost_floor_reads_from_db(self) -> None:
        """cost_floor reads bundle_profiles.cost_floor_paise from DB without recomputation."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        result = await engine.cost_floor("researcher", "starter")

        assert result == 50000
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises(self) -> None:
        """cost_floor raises KeyError for unknown agent_type."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        with pytest.raises(KeyError):
            await engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotency(self) -> None:
        """cost_floor called twice returns same value; DB queried each time (no caching)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        result1 = await engine.cost_floor("researcher", "starter")
        result2 = await engine.cost_floor("researcher", "starter")

        assert result1 == result2 == 50000
        assert mock_session.execute.call_count == 2


class TestBundleEngineDerivePrice:
    """Test BundleEngine.derive_price method — margin-on-revenue formula."""

    @pytest.mark.asyncio
    async def test_derive_price_explicit_margin(self) -> None:
        """derive_price with explicit target_margin_pct: result = ceil(floor / (1 - margin/100))."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        result = await engine.derive_price("researcher", "starter", target_margin_pct=20)

        expected = 100000
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_default_margin_from_db(self) -> None:
        """derive_price with target_margin_pct=None uses DB minimum_margin_pct."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        result = await engine.derive_price("researcher", "starter")

        expected = 106667
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_result_gte_cost_floor(self) -> None:
        """derive_price result is always >= cost_floor for valid margin 0 < m < 100."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=30.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        result = await engine.derive_price("researcher", "starter", target_margin_pct=15)

        assert result >= 50000

    @pytest.mark.asyncio
    async def test_derive_price_margin_gte_100_raises(self) -> None:
        """derive_price raises ValueError if target_margin_pct >= 100."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        with pytest.raises(ValueError):
            await engine.derive_price("researcher", "starter", target_margin_pct=100)

    @pytest.mark.asyncio
    async def test_derive_price_margin_lte_0_raises(self) -> None:
        """derive_price raises ValueError if target_margin_pct <= 0."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result

        engine = BundleEngine(session=mock_session)
        with pytest.raises(ValueError):
            await engine.derive_price("researcher", "starter", target_margin_pct=-5)


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price method — C-089 C-059 audit."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_audits(self) -> None:
        """validate_price APPROVED: outcome=APPROVED, pricing_floor_log written once."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        engine = BundleEngine(session=mock_session)
        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=100000
        )

        assert validation.outcome == ValidationOutcome.APPROVED
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_rejected_audits(self) -> None:
        """validate_price REJECTED: outcome=REJECTED, pricing_floor_log written once."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        engine = BundleEngine(session=mock_session)
        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=30000
        )

        assert validation.outcome == ValidationOutcome.REJECTED
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_response_fields(self) -> None:
        """validate_price returns PriceValidation with all fields populated."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        engine = BundleEngine(session=mock_session)
        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=100000
        )

        assert validation.cost_floor_paise == 50000
        assert validation.minimum_compliant_price_paise > 0
        assert validation.proposed_price_paise == 100000
        assert validation.outcome in (ValidationOutcome.APPROVED, ValidationOutcome.REJECTED)

    @pytest.mark.asyncio
    async def test_validate_price_idempotency(self) -> None:
        """validate_price called twice writes pricing_floor_log twice (append-only)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        engine = BundleEngine(session=mock_session)
        await engine.validate_price("researcher", "starter", proposed_price_paise=100000)
        await engine.validate_price("researcher", "starter", proposed_price_paise=100000)

        assert mock_session.add.call_count == 2
        assert mock_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_error_propagates(self) -> None:
        """validate_price propagates DB write errors (does not silently swallow)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=50000,
            minimum_margin_pct=25.0,
        )
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(side_effect=RuntimeError("DB connection failed"))

        engine = BundleEngine(session=mock_session)
        with pytest.raises(RuntimeError):
            await engine.validate_price("researcher", "starter", proposed_price_paise=100000)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    cost_floor=st.integers(min_value=1000, max_value=1000000),
    margin_pct=st.floats(min_value=0.1, max_value=99.9),
)
async def test_derive_price_property_formula(
    cost_floor: int, margin_pct: float
) -> None:
    """Property test: derive_price(cost_floor, margin) always satisfies result >= cost_floor."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = BundleProfile(
        agent_type="researcher",
        bundle_tier="starter",
        cost_floor_paise=cost_floor,
        minimum_margin_pct=50.0,
    )
    mock_session.execute.return_value = mock_result

    engine = BundleEngine(session=mock_session)
    result = await engine.derive_price("researcher", "starter", target_margin_pct=margin_pct)

    assert result >= cost_floor


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    proposed_price=st.integers(min_value=0, max_value=500000),
)
async def test_validate_price_property_outcomes(
    proposed_price: int,
) -> None:
    """Property test: validate_price covers all outcome paths (APPROVED, REJECTED)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = BundleProfile(
        agent_type="researcher",
        bundle_tier="starter",
        cost_floor_paise=50000,
        minimum_margin_pct=25.0,
    )
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    engine = BundleEngine(session=mock_session)
    validation = await engine.validate_price("researcher", "starter", proposed_price_paise=proposed_price)

    assert validation.outcome in (ValidationOutcome.APPROVED, ValidationOutcome.REJECTED)
    assert validation.proposed_price_paise == proposed_price