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

    def test_negative_margin_on_revenue_raises(self) -> None:
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
        assert req.bundle_tier == "starter"
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

    def test_valid_construction_without_margin(self) -> None:
        """PriceDeriveRequest accepts agent_type and bundle_tier without target_margin_pct."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert req.agent_type == "researcher"
        assert req.bundle_tier == "starter"
        assert req.target_margin_pct is None

    def test_valid_construction_with_margin(self) -> None:
        """PriceDeriveRequest accepts explicit target_margin_pct."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert req.target_margin_pct == 20.0

    def test_negative_target_margin_raises(self) -> None:
        """PriceDeriveRequest rejects negative target_margin_pct."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-20.0,
            )

    def test_target_margin_over_100_raises(self) -> None:
        """PriceDeriveRequest rejects target_margin_pct >= 100."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=100.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_valid_construction_approved(self) -> None:
        """PriceValidation accepts APPROVED outcome with all required fields."""
        result = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=100000,
        )
        assert result.outcome == ValidationOutcome.APPROVED
        assert result.cost_floor_paise == 80000
        assert result.minimum_compliant_price_paise == 100000
        assert result.proposed_price_paise == 100000

    def test_valid_construction_rejected(self) -> None:
        """PriceValidation accepts REJECTED outcome."""
        result = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert result.outcome == ValidationOutcome.REJECTED
        assert result.proposed_price_paise == 95000

    def test_all_price_fields_present(self) -> None:
        """PriceValidation includes cost_floor, minimum_compliant, and proposed price."""
        result = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=62500,
        )
        assert hasattr(result, "cost_floor_paise")
        assert hasattr(result, "minimum_compliant_price_paise")
        assert hasattr(result, "proposed_price_paise")


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Provide a mock async DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_bundle_engine(mock_db_session: AsyncMock) -> BundleEngine:
    """Provide a BundleEngine with mocked DB session."""
    engine = BundleEngine(mock_db_session)
    return engine


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor() method — reads from DB."""

    @pytest.mark.asyncio
    async def test_cost_floor_happy_path(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """cost_floor retrieves cost_floor_paise from DB bundle_profiles."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result = await mock_bundle_engine.cost_floor("researcher", "starter")

        assert result == 50000
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """cost_floor raises KeyError for unknown agent_type."""
        mock_db_session.execute.return_value.scalar.return_value = None

        with pytest.raises((KeyError, ValueError)):
            await mock_bundle_engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotent(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """cost_floor returns same value when called twice."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result1 = await mock_bundle_engine.cost_floor("researcher", "starter")
        result2 = await mock_bundle_engine.cost_floor("researcher", "starter")

        assert result1 == result2
        assert result1 == 50000
        assert mock_db_session.execute.call_count == 2


class TestBundleEngineDerivePrice:
    """Test BundleEngine.derive_price() — margin-on-revenue formula."""

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """derive_price(target_margin_pct=20) applies formula: floor / (1 - margin/100)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result = await mock_bundle_engine.derive_price(
            "researcher", "starter", target_margin_pct=20.0
        )

        expected = int(80000 / (1 - 20.0 / 100))
        assert result == expected
        assert result == 100000

    @pytest.mark.asyncio
    async def test_derive_price_with_default_minimum_margin(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """derive_price without target_margin_pct uses bundle_profiles.minimum_margin_pct."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter")

        expected = int(80000 / (1 - 25.0 / 100))
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_greater_than_or_equal_to_cost_floor(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """derive_price result is always >= cost_floor for 0 < margin < 100."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 15.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter")

        assert result >= 50000

    @pytest.mark.asyncio
    async def test_derive_price_margin_gte_100_raises(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """derive_price raises ValueError when target_margin_pct >= 100."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price(
                "researcher", "starter", target_margin_pct=100.0
            )

    @pytest.mark.asyncio
    async def test_derive_price_negative_margin_raises(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """derive_price raises ValueError when target_margin_pct <= 0."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price(
                "researcher", "starter", target_margin_pct=-5.0
            )

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=10000000),
        margin_pct=st.floats(min_value=0.1, max_value=99.9),
    )
    @pytest.mark.asyncio
    async def test_derive_price_formula_invariant(
        self, cost_floor: int, margin_pct: float, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """Property: derive_price(cost_floor, margin) always >= cost_floor."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = cost_floor
        mock_profile.minimum_margin_pct = margin_pct

        mock_db_session.execute.return_value.scalar.return_value = mock_profile

        result = await mock_bundle_engine.derive_price(
            "researcher", "starter", target_margin_pct=margin_pct
        )

        assert result >= cost_floor


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price() — C-059 audit obligation."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_path(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """validate_price(proposed >= minimum) returns APPROVED; writes pricing_floor_log."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=106667
        )

        assert result.outcome == ValidationOutcome.APPROVED
        assert result.minimum_compliant_price_paise == 106667
        assert result.proposed_price_paise == 106667
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_rejected_path(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """validate_price(proposed < minimum) returns REJECTED; writes pricing_floor_log."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=100000
        )

        assert result.outcome == ValidationOutcome.REJECTED
        assert result.minimum_compliant_price_paise == 106667
        assert result.proposed_price_paise == 100000
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_audit_log_written_on_approved(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """C-059: pricing_floor_log row written when outcome=APPROVED."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 20.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        _result = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=62500
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_validate_price_audit_log_written_on_rejected(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """C-059: pricing_floor_log row written when outcome=REJECTED."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 20.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        _result = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=50000
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_validate_price_idempotent_audit(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """validate_price called twice writes two separate audit log rows (append-only)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 20.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        _result1 = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=62500
        )
        _result2 = await mock_bundle_engine.validate_price(
            "researcher", "starter", proposed_price_paise=62500
        )

        assert mock_db_session.add.call_count == 2
        assert mock_db_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_error_propagates(
        self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """C-059: DB write error to pricing_floor_log propagates (audit NOT bypassed)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_profile.minimum_margin_pct = 20.0

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB write failed"))

        with pytest.raises(RuntimeError, match="DB write failed"):
            await mock_bundle_engine.validate_price(
                "researcher", "starter", proposed_price_paise=62500
            )

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=5000000),
        margin_pct=st.floats(min_value=5.0, max_value=50.0),
    )
    @pytest.mark.asyncio
    async def test_validate_price_outcome_paths(
        self, cost_floor: int, margin_pct: float, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock
    ) -> None:
        """Property: validate_price outcome is APPROVED or REJECTED based on proposed >= minimum."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = cost_floor
        mock_profile.minimum_margin_pct = margin_pct

        mock_db_session.execute.return_value.scalar.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        minimum_compliant = int(cost_floor / (1 - margin_pct / 100))

        for proposed in [minimum_compliant - 1000, minimum_compliant, minimum_compliant + 1000]:
            if proposed > 0:
                result = await mock_bundle_engine.validate_price(
                    "researcher", "starter", proposed_price_paise=proposed
                )

                if proposed >= minimum_compliant:
                    assert result.outcome == ValidationOutcome.APPROVED
                else:
                    assert result.outcome == ValidationOutcome.REJECTED

                assert result.cost_floor_paise == cost_floor
                assert result.minimum_compliant_price_paise == minimum_compliant
                assert result.proposed_price_paise == proposed