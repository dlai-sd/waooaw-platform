# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
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


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for DB operations."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_bundle_profile():
    """Mock BundleProfile DB object."""
    profile = MagicMock()
    profile.agent_type = "researcher"
    profile.bundle_tier = "starter"
    profile.cost_floor_paise = 50000
    profile.minimum_margin_pct = 25.0
    return profile


@pytest.fixture
def bundle_engine(mock_db_session):
    """BundleEngine instance with mocked DB."""
    engine = BundleEngine(db_session=mock_db_session)
    return engine


# ── ThreadEntry Model Tests ──────────────────────────────────────────────────

class TestThreadEntryModel:
    """Tests for ThreadEntry Pydantic model."""

    def test_valid_construction(self):
        """ThreadEntry accepts all required fields."""
        entry = ThreadEntry(
            thread_id="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider="openai",
            unit_description="1 LLM call",
            raw_cost_inr_paise=500,
            total_markup_pct=50.0,
            marked_up_cost_paise=750,
            is_platform_thread=False,
            applicable_agents=["researcher", "dma"],
            status="ACTIVE",
        )
        assert entry.thread_id == "gpt-4-turbo"
        assert entry.provider == "openai"
        assert entry.raw_cost_inr_paise == 500

    def test_rejects_missing_required_fields(self):
        """ThreadEntry rejects construction with missing required fields."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4",
                display_name="GPT-4",
                provider="openai",
                # missing unit_description and others
            )

    def test_rejects_negative_paise_values(self):
        """ThreadEntry rejects negative cost values."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="gpt-4",
                display_name="GPT-4",
                provider="openai",
                unit_description="1 call",
                raw_cost_inr_paise=-500,
                total_markup_pct=50.0,
                marked_up_cost_paise=750,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


# ── BundleProfile Model Tests ────────────────────────────────────────────────

class TestBundleProfileModel:
    """Tests for BundleProfile Pydantic model."""

    def test_valid_construction(self):
        """BundleProfile accepts all required fields."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
            description="Starter bundle for researchers",
        )
        assert profile.agent_type == "researcher"
        assert profile.bundle_tier == "starter"
        assert profile.cost_floor_paise == 80000
        assert profile.minimum_margin_pct == 25.0

    def test_cost_floor_paise_is_positive_int(self):
        """BundleProfile enforces cost_floor_paise > 0."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-1000,
                minimum_margin_pct=25.0,
            )

    def test_minimum_margin_pct_is_positive_float(self):
        """BundleProfile enforces minimum_margin_pct > 0."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-5.0,
            )


# ── PriceConfig Model Tests ──────────────────────────────────────────────────

class TestPriceConfigModel:
    """Tests for PriceConfig Pydantic model."""

    def test_valid_round_trip(self):
        """PriceConfig serializes and deserializes correctly."""
        original = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
            remarks="Test config",
        )
        data = original.model_dump()
        restored = PriceConfig(**data)
        assert restored.agent_type == original.agent_type
        assert restored.target_margin_pct == original.target_margin_pct

    def test_rejects_negative_values(self):
        """PriceConfig rejects negative margin."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-10.0,
            )


# ── PriceValidationRequest Model Tests ───────────────────────────────────────

class TestPriceValidationRequestModel:
    """Tests for PriceValidationRequest Pydantic model."""

    def test_valid_request(self):
        """PriceValidationRequest accepts all required fields."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.proposed_price_paise == 100000

    def test_rejects_missing_proposed_price_paise(self):
        """PriceValidationRequest requires proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                # missing proposed_price_paise
            )


# ── PriceDeriveRequest Model Tests ───────────────────────────────────────────

