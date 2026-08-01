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


# ─────────────────────────────────────────────────────────────────────────────
# ThreadEntry Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadEntry:
    """Test ThreadEntry Pydantic model validation."""

    def test_thread_entry_valid_construction(self):
        """Test valid ThreadEntry construction with all required fields."""
        entry = ThreadEntry(
            thread_id="thread-001",
            display_name="GPT-4 Turbo",
            provider="OpenAI",
            unit_description="per 1K tokens",
            raw_cost_inr_paise=15000,
            total_markup_pct=25.5,
            marked_up_cost_paise=18825,
            is_platform_thread=False,
            applicable_agents=["researcher", "analyst"],
            status="ACTIVE",
        )
        assert entry.thread_id == "thread-001"
        assert entry.display_name == "GPT-4 Turbo"
        assert entry.provider == "OpenAI"
        assert entry.raw_cost_inr_paise == 15000
        assert entry.total_markup_pct == 25.5
        assert entry.is_platform_thread is False
        assert "researcher" in entry.applicable_agents

    def test_thread_entry_missing_required_field(self):
        """Test ThreadEntry rejects missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ThreadEntry(
                thread_id="thread-001",
                display_name="GPT-4 Turbo",
                provider="OpenAI",
                # unit_description missing
                raw_cost_inr_paise=15000,
                total_markup_pct=25.5,
                marked_up_cost_paise=18825,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )
        assert "unit_description" in str(exc_info.value).lower()

    def test_thread_entry_negative_cost_rejected(self):
        """Test ThreadEntry rejects negative cost values."""
        with pytest.raises(ValidationError):
            ThreadEntry(
                thread_id="thread-001",
                display_name="GPT-4 Turbo",
                provider="OpenAI",
                unit_description="per 1K tokens",
                raw_cost_inr_paise=-15000,
                total_markup_pct=25.5,
                marked_up_cost_paise=18825,
                is_platform_thread=False,
                applicable_agents=["researcher"],
                status="ACTIVE",
            )


# ─────────────────────────────────────────────────────────────────────────────
# BundleProfile Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBundleProfile:
    """Test BundleProfile Pydantic model validation."""

    def test_bundle_profile_valid_construction(self):
        """Test valid BundleProfile construction."""
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
        assert isinstance(profile.cost_floor_paise, int)
        assert isinstance(profile.minimum_margin_pct, float)

    def test_bundle_profile_cost_floor_positive(self):
        """Test BundleProfile requires positive cost_floor_paise."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=0,
                minimum_margin_pct=25.0,
                description="Invalid zero cost",
            )

    def test_bundle_profile_margin_pct_positive(self):
        """Test BundleProfile requires positive minimum_margin_pct."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=-5.0,
                description="Invalid negative margin",
            )

    def test_bundle_profile_margin_pct_less_than_100(self):
        """Test BundleProfile rejects margin >= 100%."""
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type="researcher",
                bundle_tier="starter",
                cost_floor_paise=80000,
                minimum_margin_pct=100.0,
                description="Invalid 100% margin",
            )


# ─────────────────────────────────────────────────────────────────────────────
# PriceConfig Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceConfig:
    """Test PriceConfig Pydantic model validation."""

    def test_price_config_valid_construction(self):
        """Test valid PriceConfig construction."""
        config = PriceConfig(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
            derived_price_paise=100000,
        )
        assert config.agent_type == "researcher"
        assert config.bundle_tier == "starter"
        assert config.target_margin_pct == 20.0
        assert config.derived_price_paise == 100000

    def test_price_config_round_trip(self):
        """Test PriceConfig model_dump and model_validate round-trip."""
        original = PriceConfig(
            agent_type="analyst",
            bundle_tier="professional",
            target_margin_pct=30.0,
            derived_price_paise=150000,
        )
        data = original.model_dump()
        restored = PriceConfig(**data)
        assert restored.agent_type == original.agent_type
        assert restored.derived_price_paise == original.derived_price_paise

    def test_price_config_negative_margin_rejected(self):
        """Test PriceConfig rejects negative margin."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-10.0,
                derived_price_paise=100000,
            )

    def test_price_config_negative_derived_price_rejected(self):
        """Test PriceConfig rejects negative derived_price_paise."""
        with pytest.raises(ValidationError):
            PriceConfig(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=20.0,
                derived_price_paise=-100000,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PriceValidationRequest Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceValidationRequest:
    """Test PriceValidationRequest Pydantic model validation."""

    def test_price_validation_request_valid(self):
        """Test valid PriceValidationRequest construction."""
        request = PriceValidationRequest(
            agent_type="researcher",
            bundle_tier="starter",
            proposed_price_paise=100000,
        )
        assert request.agent_type == "researcher"
        assert request.bundle_tier == "starter"
        assert request.proposed_price_paise == 100000

    def test_price_validation_request_missing_proposed_price(self):
        """Test PriceValidationRequest rejects missing proposed_price_paise."""
        with pytest.raises(ValidationError) as exc_info:
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                # proposed_price_paise missing
            )
        assert "proposed_price_paise" in str(exc_info.value).lower()

    def test_price_validation_request_negative_price_rejected(self):
        """Test PriceValidationRequest rejects negative proposed_price_paise."""
        with pytest.raises(ValidationError):
            PriceValidationRequest(
                agent_type="researcher",
                bundle_tier="starter",
                proposed_price_paise=-50000,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PriceDeriveRequest Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceDeriveRequest:
    """Test PriceDeriveRequest Pydantic model validation."""

    def test_price_derive_request_with_explicit_margin(self):
        """Test PriceDeriveRequest with explicit target_margin_pct."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=20.0,
        )
        assert request.agent_type == "researcher"
        assert request.target_margin_pct == 20.0

    def test_price_derive_request_margin_optional(self):
        """Test PriceDeriveRequest with target_margin_pct=None (optional)."""
        request = PriceDeriveRequest(
            agent_type="researcher",
            bundle_tier="starter",
            target_margin_pct=None,
        )
        assert request.agent_type == "researcher"
        assert request.target_margin_pct is None

    def test_price_derive_request_omit_margin(self):
        """Test PriceDeriveRequest omitting target_margin_pct entirely."""
        request = PriceDeriveRequest(
            agent_type="analyst",
            bundle_tier="professional",
        )
        assert request.agent_type == "analyst"
        assert request.target_margin_pct is None

    def test_price_derive_request_negative_margin_rejected(self):
        """Test PriceDeriveRequest rejects negative margin."""
        with pytest.raises(ValidationError):
            PriceDeriveRequest(
                agent_type="researcher",
                bundle_tier="starter",
                target_margin_pct=-5.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PriceValidation (Response) Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceValidation:
    """Test PriceValidation response model."""

    def test_price_validation_response_structure(self):
        """Test PriceValidation response includes all required fields."""
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

    def test_price_validation_outcome_approved(self):
        """Test PriceValidation with APPROVED outcome."""
        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=65000,
        )
        assert response.outcome == "APPROVED"

    def test_price_validation_outcome_rejected(self):
        """Test PriceValidation with REJECTED outcome."""
        response = PriceValidation(
            outcome="REJECTED",
            cost_floor_paise=50000,
            minimum_compliant_price_paise=62500,
            proposed_price_paise=60000,
        )
        assert response.outcome == "REJECTED"
        assert response.proposed_price_paise < response.minimum_compliant_price_paise

    def test_price_validation_all_fields_typed(self):
        """Test PriceValidation field types are correct."""
        response = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        assert isinstance(response.outcome, str)
        assert isinstance(response.cost_floor_paise, int)
        assert isinstance(response.minimum_compliant_price_paise, int)
        assert isinstance(response.proposed_price_paise, int)

    def test_price_validation_invalid_outcome_rejected(self):
        """Test PriceValidation rejects invalid outcome."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome="INVALID_OUTCOME",
                cost_floor_paise=80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )

    def test_price_validation_negative_paise_rejected(self):
        """Test PriceValidation rejects negative paise values."""
        with pytest.raises(ValidationError):
            PriceValidation(
                outcome="APPROVED",
                cost_floor_paise=-80000,
                minimum_compliant_price_paise=100000,
                proposed_price_paise=105000,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Model Serialization
# ─────────────────────────────────────────────────────────────────────────────

class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_thread_entry_json_round_trip(self):
        """Test ThreadEntry JSON serialization round-trip."""
        original = ThreadEntry(
            thread_id="thread-001",
            display_name="GPT-4 Turbo",
            provider="OpenAI",
            unit_description="per 1K tokens",
            raw_cost_inr_paise=15000,
            total_markup_pct=25.5,
            marked_up_cost_paise=18825,
            is_platform_thread=False,
            applicable_agents=["researcher"],
            status="ACTIVE",
        )
        json_str = original.model_dump_json()
        restored = ThreadEntry.model_validate_json(json_str)
        assert restored.thread_id == original.thread_id
        assert restored.raw_cost_inr_paise == original.raw_cost_inr_paise

    def test_bundle_profile_json_round_trip(self):
        """Test BundleProfile JSON serialization round-trip."""
        original = BundleProfile(
            agent_type="researcher",
            bundle_tier="starter",
            cost_floor_paise=80000,
            minimum_margin_pct=25.0,
            description="Test bundle",
        )
        json_str = original.model_dump_json()
        restored = BundleProfile.model_validate_json(json_str)
        assert restored.agent_type == original.agent_type
        assert restored.cost_floor_paise == original.cost_floor_paise

    def test_price_validation_json_round_trip(self):
        """Test PriceValidation JSON serialization round-trip."""
        original = PriceValidation(
            outcome="APPROVED",
            cost_floor_paise=80000,
            minimum_compliant_price_paise=100000,
            proposed_price_paise=105000,
        )
        json_str = original.model_dump_json()
        restored = PriceValidation.model_validate_json(json_str)
        assert restored.outcome == original.outcome
        assert restored.cost_floor_paise == original.cost_floor_paise