# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R001, WC172-R002, WC172-R003, WC172-R004, WC172-R005
# Implements: architecture/reference/product/lifecycle-commercial-policy.md
# Constitutional basis: C-038, C-059, C-088, C-090
"""The Founder's lifecycle commercial rules D1 to D5 as tested code (settles OP-LIFECYCLE-COMM-01).

D1 Pause: the unused days are credited to the next invoice, never refunded to the card; one pause lasts at most
   30 days; an Emergency Stop never bills and is not a pause.
D2 Terminate: the customer may terminate any day; service ends at the paid period end with no mid-period refund,
   except a documented service failure; the evidence export stays available for 90 days afterwards.
D3 Renewal price: the locked price renews unchanged; a catalogue price change reaches a hire only after 30 days'
   notice and the customer's acknowledgement (ADR-022 Amendment 1.4, C-090), otherwise the old price continues.
D4 Amend: an upgrade is charged pro rata at once; a downgrade takes effect at the next period.
D5 Payer and funder: the payer is the signed-in account holder; a funder needs their own acceptance and a billing
   profile, and every charge names its payer (C-088).

Pure functions over integer paise and timezone-aware datetimes; nothing here reads or writes a database.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Final

from markup.package_models import PackageBody
from payment.prorata import component_fee_shares, period_seconds, prorated_share, remaining_seconds
from wallet.entity_models import as_utc

PAUSE_MAX_DAYS: Final = 30
EXPORT_WINDOW_DAYS: Final = 90
PRICE_CHANGE_NOTICE_DAYS: Final = 30
UPGRADE_TIMING: Final = "IMMEDIATE"
DOWNGRADE_TIMING: Final = "AT_RENEWAL"


def pause_window_end(period_end: datetime, at: datetime) -> datetime:
    """A pause ends at the period end or 30 days after it starts, whichever comes first."""
    return min(as_utc(period_end), as_utc(at) + timedelta(days=PAUSE_MAX_DAYS))


def paused_fee_credit_paise(
    package: PackageBody,
    fee_paid_paise: int,
    component_ids: Iterable[str] | None,
    period_start: datetime,
    period_end: datetime,
    at: datetime,
) -> int:
    """The fee credit for the days a pause actually covers: the paused components' share of the fee, pro rata
    over the pause window (at most 30 days) out of the period. It is a credit, never a card refund (D1)."""
    shares = component_fee_shares(package, fee_paid_paise)
    chosen = set(shares) if component_ids is None else set(component_ids)
    unknown = chosen - set(shares)
    if unknown:
        raise ValueError(f"unknown components: {sorted(unknown)}")
    window = min(
        remaining_seconds(period_start, period_end, at),
        int((pause_window_end(period_end, at) - as_utc(at)).total_seconds()),
    )
    whole = period_seconds(period_start, period_end)
    return prorated_share(sum(shares[component_id] for component_id in chosen), max(0, window), whole)


def service_ends_at(period_end: datetime) -> datetime:
    """A termination ends service at the paid period end (D2)."""
    return as_utc(period_end)


def export_available_until(ends_at: datetime) -> datetime:
    """The evidence export stays downloadable for 90 days after service ends (D2)."""
    return as_utc(ends_at) + timedelta(days=EXPORT_WINDOW_DAYS)


def price_change_effective_from(notified_at: datetime) -> datetime:
    """The earliest day a catalogue price change may reach a locked hire: 30 days after the notice (D3)."""
    return as_utc(notified_at) + timedelta(days=PRICE_CHANGE_NOTICE_DAYS)


def decisions_match(upgrade_timing: str, downgrade_timing: str) -> bool:
    """Whether a stored POLICY version carries the Founder's D4 timings."""
    return (upgrade_timing, downgrade_timing) == (UPGRADE_TIMING, DOWNGRADE_TIMING)
