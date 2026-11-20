# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-038, C-088, C-089, C-091
"""Pro-rata arithmetic: the shares sum to the fee, refunds equal the unelapsed share to the paisa."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from payment.prorata import (  # noqa: E402
    allocate_by_weight,
    component_fee_shares,
    prorated_component_quantity,
    refund_fee_paise,
    remaining_seconds,
    upgrade_fee_difference_paise,
)
from wc136_commercial_fakes import pro, starter  # noqa: E402

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=30)


def day(count: int) -> datetime:
    return START + timedelta(days=count)


def test_allocation_always_sums_to_the_total() -> None:
    parts = allocate_by_weight(100, {"a": 1, "b": 1, "c": 1})
    assert sum(parts.values()) == 100
    assert sorted(parts.values()) == [33, 33, 34]
    assert sum(allocate_by_weight(30_001, {"x": 20_000, "y": 10_000}).values()) == 30_001


def test_allocation_refuses_empty_or_negative_input() -> None:
    with pytest.raises(ValueError):
        allocate_by_weight(10, {})
    with pytest.raises(ValueError):
        allocate_by_weight(10, {"a": 0})


def test_component_shares_sum_to_the_fee_paid() -> None:
    shares = component_fee_shares(starter().body, 30_001)
    assert sum(shares.values()) == 30_001
    assert shares["POSTS"] > shares["INBOX"]


def test_terminate_on_day_twelve_of_thirty_refunds_the_unelapsed_share_to_the_paisa() -> None:
    assert refund_fee_paise(starter().body, 30_000, None, START, END, day(12)) == 18_000


def test_pause_of_one_component_refunds_only_its_allocation() -> None:
    assert refund_fee_paise(starter().body, 30_000, {"POSTS"}, START, END, day(12)) == 12_000


def test_refund_rounds_half_up_and_never_below_the_owed_paisa() -> None:
    assert refund_fee_paise(starter().body, 3, None, START, START + timedelta(seconds=2), START + timedelta(seconds=1)) == 2


def test_nothing_is_refunded_after_the_period_and_everything_before_it_started() -> None:
    assert refund_fee_paise(starter().body, 30_000, None, START, END, END + timedelta(days=1)) == 0
    assert refund_fee_paise(starter().body, 30_000, None, START, END, START - timedelta(days=1)) == 30_000
    assert remaining_seconds(START, END, day(15)) == 15 * 86_400


def test_unknown_component_is_refused() -> None:
    with pytest.raises(ValueError):
        refund_fee_paise(starter().body, 30_000, {"GHOST"}, START, END, day(1))


def test_upgrade_charges_only_the_unelapsed_difference() -> None:
    difference = pro().body.price_incl_gst_paise - starter().body.price_incl_gst_paise
    assert upgrade_fee_difference_paise(30_000, 60_000, START, END, day(15)) == difference // 2
    assert upgrade_fee_difference_paise(60_000, 30_000, START, END, day(15)) == 0


def test_upgraded_component_quantity_is_prorated_with_a_floor_of_one() -> None:
    assert prorated_component_quantity(8, START, END, day(15)) == 4
    assert prorated_component_quantity(8, START, END, day(30)) == 1
