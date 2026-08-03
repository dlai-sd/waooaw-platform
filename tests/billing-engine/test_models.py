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


# ---------------------------------------------------------------------------
# ThreadEntry model tests
# ---------------------------------------------------------------------------

class TestThreadEntry:
    def test_create_minimal(self):
        entry = ThreadEntry(thread_id="t-001", name="Alpha Thread", cost_per_unit=0.05)
        assert entry.thread_id == "t-001"
        assert entry.name == "Alpha Thread"
        assert entry.cost_per_unit == pytest.approx(0.05)

    def test_create_full(self):
        entry = ThreadEntry(
            thread_id="t-002",
            name="Beta Thread",
            cost_per_unit=0.10,
            description="A full thread entry",
            agent_type=AgentType.TEAM,
            bundle_tier=BundleTier.STANDARD,
            active=True,
        )
        assert entry.thread_id == "t-002"
        assert entry.agent_type == AgentType.TEAM
        assert entry.bundle_tier == BundleTier.STANDARD
        assert entry.active is True

    def test_cost_per_unit_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-003", name="Bad Thread", cost_per_unit=-1.0)

    def test_thread_id_required(self):
        with pytest.raises(ValidationError):
            ThreadEntry(name="No ID Thread", cost_per_unit=0.01)

    def test_name_required(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-004", cost_per_unit=0.01)

    def test_cost_per_unit_required(self):
        with pytest.raises(ValidationError):
            ThreadEntry(thread_id="t-005", name="No Cost Thread")

    def test_default_active_is_true(self):
        entry = ThreadEntry(thread_id="t-006", name="Default Active", cost_per_unit=0.02)
        assert entry.active is True

    def test_inactive_thread(self):
        entry = ThreadEntry(
            thread_id="t-007", name="Inactive Thread", cost_per_unit=0.02, active=False
        )
        assert entry.active is False

    def test_zero_cost_allowed(self):
        entry = ThreadEntry(thread_id="t-008", name="Free Thread", cost_per_unit=0.0)
        assert entry.cost_per_unit == pytest.approx(0.0)

    def test_serialization_round_trip(self):
        entry = ThreadEntry(
            thread_id="t-009",
            name="Round Trip",
            cost_per_unit=0.07,
            description="test desc",
        )
        data = entry.model_dump()
        restored = ThreadEntry(**data)
        assert restored.thread_id == entry.thread_id
        assert restored.name == entry.name
        assert restored.cost_per_unit == entry.cost_per_unit

    def test_json_round_trip(self):
        entry = ThreadEntry(thread_id="t-010", name="JSON Thread", cost_per_unit=0.03)
        json_str = entry.model_dump_json()
        restored = ThreadEntry.model_validate_json(json_str)
        assert restored.thread_id == entry.thread_id

    def test_agent_type_enum_values(self):
        for agent in AgentType:
            entry = ThreadEntry(
                thread_id=f"t-{agent}",
                name=f"Thread {agent}",
                cost_per_unit=0.01,
                agent_type=agent,
            )
            assert entry.agent_type == agent

    def test_bundle_tier_enum_values(self):
        for tier in BundleTier:
            entry = ThreadEntry(
                thread_id=f"t-{tier}",
                name=f"Thread {tier}",
                cost_per_unit=0.01,
                bundle_tier=tier,
            )
            assert entry.bundle_tier == tier


# ---------------------------------------------------------------------------
# BundleProfile model tests
# ---------------------------------------------------------------------------

class TestBundleProfile:
    def test_create_minimal(self):
        profile = BundleProfile(
            bundle_id="b-001",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=1.00,
        )
        assert profile.bundle_id == "b-001"
        assert profile.agent_type == AgentType.SOLO
        assert profile.bundle_tier == BundleTier.BASIC
        assert profile.cost_floor == pytest.approx(1.00)

    def test_create_full(self):
        profile = BundleProfile(
            bundle_id="b-002",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.PREMIUM,
            cost_floor=50.00,
            markup_percentage=15.0,
            description="Enterprise premium bundle",
            active=True,
        )
        assert profile.markup_percentage == pytest.approx(15.0)
        assert profile.description == "Enterprise premium bundle"

    def test_bundle_id_required(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=1.00,
            )

    def test_agent_type_required(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-003",
                bundle_tier=BundleTier.BASIC,
                cost_floor=1.00,
            )

    def test_bundle_tier_required(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-004",
                agent_type=AgentType.SOLO,
                cost_floor=1.00,
            )

    def test_cost_floor_required(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-005",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
            )

    def test_cost_floor_non_negative(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-006",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=-5.00,
            )

    def test_zero_cost_floor_allowed(self):
        profile = BundleProfile(
            bundle_id="b-007",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=0.0,
        )
        assert profile.cost_floor == pytest.approx(0.0)

    def test_markup_percentage_non_negative(self):
        with pytest.raises(ValidationError):
            BundleProfile(
                bundle_id="b-008",
                agent_type=AgentType.SOLO,
                bundle_tier=BundleTier.BASIC,
                cost_floor=1.00,
                markup_percentage=-10.0,
            )

    def test_default_active_is_true(self):
        profile = BundleProfile(
            bundle_id="b-009",
            agent_type=AgentType.TEAM,
            bundle_tier=BundleTier.STANDARD,
            cost_floor=5.00,
        )
        assert profile.active is True

    def test_inactive_bundle(self):
        profile = BundleProfile(
            bundle_id="b-010",
            agent_type=AgentType.TEAM,
            bundle_tier=BundleTier.STANDARD,
            cost_floor=5.00,
            active=False,
        )
        assert profile.active is False

    def test_serialization_round_trip(self):
        profile = BundleProfile(
            bundle_id="b-011",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.PREMIUM,
            cost_floor=100.00,
            markup_percentage=20.0,
        )
        data = profile.model_dump()
        restored = BundleProfile(**data)
        assert restored.bundle_id == profile.bundle_id
        assert restored.cost_floor == profile.cost_floor
        assert restored.markup_percentage == profile.markup_percentage

    def test_json_round_trip(self):
        profile = BundleProfile(
            bundle_id="b-012",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=2.50,
        )
        json_str = profile.model_dump_json()
        restored = BundleProfile.model_validate_json(json_str)
        assert restored.bundle_id == profile.bundle_id

    def test_all_agent_type_bundle_tier_combinations(self):
        for agent in AgentType:
            for tier in BundleTier:
                profile = BundleProfile(
                    bundle_id=f"b-{agent}-{tier}",
                    agent_type=agent,
                    bundle_tier=tier,
                    cost_floor=1.00,
                )
                assert profile.agent_type == agent
                assert profile.bundle_tier == tier

    def test_markup_percentage_zero_allowed(self):
        profile = BundleProfile(
            bundle_id="b-013",
            agent_type=AgentType.SOLO,
            bundle_tier=BundleTier.BASIC,
            cost_floor=1.00,
            markup_percentage=0.0,
        )
        assert profile.markup_percentage == pytest.approx(0.0)

    def test_high_markup_percentage(self):
        profile = BundleProfile(
            bundle_id="b-014",
            agent_type=AgentType.ENTERPRISE,
            bundle_tier=BundleTier.PREMIUM,
            cost_floor=500.00,
            markup_percentage=999.99,
        )
        assert profile.markup_percentage == pytest.approx(999.99)