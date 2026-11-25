# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R001, WC172-R002
# Constitutional basis: C-038, C-059, C-088, C-090
"""The Founder's decisions D1 to D5 as pure rules."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from payment.lifecycle_policy import (  # noqa: E402
    DOWNGRADE_TIMING,
    EXPORT_WINDOW_DAYS,
    PAUSE_MAX_DAYS,
    PRICE_CHANGE_NOTICE_DAYS,
    UPGRADE_TIMING,
    decisions_match,
    export_available_until,
    pause_window_end,
    paused_fee_credit_paise,
    price_change_effective_from,
    service_ends_at,
)
from wc136_commercial_fakes import policy_body, starter  # noqa: E402

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _quarterly():
    return starter().body.model_copy(update={"billing_period_days": 90})


def test_the_recorded_decisions_are_the_founders() -> None:
    assert (PAUSE_MAX_DAYS, EXPORT_WINDOW_DAYS, PRICE_CHANGE_NOTICE_DAYS) == (30, 90, 30)
    assert (UPGRADE_TIMING, DOWNGRADE_TIMING) == ("IMMEDIATE", "AT_RENEWAL")


def test_a_stored_policy_carries_the_upgrade_now_downgrade_later_rule() -> None:
    assert decisions_match("IMMEDIATE", "AT_RENEWAL")
    assert not decisions_match("AT_RENEWAL", "AT_RENEWAL")
    body = policy_body()
    assert decisions_match(body.upgrade_timing, body.downgrade_timing)


def test_a_pause_ends_at_thirty_days_or_the_period_end_whichever_is_first() -> None:
    period_end = START + timedelta(days=90)
    assert pause_window_end(period_end, START) == START + timedelta(days=30)
    assert pause_window_end(period_end, START + timedelta(days=80)) == period_end


def test_the_credit_covers_only_the_thirty_pause_days_of_a_long_period() -> None:
    package = _quarterly()
    end = START + timedelta(days=90)
    # 30 of 90 days of a 90_000 paise fee, then the whole of the last 10 days.
    assert paused_fee_credit_paise(package, 90_000, None, START, end, START) == 30_000
    assert paused_fee_credit_paise(package, 90_000, None, START, end, START + timedelta(days=80)) == 10_000
    assert paused_fee_credit_paise(package, 90_000, ["POSTS"], START, end, START) == 20_000


def test_a_termination_ends_at_the_period_end_and_the_export_stays_ninety_days() -> None:
    end = START + timedelta(days=30)
    assert service_ends_at(end) == end
    assert export_available_until(end) == end + timedelta(days=90)


def test_a_catalogue_price_change_needs_thirty_days_notice() -> None:
    assert price_change_effective_from(START) == START + timedelta(days=30)
