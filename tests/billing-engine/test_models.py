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

    def test_reject_negative_proposed_price(self):
        """PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValueError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-100000,
            )


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest model with optional target_margin_pct."""

    def test_valid_construction_with_margin(self):
        """PriceDeriveRequest accepts target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.target_margin_pct == 20.0

    def test_valid_construction_without_margin(self):
        """PriceDeriveRequest accepts None for target_margin_pct (optional)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None

    def test_reject_negative_margin(self):
        """PriceDeriveRequest rejects negative target_margin_pct."""
        with pytest.raises(ValueError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-10.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_all_fields_present_and_typed(self):
        """PriceValidation response includes all required fields."""
        validation = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=120000,
        )
        assert validation.outcome == "APPROVED"
        assert validation.cost_floor_paise == 80000
        assert validation.minimum_compliant_price_paise == 100000
        assert validation.proposed_price_paise == 120000
        assert isinstance(validation.cost_floor_paise, int)
        assert isinstance(validation.minimum_compliant_price_paise, int)

    def test_outcome_must_be_approved_or_rejected(self):
        """PriceValidation rejects invalid outcome values."""
        with pytest.raises(ValueError):
            PriceValidation(
                outcome="INVALID_OUTCOME",
                cost_floor_paise=80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=120000,
            )


class TestBundleEngineCostFloor:
    """Test BundleEngine.cost_floor() method."""

    @pytest.mark.asyncio
    async def test_cost_floor_reads_from_db(self):
        """cost_floor reads and returns bundle_profiles.cost_floor_paise from DB."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50000
        mock_db.execute.return_value = mock_result
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        result = await engine.cost_floor("researcher", "starter")

        assert result == 50000
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_floor_unknown_agent_type_raises_error(self):
        """cost_floor raises KeyError for unknown agent_type."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        with pytest.raises((KeyError, ValueError)):
            await engine.cost_floor("unknown_agent", "starter")

    @pytest.mark.asyncio
    async def test_cost_floor_idempotency(self):
        """Calling cost_floor twice with same args returns same value."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50000
        mock_db.execute.return_value = mock_result
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        factory = MagicMock(return_value=mock_db)
        engine = BundleEngine(db_session_factory=factory)

        result1 = await engine.cost_floor("researcher", "starter")
        result2 = await engine.cost_floor("researcher", "starter")

        assert result1 == result2 == 50000


class TestBundleEngineDerivePriceFormula:
    """Test BundleEngine.derive_price() formula correctness."""

    @pytest.mark.asyncio
    async def test_derive_price_with_explicit_margin(self):
        """derive_price with target_margin_pct=20: floor=80000 → ceil(80000/(1-0.2))=100000."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 80000
        mock_db.execute.return_value = mock_result
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        result = await engine.derive_price("researcher", "starter", target_margin_pct=20)

        assert result == 100000

    @pytest.mark.asyncio
    async def test_derive_price_with_none_uses_db_minimum_margin(self):
        """derive_price with target_margin_pct=None uses DB minimum_margin_pct."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [mock_cost_result, mock_margin_result]
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        result = await engine.derive_price("researcher", "starter", target_margin_pct=None)

        expected = int(80000 / (1 - 25 / 100))
        assert result == expected

    @pytest.mark.asyncio
    async def test_derive_price_result_gte_cost_floor(self):
        """derive_price result MUST be >= cost_floor for valid margin 0 < m < 100."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        cost_floor_value = 80000
        mock_result.scalar.return_value = cost_floor_value
        mock_db.execute.return_value = mock_result
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        result = await engine.derive_price("researcher", "starter", target_margin_pct=50)

        assert result >= cost_floor_value

    @pytest.mark.asyncio
    async def test_derive_price_margin_gte_100_raises_error(self):
        """derive_price with target_margin_pct >= 100 raises ValueError."""
        mock_db = AsyncMock()
        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        with pytest.raises(ValueError):
            await engine.derive_price("researcher", "starter", target_margin_pct=100)

    @pytest.mark.asyncio
    async def test_derive_price_margin_lte_0_raises_error(self):
        """derive_price with target_margin_pct <= 0 raises ValueError."""
        mock_db = AsyncMock()
        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        with pytest.raises(ValueError):
            await engine.derive_price("researcher", "starter", target_margin_pct=-10)


class TestBundleEngineValidatePriceAudit:
    """Test BundleEngine.validate_price() C-059 audit obligation."""

    @pytest.mark.asyncio
    async def test_validate_price_approved_writes_audit_log(self):
        """validate_price with APPROVED outcome writes pricing_floor_log exactly once."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [mock_cost_result, mock_margin_result]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=120000
        )

        assert validation.outcome == "APPROVED"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_rejected_writes_audit_log(self):
        """validate_price with REJECTED outcome writes pricing_floor_log exactly once (C-059)."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [mock_cost_result, mock_margin_result]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=50000
        )

        assert validation.outcome == "REJECTED"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_price_response_includes_all_fields(self):
        """validate_price response includes minimum_compliant_price_paise."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [mock_cost_result, mock_margin_result]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        validation = await engine.validate_price(
            "researcher", "starter", proposed_price_paise=120000
        )

        assert hasattr(validation, "cost_floor_paise")
        assert hasattr(validation, "minimum_compliant_price_paise")
        assert hasattr(validation, "proposed_price_paise")
        assert validation.cost_floor_paise == 80000
        assert validation.proposed_price_paise == 120000

    @pytest.mark.asyncio
    async def test_validate_price_idempotency_writes_twice(self):
        """Calling validate_price twice writes pricing_floor_log twice (append-only)."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [
            mock_cost_result,
            mock_margin_result,
            mock_cost_result,
            mock_margin_result,
        ]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        factory = MagicMock(return_value=mock_db)
        engine = BundleEngine(db_session_factory=factory)

        await engine.validate_price("researcher", "starter", proposed_price_paise=120000)
        await engine.validate_price("researcher", "starter", proposed_price_paise=120000)

        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_price_db_write_failure_propagates(self):
        """validate_price DB write failure raises exception (C-059 audit not bypassed)."""
        mock_db = AsyncMock()
        mock_cost_result = MagicMock()
        mock_cost_result.scalar.return_value = 80000
        mock_margin_result = MagicMock()
        mock_margin_result.scalar.return_value = 25.0
        mock_db.execute.side_effect = [mock_cost_result, mock_margin_result]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock(side_effect=RuntimeError("DB write failed"))
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        engine = BundleEngine(db_session_factory=MagicMock(return_value=mock_db))

        with pytest.raises(RuntimeError):
            await engine.validate_price("researcher", "starter", proposed_price_paise=120000)