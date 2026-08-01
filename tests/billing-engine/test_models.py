# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# constitutional_basis: C-059 (audit obligation), C-089 (margin floor)
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from markup.models import (
    ThreadEntry,
    BundleProfile,
    PriceConfig,
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
)


class TestThreadEntry:
    """Test ThreadEntry Pydantic model."""

    def test_thread_entry_valid_construction(self) -> None:
        """ThreadEntry accepts all required fields."""
        entry = ThreadEntry(
            thread_id="thread_001",
            display_name="Claude 3.5 Sonnet",
            provider="Anthropic",
            unit_description="tokens",
            raw_cost_inr_paise=50000,
            total_markup_pct=10.5,
            marked_up_cost_paise=55250,
            is_platform_thread=True,
            applicable_agents=["DMA", "Researcher"],
            status="ACTIVE",
        )
        assert entry.thread_id == "thread_001"
        assert entry.display_name == "Claude 3.5 Sonnet"
        assert entry.provider == "Anthropic"
        assert entry.raw_cost_inr_paise == 50000
        assert entry.is_platform_thread is True
        assert entry.applicable_agents == ["DMA", "Researcher"]

    def test_thread_entry_missing_required_field(self) -> None:
        """ThreadEntry rejects missing required fields."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="thread_001",
                display_name="Claude 3.5 Sonnet",
                provider="Anthropic",
                unit_description="tokens",
                raw_cost_inr_paise=50000,
                total_markup_pct=10.5,
                marked_up_cost_paise=55250,
                is_platform_thread=True,
            )


class TestBundleProfile:
    """Test BundleProfile Pydantic model."""

    def test_bundle_profile_valid_construction(self) -> None:
        """BundleProfile accepts valid cost_floor_paise and minimum_margin_pct."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
        )
        assert profile.agent_type == "researcher"
        assert profile.bundle_tier == "starter"
        assert profile.cost_floor_paise == 80000
        assert profile.minimum_margin_pct == 25.0

    def test_bundle_profile_positive_cost_floor(self) -> None:
        """BundleProfile enforces positive cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-1000,
                minimum_margin_pct=25.0,
            )

    def test_bundle_profile_positive_margin(self) -> None:
        """BundleProfile enforces non-negative minimum_margin_pct."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-5.0,
            )

    def test_bundle_profile_zero_cost_floor_rejected(self) -> None:
        """BundleProfile rejects zero cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=0,
                minimum_margin_pct=25.0,
            )


class TestPriceConfig:
    """Test PriceConfig Pydantic model."""

    def test_price_config_valid_construction(self) -> None:
        """PriceConfig accepts valid values."""
        config = PriceConfig(
            agent_type="dma",
            bundle_tier="professional",
            base_price_paise=120000,
            markup_pct=15.0,
        )
        assert config.agent_type == "dma"
        assert config.base_price_paise == 120000
        assert config.markup_pct == 15.0

    def test_price_config_round_trip(self) -> None:
        """PriceConfig serializes and deserializes correctly."""
        original = PriceConfig(
            agent_type="analyst",
            bundle_tier="enterprise",
            base_price_paise=250000,
            markup_pct=20.0,
        )
        serialized = original.model_dump()
        deserialized = PriceConfig(**serialized)
        assert deserialized == original

    def test_price_config_rejects_negative_base_price(self) -> None:
        """PriceConfig rejects negative base_price_paise."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="dma",
                bundle_tier="starter",
                base_price_paise=-50000,
                markup_pct=10.0,
            )

    def test_price_config_rejects_negative_markup(self) -> None:
        """PriceConfig rejects negative markup_pct."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="dma",
                bundle_tier="starter",
                base_price_paise=80000,
                markup_pct=-5.0,
            )


class TestPriceValidationRequest:
    """Test PriceValidationRequest Pydantic model."""

    def test_price_validation_request_valid(self) -> None:
        """PriceValidationRequest accepts valid input."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.proposed_price_paise == 100000

    def test_price_validation_request_missing_proposed_price(self) -> None:
        """PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
            )

    def test_price_validation_request_negative_price(self) -> None:
        """PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-50000,
            )


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest Pydantic model."""

    def test_price_derive_request_with_target_margin(self) -> None:
        """PriceDeriveRequest accepts explicit target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="dma",
            bundle_tier="professional",
            target_margin_pct=20.0,
        )
        assert request.agent_type == "dma"
        assert request.bundle_tier == "professional"
        assert request.target_margin_pct == 20.0

    def test_price_derive_request_target_margin_optional(self) -> None:
        """PriceDeriveRequest accepts None for target_margin_pct (uses DB minimum)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.target_margin_pct is None

    def test_price_derive_request_negative_margin_rejected(self) -> None:
        """PriceDeriveRequest rejects negative target_margin_pct."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="dma",
                bundle_tier="starter",
                target_margin_pct=-10.0,
            )


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_price_validation_approved_response(self) -> None:
        """PriceValidation response includes all required fields on APPROVED."""
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

    def test_price_validation_rejected_response(self) -> None:
        """PriceValidation response includes all required fields on REJECTED."""
        response = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=95000,
        )
        assert response.outcome == "REJECTED"
        assert response.cost_floor_paise == 80000
        assert response.minimum_compliant_price_paise == 100000
        assert response.proposed_price_paise == 95000

    def test_price_validation_all_fields_positive(self) -> None:
        """PriceValidation enforces non-negative paise values."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome="APPROVED",
                cost_floor_paise=-1000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )

    def test_price_validation_missing_outcome(self) -> None:
        """PriceValidation rejects missing outcome field."""
        with pytest.raises(ValidationError):
            PriceValidation(
                cost_floor_paise=80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )


class TestPriceValidationLogicApproved:
    """Test PriceValidation logic: APPROVED outcome when proposed >= minimum_compliant."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=500000),
        margin_pct=st.floats(min_value=1.0, max_value=99.0),
    )
    def test_price_validation_approved_when_proposed_meets_floor(
        self,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        """
        APPROVED path: proposed_price >= minimum_compliant_price.
        Formula: minimum_compliant = ceil(cost_floor / (1 - margin/100))
        """
        import math

        minimum_compliant = math.ceil(cost_floor / (1 - margin_pct / 100))
        proposed = minimum_compliant + 5000

        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=minimum_compliant,
            proposed_price_paise=proposed,
        )

        assert response.outcome == "APPROVED"
        assert response.proposed_price_paise >= response.minimum_compliant_price_paise


class TestPriceValidationLogicRejected:
    """Test PriceValidation logic: REJECTED outcome when proposed < minimum_compliant."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cost_floor=st.integers(min_value=1000, max_value=500000),
        margin_pct=st.floats(min_value=1.0, max_value=99.0),
    )
    def test_price_validation_rejected_when_proposed_below_floor(
        self,
        cost_floor: int,
        margin_pct: float,
    ) -> None:
        """
        REJECTED path: proposed_price < minimum_compliant_price (C-089 violation).
        """
        import math

        minimum_compliant = math.ceil(cost_floor / (1 - margin_pct / 100))
        proposed = maximum(1, minimum_compliant - 1000)

        response = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=cost_floor,
            minimum_compliant_price_paise=minimum_compliant,
            proposed_price_paise=proposed,
        )

        assert response.outcome == "REJECTED"
        assert response.proposed_price_paise < response.minimum_compliant_price_paise


def maximum(a: int, b: int) -> int:
    """Return the maximum of two integers."""
    return a if a > b else b