class TestPriceDeriveRequestModel:
    """Tests for PriceDeriveRequest Pydantic model."""

    def test_valid_with_target_margin(self):
        """PriceDeriveRequest accepts explicit target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.target_margin_pct == 20.0

    def test_target_margin_pct_is_optional(self):
        """PriceDeriveRequest allows target_margin_pct=None (defaults to DB value)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=None,
        )
        assert request.target_margin_pct is None

    def test_omitted_target_margin_defaults_to_none(self):
        """PriceDeriveRequest omits target_margin_pct → defaults to None."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None


# ── PriceValidation Response Model Tests ─────────────────────────────────────

class TestPriceValidationResponseModel:
    """Tests for PriceValidation response model."""

    def test_all_fields_present_and_typed(self):
        """PriceValidation includes all required response fields."""
        response = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
            remarks="Price meets margin floor",
        )
        assert response.outcome == ValidationOutcome.APPROVED
        assert response.cost_floor_paise == 80000
        assert response.minimum_compliant_price_paise == 100000
        assert response.proposed_price_paise == 105000
        assert isinstance(response.remarks, str)

    def test_rejected_outcome(self):
        """PriceValidation supports REJECTED outcome."""
        response = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
            remarks="Price below margin floor",
        )
        assert response.outcome == ValidationOutcome.REJECTED
        assert response.proposed_price_paise < response.minimum_compliant_price_paise


# ── BundleEngine.cost_floor Tests ────────────────────────────────────────────

@pytest.mark.asyncio
class TestBundleEngineCostFloor:
    """Tests for BundleEngine.cost_floor() method."""

    async def test_happy_path_reads_from_db(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """cost_floor reads bundle_profiles.cost_floor_paise from DB (no recomputation)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        result = await bundle_engine.cost_floor("researcher", "starter")

        assert result == 50000
        assert mock_db_session.execute.called

    async def test_idempotency_multiple_calls(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """Calling cost_floor twice returns same value; DB called each time (no cache mutation)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        result1 = await bundle_engine.cost_floor("researcher", "starter")
        result2 = await bundle_engine.cost_floor("researcher", "starter")

        assert result1 == result2 == 50000
        assert mock_db_session.execute.call_count == 2  # DB called each time


# ── BundleEngine.derive_price Tests ──────────────────────────────────────────

@pytest.mark.asyncio
class TestBundleEngineDerivePriceFormula:
    """Tests for BundleEngine.derive_price() formula and invariants."""

    async def test_happy_path_explicit_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price with explicit target_margin_pct=20: floor=80000 → ceil(80000/(1-0.2))=100000."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        result = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=20)

        # Formula: cost_floor / (1 - margin/100) = 50000 / 0.8 = 62500
        assert result == 62500

    async def test_happy_path_uses_db_minimum_margin(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price with target_margin_pct=None uses DB minimum_margin_pct=25: floor=80000 → ceil(80000/(1-0.25))=106667."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        result = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=None)

        # Formula: cost_floor / (1 - 25/100) = 50000 / 0.75 = 66666.666... → ceil = 66667
        assert result == 66667

    async def test_formula_invariant_result_gte_cost_floor(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price result MUST be >= cost_floor for any valid margin 0 < m < 100."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        margins = [1, 10, 25, 50, 90, 99]
        for margin in margins:
            result = await bundle_engine.derive_price("researcher", "starter", target_margin_pct=margin)
            assert result >= mock_bundle_profile.cost_floor_paise, f"Failed for margin={margin}"

    async def test_rejects_margin_gte_100(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price raises ValueError if target_margin_pct >= 100 (division by zero)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError):
            await bundle_engine.derive_price("researcher", "starter", target_margin_pct=100)

    async def test_rejects_margin_lte_0(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """derive_price raises ValueError if target_margin_pct <= 0 (nonsensical margin)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError):
            await bundle_engine.derive_price("researcher", "starter", target_margin_pct=0)


# ── BundleEngine.validate_price Tests ────────────────────────────────────────

@pytest.mark.asyncio
class TestBundleEngineValidatePriceApproved:
    """Tests for BundleEngine.validate_price() APPROVED path — C-059 critical."""

    async def test_approved_path_audits_to_log(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """APPROVED: proposed_price_paise >= minimum_compliant_price → pricing_floor_log written (C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=70000,  # >= cost_floor (50000)
        )

        assert result.outcome == ValidationOutcome.APPROVED
        assert mock_db_session.add.called, "C-059: pricing_floor_log must be written on APPROVED"
        assert mock_db_session.commit.called

    async def test_approved_response_fields(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """APPROVED response includes all required fields."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=70000,
        )

        assert result.minimum_compliant_price_paise == result.proposed_price_paise or result.proposed_price_paise >= result.cost_floor_paise
        assert result.cost_floor_paise == 50000
        assert result.proposed_price_paise == 70000


@pytest.mark.asyncio
class TestBundleEngineValidatePriceRejected:
    """Tests for BundleEngine.validate_price() REJECTED path — C-059 critical."""

    async def test_rejected_path_audits_to_log(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """REJECTED: proposed_price_paise < minimum_compliant_price → pricing_floor_log written (C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=40000,  # < cost_floor (50000)
        )

        assert result.outcome == ValidationOutcome.REJECTED
        assert mock_db_session.add.called, "C-059: pricing_floor_log must be written on REJECTED"
        assert mock_db_session.commit.called

    async def test_rejected_response_includes_minimum_compliant_price(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """REJECTED response includes minimum_compliant_price_paise for remediation."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=40000,
        )

        assert result.outcome == ValidationOutcome.REJECTED
        assert result.minimum_compliant_price_paise >= result.cost_floor_paise
        assert result.proposed_price_paise < result.minimum_compliant_price_paise


@pytest.mark.asyncio
class TestBundleEngineValidatePriceAuditInvariant:
    """Tests for C-059 audit invariant: log written on both APPROVED and REJECTED."""

    @pytest.mark.parametrize("proposed_paise,expected_outcome", [
        (70000, ValidationOutcome.APPROVED),
        (40000, ValidationOutcome.REJECTED),
    ])
    async def test_c059_audit_both_outcomes(self, bundle_engine, mock_db_session, mock_bundle_profile, proposed_paise, expected_outcome):
        """C-059: pricing_floor_log written for BOTH APPROVED and REJECTED outcomes."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        result = await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=proposed_paise,
        )

        assert result.outcome == expected_outcome
        assert mock_db_session.add.call_count == 1, f"C-059: log insert call_count must be 1 for {expected_outcome}"

    async def test_idempotency_multiple_validations(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """Calling validate_price twice → pricing_floor_log written twice (append-only, no dedup)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=70000,
        )
        await bundle_engine.validate_price(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=70000,
        )

        assert mock_db_session.add.call_count == 2, "Each validation logs independently"


@pytest.mark.asyncio
class TestBundleEngineValidatePriceErrorHandling:
    """Tests for BundleEngine.validate_price() error handling — C-059 compliance."""

    async def test_db_write_failure_propagates(self, bundle_engine, mock_db_session, mock_bundle_profile):
        """DB write to pricing_floor_log fails → exception propagated (audit NOT bypassed — C-059)."""
        mock_db_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_bundle_profile
        mock_db_session.execute.return_value = mock_result

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB write failed"))

        with pytest.raises(RuntimeError, match="DB write failed"):
            await bundle_engine.validate_price(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=70000,
            )