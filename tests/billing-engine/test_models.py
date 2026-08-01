# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from pydantic import ValidationError

from markup.models import (
    ThreadEntry,
    BundleProfile,
    PriceConfig,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
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

    def test_valid_construction_with_target_margin(self) -> None:
        """PriceDeriveRequest accepts target_margin_pct."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert req.target_margin_pct == 20.0

    def test_valid_construction_without_target_margin(self) -> None:
        """PriceDeriveRequest accepts None for target_margin_pct (optional)."""
        req = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert req.target_margin_pct is None

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
        """PriceValidation accepts APPROVED outcome."""
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

    def test_valid_construction_rejected(self) -> None:
        """PriceValidation accepts REJECTED outcome."""
        validation = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert validation.outcome == ValidationOutcome.REJECTED

    def test_all_fields_present(self) -> None:
        """PriceValidation contains all required fields."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=70000,
        )
        validation_dict = validation.model_dump()
        assert "outcome" in validation_dict
        assert "cost_floor_paise" in validation_dict
        assert "minimum_compliant_price_paise" in validation_dict
        assert "proposed_price_paise" in validation_dict


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor method."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Provide a mock async DB session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_bundle_engine(self, mock_db_session: AsyncMock) -> BundleEngine:
        """Provide a BundleEngine with mocked DB."""
        engine = BundleEngine(db_session=mock_db_session)
        return engine

    @pytest.mark.asyncio
    async def test_cost_floor_happy_path(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """cost_floor reads bundle_profiles.cost_floor_paise from DB."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result = await mock_bundle_engine.cost_floor("researcher", "starter")
        assert result == 50000

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """cost_floor raises KeyError for unknown agent_type."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = None

        with pytest.raises(KeyError):
            await mock_bundle_engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotent(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """cost_floor returns same value on repeated calls."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result1 = await mock_bundle_engine.cost_floor("researcher", "starter")
        result2 = await mock_bundle_engine.cost_floor("researcher", "starter")
        assert result1 == result2 == 50000


class TestBundleEngineDerivPrice:
    """Test BundleEngine.derive_price method."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Provide a mock async DB session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_bundle_engine(self, mock_db_session: AsyncMock) -> BundleEngine:
        """Provide a BundleEngine with mocked DB."""
        engine = BundleEngine(db_session=mock_db_session)
        return engine

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """derive_price with explicit target_margin_pct uses formula: floor / (1 - margin/100)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=20.0)
        expected = 100000
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_with_db_minimum_margin(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """derive_price without target_margin_pct uses bundle_profiles.minimum_margin_pct."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 25.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter")
        expected = 106667
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_result_gte_cost_floor(self, mock_bundle_engine: BundleEngine, mock_db_session: AsyncMock) -> None:
        """derive_price result is always >= cost_floor for valid margin."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 50000
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=15.0)
        assert result >= 50000

    @pytest.mark.asyncio
    async def test_derive_price_target_margin_gte_100_raises(self, mock_bundle_engine: BundleEngine) -> None:
        """derive_price raises ValueError for target_margin_pct >= 100."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=100.0)

    @pytest.mark.asyncio
    async def test_derive_price_target_margin_lte_0_raises(self, mock_bundle_engine: BundleEngine) -> None:
        """derive_price raises ValueError for target_margin_pct <= 0."""
        with pytest.raises(ValueError):
            await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=-5.0)

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=1000000),
        margin_pct=st.floats(min_value=0.1, max_value=99.9),
    )
    @pytest.mark.asyncio
    async def test_derive_price_formula_invariant(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        """Property test: derive_price(cost_floor, margin) >= cost_floor."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = cost_floor
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile

        result = await mock_bundle_engine.derive_price("researcher", "starter", target_margin_pct=margin_pct)
        assert result >= cost_floor


class TestBundleEngineValidatePrice:
    """Test BundleEngine.validate_price method — C-059 audit critical."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Provide a mock async DB session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_bundle_engine(self, mock_db_session: AsyncMock) -> BundleEngine:
        """Provide a BundleEngine with mocked DB."""
        engine = BundleEngine(db_session=mock_db_session)
        return engine

    @pytest.mark.asyncio
    async def test_validate_price_approved_writes_audit_log(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
    ) -> None:
        """validate_price APPROVED outcome writes exactly one pricing_floor_log entry."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation = await mock_bundle_engine.validate_price(
            "researcher",
            "starter",
            105000,
        )

        assert validation.outcome == ValidationOutcome.APPROVED
        assert mock_db_session.add.call_count == 1
        await mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_rejected_writes_audit_log(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
    ) -> None:
        """validate_price REJECTED outcome writes exactly one pricing_floor_log entry (C-059)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation = await mock_bundle_engine.validate_price(
            "researcher",
            "starter",
            95000,
        )

        assert validation.outcome == ValidationOutcome.REJECTED
        assert mock_db_session.add.call_count == 1
        await mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_response_fields_present(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
    ) -> None:
        """PriceValidation response contains all required fields."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation = await mock_bundle_engine.validate_price(
            "researcher",
            "starter",
            100000,
        )

        assert validation.cost_floor_paise == 80000
        assert validation.minimum_compliant_price_paise > 0
        assert validation.proposed_price_paise == 100000
        assert validation.outcome in [ValidationOutcome.APPROVED, ValidationOutcome.REJECTED]

    @pytest.mark.asyncio
    async def test_validate_price_idempotent_audit(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
    ) -> None:
        """Calling validate_price twice writes two independent audit records."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        await mock_bundle_engine.validate_price("researcher", "starter", 100000)
        await mock_bundle_engine.validate_price("researcher", "starter", 100000)

        assert mock_db_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_write_failure_propagates(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
    ) -> None:
        """validate_price propagates DB write errors (C-059 audit must not be bypassed)."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = 80000
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB connection failed"))

        with pytest.raises(RuntimeError):
            await mock_bundle_engine.validate_price("researcher", "starter", 100000)

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=10000, max_value=500000),
        proposed_price=st.integers(min_value=0, max_value=1000000),
    )
    @pytest.mark.asyncio
    async def test_validate_price_outcome_paths(
        self,
        mock_bundle_engine: BundleEngine,
        mock_db_session: AsyncMock,
        cost_floor: int,
        proposed_price: int,
    ) -> None:
        """Property test: validate_price returns APPROVED or REJECTED consistently."""
        mock_profile = MagicMock()
        mock_profile.cost_floor_paise = cost_floor
        mock_profile.minimum_margin_pct = 20.0
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.fetchone.return_value = mock_profile
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        validation = await mock_bundle_engine.validate_price(
            "researcher",
            "starter",
            proposed_price,
        )

        assert validation.outcome in [ValidationOutcome.APPROVED, ValidationOutcome.REJECTED]
        assert validation.minimum_compliant_price_paise >= cost_floor
        if proposed_price >= validation.minimum_compliant_price_paise:
            assert validation.outcome == ValidationOutcome.APPROVED
        else:
            assert validation.outcome == ValidationOutcome.REJECTED