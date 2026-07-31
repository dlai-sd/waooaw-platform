# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §WC027-01a
# Constitutional basis: C-059 (audit obligation)
from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from src.billing_engine.markup.models import (
    BundleProfile,
    PriceConfig,
    PriceDeriveRequest,
    PriceValidation,
    PriceValidationRequest,
    ThreadEntry,
)

logger = logging.getLogger(__name__)


# ── ThreadEntry tests ──────────────────────────────────────────────────────────


class TestThreadEntry:
    """Test ThreadEntry Pydantic model."""

    def test_thread_entry_valid_construction(self):
        """ThreadEntry: valid construction with all required fields."""
        entry = ThreadEntry(
            thread_id="ollama_llama2",
            display_name="Llama 2",
            provider="ollama",
            unit_description="1 LLM completion",
            raw_cost_inr_paise=5000,
            total_markup_pct=15.0,
            marked_up_cost_paise=5750,
            is_platform_thread=True,
            applicable_agents=["researcher", "dma"],
            status="ACTIVE",
        )
        assert entry.thread_id == "ollama_llama2"
        assert entry.display_name == "Llama 2"
        assert entry.provider == "ollama"
        assert entry.raw_cost_inr_paise == 5000
        assert entry.total_markup_pct == 15.0
        assert entry.is_platform_thread is True

    def test_thread_entry_missing_required_field_raises_validation_error(self):
        """ThreadEntry: missing required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="ollama_llama2",
                display_name="Llama 2",
                provider="ollama",
                # missing unit_description
                raw_cost_inr_paise=5000,
                total_markup_pct=15.0,
                marked_up_cost_paise=5750,
                is_platform_thread=True,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )

    def test_thread_entry_invalid_raw_cost_negative_raises_validation_error(self):
        """ThreadEntry: negative raw_cost_inr_paise raises ValidationError."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="ollama_llama2",
                display_name="Llama 2",
                provider="ollama",
                unit_description="1 LLM completion",
                raw_cost_inr_paise=-5000,
                total_markup_pct=15.0,
                marked_up_cost_paise=5750,
                is_platform_thread=True,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


# ── BundleProfile tests ────────────────────────────────────────────────────────


class TestBundleProfile:
    """Test BundleProfile Pydantic model."""

    def test_bundle_profile_valid_construction(self):
        """BundleProfile: valid construction."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
            thread_ids=["ollama_llama2", "openai_gpt4"],
        )
        assert profile.agent_type == "researcher"
        assert profile.bundle_tier == "starter"
        assert profile.cost_floor_paise == 80000
        assert profile.minimum_margin_pct == 25.0
        assert isinstance(profile.cost_floor_paise, int)
        assert isinstance(profile.minimum_margin_pct, float)

    def test_bundle_profile_negative_cost_floor_raises_validation_error(self):
        """BundleProfile: negative cost_floor_paise raises ValidationError."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=-80000,
                minimum_margin_pct=25.0,
                thread_ids=["ollama_llama2"],
            )

    def test_bundle_profile_negative_margin_raises_validation_error(self):
        """BundleProfile: negative minimum_margin_pct raises ValidationError."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-25.0,
                thread_ids=["ollama_llama2"],
            )

    def test_bundle_profile_zero_cost_floor_valid(self):
        """BundleProfile: zero cost_floor_paise is valid (free tier)."""
        profile = BundleProfile(
            agent_type="researcher",
            bundle_tier="free",
            cost_floor_paise=0,
            minimum_margin_pct=0.0,
            thread_ids=["ollama_llama2"],
        )
        assert profile.cost_floor_paise == 0
        assert profile.minimum_margin_pct == 0.0


# ── PriceConfig tests ──────────────────────────────────────────────────────────


class TestPriceConfig:
    """Test PriceConfig Pydantic model."""

    def test_price_config_valid_construction(self):
        """PriceConfig: valid construction and round-trip."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert config.agent_type == "researcher"
        assert config.bundle_tier == "starter"
        assert config.target_margin_pct == 20.0

    def test_price_config_target_margin_pct_optional(self):
        """PriceConfig: target_margin_pct is optional (defaults to None)."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert config.target_margin_pct is None

    def test_price_config_negative_margin_raises_validation_error(self):
        """PriceConfig: negative target_margin_pct raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-20.0,
            )

    def test_price_config_margin_gte_100_raises_validation_error(self):
        """PriceConfig: target_margin_pct >= 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=100.0,
            )


# ── PriceValidationRequest tests ───────────────────────────────────────────────


class TestPriceValidationRequest:
    """Test PriceValidationRequest Pydantic model."""

    def test_price_validation_request_valid_construction(self):
        """PriceValidationRequest: valid construction with all required fields."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.proposed_price_paise == 100000

    def test_price_validation_request_missing_proposed_price_raises_validation_error(self):
        """PriceValidationRequest: missing proposed_price_paise raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
            )

    def test_price_validation_request_negative_price_raises_validation_error(self):
        """PriceValidationRequest: negative proposed_price_paise raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-100000,
            )


