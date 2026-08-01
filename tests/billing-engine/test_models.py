# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import logging

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
        """PriceDeriveRequest allows target_margin_pct to be None (optional)."""
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

    def test_target_margin_100_or_more_raises(self) -> None:
        """PriceDeriveRequest rejects target_margin_pct >= 100."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=100.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_valid_approved_response(self) -> None:
        """PriceValidation response for APPROVED outcome."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=70000,
        )
        assert validation.outcome == ValidationOutcome.APPROVED
        assert validation.cost_floor_paise == 50000
        assert validation.minimum_compliant_price_paise == 62500
        assert validation.proposed_price_paise == 70000

    def test_valid_rejected_response(self) -> None:
        """PriceValidation response for REJECTED outcome."""
        validation = PriceValidation(
            outcome=ValidationOutcome.REJECTED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=40000,
        )
        assert validation.outcome == ValidationOutcome.REJECTED
        assert validation.proposed_price_paise < validation.minimum_compliant_price_paise

    def test_all_required_fields_present(self) -> None:
        """PriceValidation includes all required fields."""
        validation = PriceValidation(
            outcome=ValidationOutcome.APPROVED,
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=70000,
        )
        assert hasattr(validation, "outcome")
        assert hasattr(validation, "cost_floor_paise")
        assert hasattr(validation, "minimum_compliant_price_paise")
        assert hasattr(validation, "proposed_price_paise")

    def test_missing_outcome_raises(self) -> None:
        """PriceValidation rejects missing outcome field."""
        with pytest.raises(ValidationError):
            PriceValidation(
                cost_floor_paise=50000,
                minimum_compliant_price_paise=62500,
                proposed_price_paise=70000,
            )

    def test_missing_cost_floor_raises(self) -> None:
        """PriceValidation rejects missing cost_floor_paise."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome=ValidationOutcome.APPROVED,
                minimum_compliant_price_paise=62500,
                proposed_price_paise=70000,
            )

    def test_missing_minimum_compliant_price_raises(self) -> None:
        """PriceValidation rejects missing minimum_compliant_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome=ValidationOutcome.APPROVED,
                cost_floor_paise=50000,
                proposed_price_paise=70000,
            )

    def test_missing_proposed_price_raises(self) -> None:
        """PriceValidation rejects missing proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome=ValidationOutcome.APPROVED,
                cost_floor_paise=50000,
                minimum_compliant_price_paise=62500,
            )


class TestValidationOutcome:
    """Test ValidationOutcome enum."""

    def test_approved_value(self) -> None:
        """ValidationOutcome.APPROVED has correct string value."""
        assert ValidationOutcome.APPROVED.value == "APPROVED"

    def test_rejected_value(self) -> None:
        """ValidationOutcome.REJECTED has correct string value."""
        assert ValidationOutcome.REJECTED.value == "REJECTED"

    def test_enum_membership(self) -> None:
        """All expected outcomes are in the enum."""
        outcomes = {e.value for e in ValidationOutcome}
        assert "APPROVED" in outcomes
        assert "REJECTED" in outcomes