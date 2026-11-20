# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-038, C-088, C-089, C-091
"""Pro-rata arithmetic of the monthly fee (WC-136 C4-10); pure functions over integer paise.

The fee is shared across the components of a package by their declared price allocations. A pause refunds
the unelapsed share of the paused components, a termination the unelapsed share of the whole fee, and an
upgrade charges the unelapsed difference. Every division rounds half up, so a share never goes below the
paisa the customer is owed. A refund is a billing adjustment, never a wallet refund.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from markup.package_engine import round_half_up_div
from markup.package_models import PackageBody
from wallet.entity_models import as_utc


def remaining_seconds(period_start: datetime, period_end: datetime, at: datetime) -> int:
    """Whole seconds of the period still ahead of ``at``, clamped to the period."""
    start, end, now = as_utc(period_start), as_utc(period_end), as_utc(at)
    if now >= end:
        return 0
    if now <= start:
        return int((end - start).total_seconds())
    return int((end - now).total_seconds())


def period_seconds(period_start: datetime, period_end: datetime) -> int:
    return int((as_utc(period_end) - as_utc(period_start)).total_seconds())


def allocate_by_weight(total_paise: int, weights: Mapping[str, int]) -> dict[str, int]:
    """Split ``total_paise`` over ``weights`` so the parts always sum to the total (largest remainder)."""
    if total_paise < 0 or not weights or any(weight < 0 for weight in weights.values()):
        raise ValueError("allocation needs a non-negative total and weights")
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        raise ValueError("allocation weights sum to zero")
    floors = {key: total_paise * weight // weight_sum for key, weight in weights.items()}
    leftover = total_paise - sum(floors.values())
    by_remainder = sorted(weights, key=lambda key: (-(total_paise * weights[key] % weight_sum), key))
    for key in by_remainder[:leftover]:
        floors[key] += 1
    return floors


def component_fee_shares(package: PackageBody, fee_paid_paise: int) -> dict[str, int]:
    """The fee actually paid shared over the components by price allocation; the infrastructure share is
    carried by every component pro rata so the shares sum to the fee paid."""
    weights = {component.component_id: component.price_allocation_paise for component in package.components}
    if sum(weights.values()) == 0:
        weights = {key: 1 for key in weights}
    return allocate_by_weight(fee_paid_paise, weights)


def prorated_share(share_paise: int, remaining: int, whole: int) -> int:
    """round(share * remaining / period): the unelapsed part of a fee share."""
    if share_paise < 0 or remaining < 0 or whole <= 0:
        raise ValueError("pro-rata needs a non-negative share and a positive period")
    return round_half_up_div(share_paise * min(remaining, whole), whole)


def refund_fee_paise(
    package: PackageBody,
    fee_paid_paise: int,
    component_ids: Iterable[str] | None,
    period_start: datetime,
    period_end: datetime,
    at: datetime,
) -> int:
    """Fee refund for the unelapsed part of a pause (the paused components) or a terminate (all)."""
    shares = component_fee_shares(package, fee_paid_paise)
    chosen = set(shares) if component_ids is None else set(component_ids)
    unknown = chosen - set(shares)
    if unknown:
        raise ValueError(f"unknown components: {sorted(unknown)}")
    allocated = sum(shares[component_id] for component_id in chosen)
    return prorated_share(
        allocated, remaining_seconds(period_start, period_end, at), period_seconds(period_start, period_end)
    )


def upgrade_fee_difference_paise(
    current_price_paise: int,
    new_price_paise: int,
    period_start: datetime,
    period_end: datetime,
    at: datetime,
) -> int:
    """Pro-rated charge for the unelapsed part of the period when moving to a dearer package."""
    difference = new_price_paise - current_price_paise
    if difference <= 0:
        return 0
    return prorated_share(
        difference, remaining_seconds(period_start, period_end, at), period_seconds(period_start, period_end)
    )


def prorated_component_quantity(quantity: int, period_start: datetime, period_end: datetime, at: datetime) -> int:
    """Units of an upgraded component for the unelapsed part of the period (rounded half up, at least one)."""
    whole = period_seconds(period_start, period_end)
    remaining = remaining_seconds(period_start, period_end, at)
    return max(1, round_half_up_div(quantity * remaining, whole)) if quantity > 0 else 0