# ── PriceDeriveRequest tests ───────────────────────────────────────────────────


class TestPriceDeriveRequest:
    """Test PriceDeriveRequest Pydantic model."""

    def test_price_derive_request_valid_with_target_margin(self):
        """PriceDeriveRequest: valid with target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.target_margin_pct == 20.0

    def test_price_derive_request_valid_without_target_margin(self):
        """PriceDeriveRequest: valid without target_margin_pct (optional)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None

    def test_price_derive_request_target_margin_optional_defaults_to_none(self):
        """PriceDeriveRequest: target_margin_pct defaults to None."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
        )
        assert request.target_margin_pct is None


# ── PriceValidation response tests ─────────────────────────────────────────────


class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_price_validation_all_fields_present(self):
        """PriceValidation: all required fields present and typed correctly."""
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
        assert isinstance(response.cost_floor_paise, int)
        assert isinstance(response.minimum_compliant_price_paise, int)
        assert isinstance(response.proposed_price_paise, int)

    def test_price_validation_outcome_rejected(self):
        """PriceValidation: outcome can be REJECTED."""
        response = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=50000,
        )
        assert response.outcome == "REJECTED"

    def test_price_validation_missing_outcome_raises_validation_error(self):
        """PriceValidation: missing outcome raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceValidation(
                cost_floor_paise=80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )

    def test_price_validation_missing_cost_floor_paise_raises_validation_error(self):
        """PriceValidation: missing cost_floor_paise raises ValidationError."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome="APPROVED",
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )

    def test_price_validation_negative_price_values_raise_validation_error(self):
        """PriceValidation: negative price paise values raise ValidationError."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome="APPROVED",
                cost_floor_paise=-80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )


# ── Integration: model serialization round-trip ────────────────────────────────


class TestModelSerialization:
    """Test Pydantic model serialization and deserialization."""

    def test_price_validation_request_to_dict_and_back(self):
        """PriceValidationRequest: to_dict() and model_validate() round-trip."""
        original = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        data = original.model_dump()
        reconstructed = PriceValidationRequest(**data)
        assert reconstructed.agent_type == original.agent_type
        assert reconstructed.bundle_tier == original.bundle_tier
        assert reconstructed.proposed_price_paise == original.proposed_price_paise

    def test_price_validation_response_to_dict_and_back(self):
        """PriceValidation: to_dict() and model_validate() round-trip."""
        original = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        data = original.model_dump()
        reconstructed = PriceValidation(**data)
        assert reconstructed.outcome == original.outcome
        assert reconstructed.cost_floor_paise == original.cost_floor_paise
        assert reconstructed.minimum_compliant_price_paise == original.minimum_compliant_price_paise
        assert reconstructed.proposed_price_paise == original.proposed_price_paise

    def test_bundle_profile_to_dict_and_back(self):
        """BundleProfile: to_dict() and model_validate() round-trip."""
        original = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
            thread_ids=["ollama_llama2", "openai_gpt4"],
        )
        data = original.model_dump()
        reconstructed = BundleProfile(**data)
        assert reconstructed.agent_type == original.agent_type
        assert reconstructed.bundle_tier == original.bundle_tier
        assert reconstructed.cost_floor_paise == original.cost_floor_paise
        assert reconstructed.minimum_margin_pct == original.minimum_margin_pct