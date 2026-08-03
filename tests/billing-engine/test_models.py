# Implements: WC027-01a — WC027-01ac
# constitutional_basis: C-059, C-082
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

from enum import StrEnum

import pytest
from pydantic import ValidationError

from markup.models import ThreadEntry, BundleProfile


class AgentType(StrEnum):
    SOLO = "solo"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class BundleTier(StrEnum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class TestThreadEntry:
    def test_thread_entry_valid_minimal(self):
        entry = ThreadEntry(thread_id="t-001", name="Basic Thread", unit_cost=1.50)
        assert entry.thread_id == "t-001"
        assert entry.name == "Basic Thread"
        assert entry.unit_cost == 1.50

    def test_thread_entry_valid_full(self):
        entry = ThreadEntry(
            thread_id="t-002",
            name="Premium Thread",
            unit_cost=9.99,
            description="A premium thread option",
            currency="USD",
            active=True,
        )
        assert entry.thread_id == "t-002"
        assert entry.currency == "USD"
        assert entry.active is True

    def test_thread_entry_missing_required_thread_id(self):
        with pytest.raises(ValidationError) as exc_info:
            ThreadEntry(name="No ID Thread", unit_cost=1.00)
        assert "thread_id" in str(exc_info.value)

    def test_thread_entry_missing_required_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ThreadEntry(thread_id="t-003", unit_cost=1.00)
        assert "name" in str(exc_info.value)

    def test_thread_entry_missing_required_unit_cost(self):
        with pytest.raises(ValidationError) as exc_info:
            ThreadEntry(thread_id="t-004", name="No Cost Thread")
        assert "unit_cost" in str(exc_info.value)

    def test_thread_entry_negative_unit_cost_rejected(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-005", name="Negative Cost", unit_cost=-1.00)

    def test_thread_entry_zero_unit_cost(self):
        entry = ThreadEntry(thread_id="t-006", name="Free Thread", unit_cost=0.0)
        assert entry.unit_cost == 0.0

    def test_thread_entry_default_active_true(self):
        entry = ThreadEntry(thread_id="t-007", name="Default Active", unit_cost=2.00)
        assert entry.active is True

    def test_thread_entry_inactive(self):
        entry = ThreadEntry(
            thread_id="t-008", name="Inactive Thread", unit_cost=2.00, active=False
        )
        assert entry.active is False

    def test_thread_entry_default_currency_usd(self):
        entry = ThreadEntry(thread_id="t-009", name="Default Currency", unit_cost=3.00)
        assert entry.currency == "USD"

    def test_thread_entry_serialization(self):
        entry = ThreadEntry(thread_id="t-010", name="Serialize Me", unit_cost=5.00)
        data = entry.model_dump()
        assert data["thread_id"] == "t-010"
        assert data["unit_cost"] == 5.00

    def test_thread_entry_from_dict(self):
        payload = {"thread_id": "t-011", "name": "From Dict", "unit_cost": 7.50}
        entry = ThreadEntry(**payload)
        assert entry.thread_id == "t-011"

    def test_thread_entry_invalid_unit_cost_type(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-012", name="Bad Type", unit_cost="not-a-number")

    def test_thread_entry_large_unit_cost(self):
        entry = ThreadEntry(
            thread_id="t-013", name="Expensive Thread", unit_cost=99999.99
        )
        assert entry.unit_cost == 99999.99

    def test_thread_entry_description_optional(self):
        entry = ThreadEntry(thread_id="t-014", name="No Desc", unit_cost=1.00)
        assert entry.description is None or entry.description == ""


class TestBundleProfile:
    def test_bundle_profile_valid_minimal(self):
        profile = BundleProfile(
            bundle_id="b-001",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=10.00,
        )
        assert profile.bundle_id == "b-001"
        assert profile.base_cost == 10.00

    def test_bundle_profile_valid_full(self):
        profile = BundleProfile(
            bundle_id="b-002",
            agent_type=AgentType.TEAM,
            tier=BundleTier.STANDARD,
            base_cost=50.00,
            markup_percentage=15.0,
            thread_entries=[],
            active=True,
        )
        assert profile.markup_percentage == 15.0
        assert profile.active is True

    def test_bundle_profile_missing_bundle_id(self):
        with pytest.raises(ValidationError) as exc_info:
            BundleProfile(
                agent_type=AgentType.SOLO,
                tier=BundleTier.BASIC,
                base_cost=10.00,
            )
        assert "bundle_id" in str(exc_info.value)

    def test_bundle_profile_missing_agent_type(self):
        with pytest.raises(ValidationError) as exc_info:
            BundleProfile(
                bundle_id="b-003",
                tier=BundleTier.BASIC,
                base_cost=10.00,
            )
        assert "agent_type" in str(exc_info.value)

    def test_bundle_profile_missing_tier(self):
        with pytest.raises(ValidationError) as exc_info:
            BundleProfile(
                bundle_id="b-004",
                agent_type=AgentType.SOLO,
                base_cost=10.00,
            )
        assert "tier" in str(exc_info.value)

    def test_bundle_profile_missing_base_cost(self):
        with pytest.raises(ValidationError) as exc_info:
            BundleProfile(
                bundle_id="b-005",
                agent_type=AgentType.SOLO,
                tier=BundleTier.BASIC,
            )
        assert "base_cost" in str(exc_info.value)

    def test_bundle_profile_negative_base_cost_rejected(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-006",
                agent_type=AgentType.SOLO,
                tier=BundleTier.BASIC,
                base_cost=-5.00,
            )

    def test_bundle_profile_zero_base_cost(self):
        profile = BundleProfile(
            bundle_id="b-007",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=0.0,
        )
        assert profile.base_cost == 0.0

    def test_bundle_profile_markup_percentage_default_zero(self):
        profile = BundleProfile(
            bundle_id="b-008",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=10.00,
        )
        assert profile.markup_percentage == 0.0

    def test_bundle_profile_negative_markup_rejected(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-009",
                agent_type=AgentType.SOLO,
                tier=BundleTier.BASIC,
                base_cost=10.00,
                markup_percentage=-5.0,
            )

    def test_bundle_profile_markup_over_100_rejected(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-010",
                agent_type=AgentType.SOLO,
                tier=BundleTier.BASIC,
                base_cost=10.00,
                markup_percentage=101.0,
            )

    def test_bundle_profile_with_thread_entries(self):
        thread = ThreadEntry(thread_id="t-100", name="Thread A", unit_cost=2.00)
        profile = BundleProfile(
            bundle_id="b-011",
            agent_type=AgentType.ENTERPRISE,
            tier=BundleTier.PREMIUM,
            base_cost=100.00,
            thread_entries=[thread],
        )
        assert len(profile.thread_entries) == 1
        assert profile.thread_entries[0].thread_id == "t-100"

    def test_bundle_profile_default_active_true(self):
        profile = BundleProfile(
            bundle_id="b-012",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=10.00,
        )
        assert profile.active is True

    def test_bundle_profile_serialization(self):
        profile = BundleProfile(
            bundle_id="b-013",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=20.00,
        )
        data = profile.model_dump()
        assert data["bundle_id"] == "b-013"
        assert data["base_cost"] == 20.00

    def test_bundle_profile_effective_cost_calculation(self):
        profile = BundleProfile(
            bundle_id="b-014",
            agent_type=AgentType.TEAM,
            tier=BundleTier.STANDARD,
            base_cost=100.00,
            markup_percentage=10.0,
        )
        expected = 100.00 * (1 + 10.0 / 100)
        assert profile.effective_cost == pytest.approx(expected)

    def test_bundle_profile_effective_cost_no_markup(self):
        profile = BundleProfile(
            bundle_id="b-015",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=50.00,
            markup_percentage=0.0,
        )
        assert profile.effective_cost == pytest.approx(50.00)

    def test_bundle_profile_agent_type_enterprise(self):
        profile = BundleProfile(
            bundle_id="b-016",
            agent_type=AgentType.ENTERPRISE,
            tier=BundleTier.PREMIUM,
            base_cost=500.00,
        )
        assert profile.agent_type == AgentType.ENTERPRISE

    def test_bundle_profile_invalid_agent_type(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-017",
                agent_type="invalid_type",
                tier=BundleTier.BASIC,
                base_cost=10.00,
            )

    def test_bundle_profile_invalid_tier(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-018",
                agent_type=AgentType.SOLO,
                tier="invalid_tier",
                base_cost=10.00,
            )

    def test_bundle_profile_thread_entries_default_empty(self):
        profile = BundleProfile(
            bundle_id="b-019",
            agent_type=AgentType.SOLO,
            tier=BundleTier.BASIC,
            base_cost=10.00,
        )
        assert profile.thread_entries == []

    def test_bundle_profile_multiple_thread_entries(self):
        threads = [
            ThreadEntry(thread_id=f"t-{i}", name=f"Thread {i}", unit_cost=float(i))
            for i in range(1, 4)
        ]
        profile = BundleProfile(
            bundle_id="b-020",
            agent_type=AgentType.TEAM,
            tier=BundleTier.STANDARD,
            base_cost=30.00,
            thread_entries=threads,
        )
        assert len(profile.thread_entries) == 3