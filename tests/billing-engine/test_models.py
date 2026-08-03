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
        entry = ThreadEntry(thread_id="t-001", name="Basic Thread", cost_floor=0.01)
        assert entry.thread_id == "t-001"
        assert entry.name == "Basic Thread"
        assert entry.cost_floor == 0.01

    def test_thread_entry_valid_full(self):
        entry = ThreadEntry(
            thread_id="t-002",
            name="Premium Thread",
            cost_floor=1.50,
            description="A premium thread offering",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.PREMIUM,
        )
        assert entry.thread_id == "t-002"
        assert entry.agent_type == AgentType.ENTERPRISE
        assert entry.bundle_tier == BundleTier.PREMIUM

    def test_thread_entry_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ThreadEntry()

    def test_thread_entry_missing_thread_id(self):
        with pytest.raises(ValidationError):
            ThreadEntry(name="No ID Thread", cost_floor=0.05)

    def test_thread_entry_missing_name(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-003", cost_floor=0.05)

    def test_thread_entry_missing_cost_floor(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-004", name="No Cost Floor")

    def test_thread_entry_negative_cost_floor(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-005", name="Negative Cost", cost_floor=-1.0)

    def test_thread_entry_zero_cost_floor(self):
        entry = ThreadEntry(thread_id="t-006", name="Zero Cost", cost_floor=0.0)
        assert entry.cost_floor == 0.0

    def test_thread_entry_cost_floor_precision(self):
        entry = ThreadEntry(thread_id="t-007", name="Precise Cost", cost_floor=0.123456)
        assert entry.cost_floor == pytest.approx(0.123456)

    def test_thread_entry_serialization(self):
        entry = ThreadEntry(thread_id="t-008", name="Serialize Me", cost_floor=2.00)
        data = entry.model_dump()
        assert data["thread_id"] == "t-008"
        assert data["name"] == "Serialize Me"
        assert data["cost_floor"] == 2.00

    def test_thread_entry_from_dict(self):
        payload = {"thread_id": "t-009", "name": "From Dict", "cost_floor": 0.99}
        entry = ThreadEntry(**payload)
        assert entry.thread_id == "t-009"

    def test_thread_entry_invalid_cost_floor_type(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-010", name="Bad Type", cost_floor="not-a-number")

    def test_thread_entry_thread_id_string(self):
        entry = ThreadEntry(thread_id="thread-abc-123", name="String ID", cost_floor=0.50)
        assert isinstance(entry.thread_id, str)

    def test_thread_entry_name_string(self):
        entry = ThreadEntry(thread_id="t-011", name="Name Check", cost_floor=0.10)
        assert isinstance(entry.name, str)


class TestBundleProfile:
    def test_bundle_profile_valid_minimal(self):
        profile = BundleProfile(
            bundle_id="b-001",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.05,
        )
        assert profile.bundle_id == "b-001"
        assert profile.agent_type == AgentType.SOLO
        assert profile.bundle_tier == BundleTier.BASIC
        assert profile.cost_floor == 0.05

    def test_bundle_profile_valid_full(self):
        profile = BundleProfile(
            bundle_id="b-002",
            agent_type=AgentType.TEAM,
            bundle_tier=BundleTier.STANDARD,
            cost_floor=1.00,
            description="Standard team bundle",
            markup_percentage=15.0,
            thread_entries=[
                ThreadEntry(thread_id="t-001", name="Thread One", cost_floor=0.25),
                ThreadEntry(thread_id="t-002", name="Thread Two", cost_floor=0.75),
            ],
        )
        assert profile.bundle_id == "b-002"
        assert len(profile.thread_entries) == 2
        assert profile.markup_percentage == 15.0

    def test_bundle_profile_missing_required_fields(self):
        with pytest.raises(ValidationError):
            BundleProfile()

    def test_bundle_profile_missing_bundle_id(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
            )

    def test_bundle_profile_missing_agent_type(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-003",
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
            )

    def test_bundle_profile_missing_bundle_tier(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-004",
                agent_type=AgentType.SOLO,
                cost_floor=0.05,
            )

    def test_bundle_profile_missing_cost_floor(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-005",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
            )

    def test_bundle_profile_negative_cost_floor(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-006",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=-0.01,
            )

    def test_bundle_profile_zero_cost_floor(self):
        profile = BundleProfile(
            bundle_id="b-007",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.0,
        )
        assert profile.cost_floor == 0.0

    def test_bundle_profile_invalid_agent_type(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-008",
                agent_type="invalid_agent",
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
            )

    def test_bundle_profile_invalid_bundle_tier(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-009",
                agent_type=AgentType.SOLO,
                bundle_tier="invalid_tier",
                cost_floor=0.05,
            )

    def test_bundle_profile_serialization(self):
        profile = BundleProfile(
            bundle_id="b-010",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.PREMIUM,
            cost_floor=5.00,
        )
        data = profile.model_dump()
        assert data["bundle_id"] == "b-010"
        assert data["cost_floor"] == 5.00

    def test_bundle_profile_from_dict(self):
        payload = {
            "bundle_id": "b-011",
            "agent_type": "solo",
            "bundle_tier": "basic",
            "cost_floor": 0.10,
        }
        profile = BundleProfile(**payload)
        assert profile.bundle_id == "b-011"

    def test_bundle_profile_empty_thread_entries(self):
        profile = BundleProfile(
            bundle_id="b-012",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.05,
            thread_entries=[],
        )
        assert profile.thread_entries == []

    def test_bundle_profile_markup_percentage_zero(self):
        profile = BundleProfile(
            bundle_id="b-013",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.05,
            markup_percentage=0.0,
        )
        assert profile.markup_percentage == 0.0

    def test_bundle_profile_markup_percentage_negative(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-014",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
                markup_percentage=-5.0,
            )

    def test_bundle_profile_all_agent_types(self):
        for agent_type in AgentType:
            profile = BundleProfile(
                bundle_id=f"b-{agent_type}",
                agent_type=agent_type,
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
            )
            assert profile.agent_type == agent_type

    def test_bundle_profile_all_bundle_tiers(self):
        for bundle_tier in BundleTier:
            profile = BundleProfile(
                bundle_id=f"b-{bundle_tier}",
                agent_type=AgentType.SOLO,
                bundle_tier=bundle_tier,
                cost_floor=0.05,
            )
            assert profile.bundle_tier == bundle_tier

    def test_bundle_profile_thread_entries_type_validation(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-015",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
                thread_entries=["not-a-thread-entry"],
            )

    def test_bundle_profile_cost_floor_precision(self):
        profile = BundleProfile(
            bundle_id="b-016",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.123456789,
        )
        assert profile.cost_floor == pytest.approx(0.123456789)

    def test_bundle_profile_nested_thread_entry_validation(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-017",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=0.05,
                thread_entries=[{"thread_id": "t-bad"}],
            )

    def test_bundle_profile_bundle_id_string(self):
        profile = BundleProfile(
            bundle_id="bundle-abc-xyz",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.05,
        )
        assert isinstance(profile.bundle_id, str)