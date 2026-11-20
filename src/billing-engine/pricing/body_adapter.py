# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Constitutional basis: C-059, C-088, C-089, C-091
"""Two-way mapping between the published admin API bodies and the stored version bodies.

The published bodies (wbe-pricing-admin.openapi.yaml) and the stored bodies differ only in a few
field names. ``to_internal`` is applied to every body received; ``to_public`` to every body returned.
Neither function validates: an unknown or malformed field is passed through so the pricing validators
refuse it with a machine-readable violation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from markup.package_models import DEFAULT_GST_RATE_PERCENT
from pricing.models import PricingKind

TAX_TREATMENT = "GST_INCLUSIVE"
_PRICED_KINDS = (PricingKind.PACKAGE, PricingKind.COUPON)


def _renamed(body: Mapping[str, Any], renames: Mapping[str, str]) -> dict[str, Any]:
    return {renames.get(key, key): value for key, value in body.items()}


def to_internal(kind: PricingKind, body: Mapping[str, Any]) -> dict[str, Any]:
    """Published body to stored body."""
    if not isinstance(body, Mapping):
        return body  # type: ignore[return-value]
    if kind is PricingKind.GRANT:
        converted = _renamed(body, {"kind": "grantKind", "units": "threadUnits", "paise": "amountPaise"})
        if "windowDays" in converted and "durationDays" not in converted:
            converted["durationDays"] = converted.pop("windowDays")
        return converted
    if kind is PricingKind.BUDGET:
        return _renamed(body, {"ref": "reference"})
    if kind is PricingKind.COUPON:
        return _renamed(body, {"percent": "percentOff"})
    if kind is PricingKind.PACKAGE:
        return {key: value for key, value in body.items() if key != "taxTreatment"}
    return dict(body)


def to_public(kind: PricingKind, body: Mapping[str, Any]) -> dict[str, Any]:
    """Stored body to published body."""
    if kind is PricingKind.GRANT:
        return _renamed(body, {"grantKind": "kind", "threadUnits": "units", "amountPaise": "paise"})
    if kind is PricingKind.BUDGET:
        return _renamed(body, {"reference": "ref"})
    if kind is PricingKind.COUPON:
        return _renamed(body, {"percentOff": "percent"})
    if kind is PricingKind.PACKAGE:
        converted = dict(body)
        converted.setdefault("gstRatePercent", DEFAULT_GST_RATE_PERCENT)
        converted["components"] = [
            {"topupAllowed": False, **component} if isinstance(component, Mapping) else component
            for component in body.get("components", [])
        ]
        return converted
    return dict(body)


def tax_treatment(kind: PricingKind) -> str | None:
    """``taxTreatment`` of a version: present only on the kinds that carry a customer price."""
    return TAX_TREATMENT if kind in _PRICED_KINDS else None
